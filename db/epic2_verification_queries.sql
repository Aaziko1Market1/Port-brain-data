-- =====================================================================
-- GTI-OS Data Platform - EPIC 2 Verification Queries
-- Standardization Engine validation and testing
-- =====================================================================

-- =====================================================================
-- BASIC COUNTS & STATUS
-- =====================================================================

-- Total raw vs standardized rows
SELECT 
    'Raw Rows' as table_name, 
    COUNT(*) as row_count 
FROM stg_shipments_raw
UNION ALL
SELECT 
    'Standardized Rows', 
    COUNT(*) 
FROM stg_shipments_standardized;

-- Standardization progress by country/direction
SELECT 
    r.reporting_country,
    r.direction,
    COUNT(DISTINCT r.raw_id) as total_raw_rows,
    COUNT(DISTINCT s.std_id) as standardized_rows,
    COUNT(DISTINCT r.raw_id) - COUNT(DISTINCT s.std_id) as pending_rows,
    ROUND(100.0 * COUNT(DISTINCT s.std_id) / COUNT(DISTINCT r.raw_id), 2) as pct_complete
FROM stg_shipments_raw r
LEFT JOIN stg_shipments_standardized s ON r.raw_id = s.raw_id
GROUP BY r.reporting_country, r.direction
ORDER BY r.reporting_country, r.direction;

-- Recent standardized rows
SELECT 
    reporting_country,
    direction,
    COUNT(*) as rows,
    MIN(standardized_at) as first_standardized,
    MAX(standardized_at) as last_standardized
FROM stg_shipments_standardized
GROUP BY reporting_country, direction
ORDER BY last_standardized DESC;

-- =====================================================================
-- DATA QUALITY CHECKS
-- =====================================================================

-- Check HS code normalization
SELECT 
    hs_code_raw,
    hs_code_6,
    COUNT(*) as frequency
FROM stg_shipments_standardized
WHERE hs_code_raw IS NOT NULL
GROUP BY hs_code_raw, hs_code_6
ORDER BY frequency DESC
LIMIT 20;

-- Check country normalization
SELECT 
    origin_country_raw,
    origin_country,
    COUNT(*) as frequency
FROM stg_shipments_standardized
WHERE origin_country_raw IS NOT NULL
GROUP BY origin_country_raw, origin_country
ORDER BY frequency DESC
LIMIT 20;

-- Check destination normalization
SELECT 
    destination_country_raw,
    destination_country,
    COUNT(*) as frequency
FROM stg_shipments_standardized
WHERE destination_country_raw IS NOT NULL
GROUP BY destination_country_raw, destination_country
ORDER BY frequency DESC
LIMIT 20;

-- =====================================================================
-- UNIT CONVERSIONS VALIDATION
-- =====================================================================

-- Weight conversion check
SELECT 
    qty_raw,
    qty_unit_raw,
    qty_kg,
    CASE 
        WHEN qty_raw IS NOT NULL AND qty_kg IS NOT NULL 
        THEN ROUND(qty_kg / qty_raw, 2)
        ELSE NULL
    END as conversion_factor
FROM stg_shipments_standardized
WHERE qty_raw IS NOT NULL AND qty_kg IS NOT NULL
LIMIT 20;

-- Value conversion check (sample)
SELECT 
    value_raw,
    fob_usd,
    cif_usd,
    customs_value_usd,
    reporting_country,
    direction
FROM stg_shipments_standardized
WHERE value_raw IS NOT NULL
LIMIT 20;

-- Price per kg distribution
SELECT 
    hs_code_6,
    destination_country,
    COUNT(*) as shipments,
    MIN(price_usd_per_kg) as min_price,
    ROUND(AVG(price_usd_per_kg)::numeric, 2) as avg_price,
    MAX(price_usd_per_kg) as max_price
FROM stg_shipments_standardized
WHERE price_usd_per_kg IS NOT NULL
AND price_usd_per_kg > 0
GROUP BY hs_code_6, destination_country
HAVING COUNT(*) >= 5
ORDER BY shipments DESC
LIMIT 20;

-- =====================================================================
-- DATE PARSING VALIDATION
-- =====================================================================

