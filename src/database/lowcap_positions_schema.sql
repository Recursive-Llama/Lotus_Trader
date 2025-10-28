-- Lowcap Positions Database Schema
-- Token-centric positions with curator sources
-- Each position represents a token, not individual curator calls

-- Drop existing functions first to avoid return type conflicts
DROP FUNCTION IF EXISTS get_active_positions_by_token(TEXT, TEXT);
DROP FUNCTION IF EXISTS get_portfolio_summary(TEXT);
DROP FUNCTION IF EXISTS close_position(TEXT, FLOAT, TEXT, TEXT, FLOAT, FLOAT);

-- Drop existing table if it exists (for clean cutover)
DROP TABLE IF EXISTS lowcap_positions CASCADE;

-- Create lowcap positions table (TOKEN-CENTRIC with multi-entry/exit support)
CREATE TABLE lowcap_positions (
    -- PRIMARY KEY: Token-based ID
    id TEXT PRIMARY KEY,                    -- "PEPE_solana" or "BONK_solana"
    
    -- TOKEN INFORMATION (Primary focus)
    token_chain TEXT NOT NULL,              -- "solana", "ethereum", "base"
    token_contract TEXT NOT NULL,           -- Token contract address
    token_ticker TEXT NOT NULL,             -- "PEPE", "BONK"
    
    -- POSITION OVERVIEW
    total_allocation_pct FLOAT NOT NULL,    -- Total allocation percentage (e.g., 3.0%)
    total_quantity FLOAT DEFAULT 0,         -- Total tokens held (sum of all entries - exits)
    
    -- AGGREGATE PERFORMANCE
    total_pnl_usd FLOAT DEFAULT 0,          -- Total P&L in USD
    total_pnl_pct FLOAT DEFAULT 0,          -- Total P&L percentage
    avg_entry_price FLOAT,                  -- Weighted average entry price
    avg_exit_price FLOAT,                   -- Weighted average exit price
    total_tokens_bought FLOAT DEFAULT 0,    -- Total tokens bought across all entries
    total_tokens_sold FLOAT DEFAULT 0,      -- Total tokens sold across all exits
    total_investment_native FLOAT DEFAULT 0, -- Total native currency invested
    total_extracted_native FLOAT DEFAULT 0,  -- Total native currency extracted
    total_pnl_native FLOAT DEFAULT 0,       -- Total P&L in native currency
    first_entry_timestamp TIMESTAMP WITH TIME ZONE,
    last_activity_timestamp TIMESTAMP WITH TIME ZONE,
    
    -- STATUS AND METADATA
    status TEXT DEFAULT 'active',           -- "active", "closed", "partial", "stopped"
    book_id TEXT DEFAULT 'social',          -- Which book this belongs to
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,
    close_reason TEXT,                      -- Reason for position closure: "fully_exited", "cap_cleanup_qty_zero", etc.
    
    -- ADDITIONAL TRACKING
    tax_pct FLOAT,                          -- Tax percentage detected for this token
    
    -- JSONB DATA STORAGE
    entries JSONB,                          -- Array of standard entry data
    exits JSONB,                            -- Array of standard exit data
    exit_rules JSONB,                       -- Standard exit strategy rules
    trend_entries JSONB,                    -- Array of trend entry data
    trend_exits JSONB,                      -- Array of trend exit data
    trend_exit_rules JSONB,                 -- Trend exit strategy rules
    curator_sources JSONB,                  -- Curator source information
    
    -- SOURCE TRACKING
    source_tweet_url TEXT,                  -- Original tweet URL that triggered this position
    
    -- NOTES
    notes TEXT,                             -- Any additional notes

    -- PM FEATURES & STATE (added for Position Manager integration)
    features JSONB,                         -- Cached PM inputs/diagnostics
    cooldown_until TIMESTAMPTZ,             -- Time gate before new actions
    last_review_at TIMESTAMPTZ,             -- Last PM evaluation time
    time_patience_h INT,                    -- Patience window in hours
    reentry_lock_until TIMESTAMPTZ,         -- Lockout after exits/trails
    trend_entry_count INT DEFAULT 0,        -- Count of trend adds
    new_token_mode BOOLEAN DEFAULT FALSE    -- New token discovery mode flag
);

-- Note: Using JSONB columns in main table instead of separate tables for:
-- - entries (JSONB array) - standard entries
-- - exits (JSONB array) - standard exits
-- - exit_rules (JSONB object) - standard exit rules
-- - trend_entries (JSONB array) - trend dip entries
-- - trend_exits (JSONB array) - trend exits
-- - trend_exit_rules (JSONB object) - trend exit rules
-- - curator_sources (JSONB array) - curator attribution

-- Create indexes for performance
CREATE INDEX idx_lowcap_positions_token ON lowcap_positions(token_chain, token_contract);
CREATE INDEX idx_lowcap_positions_ticker ON lowcap_positions(token_ticker);
CREATE INDEX idx_lowcap_positions_status ON lowcap_positions(status);
CREATE INDEX idx_lowcap_positions_created ON lowcap_positions(created_at);
CREATE INDEX idx_lowcap_positions_book ON lowcap_positions(book_id);
CREATE INDEX idx_lowcap_positions_active ON lowcap_positions(book_id, status) WHERE status = 'active';

