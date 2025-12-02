-- =====================================================================
-- EPIC 6A: Buyer & Exporter Profiles - Verification Queries
-- GTI-OS Data Platform
-- =====================================================================
-- Run these queries to verify profile build results
-- =====================================================================

-- =====================================================================
-- 1. ROW COUNTS
-- =====================================================================

-- 1.1 Total profile counts
SELECT 'buyer_profile' as table_name, COUNT(*) as row_count FROM buyer_profile
UNION ALL
SELECT 'exporter_profile', COUNT(*) FROM exporter_profile;

-- 1.2 Profiles by reporting country
SELECT 
    'BUYER' as profile_type,
    reporting_country,
    COUNT(*) as profile_count,
    SUM(total_shipments) as total_shipments,
    ROUND(SUM(total_customs_value_usd)::numeric, 2) as total_value_usd
FROM buyer_profile
GROUP BY reporting_country
UNION ALL
SELECT 
    'EXPORTER',
    reporting_country,
    COUNT(*),
    SUM(total_shipments),
    ROUND(SUM(total_customs_value_usd)::numeric, 2)
FROM exporter_profile
GROUP BY reporting_country
ORDER BY profile_type, reporting_country;

-- =====================================================================
-- 2. SAMPLE PROFILES BY COUNTRY
-- =====================================================================

-- 2.1 Sample buyer profiles (top 3 per country by value)
WITH ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY reporting_country ORDER BY total_customs_value_usd DESC) as rn
    FROM buyer_profile
)
SELECT 
    reporting_country,
    destination_country,
    buyer_uuid,
    total_shipments,
    ROUND(total_customs_value_usd::numeric, 2) as total_value_usd,
    unique_hs6_count,
    persona_label,
    first_shipment_date,
    last_shipment_date
FROM ranked
WHERE rn <= 3
ORDER BY reporting_country, total_customs_value_usd DESC;

-- 2.2 Sample exporter profiles (top 3 per country by value)
WITH ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY reporting_country ORDER BY total_customs_value_usd DESC) as rn
    FROM exporter_profile
)
SELECT 
    reporting_country,
    origin_country,
    supplier_uuid,
    total_shipments,
    ROUND(total_customs_value_usd::numeric, 2) as total_value_usd,
    unique_hs6_count,
    stability_score,
    onboarding_score,
    first_shipment_date,
    last_shipment_date
FROM ranked
WHERE rn <= 3
ORDER BY reporting_country, total_customs_value_usd DESC;

-- =====================================================================
-- 3. CONSISTENCY CHECKS
-- =====================================================================

-- 3.1 Buyer profile value consistency check
-- Compare profile totals with ledger aggregates
WITH ledger_agg AS (
    SELECT 
        buyer_uuid,
        destination_country,
        COUNT(*) as ledger_shipments,
        SUM(customs_value_usd) as ledger_value
    FROM global_trades_ledger
    WHERE buyer_uuid IS NOT NULL
      AND direction = 'IMPORT'
    GROUP BY buyer_uuid, destination_country
)
SELECT 
    bp.buyer_uuid,
    bp.destination_country,
    bp.total_shipments as profile_shipments,
    la.ledger_shipments,
    bp.total_shipments - la.ledger_shipments as shipment_diff,
    ROUND(bp.total_customs_value_usd::numeric, 2) as profile_value,
    ROUND(la.ledger_value::numeric, 2) as ledger_value,
    ROUND((bp.total_customs_value_usd - COALESCE(la.ledger_value, 0))::numeric, 2) as value_diff
FROM buyer_profile bp
LEFT JOIN ledger_agg la 
    ON bp.buyer_uuid = la.buyer_uuid 
    AND bp.destination_country = la.destination_country
WHERE ABS(bp.total_shipments - COALESCE(la.ledger_shipments, 0)) > 0
   OR ABS(bp.total_customs_value_usd - COALESCE(la.ledger_value, 0)) > 0.01
LIMIT 10;