-- Date parsing success rate
SELECT 
    reporting_country,
    direction,
    COUNT(*) as total_rows,
    COUNT(shipment_date) as parsed_shipment_date,
    COUNT(export_date) as parsed_export_date,
    COUNT(import_date) as parsed_import_date,
    COUNT(year) as has_year,
    COUNT(month) as has_month,
    ROUND(100.0 * COUNT(shipment_date) / COUNT(*), 2) as date_parse_pct
FROM stg_shipments_standardized
GROUP BY reporting_country, direction;

-- Year/Month distribution
SELECT 
    year,
    month,
    COUNT(*) as shipments,
    COUNT(DISTINCT hs_code_6) as unique_products
FROM stg_shipments_standardized
WHERE year IS NOT NULL
GROUP BY year, month
ORDER BY year DESC, month DESC;

-- =====================================================================
-- COMPLETENESS CHECKS
-- =====================================================================

-- Field completeness summary
SELECT 
    reporting_country,
    direction,
    COUNT(*) as total_rows,
    COUNT(hs_code_6) as has_hs_code,
    COUNT(buyer_name_raw) as has_buyer,
    COUNT(supplier_name_raw) as has_supplier,
    COUNT(qty_kg) as has_qty_kg,
    COUNT(customs_value_usd) as has_value,
    COUNT(price_usd_per_kg) as has_price_per_kg,
    COUNT(vessel_name) as has_vessel,
    COUNT(port_loading) as has_port_loading,
    ROUND(100.0 * COUNT(hs_code_6) / COUNT(*), 2) as hs_complete_pct,
    ROUND(100.0 * COUNT(qty_kg) / COUNT(*), 2) as qty_complete_pct,
    ROUND(100.0 * COUNT(customs_value_usd) / COUNT(*), 2) as value_complete_pct
FROM stg_shipments_standardized
GROUP BY reporting_country, direction
ORDER BY reporting_country, direction;

-- Rows with missing critical fields
SELECT 
    COUNT(*) as rows_missing_critical_fields
FROM stg_shipments_standardized
WHERE hs_code_6 IS NULL 
   OR qty_kg IS NULL 
   OR customs_value_usd IS NULL;

-- =====================================================================
-- SAMPLE DATA INSPECTION
-- =====================================================================

-- Sample standardized records (full view)
SELECT 
    std_id,
    reporting_country,
    direction,
    hs_code_raw,
    hs_code_6,
    goods_description,
    buyer_name_raw,
    supplier_name_raw,
    origin_country,
    destination_country,
    shipment_date,
    year,
    month,
    qty_raw,
    qty_unit_raw,
    qty_kg,
    value_raw,
    customs_value_usd,
    price_usd_per_kg,
    teu,
    standardized_at
FROM stg_shipments_standardized
ORDER BY standardized_at DESC
LIMIT 10;

-- Compare raw vs standardized (side by side)
SELECT 
    r.raw_file_name,
    r.reporting_country,
    r.direction,
    r.raw_data->>'hs_code' as raw_hs_code,
    s.hs_code_6 as std_hs_code,
    r.raw_data->>'quantity_kg' as raw_qty,
    s.qty_kg as std_qty_kg,
    r.raw_data->>'fob_value_usd' as raw_value,
    s.customs_value_usd as std_value_usd
FROM stg_shipments_raw r
JOIN stg_shipments_standardized s ON r.raw_id = s.raw_id
LIMIT 10;

-- =====================================================================
-- ANOMALY DETECTION
-- =====================================================================

-- Outlier prices (suspiciously high or low)
SELECT 
    hs_code_6,
    goods_description,
    destination_country,
    price_usd_per_kg,
    qty_kg,
    customs_value_usd
FROM stg_shipments_standardized
WHERE price_usd_per_kg IS NOT NULL
AND (
    price_usd_per_kg > 10000  -- Suspiciously high
    OR price_usd_per_kg < 0.01  -- Suspiciously low
)
ORDER BY price_usd_per_kg DESC
LIMIT 20;

-- Zero or negative values
SELECT 
    reporting_country,
    direction,
    COUNT(*) as zero_or_negative_count
