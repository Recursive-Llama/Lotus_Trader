-- Curators and Positions Database Schema
-- Curators table for social lowcap intelligence system
-- Positions table for universal position tracking (TD and TDL)

-- Drop existing tables if they exist (for clean cutover)
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS curators CASCADE;

-- Create curators registry table
CREATE TABLE curators (
    curator_id TEXT PRIMARY KEY,  -- "tg:@alphaOne", "tw:@smartWhale"
    platform TEXT NOT NULL,      -- "telegram", "twitter"
    handle TEXT NOT NULL,         -- "@alphaOne", "@smartWhale"
    weight FLOAT DEFAULT 1.0,    -- Dynamic weight based on performance
    enabled BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE,
    performance_score FLOAT,      -- Cached performance score
    total_signals INTEGER DEFAULT 0,
    last_signal_at TIMESTAMP WITH TIME ZONE
);

-- Create universal positions table (supports both TD and TDL)
CREATE TABLE positions (
    id TEXT PRIMARY KEY,
    book_id TEXT NOT NULL,  -- "patterns" or "social"
    module TEXT NOT NULL,   -- "trader" or "trader_lowcap"
    strand_id TEXT NOT NULL, -- Links to decision/execution strand
    
    -- Token information
    token_chain TEXT NOT NULL,
    token_contract TEXT NOT NULL,
    token_ticker TEXT NOT NULL,
    
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

-- Create indexes for performance
CREATE INDEX idx_curators_enabled ON curators(enabled);
CREATE INDEX idx_curators_platform ON curators(platform);
CREATE INDEX idx_curators_performance ON curators(performance_score DESC);
CREATE INDEX idx_curators_last_seen ON curators(last_seen_at DESC);

CREATE INDEX idx_positions_book ON positions(book_id);
CREATE INDEX idx_positions_module ON positions(module);
CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_positions_token ON positions(token_chain, token_contract);
CREATE INDEX idx_positions_created ON positions(created_at);
CREATE INDEX idx_positions_venue ON positions(primary_venue);
CREATE INDEX idx_positions_performance ON positions(execution_quality DESC);
CREATE INDEX idx_positions_active ON positions(book_id, status) WHERE status = 'active';

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
CREATE VIEW active_positions AS
SELECT 
    p.*,
    c.handle as curator_handle,
    c.platform as curator_platform
FROM positions p
LEFT JOIN curators c ON p.curator_performance IS NOT NULL
WHERE p.status = 'active';

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
    AVG(venue_effectiveness) as avg_venue_effectiveness
FROM positions
GROUP BY book_id, module;

CREATE VIEW curator_performance_summary AS
SELECT 
    c.*,
    COUNT(p.id) as total_positions,
    AVG(p.curator_performance) as avg_curator_performance,
    AVG(p.total_pnl_pct) as avg_position_pnl_pct,
    SUM(p.total_pnl_usd) as total_position_pnl_usd
FROM curators c
LEFT JOIN positions p ON p.curator_performance IS NOT NULL
GROUP BY c.curator_id;

-- Insert sample curator data
INSERT INTO curators (curator_id, platform, handle, weight, enabled, notes) VALUES
('tg:@alphaOne', 'telegram', '@alphaOne', 1.0, true, 'High performer on Solana'),
('tw:@smartWhale', 'twitter', '@smartWhale', 0.8, true, 'Good on Base, learning'),
('tg:@scout', 'telegram', '@scout', 1.0, true, 'Consistent performer'),
('tw:@cryptoInsider', 'twitter', '@cryptoInsider', 0.9, true, 'Strong on Ethereum'),
('tg:@lowcapHunter', 'telegram', '@lowcapHunter', 0.7, true, 'Early stage specialist');

-- Create RPC functions for common operations
CREATE OR REPLACE FUNCTION get_curator_performance(curator_id_param TEXT)
RETURNS TABLE (
    curator_id TEXT,
    platform TEXT,
    handle TEXT,
    performance_score FLOAT,
    total_signals INTEGER,
    avg_pnl_pct FLOAT,
    total_pnl_usd FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.curator_id,
        c.platform,
        c.handle,
        c.performance_score,
        c.total_signals,
        AVG(p.total_pnl_pct) as avg_pnl_pct,
        SUM(p.total_pnl_usd) as total_pnl_usd
    FROM curators c
    LEFT JOIN positions p ON p.curator_performance IS NOT NULL
    WHERE c.curator_id = curator_id_param
    GROUP BY c.curator_id, c.platform, c.handle, c.performance_score, c.total_signals;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_portfolio_summary(book_id_param TEXT)
RETURNS TABLE (
    book_id TEXT,
    total_positions INTEGER,
    active_positions INTEGER,
    total_exposure_usd FLOAT,
    total_pnl_usd FLOAT,
    avg_pnl_pct FLOAT,
    avg_execution_quality FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.book_id,
        COUNT(*) as total_positions,
        COUNT(CASE WHEN p.status = 'active' THEN 1 END) as active_positions,
        SUM(p.current_exposure_usd) as total_exposure_usd,
        SUM(p.total_pnl_usd) as total_pnl_usd,
        AVG(p.total_pnl_pct) as avg_pnl_pct,
        AVG(p.execution_quality) as avg_execution_quality
    FROM positions p
    WHERE p.book_id = book_id_param
    GROUP BY p.book_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_curator_performance(curator_id_param TEXT, new_score FLOAT)
RETURNS VOID AS $$
BEGIN
    UPDATE curators 
    SET 
        performance_score = new_score,
        updated_at = NOW()
    WHERE curator_id = curator_id_param;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL ON curators TO your_app_user;
-- GRANT ALL ON positions TO your_app_user;
-- GRANT ALL ON active_positions TO your_app_user;
-- GRANT ALL ON position_performance_summary TO your_app_user;
-- GRANT ALL ON curator_performance_summary TO your_app_user;
-- GRANT EXECUTE ON FUNCTION get_curator_performance(TEXT) TO your_app_user;
-- GRANT EXECUTE ON FUNCTION get_portfolio_summary(TEXT) TO your_app_user;
-- GRANT EXECUTE ON FUNCTION update_curator_performance(TEXT, FLOAT) TO your_app_user;
