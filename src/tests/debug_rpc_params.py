#!/usr/bin/env python3
"""
Debug RPC Parameter Format

This test helps us understand what format the RPC functions expect
and fix the parameter passing issue.
"""

import asyncio
import json
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.supabase_manager import SupabaseManager


async def debug_rpc_parameters():
    """Debug RPC parameter format"""
    print("🔍 Debugging RPC Parameter Format")
    print("=" * 40)
    
    supabase_manager = SupabaseManager()
    
    # Test 1: Simple SELECT query
    print("\n📊 Test 1: Simple SELECT Query")
    print("-" * 30)
    
    try:
        query = "SELECT COUNT(*) FROM AD_strands WHERE kind = %s"
        params = ['prediction_review']
        
        print(f"Query: {query}")
        print(f"Params (Python list): {params}")
        print(f"Params (JSON string): {json.dumps(params)}")
        
        result = await supabase_manager.execute_query(query, params)
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Test different parameter formats
    print("\n📊 Test 2: Different Parameter Formats")
    print("-" * 40)
    
    test_formats = [
        ['prediction_review'],  # Python list
        json.dumps(['prediction_review']),  # JSON string
        '["prediction_review"]',  # JSON string literal
        [{'param': 'prediction_review'}],  # List of dicts
    ]
    
    for i, test_params in enumerate(test_formats):
        try:
            print(f"\nFormat {i+1}: {test_params} (type: {type(test_params)})")
            
            # Test with direct RPC call
            result = supabase_manager.client.rpc('execute_select_query', {
                'query_text': "SELECT COUNT(*) FROM AD_strands WHERE kind = %s",
                'query_params': test_params
            }).execute()
            
            print(f"  ✅ Success: {result.data}")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # Test 3: Check what the RPC function actually receives
    print("\n📊 Test 3: RPC Function Input Analysis")
    print("-" * 40)
    
    try:
        # Create a test RPC function that shows us what it receives
        debug_query = """
            CREATE OR REPLACE FUNCTION debug_params(
                query_text TEXT,
                query_params JSONB DEFAULT '[]'::JSONB
            )
            RETURNS TABLE(result JSONB)
            LANGUAGE plpgsql
            AS $$
            BEGIN
                result := jsonb_build_object(
                    'query_text', query_text,
                    'query_params', query_params,
                    'params_type', pg_typeof(query_params),
                    'params_is_array', jsonb_typeof(query_params) = 'array',
                    'params_length', jsonb_array_length(query_params)
                );
                RETURN NEXT;
            END;
            $$;
        """
        
        # Execute the debug function creation
        await supabase_manager.execute_query(debug_query)
        
        # Test with our parameters
        debug_result = supabase_manager.client.rpc('debug_params', {
            'query_text': "SELECT COUNT(*) FROM AD_strands WHERE kind = %s",
            'query_params': json.dumps(['prediction_review'])
        }).execute()
        
        print(f"Debug result: {debug_result.data}")
        
    except Exception as e:
        print(f"Debug error: {e}")


if __name__ == "__main__":
    asyncio.run(debug_rpc_parameters())
