"""
Auto-training trigger - fetches data and trains models
"""

import logging
from typing import Dict, Optional
import asyncpg
from datetime import datetime
import mlflow
import mlflow.tracking

from app.training.auto_trainer import AutoTrainer

logger = logging.getLogger(__name__)


class AutoTrainingTrigger:
    """
    Triggers auto-training when called
    Fetches training data from PostgreSQL and trains the appropriate model
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        mlflow_tracking_uri: str
    ):
        """
        Initialize the training trigger

        Args:
            db_pool: PostgreSQL connection pool
            mlflow_tracking_uri: MLflow tracking server URI
        """
        self.db_pool = db_pool
        self.mlflow_tracking_uri = mlflow_tracking_uri

        # Configure MLflow
        mlflow.set_tracking_uri(self.mlflow_tracking_uri)

    async def train(
        self,
        tenant_id: str,
        entity_type: str,
        model_type: str
    ) -> Dict:
        """
        Train a model for the given tenant and entity type

        Args:
            tenant_id: Tenant identifier
            entity_type: Entity type name
            model_type: Model type to train (e.g., 'price_prediction', 'risk_scoring')

        Returns:
            Model information dictionary with name, version, metrics
        """
        try:
            logger.info(
                f"Starting training for tenant={tenant_id}, "
                f"entity_type={entity_type}, model_type={model_type}"
            )

            # Fetch training data
            training_data = await self.fetch_training_data(
                tenant_id=tenant_id,
                entity_type=entity_type,
                model_type=model_type
            )

            if not training_data or len(training_data) == 0:
                raise ValueError(
                    f"No training data available for tenant={tenant_id}, "
                    f"entity_type={entity_type}"
                )

            logger.info(f"Fetched {len(training_data)} records for training")

            # Create auto-trainer
            trainer = AutoTrainer(
                tenant_id=tenant_id,
                model_type=model_type,
                entity_type=entity_type,
                mlflow_tracking_uri=self.mlflow_tracking_uri
            )

            # Train model
            model_info = await trainer.train(training_data)

            logger.info(
                f"Training completed successfully. Model: {model_info['model_name']}, "
                f"Version: {model_info['version']}"
            )

            return model_info

        except Exception as e:
            logger.error(
                f"Training failed for tenant={tenant_id}, "
                f"entity_type={entity_type}, model_type={model_type}: {e}",
                exc_info=True
            )
            raise

    async def fetch_training_data(
        self,
        tenant_id: str,
        entity_type: str,
        model_type: str
    ) -> list:
        """
        Fetch training data from PostgreSQL

        Args:
            tenant_id: Tenant identifier
            entity_type: Entity type name
            model_type: Model type

        Returns:
            List of training records
        """
        try:
            # Determine which table/schema to query based on entity type
            query = self._build_training_data_query(entity_type, model_type)

            async with self.db_pool.acquire() as conn:
                # Fetch data with tenant filtering
                results = await conn.fetch(query, tenant_id)

                # Convert asyncpg records to list of dicts
                training_data = [dict(record) for record in results]

                logger.info(
                    f"Fetched {len(training_data)} training records for "
                    f"tenant={tenant_id}, entity_type={entity_type}"
                )

                return training_data

        except Exception as e:
            logger.error(
                f"Failed to fetch training data for tenant={tenant_id}, "
                f"entity_type={entity_type}: {e}",
                exc_info=True
            )
            raise

    def _build_training_data_query(
        self,
        entity_type: str,
        model_type: str
    ) -> str:
        """
        Build SQL query to fetch training data based on entity type and model type

        Args:
            entity_type: Entity type name
            model_type: Model type

        Returns:
            SQL query string
        """
        # Map entity type and model type to appropriate queries
        # This is a simplified example - in production, you'd have more sophisticated queries

        if model_type == 'price_prediction':
            # Property price prediction
            return """
                SELECT
                    id,
                    square_footage,
                    bedrooms,
                    bathrooms,
                    year_built,
                    location,
                    price as target,
                    created_at
                FROM properties
                WHERE tenant_id = $1
                    AND price IS NOT NULL
                    AND square_footage IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 10000
            """

        elif model_type == 'risk_scoring':
            # Transaction risk scoring
            return """
                SELECT
                    id,
                    transaction_amount,
                    transaction_type,
                    customer_age,
                    credit_score,
                    debt_to_income_ratio,
                    risk_score as target,
                    created_at
                FROM transactions
                WHERE tenant_id = $1
                    AND risk_score IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 10000
            """

        elif model_type == 'lead_scoring':
            # Lead scoring
            return """
                SELECT
                    id,
                    lead_source,
                    engagement_score,
                    company_size,
                    industry,
                    budget,
                    conversion_probability as target,
                    created_at
                FROM leads
                WHERE tenant_id = $1
                    AND conversion_probability IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 10000
            """

        elif model_type == 'churn_prediction':
            # Customer churn prediction
            return """
                SELECT
                    id,
                    tenure_months,
                    monthly_revenue,
                    support_tickets,
                    nps_score,
                    product_usage_score,
                    churned as target,
                    created_at
                FROM customers
                WHERE tenant_id = $1
                    AND churned IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 10000
            """

        elif model_type == 'maintenance_prediction':
            # Asset maintenance prediction
            return """
                SELECT
                    id,
                    asset_age_months,
                    usage_hours,
                    last_maintenance_days_ago,
                    failure_count,
                    maintenance_cost,
                    requires_maintenance as target,
                    created_at
                FROM assets
                WHERE tenant_id = $1
                    AND requires_maintenance IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 10000
            """

        else:
            raise ValueError(f"Unknown model type: {model_type}")
