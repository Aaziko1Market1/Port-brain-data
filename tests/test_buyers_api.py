"""
Tests for Buyers API endpoints (buyers.py router)
==================================================
Includes tests for:
- GET /api/v1/buyers
- GET /api/v1/buyers/{uuid}/360
- GET /api/v1/buyers/{uuid}/trade-history
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ['DB_CONFIG_PATH'] = 'config/db_config.yml'

from fastapi.testclient import TestClient
from api.main import app
from etl.db_utils import DatabaseManager

client = TestClient(app)

# Known Kenya buyer UUIDs from verified data
SAJ_UUID = "96769b86-0645-4f6d-a0a3-c1f9fb2b96c8"
TILE_CARPET_UUID = "7b0ca3e5-800a-433e-a6d3-ddfb9f5b3ba8"

# Known values from Kenya QA
SAJ_EXPECTED_VALUE = 5365233.64
SAJ_EXPECTED_SHIPMENTS = 81
TILE_CARPET_EXPECTED_VALUE = 4263227.24
TILE_CARPET_EXPECTED_SHIPMENTS = 74


def test_trade_history_returns_200():
    """Test trade history endpoint returns 200 for valid buyer."""
    response = client.get(f"/api/v1/buyers/{SAJ_UUID}/trade-history")
    assert response.status_code == 200
    data = response.json()
    
    assert data["buyer_uuid"] == SAJ_UUID
    assert data["buyer_name"] == "SAJ ENTERPRISES"
    assert data["currency"] == "USD"
    assert "months" in data
    assert data["total_months"] >= 1
    
    print(f"✓ trade-history returns 200 for SAJ ENTERPRISES")
    return True


def test_trade_history_monthly_sum_matches_total():
    """Test that sum of monthly values equals known total."""
    response = client.get(f"/api/v1/buyers/{SAJ_UUID}/trade-history")
    assert response.status_code == 200
    data = response.json()
    
    # Sum all monthly values
    api_total = sum(m["total_value_usd"] for m in data["months"])
    api_shipments = sum(m["shipment_count"] for m in data["months"])
    
    # Compare with known values (within $0.01 tolerance)
    value_diff = abs(api_total - SAJ_EXPECTED_VALUE)
    assert value_diff < 0.01, f"Value mismatch: API={api_total}, expected={SAJ_EXPECTED_VALUE}"
    
    assert api_shipments == SAJ_EXPECTED_SHIPMENTS, \
        f"Shipment count mismatch: API={api_shipments}, expected={SAJ_EXPECTED_SHIPMENTS}"
    
    print(f"✓ SAJ monthly sum ${api_total:,.2f} matches expected ${SAJ_EXPECTED_VALUE:,.2f}")
    return True


def test_trade_history_tile_carpet_accuracy():
    """Test trade history accuracy for TILE AND CARPET CENTRE."""
    response = client.get(f"/api/v1/buyers/{TILE_CARPET_UUID}/trade-history")
    assert response.status_code == 200
    data = response.json()
    
    assert data["buyer_name"] == "TILE AND CARPET CENTRE"
    
    api_total = sum(m["total_value_usd"] for m in data["months"])
    api_shipments = sum(m["shipment_count"] for m in data["months"])
    
    value_diff = abs(api_total - TILE_CARPET_EXPECTED_VALUE)
    assert value_diff < 0.01, f"Value mismatch: API={api_total}, expected={TILE_CARPET_EXPECTED_VALUE}"
    
    assert api_shipments == TILE_CARPET_EXPECTED_SHIPMENTS, \
        f"Shipment count mismatch: API={api_shipments}, expected={TILE_CARPET_EXPECTED_SHIPMENTS}"
    
    print(f"✓ TILE AND CARPET monthly sum ${api_total:,.2f} matches expected")
    return True


def test_trade_history_invalid_uuid():
    """Test trade history returns 400 for invalid UUID format."""
    response = client.get("/api/v1/buyers/not-a-valid-uuid/trade-history")
    assert response.status_code == 400
    print("✓ trade-history returns 400 for invalid UUID")
    return True


def test_trade_history_not_found():
    """Test trade history returns 404 for non-existent buyer."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/buyers/{fake_uuid}/trade-history")
    assert response.status_code == 404
    print("✓ trade-history returns 404 for non-existent buyer")
    return True


def test_trade_history_has_origin_country():
    """Test that trade history includes top_origin_country."""
    response = client.get(f"/api/v1/buyers/{SAJ_UUID}/trade-history")
    assert response.status_code == 200
    data = response.json()
    
    # At least one month should have an origin country
    has_origin = any(m.get("top_origin_country") for m in data["months"])
    assert has_origin, "No origin country found in any month"
    
    # For Kenya imports, China should be a top origin
    origins = [m.get("top_origin_country") for m in data["months"] if m.get("top_origin_country")]
    assert "CHINA" in origins, f"Expected CHINA as top origin, got: {origins}"
    
    print(f"✓ trade-history includes origin countries: {set(origins)}")
    return True


def run_all_tests():
    """Run all buyers API tests."""
    print("=" * 60)
    print("BUYERS API TESTS")
    print("=" * 60)
    
    tests = [
        test_trade_history_returns_200,
        test_trade_history_monthly_sum_matches_total,
        test_trade_history_tile_carpet_accuracy,
        test_trade_history_invalid_uuid,
        test_trade_history_not_found,
        test_trade_history_has_origin_country,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = test()
            if result:
                passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
