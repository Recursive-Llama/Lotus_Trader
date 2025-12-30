-- Token-Timeframe Blocks for Episode Gating
-- 
-- Deterministic safety latch - NOT learned
-- Prevents re-entry on tokens that have proven hostile
-- Clears when a successful episode is observed
--
-- Part of Scaling A/E v2 Implementation (Phase 6)

CREATE TABLE IF NOT EXISTS token_timeframe_blocks (
    token_contract TEXT NOT NULL,
    token_chain TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    book_id TEXT NOT NULL DEFAULT 'onchain_crypto',
    
    -- Block state (deterministic, not learned)
    blocked_s1 BOOLEAN DEFAULT FALSE,
    blocked_s2 BOOLEAN DEFAULT FALSE,
    
    -- Timestamps for unblock logic
    -- Unblock happens when last_success_ts > last_*_failure_ts
    last_s1_failure_ts TIMESTAMPTZ,
    last_s2_failure_ts TIMESTAMPTZ,
    last_success_ts TIMESTAMPTZ,
    
    -- Tracking
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (token_contract, token_chain, timeframe, book_id)
);

-- Index for fast lookup during entry decisions
CREATE INDEX IF NOT EXISTS idx_token_blocks_lookup 
ON token_timeframe_blocks(token_contract, token_chain, timeframe, book_id)
WHERE blocked_s1 = TRUE OR blocked_s2 = TRUE;

-- Comment on table
COMMENT ON TABLE token_timeframe_blocks IS 
'Episode-based token blocking for risk control. Blocks entry after failures, unblocks after observed success.';

COMMENT ON COLUMN token_timeframe_blocks.blocked_s1 IS 
'True if S1 entry is blocked due to prior S1 failure (attempt ended S0 after we entered S1)';

COMMENT ON COLUMN token_timeframe_blocks.blocked_s2 IS 
'True if S2 entry is blocked due to prior S2 failure (attempt ended S0 after we entered S2)';

