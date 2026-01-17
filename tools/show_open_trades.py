#!/usr/bin/env python3
"""
Show Current Open Trades
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from supabase import create_client
from src.intelligence.system_observer.performance_data_access import PerformanceDataAccess

def main():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return
    
    sb = create_client(url, key)
    perf = PerformanceDataAccess(sb)
    
    print("=" * 80)
    print("CURRENT OPEN TRADES")
    print("=" * 80)
    
    # Get portfolio PnL which includes active positions
    pnl = perf.get_portfolio_pnl()
    
    if "error" in pnl:
        print(f"❌ Error: {pnl['error']}")
        return
    
    positions = pnl.get('positions', [])
    
    if not positions:
        print("\n⚠️  No active positions")
        return
    
    print(f"\n📊 Active Positions: {len(positions)}")
    print("-" * 80)
    
    # Group by timeframe
    by_timeframe = {}
    for pos in positions:
        tf = pos.get('timeframe', 'unknown')
        if tf not in by_timeframe:
            by_timeframe[tf] = []
        by_timeframe[tf].append(pos)
    
    for tf in ['1m', '15m', '1h', '4h']:
        if tf in by_timeframe:
            trades = by_timeframe[tf]
            print(f"\n{tf} Timeframe ({len(trades)} positions):")
            print("-" * 80)
            
            for pos in sorted(trades, key=lambda x: x.get('total_pnl_usd', 0), reverse=True):
                ticker = pos.get('ticker', 'N/A')
                pnl_usd = pos.get('total_pnl_usd', 0)
                pnl_pct = pos.get('total_pnl_pct', 0)
                allocated = pos.get('allocated_usd', 0)
                current_value = pos.get('current_value_usd', 0)
                unrealized = pos.get('unrealized_pnl_usd', 0)
                realized = pos.get('realized_pnl_usd', 0)
                
                emoji = "✅" if pnl_usd > 0 else "❌" if pnl_usd < 0 else "➖"
                print(f"\n  {emoji} {ticker}")
                print(f"    Allocated: ${allocated:.2f}")
                print(f"    Current Value: ${current_value:.2f}")
                print(f"    Unrealized: ${unrealized:.2f} ({unrealized/allocated*100 if allocated > 0 else 0:.1f}%)")
                if realized != 0:
                    print(f"    Realized (partial): ${realized:.2f}")
                print(f"    Total PnL: ${pnl_usd:.2f} ({pnl_pct:.1f}%)")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

