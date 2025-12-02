-- =====================================================================
-- Migration 005: EPIC 6C - Global Risk Engine Schema
-- GTI-OS Data Platform
-- Date: 2025-11-30
-- =====================================================================
-- This migration creates the risk engine sidecar tables:
--   risk_scores: Current risk opinions (sidecar to facts)
--   risk_scores_history: Historical risk score evolution
--   risk_engine_watermark: Incremental processing tracking
--
-- Key principles:
--   - Risk is an OPINION layer, facts (global_trades_ledger) are IMMUTABLE
--   - Unique constraint on (entity_type, entity_id, scope_key, engine_version)
--   - Full audit trail via history table
-- =====================================================================

-- =====================================================================
-- STEP 1: DROP AND RECREATE RISK_SCORES
-- =====================================================================

-- Drop existing table (schema is different from spec)
DROP TABLE IF EXISTS risk_scores CASCADE;

CREATE TABLE risk_scores (
    risk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What is being scored
    entity_type TEXT NOT NULL,        -- 'SHIPMENT' | 'BUYER' (future: 'EXPORTER', etc.)
    entity_id UUID NOT NULL,          -- For SHIPMENT: transaction_id from global_trades_ledger
                                      -- For BUYER: buyer_uuid from organizations_master

    -- Scope / dimension of risk
    scope_key TEXT NOT NULL,          -- e.g. 'GLOBAL', 'COUNTRY:KENYA', 'HS6:610990'

    -- Engine versioning
    engine_version TEXT NOT NULL,     -- e.g. 'RISK_ENGINE_V1'

    -- Scores & confidence
    risk_score NUMERIC(5,2) NOT NULL, -- 0–100 (0 low, 100 highest risk)
    confidence_score NUMERIC(4,2) NOT NULL, -- 0.0–1.0 (statistical confidence)

    -- Status & details
    risk_level TEXT NOT NULL,         -- 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
    main_reason_code TEXT NOT NULL,   -- e.g. 'UNDER_INVOICE', 'GHOST_ENTITY'
    reasons JSONB NOT NULL,           -- structured details (see JSON schema)

    -- Audit
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_rs_entity_type CHECK (entity_type IN ('SHIPMENT', 'BUYER', 'EXPORTER')),
    CONSTRAINT chk_rs_risk_level CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    CONSTRAINT chk_rs_risk_score CHECK (risk_score >= 0 AND risk_score <= 100),
    CONSTRAINT chk_rs_confidence CHECK (confidence_score >= 0 AND confidence_score <= 1)
);

-- Unique index for idempotency (one score per entity/scope/version combination)
CREATE UNIQUE INDEX idx_risk_scores_entity_scope_version
ON risk_scores(entity_type, entity_id, scope_key, engine_version);

-- Performance indexes
CREATE INDEX idx_rs_entity_type ON risk_scores(entity_type);
CREATE INDEX idx_rs_entity_id ON risk_scores(entity_id);
CREATE INDEX idx_rs_risk_level ON risk_scores(risk_level);
CREATE INDEX idx_rs_risk_score ON risk_scores(risk_score DESC);
CREATE INDEX idx_rs_engine_version ON risk_scores(engine_version);
CREATE INDEX idx_rs_computed_at ON risk_scores(computed_at DESC);
CREATE INDEX idx_rs_main_reason ON risk_scores(main_reason_code);

-- =====================================================================
-- STEP 2: CREATE RISK_SCORES_HISTORY
-- =====================================================================

CREATE TABLE risk_scores_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_id UUID NOT NULL,            -- Original risk_id from risk_scores
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    scope_key TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    risk_score NUMERIC(5,2) NOT NULL,
    confidence_score NUMERIC(4,2) NOT NULL,
    risk_level TEXT NOT NULL,
    main_reason_code TEXT NOT NULL,
    reasons JSONB NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL,
    archived_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for history queries
CREATE INDEX idx_rsh_risk_id ON risk_scores_history(risk_id);
CREATE INDEX idx_rsh_entity ON risk_scores_history(entity_type, entity_id);
CREATE INDEX idx_rsh_computed_at ON risk_scores_history(computed_at DESC);
CREATE INDEX idx_rsh_archived_at ON risk_scores_history(archived_at DESC);

