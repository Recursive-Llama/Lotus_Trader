-- Simple Lowcap Positions Schema - ONE TABLE
-- Multi-entry/exit managed with JSON arrays

-- Drop existing functions first
DROP FUNCTION IF EXISTS get_active_positions_by_token(TEXT, TEXT);
DROP FUNCTION IF EXISTS get_portfolio_summary(TEXT);
DROP FUNCTION IF EXISTS close_position(TEXT, FLOAT, TEXT, TEXT, FLOAT, FLOAT);
DROP FUNCTION IF EXISTS create_position_with_curator(TEXT, TEXT, TEXT, TEXT, TEXT, FLOAT, FLOAT, TEXT, FLOAT, TEXT, TEXT, TEXT);
DROP FUNCTION IF EXISTS add_position_entry(TEXT, FLOAT, FLOAT, FLOAT, TEXT, TEXT, TEXT, TEXT, TEXT);
DROP FUNCTION IF EXISTS add_position_exit(TEXT, FLOAT, FLOAT, TEXT, TEXT, TEXT, TEXT);
DROP FUNCTION IF EXISTS set_position_exit_rules(TEXT, TEXT, FLOAT, FLOAT, FLOAT, FLOAT, FLOAT, FLOAT, FLOAT, FLOAT, FLOAT, FLOAT, FLOAT, FLOAT);

-- Drop existing table
DROP TABLE IF EXISTS lowcap_positions CASCADE;

-- Create ONE simple table
CREATE TABLE lowcap_positions (
    -- PRIMARY KEY: Token-based ID
    id TEXT PRIMARY KEY,                    -- "PEPE_solana"
    
    -- TOKEN INFORMATION
    token_chain TEXT NOT NULL,              -- "solana", "ethereum", "base"
    token_contract TEXT NOT NULL,           -- Token contract address
    token_ticker TEXT NOT NULL,             -- "PEPE", "BONK"
    token_name TEXT,                        -- "Pepe Coin"
    
    -- POSITION OVERVIEW
    total_allocation_pct FLOAT NOT NULL,    -- Total allocation percentage (e.g., 3.0%)
    total_allocation_usd FLOAT NOT NULL,    -- Total allocation USD amount
    current_price FLOAT,                    -- Current market price per token
    total_quantity FLOAT DEFAULT 0,         -- Total tokens held
    
    -- AGGREGATE PERFORMANCE
    total_pnl_usd FLOAT DEFAULT 0,          -- Total P&L in USD
    total_pnl_pct FLOAT DEFAULT 0,          -- Total P&L percentage
    total_fees_usd FLOAT DEFAULT 0,         -- Total fees paid
    avg_entry_price FLOAT,                  -- Weighted average entry price
    
    -- ENTRIES (JSON array)
    entries JSONB DEFAULT '[]',             -- Array of entry objects
    -- Example: [{"price": 0.001, "quantity": 1000000, "usd": 1000, "venue": "Raydium", "tx": "0x123", "timestamp": "2024-12-15T10:30:00Z", "type": "initial"}]
    
    -- EXITS (JSON array)
    exits JSONB DEFAULT '[]',               -- Array of exit objects
    -- Example: [{"price": 0.002, "quantity": 200000, "usd": 400, "venue": "Raydium", "tx": "0x456", "timestamp": "2024-12-15T11:30:00Z", "type": "take_profit", "gain_pct": 100}]
    
    -- EXIT RULES (JSON object)
    exit_rules JSONB DEFAULT '{}',          -- Exit strategy configuration
    -- Example: {"strategy": "staged", "stages": [{"gain_pct": 100, "exit_pct": 20}, {"gain_pct": 200, "exit_pct": 20}], "stop_loss": -50}
    
    -- CURATOR SOURCES (JSON array)
    curator_sources JSONB DEFAULT '[]',     -- Array of curator sources
    -- Example: [{"curator_id": "0xdetweiler", "confidence": 0.85, "is_primary": true, "signal_id": "signal_123"}]
    
    -- STATUS AND METADATA
    status TEXT DEFAULT 'active',           -- "active", "closed", "partial", "stopped"
    book_id TEXT DEFAULT 'social',          -- Which book this belongs to
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,
    
    -- TIMESTAMPS
    first_entry_timestamp TIMESTAMP WITH TIME ZONE,
    last_activity_timestamp TIMESTAMP WITH TIME ZONE,
    
    -- NOTES
    notes TEXT                              -- Any additional notes
);

-- Create indexes for performance
CREATE INDEX idx_lowcap_positions_token ON lowcap_positions(token_chain, token_contract);
CREATE INDEX idx_lowcap_positions_ticker ON lowcap_positions(token_ticker);
CREATE INDEX idx_lowcap_positions_status ON lowcap_positions(status);
CREATE INDEX idx_lowcap_positions_book ON lowcap_positions(book_id);
CREATE INDEX idx_lowcap_positions_active ON lowcap_positions(book_id, status) WHERE status = 'active';

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

-- Simple views
CREATE VIEW active_lowcap_positions AS
SELECT 
    p.*,
    -- Extract primary curator info
    (p.curator_sources->0->>'curator_id') as primary_curator_id,
    (p.curator_sources->0->>'confidence')::FLOAT as primary_curator_confidence,
    -- Count entries and exits
    jsonb_array_length(p.entries) as num_entries,
    jsonb_array_length(p.exits) as num_exits
FROM lowcap_positions p
WHERE p.status = 'active';

-- Simple functions
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
    num_entries INTEGER,
    num_exits INTEGER
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
        jsonb_array_length(p.entries)::INTEGER as num_entries,
        jsonb_array_length(p.exits)::INTEGER as num_exits
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
    book_nav FLOAT := 100000.0; -- Mock NAV
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

