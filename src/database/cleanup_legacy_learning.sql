-- Cleanup Legacy Learning Tables
-- Removes V3/Early-V4 tables replaced by the Event-Miner architecture.

DROP TABLE IF EXISTS pattern_scope_stats CASCADE;
DROP TABLE IF EXISTS learning_coefficients CASCADE;
DROP TABLE IF EXISTS learning_edge_history CASCADE;

-- Note: learning_lessons and learning_configs (for non-override configs) are KEPT.

