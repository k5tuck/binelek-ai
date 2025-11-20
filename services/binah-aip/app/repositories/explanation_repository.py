"""Repository for storing and retrieving ML explanations"""

import asyncpg
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ExplanationRepository:
    """Repository for managing explanation audit trail"""

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize repository with database connection pool

        Args:
            db_pool: AsyncPG connection pool
        """
        self.db_pool = db_pool
        logger.info("ExplanationRepository initialized")

    async def store_explanation(
        self,
        explanation_data: Dict[str, Any],
        user_id: str,
        tenant_id: str,
        model_id: Optional[str] = None,
        prediction_id: Optional[str] = None
    ) -> str:
        """
        Store explanation in database for audit trail

        Args:
            explanation_data: Full explanation result dictionary
            user_id: ID of user who requested explanation
            tenant_id: Tenant ID for multi-tenancy
            model_id: Optional model ID (can be extracted from explanation_data)
            prediction_id: Optional prediction ID (can be extracted from explanation_data)

        Returns:
            ID of stored explanation record
        """
        try:
            # Extract IDs from explanation data if not provided
            if model_id is None:
                model_id = explanation_data.get("model_id")
            if prediction_id is None:
                prediction_id = explanation_data.get("prediction_id")

            method = explanation_data.get("method", "unknown")

            query = """
                INSERT INTO explanations
                (tenant_id, user_id, model_id, prediction_id, method, explanation_data, created_at)
                VALUES ($1, $2, $3::UUID, $4::UUID, $5, $6, $7)
                RETURNING id
            """

            async with self.db_pool.acquire() as conn:
                result = await conn.fetchrow(
                    query,
                    tenant_id,
                    user_id,
                    model_id,
                    prediction_id,
                    method,
                    json.dumps(explanation_data),
                    datetime.utcnow()
                )

            explanation_id = str(result["id"])
            logger.info(f"Stored explanation {explanation_id} for prediction {prediction_id}")
            return explanation_id

        except Exception as e:
            logger.error(f"Error storing explanation: {str(e)}")
            raise

    async def get_explanation_by_id(
        self,
        explanation_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve explanation by ID (with tenant isolation)

        Args:
            explanation_id: ID of explanation
            tenant_id: Tenant ID for security check

        Returns:
            Explanation record or None if not found
        """
        try:
            query = """
                SELECT * FROM explanations
                WHERE id = $1::UUID AND tenant_id = $2
            """

            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(query, explanation_id, tenant_id)

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"Error retrieving explanation {explanation_id}: {str(e)}")
            raise

    async def get_explanations_for_prediction(
        self,
        prediction_id: str,
        tenant_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all explanations for a prediction (audit trail)

        Args:
            prediction_id: ID of prediction
            tenant_id: Tenant ID for security
            limit: Maximum number of records to return

        Returns:
            List of explanation records
        """
        try:
            query = """
                SELECT
                    id,
                    tenant_id,
                    user_id,
                    model_id,
                    prediction_id,
                    method,
                    explanation_data,
                    created_at
                FROM explanations
                WHERE prediction_id = $1::UUID AND tenant_id = $2
                ORDER BY created_at DESC
                LIMIT $3
            """

            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query, prediction_id, tenant_id, limit)

            explanations = [dict(row) for row in rows]
            logger.info(f"Retrieved {len(explanations)} explanations for prediction {prediction_id}")
            return explanations

        except Exception as e:
            logger.error(f"Error retrieving explanations for prediction {prediction_id}: {str(e)}")
            raise

    async def get_explanations_for_model(
        self,
        model_id: str,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve explanations for a model (for model monitoring)

        Args:
            model_id: ID of model
            tenant_id: Tenant ID for security
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of explanation records
        """
        try:
            query = """
                SELECT
                    id,
                    tenant_id,
                    user_id,
                    model_id,
                    prediction_id,
                    method,
                    explanation_data,
                    created_at
                FROM explanations
                WHERE model_id = $1::UUID AND tenant_id = $2
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
            """

            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query, model_id, tenant_id, limit, offset)

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error retrieving explanations for model {model_id}: {str(e)}")
            raise

    async def get_explanations_by_user(
        self,
        user_id: str,
        tenant_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieve explanations requested by a user

        Args:
            user_id: ID of user
            tenant_id: Tenant ID for security
            limit: Maximum number of records to return

        Returns:
            List of explanation records
        """
        try:
            query = """
                SELECT
                    id,
                    tenant_id,
                    user_id,
                    model_id,
                    prediction_id,
                    method,
                    explanation_data,
                    created_at
                FROM explanations
                WHERE user_id = $1 AND tenant_id = $2
                ORDER BY created_at DESC
                LIMIT $3
            """

            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query, user_id, tenant_id, limit)

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error retrieving explanations for user {user_id}: {str(e)}")
            raise

    async def get_explanation_statistics(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about explanation usage (for compliance reporting)

        Args:
            tenant_id: Tenant ID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary with statistics
        """
        try:
            # Build query based on date filters
            date_filter = ""
            params = [tenant_id]
            param_count = 1

            if start_date:
                param_count += 1
                date_filter += f" AND created_at >= ${param_count}"
                params.append(start_date)

            if end_date:
                param_count += 1
                date_filter += f" AND created_at <= ${param_count}"
                params.append(end_date)

            query = f"""
                SELECT
                    COUNT(*) as total_explanations,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT model_id) as unique_models,
                    COUNT(DISTINCT prediction_id) as unique_predictions,
                    COUNT(CASE WHEN method = 'shap' THEN 1 END) as shap_count,
                    COUNT(CASE WHEN method = 'lime' THEN 1 END) as lime_count,
                    COUNT(CASE WHEN method = 'both' THEN 1 END) as both_count,
                    MIN(created_at) as first_explanation,
                    MAX(created_at) as last_explanation
                FROM explanations
                WHERE tenant_id = $1{date_filter}
            """

            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(query, *params)

            stats = dict(row) if row else {}
            logger.info(f"Retrieved explanation statistics for tenant {tenant_id}")
            return stats

        except Exception as e:
            logger.error(f"Error retrieving explanation statistics: {str(e)}")
            raise

    async def delete_old_explanations(
        self,
        tenant_id: str,
        retention_days: int = 2190  # 6 years for HIPAA compliance
    ) -> int:
        """
        Delete explanations older than retention period

        Args:
            tenant_id: Tenant ID
            retention_days: Number of days to retain (default: 6 years for HIPAA)

        Returns:
            Number of records deleted
        """
        try:
            query = """
                DELETE FROM explanations
                WHERE tenant_id = $1
                AND created_at < NOW() - INTERVAL '1 day' * $2
                RETURNING id
            """

            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query, tenant_id, retention_days)

            deleted_count = len(rows)
            logger.info(f"Deleted {deleted_count} old explanation records for tenant {tenant_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting old explanations: {str(e)}")
            raise
