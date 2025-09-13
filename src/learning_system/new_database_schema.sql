-- New Database Schema for Module-Specific Learning System
-- This replaces the existing AD_strands table with a more comprehensive structure

-- Drop existing tables if they exist (for clean cutover)
DROP TABLE IF EXISTS learning_queue CASCADE;
DROP TABLE IF EXISTS AD_strands CASCADE;
DROP TABLE IF EXISTS learning_braids CASCADE;
DROP TABLE IF EXISTS module_resonance_scores CASCADE;

-- Create new AD_strands table with module-specific fields
CREATE TABLE AD_strands (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL, -- 'pattern', 'prediction_review', 'conditional_trading_plan', 'trading_decision', 'trade_outcome', 'execution_outcome'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Core strand data
    asset TEXT,
    timeframe TEXT,
    content JSONB, -- Module-specific content data
    
    -- Module Intelligence (for RDI patterns)
    module_intelligence JSONB, -- Pattern type, analyzer, confidence, significance, etc.
    
    -- Resonance Scores (φ, ρ, θ, ω)
    resonance_scores JSONB, -- Calculated resonance values
    
    -- Historical Metrics (for improvement tracking)
    historical_metrics JSONB, -- Historical accuracy, performance data
    
    -- Learning System Fields
    processed BOOLEAN DEFAULT FALSE,
    braid_candidate BOOLEAN DEFAULT FALSE,
    braid_level INTEGER DEFAULT 1, -- 1 = strand, 2+ = braid levels
    
    -- Quality Metrics
    quality_score FLOAT,
    confidence FLOAT,
    significance FLOAT,
    
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

-- Create module resonance scores table for tracking
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

-- Create indexes for performance
CREATE INDEX idx_ad_strands_kind ON AD_strands(kind);
CREATE INDEX idx_ad_strands_created_at ON AD_strands(created_at);
CREATE INDEX idx_ad_strands_processed ON AD_strands(processed);
CREATE INDEX idx_ad_strands_braid_candidate ON AD_strands(braid_candidate);
CREATE INDEX idx_ad_strands_quality_score ON AD_strands(quality_score);

CREATE INDEX idx_learning_queue_status ON learning_queue(status);
CREATE INDEX idx_learning_queue_created_at ON learning_queue(created_at);

CREATE INDEX idx_learning_braids_level ON learning_braids(level);
CREATE INDEX idx_learning_braids_strand_type ON learning_braids(strand_type);
CREATE INDEX idx_learning_braids_quality_score ON learning_braids(quality_score);

CREATE INDEX idx_module_resonance_scores_module_type ON module_resonance_scores(module_type);
CREATE INDEX idx_module_resonance_scores_strand_id ON module_resonance_scores(strand_id);
CREATE INDEX idx_module_resonance_scores_selection_score ON module_resonance_scores(selection_score);

-- Create triggers for automatic processing
CREATE OR REPLACE FUNCTION trigger_learning_system()
RETURNS TRIGGER AS $$
BEGIN
    -- Queue strand for learning processing
    INSERT INTO learning_queue (strand_id, strand_type, created_at)
    VALUES (NEW.id, NEW.kind, NOW());
    
    -- Calculate resonance scores
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
    
    -- Update strand with resonance scores
    UPDATE AD_strands 
    SET resonance_scores = jsonb_build_object(
        'phi', v_phi,
        'rho', v_rho,
        'theta', v_theta,
        'omega', v_omega,
        'selection_score', v_selection_score
    )
    WHERE id = p_strand_id;
    
END;
$$ LANGUAGE plpgsql;

-- Create views for easy querying
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

-- Create view for high-quality braid candidates
CREATE VIEW braid_candidates AS
SELECT 
    s.*,
    mrs.phi,
    mrs.rho,
    mrs.theta,
    mrs.omega,
    mrs.selection_score
FROM AD_strands s
JOIN module_resonance_scores mrs ON s.id = mrs.strand_id
WHERE s.braid_candidate = TRUE
ORDER BY mrs.selection_score DESC;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO your_user;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO your_user;
