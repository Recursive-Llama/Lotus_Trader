"""
Trader Service: wires existing collaborators behind ports and exposes use cases.

This module does not change behavior; it only adapts current objects to the
ports defined in trader_ports and invokes use cases from trader_usecases.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from .trader_ports import PriceProvider, TradeExecutor, Wallet, PositionRepository, PriceQuote
from .entry_exit_planner import EntryExitPlanner
from . import trader_views
from .trading_logger import trading_logger
from .structured_logger import structured_logger, CorrelationContext, StateDelta, PerformanceMetrics, BusinessLogic
import time
import uuid


class _PriceProviderAdapter(PriceProvider):
    def __init__(self, repo, price_oracle):
        self.repo = repo
        self.price_oracle = price_oracle

    def get_token_price(self, contract: str, chain: str) -> Optional[PriceQuote]:
        # Prefer PriceOracle for a unified response; fallback to DB if needed
        try:
            info = None
            if chain == 'bsc':
                info = self.price_oracle.price_bsc(contract)
            elif chain == 'base':
                info = self.price_oracle.price_base(contract)
            elif chain == 'ethereum':
                info = self.price_oracle.price_eth(contract)
            elif chain == 'solana':
                info = self.price_oracle.price_solana(contract)
            if info and 'price_native' in info:
                return PriceQuote(
                    token_contract=contract,
                    chain=chain,
                    price_native=float(info.get('price_native', 0.0)),
                    price_usd=float(info.get('price_usd', 0.0)) if info.get('price_usd') is not None else None,
                    native_symbol='ETH' if chain in ('base','ethereum') else ('BNB' if chain=='bsc' else 'SOL'),
                    timestamp_iso=None,
                )
        except Exception:
            pass
        return None

    def get_native_usd_rate(self, chain: str) -> float:
        # Delegate to existing method on repo owner (DB-backed source expected)
        try:
            # We do not import the trader here; this adapter should be replaced with
            # a dedicated DB-backed rate provider later. For now, fallback to price_oracle
            if chain in ('base', 'ethereum'):
                # Use WETH from ETH for both
                info = self.price_oracle.price_eth('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
                return float((info or {}).get('price_usd') or 0.0) if info else 0.0
            elif chain == 'bsc':
                info = self.price_oracle.price_bsc('0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c')
                return float((info or {}).get('price_usd') or 0.0) if info else 0.0
            elif chain == 'solana':
                info = self.price_oracle.price_solana('So11111111111111111111111111111111111111112')
                return float((info or {}).get('price_usd') or 0.0) if info else 0.0
        except Exception:
            return 0.0
        return 0.0


class _TradeExecutorAdapter(TradeExecutor):
    def __init__(self, base_executor=None, bsc_executor=None, eth_executor=None, sol_executor=None):
        self.base_executor = base_executor
        self.bsc_executor = bsc_executor
        self.eth_executor = eth_executor
        self.sol_executor = sol_executor

    def execute_buy(self, token_address: str, amount_native: float) -> Optional[str]:
        # Not used in this phase; kept for completeness
        return None

    def execute_sell(self, token_address: str, tokens_to_sell: float, target_price_native: float) -> Optional[str]:
        # Choose executor based on which are available; caller decides chain in phase 2
        # Here we assume caller chose the correct specific executor instance
        # This generic adapter should be replaced per-chain as we migrate
        if self.base_executor:
            return self.base_executor.execute_sell(token_address, tokens_to_sell, target_price_native)
        if self.bsc_executor:
            return self.bsc_executor.execute_sell(token_address, tokens_to_sell, target_price_native)
        if self.eth_executor:
            return self.eth_executor.execute_sell(token_address, tokens_to_sell, target_price_native)
        if self.sol_executor:
            # solana is async in native code; this adapter is sync to fit the interface
            # In service, prefer calling the native sol path directly until we split adapters per chain
            return None
        return None


class TraderService:
    """Facade to invoke use cases via ports.

    This service is created by wiring existing collaborators from the caller (the legacy trader class)
    into the minimal adapters above.
    """

    def __init__(self, *,
                 repo,
                 price_oracle,
                 wallet,
                 base_executor=None,
                 bsc_executor=None,
                 eth_executor=None,
                 sol_executor=None,
                 js_solana_client=None) -> None:
        self.price_oracle = price_oracle
        self.price_provider = _PriceProviderAdapter(repo, price_oracle)
        self.wallet = wallet
        self.repo = repo
        self.executor = _TradeExecutorAdapter(
            base_executor=base_executor,
            bsc_executor=bsc_executor,
            eth_executor=eth_executor,
            sol_executor=sol_executor,
        )
        # Keep direct references for confirmations
        self.base_executor = base_executor
        self.bsc_executor = bsc_executor
        self.eth_executor = eth_executor
        self.sol_executor = sol_executor
        self._js_solana_client = js_solana_client
        self._notifier = None

        # No separate use-case layer; methods below inline simple orchestration

    def execute_exit(self, *, position_id: str, chain: str, contract: str, token_ticker: str, exit_number: int, tokens_to_sell: float, target_price_native: float) -> Optional[str]:
        # Inline: delegate to appropriate executor (sync path for EVM; SOL handled by caller)
        try:
            # Preconditions log
            executor_ready = (
                (chain == 'base' and self.base_executor is not None) or
                (chain == 'bsc' and self.bsc_executor is not None) or
                (chain == 'ethereum' and self.eth_executor is not None)
            )
            structured_logger.log_exit_preconditions(
                position_id=position_id,
                token=token_ticker or 'UNKNOWN',
                chain=chain,
                contract=contract,
                exit_number=exit_number,
                checks={
                    'executor_ready': executor_ready,
                    'price_ok': target_price_native is not None and float(target_price_native) > 0,
                    # quantity check is done upstream; we record intent here
                    'quantity_check_passed': True,
                },
                details={
                    'tokens_to_sell': tokens_to_sell,
                    'target_price': target_price_native,
                }
            )

            v = None
            tx = None
            if chain == 'base' and self.base_executor:
                v = self.resolve_base_venue(contract)
                tx = self.base_executor.execute_sell(contract, tokens_to_sell, target_price_native)
            elif chain == 'bsc' and self.bsc_executor:
                v = self.resolve_bsc_venue(contract)
                tx = self.bsc_executor.execute_sell(contract, tokens_to_sell, target_price_native)
            elif chain == 'ethereum' and self.eth_executor:
                tx = self.eth_executor.execute_sell(contract, tokens_to_sell, target_price_native)
            else:
                tx = None

            if tx:
                # Minimal structured success (state deltas are handled elsewhere)
                structured_logger.log_exit_success(
                    position_id=position_id,
                    exit_number=exit_number,
                    token=token_ticker or 'UNKNOWN',
                    chain=chain,
                    contract=contract,
                    tx_hash=tx,
                    tokens_sold=tokens_to_sell,
                    native_amount=tokens_to_sell * float(target_price_native or 0),
                    actual_price=float(target_price_native or 0),
                    venue=v['dex'] if isinstance(v, dict) and 'dex' in v else ('unknown' if chain in ('bsc','base') else 'n/a'),
                    state_before=StateDelta(),
                    state_after=StateDelta(),
                    performance=PerformanceMetrics()
                )
                structured_logger.log_performance_summary()
                return tx
            else:
                structured_logger.log_exit_failed(
                    position_id=position_id,
                    exit_number=exit_number,
                    token=token_ticker or 'UNKNOWN',
                    chain=chain,
                    contract=contract,
                    reason='executor_noop',
                    error_details={'venue': v, 'tokens_to_sell': tokens_to_sell, 'target_price': target_price_native}
                )
                return None
        except Exception as e:
            structured_logger.log_exit_failed(
                position_id=position_id,
                exit_number=exit_number,
                token=token_ticker or 'UNKNOWN',
                chain=chain,
                contract=contract,
                reason='exception',
                error_details={'error': str(e), 'type': type(e).__name__}
            )
            return None

    def execute_entry(self, *, position_id: str, chain: str, contract: str, token_ticker: str, entry_number: int, amount_native: float, price_native: float) -> Optional[str]:
        # Inline: delegate to appropriate executor (sync path for EVM; SOL handled by caller)
        try:
            if chain == 'base' and self.base_executor:
                return self.base_executor.execute_buy(contract, amount_native)
            if chain == 'bsc' and self.bsc_executor:
                return self.bsc_executor.execute_buy(contract, amount_native)
            if chain == 'ethereum' and self.eth_executor:
                return self.eth_executor.execute_buy(contract, amount_native)
            # For Solana, entry path is async on executor; caller should call sol executor directly
            return None
        except Exception:
            return None

    def spawn_trend_from_exit(self, *, position_id: str, exit_price: float, native_amount: float, source_exit_number: str) -> Optional[str]:
        """Replicate legacy trend batch creation using domain planner and repo updates."""
        try:
            if exit_price <= 0 or native_amount <= 0:
                return None
            
            # Create unique batch ID per exit to avoid collisions
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            batch_id = f"trend-{position_id}-exit{source_exit_number}-{timestamp}"
            
            trend_entries = EntryExitPlanner.build_trend_entries_from_standard_exit(
                exit_price=exit_price,
                exit_native_amount=native_amount,
                source_exit_id=source_exit_number,
                batch_id=batch_id,
            )
            
            # Replace all existing trend entries (don't extend) to avoid stale entries
            self.repo.update_trend_entries(position_id, trend_entries)
            # Structured log for batch creation
            structured_logger.log_trend_batch_created(
                position_id=position_id,
                batch_id=batch_id,
                source_exit_number=int(source_exit_number) if str(source_exit_number).isdigit() else 0,
                funded_amount=native_amount,
                chain=self.repo.get_position(position_id).get('token_chain', '').lower() if self.repo.get_position(position_id) else 'unknown',
                token=self.repo.get_position(position_id).get('token_ticker', 'UNKNOWN') if self.repo.get_position(position_id) else 'UNKNOWN'
            )
            structured_logger.log_performance_summary()
            return batch_id
        except Exception:
            return None

    def plan_buyback(self, *, chain: str, exit_value_native: float, enabled: bool, percentage: float, min_amount_native: float) -> dict:
        # Inline of previous ExecuteBuyback use-case
        try:
            if (chain or '').lower() != 'solana':
                structured_logger.log_buyback_planned(
                    position_id=None,
                    chain=chain,
                    exit_value_native=exit_value_native,
                    buyback_amount_native=0.0,
                    percentage=percentage,
                    min_amount=min_amount_native,
                    skipped=True,
                    reason='Not a SOL exit'
                )
                return {'success': True, 'skipped': True, 'reason': 'Not a SOL exit'}
            if not enabled:
                structured_logger.log_buyback_planned(
                    position_id=None,
                    chain=chain,
                    exit_value_native=exit_value_native,
                    buyback_amount_native=0.0,
                    percentage=percentage,
                    min_amount=min_amount_native,
                    skipped=True,
                    reason='Buyback disabled'
                )
                return {'success': True, 'skipped': True, 'reason': 'Buyback disabled'}
            buyback_amount = float(exit_value_native) * (float(percentage) / 100.0)
            if buyback_amount < float(min_amount_native):
                structured_logger.log_buyback_planned(
                    position_id=None,
                    chain=chain,
                    exit_value_native=exit_value_native,
                    buyback_amount_native=buyback_amount,
                    percentage=percentage,
                    min_amount=min_amount_native,
                    skipped=True,
                    reason=f'Below minimum threshold ({min_amount_native})'
                )
                return {
                    'success': True,
                    'skipped': True,
                    'reason': f'Below minimum threshold ({min_amount_native})',
                    'buyback_amount_native': buyback_amount,
                }
            
            structured_logger.log_buyback_planned(
                position_id=None,
                chain=chain,
                exit_value_native=exit_value_native,
                buyback_amount_native=buyback_amount,
                percentage=percentage,
                min_amount=min_amount_native,
                skipped=False,
                reason=None
            )
            
            return {
                'success': True,
                'skipped': False,
                'buyback_amount_native': buyback_amount,
            }
        except Exception as e:
            structured_logger.log_buyback_planned(
                position_id=None,
                chain=chain,
                exit_value_native=exit_value_native,
                buyback_amount_native=0.0,
                percentage=percentage,
                min_amount=min_amount_native,
                skipped=True,
                reason=f'Exception: {str(e)}'
            )
            return {'success': False, 'error': 'buyback_plan_failed'}

    async def perform_buyback(self, *, lotus_contract: str, holding_wallet: str, buyback_amount_native: float, slippage_pct: float = 5.0) -> dict:
        """Execute Jupiter swap SOL->Lotus and transfer to holding wallet.

        Returns a result dict similar to legacy path for compatibility.
        """
        try:
            if not self._js_solana_client:
                return {'success': False, 'error': 'JSSolanaClient not initialized'}

            # Validate inputs
            if buyback_amount_native <= 0:
                return {'success': False, 'error': 'Invalid buyback amount'}
            
            if not lotus_contract or not holding_wallet:
                return {'success': False, 'error': 'Missing contract or wallet address'}

            # Convert SOL to lamports (9 decimals)
            lamports = int(float(buyback_amount_native) * 1_000_000_000)
            slippage_bps = int(slippage_pct * 100)

            trading_logger.info(f"Executing Lotus buyback: {buyback_amount_native:.6f} SOL -> {lotus_contract}")

            # Execute Jupiter swap (async method)
            result = await self._js_solana_client.execute_jupiter_swap(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint=lotus_contract,
                amount=lamports,
                slippage_bps=slippage_bps,
            )

            if result.get('success', False):
                output_amount = result.get('outputAmount', 0)
                lotus_amount_tokens = float(output_amount) / 1_000_000_000

                # For now, just return success - the tokens are in our wallet
                # TODO: Implement transfer to holding wallet if needed
                return {
                    'success': True,
                    'skipped': False,
                    'buyback_amount_sol': buyback_amount_native,
                    'lotus_tokens': lotus_amount_tokens,
                    'swap_tx_hash': result.get('signature', ''),
                    'holding_wallet': holding_wallet,
                }

            return {'success': False, 'error': result.get('error', 'Swap failed')}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ------------------------------
    # Transaction confirmation and tax detection
    # ------------------------------
    async def wait_for_transaction_confirmation(self, tx_hash: str, chain: str, timeout: int = 60) -> bool:
        try:
            client = None
            if chain == 'base' and self.base_executor:
                client = self.base_executor.client
            elif chain == 'ethereum' and self.eth_executor:
                client = self.eth_executor.client
            elif chain == 'bsc' and self.bsc_executor:
                client = self.bsc_executor.client

            if not client:
                return False

            import time, asyncio as _asyncio
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    receipt = client.w3.eth.get_transaction_receipt(tx_hash)
                    if receipt and receipt.status == 1:
                        return True
                    elif receipt and receipt.status == 0:
                        return False
                except Exception:
                    pass
                await _asyncio.sleep(2)
            return False
        except Exception:
            return False

    async def detect_and_update_tax_token(self, token_address: str, amount_spent: float, price: float, chain: str) -> None:
        try:
            expected_tokens = amount_spent / price if price and price > 0 else 0
            import asyncio as _asyncio
            await _asyncio.sleep(5)
            actual_tokens = await self.wallet.get_balance(chain, token_address)
            if actual_tokens is None:
                return
            actual_tokens_float = float(actual_tokens)
            if expected_tokens > 0 and actual_tokens_float > 0:
                tax_pct = ((expected_tokens - actual_tokens_float) / expected_tokens) * 100
                if tax_pct > 1.0:
                    try:
                        self.repo.update_tax_percentage(token_address, tax_pct)
                    except Exception:
                        pass
        except Exception:
            return

    # ------------------------------
    # Notifier integration
    # ------------------------------
    def set_notifier(self, notifier) -> None:
        self._notifier = notifier

    async def send_buy_signal(self, *, token_ticker: str, token_contract: str, chain: str, amount_native: float, price: float, tx_hash: str, allocation_pct, source_tweet_url: Optional[str]) -> None:
        if not self._notifier:
            return
        try:
            view = await trader_views.build_buy_view(
                amount_native=amount_native,
                chain=chain,
                get_native_usd_rate=self.get_native_usd_rate_async,
            )
            await self._notifier.send_buy_signal(
                token_ticker=token_ticker,
                token_contract=token_contract,
                chain=chain,
                amount_native=amount_native,
                price=price,
                tx_hash=tx_hash,
                source_tweet_url=source_tweet_url,
                allocation_pct=allocation_pct,
                amount_usd=view.get('amount_usd'),
            )
        except Exception:
            return

    async def send_sell_signal(self, *, position_id: str, exit_number: int, tokens_sold: float, sell_price: float, tx_hash: str, chain: str, contract: str, buyback_result: Optional[dict]) -> None:
        if not self._notifier:
            return
        try:
            position = self.repo.get_position(position_id)
            if not position:
                return
            sell_view = await trader_views.build_sell_view(
                position=position,
                tokens_sold=tokens_sold,
                sell_price_native=sell_price,
                chain=chain,
                contract=contract,
                price_oracle=self.price_provider if hasattr(self.price_provider, 'price_oracle') else None or self.price_oracle,
                get_native_usd_rate=self.get_native_usd_rate_async,
            )
            await self._notifier.send_sell_signal(
                token_ticker=position.get('token_ticker', 'UNKNOWN'),
                token_contract=contract,
                chain=chain,
                tokens_sold=tokens_sold,
                sell_price=sell_price,
                tx_hash=tx_hash,
                tokens_sold_value_usd=sell_view.get('tokens_sold_value_usd'),
                total_profit_usd=position.get('total_pnl_usd'),
                source_tweet_url=position.get('source_tweet_url'),
                remaining_tokens=(position.get('total_quantity', 0) or 0) - tokens_sold,
                position_value=sell_view.get('position_value'),
                total_pnl_pct=position.get('total_pnl_pct', 0),
                profit_native=None,
                buyback_amount_sol=(buyback_result or {}).get('buyback_amount_sol') if buyback_result else None,
                lotus_tokens=(buyback_result or {}).get('lotus_tokens') if buyback_result else None,
                buyback_tx_hash=(buyback_result or {}).get('transfer_tx_hash') if buyback_result else None,
            )
        except Exception:
            return

    async def send_trend_entry_notification(self, *, position_id: str, entry_number: int, tx_hash: str, amount_native: float, price: float, dip_pct: float, batch_id: str) -> None:
        if not self._notifier:
            return
        try:
            position = self.repo.get_position(position_id)
            if not position:
                return
            view = await trader_views.build_trend_entry_view(
                amount_native=amount_native,
                chain=position.get('token_chain', '').lower(),
                get_native_usd_rate=self.get_native_usd_rate_async,
            )
            await self._notifier.send_trend_entry_notification(
                token_ticker=position.get('token_ticker', 'Unknown'),
                token_contract=position.get('token_contract', ''),
                chain=position.get('token_chain', '').lower(),
                amount_native=amount_native,
                price=price,
                tx_hash=tx_hash,
                dip_pct=dip_pct,
                batch_id=batch_id,
                source_tweet_url=position.get('source_tweet_url'),
                amount_usd=view.get('amount_usd'),
            )
        except Exception:
            return

    async def send_trend_exit_notification(self, *, position_id: str, exit_number: int, tx_hash: str, tokens_sold: float, sell_price: float, gain_pct: float, batch_id: str, profit_pct: Optional[float], profit_usd: Optional[float]) -> None:
        if not self._notifier:
            return
        try:
            position = self.repo.get_position(position_id)
            if not position:
                return
            view = await trader_views.build_trend_exit_view(
                profit_usd=profit_usd,
                chain=position.get('token_chain', '').lower(),
                get_native_usd_rate=self.get_native_usd_rate_async,
            )
            await self._notifier.send_trend_exit_notification(
                token_ticker=position.get('token_ticker', 'Unknown'),
                token_contract=position.get('token_contract', ''),
                chain=position.get('token_chain', '').lower(),
                tokens_sold=tokens_sold,
                sell_price=sell_price,
                tx_hash=tx_hash,
                gain_pct=gain_pct,
                batch_id=batch_id,
                profit_pct=profit_pct,
                profit_usd=profit_usd,
                profit_native=view.get('profit_native'),
                source_tweet_url=position.get('source_tweet_url'),
            )
        except Exception:
            return

    # ------------------------------
    # Price helpers
    # ------------------------------
    async def get_current_price_native_from_db(self, contract: str, chain: str) -> Optional[float]:
        try:
            result = self.repo.client.table('lowcap_price_data_1m').select(
                'price_native'
            ).eq('token_contract', contract).eq('chain', chain).order(
                'timestamp', desc=True
            ).limit(1).execute()
            if result.data:
                return float(result.data[0]['price_native'])
            return None
        except Exception:
            return None

    async def get_native_usd_rate_async(self, chain: str) -> float:
        try:
            return float(self.price_provider.get_native_usd_rate(chain) or 0.0)
        except Exception:
            return 0.0

    # ------------------------------
    # Exit recalculation helpers
    # ------------------------------
    async def recalculate_exits_after_entry(self, position_id: str) -> None:
        try:
            position = self.repo.get_position(position_id)
            if not position:
                return
            exit_rules = position.get('exit_rules', {})
            avg_entry_price = position.get('avg_entry_price', 0)
            if not exit_rules or not exit_rules.get('stages'):
                return
            if avg_entry_price <= 0:
                return
            new_exits = EntryExitPlanner.build_exits(exit_rules, avg_entry_price)
            position['exits'] = new_exits
            self.repo.update_position(position_id, position)
        except Exception:
            return

    def recalculate_exits_for_position(self, position_id: str, new_avg_entry_price: float) -> bool:
        try:
            position = self.repo.get_position(position_id)
            if not position:
                return False
            exit_rules = position.get('exit_rules', {})
            if not exit_rules:
                return False
            exits = EntryExitPlanner.build_exits(exit_rules, new_avg_entry_price)
            return bool(self.repo.update_exits(position_id, exits))
        except Exception:
            return False

    # ------------------------------
    # Venue resolvers
    # ------------------------------
    def resolve_bsc_venue(self, token_address: str):
        try:
            import requests
            r = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}", timeout=8)
            if not r.ok:
                return None
            pairs = (r.json() or {}).get('pairs') or []
            bsc_pairs = [p for p in pairs if p.get('chainId') == 'bsc']
            cands = [p for p in bsc_pairs if p.get('quoteToken', {}).get('symbol') in ('WBNB','BNB')]
            if not cands:
                return None
            cands.sort(key=lambda p: (p.get('liquidity', {}) .get('usd') or 0), reverse=True)
            chosen = cands[0]
            return {'dex': chosen.get('dexId'), 'pair': chosen.get('pairAddress')}
        except Exception:
            return None

    def resolve_base_venue(self, token_address: str):
        try:
            import requests
            r = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}", timeout=8)
            if not r.ok:
                return None
            pairs = (r.json() or {}).get('pairs') or []
            base_pairs = [p for p in pairs if p.get('chainId') == 'base']
            weth_pairs = [p for p in base_pairs if p.get('quoteToken',{}).get('symbol') == 'WETH']
            if not weth_pairs:
                return None
            weth_pairs.sort(key=lambda p: (p.get('liquidity',{}) .get('usd') or 0), reverse=True)
            best_pair = weth_pairs[0]
            return {'dex': best_pair.get('dexId'), 'pair': best_pair.get('pairAddress')}
        except Exception:
            return None

    # ------------------------------
    # Execute decision (position bootstrap)
    # ------------------------------
    async def execute_decision(self, decision: dict) -> Optional[dict]:
        start_time = time.time()
        decision_id = decision.get('id', str(uuid.uuid4()))
        
        try:
            token = (decision.get('signal_pack') or {}).get('token') or {}
            chain = (token.get('chain') or '').lower()
            ticker = token.get('ticker')
            contract = token.get('contract')
            allocation_pct = float((decision.get('content', {}) or {}).get('allocation_pct') or 0)
            
            # Log decision attempt with structured logging
            correlation = CorrelationContext(
                decision_id=decision_id,
                chain=chain,
                contract=contract,
                token=ticker,
                action_type="decision"
            )
            
            business = BusinessLogic(
                allocation_pct=allocation_pct,
                curator_score=float((decision.get('content', {}) or {}).get('curator_score', 0)),
                reasoning="Processing trading decision"
            )
            
            structured_logger.log_decision_approved(
                decision_id=decision_id,
                token=ticker or 'UNKNOWN',
                chain=chain,
                contract=contract,
                allocation_pct=allocation_pct,
                curator_score=float((decision.get('content', {}) or {}).get('curator_score', 0)),
                constraints_passed=["decision_processing"],
                reasoning="Processing trading decision"
            )
            
            # Log decision attempt (legacy)
            trading_logger.log_trade_attempt(
                chain=chain,
                token=ticker or 'UNKNOWN',
                action='execute_decision',
                details={
                    'decision_id': decision.get('id'),
                    'allocation_pct': allocation_pct,
                    'contract': contract
                }
            )

            if (decision.get('content', {}) or {}).get('action') != 'approve':
                # Structured rejection
                structured_logger.log_decision_rejected(
                    decision_id=decision_id,
                    token=ticker or 'UNKNOWN',
                    chain=chain,
                    contract=contract,
                    reason='action_not_approve',
                    constraints_failed=['action_approve_required'],
                    details={'action': decision.get('content', {}).get('action')}
                )
                trading_logger.log_decision_rejection(
                    token=ticker or 'UNKNOWN',
                    reason='action_not_approve',
                    details={'action': decision.get('content', {}).get('action')}
                )
                return None

            # idempotency
            existing_for_book = self.repo.get_position_by_book_id(decision.get('id'))
            if existing_for_book:
                structured_logger.log_decision_rejected(
                    decision_id=decision_id,
                    token=ticker or 'UNKNOWN',
                    chain=chain,
                    contract=contract,
                    reason='position_already_exists',
                    constraints_failed=['idempotency_conflict'],
                    details={'existing_position_id': existing_for_book.get('id')}
                )
                trading_logger.log_decision_rejection(
                    token=ticker or 'UNKNOWN',
                    reason='position_already_exists',
                    details={'existing_position_id': existing_for_book.get('id')}
                )
                return None

            # chain setup
            price = None
            executor = None
            venue = None
            native_label = ''
            if chain == 'bsc':
                native_label = 'BNB'
                balance = await self.wallet.get_balance('bsc')
                trading_logger.log_balance_check('bsc', balance)
                
                info = self.price_oracle.price_bsc(contract)
                price = info['price_native'] if info else None
                trading_logger.log_price_retrieval('bsc', ticker or 'UNKNOWN', price, 'price_oracle')
                
                executor = self.bsc_executor
                trading_logger.log_executor_status('bsc', executor, f"bsc_executor={executor is not None}")
                venue = self.resolve_bsc_venue(contract)
                trading_logger.log_venue_resolution('bsc', ticker or 'UNKNOWN', venue)
            elif chain == 'base':
                native_label = 'ETH'
                balance = await self.wallet.get_balance('base')
                trading_logger.log_balance_check('base', balance)
                
                info = self.price_oracle.price_base(contract)
                price = info['price_native'] if info else None
                trading_logger.log_price_retrieval('base', ticker or 'UNKNOWN', price, 'price_oracle')
                
                executor = self.base_executor
                trading_logger.log_executor_status('base', executor, f"base_executor={executor is not None}")
                venue = self.resolve_base_venue(contract)
                trading_logger.log_venue_resolution('base', ticker or 'UNKNOWN', venue)
            elif chain == 'ethereum':
                native_label = 'ETH'
                balance = await self.wallet.get_balance('ethereum')
                trading_logger.log_balance_check('ethereum', balance)
                
                info = self.price_oracle.price_eth(contract)
                price = info['price_native'] if info else None
                trading_logger.log_price_retrieval('ethereum', ticker or 'UNKNOWN', price, 'price_oracle')
                
                executor = self.eth_executor
                trading_logger.log_executor_status('ethereum', executor, f"eth_executor={executor is not None}")
                venue = None
            elif chain == 'solana':
                native_label = 'SOL'
                balance = await self.wallet.get_balance('solana')
                trading_logger.log_balance_check('solana', balance)
                
                info = self.price_oracle.price_solana(contract)
                price = (info or {}).get('price_native') if info else None
                trading_logger.log_price_retrieval('solana', ticker or 'UNKNOWN', price, 'price_oracle')
                
                executor = self.sol_executor
                trading_logger.log_executor_status('solana', executor, f"sol_executor={executor is not None}")
                venue = None
            else:
                structured_logger.log_decision_rejected(
                    decision_id=decision_id,
                    token=ticker or 'UNKNOWN',
                    chain=chain,
                    contract=contract,
                    reason='unsupported_chain',
                    constraints_failed=['chain_not_supported'],
                    details={'chain': chain}
                )
                trading_logger.log_decision_rejection(
                    token=ticker or 'UNKNOWN',
                    reason='unsupported_chain',
                    details={'chain': chain}
                )
                return None

            if not balance or float(balance) <= 0:
                structured_logger.log_decision_rejected(
                    decision_id=decision_id,
                    token=ticker or 'UNKNOWN',
                    chain=chain,
                    contract=contract,
                    reason='insufficient_balance',
                    constraints_failed=['liquidity_requirement'],
                    details={'balance': balance, 'required': '> 0'}
                )
                trading_logger.log_trade_failure(
                    chain=chain,
                    token=ticker or 'UNKNOWN',
                    reason='insufficient_balance',
                    details={'balance': balance, 'required': '> 0'}
                )
                return None
            alloc_native = (allocation_pct * float(balance)) / 100.0
            if alloc_native <= 0 or not price:
                structured_logger.log_decision_rejected(
                    decision_id=decision_id,
                    token=ticker or 'UNKNOWN',
                    chain=chain,
                    contract=contract,
                    reason='invalid_allocation_or_price',
                    constraints_failed=['allocation_positive', 'price_available'],
                    details={'alloc_native': alloc_native, 'price': price}
                )
                trading_logger.log_trade_failure(
                    chain=chain,
                    token=ticker or 'UNKNOWN',
                    reason='invalid_allocation_or_price',
                    details={'alloc_native': alloc_native, 'price': price}
                )
                return None

            from datetime import datetime, timezone
            position_id = f"{ticker}_{chain}_{int(datetime.now(timezone.utc).timestamp())}"

            # source url
            source_tweet_url = None
            sp = decision.get('signal_pack', {}) or {}
            source_tweet_url = sp.get('source_tweet_url') or sp.get('tweet_url') or sp.get('url') or (sp.get('message', {}) or {}).get('url')
            if not source_tweet_url:
                mi = decision.get('module_intelligence', {}) or {}
                ss = mi.get('social_signal', {}) or {}
                source_tweet_url = (ss.get('message', {}) or {}).get('url')

            # create position
            position = {
                'id': position_id,
                'token_chain': chain,
                'token_contract': contract,
                'token_ticker': ticker,
                'book_id': decision.get('id'),
                'status': 'active',
                'total_allocation_pct': allocation_pct,
                'total_quantity': 0.0,
                'total_tokens_bought': 0.0,
                'total_tokens_sold': 0.0,
                'total_investment_native': 0.0,
                'total_extracted_native': 0.0,
                'total_pnl_native': 0.0,
                'curator_sources': (decision.get('content', {}) or {}).get('curator_id'),
                'source_tweet_url': source_tweet_url,
                'first_entry_timestamp': datetime.now(timezone.utc).isoformat(),
                'exit_rules': self._build_exit_rules_from_config(),
                'trend_exit_rules': self._build_trend_exit_rules_from_config(),
            }
            if not self.repo.create_position(position):
                # DB failure logging (structured + legacy)
                structured_logger.log_entry_failed(
                    position_id=position_id,
                    entry_number=1,
                    token=ticker or 'UNKNOWN',
                    chain=chain,
                    contract=contract,
                    reason='database_update_failed',
                    error_details={'stage': 'create_position', 'position_id': position_id}
                )
                trading_logger.log_trade_failure(
                    chain=chain,
                    token=ticker or 'UNKNOWN',
                    reason='position_creation_failed',
                    details={'position_id': position_id}
                )
                return None
            
            trading_logger.log_position_creation(
                position_id=position_id,
                token=ticker or 'UNKNOWN',
                chain=chain,
                allocation=allocation_pct
            )

            # entries
            from .entry_exit_planner import EntryExitPlanner
            entries = EntryExitPlanner.build_entries(price, alloc_native)
            for e in entries:
                e['unit'] = 'NATIVE'
                e['native_symbol'] = native_label
            self.repo.update_entries(position_id, entries)

            # Precondition log before first buy
            structured_logger.log_entry_preconditions(
                position_id=position_id,
                token=ticker or 'UNKNOWN',
                chain=chain,
                contract=contract,
                entry_number=1,
                checks={
                    'balance_ok': bool(balance) and float(balance) > 0,
                    'price_ok': bool(price),
                    'executor_ready': executor is not None,
                    'venue_ok': bool(venue) if chain in ('bsc','base') else True,
                },
                details={
                    'balance': float(balance) if balance else 0.0,
                    'price': float(price) if price else None,
                    'venue': venue
                }
            )

            # first buy
            e_amt = alloc_native / 3.0
            tx_hash = None
            
            # Log entry attempt
            structured_logger.log_entry_attempted(
                position_id=position_id,
                entry_number=1,
                token=ticker or 'UNKNOWN',
                chain=chain,
                contract=contract,
                amount_native=e_amt,
                target_price=price,
                decision_id=decision_id
            )
            
            if chain in ('bsc','base') and executor:
                v = self.resolve_bsc_venue(contract) if chain=='bsc' else self.resolve_base_venue(contract)
                tx_hash = executor.execute_buy(contract, e_amt, venue=v)
            elif chain == 'ethereum' and executor:
                tx_hash = executor.execute_buy(contract, e_amt)
            elif chain == 'solana' and executor:
                tx_hash = await executor.execute_buy(contract, e_amt)
            
            if not tx_hash:
                structured_logger.log_entry_failed(
                    position_id=position_id,
                    entry_number=1,
                    token=ticker or 'UNKNOWN',
                    chain=chain,
                    contract=contract,
                    reason='executor_noop',
                    error_details={'executor': executor is not None, 'amount': e_amt}
                )
                trading_logger.log_trade_failure(
                    chain=chain,
                    token=ticker or 'UNKNOWN',
                    reason='transaction_execution_failed',
                    details={'executor': executor is not None, 'amount': e_amt}
                )
                return None
            
            # Log successful entry
            tokens_bought = e_amt / price
            duration_ms = int((time.time() - start_time) * 1000)
            performance = PerformanceMetrics(
                duration_ms=duration_ms,
                executor=f"{chain}_executor",
                venue=v if chain in ('bsc','base') else None
            )
            
            # Get state after position creation but before updates
            state_before = StateDelta(
                total_tokens_bought=0.0,
                total_quantity_before=0.0,
                total_investment_native=0.0,
                avg_entry_price=0.0,
                pnl_native=0.0,
                pnl_usd=0.0,
                pnl_pct=0.0
            )
            
            structured_logger.log_entry_success(
                position_id=position_id,
                entry_number=1,
                token=ticker or 'UNKNOWN',
                chain=chain,
                contract=contract,
                tx_hash=tx_hash,
                amount_native=e_amt,
                tokens_bought=tokens_bought,
                actual_price=price,
                venue=v if chain in ('bsc','base') else "unknown",
                state_before=state_before,
                state_after=state_before,  # Will be updated after aggregates
                performance=performance
            )
            
            trading_logger.log_trade_success(
                chain=chain,
                token=ticker or 'UNKNOWN',
                tx_hash=tx_hash,
                details={'amount': e_amt, 'price': price}
            )

            # cost + tokens
            cost_native = e_amt
            info = None
            if chain == 'bsc': info = self.price_oracle.price_bsc(contract)
            elif chain == 'base': info = self.price_oracle.price_base(contract)
            elif chain == 'ethereum': info = self.price_oracle.price_eth(contract)
            elif chain == 'solana': info = self.price_oracle.price_solana(contract)
            cost_usd = 0.0
            tokens_bought = e_amt / price
            if info and info.get('price_usd'):
                cost_usd = tokens_bought * float(info['price_usd'])
            self.repo.mark_entry_executed(position_id=position_id, entry_number=1, tx_hash=tx_hash, cost_native=cost_native, cost_usd=cost_usd, tokens_bought=tokens_bought)

            # totals and exits
            await self.set_quantity_from_trade(position_id, tokens_bought)
            
            # Update position aggregates (missing calls that were causing the bug)
            await self._update_tokens_bought(position_id, tokens_bought)
            await self._update_total_investment_native(position_id, cost_native)
            await self._update_position_pnl(position_id)
            
            # exit rules
            # (caller can update rules later; here we just recalc exits using avg price)
            await self.recalculate_exits_after_entry(position_id)
            
            # Update wallet balance after successful entry
            await self._update_wallet_balance_after_trade(chain)

            # send buy notification
            await self.send_buy_signal(
                token_ticker=ticker,
                token_contract=contract,
                chain=chain,
                amount_native=e_amt,
                price=price,
                tx_hash=tx_hash,
                allocation_pct=allocation_pct,
                source_tweet_url=source_tweet_url,
            )

            # Periodic performance summary emit
            structured_logger.log_performance_summary()

            # Position cap check - close 6 smallest positions if we now have 34+
            await self._check_and_enforce_position_cap()

            return {
                'position_id': position_id,
                'token_ticker': ticker,
                'allocation_pct': allocation_pct,
                'allocation_native': alloc_native,
                'status': 'active',
            }
        except Exception as e:
            trading_logger.errors.error(f"EXECUTE_DECISION_EXCEPTION | {ticker or 'UNKNOWN'} | {chain} | {str(e)}")
            import traceback
            trading_logger.errors.error(f"TRACEBACK: {traceback.format_exc()}")
            return None

    # ------------------------------
    # Wallet reconciliation helpers
    # ------------------------------
    async def set_quantity_from_trade(self, position_id: str, tokens_delta: float) -> bool:
        try:
            position = self.repo.get_position(position_id)
            if not position:
                return False
            old_quantity = float(position.get('total_quantity', 0.0) or 0.0)
            new_quantity = old_quantity + float(tokens_delta)
            position['total_quantity'] = new_quantity
            ok = self.repo.update_position(position_id, position)
            return bool(ok)
        except Exception:
            return False

    async def reconcile_wallet_quantity(self, position_id: str, expected_quantity: float) -> None:
        try:
            # Wait briefly to allow confirmations to settle if caller wants
            await __import__('asyncio').sleep(0)
            position = self.repo.get_position(position_id)
            if not position:
                return
            chain = position.get('token_chain')
            contract = position.get('token_contract')
            if not chain or not contract:
                return
            wallet_balance = await self.wallet.get_balance(chain, contract)
            if wallet_balance is None:
                # Don't reconcile if we can't get wallet balance - could be network error
                return
            wallet_balance_float = float(wallet_balance)
            discrepancy_pct = 0.0
            if expected_quantity > 0:
                discrepancy_pct = abs(wallet_balance_float - expected_quantity) / expected_quantity * 100.0
            else:
                discrepancy_pct = 100.0 if wallet_balance_float > 0 else 0.0
            if discrepancy_pct > 1.0:
                position['total_quantity'] = wallet_balance_float
                self.repo.update_position(position_id, position)
        except Exception:
            return

    async def update_total_quantity_from_wallet(self, position_id: str) -> bool:
        try:
            position = self.repo.get_position(position_id)
            if not position:
                return False
            token_contract = position.get('token_contract')
            token_chain = position.get('token_chain')
            if not token_contract or not token_chain:
                return False
            wallet_balance = await self.wallet.get_balance(token_chain, token_contract)
            wallet_balance_float = float(wallet_balance) if wallet_balance else 0.0
            position['total_quantity'] = wallet_balance_float
            ok = self.repo.update_position(position_id, position)
            return bool(ok)
        except Exception:
            return False

    # ------------------------------
    # Position aggregate update methods (missing from original implementation)
    # ------------------------------
    async def _update_tokens_bought(self, position_id: str, tokens_bought: float) -> bool:
        """Update total_tokens_bought when an entry is executed"""
        try:
            position = self.repo.get_position(position_id)
            if not position:
                return False
            
            # Add tokens bought to total (handle None values)
            current_total = position.get('total_tokens_bought', 0.0) or 0.0
            new_total = current_total + tokens_bought
            position['total_tokens_bought'] = new_total
            
            # Update position in database
            success = self.repo.update_position(position_id, position)
            if success:
                trading_logger.info(f"Updated total_tokens_bought for {position_id}: {current_total:.8f} -> {new_total:.8f} (+{tokens_bought:.8f})")
                
                # Post-write verification
                await self._verify_entry_aggregates(position_id, tokens_bought)
            return success
            
        except Exception as e:
            trading_logger.error(f"Error updating total_tokens_bought for position {position_id}: {e}")
            return False

    async def _update_total_investment_native(self, position_id: str, amount_native: float) -> bool:
        """Update total_investment_native when an entry is executed"""
        try:
            position = self.repo.get_position(position_id)
            if not position:
                return False
            
            # Add native amount invested to total (handle None values)
            current_total = position.get('total_investment_native', 0.0) or 0.0
            new_total = current_total + amount_native
            position['total_investment_native'] = new_total
            
            # Calculate avg_entry_price from totals
            total_tokens = position.get('total_tokens_bought', 0.0) or 0.0
            if total_tokens > 0:
                position['avg_entry_price'] = new_total / total_tokens
            else:
                position['avg_entry_price'] = 0.0
            
            # Update position in database
            success = self.repo.update_position(position_id, position)
            if success:
                trading_logger.info(f"Updated total_investment_native for {position_id}: {current_total:.8f} -> {new_total:.8f} (+{amount_native:.8f})")
                trading_logger.info(f"Calculated avg_entry_price: {position['avg_entry_price']:.8f}")
            return success
            
        except Exception as e:
            trading_logger.error(f"Error updating total_investment_native for position {position_id}: {e}")
            return False

    async def _update_position_pnl(self, position_id: str) -> bool:
        """Update position P&L using current market prices"""
        try:
            position = self.repo.get_position(position_id)
            if not position:
                return False
            
            # Get current price from database
            token_contract = position.get('token_contract')
            token_chain = position.get('token_chain', '').lower()
            if not token_contract or not token_chain:
                return False
                
            current_price = await self.get_current_price_native_from_db(token_contract, token_chain)
            if current_price is None:
                trading_logger.warning(f"Could not get current price for {token_contract} on {token_chain}")
                return False
            
            # Calculate P&L
            total_quantity = float(position.get('total_quantity', 0.0) or 0.0)
            total_investment = float(position.get('total_investment_native', 0.0) or 0.0)
            total_extracted = float(position.get('total_extracted_native', 0.0) or 0.0)
            
            current_position_value = total_quantity * current_price
            total_pnl_native = (total_extracted + current_position_value) - total_investment
            
            # Get SOL/USD rate for USD P&L
            native_usd_rate = await self.get_native_usd_rate_async(token_chain)
            total_pnl_usd = total_pnl_native * native_usd_rate
            total_pnl_pct = (total_pnl_native / total_investment * 100.0) if total_investment > 0 else 0.0
            
            # Update position
            position['total_pnl_native'] = total_pnl_native
            position['total_pnl_usd'] = total_pnl_usd
            position['total_pnl_pct'] = total_pnl_pct
            
            success = self.repo.update_position(position_id, position)
            if success:
                trading_logger.info(f"Updated P&L for {position_id}: {total_pnl_pct:.2f}% (${total_pnl_usd:.2f})")
            return success
            
        except Exception as e:
            trading_logger.error(f"Error updating P&L for position {position_id}: {e}")
            return False

    async def _update_position_pnl_in_memory(self, position: Dict[str, Any]) -> None:
        """Update position P&L in memory without database write"""
        try:
            # Get current market price
            token_contract = position.get('token_contract')
            token_chain = position.get('token_chain', '').lower()
            if not token_contract or not token_chain:
                return
                
            current_price = await self.get_current_price_native_from_db(token_contract, token_chain)
            if current_price is None:
                return
            
            # Calculate P&L
            total_quantity = float(position.get('total_quantity', 0.0) or 0.0)
            total_investment = float(position.get('total_investment_native', 0.0) or 0.0)
            total_extracted = float(position.get('total_extracted_native', 0.0) or 0.0)
            
            current_position_value = total_quantity * current_price
            total_pnl_native = (total_extracted + current_position_value) - total_investment
            
            # Get SOL/USD rate for USD P&L
            native_usd_rate = await self.get_native_usd_rate_async(token_chain)
            total_pnl_usd = total_pnl_native * native_usd_rate
            total_pnl_pct = (total_pnl_native / total_investment * 100.0) if total_investment > 0 else 0.0
            
            # Update position in memory
            position['total_pnl_native'] = total_pnl_native
            position['total_pnl_usd'] = total_pnl_usd
            position['total_pnl_pct'] = total_pnl_pct
            
        except Exception as e:
            trading_logger.error(f"Error updating P&L in memory: {e}")

    async def _update_wallet_balance_after_trade(self, chain: str):
        """Update wallet balance in database after a trade execution"""
        try:
            # Get current native token balance for this chain
            current_balance = await self.wallet.get_balance(chain)
            if current_balance is not None:
                await self._store_native_balance(chain, float(current_balance))
                trading_logger.info(f"Updated {chain} wallet balance after trade: {float(current_balance):.6f}")
            else:
                trading_logger.warning(f"Could not get current balance for {chain} after trade")
                
        except Exception as e:
            trading_logger.error(f"Error updating wallet balance for {chain} after trade: {e}")

    async def _store_native_balance(self, chain: str, balance: float):
        """Store/update native token balance in database for portfolio tracking"""
        try:
            # Get USD value if possible
            balance_usd = None
            if chain in ['ethereum', 'base']:
                eth_rate = await self._get_native_usd_rate('ethereum')
                balance_usd = float(balance) * eth_rate if eth_rate > 0 else None
            elif chain == 'bsc':
                bnb_rate = await self._get_native_usd_rate('bsc')
                balance_usd = float(balance) * bnb_rate if bnb_rate > 0 else None
            elif chain == 'solana':
                sol_rate = await self._get_native_usd_rate('solana')
                balance_usd = float(balance) * sol_rate if sol_rate > 0 else None
            
            # Upsert balance (insert or update)
            self.repo.client.table('wallet_balances').upsert({
                'chain': chain,
                'balance': float(balance),
                'balance_usd': balance_usd,
                'wallet_address': self.wallet.get_wallet_address(chain),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }).execute()
            
            trading_logger.debug(f"Updated {chain} balance: {balance:.6f}")
            
        except Exception as e:
            trading_logger.error(f"Error storing {chain} balance: {e}")

    async def _update_tokens_sold(self, position_id: str, tokens_sold: float) -> bool:
        """Update total_tokens_sold when an exit is executed"""
        try:
            position = self.repo.get_position(position_id)
            if not position:
                return False
            
            # Add tokens sold to total (handle None values)
            current_total = position.get('total_tokens_sold', 0.0) or 0.0
            new_total = current_total + tokens_sold
            position['total_tokens_sold'] = new_total
            
            # Update position in database
            success = self.repo.update_position(position_id, position)
            if success:
                trading_logger.info(f"Updated total_tokens_sold for {position_id}: {current_total:.8f} -> {new_total:.8f} (+{tokens_sold:.8f})")
                
                # Post-write verification
                await self._verify_exit_aggregates(position_id, tokens_sold)
            return success
            
        except Exception as e:
            trading_logger.error(f"Error updating total_tokens_sold for position {position_id}: {e}")
            return False

    async def _update_total_extracted_native(self, position_id: str, amount_native: float) -> bool:
        """Update total_extracted_native when an exit is executed"""
        try:
            position = self.repo.get_position(position_id)
            if not position:
                return False
            
            # Add native amount extracted to total (handle None values)
            current_total = position.get('total_extracted_native', 0.0) or 0.0
            new_total = current_total + amount_native
            position['total_extracted_native'] = new_total
            
            # Update position in database
            success = self.repo.update_position(position_id, position)
            if success:
                trading_logger.info(f"Updated total_extracted_native for {position_id}: {current_total:.8f} -> {new_total:.8f} (+{amount_native:.8f})")
            return success
            
        except Exception as e:
            trading_logger.error(f"Error updating total_extracted_native for position {position_id}: {e}")
            return False

    # ------------------------------
    # Post-write verification methods
    # ------------------------------
    async def _verify_entry_aggregates(self, position_id: str, tokens_bought: float) -> None:
        """Verify entry aggregates are consistent after update"""
        try:
            position = self.repo.get_position(position_id)
            if not position:
                return
            
            # Check that totals are positive
            total_tokens_bought = position.get('total_tokens_bought', 0.0) or 0.0
            total_investment = position.get('total_investment_native', 0.0) or 0.0
            avg_entry_price = position.get('avg_entry_price', 0.0) or 0.0
            
            if total_tokens_bought <= 0:
                trading_logger.warning(f"VERIFY: {position_id} has zero total_tokens_bought after entry")
            if total_investment <= 0:
                trading_logger.warning(f"VERIFY: {position_id} has zero total_investment after entry")
            if avg_entry_price <= 0 and total_tokens_bought > 0:
                trading_logger.warning(f"VERIFY: {position_id} has zero avg_entry_price but {total_tokens_bought} tokens")
                # Auto-recalc avg_entry_price
                position['avg_entry_price'] = total_investment / total_tokens_bought
                self.repo.update_position(position_id, position)
                trading_logger.info(f"VERIFY: Auto-corrected avg_entry_price to {position['avg_entry_price']:.8f}")
            
            # Check that exits exist if we have an avg_entry_price
            if avg_entry_price > 0:
                exits = position.get('exits', [])
                if not exits:
                    trading_logger.warning(f"VERIFY: {position_id} has avg_entry_price {avg_entry_price} but no exits")
                    # Auto-recalc exits
                    await self.recalculate_exits_after_entry(position_id)
                    trading_logger.info(f"VERIFY: Auto-recalculated exits for {position_id}")
            
            # Audit log
            trading_logger.info(f"AUDIT: Entry {position_id} | tokens_bought: {tokens_bought:.8f} | total_tokens: {total_tokens_bought:.8f} | investment: {total_investment:.8f} | avg_price: {avg_entry_price:.8f}")
            
        except Exception as e:
            trading_logger.error(f"Error in entry verification for {position_id}: {e}")

    async def _verify_exit_aggregates(self, position_id: str, tokens_sold: float) -> None:
        """Verify exit aggregates are consistent after update"""
        try:
            position = self.repo.get_position(position_id)
            if not position:
                return
            
            # Check that sold/extracted increased and quantity decreased
            total_tokens_sold = position.get('total_tokens_sold', 0.0) or 0.0
            total_extracted = position.get('total_extracted_native', 0.0) or 0.0
            total_quantity = position.get('total_quantity', 0.0) or 0.0
            total_tokens_bought = position.get('total_tokens_bought', 0.0) or 0.0
            
            # Basic consistency checks
            if total_tokens_sold > total_tokens_bought:
                trading_logger.warning(f"VERIFY: {position_id} sold {total_tokens_sold:.8f} > bought {total_tokens_bought:.8f}")
            
            expected_quantity = total_tokens_bought - total_tokens_sold
            if abs(total_quantity - expected_quantity) > 0.0001:  # Small tolerance for rounding
                trading_logger.warning(f"VERIFY: {position_id} quantity mismatch: expected {expected_quantity:.8f}, got {total_quantity:.8f}")
                # Auto-correct quantity
                position['total_quantity'] = expected_quantity
                self.repo.update_position(position_id, position)
                trading_logger.info(f"VERIFY: Auto-corrected quantity to {expected_quantity:.8f}")
            
            # Audit log
            trading_logger.info(f"AUDIT: Exit {position_id} | tokens_sold: {tokens_sold:.8f} | total_sold: {total_tokens_sold:.8f} | extracted: {total_extracted:.8f} | quantity: {total_quantity:.8f}")
            
        except Exception as e:
            trading_logger.error(f"Error in exit verification for {position_id}: {e}")

    def _build_exit_rules_from_config(self) -> Dict[str, Any]:
        """Build exit rules from config file"""
        import yaml
        import os
        
        # Load config
        config_path = os.path.join(os.path.dirname(__file__), '../../config/social_trading_config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        exit_strategy = config['position_management']['exit_strategy']
        
        stages = []
        for exit_key, exit_config in exit_strategy.items():
            if exit_key != 'final':  # Handle final exit separately
                stages.append({
                    'gain_pct': exit_config['gain_pct'],
                    'exit_pct': exit_config['exit_pct'],
                    'executed': False
                })
        
        # Add final exit
        final_config = exit_strategy['final']
        stages.append({
            'gain_pct': final_config['gain_pct'],
            'exit_pct': final_config['exit_pct'],
            'executed': False
        })
        
        return {
            'strategy': 'staged',
            'stages': stages
        }

    def _build_trend_exit_rules_from_config(self) -> Dict[str, Any]:
        """Build trend exit rules from config file (separate from regular exits)"""
        import yaml
        import os

        # Load config
        config_path = os.path.join(os.path.dirname(__file__), '../../config/social_trading_config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        trend_cfg = (config.get('position_management') or {}).get('trend_exit_strategy')
        if not trend_cfg:
            return {'strategy': 'staged', 'stages': []}

        stages: list[Dict[str, Any]] = []
        for key, rule in trend_cfg.items():
            if key != 'final':
                stages.append({
                    'gain_pct': rule['gain_pct'],
                    'exit_pct': rule['exit_pct'],
                    'executed': False
                })
        if 'final' in trend_cfg:
            final_rule = trend_cfg['final']
            stages.append({
                'gain_pct': final_rule['gain_pct'],
                'exit_pct': final_rule['exit_pct'],
                'executed': False
            })

        return {'strategy': 'staged', 'stages': stages}

    # ------------------------------
    # Position cap management
    # ------------------------------
    async def _check_and_enforce_position_cap(self) -> None:
        """Check if we have 34+ positions and close the 6 smallest by USD value"""
        try:
            # Get all active positions
            active_positions = self.repo.client.table('lowcap_positions').select('*').eq('status', 'active').execute()
            positions = active_positions.data if active_positions.data else []
            
            if len(positions) < 34:
                return  # Under cap, no action needed
            
            trading_logger.info(f"Position cap reached: {len(positions)} positions. Closing 6 smallest positions.")
            
            # Rank positions by USD value
            ranked_positions = await self._rank_positions_by_usd_value(positions)
            
            # Close the 6 smallest
            smallest_6 = ranked_positions[:6]
            for position in smallest_6:
                await self._close_position_for_cap(position)
                
        except Exception as e:
            trading_logger.error(f"Error in position cap enforcement: {e}")

    async def _rank_positions_by_usd_value(self, positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank positions by current USD value using live prices"""
        position_values = []
        
        for pos in positions:
            try:
                chain = (pos.get('token_chain') or '').lower()
                contract = pos.get('token_contract')
                total_quantity = float(pos.get('total_quantity') or 0.0)
                
                # Get latest price from DB - use price_usd directly
                price_result = self.repo.client.table('lowcap_price_data_1m').select('price_usd').eq('token_contract', contract).eq('chain', chain).order('timestamp', desc=True).limit(1).execute()
                
                if not price_result.data:
                    # Skip positions without price data
                    continue
                    
                price_usd = float(price_result.data[0]['price_usd'])
                
                # Calculate USD value directly
                usd_value = total_quantity * price_usd
                
                position_values.append({
                    'position': pos,
                    'usd_value': usd_value,
                    'total_quantity': total_quantity,
                    'price_usd': price_usd
                })
                
            except Exception as e:
                trading_logger.warning(f"Error calculating USD value for position {pos.get('id')}: {e}")
                continue
        
        # Sort by USD value (smallest first)
        position_values.sort(key=lambda x: x['usd_value'])
        return [pv['position'] for pv in position_values]

    async def _get_native_usd_rate(self, chain: str) -> float:
        """Get native->USD rate for a chain"""
        try:
            # Map chains to their native token contracts
            native_contracts = {
                'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
                'base': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',      # WETH (same as Ethereum)
                'bsc': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',       # WBNB
                'solana': 'So11111111111111111111111111111111111111112'      # SOL
            }
            
            native_contract = native_contracts.get(chain.lower())
            if not native_contract:
                trading_logger.error(f"Unknown chain for native USD rate: {chain}")
                return 0.0
            
            # Get price from database (from scheduled price collection)
            # Use the actual chain for lookup - store native prices separately for each chain
            lookup_chain = chain.lower()
            
            result = self.repo.client.table('lowcap_price_data_1m').select(
                'price_usd'
            ).eq('token_contract', native_contract).eq('chain', lookup_chain).order(
                'timestamp', desc=True
            ).limit(1).execute()
            
            if result.data:
                return float(result.data[0].get('price_usd', 0))
            else:
                trading_logger.warning(f"No native USD rate found in database for {chain}")
                return 0.0
                
        except Exception as e:
            trading_logger.error(f"Error getting native USD rate for {chain}: {e}")
            return 0.0

    async def _close_position_for_cap(self, position: Dict[str, Any]) -> None:
        """Close a position for cap management"""
        try:
            position_id = position.get('id')
            token_ticker = position.get('token_ticker', 'UNKNOWN')
            total_quantity = float(position.get('total_quantity') or 0.0)
            
            if total_quantity == 0:
                # No tokens to sell, just mark as closed
                position['status'] = 'closed'
                position['close_reason'] = 'cap_cleanup_qty_zero'
                position['closed_at'] = datetime.now(timezone.utc).isoformat()
                
                success = self.repo.update_position(position_id, position)
                if success:
                    trading_logger.info(f"Closed position {token_ticker} ({position_id}) - zero quantity")
                else:
                    trading_logger.error(f"Failed to close position {token_ticker} ({position_id}) - zero quantity")
                return
            
            # Get current price for full sell
            chain = (position.get('token_chain') or '').lower()
            contract = position.get('token_contract')
            
            price_result = self.repo.client.table('lowcap_price_data_1m').select('price_native').eq('token_contract', contract).eq('chain', chain).order('timestamp', desc=True).limit(1).execute()
            
            if not price_result.data:
                # No price data, skip sell but don't close
                trading_logger.warning(f"Skipping sell for {token_ticker} ({position_id}) - no price data")
                return
            
            # Execute full sell (100% of remaining tokens)
            trading_logger.info(f"Executing full sell for {token_ticker} ({position_id}) - {total_quantity} tokens")
            
            # Execute full sell using the working execute_exit method
            success = await self._execute_full_sell_for_cap(position_id, total_quantity, chain, contract, token_ticker)
            
            if success:
                trading_logger.info(f"Successfully closed position {token_ticker} ({position_id}) for cap management")
            else:
                trading_logger.error(f"Failed to close position {token_ticker} ({position_id}) for cap management")
                
        except Exception as e:
            trading_logger.error(f"Error closing position {position.get('id')} for cap: {e}")

    async def _execute_full_sell_for_cap(self, position_id: str, total_quantity: float, chain: str, contract: str, token_ticker: str) -> bool:
        """Execute a full sell for cap management using the working execute_exit method"""
        try:
            # Get current price for target
            price_result = self.repo.client.table('lowcap_price_data_1m').select('price_native').eq('token_contract', contract).eq('chain', chain).order('timestamp', desc=True).limit(1).execute()
            if not price_result.data:
                trading_logger.error(f"No price data for {token_ticker} cap sell")
                return False
            
            price_native = float(price_result.data[0]['price_native'])
            
            # Use the working execute_exit method with 100% sell
            trading_logger.info(f"Executing cap sell via execute_exit: {total_quantity} {token_ticker} at {price_native:.8f} {chain.upper()}")
            
            result = await self.execute_exit(
                position_id=position_id,
                chain=chain,
                contract=contract,
                token_ticker=token_ticker,
                exit_number=999,  # Special exit number for cap cleanup
                tokens_to_sell=total_quantity,
                target_price_native=price_native
            )
            
            if result:  # result is the tx_hash string
                trading_logger.info(f"Cap sell successful for {token_ticker}: {result}")
                return True
            else:  # result is None
                trading_logger.error(f"Cap sell failed for {token_ticker}: No transaction hash returned")
                return False
                
        except Exception as e:
            trading_logger.error(f"Error executing cap sell for {token_ticker}: {e}")
            return False


