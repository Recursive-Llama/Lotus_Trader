-- Supabase RPC Functions for Alpha Detector Module
-- These functions enable raw SQL query execution through Supabase RPC

-- Function to execute SELECT queries
CREATE OR REPLACE FUNCTION execute_select_query(
    query_text TEXT,
    query_params JSONB DEFAULT '[]'::JSONB
)
RETURNS TABLE(result JSONB)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    rec RECORD;
    param_array TEXT[];
    i INTEGER;
    final_query TEXT;
BEGIN
    -- Convert JSONB array to TEXT array
    param_array := ARRAY(
        SELECT jsonb_array_elements_text(query_params)
    );
    
    -- Replace %s placeholders with actual parameters
    final_query := query_text;
    FOR i IN 1..array_length(param_array, 1) LOOP
        final_query := replace(final_query, '%s', quote_literal(param_array[i]));
    END LOOP;
    
    -- Execute the query and return results as JSONB
    FOR rec IN EXECUTE final_query LOOP
        result := to_jsonb(rec);
        RETURN NEXT;
    END LOOP;
END;
$$;

-- Function to execute INSERT/UPDATE/DELETE queries
CREATE OR REPLACE FUNCTION execute_modify_query(
    query_text TEXT,
    query_params JSONB DEFAULT '[]'::JSONB
)
RETURNS TABLE(result JSONB)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    param_array TEXT[];
    i INTEGER;
    final_query TEXT;
    affected_rows INTEGER;
BEGIN
    -- Convert JSONB array to TEXT array
    param_array := ARRAY(
        SELECT jsonb_array_elements_text(query_params)
    );
    
    -- Replace %s placeholders with actual parameters
    final_query := query_text;
    FOR i IN 1..array_length(param_array, 1) LOOP
        final_query := replace(final_query, '%s', quote_literal(param_array[i]));
    END LOOP;
    
    -- Execute the query
    EXECUTE final_query;
    
    -- Get the number of affected rows
    GET DIAGNOSTICS affected_rows = ROW_COUNT;
    
    -- Return the result
    result := jsonb_build_object('affected_rows', affected_rows);
    RETURN NEXT;
END;
$$;

-- Grant execute permissions to authenticated users
GRANT EXECUTE ON FUNCTION execute_select_query(TEXT, JSONB) TO authenticated;
GRANT EXECUTE ON FUNCTION execute_modify_query(TEXT, JSONB) TO authenticated;

-- Example usage:
-- SELECT * FROM execute_select_query('SELECT * FROM AD_strands WHERE kind = %s', '["pattern"]'::JSONB);
-- SELECT * FROM execute_modify_query('INSERT INTO AD_strands (id, kind) VALUES (%s, %s)', '["test_id", "test_kind"]'::JSONB);