FROM stg_shipments_standardized
WHERE qty_kg <= 0 OR customs_value_usd <= 0
GROUP BY reporting_country, direction;

-- Missing geography
SELECT 
    COUNT(*) as rows_missing_geography
FROM stg_shipments_standardized
WHERE origin_country IS NULL 
   OR destination_country IS NULL;

-- =====================================================================
-- PERFORMANCE METRICS
-- =====================================================================

-- Standardization throughput by batch
SELECT 
    DATE(standardized_at) as standardization_date,
    reporting_country,
    direction,
    COUNT(*) as rows_standardized,
    MIN(standardized_at) as first_row,
    MAX(standardized_at) as last_row,
    EXTRACT(EPOCH FROM (MAX(standardized_at) - MIN(standardized_at))) as duration_seconds
FROM stg_shipments_standardized
GROUP BY DATE(standardized_at), reporting_country, direction
ORDER BY standardization_date DESC;

-- =====================================================================
-- EXPORT QUERIES (for further analysis)
-- =====================================================================

-- Export standardized summary to CSV (use \copy in psql)
-- \copy (
--   SELECT hs_code_6, destination_country, 
--          COUNT(*) as shipments, 
--          SUM(qty_kg) as total_kg, 
--          SUM(customs_value_usd) as total_value
--   FROM stg_shipments_standardized
--   GROUP BY hs_code_6, destination_country
-- ) TO 'standardized_summary.csv' WITH CSV HEADER;

-- =====================================================================
-- KENYA IMPORT FULL - SPECIFIC VERIFICATION
-- =====================================================================

-- Kenya Import Full: Basic counts (raw vs standardized)
SELECT 
    'Kenya Import Full - Raw Rows' as check_type,
    COUNT(*) as row_count
FROM stg_shipments_raw
WHERE reporting_country = 'KENYA'
  AND direction = 'IMPORT'
  AND source_format = 'FULL'
UNION ALL
SELECT 
    'Kenya Import Full - Standardized Rows',
    COUNT(*)
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA'
  AND direction = 'IMPORT'
  AND source_format = 'FULL';

-- Kenya Import Full: Column mapping validation
-- Verify IMPORTER_NAME, SUPPLIER_NAME, HS_CODE, ORIGIN_COUNTRY are mapped correctly
SELECT 
    'Importer Name Mapped' as field_check,
    COUNT(*) as total_rows,
    COUNT(buyer_name_raw) as field_populated,
    ROUND(100.0 * COUNT(buyer_name_raw) / COUNT(*), 2) as pct_populated
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' AND direction = 'IMPORT' AND source_format = 'FULL'
UNION ALL
SELECT 
    'Supplier Name Mapped',
    COUNT(*),
    COUNT(supplier_name_raw),
    ROUND(100.0 * COUNT(supplier_name_raw) / COUNT(*), 2)
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' AND direction = 'IMPORT' AND source_format = 'FULL'
UNION ALL
SELECT 
    'HS Code Mapped',
    COUNT(*),
    COUNT(hs_code_raw),
    ROUND(100.0 * COUNT(hs_code_raw) / COUNT(*), 2)
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' AND direction = 'IMPORT' AND source_format = 'FULL'
UNION ALL
SELECT 
    'Origin Country Mapped',
    COUNT(*),
    COUNT(origin_country_raw),
    ROUND(100.0 * COUNT(origin_country_raw) / COUNT(*), 2)
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' AND direction = 'IMPORT' AND source_format = 'FULL';

-- Kenya Import Full: HS Code normalization (10-digit to 6-digit)
SELECT 
    hs_code_raw as kenya_hs_10digit,
    hs_code_6 as normalized_hs6,
    COUNT(*) as frequency,
    SUM(customs_value_usd) as total_value_usd
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'IMPORT' 
  AND source_format = 'FULL'
  AND hs_code_raw IS NOT NULL
GROUP BY hs_code_raw, hs_code_6
ORDER BY frequency DESC
LIMIT 20;

