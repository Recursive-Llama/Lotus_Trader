#!/usr/bin/env python3
"""
Test script to verify token sorting by volume
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.intelligence.social_ingest.social_ingest_basic import SocialIngestModule
from src.utils.supabase_manager import SupabaseManager

async def test_token_sorting():
    """Test token sorting by volume"""
    
    print("🧪 Testing Token Sorting by Volume")
    print("=" * 50)
    
    # Initialize components
    print("🔧 Initializing components...")
    supabase_manager = SupabaseManager()
    
    # Create a mock social ingest instance to test the sorting method
    class MockSocialIngest:
        def _find_best_dexscreener_match(self, pairs, token_name, network):
            # Copy the method from the actual class
            try:
                if not pairs:
                    return None
                
                # Filter by network if specified
                if network and network != 'solana':
                    filtered_pairs = [p for p in pairs if p.get('chainId', '').lower() == network.lower()]
                    if filtered_pairs:
                        pairs = filtered_pairs
                
                # Filter by minimum volume requirements
                min_volume_requirements = {
                    'solana': 100000,    # $100k on Solana
                    'ethereum': 25000,   # $25k on Ethereum
                    'base': 25000,       # $25k on Base
                    'bsc': 25000,        # $25k on BSC
                }
                
                # Filter pairs by minimum volume
                valid_pairs = []
                for pair in pairs:
                    chain = pair.get('chainId', '').lower()
                    volume_24h = pair.get('volume', {}).get('h24', 0)
                    min_volume = min_volume_requirements.get(chain, 0)
                    
                    if volume_24h >= min_volume:
                        valid_pairs.append(pair)
                
                if not valid_pairs:
                    print(f"No pairs meet minimum volume requirements for {token_name}")
                    return None
                
                # Sort by volume (highest first)
                valid_pairs.sort(key=lambda x: x.get('volume', {}).get('h24', 0), reverse=True)
                
                # Look for exact ticker match first (in volume-sorted list)
                for pair in valid_pairs:
                    if pair.get('baseToken', {}).get('symbol', '').upper() == token_name.upper():
                        return pair
                
                # Look for partial match (in volume-sorted list)
                for pair in valid_pairs:
                    symbol = pair.get('baseToken', {}).get('symbol', '').upper()
                    if token_name.upper() in symbol or symbol in token_name.upper():
                        return pair
                
                # Return highest volume result
                return valid_pairs[0] if valid_pairs else None
                
            except Exception as e:
                print(f"Error finding DexScreener match: {e}")
                return None
    
    mock_ingest = MockSocialIngest()
    
    # Test data - mix of low and high volume OVPP tokens
    test_pairs = [
        {
            "chainId": "solana",
            "baseToken": {"symbol": "OVPP", "address": "BCtKkBR1Nz6MSJzCeYWt35CRkn9JrgudhPwprY6A3QJb"},
            "volume": {"h24": 3.99},
            "priceUsd": "0.09372"
        },
        {
            "chainId": "ethereum", 
            "baseToken": {"symbol": "OVPP", "address": "0xB4C6fedD984bC983b1a758d0875f1Ea34F81A6af"},
            "volume": {"h24": 3895924.55},
            "priceUsd": "0.2430"
        },
        {
            "chainId": "bsc",
            "baseToken": {"symbol": "OVPP", "address": "0xA5f915B24416E46C4Ab7c36f4bbCa7C1195FCc77"},
            "volume": {"h24": 0.46},
            "priceUsd": "0.0000000000000002424"
        }
    ]
    
    print(f"\n🔍 Testing with {len(test_pairs)} OVPP pairs:")
    for i, pair in enumerate(test_pairs):
        print(f"   {i+1}. {pair['chainId']}: ${pair['volume']['h24']:,.2f} volume")
    
    # Test the sorting
    result = mock_ingest._find_best_dexscreener_match(test_pairs, "OVPP", "ethereum")
    
    if result:
        print(f"\n✅ Best match found:")
        print(f"   Chain: {result['chainId']}")
        print(f"   Volume: ${result['volume']['h24']:,.2f}")
        print(f"   Price: ${result['priceUsd']}")
        print(f"   Address: {result['baseToken']['address']}")
    else:
        print(f"\n❌ No valid match found")
    
    print("\n🏁 Test completed")

if __name__ == "__main__":
    asyncio.run(test_token_sorting())
