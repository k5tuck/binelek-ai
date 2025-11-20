"""ML API routes - JWT Protected"""

from fastapi import APIRouter, HTTPException, Depends
from app.models import TrainingRequest, TrainingResponse, PredictionRequest, PredictionResponse
from app.middleware.auth import get_current_user, TokenData
from app.middleware.tenant import validate_tenant_isolation, TenantContext
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/ml",
    tags=["ml"],
    dependencies=[Depends(get_current_user)]  # All routes require authentication
)


@router.post("/train", response_model=TrainingResponse)
async def train_model(
    request: TrainingRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Train a machine learning model - JWT PROTECTED

    Requires valid JWT token with tenant_id claim.

    Supported model types:
    - cost_forecasting: Predict project costs using XGBoost
    - risk_assessment: Assess investment risk using Random Forest
    - roi_prediction: Predict return on investment using XGBoost
    - anomaly_detection: Detect anomalies using Isolation Forest

    All training runs are logged to MLFlow for experiment tracking.
    Models are tenant-isolated based on JWT token.
    """
    try:
        # CRITICAL: Validate tenant isolation
        # Prevent users from training models for other tenants
        validate_tenant_isolation(current_user.tenant_id, str(request.tenant_id))

        # Set tenant context for the request
        TenantContext.set_tenant_id(current_user.tenant_id)

        logger.info(
            f"Training request from user {current_user.user_id}, "
            f"tenant {current_user.tenant_id}, model type {request.model_type}"
        )

        from app.main import get_training_pipeline

        pipeline = get_training_pipeline()
        response = await pipeline.train_model(request)

        return response

    except HTTPException:
        # Re-raise HTTP exceptions (like 403 from tenant validation) as-is
        raise
    except Exception as e:
        logger.error(f"Training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clear tenant context after request
        TenantContext.clear_tenant_id()


@router.post("/predict", response_model=PredictionResponse)
async def predict(
    request: PredictionRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Make predictions using trained models - JWT PROTECTED

    Requires valid JWT token with tenant_id claim.

    Loads the latest model for the authenticated tenant and specified type,
    then makes predictions on the provided features.

    Tenant isolation is enforced - users can only predict using their own models.
    """
    try:
        # CRITICAL: Validate tenant isolation
        validate_tenant_isolation(current_user.tenant_id, str(request.tenant_id))

        # Set tenant context
        TenantContext.set_tenant_id(current_user.tenant_id)

        logger.info(
            f"Prediction request from user {current_user.user_id}, "
            f"tenant {current_user.tenant_id}, model type {request.model_type}"
        )

        # Placeholder - would load model filtered by tenant_id and predict
        # In real implementation:
        # model = load_model(request.model_type, current_user.tenant_id)
        # prediction = model.predict(request.features)

        return PredictionResponse(
            model_type=request.model_type,
            tenant_id=request.tenant_id,
            prediction={"value": 0.85, "note": "Demo prediction - model not yet trained"},
            confidence=0.92,
            model_version="v1.0"
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like 403 from tenant validation) as-is
        raise
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        TenantContext.clear_tenant_id()


@router.get("/health")
async def health_check(current_user: TokenData = Depends(get_current_user)):
    """
    ML router health check - JWT PROTECTED

    Verifies authentication is working correctly.
    """
    return {
        "status": "healthy",
        "service": "binah-ml",
        "router": "/api/ml",
        "authenticated_tenant": current_user.tenant_id,
        "authentication": "enabled"
    }
