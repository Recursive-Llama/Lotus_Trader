"""
Regime A/E Calculator

Computes Aggressiveness (A) and Exitness (E) scores based on regime driver states.

The system uses 5 regime drivers across 3 timeframes:
- BTC: Bitcoin trend (affects all tokens)
- ALT: Altcoin composite trend (affects all tokens)
- BUCKET: Market cap bucket composite (nano/small/mid/big) - affects only that bucket
- BTC.d: BTC dominance (inverted - uptrend = risk-off for alts)
- USDT.d: USDT dominance (inverted - uptrend = strong risk-off, 3x weight)

Timeframes:
- Macro (1d): Slowest, strongest influence
- Meso (1h): Main operational timeframe
- Micro (1m): Tactical adjustments

Reference: docs/inprogress/Regime_engine.md
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from supabase import Client, create_client  # type: ignore

logger = logging.getLogger(__name__)


# =============================================================================
# Constants from spec
# =============================================================================

@dataclass(frozen=True)
class RegimeConstants:
    """All regime-related constants from the spec."""
    
    # Neutral baseline for A/E
    A_BASE: float = 0.5
    E_BASE: float = 0.5
    
    # Intent delta cap (capped at ±0.4 per original design)
    INTENT_CAP: float = 0.4
    
    # Final A/E clamp range
    A_MIN: float = 0.0
    A_MAX: float = 1.0
    E_MIN: float = 0.0
    E_MAX: float = 1.0


# Timeframe weights (per spec: macro 0.50, meso 0.40, micro 0.10)
TIMEFRAME_WEIGHTS = {
    "1d": 0.50,  # Macro
    "1h": 0.40,  # Meso
    "1m": 0.10,  # Micro
}

# Driver weights (per spec)
# Positive = risk-on when trending up
# Negative = risk-off when trending up (dominance)
DRIVER_WEIGHTS = {
    "BTC": 1.0,      # Weakest positive driver
    "ALT": 1.5,      # Stronger alt environment indicator
    "BUCKET": 3.0,   # Strongest local signal (most predictive)
    "BTC.d": -1.0,   # Inverted (BTC dominance up = alts suffer)
    "USDT.d": -3.0,  # Strong inverted (USDT dominance up = risk-off)
}

# Bucket driver names (maps token bucket to regime driver)
BUCKET_DRIVERS = {
    "nano": "nano",
    "small": "small",
    "mid": "mid",
    "big": "big",
}

# Execution timeframe multipliers
# Determines how much macro/meso/micro matter for each trading timeframe
EXEC_TF_MULTIPLIERS = {
    "1m": {"1d": 0.05, "1h": 0.35, "1m": 0.60},   # Micro dominates for scalps
    "5m": {"1d": 0.10, "1h": 0.50, "1m": 0.40},
    "15m": {"1d": 0.15, "1h": 0.55, "1m": 0.30},
    "1h": {"1d": 0.30, "1h": 0.55, "1m": 0.15},   # Default baseline
    "4h": {"1d": 0.55, "1h": 0.40, "1m": 0.05},
    "1d": {"1d": 0.80, "1h": 0.18, "1m": 0.02},   # Macro dominates
}


# =============================================================================
# State/Flag/Transition Delta Tables (per spec)
# =============================================================================

# Base state deltas (bullish drivers: BTC, ALT, BUCKET)
# For dominance (BTC.d, USDT.d), these are applied with negative driver weights
# which automatically inverts the effect
STATE_DELTAS = {
    # State: (ΔA_base, ΔE_base)
    "S0": (-0.30, +0.30),  # Downtrend/bad: strong risk-off
    "S1": (+0.25, -0.15),  # Early uptrend: best asymmetry, A high, E low
    "S2": (+0.10, +0.05),  # No man's land: cautious, A lower than S1
    "S3": (+0.20, -0.05),  # Confirmed uptrend: A elevated, E slightly below neutral
    "S4": (0.0, 0.0),      # Holding pattern: neutral
}

# Flag modifiers (additive on top of base state)
FLAG_DELTAS = {
    # (state, flag): (ΔA_flag, ΔE_flag)
    ("S1", "buy_signal"): (+0.20, -0.10),       # Strong "go" signal
    ("S2", "buy_flag"): (+0.10, -0.05),         # Weak buy (retest at EMA333)
    ("S2", "trim_flag"): (-0.20, +0.25),        # Respect trims in no man's land
    ("S3", "buy_flag"): (+0.05, -0.05),         # Rare, trend already confirmed
    ("S3", "first_dip_buy_flag"): (+0.15, -0.10),  # First dip buy in S3
    ("S3", "trim_flag"): (-0.25, +0.30),        # Biggest harvest (S3 extension)
}

# Rebuy flag deltas (only valid after trim)
REBUY_DELTAS = {
    "S2": (+0.15, -0.10),  # Reload after trim in danger zone
    "S3": (+0.20, -0.10),  # Strong reload inside confirmed trend
}

# Transition deltas (emergency exits - one-off shock pulses)
# These fire when state drops to S0 from a higher state
TRANSITION_DELTAS = {
    # from_state -> S0: (ΔA_trans, ΔE_trans)
    "S1": (-0.40, +0.40),  # Early uptrend failure
    "S2": (-0.35, +0.35),  # No man's land collapse
    "S3": (-0.50, +0.50),  # Confirmed trend nuked (biggest risk-off)
}


# =============================================================================
# Main Calculator Class
# =============================================================================

class RegimeAECalculator:
    """
    Calculates regime-driven Aggressiveness (A) and Exitness (E) scores.
    
    Architecture:
    1. Read regime driver states from lowcap_positions (status='regime_driver')
    2. For each driver and timeframe, compute ΔA/ΔE from state/flag tables
    3. Apply timeframe weights and driver weights
    4. Sum across all drivers to get regime-based A/E
    5. Add intent deltas (capped)
    6. Clamp to [0, 1]
    
    Usage:
        calculator = RegimeAECalculator()
        a, e = calculator.compute_ae_for_token(
            token_bucket="nano",
            exec_timeframe="1h",
            intent_delta_a=0.1,
            intent_delta_e=-0.05,
        )
    """
    
    def __init__(self, book_id: str = "onchain_crypto") -> None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY required")
        self.sb: Client = create_client(url, key)
        self.book_id = book_id
        
        # Cache for regime driver states (refreshed on each compute call)
        self._regime_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ts: Optional[datetime] = None
    
    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    
    def compute_ae_for_token(
        self,
        token_bucket: str,
        exec_timeframe: str = "1h",
        intent_delta_a: float = 0.0,
        intent_delta_e: float = 0.0,
        refresh_cache: bool = True,
    ) -> Tuple[float, float]:
        """
        Compute final A/E scores for a token.
        
        Args:
            token_bucket: Market cap bucket ('nano', 'small', 'mid', 'big')
            exec_timeframe: Trading timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
            intent_delta_a: Intent-based A adjustment (e.g., hi_buy = +0.1)
            intent_delta_e: Intent-based E adjustment (e.g., sell = +0.1)
            refresh_cache: If True, refresh regime driver states from DB
        
        Returns:
            Tuple of (A_final, E_final) clamped to [0, 1]
        """
        if refresh_cache or self._cache_ts is None:
            self._refresh_regime_cache()
        
        # Start from neutral baseline
        a_total = RegimeConstants.A_BASE
        e_total = RegimeConstants.E_BASE
        
        # Get timeframe multipliers for this exec timeframe
        tf_mults = EXEC_TF_MULTIPLIERS.get(exec_timeframe, EXEC_TF_MULTIPLIERS["1h"])
        
        # Determine which bucket driver to use
        bucket_driver = BUCKET_DRIVERS.get(token_bucket, "small")
        
        # Process each regime driver
        for driver_name in ["BTC", "ALT", bucket_driver, "BTC.d", "USDT.d"]:
            driver_weight = DRIVER_WEIGHTS.get(
                "BUCKET" if driver_name in BUCKET_DRIVERS.values() else driver_name,
                1.0
            )
            
            # Process each timeframe (macro/meso/micro)
            for regime_tf, tf_weight in TIMEFRAME_WEIGHTS.items():
                # Apply execution timeframe multiplier
                effective_tf_weight = tf_weight * tf_mults.get(regime_tf, 0.33)
                
                # Get delta for this driver/timeframe
                delta_a, delta_e = self._compute_driver_delta(driver_name, regime_tf)
                
                # Apply weights
                weighted_da = delta_a * driver_weight * effective_tf_weight
                weighted_de = delta_e * driver_weight * effective_tf_weight
                
                a_total += weighted_da
                e_total += weighted_de
        
        # Apply intent deltas (capped)
        capped_intent_a = max(-RegimeConstants.INTENT_CAP, 
                             min(RegimeConstants.INTENT_CAP, intent_delta_a))
        capped_intent_e = max(-RegimeConstants.INTENT_CAP, 
                             min(RegimeConstants.INTENT_CAP, intent_delta_e))
        
        a_total += capped_intent_a
        e_total += capped_intent_e
        
        # Clamp to [0, 1]
        a_final = max(RegimeConstants.A_MIN, min(RegimeConstants.A_MAX, a_total))
        e_final = max(RegimeConstants.E_MIN, min(RegimeConstants.E_MAX, e_total))
        
        return (a_final, e_final)
    
    def get_regime_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all regime driver states.
        
        Returns:
            Dict with driver -> {timeframe -> state/flags} mapping
        """
        self._refresh_regime_cache()
        
        summary = {}
        for driver in ["BTC", "ALT", "nano", "small", "mid", "big", "BTC.d", "USDT.d"]:
            driver_summary = {}
            for tf in ["1d", "1h", "1m"]:
                key = f"{driver}_{tf}"
                if key in self._regime_cache:
                    data = self._regime_cache[key]
                    driver_summary[tf] = {
                        "state": data.get("state", "unknown"),
                        "buy_flag": data.get("buy_signal", False) or data.get("buy_flag", False),
                        "trim_flag": data.get("trim_flag", False),
                        "emergency_exit": data.get("emergency_exit", False),
                    }
                else:
                    driver_summary[tf] = {"state": "no_data"}
            summary[driver] = driver_summary
        
        return summary
    
    def compute_ae_batch(
        self,
        tokens: List[Dict[str, Any]],
        exec_timeframe: str = "1h",
    ) -> Dict[str, Tuple[float, float]]:
        """
        Compute A/E for multiple tokens efficiently (single cache refresh).
        
        Args:
            tokens: List of token dicts with 'token_contract' and 'bucket' keys
            exec_timeframe: Trading timeframe
        
        Returns:
            Dict mapping token_contract -> (A, E)
        """
        self._refresh_regime_cache()
        
        results = {}
        for token in tokens:
            contract = token.get("token_contract", "")
            bucket = token.get("bucket", "small")
            intent_a = token.get("intent_delta_a", 0.0)
            intent_e = token.get("intent_delta_e", 0.0)
            
            a, e = self.compute_ae_for_token(
                token_bucket=bucket,
                exec_timeframe=exec_timeframe,
                intent_delta_a=intent_a,
                intent_delta_e=intent_e,
                refresh_cache=False,
            )
            results[contract] = (a, e)
        
        return results
    
    # -------------------------------------------------------------------------
    # Private methods
    # -------------------------------------------------------------------------
    
    def _refresh_regime_cache(self) -> None:
        """Refresh cached regime driver states from database."""
        self._regime_cache = {}
        
        # Fetch all regime_driver positions
        result = (
            self.sb.table("lowcap_positions")
            .select("token_ticker, timeframe, state, features")
            .eq("status", "regime_driver")
            .eq("book_id", self.book_id)
            .execute()
        )
        
        for row in result.data or []:
            driver = row.get("token_ticker", "")
            # Map position timeframe back to regime timeframe
            pos_tf = row.get("timeframe", "1h")
            regime_tf = self._position_tf_to_regime_tf(pos_tf)
            
            key = f"{driver}_{regime_tf}"
            
            # Extract uptrend state and flags from features
            features = row.get("features") or {}
            uptrend = features.get("uptrend_engine_v4") or {}
            
            self._regime_cache[key] = {
                "state": uptrend.get("state", row.get("state", "S0")),
                "buy_signal": uptrend.get("buy_signal", False),
                "buy_flag": uptrend.get("buy_flag", False),
                "trim_flag": uptrend.get("trim_flag", False),
                "first_dip_buy_flag": uptrend.get("first_dip_buy_flag", False),
                "emergency_exit": uptrend.get("emergency_exit", False),
                "reclaimed_ema333": uptrend.get("reclaimed_ema333", False),
                "scores": uptrend.get("scores") or {},
                "prev_state": uptrend.get("prev_state"),  # For transition detection
            }
        
        self._cache_ts = datetime.now(timezone.utc)
        logger.debug(f"Refreshed regime cache: {len(self._regime_cache)} entries")
    
    def _position_tf_to_regime_tf(self, pos_tf: str) -> str:
        """Map position timeframe to regime timeframe."""
        # Now that schema allows '1d', positions use regime timeframes directly
        # This mapping is mainly for backward compatibility with any existing 4h positions
        mapping = {
            "1d": "1d",  # Macro positions now use 1d directly
            "4h": "1d",  # Legacy: old 4h positions map to 1d regime (for backward compatibility)
            "1h": "1h",  # Meso
            "1m": "1m",  # Micro
        }
        return mapping.get(pos_tf, pos_tf)
    
    def _compute_driver_delta(
        self,
        driver: str,
        regime_tf: str,
    ) -> Tuple[float, float]:
        """
        Compute ΔA/ΔE for a single driver at a single timeframe.
        
        Args:
            driver: Driver name ('BTC', 'ALT', bucket name, 'BTC.d', 'USDT.d')
            regime_tf: Regime timeframe ('1d', '1h', '1m')
        
        Returns:
            Tuple of (ΔA, ΔE) before driver/tf weighting
        """
        key = f"{driver}_{regime_tf}"
        data = self._regime_cache.get(key, {})
        
        if not data:
            # No data for this driver/tf - return neutral
            return (0.0, 0.0)
        
        state = data.get("state", "S0")
        
        # Get base state delta
        delta_a, delta_e = STATE_DELTAS.get(state, (0.0, 0.0))
        
        # Check for flags and add flag deltas
        if data.get("buy_signal") or data.get("buy_flag"):
            flag_key = (state, "buy_signal" if state == "S1" else "buy_flag")
            if flag_key in FLAG_DELTAS:
                fa, fe = FLAG_DELTAS[flag_key]
                delta_a += fa
                delta_e += fe
        
        if data.get("first_dip_buy_flag"):
            flag_key = (state, "first_dip_buy_flag")
            if flag_key in FLAG_DELTAS:
                fa, fe = FLAG_DELTAS[flag_key]
                delta_a += fa
                delta_e += fe
        
        if data.get("trim_flag"):
            flag_key = (state, "trim_flag")
            if flag_key in FLAG_DELTAS:
                fa, fe = FLAG_DELTAS[flag_key]
                delta_a += fa
                delta_e += fe
        
        # Check for emergency transitions (S3->S0, S2->S0, S1->S0)
        # These are detected by prev_state being higher and current being S0
        prev_state = data.get("prev_state")
        if state == "S0" and prev_state in TRANSITION_DELTAS:
            ta, te = TRANSITION_DELTAS[prev_state]
            delta_a += ta
            delta_e += te
        
        return (delta_a, delta_e)


