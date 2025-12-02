-- =====================================================================
-- Migration 006: EPIC 7A - Buyer 360 & HS Dashboard Serving Layer
-- GTI-OS Data Platform
-- Date: 2025-11-30
-- =====================================================================
-- This migration creates LLM-friendly serving views:
--   vw_buyer_360: One row per buyer with aggregated volumes, risk, HS mix
--   mv_country_hs_month_summary: Materialized view for country/HS dashboards
--   vw_country_hs_dashboard: Clean view on top of MV
--
-- Design principles:
--   - Read-only views over existing tables (no new data storage except MV)
--   - Optimized for frontend/LLM queries (one query = one answer)
--   - LEFT JOINs ensure completeness (buyers without risk still appear)
-- =====================================================================

-- =====================================================================
-- STEP 1: UPDATE PIPELINE_RUNS CONSTRAINT
-- =====================================================================

ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS chk_pipeline_name;
ALTER TABLE pipeline_runs ADD CONSTRAINT chk_pipeline_name 
    CHECK (pipeline_name IN (
        'ingestion', 'standardization', 'identity', 'ledger', 
        'mirror_algorithm', 'build_profiles', 'build_price_and_lanes', 
        'risk_engine', 'serving_views'
    ));

-- =====================================================================
-- STEP 2: CREATE vw_buyer_360 VIEW
-- =====================================================================

DROP VIEW IF EXISTS vw_buyer_360 CASCADE;

CREATE VIEW vw_buyer_360 AS
WITH 
-- Ledger aggregates per buyer
buyer_ledger_aggs AS (
    SELECT 
        g.buyer_uuid,
        COUNT(*) AS total_shipments,
        SUM(g.customs_value_usd) AS total_value_usd,
        SUM(g.qty_kg) AS total_qty_kg,
        SUM(g.teu) AS total_teu,
        MIN(g.shipment_date) AS first_shipment_date,
        MAX(g.shipment_date) AS last_shipment_date,
        COUNT(DISTINCT g.year) AS active_years,
        COUNT(DISTINCT g.hs_code_6) AS unique_hs_codes,
        COUNT(DISTINCT g.origin_country) AS unique_origin_countries,
        COUNT(DISTINCT g.supplier_uuid) AS unique_suppliers
    FROM global_trades_ledger g
    WHERE g.buyer_uuid IS NOT NULL
    GROUP BY g.buyer_uuid
),

-- Top HS codes per buyer (top 5 by value)
buyer_top_hs AS (
    SELECT 
        g.buyer_uuid,
        jsonb_agg(
            jsonb_build_object(
                'hs_code_6', hs_data.hs_code_6,
                'value_usd', hs_data.value_usd,
                'share_pct', ROUND((hs_data.value_usd / NULLIF(hs_data.total_buyer_value, 0) * 100)::numeric, 1)
            ) ORDER BY hs_data.value_usd DESC
        ) FILTER (WHERE hs_data.rn <= 5) AS top_hs6
    FROM global_trades_ledger g
    INNER JOIN (
        SELECT 
            buyer_uuid,
            hs_code_6,
            SUM(customs_value_usd) AS value_usd,
            SUM(SUM(customs_value_usd)) OVER (PARTITION BY buyer_uuid) AS total_buyer_value,
            ROW_NUMBER() OVER (PARTITION BY buyer_uuid ORDER BY SUM(customs_value_usd) DESC) AS rn
        FROM global_trades_ledger
        WHERE buyer_uuid IS NOT NULL AND hs_code_6 IS NOT NULL
        GROUP BY buyer_uuid, hs_code_6
    ) hs_data ON g.buyer_uuid = hs_data.buyer_uuid AND g.hs_code_6 = hs_data.hs_code_6
    WHERE g.buyer_uuid IS NOT NULL
    GROUP BY g.buyer_uuid
),

-- Top origin countries per buyer (top 5 by value)
buyer_top_origins AS (
    SELECT 
        buyer_uuid,
        jsonb_agg(
            jsonb_build_object(
                'origin_country', origin_country,
                'value_usd', value_usd,
                'share_pct', ROUND((value_usd / NULLIF(total_buyer_value, 0) * 100)::numeric, 1)
            ) ORDER BY value_usd DESC
        ) FILTER (WHERE rn <= 5) AS top_origin_countries
    FROM (
        SELECT 
            buyer_uuid,
            origin_country,
            SUM(customs_value_usd) AS value_usd,
            SUM(SUM(customs_value_usd)) OVER (PARTITION BY buyer_uuid) AS total_buyer_value,
            ROW_NUMBER() OVER (PARTITION BY buyer_uuid ORDER BY SUM(customs_value_usd) DESC) AS rn
        FROM global_trades_ledger
        WHERE buyer_uuid IS NOT NULL AND origin_country IS NOT NULL
        GROUP BY buyer_uuid, origin_country
    ) origin_data
    GROUP BY buyer_uuid
),

