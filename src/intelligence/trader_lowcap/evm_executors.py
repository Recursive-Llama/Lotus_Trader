from typing import Optional, Dict, Any
import time
import requests


class BaseEvmExecutor:
    """Base class for all EVM chain executors with shared functionality"""
    
    def __init__(self, client, chain_name: str, position_repository=None):
        self.client = client
        self.chain_name = chain_name
        self.gas_multiplier = 1.2
        self.max_retries = 3
        self._pair_cache: Dict[str, Dict[str, Any]] = {}
        self.position_repository = position_repository

    def _wait_for_transaction(self, tx_hash: str, timeout: int = 60) -> bool:
        """Wait for transaction to be mined"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                receipt = self.client.w3.eth.get_transaction_receipt(tx_hash)
                return receipt.status == 1
            except:
                time.sleep(2)
        return False

    def _execute_with_retry(self, func, *args, **kwargs):
        """Execute a function with retry logic for transaction failures"""
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                if result and result.get('status') == 1:
                    return result
                elif result and result.get('status') == 0:
                    print(f"Transaction failed (attempt {attempt + 1}): {result}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
            except Exception as e:
                print(f"Transaction error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
        return None

    def _wrap_native_token(self, amount: float) -> bool:
        """Wrap native token to wrapped version (to be overridden by subclasses)"""
        return False

    def _get_wrapped_token_address(self) -> str:
        """Get the wrapped token address for this chain (to be overridden by subclasses)"""
        return ""

    def _get_position_tax(self, token_address: str) -> float:
        """Get tax percentage for a token from the positions table"""
        try:
            if self.position_repository:
                position = self.position_repository.get_position_by_token(token_address)
                if position and 'tax_pct' in position:
                    return float(position['tax_pct'])
            return 0.0
        except Exception:
            return 0.0

    def _detect_tax_percentage(self, token_address: str, amount: float) -> float:
        """Detect tax percentage by comparing expected vs actual tokens received"""
        try:
            # Get quote for expected tokens
            amounts = self.client.v2_get_amounts_out('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', token_address, int(amount * 1e18))
            if amounts and len(amounts) >= 2:
                expected_tokens = amounts[1] / 1e18
                
                # Get actual tokens received (this would need wallet balance checking)
                # For now, return 0 - this would need proper implementation
                return 0.0
            return 0.0
        except Exception:
            return 0.0

    def _update_position_tax(self, token_address: str, tax_pct: float) -> None:
        """Update position with tax percentage"""
        try:
            if self.position_repository:
                success = self.position_repository.update_tax_percentage(token_address, tax_pct)
                if success:
                    print(f"✅ Updated position tax: {token_address} = {tax_pct}%")
                else:
                    print(f"❌ Failed to update position tax: {token_address} = {tax_pct}%")
            else:
                print(f"⚠️ No position repository available, would update: {token_address} = {tax_pct}%")
        except Exception as e:
            print(f"Error updating position tax: {e}")

    def _is_taxed_token(self, token_address: str, amount_wei: int) -> bool:
        """Check if a token has taxes by looking up in positions table"""
        tax_pct = self._get_position_tax(token_address)
        return tax_pct > 0

    def execute_buy(self, token_address: str, amount: float, venue: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Execute a buy order (to be overridden by subclasses)"""
        return None

    def execute_sell(self, token_address: str, tokens_to_sell: float, target_price: float) -> Optional[str]:
        """Execute a sell order (to be overridden by subclasses)"""
        return None


