#!/usr/bin/env python3
"""
Test Supabase client connection for Alpha Detector Module
Phase 1.1: Database connection using Supabase client
"""

import sys
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_supabase_client():
    """Test Supabase client connection"""
    try:
        # Get environment variables
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        print(f"🔍 Supabase URL: {supabase_url}")
        print(f"🔍 Supabase Key: {'*' * 20 if supabase_key else 'NOT SET'}")
        
        if not supabase_url or not supabase_key:
            print("❌ Missing Supabase URL or Key in environment variables")
            return False
        
        # Create Supabase client
        print("\n🔌 Creating Supabase client...")
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Test connection by querying the AD_strands table
        print("📊 Testing database connection...")
        result = supabase.table('ad_strands').select('*').limit(1).execute()
        
        print("✅ Supabase client connection successful!")
        print(f"📋 Query result: {len(result.data)} rows returned")
        
        # Test inserting a test record
        print("\n🧪 Testing insert operation...")
        test_data = {
            'id': 'test_connection_123',
            'module': 'alpha',
            'kind': 'test',
            'symbol': 'BTC',
            'timeframe': '1m',
            'session_bucket': 'test_session',
            'regime': 'test_regime',
            'tags': ['test', 'connection'],
            'sig_sigma': 0.5,
            'sig_confidence': 0.8,
            'sig_direction': 'long',
            'trading_plan': {'test': 'data'},
            'signal_pack': {'test': 'pack'}
        }
        
        insert_result = supabase.table('ad_strands').insert(test_data).execute()
        print("✅ Insert operation successful!")
        print(f"📋 Inserted record ID: {insert_result.data[0]['id'] if insert_result.data else 'Unknown'}")
        
        # Clean up test record
        print("\n🧹 Cleaning up test record...")
        delete_result = supabase.table('ad_strands').delete().eq('id', 'test_connection_123').execute()
        print("✅ Cleanup successful!")
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase client connection failed: {e}")
        return False

def main():
    print("🧪 Testing Supabase Client Connection")
    print("=" * 50)
    
    success = test_supabase_client()
    
    if success:
        print("\n✅ Phase 1.1: Supabase client connection test PASSED")
        print("🎉 We can now proceed with the Alpha Detector implementation!")
    else:
        print("\n❌ Phase 1.1: Supabase client connection test FAILED")
        print("🔧 Please check your Supabase URL and Key in the .env file")

if __name__ == "__main__":
    main()
