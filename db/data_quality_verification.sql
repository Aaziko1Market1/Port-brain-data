-- =====================================================================
-- Data Quality Verification Queries
-- GTI-OS Data Platform Architecture v1.0
-- =====================================================================
-- 
-- Reusable data quality checks for all countries and formats.
-- Run these after any pipeline execution to verify data integrity.
--
-- Usage:
--   psql -U postgres -d aaziko_trade -f db/data_quality_verification.sql
-- =====================================================================

\echo '=============================================================='
\echo 'Data Quality Verification'
\echo '=============================================================='

-- =====================================================================
-- 1. RAW DATA SUMMARY
-- =====================================================================

\echo ''
\echo '1. Raw Data Summary (stg_shipments_raw)'
\echo '--------------------------------------------------------------'

SELECT 
    reporting_country,
    direction,
    source_format,
    COUNT(*) AS raw_rows
FROM stg_shipments_raw
GROUP BY reporting_country, direction, source_format
ORDER BY reporting_country, direction, source_format;

-- =====================================================================
-- 2. STANDARDIZED DATA QUALITY
-- =====================================================================

\echo ''
\echo '2. Standardized Data Quality (stg_shipments_standardized)'
\echo '--------------------------------------------------------------'

SELECT 
    reporting_country,
    direction,
    source_format,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN origin_country IS NULL THEN 1 ELSE 0 END) AS null_origin,
    SUM(CASE WHEN destination_country IS NULL THEN 1 ELSE 0 END) AS null_dest,
    SUM(CASE WHEN hs_code_6 IS NULL THEN 1 ELSE 0 END) AS null_hs6,
    SUM(CASE WHEN buyer_name_raw IS NULL OR buyer_name_raw = '' THEN 1 ELSE 0 END) AS null_buyer_name,
    SUM(CASE WHEN supplier_name_raw IS NULL OR supplier_name_raw = '' THEN 1 ELSE 0 END) AS null_supplier_name,
    SUM(CASE WHEN buyer_uuid IS NULL THEN 1 ELSE 0 END) AS null_buyer_uuid,
    SUM(CASE WHEN supplier_uuid IS NULL THEN 1 ELSE 0 END) AS null_supplier_uuid
FROM stg_shipments_standardized
GROUP BY reporting_country, direction, source_format
ORDER BY reporting_country, direction, source_format;

-- =====================================================================
-- 3. LEDGER DATA QUALITY
-- =====================================================================

\echo ''
\echo '3. Ledger Data Quality (global_trades_ledger)'
\echo '--------------------------------------------------------------'

SELECT 
    reporting_country,
    direction,
    COUNT(*) AS ledger_rows,
    SUM(CASE WHEN origin_country IS NULL THEN 1 ELSE 0 END) AS null_origin,
    SUM(CASE WHEN destination_country IS NULL THEN 1 ELSE 0 END) AS null_dest,
    SUM(CASE WHEN hs_code_6 IS NULL THEN 1 ELSE 0 END) AS null_hs6,
    SUM(CASE WHEN buyer_uuid IS NULL THEN 1 ELSE 0 END) AS null_buyer_uuid,
    SUM(CASE WHEN supplier_uuid IS NULL THEN 1 ELSE 0 END) AS null_supplier_uuid,
    SUM(CASE WHEN transaction_id IS NULL THEN 1 ELSE 0 END) AS null_transaction_id
FROM global_trades_ledger
GROUP BY reporting_country, direction
ORDER BY reporting_country, direction;

-- =====================================================================
-- 4. PIPELINE RECONCILIATION
-- =====================================================================

\echo ''
\echo '4. Pipeline Row Reconciliation (Raw → Standardized → Ledger)'
\echo '--------------------------------------------------------------'

