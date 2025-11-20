#!/usr/bin/env python3
"""
Simple test runner for integration tests
Runs tests without pytest to avoid temp directory issues
"""

import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import threading
import uuid

# Test tenant IDs
TENANT_A_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TENANT_B_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

# Database connection settings (using Unix socket for peer authentication)
DB_CONFIG = {
    'database': 'binah_ml',
    'user': 'postgres',
    'host': '/var/run/postgresql'
}

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG)


def test_01_get_models_filtered_by_tenant_a():
    """Test 1: Verify models query filtered by tenant A"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT id, tenant_id, model_type, model_name, status
            FROM ml_models
            WHERE tenant_id = %s
            ORDER BY created_at DESC
        """, (TENANT_A_ID,))

        models = cursor.fetchall()

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

        cursor.close()
        conn.close()

        return True, f"Found {len(models)} models for Tenant A"
    except Exception as e:
        return False, str(e)


def test_02_get_models_filtered_by_tenant_b():
    """Test 2: Verify models query filtered by tenant B"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT id, tenant_id, model_type, model_name, status
            FROM ml_models
            WHERE tenant_id = %s
            ORDER BY created_at DESC
        """, (TENANT_B_ID,))

        models = cursor.fetchall()

        # Assertions
        assert len(models) > 0, "Tenant B should have models"
        assert len(models) == 6, f"Tenant B should have 6 models, found {len(models)}"

        # Verify all models belong to tenant B
        for model in models:
            assert str(model['tenant_id']) == TENANT_B_ID, \
                f"Model {model['id']} should belong to tenant B"

        cursor.close()
        conn.close()

        return True, f"Found {len(models)} models for Tenant B"
    except Exception as e:
        return False, str(e)


def test_03_cross_tenant_model_access_blocked():
    """Test 3: Verify cross-tenant model access returns empty"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get a model ID from tenant A
        cursor.execute("""
            SELECT id FROM ml_models
            WHERE tenant_id = %s
            LIMIT 1
        """, (TENANT_A_ID,))

        tenant_a_model = cursor.fetchone()
        assert tenant_a_model is not None

        tenant_a_model_id = tenant_a_model['id']

        # Try to access tenant A's model with tenant B filter
        cursor.execute("""
            SELECT id, tenant_id, model_name
            FROM ml_models
            WHERE id = %s AND tenant_id = %s
        """, (tenant_a_model_id, TENANT_B_ID))

        result = cursor.fetchone()

        # Should return None (no access)
        assert result is None, \
            "Tenant B should NOT be able to access Tenant A's model"

        cursor.close()
        conn.close()

        return True, "Cross-tenant model access blocked"
    except Exception as e:
        return False, str(e)


def test_04_get_predictions_filtered_by_tenant():
    """Test 4: Verify predictions query filtered by tenant"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get predictions for tenant A
        cursor.execute("""
            SELECT id, tenant_id, model_type, prediction_result
            FROM predictions
            WHERE tenant_id = %s
            ORDER BY created_at DESC
        """, (TENANT_A_ID,))

        predictions_a = cursor.fetchall()

        # Get predictions for tenant B
        cursor.execute("""
            SELECT id, tenant_id, model_type, prediction_result
            FROM predictions
            WHERE tenant_id = %s
            ORDER BY created_at DESC
        """, (TENANT_B_ID,))

        predictions_b = cursor.fetchall()

        # Assertions
        assert len(predictions_a) > 0, "Tenant A should have predictions"
        assert len(predictions_b) > 0, "Tenant B should have predictions"

        # Verify tenant isolation
        for pred in predictions_a:
            assert str(pred['tenant_id']) == TENANT_A_ID

        for pred in predictions_b:
            assert str(pred['tenant_id']) == TENANT_B_ID

        cursor.close()
        conn.close()

        return True, f"Tenant A: {len(predictions_a)} predictions, Tenant B: {len(predictions_b)} predictions"
    except Exception as e:
        return False, str(e)


