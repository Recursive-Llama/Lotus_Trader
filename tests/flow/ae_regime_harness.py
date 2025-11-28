"""
A/E Score & Regime Context Harness

Tests the A/E score calculation system including:
- Phase combinations (meso + macro)
- Cut pressure modulation
- 9-position curve (active positions)
- Per-token components (age, mcap, intent)
- Regime context extraction
- Integration with PM Core Tick
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
root_str = str(PROJECT_ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

# Load environment variables
load_dotenv()

from supabase import create_client, Client
from src.intelligence.lowcap_portfolio_manager.pm.levers import compute_levers, _compute_bucket_multiplier
from src.intelligence.lowcap_portfolio_manager.jobs.pm_core_tick import PMCoreTick
from src.intelligence.lowcap_portfolio_manager.pm.pattern_keys_v5 import extract_scope_from_context

LOGGER = None
try:
    from loguru import logger as LOGGER
except ImportError:
    import logging
    LOGGER = logging.getLogger(__name__)


class AERegimeHarness:
    """Harness for testing A/E score calculation and regime context."""
    
    def __init__(self) -> None:
        self.sb: Optional[Client] = None
        self.failures: List[str] = []
        
    def _connect_client(self) -> Client:
        """Connect to Supabase."""
        if self.sb:
            return self.sb
            
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        self.sb = create_client(url, key)
        return self.sb
    
    def run(self) -> None:
        """Run all A/E regime tests."""
        self._connect_client()
        
        tests = [
            ("Phase combinations (meso + macro)", self._test_phase_combinations),
            ("Cut pressure modulation", self._test_cut_pressure),
            ("9-position curve", self._test_9_position_curve),
            ("Age component", self._test_age_component),
            ("MCap component", self._test_mcap_component),
            ("Intent component", self._test_intent_component),
            ("Bucket ranking", self._test_bucket_ranking),
            ("Bucket multiplier (rank adjustments)", self._test_bucket_multiplier_rank),
            ("Bucket multiplier (slope adjustments)", self._test_bucket_multiplier_slope),
            ("Bucket multiplier (confidence threshold)", self._test_bucket_multiplier_confidence),
            ("Bucket multiplier (clamping)", self._test_bucket_multiplier_clamping),
            ("Bucket multiplier (integration with A/E)", self._test_bucket_multiplier_integration),
            ("Regime context extraction", self._test_regime_context_extraction),
            ("Integration with PM Core Tick", self._test_pm_core_tick_integration),
        ]
        
        LOGGER.info("=== A/E Score & Regime Context Harness ===")
        passed = 0
        failed = 0
        
        for name, test_func in tests:
            try:
                LOGGER.info(f"\n--- {name} ---")
                test_func()
                LOGGER.info(f"✅ {name} PASSED")
                passed += 1
            except Exception as e:
                LOGGER.error(f"❌ {name} FAILED: {e}")
                self.failures.append(f"{name}: {e}")
                failed += 1
        
        LOGGER.info(f"\n=== Summary: {passed} passed, {failed} failed ===")
        if self.failures:
            LOGGER.error("Failures:")
            for failure in self.failures:
                LOGGER.error(f"  - {failure}")
            raise RuntimeError(f"{failed} test(s) failed")
    
    def _test_phase_combinations(self) -> None:
        """Test all meso + macro phase combinations."""
        meso_phases = ["dip", "double-dip", "oh-shit", "recover", "good", "euphoria"]
        macro_phases = ["dip", "double-dip", "oh-shit", "recover", "good", "euphoria"]
        
        # Expected meso policy values
        meso_expected = {
            "dip": (0.2, 0.8),
            "double-dip": (0.4, 0.7),
            "oh-shit": (0.9, 0.8),
            "recover": (1.0, 0.5),
            "good": (0.5, 0.3),
            "euphoria": (0.4, 0.5),
        }
        
        # Expected macro multipliers
        macro_multipliers = {
            "dip": (0.6, 1.4),
            "double-dip": (0.8, 1.2),
            "oh-shit": (1.2, 0.8),
            "recover": (1.3, 1.0),
            "good": (1.1, 1.1),
            "euphoria": (1.0, 1.4),
        }
        
        for meso in meso_phases:
            for macro in macro_phases:
                a_pol, e_pol = meso_expected[meso]
                a_mac_mult, e_mac_mult = macro_multipliers[macro]
                
                # Calculate expected after macro
                a_mac_expected = a_pol * a_mac_mult
                e_mac_expected = e_pol * e_mac_mult
                
                # Run compute_levers with minimal features
                features = {"active_positions": 9}  # Neutral position count
                result = compute_levers(
                    phase_macro=macro,
                    phase_meso=meso,
                    cut_pressure=0.0,  # No cut pressure
                    features=features,
                )
                
                # Check that macro adjustment was applied (within tolerance for clamping)
                diag = result.get("diagnostics", {})
                components = diag.get("components", {})
                global_comp = components.get("global", {})
                a_mac_actual, e_mac_actual = global_comp.get("macro", (0, 0))
                
                # Allow small tolerance for rounding
                if abs(a_mac_actual - a_mac_expected) > 0.01:
                    raise AssertionError(
                        f"Meso={meso}, Macro={macro}: Expected A_mac={a_mac_expected:.3f}, got {a_mac_actual:.3f}"
                    )
                if abs(e_mac_actual - e_mac_expected) > 0.01:
                    raise AssertionError(
                        f"Meso={meso}, Macro={macro}: Expected E_mac={e_mac_expected:.3f}, got {e_mac_actual:.3f}"
                    )
                
                # Verify final values are clamped to [0, 1]
                a_final = result.get("A_value", 0)
                e_final = result.get("E_value", 0)
                if a_final < 0.0 or a_final > 1.0:
                    raise AssertionError(f"A_value {a_final} not in [0, 1]")
                if e_final < 0.0 or e_final > 1.0:
                    raise AssertionError(f"E_value {e_final} not in [0, 1]")
        
        LOGGER.info(f"Tested {len(meso_phases) * len(macro_phases)} phase combinations")
    
    def _test_cut_pressure(self) -> None:
        """Test cut pressure modulation."""
        # Base values (recover meso, no macro adjustment for simplicity)
        base_a = 1.0
        base_e = 0.5
        
        # Test cut_pressure = 0.0 (no pressure)
        result_0 = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=0.0,
            features={"active_positions": 9},
        )
        diag_0 = result_0.get("diagnostics", {})
        components_0 = diag_0.get("components", {})
        global_0 = components_0.get("global", {})
        a_cp_0, e_cp_0 = global_0.get("cut_pressure", (0, 0))
        
        # With cut_pressure=0.0, should be close to base (after macro)
        # Recover macro: A×1.3, E×1.0
        expected_a_0 = base_a * 1.3  # 1.3
        expected_e_0 = base_e * 1.0  # 0.5
        
        if abs(a_cp_0 - expected_a_0) > 0.01:
            raise AssertionError(f"cut_pressure=0.0: Expected A={expected_a_0:.3f}, got {a_cp_0:.3f}")
        if abs(e_cp_0 - expected_e_0) > 0.01:
            raise AssertionError(f"cut_pressure=0.0: Expected E={expected_e_0:.3f}, got {e_cp_0:.3f}")
        
        # Test cut_pressure = 0.5 (moderate)
        result_05 = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=0.5,
            features={"active_positions": 9},
        )
        diag_05 = result_05.get("diagnostics", {})
        components_05 = diag_05.get("components", {})
        global_05 = components_05.get("global", {})
        a_cp_05, e_cp_05 = global_05.get("cut_pressure", (0, 0))
        
        # With cut_pressure=0.5: A should decrease, E should increase
        # Base cut pressure: a_base = a * (1.0 - 0.33 * 0.5) = a * 0.835
        #                    e_base = e * (1.0 + 0.33 * 0.5) = e * 1.165
        expected_a_05 = expected_a_0 * 0.835
        expected_e_05 = expected_e_0 * 1.165
        
        if abs(a_cp_05 - expected_a_05) > 0.01:
            raise AssertionError(f"cut_pressure=0.5: Expected A={expected_a_05:.3f}, got {a_cp_05:.3f}")
        if abs(e_cp_05 - expected_e_05) > 0.01:
            raise AssertionError(f"cut_pressure=0.5: Expected E={expected_e_05:.3f}, got {e_cp_05:.3f}")
        
        # Verify A decreased and E increased
        if a_cp_05 >= a_cp_0:
            raise AssertionError(f"cut_pressure=0.5: A should decrease from {a_cp_0:.3f}, got {a_cp_05:.3f}")
        if e_cp_05 <= e_cp_0:
            raise AssertionError(f"cut_pressure=0.5: E should increase from {e_cp_0:.3f}, got {e_cp_05:.3f}")
        
        # Test cut_pressure = 1.0 (maximum)
        result_1 = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=1.0,
            features={"active_positions": 9},
        )
        diag_1 = result_1.get("diagnostics", {})
        components_1 = diag_1.get("components", {})
        global_1 = components_1.get("global", {})
        a_cp_1, e_cp_1 = global_1.get("cut_pressure", (0, 0))
        
        # With cut_pressure=1.0: A should be heavily reduced, E heavily increased
        # Base cut pressure: a_base = a * (1.0 - 0.33 * 1.0) = a * 0.67
        #                    e_base = e * (1.0 + 0.33 * 1.0) = e * 1.33
        expected_a_1 = expected_a_0 * 0.67
        expected_e_1 = expected_e_0 * 1.33
        
        if abs(a_cp_1 - expected_a_1) > 0.01:
            raise AssertionError(f"cut_pressure=1.0: Expected A={expected_a_1:.3f}, got {a_cp_1:.3f}")
        if abs(e_cp_1 - expected_e_1) > 0.01:
            raise AssertionError(f"cut_pressure=1.0: Expected E={expected_e_1:.3f}, got {e_cp_1:.3f}")
        
        LOGGER.info("Cut pressure modulation verified: 0.0, 0.5, 1.0")
    
    def _test_9_position_curve(self) -> None:
        """Test 9-position curve (active positions <9, =9, >9)."""
        # Test with active_positions = 5 (< 9)
        result_5 = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=0.0,  # No cut pressure to isolate position curve
            features={"active_positions": 5},
        )
        diag_5 = result_5.get("diagnostics", {})
        components_5 = diag_5.get("components", {})
        global_5 = components_5.get("global", {})
        a_cp_5, e_cp_5 = global_5.get("cut_pressure", (0, 0))
        
        # Test with active_positions = 9 (target)
        result_9 = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=0.0,
            features={"active_positions": 9},
        )
        diag_9 = result_9.get("diagnostics", {})
        components_9 = diag_9.get("components", {})
        global_9 = components_9.get("global", {})
        a_cp_9, e_cp_9 = global_9.get("cut_pressure", (0, 0))
        
        # Test with active_positions = 15 (> 9)
        result_15 = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=0.0,
            features={"active_positions": 15},
        )
        diag_15 = result_15.get("diagnostics", {})
        components_15 = diag_15.get("components", {})
        global_15 = components_15.get("global", {})
        a_cp_15, e_cp_15 = global_15.get("cut_pressure", (0, 0))
        
        # With 5 positions (< 9): Linear easing
        # deficit = 9 - 5 = 4
        # a_final = a_base * (1 + 0.05 * 4) = a_base * 1.2
        # e_final = e_base * (1 - 0.05 * 4) = e_base * 0.8
        # Base: A=1.3, E=0.5 (recover meso + recover macro)
        expected_a_5 = 1.3 * 1.2  # 1.56, clamped to 1.0
        expected_e_5 = 0.5 * 0.8  # 0.4
        
        if abs(a_cp_5 - 1.0) > 0.01:  # Clamped to 1.0
            raise AssertionError(f"active_positions=5: Expected A=1.0 (clamped), got {a_cp_5:.3f}")
        if abs(e_cp_5 - expected_e_5) > 0.01:
            raise AssertionError(f"active_positions=5: Expected E={expected_e_5:.3f}, got {e_cp_5:.3f}")
        
        # With 9 positions (= 9): No additional adjustment
        expected_a_9 = 1.3
        expected_e_9 = 0.5
        
        if abs(a_cp_9 - expected_a_9) > 0.01:
            raise AssertionError(f"active_positions=9: Expected A={expected_a_9:.3f}, got {a_cp_9:.3f}")
        if abs(e_cp_9 - expected_e_9) > 0.01:
            raise AssertionError(f"active_positions=9: Expected E={expected_e_9:.3f}, got {e_cp_9:.3f}")
        
        # With 15 positions (> 9): Exponential dampening
        # excess = 15 - 9 = 6
        # a_final = a_base * exp(-0.10 * 6) = a_base * 0.5488
        # e_final = e_base * exp(+0.10 * 6) = e_base * 1.8221
        import math
        expected_a_15 = 1.3 * math.exp(-0.10 * 6)
        expected_e_15 = 0.5 * math.exp(+0.10 * 6)
        
        if abs(a_cp_15 - expected_a_15) > 0.01:
            raise AssertionError(f"active_positions=15: Expected A={expected_a_15:.3f}, got {a_cp_15:.3f}")
        if abs(e_cp_15 - expected_e_15) > 0.01:
            raise AssertionError(f"active_positions=15: Expected E={expected_e_15:.3f}, got {e_cp_15:.3f}")
        
        # Verify ordering: A should decrease as positions increase, E should increase
        # Note: a_cp_5 is clamped to 1.0, so we can't compare it directly
        # Instead, verify that the unclamped value would be higher
        if a_cp_9 <= a_cp_15:
            raise AssertionError("A should be higher with 9 positions than 15")
        if e_cp_5 >= e_cp_9:
            raise AssertionError("E should be lower with 5 positions than 9")
        if e_cp_9 >= e_cp_15:
            raise AssertionError("E should be lower with 9 positions than 15")
        
        LOGGER.info("9-position curve verified: 5 (<9), 9 (=9), 15 (>9)")
    
    def _test_age_component(self) -> None:
        """Test age component boosts."""
        now = datetime.now(timezone.utc)
        
        # Test <6h
        age_3h = (now - timedelta(hours=3)).isoformat()
        result_3h = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=0.0,
            features={"active_positions": 9, "pair_created_at": age_3h},
        )
        diag_3h = result_3h.get("diagnostics", {})
        components_3h = diag_3h.get("components", {})
        per_token_3h = components_3h.get("per_token", {})
        a_age_3h, e_age_3h = per_token_3h.get("age", (1.0, 1.0))
        
        if abs(a_age_3h - 1.15) > 0.01:
            raise AssertionError(f"Age <6h: Expected A boost=1.15, got {a_age_3h:.3f}")
        
        # Test <12h
        age_9h = (now - timedelta(hours=9)).isoformat()
        result_9h = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=0.0,
            features={"active_positions": 9, "pair_created_at": age_9h},
        )
        diag_9h = result_9h.get("diagnostics", {})
        components_9h = diag_9h.get("components", {})
        per_token_9h = components_9h.get("per_token", {})
        a_age_9h, e_age_9h = per_token_9h.get("age", (1.0, 1.0))
        
        if abs(a_age_9h - 1.10) > 0.01:
            raise AssertionError(f"Age <12h: Expected A boost=1.10, got {a_age_9h:.3f}")
        
        # Test <72h
        age_48h = (now - timedelta(hours=48)).isoformat()
        result_48h = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=0.0,
            features={"active_positions": 9, "pair_created_at": age_48h},
        )
        diag_48h = result_48h.get("diagnostics", {})
        components_48h = diag_48h.get("components", {})
        per_token_48h = components_48h.get("per_token", {})
        a_age_48h, e_age_48h = per_token_48h.get("age", (1.0, 1.0))
        
        if abs(a_age_48h - 1.05) > 0.01:
            raise AssertionError(f"Age <72h: Expected A boost=1.05, got {a_age_48h:.3f}")
        
        # Test >72h
        age_100h = (now - timedelta(hours=100)).isoformat()
        result_100h = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=0.0,
            features={"active_positions": 9, "pair_created_at": age_100h},
        )
        diag_100h = result_100h.get("diagnostics", {})
        components_100h = diag_100h.get("components", {})
        per_token_100h = components_100h.get("per_token", {})
        a_age_100h, e_age_100h = per_token_100h.get("age", (1.0, 1.0))
        
        if abs(a_age_100h - 1.0) > 0.01:
            raise AssertionError(f"Age >72h: Expected A boost=1.0, got {a_age_100h:.3f}")
        
        LOGGER.info("Age component verified: <6h, <12h, <72h, >72h")
    
    def _test_mcap_component(self) -> None:
        """Test market cap component boosts."""
        # Test <$100k
        result_50k = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=0.0,
            features={"active_positions": 9, "market_cap": 50000},
        )
        diag_50k = result_50k.get("diagnostics", {})
        components_50k = diag_50k.get("components", {})
        per_token_50k = components_50k.get("per_token", {})
        a_mcap_50k, e_mcap_50k = per_token_50k.get("mcap", (1.0, 1.0))
        
        if abs(a_mcap_50k - 1.15) > 0.01:
            raise AssertionError(f"MCap <$100k: Expected A boost=1.15, got {a_mcap_50k:.3f}")
        
        # Test <$500k
        result_300k = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=0.0,
            features={"active_positions": 9, "market_cap": 300000},
        )
        diag_300k = result_300k.get("diagnostics", {})
        components_300k = diag_300k.get("components", {})
        per_token_300k = components_300k.get("per_token", {})
        a_mcap_300k, e_mcap_300k = per_token_300k.get("mcap", (1.0, 1.0))
        
        if abs(a_mcap_300k - 1.10) > 0.01:
            raise AssertionError(f"MCap <$500k: Expected A boost=1.10, got {a_mcap_300k:.3f}")
        
        # Test <$1m
        result_800k = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=0.0,
            features={"active_positions": 9, "market_cap": 800000},
        )
        diag_800k = result_800k.get("diagnostics", {})
        components_800k = diag_800k.get("components", {})
        per_token_800k = components_800k.get("per_token", {})
        a_mcap_800k, e_mcap_800k = per_token_800k.get("mcap", (1.0, 1.0))
        
        if abs(a_mcap_800k - 1.05) > 0.01:
            raise AssertionError(f"MCap <$1m: Expected A boost=1.05, got {a_mcap_800k:.3f}")
        
        # Test >$1m
        result_2m = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=0.0,
            features={"active_positions": 9, "market_cap": 2000000},
        )
        diag_2m = result_2m.get("diagnostics", {})
        components_2m = diag_2m.get("components", {})
        per_token_2m = components_2m.get("per_token", {})
        a_mcap_2m, e_mcap_2m = per_token_2m.get("mcap", (1.0, 1.0))
        
        if abs(a_mcap_2m - 1.0) > 0.01:
            raise AssertionError(f"MCap >$1m: Expected A boost=1.0, got {a_mcap_2m:.3f}")
        
        LOGGER.info("MCap component verified: <$100k, <$500k, <$1m, >$1m")
    
    def _test_intent_component(self) -> None:
        """Test intent component deltas."""
        # Test hi_buy intent
        result_hi_buy = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=0.0,
            features={
                "active_positions": 9,
                "intent_metrics": {"hi_buy": 1.0},
            },
        )
        diag_hi_buy = result_hi_buy.get("diagnostics", {})
        dA_hi_buy = diag_hi_buy.get("dA", 0.0)
        
        # hi_buy: +0.25 to A, -0.10 to E
        if abs(dA_hi_buy - 0.25) > 0.01:
            raise AssertionError(f"hi_buy intent: Expected dA=0.25, got {dA_hi_buy:.3f}")
        
        # Test sell intent
        result_sell = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=0.0,
            features={
                "active_positions": 9,
                "intent_metrics": {"sell": 1.0},
            },
        )
        diag_sell = result_sell.get("diagnostics", {})
        dA_sell = diag_sell.get("dA", 0.0)
        dE_sell = diag_sell.get("dE", 0.0)
        
        # sell: -0.25 to A, +0.35 to E
        if abs(dA_sell - (-0.25)) > 0.01:
            raise AssertionError(f"sell intent: Expected dA=-0.25, got {dA_sell:.3f}")
        if abs(dE_sell - 0.35) > 0.01:
            raise AssertionError(f"sell intent: Expected dE=0.35, got {dE_sell:.3f}")
        
        # Test mock intent (strongest negative)
        result_mock = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=0.0,
            features={
                "active_positions": 9,
                "intent_metrics": {"mock": 1.0},
            },
        )
        diag_mock = result_mock.get("diagnostics", {})
        dA_mock = diag_mock.get("dA", 0.0)
        dE_mock = diag_mock.get("dE", 0.0)
        
        # mock: -0.30 to A, +0.50 to E (but clamped to ±0.4)
        if abs(dA_mock - (-0.30)) > 0.01:
            raise AssertionError(f"mock intent: Expected dA=-0.30, got {dA_mock:.3f}")
        # dE is clamped to ±0.4, so 0.50 becomes 0.40
        if abs(dE_mock - 0.40) > 0.01:
            raise AssertionError(f"mock intent: Expected dE=0.40 (clamped from 0.50), got {dE_mock:.3f}")
        
        LOGGER.info("Intent component verified: hi_buy, sell, mock")
    
    def _test_bucket_ranking(self) -> None:
        """Test bucket ranking by meso score."""
        from src.intelligence.lowcap_portfolio_manager.regime.bucket_context import fetch_bucket_phase_snapshot
        
        # Create test bucket phases with different scores
        now = datetime.now(timezone.utc)
        test_buckets = [
            {"bucket": "micro", "horizon": "meso", "phase": "Good", "score": 0.8, "slope": 0.1, "confidence": 0.7, "population_count": 50, "ts": now.isoformat()},
            {"bucket": "nano", "horizon": "meso", "phase": "Recover", "score": 0.6, "slope": 0.05, "confidence": 0.6, "population_count": 20, "ts": now.isoformat()},
            {"bucket": "mid", "horizon": "meso", "phase": "Dip", "score": 0.4, "slope": -0.05, "confidence": 0.5, "population_count": 30, "ts": now.isoformat()},
        ]
        
        try:
            # Insert test data
            for bucket_data in test_buckets:
                self.sb.table("phase_state_bucket").insert(bucket_data).execute()
            
            # Fetch bucket snapshot
            snapshot = fetch_bucket_phase_snapshot(self.sb, horizon="meso")
            bucket_rank = snapshot.get("bucket_rank", [])
            
            # Verify ranking: micro (0.8) > nano (0.6) > mid (0.4)
            if len(bucket_rank) < 3:
                raise AssertionError(f"Expected 3 buckets in rank, got {len(bucket_rank)}")
            if bucket_rank[0] != "micro":
                raise AssertionError(f"Expected 'micro' as #1 (score=0.8), got '{bucket_rank[0]}'")
            if bucket_rank[1] != "nano":
                raise AssertionError(f"Expected 'nano' as #2 (score=0.6), got '{bucket_rank[1]}'")
            if bucket_rank[2] != "mid":
                raise AssertionError(f"Expected 'mid' as #3 (score=0.4), got '{bucket_rank[2]}'")
            
            LOGGER.info("Bucket ranking verified: micro > nano > mid (by meso score)")
        finally:
            # Cleanup
            try:
                for bucket_data in test_buckets:
                    self.sb.table("phase_state_bucket").delete().eq("bucket", bucket_data["bucket"]).eq("horizon", bucket_data["horizon"]).eq("ts", bucket_data["ts"]).execute()
            except Exception as e:
                LOGGER.warning(f"Failed to cleanup test bucket phases: {e}")
    
    def _test_bucket_multiplier_rank(self) -> None:
        """Test bucket multiplier based on rank position."""
        # Default config from spec
        bucket_config = {
            "rank_adjustments": {
                "1": 0.12,  # #1 bucket gets +0.12
                "2": 0.06,  # #2 bucket gets +0.06
                "3": 0.02,  # #3 bucket gets +0.02
                "4": -0.02, # #4 bucket gets -0.02
            },
            "slope_weight": 0.4,
            "min_confidence": 0.4,
            "min_multiplier": 0.7,
            "max_multiplier": 1.3,
        }
        
        # Test #1 rank (micro)
        bucket_context_1 = {
            "bucket_phases": {
                "micro": {"score": 0.8, "slope": 0.0, "confidence": 0.7},
            },
            "bucket_rank": ["micro", "nano", "mid"],
        }
        multiplier_1, diag_1 = _compute_bucket_multiplier(
            position_bucket="micro",
            bucket_context=bucket_context_1,
            bucket_config=bucket_config,
        )
        
        # Expected: 1.0 + 0.12 (rank #1) = 1.12
        if abs(multiplier_1 - 1.12) > 0.01:
            raise AssertionError(f"Rank #1: Expected multiplier=1.12, got {multiplier_1:.3f}")
        if diag_1.get("rank") != 1:
            raise AssertionError(f"Rank #1: Expected rank=1, got {diag_1.get('rank')}")
        
        # Test #2 rank (nano)
        bucket_context_2 = {
            "bucket_phases": {
                "nano": {"score": 0.6, "slope": 0.0, "confidence": 0.7},
            },
            "bucket_rank": ["micro", "nano", "mid"],
        }
        multiplier_2, diag_2 = _compute_bucket_multiplier(
            position_bucket="nano",
            bucket_context=bucket_context_2,
            bucket_config=bucket_config,
        )
        
        # Expected: 1.0 + 0.06 (rank #2) = 1.06
        if abs(multiplier_2 - 1.06) > 0.01:
            raise AssertionError(f"Rank #2: Expected multiplier=1.06, got {multiplier_2:.3f}")
        if diag_2.get("rank") != 2:
            raise AssertionError(f"Rank #2: Expected rank=2, got {diag_2.get('rank')}")
        
        # Test #4 rank (big) - negative adjustment
        bucket_context_4 = {
            "bucket_phases": {
                "big": {"score": 0.3, "slope": 0.0, "confidence": 0.7},
            },
            "bucket_rank": ["micro", "nano", "mid", "big"],
        }
        multiplier_4, diag_4 = _compute_bucket_multiplier(
            position_bucket="big",
            bucket_context=bucket_context_4,
            bucket_config=bucket_config,
        )
        
        # Expected: 1.0 + (-0.02) (rank #4) = 0.98
        if abs(multiplier_4 - 0.98) > 0.01:
            raise AssertionError(f"Rank #4: Expected multiplier=0.98, got {multiplier_4:.3f}")
        if diag_4.get("rank") != 4:
            raise AssertionError(f"Rank #4: Expected rank=4, got {diag_4.get('rank')}")
        
        LOGGER.info("Bucket multiplier rank adjustments verified: #1 (+0.12), #2 (+0.06), #4 (-0.02)")
    
    def _test_bucket_multiplier_slope(self) -> None:
        """Test bucket multiplier with slope adjustments."""
        bucket_config = {
            "rank_adjustments": {"1": 0.12},
            "slope_weight": 0.4,  # slope_weight = 0.4
            "min_confidence": 0.4,
            "min_multiplier": 0.7,
            "max_multiplier": 1.3,
        }
        
        # Test positive slope
        bucket_context_pos = {
            "bucket_phases": {
                "micro": {"score": 0.8, "slope": 0.2, "confidence": 0.7},  # slope = 0.2
            },
            "bucket_rank": ["micro"],
        }
        multiplier_pos, _ = _compute_bucket_multiplier(
            position_bucket="micro",
            bucket_context=bucket_context_pos,
            bucket_config=bucket_config,
        )
        
        # Expected: 1.0 + 0.12 (rank #1) + 0.4 * 0.2 (slope) = 1.0 + 0.12 + 0.08 = 1.20
        if abs(multiplier_pos - 1.20) > 0.01:
            raise AssertionError(f"Positive slope: Expected multiplier=1.20, got {multiplier_pos:.3f}")
        
        # Test negative slope
        bucket_context_neg = {
            "bucket_phases": {
                "micro": {"score": 0.8, "slope": -0.15, "confidence": 0.7},  # slope = -0.15
            },
            "bucket_rank": ["micro"],
        }
        multiplier_neg, _ = _compute_bucket_multiplier(
            position_bucket="micro",
            bucket_context=bucket_context_neg,
            bucket_config=bucket_config,
        )
        
        # Expected: 1.0 + 0.12 (rank #1) + 0.4 * (-0.15) (slope) = 1.0 + 0.12 - 0.06 = 1.06
        if abs(multiplier_neg - 1.06) > 0.01:
            raise AssertionError(f"Negative slope: Expected multiplier=1.06, got {multiplier_neg:.3f}")
        
        LOGGER.info("Bucket multiplier slope adjustments verified: +0.2 slope (+0.08), -0.15 slope (-0.06)")
    
    def _test_bucket_multiplier_confidence(self) -> None:
        """Test bucket multiplier confidence threshold."""
        bucket_config = {
            "rank_adjustments": {"1": 0.12},
            "slope_weight": 0.4,
            "min_confidence": 0.4,  # Requires confidence >= 0.4
            "min_multiplier": 0.7,
            "max_multiplier": 1.3,
        }
        
        # Test confidence above threshold
        bucket_context_high = {
            "bucket_phases": {
                "micro": {"score": 0.8, "slope": 0.0, "confidence": 0.7},  # confidence = 0.7 > 0.4
            },
            "bucket_rank": ["micro"],
        }
        multiplier_high, _ = _compute_bucket_multiplier(
            position_bucket="micro",
            bucket_context=bucket_context_high,
            bucket_config=bucket_config,
        )
        
        # Should apply rank adjustment: 1.0 + 0.12 = 1.12
        if abs(multiplier_high - 1.12) > 0.01:
            raise AssertionError(f"High confidence: Expected multiplier=1.12, got {multiplier_high:.3f}")
        
        # Test confidence below threshold
        bucket_context_low = {
            "bucket_phases": {
                "micro": {"score": 0.8, "slope": 0.0, "confidence": 0.3},  # confidence = 0.3 < 0.4
            },
            "bucket_rank": ["micro"],
        }
        multiplier_low, _ = _compute_bucket_multiplier(
            position_bucket="micro",
            bucket_context=bucket_context_low,
            bucket_config=bucket_config,
        )
        
        # Should NOT apply rank adjustment (confidence too low): 1.0
        if abs(multiplier_low - 1.0) > 0.01:
            raise AssertionError(f"Low confidence: Expected multiplier=1.0 (no adjustment), got {multiplier_low:.3f}")
        
        LOGGER.info("Bucket multiplier confidence threshold verified: >=0.4 applies adjustments, <0.4 returns 1.0")
    
    def _test_bucket_multiplier_clamping(self) -> None:
        """Test bucket multiplier clamping to [min_mult, max_mult]."""
        bucket_config = {
            "rank_adjustments": {"1": 0.5},  # Large adjustment
            "slope_weight": 0.4,
            "min_confidence": 0.4,
            "min_multiplier": 0.7,  # Clamp to 0.7 minimum
            "max_multiplier": 1.3,  # Clamp to 1.3 maximum
        }
        
        # Test exceeding max_multiplier
        bucket_context_max = {
            "bucket_phases": {
                "micro": {"score": 0.8, "slope": 0.5, "confidence": 0.7},  # Large positive slope
            },
            "bucket_rank": ["micro"],
        }
        multiplier_max, _ = _compute_bucket_multiplier(
            position_bucket="micro",
            bucket_context=bucket_context_max,
            bucket_config=bucket_config,
        )
        
        # Expected: 1.0 + 0.5 (rank) + 0.4 * 0.5 (slope) = 1.7, clamped to 1.3
        if abs(multiplier_max - 1.3) > 0.01:
            raise AssertionError(f"Max clamp: Expected multiplier=1.3 (clamped), got {multiplier_max:.3f}")
        
        # Test below min_multiplier (would need negative adjustments)
        # Note: large is rank #5 in the list, not #6 (0-indexed: 0,1,2,3,4,5)
        bucket_config_min = {
            "rank_adjustments": {"5": -0.5},  # Large negative adjustment for rank #5
            "slope_weight": 0.4,
            "min_confidence": 0.4,
            "min_multiplier": 0.7,
            "max_multiplier": 1.3,
        }
        bucket_context_min = {
            "bucket_phases": {
                "large": {"score": 0.2, "slope": -0.5, "confidence": 0.7},  # Large negative slope
            },
            "bucket_rank": ["micro", "nano", "mid", "big", "large"],  # large is rank #5 (1-indexed)
        }
        multiplier_min, diag_min = _compute_bucket_multiplier(
            position_bucket="large",
            bucket_context=bucket_context_min,
            bucket_config=bucket_config_min,
        )
        
        # Expected: 1.0 + (-0.5) (rank #5) + 0.4 * (-0.5) (slope) = 1.0 - 0.5 - 0.2 = 0.3, clamped to 0.7
        if abs(multiplier_min - 0.7) > 0.01:
            raise AssertionError(f"Min clamp: Expected multiplier=0.7 (clamped), got {multiplier_min:.3f}. Rank={diag_min.get('rank')}")
        
        LOGGER.info("Bucket multiplier clamping verified: max=1.3, min=0.7")
    
    def _test_bucket_multiplier_integration(self) -> None:
        """Test bucket multiplier integration with A/E calculation."""
        # Create bucket context with micro as #1
        bucket_context = {
            "bucket_phases": {
                "micro": {"score": 0.8, "slope": 0.1, "confidence": 0.7},
            },
            "bucket_rank": ["micro", "nano", "mid"],
        }
        
        bucket_config = {
            "rank_adjustments": {"1": 0.12},
            "slope_weight": 0.4,
            "min_confidence": 0.4,
            "min_multiplier": 0.7,
            "max_multiplier": 1.3,
        }
        
        # Calculate A/E with micro bucket (rank #1)
        result = compute_levers(
            phase_macro="recover",
            phase_meso="recover",
            cut_pressure=0.0,
            features={"active_positions": 9},
            bucket_context=bucket_context,
            position_bucket="micro",
            bucket_config=bucket_config,
        )
        
        # Verify bucket multiplier is applied
        diag = result.get("diagnostics", {})
        components = diag.get("components", {})
        boosts = components.get("boosts", {})
        bucket_mult = boosts.get("bucket_multiplier", 1.0)
        
        # Expected: 1.0 + 0.12 (rank #1) + 0.4 * 0.1 (slope) = 1.16
        if abs(bucket_mult - 1.16) > 0.01:
            raise AssertionError(f"Bucket multiplier: Expected 1.16, got {bucket_mult:.3f}")
        
        # Verify A/E are affected by bucket multiplier
        a_final = result.get("A_value", 0)
        e_final = result.get("E_value", 0)
        
        # A should be boosted by bucket_multiplier
        # E should be divided by bucket_multiplier (inverse relationship)
        # Base: A=1.3, E=0.5 (recover meso + recover macro)
        # With bucket_mult=1.16: A = 1.3 * 1.16 = 1.508 (clamped to 1.0)
        #                        E = 0.5 / max(1.16, 0.2) = 0.5 / 1.16 = 0.431
        # But also affected by e_boost (age * mcap), which defaults to 1.0 if no age/mcap
        # So: e_base = 0.5, e_boost = 1.0, e_final = (0.5 * 1.0) / 1.16 = 0.431
        
        if a_final != 1.0:  # Clamped to 1.0
            raise AssertionError(f"A_value should be clamped to 1.0, got {a_final:.3f}")
        # Allow some tolerance since there might be other components
        if e_final > 0.5 or e_final < 0.4:
            raise AssertionError(f"E_value: Expected ~0.431 (0.5/1.16), got {e_final:.3f}. Bucket multiplier should reduce E.")
        
        LOGGER.info("Bucket multiplier integration verified: A boosted, E divided by multiplier")
    
    def _test_regime_context_extraction(self) -> None:
        """Test regime context extraction from phase_state table."""
        # Insert test phase states
        now = datetime.now(timezone.utc)
        test_phases = [
            {"token": "PORTFOLIO", "horizon": "macro", "phase": "Recover", "score": 0.7, "ts": now.isoformat()},
            {"token": "PORTFOLIO", "horizon": "meso", "phase": "Good", "score": 0.6, "ts": now.isoformat()},
            {"token": "PORTFOLIO", "horizon": "micro", "phase": "Dip", "score": 0.4, "ts": now.isoformat()},
        ]
        
        try:
            # Insert test data
            for phase_data in test_phases:
                self.sb.table("phase_state").insert(phase_data).execute()
            
            # Test _get_regime_context
            pm = PMCoreTick(timeframe="1h")
            regime_context = pm._get_regime_context()
            
            # Verify extraction
            macro = regime_context.get("macro", {})
            meso = regime_context.get("meso", {})
            micro = regime_context.get("micro", {})
            
            if macro.get("phase") != "Recover":
                raise AssertionError(f"Expected macro phase='Recover', got '{macro.get('phase')}'")
            if meso.get("phase") != "Good":
                raise AssertionError(f"Expected meso phase='Good', got '{meso.get('phase')}'")
            if micro.get("phase") != "Dip":
                raise AssertionError(f"Expected micro phase='Dip', got '{micro.get('phase')}'")
            
            # Test extract_scope_from_context
            action_context = {
                "timeframe": "1h",
                "a_final": 0.6,
                "e_final": 0.4,
            }
            scope = extract_scope_from_context(
                action_context=action_context,
                regime_context=regime_context,
                position_bucket="micro",
            )
            
            # Verify scope includes regime phases
            if scope.get("macro_phase") != "Recover":
                raise AssertionError(f"Expected scope.macro_phase='Recover', got '{scope.get('macro_phase')}'")
            if scope.get("meso_phase") != "Good":
                raise AssertionError(f"Expected scope.meso_phase='Good', got '{scope.get('meso_phase')}'")
            if scope.get("micro_phase") != "Dip":
                raise AssertionError(f"Expected scope.micro_phase='Dip', got '{scope.get('micro_phase')}'")
            
            # Verify A_mode derived from a_final
            if scope.get("A_mode") != "normal":  # 0.6 is in [0.33, 0.67)
                raise AssertionError(f"Expected A_mode='normal' for a_final=0.6, got '{scope.get('A_mode')}'")
            
            LOGGER.info("Regime context extraction verified")
        finally:
            # Cleanup: delete test phase states
            try:
                for phase_data in test_phases:
                    self.sb.table("phase_state").delete().eq("token", "PORTFOLIO").eq("horizon", phase_data["horizon"]).eq("ts", phase_data["ts"]).execute()
            except Exception as e:
                LOGGER.warning(f"Failed to cleanup test phase states: {e}")
    
    def _test_pm_core_tick_integration(self) -> None:
        """Test A/E scores in PM Core Tick integration."""
        # This test verifies that A/E scores are correctly calculated and logged
        # in pm_action strands when PM Core Tick runs.
        # For a full integration test, we'd need a real position, but we can at least
        # verify that compute_levers is called correctly with regime context.
        
        pm = PMCoreTick(timeframe="1h")
        regime_context = pm._get_regime_context()
        
        # Extract phases
        phase_macro = (regime_context.get("macro") or {}).get("phase") or "Unknown"
        phase_meso = (regime_context.get("meso") or {}).get("phase") or "Unknown"
        
        # Calculate A/E with minimal features
        features = {"active_positions": 9}
        result = compute_levers(
            phase_macro=phase_macro,
            phase_meso=phase_meso,
            cut_pressure=0.0,
            features=features,
        )
        
        # Verify A/E values are valid
        a_value = result.get("A_value", 0)
        e_value = result.get("E_value", 0)
        
        if a_value < 0.0 or a_value > 1.0:
            raise AssertionError(f"A_value {a_value} not in [0, 1]")
        if e_value < 0.0 or e_value > 1.0:
            raise AssertionError(f"E_value {e_value} not in [0, 1]")
        
        # Verify position_size_frac is calculated
        position_size_frac = result.get("position_size_frac", 0)
        if position_size_frac < 0.1 or position_size_frac > 0.6:
            raise AssertionError(f"position_size_frac {position_size_frac} not in [0.1, 0.6]")
        
        LOGGER.info(f"PM Core Tick integration verified: A={a_value:.3f}, E={e_value:.3f}, size_frac={position_size_frac:.3f}")


if __name__ == "__main__":
    harness = AERegimeHarness()
    try:
        harness.run()
        print("\n✅ All A/E regime tests passed!")
    except Exception as e:
        print(f"\n❌ Harness failed: {e}")
        sys.exit(1)