SELECT 
    COALESCE(r.reporting_country, s.reporting_country, g.reporting_country) AS reporting_country,
    COALESCE(r.direction, s.direction, g.direction) AS direction,
    COALESCE(r.raw_rows, 0) AS raw_rows,
    COALESCE(s.std_rows, 0) AS std_rows,
    COALESCE(g.ledger_rows, 0) AS ledger_rows,
    COALESCE(r.raw_rows, 0) - COALESCE(s.std_rows, 0) AS raw_to_std_gap,
    COALESCE(s.std_rows, 0) - COALESCE(g.ledger_rows, 0) AS std_to_ledger_gap
FROM (
    SELECT reporting_country, direction, COUNT(*) AS raw_rows
    FROM stg_shipments_raw
    GROUP BY reporting_country, direction
) r
FULL OUTER JOIN (
    SELECT reporting_country, direction, COUNT(*) AS std_rows
    FROM stg_shipments_standardized
    GROUP BY reporting_country, direction
) s ON r.reporting_country = s.reporting_country AND r.direction = s.direction
FULL OUTER JOIN (
    SELECT reporting_country, direction, COUNT(*) AS ledger_rows
    FROM global_trades_ledger
    GROUP BY reporting_country, direction
) g ON COALESCE(r.reporting_country, s.reporting_country) = g.reporting_country 
   AND COALESCE(r.direction, s.direction) = g.direction
ORDER BY reporting_country, direction;

-- =====================================================================
-- 5. KENYA-SPECIFIC CHECKS
-- =====================================================================

\echo ''
\echo '5. Kenya Data Quality Summary'
\echo '--------------------------------------------------------------'

SELECT 
    direction,
    source_format,
    COUNT(*) AS rows,
    COUNT(DISTINCT origin_country) AS unique_origins,
    COUNT(DISTINCT destination_country) AS unique_destinations,
    COUNT(DISTINCT buyer_uuid) AS unique_buyers,
    COUNT(DISTINCT supplier_uuid) AS unique_suppliers
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA'
GROUP BY direction, source_format
ORDER BY direction, source_format;

\echo ''
\echo '6. Kenya Import - Origin Countries Check'
\echo '--------------------------------------------------------------'

SELECT 
    origin_country,
    COUNT(*) AS shipments
FROM global_trades_ledger
WHERE reporting_country = 'KENYA' AND direction = 'IMPORT'
GROUP BY origin_country
ORDER BY shipments DESC
LIMIT 15;

\echo ''
\echo '7. Kenya Export - Destination Countries Check'
\echo '--------------------------------------------------------------'

SELECT 
    destination_country,
    COUNT(*) AS shipments
FROM global_trades_ledger
WHERE reporting_country = 'KENYA' AND direction = 'EXPORT'
GROUP BY destination_country
ORDER BY shipments DESC
LIMIT 15;

\echo ''
\echo '8. Kenya Import - Destination = KENYA Check'
\echo '--------------------------------------------------------------'

SELECT 
    destination_country,
    COUNT(*) AS rows,
    CASE WHEN destination_country = 'KENYA' THEN 'PASS' ELSE 'FAIL' END AS check_result
FROM global_trades_ledger
WHERE reporting_country = 'KENYA' AND direction = 'IMPORT'
GROUP BY destination_country;

\echo ''
\echo '9. Kenya Export - Origin = KENYA Check'
\echo '--------------------------------------------------------------'

SELECT 
    origin_country,
    COUNT(*) AS rows,
    CASE WHEN origin_country = 'KENYA' THEN 'PASS' ELSE 'FAIL' END AS check_result
FROM global_trades_ledger
WHERE reporting_country = 'KENYA' AND direction = 'EXPORT'
GROUP BY origin_country;

-- =====================================================================
-- INDONESIA-SPECIFIC CHECKS
-- =====================================================================

\echo ''
\echo '10. Indonesia Data Quality Summary'
\echo '--------------------------------------------------------------'

SELECT 
    direction,
    source_format,
    COUNT(*) AS rows,
    COUNT(DISTINCT origin_country) AS unique_origins,
    COUNT(DISTINCT destination_country) AS unique_destinations,
    COUNT(DISTINCT buyer_uuid) AS unique_buyers,
    COUNT(DISTINCT supplier_uuid) AS unique_suppliers
