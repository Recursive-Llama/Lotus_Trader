-- Regime Price Data OHLC Schema
-- OHLC data for regime drivers: BTC, ALT composite, market cap buckets, dominance
-- Used by Regime Engine for computing market regime states

CREATE TABLE IF NOT EXISTS public.regime_price_data_ohlc (
    -- Primary key: driver + timeframe + timestamp
    driver TEXT NOT NULL,              -- 'BTC', 'ALT', 'nano', 'small', 'mid', 'big', 'BTC.d', 'USDT.d'
    timeframe TEXT NOT NULL,           -- '1m', '1h', '1d' (regime timeframes)
    timestamp TIMESTAMPTZ NOT NULL,
    
    -- Book ID for multi-asset support
    book_id TEXT NOT NULL DEFAULT 'onchain_crypto',  -- 'onchain_crypto', 'spot_crypto', 'perp_crypto'
    
    -- OHLC prices (USD for majors/composites, percentage for dominance)
    open_usd NUMERIC NOT NULL,
    high_usd NUMERIC NOT NULL,
    low_usd NUMERIC NOT NULL,
    close_usd NUMERIC NOT NULL,
    
    -- Volume (sum for composites, may be 0 for dominance)
    volume NUMERIC NOT NULL DEFAULT 0,
    
    -- Metadata
    source TEXT NOT NULL DEFAULT 'binance',  -- 'binance', 'composite', 'coingecko'
    component_count INT,                      -- Number of tokens in composite (for ALT, buckets)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (driver, book_id, timeframe, timestamp)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_regime_ohlc_driver_tf_ts 
    ON public.regime_price_data_ohlc (driver, timeframe, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_regime_ohlc_book_driver_tf 
    ON public.regime_price_data_ohlc (book_id, driver, timeframe, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_regime_ohlc_tf_ts 
    ON public.regime_price_data_ohlc (timeframe, timestamp DESC);

-- Composite index for TA computation queries
CREATE INDEX IF NOT EXISTS idx_regime_ohlc_driver_book_tf_ts 
    ON public.regime_price_data_ohlc (driver, book_id, timeframe, timestamp DESC);

-- Comments
COMMENT ON TABLE public.regime_price_data_ohlc IS 'OHLC data for regime drivers (BTC, ALT, buckets, dominance)';
COMMENT ON COLUMN public.regime_price_data_ohlc.driver IS 'Regime driver: BTC, ALT, nano, small, mid, big, BTC.d, USDT.d';
COMMENT ON COLUMN public.regime_price_data_ohlc.timeframe IS 'Regime timeframe: 1m (micro), 1h (meso), 1d (macro)';
COMMENT ON COLUMN public.regime_price_data_ohlc.book_id IS 'Asset class book: onchain_crypto, spot_crypto, perp_crypto';
COMMENT ON COLUMN public.regime_price_data_ohlc.open_usd IS 'Open price (USD for majors/composites, percentage for dominance treated as USD)';
COMMENT ON COLUMN public.regime_price_data_ohlc.high_usd IS 'High price (USD or percentage)';
COMMENT ON COLUMN public.regime_price_data_ohlc.low_usd IS 'Low price (USD or percentage)';
COMMENT ON COLUMN public.regime_price_data_ohlc.close_usd IS 'Close price (USD or percentage)';
COMMENT ON COLUMN public.regime_price_data_ohlc.volume IS 'Volume (sum for composites, 0 for dominance)';
COMMENT ON COLUMN public.regime_price_data_ohlc.source IS 'Data source: binance, composite, coingecko';
COMMENT ON COLUMN public.regime_price_data_ohlc.component_count IS 'Number of tokens in composite (ALT, buckets)';

-- Check constraint for driver enum
ALTER TABLE public.regime_price_data_ohlc ADD CONSTRAINT check_driver 
    CHECK (driver IN ('BTC', 'ALT', 'nano', 'small', 'mid', 'big', 'BTC.d', 'USDT.d'));

-- Check constraint for timeframe enum
ALTER TABLE public.regime_price_data_ohlc ADD CONSTRAINT check_timeframe 
    CHECK (timeframe IN ('1m', '1h', '1d'));

