"""
Integration Tests for Tenant Isolation in Binah ML Service

Tests verify that:
1. Requests are properly authenticated with JWT
2. Tenant context is extracted from JWT (not request body)
3. Users cannot access or modify other tenants' data
4. All ML operations are tenant-isolated

Run with:
    cd /home/user/Binelek/services/binah-ml
    python3 test_tenant_isolation.py
"""

import requests
import json
from datetime import datetime, timedelta
from jose import jwt
from uuid import uuid4
import sys

# Configuration
BASE_URL = "http://localhost:8098"
JWT_SECRET = "your-super-secret-key-change-this-in-production-at-least-32-characters-long"
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "Binah.Auth"
JWT_AUDIENCE = "Binah.Platform"

# Test tenant IDs (must be valid UUIDs)
TENANT_A_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TENANT_B_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_test_header(test_name):
    """Print test header"""
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}")
    print(f"{BOLD}{BLUE}TEST: {test_name}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 80}{RESET}\n")


def print_success(message):
    """Print success message"""
    print(f"{GREEN}✓ {message}{RESET}")


def print_error(message):
    """Print error message"""
    print(f"{RED}✗ {message}{RESET}")


def print_info(message):
    """Print info message"""
    print(f"{YELLOW}ℹ {message}{RESET}")


def generate_token(
    user_id: str = "test-user-123",
    tenant_id: str = "test-tenant-456",
    email: str = "test@example.com",
    role: str = "admin",
    expiration_minutes: int = 15
) -> str:
    """Generate a JWT token for testing"""
    now = datetime.utcnow()
    claims = {
        "sub": user_id,
        "name": "testuser",
        "email": email,
        "role": role,
        "tenant_id": tenant_id,  # CRITICAL: snake_case, matches binah-auth
        "iat": now,
        "exp": now + timedelta(minutes=expiration_minutes),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE
    }
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)


