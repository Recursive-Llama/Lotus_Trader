#!/usr/bin/env python3
"""
Verify OPAN onboarding + data/geometry state now.

Checks:
- lowcap_positions.features.canonical_pool and backfill watermark
- geometry fields present
- recent lowcap_price_data_1m rows and last timestamp
- decision_lowcap strand presence for OPAN
"""

from datetime import datetime, timezone, timedelta
import json
from typing import Any, Dict

from src.utils.supabase_manager import SupabaseManager


TOKEN_CHAIN = 'solana'
TOKEN_CONTRACT = '3Ydb2n8vAFdBJYpdiZEoDxRXLmiGDY1fuizVmMPMpump'


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def main():
    sb = SupabaseManager()
    out: Dict[str, Any] = {}

    # Position row
    try:
        pos = (
            sb.client
            .table('lowcap_positions')
            .select('*')
            .eq('token_chain', TOKEN_CHAIN)
            .eq('token_contract', TOKEN_CONTRACT)
            .order('created_at', desc=True)
            .limit(1)
            .execute()
        )
        prow = (pos.data or [None])[0]
        out['position_found'] = prow is not None
        if prow:
            feats = prow.get('features') or {}
            out['features.canonical_pool'] = feats.get('canonical_pool') if isinstance(feats, dict) else None
            bf = feats.get('backfill') if isinstance(feats, dict) else None
            out['features.backfill.last_filled_ts'] = bf.get('last_filled_ts') if isinstance(bf, dict) else None
            geom = feats.get('geometry') if isinstance(feats, dict) else None
            out['features.geometry.sample'] = {
                'sr_conf': geom.get('sr_conf') if isinstance(geom, dict) else None,
                'sr_break': geom.get('sr_break') if isinstance(geom, dict) else None,
                'diag_break': geom.get('diag_break') if isinstance(geom, dict) else None,
                'ema_long': geom.get('ema_long') if isinstance(geom, dict) else None,
                'rsi_div_bull': geom.get('rsi_divergence_bull') if isinstance(geom, dict) else None,
                'rsi_div_bear': geom.get('rsi_divergence_bear') if isinstance(geom, dict) else None,
            }
    except Exception as e:
        out['position_error'] = str(e)

    # Price data recent rows
    try:
        five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
        c = (
            sb.client
            .table('lowcap_price_data_1m')
            .select('token_contract', count='exact')
            .eq('chain', TOKEN_CHAIN)
            .eq('token_contract', TOKEN_CONTRACT)
            .gte('timestamp', iso(five_min_ago))
            .execute()
        )
        out['price.rows_last_5m'] = int(getattr(c, 'count', 0) or 0)
        last = (
            sb.client
            .table('lowcap_price_data_1m')
            .select('timestamp')
            .eq('chain', TOKEN_CHAIN)
            .eq('token_contract', TOKEN_CONTRACT)
            .order('timestamp', desc=True)
            .limit(1)
            .execute()
        )
        last_ts = (last.data or [{}])[0].get('timestamp')
        out['price.last_ts'] = last_ts
    except Exception as e:
        out['price_error'] = str(e)

    # Decision strand presence
    try:
        strands = (
            sb.client
            .table('ad_strands')
            .select('id,created_at,kind,content')
            .eq('kind', 'decision_lowcap')
            .order('created_at', desc=True)
            .limit(20)
            .execute()
        )
        # detect OPAN strands
        found = False
        for row in (strands.data or []):
            content = row.get('content') or {}
            tok = (content.get('token') or {})
            if (tok.get('ticker') or '').upper() == 'OPAN':
                found = True
                out['decision_strand_sample'] = {
                    'id': row.get('id'),
                    'created_at': row.get('created_at'),
                    'ticker': tok.get('ticker'),
                    'chain': tok.get('chain'),
                    'contract': tok.get('contract'),
                }
                break
        out['decision_lowcap_opan_present'] = found
    except Exception as e:
        out['strands_error'] = str(e)

    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()



