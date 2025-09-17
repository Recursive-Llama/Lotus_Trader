#!/usr/bin/env python3
"""
Test script to simulate the real pipeline issue
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.intelligence.universal_learning.universal_learning_system import UniversalLearningSystem
from src.utils.supabase_manager import SupabaseManager
from src.intelligence.decision_maker_lowcap.decision_maker_lowcap_simple import DecisionMakerLowcapSimple

async def test_real_pipeline():
    """Test the real pipeline issue"""
    
    print("🧪 Testing Real Pipeline Issue")
    print("=" * 50)
    
    # Initialize components exactly like the real system
    print("🔧 Initializing components...")
    supabase_manager = SupabaseManager()
    learning_system = UniversalLearningSystem(supabase_manager)
    
    # Initialize Decision Maker with learning system reference
    decision_maker = DecisionMakerLowcapSimple(
        supabase_manager=supabase_manager,
        config={
            'book_id': 'social',
            'min_curator_score': 0.6,
            'max_exposure_pct': 100.0,
            'max_positions': 30,
            'min_allocation_pct': 1.0,
            'default_allocation_pct': 3.0,
            'ignore_tokens': ['SOL', 'ETH', 'BTC', 'USDC', 'USDT', 'WETH'],
            'min_volume_requirements': {
                'solana': 100000,
                'ethereum': 25000,
                'base': 25000,
            }
        },
        learning_system=learning_system
    )
    
    print("✅ Components initialized")
    
    # Create a mock social signal (like what comes from social ingest)
    mock_social_signal = {
        'id': 'test-social-123',
        'module': 'social_ingest',
        'kind': 'social_lowcap',
        'symbol': 'PUMP',
        'session_bucket': 'test_session',
        'tags': ['curated', 'social_signal', 'dm_candidate', 'verified'],
        'sig_confidence': 0.8,
        'sig_direction': 'buy',
        'confidence': 0.8,
        'signal_pack': {
        'token': {
            'ticker': 'PUMP',
            'contract': 'pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn',  # Real PUMP contract
            'chain': 'solana',
            'price': 0.1,
            'volume_24h': 500000,  # High volume to get approved (5x minimum)
            'market_cap': 1000000,
            'liquidity': 500000,
            'dex': 'jupiter',
            'verified': True
        },
        'venue': {
            'dex': 'jupiter',
            'chain': 'solana',
            'liq_usd': 500000,
            'vol24h_usd': 500000
        },
            'curator': {
                'id': '0xdetweiler',
                'name': '0xDetweiler',
                'weight': 0.8
            },
            'trading_signals': {
                'action': 'buy',
                'timing': None,
                'confidence': 0.8
            }
        }
    }
    
    print(f"\n🔍 Testing Decision Maker with mock signal...")
    print(f"   Token: {mock_social_signal['signal_pack']['token']['ticker']}")
    print(f"   Volume: ${mock_social_signal['signal_pack']['venue']['vol24h_usd']:,.0f}")
    print(f"   Chain: {mock_social_signal['signal_pack']['token']['chain']}")
    print(f"   Curator: {mock_social_signal['signal_pack']['curator']['id']}")
    
    # Test the decision maker
    try:
        print(f"\n🔄 Calling decision_maker.make_decision()...")
        decision = await decision_maker.make_decision(mock_social_signal)
        
        if decision:
            action = decision.get('content', {}).get('action')
            print(f"\n📋 Decision created: {decision.get('id')}")
            print(f"   Action: {action}")
            print(f"   Tags: {decision.get('tags')}")
            
            if action == 'reject':
                reason = decision.get('content', {}).get('reasoning', 'No reason given')
                print(f"   ❌ REJECTION REASON: {reason}")
            else:
                print(f"   ✅ APPROVED")
            
            # Check if the decision was processed by learning system
            print(f"\n🔍 Checking if decision was processed...")
            
            # Wait a moment for any async tasks to complete
            await asyncio.sleep(2)
            
            # Check if any trader strands were created
            trader_result = supabase_manager.client.table('ad_strands').select('*').eq('parent_id', decision.get('id')).execute()
            print(f"   Trader strands found: {len(trader_result.data)}")
            
            if trader_result.data:
                for trader_strand in trader_result.data:
                    print(f"     - {trader_strand.get('kind')}: {trader_strand.get('content', {}).get('status')}")
            else:
                print("     ❌ No trader strands - decision not processed!")
                
        else:
            print(f"\n❌ Decision was rejected (no decision object returned)")
            
    except Exception as e:
        print(f"\n❌ Error in decision making: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    print("\n🏁 Test completed")

if __name__ == "__main__":
    asyncio.run(test_real_pipeline())
