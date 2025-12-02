-- =====================================================================
-- Migration 004: EPIC 6B - Price Corridor & Lane Stats Schema Updates
-- GTI-OS Data Platform
-- Date: 2025-11-30
-- =====================================================================
-- This migration restructures price_corridor and lane_stats tables
-- to support the new grain and columns specified in EPIC 6B.
-- 
-- New grains:
--   price_corridor: (hs_code_6, destination_country, year, month, direction, reporting_country)
--   lane_stats: (origin_country, destination_country, hs_code_6)
-- =====================================================================

-- =====================================================================
-- STEP 1: DROP AND RECREATE PRICE_CORRIDOR
-- =====================================================================

-- Drop existing table (likely empty or needs restructure)
DROP TABLE IF EXISTS price_corridor CASCADE;

CREATE TABLE price_corridor (
    corridor_id BIGSERIAL PRIMARY KEY,
    
    -- Grain columns
    hs_code_6 TEXT NOT NULL,
    destination_country TEXT NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    direction TEXT NOT NULL,              -- 'IMPORT' or 'EXPORT'
    reporting_country TEXT NOT NULL,
    
    -- Sample metadata
    sample_size BIGINT DEFAULT 0,         -- COUNT(*) of shipments with valid price
    
    -- Price statistics (USD per kg)
    min_price_usd_per_kg NUMERIC,
    p25_price_usd_per_kg NUMERIC,
    median_price_usd_per_kg NUMERIC,
    p75_price_usd_per_kg NUMERIC,
    max_price_usd_per_kg NUMERIC,
    avg_price_usd_per_kg NUMERIC,
    
    -- Metadata
    last_ledger_shipment_date DATE,       -- max(shipment_date) in this bucket
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint on grain
    CONSTRAINT unique_price_corridor_grain 
        UNIQUE (hs_code_6, destination_country, year, month, direction, reporting_country),
    
    -- Validation
    CONSTRAINT chk_pc_direction CHECK (direction IN ('IMPORT', 'EXPORT')),
    CONSTRAINT chk_pc_year CHECK (year >= 2000 AND year <= 2100),
    CONSTRAINT chk_pc_month CHECK (month >= 1 AND month <= 12)
);

-- Performance indexes
CREATE INDEX idx_pc_hs6 ON price_corridor(hs_code_6);
CREATE INDEX idx_pc_dest_country ON price_corridor(destination_country);
CREATE INDEX idx_pc_reporting ON price_corridor(reporting_country);
CREATE INDEX idx_pc_period ON price_corridor(year, month);
CREATE INDEX idx_pc_direction ON price_corridor(direction);
CREATE INDEX idx_pc_updated ON price_corridor(updated_at);

-- =====================================================================
-- STEP 2: DROP AND RECREATE LANE_STATS
-- =====================================================================

-- Drop existing table (different grain - port-based vs country-based)
DROP TABLE IF EXISTS lane_stats CASCADE;

CREATE TABLE lane_stats (
    lane_id BIGSERIAL PRIMARY KEY,
    
    -- Grain columns (country-based, not port-based)
    origin_country TEXT NOT NULL,
    destination_country TEXT NOT NULL,
    hs_code_6 TEXT NOT NULL,
    
    -- Volume metrics
    total_shipments BIGINT DEFAULT 0,
    total_teu NUMERIC DEFAULT 0,
    total_customs_value_usd NUMERIC DEFAULT 0,
    total_qty_kg NUMERIC DEFAULT 0,
    avg_price_usd_per_kg NUMERIC,
    
    -- Date range
    first_shipment_date DATE,
    last_shipment_date DATE,
    
    -- Carrier information (vessel_name as surrogate)
    top_carriers JSONB DEFAULT '[]'::jsonb,   -- [{carrier_name, shipments, total_teu, total_value_usd}]
    
    -- Metadata
    reporting_countries JSONB DEFAULT '[]'::jsonb,  -- array of contributing reporting_country values
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint on grain
    CONSTRAINT unique_lane_stats_grain 
        UNIQUE (origin_country, destination_country, hs_code_6)
);

-- Performance indexes
CREATE INDEX idx_ls_origin ON lane_stats(origin_country);
CREATE INDEX idx_ls_dest ON lane_stats(destination_country);
CREATE INDEX idx_ls_hs6 ON lane_stats(hs_code_6);
CREATE INDEX idx_ls_total_value ON lane_stats(total_customs_value_usd DESC);
CREATE INDEX idx_ls_updated ON lane_stats(updated_at);

-- =====================================================================
-- STEP 3: CREATE ANALYTICS WATERMARKS TABLE
-- =====================================================================

CREATE TABLE IF NOT EXISTS analytics_watermarks (
    analytics_name TEXT PRIMARY KEY,
    max_shipment_date DATE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Initialize watermarks for price_corridor and lane_stats
INSERT INTO analytics_watermarks (analytics_name, max_shipment_date)
VALUES 
    ('price_corridor', NULL),
    ('lane_stats', NULL)
ON CONFLICT (analytics_name) DO NOTHING;

-- =====================================================================
-- STEP 4: UPDATE PIPELINE_RUNS CONSTRAINT
-- =====================================================================

-- Update the check constraint to allow 'build_price_and_lanes' pipeline
ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS chk_pipeline_name;
ALTER TABLE pipeline_runs ADD CONSTRAINT chk_pipeline_name 
    CHECK (pipeline_name IN (
        'ingestion', 'standardization', 'identity', 'ledger', 
        'mirror_algorithm', 'build_profiles', 'build_price_and_lanes'
    ));

-- =====================================================================
-- VERIFICATION
-- =====================================================================

DO $$
BEGIN
    RAISE NOTICE 'EPIC 6B Migration complete:';
    RAISE NOTICE '  - price_corridor table recreated with new grain';
    RAISE NOTICE '  - lane_stats table recreated with country-based grain';
    RAISE NOTICE '  - analytics_watermarks helper table created';
    RAISE NOTICE '  - pipeline_runs constraint updated for build_price_and_lanes';
END $$;
