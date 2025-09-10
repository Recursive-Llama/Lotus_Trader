-- Agent Capabilities Schema
-- Stores agent capabilities, specializations, and performance metrics for the discovery system

CREATE TABLE IF NOT EXISTS agent_capabilities (
    -- Primary identification
    agent_name VARCHAR(100) PRIMARY KEY,
    
    -- Capabilities and specializations (stored as JSON arrays)
    capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    specializations JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Performance tracking
    performance_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Status and versioning
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'error')),
    version VARCHAR(20) NOT NULL DEFAULT '1.0',
    
    -- Timestamps
    registration_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_agent_capabilities_status ON agent_capabilities(status);
CREATE INDEX IF NOT EXISTS idx_agent_capabilities_last_active ON agent_capabilities(last_active);
CREATE INDEX IF NOT EXISTS idx_agent_capabilities_capabilities ON agent_capabilities USING GIN (capabilities);
CREATE INDEX IF NOT EXISTS idx_agent_capabilities_specializations ON agent_capabilities USING GIN (specializations);
CREATE INDEX IF NOT EXISTS idx_agent_capabilities_performance_metrics ON agent_capabilities USING GIN (performance_metrics);

-- Comments
COMMENT ON TABLE agent_capabilities IS 'Stores agent capabilities, specializations, and performance metrics for the discovery system';
COMMENT ON COLUMN agent_capabilities.agent_name IS 'Unique identifier for the agent';
COMMENT ON COLUMN agent_capabilities.capabilities IS 'JSON array of agent capabilities (e.g., ["raw_data_analysis", "pattern_detection"])';
COMMENT ON COLUMN agent_capabilities.specializations IS 'JSON array of agent specializations (e.g., ["volume_analysis", "divergence_detection"])';
COMMENT ON COLUMN agent_capabilities.performance_metrics IS 'JSON object containing performance metrics (e.g., {"accuracy": 0.85, "latency_ms": 120})';
COMMENT ON COLUMN agent_capabilities.status IS 'Current status of the agent: active, inactive, or error';
COMMENT ON COLUMN agent_capabilities.version IS 'Version of the agent capability definition';
COMMENT ON COLUMN agent_capabilities.registration_time IS 'When the agent was first registered';
COMMENT ON COLUMN agent_capabilities.last_active IS 'When the agent was last active/updated';
COMMENT ON COLUMN agent_capabilities.created_at IS 'When the record was created';
COMMENT ON COLUMN agent_capabilities.updated_at IS 'When the record was last updated';

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_agent_capabilities_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_agent_capabilities_updated_at
    BEFORE UPDATE ON agent_capabilities
    FOR EACH ROW
    EXECUTE FUNCTION update_agent_capabilities_updated_at();

-- Sample data for testing
INSERT INTO agent_capabilities (
    agent_name,
    capabilities,
    specializations,
    performance_metrics,
    status,
    version
) VALUES (
    'raw_data_intelligence',
    '["raw_data_analysis", "market_microstructure", "volume_analysis", "time_based_patterns", "cross_asset_analysis", "divergence_detection"]'::jsonb,
    '["volume_analysis", "divergence_detection"]'::jsonb,
    '{"accuracy": 0.85, "latency_ms": 120, "patterns_detected": 0}'::jsonb,
    'active',
    '1.0'
) ON CONFLICT (agent_name) DO NOTHING;