-- Kenya Import Full: Origin country normalization
SELECT 
    origin_country_raw as kenya_raw_origin,
    origin_country as normalized_origin,
    COUNT(*) as shipment_count,
    SUM(customs_value_usd) as total_value_usd
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'IMPORT' 
  AND source_format = 'FULL'
  AND origin_country_raw IS NOT NULL
GROUP BY origin_country_raw, origin_country
ORDER BY shipment_count DESC
LIMIT 20;

-- Kenya Import Full: Unit conversions (QUANTITY + UNIT -> qty_kg)
-- Common Kenya units: MTK (sq meters), KGM (kilograms), PCS (pieces), LTR (liters)
SELECT 
    qty_unit_raw as kenya_unit,
    COUNT(*) as frequency,
    COUNT(qty_kg) as converted_to_kg,
    ROUND(100.0 * COUNT(qty_kg) / COUNT(*), 2) as conversion_success_pct,
    MIN(qty_raw) as min_qty_raw,
    AVG(qty_raw) as avg_qty_raw,
    MAX(qty_raw) as max_qty_raw,
    MIN(qty_kg) as min_qty_kg,
    AVG(qty_kg) as avg_qty_kg,
    MAX(qty_kg) as max_qty_kg
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'IMPORT' 
  AND source_format = 'FULL'
GROUP BY qty_unit_raw
ORDER BY frequency DESC
LIMIT 15;

-- Kenya Import Full: Currency conversion (TOTAL_VALUE_USD should already be in USD)
SELECT 
    'Total Value USD Mapped' as value_check,
    COUNT(*) as total_rows,
    COUNT(customs_value_usd) as value_populated,
    ROUND(100.0 * COUNT(customs_value_usd) / COUNT(*), 2) as pct_populated,
    MIN(customs_value_usd) as min_value,
    ROUND(AVG(customs_value_usd)::numeric, 2) as avg_value,
    MAX(customs_value_usd) as max_value
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'IMPORT' 
  AND source_format = 'FULL';

-- Kenya Import Full: Price per kg calculation
SELECT 
    hs_code_6,
    goods_description,
    COUNT(*) as shipments,
    ROUND(MIN(price_usd_per_kg)::numeric, 2) as min_price_per_kg,
    ROUND(AVG(price_usd_per_kg)::numeric, 2) as avg_price_per_kg,
    ROUND(MAX(price_usd_per_kg)::numeric, 2) as max_price_per_kg,
    ROUND(SUM(qty_kg)::numeric, 2) as total_kg,
    ROUND(SUM(customs_value_usd)::numeric, 2) as total_value_usd
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'IMPORT' 
  AND source_format = 'FULL'
  AND price_usd_per_kg IS NOT NULL
  AND qty_kg > 0
GROUP BY hs_code_6, goods_description
HAVING COUNT(*) >= 3
ORDER BY total_value_usd DESC
LIMIT 20;

-- Kenya Import Full: Date parsing validation (IMP_DATE field)
SELECT 
    'Import Date Parsed' as date_check,
    COUNT(*) as total_rows,
    COUNT(import_date) as dates_parsed,
    ROUND(100.0 * COUNT(import_date) / COUNT(*), 2) as parse_success_pct,
    MIN(import_date) as earliest_date,
    MAX(import_date) as latest_date
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'IMPORT' 
  AND source_format = 'FULL';

-- Kenya Import Full: Year/Month distribution
SELECT 
    year,
    month,
    COUNT(*) as shipments,
    COUNT(DISTINCT hs_code_6) as unique_products,
    COUNT(DISTINCT buyer_name_raw) as unique_importers,
    COUNT(DISTINCT origin_country) as unique_origins,
    ROUND(SUM(qty_kg)::numeric, 2) as total_kg,
    ROUND(SUM(customs_value_usd)::numeric, 2) as total_value_usd
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'IMPORT' 
  AND source_format = 'FULL'
GROUP BY year, month
ORDER BY year DESC, month DESC;

-- Kenya Import Full: Sample records (first 10)
SELECT 
    std_id,
    source_file,
    hs_code_raw,
    hs_code_6,
    goods_description,
    buyer_name_raw as importer_name,
    supplier_name_raw,
    origin_country_raw,
    origin_country,
    destination_country,
    import_date,
    qty_raw,
    qty_unit_raw,
    qty_kg,
    value_raw,
    customs_value_usd,
    price_usd_per_kg,
    standardized_at
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'IMPORT' 
  AND source_format = 'FULL'
