-- Lowcap Positions v4 Schema
-- Multi-timeframe position model: 4 positions per token (1m, 15m, 1h, 4h)
-- Each timeframe = independent position with own allocation, entries, exits, PnL

-- Drop existing table if it exists (for clean cutover)
DROP TABLE IF EXISTS lowcap_positions CASCADE;

-- Create lowcap positions table (MULTI-TIMEFRAME with independent positions)
CREATE TABLE lowcap_positions (
    -- PRIMARY KEY: Auto-generated UUID
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- TOKEN INFORMATION
    token_chain TEXT NOT NULL,              -- "solana", "ethereum", "base", "bsc"
    token_contract TEXT NOT NULL,           -- Token contract address
    token_ticker TEXT,                      -- "PEPE", "BONK" (optional, for display)
    
    -- TIMEFRAME (NEW - key to multi-timeframe model)
    timeframe TEXT NOT NULL,                -- "1m", "15m", "1h", "4h"
    
    -- UNIQUE CONSTRAINT: One position per (token, chain, timeframe)
    CONSTRAINT unique_token_timeframe UNIQUE (token_contract, token_chain, timeframe),
    
    -- STATUS (NEW - dormant/watchlist/active flow)
    status TEXT NOT NULL DEFAULT 'watchlist', -- "dormant", "watchlist", "active", "paused", "archived"
    
    -- DATA AVAILABILITY GATING
    bars_count INTEGER DEFAULT 0,           -- Number of OHLC bars available for this timeframe
    bars_threshold INTEGER DEFAULT 350,     -- Minimum bars required to trade (configurable per TF)
    
    -- ALLOCATION (timeframe-specific)
    alloc_cap_usd NUMERIC NOT NULL,         -- Allocation cap for this timeframe position
    alloc_policy JSONB,                     -- Timeframe-specific config (allocation splits, thresholds, etc.)
    
    -- POSITION TRACKING
    total_quantity FLOAT DEFAULT 0,         -- Total tokens held (sum of all entries - exits)
    total_allocation_pct FLOAT,             -- Total allocation percentage (from Decision Maker, for reference)
    total_allocation_usd NUMERIC,           -- Total allocation USD (from Decision Maker, for reference)
    
    -- AGGREGATE PERFORMANCE
    total_pnl_usd FLOAT DEFAULT 0,         -- Total P&L in USD
    total_pnl_pct FLOAT DEFAULT 0,         -- Total P&L percentage
    avg_entry_price FLOAT,                  -- Weighted average entry price
    avg_exit_price FLOAT,                   -- Weighted average exit price
    total_tokens_bought FLOAT DEFAULT 0,    -- Total tokens bought across all entries
    total_tokens_sold FLOAT DEFAULT 0,      -- Total tokens sold across all exits
    total_investment_native FLOAT DEFAULT 0, -- Total native currency invested
    total_extracted_native FLOAT DEFAULT 0,  -- Total native currency extracted
    total_pnl_native FLOAT DEFAULT 0,       -- Total P&L in native currency
    first_entry_timestamp TIMESTAMP WITH TIME ZONE,
    last_activity_timestamp TIMESTAMP WITH TIME ZONE,
    
    -- METADATA
    book_id TEXT DEFAULT 'social',          -- Which book this belongs to
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,
    close_reason TEXT,                      -- Reason for position closure
    
    -- ADDITIONAL TRACKING
    tax_pct FLOAT,                          -- Tax percentage detected for this token
    
    -- JSONB DATA STORAGE
    entries JSONB,                          -- Array of standard entry data
    exits JSONB,                            -- Array of standard exit data
    exit_rules JSONB,                       -- Standard exit strategy rules
    trend_entries JSONB,                    -- Array of trend entry data
    trend_exits JSONB,                      -- Array of trend exit data
    trend_exit_rules JSONB,                 -- Trend exit strategy rules
    curator_sources JSONB,                  -- Curator source information
    
    -- SOURCE TRACKING
    source_tweet_url TEXT,                  -- Original tweet URL that triggered this position
    
    -- NOTES
    notes TEXT,                             -- Any additional notes
    
    -- PM FEATURES & STATE (for Position Manager integration)
    features JSONB,                         -- Cached PM inputs/diagnostics (uptrend_engine_v4, ta, geometry, pm_a_e, pm_execution_history)
    cooldown_until TIMESTAMPTZ,             -- Time gate before new actions
    last_review_at TIMESTAMPTZ,             -- Last PM evaluation time
    time_patience_h INT,                    -- Patience window in hours
    reentry_lock_until TIMESTAMPTZ,         -- Lockout after exits/trails
    trend_entry_count INT DEFAULT 0,        -- Count of trend adds
    new_token_mode BOOLEAN DEFAULT FALSE,   -- New token discovery mode flag
    
    -- LEARNING SYSTEM FIELDS (v4)
    entry_context JSONB,                    -- Lever values at entry (curator, chain, mcap_bucket, vol_bucket, age_bucket, intent, mapping_confidence, etc.)
    completed_trades JSONB DEFAULT '[]'::jsonb  -- Array of completed trade summaries (R/R metrics, entry/exit prices, timestamps)
);

