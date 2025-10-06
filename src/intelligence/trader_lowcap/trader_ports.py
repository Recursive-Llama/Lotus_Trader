"""
Lightweight Ports, DTOs, and in-process Events for Trader Lowcap V2 refactor.

This module defines:
- Data Transfer Objects (DTOs) used across use cases
- Ports (interfaces) that abstract external dependencies
- A minimal in-process synchronous event dispatcher

Note: Keep this file small and dependency-free to avoid circular imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional, Dict, Any


# =====================
# DTOs
# =====================

@dataclass(frozen=True)
class PriceQuote:
    token_contract: str
    chain: str
    price_native: float
    price_usd: Optional[float]
    native_symbol: str
    timestamp_iso: Optional[str] = None


@dataclass(frozen=True)
class TradeResult:
    success: bool
    tx_hash: Optional[str]
    cost_native: float
    cost_usd: Optional[float]
    error: Optional[str] = None


@dataclass(frozen=True)
class EntryPlan:
    entry_number: int
    amount_native: float
    price_native: float


@dataclass(frozen=True)
class ExitPlan:
    exit_number: int
    tokens_pct: float
    price_native: float


@dataclass(frozen=True)
class TotalsSnapshot:
    total_tokens_bought: float
    total_tokens_sold: float
    total_investment_native: float
    total_extracted_native: float
    total_pnl_native: float
    total_pnl_usd: float
    total_pnl_pct: float


@dataclass(frozen=True)
class PositionSnapshot:
    id: str
    token_chain: str
    token_contract: str
    token_ticker: str
    total_quantity: float
    avg_entry_price: Optional[float]
    avg_exit_price: Optional[float]
    total_tokens_bought: float
    total_tokens_sold: float
    total_investment_native: float
    total_extracted_native: float
    total_pnl_native: float
    total_pnl_usd: float
    total_pnl_pct: float


# =====================
# Ports (Interfaces)
# =====================

class PriceProvider(Protocol):
    def get_token_price(self, contract: str, chain: str) -> Optional[PriceQuote]:
        ...

    def get_native_usd_rate(self, chain: str) -> float:
        ...


class TradeExecutor(Protocol):
    def execute_buy(self, token_address: str, amount_native: float) -> Optional[str]:
        ...

    def execute_sell(self, token_address: str, tokens_to_sell: float, target_price_native: float) -> Optional[str]:
        ...


class Wallet(Protocol):
    async def get_balance(self, chain: str, token_contract: Optional[str] = None) -> float:
        ...


class PositionRepository(Protocol):
    # Minimal set; implemented by existing repository with same semantics
    def get_position(self, position_id: str) -> Optional[Dict[str, Any]]:
        ...

    def update_position(self, position_id: str, position: Dict[str, Any]) -> bool:
        ...

    def update_entries(self, position_id: str, entries: List[Dict[str, Any]]) -> bool:
        ...

    def update_exits(self, position_id: str, exits: List[Dict[str, Any]]) -> bool:
        ...

    # Grouped commit helpers (optional; can be thin wrappers around existing methods)
    def commit_entry_executed(self, position_id: str, entry_number: int, cost_native: float, cost_usd: float, tokens_bought: float) -> bool:
        ...

    def commit_exit_executed(self, position_id: str, exit_number: int, cost_native: float, cost_usd: float, tokens_sold: float) -> bool:
        ...

