#!/usr/bin/env python3
"""
Test Direct RPC Call

This test calls the RPC function directly to see what's happening.
"""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.supabase_manager import SupabaseManager


async def test_direct_rpc():
    """Test RPC function directly"""
    print("🧪 Testing Direct RPC Call")
    print("=" * 30)
    
    supabase_manager = SupabaseManager()
    
    # Test the RPC function directly
    print("\n📊 Direct RPC Test")
    print("-" * 20)
    
    try:
        # Test with a simple query
        result = supabase_manager.client.rpc('execute_select_query', {
            'query_text': "SELECT id, kind FROM AD_strands WHERE kind = %s LIMIT 1",
            'query_params': ['prediction_review']
        }).execute()
        
        print(f"✅ RPC Success: {result.data}")
        
    except Exception as e:
        print(f"❌ RPC Error: {e}")
    
    # Test with the problematic query
    print("\n📊 Problematic Query Test")
    print("-" * 30)
    
    try:
        result = supabase_manager.client.rpc('execute_select_query', {
            'query_text': "SELECT id, kind, braid_level FROM AD_strands WHERE kind = %s AND braid_level > %s LIMIT 1",
            'query_params': ['prediction_review', 1]
        }).execute()
        
        print(f"✅ RPC Success: {result.data}")
        
    except Exception as e:
        print(f"❌ RPC Error: {e}")
    
    # Test with different parameter order
    print("\n📊 Different Parameter Order Test")
    print("-" * 35)
    
    try:
        result = supabase_manager.client.rpc('execute_select_query', {
            'query_text': "SELECT id, kind, braid_level FROM AD_strands WHERE braid_level > %s AND kind = %s LIMIT 1",
            'query_params': [1, 'prediction_review']
        }).execute()
        
        print(f"✅ RPC Success: {result.data}")
        
    except Exception as e:
        print(f"❌ RPC Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_direct_rpc())
