-- Lowcap Price Data OHLCV Schema
-- Multi-timeframe OHLCV data for lowcap positions
-- Supports 1m, 5m, 15m, 1h, 4h, 1d timeframes

CREATE TABLE IF NOT EXISTS public.lowcap_price_data_ohlc (
  token_contract    TEXT NOT NULL,
  chain            TEXT NOT NULL,
  timeframe        TEXT NOT NULL,  -- '1m', '5m', '15m', '1h', '4h', '1d'
  timestamp        TIMESTAMPTZ NOT NULL,
  
  -- Native prices (for decisions)
  open_native      NUMERIC NOT NULL,
  high_native      NUMERIC NOT NULL,
  low_native       NUMERIC NOT NULL,
  close_native     NUMERIC NOT NULL,
  
  -- USD prices (for analysis)
  open_usd         NUMERIC NOT NULL,
  high_usd         NUMERIC NOT NULL,
  low_usd          NUMERIC NOT NULL,
  close_usd        NUMERIC NOT NULL,
  
  -- Volume (sum of 1m volumes for timeframe)
  volume           NUMERIC NOT NULL,
  
  -- Market data snapshots (carried from latest component bar)
  liquidity_usd      NUMERIC,
  liquidity_change_1m NUMERIC,
  price_change_24h   NUMERIC,
  market_cap         NUMERIC,
  fdv                NUMERIC,
  dex_id             TEXT,
  pair_address       TEXT,
  
  -- Metadata
  source           TEXT DEFAULT 'rollup',
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  
  PRIMARY KEY (token_contract, chain, timeframe, timestamp)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_lowcap_ohlc_token_timeframe_ts 
  ON public.lowcap_price_data_ohlc (token_contract, timeframe, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_lowcap_ohlc_timeframe_ts 
  ON public.lowcap_price_data_ohlc (timeframe, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_lowcap_ohlc_token_ts 
  ON public.lowcap_price_data_ohlc (token_contract, timestamp DESC);

-- Comments
COMMENT ON TABLE public.lowcap_price_data_ohlc IS 'Multi-timeframe OHLCV data for lowcap positions';
COMMENT ON COLUMN public.lowcap_price_data_ohlc.timeframe IS 'Timeframe: 1m, 5m, 15m, 1h, 4h, 1d';
COMMENT ON COLUMN public.lowcap_price_data_ohlc.open_native IS 'Opening price in native token units';
COMMENT ON COLUMN public.lowcap_price_data_ohlc.high_native IS 'Highest price in native token units';
COMMENT ON COLUMN public.lowcap_price_data_ohlc.low_native IS 'Lowest price in native token units';
COMMENT ON COLUMN public.lowcap_price_data_ohlc.close_native IS 'Closing price in native token units';
COMMENT ON COLUMN public.lowcap_price_data_ohlc.volume IS 'Total volume for the timeframe (sum of 1m volumes)';
COMMENT ON COLUMN public.lowcap_price_data_ohlc.liquidity_usd IS 'Latest liquidity snapshot in USD';
COMMENT ON COLUMN public.lowcap_price_data_ohlc.liquidity_change_1m IS 'Change in liquidity since previous raw entry';
COMMENT ON COLUMN public.lowcap_price_data_ohlc.price_change_24h IS '24-hour price change percentage (latest snapshot)';
COMMENT ON COLUMN public.lowcap_price_data_ohlc.market_cap IS 'Market capitalization snapshot in USD';
COMMENT ON COLUMN public.lowcap_price_data_ohlc.fdv IS 'Fully diluted valuation snapshot in USD';
COMMENT ON COLUMN public.lowcap_price_data_ohlc.dex_id IS 'Source DEX identifier (raydium, uniswap, etc.)';
COMMENT ON COLUMN public.lowcap_price_data_ohlc.pair_address IS 'DEX pair address used for pricing';
COMMENT ON COLUMN public.lowcap_price_data_ohlc.source IS 'Data source: rollup, external, etc.';
