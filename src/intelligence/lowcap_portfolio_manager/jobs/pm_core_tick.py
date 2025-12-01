from __future__ import annotations

import os
import logging
import uuid
import statistics
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

from supabase import create_client, Client  # type: ignore
from src.intelligence.lowcap_portfolio_manager.pm.actions import plan_actions, plan_actions_v4
from src.intelligence.lowcap_portfolio_manager.pm.levers import compute_levers
from src.intelligence.lowcap_portfolio_manager.pm.executor import PMExecutor
from src.intelligence.lowcap_portfolio_manager.pm.config import load_pm_config, fetch_and_merge_db_config
from src.intelligence.lowcap_portfolio_manager.pm.exposure import ExposureLookup, ExposureConfig
from src.intelligence.lowcap_portfolio_manager.regime.bucket_context import fetch_bucket_phase_snapshot
from src.intelligence.lowcap_portfolio_manager.pm.pattern_keys_v5 import (
    generate_canonical_pattern_key,
    extract_scope_from_context,
    extract_controls_from_action
)
from src.intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v4 import Constants
from src.intelligence.lowcap_portfolio_manager.pm.bucketing_helpers import (
    bucket_a_e, bucket_score, bucket_ema_slopes, bucket_size, bucket_bars_since_entry,
    classify_outcome, classify_hold_time
)


logger = logging.getLogger(__name__)


def bucket_cf_improvement(missed_rr: Optional[float]) -> str:
    if missed_rr is None or missed_rr < 0.5:
        return "none"
    if missed_rr < 1.0:
        return "small"
    if missed_rr < 2.0:
        return "medium"
    return "large"


def _map_meso_to_policy(phase: str) -> tuple[float, float]:
    p = (phase or "").lower()
    if p == "dip":
        return 0.2, 0.8
    if p == "double-dip":
        return 0.4, 0.7
    if p == "oh-shit":
        return 0.9, 0.8
    if p == "recover":
        return 1.0, 0.5
    if p == "good":
        return 0.5, 0.3
    if p == "euphoria":
        return 0.4, 0.5
    return 0.5, 0.5


def _apply_cut_pressure(a: float, e: float, cut_pressure: float) -> tuple[float, float]:
    a2 = max(0.0, min(1.0, a * (1.0 - 0.33 * max(0.0, cut_pressure))))
    e2 = max(0.0, min(1.0, e * (1.0 + 0.33 * max(0.0, cut_pressure))))
    return a2, e2


