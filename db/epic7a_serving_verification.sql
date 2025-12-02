-- =====================================================================
-- EPIC 7A: Serving Views - Verification Queries
-- GTI-OS Data Platform
-- =====================================================================
-- Run these queries to verify serving layer implementation
-- =====================================================================

-- =====================================================================
-- 1. ROW COUNT SANITY CHECKS
-- =====================================================================

-- 1.1 Compare MV combos vs Ledger combos
SELECT 'MV vs Ledger Grain Comparison' as check_type;

SELECT
    'ledger' AS source,
    COUNT(DISTINCT (reporting_country, direction, hs_code_6, year, month)) AS combos
FROM global_trades_ledger
WHERE hs_code_6 IS NOT NULL

UNION ALL

SELECT
    'mv' AS source,
    COUNT(*) AS combos
FROM mv_country_hs_month_summary;

-- 1.2 View row counts
SELECT 
    'vw_buyer_360' AS view_name, COUNT(*) AS row_count FROM vw_buyer_360
UNION ALL
SELECT 
    'mv_country_hs_month_summary', COUNT(*) FROM mv_country_hs_month_summary
UNION ALL
SELECT 
    'vw_country_hs_dashboard', COUNT(*) FROM vw_country_hs_dashboard
UNION ALL
SELECT 
    'vw_buyer_hs_activity', COUNT(*) FROM vw_buyer_hs_activity;

-- =====================================================================
-- 2. BUYER 360 VERIFICATION
-- =====================================================================

-- 2.1 No NULL buyer_uuid (critical check)
SELECT 'Buyer 360 NULL Check' as check_type;
SELECT COUNT(*) AS null_buyers
FROM vw_buyer_360
WHERE buyer_uuid IS NULL;

-- 2.2 Top 10 buyers by value
SELECT 'Top 10 Buyers by Value' as check_type;
SELECT 
    buyer_uuid,
    buyer_name,
    buyer_country,
    total_shipments,
    total_value_usd,
    current_risk_level,
    buyer_classification
FROM vw_buyer_360
ORDER BY total_value_usd DESC NULLS LAST
LIMIT 10;

-- 2.3 Buyer 360 vs Ledger consistency
SELECT 'Buyer 360 vs Ledger Value Check' as check_type;
SELECT 
    'buyer_360' AS source,
    SUM(total_value_usd) AS total_value
FROM vw_buyer_360

UNION ALL

SELECT 
    'ledger' AS source,
    SUM(customs_value_usd) AS total_value
FROM global_trades_ledger
WHERE buyer_uuid IS NOT NULL;

-- 2.4 Risk level distribution in Buyer 360
SELECT 'Buyer Risk Level Distribution' as check_type;
SELECT 
    current_risk_level,
    COUNT(*) AS buyer_count,
    ROUND(AVG(total_value_usd)::numeric, 2) AS avg_value_usd
FROM vw_buyer_360
GROUP BY current_risk_level
ORDER BY 
    CASE current_risk_level 
        WHEN 'CRITICAL' THEN 1 
        WHEN 'HIGH' THEN 2 
        WHEN 'MEDIUM' THEN 3 
        WHEN 'LOW' THEN 4 
        ELSE 5 
    END;

-- 2.5 Sample top_hs6 JSON structure
SELECT 'Sample Buyer top_hs6 JSON' as check_type;
SELECT 
    buyer_name,
    total_value_usd,
    jsonb_pretty(top_hs6) AS top_hs6_formatted
FROM vw_buyer_360
WHERE jsonb_array_length(top_hs6) > 0
ORDER BY total_value_usd DESC
LIMIT 3;

-- =====================================================================
-- 3. COUNTRY-HS DASHBOARD VERIFICATION
-- =====================================================================

-- 3.1 Country distribution
SELECT 'Country Distribution in Dashboard' as check_type;
SELECT 
    reporting_country,
    direction,
    COUNT(*) AS hs_month_combos,
    SUM(shipment_count) AS total_shipments,
    SUM(total_value_usd) AS total_value
FROM vw_country_hs_dashboard
GROUP BY reporting_country, direction
ORDER BY total_value DESC;

-- 3.2 Top HS codes by value
SELECT 'Top 10 HS Codes by Value' as check_type;
SELECT 
    hs_code_6,
    SUM(shipment_count) AS total_shipments,
    SUM(total_value_usd) AS total_value,
    COUNT(DISTINCT reporting_country) AS countries
FROM vw_country_hs_dashboard
GROUP BY hs_code_6
ORDER BY total_value DESC
LIMIT 10;

-- 3.3 Value share calculation check (should sum to ~100% per country/direction/month)
SELECT 'Value Share Sanity Check' as check_type;
SELECT 
    reporting_country,
    direction,
    year,
    month,
    ROUND(SUM(value_share_pct)::numeric, 1) AS total_share_pct
