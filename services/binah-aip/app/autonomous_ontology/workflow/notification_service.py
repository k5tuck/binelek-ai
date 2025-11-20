"""
Notification Service

Sends notifications for approval requests, status updates, etc.
Supports email, Slack, and webhooks.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Sends notifications for workflow events.

    Notification channels:
    - Email
    - Slack
    - Webhooks
    - In-app notifications
    """

    def __init__(self, email_client=None, slack_client=None):
        self.email_client = email_client
        self.slack_client = slack_client
        logger.info("NotificationService initialized")

    async def send_approval_request(
        self,
        reviewers: List[str],
        recommendation: Any,
        impact_report: Any,
        tenant_id: str,
        urgent: bool = False,
        requires_meeting: bool = False
    ):
        """Send approval request notifications"""
        logger.info(f"Sending approval request to {len(reviewers)} reviewers")

        message = self._format_approval_request(
            recommendation,
            impact_report,
            urgent,
            requires_meeting
        )

        # Send via multiple channels
        await self._send_slack(reviewers, message, urgent)
        await self._send_email(reviewers, message)

    async def send_notification(
        self,
        notification_type: str,
        recommendation: Any,
        impact_report: Any = None
    ):
        """Send general notification"""
        logger.info(f"Sending {notification_type} notification")

        # Implementation would send actual notifications
        # For now, just log
        logger.info(f"Notification: {notification_type} for {recommendation.id}")

    def _format_approval_request(
        self,
        recommendation: Any,
        impact_report: Any,
        urgent: bool,
        requires_meeting: bool
    ) -> str:
        """Format approval request message"""
        urgency = "🚨 URGENT" if urgent else ""
        meeting = " (Meeting Required)" if requires_meeting else ""

        return f"""
{urgency} Ontology Change Approval Requested{meeting}

**Recommendation:** {recommendation.title}
**Priority:** {recommendation.priority.value}
**Risk Score:** {impact_report.risk_score:.1f}/100 ({impact_report.risk_level.value})
**Action:** {impact_report.recommendation_action}

**Impact:**
- Breaking Changes: {impact_report.compatibility.breaking_changes}
- Performance Change: {impact_report.performance.average_improvement:+.1f}%
- Queries Tested: {impact_report.performance.queries_tested}

**Review Dashboard:** [View Details]

Please review and approve/reject within 48 hours.
        """.strip()

    async def _send_slack(self, reviewers: List[str], message: str, urgent: bool):
        """Send Slack notifications"""
        if not self.slack_client:
            logger.debug("Slack client not configured, skipping")
            return

        # In production: send to Slack
        logger.info(f"Would send Slack to {reviewers}: {message[:100]}...")

    async def _send_email(self, reviewers: List[str], message: str):
        """Send email notifications"""
        if not self.email_client:
            logger.debug("Email client not configured, skipping")
            return

        # In production: send emails
        logger.info(f"Would send email to {reviewers}: {message[:100]}...")
