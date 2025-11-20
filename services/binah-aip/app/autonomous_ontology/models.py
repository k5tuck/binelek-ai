"""
Data models for autonomous ontology refactoring system
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum


class QueryType(str, Enum):
    """Types of queries tracked in the system"""
    ENTITY_READ = "entity_read"
    ENTITY_WRITE = "entity_write"
    RELATIONSHIP_TRAVERSAL = "relationship_traversal"
    PROPERTY_ACCESS = "property_access"
    AGGREGATION = "aggregation"
    SEARCH = "search"


class RecommendationType(str, Enum):
    """Types of ontology refactoring recommendations"""
    ENTITY_CONSOLIDATION = "entity_consolidation"
    NEW_RELATIONSHIP = "new_relationship"
    COMPUTED_FIELD = "computed_field"
    INDEX_OPTIMIZATION = "index"
    VALIDATION_RULE = "validation"
    DEPRECATE_ENTITY = "deprecate_entity"
    SPLIT_ENTITY = "split_entity"


class Priority(str, Enum):
    """Priority levels for recommendations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(str, Enum):
    """Risk levels for proposed changes"""
    SAFE = "safe"           # < 20: Auto-approve
    LOW = "low"             # 20-40: Single reviewer
    MEDIUM = "medium"       # 40-60: Multiple reviewers
    HIGH = "high"           # 60-80: Architect + reviewers
    CRITICAL = "critical"   # > 80: Special approval required


# ============================================================================
# PHASE 1: Usage Analytics Models
# ============================================================================

class EntityAccessMetrics(BaseModel):
    """Metrics for entity access patterns"""
    entity_type: str
    read_count: int = 0
    write_count: int = 0
    avg_response_time: float = 0.0
    last_accessed: datetime
    tenant_id: str


class RelationshipTraversalMetrics(BaseModel):
    """Metrics for relationship traversal patterns"""
    relationship_type: str
    from_entity: str
    to_entity: str
    frequency: int = 0
    avg_depth: float = 0.0
    avg_response_time: float = 0.0
    tenant_id: str


class PropertyAccessMetrics(BaseModel):
    """Metrics for property access patterns"""
    entity_type: str
    property_name: str
    access_count: int = 0
    null_rate: float = 0.0
    unique_values: int = 0
    tenant_id: str


class QueryPattern(BaseModel):
    """Tracked query patterns"""
    pattern_hash: str
    cypher_pattern: str
    execution_count: int = 0
    avg_duration: float = 0.0
    failure_rate: float = 0.0
    last_executed: datetime
    tenant_id: str


class UsageMetrics(BaseModel):
    """Comprehensive usage metrics for a tenant"""
    tenant_id: str
    time_window_start: datetime
    time_window_end: datetime
    entity_access: List[EntityAccessMetrics] = []
    relationship_traversals: List[RelationshipTraversalMetrics] = []
    property_access: List[PropertyAccessMetrics] = []
    query_patterns: List[QueryPattern] = []
    total_queries: int = 0
    unique_entities_accessed: int = 0


# ============================================================================
# PHASE 2: Recommendation Models
# ============================================================================

class YAMLChange(BaseModel):
    """Represents a change to the YAML ontology"""
    file_path: str
    old_content: str
    new_content: str
    diff: str


class MigrationStrategy(BaseModel):
    """Data migration strategy"""
    required: bool = False
    affected_records: int = 0
    estimated_duration: str = "0 minutes"
    backfill_strategy: Literal["sync", "async", "lazy"] = "lazy"
    cypher_scripts: List[str] = []


class Implementation(BaseModel):
    """Implementation details for a recommendation"""
    yaml_changes: List[YAMLChange] = []
    migration_strategy: MigrationStrategy
    estimated_effort_hours: float = 0.0
    breaking_changes: List[str] = []


class Recommendation(BaseModel):
    """AI-generated ontology improvement recommendation"""
    id: str
    type: RecommendationType
    priority: Priority
    title: str
    rationale: str
    impact: str
    risk: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tenant_id: str
    domain: str
    implementation: Implementation
    usage_metrics: Dict[str, Any] = {}
    predicted_improvement: float = 0.0  # Percentage


