-- Learning Coefficients Database Schema
-- Shared learning table for all modules - stores performance coefficients (weights) learned from closed trades
-- Used by: Decision Maker (primary), Portfolio Manager (recalculation), future modules

-- Drop existing table if it exists (for clean cutover)
DROP TABLE IF EXISTS learning_coefficients CASCADE;

-- Create learning_coefficients table
CREATE TABLE learning_coefficients (
    module TEXT NOT NULL,                    -- 'dm', 'pm', 'ingest', etc.
    scope TEXT NOT NULL,                     -- 'lever' | 'interaction' | 'timeframe'
    name TEXT NOT NULL,                      -- 'curator', 'chain', 'cap', 'vol', 'age', 'intent', 'mapping_confidence', 'interaction', '1m', '15m', '1h', '4h'
    key TEXT NOT NULL,                       -- Bucket or hashed combo (e.g., 'cap:<2m' or 'curator=detweiler|chain=base|age<7d|vol>250k')
    weight FLOAT NOT NULL,                   -- Current multiplier (already clipped to system-wide bounds, e.g., 0.5-2.0)
    rr_short FLOAT,                          -- Short-term R/R average (τ₁, e.g., 14 days)
    rr_long FLOAT,                           -- Long-term R/R average (τ₂, e.g., 90 days)
    n INTEGER DEFAULT 0,                    -- Sample count (number of closed trades contributing to this coefficient)
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (module, scope, name, key)
);

-- Create indexes for efficient queries
CREATE INDEX idx_learning_coefficients_module_scope ON learning_coefficients(module, scope);
CREATE INDEX idx_learning_coefficients_module_name ON learning_coefficients(module, name);
CREATE INDEX idx_learning_coefficients_module_scope_name ON learning_coefficients(module, scope, name);

-- Comments for documentation
COMMENT ON TABLE learning_coefficients IS 'Shared learning table for all modules - stores performance coefficients learned from closed trades';
COMMENT ON COLUMN learning_coefficients.module IS 'Module identifier: dm (Decision Maker), pm (Portfolio Manager), etc.';
COMMENT ON COLUMN learning_coefficients.scope IS 'Scope: lever (single factor), interaction (combination), timeframe (per-timeframe performance)';
COMMENT ON COLUMN learning_coefficients.name IS 'Lever name: curator, chain, cap, vol, age, intent, mapping_confidence, interaction, or timeframe (1m, 15m, 1h, 4h)';
COMMENT ON COLUMN learning_coefficients.key IS 'Bucket value or hashed combination (e.g., cap:<2m or curator=detweiler|chain=base|age<7d|vol>250k)';
COMMENT ON COLUMN learning_coefficients.weight IS 'Current multiplier (clamped to system-wide bounds, e.g., 0.5-2.0) - used in allocation formula';
COMMENT ON COLUMN learning_coefficients.rr_short IS 'Short-term R/R average (τ₁ = 14 days) - recent performance';
COMMENT ON COLUMN learning_coefficients.rr_long IS 'Long-term R/R average (τ₂ = 90 days) - baseline performance';
COMMENT ON COLUMN learning_coefficients.n IS 'Sample count - number of closed trades contributing to this coefficient';

-- Example rows:
-- Single-factor coefficient:
-- ('dm', 'lever', 'chain', 'base', 1.4, 1.35, 1.2, 45, '2024-01-15T10:00:00Z')
--
-- Interaction pattern:
-- ('dm', 'interaction', 'interaction', 'curator=detweiler|chain=base|age<7d|vol>250k', 1.8, 1.75, 1.5, 12, '2024-01-15T10:00:00Z')
--
-- Timeframe coefficient:
-- ('dm', 'timeframe', '1h', '1h', 1.1, 1.15, 1.05, 30, '2024-01-15T10:00:00Z')

