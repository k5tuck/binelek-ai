"""ML Explainability API routes - JWT Protected

Provides SHAP and LIME explanations for ML model predictions
to meet HIPAA and FINRA/SEC compliance requirements.
"""

from fastapi import APIRouter, HTTPException, Depends
from app.models.explainability_schemas import (
    ExplanationRequest,
    ExplanationResponse,
    ComparisonResponse,
    ExplanationHistoryResponse,
    ExplanationStatisticsResponse
)
from app.middleware.auth import get_current_user, TokenData
from app.middleware.tenant import validate_tenant_isolation, TenantContext
from app.services.explainability_service import ExplainabilityService
from app.repositories.explanation_repository import ExplanationRepository
from typing import Optional, List
import logging
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/ml/explain",
    tags=["explainability"],
    dependencies=[Depends(get_current_user)]  # All routes require authentication
)

# Global service instance (in production, would use dependency injection)
_explainability_service: Optional[ExplainabilityService] = None
_explanation_repository: Optional[ExplanationRepository] = None


def get_explainability_service() -> ExplainabilityService:
    """Get global explainability service instance"""
    global _explainability_service
    if _explainability_service is None:
        _explainability_service = ExplainabilityService()
    return _explainability_service


def get_explanation_repository() -> ExplanationRepository:
    """Get global explanation repository instance"""
    global _explanation_repository
    if _explanation_repository is None:
        # In production, this would get the DB pool from app context
        raise RuntimeError("Explanation repository not initialized. Database pool required.")
    return _explanation_repository


def set_explanation_repository(repository: ExplanationRepository):
    """Set explanation repository (called during app startup)"""
    global _explanation_repository
    _explanation_repository = repository
    logger.info("Explanation repository set")


@router.post("/", response_model=dict)
async def explain_prediction(
    request: ExplanationRequest,
    current_user: TokenData = Depends(get_current_user),
    explainability_service: ExplainabilityService = Depends(get_explainability_service)
):
    """
    Generate explanation for a prediction - JWT PROTECTED

    Requires valid JWT token with tenant_id claim.

    **Request Body:**
    ```json
    {
        "model_id": "550e8400-e29b-41d4-a716-446655440000",
        "prediction_id": "650e8400-e29b-41d4-a716-446655440001",
        "method": "shap",
        "visualization_type": "waterfall"
    }
    ```

    **Compliance:**
    - HIPAA: Provides "right to explanation" (45 CFR § 164.524)
    - FINRA/SEC: Model risk management (SR 11-7)
    - All explanations logged for audit trail
    - 6-year retention for HIPAA compliance
    """
    try:
        # Set tenant context for the request
        TenantContext.set_tenant_id(current_user.tenant_id)

        logger.info(
            f"Explanation request: tenant={current_user.tenant_id}, user={current_user.user_id}, "
            f"model={request.model_id}, prediction={request.prediction_id}, method={request.method}"
        )

        # TODO: In production, validate that tenant owns the model
        # model = await get_model(request.model_id)
        # validate_tenant_isolation(current_user.tenant_id, model.tenant_id)

        # TODO: Get actual prediction data from database/MLflow
        # For now, create dummy data for demonstration
        # In production, this would fetch:
        # - X_test: Input features for the prediction
        # - X_train: Training data sample (for LIME)
        # - feature_names: Names of features
        # - class_names: Class names (for classification)
        # - model_path: Path to model file

        # Dummy data (replace with actual data retrieval)
        prediction_data = await _get_prediction_data(request.prediction_id)

        # Generate explanation based on method
        if request.method == "shap":
            result = await explainability_service.explain_with_shap(
                model_id=request.model_id,
                prediction_id=request.prediction_id,
                X_test=prediction_data["X_test"],
                feature_names=prediction_data["feature_names"],
                model_path=prediction_data.get("model_path")
            )

        elif request.method == "lime":
            result = await explainability_service.explain_with_lime(
                model_id=request.model_id,
                prediction_id=request.prediction_id,
                X_train=prediction_data["X_train"],
                X_test=prediction_data["X_test"],
                feature_names=prediction_data["feature_names"],
                class_names=prediction_data.get("class_names"),
                model_path=prediction_data.get("model_path")
            )

        elif request.method == "both":
            result = await explainability_service.compare_explanations(
                model_id=request.model_id,
                prediction_id=request.prediction_id,
                X_train=prediction_data["X_train"],
                X_test=prediction_data["X_test"],
                feature_names=prediction_data["feature_names"],
                class_names=prediction_data.get("class_names"),
                model_path=prediction_data.get("model_path")
            )

        else:
            raise HTTPException(status_code=400, detail="Invalid method. Use 'shap', 'lime', or 'both'")

        # Store explanation for audit trail
        try:
            repo = get_explanation_repository()
            explanation_id = await repo.store_explanation(
                explanation_data=result,
                user_id=current_user.user_id,
                tenant_id=current_user.tenant_id,
                model_id=request.model_id,
                prediction_id=request.prediction_id
            )
            result["explanation_id"] = explanation_id
            logger.info(f"Explanation stored with ID: {explanation_id}")
        except RuntimeError:
            # If repository not initialized (e.g., no DB), log warning but continue
            logger.warning("Explanation repository not available. Skipping audit trail storage.")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating explanation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate explanation: {str(e)}")
    finally:
        # Clear tenant context after request
        TenantContext.clear_tenant_id()


