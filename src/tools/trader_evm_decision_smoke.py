#!/usr/bin/env python3
"""
Trader EVM Decision Smoke Test

Creates a mock decision_lowcap strand and runs TraderLowcapSimple.execute_decision
using in-memory Supabase mocks. Uses real ETH/Base clients under the hood.

Usage:
  python -m src.tools.trader_evm_decision_smoke --chain base --token 0x... --allocation_pct 0.5
  python -m src.tools.trader_evm_decision_smoke --chain ethereum --token 0x... --allocation_pct 0.5
"""

import os
import uuid
import argparse
from datetime import datetime, timezone
from dotenv import load_dotenv

from src.intelligence.trader_lowcap.trader_lowcap_simple import TraderLowcapSimple
import asyncio


class InMemoryTable:
    def __init__(self, name: str):
        self.name = name
        self.rows = {}
        self._filter = None
        self._select_cols = None

    # Supabase-like chaining
    def insert(self, data):
        if isinstance(data, list):
            for row in data:
                key = row.get('id') or str(uuid.uuid4())
                row['id'] = key
                self.rows[key] = row
        else:
            key = data.get('id') or str(uuid.uuid4())
            data['id'] = key
            self.rows[key] = data
        return self

    def update(self, data):
        if self._filter and self._filter[0] == 'id':
            key = self._filter[1]
            if key in self.rows:
                self.rows[key].update(data)
        self._filter = None
        return self

    def select(self, cols):
        self._select_cols = cols
        return self

    def eq(self, col, val):
        self._filter = (col, val)
        return self

    def execute(self):
        if self._filter:
            col, val = self._filter
            data = [row for row in self.rows.values() if row.get(col) == val]
            self._filter = None
        else:
            data = list(self.rows.values())
        return type('Resp', (), { 'data': data })


class InMemoryClient:
    def __init__(self):
        self.tables = {}

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = InMemoryTable(name)
        return self.tables[name]


class MockSupabaseManager:
    def __init__(self):
        self.client = InMemoryClient()

    def table(self, name):
        return self.client.table(name)

    def rpc(self, function_name, params):
        return type('Resp', (), { 'data': True })


def build_mock_decision(chain: str, token: str, allocation_pct: float) -> dict:
    return {
        'id': f'decision_{uuid.uuid4()}',
        'module': 'decision_maker_lowcap',
        'kind': 'decision_lowcap',
        'tags': ['decision','social_lowcap','approved'],
        'content': {
            'action': 'approve',
            'curator_id': 'smoke_curator',
            'allocation_pct': allocation_pct,
            'allocation_usd': 0.0,
            'reasoning': 'smoke approve',
        },
        'signal_pack': {
            'token': {
                'ticker': 'SMOKE',
                'contract': token,
                'chain': chain,
            },
            'venue': {
                'dex': 'uniswap',
                'chain': chain,
                'liq_usd': 0,
            },
            'curator': {
                'id': 'smoke_curator'
            },
            'trading_signals': {
                'action': 'buy',
                'timing': 'now',
                'confidence': 0.7,
            }
        }
    }


async def run():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument('--chain', required=True, choices=['base','ethereum','solana'])
    parser.add_argument('--token', required=True)
    parser.add_argument('--allocation_pct', type=float, default=0.5)
    args = parser.parse_args()

    supa = MockSupabaseManager()
    trader = TraderLowcapSimple(supa)
    decision = build_mock_decision(args.chain, args.token, args.allocation_pct)
    print(f"mock | decision_id={decision['id']} chain={args.chain} token={args.token} alloc%={args.allocation_pct}")
    res = await trader.execute_decision(decision)
    print(f"result | {res}")


if __name__ == '__main__':
    asyncio.run(run())


