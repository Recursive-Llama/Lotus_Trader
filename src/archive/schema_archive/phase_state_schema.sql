-- Phase State Schema (per-horizon labels and diagnostics)

CREATE TABLE IF NOT EXISTS public.phase_state (
  token           TEXT        NOT NULL,
  ts              TIMESTAMPTZ NOT NULL,   -- snapshot time (hourly granular)
  horizon         TEXT        NOT NULL CHECK (horizon IN ('macro','meso','micro')),
  phase           TEXT        NOT NULL,   -- Dip|Double-Dip|Oh-Shit|Recover|Good|Euphoria
  score           DOUBLE PRECISION NOT NULL,
  slope           DOUBLE PRECISION,
  curvature       DOUBLE PRECISION,
  delta_res       DOUBLE PRECISION,
  confidence      DOUBLE PRECISION,
  dwell_remaining DOUBLE PRECISION,
  pending_label   TEXT NULL,
  s_btcusd        DOUBLE PRECISION,
  s_rotation      DOUBLE PRECISION,
  s_port_btc      DOUBLE PRECISION,
  s_port_alt      DOUBLE PRECISION,
  PRIMARY KEY (token, ts, horizon)
);

CREATE INDEX IF NOT EXISTS idx_phase_state_ts
  ON public.phase_state (ts DESC);

COMMENT ON TABLE  public.phase_state IS 'SPIRAL Phase outputs per token×horizon with lens diagnostics';


