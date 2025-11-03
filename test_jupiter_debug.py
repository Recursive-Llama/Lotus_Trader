#!/usr/bin/env python3
"""
Debug Jupiter API directly to understand PUMP token issues
"""

import asyncio
import aiohttp
import json
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('jupiter_debug.log')
    ]
)

logger = logging.getLogger(__name__)

async def test_jupiter_quote():
    """Test Jupiter quote API for PUMP token"""
    
    print("🔬 Testing Jupiter Quote API for PUMP Token")
    print("=" * 50)
    
    pump_mint = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
    sol_mint = "So11111111111111111111111111111111111111112"
    
    # Test different amounts
    test_amounts = [
        1000000,    # 1 token (6 decimals)
        10000000,   # 10 tokens
        100000000,  # 100 tokens
        1000000000  # 1000 tokens
    ]
    
    async with aiohttp.ClientSession() as session:
        for amount in test_amounts:
            print(f"\n🔄 Testing amount: {amount} (raw units)")
            
            try:
                # Get quote from Jupiter
                quote_url = "https://lite-api.jup.ag/swap/v1/quote"
                params = {
                    'inputMint': pump_mint,
                    'outputMint': sol_mint,
                    'amount': str(amount),
                    'slippageBps': '100',  # 1% slippage
                    'onlyDirectRoutes': 'false',
                    'asLegacyTransaction': 'false'
                }
                
                print(f"📡 Requesting quote: {quote_url}")
                print(f"📋 Params: {params}")
                
                async with session.get(quote_url, params=params) as response:
                    print(f"📊 Response status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Quote successful!")
                        print(f"   Input amount: {data.get('inAmount')}")
                        print(f"   Output amount: {data.get('outAmount')}")
                        print(f"   Price impact: {data.get('priceImpactPct')}%")
                        print(f"   Route: {data.get('routePlan', [])}")
                        
                        # Try to get swap transaction
                        await test_jupiter_swap(session, data, pump_mint, sol_mint)
                        
                    else:
                        error_text = await response.text()
                        print(f"❌ Quote failed: {response.status}")
                        print(f"   Error: {error_text}")
                        
            except Exception as e:
                print(f"❌ Error getting quote: {e}")
                logger.exception("Quote error details:")

async def test_jupiter_swap(session, quote_data, input_mint, output_mint):
    """Test Jupiter swap transaction creation"""
    
    print(f"\n🔧 Testing swap transaction creation...")
    
    try:
        swap_url = "https://lite-api.jup.ag/swap/v1/swap"
        
        # Mock user public key (you'd use real one in actual test)
        user_public_key = "8VYRUrQkugXnySsCfq55gXei88HhhimXYfsj7tsBhfyV"
        
        payload = {
            "quoteResponse": quote_data,
            "userPublicKey": user_public_key,
            "wrapAndUnwrapSol": True,
            "useSharedAccounts": False,
            "prioritizationFeeLamports": "auto",
            "asLegacyTransaction": False
        }
        
        print(f"📡 Requesting swap transaction: {swap_url}")
        print(f"📋 User public key: {user_public_key}")
        
        async with session.post(swap_url, json=payload) as response:
            print(f"📊 Swap response status: {response.status}")
            
            if response.status == 200:
                data = await response.json()
                print(f"✅ Swap transaction created successfully!")
                print(f"   Transaction length: {len(data.get('swapTransaction', ''))}")
                print(f"   Has error: {'error' in data}")
                
                if 'error' in data:
                    print(f"   Error: {data['error']}")
                    
            else:
                error_text = await response.text()
                print(f"❌ Swap transaction failed: {response.status}")
                print(f"   Error: {error_text}")
                
    except Exception as e:
        print(f"❌ Error creating swap transaction: {e}")
        logger.exception("Swap error details:")

async def test_other_tokens():
    """Test Jupiter with other working tokens for comparison"""
    
    print(f"\n🔍 Testing other tokens for comparison")
    print("=" * 50)
    
    # Test with a known working token (USDC)
    usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    sol_mint = "So11111111111111111111111111111111111111112"
    
    async with aiohttp.ClientSession() as session:
        try:
            quote_url = "https://lite-api.jup.ag/swap/v1/quote"
            params = {
                'inputMint': usdc_mint,
                'outputMint': sol_mint,
                'amount': '1000000',  # 1 USDC (6 decimals)
                'slippageBps': '100',
                'onlyDirectRoutes': 'false',
                'asLegacyTransaction': 'false'
            }
            
            print(f"🔄 Testing USDC -> SOL quote...")
            
            async with session.get(quote_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ USDC quote successful!")
                    print(f"   Input: {data.get('inAmount')} USDC")
                    print(f"   Output: {data.get('outAmount')} SOL")
                else:
                    error_text = await response.text()
                    print(f"❌ USDC quote failed: {error_text}")
                    
        except Exception as e:
            print(f"❌ Error testing USDC: {e}")

async def main():
    """Run all tests"""
    
    print("🚀 Starting Jupiter Debug Tests")
    print("=" * 60)
    
    await test_jupiter_quote()
    await test_other_tokens()
    
    print("\n🏁 All tests completed. Check jupiter_debug.log for detailed logs.")

if __name__ == "__main__":
    asyncio.run(main())
