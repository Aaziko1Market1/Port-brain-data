-- =====================================================================
-- EPIC 3 - Identity Engine Verification Queries
-- GTI-OS Data Platform Architecture v1.0
-- =====================================================================
-- 
-- These queries verify the identity resolution pipeline:
-- 1. UUID coverage in standardized shipments
-- 2. Organization master data statistics
-- 3. Matching quality checks
-- 4. Data integrity validation
--
-- Usage:
--   psql -U postgres -d aaziko_trade -f db/epic3_verification_queries.sql
-- =====================================================================

\echo '=============================================================='
\echo 'EPIC 3 - Identity Engine Verification Queries'
\echo '=============================================================='

-- =====================================================================
-- 1. UUID COVERAGE IN STANDARDIZED SHIPMENTS
-- =====================================================================

\echo ''
\echo '1. UUID Coverage by Country and Direction'
\echo '--------------------------------------------------------------'

SELECT 
    reporting_country,
    direction,
    COUNT(*) AS total_rows,
    COUNT(buyer_uuid) AS rows_with_buyer_uuid,
    COUNT(supplier_uuid) AS rows_with_supplier_uuid,
    ROUND(100.0 * COUNT(buyer_uuid) / NULLIF(COUNT(*), 0), 2) AS buyer_uuid_pct,
    ROUND(100.0 * COUNT(supplier_uuid) / NULLIF(COUNT(*), 0), 2) AS supplier_uuid_pct
FROM stg_shipments_standardized
WHERE reporting_country IN ('INDIA', 'KENYA')
GROUP BY reporting_country, direction
ORDER BY reporting_country, direction;

\echo ''
\echo '2. UUID Coverage - Missing Analysis'
\echo '--------------------------------------------------------------'

SELECT 
    reporting_country,
    direction,
    SUM(CASE WHEN buyer_name_raw IS NOT NULL AND buyer_uuid IS NULL THEN 1 ELSE 0 END) AS buyers_missing_uuid,
    SUM(CASE WHEN supplier_name_raw IS NOT NULL AND supplier_uuid IS NULL THEN 1 ELSE 0 END) AS suppliers_missing_uuid,
    SUM(CASE WHEN buyer_name_raw IS NULL THEN 1 ELSE 0 END) AS null_buyer_names,
    SUM(CASE WHEN supplier_name_raw IS NULL THEN 1 ELSE 0 END) AS null_supplier_names
FROM stg_shipments_standardized
WHERE reporting_country IN ('INDIA', 'KENYA')
GROUP BY reporting_country, direction
ORDER BY reporting_country, direction;

-- =====================================================================
-- 2. ORGANIZATIONS MASTER STATISTICS
-- =====================================================================

\echo ''
\echo '3. Organizations Count by Country and Type'
\echo '--------------------------------------------------------------'

SELECT 
    country_iso,
    type,
    COUNT(*) AS org_count
FROM organizations_master
GROUP BY country_iso, type
ORDER BY country_iso, type;

\echo ''
\echo '4. Total Organizations Summary'
\echo '--------------------------------------------------------------'

SELECT 
    COUNT(*) AS total_organizations,
    COUNT(DISTINCT country_iso) AS unique_countries,
    SUM(CASE WHEN type = 'BUYER' THEN 1 ELSE 0 END) AS buyer_only_orgs,
    SUM(CASE WHEN type = 'SUPPLIER' THEN 1 ELSE 0 END) AS supplier_only_orgs,
    SUM(CASE WHEN type = 'MIXED' THEN 1 ELSE 0 END) AS mixed_orgs
FROM organizations_master;

\echo ''
\echo '5. Recently Created Organizations (Last 20)'
\echo '--------------------------------------------------------------'

SELECT 
    org_uuid,
    name_normalized,
    country_iso,
    type,
    raw_name_variants,
    created_at
FROM organizations_master
ORDER BY created_at DESC
LIMIT 20;

-- =====================================================================
-- 3. ORGANIZATION NAME VARIANTS
-- =====================================================================

\echo ''
\echo '6. Organizations with Multiple Name Variants'
\echo '--------------------------------------------------------------'

SELECT 
    org_uuid,
    name_normalized,
    country_iso,
    type,
    raw_name_variants
FROM organizations_master
WHERE jsonb_typeof(raw_name_variants) = 'object'
  AND (
    jsonb_array_length(COALESCE(raw_name_variants->'buyer', '[]'::jsonb)) > 1
    OR jsonb_array_length(COALESCE(raw_name_variants->'supplier', '[]'::jsonb)) > 1
  )
ORDER BY created_at DESC
LIMIT 20;

\echo ''
\echo '7. MIXED Type Organizations (Both Buyer and Supplier)'
\echo '--------------------------------------------------------------'

SELECT 
    org_uuid,
    name_normalized,
    country_iso,
    raw_name_variants,
    created_at,
    updated_at