# =============================================================================
# CLI Entry Point
# =============================================================================

def main() -> None:
    """CLI entry point for testing regime A/E calculations."""
    import argparse
    
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="Regime A/E Calculator")
    parser.add_argument("--bucket", type=str, default="small", 
                       help="Token bucket (nano, small, mid, big)")
    parser.add_argument("--timeframe", type=str, default="1h",
                       help="Execution timeframe (1m, 5m, 15m, 1h, 4h, 1d)")
    parser.add_argument("--summary", action="store_true",
                       help="Show regime driver summary")
    args = parser.parse_args()
    
    calculator = RegimeAECalculator()
    
    if args.summary:
        summary = calculator.get_regime_summary()
        print("\nRegime Driver Summary:")
        print("-" * 60)
        for driver, tfs in summary.items():
            print(f"\n{driver}:")
            for tf, data in tfs.items():
                state = data.get("state", "?")
                flags = []
                if data.get("buy_flag"):
                    flags.append("BUY")
                if data.get("trim_flag"):
                    flags.append("TRIM")
                if data.get("emergency_exit"):
                    flags.append("EMERGENCY")
                flags_str = f" [{', '.join(flags)}]" if flags else ""
                print(f"  {tf}: {state}{flags_str}")
    else:
        a, e = calculator.compute_ae_for_token(
            token_bucket=args.bucket,
            exec_timeframe=args.timeframe,
        )
        print(f"\nRegime A/E for bucket={args.bucket}, exec_tf={args.timeframe}:")
        print(f"  A (Aggressiveness): {a:.3f}")
        print(f"  E (Exitness):       {e:.3f}")


if __name__ == "__main__":
    main()

