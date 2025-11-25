-- Update learning_lessons table for V5 Schema
-- Adds columns needed for the simplified allocation/edge plan

ALTER TABLE learning_lessons 
ADD COLUMN IF NOT EXISTS lesson_type TEXT DEFAULT 'pm_strength',
ADD COLUMN IF NOT EXISTS scope_subset JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS decay_halflife_hours FLOAT,
ADD COLUMN IF NOT EXISTS latent_factor_id TEXT;

-- Add index for scope_subset for faster lookups
CREATE INDEX IF NOT EXISTS idx_learning_lessons_scope_subset ON learning_lessons USING GIN(scope_subset);

COMMENT ON COLUMN learning_lessons.lesson_type IS 'Type of lesson: pm_strength, dm_alloc, etc.';
COMMENT ON COLUMN learning_lessons.scope_subset IS 'The specific scope slice this lesson applies to (V5 replacement for scope_values).';

