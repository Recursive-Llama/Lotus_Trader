-- Native token balance tracking table (single row per chain)
-- Stores current native token balances for portfolio tracking

CREATE TABLE wallet_balances (
    chain TEXT PRIMARY KEY,                 -- 'solana', 'ethereum', 'base', 'bsc', 'lotus'
    balance FLOAT NOT NULL,                 -- Current native token balance
    balance_usd FLOAT,                      -- Current USD value
    usdc_balance FLOAT,                     -- Current USDC balance (for tracking USDC separately per chain)
    wallet_address TEXT,                    -- Wallet address for reference
    positions JSONB DEFAULT '{}'::jsonb,  -- JSONB column for additional data (e.g., buyback totals for 'lotus' chain)
    last_updated TIMESTAMPTZ DEFAULT NOW()  -- When balance was last updated
);

-- Index for performance
CREATE INDEX idx_wallet_balances_chain ON wallet_balances(chain);

