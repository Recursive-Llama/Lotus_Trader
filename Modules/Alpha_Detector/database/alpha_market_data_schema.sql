-- Alpha Detector Market Data Schema
-- Phase 1.2: Market data collection for Trading Intelligence System

-- =============================================
-- MARKET DATA TABLE
-- =============================================

-- alpha_market_data_1m table - Raw 1-minute OHLCV data from Hyperliquid
CREATE TABLE IF NOT EXISTS alpha_market_data_1m (
    -- Core OHLCV data
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    
    -- Data Quality
    data_quality_score DECIMAL(3,2) DEFAULT 1.0, -- Data quality score (0-1)
    source VARCHAR(50) DEFAULT 'hyperliquid', -- Data source
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (symbol, timestamp)
);

-- =============================================
-- INDEXES
-- =============================================

-- Performance indexes for market data queries
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_1m_symbol_timestamp ON alpha_market_data_1m(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_1m_timestamp ON alpha_market_data_1m(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_1m_symbol ON alpha_market_data_1m(symbol);
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_1m_data_quality ON alpha_market_data_1m(data_quality_score DESC);

-- =============================================
-- COMMENTS
-- =============================================

COMMENT ON TABLE alpha_market_data_1m IS 'Raw 1-minute OHLCV market data from Hyperliquid WebSocket';
COMMENT ON COLUMN alpha_market_data_1m.data_quality_score IS 'Data quality score for monitoring gaps and issues';
COMMENT ON COLUMN alpha_market_data_1m.source IS 'Data source identifier (hyperliquid, etc.)';
