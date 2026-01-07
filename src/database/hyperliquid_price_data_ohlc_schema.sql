-- Hyperliquid Price Data OHLC Schema
-- OHLC candle data for Hyperliquid perpetual futures (main DEX + HIP-3)
-- Supports 15m, 1h, 4h timeframes (as used by PM)
-- Data collected via WebSocket candle subscriptions and candleSnapshot backfill

CREATE TABLE IF NOT EXISTS public.hyperliquid_price_data_ohlc (
  token            TEXT NOT NULL,        -- "BTC" or "xyz:TSLA" (HIP-3 format)
  timeframe        TEXT NOT NULL,        -- '15m', '1h', '4h'
  ts               TIMESTAMPTZ NOT NULL, -- Start of candle (from Hyperliquid "t" field)
  
  -- OHLC prices (USD, since Hyperliquid perps are USD-denominated)
  open             NUMERIC NOT NULL,
  high             NUMERIC NOT NULL,
  low              NUMERIC NOT NULL,
  close            NUMERIC NOT NULL,
  
  -- Volume and trade count
  volume           NUMERIC NOT NULL,    -- Volume from "v" field
  trades           INTEGER,             -- Number of trades from "n" field
  
  -- Metadata
  source           TEXT DEFAULT 'hyperliquid_ws',  -- 'hyperliquid_ws', 'hyperliquid_snapshot'
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  
  PRIMARY KEY (token, timeframe, ts)
);

-- Indexes for fast queries (matching pattern from lowcap_price_data_ohlc)
CREATE INDEX IF NOT EXISTS idx_hyperliquid_ohlc_token_timeframe_ts 
  ON public.hyperliquid_price_data_ohlc (token, timeframe, ts DESC);

CREATE INDEX IF NOT EXISTS idx_hyperliquid_ohlc_timeframe_ts 
  ON public.hyperliquid_price_data_ohlc (timeframe, ts DESC);

CREATE INDEX IF NOT EXISTS idx_hyperliquid_ohlc_token_ts 
  ON public.hyperliquid_price_data_ohlc (token, ts DESC);

-- Comments
COMMENT ON TABLE public.hyperliquid_price_data_ohlc IS 'OHLC candle data for Hyperliquid perpetual futures (main DEX + HIP-3)';
COMMENT ON COLUMN public.hyperliquid_price_data_ohlc.token IS 'Token symbol: "BTC" for main DEX, "xyz:TSLA" for HIP-3';
COMMENT ON COLUMN public.hyperliquid_price_data_ohlc.timeframe IS 'Timeframe: 15m, 1h, 4h (as used by PM)';
COMMENT ON COLUMN public.hyperliquid_price_data_ohlc.ts IS 'Start timestamp of candle (from Hyperliquid "t" field, epoch milliseconds converted to TIMESTAMPTZ)';
COMMENT ON COLUMN public.hyperliquid_price_data_ohlc.volume IS 'Total volume for the candle (from Hyperliquid "v" field)';
COMMENT ON COLUMN public.hyperliquid_price_data_ohlc.trades IS 'Number of trades in the candle (from Hyperliquid "n" field)';
COMMENT ON COLUMN public.hyperliquid_price_data_ohlc.source IS 'Data source: hyperliquid_ws (WebSocket), hyperliquid_snapshot (backfill)';

