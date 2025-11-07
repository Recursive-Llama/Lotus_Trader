-- Learning Configs Database Schema
-- Store module-specific configuration that can be updated by the system (future learning) or manually
-- Used by: Social Ingest (ambiguous_terms, major_tokens), Decision Maker (global_rr, bucket_definitions), future modules

-- Drop existing table if it exists (for clean cutover)
DROP TABLE IF EXISTS learning_configs CASCADE;

-- Create learning_configs table
CREATE TABLE learning_configs (
    module_id TEXT PRIMARY KEY,              -- 'social_ingest', 'decision_maker', 'pm', etc.
    config_data JSONB NOT NULL,               -- Module-specific config structure
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT,                          -- 'system' | 'manual' | 'learning_system'
    notes TEXT                                -- Optional notes about config changes
);

-- Create index for module lookups
CREATE INDEX idx_learning_configs_module ON learning_configs(module_id);

-- Comments for documentation
COMMENT ON TABLE learning_configs IS 'Module-specific configuration storage (editable settings, thresholds, lists) - separate from learned coefficients';
COMMENT ON COLUMN learning_configs.module_id IS 'Module identifier: social_ingest, decision_maker, pm, etc.';
COMMENT ON COLUMN learning_configs.config_data IS 'JSONB structure varies by module (e.g., ambiguous_terms for social_ingest, global_rr for decision_maker)';
COMMENT ON COLUMN learning_configs.updated_by IS 'Who/what updated this config: system (automated), manual (human), learning_system (future auto-updates)';

-- Example config_data structures:
-- Social Ingest:
-- {
--   "ambiguous_terms": {
--     "ICM": {"rule": "suppress", "notes": "Ambiguous - could be many tokens"},
--     "LIGHTER": {"rule": "suppress", "notes": "Ambiguous term"}
--   },
--   "major_tokens": {
--     "SOL": {"rule": "hard_block", "notes": "Major token"},
--     "ETH": {"rule": "hard_block", "notes": "Major token"}
--   }
-- }
--
-- Decision Maker:
-- {
--   "global_rr": {
--     "rr_short": 1.05,
--     "rr_long": 0.98,
--     "n": 150,
--     "updated_at": "2024-01-15T10:00:00Z"
--   },
--   "bucket_definitions": {
--     "mcap": ["<500k", "500k-1m", "1m-2m", "2m-5m", "5m-10m", "10m-50m", "50m+"],
--     "vol": ["<10k", "10k-50k", "50k-100k", "100k-250k", "250k-500k", "500k-1m", "1m+"],
--     "age": ["<1d", "1-3d", "3-7d", "7-14d", "14-30d", "30-90d", "90d+"]
--   }
-- }

