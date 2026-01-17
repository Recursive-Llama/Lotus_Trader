#!/usr/bin/env python3
"""
Analyze 1m Trades - Open and Closed
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

def extract_state_from_pattern_key(pattern_key):
    """Extract S1/S2/S3 from pattern_key"""
    if not pattern_key:
        return None
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
    perf = PerformanceDataAccess(sb)
    
    print("=" * 80)
    print("1M TIMEFRAME - COMPLETE ANALYSIS")
    print("=" * 80)
    
    # Get open positions
    pnl = perf.get_portfolio_pnl()
    positions = [p for p in pnl.get('positions', []) if p.get('timeframe') == '1m']
    
    # Get full position data
    position_ids = [p.get('id') for p in positions if p.get('id')]
    db_positions = {}
    if position_ids:
        try:
            db_data = sb.table('lowcap_positions').select('id, features').in_('id', position_ids).execute()
            db_positions = {p['id']: p for p in db_data.data}
        except:
            pass
    
    # Organize open positions by entry state
    open_by_state = {}
    for pos in positions:
        pos_id = pos.get('id')
        entry_state = None
        
        full_pos = db_positions.get(pos_id, {})
        features = full_pos.get('features', {})
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
                        break
        
        if not entry_state:
            entry_state = 'Unknown'
        
        if entry_state not in open_by_state:
            open_by_state[entry_state] = []
        
        open_by_state[entry_state].append({
            'ticker': pos.get('ticker', 'N/A'),
            'pnl_usd': pos.get('total_pnl_usd', 0),
            'pnl_pct': pos.get('total_pnl_pct', 0),
            'allocated': pos.get('allocated_usd', 0)
        })
    
    # Get closed trades
    closed_trades = [t for t in perf.get_closed_trades_over_period(None) if t.get('timeframe') == '1m']
    
    # Organize closed trades by entry state
    closed_by_state = {}
    for trade in closed_trades:
        entry_state = trade.get('entry_state', 'Unknown')
        if entry_state not in closed_by_state:
            closed_by_state[entry_state] = []
        closed_by_state[entry_state].append(trade)
    
    # Display
    print("\n📈 OPEN POSITIONS (1m):")
    print("-" * 80)
    
    if positions:
        total_open_pnl = sum(p['pnl_usd'] for p in positions)
        total_open_alloc = sum(p['allocated'] for p in positions)
        open_roi = (total_open_pnl / total_open_alloc * 100) if total_open_alloc > 0 else 0
        open_wins = [p for p in positions if p['pnl_usd'] > 0]
        
        print(f"  Total: {len(positions)} positions | ${total_open_pnl:.2f} PnL | {open_roi:.1f}% avg ROI | {len(open_wins)}/{len(positions)} wins")
        
        for state in ['S1', 'S2', 'S3', 'Unknown']:
            if state in open_by_state:
                state_positions = open_by_state[state]
                total_pnl = sum(p['pnl_usd'] for p in state_positions)
                total_alloc = sum(p['allocated'] for p in state_positions)
                avg_roi = (total_pnl / total_alloc * 100) if total_alloc > 0 else 0
                wins = [p for p in state_positions if p['pnl_usd'] > 0]
                
                print(f"\n  {state} Entry ({len(state_positions)} positions):")
                print(f"    Total PnL: ${total_pnl:.2f}")
                print(f"    Total Allocated: ${total_alloc:.2f}")
                print(f"    Avg ROI: {avg_roi:.1f}%")
                print(f"    Win Rate: {len(wins)}/{len(state_positions)} ({len(wins)/len(state_positions)*100:.1f}%)")
                
                for p in sorted(state_positions, key=lambda x: x['pnl_usd'], reverse=True):
                    emoji = "✅" if p['pnl_usd'] > 0 else "❌" if p['pnl_usd'] < 0 else "➖"
                    print(f"      {emoji} {p['ticker']}: ${p['pnl_usd']:.2f} ({p['pnl_pct']:.1f}%)")
    else:
        print("  No open 1m positions")
    
    print("\n📉 CLOSED TRADES (1m):")
    print("-" * 80)
    
    if closed_trades:
        total_closed_pnl = sum(t['rpnl_usd'] for t in closed_trades)
        closed_roi = sum(t['rpnl_pct'] for t in closed_trades) / len(closed_trades) if closed_trades else 0
        closed_wins = [t for t in closed_trades if t['rpnl_usd'] > 0]
        
        print(f"  Total: {len(closed_trades)} trades | ${total_closed_pnl:.2f} PnL | {closed_roi:.1f}% avg ROI | {len(closed_wins)}/{len(closed_trades)} wins ({len(closed_wins)/len(closed_trades)*100:.1f}%)")
        
        for state in ['S1', 'S2', 'S3', 'Unknown']:
            if state in closed_by_state:
                state_trades = closed_by_state[state]
                total_pnl = sum(t['rpnl_usd'] for t in state_trades)
                avg_roi = sum(t['rpnl_pct'] for t in state_trades) / len(state_trades) if state_trades else 0
                wins = [t for t in state_trades if t['rpnl_usd'] > 0]
                
                print(f"\n  {state} Entry ({len(state_trades)} trades):")
                print(f"    Total PnL: ${total_pnl:.2f}")
                print(f"    Avg ROI: {avg_roi:.1f}%")
                print(f"    Win Rate: {len(wins)}/{len(state_trades)} ({len(wins)/len(state_trades)*100:.1f}%)")
                
                # Show recent trades
                for t in sorted(state_trades, key=lambda x: x.get('exit_timestamp', ''), reverse=True)[:5]:
                    emoji = "✅" if t['rpnl_usd'] > 0 else "❌"
                    print(f"      {emoji} {t['token_ticker']}: ${t['rpnl_usd']:.2f} ({t['rpnl_pct']:.1f}%)")
    else:
        print("  No closed 1m trades")
    
    # Comparison
    if positions and closed_trades:
        print("\n🔍 COMPARISON (1m):")
        print("-" * 80)
        print(f"  Open: {open_roi:.1f}% avg ROI, {len(open_wins)}/{len(positions)} wins ({len(open_wins)/len(positions)*100:.1f}%)")
        print(f"  Closed: {closed_roi:.1f}% avg ROI, {len(closed_wins)}/{len(closed_trades)} wins ({len(closed_wins)/len(closed_trades)*100:.1f}%)")
        
        if open_roi > closed_roi:
            print(f"  → Open positions performing better (cutting losers, holding winners?)")
        else:
            print(f"  → Closed trades performed better")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

