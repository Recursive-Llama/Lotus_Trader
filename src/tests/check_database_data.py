#!/usr/bin/env python3
"""
Check Database Data

This simple test checks what's actually in the database
to understand the data structure issues.
"""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.supabase_manager import SupabaseManager


async def check_database_data():
    """Check what's actually in the database"""
    print("🔍 Checking Database Data")
    print("=" * 25)
    
    supabase_manager = SupabaseManager()
    
    # Get a few prediction review strands
    result = supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').limit(3).execute()
    
    if not result.data:
        print("❌ No prediction_review strands found")
        return
    
    print(f"✅ Found {len(result.data)} prediction_review strands")
    
    # Check the structure of each strand
    for i, strand in enumerate(result.data):
        print(f"\n📊 Strand {i+1}:")
        print(f"  ID: {strand.get('id', 'N/A')}")
        print(f"  Kind: {strand.get('kind', 'N/A')}")
        print(f"  Content Type: {type(strand.get('content'))}")
        print(f"  Content: {strand.get('content')}")
        print(f"  Module Intelligence: {strand.get('module_intelligence')}")
        print(f"  Cluster Key: {strand.get('cluster_key')}")


if __name__ == "__main__":
    asyncio.run(check_database_data())
