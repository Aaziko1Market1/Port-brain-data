# EPIC 6A: Core Analytics - Buyer & Exporter Profiles

**Version:** 1.0  
**Date:** November 30, 2025  
**Status:** Complete ✅

---

## Executive Summary

EPIC 6A implements the core analytics layer for the GTI-OS Data Platform, creating aggregated buyer and exporter profiles from `global_trades_ledger` data. The implementation is fully incremental, idempotent, and integrated with the pipeline tracking system.

---

## What Was Implemented

### 1. Schema Changes

**Migration:** `db/migrations/003_epic6_profiles_schema.sql`

#### buyer_profile Table (New Schema)
| Column | Type | Description |
|--------|------|-------------|
| profile_id | BIGSERIAL | Primary key |
| buyer_uuid | UUID | FK to organizations_master |
| destination_country | TEXT | Import destination |
| first_shipment_date | DATE | Earliest shipment |
| last_shipment_date | DATE | Latest shipment |
| total_shipments | BIGINT | Total shipment count |
| total_customs_value_usd | NUMERIC | Total value |
| total_qty_kg | NUMERIC | Total quantity |
| avg_price_usd_per_kg | NUMERIC | Average price |
| unique_hs6_count | INT | Product diversity |
| top_hs_codes | JSONB | Top 5 HS codes |
| top_suppliers | JSONB | Top 5 suppliers |
| growth_12m | NUMERIC | YoY growth % |
| persona_label | TEXT | Buyer classification |
| reporting_country | TEXT | Source country |
| updated_at | TIMESTAMPTZ | Last update time |

**Grain:** `(buyer_uuid, destination_country)` - unique constraint

#### exporter_profile Table (New Schema)
| Column | Type | Description |
|--------|------|-------------|
| profile_id | BIGSERIAL | Primary key |
| supplier_uuid | UUID | FK to organizations_master |
| origin_country | TEXT | Export origin |
| first_shipment_date | DATE | Earliest shipment |
| last_shipment_date | DATE | Latest shipment |
| total_shipments | BIGINT | Total shipment count |
| total_customs_value_usd | NUMERIC | Total value |
| total_qty_kg | NUMERIC | Total quantity |
| avg_price_usd_per_kg | NUMERIC | Average price |
| unique_hs6_count | INT | Product diversity |
| top_hs_codes | JSONB | Top 5 HS codes |
| top_buyers | JSONB | Top 5 buyers |
| stability_score | NUMERIC | 0-100 stability |
| onboarding_score | NUMERIC | 0-100 readiness |
| reporting_country | TEXT | Source country |
| updated_at | TIMESTAMPTZ | Last update time |

**Grain:** `(supplier_uuid, origin_country)` - unique constraint

#### Helper Table: profile_build_markers
Tracks last processed date for incremental builds.

### 2. Core Module

**Location:** `etl/analytics/build_profiles.py`

| Component | Purpose |
|-----------|---------|
| `ProfileBuilder` | Main class for building profiles |
| `ProfileBuildSummary` | Results dataclass |
| `_safe_float()` | Helper for NaN-safe conversions |
| `run_build_profiles()` | Main entry point |

### 3. Orchestration Script

**Location:** `scripts/run_build_profiles.py`

```bash
# Incremental build (default)
python scripts/run_build_profiles.py

# Full rebuild
python scripts/run_build_profiles.py --full-rebuild

# Buyers only
python scripts/run_build_profiles.py --buyers-only

# Exporters only
python scripts/run_build_profiles.py --exporters-only
```

### 4. Verification SQL

**Location:** `db/epic6_profiles_verification.sql`

---

## Profile Counts by Country

### Buyer Profiles (381 total)

| Country | Profiles | Shipments | Total Value USD |
|---------|----------|-----------|-----------------|
| INDONESIA | 65 | 1,002 | $46,271,563 |
| KENYA | 316 | 1,002 | $22,141,781 |

### Exporter Profiles (79 total)

| Country | Profiles | Shipments | Total Value USD |
|---------|----------|-----------|-----------------|
| INDIA | 7 | 8,000 | $813,065,738 |
| INDONESIA | 65 | 762 | $441,013,757 |
| KENYA | 7 | 703 | $34,230,086 |

---

## Persona Distribution (Buyers)

| Persona | Count | Avg Value USD |
|---------|-------|---------------|
| Value | 167 | $34,374 |
| New | 126 | $3,679 |
| Mid | 51 | $234,373 |
| Small | 21 | $4,980 |
| Whale | 16 | $3,134,480 |

**Persona Rules:**
- **Whale:** Total value ≥ $1M
- **Mid:** Total value ≥ $100K
- **Value:** Total value ≥ $10K
- **Growing:** High growth rate (>50% for Mid, >100% for Value)
- **New:** ≤2 shipments
- **Small:** Everything else