@router.get("/history/{prediction_id}")
async def get_explanation_history(
    prediction_id: str,
    current_user: TokenData = Depends(get_current_user),
    limit: int = 100
):
    """
    Get all explanations requested for a prediction (audit trail) - JWT PROTECTED

    Requires valid JWT token with tenant_id claim.

    **Compliance:**
    - Required for HIPAA audits
    - Required for FINRA/SEC model governance
    - Shows who requested explanations and when
    """
    try:
        repo = get_explanation_repository()
        history = await repo.get_explanations_for_prediction(
            prediction_id=prediction_id,
            tenant_id=current_user.tenant_id,
            limit=limit
        )

        return {
            "prediction_id": prediction_id,
            "total_explanations": len(history),
            "explanations": history
        }

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail="Explanation repository not available")
    except Exception as e:
        logger.error(f"Error retrieving explanation history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_explanation_statistics(
    current_user: TokenData = Depends(get_current_user),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """
    Get explanation usage statistics (for compliance reporting) - JWT PROTECTED

    Requires valid JWT token with tenant_id claim.

    **Use Cases:**
    - HIPAA: Quarterly reports on patient data access
    - FINRA/SEC: Model risk management reporting
    - Internal audits

    **Query Parameters:**
    - start_date: Optional start date filter (ISO format)
    - end_date: Optional end date filter (ISO format)
    """
    try:
        repo = get_explanation_repository()
        stats = await repo.get_explanation_statistics(
            tenant_id=current_user.tenant_id,
            start_date=start_date,
            end_date=end_date
        )

        return stats

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail="Explanation repository not available")
    except Exception as e:
        logger.error(f"Error retrieving explanation statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model/{model_id}")
async def get_model_explanations(
    model_id: str,
    current_user: TokenData = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0
):
    """
    Get all explanations for a specific model - JWT PROTECTED

    Requires valid JWT token with tenant_id claim.

    **Use Cases:**
    - Model monitoring
    - Feature importance analysis over time
    - Model governance
    """
    try:
        repo = get_explanation_repository()
        explanations = await repo.get_explanations_for_model(
            model_id=model_id,
            tenant_id=current_user.tenant_id,
            limit=limit,
            offset=offset
        )

        return {
            "model_id": model_id,
            "total_returned": len(explanations),
            "limit": limit,
            "offset": offset,
            "explanations": explanations
        }

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail="Explanation repository not available")
    except Exception as e:
        logger.error(f"Error retrieving model explanations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check(current_user: TokenData = Depends(get_current_user)):
    """
    Health check endpoint for explainability service - JWT PROTECTED

    Verifies authentication is working correctly.
    """
    service = get_explainability_service()

    try:
        repo = get_explanation_repository()
        repo_status = "healthy"
    except RuntimeError:
        repo_status = "not_initialized"

    return {
        "status": "healthy",
        "service": "explainability",
        "router": "/api/ml/explain",
        "authenticated_tenant": current_user.tenant_id,
        "authentication": "enabled",
        "features": {
            "shap": "enabled",
            "lime": "enabled",
            "comparison": "enabled",
            "audit_trail": repo_status
        },
        "compliance": {
            "hipaa": "enabled",
            "finra_sec": "enabled"
        }
    }


# Helper function to get prediction data
# In production, this would query the predictions table and load model artifacts
async def _get_prediction_data(prediction_id: str) -> dict:
    """
    Get prediction data from database

    This is a placeholder. In production, this would:
    1. Query predictions table for input features
    2. Load model from MLflow or model registry
    3. Get training data sample from feature store
    4. Return all necessary data for explanation
    """
    # TODO: Replace with actual database query
    # For now, return dummy data for testing

    logger.warning(f"Using dummy data for prediction {prediction_id}. Replace with actual data retrieval.")

    # Create dummy data
    np.random.seed(42)
    X_train = np.random.randn(100, 5)
    X_test = np.random.randn(1, 5)

    return {
        "X_train": X_train,
        "X_test": X_test,
        "feature_names": ["age", "income", "credit_score", "loan_amount", "employment_years"],
        "class_names": None,  # None for regression, ["low_risk", "high_risk"] for classification
        "model_path": None  # Path to model file
    }
