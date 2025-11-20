"""
Query Log Collector

Collects and processes Neo4j query logs for pattern analysis.
This feeds into the usage analytics system.
"""

import logging
import hashlib
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class QueryLogCollector:
    """
    Collects Neo4j query logs and processes them for analysis.

    Key responsibilities:
    - Extract queries from Neo4j query.log
    - Normalize queries to identify patterns
    - Calculate execution statistics
    - Feed data to TimescaleDB for time-series analysis
    """

    def __init__(self, neo4j_client=None, timescaledb_client=None):
        self.neo4j_client = neo4j_client
        self.timescaledb_client = timescaledb_client
        logger.info("QueryLogCollector initialized")

    async def collect_query_logs(
        self,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Collect query logs for a tenant within a time window.

        Args:
            tenant_id: Tenant identifier
            start_time: Start of time window
            end_time: End of time window

        Returns:
            List of processed query log entries
        """
        logger.info(
            f"Collecting query logs for tenant={tenant_id} "
            f"from {start_time} to {end_time}"
        )

        # In production, this would query Neo4j's query.log
        # For now, we'll create a mock implementation

        if not self.neo4j_client:
            logger.warning("No Neo4j client, returning mock data")
            return self._mock_query_logs(tenant_id)

        # Query to get logged queries from Neo4j
        # Note: Requires neo4j.conf to enable query logging
        query = """
        CALL dbms.listQueries() YIELD queryId, query, runtime, elapsedTime
        RETURN queryId, query, runtime, elapsedTime
        """

        try:
            results = []  # await self.neo4j_client.execute(query)

            processed_logs = []
            for row in results:
                processed = self._process_query_log(row, tenant_id)
                if processed:
                    processed_logs.append(processed)

            logger.info(f"Collected {len(processed_logs)} query logs")
            return processed_logs

        except Exception as e:
            logger.error(f"Error collecting query logs: {e}")
            return []

    def _process_query_log(
        self,
        log_entry: Dict[str, Any],
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single query log entry.

        Extracts:
        - Query pattern (normalized)
        - Entity types accessed
        - Relationship types traversed
        - Properties accessed
        - Execution metrics
        """
        query = log_entry.get("query", "")

        # Skip system queries
        if self._is_system_query(query):
            return None

        # Normalize query to identify patterns
        pattern = self._normalize_query(query)
        pattern_hash = self._hash_pattern(pattern)

        # Extract entity labels
        entity_labels = self._extract_entity_labels(query)

        # Extract relationship types
        relationship_types = self._extract_relationships(query)

        # Extract property names
        properties = self._extract_properties(query)

        return {
            "query_id": log_entry.get("queryId"),
            "original_query": query,
            "normalized_pattern": pattern,
            "pattern_hash": pattern_hash,
            "entity_labels": entity_labels,
            "relationship_types": relationship_types,
            "properties": properties,
            "execution_time_ms": log_entry.get("elapsedTime", 0),
            "tenant_id": tenant_id,
            "timestamp": datetime.utcnow()
        }

    def _normalize_query(self, query: str) -> str:
        """
        Normalize a Cypher query to identify patterns.

        Replaces:
        - Numeric literals with 'N'
        - String literals with 'S'
        - Lists with 'L'
        - Parameter names with 'P'
        """
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', query.strip())

        # Replace numeric literals
        normalized = re.sub(r'\b\d+\b', 'N', normalized)

        # Replace string literals
        normalized = re.sub(r"'[^']*'", 'S', normalized)
        normalized = re.sub(r'"[^"]*"', 'S', normalized)

        # Replace parameters
        normalized = re.sub(r'\$\w+', 'P', normalized)

        # Replace lists
        normalized = re.sub(r'\[[^\]]*\]', 'L', normalized)

        return normalized

    def _hash_pattern(self, pattern: str) -> str:
        """Generate a hash for a query pattern"""
        return hashlib.md5(pattern.encode()).hexdigest()

    def _is_system_query(self, query: str) -> bool:
        """Check if query is a system query (should be ignored)"""
        system_prefixes = [
            "CALL dbms.",
            "CALL db.",
            "SHOW",
            "CREATE CONSTRAINT",
            "CREATE INDEX",
            "DROP"
        ]
        return any(query.strip().upper().startswith(prefix) for prefix in system_prefixes)

    def _extract_entity_labels(self, query: str) -> List[str]:
        """Extract entity labels from Cypher query"""
        # Match patterns like (p:Property) or (o:Owner)
        pattern = r'\(\w*:(\w+)\)'
        matches = re.findall(pattern, query)
        return list(set(matches))  # Unique labels

    def _extract_relationships(self, query: str) -> List[str]:
        """Extract relationship types from Cypher query"""
        # Match patterns like -[:OWNED_BY]->
        pattern = r'-\[:(\w+)\]-'
        matches = re.findall(pattern, query)
        return list(set(matches))

    def _extract_properties(self, query: str) -> List[str]:
        """Extract property names from Cypher query"""
        # Match patterns like p.price, o.name
        pattern = r'\.(\w+)'
        matches = re.findall(pattern, query)

        # Filter out common keywords that aren't properties
        keywords = {'WHERE', 'AND', 'OR', 'NOT', 'RETURN', 'WITH', 'MATCH'}
        return list(set(m for m in matches if m.upper() not in keywords))

    def _mock_query_logs(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Generate mock query logs for testing"""
        return [
            {
                "query_id": "query-001",
                "original_query": "MATCH (p:Property) WHERE p.price < 500000 RETURN p",
                "normalized_pattern": "MATCH (p:Property) WHERE p.price < N RETURN p",
                "pattern_hash": "abc123",
                "entity_labels": ["Property"],
                "relationship_types": [],
                "properties": ["price"],
                "execution_time_ms": 45.2,
                "tenant_id": tenant_id,
                "timestamp": datetime.utcnow()
            },
            {
                "query_id": "query-002",
                "original_query": "MATCH (p:Property)-[:OWNED_BY]->(o:Owner) WHERE o.name = 'John' RETURN p, o",
                "normalized_pattern": "MATCH (p:Property)-[:OWNED_BY]->(o:Owner) WHERE o.name = S RETURN p, o",
                "pattern_hash": "def456",
                "entity_labels": ["Property", "Owner"],
                "relationship_types": ["OWNED_BY"],
                "properties": ["name"],
                "execution_time_ms": 68.5,
                "tenant_id": tenant_id,
                "timestamp": datetime.utcnow()
            }
        ]
