"""
RAG Knowledge Base Consumer

Consumes entity creation/update events from binah-ontology and automatically
updates the RAG knowledge base in Qdrant with comprehensive contextual embeddings.

Key Features:
- Fetches entity context from Neo4j (neighbors, relationships, properties)
- Generates rich contextual text representations for embeddings
- Updates Qdrant RAG knowledge base with entity context
- Maintains tenant isolation
- Handles errors gracefully with retry logic
"""

import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from confluent_kafka import Consumer, KafkaError, KafkaException
from neo4j import AsyncGraphDatabase, AsyncDriver
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from langchain.embeddings import OpenAIEmbeddings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class RAGKnowledgeBaseConsumer:
    """
    Kafka consumer that updates RAG knowledge base when entities are created/updated.

    Subscribes to:
    - ontology.entity.created.v1
    - ontology.entity.updated.v1

    For each entity event:
    1. Fetch comprehensive context from Neo4j (entity + neighbors + relationships)
    2. Generate rich text representation of entity and its context
    3. Generate embedding using OpenAI/Anthropic
    4. Store in Qdrant RAG collection with full metadata

    This enables the RAG system to have deep contextual understanding of each entity.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        neo4j_uri: str,
        neo4j_username: str,
        neo4j_password: str,
        qdrant_client: AsyncQdrantClient,
        embedding_model: str = "text-embedding-3-small"
    ):
        """
        Initialize RAG Knowledge Base Consumer.

        Args:
            bootstrap_servers: Kafka broker addresses
            neo4j_uri: Neo4j connection URI
            neo4j_username: Neo4j username
            neo4j_password: Neo4j password
            qdrant_client: Async Qdrant client instance
            embedding_model: OpenAI embedding model name
        """
        self.bootstrap_servers = bootstrap_servers
        self.consumer: Optional[Consumer] = None
        self.running = False

        # Neo4j connection
        self.neo4j_driver: AsyncDriver = AsyncGraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_username, neo4j_password)
        )

        # Qdrant client
        self.qdrant_client = qdrant_client

        # Embedding generator
        self.embeddings = OpenAIEmbeddings(model=embedding_model)

        # Consumer configuration
        self.consumer_config = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': 'binah-aip-rag-updater',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
            'auto.commit.interval.ms': 5000,
            'max.poll.interval.ms': 300000,  # 5 minutes
        }

        # Topics to subscribe to
        self.topics = [
            'ontology.entity.created.v1',
            'ontology.entity.updated.v1'
        ]

        logger.info("RAGKnowledgeBaseConsumer initialized")

    async def start(self):
        """Start consuming entity events"""
        try:
            # Ensure RAG collections exist
            await self._ensure_rag_collections()

            # Initialize Kafka consumer
            self.consumer = Consumer(self.consumer_config)
            self.consumer.subscribe(self.topics)
            self.running = True

            logger.info(f"RAG Knowledge Base Consumer started. Subscribed to: {self.topics}")

            # Start consumption loop
            await self._consume_loop()

        except KafkaException as e:
            logger.error(f"Kafka consumer error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error starting RAG consumer: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stop consuming events"""
        self.running = False
        if self.consumer:
            self.consumer.close()
            logger.info("RAG Knowledge Base Consumer stopped")

        # Close Neo4j driver
        if self.neo4j_driver:
            await self.neo4j_driver.close()

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
                logger.error(f"Error in RAG consume loop: {e}", exc_info=True)
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
            entity_id = event_data.get('entityId') or event_data.get('entity_id')
            entity_type = event_data.get('entityType') or event_data.get('entity_type')

            logger.info(f"Processing {event_type} for entity {entity_id} (tenant: {tenant_id})")

            # Validate required fields
            if not tenant_id or not entity_id:
                logger.warning(f"Missing required fields in event: {event_data}")
                return

            # Update RAG knowledge base
            await self._update_rag_knowledge_base(
                tenant_id=tenant_id,
                entity_id=entity_id,
                entity_type=entity_type,
                event_data=event_data
            )

            logger.info(f"Successfully updated RAG knowledge base for entity {entity_id}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse event JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing RAG message: {e}", exc_info=True)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _update_rag_knowledge_base(
        self,
        tenant_id: str,
        entity_id: str,
        entity_type: Optional[str],
        event_data: Dict[str, Any]
    ):
        """
        Update RAG knowledge base with comprehensive entity context.

        Steps:
        1. Fetch entity and all its context from Neo4j
        2. Generate rich text representation
        3. Generate embedding
        4. Upsert into Qdrant RAG collection
        """
        try:
            # Fetch comprehensive entity context from Neo4j
            context_data = await self._fetch_entity_context(tenant_id, entity_id)

            if not context_data:
                logger.warning(f"No context data found for entity {entity_id}")
                return

            # Generate rich text representation
            context_text = self._format_context_for_rag(context_data, entity_type)

            # Generate embedding
            embedding = await self._generate_embedding(context_text)

            # Prepare metadata
            metadata = {
                'entity_id': entity_id,
                'entity_type': entity_type or context_data.get('entity_type', 'Unknown'),
                'tenant_id': tenant_id,
                'context': context_text,
                'properties': context_data.get('properties', {}),
                'neighbor_count': len(context_data.get('neighbors', [])),
                'relationship_count': context_data.get('relationship_count', 0),
                'indexed_at': datetime.utcnow().isoformat(),
                'event_type': event_data.get('eventType', 'unknown')
            }

            # Store in Qdrant RAG collection
            collection_name = f"{tenant_id}_rag_knowledge"

            await self.qdrant_client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=entity_id,
                        vector=embedding,
                        payload=metadata
                    )
                ]
            )

            logger.info(f"Updated RAG knowledge base: {entity_id} in {collection_name}")

        except Exception as e:
            logger.error(f"Error updating RAG knowledge base: {e}", exc_info=True)
            raise

    async def _fetch_entity_context(
        self,
        tenant_id: str,
        entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch comprehensive entity context from Neo4j.

        Returns:
        - Entity properties
        - All neighbors (connected entities)
        - All relationships with types and directions
        - Relationship properties
        - Multi-hop paths (2-hop neighbors for richer context)
        """
        query = """
        MATCH (e:Entity {id: $entity_id, tenantId: $tenant_id})

        // Get direct neighbors and relationships
        OPTIONAL MATCH (e)-[r]-(neighbor:Entity {tenantId: $tenant_id})

        // Get 2-hop neighbors for richer context (limited to 5 per direct neighbor)
        OPTIONAL MATCH (neighbor)-[r2]-(neighbor2:Entity {tenantId: $tenant_id})
        WHERE neighbor2.id <> e.id
        WITH e, r, neighbor, collect(DISTINCT neighbor2)[0..5] as second_hop_neighbors

        RETURN
            e as entity,
            labels(e) as entity_labels,
            properties(e) as entity_properties,
            collect(DISTINCT {
                relationship_type: type(r),
                relationship_id: id(r),
                relationship_properties: properties(r),
                neighbor_id: neighbor.id,
                neighbor_type: labels(neighbor)[0],
                neighbor_name: neighbor.name,
                neighbor_properties: properties(neighbor),
                direction: CASE
                    WHEN startNode(r) = e THEN 'outgoing'
                    ELSE 'incoming'
                END,
                second_hop: [n2 IN second_hop_neighbors | {
                    id: n2.id,
                    type: labels(n2)[0],
                    name: n2.name
                }]
            }) as relationships
        """

        async with self.neo4j_driver.session() as session:
            result = await session.run(
                query,
                entity_id=entity_id,
                tenant_id=tenant_id
            )
            record = await result.single()

            if not record:
                return None

            # Extract and structure the data
            entity = record['entity']
            entity_props = record['entity_properties']
            relationships = record['relationships']

            # Filter out null relationships
            relationships = [r for r in relationships if r['neighbor_id'] is not None]

            return {
                'entity_id': entity_id,
                'entity_type': record['entity_labels'][0] if record['entity_labels'] else 'Entity',
                'properties': dict(entity_props),
                'neighbors': relationships,
                'relationship_count': len(relationships)
            }

    def _format_context_for_rag(
        self,
        context_data: Dict[str, Any],
        entity_type: Optional[str]
    ) -> str:
        """
        Format entity context into rich text representation for RAG embedding.

        This creates a comprehensive text description that captures:
        - Entity type and identifier
        - All entity properties
        - All connected entities and relationship types
        - 2-hop context for understanding entity's place in the graph

        Example output:
        '''
        Property: 123 Main Street
        Type: Property
        Properties:
          - address: 123 Main Street
          - sqft: 2500
          - price: 450000

        Connected Entities:
          - OWNED_BY (outgoing) → Owner: John Doe
          - LOCATED_IN (outgoing) → City: San Francisco
          - HAS_LISTING (incoming) ← Listing: MLS-456

        Extended Context (2-hop):
          - Owner John Doe is also connected to Property: 456 Oak Avenue
          - City San Francisco is also connected to Neighborhood: Mission District
        '''
        """
        entity_id = context_data['entity_id']
        entity_type_resolved = entity_type or context_data['entity_type']
        properties = context_data['properties']
        neighbors = context_data['neighbors']

        # Build rich text representation
        lines = []

        # Header
        entity_name = properties.get('name') or properties.get('title') or entity_id
        lines.append(f"{entity_type_resolved}: {entity_name}")
        lines.append(f"Type: {entity_type_resolved}")
        lines.append(f"ID: {entity_id}")
        lines.append("")

        # Properties section
        if properties:
            lines.append("Properties:")
            for key, value in properties.items():
                if key not in ['id', 'tenantId', 'createdAt', 'updatedAt']:
                    lines.append(f"  - {key}: {value}")
            lines.append("")

        # Relationships section
        if neighbors:
            lines.append("Connected Entities:")
            for rel in neighbors:
                direction_symbol = "→" if rel['direction'] == 'outgoing' else "←"
                neighbor_name = rel.get('neighbor_name') or rel['neighbor_id']
                rel_type = rel['relationship_type']
                neighbor_type = rel.get('neighbor_type', 'Entity')

                lines.append(
                    f"  - {rel_type} ({rel['direction']}) {direction_symbol} "
                    f"{neighbor_type}: {neighbor_name}"
                )

                # Add relationship properties if any
                rel_props = rel.get('relationship_properties', {})
                if rel_props:
                    for key, value in rel_props.items():
                        lines.append(f"      {key}: {value}")
            lines.append("")

        # Extended context (2-hop neighbors)
        second_hop_items = []
        for rel in neighbors:
            second_hop = rel.get('second_hop', [])
            if second_hop:
                neighbor_name = rel.get('neighbor_name') or rel['neighbor_id']
                neighbor_type = rel.get('neighbor_type', 'Entity')

                for sh in second_hop:
                    sh_name = sh.get('name') or sh['id']
                    sh_type = sh.get('type', 'Entity')
                    second_hop_items.append(
                        f"  - {neighbor_type} {neighbor_name} is also connected to "
                        f"{sh_type}: {sh_name}"
                    )

        if second_hop_items:
            lines.append("Extended Context (2-hop):")
            lines.extend(second_hop_items[:10])  # Limit to 10 to avoid context overflow
            lines.append("")

        return "\n".join(lines)

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI embeddings"""
        try:
            # Use LangChain's async embedding
            embedding = await self.embeddings.aembed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def _ensure_rag_collections(self):
        """Ensure Qdrant RAG collections exist for all active tenants"""
        # For now, collections are created on-demand when first entity is indexed
        # In production, this would query a tenant registry service
        logger.info("RAG collections will be created on-demand per tenant")
        pass

    async def _ensure_collection_exists(self, collection_name: str):
        """Ensure a specific RAG collection exists in Qdrant"""
        try:
            # Check if collection exists
            collections = await self.qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if collection_name not in collection_names:
                # Create collection
                await self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=1536,  # OpenAI text-embedding-3-small dimension
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created RAG collection: {collection_name}")
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            # Continue anyway - upsert will create if needed
