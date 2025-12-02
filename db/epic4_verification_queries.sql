-- =====================================================================
-- EPIC 4 - Global Trades Ledger Verification Queries
-- GTI-OS Data Platform Architecture v1.0
-- =====================================================================
-- 
-- These queries verify the global_trades_ledger population:
-- 1. Row reconciliation between staging and ledger
-- 2. Data integrity checks
-- 3. Sample data verification
-- 4. Analytics readiness checks
--
-- Usage:
--   psql -U postgres -d aaziko_trade -f db/epic4_verification_queries.sql
-- =====================================================================

\echo '=============================================================='
\echo 'EPIC 4 - Global Trades Ledger Verification Queries'
\echo '=============================================================='

-- =====================================================================
-- 1. ROW RECONCILIATION: STAGING vs LEDGER
-- =====================================================================

\echo ''
\echo '1. Staging Table Row Counts (with UUID coverage)'
\echo '--------------------------------------------------------------'

SELECT 
    reporting_country,
    direction,
    COUNT(*) AS staging_rows,
    SUM(CASE WHEN buyer_uuid IS NOT NULL AND supplier_uuid IS NOT NULL THEN 1 ELSE 0 END) AS staging_with_both_uuids,
    SUM(CASE WHEN buyer_uuid IS NOT NULL THEN 1 ELSE 0 END) AS staging_with_buyer_uuid,
    SUM(CASE WHEN supplier_uuid IS NOT NULL THEN 1 ELSE 0 END) AS staging_with_supplier_uuid
FROM stg_shipments_standardized
WHERE reporting_country IN ('INDIA', 'KENYA')
GROUP BY reporting_country, direction
ORDER BY reporting_country, direction;

\echo ''
\echo '2. Ledger Table Row Counts (with UUID coverage)'
\echo '--------------------------------------------------------------'

SELECT 
    reporting_country,
    direction,
    COUNT(*) AS ledger_rows,
    SUM(CASE WHEN buyer_uuid IS NOT NULL AND supplier_uuid IS NOT NULL THEN 1 ELSE 0 END) AS ledger_with_both_uuids,
    SUM(CASE WHEN buyer_uuid IS NOT NULL THEN 1 ELSE 0 END) AS ledger_with_buyer_uuid,
    SUM(CASE WHEN supplier_uuid IS NOT NULL THEN 1 ELSE 0 END) AS ledger_with_supplier_uuid
FROM global_trades_ledger
WHERE reporting_country IN ('INDIA', 'KENYA')
GROUP BY reporting_country, direction
ORDER BY reporting_country, direction;

\echo ''
\echo '3. Row Count Comparison: Staging vs Ledger'
\echo '--------------------------------------------------------------'

SELECT 
    COALESCE(s.reporting_country, g.reporting_country) AS reporting_country,
    COALESCE(s.direction, g.direction) AS direction,
    COALESCE(s.staging_rows, 0) AS staging_rows,
    COALESCE(g.ledger_rows, 0) AS ledger_rows,
    COALESCE(s.staging_rows, 0) - COALESCE(g.ledger_rows, 0) AS difference
FROM (
    SELECT reporting_country, direction, COUNT(*) AS staging_rows
    FROM stg_shipments_standardized
    WHERE reporting_country IN ('INDIA', 'KENYA')
    GROUP BY reporting_country, direction
) s
FULL OUTER JOIN (
    SELECT reporting_country, direction, COUNT(*) AS ledger_rows
    FROM global_trades_ledger
    WHERE reporting_country IN ('INDIA', 'KENYA')
    GROUP BY reporting_country, direction
) g ON s.reporting_country = g.reporting_country AND s.direction = g.direction
ORDER BY reporting_country, direction;

-- =====================================================================
-- 2. DATA INTEGRITY CHECKS
-- =====================================================================

\echo ''
\echo '4. NULL Transaction ID Check (should be 0)'
\echo '--------------------------------------------------------------'

SELECT COUNT(*) AS null_transaction_ids
FROM global_trades_ledger 
WHERE transaction_id IS NULL;

\echo ''
\echo '5. Duplicate std_id Check (should be 0)'
\echo '--------------------------------------------------------------'

SELECT std_id, COUNT(*) AS duplicate_count
FROM global_trades_ledger
WHERE std_id IS NOT NULL
GROUP BY std_id
HAVING COUNT(*) > 1
LIMIT 10;

\echo ''
\echo '6. Price Sanity Check - Negative Values (should be 0)'
\echo '--------------------------------------------------------------'

SELECT COUNT(*) AS negative_price_count
FROM global_trades_ledger
WHERE price_usd_per_kg IS NOT NULL AND price_usd_per_kg < 0;

\echo ''
\echo '7. NULL Required Fields Check'
\echo '--------------------------------------------------------------'

SELECT 
    'shipment_date' AS field, COUNT(*) AS null_count 
    FROM global_trades_ledger WHERE shipment_date IS NULL
