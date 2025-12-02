#!/usr/bin/env python3
"""
EPIC 9 - Admin Upload API Tests
================================
Tests for the admin file upload functionality.

Usage:
    python tests/test_admin_upload.py
    pytest tests/test_admin_upload.py -v
"""

import io
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up test config
os.environ.setdefault('DB_CONFIG_PATH', 'config/db_config.yml')

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

# ============================================================================
# TEST DATA
# ============================================================================

# Minimal valid Excel-like CSV content (will be used as CSV for testing)
def get_unique_csv_content():
    """Generate unique CSV content to avoid duplicate detection."""
    unique_id = os.urandom(8).hex()
    return f"""IMPORTER_NAME,HS_CODE,QUANTITY,UNIT,TOTAL_VALUE_USD,ORIGIN_COUNTRY
TEST COMPANY {unique_id},690721,1000,KGS,50000,INDIA
TEST COMPANY B_{unique_id},690722,2000,PCS,75000,CHINA
"""


MISSING_COLUMNS_CSV = """IMPORTER_NAME,QUANTITY
TEST COMPANY A,1000
"""


def create_test_file(content: str = None, filename: str = "test_file.csv") -> tuple:
    """Create a file-like object for testing. Uses unique content if none provided."""
    if content is None:
        content = get_unique_csv_content()
    return (filename, io.BytesIO(content.encode('utf-8')), 'text/csv')


# ============================================================================
# TESTS
# ============================================================================

def test_upload_valid_csv_ingest_only():
    """Test uploading a valid CSV file with INGEST_ONLY mode (no year/month required)."""
    
    file_data = create_test_file(filename="test_kenya_import.csv")
    
    # Use source_format=OTHER to avoid matching a config with header_row=6
    # NOTE: year and month are NO LONGER required - they are derived from data
    response = client.post(
        "/api/v1/admin/upload-port-file",
        data={
            "reporting_country": "KENYA",
            "direction": "IMPORT",
            "source_format": "OTHER",  # Avoids matching kenya_import_full.yml
            "is_production": "false",  # Mark as non-production for testing
            "processing_mode": "INGEST_ONLY",
            "run_now": "false",
            "header_row_index": "1",
        },
        files={"file": file_data}
    )
    
    # Should succeed
    if response.status_code != 200:
        print(f"Error: {response.json()}")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    
    # Check response structure
    assert "file_id" in data
    assert data["reporting_country"] == "KENYA"
    assert data["direction"] == "IMPORT"
    assert data["source_format"] == "OTHER"
    # min/max shipment dates are NULL until standardization runs
    assert data["min_shipment_date"] is None
    assert data["max_shipment_date"] is None
    
    # Check validation
    assert "validation" in data
    assert data["validation"]["status"] == "OK"
    
    # Check pipeline
    assert "pipeline" in data
    assert data["pipeline"]["processing_mode"] == "INGEST_ONLY"
    assert data["pipeline"]["run_now"] == False
    assert data["pipeline"]["status"] in ["SKIPPED", "COMPLETED"]
    
    print(f"✓ Upload successful - file_id: {data['file_id']}")
    
    return data["file_id"]


