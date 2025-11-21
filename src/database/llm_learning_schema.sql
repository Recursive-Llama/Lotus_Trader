-- LLM Learning Database Schema
-- LLM layer outputs: hypotheses, reports, semantic tags, family proposals, semantic patterns
-- Used by: LLM Learning Layer (all 5 levels)

-- Drop existing table if it exists (for clean cutover)
DROP TABLE IF EXISTS llm_learning CASCADE;

-- Create llm_learning table
CREATE TABLE llm_learning (
    id SERIAL PRIMARY KEY,
    kind TEXT NOT NULL,                         -- 'hypothesis' | 'report' | 'semantic_tag' | 'family_proposal' | 'semantic_pattern'
    level INTEGER NOT NULL,                     -- 1-5 (which LLM level generated this)
    module TEXT,                                -- 'dm' | 'pm' | 'global' (which module this relates to)
    status TEXT NOT NULL,                       -- 'hypothesis' | 'validated' | 'rejected' | 'active' | 'deprecated'
    content JSONB NOT NULL,                     -- Kind-specific structure
    test_results JSONB,                         -- Auto-test results (if kind='hypothesis' or 'family_proposal')
    created_at TIMESTAMPTZ DEFAULT NOW(),
    validated_at TIMESTAMPTZ,                   -- When this was validated (if status='validated')
    notes TEXT                                  -- Optional notes
);

-- Create indexes for efficient queries
CREATE INDEX idx_llm_learning_kind_status ON llm_learning(kind, status);
CREATE INDEX idx_llm_learning_module ON llm_learning(module);
CREATE INDEX idx_llm_learning_level ON llm_learning(level);
CREATE INDEX idx_llm_learning_status ON llm_learning(status);

-- GIN index for JSONB content queries
CREATE INDEX idx_llm_learning_content ON llm_learning USING GIN(content);
CREATE INDEX idx_llm_learning_test_results ON llm_learning USING GIN(test_results);

-- Comments for documentation
COMMENT ON TABLE llm_learning IS 'LLM layer outputs: hypotheses, reports, semantic tags, family proposals, semantic patterns';
COMMENT ON COLUMN llm_learning.kind IS 'Type: hypothesis, report, semantic_tag, family_proposal, semantic_pattern';
COMMENT ON COLUMN llm_learning.level IS 'LLM level (1-5): 1=Commentary, 2=Semantic Features, 3=Family Optimization, 4=Semantic Compression, 5=Hypothesis Generation';
COMMENT ON COLUMN llm_learning.module IS 'Module: dm, pm, or global';
COMMENT ON COLUMN llm_learning.status IS 'Status: hypothesis (untested), validated (math validated), rejected (math rejected), active (in use), deprecated (no longer valid)';
COMMENT ON COLUMN llm_learning.content IS 'Kind-specific structure (varies by kind)';
COMMENT ON COLUMN llm_learning.test_results IS 'Auto-test results from math layer (if kind=hypothesis or family_proposal)';

-- Example rows:
-- Level 1 (Commentary):
-- kind: "report"
-- level: 1
-- module: "pm"
-- status: "active"
-- content: {"type": "commentary", "summary": "Most S1+med A+buy_flag entries have been strong...", "time_window_days": 30}
--
-- Level 2 (Semantic Features):
-- kind: "semantic_tag"
-- level: 2
-- module: "dm"
-- status: "hypothesis"
-- content: {"tag": "ai_narrative", "confidence": 0.85, "extracted_from": ["curator_message", "token_name"]}
--
-- Level 5 (Hypothesis Generation):
-- kind: "hypothesis"
-- level: 5
-- module: "pm"
-- status: "validated"
-- content: {"type": "interaction_pattern", "proposal": "Test rising OX + falling EDX", "reasoning": "..."}
-- test_results: {"avg_rr": 1.9, "n": 8, "p_value": 0.03, "statistically_significant": true}

