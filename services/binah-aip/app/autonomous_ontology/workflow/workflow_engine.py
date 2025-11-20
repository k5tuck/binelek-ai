"""
Workflow Engine

Orchestrates the approval workflow for ontology changes.
Implements risk-based routing and tracks approval status.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ..models import (
    WorkflowState,
    Approval,
    ApprovalStatus,
    ImpactReport,
    Recommendation,
    RiskLevel
)

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Manages approval workflows for ontology changes.

    Risk-based routing:
    - Safe (risk < 20): Auto-approve
    - Low (20-40): Single reviewer
    - Medium (40-60): Multiple reviewers
    - High (60-80): Architect + domain expert
    - Critical (>80): Special approval required
    """

    def __init__(self, notification_service=None):
        self.notification_service = notification_service
        self.active_workflows: Dict[str, WorkflowState] = {}
        logger.info("WorkflowEngine initialized")

    async def start_workflow(
        self,
        recommendation: Recommendation,
        impact_report: ImpactReport,
        tenant_id: str
    ) -> WorkflowState:
        """
        Start approval workflow for a recommendation.

        Args:
            recommendation: Recommendation to approve
            impact_report: Impact analysis report
            tenant_id: Tenant identifier

        Returns:
            WorkflowState tracking the approval process
        """
        logger.info(
            f"Starting workflow for recommendation {recommendation.id}, "
            f"risk={impact_report.risk_level.value}"
        )

        # Create workflow state
        workflow = WorkflowState(
            recommendation_id=recommendation.id,
            current_state="review",
            approvals=[],
            required_approvals=self._determine_required_approvals(impact_report.risk_level),
            scheduled_execution=None
        )

        # Track workflow
        self.active_workflows[recommendation.id] = workflow

        # Route based on risk level
        if impact_report.risk_level == RiskLevel.SAFE:
            # Auto-approve
            await self._auto_approve(workflow, recommendation, impact_report)

        elif impact_report.risk_level == RiskLevel.LOW:
            # Single reviewer
            await self._request_single_approval(workflow, recommendation, impact_report, tenant_id)

        elif impact_report.risk_level == RiskLevel.MEDIUM:
            # Multiple reviewers
            await self._request_multiple_approvals(workflow, recommendation, impact_report, tenant_id)

        elif impact_report.risk_level == RiskLevel.HIGH:
            # Architect + reviewers
            await self._request_architect_approval(workflow, recommendation, impact_report, tenant_id)

        else:  # CRITICAL
            # Special approval process
            await self._request_special_approval(workflow, recommendation, impact_report, tenant_id)

        logger.info(
            f"Workflow started for {recommendation.id}: "
            f"{workflow.required_approvals} approvals required"
        )

        return workflow

    def _determine_required_approvals(self, risk_level: RiskLevel) -> int:
        """Determine number of approvals needed based on risk"""
        approval_map = {
            RiskLevel.SAFE: 0,      # Auto-approve
            RiskLevel.LOW: 1,       # Single reviewer
            RiskLevel.MEDIUM: 2,    # Two reviewers
            RiskLevel.HIGH: 3,      # Three reviewers including architect
            RiskLevel.CRITICAL: 4   # Four reviewers including architect + domain expert
        }
        return approval_map.get(risk_level, 2)

    async def _auto_approve(
        self,
        workflow: WorkflowState,
        recommendation: Recommendation,
        impact_report: ImpactReport
    ):
        """Auto-approve low-risk changes"""
        logger.info(f"Auto-approving recommendation {recommendation.id}")

        approval = Approval(
            approver_id="system",
            approver_role="auto-approval",
            status=ApprovalStatus.APPROVED,
            comments="Auto-approved: Low risk, no breaking changes",
            approved_at=datetime.utcnow()
        )

        workflow.approvals.append(approval)
        workflow.current_state = "approved"
        workflow.updated_at = datetime.utcnow()

        # Notify about auto-approval
        if self.notification_service:
            await self.notification_service.send_notification(
                notification_type="auto_approval",
                recommendation=recommendation,
                impact_report=impact_report
            )

    async def _request_single_approval(
        self,
        workflow: WorkflowState,
        recommendation: Recommendation,
        impact_report: ImpactReport,
        tenant_id: str
    ):
        """Request approval from single reviewer"""
        logger.info(f"Requesting single approval for {recommendation.id}")

        # Send notification to ontology admin
        if self.notification_service:
            await self.notification_service.send_approval_request(
                reviewers=["ontology-admin"],
                recommendation=recommendation,
                impact_report=impact_report,
                tenant_id=tenant_id
            )

    async def _request_multiple_approvals(
        self,
        workflow: WorkflowState,
        recommendation: Recommendation,
        impact_report: ImpactReport,
        tenant_id: str
    ):
        """Request approvals from multiple reviewers"""
        logger.info(f"Requesting multiple approvals for {recommendation.id}")

        reviewers = ["ontology-admin", "lead-engineer"]

        if self.notification_service:
            await self.notification_service.send_approval_request(
                reviewers=reviewers,
                recommendation=recommendation,
                impact_report=impact_report,
                tenant_id=tenant_id
            )

    async def _request_architect_approval(
        self,
        workflow: WorkflowState,
        recommendation: Recommendation,
        impact_report: ImpactReport,
        tenant_id: str
    ):
        """Request approvals including architect"""
        logger.info(f"Requesting architect approval for {recommendation.id}")

        reviewers = ["ontology-admin", "lead-engineer", "lead-architect"]

        if self.notification_service:
            await self.notification_service.send_approval_request(
                reviewers=reviewers,
                recommendation=recommendation,
                impact_report=impact_report,
                tenant_id=tenant_id,
                urgent=True
            )

    async def _request_special_approval(
        self,
        workflow: WorkflowState,
        recommendation: Recommendation,
        impact_report: ImpactReport,
        tenant_id: str
    ):
        """Request special approval for critical changes"""
        logger.info(f"Requesting special approval for {recommendation.id}")

        reviewers = ["ontology-admin", "lead-architect", "domain-expert", "cto"]

        if self.notification_service:
            await self.notification_service.send_approval_request(
                reviewers=reviewers,
                recommendation=recommendation,
                impact_report=impact_report,
                tenant_id=tenant_id,
                urgent=True,
                requires_meeting=True
            )

    async def submit_approval(
        self,
        recommendation_id: str,
        approver_id: str,
        approver_role: str,
        status: ApprovalStatus,
        comments: str = ""
    ) -> WorkflowState:
        """
        Submit an approval decision.

        Args:
            recommendation_id: Recommendation being approved
            approver_id: ID of approver
            approver_role: Role of approver
            status: Approval decision
            comments: Optional comments

        Returns:
            Updated workflow state
        """
        logger.info(
            f"Approval submitted for {recommendation_id} by {approver_id}: {status.value}"
        )

        workflow = self.active_workflows.get(recommendation_id)
        if not workflow:
            raise ValueError(f"Workflow not found for {recommendation_id}")

        # Create approval record
        approval = Approval(
            approver_id=approver_id,
            approver_role=approver_role,
            status=status,
            comments=comments,
            approved_at=datetime.utcnow()
        )

        workflow.approvals.append(approval)
        workflow.updated_at = datetime.utcnow()

        # Check if enough approvals
        approved_count = sum(1 for a in workflow.approvals if a.status == ApprovalStatus.APPROVED)
        rejected_count = sum(1 for a in workflow.approvals if a.status == ApprovalStatus.REJECTED)

        if rejected_count > 0:
            workflow.current_state = "rejected"
        elif approved_count >= workflow.required_approvals:
            workflow.current_state = "approved"
            workflow.scheduled_execution = datetime.utcnow() + timedelta(hours=1)  # Schedule for 1 hour from now

        return workflow

    def get_workflow_status(self, recommendation_id: str) -> Optional[WorkflowState]:
        """Get current workflow status"""
        return self.active_workflows.get(recommendation_id)

    def list_pending_approvals(self, approver_id: Optional[str] = None) -> List[WorkflowState]:
        """List workflows pending approval"""
        pending = [
            w for w in self.active_workflows.values()
            if w.current_state == "review"
        ]

        # Filter by approver if specified
        if approver_id:
            # In production, filter by approver role/permissions
            pass

        return pending
