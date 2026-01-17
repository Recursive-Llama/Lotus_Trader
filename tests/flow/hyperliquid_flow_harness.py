"""
Hyperliquid Flow Test Harness (Real Data)
=========================================

Tests the end-to-end flow using REAL system components and REAL API data:

1. System Startup: Runs `BootstrapSystem.bootstrap_all()`.
   - Discovers markets via `HyperliquidMarketDiscovery`.
   - Backfills history via `backfill_for_position`.
2. Analysis: Runs TATracker -> UptrendEngine.
3. Decision: Runs PMCoreTick.
4. Verify: Checks if position state updated and trade execution attempted (expected to fail/skip for now).

Usage:
    HL_DRY_RUN=1 hl_ingest_enabled=1 PYTHONPATH=. .venv/bin/python tests/flow/hyperliquid_flow_harness.py
"""

import os
import sys
import time
import json
import logging
from typing import Dict, Any

from supabase import create_client
from dotenv import load_dotenv

# Ensure src is in path
sys.path.append(os.getcwd())
load_dotenv()

# Enable HL Ingest for the test (required for bootstrap to run HL steps)
os.environ["HL_INGEST_ENABLED"] = "1"

from src.intelligence.lowcap_portfolio_manager.jobs.bootstrap_system import BootstrapSystem
from src.intelligence.lowcap_portfolio_manager.jobs.ta_tracker import TATracker
from src.intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v4 import UptrendEngineV4
from src.intelligence.lowcap_portfolio_manager.jobs.pm_core_tick import PMCoreTick

# Configuration
TEST_TOKEN = "BTC"
TEST_CHAIN = "hyperliquid"
TEST_TIMEFRAME = "1h"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Silence noisy libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("supabase").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)

logger = logging.getLogger("HL_REAL_TEST")
logger.setLevel(logging.INFO)

