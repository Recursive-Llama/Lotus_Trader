#!/usr/bin/env python3
"""
PM Shadow Diagnostics (last 2 hours)

Reports data health and PM signals without executing trades.
Outputs a compact JSON summary to stdout.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from src.utils.supabase_manager import SupabaseManager


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def get_ingest_summary(sb: SupabaseManager, table: str, chain_field: str = 'chain') -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=2)
    summary: Dict[str, Any] = {}
    for chain in ['solana', 'base', 'bsc', 'ethereum']:
        try:
            res = (
                sb.client
                .table(table)
                .select('timestamp')
                .eq(chain_field, chain)
                .gte('timestamp', iso(start))
                .order('timestamp', desc=True)
                .limit(1)
                .execute()
            )
            count_res = (
                sb.client
                .table(table)
                .select(chain_field, count='exact')
                .eq(chain_field, chain)
                .gte('timestamp', iso(start))
                .execute()
            )
            last_ts = None
            if res.data:
                last_ts = datetime.fromisoformat(res.data[0]['timestamp'].replace('Z','+00:00'))
            lag_s = (now - last_ts).total_seconds() if last_ts else None
            summary[chain] = {
                'rows_2h': int(getattr(count_res, 'count', 0) or 0),
                'last_ts': iso(last_ts) if last_ts else None,
                'lag_s': int(lag_s) if lag_s is not None else None,
            }
        except Exception:
            summary[chain] = {'rows_2h': 0, 'last_ts': None, 'lag_s': None}
    return summary


def get_phase_summary(sb: SupabaseManager) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=2)
    out: Dict[str, Any] = {}
    for horizon in ['macro','meso','micro']:
        try:
            res = (
                sb.client
                .table('phase_state')
                .select('id', count='exact')
                .eq('token', 'PORTFOLIO')
                .eq('horizon', horizon)
                .gte('ts', iso(start))
                .execute()
            )
            out[horizon] = int(getattr(res, 'count', 0) or 0)
        except Exception:
            out[horizon] = 0
    return out


def get_strands_summary(sb: SupabaseManager) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=2)
    try:
        res = (
            sb.client
            .table('ad_strands')
            .select('id', count='exact')
            .gte('created_at', iso(start))
            .execute()
        )
        return {'rows_2h': int(getattr(res, 'count', 0) or 0)}
    except Exception:
        return {'rows_2h': 0}


def get_geometry_presence(sb: SupabaseManager) -> Dict[str, Any]:
    try:
        res = (
            sb.client
            .table('lowcap_positions')
            .select('id,features')
            .eq('status', 'active')
            .limit(50)
            .execute()
        )
        total = len(res.data or [])
        have_geom = 0
        for row in (res.data or []):
            f = row.get('features') or {}
            g = f.get('geometry') if isinstance(f, dict) else None
            if isinstance(g, dict) and (g.get('sr_conf') is not None or g.get('diag_break') is not None):
                have_geom += 1
        return {'sampled': total, 'with_geometry': have_geom}
    except Exception:
        return {'sampled': 0, 'with_geometry': 0}


def main():
    sb = SupabaseManager()
    report = {
        'window': 'last_2h',
        'lowcap_ingest': get_ingest_summary(sb, 'lowcap_price_data_1m', 'chain'),
        'majors_ingest': get_ingest_summary(sb, 'majors_price_data_1m', 'token'),
        'phase_state_rows': get_phase_summary(sb),
        'strands_rows': get_strands_summary(sb),
        'geometry_presence': get_geometry_presence(sb),
        'ts': iso(datetime.now(timezone.utc)),
    }
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()



