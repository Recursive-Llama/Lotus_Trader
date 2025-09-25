#!/usr/bin/env python3
"""
Test script for Discord Gem Bot Monitor
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.supabase_manager import SupabaseManager
from llm_integration.openrouter_client import OpenRouterClient
from intelligence.universal_learning.universal_learning_system import UniversalLearningSystem
from intelligence.social_ingest.discord_gem_bot_monitor import DiscordGemBotMonitor


async def test_discord_gem_bot_monitor():
    """Test Discord Gem Bot Monitor with real Discord"""
    print("🧪 Testing Discord Gem Bot Monitor...")
    print("📋 Test Configuration:")
    print("   - Channel: #gembot-risky-calls")
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
    
    # Create monitor in test mode (monitors Risky channel with 1.2% allocation)
    monitor = DiscordGemBotMonitor(
        supabase_manager=supabase_manager,
        llm_client=llm_client,
        learning_system=learning_system,
        test_mode=True,  # This enables test mode
        channels=['risky']  # Monitor only Risky channel
    )
    
    print("🚀 Starting Discord Gem Bot monitor in test mode...")
    print("   - Will monitor #gembot-risky-calls for new messages")
    print("   - Will create strands with 1.2% allocation (test mode)")
    print("   - Press Ctrl+C to stop")
    print()
    
    try:
        await monitor.start_monitoring(check_interval=10)  # Check every 10 seconds
    except KeyboardInterrupt:
        print("\n👋 Stopping monitor...")
    finally:
        await monitor._cleanup()


async def test_strand_creation():
    """Test strand creation with sample data"""
    print("🧪 Testing Discord Gem Bot strand creation...")
    
    # Initialize components
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    learning_system = UniversalLearningSystem(
        supabase_manager=supabase_manager,
        llm_client=llm_client,
        llm_config=None
    )
    
    # Create monitor in test mode
    monitor = DiscordGemBotMonitor(
        supabase_manager=supabase_manager,
        llm_client=llm_client,
        learning_system=learning_system,
        test_mode=True,
        channels=['risky']
    )
    
    # Create test token data (using a real Solana token for Jupiter API)
    token_data = {
        'ticker': 'TESTCOIN',
        'contract': 'So11111111111111111111111111111111111111112',  # Wrapped SOL
        'market_cap': 100000,
        'liquidity': 50000,
        'transactions': 1000,
        'holders': 500,
        'creator_pct': 2.5,
        'bundle_pct': 4.8,
        'sniped_pct': 6.8,
        'timestamp': '2025-01-20T12:31:00Z'
    }
    
    print("🚀 Creating test strand...")
    await monitor._create_gem_bot_strand(token_data, 'risky')
    print("✅ Test strand creation completed")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Discord Gem Bot Monitor')
    parser.add_argument('--mode', choices=['full', 'strand'], default='full',
                       help='Test mode: full monitoring or just strand creation')
    
    args = parser.parse_args()
    
    if args.mode == 'full':
        await test_discord_gem_bot_monitor()
    elif args.mode == 'strand':
        await test_strand_creation()


if __name__ == "__main__":
    asyncio.run(main())
