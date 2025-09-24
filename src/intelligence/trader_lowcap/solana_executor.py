from typing import Optional


class SolanaExecutor:
    def __init__(self, js_client):
        self.js = js_client

    async def execute_buy(self, token_mint: str, amount_sol: float) -> Optional[str]:
        try:
            lamports = int(amount_sol * 1e9)
            res = await self.js.execute_jupiter_swap(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint=token_mint,
                amount=lamports,
                slippage_bps=50
            )
            if res.get('success'):
                return res.get('tx_hash') or res.get('signature')
        except Exception:
            return None
        return None

    async def execute_sell(self, token_mint: str, tokens_to_sell: float, target_price_sol: float) -> Optional[str]:
        """Execute a sell order for Solana tokens"""
        try:
            # Convert tokens to lamports (assuming 6 decimals for most SPL tokens)
            tokens_lamports = int(tokens_to_sell * 1e6)
            
            # Calculate minimum SOL output (with 5% slippage)
            min_sol_out = int(tokens_to_sell * target_price_sol * 0.95 * 1e9)
            
            # Execute Jupiter swap: token -> SOL
            res = await self.js.execute_jupiter_swap(
                input_mint=token_mint,
                output_mint="So11111111111111111111111111111111111111112",  # SOL mint
                amount=tokens_lamports,
                slippage_bps=50
            )
            
            if res.get('success'):
                print(f"✅ Solana sell successful: {res.get('tx_hash') or res.get('signature')}")
                return res.get('tx_hash') or res.get('signature')
            
            print(f"❌ Solana sell failed for {token_mint}")
            return None
            
        except Exception as e:
            print(f"Error in Solana execute_sell: {e}")
            return None



