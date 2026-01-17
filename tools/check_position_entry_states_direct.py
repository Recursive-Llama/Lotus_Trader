#!/usr/bin/env python3
"""
Check Position Entry States Directly from Database
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

def extract_entry_state_from_str(pattern_key):
    """Extract S1/S2/S3 from pattern_key string"""
    if not pattern_key:
        return None
    if 'S1' in pattern_key or '.S1.' in pattern_key:
        return 'S1'
    elif 'S2' in pattern_key or '.S2.' in pattern_key:
        return 'S2'
    elif 'S3' in pattern_key or '.S3.' in pattern_key:
        return 'S3'
    return None

def main():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return
    
    sb = create_client(url, key)
    
    print("=" * 80)
    print("OPEN POSITIONS - ENTRY STATE (Direct DB Check)")
    print("=" * 80)
    
    # Get active positions
    positions = sb.table('lowcap_positions').select('*').eq('status', 'active').execute()
    
    if not positions.data:
        print("\n⚠️  No active positions")
        return
    
    print(f"\n📊 Active Positions: {len(positions.data)}")
    print("-" * 80)
    
    # Group by timeframe
    by_tf = {}
    for pos in positions.data:
        tf = pos.get('timeframe', 'unknown')
        if tf not in by_tf:
            by_tf[tf] = []
        by_tf[tf].append(pos)
    
    for tf in ['15m', '1h', '4h']:
        if tf not in by_tf:
            continue
        
        print(f"\n{'='*80}")
        print(f"{tf} TIMEFRAME ({len(by_tf[tf])} positions)")
        print("=" * 80)
        
        # Try multiple ways to get entry state
        by_state = {}
        
        for pos in by_tf[tf]:
            ticker = pos.get('token_ticker', 'N/A')
            pnl_usd = float(pos.get('total_pnl_usd', 0) or 0)
            pnl_pct = float(pos.get('total_pnl_pct', 0) or 0)
            allocated = float(pos.get('total_allocation_usd', 0) or 0)
            
            entry_state = None
            
            # Method 1: Check pattern_key field
            pattern_key = pos.get('pattern_key', '')
            if pattern_key:
                entry_state = extract_entry_state_from_str(pattern_key)
            
            # Method 2: Check execution_history
            if not entry_state:
                exec_history = pos.get('execution_history', {})
                if isinstance(exec_history, str):
                    try:
                        exec_history = json.loads(exec_history)
                    except:
                        exec_history = {}
                
                actions = exec_history.get('actions', [])
                for action in actions:
                    if action.get('action_category') == 'entry' or action.get('decision_type') == 'entry':
                        pattern_key = action.get('pattern_key', '')
                        entry_state = extract_entry_state_from_str(pattern_key)
                        if entry_state:
                            break
            
            # Method 3: Check completed_trades (for positions that had previous trades)
            if not entry_state:
                completed_trades = pos.get('completed_trades', [])
                if completed_trades:
                    for trade in completed_trades if isinstance(completed_trades, list) else [completed_trades]:
                        if isinstance(trade, dict):
                            actions = trade.get('actions', [])
                            for action in actions:
                                if action.get('action_category') == 'entry':
                                    pattern_key = action.get('pattern_key', '')
                                    entry_state = extract_entry_state_from_str(pattern_key)
                                    if entry_state:
                                        break
                        if entry_state:
                            break
            
            if not entry_state:
                entry_state = 'Unknown'
            
            if entry_state not in by_state:
                by_state[entry_state] = []
            
            by_state[entry_state].append({
                'ticker': ticker,
                'pnl_usd': pnl_usd,
                'pnl_pct': pnl_pct,
                'allocated': allocated,
                'pattern_key': pattern_key[:50] if pattern_key else 'N/A'
            })
        
        # Display by state
        for state in ['S1', 'S2', 'S3', 'Unknown']:
            if state in by_state:
                state_positions = by_state[state]
                total_pnl = sum(p['pnl_usd'] for p in state_positions)
                total_allocated = sum(p['allocated'] for p in state_positions)
                avg_roi = (total_pnl / total_allocated * 100) if total_allocated > 0 else 0
                wins = [p for p in state_positions if p['pnl_usd'] > 0]
                
                print(f"\n  {state} Entry ({len(state_positions)} positions):")
                print(f"    Total PnL: ${total_pnl:.2f}")
                print(f"    Total Allocated: ${total_allocated:.2f}")
                print(f"    Avg ROI: {avg_roi:.1f}%")
                print(f"    Win Rate: {len(wins)}/{len(state_positions)} ({len(wins)/len(state_positions)*100:.1f}%)")
                
                print(f"\n    Positions:")
                for p in sorted(state_positions, key=lambda x: x['pnl_usd'], reverse=True):
                    emoji = "✅" if p['pnl_usd'] > 0 else "❌" if p['pnl_usd'] < 0 else "➖"
                    print(f"      {emoji} {p['ticker']}: ${p['pnl_usd']:.2f} ({p['pnl_pct']:.1f}%)")
                    if p['pattern_key'] != 'N/A':
                        print(f"         Pattern: {p['pattern_key']}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

