-- Learning Lessons Database Schema
-- Compressed, validated rules derived from braids - used at decision-time
-- Used by: PM (action size adjustments), DM (allocation adjustments)

-- Drop existing table if it exists (for clean cutover)
DROP TABLE IF EXISTS learning_lessons CASCADE;

-- Create learning_lessons table
CREATE TABLE learning_lessons (
    id SERIAL PRIMARY KEY,
    module TEXT NOT NULL,                       -- 'dm' | 'pm'
    trigger JSONB NOT NULL,                     -- { state: "S1", a_bucket: "med", buy_flag: true, ... } (subset of context)
    effect JSONB NOT NULL,                      -- { size_multiplier: 1.08 } or { alloc_multiplier: 0.8 }
    stats JSONB NOT NULL,                       -- { edge_raw, incremental_edge, n, avg_rr, family_id, ... }
    status TEXT NOT NULL,                       -- 'candidate' | 'active' | 'deprecated'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_validated TIMESTAMPTZ,                 -- When this lesson was last validated/updated
    notes TEXT                                  -- Optional notes about this lesson
);

-- Create indexes for efficient queries
CREATE INDEX idx_learning_lessons_module_status ON learning_lessons(module, status);
CREATE INDEX idx_learning_lessons_status ON learning_lessons(status);

-- GIN index for JSONB trigger matching (subset matching)
CREATE INDEX idx_learning_lessons_trigger ON learning_lessons USING GIN(trigger);
CREATE INDEX idx_learning_lessons_effect ON learning_lessons USING GIN(effect);
CREATE INDEX idx_learning_lessons_stats ON learning_lessons USING GIN(stats);

-- Comments for documentation
COMMENT ON TABLE learning_lessons IS 'Compressed, validated rules derived from braids - used at decision-time';
COMMENT ON COLUMN learning_lessons.module IS 'Module: dm (Decision Maker) or pm (Portfolio Manager)';
COMMENT ON COLUMN learning_lessons.trigger IS 'Dimension values that trigger this lesson (subset of context)';
COMMENT ON COLUMN learning_lessons.effect IS 'Behavioral adjustment: size_multiplier (PM) or alloc_multiplier (DM)';
COMMENT ON COLUMN learning_lessons.stats IS 'Evidence: edge_raw, incremental_edge, n, avg_rr, family_id';
COMMENT ON COLUMN learning_lessons.status IS 'Lifecycle: candidate (newly created), active (validated, in use), deprecated (no longer valid)';

-- Example rows:
-- PM Lesson:
-- module: "pm"
-- trigger: {"state": "S1", "a_bucket": "med", "buy_flag": true}
-- effect: {"size_multiplier": 1.08}
-- stats: {"edge_raw": 1.2, "incremental_edge": 0.3, "n": 23, "avg_rr": 2.3, "family_id": "pm|add|S1|big_win"}
-- status: "active"
--
-- DM Lesson:
-- module: "dm"
-- trigger: {"curator": "detweiler", "chain": "base", "mcap_bucket": "<500k"}
-- effect: {"alloc_multiplier": 0.8}
-- stats: {"edge_raw": -0.5, "incremental_edge": -0.2, "n": 15, "avg_rr": 0.6, "family_id": "dm|detweiler|base|big_loss"}
-- status: "active"