-- Function to add entry to position
CREATE OR REPLACE FUNCTION add_position_entry(
    position_id_param TEXT,
    entry_price_param FLOAT,
    quantity_param FLOAT,
    allocation_usd_param FLOAT,
    venue_param TEXT,
    tx_hash_param TEXT DEFAULT NULL,
    entry_type_param TEXT DEFAULT 'initial'
)
RETURNS BOOLEAN AS $$
DECLARE
    new_entry JSONB;
    current_entries JSONB;
    new_avg_price FLOAT;
    new_total_quantity FLOAT;
BEGIN
    -- Create new entry object
    new_entry := jsonb_build_object(
        'price', entry_price_param,
        'quantity', quantity_param,
        'usd', allocation_usd_param,
        'venue', venue_param,
        'tx', tx_hash_param,
        'timestamp', NOW(),
        'type', entry_type_param
    );
    
    -- Get current entries and add new one
    SELECT entries INTO current_entries FROM lowcap_positions WHERE id = position_id_param;
    current_entries := current_entries || new_entry;
    
    -- Calculate new totals
    SELECT 
        SUM((entry->>'quantity')::FLOAT),
        SUM((entry->>'usd')::FLOAT) / SUM((entry->>'quantity')::FLOAT)
    INTO new_total_quantity, new_avg_price
    FROM jsonb_array_elements(current_entries) AS entry;
    
    -- Update position
    UPDATE lowcap_positions 
    SET 
        entries = current_entries,
        total_quantity = new_total_quantity,
        avg_entry_price = new_avg_price,
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
    exit_type_param TEXT DEFAULT 'take_profit'
)
RETURNS BOOLEAN AS $$
DECLARE
    new_exit JSONB;
    current_exits JSONB;
    avg_entry_price FLOAT;
    gain_pct FLOAT;
    exit_usd FLOAT;
    new_total_quantity FLOAT;
    new_total_pnl FLOAT;
BEGIN
    -- Get current position data
    SELECT avg_entry_price, total_quantity, exits INTO avg_entry_price, new_total_quantity, current_exits
    FROM lowcap_positions WHERE id = position_id_param;
    
    -- Calculate gain percentage and exit USD
    gain_pct := ((exit_price_param - avg_entry_price) / avg_entry_price) * 100;
    exit_usd := exit_price_param * quantity_param;
    
    -- Create new exit object
    new_exit := jsonb_build_object(
        'price', exit_price_param,
        'quantity', quantity_param,
        'usd', exit_usd,
        'venue', venue_param,
        'tx', tx_hash_param,
        'timestamp', NOW(),
        'type', exit_type_param,
        'gain_pct', gain_pct
    );
    
    -- Add to exits array
    current_exits := current_exits || new_exit;
    
    -- Update totals
    new_total_quantity := new_total_quantity - quantity_param;
    new_total_pnl := new_total_pnl + (exit_usd - (quantity_param * avg_entry_price));
    
    -- Update position
    UPDATE lowcap_positions 
    SET 
        exits = current_exits,
        total_quantity = new_total_quantity,
        total_pnl_usd = new_total_pnl,
        total_pnl_pct = (new_total_pnl / total_allocation_usd) * 100,
        last_activity_timestamp = NOW(),
        updated_at = NOW()
    WHERE id = position_id_param;
    
    RETURN TRUE;
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Function to set exit rules
CREATE OR REPLACE FUNCTION set_position_exit_rules(
    position_id_param TEXT,
    strategy_param TEXT DEFAULT 'staged',
    stages_param JSONB DEFAULT '[]',
    stop_loss_param FLOAT DEFAULT -50.0,
    full_exit_price_param FLOAT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    new_rules JSONB;
BEGIN
    -- Create exit rules object
    new_rules := jsonb_build_object(
        'strategy', strategy_param,
        'stages', stages_param,
        'stop_loss', stop_loss_param,
        'full_exit_price', full_exit_price_param
    );
    
    -- Update position
    UPDATE lowcap_positions 
    SET 
        exit_rules = new_rules,
        updated_at = NOW()
    WHERE id = position_id_param;
    
    RETURN TRUE;
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Function to create position with curator
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
    social_signal_id_param TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    position_exists BOOLEAN;
    new_curator_source JSONB;
    current_sources JSONB;
BEGIN
    -- Check if position exists
    SELECT EXISTS(SELECT 1 FROM lowcap_positions WHERE id = position_id_param) INTO position_exists;
    
    -- Create curator source object
    new_curator_source := jsonb_build_object(
        'curator_id', curator_id_param,
        'confidence', curator_confidence_param,
        'is_primary', NOT position_exists,
        'signal_id', social_signal_id_param,
        'added_at', NOW()
    );
    
    IF position_exists THEN
        -- Add curator source to existing position
        SELECT curator_sources INTO current_sources FROM lowcap_positions WHERE id = position_id_param;
        current_sources := current_sources || new_curator_source;
        
        UPDATE lowcap_positions 
        SET curator_sources = current_sources, updated_at = NOW()
        WHERE id = position_id_param;
    ELSE
        -- Create new position
        INSERT INTO lowcap_positions (
            id, token_chain, token_contract, token_ticker, token_name,
            total_allocation_pct, total_allocation_usd, book_id, status,
            curator_sources
        ) VALUES (
            position_id_param, token_chain_param, token_contract_param, 
            token_ticker_param, token_name_param, total_allocation_pct_param, 
            total_allocation_usd_param, 'social', 'pending',
            jsonb_build_array(new_curator_source)
        );
    END IF;
    
    RETURN TRUE;
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;
