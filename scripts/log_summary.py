#!/usr/bin/env python3
"""
Daily log summary for trading_executions.log

- Aggregates by day
  - Counts by event and chain
  - Success vs failure rates per action
  - Top error reasons
  - Median/p95 durations (where available)

Usage:
  python3 scripts/log_summary.py --log logs/trading_executions.log [--date 2025-10-06]

Schedule via cron or CI daily. Example cron (midnight):
  0 0 * * * /usr/bin/python3 /path/to/scripts/log_summary.py --log /path/to/logs/trading_executions.log >> /path/to/logs/daily_summary.log 2>&1
"""

import argparse
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log', default='logs/trading_executions.log')
    parser.add_argument('--date', help='YYYY-MM-DD (UTC). If omitted, include all.')
    return parser.parse_args()


def iso_to_date(iso_ts: str) -> str:
    try:
        return iso_ts.split('T', 1)[0]
    except Exception:
        return ''


def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    k = (len(values)-1) * (p/100.0)
    f = int(k)
    c = min(f+1, len(values)-1)
    if f == c:
        return values[f]
    return values[f] + (values[c]-values[f]) * (k-f)


def main():
    args = parse_args()
    target_date = args.date

    counts_by_event = Counter()
    counts_by_chain = Counter()
    success_fail_by_action = defaultdict(lambda: {'success': 0, 'failed': 0})
    top_errors = Counter()
    durations_by_event = defaultdict(list)

    with open(args.log, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                j = json.loads(line)
            except Exception:
                continue

            ts = j.get('ts') or ''
            event_date = iso_to_date(ts)
            if target_date and event_date != target_date:
                continue

            event = j.get('event') or 'UNKNOWN'
            counts_by_event[event] += 1

            chain = ((j.get('correlation') or {}).get('chain') or 'unknown').lower()
            counts_by_chain[chain] += 1

            # Success/failure classification
            if event.endswith('_SUCCESS') or event in ('ENTRY_SUCCESS', 'EXIT_SUCCESS', 'BUYBACK_EXECUTED'):
                action = event.split('_SUCCESS')[0].lower()
                success_fail_by_action[action]['success'] += 1
            elif event.endswith('_FAILED') or event.endswith('_FAILED_AGGREGATED'):
                action = event.split('_FAILED')[0].lower()
                success_fail_by_action[action]['failed'] += 1

            # Top errors
            err = j.get('error') or {}
            if 'reason' in err and err['reason']:
                top_errors[err['reason']] += 1

            # Durations
            perf = j.get('performance') or {}
            if 'duration_ms' in perf and isinstance(perf['duration_ms'], (int, float)):
                durations_by_event[event].append(perf['duration_ms'])

    # Print summary
    print('=== Daily Log Summary ===')
    print(f"Date: {target_date or 'ALL'}")
    print('\nEvents:')
    for k, v in counts_by_event.most_common():
        print(f"  {k}: {v}")

    print('\nBy Chain:')
    for k, v in counts_by_chain.most_common():
        print(f"  {k}: {v}")

    print('\nSuccess/Failure by Action:')
    for action, sf in success_fail_by_action.items():
        total = sf['success'] + sf['failed']
        rate = (sf['success'] / total * 100.0) if total else 0.0
        print(f"  {action}: success={sf['success']}, failed={sf['failed']} (success_rate={rate:.1f}%)")

    print('\nTop Errors:')
    for k, v in top_errors.most_common(10):
        print(f"  {k}: {v}")

    print('\nDurations (ms):')
    for event, vals in durations_by_event.items():
        med = statistics.median(vals) if vals else None
        p95 = percentile(vals, 95) if vals else None
        print(f"  {event}: median={med}, p95={p95}")


if __name__ == '__main__':
    main()


