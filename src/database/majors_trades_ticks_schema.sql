-- Majors Trades Ticks Schema (Hyperliquid)
-- Raw trade ticks used to roll up to 1m OHLCV for majors

CREATE TABLE IF NOT EXISTS public.majors_trades_ticks (
  token       TEXT        NOT NULL,   -- 'BTC','ETH','BNB','SOL','HYPE'
  ts          TIMESTAMPTZ NOT NULL,   -- trade timestamp (UTC)
  price       NUMERIC     NOT NULL,
  size        NUMERIC     NOT NULL,   -- base size; quote volume can be summed via price*size
  side        TEXT        NULL,       -- optional: 'buy' | 'sell'
  trade_id    TEXT        NULL,
  source      TEXT        NOT NULL DEFAULT 'hyperliquid',
  inserted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (token, ts, trade_id)
);

-- Helpful indexes for time-range queries
CREATE INDEX IF NOT EXISTS idx_majors_trades_ticks_ts
  ON public.majors_trades_ticks (ts DESC);

COMMENT ON TABLE  public.majors_trades_ticks IS 'Raw Hyperliquid trades for majors; rolled up to 1m OHLCV';
COMMENT ON COLUMN public.majors_trades_ticks.token IS 'Ticker: BTC, ETH, BNB, SOL, HYPE';
COMMENT ON COLUMN public.majors_trades_ticks.ts    IS 'Trade timestamp (UTC)';
COMMENT ON COLUMN public.majors_trades_ticks.price IS 'Trade price in USD';
COMMENT ON COLUMN public.majors_trades_ticks.size  IS 'Base amount traded';
COMMENT ON COLUMN public.majors_trades_ticks.side  IS 'Buy/Sell if available';
COMMENT ON COLUMN public.majors_trades_ticks.source IS 'Data source (hyperliquid)';


