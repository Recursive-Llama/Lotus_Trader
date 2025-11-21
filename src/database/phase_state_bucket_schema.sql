-- Phase State Bucket Schema (per-cap bucket regime scores)

CREATE TABLE IF NOT EXISTS public.phase_state_bucket (
  bucket           TEXT NOT NULL CHECK (bucket IN ('nano','micro','mid','big','large','xl')),
  horizon          TEXT NOT NULL CHECK (horizon IN ('macro','meso','micro')),
  ts               TIMESTAMPTZ NOT NULL,
  phase            TEXT NOT NULL,
  score            DOUBLE PRECISION NOT NULL,
  slope            DOUBLE PRECISION,
  curvature        DOUBLE PRECISION,
  delta_res        DOUBLE PRECISION,
  confidence       DOUBLE PRECISION,
  population_count INTEGER NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (bucket, horizon, ts)
);

CREATE INDEX IF NOT EXISTS idx_phase_state_bucket_ts
  ON public.phase_state_bucket (ts DESC);

COMMENT ON TABLE public.phase_state_bucket IS 'SPIRAL phase outputs per market-cap bucket × horizon with diagnostics';

