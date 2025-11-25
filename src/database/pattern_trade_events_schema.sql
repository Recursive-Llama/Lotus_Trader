-- Pattern Trade Events Database Schema
-- Fact table for raw trade outcomes (Entry, Add, Trim, Exit actions) with full context.
-- Used by: Lesson Builder (Mining) to discover stable patterns.

-- Drop existing table if it exists
DROP TABLE IF EXISTS pattern_trade_events CASCADE;

-- Create pattern_trade_events table
CREATE TABLE pattern_trade_events (
    id BIGSERIAL PRIMARY KEY,
    pattern_key TEXT NOT NULL,                      -- Canonical pattern: "pm.uptrend.S1.buy_flag"
    action_category TEXT NOT NULL,                  -- "entry", "add", "trim", "exit"
    scope JSONB NOT NULL,                           -- Full unified context: {chain, bucket, timeframe, phase...}
    rr FLOAT NOT NULL,                              -- Realized R/R for this action (or attributed trade R/R)
    pnl_usd FLOAT,                                  -- Realized PnL in USD
    trade_id UUID NOT NULL,                         -- Link to the parent trade (for joining/deduping)
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),   -- When the action occurred
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for efficient mining
-- 1. Lookup by pattern (Primary mining path)
CREATE INDEX idx_pte_pattern_key ON pattern_trade_events(pattern_key, action_category);

-- 2. GIN index for scope slicing (e.g. WHERE scope->>'chain' = 'solana')
CREATE INDEX idx_pte_scope ON pattern_trade_events USING GIN(scope);

-- 3. Time-based index for decay analysis and recent window scans
CREATE INDEX idx_pte_timestamp ON pattern_trade_events(timestamp DESC);

-- 4. Trade ID for joins
CREATE INDEX idx_pte_trade_id ON pattern_trade_events(trade_id);

-- Comments
COMMENT ON TABLE pattern_trade_events IS 'Raw fact table for trade actions and outcomes. Source of truth for the Learning Miner.';
COMMENT ON COLUMN pattern_trade_events.scope IS 'Full unified scope context at the time of action (entry/regime/action context merged).';
COMMENT ON COLUMN pattern_trade_events.rr IS 'Outcome metric (usually final trade R/R attributed to this action).';

