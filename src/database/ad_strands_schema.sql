-- ad_strands Database Schema (Cleaned for Lowcap System)
-- SINGLE STRANDS TABLE: All strand types (social_lowcap, decision_lowcap, pm_action, position_closed) use this table with different `kind` values
-- Legacy CIL/RDI/CTP columns removed - focused on lowcap trading system

-- Drop existing tables if they exist (for clean cutover)
DROP TABLE IF EXISTS ad_strands CASCADE;
DROP TABLE IF EXISTS module_resonance_scores CASCADE;
DROP TABLE IF EXISTS pattern_evolution CASCADE;

-- Drop legacy views
DROP VIEW IF EXISTS rdi_strands CASCADE;
DROP VIEW IF EXISTS cil_strands CASCADE;
DROP VIEW IF EXISTS ctp_strands CASCADE;
DROP VIEW IF EXISTS dm_strands CASCADE;
DROP VIEW IF EXISTS td_strands CASCADE;
DROP VIEW IF EXISTS braid_candidates CASCADE;

-- Create cleaned ad_strands table (lowcap system only)
CREATE TABLE ad_strands (
    -- REQUIRED COMMUNICATION FIELDS
    id TEXT PRIMARY KEY,                     -- ULID
    module TEXT DEFAULT 'alpha',             -- Module identifier ('social_ingest', 'decision_maker_lowcap', 'pm', etc.)
    kind TEXT,                               -- Strand type: 'social_lowcap'|'decision_lowcap'|'pm_action'|'position_closed'
    symbol TEXT,                             -- Trading symbol/ticker
    timeframe TEXT,                          -- '1m'|'5m'|'15m'|'1h'|'4h'|'1d'
    session_bucket TEXT,                     -- Session identifier
    tags JSONB,                              -- Communication tags (REQUIRED)
    target_agent TEXT,                       -- Target agent for communication
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- STRAND HIERARCHY FIELDS
    position_id TEXT,                        -- Position ID (for PM strands, can be backfilled to social/decision strands)
    trade_id UUID,                           -- Trade cycle identifier (links pm_action strands to position_closed strands)
    parent_id TEXT,                          -- Linkage to parent strand (e.g., decision_lowcap → social_lowcap)
    
    -- DATA FIELDS
    signal_pack JSONB,                       -- Structured token/venue/curator data + identification_source (LLM-ready)
    content JSONB,                           -- Module-specific operational data (PM action details, position data, decision reasoning, etc.)
    module_intelligence JSONB,               -- Module-specific intelligence
    regime_context JSONB,                    -- Regime context (for future regime-based learning)
    
    -- METADATA
    status VARCHAR(20) DEFAULT 'active',     -- Strand status: active|inactive|deprecated
    metadata JSONB,                          -- For future extensibility
    context_vector VECTOR(1536)              -- Vector embedding for similarity search (future use)
);

-- =============================================
-- INDEXES
-- =============================================

-- Core indexes for fast queries
CREATE INDEX idx_ad_strands_symbol_time ON ad_strands(symbol, created_at DESC);
CREATE INDEX idx_ad_strands_position_id ON ad_strands(position_id);
CREATE INDEX idx_ad_strands_trade_id ON ad_strands(trade_id);
CREATE INDEX idx_ad_strands_kind ON ad_strands(kind);
CREATE INDEX idx_ad_strands_parent_id ON ad_strands(parent_id);
CREATE INDEX idx_ad_strands_tags ON ad_strands USING GIN(tags);
CREATE INDEX idx_ad_strands_target_agent ON ad_strands(target_agent);
CREATE INDEX idx_ad_strands_created_at ON ad_strands(created_at DESC);
CREATE INDEX idx_ad_strands_status ON ad_strands(status);

-- JSONB indexes for fast queries on structured data
CREATE INDEX idx_ad_strands_content ON ad_strands USING GIN(content);
CREATE INDEX idx_ad_strands_signal_pack ON ad_strands USING GIN(signal_pack);
CREATE INDEX idx_ad_strands_module_intelligence ON ad_strands USING GIN(module_intelligence);
CREATE INDEX idx_ad_strands_regime_context ON ad_strands USING GIN(regime_context);

-- Vector similarity search index (for future use)
CREATE INDEX idx_ad_strands_context_vector ON ad_strands USING ivfflat (context_vector vector_cosine_ops);

-- =============================================
-- VIEWS FOR EASY QUERYING (Lowcap System Only)
-- =============================================

-- Lowcap-specific views
CREATE VIEW social_lowcap_strands AS
SELECT * FROM ad_strands WHERE kind = 'social_lowcap';

CREATE VIEW decision_lowcap_strands AS
SELECT * FROM ad_strands WHERE kind = 'decision_lowcap';

CREATE VIEW pm_action_strands AS
SELECT * FROM ad_strands WHERE kind = 'pm_action';

CREATE VIEW position_closed_strands AS
SELECT * FROM ad_strands WHERE kind = 'position_closed';

-- =============================================
-- COMMENTS AND DOCUMENTATION
-- =============================================

COMMENT ON TABLE ad_strands IS 'SINGLE STRANDS TABLE: All strand types use this table with different kind values (social_lowcap, decision_lowcap, pm_action, position_closed). Legacy CIL/RDI/CTP columns removed.';
COMMENT ON COLUMN ad_strands.kind IS 'Strand type: social_lowcap, decision_lowcap, pm_action, position_closed';
COMMENT ON COLUMN ad_strands.module IS 'Module identifier: social_ingest, decision_maker_lowcap, pm, etc.';
COMMENT ON COLUMN ad_strands.position_id IS 'Position ID - for PM strands (pm_action, position_closed), can be backfilled to social_lowcap and decision_lowcap strands after position creation';
COMMENT ON COLUMN ad_strands.parent_id IS 'Link to parent strand (e.g., decision_lowcap.parent_id → social_lowcap.id)';
COMMENT ON COLUMN ad_strands.signal_pack IS 'Structured token/venue/curator data + identification_source - LLM-ready structured data';
COMMENT ON COLUMN ad_strands.content IS 'Module-specific operational data (PM action details, position data, decision reasoning, etc.)';
COMMENT ON COLUMN ad_strands.module_intelligence IS 'Module-specific intelligence data';
COMMENT ON COLUMN ad_strands.regime_context IS 'Regime context for future regime-based learning';
COMMENT ON COLUMN ad_strands.context_vector IS 'Vector embedding for similarity search (future use)';

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO your_user;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO your_user;