class BscExecutor(BaseEvmExecutor):
    """BSC-specific executor"""
    
    def __init__(self, bsc_client, position_repository=None):
        super().__init__(bsc_client, "BSC", position_repository)
        self.wrapped_token = "WBNB"

    def _get_wrapped_token_address(self) -> str:
        return self.client.weth_address

    def _wrap_native_token(self, amount: float) -> bool:
        """Wrap BNB to WBNB"""
        wrap_res = self._execute_with_retry(self.client.wrap_eth, amount)
        return wrap_res and wrap_res.get('status') == 1

    def _resolve_venue(self, token_address: str) -> Optional[Dict[str, Any]]:
        """BSC venue resolution - simple V2 pairs"""
        if token_address in self._pair_cache:
            return self._pair_cache[token_address]
        
        # For BSC, we'll use a simple approach - just return None to use router
        return None

    def execute_buy(self, token_address: str, amount_bnb: float, venue: Optional[Dict[str, Any]] = None) -> Optional[str]:
        amount_wei = int(amount_bnb * 1e18)
        
        # Wrap BNB to WBNB
        if not self._wrap_native_token(amount_bnb):
            print(f"❌ WBNB wrapping failed")
            return None
        
        # Try direct pair if venue provided
        if venue and venue.get('pair'):
            try:
                out = self.client.pair_get_amount_out(venue['pair'], amount_wei, self.client.weth_address)
                if out and out > 0:
                    min_out = int(out * 0.99)
                    res_pair = self.client.pair_swap_exact_tokens_for_tokens(
                        venue['pair'], self.client.weth_address, token_address, amount_wei, min_out, 
                        recipient=self.client.account.address
                    )
                    if res_pair.get('status') == 1:
                        return (res_pair.get('swap_tx') or {}).get('tx_hash')
            except Exception as e:
                print(f"Direct pair swap error: {e}")
        
        # Router fallback - wait for approval confirmation
        print(f"Approving WBNB for V3 router: {amount_wei} wei")
        approve_res = self.client.approve_erc20(self.client.weth_address, self.client.router_contract.address, amount_wei)
        if not approve_res or approve_res.get('status') != 1:
            print(f"❌ WBNB approval failed: {approve_res}")
            return None
        
        print(f"✅ WBNB approved: {approve_res.get('tx_hash')}")
        
        # Wait for approval to be confirmed
        import time
        time.sleep(3)  # Wait for approval to be mined
        
        # For BSC, use V3 router (STBL/WBNB is on PancakeSwap V3)
        print("Using V3 router for BSC...")
        
        # Try V3 with different fee tiers
        if self.client.router_contract:
            print("Trying V3 swaps...")
            for fee in [10000, 3000, 500, 2500]:  # Try 1% first for STBL pair
                print(f"Trying V3 swap with fee {fee}...")
                res_v3 = self.client.swap_exact_input_single(
                    self.client.weth_address, token_address, amount_wei, fee=fee, amount_out_min=0
                )
                print(f"V3 swap result: {res_v3}")
                if res_v3.get('status') == 1:
                    print(f"✅ V3 swap successful: {res_v3.get('tx_hash')}")
                    return res_v3.get('tx_hash')
        
        print("❌ V3 swap failed")
        
        # Fallback: try PancakeSwap V2 single-hop (WBNB -> token)
        try:
            if hasattr(self.client, 'v2_router') and self.client.v2_router:
                # Ensure approval for V2 router
                try:
                    current_allowance = self.client.erc20_allowance(self.client.weth_address, self.client.account.address, self.client.v2_router.address)
                    if current_allowance < amount_wei:
                        print(f"Approving WBNB for V2 router: {amount_wei} wei")
                        approve_res_v2 = self.client.approve_erc20(self.client.weth_address, self.client.v2_router.address, amount_wei)
                        if not approve_res_v2 or approve_res_v2.get('status') != 1:
                            print(f"❌ WBNB V2 approval failed: {approve_res_v2}")
                            return None
                        print(f"✅ WBNB V2 approved: {approve_res_v2.get('tx_hash')}")
                        import time as _t
                        _t.sleep(3)
                except Exception as e:
                    print(f"V2 approval error: {e}")
                    return None

                # Get quote for sane minOut
                amounts = self.client.v2_get_amounts_out(self.client.weth_address, token_address, amount_wei)
                min_out = 0
                if amounts and len(amounts) >= 2 and amounts[1] and int(amounts[1]) > 0:
                    # 1% slippage buffer
                    min_out = int(int(amounts[1]) * 0.99)
                
                print(f"Trying V2 swap... min_out={min_out}")
                swap_v2 = self.client.v2_swap_exact_tokens_for_tokens(
                    self.client.weth_address,
                    token_address,
                    amount_wei,
                    amount_out_min_wei=min_out,
                    recipient=self.client.account.address,
                    deadline_seconds=600
                )
                if swap_v2 and swap_v2.get('status') == 1:
                    print(f"✅ V2 swap successful: {swap_v2.get('tx_hash')}")
                    return swap_v2.get('tx_hash')
                print(f"❌ V2 swap failed: {swap_v2}")
        except Exception as e:
            print(f"V2 fallback error: {e}")

        return None

    def execute_sell(self, token_address: str, tokens_to_sell: float, target_price_bnb: float) -> Optional[str]:
        """Execute a sell order for BSC tokens"""
        try:
            tokens_wei = int(tokens_to_sell * 1e18)
            # Don't use target_price_bnb for slippage - it's often wrong
            # We'll calculate min_bnb_out from the actual quote instead
            
            # First try PancakeSwap V3 direct single-hop (token -> WBNB)
            try:
                if self.client.router_contract:
                    # Approve token for V3 router if needed
                    current_allowance = self.client.erc20_allowance(token_address, self.client.account.address, self.client.router_contract.address)
                    if current_allowance < tokens_wei:
                        print(f"Approving token for V3 router: {tokens_wei} wei")
                        approve_res = self.client.approve_erc20(token_address, self.client.router_contract.address, tokens_wei)
                        if not approve_res or approve_res.get('status') != 1:
                            print(f"❌ Token V3 approval failed: {approve_res}")
                            # continue to v2 fallback
                        else:
                            print(f"✅ Token V3 approved: {approve_res.get('tx_hash')}")
                            import time as _t
                            _t.sleep(3)
                    print("Trying V3 sells...")
                    for fee in [10000, 3000, 500, 2500]:
                        try:
                            print(f"Trying V3 sell with fee {fee}...")
                            res_v3 = self.client.swap_exact_input_single(
                                token_address, self.client.weth_address, tokens_wei,
                                fee=fee, amount_out_min=0
                            )
                            print(f"V3 sell result: {res_v3}")
                            if res_v3 and res_v3.get('status') == 1:
                                print(f"✅ V3 sell successful: {res_v3.get('tx_hash')}")
                                return res_v3.get('tx_hash')
                        except Exception as ve:
                            print(f"V3 sell error (fee={fee}): {ve}")
            except Exception as e:
                print(f"V3 pre-sell setup error: {e}")
            
            # Approve token for V2 router first
            try:
                if hasattr(self.client, 'v2_router'):
                    current_allowance = self.client.erc20_allowance(token_address, self.client.account.address, self.client.v2_router.address)
                    if current_allowance < tokens_wei:
                        print(f"Approving token for V2 router: {tokens_wei} wei")
                        approve_res = self.client.approve_erc20(token_address, self.client.v2_router.address, tokens_wei)
                        if not approve_res or approve_res.get('status') != 1:
                            print(f"❌ Token approval failed: {approve_res}")
                            return None
                        print(f"✅ Token approved: {approve_res.get('tx_hash')}")
                        time.sleep(3)  # Wait for approval to be mined
            except Exception as e:
                print(f"Token approval error: {e}")
            
            # Get quote first for proper slippage calculation
            amounts = self.client.v2_get_amounts_out(token_address, self.client.weth_address, tokens_wei)
            if amounts and len(amounts) >= 2:
                expected_out = amounts[1]
                # Account for potential token taxes (4%) + slippage (5%) = 9% total
                min_bnb_out = int(expected_out * 0.91)  # 9% slippage to account for taxes
            else:
                # Fallback to target price calculation if quote fails
                min_bnb_out = int(tokens_to_sell * target_price_bnb * 0.91 * 1e18)
            
            # Use v2 router for selling
            swap_res = self.client.v2_swap_exact_tokens_for_tokens(
                token_address, self.client.weth_address, tokens_wei,
                amount_out_min_wei=min_bnb_out, recipient=self.client.account.address,
                deadline_seconds=600
            )
            
            if swap_res and swap_res.get('tx_hash'):
                print(f"✅ BSC sell successful: {swap_res['tx_hash']}")
                return swap_res['tx_hash']
            
            print(f"❌ BSC sell failed for {token_address}")
            return None
            
        except Exception as e:
            print(f"Error in BSC execute_sell: {e}")
            return None

    async def swap_native_to_usdc(self, bnb_amount: float, slippage_pct: float = 2.0) -> Dict[str, Any]:
        """Convert BNB to USDC (like Lotus buyback)"""
        try:
            # USDC contract on BSC
            usdc_contract = "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"
            
            # Wrap BNB to WBNB first
            if not self._wrap_native_token(bnb_amount):
                return {'success': False, 'error': 'Failed to wrap BNB to WBNB'}
            
            amount_wei = int(bnb_amount * 1e18)
            
            # Approve WBNB for router
            approve_res = self.client.approve_erc20(
                self.client.weth_address, 
                self.client.router_contract.address, 
                amount_wei
            )
            if not approve_res or approve_res.get('status') != 1:
                return {'success': False, 'error': f'WBNB approval failed: {approve_res}'}
            
            import time
            time.sleep(3)  # Wait for approval
            
            # Try V3 swap (WBNB -> USDC)
            for fee in [10000, 3000, 500, 2500]:
                try:
                    res_v3 = self.client.swap_exact_input_single(
                        self.client.weth_address, 
                        usdc_contract, 
                        amount_wei,
                        fee=fee, 
                        amount_out_min=0
                    )
                    if res_v3 and res_v3.get('status') == 1:
                        # Get USDC balance after swap
                        usdc_balance = self.client.erc20_balance(usdc_contract, self.client.account.address)
                        usdc_received = float(usdc_balance) / 1e18  # USDC has 18 decimals on BSC
                        
                        return {
                            'success': True,
                            'tx_hash': res_v3.get('tx_hash'),
                            'usdc_received': usdc_received,
                            'bnb_amount': bnb_amount
                        }
                except Exception as e:
                    print(f"V3 USDC swap error (fee={fee}): {e}")
                    continue
            
            # Fallback to V2
            if hasattr(self.client, 'v2_router') and self.client.v2_router:
                try:
                    # Approve WBNB for V2 router
                    approve_res_v2 = self.client.approve_erc20(
                        self.client.weth_address, 
                        self.client.v2_router.address, 
                        amount_wei
                    )
                    if approve_res_v2 and approve_res_v2.get('status') == 1:
                        time.sleep(3)
                        
                        # Get quote for minOut
                        amounts = self.client.v2_get_amounts_out(
                            self.client.weth_address, 
                            usdc_contract, 
                            amount_wei
                        )
                        min_out = 0
                        if amounts and len(amounts) >= 2 and amounts[1]:
                            min_out = int(int(amounts[1]) * (100 - slippage_pct) / 100)
                        
                        swap_v2 = self.client.v2_swap_exact_tokens_for_tokens(
                            self.client.weth_address,
                            usdc_contract,
                            amount_wei,
                            amount_out_min_wei=min_out,
                            recipient=self.client.account.address,
                            deadline_seconds=600
                        )
                        
                        if swap_v2 and swap_v2.get('status') == 1:
                            # Get USDC balance after swap
                            usdc_balance = self.client.erc20_balance(usdc_contract, self.client.account.address)
                            usdc_received = float(usdc_balance) / 1e18
                            
                            return {
                                'success': True,
                                'tx_hash': swap_v2.get('tx_hash'),
                                'usdc_received': usdc_received,
                                'bnb_amount': bnb_amount
                            }
                except Exception as e:
                    print(f"V2 USDC swap error: {e}")
            
            return {'success': False, 'error': 'All swap methods failed'}
            
        except Exception as e:
            return {'success': False, 'error': f'USDC conversion error: {e}'}


