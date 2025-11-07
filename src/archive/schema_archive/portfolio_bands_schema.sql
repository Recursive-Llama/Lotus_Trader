-- Portfolio Bands & Cut-Pressure State

CREATE TABLE IF NOT EXISTS public.portfolio_bands (
  ts                 TIMESTAMPTZ NOT NULL,
  core_count         INT         NOT NULL,
  cut_pressure       DOUBLE PRECISION NOT NULL,
  cut_pressure_raw   DOUBLE PRECISION,
  phase_tension      DOUBLE PRECISION,
  core_congestion    DOUBLE PRECISION,
  liquidity_stress   DOUBLE PRECISION,
  intent_skew        DOUBLE PRECISION,
  btc_dom_delta      DOUBLE PRECISION,
  usdt_dom_delta     DOUBLE PRECISION,
  dominance_delta    DOUBLE PRECISION,
  btc_dom_level      DOUBLE PRECISION,
  usdt_dom_level     DOUBLE PRECISION,
  btc_dom_slope_z    DOUBLE PRECISION,
  btc_dom_curv_z     DOUBLE PRECISION,
  btc_dom_level_z    DOUBLE PRECISION,
  usdt_dom_slope_z   DOUBLE PRECISION,
  usdt_dom_curv_z    DOUBLE PRECISION,
  usdt_dom_level_z   DOUBLE PRECISION,
  nav_usd            DOUBLE PRECISION NULL,
  core_pressure      DOUBLE PRECISION NULL,
  delta_core         DOUBLE PRECISION NULL,
  PRIMARY KEY (ts)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_bands_ts
  ON public.portfolio_bands (ts DESC);

COMMENT ON TABLE  public.portfolio_bands IS 'Portfolio structure, cut-pressure, and dominance diagnostics (hourly)';
COMMENT ON COLUMN public.portfolio_bands.core_pressure IS 'Core count pressure component (0-1) calculated from core_count vs ideal_core';
COMMENT ON COLUMN public.portfolio_bands.delta_core IS 'Core count delta for portfolio breathing adjustments';


