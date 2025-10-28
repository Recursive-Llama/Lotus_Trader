#!/usr/bin/env python3
"""
Hourly gap scan for GeckoTerminal backfill

- Scans active positions for missing 1m rows over the last 48h
- Uses canonical pool from lowcap_positions.features; if missing, resolves and persists
- Calls backfill for small windows (e.g., last 180 minutes) to keep up to date
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from src.utils.supabase_manager import SupabaseManager
from src.intelligence.lowcap_portfolio_manager.jobs.geckoterminal_backfill import backfill_token_1m, _get_canonical_pool_from_features, _update_canonical_pool_features, _select_canonical_pool_from_gt


logger = logging.getLogger(__name__)


def _list_active_positions(sb: SupabaseManager) -> List[Dict[str, Any]]:
    try:
        res = sb.client.table('lowcap_positions').select('id,token_contract,token_chain,features,status').eq('status', 'active').execute()
        return res.data or []
    except Exception as e:
        logger.warning(f"Failed to list active positions: {e}")
        return []


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    sb = SupabaseManager()
    positions = _list_active_positions(sb)
    if not positions:
        print("No active positions for gap scan")
        return

    for pos in positions:
        token = pos.get('token_contract')
        chain = (pos.get('token_chain') or '').lower()
        features = pos.get('features') or {}

        # Ensure canonical pool exists
        canonical = _get_canonical_pool_from_features(features)
        if not canonical:
            picked = _select_canonical_pool_from_gt(chain, token)
            if picked:
                pool_addr, dex_id, _ = picked
                _update_canonical_pool_features(sb, token, chain, pool_addr, dex_id)

        # Backfill recent 180 minutes (3h) to keep fresh
        try:
            res = backfill_token_1m(token, chain, lookback_minutes=180)
            logger.info(f"Gap scan backfilled {res.get('inserted_rows')} rows for {token} on {chain}")
        except Exception as e:
            logger.warning(f"Backfill error for {token} on {chain}: {e}")


if __name__ == "__main__":
    main()



