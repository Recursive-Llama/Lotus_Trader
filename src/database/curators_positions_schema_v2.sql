-- Enhanced Curators and Positions Database Schema v2
-- Supports multi-platform curators with comprehensive performance tracking
-- Fresh start - no test data, ready for production

-- Drop existing tables if they exist (for clean cutover)
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS curator_platforms CASCADE;
DROP TABLE IF EXISTS curators CASCADE;

-- Create enhanced curators table
CREATE TABLE curators (
    curator_id TEXT PRIMARY KEY,  -- "0xdetweiler", "louiscooper" (unique identifier)
    name TEXT NOT NULL,           -- "0xDetweiler", "Louis Cooper"
    display_name TEXT,            -- Optional display name
    description TEXT,             -- Curator description/bio
    website_url TEXT,             -- Personal website or portfolio
    avatar_url TEXT,              -- Profile picture URL
    
    -- Performance tracking
    total_signals INTEGER DEFAULT 0,
    successful_signals INTEGER DEFAULT 0,
    failed_signals INTEGER DEFAULT 0,
    win_rate FLOAT DEFAULT 0.0,   -- Calculated: successful_signals / total_signals
    avg_return_pct FLOAT DEFAULT 0.0,  -- Average return percentage
    total_pnl_usd FLOAT DEFAULT 0.0,   -- Total P&L in USD
    max_drawdown_pct FLOAT DEFAULT 0.0, -- Maximum drawdown percentage
    sharpe_ratio FLOAT DEFAULT 0.0,    -- Risk-adjusted return metric
    
    -- Dynamic weighting system
    base_weight FLOAT DEFAULT 0.5,     -- Base weight (0.0 to 1.0)
    performance_weight FLOAT DEFAULT 0.5, -- Performance-adjusted weight
    final_weight FLOAT DEFAULT 0.5,    -- Final calculated weight
    weight_history JSONB,              -- Historical weight changes
    
    -- Status and metadata
    status TEXT DEFAULT 'active',      -- "active", "inactive", "suspended", "testing"
    tier TEXT DEFAULT 'standard',      -- "premium", "standard", "testing", "vip"
    tags TEXT[],                       -- ["defi", "alpha", "technical", "multi_platform"]
    notes TEXT,                        -- Admin notes
    risk_profile TEXT DEFAULT 'medium', -- "low", "medium", "high", "degen"
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE,
    last_signal_at TIMESTAMP WITH TIME ZONE,
    performance_updated_at TIMESTAMP WITH TIME ZONE
);

-- Create curator platforms table (supports multiple platforms per curator)
CREATE TABLE curator_platforms (
    id SERIAL PRIMARY KEY,
    curator_id TEXT NOT NULL REFERENCES curators(curator_id) ON DELETE CASCADE,
    platform TEXT NOT NULL,           -- "twitter", "telegram", "discord", "youtube"
    handle TEXT NOT NULL,             -- "@0xdetweiler", "@ducksinnerpond"
    platform_id TEXT,                 -- Platform-specific ID (channel_id, user_id, etc.)
    url TEXT,                         -- Full URL to profile/channel
    is_primary BOOLEAN DEFAULT false, -- Primary platform for this curator
    is_active BOOLEAN DEFAULT true,   -- Currently monitoring this platform
    weight FLOAT DEFAULT 0.5,         -- Platform-specific weight
    priority TEXT DEFAULT 'medium',   -- "low", "medium", "high", "critical"
    
    -- Platform-specific settings
    settings JSONB,                   -- Platform-specific configuration
    last_checked_at TIMESTAMP WITH TIME ZONE,
    last_post_at TIMESTAMP WITH TIME ZONE,
    total_posts INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique platform per curator
    UNIQUE(curator_id, platform)
);