-- Latest risk score per buyer (using window function to get most recent)
buyer_latest_risk AS (
    SELECT DISTINCT ON (entity_id)
        entity_id AS buyer_uuid,
        risk_level AS current_risk_level,
        risk_score AS current_risk_score,
        confidence_score AS current_confidence_score,
        main_reason_code AS current_main_reason_code,
        engine_version AS risk_engine_version,
        computed_at AS last_risk_scored_at,
        reasons AS risk_reasons_sample
    FROM risk_scores
    WHERE entity_type = 'BUYER'
    ORDER BY entity_id, computed_at DESC
),

-- Ghost entity flag (any GHOST_ENTITY reason for this buyer)
buyer_ghost_flag AS (
    SELECT DISTINCT entity_id AS buyer_uuid, TRUE AS has_ghost_flag
    FROM risk_scores
    WHERE entity_type = 'BUYER' AND main_reason_code = 'GHOST_ENTITY'
),

-- Latest profile update per buyer
buyer_latest_profile AS (
    SELECT DISTINCT ON (buyer_uuid)
        buyer_uuid,
        persona_label AS buyer_classification,
        updated_at AS last_profile_updated_at
    FROM buyer_profile
    ORDER BY buyer_uuid, updated_at DESC
)

SELECT 
    -- Identity & profile
    om.org_uuid AS buyer_uuid,
    om.name_normalized AS buyer_name,
    om.country_iso AS buyer_country,
    -- Website/email from raw_name_variants (if available)
    NULL::TEXT AS primary_website,  -- Not stored in current schema
    NULL::TEXT AS primary_email_domain,  -- Not stored in current schema
    COALESCE(bp.buyer_classification, 'Unknown') AS buyer_classification,
    
    -- Volume & activity (ledger-based)
    COALESCE(bla.total_shipments, 0) AS total_shipments,
    COALESCE(bla.total_value_usd, 0) AS total_value_usd,
    COALESCE(bla.total_qty_kg, 0) AS total_qty_kg,
    COALESCE(bla.total_teu, 0) AS total_teu,
    bla.first_shipment_date,
    bla.last_shipment_date,
    COALESCE(bla.active_years, 0) AS active_years,
    COALESCE(bla.unique_hs_codes, 0) AS unique_hs_codes,
    COALESCE(bla.unique_origin_countries, 0) AS unique_origin_countries,
    COALESCE(bla.unique_suppliers, 0) AS unique_suppliers,
    
    -- Product & lane mix (JSON aggregates)
    COALESCE(bth.top_hs6, '[]'::jsonb) AS top_hs6,
    COALESCE(bto.top_origin_countries, '[]'::jsonb) AS top_origin_countries,
    
    -- Risk snapshot
    COALESCE(blr.current_risk_level, 'UNSCORED') AS current_risk_level,
    blr.current_risk_score,
    blr.current_confidence_score,
    blr.current_main_reason_code,
    COALESCE(bgf.has_ghost_flag, FALSE) AS has_ghost_flag,
    blr.risk_engine_version,
    blr.risk_reasons_sample,
    
    -- Serving metadata
    bp.last_profile_updated_at,
    blr.last_risk_scored_at,
    om.created_at AS organization_created_at,
    om.updated_at AS organization_updated_at

FROM organizations_master om
-- Only buyers (type BUYER or MIXED with buyer activity)
LEFT JOIN buyer_ledger_aggs bla ON om.org_uuid = bla.buyer_uuid
LEFT JOIN buyer_top_hs bth ON om.org_uuid = bth.buyer_uuid
LEFT JOIN buyer_top_origins bto ON om.org_uuid = bto.buyer_uuid
LEFT JOIN buyer_latest_risk blr ON om.org_uuid = blr.buyer_uuid
LEFT JOIN buyer_ghost_flag bgf ON om.org_uuid = bgf.buyer_uuid
LEFT JOIN buyer_latest_profile bp ON om.org_uuid = bp.buyer_uuid
WHERE om.type IN ('BUYER', 'MIXED')
   OR bla.buyer_uuid IS NOT NULL;  -- Include any org with buyer activity

-- Add comment for documentation
COMMENT ON VIEW vw_buyer_360 IS 'EPIC 7A: Buyer 360 view combining identity, ledger aggregates, product mix, and risk intelligence. One row per buyer organization.';

-- =====================================================================
-- STEP 3: CREATE MATERIALIZED VIEW mv_country_hs_month_summary
-- =====================================================================

DROP MATERIALIZED VIEW IF EXISTS mv_country_hs_month_summary CASCADE;