FROM stg_shipments_standardized
WHERE reporting_country = 'INDONESIA'
GROUP BY direction, source_format
ORDER BY direction, source_format;

\echo ''
\echo '11. Indonesia Import - Destination = INDONESIA Check'
\echo '--------------------------------------------------------------'

SELECT 
    destination_country,
    COUNT(*) AS rows,
    CASE WHEN destination_country = 'INDONESIA' THEN 'PASS' ELSE 'FAIL' END AS check_result
FROM global_trades_ledger
WHERE reporting_country = 'INDONESIA' AND direction = 'IMPORT'
GROUP BY destination_country;

\echo ''
\echo '12. Indonesia Export - Origin = INDONESIA Check'
\echo '--------------------------------------------------------------'

SELECT 
    origin_country,
    COUNT(*) AS rows,
    CASE WHEN origin_country = 'INDONESIA' THEN 'PASS' ELSE 'FAIL' END AS check_result
FROM global_trades_ledger
WHERE reporting_country = 'INDONESIA' AND direction = 'EXPORT'
GROUP BY origin_country;

\echo ''
\echo '13. Indonesia Import - Top Origin Countries'
\echo '--------------------------------------------------------------'

SELECT 
    origin_country,
    COUNT(*) AS shipments
FROM global_trades_ledger
WHERE reporting_country = 'INDONESIA' AND direction = 'IMPORT'
GROUP BY origin_country
ORDER BY shipments DESC
LIMIT 10;

\echo ''
\echo '14. Indonesia Export - Top Destination Countries'
\echo '--------------------------------------------------------------'

SELECT 
    destination_country,
    COUNT(*) AS shipments
FROM global_trades_ledger
WHERE reporting_country = 'INDONESIA' AND direction = 'EXPORT'
GROUP BY destination_country
ORDER BY shipments DESC
LIMIT 10;

-- =====================================================================
-- 6. UUID COVERAGE
-- =====================================================================

\echo ''
\echo '10. UUID Coverage in Ledger'
\echo '--------------------------------------------------------------'

SELECT 
    reporting_country,
    direction,
    COUNT(*) AS total,
    SUM(CASE WHEN buyer_uuid IS NOT NULL AND supplier_uuid IS NOT NULL THEN 1 ELSE 0 END) AS with_both_uuids,
    ROUND(100.0 * SUM(CASE WHEN buyer_uuid IS NOT NULL AND supplier_uuid IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_coverage
FROM global_trades_ledger
GROUP BY reporting_country, direction
ORDER BY reporting_country, direction;

-- =====================================================================
-- 7. VALUE SANITY CHECKS
-- =====================================================================

\echo ''
\echo '11. Value Sanity Checks'
\echo '--------------------------------------------------------------'

SELECT 
    reporting_country,
    direction,
    COUNT(*) AS total,
    SUM(CASE WHEN customs_value_usd IS NULL THEN 1 ELSE 0 END) AS null_value,
    SUM(CASE WHEN customs_value_usd < 0 THEN 1 ELSE 0 END) AS negative_value,
    SUM(CASE WHEN price_usd_per_kg < 0 THEN 1 ELSE 0 END) AS negative_price,
    ROUND(MIN(customs_value_usd)::numeric, 2) AS min_value,
    ROUND(MAX(customs_value_usd)::numeric, 2) AS max_value,
    ROUND(AVG(customs_value_usd)::numeric, 2) AS avg_value
FROM global_trades_ledger
GROUP BY reporting_country, direction
ORDER BY reporting_country, direction;

-- =====================================================================
-- 8. ORGANIZATIONS CHECK
-- =====================================================================

\echo ''
\echo '12. Organizations Master Summary'
\echo '--------------------------------------------------------------'

SELECT 
    country_iso,
    type,
    COUNT(*) AS org_count
FROM organizations_master
GROUP BY country_iso, type
ORDER BY country_iso, type;

-- =====================================================================
-- END OF DATA QUALITY VERIFICATION
-- =====================================================================

\echo ''
\echo '=============================================================='
\echo 'Data Quality Verification Complete'
\echo '=============================================================='
