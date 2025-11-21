-- Lowcap Price Data 1m Schema
-- Raw 1-minute price points (not OHLC bars)
-- Collected by price collector, then rolled up to OHLC bars for all timeframes

CREATE TABLE IF NOT EXISTS public.lowcap_price_data_1m (
  token_contract    TEXT NOT NULL,
  chain            TEXT NOT NULL,
  timestamp        TIMESTAMPTZ NOT NULL,
  
  -- Price data (raw price points)
  price_native     NUMERIC NOT NULL,  -- Price in native token units
  price_usd        NUMERIC NOT NULL,  -- Price in USD
  
  -- Multi-timeframe volume data (from Dexscreener API)
  volume_5m         NUMERIC,          -- 5-minute rolling volume (m5)
  volume_1m         NUMERIC,      -- Calculated 1-minute volume (m5/5)
  volume_1h         NUMERIC,           -- 1-hour volume (h1) for 1h rollups
  volume_6h         NUMERIC,           -- 6-hour volume (h6) for 4h rollups
  volume_24h        NUMERIC,           -- 24-hour volume (h24) for 1d rollups
  
  -- Market data
  quote_token       TEXT,              -- Quote token symbol (SOL, WETH, WBNB, USDC, etc.)
  liquidity_usd      NUMERIC,           -- Total liquidity in USD
  liquidity_change_1m NUMERIC,         -- Liquidity difference from previous entry
  price_change_24h   NUMERIC,           -- 24-hour price change percentage
  market_cap         NUMERIC,           -- Market capitalization in USD
  fdv                NUMERIC,           -- Fully diluted valuation in USD
  
  -- DEX metadata
  dex_id             TEXT,              -- DEX identifier (raydium, uniswap, pancake, etc.)
  pair_address       TEXT,              -- Trading pair contract address
  
  -- Metadata
  source           TEXT DEFAULT 'dexscreener',
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  
  PRIMARY KEY (token_contract, chain, timestamp)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_lowcap_price_1m_token_ts 
  ON public.lowcap_price_data_1m (token_contract, chain, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_lowcap_price_1m_ts 
  ON public.lowcap_price_data_1m (timestamp DESC);

-- Composite index for rollup queries (grouping by token+chain, ordering by time)
CREATE INDEX IF NOT EXISTS idx_lowcap_price_1m_token_chain_ts 
  ON public.lowcap_price_data_1m (token_contract, chain, timestamp DESC);

-- Comments
COMMENT ON TABLE public.lowcap_price_data_1m IS 'Raw 1-minute price points for lowcap positions (rolled up to OHLC bars)';
COMMENT ON COLUMN public.lowcap_price_data_1m.price_native IS 'Price in native token units (for execution)';
COMMENT ON COLUMN public.lowcap_price_data_1m.price_usd IS 'Price in USD (for analysis)';
COMMENT ON COLUMN public.lowcap_price_data_1m.volume_5m IS '5-minute rolling volume (m5) from Dexscreener';
COMMENT ON COLUMN public.lowcap_price_data_1m.volume_1m IS 'Calculated 1-minute volume (m5/5) for 1m OHLC bars';
COMMENT ON COLUMN public.lowcap_price_data_1m.volume_1h IS '1-hour volume (h1) from Dexscreener for 1h rollups';
COMMENT ON COLUMN public.lowcap_price_data_1m.volume_6h IS '6-hour volume (h6) from Dexscreener for 4h rollups';
COMMENT ON COLUMN public.lowcap_price_data_1m.volume_24h IS '24-hour volume (h24) from Dexscreener for 1d rollups';
COMMENT ON COLUMN public.lowcap_price_data_1m.quote_token IS 'Quote token symbol (SOL, WETH, WBNB, USDC, etc.)';
COMMENT ON COLUMN public.lowcap_price_data_1m.liquidity_usd IS 'Total liquidity in USD';
COMMENT ON COLUMN public.lowcap_price_data_1m.liquidity_change_1m IS 'Liquidity difference from previous entry';
COMMENT ON COLUMN public.lowcap_price_data_1m.price_change_24h IS '24-hour price change percentage';
COMMENT ON COLUMN public.lowcap_price_data_1m.market_cap IS 'Market capitalization in USD';
COMMENT ON COLUMN public.lowcap_price_data_1m.fdv IS 'Fully diluted valuation in USD';
COMMENT ON COLUMN public.lowcap_price_data_1m.dex_id IS 'DEX identifier (raydium, uniswap, pancake, etc.)';
COMMENT ON COLUMN public.lowcap_price_data_1m.pair_address IS 'Trading pair contract address';
COMMENT ON COLUMN public.lowcap_price_data_1m.source IS 'Data source: dexscreener, external, etc.';

