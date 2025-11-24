"""
FastAPI application for binah-llm-extractor service.

This service extracts structured entities from unstructured text using LLMs
and integrates with binah-discovery for ontology schemas.
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from .config import settings
from .extractor import LLMEntityExtractor
from .consumer import EntityExtractionConsumer

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
extractor: Optional[LLMEntityExtractor] = None
consumer: Optional[EntityExtractionConsumer] = None
consumer_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown logic."""
    global extractor, consumer, consumer_task

    # Startup
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")

    try:
        # Initialize LLM extractor
        extractor = LLMEntityExtractor()
        logger.info("LLM extractor initialized")

        # Initialize and start Kafka consumer
        consumer = EntityExtractionConsumer(extractor)
        consumer_task = asyncio.create_task(consumer.start())
        logger.info("Kafka consumer started in background")

        logger.info(f"Service ready on port {settings.PORT}")

    except Exception as e:
        logger.error(f"Failed to start service: {e}", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("Shutting down service...")

    if consumer:
        await consumer.stop()

    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    if extractor:
        await extractor.close()

    logger.info("Service shut down successfully")


# Create FastAPI app
app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.SERVICE_VERSION,
    description="LLM-powered entity extraction from unstructured data",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure properly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    provider: str
    model: str


class ExtractRequest(BaseModel):
    """Manual entity extraction request."""
    text: str
    tenant_id: str
    domain: str
    metadata: Optional[Dict[str, Any]] = None


class Entity(BaseModel):
    """Extracted entity."""
    type: str
    attributes: Dict[str, Any]
    confidence: float


class ExtractResponse(BaseModel):
    """Entity extraction response."""
    entities: List[Entity]
    count: int


class StatsResponse(BaseModel):
    """Service statistics."""
    service: str
    version: str
    kafka_connected: bool
    kafka_topic_pattern: str
    provider: str
    model: str
    confidence_thresholds: Dict[str, float]


# API Endpoints

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        provider=settings.LLM_PROVIDER,
        model=settings.LLM_MODEL
    )


@app.get("/stats", response_model=StatsResponse)
async def stats():
    """Service statistics endpoint."""
    return StatsResponse(
        service=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        kafka_connected=consumer is not None and consumer.running,
        kafka_topic_pattern=settings.KAFKA_TOPIC_PATTERN,
        provider=settings.LLM_PROVIDER,
        model=settings.LLM_MODEL,
        confidence_thresholds={
            "auto_apply": settings.AUTO_APPLY_THRESHOLD,
            "manual_review": settings.MANUAL_REVIEW_THRESHOLD
        }
    )


@app.post("/extract", response_model=ExtractResponse)
async def extract_entities(request: ExtractRequest):
    """
    Manual entity extraction endpoint (for testing/debugging).

    This allows direct extraction without going through Kafka.
    """
    if not extractor:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        entities = await extractor.extract_entities(
            raw_text=request.text,
            tenant_id=request.tenant_id,
            domain=request.domain,
            source_metadata=request.metadata
        )

        return ExtractResponse(
            entities=[
                Entity(
                    type=e["type"],
                    attributes=e.get("attributes", {}),
                    confidence=e.get("confidence", 0.0)
                )
                for e in entities
            ],
            count=len(entities)
        )

    except Exception as e:
        logger.error(f"Error in manual extraction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "description": "LLM-powered entity extraction from unstructured data",
        "endpoints": {
            "health": "/health",
            "stats": "/stats",
            "extract": "/extract (POST)",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=False
    )
