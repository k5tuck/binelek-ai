#!/usr/bin/env python3
"""
Comprehensive Authentication Testing Script for binah-ml Service

Tests all authentication scenarios for Phase 1, Week 1, Day 2:
1. Unauthenticated access (should fail with 401/403)
2. Authenticated access with valid token (should succeed)
3. Tenant isolation (cross-tenant access should fail)
4. Expired token (should fail with 401)
5. Invalid/malformed tokens (should fail with 401)
6. Missing required claims (should fail with 401)
7. Invalid issuer/audience (should fail with 401)

Usage:
    python3 test_authentication.py

Requirements:
    - binah-ml service running on http://localhost:8098
    - python-jose[cryptography] installed
"""

import requests
import json
from datetime import datetime, timedelta
from jose import jwt
from typing import Dict, List, Tuple
import sys

# Test configuration
BASE_URL = "http://localhost:8098"
JWT_SECRET = "your-super-secret-key-change-this-in-production-at-least-32-characters-long"
JWT_ISSUER = "Binah.Auth"
JWT_AUDIENCE = "Binah.Platform"
JWT_ALGORITHM = "HS256"

# ANSI color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results: List[Tuple[str, bool, str]] = []

    def add(self, test_name: str, passed: bool, message: str = ""):
        self.results.append((test_name, passed, message))
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def print_summary(self):
        print("\n" + "=" * 80)
        print(f"{BOLD}TEST SUMMARY{RESET}")
        print("=" * 80)

        for test_name, passed, message in self.results:
            status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
            print(f"{status} - {test_name}")
            if message:
                print(f"       {message}")

        print("\n" + "-" * 80)
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0

        if self.failed == 0:
            color = GREEN
        elif pass_rate >= 70:
            color = YELLOW
        else:
            color = RED

        print(f"{BOLD}Total Tests:{RESET} {total}")
        print(f"{GREEN}{BOLD}Passed:{RESET} {self.passed}")
        print(f"{RED}{BOLD}Failed:{RESET} {self.failed}")
        print(f"{color}{BOLD}Pass Rate:{RESET} {pass_rate:.1f}%")
        print("=" * 80 + "\n")


def generate_token(
    user_id: str = "test-user-123",
    tenant_id: str = "test-tenant-456",
    email: str = "test@example.com",
    username: str = "testuser",
    role: str = "admin",
    expiration_minutes: int = 15,
    issuer: str = JWT_ISSUER,
    audience: str = JWT_AUDIENCE
) -> str:
    """Generate a JWT token for testing"""
    now = datetime.utcnow()

    claims = {
        "sub": user_id,
        "name": username,
        "email": email,
        "role": role,
        "tenant_id": tenant_id,
        "iat": now,
        "exp": now + timedelta(minutes=expiration_minutes),
        "iss": issuer,
        "aud": audience
    }

    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)


