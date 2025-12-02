-- =====================================================================
-- EPIC 6C: Global Risk Engine - Verification Queries
-- GTI-OS Data Platform
-- =====================================================================
-- Run these queries to verify risk engine implementation
-- =====================================================================

-- =====================================================================
-- 1. TABLE SANITY CHECKS
-- =====================================================================

-- 1.1 Total risk scores count
SELECT 'risk_scores' as table_name, COUNT(*) as row_count FROM risk_scores;

-- 1.2 Risk scores by entity type
SELECT 
    entity_type,
    COUNT(*) as count,
    COUNT(DISTINCT entity_id) as unique_entities
FROM risk_scores
GROUP BY entity_type
ORDER BY entity_type;

-- 1.3 Risk scores by risk level
SELECT 
    risk_level,
    COUNT(*) as count,
    ROUND(AVG(risk_score)::numeric, 2) as avg_score,
    ROUND(AVG(confidence_score)::numeric, 2) as avg_confidence
FROM risk_scores
GROUP BY risk_level
ORDER BY 
    CASE risk_level 
        WHEN 'CRITICAL' THEN 1 
        WHEN 'HIGH' THEN 2 
        WHEN 'MEDIUM' THEN 3 
        WHEN 'LOW' THEN 4 
    END;

-- 1.4 Risk scores by main reason code
SELECT 
    main_reason_code,
    entity_type,
    COUNT(*) as count,
    ROUND(AVG(risk_score)::numeric, 2) as avg_score
FROM risk_scores
GROUP BY main_reason_code, entity_type
ORDER BY count DESC;

-- 1.5 Engine versions in use
SELECT 
    engine_version,
    COUNT(*) as count,
    MIN(computed_at) as first_computed,
    MAX(computed_at) as last_computed
FROM risk_scores
GROUP BY engine_version;

-- =====================================================================
-- 2. UNIQUENESS & IDEMPOTENCY CHECKS
-- =====================================================================

-- 2.1 Check for duplicates (should return 0 rows)
SELECT 
    entity_type, 
    entity_id, 
    scope_key, 
    engine_version, 
    COUNT(*) as duplicate_count
FROM risk_scores
GROUP BY entity_type, entity_id, scope_key, engine_version
HAVING COUNT(*) > 1;

-- 2.2 Verify unique index exists
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'risk_scores'
  AND indexname LIKE '%entity_scope_version%';

-- =====================================================================
-- 3. LINKAGE CHECKS
-- =====================================================================

-- 3.1 Shipment risks must link to real transactions
SELECT 
    'SHIPMENT risks' as check_type,
    COUNT(*) as total_risks,
    SUM(CASE WHEN g.transaction_id IS NOT NULL THEN 1 ELSE 0 END) as linked,
    SUM(CASE WHEN g.transaction_id IS NULL THEN 1 ELSE 0 END) as orphaned
FROM risk_scores rs
LEFT JOIN global_trades_ledger g 
    ON rs.entity_id = g.transaction_id
WHERE rs.entity_type = 'SHIPMENT';

-- 3.2 Buyer risks must link to real organizations
SELECT 
    'BUYER risks' as check_type,
    COUNT(*) as total_risks,
    SUM(CASE WHEN om.org_uuid IS NOT NULL THEN 1 ELSE 0 END) as linked,
    SUM(CASE WHEN om.org_uuid IS NULL THEN 1 ELSE 0 END) as orphaned
FROM risk_scores rs
LEFT JOIN organizations_master om 
    ON rs.entity_id = om.org_uuid
WHERE rs.entity_type = 'BUYER';

-- 3.3 Buyer risks linkage to buyer_profile
SELECT 
    'BUYER profile linkage' as check_type,
    COUNT(*) as total_buyer_risks,
    SUM(CASE WHEN bp.buyer_uuid IS NOT NULL THEN 1 ELSE 0 END) as has_profile,
    SUM(CASE WHEN bp.buyer_uuid IS NULL THEN 1 ELSE 0 END) as no_profile
FROM risk_scores rs
LEFT JOIN buyer_profile bp 
    ON rs.entity_id = bp.buyer_uuid
WHERE rs.entity_type = 'BUYER';

-- =====================================================================
-- 4. LEDGER INTEGRITY CHECK (must remain unchanged)
-- =====================================================================

-- 4.1 Verify ledger row count unchanged
SELECT 
    'global_trades_ledger' as table_name,
    COUNT(*) as row_count,
    COUNT(DISTINCT transaction_id) as unique_transactions
FROM global_trades_ledger;

-- 4.2 Verify ledger equals staging (no aggregation)
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
-- 5. SAMPLE RISK RECORDS
-- =====================================================================

