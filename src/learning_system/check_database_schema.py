"""
Check Database Schema

Check what tables and functions are available in the database.
"""

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁')
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/src')

from Modules.Alpha_Detector.src.utils.supabase_manager import SupabaseManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_database_schema():
    """Check database schema"""
    try:
        logger.info("🔍 Checking database schema...")
        
        supabase_manager = SupabaseManager()
        
        # Check available tables
        try:
            result = supabase_manager.client.table('ad_strands').select('*').limit(1).execute()
            logger.info("✅ ad_strands table exists")
        except Exception as e:
            logger.error(f"❌ ad_strands table error: {e}")
        
        # Check if ad_braids table exists
        try:
            result = supabase_manager.client.table('ad_braids').select('*').limit(1).execute()
            logger.info("✅ ad_braids table exists")
        except Exception as e:
            logger.error(f"❌ ad_braids table does not exist: {e}")
        
        # Try to create a simple test table
        try:
            test_data = {
                'id': 'test_123',
                'test_field': 'test_value'
            }
            
            # Try to insert into a test table
            result = supabase_manager.client.table('test_table').insert(test_data).execute()
            logger.info("✅ test_table exists")
        except Exception as e:
            logger.error(f"❌ test_table does not exist: {e}")
        
        # Check available RPC functions
        try:
            result = supabase_manager.client.rpc('get_schema_info').execute()
            logger.info(f"✅ RPC functions available: {result.data}")
        except Exception as e:
            logger.error(f"❌ RPC functions error: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking database schema: {e}")
        return False


async def main():
    """Main function"""
    await check_database_schema()


if __name__ == "__main__":
    asyncio.run(main())
