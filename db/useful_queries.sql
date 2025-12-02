-- =====================================================================
-- GTI-OS Data Platform - Useful SQL Queries
-- Quick reference for monitoring and testing
-- =====================================================================

-- =====================================================================
-- FILE REGISTRY QUERIES
-- =====================================================================

-- Check ingestion status summary
SELECT 
    status,
    COUNT(*) as file_count,
    SUM(total_rows) as total_rows,
    SUM(file_size_bytes) / 1024 / 1024 as total_size_mb
FROM file_registry
GROUP BY status
ORDER BY status;

-- Recent ingestions
SELECT 
    file_name,
    reporting_country,
    direction,
    year,
    month,
    total_rows,
    status,
    ingested_at
FROM file_registry
ORDER BY ingested_at DESC NULLS LAST
LIMIT 20;

-- Failed ingestions with errors
SELECT 
    file_name,
    reporting_country,
    direction,
    error_message,
    updated_at
FROM file_registry
WHERE status = 'FAILED'
ORDER BY updated_at DESC;

-- Files by country and direction
SELECT 
    reporting_country,
    direction,
    COUNT(*) as file_count,
    SUM(total_rows) as total_rows
FROM file_registry
WHERE status = 'INGESTED'
GROUP BY reporting_country, direction
ORDER BY reporting_country, direction;

-- Monthly ingestion volumes
SELECT 
    year,
    month,
    COUNT(*) as file_count,
    SUM(total_rows) as total_rows
FROM file_registry
WHERE status = 'INGESTED'
GROUP BY year, month
ORDER BY year, month;

-- =====================================================================
-- STAGING RAW DATA QUERIES
-- =====================================================================

-- Total raw rows by country/direction
SELECT 
    reporting_country,
    direction,
    COUNT(*) as row_count,
    MIN(ingested_at) as first_ingested,
    MAX(ingested_at) as last_ingested
FROM stg_shipments_raw
GROUP BY reporting_country, direction
ORDER BY row_count DESC;

-- Sample raw data
SELECT 
    raw_id,
    raw_file_name,
    reporting_country,
    direction,
    raw_row_number,
    hs_code_raw,
    buyer_name_raw,
    supplier_name_raw,
    raw_data
FROM stg_shipments_raw
LIMIT 10;

-- Search for specific HS code in raw data
SELECT 
    raw_file_name,
    reporting_country,
    direction,
    raw_data->>'hs_code' as hs_code,
    raw_data->>'goods_description' as goods,
    raw_data->>'buyer_name' as buyer,
    raw_data->>'quantity_kg' as quantity
FROM stg_shipments_raw
WHERE raw_data->>'hs_code' LIKE '0806%'  -- Change HS code as needed
LIMIT 20;

-- Count distinct buyers/suppliers in raw data
SELECT 
    COUNT(DISTINCT buyer_name_raw) as unique_buyers,
    COUNT(DISTINCT supplier_name_raw) as unique_suppliers,
    COUNT(DISTINCT hs_code_raw) as unique_hs_codes
FROM stg_shipments_raw
WHERE buyer_name_raw IS NOT NULL;

-- Daily ingestion volume
SELECT 
    DATE(ingested_at) as ingestion_date,
    COUNT(*) as rows_ingested,
    COUNT(DISTINCT raw_file_name) as files_ingested
FROM stg_shipments_raw
GROUP BY DATE(ingested_at)
ORDER BY ingestion_date DESC;

-- =====================================================================
-- DATA QUALITY CHECKS
-- =====================================================================

-- Rows with missing critical fields
SELECT 
    reporting_country,
    direction,
    COUNT(*) as total_rows,
    COUNT(hs_code_raw) as has_hs_code,
    COUNT(buyer_name_raw) as has_buyer,
    COUNT(supplier_name_raw) as has_supplier,
    COUNT(*) - COUNT(hs_code_raw) as missing_hs_code,
    COUNT(*) - COUNT(buyer_name_raw) as missing_buyer
FROM stg_shipments_raw
GROUP BY reporting_country, direction;

-- Find duplicate file checksums (should be none)
SELECT 
    file_checksum,
    COUNT(*) as count
FROM file_registry
GROUP BY file_checksum
HAVING COUNT(*) > 1;

