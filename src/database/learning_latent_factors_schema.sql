-- Learning Latent Factors Database Schema (v5.3)
-- Pattern clusters / orthogonalization to prevent double-counting
-- Used by: Lesson builder (deduplication), override materializer (merge levers)

-- Drop existing table if it exists (for clean cutover)
DROP TABLE IF EXISTS learning_latent_factors CASCADE;

-- Create learning_latent_factors table
CREATE TABLE learning_latent_factors (
    id BIGSERIAL PRIMARY KEY,
    factor_id TEXT NOT NULL UNIQUE,                -- Unique factor identifier (e.g., "factor_001")
    pattern_keys TEXT[] NOT NULL,                   -- Array of pattern_keys in this cluster
    representative_pattern TEXT,                    -- Canonical pattern for this factor (most common or highest edge)
    correlation_matrix JSONB,                       -- Pairwise correlations between patterns in cluster
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for efficient queries
CREATE INDEX idx_latent_factors_factor_id 
    ON learning_latent_factors(factor_id);
CREATE INDEX idx_latent_factors_pattern_keys 
    ON learning_latent_factors USING GIN(pattern_keys);
CREATE INDEX idx_latent_factors_updated 
    ON learning_latent_factors(updated_at DESC);

-- Comments for documentation
COMMENT ON TABLE learning_latent_factors IS 'Pattern clusters / orthogonalization to prevent double-counting (v5.3 meta-learning)';
COMMENT ON COLUMN learning_latent_factors.factor_id IS 'Unique factor identifier';
COMMENT ON COLUMN learning_latent_factors.pattern_keys IS 'Array of pattern_keys that belong to this latent factor cluster';
COMMENT ON COLUMN learning_latent_factors.representative_pattern IS 'Canonical pattern for this factor (used for override merging)';
COMMENT ON COLUMN learning_latent_factors.correlation_matrix IS 'Pairwise correlations between patterns in cluster (JSONB matrix)';

-- Example row:
-- factor_id: "factor_001"
-- pattern_keys: ["pm.uptrend.S1.buy_flag", "pm.uptrend.S1.breakout_follow_through"]
-- representative_pattern: "pm.uptrend.S1.buy_flag"
-- correlation_matrix: {"pm.uptrend.S1.buy_flag": {"pm.uptrend.S1.breakout_follow_through": 0.85}, ...}