-- Create enhanced positions table (supports both TD and TDL)
CREATE TABLE positions (
    id TEXT PRIMARY KEY,
    book_id TEXT NOT NULL,  -- "patterns" or "social"
    module TEXT NOT NULL,   -- "trader" or "trader_lowcap"
    strand_id TEXT NOT NULL, -- Links to decision/execution strand
    
    -- Curator information (enhanced)
    curator_id TEXT REFERENCES curators(curator_id),
    curator_platform TEXT,  -- "twitter", "telegram", etc.
    curator_handle TEXT,    -- "@0xdetweiler", "@ducksinnerpond"
    curator_weight FLOAT,   -- Weight at time of signal
    curator_tier TEXT,      -- Tier at time of signal
    
    -- Token information
    token_chain TEXT NOT NULL,
    token_contract TEXT NOT NULL,
    token_ticker TEXT NOT NULL,
    token_name TEXT,
    
    -- Position details
    entry_strategy TEXT NOT NULL,  -- "three_way_entry", "immediate", "ladder_entry", "dca_entry"
    exit_strategy TEXT NOT NULL,   -- "progressive_exit", "stop_loss", "take_profit", "trailing_stop"
    position_size_usd FLOAT NOT NULL,
    entry_price FLOAT NOT NULL,
    current_price FLOAT,
    
    -- Universal Entry Tracking (for both TD and TDL)
    entry_1_size_usd FLOAT,        -- Immediate entry
    entry_1_price FLOAT,
    entry_1_executed BOOLEAN DEFAULT false,
    entry_1_timestamp TIMESTAMP WITH TIME ZONE,
    entry_1_venue TEXT,            -- Raydium, Orca, Uniswap, etc.
    entry_1_slippage_pct FLOAT,
    entry_1_fee_usd FLOAT,
    
    entry_2_size_usd FLOAT,        -- Second entry (TD: ladder, TDL: -20%)
    entry_2_price FLOAT,
    entry_2_executed BOOLEAN DEFAULT false,
    entry_2_timestamp TIMESTAMP WITH TIME ZONE,
    entry_2_venue TEXT,
    entry_2_slippage_pct FLOAT,
    entry_2_fee_usd FLOAT,
    
    entry_3_size_usd FLOAT,        -- Third entry (TD: ladder, TDL: -50%)
    entry_3_price FLOAT,
    entry_3_executed BOOLEAN DEFAULT false,
    entry_3_timestamp TIMESTAMP WITH TIME ZONE,
    entry_3_venue TEXT,
    entry_3_slippage_pct FLOAT,
    entry_3_fee_usd FLOAT,
    
    -- Additional Entry Levels (for TD ladder strategies)
    entry_4_size_usd FLOAT,
    entry_4_price FLOAT,
    entry_4_executed BOOLEAN DEFAULT false,
    entry_4_timestamp TIMESTAMP WITH TIME ZONE,
    entry_4_venue TEXT,
    entry_4_slippage_pct FLOAT,
    entry_4_fee_usd FLOAT,
    
    entry_5_size_usd FLOAT,
    entry_5_price FLOAT,
    entry_5_executed BOOLEAN DEFAULT false,
    entry_5_timestamp TIMESTAMP WITH TIME ZONE,
    entry_5_venue TEXT,
    entry_5_slippage_pct FLOAT,
    entry_5_fee_usd FLOAT,
    
    -- Universal Exit Tracking (for both TD and TDL)
    exit_1_target_price FLOAT,     -- First exit target
    exit_1_size_usd FLOAT,
    exit_1_executed BOOLEAN DEFAULT false,
    exit_1_timestamp TIMESTAMP WITH TIME ZONE,
    exit_1_venue TEXT,
    exit_1_slippage_pct FLOAT,
    exit_1_fee_usd FLOAT,
    exit_1_pnl_usd FLOAT,
    exit_1_pnl_pct FLOAT,
    
    exit_2_target_price FLOAT,     -- Second exit target
    exit_2_size_usd FLOAT,
    exit_2_executed BOOLEAN DEFAULT false,
    exit_2_timestamp TIMESTAMP WITH TIME ZONE,
    exit_2_venue TEXT,
    exit_2_slippage_pct FLOAT,
    exit_2_fee_usd FLOAT,
    exit_2_pnl_usd FLOAT,
    exit_2_pnl_pct FLOAT,
    
    exit_3_target_price FLOAT,     -- Third exit target
    exit_3_size_usd FLOAT,
    exit_3_executed BOOLEAN DEFAULT false,
    exit_3_timestamp TIMESTAMP WITH TIME ZONE,
    exit_3_venue TEXT,
    exit_3_slippage_pct FLOAT,
    exit_3_fee_usd FLOAT,
    exit_3_pnl_usd FLOAT,
    exit_3_pnl_pct FLOAT,
    
    -- Additional Exit Levels (for TD complex strategies)
    exit_4_target_price FLOAT,
    exit_4_size_usd FLOAT,
    exit_4_executed BOOLEAN DEFAULT false,
    exit_4_timestamp TIMESTAMP WITH TIME ZONE,
    exit_4_venue TEXT,
    exit_4_slippage_pct FLOAT,
    exit_4_fee_usd FLOAT,
    exit_4_pnl_usd FLOAT,
    exit_4_pnl_pct FLOAT,
    
    exit_5_target_price FLOAT,
    exit_5_size_usd FLOAT,
    exit_5_executed BOOLEAN DEFAULT false,
    exit_5_timestamp TIMESTAMP WITH TIME ZONE,
    exit_5_venue TEXT,
    exit_5_slippage_pct FLOAT,
    exit_5_fee_usd FLOAT,
    exit_5_pnl_usd FLOAT,
    exit_5_pnl_pct FLOAT,
    
    -- Risk Management (for both TD and TDL)
    stop_loss_price FLOAT,
    stop_loss_executed BOOLEAN DEFAULT false,
    stop_loss_timestamp TIMESTAMP WITH TIME ZONE,
    stop_loss_pnl_usd FLOAT,
    stop_loss_pnl_pct FLOAT,
    
    trailing_stop_price FLOAT,
    trailing_stop_activated BOOLEAN DEFAULT false,
    trailing_stop_timestamp TIMESTAMP WITH TIME ZONE,
    
    -- Performance Metrics (universal)
    total_pnl_usd FLOAT DEFAULT 0,
    total_pnl_pct FLOAT DEFAULT 0,
    total_fees_usd FLOAT DEFAULT 0,
    total_slippage_pct FLOAT DEFAULT 0,
    max_drawdown_pct FLOAT DEFAULT 0,
    max_gain_pct FLOAT DEFAULT 0,
    current_exposure_usd FLOAT DEFAULT 0,
    realized_pnl_usd FLOAT DEFAULT 0,
    unrealized_pnl_usd FLOAT DEFAULT 0,
    
    -- Venue Performance (for learning)
    primary_venue TEXT,            -- Most used venue for this position
    venue_performance_score FLOAT, -- Venue effectiveness score
    execution_quality_score FLOAT, -- Overall execution quality
    
    -- Status and Metadata
    status TEXT DEFAULT 'active',  -- "active", "closed", "partial", "stopped"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,
    
    -- Learning System Integration (universal)
    execution_quality FLOAT,       -- TDL/TD execution score
    venue_effectiveness FLOAT,     -- Venue performance score
    allocation_accuracy FLOAT,     -- DML allocation score
    strategy_effectiveness FLOAT,  -- Strategy performance score
    risk_management_score FLOAT,   -- Risk management effectiveness
    
    -- Module-Specific Learning Data
    curator_performance FLOAT,     -- TDL: Curator performance score
    pattern_strength FLOAT,        -- TD: Pattern strength score
    market_regime TEXT,            -- Market conditions during position
    volatility_regime TEXT,        -- Volatility conditions during position
    liquidity_regime TEXT          -- Liquidity conditions during position
);

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
    position_id TEXT REFERENCES positions(id),
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
CREATE INDEX idx_curators_tier ON curators(tier);
CREATE INDEX idx_curators_performance ON curators(win_rate DESC, avg_return_pct DESC);
CREATE INDEX idx_curators_last_seen ON curators(last_seen_at DESC);
CREATE INDEX idx_curators_weight ON curators(final_weight DESC);

