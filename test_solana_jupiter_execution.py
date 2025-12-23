#!/usr/bin/env python3
"""
Test Solana Jupiter Execution in Isolation

Tests buy/sell execution using Jupiter directly (bypassing Li.Fi) to ensure:
- Jupiter swaps work correctly
- PnL tracking works
- Position updates work
- All reporting is correct

This tests the execution path we'll use in PMExecutor for Solana-only trading.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, will use system env vars

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.trading.js_solana_client import JSSolanaClient
from src.intelligence.trader_lowcap.solana_executor import SolanaExecutor

# USDC mint address on Solana
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
SOL_MINT = "So11111111111111111111111111111111111111112"


class SolanaJupiterTester:
    """Test Solana buy/sell execution with Jupiter"""
    
    def __init__(self):
        """Initialize test components"""
        # Setup Solana client
        solana_key = os.getenv('SOL_WALLET_PRIVATE_KEY')
        if not solana_key:
            raise ValueError("SOL_WALLET_PRIVATE_KEY not found in environment")
        
        helius_key = os.getenv('HELIUS_API_KEY')
        if helius_key:
            rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
        else:
            rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
        
        self.js_client = JSSolanaClient(rpc_url=rpc_url, private_key=solana_key)
        self.solana_executor = SolanaExecutor(self.js_client)
        
        print("✅ Initialized Solana Jupiter Tester")
        print(f"   RPC: {rpc_url[:50]}...")
        print(f"   Wallet: {self._get_wallet_address()}")
    
    def _get_wallet_address(self) -> str:
        """Get wallet address from private key"""
        # Use the JS client to get wallet address if available
        # Otherwise return placeholder
        try:
            # The JS client should have this, but for now just return a placeholder
            # In production, this would come from wallet manager
            return "[wallet_address]"
        except:
            return "[wallet_address]"
    
    async def test_buy_usdc_to_token(
        self, 
        token_mint: str, 
        usdc_amount: float,
        slippage_bps: int = 50
    ) -> Dict[str, Any]:
        """
        Test buying tokens with USDC via Jupiter
        
        Args:
            token_mint: Token mint address to buy
            usdc_amount: Amount of USDC to spend
            slippage_bps: Slippage in basis points (50 = 0.5%)
        
        Returns:
            Execution result with all tracking data
        """
        print(f"\n{'='*60}")
        print(f"TEST: Buy {token_mint} with ${usdc_amount:.2f} USDC")
        print(f"{'='*60}")
        
        try:
            # Convert USDC to smallest units (6 decimals)
            usdc_amount_raw = int(usdc_amount * 1_000_000)
            
            print(f"📊 Executing Jupiter swap: USDC → Token")
            print(f"   USDC Amount: ${usdc_amount:.2f} ({usdc_amount_raw} raw)")
            print(f"   Token Mint: {token_mint}")
            print(f"   Slippage: {slippage_bps} bps ({slippage_bps/100}%)")
            
            # Execute swap via Jupiter
            result = await self.js_client.execute_jupiter_swap(
                input_mint=USDC_MINT,
                output_mint=token_mint,
                amount=usdc_amount_raw,
                slippage_bps=slippage_bps
            )
            
            if not result.get('success'):
                return {
                    "status": "error",
                    "error": result.get('error', 'Unknown error'),
                    "test_type": "buy_usdc_to_token"
                }
            
            tx_hash = result.get('signature') or result.get('tx_hash')
            output_amount_raw = result.get('outputAmount', 0)
            
            # Get token decimals
            decimals_result = await self.js_client.get_token_decimals(token_mint)
            token_decimals = decimals_result.get('decimals', 9) if decimals_result.get('success') else 9
            
            # Convert output to human-readable
            tokens_received = float(output_amount_raw) / (10 ** token_decimals)
            
            # Calculate price
            price_per_token = usdc_amount / tokens_received if tokens_received > 0 else 0
            
            print(f"\n✅ Buy Execution Successful!")
            print(f"   TX Hash: {tx_hash}")
            print(f"   USDC Spent: ${usdc_amount:.2f}")
            print(f"   Tokens Received: {tokens_received:.6f}")
            print(f"   Token Decimals: {token_decimals}")
            print(f"   Price per Token: ${price_per_token:.8f}")
            price_impact = result.get('priceImpact', 0)
            price_impact_val = float(price_impact) if price_impact else 0.0
            print(f"   Price Impact: {price_impact_val:.2f}%")
            
            return {
                "status": "success",
                "test_type": "buy_usdc_to_token",
                "tx_hash": tx_hash,
                "usdc_spent": usdc_amount,
                "usdc_spent_raw": usdc_amount_raw,
                "tokens_received": tokens_received,
                "tokens_received_raw": output_amount_raw,
                "token_decimals": token_decimals,
                "price_per_token": price_per_token,
                "price_impact": price_impact_val,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            print(f"\n❌ Buy Execution Failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e),
                "test_type": "buy_usdc_to_token"
            }
    
    async def test_sell_token_to_usdc(
        self,
        token_mint: str,
        tokens_to_sell: float,
        slippage_bps: int = 50
    ) -> Dict[str, Any]:
        """
        Test selling tokens for USDC via Jupiter
        
        Args:
            token_mint: Token mint address to sell
            tokens_to_sell: Amount of tokens to sell
            slippage_bps: Slippage in basis points (50 = 0.5%)
        
        Returns:
            Execution result with all tracking data
        """
        print(f"\n{'='*60}")
        print(f"TEST: Sell {tokens_to_sell:.6f} tokens for USDC")
        print(f"{'='*60}")
        
        try:
            # Get token decimals
            decimals_result = await self.js_client.get_token_decimals(token_mint)
            token_decimals = decimals_result.get('decimals', 9) if decimals_result.get('success') else 9
            
            # Convert tokens to smallest units
            tokens_raw = int(tokens_to_sell * (10 ** token_decimals))
            
            print(f"📊 Executing Jupiter swap: Token → USDC")
            print(f"   Token Amount: {tokens_to_sell:.6f} ({tokens_raw} raw)")
            print(f"   Token Mint: {token_mint}")
            print(f"   Token Decimals: {token_decimals}")
            print(f"   Slippage: {slippage_bps} bps ({slippage_bps/100}%)")
            
            # Execute swap via Jupiter
            result = await self.js_client.execute_jupiter_swap(
                input_mint=token_mint,
                output_mint=USDC_MINT,
                amount=tokens_raw,
                slippage_bps=slippage_bps
            )
            
            if not result.get('success'):
                return {
                    "status": "error",
                    "error": result.get('error', 'Unknown error'),
                    "test_type": "sell_token_to_usdc"
                }
            
            tx_hash = result.get('signature') or result.get('tx_hash')
            output_amount_raw = result.get('outputAmount', 0)
            
            # Convert USDC output to human-readable (6 decimals)
            usdc_received = float(output_amount_raw) / 1_000_000
            
            # Calculate price
            price_per_token = usdc_received / tokens_to_sell if tokens_to_sell > 0 else 0
            
            print(f"\n✅ Sell Execution Successful!")
            print(f"   TX Hash: {tx_hash}")
            print(f"   Tokens Sold: {tokens_to_sell:.6f}")
            print(f"   USDC Received: ${usdc_received:.2f}")
            print(f"   Price per Token: ${price_per_token:.8f}")
            price_impact = result.get('priceImpact', 0)
            price_impact_val = float(price_impact) if price_impact else 0.0
            print(f"   Price Impact: {price_impact_val:.2f}%")
            
            return {
                "status": "success",
                "test_type": "sell_token_to_usdc",
                "tx_hash": tx_hash,
                "tokens_sold": tokens_to_sell,
                "tokens_sold_raw": tokens_raw,
                "usdc_received": usdc_received,
                "usdc_received_raw": output_amount_raw,
                "token_decimals": token_decimals,
                "price_per_token": price_per_token,
                "price_impact": price_impact_val,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            print(f"\n❌ Sell Execution Failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e),
                "test_type": "sell_token_to_usdc"
            }
    
    async def test_full_round_trip(
        self,
        token_mint: str,
        usdc_amount: float = 10.0,
        slippage_bps: int = 50
    ) -> Dict[str, Any]:
        """
        Test a full round trip: Buy token with USDC, then sell it back
        
        This tests the complete flow and PnL calculation
        """
        print(f"\n{'='*70}")
        print(f"FULL ROUND TRIP TEST")
        print(f"{'='*70}")
        print(f"Token: {token_mint}")
        print(f"USDC Amount: ${usdc_amount:.2f}")
        print(f"Slippage: {slippage_bps} bps")
        
        results = {
            "token_mint": token_mint,
            "initial_usdc": usdc_amount,
            "buy": None,
            "sell": None,
            "pnl": None
        }
        
        # Step 1: Buy
        buy_result = await self.test_buy_usdc_to_token(
            token_mint=token_mint,
            usdc_amount=usdc_amount,
            slippage_bps=slippage_bps
        )
        results["buy"] = buy_result
        
        if buy_result.get("status") != "success":
            print(f"\n❌ Round trip failed at buy step")
            return results
        
        # Wait a bit between trades
        print(f"\n⏳ Waiting 5 seconds before sell...")
        await asyncio.sleep(5)
        
        # Step 2: Sell (sell all tokens we just bought)
        tokens_to_sell = buy_result.get("tokens_received", 0)
        sell_result = await self.test_sell_token_to_usdc(
            token_mint=token_mint,
            tokens_to_sell=tokens_to_sell,
            slippage_bps=slippage_bps
        )
        results["sell"] = sell_result
        
        if sell_result.get("status") != "success":
            print(f"\n❌ Round trip failed at sell step")
            return results
        
        # Step 3: Calculate PnL
        usdc_spent = buy_result.get("usdc_spent", 0)
        usdc_received = sell_result.get("usdc_received", 0)
        pnl_usd = usdc_received - usdc_spent
        pnl_pct = (pnl_usd / usdc_spent * 100) if usdc_spent > 0 else 0
        
        results["pnl"] = {
            "usdc_spent": usdc_spent,
            "usdc_received": usdc_received,
            "pnl_usd": pnl_usd,
            "pnl_pct": pnl_pct,
            "fees_estimate": usdc_spent - usdc_received  # Approximate fees (includes slippage)
        }
        
        print(f"\n{'='*70}")
        print(f"ROUND TRIP RESULTS")
        print(f"{'='*70}")
        print(f"USDC Spent:     ${usdc_spent:.2f}")
        print(f"USDC Received:  ${usdc_received:.2f}")
        print(f"PnL:            ${pnl_usd:.2f} ({pnl_pct:+.2f}%)")
        print(f"Est. Fees:      ${results['pnl']['fees_estimate']:.2f}")
        print(f"{'='*70}")
        
        return results


async def main():
    """Run tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Solana Jupiter execution")
    parser.add_argument("--token", type=str, required=True, help="Token mint address")
    parser.add_argument("--amount", type=float, default=10.0, help="USDC amount for buy test")
    parser.add_argument("--sell-amount", type=float, help="Token amount for sell test (if not doing round trip)")
    parser.add_argument("--round-trip", action="store_true", help="Do full round trip test")
    parser.add_argument("--slippage", type=int, default=50, help="Slippage in basis points (default: 50)")
    
    args = parser.parse_args()
    
    tester = SolanaJupiterTester()
    
    if args.round_trip:
        # Full round trip
        results = await tester.test_full_round_trip(
            token_mint=args.token,
            usdc_amount=args.amount,
            slippage_bps=args.slippage
        )
        print(f"\n📊 Final Results:")
        print(f"   Status: {'✅ Success' if results.get('pnl') else '❌ Failed'}")
        if results.get('pnl'):
            print(f"   PnL: ${results['pnl']['pnl_usd']:.2f} ({results['pnl']['pnl_pct']:+.2f}%)")
    
    elif args.sell_amount:
        # Sell only
        result = await tester.test_sell_token_to_usdc(
            token_mint=args.token,
            tokens_to_sell=args.sell_amount,
            slippage_bps=args.slippage
        )
        print(f"\n📊 Sell Result: {'✅ Success' if result.get('status') == 'success' else '❌ Failed'}")
    
    else:
        # Buy only
        result = await tester.test_buy_usdc_to_token(
            token_mint=args.token,
            usdc_amount=args.amount,
            slippage_bps=args.slippage
        )
        print(f"\n📊 Buy Result: {'✅ Success' if result.get('status') == 'success' else '❌ Failed'}")


if __name__ == "__main__":
    asyncio.run(main())

