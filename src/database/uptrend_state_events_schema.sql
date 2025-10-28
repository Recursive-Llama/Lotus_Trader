-- Uptrend State Events Schema
-- Append-only log of state machine/emitted events for analytics/backtests

CREATE TABLE IF NOT EXISTS uptrend_state_events (
  id BIGSERIAL PRIMARY KEY,
  token_contract TEXT NOT NULL,
  chain TEXT NOT NULL,
  event_type TEXT NOT NULL,         -- e.g. 's1_breakout', 's2_support_touch', 's4_euphoria_on'
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  state TEXT,                       -- S0..S5 at time of event
  payload JSONB NOT NULL            -- unified snapshot or minimal event payload
);

-- Common query patterns
CREATE INDEX IF NOT EXISTS idx_uptrend_events_ts ON uptrend_state_events (ts DESC);
CREATE INDEX IF NOT EXISTS idx_uptrend_events_token_chain_ts ON uptrend_state_events (token_contract, chain, ts DESC);
CREATE INDEX IF NOT EXISTS idx_uptrend_events_type_ts ON uptrend_state_events (event_type, ts DESC);
CREATE INDEX IF NOT EXISTS idx_uptrend_events_payload_gin ON uptrend_state_events USING GIN (payload);