ORDER BY standardized_at DESC
LIMIT 10;

-- Kenya Import Full: Data quality issues
-- Check for rows with missing critical fields
SELECT 
    'Missing HS Code' as issue_type,
    COUNT(*) as affected_rows
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'IMPORT' 
  AND source_format = 'FULL'
  AND hs_code_6 IS NULL
UNION ALL
SELECT 
    'Missing Origin Country',
    COUNT(*)
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'IMPORT' 
  AND source_format = 'FULL'
  AND origin_country IS NULL
UNION ALL
SELECT 
    'Missing Quantity (kg)',
    COUNT(*)
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'IMPORT' 
  AND source_format = 'FULL'
  AND qty_kg IS NULL
UNION ALL
SELECT 
    'Missing Value (USD)',
    COUNT(*)
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'IMPORT' 
  AND source_format = 'FULL'
  AND customs_value_usd IS NULL
UNION ALL
SELECT 
    'Zero or Negative Quantity',
    COUNT(*)
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'IMPORT' 
  AND source_format = 'FULL'
  AND (qty_kg <= 0 OR qty_kg IS NULL)
UNION ALL
SELECT 
    'Zero or Negative Value',
    COUNT(*)
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'IMPORT' 
  AND source_format = 'FULL'
  AND (customs_value_usd <= 0 OR customs_value_usd IS NULL);

-- Kenya Import Full: Top importers by value
SELECT 
    buyer_name_raw as importer_name,
    COUNT(*) as total_shipments,
    COUNT(DISTINCT hs_code_6) as unique_products,
    COUNT(DISTINCT origin_country) as unique_origins,
    ROUND(SUM(qty_kg)::numeric, 2) as total_kg,
    ROUND(SUM(customs_value_usd)::numeric, 2) as total_value_usd,
    ROUND(AVG(customs_value_usd)::numeric, 2) as avg_value_per_shipment
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'IMPORT' 
  AND source_format = 'FULL'
  AND buyer_name_raw IS NOT NULL
GROUP BY buyer_name_raw
ORDER BY total_value_usd DESC
LIMIT 20;

-- Kenya Import Full: Top origin countries
SELECT 
    origin_country,
    COUNT(*) as total_shipments,
    COUNT(DISTINCT hs_code_6) as unique_products,
    COUNT(DISTINCT buyer_name_raw) as unique_importers,
    ROUND(SUM(qty_kg)::numeric, 2) as total_kg,
    ROUND(SUM(customs_value_usd)::numeric, 2) as total_value_usd,
    ROUND(AVG(price_usd_per_kg)::numeric, 2) as avg_price_per_kg
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'IMPORT' 
  AND source_format = 'FULL'
  AND origin_country IS NOT NULL
GROUP BY origin_country
ORDER BY total_value_usd DESC
LIMIT 20;

-- =====================================================================
-- KENYA EXPORT FULL VERIFICATION QUERIES
-- =====================================================================

-- Kenya Export Full: Raw vs Standardized Row Counts
SELECT 
    'KENYA_EXPORT_FULL' AS group_name,
    SUM(CASE WHEN table_name = 'stg_shipments_raw' THEN row_count ELSE 0 END) AS raw_rows,
    SUM(CASE WHEN table_name = 'stg_shipments_standardized' THEN row_count ELSE 0 END) AS standardized_rows,
    ROUND(100.0 * SUM(CASE WHEN table_name = 'stg_shipments_standardized' THEN row_count ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN table_name = 'stg_shipments_raw' THEN row_count ELSE 0 END), 0), 2) AS coverage_pct
FROM (
    SELECT 'stg_shipments_raw' AS table_name, COUNT(*) AS row_count
    FROM stg_shipments_raw
    WHERE reporting_country = 'KENYA' AND direction = 'EXPORT' AND source_format = 'FULL'
    UNION ALL
    SELECT 'stg_shipments_standardized' AS table_name, COUNT(*) AS row_count
    FROM stg_shipments_standardized
    WHERE reporting_country = 'KENYA' AND direction = 'EXPORT' AND source_format = 'FULL'
) t;

