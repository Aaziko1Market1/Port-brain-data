-- =====================================================================
-- GTI-OS Data Platform - Database Schema v1.0
-- Target: PostgreSQL 13+
-- Database: aaziko_trade
-- =====================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy matching in Phase 3

-- =====================================================================
-- PHASE 0: OPERATIONAL TABLES
-- =====================================================================

-- File Registry: Track all ingested files with checksums and EPIC lifecycle
CREATE TABLE IF NOT EXISTS file_registry (
    file_id SERIAL PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_checksum TEXT NOT NULL UNIQUE,
    reporting_country TEXT,
    direction TEXT,  -- EXPORT, IMPORT
    year INTEGER,
    month INTEGER,
    file_size_bytes BIGINT,
    total_rows INTEGER,
    status TEXT NOT NULL,  -- PENDING, INGESTED, FAILED, DUPLICATE
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ingested_at TIMESTAMP,
    
    -- EPIC lifecycle tracking (for incremental processing)
    ingestion_completed_at TIMESTAMPTZ,
    standardization_started_at TIMESTAMPTZ,
    standardization_completed_at TIMESTAMPTZ,
    identity_started_at TIMESTAMPTZ,
    identity_completed_at TIMESTAMPTZ,
    ledger_started_at TIMESTAMPTZ,
    ledger_completed_at TIMESTAMPTZ,
    
    -- EPIC 9: Admin upload metadata
    source_format TEXT,  -- FULL, SHORT, OTHER
    source_provider TEXT,  -- e.g., Eximpedia, Customs Portal
    data_grain TEXT,  -- SHIPMENT_LINE, CONTAINER, INVOICE, UNKNOWN
    is_production BOOLEAN DEFAULT true,
    data_quality_level TEXT DEFAULT 'RAW',  -- RAW, CLEANED_BASIC, CLEANED_AAZIKO, UNKNOWN
    tags TEXT,  -- comma-separated
    notes TEXT,  -- free text
    header_row_index INTEGER DEFAULT 1,
    sheet_name TEXT,  -- Excel sheet name
    processing_mode TEXT,  -- INGEST_ONLY, INGEST_AND_STANDARDIZE, FULL_PIPELINE
    config_file_used TEXT,  -- YAML config path
    upload_source TEXT DEFAULT 'manual',  -- admin_upload, cron, manual
    uploaded_by TEXT,  -- future: user ID
    
    -- Extended pipeline tracking
    profiles_started_at TIMESTAMPTZ,
    profiles_completed_at TIMESTAMPTZ,
    lanes_started_at TIMESTAMPTZ,
    lanes_completed_at TIMESTAMPTZ,
    risk_started_at TIMESTAMPTZ,
    risk_completed_at TIMESTAMPTZ,
    serving_started_at TIMESTAMPTZ,
    serving_completed_at TIMESTAMPTZ,
    
    CONSTRAINT unique_file_checksum UNIQUE (file_checksum),
    CONSTRAINT chk_fr_data_grain CHECK (data_grain IS NULL OR data_grain IN ('SHIPMENT_LINE', 'CONTAINER', 'INVOICE', 'UNKNOWN')),
    CONSTRAINT chk_fr_data_quality CHECK (data_quality_level IS NULL OR data_quality_level IN ('RAW', 'CLEANED_BASIC', 'CLEANED_AAZIKO', 'UNKNOWN')),
    CONSTRAINT chk_fr_processing_mode CHECK (processing_mode IS NULL OR processing_mode IN ('INGEST_ONLY', 'INGEST_AND_STANDARDIZE', 'FULL_PIPELINE'))
);

CREATE INDEX idx_file_registry_status ON file_registry(status);
CREATE INDEX idx_file_registry_country_dir ON file_registry(reporting_country, direction);
CREATE INDEX idx_file_registry_year_month ON file_registry(year, month);
CREATE INDEX idx_fr_upload_source ON file_registry(upload_source);
CREATE INDEX idx_fr_is_production ON file_registry(is_production);
CREATE INDEX idx_fr_created_at ON file_registry(created_at DESC);

-- Partial indexes for pending work in each EPIC
CREATE INDEX idx_fr_std_pending ON file_registry(reporting_country, direction)
    WHERE status = 'INGESTED' AND standardization_completed_at IS NULL;