FROM organizations_master
WHERE type = 'MIXED'
ORDER BY updated_at DESC
LIMIT 20;

-- =====================================================================
-- 4. SHIPMENT-ORGANIZATION JOIN VERIFICATION
-- =====================================================================

\echo ''
\echo '8. Sample Shipments with Buyer Organization Data'
\echo '--------------------------------------------------------------'

SELECT 
    s.std_id,
    s.buyer_name_raw,
    o.name_normalized AS buyer_normalized,
    o.country_iso AS buyer_country,
    o.type AS buyer_type,
    s.reporting_country,
    s.direction
FROM stg_shipments_standardized s
JOIN organizations_master o ON s.buyer_uuid = o.org_uuid
WHERE s.reporting_country IN ('INDIA', 'KENYA')
LIMIT 20;

\echo ''
\echo '9. Sample Shipments with Supplier Organization Data'
\echo '--------------------------------------------------------------'

SELECT 
    s.std_id,
    s.supplier_name_raw,
    o.name_normalized AS supplier_normalized,
    o.country_iso AS supplier_country,
    o.type AS supplier_type,
    s.reporting_country,
    s.direction
FROM stg_shipments_standardized s
JOIN organizations_master o ON s.supplier_uuid = o.org_uuid
WHERE s.reporting_country IN ('INDIA', 'KENYA')
LIMIT 20;

-- =====================================================================
-- 5. TOP ORGANIZATIONS BY SHIPMENT COUNT
-- =====================================================================

\echo ''
\echo '10. Top 15 Buyers by Shipment Count'
\echo '--------------------------------------------------------------'

SELECT 
    o.org_uuid,
    o.name_normalized,
    o.country_iso,
    o.type,
    COUNT(*) AS shipment_count
FROM stg_shipments_standardized s
JOIN organizations_master o ON s.buyer_uuid = o.org_uuid
WHERE s.reporting_country IN ('INDIA', 'KENYA')
GROUP BY o.org_uuid, o.name_normalized, o.country_iso, o.type
ORDER BY shipment_count DESC
LIMIT 15;

\echo ''
\echo '11. Top 15 Suppliers by Shipment Count'
\echo '--------------------------------------------------------------'

SELECT 
    o.org_uuid,
    o.name_normalized,
    o.country_iso,
    o.type,
    COUNT(*) AS shipment_count
FROM stg_shipments_standardized s
JOIN organizations_master o ON s.supplier_uuid = o.org_uuid
WHERE s.reporting_country IN ('INDIA', 'KENYA')
GROUP BY o.org_uuid, o.name_normalized, o.country_iso, o.type
ORDER BY shipment_count DESC
LIMIT 15;

-- =====================================================================
-- 6. DATA QUALITY CHECKS
-- =====================================================================

\echo ''
\echo '12. Orphaned UUIDs (UUIDs not in organizations_master)'
\echo '--------------------------------------------------------------'

SELECT 'buyer_uuid' AS uuid_type, COUNT(*) AS orphan_count
FROM stg_shipments_standardized s
WHERE s.buyer_uuid IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM organizations_master o WHERE o.org_uuid = s.buyer_uuid)
  AND s.reporting_country IN ('INDIA', 'KENYA')
UNION ALL
SELECT 'supplier_uuid' AS uuid_type, COUNT(*) AS orphan_count
FROM stg_shipments_standardized s
WHERE s.supplier_uuid IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM organizations_master o WHERE o.org_uuid = s.supplier_uuid)
  AND s.reporting_country IN ('INDIA', 'KENYA');

\echo ''
\echo '13. Duplicate Normalized Names Check'
\echo '--------------------------------------------------------------'

SELECT 
    name_normalized,
    country_iso,
    COUNT(*) AS duplicate_count
FROM organizations_master
GROUP BY name_normalized, country_iso
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC
LIMIT 20;

\echo ''
\echo '14. Organizations Without Any Shipment Links'
\echo '--------------------------------------------------------------'

SELECT COUNT(*) AS unlinked_orgs
FROM organizations_master o
WHERE NOT EXISTS (
    SELECT 1 FROM stg_shipments_standardized s 
    WHERE s.buyer_uuid = o.org_uuid OR s.supplier_uuid = o.org_uuid
);

-- =====================================================================
-- 7. COVERAGE METRICS FOR SUCCESS CRITERIA
-- =====================================================================

\echo ''
\echo '15. EPIC 3 Success Criteria - Coverage Metrics'
\echo '--------------------------------------------------------------'

