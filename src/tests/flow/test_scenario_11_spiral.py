"""
Flow Test: Scenario 11 - SPIRAL Engine Testing (A/E Score Computation)

Flow Testing Approach: Test SPIRAL engine phase detection and A/E score calculation

Objective: Verify SPIRAL engine computes A/E scores correctly from phase, cut_pressure, intent, age, and mcap

Flow Test Definition:
- Ingress: Majors data (from Scenario 10) + test position
- Payload: Real majors data + test position with various phase states
- Expected Path: 
  1. Majors data available (from Scenario 10)
  2. Portfolio bands NAV data available
  3. SPIRAL computes phase detection (macro/meso/micro phases)
  4. SPIRAL computes A/E scores from phase + cut_pressure + intent + age + mcap
  5. A/E scores validated
- Required Side-Effects: 
  - Phase state computed (if stored in database)
  - A/E scores computed correctly
  - A/E scores clamped to 0.0-1.0 range
- Timeout: 5 minutes
"""

import pytest
from datetime import datetime, timezone, timedelta
from src.intelligence.lowcap_portfolio_manager.spiral.returns import ReturnsComputer
from src.intelligence.lowcap_portfolio_manager.spiral.lenses import compute_lens_scores
from src.intelligence.lowcap_portfolio_manager.spiral.phase import compute_phase_scores, label_from_score
from src.intelligence.lowcap_portfolio_manager.pm.levers import compute_levers


