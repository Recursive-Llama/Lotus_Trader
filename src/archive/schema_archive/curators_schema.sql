-- Curators Database Schema
-- Focused on curator management and performance tracking
-- Separate from position tracking (will be handled later)

-- Drop existing tables and functions if they exist (for clean cutover)
DROP TABLE IF EXISTS curator_signals CASCADE;
DROP TABLE IF EXISTS curator_platforms CASCADE;
DROP TABLE IF EXISTS curators CASCADE;

-- Drop existing functions
DROP FUNCTION IF EXISTS register_curator(TEXT, TEXT, TEXT, TEXT, TEXT, FLOAT, TEXT);
DROP FUNCTION IF EXISTS update_curator_performance(TEXT);
DROP FUNCTION IF EXISTS get_curator_performance(TEXT);
DROP FUNCTION IF EXISTS get_top_curators(INTEGER, TEXT);

-- Create curators table
CREATE TABLE curators (
    curator_id TEXT PRIMARY KEY,  -- "0xdetweiler", "louiscooper" (unique identifier)
    name TEXT NOT NULL,           -- "0xDetweiler", "Louis Cooper"
    description TEXT,             -- Curator description/bio
    notes TEXT,                   -- Admin notes
    
    -- Platform handles (stored directly in curators table)
    twitter_handle TEXT,          -- "@0xdetweiler"
    telegram_handle TEXT,         -- "@ducksinnerpond"
    
    -- Performance tracking
    total_signals INTEGER DEFAULT 0,
    successful_signals INTEGER DEFAULT 0,
    failed_signals INTEGER DEFAULT 0,
    win_rate FLOAT DEFAULT 0.0,   -- Calculated: successful_signals / total_signals
    
    -- Position tracking metrics
    total_pnl_pct FLOAT DEFAULT 0.0,      -- Total P&L percentage
    best_performer_token TEXT,            -- Best performing token ticker
    best_performer_pct FLOAT,             -- Best performing token percentage
    worst_performer_token TEXT,           -- Worst performing token ticker  
    worst_performer_pct FLOAT,            -- Worst performing token percentage
    avg_performer_token TEXT,             -- Average performing token ticker
    avg_performer_pct FLOAT,              -- Average performing token percentage
    
    -- Dynamic weighting system
    base_weight FLOAT DEFAULT 0.5,        -- Base weight (0.0 to 1.0)
    performance_weight FLOAT DEFAULT 0.5, -- Performance-adjusted weight
    final_weight FLOAT DEFAULT 0.5,       -- Final calculated weight
    
    -- Status and metadata
    status TEXT DEFAULT 'active',         -- "active", "inactive", "suspended", "testing"
    tags TEXT[],                          -- ["defi", "alpha", "technical", "multi_platform"]
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE,
    last_signal_at TIMESTAMP WITH TIME ZONE,
    performance_updated_at TIMESTAMP WITH TIME ZONE
);

-- No separate platforms table needed - handles stored directly in curators table

