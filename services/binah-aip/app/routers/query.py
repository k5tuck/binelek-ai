"""Query API routes - JWT Protected"""

from fastapi import APIRouter, HTTPException, Depends
from app.models import QueryRequest, AIResponse
from app.services.ai_orchestrator import AIOrchestrator
from app.middleware.auth import get_current_user, TokenData
from app.middleware.tenant import validate_tenant_isolation, TenantContext
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/query",
    tags=["query"],
    dependencies=[Depends(get_current_user)]  # All routes require authentication
)


# Dependency to get orchestrator (would be injected via DI in production)
def get_orchestrator():
    # This is a placeholder - in production would be properly initialized
    from app.main import get_ai_orchestrator
    return get_ai_orchestrator()


@router.post("/", response_model=AIResponse)
async def process_query(
    request: QueryRequest,
    current_user: TokenData = Depends(get_current_user),
    orchestrator: AIOrchestrator = Depends(get_orchestrator)
):
    """
    Process a natural language query - JWT PROTECTED

    Requires valid JWT token with tenant_id claim.

    This endpoint accepts a user query and uses AI to:
    1. Classify the query type
    2. Create an execution plan
    3. Retrieve relevant data from knowledge graph and vector store
    4. Execute any required ML predictions
    5. Synthesize a comprehensive response

    All queries are tenant-isolated for multi-tenancy.
    """
    try:
        # CRITICAL: Validate tenant isolation
        validate_tenant_isolation(current_user.tenant_id, request.tenant_id)

        # Set tenant context for the request
        TenantContext.set_tenant_id(current_user.tenant_id)

        logger.info(
            f"Received query from user {current_user.user_id}, "
            f"tenant {current_user.tenant_id}: {request.query}"
        )
        response = await orchestrator.process_query(request)
        return response

    except HTTPException:
        # Re-raise HTTP exceptions (like 403 from tenant validation) as-is
        raise
    except Exception as e:
        logger.error(f"Query processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clear tenant context after request
        TenantContext.clear_tenant_id()


@router.get("/health")
async def health_check(current_user: TokenData = Depends(get_current_user)):
    """
    Query router health check - JWT PROTECTED

    Verifies authentication is working correctly.
    """
    return {
        "status": "healthy",
        "service": "binah-aip",
        "router": "/api/query",
        "authenticated_tenant": current_user.tenant_id,
        "authentication": "enabled"
    }