def test_01_unauthenticated_access():
    """Test 1: Verify unauthenticated requests are rejected"""
    print_test_header("Test 1: Unauthenticated Access Rejection")

    try:
        response = requests.get(f"{BASE_URL}/api/ml/health")

        if response.status_code == 403:
            print_success(f"Unauthenticated request correctly rejected: {response.status_code}")
            return True
        else:
            print_error(f"Expected 403, got {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
    except Exception as e:
        print_error(f"Test failed with exception: {e}")
        return False


def test_02_authenticated_access_tenant_a():
    """Test 2: Verify authenticated access works for Tenant A"""
    print_test_header("Test 2: Authenticated Access - Tenant A")

    try:
        tenant_a_token = generate_token(
            user_id="user-a-001",
            tenant_id=TENANT_A_ID,
            email="user.a@tenant-a.com"
        )

        headers = {"Authorization": f"Bearer {tenant_a_token}"}
        response = requests.get(f"{BASE_URL}/api/ml/health", headers=headers)

        if response.status_code == 200:
            data = response.json()
            print_success(f"Authenticated request successful: {response.status_code}")
            print_info(f"Service: {data.get('service')}")
            print_info(f"Authenticated Tenant: {data.get('authenticated_tenant')}")

            if data.get('authenticated_tenant') == TENANT_A_ID:
                print_success("Tenant context correctly extracted from JWT")
                return True
            else:
                print_error(f"Expected tenant '{TENANT_A_ID}', got '{data.get('authenticated_tenant')}'")
                return False
        else:
            print_error(f"Expected 200, got {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
    except Exception as e:
        print_error(f"Test failed with exception: {e}")
        return False


def test_03_authenticated_access_tenant_b():
    """Test 3: Verify authenticated access works for Tenant B"""
    print_test_header("Test 3: Authenticated Access - Tenant B")

    try:
        tenant_b_token = generate_token(
            user_id="user-b-001",
            tenant_id=TENANT_B_ID,
            email="user.b@tenant-b.com"
        )

        headers = {"Authorization": f"Bearer {tenant_b_token}"}
        response = requests.get(f"{BASE_URL}/api/ml/health", headers=headers)

        if response.status_code == 200:
            data = response.json()
            print_success(f"Authenticated request successful: {response.status_code}")
            print_info(f"Authenticated Tenant: {data.get('authenticated_tenant')}")

            if data.get('authenticated_tenant') == TENANT_B_ID:
                print_success("Tenant context correctly extracted for different tenant")
                return True
            else:
                print_error(f"Expected tenant '{TENANT_B_ID}', got '{data.get('authenticated_tenant')}'")
                return False
        else:
            print_error(f"Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Test failed with exception: {e}")
        return False


def test_04_tenant_isolation_prediction_request():
    """Test 4: Verify tenant_id in request body must match JWT tenant_id"""
    print_test_header("Test 4: Tenant Isolation - Prediction Request Body Validation")

    try:
        # User from Tenant A tries to make prediction for Tenant B (should fail)
        tenant_a_token = generate_token(
            user_id="user-a-001",
            tenant_id=TENANT_A_ID,
            email="user.a@tenant-a.com"
        )

        headers = {"Authorization": f"Bearer {tenant_a_token}"}
        payload = {
            "model_type": "cost_forecasting",
            "tenant_id": TENANT_B_ID,  # DIFFERENT tenant - should be rejected
            "features": {
                "project_size_sqft": 5000,
                "num_units": 50,
                "location_tier": 2,
                "property_type": 1,
                "year": 2024
            }
        }

        response = requests.post(f"{BASE_URL}/api/ml/predict", headers=headers, json=payload)

        if response.status_code == 403:
            print_success(f"Cross-tenant request correctly rejected: {response.status_code}")
            print_info(f"Error: {response.json().get('detail')}")
            return True
        else:
            print_error(f"Expected 403 (Forbidden), got {response.status_code}")
            print_error(f"Security VIOLATION: User from tenant-a accessed tenant-b data!")
            print_error(f"Response: {response.text}")
            return False
    except Exception as e:
        print_error(f"Test failed with exception: {e}")
        return False


def test_05_tenant_isolation_training_request():
    """Test 5: Verify training requests are tenant-isolated"""
    print_test_header("Test 5: Tenant Isolation - Training Request Body Validation")

    try:
        # User from Tenant A tries to train model for Tenant B (should fail)
        tenant_a_token = generate_token(
            user_id="user-a-001",
            tenant_id=TENANT_A_ID,
            email="user.a@tenant-a.com"
        )

        headers = {"Authorization": f"Bearer {tenant_a_token}"}
        payload = {
            "model_type": "risk_assessment",
            "tenant_id": TENANT_B_ID,  # DIFFERENT tenant - should be rejected
            "hyperparameters": {
                "n_estimators": 100,
                "max_depth": 10
            },
            "validation_split": 0.2
        }

        response = requests.post(f"{BASE_URL}/api/ml/train", headers=headers, json=payload)

        if response.status_code == 403:
            print_success(f"Cross-tenant training request correctly rejected: {response.status_code}")
            print_info(f"Error: {response.json().get('detail')}")
            return True
        else:
            print_error(f"Expected 403 (Forbidden), got {response.status_code}")
            print_error(f"Security VIOLATION: User from tenant-a could train model for tenant-b!")
            print_error(f"Response: {response.text}")
            return False
    except Exception as e:
        print_error(f"Test failed with exception: {e}")
        return False


def test_06_valid_prediction_request_same_tenant():
    """Test 6: Verify prediction works when tenant_id matches JWT"""
    print_test_header("Test 6: Valid Prediction Request - Same Tenant")

    try:
        tenant_a_token = generate_token(
            user_id="user-a-001",
            tenant_id=TENANT_A_ID,
            email="user.a@tenant-a.com"
        )

        headers = {"Authorization": f"Bearer {tenant_a_token}"}
        payload = {
            "model_type": "cost_forecasting",
            "tenant_id": TENANT_A_ID,  # SAME tenant as JWT - should succeed
            "features": {
                "project_size_sqft": 5000,
                "num_units": 50,
                "location_tier": 2,
                "property_type": 1,
                "year": 2024
            }
        }

        response = requests.post(f"{BASE_URL}/api/ml/predict", headers=headers, json=payload)

        if response.status_code == 200:
            data = response.json()
            print_success(f"Prediction request successful: {response.status_code}")
            print_info(f"Model Type: {data.get('model_type')}")
            print_info(f"Tenant ID: {data.get('tenant_id')}")
            print_info(f"Prediction: {data.get('prediction')}")

            if data.get('tenant_id') == TENANT_A_ID:
                print_success("Response correctly includes tenant_id from JWT")
                return True
            else:
                print_error(f"Expected tenant '{TENANT_A_ID}', got '{data.get('tenant_id')}'")
                return False
        else:
            print_error(f"Expected 200, got {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
    except Exception as e:
        print_error(f"Test failed with exception: {e}")
        return False


def test_07_expired_token():
    """Test 7: Verify expired tokens are rejected"""
    print_test_header("Test 7: Expired Token Rejection")

    try:
        # Generate token that expired 5 minutes ago
        expired_token = generate_token(
            user_id="user-a-001",
            tenant_id=TENANT_A_ID,
            expiration_minutes=-5  # Expired
        )

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = requests.get(f"{BASE_URL}/api/ml/health", headers=headers)

        if response.status_code == 401:
            print_success(f"Expired token correctly rejected: {response.status_code}")
            return True
        else:
            print_error(f"Expected 401, got {response.status_code}")
            print_error(f"Security RISK: Expired token was accepted!")
            return False
    except Exception as e:
        print_error(f"Test failed with exception: {e}")
        return False


def run_all_tests():
    """Run all tenant isolation tests"""
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}")
    print(f"{BOLD}{BLUE}BINAH ML - TENANT ISOLATION INTEGRATION TESTS{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 80}{RESET}\n")

    print_info(f"Testing service at: {BASE_URL}")
    print_info(f"Timestamp: {datetime.utcnow().isoformat()}Z\n")

    tests = [
        test_01_unauthenticated_access,
        test_02_authenticated_access_tenant_a,
        test_03_authenticated_access_tenant_b,
        test_04_tenant_isolation_prediction_request,
        test_05_tenant_isolation_training_request,
        test_06_valid_prediction_request_same_tenant,
        test_07_expired_token
    ]

    results = []
    for test in tests:
        result = test()
        results.append(result)

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
        print(f"{BOLD}{GREEN}ALL TESTS PASSED - TENANT ISOLATION VERIFIED ✓{RESET}")
        print(f"{BOLD}{GREEN}{'=' * 80}{RESET}\n")
        return 0
    else:
        print(f"{BOLD}{RED}{'=' * 80}{RESET}")
        print(f"{BOLD}{RED}SOME TESTS FAILED - REVIEW SECURITY ISSUES{RESET}")
        print(f"{BOLD}{RED}{'=' * 80}{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