CREATE INDEX idx_curator_platforms_curator ON curator_platforms(curator_id);
CREATE INDEX idx_curator_platforms_platform ON curator_platforms(platform);
CREATE INDEX idx_curator_platforms_active ON curator_platforms(is_active);
CREATE INDEX idx_curator_platforms_primary ON curator_platforms(is_primary);

CREATE INDEX idx_positions_book ON positions(book_id);
CREATE INDEX idx_positions_module ON positions(module);
CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_positions_curator ON positions(curator_id);
CREATE INDEX idx_positions_token ON positions(token_chain, token_contract);
CREATE INDEX idx_positions_created ON positions(created_at);
CREATE INDEX idx_positions_venue ON positions(primary_venue);
CREATE INDEX idx_positions_performance ON positions(execution_quality DESC);
CREATE INDEX idx_positions_active ON positions(book_id, status) WHERE status = 'active';

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

CREATE OR REPLACE FUNCTION update_curator_platform_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_curator_platform_updated_at
    BEFORE UPDATE ON curator_platforms
    FOR EACH ROW
    EXECUTE FUNCTION update_curator_platform_updated_at();

CREATE OR REPLACE FUNCTION update_position_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_position_updated_at
    BEFORE UPDATE ON positions
    FOR EACH ROW
    EXECUTE FUNCTION update_position_updated_at();