-- Create curator signals table (tracks all signals from curators)
CREATE TABLE curator_signals (
    id SERIAL PRIMARY KEY,
    curator_id TEXT NOT NULL REFERENCES curators(curator_id),
    platform TEXT NOT NULL,           -- "twitter", "telegram", etc.
    handle TEXT NOT NULL,             -- "@0xdetweiler"
    signal_id TEXT UNIQUE,            -- Unique signal identifier
    message_id TEXT,                  -- Platform message ID
    message_url TEXT,                 -- Link to original message
    
    -- Signal content
    content TEXT NOT NULL,            -- Original message content
    extracted_tokens JSONB,           -- Tokens extracted from message
    sentiment TEXT,                   -- "bullish", "bearish", "neutral"
    confidence FLOAT,                 -- Signal confidence (0.0 to 1.0)
    
    -- Token information
    primary_token_chain TEXT,
    primary_token_contract TEXT,
    primary_token_ticker TEXT,
    primary_token_name TEXT,
    
    -- Signal metadata
    signal_type TEXT,                 -- "call", "alert", "analysis", "update"
    urgency TEXT DEFAULT 'medium',    -- "low", "medium", "high", "critical"
    tags TEXT[],                      -- Signal tags
    
    -- Performance tracking
    position_created BOOLEAN DEFAULT false,
    position_id TEXT,                 -- Will link to positions table later
    signal_outcome TEXT,              -- "profitable", "loss", "breakeven", "pending"
    signal_pnl_pct FLOAT,             -- P&L percentage for this signal
    signal_pnl_usd FLOAT,             -- P&L USD for this signal
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    outcome_updated_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for performance
CREATE INDEX idx_curators_status ON curators(status);
CREATE INDEX idx_curators_performance ON curators(win_rate DESC, total_pnl_pct DESC);
CREATE INDEX idx_curators_last_seen ON curators(last_seen_at DESC);
CREATE INDEX idx_curators_weight ON curators(final_weight DESC);
CREATE INDEX idx_curators_twitter ON curators(twitter_handle);
CREATE INDEX idx_curators_telegram ON curators(telegram_handle);

CREATE INDEX idx_curator_signals_curator ON curator_signals(curator_id);
CREATE INDEX idx_curator_signals_platform ON curator_signals(platform);
CREATE INDEX idx_curator_signals_created ON curator_signals(created_at);
CREATE INDEX idx_curator_signals_outcome ON curator_signals(signal_outcome);
CREATE INDEX idx_curator_signals_tokens ON curator_signals USING GIN(extracted_tokens);

-- Create triggers for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_curator_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_curator_updated_at
    BEFORE UPDATE ON curators
    FOR EACH ROW
    EXECUTE FUNCTION update_curator_updated_at();

-- Create views for common queries
CREATE VIEW active_curators AS
SELECT 
    c.*,
    CASE 
        WHEN c.twitter_handle IS NOT NULL AND c.telegram_handle IS NOT NULL THEN 'multi_platform'
        WHEN c.twitter_handle IS NOT NULL THEN 'twitter'
        WHEN c.telegram_handle IS NOT NULL THEN 'telegram'
        ELSE 'unknown'
    END as platform_type
FROM curators c
WHERE c.status = 'active';

CREATE VIEW curator_performance_summary AS
SELECT 
    c.curator_id,
    c.name,
    c.total_signals,
    c.successful_signals,
    c.failed_signals,
    c.win_rate,
    c.total_pnl_pct,
    c.best_performer_token,
    c.best_performer_pct,
    c.worst_performer_token,
    c.worst_performer_pct,
    c.avg_performer_token,
    c.avg_performer_pct,
    c.final_weight,
    COUNT(cs.id) as total_signals_count,
    COUNT(CASE WHEN cs.signal_outcome = 'profitable' THEN 1 END) as profitable_signals,
    COUNT(CASE WHEN cs.signal_outcome = 'loss' THEN 1 END) as loss_signals,
    AVG(cs.signal_pnl_pct) as avg_signal_pnl_pct
FROM curators c
LEFT JOIN curator_signals cs ON c.curator_id = cs.curator_id
GROUP BY c.curator_id, c.name, c.total_signals, c.successful_signals, 
         c.failed_signals, c.win_rate, c.total_pnl_pct, c.best_performer_token,
         c.best_performer_pct, c.worst_performer_token, c.worst_performer_pct,
         c.avg_performer_token, c.avg_performer_pct, c.final_weight;

-- Create RPC functions for common operations
CREATE OR REPLACE FUNCTION register_curator(
    curator_id_param TEXT,
    name_param TEXT,
    platform_param TEXT,
    handle_param TEXT,
    description_param TEXT DEFAULT NULL,
    weight_param FLOAT DEFAULT 0.5
)
RETURNS TEXT AS $$
DECLARE
    curator_exists BOOLEAN;
BEGIN
    -- Check if curator exists
    SELECT EXISTS(SELECT 1 FROM curators WHERE curator_id = curator_id_param) INTO curator_exists;
    
    -- Create curator if doesn't exist
    IF NOT curator_exists THEN
        INSERT INTO curators (curator_id, name, description, base_weight, final_weight)
        VALUES (curator_id_param, name_param, description_param, weight_param, weight_param);
    END IF;
    
    -- Update platform handle based on platform type
    IF platform_param = 'twitter' THEN
        UPDATE curators SET twitter_handle = handle_param WHERE curator_id = curator_id_param;
    ELSIF platform_param = 'telegram' THEN
        UPDATE curators SET telegram_handle = handle_param WHERE curator_id = curator_id_param;
    END IF;
    
    RETURN curator_id_param;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_curator_performance(curator_id_param TEXT)
RETURNS VOID AS $$
DECLARE
    total_signals_count INTEGER;
    successful_signals_count INTEGER;
    failed_signals_count INTEGER;
    total_pnl_pct_calc FLOAT;
    win_rate_calc FLOAT;
    performance_weight_calc FLOAT;
    final_weight_calc FLOAT;
    best_token TEXT;
    best_pct FLOAT;
    worst_token TEXT;
    worst_pct FLOAT;
    avg_token TEXT;
    avg_pct FLOAT;
BEGIN
    -- Calculate performance metrics from signals
    SELECT 
        COUNT(*),
        COUNT(CASE WHEN signal_outcome = 'profitable' THEN 1 END),
        COUNT(CASE WHEN signal_outcome = 'loss' THEN 1 END),
        SUM(signal_pnl_pct)
    INTO total_signals_count, successful_signals_count, failed_signals_count, total_pnl_pct_calc
    FROM curator_signals 
    WHERE curator_id = curator_id_param;
    
    -- Calculate win rate
    IF total_signals_count > 0 THEN
        win_rate_calc := successful_signals_count::FLOAT / total_signals_count;
    ELSE
        win_rate_calc := 0.0;
    END IF;
    
    -- Find best, worst, and average performers
    SELECT primary_token_ticker, signal_pnl_pct
    INTO best_token, best_pct
    FROM curator_signals 
    WHERE curator_id = curator_id_param AND signal_pnl_pct IS NOT NULL
    ORDER BY signal_pnl_pct DESC 
    LIMIT 1;
    
    SELECT primary_token_ticker, signal_pnl_pct
    INTO worst_token, worst_pct
    FROM curator_signals 
    WHERE curator_id = curator_id_param AND signal_pnl_pct IS NOT NULL
    ORDER BY signal_pnl_pct ASC 
    LIMIT 1;
    
    SELECT primary_token_ticker, AVG(signal_pnl_pct)
    INTO avg_token, avg_pct
    FROM curator_signals 
    WHERE curator_id = curator_id_param AND signal_pnl_pct IS NOT NULL
    GROUP BY primary_token_ticker
    ORDER BY AVG(signal_pnl_pct) DESC
    LIMIT 1;
    
    -- Calculate performance weight (0.0 to 1.0)
    performance_weight_calc := GREATEST(0.0, LEAST(1.0, 
        (win_rate_calc * 0.5) + 
        (GREATEST(0, COALESCE(total_pnl_pct_calc, 0) / 100) * 0.5)
    ));
    
    -- Calculate final weight (average of base and performance)
    SELECT (base_weight + performance_weight_calc) / 2 INTO final_weight_calc
    FROM curators WHERE curator_id = curator_id_param;
    
    -- Update curator performance
    UPDATE curators 
    SET 
        total_signals = total_signals_count,
        successful_signals = successful_signals_count,
        failed_signals = failed_signals_count,
        win_rate = win_rate_calc,
        total_pnl_pct = COALESCE(total_pnl_pct_calc, 0.0),
        best_performer_token = best_token,
        best_performer_pct = COALESCE(best_pct, 0.0),
        worst_performer_token = worst_token,
        worst_performer_pct = COALESCE(worst_pct, 0.0),
        avg_performer_token = avg_token,
        avg_performer_pct = COALESCE(avg_pct, 0.0),
        performance_weight = performance_weight_calc,
        final_weight = final_weight_calc,
        performance_updated_at = NOW(),
        updated_at = NOW()
    WHERE curator_id = curator_id_param;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_curator_performance(curator_id_param TEXT)
RETURNS TABLE (
    curator_id TEXT,
    name TEXT,
    total_signals INTEGER,
    successful_signals INTEGER,
    failed_signals INTEGER,
    win_rate FLOAT,
    total_pnl_pct FLOAT,
    best_performer_token TEXT,
    best_performer_pct FLOAT,
    worst_performer_token TEXT,
    worst_performer_pct FLOAT,
    avg_performer_token TEXT,
    avg_performer_pct FLOAT,
    final_weight FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.curator_id,
        c.name,
        c.total_signals,
        c.successful_signals,
        c.failed_signals,
        c.win_rate,
        c.total_pnl_pct,
        c.best_performer_token,
        c.best_performer_pct,
        c.worst_performer_token,
        c.worst_performer_pct,
        c.avg_performer_token,
        c.avg_performer_pct,
        c.final_weight
    FROM curators c
    WHERE c.curator_id = curator_id_param;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_top_curators(limit_param INTEGER DEFAULT 10, platform_param TEXT DEFAULT NULL)
RETURNS TABLE (
    curator_id TEXT,
    name TEXT,
    win_rate FLOAT,
    total_pnl_pct FLOAT,
    best_performer_token TEXT,
    best_performer_pct FLOAT,
    final_weight FLOAT,
    total_signals INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.curator_id,
        c.name,
        c.win_rate,
        c.total_pnl_pct,
        c.best_performer_token,
        c.best_performer_pct,
        c.final_weight,
        c.total_signals
    FROM curators c
    WHERE c.status = 'active'
    AND (platform_param IS NULL OR 
         (platform_param = 'twitter' AND c.twitter_handle IS NOT NULL) OR
         (platform_param = 'telegram' AND c.telegram_handle IS NOT NULL))
    ORDER BY c.win_rate DESC, c.total_pnl_pct DESC
    LIMIT limit_param;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL ON curators TO your_app_user;
-- GRANT ALL ON curator_signals TO your_app_user;
-- GRANT ALL ON active_curators TO your_app_user;
-- GRANT ALL ON curator_performance_summary TO your_app_user;
-- GRANT EXECUTE ON FUNCTION register_curator(TEXT, TEXT, TEXT, TEXT, TEXT, FLOAT) TO your_app_user;
-- GRANT EXECUTE ON FUNCTION update_curator_performance(TEXT) TO your_app_user;
-- GRANT EXECUTE ON FUNCTION get_curator_performance(TEXT) TO your_app_user;
-- GRANT EXECUTE ON FUNCTION get_top_curators(INTEGER, TEXT) TO your_app_user;
