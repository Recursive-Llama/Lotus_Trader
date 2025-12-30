-- Wallet Balance Snapshots Schema
-- Tracks portfolio balance over time for PnL calculations
-- Daily snapshots → Weekly aggregates → Monthly aggregates (kept forever)

-- Drop existing table if it exists
DROP TABLE IF EXISTS wallet_balance_snapshots CASCADE;

-- Create wallet_balance_snapshots table
CREATE TABLE wallet_balance_snapshots (
    id SERIAL PRIMARY KEY,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    snapshot_type TEXT NOT NULL DEFAULT 'daily',  -- 'daily', 'weekly', 'monthly'
    total_balance_usd FLOAT NOT NULL,              -- USDC + active positions
    usdc_total FLOAT NOT NULL,                     -- Sum of all USDC across chains
    active_positions_value FLOAT NOT NULL,         -- Sum of current_usd_value for active positions
    active_positions_count INT NOT NULL,           -- Count of active positions
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for time-based queries
CREATE INDEX idx_wallet_snapshots_captured_at ON wallet_balance_snapshots(captured_at DESC);
CREATE INDEX idx_wallet_snapshots_type ON wallet_balance_snapshots(snapshot_type, captured_at DESC);

-- Comments
COMMENT ON TABLE wallet_balance_snapshots IS 'Portfolio balance snapshots: daily (7 days), weekly (4 weeks), monthly (forever)';
COMMENT ON COLUMN wallet_balance_snapshots.snapshot_type IS 'Type: daily (kept 7 days), weekly (kept 4 weeks), monthly (kept forever)';
COMMENT ON COLUMN wallet_balance_snapshots.total_balance_usd IS 'Total portfolio value: USDC + active positions';
COMMENT ON COLUMN wallet_balance_snapshots.usdc_total IS 'Sum of USDC balance across all chains';
COMMENT ON COLUMN wallet_balance_snapshots.active_positions_value IS 'Sum of current_usd_value for all active positions';

