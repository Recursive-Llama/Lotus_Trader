"""
Lesson Builder v5 - Mining from Fact Table
Replaces legacy stat-reading with raw event mining.

Goals:
1. Scan pattern_trade_events for slices with N >= N_min.
2. Recursively mine ALL valid scope combinations (Apriori).
3. Compute edge stats (avg_rr, decay slope) for valid slices.
4. Upsert to learning_lessons.
"""

import logging
import os
import json
import math
import statistics
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import pandas as pd

from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Mining Config
N_MIN_SLICE = 33
# We'll dynamically determine dims from data, or stick to this list to be safe
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
    
    state = "stable"
    if slope < -0.001:
        state = "decaying"
    elif slope > 0.001:
        state = "improving"
        
    # Calculate simple decay multiplier for Override usage
    mult = 1.0
    if state == "decaying":
        severity = min(abs(slope) * 100, 0.5) 
        mult = max(0.5, 1.0 - severity)
    elif state == "improving":
        severity = min(abs(slope) * 100, 0.5)
        mult = min(1.5, 1.0 + severity)
    
    return {
        "state": state,
        "slope": slope,
        "multiplier": mult,
        "half_life_hours": None 
    }

def compute_lesson_stats(events: List[Dict[str, Any]], global_baseline_rr: float) -> Dict[str, Any]:
    """Compute aggregate stats for a set of events (6-D Edge Math)."""
    if not events:
        return {}

    rrs = [float(e['rr']) for e in events]
    n = len(rrs)
    avg_rr = sum(rrs) / n
    variance = statistics.variance(rrs) if n > 1 else 0.0
    
    decay_meta = fit_decay_curve(events)
    
    # --- 6-D Edge Components (V5) ---
    delta_rr = avg_rr - global_baseline_rr
    
    # Scores (0-1 normalized)
    ev_score = _sigmoid(delta_rr / 0.5)
    reliability_score = 1.0 / (1.0 + variance)
    support_score = 1.0 - math.exp(-n / 50.0)
    magnitude_score = _sigmoid(avg_rr / 1.0) 
    
    time_score = 1.0 
    stability_score = 1.0 / (1.0 + variance) 
    
    integral = support_score + magnitude_score + time_score + stability_score
    edge_raw = delta_rr * reliability_score * integral * decay_meta.get('multiplier', 1.0)
    
    return {
        "avg_rr": avg_rr,
        "global_baseline_rr": global_baseline_rr,
        "delta_rr": delta_rr,
        "variance": variance,
        "n": n,
        "edge_raw": edge_raw,
        "ev_score": ev_score,
        "reliability_score": reliability_score,
        "support_score": support_score,
        "magnitude_score": magnitude_score,
        "time_score": time_score,
        "stability_score": stability_score,
        "decay_meta": decay_meta
    }

