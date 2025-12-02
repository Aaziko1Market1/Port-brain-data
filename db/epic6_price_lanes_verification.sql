-- =====================================================================
-- EPIC 6B: Price Corridors & Lane Stats - Verification Queries
-- GTI-OS Data Platform
-- =====================================================================
-- Run these queries to verify price corridor and lane stats build results
-- =====================================================================

-- =====================================================================
-- 1. ROW COUNTS
-- =====================================================================

-- 1.1 Total counts
SELECT 'price_corridor' as table_name, COUNT(*) as row_count FROM price_corridor
UNION ALL
SELECT 'lane_stats', COUNT(*) FROM lane_stats;

-- 1.2 Price corridors by reporting country
SELECT 
    reporting_country,
    direction,
    COUNT(*) as corridor_count,
    SUM(sample_size) as total_samples
FROM price_corridor
GROUP BY reporting_country, direction
ORDER BY reporting_country, direction;

-- 1.3 Lane stats by origin country
SELECT 
    origin_country,
    COUNT(*) as lane_count,
    SUM(total_shipments) as total_shipments,
    ROUND(SUM(total_customs_value_usd)::numeric, 2) as total_value_usd
FROM lane_stats
GROUP BY origin_country
ORDER BY total_value_usd DESC;

-- =====================================================================
-- 2. SAMPLE CORRIDOR RECORDS BY COUNTRY
-- =====================================================================

-- 2.1 Sample corridors for INDIA (5 records)
SELECT 
    hs_code_6,
    destination_country,
    year,
    month,
    direction,
    sample_size,
    ROUND(median_price_usd_per_kg::numeric, 4) as median_price,
    ROUND(min_price_usd_per_kg::numeric, 4) as min_price,
    ROUND(max_price_usd_per_kg::numeric, 4) as max_price
FROM price_corridor
WHERE reporting_country = 'INDIA'
ORDER BY sample_size DESC
LIMIT 5;

-- 2.2 Sample corridors for KENYA (5 records)
SELECT 
    hs_code_6,
    destination_country,
    year,
    month,
    direction,
    sample_size,
    ROUND(median_price_usd_per_kg::numeric, 4) as median_price,
    ROUND(min_price_usd_per_kg::numeric, 4) as min_price,
    ROUND(max_price_usd_per_kg::numeric, 4) as max_price
FROM price_corridor
WHERE reporting_country = 'KENYA'
ORDER BY sample_size DESC
LIMIT 5;

-- 2.3 Sample corridors for INDONESIA (5 records)
SELECT 
    hs_code_6,
    destination_country,
    year,
    month,
    direction,
    sample_size,
    ROUND(median_price_usd_per_kg::numeric, 4) as median_price,
    ROUND(min_price_usd_per_kg::numeric, 4) as min_price,
    ROUND(max_price_usd_per_kg::numeric, 4) as max_price
FROM price_corridor
WHERE reporting_country = 'INDONESIA'
ORDER BY sample_size DESC
LIMIT 5;

-- =====================================================================
-- 3. CONSISTENCY CHECKS - PRICE CORRIDOR
-- =====================================================================

-- 3.1 Pick a specific corridor and verify against ledger
-- This query selects one corridor and recomputes from ledger for comparison
WITH sample_corridor AS (
    SELECT hs_code_6, destination_country, year, month, direction, reporting_country
    FROM price_corridor
    LIMIT 1
),
ledger_recompute AS (
    SELECT 
        COUNT(*) as computed_sample_size,
        MIN(price_usd_per_kg) as computed_min,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_usd_per_kg) as computed_median,
        MAX(price_usd_per_kg) as computed_max
    FROM global_trades_ledger g
    JOIN sample_corridor sc 
        ON g.hs_code_6 = sc.hs_code_6
        AND g.destination_country = sc.destination_country
        AND EXTRACT(YEAR FROM g.shipment_date) = sc.year
        AND EXTRACT(MONTH FROM g.shipment_date) = sc.month
        AND g.direction = sc.direction
        AND g.reporting_country = sc.reporting_country
    WHERE g.price_usd_per_kg IS NOT NULL 
      AND g.price_usd_per_kg > 0 
      AND g.qty_kg > 0
)
SELECT 
    pc.hs_code_6,
    pc.year,
    pc.month,
    pc.sample_size as stored_sample_size,
    lr.computed_sample_size,
    CASE WHEN pc.sample_size = lr.computed_sample_size THEN 'MATCH' ELSE 'MISMATCH' END as sample_check,
    ROUND(pc.median_price_usd_per_kg::numeric, 4) as stored_median,
    ROUND(lr.computed_median::numeric, 4) as computed_median,
    CASE WHEN ABS(pc.median_price_usd_per_kg - lr.computed_median) < 0.01 THEN 'MATCH' ELSE 'MISMATCH' END as median_check
