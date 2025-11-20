"""
Recommendation Updater Service

Manages updates to the recommendation engine when new relationships are created
in the knowledge graph.

Key Responsibilities:
- Maintain collaborative filtering matrices
- Update content-based recommendation indices
- Recalculate recommendations for affected entities
- Manage recommendation cache and invalidation
- Provide hybrid recommendations (collaborative + content-based)
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from neo4j import AsyncDriver
from qdrant_client import AsyncQdrantClient

logger = logging.getLogger(__name__)


class RecommendationUpdater:
    """
    Service for updating recommendation engine based on knowledge graph changes.

    Implements three recommendation strategies:
    1. Collaborative Filtering - Based on entity relationship patterns
    2. Content-Based Filtering - Based on entity property similarity
    3. Graph-Based - Based on graph structure and path analysis
    """

    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        qdrant_client: AsyncQdrantClient,
        cache_ttl_seconds: int = 3600
    ):
        """
        Initialize Recommendation Updater.

        Args:
            neo4j_driver: Async Neo4j driver instance
            qdrant_client: Async Qdrant client instance
            cache_ttl_seconds: Cache TTL for recommendations (default: 1 hour)
        """
        self.neo4j_driver = neo4j_driver
        self.qdrant_client = qdrant_client
        self.cache_ttl_seconds = cache_ttl_seconds

        # In-memory cache for recommendations
        # In production, this would use Redis
        self._recommendation_cache: Dict[str, Tuple[List[Dict], datetime]] = {}

        # Collaborative filtering matrices (per tenant)
        # In production, this would be persisted to database
        self._cf_matrices: Dict[str, Dict[Tuple[str, str], float]] = defaultdict(dict)

        logger.info("RecommendationUpdater initialized")

    async def add_relationship(
        self,
        tenant_id: str,
        source_id: str,
        target_id: str,
        relationship_type: str,
        weight: float = 1.0
    ):
        """
        Add a new relationship to the collaborative filtering matrix.

        Args:
            tenant_id: Tenant identifier
            source_id: Source entity ID
            target_id: Target entity ID
            relationship_type: Type of relationship
            weight: Relationship weight (default: 1.0)
        """
        try:
            # Add to collaborative filtering matrix
            matrix_key = (source_id, target_id)

            if tenant_id not in self._cf_matrices:
                self._cf_matrices[tenant_id] = {}

            # Update weight (additive for repeated relationships)
            current_weight = self._cf_matrices[tenant_id].get(matrix_key, 0.0)
            self._cf_matrices[tenant_id][matrix_key] = current_weight + weight

            # Store relationship type for later analysis
            # In production, this would query Neo4j for relationship types

            logger.debug(
                f"Added relationship to CF matrix: {source_id} -> {target_id} "
                f"(weight: {weight})"
            )

        except Exception as e:
            logger.error(f"Error adding relationship: {e}")
            raise

    async def recalculate_recommendations(
        self,
        tenant_id: str,
        entity_id: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recalculate recommendations for a specific entity.

        Uses hybrid approach combining:
        1. Collaborative filtering (graph structure)
        2. Content-based filtering (entity similarity)
        3. Graph-based (path analysis)

        Args:
            tenant_id: Tenant identifier
            entity_id: Entity to generate recommendations for
            top_k: Number of recommendations to return

        Returns:
            List of recommended entities with scores
        """
        try:
            # Run all three strategies in parallel
            cf_recs, content_recs, graph_recs = await asyncio.gather(
                self._collaborative_filtering_recommendations(tenant_id, entity_id, top_k),
                self._content_based_recommendations(tenant_id, entity_id, top_k),
                self._graph_based_recommendations(tenant_id, entity_id, top_k),
                return_exceptions=True
            )

            # Handle exceptions
            if isinstance(cf_recs, Exception):
                logger.warning(f"CF recommendations failed: {cf_recs}")
                cf_recs = []
            if isinstance(content_recs, Exception):
                logger.warning(f"Content recommendations failed: {content_recs}")
                content_recs = []
            if isinstance(graph_recs, Exception):
                logger.warning(f"Graph recommendations failed: {graph_recs}")
                graph_recs = []

            # Combine recommendations with weighted scoring
            combined = self._combine_recommendations(
                cf_recs=cf_recs,
                content_recs=content_recs,
                graph_recs=graph_recs,
                weights={'cf': 0.4, 'content': 0.3, 'graph': 0.3}
            )

            # Update cache
            cache_key = f"{tenant_id}:{entity_id}"
            self._recommendation_cache[cache_key] = (combined[:top_k], datetime.utcnow())

            logger.info(f"Recalculated {len(combined)} recommendations for entity {entity_id}")

            return combined[:top_k]

        except Exception as e:
            logger.error(f"Error recalculating recommendations: {e}", exc_info=True)
            return []

    async def _collaborative_filtering_recommendations(
        self,
        tenant_id: str,
        entity_id: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations using collaborative filtering.

        Logic:
        - Find entities with similar relationship patterns
        - Recommend entities that similar entities connect to
        """
        # Query Neo4j for collaborative filtering data
        query = """
        MATCH (e:Entity {id: $entity_id, tenantId: $tenant_id})-[r1]-(intermediate:Entity)
        MATCH (intermediate)-[r2]-(recommended:Entity {tenantId: $tenant_id})
        WHERE recommended.id <> $entity_id
        AND NOT EXISTS((e)--(recommended))

        WITH recommended,
             count(DISTINCT intermediate) as common_neighbors,
             collect(DISTINCT type(r2)) as relationship_types

        RETURN
            recommended.id as entity_id,
            recommended.name as entity_name,
            labels(recommended)[0] as entity_type,
            common_neighbors,
            relationship_types
        ORDER BY common_neighbors DESC
        LIMIT $limit
        """

        async with self.neo4j_driver.session() as session:
            result = await session.run(
                query,
                entity_id=entity_id,
                tenant_id=tenant_id,
                limit=top_k
            )

            recommendations = []
            async for record in result:
                recommendations.append({
                    'entity_id': record['entity_id'],
                    'entity_name': record['entity_name'],
                    'entity_type': record['entity_type'],
                    'score': float(record['common_neighbors']) / 10.0,  # Normalize
                    'reason': f"Shares {record['common_neighbors']} common connections",
                    'strategy': 'collaborative_filtering'
                })

            return recommendations

    async def _content_based_recommendations(
        self,
        tenant_id: str,
        entity_id: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations using content-based filtering.

        Logic:
        - Use Qdrant to find entities with similar embeddings
        - Recommend entities with high semantic similarity
        """
        try:
            collection_name = f"{tenant_id}_rag_knowledge"

            # Get entity's embedding from Qdrant
            entity_point = await self.qdrant_client.retrieve(
                collection_name=collection_name,
                ids=[entity_id]
            )

            if not entity_point:
                return []

            entity_vector = entity_point[0].vector

            # Search for similar entities
            search_result = await self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=entity_vector,
                limit=top_k + 1,  # +1 because query entity will be in results
                score_threshold=0.5  # Minimum similarity threshold
            )

            recommendations = []
            for point in search_result:
                # Skip the query entity itself
                if point.id == entity_id:
                    continue

                recommendations.append({
                    'entity_id': point.id,
                    'entity_name': point.payload.get('properties', {}).get('name', point.id),
                    'entity_type': point.payload.get('entity_type', 'Unknown'),
                    'score': point.score,
                    'reason': f"Similar content (similarity: {point.score:.2f})",
                    'strategy': 'content_based'
                })

            return recommendations[:top_k]

        except Exception as e:
            logger.warning(f"Content-based recommendations failed: {e}")
            return []

    async def _graph_based_recommendations(
        self,
        tenant_id: str,
        entity_id: str,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations using graph structure analysis.

        Logic:
        - Analyze graph patterns (hubs, authorities, communities)
        - Recommend highly connected entities in the same neighborhood
        """
        query = """
        MATCH (e:Entity {id: $entity_id, tenantId: $tenant_id})
        CALL {
            WITH e
            MATCH (e)-[*1..2]-(neighbor:Entity {tenantId: $tenant_id})
            WHERE neighbor.id <> e.id
            RETURN neighbor, count(*) as path_count
        }

        WITH neighbor, path_count,
             size((neighbor)-[:RELATES_TO]-()) as degree

        WHERE NOT EXISTS((e)--(neighbor))

        RETURN
            neighbor.id as entity_id,
            neighbor.name as entity_name,
            labels(neighbor)[0] as entity_type,
            path_count,
            degree
        ORDER BY path_count DESC, degree DESC
        LIMIT $limit
        """

        async with self.neo4j_driver.session() as session:
            result = await session.run(
                query,
                entity_id=entity_id,
                tenant_id=tenant_id,
                limit=top_k
            )

            recommendations = []
            async for record in result:
                recommendations.append({
                    'entity_id': record['entity_id'],
                    'entity_name': record['entity_name'],
                    'entity_type': record['entity_type'],
                    'score': float(record['path_count']) / 5.0,  # Normalize
                    'reason': f"Closely connected in graph (paths: {record['path_count']})",
                    'strategy': 'graph_based'
                })

            return recommendations

    def _combine_recommendations(
        self,
        cf_recs: List[Dict[str, Any]],
        content_recs: List[Dict[str, Any]],
        graph_recs: List[Dict[str, Any]],
        weights: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Combine recommendations from multiple strategies using weighted scoring.

        Args:
            cf_recs: Collaborative filtering recommendations
            content_recs: Content-based recommendations
            graph_recs: Graph-based recommendations
            weights: Strategy weights (must sum to 1.0)

        Returns:
            Combined and re-ranked recommendations
        """
        # Aggregate scores by entity ID
        entity_scores = defaultdict(lambda: {
            'total_score': 0.0,
            'strategies': [],
            'reasons': [],
            'entity_name': None,
            'entity_type': None
        })

        # Add CF recommendations
        for rec in cf_recs:
            entity_id = rec['entity_id']
            entity_scores[entity_id]['total_score'] += rec['score'] * weights['cf']
            entity_scores[entity_id]['strategies'].append('CF')
            entity_scores[entity_id]['reasons'].append(rec['reason'])
            entity_scores[entity_id]['entity_name'] = rec.get('entity_name')
            entity_scores[entity_id]['entity_type'] = rec.get('entity_type')

        # Add content recommendations
        for rec in content_recs:
            entity_id = rec['entity_id']
            entity_scores[entity_id]['total_score'] += rec['score'] * weights['content']
            entity_scores[entity_id]['strategies'].append('Content')
            entity_scores[entity_id]['reasons'].append(rec['reason'])
            if not entity_scores[entity_id]['entity_name']:
                entity_scores[entity_id]['entity_name'] = rec.get('entity_name')
                entity_scores[entity_id]['entity_type'] = rec.get('entity_type')

        # Add graph recommendations
        for rec in graph_recs:
            entity_id = rec['entity_id']
            entity_scores[entity_id]['total_score'] += rec['score'] * weights['graph']
            entity_scores[entity_id]['strategies'].append('Graph')
            entity_scores[entity_id]['reasons'].append(rec['reason'])
            if not entity_scores[entity_id]['entity_name']:
                entity_scores[entity_id]['entity_name'] = rec.get('entity_name')
                entity_scores[entity_id]['entity_type'] = rec.get('entity_type')

        # Convert to list and sort by score
        combined = [
            {
                'entity_id': entity_id,
                'entity_name': data['entity_name'],
                'entity_type': data['entity_type'],
                'score': data['total_score'],
                'strategies': list(set(data['strategies'])),
                'reasons': data['reasons']
            }
            for entity_id, data in entity_scores.items()
        ]

        combined.sort(key=lambda x: x['score'], reverse=True)

        return combined

    async def invalidate_cache(
        self,
        tenant_id: str,
        entity_id: str
    ):
        """
        Invalidate cached recommendations for an entity.

        Called when relationships change.
        """
        cache_key = f"{tenant_id}:{entity_id}"
        if cache_key in self._recommendation_cache:
            del self._recommendation_cache[cache_key]
            logger.debug(f"Invalidated recommendation cache for entity {entity_id}")

    async def update_graph_indices(
        self,
        tenant_id: str,
        entity_ids: List[str]
    ):
        """
        Update graph-based recommendation indices for entities.

        In production, this would update materialized views or graph indices.
        For now, it's a placeholder.
        """
        logger.debug(f"Updated graph indices for {len(entity_ids)} entities")
        # TODO: Implement graph index updates
        pass

    def get_cached_recommendations(
        self,
        tenant_id: str,
        entity_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached recommendations if available and not expired.

        Returns:
            Cached recommendations or None if not available/expired
        """
        cache_key = f"{tenant_id}:{entity_id}"

        if cache_key not in self._recommendation_cache:
            return None

        recommendations, cached_at = self._recommendation_cache[cache_key]

        # Check if cache is expired
        if datetime.utcnow() - cached_at > timedelta(seconds=self.cache_ttl_seconds):
            del self._recommendation_cache[cache_key]
            return None

        return recommendations
