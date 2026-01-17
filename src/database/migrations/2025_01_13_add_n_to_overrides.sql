-- Migration: Add 'n' column to pm_overrides
-- Date: 2025-01-13
-- Purpose: Track sample size for learned lessons

ALTER TABLE pm_overrides 
    ADD COLUMN IF NOT EXISTS n INTEGER;

COMMENT ON COLUMN pm_overrides.n IS 'Number of trajectory samples used to generate this lesson (N_MIN check).';