def test_05_get_training_jobs_filtered_by_tenant():
    """Test 5: Verify training jobs query filtered by tenant"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get training jobs for tenant A
        cursor.execute("""
            SELECT id, tenant_id, model_type, status
            FROM training_jobs
            WHERE tenant_id = %s
            ORDER BY created_at DESC
        """, (TENANT_A_ID,))

        jobs_a = cursor.fetchall()

        # Get training jobs for tenant B
        cursor.execute("""
            SELECT id, tenant_id, model_type, status
            FROM training_jobs
            WHERE tenant_id = %s
            ORDER BY created_at DESC
        """, (TENANT_B_ID,))

        jobs_b = cursor.fetchall()

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

        cursor.close()
        conn.close()

        return True, f"Tenant A: {len(jobs_a)} jobs, Tenant B: {len(jobs_b)} jobs"
    except Exception as e:
        return False, str(e)


def test_06_insert_model_with_tenant_id():
    """Test 6: Verify new model automatically gets tenant_id"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Create new model for tenant A
        new_model_id = str(uuid.uuid4())
        mlflow_run_id = f"test_run_{int(time.time())}"

        cursor.execute("""
            INSERT INTO ml_models
            (id, tenant_id, model_type, model_name, model_version, mlflow_run_id, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id, tenant_id
        """, (new_model_id, TENANT_A_ID, 'test_model', 'Test Model', '1.0', mlflow_run_id, 'training'))

        result = cursor.fetchone()

        # Verify insertion
        assert result is not None
        assert str(result['tenant_id']) == TENANT_A_ID

        # Verify it's not accessible by tenant B
        cursor.execute("""
            SELECT id FROM ml_models
            WHERE id = %s AND tenant_id = %s
        """, (new_model_id, TENANT_B_ID))

        cross_tenant_result = cursor.fetchone()
        assert cross_tenant_result is None

        # Cleanup
        cursor.execute("DELETE FROM ml_models WHERE id = %s", (new_model_id,))
        conn.commit()

        cursor.close()
        conn.close()

        return True, "Model created with correct tenant_id and isolated"
    except Exception as e:
        return False, str(e)


def test_07_update_model_respects_tenant_isolation():
    """Test 7: Verify updates respect tenant isolation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get a model from tenant A
        cursor.execute("""
            SELECT id, status FROM ml_models
            WHERE tenant_id = %s AND status = 'ready'
            LIMIT 1
        """, (TENANT_A_ID,))

        model_a = cursor.fetchone()
        assert model_a is not None

        model_id = model_a['id']

        # Try to update as tenant A (should succeed)
        cursor.execute("""
            UPDATE ml_models
            SET status = 'deprecated'
            WHERE id = %s AND tenant_id = %s
        """, (model_id, TENANT_A_ID))

        assert cursor.rowcount == 1, "Update should affect 1 row"

        # Try to update the same model as tenant B (should fail)
        cursor.execute("""
            UPDATE ml_models
            SET status = 'ready'
            WHERE id = %s AND tenant_id = %s
        """, (model_id, TENANT_B_ID))

        assert cursor.rowcount == 0, "Tenant B should not be able to update Tenant A's model"

        # Rollback changes
        conn.rollback()

        cursor.close()
        conn.close()

        return True, "Updates respect tenant isolation"
    except Exception as e:
        return False, str(e)


def test_08_delete_model_respects_tenant_isolation():
    """Test 8: Verify deletes respect tenant isolation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Create a test model for tenant A
        test_model_id = str(uuid.uuid4())
        mlflow_run_id = f"test_delete_{int(time.time())}"

        cursor.execute("""
            INSERT INTO ml_models
            (id, tenant_id, model_type, model_name, model_version, mlflow_run_id, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """, (test_model_id, TENANT_A_ID, 'test_model', 'Test Delete Model', '1.0', mlflow_run_id, 'training'))

        # Try to delete as tenant B (should fail)
        cursor.execute("""
            DELETE FROM ml_models
            WHERE id = %s AND tenant_id = %s
        """, (test_model_id, TENANT_B_ID))

        assert cursor.rowcount == 0, "Tenant B should not be able to delete Tenant A's model"

        # Verify model still exists
        cursor.execute("""
            SELECT id FROM ml_models WHERE id = %s
        """, (test_model_id,))

        assert cursor.fetchone() is not None, "Model should still exist"

        # Delete as tenant A (should succeed)
        cursor.execute("""
            DELETE FROM ml_models
            WHERE id = %s AND tenant_id = %s
        """, (test_model_id, TENANT_A_ID))

        assert cursor.rowcount == 1, "Tenant A should be able to delete its own model"

        conn.commit()

        cursor.close()
        conn.close()

        return True, "Deletes respect tenant isolation"
    except Exception as e:
        return False, str(e)