-- Create views for common queries
CREATE VIEW active_curators AS
SELECT 
    c.*,
    cp.platform,
    cp.handle,
    cp.is_primary,
    cp.is_active as platform_active
FROM curators c
JOIN curator_platforms cp ON c.curator_id = cp.curator_id
WHERE c.status = 'active' AND cp.is_active = true;

CREATE VIEW curator_performance_summary AS
SELECT 
    c.curator_id,
    c.name,
    c.tier,
    c.total_signals,
    c.successful_signals,
    c.failed_signals,
    c.win_rate,
    c.avg_return_pct,
    c.total_pnl_usd,
    c.final_weight,
    COUNT(p.id) as total_positions,
    AVG(p.total_pnl_pct) as avg_position_pnl_pct,
    SUM(p.total_pnl_usd) as total_position_pnl_usd,
    COUNT(CASE WHEN p.status = 'active' THEN 1 END) as active_positions
FROM curators c
LEFT JOIN positions p ON c.curator_id = p.curator_id
GROUP BY c.curator_id, c.name, c.tier, c.total_signals, c.successful_signals, 
         c.failed_signals, c.win_rate, c.avg_return_pct, c.total_pnl_usd, c.final_weight;

CREATE VIEW position_performance_summary AS
SELECT 
    book_id,
    module,
    COUNT(*) as total_positions,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_positions,
    COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed_positions,
    AVG(total_pnl_pct) as avg_pnl_pct,
    SUM(total_pnl_usd) as total_pnl_usd,
    AVG(execution_quality) as avg_execution_quality,
    AVG(venue_effectiveness) as avg_venue_effectiveness,
    COUNT(DISTINCT curator_id) as unique_curators
FROM positions
GROUP BY book_id, module;

-- Create RPC functions for common operations
CREATE OR REPLACE FUNCTION register_curator(
    curator_id_param TEXT,
    name_param TEXT,
    platform_param TEXT,
    handle_param TEXT,
    platform_id_param TEXT DEFAULT NULL,
    weight_param FLOAT DEFAULT 0.5,
    tier_param TEXT DEFAULT 'standard'
)
RETURNS TEXT AS $$
DECLARE
    curator_exists BOOLEAN;
    platform_exists BOOLEAN;