-- 3.2 Exporter profile value consistency check
WITH ledger_agg AS (
    SELECT 
        supplier_uuid,
        origin_country,
        COUNT(*) as ledger_shipments,
        SUM(customs_value_usd) as ledger_value
    FROM global_trades_ledger
    WHERE supplier_uuid IS NOT NULL
      AND direction = 'EXPORT'
    GROUP BY supplier_uuid, origin_country
)
SELECT 
    ep.supplier_uuid,
    ep.origin_country,
    ep.total_shipments as profile_shipments,
    la.ledger_shipments,
    ep.total_shipments - la.ledger_shipments as shipment_diff,
    ROUND(ep.total_customs_value_usd::numeric, 2) as profile_value,
    ROUND(la.ledger_value::numeric, 2) as ledger_value,
    ROUND((ep.total_customs_value_usd - COALESCE(la.ledger_value, 0))::numeric, 2) as value_diff
FROM exporter_profile ep
LEFT JOIN ledger_agg la 
    ON ep.supplier_uuid = la.supplier_uuid 
    AND ep.origin_country = la.origin_country
WHERE ABS(ep.total_shipments - COALESCE(la.ledger_shipments, 0)) > 0
   OR ABS(ep.total_customs_value_usd - COALESCE(la.ledger_value, 0)) > 0.01
LIMIT 10;

-- =====================================================================
-- 4. INTEGRITY CHECKS
-- =====================================================================

-- 4.1 Check for NULL buyer_uuid in buyer_profile (should be 0)
SELECT 'buyer_profile NULL buyer_uuid' as check_name, 
       COUNT(*) as invalid_count
FROM buyer_profile 
WHERE buyer_uuid IS NULL;

-- 4.2 Check for NULL supplier_uuid in exporter_profile (should be 0)
SELECT 'exporter_profile NULL supplier_uuid' as check_name,
       COUNT(*) as invalid_count
FROM exporter_profile 
WHERE supplier_uuid IS NULL;

-- 4.3 Check for orphaned buyer profiles (buyer_uuid not in organizations_master)
SELECT 'buyer_profile orphaned' as check_name,
       COUNT(*) as invalid_count
FROM buyer_profile bp
WHERE NOT EXISTS (
    SELECT 1 FROM organizations_master om WHERE om.org_uuid = bp.buyer_uuid
);

-- 4.4 Check for orphaned exporter profiles (supplier_uuid not in organizations_master)
SELECT 'exporter_profile orphaned' as check_name,
       COUNT(*) as invalid_count
FROM exporter_profile ep
WHERE NOT EXISTS (
    SELECT 1 FROM organizations_master om WHERE om.org_uuid = ep.supplier_uuid
);

-- 4.5 Combined integrity summary
SELECT 
    'INTEGRITY CHECK' as category,
    SUM(CASE WHEN check_name = 'buyer_profile NULL' THEN cnt ELSE 0 END) as buyer_null,
    SUM(CASE WHEN check_name = 'exporter_profile NULL' THEN cnt ELSE 0 END) as exporter_null,
    SUM(CASE WHEN check_name = 'buyer_orphan' THEN cnt ELSE 0 END) as buyer_orphan,
    SUM(CASE WHEN check_name = 'exporter_orphan' THEN cnt ELSE 0 END) as exporter_orphan
FROM (
    SELECT 'buyer_profile NULL' as check_name, COUNT(*) as cnt FROM buyer_profile WHERE buyer_uuid IS NULL
    UNION ALL
    SELECT 'exporter_profile NULL', COUNT(*) FROM exporter_profile WHERE supplier_uuid IS NULL
    UNION ALL
    SELECT 'buyer_orphan', COUNT(*) FROM buyer_profile bp WHERE NOT EXISTS (SELECT 1 FROM organizations_master om WHERE om.org_uuid = bp.buyer_uuid)
    UNION ALL
    SELECT 'exporter_orphan', COUNT(*) FROM exporter_profile ep WHERE NOT EXISTS (SELECT 1 FROM organizations_master om WHERE om.org_uuid = ep.supplier_uuid)
) checks;

