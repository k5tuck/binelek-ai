"""
Kafka Event Consumer for AI Platform
Consumes events from ontology, context, and integration services
Triggers AI processing based on events
"""

import json
import asyncio
import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime
from confluent_kafka import Consumer, KafkaError, KafkaException
from app.config import settings

logger = logging.getLogger(__name__)


class KafkaEventConsumer:
    """
    Consumes Kafka events and triggers appropriate AI processing
    """

    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.consumer: Optional[Consumer] = None
        self.running = False
        self.event_handlers: Dict[str, Callable] = {}

        # Configure consumer
        self.consumer_config = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': 'binah-ai-consumer',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
            'auto.commit.interval.ms': 5000,
            'max.poll.interval.ms': 300000,  # 5 minutes
        }

        # Topics to subscribe to
        self.topics = [
            'Binah.ontology.events',
            'Binah.context.events',
            'Binah.integration.events',
            'Binah.pipeline.events'
        ]

        # Register default event handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default event handlers"""
        self.event_handlers = {
            'EntityCreated': self._handle_entity_created,
            'EntityUpdated': self._handle_entity_updated,
            'EntityDeleted': self._handle_entity_deleted,
            'RelationshipCreated': self._handle_relationship_created,
            'RelationshipDeleted': self._handle_relationship_deleted,
            'EmbeddingGenerated': self._handle_embedding_generated,
            'DataIngested': self._handle_data_ingested,
            'EntityFullyProcessed': self._handle_entity_fully_processed,
        }

    async def start(self):
        """Start consuming events"""
        try:
            self.consumer = Consumer(self.consumer_config)
            self.consumer.subscribe(self.topics)
            self.running = True

            logger.info(f"Kafka consumer started. Subscribed to topics: {self.topics}")

            # Start consumption loop
            await self._consume_loop()

        except KafkaException as e:
            logger.error(f"Kafka consumer error: {e}")
            raise

    async def stop(self):
        """Stop consuming events"""
        self.running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer stopped")

    async def _consume_loop(self):
        """Main consumption loop"""
        while self.running:
            try:
                # Poll for messages
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    # No message available, continue
                    await asyncio.sleep(0.1)
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition event
                        logger.debug(f'Reached end of partition: {msg.topic()} [{msg.partition()}]')
                    else:
                        logger.error(f'Error while consuming: {msg.error()}')
                    continue

                # Process the message
                await self._process_message(msg)

            except Exception as e:
                logger.error(f"Error in consume loop: {e}", exc_info=True)
                await asyncio.sleep(1)  # Back off on error

    async def _process_message(self, msg):
        """Process a Kafka message"""
        try:
            # Decode message
            topic = msg.topic()
            key = msg.key().decode('utf-8') if msg.key() else None
            value = msg.value().decode('utf-8')

            # Parse JSON payload
            event_data = json.loads(value)

            # Extract event type from headers or payload
            event_type = None
            if msg.headers():
                for header_key, header_value in msg.headers():
                    if header_key == 'event-type':
                        event_type = header_value.decode('utf-8')
                        break

            if not event_type:
                event_type = event_data.get('eventType') or event_data.get('event_type')

            logger.info(f"Received event: {event_type} from topic: {topic}, key: {key}")
            logger.debug(f"Event data: {event_data}")

            # Route to appropriate handler
            if event_type and event_type in self.event_handlers:
                handler = self.event_handlers[event_type]
                await handler(event_data, topic, key)
            else:
                logger.warning(f"No handler registered for event type: {event_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse event JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    # Event Handlers

    async def _handle_entity_created(self, event_data: Dict[str, Any], topic: str, key: str):
        """Handle EntityCreated event"""
        logger.info(f"Processing EntityCreated event for entity: {event_data.get('entityId')}")

        try:
            entity_id = event_data.get('entityId')
            entity_type = event_data.get('entityType')
            tenant_id = event_data.get('tenantId')
            properties = event_data.get('properties', {})

            # Trigger AI analysis for the new entity
            analysis_tasks = []

            # 1. Entity classification
            if entity_type:
                analysis_tasks.append(self._classify_entity(entity_id, entity_type, properties))

            # 2. Risk assessment
            analysis_tasks.append(self._assess_risk(entity_id, entity_type, properties))

            # 3. Recommendations generation
            analysis_tasks.append(self._generate_recommendations(entity_id, entity_type, properties))

            # 4. Relationship suggestions
            analysis_tasks.append(self._suggest_relationships(entity_id, entity_type, properties, tenant_id))

            # Execute all analysis tasks
            await asyncio.gather(*analysis_tasks, return_exceptions=True)

            logger.info(f"AI analysis completed for entity: {entity_id}")

        except Exception as e:
            logger.error(f"Error handling EntityCreated event: {e}", exc_info=True)

    async def _handle_entity_updated(self, event_data: Dict[str, Any], topic: str, key: str):
        """Handle EntityUpdated event"""
        logger.info(f"Processing EntityUpdated event for entity: {event_data.get('entityId')}")

        try:
            entity_id = event_data.get('entityId')
            changed_properties = event_data.get('changedProperties', {})

            # Trigger incremental analysis based on what changed
            if changed_properties:
                await self._incremental_analysis(entity_id, changed_properties)

            # Check if ontology recommendations need updating
            tenant_id = event_data.get('tenantId')
            if tenant_id:
                await self._trigger_ontology_analysis(tenant_id)

        except Exception as e:
            logger.error(f"Error handling EntityUpdated event: {e}", exc_info=True)

    async def _handle_entity_deleted(self, event_data: Dict[str, Any], topic: str, key: str):
        """Handle EntityDeleted event"""
        logger.info(f"Processing EntityDeleted event for entity: {event_data.get('entityId')}")

        try:
            entity_id = event_data.get('entityId')

            # Clean up AI-generated data for this entity
            await self._cleanup_ai_data(entity_id)

            logger.info(f"AI data cleaned up for deleted entity: {entity_id}")

        except Exception as e:
            logger.error(f"Error handling EntityDeleted event: {e}", exc_info=True)

    async def _handle_relationship_created(self, event_data: Dict[str, Any], topic: str, key: str):
        """Handle RelationshipCreated event"""
        logger.info("Processing RelationshipCreated event")

        try:
            from_entity_id = event_data.get('fromEntityId')
            to_entity_id = event_data.get('toEntityId')
            relationship_type = event_data.get('relationshipType')

            # Analyze impact of new relationship
            await self._analyze_relationship_impact(from_entity_id, to_entity_id, relationship_type)

            # Update graph-based recommendations
            await self._update_graph_recommendations(from_entity_id, to_entity_id)

        except Exception as e:
            logger.error(f"Error handling RelationshipCreated event: {e}", exc_info=True)

    async def _handle_relationship_deleted(self, event_data: Dict[str, Any], topic: str, key: str):
        """Handle RelationshipDeleted event"""
        logger.info("Processing RelationshipDeleted event")

        try:
            from_entity_id = event_data.get('fromEntityId')
            to_entity_id = event_data.get('toEntityId')

            # Re-evaluate recommendations without this relationship
            await self._update_graph_recommendations(from_entity_id, to_entity_id)

        except Exception as e:
            logger.error(f"Error handling RelationshipDeleted event: {e}", exc_info=True)

    async def _handle_embedding_generated(self, event_data: Dict[str, Any], topic: str, key: str):
        """Handle EmbeddingGenerated event from context service"""
        logger.info("Processing EmbeddingGenerated event")

        try:
            entity_id = event_data.get('entityId')
            embedding_id = event_data.get('embeddingId')

            # Trigger semantic similarity analysis
            await self._semantic_similarity_analysis(entity_id, embedding_id)

        except Exception as e:
            logger.error(f"Error handling EmbeddingGenerated event: {e}", exc_info=True)

    async def _handle_data_ingested(self, event_data: Dict[str, Any], topic: str, key: str):
        """Handle DataIngested event from pipeline service"""
        logger.info("Processing DataIngested event")

        try:
            batch_id = event_data.get('batchId')
            record_count = event_data.get('recordCount', 0)

            logger.info(f"Data batch ingested: {batch_id}, {record_count} records")

            # Trigger batch analysis if needed
            if record_count > 0:
                await self._batch_analysis(batch_id, record_count)

        except Exception as e:
            logger.error(f"Error handling DataIngested event: {e}", exc_info=True)

    async def _handle_entity_fully_processed(self, event_data: Dict[str, Any], topic: str, key: str):
        """Handle EntityFullyProcessed event (saga completion)"""
        logger.info("Processing EntityFullyProcessed event")

        try:
            entity_id = event_data.get('entityId')
            tenant_id = event_data.get('tenantId')
            steps = event_data.get('steps', {})

            logger.info(f"Entity {entity_id} fully processed. Steps: {steps}")

            # Trigger final analysis now that all data is available
            if steps.get('ontologyCreated') and steps.get('embeddingsGenerated'):
                await self._comprehensive_analysis(entity_id, tenant_id)

            # Check for autonomous ontology recommendations
            if tenant_id:
                await self._trigger_ontology_analysis(tenant_id)

        except Exception as e:
            logger.error(f"Error handling EntityFullyProcessed event: {e}", exc_info=True)

    # AI Processing Methods

    async def _classify_entity(self, entity_id: str, entity_type: str, properties: Dict[str, Any]):
        """Classify entity using AI"""
        logger.debug(f"Classifying entity {entity_id} of type {entity_type}")
        # TODO: Implement actual classification logic
        await asyncio.sleep(0.1)  # Simulate processing

    async def _assess_risk(self, entity_id: str, entity_type: str, properties: Dict[str, Any]):
        """Assess risk for entity"""
        logger.debug(f"Assessing risk for entity {entity_id}")
        # TODO: Implement risk assessment logic
        await asyncio.sleep(0.1)

    async def _generate_recommendations(self, entity_id: str, entity_type: str, properties: Dict[str, Any]):
        """Generate recommendations for entity"""
        logger.debug(f"Generating recommendations for entity {entity_id}")
        # TODO: Implement recommendation logic
        await asyncio.sleep(0.1)

    async def _suggest_relationships(self, entity_id: str, entity_type: str, properties: Dict[str, Any], tenant_id: str):
        """Suggest potential relationships"""
        logger.debug(f"Suggesting relationships for entity {entity_id}")
        # TODO: Implement relationship suggestion logic
        await asyncio.sleep(0.1)

    async def _incremental_analysis(self, entity_id: str, changed_properties: Dict[str, Any]):
        """Perform incremental analysis on changed properties"""
        logger.debug(f"Incremental analysis for entity {entity_id}")
        await asyncio.sleep(0.1)

    async def _trigger_ontology_analysis(self, tenant_id: str):
        """Trigger autonomous ontology analysis"""
        logger.debug(f"Triggering ontology analysis for tenant {tenant_id}")
        # TODO: Call autonomous ontology orchestrator
        await asyncio.sleep(0.1)

    async def _cleanup_ai_data(self, entity_id: str):
        """Clean up AI-generated data for deleted entity"""
        logger.debug(f"Cleaning up AI data for entity {entity_id}")
        await asyncio.sleep(0.1)

    async def _analyze_relationship_impact(self, from_entity_id: str, to_entity_id: str, relationship_type: str):
        """Analyze impact of new relationship"""
        logger.debug(f"Analyzing relationship impact: {from_entity_id} -> {to_entity_id}")
        await asyncio.sleep(0.1)

    async def _update_graph_recommendations(self, entity_id_1: str, entity_id_2: str):
        """Update graph-based recommendations"""
        logger.debug(f"Updating graph recommendations for entities {entity_id_1}, {entity_id_2}")
        await asyncio.sleep(0.1)

    async def _semantic_similarity_analysis(self, entity_id: str, embedding_id: str):
        """Perform semantic similarity analysis"""
        logger.debug(f"Semantic similarity analysis for entity {entity_id}")
        await asyncio.sleep(0.1)

    async def _batch_analysis(self, batch_id: str, record_count: int):
        """Analyze ingested batch of data"""
        logger.debug(f"Batch analysis for batch {batch_id} with {record_count} records")
        await asyncio.sleep(0.1)

    async def _comprehensive_analysis(self, entity_id: str, tenant_id: str):
        """Comprehensive analysis after all data is available"""
        logger.info(f"Running comprehensive analysis for entity {entity_id}")
        await asyncio.sleep(0.1)


# Singleton instance
_kafka_consumer: Optional[KafkaEventConsumer] = None


def get_kafka_consumer(bootstrap_servers: str = "localhost:9092") -> KafkaEventConsumer:
    """Get or create Kafka consumer singleton"""
    global _kafka_consumer
    if _kafka_consumer is None:
        _kafka_consumer = KafkaEventConsumer(bootstrap_servers)
    return _kafka_consumer


async def start_kafka_consumer(bootstrap_servers: str = "localhost:9092"):
    """Start Kafka consumer as background task"""
    consumer = get_kafka_consumer(bootstrap_servers)
    await consumer.start()


async def stop_kafka_consumer():
    """Stop Kafka consumer"""
    global _kafka_consumer
    if _kafka_consumer:
        await _kafka_consumer.stop()
        _kafka_consumer = None
