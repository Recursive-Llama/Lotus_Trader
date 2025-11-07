-- Price Data Schema
-- Unified price data collection for multi-chain token pricing
-- Phase 1: 1-minute price data collection

-- =============================================
-- PRICE DATA TABLE
-- =============================================

-- lowcap_price_data_1m table - 1-minute price snapshots from DexScreener
CREATE TABLE IF NOT EXISTS lowcap_price_data_1m (
    -- Core identifiers
    token_contract TEXT NOT NULL,
    chain TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    
    -- Raw price data (from DexScreener API)
    price_usd DECIMAL(20,8) NOT NULL,
    price_native DECIMAL(20,8) NOT NULL,
    quote_token TEXT NOT NULL,
    
    -- Market data
    liquidity_usd DECIMAL(20,2),
    liquidity_change_1m DECIMAL(20,2), -- Liquidity difference from previous 1-minute reading
    volume_24h DECIMAL(20,2),
    volume_change_1m DECIMAL(20,2), -- Volume difference from previous 1-minute reading
    price_change_24h DECIMAL(8,4),
    market_cap DECIMAL(20,2),
    fdv DECIMAL(20,2),
    
    -- Metadata
    dex_id TEXT,
    pair_address TEXT,
    source TEXT DEFAULT 'dexscreener',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (token_contract, chain, timestamp)
);

-- =============================================
-- INDEXES
-- =============================================

-- Core query indexes
CREATE INDEX IF NOT EXISTS idx_lowcap_price_data_1m_token_timestamp ON lowcap_price_data_1m(token_contract, chain, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_lowcap_price_data_1m_timestamp ON lowcap_price_data_1m(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_lowcap_price_data_1m_chain ON lowcap_price_data_1m(chain);

-- Performance indexes for common queries
CREATE INDEX IF NOT EXISTS idx_lowcap_price_data_1m_token_chain ON lowcap_price_data_1m(token_contract, chain);
CREATE INDEX IF NOT EXISTS idx_lowcap_price_data_1m_created_at ON lowcap_price_data_1m(created_at DESC);

-- =============================================
-- COMMENTS
-- =============================================

COMMENT ON TABLE lowcap_price_data_1m IS '1-minute price snapshots from DexScreener API for multi-chain tokens';
COMMENT ON COLUMN lowcap_price_data_1m.token_contract IS 'Token contract address';
COMMENT ON COLUMN lowcap_price_data_1m.chain IS 'Blockchain network (solana, base, bsc, ethereum)';
COMMENT ON COLUMN lowcap_price_data_1m.timestamp IS 'Price snapshot timestamp (1-minute intervals)';
COMMENT ON COLUMN lowcap_price_data_1m.price_usd IS 'Token price in USD';
COMMENT ON COLUMN lowcap_price_data_1m.price_native IS 'Token price in native token (SOL, ETH, BNB)';
COMMENT ON COLUMN lowcap_price_data_1m.quote_token IS 'Quote token symbol (SOL, WETH, WBNB, USDC)';
COMMENT ON COLUMN lowcap_price_data_1m.liquidity_usd IS 'Total liquidity in USD';
COMMENT ON COLUMN lowcap_price_data_1m.liquidity_change_1m IS 'Liquidity difference from previous 1-minute reading (for liquidity monitoring)';
COMMENT ON COLUMN lowcap_price_data_1m.volume_24h IS '24-hour trading volume in USD';
COMMENT ON COLUMN lowcap_price_data_1m.volume_change_1m IS 'Volume difference from previous 1-minute reading (volume per candle)';
COMMENT ON COLUMN lowcap_price_data_1m.price_change_24h IS '24-hour price change percentage';
COMMENT ON COLUMN lowcap_price_data_1m.market_cap IS 'Market capitalization in USD';
COMMENT ON COLUMN lowcap_price_data_1m.fdv IS 'Fully diluted valuation in USD';
COMMENT ON COLUMN lowcap_price_data_1m.dex_id IS 'DEX identifier (raydium, uniswap, pancake, etc.)';
COMMENT ON COLUMN lowcap_price_data_1m.pair_address IS 'Trading pair contract address';
COMMENT ON COLUMN lowcap_price_data_1m.source IS 'Data source (dexscreener)';

-- =============================================
-- FUTURE ROLLUP TABLES (Phase 2)
-- =============================================

-- Note: These tables will be added in Phase 2 for data rollups
-- lowcap_price_data_5m, lowcap_price_data_15m, lowcap_price_data_1h, lowcap_price_data_4h
-- Following the same pattern as alpha_market_data_schema.sql
