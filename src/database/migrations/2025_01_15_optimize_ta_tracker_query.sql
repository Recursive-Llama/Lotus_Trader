-- Migration: Optimize TA Tracker position query performance
-- Adds composite index on (timeframe, status) to match query pattern
-- This index will significantly speed up queries that filter by timeframe and status

-- Create composite index matching the query pattern in ta_tracker.py
-- Query filters: .eq("timeframe", ...) .in_("status", ["watchlist", "active"])
-- Index order: timeframe first (most selective), then status
CREATE INDEX IF NOT EXISTS idx_lowcap_positions_timeframe_status 
    ON lowcap_positions(timeframe, status);

-- Create partial index for the specific status values used in TA tracker
-- This is even more efficient for the common query pattern
CREATE INDEX IF NOT EXISTS idx_lowcap_positions_timeframe_watchlist_active 
    ON lowcap_positions(timeframe, id) 
    WHERE status IN ('watchlist', 'active');

-- Add comment explaining the optimization
COMMENT ON INDEX idx_lowcap_positions_timeframe_status IS 
    'Composite index for TA tracker queries filtering by timeframe and status. Optimizes _active_positions_chunked() performance.';

COMMENT ON INDEX idx_lowcap_positions_timeframe_watchlist_active IS 
    'Partial index for TA tracker queries on watchlist/active positions. More efficient than full index for this specific query pattern.';

