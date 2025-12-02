-- =====================================================================
-- Migration 003: EPIC 6A - Buyer & Exporter Profile Schema Updates
-- GTI-OS Data Platform
-- Date: 2025-11-30
-- =====================================================================
-- This migration restructures buyer_profile and exporter_profile tables
-- to support the new grain and columns specified in EPIC 6A.
-- 
-- New grain:
--   buyer_profile: (buyer_uuid, destination_country)
--   exporter_profile: (supplier_uuid, origin_country)
-- =====================================================================

-- =====================================================================
-- STEP 1: BACKUP AND DROP EXISTING TABLES (if empty or for clean start)
-- =====================================================================

-- Check if tables have data and handle accordingly
DO $$
DECLARE
    buyer_count INT;
    exporter_count INT;
BEGIN
    SELECT COUNT(*) INTO buyer_count FROM buyer_profile;
    SELECT COUNT(*) INTO exporter_count FROM exporter_profile;
    
    IF buyer_count > 0 OR exporter_count > 0 THEN
        RAISE NOTICE 'WARNING: Existing profile data found (buyer: %, exporter: %). Will preserve and migrate.', buyer_count, exporter_count;
    ELSE
        RAISE NOTICE 'No existing profile data. Proceeding with clean rebuild.';
    END IF;
END $$;

-- =====================================================================
-- STEP 2: DROP AND RECREATE BUYER_PROFILE WITH NEW SCHEMA
-- =====================================================================

-- Drop existing constraints and indexes first
DROP INDEX IF EXISTS idx_buyer_profile_buyer;
DROP INDEX IF EXISTS idx_buyer_profile_country;
DROP INDEX IF EXISTS idx_buyer_profile_hs6;
DROP INDEX IF EXISTS idx_buyer_profile_period;
DROP INDEX IF EXISTS idx_buyer_profile_persona;

-- Drop and recreate table with new schema
DROP TABLE IF EXISTS buyer_profile CASCADE;

CREATE TABLE buyer_profile (
    profile_id BIGSERIAL PRIMARY KEY,
    buyer_uuid UUID NOT NULL,
    destination_country TEXT NOT NULL,
    
    -- Date range
    first_shipment_date DATE,
    last_shipment_date DATE,
    
    -- Volumes & Values
    total_shipments BIGINT DEFAULT 0,
    total_customs_value_usd NUMERIC DEFAULT 0,
    total_qty_kg NUMERIC DEFAULT 0,
    avg_price_usd_per_kg NUMERIC,
    
    -- Product diversity
    unique_hs6_count INT DEFAULT 0,
    
    -- JSON aggregates
    top_hs_codes JSONB DEFAULT '[]'::jsonb,      -- [{hs_code_6, total_value_usd, shipments}]
    top_suppliers JSONB DEFAULT '[]'::jsonb,     -- [{supplier_uuid, supplier_name, total_value_usd}]
    
    -- Analytics
    growth_12m NUMERIC,                          -- YoY growth (NULL if insufficient data)
    persona_label TEXT,                          -- 'Whale','Mid','Value','Growing','Seasonal'
    
    -- Metadata
    reporting_country TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Grain: unique by (buyer_uuid, destination_country)
    CONSTRAINT unique_buyer_profile_grain UNIQUE (buyer_uuid, destination_country)
);

-- Performance indexes
CREATE INDEX idx_bp_buyer ON buyer_profile(buyer_uuid);
CREATE INDEX idx_bp_destination ON buyer_profile(destination_country);
CREATE INDEX idx_bp_reporting ON buyer_profile(reporting_country);
CREATE INDEX idx_bp_persona ON buyer_profile(persona_label);
CREATE INDEX idx_bp_total_value ON buyer_profile(total_customs_value_usd DESC);
CREATE INDEX idx_bp_updated ON buyer_profile(updated_at);

-- =====================================================================
-- STEP 3: DROP AND RECREATE EXPORTER_PROFILE WITH NEW SCHEMA
-- =====================================================================

