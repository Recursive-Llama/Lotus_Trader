-- Migration: Add tuning_params column to pm_overrides for Learning System v2
-- Date: 2025-01-13

-- Add tuning_params column for gate adjustment lessons
ALTER TABLE pm_overrides 
    ADD COLUMN IF NOT EXISTS tuning_params JSONB;

-- Update comments
COMMENT ON COLUMN pm_overrides.tuning_params IS 'Tuning gate adjustments: {"ts_min_delta": 0.05, "halo_max_delta": -0.1, ...}. Used by tuning lessons for specific gate deltas.';
