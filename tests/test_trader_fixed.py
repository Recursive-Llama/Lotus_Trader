#!/usr/bin/env python3
"""
Test the fixed trader module
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime, timezone

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.supabase_manager import SupabaseManager
from intelligence.trader_lowcap.trader_lowcap_simple import TraderLowcapSimple

async def test_trader_fixed():
    """Test the fixed trader with signal_pack and native token amounts"""
    
    print("🧪 Testing Fixed Trader Module...")
    
    # Initialize database manager
    supabase_manager = SupabaseManager()
    
    # Initialize trader
    trader_config = {
        'book_id': 'social',
        'max_position_size_pct': 2.0,
        'entry_strategy': 'three_entry',
        'exit_strategy': 'staged_exit'
    }
    
    trader = TraderLowcapSimple(supabase_manager, trader_config)
    
    # Use real Jupiter API for BONK price
    # trader._get_current_price = mock_get_current_price  # Removed mock
    print("✅ Trader initialized with real Jupiter price fetching")
    
    # Create a mock decision strand with signal_pack
    decision_strand = {
        "id": str(uuid.uuid4()),
        "module": "decision_maker_lowcap",
        "kind": "decision_lowcap",
        "symbol": "BONK",
        "timeframe": None,
        "session_bucket": "test_20250916_10",
        "regime": None,
        "tags": ["decision", "social_lowcap", "approved", "simple"],
        "target_agent": "trader_lowcap",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "lifecycle_id": None,
        "parent_id": str(uuid.uuid4()),
        "sig_sigma": None,
        "sig_confidence": 0.7,
        "confidence": 0.8,
        "sig_direction": "buy",
        "trading_plan": None,
        "signal_pack": {
            "token": {
                "ticker": "BONK",
                "name": "Bonk",
                "contract": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
                "chain": "solana",
                "price": 0.000034,
                "volume_24h": 100000000.0,
                "market_cap": 2000000000.0,
                "liquidity": 50000000.0,
                "dex": "raydium",
                "verified": True
            },
            "venue": {
                "dex": "raydium",
                "chain": "solana",
                "liq_usd": 50000000.0,
                "vol24h_usd": 100000000.0
            },
            "curator": {
                "id": "test_curator",
                "name": "Test Curator",
                "tags": ["test"],
                "handle": "@test",
                "weight": 0.6,
                "platform": "twitter",
                "priority": "high"
            },
            "trading_signals": {
                "action": "buy",
                "timing": "now",
                "confidence": 0.7
            }
        },
        "content": {
            "source_kind": "social_lowcap",
            "source_strand_id": str(uuid.uuid4()),
            "curator_id": "test_curator",
            "action": "approve",
            "allocation_pct": 2.0,
            "curator_confidence": 0.6,
            "reasoning": "Test approval"
        },
        "status": "active"
    }
    
    print(f"🧪 Created mock decision strand: {decision_strand['id']}")
    print(f"   Symbol: {decision_strand['symbol']}")
    print(f"   Action: {decision_strand['content']['action']}")
    print(f"   Allocation: {decision_strand['content']['allocation_pct']}%")
    print(f"   Signal Pack: {decision_strand['signal_pack']['token']['ticker']} on {decision_strand['signal_pack']['token']['chain']}")
    print(f"   Contract: {decision_strand['signal_pack']['token']['contract']}")
    print(f"   Position ID will be: {decision_strand['signal_pack']['token']['ticker']}_{decision_strand['signal_pack']['token']['chain']}")
    
    # Test trader execution
    try:
        print("\n🧪 Testing trader execution...")
        result = await trader.execute_decision(decision_strand)
        
        if result:
            print(f"✅ Trader execution successful!")
            print(f"   Result: {result}")
        else:
            print("⚠️  Trader execution returned None")
            
    except Exception as e:
        print(f"❌ Trader execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_trader_fixed())