class PMCoreTick:
    def __init__(self, timeframe: str = "1h", learning_system=None) -> None:
        """
        Initialize PM Core Tick for a specific timeframe.
        
        Args:
            timeframe: Timeframe to process (1m, 15m, 1h, 4h)
            learning_system: Optional learning system instance for processing position_closed strands
        """
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(url, key)
        self.timeframe = timeframe
        self.learning_system = learning_system  # Store learning system for position_closed strand processing
        
        # Initialize PM Executor (trader=None since we use Li.Fi SDK)
        self.executor = PMExecutor(trader=None, sb_client=self.sb)
        self._exposure_lookup: Optional["ExposureLookup"] = None

    def _latest_phase(self) -> Dict[str, Any]:
        # Use portfolio-level meso phase for now
        res = (
            self.sb.table("phase_state")
            .select("phase,score,ts")
            .eq("token", "PORTFOLIO")
            .eq("horizon", "meso")
            .order("ts", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else {"phase": None, "score": 0.0}
    
    def _get_regime_context(self) -> Dict[str, Dict[str, Any]]:
        """
        Get regime phases plus bucket summaries for regime_context.
        
        Returns:
            Dict with keys: macro/meso/micro entries plus bucket_phases, bucket_rank, bucket_population.
        """
        regime_context = {}
        
        for horizon in ["macro", "meso", "micro"]:
            try:
                res = (
                    self.sb.table("phase_state")
                    .select("phase,score,ts")
                    .eq("token", "PORTFOLIO")
                    .eq("horizon", horizon)
                    .order("ts", desc=True)
                    .limit(1)
                    .execute()
                )
                rows = res.data or []
                if rows:
                    regime_context[horizon] = {
                        "phase": rows[0].get("phase") or "",
                        "score": float(rows[0].get("score") or 0.0),
                        "ts": rows[0].get("ts") or datetime.now(timezone.utc).isoformat()
                    }
                else:
                    regime_context[horizon] = {
                        "phase": "",
                        "score": 0.0,
                        "ts": datetime.now(timezone.utc).isoformat()
                    }
            except Exception as e:
                logger.warning(f"Error fetching {horizon} phase: {e}")
                regime_context[horizon] = {
                    "phase": "",
                    "score": 0.0,
                    "ts": datetime.now(timezone.utc).isoformat()
                }
        bucket_snapshot = fetch_bucket_phase_snapshot(self.sb)
        regime_context["bucket_phases"] = bucket_snapshot.get("bucket_phases", {})
        regime_context["bucket_population"] = bucket_snapshot.get("bucket_population", {})
        regime_context["bucket_rank"] = bucket_snapshot.get("bucket_rank", [])

        return regime_context

    def _positions_for_exposure(self) -> List[Dict[str, Any]]:
        """
        Fetch positions for exposure calculation.
        Only includes positions with current_usd_value > 0 (actual holdings).
        """
        try:
            res = (
                self.sb.table("lowcap_positions")
                .select("token_contract,token_chain,timeframe,status,current_usd_value,book_id,state,entry_context,features")
                .gt("current_usd_value", 0.0)  # Only positions with actual holdings
                .limit(2000)
                .execute()
            )
            return res.data or []
        except Exception as exc:
            logger.warning(f"Exposure lookup positions failed: {exc}")
            return []

    def _build_exposure_lookup(
        self,
        regime_context: Dict[str, Dict[str, Any]],
        pm_cfg: Dict[str, Any],
    ) -> Optional[ExposureLookup]:
        positions = self._positions_for_exposure()
        if not positions:
            return None
        try:
            exposure_cfg = ExposureConfig.from_pm_config(pm_cfg)
        except Exception as exc:
            logger.warning(f"Exposure config failed: {exc}")
            return None
        defaults = {
            "macro_phase": (regime_context.get("macro") or {}).get("phase"),
            "meso_phase": (regime_context.get("meso") or {}).get("phase"),
            "micro_phase": (regime_context.get("micro") or {}).get("phase"),
        }
        try:
            return ExposureLookup.build(positions, exposure_cfg, defaults)
        except Exception as exc:
            logger.warning(f"Exposure lookup build failed: {exc}")
            return None

    def _latest_cut_pressure(self) -> float:
        res = self.sb.table("portfolio_bands").select("cut_pressure").order("ts", desc=True).limit(1).execute()
        rows = res.data or []
        try:
            return float((rows[0] or {}).get("cut_pressure") or 0.0)
        except Exception:
            return 0.0

    def _active_positions(self) -> List[Dict[str, Any]]:
        """
        Get positions for this timeframe (watchlist + active - skip dormant).
        
        Returns:
            List of positions matching the timeframe and status
        """
        res = (
            self.sb.table("lowcap_positions")
            .select("id,token_contract,token_chain,token_ticker,timeframe,status,features,avg_entry_price,avg_exit_price,total_allocation_usd,total_extracted_usd,total_quantity,total_tokens_bought,total_tokens_sold,total_allocation_pct,entry_context,current_trade_id")
            .eq("timeframe", self.timeframe)
            .in_("status", ["watchlist", "active"])  # Skip dormant positions
            .limit(2000)
            .execute()
        )
        return res.data or []

    def _fetch_token_buckets(self, keys: List[tuple[str, str | None]]) -> Dict[tuple[str, str | None], str]:
        contracts = sorted({k[0] for k in keys if k and k[0]})
        if not contracts:
            return {}
        try:
            res = (
                self.sb.table("token_cap_bucket")
                .select("token_contract,chain,bucket")
                .in_("token_contract", contracts)
                .execute()
            )
        except Exception as exc:
            logger.warning(f"Error fetching token cap buckets: {exc}")
            return {}
        rows = res.data or []
        out: Dict[tuple[str, str | None], str] = {}
        for row in rows:
            token = row.get("token_contract")
            chain = row.get("chain")
            bucket = row.get("bucket")
            if token and bucket:
                out[(token, chain)] = bucket
        return out

    @staticmethod
    def _generate_episode_id(prefix: str = "epi") -> str:
        return f"{prefix}_{uuid.uuid4().hex}"

    @staticmethod
    def _iso_to_datetime(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    def _ensure_episode_meta(self, features: Dict[str, Any]) -> Dict[str, Any]:
        meta = features.get("uptrend_episode_meta")
        if not isinstance(meta, dict):
            meta = {}
        meta.setdefault("s1_episode", None)
        meta.setdefault("s3_episode", None)
        meta.setdefault("last_consumed_s1_buy_ts", None)
        meta.setdefault("last_consumed_s3_buy_ts", None)
        meta.setdefault("last_consumed_trim_ts", None)
        features["uptrend_episode_meta"] = meta
        return meta

    def _log_episode_event(
        self,
        window: Dict[str, Any],
        scope: Dict[str, Any],
        pattern_key: str,
        decision: str,
        factors: Dict[str, Any],
        episode_id: str,
        trade_id: Optional[str] = None,
    ) -> Optional[int]:
        """Log an episode event to pattern_episode_events table."""
        try:
            payload = {
                "scope": scope,
                "pattern_key": pattern_key,
                "episode_id": episode_id,
                "decision": decision,
                "factors": factors,
                "outcome": None, # Pending
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trade_id": trade_id
            }
            res = self.sb.table("pattern_episode_events").insert(payload).execute()
            if res.data:
                return res.data[0].get("id")
        except Exception as e:
            logger.warning(f"Failed to log episode event: {e}")
        return None

    def _update_episode_outcome(self, db_ids: List[int], outcome: str) -> None:
        """Update outcome for a list of episode event IDs."""
        if not db_ids:
            return
        try:
            self.sb.table("pattern_episode_events").update({"outcome": outcome}).in_("id", db_ids).execute()
        except Exception as e:
            logger.warning(f"Failed to update episode outcomes: {e}")

    def _update_episode_outcomes_from_meta(self, episode: Dict[str, Any], outcome: str) -> None:
        """Helper to collect db_ids from episode windows and update outcomes."""
        windows = episode.get("windows") or []
        ids = []
        for w in windows:
            if w.get("db_id"):
                ids.append(w.get("db_id"))
        if ids:
            self._update_episode_outcome(ids, outcome)

    def _sync_s3_window_outcomes_to_db(self, episode: Dict[str, Any]) -> None:
        """Helper to sync S3 window-specific outcomes to DB."""
        windows = episode.get("windows") or []
        # Group by outcome to batch updates
        by_outcome: Dict[str, List[int]] = {}
        for w in windows:
            db_id = w.get("db_id")
            outcome = w.get("outcome")
            if db_id and outcome:
                by_outcome.setdefault(outcome, []).append(db_id)
        
        for outcome, ids in by_outcome.items():
            self._update_episode_outcome(ids, outcome)

    def _capture_s1_window_sample(self, uptrend: Dict[str, Any], now: datetime, levers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        diagnostics = (uptrend.get("diagnostics") or {}).get("buy_check") or {}
        ema_vals = uptrend.get("ema") or {}
        price = float(uptrend.get("price", 0.0))
        ema60 = float(ema_vals.get("ema60", 0.0))
        atr = float(diagnostics.get("atr", 0.0))
        halo = float(diagnostics.get("halo", 0.0))
        halo_dist = None
        if atr > 0 and ema60 > 0:
            halo_dist = abs(price - ema60) / atr

        sample = {
            "ts": now.isoformat(),
            "ts_score": float(diagnostics.get("ts_score", 0.0)),
            "ts_with_boost": float(diagnostics.get("ts_with_boost", 0.0)),
            "sr_boost": float(diagnostics.get("sr_boost", 0.0)),
            "entry_zone_ok": bool(diagnostics.get("entry_zone_ok")),
            "slope_ok": bool(diagnostics.get("slope_ok")),
            "ts_ok": bool(diagnostics.get("ts_ok")),
            "ema60_slope": float(diagnostics.get("ema60_slope", 0.0)),
            "ema144_slope": float(diagnostics.get("ema144_slope", 0.0)),
            "halo": halo,
            "halo_distance": halo_dist,
            "price": price,
            "ema60": ema60,
        }
        
        if levers:
            sample["a_value"] = float(levers.get("A_value", 0.0))
            sample["position_size_frac"] = float(levers.get("position_size_frac", 0.0))
            
        return sample

    def _capture_s3_window_sample(self, uptrend: Dict[str, Any], now: datetime, levers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        scores = uptrend.get("scores") or {}
        ema_vals = uptrend.get("ema") or {}
        diagnostics = (uptrend.get("diagnostics") or {}).get("s3_buy_check") or {}
        slopes = diagnostics or {}
        price = float(uptrend.get("price", 0.0))
        ema144 = float(ema_vals.get("ema144", 0.0))
        ema333 = float(ema_vals.get("ema333", 0.0))
        price_pos = None
        band_width = abs(ema144 - ema333)
        if band_width > 0:
            if ema144 >= ema333:
                ratio = (price - ema333) / band_width
            else:
                ratio = (price - ema144) / band_width
            ratio = max(0.0, min(1.0, ratio))
            price_pos = 1.0 - ratio if ema144 >= ema333 else ratio

        sample = {
            "ts": now.isoformat(),
            "ts_score": float(scores.get("ts", 0.0)),
            "dx_score": float(scores.get("dx", 0.0)),
            "edx_score": float(scores.get("edx", 0.0)),
            "price": price,
            "price_pos": price_pos,
            "ema144": ema144,
            "ema333": ema333,
            "ema250_slope": float(slopes.get("ema250_slope", 0.0)),
            "ema333_slope": float(slopes.get("ema333_slope", 0.0)),
        }
        
        if levers:
            sample["a_value"] = float(levers.get("A_value", 0.0))
            sample["position_size_frac"] = float(levers.get("position_size_frac", 0.0))

        return sample

    @staticmethod
    def _summarize_window_samples(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not samples:
            return {}

        def collect(key: str) -> List[float]:
            vals = []
            for s in samples:
                val = s.get(key)
                if isinstance(val, (int, float)):
                    vals.append(float(val))
            return vals

        summary: Dict[str, Any] = {}
        summary["sample_count"] = len(samples)
        metrics = [
            "ts_score",
            "ts_with_boost",
            "sr_boost",
            "dx_score",
            "edx_score",
            "price_pos",
            "ema60_slope",
            "ema144_slope",
            "ema250_slope",
            "ema333_slope",
            "halo_distance",
        ]
        for metric in metrics:
            values = collect(metric)
            if values:
                summary[metric] = {
                    "min": min(values),
                    "max": max(values),
                    "median": statistics.median(values),
                }
        summary["sample_count"] = len(samples)
        return summary

    @staticmethod
    def _make_lever_entry(lever: str, delta: float, confidence: float, severity_cap: float) -> Dict[str, Any]:
        severity_cap = max(severity_cap, 1e-6)
        severity = min(1.0, abs(delta) / severity_cap)
        direction = "tighten" if delta > 0 else "loosen"
        return {
            "lever": lever,
            "delta": delta,
            "severity": severity,
            "signal_confidence": max(0.0, min(1.0, confidence)),
            "direction": direction,
        }

    def _compute_lever_considerations(self, episode: Dict[str, Any], episode_type: str) -> List[Dict[str, Any]]:
        windows = episode.get("windows") or []
        total_samples = 0
        for w in windows:
            summary = w.get("summary") or {}
            sample_count = summary.get("sample_count") or len(w.get("samples") or [])
            total_samples += sample_count
        if total_samples <= 0:
            total_samples = len(windows) or 1

        considerations: List[Dict[str, Any]] = []

        for win in windows:
            summary = win.get("summary") or {}
            sample_count = summary.get("sample_count") or len(win.get("samples") or [])
            if sample_count <= 0:
                continue
            confidence = sample_count / max(total_samples, 1)

            if episode_type == "s1_entry":
                ts_summary = summary.get("ts_with_boost") or {}
                median_ts = ts_summary.get("median")
                if median_ts is not None:
                    delta = Constants.TS_THRESHOLD - median_ts
                    considerations.append(self._make_lever_entry("ts_min", delta, confidence, 0.10))

                sr_summary = summary.get("sr_boost") or {}
                median_sr = sr_summary.get("median")
                if median_sr is not None:
                    target_sr = Constants.SR_BOOST_MAX * 0.5
                    delta = target_sr - median_sr
                    considerations.append(self._make_lever_entry("sr_boost", delta, confidence, Constants.SR_BOOST_MAX))

                slope60 = (summary.get("ema60_slope") or {}).get("median")
                if slope60 is not None:
                    delta = 0.0 - slope60
                    considerations.append(self._make_lever_entry("ema60_slope_min", delta, confidence, 0.02))

                slope144 = (summary.get("ema144_slope") or {}).get("median")
                if slope144 is not None:
                    delta = 0.0 - slope144
                    considerations.append(self._make_lever_entry("ema144_slope_min", delta, confidence, 0.02))

                halo_dist = (summary.get("halo_distance") or {}).get("median")
                if halo_dist is not None:
                    delta = halo_dist - Constants.ENTRY_HALO_ATR_MULTIPLIER
                    considerations.append(self._make_lever_entry("halo_multiplier", delta, confidence, 0.20))

            elif episode_type == "s3_retest":
                dx_summary = summary.get("dx_score") or {}
                median_dx = dx_summary.get("median")
                if median_dx is not None:
                    delta = Constants.DX_BUY_THRESHOLD - median_dx
                    considerations.append(self._make_lever_entry("dx_min", delta, confidence, 0.10))

                edx_summary = summary.get("edx_score") or {}
                median_edx = edx_summary.get("median")
                if median_edx is not None:
                    delta = median_edx - 0.5
                    considerations.append(self._make_lever_entry("edx_supp_mult", delta, confidence, 0.20))

                slope250 = (summary.get("ema250_slope") or {}).get("median")
                if slope250 is not None:
                    delta = 0.0 - slope250
                    considerations.append(self._make_lever_entry("ema250_slope_min", delta, confidence, 0.02))

                slope333 = (summary.get("ema333_slope") or {}).get("median")
                if slope333 is not None:
                    delta = 0.0 - slope333
                    considerations.append(self._make_lever_entry("ema333_slope_min", delta, confidence, 0.02))

                price_pos = (summary.get("price_pos") or {}).get("median")
                if price_pos is not None:
                    delta = 0.5 - price_pos
                    considerations.append(self._make_lever_entry("price_band_bias", delta, confidence, 0.50))

        return considerations

    def _append_window_sample(self, window: Dict[str, Any], sample: Dict[str, Any]) -> None:
        samples = window.setdefault("samples", [])
        samples.append(sample)
        max_samples = 12
        if len(samples) > max_samples:
            trimmed = [samples[0]]
            trimmed.extend(samples[-(max_samples - 1):])
            window["samples"] = trimmed

    def _finalize_active_window(
        self, 
        episode: Dict[str, Any], 
        now: datetime,
        position: Optional[Dict[str, Any]] = None,
        regime_context: Optional[Dict[str, Any]] = None,
        token_bucket: Optional[str] = None,
        uptrend_signals: Optional[Dict[str, Any]] = None,
        levers: Optional[Dict[str, Any]] = None,
    ) -> bool:
        active = episode.get("active_window")
        if not active:
            return False
        if "ended_at" not in active:
            active["ended_at"] = now.isoformat()
        samples = active.get("samples", [])
        active["summary"] = self._summarize_window_samples(samples)
        
        # Log to pattern_episode_events if context is provided
        if position and uptrend_signals:
            try:
                decision = "acted" if active.get("entered") else "skipped"
                
                # Determine pattern key and scope
                window_type = active.get("window_type") # s1_buy_signal or None (s3)
                is_s1 = window_type == "s1_buy_signal" or (episode.get("episode_id") or "").startswith("s1_")
                state = "S1" if is_s1 else "S3"
                
                # For skipped events, we infer the action type
                action_type = "entry" if is_s1 else "add"
                
                # Build scope
                pattern_key, _, scope = self._build_pattern_scope(
                    position=position,
                    uptrend_signals=uptrend_signals,
                    action_type=action_type,
                    regime_context=regime_context or {},
                    token_bucket=token_bucket,
                    state=state
                )
                
                if pattern_key and scope:
                    # Merge levers into summary for factors
                    factors = active.get("summary") or {}
                    if levers:
                        factors["a_value"] = float(levers.get("A_value", 0.0))
                        factors["position_size_frac"] = float(levers.get("position_size_frac", 0.0))
                        
                    # Log event
                    db_id = self._log_episode_event(
                        window=active,
                        scope=scope,
                        pattern_key=pattern_key,
                        decision=decision,
                        factors=factors,
                        episode_id=active.get("window_id") or episode.get("episode_id"),
                        trade_id=position.get("current_trade_id") if decision == "acted" else None
                    )
                    if db_id:
                        active["db_id"] = db_id
                        
            except Exception as e:
                logger.warning(f"Error finalizing active window logging: {e}")

        episode.setdefault("windows", []).append(active)
        episode["active_window"] = None
        return True

    def _compute_s3_window_outcomes(self, episode: Dict[str, Any]) -> None:
        windows = episode.get("windows") or []
        trimmed = episode.get("trimmed")
        
        for win in windows:
            if win.get("outcome"):
                continue
            
            # Success if we trimmed (actual) or if a trim signal fired (virtual/missed)
            if (win.get("entered") and win.get("trim_timestamp")) or trimmed:
                    win["outcome"] = "success"
            
            # Note: Failures are handled on S3 -> S0 transition or explicitly if needed.
            # We leave outcome as None if pending.

    def _compute_s3_episode_outcome(self, episode: Dict[str, Any]) -> str:
        windows = episode.get("windows") or []
        entered = [w for w in windows if w.get("entered")]
        if entered:
            if any(w.get("outcome") == "success" for w in entered):
                return "success"
            return "failure"
        if any((w.get("samples") or w.get("summary")) for w in windows):
            return "missed"
        return "correct_skip"

    def _build_pattern_scope(
        self,
        position: Dict[str, Any],
        uptrend_signals: Dict[str, Any],
        action_type: str,
        regime_context: Dict[str, Any],
        token_bucket: Optional[str],
        state: str,
        levers: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
        a_val = 0.5
        e_val = 0.5
        if levers:
            a_val = float(levers.get("A_value", 0.5))
            e_val = float(levers.get("E_value", 0.5))

        action_context = {
            "state": state,
            "timeframe": position.get("timeframe", self.timeframe),
            "market_family": "lowcaps",
            "buy_signal": state == "S1",
            "buy_flag": state == "S3",
            "a_final": a_val,
            "e_final": e_val,
        }
        try:
            pattern_key, action_category = generate_canonical_pattern_key(
                module="pm",
                action_type=action_type,
                action_context=action_context,
                uptrend_signals=uptrend_signals,
            )
        except Exception:
            pattern_key = None
            action_category = None

        bucket_rank = (regime_context or {}).get("bucket_rank", [])
        try:
            scope = extract_scope_from_context(
                action_context=action_context,
                regime_context=regime_context or {},
                position_bucket=token_bucket,
                bucket_rank=bucket_rank,
            )
        except Exception:
            scope = {}
        return pattern_key, action_category, scope

    def _build_stage_transition_strand(
        self,
        position: Dict[str, Any],
        from_state: Optional[str],
        to_state: Optional[str],
        uptrend_signals: Dict[str, Any],
        regime_context: Dict[str, Any],
        token_bucket: Optional[str],
        now: datetime,
        episode_id: Optional[str] = None,
        levers: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        pattern_key, action_category, scope = self._build_pattern_scope(
            position=position,
            uptrend_signals=uptrend_signals,
            action_type="entry" if to_state == "S1" else "add",
            regime_context=regime_context,
            token_bucket=token_bucket,
            state=to_state or "Unknown",
            levers=levers,
        )
        position_id = position.get("id")
        timeframe = position.get("timeframe", self.timeframe)
        symbol = position.get("token_ticker") or position.get("token_contract")

        content = {
            "position_id": position_id,
            "episode_id": episode_id,
            "from_state": from_state,
            "to_state": to_state,
            "pattern_key": pattern_key,
            "action_category": action_category,
            "scope": scope,
            "ts": now.isoformat(),
        }

        strand = {
            "id": f"uptrend_stage_{position_id}_{int(now.timestamp() * 1000)}",
            "module": "pm",
            "kind": "uptrend_stage_transition",
            "symbol": symbol,
            "timeframe": timeframe,
            "position_id": position_id,
            "trade_id": position.get("current_trade_id"),
            "content": content,
            "regime_context": regime_context or {},
            "tags": ["uptrend", "stage_transition"],
            "target_agent": "learning_system",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        return strand

    def _update_episode_entry_flags(self, meta: Dict[str, Any], features: Dict[str, Any]) -> bool:
        changed = False
        execution_history = features.get("pm_execution_history") or {}
        last_s1_buy = execution_history.get("last_s1_buy") or {}
        last_ts = last_s1_buy.get("timestamp")
        if last_ts:
            episode = meta.get("s1_episode")
            consumed = meta.get("last_consumed_s1_buy_ts")
            if episode and consumed != last_ts:
                started_at = episode.get("started_at")
                started_dt = self._iso_to_datetime(started_at)
                ts_dt = self._iso_to_datetime(last_ts)
                if started_dt and ts_dt and ts_dt >= started_dt:
                    episode["entered"] = True
                    active_window = episode.get("active_window")
                    if active_window:
                        active_window["entered"] = True
                        active_window["entry_timestamp"] = last_ts
                    meta["last_consumed_s1_buy_ts"] = last_ts
                    changed = True
        s3_episode = meta.get("s3_episode")
        last_s3_buy = execution_history.get("last_s3_buy") or {}
        last_s3_ts = last_s3_buy.get("timestamp")
        if s3_episode and last_s3_ts:
            consumed = meta.get("last_consumed_s3_buy_ts")
            active = s3_episode.get("active_window")
            if active and consumed != last_s3_ts:
                start_dt = self._iso_to_datetime(active.get("started_at"))
                buy_dt = self._iso_to_datetime(last_s3_ts)
                if start_dt and buy_dt and buy_dt >= start_dt:
                    active["entered"] = True
                    active["entry_timestamp"] = last_s3_ts
                    meta["last_consumed_s3_buy_ts"] = last_s3_ts
                    changed = True
        last_trim = execution_history.get("last_trim") or {}
        last_trim_ts = last_trim.get("timestamp")
        if s3_episode and last_trim_ts and meta.get("last_consumed_trim_ts") != last_trim_ts:
            trim_dt = self._iso_to_datetime(last_trim_ts)
            
            # Check against episode start for Virtual Success
            episode_start = s3_episode.get("started_at")
            episode_start_ts = self._iso_to_datetime(episode_start)
            
            if trim_dt and episode_start_ts and trim_dt > episode_start_ts:
                if not s3_episode.get("trimmed"):
                    s3_episode["trimmed"] = True
                    changed = True
            
            meta["last_consumed_trim_ts"] = last_trim_ts

        return changed

    def _process_episode_logging(
        self,
        position: Dict[str, Any],
        regime_context: Dict[str, Any],
        token_bucket: Optional[str],
        now: datetime,
        levers: Dict[str, Any] = None,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        features = position.get("features") or {}
        uptrend = features.get("uptrend_engine_v4") or {}
        if not uptrend:
            return [], False

        meta = self._ensure_episode_meta(features)
        strands: List[Dict[str, Any]] = []
        changed = False

        flags_changed = self._update_episode_entry_flags(meta, features)
        changed |= flags_changed
        
        # If flags changed (e.g. trim), sync outcomes immediately for S3 windows
        if flags_changed:
            s3_episode = meta.get("s3_episode")
            if s3_episode:
                self._compute_s3_window_outcomes(s3_episode)
                self._sync_s3_window_outcomes_to_db(s3_episode)

        state = uptrend.get("state")
        prev_state = meta.get("prev_state")

        if state and prev_state is None:
            meta["prev_state"] = state
            changed = True
            prev_state = state

        if state and prev_state and prev_state != state:
            episode_id = None
            if state == "S1" and prev_state == "S0":
                episode_id = self._generate_episode_id("s1")
                meta["s1_episode"] = {
                    "episode_id": episode_id,
                    "started_at": now.isoformat(),
                    "entered": False,
                    "windows": [],
                    "active_window": None,
                }
                changed = True
            elif state == "S3" and prev_state != "S3":
                episode_id = self._generate_episode_id("s3")
                meta["s3_episode"] = {
                    "episode_id": episode_id,
                    "started_at": now.isoformat(),
                    "windows": [],
                    "retest_index": 0,
                    "entered": False,
                    "active_window": None,
                }
                changed = True
            strand = self._build_stage_transition_strand(
                position=position,
                from_state=prev_state,
                to_state=state,
                uptrend_signals=uptrend,
                regime_context=regime_context,
                token_bucket=token_bucket,
                now=now,
                episode_id=episode_id,
                levers=levers,
            )
            strands.append(strand)

            s1_episode = meta.get("s1_episode")
            if s1_episode:
                if state == "S3":
                    outcome = "success"
                    # Update DB outcomes for all windows in this episode
                    self._update_episode_outcomes_from_meta(s1_episode, outcome)
                    
                    s1_episode.pop("active_window", None)
                    strands.append(
                        self._build_episode_summary_strand(
                            position=position,
                            episode=s1_episode,
                            outcome="missed" if not s1_episode.get("entered") else "success", # Keep legacy string for strand
                            regime_context=regime_context,
                            token_bucket=token_bucket,
                            now=now,
                            episode_type="s1_entry",
                            levers=levers,
                        )
                    )
                    meta["s1_episode"] = None
                    changed = True
                elif state == "S0" and prev_state in ("S1", "S2"):
                    outcome = "failure"
                    # Update DB outcomes for all windows in this episode
                    self._update_episode_outcomes_from_meta(s1_episode, outcome)

                    s1_episode.pop("active_window", None)
                    strands.append(
                        self._build_episode_summary_strand(
                            position=position,
                            episode=s1_episode,
                            outcome="correct_skip" if not s1_episode.get("entered") else "failure", # Keep legacy string for strand
                            regime_context=regime_context,
                            token_bucket=token_bucket,
                            now=now,
                            episode_type="s1_entry",
                            levers=levers,
                        )
                    )
                    meta["s1_episode"] = None
                    changed = True

            s3_episode = meta.get("s3_episode")
            if s3_episode and state == "S0":
                changed |= self._finalize_active_window(s3_episode, now, position, regime_context, token_bucket, uptrend, levers)
                self._compute_s3_window_outcomes(s3_episode)
                s3_outcome = self._compute_s3_episode_outcome(s3_episode)
                s3_episode["outcome"] = s3_outcome
                
                # Update DB outcomes for all windows in this episode
                # Note: S3 windows have individual outcomes based on trims, but the episode fail terminates all open ones.
                # _compute_s3_window_outcomes sets 'outcome' key in window dict.
                # We should sync these to DB.
                self._sync_s3_window_outcomes_to_db(s3_episode)

                s3_episode.pop("active_window", None)
                strands.append(
                    self._build_episode_summary_strand(
                        position=position,
                        episode=s3_episode,
                        outcome=s3_outcome,
                        regime_context=regime_context,
                        token_bucket=token_bucket,
                        now=now,
                        episode_type="s3_retest",
                        levers=levers,
                    )
                )
                meta["s3_episode"] = None
                changed = True

        if state and meta.get("prev_state") != state:
            meta["prev_state"] = state
            changed = True

        # Handle S1 windows (Trigger: Entry Zone)
        diagnostics = (uptrend.get("diagnostics") or {}).get("buy_check") or {}
        entry_zone_ok = bool(diagnostics.get("entry_zone_ok"))
        
        s1_episode = meta.get("s1_episode")
        if s1_episode:
            if state == "S1":
                active_window = s1_episode.get("active_window")
                if entry_zone_ok:
                    if not active_window:
                        active_window = {
                            "window_id": self._generate_episode_id("s1win"),
                            "window_type": "s1_buy_signal",
                            "started_at": now.isoformat(),
                            "samples": [],
                            "entered": False,
                        }
                        s1_episode["active_window"] = active_window
                        changed = True
                    sample = self._capture_s1_window_sample(uptrend, now, levers)
                    if sample:
                        self._append_window_sample(active_window, sample)
                        changed = True
                elif active_window:
                    changed |= self._finalize_active_window(s1_episode, now, position, regime_context, token_bucket, uptrend, levers)
            else:
                changed |= self._finalize_active_window(s1_episode, now, position, regime_context, token_bucket, uptrend, levers)

        # Handle S3 retest windows (Trigger: Price < EMA144)
        s3_episode = meta.get("s3_episode")
        
        ema_vals = uptrend.get("ema") or {}
        price = float(uptrend.get("price", 0.0))
        ema144 = float(ema_vals.get("ema144", 0.0))
        # In S3, EMA144 > EMA333. Price < EMA144 means we are in the band or lower (dipping).
        in_band = (price > 0 and ema144 > 0 and price < ema144)
        
        if s3_episode:
            if state == "S3":
                active_window = s3_episode.get("active_window")
                if in_band:
                    if not active_window:
                        retest_index = s3_episode.get("retest_index", 0) + 1
                        s3_episode["retest_index"] = retest_index
                        active_window = {
                            "window_id": self._generate_episode_id("s3win"),
                            "retest_index": retest_index,
                            "started_at": now.isoformat(),
                            "samples": [],
                            "entered": False,
                        }
                        s3_episode["active_window"] = active_window
                        changed = True
                    sample = self._capture_s3_window_sample(uptrend, now, levers)
                    if sample:
                        self._append_window_sample(active_window, sample)
                        changed = True
                elif active_window:
                    changed |= self._finalize_active_window(s3_episode, now, position, regime_context, token_bucket, uptrend, levers)
            else:
                changed |= self._finalize_active_window(s3_episode, now, position, regime_context, token_bucket, uptrend, levers)

        features["uptrend_episode_meta"] = meta
        position["features"] = features
        return strands, changed

    def _build_episode_summary_strand(
        self,
        position: Dict[str, Any],
        episode: Dict[str, Any],
        outcome: str,
        regime_context: Dict[str, Any],
        token_bucket: Optional[str],
        now: datetime,
        episode_type: str = "s1_entry",
        levers: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        features = position.get("features") or {}
        uptrend_signals = features.get("uptrend_engine_v4") or {}
        action_type = "entry" if episode_type == "s1_entry" else "add"
        pattern_key, action_category, scope = self._build_pattern_scope(
            position=position,
            uptrend_signals=uptrend_signals,
            action_type=action_type,
            regime_context=regime_context,
            token_bucket=token_bucket,
            state="S1" if episode_type == "s1_entry" else "S3",
            levers=levers,
        )
        position_id = position.get("id")
        timeframe = position.get("timeframe", self.timeframe)
        symbol = position.get("token_ticker") or position.get("token_contract")

        levers_considered = self._compute_lever_considerations(episode, episode_type)

        content = {
            "position_id": position_id,
            "episode_id": episode.get("episode_id"),
            "episode_type": episode_type,
            "outcome": outcome,
            "entered": episode.get("entered", False),
            "started_at": episode.get("started_at"),
            "ended_at": now.isoformat(),
            "pattern_key": pattern_key,
            "action_category": action_category,
            "scope": scope,
            "episode_edge": None,
            "windows": episode.get("windows", []),
            "levers_considered": levers_considered,
        }

        strand = {
            "id": f"uptrend_episode_{position_id}_{int(now.timestamp() * 1000)}",
            "module": "pm",
            "kind": "uptrend_episode_summary",
            "symbol": symbol,
            "timeframe": timeframe,
            "position_id": position_id,
            "trade_id": position.get("current_trade_id"),
            "content": content,
            "regime_context": regime_context or {},
            "tags": ["uptrend", "episode_summary"],
            "target_agent": "learning_system",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        return strand


    def _build_action_context(
        self,
        position: Dict[str, Any],
        action: Dict[str, Any],
        a_final: float,
        e_final: float
    ) -> Dict[str, Any]:
        """
        Build action_context for braiding system.
        
        Args:
            position: Position dict with features
            action: Action dict with decision_type, size_frac, reasons
            a_final: Final aggressiveness score
            e_final: Final exit assertiveness score
        
        Returns:
            action_context dict with all dimensions needed for braiding
        """
        features = position.get("features") or {}
        uptrend = features.get("uptrend_engine_v4") or {}
        ta = features.get("ta") or {}
        geometry = features.get("geometry") or {}
        exec_history = features.get("pm_execution_history") or {}
        
        # Get engine signals and flags
        state = uptrend.get("state", "")
        buy_signal = uptrend.get("buy_signal", False)
        buy_flag = uptrend.get("buy_flag", False)
        first_dip_buy_flag = uptrend.get("first_dip_buy_flag", False)
        trim_flag = uptrend.get("trim_flag", False)
        emergency_exit = uptrend.get("emergency_exit", False)
        reclaimed_ema333 = uptrend.get("reclaimed_ema333", False)
        
        # Get engine scores
        scores = uptrend.get("scores") or {}
        ts_score = float(scores.get("ts", 0.0))
        dx_score = float(scores.get("dx", 0.0))
        ox_score = float(scores.get("ox", 0.0))
        edx_score = float(scores.get("edx", 0.0))
        
        # Get EMA slopes
        ema_slopes_raw = ta.get("ema_slopes") or {}
        timeframe = position.get("timeframe", self.timeframe)
        ta_suffix = f"_{timeframe}" if timeframe != "1h" else ""
        
        ema_slopes = {}
        for key in ["ema60_slope", "ema144_slope", "ema250_slope", "ema333_slope"]:
            ema_slopes[key] = float(ema_slopes_raw.get(f"{key}{ta_suffix}", 0.0))
        
        # Get S/R levels
        sr_levels = geometry.get("levels", {}).get("sr_levels", []) if isinstance(geometry.get("levels"), dict) else []
        current_price = float(uptrend.get("price", 0.0))
        current_sr_level = None
        if sr_levels and current_price > 0:
            try:
                closest_sr = min(sr_levels, key=lambda x: abs(float(x.get("price", 0)) - current_price))
                current_sr_level = float(closest_sr.get("price", 0))
            except Exception:
                pass
        
        # Get timing info
        first_entry_ts = position.get("first_entry_timestamp") or position.get("created_at")
        bars_since_entry = 0
        if first_entry_ts:
            try:
                token_contract = position.get("token_contract", "")
                chain = position.get("token_chain", "").lower()
                from src.intelligence.lowcap_portfolio_manager.pm.actions import _count_bars_since
                bars_since_entry = _count_bars_since(first_entry_ts, token_contract, chain, timeframe, self.sb)
            except Exception:
                pass
        
        # Get action details
        decision_type = action.get("decision_type", "").lower()
        size_frac = float(action.get("size_frac", 0.0))
        reasons = action.get("reasons", {})
        
        # Build action_context
        action_context = {
            # A/E Scores
            "a_final": a_final,
            "e_final": e_final,
            "a_bucket": bucket_a_e(a_final),
            "e_bucket": bucket_a_e(e_final),
            
            # Uptrend Engine State & Signals
            "state": state,
            "buy_signal": buy_signal,
            "buy_flag": buy_flag,
            "first_dip_buy_flag": first_dip_buy_flag,
            "trim_flag": trim_flag,
            "emergency_exit": emergency_exit,
            "reclaimed_ema333": reclaimed_ema333,
            
            # Engine Scores
            "ts_score": ts_score,
            "dx_score": dx_score,
            "ox_score": ox_score,
            "edx_score": edx_score,
            "ts_score_bucket": bucket_score(ts_score),
            "dx_score_bucket": bucket_score(dx_score),
            "ox_score_bucket": bucket_score(ox_score),
            "edx_score_bucket": bucket_score(edx_score),
            
            # EMA Slopes
            "ema_slopes": ema_slopes,
            "ema_slopes_bucket": bucket_ema_slopes(ema_slopes),
            
            # Entry Zone Conditions (from uptrend engine diagnostics)
            "entry_zone_ok": uptrend.get("entry_zone", False),
            "slope_ok": uptrend.get("slope_ok", False),
            "ts_ok": uptrend.get("ts_ok", False),
            
            # S/R Levels
            "sr_levels": [float(x.get("price", 0)) for x in sr_levels[:5]] if sr_levels else [],
            "current_sr_level": current_sr_level,
            "sr_level_changed": reasons.get("sr_level_changed", False),
            
            # Action Details
            "action_type": decision_type,  # "add", "trim", "emergency_exit"
            "size_frac": size_frac,
            "size_bucket": bucket_size(size_frac),
            "entry_multiplier": reasons.get("entry_multiplier", 1.0),
            "trim_multiplier": reasons.get("trim_multiplier", 1.0),
            
            # Timing
            "bars_since_entry": bars_since_entry,
            "bars_since_entry_bucket": bucket_bars_since_entry(bars_since_entry),
            "bars_since_last_action": 0,  # TODO: Calculate from exec_history
            "bars_until_exit": None,  # Don't know yet
        }
        
        return action_context

    def _update_position_after_execution(
        self,
        position_id: int,
        decision_type: str,
        execution_result: Dict[str, Any],
        action: Dict[str, Any],
        position: Dict[str, Any],
        a_final: float,
        e_final: float
    ) -> None:
        """
        Update position table after execution.
        
        Args:
            position_id: Position ID
            decision_type: "add", "trim", "emergency_exit"
            execution_result: Result from executor.execute()
            action: Action dict with decision_type, size_frac, reasons
            position: Position dict with features
            a_final: Final aggressiveness score
            e_final: Final exit assertiveness score
        """
        if execution_result.get("status") != "success":
            return
        
        try:
            # Get current position
            current = (
                self.sb.table("lowcap_positions")
                .select("total_quantity,total_allocation_usd,total_extracted_usd,total_tokens_bought,total_tokens_sold,status,avg_entry_price,avg_exit_price,features,current_trade_id")
                .eq("id", position_id)
                .limit(1)
                .execute()
            ).data
            
            if not current:
                return
            
            current_pos = current[0]
            updates: Dict[str, Any] = {}
            
            # Update last_activity_timestamp on every action
            now_iso = datetime.now(timezone.utc).isoformat()
            updates["last_activity_timestamp"] = now_iso
            
            token_decimals = execution_result.get("token_decimals")
            if token_decimals is not None:
                try:
                    token_decimals = int(token_decimals)
                except (TypeError, ValueError):
                    token_decimals = None
            if token_decimals is not None:
                features = current_pos.get("features") or {}
                if features.get("token_decimals") != token_decimals:
                    features["token_decimals"] = token_decimals
                    updates["features"] = features
            
            reasons = action.get("reasons") or {}
            action_flag = (reasons.get("flag") or "").lower()
            size_frac = float(action.get("size_frac", 0.0))
            
            if decision_type in ("add", "entry"):
                # Add tokens and investment (USD tracking)
                tokens_bought = float(execution_result.get("tokens_bought", 0.0))
                notional_usd = float(execution_result.get("notional_usd", 0.0))  # Exact USD from executor tx
                entry_price = float(execution_result.get("price", 0.0))
                
                current_quantity = float(current_pos.get("total_quantity", 0.0))
                current_allocation_usd = float(current_pos.get("total_allocation_usd", 0.0))
                current_tokens_bought = float(current_pos.get("total_tokens_bought", 0.0))
                
                # Update cumulative fields (exact from executor)
                updates["total_quantity"] = current_quantity + tokens_bought
                updates["total_allocation_usd"] = current_allocation_usd + notional_usd  # Cumulative USD invested
                updates["total_tokens_bought"] = current_tokens_bought + tokens_bought
                
                # Calculate weighted average entry price (total_allocation_usd / total_tokens_bought)
                if (current_tokens_bought + tokens_bought) > 0:
                    updates["avg_entry_price"] = (current_allocation_usd + notional_usd) / (current_tokens_bought + tokens_bought)
                
                # Update status and trade tracking on first buy
                if current_pos.get("status") == "watchlist":
                    updates["status"] = "active"
                if not current_pos.get("current_trade_id"):
                    now_iso = datetime.now(timezone.utc).isoformat()
                    updates["first_entry_timestamp"] = now_iso
                    new_trade_id = str(uuid.uuid4())
                    updates["current_trade_id"] = new_trade_id
                    position["current_trade_id"] = new_trade_id
            
            elif decision_type in ["trim", "emergency_exit"]:
                # Remove tokens and add to extracted (USD tracking)
                tokens_sold = float(execution_result.get("tokens_sold", 0.0))
                actual_usd = float(execution_result.get("actual_usd", 0.0))  # Exact USD from executor tx
                exit_price = float(execution_result.get("price", 0.0))
                
                current_quantity = float(current_pos.get("total_quantity", 0.0))
                current_extracted_usd = float(current_pos.get("total_extracted_usd", 0.0))
                current_tokens_sold = float(current_pos.get("total_tokens_sold", 0.0))
                
                # Update cumulative fields (exact from executor)
                updates["total_quantity"] = max(0.0, current_quantity - tokens_sold)
                updates["total_extracted_usd"] = current_extracted_usd + actual_usd  # Cumulative USD extracted
                updates["total_tokens_sold"] = current_tokens_sold + tokens_sold
                
                # Calculate weighted average exit price (total_extracted_usd / total_tokens_sold)
                if (current_tokens_sold + tokens_sold) > 0:
                    updates["avg_exit_price"] = (current_extracted_usd + actual_usd) / (current_tokens_sold + tokens_sold)
                
                remaining_quantity = updates.get("total_quantity", current_quantity - tokens_sold)
                
                # Note: Trade closure is handled separately in _check_position_closure
                # based on state == S0 AND current_trade_id exists
                # We don't close here - just update quantities
            
            if updates:
                logger.info(
                    "pm_core_tick.exec_update decision=%s status_before=%s qty_before=%s tokens_sold=%s actual_usd=%s updates=%s",
                    decision_type,
                    current_pos.get("status"),
                    current_pos.get("total_quantity"),
                    execution_result.get("tokens_sold"),
                    execution_result.get("actual_usd"),
                    {k: updates[k] for k in ("total_quantity", "status") if k in updates},
                )
                self.sb.table("lowcap_positions").update(updates).eq("id", position_id).execute()
                # Keep position dict in sync for downstream logic (_write_strands uses trade_id)
                for key, value in updates.items():
                    position[key] = value
                
                # Recalculate P&L fields after execution (hybrid approach - update when data changes)
                try:
                    # Reload position with updated values
                    updated_pos_result = (
                        self.sb.table("lowcap_positions")
                        .select("*")
                        .eq("id", position_id)
                        .limit(1)
                        .execute()
                    )
                    if updated_pos_result.data:
                        updated_pos = updated_pos_result.data[0]
                        pnl_updates = self._recalculate_pnl_fields(updated_pos)
                        if pnl_updates:
                            self.sb.table("lowcap_positions").update(pnl_updates).eq("id", position_id).execute()
                except Exception as e:
                    logger.warning(f"Error recalculating P&L fields for position {position_id}: {e}")
                
        except Exception as e:
            logger.error(f"Error updating position {position_id} after execution: {e}")
    
    def _update_execution_history(
        self,
        position_id: int,
        decision_type: str,
        execution_result: Dict[str, Any],
        action: Dict[str, Any]
    ) -> None:
        """
        Update pm_execution_history in position features.
        
        Args:
            position_id: Position ID
            decision_type: "add", "trim", "emergency_exit"
            execution_result: Result from executor.execute()
            action: Action dict from plan_actions_v4()
        """
        if execution_result.get("status") != "success":
            return
        
        try:
            # Get current features
            current = (
                self.sb.table("lowcap_positions")
                .select("features")
                .eq("id", position_id)
                .limit(1)
                .execute()
            ).data
            
            if not current:
                return
            
            features = current[0].get("features") or {}
            execution_history = features.get("pm_execution_history") or {}
            
            now_iso = datetime.now(timezone.utc).isoformat()
            price = float(execution_result.get("price", 0.0))
            size_frac = float(action.get("size_frac", 0.0))
            
            # Get signal from action reasons
            reasons = action.get("reasons") or {}
            signal = reasons.get("flag") or decision_type
            
            # Update execution history based on decision type
            if decision_type in ["add", "entry"]:
                # Determine which buy signal (S1, S2, S3, reclaimed_ema333)
                if "s1" in signal.lower() or "buy_signal" in signal.lower():
                    execution_history["last_s1_buy"] = {
                        "timestamp": now_iso,
                        "price": price,
                        "size_frac": size_frac,
                        "signal": signal
                    }
                elif "s2" in signal.lower():
                    execution_history["last_s2_buy"] = {
                        "timestamp": now_iso,
                        "price": price,
                        "size_frac": size_frac,
                        "signal": signal
                    }
                elif "s3" in signal.lower():
                    execution_history["last_s3_buy"] = {
                        "timestamp": now_iso,
                        "price": price,
                        "size_frac": size_frac,
                        "signal": signal
                    }
                elif "reclaimed" in signal.lower() or "ema333" in signal.lower():
                    execution_history["last_reclaim_buy"] = {
                        "timestamp": now_iso,
                        "price": price,
                        "size_frac": size_frac,
                        "signal": signal
                    }
            
            elif decision_type in ["trim", "emergency_exit"]:
                execution_history["last_trim"] = {
                    "timestamp": now_iso,
                    "price": price,
                    "size_frac": size_frac,
                    "signal": signal
                }
            
            # Update prev_state if we have state info
            uptrend_engine = features.get("uptrend_engine_v4") or {}
            current_state = uptrend_engine.get("state")
            if current_state:
                execution_history["prev_state"] = current_state
            
            # Save back to features
            features["pm_execution_history"] = execution_history
            self.sb.table("lowcap_positions").update({"features": features}).eq("id", position_id).execute()
            
        except Exception as e:
            logger.error(f"Error updating execution history for position {position_id}: {e}")
    
    def _recalculate_pnl_fields(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recalculate P&L fields (hybrid approach - stored but recalculated when needed).
        
        Args:
            position: Position dict with current values
        
        Returns:
            Dict with updated P&L fields
        """
        updates: Dict[str, Any] = {}
        
        total_allocation_usd = float(position.get("total_allocation_usd") or 0.0)
        total_extracted_usd = float(position.get("total_extracted_usd") or 0.0)
        total_tokens_bought = float(position.get("total_tokens_bought") or 0.0)
        total_tokens_sold = float(position.get("total_tokens_sold") or 0.0)
        total_quantity = float(position.get("total_quantity") or 0.0)
        avg_entry_price = float(position.get("avg_entry_price") or 0.0) if position.get("avg_entry_price") is not None else 0.0
        avg_exit_price = float(position.get("avg_exit_price") or 0.0) if position.get("avg_exit_price") is not None else 0.0
        
        # Get current market price from latest OHLC
        token_contract = position.get("token_contract", "")
        token_chain = position.get("token_chain", "")
        timeframe = position.get("timeframe", self.timeframe)
        
        try:
            ohlc_result = (
                self.sb.table("lowcap_price_data_ohlc")
                .select("close_usd")
                .eq("token_contract", token_contract)
                .eq("chain", token_chain)
                .eq("timeframe", timeframe)
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            market_price = float(ohlc_result.data[0].get("close_usd", 0.0)) if ohlc_result.data else 0.0
        except Exception:
            market_price = 0.0
        
        # Calculate current_usd_value (total_quantity * market_price)
        current_usd_value = total_quantity * market_price if market_price > 0 else 0.0
        updates["current_usd_value"] = current_usd_value
        
        # Calculate realized P&L (rpnl_usd, rpnl_pct)
        if total_tokens_sold > 0 and avg_entry_price > 0 and avg_exit_price > 0:
            # Realized P&L = (tokens_sold * avg_exit_price) - (tokens_sold * avg_entry_price)
            rpnl_usd = (total_tokens_sold * avg_exit_price) - (total_tokens_sold * avg_entry_price)
            # rpnl_pct should use cost basis of sold tokens, not total allocation
            cost_basis_of_sold_tokens = total_tokens_sold * avg_entry_price
            rpnl_pct = (rpnl_usd / cost_basis_of_sold_tokens * 100.0) if cost_basis_of_sold_tokens > 0 else 0.0
            updates["rpnl_usd"] = rpnl_usd
            updates["rpnl_pct"] = rpnl_pct
        else:
            updates["rpnl_usd"] = 0.0
            updates["rpnl_pct"] = 0.0
        
        # Calculate total P&L (rpnl_usd + unrealized_pnl)
        # Unrealized P&L = current_usd_value - net_cost_basis (cost of remaining tokens)
        net_cost_basis = total_allocation_usd - total_extracted_usd
        unrealized_pnl = current_usd_value - net_cost_basis
        total_pnl_usd = updates.get("rpnl_usd", 0.0) + unrealized_pnl
        # total_pnl_pct should use net_cost_basis as denominator, not total_allocation_usd
        total_pnl_pct = (total_pnl_usd / net_cost_basis * 100.0) if net_cost_basis > 0 else 0.0
        updates["total_pnl_usd"] = total_pnl_usd
        updates["total_pnl_pct"] = total_pnl_pct
        
        # Calculate usd_alloc_remaining
        # Formula: (total_allocation_pct * wallet_balance) - (total_allocation_usd - total_extracted_usd)
        # NOTE: Always use Solana USDC balance (home chain) - all capital is centralized there
        total_allocation_pct = float(position.get("total_allocation_pct") or 0.0)
        if total_allocation_pct > 0:
            # Get Solana USDC balance (home chain - all capital is here)
            home_chain = os.getenv("HOME_CHAIN", "solana").lower()
            try:
                wallet_result = (
                    self.sb.table("wallet_balances")
                    .select("usdc_balance,balance_usd")
                    .eq("chain", home_chain)
                    .limit(1)
                    .execute()
                )
                if wallet_result.data:
                    row = wallet_result.data[0]
                    wallet_balance = float(row.get("usdc_balance") or row.get("balance_usd") or 0.0)
                else:
                    wallet_balance = 0.0
                    logger.warning(f"No wallet_balances row found for home chain={home_chain}, using 0.0")
            except Exception as e:
                wallet_balance = 0.0
                logger.warning(f"Error getting wallet balance for home chain {home_chain}: {e}")
            
            # Calculate max allocation and net deployed
            max_allocation_usd = wallet_balance * (total_allocation_pct / 100.0)
            net_deployed_usd = total_allocation_usd - total_extracted_usd
            usd_alloc_remaining = max_allocation_usd - net_deployed_usd
            
            logger.debug(f"usd_alloc_remaining calc (home_chain={home_chain}): wallet_balance=${wallet_balance:.2f}, total_allocation_pct={total_allocation_pct}%, max_allocation_usd=${max_allocation_usd:.2f}, net_deployed_usd=${net_deployed_usd:.2f}, usd_alloc_remaining=${usd_alloc_remaining:.2f}")
            
            updates["usd_alloc_remaining"] = max(0.0, usd_alloc_remaining)  # Can't be negative
        else:
            updates["usd_alloc_remaining"] = 0.0
        
        # Update timestamp
        updates["pnl_last_calculated_at"] = datetime.now(timezone.utc).isoformat()
        
        return updates
    
    def _calculate_rr_metrics(
        self,
        token_contract: str,
        chain: str,
        timeframe: str,
        entry_timestamp: datetime,
        exit_timestamp: datetime,
        entry_price: float,
        exit_price: float
    ) -> Dict[str, Any]:
        """
        Calculate R/R metrics from OHLCV data.
        
        Args:
            token_contract: Token contract address
            chain: Chain name
            timeframe: Timeframe (1m, 15m, 1h, 4h)
            entry_timestamp: Entry timestamp
            exit_timestamp: Exit timestamp
            entry_price: Entry price
            exit_price: Exit price
        
        Returns:
            Dict with rr, return, max_drawdown, max_gain
        """
        try:
            if entry_price <= 0 or exit_price <= 0:
                return {
                    "rr": None,
                    "return": None,
                    "max_drawdown": None,
                    "max_gain": None
                }
            
            # Query OHLCV data that overlaps with entry/exit time range
            # OHLC bars represent time periods, not exact timestamps
            # For a bar with timestamp T and duration D, it covers [T, T+D)
            # We need bars where: T <= exit_timestamp AND (T + D) >= entry_timestamp
            
            # Calculate timeframe duration in hours
            timeframe_hours = {
                "1m": 1/60,
                "15m": 15/60,
                "1h": 1,
                "4h": 4,
                "1d": 24
            }.get(timeframe, 1)
            
            # Find bars that start before or at exit, and end after or at entry
            # Bar starts at timestamp, ends at timestamp + timeframe_duration
            # We want: timestamp <= exit_timestamp AND (timestamp + duration) >= entry_timestamp
            # Which simplifies to: timestamp <= exit_timestamp AND timestamp >= (entry_timestamp - duration)
            
            from datetime import timedelta
            earliest_bar_start = entry_timestamp - timedelta(hours=timeframe_hours)
            
            # Query bars that could overlap: start <= exit AND start >= (entry - duration)
            ohlc_data = (
                self.sb.table("lowcap_price_data_ohlc")
                .select("timestamp,low_usd,high_usd")
                .eq("token_contract", token_contract)
                .eq("chain", chain)
                .eq("timeframe", timeframe)
                .gte("timestamp", earliest_bar_start.isoformat())  # Bar starts at or after (entry - duration)
                .lte("timestamp", exit_timestamp.isoformat())  # Bar starts at or before exit
                .order("timestamp", desc=False)  # Order by timestamp ascending
                .execute()
            ).data
            
            # Filter to only bars that actually overlap with [entry_timestamp, exit_timestamp]
            overlapping_bars = []
            for bar in ohlc_data:
                bar_timestamp = datetime.fromisoformat(bar["timestamp"].replace('Z', '+00:00'))
                bar_end = bar_timestamp + timedelta(hours=timeframe_hours)
                # Bar overlaps if: bar_start <= exit AND bar_end >= entry
                if bar_timestamp <= exit_timestamp and bar_end >= entry_timestamp:
                    overlapping_bars.append(bar)
            
            ohlc_data = overlapping_bars
            
            if not ohlc_data:
                logger.warning(f"No OHLCV data found for R/R calculation: {token_contract} {timeframe}")
                logger.warning(f"  Entry: {entry_timestamp.isoformat()}, Exit: {exit_timestamp.isoformat()}")
                logger.warning(f"  Timeframe: {timeframe} ({timeframe_hours}h duration)")
                logger.warning(f"  Query range: {earliest_bar_start.isoformat()} to {exit_timestamp.isoformat()}")
                return {
                    "rr": None,
                    "return": None,
                    "max_drawdown": None,
                    "max_gain": None
                }
            
            min_price = entry_price
            max_price = entry_price
            min_price_ts = entry_timestamp
            max_price_ts = entry_timestamp
            for bar in ohlc_data:
                bar_timestamp = datetime.fromisoformat(bar["timestamp"].replace('Z', '+00:00'))
                low_val = float(bar.get("low_usd") or entry_price)
                high_val = float(bar.get("high_usd") or entry_price)
                if low_val > 0 and low_val < min_price:
                    min_price = low_val
                    min_price_ts = bar_timestamp
                if high_val > 0 and high_val > max_price:
                    max_price = high_val
                    max_price_ts = bar_timestamp
            
            min_price = min(min_price, entry_price)
            max_price = max(max_price, entry_price)
            
            # Calculate metrics
            return_pct = (exit_price - entry_price) / entry_price if entry_price > 0 else 0.0
            max_drawdown = (entry_price - min_price) / entry_price if entry_price > 0 else 0.0
            max_gain = (max_price - entry_price) / entry_price if entry_price > 0 else 0.0
            
            # Calculate R/R ratio (return / max_drawdown)
            # Handle division by zero: if no drawdown, R/R is infinite (perfect trade)
            if max_drawdown > 0:
                rr = return_pct / max_drawdown
            else:
                # No drawdown - perfect trade (or entry was at absolute bottom)
                rr = float('inf') if return_pct > 0 else 0.0
            
            # Bound R/R to reasonable range (e.g., -10 to 10)
            if rr != float('inf') and rr != float('-inf'):
                rr = max(-10.0, min(10.0, rr))
            
            return {
                "rr": rr if rr != float('inf') and rr != float('-inf') else None,
                "return": return_pct,
                "max_drawdown": max_drawdown,
                "max_gain": max_gain,
                "min_price": min_price,
                "max_price": max_price,
                "best_entry_price": min_price,
                "best_entry_timestamp": min_price_ts.isoformat() if min_price_ts else None,
                "best_exit_price": max_price,
                "best_exit_timestamp": max_price_ts.isoformat() if max_price_ts else None
            }
            
        except Exception as e:
            logger.error(f"Error calculating R/R metrics: {e}")
            return {
                "rr": None,
                "return": None,
                "max_drawdown": None,
                "max_gain": None
            }
    
    def _check_position_closure(
        self,
        position: Dict[str, Any],
        decision_type: str,
        execution_result: Dict[str, Any],
        action: Dict[str, Any]
    ) -> bool:
        """
        Check if position should be closed and handle closure.
        
        Simple rule: If state is S0 AND current_trade_id exists → close the trade.
        
        This handles:
        - S1 → S0 (fast_band_at_bottom)
        - S3 → S0 (all EMAs below EMA333)
        
        Args:
            position: Position dict
            decision_type: Unused (kept for compatibility)
            execution_result: Unused (kept for compatibility)
            action: Unused (kept for compatibility)
        
        Returns:
            True if position was closed, False otherwise
        """
        position_id = position.get("id")
        features = position.get("features") or {}
        uptrend = features.get("uptrend_engine_v4") or {}
        state = uptrend.get("state", "")
        
        # Simple rule: state == S0 AND current_trade_id exists → close
        if state != "S0":
            return False
        
        # Check current position state
        current = (
            self.sb.table("lowcap_positions")
            .select("status,current_trade_id")
            .eq("id", position_id)
            .limit(1)
            .execute()
        ).data
        
        if not current:
            return False
        
        current_pos = current[0]
        
        # If already closed, skip
        if current_pos.get("status") == "watchlist":
            return False
        
        # If no trade_id, nothing to close
        if not current_pos.get("current_trade_id"):
            return False
        
        # State is S0 and we have an open trade → close it
        return self._close_trade_on_s0_transition(position_id, current_pos, uptrend)
    
    def _close_trade_on_s0_transition(
        self,
        position_id: int,
        current_pos: Dict[str, Any],
        uptrend: Dict[str, Any]
    ) -> bool:
        """
        Close trade when state transitions to S0 (after emergency_exit or structural exit).
        
        Args:
            position_id: Position ID
            current_pos: Current position row from DB
            uptrend: Uptrend engine state dict
        
        Returns:
            True if trade was closed, False otherwise
        """
        try:
            # Get position details for R/R calculation (including features for S3 timestamp)
            position_details = (
                self.sb.table("lowcap_positions")
                .select("first_entry_timestamp,avg_entry_price,created_at,token_contract,token_chain,timeframe,current_trade_id,completed_trades,entry_context,total_quantity,features")
                .eq("id", position_id)
                .limit(1)
                .execute()
            ).data
            
            if not position_details:
                return False
            
            pos_details = position_details[0]
            features = pos_details.get("features") or {}
            total_quantity = float(pos_details.get("total_quantity", 0.0))
            
            # Only close if position is empty (emergency_exit already sold everything)
            if total_quantity > 0:
                return False
            
            # Get latest price for exit
            token_contract = pos_details.get("token_contract")
            chain = pos_details.get("token_chain")
            timeframe = pos_details.get("timeframe", self.timeframe)
            
            try:
                ohlc_result = (
                    self.sb.table("lowcap_price_data_ohlc")
                    .select("close_usd")
                    .eq("token_contract", token_contract)
                    .eq("chain", chain)
                    .eq("timeframe", timeframe)
                    .order("timestamp", desc=True)
                    .limit(1)
                    .execute()
                )
                exit_price = float(ohlc_result.data[0].get("close_usd", 0.0)) if ohlc_result.data else 0.0
            except Exception:
                exit_price = 0.0
            
            exit_timestamp = datetime.now(timezone.utc)
            entry_price = float(pos_details.get("avg_entry_price", 0.0))
            entry_context = pos_details.get("entry_context") or {}
            
            # Use first_entry_timestamp if available, otherwise created_at
            entry_timestamp_str = pos_details.get("first_entry_timestamp") or pos_details.get("created_at")
            if isinstance(entry_timestamp_str, str):
                entry_timestamp = datetime.fromisoformat(entry_timestamp_str.replace('Z', '+00:00'))
            else:
                entry_timestamp = exit_timestamp
            
            # Get decision_type from exit_reason (if available) or default to "emergency_exit"
            decision_type = uptrend.get("exit_reason", "emergency_exit")
            # Normalize exit_reason to decision_type format
            if decision_type == "fast_band_at_bottom" or decision_type == "all_emas_below_333":
                decision_type = "emergency_exit"
            
            # Calculate time_to_s3: time from entry to S3 state transition
            time_to_s3 = None
            uptrend_meta = features.get("uptrend_engine_v4_meta") or {}
            s3_start_ts_str = uptrend_meta.get("s3_start_ts")
            
            if s3_start_ts_str:
                try:
                    s3_start_ts = datetime.fromisoformat(s3_start_ts_str.replace('Z', '+00:00'))
                    if s3_start_ts >= entry_timestamp:
                        time_to_s3 = (s3_start_ts - entry_timestamp).total_seconds() / (24 * 3600)
                except Exception:
                    pass
            
            # Calculate R/R from OHLCV data
            rr_metrics = self._calculate_rr_metrics(
                token_contract=token_contract,
                chain=chain,
                timeframe=timeframe,
                entry_timestamp=entry_timestamp,
                exit_timestamp=exit_timestamp,
                entry_price=entry_price,
                exit_price=exit_price
            )
            
            completed_trades = pos_details.get("completed_trades") or []
            if not isinstance(completed_trades, list):
                completed_trades = []
            
            # Calculate hold time
            hold_time_days = (exit_timestamp - entry_timestamp).total_seconds() / (24 * 3600)
            
            # Classify outcome
            rr_value = rr_metrics.get("rr")
            if rr_value is None:
                logger.warning(
                    f"Could not calculate R/R for position {position_id} on S0 transition"
                )
                rr = 0.0
            else:
                rr = float(rr_value)
            
            outcome_class = classify_outcome(rr)
            hold_time_class = classify_hold_time(hold_time_days)
            
            # Calculate counterfactuals (could_enter_better, could_exit_better)
            min_price = float(rr_metrics.get("min_price", entry_price))
            max_price = float(rr_metrics.get("max_price", exit_price))
            best_entry_price = float(rr_metrics.get("best_entry_price", min_price)) if rr_metrics.get("best_entry_price") is not None else min_price
            best_exit_price = float(rr_metrics.get("best_exit_price", max_price)) if rr_metrics.get("best_exit_price") is not None else max_price
            best_entry_ts = rr_metrics.get("best_entry_timestamp") or entry_timestamp.isoformat()
            best_exit_ts = rr_metrics.get("best_exit_timestamp") or exit_timestamp.isoformat()
            
            risk = entry_price - min_price
            if risk <= 0:
                risk = None
            missed_entry_rr = None
            missed_exit_rr = None
            if risk:
                missed_entry_rr = max(0.0, (entry_price - best_entry_price) / risk) if best_entry_price is not None else 0.0
                missed_exit_rr = max(0.0, (best_exit_price - exit_price) / risk) if best_exit_price is not None else 0.0
            else:
                missed_entry_rr = 0.0
                missed_exit_rr = 0.0
            
            cf_entry_bucket = bucket_cf_improvement(missed_entry_rr)
            cf_exit_bucket = bucket_cf_improvement(missed_exit_rr)
            
            could_enter_better = {
                "best_entry_price": best_entry_price,
                "best_entry_timestamp": best_entry_ts,
                "missed_rr": missed_entry_rr
            }
            could_exit_better = {
                "best_exit_price": best_exit_price,
                "best_exit_timestamp": best_exit_ts,
                "missed_rr": missed_exit_rr
            }
            
            # Get v5 fields from pm_action strands for this position
            v5_fields = {}
            try:
                action_strands = (
                    self.sb.table("ad_strands")
                    .select("content,created_at")
                    .eq("module", "pm")
                    .eq("kind", "pm_action")
                    .eq("position_id", position_id)
                    .order("created_at", desc=True)
                    .execute()
                )
                if action_strands.data and len(action_strands.data) > 0:
                    action_content = action_strands.data[0].get("content", {})
                    if action_content.get("pattern_key"):
                        v5_fields["pattern_key"] = action_content["pattern_key"]
                    if action_content.get("action_category"):
                        v5_fields["action_category"] = action_content["action_category"]
                    if action_content.get("scope"):
                        v5_fields["scope"] = action_content["scope"]
                    if action_content.get("controls"):
                        v5_fields["controls"] = action_content["controls"]
            except Exception as e:
                logger.warning(f"Error fetching v5 fields from pm_action strands: {e}")
            
            # Build trade summary (same structure as original _check_position_closure)
            trade_summary = {
                "entry_context": entry_context,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "entry_timestamp": entry_timestamp.isoformat(),
                "exit_timestamp": exit_timestamp.isoformat(),
                "decision_type": decision_type,
                "rr": rr,
                "return": rr_metrics.get("return"),
                "max_drawdown": rr_metrics.get("max_drawdown"),
                "max_gain": rr_metrics.get("max_gain"),
                "could_enter_better": could_enter_better,
                "could_exit_better": could_exit_better,
                "cf_entry_improvement_bucket": cf_entry_bucket,
                "cf_exit_improvement_bucket": cf_exit_bucket,
                "outcome_class": outcome_class,
                "hold_time_bars": None,  # TODO: Calculate from OHLCV if needed
                "hold_time_days": hold_time_days,
                "hold_time_class": hold_time_class,
                "time_to_s3": time_to_s3,  # Time from entry to S3 state transition (None if never reached S3)
                # Include v5 fields for aggregation
                **v5_fields
            }
            
            trade_id = pos_details.get("current_trade_id")
            if not trade_id:
                trade_id = str(uuid.uuid4())
            trade_summary["trade_id"] = trade_id
            
            # Build actions summary
            actions_summary: List[Dict[str, Any]] = []
            try:
                action_rows = (
                    self.sb.table("ad_strands")
                    .select("id,content,created_at")
                    .eq("kind", "pm_action")
                    .eq("position_id", position_id)
                    .eq("trade_id", trade_id)
                    .order("created_at")
                    .execute()
                ).data or []
                for row in action_rows:
                    content = row.get("content") or {}
                    actions_summary.append({
                        "strand_id": row.get("id"),
                        "ts": row.get("created_at"),
                        "decision_type": content.get("decision_type"),
                        "pattern_key": content.get("pattern_key"),
                        "action_category": content.get("action_category"),
                        "scope": content.get("scope"),
                        "controls": content.get("controls")
                    })
            except Exception as e:
                logger.warning(f"Error loading pm_action strands for trade {trade_id}: {e}")
            
            trade_cycle_entry = {
                "trade_id": trade_id,
                "actions": actions_summary,
                "summary": trade_summary
            }
            completed_trades.append(trade_cycle_entry)
            
            # Update position
            self.sb.table("lowcap_positions").update({
                "completed_trades": completed_trades,
                "status": "watchlist",
                "closed_at": exit_timestamp.isoformat(),
                "current_trade_id": None,
                "last_activity_timestamp": exit_timestamp.isoformat(),
                "features": features,
            }).eq("id", position_id).execute()
            
            # Emit position_closed strand
            regime_context = self._get_regime_context()
            position_closed_strand = {
                "id": f"position_closed_{position_id}_{int(exit_timestamp.timestamp() * 1000)}",
                "module": "pm",
                "kind": "position_closed",
                "symbol": current_pos.get("token_ticker") or token_contract,
                "timeframe": timeframe,
                "position_id": position_id,
                "trade_id": trade_id,
                "content": {
                    "position_id": position_id,
                    "token_contract": token_contract,
                    "chain": chain,
                    "ts": exit_timestamp.isoformat(),
                    "entry_context": entry_context,
                    "trade_id": trade_id,
                    "trade_summary": trade_summary,
                    "decision_type": decision_type,
                    "exit_reason": uptrend.get("exit_reason", "state_transition_to_s0"),
                },
                "regime_context": regime_context,
                "tags": ["position_closed", "pm", "learning"],
                "target_agent": "learning_system",
                "created_at": exit_timestamp.isoformat(),
                "updated_at": exit_timestamp.isoformat(),
            }
            
            self.sb.table("ad_strands").insert(position_closed_strand).execute()
            logger.info(f"Position {position_id} closed on S0 transition - emitted position_closed strand")
            return True
            
        except Exception as e:
            logger.error(f"Error closing trade on S0 transition for position {position_id}: {e}")
            return False
            if self.learning_system:
                try:
                    # Process strand in learning system (async call from sync context)
                    # Since run() is synchronous and called from thread pool, we create a new event loop
                    # Position closures are rare (1-2 per day), so blocking is acceptable
                    import asyncio
                    asyncio.run(self.learning_system.process_strand_event(position_closed_strand))
                    logger.info(f"Learning system processed position_closed strand: {position_id}")
                except Exception as e:
                    logger.error(f"Error processing position_closed strand in learning system: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            else:
                logger.warning(f"Learning system not available - position_closed strand not processed: {position_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling position closure for {position_id}: {e}")
            return False
    
    def _write_strands(self, position: Dict[str, Any], token: str, now: datetime, a_val: float, e_val: float, phase: str, cut_pressure: float, actions: list[dict], execution_results: Dict[str, Dict[str, Any]] = None, regime_context: Dict[str, Dict[str, Any]] = None, token_bucket: Optional[str] = None) -> None:
        """
        Write strands for PM actions.
        
        Args:
            position: Position dict (for position_id, timeframe, chain)
            token: Token contract address or ticker
            now: Current timestamp
            a_val: Aggressiveness score
            e_val: Exit assertiveness score
            phase: Meso phase
            cut_pressure: Cut pressure value
            actions: List of action dicts
            execution_results: Execution results dict
            regime_context: Regime context with macro/meso/micro phases
            token_bucket: Token's cap bucket (e.g., "micro")
        """
        rows = []
        position_id = position.get("id")
        timeframe = position.get("timeframe", self.timeframe)
        chain = position.get("token_chain", "").lower()
        token_ticker = position.get("token_ticker") or token
        
        trade_id = position.get("current_trade_id")
        
        for act in actions:
            # Skip hold actions (only actions emit strands)
            decision_type = act.get("decision_type", "").lower()
            if decision_type == "hold" or not decision_type:
                continue
            
            # Merge lever diagnostics into reasons for audit
            lever_diag = {}
            try:
                lever_diag = (act.get("lever_diag") or {})  # actions may not include; fallback below
            except Exception:
                lever_diag = {}
            reasons = {**(act.get("reasons") or {}), **lever_diag, "phase_meso": phase, "cut_pressure": cut_pressure}
            # Derive a simple ordered reasons list for audit (stable key order)
            preferred_order = [
                "phase_meso",
                "cut_pressure",
                "envelope",
                "mode",
                "sr_break",
                "diag_break",
                "sr_conf",
                "diag_conf",
                "trail",
                "obv_slope",
                "vo_z",
                "retrace_r",
                "zone",
                "std_hits",
                "strong",
                "zone_trim_count",
                "moon_bag_target",
                "moon_bag_clamped",
            ]
            reasons_ordered: list[dict] = []
            for k in preferred_order:
                if k in reasons:
                    reasons_ordered.append({"name": k, "value": reasons[k]})
            # append any remaining keys deterministically
            for k in sorted(reasons.keys()):
                if k not in {r["name"] for r in reasons_ordered}:
                    reasons_ordered.append({"name": k, "value": reasons[k]})
            
            # Extract v5 pattern key, action_category, scope, and controls
            try:
                features = position.get("features") or {}
                uptrend_signals = features.get("uptrend_engine_v4") or {}
                
                # Build action_context for pattern key generation
                action_context = {
                    "state": uptrend_signals.get("state", "Unknown"),
                    "timeframe": timeframe,
                    "a_final": a_val,
                    "e_final": e_val,
                    "buy_flag": uptrend_signals.get("buy_flag", False),
                    "first_dip_buy_flag": uptrend_signals.get("first_dip_buy_flag", False),
                    "reclaimed_ema333": uptrend_signals.get("reclaimed_ema333", False),
                    "at_support": (features.get("geometry") or {}).get("at_support", False),
                    "market_family": "lowcaps",  # PM only trades lowcaps
                }
                
                # Generate canonical pattern key and action_category
                pattern_key, action_category = generate_canonical_pattern_key(
                    module="pm",
                    action_type=decision_type,
                    action_context=action_context,
                    uptrend_signals=uptrend_signals
                )
                
                # Extract scope
                bucket_rank = regime_context.get("bucket_rank", []) if regime_context else []
                scope = extract_scope_from_context(
                    action_context=action_context,
                    regime_context=regime_context or {},
                    position_bucket=token_bucket,
                    bucket_rank=bucket_rank
                )
                
                # Extract controls (signals + applied knobs)
                # Note: applied_knobs would come from plan_actions_v4 or overrides
                # For now, we'll extract what we can from the action/reasons
                applied_knobs = {
                    "entry_delay_bars": reasons.get("entry_delay_bars"),
                    "phase1_frac": reasons.get("phase1_frac"),
                    "trim_delay": reasons.get("trim_delay"),
                    "trail_speed": reasons.get("trail_speed"),
                }
                controls = extract_controls_from_action(
                    action_context=action_context,
                    uptrend_signals=uptrend_signals,
                    applied_knobs=applied_knobs
                )
            except Exception as e:
                logger.warning(f"Error extracting v5 pattern data for {token}: {e}")
                pattern_key = None
                action_category = None
                scope = {}
                controls = {}
            
            # Build content JSONB with all PM-specific operational data
            content_data = {
                "position_id": position_id,  # Include in content too
                "token_contract": token,
                "chain": chain,
                "ts": now.replace(second=0, microsecond=0, tzinfo=timezone.utc).isoformat(),
                "decision_type": act.get("decision_type"),
                "size_frac": float(act.get("size_frac", 0.0)),
                "a_value": a_val,
                "e_value": e_val,
                "reasons": {"ordered": reasons_ordered, **reasons},
                "new_token_mode": False,
            }

            learning_mults = act.get("learning_multipliers") or {}
            if learning_mults:
                content_data["learning_multipliers"] = learning_mults
                if "pm_strength" in learning_mults:
                    content_data.setdefault("pm_strength_applied", learning_mults["pm_strength"])
                if "exposure_skew" in learning_mults:
                    content_data.setdefault("exposure_skew_applied", learning_mults["exposure_skew"])
                if "combined_multiplier" in learning_mults:
                    content_data.setdefault("pm_final_multiplier", learning_mults["combined_multiplier"])
            
            # Add v5 learning fields if available
            if pattern_key:
                content_data["pattern_key"] = pattern_key
            if action_category:
                content_data["action_category"] = action_category
            if scope:
                content_data["scope"] = scope
            if controls:
                content_data["controls"] = controls
            if trade_id:
                content_data["trade_id"] = trade_id
            
            # Add execution result if available
            if execution_results:
                exec_key = f"{position_id}:{act.get('decision_type')}"
                exec_result = execution_results.get(exec_key)
                if exec_result:
                    content_data["execution_result"] = {
                        "status": exec_result.get("status"),
                        "tx_hash": exec_result.get("tx_hash"),
                        "slippage": exec_result.get("slippage"),
                        "price": exec_result.get("price"),
                    }
            
            # Build strand with proper ad_strands schema structure
            strand = {
                "id": f"pm_action_{position_id}_{decision_type}_{int(now.timestamp() * 1000)}",
                "module": "pm",
                "kind": "pm_action",
                "symbol": token_ticker,
                "timeframe": timeframe,
                "position_id": position_id,  # Top-level column for querying
                "trade_id": trade_id,
                "content": content_data,  # All PM-specific data in content JSONB
                "regime_context": regime_context or {},  # Macro/meso/micro phases
                "tags": ["pm_action", "execution", decision_type],
                "target_agent": "learning_system",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
            
            rows.append(strand)
        if not rows:
            return
        try:
            self.sb.table("ad_strands").insert(rows).execute()
            # Emit decision_approved events (note: realized_proceeds not available here)
            try:
                from src.intelligence.lowcap_portfolio_manager.events.bus import emit
                for r in rows:
                    decision_type_emit = r.get("content", {}).get("decision_type", "")
                    if str(decision_type_emit or "").lower() != "hold":
                        emit("decision_approved", {
                            "token": r.get("content", {}).get("token_contract"),
                            "decision_type": decision_type_emit,
                            "a_value": r.get("content", {}).get("a_value"),
                            "e_value": r.get("content", {}).get("e_value"),
                            "phase_meso": phase,
                            "realized_proceeds": 0.0,
                        })
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"strand write failed for {token}: {e}")

    def run(self) -> int:
        now = datetime.now(timezone.utc)
        meso = self._latest_phase()
        phase = meso.get("phase") or ""
        cp = self._latest_cut_pressure()
        # Load macro phase (portfolio-level); neutral if missing
        macro_row = (
            self.sb.table("phase_state")
            .select("phase,ts")
            .eq("token", "PORTFOLIO")
            .eq("horizon", "macro")
            .order("ts", desc=True)
            .limit(1)
            .execute()
            .data
            or [{}]
        )[0]
        macro_phase = macro_row.get("phase") or ""
        
        # Get regime context (macro/meso/micro) for all PM strands
        regime_context = self._get_regime_context()
        pm_cfg = load_pm_config()
        pm_cfg = fetch_and_merge_db_config(pm_cfg, self.sb)
        bucket_cfg = pm_cfg.get("bucket_order_multipliers") or {}
        exposure_lookup = self._build_exposure_lookup(regime_context, pm_cfg)

        positions = self._active_positions()
        token_keys = [(p.get("token_contract"), p.get("token_chain")) for p in positions]
        bucket_map = self._fetch_token_buckets(token_keys)
        written = 0
        actions_enabled = (os.getenv("ACTIONS_ENABLED", "0") == "1")
        use_v4 = (os.getenv("PM_USE_V4", "1") == "1")  # Default to v4, can disable with env var
        
        for p in positions:
            token_contract = p.get("token_contract")
            token_chain = p.get("token_chain")
            token = token_contract or p.get("token_ticker") or "UNKNOWN"
            features = p.get("features") or {}
            token_bucket = bucket_map.get((token_contract, token_chain)) or bucket_map.get((token_contract, None))

            # Compute levers first so we can log A/E values in episode events
            le = compute_levers(
                macro_phase,
                str(phase),
                cp,
                features,
                bucket_context=regime_context,
                position_bucket=token_bucket,
                bucket_config=bucket_cfg,
            )
            a_final = float(le["A_value"])  # per-position intent deltas + age/mcap boosts
            e_final = float(le["E_value"])  # cut_pressure and macro applied
            position_size_frac = float(le.get("position_size_frac", 0.33))  # continuous sizing

            episode_strands: List[Dict[str, Any]] = []
            meta_changed = False
            try:
                episode_strands, meta_changed = self._process_episode_logging(
                    position=p,
                    regime_context=regime_context,
                    token_bucket=token_bucket,
                    now=now,
                    levers=le, # Pass levers for factor logging
                )
            except Exception as episode_err:
                logger.warning(f"Episode logging failed for position {p.get('id')}: {episode_err}")
                episode_strands = []
                meta_changed = False

            if meta_changed:
                try:
                    self.sb.table("lowcap_positions").update({"features": p.get("features")}).eq("id", p.get("id")).execute()
                except Exception as update_err:
                    logger.warning(f"Failed to persist episode meta for position {p.get('id')}: {update_err}")
            if episode_strands:
                try:
                    self.sb.table("ad_strands").insert(episode_strands).execute()
                except Exception as strand_err:
                    logger.warning(f"Failed to insert episode strands for position {p.get('id')}: {strand_err}")
            
            # Recalculate P&L fields before decisions (hybrid approach - check if stale)
            pnl_last_calculated = p.get("pnl_last_calculated_at")
            should_recalculate = False
            
            if not pnl_last_calculated:
                should_recalculate = True
            else:
                try:
                    last_calc_dt = datetime.fromisoformat(pnl_last_calculated.replace("Z", "+00:00"))
                    minutes_since = (now - last_calc_dt).total_seconds() / 60.0
                    # Recalculate if > 5 minutes old (hybrid approach)
                    should_recalculate = minutes_since > 5.0
                except Exception:
                    should_recalculate = True
            
            if should_recalculate:
                try:
                    pnl_updates = self._recalculate_pnl_fields(p)
                    if pnl_updates:
                        self.sb.table("lowcap_positions").update(pnl_updates).eq("id", p.get("id")).execute()
                        # Update p dict with new values for this iteration
                        p.update(pnl_updates)
                except Exception as e:
                    logger.warning(f"Error recalculating P&L fields for position {p.get('id')}: {e}")
            
            # Use v4 if enabled, otherwise fall back to old plan_actions
            if use_v4 and actions_enabled:
                # Get feature flags from config (if available)
                feature_flags = {}
                feature_flags = pm_cfg.get("feature_flags", {})
                
                actions = plan_actions_v4(
                    p, a_final, e_final, str(phase), self.sb,
                    regime_context=regime_context,
                    token_bucket=token_bucket,
                    feature_flags=feature_flags,
                    exposure_lookup=exposure_lookup
                )
            elif actions_enabled:
                actions = plan_actions(p, a_final, e_final, str(phase), exposure_lookup=exposure_lookup)
            else:
                actions = [{"decision_type": "hold", "size_frac": 0.0, "reasons": {}}]
            
            # Attach enhanced A/E diagnostics to each action for strand auditing
            try:
                diag = le.get("diagnostics") or {}
                for act in actions:
                    act["lever_diag"] = {
                        **diag,
                        "a_e_components": {
                            "a_final": a_final,
                            "e_final": e_final,
                            "position_size_frac": position_size_frac,
                            "phase_macro": macro_phase,
                            "phase_meso": str(phase),
                            "cut_pressure": cp,
                            "active_positions": len(positions)
                        }
                    }
            except Exception:
                pass
            
            # Execute actions and collect results
            execution_results: Dict[str, Dict[str, Any]] = {}
            
            for act in actions:
                decision_type = act.get("decision_type", "").lower()
                
                # Skip hold actions
                if decision_type == "hold" or not decision_type:
                    continue
                
                # Execute via executor
                try:
                    exec_result = self.executor.execute(act, p)
                    exec_key = f"{p.get('id')}:{decision_type}"
                    execution_results[exec_key] = exec_result
                    
                    # Update position table
                    if exec_result.get("status") == "success":
                        # Get a_final and e_final from the action's lever_diag if available
                        lever_diag = act.get("lever_diag", {})
                        a_e_components = lever_diag.get("a_e_components", {})
                        a_final = float(a_e_components.get("a_final", 0.5))
                        e_final = float(a_e_components.get("e_final", 0.5))
                        
                        self._update_position_after_execution(
                            p.get("id"), decision_type, exec_result, act, p, a_final, e_final
                        )
                        self._update_execution_history(p.get("id"), decision_type, exec_result, act)
                except Exception as e:
                    logger.error(f"Error executing action for position {p.get('id')}: {e}")
                    execution_results[f"{p.get('id')}:{decision_type}"] = {
                        "status": "error",
                        "error": str(e)
                    }
            
            # Check for position closure after all actions (state-based, not action-based)
            # This handles S0 transitions regardless of which action triggered it
            self._check_position_closure(p, "", {}, {})
            
            # Write strands with execution results
            self._write_strands(p, str(token), now, a_final, e_final, str(phase), cp, actions, execution_results, regime_context, token_bucket)
            written += len(actions)
        logger.info("pm_core_tick (%s) wrote %d strands for %d positions", self.timeframe, written, len(positions))
        return written


# Event-subscribe path for immediate recompute on structure/trail changes
def _subscribe_events() -> None:
    try:
        from intelligence.lowcap_portfolio_manager.events.bus import subscribe

        def on_structure_change(_payload: dict) -> None:
            try:
                PMCoreTick().run()
            except Exception:
                pass

        subscribe('structure_change', on_structure_change)

        def on_phase_transition(_payload: dict) -> None:
            try:
                # Recompute on phase flips (affects A/E globally)
                PMCoreTick().run()
            except Exception:
                pass

        subscribe('phase_transition', on_phase_transition)

        def on_sr_break(_payload: dict) -> None:
            try:
                PMCoreTick().run()
            except Exception:
                pass

        def on_trail_breach(_payload: dict) -> None:
            try:
                PMCoreTick().run()
            except Exception:
                pass

        subscribe('sr_break_detected', on_sr_break)
        subscribe('ema_trail_breach', on_trail_breach)
    except Exception:
        pass


def main(timeframe: str = "1h", learning_system=None) -> None:
    """
    Main entry point for PM Core Tick.
    
    Args:
        timeframe: Timeframe to process (1m, 15m, 1h, 4h)
        learning_system: Optional learning system instance for processing position_closed strands
    """
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    _subscribe_events()
    PMCoreTick(timeframe=timeframe, learning_system=learning_system).run()


if __name__ == "__main__":
    main()


