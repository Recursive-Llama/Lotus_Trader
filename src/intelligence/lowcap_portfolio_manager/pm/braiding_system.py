"""
Braiding System - Pattern Discovery and Learning

Processes position_closed strands to:
1. Generate pattern keys from trade context
2. Update braid statistics (streaming aggregation)
3. Calculate edge scores
4. Build lessons from strong patterns

Used by: Learning System (processes position_closed strands)
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from itertools import combinations
import math

logger = logging.getLogger(__name__)


# Dimension whitelists (broader - incremental edge will filter out what doesn't matter)
ALLOWED_DM_DIMS = {
    'curator', 'chain', 'mcap_bucket', 'vol_bucket', 'age_bucket', 'intent', 
    'mapping_confidence', 'timeframe', 'mcap_vol_ratio_bucket',
    'cf_entry_improvement_bucket', 'cf_exit_improvement_bucket'
}

ALLOWED_PM_DIMS = {
    'state', 'a_bucket', 'e_bucket', 'buy_flag', 'trim_flag', 'action_type', 
    'ts_score_bucket', 'size_bucket', 'bars_since_entry_bucket',
    'reclaimed_ema333', 'first_dip_buy_flag', 'emergency_exit',
    'dx_score_bucket', 'ox_score_bucket', 'edx_score_bucket', 'ema_slopes_bucket',
    'cf_entry_improvement_bucket', 'cf_exit_improvement_bucket'
}


FIELD_DIM_NAMES = {
    'timeframe', 'mcap_bucket', 'vol_bucket', 'age_bucket', 'chain'
}


def generate_pattern_keys(context: Dict[str, Any], module: str, k: int = 3) -> List[str]:
    """
    Generate all pattern keys (all subsets up to size K) from context.
    
    Args:
        context: Dict with bucketed dimension values
        module: 'dm' or 'pm' (determines which dimensions are allowed)
        k: Maximum subset size (default 3)
    
    Returns:
        List of pattern keys (sorted, delimited strings)
    """
    # Get allowed dimensions for this module
    allowed_dims = ALLOWED_DM_DIMS if module == 'dm' else ALLOWED_PM_DIMS
    
    # Filter: only allowed dimensions, non-None values, exclude outcome (added separately)
    outcome_dims = {'outcome_class', 'hold_time_class'}
    dims = {
        k: v for k, v in context.items() 
        if k in allowed_dims and v is not None and k not in outcome_dims
    }
    
    # Require outcome_class
    if 'outcome_class' not in context:
        return []  # No patterns without outcome
    
    outcome = context['outcome_class']
    pattern_keys = []
    module_token = f"module={module}"
    
    # Generate all subsets of size 1, 2, ..., k
    for size in range(1, k + 1):
        for combo in combinations(dims.items(), size):
            # Sort by dimension name for consistency
            sorted_combo = sorted(combo, key=lambda x: x[0])
            # Create pattern key: "dim1=val1|dim2=val2|...|outcome_class=big_win"
            # Convert boolean values to lowercase strings for consistency
            pattern_key = "|".join([f"{k}={str(v).lower()}" if isinstance(v, bool) else f"{k}={v}" for k, v in sorted_combo])
            pattern_key = f"{pattern_key}|outcome_class={outcome}"  # Always include outcome
            pattern_keys.append(f"{module_token}|{pattern_key}")
    
    # Also add outcome alone
    pattern_keys.append(f"{module_token}|outcome_class={outcome}")
    
    return pattern_keys


def compute_family_id(context: Dict[str, Any], module: str = 'pm') -> str:
    """
    Compute family_id from core dimensions.
    
    For PM: module|action_type|state|outcome_class
    For DM: module|curator|chain|outcome_class
    
    Args:
        context: Context dict with dimension values
        module: 'dm' or 'pm'
    
    Returns:
        Family ID string
    """
    if module == 'pm':
        core_dims = {
            'module': module,
            'action_type': context.get('action_type'),
            'state': context.get('state'),
            'outcome_class': context.get('outcome_class')
        }
    else:  # DM
        core_dims = {
            'module': module,
            'curator': context.get('curator'),
            'chain': context.get('chain'),
            'outcome_class': context.get('outcome_class')
        }
    
    # Sort keys for consistency
    sorted_items = sorted([(k, v) for k, v in core_dims.items() if v is not None])
    return '|'.join([f"{k}={v}" for k, v in sorted_items])


def compute_parent_keys(pattern_key: str) -> List[str]:
    """
    Compute all parent pattern keys (all (k-1) subsets).
    
    Args:
        pattern_key: Pattern key like "outcome_class=big_win|state=S1|a_bucket=med|buy_flag=true"
    
    Returns:
        List of parent pattern keys
    """
    # Parse pattern key into dimensions
    dims = pattern_key.split('|')
    fixed_dims = [d for d in dims if d.startswith('module=')]
    variable_dims = [d for d in dims if not d.startswith('module=')]
    
    if len(variable_dims) <= 1:
        return []  # No parents for 1D variable patterns
    
    parent_keys = []
    for combo in combinations(variable_dims, len(variable_dims) - 1):
        parent_dims = sorted(fixed_dims + list(combo))
        parent_key = "|".join(parent_dims)
        parent_keys.append(parent_key)
    
    return parent_keys


def build_core_key_from_dimensions(dimensions: Dict[str, Any]) -> str:
    items = []
    for key, value in dimensions.items():
        if key in FIELD_DIM_NAMES:
            continue
        if value is None:
            continue
        items.append(f"{key}={value}")
    items.sort()
    return "|".join(items)


async def compute_field_coherence_metrics(
    sb_client,
    module: str,
    dimensions: Dict[str, Any],
    family_id: str
) -> Dict[str, Any]:
    """
    Compute field coherence (phi) and segment stats for a braid core pattern.
    """
    core_key = build_core_key_from_dimensions(dimensions)
    if not core_key:
        return {"field_coherence": None, "segments_tested": 0, "segments_positive": 0}
    try:
        result = (
            sb_client.table('learning_braids')
            .select('pattern_key,dimensions,stats')
            .eq('module', module)
            .eq('family_id', family_id)
            .execute()
        )
    except Exception as e:
        logger.warning(f"Error fetching braids for field coherence: {e}")
        return {"field_coherence": None, "segments_tested": 0, "segments_positive": 0}
    rows = result.data or []
    segments: Dict[str, float] = {}
    for row in rows:
        dims = row.get('dimensions') or {}
        if build_core_key_from_dimensions(dims) != core_key:
            continue
        segment_key = f"{dims.get('mcap_bucket') or 'global'}|{dims.get('timeframe') or 'all'}"
        if segment_key in segments:
            continue
        stats = row.get('stats') or {}
        n = stats.get('n', 0)
        if n < 1:
            continue
        rr_baseline = await get_rr_baseline(sb_client, module, {
            'mcap_bucket': dims.get('mcap_bucket'),
            'timeframe': dims.get('timeframe')
        })
        edge = compute_edge_score(
            stats.get('avg_rr', 0.0),
            stats.get('variance', 0.0),
            n,
            rr_baseline,
            stats.get('time_efficiency')
        )
        segments[segment_key] = edge
    segments_tested = len(segments)
    if segments_tested == 0:
        return {"field_coherence": None, "segments_tested": 0, "segments_positive": 0}
    segments_positive = sum(1 for edge in segments.values() if edge > 0)
    field_coherence = segments_positive / segments_tested
    return {
        "field_coherence": field_coherence,
        "segments_tested": segments_tested,
        "segments_positive": segments_positive
    }


def bucket_cf_improvement(missed_rr: Optional[float]) -> Optional[str]:
    if missed_rr is None:
        return None
    if missed_rr < 0.5:
        return "none"
    if missed_rr < 1.0:
        return "small"
    if missed_rr < 2.0:
        return "medium"
    return "large"


def _parse_iso_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except Exception:
        return None


async def compute_time_to_payback(
    sb_client,
    token_contract: Optional[str],
    chain: Optional[str],
    timeframe: Optional[str],
    entry_timestamp: Optional[str],
    exit_timestamp: Optional[str],
    entry_price: Optional[float],
    hold_time_days: Optional[float]
) -> Optional[float]:
    """
    Compute time (in days) from entry to first +1R touch using OHLC data.
    Falls back to hold_time_days if insufficient data.
    """
    if not token_contract or not chain or not timeframe or entry_price is None or entry_price <= 0:
        return hold_time_days
    entry_dt = _parse_iso_timestamp(entry_timestamp)
    exit_dt = _parse_iso_timestamp(exit_timestamp)
    if not entry_dt or not exit_dt or exit_dt <= entry_dt:
        return hold_time_days
    try:
        result = (
            sb_client.table("lowcap_price_data_ohlc")
            .select("timestamp,high_usd,low_usd")
            .eq("token_contract", token_contract)
            .eq("chain", chain)
            .eq("timeframe", timeframe)
            .gte("timestamp", entry_dt.isoformat())
            .lte("timestamp", exit_dt.isoformat())
            .order("timestamp", desc=False)
            .execute()
        )
        bars = result.data or []
    except Exception as e:
        logger.warning(f"Error fetching OHLCV for time_to_payback: {e}")
        return hold_time_days
    if not bars:
        return hold_time_days
    min_price = entry_price
    for bar in bars:
        high_price = float(bar.get("high_usd") or 0.0)
        low_price = float(bar.get("low_usd") or 0.0)
        if low_price > 0:
            min_price = min(min_price, low_price)
        risk = (entry_price - min_price) / entry_price if entry_price > 0 else 0.0
        if risk <= 0:
            continue
        if high_price <= 0:
            continue
        return_pct = (high_price - entry_price) / entry_price
        if return_pct >= risk:
            touch_dt = _parse_iso_timestamp(bar.get("timestamp"))
            if touch_dt and touch_dt >= entry_dt:
                delta_days = (touch_dt - entry_dt).total_seconds() / 86400.0
                return max(0.0, delta_days)
            return 0.0
    return hold_time_days


def _update_recurrence_stats(stats: Dict[str, Any], edge_raw: float) -> None:
    now = datetime.now(timezone.utc)
    last_ts = stats.get('last_recurrence_update')
    last_dt = _parse_iso_timestamp(last_ts)
    if last_dt is None:
        recurrence_new = edge_raw
    else:
        delta_days = max((now - last_dt).total_seconds() / 86400.0, 0.0)
        tau_days = 30.0
        alpha = 1.0 if delta_days == 0 else (1.0 - math.exp(-delta_days / tau_days))
        previous = float(stats.get('recurrence_score', 0.0))
        recurrence_new = alpha * edge_raw + (1 - alpha) * previous
    stats['recurrence_score'] = recurrence_new
    stats['last_recurrence_update'] = now.isoformat()


def _compute_emergence_score(
    incremental_edge: float,
    variance: float,
    n: int
) -> float:
    safe_n = max(n, 3)
    return (incremental_edge / (1.0 + variance)) * (1.0 / math.sqrt(safe_n))


async def update_braid_stats(
    sb_client,
    pattern_key: str,
    module: str,
    dimensions: Dict[str, Any],
    rr: float,
    is_win: bool,
    hold_time_days: float,
    family_id: str,
    parent_keys: List[str],
    time_to_payback_days: Optional[float] = None
) -> None:
    """
    Update braid stats using streaming aggregation (Welford's algorithm).
    
    Args:
        sb_client: Supabase client
        pattern_key: Pattern key (e.g., "big_win|state=S1|a_bucket=med")
        module: 'dm' or 'pm'
        dimensions: Dimension values (JSONB)
        rr: R/R value for this trade
        is_win: Whether this trade was a win (R/R > 0)
        hold_time_days: Hold time in days
        family_id: Family ID
        parent_keys: List of parent pattern keys
    """
    try:
        # Get current stats (if exists)
        result = sb_client.table('learning_braids').select('stats').eq('pattern_key', pattern_key).execute()
        
        if result.data and len(result.data) > 0:
            # Update existing braid
            current_stats = result.data[0]['stats']
            n = current_stats.get('n', 0)
            sum_rr = current_stats.get('sum_rr', 0.0)
            sum_rr_squared = current_stats.get('sum_rr_squared', 0.0)
            sum_hold_time = current_stats.get('sum_hold_time_days', 0.0)
            wins = current_stats.get('wins', 0)
            sum_ttp = current_stats.get('sum_time_to_payback_days', 0.0)
            
            # Update streaming stats
            n_new = n + 1
            sum_rr_new = sum_rr + rr
            sum_rr_squared_new = sum_rr_squared + (rr * rr)
            sum_hold_time_new = sum_hold_time + hold_time_days
            wins_new = wins + (1 if is_win else 0)
            if time_to_payback_days is not None:
                sum_ttp_new = sum_ttp + time_to_payback_days
            else:
                sum_ttp_new = sum_ttp
            
            # Compute new averages
            avg_rr_new = sum_rr_new / n_new
            avg_hold_time_new = sum_hold_time_new / n_new
            win_rate_new = wins_new / n_new
            
            # Compute variance (using Welford's algorithm)
            # variance = (sum_rr_squared / n) - avg_rr²
            variance_new = (sum_rr_squared_new / n_new) - (avg_rr_new * avg_rr_new)
            avg_time_to_payback = None
            time_efficiency = None
            if sum_ttp_new > 0 and n_new > 0:
                avg_time_to_payback = sum_ttp_new / n_new
                time_efficiency = 1.0 / (1.0 + max(avg_time_to_payback, 0.0))
            
            new_stats = {
                'n': n_new,
                'sum_rr': sum_rr_new,
                'sum_rr_squared': sum_rr_squared_new,
                'avg_rr': avg_rr_new,
                'variance': max(0.0, variance_new),  # Variance can't be negative (rounding errors)
                'win_rate': win_rate_new,
                'avg_hold_time_days': avg_hold_time_new,
                'wins': wins_new,
                'sum_hold_time_days': sum_hold_time_new,
                'sum_time_to_payback_days': sum_ttp_new
            }
            if avg_time_to_payback is not None:
                new_stats['avg_time_to_payback_days'] = avg_time_to_payback
                new_stats['time_efficiency'] = time_efficiency
            elif current_stats.get('avg_time_to_payback_days') is not None:
                new_stats['avg_time_to_payback_days'] = current_stats.get('avg_time_to_payback_days')
                new_stats['time_efficiency'] = current_stats.get('time_efficiency')
            
            # Update recurrence stats
            rr_baseline = await get_rr_baseline(sb_client, module, {
                'mcap_bucket': dimensions.get('mcap_bucket'),
                'timeframe': dimensions.get('timeframe')
            })
            edge_current = compute_edge_score(
                new_stats['avg_rr'],
                new_stats['variance'],
                new_stats['n'],
                rr_baseline,
                new_stats.get('time_efficiency')
            )
            _update_recurrence_stats(new_stats, edge_current)
            
            # Update row
            sb_client.table('learning_braids').update({
                'stats': new_stats,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }).eq('pattern_key', pattern_key).execute()
        else:
            # Insert new braid
            new_stats = {
                'n': 1,
                'sum_rr': rr,
                'sum_rr_squared': rr * rr,
                'avg_rr': rr,
                'variance': 0.0,
                'win_rate': 1.0 if is_win else 0.0,
                'avg_hold_time_days': hold_time_days,
                'wins': 1 if is_win else 0,
                'sum_hold_time_days': hold_time_days,
                'sum_time_to_payback_days': time_to_payback_days or 0.0
            }
            if time_to_payback_days is not None:
                new_stats['avg_time_to_payback_days'] = time_to_payback_days
                new_stats['time_efficiency'] = 1.0 / (1.0 + max(time_to_payback_days, 0.0))
            rr_baseline = await get_rr_baseline(sb_client, module, {
                'mcap_bucket': dimensions.get('mcap_bucket'),
                'timeframe': dimensions.get('timeframe')
            })
            edge_current = compute_edge_score(
                new_stats['avg_rr'],
                new_stats['variance'],
                new_stats['n'],
                rr_baseline,
                new_stats.get('time_efficiency')
            )
            _update_recurrence_stats(new_stats, edge_current)
            
            sb_client.table('learning_braids').insert({
                'pattern_key': pattern_key,
                'module': module,
                'dimensions': dimensions,
                'stats': new_stats,
                'family_id': family_id,
                'parent_keys': parent_keys,
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'created_at': datetime.now(timezone.utc).isoformat()
            }).execute()
            
    except Exception as e:
        logger.error(f"Error updating braid stats for pattern {pattern_key}: {e}")
        raise


async def process_position_closed_for_braiding(
    sb_client,
    strand: Dict[str, Any]
) -> None:
    """
    Process a position_closed strand to generate and update braids.
    
    This is the main entry point for the braiding system.
    Called when a position closes and emits a position_closed strand.
    
    Args:
        sb_client: Supabase client
        strand: position_closed strand dictionary with completed_trades and entry_context
    """
    try:
        logger.info(f"Processing position_closed strand for braiding")
        
        # Extract data from strand (entry_context and completed_trades are now in content JSONB)
        content = strand.get('content', {})
        entry_context = content.get('entry_context', {})
        completed_trades = content.get('completed_trades', [])
        timeframe = strand.get('timeframe', '1h')
        
        if not completed_trades:
            logger.warning(f"No completed_trades found in position_closed strand")
            return
        
        # Get the trade summary (last item in completed_trades)
        trade_summary = completed_trades[-1] if isinstance(completed_trades, list) else completed_trades
        
        # Extract outcome classification
        outcome_class = trade_summary.get('outcome_class')
        if not outcome_class:
            logger.warning(f"No outcome_class found in trade summary, skipping braiding")
            return
        
        rr = float(trade_summary.get('rr', 0.0))
        hold_time_days = float(trade_summary.get('hold_time_days', 0.0))
        is_win = rr > 0
        time_to_payback_days = trade_summary.get('time_to_payback_days')
        if time_to_payback_days is not None:
            try:
                time_to_payback_days = float(time_to_payback_days)
            except Exception:
                time_to_payback_days = None
        if time_to_payback_days is None:
            time_to_payback_days = await compute_time_to_payback(
                sb_client=sb_client,
                token_contract=strand.get('token') or strand.get('token_contract'),
                chain=strand.get('chain'),
                timeframe=timeframe,
                entry_timestamp=trade_summary.get('entry_timestamp'),
                exit_timestamp=trade_summary.get('exit_timestamp'),
                entry_price=trade_summary.get('entry_price'),
                hold_time_days=hold_time_days
            )
            if time_to_payback_days is None:
                time_to_payback_days = hold_time_days
            trade_summary['time_to_payback_days'] = time_to_payback_days
        
        # Update baselines (for edge score calculation)
        mcap_bucket = entry_context.get('mcap_bucket')
        try:
            # Update segment baseline (mcap + timeframe)
            if mcap_bucket and timeframe:
                await update_baseline_stats(sb_client, 'pm', mcap_bucket, timeframe, rr)
            
            # Update timeframe-only baseline
            if timeframe:
                await update_baseline_stats(sb_client, 'pm', None, timeframe, rr)
            
            # Update global baseline
            await update_baseline_stats(sb_client, 'pm', None, None, rr)
        except Exception as e:
            logger.warning(f"Error updating baselines: {e}")
        
        # Determine module (PM for now, DM later)
        # For PM: use action_context from completed_trades entries
        # For DM: use entry_context
        
        cf_entry_bucket = trade_summary.get('cf_entry_improvement_bucket')
        if cf_entry_bucket is None:
            missed_rr_entry = ((trade_summary.get('could_enter_better') or {}).get('missed_rr'))
            cf_entry_bucket = bucket_cf_improvement(missed_rr_entry) or 'none'
            trade_summary['cf_entry_improvement_bucket'] = cf_entry_bucket
        cf_exit_bucket = trade_summary.get('cf_exit_improvement_bucket')
        if cf_exit_bucket is None:
            missed_rr_exit = ((trade_summary.get('could_exit_better') or {}).get('missed_rr'))
            cf_exit_bucket = bucket_cf_improvement(missed_rr_exit) or 'none'
            trade_summary['cf_exit_improvement_bucket'] = cf_exit_bucket
        
        # PM Braiding: Process each action in completed_trades
        for trade_entry in completed_trades:
            if not isinstance(trade_entry, dict):
                continue
            
            # Skip if this is the trade summary (has outcome_class)
            if 'outcome_class' in trade_entry:
                continue
            
            # Get action_context
            action_context = trade_entry.get('action_context', {})
            if not action_context:
                continue
            
            # Build context for pattern generation
            context = {
                **action_context,
                'outcome_class': outcome_class,  # Use final trade outcome
                'hold_time_class': trade_summary.get('hold_time_class'),
                'timeframe': timeframe,
                'mcap_bucket': entry_context.get('mcap_bucket'),  # From entry context
                'vol_bucket': entry_context.get('vol_bucket'),  # From entry context (for baseline segmentation)
                'cf_entry_improvement_bucket': trade_summary.get('cf_entry_improvement_bucket'),
                'cf_exit_improvement_bucket': trade_summary.get('cf_exit_improvement_bucket'),
            }
            
            # Generate pattern keys
            pattern_keys = generate_pattern_keys(context, module='pm', k=3)
            
            # Compute family_id and parent_keys for each pattern
            family_id = compute_family_id(context, module='pm')
            
            for pattern_key in pattern_keys:
                parent_keys = compute_parent_keys(pattern_key)
                
                # Update braid stats
                await update_braid_stats(
                    sb_client=sb_client,
                    pattern_key=pattern_key,
                    module='pm',
                    dimensions=context,
                    rr=rr,
                    is_win=is_win,
                    hold_time_days=hold_time_days,
                    family_id=family_id,
                    parent_keys=parent_keys,
                    time_to_payback_days=time_to_payback_days
                )
        
        # DM Braiding: Process entry_context (if we have DM data)
        if entry_context and entry_context.get('curator'):
            # Build DM context
            dm_context = {
                **entry_context,
                'outcome_class': outcome_class,
                'hold_time_class': trade_summary.get('hold_time_class'),
                'timeframe': timeframe,
                'cf_entry_improvement_bucket': trade_summary.get('cf_entry_improvement_bucket'),
                'cf_exit_improvement_bucket': trade_summary.get('cf_exit_improvement_bucket'),
            }
            
            # Generate pattern keys
            pattern_keys = generate_pattern_keys(dm_context, module='dm', k=3)
            
            # Compute family_id and parent_keys for each pattern
            family_id = compute_family_id(dm_context, module='dm')
            
            for pattern_key in pattern_keys:
                parent_keys = compute_parent_keys(pattern_key)
                
                # Update braid stats
                await update_braid_stats(
                    sb_client=sb_client,
                    pattern_key=pattern_key,
                    module='dm',
                    dimensions=dm_context,
                    rr=rr,
                    is_win=is_win,
                    hold_time_days=hold_time_days,
                    family_id=family_id,
                    parent_keys=parent_keys,
                    time_to_payback_days=time_to_payback_days
                )
        
        logger.info(f"Successfully processed position_closed strand for braiding")
        
    except Exception as e:
        logger.error(f"Error processing position_closed strand for braiding: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


# ============================================================================
# Edge Score Calculation
# ============================================================================

async def get_rr_baseline(
    sb_client,
    module: str,
    context: Dict[str, Any]
) -> float:
    """
    Get R/R baseline for a segment (mcap_bucket + timeframe).
    
    Falls back hierarchically: segment → mcap-only → timeframe-only → global
    
    Args:
        sb_client: Supabase client
        module: 'dm' or 'pm'
        context: Context with mcap_bucket and timeframe
    
    Returns:
        Baseline R/R for this segment
    """
    mcap_bucket = context.get('mcap_bucket')
    timeframe = context.get('timeframe')
    
    N_MIN_SEG = 10  # Minimum samples for segment baseline
    N_MIN_LOOSE = 5  # Minimum samples for fallback baselines
    
    # 1) Try segment baseline (mcap + timeframe)
    if mcap_bucket and timeframe:
        try:
            result = sb_client.table('learning_baselines').select('stats').eq('module', module).eq('mcap_bucket', mcap_bucket).eq('timeframe', timeframe).execute()
            if result.data and len(result.data) > 0:
                stats = result.data[0]['stats']
                n_seg = stats.get('n', 0)
                if n_seg >= N_MIN_SEG:
                    return float(stats.get('avg_rr', 1.0))
        except Exception:
            pass
    
    # 2) Fall back to looser segments
    candidates = []
    
    if mcap_bucket:
        try:
            result = sb_client.table('learning_baselines').select('stats').eq('module', module).eq('mcap_bucket', mcap_bucket).is_('timeframe', 'null').execute()
            if result.data and len(result.data) > 0:
                stats = result.data[0]['stats']
                n_mcap = stats.get('n', 0)
                if n_mcap >= N_MIN_LOOSE:
                    candidates.append((float(stats.get('avg_rr', 1.0)), n_mcap))
        except Exception:
            pass
    
    if timeframe:
        try:
            result = sb_client.table('learning_baselines').select('stats').eq('module', module).is_('mcap_bucket', 'null').eq('timeframe', timeframe).execute()
            if result.data and len(result.data) > 0:
                stats = result.data[0]['stats']
                n_tf = stats.get('n', 0)
                if n_tf >= N_MIN_LOOSE:
                    candidates.append((float(stats.get('avg_rr', 1.0)), n_tf))
        except Exception:
            pass
    
    if candidates:
        # Weighted average of available fallbacks
        total_n = sum(n for _, n in candidates)
        rr_combined = sum(rr * n for rr, n in candidates) / total_n
        return rr_combined
    
    # 3) Fall back to global
    try:
        result = sb_client.table('learning_baselines').select('stats').eq('module', module).is_('mcap_bucket', 'null').is_('timeframe', 'null').execute()
        if result.data and len(result.data) > 0:
            stats = result.data[0]['stats']
            return float(stats.get('avg_rr', 1.0))
    except Exception:
        pass
    
    # Ultimate fallback: return 1.0 (neutral R/R)
    return 1.0


def compute_edge_score(
    avg_rr: float,
    variance: float,
    n: int,
    rr_baseline: float,
    time_efficiency: Optional[float] = None
) -> float:
    """
    Compute edge score for a braid pattern.
    
    Formula: edge_raw = (rr_p - rr_baseline) * coherence * log(1+n)
    where coherence = 1 / (1 + variance)
    
    Args:
        avg_rr: Average R/R for this pattern
        variance: Variance of R/R for this pattern
        n: Sample size
        rr_baseline: Segment baseline R/R (mcap_bucket + timeframe)
    
    Returns:
        Edge score (positive = good, negative = bad)
    """
    delta_rr = avg_rr - rr_baseline
    coherence = 1.0 / (1.0 + variance)  # Low variance = high coherence
    support = math.log(1 + n)  # Diminishing returns on sample size
    time_weight = 1.0
    if time_efficiency is not None:
        time_eff = max(0.0, min(1.0, time_efficiency))
        time_weight = 0.5 + 0.5 * time_eff
    
    edge_raw = delta_rr * coherence * support * time_weight
    return edge_raw


async def compute_incremental_edge(
    sb_client,
    pattern_key: str,
    edge_raw: float,
    module: str,
    context: Dict[str, Any]
) -> float:
    """
    Compute incremental edge vs parents.
    
    incremental_edge = edge_raw(child) - max(edge_raw(parents))
    
    If incremental_edge <= 0, the extra dimension doesn't add value.
    If incremental_edge > 0, the recombination is valuable.
    
    Args:
        sb_client: Supabase client
        pattern_key: Pattern key
        edge_raw: Edge score for this pattern
        module: 'dm' or 'pm'
        context: Context for baseline lookup
    
    Returns:
        Incremental edge score
    """
    try:
        # Get parent keys
        result = sb_client.table('learning_braids').select('parent_keys, stats').eq('pattern_key', pattern_key).execute()
        if not result.data or not result.data[0].get('parent_keys'):
            return edge_raw  # No parents, so full edge is incremental
        
        parent_keys = result.data[0]['parent_keys']
        
        # Get edge scores for all parents
        parent_edges = []
        for parent_key in parent_keys:
            try:
                parent_result = sb_client.table('learning_braids').select('stats, dimensions').eq('pattern_key', parent_key).execute()
                if parent_result.data and len(parent_result.data) > 0:
                    parent_stats = parent_result.data[0]['stats']
                    parent_context = parent_result.data[0].get('dimensions', {})
                    
                    # Get segment baseline for parent (same segment as child)
                    rr_baseline = await get_rr_baseline(sb_client, module, {
                        'mcap_bucket': parent_context.get('mcap_bucket') or context.get('mcap_bucket'),
                        'timeframe': parent_context.get('timeframe') or context.get('timeframe')
                    })
                    
                    parent_edge = compute_edge_score(
                        parent_stats['avg_rr'],
                        parent_stats['variance'],
                        parent_stats['n'],
                        rr_baseline,
                        parent_stats.get('time_efficiency')
                    )
                    parent_edges.append(parent_edge)
            except Exception:
                continue
        
        if not parent_edges:
            return edge_raw  # No valid parents
        
        max_parent_edge = max(parent_edges)
        incremental_edge = edge_raw - max_parent_edge
        return incremental_edge
        
    except Exception as e:
        logger.error(f"Error computing incremental edge for {pattern_key}: {e}")
        return edge_raw  # Fallback to full edge


# ============================================================================
# Baseline Updates
# ============================================================================

async def update_baseline_stats(
    sb_client,
    module: str,
    mcap_bucket: Optional[str],
    timeframe: Optional[str],
    rr: float
) -> None:
    """
    Update baseline statistics for a segment.
    
    Uses streaming aggregation (Welford's algorithm) to update baseline R/R.
    
    Args:
        sb_client: Supabase client
        module: 'dm' or 'pm'
        mcap_bucket: Market cap bucket (can be None for timeframe-only or global)
        timeframe: Timeframe (can be None for mcap-only or global)
        rr: R/R value from closed trade
    """
    try:
        # Get current baseline stats
        query = sb_client.table('learning_baselines').select('stats')
        
        if mcap_bucket:
            query = query.eq('mcap_bucket', mcap_bucket)
        else:
            query = query.is_('mcap_bucket', 'null')
        
        if timeframe:
            query = query.eq('timeframe', timeframe)
        else:
            query = query.is_('timeframe', 'null')
        
        result = query.eq('module', module).execute()
        
        if result.data and len(result.data) > 0:
            # Update existing baseline
            current_stats = result.data[0]['stats']
            n = current_stats.get('n', 0)
            sum_rr = current_stats.get('sum_rr', 0.0)
            sum_rr_squared = current_stats.get('sum_rr_squared', 0.0)
            
            # Update streaming stats
            n_new = n + 1
            sum_rr_new = sum_rr + rr
            sum_rr_squared_new = sum_rr_squared + (rr * rr)
            
            # Compute new averages
            avg_rr_new = sum_rr_new / n_new
            
            # Compute variance
            variance_new = (sum_rr_squared_new / n_new) - (avg_rr_new * avg_rr_new)
            
            new_stats = {
                'n': n_new,
                'sum_rr': sum_rr_new,
                'sum_rr_squared': sum_rr_squared_new,
                'avg_rr': avg_rr_new,
                'variance': max(0.0, variance_new),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            # Update row
            update_query = sb_client.table('learning_baselines').update({
                'stats': new_stats,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }).eq('module', module)
            
            if mcap_bucket:
                update_query = update_query.eq('mcap_bucket', mcap_bucket)
            else:
                update_query = update_query.is_('mcap_bucket', 'null')
            
            if timeframe:
                update_query = update_query.eq('timeframe', timeframe)
            else:
                update_query = update_query.is_('timeframe', 'null')
            
            update_query.execute()
        else:
            # Insert new baseline
            new_stats = {
                'n': 1,
                'sum_rr': rr,
                'sum_rr_squared': rr * rr,
                'avg_rr': rr,
                'variance': 0.0,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            insert_data = {
                'module': module,
                'mcap_bucket': mcap_bucket,
                'timeframe': timeframe,
                'stats': new_stats,
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            sb_client.table('learning_baselines').insert(insert_data).execute()
            
    except Exception as e:
        logger.error(f"Error updating baseline stats: {e}")
        # Don't fail the whole process if baseline update fails


# ============================================================================
# Lesson Builder
# ============================================================================

async def build_lessons_from_braids(
    sb_client,
    module: str = 'pm',
    n_min: int = 10,
    edge_min: float = 0.5,
    incremental_min: float = 0.1,
    max_lessons_per_family: int = 3
) -> int:
    """
    Build lessons from braids by:
    1. Filtering candidates (n >= n_min, |edge_raw| >= edge_min)
    2. Grouping by family
    3. Choosing representative patterns (prefer simpler when possible)
    4. Creating lesson rows
    
    Args:
        sb_client: Supabase client
        module: 'pm' or 'dm'
        n_min: Minimum sample size
        edge_min: Minimum edge score
        incremental_min: Minimum incremental edge vs parents
        max_lessons_per_family: Maximum lessons per family
    
    Returns:
        Number of lessons created/updated
    """
    try:
        # Get all braids for this module
        result = sb_client.table('learning_braids').select('*').eq('module', module).execute()
        braids = result.data if result.data else []
        
        if not braids:
            logger.info(f"No braids found for module {module}")
            return 0
        
        # Filter candidates
        candidates = []
        for braid in braids:
            stats = braid['stats']
            n = stats.get('n', 0)
            avg_rr = stats.get('avg_rr', 0.0)
            variance = stats.get('variance', 0.0)
            
            # Get segment baseline
            dimensions = braid.get('dimensions', {})
            rr_baseline = await get_rr_baseline(sb_client, module, {
                'mcap_bucket': dimensions.get('mcap_bucket'),
                'timeframe': dimensions.get('timeframe')
            })
            
            # Compute edge score
            edge_raw = compute_edge_score(
                avg_rr,
                variance,
                n,
                rr_baseline,
                braid['stats'].get('time_efficiency')
            )
            coherence_stats = await compute_field_coherence_metrics(
                sb_client,
                module,
                dimensions,
                braid.get('family_id', '')
            )
            field_coherence = coherence_stats.get('field_coherence')
            segments_tested = coherence_stats.get('segments_tested', 0)
            segments_positive = coherence_stats.get('segments_positive', 0)
            if field_coherence is not None:
                field_multiplier = 0.5 + 0.5 * field_coherence
                support_multiplier = 0.5 + 0.5 * math.tanh(segments_tested / 3.0)
                edge_raw *= field_multiplier * support_multiplier
            updated_stats = dict(braid['stats'])
            updated_stats['field_coherence'] = field_coherence
            updated_stats['segments_tested'] = segments_tested
            updated_stats['segments_positive'] = segments_positive
            updated_stats['recurrence_score'] = updated_stats.get('recurrence_score')
            braid['stats'] = updated_stats
            try:
                sb_client.table('learning_braids').update({
                    'stats': updated_stats
                }).eq('pattern_key', braid['pattern_key']).execute()
            except Exception as e:
                logger.warning(f"Error updating field coherence stats for {braid['pattern_key']}: {e}")
            recurrence_score = updated_stats.get('recurrence_score')
            if recurrence_score is not None:
                recurrence_multiplier = 0.5 + 0.5 * math.tanh(recurrence_score)
                edge_raw *= recurrence_multiplier
            
            # Filter
            if n >= n_min and abs(edge_raw) >= edge_min:
                incremental_edge = await compute_incremental_edge(
                    sb_client, braid['pattern_key'], edge_raw, module, dimensions
                )
                emergence_score = _compute_emergence_score(
                    incremental_edge,
                    variance,
                    n
                )
                updated_stats = dict(braid['stats'])
                updated_stats['emergence_score'] = emergence_score
                braid['stats'] = updated_stats
                try:
                    sb_client.table('learning_braids').update({
                        'stats': updated_stats
                    }).eq('pattern_key', braid['pattern_key']).execute()
                except Exception as e:
                    logger.warning(f"Error updating emergence score for {braid['pattern_key']}: {e}")
                candidates.append({
                    'braid': braid,
                    'edge_raw': edge_raw,
                    'incremental_edge': incremental_edge,
                    'emergence_score': emergence_score
                })
        
        if not candidates:
            logger.info(f"No candidates found for module {module} (n_min={n_min}, edge_min={edge_min})")
            return 0
        
        # Group by family
        families = {}
        for candidate in candidates:
            family_id = candidate['braid']['family_id']
            if family_id not in families:
                families[family_id] = []
            families[family_id].append(candidate)
        
        # Build lessons per family
        lessons_created = 0
        for family_id, family_candidates in families.items():
            # Sort by edge_raw (strongest first)
            family_candidates.sort(key=lambda x: abs(x['edge_raw']), reverse=True)
            
            selected_patterns = []
            
            for candidate in family_candidates:
                if len(selected_patterns) >= max_lessons_per_family:
                    break
                
                braid = candidate['braid']
                edge_raw = candidate['edge_raw']
                incremental_edge = candidate['incremental_edge']
                
                # If incremental edge is too small, prefer parent
                if incremental_edge <= incremental_min:
                    # Check if parent is in candidates
                    parent_keys = braid.get('parent_keys', [])
                    # Find best parent that's also a candidate
                    best_parent = None
                    for parent_key in parent_keys:
                        parent_candidate = next(
                            (c for c in candidates if c['braid']['pattern_key'] == parent_key),
                            None
                        )
                        if parent_candidate and parent_candidate not in selected_patterns:
                            if best_parent is None or abs(parent_candidate['edge_raw']) > abs(best_parent['edge_raw']):
                                best_parent = parent_candidate
                    
                    if best_parent:
                        if best_parent not in selected_patterns:
                            selected_patterns.append(best_parent)
                        continue
                
                # This pattern is valuable - add it
                if candidate not in selected_patterns:
                    selected_patterns.append(candidate)
            
            # Create lesson rows
            for selected in selected_patterns:
                braid = selected['braid']
                edge_raw = selected['edge_raw']
                
                # Convert edge to multiplier
                edge_scale = 20.0  # Tuning parameter: edge_raw=20 → +10%
                mult = 1.0 + max(-0.10, min(0.10, edge_raw / edge_scale))
                emergence_score = selected.get('emergence_score')
                
                # Check if should promote to active (lifecycle rules)
                n = braid['stats']['n']
                edge_promote = 0.5
                n_promote = 20
                
                status = 'active' if (n >= n_promote and abs(edge_raw) > edge_promote) else 'candidate'
                
                # Create lesson
                lesson = {
                    'module': module,
                    'trigger': braid['dimensions'],
                    'effect': {
                        ('size_multiplier' if module == 'pm' else 'alloc_multiplier'): mult
                    },
                    'stats': {
                        'edge_raw': edge_raw,
                        'incremental_edge': selected['incremental_edge'],
                        'n': n,
                        'avg_rr': braid['stats']['avg_rr'],
                        'family_id': family_id,
                        'emergence_score': emergence_score
                    },
                    'status': status,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Insert or update lesson
                # Check if lesson with same trigger exists
                existing = sb_client.table('learning_lessons').select('id').eq('module', module).eq('trigger', braid['dimensions']).execute()
                if existing.data and len(existing.data) > 0:
                    # Update
                    sb_client.table('learning_lessons').update({
                        **lesson,
                        'last_validated': datetime.now(timezone.utc).isoformat()
                    }).eq('id', existing.data[0]['id']).execute()
                else:
                    # Insert
                    sb_client.table('learning_lessons').insert(lesson).execute()
                
                lessons_created += 1
        
        logger.info(f"Created/updated {lessons_created} lessons for module {module}")
        return lessons_created
        
    except Exception as e:
        logger.error(f"Error building lessons from braids: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 0


# ============================================================================
# Lesson Matching (Integration Hooks)
# ============================================================================

async def get_matching_lessons(
    sb_client,
    module: str,
    context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Get all active lessons that match the current context.
    
    Uses PostgreSQL JSONB containment (@>) for efficient subset matching.
    Lesson trigger must be subset of context.
    Returns most specific match (highest dimensional match).
    
    Args:
        sb_client: Supabase client
        module: 'dm' or 'pm'
        context: Current context dict with dimension values
    
    Returns:
        List of matching lessons (sorted by specificity, most specific first)
    """
    try:
        # Use PostgreSQL JSONB containment operator (@>) for efficient subset matching
        # This is much faster than Python-side checking, especially with GIN index
        result = (
            sb_client.table('learning_lessons')
            .select('*')
            .eq('module', module)
            .eq('status', 'active')
            .execute()
        )
        lessons = result.data if result.data else []
        
        # Filter using JSONB containment: trigger @> context means trigger is subset of context
        # We need to check if context contains all trigger keys/values
        matching_lessons = []
        for lesson in lessons:
            trigger = lesson.get('trigger', {})
            if not trigger:
                continue
            
            # Check if trigger is subset of context using PostgreSQL JSONB containment
            # Since Supabase doesn't directly support @>, we'll use a workaround:
            # Query with trigger as JSONB and check containment in Python (still faster than full scan)
            # For now, use Python-side check but with early exit optimization
            is_subset = True
            for k, v in trigger.items():
                if k not in context or context[k] != v:
                    is_subset = False
                    break
            
            if is_subset:
                matching_lessons.append(lesson)
        
        # Sort by specificity (most dimensions first)
        matching_lessons.sort(key=lambda l: len(l.get('trigger', {})), reverse=True)
        
        return matching_lessons
        
    except Exception as e:
        logger.error(f"Error getting matching lessons: {e}")
        return []


async def apply_lessons_to_action_size(
    sb_client,
    base_size_frac: float,
    context: Dict[str, Any]
) -> float:
    """
    Apply lessons to action size (PM).
    
    Uses most specific match (highest dimensional match).
    
    Args:
        sb_client: Supabase client
        base_size_frac: Base size fraction from A/E and engine
        context: Current context dict
    
    Returns:
        Final size fraction after lesson adjustments
    """
    try:
        lessons = await get_matching_lessons(sb_client, 'pm', context)
        
        if not lessons:
            return base_size_frac
        
        # Use most specific match (first in sorted list)
        lesson = lessons[0]
        multiplier = lesson['effect'].get('size_multiplier', 1.0)
        
        # Apply multiplier (already clamped in lesson creation)
        final_size = base_size_frac * multiplier
        
        # Clamp to reasonable bounds (safety check)
        final_size = max(0.0, min(1.0, final_size))
        
        return final_size
        
    except Exception as e:
        logger.error(f"Error applying lessons to action size: {e}")
        return base_size_frac


async def apply_lessons_to_allocation(
    sb_client,
    base_allocation_pct: float,
    context: Dict[str, Any]
) -> float:
    """
    Apply lessons to allocation (DM).
    
    Uses most specific match (highest dimensional match).
    
    Args:
        sb_client: Supabase client
        base_allocation_pct: Base allocation percentage
        context: Current context dict
    
    Returns:
        Final allocation percentage after lesson adjustments
    """
    try:
        lessons = await get_matching_lessons(sb_client, 'dm', context)
        
        if not lessons:
            return base_allocation_pct
        
        # Use most specific match
        lesson = lessons[0]
        multiplier = lesson['effect'].get('alloc_multiplier', 1.0)
        
        # Apply multiplier
        final_allocation = base_allocation_pct * multiplier
        
        # Clamp to reasonable bounds
        final_allocation = max(0.0, min(100.0, final_allocation))
        
        return final_allocation
        
    except Exception as e:
        logger.error(f"Error applying lessons to allocation: {e}")
        return base_allocation_pct

