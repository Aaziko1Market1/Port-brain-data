# EPIC 6B: Price Corridors & Lane Stats - Implementation Summary

**Version:** 1.0  
**Date:** November 30, 2025  
**Status:** Complete ✅

---

## Executive Summary

EPIC 6B implements market price intelligence and trade lane analytics for the GTI-OS Data Platform. It creates aggregated price corridors (percentile distributions by HS6/market/month) and trade lane statistics (origin→destination aggregates per HS6). The implementation is fully incremental, idempotent, and integrated with the pipeline tracking system.

---

## What Was Implemented

### 1. Schema Changes

**Migration:** `db/migrations/004_epic6b_price_lanes.sql`

#### price_corridor Table (Restructured)

| Column | Type | Description |
|--------|------|-------------|
| corridor_id | BIGSERIAL | Primary key |
| hs_code_6 | TEXT | HS code (6 digits) |
| destination_country | TEXT | Market country |
| year | INT | Year |
| month | INT | Month |
| direction | TEXT | IMPORT or EXPORT |
| reporting_country | TEXT | Source country |
| sample_size | BIGINT | Number of shipments |
| min_price_usd_per_kg | NUMERIC | Minimum price |
| p25_price_usd_per_kg | NUMERIC | 25th percentile |
| median_price_usd_per_kg | NUMERIC | Median price |
| p75_price_usd_per_kg | NUMERIC | 75th percentile |
| max_price_usd_per_kg | NUMERIC | Maximum price |
| avg_price_usd_per_kg | NUMERIC | Average price |
| last_ledger_shipment_date | DATE | Latest shipment |
| updated_at | TIMESTAMPTZ | Last update |

**Grain:** `(hs_code_6, destination_country, year, month, direction, reporting_country)`

#### lane_stats Table (Restructured)

| Column | Type | Description |
|--------|------|-------------|
| lane_id | BIGSERIAL | Primary key |
| origin_country | TEXT | Origin country |
| destination_country | TEXT | Destination country |
| hs_code_6 | TEXT | HS code |
| total_shipments | BIGINT | Total shipment count |
| total_teu | NUMERIC | Total TEU |
| total_customs_value_usd | NUMERIC | Total value |
| total_qty_kg | NUMERIC | Total quantity |
| avg_price_usd_per_kg | NUMERIC | Average price |
| first_shipment_date | DATE | First shipment |
| last_shipment_date | DATE | Last shipment |
| top_carriers | JSONB | Top 5 carriers |
| reporting_countries | JSONB | Contributing countries |
| updated_at | TIMESTAMPTZ | Last update |

**Grain:** `(origin_country, destination_country, hs_code_6)`

#### Helper Table: analytics_watermarks

Tracks last processed date for incremental builds.

### 2. Core Module

**Location:** `etl/analytics/build_price_and_lanes.py`

| Component | Purpose |
|-----------|---------|
| `PriceAndLanesBuilder` | Main builder class |
| `PriceLanesBuildSummary` | Results dataclass |
| `_safe_float()` | Helper for NaN-safe conversions |
| `run_build_price_and_lanes()` | Main entry point |

### 3. Orchestration Script

**Location:** `scripts/run_build_price_and_lanes.py`

```bash
# Incremental build (default)
python scripts/run_build_price_and_lanes.py

# Full rebuild
python scripts/run_build_price_and_lanes.py --full-rebuild

# Corridors only
python scripts/run_build_price_and_lanes.py --corridors-only

# Lanes only
python scripts/run_build_price_and_lanes.py --lanes-only
```

### 4. Verification SQL

**Location:** `db/epic6_price_lanes_verification.sql`

---

## Record Counts

### Price Corridors (658 total)

| Country | Direction | Corridors | Sample Size |
|---------|-----------|-----------|-------------|
| INDIA | EXPORT | 604 | 8,000 |
| INDONESIA | EXPORT | 43 | 760 |
| INDONESIA | IMPORT | 1 | 1,000 |
| KENYA | EXPORT | 9 | 703 |
| KENYA | IMPORT | 1 | 1,000 |

### Lane Stats (130 total)

| Origin Country | Lanes | Shipments | Total Value USD |
|----------------|-------|-----------|-----------------|
| INDIA | 51 | 8,320 | $826,974,731 |
| INDONESIA | 43 | 762 | $442,028,819 |
| CHINA | 2 | 1,397 | $45,860,606 |
| KENYA | 8 | 703 | $34,230,086 |
| Others | 26 | 287 | Various |

---

## Sample Price Corridors

| HS Code | Destination | Period | Samples | Median Price |
|---------|-------------|--------|---------|--------------|
| 690721 | KENYA | 2025-11 | 1,000 | $6.19/kg |
| 690721 | INDONESIA | 2025-11 | 1,000 | $0.21/kg |
| 230230 | OMAN | 2025-11 | 275 | $0.10/kg |
| 230230 | QATAR | 2025-11 | 204 | $0.17/kg |
| 690721 | USA | 2025-11 | 133 | $3.77/kg |

---

## Incremental Processing Strategy

The builder uses a **watermark-based incremental strategy**:

