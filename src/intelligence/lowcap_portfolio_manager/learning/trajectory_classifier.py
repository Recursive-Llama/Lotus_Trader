"""
Learning System v2: Trajectory Classification

Records position trajectories when positions close (S0 transition).
Classifies outcomes into: immediate_failure, trim_but_loss, trimmed_winner, clean_winner
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("learning_system")


def classify_trajectory(
    reached_s3: bool,
    did_trim: bool,
    roi: float,
) -> str:
    """
    Classify position outcome into one of four trajectory types.
    
    Per v2 spec:
    - immediate_failure: Never reached S3, ROI <= 0
    - trim_but_loss: Trimmed but still lost (ROI <= 0)  
    - trimmed_winner: Reached S3 with trims, ROI > 0
    - clean_winner: Reached S3 with minimal/no trim, ROI > 0
    
    Args:
        reached_s3: True if position ever reached S3 state
        did_trim: True if any trim occurred
        roi: Final realized ROI (from rpnl_pct)
    
    Returns:
        One of: 'immediate_failure', 'trim_but_loss', 'trimmed_winner', 'clean_winner'
    """
    is_winner = roi > 0
    
    if not reached_s3 and not is_winner:
        # Never reached S3 and lost money
        return "immediate_failure"
    
    if did_trim and not is_winner:
        # Trimmed but still lost
        return "trim_but_loss"
    
    if is_winner:
        if did_trim:
            return "trimmed_winner"
        else:
            return "clean_winner"
    
    # Edge case: reached_s3 but ROI <= 0 with no trim (messy loser)
    # Per spec, classify as trimmed_winner with did_trim=false
    if reached_s3:
        return "trimmed_winner"
    
    # Fallback
    return "immediate_failure"


def record_position_trajectory(
    sb_client,
    position: Dict[str, Any],
    is_shadow: bool,
) -> Optional[Dict[str, Any]]:
    """
    Record a position's trajectory when it closes.
    
    Called when:
    - Active position closes (state transitions to S0)
    - Shadow position closes (state transitions to S0)
    
    Args:
        sb_client: Supabase client
        position: Position dict with all fields
        is_shadow: True if this was a shadow position
    
    Returns:
        Created trajectory record, or None if failed
    """
    try:
        position_id = str(position.get("id", ""))
        trade_id = position.get("current_trade_id")
        
        features = position.get("features") or {}
        uptrend = features.get("uptrend_engine_v4") or {}
        exec_history = features.get("pm_execution_history") or {}
        shadow_data = features.get("shadow_entry_data") or {}
        entry_context = position.get("entry_context") or {}
        
        # Entry event - from shadow_data for shadows, default for active
        entry_event = shadow_data.get("entry_event") or entry_context.get("entry_event") or "S2.entry"
        
        # Pattern key
        pattern_key = f"pm.uptrend.{entry_event.replace('.', '.')}"
        
        # Entry time
        entry_time = position.get("first_entry_timestamp") or position.get("created_at")
        
        # Query entry strand for gate_margins AND scope (primary source)
        # Strands are the authoritative source; features are backup
        gate_margins = None
        blocked_by = None
        near_miss_gates = None
        strand_scope = None  # Will hold scope from strand if available
        applied_overrides = []  # NEW: track which overrides affected this decision
        
        try:
            entry_strand_res = sb_client.table("ad_strands")\
                .select("content")\
                .eq("position_id", position_id)\
                .eq("kind", "pm_action")\
                .in_("tags", ["shadow_entry", "entry"])\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if entry_strand_res.data:
                strand_content = entry_strand_res.data[0].get("content") or {}
                gate_margins = strand_content.get("gate_margins")
                blocked_by = strand_content.get("blocked_by")
                near_miss_gates = strand_content.get("near_miss_gates")
                strand_scope = strand_content.get("scope")  # New: read scope from strand
                applied_overrides = strand_content.get("applied_overrides") or []  # NEW: for effectiveness tracking
                # Use entry_event from strand if available
                if strand_content.get("entry_event"):
                    entry_event = strand_content.get("entry_event")
        except Exception as e:
            logger.warning(f"Failed to query entry strand for {position_id}: {e}")
        
        # Build scope: Primary is strand scope, fallback to build_unified_scope
        if strand_scope:
            scope = strand_scope.copy()
        else:
            # Fallback: build from position using unified scope builder
            from src.intelligence.lowcap_portfolio_manager.pm.pattern_keys_v5 import build_unified_scope
            scope = build_unified_scope(position=position)
        
        # Fallback to features if strand query failed or data missing
        if not gate_margins:
            if is_shadow:
                gate_margins = shadow_data.get("gate_margins")
                blocked_by = shadow_data.get("blocked_by")
            else:
                gate_margins = features.get("gate_margins")
                near_miss_gates = features.get("near_miss_gates")
        
        # Outcome dimensions
        roi = float(position.get("rpnl_pct", 0.0) or 0.0)
        
        # Did trim - check exec_history
        trim_count = exec_history.get("trim_count", 0) or 0
        n_trims = trim_count
        did_trim = n_trims > 0
        
        # Reached S3 - check from episode metadata
        episode_meta = features.get("uptrend_episode_meta") or {}
        s3_episode = episode_meta.get("s3_episode")
        reached_s3 = s3_episode is not None
        
        # Classify trajectory
        trajectory_type = classify_trajectory(reached_s3, did_trim, roi)
        
        # For shadow positions that were blocked, we don't have actual ROI
        # We need to use simulated ROI (what would have happened)
        # For now, use the position's actual movement even though no trade occurred
        if is_shadow:
            # Use total_pnl_pct as simulated ROI for shadow (unrealized movement)
            roi = float(position.get("total_pnl_pct", 0.0) or 0.0)
        
        # Phase 6: Extract dip-buy stats for learning
        pool = exec_history.get("pool") or {}
        n_dip_buys = pool.get("dx_count", 0) or 0
        recovery_started = pool.get("recovery_started", False)
        pool_usd_basis = pool.get("usd_basis", 0.0) or 0.0
        
        # Build record
        trajectory_record = {
            "position_id": position_id,
            "trade_id": str(trade_id) if trade_id else None,
            "entry_event": entry_event,
            "pattern_key": pattern_key,
            "scope": scope,
            "entry_time": entry_time,
            "is_shadow": is_shadow,
            "blocked_by": blocked_by,
            "near_miss_gates": near_miss_gates,
            "gate_margins": gate_margins,
            "trajectory_type": trajectory_type,
            "roi": roi,
            "did_trim": did_trim,
            "n_trims": n_trims,
            "reached_s3": reached_s3,
            "closed_at": datetime.now(timezone.utc).isoformat(),
            "applied_overrides": applied_overrides,  # NEW: for effectiveness tracking
        }
        
        # Add dip-buy stats to scope for mining (stored in scope JSONB for querying)
        if n_dip_buys > 0:
            trajectory_record["scope"]["n_dip_buys"] = n_dip_buys
            trajectory_record["scope"]["recovery_started"] = recovery_started
        
        # Insert
        result = sb_client.table("position_trajectories").insert(trajectory_record).execute()
        
        if result.data:
            logger.info(
                "TRAJECTORY RECORDED: %s | position=%s | roi=%.2f%% | shadow=%s | type=%s",
                pattern_key, position_id[:8], roi, is_shadow, trajectory_type
            )
            
            # Process DX trajectories (sidecar)
            if not is_shadow:
                _process_dx_trajectories(sb_client, position_id)
                
            return result.data[0]
        
        return None
        
        return None
        
    except Exception as e:
        logger.warning(f"Failed to record position trajectory: {e}")
        return None


def _process_dx_trajectories(sb_client, position_id: str):
    """
    Process separate trajectories for each S3 DX buy action.
    
    Logic:
    1. Find all 'S3.dx' strands for this position.
    2. Find all 'trim' strands for this position.
    3. For each DX buy:
       - Success if a trim occurred AFTER the buy.
       - Failure if position closed without subsequent trim.
    4. Record trajectory with binary outcome.
    """
    try:
        # 1. Fetch DX strands
        dx_strands = sb_client.table("ad_strands")\
            .select("content, created_at")\
            .eq("position_id", position_id)\
            .ilike("content->>pattern_key", "%S3.dx%")\
            .execute()
            
        if not dx_strands.data:
            return

        # 2. Fetch Trim strands (to check for success)
        trim_strands = sb_client.table("ad_strands")\
            .select("created_at")\
            .eq("position_id", position_id)\
            .eq("content->>action_category", "trim")\
            .execute()
            
        trim_timestamps = []
        for t in trim_strands.data:
            try:
                # Parse timestamp (handle Z or not)
                ts_str = t.get("created_at", "").replace("Z", "+00:00")
                trim_timestamps.append(datetime.fromisoformat(ts_str))
            except:
                continue
                
        # 3. Process each DX buy
        for strand in dx_strands.data:
            content = strand.get("content") or {}
            created_at_str = strand.get("created_at", "").replace("Z", "+00:00")
            dx_ts = datetime.fromisoformat(created_at_str)
            
            # Determine outcome: Did a trim happen AFTER this buy?
            is_success = False
            for trim_ts in trim_timestamps:
                if trim_ts > dx_ts:
                    is_success = True
                    break
            
            # DX buy outcomes use dedicated trajectory types
            trajectory_type = "dx_success" if is_success else "dx_failure"
            
            # Extract dx_count for mining
            reasons = content.get("reasons") or {}
            # dx_buy_number is 1-based index (1, 2, 3...)
            dx_buy_num = reasons.get("dx_buy_number")
            scope = content.get("scope", {}).copy()
            
            if dx_buy_num is not None:
                # Store as 1-based count in scope for consistency with legacy miner
                scope["dx_count"] = dx_buy_num
            
            # Build record
            record = {
                "position_id": position_id,
                "entry_event": "S3.dx",  # Virtual event
                "pattern_key": "pm.uptrend.S3.dx",
                "scope": scope,
                "entry_time": created_at_str,
                "is_shadow": False, # DX buys are always real actions 
                "trajectory_type": trajectory_type,
                "roi": 0.0, # Not used for binary tuning
                "did_trim": is_success,
                "n_trims": 1 if is_success else 0,
                "reached_s3": True,
                "closed_at": datetime.now(timezone.utc).isoformat(),
            }
            
            # Insert
            sb_client.table("position_trajectories").insert(record).execute()
            logger.info(f"DX TRAJECTORY: {trajectory_type} | pos={position_id[:8]}")

    except Exception as e:
        logger.warning(f"Failed to process DX trajectories for {position_id}: {e}")
