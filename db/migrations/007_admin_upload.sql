-- =====================================================================
-- EPIC 9 - Admin Upload Feature
-- Migration: 007_admin_upload.sql
-- =====================================================================
-- Adds new columns to file_registry for admin upload metadata
-- =====================================================================

-- STEP 1: Add new columns to file_registry
-- =====================================================================

-- Source format (FULL, SHORT, OTHER)
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS source_format TEXT;

-- Source provider (e.g., Eximpedia, Customs Portal)
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS source_provider TEXT;

-- Data grain (SHIPMENT_LINE, CONTAINER, INVOICE, UNKNOWN)
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS data_grain TEXT;

-- Is production data flag
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS is_production BOOLEAN DEFAULT true;

-- Data quality level (RAW, CLEANED_BASIC, CLEANED_AAZIKO, UNKNOWN)
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS data_quality_level TEXT DEFAULT 'RAW';

-- Tags (comma-separated)
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS tags TEXT;

-- Notes (free text)
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS notes TEXT;

-- Header row index (1-indexed, default 1)
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS header_row_index INTEGER DEFAULT 1;

-- Sheet name for Excel files
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS sheet_name TEXT;

-- Processing mode used during upload
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS processing_mode TEXT;

-- Config file used for validation
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS config_file_used TEXT;

-- Upload source (e.g., 'admin_upload', 'cron', 'manual')
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS upload_source TEXT DEFAULT 'manual';

-- Uploaded by user (for future auth integration)
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS uploaded_by TEXT;

-- Analytics pipeline timestamps
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS profiles_started_at TIMESTAMPTZ;
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS profiles_completed_at TIMESTAMPTZ;
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS lanes_started_at TIMESTAMPTZ;
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS lanes_completed_at TIMESTAMPTZ;
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS risk_started_at TIMESTAMPTZ;
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS risk_completed_at TIMESTAMPTZ;
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS serving_started_at TIMESTAMPTZ;
ALTER TABLE file_registry ADD COLUMN IF NOT EXISTS serving_completed_at TIMESTAMPTZ;

-- STEP 2: Add constraints
-- =====================================================================

-- Constraint for data_grain values
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_fr_data_grain'
    ) THEN
        ALTER TABLE file_registry ADD CONSTRAINT chk_fr_data_grain 
            CHECK (data_grain IS NULL OR data_grain IN ('SHIPMENT_LINE', 'CONTAINER', 'INVOICE', 'UNKNOWN'));
    END IF;
END $$;

-- Constraint for data_quality_level values
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_fr_data_quality'
    ) THEN
        ALTER TABLE file_registry ADD CONSTRAINT chk_fr_data_quality 
            CHECK (data_quality_level IS NULL OR data_quality_level IN ('RAW', 'CLEANED_BASIC', 'CLEANED_AAZIKO', 'UNKNOWN'));
    END IF;
END $$;

-- Constraint for processing_mode values
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_fr_processing_mode'
    ) THEN
        ALTER TABLE file_registry ADD CONSTRAINT chk_fr_processing_mode 
            CHECK (processing_mode IS NULL OR processing_mode IN ('INGEST_ONLY', 'INGEST_AND_STANDARDIZE', 'FULL_PIPELINE'));
    END IF;
END $$;

-- STEP 3: Add indexes
-- =====================================================================

CREATE INDEX IF NOT EXISTS idx_fr_upload_source ON file_registry(upload_source);
CREATE INDEX IF NOT EXISTS idx_fr_is_production ON file_registry(is_production);
CREATE INDEX IF NOT EXISTS idx_fr_created_at ON file_registry(created_at DESC);

-- STEP 4: Update pipeline_runs constraint to include admin_upload pipelines
-- =====================================================================

-- Drop and recreate the constraint to include new pipeline names
ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS chk_pipeline_name;

ALTER TABLE pipeline_runs ADD CONSTRAINT chk_pipeline_name 
    CHECK (pipeline_name IN (
        'ingestion', 'standardization', 'identity', 'ledger',
        'mirror_algorithm', 'build_profiles', 'build_price_and_lanes', 
        'risk_engine', 'serving_views',
        'admin_upload_ingest_only', 'admin_upload_ingest_and_standardize', 'admin_upload_full_pipeline'
    ));

-- =====================================================================
-- MIGRATION COMPLETE
-- =====================================================================
