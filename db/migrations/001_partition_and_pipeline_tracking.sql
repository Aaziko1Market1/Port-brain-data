-- =====================================================================
-- Migration 001: Partition global_trades_ledger + Pipeline Tracking
-- GTI-OS Data Platform - Architecture Hardening for Scale
-- Date: 2025-11-30
-- =====================================================================
-- This migration:
--   1. Partitions global_trades_ledger by YEAR for 47+ countries / 100M+ rows
--   2. Adds file-level processing markers to file_registry
--   3. Creates pipeline_runs table for Control Tower visibility
-- =====================================================================

-- =====================================================================
-- STEP A: BACKUP EXISTING DATA
-- =====================================================================
-- Create backup table (preserves all existing data)
CREATE TABLE IF NOT EXISTS global_trades_ledger_backup AS
SELECT * FROM global_trades_ledger;

-- Log backup count
DO $$
DECLARE
    backup_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO backup_count FROM global_trades_ledger_backup;
    RAISE NOTICE 'Backup complete: % rows saved to global_trades_ledger_backup', backup_count;
END $$;

-- =====================================================================
-- STEP B: DROP OLD TABLE (CASCADE for dependent objects)
-- =====================================================================
-- Drop dependent view first to be explicit
DROP VIEW IF EXISTS vw_global_shipments_for_llm CASCADE;

-- Drop the non-partitioned table
DROP TABLE IF EXISTS global_trades_ledger CASCADE;

-- =====================================================================
-- STEP C: CREATE PARTITIONED PARENT TABLE
-- =====================================================================
CREATE TABLE global_trades_ledger (
    transaction_id UUID NOT NULL,
    std_id BIGINT NOT NULL,
    reporting_country TEXT NOT NULL,
    direction TEXT NOT NULL,
    origin_country TEXT NOT NULL,
    destination_country TEXT NOT NULL,
    export_date DATE,
    import_date DATE,
    shipment_date DATE NOT NULL,
    year INT NOT NULL,
    month INT,
    buyer_uuid UUID,
    supplier_uuid UUID,
    hs_code_raw TEXT,
    hs_code_6 TEXT NOT NULL,
    goods_description TEXT,
    qty_raw NUMERIC,
    qty_kg NUMERIC,
    qty_unit TEXT,
    fob_usd NUMERIC,
    cif_usd NUMERIC,
    customs_value_usd NUMERIC,
    price_usd_per_kg NUMERIC,
    teu NUMERIC,
    vessel_name TEXT,
    container_id TEXT,
    port_loading TEXT,
    port_unloading TEXT,
    record_grain TEXT,
    source_format TEXT,
    source_file TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Composite primary key required for partitioning
    PRIMARY KEY (transaction_id, year),
    
    -- Constraints
    CONSTRAINT chk_gtl_year_valid CHECK (year >= 2000 AND year <= 2100),
    CONSTRAINT chk_gtl_month_valid CHECK (month >= 1 AND month <= 12),
    CONSTRAINT chk_gtl_direction CHECK (direction IN ('EXPORT', 'IMPORT'))
) PARTITION BY RANGE (year);

-- =====================================================================
-- STEP D: CREATE YEAR PARTITIONS (2020-2030 range)
-- =====================================================================
-- Historical years (in case of old data)
CREATE TABLE global_trades_ledger_2020 PARTITION OF global_trades_ledger
    FOR VALUES FROM (2020) TO (2021);

CREATE TABLE global_trades_ledger_2021 PARTITION OF global_trades_ledger
    FOR VALUES FROM (2021) TO (2022);

CREATE TABLE global_trades_ledger_2022 PARTITION OF global_trades_ledger
    FOR VALUES FROM (2022) TO (2023);

-- Current data years
CREATE TABLE global_trades_ledger_2023 PARTITION OF global_trades_ledger
    FOR VALUES FROM (2023) TO (2024);

CREATE TABLE global_trades_ledger_2024 PARTITION OF global_trades_ledger
    FOR VALUES FROM (2024) TO (2025);

CREATE TABLE global_trades_ledger_2025 PARTITION OF global_trades_ledger
    FOR VALUES FROM (2025) TO (2026);

-- Future years
CREATE TABLE global_trades_ledger_2026 PARTITION OF global_trades_ledger
    FOR VALUES FROM (2026) TO (2027);

CREATE TABLE global_trades_ledger_2027 PARTITION OF global_trades_ledger
    FOR VALUES FROM (2027) TO (2028);

CREATE TABLE global_trades_ledger_2028 PARTITION OF global_trades_ledger
    FOR VALUES FROM (2028) TO (2029);

CREATE TABLE global_trades_ledger_2029 PARTITION OF global_trades_ledger
    FOR VALUES FROM (2029) TO (2030);

CREATE TABLE global_trades_ledger_2030 PARTITION OF global_trades_ledger
    FOR VALUES FROM (2030) TO (2031);

-- =====================================================================
-- STEP E: CREATE INDEXES ON PARENT (Postgres propagates to partitions)
-- =====================================================================
-- Unique index on std_id for idempotency (critical for EPIC 4)
CREATE UNIQUE INDEX idx_gtl_std_id ON global_trades_ledger(std_id);

