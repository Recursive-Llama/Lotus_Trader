"""
Check position states and transition conditions.
Query database to see if positions are stuck or transitions are being blocked.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment
load_dotenv()

def check_position_states():
    """Check all positions and analyze their states and transition conditions."""
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL and SUPABASE_KEY required")
        return
    
    sb: Client = create_client(supabase_url, supabase_key)
    
    # Get all positions with their features
    result = (
        sb.table("lowcap_positions")
        .select("id,token_ticker,token_contract,token_chain,timeframe,status,total_quantity,bars_count,features")
        .in_("status", ["watchlist", "active"])
        .limit(1000)
        .execute()
    )
    
    positions = result.data or []
    
    print(f"\n{'='*80}")
    print(f"Position State Analysis ({len(positions)} positions)")
    print(f"{'='*80}\n")
    
    # Group by timeframe
    by_timeframe = {}
    by_state = {}
    stuck_in_s4 = []
    s0_could_transition = []
    s0_blocked_by_exit = []
    
    for pos in positions:
        tf = pos.get("timeframe", "unknown")
        features = pos.get("features") or {}
        uptrend = features.get("uptrend_engine_v4") or {}
        
        state = uptrend.get("state", "unknown")
        prev_state = uptrend.get("prev_state", "")
        exit_position = uptrend.get("exit_position", False)
        exit_reason = uptrend.get("exit_reason", "")
        
        # Get EMA values
        ema_vals = uptrend.get("ema", {})
        ema20 = ema_vals.get("ema20", 0.0)
        ema30 = ema_vals.get("ema30", 0.0)
        ema60 = ema_vals.get("ema60", 0.0)
        ema144 = ema_vals.get("ema144", 0.0)
        ema250 = ema_vals.get("ema250", 0.0)
        ema333 = ema_vals.get("ema333", 0.0)
        price = uptrend.get("price", 0.0)
        
        # Check conditions
        bottom_ema = min(ema60, ema144, ema250, ema333) if all([ema60, ema144, ema250, ema333]) else 0.0
        fast_band_at_bottom = (ema20 < bottom_ema) and (ema30 < bottom_ema) if bottom_ema > 0 else False
        fast_band_above_60 = (ema20 > ema60) and (ema30 > ema60) if ema60 > 0 else False
        price_above_60 = price > ema60 if ema60 > 0 else False
        
        # Track by timeframe
        if tf not in by_timeframe:
            by_timeframe[tf] = {"total": 0, "by_state": {}}
        by_timeframe[tf]["total"] += 1
        by_timeframe[tf]["by_state"][state] = by_timeframe[tf]["by_state"].get(state, 0) + 1
        
        # Track by state
        if state not in by_state:
            by_state[state] = []
        by_state[state].append({
            "ticker": pos.get("token_ticker", "?"),
            "tf": tf,
            "qty": pos.get("total_quantity", 0.0),
            "exit_position": exit_position,
            "exit_reason": exit_reason
        })
        
        # Check for stuck S4
        if state == "S4":
            stuck_in_s4.append({
                "ticker": pos.get("token_ticker", "?"),
                "tf": tf,
                "contract": pos.get("token_contract", "")[:8]
            })
        
        # Check S0 positions that could transition
        if state == "S0" and prev_state == "S0":
            if fast_band_above_60 and price_above_60:
                # Could transition but might be blocked
                if fast_band_at_bottom:
                    s0_blocked_by_exit.append({
                        "ticker": pos.get("token_ticker", "?"),
                        "tf": tf,
                        "qty": pos.get("total_quantity", 0.0),
                        "ema20": ema20,
                        "ema30": ema30,
                        "ema60": ema60,
                        "price": price
                    })
                else:
                    s0_could_transition.append({
                        "ticker": pos.get("token_ticker", "?"),
                        "tf": tf,
                        "qty": pos.get("total_quantity", 0.0),
                        "ema20": ema20,
                        "ema30": ema30,
                        "ema60": ema60,
                        "price": price
                    })
    
    # Print summary
    print("📊 Positions by Timeframe:")
    for tf in sorted(by_timeframe.keys()):
        print(f"\n  {tf}:")
        for state, count in sorted(by_timeframe[tf]["by_state"].items()):
            print(f"    {state}: {count}")
    
    print(f"\n{'='*80}")
    print("🔍 Analysis")
    print(f"{'='*80}\n")
    
    print(f"Positions stuck in S4 (no clear alignment): {len(stuck_in_s4)}")
    if stuck_in_s4:
        print("  Examples:")
        for p in stuck_in_s4[:10]:
            print(f"    {p['ticker']} ({p['tf']})")
    
    print(f"\nS0 positions that COULD transition S0 → S1 (conditions met): {len(s0_could_transition)}")
    if s0_could_transition:
        print("  These should transition but aren't:")
        for p in s0_could_transition[:5]:
            print(f"    {p['ticker']} ({p['tf']}): EMA20={p['ema20']:.4f}, EMA30={p['ema30']:.4f}, EMA60={p['ema60']:.4f}, Price={p['price']:.4f}")
    
    print(f"\nS0 positions BLOCKED by global exit check: {len(s0_blocked_by_exit)}")
    if s0_blocked_by_exit:
        print("  These could transition but global exit check blocks them:")
        for p in s0_blocked_by_exit[:5]:
            print(f"    {p['ticker']} ({p['tf']}): EMA20={p['ema20']:.4f}, EMA30={p['ema30']:.4f}, EMA60={p['ema60']:.4f}, Price={p['price']:.4f}")
    
    print(f"\n{'='*80}")
    print("State Distribution:")
    for state in sorted(by_state.keys()):
        count = len(by_state[state])
        print(f"  {state}: {count} positions")
        if state == "S0":
            with_exit = sum(1 for p in by_state[state] if p["exit_position"])
            print(f"    → {with_exit} with exit_position=True")
    
    print(f"\n{'='*80}")
    print("🔬 Detailed Analysis - 1m Positions in S4:")
    print(f"{'='*80}\n")
    
    # Check 1m S4 positions in detail
    s4_1m = []
    for pos in positions:
        if pos.get("timeframe") == "1m":
            features = pos.get("features") or {}
            uptrend = features.get("uptrend_engine_v4") or {}
            state = uptrend.get("state", "unknown")
            
            if state == "S4":
                ema_vals = uptrend.get("ema", {})
                ema20 = ema_vals.get("ema20", 0.0)
                ema30 = ema_vals.get("ema30", 0.0)
                ema60 = ema_vals.get("ema60", 0.0)
                ema144 = ema_vals.get("ema144", 0.0)
                ema250 = ema_vals.get("ema250", 0.0)
                ema333 = ema_vals.get("ema333", 0.0)
                price = uptrend.get("price", 0.0)
                
                # Check S0 order
                fast_below_mid = (ema20 < ema60) and (ema30 < ema60) if ema60 > 0 else False
                slow_descending = (ema60 < ema144) and (ema144 < ema250) and (ema250 < ema333) if all([ema60, ema144, ema250, ema333]) else False
                s0_order = fast_below_mid and slow_descending
                
                # Check S3 order
                fast_above_mid = (ema20 > ema60) and (ema30 > ema60) if ema60 > 0 else False
                slow_ascending = (ema60 > ema144) and (ema144 > ema250) and (ema250 > ema333) if all([ema60, ema144, ema250, ema333]) else False
                s3_order = fast_above_mid and slow_ascending
                
                bars_count = pos.get("bars_count")  # Get from database, not features
                s4_1m.append({
                    "ticker": pos.get("token_ticker", "?"),
                    "bars": bars_count,
                    "s0_order": s0_order,
                    "s3_order": s3_order,
                    "ema20": ema20,
                    "ema30": ema30,
                    "ema60": ema60,
                    "ema144": ema144,
                    "ema250": ema250,
                    "ema333": ema333,
                    "price": price,
                    "prev_state": uptrend.get("prev_state", "")
                })
    
    if s4_1m:
        print(f"Found {len(s4_1m)} 1m positions in S4:")
        for p in s4_1m[:10]:
            print(f"\n  {p['ticker']}:")
            print(f"    Bars: {p['bars']}")
            print(f"    Prev state: {p['prev_state']}")
            print(f"    S0 order (bearish): {p['s0_order']}")
            print(f"    S3 order (bullish): {p['s3_order']}")
            if not p['s0_order'] and not p['s3_order']:
                print(f"    ⚠️  No clear alignment - EMA structure:")
                print(f"       EMA20={p['ema20']:.4f}, EMA30={p['ema30']:.4f}, EMA60={p['ema60']:.4f}")
                print(f"       EMA144={p['ema144']:.4f}, EMA250={p['ema250']:.4f}, EMA333={p['ema333']:.4f}")
                print(f"       Price={p['price']:.4f}")
                # Check why it's not S0 or S3
                if p['ema20'] > 0 and p['ema60'] > 0:
                    fast_below = p['ema20'] < p['ema60'] and p['ema30'] < p['ema60']
                    fast_above = p['ema20'] > p['ema60'] and p['ema30'] > p['ema60']
                    print(f"       Fast below mid? {fast_below}")
                    print(f"       Fast above mid? {fast_above}")
                    if p['ema60'] > 0 and p['ema144'] > 0 and p['ema250'] > 0 and p['ema333'] > 0:
                        slow_desc = p['ema60'] < p['ema144'] < p['ema250'] < p['ema333']
                        slow_asc = p['ema60'] > p['ema144'] > p['ema250'] > p['ema333']
                        print(f"       Slow descending? {slow_desc}")
                        print(f"       Slow ascending? {slow_asc}")
    
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    check_position_states()

