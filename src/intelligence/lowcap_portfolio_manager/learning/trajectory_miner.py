"""
Learning System v2: Trajectory Miner

Reads from position_trajectories table (v2) instead of pattern_episode_events (legacy).
Mines trajectory outcomes to generate strength and tuning lessons.

Key differences from legacy TuningMiner:
- Uses trajectory_type instead of outcome (success/failure)
- Uses continuous ROI instead of binary outcome
- Separate strength vs tuning learning paths
- Implements EV tradeoff for gate loosening decisions
"""

import os
import logging
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("learning_system")


class TrajectoryMiner:
    """
    Learning System v2: Trajectory-based miner.
    
    Reads from position_trajectories table.
    Generates:
    - Strength lessons (dirA/dirE updates) from all trajectories
    - Tuning lessons (gate adjustments) from active failures + shadow winners
    """
    
    def __init__(self):
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
            
        self.sb: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Config - per spec section 2.6
        self.N_MIN = 12  # N_MIN_START: eligibility threshold
        self.N_CONFIDENT = 124  # Full confidence at n=124
        self.LOOKBACK_DAYS = 90
        self.ASYMMETRY_RATIO = 1.69  # Loss aversion ratio
        self.SPECIFICITY_ALPHA = 0.5  # Spec says (spec_mass + 1.0) ^ SPECIFICITY_ALPHA
        
        # Dimension weights per spec section 2.4
        self.STRENGTH_WEIGHTS = {
            "timeframe": 3.0,
            "ticker": 3.0,
            "mcap_bucket": 2.2,
            "bucket_rank_meso_bin": 2.0,
            "age_bucket": 2.0,
            "opp_meso_bin": 1.8,
            "curator": 1.8,
            "vol_bucket": 1.5,
            "riskoff_meso_bin": 1.4,
            "chain": 1.2,
            "mcap_vol_ratio_bucket": 1.2,
            "conf_meso_bin": 1.0,
            "opp_micro_bin": 0.7,
            "conf_micro_bin": 0.7,
            "riskoff_micro_bin": 0.7,
        }
        
        self.TUNING_WEIGHTS = {
            "timeframe": 3.0,
            "ticker": 2.6,
            "riskoff_meso_bin": 2.2,
            "mcap_bucket": 2.0,
            "conf_meso_bin": 1.8,
            "age_bucket": 1.6,
            "bucket_rank_meso_bin": 1.6,
            "chain": 1.2,
            "vol_bucket": 1.2,
            "opp_meso_bin": 1.0,
            "mcap_vol_ratio_bucket": 1.0,
            "riskoff_micro_bin": 1.0,
            "curator": 0.6,
        }
        
    def run(self):
        """Main execution entry point with metrics logging."""
        run_id = None
        started_at = datetime.now(timezone.utc)
        n_trajectories = 0
        n_strength = 0
        n_tuning = 0
        max_dims = 0
        n_combos = 0
        
        try:
            # Record run start
            try:
                run_result = self.sb.table("learning_miner_runs").insert({
                    "miner_name": "TrajectoryMiner",
                    "started_at": started_at.isoformat(),
                    "status": "running",
                    "config_snapshot": {
                        "N_MIN": self.N_MIN,
                        "N_CONFIDENT": self.N_CONFIDENT,
                        "LOOKBACK_DAYS": self.LOOKBACK_DAYS,
                    }
                }).execute()
                if run_result.data:
                    run_id = run_result.data[0].get("id")
            except Exception as e:
                logger.warning(f"Failed to log miner run start: {e}")
            
            logger.info("Starting Trajectory Miner v2...")
            
            # 1. Fetch trajectories
            trajectories = self._fetch_trajectories()
            n_trajectories = len(trajectories)
            logger.info(f"Fetched {n_trajectories} trajectory records.")
            
            if not trajectories:
                self._update_run_metrics(run_id, "completed", started_at, 0, 0, 0, 0, 0, 0)
                return
            
            # 2. Mine strength lessons
            strength_lessons = self._mine_strength_lessons(trajectories)
            n_strength = len(strength_lessons)
            logger.info(f"Generated {n_strength} strength lessons.")
            
            # Track max dimensions and combo count
            for lesson in strength_lessons:
                scope_subset = lesson.get("scope_subset", {})
                max_dims = max(max_dims, len(scope_subset))
                n_combos += 1
            
            # 3. Mine tuning lessons
            tuning_lessons = self._mine_tuning_lessons(trajectories)
            n_tuning = len(tuning_lessons)
            logger.info(f"Generated {n_tuning} tuning lessons.")
            n_combos += n_tuning
            
            # 4. Write to pm_overrides
            all_lessons = strength_lessons + tuning_lessons
            n_overrides = 0
            if all_lessons:
                n_overrides = self._write_overrides(all_lessons)
            
            # Update run metrics
            self._update_run_metrics(
                run_id, "completed", started_at, 
                n_trajectories, n_strength, n_tuning, n_overrides, max_dims, n_combos
            )
            
            logger.info("Trajectory Miner v2 Complete.")
            
        except Exception as e:
            logger.error(f"Trajectory Miner failed: {e}", exc_info=True)
            self._update_run_metrics(run_id, "failed", started_at, 0, 0, 0, 0, 0, 0, str(e))
            raise
    
    def _update_run_metrics(
        self, run_id: Optional[int], status: str, started_at: datetime,
        n_traj: int, n_strength: int, n_tuning: int, n_overrides: int,
        max_dims: int, n_combos: int, error: Optional[str] = None
    ):
        """Update run metrics in learning_miner_runs table."""
        if run_id is None:
            return
        try:
            self.sb.table("learning_miner_runs").update({
                "status": status,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "n_trajectories_fetched": n_traj,
                "n_strength_lessons_created": n_strength,
                "n_tuning_lessons_created": n_tuning,
                "n_overrides_written": n_overrides,
                "max_scope_dimensions": max_dims,
                "n_scope_combinations_mined": n_combos,
                "error_message": error,
            }).eq("id", run_id).execute()
        except Exception as e:
            logger.warning(f"Failed to update miner run metrics: {e}")
    
    def _fetch_trajectories(self) -> List[Dict[str, Any]]:
        """Fetch trajectories from position_trajectories table."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.LOOKBACK_DAYS)).isoformat()
        
        try:
            res = self.sb.table("position_trajectories")\
                .select("*")\
                .gte("closed_at", cutoff)\
                .execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Failed to fetch trajectories: {e}")
            return []
    
    def _mine_strength_lessons(self, trajectories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Mine strength lessons from trajectory outcomes.
        
        Strength learning per spec section 2.5:
        - Uses ALL active trajectories
        - Uses positive-ROI shadow trajectories (blocked winners)
        - Generates dirA/dirE with specificity-weighted confidence
        
        Uses RECURSIVE APRIORI algorithm for multi-dimension scope mining:
        - Builds compound conditions like {timeframe: 1h, mcap_bucket: micro}
        - Prunes branches early when n < N_MIN (Apriori pruning)
        - Weighted specificity = sum of dimension weights
        """
        lessons = []
        
        df = pd.DataFrame(trajectories)
        if df.empty:
            return lessons
        
        # Filter for strength-eligible trajectories
        # Active: all trajectories
        # Shadow: only positive ROI (blocked winners = missed opportunity)
        strength_eligible = df[
            (~df['is_shadow']) |  # All active
            ((df['is_shadow']) & (df['roi'] > 0))  # Shadow winners only
        ].copy()
        
        if len(strength_eligible) < self.N_MIN:
            return lessons
        
        # Flatten scope for grouping
        self._expand_scope_columns(strength_eligible)
        
        # Get available scope columns and sort for consistent ordering
        scope_cols = [c for c in strength_eligible.columns if c.startswith('scope_')]
        sorted_dims = sorted([c.replace('scope_', '') for c in scope_cols])
        
        # Recursive Apriori mining function
        def mine_recursive(df_slice: pd.DataFrame, current_mask: Dict[str, Any], start_dim_idx: int):
            """
            Recursive DFS with Apriori pruning.
            
            Builds multi-dimension scope subsets:
            {} → {timeframe: 1h} → {timeframe: 1h, mcap_bucket: micro} → ...
            """
            # Base case: Prune if too small
            if len(df_slice) < self.N_MIN:
                return
            
            # Process current node: Create lessons for this slice (grouped by pattern_key)
            for pattern_key in df_slice['pattern_key'].unique():
                pattern_group = df_slice[df_slice['pattern_key'] == pattern_key]
                if len(pattern_group) >= self.N_MIN:
                    # Calculate spec_mass = sum of dimension weights
                    spec_mass = sum(self.STRENGTH_WEIGHTS.get(dim, 1.0) for dim in current_mask.keys())
                    
                    lesson = self._compute_strength_lesson(
                        pattern_group, pattern_key, current_mask, spec_mass=spec_mass
                    )
                    if lesson:
                        lessons.append(lesson)
            
            # Recursive step: Try adding one more dimension
            for i in range(start_dim_idx, len(sorted_dims)):
                dim = sorted_dims[i]
                col = f"scope_{dim}"
                
                if col not in df_slice.columns:
                    continue
                
                # Apriori pruning: only branch on values that exist frequently in this slice
                counts = df_slice[col].value_counts()
                valid_values = counts[counts >= self.N_MIN].index.tolist()
                
                for val in valid_values:
                    # Create new mask with additional dimension
                    new_mask = current_mask.copy()
                    new_mask[dim] = val
                    
                    # Filter to new slice
                    new_slice = df_slice[df_slice[col] == val]
                    
                    # Recurse deeper (start from i+1 to avoid duplicates)
                    mine_recursive(new_slice, new_mask, i + 1)
        
        # Start recursion with global slice and empty mask
        mine_recursive(strength_eligible, {}, 0)
        
        return lessons

    def _analyze_dx_ladder_tuning(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Phase 7: Analyze DX ladder pressure from discrete S3.dx trajectories.
        
        Legacy Logic (tuning_miner.py):
        - Filter for successful S3.dx trajectories
        - Calculate distribution of dx_count (1, 2, 3)
        - ladder_pressure = (count_3 - count_1) / total_successful
        - If pressure > threshold: Increase dx_atr_mult (spread out)
        - If pressure < -threshold: Decrease dx_atr_mult (tighten)
        """
        lessons = []
        
        # Filter for S3.dx trajectories
        dx_trajs = df[df['pattern_key'].str.contains('S3.dx', na=False)]
        
        if len(dx_trajs) < self.N_MIN:
            return lessons
            
        # Consider ONLY successful DX buys for ladder pressure
        # (Failures mean the level broke, which is handled by stop/panic logic)
        successful = dx_trajs[dx_trajs['trajectory_type'] == 'success'].copy()
        
        n_success = len(successful)
        if n_success < 5:
            return lessons
            
        # Extract dx_count from scope
        def get_dx_count(scope_val):
            if isinstance(scope_val, dict):
                return scope_val.get('dx_count')
            return None
            
        successful['dx_count'] = successful['scope'].apply(get_dx_count)
        
        # Count frequencies
        # dx_count is 1-based (1, 2, 3...)
        counts = successful['dx_count'].value_counts().to_dict()
        count_1 = counts.get(1, 0)
        count_2 = counts.get(2, 0)
        count_3 = counts.get(3, 0)
        
        # Calculate ladder pressure (-1.0 to 1.0)
        # +1.0 means ALL 3s (tight)
        # -1.0 means ALL 1s (wide)
        ladder_pressure = (count_3 - count_1) / n_success
        
        logger.info(f"DX Ladder Analysis: n={n_success}, 1s={count_1}, 2s={count_2}, 3s={count_3}, pressure={ladder_pressure:.2f}")
        
        # Determine tuning
        tuning_params = None
        recommendation = "maintain"
        
        PRESSURE_THRESHOLD = 0.2
        
        if ladder_pressure > PRESSURE_THRESHOLD:
            # Too many 3s -> Spread out
            tuning_params = {"dx_atr_mult_delta": 0.5}
            recommendation = "spread_out"
        elif ladder_pressure < -PRESSURE_THRESHOLD:
            # Too many 1s -> Tighten
            tuning_params = {"dx_atr_mult_delta": -0.5}
            recommendation = "tighten"
            
        if tuning_params:
            lesson = {
                "pattern_key": "pm.uptrend.S3.dx", # Ladder applies to the whole DX logic
                "action_category": "tuning_dx",
                "scope_subset": {}, # Global for now, could slice by bucket later
                "tuning_params": tuning_params,
                "confidence_score": 0.7, # Base confidence
                "n": n_success,
                "stats": {
                    "ladder_pressure": round(ladder_pressure, 3),
                    "n_success": n_success,
                    "count_1": count_1,
                    "count_3": count_3,
                    "recommendation": recommendation
                }
            }
            lessons.append(lesson)
            
        return lessons
    
    def _compute_strength_lesson(
        self, 
        group: pd.DataFrame, 
        pattern_key: str, 
        scope_subset: Dict[str, Any],
        spec_mass: float = 0.0
    ) -> Optional[Dict[str, Any]]:
        """
        Compute a single strength lesson with:
        - Reliability score (variance-aware) per spec 2.6
        - Trajectory-specific delta values per spec section 4
        - ROI magnitude scaling per spec section 6 rule 9
        """
        n = len(group)
        if n < self.N_MIN:
            return None
        
        # Calculate aggregate stats
        avg_roi = group['roi'].mean()
        roi_variance = group['roi'].var() if n > 1 else 0.0
        win_rate = (group['roi'] > 0).mean()
        
        # Trajectory-type breakdown for delta calculation (spec section 4)
        n_immediate_failure = len(group[group['trajectory_type'] == 'immediate_failure'])
        n_trim_but_loss = len(group[group['trajectory_type'] == 'trim_but_loss'])
        n_trimmed_winner = len(group[group['trajectory_type'] == 'trimmed_winner'])
        n_clean_winner = len(group[group['trajectory_type'] == 'clean_winner'])
        n_shadow_winners = int((group['is_shadow'] & (group['roi'] > 0)).sum())
        
        # Calculate dirA using trajectory-specific deltas per spec:
        # Immediate Failure (Active): Mild A↓ 
        # Trimmed Winner (Active): A↑ +0.02
        # Clean Winner (Active): A↑↑ +0.10
        # Shadow Winner: A↑ +0.03 to +0.12
        active_mask = ~group['is_shadow']
        shadow_mask = group['is_shadow']
        
        weighted_dir_a = 0.0
        total_weight = 0
        
        # Active immediate failures: A↓ -0.02 (mild decrease)
        if n_immediate_failure > 0:
            weighted_dir_a += -0.02 * n_immediate_failure
            total_weight += n_immediate_failure
        
        # Active trim-but-loss: neutral for A (E↑ handled separately)
        if n_trim_but_loss > 0:
            weighted_dir_a += 0.0 * n_trim_but_loss
            total_weight += n_trim_but_loss
        
        # Active trimmed winners: A↑ +0.02
        active_trimmed = len(group[(active_mask) & (group['trajectory_type'] == 'trimmed_winner')])
        if active_trimmed > 0:
            weighted_dir_a += 0.02 * active_trimmed
            total_weight += active_trimmed
        
        # Active clean winners: A↑↑ +0.10, scaled by avg ROI magnitude
        active_clean = len(group[(active_mask) & (group['trajectory_type'] == 'clean_winner')])
        if active_clean > 0:
            clean_roi = group[(active_mask) & (group['trajectory_type'] == 'clean_winner')]['roi'].mean()
            roi_scale = min(1.0, max(0.5, clean_roi / 20.0))  # Scale by ROI magnitude (20% = full)
            weighted_dir_a += 0.10 * roi_scale * active_clean
            total_weight += active_clean
        
        # Shadow winners: A↑ +0.03 to +0.12 (stronger for clean winners)
        shadow_trimmed = len(group[(shadow_mask) & (group['trajectory_type'] == 'trimmed_winner')])
        shadow_clean = len(group[(shadow_mask) & (group['trajectory_type'] == 'clean_winner')])
        if shadow_trimmed > 0:
            weighted_dir_a += 0.03 * shadow_trimmed
            total_weight += shadow_trimmed
        if shadow_clean > 0:
            weighted_dir_a += 0.12 * shadow_clean
            total_weight += shadow_clean
        
        # Compute final dirA as weighted average
        dir_a = weighted_dir_a / max(1, total_weight)
        dir_a = max(-1.0, min(1.0, dir_a))
        
        # Calculate reliability score (variance-aware) per spec 2.6
        # reliability = 1 / (1 + σ²) where σ² is ROI variance
        reliability = 1.0 / (1.0 + roi_variance) if roi_variance >= 0 else 1.0
        
        # g(n) sample ramp per spec table
        if n < 12:
            g_n = 0.0
        elif n <= 33:
            g_n = 0.2 + (0.3 * (n - 12) / 21)  # 0.2 → 0.5
        elif n <= 69:
            g_n = 0.5 + (0.4 * (n - 33) / 36)  # 0.5 → 0.9
        elif n <= 124:
            g_n = 0.9 + (0.1 * (n - 69) / 55)  # 0.9 → 1.0
        else:
            g_n = 1.0
        
        # confidence_eff = reliability × g(n) per spec
        base_confidence = reliability * g_n
        
        # Apply specificity weighting
        specificity = (spec_mass + 1.0) ** self.SPECIFICITY_ALPHA
        confidence = base_confidence * specificity
        confidence = min(1.0, confidence)
        
        # Calculate dirE from trajectory types (E↑ for trim_but_loss)
        dir_e = None
        if n_trim_but_loss > 0:
            # E↑ +0.05 for trim-but-loss per spec
            dir_e = 0.05 * (n_trim_but_loss / n)
        
        return {
            "pattern_key": pattern_key,
            "action_category": "strength",
            "scope_subset": scope_subset,
            "dira": round(dir_a, 3),
            "dire": round(dir_e, 3) if dir_e else None,
            "confidence_score": round(confidence, 3),
            "reliability": round(reliability, 3),
            "g_n": round(g_n, 3),
            "specificity": round(specificity, 3),
            "n": n,
            "stats": {
                "avg_roi": round(avg_roi, 4),
                "roi_variance": round(roi_variance, 4),
                "win_rate": round(win_rate, 3),
                "n_immediate_failure": n_immediate_failure,
                "n_trim_but_loss": n_trim_but_loss,
                "n_trimmed_winner": n_trimmed_winner,
                "n_clean_winner": n_clean_winner,
                "n_shadow_winners": n_shadow_winners,
                "spec_mass": round(spec_mass, 2),
            },
        }
    
    def _mine_tuning_lessons(self, trajectories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Mine tuning lessons from trajectory outcomes.
        
        Tuning learning:
        - Active failures (immediate_failure, trim_but_loss) → tighten gates
        - Shadow winners (blocked but ROI > 0) → evaluate loosening via EV tradeoff
        - Shadow failures → confirmed correct blocks (no action)
        """
        lessons = []
        
        df = pd.DataFrame(trajectories)
        if df.empty:
            return lessons
        
        # Active failures: tight gates were right but maybe not tight enough elsewhere
        active_failures = df[
            (~df['is_shadow']) & 
            (df['trajectory_type'].isin(['immediate_failure', 'trim_but_loss']))
        ]
        
        # Shadow winners: gates blocked what would have been a profitable trade
        shadow_winners = df[
            (df['is_shadow']) & (df['roi'] > 0)
        ]
        
        # Shadow failures: gates correctly blocked losing trades (no action needed)
        shadow_failures = df[
            (df['is_shadow']) & (df['roi'] <= 0)
        ]
        
        logger.info(f"Tuning analysis: {len(active_failures)} active failures, "
                   f"{len(shadow_winners)} shadow winners, {len(shadow_failures)} shadow failures (correct blocks)")
        
        # Process gate-specific tuning for shadow winners (evaluate loosening)
        if len(shadow_winners) >= self.N_MIN:
            gate_lessons = self._analyze_gate_loosening(shadow_winners, df)
            lessons.extend(gate_lessons)
        
        # NEW: Process gate tightening for active failures (spec section 4)
        if len(active_failures) >= self.N_MIN:
            tighten_lessons = self._analyze_gate_tightening(active_failures)
            lessons.extend(tighten_lessons)
        
        # Phase 4: Process trim tuning from trim_but_loss trajectories
        trim_tuning_lessons = self._analyze_trim_tuning(df)
        lessons.extend(trim_tuning_lessons)
        
        # Phase 6: Process dip-buy outcome learning (Position level)
        dip_buy_lessons = self._analyze_dip_buy_outcomes(df)
        lessons.extend(dip_buy_lessons)
        
        # Phase 7: DX Ladder Tuning (S3.dx Trajectory level)
        dx_ladder_lessons = self._analyze_dx_ladder_tuning(df)
        lessons.extend(dx_ladder_lessons)
        
        return lessons
    
    def _analyze_gate_tightening(self, active_failures: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Analyze active failures to determine gate tightening.
        
        Per spec section 4:
        - Active immediate_failure: Tighten entry gates (Δts_min = +0.05, Δhalo_max = -0.1)
        - Active trim_but_loss: Tighten entry OR trim gates
        - Uses near_miss_gates to identify which gates to tighten
        """
        lessons = []
        
        # Group by pattern_key
        for pattern_key in active_failures['pattern_key'].unique():
            group = active_failures[active_failures['pattern_key'] == pattern_key]
            if len(group) < self.N_MIN:
                continue
            
            # Count gate frequencies from near_miss_gates
            gate_counts = {}
            for _, row in group.iterrows():
                near_miss = row.get('near_miss_gates')
                if isinstance(near_miss, list):
                    for gate in near_miss:
                        gate_counts[gate] = gate_counts.get(gate, 0) + 1
            
            if not gate_counts:
                continue
            
            # Calculate tuning_params based on gate frequencies
            # Per spec: Δts_min = +0.05, Δhalo_max = -0.1, etc.
            tuning_params = {}
            total = len(group)
            
            for gate, count in gate_counts.items():
                freq = count / total  # Frequency of this gate being near-miss
                if freq < 0.1:  # Only tune gates that appear in >10% of failures
                    continue
                
                # Apply spec deltas scaled by frequency
                if gate == 'ts':
                    tuning_params['ts_min_delta'] = round(0.05 * freq, 3)
                elif gate == 'halo':
                    tuning_params['halo_max_delta'] = round(-0.1 * freq, 3)
                elif gate == 'slope':
                    tuning_params['slope_min_delta'] = round(0.02 * freq, 3)
                elif gate == 'dx':
                    tuning_params['dx_min_delta'] = round(0.05 * freq, 3)
            
            if not tuning_params:
                continue
            
            # Calculate confidence
            n = len(group)
            g_n = min(1.0, max(0.2, (n - 12) / 112))  # Simple linear for tuning
            
            lesson = {
                "pattern_key": pattern_key,
                "action_category": "tuning_tighten",
                "scope_subset": {},
                "tuning_params": tuning_params,
                "confidence_score": round(g_n, 3),
                "n": n,
                "stats": {
                    "n_immediate": len(group[group['trajectory_type'] == 'immediate_failure']),
                    "n_trim_but_loss": len(group[group['trajectory_type'] == 'trim_but_loss']),
                    "gate_counts": gate_counts,
                    "avg_roi": round(group['roi'].mean(), 4),
                },
            }
            lessons.append(lesson)
            
            logger.info(f"Gate tightening '{pattern_key}': n={n}, params={tuning_params}")
        
        return lessons
    
    def _analyze_dip_buy_outcomes(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Phase 6: Analyze dip-buy outcomes from trajectory data.
        
        Learns from positions that used dip-buys (S3 DX ladder):
        - ROI correlation with n_dip_buys
        - Recovery success rate by dip-buy count
        - Whether dip-buys improved outcome
        """
        lessons = []
        
        # Only active positions for dip-buy learning (shadows don't execute dip-buys)
        active = df[~df['is_shadow']]
        
        if len(active) < self.N_MIN:
            return lessons
        
        # Extract n_dip_buys from scope JSONB
        def get_n_dip_buys(scope):
            if isinstance(scope, dict):
                return scope.get('n_dip_buys', 0) or 0
            return 0
        
        active = active.copy()
        active['n_dip_buys'] = active['scope'].apply(get_n_dip_buys)
        
        # Positions with dip-buys
        with_dip_buys = active[active['n_dip_buys'] > 0]
        without_dip_buys = active[active['n_dip_buys'] == 0]
        
        if len(with_dip_buys) < 5:
            return lessons  # Not enough data
        
        # Calculate dip-buy effectiveness
        avg_roi_with_dips = with_dip_buys['roi'].mean()
        avg_roi_without_dips = without_dip_buys['roi'].mean() if len(without_dip_buys) > 0 else 0.0
        
        win_rate_with_dips = (with_dip_buys['roi'] > 0).mean()
        win_rate_without_dips = (without_dip_buys['roi'] > 0).mean() if len(without_dip_buys) > 0 else 0.5
        
        # Analyze by dip-buy count (1, 2, 3)
        dx_stats = {}
        for dx_count in [1, 2, 3]:
            subset = with_dip_buys[with_dip_buys['n_dip_buys'] == dx_count]
            if len(subset) >= 3:
                dx_stats[dx_count] = {
                    "n": len(subset),
                    "avg_roi": round(subset['roi'].mean(), 4),
                    "win_rate": round((subset['roi'] > 0).mean(), 3),
                }
        
        # Create lesson
        lesson = {
            "pattern_key": "pm.uptrend.S3.dip_buy",
            "action_category": "tuning_dip_buy",
            "scope_subset": {},
            "n": len(with_dip_buys),
            "stats": {
                "n_with_dip_buys": len(with_dip_buys),
                "n_without_dip_buys": len(without_dip_buys),
                "avg_roi_with_dips": round(avg_roi_with_dips, 4),
                "avg_roi_without_dips": round(avg_roi_without_dips, 4),
                "win_rate_with_dips": round(win_rate_with_dips, 3),
                "win_rate_without_dips": round(win_rate_without_dips, 3),
                "roi_delta": round(avg_roi_with_dips - avg_roi_without_dips, 4),
                "by_dx_count": dx_stats,
                "recommendation": "increase_dips" if avg_roi_with_dips > avg_roi_without_dips else "reduce_dips",
            },
        }
        lessons.append(lesson)
        
        logger.info(
            f"Dip-buy learning: n={len(with_dip_buys)}, "
            f"roi_with={avg_roi_with_dips:.1f}% vs without={avg_roi_without_dips:.1f}%, "
            f"delta={avg_roi_with_dips - avg_roi_without_dips:.1f}%"
        )
        
        return lessons
    
    def _analyze_trim_tuning(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Phase 4: Analyze trim tuning from trajectory outcomes.
        
        Trim tuning learns from:
        - trim_but_loss: Trimmed but still lost → trim timing may be off
        - trimmed_winner: Trimmed and won → good trim timing
        - clean_winner: No trim but won → maybe trims were unnecessary
        - immediate_failure: No trim and lost → trim wouldn't have helped
        
        Generates:
        - dirE: Exit assertiveness (-1 = hold longer, +1 = exit faster)
        - Trim threshold adjustments per scope
        """
        lessons = []
        
        # Only active positions for trim learning (shadows don't trim)
        active = df[~df['is_shadow']]
        
        if len(active) < self.N_MIN:
            return lessons
        
        # Group by pattern_key
        grouped = active.groupby('pattern_key')
        
        for pattern_key, group in grouped:
            if len(group) < self.N_MIN:
                continue
            
            # Count trajectory types
            n_trim_but_loss = (group['trajectory_type'] == 'trim_but_loss').sum()
            n_trimmed_winner = (group['trajectory_type'] == 'trimmed_winner').sum()
            n_clean_winner = (group['trajectory_type'] == 'clean_winner').sum()
            n_immediate_failure = (group['trajectory_type'] == 'immediate_failure').sum()
            
            n_trimmed = n_trim_but_loss + n_trimmed_winner
            n_total = len(group)
            
            # Calculate trim effectiveness
            if n_trimmed > 0:
                trim_success_rate = n_trimmed_winner / n_trimmed
            else:
                trim_success_rate = 0.5  # No data, neutral
            
            # Calculate ROI by trim behavior
            trimmed = group[group['did_trim'] == True]
            not_trimmed = group[group['did_trim'] == False]
            
            avg_roi_trimmed = trimmed['roi'].mean() if len(trimmed) > 0 else 0.0
            avg_roi_not_trimmed = not_trimmed['roi'].mean() if len(not_trimmed) > 0 else 0.0
            
            # dirE: Based on trim effectiveness
            # If trimming helps (higher ROI when trimmed), increase dirE (exit faster)
            # If holding helps (higher ROI when not trimmed), decrease dirE (hold longer)
            roi_delta = avg_roi_trimmed - avg_roi_not_trimmed
            
            # Scale to [-1, 1] with reasonable bounds
            dir_e = roi_delta / 20.0  # 20% ROI difference = full scale
            dir_e = max(-1.0, min(1.0, dir_e))
            
            # Only create lesson if significant sample size
            if n_trimmed >= 5:
                confidence = min(1.0, len(group) / self.N_CONFIDENT)
                
                lesson = {
                    "pattern_key": pattern_key,
                    "action_category": "tuning_trim",
                    "scope_subset": {},
                    "dirE": round(dir_e, 3),
                    "confidence_score": round(confidence, 3),
                    "n": n_total,
                    "stats": {
                        "n_trim_but_loss": int(n_trim_but_loss),
                        "n_trimmed_winner": int(n_trimmed_winner),
                        "n_clean_winner": int(n_clean_winner),
                        "n_immediate_failure": int(n_immediate_failure),
                        "trim_success_rate": round(trim_success_rate, 3),
                        "avg_roi_trimmed": round(avg_roi_trimmed, 4),
                        "avg_roi_not_trimmed": round(avg_roi_not_trimmed, 4),
                        "recommendation": "trim_faster" if dir_e > 0.1 else ("hold_longer" if dir_e < -0.1 else "maintain"),
                    },
                }
                lessons.append(lesson)
                
                logger.info(f"Trim tuning '{pattern_key}': dirE={dir_e:.2f}, "
                           f"trim_success={trim_success_rate:.1%}, "
                           f"roi_trimmed={avg_roi_trimmed:.1f}% vs not={avg_roi_not_trimmed:.1f}%")
        
        return lessons
    
    def _analyze_gate_loosening(self, shadow_winners: pd.DataFrame, all_trajectories: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Analyze whether gates should be loosened based on EV tradeoff.
        
        For each blocking gate, simulate what would happen if it were loosened:
        - Find all positions whose gate outcome would flip
        - Calculate EV_delta = Σ(winner ROI) - 1.69 × Σ(|loser ROI|)
        - Only recommend loosening if EV_delta > 0
        """
        lessons = []
        
        # Group by the gates that blocked
        gate_counts: Dict[str, List[float]] = {}  # gate -> list of ROIs
        
        for _, row in shadow_winners.iterrows():
            blocked_by = row.get('blocked_by') or []
            roi = row.get('roi', 0)
            
            for gate in blocked_by:
                if gate not in gate_counts:
                    gate_counts[gate] = []
                gate_counts[gate].append(roi)
        
        for gate, rois in gate_counts.items():
            n = len(rois)
            if n < self.N_MIN:
                continue
            
            # Winners blocked by this gate
            winner_rois = [r for r in rois if r > 0]
            loser_rois = [r for r in rois if r <= 0]
            
            # EV calculation
            ev_winners = sum(winner_rois)
            ev_losers = sum(abs(r) for r in loser_rois) * self.ASYMMETRY_RATIO
            ev_delta = ev_winners - ev_losers
            
            # Create lesson
            lesson = {
                "pattern_key": f"gate.{gate}",
                "action_category": "tuning_gate",
                "scope_subset": {},
                "n": n,
                "stats": {
                    "n_blocked": n,
                    "n_would_win": len(winner_rois),
                    "n_would_lose": len(loser_rois),
                    "total_winner_roi": round(ev_winners, 4),
                    "total_loser_roi_weighted": round(ev_losers, 4),
                    "ev_delta": round(ev_delta, 4),
                    "recommendation": "loosen" if ev_delta > 0 else "maintain",
                },
                "tuning_params": {
                    "ts_min_delta": -5.0 if gate == "ts" else 0,
                    "halo_max_delta": +0.1 if gate == "halo" else 0,
                    "dx_min_delta": -5.0 if gate == "dx" else 0,
                    "slope_min_delta": -0.05 if gate == "slope" else 0,
                } if ev_delta > 0 else None,
            }
            # Clean up params (remove 0s)
            if lesson["tuning_params"]:
                lesson["tuning_params"] = {k: v for k, v in lesson["tuning_params"].items() if v != 0}
                if not lesson["tuning_params"]: 
                    lesson["tuning_params"] = None
            
            lessons.append(lesson)
            
            logger.info(f"Gate '{gate}': n={n}, ev_delta={ev_delta:.2f} → {'LOOSEN' if ev_delta > 0 else 'MAINTAIN'}")
        
        return lessons
    
    def _expand_scope_columns(self, df: pd.DataFrame) -> None:
        """Flatten scope JSONB into separate columns for grouping."""
        scope_keys = set()
        for scope in df['scope']:
            if isinstance(scope, dict):
                scope_keys.update(scope.keys())
        
        for key in sorted(scope_keys):
            df[f"scope_{key}"] = df['scope'].apply(
                lambda x: x.get(key) if isinstance(x, dict) else None
            )
    
    def _write_overrides(self, lessons: List[Dict[str, Any]]) -> int:
        """Write lessons to pm_overrides table. Returns count written."""
        written = 0
        try:
            now = datetime.now(timezone.utc).isoformat()
            
            for lesson in lessons:
                override = {
                    "pattern_key": lesson["pattern_key"],
                    "action_category": lesson["action_category"],
                    "scope_subset": lesson.get("scope_subset", {}),
                    "dira": lesson.get("dira"),
                    "dire": lesson.get("dire"),
                    "confidence_score": lesson.get("confidence_score"),
                    "tuning_params": lesson.get("tuning_params"),
                    "n": lesson.get("n"),
                    "last_updated_at": now,
                }
                
                # Upsert
                self.sb.table("pm_overrides").upsert(
                    override,
                    on_conflict="pattern_key,action_category,scope_subset"
                ).execute()
                written += 1
            
            logger.info(f"Wrote {written} overrides to pm_overrides.")
            return written
            
        except Exception as e:
            logger.error(f"Failed to write overrides: {e}")
            return written


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    miner = TrajectoryMiner()
    miner.run()
