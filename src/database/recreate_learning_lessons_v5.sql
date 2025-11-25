-- Recreate Learning Lessons Table (V5)
-- This script drops and recreates the learning_lessons table to ensure it has the correct schema for V5.
-- WARNING: This will delete existing lessons (which is fine as we are mining from scratch).

DROP TABLE IF EXISTS learning_lessons CASCADE;

CREATE TABLE learning_lessons (
    id BIGSERIAL PRIMARY KEY,
    module TEXT NOT NULL,                           -- 'pm', 'dm'
    pattern_key TEXT NOT NULL,                      -- "pm.uptrend.S1.buy_flag"
    action_category TEXT NOT NULL,                  -- 'entry', 'add', 'trim', 'exit'
    scope_subset JSONB NOT NULL DEFAULT '{}'::jsonb,-- The scope slice (e.g. {"chain": "solana"})
    
    n INTEGER NOT NULL DEFAULT 0,                   -- Number of samples
    stats JSONB NOT NULL DEFAULT '{}'::jsonb,       -- Aggregated stats (avg_rr, edge_raw, decay_meta, etc.)
    
    lesson_type TEXT NOT NULL DEFAULT 'pm_strength',-- 'pm_strength', 'dm_alloc', etc.
    decay_halflife_hours FLOAT,                     -- Estimated half-life
    latent_factor_id TEXT,                          -- For grouping related lessons
    
    status TEXT NOT NULL DEFAULT 'active',          -- 'active', 'archived'
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Compat column for V4 readers if any (can be removed later)
    scope_values JSONB DEFAULT '{}'::jsonb,
    
    UNIQUE (module, pattern_key, action_category, scope_subset)
);

CREATE INDEX idx_learning_lessons_lookup ON learning_lessons(module, pattern_key, action_category);
CREATE INDEX idx_learning_lessons_scope_gin ON learning_lessons USING GIN(scope_subset);
CREATE INDEX idx_learning_lessons_stats_gin ON learning_lessons USING GIN(stats);

COMMENT ON TABLE learning_lessons IS 'Stores mined patterns (lessons) with aggregated stats and decay metadata (V5).';

