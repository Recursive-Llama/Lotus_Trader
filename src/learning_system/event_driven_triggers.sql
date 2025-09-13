-- Event-Driven Learning System Database Triggers
-- Every strand triggers the learning system instantly

-- Function to trigger learning system when any strand is created
CREATE OR REPLACE FUNCTION trigger_learning_system_on_strand()
RETURNS TRIGGER AS $$
BEGIN
    -- Queue strand for immediate learning processing
    INSERT INTO learning_queue (strand_id, strand_type, created_at, status)
    VALUES (NEW.id, NEW.kind, NOW(), 'pending')
    ON CONFLICT (strand_id) DO NOTHING;
    
    -- Log the trigger
    RAISE LOG 'Triggered learning system for strand: % (%)', NEW.id, NEW.kind;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for strand creation
DROP TRIGGER IF EXISTS strand_learning_trigger ON ad_strands;
CREATE TRIGGER strand_learning_trigger
    AFTER INSERT ON ad_strands
    FOR EACH ROW
    EXECUTE FUNCTION trigger_learning_system_on_strand();

-- Function to process learning queue
CREATE OR REPLACE FUNCTION process_learning_queue()
RETURNS void AS $$
DECLARE
    queue_item RECORD;
    strand_data RECORD;
BEGIN
    -- Get pending items from learning queue
    FOR queue_item IN 
        SELECT * FROM learning_queue 
        WHERE status = 'pending' 
        ORDER BY created_at ASC 
        LIMIT 10
    LOOP
        -- Get the actual strand data
        SELECT * INTO strand_data 
        FROM ad_strands 
        WHERE id = queue_item.strand_id;
        
        IF FOUND THEN
            -- Mark as processing
            UPDATE learning_queue 
            SET status = 'processing', processed_at = NOW() 
            WHERE strand_id = queue_item.strand_id;
            
            -- Process the strand (this would call the Python function)
            -- For now, just mark as completed
            UPDATE learning_queue 
            SET status = 'completed', processed_at = NOW() 
            WHERE strand_id = queue_item.strand_id;
            
            RAISE LOG 'Processed learning queue item: %', queue_item.strand_id;
        ELSE
            -- Strand not found, mark as failed
            UPDATE learning_queue 
            SET status = 'failed', processed_at = NOW() 
            WHERE strand_id = queue_item.strand_id;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Create index for efficient queue processing
CREATE INDEX IF NOT EXISTS idx_learning_queue_pending ON learning_queue(status, created_at) 
WHERE status = 'pending';

-- Function to get learning queue stats
CREATE OR REPLACE FUNCTION get_learning_queue_stats()
RETURNS TABLE(
    status TEXT,
    count BIGINT,
    oldest_pending TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        lq.status,
        COUNT(*) as count,
        MIN(lq.created_at) as oldest_pending
    FROM learning_queue lq
    GROUP BY lq.status
    ORDER BY lq.status;
END;
$$ LANGUAGE plpgsql;