-- =====================================================================
-- STEP 3: CREATE RISK_ENGINE_WATERMARK
-- =====================================================================

CREATE TABLE IF NOT EXISTS risk_engine_watermark (
    id SMALLINT PRIMARY KEY DEFAULT 1,
    last_processed_shipment_date DATE,
    last_run_at TIMESTAMPTZ,
    engine_version TEXT,
    
    -- Ensure single row
    CONSTRAINT risk_engine_watermark_single_row CHECK (id = 1)
);

-- Initialize watermark
INSERT INTO risk_engine_watermark (id, last_processed_shipment_date, last_run_at, engine_version)
VALUES (1, NULL, NULL, NULL)
ON CONFLICT (id) DO NOTHING;

-- =====================================================================
-- STEP 4: CREATE TRIGGER FOR HISTORY ARCHIVING
-- =====================================================================

-- Function to archive old risk scores before update
CREATE OR REPLACE FUNCTION archive_risk_score_on_update()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert old record into history before update
    INSERT INTO risk_scores_history (
        risk_id, entity_type, entity_id, scope_key, engine_version,
        risk_score, confidence_score, risk_level, main_reason_code,
        reasons, computed_at
    ) VALUES (
        OLD.risk_id, OLD.entity_type, OLD.entity_id, OLD.scope_key, OLD.engine_version,
        OLD.risk_score, OLD.confidence_score, OLD.risk_level, OLD.main_reason_code,
        OLD.reasons, OLD.computed_at
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trg_archive_risk_score ON risk_scores;
CREATE TRIGGER trg_archive_risk_score
BEFORE UPDATE ON risk_scores
FOR EACH ROW
EXECUTE FUNCTION archive_risk_score_on_update();

-- =====================================================================
-- STEP 5: UPDATE PIPELINE_RUNS CONSTRAINT
-- =====================================================================

-- Update the check constraint to allow 'risk_engine' pipeline
ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS chk_pipeline_name;
ALTER TABLE pipeline_runs ADD CONSTRAINT chk_pipeline_name 
    CHECK (pipeline_name IN (
        'ingestion', 'standardization', 'identity', 'ledger', 
        'mirror_algorithm', 'build_profiles', 'build_price_and_lanes', 'risk_engine'
    ));

-- =====================================================================
-- STEP 6: CREATE LLM VIEW FOR RISK SCORES
-- =====================================================================

-- Drop old view if exists (schema changed)
DROP VIEW IF EXISTS vw_risk_scores_for_llm;

-- Create updated view
CREATE OR REPLACE VIEW vw_risk_scores_for_llm AS
SELECT 
    rs.risk_id,
    rs.entity_type,
    rs.entity_id,
    rs.scope_key,
    rs.engine_version,
    rs.risk_score,
    rs.confidence_score,
    rs.risk_level,
    rs.main_reason_code,
    rs.reasons,
    rs.computed_at,
    -- Join entity names for convenience
    CASE 
        WHEN rs.entity_type = 'BUYER' THEN om.name_normalized
        WHEN rs.entity_type = 'EXPORTER' THEN om.name_normalized
        ELSE NULL
    END as entity_name
FROM risk_scores rs
LEFT JOIN organizations_master om ON rs.entity_id = om.org_uuid 
    AND rs.entity_type IN ('BUYER', 'EXPORTER');

-- Grant SELECT to LLM role if exists
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'llm_readonly') THEN
        GRANT SELECT ON vw_risk_scores_for_llm TO llm_readonly;
    END IF;
END
$$;

-- =====================================================================
-- VERIFICATION
-- =====================================================================

DO $$
BEGIN
    RAISE NOTICE 'EPIC 6C Migration complete:';
    RAISE NOTICE '  - risk_scores table created with new schema';
    RAISE NOTICE '  - risk_scores_history table created for audit trail';
    RAISE NOTICE '  - risk_engine_watermark table created for incremental processing';
    RAISE NOTICE '  - History archiving trigger installed';
    RAISE NOTICE '  - pipeline_runs constraint updated for risk_engine';
    RAISE NOTICE '  - vw_risk_scores_for_llm view recreated';
END $$;
