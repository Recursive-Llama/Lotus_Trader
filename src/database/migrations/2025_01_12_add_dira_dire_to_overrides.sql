-- Migration: Add dirA/dirE columns to pm_overrides for Learning System v2
-- Date: 2025-01-12

-- Add direction columns for strength steering
ALTER TABLE pm_overrides ADD COLUMN IF NOT EXISTS dirA FLOAT;  -- Direction for A (aggressiveness): -1 to +1
ALTER TABLE pm_overrides ADD COLUMN IF NOT EXISTS dirE FLOAT;  -- Direction for E (exit assertiveness): -1 to +1

-- Comments
COMMENT ON COLUMN pm_overrides.dirA IS 'Learning System v2: Direction for A (aggressiveness). Range -1 to +1. Negative = less aggressive, positive = more aggressive.';
COMMENT ON COLUMN pm_overrides.dirE IS 'Learning System v2: Direction for E (exit assertiveness). Range -1 to +1. Negative = hold longer, positive = exit faster.';

-- Note: 'multiplier' column is deprecated but kept for backward compat
-- New code should use dirA/dirE for strength steering
