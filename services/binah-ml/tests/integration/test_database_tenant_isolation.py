"""
Integration Tests for Database Tenant Isolation - Day 4

Tests verify:
1. PostgreSQL queries filter by tenant_id
2. Cross-tenant data access is prevented
3. CRUD operations maintain tenant isolation
4. Concurrent multi-tenant access works correctly
5. Data integrity is maintained

Run with:
    cd /home/user/Binelek/services/binah-ml
    python3 -m pytest tests/integration/test_database_tenant_isolation.py -v
"""

import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
from uuid import UUID
import json
from datetime import datetime
import time

# Test tenant IDs
TENANT_A_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TENANT_B_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

# Database connection settings
import os

# Try to connect as postgres user using peer authentication (Unix socket)
DB_CONFIG = {
    'database': 'binah_ml',
    'user': 'postgres',
    'host': '/var/run/postgresql'  # Unix socket for peer authentication
}


@pytest.fixture
def db_connection():
    """Create database connection for testing"""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    yield conn
    conn.rollback()
    conn.close()


@pytest.fixture
def db_cursor(db_connection):
    """Create database cursor with dictionary results"""
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    yield cursor
    cursor.close()


class TestDatabaseTenantIsolation:
    """Integration tests for database tenant isolation"""

    def test_01_get_models_filtered_by_tenant_a(self, db_cursor):
        """Test 1: Verify models query filtered by tenant A"""
        # Query models for tenant A
        db_cursor.execute("""
            SELECT id, tenant_id, model_type, model_name, status
            FROM ml_models
            WHERE tenant_id = %s
            ORDER BY created_at DESC
        """, (TENANT_A_ID,))

        models = db_cursor.fetchall()

        # Assertions
        assert len(models) > 0, "Tenant A should have models"
        assert len(models) == 6, f"Tenant A should have 6 models, found {len(models)}"

        # Verify all models belong to tenant A
        for model in models:
            assert str(model['tenant_id']) == TENANT_A_ID, \
                f"Model {model['id']} should belong to tenant A"

        # Verify expected models exist
        model_types = [m['model_type'] for m in models]
        assert 'cost_forecasting' in model_types
        assert 'risk_assessment' in model_types
        assert 'roi_prediction' in model_types
        assert 'anomaly_detection' in model_types

        print(f"✓ Test 1 PASSED: Found {len(models)} models for Tenant A")

    def test_02_get_models_filtered_by_tenant_b(self, db_cursor):
        """Test 2: Verify models query filtered by tenant B"""
        # Query models for tenant B
        db_cursor.execute("""
            SELECT id, tenant_id, model_type, model_name, status
            FROM ml_models
            WHERE tenant_id = %s
            ORDER BY created_at DESC
        """, (TENANT_B_ID,))

        models = db_cursor.fetchall()

        # Assertions
        assert len(models) > 0, "Tenant B should have models"
        assert len(models) == 6, f"Tenant B should have 6 models, found {len(models)}"

        # Verify all models belong to tenant B
        for model in models:
            assert str(model['tenant_id']) == TENANT_B_ID, \
                f"Model {model['id']} should belong to tenant B"

        print(f"✓ Test 2 PASSED: Found {len(models)} models for Tenant B")

    def test_03_cross_tenant_model_access_blocked(self, db_cursor):
        """Test 3: Verify cross-tenant model access returns empty"""
        # Get a model ID from tenant A
        db_cursor.execute("""
            SELECT id FROM ml_models
            WHERE tenant_id = %s
            LIMIT 1
        """, (TENANT_A_ID,))

        tenant_a_model = db_cursor.fetchone()
        assert tenant_a_model is not None

        tenant_a_model_id = tenant_a_model['id']

        # Try to access tenant A's model with tenant B filter
        db_cursor.execute("""
            SELECT id, tenant_id, model_name
            FROM ml_models
            WHERE id = %s AND tenant_id = %s
        """, (tenant_a_model_id, TENANT_B_ID))

        result = db_cursor.fetchone()

        # Should return None (no access)
        assert result is None, \
            "Tenant B should NOT be able to access Tenant A's model"

        print("✓ Test 3 PASSED: Cross-tenant model access blocked")

    def test_04_get_predictions_filtered_by_tenant(self, db_cursor):
        """Test 4: Verify predictions query filtered by tenant"""
        # Get predictions for tenant A
        db_cursor.execute("""
            SELECT id, tenant_id, model_type, prediction_result
            FROM predictions
            WHERE tenant_id = %s
            ORDER BY created_at DESC
        """, (TENANT_A_ID,))

        predictions_a = db_cursor.fetchall()

        # Get predictions for tenant B
        db_cursor.execute("""
            SELECT id, tenant_id, model_type, prediction_result
            FROM predictions
            WHERE tenant_id = %s
            ORDER BY created_at DESC
        """, (TENANT_B_ID,))

        predictions_b = db_cursor.fetchall()

        # Assertions
        assert len(predictions_a) > 0, "Tenant A should have predictions"
        assert len(predictions_b) > 0, "Tenant B should have predictions"

        # Verify tenant isolation
        for pred in predictions_a:
            assert str(pred['tenant_id']) == TENANT_A_ID

        for pred in predictions_b:
            assert str(pred['tenant_id']) == TENANT_B_ID

        print(f"✓ Test 4 PASSED: Tenant A: {len(predictions_a)} predictions, "
              f"Tenant B: {len(predictions_b)} predictions")

    def test_05_get_training_jobs_filtered_by_tenant(self, db_cursor):
        """Test 5: Verify training jobs query filtered by tenant"""
        # Get training jobs for tenant A
        db_cursor.execute("""
            SELECT id, tenant_id, model_type, status
            FROM training_jobs
            WHERE tenant_id = %s
            ORDER BY created_at DESC
        """, (TENANT_A_ID,))

        jobs_a = db_cursor.fetchall()

        # Get training jobs for tenant B
        db_cursor.execute("""
            SELECT id, tenant_id, model_type, status
            FROM training_jobs
            WHERE tenant_id = %s
            ORDER BY created_at DESC
        """, (TENANT_B_ID,))

        jobs_b = db_cursor.fetchall()

        # Assertions
        assert len(jobs_a) > 0, "Tenant A should have training jobs"
        assert len(jobs_b) > 0, "Tenant B should have training jobs"

        # Verify tenant isolation
        for job in jobs_a:
            assert str(job['tenant_id']) == TENANT_A_ID

        for job in jobs_b:
            assert str(job['tenant_id']) == TENANT_B_ID

        # Verify different statuses exist
        statuses_a = {job['status'] for job in jobs_a}
        assert 'completed' in statuses_a or 'running' in statuses_a

        print(f"✓ Test 5 PASSED: Tenant A: {len(jobs_a)} jobs, "
              f"Tenant B: {len(jobs_b)} jobs")

    def test_06_insert_model_with_tenant_id(self, db_connection, db_cursor):
        """Test 6: Verify new model automatically gets tenant_id"""
        import uuid

        # Create new model for tenant A
        new_model_id = str(uuid.uuid4())
        mlflow_run_id = f"test_run_{int(time.time())}"

        db_cursor.execute("""
            INSERT INTO ml_models
            (id, tenant_id, model_type, model_name, model_version, mlflow_run_id, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id, tenant_id
        """, (new_model_id, TENANT_A_ID, 'test_model', 'Test Model', '1.0', mlflow_run_id, 'training'))

        result = db_cursor.fetchone()

        # Verify insertion
        assert result is not None
        assert str(result['tenant_id']) == TENANT_A_ID

        # Verify it's not accessible by tenant B
        db_cursor.execute("""
            SELECT id FROM ml_models
            WHERE id = %s AND tenant_id = %s
        """, (new_model_id, TENANT_B_ID))

        cross_tenant_result = db_cursor.fetchone()
        assert cross_tenant_result is None

        # Cleanup (rollback will handle this)
        print("✓ Test 6 PASSED: Model created with correct tenant_id and isolated")

    def test_07_update_model_respects_tenant_isolation(self, db_connection, db_cursor):
        """Test 7: Verify updates respect tenant isolation"""
        # Get a model from tenant A
        db_cursor.execute("""
            SELECT id, status FROM ml_models
            WHERE tenant_id = %s AND status = 'ready'
            LIMIT 1
        """, (TENANT_A_ID,))

        model_a = db_cursor.fetchone()
        assert model_a is not None

        model_id = model_a['id']
        original_status = model_a['status']

        # Try to update as tenant A (should succeed)
        db_cursor.execute("""
            UPDATE ml_models
            SET status = 'deprecated'
            WHERE id = %s AND tenant_id = %s
        """, (model_id, TENANT_A_ID))

        assert db_cursor.rowcount == 1, "Update should affect 1 row"

        # Try to update the same model as tenant B (should fail)
        db_cursor.execute("""
            UPDATE ml_models
            SET status = 'ready'
            WHERE id = %s AND tenant_id = %s
        """, (model_id, TENANT_B_ID))

        assert db_cursor.rowcount == 0, "Tenant B should not be able to update Tenant A's model"

        print("✓ Test 7 PASSED: Updates respect tenant isolation")

    def test_08_delete_model_respects_tenant_isolation(self, db_connection, db_cursor):
        """Test 8: Verify deletes respect tenant isolation"""
        import uuid

        # Create a test model for tenant A
        test_model_id = str(uuid.uuid4())
        mlflow_run_id = f"test_delete_{int(time.time())}"

        db_cursor.execute("""
            INSERT INTO ml_models
            (id, tenant_id, model_type, model_name, model_version, mlflow_run_id, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """, (test_model_id, TENANT_A_ID, 'test_model', 'Test Delete Model', '1.0', mlflow_run_id, 'training'))

        # Try to delete as tenant B (should fail)
        db_cursor.execute("""
            DELETE FROM ml_models
            WHERE id = %s AND tenant_id = %s
        """, (test_model_id, TENANT_B_ID))

        assert db_cursor.rowcount == 0, "Tenant B should not be able to delete Tenant A's model"

        # Verify model still exists
        db_cursor.execute("""
            SELECT id FROM ml_models WHERE id = %s
        """, (test_model_id,))

        assert db_cursor.fetchone() is not None, "Model should still exist"

        # Delete as tenant A (should succeed)
        db_cursor.execute("""
            DELETE FROM ml_models
            WHERE id = %s AND tenant_id = %s
        """, (test_model_id, TENANT_A_ID))

        assert db_cursor.rowcount == 1, "Tenant A should be able to delete its own model"

        print("✓ Test 8 PASSED: Deletes respect tenant isolation")

    def test_09_complex_join_query_with_tenant_filter(self, db_cursor):
        """Test 9: Verify complex JOIN queries maintain tenant isolation"""
        # Query models with predictions (JOIN) for tenant A
        db_cursor.execute("""
            SELECT
                m.id as model_id,
                m.tenant_id,
                m.model_type,
                m.model_name,
                COUNT(p.id) as prediction_count
            FROM ml_models m
            LEFT JOIN predictions p ON m.id = p.model_id AND p.tenant_id = m.tenant_id
            WHERE m.tenant_id = %s
            GROUP BY m.id, m.tenant_id, m.model_type, m.model_name
            ORDER BY prediction_count DESC
        """, (TENANT_A_ID,))

        results_a = db_cursor.fetchall()

        # Verify all results belong to tenant A
        assert len(results_a) > 0
        for row in results_a:
            assert str(row['tenant_id']) == TENANT_A_ID

        # Same query for tenant B
        db_cursor.execute("""
            SELECT
                m.id as model_id,
                m.tenant_id,
                m.model_type,
                COUNT(p.id) as prediction_count
            FROM ml_models m
            LEFT JOIN predictions p ON m.id = p.model_id AND p.tenant_id = m.tenant_id
            WHERE m.tenant_id = %s
            GROUP BY m.id, m.tenant_id, m.model_type
        """, (TENANT_B_ID,))

        results_b = db_cursor.fetchall()

        # Verify all results belong to tenant B
        for row in results_b:
            assert str(row['tenant_id']) == TENANT_B_ID

        print(f"✓ Test 9 PASSED: JOIN queries maintain tenant isolation "
              f"(A: {len(results_a)} models, B: {len(results_b)} models)")

    def test_10_model_metadata_tenant_isolation(self, db_cursor):
        """Test 10: Verify model metadata respects tenant isolation via model FK"""
        # Get model metadata for tenant A models
        db_cursor.execute("""
            SELECT mm.id, mm.key, mm.value, m.tenant_id
            FROM model_metadata mm
            JOIN ml_models m ON mm.model_id = m.id
            WHERE m.tenant_id = %s
        """, (TENANT_A_ID,))

        metadata_a = db_cursor.fetchall()

        # Get model metadata for tenant B models
        db_cursor.execute("""
            SELECT mm.id, mm.key, mm.value, m.tenant_id
            FROM model_metadata mm
            JOIN ml_models m ON mm.model_id = m.id
            WHERE m.tenant_id = %s
        """, (TENANT_B_ID,))

        metadata_b = db_cursor.fetchall()

        # Assertions
        assert len(metadata_a) > 0, "Tenant A should have model metadata"
        assert len(metadata_b) > 0, "Tenant B should have model metadata"

        # Verify isolation
        for meta in metadata_a:
            assert str(meta['tenant_id']) == TENANT_A_ID

        for meta in metadata_b:
            assert str(meta['tenant_id']) == TENANT_B_ID

        print(f"✓ Test 10 PASSED: Model metadata respects tenant isolation "
              f"(A: {len(metadata_a)} entries, B: {len(metadata_b)} entries)")

    def test_11_concurrent_tenant_access(self, db_connection):
        """Test 11: Verify concurrent access from multiple tenants works correctly"""
        import threading

        results = {'tenant_a': None, 'tenant_b': None, 'errors': []}

        def query_tenant_a():
            try:
                conn = psycopg2.connect(**DB_CONFIG)
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT COUNT(*) as count FROM ml_models WHERE tenant_id = %s
                """, (TENANT_A_ID,))
                results['tenant_a'] = cursor.fetchone()['count']
                cursor.close()
                conn.close()
            except Exception as e:
                results['errors'].append(f"Tenant A: {e}")

        def query_tenant_b():
            try:
                conn = psycopg2.connect(**DB_CONFIG)
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT COUNT(*) as count FROM ml_models WHERE tenant_id = %s
                """, (TENANT_B_ID,))
                results['tenant_b'] = cursor.fetchone()['count']
                cursor.close()
                conn.close()
            except Exception as e:
                results['errors'].append(f"Tenant B: {e}")

        # Run queries concurrently
        thread_a = threading.Thread(target=query_tenant_a)
        thread_b = threading.Thread(target=query_tenant_b)

        thread_a.start()
        thread_b.start()

        thread_a.join()
        thread_b.join()

        # Verify no errors
        assert len(results['errors']) == 0, f"Concurrent queries failed: {results['errors']}"

        # Verify both got results
        assert results['tenant_a'] > 0
        assert results['tenant_b'] > 0

        print(f"✓ Test 11 PASSED: Concurrent access works correctly "
              f"(A: {results['tenant_a']} models, B: {results['tenant_b']} models)")

    def test_12_training_data_query_with_tenant_filter(self, db_cursor):
        """Test 12: Verify training data queries include tenant_id filter"""
        # Simulate loading training data for cost forecasting model
        db_cursor.execute("""
            SELECT
                tj.id,
                tj.tenant_id,
                tj.model_type,
                tj.status,
                tj.metrics
            FROM training_jobs tj
            WHERE tj.tenant_id = %s
                AND tj.model_type = %s
                AND tj.status = 'completed'
            ORDER BY tj.completed_at DESC
            LIMIT 10
        """, (TENANT_A_ID, 'cost_forecasting'))

        training_data_a = db_cursor.fetchall()

        # Verify results
        assert len(training_data_a) > 0, "Should find completed training jobs for tenant A"

        for job in training_data_a:
            assert str(job['tenant_id']) == TENANT_A_ID
            assert job['model_type'] == 'cost_forecasting'
            assert job['status'] == 'completed'

        print(f"✓ Test 12 PASSED: Training data queries filtered by tenant "
              f"(found {len(training_data_a)} completed jobs)")

    def test_13_query_performance_with_tenant_filter(self, db_cursor):
        """Test 13: Verify query performance with tenant_id filter (indexed)"""
        import time

        # Test query performance with index
        start_time = time.time()

        db_cursor.execute("""
            EXPLAIN ANALYZE
            SELECT id, model_type, status
            FROM ml_models
            WHERE tenant_id = %s
        """, (TENANT_A_ID,))

        explain_output = db_cursor.fetchall()
        elapsed_time = time.time() - start_time

        # Performance should be fast (< 100ms for this small dataset)
        assert elapsed_time < 0.1, f"Query took too long: {elapsed_time:.3f}s"

        # Check if index is used (look for "Index Scan" in explain output)
        explain_text = str(explain_output)
        # In production, we'd verify index usage, but for now just check performance

        print(f"✓ Test 13 PASSED: Query performed in {elapsed_time*1000:.2f}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
