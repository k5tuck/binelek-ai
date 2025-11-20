"""Main FastAPI application for Binah ML service"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.routers import ml  # ML router with JWT authentication
from app.middleware.auth import get_current_user, TokenData
import logging
import asyncpg
import httpx
import mlflow
import mlflow.tracking
from datetime import datetime
import shutil
import os

# Optional ML pipeline import (allows service to start for auth testing without full ML stack)
# FORCE DISABLED FOR AUTHENTICATION TESTING - set to True when ML stack is ready
ML_PIPELINE_AVAILABLE = False
MLTrainingPipeline = None

# try:
#     from app.training.pipeline import MLTrainingPipeline
#     ML_PIPELINE_AVAILABLE = True
# except ImportError as e:
#     logging.warning(f"ML Pipeline not available (will skip training features): {e}")
#     ML_PIPELINE_AVAILABLE = False
#     MLTrainingPipeline = None

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Binah ML",
    description="Machine Learning model training and inference with MLFlow - JWT Secured",
    version="0.2.0",
    docs_url="/docs" if settings.environment == "development" else None,  # Disable docs in production
    redoc_url="/redoc" if settings.environment == "development" else None
)

# CORS middleware - RESTRICTED (no longer allows all origins)
allowed_origins = [
    "http://localhost:3000",  # Frontend development
    "http://localhost:8092",  # API Gateway
    "https://app.binelek.com",  # Production frontend (update as needed)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if settings.environment == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

# Global training pipeline instance
_training_pipeline = None

# Global Kafka consumer instance
_kafka_consumer = None

# Global database pool
_db_pool = None


def get_training_pipeline() -> MLTrainingPipeline:
    """Get the global training pipeline instance"""
    global _training_pipeline
    if _training_pipeline is None:
        raise RuntimeError("Training pipeline not initialized")
    return _training_pipeline


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global _training_pipeline, _kafka_consumer, _db_pool

    logger.info("Initializing Binah ML service...")

    # Track startup time for uptime calculation
    app.state.start_time = datetime.utcnow()

    # Initialize database connection pool
    try:
        database_url = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        _db_pool = await asyncpg.create_pool(
            database_url,
            min_size=5,
            max_size=20
        )
        logger.info("Database connection pool created")
    except Exception as e:
        logger.error(f"Failed to create database pool: {e}")
        # Continue startup even if DB pool fails (for testing)

    # Initialize training pipeline (if available)
    if ML_PIPELINE_AVAILABLE:
        _training_pipeline = MLTrainingPipeline()
        logger.info(f"MLFlow tracking URI: {settings.mlflow_tracking_uri}")
    else:
        logger.warning("ML Pipeline unavailable - authentication testing mode only")

    # Initialize Kafka consumer for auto-training
    try:
        from app.consumers.entity_consumer import EntityCreatedConsumer

        kafka_broker = settings.kafka_bootstrap_servers if hasattr(settings, 'kafka_bootstrap_servers') else 'localhost:9092'
        mlflow_uri = settings.mlflow_tracking_uri if hasattr(settings, 'mlflow_tracking_uri') else 'http://localhost:5000'

        _kafka_consumer = EntityCreatedConsumer(
            kafka_broker=kafka_broker,
            db_pool=_db_pool,
            mlflow_tracking_uri=mlflow_uri,
            training_threshold=100  # Train after 100 new entities
        )

        # Start consumer in background
        import asyncio
        asyncio.create_task(_kafka_consumer.start())

        logger.info("Kafka consumer for auto-training initialized")
    except Exception as e:
        logger.warning(f"Kafka consumer not started (optional feature): {e}")
        # Continue without Kafka consumer if it fails

    logger.info(f"Binah ML service started successfully on {settings.api_host}:{settings.api_port}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global _kafka_consumer, _db_pool

    # Stop Kafka consumer
    if _kafka_consumer:
        await _kafka_consumer.stop()
        logger.info("Kafka consumer stopped")

    # Close database pool
    if _db_pool:
        await _db_pool.close()
        logger.info("Database pool closed")

    logger.info("Binah ML service shut down successfully")


# Include routers
# ML router enabled with JWT authentication and tenant isolation
app.include_router(ml.router)


@app.get("/")
async def root():
    """
    Root endpoint - Public (no authentication required)

    Returns basic service information.
    """
    return {
        "service": "Binah ML",
        "version": "0.2.0",
        "description": "Machine Learning training and inference with MLFlow - JWT Secured",
        "status": "operational",
        "authentication": "required",
        "docs": "/docs" if settings.environment == "development" else "disabled"
    }


@app.get("/health")
async def health_check():
    """
    Comprehensive health check with all dependencies

    Checks:
    - PostgreSQL connection
    - MLflow tracking server
    - Model registry access
    - Disk space for model storage
    """
    checks = {}
    overall_status = "healthy"

    # Check PostgreSQL
    try:
        database_url = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        conn = await asyncpg.connect(database_url)
        await conn.execute("SELECT 1")
        await conn.close()
        checks["postgresql"] = {"status": "healthy", "message": "Connection successful"}
    except Exception as e:
        checks["postgresql"] = {"status": "unhealthy", "error": str(e)}
        overall_status = "unhealthy"

    # Check MLflow Tracking Server
    try:
        tracking_uri = settings.mlflow_tracking_uri
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{tracking_uri}/health", timeout=5.0)
            checks["mlflow"] = {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "uri": tracking_uri
            }
    except Exception as e:
        checks["mlflow"] = {"status": "degraded", "error": str(e)}
        # MLflow is not critical, so just degrade, don't fail

    # Check Model Registry Access
    try:
        client = mlflow.tracking.MlflowClient(tracking_uri=settings.mlflow_tracking_uri)
        experiments = client.search_experiments(max_results=1)
        checks["model_registry"] = {"status": "healthy", "message": "Registry accessible"}
    except Exception as e:
        checks["model_registry"] = {"status": "degraded", "error": str(e)}

    # Check Disk Space (for model storage)
    stat = shutil.disk_usage("/")
    free_gb = stat.free / (1024**3)
    checks["disk_space"] = {
        "status": "healthy" if free_gb > 10 else "degraded",
        "free_gb": round(free_gb, 2),
        "message": "Low disk space" if free_gb < 10 else "Sufficient space"
    }

    status_code = 200 if overall_status == "healthy" else 503
    return JSONResponse(
        content={
            "status": overall_status,
            "service": "binah-ml",
            "version": "0.2.0",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        },
        status_code=status_code
    )


@app.get("/health/ready")
async def readiness():
    """
    Readiness probe for Kubernetes

    Service is ready when all critical dependencies are healthy.
    """
    health = await health_check()
    is_ready = health.body.decode().find('"status":"healthy"') != -1
    return JSONResponse(
        content={"status": "ready" if is_ready else "not_ready"},
        status_code=200 if is_ready else 503
    )


@app.get("/health/live")
async def liveness():
    """
    Liveness probe - always returns 200 unless process is dead

    Returns uptime information for monitoring.
    """
    return {
        "status": "alive",
        "service": "binah-ml",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": (datetime.utcnow() - app.state.start_time).total_seconds()
    }


@app.get("/me")
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """
    Get current authenticated user information - PROTECTED

    Returns the decoded JWT token claims for debugging.
    """
    return {
        "user_id": current_user.user_id,
        "tenant_id": current_user.tenant_id,
        "email": current_user.email,
        "role": current_user.role,
        "message": "Authentication successful"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development"
    )
