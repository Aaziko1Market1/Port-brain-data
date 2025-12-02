-- =====================================================================
-- Migration 002: EPIC 5 - Mirror Algorithm Schema Updates
-- GTI-OS Data Platform
-- Date: 2025-11-30
-- =====================================================================
-- This migration:
--   1. Adds unique constraint on mirror_match_log(export_transaction_id)
--   2. Adds export_year/import_year for partitioned table compatibility
--   3. Adds indexes for mirror algorithm performance
-- =====================================================================

-- Ensure unique constraint exists (idempotent)
-- Only one mirror match per export is allowed
DROP INDEX IF EXISTS idx_mirror_export_unique;
CREATE UNIQUE INDEX idx_mirror_export_unique
    ON mirror_match_log(export_transaction_id);

-- Add export_year and import_year columns if they don't exist
-- These are needed to join back to partitioned global_trades_ledger
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'mirror_match_log' AND column_name = 'export_year'
    ) THEN
        ALTER TABLE mirror_match_log ADD COLUMN export_year INT;
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'mirror_match_log' AND column_name = 'import_year'
    ) THEN
        ALTER TABLE mirror_match_log ADD COLUMN import_year INT;
    END IF;
END $$;

-- Add index for efficient lookups by export/import year
CREATE INDEX IF NOT EXISTS idx_mirror_export_year ON mirror_match_log(export_year);
CREATE INDEX IF NOT EXISTS idx_mirror_import_year ON mirror_match_log(import_year);

-- Add index on global_trades_ledger for mirror candidate lookup
-- These help with the HS6 + origin + destination + date range queries
CREATE INDEX IF NOT EXISTS idx_gtl_mirror_candidate 
    ON global_trades_ledger(hs_code_6, origin_country, destination_country, shipment_date)
    WHERE direction = 'IMPORT';

CREATE INDEX IF NOT EXISTS idx_gtl_mirror_export
    ON global_trades_ledger(hs_code_6, origin_country, destination_country, shipment_date)
    WHERE direction = 'EXPORT';

-- Add hidden_buyer_flag to stg_shipments_standardized for easier querying
-- This is a computed flag based on buyer_name patterns
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'stg_shipments_standardized' AND column_name = 'hidden_buyer_flag'
    ) THEN
        ALTER TABLE stg_shipments_standardized ADD COLUMN hidden_buyer_flag BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- Update hidden_buyer_flag for existing rows
UPDATE stg_shipments_standardized
SET hidden_buyer_flag = TRUE
WHERE hidden_buyer_flag IS NOT TRUE
  AND (
      buyer_name_raw IS NULL 
      OR TRIM(buyer_name_raw) = ''
      OR UPPER(buyer_name_raw) LIKE '%TO THE ORDER%'
      OR UPPER(buyer_name_raw) LIKE '%TO ORDER%'
      OR UPPER(buyer_name_raw) LIKE '%BANK%'
      OR UPPER(buyer_name_raw) LIKE '%L/C%'
      OR UPPER(buyer_name_raw) LIKE '%LETTER OF CREDIT%'
  );

-- Create index for hidden buyer lookups
CREATE INDEX IF NOT EXISTS idx_std_hidden_buyer 
    ON stg_shipments_standardized(std_id) 
    WHERE hidden_buyer_flag = TRUE;

-- Add mirror_matched_at column to global_trades_ledger for tracking
-- This helps identify which exports were updated by mirror algorithm
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'global_trades_ledger' AND column_name = 'mirror_matched_at'
    ) THEN
        -- Note: For partitioned tables, we need to add to all partitions
        -- The ALTER TABLE on parent propagates to partitions in Postgres 11+
        ALTER TABLE global_trades_ledger ADD COLUMN mirror_matched_at TIMESTAMPTZ;
    END IF;
END $$;

-- Verification
DO $$
DECLARE
    hidden_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO hidden_count
    FROM stg_shipments_standardized
    WHERE hidden_buyer_flag = TRUE;
    
    RAISE NOTICE 'EPIC 5 Migration complete. Hidden buyer rows flagged: %', hidden_count;
END $$;
