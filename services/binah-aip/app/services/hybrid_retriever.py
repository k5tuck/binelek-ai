"""Hybrid Retriever - Combines Neo4j, Qdrant, and PostgreSQL for RAG"""

from neo4j import AsyncGraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
import logging
from app.config import settings
from typing import Any

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Retrieves relevant context from multiple data sources"""

    def __init__(self):
        # Neo4j connection
        self.neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password)
        )

        # Qdrant connection
        self.qdrant_client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key
        )

    async def retrieve(
        self,
        query: str,
        tenant_id: str,
        retrieval_type: str = "hybrid",
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant context from data sources

        Args:
            query: Search query
            tenant_id: Tenant ID for filtering
            retrieval_type: Type of retrieval (graph, vector, hybrid)
            limit: Maximum results to return

        Returns:
            List of relevant documents/entities
        """
        results = []

        try:
            if retrieval_type in ["graph", "hybrid"]:
                graph_results = await self._retrieve_from_graph(query, tenant_id, limit)
                results.extend(graph_results)

            if retrieval_type in ["vector", "hybrid"]:
                vector_results = await self._retrieve_from_vectors(query, tenant_id, limit)
                results.extend(vector_results)

            # Deduplicate and rank
            results = self._deduplicate_and_rank(results, limit)

            logger.info(f"Retrieved {len(results)} results for tenant {tenant_id}")
            return results

        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return []

    async def _retrieve_from_graph(
        self,
        query: str,
        tenant_id: str,
        limit: int
    ) -> list[dict[str, Any]]:
        """Retrieve from Neo4j knowledge graph"""
        try:
            async with self.neo4j_driver.session() as session:
                # Full-text search on entities
                cypher = """
                CALL db.index.fulltext.queryNodes('entitySearch', $query)
                YIELD node, score
                WHERE node.tenantId = $tenantId
                RETURN
                    node.id as id,
                    node.name as name,
                    labels(node)[0] as type,
                    properties(node) as properties,
                    score,
                    'graph' as source
                ORDER BY score DESC
                LIMIT $limit
                """

                result = await session.run(
                    cypher,
                    query=query,
                    tenantId=tenant_id,
                    limit=limit
                )

                records = await result.data()
                return [
                    {
                        "id": r["id"],
                        "name": r["name"],
                        "type": r["type"],
                        "properties": r["properties"],
                        "score": r["score"],
                        "source": "graph"
                    }
                    for r in records
                ]

        except Exception as e:
            logger.error(f"Graph retrieval error: {e}")
            return []

    async def _retrieve_from_vectors(
        self,
        query: str,
        tenant_id: str,
        limit: int
    ) -> list[dict[str, Any]]:
        """Retrieve from Qdrant vector store"""
        try:
            # Note: In production, query should be embedded first
            # For now, we'll use a placeholder search

            search_result = self.qdrant_client.scroll(
                collection_name="entities",
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="tenant_id",
                            match=MatchValue(value=tenant_id)
                        )
                    ]
                ),
                limit=limit,
                with_payload=True,
                with_vectors=False
            )

            results = []
            for point in search_result[0]:
                results.append({
                    "id": point.id,
                    "payload": point.payload,
                    "source": "vector"
                })

            return results

        except Exception as e:
            logger.error(f"Vector retrieval error: {e}")
            return []

    def _deduplicate_and_rank(
        self,
        results: list[dict[str, Any]],
        limit: int
    ) -> list[dict[str, Any]]:
        """Deduplicate results and rank by relevance"""
        # Simple deduplication by ID
        seen_ids = set()
        unique_results = []

        for result in results:
            result_id = result.get("id")
            if result_id and result_id not in seen_ids:
                seen_ids.add(result_id)
                unique_results.append(result)

        # Sort by score if available
        unique_results.sort(
            key=lambda x: x.get("score", 0),
            reverse=True
        )

        return unique_results[:limit]

    async def close(self):
        """Close connections"""
        await self.neo4j_driver.close()