-- =====================================================================
-- 5. JSON SAMPLES
-- =====================================================================

-- 5.1 Sample top_hs_codes from buyer profiles
SELECT 
    buyer_uuid,
    destination_country,
    reporting_country,
    top_hs_codes
FROM buyer_profile
WHERE jsonb_array_length(top_hs_codes) > 0
LIMIT 5;

-- 5.2 Sample top_suppliers from buyer profiles
SELECT 
    buyer_uuid,
    destination_country,
    reporting_country,
    top_suppliers
FROM buyer_profile
WHERE jsonb_array_length(top_suppliers) > 0
LIMIT 5;

-- 5.3 Sample top_hs_codes from exporter profiles
SELECT 
    supplier_uuid,
    origin_country,
    reporting_country,
    top_hs_codes
FROM exporter_profile
WHERE jsonb_array_length(top_hs_codes) > 0
LIMIT 5;

-- 5.4 Sample top_buyers from exporter profiles
SELECT 
    supplier_uuid,
    origin_country,
    reporting_country,
    top_buyers
FROM exporter_profile
WHERE jsonb_array_length(top_buyers) > 0
LIMIT 5;

-- =====================================================================
-- 6. PERSONA/SCORE DISTRIBUTION
-- =====================================================================

-- 6.1 Buyer persona distribution
SELECT 
    persona_label,
    COUNT(*) as buyer_count,
    ROUND(AVG(total_customs_value_usd)::numeric, 2) as avg_value_usd,
    ROUND(AVG(total_shipments)::numeric, 0) as avg_shipments
FROM buyer_profile
GROUP BY persona_label
ORDER BY buyer_count DESC;

-- 6.2 Exporter stability score distribution
SELECT 
    CASE 
        WHEN stability_score >= 80 THEN '80-100 (High)'
        WHEN stability_score >= 60 THEN '60-79 (Medium)'
        WHEN stability_score >= 40 THEN '40-59 (Low)'
        ELSE '0-39 (Very Low)'
    END as stability_band,
    COUNT(*) as exporter_count,
    ROUND(AVG(total_customs_value_usd)::numeric, 2) as avg_value_usd
FROM exporter_profile
GROUP BY stability_band
ORDER BY stability_band;

-- 6.3 Exporter onboarding score distribution
SELECT 
    CASE 
        WHEN onboarding_score >= 80 THEN '80-100 (Excellent)'
        WHEN onboarding_score >= 60 THEN '60-79 (Good)'
        WHEN onboarding_score >= 40 THEN '40-59 (Fair)'
        ELSE '0-39 (Poor)'
    END as onboarding_band,
    COUNT(*) as exporter_count,
    ROUND(AVG(total_shipments)::numeric, 0) as avg_shipments
FROM exporter_profile
GROUP BY onboarding_band
ORDER BY onboarding_band;

-- =====================================================================
-- 7. GLOBAL_TRADES_LEDGER INTEGRITY (must remain unchanged)
-- =====================================================================

-- 7.1 Verify ledger row count unchanged
SELECT 
    'global_trades_ledger' as table_name,
    COUNT(*) as row_count,
    COUNT(DISTINCT transaction_id) as unique_transactions
FROM global_trades_ledger;

-- 7.2 Verify no shipment aggregation occurred (ledger vs staging)
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
-- 8. PIPELINE RUNS TRACKING
-- =====================================================================

-- 8.1 Profile build run history
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
WHERE pipeline_name = 'build_profiles'
ORDER BY started_at DESC
LIMIT 10;

-- =====================================================================
-- 9. INCREMENTAL MARKERS
-- =====================================================================

-- 9.1 Profile build markers status
SELECT 
    profile_type,
    last_processed_date,
    last_processed_at
FROM profile_build_markers
ORDER BY profile_type;

-- =====================================================================
-- END OF VERIFICATION QUERIES
-- =====================================================================
