-- Learning Baselines Database Schema
-- Segmented R/R baselines by (module, mcap_bucket, timeframe) for edge score calculation
-- Used by: Braiding System (edge score calculation with segmented baselines)

-- Drop existing table if it exists (for clean cutover)
DROP TABLE IF EXISTS learning_baselines CASCADE;

-- Create learning_baselines table
CREATE TABLE learning_baselines (
    module TEXT NOT NULL,                       -- 'dm' | 'pm'
    mcap_bucket TEXT,                           -- '<500k', '500k-1m', '1m-2m', etc. (NULL for timeframe-only or global)
    timeframe TEXT,                             -- '1m', '15m', '1h', '4h' (NULL for mcap-only or global)
    stats JSONB NOT NULL,                       -- { n, sum_rr, sum_rr_squared, avg_rr, variance, last_updated }
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (module, mcap_bucket, timeframe)
);

-- Create indexes for efficient queries
CREATE INDEX idx_learning_baselines_module ON learning_baselines(module);
CREATE INDEX idx_learning_baselines_module_mcap ON learning_baselines(module, mcap_bucket);
CREATE INDEX idx_learning_baselines_module_timeframe ON learning_baselines(module, timeframe);

-- GIN index for JSONB stats queries
CREATE INDEX idx_learning_baselines_stats ON learning_baselines USING GIN(stats);

-- Comments for documentation
COMMENT ON TABLE learning_baselines IS 'Segmented R/R baselines by (module, mcap_bucket, timeframe) for edge score calculation';
COMMENT ON COLUMN learning_baselines.module IS 'Module: dm (Decision Maker) or pm (Portfolio Manager)';
COMMENT ON COLUMN learning_baselines.mcap_bucket IS 'Market cap bucket: <500k, 500k-1m, etc. (NULL for timeframe-only or global baseline)';
COMMENT ON COLUMN learning_baselines.timeframe IS 'Timeframe: 1m, 15m, 1h, 4h (NULL for mcap-only or global baseline)';
COMMENT ON COLUMN learning_baselines.stats IS 'Aggregated statistics: n, sum_rr, sum_rr_squared, avg_rr, variance, last_updated';

-- Example rows:
-- Segment baseline (mcap + timeframe):
-- module: "pm"
-- mcap_bucket: "<500k"
-- timeframe: "1m"
-- stats: {"n": 45, "sum_rr": 67.5, "sum_rr_squared": 125.3, "avg_rr": 1.5, "variance": 0.8, "last_updated": "2024-01-15T10:00:00Z"}
--
-- Timeframe-only baseline:
-- module: "pm"
-- mcap_bucket: NULL
-- timeframe: "1h"
-- stats: {"n": 120, "sum_rr": 144.0, "sum_rr_squared": 200.5, "avg_rr": 1.2, "variance": 0.6, "last_updated": "2024-01-15T10:00:00Z"}
--
-- Global baseline:
-- module: "pm"
-- mcap_bucket: NULL
-- timeframe: NULL
-- stats: {"n": 500, "sum_rr": 550.0, "sum_rr_squared": 750.2, "avg_rr": 1.1, "variance": 0.5, "last_updated": "2024-01-15T10:00:00Z"}

