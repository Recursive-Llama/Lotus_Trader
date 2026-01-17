#!/usr/bin/env python3
"""
Comprehensive Trade Analysis - Open vs Closed by Timeframe and Entry State
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
    print("COMPREHENSIVE TRADE ANALYSIS - OPEN vs CLOSED")
    print("=" * 80)
    
    # ========================================================================
    # GET OPEN POSITIONS
    # ========================================================================
    print("\n📊 GATHERING DATA...")
    print("-" * 80)
    
    pnl = perf.get_portfolio_pnl()
    positions = pnl.get('positions', [])
    
    # Get full position data for entry states
    position_ids = [p.get('id') for p in positions if p.get('id')]
    db_positions = {}
    if position_ids:
        try:
            db_data = sb.table('lowcap_positions').select('id, features').in_('id', position_ids).execute()
            db_positions = {p['id']: p for p in db_data.data}
        except:
            pass
    
    # Organize open positions
    open_by_tf_state = {}
    for pos in positions:
        tf = pos.get('timeframe', 'unknown')
        pos_id = pos.get('id')
        
        # Get entry state from execution history
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
        
        key = f"{tf}|{entry_state}"
        if key not in open_by_tf_state:
            open_by_tf_state[key] = []
        
        open_by_tf_state[key].append({
            'ticker': pos.get('ticker', 'N/A'),
            'pnl_usd': pos.get('total_pnl_usd', 0),
            'pnl_pct': pos.get('total_pnl_pct', 0),
            'allocated': pos.get('allocated_usd', 0)
        })
    
    # ========================================================================
    # GET CLOSED TRADES
    # ========================================================================
    closed_trades = perf.get_closed_trades_over_period(None)  # All time
    
    # Organize closed trades
    closed_by_tf_state = {}
    for trade in closed_trades:
        tf = trade.get('timeframe', 'unknown')
        entry_state = trade.get('entry_state', 'Unknown')
        key = f"{tf}|{entry_state}"
        
        if key not in closed_by_tf_state:
            closed_by_tf_state[key] = []
        
        closed_by_tf_state[key].append({
            'ticker': trade.get('token_ticker', 'N/A'),
            'pnl_usd': trade.get('rpnl_usd', 0),
            'pnl_pct': trade.get('rpnl_pct', 0)
        })
    
    # ========================================================================
    # DISPLAY COMPREHENSIVE ANALYSIS
    # ========================================================================
    
    for tf in ['15m', '1h', '4h']:
        print(f"\n{'='*80}")
        print(f"{tf} TIMEFRAME - COMPLETE ANALYSIS")
        print("=" * 80)
        
        # OPEN POSITIONS
        print(f"\n📈 OPEN POSITIONS ({tf}):")
        print("-" * 80)
        
        open_s1 = open_by_tf_state.get(f"{tf}|S1", [])
        open_s2 = open_by_tf_state.get(f"{tf}|S2", [])
        open_unknown = open_by_tf_state.get(f"{tf}|Unknown", [])
        
        if open_s1:
            total_pnl = sum(p['pnl_usd'] for p in open_s1)
            total_alloc = sum(p['allocated'] for p in open_s1)
            avg_roi = (total_pnl / total_alloc * 100) if total_alloc > 0 else 0
            wins = [p for p in open_s1 if p['pnl_usd'] > 0]
            print(f"  S1 Entry: {len(open_s1)} positions | ${total_pnl:.2f} PnL | {avg_roi:.1f}% avg ROI | {len(wins)}/{len(open_s1)} wins")
        
        if open_s2:
            total_pnl = sum(p['pnl_usd'] for p in open_s2)
            total_alloc = sum(p['allocated'] for p in open_s2)
            avg_roi = (total_pnl / total_alloc * 100) if total_alloc > 0 else 0
            wins = [p for p in open_s2 if p['pnl_usd'] > 0]
            print(f"  S2 Entry: {len(open_s2)} positions | ${total_pnl:.2f} PnL | {avg_roi:.1f}% avg ROI | {len(wins)}/{len(open_s2)} wins")
        
        if open_unknown:
            total_pnl = sum(p['pnl_usd'] for p in open_unknown)
            total_alloc = sum(p['allocated'] for p in open_unknown)
            avg_roi = (total_pnl / total_alloc * 100) if total_alloc > 0 else 0
            wins = [p for p in open_unknown if p['pnl_usd'] > 0]
            print(f"  Unknown Entry: {len(open_unknown)} positions | ${total_pnl:.2f} PnL | {avg_roi:.1f}% avg ROI | {len(wins)}/{len(open_unknown)} wins")
        
        if not open_s1 and not open_s2 and not open_unknown:
            print("  No open positions")
        
        # CLOSED TRADES
        print(f"\n📉 CLOSED TRADES ({tf}):")
        print("-" * 80)
        
        # Get breakdown for this timeframe
        breakdown = perf.get_performance_breakdown(None)  # All time
        
        # Filter by timeframe
        tf_trades = [t for t in closed_trades if t.get('timeframe') == tf]
        
        closed_s1 = [t for t in tf_trades if t.get('entry_state') == 'S1']
        closed_s2 = [t for t in tf_trades if t.get('entry_state') == 'S2']
        closed_unknown = [t for t in tf_trades if t.get('entry_state') not in ['S1', 'S2']]
        
        if closed_s1:
            total_pnl = sum(t['rpnl_usd'] for t in closed_s1)
            avg_roi = sum(t['rpnl_pct'] for t in closed_s1) / len(closed_s1) if closed_s1 else 0
            wins = [t for t in closed_s1 if t['rpnl_usd'] > 0]
            print(f"  S1 Entry: {len(closed_s1)} trades | ${total_pnl:.2f} PnL | {avg_roi:.1f}% avg ROI | {len(wins)}/{len(closed_s1)} wins ({len(wins)/len(closed_s1)*100:.1f}%)")
        
        if closed_s2:
            total_pnl = sum(t['rpnl_usd'] for t in closed_s2)
            avg_roi = sum(t['rpnl_pct'] for t in closed_s2) / len(closed_s2) if closed_s2 else 0
            wins = [t for t in closed_s2 if t['rpnl_usd'] > 0]
            print(f"  S2 Entry: {len(closed_s2)} trades | ${total_pnl:.2f} PnL | {avg_roi:.1f}% avg ROI | {len(wins)}/{len(closed_s2)} wins ({len(wins)/len(closed_s2)*100:.1f}%)")
        
        if closed_unknown:
            total_pnl = sum(t['rpnl_usd'] for t in closed_unknown)
            avg_roi = sum(t['rpnl_pct'] for t in closed_unknown) / len(closed_unknown) if closed_unknown else 0
            wins = [t for t in closed_unknown if t['rpnl_usd'] > 0]
            print(f"  Unknown Entry: {len(closed_unknown)} trades | ${total_pnl:.2f} PnL | {avg_roi:.1f}% avg ROI | {len(wins)}/{len(closed_unknown)} wins")
        
        if not closed_s1 and not closed_s2 and not closed_unknown:
            print("  No closed trades")
        
        # COMPARISON
        print(f"\n🔍 COMPARISON ({tf}):")
        print("-" * 80)
        
        if open_s1 and closed_s1:
            open_roi = (sum(p['pnl_usd'] for p in open_s1) / sum(p['allocated'] for p in open_s1) * 100) if sum(p['allocated'] for p in open_s1) > 0 else 0
            closed_roi = sum(t['rpnl_pct'] for t in closed_s1) / len(closed_s1) if closed_s1 else 0
            print(f"  S1: Open avg ROI {open_roi:.1f}% vs Closed avg ROI {closed_roi:.1f}%")
            if open_roi > closed_roi:
                print(f"     → Open positions performing better (cutting losers, holding winners?)")
            else:
                print(f"     → Closed trades performed better")
        
        if open_s2 and closed_s2:
            open_roi = (sum(p['pnl_usd'] for p in open_s2) / sum(p['allocated'] for p in open_s2) * 100) if sum(p['allocated'] for p in open_s2) > 0 else 0
            closed_roi = sum(t['rpnl_pct'] for t in closed_s2) / len(closed_s2) if closed_s2 else 0
            print(f"  S2: Open avg ROI {open_roi:.1f}% vs Closed avg ROI {closed_roi:.1f}%")
            if open_roi > closed_roi:
                print(f"     → Open positions performing better (cutting losers, holding winners?)")
            else:
                print(f"     → Closed trades performed better")
        
        # S1 vs S2 comparison
        if (open_s1 or closed_s1) and (open_s2 or closed_s2):
            print(f"\n  S1 vs S2:")
            if open_s1 and open_s2:
                open_s1_roi = (sum(p['pnl_usd'] for p in open_s1) / sum(p['allocated'] for p in open_s1) * 100) if sum(p['allocated'] for p in open_s1) > 0 else 0
                open_s2_roi = (sum(p['pnl_usd'] for p in open_s2) / sum(p['allocated'] for p in open_s2) * 100) if sum(p['allocated'] for p in open_s2) > 0 else 0
                print(f"    Open: S1={open_s1_roi:.1f}% vs S2={open_s2_roi:.1f}%")
            if closed_s1 and closed_s2:
                closed_s1_roi = sum(t['rpnl_pct'] for t in closed_s1) / len(closed_s1) if closed_s1 else 0
                closed_s2_roi = sum(t['rpnl_pct'] for t in closed_s2) / len(closed_s2) if closed_s2 else 0
                print(f"    Closed: S1={closed_s1_roi:.1f}% vs S2={closed_s2_roi:.1f}%")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print(f"\n{'='*80}")
    print("SUMMARY")
    print("=" * 80)
    
    # Overall open
    all_open = []
    for pos_list in open_by_tf_state.values():
        all_open.extend(pos_list)
    
    if all_open:
        total_open_pnl = sum(p['pnl_usd'] for p in all_open)
        total_open_alloc = sum(p['allocated'] for p in all_open)
        open_roi = (total_open_pnl / total_open_alloc * 100) if total_open_alloc > 0 else 0
        open_wins = [p for p in all_open if p['pnl_usd'] > 0]
        print(f"\n📈 All Open Positions: {len(all_open)} | ${total_open_pnl:.2f} PnL | {open_roi:.1f}% avg ROI | {len(open_wins)}/{len(all_open)} wins")
    
    # Overall closed
    if closed_trades:
        total_closed_pnl = sum(t['rpnl_usd'] for t in closed_trades)
        closed_roi = sum(t['rpnl_pct'] for t in closed_trades) / len(closed_trades) if closed_trades else 0
        closed_wins = [t for t in closed_trades if t['rpnl_usd'] > 0]
        print(f"📉 All Closed Trades: {len(closed_trades)} | ${total_closed_pnl:.2f} PnL | {closed_roi:.1f}% avg ROI | {len(closed_wins)}/{len(closed_trades)} wins ({len(closed_wins)/len(closed_trades)*100:.1f}%)")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

