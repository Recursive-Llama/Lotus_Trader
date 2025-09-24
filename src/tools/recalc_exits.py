#!/usr/bin/env python3
"""
One-off admin tool to recalculate exits for all active positions.

Actions:
- Optionally enforce first take-profit stage to +60% (updates per-position exit_rules)
- Recalculate pending exits using TraderLowcapSimple._recalculate_exits

Run:
  source .venv/bin/activate && python src/tools/recalc_exits.py --enforce-60
"""

import asyncio
import argparse
import logging
from datetime import datetime, timezone

from utils.supabase_manager import SupabaseManager
from intelligence.trader_lowcap.trader_lowcap_simple_v2 import TraderLowcapSimpleV2

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


async def main(enforce_first_stage_60: bool = False):
    sb = SupabaseManager()
    trader = TraderLowcapSimpleV2(sb)

    # Fetch active positions
    res = sb.client.table('lowcap_positions').select('id, exit_rules').eq('status', 'active').order('created_at', desc=True).execute()
    positions = res.data or []
    logger.info(f"Found {len(positions)} active positions")

    updated = 0
    recalculated = 0

    for pos in positions:
        pid = pos.get('id')
        if not pid:
            continue

        try:
            # Optionally mutate exit_rules to first TP at +60%
            if enforce_first_stage_60:
                exit_rules = pos.get('exit_rules') or {'strategy': 'staged', 'stages': []}
                stages = exit_rules.get('stages') or []
                if not stages:
                    # Seed default stages if missing
                    stages = [
                        {'gain_pct': 60, 'exit_pct': 30, 'executed': False},
                        {'gain_pct': 200, 'exit_pct': 30, 'executed': False},
                        {'gain_pct': 300, 'exit_pct': 30, 'executed': False},
                        {'gain_pct': 400, 'exit_pct': 30, 'executed': False},
                        {'gain_pct': 500, 'exit_pct': 30, 'executed': False},
                        {'gain_pct': 600, 'exit_pct': 30, 'executed': False},
                        {'gain_pct': 1000, 'exit_pct': 100, 'executed': False}
                    ]
                else:
                    # Force first stage to 60%
                    stages[0]['gain_pct'] = 60
                exit_rules['stages'] = stages
                sb.client.table('lowcap_positions').update({'exit_rules': exit_rules, 'updated_at': datetime.now(timezone.utc).isoformat()}).eq('id', pid).execute()
                updated += 1
                logger.info(f"Updated exit_rules to +60% first TP for {pid}")

            # Recalculate exits using trader logic
            await trader._recalculate_exits(pid)
            recalculated += 1
        except Exception as e:
            logger.error(f"Error processing {pid}: {e}")

    logger.info(f"Completed. Rules updated: {updated}, Exits recalculated: {recalculated}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Recalculate exits for active positions')
    parser.add_argument('--enforce-60', action='store_true', help='Set first take-profit stage to +60% before recalculation')
    args = parser.parse_args()

    asyncio.run(main(enforce_first_stage_60=args.enforce_60))


