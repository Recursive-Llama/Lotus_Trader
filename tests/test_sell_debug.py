#!/usr/bin/env python3
"""
Debug test for sell functionality - isolate the exact issue
"""

import asyncio
import os
from dotenv import load_dotenv
from trading.evm_uniswap_client import EvmUniswapClient
from trading.wallet_manager import WalletManager

load_dotenv()

async def test_sell_debug():
    print("🔍 Debug Test: Sell Functionality")
    print("=" * 50)
    
    # Initialize Base client
    base_rpc = os.getenv('BASE_RPC_URL', 'https://mainnet.base.org')
    evm_pk = os.getenv('ETHEREUM_WALLET_PRIVATE_KEY') or os.getenv('ETH_WALLET_PRIVATE_KEY')
    
    if not evm_pk:
        print("❌ No private key found")
        return
        
    base_client = EvmUniswapClient(chain='base', rpc_url=base_rpc, private_key=evm_pk)
    
    # Test parameters
    contract = '0x696F9436B67233384889472Cd7cD58A6fB5DF4f1'
    tokens_to_sell = 0.01  # Very small amount
    target_price = 0.0005  # Test price
    
    print(f"Contract: {contract}")
    print(f"Tokens to sell: {tokens_to_sell}")
    print(f"Target price: {target_price} ETH")
    print()
    
    # Step 1: Check if we have tokens
    print("1️⃣ Checking token balance...")
    try:
        # Use wallet manager
        wallet_manager = WalletManager()
        balance = await wallet_manager.get_balance('base', contract)
        balance_float = float(balance) if balance else 0
        print(f"   Token balance: {balance_float:.6f} tokens")
        
        if balance_float == 0:
            print("   ❌ No tokens to sell!")
            return
        elif balance_float < tokens_to_sell:
            print(f"   ⚠️  Not enough tokens (need {tokens_to_sell}, have {balance_float:.6f})")
            tokens_to_sell = balance_float  # Use what we have
            print(f"   📝 Adjusted to sell: {tokens_to_sell} tokens")
    except Exception as e:
        print(f"   ❌ Error checking balance: {e}")
        # Continue anyway - maybe we can still test the swap logic
        print("   ⚠️  Continuing without balance check...")
    
    print()
    
    # Step 2: Get venue (use high liquidity pair)
    print("2️⃣ Getting trading venue...")
    try:
        import requests
        r = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{contract}", timeout=8)
        if r.ok:
            data = r.json()
            pairs = data.get('pairs', [])
            base_pairs = [p for p in pairs if p.get('chainId') == 'base']
            base_pairs.sort(key=lambda p: float(p.get('liquidity', {}).get('usd', 0)), reverse=True)
            
            if base_pairs:
                best_pair = base_pairs[0]
                venue = {
                    'dex': best_pair.get('dexId'),
                    'pair': best_pair.get('pairAddress'),
                    'stable': False
                }
                print(f"   Using pair: {venue['pair']} ({venue['dex']})")
                print(f"   Liquidity: ${best_pair.get('liquidity', {}).get('usd', 0):,.0f}")
            else:
                print("   ❌ No pairs found")
                return
        else:
            print(f"   ❌ DexScreener error: {r.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Error getting venue: {e}")
        return
    
    print()
    
    # Step 3: Test pair quote
    print("3️⃣ Testing pair quote...")
    try:
        tokens_wei = int(tokens_to_sell * 1e18)
        
        # Test both directions
        quote_weth_to_token = base_client.pair_get_amount_out(venue['pair'], tokens_wei, base_client.weth_address)
        quote_token_to_weth = base_client.pair_get_amount_out(venue['pair'], tokens_wei, contract)
        
        print(f"   Quote (WETH→Token): {quote_weth_to_token}")
        print(f"   Quote (Token→WETH): {quote_token_to_weth}")
        
        if quote_token_to_weth and quote_token_to_weth > 0:
            print(f"   ✅ Token→WETH quote successful: {quote_token_to_weth} wei")
            min_out = int(quote_token_to_weth * 0.99)
            print(f"   Min output (1% slippage): {min_out} wei")
        else:
            print(f"   ❌ Token→WETH quote failed")
            return
            
    except Exception as e:
        print(f"   ❌ Error testing quote: {e}")
        return
    
    print()
    
    # Step 4: Test token approval
    print("4️⃣ Testing token approval...")
    try:
        current_allowance = base_client.erc20_allowance(contract, base_client.account.address, venue['pair'])
        print(f"   Current allowance: {current_allowance} wei")
        
        if current_allowance < tokens_wei:
            print(f"   Approving {tokens_wei} wei...")
            approve_res = base_client.approve_erc20(contract, venue['pair'], tokens_wei)
            print(f"   Approval result: {approve_res}")
            
            if approve_res and approve_res.get('status') == 1:
                print(f"   ✅ Approval successful: {approve_res.get('tx_hash')}")
                # Wait for approval
                import time
                time.sleep(3)
            else:
                print(f"   ❌ Approval failed")
                return
        else:
            print(f"   ✅ Already approved")
            
    except Exception as e:
        print(f"   ❌ Error with approval: {e}")
        return
    
    print()
    
    # Step 5: Test direct pair swap
    print("5️⃣ Testing direct pair swap...")
    try:
        print(f"   Calling pair_swap_exact_tokens_for_tokens...")
        print(f"   Pair: {venue['pair']}")
        print(f"   Token in: {contract}")
        print(f"   Token out: {base_client.weth_address}")
        print(f"   Amount in: {tokens_wei}")
        print(f"   Min out: {min_out}")
        
        swap_res = base_client.pair_swap_exact_tokens_for_tokens(
            venue['pair'], 
            contract, 
            base_client.weth_address, 
            tokens_wei, 
            min_out,
            recipient=base_client.account.address
        )
        
        print(f"   Swap result: {swap_res}")
        
        if swap_res and swap_res.get('status') == 1:
            tx_hash = (swap_res.get('swap_tx') or {}).get('tx_hash')
            print(f"   ✅ Direct swap successful: {tx_hash}")
        else:
            print(f"   ❌ Direct swap failed")
            
            # Check transaction receipt for more details
            if swap_res and swap_res.get('tx_hash'):
                try:
                    receipt = base_client.w3.eth.get_transaction_receipt(swap_res['tx_hash'])
                    print(f"   Transaction receipt: {receipt}")
                    print(f"   Gas used: {receipt.gasUsed}")
                    print(f"   Status: {receipt.status}")
                except Exception as e:
                    print(f"   Error getting receipt: {e}")
            
    except Exception as e:
        print(f"   ❌ Error in direct swap: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # Step 6: Test router fallback
    print("6️⃣ Testing router fallback...")
    try:
        print(f"   Calling v2_swap_exact_tokens_for_tokens...")
        
        router_res = base_client.v2_swap_exact_tokens_for_tokens(
            contract,
            base_client.weth_address,
            tokens_wei,
            amount_out_min_wei=0,  # Use 0 like buy logic
            recipient=base_client.account.address,
            deadline_seconds=600,
            stable=False
        )
        
        print(f"   Router result: {router_res}")
        
        if router_res and router_res.get('status') == 1:
            tx_hash = router_res.get('tx_hash')
            print(f"   ✅ Router swap successful: {tx_hash}")
        else:
            print(f"   ❌ Router swap failed")
            
    except Exception as e:
        print(f"   ❌ Error in router swap: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sell_debug())
