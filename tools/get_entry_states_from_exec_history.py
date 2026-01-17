#!/usr/bin/env python3
"""
Get Entry States from Execution History
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

def extract_state_from_pattern_key(pattern_key):
    """Extract S1/S2/S3 from pattern_key"""
    if not pattern_key:
        return None
    # Pattern format: "module=pm|pattern_key=uptrend.S1.entry"
    if '.S1.' in pattern_key or pattern_key.endswith('.S1'):
        return 'S1'
    elif '.S2.' in pattern_key or pattern_key.endswith('.S2'):
        return 'S2'
    elif '.S3.' in pattern_key or pattern_key.endswith('.S3'):
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
    print("OPEN POSITIONS - ENTRY STATE FROM EXECUTION HISTORY")
    print("=" * 80)
    
    # Get active positions with features
    positions = sb.table('lowcap_positions').select('id, token_ticker, timeframe, total_pnl_usd, total_pnl_pct, total_allocation_usd, features').eq('status', 'active').execute()
    
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
        
        by_state = {}
        
        for pos in by_tf[tf]:
            ticker = pos.get('token_ticker', 'N/A')
            pnl_usd = float(pos.get('total_pnl_usd', 0) or 0)
            pnl_pct = float(pos.get('total_pnl_pct', 0) or 0)
            allocated = float(pos.get('total_allocation_usd', 0) or 0)
            
            entry_state = None
            entry_pattern = None
            
            # Check features -> pm_execution_history -> actions
            features = pos.get('features', {})
            if isinstance(features, str):
                try:
                    features = json.loads(features)
                except:
                    features = {}
            
            exec_history = features.get('pm_execution_history', {})
            if isinstance(exec_history, dict):
                actions = exec_history.get('actions', [])
                for action in actions:
                    if action.get('action_category') == 'entry' or action.get('decision_type') == 'entry':
                        pattern_key = action.get('pattern_key', '')
                        entry_state = extract_state_from_pattern_key(pattern_key)
                        if entry_state:
                            entry_pattern = pattern_key
                            break
            
            # If still not found, check if there's a last_s1_buy or similar
            if not entry_state and isinstance(exec_history, dict):
                if exec_history.get('last_s1_buy'):
                    entry_state = 'S1'
                elif exec_history.get('last_s2_buy'):
                    entry_state = 'S2'
            
            if not entry_state:
                entry_state = 'Unknown'
            
            if entry_state not in by_state:
                by_state[entry_state] = []
            
            by_state[entry_state].append({
                'ticker': ticker,
                'pnl_usd': pnl_usd,
                'pnl_pct': pnl_pct,
                'allocated': allocated,
                'pattern': entry_pattern
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
                    if p['pattern']:
                        print(f"         Pattern: {p['pattern']}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

