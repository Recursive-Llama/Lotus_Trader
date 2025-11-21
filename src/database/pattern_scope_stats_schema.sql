-- Pattern Scope Stats Database Schema
-- Aggregated edge stats per (pattern_key, action_category, scope_subset)
-- Used by: Learning System (pattern strength evaluation, lesson building)

-- Drop existing table if it exists (for clean cutover)
DROP TABLE IF EXISTS pattern_scope_stats CASCADE;

-- Create pattern_scope_stats table
CREATE TABLE pattern_scope_stats (
    id BIGSERIAL PRIMARY KEY,
    pattern_key TEXT NOT NULL,                      -- Canonical pattern: "pm.uptrend.S1.buy_flag"
    action_category TEXT NOT NULL CHECK (action_category IN ('entry', 'add', 'trim', 'exit')),
    scope_mask SMALLINT NOT NULL,                   -- Bitmask over 10 scope dimensions
    scope_values JSONB NOT NULL,                    -- Only dims indicated by mask: {"macro_phase": "Recover", "bucket": "micro"}
    scope_values_hash TEXT NOT NULL,                -- Deterministic hash for uniqueness (sorted JSON string hash)
    n INT NOT NULL,                                 -- Sample count (also in stats for convenience)
    stats JSONB NOT NULL,                           -- { avg_rr, variance, edge_raw, time_efficiency, field_coherence, recurrence_score, ... }
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (pattern_key, action_category, scope_mask, scope_values_hash)
);

-- Create indexes for efficient queries
CREATE INDEX idx_pattern_scope_stats_lookup 
    ON pattern_scope_stats(pattern_key, action_category, scope_mask);
CREATE INDEX idx_pattern_scope_stats_n 
    ON pattern_scope_stats(n DESC) WHERE n >= 10;
CREATE INDEX idx_pattern_scope_stats_pattern_category 
    ON pattern_scope_stats(pattern_key, action_category);
CREATE INDEX idx_pattern_scope_stats_updated 
    ON pattern_scope_stats(updated_at DESC);

-- GIN index for JSONB scope_values queries
CREATE INDEX idx_pattern_scope_stats_scope_values 
    ON pattern_scope_stats USING GIN(scope_values);
CREATE INDEX idx_pattern_scope_stats_stats 
    ON pattern_scope_stats USING GIN(stats);

-- Comments for documentation
COMMENT ON TABLE pattern_scope_stats IS 'Aggregated edge stats per (pattern_key, action_category, scope_subset) - used for pattern strength evaluation';
COMMENT ON COLUMN pattern_scope_stats.pattern_key IS 'Canonical pattern identity: module.family.state.motif (e.g., "pm.uptrend.S1.buy_flag")';
COMMENT ON COLUMN pattern_scope_stats.action_category IS 'Action class: entry, add, trim, or exit - always included as required grouping dimension';
COMMENT ON COLUMN pattern_scope_stats.scope_mask IS 'Bitmask indicating which of 10 scope dimensions are included in this subset';
COMMENT ON COLUMN pattern_scope_stats.scope_values IS 'JSONB with only the scope dimensions indicated by scope_mask';
COMMENT ON COLUMN pattern_scope_stats.scope_values_hash IS 'Deterministic hash of sorted scope_values JSON for uniqueness';
COMMENT ON COLUMN pattern_scope_stats.n IS 'Sample count for this pattern+category+scope combination';
COMMENT ON COLUMN pattern_scope_stats.stats IS 'Aggregated stats: avg_rr, variance, edge_raw, time_efficiency, field_coherence, recurrence_score, segments_tested, segments_positive';

-- Scope dimension bitmask (10 dims total):
-- Bit 0: macro_phase
-- Bit 1: meso_phase
-- Bit 2: micro_phase
-- Bit 3: bucket_leader
-- Bit 4: bucket_rank_position
-- Bit 5: market_family
-- Bit 6: bucket
-- Bit 7: timeframe
-- Bit 8: A_mode
-- Bit 9: E_mode

-- Example row:
-- pattern_key: "pm.uptrend.S1.buy_flag"
-- action_category: "entry"
-- scope_mask: 3 (bits 0+1 = macro_phase + meso_phase)
-- scope_values: {"macro_phase": "Recover", "meso_phase": "Dip"}
-- scope_values_hash: "abc123def456..."
-- n: 42
-- stats: {"avg_rr": 1.85, "variance": 0.32, "edge_raw": 0.68, "time_efficiency": 0.75, "field_coherence": 0.82, "recurrence_score": 0.45, "segments_tested": 5, "segments_positive": 4}

