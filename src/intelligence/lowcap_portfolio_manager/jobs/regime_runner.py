"""
Regime Runner

Orchestrates the full regime pipeline:
1. regime_price_collector: Collect OHLC for BTC/ALT/buckets/dominance
2. regime_ta_tracker: Compute TA for regime driver positions
3. uptrend_engine_v4: Run uptrend engine on regime drivers (compute S0/S1/S2/S3 states)

The regime_ae_calculator then uses these states to compute A/E for tokens.

Usage:
    # Run full pipeline for 1h timeframe
    python -m src.intelligence.lowcap_portfolio_manager.jobs.regime_runner --timeframe 1h
    
    # Run all timeframes
    python -m src.intelligence.lowcap_portfolio_manager.jobs.regime_runner --all
    
    # Show regime summary
    python -m src.intelligence.lowcap_portfolio_manager.jobs.regime_runner --summary
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def run_regime_pipeline(
    timeframe: str = "1h",
    collect_prices: bool = True,
    compute_ta: bool = True,
    run_uptrend: bool = True,
) -> Dict[str, Any]:
    """
    Run the full regime pipeline for a timeframe.
    
    Args:
        timeframe: Regime timeframe ('1m', '1h', '1d')
        collect_prices: If True, collect regime price data
        compute_ta: If True, compute TA for regime drivers
        run_uptrend: If True, run uptrend engine on regime drivers
    
    Returns:
        Summary of pipeline results
    """
    results = {
        "timeframe": timeframe,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "steps": {},
    }
    
    # Step 1: Collect regime prices
    if collect_prices:
        try:
            from src.intelligence.lowcap_portfolio_manager.jobs.regime_price_collector import (
                RegimePriceCollector,
            )
            collector = RegimePriceCollector()
            price_results = collector.run(timeframe=timeframe)
            results["steps"]["price_collector"] = {
                "success": True,
                "drivers_collected": price_results.get("drivers_collected", []),
                "errors": price_results.get("errors", []),
            }
            logger.info(f"Price collection complete: {price_results}")
        except Exception as e:
            logger.error(f"Price collection failed: {e}")
            results["steps"]["price_collector"] = {"success": False, "error": str(e)}
    
    # Step 2: Compute TA for regime drivers
    if compute_ta:
        try:
            from src.intelligence.lowcap_portfolio_manager.jobs.regime_ta_tracker import (
                RegimeTATracker,
            )
            tracker = RegimeTATracker(timeframe=timeframe)
            ta_updated = tracker.run()
            results["steps"]["ta_tracker"] = {
                "success": True,
                "positions_updated": ta_updated,
            }
            logger.info(f"TA tracker updated {ta_updated} positions")
        except Exception as e:
            logger.error(f"TA tracker failed: {e}")
            results["steps"]["ta_tracker"] = {"success": False, "error": str(e)}
    
    # Step 3: Run uptrend engine on regime drivers
    if run_uptrend:
        try:
            from src.intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v4 import (
                UptrendEngineV4,
            )
            # Map regime timeframe to position timeframe for uptrend engine
            # Now that schema allows '1d', we use regime timeframes directly
            position_tf = {"1d": "1d", "1h": "1h", "1m": "1m"}.get(timeframe, timeframe)
            engine = UptrendEngineV4(timeframe=position_tf)
            uptrend_updated = engine.run(include_regime_drivers=True)
            results["steps"]["uptrend_engine"] = {
                "success": True,
                "positions_updated": uptrend_updated,
            }
            logger.info(f"Uptrend engine updated {uptrend_updated} positions")
        except Exception as e:
            logger.error(f"Uptrend engine failed: {e}")
            results["steps"]["uptrend_engine"] = {"success": False, "error": str(e)}
    
    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    return results


def run_all_timeframes() -> Dict[str, Any]:
    """Run regime pipeline for all timeframes (1d, 1h, 1m)."""
    results = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "timeframes": {},
    }
    
    for tf in ["1d", "1h", "1m"]:
        logger.info(f"Running regime pipeline for {tf}")
        tf_results = run_regime_pipeline(timeframe=tf)
        results["timeframes"][tf] = tf_results
    
    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    return results


def show_regime_summary() -> None:
    """Show a summary of current regime states."""
    def _glyph(stage: str) -> str:
        mapping = {
            "S0": "🜁0",
            "S1": "🜂1",
            "S2": "🜃2",
            "S3": "🜓3",
            "S4": "🝪4",
        }
        return mapping.get(str(stage), str(stage))
    try:
        from src.intelligence.lowcap_portfolio_manager.jobs.regime_ae_calculator import (
            RegimeAECalculator,
        )
        calculator = RegimeAECalculator()
        summary = calculator.get_regime_summary()
        
        print("\n" + "=" * 70)
        print("REGIME DRIVER SUMMARY")
        print("=" * 70)
        
        # Group by driver type
        global_drivers = ["BTC", "ALT", "BTC.d", "USDT.d"]
        bucket_drivers = ["nano", "small", "mid", "big"]
        
        print("\n--- Global Drivers ---")
        for driver in global_drivers:
            if driver in summary:
                print(f"\n  {driver}:")
                for tf in ["1d", "1h", "1m"]:
                    if tf in summary[driver]:
                        data = summary[driver][tf]
                        state = _glyph(data.get("state", "?"))
                        flags = []
                        if data.get("buy_flag"):
                            flags.append("BUY")
                        if data.get("trim_flag"):
                            flags.append("TRIM")
                        if data.get("emergency_exit"):
                            flags.append("EMERG")
                        flags_str = f" [{', '.join(flags)}]" if flags else ""
                        print(f"    {tf}: {state}{flags_str}")
        
        print("\n--- Bucket Drivers ---")
        for driver in bucket_drivers:
            if driver in summary:
                print(f"\n  {driver}:")
                for tf in ["1d", "1h", "1m"]:
                    if tf in summary[driver]:
                        data = summary[driver][tf]
                        state = _glyph(data.get("state", "?"))
                        flags = []
                        if data.get("buy_flag"):
                            flags.append("BUY")
                        if data.get("trim_flag"):
                            flags.append("TRIM")
                        if data.get("emergency_exit"):
                            flags.append("EMERG")
                        flags_str = f" [{', '.join(flags)}]" if flags else ""
                        print(f"    {tf}: {state}{flags_str}")
        
        # Show sample A/E calculations
        print("\n" + "-" * 70)
        print("Sample A/E Calculations (exec_tf=1h, no intent deltas)")
        print("-" * 70)
        for bucket in bucket_drivers:
            a, e = calculator.compute_ae_for_token(
                token_bucket=bucket,
                exec_timeframe="1h",
                refresh_cache=False,
            )
            print(f"  {bucket:8s}: A={a:.3f}, E={e:.3f}")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        logger.error(f"Failed to get regime summary: {e}")
        raise


def main() -> None:
    """CLI entry point."""
    import argparse
    
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="Regime Runner")
    parser.add_argument("--timeframe", type=str, default="1h",
                       help="Timeframe to run (1m, 1h, 1d)")
    parser.add_argument("--all", action="store_true",
                       help="Run all timeframes")
    parser.add_argument("--summary", action="store_true",
                       help="Show regime summary")
    parser.add_argument("--no-prices", action="store_true",
                       help="Skip price collection")
    parser.add_argument("--no-ta", action="store_true",
                       help="Skip TA computation")
    parser.add_argument("--no-uptrend", action="store_true",
                       help="Skip uptrend engine")
    args = parser.parse_args()
    
    if args.summary:
        show_regime_summary()
    elif args.all:
        results = run_all_timeframes()
        print(f"\nPipeline complete: {results}")
    else:
        results = run_regime_pipeline(
            timeframe=args.timeframe,
            collect_prices=not args.no_prices,
            compute_ta=not args.no_ta,
            run_uptrend=not args.no_uptrend,
        )
        print(f"\nPipeline complete: {results}")


if __name__ == "__main__":
    main()

