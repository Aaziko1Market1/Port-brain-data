-- =====================================================================
-- Migration 009: Mapping Registry for Multi-Country Onboarding
-- =====================================================================
-- EPIC 10: Tracks per-country mapping status (DRAFT / VERIFIED / LIVE)
-- Ensures safe onboarding of new countries without corrupting production
-- =====================================================================

-- STEP 1: Create mapping_registry table
-- =====================================================================

CREATE TABLE IF NOT EXISTS mapping_registry (
    mapping_id SERIAL PRIMARY KEY,
    reporting_country TEXT NOT NULL,
    direction TEXT NOT NULL,          -- IMPORT / EXPORT
    source_format TEXT NOT NULL,      -- FULL / SHORT
    config_key TEXT NOT NULL,         -- e.g. 'kenya_import_full'
    yaml_path TEXT NOT NULL,          -- e.g. 'config/kenya_import_full.yml'
    status TEXT NOT NULL DEFAULT 'DRAFT', -- DRAFT / VERIFIED / LIVE
    sample_file_path TEXT,            -- e.g. 'data/reference/port_real/Kenya Import F.xlsx'
    last_verified_at TIMESTAMPTZ,
    verified_row_count INTEGER,       -- Number of rows validated
    verified_date_coverage TEXT,      -- e.g. '2023-01 to 2024-06'
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_mr_direction CHECK (direction IN ('IMPORT', 'EXPORT')),
    CONSTRAINT chk_mr_source_format CHECK (source_format IN ('FULL', 'SHORT')),
    CONSTRAINT chk_mr_status CHECK (status IN ('DRAFT', 'VERIFIED', 'LIVE'))
);

-- Unique index on the natural key
CREATE UNIQUE INDEX IF NOT EXISTS idx_mapping_registry_key
    ON mapping_registry (reporting_country, direction, source_format);

-- Index for status queries
CREATE INDEX IF NOT EXISTS idx_mapping_registry_status
    ON mapping_registry (status);

-- Index for config_key lookups
CREATE INDEX IF NOT EXISTS idx_mapping_registry_config_key
    ON mapping_registry (config_key);

-- STEP 2: Add comments for documentation
-- =====================================================================

COMMENT ON TABLE mapping_registry IS 
    'EPIC 10: Registry of country/direction/format mappings with lifecycle status (DRAFT → VERIFIED → LIVE)';

COMMENT ON COLUMN mapping_registry.status IS 
    'DRAFT = auto-generated, untested; VERIFIED = passed sandbox validation; LIVE = approved for production pipeline';

COMMENT ON COLUMN mapping_registry.config_key IS 
    'Unique key like "kenya_import_full" used to identify the YAML config file';

COMMENT ON COLUMN mapping_registry.sample_file_path IS 
    'Path to sample file used for validation, e.g. data/reference/port_real/Kenya Import F.xlsx';

COMMENT ON COLUMN mapping_registry.last_verified_at IS 
    'Timestamp when the mapping was last validated successfully in sandbox';

-- STEP 3: Create sandbox/temporary tables for validation
-- =====================================================================

-- Temporary raw table for sandbox validation (mirrors stg_shipments_raw structure)
CREATE TABLE IF NOT EXISTS tmp_stg_shipments_raw (
    raw_id BIGSERIAL PRIMARY KEY,
    raw_file_name TEXT NOT NULL,
    reporting_country TEXT NOT NULL,
    direction TEXT NOT NULL,
    source_format TEXT,
    record_grain TEXT,
    raw_row_number INTEGER NOT NULL,
    raw_data JSONB NOT NULL,
    file_checksum TEXT,
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Validation session tracking
    validation_session_id UUID,
    
    CONSTRAINT chk_tmp_raw_direction CHECK (direction IN ('EXPORT', 'IMPORT'))
);

CREATE INDEX IF NOT EXISTS idx_tmp_raw_session ON tmp_stg_shipments_raw(validation_session_id);
CREATE INDEX IF NOT EXISTS idx_tmp_raw_country ON tmp_stg_shipments_raw(reporting_country, direction);

-- Temporary standardized table for sandbox validation
CREATE TABLE IF NOT EXISTS tmp_stg_shipments_standardized (
    std_id BIGSERIAL PRIMARY KEY,
    raw_id BIGINT,
    
    -- Standardized entity names
    buyer_name_raw TEXT,
    buyer_name_clean TEXT,
    supplier_name_raw TEXT,
    supplier_name_clean TEXT,
    
    -- Product classification
    hs_code_raw TEXT,
    hs_code_6 TEXT,
    goods_description TEXT,
    
    -- Geography
    origin_country TEXT,
    origin_country_raw TEXT,
    destination_country TEXT,
    destination_country_raw TEXT,
    reporting_country TEXT,
    
    -- Dates
    export_date DATE,
    import_date DATE,
    shipment_date DATE,
    year INTEGER,
    month INTEGER,
    
    -- Quantities
    qty_raw NUMERIC,
    qty_unit_raw TEXT,
    qty_kg NUMERIC,
    
    -- Values
    value_raw NUMERIC,
    value_currency TEXT,
    fob_usd NUMERIC,
    cif_usd NUMERIC,
    customs_value_usd NUMERIC,
    price_usd_per_kg NUMERIC,
    
    -- Logistics
    teu NUMERIC,
    vessel_name TEXT,
    container_id TEXT,
    port_loading TEXT,
    port_unloading TEXT,
    
    -- Metadata
    record_grain TEXT,
    source_format TEXT,
    source_file TEXT,
    direction TEXT,
    
    standardized_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Validation session tracking
    validation_session_id UUID
);

CREATE INDEX IF NOT EXISTS idx_tmp_std_session ON tmp_stg_shipments_standardized(validation_session_id);
CREATE INDEX IF NOT EXISTS idx_tmp_std_country ON tmp_stg_shipments_standardized(reporting_country, direction);

COMMENT ON TABLE tmp_stg_shipments_raw IS 
    'Sandbox table for validation - NOT connected to production pipeline';

COMMENT ON TABLE tmp_stg_shipments_standardized IS 
    'Sandbox table for validation - NOT connected to production pipeline';

-- =====================================================================
-- MIGRATION COMPLETE
-- =====================================================================