-- Entity indexes
CREATE INDEX idx_gtl_buyer ON global_trades_ledger(buyer_uuid);
CREATE INDEX idx_gtl_supplier ON global_trades_ledger(supplier_uuid);

-- Geographic and temporal indexes
CREATE INDEX idx_gtl_hs_dest_year ON global_trades_ledger(hs_code_6, destination_country, year);
CREATE INDEX idx_gtl_origin_dest_date ON global_trades_ledger(origin_country, destination_country, shipment_date);
CREATE INDEX idx_gtl_reporting_country ON global_trades_ledger(reporting_country);
CREATE INDEX idx_gtl_direction ON global_trades_ledger(direction);
CREATE INDEX idx_gtl_year_month ON global_trades_ledger(year, month);
CREATE INDEX idx_gtl_shipment_date ON global_trades_ledger(shipment_date);
CREATE INDEX idx_gtl_hs6 ON global_trades_ledger(hs_code_6);

-- Composite indexes for common query patterns
CREATE INDEX idx_gtl_country_dir_year ON global_trades_ledger(reporting_country, direction, year);
CREATE INDEX idx_gtl_buyer_hs6 ON global_trades_ledger(buyer_uuid, hs_code_6) WHERE buyer_uuid IS NOT NULL;
CREATE INDEX idx_gtl_supplier_hs6 ON global_trades_ledger(supplier_uuid, hs_code_6) WHERE supplier_uuid IS NOT NULL;

-- =====================================================================
-- STEP F: RELOAD DATA FROM BACKUP
-- =====================================================================
INSERT INTO global_trades_ledger (
    transaction_id, std_id, reporting_country, direction, origin_country,
    destination_country, export_date, import_date, shipment_date, year, month,
    buyer_uuid, supplier_uuid, hs_code_raw, hs_code_6, goods_description,
    qty_raw, qty_kg, qty_unit, fob_usd, cif_usd, customs_value_usd,
    price_usd_per_kg, teu, vessel_name, container_id, port_loading,
    port_unloading, record_grain, source_format, source_file, created_at
)
SELECT
    transaction_id, std_id, reporting_country, direction, origin_country,
    destination_country, export_date, import_date, shipment_date, year, month,
    buyer_uuid, supplier_uuid, hs_code_raw, hs_code_6, goods_description,
    qty_raw, qty_kg, qty_unit, fob_usd, cif_usd, customs_value_usd,
    price_usd_per_kg, teu, vessel_name, container_id, port_loading,
    port_unloading, record_grain, source_format, source_file, created_at
FROM global_trades_ledger_backup;

-- Verify row count
DO $$
DECLARE
    new_count INTEGER;
    backup_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO new_count FROM global_trades_ledger;
    SELECT COUNT(*) INTO backup_count FROM global_trades_ledger_backup;
    
    IF new_count = backup_count THEN
        RAISE NOTICE 'Migration successful: % rows migrated to partitioned table', new_count;
    ELSE
        RAISE EXCEPTION 'Migration failed: backup has % rows but new table has % rows', backup_count, new_count;
    END IF;
END $$;

-- =====================================================================
-- STEP G: RECREATE DEPENDENT VIEW
-- =====================================================================
CREATE OR REPLACE VIEW vw_global_shipments_for_llm AS
SELECT 
    t.transaction_id,
    t.shipment_date,
    t.year,
    t.month,
    t.origin_country,
    t.destination_country,
    b.name_normalized AS buyer_name,
    s.name_normalized AS supplier_name,
    t.hs_code_6,
    t.goods_description,
    t.qty_kg,
    t.fob_usd,
    t.cif_usd,
    t.price_usd_per_kg,
    t.vessel_name,
    t.port_loading,
    t.port_unloading
FROM global_trades_ledger t
LEFT JOIN organizations_master b ON t.buyer_uuid = b.org_uuid
LEFT JOIN organizations_master s ON t.supplier_uuid = s.org_uuid;

-- Re-grant permissions
GRANT SELECT ON vw_global_shipments_for_llm TO llm_readonly;

-- =====================================================================
-- PART 2: FILE-LEVEL PROCESSING MARKERS
-- =====================================================================
-- Add lifecycle columns to file_registry for incremental processing

