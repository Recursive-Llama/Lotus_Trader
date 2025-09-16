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
    token_name TEXT,                        -- "Pepe Coin"
    
    -- POSITION OVERVIEW
    total_allocation_pct FLOAT NOT NULL,    -- Total allocation percentage (e.g., 3.0%)
    total_allocation_usd FLOAT NOT NULL,    -- Total allocation USD amount
    current_price FLOAT,                    -- Current market price per token
    total_quantity FLOAT DEFAULT 0,         -- Total tokens held (sum of all entries - exits)
    
    -- AGGREGATE PERFORMANCE
    total_pnl_usd FLOAT DEFAULT 0,          -- Total P&L in USD
    total_pnl_pct FLOAT DEFAULT 0,          -- Total P&L percentage
    total_fees_usd FLOAT DEFAULT 0,         -- Total fees paid
    avg_entry_price FLOAT,                  -- Weighted average entry price
    first_entry_timestamp TIMESTAMP WITH TIME ZONE,
    last_activity_timestamp TIMESTAMP WITH TIME ZONE,
    
    -- STATUS AND METADATA
    status TEXT DEFAULT 'active',           -- "active", "closed", "partial", "stopped"
    book_id TEXT DEFAULT 'social',          -- Which book this belongs to
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,
    
    -- LEARNING DATA
    market_conditions TEXT,                 -- "bull", "bear", "sideways"
    volatility_regime TEXT,                 -- "low", "medium", "high"
    
    -- NOTES
    notes TEXT                              -- Any additional notes
);

-- Create curator sources table (links curators to positions)
CREATE TABLE position_curator_sources (
    id TEXT PRIMARY KEY,                    -- "PEPE_solana_0xdetweiler"
    position_id TEXT NOT NULL,              -- Links to lowcap_positions.id
    curator_id TEXT NOT NULL,               -- Links to curators.curator_id
    social_signal_id TEXT,                  -- Links to curator_signals.id
    decision_strand_id TEXT,                -- Links to decision_lowcap strand
    
    -- Curator contribution to this position
    curator_confidence FLOAT,               -- Curator score when position opened
    curator_weight FLOAT,                   -- Weight of this curator's signal
    is_primary_curator BOOLEAN DEFAULT FALSE, -- Primary curator for this position
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign key constraints
    FOREIGN KEY (position_id) REFERENCES lowcap_positions(id) ON DELETE CASCADE,
    FOREIGN KEY (curator_id) REFERENCES curators(curator_id) ON DELETE CASCADE
);

-- Create position entries table (multiple entries per position)
CREATE TABLE position_entries (
    id TEXT PRIMARY KEY,                    -- "PEPE_solana_entry_001"
    position_id TEXT NOT NULL,              -- Links to lowcap_positions.id
    entry_number INTEGER NOT NULL,          -- 1, 2, 3 (which entry this is)
    
    -- Entry details
    entry_price FLOAT NOT NULL,             -- Price per token for this entry
    quantity FLOAT NOT NULL,                -- Number of tokens in this entry
    allocation_usd FLOAT NOT NULL,          -- USD amount for this entry
    allocation_pct FLOAT NOT NULL,          -- Percentage of total position for this entry
    
    -- Execution details
    venue TEXT NOT NULL,                    -- "Raydium", "Orca", "Uniswap"
    tx_hash TEXT,                           -- Transaction hash
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    slippage_pct FLOAT,                     -- Actual slippage
    fee_usd FLOAT,                          -- Gas/fee cost
    
    -- Entry strategy
    entry_type TEXT DEFAULT 'initial',      -- "initial", "dca", "dip_buy", "breakout"
    entry_trigger TEXT,                     -- "social_signal", "price_drop", "breakout"
    curator_id TEXT,                        -- Which curator triggered this entry
    
    -- Status
    status TEXT DEFAULT 'completed',        -- "pending", "completed", "failed", "cancelled"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign key constraints
    FOREIGN KEY (position_id) REFERENCES lowcap_positions(id) ON DELETE CASCADE
);

