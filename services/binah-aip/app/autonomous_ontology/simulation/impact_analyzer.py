"""
Impact Analyzer

Analyzes the impact of proposed ontology changes by combining
sandbox testing results with risk assessment.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from ..models import (
    ImpactReport,
    CompatibilityResult,
    PerformanceResult,
    RiskLevel,
    Recommendation
)

logger = logging.getLogger(__name__)


class ImpactAnalyzer:
    """
    Analyzes impact of proposed ontology changes.

    Combines:
    - Query replay results (performance, compatibility)
    - Data migration requirements
    - Risk scoring
    - Recommendation for approval/rejection
    """

    def __init__(self):
        logger.info("ImpactAnalyzer initialized")

    async def analyze_impact(
        self,
        recommendation: Recommendation,
        replay_results: Dict[str, Any],
        breaking_changes: List[Dict[str, Any]],
        tenant_id: str
    ) -> ImpactReport:
        """
        Generate comprehensive impact analysis report.

        Args:
            recommendation: Recommendation being tested
            replay_results: Results from query replay
            breaking_changes: Detected breaking changes
            tenant_id: Tenant identifier

        Returns:
            Complete impact report with risk assessment
        """
        logger.info(f"Analyzing impact for recommendation {recommendation.id}")

        # Compatibility analysis
        compatibility = CompatibilityResult(
            breaking_changes=len(breaking_changes),
            failing_queries=[bc["query_id"] for bc in breaking_changes if bc["type"] == "query_failure"],
            affected_entities=self._extract_affected_entities(recommendation)
        )

        # Performance analysis
        summary = replay_results.get("summary", {})
        performance = PerformanceResult(
            queries_tested=replay_results.get("total_queries", 0),
            average_improvement=summary.get("average_change_percent", 0.0),
            queries_improved=summary.get("queries_improved", 0),
            queries_degraded=summary.get("queries_degraded", 0),
            outliers=self._find_performance_outliers(replay_results)
        )

        # Calculate risk score
        risk_score = self._calculate_risk_score(
            recommendation,
            compatibility,
            performance,
            breaking_changes
        )

        # Determine risk level
        risk_level = self._determine_risk_level(risk_score)

        # Make recommendation
        recommendation_action = self._make_recommendation(
            risk_score,
            compatibility,
            performance
        )

        # Create impact report
        report = ImpactReport(
            recommendation_id=recommendation.id,
            simulation_date=datetime.utcnow(),
            compatibility=compatibility,
            performance=performance,
            data_migration=recommendation.implementation.migration_strategy,
            risk_score=risk_score,
            risk_level=risk_level,
            recommendation_action=recommendation_action
        )

        logger.info(
            f"Impact analysis complete: "
            f"risk_score={risk_score:.1f}, "
            f"action={recommendation_action}"
        )

        return report

    def _extract_affected_entities(self, recommendation: Recommendation) -> List[str]:
        """Extract list of entities affected by recommendation"""
        # Parse from recommendation usage_metrics
        affected = []

        usage_metrics = recommendation.usage_metrics
        if "affected_entities" in usage_metrics:
            affected = usage_metrics["affected_entities"]
        elif "from_entity" in usage_metrics and "to_entity" in usage_metrics:
            affected = [usage_metrics["from_entity"], usage_metrics["to_entity"]]

        return affected

    def _find_performance_outliers(
        self,
        replay_results: Dict[str, Any],
        threshold_percent: float = 50.0
    ) -> List[Dict[str, Any]]:
        """
        Find queries with extreme performance changes.

        Args:
            replay_results: Query replay results
            threshold_percent: Threshold for outlier (>50% change)

        Returns:
            List of outlier queries
        """
        outliers = []

        for perf in replay_results.get("performance_changes", []):
            if abs(perf["change_percent"]) > threshold_percent:
                outliers.append({
                    "query_id": perf["query_id"],
                    "change_percent": perf["change_percent"],
                    "baseline_ms": perf["baseline_ms"],
                    "new_ms": perf["sandbox_ms"]
                })

        return outliers

    def _calculate_risk_score(
        self,
        recommendation: Recommendation,
        compatibility: CompatibilityResult,
        performance: PerformanceResult,
        breaking_changes: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate risk score (0-100).

        Factors:
        - Breaking changes (critical)
        - Performance degradation
        - Number of affected entities
        - Migration complexity
        - Recommendation priority

        Score ranges:
        - 0-20: Safe (auto-approve)
        - 20-40: Low risk (single reviewer)
        - 40-60: Medium risk (multiple reviewers)
        - 60-80: High risk (architect + reviewers)
        - 80-100: Critical risk (special approval)
        """
        score = 0.0

        # Breaking changes (most critical)
        if compatibility.breaking_changes > 0:
            # Critical failures get high score
            critical_failures = sum(
                1 for bc in breaking_changes
                if bc.get("severity") == "critical"
            )
            score += critical_failures * 25  # Up to 100 if 4+ critical failures

            # Other breaking changes
            other_failures = compatibility.breaking_changes - critical_failures
            score += other_failures * 10

        # Performance degradation
        if performance.average_improvement < 0:  # Negative = slower
            # Moderate penalty for performance loss
            score += abs(performance.average_improvement) / 10

        # Queries degraded
        if performance.queries_tested > 0:
            degradation_rate = performance.queries_degraded / performance.queries_tested
            score += degradation_rate * 20

        # Migration complexity
        if recommendation.implementation.migration_strategy.required:
            score += 15  # Migration adds risk

        # Breaking changes in implementation
        breaking_count = len(recommendation.implementation.breaking_changes)
        score += breaking_count * 5

        # Number of affected entities
        affected_count = len(compatibility.affected_entities)
        if affected_count > 3:
            score += 10

        # Cap at 100
        return min(score, 100.0)

    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Convert numeric risk score to risk level"""
        if risk_score < 20:
            return RiskLevel.SAFE
        elif risk_score < 40:
            return RiskLevel.LOW
        elif risk_score < 60:
            return RiskLevel.MEDIUM
        elif risk_score < 80:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _make_recommendation(
        self,
        risk_score: float,
        compatibility: CompatibilityResult,
        performance: PerformanceResult
    ) -> str:
        """
        Make recommendation on whether to approve or reject.

        Args:
            risk_score: Calculated risk score
            compatibility: Compatibility test results
            performance: Performance test results

        Returns:
            "approve", "reject", or "needs_review"
        """
        # Auto-reject if critical breaking changes
        if compatibility.breaking_changes > 0:
            for failing_query in compatibility.failing_queries:
                return "reject"

        # Auto-reject if severe performance degradation
        if performance.average_improvement < -50:  # >50% slower
            return "reject"

        # Auto-approve if low risk and performance improvement
        if risk_score < 20 and performance.average_improvement > 0:
            return "approve"

        # Otherwise needs human review
        return "needs_review"

    async def generate_impact_summary(
        self,
        report: ImpactReport
    ) -> str:
        """
        Generate human-readable summary of impact analysis.

        Args:
            report: Impact report

        Returns:
            Formatted summary text
        """
        summary_lines = [
            f"## Impact Analysis Summary",
            f"",
            f"**Risk Score:** {report.risk_score:.1f}/100 ({report.risk_level.value})",
            f"**Recommendation:** {report.recommendation_action}",
            f"",
            f"### Compatibility",
            f"- Breaking Changes: {report.compatibility.breaking_changes}",
            f"- Failing Queries: {len(report.compatibility.failing_queries)}",
            f"- Affected Entities: {len(report.compatibility.affected_entities)}",
            f"",
            f"### Performance",
            f"- Queries Tested: {report.performance.queries_tested}",
            f"- Average Change: {report.performance.average_improvement:+.1f}%",
            f"- Improved: {report.performance.queries_improved}",
            f"- Degraded: {report.performance.queries_degraded}",
            f"- Performance Outliers: {len(report.performance.outliers)}",
            f"",
            f"### Data Migration",
            f"- Required: {'Yes' if report.data_migration.required else 'No'}",
        ]

        if report.data_migration.required:
            summary_lines.extend([
                f"- Affected Records: {report.data_migration.affected_records:,}",
                f"- Estimated Duration: {report.data_migration.estimated_duration}",
                f"- Strategy: {report.data_migration.backfill_strategy}",
            ])

        return "\n".join(summary_lines)