-- Add columns if they don't exist (idempotent)
DO $$
BEGIN
    -- ingestion_completed_at
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'file_registry' AND column_name = 'ingestion_completed_at'
    ) THEN
        ALTER TABLE file_registry ADD COLUMN ingestion_completed_at TIMESTAMPTZ;
    END IF;
    
    -- standardization columns
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'file_registry' AND column_name = 'standardization_started_at'
    ) THEN
        ALTER TABLE file_registry ADD COLUMN standardization_started_at TIMESTAMPTZ;
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'file_registry' AND column_name = 'standardization_completed_at'
    ) THEN
        ALTER TABLE file_registry ADD COLUMN standardization_completed_at TIMESTAMPTZ;
    END IF;
    
    -- identity columns
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'file_registry' AND column_name = 'identity_started_at'
    ) THEN
        ALTER TABLE file_registry ADD COLUMN identity_started_at TIMESTAMPTZ;
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'file_registry' AND column_name = 'identity_completed_at'
    ) THEN
        ALTER TABLE file_registry ADD COLUMN identity_completed_at TIMESTAMPTZ;
    END IF;
    
    -- ledger columns
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'file_registry' AND column_name = 'ledger_started_at'
    ) THEN
        ALTER TABLE file_registry ADD COLUMN ledger_started_at TIMESTAMPTZ;
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'file_registry' AND column_name = 'ledger_completed_at'
    ) THEN
        ALTER TABLE file_registry ADD COLUMN ledger_completed_at TIMESTAMPTZ;
    END IF;
END $$;

-- Create partial indexes for efficient pending-file queries
DROP INDEX IF EXISTS idx_fr_std_pending;
CREATE INDEX idx_fr_std_pending
    ON file_registry(reporting_country, direction)
    WHERE status = 'INGESTED' AND standardization_completed_at IS NULL;

DROP INDEX IF EXISTS idx_fr_identity_pending;
CREATE INDEX idx_fr_identity_pending
    ON file_registry(reporting_country, direction)
    WHERE status = 'INGESTED' AND identity_completed_at IS NULL;

DROP INDEX IF EXISTS idx_fr_ledger_pending;
CREATE INDEX idx_fr_ledger_pending
    ON file_registry(reporting_country, direction)
    WHERE status = 'INGESTED' AND ledger_completed_at IS NULL;

-- Backfill: mark existing ingested files as fully processed
-- (since current data has already gone through all EPICs)
UPDATE file_registry
SET 
    ingestion_completed_at = COALESCE(ingested_at, updated_at, created_at),
    standardization_started_at = COALESCE(ingested_at, updated_at, created_at),
    standardization_completed_at = COALESCE(ingested_at, updated_at, created_at),
    identity_started_at = COALESCE(ingested_at, updated_at, created_at),
    identity_completed_at = COALESCE(ingested_at, updated_at, created_at),
    ledger_started_at = COALESCE(ingested_at, updated_at, created_at),
    ledger_completed_at = COALESCE(ingested_at, updated_at, created_at)
WHERE status = 'INGESTED'
  AND ingestion_completed_at IS NULL;

-- =====================================================================
-- PART 3: PIPELINE RUNS TRACKING TABLE
-- =====================================================================
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_name TEXT NOT NULL,              -- 'ingestion', 'standardization', 'identity', 'ledger'
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'RUNNING',   -- 'RUNNING', 'SUCCESS', 'FAILED', 'PARTIAL'
    countries_filter TEXT[],                  -- e.g. ARRAY['INDIA','KENYA']
    countries_filter_str TEXT,                -- e.g. 'INDIA,KENYA' (for easier querying)
    directions_filter TEXT[],                 -- e.g. ARRAY['EXPORT','IMPORT']
    rows_processed INT DEFAULT 0,
    rows_created INT DEFAULT 0,
    rows_updated INT DEFAULT 0,
    rows_skipped INT DEFAULT 0,
    files_processed INT DEFAULT 0,
    error_message TEXT,
    metadata JSONB,
    
    CONSTRAINT chk_pipeline_name CHECK (pipeline_name IN ('ingestion', 'standardization', 'identity', 'ledger')),
    CONSTRAINT chk_pipeline_status CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED', 'PARTIAL'))
);

-- Indexes for Control Tower queries
CREATE INDEX IF NOT EXISTS idx_pr_pipeline_started ON pipeline_runs(pipeline_name, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_pr_status_running ON pipeline_runs(status) WHERE status = 'RUNNING';
CREATE INDEX IF NOT EXISTS idx_pr_status ON pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_pr_started_at ON pipeline_runs(started_at DESC);

-- =====================================================================
-- VERIFICATION QUERIES
-- =====================================================================

-- Check partition setup
DO $$
DECLARE
    partition_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO partition_count
    FROM pg_tables
    WHERE tablename LIKE 'global_trades_ledger_20%';
    
    RAISE NOTICE 'Partitions created: %', partition_count;
END $$;

-- Check file_registry columns
DO $$
DECLARE
    col_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE table_name = 'file_registry'
      AND column_name IN (
          'ingestion_completed_at', 
          'standardization_started_at', 'standardization_completed_at',
          'identity_started_at', 'identity_completed_at',
          'ledger_started_at', 'ledger_completed_at'
      );
    
    RAISE NOTICE 'File registry lifecycle columns: % (expected 7)', col_count;
END $$;

-- Check pipeline_runs table
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pipeline_runs') THEN
        RAISE NOTICE 'pipeline_runs table created successfully';
    ELSE
        RAISE EXCEPTION 'pipeline_runs table not found';
    END IF;
END $$;

-- =====================================================================
-- MIGRATION COMPLETE
-- =====================================================================
-- Note: global_trades_ledger_backup is retained for safety
-- Run this to drop after verifying: DROP TABLE global_trades_ledger_backup;
