"""
Lesson Builder v5 - Mining from Fact Table
Replaces legacy stat-reading with raw event mining.

Goals:
1. Scan pattern_trade_events for slices with N >= N_min.
2. Compute edge stats (avg_rr, decay slope) for valid slices.
3. Upsert to learning_lessons.
"""

import logging
import os
import json
import math
import statistics
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from itertools import combinations

from supabase import create_client, Client

# Optional imports for curve fitting
try:
    import numpy as np
    from scipy.optimize import curve_fit
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

logger = logging.getLogger(__name__)

# Mining Config
N_MIN_SLICE = 33
SCOPE_DIMS = [
    "curator", "chain", "mcap_bucket", "vol_bucket", "age_bucket", "intent",
    "mcap_vol_ratio_bucket", "market_family", "timeframe",
    "A_mode", "E_mode", "macro_phase", "meso_phase", "micro_phase",
    "bucket_leader", "bucket_rank_position"
]

def _sigmoid(x: float) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0

def _linear_regression(times: List[float], values: List[float]) -> float:
    if len(times) < 2:
        return 0.0
    n = len(times)
    sum_t = sum(times)
    sum_v = sum(values)
    sum_t2 = sum(t * t for t in times)
    sum_tv = sum(t * v for t, v in zip(times, values))
    denom = n * sum_t2 - sum_t * sum_t
    if abs(denom) < 1e-9:
        return 0.0
    return (n * sum_tv - sum_t * sum_v) / denom