def test_09_complex_join_query_with_tenant_filter():
    """Test 9: Verify complex JOIN queries maintain tenant isolation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Query models with predictions (JOIN) for tenant A
        cursor.execute("""
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

        results_a = cursor.fetchall()

        # Verify all results belong to tenant A
        assert len(results_a) > 0
        for row in results_a:
            assert str(row['tenant_id']) == TENANT_A_ID

        # Same query for tenant B
        cursor.execute("""
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

        results_b = cursor.fetchall()

        # Verify all results belong to tenant B
        for row in results_b:
            assert str(row['tenant_id']) == TENANT_B_ID

        cursor.close()
        conn.close()

        return True, f"JOIN queries maintain tenant isolation (A: {len(results_a)} models, B: {len(results_b)} models)"
    except Exception as e:
        return False, str(e)


def test_10_model_metadata_tenant_isolation():
    """Test 10: Verify model metadata respects tenant isolation via model FK"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get model metadata for tenant A models
        cursor.execute("""
            SELECT mm.id, mm.key, mm.value, m.tenant_id
            FROM model_metadata mm
            JOIN ml_models m ON mm.model_id = m.id
            WHERE m.tenant_id = %s
        """, (TENANT_A_ID,))

        metadata_a = cursor.fetchall()

        # Get model metadata for tenant B models
        cursor.execute("""
            SELECT mm.id, mm.key, mm.value, m.tenant_id
            FROM model_metadata mm
            JOIN ml_models m ON mm.model_id = m.id
            WHERE m.tenant_id = %s
        """, (TENANT_B_ID,))

        metadata_b = cursor.fetchall()

        # Assertions
        assert len(metadata_a) > 0, "Tenant A should have model metadata"
        assert len(metadata_b) > 0, "Tenant B should have model metadata"

        # Verify isolation
        for meta in metadata_a:
            assert str(meta['tenant_id']) == TENANT_A_ID

        for meta in metadata_b:
            assert str(meta['tenant_id']) == TENANT_B_ID

        cursor.close()
        conn.close()

        return True, f"Model metadata respects tenant isolation (A: {len(metadata_a)} entries, B: {len(metadata_b)} entries)"
    except Exception as e:
        return False, str(e)


def test_11_concurrent_tenant_access():
    """Test 11: Verify concurrent access from multiple tenants works correctly"""
    try:
        results = {'tenant_a': None, 'tenant_b': None, 'errors': []}

        def query_tenant_a():
            try:
                conn = get_db_connection()
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
                conn = get_db_connection()
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

        return True, f"Concurrent access works correctly (A: {results['tenant_a']} models, B: {results['tenant_b']} models)"
    except Exception as e:
        return False, str(e)


def test_12_training_data_query_with_tenant_filter():
    """Test 12: Verify training data queries include tenant_id filter"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Simulate loading training data for cost forecasting model
        cursor.execute("""
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

        training_data_a = cursor.fetchall()

        # Verify results
        assert len(training_data_a) > 0, "Should find completed training jobs for tenant A"

        for job in training_data_a:
            assert str(job['tenant_id']) == TENANT_A_ID
            assert job['model_type'] == 'cost_forecasting'
            assert job['status'] == 'completed'

        cursor.close()
        conn.close()

        return True, f"Training data queries filtered by tenant (found {len(training_data_a)} completed jobs)"
    except Exception as e:
        return False, str(e)


def test_13_query_performance_with_tenant_filter():
    """Test 13: Verify query performance with tenant_id filter (indexed)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Test query performance with index
        start_time = time.time()

        cursor.execute("""
            SELECT id, model_type, status
            FROM ml_models
            WHERE tenant_id = %s
        """, (TENANT_A_ID,))

        results = cursor.fetchall()
        elapsed_time = time.time() - start_time

        # Performance should be fast (< 100ms for this small dataset)
        assert elapsed_time < 0.1, f"Query took too long: {elapsed_time:.3f}s"

        cursor.close()
        conn.close()

        return True, f"Query performed in {elapsed_time*1000:.2f}ms"
    except Exception as e:
        return False, str(e)


def run_all_tests():
    """Run all integration tests"""
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}")
    print(f"{BOLD}{BLUE}PHASE 1 DAY 4: DATABASE INTEGRATION TESTS{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 80}{RESET}\n")

    tests = [
        ("Test 1: Get models filtered by tenant A", test_01_get_models_filtered_by_tenant_a),
        ("Test 2: Get models filtered by tenant B", test_02_get_models_filtered_by_tenant_b),
        ("Test 3: Cross-tenant model access blocked", test_03_cross_tenant_model_access_blocked),
        ("Test 4: Get predictions filtered by tenant", test_04_get_predictions_filtered_by_tenant),
        ("Test 5: Get training jobs filtered by tenant", test_05_get_training_jobs_filtered_by_tenant),
        ("Test 6: Insert model with tenant_id", test_06_insert_model_with_tenant_id),
        ("Test 7: Update model respects tenant isolation", test_07_update_model_respects_tenant_isolation),
        ("Test 8: Delete model respects tenant isolation", test_08_delete_model_respects_tenant_isolation),
        ("Test 9: Complex JOIN query with tenant filter", test_09_complex_join_query_with_tenant_filter),
        ("Test 10: Model metadata tenant isolation", test_10_model_metadata_tenant_isolation),
        ("Test 11: Concurrent tenant access", test_11_concurrent_tenant_access),
        ("Test 12: Training data query with tenant filter", test_12_training_data_query_with_tenant_filter),
        ("Test 13: Query performance with tenant filter", test_13_query_performance_with_tenant_filter),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"{BOLD}{test_name}{RESET}")
        try:
            passed, message = test_func()
            if passed:
                print(f"{GREEN}✓ PASSED: {message}{RESET}\n")
                results.append(True)
            else:
                print(f"{RED}✗ FAILED: {message}{RESET}\n")
                results.append(False)
        except Exception as e:
            print(f"{RED}✗ ERROR: {e}{RESET}\n")
            results.append(False)

    # Summary
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}")
    print(f"{BOLD}{BLUE}TEST SUMMARY{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 80}{RESET}\n")

    passed = sum(results)
    failed = len(results) - passed
    pass_rate = (passed / len(results)) * 100

    print(f"Total Tests:   {len(results)}")
    print(f"{GREEN}Passed:        {passed}{RESET}")
    print(f"{RED}Failed:        {failed}{RESET}")
    print(f"Pass Rate:     {pass_rate:.1f}%\n")

    if failed == 0:
        print(f"{BOLD}{GREEN}{'=' * 80}{RESET}")
        print(f"{BOLD}{GREEN}ALL TESTS PASSED - DATABASE TENANT ISOLATION VERIFIED ✓{RESET}")
        print(f"{BOLD}{GREEN}{'=' * 80}{RESET}\n")
        return 0
    else:
        print(f"{BOLD}{RED}{'=' * 80}{RESET}")
        print(f"{BOLD}{RED}SOME TESTS FAILED - REVIEW ISSUES{RESET}")
        print(f"{BOLD}{RED}{'=' * 80}{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
