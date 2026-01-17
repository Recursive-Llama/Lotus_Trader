-- Migration: Create position_trajectories table for Learning System v2
-- Date: 2025-01-12

-- Position Trajectories - Unified learning fact table
-- Replaces pattern_trade_events and pattern_episode_events

CREATE TABLE IF NOT EXISTS position_trajectories (
    id BIGSERIAL PRIMARY KEY,
    
    -- Link to position
    position_id UUID NOT NULL,            -- lowcap_positions.id
    trade_id UUID,                        -- If position had a trade cycle
    
    -- Entry context
    entry_event TEXT NOT NULL,            -- 'S2.entry' or 'S1.retest_entry'
    pattern_key TEXT NOT NULL,            -- 'pm.uptrend.S2.entry'
    scope JSONB NOT NULL,                 -- Full scope at entry time
    entry_time TIMESTAMPTZ NOT NULL,
    
    -- Shadow vs Active
    is_shadow BOOLEAN NOT NULL,           -- Derived from status at creation (entry decision), not at close
    blocked_by TEXT[],                    -- Shadow only: gates that blocked entry (negative margins)
    near_miss_gates TEXT[],               -- Active failures: gates with smallest positive margin
    gate_margins JSONB,                   -- All gate margins at decision tick
    
    -- Outcome dimensions
    trajectory_type TEXT NOT NULL,        -- 'immediate_failure', 'trim_but_loss', 'trimmed_winner', 'clean_winner'
    roi FLOAT NOT NULL,                   -- Final ROI (continuous, from rpnl_pct)
    did_trim BOOLEAN NOT NULL,
    n_trims INTEGER DEFAULT 0,
    reached_s3 BOOLEAN NOT NULL,
    
    -- Timestamps
    closed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for mining queries
CREATE INDEX idx_pt_scope_gin ON position_trajectories USING GIN(scope);
CREATE INDEX idx_pt_pattern ON position_trajectories(pattern_key, trajectory_type);
CREATE INDEX idx_pt_shadow ON position_trajectories(is_shadow);
CREATE INDEX idx_pt_closed_at ON position_trajectories(closed_at DESC);
CREATE INDEX idx_pt_position_id ON position_trajectories(position_id);
CREATE INDEX idx_pt_trajectory_type ON position_trajectories(trajectory_type);

-- Constraint for trajectory_type enum
ALTER TABLE position_trajectories ADD CONSTRAINT check_trajectory_type 
    CHECK (trajectory_type IN ('immediate_failure', 'trim_but_loss', 'trimmed_winner', 'clean_winner'));

-- Comments
COMMENT ON TABLE position_trajectories IS 'Learning System v2: Position outcomes for trajectory-based learning. One row per position close event.';
COMMENT ON COLUMN position_trajectories.is_shadow IS 'True if position was blocked by gates at entry (counterfactual). Derived from status at entry decision, not at close.';
COMMENT ON COLUMN position_trajectories.blocked_by IS 'Shadow only: list of gates with negative margin at decision time (e.g. ["ts", "halo"])';
COMMENT ON COLUMN position_trajectories.near_miss_gates IS 'Active failures: top 2 gates with smallest positive margin (closest to blocking)';
COMMENT ON COLUMN position_trajectories.gate_margins IS 'All gate margins at decision tick: {"ts_margin": 5.2, "halo_margin": -0.3, ...}';
COMMENT ON COLUMN position_trajectories.trajectory_type IS 'Four trajectory types: immediate_failure (S0 before S3), trim_but_loss (trimmed but ROI<=0), trimmed_winner (reached S3 with trim), clean_winner (reached S3 no trim/minimal)';
COMMENT ON COLUMN position_trajectories.roi IS 'Final realized ROI percentage from rpnl_pct. Continuous value used for EV calculations.';
