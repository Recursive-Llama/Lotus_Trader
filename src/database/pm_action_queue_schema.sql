-- PM Action Queue Schema
-- Stores execution conditions from PM Core for Price Monitor to watch and execute

CREATE TABLE pm_action_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    position_id UUID NOT NULL,
    action_id UUID NOT NULL,
    action_type VARCHAR(20) NOT NULL,  -- 'buy', 'sell', 'trim'
    condition JSONB NOT NULL,
    execution JSONB NOT NULL,
    safety JSONB NOT NULL,
    correlation_id UUID NOT NULL,
    a_value DECIMAL(3,2) NOT NULL,
    e_value DECIMAL(3,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'executed', 'expired', 'cancelled'
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    executed_at TIMESTAMP NULL,
    executed_price_native DECIMAL(20,8) NULL,
    executed_amount_sol DECIMAL(10,4) NULL,
    tx_hash TEXT NULL,
    error_message TEXT NULL
);

-- Indexes for efficient querying
CREATE INDEX idx_pm_action_queue_position ON pm_action_queue(position_id);
CREATE INDEX idx_pm_action_queue_status ON pm_action_queue(status);
CREATE INDEX idx_pm_action_queue_correlation ON pm_action_queue(correlation_id);
CREATE INDEX idx_pm_action_queue_expires ON pm_action_queue(expires_at);
CREATE INDEX idx_pm_action_queue_created_at ON pm_action_queue(created_at);

-- Unique constraint for idempotency
CREATE UNIQUE INDEX idx_pm_action_queue_correlation_unique ON pm_action_queue(correlation_id);

-- Composite index for common queries
CREATE INDEX idx_pm_action_queue_position_status ON pm_action_queue(position_id, status);

-- Comments for documentation
COMMENT ON TABLE pm_action_queue IS 'Stores execution conditions from PM Core for Price Monitor to watch and execute';
COMMENT ON COLUMN pm_action_queue.position_id IS 'Reference to lowcap_positions.id';
COMMENT ON COLUMN pm_action_queue.action_id IS 'Unique identifier for this specific action';
COMMENT ON COLUMN pm_action_queue.action_type IS 'Type of action: buy, sell, trim';
COMMENT ON COLUMN pm_action_queue.condition IS 'Execution condition JSON (trigger, level, halo, direction)';
COMMENT ON COLUMN pm_action_queue.execution IS 'Execution details JSON (amount_sol, max_slippage_bps, priority)';
COMMENT ON COLUMN pm_action_queue.safety IS 'Safety guards JSON (forbid_if_euphoria, forbid_if_emergency_exit)';
COMMENT ON COLUMN pm_action_queue.correlation_id IS 'Unique correlation ID for idempotency';
COMMENT ON COLUMN pm_action_queue.a_value IS 'Add Appetite score when action was created';
COMMENT ON COLUMN pm_action_queue.e_value IS 'Exit Assertiveness score when action was created';
COMMENT ON COLUMN pm_action_queue.status IS 'Action status: pending, executed, expired, cancelled';
COMMENT ON COLUMN pm_action_queue.expires_at IS 'When this action expires (typically 24h)';
COMMENT ON COLUMN pm_action_queue.executed_price_native IS 'Price at which action was executed';
COMMENT ON COLUMN pm_action_queue.executed_amount_sol IS 'SOL amount that was executed';
COMMENT ON COLUMN pm_action_queue.tx_hash IS 'Transaction hash of the execution';
COMMENT ON COLUMN pm_action_queue.error_message IS 'Error message if execution failed';