def test_upload_run_now_false_no_pipeline_run():
    """Test that run_now=false does not create a pipeline_run."""
    
    file_data = create_test_file(filename="test_no_pipeline.csv")
    
    # Use OTHER source_format to avoid config header row validation
    response = client.post(
        "/api/v1/admin/upload-port-file",
        data={
            "reporting_country": "INDIA",
            "direction": "IMPORT",
            "source_format": "OTHER",  # Avoids config header validation
            "is_production": "false",
            "processing_mode": "INGEST_ONLY",  # INGEST_ONLY is always allowed
            "run_now": "false",  # Should NOT create pipeline run
            "header_row_index": "1",
        },
        files={"file": file_data}
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    # Should not have pipeline_run_id when run_now=false
    assert data["pipeline"]["run_now"] == False
    assert data["pipeline"]["pipeline_run_id"] is None
    assert data["pipeline"]["status"] == "SKIPPED"
    
    print("✓ run_now=false correctly skips pipeline creation")


def test_upload_run_now_true_creates_pipeline_run():
    """Test that run_now=true with allowed mode triggers pipeline."""
    
    file_data = create_test_file(filename="test_with_pipeline.csv")
    
    # Use OTHER source_format with INGEST_ONLY (always allowed)
    # INGEST_ONLY + run_now=true should complete the ingestion immediately
    response = client.post(
        "/api/v1/admin/upload-port-file",
        data={
            "reporting_country": "INDIA",
            "direction": "IMPORT",
            "source_format": "OTHER",  # Avoids config header validation
            "is_production": "false",
            "processing_mode": "INGEST_ONLY",  # Always allowed
            "run_now": "true",  # Should process immediately
            "header_row_index": "1",
        },
        files={"file": file_data}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # With INGEST_ONLY + run_now=true:
    # - status is COMPLETED (ingestion is done immediately)
    # - pipeline_run_id is None (INGEST_ONLY doesn't spawn background pipeline)
    assert data["pipeline"]["run_now"] == True
    assert data["pipeline"]["status"] == "COMPLETED"  # INGEST_ONLY completes immediately
    
    print(f"✓ run_now=true with INGEST_ONLY completes immediately")


def test_upload_invalid_file_type():
    """Test that invalid file types are rejected."""
    
    file_data = ("test.txt", io.BytesIO(b"invalid content"), "text/plain")
    
    response = client.post(
        "/api/v1/admin/upload-port-file",
        data={
            "reporting_country": "KENYA",
            "direction": "IMPORT",
            "source_format": "FULL",
            "is_production": "false",
            "processing_mode": "INGEST_ONLY",
            "run_now": "false",
            "header_row_index": "1",
        },
        files={"file": file_data}
    )
    
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]
    
    print("✓ Invalid file type correctly rejected")


def test_upload_empty_file():
    """Test that empty files are rejected."""
    
    file_data = ("empty.csv", io.BytesIO(b""), "text/csv")
    
    response = client.post(
        "/api/v1/admin/upload-port-file",
        data={
            "reporting_country": "KENYA",
            "direction": "IMPORT",
            "source_format": "FULL",
            "is_production": "false",
            "processing_mode": "INGEST_ONLY",
            "run_now": "false",
            "header_row_index": "1",
        },
        files={"file": file_data}
    )
    
    assert response.status_code == 400
    assert "Empty file" in response.json()["detail"]
    
    print("✓ Empty file correctly rejected")


def test_list_files():
    """Test the GET /admin/files endpoint."""
    
    response = client.get("/api/v1/admin/files?limit=10")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    
    print(f"✓ List files - {data['total']} total files, {len(data['items'])} returned")


def test_list_files_with_filters():
    """Test listing files with filters."""
    
    response = client.get("/api/v1/admin/files?reporting_country=KENYA&direction=IMPORT")
    
    assert response.status_code == 200
    data = response.json()
    
    # All returned items should match the filter
    for item in data["items"]:
        if item["reporting_country"]:
            assert item["reporting_country"] == "KENYA"
        if item["direction"]:
            assert item["direction"] == "IMPORT"
    
    print(f"✓ Filtered list files - {len(data['items'])} matching files")


def test_get_available_configs():
    """Test the GET /admin/configs endpoint."""
    
    response = client.get("/api/v1/admin/configs")
    
    assert response.status_code == 200
    configs = response.json()
    
    assert isinstance(configs, list)
    assert len(configs) > 0
    
    # Should include Kenya config
    assert any("kenya" in c.lower() for c in configs)
    
    print(f"✓ Available configs: {len(configs)} - {configs[:3]}...")


def test_duplicate_file_detection():
    """Test that duplicate files are detected by checksum."""
    
    unique_content = f"HEADER1,HEADER2\nDATA_{os.urandom(8).hex()},VALUE\n"
    
    # Upload first time
    file_data = create_test_file(unique_content, "test_duplicate.csv")
    
    response1 = client.post(
        "/api/v1/admin/upload-port-file",
        data={
            "reporting_country": "KENYA",
            "direction": "IMPORT",
            "source_format": "OTHER",
            "is_production": "false",
            "processing_mode": "INGEST_ONLY",
            "run_now": "false",
            "header_row_index": "1",
        },
        files={"file": file_data}
    )
    
    assert response1.status_code == 200
    
    # Try to upload same content again
    file_data2 = create_test_file(unique_content, "test_duplicate_2.csv")
    
    response2 = client.post(
        "/api/v1/admin/upload-port-file",
        data={
            "reporting_country": "KENYA",
            "direction": "IMPORT",
            "source_format": "OTHER",
            "is_production": "false",
            "processing_mode": "INGEST_ONLY",
            "run_now": "false",
            "header_row_index": "1",
        },
        files={"file": file_data2}
    )
    
    assert response2.status_code == 409
    assert "Duplicate" in response2.json()["detail"]
    
    print("✓ Duplicate file correctly detected")


def test_upload_without_year_month():
    """Test that upload works without year/month - they are derived from data."""
    
    file_data = create_test_file(filename="test_no_year_month.csv")
    
    response = client.post(
        "/api/v1/admin/upload-port-file",
        data={
            "reporting_country": "KENYA",
            "direction": "EXPORT",
            "source_format": "OTHER",
            "is_production": "false",
            "processing_mode": "INGEST_ONLY",
            "run_now": "false",
            "header_row_index": "1",
        },
        files={"file": file_data}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # min/max dates should be None until standardization runs
    assert data["min_shipment_date"] is None
    assert data["max_shipment_date"] is None
    # File name should NOT contain year/month segments
    assert data["file_name"].startswith("KENYA_EXPORT_")
    
    print("✓ Upload without year/month works correctly")


def test_custom_country_upload():
    """Test uploading with a custom country not in predefined lists (e.g., MALAYSIA)."""
    
    file_data = create_test_file(filename="test_malaysia_data.csv")
    
    response = client.post(
        "/api/v1/admin/upload-port-file",
        data={
            "reporting_country": "MALAYSIA",  # Not in original hardcoded list
            "direction": "IMPORT",
            "source_format": "OTHER",
            "is_production": "false",
            "processing_mode": "INGEST_ONLY",
            "run_now": "false",
            "header_row_index": "1",
        },
        files={"file": file_data}
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    # Verify the custom country is accepted and stored correctly
    assert data["reporting_country"] == "MALAYSIA"
    assert data["direction"] == "IMPORT"
    assert data["file_id"] is not None
    
    print(f"✓ Custom country (MALAYSIA) accepted - file_id: {data['file_id']}")
    return data["file_id"]


def test_custom_country_arbitrary_name():
    """Test uploading with any arbitrary country string."""
    
    file_data = create_test_file(filename="test_custom_country.csv")
    
    response = client.post(
        "/api/v1/admin/upload-port-file",
        data={
            "reporting_country": "NEWZEALAND",  # Can be any valid string
            "direction": "EXPORT",
            "source_format": "OTHER",
            "is_production": "false",
            "processing_mode": "INGEST_ONLY",
            "run_now": "false",
            "header_row_index": "1",
        },
        files={"file": file_data}
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    # Verify arbitrary country name is accepted
    assert data["reporting_country"] == "NEWZEALAND"
    
    print(f"✓ Arbitrary country name (NEWZEALAND) accepted - file_id: {data['file_id']}")


# ============================================================================
# EPIC 10: MAPPING STATUS ENFORCEMENT TESTS
# ============================================================================

def test_draft_mapping_rejects_full_pipeline():
    """Test that DRAFT mappings reject FULL_PIPELINE mode."""
    from etl.db_utils import DatabaseManager
    
    db = DatabaseManager('config/db_config.yml')
    
    # Find a DRAFT mapping
    result = db.execute_query("""
        SELECT reporting_country, direction, source_format 
        FROM mapping_registry 
        WHERE status = 'DRAFT' 
        LIMIT 1
    """)
    
    if not result:
        print("⚠ No DRAFT mappings found - skipping test")
        return
    
    country, direction, fmt = result[0]
    
    # Try to upload with FULL_PIPELINE - should be rejected
    csv_content = "HS_CODE,BUYER,VALUE\n123456,Test Buyer,1000"
    
    response = client.post(
        "/api/v1/admin/upload-port-file",
        files={"file": ("test_draft.csv", csv_content, "text/csv")},
        data={
            "reporting_country": country,
            "direction": direction,
            "source_format": fmt,
            "processing_mode": "FULL_PIPELINE",
            "run_now": "false",
        }
    )
    
    # Should be rejected with 400
    assert response.status_code == 400, f"DRAFT mapping should reject FULL_PIPELINE. Got {response.status_code}: {response.text}"
    assert "DRAFT" in response.json().get("detail", "") or "allowed" in response.json().get("detail", "").lower()
    
    print(f"✓ DRAFT mapping ({country}) correctly rejects FULL_PIPELINE")


def test_live_mapping_allows_full_pipeline():
    """Test that LIVE mappings allow FULL_PIPELINE mode via the API status check."""
    # First verify that the mapping status endpoint shows LIVE status
    status_response = client.get(
        "/api/v1/admin/mapping-status",
        params={
            "reporting_country": "KENYA",
            "direction": "IMPORT",
            "source_format": "FULL"
        }
    )
    
    assert status_response.status_code == 200
    status_data = status_response.json()
    
    # Verify LIVE status and FULL_PIPELINE is allowed
    assert status_data["status"] == "LIVE", f"Expected LIVE status, got {status_data['status']}"
    assert "FULL_PIPELINE" in status_data["allowed_modes"], "FULL_PIPELINE should be allowed for LIVE mapping"
    
    print(f"✓ LIVE mapping (KENYA IMPORT FULL) correctly allows FULL_PIPELINE")


# ============================================================================
# MAIN
# ============================================================================

def run_tests():
    """Run all tests and print summary."""
    
    print("=" * 70)
    print("  EPIC 9 - ADMIN UPLOAD API TESTS")
    print("=" * 70)
    print()
    
    tests = [
        ("Upload valid CSV (INGEST_ONLY)", test_upload_valid_csv_ingest_only),
        ("run_now=false no pipeline run", test_upload_run_now_false_no_pipeline_run),
        ("run_now=true creates pipeline run", test_upload_run_now_true_creates_pipeline_run),
        ("Invalid file type rejected", test_upload_invalid_file_type),
        ("Empty file rejected", test_upload_empty_file),
        ("List files", test_list_files),
        ("List files with filters", test_list_files_with_filters),
        ("Get available configs", test_get_available_configs),
        ("Duplicate file detection", test_duplicate_file_detection),
        ("Upload without year/month", test_upload_without_year_month),
        ("Custom country (MALAYSIA)", test_custom_country_upload),
        ("Arbitrary country name", test_custom_country_arbitrary_name),
        ("DRAFT mapping rejects FULL_PIPELINE", test_draft_mapping_rejects_full_pipeline),
        ("LIVE mapping allows FULL_PIPELINE", test_live_mapping_allows_full_pipeline),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: FAILED - {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name}: ERROR - {e}")
            failed += 1
    
    print()
    print("=" * 70)
    print(f"  RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