BEGIN
    -- Check if curator exists
    SELECT EXISTS(SELECT 1 FROM curators WHERE curator_id = curator_id_param) INTO curator_exists;
    
    -- Create curator if doesn't exist
    IF NOT curator_exists THEN
        INSERT INTO curators (curator_id, name, tier)
        VALUES (curator_id_param, name_param, tier_param);
    END IF;
    
    -- Check if platform exists for this curator
    SELECT EXISTS(SELECT 1 FROM curator_platforms 
                  WHERE curator_id = curator_id_param AND platform = platform_param) 
    INTO platform_exists;
    
    -- Create platform entry if doesn't exist
    IF NOT platform_exists THEN
        INSERT INTO curator_platforms (curator_id, platform, handle, platform_id, weight)
        VALUES (curator_id_param, platform_param, handle_param, platform_id_param, weight_param);
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
    avg_return_pct_calc FLOAT;
    total_pnl_usd_calc FLOAT;
    win_rate_calc FLOAT;
    performance_weight_calc FLOAT;
    final_weight_calc FLOAT;
BEGIN
    -- Calculate performance metrics
    SELECT 
        COUNT(*),
        COUNT(CASE WHEN signal_outcome = 'profitable' THEN 1 END),
        COUNT(CASE WHEN signal_outcome = 'loss' THEN 1 END),
        AVG(signal_pnl_pct),
        SUM(signal_pnl_usd)
    INTO total_signals_count, successful_signals_count, failed_signals_count, 
         avg_return_pct_calc, total_pnl_usd_calc
    FROM curator_signals 
    WHERE curator_id = curator_id_param;
    
    -- Calculate win rate
    IF total_signals_count > 0 THEN
        win_rate_calc := successful_signals_count::FLOAT / total_signals_count;
    ELSE
        win_rate_calc := 0.0;
    END IF;
    
    -- Calculate performance weight (0.0 to 1.0)
    performance_weight_calc := GREATEST(0.0, LEAST(1.0, 
        (win_rate_calc * 0.4) + 
        (GREATEST(0, avg_return_pct_calc) * 0.3) + 
        (GREATEST(0, total_pnl_usd_calc / 1000) * 0.3)
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
        avg_return_pct = COALESCE(avg_return_pct_calc, 0.0),
        total_pnl_usd = COALESCE(total_pnl_usd_calc, 0.0),
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
    tier TEXT,
    total_signals INTEGER,
    successful_signals INTEGER,
    failed_signals INTEGER,
    win_rate FLOAT,
    avg_return_pct FLOAT,
    total_pnl_usd FLOAT,
    final_weight FLOAT,
    total_positions INTEGER,
    active_positions INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.curator_id,
        c.name,
        c.tier,
        c.total_signals,
        c.successful_signals,
        c.failed_signals,
        c.win_rate,
        c.avg_return_pct,
        c.total_pnl_usd,
        c.final_weight,
        COUNT(p.id)::INTEGER as total_positions,
        COUNT(CASE WHEN p.status = 'active' THEN 1 END)::INTEGER as active_positions
    FROM curators c
    LEFT JOIN positions p ON c.curator_id = p.curator_id
    WHERE c.curator_id = curator_id_param
    GROUP BY c.curator_id, c.name, c.tier, c.total_signals, c.successful_signals, 
             c.failed_signals, c.win_rate, c.avg_return_pct, c.total_pnl_usd, c.final_weight;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL ON curators TO your_app_user;
-- GRANT ALL ON curator_platforms TO your_app_user;
-- GRANT ALL ON positions TO your_app_user;
-- GRANT ALL ON curator_signals TO your_app_user;
-- GRANT ALL ON active_curators TO your_app_user;
-- GRANT ALL ON curator_performance_summary TO your_app_user;
-- GRANT ALL ON position_performance_summary TO your_app_user;
-- GRANT EXECUTE ON FUNCTION register_curator(TEXT, TEXT, TEXT, TEXT, TEXT, FLOAT, TEXT) TO your_app_user;
-- GRANT EXECUTE ON FUNCTION update_curator_performance(TEXT) TO your_app_user;
-- GRANT EXECUTE ON FUNCTION get_curator_performance(TEXT) TO your_app_user;
