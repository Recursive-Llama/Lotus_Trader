#!/usr/bin/env python3
"""
Test Parameter Order

This test verifies the correct parameter order for RPC functions.
"""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.supabase_manager import SupabaseManager


async def test_parameter_order():
    """Test parameter order in RPC functions"""
    print("🔍 Testing Parameter Order")
    print("=" * 30)
    
    supabase_manager = SupabaseManager()
    
    # Test different parameter orders
    test_cases = [
        {
            'name': 'Correct Order',
            'query': "SELECT * FROM AD_strands WHERE kind = %s AND braid_level > %s",
            'params': ['prediction_review', 1]
        },
        {
            'name': 'Reverse Order',
            'query': "SELECT * FROM AD_strands WHERE braid_level > %s AND kind = %s",
            'params': [1, 'prediction_review']
        },
        {
            'name': 'Single Parameter',
            'query': "SELECT * FROM AD_strands WHERE kind = %s",
            'params': ['prediction_review']
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📊 {test_case['name']}")
        print("-" * 25)
        
        try:
            print(f"Query: {test_case['query']}")
            print(f"Params: {test_case['params']}")
            
            result = await supabase_manager.execute_query(test_case['query'], test_case['params'])
            print(f"✅ Success: {len(result)} rows returned")
            
            if result:
                for row in result[:2]:  # Show first 2 rows
                    print(f"  - ID: {row.get('id', 'N/A')[:8]}..., Braid Level: {row.get('braid_level', 'N/A')}")
            
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_parameter_order())