-- Kenya Export Full: HS Code Normalization
-- Verify that 10-digit HS codes are normalized to 6 digits
SELECT 
    hs_code_raw,
    hs_code_6,
    COUNT(*) AS frequency,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'EXPORT' 
  AND source_format = 'FULL'
  AND hs_code_raw IS NOT NULL
GROUP BY hs_code_raw, hs_code_6
ORDER BY frequency DESC
LIMIT 15;

-- Kenya Export Full: Destination Country Normalization
-- Check how raw destination countries are normalized
SELECT 
    destination_country_raw,
    destination_country,
    COUNT(*) AS shipment_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'EXPORT' 
  AND source_format = 'FULL'
  AND destination_country_raw IS NOT NULL
GROUP BY destination_country_raw, destination_country
ORDER BY shipment_count DESC
LIMIT 20;

-- Kenya Export Full: Unit conversions (TOTALQUANTITY -> qty_kg)
-- Note: Unit not available in aggregated data, so qty_kg will be NULL
SELECT 
    qty_unit_raw as kenya_unit,
    COUNT(*) as frequency,
    COUNT(qty_kg) as converted_to_kg,
    ROUND(100.0 * COUNT(qty_kg) / COUNT(*), 2) as conversion_success_pct,
    MIN(qty_raw) as min_qty_raw,
    AVG(qty_raw) as avg_qty_raw,
    MAX(qty_raw) as max_qty_raw,
    MIN(qty_kg) as min_qty_kg,
    AVG(qty_kg) as avg_qty_kg,
    MAX(qty_kg) as max_qty_kg
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'EXPORT' 
  AND source_format = 'FULL'
GROUP BY qty_unit_raw
ORDER BY frequency DESC
LIMIT 15;

-- Kenya Export Full: Value Coverage
-- Check if customs_value_usd is populated (should use TOTALVALUE)
SELECT 
    'Total Value Coverage' as value_check,
    COUNT(*) as total_rows,
    COUNT(customs_value_usd) as value_populated,
    ROUND(100.0 * COUNT(customs_value_usd) / COUNT(*), 2) as pct_populated,
    MIN(customs_value_usd) as min_value,
    ROUND(AVG(customs_value_usd)::numeric, 2) as avg_value,
    MAX(customs_value_usd) as max_value,
    ROUND(SUM(customs_value_usd)::numeric, 2) as total_value
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'EXPORT' 
  AND source_format = 'FULL';

-- Kenya Export Full: FOB Value Coverage (if available)
SELECT 
    'FOB Value Coverage' as value_check,
    COUNT(*) as total_rows,
    COUNT(fob_usd) as fob_populated,
    ROUND(100.0 * COUNT(fob_usd) / COUNT(*), 2) as pct_populated,
    MIN(fob_usd) as min_fob,
    ROUND(AVG(fob_usd)::numeric, 2) as avg_fob,
    MAX(fob_usd) as max_fob,
    ROUND(SUM(fob_usd)::numeric, 2) as total_fob
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'EXPORT' 
  AND source_format = 'FULL';