-- Create position exits table (staged exits per position)
CREATE TABLE position_exits (
    id TEXT PRIMARY KEY,                    -- "PEPE_solana_exit_001"
    position_id TEXT NOT NULL,              -- Links to lowcap_positions.id
    exit_number INTEGER NOT NULL,           -- 1, 2, 3 (which exit this is)
    
    -- Exit details
    exit_price FLOAT NOT NULL,              -- Price per token for this exit
    quantity FLOAT NOT NULL,                -- Number of tokens in this exit
    exit_pct FLOAT NOT NULL,                -- Percentage of position exited
    exit_usd FLOAT NOT NULL,                -- USD amount from this exit
    
    -- Execution details
    venue TEXT NOT NULL,                    -- "Raydium", "Orca", "Uniswap"
    tx_hash TEXT,                           -- Transaction hash
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    slippage_pct FLOAT,                     -- Actual slippage
    fee_usd FLOAT,                          -- Gas/fee cost
    
    -- Exit strategy
    exit_type TEXT NOT NULL,                -- "take_profit", "stop_loss", "full_exit", "staged"
    exit_trigger TEXT,                      -- "price_target", "stop_loss", "manual", "rule_based"
    gain_pct FLOAT,                         -- Percentage gain when exit was triggered
    
    -- Status
    status TEXT DEFAULT 'completed',        -- "pending", "completed", "failed", "cancelled"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign key constraints
    FOREIGN KEY (position_id) REFERENCES lowcap_positions(id) ON DELETE CASCADE
);

