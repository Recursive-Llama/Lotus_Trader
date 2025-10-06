"""
Trader Service: wires existing collaborators behind ports and exposes use cases.

This module does not change behavior; it only adapts current objects to the
ports defined in trader_ports and invokes use cases from trader_usecases.
"""

from __future__ import annotations

from typing import Optional

from .trader_ports import PriceProvider, TradeExecutor, Wallet, PositionRepository, EventBus, PriceQuote
from .trader_usecases import ExecuteExit, ExecuteExitRequest, ExecuteEntry, ExecuteEntryRequest, ExecuteBuyback, ExecuteBuybackRequest
from .entry_exit_planner import EntryExitPlanner
from . import trader_views
from .trading_logger import trading_logger


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
        self.events = EventBus()
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

        # Use cases (instantiate once)
        self._execute_exit_uc = ExecuteExit(
            price_provider=self.price_provider,
            executor=self.executor,
            wallet=self.wallet,
            repo=self.repo,
            events=self.events,
        )
        self._execute_entry_uc = ExecuteEntry(
            price_provider=self.price_provider,
            executor=self.executor,
            wallet=self.wallet,
            repo=self.repo,
            events=self.events,
        )
        self._execute_buyback_uc = ExecuteBuyback(
            price_provider=self.price_provider,
        )

    def execute_exit(self, *, position_id: str, chain: str, contract: str, token_ticker: str, exit_number: int, tokens_to_sell: float, target_price_native: float) -> Optional[str]:
        req = ExecuteExitRequest(
            position_id=position_id,
            chain=chain,
            contract=contract,
            token_ticker=token_ticker,
            exit_number=exit_number,
            tokens_to_sell=tokens_to_sell,
            target_price_native=target_price_native,
        )
        return self._execute_exit_uc(req)

    def execute_entry(self, *, position_id: str, chain: str, contract: str, token_ticker: str, entry_number: int, amount_native: float, price_native: float) -> Optional[str]:
        req = ExecuteEntryRequest(
            position_id=position_id,
            chain=chain,
            contract=contract,
            token_ticker=token_ticker,
            entry_number=entry_number,
            amount_native=amount_native,
            price_native=price_native,
        )
        return self._execute_entry_uc(req)

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
            return batch_id
        except Exception:
            return None

    def plan_buyback(self, *, chain: str, exit_value_native: float, enabled: bool, percentage: float, min_amount_native: float) -> dict:
        req = ExecuteBuybackRequest(
            chain=chain,
            exit_value_native=exit_value_native,
            enabled=enabled,
            percentage=percentage,
            min_amount_native=min_amount_native,
        )
        return self._execute_buyback_uc(req)

    def perform_buyback(self, *, lotus_contract: str, holding_wallet: str, buyback_amount_native: float, slippage_pct: float = 5.0) -> dict:
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

            # Execute Jupiter swap
            result = self._js_solana_client.execute_jupiter_swap_sync(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint=lotus_contract,
                amount=lamports,
                slippage_bps=slippage_bps,
            ) if hasattr(self._js_solana_client, 'execute_jupiter_swap_sync') else None

            if result is None:
                return {'success': False, 'error': 'Sync Jupiter swap not available'}

            if result.get('success', False):
                output_amount = result.get('outputAmount', 0)
                lotus_amount_tokens = float(output_amount) / 1_000_000_000

                # Transfer Lotus tokens to holding wallet
                transfer = self._js_solana_client.send_lotus_tokens_sync(lotus_amount_tokens, holding_wallet) \
                    if hasattr(self._js_solana_client, 'send_lotus_tokens_sync') else None

                if transfer and transfer.get('success'):
                    return {
                        'success': True,
                        'skipped': False,
                        'buyback_amount_sol': buyback_amount_native,
                        'lotus_tokens': lotus_amount_tokens,
                        'transfer_tx_hash': result.get('signature', ''),
                        'holding_wallet': holding_wallet,
                    }
                return {'success': False, 'error': 'Transfer failed'}

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
        try:
            token = (decision.get('signal_pack') or {}).get('token') or {}
            chain = (token.get('chain') or '').lower()
            ticker = token.get('ticker')
            contract = token.get('contract')
            allocation_pct = float((decision.get('content', {}) or {}).get('allocation_pct') or 0)
            
            # Log decision attempt
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
                trading_logger.log_decision_rejection(
                    token=ticker or 'UNKNOWN',
                    reason='action_not_approve',
                    details={'action': decision.get('content', {}).get('action')}
                )
                return None

            # idempotency
            existing_for_book = self.repo.get_position_by_book_id(decision.get('id'))
            if existing_for_book:
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
                trading_logger.log_decision_rejection(
                    token=ticker or 'UNKNOWN',
                    reason='unsupported_chain',
                    details={'chain': chain}
                )
                return None

            if not balance or float(balance) <= 0:
                trading_logger.log_trade_failure(
                    chain=chain,
                    token=ticker or 'UNKNOWN',
                    reason='insufficient_balance',
                    details={'balance': balance, 'required': '> 0'}
                )
                return None
            alloc_native = (allocation_pct * float(balance)) / 100.0
            if alloc_native <= 0 or not price:
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
            }
            if not self.repo.create_position(position):
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

            # first buy
            e_amt = alloc_native / 3.0
            tx_hash = None
            if chain in ('bsc','base') and executor:
                v = self.resolve_bsc_venue(contract) if chain=='bsc' else self.resolve_base_venue(contract)
                tx_hash = executor.execute_buy(contract, e_amt, venue=v)
            elif chain == 'ethereum' and executor:
                tx_hash = executor.execute_buy(contract, e_amt)
            elif chain == 'solana' and executor:
                tx_hash = await executor.execute_buy(contract, e_amt)
            if not tx_hash:
                trading_logger.log_trade_failure(
                    chain=chain,
                    token=ticker or 'UNKNOWN',
                    reason='transaction_execution_failed',
                    details={'executor': executor is not None, 'amount': e_amt}
                )
                return None
            
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
            wallet_balance_float = float(wallet_balance) if wallet_balance else 0.0
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
            sol_usd_rate = await self.get_native_usd_rate_async('solana') if token_chain == 'solana' else 1.0
            total_pnl_usd = total_pnl_native * sol_usd_rate
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


