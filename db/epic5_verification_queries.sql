-- =====================================================================
-- EPIC 5: Global Mirror Algorithm - Verification Queries
-- GTI-OS Data Platform
-- =====================================================================
-- Run these queries to verify mirror algorithm results
-- =====================================================================

-- =====================================================================
-- 1. HIDDEN BUYER ANALYSIS
-- =====================================================================

-- 1.1 Count of exports with hidden vs known buyers
SELECT 
    CASE 
        WHEN s.hidden_buyer_flag = TRUE THEN 'HIDDEN'
        ELSE 'KNOWN'
    END as buyer_type,
    COUNT(*) as export_count
FROM global_trades_ledger g
JOIN stg_shipments_standardized s ON g.std_id = s.std_id
WHERE g.direction = 'EXPORT'
GROUP BY s.hidden_buyer_flag
ORDER BY export_count DESC;

-- 1.2 Hidden buyer patterns breakdown
SELECT 
    CASE 
        WHEN UPPER(COALESCE(s.buyer_name_raw, '')) LIKE '%TO THE ORDER%' THEN 'TO_THE_ORDER'
        WHEN UPPER(COALESCE(s.buyer_name_raw, '')) LIKE '%TO ORDER%' THEN 'TO_ORDER'
        WHEN UPPER(COALESCE(s.buyer_name_raw, '')) LIKE '%BANK%' THEN 'BANK'
        WHEN UPPER(COALESCE(s.buyer_name_raw, '')) LIKE '%L/C%' THEN 'LC'
        WHEN UPPER(COALESCE(s.buyer_name_raw, '')) LIKE '%LETTER OF CREDIT%' THEN 'LETTER_OF_CREDIT'
        WHEN s.buyer_name_raw IS NULL OR TRIM(s.buyer_name_raw) = '' THEN 'EMPTY'
        ELSE 'KNOWN'
    END as buyer_pattern,
    COUNT(*) as export_count
FROM global_trades_ledger g
JOIN stg_shipments_standardized s ON g.std_id = s.std_id
WHERE g.direction = 'EXPORT'
GROUP BY buyer_pattern
ORDER BY export_count DESC;

-- 1.3 Hidden buyers by country
SELECT 
    g.reporting_country,
    SUM(CASE WHEN s.hidden_buyer_flag = TRUE THEN 1 ELSE 0 END) as hidden_count,
    SUM(CASE WHEN s.hidden_buyer_flag = FALSE OR s.hidden_buyer_flag IS NULL THEN 1 ELSE 0 END) as known_count,
    COUNT(*) as total_exports
FROM global_trades_ledger g
JOIN stg_shipments_standardized s ON g.std_id = s.std_id
WHERE g.direction = 'EXPORT'
GROUP BY g.reporting_country
ORDER BY hidden_count DESC;

-- =====================================================================
-- 2. MIRROR MATCH LOG ANALYSIS
-- =====================================================================

-- 2.1 Total mirror matches
SELECT COUNT(*) as total_mirror_matches
FROM mirror_match_log;

-- 2.2 Mirror matches by origin/destination country
SELECT 
    e.origin_country,
    e.destination_country,
    COUNT(*) as match_count
FROM mirror_match_log m
JOIN global_trades_ledger e 
    ON m.export_transaction_id = e.transaction_id 
    AND m.export_year = e.year
GROUP BY e.origin_country, e.destination_country
ORDER BY match_count DESC;

-- 2.3 Mirror matches by HS code
SELECT 
    e.hs_code_6,
    COUNT(*) as match_count
FROM mirror_match_log m
JOIN global_trades_ledger e 
    ON m.export_transaction_id = e.transaction_id 
    AND m.export_year = e.year
GROUP BY e.hs_code_6
ORDER BY match_count DESC
LIMIT 20;

-- 2.4 Match score distribution (histogram)
SELECT 
    CASE 
        WHEN match_score >= 90 THEN '90-100'
        WHEN match_score >= 80 THEN '80-89'
        WHEN match_score >= 70 THEN '70-79'
        WHEN match_score >= 60 THEN '60-69'
        ELSE '<60'
    END as score_bucket,
    COUNT(*) as match_count,
    ROUND(AVG(match_score), 1) as avg_score
FROM mirror_match_log
GROUP BY score_bucket
ORDER BY score_bucket;

-- =====================================================================
-- 3. IDEMPOTENCY & INTEGRITY CHECKS
-- =====================================================================

-- 3.1 Verify no export appears more than once (MUST BE EMPTY)
SELECT export_transaction_id, COUNT(*) as occurrence_count
FROM mirror_match_log
GROUP BY export_transaction_id
HAVING COUNT(*) > 1;

-- 3.2 Verify all matched exports have hidden_buyer_flag = TRUE
SELECT 
    COUNT(*) as matched_exports_without_hidden_flag
FROM mirror_match_log m
JOIN global_trades_ledger e 
    ON m.export_transaction_id = e.transaction_id 
    AND m.export_year = e.year
JOIN stg_shipments_standardized s ON e.std_id = s.std_id
WHERE s.hidden_buyer_flag = FALSE OR s.hidden_buyer_flag IS NULL;

