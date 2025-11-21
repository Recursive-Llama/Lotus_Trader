-- Learning Edge History Database Schema (v5.2)
-- Historical edge_raw snapshots for half-life estimation
-- Used by: Half-life estimation job, decay modeling

-- Drop existing table if it exists (for clean cutover)
DROP TABLE IF EXISTS learning_edge_history CASCADE;

-- Create learning_edge_history table
CREATE TABLE learning_edge_history (
    id BIGSERIAL PRIMARY KEY,
    pattern_key TEXT NOT NULL,
    action_category TEXT NOT NULL CHECK (action_category IN ('entry', 'add', 'trim', 'exit')),
    scope_signature TEXT NOT NULL,                  -- Hash or sorted JSON string of scope subset
    edge_raw FLOAT NOT NULL,                        -- Edge score at this snapshot
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    n INT NOT NULL                                  -- Sample count at this snapshot
);

-- Create indexes for efficient queries
CREATE INDEX idx_edge_history_pattern 
    ON learning_edge_history(pattern_key, action_category, scope_signature, ts DESC);
CREATE INDEX idx_edge_history_ts 
    ON learning_edge_history(ts DESC);
CREATE INDEX idx_edge_history_pattern_category 
    ON learning_edge_history(pattern_key, action_category);

-- Comments for documentation
COMMENT ON TABLE learning_edge_history IS 'Historical edge_raw snapshots for half-life estimation (v5.2 meta-learning)';
COMMENT ON COLUMN learning_edge_history.pattern_key IS 'Pattern identity: module.family.state.motif';
COMMENT ON COLUMN learning_edge_history.action_category IS 'Action class: entry, add, trim, or exit';
COMMENT ON COLUMN learning_edge_history.scope_signature IS 'Hash or sorted JSON string identifying the scope subset';
COMMENT ON COLUMN learning_edge_history.edge_raw IS 'Edge score at this snapshot (for decay curve fitting)';
COMMENT ON COLUMN learning_edge_history.n IS 'Sample count at this snapshot';

-- Example row:
-- pattern_key: "pm.uptrend.S1.buy_flag"
-- action_category: "entry"
-- scope_signature: "hash_abc123..."
-- edge_raw: 0.68
-- ts: "2024-01-15T10:30:00Z"
-- n: 42