-- Create exit rules table (defines staged exit strategy)
CREATE TABLE position_exit_rules (
    id TEXT PRIMARY KEY,                    -- "PEPE_solana_rules"
    position_id TEXT NOT NULL,              -- Links to lowcap_positions.id
    
    -- Exit strategy configuration
    exit_strategy TEXT NOT NULL,            -- "staged", "full_exit", "hybrid"
    total_exit_pct FLOAT DEFAULT 100.0,    -- Total percentage to exit (100% = full exit)
    
    -- Staged exit rules (e.g., exit 20% at each 100% gain)
    stage_1_gain_pct FLOAT,                 -- First exit trigger (e.g., 100%)
    stage_1_exit_pct FLOAT,                 -- First exit percentage (e.g., 20%)
    stage_2_gain_pct FLOAT,                 -- Second exit trigger (e.g., 200%)
    stage_2_exit_pct FLOAT,                 -- Second exit percentage (e.g., 20%)
    stage_3_gain_pct FLOAT,                 -- Third exit trigger (e.g., 300%)
    stage_3_exit_pct FLOAT,                 -- Third exit percentage (e.g., 20%)
    stage_4_gain_pct FLOAT,                 -- Fourth exit trigger (e.g., 500%)
    stage_4_exit_pct FLOAT,                 -- Fourth exit percentage (e.g., 20%)
    final_exit_gain_pct FLOAT,              -- Final exit trigger (e.g., 1000%)
    final_exit_pct FLOAT,                   -- Final exit percentage (e.g., 20%)
    
    -- Stop loss
    stop_loss_pct FLOAT,                    -- Stop loss percentage (e.g., -50%)
    stop_loss_exit_pct FLOAT DEFAULT 100.0, -- Percentage to exit on stop loss
    
    -- Full exit price (optional)
    full_exit_price FLOAT,                  -- Specific price to exit everything
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,         -- Whether rules are active
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign key constraints
    FOREIGN KEY (position_id) REFERENCES lowcap_positions(id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX idx_lowcap_positions_token ON lowcap_positions(token_chain, token_contract);
CREATE INDEX idx_lowcap_positions_ticker ON lowcap_positions(token_ticker);
CREATE INDEX idx_lowcap_positions_status ON lowcap_positions(status);
CREATE INDEX idx_lowcap_positions_created ON lowcap_positions(created_at);
CREATE INDEX idx_lowcap_positions_book ON lowcap_positions(book_id);
CREATE INDEX idx_lowcap_positions_active ON lowcap_positions(book_id, status) WHERE status = 'active';

-- Create indexes for curator sources
CREATE INDEX idx_position_curator_sources_position ON position_curator_sources(position_id);
CREATE INDEX idx_position_curator_sources_curator ON position_curator_sources(curator_id);
CREATE INDEX idx_position_curator_sources_primary ON position_curator_sources(position_id, is_primary_curator) WHERE is_primary_curator = TRUE;

-- Create indexes for entries
CREATE INDEX idx_position_entries_position ON position_entries(position_id);
CREATE INDEX idx_position_entries_number ON position_entries(position_id, entry_number);
CREATE INDEX idx_position_entries_timestamp ON position_entries(timestamp);
CREATE INDEX idx_position_entries_status ON position_entries(status);

-- Create indexes for exits
CREATE INDEX idx_position_exits_position ON position_exits(position_id);
CREATE INDEX idx_position_exits_number ON position_exits(position_id, exit_number);
CREATE INDEX idx_position_exits_timestamp ON position_exits(timestamp);
CREATE INDEX idx_position_exits_status ON position_exits(status);

-- Create indexes for exit rules
CREATE INDEX idx_position_exit_rules_position ON position_exit_rules(position_id);
CREATE INDEX idx_position_exit_rules_active ON position_exit_rules(position_id, is_active) WHERE is_active = TRUE;

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
    p.*,
    -- Get primary curator info
    pc.curator_id as primary_curator_id,
    c.name as primary_curator_name,
    c.twitter_handle as primary_curator_twitter,
    c.telegram_handle as primary_curator_telegram,
    c.win_rate as primary_curator_win_rate,
    c.final_weight as primary_curator_weight,
    -- Count total curators for this position
    (SELECT COUNT(*) FROM position_curator_sources pcs WHERE pcs.position_id = p.id) as total_curator_sources
FROM lowcap_positions p
LEFT JOIN position_curator_sources pc ON p.id = pc.position_id AND pc.is_primary_curator = TRUE
LEFT JOIN curators c ON pc.curator_id = c.curator_id
WHERE p.status = 'active';

CREATE VIEW position_curator_details AS
SELECT 
    p.id as position_id,
    p.token_ticker,
    p.token_chain,
    p.status,
    p.total_allocation_pct,
    p.total_pnl_pct,
    pcs.curator_id,
    c.name as curator_name,
    c.twitter_handle,
    c.telegram_handle,
    c.win_rate as curator_win_rate,
    c.final_weight as curator_weight,
    pcs.curator_confidence,
    pcs.is_primary_curator,
    pcs.created_at as curator_signal_time
FROM lowcap_positions p
JOIN position_curator_sources pcs ON p.id = pcs.position_id
JOIN curators c ON pcs.curator_id = c.curator_id;

CREATE VIEW lowcap_performance_summary AS
SELECT 
    p.token_ticker,
    p.token_chain,
    p.status,
    p.total_allocation_pct,
    p.total_pnl_pct,
    p.total_pnl_usd,
    p.last_activity_timestamp,
    -- Curator info
    COUNT(DISTINCT pcs.curator_id) as num_curator_sources,
    AVG(pcs.curator_confidence) as avg_curator_confidence,
    MAX(pcs.curator_confidence) as max_curator_confidence
FROM lowcap_positions p
LEFT JOIN position_curator_sources pcs ON p.id = pcs.position_id
GROUP BY p.id, p.token_ticker, p.token_chain, p.status, p.total_allocation_pct, p.total_pnl_pct, p.total_pnl_usd, p.last_activity_timestamp;

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
    status TEXT,
    primary_curator_id TEXT,
    num_curator_sources INTEGER
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
        p.status,
        pc.curator_id as primary_curator_id,
        (SELECT COUNT(*)::INTEGER FROM position_curator_sources pcs WHERE pcs.position_id = p.id) as num_curator_sources
    FROM lowcap_positions p
    LEFT JOIN position_curator_sources pc ON p.id = pc.position_id AND pc.is_primary_curator = TRUE
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

-- Function to create position with curator sources
CREATE OR REPLACE FUNCTION create_position_with_curator(
    position_id_param TEXT,
    token_chain_param TEXT,
    token_contract_param TEXT,
    token_ticker_param TEXT,
    token_name_param TEXT,
    total_allocation_pct_param FLOAT,
    total_allocation_usd_param FLOAT,
    curator_id_param TEXT,
    curator_confidence_param FLOAT,
    social_signal_id_param TEXT DEFAULT NULL,
    decision_strand_id_param TEXT DEFAULT NULL,
    book_id_param TEXT DEFAULT 'social'
)
RETURNS BOOLEAN AS $$
DECLARE
    position_exists BOOLEAN;
BEGIN
    -- Check if position already exists
    SELECT EXISTS(SELECT 1 FROM lowcap_positions WHERE id = position_id_param) INTO position_exists;
    
    IF position_exists THEN
        -- Position exists, just add curator source
        INSERT INTO position_curator_sources (
            id, position_id, curator_id, social_signal_id, decision_strand_id,
            curator_confidence, curator_weight, is_primary_curator
        ) VALUES (
            position_id_param || '_' || curator_id_param,
            position_id_param,
            curator_id_param,
            social_signal_id_param,
            decision_strand_id_param,
            curator_confidence_param,
            curator_confidence_param, -- Use confidence as weight for now
            FALSE -- Not primary since position already exists
        );
        RETURN TRUE;
    ELSE
        -- Create new position and add curator as primary
        INSERT INTO lowcap_positions (
            id, token_chain, token_contract, token_ticker, token_name,
            total_allocation_pct, total_allocation_usd, book_id, status
        ) VALUES (
            position_id_param,
            token_chain_param,
            token_contract_param,
            token_ticker_param,
            token_name_param,
            total_allocation_pct_param,
            total_allocation_usd_param,
            book_id_param,
            'pending'
        );
        
        -- Add curator as primary source
        INSERT INTO position_curator_sources (
            id, position_id, curator_id, social_signal_id, decision_strand_id,
            curator_confidence, curator_weight, is_primary_curator
        ) VALUES (
            position_id_param || '_' || curator_id_param,
            position_id_param,
            curator_id_param,
            social_signal_id_param,
            decision_strand_id_param,
            curator_confidence_param,
            curator_confidence_param, -- Use confidence as weight for now
            TRUE -- Primary curator for new position
        );
        
        RETURN TRUE;
    END IF;
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Function to add entry to position
CREATE OR REPLACE FUNCTION add_position_entry(
    position_id_param TEXT,
    entry_price_param FLOAT,
    quantity_param FLOAT,
    allocation_usd_param FLOAT,
    venue_param TEXT,
    tx_hash_param TEXT DEFAULT NULL,
    entry_type_param TEXT DEFAULT 'initial',
    entry_trigger_param TEXT DEFAULT 'social_signal',
    curator_id_param TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    entry_number INTEGER;
    allocation_pct FLOAT;
    position_total_usd FLOAT;
BEGIN
    -- Get next entry number
    SELECT COALESCE(MAX(entry_number), 0) + 1 INTO entry_number
    FROM position_entries 
    WHERE position_id = position_id_param;
    
    -- Get position total allocation
    SELECT total_allocation_usd INTO position_total_usd
    FROM lowcap_positions 
    WHERE id = position_id_param;
    
    -- Calculate allocation percentage
    allocation_pct := (allocation_usd_param / position_total_usd) * 100;
    
    -- Insert entry
    INSERT INTO position_entries (
        id, position_id, entry_number, entry_price, quantity, 
        allocation_usd, allocation_pct, venue, tx_hash, 
        entry_type, entry_trigger, curator_id, timestamp
    ) VALUES (
        position_id_param || '_entry_' || LPAD(entry_number::TEXT, 3, '0'),
        position_id_param,
        entry_number,
        entry_price_param,
        quantity_param,
        allocation_usd_param,
        allocation_pct,
        venue_param,
        tx_hash_param,
        entry_type_param,
        entry_trigger_param,
        curator_id_param,
        NOW()
    );
    
    -- Update position totals
    UPDATE lowcap_positions 
    SET 
        total_quantity = total_quantity + quantity_param,
        avg_entry_price = (
            SELECT AVG(entry_price) 
            FROM position_entries 
            WHERE position_id = position_id_param AND status = 'completed'
        ),
        first_entry_timestamp = COALESCE(first_entry_timestamp, NOW()),
        last_activity_timestamp = NOW(),
        updated_at = NOW()
    WHERE id = position_id_param;
    
    RETURN TRUE;
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Function to add exit to position
CREATE OR REPLACE FUNCTION add_position_exit(
    position_id_param TEXT,
    exit_price_param FLOAT,
    quantity_param FLOAT,
    venue_param TEXT,
    tx_hash_param TEXT DEFAULT NULL,
    exit_type_param TEXT DEFAULT 'take_profit',
    exit_trigger_param TEXT DEFAULT 'rule_based'
)
RETURNS BOOLEAN AS $$
DECLARE
    exit_number INTEGER;
    exit_pct FLOAT;
    exit_usd FLOAT;
    gain_pct FLOAT;
    avg_entry_price FLOAT;
    current_quantity FLOAT;
BEGIN
    -- Get next exit number
    SELECT COALESCE(MAX(exit_number), 0) + 1 INTO exit_number
    FROM position_exits 
    WHERE position_id = position_id_param;
    
    -- Get position details
    SELECT total_quantity, avg_entry_price INTO current_quantity, avg_entry_price
    FROM lowcap_positions 
    WHERE id = position_id_param;
    
    -- Calculate exit percentage and USD
    exit_pct := (quantity_param / current_quantity) * 100;
    exit_usd := exit_price_param * quantity_param;
    
    -- Calculate gain percentage
    IF avg_entry_price > 0 THEN
        gain_pct := ((exit_price_param - avg_entry_price) / avg_entry_price) * 100;
    ELSE
        gain_pct := 0;
    END IF;
    
    -- Insert exit
    INSERT INTO position_exits (
        id, position_id, exit_number, exit_price, quantity, 
        exit_pct, exit_usd, venue, tx_hash, 
        exit_type, exit_trigger, gain_pct, timestamp
    ) VALUES (
        position_id_param || '_exit_' || LPAD(exit_number::TEXT, 3, '0'),
        position_id_param,
        exit_number,
        exit_price_param,
        quantity_param,
        exit_pct,
        exit_usd,
        venue_param,
        tx_hash_param,
        exit_type_param,
        exit_trigger_param,
        gain_pct,
        NOW()
    );
    
    -- Update position totals
    UPDATE lowcap_positions 
    SET 
        total_quantity = total_quantity - quantity_param,
        total_pnl_usd = total_pnl_usd + (exit_usd - (quantity_param * avg_entry_price)),
        last_activity_timestamp = NOW(),
        updated_at = NOW()
    WHERE id = position_id_param;
    
    -- Update P&L percentage
    UPDATE lowcap_positions 
    SET total_pnl_pct = (total_pnl_usd / total_allocation_usd) * 100
    WHERE id = position_id_param;
    
    RETURN TRUE;
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Function to set exit rules for position
CREATE OR REPLACE FUNCTION set_position_exit_rules(
    position_id_param TEXT,
    exit_strategy_param TEXT DEFAULT 'staged',
    stage_1_gain_pct_param FLOAT DEFAULT 100.0,
    stage_1_exit_pct_param FLOAT DEFAULT 20.0,
    stage_2_gain_pct_param FLOAT DEFAULT 200.0,
    stage_2_exit_pct_param FLOAT DEFAULT 20.0,
    stage_3_gain_pct_param FLOAT DEFAULT 300.0,
    stage_3_exit_pct_param FLOAT DEFAULT 20.0,
    stage_4_gain_pct_param FLOAT DEFAULT 500.0,
    stage_4_exit_pct_param FLOAT DEFAULT 20.0,
    final_exit_gain_pct_param FLOAT DEFAULT 1000.0,
    final_exit_pct_param FLOAT DEFAULT 20.0,
    stop_loss_pct_param FLOAT DEFAULT -50.0,
    full_exit_price_param FLOAT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    -- Insert or update exit rules
    INSERT INTO position_exit_rules (
        id, position_id, exit_strategy,
        stage_1_gain_pct, stage_1_exit_pct,
        stage_2_gain_pct, stage_2_exit_pct,
        stage_3_gain_pct, stage_3_exit_pct,
        stage_4_gain_pct, stage_4_exit_pct,
        final_exit_gain_pct, final_exit_pct,
        stop_loss_pct, full_exit_price
    ) VALUES (
        position_id_param || '_rules',
        position_id_param,
        exit_strategy_param,
        stage_1_gain_pct_param, stage_1_exit_pct_param,
        stage_2_gain_pct_param, stage_2_exit_pct_param,
        stage_3_gain_pct_param, stage_3_exit_pct_param,
        stage_4_gain_pct_param, stage_4_exit_pct_param,
        final_exit_gain_pct_param, final_exit_pct_param,
        stop_loss_pct_param, full_exit_price_param
    )
    ON CONFLICT (id) DO UPDATE SET
        exit_strategy = EXCLUDED.exit_strategy,
        stage_1_gain_pct = EXCLUDED.stage_1_gain_pct,
        stage_1_exit_pct = EXCLUDED.stage_1_exit_pct,
        stage_2_gain_pct = EXCLUDED.stage_2_gain_pct,
        stage_2_exit_pct = EXCLUDED.stage_2_exit_pct,
        stage_3_gain_pct = EXCLUDED.stage_3_gain_pct,
        stage_3_exit_pct = EXCLUDED.stage_3_exit_pct,
        stage_4_gain_pct = EXCLUDED.stage_4_gain_pct,
        stage_4_exit_pct = EXCLUDED.stage_4_exit_pct,
        final_exit_gain_pct = EXCLUDED.final_exit_gain_pct,
        final_exit_pct = EXCLUDED.final_exit_pct,
        stop_loss_pct = EXCLUDED.stop_loss_pct,
        full_exit_price = EXCLUDED.full_exit_price,
        updated_at = NOW();
    
    RETURN TRUE;
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL ON lowcap_positions TO your_app_user;
-- GRANT ALL ON position_curator_sources TO your_app_user;
-- GRANT ALL ON active_lowcap_positions TO your_app_user;
-- GRANT ALL ON position_curator_details TO your_app_user;
-- GRANT ALL ON lowcap_performance_summary TO your_app_user;
-- GRANT EXECUTE ON FUNCTION get_active_positions_by_token(TEXT, TEXT) TO your_app_user;
-- GRANT EXECUTE ON FUNCTION get_portfolio_summary(TEXT) TO your_app_user;
-- GRANT EXECUTE ON FUNCTION close_position(TEXT, FLOAT, TEXT, TEXT, FLOAT, FLOAT) TO your_app_user;
-- GRANT EXECUTE ON FUNCTION create_position_with_curator(TEXT, TEXT, TEXT, TEXT, TEXT, FLOAT, FLOAT, TEXT, FLOAT, TEXT, TEXT, TEXT) TO your_app_user;
