#!/usr/bin/env python3
"""
Diagnostic script to analyze 1m data coverage and backfill needs.

Checks:
1. How many tokens are tracked (active/watchlist/dormant)
2. How many have 1m data in the last hour
3. Coverage rates per token
4. Which tokens need backfill
5. Price collector activity
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Any
from collections import defaultdict

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def get_supabase() -> Client:
    """Get Supabase client"""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
    return create_client(url, key)

def get_tracked_tokens(sb: Client) -> List[Tuple[str, str]]:
    """Get all tracked tokens (active/watchlist/dormant)"""
    result = (
        sb.table('lowcap_positions')
        .select('token_contract', 'token_chain', 'status')
        .in_('status', ['active', 'watchlist', 'dormant'])
        .execute()
    )
    
    # Deduplicate by (token_contract, chain)
    tokens = set()
    for row in (result.data or []):
        token = (row['token_contract'], (row.get('token_chain') or '').lower())
        if token[0] and token[1]:
            tokens.add(token)
    
    return list(tokens)

def check_1m_coverage(sb: Client, token_contract: str, chain: str, hour_start: datetime, hour_end: datetime) -> Dict[str, Any]:
    """Check 1m data coverage for a token in a specific hour"""
    result = (
        sb.table('lowcap_price_data_1m')
        .select('timestamp')
        .eq('token_contract', token_contract)
        .eq('chain', chain)
        .gte('timestamp', hour_start.isoformat())
        .lt('timestamp', hour_end.isoformat())
        .order('timestamp', desc=False)
        .execute()
    )
    
    bars = result.data or []
    count = len(bars)
    
    # Calculate coverage
    expected_bars = 60  # 60 minutes in an hour
    coverage_pct = (count / expected_bars * 100) if expected_bars > 0 else 0
    
    # Get latest timestamp
    latest_ts = None
    if bars:
        latest_ts = datetime.fromisoformat(bars[-1]['timestamp'].replace('Z', '+00:00'))
    
    return {
        'count': count,
        'expected': expected_bars,
        'coverage_pct': coverage_pct,
        'latest_ts': latest_ts,
        'needs_backfill': count < 36  # Less than 60% (36/60)
    }

def check_1m_ohlc_coverage(sb: Client, token_contract: str, chain: str, hour_start: datetime, hour_end: datetime) -> Dict[str, Any]:
    """Check 1m OHLC data coverage (rolled up from 1m price points)"""
    result = (
        sb.table('lowcap_price_data_ohlc')
        .select('timestamp')
        .eq('token_contract', token_contract)
        .eq('chain', chain)
        .eq('timeframe', '1m')
        .gte('timestamp', hour_start.isoformat())
        .lt('timestamp', hour_end.isoformat())
        .order('timestamp', desc=False)
        .execute()
    )
    
    bars = result.data or []
    count = len(bars)
    
    expected_bars = 60
    coverage_pct = (count / expected_bars * 100) if expected_bars > 0 else 0
    
    latest_ts = None
    if bars:
        latest_ts = datetime.fromisoformat(bars[-1]['timestamp'].replace('Z', '+00:00'))
    
    return {
        'count': count,
        'expected': expected_bars,
        'coverage_pct': coverage_pct,
        'latest_ts': latest_ts,
        'needs_backfill': count < 36
    }

def get_latest_price_collector_activity(sb: Client, minutes: int = 60) -> Dict[str, Any]:
    """Get latest price collector activity"""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    
    result = (
        sb.table('lowcap_price_data_1m')
        .select('token_contract', 'chain', 'timestamp', 'source')
        .gte('timestamp', cutoff)
        .order('timestamp', desc=True)
        .limit(1000)
        .execute()
    )
    
    data = result.data or []
    
    # Group by token
    by_token = defaultdict(list)
    for row in data:
        key = (row['token_contract'], row['chain'])
        by_token[key].append(row['timestamp'])
    
    # Get latest timestamp overall
    latest_overall = None
    if data:
        latest_overall = datetime.fromisoformat(data[0]['timestamp'].replace('Z', '+00:00'))
    
    return {
        'total_points': len(data),
        'tokens_with_data': len(by_token),
        'latest_overall': latest_overall,
        'by_token': dict(by_token)
    }

def main():
    print("=" * 80)
    print("Data Coverage Diagnostic")
    print("=" * 80)
    print()
    
    sb = get_supabase()
    
    # 1. Get tracked tokens
    print("1. TRACKED TOKENS")
    print("-" * 80)
    tokens = get_tracked_tokens(sb)
    print(f"Total tracked tokens: {len(tokens)}")
    print()
    
    # 2. Check current hour coverage
    print("2. CURRENT HOUR COVERAGE (1m price points)")
    print("-" * 80)
    now = datetime.now(timezone.utc)
    current_hour_start = now.replace(minute=0, second=0, microsecond=0)
    current_hour_end = current_hour_start + timedelta(hours=1)
    
    coverage_stats = []
    needs_backfill = []
    
    for token_contract, chain in tokens[:50]:  # Limit to first 50 for speed
        coverage = check_1m_coverage(sb, token_contract, chain, current_hour_start, current_hour_end)
        coverage_stats.append({
            'token': f"{token_contract[:8]}.../{chain}",
            'count': coverage['count'],
            'coverage_pct': coverage['coverage_pct'],
            'latest_ts': coverage['latest_ts']
        })
        
        if coverage['needs_backfill']:
            needs_backfill.append({
                'token': f"{token_contract[:8]}.../{chain}",
                'count': coverage['count'],
                'coverage_pct': coverage['coverage_pct']
            })
    
    # Sort by coverage
    coverage_stats.sort(key=lambda x: x['coverage_pct'])
    
    print(f"Current hour: {current_hour_start} to {current_hour_end}")
    print(f"Tokens checked: {len(coverage_stats)}")
    print()
    
    print("Top 10 tokens with LOWEST coverage:")
    for stat in coverage_stats[:10]:
        latest_str = stat['latest_ts'].strftime('%H:%M:%S') if stat['latest_ts'] else 'N/A'
        print(f"  {stat['token']}: {stat['count']}/60 bars ({stat['coverage_pct']:.1f}%) - latest: {latest_str}")
    print()
    
    print(f"Tokens needing backfill (<60%): {len(needs_backfill)}")
    if needs_backfill:
        print("First 10:")
        for item in needs_backfill[:10]:
            print(f"  {item['token']}: {item['count']}/60 bars ({item['coverage_pct']:.1f}%)")
    print()
    
    # 3. Check 1m OHLC coverage (rolled up)
    print("3. CURRENT HOUR COVERAGE (1m OHLC bars - rolled up)")
    print("-" * 80)
    ohlc_coverage_stats = []
    ohlc_needs_backfill = []
    
    for token_contract, chain in tokens[:50]:
        coverage = check_1m_ohlc_coverage(sb, token_contract, chain, current_hour_start, current_hour_end)
        ohlc_coverage_stats.append({
            'token': f"{token_contract[:8]}.../{chain}",
            'count': coverage['count'],
            'coverage_pct': coverage['coverage_pct'],
            'latest_ts': coverage['latest_ts']
        })
        
        if coverage['needs_backfill']:
            ohlc_needs_backfill.append({
                'token': f"{token_contract[:8]}.../{chain}",
                'count': coverage['count'],
                'coverage_pct': coverage['coverage_pct']
            })
    
    ohlc_coverage_stats.sort(key=lambda x: x['coverage_pct'])
    
    print(f"Tokens checked: {len(ohlc_coverage_stats)}")
    print("Top 10 tokens with LOWEST OHLC coverage:")
    for stat in ohlc_coverage_stats[:10]:
        latest_str = stat['latest_ts'].strftime('%H:%M:%S') if stat['latest_ts'] else 'N/A'
        print(f"  {stat['token']}: {stat['count']}/60 bars ({stat['coverage_pct']:.1f}%) - latest: {latest_str}")
    print()
    
    print(f"Tokens needing OHLC backfill (<60%): {len(ohlc_needs_backfill)}")
    print()
    
    # 4. Price collector activity
    print("4. PRICE COLLECTOR ACTIVITY (last 60 minutes)")
    print("-" * 80)
    activity = get_latest_price_collector_activity(sb, minutes=60)
    
    print(f"Total 1m price points collected: {activity['total_points']}")
    print(f"Tokens with data: {activity['tokens_with_data']}")
    if activity['latest_overall']:
        age_minutes = (now - activity['latest_overall']).total_seconds() / 60
        print(f"Latest data point: {activity['latest_overall']} ({age_minutes:.1f} minutes ago)")
    print()
    
    # Show tokens with most recent data
    print("Top 10 tokens with most recent data:")
    token_counts = [(k, len(v)) for k, v in activity['by_token'].items()]
    token_counts.sort(key=lambda x: x[1], reverse=True)
    for (token_contract, chain), count in token_counts[:10]:
        print(f"  {token_contract[:8]}.../{chain}: {count} points")
    print()
    
    # 5. Summary
    print("5. SUMMARY")
    print("-" * 80)
    avg_coverage = sum(s['coverage_pct'] for s in coverage_stats) / len(coverage_stats) if coverage_stats else 0
    print(f"Average 1m price point coverage: {avg_coverage:.1f}%")
    
    avg_ohlc_coverage = sum(s['coverage_pct'] for s in ohlc_coverage_stats) / len(ohlc_coverage_stats) if ohlc_coverage_stats else 0
    print(f"Average 1m OHLC coverage: {avg_ohlc_coverage:.1f}%")
    
    print(f"Tokens needing backfill: {len(needs_backfill)}/{len(coverage_stats)} ({len(needs_backfill)/len(coverage_stats)*100:.1f}%)" if coverage_stats else "N/A")
    print()
    
    print("=" * 80)
    print("Diagnostic complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()

