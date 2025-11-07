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
  
  -- Volume (if available)
  volume           NUMERIC,           -- Volume for this 1-minute period (optional)
  
  -- Metadata
  source           TEXT DEFAULT 'price_collector',
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
COMMENT ON COLUMN public.lowcap_price_data_1m.volume IS 'Volume for this 1-minute period (optional, may be null)';
COMMENT ON COLUMN public.lowcap_price_data_1m.source IS 'Data source: price_collector, external, etc.';

