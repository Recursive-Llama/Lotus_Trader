-- Migration: Add applied_overrides column to position_trajectories
-- Date: 2025-01-14
-- Purpose: Track which pm_overrides affected each trajectory for effectiveness analysis

-- Add applied_overrides column as JSONB array
-- Each element: {"override_id": UUID, "scope_subset": {}, "dirA": 0.05, "dirE": null, "confidence": 0.7}
ALTER TABLE position_trajectories 
ADD COLUMN IF NOT EXISTS applied_overrides JSONB DEFAULT '[]'::jsonb;

-- Index for finding trajectories affected by specific overrides
CREATE INDEX IF NOT EXISTS idx_pt_applied_overrides_gin 
ON position_trajectories USING GIN(applied_overrides);

-- Comments
COMMENT ON COLUMN position_trajectories.applied_overrides IS 'Array of override objects that were applied at entry decision. Used to measure override effectiveness by correlating with trajectory outcome.';
