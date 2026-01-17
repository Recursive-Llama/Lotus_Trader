#!/usr/bin/env python3
"""
Investigate 1h Trades - Why is RR so bad?
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from supabase import create_client
import json

def main():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return
    
    sb = create_client(url, key)
    
    print("=" * 80)
    print("1H TRADES INVESTIGATION")
    print("=" * 80)
    
    # Find all 1h position_closed strands
    print("\n📊 All 1h Closed Trades:")
    print("-" * 80)
    try:
        strands = sb.table('ad_strands').select('*').eq('kind', 'position_closed').eq('timeframe', '1h').order('created_at', desc=True).execute()
        
        print(f"Found {len(strands.data)} 1h trades\n")
        
        for i, strand in enumerate(strands.data, 1):
            content = strand.get('content', {})
            completed_trades = content.get('completed_trades', [])
            token = strand.get('token', 'N/A')
            
            print(f"Trade {i}: {token}")
            print(f"  Strand ID: {strand.get('id')}")
            print(f"  Created: {strand.get('created_at')}")
            
            for j, trade in enumerate(completed_trades if isinstance(completed_trades, list) else [completed_trades]):
                if isinstance(trade, dict):
                    summary = trade.get('summary', {})
                    
                    # Get key metrics
                    rr = summary.get('rr', trade.get('rr', 'N/A'))
                    return_pct = summary.get('return', trade.get('return', 'N/A'))
                    max_drawdown = summary.get('max_drawdown', trade.get('max_drawdown', 'N/A'))
                    max_gain = summary.get('max_gain', trade.get('max_gain', 'N/A'))
                    rpnl_usd = summary.get('rpnl_usd', trade.get('rpnl_usd', 0))
                    rpnl_pct = summary.get('rpnl_pct', trade.get('rpnl_pct', 0))
                    
                    entry_price = summary.get('entry_price', trade.get('entry_price', 'N/A'))
                    exit_price = summary.get('exit_price', trade.get('exit_price', 'N/A'))
                    min_price = summary.get('min_price', trade.get('min_price', 'N/A'))
                    max_price = summary.get('max_price', trade.get('max_price', 'N/A'))
                    
                    entry_ts = summary.get('entry_timestamp', trade.get('entry_timestamp', 'N/A'))
                    exit_ts = summary.get('exit_timestamp', trade.get('exit_timestamp', 'N/A'))
                    
                    print(f"\n  Trade {j+1} Details:")
                    print(f"    Entry: ${entry_price} at {entry_ts}")
                    print(f"    Exit: ${exit_price} at {exit_ts}")
                    print(f"    Min Price: ${min_price}")
                    print(f"    Max Price: ${max_price}")
                    print(f"\n    Performance:")
                    print(f"      PnL: ${rpnl_usd:.2f} ({rpnl_pct:.2f}%)")
                    print(f"      Return: {return_pct*100 if isinstance(return_pct, (int, float)) else return_pct:.2f}%")
                    print(f"      Max Drawdown: {max_drawdown*100 if isinstance(max_drawdown, (int, float)) else max_drawdown:.2f}%")
                    print(f"      Max Gain: {max_gain*100 if isinstance(max_gain, (int, float)) else max_gain:.2f}%")
                    if isinstance(rr, (int, float)):
                        print(f"      RR: {rr:.3f}")
                    else:
                        print(f"      RR: {rr}")
                    
                    # Calculate RR manually to verify
                    if isinstance(return_pct, (int, float)) and isinstance(max_drawdown, (int, float)) and max_drawdown > 0:
                        calculated_rr = return_pct / max_drawdown
                        print(f"      Calculated RR: {calculated_rr:.3f} (return/max_drawdown)")
                    
                    # Show price movement
                    if isinstance(entry_price, (int, float)) and isinstance(min_price, (int, float)) and isinstance(exit_price, (int, float)):
                        drawdown_usd = entry_price - min_price
                        drawdown_pct = (drawdown_usd / entry_price) * 100 if entry_price > 0 else 0
                        print(f"\n    Price Movement:")
                        print(f"      Entry: ${entry_price:.6f}")
                        print(f"      Dropped to: ${min_price:.6f} (${drawdown_usd:.6f} down, {drawdown_pct:.2f}%)")
                        print(f"      Exited at: ${exit_price:.6f}")
                        
                        if isinstance(max_price, (int, float)):
                            gain_usd = max_price - entry_price
                            gain_pct = (gain_usd / entry_price) * 100 if entry_price > 0 else 0
                            print(f"      Went up to: ${max_price:.6f} (${gain_usd:.6f} up, {gain_pct:.2f}%)")
                    
                    print()
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 80)

if __name__ == "__main__":
    main()

