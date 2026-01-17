#!/usr/bin/env python3
"""
Analyze Open Positions by Entry State (S1 vs S2)
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
import json

def extract_entry_state_from_position(position):
    """Extract entry state from position data"""
    # Check current_trade_id and execution_history
    execution_history = position.get('execution_history', {})
    if isinstance(execution_history, str):
        try:
            execution_history = json.loads(execution_history)
        except:
            execution_history = {}
    
    # Check for first entry action
    actions = execution_history.get('actions', [])
    for action in actions:
        if action.get('action_category') == 'entry' or action.get('decision_type') == 'entry':
            pattern_key = action.get('pattern_key', '')
            if 'S1' in pattern_key:
                return 'S1'
            elif 'S2' in pattern_key:
                return 'S2'
            elif 'S3' in pattern_key:
                return 'S3'
    
    # Check completed_trades for entry state
    completed_trades = position.get('completed_trades', [])
    if completed_trades:
        for trade in completed_trades if isinstance(completed_trades, list) else [completed_trades]:
            if isinstance(trade, dict):
                actions = trade.get('actions', [])
                for action in actions:
                    if action.get('action_category') == 'entry':
                        pattern_key = action.get('pattern_key', '')
                        if 'S1' in pattern_key:
                            return 'S1'
                        elif 'S2' in pattern_key:
                            return 'S2'
                        elif 'S3' in pattern_key:
                            return 'S3'
    
    # Check current_trade actions if available
    current_trade = position.get('current_trade', {})
    if isinstance(current_trade, dict):
        actions = current_trade.get('actions', [])
        for action in actions:
            if action.get('action_category') == 'entry':
                pattern_key = action.get('pattern_key', '')
                if 'S1' in pattern_key:
                    return 'S1'
                elif 'S2' in pattern_key:
                    return 'S2'
                elif 'S3' in pattern_key:
                    return 'S3'
    
    return None

def main():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return
    
    sb = create_client(url, key)
    perf = PerformanceDataAccess(sb)
    
    print("=" * 80)
    print("OPEN POSITIONS - ENTRY STATE ANALYSIS (S1 vs S2)")
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
    
    # Get full position data from database
    position_ids = [p.get('id') for p in positions if p.get('id')]
    
    try:
        db_positions = sb.table('lowcap_positions').select('*').in_('id', position_ids).execute()
        position_map = {p['id']: p for p in db_positions.data}
    except Exception as e:
        print(f"⚠️  Could not fetch full position data: {e}")
        position_map = {}
    
    # Group by timeframe and entry state
    by_tf_state = {}
    
    for pos in positions:
        pos_id = pos.get('id')
        tf = pos.get('timeframe', 'unknown')
        
        # Get full position data
        full_pos = position_map.get(pos_id, {})
        
        # Extract entry state
        entry_state = extract_entry_state_from_position(full_pos)
        if entry_state is None:
            # Try to get from pattern_key in position
            pattern_key = full_pos.get('pattern_key', '')
            if 'S1' in pattern_key:
                entry_state = 'S1'
            elif 'S2' in pattern_key:
                entry_state = 'S2'
            elif 'S3' in pattern_key:
                entry_state = 'S3'
            else:
                entry_state = 'Unknown'
        
        key = f"{tf}|{entry_state}"
        if key not in by_tf_state:
            by_tf_state[key] = []
        
        by_tf_state[key].append({
            'ticker': pos.get('ticker', 'N/A'),
            'pnl_usd': pos.get('total_pnl_usd', 0),
            'pnl_pct': pos.get('total_pnl_pct', 0),
            'allocated': pos.get('allocated_usd', 0),
            'current_value': pos.get('current_value_usd', 0),
            'unrealized': pos.get('unrealized_pnl_usd', 0),
            'realized': pos.get('realized_pnl_usd', 0),
            'entry_state': entry_state,
            'position_id': pos_id
        })
    
    # Display by timeframe
    for tf in ['15m', '1h', '4h']:
        print(f"\n{'='*80}")
        print(f"{tf} TIMEFRAME")
        print("=" * 80)
        
        # Get positions for this timeframe
        tf_positions = {k: v for k, v in by_tf_state.items() if k.startswith(f"{tf}|")}
        
        if not tf_positions:
            print(f"  No {tf} positions")
            continue
        
        # Group by entry state
        by_state = {}
        for key, positions_list in tf_positions.items():
            state = key.split('|')[1]
            if state not in by_state:
                by_state[state] = []
            by_state[state].extend(positions_list)
        
        # Show summary by state
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
                    print(f"      {emoji} {p['ticker']}: ${p['pnl_usd']:.2f} ({p['pnl_pct']:.1f}%) | Allocated: ${p['allocated']:.2f}")
                    print(f"         Unrealized: ${p['unrealized']:.2f}, Realized: ${p['realized']:.2f}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