CREATE MATERIALIZED VIEW mv_country_hs_month_summary AS
WITH 
-- Base ledger aggregates by grain
ledger_aggs AS (
    SELECT 
        g.reporting_country,
        g.direction,
        g.hs_code_6,
        g.year,
        g.month,
        COUNT(*) AS shipment_count,
        COUNT(DISTINCT g.buyer_uuid) AS unique_buyers,
        COUNT(DISTINCT g.supplier_uuid) AS unique_suppliers,
        SUM(g.customs_value_usd) AS total_value_usd,
        SUM(g.qty_kg) AS total_qty_kg,
        SUM(g.teu) AS total_teu,
        AVG(g.price_usd_per_kg) FILTER (WHERE g.price_usd_per_kg > 0) AS avg_price_usd_per_kg,
        MIN(g.shipment_date) AS first_shipment_date,
        MAX(g.shipment_date) AS last_shipment_date
    FROM global_trades_ledger g
    WHERE g.hs_code_6 IS NOT NULL
    GROUP BY g.reporting_country, g.direction, g.hs_code_6, g.year, g.month
),

-- High-risk shipment counts per grain
risk_shipment_aggs AS (
    SELECT 
        g.reporting_country,
        g.direction,
        g.hs_code_6,
        g.year,
        g.month,
        COUNT(DISTINCT CASE WHEN rs.risk_level IN ('HIGH', 'CRITICAL') THEN g.transaction_id END) AS high_risk_shipments
    FROM global_trades_ledger g
    LEFT JOIN risk_scores rs ON g.transaction_id = rs.entity_id 
        AND rs.entity_type = 'SHIPMENT'
    WHERE g.hs_code_6 IS NOT NULL
    GROUP BY g.reporting_country, g.direction, g.hs_code_6, g.year, g.month
),

-- High-risk buyer counts per grain
risk_buyer_aggs AS (
    SELECT 
        g.reporting_country,
        g.direction,
        g.hs_code_6,
        g.year,
        g.month,
        COUNT(DISTINCT CASE WHEN rs.risk_level IN ('HIGH', 'CRITICAL') THEN g.buyer_uuid END) AS high_risk_buyers
    FROM global_trades_ledger g
    LEFT JOIN risk_scores rs ON g.buyer_uuid = rs.entity_id 
        AND rs.entity_type = 'BUYER'
    WHERE g.hs_code_6 IS NOT NULL AND g.buyer_uuid IS NOT NULL
    GROUP BY g.reporting_country, g.direction, g.hs_code_6, g.year, g.month
)

SELECT 
    -- Grain columns
    la.reporting_country,
    la.direction,
    la.hs_code_6,
    la.year,
    la.month,
    
    -- Volume metrics
    la.shipment_count,
    la.unique_buyers,
    la.unique_suppliers,
    la.total_value_usd,
    la.total_qty_kg,
    la.total_teu,
    la.avg_price_usd_per_kg,
    
    -- Date range
    la.first_shipment_date,
    la.last_shipment_date,
    
    -- Risk summaries
    COALESCE(rsa.high_risk_shipments, 0) AS high_risk_shipments,
    COALESCE(rba.high_risk_buyers, 0) AS high_risk_buyers,
    
    -- Derived metrics
    CASE WHEN la.shipment_count > 0 
         THEN ROUND((la.total_value_usd / la.shipment_count)::numeric, 2) 
         ELSE 0 
    END AS avg_value_per_shipment_usd,
    
    -- Refresh timestamp
    NOW() AS refreshed_at

FROM ledger_aggs la
LEFT JOIN risk_shipment_aggs rsa 
    ON la.reporting_country = rsa.reporting_country
    AND la.direction = rsa.direction
    AND la.hs_code_6 = rsa.hs_code_6
    AND la.year = rsa.year
    AND la.month = rsa.month
LEFT JOIN risk_buyer_aggs rba 
    ON la.reporting_country = rba.reporting_country
    AND la.direction = rba.direction
    AND la.hs_code_6 = rba.hs_code_6
    AND la.year = rba.year
    AND la.month = rba.month;

-- Unique index for fast lookups and REFRESH CONCURRENTLY support
CREATE UNIQUE INDEX idx_mv_chs_grain 
    ON mv_country_hs_month_summary(reporting_country, direction, hs_code_6, year, month);

-- Performance indexes
CREATE INDEX idx_mv_chs_country ON mv_country_hs_month_summary(reporting_country);
CREATE INDEX idx_mv_chs_direction ON mv_country_hs_month_summary(direction);
CREATE INDEX idx_mv_chs_hs6 ON mv_country_hs_month_summary(hs_code_6);
CREATE INDEX idx_mv_chs_period ON mv_country_hs_month_summary(year DESC, month DESC);
CREATE INDEX idx_mv_chs_value ON mv_country_hs_month_summary(total_value_usd DESC);

