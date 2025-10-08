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

    async def execute_sell(self, token_mint: str, tokens_to_sell: float, target_price_sol: float) -> Optional[dict]:
        """Execute a sell order for Solana tokens"""
        try:
            # Detect Token-2022 to adjust slippage for transfer-fee (tax) tokens
            is_token2022 = False
            try:
                program_info = await self.js.get_mint_program_id(token_mint)
                owner = (program_info or {}).get('owner')
                if owner == 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb':
                    is_token2022 = True
            except Exception:
                pass
            default_slippage_bps = 50
            sell_slippage_bps = 250 if is_token2022 else default_slippage_bps
            
            # Get token decimals dynamically
            decimals_result = await self.js.get_token_decimals(token_mint)
            decimals = 9  # Default fallback
            if decimals_result.get('success'):
                decimals = decimals_result.get('decimals', 9)
            
            # Convert tokens to smallest units using actual decimals
            tokens_smallest_units = int(tokens_to_sell * (10 ** decimals))
            
            # Calculate minimum SOL output (with 5% slippage)
            min_sol_out = int(tokens_to_sell * target_price_sol * 0.95 * 1e9)
            
            # Execute Jupiter swap: token -> SOL (initial attempt)
            res = await self.js.execute_jupiter_swap(
                input_mint=token_mint,
                output_mint="So11111111111111111111111111111111111111112",  # SOL mint
                amount=tokens_smallest_units,
                slippage_bps=sell_slippage_bps
            )
            
            if res.get('success'):
                tx_hash = res.get('tx_hash') or res.get('signature')
                output_amount = res.get('outputAmount', 0)
                # Convert from lamports to SOL (9 decimals)
                actual_sol_received = float(output_amount) / 1_000_000_000
                print(f"✅ Solana sell successful: {tx_hash}, received {actual_sol_received:.6f} SOL")
                return {
                    'tx_hash': tx_hash,
                    'actual_sol_received': actual_sol_received
                }
            
            # Retry once with higher slippage if simulation failed
            err = res.get('error', '') if isinstance(res, dict) else ''
            if 'Simulation failed' in err or 'custom program error' in err:
                retry_slippage_bps = max(sell_slippage_bps, 300)
                res2 = await self.js.execute_jupiter_swap(
                    input_mint=token_mint,
                    output_mint="So11111111111111111111111111111111111111112",
                    amount=tokens_smallest_units,
                    slippage_bps=retry_slippage_bps
                )
                if res2.get('success'):
                    tx_hash = res2.get('tx_hash') or res2.get('signature')
                    output_amount = res2.get('outputAmount', 0)
                    # Convert from lamports to SOL (9 decimals)
                    actual_sol_received = float(output_amount) / 1_000_000_000
                    print(f"✅ Solana sell successful on retry: {tx_hash}, received {actual_sol_received:.6f} SOL")
                    return {
                        'tx_hash': tx_hash,
                        'actual_sol_received': actual_sol_received
                    }

            print(f"❌ Solana sell failed for {token_mint}")
            print(f"Error details: {res.get('error', 'No error details available')}")
            return None
            
        except Exception as e:
            print(f"Error in Solana execute_sell: {e}")
            return None



