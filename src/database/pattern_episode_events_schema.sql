-- Pattern Episode Events (Fact Table for Tuning)
-- Stores "Opportunities" (Episodes) and our decisions (Acted/Skipped) + Outcomes.

DROP TABLE IF EXISTS pattern_episode_events CASCADE;

CREATE TABLE pattern_episode_events (
    id BIGSERIAL PRIMARY KEY,
    
    -- Context
    scope JSONB NOT NULL,               -- Unified Scope (Chain, Mcap, Timeframe, etc.)
    pattern_key TEXT NOT NULL,          -- "pm.s1_entry", "pm.s3_retest"
    episode_id TEXT NOT NULL,           -- Unique ID for this specific window (s1_win_..., s3_win_...)
    trade_id TEXT,                      -- Linked trade_id if we acted (nullable)
    
    -- The Experiment
    decision TEXT NOT NULL CHECK (decision IN ('acted', 'skipped')),
    outcome TEXT CHECK (outcome IN ('success', 'failure', 'neutral')), -- Null if pending
    
    -- Causal Factors (Snapshot at decision time)
    factors JSONB NOT NULL,             
    -- Example: { "ts_score": 65, "ts_min": 60, "dx": 0.7, "dx_min": 0.65, "a_value": 0.4 }

    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pattern_episode_events_scope_gin ON pattern_episode_events USING GIN(scope);
CREATE INDEX idx_pattern_episode_events_lookup ON pattern_episode_events(pattern_key, decision);
CREATE INDEX idx_pattern_episode_events_episode_id ON pattern_episode_events(episode_id);
CREATE INDEX idx_pattern_episode_events_trade_id ON pattern_episode_events(trade_id);

COMMENT ON TABLE pattern_episode_events IS 'Fact table for the Tuning System. Logs every opportunity (episode), the decision (act/skip), and the eventual outcome.';

