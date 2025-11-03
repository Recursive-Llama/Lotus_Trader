#!/usr/bin/env python3
"""
Batch backtest runner V3 - runs backtest workflow for multiple tokens sequentially.
"""

import os
import sys
import logging
from typing import List, Dict, Any

from dotenv import load_dotenv
from supabase import create_client, Client

# Add project root to path
# File is at: backtester/v3/code/run_batch_backtest.py
# Need to go up 4 levels to reach project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import run_backtest functions
import importlib.util
run_backtest_path = os.path.join(os.path.dirname(__file__), "run_backtest.py")
spec = importlib.util.spec_from_file_location("run_backtest", run_backtest_path)
run_backtest_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_backtest_module)
get_token_info = run_backtest_module.get_token_info
run_backfill = run_backtest_module.run_backfill
run_geometry = run_backtest_module.run_geometry
run_ta_tracker = run_backtest_module.run_ta_tracker
run_backtest = run_backtest_module.run_backtest

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def list_active_tokens(limit: int = 50) -> List[Dict[str, Any]]:
    """Get list of active tokens from positions table."""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
    sb: Client = create_client(url, key)
    
    res = (
        sb.table("lowcap_positions")
        .select("token_ticker, token_contract, token_chain")
        .eq("status", "active")
        .limit(limit)
        .execute()
    )
    
    return res.data or []


def run_token_backtest(ticker: str, days: int) -> bool:
    """Run full backtest workflow for a single token. Returns True if successful."""
    try:
        print(f"\n{'='*60}")
        print(f"Processing {ticker}")
        print(f"{'='*60}\n")
        
        token_info = get_token_info(ticker)
        contract = token_info["contract"]
        chain = token_info["chain"]
        ticker = token_info["ticker"]
        
        # Step 1: Backfill
        run_backfill(contract, chain, days)
        
        # Step 2: Geometry
        run_geometry(contract, chain)
        
        # Step 3: TA Tracker
        run_ta_tracker(contract, chain)
        
        # Step 4: Backtest
        run_backtest(ticker, days)
        
        print(f"✅ {ticker} complete!\n")
        return True
        
    except Exception as e:
        logger.error(f"❌ {ticker} failed: {e}", exc_info=True)
        return False


def main():
    """Run backtests for multiple tokens.
    
    Usage:
        python3 run_batch_backtest.py                    # Run all active tokens (default)
        python3 run_batch_backtest.py TICKER1 TICKER2   # Run specific tokens
        python3 run_batch_backtest.py --days 21          # Run all tokens with custom days
        python3 run_batch_backtest.py TICKER1 --days 21 # Run specific token with custom days
    """
    days = 14
    
    # Parse arguments
    args = sys.argv[1:]
    
    # Check for --days flag
    if "--days" in args:
        days_idx = args.index("--days")
        if days_idx + 1 < len(args):
            try:
                days = int(args[days_idx + 1])
                # Remove --days and its value
                args = args[:days_idx] + args[days_idx + 2:]
            except ValueError:
                print("Error: --days requires a number")
                sys.exit(1)
        else:
            print("Error: --days requires a value")
            sys.exit(1)
    
    # Get tickers from remaining args, or all active tokens if none specified
    if args:
        tickers = [t.upper() for t in args]
    else:
        # No tokens specified, get all active tokens
        print("No tokens specified. Selecting all active tokens from positions table...\n")
        all_tokens = list_active_tokens(limit=50)
        
        if len(all_tokens) == 0:
            print("No active tokens found in positions table")
            sys.exit(1)
        
        # Extract all tickers
        tickers = [t.get("token_ticker", "").upper() for t in all_tokens if t.get("token_ticker")]
        tickers = [t for t in tickers if t]  # Filter out empty
        
        # Exclude specific tickers from batch
        exclude = {"ALCH", "ASTER", "GIGGLE"}
        before = len(tickers)
        tickers = [t for t in tickers if t not in exclude]
        after = len(tickers)
        if after < before:
            print(f"Excluding from batch: {', '.join(sorted(exclude))}")
        
        if not tickers:
            print("No valid tickers found")
            sys.exit(1)
        
        print(f"Found {len(tickers)} active token(s)")
    
    print(f"\n{'='*60}")
    print(f"Batch Backtest V3: {len(tickers)} token(s), {days} days each")
    print(f"Tokens: {', '.join(tickers)}")
    print(f"{'='*60}\n")
    
    results = []
    for ticker in tickers:
        success = run_token_backtest(ticker, days)
        results.append({"ticker": ticker, "success": success})
    
    # Summary
    print(f"\n{'='*60}")
    print("BATCH SUMMARY")
    print(f"{'='*60}")
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"✅ Successful: {len(successful)}/{len(results)}")
    for r in successful:
        print(f"   - {r['ticker']}")
    
    if failed:
        print(f"\n❌ Failed: {len(failed)}/{len(results)}")
        for r in failed:
            print(f"   - {r['ticker']}")
    
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