class BaseExecutor(BaseEvmExecutor):
    """Base network-specific executor with Aerodrome and V3 support"""
    
    def __init__(self, base_client, position_repository=None):
        super().__init__(base_client, "Base", position_repository)
        self.wrapped_token = "WETH"

    def _get_wrapped_token_address(self) -> str:
        return self.client.weth_address

    def _wrap_native_token(self, amount: float) -> bool:
        """Wrap ETH to WETH"""
        wrap_res = self._execute_with_retry(self.client.wrap_eth, amount)
        if wrap_res and wrap_res.get('status') == 1:
            print(f"✅ BASE wrap successful: {wrap_res.get('tx_hash')}")
            time.sleep(3)  # Wait for transaction to be mined
            return True
        print(f"❌ WETH wrapping failed: {wrap_res}")
        return False

    # Note: Solidly/V2 detection is performed opportunistically by probing getAmountOut in swap path

    def _try_uniswap_v3_multihop(self, token_address: str, amount_wei: int) -> Optional[str]:
        """Try Uniswap v3 multi-hop WETH -> USDC -> TOKEN with fee search and simulation."""
        weth = self.client.weth_address
        usdc = self.client.usdc_address
        # Approve WETH for router if needed
        v3_router = self.client.router_address
        current_allowance = self.client.erc20_allowance(weth, self.client.account.address, v3_router)
        if current_allowance < amount_wei:
            print(f"Approving WETH for V3 router (multihop): {amount_wei} wei")
            approve_res = self.client.approve_erc20(weth, v3_router, amount_wei)
            if not approve_res or approve_res.get('status') != 1:
                print(f"❌ WETH approval failed: {approve_res}")
                return None
            print(f"✅ WETH approved: {approve_res.get('tx_hash')}")
            time.sleep(3)

        fee_tiers = [3000, 500, 10000]
        for fee_a in fee_tiers:
            for fee_b in fee_tiers:
                try:
                    path = self.client.v3_build_path([weth, usdc, token_address], [fee_a, fee_b])
                    quote = self.client.v3_quote_exact_input(path, amount_wei)
                    if not quote or quote <= 0:
                        continue
                    # simulate
                    ok = self.client.simulate_v3_exact_input(path, amount_wei, 0)
                    if not ok:
                        continue
                    # execute
                    res = self.client.v3_exact_input(path, amount_wei, 0, recipient=self.client.account.address)
                    if res and res.get('status') == 1:
                        txh = res.get('tx_hash')
                        print(f"✅ Base Uniswap V3 multihop buy executed (fees={fee_a},{fee_b}): {txh}")
                        return txh
                    else:
                        print(f"❌ V3 multihop failed (fees={fee_a},{fee_b}): {res}")
                except Exception as e:
                    print(f"V3 multihop error (fees={fee_a},{fee_b}): {e}")
        return None

    def _resolve_venue(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Resolve the best WETH pair by liquidity across all DEXs for Base"""
        if token_address in self._pair_cache:
            return self._pair_cache[token_address]
        
        try:
            print(f"Base: Fetching DexScreener data for {token_address}")
            ds = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}", timeout=8)
            print(f"Base: DexScreener response: {ds.ok}")
            if ds.ok:
                data = ds.json() or {}
                pairs = data.get('pairs') or []
                print(f"Base: Found {len(pairs)} total pairs")
                base_pairs = [p for p in pairs if p.get('chainId') == 'base']
                print(f"Base: Found {len(base_pairs)} Base pairs")
                
                # Get all WETH pairs across all DEXs and sort by liquidity
                weth_pairs = [p for p in base_pairs if p.get('quoteToken',{}).get('symbol') == 'WETH']
                print(f"Base: Found {len(weth_pairs)} WETH pairs")
                if weth_pairs:
                    weth_pairs.sort(key=lambda p: (p.get('liquidity',{}).get('usd') or 0), reverse=True)
                    chosen = weth_pairs[0]
                    pair_addr = chosen['pairAddress']
                    dex_type = chosen.get('dexId')
                    print(f"Base: Chosen pair: {dex_type} - {pair_addr}")
                    
                    # Check if it's a V2-style pair (Aerodrome V2 or Uniswap V2)
                    stable = None
                    if dex_type == 'aerodrome':
                        stable = self.client.pair_is_stable(pair_addr)
                    
                    venue = {
                        'dex': dex_type,
                        'pair': pair_addr,
                        'stable': bool(stable) if stable is not None else False
                    }
                    print(f"Base: Created venue: {venue}")
                    self._pair_cache[token_address] = venue
                    return venue
                else:
                    print("Base: No WETH pairs found")
            else:
                print(f"Base: DexScreener request failed: {ds.status_code}")
        except Exception as ds_err:
            print(f"Base: DexScreener resolution failed: {ds_err}")
            import traceback
            traceback.print_exc()
        
        return None

    def _try_uniswap_v3_swap(self, token_address: str, amount_wei: int, is_buy: bool = True) -> Optional[str]:
        """Try Uniswap V3 swap"""
        v3_router = '0x2626664c2603336E57B271c5C0b26F421741e481'
        
        if is_buy:
            # Approve WETH for V3 router
            current_allowance = self.client.erc20_allowance(self.client.weth_address, self.client.account.address, v3_router)
            if current_allowance < amount_wei:
                print(f"Approving WETH for V3 router: {amount_wei} wei")
                approve_res = self.client.approve_erc20(self.client.weth_address, v3_router, amount_wei)
                if not approve_res or approve_res.get('status') != 1:
                    print(f"❌ WETH approval failed: {approve_res}")
                    return None
                print(f"✅ WETH approved: {approve_res.get('tx_hash')}")
                time.sleep(3)
        else:
            # Approve token for V3 router
            current_allowance = self.client.erc20_allowance(token_address, self.client.account.address, v3_router)
            if current_allowance < amount_wei:
                print(f"Approving token for V3 router: {amount_wei} wei")
                approve_res = self.client.approve_erc20(token_address, v3_router, amount_wei)
                if not approve_res or approve_res.get('status') != 1:
                    print(f"❌ Token approval failed: {approve_res}")
                    return None
                print(f"✅ Token approved: {approve_res.get('tx_hash')}")
                time.sleep(3)
        
        for fee in [500, 3000, 10000]:
            try:
                if is_buy:
                    # Single attempt per fee tier (no retry on status=0)
                    swap_res = self.client.swap_exact_input_single(self.client.weth_address, token_address, amount_wei, fee=fee, amount_out_min=0)
                else:
                    swap_res = self.client.swap_exact_input_single(token_address, self.client.weth_address, amount_wei, fee=fee, amount_out_min=0)
                
                if swap_res and swap_res.get('status') == 1:
                    tx_hash = swap_res.get('tx_hash')
                    print(f"✅ Base Uniswap V3 {'buy' if is_buy else 'sell'} executed (fee={fee}): {tx_hash}")
                    return tx_hash
                else:
                    print(f"❌ Base Uniswap V3 {'buy' if is_buy else 'sell'} failed (fee={fee}): {swap_res}")
            except Exception as e:
                print(f"Uniswap v3 {'buy' if is_buy else 'sell'} error (fee={fee}): {e}")
        
        # Try multihop if buys failed
        if is_buy:
            return self._try_uniswap_v3_multihop(token_address, amount_wei)
        return None

    def _try_aerodrome_swap(self, token_address: str, amount_wei: int, is_buy: bool = True, venue: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Try Aerodrome direct pair swap (V2 and Solidly)"""
        if not venue:
            venue = self._resolve_venue(token_address)
        if not venue or venue.get('dex') != 'aerodrome' or not venue.get('pair'):
            return None
        
        pair_address = venue['pair']
        
        # Approve WETH for Aerodrome pair
        if is_buy:
            current_allowance = self.client.erc20_allowance(self.client.weth_address, self.client.account.address, pair_address)
            if current_allowance < amount_wei:
                print(f"Approving WETH for Aerodrome pair: {amount_wei} wei")
                approve_res = self.client.approve_erc20(self.client.weth_address, pair_address, amount_wei)
                if not approve_res or approve_res.get('status') != 1:
                    print(f"❌ WETH approval failed: {approve_res}")
                    return None
                print(f"✅ WETH approved: {approve_res.get('tx_hash')}")
                # Wait longer for approval to be mined to avoid nonce conflicts
                time.sleep(5)
        else:
            # Approve token for Aerodrome pair
            current_allowance = self.client.erc20_allowance(token_address, self.client.account.address, pair_address)
            if current_allowance < amount_wei:
                print(f"Approving token for Aerodrome pair: {amount_wei} wei")
                approve_res = self.client.approve_erc20(token_address, pair_address, amount_wei)
                if not approve_res or approve_res.get('status') != 1:
                    print(f"❌ Token approval failed: {approve_res}")
                    return None
                print(f"✅ Token approved: {approve_res.get('tx_hash')}")
                # Wait longer for approval to be mined to avoid nonce conflicts
                time.sleep(5)
        
        # Try direct pair swap (works for both V2 and Solidly Aerodrome pairs)
        try:
            if is_buy:
                # Tiny probe first (0.001 ETH) to confirm path viability
                probe_amount = int(10**15)  # 0.001 ETH in wei
                probe_out = self.client.pair_get_amount_out(pair_address, probe_amount, self.client.weth_address)
                if probe_out and probe_out > 0:
                    expected_out = self.client.pair_get_amount_out(pair_address, amount_wei, self.client.weth_address)
                    if expected_out and expected_out > 0:
                        min_out = int(expected_out * 0.99)
                    else:
                        # Scale from probe with extra buffer
                        scaled = int(probe_out * (amount_wei / probe_amount)) if probe_amount > 0 else 0
                        min_out = int(scaled * 0.97) if scaled > 0 else 0
                    if min_out and min_out > 0:
                        # clamp min_out to at least 1 wei
                        min_out = max(1, min_out)
                        swap_res = self.client.pair_swap_exact_tokens_for_tokens(
                            pair_address, self.client.weth_address, token_address, amount_wei, min_out,
                            recipient=self.client.account.address
                        )
                        if swap_res and swap_res.get('status') == 1:
                            tx_hash = (swap_res.get('swap_tx') or {}).get('tx_hash')
                            print(f"✅ Base direct pair {'buy' if is_buy else 'sell'} executed: {tx_hash}")
                            return tx_hash
                else:
                    print("Aerodrome probe (0.001 ETH) returned None/0; skipping direct-pair path")
            else:
                probe_amount = int(10**15)
                probe_out = self.client.pair_get_amount_out(pair_address, probe_amount, token_address)
                if probe_out and probe_out > 0:
                    expected_out = self.client.pair_get_amount_out(pair_address, amount_wei, token_address)
                    if expected_out and expected_out > 0:
                        min_out = int(expected_out * 0.99)
                    else:
                        scaled = int(probe_out * (amount_wei / probe_amount)) if probe_amount > 0 else 0
                        min_out = int(scaled * 0.97) if scaled > 0 else 0
                    if min_out and min_out > 0:
                        min_out = max(1, min_out)
                        swap_res = self.client.pair_swap_exact_tokens_for_tokens(
                            pair_address, token_address, self.client.weth_address, amount_wei, min_out,
                            recipient=self.client.account.address
                        )
                        if swap_res and swap_res.get('status') == 1:
                            tx_hash = (swap_res.get('swap_tx') or {}).get('tx_hash')
                            print(f"✅ Base direct pair {'buy' if is_buy else 'sell'} executed: {tx_hash}")
                            return tx_hash
                else:
                    print("Aerodrome probe (0.001 ETH) returned None/0; skipping direct-pair path")
        except Exception as e:
            print(f"Direct pair {'buy' if is_buy else 'sell'} error: {e}")
        
        return None

    def _find_uniswap_v2_venue(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Find highest liquidity Uniswap V2 pair for token"""
        try:
            print(f"Base: Finding Uniswap V2 pairs for {token_address}")
            ds = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}", timeout=8)
            if ds.ok:
                data = ds.json() or {}
                pairs = data.get('pairs') or []
                base_pairs = [p for p in pairs if p.get('chainId') == 'base']
                
                # Get all Uniswap V2 pairs with WETH
                uniswap_v2_pairs = [p for p in base_pairs if p.get('dexId') == 'uniswap' and p.get('quoteToken',{}).get('symbol') == 'WETH']
                
                if uniswap_v2_pairs:
                    # Sort by liquidity and get the best one
                    uniswap_v2_pairs.sort(key=lambda p: (p.get('liquidity',{}).get('usd') or 0), reverse=True)
                    chosen = uniswap_v2_pairs[0]
                    pair_addr = chosen['pairAddress']
                    print(f"Base: Found Uniswap V2 pair: {pair_addr} (liquidity: ${chosen.get('liquidity',{}).get('usd', 0):,})")
                    
                    venue = {
                        'dex': 'uniswap_v2',
                        'pair': pair_addr,
                        'stable': False
                    }
                    return venue
                else:
                    print("Base: No Uniswap V2 WETH pairs found")
            else:
                print(f"Base: DexScreener request failed: {ds.status_code}")
        except Exception as e:
            print(f"Base: Error finding Uniswap V2 venue: {e}")
        
        return None

    def _try_uniswap_v2_direct_pair_swap(self, token_address: str, amount_wei: int, venue: Dict[str, Any]) -> Optional[str]:
        """Try Uniswap V2 direct pair swap using existing pair_swap_exact_tokens_for_tokens method"""
        if not venue or venue.get('dex') != 'uniswap_v2' or not venue.get('pair'):
            return None
        
        pair_address = venue['pair']
        
        # Approve WETH for Uniswap V2 pair
        current_allowance = self.client.erc20_allowance(self.client.weth_address, self.client.account.address, pair_address)
        if current_allowance < amount_wei:
            print(f"Approving WETH for Uniswap V2 pair: {amount_wei} wei")
            approve_res = self.client.approve_erc20(self.client.weth_address, pair_address, amount_wei)
            if not approve_res or approve_res.get('status') != 1:
                print(f"❌ WETH approval failed: {approve_res}")
                return None
            print(f"✅ WETH approved: {approve_res.get('tx_hash')}")
            time.sleep(3)
        
        # Try direct pair swap (reuse existing method)
        try:
            expected_out = self.client.pair_get_amount_out(pair_address, amount_wei, self.client.weth_address)
            if expected_out and expected_out > 0:
                min_out = int(expected_out * 0.99)
                swap_res = self.client.pair_swap_exact_tokens_for_tokens(
                    pair_address, self.client.weth_address, token_address, amount_wei, min_out,
                    recipient=self.client.account.address
                )
                if swap_res and swap_res.get('status') == 1:
                    tx_hash = (swap_res.get('swap_tx') or {}).get('tx_hash')
                    print(f"✅ Base Uniswap V2 direct pair buy executed: {tx_hash}")
                    return tx_hash
            else:
                print("❌ Uniswap V2 pair_get_amount_out failed")
        except Exception as e:
            print(f"Uniswap V2 direct pair swap error: {e}")
        
        return None

    def execute_buy(self, token_address: str, amount_eth: float, venue: Optional[Dict[str, Any]] = None) -> Optional[str]:
        amount_wei = int(amount_eth * 1e18)
        
        # Increase gas headroom for Base
        self.client.gas_limit_default = max(self.client.gas_limit_default, 300000)
        
        # Wrap ETH to WETH
        if not self._wrap_native_token(amount_eth):
            return None
        
        # Resolve venue if not provided
        if not venue:
            venue = self._resolve_venue(token_address)
        
        print(f"BASE venue: {venue}")
        
        # Try appropriate swap method based on DEX type
        if venue and venue.get('dex') == 'uniswap':
            return self._try_uniswap_v3_swap(token_address, amount_wei, is_buy=True)
        elif venue and venue.get('dex') == 'aerodrome':
            result = self._try_aerodrome_swap(token_address, amount_wei, is_buy=True, venue=venue)
            if result:
                return result
            else:
                # Fallback: try Uniswap V2 direct pair swap
                print("Aerodrome failed, trying Uniswap V2 direct pair...")
                uniswap_v2_venue = self._find_uniswap_v2_venue(token_address)
                if uniswap_v2_venue:
                    v2_result = self._try_uniswap_v2_direct_pair_swap(token_address, amount_wei, uniswap_v2_venue)
                    if v2_result:
                        return v2_result
                
                # Final fallback: try Uniswap V3
                print("Uniswap V2 failed or not found, trying Uniswap V3...")
                return self._try_uniswap_v3_swap(token_address, amount_wei, is_buy=True)
        
        print(f"❌ No suitable venue found for Base trade: {token_address}")
        return None

    def execute_sell(self, token_address: str, tokens_to_sell: float, target_price_eth: float) -> Optional[str]:
        """Execute a sell order for Base tokens"""
        try:
            tokens_wei = int(tokens_to_sell * 1e18)
            
            # Increase gas headroom for Base
            self.client.gas_limit_default = max(self.client.gas_limit_default, 300000)
            
            # Resolve venue for selling
            venue = self._resolve_venue(token_address)
            print(f"BASE sell venue: {venue}")
            
            # Try appropriate sell method based on DEX type
            if venue and venue.get('dex') == 'uniswap':
                return self._try_uniswap_v3_swap(token_address, tokens_wei, is_buy=False)
            elif venue and venue.get('dex') == 'aerodrome':
                return self._try_aerodrome_swap(token_address, tokens_wei, is_buy=False, venue=venue)
            
            print(f"❌ No suitable venue found for Base sell: {token_address}")
            return None
            
        except Exception as e:
            print(f"Error in execute_sell: {e}")
            return None

    async def swap_native_to_usdc(self, eth_amount: float, slippage_pct: float = 2.0) -> Dict[str, Any]:
        """Convert ETH to USDC (like Lotus buyback)"""
        try:
            # USDC contract on Base
            usdc_contract = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
            
            # Wrap ETH to WETH first
            if not self._wrap_native_token(eth_amount):
                return {'success': False, 'error': 'Failed to wrap ETH to WETH'}
            
            amount_wei = int(eth_amount * 1e18)
            
            # Approve WETH for router
            approve_res = self.client.approve_erc20(
                self.client.weth_address, 
                self.client.router_contract.address, 
                amount_wei
            )
            if not approve_res or approve_res.get('status') != 1:
                return {'success': False, 'error': f'WETH approval failed: {approve_res}'}
            
            import time
            time.sleep(3)  # Wait for approval
            
            # Try V3 swap (WETH -> USDC)
            for fee in [10000, 3000, 500, 2500]:
                try:
                    res_v3 = self.client.swap_exact_input_single(
                        self.client.weth_address, 
                        usdc_contract, 
                        amount_wei,
                        fee=fee, 
                        amount_out_min=0
                    )
                    if res_v3 and res_v3.get('status') == 1:
                        # Get USDC balance after swap
                        usdc_balance = self.client.erc20_balance(usdc_contract, self.client.account.address)
                        usdc_received = float(usdc_balance) / 1e6  # USDC has 6 decimals on Base
                        
                        return {
                            'success': True,
                            'tx_hash': res_v3.get('tx_hash'),
                            'usdc_received': usdc_received,
                            'eth_amount': eth_amount
                        }
                except Exception as e:
                    print(f"V3 USDC swap error (fee={fee}): {e}")
                    continue
            
            # Fallback to V2
            if hasattr(self.client, 'v2_router') and self.client.v2_router:
                try:
                    # Approve WETH for V2 router
                    approve_res_v2 = self.client.approve_erc20(
                        self.client.weth_address, 
                        self.client.v2_router.address, 
                        amount_wei
                    )
                    if approve_res_v2 and approve_res_v2.get('status') == 1:
                        time.sleep(3)
                        
                        # Get quote for minOut
                        amounts = self.client.v2_get_amounts_out(
                            self.client.weth_address, 
                            usdc_contract, 
                            amount_wei
                        )
                        min_out = 0
                        if amounts and len(amounts) >= 2 and amounts[1]:
                            min_out = int(int(amounts[1]) * (100 - slippage_pct) / 100)
                        
                        swap_v2 = self.client.v2_swap_exact_tokens_for_tokens(
                            self.client.weth_address,
                            usdc_contract,
                            amount_wei,
                            amount_out_min_wei=min_out,
                            recipient=self.client.account.address,
                            deadline_seconds=600
                        )
                        
                        if swap_v2 and swap_v2.get('status') == 1:
                            # Get USDC balance after swap
                            usdc_balance = self.client.erc20_balance(usdc_contract, self.client.account.address)
                            usdc_received = float(usdc_balance) / 1e6  # USDC has 6 decimals on Base
                            
                            return {
                                'success': True,
                                'tx_hash': swap_v2.get('tx_hash'),
                                'usdc_received': usdc_received,
                                'eth_amount': eth_amount
                            }
                except Exception as e:
                    print(f"V2 USDC swap error: {e}")
            
            return {'success': False, 'error': 'All swap methods failed'}
            
        except Exception as e:
            return {'success': False, 'error': f'USDC conversion error: {e}'}


class EthExecutor(BaseEvmExecutor):
    """Ethereum-specific executor"""
    
    def __init__(self, eth_client, position_repository=None):
        super().__init__(eth_client, "Ethereum", position_repository)
        self.wrapped_token = "WETH"
        # One-shot on Ethereum
        self.max_retries = 1

    def _get_wrapped_token_address(self) -> str:
        return '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'

    def _wrap_native_token(self, amount: float) -> bool:
        """Wrap ETH to WETH"""
        wrap_res = self._execute_with_retry(self.client.wrap_eth, amount)
        return wrap_res and wrap_res.get('status') == 1

    def _resolve_venue(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Resolve the best WETH pair by liquidity across all DEXs"""
        if token_address in self._pair_cache:
            return self._pair_cache[token_address]
        
        try:
            print(f"ETH: Fetching DexScreener data for {token_address}")
            ds = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}", timeout=8)
            print(f"ETH: DexScreener response: {ds.ok}")
            if ds.ok:
                data = ds.json() or {}
                pairs = data.get('pairs') or []
                print(f"ETH: Found {len(pairs)} total pairs")
                eth_pairs = [p for p in pairs if p.get('chainId') == 'ethereum']
                print(f"ETH: Found {len(eth_pairs)} Ethereum pairs")
                
                # Get all WETH pairs across all DEXs and sort by liquidity
                weth_pairs = [p for p in eth_pairs if p.get('quoteToken',{}).get('symbol') == 'WETH']
                print(f"ETH: Found {len(weth_pairs)} WETH pairs")
                if weth_pairs:
                    weth_pairs.sort(key=lambda p: (p.get('liquidity',{}).get('usd') or 0), reverse=True)
                    chosen = weth_pairs[0]
                    pair_addr = chosen['pairAddress']
                    dex_type = chosen.get('dexId')
                    print(f"ETH: Chosen pair: {dex_type} - {pair_addr}")
                    
                    # Check if it's a V2-style pair (Aerodrome V2 or Uniswap V2)
                    stable = None
                    if dex_type == 'aerodrome':
                        stable = self.client.pair_is_stable(pair_addr)
                    
                    venue = {
                        'dex': dex_type,
                        'pair': pair_addr,
                        'stable': bool(stable) if stable is not None else False
                    }
                    print(f"ETH: Created venue: {venue}")
                    self._pair_cache[token_address] = venue
                    return venue
                else:
                    print("ETH: No WETH pairs found")
            else:
                print(f"ETH: DexScreener request failed: {ds.status_code}")
        except Exception as ds_err:
            print(f"ETH: DexScreener resolution failed: {ds_err}")
            import traceback
            traceback.print_exc()
        
        return None

    def execute_buy(self, token_address: str, amount_eth: float, venue: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Execute buy for Ethereum token
        
        Args:
            token_address: Token contract address
            amount_eth: Amount of ETH to spend
            venue: Optional venue information (if not provided, will be resolved)
            
        Returns:
            Transaction hash if successful, None otherwise
        """
        try:
            print(f"ETH: Executing buy for {token_address}")
            print(f"ETH: Spending {amount_eth} ETH")
            
            amount_wei = int(amount_eth * 1e18)
            
            # Resolve venue before wrapping; fallback to Uniswap if not resolvable
            if not venue:
                venue = self._resolve_venue(token_address)
            # Pre-route check: must have some venue
            if not venue:
                # Default to Uniswap if resolution failed
                venue = {'dex': 'uniswap'}
                print(f"ETH: Venue resolution failed; defaulting to Uniswap router")

            # If even default cannot provide route (no pair known), abort early
            if not venue:
                print(f"❌ ETH: No viable venue/route for {token_address}")
                return None

            # Only wrap when we are about to trade; do minimal precheck
            # Check ETH balance sufficient for wrap + gas before attempting
            try:
                balance_wei = int(self.client.w3.eth.get_balance(self.client.account.address))
                gas_price = int(self.client.w3.eth.gas_price)
                gas_limit = 70000
                needed_wei = int(amount_eth * 1e18) + gas_price * gas_limit
                if balance_wei < needed_wei:
                    print(f"❌ ETH: Insufficient funds for wrap: have {balance_wei}, need {needed_wei}")
                    return None
            except Exception:
                # If precheck fails, proceed to single attempt
                pass

            if not self._wrap_native_token(amount_eth):
                print(f"❌ ETH: WETH wrapping failed")
                return None
            
            print(f"ETH: Using venue: {venue}")
            
            # Smart routing: quote all routes, pick best, execute with fallback
            if venue.get('dex') == 'uniswap':
                print(f"ETH: Using smart routing...")
                result = self._smart_routing_swap(token_address, amount_wei)
                if result:
                    return result
            
            # Try other DEX types (SushiSwap, etc.)
            elif venue.get('dex') in ['sushiswap', 'shibaswap']:
                print(f"ETH: Trying {venue.get('dex')} swap...")
                result = self._try_uniswap_v2_swap_simple(token_address, amount_wei)
                if result:
                    return result
            
            print(f"❌ ETH: All swap methods failed for {token_address}")
            return None
            
        except Exception as e:
            print(f"❌ ETH: Buy execution error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _smart_routing_swap(self, token_address: str, amount_wei: int) -> Optional[str]:
        """Smart routing: quote all routes, pick best, execute with fallback"""
        try:
            print(f"ETH: Smart routing for {token_address}")
            weth = self._get_wrapped_token_address()
            
            # Step 1: Quote all available routes
            routes = []
            
            # V2 quote
            v2_quote = self.client.v2_get_amounts_out(weth, token_address, amount_wei)
            if v2_quote and len(v2_quote) >= 2 and v2_quote[1]:
                routes.append({
                    'type': 'V2',
                    'router': self.client.v2_router,
                    'fee': None,
                    'amount_out': int(v2_quote[1]),
                    'priority': 1  # Highest priority (cheapest)
                })
                print(f"ETH: V2 quote: {int(v2_quote[1])} tokens")
            
            # Classic V3 quotes
            for fee in [3000, 10000, 500, 2500]:
                quote = self.client.v3_quote_amount_out(weth, token_address, amount_wei, fee=fee)
                if quote and quote > 0:
                    routes.append({
                        'type': 'Classic V3',
                        'router': self.client.v3_router,
                        'fee': fee,
                        'amount_out': quote,
                        'priority': 2  # Second priority (reliable for V3)
                    })
                    print(f"ETH: Classic V3 fee {fee} quote: {quote} tokens")
            
            # SwapRouter02 quotes
            for fee in [3000, 10000, 500, 2500]:
                quote = self.client.v3_quote_amount_out(weth, token_address, amount_wei, fee=fee)
                if quote and quote > 0:
                    routes.append({
                        'type': 'SwapRouter02',
                        'router': self.client.router,
                        'fee': fee,
                        'amount_out': quote,
                        'priority': 3  # Third priority (unreliable for simple swaps)
                    })
                    print(f"ETH: SwapRouter02 fee {fee} quote: {quote} tokens")
            
            if not routes:
                print(f"❌ ETH: No viable routes found")
                return None
            
            # Step 2: Sort by priority, then by amount_out (descending)
            routes.sort(key=lambda x: (x['priority'], -x['amount_out']))
            print(f"ETH: Found {len(routes)} viable routes, trying in order...")
            
            # Step 3: Try to execute routes in order
            for i, route in enumerate(routes):
                print(f"ETH: Attempt {i+1}: {route['type']} fee {route['fee']}")
                
                try:
                    # Approve WETH for the router
                    current_allowance = self.client.erc20_allowance(weth, self.client.account.address, route['router'].address)
                    if current_allowance < amount_wei:
                        # Approve more than needed to account for fees/rounding
                        approval_amount = amount_wei * 2
                        print(f"ETH: Approving WETH for {route['type']}: {approval_amount} wei")
                        approve_res = self.client.approve_erc20(weth, route['router'].address, approval_amount)
                        if not approve_res or approve_res.get('status') != 1:
                            print(f"ETH: {route['type']} approval failed: {approve_res}")
                            continue
                        print(f"ETH: {route['type']} approved: {approve_res.get('tx_hash')}")
                        import time
                        time.sleep(3)  # Wait for approval
                    
                    # Calculate min_out with proper fee accounting and slippage
                    if route['type'] == 'V2':
                        # V2 doesn't have fees, just slippage
                        min_out = int(route['amount_out'] * 0.98)  # 2% slippage
                    else:
                        # V3 has fees (0.3% for 3000, 0.05% for 500, 1% for 10000)
                        fee_rate = 0.997 if route['fee'] == 3000 else (0.9995 if route['fee'] == 500 else 0.99)
                        expected_after_fee = int(route['amount_out'] * fee_rate)
                        min_out = int(expected_after_fee * 0.98)  # 2% slippage after fee
                    
                    # Execute swap
                    if route['type'] == 'V2':
                        result = self.client.v2_swap_exact_tokens_for_tokens(
                            token_in=weth,
                            token_out=token_address,
                            amount_in_wei=amount_wei,
                            amount_out_min_wei=min_out,
                            recipient=self.client.account.address,
                            deadline_seconds=600
                        )
                    elif route['type'] == 'SwapRouter02':
                        result = self.client.swap_exact_input_single(
                            token_in=weth,
                            token_out=token_address,
                            amount_in_wei=amount_wei,
                            fee=route['fee'],
                            amount_out_min=min_out,
                            recipient=self.client.account.address,
                            deadline_seconds=600
                        )
                    elif route['type'] == 'Classic V3':
                        result = self.client.v3_swap_exact_input_single(
                            token_in=weth,
                            token_out=token_address,
                            amount_in_wei=amount_wei,
                            fee=route['fee'],
                            amount_out_min=min_out,
                            recipient=self.client.account.address,
                            deadline_seconds=600
                        )
                    
                    if result and result.get('status') == 1:
                        print(f"✅ ETH: {route['type']} swap successful: {result.get('tx_hash')}")
                        print(f"ETH: Gas used: {result.get('gas_used', 'unknown')}")
                        return result.get('tx_hash')
                    else:
                        print(f"❌ ETH: {route['type']} swap failed: {result}")
                        
                except Exception as e:
                    print(f"❌ ETH: {route['type']} swap error: {e}")
                    continue
            
            print(f"❌ ETH: All smart routing attempts failed")
            return None
            
        except Exception as e:
            print(f"❌ ETH: Smart routing error: {e}")
            return None

    def _smart_routing_sell(self, token_address: str, amount_wei: int) -> Optional[str]:
        """Smart routing for sells: token -> WETH using proper router flow"""
        try:
            print(f"ETH: Smart routing sell for {token_address}")
            weth = self._get_wrapped_token_address()
            is_tax_known = False
            try:
                is_tax_known = self._is_taxed_token(token_address, amount_wei)
            except Exception:
                is_tax_known = False
            
            # Step 1: Quote all available routes (token -> WETH)
            routes = []
            
            # V2 quote (token -> WETH)
            v2_quote = self.client.v2_get_amounts_out(token_address, weth, amount_wei)
            if v2_quote and len(v2_quote) >= 2 and v2_quote[1]:
                routes.append({
                    'type': 'V2',
                    'router': self.client.v2_router,
                    'fee': None,
                    'amount_out': int(v2_quote[1]),
                    'priority': 1  # Highest priority (most reliable)
                })
                print(f"ETH: V2 sell quote: {int(v2_quote[1]) / 10**18:.6f} WETH")
            
            # Only include V3/Router02 routes when token is NOT known tax token
            if not is_tax_known:
                # SwapRouter02 quotes (token -> WETH)
                for fee in [3000, 10000, 500, 2500]:
                    quote = self.client.v3_quote_amount_out(token_address, weth, amount_wei, fee=fee)
                    if quote and quote > 0:
                        routes.append({
                            'type': 'SwapRouter02',
                            'router': self.client.router,
                            'fee': fee,
                            'amount_out': quote,
                            'priority': 2  # Second priority (less reliable)
                        })
                        print(f"ETH: SwapRouter02 fee {fee} sell quote: {quote / 10**18:.6f} WETH")
                
                # Classic V3 quotes (token -> WETH)
                for fee in [3000, 10000, 500, 2500]:
                    quote = self.client.v3_quote_amount_out(token_address, weth, amount_wei, fee=fee)
                    if quote and quote > 0:
                        routes.append({
                            'type': 'Classic V3',
                            'router': self.client.v3_router,
                            'fee': fee,
                            'amount_out': quote,
                            'priority': 3  # Third priority (fallback)
                        })
                        print(f"ETH: Classic V3 fee {fee} sell quote: {quote / 10**18:.6f} WETH")
            
            if not routes:
                print(f"❌ ETH: No viable sell routes found")
                return None
            
            # Sort by priority (V2 first, then SwapRouter02, then Classic V3)
            routes.sort(key=lambda x: x['priority'])
            
            # Step 2: Try each route in order
            for route in routes:
                try:
                    print(f"ETH: Trying {route['type']} sell...")
                    
                    # Approve token for the router
                    current_allowance = self.client.erc20_allowance(
                        token_address, 
                        self.client.account.address, 
                        route['router'].address
                    )
                    if current_allowance < amount_wei:
                        # Approve more than needed to account for fees/rounding
                        approval_amount = amount_wei * 2
                        print(f"ETH: Approving token for {route['type']} router: {approval_amount} wei")
                        approve_res = self.client.approve_erc20(
                            token_address, 
                            route['router'].address, 
                            approval_amount
                        )
                        if not approve_res or approve_res.get('status') != 1:
                            print(f"ETH: Token approval for {route['type']} failed: {approve_res}")
                            continue
                        print(f"ETH: Token approved for {route['type']}: {approve_res.get('tx_hash')}")
                        import time
                        time.sleep(3)  # Wait for approval to be mined
                    
                    # Calculate min_out with proper fee accounting and slippage
                    if route['type'] == 'V2':
                        # V2 doesn't have fees, just slippage
                        min_out = int(route['amount_out'] * 0.98)  # 2% slippage
                    else:
                        # V3 has fees (0.3% for 3000, 0.05% for 500, 1% for 10000)
                        fee_rate = 0.997 if route['fee'] == 3000 else (0.9995 if route['fee'] == 500 else 0.99)
                        expected_after_fee = int(route['amount_out'] * fee_rate)
                        min_out = int(expected_after_fee * 0.98)  # 2% slippage after fee
                    
                    # Execute swap (token -> WETH)
                    if route['type'] == 'V2':
                        result = self.client.v2_swap_exact_tokens_for_tokens(
                            token_in=token_address,
                            token_out=weth,
                            amount_in_wei=amount_wei,
                            amount_out_min_wei=min_out,
                            recipient=self.client.account.address,
                            deadline_seconds=600
                        )
                    elif route['type'] == 'SwapRouter02':
                        result = self.client.swap_exact_input_single(
                            token_in=token_address,
                            token_out=weth,
                            amount_in_wei=amount_wei,
                            fee=route['fee'],
                            amount_out_min=min_out,
                            recipient=self.client.account.address,
                            deadline_seconds=600
                        )
                    elif route['type'] == 'Classic V3':
                        result = self.client.v3_swap_exact_input_single(
                            token_in=token_address,
                            token_out=weth,
                            amount_in_wei=amount_wei,
                            fee=route['fee'],
                            amount_out_min=min_out,
                            recipient=self.client.account.address,
                            deadline_seconds=600
                        )
                    
                    if result and result.get('status') == 1:
                        print(f"✅ ETH: {route['type']} sell successful: {result.get('tx_hash')}")
                        print(f"ETH: Gas used: {result.get('gas_used', 'unknown')}")
                        return result.get('tx_hash')
                    else:
                        print(f"❌ ETH: {route['type']} sell failed: {result}")
                        
                except Exception as e:
                    print(f"❌ ETH: {route['type']} sell error: {e}")
                    continue
            
            print(f"❌ ETH: All smart routing sell attempts failed")

            # Final fallback: try V2 supportingFeeOnTransfer for potential tax tokens
            try:
                # Derive a conservative min_out from V2 quote if available
                min_out_support = 0
                if v2_quote and len(v2_quote) >= 2 and v2_quote[1]:
                    # Apply an extra buffer to tolerate transfer fees (e.g., ~5%) plus 2% slippage
                    expected_out = int(v2_quote[1])
                    min_out_support = int(expected_out * 0.93)  # 7% total headroom
                print("ETH: Trying V2 supportingFeeOnTransfer as final fallback...")
                result_tax = self.client.v2_swap_exact_tokens_for_tokens_supporting_fee(
                    token_in=token_address,
                    token_out=weth,
                    amount_in_wei=amount_wei,
                    amount_out_min_wei=min_out_support,
                    recipient=self.client.account.address,
                    deadline_seconds=600
                )
                if result_tax and result_tax.get('status') == 1:
                    print(f"✅ ETH: V2 supportingFeeOnTransfer sell successful: {result_tax.get('tx_hash')}")
                    # Persist tax flag conservatively
                    try:
                        self._update_position_tax(token_address, 1.0)
                    except Exception:
                        pass
                    return result_tax.get('tx_hash')
                else:
                    print(f"❌ ETH: V2 supportingFeeOnTransfer sell failed: {result_tax}")
            except Exception as e:
                print(f"❌ ETH: V2 supportingFeeOnTransfer error: {e}")

            return None
            
        except Exception as e:
            print(f"❌ ETH: Smart routing sell error: {e}")
            return None

    def _try_swaprouter02_swap_simple(self, token_address: str, amount_wei: int) -> Optional[str]:
        """SwapRouter02 swap for Ethereum (modern, multihop capable)"""
        try:
            print(f"ETH: Attempting SwapRouter02 swap...")
            
            # Approve WETH for SwapRouter02
            current_allowance = self.client.erc20_allowance(self._get_wrapped_token_address(), self.client.account.address, self.client.router.address)
            if current_allowance < amount_wei:
                print(f"ETH: Approving WETH for SwapRouter02: {amount_wei} wei")
                approve_res = self.client.approve_erc20(self._get_wrapped_token_address(), self.client.router.address, amount_wei)
                if not approve_res or approve_res.get('status') != 1:
                    print(f"ETH: WETH SwapRouter02 approval failed: {approve_res}")
                    return None
                print(f"ETH: WETH SwapRouter02 approved: {approve_res.get('tx_hash')}")
                import time
                time.sleep(3)  # Wait for approval to be mined
            
            # Try different fee tiers
            fee_tiers = [3000, 10000, 500, 2500]
            
            for fee in fee_tiers:
                try:
                    print(f"ETH: Trying SwapRouter02 with fee {fee}...")
                    
                    # Get quote for proper minimum output calculation
                    amount_out = self.client.v3_quote_amount_out(
                        self._get_wrapped_token_address(), 
                        token_address, 
                        amount_wei, 
                        fee=fee
                    )
                    min_out = 0
                    if amount_out and amount_out > 0:
                        # 1% slippage buffer
                        min_out = int(amount_out * 0.99)
                    
                    print(f"ETH: SwapRouter02 quote for fee {fee}: {amount_out}, min_out={min_out}")
                    
                    result = self.client.swap_exact_input_single(
                        token_in=self._get_wrapped_token_address(),
                        token_out=token_address,
                        amount_in_wei=amount_wei,
                        fee=fee,
                        amount_out_min=min_out,
                        recipient=self.client.account.address,
                        deadline_seconds=600
                    )
                    
                    if result and result.get('status') == 1:
                        print(f"✅ ETH: SwapRouter02 swap successful with fee {fee}: {result.get('tx_hash')}")
                        return result.get('tx_hash')
                    else:
                        print(f"❌ ETH: SwapRouter02 swap failed with fee {fee}: {result}")
                        
                except Exception as e:
                    print(f"❌ ETH: SwapRouter02 swap error with fee {fee}: {e}")
            
            print(f"❌ ETH: All SwapRouter02 fee tiers failed")
            return None
            
        except Exception as e:
            print(f"❌ ETH: SwapRouter02 swap error: {e}")
            return None

    def _try_uniswap_v3_swap_simple(self, token_address: str, amount_wei: int) -> Optional[str]:
        """Simple Uniswap V3 swap for Ethereum using classic V3 Router"""
        try:
            print(f"ETH: Attempting Uniswap V3 swap with classic router...")
            
            # Approve WETH for classic V3 router
            current_allowance = self.client.erc20_allowance(self._get_wrapped_token_address(), self.client.account.address, self.client.v3_router.address)
            if current_allowance < amount_wei:
                print(f"ETH: Approving WETH for classic V3 router: {amount_wei} wei")
                approve_res = self.client.approve_erc20(self._get_wrapped_token_address(), self.client.v3_router.address, amount_wei)
                if not approve_res or approve_res.get('status') != 1:
                    print(f"ETH: WETH classic V3 approval failed: {approve_res}")
                    return None
                print(f"ETH: WETH classic V3 approved: {approve_res.get('tx_hash')}")
                import time
                time.sleep(3)  # Wait for approval to be mined
            
            # Try different fee tiers
            fee_tiers = [3000, 10000, 500, 2500]
            
            for fee in fee_tiers:
                try:
                    print(f"ETH: Trying classic V3 swap with fee {fee}...")
                    
                    # Get quote for proper minimum output calculation
                    amount_out = self.client.v3_quote_amount_out(
                        self._get_wrapped_token_address(), 
                        token_address, 
                        amount_wei, 
                        fee=fee
                    )
                    min_out = 0
                    if amount_out and amount_out > 0:
                        # 1% slippage buffer
                        min_out = int(amount_out * 0.99)
                    
                    print(f"ETH: Classic V3 quote for fee {fee}: {amount_out}, min_out={min_out}")
                    
                    result = self.client.v3_swap_exact_input_single(
                        token_in=self._get_wrapped_token_address(),
                        token_out=token_address,
                        amount_in_wei=amount_wei,
                        fee=fee,
                        amount_out_min=min_out,
                        recipient=self.client.account.address,
                        deadline_seconds=600
                    )
                    
                    if result and result.get('status') == 1:
                        print(f"✅ ETH: Classic V3 swap successful with fee {fee}: {result.get('tx_hash')}")
                        return result.get('tx_hash')
                    else:
                        print(f"❌ ETH: V3 swap failed with fee {fee}: {result}")
                        
                except Exception as e:
                    print(f"❌ ETH: V3 swap error with fee {fee}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            print(f"❌ ETH: V3 swap general error: {e}")
            return None

    def _try_uniswap_v2_swap_simple(self, token_address: str, amount_wei: int) -> Optional[str]:
        """Simple Uniswap V2 swap for Ethereum"""
        try:
            print(f"ETH: Attempting Uniswap V2 swap...")
            
            # Approve WETH for V2 router
            current_allowance = self.client.erc20_allowance(self._get_wrapped_token_address(), self.client.account.address, self.client.v2_router.address)
            if current_allowance < amount_wei:
                print(f"ETH: Approving WETH for V2 router: {amount_wei} wei")
                approve_res = self.client.approve_erc20(self._get_wrapped_token_address(), self.client.v2_router.address, amount_wei)
                if not approve_res or approve_res.get('status') != 1:
                    print(f"ETH: WETH V2 approval failed: {approve_res}")
                    return None
                print(f"ETH: WETH V2 approved: {approve_res.get('tx_hash')}")
                import time
                time.sleep(3)  # Wait for approval to be mined
            
            # Get quote for proper minimum output calculation
            amounts = self.client.v2_get_amounts_out(self._get_wrapped_token_address(), token_address, amount_wei)
            min_out = 0
            if amounts and len(amounts) >= 2 and amounts[1] and int(amounts[1]) > 0:
                # 1% slippage buffer
                min_out = int(int(amounts[1]) * 0.99)
            
            print(f"ETH: V2 swap quote: {amounts}, min_out={min_out}")
            
            # Use the V2 swap method from the client
            result = self.client.v2_swap_exact_tokens_for_tokens(
                token_in=self._get_wrapped_token_address(),
                token_out=token_address,
                amount_in_wei=amount_wei,
                amount_out_min_wei=min_out,
                recipient=self.client.account.address,
                deadline_seconds=600
            )
            
            if result and result.get('status') == 1:
                print(f"✅ ETH: V2 swap successful: {result.get('tx_hash')}")
                return result.get('tx_hash')
            else:
                print(f"❌ ETH: V2 swap failed: {result}")
                return None
                
        except Exception as e:
            print(f"❌ ETH: V2 swap error: {e}")
            return None

    def execute_sell(self, token_address: str, tokens_to_sell: float, target_price_eth: float) -> Optional[str]:
        """
        Execute sell for Ethereum token using smart routing
        
        Args:
            token_address: Token contract address
            tokens_to_sell: Amount of tokens to sell
            target_price_eth: Target price in ETH (not used for execution, just for logging)
            
        Returns:
            Transaction hash if successful, None otherwise
        """
        try:
            print(f"ETH: Executing sell for {token_address}")
            print(f"ETH: Selling {tokens_to_sell} tokens")
            
            # Get token decimals
            decimals = self.client.get_token_decimals(token_address)
            tokens_wei = int(tokens_to_sell * (10 ** decimals))
            
            print(f"ETH: Tokens in wei: {tokens_wei}")
            
            # Check if we have enough tokens
            balance = self.client.get_token_balance(token_address)
            if balance is None or balance < tokens_to_sell:
                print(f"ETH: Insufficient balance. Available: {balance}, Requested: {tokens_to_sell}")
                return None
            
            # Use smart routing for sell (token -> WETH)
            print("ETH: Using smart routing for sell...")
            return self._smart_routing_sell(token_address, tokens_wei)
            
        except Exception as e:
            print(f"ETH: Sell execution error: {e}")
            return None


