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
    lesson TEXT,                             -- LLM-generated lesson
    braid_level INTEGER DEFAULT 1,           -- Learning hierarchy level
    -- Note: source_strands, clustering_columns moved to module_intelligence
    
    -- CIL (Central Intelligence Layer) FIELDS
    resonance_score FLOAT,                   -- Mathematical resonance score
    strategic_meta_type TEXT,                -- Type of strategic meta-signal
    team_member TEXT,                        -- Team member that created this strand
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
    
    -- MOTIF CARD FIELDS (Pattern Metadata) - High-level only
    motif_id TEXT,                           -- Motif identifier
    motif_name TEXT,                         -- Motif name
    motif_family TEXT,                       -- Motif family classification
    pattern_type TEXT,                       -- Pattern type classification
    -- Note: hypothesis_id, invariants, fails_when, contexts, evidence_refs, why_map, lineage moved to module_intelligence
    
    -- CIL CORE FUNCTIONALITY FIELDS - High-level only
    autonomy_level TEXT,                     -- Agent autonomy: strict|bounded|exploratory
    directive_type TEXT,                     -- CIL directive type: beacon|envelope|seed
    -- Note: mechanism_hypothesis, mechanism_supports, mechanism_fails_when, confluence_graph_data, 
    -- experiment_shape, experiment_grammar, lineage_parent_ids, lineage_mutation_note, 
    -- prioritization_score, directive_content, feedback_request, governance_boundary, 
    -- human_override_data moved to module_intelligence
    
    -- UNIFIED CLUSTERING FIELDS
    status VARCHAR(20) DEFAULT 'active',     -- Strand status: active|inactive|deprecated
    feature_version SMALLINT DEFAULT 1,     -- Feature version for auditable clustering
    derivation_spec_id VARCHAR(100),        -- Derivation spec ID for re-derivation
    
    -- LEARNING SYSTEM FIELDS
    persistence_score DECIMAL(5,4),          -- How reliable/consistent is this pattern (0-1)
    novelty_score DECIMAL(5,4),             -- How unique/new is this pattern (0-1)
    surprise_rating DECIMAL(5,4),           -- How unexpected was this outcome (0-1)
    cluster_key VARCHAR(100),               -- Clustering key for grouping similar strands
    strength_range VARCHAR(20),             -- Pattern strength classification
    rr_profile VARCHAR(20),                 -- Risk/reward profile classification
    market_conditions VARCHAR(20),          -- Market conditions classification
    prediction_data JSONB,                  -- Prediction tracking data
    outcome_data JSONB,                     -- Outcome analysis data
    max_drawdown DECIMAL(10,4),             -- Maximum drawdown for trading strands
    tracking_status VARCHAR(20) DEFAULT 'active', -- Prediction tracking status
    plan_version INT DEFAULT 1,             -- Plan version for evolution tracking
    replaces_id VARCHAR(100),               -- ID of strand this replaces
    replaced_by_id VARCHAR(100),            -- ID of strand that replaces this
    context_vector VECTOR(1536)             -- Vector embedding for similarity search
);

-- =============================================
-- PATTERN EVOLUTION TABLE
-- =============================================

