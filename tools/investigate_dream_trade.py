#!/usr/bin/env python3
"""
Investigate DREAM Trade - Why RR=12.793?
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
    print("DREAM TRADE INVESTIGATION")
    print("=" * 80)
    
    # Find DREAM in position_closed strands
    print("\n📊 Searching for DREAM in position_closed strands:")
    print("-" * 80)
    try:
        strands = sb.table('ad_strands').select('*').eq('kind', 'position_closed').order('created_at', desc=True).limit(50).execute()
        
        for strand in strands.data:
            content = strand.get('content', {})
            completed_trades = content.get('completed_trades', [])
            token = strand.get('token', '')
            
            if 'DREAM' in token.upper() or any('DREAM' in str(t).upper() for t in completed_trades if isinstance(t, dict)):
                print(f"\n  Found DREAM trade!")
                print(f"  Strand ID: {strand.get('id')}")
                print(f"  Created: {strand.get('created_at')}")
                print(f"  Token: {token}")
                print(f"  Timeframe: {strand.get('timeframe')}")
                
                print(f"\n  Entry Context:")
                entry_context = content.get('entry_context', {})
                print(f"    {json.dumps(entry_context, indent=4)}")
                
                print(f"\n  Completed Trades:")
                for i, trade in enumerate(completed_trades if isinstance(completed_trades, list) else [completed_trades]):
                    print(f"\n    Trade {i+1}:")
                    if isinstance(trade, dict):
                        summary = trade.get('summary', {})
                        print(f"      RR: {summary.get('rr', trade.get('rr', 'N/A'))}")
                        print(f"      PnL USD: ${summary.get('rpnl_usd', trade.get('rpnl_usd', 0)):.2f}")
                        print(f"      PnL %: {summary.get('rpnl_pct', trade.get('rpnl_pct', 0)):.2f}%")
                        print(f"      Entry: {summary.get('entry_timestamp', trade.get('entry_timestamp', 'N/A'))}")
                        print(f"      Exit: {summary.get('exit_timestamp', trade.get('exit_timestamp', 'N/A'))}")
                        
                        # Show full trade data
                        print(f"\n      Full Trade Data:")
                        print(f"        {json.dumps(trade, indent=8, default=str)}")
                    else:
                        print(f"      {trade}")
                
                # Check if position exists
                position_id = strand.get('position_id')
                if position_id:
                    print(f"\n  Checking Position {position_id}:")
                    pos = sb.table('lowcap_positions').select('*').eq('id', position_id).execute()
                    if pos.data:
                        p = pos.data[0]
                        print(f"    Status: {p.get('status')}")
                        print(f"    Total PnL: ${p.get('total_pnl_usd', 0):.2f}")
                        print(f"    Total Allocation: ${p.get('total_allocation_usd', 0):.2f}")
                        print(f"    Current Value: ${p.get('current_usd_value', 0):.2f}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

