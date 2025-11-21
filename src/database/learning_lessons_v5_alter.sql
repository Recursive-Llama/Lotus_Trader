-- Learning Lessons v5 Schema Extensions
-- Add new columns for v5 learning system: action_category, scope fields, meta-learning fields
-- Used by: Lesson builder, override materializer

-- Add new columns to learning_lessons
ALTER TABLE learning_lessons 
    ADD COLUMN IF NOT EXISTS pattern_key TEXT,  -- Canonical pattern key: "pm.uptrend.S1.buy_flag"
    ADD COLUMN IF NOT EXISTS action_category TEXT CHECK (action_category IN ('entry', 'add', 'trim', 'exit', 'allocation')),
    ADD COLUMN IF NOT EXISTS lesson_type TEXT,  -- 'pm_strength', 'dm_alloc', 'pm_tuning', etc.
    ADD COLUMN IF NOT EXISTS scope_dims TEXT[],  -- e.g. ['macro_phase', 'bucket', 'A_mode']
    ADD COLUMN IF NOT EXISTS scope_values JSONB,  -- e.g. {"macro_phase": "Recover", "bucket": "micro"}
    ADD COLUMN IF NOT EXISTS lesson_strength FLOAT,  -- 0.0-1.0, for decay weighting
    ADD COLUMN IF NOT EXISTS decay_halflife_hours INT,  -- from v5.2 half-life estimation
    ADD COLUMN IF NOT EXISTS latent_factor_id TEXT;  -- from v5.3 clustering

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_learning_lessons_pattern_key 
    ON learning_lessons(pattern_key);
CREATE INDEX IF NOT EXISTS idx_learning_lessons_action_category 
    ON learning_lessons(action_category);
CREATE INDEX IF NOT EXISTS idx_learning_lessons_scope_dims 
    ON learning_lessons USING GIN(scope_dims);
CREATE INDEX IF NOT EXISTS idx_learning_lessons_scope_values 
    ON learning_lessons USING GIN(scope_values);
CREATE INDEX IF NOT EXISTS idx_learning_lessons_latent_factor 
    ON learning_lessons(latent_factor_id);

-- Comments for documentation
COMMENT ON COLUMN learning_lessons.pattern_key IS 'Canonical pattern key: module.family.state.motif (e.g., "pm.uptrend.S1.buy_flag")';
COMMENT ON COLUMN learning_lessons.action_category IS 'Action class: entry, add, trim, or exit - always included as required grouping dimension';
COMMENT ON COLUMN learning_lessons.lesson_type IS 'Lesson type: pm_strength, dm_alloc, pm_tuning, etc.';
COMMENT ON COLUMN learning_lessons.scope_dims IS 'Array of scope dimension names that define this lesson (e.g., ["macro_phase", "bucket", "A_mode"])';
COMMENT ON COLUMN learning_lessons.scope_values IS 'JSONB with scope dimension values that define this lesson';
COMMENT ON COLUMN learning_lessons.lesson_strength IS 'Lesson strength (0.0-1.0) used for decay weighting';
COMMENT ON COLUMN learning_lessons.decay_halflife_hours IS 'Half-life in hours for this lesson (from v5.2 meta-learning)';
COMMENT ON COLUMN learning_lessons.latent_factor_id IS 'Latent factor cluster ID (from v5.3 meta-learning) for deduplication';

-- Note: The effect JSONB column structure is extended to support:
-- {
--   "capital_levers": {
--     "size_mult": 1.12,
--     "entry_aggression_mult": 1.08,
--     "exit_aggression_mult": 0.95
--   },
--   "execution_levers": {
--     "entry_delay_bars": 1,
--     "phase1_frac_mult": 0.85,
--     "trim_delay_mult": 1.1,
--     "trail_mult": 0.95,
--     "signal_thresholds": {
--       "min_ts_for_add": 0.55,
--       "min_ox_for_trim": 0.40
--     }
--   }
-- }
-- This is handled in application code, not schema changes.

