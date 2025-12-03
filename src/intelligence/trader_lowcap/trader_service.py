"""
Trader Service: v4 simplified - wires existing collaborators and exposes minimal use cases.

v4 Changes:
- Decision Maker creates 4 positions per token (1m, 15m, 1h, 4h)
- Portfolio Manager handles all execution and position state
- This service now only validates decisions and triggers backfill

Legacy methods have been archived to src/archive/trader_service_legacy_methods.py
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime, timezone

from .trader_ports import PriceProvider, TradeExecutor, Wallet, PositionRepository, PriceQuote
from . import trader_views
from .trading_logger import trading_logger
from .structured_logger import structured_logger, StateDelta, PerformanceMetrics


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
        # Not used in v4; PM calls executors directly
        return None

    def execute_sell(self, token_address: str, tokens_to_sell: float, target_price_native: float) -> Optional[str]:
        # Not used in v4; PM calls executors directly
        return None


class TraderService:
    """v4 simplified facade - validates decisions and triggers backfill.
    
    In v4:
    - Decision Maker creates 4 positions per token
    - Portfolio Manager handles all execution and position state
    - This service only validates and triggers backfill
    """

    def __init__(self, *,
                 repo,
                 price_oracle,
                 wallet,
                 base_executor=None,
                 bsc_executor=None,
                 eth_executor=None,
                 sol_executor=None,
                 js_solana_client=None,
                 trader_instance=None) -> None:
        self.price_oracle = price_oracle
        self.price_provider = _PriceProviderAdapter(repo, price_oracle)
        self.wallet = wallet
        self.repo = repo
        self._trader_instance = trader_instance
        self.executor = _TradeExecutorAdapter(
            base_executor=base_executor,
            bsc_executor=bsc_executor,
            eth_executor=eth_executor,
            sol_executor=sol_executor,
        )
        # Keep direct references for confirmations (if needed)
        self.base_executor = base_executor
        self.bsc_executor = bsc_executor
        self.eth_executor = eth_executor
        self.sol_executor = sol_executor
        self._js_solana_client = js_solana_client
        self._notifier = None

    # ------------------------------
    # Notifier integration (still useful for Telegram alerts)
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
    # Price helpers (utilities)
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
    # Venue resolvers (still useful for BSC/Base)
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
