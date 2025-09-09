-- Alpha Detector Module Database Schema
-- Phase 1: Foundation - Complete AD_strands table with all required columns

-- =============================================
-- ALPHA DETECTOR STRANDS TABLE
-- =============================================

-- AD_strands table - Alpha Detector's main data table
CREATE TABLE IF NOT EXISTS AD_strands (
    -- REQUIRED COMMUNICATION FIELDS (DO NOT MODIFY)
    id TEXT PRIMARY KEY,                     -- ULID
    module TEXT DEFAULT 'alpha',             -- Module identifier
    kind TEXT,                               -- 'signal'|'trading_plan'|'intelligence'|'braid'|'meta_braid'|'meta2_braid'
    symbol TEXT,                             -- Trading symbol
    timeframe TEXT,                          -- '1m'|'5m'|'15m'|'1h'|'4h'|'1d'
    session_bucket TEXT,                     -- Session identifier
    regime TEXT,                             -- Market regime
    tags JSONB,                              -- Communication tags (REQUIRED)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- STRAND HIERARCHY FIELDS (Phase 4+)
    lifecycle_id TEXT,                       -- Thread identifier
    parent_id TEXT,                          -- Linkage to parent strand
    
    -- SIGNAL DATA
    sig_sigma FLOAT8,                        -- Signal strength (0-1)
    sig_confidence FLOAT8,                   -- Signal confidence (0-1)
    confidence FLOAT8,                       -- Generic confidence score (0-1) - for patterns, intelligence, etc.
    sig_direction TEXT,                      -- 'long'|'short'|'neutral'
    
    -- TRADING PLAN DATA
    trading_plan JSONB,                      -- Complete trading plan OR braid lesson
    signal_pack JSONB,                       -- Signal pack for LLM consumption
    
    -- INTELLIGENCE DATA
    dsi_evidence JSONB,                      -- DSI evidence
    regime_context JSONB,                    -- Regime context
    event_context JSONB,                     -- Event context
    
    -- MODULE INTELLIGENCE
    module_intelligence JSONB,               -- Module-specific intelligence
    curator_feedback JSONB,                  -- Curator evaluation results
    
    -- LEARNING FIELDS (Phase 4+)
    accumulated_score FLOAT8,                -- Accumulated performance score
    source_strands JSONB,                    -- Source strands for learning
    clustering_columns JSONB,                -- Columns for clustering
    lesson TEXT,                             -- LLM-generated lesson
    braid_level INTEGER DEFAULT 1,           -- Learning hierarchy level
    
    -- CIL (Central Intelligence Layer) FIELDS
    resonance_score FLOAT,                   -- Mathematical resonance score
    strategic_meta_type TEXT,                -- Type of strategic meta-signal
    cil_team_member TEXT,                    -- CIL team member that created this strand
    agent_id TEXT,                           -- Agent team identifier: raw_data_intelligence|decision_maker|trader|central_intelligence_layer
    experiment_id TEXT,                      -- Experiment ID for tracking
    doctrine_status TEXT,                    -- Doctrine status: provisional|affirmed|retired|contraindicated
    
    -- OUTCOME TRACKING FIELDS
    prediction_score FLOAT,                  -- How accurate was the prediction (0.0-1.0)
    outcome_score FLOAT,                     -- How well was it executed (0.0-1.0)
    content JSONB,                           -- Generic message content for communication
    
    -- RESONANCE SYSTEM FIELDS (Mathematical Resonance)
    phi FLOAT8,                              -- Mathematical resonance field strength (φ)
    rho FLOAT8,                              -- Mathematical resonance density (ρ)
    telemetry JSONB,                         -- Resonance metrics: sr, cr, xr, surprise
    phi_updated_at TIMESTAMPTZ,              -- Timestamp for phi updates
    rho_updated_at TIMESTAMPTZ,              -- Timestamp for rho updates
    
    -- MOTIF CARD FIELDS (Pattern Metadata)
    motif_id TEXT,                           -- Motif identifier
    motif_name TEXT,                         -- Motif name
    motif_family TEXT,                       -- Motif family classification
    hypothesis_id TEXT,                      -- Hypothesis identifier for experiments
    invariants JSONB,                        -- Pattern invariants
    fails_when JSONB,                        -- Failure conditions
    contexts JSONB,                          -- Pattern contexts
    evidence_refs JSONB,                     -- Evidence references
    why_map JSONB,                           -- Why-map data
    lineage JSONB,                           -- Pattern lineage
    
    -- CIL CORE FUNCTIONALITY FIELDS
    mechanism_hypothesis TEXT,               -- Why does this work? (Why-Map)
    mechanism_supports JSONB,                -- Evidence motifs supporting hypothesis
    mechanism_fails_when JSONB,              -- Counter-conditions when it fails
    confluence_graph_data JSONB,             -- Cross-agent motif data
    experiment_shape TEXT,                   -- Canonical experiment shape: durability|stack|lead_lag|ablation|boundary
    experiment_grammar JSONB,                -- Experiment design parameters
    lineage_parent_ids JSONB,                -- Parent strand IDs for lineage tracking
    lineage_mutation_note TEXT,              -- How this variant was created
    prioritization_score FLOAT,              -- Resonance-driven prioritization score
    autonomy_level TEXT,                     -- Agent autonomy: strict|bounded|exploratory
    directive_type TEXT,                     -- CIL directive type: beacon|envelope|seed
    directive_content JSONB,                 -- Directive content and parameters
    feedback_request JSONB,                  -- Feedback requirements for agents
    governance_boundary TEXT,                -- Governance boundary classification
    human_override_data JSONB                -- Human override information
);

