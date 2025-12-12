-- Add partial/coverage fields to OHLC tables

ALTER TABLE public.lowcap_price_data_ohlc
  ADD COLUMN IF NOT EXISTS partial boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS coverage_pct numeric,
  ADD COLUMN IF NOT EXISTS bars_used integer,
  ADD COLUMN IF NOT EXISTS expected_bars integer;

ALTER TABLE public.majors_price_data_ohlc
  ADD COLUMN IF NOT EXISTS partial boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS coverage_pct numeric,
  ADD COLUMN IF NOT EXISTS bars_used integer,
  ADD COLUMN IF NOT EXISTS expected_bars integer;

-- Optional: index for partial flag if querying frequently
-- CREATE INDEX IF NOT EXISTS idx_lowcap_ohlc_partial ON public.lowcap_price_data_ohlc (partial);

