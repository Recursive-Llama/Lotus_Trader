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
    scope_mask INTEGER NOT NULL,                    -- Bitmask over up to 32 scope dimensions
    scope_values JSONB NOT NULL,                    -- Only dims indicated by mask: {"macro_phase": "Recover", "mcap_bucket": "micro"}
    scope_values_hash TEXT NOT NULL,                -- Deterministic hash for uniqueness (sorted JSON string hash)
    n INT NOT NULL,                                 -- Sample count (also in stats for convenience)
    stats JSONB NOT NULL,                           -- { avg_rr, variance, edge_raw, ev_score, time_score, stability_score, decay_meta, ... }
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
COMMENT ON COLUMN pattern_scope_stats.scope_mask IS 'Bitmask indicating which of the 32 scope dimensions are included in this subset';
COMMENT ON COLUMN pattern_scope_stats.scope_values IS 'JSONB with only the scope dimensions indicated by scope_mask';
COMMENT ON COLUMN pattern_scope_stats.scope_values_hash IS 'Deterministic hash of sorted scope_values JSON for uniqueness';
COMMENT ON COLUMN pattern_scope_stats.n IS 'Sample count for this pattern+category+scope combination';
COMMENT ON COLUMN pattern_scope_stats.stats IS 'Aggregated stats: avg_rr, variance, edge_raw, ev_score, reliability_score, support_score, magnitude_score, time_score, stability_score, decay metadata, etc.';

-- Scope dimension bitmask (32 dims max, currently using 16):
-- Bit 0: curator
-- Bit 1: chain
-- Bit 2: mcap_bucket
-- Bit 3: vol_bucket
-- Bit 4: age_bucket
-- Bit 5: intent
- Bit 6: mcap_vol_ratio_bucket
- Bit 7: market_family
- Bit 8: timeframe
- Bit 9: A_mode
- Bit10: E_mode
- Bit11: macro_phase
- Bit12: meso_phase
- Bit13: micro_phase
- Bit14: bucket_leader
- Bit15: bucket_rank_position

-- Example row:
-- pattern_key: "pm.uptrend.S1.buy_flag"
-- action_category: "entry"
-- scope_mask: e.g., bits 2 + 9 + 12 set (mcap_bucket + timeframe + macro_phase)
-- scope_values: {"mcap_bucket": "micro", "timeframe": "1h", "macro_phase": "Recover"}
-- scope_values_hash: "abc123def456..."
-- n: 42
-- stats: {"avg_rr": 1.85, "variance": 0.32, "edge_raw": 0.68, "ev_score": 0.73, "reliability_score": 0.61, "support_score": 0.91, "magnitude_score": 0.54, "time_score": 0.67, "stability_score": 0.58, "decay_meta": {"state": "stable", "slope": 0.0}}

