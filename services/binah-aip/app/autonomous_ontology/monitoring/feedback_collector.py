"""
Feedback Collector

Collects post-deployment feedback to improve future recommendations.
Monitors deployments for 7 days to gather actual outcomes.
"""

import logging
from typing import Dict, Any
from datetime import datetime, timedelta

from ..models import FeedbackData, Deployment, Recommendation

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """
    Collects feedback from deployed ontology changes.

    Tracks:
    - Actual performance improvement vs predicted
    - Error rate changes
    - User satisfaction
    - Missed issues
    - Unexpected benefits
    """

    def __init__(self, metrics_client=None):
        self.metrics_client = metrics_client
        logger.info("FeedbackCollector initialized")

    async def collect_deployment_feedback(
        self,
        deployment: Deployment,
        recommendation: Recommendation,
        monitoring_days: int = 7
    ) -> FeedbackData:
        """
        Collect post-deployment feedback.

        Args:
            deployment: Completed deployment
            recommendation: Original recommendation
            monitoring_days: Days to monitor (default: 7)

        Returns:
            FeedbackData for ML training
        """
        logger.info(
            f"Collecting feedback for deployment {deployment.recommendation_id}, "
            f"monitoring for {monitoring_days} days"
        )

        # Calculate predicted vs actual impact
        predicted_impact = {
            "performance_improvement": recommendation.predicted_improvement,
            "risk_score": recommendation.risk if hasattr(recommendation, 'risk_score') else 0.0
        }

        actual_impact = await self._calculate_actual_impact(deployment, monitoring_days)

        # Calculate prediction accuracy
        accuracy = self._calculate_prediction_accuracy(predicted_impact, actual_impact)

        # Identify missed issues
        missed_issues = await self._identify_missed_issues(deployment)

        # Identify unexpected benefits
        unexpected_benefits = await self._identify_unexpected_benefits(deployment)

        # Collect user feedback
        user_satisfaction = await self._collect_user_satisfaction(deployment)

        feedback = FeedbackData(
            recommendation_id=recommendation.id,
            deployment_date=deployment.completed_at or datetime.utcnow(),
            outcome=self._determine_outcome(deployment),
            predicted_impact=predicted_impact,
            actual_impact=actual_impact,
            prediction_accuracy=accuracy,
            missed_issues=missed_issues,
            unexpected_benefits=unexpected_benefits,
            user_satisfaction=user_satisfaction,
            user_comments=""
        )

        # Store feedback for ML training
        await self._store_feedback(feedback)

        logger.info(
            f"Feedback collected: "
            f"accuracy={accuracy:.1%}, "
            f"outcome={feedback.outcome}"
        )

        return feedback

    async def _calculate_actual_impact(
        self,
        deployment: Deployment,
        monitoring_days: int
    ) -> Dict[str, Any]:
        """Calculate actual impact from deployment metrics"""

        if not deployment.metrics:
            return {
                "performance_improvement": 0.0,
                "error_rate_change": 0.0,
                "user_satisfaction": 0.0
            }

        # Analyze deployment metrics
        baseline_metrics = deployment.metrics[0]  # First measurement
        current_metrics = deployment.metrics[-1]  # Latest measurement

        # Calculate changes
        latency_improvement = (
            (baseline_metrics.p99_latency - current_metrics.p99_latency) /
            baseline_metrics.p99_latency * 100
        ) if baseline_metrics.p99_latency > 0 else 0.0

        error_rate_change = (
            current_metrics.error_rate - baseline_metrics.error_rate
        )

        return {
            "performance_improvement": latency_improvement,
            "error_rate_change": error_rate_change,
            "throughput_change": current_metrics.throughput - baseline_metrics.throughput,
            "rollback_required": deployment.status.value == "rolled_back"
        }

    def _calculate_prediction_accuracy(
        self,
        predicted: Dict[str, Any],
        actual: Dict[str, Any]
    ) -> float:
        """
        Calculate how accurate the prediction was.

        Returns value from 0.0 to 1.0
        """
        predicted_perf = predicted.get("performance_improvement", 0.0)
        actual_perf = actual.get("performance_improvement", 0.0)

        # If both predicted improvement and it happened
        if predicted_perf > 0 and actual_perf > 0:
            # Calculate percentage match
            accuracy = min(actual_perf, predicted_perf) / max(actual_perf, predicted_perf)
            return accuracy

        # If predicted correctly there would be no improvement
        if predicted_perf == 0 and abs(actual_perf) < 5:
            return 1.0

        # If predicted improvement but got degradation (or vice versa)
        if (predicted_perf > 0 and actual_perf < 0) or (predicted_perf < 0 and actual_perf > 0):
            return 0.0

        return 0.5  # Uncertain

    async def _identify_missed_issues(self, deployment: Deployment) -> list:
        """Identify issues that weren't caught in simulation"""
        missed_issues = []

        # Check if rollback was required
        if deployment.status.value == "rolled_back":
            missed_issues.append({
                "issue": "deployment_failure",
                "description": deployment.rollback_reason or "Unknown failure",
                "severity": "high"
            })

        # Check deployment metrics for unexpected problems
        for metric in deployment.metrics:
            if metric.error_rate > 0.05:  # >5% error rate
                missed_issues.append({
                    "issue": "high_error_rate",
                    "description": f"Error rate: {metric.error_rate:.1%}",
                    "severity": "medium"
                })

        return missed_issues

    async def _identify_unexpected_benefits(self, deployment: Deployment) -> list:
        """Identify unexpected positive outcomes"""
        benefits = []

        # Check if performance improved more than expected
        if deployment.metrics:
            latest = deployment.metrics[-1]
            if latest.error_rate < 0.01:  # Very low error rate
                benefits.append({
                    "benefit": "excellent_reliability",
                    "description": f"Error rate below 1%: {latest.error_rate:.2%}"
                })

            if latest.throughput > 1500:  # High throughput
                benefits.append({
                    "benefit": "high_throughput",
                    "description": f"Throughput: {latest.throughput:.0f} req/s"
                })

        return benefits

    async def _collect_user_satisfaction(self, deployment: Deployment) -> float:
        """Collect user satisfaction score (0-10)"""
        # In production: survey users or analyze metrics
        # For now, infer from deployment success
        if deployment.status.value == "completed":
            return 8.0
        elif deployment.status.value == "rolled_back":
            return 3.0
        else:
            return 5.0

    def _determine_outcome(self, deployment: Deployment) -> str:
        """Determine deployment outcome"""
        if deployment.status.value == "completed":
            return "success"
        elif deployment.status.value == "rolled_back":
            return "rolled_back"
        else:
            return "reverted"

    async def _store_feedback(self, feedback: FeedbackData):
        """Store feedback in database for ML training"""
        logger.info(f"Storing feedback for {feedback.recommendation_id}")
        # In production: store in PostgreSQL or similar