def fit_decay_curve(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Fit decay curve to event series (RR over time).
    Returns decay metadata.
    """
    if len(events) < 5:
        return {"state": "insufficient", "multiplier": 1.0}
        
    # Sort by timestamp
    # events are assumed sorted or we sort them
    sorted_events = sorted(events, key=lambda x: x['timestamp'])
    
    # Extract (t, rr)
    # Normalize t to hours from start
    t0 = datetime.fromisoformat(sorted_events[0]['timestamp'].replace('Z', '+00:00'))
    
    times = []
    values = []
    
    for e in sorted_events:
        ts = datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00'))
        hours = (ts - t0).total_seconds() / 3600.0
        rr = float(e['rr'])
        times.append(hours)
        values.append(rr)
        
    slope = _linear_regression(times, values)
    
    # Exponential fit?
    # y = A * exp(B * t)
    # ln(y) = ln(A) + B*t
    # Only works if rr > 0. Shift if needed?
    # For now, linear slope on Rolling RR is robust.
    
    state = "stable"
    if slope < -0.001:
        state = "decaying"
    elif slope > 0.001:
        state = "improving"
        
    # Calculate simple decay multiplier for Override usage
    # If decaying fast, mult < 1.0
    mult = 1.0
    if state == "decaying":
        # E.g. -0.01 slope -> 0.9x?
        # Clamp reasonably
        severity = min(abs(slope) * 100, 0.5) # 0.01 slope -> 1.0 severity? No.
        mult = max(0.5, 1.0 - severity)
    elif state == "improving":
        severity = min(abs(slope) * 100, 0.5)
        mult = min(1.5, 1.0 + severity)
        
    return {
        "state": state,
        "slope": slope,
        "multiplier": mult,
        "half_life_hours": None # Todo: calc if exp fit
    }

def compute_lesson_stats(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aggregate stats for a set of events."""
    if not events:
        return {}
        
    rrs = [float(e['rr']) for e in events]
    n = len(rrs)
    avg_rr = sum(rrs) / n
    variance = statistics.variance(rrs) if n > 1 else 0.0
    
    decay_meta = fit_decay_curve(events)
    
    # 6-D Edge Components (simplified V5)
    # EV = avg_rr (or delta from 1.0?)
    # Let's use raw avg_rr for magnitude
    
    ev_score = _sigmoid((avg_rr - 1.0) / 0.5) # Centered at 1.0
    reliability_score = 1.0 / (1.0 + variance)
    support_score = 1.0 - math.exp(-n / 50.0)
    
    # Edge Raw = Geometric mean? Or weighted sum?
    # V5 Plan: EV * Rel * Integral
    # Simple version:
    edge_raw = (avg_rr - 1.0) * reliability_score * support_score * decay_meta.get('multiplier', 1.0)
    
    return {
        "avg_rr": avg_rr,
        "variance": variance,
        "n": n,
        "edge_raw": edge_raw,
        "ev_score": ev_score,
        "reliability_score": reliability_score,
        "support_score": support_score,
        "decay_meta": decay_meta
    }

async def mine_lessons(sb_client: Client, module: str = 'pm') -> int:
    """
    Miner: Scans pattern_trade_events -> writes learning_lessons.
    """
    try:
        # 1. Fetch all events (In production, window this or chunk it)
        # V1: Fetch all. If > 10k rows, we need pagination/grouping in SQL.
        # Better V1: Fetch DISTINCT pattern_keys, then process per pattern.
        
        patterns = sb_client.table('pattern_trade_events').select('pattern_key').eq('action_category', 'entry').execute() # Just entries for now? Or trims?
        # Actually we want to mine trims too.
        
        # Get unique (pattern, category) pairs
        # PostgREST doesn't do distinct nicely without RPC.
        # Just fetch raw events limit 10000 order desc?
        
        # Let's fetch all events for now (assuming low volume start)
        res = sb_client.table('pattern_trade_events').select('*').order('timestamp', desc=True).limit(2000).execute()
        events = res.data or []
        
        if not events:
            logger.info("No events to mine.")
            return 0
            
        # Group by (pattern_key, category)
        groups = {}
        for e in events:
            key = (e['pattern_key'], e['action_category'])
            if key not in groups:
                groups[key] = []
            groups[key].append(e)
            
        lessons_created = 0
        
        for (pk, cat), group_events in groups.items():
            # 2. Level 1 Mining: Single Dims
            # Iterate dimensions, group events by value
            
            # Also "Full Pattern" (Global)
            if len(group_events) >= N_MIN_SLICE:
                stats = compute_lesson_stats(group_events)
                await upsert_lesson(sb_client, module, pk, cat, {}, stats)
                lessons_created += 1
            
            # Single Dims
            for dim in SCOPE_DIMS:
                # Bucket by value
                buckets = {}
                for e in group_events:
                    val = e.get('scope', {}).get(dim)
                    if val:
                        if val not in buckets:
                            buckets[val] = []
                        buckets[val].append(e)
                
                for val, slice_events in buckets.items():
                    if len(slice_events) >= N_MIN_SLICE:
                        # Found a stable slice!
                        subset = {dim: val}
                        stats = compute_lesson_stats(slice_events)
                        await upsert_lesson(sb_client, module, pk, cat, subset, stats)
                        lessons_created += 1
                        
        logger.info(f"Mined {lessons_created} lessons from {len(events)} events.")
        return lessons_created

    except Exception as e:
        logger.error(f"Mining failed: {e}")
        return 0

async def upsert_lesson(sb: Client, module: str, pk: str, cat: str, subset: Dict, stats: Dict):
    try:
        # Payload
        decay_meta = stats.get('decay_meta', {})
        
        payload = {
            "module": module,
            "pattern_key": pk,
            "action_category": cat,
            "scope_subset": subset,
            "lesson_type": "pm_strength",
            "n": stats['n'],
            "stats": stats,
            "decay_halflife_hours": decay_meta.get('half_life_hours'),
            "status": "active",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Upsert using the new V5 constraint
        # UNIQUE (module, pattern_key, action_category, scope_subset)
        sb.table("learning_lessons").upsert(
            payload, 
            on_conflict="module,pattern_key,action_category,scope_subset"
        ).execute()
        
    except Exception as e:
        logger.warning(f"Lesson upsert failed: {e}")

async def build_lessons_from_pattern_scope_stats(sb_client: Client, module: str = 'pm', **kwargs) -> int:
    """Wrapper for backward compat."""
    return await mine_lessons(sb_client, module)

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(mine_lessons(create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))))
    print(result)
