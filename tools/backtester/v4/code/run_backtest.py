#!/usr/bin/env python3
"""
Workflow script to run full backtest process for a token (V4):
1. Backfill 1h data
2. Run Geometry (no charts)
3. Run TA Tracker
4. Run Backtest
"""

import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

# Add project root to path for imports
# File is at: backtester/v4/code/run_backtest.py
# Need to go up 4 levels to reach project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
from supabase import create_client, Client

# Production jobs
from src.intelligence.lowcap_portfolio_manager.jobs.geckoterminal_backfill import backfill_token_1h
from src.intelligence.lowcap_portfolio_manager.jobs.geometry_build_daily import GeometryBuilder
from src.intelligence.lowcap_portfolio_manager.jobs.ta_tracker import TATracker

# Import backtest main (must be after path setup)
import importlib.util
backtest_path = os.path.join(os.path.dirname(__file__), "backtest_uptrend_v4.py")
spec = importlib.util.spec_from_file_location("backtest_uptrend_v4", backtest_path)
backtest_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backtest_module)
backtest_main = backtest_module.main

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def get_token_info(ticker: str) -> Dict[str, Any]:
    """Look up token contract and chain from ticker."""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
    sb: Client = create_client(url, key)
    
    res = (
        sb.table("lowcap_positions")
        .select("token_contract, token_chain, token_ticker")
        .eq("token_ticker", ticker.upper())
        .eq("status", "active")
        .limit(1)
        .execute()
    )
    
    if not res.data:
        raise ValueError(f"Token '{ticker}' not found in active positions")
    
    return {
        "contract": res.data[0]["token_contract"],
        "chain": res.data[0]["token_chain"],
        "ticker": res.data[0].get("token_ticker", ticker.upper()),
    }


def run_backfill(contract: str, chain: str, days: int) -> Dict[str, Any]:
    """Step 1: Backfill 1h OHLCV data."""
    logger.info(f"=== Step 1: Backfilling {days} days of 1h data ===")
    lookback_minutes = days * 24 * 60  # Convert days to minutes
    try:
        result = backfill_token_1h(contract, chain, lookback_minutes=lookback_minutes)
        logger.info(f"Backfill complete: {result.get('inserted_rows', 0)} rows inserted")
        if result.get('error'):
            logger.warning(f"Backfill had errors: {result.get('error')}")
        return result
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        raise


def run_geometry(contract: str, chain: str) -> None:
    """Step 2: Build geometry (no charts)."""
    logger.info(f"=== Step 2: Building geometry (no charts) ===")
    GeometryBuilder(generate_charts=False).build()
    logger.info("Geometry build complete")


def run_ta_tracker(contract: str, chain: str) -> None:
    """Step 3: Run TA Tracker."""
    logger.info(f"=== Step 3: Running TA Tracker ===")
    tracker = TATracker()
    tracker.run()
    logger.info("TA Tracker complete")


def run_backtest(ticker: str, days: int) -> None:
    """Step 4: Run backtest."""
    logger.info(f"=== Step 4: Running backtest ===")
    # Simulate command-line args for backtest_main
    sys.argv = ["backtest_uptrend_v4.py", ticker, str(days)]
    try:
        backtest_main()
    except SystemExit:
        pass
    logger.info("Backtest complete")


def main():
    """Main workflow: backfill → geometry → TA → backtest."""
    if len(sys.argv) < 2:
        print("Usage: python3 run_backtest.py <TOKEN_TICKER> [days]")
        print("\nExample: python3 run_backtest.py DREAMS 14")
        print("\nThis will:")
        print("  1. Backfill 1h OHLCV data")
        print("  2. Build geometry (no charts)")
        print("  3. Run TA Tracker")
        print("  4. Run backtest and generate chart")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    days = int(sys.argv[2]) if len(sys.argv) >= 3 else 14
    
    print(f"\n{'='*60}")
    print(f"Backtest Workflow V4 for {ticker} ({days} days)")
    print(f"{'='*60}\n")
    
    try:
        # Look up token info
        token_info = get_token_info(ticker)
        contract = token_info["contract"]
        chain = token_info["chain"]
        ticker = token_info["ticker"]
        
        print(f"Token: {ticker}")
        print(f"Contract: {contract[:30]}...")
        print(f"Chain: {chain}\n")
        
        # Step 1: Backfill
        backfill_result = run_backfill(contract, chain, days)
        if backfill_result.get("inserted_rows", 0) == 0:
            logger.warning("No rows inserted in backfill - data may already exist or backfill failed")
        
        # Step 2: Geometry
        run_geometry(contract, chain)
        
        # Step 3: TA Tracker
        run_ta_tracker(contract, chain)
        
        # Step 4: Backtest
        run_backtest(ticker, days)
        
        print(f"\n{'='*60}")
        print(f"✅ Complete! Check backtester/v4/backests/backtest_results_v4_{ticker}_*.png for chart")
        print(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

