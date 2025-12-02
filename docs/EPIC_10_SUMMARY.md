# EPIC 10 – Multi-Country Onboarding (Safety-First)

## Summary

EPIC 10 implements a safety-first approach to onboarding new countries into the Port Data Brain ETL pipeline. It introduces a `mapping_registry` table to track the validation status of country mappings and enforces processing restrictions based on that status.

## Key Components

### 1. Mapping Registry Table
- **Location**: `db/migrations/009_mapping_registry.sql`, `db/schema_v1.sql`
- **Purpose**: Tracks status of country/direction/format mappings
- **Statuses**: `DRAFT` → `VERIFIED` → `LIVE`
- **Script**: `scripts/populate_mapping_registry.py` populates from existing configs

### 2. Sandbox Tables
- `tmp_stg_shipments_raw` - Temporary raw data for validation
- `tmp_stg_shipments_standardized` - Temporary standardized data for DQ checks
- Isolated from production tables to prevent accidental data pollution

### 3. Validation Script
- **Location**: `scripts/validate_country_mapping.py`
- **Purpose**: Validates new country mappings in sandbox before promoting to VERIFIED
- **Features**:
  - Ingests sample file into sandbox tables
  - Runs standardization with country config
  - Performs DQ checks (null rates, date validity, value ranges)
  - Generates validation report
  - Updates mapping status to VERIFIED if checks pass

### 4. Bulk Ingest Script
- **Location**: `scripts/bulk_ingest_live_countries.py`
- **Purpose**: Processes only LIVE country mappings
- **Features**:
  - Finds files from raw folders and file_registry
  - Runs full pipeline (ingest → standardize → identity → ledger)
  - Skips already processed files
  - Dry-run mode available

### 5. API Enforcement
- **Location**: `api/routers/admin_upload.py`
- **New Endpoint**: `GET /api/v1/admin/mapping-status`
- **Processing Mode Restrictions**:
  | Status | Allowed Modes |
  |--------|---------------|
  | LIVE | INGEST_ONLY, INGEST_AND_STANDARDIZE, FULL_PIPELINE |
  | VERIFIED | INGEST_ONLY, INGEST_AND_STANDARDIZE |
  | DRAFT | INGEST_ONLY |
  | NOT_FOUND | INGEST_ONLY |

### 6. Frontend UI
- **Location**: `control-tower-ui/src/pages/AdminUpload.tsx`
- **Features**:
  - Status pill showing LIVE/VERIFIED/DRAFT with color coding
  - Processing mode options filtered based on mapping status
  - Clear messaging about what's allowed

## Files Created/Modified

### New Files
| File | Description |
|------|-------------|
| `db/migrations/009_mapping_registry.sql` | Migration for mapping_registry and sandbox tables |
| `scripts/populate_mapping_registry.py` | Populates registry from existing configs |
| `scripts/validate_country_mapping.py` | Sandbox validation script |
| `scripts/bulk_ingest_live_countries.py` | Bulk ingestion for LIVE countries |
| `tests/test_mapping_registry.py` | Tests for mapping registry functionality |

### Modified Files
| File | Changes |
|------|---------|
| `db/schema_v1.sql` | Added mapping_registry and sandbox tables |
| `api/routers/admin_upload.py` | Added mapping status endpoint and enforcement |
| `control-tower-ui/src/api/client.ts` | Added getMappingStatus API method |
| `control-tower-ui/src/pages/AdminUpload.tsx` | Added status pills and mode filtering |
| `tests/test_admin_upload.py` | Added status enforcement tests |

## Test Results

```
52 passed, 1 skipped, 25 warnings in 2.27s
```

Frontend build: **SUCCESS** (673.82 kB bundle)

## Usage

### Validate a New Country Mapping
```bash
python scripts/validate_country_mapping.py \
    --country BRAZIL \
    --direction IMPORT \
    --format FULL \
    --sample-file data/reference/brazil_sample.xlsx
```

### Bulk Ingest LIVE Countries
```bash
# Dry run first
python scripts/bulk_ingest_live_countries.py --dry-run

# Actual run
python scripts/bulk_ingest_live_countries.py
```

### Check Mapping Status (API)
```bash
curl "http://localhost:8000/api/v1/admin/mapping-status?reporting_country=KENYA&direction=IMPORT&source_format=FULL"
```

## Safety Guarantees

1. **DRAFT mappings** can only ingest raw data - no standardization or ledger writes
2. **VERIFIED mappings** can standardize but cannot write to production ledger
3. **LIVE mappings** have full pipeline access
4. Sandbox tables are isolated and cleaned after each validation session
5. Existing India/Kenya/Indonesia flows are preserved as LIVE
