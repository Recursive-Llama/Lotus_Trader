-- Migration: Allow '1d' timeframe in lowcap_positions table
-- Date: 2025-12-05
-- Reason: Regime drivers need to store 1d (macro) timeframe, but current constraint only allows '1m', '15m', '1h', '4h'
-- This removes the confusing mapping where 1d regime timeframe was stored as 4h position timeframe

-- Drop existing constraint
ALTER TABLE lowcap_positions DROP CONSTRAINT IF EXISTS check_timeframe;

-- Add new constraint that includes '1d'
ALTER TABLE lowcap_positions ADD CONSTRAINT check_timeframe 
    CHECK (timeframe IN ('1m', '15m', '1h', '4h', '1d'));

-- Update comment to reflect new allowed values
COMMENT ON COLUMN lowcap_positions.timeframe IS 'Timeframe for this position: 1m, 15m, 1h, 4h, or 1d (1d used for regime drivers)';