async def mine_lessons(sb_client: Client, module: str = 'pm') -> int:
    """
    Miner: Scans pattern_trade_events -> writes learning_lessons.
    Uses Recursive Apriori to find ALL valid scope combinations.
    """
    try:
        # 1. Fetch events
        # Calculate Global Baseline (Dynamic)
        baseline_res = sb_client.table('pattern_trade_events').select('rr').execute()
        all_rrs = [r['rr'] for r in baseline_res.data or []]
        if not all_rrs:
            logger.info("No events to mine.")
            return 0
        
        global_baseline_rr = sum(all_rrs) / len(all_rrs)
        logger.info(f"Dynamic Global Baseline RR: {global_baseline_rr:.3f} (N={len(all_rrs)})")
        
        # Fetch events for processing (Limit 5000 for safety in this iteration)
        res = sb_client.table('pattern_trade_events').select('*').order('timestamp', desc=True).limit(5000).execute()
        events = res.data or []
        
        # Use Pandas for fast filtering
        df = pd.DataFrame(events)
        
        # Flatten scope columns
        scope_keys = set()
        for scope in df['scope']:
            if isinstance(scope, dict):
                scope_keys.update(scope.keys())
        
        # Filter relevant dims only
        valid_dims = sorted([k for k in scope_keys if k in SCOPE_DIMS])
        
        for key in valid_dims:
            df[f"scope_{key}"] = df['scope'].apply(lambda x: x.get(key) if isinstance(x, dict) else None)
            
        lessons_to_write = []
        
        # Group by (pattern_key, category) first - these are hard boundaries
        # We don't mix S1 entries with S3 exits
        
        # Create a composite key column for grouping
        df['group_key'] = list(zip(df['pattern_key'], df['action_category']))
        grouped = df.groupby('group_key')
        
        for (pk, cat), group_df in grouped:
            if len(group_df) < N_MIN_SLICE:
                continue
                
            # Recursive Mining Function for this Pattern Group
            def mine_recursive(slice_df: pd.DataFrame, current_mask: Dict[str, Any], start_dim_idx: int):
                # Base Case: Prune
                if len(slice_df) < N_MIN_SLICE:
                    return

                # Process Current Node
                # Convert DF rows back to list of dicts for existing helper (or rewrite helper)
                # Helper expects raw event dicts. We can reconstruct or just pass relevant columns.
                # Actually, fit_decay_curve needs timestamp and rr.
                slice_events = slice_df[['rr', 'timestamp']].to_dict('records')
                
                stats = compute_lesson_stats(slice_events, global_baseline_rr)
                
                # Queue Lesson
                lesson = {
                    "module": module,
                    "pattern_key": pk,
                    "action_category": cat,
                    "scope_subset": current_mask,
                    "lesson_type": "pm_strength",
                    "n": stats['n'],
                    "stats": stats,
                    "decay_halflife_hours": stats['decay_meta'].get('half_life_hours'),
                    "status": "active",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                lessons_to_write.append(lesson)
                
                # Recursive Step
                for i in range(start_dim_idx, len(valid_dims)):
                    dim = valid_dims[i]
                    col = f"scope_{dim}"
                    
                    # Apriori Check: Which values for this dim are frequent in current slice?
                    counts = slice_df[col].value_counts()
                    valid_values = counts[counts >= N_MIN_SLICE].index.tolist()
                    
                    for val in valid_values:
                        new_mask = current_mask.copy()
                        new_mask[dim] = val
                        
                        # Filter
                        new_slice = slice_df[slice_df[col] == val]
                        
                        # Recurse
                        mine_recursive(new_slice, new_mask, i + 1)

            # Start recursion for this pattern group
            mine_recursive(group_df, {}, 0)

        # Bulk Write
        if lessons_to_write:
            # Upsert in batches
            BATCH_SIZE = 100
            for i in range(0, len(lessons_to_write), BATCH_SIZE):
                batch = lessons_to_write[i:i+BATCH_SIZE]
                await upsert_lessons_batch(sb_client, batch)
                
        logger.info(f"Mined {len(lessons_to_write)} lessons from {len(events)} events.")
        return len(lessons_to_write)
        
    except Exception as e:
        logger.error(f"Mining failed: {e}", exc_info=True)
        return 0

async def upsert_lessons_batch(sb: Client, batch: List[Dict]):
    try:
        sb.table("learning_lessons").upsert(
            batch, 
            on_conflict="module,pattern_key,action_category,scope_subset"
        ).execute()
    except Exception as e:
        logger.warning(f"Lesson batch upsert failed: {e}")

async def build_lessons_from_pattern_scope_stats(sb_client: Client, module: str = 'pm', **kwargs) -> int:
    """Wrapper for backward compat."""
    return await mine_lessons(sb_client, module)

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    # Needs .env loaded
    from dotenv import load_dotenv
    load_dotenv()
    
    result = asyncio.run(mine_lessons(create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))))
    print(result)
