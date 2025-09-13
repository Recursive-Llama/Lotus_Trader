"""
Create Braids Table - Simple Approach

Creates the ad_braids table directly using Supabase client.
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


async def create_braids_table():
    """Create the ad_braids table"""
    try:
        logger.info("🗄️  Creating ad_braids table...")
        
        # Initialize Supabase manager
        supabase_manager = SupabaseManager()
        
        # Create table using raw SQL
        sql = """
        CREATE TABLE IF NOT EXISTS public.ad_braids (
            id TEXT PRIMARY KEY,
            level INTEGER NOT NULL DEFAULT 1,
            strand_type TEXT NOT NULL,
            strand_ids TEXT[] NOT NULL,
            resonance_score FLOAT NOT NULL,
            cluster_size INTEGER NOT NULL,
            cluster_metadata JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
        
        # Execute SQL
        result = supabase_manager.client.rpc('exec_sql', {'sql': sql}).execute()
        
        if result.data:
            logger.info("✅ ad_braids table created successfully")
            return True
        else:
            logger.error("❌ Failed to create ad_braids table")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error creating ad_braids table: {e}")
        return False


async def test_braids_table():
    """Test the braids table"""
    try:
        logger.info("🧪 Testing ad_braids table...")
        
        supabase_manager = SupabaseManager()
        
        # Try to insert a test braid
        test_braid = {
            'id': 'test_braid_123',
            'level': 1,
            'strand_type': 'pattern',
            'strand_ids': ['strand_1', 'strand_2'],
            'resonance_score': 0.85,
            'cluster_size': 2,
            'cluster_metadata': {'test': True}
        }
        
        result = supabase_manager.client.table('ad_braids').insert(test_braid).execute()
        
        if result.data:
            logger.info("✅ Test braid inserted successfully")
            
            # Clean up test data
            supabase_manager.client.table('ad_braids').delete().eq('id', 'test_braid_123').execute()
            logger.info("✅ Test braid cleaned up")
            
            return True
        else:
            logger.error("❌ Failed to insert test braid")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error testing ad_braids table: {e}")
        return False


async def main():
    """Main function"""
    logger.info("🚀 Creating ad_braids table...")
    
    # Create table
    create_success = await create_braids_table()
    if not create_success:
        logger.error("❌ Table creation failed")
        return False
    
    # Test table
    test_success = await test_braids_table()
    if not test_success:
        logger.error("❌ Table test failed")
        return False
    
    logger.info("🎉 ad_braids table setup completed successfully!")
    return True


if __name__ == "__main__":
    asyncio.run(main())
