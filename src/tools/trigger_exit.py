#!/usr/bin/env python3
"""
Trigger the first pending exit for a position by contract address.

Usage:
  source .venv/bin/activate && PYTHONPATH=src python src/tools/trigger_exit.py --contract <SOL_MINT>

Optional:
  --exit <N>  Specify a particular exit_number to execute
"""

import asyncio
import argparse
import logging
from typing import Optional

from utils.supabase_manager import SupabaseManager
from intelligence.trader_lowcap.trader_lowcap_simple_v2 import TraderLowcapSimpleV2

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


async def trigger_exit_by_contract(contract: str, exit_number: Optional[int] = None):
    sb = SupabaseManager()
    trader = TraderLowcapSimpleV2(sb)

    # Find active position for this contract on Solana
    res = sb.client.table('lowcap_positions').select('*').eq('status', 'active').eq('token_chain', 'solana').eq('token_contract', contract).order('created_at', desc=True).execute()
    positions = res.data or []
    if not positions:
        logger.error(f"No active Solana position found for contract {contract}")
        return

    pos = positions[0]
    position_id = pos['id']
    exits = pos.get('exits', []) or []

    if exit_number is None:
        # Pick the first pending exit by lowest exit_number
        pending = [e for e in exits if e.get('status') == 'pending']
        if not pending:
            logger.error(f"No pending exits for position {position_id}")
            return
        exit_number = min(e.get('exit_number') for e in pending)

    logger.info(f"Triggering exit {exit_number} for position {position_id} ({contract})")
    success = await trader._execute_exit(position_id, exit_number)
    if success:
        logger.info(f"✅ Exit {exit_number} executed for {position_id}")
    else:
        logger.error(f"❌ Failed to execute exit {exit_number} for {position_id}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Trigger pending exit for a Solana position by contract')
    parser.add_argument('--contract', required=True, help='Solana token mint address')
    parser.add_argument('--exit', type=int, default=None, help='Exit number to execute (optional)')
    args = parser.parse_args()

    asyncio.run(trigger_exit_by_contract(args.contract, args.exit))


