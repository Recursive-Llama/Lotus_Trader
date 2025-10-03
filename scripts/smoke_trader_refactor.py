#!/usr/bin/env python3
"""
Non-invasive smoke test for refactored trader use cases.

Uses stubbed adapters (no RPC/DB/real trades). Verifies that:
- ExecuteEntry and ExecuteExit return mock tx hashes
- Trend batch planning produces entries
- Buyback planning calculates thresholds for SOL

Run: python scripts/smoke_trader_refactor.py
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from src.intelligence.trader_lowcap.trader_ports import (
    PriceProvider,
    TradeExecutor,
    Wallet,
    PositionRepository,
    PriceQuote,
)
from src.intelligence.trader_lowcap.trader_usecases import (
    ExecuteEntry,
    ExecuteEntryRequest,
    ExecuteExit,
    ExecuteExitRequest,
    ExecuteBuyback,
    ExecuteBuybackRequest,
)
from src.intelligence.trader_lowcap.entry_exit_planner import EntryExitPlanner


class StubPriceProvider(PriceProvider):
    def __init__(self, price_native: float = 0.0005, price_usd: float = 0.001, native_symbol: str = 'ETH') -> None:
        self.price_native = price_native
        self.price_usd = price_usd
        self.native_symbol = native_symbol

    def get_token_price(self, contract: str, chain: str) -> Optional[PriceQuote]:
        return PriceQuote(
            token_contract=contract,
            chain=chain,
            price_native=self.price_native,
            price_usd=self.price_usd,
            native_symbol=self.native_symbol,
            timestamp_iso=None,
        )

    def get_native_usd_rate(self, chain: str) -> float:
        # Fixed USD rates for smoke
        return {
            'ethereum': 3200.0,
            'base': 3200.0,
            'bsc': 500.0,
            'solana': 200.0,
        }.get(chain, 0.0)


class StubTradeExecutor(TradeExecutor):
    def execute_buy(self, token_address: str, amount_native: float) -> Optional[str]:
        return '0xMOCK_BUY_TX'

    def execute_sell(self, token_address: str, tokens_to_sell: float, target_price_native: float) -> Optional[str]:
        return '0xMOCK_SELL_TX'


class StubWallet(Wallet):
    async def get_balance(self, chain: str, token_contract: Optional[str] = None) -> float:
        return 10_000_000.0


class StubRepo(PositionRepository):
    def __init__(self) -> None:
        self.positions: Dict[str, Dict[str, Any]] = {}

    def get_position(self, position_id: str) -> Optional[Dict[str, Any]]:
        return self.positions.get(position_id)

    def update_position(self, position_id: str, position: Dict[str, Any]) -> bool:
        self.positions[position_id] = position
        return True

    def update_entries(self, position_id: str, entries: List[Dict[str, Any]]) -> bool:
        pos = self.positions.setdefault(position_id, {})
        pos['entries'] = entries
        return True

    def update_exits(self, position_id: str, exits: List[Dict[str, Any]]) -> bool:
        pos = self.positions.setdefault(position_id, {})
        pos['exits'] = exits
        return True

    def commit_entry_executed(self, position_id: str, entry_number: int, cost_native: float, cost_usd: float, tokens_bought: float) -> bool:
        pos = self.positions.setdefault(position_id, {})
        entries = pos.get('entries', [])
        for e in entries:
            if e.get('entry_number') == entry_number:
                e['status'] = 'executed'
                e['tokens_bought'] = tokens_bought
                e['cost_native'] = cost_native
                e['cost_usd'] = cost_usd
                break
        pos['total_tokens_bought'] = pos.get('total_tokens_bought', 0.0) + tokens_bought
        pos['total_investment_native'] = pos.get('total_investment_native', 0.0) + cost_native
        self.positions[position_id] = pos
        return True

    def commit_exit_executed(self, position_id: str, exit_number: int, cost_native: float, cost_usd: float, tokens_sold: float) -> bool:
        pos = self.positions.setdefault(position_id, {})
        exits = pos.get('exits', [])
        for x in exits:
            if x.get('exit_number') == exit_number:
                x['status'] = 'executed'
                x['tokens_sold'] = tokens_sold
                x['cost_native'] = cost_native
                x['cost_usd'] = cost_usd
                break
        pos['total_tokens_sold'] = pos.get('total_tokens_sold', 0.0) + tokens_sold
        pos['total_extracted_native'] = pos.get('total_extracted_native', 0.0) + cost_native
        self.positions[position_id] = pos
        return True

    # Additional helper for trend entries
    def update_trend_entries(self, position_id: str, trend_entries: List[Dict[str, Any]]) -> bool:
        pos = self.positions.setdefault(position_id, {})
        pos['trend_entries'] = trend_entries
        return True


def smoke():
    price = StubPriceProvider()
    execu = StubTradeExecutor()
    wallet = StubWallet()
    repo = StubRepo()

    # Seed a simple position
    position_id = 'TEST_ETH_1'
    repo.update_position(position_id, {
        'id': position_id,
        'token_chain': 'ethereum',
        'token_contract': '0xToken',
        'token_ticker': 'TEST',
        'total_quantity': 1000.0,
        'entries': [{'entry_number': 1, 'amount_native': 0.5, 'price': 0.0005, 'status': 'pending'}],
        'exits': [{'exit_number': 1, 'price': 0.001, 'exit_pct': 10.0, 'status': 'pending'}],
    })

    # Entry
    entry_uc = ExecuteEntry(price_provider=price, executor=execu, wallet=wallet, repo=repo, events=None)
    tx_buy = entry_uc(ExecuteEntryRequest(
        position_id=position_id,
        chain='ethereum',
        contract='0xToken',
        token_ticker='TEST',
        entry_number=1,
        amount_native=0.5,
        price_native=0.0005,
    ))
    print('BUY TX:', tx_buy)

    # Exit (sell 100 tokens @ 0.001 native)
    exit_uc = ExecuteExit(price_provider=price, executor=execu, wallet=wallet, repo=repo, events=None)
    tx_sell = exit_uc(ExecuteExitRequest(
        position_id=position_id,
        chain='ethereum',
        contract='0xToken',
        token_ticker='TEST',
        exit_number=1,
        tokens_to_sell=100.0,
        target_price_native=0.001,
    ))
    print('SELL TX:', tx_sell)

    # Trend planning from exit
    trend = EntryExitPlanner.build_trend_entries_from_standard_exit(
        exit_price=0.001,
        exit_native_amount=0.1,
        source_exit_id='1',
        batch_id='trend-TEST_ETH_1',
    )
    print('TREND ENTRIES:', len(trend))

    # Buyback planning (SOL chain)
    buyback = ExecuteBuyback(price)
    plan = buyback(ExecuteBuybackRequest(
        chain='solana',
        exit_value_native=1.0,
        enabled=True,
        percentage=10.0,
        min_amount_native=0.001,
    ))
    print('BUYBACK PLAN:', plan)


if __name__ == '__main__':
    smoke()


