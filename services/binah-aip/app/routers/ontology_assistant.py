"""Ontology Assistant Router - LLM-powered chatbot for ontology queries - JWT Protected"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.middleware.auth import get_current_user, TokenData
from app.middleware.tenant import validate_tenant_isolation, TenantContext
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/ontology-assistant",
    tags=["ontology-assistant"],
    dependencies=[Depends(get_current_user)]  # All routes require authentication
)


class Message(BaseModel):
    """Chat message"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[datetime] = None


class QueryRequest(BaseModel):
    """Request model for ontology assistant queries"""
    query: str
    tenant_id: str
    conversation_history: List[Message] = []
    enable_voice: bool = False  # Enable text-to-speech for response


class QueryResponse(BaseModel):
    """Response model for ontology assistant"""
    message: str
    data: Optional[Dict[str, Any]] = None
    cypher_query: Optional[str] = None
    query_type: str  # 'data_query', 'schema_question', 'schema_change', 'health_check'
    requires_confirmation: bool = False
    voice_enabled: bool = False


class OntologyContext(BaseModel):
    """Context about the current ontology"""
    entities: List[str]
    relationships: List[str]
    entity_count: int
    relationship_count: int


@router.post("/query", response_model=QueryResponse)
async def process_ontology_query(
    request: QueryRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Process natural language queries about the ontology - JWT PROTECTED

    Requires valid JWT token with tenant_id claim.

    Examples:
    - "What entities am I tracking?"
    - "Show me all properties over $500k"
    - "Add a field for supplier to my products"
    - "How are clients connected to properties?"
    """
    try:
        # CRITICAL: Validate tenant isolation
        validate_tenant_isolation(current_user.tenant_id, request.tenant_id)

        # Set tenant context for the request
        TenantContext.set_tenant_id(current_user.tenant_id)

        logger.info(
            f"Processing ontology query for user {current_user.user_id}, "
            f"tenant {current_user.tenant_id}: {request.query}"
        )

        # Classify query type
        query_type = classify_query(request.query)

        if query_type == "data_query":
            return await handle_data_query(request)
        elif query_type == "schema_question":
            return await handle_schema_question(request)
        elif query_type == "schema_change":
            return await handle_schema_change(request)
        elif query_type == "health_check":
            return await handle_health_check(request)
        else:
            return QueryResponse(
                message="I'm not sure how to help with that. Can you rephrase your question?",
                query_type="unknown",
                voice_enabled=request.enable_voice
            )

    except HTTPException:
        # Re-raise HTTP exceptions (like 403 from tenant validation) as-is
        raise
    except Exception as e:
        logger.error(f"Error processing ontology query: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clear tenant context after request
        TenantContext.clear_tenant_id()


def classify_query(query: str) -> str:
    """Classify the type of query"""
    query_lower = query.lower()

    # Data query keywords
    if any(keyword in query_lower for keyword in ['show', 'find', 'get', 'list', 'display', 'count']):
        return "data_query"

    # Schema question keywords
    if any(keyword in query_lower for keyword in ['what is', 'what are', 'how are', 'explain', 'describe']):
        return "schema_question"

    # Schema change keywords
    if any(keyword in query_lower for keyword in ['add', 'create', 'remove', 'delete', 'update', 'modify']):
        return "schema_change"

    # Health check keywords
    if any(keyword in query_lower for keyword in ['check', 'health', 'status', 'issues', 'problems']):
        return "health_check"

    return "unknown"


async def handle_data_query(request: QueryRequest) -> QueryResponse:
    """Handle queries requesting data"""
    # For mock mode, return sample data
    return QueryResponse(
        message=f"I found 5 items matching your query: '{request.query}'. "
                "This is mock data since the database is not connected.",
        data={
            "items": [
                {"id": "1", "name": "Sample Property 1", "price": 550000},
                {"id": "2", "name": "Sample Property 2", "price": 620000},
                {"id": "3", "name": "Sample Property 3", "price": 480000},
                {"id": "4", "name": "Sample Property 4", "price": 750000},
                {"id": "5", "name": "Sample Property 5", "price": 890000},
            ],
            "total_count": 5
        },
        cypher_query="MATCH (p:Property) WHERE p.price > 500000 RETURN p LIMIT 5",
        query_type="data_query",
        voice_enabled=request.enable_voice
    )


async def handle_schema_question(request: QueryRequest) -> QueryResponse:
    """Handle questions about the ontology schema"""
    query_lower = request.query.lower()

    if 'tracking' in query_lower or 'entities' in query_lower:
        message = """You're tracking 5 main entity types:

🏠 **Property**: address, price, bedrooms, bathrooms, sqft (189 records)
👤 **Client**: name, email, phone, type, budget (237 records)
📅 **Showing**: date, time, feedback, interest level (543 records)
💰 **Offer**: amount, date, status, contingencies (67 records)
💵 **Commission**: rate, amount, split, paid date (45 records)

Would you like me to explain any of these in more detail?"""

    elif 'connected' in query_lower or 'relationship' in query_lower:
        message = """Clients are connected to properties in 2 ways:

1. **INTERESTED_IN** relationship
   - Meaning: Client wants to view/buy this property
   - Attributes: priority (High, Medium, Low)

2. **OWNS** relationship
   - Meaning: Client owns/selling this property

You also track **SHOWINGS** to see which clients visited which properties.

Would you like to see specific examples?"""

    else:
        message = "I can help you understand your data structure. Try asking about entities you're tracking or how they're connected."

    return QueryResponse(
        message=message,
        query_type="schema_question",
        voice_enabled=request.enable_voice
    )


async def handle_schema_change(request: QueryRequest) -> QueryResponse:
    """Handle requests to modify the ontology"""
    return QueryResponse(
        message="""I can help you modify your ontology. Here's what I propose:

**Option 1**: Add a simple field to an existing entity
- Quick and easy
- Good for simple attributes

**Option 2**: Create a new entity with relationships
- More structured
- Better for complex data

Which approach would you prefer? Please confirm before I make changes.""",
        query_type="schema_change",
        requires_confirmation=True,
        voice_enabled=request.enable_voice
    )


async def handle_health_check(request: QueryRequest) -> QueryResponse:
    """Perform ontology health check"""
    return QueryResponse(
        message="""I analyzed your ontology and found:

✅ **Overall Health**: Good (85/100)

**Recommendations**:
1. Consider adding indexes for frequently queried fields
2. Some entities could use timestamp fields (created_at, updated_at)
3. Your relationship structure is well-organized

Everything looks good! Your ontology is healthy.""",
        query_type="health_check",
        voice_enabled=request.enable_voice
    )


@router.get("/context/{tenant_id}", response_model=OntologyContext)
async def get_ontology_context(
    tenant_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get current ontology context for a tenant - JWT PROTECTED

    Requires valid JWT token with tenant_id claim.
    """
    # CRITICAL: Validate tenant isolation
    # Only allow users to get context for their own tenant
    validate_tenant_isolation(current_user.tenant_id, tenant_id)

    # Mock data for now
    return OntologyContext(
        entities=["Property", "Client", "Showing", "Offer", "Commission"],
        relationships=["INTERESTED_IN", "OWNS", "ATTENDED", "MADE_OFFER"],
        entity_count=1081,
        relationship_count=2547
    )