COMMENT ON MATERIALIZED VIEW mv_country_hs_month_summary IS 'EPIC 7A: Pre-aggregated country/HS/month metrics for fast dashboard queries. Refresh with: REFRESH MATERIALIZED VIEW CONCURRENTLY mv_country_hs_month_summary;';

-- =====================================================================
-- STEP 4: CREATE vw_country_hs_dashboard VIEW
-- =====================================================================

DROP VIEW IF EXISTS vw_country_hs_dashboard CASCADE;

CREATE VIEW vw_country_hs_dashboard AS
WITH country_totals AS (
    SELECT 
        reporting_country,
        direction,
        year,
        month,
        SUM(total_value_usd) AS country_month_total_value
    FROM mv_country_hs_month_summary
    GROUP BY reporting_country, direction, year, month
)
SELECT 
    -- Grain
    mv.reporting_country,
    mv.direction,
    mv.hs_code_6,
    mv.year,
    mv.month,
    
    -- Volume metrics
    mv.shipment_count,
    mv.unique_buyers,
    mv.unique_suppliers,
    mv.total_value_usd,
    mv.total_qty_kg,
    mv.total_teu,
    mv.avg_price_usd_per_kg,
    mv.avg_value_per_shipment_usd,
    
    -- Value share within country/direction/month
    CASE WHEN ct.country_month_total_value > 0 
         THEN ROUND((mv.total_value_usd / ct.country_month_total_value * 100)::numeric, 2)
         ELSE 0 
    END AS value_share_pct,
    
    -- Date range
    mv.first_shipment_date,
    mv.last_shipment_date,
    
    -- Risk summaries
    mv.high_risk_shipments,
    mv.high_risk_buyers,
    CASE WHEN mv.shipment_count > 0 
         THEN ROUND((mv.high_risk_shipments::numeric / mv.shipment_count * 100)::numeric, 1)
         ELSE 0 
    END AS high_risk_shipment_pct,
    
    -- Metadata
    mv.refreshed_at

FROM mv_country_hs_month_summary mv
LEFT JOIN country_totals ct 
    ON mv.reporting_country = ct.reporting_country
    AND mv.direction = ct.direction
    AND mv.year = ct.year
    AND mv.month = ct.month;

COMMENT ON VIEW vw_country_hs_dashboard IS 'EPIC 7A: LLM-friendly dashboard view with value share calculations. Built on mv_country_hs_month_summary.';

-- =====================================================================
-- STEP 5: CREATE HELPER VIEW FOR LLM QUERIES
-- =====================================================================

DROP VIEW IF EXISTS vw_buyer_hs_activity CASCADE;

CREATE VIEW vw_buyer_hs_activity AS
SELECT 
    g.buyer_uuid,
    om.name_normalized AS buyer_name,
    g.hs_code_6,
    g.reporting_country,
    g.direction,
    COUNT(*) AS shipment_count,
    SUM(g.customs_value_usd) AS total_value_usd,
    SUM(g.qty_kg) AS total_qty_kg,
    MIN(g.shipment_date) AS first_shipment_date,
    MAX(g.shipment_date) AS last_shipment_date
FROM global_trades_ledger g
JOIN organizations_master om ON g.buyer_uuid = om.org_uuid
WHERE g.buyer_uuid IS NOT NULL AND g.hs_code_6 IS NOT NULL
GROUP BY g.buyer_uuid, om.name_normalized, g.hs_code_6, g.reporting_country, g.direction;

COMMENT ON VIEW vw_buyer_hs_activity IS 'EPIC 7A: Helper view for querying buyer activity by HS code. Use for "Top buyers for HS X in country Y" queries.';

-- =====================================================================
-- VERIFICATION
-- =====================================================================

DO $$
DECLARE
    v_buyer_360_count INT;
    v_mv_count INT;
    v_dashboard_count INT;
BEGIN
    SELECT COUNT(*) INTO v_buyer_360_count FROM vw_buyer_360;
    SELECT COUNT(*) INTO v_mv_count FROM mv_country_hs_month_summary;
    SELECT COUNT(*) INTO v_dashboard_count FROM vw_country_hs_dashboard;
    
    RAISE NOTICE 'EPIC 7A Migration complete:';
    RAISE NOTICE '  - vw_buyer_360: % rows', v_buyer_360_count;
    RAISE NOTICE '  - mv_country_hs_month_summary: % rows', v_mv_count;
    RAISE NOTICE '  - vw_country_hs_dashboard: % rows', v_dashboard_count;
    RAISE NOTICE '  - pipeline_runs constraint updated for serving_views';
END $$;