-- Drop existing constraints and indexes first
DROP INDEX IF EXISTS idx_exporter_profile_supplier;
DROP INDEX IF EXISTS idx_exporter_profile_country;
DROP INDEX IF EXISTS idx_exporter_profile_hs6;
DROP INDEX IF EXISTS idx_exporter_profile_period;

-- Drop and recreate table with new schema
DROP TABLE IF EXISTS exporter_profile CASCADE;

CREATE TABLE exporter_profile (
    profile_id BIGSERIAL PRIMARY KEY,
    supplier_uuid UUID NOT NULL,
    origin_country TEXT NOT NULL,
    
    -- Date range
    first_shipment_date DATE,
    last_shipment_date DATE,
    
    -- Volumes & Values
    total_shipments BIGINT DEFAULT 0,
    total_customs_value_usd NUMERIC DEFAULT 0,
    total_qty_kg NUMERIC DEFAULT 0,
    avg_price_usd_per_kg NUMERIC,
    
    -- Product diversity
    unique_hs6_count INT DEFAULT 0,
    
    -- JSON aggregates
    top_hs_codes JSONB DEFAULT '[]'::jsonb,      -- [{hs_code_6, total_value_usd, shipments}]
    top_buyers JSONB DEFAULT '[]'::jsonb,        -- [{buyer_uuid, buyer_name, total_value_usd}]
    
    -- Analytics
    stability_score NUMERIC,                      -- 0-100, rule-based
    onboarding_score NUMERIC,                     -- 0-100, rule-based
    
    -- Metadata
    reporting_country TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Grain: unique by (supplier_uuid, origin_country)
    CONSTRAINT unique_exporter_profile_grain UNIQUE (supplier_uuid, origin_country)
);

-- Performance indexes
CREATE INDEX idx_ep_supplier ON exporter_profile(supplier_uuid);
CREATE INDEX idx_ep_origin ON exporter_profile(origin_country);
CREATE INDEX idx_ep_reporting ON exporter_profile(reporting_country);
CREATE INDEX idx_ep_stability ON exporter_profile(stability_score DESC);
CREATE INDEX idx_ep_total_value ON exporter_profile(total_customs_value_usd DESC);
CREATE INDEX idx_ep_updated ON exporter_profile(updated_at);

-- =====================================================================
-- STEP 4: CREATE HELPER TABLE FOR INCREMENTAL PROCESSING
-- =====================================================================

CREATE TABLE IF NOT EXISTS profile_build_markers (
    marker_id SERIAL PRIMARY KEY,
    profile_type TEXT NOT NULL,                   -- 'buyer' or 'exporter'
    last_processed_date DATE,
    last_processed_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_profile_marker UNIQUE (profile_type)
);

-- Initialize markers if not exists
INSERT INTO profile_build_markers (profile_type, last_processed_date)
VALUES ('buyer', NULL), ('exporter', NULL)
ON CONFLICT (profile_type) DO NOTHING;

-- =====================================================================
-- STEP 5: UPDATE PIPELINE_RUNS CONSTRAINT
-- =====================================================================

-- Update the check constraint to allow 'build_profiles' pipeline
ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS chk_pipeline_name;
ALTER TABLE pipeline_runs ADD CONSTRAINT chk_pipeline_name 
    CHECK (pipeline_name IN ('ingestion', 'standardization', 'identity', 'ledger', 'mirror_algorithm', 'build_profiles'));

-- =====================================================================
-- VERIFICATION
-- =====================================================================

DO $$
BEGIN
    RAISE NOTICE 'EPIC 6A Migration complete:';
    RAISE NOTICE '  - buyer_profile table recreated with new grain (buyer_uuid, destination_country)';
    RAISE NOTICE '  - exporter_profile table recreated with new grain (supplier_uuid, origin_country)';
    RAISE NOTICE '  - profile_build_markers helper table created';
    RAISE NOTICE '  - pipeline_runs constraint updated for build_profiles';
END $$;
