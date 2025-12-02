-- =====================================================================
-- Migration 008: Remove year/month requirement from Admin Upload
-- =====================================================================
-- Adds min_shipment_date and max_shipment_date to file_registry
-- These are computed AFTER standardization based on actual data
-- =====================================================================

-- STEP 1: Add date coverage columns to file_registry
-- =====================================================================

-- Min and max shipment dates from actual data (computed after standardization)
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS min_shipment_date DATE;
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS max_shipment_date DATE;

-- STEP 2: Create index for date coverage queries
-- =====================================================================
CREATE INDEX IF NOT EXISTS idx_fr_shipment_date_range 
    ON file_registry(min_shipment_date, max_shipment_date);

-- STEP 3: Add comment for documentation
-- =====================================================================
COMMENT ON COLUMN file_registry.min_shipment_date IS 
    'Minimum shipment_date from standardized data. Computed after standardization completes.';
COMMENT ON COLUMN file_registry.max_shipment_date IS 
    'Maximum shipment_date from standardized data. Computed after standardization completes.';
COMMENT ON COLUMN file_registry.year IS 
    'DEPRECATED: Year should be derived from shipment_date in standardized data. Kept for backward compatibility.';
COMMENT ON COLUMN file_registry.month IS 
    'DEPRECATED: Month should be derived from shipment_date in standardized data. Kept for backward compatibility.';

-- =====================================================================
-- MIGRATION COMPLETE
-- =====================================================================