FROM price_corridor pc
JOIN sample_corridor sc 
    ON pc.hs_code_6 = sc.hs_code_6
    AND pc.destination_country = sc.destination_country
    AND pc.year = sc.year
    AND pc.month = sc.month
    AND pc.direction = sc.direction
    AND pc.reporting_country = sc.reporting_country
CROSS JOIN ledger_recompute lr;

-- 3.2 Aggregate sample_size check (should match ledger qualifying rows)
WITH corridor_totals AS (
    SELECT SUM(sample_size) as total_corridor_samples
    FROM price_corridor
),
ledger_qualifying AS (
    SELECT COUNT(*) as total_ledger_qualifying
    FROM global_trades_ledger
    WHERE price_usd_per_kg IS NOT NULL
      AND price_usd_per_kg > 0
      AND qty_kg > 0
      AND hs_code_6 IS NOT NULL
      AND destination_country IS NOT NULL
)
SELECT 
    ct.total_corridor_samples,
    lq.total_ledger_qualifying,
    CASE 
        WHEN ct.total_corridor_samples = lq.total_ledger_qualifying THEN 'EXACT MATCH'
        WHEN ABS(ct.total_corridor_samples - lq.total_ledger_qualifying) < 10 THEN 'CLOSE MATCH'
        ELSE 'MISMATCH - INVESTIGATE'
    END as status
FROM corridor_totals ct, ledger_qualifying lq;

-- =====================================================================
-- 4. CONSISTENCY CHECKS - LANE STATS
-- =====================================================================

-- 4.1 Pick a specific lane and verify against ledger
WITH sample_lane AS (
    SELECT origin_country, destination_country, hs_code_6
    FROM lane_stats
    LIMIT 1
),
ledger_recompute AS (
    SELECT 
        COUNT(*) as computed_shipments,
        COALESCE(SUM(customs_value_usd), 0) as computed_value,
        COALESCE(SUM(teu), 0) as computed_teu
    FROM global_trades_ledger g
    JOIN sample_lane sl 
        ON g.origin_country = sl.origin_country
        AND g.destination_country = sl.destination_country
        AND g.hs_code_6 = sl.hs_code_6
)
SELECT 
    ls.origin_country,
    ls.destination_country,
    ls.hs_code_6,
    ls.total_shipments as stored_shipments,
    lr.computed_shipments,
    CASE WHEN ls.total_shipments = lr.computed_shipments THEN 'MATCH' ELSE 'MISMATCH' END as shipment_check,
    ROUND(ls.total_customs_value_usd::numeric, 2) as stored_value,
    ROUND(lr.computed_value::numeric, 2) as computed_value,
    CASE WHEN ABS(ls.total_customs_value_usd - lr.computed_value) < 1 THEN 'MATCH' ELSE 'MISMATCH' END as value_check
FROM lane_stats ls
JOIN sample_lane sl 
    ON ls.origin_country = sl.origin_country
    AND ls.destination_country = sl.destination_country
    AND ls.hs_code_6 = sl.hs_code_6
CROSS JOIN ledger_recompute lr;

-- 4.2 Total shipments check
WITH lane_totals AS (
    SELECT SUM(total_shipments) as total_lane_shipments
    FROM lane_stats
),
ledger_totals AS (
    SELECT COUNT(*) as total_ledger_shipments
    FROM global_trades_ledger
    WHERE origin_country IS NOT NULL
      AND destination_country IS NOT NULL
      AND hs_code_6 IS NOT NULL
)
SELECT 
    lt.total_lane_shipments,
    lg.total_ledger_shipments,
    CASE 
        WHEN lt.total_lane_shipments = lg.total_ledger_shipments THEN 'EXACT MATCH'
        ELSE 'MISMATCH - INVESTIGATE'
    END as status
FROM lane_totals lt, ledger_totals lg;

-- =====================================================================
-- 5. INTEGRITY CHECKS
-- =====================================================================

-- 5.1 No NULL hs_code_6 in price_corridor
SELECT 'price_corridor NULL hs_code_6' as check_name,
       COUNT(*) as invalid_count
FROM price_corridor 
WHERE hs_code_6 IS NULL;

-- 5.2 No NULL hs_code_6 in lane_stats
SELECT 'lane_stats NULL hs_code_6' as check_name,
       COUNT(*) as invalid_count
FROM lane_stats 
WHERE hs_code_6 IS NULL;

-- 5.3 No NULL destination_country in price_corridor
SELECT 'price_corridor NULL destination_country' as check_name,
       COUNT(*) as invalid_count
FROM price_corridor 
WHERE destination_country IS NULL;

-- 5.4 No NULL origin/destination in lane_stats
SELECT 'lane_stats NULL countries' as check_name,
       COUNT(*) as invalid_count
FROM lane_stats 
WHERE origin_country IS NULL OR destination_country IS NULL;