def test_service_running(results: TestResult) -> bool:
    """Test 0: Verify service is running"""
    print(f"\n{BLUE}{BOLD}TEST 0: Service Health Check{RESET}")
    print("-" * 80)

    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"{GREEN}✓ Service is running{RESET}")
            print(f"  Version: {data.get('version')}")
            print(f"  Status: {data.get('status')}")
            results.add("Service health check", True, "Service running correctly")
            return True
        else:
            print(f"{RED}✗ Service returned status {response.status_code}{RESET}")
            results.add("Service health check", False, f"Status code: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"{RED}✗ Cannot connect to service: {e}{RESET}")
        results.add("Service health check", False, f"Connection error: {str(e)}")
        return False


def test_unauthenticated_access(results: TestResult):
    """Test 1: Unauthenticated access should fail"""
    print(f"\n{BLUE}{BOLD}TEST 1: Unauthenticated Access (Should Fail with 403){RESET}")
    print("-" * 80)

    # Test /me endpoint without token
    try:
        response = requests.get(f"{BASE_URL}/me", timeout=5)
        if response.status_code == 403:
            print(f"{GREEN}✓ /me endpoint correctly rejected unauthenticated request (403){RESET}")
            results.add("Unauthenticated /me endpoint", True, "Correctly returned 403")
        else:
            print(f"{RED}✗ /me endpoint returned {response.status_code}, expected 403{RESET}")
            print(f"  Response: {response.text[:200]}")
            results.add("Unauthenticated /me endpoint", False, f"Got {response.status_code} instead of 403")
    except requests.RequestException as e:
        print(f"{RED}✗ Request failed: {e}{RESET}")
        results.add("Unauthenticated /me endpoint", False, f"Request error: {str(e)}")


def test_authenticated_access(results: TestResult):
    """Test 2: Authenticated access with valid token"""
    print(f"\n{BLUE}{BOLD}TEST 2: Authenticated Access with Valid Token{RESET}")
    print("-" * 80)

    # Generate valid token
    token = generate_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Test /me endpoint
    try:
        response = requests.get(f"{BASE_URL}/me", headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"{GREEN}✓ /me endpoint accepted valid token{RESET}")
            print(f"  User ID: {data.get('user_id')}")
            print(f"  Tenant ID: {data.get('tenant_id')}")
            print(f"  Email: {data.get('email')}")
            print(f"  Role: {data.get('role')}")

            # Verify correct data returned
            if data.get('tenant_id') == 'test-tenant-456' and data.get('user_id') == 'test-user-123':
                results.add("Authenticated /me endpoint", True, "Token validated, correct data returned")
            else:
                results.add("Authenticated /me endpoint", False, "Token validated but wrong data returned")
        else:
            print(f"{RED}✗ /me endpoint returned {response.status_code}, expected 200{RESET}")
            print(f"  Response: {response.text[:200]}")
            results.add("Authenticated /me endpoint", False, f"Got {response.status_code} instead of 200")
    except requests.RequestException as e:
        print(f"{RED}✗ Request failed: {e}{RESET}")
        results.add("Authenticated /me endpoint", False, f"Request error: {str(e)}")

    # Test /health endpoint
    try:
        response = requests.get(f"{BASE_URL}/health", headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"{GREEN}✓ /health endpoint accessible{RESET}")
            print(f"  Status: {data.get('status')}")
            print(f"  Authentication: {data.get('authentication_enabled')}")
            results.add("Authenticated /health endpoint", True, "Health check successful")
        else:
            print(f"{RED}✗ /health returned {response.status_code}{RESET}")
            results.add("Authenticated /health endpoint", False, f"Got {response.status_code}")
    except requests.RequestException as e:
        print(f"{RED}✗ Request failed: {e}{RESET}")
        results.add("Authenticated /health endpoint", False, f"Request error: {str(e)}")


def test_tenant_isolation(results: TestResult):
    """Test 3: Cross-tenant access should fail"""
    print(f"\n{BLUE}{BOLD}TEST 3: Tenant Isolation (Cross-Tenant Access){RESET}")
    print("-" * 80)

    # Generate token for different tenant
    different_tenant_token = generate_token(
        user_id="different-user-789",
        tenant_id="different-tenant-789",
        email="different@example.com"
    )
    headers = {"Authorization": f"Bearer {different_tenant_token}"}

    # Try to access /me endpoint (should work, showing different tenant)
    try:
        response = requests.get(f"{BASE_URL}/me", headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('tenant_id') == 'different-tenant-789':
                print(f"{GREEN}✓ Token validated for different tenant{RESET}")
                print(f"  Tenant ID: {data.get('tenant_id')}")
                results.add("Different tenant token validation", True, "Correctly validated different tenant")
            else:
                print(f"{RED}✗ Tenant ID mismatch in response{RESET}")
                results.add("Different tenant token validation", False, "Tenant ID mismatch")
        else:
            print(f"{RED}✗ Different tenant token rejected unexpectedly: {response.status_code}{RESET}")
            results.add("Different tenant token validation", False, f"Unexpected rejection: {response.status_code}")
    except requests.RequestException as e:
        print(f"{RED}✗ Request failed: {e}{RESET}")
        results.add("Different tenant token validation", False, f"Request error: {str(e)}")

    print(f"\n{YELLOW}Note: Full tenant isolation test requires ML endpoints{RESET}")
    print(f"{YELLOW}      ML router is disabled in current authentication-testing mode{RESET}")


def test_expired_token(results: TestResult):
    """Test 4: Expired token should fail"""
    print(f"\n{BLUE}{BOLD}TEST 4: Expired Token (Should Fail){RESET}")
    print("-" * 80)

    # Generate expired token
    expired_token = generate_token(expiration_minutes=-5)  # Expired 5 minutes ago
    headers = {"Authorization": f"Bearer {expired_token}"}

    try:
        response = requests.get(f"{BASE_URL}/me", headers=headers, timeout=5)
        if response.status_code == 401:
            print(f"{GREEN}✓ Expired token correctly rejected (401){RESET}")
            try:
                error_data = response.json()
                print(f"  Error: {error_data.get('detail', 'No detail provided')}")
            except:
                pass
            results.add("Expired token rejection", True, "Correctly returned 401")
        else:
            print(f"{RED}✗ Expired token returned {response.status_code}, expected 401{RESET}")
            print(f"  Response: {response.text[:200]}")
            results.add("Expired token rejection", False, f"Got {response.status_code} instead of 401")
    except requests.RequestException as e:
        print(f"{RED}✗ Request failed: {e}{RESET}")
        results.add("Expired token rejection", False, f"Request error: {str(e)}")


def test_invalid_tokens(results: TestResult):
    """Test 5: Invalid/malformed tokens should fail"""
    print(f"\n{BLUE}{BOLD}TEST 5: Invalid/Malformed Tokens{RESET}")
    print("-" * 80)

    # Test 5a: Completely invalid token
    print("\n  5a. Malformed token:")
    headers = {"Authorization": "Bearer invalid.token.here"}
    try:
        response = requests.get(f"{BASE_URL}/me", headers=headers, timeout=5)
        if response.status_code == 401:
            print(f"  {GREEN}✓ Malformed token rejected (401){RESET}")
            results.add("Malformed token rejection", True, "Correctly returned 401")
        else:
            print(f"  {RED}✗ Malformed token returned {response.status_code}{RESET}")
            results.add("Malformed token rejection", False, f"Got {response.status_code}")
    except requests.RequestException as e:
        print(f"  {RED}✗ Request failed: {e}{RESET}")
        results.add("Malformed token rejection", False, f"Request error: {str(e)}")

    # Test 5b: Token with wrong secret
    print("\n  5b. Token with wrong secret:")
    wrong_secret_token = jwt.encode(
        {
            "sub": "test-user",
            "tenant_id": "test-tenant",
            "email": "test@example.com",
            "role": "admin",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=15),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE
        },
        "wrong-secret-key",
        algorithm=JWT_ALGORITHM
    )
    headers = {"Authorization": f"Bearer {wrong_secret_token}"}
    try:
        response = requests.get(f"{BASE_URL}/me", headers=headers, timeout=5)
        if response.status_code == 401:
            print(f"  {GREEN}✓ Wrong secret token rejected (401){RESET}")
            results.add("Wrong secret token rejection", True, "Correctly returned 401")
        else:
            print(f"  {RED}✗ Wrong secret token returned {response.status_code}{RESET}")
            results.add("Wrong secret token rejection", False, f"Got {response.status_code}")
    except requests.RequestException as e:
        print(f"  {RED}✗ Request failed: {e}{RESET}")
        results.add("Wrong secret token rejection", False, f"Request error: {str(e)}")


def test_missing_claims(results: TestResult):
    """Test 6: Tokens missing required claims should fail"""
    print(f"\n{BLUE}{BOLD}TEST 6: Missing Required Claims{RESET}")
    print("-" * 80)

    # Test 6a: Missing tenant_id claim
    print("\n  6a. Missing tenant_id claim:")
    token_no_tenant = jwt.encode(
        {
            "sub": "test-user-123",
            "email": "test@example.com",
            "role": "admin",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=15),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )
    headers = {"Authorization": f"Bearer {token_no_tenant}"}
    try:
        response = requests.get(f"{BASE_URL}/me", headers=headers, timeout=5)
        if response.status_code == 401:
            print(f"  {GREEN}✓ Token missing tenant_id rejected (401){RESET}")
            results.add("Missing tenant_id rejection", True, "Correctly returned 401")
        else:
            print(f"  {RED}✗ Token missing tenant_id returned {response.status_code}{RESET}")
            results.add("Missing tenant_id rejection", False, f"Got {response.status_code}")
    except requests.RequestException as e:
        print(f"  {RED}✗ Request failed: {e}{RESET}")
        results.add("Missing tenant_id rejection", False, f"Request error: {str(e)}")

    # Test 6b: Missing sub (user_id) claim
    print("\n  6b. Missing sub claim:")
    token_no_sub = jwt.encode(
        {
            "tenant_id": "test-tenant-456",
            "email": "test@example.com",
            "role": "admin",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=15),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )
    headers = {"Authorization": f"Bearer {token_no_sub}"}
    try:
        response = requests.get(f"{BASE_URL}/me", headers=headers, timeout=5)
        if response.status_code == 401:
            print(f"  {GREEN}✓ Token missing sub rejected (401){RESET}")
            results.add("Missing sub rejection", True, "Correctly returned 401")
        else:
            print(f"  {RED}✗ Token missing sub returned {response.status_code}{RESET}")
            results.add("Missing sub rejection", False, f"Got {response.status_code}")
    except requests.RequestException as e:
        print(f"  {RED}✗ Request failed: {e}{RESET}")
        results.add("Missing sub rejection", False, f"Request error: {str(e)}")


def test_invalid_issuer_audience(results: TestResult):
    """Test 7: Invalid issuer/audience should fail"""
    print(f"\n{BLUE}{BOLD}TEST 7: Invalid Issuer/Audience{RESET}")
    print("-" * 80)

    # Test 7a: Wrong issuer
    print("\n  7a. Wrong issuer:")
    wrong_issuer_token = generate_token(issuer="Wrong.Issuer")
    headers = {"Authorization": f"Bearer {wrong_issuer_token}"}
    try:
        response = requests.get(f"{BASE_URL}/me", headers=headers, timeout=5)
        if response.status_code == 401:
            print(f"  {GREEN}✓ Wrong issuer token rejected (401){RESET}")
            results.add("Wrong issuer rejection", True, "Correctly returned 401")
        else:
            print(f"  {RED}✗ Wrong issuer token returned {response.status_code}{RESET}")
            results.add("Wrong issuer rejection", False, f"Got {response.status_code}")
    except requests.RequestException as e:
        print(f"  {RED}✗ Request failed: {e}{RESET}")
        results.add("Wrong issuer rejection", False, f"Request error: {str(e)}")

    # Test 7b: Wrong audience
    print("\n  7b. Wrong audience:")
    wrong_audience_token = generate_token(audience="Wrong.Audience")
    headers = {"Authorization": f"Bearer {wrong_audience_token}"}
    try:
        response = requests.get(f"{BASE_URL}/me", headers=headers, timeout=5)
        if response.status_code == 401:
            print(f"  {GREEN}✓ Wrong audience token rejected (401){RESET}")
            results.add("Wrong audience rejection", True, "Correctly returned 401")
        else:
            print(f"  {RED}✗ Wrong audience token returned {response.status_code}{RESET}")
            results.add("Wrong audience rejection", False, f"Got {response.status_code}")
    except requests.RequestException as e:
        print(f"  {RED}✗ Request failed: {e}{RESET}")
        results.add("Wrong audience rejection", False, f"Request error: {str(e)}")


def main():
    """Run all authentication tests"""
    print(f"\n{BOLD}{'=' * 80}{RESET}")
    print(f"{BOLD}BINAH-ML AUTHENTICATION TESTING SUITE{RESET}")
    print(f"{BOLD}Phase 1, Week 1, Day 2 - Manual Endpoint Security Testing{RESET}")
    print(f"{BOLD}{'=' * 80}{RESET}")

    results = TestResult()

    # Test 0: Service health
    if not test_service_running(results):
        print(f"\n{RED}{BOLD}ERROR: Service is not running. Please start binah-ml service first.{RESET}")
        print(f"\nTo start the service:")
        print(f"  cd /home/user/Binelek/services/binah-ml")
        print(f"  PYTHONPATH=/home/user/Binelek/services/binah-ml python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8098")
        sys.exit(1)

    # Run all test suites
    test_unauthenticated_access(results)
    test_authenticated_access(results)
    test_tenant_isolation(results)
    test_expired_token(results)
    test_invalid_tokens(results)
    test_missing_claims(results)
    test_invalid_issuer_audience(results)

    # Print summary
    results.print_summary()

    # Return exit code based on results
    sys.exit(0 if results.failed == 0 else 1)


if __name__ == "__main__":
    main()
