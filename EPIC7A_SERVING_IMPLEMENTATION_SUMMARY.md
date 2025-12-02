# EPIC 7A - Buyer 360 & HS Dashboard Serving Layer Implementation Summary

**Date:** 2025-11-30  
**Platform:** GTI-OS Data Platform v1.0  
**Status:** ✅ COMPLETE

---

## 1. Overview

EPIC 7A creates an **LLM-friendly serving layer** with pre-computed views that enable single-query answers for common business questions like:

> "Show me top N buyers for HS X in country Y, with risk + price corridor + lane context"

### Key Principles

- **Read-only views**: No new data storage (except materialized view for performance)
- **Set-based SQL**: All aggregations done in SQL, no Python loops
- **Completeness**: LEFT JOINs ensure buyers without risk scores still appear
- **LLM-optimized**: Clear column names, pre-computed aggregates, JSON arrays for nested data

---

## 2. Views Created

### 2.1 `vw_buyer_360` - Buyer Intelligence View

**Purpose:** One row per buyer organization with complete trade intelligence.

| Column Group | Columns | Description |
|--------------|---------|-------------|
| **Identity** | `buyer_uuid`, `buyer_name`, `buyer_country`, `buyer_classification` | Organization identity and persona |
| **Volume** | `total_shipments`, `total_value_usd`, `total_qty_kg`, `total_teu` | Aggregated trade volumes |
| **Activity** | `first_shipment_date`, `last_shipment_date`, `active_years` | Activity timeline |
| **Diversity** | `unique_hs_codes`, `unique_origin_countries`, `unique_suppliers` | Business diversity metrics |
| **Product Mix** | `top_hs6` (JSONB) | Top 5 HS codes with value and share % |
| **Lane Mix** | `top_origin_countries` (JSONB) | Top 5 origin countries |
| **Risk** | `current_risk_level`, `current_risk_score`, `has_ghost_flag`, `risk_engine_version` | Latest risk assessment |
| **Metadata** | `last_profile_updated_at`, `last_risk_scored_at` | Freshness timestamps |

**Row Count:** 685 buyers

### 2.2 `mv_country_hs_month_summary` - Materialized Dashboard View

**Purpose:** Pre-aggregated metrics for fast country/HS/month dashboards.

**Grain:** `(reporting_country, direction, hs_code_6, year, month)`

| Column | Description |
|--------|-------------|
| `shipment_count` | Number of shipments |
| `unique_buyers` | Distinct buyer count |
| `unique_suppliers` | Distinct supplier count |
| `total_value_usd` | Sum of customs value |
| `total_qty_kg` | Sum of quantity |
| `total_teu` | Sum of TEU |
| `avg_price_usd_per_kg` | Average unit price |
| `high_risk_shipments` | Count of HIGH/CRITICAL risk shipments |
| `high_risk_buyers` | Count of HIGH/CRITICAL risk buyers |
| `avg_value_per_shipment_usd` | Derived: value / shipments |
| `refreshed_at` | Last refresh timestamp |

**Row Count:** 99 country/HS/month combinations

### 2.3 `vw_country_hs_dashboard` - Dashboard View

**Purpose:** Clean interface on top of materialized view with additional derived columns.

**Additional Columns:**
- `value_share_pct`: Share of HS code within country/direction/month
- `high_risk_shipment_pct`: Percentage of high-risk shipments

### 2.4 `vw_buyer_hs_activity` - Helper View

**Purpose:** Buyer activity by HS code for "Top buyers for HS X" queries.

**Grain:** `(buyer_uuid, hs_code_6, reporting_country, direction)`

**Row Count:** 979 buyer-HS combinations

---

## 3. How to Refresh

### Automated Refresh (Recommended)

```bash
python scripts/run_serving_refresh.py
```

**Options:**
- `--no-concurrent`: Use non-concurrent refresh (for first refresh or empty MVs)
- `--log-level DEBUG`: Verbose logging

### Manual Refresh

