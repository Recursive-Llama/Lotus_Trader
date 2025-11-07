-- Majors Price Data OHLCV Schema
-- Similar to lowcap_price_data_ohlc but for majors data

CREATE TABLE IF NOT EXISTS public.majors_price_data_ohlc (
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
  
  -- Metadata
  source           TEXT DEFAULT 'rollup',
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  
  PRIMARY KEY (token_contract, chain, timeframe, timestamp)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_majors_ohlc_token_timeframe_ts 
  ON public.majors_price_data_ohlc (token_contract, timeframe, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_majors_ohlc_timeframe_ts 
  ON public.majors_price_data_ohlc (timeframe, timestamp DESC);

-- Comments
COMMENT ON TABLE public.majors_price_data_ohlc IS 'OHLCV data for major cryptocurrencies across multiple timeframes';
COMMENT ON COLUMN public.majors_price_data_ohlc.token_contract IS 'Token contract address';
COMMENT ON COLUMN public.majors_price_data_ohlc.chain IS 'Blockchain network';
COMMENT ON COLUMN public.majors_price_data_ohlc.timeframe IS 'Timeframe: 1m, 5m, 15m, 1h, 4h, 1d';
COMMENT ON COLUMN public.majors_price_data_ohlc.open_native IS 'Opening price in native currency';
COMMENT ON COLUMN public.majors_price_data_ohlc.high_native IS 'Highest price in native currency';
COMMENT ON COLUMN public.majors_price_data_ohlc.low_native IS 'Lowest price in native currency';
COMMENT ON COLUMN public.majors_price_data_ohlc.close_native IS 'Closing price in native currency';
COMMENT ON COLUMN public.majors_price_data_ohlc.open_usd IS 'Opening price in USD';
COMMENT ON COLUMN public.majors_price_data_ohlc.high_usd IS 'Highest price in USD';
COMMENT ON COLUMN public.majors_price_data_ohlc.low_usd IS 'Lowest price in USD';
COMMENT ON COLUMN public.majors_price_data_ohlc.close_usd IS 'Closing price in USD';
COMMENT ON COLUMN public.majors_price_data_ohlc.volume IS 'Total volume for the timeframe';
COMMENT ON COLUMN public.majors_price_data_ohlc.source IS 'Data source: rollup, hyperliquid, etc.';
