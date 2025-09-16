#!/usr/bin/env python3
"""
Test Decision Maker in isolation
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.supabase_manager import SupabaseManager
from src.intelligence.decision_maker_lowcap.decision_maker_lowcap_simple import DecisionMakerLowcapSimple

async def test_decision_maker():
    """Test Decision Maker with a mock social signal"""
    
    print("🧪 Testing Decision Maker in isolation...")
    
    # Initialize components
    supabase_manager = SupabaseManager()
    decision_maker = DecisionMakerLowcapSimple(supabase_manager)
    
    # Create a mock social signal strand (like the ones being generated)
    mock_social_signal = {
        "id": "test-strand-123",
        "module": "social_ingest",
        "kind": "social_lowcap",
        "symbol": "HYDX",
        "signal_pack": {
            "token": {
                "ticker": "HYDX",
                "name": "Hydrex",
                "contract": "0x00000e7efa313F4E11Bfff432471eD9423AC6B30",
                "chain": "base",
                "price": 0.3057,
                "volume_24h": 41717.84,
                "market_cap": 30238638.0,
                "liquidity": 1260.32,
                "dex": "uniswap",
                "verified": True
            },
            "venue": {
                "dex": "uniswap",
                "chain": "base",
                "liq_usd": 1260.32,
                "vol24h_usd": 41717.84
            },
            "curator": {
                "id": "crypto_popseye",
                "name": "Crypto Popseye",
                "tags": ["degen", "early", "calls", "multi_platform"],
                "handle": "@crypto_popseye_calls",
                "weight": 0.7,
                "platform": "telegram",
                "priority": "medium"
            },
            "trading_signals": {
                "action": "buy",
                "timing": "now",
                "confidence": 0.6
            }
        },
        "content": {
            "summary": "Social signal for HYDX from Crypto Popseye",
            "platform": "telegram",
            "confidence": 0.7,
            "curator_id": "crypto_popseye",
            "token_ticker": "HYDX"
        },
        "sig_confidence": 0.6,
        "sig_direction": "buy",
        "session_bucket": "social_20250916_09",
        "module_intelligence": {
            "social_signal": {
                "message": {
                    "text": "Bought this $hydx Snipers had a lot but seems ok risk reward for second leg up",
                    "timestamp": "2025-09-16T05:34:56+00:00",
                    "url": "https://x.com/crypto_popseye/status/1967824301790515605",
                    "has_image": True,
                    "has_chart": False
                },
                "context_slices": {
                    "liquidity_bucket": "<5k",
                    "volume_bucket": "10-100k",
                    "time_bucket_utc": "6-12",
                    "sentiment": "positive"
                }
            }
        }
    }
    
    print(f"📝 Mock social signal created for {mock_social_signal['signal_pack']['token']['ticker']}")
    print(f"   Curator: {mock_social_signal['signal_pack']['curator']['id']}")
    print(f"   Contract: {mock_social_signal['signal_pack']['token']['contract']}")
    print(f"   Chain: {mock_social_signal['signal_pack']['token']['chain']}")
    
    try:
        print("\n🔄 Calling Decision Maker...")
        
        # Add debug output to see the decision process
        print(f"🔍 Debug - Checking curator performance...")
        curator_score = await decision_maker._get_curator_score('crypto_popseye')
        print(f"   Curator score: {curator_score}")
        
        print(f"🔍 Debug - Checking if already have token...")
        has_token = await decision_maker._already_has_token('0x00000e7efa313F4E11Bfff432471eD9423AC6B30', 'base')
        print(f"   Already have token: {has_token}")
        
        print(f"🔍 Debug - Checking available capital...")
        print(f"   Max exposure: {decision_maker.config['max_exposure_pct']}%")
        print(f"   Max positions: {decision_maker.max_positions}")
        
        result = await decision_maker.make_decision(mock_social_signal)
        
        if result:
            print(f"✅ Decision Maker succeeded!")
            print(f"   Result type: {type(result)}")
            print(f"   Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            if isinstance(result, dict):
                print(f"   Action: {result.get('content', {}).get('action', 'Unknown')}")
                print(f"   Allocation: {result.get('content', {}).get('allocation_pct', 'Unknown')}%")
                print(f"   Reason: {result.get('content', {}).get('reasoning', 'No reason given')}")
        else:
            print("❌ Decision Maker returned None (rejected)")
            
    except Exception as e:
        print(f"❌ Decision Maker failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_decision_maker())
