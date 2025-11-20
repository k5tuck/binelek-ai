"""Property Analysis API routes - JWT Protected"""

from fastapi import APIRouter, HTTPException, Depends
from app.models import PropertyAnalysisRequest, PropertyAnalysisResponse
from app.middleware.auth import get_current_user, TokenData
from app.middleware.tenant import validate_tenant_isolation, TenantContext
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/property",
    tags=["property"],
    dependencies=[Depends(get_current_user)]  # All routes require authentication
)


@router.post("/analyze", response_model=PropertyAnalysisResponse)
async def analyze_property(
    request: PropertyAnalysisRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Analyze a property - JWT PROTECTED

    Requires valid JWT token with tenant_id claim.

    Supported analysis types:
    - valuation: Estimate property value
    - risk: Assess investment risks
    - roi: Calculate return on investment
    - market_comparison: Compare with similar properties
    """
    try:
        # CRITICAL: Validate tenant isolation
        validate_tenant_isolation(current_user.tenant_id, request.tenant_id)

        # Set tenant context for the request
        TenantContext.set_tenant_id(current_user.tenant_id)

        logger.info(
            f"Analyzing property {request.property_id} for user {current_user.user_id}, "
            f"tenant {current_user.tenant_id}"
        )

        # Would call agent here
        from app.agents.property_agent import PropertyAnalysisAgent
        from app.main import get_ai_orchestrator

        orchestrator = get_ai_orchestrator()
        agent = PropertyAnalysisAgent(orchestrator.llm, orchestrator.hybrid_retriever)

        response = await agent.analyze(request)
        return response

    except HTTPException:
        # Re-raise HTTP exceptions (like 403 from tenant validation) as-is
        raise
    except Exception as e:
        logger.error(f"Property analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clear tenant context after request
        TenantContext.clear_tenant_id()
