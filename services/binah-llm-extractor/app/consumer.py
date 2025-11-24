"""
Kafka Consumer - Consumes unstructured data and extracts entities using LLM.

This consumer listens to extraction.raw.* topics for unstructured text data
and uses the LLM entity extractor to create structured entities.
"""

import json
import logging
import asyncio
from typing import Dict, Any
from aiokafka import AIOKafkaConsumer
import httpx

from .config import settings
from .extractor import LLMEntityExtractor

logger = logging.getLogger(__name__)


class EntityExtractionConsumer:
    """
    Consumes unstructured data from Kafka and extracts entities using LLM.

    Integrates with:
    - binah-discovery: Fetches ontology schemas
    - binah-ontology: Creates extracted entities
    - binah-discovery review queue: Sends low-confidence entities for review
    """

    def __init__(self, extractor: LLMEntityExtractor):
        """Initialize consumer with LLM extractor."""
        self.extractor = extractor
        self.consumer = None
        self.running = False

        # HTTP clients for service communication
        self.ontology_client = httpx.AsyncClient(
            base_url=settings.ONTOLOGY_SERVICE_URL,
            timeout=settings.REQUEST_TIMEOUT
        )
        self.discovery_client = httpx.AsyncClient(
            base_url=settings.DISCOVERY_SERVICE_URL,
            timeout=settings.REQUEST_TIMEOUT
        )

        logger.info("EntityExtractionConsumer initialized")

    async def start(self):
        """Start consuming messages from Kafka."""
        logger.info(
            f"Starting Kafka consumer for topic pattern: "
            f"{settings.KAFKA_TOPIC_PATTERN}"
        )

        self.consumer = AIOKafkaConsumer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_GROUP_ID,
            auto_offset_reset=settings.KAFKA_AUTO_OFFSET_RESET,
            enable_auto_commit=settings.KAFKA_ENABLE_AUTO_COMMIT,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )

        await self.consumer.start()
        self.running = True

        # Subscribe to topic pattern
        self.consumer.subscribe(pattern=settings.KAFKA_TOPIC_PATTERN)

        logger.info("Kafka consumer started successfully")

        try:
            async for msg in self.consumer:
                if not self.running:
                    break
                await self._process_message(msg)
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}", exc_info=True)
        finally:
            await self.stop()

    async def stop(self):
        """Stop the consumer gracefully."""
        logger.info("Stopping Kafka consumer...")
        self.running = False

        if self.consumer:
            await self.consumer.stop()

        await self.ontology_client.aclose()
        await self.discovery_client.aclose()

        logger.info("Kafka consumer stopped")

    async def _process_message(self, msg):
        """Process a single Kafka message."""
        topic = msg.topic
        value = msg.value

        # Extract domain from topic name: extraction.raw.{domain}.v1
        try:
            domain = topic.split('.')[2]
        except IndexError:
            logger.warning(f"Invalid topic format: {topic}")
            return

        tenant_id = value.get("tenant_id")
        if not tenant_id:
            logger.warning(f"No tenant_id in message from topic: {topic}")
            return

        logger.info(
            f"Processing message from topic={topic}, "
            f"tenant={tenant_id}, domain={domain}"
        )

        try:
            # Extract text from message
            raw_text = value.get("text") or value.get("data") or value.get("content")
            if not raw_text:
                logger.warning(f"No text content in message: {value.keys()}")
                return

            if isinstance(raw_text, dict):
                raw_text = json.dumps(raw_text, indent=2)

            # Extract source metadata
            source_metadata = {
                "topic": topic,
                "partition": msg.partition,
                "offset": msg.offset,
                "timestamp": msg.timestamp,
                **value.get("metadata", {})
            }

            # Extract entities using LLM
            extracted = await self.extractor.extract_entities(
                raw_text=raw_text,
                tenant_id=tenant_id,
                domain=domain,
                source_metadata=source_metadata
            )

            logger.info(f"Extracted {len(extracted)} entities from message")

            # Process each extracted entity
            for entity in extracted:
                await self._handle_extracted_entity(
                    entity=entity,
                    tenant_id=tenant_id,
                    source_text=raw_text,
                    source_metadata=source_metadata
                )

        except Exception as e:
            logger.error(
                f"Error processing message from {topic}: {e}",
                exc_info=True
            )

    async def _handle_extracted_entity(
        self,
        entity: Dict[str, Any],
        tenant_id: str,
        source_text: str,
        source_metadata: Dict[str, Any]
    ):
        """Handle a single extracted entity based on confidence score."""
        entity_type = entity.get("type")
        confidence = entity.get("confidence", 0.0)

        logger.debug(
            f"Handling entity: type={entity_type}, confidence={confidence:.2f}"
        )

        # Apply same confidence thresholds as binah-discovery
        if confidence >= settings.AUTO_APPLY_THRESHOLD:
            # High confidence - auto-create entity
            await self._create_entity(
                tenant_id=tenant_id,
                entity_type=entity_type,
                attributes=entity.get("attributes", {}),
                metadata={
                    "source": "llm_extraction",
                    "confidence": confidence,
                    "model": settings.LLM_MODEL,
                    **source_metadata
                }
            )

        elif confidence >= settings.MANUAL_REVIEW_THRESHOLD:
            # Medium confidence - send to review queue
            if settings.SEND_TO_REVIEW_QUEUE:
                await self._send_to_review_queue(
                    tenant_id=tenant_id,
                    entity=entity,
                    source_text=source_text,
                    source_metadata=source_metadata
                )
            else:
                logger.info(
                    f"Skipping review queue (disabled): {entity_type} "
                    f"with confidence {confidence:.2f}"
                )

        else:
            # Low confidence - reject
            logger.info(
                f"Rejected entity {entity_type} with low confidence "
                f"{confidence:.2f} (threshold: {settings.MANUAL_REVIEW_THRESHOLD})"
            )

    async def _create_entity(
        self,
        tenant_id: str,
        entity_type: str,
        attributes: Dict[str, Any],
        metadata: Dict[str, Any]
    ):
        """Create entity in binah-ontology service."""
        try:
            response = await self.ontology_client.post(
                f"/api/tenants/{tenant_id}/entities",
                json={
                    "entityType": entity_type,
                    "attributes": attributes,
                    "metadata": metadata
                },
                headers=self._get_service_headers()
            )

            if response.status_code == 201:
                entity = response.json()
                logger.info(
                    f"✓ Created entity: {entity_type} with ID {entity.get('id')} "
                    f"(confidence: {metadata.get('confidence', 0):.2f})"
                )
            else:
                logger.error(
                    f"Failed to create entity: status={response.status_code}, "
                    f"body={response.text}"
                )

        except Exception as e:
            logger.error(f"Error creating entity: {e}", exc_info=True)

    async def _send_to_review_queue(
        self,
        tenant_id: str,
        entity: Dict[str, Any],
        source_text: str,
        source_metadata: Dict[str, Any]
    ):
        """
        Send medium-confidence entity to binah-discovery review queue.

        This uses the same review queue as binah-discovery for consistency.
        """
        try:
            response = await self.discovery_client.post(
                f"/api/discovery/{tenant_id}/review-queue",
                json={
                    "entity_type": entity["type"],
                    "attributes": entity.get("attributes", {}),
                    "confidence": entity.get("confidence", 0.0),
                    "source": "llm_extraction",
                    "source_data": source_text[:1000],  # Truncate for storage
                    "metadata": {
                        "model": settings.LLM_MODEL,
                        "provider": settings.LLM_PROVIDER,
                        **source_metadata
                    }
                },
                headers=self._get_service_headers()
            )

            if response.status_code in [200, 201]:
                logger.info(
                    f"→ Sent to review queue: {entity['type']} "
                    f"(confidence: {entity.get('confidence', 0):.2f})"
                )
            else:
                logger.error(
                    f"Failed to send to review queue: "
                    f"status={response.status_code}, body={response.text}"
                )

        except Exception as e:
            logger.error(f"Error sending to review queue: {e}", exc_info=True)

    def _get_service_headers(self) -> Dict[str, str]:
        """Get headers for service-to-service communication."""
        return {
            "Content-Type": "application/json",
            "X-Service-Name": settings.SERVICE_NAME,
            "X-Service-Version": settings.SERVICE_VERSION,
            # TODO: Add service-to-service auth token
        }