UNION ALL
SELECT 'origin_country', COUNT(*) FROM global_trades_ledger WHERE origin_country IS NULL
UNION ALL
SELECT 'destination_country', COUNT(*) FROM global_trades_ledger WHERE destination_country IS NULL
UNION ALL
SELECT 'hs_code_6', COUNT(*) FROM global_trades_ledger WHERE hs_code_6 IS NULL
UNION ALL
SELECT 'year', COUNT(*) FROM global_trades_ledger WHERE year IS NULL
UNION ALL
SELECT 'month', COUNT(*) FROM global_trades_ledger WHERE month IS NULL
UNION ALL
SELECT 'direction', COUNT(*) FROM global_trades_ledger WHERE direction IS NULL
UNION ALL
SELECT 'reporting_country', COUNT(*) FROM global_trades_ledger WHERE reporting_country IS NULL;

\echo ''
\echo '8. Value Range Sanity Check'
\echo '--------------------------------------------------------------'

SELECT 
    reporting_country,
    direction,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN customs_value_usd IS NOT NULL THEN 1 ELSE 0 END) AS has_customs_value,
    SUM(CASE WHEN qty_kg IS NOT NULL THEN 1 ELSE 0 END) AS has_qty_kg,
    SUM(CASE WHEN price_usd_per_kg IS NOT NULL THEN 1 ELSE 0 END) AS has_price_per_kg,
    ROUND(MIN(customs_value_usd)::numeric, 2) AS min_value_usd,
    ROUND(MAX(customs_value_usd)::numeric, 2) AS max_value_usd,
    ROUND(AVG(customs_value_usd)::numeric, 2) AS avg_value_usd
FROM global_trades_ledger
WHERE reporting_country IN ('INDIA', 'KENYA')
GROUP BY reporting_country, direction
ORDER BY reporting_country, direction;

-- =====================================================================
-- 3. SAMPLE DATA WITH ORGANIZATION JOINS
-- =====================================================================

\echo ''
\echo '9. Sample Ledger Records with Buyer/Supplier Names'
\echo '--------------------------------------------------------------'

SELECT 
    g.reporting_country,
    g.direction,
    g.hs_code_6,
    g.qty_kg,
    ROUND(g.customs_value_usd::numeric, 2) AS customs_value_usd,
    ROUND(g.price_usd_per_kg::numeric, 2) AS price_usd_per_kg,
    b.name_normalized AS buyer_name,
    s.name_normalized AS supplier_name
FROM global_trades_ledger g
LEFT JOIN organizations_master b ON g.buyer_uuid = b.org_uuid
LEFT JOIN organizations_master s ON g.supplier_uuid = s.org_uuid
WHERE g.reporting_country IN ('INDIA', 'KENYA')
LIMIT 20;

\echo ''
\echo '10. Sample India Export Records'
\echo '--------------------------------------------------------------'

SELECT 
    g.transaction_id,
    g.shipment_date,
    g.origin_country,
    g.destination_country,
    g.hs_code_6,
    ROUND(g.qty_kg::numeric, 2) AS qty_kg,
    ROUND(g.customs_value_usd::numeric, 2) AS value_usd,
    b.name_normalized AS buyer,
    s.name_normalized AS supplier
FROM global_trades_ledger g
LEFT JOIN organizations_master b ON g.buyer_uuid = b.org_uuid
LEFT JOIN organizations_master s ON g.supplier_uuid = s.org_uuid
WHERE g.reporting_country = 'INDIA' AND g.direction = 'EXPORT'
LIMIT 10;

\echo ''
\echo '11. Sample Kenya Import Records'
\echo '--------------------------------------------------------------'

SELECT 
    g.transaction_id,
    g.shipment_date,
    g.origin_country,
    g.destination_country,
    g.hs_code_6,
    ROUND(g.qty_kg::numeric, 2) AS qty_kg,
    ROUND(g.customs_value_usd::numeric, 2) AS value_usd,
    b.name_normalized AS buyer,
    s.name_normalized AS supplier
FROM global_trades_ledger g
LEFT JOIN organizations_master b ON g.buyer_uuid = b.org_uuid
LEFT JOIN organizations_master s ON g.supplier_uuid = s.org_uuid
WHERE g.reporting_country = 'KENYA' AND g.direction = 'IMPORT'
LIMIT 10;

\echo ''
\echo '12. Sample Kenya Export Records'
\echo '--------------------------------------------------------------'

SELECT 
    g.transaction_id,
    g.shipment_date,
    g.origin_country,
    g.destination_country,
    g.hs_code_6,
    ROUND(g.qty_kg::numeric, 2) AS qty_kg,
    ROUND(g.customs_value_usd::numeric, 2) AS value_usd,
    b.name_normalized AS buyer,
    s.name_normalized AS supplier
FROM global_trades_ledger g
LEFT JOIN organizations_master b ON g.buyer_uuid = b.org_uuid
LEFT JOIN organizations_master s ON g.supplier_uuid = s.org_uuid
WHERE g.reporting_country = 'KENYA' AND g.direction = 'EXPORT'
LIMIT 10;

-- =====================================================================
-- 4. ANALYTICS READINESS CHECKS
-- =====================================================================

\echo ''
\echo '13. Top HS Codes by Value (Analytics Ready)'
\echo '--------------------------------------------------------------'

