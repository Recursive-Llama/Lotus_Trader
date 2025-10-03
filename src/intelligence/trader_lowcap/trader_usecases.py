"""
Use-case orchestrations for Trader Lowcap V2.

Each use case depends only on ports and DTOs from trader_ports.
Side effects (DB writes, executions) are invoked via ports; no direct infra calls here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .trader_ports import (
    PriceProvider,
    TradeExecutor,
    Wallet,
    PositionRepository,
    EventBus,
)


@dataclass
class ExecuteExitRequest:
    position_id: str
    chain: str
    contract: str
    token_ticker: str
    exit_number: int
    tokens_to_sell: float
    target_price_native: float


class ExecuteExit:
    def __init__(self, price_provider: PriceProvider, executor: TradeExecutor, wallet: Wallet, repo: PositionRepository, events: EventBus) -> None:
        self.price_provider = price_provider
        self.executor = executor
        self.wallet = wallet
        self.repo = repo
        self.events = events

    def __call__(self, req: ExecuteExitRequest) -> Optional[str]:
        # Execute sell and return tx hash; state updates remain in legacy flow
        return self.executor.execute_sell(req.contract, req.tokens_to_sell, req.target_price_native)


@dataclass
class ExecuteEntryRequest:
    position_id: str
    chain: str
    contract: str
    token_ticker: str
    entry_number: int
    amount_native: float
    price_native: float


class ExecuteEntry:
    def __init__(self, price_provider: PriceProvider, executor: TradeExecutor, wallet: Wallet, repo: PositionRepository, events: EventBus) -> None:
        self.price_provider = price_provider
        self.executor = executor
        self.wallet = wallet
        self.repo = repo
        self.events = events

    def __call__(self, req: ExecuteEntryRequest) -> Optional[str]:
        # Execute buy with native amount; state updates remain in legacy flow
        return self.executor.execute_buy(req.contract, req.amount_native)


@dataclass
class ExecuteBuybackRequest:
    chain: str
    exit_value_native: float
    enabled: bool
    percentage: float
    min_amount_native: float


class ExecuteBuyback:
    """Calculates buyback amount and threshold. Does not perform swaps."""

    def __init__(self, price_provider: PriceProvider) -> None:
        self.price_provider = price_provider

    def __call__(self, req: ExecuteBuybackRequest) -> dict:
        if req.chain.lower() != 'solana':
            return {'success': True, 'skipped': True, 'reason': 'Not a SOL exit'}
        if not req.enabled:
            return {'success': True, 'skipped': True, 'reason': 'Buyback disabled'}
        buyback_amount = float(req.exit_value_native) * (req.percentage / 100.0)
        if buyback_amount < req.min_amount_native:
            return {
                'success': True,
                'skipped': True,
                'reason': f'Below minimum threshold ({req.min_amount_native})',
                'buyback_amount_native': buyback_amount,
            }
        return {
            'success': True,
            'skipped': False,
            'buyback_amount_native': buyback_amount,
        }


