-- Migration: Add raw dominance level columns to portfolio_bands
-- Date: 2025-10-17

ALTER TABLE IF EXISTS public.portfolio_bands
  ADD COLUMN IF NOT EXISTS btc_dom_level DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS usdt_dom_level DOUBLE PRECISION;

-- Helpful index if querying recent rows often
CREATE INDEX IF NOT EXISTS idx_portfolio_bands_ts_desc ON public.portfolio_bands (ts DESC);


