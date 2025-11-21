"""
Pattern Scope Stats Aggregator Job

Aggregates action events into pattern_scope_stats table.
Reads from position_closed strands (which have final R/R) and groups by (pattern_key, action_category, scope_subset).

Runs periodically (cron or event-driven) to update pattern_scope_stats.
"""

import logging
import os
import hashlib
import json
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from itertools import combinations

from supabase import create_client, Client

from src.intelligence.lowcap_portfolio_manager.pm.pattern_keys_v5 import (
    generate_canonical_pattern_key,
    extract_scope_from_context
)

logger = logging.getLogger(__name__)

# Scope dimension order (matches bitmask bits 0-9)
SCOPE_DIMS = [
    "macro_phase",
    "meso_phase", 
    "micro_phase",
    "bucket_leader",
    "bucket_rank_position",
    "market_family",
    "bucket",
    "timeframe",
    "A_mode",
    "E_mode"
]

# N_min thresholds per subset size
N_MIN_BY_SIZE = {
    1: 10,
    2: 10,
    3: 20,
    4: 20,
    5: 30,
    6: 30,
    7: 50,
    8: 50,
    9: 50,
    10: 50
}


def compute_scope_mask(scope: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """
    Compute bitmask and filtered scope_values for a scope dict.
    
    Args:
        scope: Scope dict with all 10 dimensions (some may be None/Unknown)
    
    Returns:
        Tuple of (mask, filtered_scope_values)
        mask: Bitmask (SMALLINT) indicating which dims are present
        filtered_scope_values: JSONB with only non-None, non-Unknown values
    """
    mask = 0
    filtered_values = {}
    
    for i, dim in enumerate(SCOPE_DIMS):
        value = scope.get(dim)
        # Include if value exists and is not None/Unknown/empty
        if value is not None and value != "Unknown" and value != "":
            mask |= (1 << i)
            filtered_values[dim] = value
    
    return mask, filtered_values


def hash_scope_values(scope_values: Dict[str, Any]) -> str:
    """
    Create deterministic hash of scope_values for uniqueness.
    
    Args:
        scope_values: Filtered scope values dict
    
    Returns:
        Hash string
    """
    # Sort keys for deterministic hashing
    sorted_items = sorted(scope_values.items())
    json_str = json.dumps(sorted_items, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]


def generate_subset_masks(scope: Dict[str, Any]) -> List[Tuple[int, Dict[str, Any]]]:
    """
    Generate all non-empty subset masks from a scope dict.
    
    Args:
        scope: Full scope dict
    
    Returns:
        List of (mask, scope_values) tuples for all non-empty subsets
    """
    # First, compute which dims are actually present
    present_dims = {}
    for dim in SCOPE_DIMS:
        value = scope.get(dim)
        if value is not None and value != "Unknown" and value != "":
            present_dims[dim] = value
    
    if not present_dims:
        return []
    
    # Generate all non-empty subsets
    subsets = []
    dim_list = list(present_dims.items())
    
    for size in range(1, len(dim_list) + 1):
        for combo in combinations(dim_list, size):
            subset_dict = dict(combo)
            mask, filtered = compute_scope_mask(subset_dict)
            if mask > 0:
                subsets.append((mask, filtered))
    
    return subsets


def _update_tuning_stats(
    stats: Dict[str, Any],
    episode_type: str,
    outcome: str,
    levers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    tuning = stats.get('tuning') or {}
    type_stats = tuning.get(episode_type, {})
    outcomes = type_stats.get('outcomes') or {}
    outcomes[outcome] = outcomes.get(outcome, 0) + 1
    type_stats['outcomes'] = outcomes

    lever_bucket = type_stats.get('levers') or {}
    for lever_entry in levers:
        lever_name = lever_entry.get('lever')
        if not lever_name:
            continue
        bucket = lever_bucket.get(lever_name) or {
            'sum_delta': 0.0,
            'sum_severity': 0.0,
            'sum_confidence': 0.0,
            'count': 0,
        }
        try:
            bucket['sum_delta'] += float(lever_entry.get('delta') or 0.0)
        except Exception:
            pass
        try:
            bucket['sum_severity'] += float(lever_entry.get('severity') or 0.0)
        except Exception:
            pass
        try:
            bucket['sum_confidence'] += float(lever_entry.get('signal_confidence') or 0.0)
        except Exception:
            pass
        bucket['count'] += 1
        lever_bucket[lever_name] = bucket

    if lever_bucket:
        type_stats['levers'] = lever_bucket

    tuning[episode_type] = type_stats
    stats['tuning'] = tuning
    return stats


async def get_rr_baseline(
    sb_client: Client,
    module: str,
    scope: Dict[str, Any]
) -> float:
    """
    Get R/R baseline for a segment (bucket + timeframe).
    Falls back hierarchically: segment → bucket-only → timeframe-only → global
    
    Args:
        sb_client: Supabase client
        module: 'dm' or 'pm'
        scope: Scope dict with bucket and timeframe
    
    Returns:
        Baseline R/R for this segment
    """
    bucket = scope.get("bucket")
    timeframe = scope.get("timeframe")
    
    N_MIN_SEG = 10
    N_MIN_LOOSE = 5
    
    # Try segment baseline (bucket + timeframe)
    if bucket and timeframe:
        try:
            result = (
                sb_client.table('learning_baselines')
                .select('stats')
                .eq('module', module)
                .eq('mcap_bucket', bucket)  # Note: baselines use mcap_bucket, scope uses bucket
                .eq('timeframe', timeframe)
                .execute()
            )
            if result.data and len(result.data) > 0:
                stats = result.data[0]['stats']
                n_seg = stats.get('n', 0)
                if n_seg >= N_MIN_SEG:
                    return float(stats.get('avg_rr', 1.0))
        except Exception:
            pass
    
    # Fall back to looser segments
    candidates = []
    
    if bucket:
        try:
            result = (
                sb_client.table('learning_baselines')
                .select('stats')
                .eq('module', module)
                .eq('mcap_bucket', bucket)
                .is_('timeframe', 'null')
                .execute()
            )
            if result.data and len(result.data) > 0:
                stats = result.data[0]['stats']
                n_mcap = stats.get('n', 0)
                if n_mcap >= N_MIN_LOOSE:
                    candidates.append((float(stats.get('avg_rr', 1.0)), n_mcap))
        except Exception:
            pass
    
    if timeframe:
        try:
            result = (
                sb_client.table('learning_baselines')
                .select('stats')
                .eq('module', module)
                .is_('mcap_bucket', 'null')
                .eq('timeframe', timeframe)
                .execute()
            )
            if result.data and len(result.data) > 0:
                stats = result.data[0]['stats']
                n_tf = stats.get('n', 0)
                if n_tf >= N_MIN_LOOSE:
                    candidates.append((float(stats.get('avg_rr', 1.0)), n_tf))
        except Exception:
            pass
    
    if candidates:
        total_n = sum(n for _, n in candidates)
        rr_combined = sum(rr * n for rr, n in candidates) / total_n
        return rr_combined
    
    # Fall back to global
    try:
        result = (
            sb_client.table('learning_baselines')
            .select('stats')
            .eq('module', module)
            .is_('mcap_bucket', 'null')
            .is_('timeframe', 'null')
            .execute()
        )
        if result.data and len(result.data) > 0:
            stats = result.data[0]['stats']
            return float(stats.get('avg_rr', 1.0))
    except Exception:
        pass
    
    return 1.0  # Ultimate fallback


async def get_regime_weights(
    sb_client: Client,
    pattern_key: str,
    action_category: str,
    regime_signature: str
) -> Dict[str, float]:
    """
    Get regime-specific weights for edge computation (v5.1).
    Falls back to defaults if not yet learned.
    
    Args:
        sb_client: Supabase client
        pattern_key: Pattern key
        action_category: Action category
        regime_signature: Regime signature string
    
    Returns:
        Weights dict with defaults if not found
    """
    try:
        result = (
            sb_client.table('learning_regime_weights')
            .select('weights')
            .eq('pattern_key', pattern_key)
            .eq('action_category', action_category)
            .eq('regime_signature', regime_signature)
            .execute()
        )
        if result.data and len(result.data) > 0:
            return result.data[0]['weights']
    except Exception:
        pass
    
    # Default weights (neutral)
    return {
        "time_efficiency": 1.0,
        "field_coherence": 1.0,
        "recurrence": 1.0,
        "variance": 1.0
    }


def compute_edge_with_regime_weights(
    avg_rr: float,
    variance: float,
    n: int,
    rr_baseline: float,
    time_efficiency: Optional[float],
    field_coherence: Optional[float],
    recurrence_score: Optional[float],
    regime_weights: Dict[str, float]
) -> float:
    """
    Compute edge_raw using regime-specific weights (v5.1).
    
    Args:
        avg_rr: Average R/R
        variance: Variance
        n: Sample count
        rr_baseline: Baseline R/R
        time_efficiency: Time efficiency (0-1)
        field_coherence: Field coherence (0-1)
        recurrence_score: Recurrence score
        regime_weights: Regime-specific weights
    
    Returns:
        Edge score
    """
    delta_rr = avg_rr - rr_baseline
    coherence = 1.0 / (1.0 + variance)
    support = math.log(1 + n)
    
    # Apply regime-specific weights
    time_weight = regime_weights.get('time_efficiency', 1.0)
    field_weight = regime_weights.get('field_coherence', 1.0)
    recur_weight = regime_weights.get('recurrence', 1.0)
    var_penalty = regime_weights.get('variance', 1.0)
    
    # Compute weighted multipliers
    time_mult = time_efficiency if time_efficiency is not None else 1.0
    field_mult = field_coherence if field_coherence is not None else 1.0
    recur_mult = recurrence_score if recurrence_score is not None else 0.0
    
    # Apply weights
    weighted_time = 0.5 + 0.5 * (time_mult * time_weight)
    weighted_field = 0.5 + 0.5 * (field_mult * field_weight)
    weighted_recur = 0.5 + 0.5 * math.tanh(recur_mult * recur_weight)
    
    # Combine multipliers
    multiplier = (weighted_time + weighted_field + weighted_recur) / 3.0
    variance_mult = 1.0 / (1.0 + variance * var_penalty)
    
    edge_raw = delta_rr * coherence * support * multiplier * variance_mult
    
    return edge_raw


async def process_position_closed_strand(
    sb_client: Client,
    strand: Dict[str, Any]
) -> int:
    """
    Process a position_closed strand to aggregate pattern scope stats.
    
    Args:
        sb_client: Supabase client
        strand: position_closed strand with completed_trades
    
    Returns:
        Number of scope stats rows created/updated
    """
    try:
        content = strand.get('content', {})
        trade_id = content.get('trade_id')
        entry_context = content.get('entry_context', {})
        regime_context = strand.get('regime_context', {})
        trade_summary = content.get('trade_summary')
        completed_trades_legacy = content.get('completed_trades', [])
        
        if trade_summary and isinstance(trade_summary, dict):
            rr = float(trade_summary.get('rr', 0.0))
            hold_time_days = float(trade_summary.get('hold_time_days', 0.0))
            time_to_payback_days = trade_summary.get('time_to_payback_days')
        elif completed_trades_legacy:
            # Legacy format: trade_summary is last entry in completed_trades
            trade_summary = completed_trades_legacy[-1] if isinstance(completed_trades_legacy, list) else completed_trades_legacy
            if not isinstance(trade_summary, dict):
                return 0
            rr = float(trade_summary.get('rr', 0.0))
            hold_time_days = float(trade_summary.get('hold_time_days', 0.0))
            time_to_payback_days = trade_summary.get('time_to_payback_days')
        else:
            return 0
        if time_to_payback_days is not None:
            try:
                time_to_payback_days = float(time_to_payback_days)
            except Exception:
                time_to_payback_days = None
        
        # Compute time efficiency
        time_efficiency = None
        if time_to_payback_days is not None:
            time_efficiency = 1.0 / (1.0 + max(time_to_payback_days, 0.0))
        elif hold_time_days > 0:
            time_efficiency = 1.0 / (1.0 + hold_time_days)
        
        rows_updated = 0
        
        action_entries: List[Dict[str, Any]] = []
        if trade_id:
            try:
                action_rows = (
                    sb_client.table('ad_strands')
                    .select('content')
                    .eq('kind', 'pm_action')
                    .eq('trade_id', trade_id)
                    .eq('position_id', strand.get('position_id'))
                    .order('created_at')
                    .execute()
                ).data or []
                for row in action_rows:
                    entry = row.get('content') or {}
                    action_entries.append(entry)
            except Exception as e:
                logger.warning(f"Error loading pm_action strands for trade {trade_id}: {e}")
        else:
            # Legacy path: use completed_trades array
            for trade_entry in completed_trades_legacy:
                if isinstance(trade_entry, dict) and 'outcome_class' not in trade_entry:
                    action_entries.append(trade_entry)
        
        if not action_entries:
            return 0
        
        for action_entry in action_entries:
            if not isinstance(action_entry, dict):
                continue
            
            pattern_key = action_entry.get('pattern_key')
            action_category = action_entry.get('action_category')
            scope = action_entry.get('scope', {})
            
            # If missing v5 fields, try to reconstruct from action_context (legacy data)
            if not pattern_key or not action_category or not scope:
                action_context = action_entry.get('action_context', {})
                if not action_context:
                    continue  # Skip if no action_context
                
                decision_type = action_entry.get('decision_type') or action_context.get('action_type', '')
                uptrend_signals = action_context.get('uptrend_engine_v4') or {}
                
                try:
                    pattern_key, action_category = generate_canonical_pattern_key(
                        module='pm',
                        action_type=decision_type,
                        action_context=action_context,
                        uptrend_signals=uptrend_signals
                    )
                    
                    entry_context = content.get('entry_context', {})
                    regime_context = strand.get('regime_context', {})
                    
                    position_bucket = entry_context.get('bucket') or action_context.get('bucket')
                    bucket_rank = regime_context.get('bucket_rank', []) if regime_context else []
                    
                    scope = extract_scope_from_context(
                        action_context=action_context,
                        regime_context=regime_context,
                        position_bucket=position_bucket,
                        bucket_rank=bucket_rank
                    )
                except Exception as e:
                    logger.warning(f"Error reconstructing v5 fields from action_context: {e}")
                    continue
            
            if not pattern_key or not action_category or not scope:
                continue
            
            # Generate all subset masks
            subset_masks = generate_subset_masks(scope)
            
            # Build regime signature for weight lookup
            macro_phase = scope.get('macro_phase', 'Unknown')
            meso_phase = scope.get('meso_phase', 'Unknown')
            micro_phase = scope.get('micro_phase', 'Unknown')
            bucket_rank_pos = scope.get('bucket_rank_position')
            regime_signature = f"macro={macro_phase}|meso={meso_phase}|micro={micro_phase}"
            if bucket_rank_pos:
                regime_signature += f"|bucket_rank={bucket_rank_pos}"
            
            # Get regime weights
            regime_weights = await get_regime_weights(
                sb_client, pattern_key, action_category, regime_signature
            )
            
            # Get baseline R/R
            rr_baseline = await get_rr_baseline(sb_client, 'pm', scope)
            
            # Process each subset
            for mask, scope_values in subset_masks:
                # Check N_min for this subset size
                subset_size = bin(mask).count('1')
                n_min = N_MIN_BY_SIZE.get(subset_size, 50)
                
                # Hash scope values
                scope_hash = hash_scope_values(scope_values)
                
                # Check if row exists
                try:
                    result = (
                        sb_client.table('pattern_scope_stats')
                        .select('n,stats')
                        .eq('pattern_key', pattern_key)
                        .eq('action_category', action_category)
                        .eq('scope_mask', mask)
                        .eq('scope_values_hash', scope_hash)
                        .execute()
                    )
                    
                    if result.data and len(result.data) > 0:
                        # Update existing row
                        existing = result.data[0]
                        n_old = existing['n']
                        stats_old = existing['stats']
                        
                        # Update streaming stats (Welford's algorithm)
                        n_new = n_old + 1
                        sum_rr_old = stats_old.get('sum_rr', 0.0)
                        sum_rr_squared_old = stats_old.get('sum_rr_squared', 0.0)
                        sum_hold_time_old = stats_old.get('sum_hold_time_days', 0.0)
                        sum_ttp_old = stats_old.get('sum_time_to_payback_days', 0.0)
                        
                        sum_rr_new = sum_rr_old + rr
                        sum_rr_squared_new = sum_rr_squared_old + (rr * rr)
                        sum_hold_time_new = sum_hold_time_old + hold_time_days
                        if time_to_payback_days is not None:
                            sum_ttp_new = sum_ttp_old + time_to_payback_days
                        else:
                            sum_ttp_new = sum_ttp_old
                        
                        avg_rr_new = sum_rr_new / n_new
                        avg_hold_time_new = sum_hold_time_new / n_new
                        variance_new = (sum_rr_squared_new / n_new) - (avg_rr_new * avg_rr_new)
                        
                        avg_time_to_payback = None
                        time_efficiency_new = None
                        if sum_ttp_new > 0 and n_new > 0:
                            avg_time_to_payback = sum_ttp_new / n_new
                            time_efficiency_new = 1.0 / (1.0 + max(avg_time_to_payback, 0.0))
                        else:
                            time_efficiency_new = time_efficiency
                        
                        # Compute edge_raw
                        field_coherence = stats_old.get('field_coherence')
                        recurrence_score = stats_old.get('recurrence_score')
                        
                        edge_raw = compute_edge_with_regime_weights(
                            avg_rr_new,
                            max(0.0, variance_new),
                            n_new,
                            rr_baseline,
                            time_efficiency_new,
                            field_coherence,
                            recurrence_score,
                            regime_weights
                        )
                        
                        # Update stats
                        new_stats = {
                            'n': n_new,
                            'sum_rr': sum_rr_new,
                            'sum_rr_squared': sum_rr_squared_new,
                            'avg_rr': avg_rr_new,
                            'variance': max(0.0, variance_new),
                            'avg_hold_time_days': avg_hold_time_new,
                            'sum_hold_time_days': sum_hold_time_new,
                            'sum_time_to_payback_days': sum_ttp_new,
                            'edge_raw': edge_raw
                        }
                        
                        if avg_time_to_payback is not None:
                            new_stats['avg_time_to_payback_days'] = avg_time_to_payback
                            new_stats['time_efficiency'] = time_efficiency_new
                        
                        if field_coherence is not None:
                            new_stats['field_coherence'] = field_coherence
                        if recurrence_score is not None:
                            new_stats['recurrence_score'] = recurrence_score
                        
                        # Only update if n >= N_min
                        if n_new >= n_min:
                            sb_client.table('pattern_scope_stats').update({
                                'n': n_new,
                                'stats': new_stats,
                                'updated_at': datetime.now(timezone.utc).isoformat()
                            }).eq('pattern_key', pattern_key).eq('action_category', action_category).eq('scope_mask', mask).eq('scope_values_hash', scope_hash).execute()
                            rows_updated += 1
                            
                            # Snapshot edge history (v5.2)
                            try:
                                import json
                                scope_sig = json.dumps(sorted(scope_values.items()), sort_keys=True)
                                sb_client.table('learning_edge_history').insert({
                                    'pattern_key': pattern_key,
                                    'action_category': action_category,
                                    'scope_signature': scope_sig,
                                    'edge_raw': edge_raw,
                                    'n': n_new,
                                    'ts': datetime.now(timezone.utc).isoformat()
                                }).execute()
                            except Exception as e:
                                logger.warning(f"Error snapshotting edge history: {e}")
                    else:
                        # Insert new row (only if we'll meet N_min after this insert)
                        # Actually, we insert anyway and let N_min filtering happen in queries
                        n_new = 1
                        variance_new = 0.0
                        time_efficiency_new = time_efficiency
                        
                        edge_raw = compute_edge_with_regime_weights(
                            rr,
                            variance_new,
                            n_new,
                            rr_baseline,
                            time_efficiency_new,
                            None,  # field_coherence
                            None,  # recurrence_score
                            regime_weights
                        )
                        
                        new_stats = {
                            'n': n_new,
                            'sum_rr': rr,
                            'sum_rr_squared': rr * rr,
                            'avg_rr': rr,
                            'variance': variance_new,
                            'avg_hold_time_days': hold_time_days,
                            'sum_hold_time_days': hold_time_days,
                            'sum_time_to_payback_days': time_to_payback_days or 0.0,
                            'edge_raw': edge_raw
                        }
                        
                        if time_to_payback_days is not None:
                            new_stats['avg_time_to_payback_days'] = time_to_payback_days
                            new_stats['time_efficiency'] = time_efficiency_new
                        
                        sb_client.table('pattern_scope_stats').insert({
                            'pattern_key': pattern_key,
                            'action_category': action_category,
                            'scope_mask': mask,
                            'scope_values': scope_values,
                            'scope_values_hash': scope_hash,
                            'n': n_new,
                            'stats': new_stats,
                            'created_at': datetime.now(timezone.utc).isoformat(),
                            'updated_at': datetime.now(timezone.utc).isoformat()
                        }).execute()
                        rows_updated += 1
                        
                except Exception as e:
                    logger.warning(f"Error processing scope subset for {pattern_key}/{action_category}: {e}")
                    continue
        
        return rows_updated
        
    except Exception as e:
        logger.error(f"Error processing position_closed strand: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0


async def process_uptrend_episode_summary_strand(
    sb_client: Client,
    strand: Dict[str, Any]
) -> int:
    try:
        content = strand.get('content') or {}
        pattern_key = content.get('pattern_key')
        scope = content.get('scope') or {}
        episode_type = content.get('episode_type')
        outcome = content.get('outcome') or "unknown"
        levers = content.get('levers_considered') or []

        if not pattern_key or not episode_type:
            return 0

        action_category = 'entry' if episode_type == 's1_entry' else 'add'

        subsets = generate_subset_masks(scope)
        if not subsets:
            mask, filtered = compute_scope_mask(scope)
            if mask == 0:
                return 0
            subsets = [(mask, filtered)]

        rows_updated = 0
        now_iso = datetime.now(timezone.utc).isoformat()

        for mask, scope_values in subsets:
            scope_hash = hash_scope_values(scope_values)
            try:
                row_result = (
                    sb_client.table('pattern_scope_stats')
                    .select('stats')
                    .eq('pattern_key', pattern_key)
                    .eq('action_category', action_category)
                    .eq('scope_mask', mask)
                    .eq('scope_values_hash', scope_hash)
                    .limit(1)
                    .execute()
                )
            except Exception as e:
                logger.warning(f"Error fetching stats for tuning episode: {e}")
                continue

            stats_payload = {}
            if row_result.data:
                stats_payload = row_result.data[0].get('stats') or {}
                stats_payload = _update_tuning_stats(stats_payload, episode_type, outcome, levers)
                try:
                    (
                        sb_client.table('pattern_scope_stats')
                        .update({
                            'stats': stats_payload,
                            'updated_at': now_iso,
                        })
                        .eq('pattern_key', pattern_key)
                        .eq('action_category', action_category)
                        .eq('scope_mask', mask)
                        .eq('scope_values_hash', scope_hash)
                        .execute()
                    )
                    rows_updated += 1
                except Exception as e:
                    logger.warning(f"Error updating tuning stats: {e}")
            else:
                stats_payload = _update_tuning_stats({}, episode_type, outcome, levers)
                insert_payload = {
                    'pattern_key': pattern_key,
                    'action_category': action_category,
                    'scope_mask': mask,
                    'scope_values': scope_values,
                    'scope_values_hash': scope_hash,
                    'n': 0,
                    'stats': stats_payload,
                    'created_at': now_iso,
                    'updated_at': now_iso,
                }
                try:
                    sb_client.table('pattern_scope_stats').insert(insert_payload).execute()
                    rows_updated += 1
                except Exception as e:
                    logger.warning(f"Error inserting tuning stats row: {e}")

        return rows_updated

    except Exception as e:
        logger.error(f"Error processing uptrend episode summary strand: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0


async def run_aggregator(
    sb_client: Optional[Client] = None,
    limit: int = 100,
    since: Optional[datetime] = None
) -> Dict[str, int]:
    """
    Run pattern scope aggregator on recent position_closed strands.
    
    Args:
        sb_client: Supabase client (creates if None)
        limit: Max strands to process
        since: Only process strands since this timestamp
    
    Returns:
        Dict with counts: {'processed': N, 'rows_updated': M}
    """
    if sb_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not supabase_key:
            logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
            return {'processed': 0, 'rows_updated': 0}
        sb_client = create_client(supabase_url, supabase_key)
    
    try:
        # Query position_closed strands
        query = (
            sb_client.table('ad_strands')
            .select('*')
            .eq('kind', 'position_closed')
            .eq('module', 'pm')
            .order('created_at', desc=True)
            .limit(limit)
        )
        
        if since:
            query = query.gte('created_at', since.isoformat())
        
        result = query.execute()
        strands = result.data or []
        
        total_updated = 0
        for strand in strands:
            updated = await process_position_closed_strand(sb_client, strand)
            total_updated += updated

        episode_query = (
            sb_client.table('ad_strands')
            .select('*')
            .eq('kind', 'uptrend_episode_summary')
            .eq('module', 'pm')
            .order('created_at', desc=True)
            .limit(limit)
        )
        if since:
            episode_query = episode_query.gte('created_at', since.isoformat())
        episode_result = episode_query.execute()
        episode_strands = episode_result.data or []

        episode_updates = 0
        for strand in episode_strands:
            episode_updates += await process_uptrend_episode_summary_strand(sb_client, strand)
        
        logger.info(
            f"Processed {len(strands)} trade strands (+{len(episode_strands)} tuning episodes), "
            f"updated {total_updated} trade stats rows and {episode_updates} tuning rows"
        )
        return {
            'processed': len(strands),
            'rows_updated': total_updated,
            'episodes_processed': len(episode_strands),
            'episode_rows_updated': episode_updates,
        }
        
    except Exception as e:
        logger.error(f"Error running pattern scope aggregator: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {'processed': 0, 'rows_updated': 0}


if __name__ == "__main__":
    # Standalone execution
    import asyncio
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(run_aggregator())
    print(f"Aggregator result: {result}")

