"""
Usage Analytics Collector

Captures comprehensive usage data from all platform touchpoints:
- Neo4j query logs
- API access logs
- GraphQL introspection
- Kafka event streams
- User behavior tracking
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

from ..models import (
    UsageMetrics,
    EntityAccessMetrics,
    RelationshipTraversalMetrics,
    PropertyAccessMetrics,
    QueryPattern,
    QueryType
)

logger = logging.getLogger(__name__)


class UsageAnalyticsCollector:
    """
    Collects usage analytics from multiple data sources.

    This is the foundation of Phase 1 - it gathers all the data needed
    for the AI recommendation engine to make informed decisions.
    """

    def __init__(
        self,
        neo4j_client=None,
        timescaledb_client=None,
        kafka_consumer=None
    ):
        """
        Initialize the usage analytics collector.

        Args:
            neo4j_client: Neo4j database client for query logs
            timescaledb_client: TimescaleDB client for storing metrics
            kafka_consumer: Kafka consumer for event streams
        """
        self.neo4j_client = neo4j_client
        self.timescaledb_client = timescaledb_client
        self.kafka_consumer = kafka_consumer

        logger.info("UsageAnalyticsCollector initialized")

    async def collect_usage_metrics(
        self,
        tenant_id: str,
        time_window_days: int = 30,
        domain: Optional[str] = None
    ) -> UsageMetrics:
        """
        Collect comprehensive usage metrics for a tenant.

        Args:
            tenant_id: Tenant identifier
            time_window_days: Number of days to look back
            domain: Optional domain filter (e.g., 'real-estate', 'healthcare')

        Returns:
            UsageMetrics object with all collected data
        """
        logger.info(
            f"Collecting usage metrics for tenant={tenant_id}, "
            f"window={time_window_days} days, domain={domain}"
        )

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=time_window_days)

        # Collect metrics from all sources in parallel
        entity_access_task = self._collect_entity_access(tenant_id, start_time, end_time, domain)
        relationship_task = self._collect_relationship_traversals(tenant_id, start_time, end_time, domain)
        property_task = self._collect_property_access(tenant_id, start_time, end_time, domain)
        query_pattern_task = self._collect_query_patterns(tenant_id, start_time, end_time, domain)

        (
            entity_access,
            relationship_traversals,
            property_access,
            query_patterns
        ) = await asyncio.gather(
            entity_access_task,
            relationship_task,
            property_task,
            query_pattern_task
        )

        # Calculate summary stats
        total_queries = sum(qp.execution_count for qp in query_patterns)
        unique_entities = len(set(ea.entity_type for ea in entity_access))

        metrics = UsageMetrics(
            tenant_id=tenant_id,
            time_window_start=start_time,
            time_window_end=end_time,
            entity_access=entity_access,
            relationship_traversals=relationship_traversals,
            property_access=property_access,
            query_patterns=query_patterns,
            total_queries=total_queries,
            unique_entities_accessed=unique_entities
        )

        # Store in TimescaleDB for historical tracking
        await self._store_metrics(metrics)

        logger.info(
            f"Collected metrics for {tenant_id}: "
            f"{total_queries} queries, {unique_entities} unique entities"
        )

        return metrics

    async def _collect_entity_access(
        self,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime,
        domain: Optional[str]
    ) -> List[EntityAccessMetrics]:
        """Collect entity access patterns from Neo4j query logs"""

        # In production, this would query actual Neo4j logs
        # For now, we'll query Neo4j to get entity statistics

        if not self.neo4j_client:
            logger.warning("No Neo4j client configured, returning mock data")
            return self._mock_entity_access(tenant_id)

        # Example Cypher query to analyze entity access
        query = """
        // Get all queries from query log in time window
        MATCH (log:QueryLog)
        WHERE log.tenantId = $tenantId
          AND log.timestamp >= $startTime
          AND log.timestamp <= $endTime
          AND ($domain IS NULL OR log.domain = $domain)

        // Extract entity types from queries
        WITH log,
             [label IN log.matchedLabels | label] AS entityTypes,
             log.executionTime AS execTime

        UNWIND entityTypes AS entityType

        // Aggregate by entity type
        RETURN
            entityType,
            COUNT(*) AS readCount,
            AVG(execTime) AS avgResponseTime,
            MAX(log.timestamp) AS lastAccessed
        ORDER BY readCount DESC
        """

        try:
            # Execute query (mock implementation for now)
            results = []  # await self.neo4j_client.execute(query, {...})

            return [
                EntityAccessMetrics(
                    entity_type=row["entityType"],
                    read_count=row["readCount"],
                    avg_response_time=row["avgResponseTime"],
                    last_accessed=row["lastAccessed"],
                    tenant_id=tenant_id
                )
                for row in results
            ]
        except Exception as e:
            logger.error(f"Error collecting entity access: {e}")
            return []

    async def _collect_relationship_traversals(
        self,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime,
        domain: Optional[str]
    ) -> List[RelationshipTraversalMetrics]:
        """Collect relationship traversal patterns"""

        if not self.neo4j_client:
            logger.warning("No Neo4j client configured, returning mock data")
            return self._mock_relationship_traversals(tenant_id)

        # Query to analyze relationship usage
        query = """
        MATCH (log:QueryLog)
        WHERE log.tenantId = $tenantId
          AND log.timestamp >= $startTime
          AND log.timestamp <= $endTime

        // Extract relationship patterns
        WITH log,
             log.relationshipTraversals AS traversals

        UNWIND traversals AS rel

        RETURN
            rel.type AS relationshipType,
            rel.fromEntity AS fromEntity,
            rel.toEntity AS toEntity,
            COUNT(*) AS frequency,
            AVG(rel.depth) AS avgDepth,
            AVG(log.executionTime) AS avgResponseTime
        ORDER BY frequency DESC
        """

        try:
            results = []  # Mock
            return [
                RelationshipTraversalMetrics(
                    relationship_type=row["relationshipType"],
                    from_entity=row["fromEntity"],
                    to_entity=row["toEntity"],
                    frequency=row["frequency"],
                    avg_depth=row["avgDepth"],
                    avg_response_time=row["avgResponseTime"],
                    tenant_id=tenant_id
                )
                for row in results
            ]
        except Exception as e:
            logger.error(f"Error collecting relationship traversals: {e}")
            return []

    async def _collect_property_access(
        self,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime,
        domain: Optional[str]
    ) -> List[PropertyAccessMetrics]:
        """Collect property access patterns"""

        if not self.neo4j_client:
            logger.warning("No Neo4j client configured, returning mock data")
            return self._mock_property_access(tenant_id)

        # Analyze which properties are accessed most frequently
        query = """
        MATCH (log:QueryLog)
        WHERE log.tenantId = $tenantId
          AND log.timestamp >= $startTime
          AND log.timestamp <= $endTime

        WITH log,
             log.propertiesAccessed AS props

        UNWIND props AS prop

        RETURN
            prop.entityType AS entityType,
            prop.propertyName AS propertyName,
            COUNT(*) AS accessCount,
            AVG(CASE WHEN prop.value IS NULL THEN 1.0 ELSE 0.0 END) AS nullRate,
            COUNT(DISTINCT prop.value) AS uniqueValues
        ORDER BY accessCount DESC
        """

        try:
            results = []  # Mock
            return [
                PropertyAccessMetrics(
                    entity_type=row["entityType"],
                    property_name=row["propertyName"],
                    access_count=row["accessCount"],
                    null_rate=row["nullRate"],
                    unique_values=row["uniqueValues"],
                    tenant_id=tenant_id
                )
                for row in results
            ]
        except Exception as e:
            logger.error(f"Error collecting property access: {e}")
            return []

    async def _collect_query_patterns(
        self,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime,
        domain: Optional[str]
    ) -> List[QueryPattern]:
        """Collect and analyze query patterns"""

        if not self.neo4j_client:
            logger.warning("No Neo4j client configured, returning mock data")
            return self._mock_query_patterns(tenant_id)

        # Group similar queries by pattern
        query = """
        MATCH (log:QueryLog)
        WHERE log.tenantId = $tenantId
          AND log.timestamp >= $startTime
          AND log.timestamp <= $endTime

        // Normalize queries to patterns (remove literals)
        WITH log,
             log.cypherQuery AS rawQuery,
             apoc.text.replace(rawQuery, '\\d+', 'N') AS normalized,
             apoc.text.replace(normalized, '["\'].*?["\']', 'S') AS pattern

        RETURN
            apoc.util.md5([pattern]) AS patternHash,
            pattern AS cypherPattern,
            COUNT(*) AS executionCount,
            AVG(log.executionTime) AS avgDuration,
            SUM(CASE WHEN log.failed THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS failureRate,
            MAX(log.timestamp) AS lastExecuted
        ORDER BY executionCount DESC
        LIMIT 100
        """

        try:
            results = []  # Mock
            return [
                QueryPattern(
                    pattern_hash=row["patternHash"],
                    cypher_pattern=row["cypherPattern"],
                    execution_count=row["executionCount"],
                    avg_duration=row["avgDuration"],
                    failure_rate=row["failureRate"],
                    last_executed=row["lastExecuted"],
                    tenant_id=tenant_id
                )
                for row in results
            ]
        except Exception as e:
            logger.error(f"Error collecting query patterns: {e}")
            return []

    async def _store_metrics(self, metrics: UsageMetrics) -> None:
        """Store collected metrics in TimescaleDB"""

        if not self.timescaledb_client:
            logger.warning("No TimescaleDB client configured, skipping storage")
            return

        try:
            # Store entity access metrics
            for ea in metrics.entity_access:
                await self.timescaledb_client.execute("""
                    INSERT INTO entity_access_metrics
                    (timestamp, tenant_id, entity_type, read_count, write_count, avg_response_time)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, metrics.time_window_end, ea.tenant_id, ea.entity_type,
                    ea.read_count, ea.write_count, ea.avg_response_time)

            # Store relationship traversals
            for rt in metrics.relationship_traversals:
                await self.timescaledb_client.execute("""
                    INSERT INTO relationship_traversal_metrics
                    (timestamp, tenant_id, relationship_type, from_entity, to_entity, frequency, avg_depth)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, metrics.time_window_end, rt.tenant_id, rt.relationship_type,
                    rt.from_entity, rt.to_entity, rt.frequency, rt.avg_depth)

            logger.info(f"Stored metrics for tenant {metrics.tenant_id} in TimescaleDB")

        except Exception as e:
            logger.error(f"Error storing metrics: {e}")

    # Mock data generators for development/testing

    def _mock_entity_access(self, tenant_id: str) -> List[EntityAccessMetrics]:
        """Generate mock entity access data for testing"""
        return [
            EntityAccessMetrics(
                entity_type="Property",
                read_count=1250,
                write_count=150,
                avg_response_time=45.5,
                last_accessed=datetime.utcnow(),
                tenant_id=tenant_id
            ),
            EntityAccessMetrics(
                entity_type="Owner",
                read_count=890,
                write_count=120,
                avg_response_time=32.1,
                last_accessed=datetime.utcnow(),
                tenant_id=tenant_id
            ),
            EntityAccessMetrics(
                entity_type="Transaction",
                read_count=560,
                write_count=340,
                avg_response_time=67.8,
                last_accessed=datetime.utcnow(),
                tenant_id=tenant_id
            )
        ]

    def _mock_relationship_traversals(self, tenant_id: str) -> List[RelationshipTraversalMetrics]:
        """Generate mock relationship traversal data"""
        return [
            RelationshipTraversalMetrics(
                relationship_type="OWNED_BY",
                from_entity="Property",
                to_entity="Owner",
                frequency=1150,
                avg_depth=1.0,
                avg_response_time=28.3,
                tenant_id=tenant_id
            ),
            RelationshipTraversalMetrics(
                relationship_type="HAS_TRANSACTION",
                from_entity="Property",
                to_entity="Transaction",
                frequency=890,
                avg_depth=1.2,
                avg_response_time=52.1,
                tenant_id=tenant_id
            )
        ]

    def _mock_property_access(self, tenant_id: str) -> List[PropertyAccessMetrics]:
        """Generate mock property access data"""
        return [
            PropertyAccessMetrics(
                entity_type="Property",
                property_name="address",
                access_count=1200,
                null_rate=0.02,
                unique_values=1150,
                tenant_id=tenant_id
            ),
            PropertyAccessMetrics(
                entity_type="Property",
                property_name="price",
                access_count=1100,
                null_rate=0.15,
                unique_values=980,
                tenant_id=tenant_id
            )
        ]

    def _mock_query_patterns(self, tenant_id: str) -> List[QueryPattern]:
        """Generate mock query patterns"""
        return [
            QueryPattern(
                pattern_hash="abc123",
                cypher_pattern="MATCH (p:Property)-[:OWNED_BY]->(o:Owner) WHERE p.price < N RETURN p",
                execution_count=450,
                avg_duration=45.2,
                failure_rate=0.02,
                last_executed=datetime.utcnow(),
                tenant_id=tenant_id
            )
        ]
