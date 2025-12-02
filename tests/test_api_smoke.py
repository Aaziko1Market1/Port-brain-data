"""
EPIC 7B - API Smoke Tests
==========================
Quick tests to verify API endpoints work correctly.

Run with: python tests/test_api_smoke.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ['DB_CONFIG_PATH'] = 'config/db_config.yml'

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


@pytest.fixture
def buyer_uuid():
    """Fixture that provides a buyer_uuid from the buyers list."""
    response = client.get("/api/v1/buyers?limit=1")
    if response.status_code == 200:
        data = response.json()
        if data["items"]:
            return data["items"][0]["buyer_uuid"]
    pytest.skip("No buyers available in database for testing")


def test_root():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    print("✓ Root endpoint OK")
    return True


def test_health():
    """Test health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
    print(f"✓ Health check OK - DB: {data['db']}")
    return True


def test_meta_stats():
    """Test meta stats endpoint."""
    response = client.get("/api/v1/meta/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_shipments" in data
    assert "total_buyers" in data
    print(f"✓ Meta stats OK - {data['total_shipments']} shipments, {data['total_buyers']} buyers")
    return True


def test_buyers_list():
    """Test buyers list endpoint."""
    response = client.get("/api/v1/buyers?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) <= 5
    print(f"✓ Buyers list OK - {data['total']} total, {len(data['items'])} returned")
    
    # Check no NULL buyer_uuid
    for item in data["items"]:
        assert item["buyer_uuid"] is not None, "Found NULL buyer_uuid!"
    print("✓ No NULL buyer_uuid in results")
    return data


def test_buyer_360(buyer_uuid: str):
    """Test buyer 360 endpoint."""
    response = client.get(f"/api/v1/buyers/{buyer_uuid}/360")
    assert response.status_code == 200
    data = response.json()
    assert data["buyer_uuid"] == buyer_uuid
    assert "total_shipments" in data
    assert "top_hs_codes" in data
    print(f"✓ Buyer 360 OK - {data['buyer_name']}: {data['total_shipments']} shipments")
    return True


def test_hs_dashboard():
    """Test HS dashboard endpoint."""
    response = client.get("/api/v1/hs-dashboard?hs_code_6=690721")
    assert response.status_code == 200
    data = response.json()
    assert data["hs_code_6"] == "690721"
    print(f"✓ HS Dashboard OK - HS 690721: {data['total_shipments']} shipments")
    return True


def test_risk_top_shipments():
    """Test top risky shipments endpoint."""
    response = client.get("/api/v1/risk/top-shipments?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    print(f"✓ Risk shipments OK - {data['total']} total, {len(data['items'])} returned")
    return True


def test_risk_top_buyers():
    """Test top risky buyers endpoint."""
    response = client.get("/api/v1/risk/top-buyers?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    print(f"✓ Risk buyers OK - {data['total']} total, {len(data['items'])} returned")
    return True


def test_risk_summary():
    """Test risk summary endpoint."""
    response = client.get("/api/v1/risk/summary")
    assert response.status_code == 200
    data = response.json()
    assert "SHIPMENT" in data
    assert "BUYER" in data
    print(f"✓ Risk summary OK - Shipment risks: {data['totals']['SHIPMENT']}, Buyer risks: {data['totals']['BUYER']}")
    return True


def test_sql_injection_safety():
    """Test that SQL injection attempts are safe."""
    # Try some injection patterns - they should not crash and return 0 results
    dangerous_inputs = [
        "'; DROP TABLE --",
        "1; DELETE FROM risk_scores;--",
        "' OR '1'='1",
        "1 UNION SELECT * FROM pipeline_runs--"
    ]
    
    for payload in dangerous_inputs:
        response = client.get(f"/api/v1/buyers?country={payload}")
        # Should return 200 with empty results, not crash
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0  # No results for garbage input
    
    print("✓ SQL injection safety OK - Parameterized queries working")
    return True


def run_all_tests():
    """Run all smoke tests."""
    print()
    print("=" * 70)
    print("  EPIC 7B - API SMOKE TESTS")
    print("=" * 70)
    print()
    
    passed = 0
    failed = 0
    
    tests = [
        ("Root endpoint", test_root),
        ("Health check", test_health),
        ("Meta stats", test_meta_stats),
        ("Buyers list", lambda: test_buyers_list()),
        ("HS Dashboard", test_hs_dashboard),
        ("Risk top shipments", test_risk_top_shipments),
        ("Risk top buyers", test_risk_top_buyers),
        ("Risk summary", test_risk_summary),
        ("SQL injection safety", test_sql_injection_safety),
    ]
    
    buyer_uuid = None
    
    for name, test_fn in tests:
        try:
            result = test_fn()
            passed += 1
            # Save buyer_uuid for 360 test
            if name == "Buyers list" and result and result["items"]:
                buyer_uuid = result["items"][0]["buyer_uuid"]
        except Exception as e:
            print(f"✗ {name} FAILED: {e}")
            failed += 1
    
    # Run buyer 360 test with actual UUID
    if buyer_uuid:
        try:
            test_buyer_360(buyer_uuid)
            passed += 1
        except Exception as e:
            print(f"✗ Buyer 360 FAILED: {e}")
            failed += 1
    
    print()
    print("=" * 70)
    print(f"  RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    print()
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