-- 5.1 Sample UNDER_INVOICE risks with reasons
SELECT 
    risk_id,
    entity_type,
    risk_score,
    risk_level,
    confidence_score,
    reasons->>'code' as reason_code,
    reasons->'context'->>'hs_code_6' as hs_code,
    reasons->'context'->>'shipment_price' as shipment_price,
    reasons->'context'->>'corridor_median' as corridor_median,
    reasons->'context'->>'z_score' as z_score,
    reasons->'context'->>'deviation_pct' as deviation_pct
FROM risk_scores
WHERE main_reason_code = 'UNDER_INVOICE'
ORDER BY risk_score DESC
LIMIT 5;

-- 5.2 Sample OVER_INVOICE risks
SELECT 
    risk_id,
    risk_score,
    risk_level,
    reasons->'context'->>'hs_code_6' as hs_code,
    reasons->'context'->>'shipment_price' as shipment_price,
    reasons->'context'->>'corridor_median' as corridor_median,
    reasons->'context'->>'z_score' as z_score
FROM risk_scores
WHERE main_reason_code = 'OVER_INVOICE'
ORDER BY risk_score DESC
LIMIT 5;

-- 5.3 Sample WEIRD_LANE risks
SELECT 
    risk_id,
    risk_score,
    risk_level,
    reasons->'context'->>'origin_country' as origin,
    reasons->'context'->>'destination_country' as destination,
    reasons->'context'->>'hs_code_6' as hs_code,
    reasons->'context'->>'lane_shipment_count' as lane_count,
    reasons->'context'->>'global_hs6_shipments' as global_count
FROM risk_scores
WHERE main_reason_code = 'WEIRD_LANE'
ORDER BY risk_score DESC
LIMIT 5;

-- 5.4 Sample GHOST_ENTITY risks
SELECT 
    risk_id,
    risk_score,
    risk_level,
    reasons->'context'->>'buyer_name' as buyer_name,
    reasons->'context'->>'total_value_usd' as total_value,
    reasons->'context'->>'total_shipments' as shipments,
    reasons->'context'->>'has_website' as has_website
FROM risk_scores
WHERE main_reason_code = 'GHOST_ENTITY'
ORDER BY risk_score DESC
LIMIT 5;

-- 5.5 Sample VOLUME_SPIKE risks
SELECT 
    risk_id,
    risk_score,
    risk_level,
    reasons->'context'->>'buyer_name' as buyer_name,
    reasons->'context'->>'persona_label' as persona,
    reasons->'context'->>'pct_change' as pct_change,
    reasons->'context'->>'z_score' as z_score,
    reasons->'context'->>'is_large_buyer' as is_large
FROM risk_scores
WHERE main_reason_code = 'VOLUME_SPIKE'
ORDER BY risk_score DESC
LIMIT 5;

-- =====================================================================
-- 6. RISK DISTRIBUTION ANALYSIS
-- =====================================================================

-- 6.1 Risk score distribution histogram
SELECT 
    CASE 
        WHEN risk_score >= 90 THEN '90-100'
        WHEN risk_score >= 80 THEN '80-89'
        WHEN risk_score >= 70 THEN '70-79'
        WHEN risk_score >= 60 THEN '60-69'
        WHEN risk_score >= 50 THEN '50-59'
        WHEN risk_score >= 40 THEN '40-49'
        WHEN risk_score >= 30 THEN '30-39'
        ELSE '0-29'
    END as score_band,
    entity_type,
    COUNT(*) as count
FROM risk_scores
GROUP BY 1, entity_type
ORDER BY 
    CASE 
        WHEN score_band = '90-100' THEN 1
        WHEN score_band = '80-89' THEN 2
        WHEN score_band = '70-79' THEN 3
        WHEN score_band = '60-69' THEN 4
        WHEN score_band = '50-59' THEN 5
        WHEN score_band = '40-49' THEN 6
        WHEN score_band = '30-39' THEN 7
        ELSE 8
    END,
    entity_type;

-- 6.2 Confidence score distribution
SELECT 
    CASE 
        WHEN confidence_score >= 0.9 THEN 'Very High (0.9+)'
        WHEN confidence_score >= 0.7 THEN 'High (0.7-0.89)'
        WHEN confidence_score >= 0.5 THEN 'Medium (0.5-0.69)'
        ELSE 'Low (<0.5)'
    END as confidence_band,
    COUNT(*) as count,
    ROUND(AVG(risk_score)::numeric, 2) as avg_risk_score
