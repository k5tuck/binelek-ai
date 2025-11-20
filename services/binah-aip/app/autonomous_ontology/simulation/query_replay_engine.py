"""
Query Replay Engine

Replays historical queries against sandbox environment to test
performance and compatibility of proposed ontology changes.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time
from collections import defaultdict

logger = logging.getLogger(__name__)


class QueryReplayEngine:
    """
    Replays historical queries to test ontology changes.

    Key responsibilities:
    - Load historical query logs
    - Replay queries against sandbox
    - Measure performance (before/after)
    - Detect breaking changes (queries that fail)
    - Generate performance comparison report
    """

    def __init__(self, neo4j_client=None):
        self.neo4j_client = neo4j_client
        logger.info("QueryReplayEngine initialized")

    async def replay_queries(
        self,
        sandbox_uri: str,
        sandbox_credentials: Dict[str, str],
        query_log: List[Dict[str, Any]],
        baseline_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Replay historical queries against sandbox.

        Args:
            sandbox_uri: Sandbox Neo4j URI
            sandbox_credentials: Username/password
            query_log: Historical queries to replay
            baseline_metrics: Original performance metrics

        Returns:
            Performance comparison results
        """
        logger.info(f"Replaying {len(query_log)} queries against sandbox")

        results = {
            "total_queries": len(query_log),
            "successful": 0,
            "failed": 0,
            "performance_changes": [],
            "errors": [],
            "summary": {}
        }

        # Replay each query
        for query_entry in query_log:
            try:
                result = await self._replay_single_query(
                    sandbox_uri,
                    sandbox_credentials,
                    query_entry,
                    baseline_metrics
                )

                if result["success"]:
                    results["successful"] += 1
                    results["performance_changes"].append(result["performance"])
                else:
                    results["failed"] += 1
                    results["errors"].append(result["error"])

            except Exception as e:
                logger.error(f"Error replaying query: {e}")
                results["failed"] += 1
                results["errors"].append({
                    "query_id": query_entry.get("query_id"),
                    "error": str(e)
                })

        # Calculate summary statistics
        results["summary"] = self._calculate_summary(results)

        logger.info(
            f"Replay complete: {results['successful']} successful, "
            f"{results['failed']} failed"
        )

        return results

    async def _replay_single_query(
        self,
        sandbox_uri: str,
        credentials: Dict[str, str],
        query_entry: Dict[str, Any],
        baseline_metrics: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Replay a single query and measure performance"""

        query_id = query_entry.get("query_id", "unknown")
        cypher = query_entry.get("cypher", "")
        params = query_entry.get("params", {})
        baseline_duration = query_entry.get("duration_ms", 0)

        try:
            # Execute query and measure time
            start_time = time.time()

            # In production, execute against sandbox Neo4j
            # For now, simulate execution
            await asyncio.sleep(0.01)  # Simulate query execution
            result = {"records": [], "count": 0}

            duration_ms = (time.time() - start_time) * 1000

            # Calculate performance change
            perf_change = 0.0
            if baseline_duration > 0:
                perf_change = ((duration_ms - baseline_duration) / baseline_duration) * 100

            return {
                "success": True,
                "query_id": query_id,
                "performance": {
                    "query_id": query_id,
                    "baseline_ms": baseline_duration,
                    "sandbox_ms": duration_ms,
                    "change_percent": perf_change,
                    "improved": perf_change < 0
                }
            }

        except Exception as e:
            logger.error(f"Query {query_id} failed: {e}")
            return {
                "success": False,
                "query_id": query_id,
                "error": {
                    "query_id": query_id,
                    "error": str(e),
                    "breaking_change": True
                }
            }

    def _calculate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary statistics from replay results"""

        perf_changes = results.get("performance_changes", [])

        if not perf_changes:
            return {
                "average_change_percent": 0.0,
                "queries_improved": 0,
                "queries_degraded": 0,
                "max_improvement_percent": 0.0,
                "max_degradation_percent": 0.0
            }

        # Calculate statistics
        change_percents = [p["change_percent"] for p in perf_changes]
        improved_count = sum(1 for p in perf_changes if p["improved"])
        degraded_count = len(perf_changes) - improved_count

        return {
            "average_change_percent": sum(change_percents) / len(change_percents),
            "queries_improved": improved_count,
            "queries_degraded": degraded_count,
            "max_improvement_percent": min(change_percents),
            "max_degradation_percent": max(change_percents),
            "median_change_percent": sorted(change_percents)[len(change_percents) // 2]
        }

    async def load_query_log(
        self,
        tenant_id: str,
        time_window_days: int = 30,
        max_queries: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Load historical query log for replay.

        Args:
            tenant_id: Tenant identifier
            time_window_days: How far back to look
            max_queries: Maximum queries to load

        Returns:
            List of query entries
        """
        logger.info(
            f"Loading query log for tenant {tenant_id}, "
            f"window={time_window_days} days, max={max_queries}"
        )

        # In production, query from database
        # For now, return mock data
        return self._mock_query_log(tenant_id, max_queries)

    def _mock_query_log(self, tenant_id: str, count: int) -> List[Dict[str, Any]]:
        """Generate mock query log for testing"""
        return [
            {
                "query_id": f"query-{i}",
                "cypher": "MATCH (p:Property) WHERE p.price < $price RETURN p",
                "params": {"price": 500000},
                "duration_ms": 45.2 + (i % 50),
                "tenant_id": tenant_id,
                "timestamp": datetime.utcnow() - timedelta(days=i % 30)
            }
            for i in range(min(count, 100))
        ]

    async def detect_breaking_changes(
        self,
        replay_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analyze replay results to identify breaking changes.

        Breaking changes:
        - Queries that fail after changes
        - Queries with significantly different results
        - Queries with severe performance degradation (>2x slower)

        Args:
            replay_results: Results from replay_queries()

        Returns:
            List of breaking changes detected
        """
        breaking_changes = []

        # Failed queries are breaking changes
        for error in replay_results.get("errors", []):
            breaking_changes.append({
                "type": "query_failure",
                "severity": "critical",
                "query_id": error.get("query_id"),
                "description": f"Query failed: {error.get('error')}",
                "recommendation": "Review query compatibility with ontology changes"
            })

        # Severe performance degradation
        for perf in replay_results.get("performance_changes", []):
            if perf["change_percent"] > 100:  # More than 2x slower
                breaking_changes.append({
                    "type": "performance_degradation",
                    "severity": "high",
                    "query_id": perf["query_id"],
                    "description": f"Query {perf['change_percent']:.1f}% slower",
                    "baseline_ms": perf["baseline_ms"],
                    "new_ms": perf["sandbox_ms"],
                    "recommendation": "Consider adding indexes or optimizing relationship paths"
                })

        logger.info(f"Detected {len(breaking_changes)} breaking changes")
        return breaking_changes