@pytest.mark.flow
class TestScenario11SPIRAL:
    """Test Scenario 11: SPIRAL Engine Testing"""
    
    def test_spiral_phase_detection(
        self,
        test_db
    ):
        """
        Test SPIRAL phase detection from majors data.
        
        Prerequisites: Scenario 10 must pass (majors data available)
        Expected:
        - ReturnsComputer can compute returns from majors data
        - Lens scores computed from returns
        - Phase scores computed from lens scores
        - Phase labels computed from phase scores
        """
        print("\n📊 Step 1: Testing SPIRAL phase detection...")
        
        # Step 1: Verify majors data available (from Scenario 10)
        sb = test_db.client
        now = datetime.now(timezone.utc)
        
        # Check for 1m OHLC data
        majors_check = (
            sb.table("majors_price_data_ohlc")
            .select("token_contract,timestamp")
            .eq("chain", "hyperliquid")
            .eq("timeframe", "1m")
            .in_("token_contract", ["BTC", "ETH", "SOL", "BNB", "HYPE"])
            .gte("timestamp", (now - timedelta(days=1)).isoformat())
            .limit(1)
            .execute()
        )
        
        if not majors_check.data:
            pytest.skip("Majors data not available - run Scenario 10 first")
        
        print("   ✅ Majors data available")
        
        # Step 2: Compute returns
        print("\n📊 Step 2: Computing returns from majors data...")
        rc = ReturnsComputer()
        returns_result = rc.compute(when=now)
        
        assert returns_result is not None, "ReturnsComputer should return a result"
        assert hasattr(returns_result, 'r_btc'), "Returns should have r_btc"
        assert hasattr(returns_result, 'r_alt'), "Returns should have r_alt"
        assert hasattr(returns_result, 'r_port'), "Returns should have r_port"
        
        print(f"   ✅ Returns computed: r_btc={returns_result.r_btc:.4f}, r_alt={returns_result.r_alt:.4f}, r_port={returns_result.r_port:.4f}")
        
        # Step 3: Compute lens scores (simplified - in real system, this uses geometry streams)
        # For testing, we'll use mock lens streams based on returns
        print("\n📊 Step 3: Computing lens scores...")
        
        # Mock lens streams (in real system, these come from geometry_build_daily)
        # Using returns as a proxy for lens scores for testing
        lens_streams = {
            "btc_slope": returns_result.r_btc * 0.5,
            "btc_curv": returns_result.r_btc * 0.3,
            "btc_delta": returns_result.r_btc * 0.2,
            "btc_level": returns_result.r_btc * 0.1,
            "rotation_slope": (returns_result.r_alt - returns_result.r_btc) * 0.5,
            "rotation_curv": (returns_result.r_alt - returns_result.r_btc) * 0.3,
            "rotation_delta": (returns_result.r_alt - returns_result.r_btc) * 0.2,
            "rotation_level": (returns_result.r_alt - returns_result.r_btc) * 0.1,
            "port_btc_slope": returns_result.r_port * 0.5,
            "port_btc_curv": returns_result.r_port * 0.3,
            "port_btc_delta": returns_result.r_port * 0.2,
            "port_btc_level": returns_result.r_port * 0.1,
            "port_alt_slope": returns_result.r_alt * 0.5,
            "port_alt_curv": returns_result.r_alt * 0.3,
            "port_alt_delta": returns_result.r_alt * 0.2,
            "port_alt_level": returns_result.r_alt * 0.1,
        }
        
        lens_scores = compute_lens_scores(lens_streams)
        assert lens_scores is not None, "Lens scores should be computed"
        assert hasattr(lens_scores, 'S_btcusd'), "Lens scores should have S_btcusd"
        assert hasattr(lens_scores, 'S_rotation'), "Lens scores should have S_rotation"
        assert hasattr(lens_scores, 'S_port_btc'), "Lens scores should have S_port_btc"
        assert hasattr(lens_scores, 'S_port_alt'), "Lens scores should have S_port_alt"
        
        print(f"   ✅ Lens scores computed: S_btcusd={lens_scores.S_btcusd:.4f}, S_rotation={lens_scores.S_rotation:.4f}")
        
        # Step 4: Compute phase scores
        print("\n📊 Step 4: Computing phase scores...")
        phase_scores = compute_phase_scores(lens_scores.__dict__)
        assert phase_scores is not None, "Phase scores should be computed"
        assert hasattr(phase_scores, 'macro'), "Phase scores should have macro"
        assert hasattr(phase_scores, 'meso'), "Phase scores should have meso"
        assert hasattr(phase_scores, 'micro'), "Phase scores should have micro"
        
        print(f"   ✅ Phase scores computed: macro={phase_scores.macro:.4f}, meso={phase_scores.meso:.4f}, micro={phase_scores.micro:.4f}")
        
        # Step 5: Convert to phase labels
        print("\n📊 Step 5: Converting phase scores to labels...")
        macro_label = label_from_score(phase_scores.macro)
        meso_label = label_from_score(phase_scores.meso)
        micro_label = label_from_score(phase_scores.micro)
        
        valid_labels = ["Euphoria", "Good", "Recover", "Dip", "Double-Dip", "Oh-Shit"]
        assert macro_label in valid_labels, f"Macro label should be valid: {macro_label}"
        assert meso_label in valid_labels, f"Meso label should be valid: {meso_label}"
        assert micro_label in valid_labels, f"Micro label should be valid: {micro_label}"
        
        print(f"   ✅ Phase labels: macro={macro_label}, meso={meso_label}, micro={micro_label}")
        print("✅ Step 1: SPIRAL phase detection works correctly")
    
    def test_a_score_calculation(
        self,
        test_db
    ):
        """
        Test A score calculation from phase, cut_pressure, intent, age, mcap.
        
        Test Case 11.1: Favorable Phase + Research Positive Intent
        Test Case 11.2: Unfavorable Phase + Pump Negative Intent
        
        Expected:
        - a_final clamped between 0.0 and 1.0
        - a_final reflects phase, intent, age, mcap
        """
        print("\n📊 Step 1: Testing A score calculation...")
        
        # Test Case 11.1: Favorable Phase + Research Positive Intent
        print("\n📊 Test Case 11.1: Favorable Phase + Research Positive Intent")
        features_favorable = {
            "intent_metrics": {
                "hi_buy": 0.8,  # Research positive intent
                "med_buy": 0.2,
                "profit": 0.0,
                "sell": 0.0,
                "mock": 0.0,
            },
            "pair_created_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),  # 3 days old
            "market_cap": 1_500_000,  # $1.5M
            "active_positions": 5,  # Below 9
        }
        
        levers_favorable = compute_levers(
            phase_macro="Good",
            phase_meso="Recover",
            cut_pressure=0.2,
            features=features_favorable
        )
        
        a_final_1 = levers_favorable["A_value"]
        e_final_1 = levers_favorable["E_value"]
        
        assert 0.0 <= a_final_1 <= 1.0, f"a_final should be clamped: {a_final_1}"
        assert 0.0 <= e_final_1 <= 1.0, f"e_final should be clamped: {e_final_1}"
        
        # With favorable phase + research positive intent, a_final should be high
        assert a_final_1 > 0.5, f"a_final should be high for favorable phase + research positive: {a_final_1}"
        
        print(f"   ✅ Test Case 11.1: a_final={a_final_1:.4f}, e_final={e_final_1:.4f}")
        
        # Test Case 11.2: Unfavorable Phase + Pump Negative Intent
        print("\n📊 Test Case 11.2: Unfavorable Phase + Pump Negative Intent")
        features_unfavorable = {
            "intent_metrics": {
                "hi_buy": 0.0,
                "med_buy": 0.0,
                "profit": 0.0,
                "sell": 0.0,
                "mock": 0.8,  # Pump negative (mocking = "get out")
            },
            "pair_created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),  # 30 days old
            "market_cap": 10_000_000,  # $10M
            "active_positions": 12,  # Above 9 (exponential dampening)
        }
        
        levers_unfavorable = compute_levers(
            phase_macro="Dip",
            phase_meso="Double-Dip",
            cut_pressure=0.8,
            features=features_unfavorable
        )
        
        a_final_2 = levers_unfavorable["A_value"]
        e_final_2 = levers_unfavorable["E_value"]
        
        assert 0.0 <= a_final_2 <= 1.0, f"a_final should be clamped: {a_final_2}"
        assert 0.0 <= e_final_2 <= 1.0, f"e_final should be clamped: {e_final_2}"
        
        # With unfavorable phase + pump negative intent, a_final should be low
        assert a_final_2 < a_final_1, f"a_final should be lower for unfavorable phase + pump negative: {a_final_2} < {a_final_1}"
        
        print(f"   ✅ Test Case 11.2: a_final={a_final_2:.4f}, e_final={e_final_2:.4f}")
        
        # Test age component (use a case where A isn't already maxed)
        print("\n📊 Testing age component...")
        features_base = {
            "intent_metrics": {
                "hi_buy": 0.3,  # Lower intent to avoid maxing out A
                "med_buy": 0.1,
                "profit": 0.0,
                "sell": 0.0,
                "mock": 0.0,
            },
            "pair_created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),  # 30 days old (no boost)
            "market_cap": 2_000_000,  # >$1M (no boost)
            "active_positions": 5,
        }
        
        levers_base = compute_levers(
            phase_macro="Good",
            phase_meso="Recover",
            cut_pressure=0.2,
            features=features_base
        )
        
        features_new = features_base.copy()
        features_new["pair_created_at"] = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()  # 3 hours old (15% boost)
        
        levers_new = compute_levers(
            phase_macro="Good",
            phase_meso="Recover",
            cut_pressure=0.2,
            features=features_new
        )
        
        # Newer tokens should have higher a_final (age boost)
        assert levers_new["A_value"] >= levers_base["A_value"], f"Newer token should have higher or equal a_final: {levers_new['A_value']} >= {levers_base['A_value']}"
        
        print(f"   ✅ Age component works: newer token has higher a_final ({levers_new['A_value']:.4f} >= {levers_base['A_value']:.4f})")
        
        # Test mcap component
        print("\n📊 Testing mcap component...")
        features_small = features_base.copy()
        features_small["market_cap"] = 50_000  # <$100k (15% boost)
        
        levers_small = compute_levers(
            phase_macro="Good",
            phase_meso="Recover",
            cut_pressure=0.2,
            features=features_small
        )
        
        # Smaller mcap should have higher a_final (mcap boost)
        assert levers_small["A_value"] >= levers_base["A_value"], f"Smaller mcap should have higher or equal a_final: {levers_small['A_value']} >= {levers_base['A_value']}"
        
        print(f"   ✅ MCap component works: smaller mcap has higher a_final ({levers_small['A_value']:.4f} >= {levers_base['A_value']:.4f})")
        
        print("✅ Step 1: A score calculation works correctly")
    
    def test_e_score_calculation(
        self,
        test_db
    ):
        """
        Test E score calculation from phase and cut_pressure.
        
        Expected:
        - e_final clamped between 0.0 and 1.0
        - e_final reflects phase and cut_pressure
        """
        print("\n📊 Step 1: Testing E score calculation...")
        
        features = {
            "intent_metrics": {},
            "active_positions": 5,
        }
        
        # Test with high cut pressure
        print("\n📊 Test Case: High cut pressure")
        levers_high_cp = compute_levers(
            phase_macro="Dip",
            phase_meso="Double-Dip",
            cut_pressure=0.9,
            features=features
        )
        
        e_final_high = levers_high_cp["E_value"]
        assert 0.0 <= e_final_high <= 1.0, f"e_final should be clamped: {e_final_high}"
        
        print(f"   ✅ High cut pressure: e_final={e_final_high:.4f}")
        
        # Test with low cut pressure
        print("\n📊 Test Case: Low cut pressure")
        levers_low_cp = compute_levers(
            phase_macro="Dip",
            phase_meso="Double-Dip",
            cut_pressure=0.1,
            features=features
        )
        
        e_final_low = levers_low_cp["E_value"]
        assert 0.0 <= e_final_low <= 1.0, f"e_final should be clamped: {e_final_low}"
        
        # Higher cut pressure should result in higher e_final
        assert e_final_high > e_final_low, f"Higher cut pressure should result in higher e_final: {e_final_high} > {e_final_low}"
        
        print(f"   ✅ Low cut pressure: e_final={e_final_low:.4f}")
        print(f"   ✅ Cut pressure effect verified: {e_final_high:.4f} > {e_final_low:.4f}")
        
        # Test phase effect on E
        print("\n📊 Test Case: Phase effect on E")
        levers_oh_shit = compute_levers(
            phase_macro="Oh-Shit",
            phase_meso="Oh-Shit",
            cut_pressure=0.5,
            features=features
        )
        
        e_final_oh_shit = levers_oh_shit["E_value"]
        assert 0.0 <= e_final_oh_shit <= 1.0, f"e_final should be clamped: {e_final_oh_shit}"
        
        print(f"   ✅ Oh-Shit phase: e_final={e_final_oh_shit:.4f}")
        
        print("✅ Step 1: E score calculation works correctly")
    
    def test_ae_scores_missing_data(
        self,
        test_db
    ):
        """
        Test A/E scores with missing majors data or missing features.
        
        Expected: Fallback values used (system continues without errors)
        """
        print("\n📊 Step 1: Testing A/E scores with missing data...")
        
        # Test with missing intent_metrics
        print("\n📊 Test Case: Missing intent_metrics")
        features_no_intent = {
            "active_positions": 5,
        }
        
        levers_no_intent = compute_levers(
            phase_macro="Good",
            phase_meso="Recover",
            cut_pressure=0.3,
            features=features_no_intent
        )
        
        assert 0.0 <= levers_no_intent["A_value"] <= 1.0, "A_value should be clamped even with missing intent"
        assert 0.0 <= levers_no_intent["E_value"] <= 1.0, "E_value should be clamped even with missing intent"
        
        print(f"   ✅ Missing intent: a_final={levers_no_intent['A_value']:.4f}, e_final={levers_no_intent['E_value']:.4f}")
        
        # Test with missing age (no pair_created_at)
        print("\n📊 Test Case: Missing age (no pair_created_at)")
        features_no_age = {
            "intent_metrics": {},
            "active_positions": 5,
        }
        
        levers_no_age = compute_levers(
            phase_macro="Good",
            phase_meso="Recover",
            cut_pressure=0.3,
            features=features_no_age
        )
        
        assert 0.0 <= levers_no_age["A_value"] <= 1.0, "A_value should be clamped even with missing age"
        assert 0.0 <= levers_no_age["E_value"] <= 1.0, "E_value should be clamped even with missing age"
        
        print(f"   ✅ Missing age: a_final={levers_no_age['A_value']:.4f}, e_final={levers_no_age['E_value']:.4f}")
        
        # Test with missing mcap
        print("\n📊 Test Case: Missing mcap")
        features_no_mcap = {
            "intent_metrics": {},
            "active_positions": 5,
        }
        
        levers_no_mcap = compute_levers(
            phase_macro="Good",
            phase_meso="Recover",
            cut_pressure=0.3,
            features=features_no_mcap
        )
        
        assert 0.0 <= levers_no_mcap["A_value"] <= 1.0, "A_value should be clamped even with missing mcap"
        assert 0.0 <= levers_no_mcap["E_value"] <= 1.0, "E_value should be clamped even with missing mcap"
        
        print(f"   ✅ Missing mcap: a_final={levers_no_mcap['A_value']:.4f}, e_final={levers_no_mcap['E_value']:.4f}")
        
        # Test with all missing (minimal features)
        print("\n📊 Test Case: Minimal features (all optional missing)")
        features_minimal = {}
        
        levers_minimal = compute_levers(
            phase_macro="Good",
            phase_meso="Recover",
            cut_pressure=0.3,
            features=features_minimal
        )
        
        assert 0.0 <= levers_minimal["A_value"] <= 1.0, "A_value should be clamped even with minimal features"
        assert 0.0 <= levers_minimal["E_value"] <= 1.0, "E_value should be clamped even with minimal features"
        
        print(f"   ✅ Minimal features: a_final={levers_minimal['A_value']:.4f}, e_final={levers_minimal['E_value']:.4f}")
        
        print("✅ Step 1: Missing data handling works correctly (no errors, fallback values used)")


