#!/usr/bin/env python3
"""
Manual EVM Trade Injector

Creates a decision_lowcap strand for an EVM token (ethereum/base) with a target
allocation in native units (e.g., 0.001 ETH), inserts it into the database, and
triggers the trade via a standalone UniversalLearningSystem instance.

Usage:
  python -m src.tools.manual_evm_trade_injector --chain ethereum \
      --ticker XMW --contract 0x391cF4b21F557c935C7f670218Ef42C21bd8d686 \
      --allocation_native 0.001 --curator cryptotrissy

  python -m src.tools.manual_evm_trade_injector --chain base \
      --ticker HYDX --contract 0x00000e7efa313f4e11bfff432471ed9423ac6b30 \
      --allocation_native 0.001 --curator cryptotrissy
"""

import argparse
import asyncio
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv

from src.utils.supabase_manager import SupabaseManager
from src.intelligence.universal_learning.universal_learning_system import UniversalLearningSystem
from src.trading.wallet_manager import WalletManager


def _build_decision_strand(
    chain: str,
    ticker: str,
    contract: str,
    curator_id: str,
    allocation_pct: float,
) -> dict:
    now_iso = datetime.now(timezone.utc).isoformat()
    strand_id = str(uuid.uuid4())

    # Minimal-but-complete token/venue info expected by Trader/DM
    token = {
        'ticker': ticker,
        'contract': contract,
        'chain': chain,
        'price': 0.0,  # Trader fetches real price later
        'volume_24h': 100000.0,  # pass DM thresholds
        'market_cap': 0.0,
        'liquidity': 50000.0,
        'dex': '0x',
        'verified': True,
    }
    venue = {
        'dex': '0x',
        'chain': chain,
        'liq_usd': token['liquidity'],
        'vol24h_usd': token['volume_24h'],
    }
    curator = {
        'id': curator_id,
        'name': curator_id,
        'platform': 'twitter',
        'handle': f'@{curator_id}',
        'weight': 0.6,
        'priority': 'medium',
        'tags': ['manual_test']
    }

    decision = {
        'id': strand_id,
        'module': 'decision_maker_lowcap',
        'kind': 'decision_lowcap',
        'symbol': ticker,
        'session_bucket': f"manual_{datetime.now(timezone.utc).strftime('%Y%m%d_%H')}",
        'parent_id': None,
        'signal_pack': {
            'token': token,
            'venue': venue,
            'curator': curator,
            'trading_signals': {'action': 'buy', 'timing': None, 'confidence': 0.8},
        },
        'module_intelligence': {'source': 'manual_injector'},
        'sig_confidence': 0.8,
        'sig_direction': 'buy',
        'confidence': 0.8,
        'content': {
            'source_kind': 'social_lowcap',
            'source_strand_id': None,
            'curator_id': curator_id,
            'token': token,
            'venue': venue,
            'action': 'approve',
            'allocation_pct': allocation_pct,
            'curator_confidence': 0.6,
            'reasoning': f'Manual approval for {ticker} on {chain} (allocation {allocation_pct:.4f}%)',
        },
        'tags': ['decision', 'social_lowcap', 'approved', 'simple', 'manual'],
        'status': 'active',
        'created_at': now_iso,
        'updated_at': now_iso,
    }

    return decision


async def main():
    # Load environment
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument('--chain', required=True, choices=['ethereum', 'base'])
    parser.add_argument('--ticker', required=True)
    parser.add_argument('--contract', required=True)
    parser.add_argument('--allocation_native', type=float, required=True, help='Native units to allocate (e.g., 0.001)')
    parser.add_argument('--curator', default='cryptotrissy')
    args = parser.parse_args()

    supabase = SupabaseManager()
    learning = UniversalLearningSystem(supabase_manager=supabase)
    wallet = WalletManager()

    # Compute allocation_pct based on live wallet balance
    native_balance = await wallet.get_balance(args.chain)
    if not native_balance or float(native_balance) <= 0:
        raise RuntimeError(f'No native balance for {args.chain}.')
    allocation_pct = (args.allocation_native / float(native_balance)) * 100.0

    decision = _build_decision_strand(
        chain=args.chain,
        ticker=args.ticker,
        contract=args.contract,
        curator_id=args.curator,
        allocation_pct=allocation_pct,
    )

    # Insert strand then trigger trader via learning system
    created = await supabase.create_strand(decision)
    # Let learning system process the decision (will call Trader)
    await learning.process_strand_event(created)

    print('Injected and processed decision:', created.get('id'))


if __name__ == '__main__':
    asyncio.run(main())