CREATE INDEX idx_fr_identity_pending ON file_registry(reporting_country, direction)
    WHERE status = 'INGESTED' AND identity_completed_at IS NULL;
CREATE INDEX idx_fr_ledger_pending ON file_registry(reporting_country, direction)
    WHERE status = 'INGESTED' AND ledger_completed_at IS NULL;

-- =====================================================================
-- PHASE 1: STAGING TABLES
-- =====================================================================

-- Stage 1: Raw Shipments (as ingested from files)
CREATE TABLE IF NOT EXISTS stg_shipments_raw (
    raw_id BIGSERIAL PRIMARY KEY,
    raw_file_name TEXT NOT NULL,
    reporting_country TEXT NOT NULL,
    direction TEXT NOT NULL,  -- EXPORT, IMPORT
    source_format TEXT,  -- FULL, SHORT
    record_grain TEXT,  -- LINE_ITEM, AGGREGATE
    raw_row_number INTEGER NOT NULL,
    
    -- Core raw data as JSONB
    raw_data JSONB NOT NULL,
    
    -- Optional: Pre-extracted fields for quick access
    hs_code_raw TEXT,
    buyer_name_raw TEXT,
    supplier_name_raw TEXT,
    shipment_date_raw TEXT,
    
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stg_raw_file ON stg_shipments_raw(raw_file_name);
CREATE INDEX idx_stg_raw_country_dir ON stg_shipments_raw(reporting_country, direction);
CREATE INDEX idx_stg_raw_ingested_at ON stg_shipments_raw(ingested_at);
CREATE INDEX idx_stg_raw_data_gin ON stg_shipments_raw USING GIN (raw_data);

-- Stage 2: Standardized Shipments (after Phase 2 processing)
CREATE TABLE IF NOT EXISTS stg_shipments_standardized (
    std_id BIGSERIAL PRIMARY KEY,
    raw_id BIGINT REFERENCES stg_shipments_raw(raw_id),
    
    -- Standardized entity names
    buyer_name_raw TEXT,
    buyer_name_clean TEXT,
    buyer_uuid UUID,  -- Linked in Phase 3
    
    supplier_name_raw TEXT,
    supplier_name_clean TEXT,
    supplier_uuid UUID,  -- Linked in Phase 3
    
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
    
    standardized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_year_valid CHECK (year >= 2000 AND year <= 2100),
    CONSTRAINT chk_month_valid CHECK (month >= 1 AND month <= 12)
);

CREATE INDEX idx_stg_std_raw_id ON stg_shipments_standardized(raw_id);
CREATE INDEX idx_stg_std_buyer_uuid ON stg_shipments_standardized(buyer_uuid);
CREATE INDEX idx_stg_std_supplier_uuid ON stg_shipments_standardized(supplier_uuid);
CREATE INDEX idx_stg_std_hs6 ON stg_shipments_standardized(hs_code_6);
CREATE INDEX idx_stg_std_dates ON stg_shipments_standardized(shipment_date, year, month);
CREATE INDEX idx_stg_std_countries ON stg_shipments_standardized(origin_country, destination_country);

-- =====================================================================
-- PHASE 3: MASTER DATA
-- =====================================================================

-- Organizations Master: Unified buyer/supplier registry
CREATE TABLE IF NOT EXISTS organizations_master (
    org_uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name_normalized TEXT NOT NULL,
    country_iso TEXT NOT NULL,
    type TEXT NOT NULL,  -- BUYER, SUPPLIER, MIXED
    
    -- Name variants seen across sources
    raw_name_variants JSONB DEFAULT '[]'::jsonb,
    
    -- Address & contact (future)
    address TEXT,
    city TEXT,
    postal_code TEXT,
    
    -- Metadata
    first_seen_date DATE,
    last_seen_date DATE,
    total_transactions INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_org_type CHECK (type IN ('BUYER', 'SUPPLIER', 'MIXED'))
);

CREATE UNIQUE INDEX idx_org_name_country ON organizations_master(name_normalized, country_iso);
CREATE INDEX idx_org_type ON organizations_master(type);
CREATE INDEX idx_org_country ON organizations_master(country_iso);
CREATE INDEX idx_org_name_trgm ON organizations_master USING gin(name_normalized gin_trgm_ops);

-- Product Taxonomy (for future HS code enrichment)
CREATE TABLE IF NOT EXISTS product_taxonomy (
    hs_code_6 TEXT PRIMARY KEY,
    hs_code_4 TEXT,
    hs_code_2 TEXT,
    description TEXT,
    category_l1 TEXT,
    category_l2 TEXT,
    category_l3 TEXT,
    unit_of_measure TEXT,
    avg_density_kg_per_m3 NUMERIC,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_product_hs4 ON product_taxonomy(hs_code_4);
CREATE INDEX idx_product_hs2 ON product_taxonomy(hs_code_2);
CREATE INDEX idx_product_category ON product_taxonomy(category_l1, category_l2);

-- =====================================================================
-- PHASE 4: FACT TABLE (PARTITIONED BY YEAR)
-- =====================================================================

-- Global Trades Ledger: Single source of truth for all trade transactions
-- Partitioned by year for 47+ countries / 100M+ rows scale
CREATE TABLE IF NOT EXISTS global_trades_ledger (
    transaction_id UUID NOT NULL,
    std_id BIGINT NOT NULL,  -- Links to stg_shipments_standardized for idempotency
    
    -- Geography
    reporting_country TEXT NOT NULL,
    direction TEXT NOT NULL,
    origin_country TEXT NOT NULL,
    destination_country TEXT NOT NULL,
    
    -- Temporal
    export_date DATE,
    import_date DATE,
    shipment_date DATE NOT NULL,
    year INT NOT NULL,
    month INT,
    
    -- Entities
    buyer_uuid UUID,
    supplier_uuid UUID,
    
    -- Product
    hs_code_raw TEXT,
    hs_code_6 TEXT NOT NULL,
    goods_description TEXT,
    
    -- Quantities
    qty_raw NUMERIC,
    qty_kg NUMERIC,
    qty_unit TEXT,
    
    -- Values
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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Composite primary key (required for partitioning)
    PRIMARY KEY (transaction_id, year),
    
    CONSTRAINT chk_gtl_year_valid CHECK (year >= 2000 AND year <= 2100),
    CONSTRAINT chk_gtl_month_valid CHECK (month >= 1 AND month <= 12),
    CONSTRAINT chk_gtl_direction CHECK (direction IN ('EXPORT', 'IMPORT'))
) PARTITION BY RANGE (year);

-- Create year partitions (2020-2030)
CREATE TABLE IF NOT EXISTS global_trades_ledger_2020 PARTITION OF global_trades_ledger FOR VALUES FROM (2020) TO (2021);
CREATE TABLE IF NOT EXISTS global_trades_ledger_2021 PARTITION OF global_trades_ledger FOR VALUES FROM (2021) TO (2022);
CREATE TABLE IF NOT EXISTS global_trades_ledger_2022 PARTITION OF global_trades_ledger FOR VALUES FROM (2022) TO (2023);
CREATE TABLE IF NOT EXISTS global_trades_ledger_2023 PARTITION OF global_trades_ledger FOR VALUES FROM (2023) TO (2024);
CREATE TABLE IF NOT EXISTS global_trades_ledger_2024 PARTITION OF global_trades_ledger FOR VALUES FROM (2024) TO (2025);
CREATE TABLE IF NOT EXISTS global_trades_ledger_2025 PARTITION OF global_trades_ledger FOR VALUES FROM (2025) TO (2026);
CREATE TABLE IF NOT EXISTS global_trades_ledger_2026 PARTITION OF global_trades_ledger FOR VALUES FROM (2026) TO (2027);
CREATE TABLE IF NOT EXISTS global_trades_ledger_2027 PARTITION OF global_trades_ledger FOR VALUES FROM (2027) TO (2028);
CREATE TABLE IF NOT EXISTS global_trades_ledger_2028 PARTITION OF global_trades_ledger FOR VALUES FROM (2028) TO (2029);
CREATE TABLE IF NOT EXISTS global_trades_ledger_2029 PARTITION OF global_trades_ledger FOR VALUES FROM (2029) TO (2030);
CREATE TABLE IF NOT EXISTS global_trades_ledger_2030 PARTITION OF global_trades_ledger FOR VALUES FROM (2030) TO (2031);

-- Critical indexes (automatically created on partitions)
CREATE UNIQUE INDEX idx_gtl_std_id ON global_trades_ledger(std_id, year);
CREATE INDEX idx_gtl_buyer ON global_trades_ledger(buyer_uuid);
CREATE INDEX idx_gtl_supplier ON global_trades_ledger(supplier_uuid);
CREATE INDEX idx_gtl_hs_dest_year ON global_trades_ledger(hs_code_6, destination_country, year);
CREATE INDEX idx_gtl_origin_dest_date ON global_trades_ledger(origin_country, destination_country, shipment_date);
CREATE INDEX idx_gtl_reporting_country ON global_trades_ledger(reporting_country);
CREATE INDEX idx_gtl_direction ON global_trades_ledger(direction);
CREATE INDEX idx_gtl_year_month ON global_trades_ledger(year, month);
CREATE INDEX idx_gtl_shipment_date ON global_trades_ledger(shipment_date);
CREATE INDEX idx_gtl_hs6 ON global_trades_ledger(hs_code_6);
CREATE INDEX idx_gtl_country_dir_year ON global_trades_ledger(reporting_country, direction, year);
CREATE INDEX idx_gtl_buyer_hs6 ON global_trades_ledger(buyer_uuid, hs_code_6) WHERE buyer_uuid IS NOT NULL;
CREATE INDEX idx_gtl_supplier_hs6 ON global_trades_ledger(supplier_uuid, hs_code_6) WHERE supplier_uuid IS NOT NULL;

-- =====================================================================
-- PIPELINE RUNS TRACKING (Control Tower visibility)
-- =====================================================================

-- Pipeline Runs: Track every execution of ingestion/standardization/identity/ledger
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
    
    CONSTRAINT chk_pipeline_name CHECK (pipeline_name IN ('ingestion', 'standardization', 'identity', 'ledger', 'mirror_algorithm', 'build_profiles', 'build_price_and_lanes', 'risk_engine', 'serving_views', 'admin_upload_ingest_only', 'admin_upload_ingest_and_standardize', 'admin_upload_full_pipeline')),
    CONSTRAINT chk_pipeline_status CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED', 'PARTIAL'))
);

CREATE INDEX idx_pr_pipeline_started ON pipeline_runs(pipeline_name, started_at DESC);
CREATE INDEX idx_pr_status_running ON pipeline_runs(status) WHERE status = 'RUNNING';
CREATE INDEX idx_pr_status ON pipeline_runs(status);
CREATE INDEX idx_pr_started_at ON pipeline_runs(started_at DESC);

-- =====================================================================
-- PHASE 5: MIRROR ALGORITHM
-- =====================================================================

-- Mirror Match Log: Track export-import matched pairs
-- Note: References removed due to partitioned table - integrity maintained via application logic
CREATE TABLE IF NOT EXISTS mirror_match_log (
    match_id BIGSERIAL PRIMARY KEY,
    export_transaction_id UUID NOT NULL,
    export_year INT NOT NULL,
    import_transaction_id UUID NOT NULL,
    import_year INT NOT NULL,
    match_score NUMERIC NOT NULL,
    criteria_used JSONB,  -- Details of matching criteria
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_export_match UNIQUE (export_transaction_id)
);

CREATE INDEX idx_mirror_export ON mirror_match_log(export_transaction_id);
CREATE INDEX idx_mirror_import ON mirror_match_log(import_transaction_id);
CREATE INDEX idx_mirror_score ON mirror_match_log(match_score);

-- =====================================================================
-- PHASE 6: ANALYTICS TABLES
-- =====================================================================

-- Buyer Profile: Aggregated buyer intelligence
CREATE TABLE IF NOT EXISTS buyer_profile (
    profile_id BIGSERIAL PRIMARY KEY,
    buyer_uuid UUID NOT NULL REFERENCES organizations_master(org_uuid),
    destination_country TEXT NOT NULL,
    hs_code_6 TEXT,  -- NULL = all products
    
    -- Time window
    year INTEGER,
    month INTEGER,
    
    -- Volumes
    total_teu NUMERIC,
    total_cif_usd NUMERIC,
    volume_kg NUMERIC,
    transaction_count INTEGER,
    
    -- Pricing
    avg_price_usd NUMERIC,
    median_price_usd NUMERIC,
    
    -- Growth
    growth_rate_mom NUMERIC,  -- Month-over-month
    growth_rate_yoy NUMERIC,  -- Year-over-year
    
    -- Relationships
    top_hs_codes JSONB,
    top_suppliers JSONB,
    supplier_count INTEGER,
    
    -- Logistics
    port_preference JSONB,
    avg_order_size_kg NUMERIC,
    
    -- Persona
    persona_label TEXT,  -- Whale, Mid, Value, Growing, Seasonal
    
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_buyer_profile UNIQUE (buyer_uuid, destination_country, hs_code_6, year, month)
);

CREATE INDEX idx_buyer_profile_buyer ON buyer_profile(buyer_uuid);
CREATE INDEX idx_buyer_profile_country ON buyer_profile(destination_country);
CREATE INDEX idx_buyer_profile_hs6 ON buyer_profile(hs_code_6);
CREATE INDEX idx_buyer_profile_period ON buyer_profile(year, month);
CREATE INDEX idx_buyer_profile_persona ON buyer_profile(persona_label);

-- Exporter Profile: Aggregated supplier intelligence
CREATE TABLE IF NOT EXISTS exporter_profile (
    profile_id BIGSERIAL PRIMARY KEY,
    supplier_uuid UUID NOT NULL REFERENCES organizations_master(org_uuid),
    origin_country TEXT NOT NULL,
    hs_code_6 TEXT,  -- NULL = all products
    
    -- Time window
    year INTEGER,
    month INTEGER,
    
    -- Volumes
    total_fob_usd NUMERIC,
    total_volume_kg NUMERIC,
    shipment_count INTEGER,
    
    -- Market reach
    destination_country_count INTEGER,
    buyer_count INTEGER,
    
    -- Relationships
    top_buyers JSONB,
    top_hs_codes JSONB,
    top_destinations JSONB,
    
    -- Performance
    stability_score NUMERIC,
    onboarding_score NUMERIC,
    
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_exporter_profile UNIQUE (supplier_uuid, origin_country, hs_code_6, year, month)
);

CREATE INDEX idx_exporter_profile_supplier ON exporter_profile(supplier_uuid);
CREATE INDEX idx_exporter_profile_country ON exporter_profile(origin_country);
CREATE INDEX idx_exporter_profile_hs6 ON exporter_profile(hs_code_6);
CREATE INDEX idx_exporter_profile_period ON exporter_profile(year, month);

-- Price Corridor: Statistical price ranges by product-market-time
CREATE TABLE IF NOT EXISTS price_corridor (
    corridor_id BIGSERIAL PRIMARY KEY,
    hs_code_6 TEXT NOT NULL,
    destination_country TEXT NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    
    -- Price statistics (USD per kg)
    min_price NUMERIC,
    p25_price NUMERIC,
    median_price NUMERIC,
    p75_price NUMERIC,
    max_price NUMERIC,
    avg_price NUMERIC,
    std_dev_price NUMERIC,
    
    -- Sample metadata
    sample_size INTEGER,
    total_volume_kg NUMERIC,
    
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_price_corridor UNIQUE (hs_code_6, destination_country, year, month)
);

CREATE INDEX idx_price_corridor_hs6 ON price_corridor(hs_code_6);
CREATE INDEX idx_price_corridor_country ON price_corridor(destination_country);
CREATE INDEX idx_price_corridor_period ON price_corridor(year, month);

-- Lane Statistics: Route-level intelligence
CREATE TABLE IF NOT EXISTS lane_stats (
    lane_id BIGSERIAL PRIMARY KEY,
    origin_port TEXT NOT NULL,
    destination_port TEXT NOT NULL,
    hs_code_6 TEXT,
    
    -- Time window
    year INTEGER,
    month INTEGER,
    
    -- Transit performance
    avg_transit_days NUMERIC,
    min_transit_days INTEGER,
    max_transit_days INTEGER,
    
    -- Volume
    total_teu NUMERIC,
    shipment_count INTEGER,
    
    -- Carriers
    carrier_usage JSONB,
    top_carrier TEXT,
    
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_lane_stats UNIQUE (origin_port, destination_port, hs_code_6, year, month)
);

CREATE INDEX idx_lane_stats_origin ON lane_stats(origin_port);
CREATE INDEX idx_lane_stats_destination ON lane_stats(destination_port);
CREATE INDEX idx_lane_stats_hs6 ON lane_stats(hs_code_6);
CREATE INDEX idx_lane_stats_period ON lane_stats(year, month);

-- Risk Scores: Rule-based risk flags
CREATE TABLE IF NOT EXISTS risk_scores (
    risk_id BIGSERIAL PRIMARY KEY,
    entity_id UUID NOT NULL,  -- transaction_id, buyer_uuid, or supplier_uuid
    entity_type TEXT NOT NULL,  -- SHIPMENT, BUYER, EXPORTER
    
    risk_score NUMERIC NOT NULL,
    risk_level TEXT NOT NULL,  -- LOW, MEDIUM, HIGH, CRITICAL
    
    -- Risk reasons
    reasons JSONB,
    
    -- Flags
    under_invoicing_flag BOOLEAN DEFAULT FALSE,
    unusual_route_flag BOOLEAN DEFAULT FALSE,
    sudden_spike_flag BOOLEAN DEFAULT FALSE,
    new_relationship_flag BOOLEAN DEFAULT FALSE,
    
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_risk_level CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    CONSTRAINT chk_entity_type CHECK (entity_type IN ('SHIPMENT', 'BUYER', 'EXPORTER'))
);

CREATE INDEX idx_risk_entity ON risk_scores(entity_id, entity_type);
CREATE INDEX idx_risk_level ON risk_scores(risk_level);
CREATE INDEX idx_risk_score ON risk_scores(risk_score);

-- =====================================================================
-- PHASE 7: ADVANCED ANALYTICS (Schema Only)
-- =====================================================================

-- Demand Trends: Time-series demand patterns
CREATE TABLE IF NOT EXISTS demand_trends (
    trend_id BIGSERIAL PRIMARY KEY,
    hs_code_6 TEXT NOT NULL,
    destination_country TEXT NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    
    total_volume_kg NUMERIC,
    total_value_usd NUMERIC,
    transaction_count INTEGER,
    
    -- Moving averages
    ma_3month_volume NUMERIC,
    ma_6month_volume NUMERIC,
    ma_12month_volume NUMERIC,
    
    -- Trend indicators
    trend_direction TEXT,  -- GROWING, STABLE, DECLINING
    seasonality_index NUMERIC,
    
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_demand_trend UNIQUE (hs_code_6, destination_country, year, month)
);

CREATE INDEX idx_demand_hs6 ON demand_trends(hs_code_6);
CREATE INDEX idx_demand_country ON demand_trends(destination_country);
CREATE INDEX idx_demand_period ON demand_trends(year, month);

-- Country Opportunity Scores: Market attractiveness by product
CREATE TABLE IF NOT EXISTS country_opportunity_scores (
    opportunity_id BIGSERIAL PRIMARY KEY,
    hs_code_6 TEXT NOT NULL,
    destination_country TEXT NOT NULL,
    
    opportunity_score NUMERIC NOT NULL,  -- 0-100
    
    -- Score components
    volume_score NUMERIC,
    growth_score NUMERIC,
    price_score NUMERIC,
    competition_score NUMERIC,
    
    -- Market intelligence
    market_size_usd NUMERIC,
    growth_rate_yoy NUMERIC,
    avg_price_premium NUMERIC,
    supplier_count INTEGER,
    
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_country_opp UNIQUE (hs_code_6, destination_country)
);

CREATE INDEX idx_country_opp_hs6 ON country_opportunity_scores(hs_code_6);
CREATE INDEX idx_country_opp_country ON country_opportunity_scores(destination_country);
CREATE INDEX idx_country_opp_score ON country_opportunity_scores(opportunity_score DESC);

-- Product Bundle Stats: Co-purchase patterns
CREATE TABLE IF NOT EXISTS product_bundle_stats (
    bundle_id BIGSERIAL PRIMARY KEY,
    hs_code_6_primary TEXT NOT NULL,
    hs_code_6_secondary TEXT NOT NULL,
    destination_country TEXT,
    
    co_occurrence_count INTEGER,
    lift_score NUMERIC,  -- Association strength
    confidence_score NUMERIC,
    
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_bundle UNIQUE (hs_code_6_primary, hs_code_6_secondary, destination_country)
);

CREATE INDEX idx_bundle_primary ON product_bundle_stats(hs_code_6_primary);
CREATE INDEX idx_bundle_secondary ON product_bundle_stats(hs_code_6_secondary);
CREATE INDEX idx_bundle_lift ON product_bundle_stats(lift_score DESC);

-- =====================================================================
-- PHASE 8: LLM SERVING VIEWS
-- =====================================================================

-- View: Global Shipments for LLM
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

-- View: Buyer Profiles for LLM
CREATE OR REPLACE VIEW vw_buyer_profile_for_llm AS
SELECT 
    bp.buyer_uuid,
    o.name_normalized AS buyer_name,
    bp.destination_country,
    bp.hs_code_6,
    bp.year,
    bp.month,
    bp.total_cif_usd,
    bp.volume_kg,
    bp.transaction_count,
    bp.avg_price_usd,
    bp.growth_rate_yoy,
    bp.persona_label,
    bp.top_suppliers,
    bp.supplier_count
FROM buyer_profile bp
JOIN organizations_master o ON bp.buyer_uuid = o.org_uuid;

-- View: Exporter Profiles for LLM
CREATE OR REPLACE VIEW vw_exporter_profile_for_llm AS
SELECT 
    ep.supplier_uuid,
    o.name_normalized AS exporter_name,
    ep.origin_country,
    ep.hs_code_6,
    ep.year,
    ep.month,
    ep.total_fob_usd,
    ep.total_volume_kg,
    ep.shipment_count,
    ep.buyer_count,
    ep.top_buyers,
    ep.stability_score
FROM exporter_profile ep
JOIN organizations_master o ON ep.supplier_uuid = o.org_uuid;

-- View: Price Corridors for LLM
CREATE OR REPLACE VIEW vw_price_corridor_for_llm AS
SELECT 
    hs_code_6,
    destination_country,
    year,
    month,
    min_price,
    p25_price,
    median_price,
    p75_price,
    max_price,
    avg_price,
    sample_size
FROM price_corridor;

-- View: Lane Statistics for LLM
CREATE OR REPLACE VIEW vw_lane_stats_for_llm AS
SELECT 
    origin_port,
    destination_port,
    hs_code_6,
    year,
    month,
    avg_transit_days,
    total_teu,
    shipment_count,
    carrier_usage
FROM lane_stats;

-- View: Risk Scores for LLM (updated for EPIC 6C schema)
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
    CASE 
        WHEN rs.entity_type = 'BUYER' THEN om.name_normalized
        WHEN rs.entity_type = 'EXPORTER' THEN om.name_normalized
        ELSE NULL
    END as entity_name
FROM risk_scores rs
LEFT JOIN organizations_master om ON rs.entity_id = om.org_uuid 
    AND rs.entity_type IN ('BUYER', 'EXPORTER');

-- View: Country Opportunities for LLM
CREATE OR REPLACE VIEW vw_country_opportunity_for_llm AS
SELECT 
    hs_code_6,
    destination_country,
    opportunity_score,
    market_size_usd,
    growth_rate_yoy,
    supplier_count,
    computed_at
FROM country_opportunity_scores
ORDER BY opportunity_score DESC;

-- =====================================================================
-- EPIC 7A: SERVING LAYER VIEWS
-- =====================================================================

-- Note: Full view definitions are in migration 006_epic7a_serving_views.sql
-- These are placeholder definitions for documentation purposes.
-- The actual views are created by the migration which includes complex CTEs.

-- vw_buyer_360: One row per buyer with aggregated volumes, risk, HS mix
-- Columns: buyer_uuid, buyer_name, buyer_country, buyer_classification,
--          total_shipments, total_value_usd, total_qty_kg, total_teu,
--          first_shipment_date, last_shipment_date, active_years,
--          top_hs6 (JSONB), top_origin_countries (JSONB),
--          current_risk_level, current_risk_score, has_ghost_flag,
--          risk_engine_version, last_profile_updated_at, last_risk_scored_at

-- mv_country_hs_month_summary: Materialized view for country/HS dashboards
-- Grain: (reporting_country, direction, hs_code_6, year, month)
-- Columns: shipment_count, unique_buyers, unique_suppliers, total_value_usd,
--          total_qty_kg, avg_price_usd_per_kg, high_risk_shipments,
--          high_risk_buyers, avg_value_per_shipment_usd, refreshed_at

-- vw_country_hs_dashboard: Clean view on mv_country_hs_month_summary
-- Adds: value_share_pct, high_risk_shipment_pct

-- vw_buyer_hs_activity: Helper for buyer-HS queries
-- Grain: (buyer_uuid, hs_code_6, reporting_country, direction)

-- =====================================================================
-- PHASE 8: DATABASE ROLES & PERMISSIONS
-- =====================================================================

-- Create LLM read-only role
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'llm_readonly') THEN
        CREATE ROLE llm_readonly;
    END IF;
