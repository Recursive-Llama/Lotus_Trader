-- Alpha Detector Module Database Schema
-- Phase 1: Foundation - Complete AD_strands table with all required columns

-- =============================================
-- AD STRANDS TABLE
-- =============================================


-- Drop existing tables if they exist (for clean cutover)
DROP TABLE IF EXISTS learning_queue CASCADE;
DROP TABLE IF EXISTS AD_strands CASCADE;
DROP TABLE IF EXISTS learning_braids CASCADE;
DROP TABLE IF EXISTS module_resonance_scores CASCADE;
DROP TABLE IF EXISTS pattern_evolution CASCADE;

-- Create enhanced AD_strands table with all clustering infrastructure + module-specific resonance
CREATE TABLE AD_strands (
    -- REQUIRED COMMUNICATION FIELDS (DO NOT MODIFY)
    id TEXT PRIMARY KEY,                     -- ULID
    module TEXT DEFAULT 'alpha',             -- Module identifier
    kind TEXT,                               -- 'pattern'|'prediction_review'|'conditional_trading_plan'|'trading_decision'|'execution_outcome'|'braid'|'meta_braid'|'meta2_braid'
    symbol TEXT,                             -- Trading symbol
    timeframe TEXT,                          -- '1m'|'5m'|'15m'|'1h'|'4h'|'1d'
    session_bucket TEXT,                     -- Session identifier
    regime TEXT,                             -- Market regime
    tags JSONB,                              -- Communication tags (REQUIRED)
    target_agent TEXT,                       -- Target agent for communication
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- STRAND HIERARCHY FIELDS
    lifecycle_id TEXT,                       -- Thread identifier
    parent_id TEXT,                          -- Linkage to parent strand
    
    -- SIGNAL DATA (RDI)
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
    
    -- MODULE INTELLIGENCE (RDI patterns, CIL predictions, etc.)
    module_intelligence JSONB,               -- Module-specific intelligence
    curator_feedback JSONB,                  -- Curator evaluation results
    
    -- LEARNING FIELDS
    accumulated_score FLOAT8,                -- Accumulated performance score
    lesson TEXT,                             -- LLM-generated lesson
    braid_level INTEGER DEFAULT 1,           -- Learning hierarchy level
    
    -- CIL (Central Intelligence Layer) FIELDS
    resonance_score FLOAT,                   -- Mathematical resonance score
    strategic_meta_type TEXT,                -- Type of strategic meta-signal
    team_member TEXT,                        -- Team member that created this strand
    agent_id TEXT,                           -- Agent team identifier: raw_data_intelligence|decision_maker|trader|central_intelligence_layer
    experiment_id TEXT,                      -- Experiment ID for tracking
    doctrine_status TEXT,                    -- Doctrine status: provisional|affirmed|retired|contraindicated
    
    -- OUTCOME TRACKING FIELDS (CIL predictions)
    prediction_score FLOAT,                  -- How accurate was the prediction (0.0-1.0)
    outcome_score FLOAT,                     -- How well was it executed (0.0-1.0)
    content JSONB,                           -- Generic message content for communication
    
    -- RESONANCE SYSTEM FIELDS (Mathematical Resonance) - ENHANCED
    telemetry JSONB,                         -- Resonance metrics: sr, cr, xr, surprise
    resonance_updated_at TIMESTAMPTZ,        -- Timestamp for resonance updates
    
    -- MOTIF CARD FIELDS (Pattern Metadata) - RDI
    motif_id TEXT,                           -- Motif identifier
    motif_name TEXT,                         -- Motif name
    motif_family TEXT,                       -- Motif family classification
    pattern_type TEXT,                       -- Pattern type classification
    
    -- CIL CORE FUNCTIONALITY FIELDS
    autonomy_level TEXT,                     -- Agent autonomy: strict|bounded|exploratory
    directive_type TEXT,                     -- CIL directive type: beacon|envelope|seed
    
    -- UNIFIED CLUSTERING FIELDS (PRESERVED - ESSENTIAL)
    status VARCHAR(20) DEFAULT 'active',     -- Strand status: active|inactive|deprecated
    feature_version SMALLINT DEFAULT 1,     -- Feature version for auditable clustering
    derivation_spec_id VARCHAR(100),        -- Derivation spec ID for re-derivation
    
    -- LEARNING SYSTEM FIELDS (PRESERVED - ESSENTIAL)
    persistence_score DECIMAL(5,4),          -- How reliable/consistent is this pattern (0-1)
    novelty_score DECIMAL(5,4),             -- How unique/new is this pattern (0-1)
    surprise_rating DECIMAL(5,4),           -- How unexpected was this outcome (0-1)
    cluster_key JSONB,                       -- Clustering assignments: [{"cluster_type": "asset", "cluster_key": "BTC", "braid_level": 1, "consumed": false}]
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
    context_vector VECTOR(1536),            -- Vector embedding for similarity search
    
    -- MODULE-SPECIFIC RESONANCE SCORES (NEW)
    resonance_scores JSONB,                 -- Calculated resonance values: {"phi": 1.0, "rho": 1.0, "theta": 1.0, "omega": 1.0, "selection_score": 1.0}
    historical_metrics JSONB,               -- Historical accuracy, performance data for improvement tracking
    
    -- LEARNING SYSTEM FIELDS (ENHANCED)
    processed BOOLEAN DEFAULT FALSE,        -- Learning system processing status
    braid_candidate BOOLEAN DEFAULT FALSE,  -- Candidate for braid creation
    quality_score FLOAT,                    -- Overall quality score
    
    -- Metadata
    metadata JSONB
);

