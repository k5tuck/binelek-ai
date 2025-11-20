"""
Metrics Aggregator

Aggregates collected metrics from various sources and provides
aggregated views for the AI recommendation engine.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

from ..models import UsageMetrics

logger = logging.getLogger(__name__)


class MetricsAggregator:
    """
    Aggregates usage metrics for analysis and recommendation generation.

    Provides aggregated views like:
    - Most frequently accessed entities
    - Slowest queries
    - Under-utilized entities
    - Frequently co-accessed entities (for relationship suggestions)
    - Properties with high null rates
    """

    def __init__(self, timescaledb_client=None):
        self.timescaledb_client = timescaledb_client
        logger.info("MetricsAggregator initialized")

    async def aggregate_metrics(
        self,
        metrics: UsageMetrics
    ) -> Dict[str, Any]:
        """
        Aggregate usage metrics into meaningful insights.

        Args:
            metrics: Raw usage metrics

        Returns:
            Dictionary of aggregated insights
        """
        logger.info(f"Aggregating metrics for tenant {metrics.tenant_id}")

        aggregations = {
            "summary": self._summarize_metrics(metrics),
            "top_entities": self._get_top_entities(metrics),
            "slow_queries": self._get_slow_queries(metrics),
            "underutilized_entities": self._get_underutilized_entities(metrics),
            "coaccessed_entities": self._get_coaccessed_entities(metrics),
            "data_quality_issues": self._get_data_quality_issues(metrics),
            "performance_issues": self._get_performance_issues(metrics)
        }

        return aggregations

    def _summarize_metrics(self, metrics: UsageMetrics) -> Dict[str, Any]:
        """Generate high-level summary"""
        return {
            "total_queries": metrics.total_queries,
            "unique_entities_accessed": metrics.unique_entities_accessed,
            "time_window_days": (metrics.time_window_end - metrics.time_window_start).days,
            "queries_per_day": metrics.total_queries / max(1, (metrics.time_window_end - metrics.time_window_start).days),
            "total_entity_types": len(metrics.entity_access),
            "total_relationship_types": len(set(rt.relationship_type for rt in metrics.relationship_traversals)),
            "total_properties_accessed": len(metrics.property_access)
        }

    def _get_top_entities(
        self,
        metrics: UsageMetrics,
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """Get most frequently accessed entities"""
        sorted_entities = sorted(
            metrics.entity_access,
            key=lambda x: x.read_count + x.write_count,
            reverse=True
        )

        return [
            {
                "entity_type": ea.entity_type,
                "total_access": ea.read_count + ea.write_count,
                "read_count": ea.read_count,
                "write_count": ea.write_count,
                "avg_response_time": ea.avg_response_time
            }
            for ea in sorted_entities[:top_n]
        ]

    def _get_slow_queries(
        self,
        metrics: UsageMetrics,
        threshold_ms: float = 1000.0,
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """Get slowest query patterns"""
        slow_queries = [
            qp for qp in metrics.query_patterns
            if qp.avg_duration > threshold_ms
        ]

        sorted_slow = sorted(
            slow_queries,
            key=lambda x: x.avg_duration,
            reverse=True
        )

        return [
            {
                "pattern": qp.cypher_pattern,
                "avg_duration_ms": qp.avg_duration,
                "execution_count": qp.execution_count,
                "failure_rate": qp.failure_rate
            }
            for qp in sorted_slow[:top_n]
        ]

    def _get_underutilized_entities(
        self,
        metrics: UsageMetrics,
        threshold_access: int = 10
    ) -> List[Dict[str, Any]]:
        """Find entities that are rarely accessed (candidates for deprecation)"""
        underutilized = [
            ea for ea in metrics.entity_access
            if (ea.read_count + ea.write_count) < threshold_access
        ]

        return [
            {
                "entity_type": ea.entity_type,
                "total_access": ea.read_count + ea.write_count,
                "last_accessed": ea.last_accessed.isoformat()
            }
            for ea in underutilized
        ]

    def _get_coaccessed_entities(
        self,
        metrics: UsageMetrics,
        min_frequency: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Find entities frequently accessed together.

        This is key for suggesting new direct relationships!
        Example: If queries often go Property → Owner → Transaction,
        suggest adding Property → Transaction relationship.
        """
        # Build co-access matrix from relationship traversals
        coaccessed = []

        for rt in metrics.relationship_traversals:
            if rt.frequency >= min_frequency and rt.avg_depth > 1.0:
                coaccessed.append({
                    "from_entity": rt.from_entity,
                    "to_entity": rt.to_entity,
                    "via_relationship": rt.relationship_type,
                    "frequency": rt.frequency,
                    "avg_hops": rt.avg_depth,
                    "suggestion": f"Consider adding direct {rt.from_entity} → {rt.to_entity} relationship"
                })

        return sorted(coaccessed, key=lambda x: x["frequency"], reverse=True)

    def _get_data_quality_issues(
        self,
        metrics: UsageMetrics,
        null_rate_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Identify data quality issues.

        High null rates indicate:
        - Field should be optional
        - Field should have a default value
        - Data collection process needs improvement
        """
        issues = []

        for pa in metrics.property_access:
            if pa.null_rate > null_rate_threshold:
                issues.append({
                    "entity_type": pa.entity_type,
                    "property_name": pa.property_name,
                    "null_rate": pa.null_rate,
                    "access_count": pa.access_count,
                    "issue_type": "high_null_rate",
                    "recommendation": (
                        f"Property '{pa.property_name}' has {pa.null_rate:.1%} null rate. "
                        f"Consider making it optional or adding a default value."
                    )
                })

        return issues

    def _get_performance_issues(
        self,
        metrics: UsageMetrics,
        response_time_threshold_ms: float = 500.0
    ) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        issues = []

        # Slow entity access
        for ea in metrics.entity_access:
            if ea.avg_response_time > response_time_threshold_ms:
                issues.append({
                    "type": "slow_entity_access",
                    "entity_type": ea.entity_type,
                    "avg_response_time_ms": ea.avg_response_time,
                    "access_frequency": ea.read_count + ea.write_count,
                    "recommendation": f"Consider adding indexes for {ea.entity_type}"
                })

        # Slow relationship traversals
        for rt in metrics.relationship_traversals:
            if rt.avg_response_time > response_time_threshold_ms:
                issues.append({
                    "type": "slow_relationship_traversal",
                    "relationship": rt.relationship_type,
                    "from_entity": rt.from_entity,
                    "to_entity": rt.to_entity,
                    "avg_response_time_ms": rt.avg_response_time,
                    "frequency": rt.frequency,
                    "recommendation": (
                        f"Slow traversal of {rt.relationship_type}. "
                        f"Consider optimizing or adding computed fields."
                    )
                })

        return sorted(issues, key=lambda x: x.get("avg_response_time_ms", 0), reverse=True)
