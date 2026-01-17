#!/usr/bin/env python3
"""
Investigate S3 Trim Issues

This script queries positions in S3 state and analyzes:
1. Whether trim_flags are being set by uptrend engine
2. Whether trim_flags are reaching the action planner
3. Whether trims are being blocked and why
4. Episode tracking status
5. Execution history status
"""

import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

def get_s3_positions(sb: Client) -> List[Dict[str, Any]]:
    """Get all positions currently in S3 state."""
    result = (
        sb.table("lowcap_positions")
        .select("id,token_ticker,token_contract,token_chain,timeframe,status,total_quantity,features,state")
        .in_("status", ["active", "watchlist"])
        .limit(1000)
        .execute()
    )
    
    positions = result.data or []
    s3_positions = []
    
    for pos in positions:
        features = pos.get("features") or {}
        uptrend = features.get("uptrend_engine_v4") or {}
        state = uptrend.get("state", "")
        
        if state == "S3":
            s3_positions.append(pos)
    
    return s3_positions


def analyze_position(sb: Client, position: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a single S3 position for trim issues."""
    pos_id = position.get("id")
    ticker = position.get("token_ticker", "?")
    chain = position.get("token_chain", "?")
    timeframe = position.get("timeframe", "?")
    total_qty = float(position.get("total_quantity", 0.0))
    
    features = position.get("features") or {}
    uptrend = features.get("uptrend_engine_v4") or {}
    exec_history = features.get("pm_execution_history") or {}
    geometry = features.get("geometry") or {}
    ta = features.get("ta") or {}
    
    # Extract uptrend engine data
    state = uptrend.get("state", "")
    trim_flag = uptrend.get("trim_flag", False)
    scores = uptrend.get("scores") or {}
    ox_score = float(scores.get("ox", 0.0))
    price = float(uptrend.get("price", 0.0))
    uptrend_ts = uptrend.get("ts")  # When was this payload last updated?
    meta = uptrend.get("meta") or {}
    updated_at = meta.get("updated_at")
    
    # Debug: Check if scores dict exists and what keys it has
    scores_keys = list(scores.keys()) if scores else []
    scores_raw = scores  # Keep raw for debugging
    
    # Check all keys in uptrend payload
    uptrend_keys = list(uptrend.keys()) if uptrend else []
    
    # Extract execution history
    last_trim = exec_history.get("last_trim", {})
    last_trim_ts = last_trim.get("timestamp")
    last_trim_sr_level = last_trim.get("sr_level_price")
    last_trim_signal = exec_history.get("last_trim_signal", {})
    last_trim_signal_sr_level = last_trim_signal.get("sr_level_price")
    
    # Extract geometry
    sr_levels = geometry.get("levels", {}).get("sr_levels", []) if isinstance(geometry.get("levels"), dict) else []
    sr_levels_count = len(sr_levels) if sr_levels else 0
    
    # Extract ATR
    atr_data = ta.get("atr") or {}
    ta_suffix = f"_{timeframe}" if timeframe != "1h" else ""
    atr_key = f"atr{ta_suffix}"
    atr_val = float(atr_data.get(atr_key, 0.0))
    
    # Calculate SR halo and check near_sr
    sr_halo = 1.0 * atr_val if atr_val > 0 else 0.0
    near_sr = False
    closest_sr_level = None
    closest_sr_distance = float('inf')
    
    if sr_levels and atr_val > 0:
        for level in sr_levels:
            level_price = float(level.get("price") or 0.0)
            if level_price > 0:
                distance = abs(price - level_price)
                if distance <= sr_halo:
                    near_sr = True
                if distance < closest_sr_distance:
                    closest_sr_distance = distance
                    closest_sr_level = level_price
    
    # Check if trim_flag should be set
    ox_threshold = 0.65
    should_have_trim_flag = (ox_score >= ox_threshold) and near_sr
    
    # Episode tracking
    episode_meta = features.get("uptrend_episode_meta") or {}
    s3_episode = episode_meta.get("s3_episode")
    episode_trimmed = s3_episode.get("trimmed", False) if s3_episode else False
    
    # Analysis result
    analysis = {
        "position_id": str(pos_id),
        "token": f"{ticker}/{chain}",
        "timeframe": timeframe,
        "total_quantity": total_qty,
        "state": state,
        "trim_flag": trim_flag,
        "ox_score": ox_score,
        "ox_threshold": ox_threshold,
        "price": price,
        "atr_val": atr_val,
        "sr_halo": sr_halo,
        "sr_levels_count": sr_levels_count,
        "near_sr": near_sr,
        "closest_sr_level": closest_sr_level,
        "closest_sr_distance": closest_sr_distance,
        "should_have_trim_flag": should_have_trim_flag,
        "last_trim_ts": last_trim_ts,
        "last_trim_sr_level": last_trim_sr_level,
        "last_trim_signal_sr_level": last_trim_signal_sr_level,
        "episode_trimmed": episode_trimmed,
        "scores_keys": scores_keys,
        "scores_raw": scores_raw,
        "uptrend_ts": uptrend_ts,
        "updated_at": updated_at,
        "uptrend_keys": uptrend_keys,
        "issues": [],
    }
    
    # Identify issues
    if ox_score >= ox_threshold and not trim_flag:
        if not sr_levels:
            analysis["issues"].append("HIGH_OX_NO_SR_LEVELS")
        elif atr_val <= 0:
            analysis["issues"].append("HIGH_OX_INVALID_ATR")
        elif not near_sr:
            analysis["issues"].append("HIGH_OX_NOT_NEAR_SR")
            analysis["issues"].append(f"DISTANCE_TOO_FAR: {closest_sr_distance:.8f} > {sr_halo:.8f}")
        else:
            analysis["issues"].append("HIGH_OX_NEAR_SR_BUT_NO_FLAG")
    
    if trim_flag and total_qty <= 0:
        analysis["issues"].append("TRIM_FLAG_BUT_NO_TOKENS")
    
    if trim_flag and not last_trim_ts:
        analysis["issues"].append("TRIM_FLAG_BUT_NEVER_TRIMMED")
    
    return analysis


def main():
    """Main investigation function."""
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL and SUPABASE_KEY required")
        return
    
    sb: Client = create_client(supabase_url, supabase_key)
    
    print("\n" + "="*80)
    print("S3 TRIM INVESTIGATION")
    print("="*80 + "\n")
    
    # Get all S3 positions
    s3_positions = get_s3_positions(sb)
    print(f"Found {len(s3_positions)} positions in S3 state\n")
    
    if not s3_positions:
        print("No positions in S3 state. Nothing to investigate.")
        return
    
    # Analyze each position
    analyses = []
    for pos in s3_positions:
        analysis = analyze_position(sb, pos)
        analyses.append(analysis)
    
    # Group by issue type
    by_issue = {}
    high_ox_no_flag = []
    trim_flag_no_tokens = []
    no_sr_levels = []
    invalid_atr = []
    not_near_sr = []
    
    for analysis in analyses:
        issues = analysis["issues"]
        if issues:
            for issue in issues:
                if issue not in by_issue:
                    by_issue[issue] = []
                by_issue[issue].append(analysis)
        
        if analysis["ox_score"] >= 0.65 and not analysis["trim_flag"]:
            high_ox_no_flag.append(analysis)
        
        if analysis["trim_flag"] and analysis["total_quantity"] <= 0:
            trim_flag_no_tokens.append(analysis)
        
        if analysis["sr_levels_count"] == 0:
            no_sr_levels.append(analysis)
        
        if analysis["atr_val"] <= 0:
            invalid_atr.append(analysis)
        
        if analysis["ox_score"] >= 0.65 and not analysis["near_sr"] and analysis["sr_levels_count"] > 0:
            not_near_sr.append(analysis)
    
    # Print summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total S3 positions: {len(analyses)}")
    print(f"Positions with trim_flag=True: {sum(1 for a in analyses if a['trim_flag'])}")
    print(f"Positions with OX >= 0.65: {sum(1 for a in analyses if a['ox_score'] >= 0.65)}")
    print(f"Positions with OX >= 0.65 but no trim_flag: {len(high_ox_no_flag)}")
    print(f"Positions with no SR levels: {len(no_sr_levels)}")
    print(f"Positions with invalid ATR: {len(invalid_atr)}")
    print(f"Positions with trim_flag but no tokens: {len(trim_flag_no_tokens)}")
    print(f"Positions with high OX but not near SR: {len(not_near_sr)}")
    print()
    
    # Print detailed issues
    if by_issue:
        print("="*80)
        print("ISSUES BY TYPE")
        print("="*80)
        for issue_type, affected in sorted(by_issue.items()):
            print(f"\n{issue_type}: {len(affected)} positions")
            for a in affected[:5]:  # Show first 5
                print(f"  - {a['token']} tf={a['timeframe']} | ox={a['ox_score']:.4f} trim_flag={a['trim_flag']} qty={a['total_quantity']:.6f}")
            if len(affected) > 5:
                print(f"  ... and {len(affected) - 5} more")
    
    # Print detailed analysis for ALL S3 positions (to see what's actually there)
    print("\n" + "="*80)
    print("DETAILED ANALYSIS OF ALL S3 POSITIONS")
    print("="*80)
    for a in analyses[:10]:  # Show first 10
        print(f"\n{a['token']} tf={a['timeframe']} (id: {a['position_id'][:8]}...)")
        print(f"  State: {a['state']}")
        print(f"  Trim Flag: {a['trim_flag']}")
        print(f"  OX Score: {a['ox_score']:.4f} (threshold: {a['ox_threshold']:.4f})")
        print(f"  Scores keys: {a['scores_keys']}")
        if a['scores_raw']:
            print(f"  Scores raw: {a['scores_raw']}")
        print(f"  Uptrend TS: {a['uptrend_ts'] or 'N/A'}")
        print(f"  Updated At: {a['updated_at'] or 'N/A'}")
        print(f"  Uptrend keys: {a['uptrend_keys'][:10]}...")  # Show first 10 keys
        print(f"  Price: {a['price']:.8f}")
        print(f"  Quantity: {a['total_quantity']:.6f}")
        print(f"  ATR: {a['atr_val']:.8f} | SR Halo: {a['sr_halo']:.8f}")
        print(f"  SR Levels: {a['sr_levels_count']}")
        print(f"  Near SR: {a['near_sr']}")
        if a['closest_sr_level']:
            print(f"  Closest SR: {a['closest_sr_level']:.8f} (distance: {a['closest_sr_distance']:.8f})")
        print(f"  Last Trim TS: {a['last_trim_ts'] or 'Never'}")
        if a['issues']:
            print(f"  Issues: {', '.join(a['issues'])}")
    if len(analyses) > 10:
        print(f"\n... and {len(analyses) - 10} more positions")
    
    # Print detailed analysis for positions with high OX but no flag
    if high_ox_no_flag:
        print("\n" + "="*80)
        print("HIGH OX BUT NO TRIM FLAG (Most Critical)")
        print("="*80)
        for a in high_ox_no_flag:
            print(f"\n{a['token']} tf={a['timeframe']}")
            print(f"  OX Score: {a['ox_score']:.4f} (threshold: {a['ox_threshold']:.4f})")
            print(f"  Price: {a['price']:.8f}")
            print(f"  ATR: {a['atr_val']:.8f} | SR Halo: {a['sr_halo']:.8f}")
            print(f"  SR Levels: {a['sr_levels_count']}")
            print(f"  Near SR: {a['near_sr']}")
            if a['closest_sr_level']:
                print(f"  Closest SR: {a['closest_sr_level']:.8f} (distance: {a['closest_sr_distance']:.8f})")
            print(f"  Issues: {', '.join(a['issues'])}")
    
    # Print positions with trim_flag
    trim_flag_positions = [a for a in analyses if a['trim_flag']]
    if trim_flag_positions:
        print("\n" + "="*80)
        print("POSITIONS WITH TRIM_FLAG SET")
        print("="*80)
        for a in trim_flag_positions:
            print(f"\n{a['token']} tf={a['timeframe']}")
            print(f"  OX Score: {a['ox_score']:.4f}")
            print(f"  Quantity: {a['total_quantity']:.6f}")
            print(f"  Last Trim TS: {a['last_trim_ts'] or 'Never'}")
            print(f"  Episode Trimmed: {a['episode_trimmed']}")
            if a['issues']:
                print(f"  Issues: {', '.join(a['issues'])}")
    
    print("\n" + "="*80)
    print("Investigation complete!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

