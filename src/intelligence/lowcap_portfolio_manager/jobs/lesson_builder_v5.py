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
# Variance shrinkage prior for small-N reliability correction
VAR_PRIOR = 0.25  # Tune based on expected RR variance (0.25 = reasonable default)
# We'll dynamically determine dims from data, or stick to this list to be safe
SCOPE_DIMS = [
    "curator", "chain", "mcap_bucket", "vol_bucket", "age_bucket", "intent",
    "mcap_vol_ratio_bucket", "market_family", "timeframe",
    "A_mode", "E_mode",
    "bucket_leader", "bucket_rank_position",
    # Regime states (drivers × horizons)
    "btc_macro", "btc_meso", "btc_micro",
    "alt_macro", "alt_meso", "alt_micro",
    "bucket_macro", "bucket_meso", "bucket_micro",
    "btcd_macro", "btcd_meso", "btcd_micro",
    "usdtd_macro", "usdtd_meso", "usdtd_micro",
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

def estimate_half_life(edge_history: List[Tuple[float, datetime]]) -> Optional[float]:
    """
    Estimate exponential decay half-life from edge history.
    
    Fits exponential decay toward zero: |y(t)| = |y_0| * exp(-lambda * t)
    Works for both positive and negative values by using absolute values for fitting.
    Model: y(t) = sign(y_0) * |y_0| * exp(-lambda * t) (decays toward zero)
    
    Args:
        edge_history: List of (edge_value, timestamp) tuples, sorted by time
        
    Returns:
        Half-life in hours, or None if insufficient data or fit fails
    """
    if len(edge_history) < 5:
        return None
    
    # Sort by timestamp (should already be sorted, but be safe)
    sorted_history = sorted(edge_history, key=lambda x: x[1])
    
    # Extract times and values
    t0 = sorted_history[0][1]
    times = []
    values = []
    
    for edge_val, ts in sorted_history:
        hours = (ts - t0).total_seconds() / 3600.0
        times.append(hours)
        values.append(edge_val)
    
    # Check if values cross zero (change sign)
    signs = [1 if v > 0 else (-1 if v < 0 else 0) for v in values]
    has_positive = any(s > 0 for s in signs)
    has_negative = any(s < 0 for s in signs)
    crosses_zero = has_positive and has_negative
    
    if crosses_zero:
        # If values cross zero, use the more recent segment (after zero-crossing)
        # Find the zero-crossing point
        zero_cross_idx = None
        for i in range(1, len(values)):
            if (values[i-1] > 0 and values[i] <= 0) or (values[i-1] < 0 and values[i] >= 0):
                zero_cross_idx = i
                break
        
        if zero_cross_idx is not None and len(values) - zero_cross_idx >= 5:
            # Use segment after zero-crossing
            times = times[zero_cross_idx:]
            values = values[zero_cross_idx:]
        elif zero_cross_idx is not None and zero_cross_idx >= 5:
            # Use segment before zero-crossing
            times = times[:zero_cross_idx]
            values = values[:zero_cross_idx]
        else:
            # Not enough data on either side, can't fit reliably
            return None
    
    # Use absolute values for fitting (exponential decay toward zero)
    # Filter out zero values (can't take log)
    abs_pairs = [(t, abs(v)) for t, v in zip(times, values) if abs(v) > 1e-9]
    if len(abs_pairs) < 5:
        return None
    
    abs_times = [t for t, _ in abs_pairs]
    abs_values = [v for _, v in abs_pairs]
    
    # Fit exponential decay: |y| = |y_0| * exp(-lambda * t)
    # Take log: ln(|y|) = ln(|y_0|) - lambda * t
    log_values = [math.log(v) for v in abs_values]
    
    # Linear regression: ln(|y|) = a + b*t, where b = -lambda
    slope = _linear_regression(abs_times, log_values)
    
    # If slope is positive or near zero, pattern is improving or stable (no decay)
    if slope >= -1e-6:
        return None  # No decay to measure (pattern is improving or stable)
    
    # lambda = -slope
    lambda_val = -slope
    
    # Half-life: t_half = ln(2) / lambda
    if lambda_val > 0:
        half_life_hours = math.log(2) / lambda_val
        # Clamp to reasonable range (1 hour to 1 year)
        half_life_hours = max(1.0, min(8760.0, half_life_hours))
        return half_life_hours
    
    return None

def fit_decay_curve(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Fit decay curve to event series (RR over time).
    Uses exponential decay to compute half-life.
    Returns decay metadata.
    """
    if len(events) < 5:
        return {"state": "insufficient", "multiplier": 1.0, "half_life_hours": None}
    
    # Sort by timestamp
    sorted_events = sorted(events, key=lambda x: x['timestamp'])
    
    # Extract (t, rr) for exponential decay fitting
    t0 = datetime.fromisoformat(sorted_events[0]['timestamp'].replace('Z', '+00:00'))
    
    edge_history = []
    for e in sorted_events:
        ts = datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00'))
        rr = float(e['rr'])
        edge_history.append((rr, ts))
    
    # Estimate half-life using exponential decay
    half_life_hours = estimate_half_life(edge_history)
    
    # Also compute linear slope for state detection (backward compat)
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
    
    # Calculate decay multiplier based on half-life if available, otherwise use slope
    mult = 1.0
    if half_life_hours:
        # If half-life is short (< 7 days), apply decay multiplier
        # Longer half-life = more stable = higher multiplier
        if half_life_hours < 168:  # 7 days
            # Decay multiplier based on half-life quality
            # 1 day = 0.5, 7 days = 0.9, 30+ days = 1.0
            half_life_quality = min(1.0, half_life_hours / 168.0)
            mult = 0.5 + 0.5 * half_life_quality
        else:
            mult = 1.0  # Stable pattern
    else:
        # Fallback to slope-based multiplier (backward compat)
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
        "half_life_hours": half_life_hours
    }

def compute_lesson_stats(events: List[Dict[str, Any]], global_baseline_rr: float) -> Dict[str, Any]:
    """Compute aggregate stats for a set of events (6-D Edge Math)."""
    if not events:
        return {}

    rrs = [float(e['rr']) for e in events]
    n = len(rrs)
    avg_rr = sum(rrs) / n
    variance = statistics.variance(rrs) if n > 1 else 0.0
    
    # Only fit decay if we have enough samples (N_MIN_SLICE)
    if n >= N_MIN_SLICE:
        decay_meta = fit_decay_curve(events)
    else:
        decay_meta = {"state": "insufficient", "multiplier": 1.0}
    
    # --- 6-D Edge Components (V5) ---
    delta_rr = avg_rr - global_baseline_rr
    
    # Scores (0-1 normalized)
    ev_score = _sigmoid(delta_rr / 0.5)
    
    # Variance shrinkage prior for small-N reliability correction
    # Prevents over-trusting tiny samples (variance=0 → reliability=1.0)
    # Prior shrinks as n grows, becoming negligible for large samples
    prior_variance = VAR_PRIOR / max(1, n)
    adjusted_variance = variance + prior_variance
    reliability_score = 1.0 / (1.0 + adjusted_variance)
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

                # FIX: Trade-normalized learning - deduplicate by trade_id within this slice
                # Multiple actions from the same trade share the same outcome (final trade R/R)
                # We must count distinct trades, not actions, to maintain statistical independence
                if 'trade_id' in slice_df.columns:
                    deduplicated = slice_df.drop_duplicates(subset=['trade_id'], keep='first')
                    # Check if we still have enough after deduplication
                    if len(deduplicated) < N_MIN_SLICE:
                        return
                    slice_df = deduplicated
                else:
                    logger.warning(f"trade_id column missing in slice_df, skipping deduplication")
                
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
                    # Note: After deduplication, counts are per trade, not per action
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