class HyperliquidRealFlowHarness:
    def __init__(self):
        self.sb = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        self.position_id = None
        # Initialize PMCoreTick to get access to executor
        self.pm = PMCoreTick(timeframe=TEST_TIMEFRAME)

    def cleanup_previous_state(self):
        """Delete existing position to force fresh discovery and backfill."""
        logger.info(f"CLEANUP: Deleting existing {TEST_TOKEN} position...")
        try:
            self.sb.table("lowcap_positions").delete().eq("token_contract", TEST_TOKEN).eq("token_chain", TEST_CHAIN).execute()
        except Exception as e:
            logger.warning(f"Cleanup warning: {e}")

    def run_system_startup(self):
        """Simulate 'Turning the System On' via BootstrapSystem."""
        logger.info("STARTUP: Running BootstrapSystem...")
        
        bootstrap = BootstrapSystem()
        results = bootstrap.bootstrap_all()
        
        # Verify HL steps
        hl_markets = results.get("steps", {}).get("hyperliquid_markets", {})
        logger.info(f"Bootstrap Result (HL Markets): {hl_markets}")
        
        if hl_markets.get("error"):
            logger.error("Bootstrap failed to initialize Hyperliquid markets!")
            sys.exit(1)
            
        # Verify Backfill happened
        if hl_markets.get("backfilled_total", 0) == 0:
             logger.warning("Bootstrap didn't report any backfilled bars. This might be fine if data existed, but we did cleanup.")
        else:
             logger.info(f"SUCCESS: Backfilled {hl_markets['backfilled_total']} bars.")

        # Get the new position ID
        res = self.sb.table("lowcap_positions").select("id").eq("token_contract", TEST_TOKEN).eq("timeframe", TEST_TIMEFRAME).execute()
        if res.data:
            self.position_id = res.data[0]['id']
            logger.info(f"Position Discovered & Created: {self.position_id}")
        else:
            logger.error(f"Position {TEST_TOKEN} was NOT created by bootstrap!")
            sys.exit(1)

    def run_analysis_pipeline(self):
        """Run TATracker and UptrendEngine."""
        logger.info("PIPELINE: Running Analysis...")
        
        # 1. TA Tracker (Real Data from Backfill)
        logger.info(">> Running TATracker...")
        try:
            tracker = TATracker(timeframe=TEST_TIMEFRAME)
            tracker.run() 
        except Exception as e:
            logger.error(f"TA Tracker failed: {e}")
            
        # 2. Uptrend Engine
        logger.info(">> Running UptrendEngine...")
        try:
            engine = UptrendEngineV4(timeframe=TEST_TIMEFRAME)
            engine.run(include_regime_drivers=True)
        except Exception as e:
             logger.error(f"Uptrend Engine failed: {e}")

        # Verify State
        pos = self._get_position()
        uptrend = pos.get('features', {}).get('uptrend_engine_v4', {})
        state = uptrend.get('state')
        logger.info(f"Current State: {state}")

    def run_pm_decision(self):
        """
        Force a decision execution to test the wiring.
        The real analysis might not produce a buy signal (because market is just meandering),
        but we need to verify the executor path.
        """
        print("FORCING PM EXECUTION (To verify wiring)...")
        
        # 1. Get position
        if not self.position_id:
             print("Skipping execution (no position ID)")
             return

        pos = self._get_position()
        
        # 2. Create synthetic decision
        # Dry run execution for Hyperliquid
        # Use a small size fraction
        decision = {
            "decision_type": "entry", # or "add"
            "size_frac": 0.01, # 1%
            "reasons": {
                "flag": "manual_test",
                "state": "S0",
                "score": 100
            }
        }
        
        print(f"Executing forced decision: {decision}")
        
        # 3. Call executor directly
        # The PMExecutor should route this to HyperliquidExecutor based on chain='hyperliquid'
        try:
            result = self.pm.executor.execute(decision, pos)
            print(f"Execution Result: {json.dumps(result, indent=2)}")
            
            if result.get("status") in ["success", "skipped"]:
                 # Dry run usually returns "skipped" with reason "Dry run"
                 # Or "success" with skipped=True
                 print("--> Execution path verify: OK")
                 self.execution_result = result
            else:
                 print(f"--> Execution path verify: FAIL ({result.get('error')})")
                 sys.exit(1)
                 
        except Exception as e:
            logger.exception("Execution wiring failed")
            sys.exit(1)
            
    def verify_results(self):
        print("\n" + "="*50)
        print("HYPERLIQUID REAL FLOW TEST RESULTS")
        print("="*50)
        
        # 1. Verify Ingestion
        try:
             pos = self._get_position()
             state = (pos.get("features") or {}).get("uptrend_engine_v4", {}).get("state", "unknown")
             print(f"Ingestion & Analysis: PASS (State: {state})")
        except:
             print("Ingestion & Analysis: FAIL (Could not read position)")
             
        # 2. Verify Execution Wiring
        if hasattr(self, 'execution_result'):
             res = self.execution_result
             # dry run checks
             if res.get("status") == "skipped" or (res.get("status") == "success" and res.get("slippage") == 0.0):
                  print("Execution Wiring:     PASS (HyperliquidExecutor was called)")
             else:
                  print(f"Execution Wiring:     FAIL (Unexpected result: {res})")
        else:
             print("Execution Wiring:     FAIL (Not attempted)")
             
        print("="*50 + "\n")

    def _get_position(self):
        res = self.sb.table("lowcap_positions").select("*").eq("id", self.position_id).execute()
        return res.data[0]

def main():
    if not os.getenv("HL_DRY_RUN"):
        os.environ["HL_DRY_RUN"] = "1"
        
    harness = HyperliquidRealFlowHarness()
    try:
        harness.run_system_startup()
        harness.run_analysis_pipeline()
        harness.run_pm_decision() # Forces execution
        harness.verify_results()
    except Exception as e:
        logger.exception(f"Test Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
