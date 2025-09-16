#!/usr/bin/env python3
"""
Test TraderLowcapSimple in isolation
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

async def test_trader():
    """Test trader with a mock decision strand"""
    
    print("🧪 Testing TraderLowcapSimple in isolation...")
    
    # Initialize database manager
    supabase_manager = SupabaseManager()
    
    # Initialize trader
    trader_config = {
        'book_id': 'social',
        'book_nav': 100000.0,
        'max_position_size_pct': 2.0,
        'entry_strategy': 'three_entry',
        'exit_strategy': 'staged_exit'
    }
    
    trader = TraderLowcapSimple(supabase_manager, trader_config)
    print("✅ Trader initialized")
    
    # Create a mock decision strand (approved)
    decision_strand = {
        "id": str(uuid.uuid4()),
        "module": "decision_maker_lowcap",
        "kind": "decision_lowcap",
        "symbol": "TEST",
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
                "ticker": "TEST",
                "name": "Test Token",
                "contract": "TEST123456789",
                "chain": "solana",
                "price": 0.01,
                "volume_24h": 100000.0,
                "market_cap": 1000000.0,
                "liquidity": 500000.0,
                "dex": "pumpswap",
                "verified": True
            },
            "venue": {
                "dex": "pumpswap",
                "chain": "solana",
                "liq_usd": 500000.0,
                "vol24h_usd": 100000.0
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
            "token": {
                "ticker": "TEST",
                "name": "Test Token",
                "contract": "TEST123456789",
                "chain": "solana",
                "price": 0.01,
                "volume_24h": 100000.0,
                "market_cap": 1000000.0,
                "liquidity": 500000.0,
                "dex": "pumpswap",
                "verified": True
            },
            "venue": {
                "dex": "pumpswap",
                "chain": "solana",
                "liq_usd": 500000.0,
                "vol24h_usd": 100000.0
            },
            "action": "approve",
            "allocation_pct": 2.0,
            "allocation_usd": 2000.0,
            "curator_confidence": 0.6,
            "reasoning": "Test approval"
        },
        "status": "active"
    }
    
    print(f"🧪 Created mock decision strand: {decision_strand['id']}")
    print(f"   Symbol: {decision_strand['symbol']}")
    print(f"   Action: {decision_strand['content']['action']}")
    print(f"   Allocation: {decision_strand['content']['allocation_pct']}%")
    
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
    asyncio.run(test_trader())
