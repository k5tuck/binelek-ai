"""Data models for ML service"""

from pydantic import BaseModel, Field
from typing import Any, Literal
from uuid import UUID
from datetime import datetime


class TrainingRequest(BaseModel):
    """Request to train a model"""
    model_type: Literal["cost_forecasting", "risk_assessment", "roi_prediction", "anomaly_detection"]
    tenant_id: UUID
    hyperparameters: dict[str, Any] | None = None
    training_data_query: str | None = None  # Custom query for training data
    validation_split: float = Field(0.2, ge=0.0, le=0.5)


class TrainingResponse(BaseModel):
    """Response from model training"""
    run_id: str
    model_type: str
    tenant_id: UUID
    status: Literal["queued", "training", "completed", "failed"]
    metrics: dict[str, float] | None = None
    model_uri: str | None = None
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PredictionRequest(BaseModel):
    """Request for model prediction"""
    model_type: Literal["cost_forecasting", "risk_assessment", "roi_prediction", "anomaly_detection"]
    tenant_id: UUID
    features: dict[str, Any]
    model_version: str | None = None  # Optional: use specific model version


class PredictionResponse(BaseModel):
    """Response from model prediction"""
    model_type: str
    tenant_id: UUID
    prediction: Any
    confidence: float | None = None
    model_version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ModelInfo(BaseModel):
    """Information about a trained model"""
    model_type: str
    tenant_id: UUID
    version: str
    metrics: dict[str, float]
    hyperparameters: dict[str, Any]
    training_date: datetime
    status: Literal["training", "ready", "deprecated"]