WITH coverage AS (
    SELECT 
        reporting_country,
        direction,
        COUNT(*) AS total,
        COUNT(buyer_uuid) AS with_buyer_uuid,
        COUNT(supplier_uuid) AS with_supplier_uuid,
        COUNT(CASE WHEN buyer_name_raw IS NOT NULL THEN 1 END) AS has_buyer_name,
        COUNT(CASE WHEN supplier_name_raw IS NOT NULL THEN 1 END) AS has_supplier_name
    FROM stg_shipments_standardized
    WHERE reporting_country IN ('INDIA', 'KENYA')
    GROUP BY reporting_country, direction
)
SELECT 
    reporting_country,
    direction,
    total AS total_rows,
    -- Buyer coverage (of rows that have buyer_name_raw)
    CASE WHEN has_buyer_name > 0 
         THEN ROUND(100.0 * with_buyer_uuid / has_buyer_name, 2) 
         ELSE 0 END AS buyer_uuid_coverage_pct,
    -- Supplier coverage (of rows that have supplier_name_raw)
    CASE WHEN has_supplier_name > 0 
         THEN ROUND(100.0 * with_supplier_uuid / has_supplier_name, 2) 
         ELSE 0 END AS supplier_uuid_coverage_pct,
    -- Absolute numbers
    with_buyer_uuid AS rows_with_buyer_uuid,
    has_buyer_name AS rows_with_buyer_name,
    with_supplier_uuid AS rows_with_supplier_uuid,
    has_supplier_name AS rows_with_supplier_name
FROM coverage
ORDER BY reporting_country, direction;

\echo ''
\echo '16. Organization Master Summary by Country'
\echo '--------------------------------------------------------------'

SELECT 
    country_iso,
    COUNT(*) AS total_orgs,
    SUM(CASE WHEN type = 'BUYER' THEN 1 ELSE 0 END) AS buyers,
    SUM(CASE WHEN type = 'SUPPLIER' THEN 1 ELSE 0 END) AS suppliers,
    SUM(CASE WHEN type = 'MIXED' THEN 1 ELSE 0 END) AS mixed
FROM organizations_master
WHERE country_iso IN ('INDIA', 'KENYA', 'UAE', 'CHINA', 'USA', 'QATAR', 'OMAN', 'SAUDI ARABIA')
GROUP BY country_iso
ORDER BY total_orgs DESC;

-- =====================================================================
-- 8. DETAILED SAMPLE DATA
-- =====================================================================

\echo ''
\echo '17. Sample Kenya Import Shipments with Both UUIDs'
\echo '--------------------------------------------------------------'

SELECT 
    s.std_id,
    s.buyer_name_raw,
    b.name_normalized AS buyer_norm,
    s.supplier_name_raw,
    sup.name_normalized AS supplier_norm,
    s.origin_country,
    s.destination_country
FROM stg_shipments_standardized s
LEFT JOIN organizations_master b ON s.buyer_uuid = b.org_uuid
LEFT JOIN organizations_master sup ON s.supplier_uuid = sup.org_uuid
WHERE s.reporting_country = 'KENYA' 
  AND s.direction = 'IMPORT'
  AND s.buyer_uuid IS NOT NULL
  AND s.supplier_uuid IS NOT NULL
LIMIT 10;

\echo ''
\echo '18. Sample India Export Shipments with Both UUIDs'
\echo '--------------------------------------------------------------'

SELECT 
    s.std_id,
    s.buyer_name_raw,
    b.name_normalized AS buyer_norm,
    s.supplier_name_raw,
    sup.name_normalized AS supplier_norm,
    s.origin_country,
    s.destination_country
FROM stg_shipments_standardized s
LEFT JOIN organizations_master b ON s.buyer_uuid = b.org_uuid
LEFT JOIN organizations_master sup ON s.supplier_uuid = sup.org_uuid
WHERE s.reporting_country = 'INDIA' 
  AND s.direction = 'EXPORT'
  AND s.buyer_uuid IS NOT NULL
  AND s.supplier_uuid IS NOT NULL
LIMIT 10;

\echo ''
\echo '19. Sample Kenya Export Shipments with Both UUIDs'
\echo '--------------------------------------------------------------'

SELECT 
    s.std_id,
    s.buyer_name_raw,
    b.name_normalized AS buyer_norm,
    s.supplier_name_raw,
    sup.name_normalized AS supplier_norm,
    s.origin_country,
    s.destination_country
FROM stg_shipments_standardized s
LEFT JOIN organizations_master b ON s.buyer_uuid = b.org_uuid
LEFT JOIN organizations_master sup ON s.supplier_uuid = sup.org_uuid
WHERE s.reporting_country = 'KENYA' 
  AND s.direction = 'EXPORT'
  AND s.buyer_uuid IS NOT NULL
  AND s.supplier_uuid IS NOT NULL
LIMIT 10;

-- =====================================================================
-- END OF EPIC 3 VERIFICATION QUERIES
-- =====================================================================

\echo ''
\echo '=============================================================='
\echo 'EPIC 3 Verification Complete'
\echo '=============================================================='
