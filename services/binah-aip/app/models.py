"""Data models for AIP service"""

from pydantic import BaseModel, Field
from typing import Any, Literal
from datetime import datetime
from uuid import UUID, uuid4


class QueryRequest(BaseModel):
    """Request for AI query processing"""
    query: str = Field(..., description="Natural language query from user")
    tenant_id: UUID = Field(..., description="Tenant ID for data isolation")
    user_id: UUID | None = Field(None, description="User ID for personalization")
    context: dict[str, Any] | None = Field(None, description="Additional context")
    max_steps: int | None = Field(5, description="Maximum reasoning steps")


class QueryType(BaseModel):
    """Classification of query type"""
    type: Literal["factual", "analytical", "predictive", "conversational"]
    confidence: float
    reasoning: str


class ExecutionPlan(BaseModel):
    """Plan for executing a query"""
    steps: list[dict[str, Any]]
    tools_required: list[str]
    estimated_complexity: Literal["low", "medium", "high"]


class AIResponse(BaseModel):
    """Response from AI query processing"""
    query_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    query: str
    query_type: str
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_steps: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    processing_time_ms: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Agent(BaseModel):
    """Configuration for a specialized agent"""
    name: str
    description: str
    capabilities: list[str]
    tools: list[str]


class PropertyAnalysisRequest(BaseModel):
    """Request for property analysis"""
    property_id: UUID
    tenant_id: UUID
    analysis_type: Literal["valuation", "risk", "roi", "market_comparison"]
    parameters: dict[str, Any] | None = None


class PropertyAnalysisResponse(BaseModel):
    """Response from property analysis"""
    property_id: UUID
    analysis_type: str
    result: dict[str, Any]
    confidence: float
    reasoning: str
    recommendations: list[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MarketResearchRequest(BaseModel):
    """Request for market research"""
    location: str
    tenant_id: UUID
    research_type: Literal["trends", "pricing", "demographics", "competition"]
    parameters: dict[str, Any] | None = None


class AuditLogEntry(BaseModel):
    """Audit log entry for AI interactions"""
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    user_id: UUID | None
    query: str
    query_type: str
    response_summary: str
    tools_used: list[str]
    processing_time_ms: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