1. **analytics_watermarks** table stores `max_shipment_date` per analytics type
2. On each run:
   - Get current watermark (last processed shipment_date)
   - Find max(shipment_date) in ledger
   - Apply 7-day lookback window for safety
   - Process only shipments in that date window
   - For price corridors: Recompute affected (hs6, dest, year, month, dir, reporting) buckets
   - For lane stats: Fully recompute affected (origin, dest, hs6) lanes
   - UPSERT into tables
3. Update watermarks after successful processing

**Benefits:**
- Processes only recent data by default
- Catches late-arriving shipments via lookback window
- Full rebuild available via `--full-rebuild` flag

---

## Idempotency Verification

| Run | Mode | Ledger Rows | Corridors | Lanes | Result |
|-----|------|-------------|-----------|-------|--------|
| 1 | Full Rebuild | 11,463 | 658 new | 130 new | Initial load |
| 2 | Incremental | 3,461 | 53 updated | 81 updated | Updates only |
| 3 | Incremental | (same window) | Updates | Updates | Same values |

✅ **Confirmed:** Re-running does not create duplicates. UPSERT overwrites with identical values.

---

## Consistency Verification

### Price Corridors

| Check | Status |
|-------|--------|
| Total sample_size across corridors | 11,463 |
| Qualifying ledger rows | 11,463 |
| Match | ✅ EXACT MATCH |

### Lane Stats

| Check | Status |
|-------|--------|
| Total shipments across lanes | 11,469 |
| Ledger rows with valid countries/HS6 | 11,469 |
| Match | ✅ EXACT MATCH |

---

## Integrity Verification

| Check | Result |
|-------|--------|
| NULL hs_code_6 in price_corridor | 0 ✅ |
| NULL hs_code_6 in lane_stats | 0 ✅ |
| NULL destination_country in price_corridor | 0 ✅ |
| NULL origin/destination in lane_stats | 0 ✅ |
| Negative prices in price_corridor | 0 ✅ |

---

## Ledger Integrity (Unchanged)

| Table | Row Count | Status |
|-------|-----------|--------|
| stg_shipments_raw | 11,469 | ✅ |
| stg_shipments_standardized | 11,469 | ✅ |
| global_trades_ledger | 11,469 | ✅ |

✅ **Confirmed:** No aggregation or deletion of shipments. Analytics are derived tables only.

---

## Pipeline Tracking Integration

All runs are tracked in `pipeline_runs`:

```sql
SELECT pipeline_name, started_at, status, rows_processed, rows_created, rows_updated
FROM pipeline_runs
WHERE pipeline_name = 'build_price_and_lanes'
ORDER BY started_at DESC;
```

Sample output:
```
build_price_and_lanes | 2025-11-30 13:06:22 | SUCCESS | 3461 | 0   | 134  (incremental)
build_price_and_lanes | 2025-11-30 13:06:12 | SUCCESS | 11463| 788 | 0    (full rebuild)
```

---

## Files Created/Modified

### New Files

| File | Purpose |
|------|---------|
| `db/migrations/004_epic6b_price_lanes.sql` | Schema migration |
| `etl/analytics/build_price_and_lanes.py` | Core builder module |
| `scripts/run_build_price_and_lanes.py` | CLI orchestration |
| `db/epic6_price_lanes_verification.sql` | Verification queries |
| `EPIC6_PRICE_LANES_IMPLEMENTATION_SUMMARY.md` | This document |

### Modified Files

| File | Change |
|------|--------|
| `etl/analytics/__init__.py` | Export price/lanes builder |
| `db/schema_v1.sql` | Add `build_price_and_lanes` to pipeline_runs constraint |

---

## Compatibility with EPIC 0-6A

| EPIC | Status | Impact |
|------|--------|--------|
| EPIC 0-1 (Ingestion) | ✅ Compatible | No changes |
| EPIC 2 (Standardization) | ✅ Compatible | No changes |
| EPIC 3 (Identity) | ✅ Compatible | No changes |
| EPIC 4 (Ledger) | ✅ Compatible | Reads from global_trades_ledger |
| EPIC 5 (Mirror) | ✅ Compatible | No interference |
| EPIC 6A (Profiles) | ✅ Compatible | Shared analytics module |

---

## Data Filtering Rules

### Price Corridor Qualifying Shipments:
- `price_usd_per_kg IS NOT NULL`
- `price_usd_per_kg > 0`
- `qty_kg > 0`
- `hs_code_6 IS NOT NULL`
- `destination_country IS NOT NULL`

### Lane Stats Qualifying Shipments:
- `origin_country IS NOT NULL`
- `destination_country IS NOT NULL`
- `hs_code_6 IS NOT NULL`

---

## Known Limitations

1. **Carrier data:** Uses `vessel_name` as carrier surrogate (actual carrier field may be added later)
2. **Transit days:** Not computed (requires export/import date matching)
3. **Percentiles:** Computed per month; finer granularity available on demand

---

## Future Improvements

1. Add carrier master table for better carrier identification
2. Add transit time calculations when data permits
3. Add price trend indicators (MoM, YoY changes)
4. Add market share calculations per lane
5. Create materialized views for dashboard queries

---

*Report generated: November 30, 2025*  
*Total price corridors: 658*  
*Total lane stats: 130*  
*All consistency checks: PASSED*  
*Ledger integrity: PRESERVED*