END
$$;

-- Grant SELECT on all LLM views
GRANT SELECT ON vw_global_shipments_for_llm TO llm_readonly;
GRANT SELECT ON vw_buyer_profile_for_llm TO llm_readonly;
GRANT SELECT ON vw_exporter_profile_for_llm TO llm_readonly;
GRANT SELECT ON vw_price_corridor_for_llm TO llm_readonly;
GRANT SELECT ON vw_lane_stats_for_llm TO llm_readonly;
GRANT SELECT ON vw_risk_scores_for_llm TO llm_readonly;
GRANT SELECT ON vw_country_opportunity_for_llm TO llm_readonly;

-- =====================================================================
-- UTILITY FUNCTIONS
-- =====================================================================

-- Function: Update file registry status
CREATE OR REPLACE FUNCTION update_file_registry_status()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_file_registry_update
BEFORE UPDATE ON file_registry
FOR EACH ROW
EXECUTE FUNCTION update_file_registry_status();

-- Function: Update organization updated_at
CREATE OR REPLACE FUNCTION update_organization_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_organization_update
BEFORE UPDATE ON organizations_master
FOR EACH ROW
EXECUTE FUNCTION update_organization_timestamp();

-- =====================================================================
-- EPIC 10: MAPPING REGISTRY FOR MULTI-COUNTRY ONBOARDING
-- =====================================================================