-- =============================================
-- INDEXES
-- =============================================

-- AD_strands indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_ad_strands_symbol_time ON AD_strands(symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ad_strands_lifecycle ON AD_strands(lifecycle_id);
CREATE INDEX IF NOT EXISTS idx_ad_strands_kind ON AD_strands(kind);
CREATE INDEX IF NOT EXISTS idx_ad_strands_sigma ON AD_strands(sig_sigma);
CREATE INDEX IF NOT EXISTS idx_ad_strands_braid_level ON AD_strands((trading_plan->>'braid_level'));
CREATE INDEX IF NOT EXISTS idx_ad_strands_tags ON AD_strands USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_ad_strands_confidence ON AD_strands(sig_confidence DESC);
CREATE INDEX IF NOT EXISTS idx_ad_strands_generic_confidence ON AD_strands(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_ad_strands_created_at ON AD_strands(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ad_strands_direction ON AD_strands(sig_direction);

-- CIL (Central Intelligence Layer) indexes
CREATE INDEX IF NOT EXISTS idx_ad_strands_resonance ON AD_strands(resonance_score DESC);
CREATE INDEX IF NOT EXISTS idx_ad_strands_strategic_meta ON AD_strands(strategic_meta_type);
CREATE INDEX IF NOT EXISTS idx_ad_strands_cil_member ON AD_strands(cil_team_member);
CREATE INDEX IF NOT EXISTS idx_ad_strands_agent_id ON AD_strands(agent_id);
CREATE INDEX IF NOT EXISTS idx_ad_strands_experiment_id ON AD_strands(experiment_id);
CREATE INDEX IF NOT EXISTS idx_ad_strands_doctrine_status ON AD_strands(doctrine_status);

-- Outcome Tracking indexes
CREATE INDEX IF NOT EXISTS idx_ad_strands_prediction_score ON AD_strands(prediction_score DESC);
CREATE INDEX IF NOT EXISTS idx_ad_strands_outcome_score ON AD_strands(outcome_score DESC);
CREATE INDEX IF NOT EXISTS idx_ad_strands_content ON AD_strands USING GIN(content);

-- CIL Core Functionality indexes
CREATE INDEX IF NOT EXISTS idx_ad_strands_mechanism_hypothesis ON AD_strands(mechanism_hypothesis);
CREATE INDEX IF NOT EXISTS idx_ad_strands_experiment_shape ON AD_strands(experiment_shape);
CREATE INDEX IF NOT EXISTS idx_ad_strands_prioritization_score ON AD_strands(prioritization_score DESC);
CREATE INDEX IF NOT EXISTS idx_ad_strands_autonomy_level ON AD_strands(autonomy_level);
CREATE INDEX IF NOT EXISTS idx_ad_strands_directive_type ON AD_strands(directive_type);
CREATE INDEX IF NOT EXISTS idx_ad_strands_governance_boundary ON AD_strands(governance_boundary);
CREATE INDEX IF NOT EXISTS idx_ad_strands_confluence_graph ON AD_strands USING GIN(confluence_graph_data);
CREATE INDEX IF NOT EXISTS idx_ad_strands_lineage_parents ON AD_strands USING GIN(lineage_parent_ids);

-- Resonance System indexes
CREATE INDEX IF NOT EXISTS idx_ad_strands_phi ON AD_strands(phi DESC);
CREATE INDEX IF NOT EXISTS idx_ad_strands_rho ON AD_strands(rho DESC);
CREATE INDEX IF NOT EXISTS idx_ad_strands_telemetry ON AD_strands USING GIN(telemetry);
CREATE INDEX IF NOT EXISTS idx_ad_strands_phi_updated ON AD_strands(phi_updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ad_strands_rho_updated ON AD_strands(rho_updated_at DESC);

-- Motif Card indexes
CREATE INDEX IF NOT EXISTS idx_ad_strands_motif_id ON AD_strands(motif_id);
CREATE INDEX IF NOT EXISTS idx_ad_strands_motif_name ON AD_strands(motif_name);
CREATE INDEX IF NOT EXISTS idx_ad_strands_motif_family ON AD_strands(motif_family);
CREATE INDEX IF NOT EXISTS idx_ad_strands_hypothesis_id ON AD_strands(hypothesis_id);
CREATE INDEX IF NOT EXISTS idx_ad_strands_invariants ON AD_strands USING GIN(invariants);
CREATE INDEX IF NOT EXISTS idx_ad_strands_fails_when ON AD_strands USING GIN(fails_when);
CREATE INDEX IF NOT EXISTS idx_ad_strands_contexts ON AD_strands USING GIN(contexts);
CREATE INDEX IF NOT EXISTS idx_ad_strands_evidence_refs ON AD_strands USING GIN(evidence_refs);
CREATE INDEX IF NOT EXISTS idx_ad_strands_why_map ON AD_strands USING GIN(why_map);
CREATE INDEX IF NOT EXISTS idx_ad_strands_lineage ON AD_strands USING GIN(lineage);

-- =============================================
-- TRIGGERS FOR COMMUNICATION
-- =============================================

-- Function to notify other modules when AD_strands is updated
CREATE OR REPLACE FUNCTION notify_ad_strands_update()
RETURNS TRIGGER AS $$
BEGIN
    -- Notify Decision Maker when Alpha Detector creates a trading plan
    IF NEW.tags ? 'decision_maker' THEN
        PERFORM pg_notify('ad_to_dm', json_build_object(
            'strand_id', NEW.id,
            'symbol', NEW.symbol,
            'trading_plan', NEW.trading_plan,
            'tags', NEW.tags,
            'created_at', NEW.created_at
        )::text);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger on AD_strands table
CREATE TRIGGER ad_strands_notify_trigger
    AFTER INSERT OR UPDATE ON AD_strands
    FOR EACH ROW
    EXECUTE FUNCTION notify_ad_strands_update();

-- =============================================
-- COMMENTS
-- =============================================

COMMENT ON TABLE AD_strands IS 'Alpha Detector main data table - stores trading plans, signals, and learning strands';
COMMENT ON COLUMN AD_strands.tags IS 'Communication tags - used to notify other modules';
COMMENT ON COLUMN AD_strands.kind IS 'Strand type: signal|trading_plan|intelligence|braid|meta_braid|meta2_braid';
COMMENT ON COLUMN AD_strands.confidence IS 'Generic confidence score (0-1) - used for patterns, intelligence, and other non-signal confidence measures';
COMMENT ON COLUMN AD_strands.lifecycle_id IS 'Thread identifier for grouping related strands';
COMMENT ON COLUMN AD_strands.parent_id IS 'Linkage to parent strand for hierarchy';
COMMENT ON COLUMN AD_strands.trading_plan IS 'Complete trading plan OR braid lesson';
COMMENT ON COLUMN AD_strands.signal_pack IS 'Signal package with all extracted features for LLM consumption';
COMMENT ON COLUMN AD_strands.dsi_evidence IS 'Deep Signal Intelligence evidence (Phase 2+)';
COMMENT ON COLUMN AD_strands.module_intelligence IS 'Module-specific intelligence (Phase 3+)';
COMMENT ON COLUMN AD_strands.accumulated_score IS 'Accumulated performance score for learning (Phase 4+)';
COMMENT ON COLUMN AD_strands.braid_level IS 'Learning hierarchy level: 1=strand, 2=braid, 3=meta-braid, 4=meta2-braid';
COMMENT ON COLUMN AD_strands.resonance_score IS 'Mathematical resonance score for organic growth (CIL)';
COMMENT ON COLUMN AD_strands.strategic_meta_type IS 'Type of strategic meta-signal: confluence|experiment|doctrine|plan|warning';
COMMENT ON COLUMN AD_strands.cil_team_member IS 'CIL team member that created this strand';
COMMENT ON COLUMN AD_strands.agent_id IS 'Agent team identifier: raw_data_intelligence|decision_maker|trader|central_intelligence_layer';
COMMENT ON COLUMN AD_strands.experiment_id IS 'Experiment ID for tracking strategic experiments';
COMMENT ON COLUMN AD_strands.doctrine_status IS 'Doctrine status: provisional|affirmed|retired|contraindicated';

-- Outcome Tracking column comments
COMMENT ON COLUMN AD_strands.prediction_score IS 'How accurate was the prediction (0.0-1.0) - tracks prediction vs market outcome';
COMMENT ON COLUMN AD_strands.outcome_score IS 'How well was it executed (0.0-1.0) - tracks execution quality for trades';
COMMENT ON COLUMN AD_strands.content IS 'Generic message content for inter-agent communication';

-- Resonance System column comments
COMMENT ON COLUMN AD_strands.phi IS 'Mathematical resonance field strength (φ) - consciousness acceleration';
COMMENT ON COLUMN AD_strands.rho IS 'Mathematical resonance density (ρ) - fractal self-similarity';
COMMENT ON COLUMN AD_strands.telemetry IS 'Resonance metrics: sr (success rate), cr (confirmation rate), xr (contradiction rate), surprise';
COMMENT ON COLUMN AD_strands.phi_updated_at IS 'Timestamp for phi updates - tracks resonance field changes';
COMMENT ON COLUMN AD_strands.rho_updated_at IS 'Timestamp for rho updates - tracks resonance density changes';

-- Motif Card column comments
COMMENT ON COLUMN AD_strands.motif_id IS 'Motif identifier - unique pattern identifier';
COMMENT ON COLUMN AD_strands.motif_name IS 'Motif name - human-readable pattern name';
COMMENT ON COLUMN AD_strands.motif_family IS 'Motif family classification - divergence|volume|correlation|session';
COMMENT ON COLUMN AD_strands.hypothesis_id IS 'Hypothesis identifier for experiment tracking';
COMMENT ON COLUMN AD_strands.invariants IS 'Pattern invariants - what stays the same across contexts';
COMMENT ON COLUMN AD_strands.fails_when IS 'Failure conditions - when this pattern breaks down';
COMMENT ON COLUMN AD_strands.contexts IS 'Pattern contexts - market conditions where this works';
COMMENT ON COLUMN AD_strands.evidence_refs IS 'Evidence references - supporting strand IDs';
COMMENT ON COLUMN AD_strands.why_map IS 'Why-map data - causal reasoning for pattern success';
COMMENT ON COLUMN AD_strands.lineage IS 'Pattern lineage - how this pattern evolved from others';
