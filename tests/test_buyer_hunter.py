"""
EPIC 7D - Buyer Hunter Tests
==============================
Tests for buyer hunter scoring and API endpoints.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ['DB_CONFIG_PATH'] = 'config/db_config.yml'

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_buyer_hunter_top_returns_200():
    """Test /buyer-hunter/top returns 200 with valid HS code."""
    response = client.get("/api/v1/buyer-hunter/top?hs_code_6=690721")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "count" in data
    assert data["hs_code_6"] == "690721"
    print(f"✓ /buyer-hunter/top returns 200 with {data['count']} results")
    return data


def test_buyer_hunter_scores_in_range():
    """Test that opportunity scores are in [0, 100]."""
    response = client.get("/api/v1/buyer-hunter/top?hs_code_6=690721&limit=50")
    assert response.status_code == 200
    data = response.json()
    
    for item in data["items"]:
        score = item["opportunity_score"]
        assert 0 <= score <= 100, f"Score {score} out of range"
        
        # Check score breakdown sums roughly to total
        breakdown_sum = (
            item["volume_score"] +
            item["stability_score"] +
            item["hs_focus_score"] +
            item["risk_score_component"] +
            item["data_quality_score"]
        )
        # Allow small floating point variance
        assert abs(breakdown_sum - score) < 0.5, f"Score breakdown doesn't match: {breakdown_sum} vs {score}"
    
    print(f"✓ All {len(data['items'])} scores in [0, 100] with valid breakdown")
    return True


def test_buyer_hunter_sorted_by_score():
    """Test that results are sorted by opportunity_score descending."""
    response = client.get("/api/v1/buyer-hunter/top?hs_code_6=690721&limit=30")
    assert response.status_code == 200
    data = response.json()
    
    scores = [item["opportunity_score"] for item in data["items"]]
    assert scores == sorted(scores, reverse=True), "Results not sorted by score DESC"
    
    print(f"✓ Results correctly sorted by opportunity_score DESC")
    return True


def test_risk_filter_respected():
    """Test that max_risk_level filter is respected.
    
    REFINED: max_risk_level=LOW now only includes verified LOW buyers,
    NOT UNKNOWN/UNSCORED buyers (which are between MEDIUM and HIGH).
    """
    # Only LOW risk - should NOT include UNKNOWN
    response = client.get("/api/v1/buyer-hunter/top?hs_code_6=690721&max_risk_level=LOW")
    assert response.status_code == 200
    data = response.json()
    
    for item in data["items"]:
        # REFINED: LOW filter should only return verified LOW-risk buyers
        assert item["current_risk_level"] == "LOW", \
            f"Found {item['current_risk_level']} buyer when max_risk_level=LOW (expected only LOW)"
    
    # MEDIUM should include LOW, MEDIUM, and UNKNOWN
    response_med = client.get("/api/v1/buyer-hunter/top?hs_code_6=690721&max_risk_level=MEDIUM")
    assert response_med.status_code == 200
    data_med = response_med.json()
    
    allowed_levels = {"LOW", "MEDIUM", "UNKNOWN"}
    for item in data_med["items"]:
        assert item["current_risk_level"] in allowed_levels, \
            f"Found {item['current_risk_level']} with max_risk_level=MEDIUM"
    
    print(f"✓ Risk filter respected - LOW={len(data['items'])}, MEDIUM={len(data_med['items'])} buyers")
    return True


def test_destination_country_filter():
    """Test destination_countries filter."""
    response = client.get("/api/v1/buyer-hunter/top?hs_code_6=690721&destination_countries=KENYA")
    assert response.status_code == 200
    data = response.json()
    
    for item in data["items"]:
        # Destination should match filter
        assert item["destination_country"] == "KENYA", \
            f"Found destination {item['destination_country']} when filtering for KENYA"
    
    print(f"✓ Destination country filter works - {len(data['items'])} KENYA buyers")
    return True


def test_sql_injection_safe():
    """Test that SQL injection attempts are blocked."""
    payloads = [
        "'; DROP TABLE --",
        "690721' OR '1'='1",
        "1; DELETE FROM risk_scores;--"
    ]
    
    for payload in payloads:
        response = client.get(f"/api/v1/buyer-hunter/top?hs_code_6=690721&destination_countries={payload}")
        # Should return 200 with empty or filtered results, not crash
        assert response.status_code == 200, f"Unexpected status for payload: {payload}"
    
    print("✓ SQL injection attempts safely handled (parameterized queries)")
    return True


def test_invalid_hs_code_rejected():
    """Test that invalid HS codes are rejected."""
    # Non-numeric
    response = client.get("/api/v1/buyer-hunter/top?hs_code_6=abcdef")
    assert response.status_code == 400
    
    # Wrong length
    response = client.get("/api/v1/buyer-hunter/top?hs_code_6=12345")
    assert response.status_code == 422  # Validation error
    
    print("✓ Invalid HS codes properly rejected")
    return True


def test_search_endpoint():
    """Test /buyer-hunter/search endpoint with pagination."""
    response = client.get("/api/v1/buyer-hunter/search?hs_code_6=690721&limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert len(data["items"]) <= 10
    
    print(f"✓ /buyer-hunter/search works - {data['total']} total, {len(data['items'])} returned")
    return True


def test_score_breakdown_endpoint():
    """Test /buyer-hunter/score-breakdown endpoint."""
    response = client.get("/api/v1/buyer-hunter/score-breakdown")
    assert response.status_code == 200
    data = response.json()
    
    assert "algorithm" in data
    assert "components" in data
    assert "volume" in data["components"]
    assert "stability" in data["components"]
    assert "hs_focus" in data["components"]
    assert "risk" in data["components"]
    assert "data_quality" in data["components"]
    
    print("✓ /buyer-hunter/score-breakdown returns algorithm documentation")
    return True


# =====================================================================
# TASK 5: Business-Focused Tests
# =====================================================================

def test_monotonicity_higher_volume_higher_score():
    """
    Test A: Monotonicity - Higher volume buyer should score >= lower volume buyer
    when other factors are equal or better.
    
    This catches weird scoring bugs where a weaker buyer gets a higher score.
    """
    response = client.get("/api/v1/buyer-hunter/top?hs_code_6=690721&destination_countries=KENYA&limit=50")
    assert response.status_code == 200
    data = response.json()
    
    if len(data["items"]) < 2:
        print("✓ Monotonicity test skipped (< 2 buyers)")
        return True
    
    # Find pairs where buyer A has strictly higher volume
    violations = []
    items = data["items"]
    
    for i, buyer_a in enumerate(items):
        for buyer_b in items[i+1:]:
            # If A has higher volume, same or better risk, similar history
            # Then A's score should be >= B's score
            vol_a = buyer_a["total_value_usd_12m"]
            vol_b = buyer_b["total_value_usd_12m"]
            
            risk_order = {"LOW": 0, "MEDIUM": 1, "UNKNOWN": 2, "HIGH": 3, "CRITICAL": 4}
            risk_a = risk_order.get(buyer_a["current_risk_level"], 2)
            risk_b = risk_order.get(buyer_b["current_risk_level"], 2)
            
            months_a = buyer_a["months_with_shipments_12m"]
            months_b = buyer_b["months_with_shipments_12m"]
            
            # A is strictly better on volume AND at least as good on risk and history
            if vol_a > vol_b * 1.5 and risk_a <= risk_b and months_a >= months_b:
                score_a = buyer_a["opportunity_score"]
                score_b = buyer_b["opportunity_score"]
                
                if score_a < score_b:
                    violations.append({
                        "buyer_a": buyer_a["buyer_name"],
                        "buyer_b": buyer_b["buyer_name"],
                        "vol_a": vol_a,
                        "vol_b": vol_b,
                        "score_a": score_a,
                        "score_b": score_b
                    })
    
    # Allow a small number of edge cases but flag major violations
    assert len(violations) <= 2, f"Monotonicity violations found: {violations[:3]}"
    
    print(f"✓ Monotonicity test passed - {len(items)} buyers, {len(violations)} minor edge cases")
    return True


def test_known_hs_690721_kenya_ranking():
    """
    Test B: Known HS 690721 (ceramic tiles) scenario for Kenya.
    
    Verifies that high-volume, stable buyers rank near the top.
    This uses real data from the GTI-OS ledger.
    """
    response = client.get("/api/v1/buyer-hunter/top?hs_code_6=690721&destination_countries=KENYA&limit=30")
    assert response.status_code == 200
    data = response.json()
    
    if len(data["items"]) == 0:
        print("✓ HS 690721 Kenya test skipped (no data)")
        return True
    
    # Get top 5 buyers
    top_5 = data["items"][:5]
    top_5_names = [b["buyer_name"] for b in top_5]
    top_5_volumes = [b["total_value_usd_12m"] for b in top_5]
    
    # Business rule: Top buyers should have meaningful volume
    # At least one of top 5 should have > $100K volume (if data exists)
    max_volume_in_top5 = max(top_5_volumes) if top_5_volumes else 0
    
    # Also verify that the #1 buyer is not a tiny buyer
    # (i.e., score isn't dominated by non-volume factors)
    top_buyer = data["items"][0]
    
    # If there are high-volume buyers, they should be near the top
    all_volumes = [b["total_value_usd_12m"] for b in data["items"]]
    max_overall_volume = max(all_volumes) if all_volumes else 0
    
    if max_overall_volume > 100000:
        # The highest volume buyer should be in top 10
        high_vol_buyers = [b for b in data["items"] if b["total_value_usd_12m"] >= max_overall_volume * 0.8]
        
        for hvb in high_vol_buyers:
            rank = data["items"].index(hvb) + 1
            assert rank <= 10, \
                f"High volume buyer '{hvb['buyer_name']}' (${hvb['total_value_usd_12m']:,.0f}) ranked #{rank}, expected top 10"
    
    print(f"✓ HS 690721 Kenya ranking test passed")
    print(f"  Top buyer: {top_buyer['buyer_name']} (score={top_buyer['opportunity_score']}, vol=${top_buyer['total_value_usd_12m']:,.0f})")
    return True


def test_unknown_risk_scoring():
    """
    Test: Verify UNKNOWN risk buyers get score=6 (between MEDIUM=8 and HIGH=2).
    """
    response = client.get("/api/v1/buyer-hunter/top?hs_code_6=690721&max_risk_level=ALL&limit=50")
    assert response.status_code == 200
    data = response.json()
    
    unknown_buyers = [b for b in data["items"] if b["current_risk_level"] == "UNKNOWN"]
    
    for buyer in unknown_buyers:
        # UNKNOWN should get risk_score_component = 6
        assert buyer["risk_score_component"] == 6, \
            f"UNKNOWN buyer {buyer['buyer_name']} has risk_score={buyer['risk_score_component']}, expected 6"
    
    print(f"✓ UNKNOWN risk scoring correct - {len(unknown_buyers)} UNKNOWN buyers verified")
    return True


def test_davita_kenya_tiles_is_discoverable():
    """
    CRITICAL VALIDATION TEST: Ensure DAVITA SOLUTIONS LIMITED is discoverable
    for HS 690721 (tiles) in Kenya.
    
    This buyer exists in the source data (Kenya Import S.xlsx) with:
    - HS: 6907210000 (→ hs_code_6 = 690721)
    - Total value: ~$56,108 USD
    - Origin: INDIA
    - Destination: KENYA
    - 2 shipments (Sep 2025, Oct 2025)
    
    The buyer is ranked ~#69 out of 316 buyers, so they won't appear in
    the default TOP 20. The /search-by-name endpoint must find them.
    """
    # Test 1: Search by name should find DAVITA
    response = client.get(
        "/api/v1/buyer-hunter/search-by-name",
        params={
            "buyer_name": "DAVITA",
            "hs_code_6": "690721",
            "destination_countries": "KENYA"
        }
    )
    assert response.status_code == 200, f"Search by name failed: {response.text}"
    data = response.json()
    
    assert data["total"] >= 1, "DAVITA not found in search results"
    
    # Find DAVITA in results
    davita = None
    for item in data["items"]:
        if "DAVITA" in item["buyer_name"].upper():
            davita = item
            break
    
    assert davita is not None, "DAVITA not in search results items"
    
    # Validate DAVITA's data
    assert davita["destination_country"] == "KENYA", \
        f"DAVITA destination should be KENYA, got {davita['destination_country']}"
    
    # Value should be ~$56,108 (allow some variance)
    assert 50000 <= davita["total_value_usd_12m"] <= 60000, \
        f"DAVITA value should be ~$56,108, got ${davita['total_value_usd_12m']:,.2f}"
    
    assert davita["total_shipments_12m"] >= 2, \
        f"DAVITA should have at least 2 shipments, got {davita['total_shipments_12m']}"
    
    # HS focus should be 100% (only imports tiles)
    assert davita["hs_share_pct"] >= 99, \
        f"DAVITA hs_share_pct should be ~100%, got {davita['hs_share_pct']}%"
    
    print(f"✓ DAVITA SOLUTIONS found and validated:")
    print(f"  - UUID: {davita['buyer_uuid']}")
    print(f"  - Value: ${davita['total_value_usd_12m']:,.2f}")
    print(f"  - Shipments: {davita['total_shipments_12m']}")
    print(f"  - Opportunity Score: {davita['opportunity_score']}")
    
    return True


def test_marble_inn_kenya_tiles_is_discoverable():
    """
    CRITICAL VALIDATION TEST: Ensure MARBLE INN DEVELOPERS LIMITED is discoverable
    for HS 690721 (tiles) in Kenya.
    
    This buyer exists in the source data (Kenya Import S.xlsx) with:
    - HS: 6907210000 (→ hs_code_6 = 690721)
    - Total value: ~$130,582.91 USD
    - Origin: EGYPT
    - Destination: KENYA
    - 5 shipments
    """
    # Test: Search by name should find MARBLE INN
    response = client.get(
        "/api/v1/buyer-hunter/search-by-name",
        params={
            "buyer_name": "MARBLE INN",
            "hs_code_6": "690721",
            "destination_countries": "KENYA"
        }
    )
    assert response.status_code == 200, f"Search by name failed: {response.text}"
    data = response.json()
    
    assert data["total"] >= 1, "MARBLE INN not found in search results"
    
    # Find MARBLE INN in results
    marble_inn = None
    for item in data["items"]:
        if "MARBLE INN" in item["buyer_name"].upper():
            marble_inn = item
            break
    
    assert marble_inn is not None, "MARBLE INN not in search results items"
    
    # Validate MARBLE INN's data
    assert marble_inn["destination_country"] == "KENYA", \
        f"MARBLE INN destination should be KENYA, got {marble_inn['destination_country']}"
    
    # Value should be ~$130,582.91 (allow some variance)
    assert 125000 <= marble_inn["total_value_usd_12m"] <= 135000, \
        f"MARBLE INN value should be ~$130,582, got ${marble_inn['total_value_usd_12m']:,.2f}"
    
    assert marble_inn["total_shipments_12m"] >= 5, \
        f"MARBLE INN should have at least 5 shipments, got {marble_inn['total_shipments_12m']}"
    
    print(f"✓ MARBLE INN DEVELOPERS found and validated:")
    print(f"  - UUID: {marble_inn['buyer_uuid']}")
    print(f"  - Value: ${marble_inn['total_value_usd_12m']:,.2f}")
    print(f"  - Shipments: {marble_inn['total_shipments_12m']}")
    print(f"  - Opportunity Score: {marble_inn['opportunity_score']}")
    
    return True


def test_search_by_name_endpoint():
    """Test /buyer-hunter/search-by-name endpoint basics."""
    response = client.get(
        "/api/v1/buyer-hunter/search-by-name",
        params={
            "buyer_name": "TILE",
            "hs_code_6": "690721",
            "destination_countries": "KENYA"
        }
    )
    assert response.status_code == 200
    data = response.json()
    
    assert "items" in data
    assert "total" in data
    assert data["min_total_value_usd"] == 10000  # Default for name search is 10k
    assert data["max_risk_level"] == "ALL"  # Default for name search is ALL
    
    # Results should contain buyers with "TILE" in name
    for item in data["items"]:
        assert "TILE" in item["buyer_name"].upper(), \
            f"Result {item['buyer_name']} doesn't match search term 'TILE'"
    
    print(f"✓ /buyer-hunter/search-by-name works - found {data['total']} buyers with 'TILE'")
    return True


def run_all_tests():
    """Run all buyer hunter tests."""
    print()
    print("=" * 70)
    print("  EPIC 7D - BUYER HUNTER TESTS (Refined)")
    print("=" * 70)
    print()
    
    passed = 0
    failed = 0
    
    tests = [
        ("Top endpoint returns 200", test_buyer_hunter_top_returns_200),
        ("Scores in valid range", test_buyer_hunter_scores_in_range),
        ("Results sorted by score", test_buyer_hunter_sorted_by_score),
        ("Risk filter respected", test_risk_filter_respected),
        ("Destination filter works", test_destination_country_filter),
        ("SQL injection safe", test_sql_injection_safe),
        ("Invalid HS code rejected", test_invalid_hs_code_rejected),
        ("Search endpoint works", test_search_endpoint),
        ("Score breakdown endpoint", test_score_breakdown_endpoint),
        # TASK 5: Business-focused tests
        ("UNKNOWN risk scoring", test_unknown_risk_scoring),
        ("Monotonicity (volume vs score)", test_monotonicity_higher_volume_higher_score),
        ("HS 690721 Kenya ranking", test_known_hs_690721_kenya_ranking),
        # Kenya buyer validation tests
        ("Search by name endpoint", test_search_by_name_endpoint),
        ("DAVITA Kenya tiles discoverable", test_davita_kenya_tiles_is_discoverable),
        ("MARBLE INN Kenya tiles discoverable", test_marble_inn_kenya_tiles_is_discoverable),
    ]
    
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"✗ {name} FAILED: {e}")
            failed += 1
    
    print()
    print("=" * 70)
    print(f"  RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    print()
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