-- Note: Indexes for JSONB columns can be added as needed using GIN indexes
-- Example: CREATE INDEX idx_entries_gin ON lowcap_positions USING GIN (entries);
CREATE INDEX IF NOT EXISTS idx_lowcap_positions_features_gin ON lowcap_positions USING GIN (features);

-- Create trigger for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_lowcap_position_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_lowcap_position_updated_at
    BEFORE UPDATE ON lowcap_positions
    FOR EACH ROW
    EXECUTE FUNCTION update_lowcap_position_updated_at();

-- Create views for common queries
CREATE VIEW active_lowcap_positions AS
SELECT 
    p.*
FROM lowcap_positions p
WHERE p.status = 'active';

CREATE VIEW lowcap_performance_summary AS
SELECT 
    p.token_ticker,
    p.token_chain,
    p.status,
    p.total_allocation_pct,
    p.total_pnl_pct,
    p.total_pnl_usd,
    p.last_activity_timestamp
FROM lowcap_positions p;

-- Create RPC functions for common operations
CREATE OR REPLACE FUNCTION get_active_positions_by_token(token_contract_param TEXT, token_chain_param TEXT)
RETURNS TABLE (
    id TEXT,
    token_ticker TEXT,
    total_allocation_pct FLOAT,
    total_allocation_usd FLOAT,
    avg_entry_price FLOAT,
    current_price FLOAT,
    total_pnl_pct FLOAT,
    status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.token_ticker,
        p.total_allocation_pct,
        p.total_allocation_usd,
        p.avg_entry_price,
        p.current_price,
        p.total_pnl_pct,
        p.status
    FROM lowcap_positions p
    WHERE p.token_contract = token_contract_param 
    AND p.token_chain = token_chain_param
    AND p.status = 'active';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_portfolio_summary(book_id_param TEXT DEFAULT 'social')
RETURNS TABLE (
    book_id TEXT,
    total_positions INTEGER,
    active_positions INTEGER,
    total_allocation_usd FLOAT,
    total_pnl_usd FLOAT,
    avg_pnl_pct FLOAT,
    current_exposure_pct FLOAT
) AS $$
DECLARE
    book_nav FLOAT := 100000.0; -- Mock NAV, should be replaced with real value
BEGIN
    RETURN QUERY
    SELECT 
        p.book_id,
        COUNT(*)::INTEGER as total_positions,
        COUNT(CASE WHEN p.status = 'active' THEN 1 END)::INTEGER as active_positions,
        SUM(p.total_allocation_usd) as total_allocation_usd,
        SUM(p.total_pnl_usd) as total_pnl_usd,
        AVG(p.total_pnl_pct) as avg_pnl_pct,
        (SUM(p.total_allocation_usd) / book_nav * 100) as current_exposure_pct
    FROM lowcap_positions p
    WHERE p.book_id = book_id_param
    GROUP BY p.book_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION close_position(
    position_id_param TEXT,
    exit_price_param FLOAT,
    exit_venue_param TEXT,
    exit_tx_hash_param TEXT,
    exit_slippage_pct_param FLOAT DEFAULT 0,
    exit_fee_usd_param FLOAT DEFAULT 0
)
RETURNS BOOLEAN AS $$
DECLARE
    avg_entry_price_val FLOAT;
    total_allocation_usd_val FLOAT;
    total_quantity_val FLOAT;
    pnl_usd_calc FLOAT;
    pnl_pct_calc FLOAT;
    holding_duration_calc FLOAT;
    first_entry_time TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Get position details
    SELECT avg_entry_price, total_allocation_usd, total_quantity, first_entry_timestamp
    INTO avg_entry_price_val, total_allocation_usd_val, total_quantity_val, first_entry_time
    FROM lowcap_positions 
    WHERE id = position_id_param AND status = 'active';
    
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    
    -- Calculate P&L
    pnl_usd_calc := (exit_price_param - avg_entry_price_val) * total_quantity_val;
    pnl_pct_calc := (exit_price_param - avg_entry_price_val) / avg_entry_price_val * 100;
    
    -- Calculate holding duration
    holding_duration_calc := EXTRACT(EPOCH FROM (NOW() - first_entry_time)) / 3600; -- hours
    
    -- Update position
    UPDATE lowcap_positions 
    SET 
        status = 'closed',
        total_pnl_usd = pnl_usd_calc,
        total_pnl_pct = pnl_pct_calc,
        total_fees_usd = total_fees_usd + exit_fee_usd_param,
        closed_at = NOW(),
        updated_at = NOW()
    WHERE id = position_id_param;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Note: Functions for managing entries, exits, and curator sources are now handled
-- directly in the application code using JSONB operations on the main table

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL ON lowcap_positions TO your_app_user;
-- GRANT ALL ON active_lowcap_positions TO your_app_user;
-- GRANT ALL ON lowcap_performance_summary TO your_app_user;
-- GRANT EXECUTE ON FUNCTION get_active_positions_by_token(TEXT, TEXT) TO your_app_user;
-- GRANT EXECUTE ON FUNCTION get_portfolio_summary(TEXT) TO your_app_user;
-- GRANT EXECUTE ON FUNCTION close_position(TEXT, FLOAT, TEXT, TEXT, FLOAT, FLOAT) TO your_app_user;
