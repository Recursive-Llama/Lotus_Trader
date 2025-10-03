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
                 sol_executor=None) -> None:
        self.events = EventBus()
        self.price_provider = _PriceProviderAdapter(repo, price_oracle)
        self.wallet = wallet
        self.repo = repo
        self.executor = _TradeExecutorAdapter(
            base_executor=base_executor,
            bsc_executor=bsc_executor,
            eth_executor=eth_executor,
            sol_executor=sol_executor,
        )

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
            batch_id = f"trend-{position_id}"
            trend_entries = EntryExitPlanner.build_trend_entries_from_standard_exit(
                exit_price=exit_price,
                exit_native_amount=native_amount,
                source_exit_id=source_exit_number,
                batch_id=batch_id,
            )
            position = self.repo.get_position(position_id) or {}
            existing = position.get('trend_entries', []) or []
            existing.extend(trend_entries)
            self.repo.update_trend_entries(position_id, existing)
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