-- Kenya Export Full: Data Completeness
SELECT 
    'Exporter (Supplier)' AS field_name,
    COUNT(*) AS total_rows,
    COUNT(supplier_name_raw) AS populated,
    ROUND(100.0 * COUNT(supplier_name_raw) / COUNT(*), 2) AS completeness_pct
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' AND direction = 'EXPORT' AND source_format = 'FULL'
UNION ALL
SELECT 
    'Buyer (Consignee)' AS field_name,
    COUNT(*) AS total_rows,
    COUNT(buyer_name_raw) AS populated,
    ROUND(100.0 * COUNT(buyer_name_raw) / COUNT(*), 2) AS completeness_pct
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' AND direction = 'EXPORT' AND source_format = 'FULL'
UNION ALL
SELECT 
    'HS Code' AS field_name,
    COUNT(*) AS total_rows,
    COUNT(hs_code_6) AS populated,
    ROUND(100.0 * COUNT(hs_code_6) / COUNT(*), 2) AS completeness_pct
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' AND direction = 'EXPORT' AND source_format = 'FULL'
UNION ALL
SELECT 
    'Destination Country' AS field_name,
    COUNT(*) AS total_rows,
    COUNT(destination_country) AS populated,
    ROUND(100.0 * COUNT(destination_country) / COUNT(*), 2) AS completeness_pct
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' AND direction = 'EXPORT' AND source_format = 'FULL'
UNION ALL
SELECT 
    'Quantity' AS field_name,
    COUNT(*) AS total_rows,
    COUNT(qty_raw) AS populated,
    ROUND(100.0 * COUNT(qty_raw) / COUNT(*), 2) AS completeness_pct
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' AND direction = 'EXPORT' AND source_format = 'FULL'
UNION ALL
SELECT 
    'Value USD' AS field_name,
    COUNT(*) AS total_rows,
    COUNT(customs_value_usd) AS populated,
    ROUND(100.0 * COUNT(customs_value_usd) / COUNT(*), 2) AS completeness_pct
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' AND direction = 'EXPORT' AND source_format = 'FULL'
ORDER BY field_name;

-- Kenya Export Full: Sample records (first 10)
SELECT 
    std_id,
    source_file,
    hs_code_raw,
    hs_code_6,
    goods_description,
    supplier_name_raw as exporter_name,
    buyer_name_raw as consignee_name,
    origin_country,
    destination_country_raw,
    destination_country,
    export_date,
    qty_raw,
    qty_unit_raw,
    qty_kg,
    value_raw,
    fob_usd,
    customs_value_usd,
    price_usd_per_kg,
    standardized_at
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'EXPORT' 
  AND source_format = 'FULL'
ORDER BY standardized_at DESC
LIMIT 10;

-- Kenya Export Full: Top Exporters (Kenyan Companies)
SELECT 
    supplier_name_raw as exporter,
    COUNT(*) as shipment_count,
    COUNT(DISTINCT hs_code_6) as unique_products,
    COUNT(DISTINCT destination_country) as unique_destinations,
    ROUND(SUM(customs_value_usd)::numeric, 2) as total_value_usd,
    ROUND(AVG(customs_value_usd)::numeric, 2) as avg_value_per_shipment
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'EXPORT' 
  AND source_format = 'FULL'
  AND supplier_name_raw IS NOT NULL
GROUP BY supplier_name_raw
ORDER BY total_value_usd DESC
LIMIT 20;

-- Kenya Export Full: Top Destination Countries
SELECT 
    destination_country,
    COUNT(*) as shipment_count,
    COUNT(DISTINCT supplier_name_raw) as unique_exporters,
    COUNT(DISTINCT hs_code_6) as unique_products,
    ROUND(SUM(customs_value_usd)::numeric, 2) as total_value_usd,
    ROUND(AVG(customs_value_usd)::numeric, 2) as avg_value_per_shipment
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'EXPORT' 
  AND source_format = 'FULL'
  AND destination_country IS NOT NULL
GROUP BY destination_country
ORDER BY total_value_usd DESC
LIMIT 20;

-- Kenya Export Full: Top Export Products (by HS Code 6)
SELECT 
    hs_code_6,
    MAX(goods_description) as product_description,
    COUNT(*) as shipment_count,
    COUNT(DISTINCT supplier_name_raw) as unique_exporters,
    COUNT(DISTINCT destination_country) as unique_destinations,
    ROUND(SUM(customs_value_usd)::numeric, 2) as total_value_usd,
    ROUND(AVG(customs_value_usd)::numeric, 2) as avg_value_per_shipment
FROM stg_shipments_standardized
WHERE reporting_country = 'KENYA' 
  AND direction = 'EXPORT' 
  AND source_format = 'FULL'
  AND hs_code_6 IS NOT NULL
GROUP BY hs_code_6
ORDER BY total_value_usd DESC
LIMIT 20;

-- =====================================================================
-- END OF EPIC 2 VERIFICATION QUERIES (INCLUDING KENYA IMPORT & EXPORT FULL)
-- =====================================================================
