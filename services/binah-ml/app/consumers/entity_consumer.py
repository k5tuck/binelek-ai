"""
Kafka consumer for entity created events
Tracks new data and triggers auto-training when threshold is reached
"""

import asyncio
import json
import logging
from typing import Dict, Optional
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
import asyncpg
from datetime import datetime

from app.config import settings
from .training_trigger import AutoTrainingTrigger

logger = logging.getLogger(__name__)


class EntityCreatedConsumer:
    """
    Consumes entity.created events from Kafka and tracks new data counters
    per tenant + entity type. Triggers auto-training when threshold is reached.
    """

    def __init__(
        self,
        kafka_broker: str,
        db_pool: asyncpg.Pool,
        mlflow_tracking_uri: str,
        training_threshold: int = 100
    ):
        """
        Initialize the entity created consumer

        Args:
            kafka_broker: Kafka bootstrap servers
            db_pool: PostgreSQL connection pool
            mlflow_tracking_uri: MLflow tracking server URI
            training_threshold: Number of new entities before triggering training
        """
        self.kafka_broker = kafka_broker
        self.db_pool = db_pool
        self.mlflow_tracking_uri = mlflow_tracking_uri
        self.training_threshold = training_threshold
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.running = False

        # Topic to subscribe to
        self.topic = "ontology.entity.created.v1"

        # Training trigger
        self.training_trigger = AutoTrainingTrigger(
            db_pool=db_pool,
            mlflow_tracking_uri=mlflow_tracking_uri
        )

    async def start(self):
        """Start consuming messages from Kafka"""
        try:
            self.consumer = AIOKafkaConsumer(
                self.topic,
                bootstrap_servers=self.kafka_broker,
                group_id='binah-ml-auto-trainer',
                auto_offset_reset='earliest',
                enable_auto_commit=False,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )

            await self.consumer.start()
            self.running = True
            logger.info(
                f"EntityCreatedConsumer started, subscribed to topic: {self.topic}"
            )

            # Initialize counter tracking table
            await self._ensure_counter_table_exists()

            # Consume messages
            await self.consume()

        except Exception as e:
            logger.error(f"Failed to start EntityCreatedConsumer: {e}")
            raise

    async def stop(self):
        """Stop consuming messages and cleanup"""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
            logger.info("EntityCreatedConsumer stopped")

    async def consume(self):
        """Main consume loop"""
        try:
            async for message in self.consumer:
                if not self.running:
                    break

                try:
                    await self.process_event(message.value)

                    # Commit offset after successful processing
                    await self.consumer.commit()

                except Exception as e:
                    logger.error(
                        f"Error processing message from {message.topic}: {e}",
                        exc_info=True
                    )
                    # Continue processing next message

        except KafkaError as e:
            logger.error(f"Kafka consumer error: {e}")
            raise

    async def process_event(self, event: Dict):
        """
        Process entity created event

        Args:
            event: Entity created event payload
        """
        try:
            tenant_id = event.get('tenantId')
            entity_type = event.get('entityType')
            entity_id = event.get('payload', {}).get('entityId')

            if not tenant_id or not entity_type:
                logger.warning(f"Missing tenantId or entityType in event: {event}")
                return

            logger.debug(
                f"Processing entity created event: "
                f"tenant={tenant_id}, type={entity_type}, id={entity_id}"
            )

            # Increment counter
            count = await self.increment_counter(tenant_id, entity_type)

            logger.info(
                f"Entity count for tenant={tenant_id}, type={entity_type}: {count}"
            )

            # Check threshold
            if count >= self.training_threshold:
                logger.info(
                    f"Training threshold reached for tenant={tenant_id}, "
                    f"type={entity_type}. Triggering auto-training..."
                )
                await self.trigger_training(tenant_id, entity_type)

        except Exception as e:
            logger.error(f"Error processing event: {e}", exc_info=True)
            raise

    async def increment_counter(self, tenant_id: str, entity_type: str) -> int:
        """
        Increment the entity counter for a tenant + entity type

        Args:
            tenant_id: Tenant identifier
            entity_type: Entity type name

        Returns:
            Updated counter value
        """
        async with self.db_pool.acquire() as conn:
            # Upsert counter
            result = await conn.fetchrow(
                """
                INSERT INTO ml_entity_counters (tenant_id, entity_type, count, last_updated)
                VALUES ($1, $2, 1, $3)
                ON CONFLICT (tenant_id, entity_type)
                DO UPDATE SET
                    count = ml_entity_counters.count + 1,
                    last_updated = $3
                RETURNING count
                """,
                tenant_id,
                entity_type,
                datetime.utcnow()
            )

            return result['count'] if result else 0

    async def reset_counter(self, tenant_id: str, entity_type: str):
        """
        Reset the entity counter after training

        Args:
            tenant_id: Tenant identifier
            entity_type: Entity type name
        """
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE ml_entity_counters
                SET count = 0, last_trained = $3, last_updated = $3
                WHERE tenant_id = $1 AND entity_type = $2
                """,
                tenant_id,
                entity_type,
                datetime.utcnow()
            )

        logger.info(f"Reset counter for tenant={tenant_id}, type={entity_type}")

    async def get_counter(self, tenant_id: str, entity_type: str) -> int:
        """
        Get current counter value

        Args:
            tenant_id: Tenant identifier
            entity_type: Entity type name

        Returns:
            Current counter value
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT count FROM ml_entity_counters
                WHERE tenant_id = $1 AND entity_type = $2
                """,
                tenant_id,
                entity_type
            )

            return result['count'] if result else 0

    async def trigger_training(self, tenant_id: str, entity_type: str):
        """
        Trigger auto-training for a tenant + entity type

        Args:
            tenant_id: Tenant identifier
            entity_type: Entity type name
        """
        try:
            # Determine model type based on entity type
            model_type = self._map_entity_to_model_type(entity_type)

            if not model_type:
                logger.warning(
                    f"No model type mapping for entity type: {entity_type}. Skipping training."
                )
                return

            logger.info(
                f"Starting auto-training for tenant={tenant_id}, "
                f"entity_type={entity_type}, model_type={model_type}"
            )

            # Trigger training
            model_info = await self.training_trigger.train(
                tenant_id=tenant_id,
                entity_type=entity_type,
                model_type=model_type
            )

            logger.info(
                f"Auto-training completed successfully. Model: {model_info.get('model_name')}, "
                f"Version: {model_info.get('version')}, "
                f"Metrics: {model_info.get('metrics')}"
            )

            # Reset counter after successful training
            await self.reset_counter(tenant_id, entity_type)

        except Exception as e:
            logger.error(
                f"Auto-training failed for tenant={tenant_id}, "
                f"entity_type={entity_type}: {e}",
                exc_info=True
            )
            # Don't reset counter on failure - will retry on next threshold

    def _map_entity_to_model_type(self, entity_type: str) -> Optional[str]:
        """
        Map entity type to ML model type

        Args:
            entity_type: Entity type name

        Returns:
            Model type name or None if no mapping
        """
        mapping = {
            'Property': 'price_prediction',
            'Transaction': 'risk_scoring',
            'Lead': 'lead_scoring',
            'Customer': 'churn_prediction',
            'Listing': 'price_prediction',
            'Asset': 'maintenance_prediction'
        }

        return mapping.get(entity_type)

    async def _ensure_counter_table_exists(self):
        """Ensure the entity counter table exists"""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ml_entity_counters (
                    tenant_id VARCHAR(255) NOT NULL,
                    entity_type VARCHAR(255) NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    last_trained TIMESTAMP,
                    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (tenant_id, entity_type)
                )
                """
            )

        logger.info("Entity counter table initialized")