-- Track pattern evolution over time for learning system
CREATE TABLE IF NOT EXISTS pattern_evolution (
    pattern_type VARCHAR(50),
    cluster_key VARCHAR(100),
    version INT,
    success_rate DECIMAL(5,4),
    avg_rr DECIMAL(10,4),
    avg_mdd DECIMAL(10,4),
    sample_size INT,
    last_updated TIMESTAMPTZ,
    PRIMARY KEY (pattern_type, cluster_key, version)
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
CREATE INDEX IF NOT EXISTS idx_ad_strands_team_member ON AD_strands(team_member);
CREATE INDEX IF NOT EXISTS idx_ad_strands_agent_id ON AD_strands(agent_id);
CREATE INDEX IF NOT EXISTS idx_ad_strands_experiment_id ON AD_strands(experiment_id);
CREATE INDEX IF NOT EXISTS idx_ad_strands_doctrine_status ON AD_strands(doctrine_status);

-- Outcome Tracking indexes
CREATE INDEX IF NOT EXISTS idx_ad_strands_prediction_score ON AD_strands(prediction_score DESC);
CREATE INDEX IF NOT EXISTS idx_ad_strands_outcome_score ON AD_strands(outcome_score DESC);
CREATE INDEX IF NOT EXISTS idx_ad_strands_content ON AD_strands USING GIN(content);

-- CIL Core Functionality indexes (high-level only)
CREATE INDEX IF NOT EXISTS idx_ad_strands_autonomy_level ON AD_strands(autonomy_level);
CREATE INDEX IF NOT EXISTS idx_ad_strands_directive_type ON AD_strands(directive_type);

-- Unified Clustering indexes
CREATE INDEX IF NOT EXISTS idx_ad_strands_status ON AD_strands(status);
CREATE INDEX IF NOT EXISTS idx_ad_strands_feature_version ON AD_strands(feature_version);
CREATE INDEX IF NOT EXISTS idx_ad_strands_derivation_spec ON AD_strands(derivation_spec_id);

-- Learning System indexes
CREATE INDEX IF NOT EXISTS idx_ad_strands_persistence_score ON AD_strands(persistence_score);
CREATE INDEX IF NOT EXISTS idx_ad_strands_novelty_score ON AD_strands(novelty_score);
CREATE INDEX IF NOT EXISTS idx_ad_strands_surprise_rating ON AD_strands(surprise_rating);
CREATE INDEX IF NOT EXISTS idx_ad_strands_cluster_key ON AD_strands(cluster_key);
CREATE INDEX IF NOT EXISTS idx_ad_strands_strength_range ON AD_strands(strength_range);
CREATE INDEX IF NOT EXISTS idx_ad_strands_rr_profile ON AD_strands(rr_profile);
CREATE INDEX IF NOT EXISTS idx_ad_strands_market_conditions ON AD_strands(market_conditions);
CREATE INDEX IF NOT EXISTS idx_ad_strands_tracking_status ON AD_strands(tracking_status);
CREATE INDEX IF NOT EXISTS idx_ad_strands_plan_version ON AD_strands(plan_version);
CREATE INDEX IF NOT EXISTS idx_ad_strands_prediction_tracking ON AD_strands(kind, tracking_status) WHERE kind = 'prediction';
CREATE INDEX IF NOT EXISTS idx_ad_strands_context_vector ON AD_strands USING ivfflat (context_vector vector_cosine_ops);

-- Pattern Evolution indexes
CREATE INDEX IF NOT EXISTS idx_pattern_evolution_pattern_type ON pattern_evolution(pattern_type);
CREATE INDEX IF NOT EXISTS idx_pattern_evolution_cluster_key ON pattern_evolution(cluster_key);
CREATE INDEX IF NOT EXISTS idx_pattern_evolution_success_rate ON pattern_evolution(success_rate DESC);
CREATE INDEX IF NOT EXISTS idx_pattern_evolution_last_updated ON pattern_evolution(last_updated DESC);

-- Resonance System indexes
CREATE INDEX IF NOT EXISTS idx_ad_strands_phi ON AD_strands(phi DESC);
CREATE INDEX IF NOT EXISTS idx_ad_strands_rho ON AD_strands(rho DESC);
CREATE INDEX IF NOT EXISTS idx_ad_strands_telemetry ON AD_strands USING GIN(telemetry);
CREATE INDEX IF NOT EXISTS idx_ad_strands_phi_updated ON AD_strands(phi_updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ad_strands_rho_updated ON AD_strands(rho_updated_at DESC);

-- Motif Card indexes (high-level only)
CREATE INDEX IF NOT EXISTS idx_ad_strands_motif_id ON AD_strands(motif_id);
CREATE INDEX IF NOT EXISTS idx_ad_strands_motif_name ON AD_strands(motif_name);
CREATE INDEX IF NOT EXISTS idx_ad_strands_motif_family ON AD_strands(motif_family);
CREATE INDEX IF NOT EXISTS idx_ad_strands_pattern_type ON AD_strands(pattern_type);

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
COMMENT ON COLUMN AD_strands.team_member IS 'Team member that created this strand';
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

-- Motif Card column comments (high-level only)
COMMENT ON COLUMN AD_strands.motif_id IS 'Motif identifier - unique pattern identifier';
COMMENT ON COLUMN AD_strands.motif_name IS 'Motif name - human-readable pattern name';
COMMENT ON COLUMN AD_strands.motif_family IS 'Motif family classification - divergence|volume|correlation|session';
COMMENT ON COLUMN AD_strands.pattern_type IS 'Pattern type classification - volume_spike|divergence|correlation_break|anomaly|session_pattern';
-- Note: hypothesis_id, invariants, fails_when, contexts, evidence_refs, why_map, lineage moved to module_intelligence

-- Unified Clustering column comments
COMMENT ON COLUMN AD_strands.status IS 'Strand status: active|inactive|deprecated - for unified clustering';
COMMENT ON COLUMN AD_strands.feature_version IS 'Feature version for auditable clustering - tracks derivation changes';
COMMENT ON COLUMN AD_strands.derivation_spec_id IS 'Derivation spec ID for re-derivation - enables reproducible clustering';

-- Learning System column comments
COMMENT ON COLUMN AD_strands.persistence_score IS 'How reliable/consistent is this pattern (0-1) - calculated for all strands';
COMMENT ON COLUMN AD_strands.novelty_score IS 'How unique/new is this pattern (0-1) - calculated for all strands';
COMMENT ON COLUMN AD_strands.surprise_rating IS 'How unexpected was this outcome (0-1) - calculated for all strands';
COMMENT ON COLUMN AD_strands.cluster_key IS 'Clustering key for grouping similar strands - used in two-tier clustering';
COMMENT ON COLUMN AD_strands.strength_range IS 'Pattern strength classification - weak|moderate|strong|extreme|anomalous';
COMMENT ON COLUMN AD_strands.rr_profile IS 'Risk/reward profile classification - conservative|moderate|aggressive';
COMMENT ON COLUMN AD_strands.market_conditions IS 'Market conditions classification - bull|bear|sideways|transition|anomaly';
COMMENT ON COLUMN AD_strands.prediction_data IS 'Prediction tracking data - entry_price, target_price, stop_loss, max_time';
COMMENT ON COLUMN AD_strands.outcome_data IS 'Outcome analysis data - final_outcome, max_drawdown, time_to_outcome';
COMMENT ON COLUMN AD_strands.max_drawdown IS 'Maximum drawdown for trading strands - used in R/R optimization';
COMMENT ON COLUMN AD_strands.tracking_status IS 'Prediction tracking status - active|completed|expired|cancelled';
COMMENT ON COLUMN AD_strands.plan_version IS 'Plan version for evolution tracking - enables version control';
COMMENT ON COLUMN AD_strands.replaces_id IS 'ID of strand this replaces - tracks evolution lineage';
COMMENT ON COLUMN AD_strands.replaced_by_id IS 'ID of strand that replaces this - tracks evolution lineage';
COMMENT ON COLUMN AD_strands.context_vector IS 'Vector embedding for similarity search - 1536 dimensions for OpenAI embeddings';

-- Pattern Evolution table comments
COMMENT ON TABLE pattern_evolution IS 'Track pattern evolution over time for learning system - success rates, R/R ratios, drawdowns';
COMMENT ON COLUMN pattern_evolution.pattern_type IS 'Type of pattern being tracked - volume_spike|divergence|correlation_break';
COMMENT ON COLUMN pattern_evolution.cluster_key IS 'Clustering key for this pattern group - enables pattern-specific evolution';
COMMENT ON COLUMN pattern_evolution.version IS 'Version number for this pattern evolution - tracks improvements over time';
COMMENT ON COLUMN pattern_evolution.success_rate IS 'Success rate for this pattern version (0-1) - tracks prediction accuracy';
COMMENT ON COLUMN pattern_evolution.avg_rr IS 'Average risk/reward ratio for this pattern version - tracks profitability';
COMMENT ON COLUMN pattern_evolution.avg_mdd IS 'Average maximum drawdown for this pattern version - tracks risk';
COMMENT ON COLUMN pattern_evolution.sample_size IS 'Number of samples used to calculate these metrics - tracks statistical significance';
COMMENT ON COLUMN pattern_evolution.last_updated IS 'When this pattern version was last updated - tracks evolution timeline';
