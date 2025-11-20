"""
RAG Updater Service

Manages updates to the RAG (Retrieval-Augmented Generation) knowledge base
when entities are created or updated in the knowledge graph.

Key Responsibilities:
- Fetch comprehensive entity context from Neo4j
- Generate rich text representations for embeddings
- Update Qdrant RAG collections with contextual embeddings
- Maintain RAG metadata and versioning
- Handle incremental updates efficiently
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from neo4j import AsyncDriver
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams, Filter, FieldCondition
from langchain.embeddings import OpenAIEmbeddings

logger = logging.getLogger(__name__)


class RAGUpdater:
    """
    Service for updating RAG knowledge base with entity context.

    Uses Neo4j to fetch comprehensive entity context and stores
    contextual embeddings in Qdrant for semantic search and RAG.
    """

    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        qdrant_client: AsyncQdrantClient,
        embedding_model: str = "text-embedding-3-small"
    ):
        """
        Initialize RAG Updater.

        Args:
            neo4j_driver: Async Neo4j driver instance
            qdrant_client: Async Qdrant client instance
            embedding_model: OpenAI embedding model name
        """
        self.neo4j_driver = neo4j_driver
        self.qdrant_client = qdrant_client
        self.embeddings = OpenAIEmbeddings(model=embedding_model)

        logger.info("RAGUpdater initialized")

    async def update_entity_context(
        self,
        tenant_id: str,
        entity_id: str,
        entity_type: Optional[str] = None
    ):
        """
        Update RAG knowledge base with latest entity context.

        Args:
            tenant_id: Tenant identifier
            entity_id: Entity identifier
            entity_type: Optional entity type hint
        """
        try:
            # Fetch entity context from Neo4j
            context_data = await self._fetch_entity_context(tenant_id, entity_id)

            if not context_data:
                logger.warning(f"No context found for entity {entity_id}")
                return

            # Generate rich text representation
            context_text = self._generate_context_text(context_data, entity_type)

            # Generate embedding
            embedding = await self._generate_embedding(context_text)

            # Prepare metadata
            metadata = self._prepare_metadata(context_data, entity_type, context_text)

            # Update Qdrant collection
            await self._update_qdrant_collection(
                tenant_id=tenant_id,
                entity_id=entity_id,
                embedding=embedding,
                metadata=metadata
            )

            logger.info(f"Updated RAG context for entity {entity_id}")

        except Exception as e:
            logger.error(f"Error updating entity context: {e}", exc_info=True)
            raise

    async def _fetch_entity_context(
        self,
        tenant_id: str,
        entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch comprehensive entity context from Neo4j.

        Returns entity with:
        - All properties
        - Direct neighbors (1-hop)
        - Relationship types and properties
        - Selected 2-hop neighbors for extended context
        - Entity degree (number of connections)
        - Common patterns (e.g., ownership chains, location hierarchies)
        """
        query = """
        MATCH (e:Entity {id: $entity_id, tenantId: $tenant_id})

        // Get direct neighbors and relationships
        OPTIONAL MATCH (e)-[r]-(neighbor:Entity {tenantId: $tenant_id})

        // Get entity degree
        WITH e, r, neighbor,
             size((e)-[:RELATES_TO]-()) as degree

        // Get 2-hop neighbors (limited)
        OPTIONAL MATCH (neighbor)-[r2]-(neighbor2:Entity {tenantId: $tenant_id})
        WHERE neighbor2.id <> e.id AND id(r2) IS NOT NULL
        WITH e, r, neighbor, degree,
             collect(DISTINCT {
                id: neighbor2.id,
                type: labels(neighbor2)[0],
                name: coalesce(neighbor2.name, neighbor2.id)
             })[0..5] as second_hop

        // Get common relationship patterns
        WITH e, degree,
             collect(DISTINCT {
                relationship_type: type(r),
                relationship_id: id(r),
                relationship_properties: properties(r),
                neighbor_id: neighbor.id,
                neighbor_type: labels(neighbor)[0],
                neighbor_name: coalesce(neighbor.name, neighbor.id),
                neighbor_properties: properties(neighbor),
                direction: CASE
                    WHEN startNode(r) = e THEN 'outgoing'
                    ELSE 'incoming'
                END,
                second_hop: second_hop
             }) as relationships

        RETURN
            e as entity,
            labels(e) as entity_labels,
            properties(e) as entity_properties,
            relationships,
            degree
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

            # Extract data
            entity_props = dict(record['entity_properties'])
            relationships = [r for r in record['relationships'] if r['neighbor_id'] is not None]

            return {
                'entity_id': entity_id,
                'entity_type': record['entity_labels'][0] if record['entity_labels'] else 'Entity',
                'properties': entity_props,
                'neighbors': relationships,
                'degree': record['degree'],
                'relationship_count': len(relationships)
            }

    def _generate_context_text(
        self,
        context_data: Dict[str, Any],
        entity_type_hint: Optional[str]
    ) -> str:
        """
        Generate rich text representation of entity context for RAG.

        Creates a narrative description that includes:
        - Entity type and identifier
        - Key properties in natural language
        - Relationship descriptions
        - Context from connected entities
        """
        entity_id = context_data['entity_id']
        entity_type = entity_type_hint or context_data['entity_type']
        properties = context_data['properties']
        neighbors = context_data['neighbors']
        degree = context_data.get('degree', 0)

        lines = []

        # Entity header
        entity_name = properties.get('name') or properties.get('title') or entity_id
        lines.append(f"Entity: {entity_name}")
        lines.append(f"Type: {entity_type}")
        lines.append(f"Connections: {degree}")
        lines.append("")

        # Key properties (natural language)
        if properties:
            lines.append("Description:")
            for key, value in properties.items():
                if key not in ['id', 'tenantId', 'createdAt', 'updatedAt', 'name', 'title']:
                    if value is not None:
                        lines.append(f"  {key.replace('_', ' ').title()}: {value}")
            lines.append("")

        # Relationships (grouped by type)
        if neighbors:
            rel_by_type = {}
            for rel in neighbors:
                rel_type = rel['relationship_type']
                if rel_type not in rel_by_type:
                    rel_by_type[rel_type] = []
                rel_by_type[rel_type].append(rel)

            lines.append("Relationships:")
            for rel_type, rels in rel_by_type.items():
                direction = rels[0]['direction']
                count = len(rels)

                if count == 1:
                    rel = rels[0]
                    neighbor_name = rel.get('neighbor_name', rel['neighbor_id'])
                    neighbor_type = rel.get('neighbor_type', 'Entity')
                    lines.append(
                        f"  {rel_type} ({direction}): {neighbor_type} '{neighbor_name}'"
                    )
                else:
                    sample_names = [
                        rel.get('neighbor_name', rel['neighbor_id'])
                        for rel in rels[:3]
                    ]
                    lines.append(
                        f"  {rel_type} ({direction}): {count} entities "
                        f"(e.g., {', '.join(sample_names)})"
                    )
            lines.append("")

        # Extended context from 2-hop neighbors
        second_hop_contexts = []
        for rel in neighbors[:5]:  # Limit to top 5 relationships
            second_hop = rel.get('second_hop', [])
            if second_hop:
                neighbor_name = rel.get('neighbor_name', rel['neighbor_id'])
                for sh in second_hop[:2]:  # Max 2 per relationship
                    sh_name = sh.get('name', sh['id'])
                    sh_type = sh.get('type', 'Entity')
                    second_hop_contexts.append(
                        f"  Connected via {neighbor_name} to {sh_type} '{sh_name}'"
                    )

        if second_hop_contexts:
            lines.append("Extended Context:")
            lines.extend(second_hop_contexts)
            lines.append("")

        return "\n".join(lines)

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text"""
        try:
            embedding = await self.embeddings.aembed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def _prepare_metadata(
        self,
        context_data: Dict[str, Any],
        entity_type: Optional[str],
        context_text: str
    ) -> Dict[str, Any]:
        """Prepare metadata payload for Qdrant"""
        return {
            'entity_id': context_data['entity_id'],
            'entity_type': entity_type or context_data['entity_type'],
            'properties': context_data['properties'],
            'context_text': context_text,
            'neighbor_count': len(context_data.get('neighbors', [])),
            'relationship_count': context_data.get('relationship_count', 0),
            'degree': context_data.get('degree', 0),
            'indexed_at': datetime.utcnow().isoformat(),
            'version': 1
        }

    async def _update_qdrant_collection(
        self,
        tenant_id: str,
        entity_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ):
        """Update Qdrant collection with entity embedding"""
        collection_name = f"{tenant_id}_rag_knowledge"

        # Ensure collection exists
        await self._ensure_collection_exists(collection_name)

        # Upsert point
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

        logger.debug(f"Updated Qdrant collection {collection_name} with entity {entity_id}")

    async def _ensure_collection_exists(self, collection_name: str):
        """Ensure Qdrant collection exists, create if not"""
        try:
            collections = await self.qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if collection_name not in collection_names:
                await self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=1536,  # OpenAI text-embedding-3-small
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created RAG collection: {collection_name}")
        except Exception as e:
            logger.warning(f"Error ensuring collection exists: {e}")
            # Continue - upsert will handle it

    async def delete_entity_context(
        self,
        tenant_id: str,
        entity_id: str
    ):
        """
        Delete entity context from RAG knowledge base.

        Called when an entity is deleted.
        """
        try:
            collection_name = f"{tenant_id}_rag_knowledge"

            await self.qdrant_client.delete(
                collection_name=collection_name,
                points_selector=[entity_id]
            )

            logger.info(f"Deleted entity {entity_id} from RAG knowledge base")

        except Exception as e:
            logger.error(f"Error deleting entity context: {e}")
            # Don't raise - deletion is best-effort
