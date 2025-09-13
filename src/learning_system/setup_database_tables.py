"""
Setup Database Tables

Creates the necessary database tables for the learning system.
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


async def setup_database_tables():
    """Setup database tables for the learning system"""
    try:
        logger.info("🗄️  Setting up database tables...")
        
        # Initialize Supabase manager
        supabase_manager = SupabaseManager()
        
        # Read the SQL file
        with open('create_braids_table.sql', 'r') as f:
            sql_content = f.read()
        
        # Execute the SQL
        result = supabase_manager.client.rpc('exec_sql', {'sql': sql_content}).execute()
        
        if result.data:
            logger.info("✅ Database tables created successfully")
            return True
        else:
            logger.error("❌ Failed to create database tables")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error setting up database tables: {e}")
        return False


async def verify_tables():
    """Verify that tables exist"""
    try:
        logger.info("🔍 Verifying database tables...")
        
        supabase_manager = SupabaseManager()
        
        # Check if ad_braids table exists
        try:
            result = supabase_manager.client.table('ad_braids').select('id').limit(1).execute()
            logger.info("✅ ad_braids table exists")
        except Exception as e:
            logger.error(f"❌ ad_braids table does not exist: {e}")
            return False
        
        # Check if ad_strands table exists
        try:
            result = supabase_manager.client.table('ad_strands').select('id').limit(1).execute()
            logger.info("✅ ad_strands table exists")
        except Exception as e:
            logger.error(f"❌ ad_strands table does not exist: {e}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error verifying tables: {e}")
        return False


async def main():
    """Main setup function"""
    logger.info("🚀 Starting database setup...")
    
    # Setup tables
    setup_success = await setup_database_tables()
    if not setup_success:
        logger.error("❌ Database setup failed")
        return False
    
    # Verify tables
    verify_success = await verify_tables()
    if not verify_success:
        logger.error("❌ Table verification failed")
        return False
    
    logger.info("🎉 Database setup completed successfully!")
    return True


if __name__ == "__main__":
    asyncio.run(main())