```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_country_hs_month_summary;
```

### Refresh Frequency

- **Recommended:** After each risk engine run or daily
- **Note:** `vw_buyer_360` is a regular view (always fresh), only `mv_country_hs_month_summary` needs refresh

---

## 4. Example Business Queries

### Query 1: Top 25 Safe Buyers for HS Code in Country

```sql
SELECT 
    b.buyer_uuid,
    b.buyer_name,
    b.total_shipments,
    b.total_value_usd,
    b.current_risk_level,
    b.buyer_classification
FROM vw_buyer_360 b
WHERE EXISTS (
    SELECT 1
    FROM global_trades_ledger g
    WHERE g.buyer_uuid = b.buyer_uuid
      AND g.hs_code_6 = '690721'
)
AND b.current_risk_level IN ('LOW', 'MEDIUM', 'UNSCORED')
ORDER BY b.total_value_usd DESC
LIMIT 25;
```

### Query 2: Monthly Dashboard for Country/Direction

```sql
SELECT 
    hs_code_6,
    year,
    month,
    shipment_count,
    total_value_usd,
    unique_buyers,
    value_share_pct,
    high_risk_shipment_pct
FROM vw_country_hs_dashboard
WHERE reporting_country = 'INDIA'
  AND direction = 'EXPORT'
ORDER BY year DESC, month DESC, total_value_usd DESC
LIMIT 20;
```

### Query 3: Buyer Product Portfolio

```sql
SELECT 
    buyer_name,
    buyer_country,
    total_value_usd,
    jsonb_pretty(top_hs6) AS product_mix,
    current_risk_level
FROM vw_buyer_360
WHERE total_value_usd > 1000000
ORDER BY total_value_usd DESC
LIMIT 10;
```

### Query 4: High-Risk HS Codes by Country

```sql
SELECT 
    reporting_country,
    hs_code_6,
    SUM(shipment_count) AS total_shipments,
    SUM(high_risk_shipments) AS risky_shipments,
    ROUND(SUM(high_risk_shipments)::numeric / NULLIF(SUM(shipment_count), 0) * 100, 1) AS risk_pct
FROM vw_country_hs_dashboard
GROUP BY reporting_country, hs_code_6
HAVING SUM(high_risk_shipments) > 0
ORDER BY risk_pct DESC
LIMIT 20;
```

---

## 5. Verified Statistics

| Metric | Value |
|--------|-------|
| `vw_buyer_360` rows | 685 |
| `mv_country_hs_month_summary` rows | 99 |
| `vw_country_hs_dashboard` rows | 99 |
| `vw_buyer_hs_activity` rows | 979 |
| MV vs Ledger grain match | ✅ PASS |
| NULL buyer_uuid in buyer_360 | 0 |
| Ledger integrity | ✅ Unchanged (11,469 rows) |

### Buyer Risk Distribution

| Risk Level | Count |
|------------|-------|
| UNSCORED | 665 |
| MEDIUM | 17 |
| HIGH | 3 |

### Dashboard Coverage

| Country | Direction | Shipments | Value USD |
|---------|-----------|-----------|-----------|
| INDIA | EXPORT | 8,000 | $813M |
| INDONESIA | IMPORT | 1,002 | $46M |
| KENYA | EXPORT | 703 | $34M |
| KENYA | IMPORT | 1,002 | $22M |

---

## 6. File Changes

### New Files

| File | Purpose |
|------|---------|
| `db/migrations/006_epic7a_serving_views.sql` | Migration creating all views |
| `scripts/run_serving_refresh.py` | Refresh orchestration script |
| `db/epic7a_serving_verification.sql` | Verification queries |

### Modified Files

| File | Change |
|------|--------|
| `db/schema_v1.sql` | Added `serving_views` to pipeline constraint, view documentation |

---

## 7. Pipeline Integration

### Pipeline Tracking

```sql
SELECT * FROM pipeline_runs 
WHERE pipeline_name = 'serving_views' 
ORDER BY started_at DESC;
```

