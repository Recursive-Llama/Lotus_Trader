-- Learning Regime Weights Database Schema (v5.1)
-- Regime-specific weights for time efficiency, field coherence, recurrence, variance
-- Used by: Edge computation in pattern_scope_stats aggregation

-- Drop existing table if it exists (for clean cutover)
DROP TABLE IF EXISTS learning_regime_weights CASCADE;

-- Create learning_regime_weights table
CREATE TABLE learning_regime_weights (
    id BIGSERIAL PRIMARY KEY,
    pattern_key TEXT NOT NULL,
    action_category TEXT NOT NULL CHECK (action_category IN ('entry', 'add', 'trim', 'exit')),
    regime_signature TEXT NOT NULL,                 -- e.g. "macro=Recover|meso=Dip|bucket_rank=1"
    weights JSONB NOT NULL,                         -- { time_efficiency: 0.6, field_coherence: 0.8, recurrence: 0.5, variance: 0.3 }
    n_samples INT NOT NULL,                        -- Number of samples used to learn these weights
    confidence FLOAT,                               -- Confidence in weight estimates (0.0-1.0)
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (pattern_key, action_category, regime_signature)
);

-- Create indexes for efficient queries
CREATE INDEX idx_regime_weights_pattern 
    ON learning_regime_weights(pattern_key, action_category);
CREATE INDEX idx_regime_weights_signature 
    ON learning_regime_weights(regime_signature);
CREATE INDEX idx_regime_weights_updated 
    ON learning_regime_weights(updated_at DESC);

-- GIN index for JSONB weights queries
CREATE INDEX idx_regime_weights_weights 
    ON learning_regime_weights USING GIN(weights);

-- Comments for documentation
COMMENT ON TABLE learning_regime_weights IS 'Regime-specific weights for edge computation multipliers (v5.1 meta-learning)';
COMMENT ON COLUMN learning_regime_weights.pattern_key IS 'Pattern identity: module.family.state.motif';
COMMENT ON COLUMN learning_regime_weights.action_category IS 'Action class: entry, add, trim, or exit';
COMMENT ON COLUMN learning_regime_weights.regime_signature IS 'Regime signature: macro=<phase>|meso=<phase>|micro=<phase>|bucket_rank=<n>';
COMMENT ON COLUMN learning_regime_weights.weights IS 'Learned weights for time_efficiency, field_coherence, recurrence, variance (default 1.0 if not learned)';
COMMENT ON COLUMN learning_regime_weights.n_samples IS 'Number of samples used to learn these weights';
COMMENT ON COLUMN learning_regime_weights.confidence IS 'Confidence in weight estimates (0.0-1.0)';

-- Example row:
-- pattern_key: "pm.uptrend.S1.buy_flag"
-- action_category: "entry"
-- regime_signature: "macro=Recover|meso=Dip|bucket_rank=1"
-- weights: {"time_efficiency": 0.6, "field_coherence": 0.8, "recurrence": 0.5, "variance": 0.3}
-- n_samples: 150
-- confidence: 0.72