-- Check for orphaned raw rows (file not in registry)
SELECT COUNT(*) as orphaned_rows
FROM stg_shipments_raw r
WHERE NOT EXISTS (
    SELECT 1 FROM file_registry f 
    WHERE f.file_name = r.raw_file_name
);

-- =====================================================================
-- PERFORMANCE MONITORING
-- =====================================================================

-- Table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_total_relation_size(schemaname||'.'||tablename) as bytes
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY bytes DESC;

-- Index usage statistics
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Largest tables by row count
SELECT 
    schemaname,
    tablename,
    n_live_tup as row_count
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC;

-- =====================================================================
-- SAMPLE DATA EXPLORATION
-- =====================================================================

-- Top 10 HS codes by frequency
SELECT 
    hs_code_raw,
    COUNT(*) as frequency,
    COUNT(DISTINCT raw_file_name) as files
FROM stg_shipments_raw
WHERE hs_code_raw IS NOT NULL AND hs_code_raw != ''
GROUP BY hs_code_raw
ORDER BY frequency DESC
LIMIT 10;

-- Top buyers by transaction count
SELECT 
    buyer_name_raw,
    COUNT(*) as transactions,
    COUNT(DISTINCT raw_file_name) as files
FROM stg_shipments_raw
WHERE buyer_name_raw IS NOT NULL AND buyer_name_raw != ''
GROUP BY buyer_name_raw
ORDER BY transactions DESC
LIMIT 10;

-- Top suppliers by transaction count
SELECT 
    supplier_name_raw,
    COUNT(*) as transactions,
    COUNT(DISTINCT raw_file_name) as files
FROM stg_shipments_raw
WHERE supplier_name_raw IS NOT NULL AND supplier_name_raw != ''
GROUP BY supplier_name_raw
ORDER BY transactions DESC
LIMIT 10;

-- Sample JSON data structure
SELECT 
    raw_file_name,
    jsonb_object_keys(raw_data) as field_name
FROM stg_shipments_raw
LIMIT 1;

-- Count fields in JSON data
SELECT 
    raw_file_name,
    COUNT(DISTINCT jsonb_object_keys(raw_data)) as field_count
FROM stg_shipments_raw
GROUP BY raw_file_name
ORDER BY field_count DESC;

-- =====================================================================
-- CLEANUP & MAINTENANCE
-- =====================================================================

-- Delete all data from a specific file (use with caution!)
-- Uncomment to use:
-- DELETE FROM stg_shipments_raw 
-- WHERE raw_file_name = 'specific_file.xlsx';
-- 
-- DELETE FROM file_registry 
-- WHERE file_name = 'specific_file.xlsx';

-- Reset file registry status (to re-ingest)
-- Uncomment to use:
-- UPDATE file_registry 
-- SET status = 'PENDING', ingested_at = NULL 
-- WHERE file_name = 'specific_file.xlsx';

-- Vacuum tables (reclaim space after deletes)
-- VACUUM ANALYZE file_registry;
-- VACUUM ANALYZE stg_shipments_raw;

-- =====================================================================
-- EXPORT QUERIES
-- =====================================================================

-- Export sample to CSV (from psql)
-- \copy (SELECT * FROM stg_shipments_raw LIMIT 1000) TO 'sample_data.csv' WITH CSV HEADER;

-- Export file registry summary
-- \copy (SELECT * FROM file_registry) TO 'file_registry_export.csv' WITH CSV HEADER;

-- =====================================================================
-- PHASE 2+ PREVIEW (Empty tables for now)
-- =====================================================================

-- Check standardized shipments (Phase 2)
SELECT COUNT(*) FROM stg_shipments_standardized;

-- Check organizations (Phase 3)
SELECT COUNT(*) FROM organizations_master;

-- Check global trades ledger (Phase 4)
SELECT COUNT(*) FROM global_trades_ledger;

-- Check all analytics tables
SELECT 
    'buyer_profile' as table_name, COUNT(*) as row_count FROM buyer_profile
UNION ALL
SELECT 'exporter_profile', COUNT(*) FROM exporter_profile
UNION ALL
SELECT 'price_corridor', COUNT(*) FROM price_corridor
UNION ALL
SELECT 'lane_stats', COUNT(*) FROM lane_stats
UNION ALL
SELECT 'risk_scores', COUNT(*) FROM risk_scores;

-- =====================================================================
-- END OF QUERIES
-- =====================================================================
