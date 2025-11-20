"""Main FastAPI application for Binah AIP service"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.config import settings
from app.middleware.auth import get_current_user, TokenData
from app.middleware.error_handler import (
    ErrorHandlingMiddleware,
    validation_exception_handler,
    generic_exception_handler
)
from app.routers import query, property, ontology_assistant, autonomous_ontology, explainability
from app.services.ai_orchestrator import AIOrchestrator
from app.services.kafka_event_consumer import KafkaEventConsumer
from app.services.rag_updater import RAGUpdater
from app.services.recommendation_updater import RecommendationUpdater
from app.consumers.entity_consumer import RAGKnowledgeBaseConsumer
from app.consumers.relationship_consumer import RecommendationEngineConsumer
from app.autonomous_ontology import AutonomousOntologyOrchestrator
import logging
import asyncio
from datetime import datetime
from neo4j import GraphDatabase, AsyncGraphDatabase
from qdrant_client import AsyncQdrantClient
import asyncpg
import httpx

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Binah AIP - AI Platform",
    description="AI-powered query processing and analysis for real estate knowledge graphs",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add error handling middleware (adds correlation ID to requests)
app.add_middleware(ErrorHandlingMiddleware)

# Add exception handlers for standardized error responses
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Global orchestrator instances (in production, would use dependency injection)
_orchestrator: AIOrchestrator | None = None
_autonomous_orchestrator: AutonomousOntologyOrchestrator | None = None
_kafka_consumer: KafkaEventConsumer | None = None
_kafka_consumer_task: asyncio.Task | None = None

# Event-driven AI orchestration (Phase 3 Week 14-15)
_rag_consumer: RAGKnowledgeBaseConsumer | None = None
_rag_consumer_task: asyncio.Task | None = None
_rec_consumer: RecommendationEngineConsumer | None = None
_rec_consumer_task: asyncio.Task | None = None
_neo4j_async_driver = None
_qdrant_client: AsyncQdrantClient | None = None
_rag_updater: RAGUpdater | None = None
_recommendation_updater: RecommendationUpdater | None = None


def get_ai_orchestrator() -> AIOrchestrator:
    """Get the global AI orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        raise RuntimeError("AI Orchestrator not initialized")
    return _orchestrator


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global _orchestrator, _autonomous_orchestrator

    logger.info("Initializing Binah AIP service...")

    # Initialize LLM based on provider
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            openai_api_key=settings.openai_api_key
        )
        logger.info(f"Initialized OpenAI LLM: {settings.llm_model}")

    elif settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(
            model=settings.llm_model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            anthropic_api_key=settings.anthropic_api_key
        )
        logger.info(f"Initialized Anthropic LLM: {settings.llm_model}")

    elif settings.llm_provider == "ollama":
        from langchain.llms import Ollama
        llm = Ollama(
            base_url=settings.ollama_base_url,
            model=settings.llm_model
        )
        logger.info(f"Initialized Ollama LLM: {settings.llm_model}")

    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")

    # Initialize AI Orchestrator
    _orchestrator = AIOrchestrator(llm)
    logger.info("AI Orchestrator initialized")

    # Initialize Autonomous Ontology Orchestrator
    _autonomous_orchestrator = AutonomousOntologyOrchestrator(llm=llm)
    autonomous_ontology.set_orchestrator(_autonomous_orchestrator)
    logger.info("Autonomous Ontology Orchestrator initialized")

    # Initialize and start Kafka event consumer
    try:
        kafka_brokers = settings.kafka_brokers if hasattr(settings, 'kafka_brokers') else "localhost:9092"
        _kafka_consumer = KafkaEventConsumer(bootstrap_servers=kafka_brokers)

        # Start Kafka consumer in background task
        _kafka_consumer_task = asyncio.create_task(_kafka_consumer.start())
        logger.info(f"Kafka event consumer started. Subscribed to: {_kafka_consumer.topics}")
    except Exception as e:
        logger.warning(f"Failed to start Kafka consumer: {e}. Service will continue without event processing.")

    # Initialize Event-Driven AI Orchestration (Phase 3 Week 14-15)
    try:
        global _rag_consumer, _rag_consumer_task, _rec_consumer, _rec_consumer_task
        global _neo4j_async_driver, _qdrant_client, _rag_updater, _recommendation_updater

        kafka_brokers = settings.kafka_brokers if hasattr(settings, 'kafka_brokers') else "localhost:9092"

        # Initialize Neo4j async driver
        _neo4j_async_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password)
        )
        logger.info("Neo4j async driver initialized")

        # Initialize Qdrant client
        _qdrant_client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key
        )
        logger.info("Qdrant async client initialized")

        # Initialize RAG updater
        _rag_updater = RAGUpdater(
            neo4j_driver=_neo4j_async_driver,
            qdrant_client=_qdrant_client,
            embedding_model=settings.embedding_model
        )
        logger.info("RAG Updater initialized")

        # Initialize Recommendation updater
        _recommendation_updater = RecommendationUpdater(
            neo4j_driver=_neo4j_async_driver,
            qdrant_client=_qdrant_client
        )
        logger.info("Recommendation Updater initialized")

        # Initialize and start RAG Knowledge Base Consumer
        _rag_consumer = RAGKnowledgeBaseConsumer(
            bootstrap_servers=kafka_brokers,
            neo4j_uri=settings.neo4j_uri,
            neo4j_username=settings.neo4j_username,
            neo4j_password=settings.neo4j_password,
            qdrant_client=_qdrant_client,
            embedding_model=settings.embedding_model
        )
        _rag_consumer_task = asyncio.create_task(_rag_consumer.start())
        logger.info(f"RAG Knowledge Base Consumer started. Subscribed to: {_rag_consumer.topics}")

        # Initialize and start Recommendation Engine Consumer
        _rec_consumer = RecommendationEngineConsumer(
            bootstrap_servers=kafka_brokers,
            recommendation_updater=_recommendation_updater
        )
        _rec_consumer_task = asyncio.create_task(_rec_consumer.start())
        logger.info(f"Recommendation Engine Consumer started. Subscribed to: {_rec_consumer.topics}")

        logger.info("Event-Driven AI Orchestration consumers started successfully")

    except Exception as e:
        logger.warning(f"Failed to start Event-Driven AI consumers: {e}. Service will continue without real-time AI updates.")

    logger.info(f"Binah AIP service started successfully on {settings.api_host}:{settings.api_port}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global _orchestrator, _autonomous_orchestrator, _kafka_consumer, _kafka_consumer_task
    global _rag_consumer, _rag_consumer_task, _rec_consumer, _rec_consumer_task
    global _neo4j_async_driver, _qdrant_client

    logger.info("Shutting down Binah AIP service...")

    # Stop RAG Knowledge Base Consumer
    if _rag_consumer:
        try:
            await _rag_consumer.stop()
            logger.info("RAG Knowledge Base Consumer stopped")
        except Exception as e:
            logger.error(f"Error stopping RAG consumer: {e}")

    # Cancel RAG consumer task
    if _rag_consumer_task and not _rag_consumer_task.done():
        _rag_consumer_task.cancel()
        try:
            await _rag_consumer_task
        except asyncio.CancelledError:
            pass

    # Stop Recommendation Engine Consumer
    if _rec_consumer:
        try:
            await _rec_consumer.stop()
            logger.info("Recommendation Engine Consumer stopped")
        except Exception as e:
            logger.error(f"Error stopping Recommendation consumer: {e}")

    # Cancel Recommendation consumer task
    if _rec_consumer_task and not _rec_consumer_task.done():
        _rec_consumer_task.cancel()
        try:
            await _rec_consumer_task
        except asyncio.CancelledError:
            pass

    # Stop Kafka consumer
    if _kafka_consumer:
        try:
            await _kafka_consumer.stop()
            logger.info("Kafka consumer stopped")
        except Exception as e:
            logger.error(f"Error stopping Kafka consumer: {e}")

    # Cancel Kafka consumer task
    if _kafka_consumer_task and not _kafka_consumer_task.done():
        _kafka_consumer_task.cancel()
        try:
            await _kafka_consumer_task
        except asyncio.CancelledError:
            pass

    # Close Neo4j async driver
    if _neo4j_async_driver:
        try:
            await _neo4j_async_driver.close()
            logger.info("Neo4j async driver closed")
        except Exception as e:
            logger.error(f"Error closing Neo4j driver: {e}")

    # Close Qdrant client
    if _qdrant_client:
        try:
            await _qdrant_client.close()
            logger.info("Qdrant client closed")
        except Exception as e:
            logger.error(f"Error closing Qdrant client: {e}")

    if _orchestrator:
        await _orchestrator.close()
        logger.info("AI Orchestrator closed")

    if _autonomous_orchestrator:
        await _autonomous_orchestrator.close()
        logger.info("Autonomous Ontology Orchestrator closed")

    logger.info("Binah AIP service shut down successfully")


# Include routers
app.include_router(query.router)
app.include_router(property.router)
app.include_router(ontology_assistant.router)
app.include_router(autonomous_ontology.router)
app.include_router(explainability.router)


@app.get("/")
async def root():
    """Root endpoint - PUBLIC (no authentication required)"""
    return {
        "service": "Binah AIP",
        "version": "0.2.0",
        "description": "AI Platform for Real Estate Knowledge Graph Intelligence with Autonomous Ontology Management",
        "status": "operational",
        "authentication": "JWT Required (all API endpoints)",
        "features": {
            "ai_query_processing": "✅ Enabled",
            "property_analysis_agents": "✅ Enabled",
            "ontology_assistant": "✅ Enabled",
            "autonomous_ontology_management": "✅ Enabled (Phase 1-2)"
        }
    }


@app.get("/me")
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """
    Get current authenticated user information - PROTECTED

    Returns the decoded JWT token claims for debugging.
    Useful for verifying authentication is working correctly.
    Returns standardized success response format.
    """
    return {
        "success": True,
        "data": {
            "user_id": current_user.user_id,
            "tenant_id": current_user.tenant_id,
            "email": current_user.email,
            "role": current_user.role
        },
        "metadata": {
            "message": "Authentication successful"
        }
    }


@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint with dependency verification - PUBLIC (no authentication required)"""
    checks = {}
    overall_status = "healthy"

    # Check Neo4j connectivity
    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password)
        )
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        checks["neo4j"] = {"status": "healthy", "uri": settings.neo4j_uri}
    except Exception as e:
        checks["neo4j"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"

    # Check PostgreSQL connectivity
    try:
        database_url = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        conn = await asyncpg.connect(database_url)
        await conn.execute("SELECT 1")
        await conn.close()
        checks["postgresql"] = {"status": "healthy", "database": settings.postgres_db}
    except Exception as e:
        checks["postgresql"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"

    # Check Qdrant connectivity
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.qdrant_url}/health")
            if response.status_code == 200:
                checks["qdrant"] = {"status": "healthy", "url": settings.qdrant_url}
            else:
                checks["qdrant"] = {"status": "unhealthy", "http_status": response.status_code}
                overall_status = "unhealthy"
    except Exception as e:
        checks["qdrant"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"

    # Add service-specific status
    checks["service_info"] = {
        "llm_provider": settings.llm_provider,
        "tenant_isolation": settings.enable_tenant_isolation,
        "kafka_consumer": {
            "enabled": _kafka_consumer is not None,
            "running": _kafka_consumer is not None and _kafka_consumer.running,
            "topics": _kafka_consumer.topics if _kafka_consumer else []
        },
        "autonomous_ontology": {
            "enabled": _autonomous_orchestrator is not None
        },
        "event_driven_ai": {
            "rag_consumer": {
                "enabled": _rag_consumer is not None,
                "running": _rag_consumer is not None and _rag_consumer.running,
                "topics": _rag_consumer.topics if _rag_consumer else []
            },
            "recommendation_consumer": {
                "enabled": _rec_consumer is not None,
                "running": _rec_consumer is not None and _rec_consumer.running,
                "topics": _rec_consumer.topics if _rec_consumer else []
            }
        }
    }

    status_code = 200 if overall_status == "healthy" else 503
    return JSONResponse(
        content={
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks
        },
        status_code=status_code
    )


@app.get("/health/ready")
async def readiness():
    """Readiness probe - checks if service is ready to accept traffic - PUBLIC (no authentication required)"""
    try:
        health_response = await health_check()
        health_data = health_response.body.decode() if hasattr(health_response, 'body') else None

        # Service is ready if all critical dependencies are healthy
        # For readiness, we check if the main health endpoint returns 200
        is_ready = health_response.status_code == 200

        return JSONResponse(
            content={
                "status": "ready" if is_ready else "not_ready",
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=200 if is_ready else 503
        )
    except Exception as e:
        return JSONResponse(
            content={
                "status": "not_ready",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=503
        )


@app.get("/health/live")
async def liveness():
    """Liveness probe - checks if service is alive (doesn't check dependencies) - PUBLIC (no authentication required)"""
    return JSONResponse(
        content={
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "binah-aip",
            "version": "0.2.0"
        },
        status_code=200
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development"
    )
