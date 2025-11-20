"""
Database connection and query utilities for Binah ML service

Provides PostgreSQL connection pooling and tenant-isolated query functions.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from app.config import settings

logger = logging.getLogger(__name__)

# Connection pool
_connection_pool: Optional[pool.SimpleConnectionPool] = None


def initialize_connection_pool():
    """Initialize PostgreSQL connection pool"""
    global _connection_pool

    if _connection_pool is None:
        try:
            _connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=20,
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password
            )
            logger.info("PostgreSQL connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise


def get_connection():
    """Get connection from pool"""
    if _connection_pool is None:
        initialize_connection_pool()

    return _connection_pool.getconn()


def return_connection(conn):
    """Return connection to pool"""
    if _connection_pool:
        _connection_pool.putconn(conn)


class DatabaseService:
    """
    Database service with tenant-isolated queries

    SECURITY: All queries MUST include tenant_id filter
    """

    def __init__(self, tenant_id: UUID):
        """
        Initialize database service for a specific tenant

        Args:
            tenant_id: UUID of the tenant (from JWT, NOT from request body)
        """
        self.tenant_id = str(tenant_id)
        logger.info(f"DatabaseService initialized for tenant: {self.tenant_id}")

    async def get_training_data_for_model_type(
        self,
        model_type: str,
        limit: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        Load training data for a specific model type

        SECURITY: Always filters by tenant_id from constructor

        Args:
            model_type: Type of model (e.g., 'cost_forecasting')
            limit: Maximum number of records to return

        Returns:
            List of training data records
        """
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # CRITICAL: Query filtered by tenant_id
            query = """
                SELECT
                    tj.id,
                    tj.tenant_id,
                    tj.model_type,
                    tj.training_data_query,
                    tj.metrics,
                    tj.hyperparameters,
                    tj.completed_at
                FROM training_jobs tj
                WHERE tj.tenant_id = %s
                    AND tj.model_type = %s
                    AND tj.status = 'completed'
                    AND tj.metrics IS NOT NULL
                ORDER BY tj.completed_at DESC
                LIMIT %s
            """

            logger.info(f"Loading training data: tenant={self.tenant_id}, model_type={model_type}, limit={limit}")

            cursor.execute(query, (self.tenant_id, model_type, limit))
            results = cursor.fetchall()

            cursor.close()
            return_connection(conn)

            logger.info(f"Loaded {len(results)} training data records")
            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            if conn:
                return_connection(conn)
            return []

    async def get_model_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get model by ID (tenant-filtered)

        Args:
            model_id: UUID of the model

        Returns:
            Model record or None
        """
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # CRITICAL: Query filtered by tenant_id AND model_id
            query = """
                SELECT
                    id,
                    tenant_id,
                    model_type,
                    model_name,
                    model_version,
                    mlflow_run_id,
                    mlflow_model_uri,
                    status,
                    metrics,
                    hyperparameters,
                    created_at,
                    updated_at
                FROM ml_models
                WHERE tenant_id = %s AND id = %s
            """

            cursor.execute(query, (self.tenant_id, model_id))
            result = cursor.fetchone()

            cursor.close()
            return_connection(conn)

            if result:
                return dict(result)
            return None

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            if conn:
                return_connection(conn)
            return None

    async def get_models_by_type(
        self,
        model_type: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get models by type (tenant-filtered)

        Args:
            model_type: Type of model
            status: Optional status filter ('ready', 'training', etc.)

        Returns:
            List of model records
        """
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # CRITICAL: Query filtered by tenant_id
            if status:
                query = """
                    SELECT
                        id,
                        tenant_id,
                        model_type,
                        model_name,
                        model_version,
                        mlflow_run_id,
                        status,
                        metrics,
                        created_at
                    FROM ml_models
                    WHERE tenant_id = %s
                        AND model_type = %s
                        AND status = %s
                    ORDER BY created_at DESC
                """
                cursor.execute(query, (self.tenant_id, model_type, status))
            else:
                query = """
                    SELECT
                        id,
                        tenant_id,
                        model_type,
                        model_name,
                        model_version,
                        mlflow_run_id,
                        status,
                        metrics,
                        created_at
                    FROM ml_models
                    WHERE tenant_id = %s
                        AND model_type = %s
                    ORDER BY created_at DESC
                """
                cursor.execute(query, (self.tenant_id, model_type))

            results = cursor.fetchall()

            cursor.close()
            return_connection(conn)

            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error loading models: {e}")
            if conn:
                return_connection(conn)
            return []

    async def save_prediction(
        self,
        model_id: str,
        model_type: str,
        model_version: str,
        input_features: Dict[str, Any],
        prediction_result: Dict[str, Any],
        confidence: Optional[float] = None,
        created_by: Optional[str] = None
    ) -> Optional[str]:
        """
        Save prediction to database

        Args:
            model_id: UUID of the model
            model_type: Type of model
            model_version: Version of model
            input_features: Input features dict
            prediction_result: Prediction result dict
            confidence: Optional confidence score
            created_by: Optional user ID

        Returns:
            Prediction ID or None
        """
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            import uuid
            import json

            prediction_id = str(uuid.uuid4())

            # CRITICAL: tenant_id automatically set from constructor
            query = """
                INSERT INTO predictions
                (id, tenant_id, model_id, model_type, model_version, input_features, prediction_result, confidence, created_at, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                RETURNING id
            """

            cursor.execute(query, (
                prediction_id,
                self.tenant_id,
                model_id,
                model_type,
                model_version,
                json.dumps(input_features),
                json.dumps(prediction_result),
                confidence,
                created_by
            ))

            result = cursor.fetchone()
            conn.commit()

            cursor.close()
            return_connection(conn)

            logger.info(f"Saved prediction: {prediction_id} for tenant {self.tenant_id}")
            return result['id'] if result else None

        except Exception as e:
            logger.error(f"Error saving prediction: {e}")
            if conn:
                conn.rollback()
                return_connection(conn)
            return None

    async def create_training_job(
        self,
        model_type: str,
        mlflow_run_id: str,
        hyperparameters: Dict[str, Any],
        validation_split: float = 0.2,
        created_by: Optional[str] = None
    ) -> Optional[str]:
        """
        Create training job record

        Args:
            model_type: Type of model
            mlflow_run_id: MLflow run ID
            hyperparameters: Hyperparameters dict
            validation_split: Validation split ratio
            created_by: Optional user ID

        Returns:
            Training job ID or None
        """
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            import uuid
            import json

            job_id = str(uuid.uuid4())

            # CRITICAL: tenant_id automatically set from constructor
            query = """
                INSERT INTO training_jobs
                (id, tenant_id, model_type, status, mlflow_run_id, hyperparameters, validation_split, created_at, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                RETURNING id
            """

            cursor.execute(query, (
                job_id,
                self.tenant_id,
                model_type,
                'queued',
                mlflow_run_id,
                json.dumps(hyperparameters),
                validation_split,
                created_by
            ))

            result = cursor.fetchone()
            conn.commit()

            cursor.close()
            return_connection(conn)

            logger.info(f"Created training job: {job_id} for tenant {self.tenant_id}")
            return result['id'] if result else None

        except Exception as e:
            logger.error(f"Error creating training job: {e}")
            if conn:
                conn.rollback()
                return_connection(conn)
            return None


# Initialize connection pool on import
try:
    initialize_connection_pool()
except Exception as e:
    logger.warning(f"Could not initialize connection pool on import: {e}")
