-- Alpha Detector Market Data Schema
-- Phase 1.2: Market data collection for Trading Intelligence System

-- =============================================
-- MARKET DATA TABLE
-- =============================================

-- alpha_market_data_ticks table - Raw tick data from WebSocket
CREATE TABLE IF NOT EXISTS alpha_market_data_ticks (
    -- Core tick data
    tick_id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    
    -- Tick metadata
    data_quality_score DECIMAL(3,2) DEFAULT 1.0,
    source VARCHAR(50) DEFAULT 'hyperliquid',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- alpha_market_data_1m table - Rolled-up 1-minute OHLCV data from ticks
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

-- Tick data indexes
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_ticks_symbol_timestamp ON alpha_market_data_ticks(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_ticks_timestamp ON alpha_market_data_ticks(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_ticks_symbol ON alpha_market_data_ticks(symbol);

-- Performance indexes for market data queries
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_1m_symbol_timestamp ON alpha_market_data_1m(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_1m_timestamp ON alpha_market_data_1m(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_1m_symbol ON alpha_market_data_1m(symbol);
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_1m_data_quality ON alpha_market_data_1m(data_quality_score DESC);

-- =============================================
-- MULTI-TIMEFRAME DATA TABLES
-- =============================================

-- 5-minute data table
CREATE TABLE IF NOT EXISTS alpha_market_data_5m (
    -- Core OHLCV data
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    
    -- Data Quality
    data_quality_score DECIMAL(3,2) DEFAULT 1.0,
    source VARCHAR(50) DEFAULT 'hyperliquid',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (symbol, timestamp)
);

-- 15-minute data table
CREATE TABLE IF NOT EXISTS alpha_market_data_15m (
    -- Core OHLCV data
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    
    -- Data Quality
    data_quality_score DECIMAL(3,2) DEFAULT 1.0,
    source VARCHAR(50) DEFAULT 'hyperliquid',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (symbol, timestamp)
);

-- 1-hour data table
CREATE TABLE IF NOT EXISTS alpha_market_data_1h (
    -- Core OHLCV data
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    
    -- Data Quality
    data_quality_score DECIMAL(3,2) DEFAULT 1.0,
    source VARCHAR(50) DEFAULT 'hyperliquid',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (symbol, timestamp)
);

-- 4-hour data table
CREATE TABLE IF NOT EXISTS alpha_market_data_4h (
    -- Core OHLCV data
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    
    -- Data Quality
    data_quality_score DECIMAL(3,2) DEFAULT 1.0,
    source VARCHAR(50) DEFAULT 'hyperliquid',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (symbol, timestamp)
);

-- =============================================
-- MULTI-TIMEFRAME INDEXES
-- =============================================

-- 5-minute indexes
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_5m_symbol_timestamp ON alpha_market_data_5m(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_5m_timestamp ON alpha_market_data_5m(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_5m_symbol ON alpha_market_data_5m(symbol);

-- 15-minute indexes
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_15m_symbol_timestamp ON alpha_market_data_15m(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_15m_timestamp ON alpha_market_data_15m(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_15m_symbol ON alpha_market_data_15m(symbol);

-- 1-hour indexes
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_1h_symbol_timestamp ON alpha_market_data_1h(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_1h_timestamp ON alpha_market_data_1h(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_1h_symbol ON alpha_market_data_1h(symbol);

-- 4-hour indexes
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_4h_symbol_timestamp ON alpha_market_data_4h(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_4h_timestamp ON alpha_market_data_4h(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_market_data_4h_symbol ON alpha_market_data_4h(symbol);

-- =============================================
-- COMMENTS
-- =============================================

COMMENT ON TABLE alpha_market_data_1m IS 'Raw 1-minute OHLCV market data from Hyperliquid WebSocket';
COMMENT ON TABLE alpha_market_data_5m IS 'Rolled-up 5-minute OHLCV market data';
COMMENT ON TABLE alpha_market_data_15m IS 'Rolled-up 15-minute OHLCV market data';
COMMENT ON TABLE alpha_market_data_1h IS 'Rolled-up 1-hour OHLCV market data';
COMMENT ON TABLE alpha_market_data_4h IS 'Rolled-up 4-hour OHLCV market data';
COMMENT ON COLUMN alpha_market_data_1m.data_quality_score IS 'Data quality score for monitoring gaps and issues';
COMMENT ON COLUMN alpha_market_data_1m.source IS 'Data source identifier (hyperliquid, etc.)';
