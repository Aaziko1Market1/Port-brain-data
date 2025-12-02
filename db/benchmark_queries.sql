-- =====================================================================
-- EPIC 8 - Performance Benchmark Queries
-- =====================================================================
-- These queries represent the most critical operations in GTI-OS:
-- 1. Buyer Hunter aggregations
-- 2. HS Dashboard summaries
-- 3. Risk engine queries
-- 4. Serving view lookups
-- =====================================================================

-- ---------------------------------------------------------------------
-- QUERY 1: buyer_hunter_lane_agg
-- Purpose: Buyer Hunter scoring - lane aggregation by HS code + destination
-- Used by: /api/v1/buyer-hunter/top and /api/v1/buyer-hunter/search
-- ---------------------------------------------------------------------
-- buyer_hunter_lane_agg
SELECT 
    g.buyer_uuid,
    g.destination_country,
    SUM(g.customs_value_usd) AS total_value_usd_12m,
    COUNT(*) AS total_shipments_12m,
    AVG(g.customs_value_usd) AS avg_shipment_value_usd,
    COUNT(DISTINCT (g.year, g.month)) AS months_with_shipments,
    COUNT(DISTINCT g.year) AS years_active
FROM global_trades_ledger g
WHERE g.hs_code_6 = '690721'
  AND g.shipment_date >= CURRENT_DATE - INTERVAL '12 months'
  AND g.buyer_uuid IS NOT NULL
GROUP BY g.buyer_uuid, g.destination_country
ORDER BY total_value_usd_12m DESC
LIMIT 50;

-- ---------------------------------------------------------------------
-- QUERY 2: buyer_hunter_full
-- Purpose: Full Buyer Hunter query with joins (as used in API)
-- Used by: /api/v1/buyer-hunter/top
-- ---------------------------------------------------------------------
-- buyer_hunter_full
WITH buyer_hs_stats AS (
    SELECT 
        g.buyer_uuid,
        g.destination_country,
        SUM(g.customs_value_usd) AS total_value_usd_12m,
        COUNT(*) AS total_shipments_12m,
        AVG(g.customs_value_usd) AS avg_shipment_value_usd,
        COUNT(DISTINCT (g.year, g.month)) AS months_with_shipments_12m,
        COUNT(DISTINCT g.year) AS years_active
    FROM global_trades_ledger g
    WHERE g.hs_code_6 = '690721'
      AND g.shipment_date >= CURRENT_DATE - INTERVAL '12 months'
      AND g.buyer_uuid IS NOT NULL
    GROUP BY g.buyer_uuid, g.destination_country
),
buyer_total_value AS (
    SELECT 
        g.buyer_uuid,
        SUM(g.customs_value_usd) AS total_all_hs_value
    FROM global_trades_ledger g
    WHERE g.shipment_date >= CURRENT_DATE - INTERVAL '12 months'
      AND g.buyer_uuid IS NOT NULL
    GROUP BY g.buyer_uuid
)
SELECT 
    bhs.buyer_uuid,
    bhs.destination_country,
    bhs.total_value_usd_12m,
    bhs.total_shipments_12m,
    bhs.avg_shipment_value_usd,
    CASE 
        WHEN btv.total_all_hs_value > 0 
        THEN (bhs.total_value_usd_12m / btv.total_all_hs_value * 100)
        ELSE 0 
    END AS hs_share_pct,
    bhs.months_with_shipments_12m,
    bhs.years_active
FROM buyer_hs_stats bhs
LEFT JOIN buyer_total_value btv ON bhs.buyer_uuid = btv.buyer_uuid
WHERE bhs.total_value_usd_12m >= 50000
ORDER BY bhs.total_value_usd_12m DESC
LIMIT 50;

-- ---------------------------------------------------------------------
-- QUERY 3: hs_dashboard_monthly
-- Purpose: HS Dashboard - monthly summary by country
-- Used by: /api/v1/hs-dashboard
-- ---------------------------------------------------------------------
-- hs_dashboard_monthly
SELECT 
    reporting_country,
    hs_code_6,
    year,
    month,
    COUNT(*) as shipment_count,
    SUM(customs_value_usd) as total_value_usd,
    SUM(qty_kg) as total_qty_kg,
    COUNT(DISTINCT buyer_uuid) as unique_buyers,
    COUNT(DISTINCT supplier_uuid) as unique_suppliers
FROM global_trades_ledger
WHERE hs_code_6 = '690721'
  AND year >= 2023
GROUP BY reporting_country, hs_code_6, year, month
ORDER BY year DESC, month DESC, total_value_usd DESC;

-- ---------------------------------------------------------------------
-- QUERY 4: hs_dashboard_countries
-- Purpose: HS Dashboard - aggregation by origin/destination
-- Used by: /api/v1/hs-dashboard
-- ---------------------------------------------------------------------
-- hs_dashboard_countries
SELECT 
    origin_country,
    destination_country,
    COUNT(*) as shipment_count,
    SUM(customs_value_usd) as total_value_usd,
    AVG(customs_value_usd) as avg_shipment_value,
    SUM(qty_kg) as total_qty_kg
