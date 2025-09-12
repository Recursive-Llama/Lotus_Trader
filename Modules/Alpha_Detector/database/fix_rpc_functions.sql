-- Fixed RPC Functions for Parameter Substitution
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
BEGIN
    -- Convert JSONB array to PostgreSQL array
    SELECT ARRAY(SELECT jsonb_array_elements_text(query_params)) INTO param_array;
    
    -- Replace %s with actual parameters
    final_query := query_text;
    FOR i IN 1..array_length(param_array, 1) LOOP
        final_query := replace(final_query, '%s', quote_literal(param_array[i]));
    END LOOP;
    
    -- Execute the final query and return results
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
BEGIN
    -- Convert JSONB array to PostgreSQL array
    SELECT ARRAY(SELECT jsonb_array_elements_text(query_params)) INTO param_array;
    
    -- Replace %s with actual parameters
    final_query := query_text;
    FOR i IN 1..array_length(param_array, 1) LOOP
        final_query := replace(final_query, '%s', quote_literal(param_array[i]));
    END LOOP;
    
    -- Execute the final query
    EXECUTE final_query;
    
    -- Return success result
    result := '{"success": true, "message": "Query executed successfully"}'::JSONB;
    RETURN NEXT;
END;
$$;