-- Create learning queue table
CREATE TABLE learning_queue (
    id SERIAL PRIMARY KEY,
    strand_id TEXT NOT NULL REFERENCES AD_strands(id) ON DELETE CASCADE,
    strand_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

-- Create braids table for higher-level learning
CREATE TABLE learning_braids (
    id TEXT PRIMARY KEY,
    level INTEGER NOT NULL, -- 2, 3, 4, etc.
    strand_type TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Braid content
    content JSONB, -- Synthesized content from multiple strands
    source_strand_ids TEXT[], -- IDs of strands that created this braid
    
    -- Quality metrics
    quality_score FLOAT,
    confidence FLOAT,
    significance FLOAT,
    
    -- Resonance scores
    resonance_scores JSONB,
    
    -- Metadata
    metadata JSONB
);

-- Create module resonance scores table for detailed tracking
CREATE TABLE module_resonance_scores (
    id SERIAL PRIMARY KEY,
    module_type TEXT NOT NULL, -- 'rdi', 'cil', 'ctp', 'dm', 'td'
    strand_id TEXT NOT NULL REFERENCES AD_strands(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Resonance values
    phi FLOAT NOT NULL, -- Fractal self-similarity
    rho FLOAT NOT NULL, -- Recursive feedback
    theta FLOAT NOT NULL, -- Collective intelligence
    omega FLOAT NOT NULL, -- Meta-evolution
    
    -- Selection score
    selection_score FLOAT NOT NULL,
    
    -- Module-specific metrics
    module_metrics JSONB,
    
    -- Historical comparison
    historical_phi FLOAT,
    historical_rho FLOAT,
    historical_theta FLOAT,
    historical_omega FLOAT,
    
    -- Improvement rates
    phi_improvement FLOAT,
    rho_improvement FLOAT,
    theta_improvement FLOAT,
    omega_improvement FLOAT
);

-- Track pattern evolution over time for learning system
CREATE TABLE pattern_evolution (
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
-- INDEXES (PRESERVED + ENHANCED)
-- =============================================

-- AD_strands indexes for fast queries (PRESERVED)
CREATE INDEX idx_ad_strands_symbol_time ON AD_strands(symbol, created_at DESC);
CREATE INDEX idx_ad_strands_lifecycle ON AD_strands(lifecycle_id);
CREATE INDEX idx_ad_strands_kind ON AD_strands(kind);
CREATE INDEX idx_ad_strands_sigma ON AD_strands(sig_sigma);
CREATE INDEX idx_ad_strands_braid_level ON AD_strands((trading_plan->>'braid_level'));
CREATE INDEX idx_ad_strands_tags ON AD_strands USING GIN(tags);
CREATE INDEX idx_ad_strands_target_agent ON AD_strands(target_agent);
CREATE INDEX idx_ad_strands_confidence ON AD_strands(sig_confidence DESC);
CREATE INDEX idx_ad_strands_generic_confidence ON AD_strands(confidence DESC);
CREATE INDEX idx_ad_strands_created_at ON AD_strands(created_at DESC);
CREATE INDEX idx_ad_strands_direction ON AD_strands(sig_direction);

-- CIL (Central Intelligence Layer) indexes (PRESERVED)
CREATE INDEX idx_ad_strands_resonance ON AD_strands(resonance_score DESC);
CREATE INDEX idx_ad_strands_strategic_meta ON AD_strands(strategic_meta_type);
CREATE INDEX idx_ad_strands_team_member ON AD_strands(team_member);
CREATE INDEX idx_ad_strands_agent_id ON AD_strands(agent_id);
CREATE INDEX idx_ad_strands_experiment_id ON AD_strands(experiment_id);
CREATE INDEX idx_ad_strands_doctrine_status ON AD_strands(doctrine_status);

-- Outcome Tracking indexes (PRESERVED)
CREATE INDEX idx_ad_strands_prediction_score ON AD_strands(prediction_score DESC);
CREATE INDEX idx_ad_strands_outcome_score ON AD_strands(outcome_score DESC);
CREATE INDEX idx_ad_strands_content ON AD_strands USING GIN(content);

-- CIL Core Functionality indexes (PRESERVED)
CREATE INDEX idx_ad_strands_autonomy_level ON AD_strands(autonomy_level);
CREATE INDEX idx_ad_strands_directive_type ON AD_strands(directive_type);

-- Unified Clustering indexes (PRESERVED - ESSENTIAL)
CREATE INDEX idx_ad_strands_status ON AD_strands(status);
CREATE INDEX idx_ad_strands_feature_version ON AD_strands(feature_version);
CREATE INDEX idx_ad_strands_derivation_spec ON AD_strands(derivation_spec_id);

-- Learning System indexes (PRESERVED - ESSENTIAL)
CREATE INDEX idx_ad_strands_persistence_score ON AD_strands(persistence_score);
CREATE INDEX idx_ad_strands_novelty_score ON AD_strands(novelty_score);
CREATE INDEX idx_ad_strands_surprise_rating ON AD_strands(surprise_rating);
CREATE INDEX idx_ad_strands_cluster_key_gin ON AD_strands USING GIN(cluster_key);
CREATE INDEX idx_ad_strands_strength_range ON AD_strands(strength_range);
CREATE INDEX idx_ad_strands_rr_profile ON AD_strands(rr_profile);
CREATE INDEX idx_ad_strands_market_conditions ON AD_strands(market_conditions);
CREATE INDEX idx_ad_strands_tracking_status ON AD_strands(tracking_status);
CREATE INDEX idx_ad_strands_plan_version ON AD_strands(plan_version);
CREATE INDEX idx_ad_strands_prediction_tracking ON AD_strands(kind, tracking_status) WHERE kind = 'prediction';
CREATE INDEX idx_ad_strands_context_vector ON AD_strands USING ivfflat (context_vector vector_cosine_ops);

-- Resonance System indexes (ENHANCED)
CREATE INDEX idx_ad_strands_telemetry ON AD_strands USING GIN(telemetry);
CREATE INDEX idx_ad_strands_resonance_updated ON AD_strands(resonance_updated_at DESC);

-- Motif Card indexes (PRESERVED)
CREATE INDEX idx_ad_strands_motif_id ON AD_strands(motif_id);
CREATE INDEX idx_ad_strands_motif_name ON AD_strands(motif_name);
CREATE INDEX idx_ad_strands_motif_family ON AD_strands(motif_family);
CREATE INDEX idx_ad_strands_pattern_type ON AD_strands(pattern_type);

-- NEW: Module-specific resonance indexes
CREATE INDEX idx_ad_strands_resonance_scores ON AD_strands USING GIN(resonance_scores);
CREATE INDEX idx_ad_strands_historical_metrics ON AD_strands USING GIN(historical_metrics);
CREATE INDEX idx_ad_strands_processed ON AD_strands(processed);
CREATE INDEX idx_ad_strands_braid_candidate ON AD_strands(braid_candidate);
CREATE INDEX idx_ad_strands_quality_score ON AD_strands(quality_score);

-- Learning queue indexes
CREATE INDEX idx_learning_queue_status ON learning_queue(status);
CREATE INDEX idx_learning_queue_created_at ON learning_queue(created_at);

-- Learning braids indexes
CREATE INDEX idx_learning_braids_level ON learning_braids(level);
CREATE INDEX idx_learning_braids_strand_type ON learning_braids(strand_type);
CREATE INDEX idx_learning_braids_quality_score ON learning_braids(quality_score);

-- Module resonance scores indexes
CREATE INDEX idx_module_resonance_scores_module_type ON module_resonance_scores(module_type);
CREATE INDEX idx_module_resonance_scores_strand_id ON module_resonance_scores(strand_id);
CREATE INDEX idx_module_resonance_scores_selection_score ON module_resonance_scores(selection_score);

-- Pattern Evolution indexes (PRESERVED)
CREATE INDEX idx_pattern_evolution_pattern_type ON pattern_evolution(pattern_type);
CREATE INDEX idx_pattern_evolution_cluster_key ON pattern_evolution(cluster_key);
CREATE INDEX idx_pattern_evolution_success_rate ON pattern_evolution(success_rate DESC);
CREATE INDEX idx_pattern_evolution_last_updated ON pattern_evolution(last_updated DESC);

-- =============================================
-- TRIGGERS FOR COMMUNICATION AND LEARNING
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

-- Function to trigger learning system and calculate resonance scores
CREATE OR REPLACE FUNCTION trigger_learning_system()
RETURNS TRIGGER AS $$
BEGIN
    -- Queue strand for learning processing
    INSERT INTO learning_queue (strand_id, strand_type, created_at)
    VALUES (NEW.id, NEW.kind, NOW());
    
    -- Calculate resonance scores (will be implemented in Python)
    PERFORM calculate_module_resonance_scores(NEW.id, NEW.kind, NEW.content, NEW.module_intelligence);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER strand_learning_trigger
    AFTER INSERT ON AD_strands
    FOR EACH ROW
    EXECUTE FUNCTION trigger_learning_system();

-- Function to calculate module-specific resonance scores
CREATE OR REPLACE FUNCTION calculate_module_resonance_scores(
    p_strand_id TEXT,
    p_kind TEXT,
    p_content JSONB,
    p_module_intelligence JSONB
)
RETURNS VOID AS $$
DECLARE
    v_phi FLOAT;
    v_rho FLOAT;
    v_theta FLOAT;
    v_omega FLOAT;
    v_selection_score FLOAT;
    v_module_type TEXT;
BEGIN
    -- Determine module type based on strand kind
    CASE p_kind
        WHEN 'pattern' THEN v_module_type := 'rdi';
        WHEN 'prediction_review' THEN v_module_type := 'cil';
        WHEN 'conditional_trading_plan' THEN v_module_type := 'ctp';
        WHEN 'trading_decision' THEN v_module_type := 'dm';
        WHEN 'execution_outcome' THEN v_module_type := 'td';
        ELSE v_module_type := 'unknown';
    END CASE;
    
    -- Calculate resonance scores (will be implemented in Python)
    -- For now, set default values
    v_phi := 1.0;
    v_rho := 1.0;
    v_theta := 1.0;
    v_omega := 1.0;
    v_selection_score := 1.0;
    
    -- Insert resonance scores
    INSERT INTO module_resonance_scores (
        module_type, strand_id, phi, rho, theta, omega, selection_score
    ) VALUES (
        v_module_type, p_strand_id, v_phi, v_rho, v_theta, v_omega, v_selection_score
    );
    
    -- Update strand with resonance scores and timestamp
    UPDATE AD_strands 
    SET 
        resonance_scores = jsonb_build_object(
            'phi', v_phi,
            'rho', v_rho,
            'theta', v_theta,
            'omega', v_omega,
            'selection_score', v_selection_score
        ),
        resonance_updated_at = NOW()
    WHERE id = p_strand_id;
    
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- VIEWS FOR EASY QUERYING
-- =============================================

-- Module-specific views
CREATE VIEW rdi_strands AS
SELECT * FROM AD_strands WHERE kind = 'pattern';

CREATE VIEW cil_strands AS
SELECT * FROM AD_strands WHERE kind = 'prediction_review';

CREATE VIEW ctp_strands AS
SELECT * FROM AD_strands WHERE kind = 'conditional_trading_plan';

CREATE VIEW dm_strands AS
SELECT * FROM AD_strands WHERE kind = 'trading_decision';

CREATE VIEW td_strands AS
SELECT * FROM AD_strands WHERE kind = 'execution_outcome';

-- High-quality braid candidates
CREATE VIEW braid_candidates AS
SELECT 
    s.*,
    s.resonance_scores->>'phi' as phi,
    s.resonance_scores->>'rho' as rho,
    s.resonance_scores->>'theta' as theta,
    s.resonance_scores->>'omega' as omega,
    s.resonance_scores->>'selection_score' as selection_score
FROM AD_strands s
WHERE s.braid_candidate = TRUE
ORDER BY (s.resonance_scores->>'selection_score')::FLOAT DESC;

-- =============================================
-- COMMENTS AND DOCUMENTATION
-- =============================================

COMMENT ON TABLE AD_strands IS 'Enhanced Alpha Detector main data table with module-specific resonance scoring and preserved clustering infrastructure';
COMMENT ON COLUMN AD_strands.cluster_key IS 'Clustering assignments for multi-dimensional learning - ESSENTIAL for clustering system';
COMMENT ON COLUMN AD_strands.resonance_scores IS 'Module-specific resonance scores (φ, ρ, θ, ω) calculated by mathematical resonance engine';
COMMENT ON COLUMN AD_strands.historical_metrics IS 'Historical accuracy and performance data for improvement tracking';
COMMENT ON COLUMN AD_strands.module_intelligence IS 'Module-specific intelligence data (RDI patterns, CIL predictions, etc.)';
COMMENT ON COLUMN AD_strands.content IS 'Generic message content for inter-agent communication (CIL predictions, etc.)';

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO your_user;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO your_user;
