-- Migration: Create learning_miner_runs table for miner metrics visibility
-- Date: 2025-01-14
-- Purpose: Track each miner run for operational visibility and debugging

CREATE TABLE IF NOT EXISTS learning_miner_runs (
    id BIGSERIAL PRIMARY KEY,
    
    -- Run identification
    run_id UUID NOT NULL DEFAULT gen_random_uuid(),
    miner_name TEXT NOT NULL DEFAULT 'TrajectoryMiner',
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    
    -- Scope
    book_id TEXT,  -- NULL = all books, else specific book
    
    -- Input stats
    n_trajectories_fetched INTEGER DEFAULT 0,
    n_strength_eligible INTEGER DEFAULT 0,
    n_tuning_eligible INTEGER DEFAULT 0,
    
    -- Output stats
    n_strength_lessons_created INTEGER DEFAULT 0,
    n_tuning_lessons_created INTEGER DEFAULT 0,
    n_overrides_written INTEGER DEFAULT 0,
    
    -- Mining depth
    max_scope_dimensions INTEGER DEFAULT 0,  -- Deepest scope subset created
    n_scope_combinations_mined INTEGER DEFAULT 0,  -- Total scope combos processed
    
    -- Status
    status TEXT NOT NULL DEFAULT 'running',  -- 'running', 'completed', 'failed'
    error_message TEXT,
    
    -- Metadata
    config_snapshot JSONB,  -- Snapshot of N_MIN, weights, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_lmr_started_at ON learning_miner_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_lmr_status ON learning_miner_runs(status);
CREATE INDEX IF NOT EXISTS idx_lmr_miner_name ON learning_miner_runs(miner_name);

-- Comments
COMMENT ON TABLE learning_miner_runs IS 'Tracks each learning miner execution for operational visibility and debugging.';
COMMENT ON COLUMN learning_miner_runs.max_scope_dimensions IS 'Maximum depth of scope dimensions in lessons created (1 = single-dim, 5 = 5 dimensions combined).';
COMMENT ON COLUMN learning_miner_runs.n_scope_combinations_mined IS 'Total number of scope combinations processed (includes pruned branches).';