---

## Stability Score Distribution (Exporters)

| Score Band | Count | Description |
|------------|-------|-------------|
| 80-100 | 0 | Highly stable |
| 60-79 | 0 | Stable |
| 40-59 | 76 | Moderate |
| 0-39 | 3 | Low stability |

**Stability Score Formula:**
- Active months (0-50 pts): More months active = higher score
- Variance (0-50 pts): Lower shipment variance = higher score

---

## Incremental Processing Strategy

The profile builder uses a **marker-based incremental strategy**:

1. **profile_build_markers** table stores `last_processed_date` per profile type
2. On each run:
   - Query ledger for shipments with `created_at > last_processed_date`
   - Get distinct affected `buyer_uuid/supplier_uuid` combinations
   - FULLY recompute profiles for affected entities only
   - UPSERT into profile tables (handles both insert and update)
3. Update markers after successful processing

**Benefits:**
- Processes only new/changed data
- No double-counting due to UPSERT semantics
- Full rebuild available via `--full-rebuild` flag

---

## Idempotency Verification

| Run | Mode | Buyers Processed | Exporters Processed | Result |
|-----|------|------------------|---------------------|--------|
| 1 | Full Rebuild | 381 | 79 | 381 created, 79 created |
| 2 | Incremental | 0 | 0 | No updates (data current) |
| 3 | Incremental | 0 | 0 | No updates (data current) |

✅ **Confirmed:** Re-running does not create duplicates or double-count values.

---

## Data Integrity Verification

| Check | Result |
|-------|--------|
| NULL buyer_uuid in buyer_profile | 0 ✅ |
| NULL supplier_uuid in exporter_profile | 0 ✅ |
| Orphaned buyer profiles | 0 ✅ |
| Orphaned exporter profiles | 0 ✅ |
| Buyer profile value mismatch vs ledger | 0 ✅ |
| Exporter profile value mismatch vs ledger | 0 ✅ |

---

## Ledger Integrity (Unchanged)

| Table | Row Count | Status |
|-------|-----------|--------|
| stg_shipments_raw | 11,469 | ✅ |
| stg_shipments_standardized | 11,469 | ✅ |
| global_trades_ledger | 11,469 | ✅ |

✅ **Confirmed:** No aggregation or deletion of shipments. 1 row = 1 shipment preserved.

---

## Pipeline Tracking Integration

All runs are tracked in `pipeline_runs`:

```sql
SELECT pipeline_name, started_at, status, rows_processed, rows_created
FROM pipeline_runs
WHERE pipeline_name = 'build_profiles'
ORDER BY started_at DESC;
```

Sample output:
```
build_profiles | 2025-11-30 12:57:33 | SUCCESS | 0   | 0   | (incremental, no changes)
build_profiles | 2025-11-30 12:57:00 | SUCCESS | 460 | 2   | (full rebuild)
```

---

## Files Created/Modified

### New Files

| File | Purpose |
|------|---------|
| `db/migrations/003_epic6_profiles_schema.sql` | Schema migration |
| `etl/analytics/build_profiles.py` | Core profile builder |
| `scripts/run_build_profiles.py` | CLI orchestration |
| `db/epic6_profiles_verification.sql` | Verification queries |
| `EPIC6_PROFILES_IMPLEMENTATION_SUMMARY.md` | This document |

### Modified Files

| File | Change |
|------|--------|
| `etl/analytics/__init__.py` | Export profile builder functions |
| `db/schema_v1.sql` | Add `build_profiles` to pipeline_runs constraint |

---

## Compatibility with EPIC 0-5

| EPIC | Status | Impact |
|------|--------|--------|
| EPIC 0-1 (Ingestion) | ✅ Compatible | No changes |
| EPIC 2 (Standardization) | ✅ Compatible | No changes |
| EPIC 3 (Identity) | ✅ Compatible | Uses organizations_master |
| EPIC 4 (Ledger) | ✅ Compatible | Reads from global_trades_ledger |
| EPIC 5 (Mirror) | ✅ Compatible | No interference |

---

## Known Limitations

1. **Growth calculation:** Requires 24 months of data for YoY growth (returns NULL otherwise)
2. **Stability score:** Uses last 12 months only; new exporters get neutral score
3. **JSON fields:** Limited to top 5 items per profile

---

## Future Improvements

1. Add configurable persona thresholds via YAML
2. Add trend indicators (improving/declining)
3. Add geographic diversity metrics
4. Add product seasonality detection
5. Create materialized views for dashboard queries

---

*Report generated: November 30, 2025*  
*Total buyer profiles: 381*  
*Total exporter profiles: 79*  
*All integrity checks: PASSED*
