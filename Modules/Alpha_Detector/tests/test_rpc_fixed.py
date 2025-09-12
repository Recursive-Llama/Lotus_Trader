#!/usr/bin/env python3
"""
Test Fixed RPC Functions

This test verifies that the RPC functions are working correctly
with the fixed parameter format.
"""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.supabase_manager import SupabaseManager


async def test_rpc_functions():
    """Test the fixed RPC functions"""
    print("🧪 Testing Fixed RPC Functions")
    print("=" * 40)
    
    supabase_manager = SupabaseManager()
    
    # Test 1: SELECT query that returns JSONB (should work)
    print("\n📊 Test 1: SELECT with JSONB return")
    print("-" * 35)
    
    try:
        query = "SELECT id, kind, created_at FROM AD_strands WHERE kind = %s LIMIT 3"
        params = ['prediction_review']
        
        print(f"Query: {query}")
        print(f"Params: {params}")
        
        result = await supabase_manager.execute_query(query, params)
        print(f"✅ Success: {len(result)} rows returned")
        for row in result:
            print(f"  - {row}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: COUNT query (will fail due to return type)
    print("\n📊 Test 2: COUNT query (expected to fail)")
    print("-" * 40)
    
    try:
        query = "SELECT COUNT(*) FROM AD_strands WHERE kind = %s"
        params = ['prediction_review']
        
        print(f"Query: {query}")
        print(f"Params: {params}")
        
        result = await supabase_manager.execute_query(query, params)
        print(f"✅ Success: {result}")
        
    except Exception as e:
        print(f"❌ Expected Error: {e}")
    
    # Test 3: Test the learning system query
    print("\n📊 Test 3: Learning System Query")
    print("-" * 35)
    
    try:
        query = "SELECT * FROM AD_strands WHERE kind = %s AND braid_level > %s"
        params = ['prediction_review', 1]
        
        print(f"Query: {query}")
        print(f"Params: {params}")
        
        result = await supabase_manager.execute_query(query, params)
        print(f"✅ Success: {len(result)} braids found")
        for row in result:
            print(f"  - Braid Level: {row.get('braid_level', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_rpc_functions())
