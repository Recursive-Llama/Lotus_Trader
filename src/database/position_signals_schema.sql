-- Position Signals Schema
-- Time-series history of Uptrend Engine outputs per position
-- Optional table for audit trail and learning system analysis

-- Drop existing table if it exists
DROP TABLE IF EXISTS position_signals CASCADE;

-- Create position signals table
CREATE TABLE position_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign key to position
    position_id UUID NOT NULL REFERENCES lowcap_positions(id) ON DELETE CASCADE,
    
    -- Timestamp
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Engine output payload (full JSONB from uptrend_engine_v4)
    payload JSONB NOT NULL,
    
    -- Optional: Signal type for quick filtering
    signal_type TEXT,                        -- "buy_signal", "buy_flag", "trim_flag", "exit", "hold", etc.
    
    -- Optional: State for quick filtering
    state TEXT,                              -- "S0", "S1", "S2", "S3"
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_position_signals_position_id ON position_signals(position_id);
CREATE INDEX idx_position_signals_timestamp ON position_signals(timestamp DESC);
CREATE INDEX idx_position_signals_position_timestamp ON position_signals(position_id, timestamp DESC);
CREATE INDEX idx_position_signals_signal_type ON position_signals(signal_type) WHERE signal_type IS NOT NULL;
CREATE INDEX idx_position_signals_state ON position_signals(state) WHERE state IS NOT NULL;

-- GIN index for JSONB payload (for querying engine outputs)
CREATE INDEX IF NOT EXISTS idx_position_signals_payload_gin ON position_signals USING GIN (payload);

-- Comments for documentation
COMMENT ON TABLE position_signals IS 'Time-series history of Uptrend Engine outputs per position for audit trail and learning';
COMMENT ON COLUMN position_signals.payload IS 'Full JSONB payload from uptrend_engine_v4 (state, flags, scores, diagnostics)';
COMMENT ON COLUMN position_signals.signal_type IS 'Quick filter: buy_signal, buy_flag, trim_flag, exit, hold, etc.';
COMMENT ON COLUMN position_signals.state IS 'Quick filter: S0, S1, S2, S3';