-- 3.3 Verify matched exports now have buyer_uuid populated
SELECT 
    COUNT(*) as exports_with_buyer,
    SUM(CASE WHEN e.buyer_uuid IS NOT NULL THEN 1 ELSE 0 END) as have_buyer_uuid,
    SUM(CASE WHEN e.mirror_matched_at IS NOT NULL THEN 1 ELSE 0 END) as have_mirror_timestamp
FROM mirror_match_log m
JOIN global_trades_ledger e 
    ON m.export_transaction_id = e.transaction_id 
    AND m.export_year = e.year;

-- =====================================================================
-- 4. SAMPLE MATCH INSPECTION
-- =====================================================================

-- 4.1 Show 20 random mirror matches with full details
SELECT 
    e.reporting_country AS export_reporting_country,
    e.origin_country AS export_origin,
    e.destination_country AS export_dest,
    e.hs_code_6,
    e.shipment_date AS export_date,
    i.shipment_date AS import_date,
    (i.shipment_date - e.shipment_date) AS days_diff,
    e.qty_kg AS export_qty_kg,
    i.qty_kg AS import_qty_kg,
    ROUND(((i.qty_kg - e.qty_kg) / NULLIF(e.qty_kg, 0) * 100)::numeric, 2) AS qty_diff_pct,
    b.name_normalized AS inferred_buyer_name,
    s.name_normalized AS supplier_name,
    m.match_score,
    m.criteria_used
FROM mirror_match_log m
JOIN global_trades_ledger e 
    ON m.export_transaction_id = e.transaction_id 
    AND m.export_year = e.year
JOIN global_trades_ledger i 
    ON m.import_transaction_id = i.transaction_id 
    AND m.import_year = i.year
LEFT JOIN organizations_master b ON e.buyer_uuid = b.org_uuid
LEFT JOIN organizations_master s ON e.supplier_uuid = s.org_uuid
ORDER BY RANDOM()
LIMIT 20;

-- 4.2 Sample hidden buyer exports that were NOT matched (no candidates)
SELECT 
    g.transaction_id,
    g.reporting_country,
    g.origin_country,
    g.destination_country,
    g.hs_code_6,
    g.shipment_date,
    g.qty_kg,
    s.buyer_name_raw
FROM global_trades_ledger g
JOIN stg_shipments_standardized s ON g.std_id = s.std_id
WHERE g.direction = 'EXPORT'
  AND s.hidden_buyer_flag = TRUE
  AND g.mirror_matched_at IS NULL
  AND NOT EXISTS (
      SELECT 1 FROM mirror_match_log m 
      WHERE m.export_transaction_id = g.transaction_id
  )
ORDER BY g.shipment_date DESC
LIMIT 20;

-- =====================================================================
-- 5. DATA QUALITY CHECKS
-- =====================================================================

-- 5.1 Check that shipment counts haven't changed (no aggregation)
SELECT 
    'stg_shipments_raw' as table_name, 
    COUNT(*) as row_count
FROM stg_shipments_raw
UNION ALL
SELECT 
    'stg_shipments_standardized', 
    COUNT(*)
FROM stg_shipments_standardized
UNION ALL
SELECT 
    'global_trades_ledger', 
    COUNT(*)
FROM global_trades_ledger;

-- 5.2 Exports before and after mirror (buyer_uuid status)
SELECT 
    CASE 
        WHEN buyer_uuid IS NOT NULL AND mirror_matched_at IS NOT NULL THEN 'INFERRED_BY_MIRROR'
        WHEN buyer_uuid IS NOT NULL THEN 'ORIGINAL_BUYER'
        ELSE 'NO_BUYER'
    END as buyer_status,
    COUNT(*) as export_count
FROM global_trades_ledger
WHERE direction = 'EXPORT'
GROUP BY buyer_status
ORDER BY export_count DESC;

-- 5.3 Check mirror candidates availability (why no matches?)
-- This shows potential export-import pairs that could match if dates aligned
SELECT 
    e.origin_country,
    e.destination_country,
    e.hs_code_6,
    COUNT(DISTINCT e.transaction_id) as hidden_exports,
    COUNT(DISTINCT i.transaction_id) as potential_imports,
    MIN(e.shipment_date) as earliest_export,
    MAX(e.shipment_date) as latest_export,
    MIN(i.shipment_date) as earliest_import,
    MAX(i.shipment_date) as latest_import
FROM global_trades_ledger e
JOIN stg_shipments_standardized s ON e.std_id = s.std_id
LEFT JOIN global_trades_ledger i 
    ON e.destination_country = i.reporting_country
    AND e.origin_country = i.origin_country
    AND e.hs_code_6 = i.hs_code_6
    AND i.direction = 'IMPORT'
    AND i.buyer_uuid IS NOT NULL
WHERE e.direction = 'EXPORT'
  AND s.hidden_buyer_flag = TRUE
GROUP BY e.origin_country, e.destination_country, e.hs_code_6
ORDER BY hidden_exports DESC;

-- =====================================================================
-- 6. PIPELINE RUNS TRACKING
-- =====================================================================

-- 6.1 Mirror algorithm run history
SELECT 
    run_id,
    started_at,
    completed_at,
    status,
    rows_processed,
    rows_created,
    rows_updated,
    rows_skipped,
    error_message
FROM pipeline_runs
WHERE pipeline_name = 'mirror_algorithm'
ORDER BY started_at DESC
LIMIT 10;

-- =====================================================================
-- END OF VERIFICATION QUERIES
-- =====================================================================
