#!/usr/bin/env python3
"""
Test script for Gem Bot Monitor

Tests the Gem Bot monitor functionality with real website access.
Uses test mode to monitor the Risky column with 1.2% allocation.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Add src to path for imports
sys.path.append('src')

from utils.supabase_manager import SupabaseManager
from llm_integration.openrouter_client import OpenRouterClient
from intelligence.universal_learning.universal_learning_system import UniversalLearningSystem
from intelligence.social_ingest.gem_bot_monitor import GemBotMonitor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_gem_bot_monitor():
    """Test the Gem Bot monitor functionality with real website"""
    try:
        print("🧪 Testing Gem Bot Monitor with real website...")
        print("📋 Test Configuration:")
        print("   - Column: Risky (left column)")
        print("   - Allocation: 1.2% (test mode)")
        print("   - Strand Kind: gem_bot_risky_test")
        print("   - Auto-approve: Yes")
        print()
        
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        learning_system = UniversalLearningSystem(
            supabase_manager=supabase_manager,
            llm_client=llm_client,
            llm_config=None
        )
        
        # Create monitor in test mode (monitors Risky column with 1.2% allocation)
        monitor = GemBotMonitor(
            supabase_manager=supabase_manager,
            llm_client=llm_client,
            learning_system=learning_system,
            test_mode=True,  # This enables test mode
            columns=['risky']  # Monitor only Risky column
        )
        
        print("🚀 Starting Gem Bot monitor in test mode...")
        print("   - Will monitor Risky column for new tokens")
        print("   - Will create strands with 1.2% allocation (test mode)")
        print("   - Press Ctrl+C to stop")
        print()
        
        # Start monitoring (this will open browser and prompt for login)
        await monitor.start_monitoring(check_interval=10)  # Check every 10 seconds
        
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_strand_creation():
    """Test strand creation without website access"""
    try:
        print("🧪 Testing Gem Bot strand creation...")
        
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        learning_system = UniversalLearningSystem(
            supabase_manager=supabase_manager,
            llm_client=llm_client,
            llm_config=None
        )
        
        # Create monitor in test mode
        monitor = GemBotMonitor(
            supabase_manager=supabase_manager,
            llm_client=llm_client,
            learning_system=learning_system,
            test_mode=True,
            columns=['risky']
        )
        
        # Create test token data (using a real Solana token for Jupiter API)
        token_data = {
            'ticker': 'TESTCOIN',
            'contract': 'So11111111111111111111111111111111111111112',  # Wrapped SOL
            'chain': 'solana',
            'dex': 'Raydium',
            'verified': True,
            'project_name': 'Test Project',
            'multiplier': 3,
            'market_cap': 150000.0,
            'liquidity': 25000.0,
            'transactions': 1500,
            'holders': 300,
            'creator_pct': 2.5,
            'bundled_pct': 8.0,
            'snipers_pct': 15.0,
            'timestamp': datetime.now(timezone.utc).strftime('%I:%M:%S %p')
        }
        
        print(f"🧪 Creating test strand for {token_data['ticker']}...")
        await monitor._create_gem_bot_strand(token_data)
        
        print("✅ Strand creation test completed successfully!")
        
    except Exception as e:
        print(f"❌ Strand creation test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Gem Bot Monitor')
    parser.add_argument('--mode', choices=['full', 'strand'], default='strand',
                       help='Test mode: full (with website) or strand (strand creation only)')
    
    args = parser.parse_args()
    
    if args.mode == 'full':
        asyncio.run(test_gem_bot_monitor())
    else:
        asyncio.run(test_strand_creation())
