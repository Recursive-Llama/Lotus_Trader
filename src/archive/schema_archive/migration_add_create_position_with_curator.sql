-- Migration: Add create_position_with_curator function with features initialization
-- This function creates positions and initializes the features field with pair_created_at and market_cap

-- Drop existing function if it exists
DROP FUNCTION IF EXISTS create_position_with_curator(TEXT, TEXT, TEXT, TEXT, TEXT, FLOAT, FLOAT, TEXT, FLOAT, TEXT);

-- Create function to create position with curator and initialize features
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
        -- Create new position with initial features
        INSERT INTO lowcap_positions (
            id, token_chain, token_contract, token_ticker, token_name,
            total_allocation_pct, total_allocation_usd, book_id, status,
            curator_sources, features
        ) VALUES (
            position_id_param, token_chain_param, token_contract_param, 
            token_ticker_param, token_name_param, total_allocation_pct_param, 
            total_allocation_usd_param, 'social', 'pending',
            jsonb_build_array(new_curator_source),
            jsonb_build_object(
                'pair_created_at', '',
                'market_cap', 0.0,
                'features_initialized_at', NOW()
            )
        );
    END IF;
    
    RETURN TRUE;
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission (adjust as needed for your setup)
-- GRANT EXECUTE ON FUNCTION create_position_with_curator(TEXT, TEXT, TEXT, TEXT, TEXT, FLOAT, FLOAT, TEXT, FLOAT, TEXT) TO your_app_user;