### Typical Run Output

```
VIEW ROW COUNTS:
  mv_country_hs_month_summary:  99
  vw_buyer_360:                 685

DASHBOARD COVERAGE:
  Unique countries:     3
  Unique HS codes:      9
  Year-month periods:   15

ELAPSED TIME: 0.19 seconds
STATUS: SUCCESS
```

---

## 8. Index Strategy

### Materialized View Indexes

```sql
-- Unique index (enables CONCURRENTLY refresh)
CREATE UNIQUE INDEX idx_mv_chs_grain 
    ON mv_country_hs_month_summary(reporting_country, direction, hs_code_6, year, month);

-- Query performance indexes
CREATE INDEX idx_mv_chs_country ON mv_country_hs_month_summary(reporting_country);
CREATE INDEX idx_mv_chs_direction ON mv_country_hs_month_summary(direction);
CREATE INDEX idx_mv_chs_hs6 ON mv_country_hs_month_summary(hs_code_6);
CREATE INDEX idx_mv_chs_period ON mv_country_hs_month_summary(year DESC, month DESC);
CREATE INDEX idx_mv_chs_value ON mv_country_hs_month_summary(total_value_usd DESC);
```

---

## 9. Known Limitations

1. **Website/Email fields**: `primary_website` and `primary_email_domain` return NULL (not stored in current schema)

2. **UNSCORED buyers**: 97% of buyers show as UNSCORED because risk engine only scored buyers with $500K+ volume

3. **MV Staleness**: `mv_country_hs_month_summary` must be refreshed after ledger updates; `vw_buyer_360` is always fresh

4. **Performance on large datasets**: For 100M+ rows, consider partitioning the MV or adding date filters to base query

---

## 10. Future Improvements

1. **Add more serving views:**
   - `vw_exporter_360` for supplier intelligence
   - `vw_hs_code_profile` for product intelligence

2. **Website/email enrichment:**
   - Extend organizations_master with contact fields
   - Populate from external data sources

3. **MV partitioning:**
   - For scale, partition MV by year or reporting_country

4. **Caching layer:**
   - Add Redis/Memcached for frequently-queried dashboards

---

## 11. LLM/API Usage

### Recommended Pattern

```python
# For LLM query answering
def get_buyers_for_hs(hs_code, country, max_results=25):
    return db.execute_query("""
        SELECT buyer_name, total_value_usd, current_risk_level
        FROM vw_buyer_360
        WHERE EXISTS (
            SELECT 1 FROM global_trades_ledger g
            WHERE g.buyer_uuid = vw_buyer_360.buyer_uuid
              AND g.hs_code_6 = %s
        )
        AND buyer_country = %s
        ORDER BY total_value_usd DESC
        LIMIT %s
    """, (hs_code, country, max_results))
```

### View Selection Guide

| Question Type | Use View |
|---------------|----------|
| "Top buyers for HS X in country Y" | `vw_buyer_360` + ledger EXISTS |
| "Monthly trade trends for India" | `vw_country_hs_dashboard` |
| "Buyer risk profile" | `vw_buyer_360` |
| "Which HS codes does buyer X trade?" | `vw_buyer_hs_activity` |

---

## Conclusion

EPIC 7A successfully implements an LLM-friendly serving layer with:

- ✅ `vw_buyer_360`: 685 buyers with complete trade intelligence
- ✅ `mv_country_hs_month_summary`: 99 pre-aggregated dashboard rows
- ✅ `vw_country_hs_dashboard`: Clean dashboard interface
- ✅ `vw_buyer_hs_activity`: Buyer-HS helper view
- ✅ Refresh script with pipeline tracking
- ✅ MV ↔ Ledger grain match verified
- ✅ Zero NULL buyer_uuid (linkage integrity)
- ✅ Ledger immutability preserved

The serving layer is ready for LLM/API integration, enabling single-query answers for common business questions.
