-- Migration: Add 'regime_driver' status to lowcap_positions check constraint
-- Allows regime driver positions (BTC, ALT, buckets, dominance) to be stored

-- Drop existing constraint
ALTER TABLE lowcap_positions DROP CONSTRAINT IF EXISTS check_status;

-- Recreate constraint with 'regime_driver' added
ALTER TABLE lowcap_positions ADD CONSTRAINT check_status 
    CHECK (status IN ('dormant', 'watchlist', 'active', 'paused', 'archived', 'regime_driver'));

-- Update comment to reflect new status
COMMENT ON COLUMN lowcap_positions.status IS 'Position status: dormant (< 300 bars), watchlist (ready to trade), active (holding), paused, archived, regime_driver (regime engine driver positions)';