SELECT 
    reporting_country,
    direction,
    hs_code_6,
    COUNT(*) AS shipments,
    ROUND(SUM(customs_value_usd)::numeric, 2) AS total_value_usd
FROM global_trades_ledger
WHERE reporting_country IN ('INDIA', 'KENYA')
  AND customs_value_usd IS NOT NULL
GROUP BY reporting_country, direction, hs_code_6
ORDER BY total_value_usd DESC
LIMIT 20;

\echo ''
\echo '14. Trade Volume by Month'
\echo '--------------------------------------------------------------'

SELECT 
    reporting_country,
    direction,
    year,
    month,
    COUNT(*) AS shipments,
    ROUND(SUM(customs_value_usd)::numeric, 2) AS total_value_usd
FROM global_trades_ledger
WHERE reporting_country IN ('INDIA', 'KENYA')
GROUP BY reporting_country, direction, year, month
ORDER BY reporting_country, direction, year, month;

\echo ''
\echo '15. Top Destination Countries (from Exports)'
\echo '--------------------------------------------------------------'

SELECT 
    reporting_country,
    destination_country,
    COUNT(*) AS shipments,
    ROUND(SUM(customs_value_usd)::numeric, 2) AS total_value_usd
FROM global_trades_ledger
WHERE direction = 'EXPORT'
  AND reporting_country IN ('INDIA', 'KENYA')
GROUP BY reporting_country, destination_country
ORDER BY total_value_usd DESC
LIMIT 15;

\echo ''
\echo '16. Top Origin Countries (for Imports)'
\echo '--------------------------------------------------------------'

SELECT 
    reporting_country,
    origin_country,
    COUNT(*) AS shipments,
    ROUND(SUM(customs_value_usd)::numeric, 2) AS total_value_usd
FROM global_trades_ledger
WHERE direction = 'IMPORT'
  AND reporting_country IN ('INDIA', 'KENYA')
GROUP BY reporting_country, origin_country
ORDER BY total_value_usd DESC
LIMIT 15;

-- =====================================================================
-- 5. IDEMPOTENCY VERIFICATION
-- =====================================================================

\echo ''
\echo '17. std_id Coverage Check (should match staging counts)'
\echo '--------------------------------------------------------------'

SELECT 
    'Staging rows' AS source,
    COUNT(*) AS count
FROM stg_shipments_standardized
WHERE reporting_country IN ('INDIA', 'KENYA')
UNION ALL
SELECT 
    'Ledger rows with std_id',
    COUNT(*)
FROM global_trades_ledger
WHERE std_id IS NOT NULL
  AND reporting_country IN ('INDIA', 'KENYA')
UNION ALL
SELECT 
    'Ledger rows without std_id',
    COUNT(*)
FROM global_trades_ledger
WHERE std_id IS NULL
  AND reporting_country IN ('INDIA', 'KENYA');

\echo ''
\echo '18. Unloaded Staging Rows (candidates for next run)'
\echo '--------------------------------------------------------------'

SELECT 
    s.reporting_country,
    s.direction,
    COUNT(*) AS unloaded_rows
FROM stg_shipments_standardized s
LEFT JOIN global_trades_ledger g ON s.std_id = g.std_id
WHERE g.std_id IS NULL
  AND s.reporting_country IN ('INDIA', 'KENYA')
  AND s.shipment_date IS NOT NULL
  AND s.origin_country IS NOT NULL
  AND s.destination_country IS NOT NULL
  AND s.hs_code_6 IS NOT NULL
GROUP BY s.reporting_country, s.direction
ORDER BY s.reporting_country, s.direction;

-- =====================================================================
-- 6. SUCCESS CRITERIA SUMMARY
-- =====================================================================

\echo ''
\echo '19. EPIC 4 Success Criteria Summary'
\echo '--------------------------------------------------------------'

SELECT 
    'Total Ledger Rows' AS metric,
    COUNT(*)::text AS value
FROM global_trades_ledger
WHERE reporting_country IN ('INDIA', 'KENYA')
UNION ALL
SELECT 
    'India Export Rows',
    COUNT(*)::text
FROM global_trades_ledger
WHERE reporting_country = 'INDIA' AND direction = 'EXPORT'
UNION ALL
SELECT 
    'Kenya Import Rows',
    COUNT(*)::text
FROM global_trades_ledger
WHERE reporting_country = 'KENYA' AND direction = 'IMPORT'
UNION ALL
SELECT 
    'Kenya Export Rows',
    COUNT(*)::text
FROM global_trades_ledger
WHERE reporting_country = 'KENYA' AND direction = 'EXPORT'
UNION ALL
SELECT 
    'Rows with NULL transaction_id',
    COUNT(*)::text
FROM global_trades_ledger
WHERE transaction_id IS NULL
UNION ALL
SELECT 
    'Rows with negative price',
    COUNT(*)::text
FROM global_trades_ledger
WHERE price_usd_per_kg < 0;

-- =====================================================================
-- END OF EPIC 4 VERIFICATION QUERIES
-- =====================================================================

\echo ''
\echo '=============================================================='
\echo 'EPIC 4 Verification Complete'
\echo '=============================================================='
