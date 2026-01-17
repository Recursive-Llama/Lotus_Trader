#!/usr/bin/env python3
"""
Test Performance Tracking System
Quick script to check snapshots and performance data
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from supabase import create_client
from src.intelligence.system_observer.performance_data_access import PerformanceDataAccess
from datetime import datetime, timezone

def main():
    # Connect to Supabase
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return
    
    sb = create_client(url, key)
    
    # Check snapshots
    print("📊 Recent Snapshots:")
    print("=" * 60)
    snapshots = sb.table('wallet_balance_snapshots').select('*').order('captured_at', desc=True).limit(5).execute()
    if snapshots.data:
        for s in snapshots.data:
            print(f"  {s['captured_at']}: ${s['total_balance_usd']:.2f} (Type: {s['snapshot_type']})")
            print(f"    USDC: ${s['usdc_total']:.2f}, Active: ${s['active_positions_value']:.2f} ({s['active_positions_count']} positions)")
    else:
        print("  ⚠️  No snapshots found yet - initial snapshot should be created on startup")
    
    # Test performance access
    print("\n💰 Current Performance:")
    print("=" * 60)
    perf = PerformanceDataAccess(sb)
    current = perf.get_current_balance()
    if "error" in current:
        print(f"  ❌ Error: {current['error']}")
    else:
        print(f"  Total Balance: ${current.get('total_balance_usd', 0):.2f}")
        print(f"  USDC: ${current.get('usdc_total', 0):.2f}")
        print(f"  Active Positions: ${current.get('active_positions_value', 0):.2f} ({current.get('active_positions_count', 0)} positions)")
        
        if current.get('usdc_by_chain'):
            print("  USDC by Chain:")
            for chain, amount in current['usdc_by_chain'].items():
                if amount > 0:
                    print(f"    {chain}: ${amount:.2f}")
    
    # Detailed PnL breakdown
    print("\n📊 Portfolio PnL Breakdown:")
    print("=" * 60)
    pnl = perf.get_portfolio_pnl()
    if "error" in pnl:
        print(f"  ❌ Error: {pnl['error']}")
    else:
        print(f"  Starting USDC: ${pnl.get('starting_usdc', 0):.2f}")
        print(f"  Starting Balance: ${pnl.get('starting_balance', 0):.2f}")
        print(f"\n  Current State:")
        print(f"    Current USDC: ${pnl.get('current_usdc', 0):.2f}")
        print(f"    Capital Deployed: ${pnl.get('capital_deployed', 0):.2f}")
        print(f"    Positions Current Value: ${pnl.get('positions_current_value', 0):.2f}")
        print(f"\n  PnL Breakdown:")
        print(f"    Unrealized PnL: ${pnl.get('unrealized_pnl_usd', 0):.2f} ({pnl.get('unrealized_pnl_pct', 0):.1f}%)")
        print(f"    Realized PnL: ${pnl.get('realized_pnl_usd', 0):.2f}")
        print(f"      - From closed trades: ${pnl.get('realized_from_closed_trades', 0):.2f}")
        print(f"      - From partial exits: ${pnl.get('realized_from_partial_exits', 0):.2f}")
        print(f"    Total PnL: ${pnl.get('total_pnl_usd', 0):.2f} ({pnl.get('total_pnl_pct', 0):.1f}%)")
        print(f"    Current Total Balance: ${pnl.get('current_total_balance', 0):.2f}")
        
        positions = pnl.get('positions', [])
        if positions:
            print(f"\n  Active Positions ({len(positions)}):")
            for pos in positions:
                pnl_emoji = "✅" if pos['total_pnl_usd'] > 0 else "❌" if pos['total_pnl_usd'] < 0 else "➖"
                print(f"    {pnl_emoji} {pos['ticker']} ({pos['timeframe']}):")
                print(f"      Deployed: ${pos['allocated_usd']:.2f}")
                print(f"      Current Value: ${pos['current_value_usd']:.2f}")
                print(f"      Unrealized: ${pos['unrealized_pnl_usd']:.2f} ({pos['unrealized_pnl_pct']:.1f}%)")
                if pos['realized_pnl_usd'] != 0:
                    print(f"      Realized (partial): ${pos['realized_pnl_usd']:.2f}")
                print(f"      Total PnL: ${pos['total_pnl_usd']:.2f} ({pos['total_pnl_pct']:.1f}%)")
    
    # Get closed trades
    print("\n📈 Closed Trades (Last 24h):")
    print("=" * 60)
    trades = perf.get_closed_trades_over_period(24)
    print(f"  Total trades: {len(trades)}")
    if trades:
        total_pnl = sum(t['rpnl_usd'] for t in trades)
        wins = [t for t in trades if t['rpnl_usd'] > 0]
        print(f"  Total PnL: ${total_pnl:.2f}")
        print(f"  Wins: {len(wins)}/{len(trades)} ({len(wins)/len(trades)*100:.1f}% win rate)")
        print("\n  Recent trades:")
        for t in trades[:10]:
            pnl_emoji = "✅" if t['rpnl_usd'] > 0 else "❌"
            state = t.get('entry_state', '?')
            print(f"    {pnl_emoji} {t['token_ticker']} ({t['timeframe']}, {state}): ${t['rpnl_usd']:.2f} ({t['rpnl_pct']:.1f}%)")
    else:
        print("  No closed trades in last 24h")
    
    # Performance breakdown by multiple time periods
    print("\n📊 Performance Breakdown by Timeframe & Entry State:")
    print("=" * 60)
    
    for hours in [24, 168, 720]:  # 24h, 7d, 30d
        period_name = f"{hours//24}d" if hours >= 24 else f"{hours}h"
        print(f"\n  📅 Period: Last {period_name}")
        print("  " + "-" * 58)
        
        breakdown = perf.get_performance_breakdown(hours)
    if "error" in breakdown:
            print(f"    ❌ Error: {breakdown['error']}")
            continue
        
        total_trades = breakdown.get('total_trades', 0)
        total_pnl = breakdown.get('total_pnl_usd', 0)
        
        if total_trades == 0:
            print(f"    No closed trades in this period")
            continue
        
        print(f"    Total: {total_trades} trades, PnL: ${total_pnl:.2f}")
        
        # By Timeframe
        print(f"\n    By Timeframe:")
        by_tf = breakdown.get('by_timeframe', {})
        for tf in ['1m', '15m', '1h', '4h']:
            data = by_tf.get(tf, {})
            if data.get('count', 0) > 0:
                win_rate_pct = data['win_rate'] * 100
                print(f"      {tf:>4s}: {data['count']:>3d} trades | {win_rate_pct:>5.1f}% win | {data['avg_roi_pct']:>6.1f}% avg ROI | ${data['total_pnl_usd']:>7.2f} PnL")
        
        # By Entry State - First Buys Only
        print(f"\n    By Entry State (first buys only):")
        by_state_first = breakdown.get('by_entry_state_first', {})
        has_state_data = False
        for state in ['S1', 'S2', 'S3']:
            data = by_state_first.get(state, {})
            if data.get('count', 0) > 0:
                has_state_data = True
                print(f"      {state}: {data['count']:>3d} trades | {data['avg_return_pct']:>6.1f}% avg return | ${data['total_pnl_usd']:>7.2f} PnL")
        
        if not has_state_data:
            print(f"      (No first buy entry state data)")
        
        # By Entry State - ALL Entries (new)
        print(f"\n    By Entry State (ALL entries - includes adds):")
        by_state_all = breakdown.get('by_entry_state_all', {})
        has_state_data_all = False
        for state in ['S1', 'S2', 'S3']:
            data = by_state_all.get(state, {})
            if data.get('count', 0) > 0:
                has_state_data_all = True
                print(f"      {state}: {data['count']:>3d} trades | {data['avg_return_pct']:>6.1f}% avg return | ${data['total_pnl_usd']:>7.2f} PnL")
        
        if not has_state_data_all:
            print(f"      (No entry state data for all entries)")
        
        # By Entry Sequence (new)
        by_sequence = breakdown.get('by_entry_sequence', {})
        if by_sequence:
            print(f"\n    By Entry Sequence (e.g., S2→S1):")
            # Sort by count descending
            sorted_sequences = sorted(by_sequence.items(), key=lambda x: x[1].get('count', 0), reverse=True)
            for seq, data in sorted_sequences[:10]:  # Show top 10 sequences
                win_rate_pct = data.get('win_rate', 0) * 100
                print(f"      {seq:>10s}: {data['count']:>3d} trades | {win_rate_pct:>5.1f}% win | {data.get('avg_return_pct', 0):>6.1f}% avg return | ${data['total_pnl_usd']:>7.2f} PnL")
        
        # Combined: By Timeframe AND Entry State (first buy)
        by_tf_entry = breakdown.get('by_tf_entry_first', {})
        if any(by_tf_entry.values()):
            print(f"\n    By Timeframe + Entry State (first buy):")
            for tf in ['1m', '15m', '1h', '4h']:
                tf_data = by_tf_entry.get(tf, {})
                if tf_data:
                    print(f"      {tf}:")
                    for state in ['S1', 'S2', 'S3']:
                        state_data = tf_data.get(state, {})
                        if state_data.get('count', 0) > 0:
                            win_rate_pct = state_data.get('win_rate', 0) * 100
                            print(f"        {state}: {state_data['count']:>3d} trades | {win_rate_pct:>5.1f}% win | {state_data.get('avg_roi_pct', 0):>6.1f}% avg ROI | ${state_data['total_pnl_usd']:>7.2f} PnL")
        
        # Combined: By Timeframe AND Entry Sequence
        by_tf_seq = breakdown.get('by_tf_sequence', {})
        if any(by_tf_seq.values()):
            print(f"\n    By Timeframe + Entry Sequence:")
            for tf in ['1m', '15m', '1h', '4h']:
                tf_data = by_tf_seq.get(tf, {})
                if tf_data:
                    print(f"      {tf}:")
                    # Sort sequences by count descending
                    sorted_seqs = sorted(tf_data.items(), key=lambda x: x[1].get('count', 0), reverse=True)
                    for seq, data in sorted_seqs:
                        win_rate_pct = data.get('win_rate', 0) * 100
                        print(f"        {seq:>10s}: {data['count']:>3d} trades | {win_rate_pct:>5.1f}% win | {data.get('avg_return_pct', 0):>6.1f}% avg return | ${data['total_pnl_usd']:>7.2f} PnL")
    
    # Historical PnL
    print("\n📉 Historical PnL:")
    print("=" * 60)
    for hours in [24, 168, 720]:  # 24h, 7d, 30d
        pnl_data = perf.get_pnl_over_period(hours)
        if "error" not in pnl_data:
            period_name = f"{hours//24}d" if hours >= 24 else f"{hours}h"
            print(f"  Last {period_name}: ${pnl_data['pnl_usd']:.2f} ({pnl_data['pnl_pct']:.2f}%)")
            print(f"    From ${pnl_data['starting_balance']:.2f} → ${pnl_data['ending_balance']:.2f}")

if __name__ == "__main__":
    main()

