#!/usr/bin/env python3
"""
Test script to verify OVPP token detection with the specific contract address
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.intelligence.social_ingest.social_ingest_basic import SocialIngestModule
from src.utils.supabase_manager import SupabaseManager
from src.intelligence.llm.openrouter_client import OpenRouterClient

async def test_ovpp_verification():
    """Test OVPP token verification with specific contract"""
    
    print("🧪 Testing OVPP Token Verification")
    print("=" * 50)
    
    # Initialize components
    print("🔧 Initializing components...")
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    social_ingest = SocialIngestModule(supabase_manager, llm_client)
    
    print("✅ Components initialized")
    
    # Test token data with the specific contract address
    token_data = {
        'token_name': 'OVPP',
        'contract_address': '0xB4C6fedD984bC983b1a758d0875f1Ea34F81A6af',
        'network': 'ethereum'  # This should be Ethereum based on the contract format
    }
    
    print(f"\n🔍 Testing token verification for:")
    print(f"   Token: {token_data['token_name']}")
    print(f"   Contract: {token_data['contract_address']}")
    print(f"   Network: {token_data['network']}")
    
    # Test the verification
    try:
        result = await social_ingest._verify_token(token_data)
        
        if result:
            print(f"\n✅ Token verification successful!")
            print(f"   Ticker: {result.get('ticker')}")
            print(f"   Name: {result.get('name')}")
            print(f"   Contract: {result.get('contract')}")
            print(f"   Chain: {result.get('chain')}")
            print(f"   Price: ${result.get('price', 0):.6f}")
            print(f"   Volume 24h: ${result.get('volume_24h', 0):,.2f}")
            print(f"   Market Cap: ${result.get('market_cap', 0):,.2f}")
            print(f"   Liquidity: ${result.get('liquidity', 0):,.2f}")
            print(f"   DEX: {result.get('dex')}")
            print(f"   Verified: {result.get('verified')}")
        else:
            print(f"\n❌ Token verification failed - no valid token found")
            
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    print("\n🏁 Test completed")

if __name__ == "__main__":
    asyncio.run(test_ovpp_verification())
