-- Majors 1m OHLCV rolled up from Hyperliquid ticks
-- Mirrors lowcap 1m structure semantically but simplified to OHLCV

CREATE TABLE IF NOT EXISTS public.majors_price_data_1m (
  token      TEXT        NOT NULL,   -- 'BTC','ETH','BNB','SOL','HYPE'
  ts         TIMESTAMPTZ NOT NULL,   -- minute start UTC
  open       NUMERIC     NOT NULL,
  high       NUMERIC     NOT NULL,
  low        NUMERIC     NOT NULL,
  close      NUMERIC     NOT NULL,
  volume     NUMERIC     NOT NULL,   -- quote volume in USD if available; else Σ(price*size)
  source     TEXT        NOT NULL DEFAULT 'hyperliquid',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (token, ts)
);

CREATE INDEX IF NOT EXISTS idx_majors_price_data_1m_ts
  ON public.majors_price_data_1m (ts DESC);

COMMENT ON TABLE  public.majors_price_data_1m IS '1m OHLCV for majors (BTC, ETH, BNB, SOL, HYPE) from Hyperliquid';
COMMENT ON COLUMN public.majors_price_data_1m.volume IS 'Quote USD volume; fallback Σ(price*size)';