-- Mapping Registry: Track status of country mappings (DRAFT → VERIFIED → LIVE)
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
    verified_row_count INTEGER,
    verified_date_coverage TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_mr_direction CHECK (direction IN ('IMPORT', 'EXPORT')),
    CONSTRAINT chk_mr_source_format CHECK (source_format IN ('FULL', 'SHORT')),
    CONSTRAINT chk_mr_status CHECK (status IN ('DRAFT', 'VERIFIED', 'LIVE'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mapping_registry_key
    ON mapping_registry (reporting_country, direction, source_format);
CREATE INDEX IF NOT EXISTS idx_mapping_registry_status ON mapping_registry (status);
CREATE INDEX IF NOT EXISTS idx_mapping_registry_config_key ON mapping_registry (config_key);

-- Sandbox tables for validation (EPIC 10)
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
    validation_session_id UUID,
    CONSTRAINT chk_tmp_raw_direction CHECK (direction IN ('EXPORT', 'IMPORT'))
);

CREATE TABLE IF NOT EXISTS tmp_stg_shipments_standardized (
    std_id BIGSERIAL PRIMARY KEY,
    raw_id BIGINT,
    buyer_name_raw TEXT,
    buyer_name_clean TEXT,
    supplier_name_raw TEXT,
    supplier_name_clean TEXT,
    hs_code_raw TEXT,
    hs_code_6 TEXT,
    goods_description TEXT,
    origin_country TEXT,
    origin_country_raw TEXT,
    destination_country TEXT,
    destination_country_raw TEXT,
    reporting_country TEXT,
    export_date DATE,
    import_date DATE,
    shipment_date DATE,
    year INTEGER,
    month INTEGER,
    qty_raw NUMERIC,
    qty_unit_raw TEXT,
    qty_kg NUMERIC,
    value_raw NUMERIC,
    value_currency TEXT,
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
    direction TEXT,
    standardized_at TIMESTAMPTZ DEFAULT NOW(),
    validation_session_id UUID
);

CREATE INDEX IF NOT EXISTS idx_tmp_raw_session ON tmp_stg_shipments_raw(validation_session_id);
CREATE INDEX IF NOT EXISTS idx_tmp_std_session ON tmp_stg_shipments_standardized(validation_session_id);

-- =====================================================================
-- COMPLETED: Schema v1.0
-- =====================================================================

COMMENT ON DATABASE aaziko_trade IS 'GTI-OS Global Trade Intelligence Platform - v1.0';
