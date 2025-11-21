-- Token Cap Bucket Schema

CREATE TABLE IF NOT EXISTS public.token_cap_bucket (
  token_contract TEXT NOT NULL,
  chain          TEXT NOT NULL,
  bucket         TEXT NOT NULL CHECK (bucket IN ('nano','micro','mid','big','large','xl')),
  market_cap_usd DOUBLE PRECISION NOT NULL,
  circulating_supply DOUBLE PRECISION,
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (token_contract, chain)
);

CREATE INDEX IF NOT EXISTS idx_token_cap_bucket_bucket
  ON public.token_cap_bucket (bucket);

COMMENT ON TABLE public.token_cap_bucket IS 'Latest market cap bucket tagging per token×chain.';

