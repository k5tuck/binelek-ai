"""Pydantic schemas for ML Explainability API"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime


class ExplanationRequest(BaseModel):
    """Request schema for generating ML explanation"""

    model_id: str = Field(..., description="ID of the ML model")
    prediction_id: str = Field(..., description="ID of the prediction to explain")
    method: Literal["shap", "lime", "both"] = Field(
        default="shap",
        description="Explanation method to use"
    )
    visualization_type: Optional[Literal["waterfall", "bar", "force"]] = Field(
        default="waterfall",
        description="Type of visualization to generate"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "model_id": "550e8400-e29b-41d4-a716-446655440000",
                "prediction_id": "650e8400-e29b-41d4-a716-446655440001",
                "method": "shap",
                "visualization_type": "waterfall"
            }
        }


class FeatureImportance(BaseModel):
    """Feature importance from explanation"""

    feature: str = Field(..., description="Feature name")
    shap_value: Optional[float] = Field(None, description="SHAP value (if using SHAP)")
    weight: Optional[float] = Field(None, description="LIME weight (if using LIME)")
    feature_value: Optional[float] = Field(None, description="Actual feature value")
    feature_description: Optional[str] = Field(None, description="LIME feature description")
    abs_importance: float = Field(..., description="Absolute importance score")


class WaterfallData(BaseModel):
    """Waterfall plot data for SHAP"""

    plot_type: str = Field(default="waterfall", description="Type of plot")
    base_value: float = Field(..., description="Base value (expected value)")
    features: List[Dict[str, Any]] = Field(..., description="Feature contributions")
    final_prediction: float = Field(..., description="Final prediction value")


class ExplanationResponse(BaseModel):
    """Response schema for single explanation (SHAP or LIME)"""

    method: Literal["shap", "lime"] = Field(..., description="Explanation method used")
    prediction_id: str = Field(..., description="ID of explained prediction")
    model_id: str = Field(..., description="ID of model")
    base_value: Optional[float] = Field(None, description="Base value (SHAP)")
    intercept: Optional[float] = Field(None, description="Intercept (LIME)")
    feature_importance: List[FeatureImportance] = Field(..., description="Ranked feature importance")
    waterfall_data: Optional[WaterfallData] = Field(None, description="Waterfall plot data")
    explanation_type: Optional[str] = Field(None, description="local or global")
    prediction_score: Optional[float] = Field(None, description="LIME prediction score")
    local_prediction: Optional[float] = Field(None, description="LIME local prediction")

    class Config:
        json_schema_extra = {
            "example": {
                "method": "shap",
                "prediction_id": "650e8400-e29b-41d4-a716-446655440001",
                "model_id": "550e8400-e29b-41d4-a716-446655440000",
                "base_value": 0.5,
                "feature_importance": [
                    {
                        "feature": "age",
                        "shap_value": 0.15,
                        "feature_value": 65,
                        "abs_importance": 0.15
                    },
                    {
                        "feature": "blood_pressure",
                        "shap_value": -0.08,
                        "feature_value": 140,
                        "abs_importance": 0.08
                    }
                ],
                "explanation_type": "local"
            }
        }


class ComparisonResponse(BaseModel):
    """Response schema for comparing SHAP and LIME"""

    shap: Dict[str, Any] = Field(..., description="SHAP explanation")
    lime: Dict[str, Any] = Field(..., description="LIME explanation")
    agreement_score: float = Field(..., description="Agreement score between methods (0-1)")
    top_features_match: Dict[str, Any] = Field(..., description="Top features comparison")
    recommendation: str = Field(..., description="Recommendation on which method to use")


class ExplanationHistoryResponse(BaseModel):
    """Response schema for explanation audit trail"""

    id: str = Field(..., description="Explanation record ID")
    tenant_id: str = Field(..., description="Tenant ID")
    user_id: str = Field(..., description="User who requested explanation")
    model_id: Optional[str] = Field(None, description="Model ID")
    prediction_id: Optional[str] = Field(None, description="Prediction ID")
    method: str = Field(..., description="Explanation method used")
    explanation_data: Dict[str, Any] = Field(..., description="Full explanation data")
    created_at: datetime = Field(..., description="When explanation was generated")


class ExplanationStatisticsResponse(BaseModel):
    """Response schema for explanation usage statistics"""

    total_explanations: int = Field(..., description="Total number of explanations")
    unique_users: int = Field(..., description="Number of unique users requesting explanations")
    unique_models: int = Field(..., description="Number of unique models explained")
    unique_predictions: int = Field(..., description="Number of unique predictions explained")
    shap_count: int = Field(..., description="Number of SHAP explanations")
    lime_count: int = Field(..., description="Number of LIME explanations")
    both_count: int = Field(..., description="Number of comparisons")
    first_explanation: Optional[datetime] = Field(None, description="Timestamp of first explanation")
    last_explanation: Optional[datetime] = Field(None, description="Timestamp of last explanation")

    class Config:
        json_schema_extra = {
            "example": {
                "total_explanations": 1542,
                "unique_users": 45,
                "unique_models": 8,
                "unique_predictions": 1200,
                "shap_count": 980,
                "lime_count": 420,
                "both_count": 142,
                "first_explanation": "2025-01-01T00:00:00Z",
                "last_explanation": "2025-11-14T12:00:00Z"
            }
        }