# ============================================================================
# PHASE 3: Impact Simulation Models
# ============================================================================

class CompatibilityResult(BaseModel):
    """Compatibility test results"""
    breaking_changes: int = 0
    failing_queries: List[str] = []
    affected_entities: List[str] = []


class PerformanceResult(BaseModel):
    """Performance test results"""
    queries_tested: int = 0
    average_improvement: float = 0.0  # Percentage
    queries_improved: int = 0
    queries_degraded: int = 0
    outliers: List[Dict[str, Any]] = []


class ImpactReport(BaseModel):
    """Comprehensive impact analysis report"""
    recommendation_id: str
    simulation_date: datetime = Field(default_factory=datetime.utcnow)
    compatibility: CompatibilityResult
    performance: PerformanceResult
    data_migration: MigrationStrategy
    risk_score: float = 0.0  # 0-100
    risk_level: RiskLevel
    recommendation_action: Literal["approve", "reject", "needs_review"]


# ============================================================================
# PHASE 4: Approval Workflow Models
# ============================================================================

class ApprovalStatus(str, Enum):
    """Status of approval process"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class Approval(BaseModel):
    """Individual approval record"""
    approver_id: str
    approver_role: str
    status: ApprovalStatus
    comments: str = ""
    approved_at: Optional[datetime] = None


class WorkflowState(BaseModel):
    """State of the approval workflow"""
    recommendation_id: str
    current_state: Literal["simulation", "review", "approval", "execution", "monitoring", "completed", "failed"]
    approvals: List[Approval] = []
    required_approvals: int = 1
    scheduled_execution: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# PHASE 5: Execution Models
# ============================================================================

class DeploymentStatus(str, Enum):
    """Deployment status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class DeploymentMetrics(BaseModel):
    """Metrics tracked during deployment"""
    error_rate: float = 0.0
    p99_latency: float = 0.0
    throughput: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Deployment(BaseModel):
    """Deployment execution record"""
    recommendation_id: str
    status: DeploymentStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    git_branch: str = ""
    git_commit: str = ""
    pr_url: str = ""
    metrics: List[DeploymentMetrics] = []
    rollback_reason: Optional[str] = None


# ============================================================================
# PHASE 6: Feedback & Learning Models
# ============================================================================

class FeedbackData(BaseModel):
    """Post-deployment feedback data"""
    recommendation_id: str
    deployment_date: datetime
    outcome: Literal["success", "rolled_back", "reverted"]

    # Predicted vs Actual
    predicted_impact: Dict[str, Any] = {}
    actual_impact: Dict[str, Any] = {}

    # Lessons learned
    prediction_accuracy: float = 0.0
    missed_issues: List[str] = []
    unexpected_benefits: List[str] = []

    # User feedback
    user_satisfaction: float = 0.0  # 0-10
    user_comments: str = ""

    collected_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# API Request/Response Models
# ============================================================================

class GenerateRecommendationsRequest(BaseModel):
    """Request to generate recommendations"""
    tenant_id: str
    domain: Optional[str] = None
    time_window_days: int = 30
    min_priority: Priority = Priority.LOW


class GenerateRecommendationsResponse(BaseModel):
    """Response with generated recommendations"""
    recommendations: List[Recommendation]
    total_count: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class SimulateRecommendationRequest(BaseModel):
    """Request to simulate a recommendation"""
    recommendation_id: str
    tenant_id: str


class ApproveRecommendationRequest(BaseModel):
    """Request to approve a recommendation"""
    recommendation_id: str
    approver_id: str
    approver_role: str
    comments: str = ""
    schedule_for: Optional[datetime] = None


class ExecuteRecommendationRequest(BaseModel):
    """Request to execute an approved recommendation"""
    recommendation_id: str
    tenant_id: str
    create_pr: bool = True
    auto_merge: bool = False
