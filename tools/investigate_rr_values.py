#!/usr/bin/env python3
"""
Investigate RR Values - Why is 1m RR so high?
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
import json

def main():
    # Connect to Supabase
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return
    
    sb = create_client(url, key)
    perf = PerformanceDataAccess(sb)
    
    print("=" * 80)
    print("RR VALUE INVESTIGATION")
    print("=" * 80)
    
    # Get all closed trades
    print("\n📊 Closed Trades with RR Values:")
    print("-" * 80)
    trades = perf.get_closed_trades_over_period(None)  # All time
    
    # Group by timeframe
    by_timeframe = {}
    for trade in trades:
        tf = trade.get('timeframe', 'unknown')
        if tf not in by_timeframe:
            by_timeframe[tf] = []
        by_timeframe[tf].append(trade)
    
    for tf in ['1m', '15m', '1h', '4h']:
        if tf in by_timeframe:
            tf_trades = by_timeframe[tf]
            print(f"\n  {tf} Timeframe ({len(tf_trades)} trades):")
            
            rrs = []
            for trade in tf_trades:
                rpnl_pct = trade.get('rpnl_pct', 0)
                rpnl_usd = trade.get('rpnl_usd', 0)
                # Try to get RR from the trade - but we don't have it in the performance data
                # Let's check the actual position_closed strands
                print(f"    {trade.get('token_ticker', '?')}: PnL={rpnl_usd:.2f} ({rpnl_pct:.1f}%)")
    
    # Check position_closed strands for actual RR values
    print("\n\n📈 Position Closed Strands (with RR values):")
    print("-" * 80)
    try:
        strands = sb.table('ad_strands').select('*').eq('kind', 'position_closed').order('created_at', desc=True).limit(30).execute()
        
        by_tf = {}
        for strand in strands.data:
            content = strand.get('content', {})
            completed_trades = content.get('completed_trades', [])
            timeframe = strand.get('timeframe', 'unknown')
            
            if timeframe not in by_tf:
                by_tf[timeframe] = []
            
            for trade in completed_trades if isinstance(completed_trades, list) else [completed_trades]:
                # Get RR from trade
                rr = trade.get('rr')
                if rr is None and isinstance(trade, dict) and 'summary' in trade:
                    rr = trade.get('summary', {}).get('rr')
                
                if rr is not None:
                    by_tf[timeframe].append({
                        'rr': rr,
                        'rpnl_usd': trade.get('rpnl_usd') or (trade.get('summary', {}).get('rpnl_usd') if isinstance(trade, dict) else 0),
                        'rpnl_pct': trade.get('rpnl_pct') or (trade.get('summary', {}).get('rpnl_pct') if isinstance(trade, dict) else 0),
                        'token': strand.get('token', '?')
                    })
        
        for tf in ['1m', '15m', '1h', '4h']:
            if tf in by_tf and by_tf[tf]:
                trades = by_tf[tf]
                rrs = [t['rr'] for t in trades if t['rr'] is not None]
                if rrs:
                    print(f"\n  {tf} Timeframe ({len(rrs)} trades with RR):")
                    print(f"    RR values: {[f'{rr:.3f}' for rr in rrs]}")
                    print(f"    Avg RR: {sum(rrs)/len(rrs):.3f}")
                    print(f"    Min RR: {min(rrs):.3f}")
                    print(f"    Max RR: {max(rrs):.3f}")
                    
                    # Show individual trades
                    for t in trades[:10]:
                        print(f"      {t['token']}: RR={t['rr']:.3f}, PnL=${t['rpnl_usd']:.2f} ({t['rpnl_pct']:.1f}%)")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check pattern_trade_events for RR values
    print("\n\n📊 Pattern Trade Events (RR values by timeframe):")
    print("-" * 80)
    try:
        events = sb.table('pattern_trade_events').select('*').execute()
        
        by_tf = {}
        for event in events.data:
            scope = event.get('scope', {})
            tf = scope.get('timeframe', 'unknown')
            rr = event.get('rr', 0)
            
            if tf not in by_tf:
                by_tf[tf] = []
            by_tf[tf].append(rr)
        
        for tf in ['1m', '15m', '1h', '4h']:
            if tf in by_tf and by_tf[tf]:
                rrs = by_tf[tf]
                print(f"\n  {tf} Timeframe ({len(rrs)} events):")
                print(f"    Avg RR: {sum(rrs)/len(rrs):.3f}")
                print(f"    Min RR: {min(rrs):.3f}")
                print(f"    Max RR: {max(rrs):.3f}")
                print(f"    Sample RRs: {[f'{rr:.3f}' for rr in rrs[:10]]}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

