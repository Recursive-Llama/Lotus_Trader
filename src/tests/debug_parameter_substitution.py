#!/usr/bin/env python3
"""
Debug Parameter Substitution

This test helps us understand exactly how parameters are being substituted.
"""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.supabase_manager import SupabaseManager


async def debug_parameter_substitution():
    """Debug how parameters are being substituted"""
    print("🔍 Debugging Parameter Substitution")
    print("=" * 40)
    
    supabase_manager = SupabaseManager()
    
    # Test with a simple query to see the substitution
    print("\n📊 Test 1: Simple Parameter Substitution")
    print("-" * 40)
    
    try:
        # Create a debug RPC function that shows us the final query
        debug_query = """
            CREATE OR REPLACE FUNCTION debug_query_substitution(
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
            BEGIN
                -- Convert JSONB array to PostgreSQL array
                SELECT ARRAY(SELECT jsonb_array_elements_text(query_params)) INTO param_array;
                
                -- Get the number of parameters
                param_count := array_length(param_array, 1);
                
                -- Replace %s with actual parameters in order
                final_query := query_text;
                FOR i IN 1..param_count LOOP
                    final_query := replace(final_query, '%s', quote_literal(param_array[i]));
                END LOOP;
                
                -- Return the final query
                result := jsonb_build_object(
                    'original_query', query_text,
                    'parameters', query_params,
                    'param_array', to_jsonb(param_array),
                    'final_query', final_query,
                    'param_count', param_count
                );
                RETURN NEXT;
            END;
            $$;
        """
        
        # Execute the debug function creation
        await supabase_manager.execute_query(debug_query)
        
        # Test with our problematic query
        test_query = "SELECT * FROM AD_strands WHERE kind = %s AND braid_level > %s"
        test_params = ['prediction_review', 1]
        
        print(f"Original Query: {test_query}")
        print(f"Parameters: {test_params}")
        
        # Call the debug function
        debug_result = supabase_manager.client.rpc('debug_query_substitution', {
            'query_text': test_query,
            'query_params': test_params
        }).execute()
        
        if debug_result.data:
            result = debug_result.data[0]['result']
            print(f"\nDebug Result:")
            print(f"  Original Query: {result['original_query']}")
            print(f"  Parameters: {result['parameters']}")
            print(f"  Param Array: {result['param_array']}")
            print(f"  Final Query: {result['final_query']}")
            print(f"  Param Count: {result['param_count']}")
        
    except Exception as e:
        print(f"Debug error: {e}")


if __name__ == "__main__":
    asyncio.run(debug_parameter_substitution())
