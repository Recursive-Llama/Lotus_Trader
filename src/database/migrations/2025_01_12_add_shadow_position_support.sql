-- Migration: Add shadow position support for Learning System v2
-- Date: 2025-01-12

-- 1. Drop and recreate status constraint to include 'shadow'
ALTER TABLE lowcap_positions DROP CONSTRAINT IF EXISTS check_status;

ALTER TABLE lowcap_positions ADD CONSTRAINT check_status 
    CHECK (status IN ('dormant', 'watchlist', 'active', 'shadow', 'paused', 'archived', 'regime_driver'));

-- 2. Add entry_event column for tracking entry type
ALTER TABLE lowcap_positions 
    ADD COLUMN IF NOT EXISTS entry_event TEXT;

-- 3. Add index for shadow positions
CREATE INDEX IF NOT EXISTS idx_lowcap_positions_shadow 
    ON lowcap_positions(status) WHERE status = 'shadow';

-- 4. Update comments
COMMENT ON COLUMN lowcap_positions.status IS 'Position status: dormant (< 300 bars), watchlist (ready to trade), active (holding), shadow (counterfactual position for learning), paused, archived, regime_driver (regime engine driver positions)';
COMMENT ON COLUMN lowcap_positions.entry_event IS 'Entry event type: S2.entry (primary) or S1.retest_entry (secondary). Used for learning system pattern keys.';
