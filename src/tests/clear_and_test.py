#!/usr/bin/env python3
"""
Clear Database and Run Detailed Test
"""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.supabase_manager import SupabaseManager


async def clear_database():
    """Clear the database"""
    print("🧹 Clearing Database")
    print("=" * 20)
    
    supabase_manager = SupabaseManager()
    
    # Get count before clearing
    result = supabase_manager.client.table('ad_strands').select('id', count='exact').execute()
    before_count = result.count
    print(f"📊 Strands before clearing: {before_count}")
    
    if before_count == 0:
        print("✅ Database already empty")
        return True
    
    # Clear all strands
    try:
        supabase_manager.client.table('ad_strands').delete().neq('id', 'dummy').execute()
        
        # Verify clearing
        result = supabase_manager.client.table('ad_strands').select('id', count='exact').execute()
        after_count = result.count
        
        print(f"📊 Strands after clearing: {after_count}")
        
        if after_count == 0:
            print("✅ Database cleared successfully!")
            return True
        else:
            print(f"⚠️ Warning: {after_count} strands still remain")
            return False
            
    except Exception as e:
        print(f"❌ Error clearing database: {e}")
        return False


async def main():
    """Main function"""
    # Clear database
    success = await clear_database()
    
    if not success:
        print("❌ Failed to clear database, aborting test")
        return
    
    print("\n" + "=" * 50)
    print("🚀 Running Detailed Learning Test")
    print("=" * 50)
    
    # Import and run the detailed test
    from detailed_learning_test import DetailedLearningTest
    
    test = DetailedLearningTest()
    await test.run_detailed_test()


if __name__ == "__main__":
    asyncio.run(main())