FROM global_trades_ledger
WHERE hs_code_6 = '690721'
  AND shipment_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY origin_country, destination_country
ORDER BY total_value_usd DESC
LIMIT 100;

-- ---------------------------------------------------------------------
-- QUERY 5: risk_top_shipments
-- Purpose: Top risky shipments joined with ledger
-- Used by: /api/v1/risk/top-shipments
-- ---------------------------------------------------------------------
-- risk_top_shipments
SELECT 
    rs.entity_id,
    rs.risk_level,
    rs.risk_score,
    rs.main_reason_code,
    g.hs_code_6,
    g.customs_value_usd,
    g.origin_country,
    g.destination_country,
    g.shipment_date
FROM risk_scores rs
JOIN global_trades_ledger g 
    ON rs.entity_id = g.transaction_id
WHERE rs.entity_type = 'SHIPMENT'
  AND rs.risk_level IN ('HIGH', 'CRITICAL')
ORDER BY rs.risk_score DESC
LIMIT 100;

-- ---------------------------------------------------------------------
-- QUERY 6: risk_top_buyers
-- Purpose: Top risky buyers with aggregated stats
-- Used by: /api/v1/risk/top-buyers
-- ---------------------------------------------------------------------
-- risk_top_buyers
SELECT 
    rs.entity_id as buyer_uuid,
    rs.risk_level,
    rs.risk_score,
    rs.main_reason_code,
    COUNT(DISTINCT g.transaction_id) as shipment_count,
    SUM(g.customs_value_usd) as total_value_usd
FROM risk_scores rs
LEFT JOIN global_trades_ledger g ON rs.entity_id = g.buyer_uuid
WHERE rs.entity_type = 'BUYER'
  AND rs.risk_level IN ('HIGH', 'CRITICAL', 'MEDIUM')
GROUP BY rs.entity_id, rs.risk_level, rs.risk_score, rs.main_reason_code
ORDER BY rs.risk_score DESC
LIMIT 50;

-- ---------------------------------------------------------------------
-- QUERY 7: vw_buyer_360_lookup
-- Purpose: Buyer 360 view lookup for single buyer
-- Used by: /api/v1/buyers/{uuid}/360
-- ---------------------------------------------------------------------
-- vw_buyer_360_lookup
SELECT * 
FROM vw_buyer_360 
WHERE buyer_uuid = (
    SELECT buyer_uuid 
    FROM global_trades_ledger 
    WHERE buyer_uuid IS NOT NULL 
    LIMIT 1
);

-- ---------------------------------------------------------------------
-- QUERY 8: country_hs_summary
-- Purpose: Country-level HS summary (dashboard overview)
-- Used by: /api/v1/meta/stats, dashboard
-- ---------------------------------------------------------------------
-- country_hs_summary
SELECT 
    reporting_country,
    direction,
    COUNT(DISTINCT hs_code_6) as unique_hs_codes,
    COUNT(*) as total_shipments,
    SUM(customs_value_usd) as total_value_usd,
    COUNT(DISTINCT buyer_uuid) as unique_buyers,
    COUNT(DISTINCT supplier_uuid) as unique_suppliers
FROM global_trades_ledger
WHERE year >= 2023
GROUP BY reporting_country, direction
ORDER BY total_value_usd DESC;

-- ---------------------------------------------------------------------
-- QUERY 9: buyer_hs_activity
-- Purpose: Buyer HS activity aggregation
-- Used by: vw_buyer_hs_activity, buyer profiles
-- ---------------------------------------------------------------------
-- buyer_hs_activity
SELECT 
    buyer_uuid,
    hs_code_6,
    year,
    COUNT(*) as shipment_count,
    SUM(customs_value_usd) as total_value_usd,
    SUM(qty_kg) as total_qty_kg,
    MIN(shipment_date) as first_shipment,
    MAX(shipment_date) as last_shipment
FROM global_trades_ledger
WHERE buyer_uuid IS NOT NULL
  AND shipment_date >= CURRENT_DATE - INTERVAL '24 months'
GROUP BY buyer_uuid, hs_code_6, year
ORDER BY total_value_usd DESC
LIMIT 1000;

-- ---------------------------------------------------------------------
-- QUERY 10: full_table_scan_baseline
-- Purpose: Baseline full table aggregation (worst case)
-- Used by: Performance baseline measurement
-- ---------------------------------------------------------------------
-- full_table_scan_baseline
SELECT 
    COUNT(*) as total_rows,
    COUNT(DISTINCT buyer_uuid) as unique_buyers,
    COUNT(DISTINCT supplier_uuid) as unique_suppliers,
    COUNT(DISTINCT hs_code_6) as unique_hs_codes,
    SUM(customs_value_usd) as total_value,
    MIN(shipment_date) as min_date,
    MAX(shipment_date) as max_date
FROM global_trades_ledger;