-- 5.5 No negative prices in price_corridor
SELECT 'price_corridor negative prices' as check_name,
       COUNT(*) as invalid_count
FROM price_corridor 
WHERE min_price_usd_per_kg < 0 
   OR median_price_usd_per_kg < 0 
   OR max_price_usd_per_kg < 0;

-- 5.6 Combined integrity summary
SELECT 
    'INTEGRITY CHECK' as category,
    SUM(CASE WHEN check_name = 'null_hs6_pc' THEN cnt ELSE 0 END) as pc_null_hs6,
    SUM(CASE WHEN check_name = 'null_hs6_ls' THEN cnt ELSE 0 END) as ls_null_hs6,
    SUM(CASE WHEN check_name = 'null_dest_pc' THEN cnt ELSE 0 END) as pc_null_dest,
    SUM(CASE WHEN check_name = 'null_countries_ls' THEN cnt ELSE 0 END) as ls_null_countries,
    SUM(CASE WHEN check_name = 'negative_prices' THEN cnt ELSE 0 END) as negative_prices
FROM (
    SELECT 'null_hs6_pc' as check_name, COUNT(*) as cnt FROM price_corridor WHERE hs_code_6 IS NULL
    UNION ALL
    SELECT 'null_hs6_ls', COUNT(*) FROM lane_stats WHERE hs_code_6 IS NULL
    UNION ALL
    SELECT 'null_dest_pc', COUNT(*) FROM price_corridor WHERE destination_country IS NULL
    UNION ALL
    SELECT 'null_countries_ls', COUNT(*) FROM lane_stats WHERE origin_country IS NULL OR destination_country IS NULL
    UNION ALL
    SELECT 'negative_prices', COUNT(*) FROM price_corridor WHERE min_price_usd_per_kg < 0
) checks;

-- =====================================================================
-- 6. SAMPLE JSON DATA
-- =====================================================================

-- 6.1 Sample top_carriers from lane_stats
SELECT 
    origin_country,
    destination_country,
    hs_code_6,
    total_shipments,
    top_carriers
FROM lane_stats
WHERE jsonb_array_length(top_carriers) > 0
LIMIT 3;

-- 6.2 Sample reporting_countries from lane_stats
SELECT 
    origin_country,
    destination_country,
    hs_code_6,
    reporting_countries
FROM lane_stats
WHERE jsonb_array_length(reporting_countries) > 0
LIMIT 3;

-- =====================================================================
-- 7. PRICE DISTRIBUTION ANALYSIS
-- =====================================================================

-- 7.1 Price corridor statistics summary
SELECT 
    reporting_country,
    direction,
    COUNT(*) as corridor_count,
    ROUND(AVG(sample_size)::numeric, 0) as avg_sample_size,
    ROUND(AVG(median_price_usd_per_kg)::numeric, 4) as avg_median_price,
    ROUND(MIN(min_price_usd_per_kg)::numeric, 4) as overall_min_price,
    ROUND(MAX(max_price_usd_per_kg)::numeric, 4) as overall_max_price
FROM price_corridor
GROUP BY reporting_country, direction
ORDER BY reporting_country, direction;

-- =====================================================================
-- 8. LEDGER INTEGRITY (must remain unchanged)
-- =====================================================================

-- 8.1 Verify ledger row count unchanged
SELECT 
    'global_trades_ledger' as table_name,
    COUNT(*) as row_count,
    COUNT(DISTINCT transaction_id) as unique_transactions
FROM global_trades_ledger;

-- 8.2 Verify no shipment aggregation (ledger vs staging match)
SELECT 
    'LEDGER_VS_STAGING' as check_type,
    (SELECT COUNT(*) FROM global_trades_ledger) as ledger_count,
    (SELECT COUNT(*) FROM stg_shipments_standardized) as staging_count,
    CASE 
        WHEN (SELECT COUNT(*) FROM global_trades_ledger) = (SELECT COUNT(*) FROM stg_shipments_standardized) 
        THEN 'PASS' 
        ELSE 'FAIL' 
    END as status;

-- =====================================================================
-- 9. PIPELINE RUNS TRACKING
-- =====================================================================

-- 9.1 Build price and lanes run history
SELECT 
    run_id,
    started_at,
    completed_at,
    status,
    rows_processed,
    rows_created,
    rows_updated,
    error_message
FROM pipeline_runs
WHERE pipeline_name = 'build_price_and_lanes'
ORDER BY started_at DESC
LIMIT 10;

-- =====================================================================
-- 10. WATERMARKS STATUS
-- =====================================================================

-- 10.1 Analytics watermarks
SELECT 
    analytics_name,
    max_shipment_date,
    updated_at
FROM analytics_watermarks
ORDER BY analytics_name;

-- =====================================================================
-- END OF VERIFICATION QUERIES
-- =====================================================================
