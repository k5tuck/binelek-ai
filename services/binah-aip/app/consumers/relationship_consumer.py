"""
Recommendation Engine Consumer

Consumes relationship creation events from binah-ontology and automatically
updates the recommendation engine's collaborative filtering matrix and
graph-based recommendation indices.

Key Features:
- Updates collaborative filtering matrix when new relationships are created
- Recalculates recommendations for affected entities
- Invalidates recommendation cache
- Maintains graph-based recommendation indices
- Enforces tenant isolation
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from confluent_kafka import Consumer, KafkaError, KafkaException
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class RecommendationEngineConsumer:
    """
    Kafka consumer that updates recommendation engine when relationships are created.

    Subscribes to:
    - ontology.relationship.created.v1

    For each relationship event:
    1. Update collaborative filtering matrix with new relationship
    2. Recalculate recommendations for source and target entities
    3. Update graph-based recommendation indices
    4. Invalidate cache for affected entities

    This enables real-time recommendation updates as the knowledge graph evolves.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        recommendation_updater
    ):
        """
        Initialize Recommendation Engine Consumer.

        Args:
            bootstrap_servers: Kafka broker addresses
            recommendation_updater: RecommendationUpdater instance
        """
        self.bootstrap_servers = bootstrap_servers
        self.consumer: Optional[Consumer] = None
        self.running = False

        # Recommendation updater service
        self.recommendation_updater = recommendation_updater

        # Consumer configuration
        self.consumer_config = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': 'binah-aip-recommendation-updater',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
            'auto.commit.interval.ms': 5000,
            'max.poll.interval.ms': 300000,  # 5 minutes
        }

        # Topics to subscribe to
        self.topics = [
            'ontology.relationship.created.v1'
        ]

        logger.info("RecommendationEngineConsumer initialized")

    async def start(self):
        """Start consuming relationship events"""
        try:
            # Initialize Kafka consumer
            self.consumer = Consumer(self.consumer_config)
            self.consumer.subscribe(self.topics)
            self.running = True

            logger.info(
                f"Recommendation Engine Consumer started. Subscribed to: {self.topics}"
            )

            # Start consumption loop
            await self._consume_loop()

        except KafkaException as e:
            logger.error(f"Kafka consumer error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error starting recommendation consumer: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stop consuming events"""
        self.running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Recommendation Engine Consumer stopped")

    async def _consume_loop(self):
        """Main consumption loop"""
        while self.running:
            try:
                # Poll for messages (synchronous call)
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    # No message available
                    await asyncio.sleep(0.1)
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition
                        logger.debug(f'Reached end of partition: {msg.topic()} [{msg.partition()}]')
                    else:
                        logger.error(f'Error while consuming: {msg.error()}')
                    continue

                # Process the message
                await self._process_message(msg)

            except Exception as e:
                logger.error(f"Error in recommendation consume loop: {e}", exc_info=True)
                await asyncio.sleep(1)  # Back off on error

    async def _process_message(self, msg):
        """Process a single Kafka message"""
        try:
            # Decode message
            topic = msg.topic()
            value = msg.value().decode('utf-8')
            event_data = json.loads(value)

            # Extract event metadata
            event_type = event_data.get('eventType') or event_data.get('event_type')
            tenant_id = event_data.get('tenantId') or event_data.get('tenant_id')
            source_id = event_data.get('sourceId') or event_data.get('source_id') or \
                        event_data.get('fromEntityId') or event_data.get('from_entity_id')
            target_id = event_data.get('targetId') or event_data.get('target_id') or \
                        event_data.get('toEntityId') or event_data.get('to_entity_id')
            relationship_type = event_data.get('relationshipType') or \
                              event_data.get('relationship_type') or \
                              event_data.get('type')

            logger.info(
                f"Processing {event_type}: {source_id} -> {relationship_type} -> {target_id} "
                f"(tenant: {tenant_id})"
            )

            # Validate required fields
            if not tenant_id or not source_id or not target_id:
                logger.warning(f"Missing required fields in event: {event_data}")
                return

            # Update recommendation engine
            await self._update_recommendations(
                tenant_id=tenant_id,
                source_id=source_id,
                target_id=target_id,
                relationship_type=relationship_type,
                event_data=event_data
            )

            logger.info(
                f"Successfully updated recommendations for relationship: "
                f"{source_id} -> {target_id}"
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse event JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing recommendation message: {e}", exc_info=True)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _update_recommendations(
        self,
        tenant_id: str,
        source_id: str,
        target_id: str,
        relationship_type: Optional[str],
        event_data: Dict[str, Any]
    ):
        """
        Update recommendation engine based on new relationship.

        Steps:
        1. Add relationship to collaborative filtering matrix
        2. Recalculate recommendations for source entity
        3. Recalculate recommendations for target entity
        4. Update graph-based recommendation indices
        5. Invalidate cache for affected entities
        """
        try:
            # Add relationship to collaborative filtering matrix
            await self.recommendation_updater.add_relationship(
                tenant_id=tenant_id,
                source_id=source_id,
                target_id=target_id,
                relationship_type=relationship_type or 'RELATED_TO',
                weight=event_data.get('weight', 1.0)
            )

            # Recalculate recommendations for both entities
            # Do this in parallel for efficiency
            await asyncio.gather(
                self.recommendation_updater.recalculate_recommendations(
                    tenant_id=tenant_id,
                    entity_id=source_id
                ),
                self.recommendation_updater.recalculate_recommendations(
                    tenant_id=tenant_id,
                    entity_id=target_id
                ),
                return_exceptions=True
            )

            # Invalidate cache for affected entities
            await asyncio.gather(
                self.recommendation_updater.invalidate_cache(
                    tenant_id=tenant_id,
                    entity_id=source_id
                ),
                self.recommendation_updater.invalidate_cache(
                    tenant_id=tenant_id,
                    entity_id=target_id
                ),
                return_exceptions=True
            )

            # Update graph-based recommendation indices
            await self.recommendation_updater.update_graph_indices(
                tenant_id=tenant_id,
                entity_ids=[source_id, target_id]
            )

            logger.info(
                f"Updated recommendation engine for relationship: "
                f"{source_id} -> {target_id}"
            )

        except Exception as e:
            logger.error(f"Error updating recommendations: {e}", exc_info=True)
            raise

    async def _handle_batch_updates(
        self,
        tenant_id: str,
        relationships: List[Dict[str, Any]]
    ):
        """
        Handle batch relationship updates efficiently.

        Used for bulk imports or migrations.
        """
        try:
            logger.info(f"Processing batch update of {len(relationships)} relationships")

            # Extract all affected entity IDs
            affected_entities = set()
            for rel in relationships:
                source_id = rel.get('source_id') or rel.get('from_entity_id')
                target_id = rel.get('target_id') or rel.get('to_entity_id')
                if source_id:
                    affected_entities.add(source_id)
                if target_id:
                    affected_entities.add(target_id)

            # Add all relationships to matrix
            for rel in relationships:
                await self.recommendation_updater.add_relationship(
                    tenant_id=tenant_id,
                    source_id=rel.get('source_id') or rel.get('from_entity_id'),
                    target_id=rel.get('target_id') or rel.get('to_entity_id'),
                    relationship_type=rel.get('relationship_type', 'RELATED_TO'),
                    weight=rel.get('weight', 1.0)
                )

            # Recalculate recommendations for all affected entities (in batches)
            batch_size = 100
            affected_list = list(affected_entities)

            for i in range(0, len(affected_list), batch_size):
                batch = affected_list[i:i+batch_size]
                tasks = [
                    self.recommendation_updater.recalculate_recommendations(
                        tenant_id=tenant_id,
                        entity_id=entity_id
                    )
                    for entity_id in batch
                ]
                await asyncio.gather(*tasks, return_exceptions=True)

            # Invalidate cache for all affected entities
            for entity_id in affected_entities:
                await self.recommendation_updater.invalidate_cache(
                    tenant_id=tenant_id,
                    entity_id=entity_id
                )

            # Update graph indices for all affected entities
            await self.recommendation_updater.update_graph_indices(
                tenant_id=tenant_id,
                entity_ids=list(affected_entities)
            )

            logger.info(
                f"Completed batch update: {len(relationships)} relationships, "
                f"{len(affected_entities)} entities affected"
            )

        except Exception as e:
            logger.error(f"Error in batch update: {e}", exc_info=True)
            raise
