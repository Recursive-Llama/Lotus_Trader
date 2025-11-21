-- Learning Braids Database Schema
-- Raw pattern statistics - aggregated across all trades matching each pattern
-- Used by: Braiding System (pattern discovery and aggregation)

-- Drop existing table if it exists (for clean cutover)
DROP TABLE IF EXISTS learning_braids CASCADE;

-- Create learning_braids table
CREATE TABLE learning_braids (
    pattern_key TEXT PRIMARY KEY,              -- "big_win|state=S1|A=med|buy_flag=true" (sorted, delimited dimensions)
    module TEXT NOT NULL,                       -- 'dm' | 'pm' (explicit module, not just in family_id)
    dimensions JSONB NOT NULL,                  -- { outcome_class: "big_win", state: "S1", a_bucket: "med", buy_flag: true }
    stats JSONB NOT NULL,                       -- { n, sum_rr, sum_rr_squared, avg_rr, variance, win_rate, avg_hold_time_days }
    family_id TEXT NOT NULL,                    -- "pm|add|S1|big_win" (computed from core dimensions)
    parent_keys TEXT[],                         -- Array of parent pattern_keys (all (k-1) subsets) for incremental edge calculation
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for efficient queries
CREATE INDEX idx_learning_braids_module ON learning_braids(module);
CREATE INDEX idx_learning_braids_family ON learning_braids(family_id);
CREATE INDEX idx_learning_braids_pattern ON learning_braids(pattern_key);  -- Already PK, but explicit for clarity

-- GIN index for JSONB dimension queries
CREATE INDEX idx_learning_braids_dimensions ON learning_braids USING GIN(dimensions);
CREATE INDEX idx_learning_braids_stats ON learning_braids USING GIN(stats);

-- Comments for documentation
COMMENT ON TABLE learning_braids IS 'Raw pattern statistics - aggregated across all trades matching each pattern';
COMMENT ON COLUMN learning_braids.pattern_key IS 'Unique pattern identifier (sorted, delimited dimensions)';
COMMENT ON COLUMN learning_braids.module IS 'Module: dm (Decision Maker) or pm (Portfolio Manager)';
COMMENT ON COLUMN learning_braids.dimensions IS 'Dimension values that define this pattern (JSONB for flexible querying)';
COMMENT ON COLUMN learning_braids.stats IS 'Aggregated statistics: n, sum_rr, sum_rr_squared, avg_rr, variance, win_rate, avg_hold_time_days';
COMMENT ON COLUMN learning_braids.family_id IS 'Family core dimensions (module|action|state|outcome_class for PM, module|curator|chain|outcome_class for DM)';
COMMENT ON COLUMN learning_braids.parent_keys IS 'Array of parent pattern_keys (all (k-1) subsets) for incremental edge calculation';

-- Example row:
-- pattern_key: "big_win|state=S1|a_bucket=med|buy_flag=true"
-- module: "pm"
-- dimensions: {"outcome_class": "big_win", "state": "S1", "a_bucket": "med", "buy_flag": true}
-- stats: {"n": 23, "sum_rr": 52.9, "sum_rr_squared": 125.3, "avg_rr": 2.3, "variance": 0.5, "win_rate": 0.87, "avg_hold_time_days": 4.8}
-- family_id: "pm|add|S1|big_win"
-- parent_keys: ["big_win|state=S1|a_bucket=med", "big_win|state=S1|buy_flag=true", "big_win|a_bucket=med|buy_flag=true", "state=S1|a_bucket=med|buy_flag=true"]