FROM vw_country_hs_dashboard
GROUP BY reporting_country, direction, year, month
HAVING ABS(SUM(value_share_pct) - 100) > 1  -- Allow 1% tolerance
LIMIT 5;

-- 3.4 Risk summary in dashboard
SELECT 'Dashboard Risk Summary' as check_type;
SELECT 
    reporting_country,
    SUM(high_risk_shipments) AS total_high_risk_shipments,
    SUM(high_risk_buyers) AS total_high_risk_buyers,
    SUM(shipment_count) AS total_shipments,
    ROUND(SUM(high_risk_shipments)::numeric / NULLIF(SUM(shipment_count), 0) * 100, 2) AS high_risk_pct
FROM vw_country_hs_dashboard
GROUP BY reporting_country
ORDER BY high_risk_pct DESC NULLS LAST;

-- =====================================================================
-- 4. LINKAGE CHECKS
-- =====================================================================

-- 4.1 Buyer 360 linkage to organizations_master
SELECT 'Buyer 360 Organization Linkage' as check_type;
SELECT 
    COUNT(*) AS total_buyers,
    SUM(CASE WHEN om.org_uuid IS NOT NULL THEN 1 ELSE 0 END) AS linked_to_org,
    SUM(CASE WHEN om.org_uuid IS NULL THEN 1 ELSE 0 END) AS orphaned
FROM vw_buyer_360 b360
LEFT JOIN organizations_master om ON b360.buyer_uuid = om.org_uuid;

-- 4.2 Buyer 360 linkage to risk_scores
SELECT 'Buyer 360 Risk Linkage' as check_type;
SELECT 
    COUNT(*) AS total_buyers,
    SUM(CASE WHEN current_risk_level != 'UNSCORED' THEN 1 ELSE 0 END) AS with_risk_score,
    SUM(CASE WHEN current_risk_level = 'UNSCORED' THEN 1 ELSE 0 END) AS without_risk_score
FROM vw_buyer_360;

-- =====================================================================
-- 5. LEDGER INTEGRITY (must remain unchanged)
-- =====================================================================

SELECT 'Ledger Integrity Check' as check_type;
SELECT 
    'global_trades_ledger' AS table_name,
    COUNT(*) AS row_count,
    COUNT(DISTINCT transaction_id) AS unique_transactions
FROM global_trades_ledger;

-- =====================================================================
-- 6. PERFORMANCE HINT CHECKS
-- =====================================================================

-- 6.1 Index usage check for common dashboard query
SELECT 'Index Usage Check (EXPLAIN)' as check_type;
EXPLAIN (COSTS OFF)
SELECT *
FROM mv_country_hs_month_summary
WHERE reporting_country = 'INDIA'
  AND direction = 'EXPORT'
  AND hs_code_6 = '610990'
ORDER BY year DESC, month DESC
LIMIT 12;

-- 6.2 Index usage check for buyer query
EXPLAIN (COSTS OFF)
SELECT *
FROM vw_buyer_360
WHERE buyer_country = 'KENYA'
ORDER BY total_value_usd DESC
LIMIT 25;

-- =====================================================================
-- 7. SAMPLE BUSINESS QUERIES
-- =====================================================================

-- 7.1 Top 25 safe buyers for HS 690721 in KENYA
SELECT 'Sample Query: Top Safe Buyers for HS 690721 in KENYA' as check_type;
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
LIMIT 10;

-- 7.2 Monthly dashboard for INDIA IMPORT last 6 months
SELECT 'Sample Query: INDIA IMPORT Monthly Dashboard' as check_type;
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
  AND direction = 'IMPORT'
ORDER BY year DESC, month DESC, total_value_usd DESC
LIMIT 20;

-- =====================================================================
-- 8. PIPELINE RUNS CHECK
-- =====================================================================

SELECT 'Pipeline Runs for serving_views' as check_type;
SELECT 
    run_id,
    started_at,
    completed_at,
    status,
    rows_processed,
    metadata
FROM pipeline_runs
WHERE pipeline_name = 'serving_views'
ORDER BY started_at DESC
LIMIT 5;

-- =====================================================================
-- 9. COMBINED SUMMARY
-- =====================================================================

SELECT 
    'EPIC 7A SUMMARY' AS report,
    (SELECT COUNT(*) FROM vw_buyer_360) AS buyer_360_count,
    (SELECT COUNT(*) FROM mv_country_hs_month_summary) AS mv_count,
    (SELECT COUNT(DISTINCT reporting_country) FROM mv_country_hs_month_summary) AS countries,
    (SELECT COUNT(DISTINCT hs_code_6) FROM mv_country_hs_month_summary) AS hs_codes,
    (SELECT COUNT(*) FROM vw_buyer_360 WHERE current_risk_level != 'UNSCORED') AS buyers_with_risk,
    (SELECT COUNT(*) FROM global_trades_ledger) AS ledger_row_count;

-- =====================================================================
-- END OF VERIFICATION QUERIES
-- =====================================================================
