#!/usr/bin/env python3
"""
Test script to debug decision strand processing in the learning system
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.intelligence.universal_learning.universal_learning_system import UniversalLearningSystem
from src.utils.supabase_manager import SupabaseManager
from src.intelligence.decision_maker_lowcap.decision_maker_lowcap_simple import DecisionMakerLowcapSimple

async def test_decision_processing():
    """Test decision strand processing with extensive debugging"""
    
    print("🧪 Starting Decision Processing Test")
    print("=" * 50)
    
    # Initialize components
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
    
    # Create a mock decision strand (what Decision Maker would create)
    mock_decision_strand = {
        'id': 'test-decision-123',
        'module': 'decision_maker_lowcap',
        'kind': 'decision_lowcap',
        'symbol': 'TEST',
        'session_bucket': 'test_session',
        'tags': ['approved', 'decision'],
        'target_agent': 'trader_lowcap',
        'sig_confidence': 0.8,
        'sig_direction': 'buy',
        'confidence': 0.8,
        'content': {
            'action': 'approve',
            'allocation_pct': 3.0,
            'curator_score': 0.8,
            'reason': 'Test approval'
        },
        'signal_pack': {
            'token': {
                'ticker': 'TEST',
                'contract': 'test-contract',
                'chain': 'solana'
            },
            'curator': {
                'id': 'test_curator',
                'name': 'Test Curator'
            }
        },
        'module_intelligence': {
            'decision_maker': {
                'curator_score': 0.8,
                'allocation_pct': 3.0
            }
        }
    }
    
    print("\n🧪 Testing Decision Strand Processing")
    print("=" * 50)
    print(f"📝 Mock decision strand: {mock_decision_strand['id']}")
    print(f"📝 Kind: {mock_decision_strand['kind']}")
    print(f"📝 Action: {mock_decision_strand['content']['action']}")
    print(f"📝 Tags: {mock_decision_strand['tags']}")
    
    # Test 1: Direct learning system call
    print("\n🔬 Test 1: Direct Learning System Call")
    print("-" * 30)
    
    try:
        print("🔄 Calling learning_system.process_strand_event() directly...")
        await learning_system.process_strand_event(mock_decision_strand)
        print("✅ Direct call completed")
    except Exception as e:
        print(f"❌ Direct call failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    # Test 2: Check if decision maker callback works
    print("\n🔬 Test 2: Decision Maker Callback")
    print("-" * 30)
    
    try:
        print("🔄 Testing decision maker callback...")
        # Simulate what happens in _create_approval_decision
        if hasattr(decision_maker, 'learning_system') and decision_maker.learning_system:
            print("✅ Learning system reference exists")
            print("🔄 Creating asyncio task...")
            asyncio.create_task(decision_maker.learning_system.process_strand_event(mock_decision_strand))
            print("✅ Task created")
        else:
            print("❌ No learning system reference")
    except Exception as e:
        print(f"❌ Callback test failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    # Test 3: Check learning system's _should_trigger_trader method
    print("\n🔬 Test 3: Trader Trigger Check")
    print("-" * 30)
    
    try:
        print("🔄 Testing _should_trigger_trader method...")
        should_trigger = learning_system._should_trigger_trader(mock_decision_strand)
        print(f"✅ Should trigger trader: {should_trigger}")
        
        # Let's also check what the method is looking for
        print(f"📝 Strand kind: {mock_decision_strand.get('kind')}")
        print(f"📝 Strand action: {mock_decision_strand.get('content', {}).get('action')}")
        print(f"📝 Strand tags: {mock_decision_strand.get('tags', [])}")
        
    except Exception as e:
        print(f"❌ Trader trigger check failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    print("\n🏁 Test completed")

if __name__ == "__main__":
    asyncio.run(test_decision_processing())