FROM risk_scores
GROUP BY 1
ORDER BY 
    CASE 
        WHEN confidence_band = 'Very High (0.9+)' THEN 1
        WHEN confidence_band = 'High (0.7-0.89)' THEN 2
        WHEN confidence_band = 'Medium (0.5-0.69)' THEN 3
        ELSE 4
    END;

-- =====================================================================
-- 7. HISTORY TABLE CHECK
-- =====================================================================

-- 7.1 History records count (populated on updates)
SELECT 
    'risk_scores_history' as table_name,
    COUNT(*) as row_count,
    COUNT(DISTINCT risk_id) as unique_original_risks
FROM risk_scores_history;

-- 7.2 Recent history entries
SELECT 
    history_id,
    risk_id,
    entity_type,
    main_reason_code,
    risk_score,
    computed_at,
    archived_at
FROM risk_scores_history
ORDER BY archived_at DESC
LIMIT 5;

-- =====================================================================
-- 8. WATERMARK STATUS
-- =====================================================================

-- 8.1 Current watermark
SELECT 
    id,
    last_processed_shipment_date,
    last_run_at,
    engine_version
FROM risk_engine_watermark;

-- =====================================================================
-- 9. PIPELINE RUNS TRACKING
-- =====================================================================

-- 9.1 Risk engine run history
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
WHERE pipeline_name = 'risk_engine'
ORDER BY started_at DESC
LIMIT 10;

-- =====================================================================
-- 10. EDGE CASE VERIFICATION
-- =====================================================================

-- 10.1 High-value shipments without risk flags (should be mostly normal)
WITH high_value_shipments AS (
    SELECT 
        g.transaction_id,
        g.customs_value_usd,
        g.hs_code_6,
        g.origin_country,
        g.destination_country
    FROM global_trades_ledger g
    WHERE g.customs_value_usd > 100000
)
SELECT 
    'High-value shipment risk coverage' as check_type,
    COUNT(*) as total_high_value,
    SUM(CASE WHEN rs.risk_id IS NOT NULL THEN 1 ELSE 0 END) as with_risk_flag,
    SUM(CASE WHEN rs.risk_id IS NULL THEN 1 ELSE 0 END) as without_risk_flag
FROM high_value_shipments hvs
LEFT JOIN risk_scores rs 
    ON hvs.transaction_id = rs.entity_id 
    AND rs.entity_type = 'SHIPMENT';

-- 10.2 Large buyers (Whale persona) should have lower spike risk scores
SELECT 
    'Large buyer spike scores' as check_type,
    bp.persona_label,
    COUNT(rs.risk_id) as spike_risks,
    ROUND(AVG(rs.risk_score)::numeric, 2) as avg_risk_score
FROM buyer_profile bp
LEFT JOIN risk_scores rs 
    ON bp.buyer_uuid = rs.entity_id 
    AND rs.entity_type = 'BUYER'
    AND rs.main_reason_code = 'VOLUME_SPIKE'
WHERE bp.persona_label IN ('Whale', 'Mid')
GROUP BY bp.persona_label;

-- 10.3 JSON reasons structure validation
SELECT 
    'JSON structure check' as check_type,
    COUNT(*) as total,
    SUM(CASE WHEN reasons ? 'code' THEN 1 ELSE 0 END) as has_code,
    SUM(CASE WHEN reasons ? 'severity' THEN 1 ELSE 0 END) as has_severity,
    SUM(CASE WHEN reasons ? 'context' THEN 1 ELSE 0 END) as has_context
FROM risk_scores;

-- =====================================================================
-- 11. COMBINED SUMMARY
-- =====================================================================

SELECT 
    'EPIC 6C SUMMARY' as report,
    (SELECT COUNT(*) FROM risk_scores) as total_risks,
    (SELECT COUNT(*) FROM risk_scores WHERE entity_type = 'SHIPMENT') as shipment_risks,
    (SELECT COUNT(*) FROM risk_scores WHERE entity_type = 'BUYER') as buyer_risks,
    (SELECT COUNT(*) FROM risk_scores WHERE risk_level = 'CRITICAL') as critical_count,
    (SELECT COUNT(*) FROM risk_scores WHERE risk_level = 'HIGH') as high_count,
    (SELECT COUNT(*) FROM risk_scores WHERE risk_level = 'MEDIUM') as medium_count,
    (SELECT COUNT(*) FROM risk_scores WHERE risk_level = 'LOW') as low_count,
    (SELECT COUNT(*) FROM risk_scores_history) as history_count,
    (SELECT COUNT(*) FROM global_trades_ledger) as ledger_row_count;

-- =====================================================================
-- END OF VERIFICATION QUERIES
-- =====================================================================
