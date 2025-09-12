-- Correct RPC Functions for Parameter Substitution
-- Run this in Supabase SQL Editor

-- Function for SELECT queries with parameter substitution
CREATE OR REPLACE FUNCTION execute_select_query(
    query_text TEXT,
    query_params JSONB DEFAULT '[]'::JSONB
)
RETURNS TABLE(result JSONB)
LANGUAGE plpgsql
AS $$
DECLARE
    param_array TEXT[];
    i INTEGER;
    final_query TEXT;
    rec RECORD;
    param_count INTEGER;
    current_pos INTEGER;
    next_pos INTEGER;
BEGIN
    -- Convert JSONB array to PostgreSQL array
    SELECT ARRAY(SELECT jsonb_array_elements_text(query_params)) INTO param_array;
    
    -- Get the number of parameters
    param_count := array_length(param_array, 1);
    
    -- Replace %s with actual parameters one by one in order
    final_query := query_text;
    current_pos := 1;
    
    FOR i IN 1..param_count LOOP
        -- Find the next %s position
        next_pos := position('%s' in substring(final_query from current_pos));
        
        IF next_pos > 0 THEN
            -- Replace the first %s with the current parameter
            final_query := overlay(final_query placing quote_literal(param_array[i]) from current_pos + next_pos - 1 for 2);
            current_pos := current_pos + next_pos + length(quote_literal(param_array[i])) - 1;
        END IF;
    END LOOP;
    
    -- Execute the final query and return results as JSONB
    FOR rec IN EXECUTE final_query LOOP
        result := to_jsonb(rec);
        RETURN NEXT;
    END LOOP;
END;
$$;

-- Function for INSERT/UPDATE/DELETE queries with parameter substitution
CREATE OR REPLACE FUNCTION execute_modify_query(
    query_text TEXT,
    query_params JSONB DEFAULT '[]'::JSONB
)
RETURNS TABLE(result JSONB)
LANGUAGE plpgsql
AS $$
DECLARE
    param_array TEXT[];
    i INTEGER;
    final_query TEXT;
    param_count INTEGER;
    current_pos INTEGER;
    next_pos INTEGER;
BEGIN
    -- Convert JSONB array to PostgreSQL array
    SELECT ARRAY(SELECT jsonb_array_elements_text(query_params)) INTO param_array;
    
    -- Get the number of parameters
    param_count := array_length(param_array, 1);
    
    -- Replace %s with actual parameters one by one in order
    final_query := query_text;
    current_pos := 1;
    
    FOR i IN 1..param_count LOOP
        -- Find the next %s position
        next_pos := position('%s' in substring(final_query from current_pos));
        
        IF next_pos > 0 THEN
            -- Replace the first %s with the current parameter
            final_query := overlay(final_query placing quote_literal(param_array[i]) from current_pos + next_pos - 1 for 2);
            current_pos := current_pos + next_pos + length(quote_literal(param_array[i])) - 1;
        END IF;
    END LOOP;
    
    -- Execute the final query
    EXECUTE final_query;
    
    -- Return success result
    result := '{"success": true, "message": "Query executed successfully"}'::JSONB;
    RETURN NEXT;
END;
$$;