-- Create indexes for performance
CREATE INDEX idx_lowcap_positions_token_timeframe ON lowcap_positions(token_chain, token_contract, timeframe);
CREATE INDEX idx_lowcap_positions_status_timeframe ON lowcap_positions(status, timeframe);
CREATE INDEX idx_lowcap_positions_timeframe ON lowcap_positions(timeframe);
CREATE INDEX idx_lowcap_positions_ticker ON lowcap_positions(token_ticker);
CREATE INDEX idx_lowcap_positions_created ON lowcap_positions(created_at);
CREATE INDEX idx_lowcap_positions_book ON lowcap_positions(book_id);
CREATE INDEX idx_lowcap_positions_active ON lowcap_positions(book_id, status) WHERE status = 'active';
CREATE INDEX idx_lowcap_positions_watchlist_active ON lowcap_positions(status) WHERE status IN ('watchlist', 'active');

-- GIN index for JSONB features column (for fast queries on engine signals, TA, geometry)
CREATE INDEX IF NOT EXISTS idx_lowcap_positions_features_gin ON lowcap_positions USING GIN (features);

-- Create trigger for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_lowcap_position_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_lowcap_position_updated_at
    BEFORE UPDATE ON lowcap_positions
    FOR EACH ROW
    EXECUTE FUNCTION update_lowcap_position_updated_at();

-- Add check constraint for status enum
ALTER TABLE lowcap_positions ADD CONSTRAINT check_status 
    CHECK (status IN ('dormant', 'watchlist', 'active', 'paused', 'archived'));

-- Add check constraint for timeframe enum
ALTER TABLE lowcap_positions ADD CONSTRAINT check_timeframe 
    CHECK (timeframe IN ('1m', '15m', '1h', '4h'));

-- Comments for documentation
COMMENT ON TABLE lowcap_positions IS 'Multi-timeframe positions: 4 positions per token (1m, 15m, 1h, 4h), each with independent allocation and tracking';
COMMENT ON COLUMN lowcap_positions.timeframe IS 'Timeframe for this position: 1m, 15m, 1h, or 4h';
COMMENT ON COLUMN lowcap_positions.status IS 'Position status: dormant (< 350 bars), watchlist (ready to trade), active (holding), paused, archived';
COMMENT ON COLUMN lowcap_positions.bars_count IS 'Number of OHLC bars available for this timeframe (gates trading)';
COMMENT ON COLUMN lowcap_positions.alloc_cap_usd IS 'Allocation cap for this timeframe position (calculated from total_allocation_usd * timeframe_percentage)';
COMMENT ON COLUMN lowcap_positions.alloc_policy IS 'Timeframe-specific config JSONB (allocation splits, thresholds, etc.)';
COMMENT ON COLUMN lowcap_positions.entry_context IS 'Learning system: Lever values at entry (curator, chain, mcap_bucket, vol_bucket, age_bucket, intent, mapping_confidence, etc.) - populated when DM creates position';
COMMENT ON COLUMN lowcap_positions.completed_trades IS 'Learning system: Array of completed trade summaries (R/R metrics, entry/exit prices, timestamps) - populated when position closes';

