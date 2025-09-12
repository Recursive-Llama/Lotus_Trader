-- Database Cleanup Script for Centralized Learning System
-- This script clears the database and sets up the learning system

-- Clear existing data
DELETE FROM learning_queue;
DELETE FROM AD_strands WHERE braid_level >= 2;

-- Reset sequences
ALTER SEQUENCE learning_queue_id_seq RESTART WITH 1;

-- Clear any existing triggers
DROP TRIGGER IF EXISTS strand_learning_trigger ON AD_strands;

-- Recreate learning queue table
DROP TABLE IF EXISTS learning_queue;
CREATE TABLE learning_queue (
    id SERIAL PRIMARY KEY,
    strand_id TEXT NOT NULL,
    strand_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    status TEXT DEFAULT 'pending'
);

-- Create indexes for efficient querying
CREATE INDEX idx_learning_queue_status ON learning_queue(status);
CREATE INDEX idx_learning_queue_strand_type ON learning_queue(strand_type);
CREATE INDEX idx_learning_queue_created_at ON learning_queue(created_at);

-- Recreate trigger function
CREATE OR REPLACE FUNCTION trigger_learning_system()
RETURNS TRIGGER AS $$
BEGIN
    -- Only queue strands that are not already braids (braid_level is null or 1)
    IF NEW.braid_level IS NULL OR NEW.braid_level = 1 THEN
        -- Queue strand for learning processing
        INSERT INTO learning_queue (strand_id, strand_type, created_at)
        VALUES (NEW.id, NEW.kind, NOW());
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for strand creation
CREATE TRIGGER strand_learning_trigger
    AFTER INSERT ON AD_strands
    FOR EACH ROW
    EXECUTE FUNCTION trigger_learning_system();

-- Create utility functions
CREATE OR REPLACE FUNCTION cleanup_learning_queue()
RETURNS void AS $$
BEGIN
    -- Delete completed items older than 7 days
    DELETE FROM learning_queue 
    WHERE status = 'completed' 
    AND processed_at < NOW() - INTERVAL '7 days';
    
    -- Delete failed items older than 3 days
    DELETE FROM learning_queue 
    WHERE status = 'failed' 
    AND processed_at < NOW() - INTERVAL '3 days';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_learning_queue_stats()
RETURNS TABLE(
    status TEXT,
    count BIGINT,
    oldest_created TIMESTAMP,
    newest_created TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        lq.status,
        COUNT(*) as count,
        MIN(lq.created_at) as oldest_created,
        MAX(lq.created_at) as newest_created
    FROM learning_queue lq
    GROUP BY lq.status
    ORDER BY lq.status;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION reset_failed_learning_items()
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE learning_queue 
    SET status = 'pending', processed_at = NULL
    WHERE status = 'failed';
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_strands_for_learning(
    strand_type_filter TEXT DEFAULT NULL,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE(
    strand_id TEXT,
    strand_type TEXT,
    created_at TIMESTAMP,
    content JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        lq.strand_id,
        lq.strand_type,
        lq.created_at,
        s.content
    FROM learning_queue lq
    JOIN AD_strands s ON s.id = lq.strand_id
    WHERE lq.status = 'pending'
    AND (strand_type_filter IS NULL OR lq.strand_type = strand_type_filter)
    ORDER BY lq.created_at ASC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION mark_learning_item_processed(
    queue_id INTEGER,
    success BOOLEAN
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE learning_queue 
    SET 
        status = CASE WHEN success THEN 'completed' ELSE 'failed' END,
        processed_at = NOW()
    WHERE id = queue_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION trigger_learning_system() TO PUBLIC;
GRANT EXECUTE ON FUNCTION cleanup_learning_queue() TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_learning_queue_stats() TO PUBLIC;
GRANT EXECUTE ON FUNCTION reset_failed_learning_items() TO PUBLIC;
GRANT EXECUTE ON FUNCTION get_strands_for_learning(TEXT, INTEGER) TO PUBLIC;
GRANT EXECUTE ON FUNCTION mark_learning_item_processed(INTEGER, BOOLEAN) TO PUBLIC;

-- Insert some test data
INSERT INTO AD_strands (id, kind, content, created_at) VALUES
('test_pattern_1', 'pattern', '{"pattern_type": "volume_spike", "asset": "BTC", "timeframe": "1m", "confidence": 0.8}', NOW()),
('test_pattern_2', 'pattern', '{"pattern_type": "volume_spike", "asset": "BTC", "timeframe": "5m", "confidence": 0.7}', NOW()),
('test_prediction_1', 'prediction_review', '{"group_signature": "BTC_1h_volume_spike", "asset": "BTC", "timeframe": "1h", "outcome": {"success": true, "return_pct": 2.5}}', NOW()),
('test_prediction_2', 'prediction_review', '{"group_signature": "BTC_1h_volume_spike", "asset": "BTC", "timeframe": "1h", "outcome": {"success": false, "return_pct": -1.2}}', NOW()),
('test_trade_1', 'trade_outcome', '{"trade_id": "trade_001", "asset": "BTC", "timeframe": "1h", "performance": {"success": true, "return_pct": 3.1}}', NOW()),
('test_trade_2', 'trade_outcome', '{"trade_id": "trade_002", "asset": "BTC", "timeframe": "1h", "performance": {"success": false, "return_pct": -0.8}}', NOW());

-- Show initial state
SELECT 'Database cleaned and learning system initialized' as status;
SELECT * FROM get_learning_queue_stats();
