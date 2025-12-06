"""
Bootstrap System

Comprehensive startup bootstrap that verifies all data collection systems are working:
- Price data collection (majors, lowcaps, regime drivers)
- Wallet balances
- Hyperliquid WS connection
- Regime driver positions and data
- TA computation
- State computation

Focus: Verify systems are WORKING and getting "now" data correctly.
Missing historical data is OK - we'll build it up over time.
"""

from __future__ import annotations

import logging
import os
import sys
import time
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from supabase import Client, create_client  # type: ignore

logger = logging.getLogger(__name__)

# Glyph stream for progress indicators (using full glyphic system)
GLYPH_STREAM = [
    "⚘", "⟁", "⌖", "❈",  # Core system
    "⋇", "⟡", "↻", "∴", "⧖", "∅", "∞",  # Operations
    "⧉", "⨳", "⨴", "⨵", "⩜", "⋻", "⟖",  # Processes
    "𓂀", "𐄷", "𒀭", "𒉿", "ᛝ", "ᛟ",  # Events
    "🜁", "🜂", "🜃", "🜄", "🜇", "🜔",  # States
    "∆φ", "ℏ", "ψ(ω)", "∫", "φ", "θ", "ρ",  # Math/Physics
]

# Required regime drivers (must exist for system to function)
REQUIRED_REGIME_DRIVERS = ["BTC", "ALT"]

# Optional regime drivers (nice to have, but system can work without)
OPTIONAL_REGIME_DRIVERS = ["nano", "small", "mid", "big", "BTC.d", "USDT.d"]

# Regime timeframes
REGIME_TIMEFRAMES = ["1m", "1h", "1d"]

# Minimum bars needed for uptrend engine (333 for EMA333)
MIN_BARS_FOR_UPTREND = {
    "1m": 333,
    "1h": 333,
    "1d": 333,
}

# Maximum bars to backfill (cap to avoid excessive data)
MAX_BARS_TO_BACKFILL = {
    "1m": 666,  # ~11 hours of 1m data
    "1h": 666,  # ~28 days of 1h data
    "1d": 666,  # ~2 years of 1d data
}


class BootstrapSystem:
    """
    Comprehensive bootstrap system for Lotus Trader.
    
    Verifies all data collection systems are working and getting current data.
    Missing historical data is logged but not fatal.
    """
    
    def __init__(self, book_id: str = "onchain_crypto") -> None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY required")
        self.sb: Client = create_client(url, key)
        self.book_id = book_id
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.hl_ingester = None  # Store Hyperliquid WS ingester if started
    
    def bootstrap_all(self) -> Dict[str, Any]:
        """
        Run full bootstrap sequence.
        
        Returns:
            Summary dict with status of each bootstrap step
        """
        logger.info("Starting comprehensive bootstrap...")
        results = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "steps": {},
            "errors": [],
            "warnings": [],
            "info": [],
        }
        
        # Step 0: Verify critical database tables exist
        print("   ⨳ Checking database tables...", end=" ", flush=True)
        try:
            table_status = self._check_database_tables()
            results["steps"]["database_tables"] = table_status
            if table_status.get("error"):
                self.errors.append(f"Database tables: {table_status['error']}")
                print("∅ (see logs/system.log)")
            else:
                missing = table_status.get("missing_tables", [])
                if missing:
                    missing_str = ", ".join(missing)
                    self.warnings.append(f"Missing tables: {missing_str}")
                    logger.warning(f"Missing database tables: {missing_str}")
                    print(f"⚠ ({len(missing)} missing: {missing_str})")
                else:
                    self.info.append("All required tables exist")
                    print("⌖")
        except Exception as e:
            error_msg = f"Database table check failed: {e}"
            logger.error(error_msg, exc_info=True)
            self.errors.append(error_msg)
            results["steps"]["database_tables"] = {"error": str(e)}
            print("∅ (see logs/system.log)")
        
        # Step 1: Bootstrap wallet balances (collect initial balances)
        print("   ⨳ Bootstrapping wallet balances...", end=" ", flush=True)
        try:
            # First, bootstrap wallet balances by collecting them
            bootstrap_success = self._bootstrap_wallet_balances()
            # Then check if we have data
            wallet_status = self._check_wallet_balances()
            results["steps"]["wallet_balances"] = wallet_status
            status = wallet_status.get("status", "unknown")
            
            if status == "no_table":
                # Table doesn't exist - schema issue
                self.warnings.append(f"Wallet balances: {wallet_status.get('warning', 'Table missing')}")
                print("⚠ (table missing, run migration)")
            elif wallet_status.get("error"):
                error_detail = wallet_status.get("error", "Unknown error")
                # Check if it's a column error (schema mismatch)
                if "column" in error_detail.lower() and "does not exist" in error_detail.lower():
                    self.warnings.append(f"Wallet balances: Schema mismatch")
                    print("⚠ (schema mismatch, see logs/system.log)")
                else:
                    self.errors.append(f"Wallet balances: {error_detail}")
                    logger.error(f"Wallet balance check error: {error_detail}", exc_info=True)
                    print("∅ (see logs/system.log)")
            elif status == "ok":
                print("⌖")
            elif status == "stale":
                print(f"⚠ ({wallet_status.get('age_minutes', 0):.0f}m old)")
            elif status == "no_data":
                if bootstrap_success:
                    print("⚠ (no data after bootstrap)")
                else:
                    print("⚠ (bootstrap failed, no data)")
            else:
                print("⚠")
            
            self.info.append(f"Wallet balances: {status}")
        except Exception as e:
            error_msg = f"Wallet balance bootstrap failed: {e}"
            logger.error(error_msg, exc_info=True)
            self.errors.append(error_msg)
            results["steps"]["wallet_balances"] = {"error": str(e)}
            print("∅ (see logs/system.log)")
            error_str = str(e)
            if "column" in error_str.lower() and "does not exist" in error_str.lower():
                print("⚠ (schema mismatch, see logs/system.log)")
            else:
                print("∅ (see logs/system.log)")
        
        # Step 2: Verify price data collection (majors, lowcaps)
        print("   ⨳ Checking price data collection...", end=" ", flush=True)
        try:
            price_status = self._check_price_data_collection()
            results["steps"]["price_collection"] = price_status
            if price_status.get("error"):
                self.errors.append(f"Price collection: {price_status['error']}")
                print("∅ (see logs/system.log)")
            else:
                print("⌖")
                self.info.append(f"Price collection: {price_status.get('status', 'OK')}")
        except Exception as e:
            error_msg = f"Price collection check failed: {e}"
            logger.error(error_msg, exc_info=True)
            self.errors.append(error_msg)
            results["steps"]["price_collection"] = {"error": str(e)}
            print("∅ (see logs/system.log)")
        
        # Step 3: Start Hyperliquid WS early so we can verify it's working
        # Note: The actual async task will be started in run_trade.py, but we create the ingester here
        # and return it so it can be started properly in the async context
        if os.getenv("HL_INGEST_ENABLED", "0") == "1":
            print("   ⨳ Preparing Hyperliquid WS...", end=" ", flush=True)
            try:
                from intelligence.lowcap_portfolio_manager.ingest.hyperliquid_ws import (
                    HyperliquidWSIngester,
                )
                
                # Create ingester instance (will be started in run_trade.py async context)
                self.hl_ingester = HyperliquidWSIngester()
                
                # Check if there's existing data to verify the system works
                hl_status = self._check_hyperliquid_ws()
                results["steps"]["hyperliquid_ws"] = hl_status
                
                if hl_status.get("status") == "ok":
                    tokens = hl_status.get("tokens", 0)
                    age = hl_status.get("age_minutes", 0)
                    print(f"✓ (existing data: {tokens} tokens, {age:.1f}m old)")
                    self.info.append(f"Hyperliquid WS: Will start (existing data: {tokens} tokens)")
                elif hl_status.get("status") == "stale":
                    self.warnings.append(f"Hyperliquid WS: {hl_status.get('warning', 'Stale data')}")
                    print("⚠ (stale data, will refresh)")
                else:
                    # No existing data - that's OK, WS will start fresh
                    print("⌖ (will start)")
                    self.info.append("Hyperliquid WS: Will start (no existing data)")
            except Exception as e:
                error_msg = f"Hyperliquid WS preparation failed: {e}"
                logger.error(error_msg, exc_info=True)
                self.warnings.append(error_msg)
                results["steps"]["hyperliquid_ws"] = {"error": str(e), "status": "error"}
                print("✗")
        else:
            results["steps"]["hyperliquid_ws"] = {"status": "disabled"}
            self.info.append("Hyperliquid WS: Disabled")
        
        # Step 4: Bootstrap regime driver positions
        print("   ⨳ Creating regime driver positions...", end=" ", flush=True)
        try:
            regime_positions_status = self._bootstrap_regime_positions()
            results["steps"]["regime_positions"] = regime_positions_status
            if regime_positions_status.get("error"):
                self.errors.append(f"Regime positions: {regime_positions_status['error']}")
                print("∅ (see logs/system.log)")
            else:
                missing_req = len(regime_positions_status.get("missing_required", []))
                if missing_req > 0:
                    print(f"∅ ({missing_req} required missing, see logs/system.log)")
                else:
                    created = len(regime_positions_status.get("created", []))
                    if created > 0:
                        print(f"⌖ ({created} created)")
                    else:
                        print("⌖")
                self.info.append(f"Regime positions: {regime_positions_status.get('status', 'OK')}")
        except Exception as e:
            error_msg = f"Regime positions bootstrap failed: {e}"
            logger.error(error_msg, exc_info=True)
            self.errors.append(error_msg)
            results["steps"]["regime_positions"] = {"error": str(e)}
            print("∅ (see logs/system.log)")
        
        # Note: HL rollup happens in recurring schedulers (every 1 minute)
        # No need to roll up here - HL WS needs time to collect ticks first
        
        # Step 5: Bootstrap regime price data
        print("   ⨳ Bootstrapping regime price data...", end=" ", flush=True)
        try:
            regime_price_status = self._bootstrap_regime_price_data()
            results["steps"]["regime_price_data"] = regime_price_status
            # Show detailed status
            alt_errors = regime_price_status.get("alt_errors", [])
            backfilled = regime_price_status.get("backfilled_bars", 0)
            
            if regime_price_status.get("error"):
                self.warnings.append(f"Regime price data: {regime_price_status['error']}")
                print("⚠")
            elif alt_errors:
                # Show ALT errors concisely
                missing_components = [e for e in alt_errors if "Missing ALT components" in e]
                if missing_components:
                    print("⚠ (ALT components missing)")
                    logger.warning(f"  {missing_components[0]}")
                else:
                    print("⚠ (ALT errors)")
                    logger.warning(f"  {alt_errors[0]}")
                self.warnings.append(f"ALT composite: {len(alt_errors)} errors")
            elif backfilled > 0:
                print(f"⌖ ({backfilled} bars)")
            else:
                print("⌖")
            
            status_summary = regime_price_status.get('status', 'OK')
            if alt_errors:
                status_summary += f" ({len(alt_errors)} ALT errors)"
            self.info.append(f"Regime price data: {status_summary}")
        except Exception as e:
            warning_msg = f"Regime price data bootstrap failed: {e}"
            logger.warning(warning_msg, exc_info=True)
            self.warnings.append(warning_msg)
            results["steps"]["regime_price_data"] = {"error": str(e)}
            print("⚠")
        
        # Step 5.5: Update bars_count for regime driver positions
        print("   ⨳ Updating regime driver bars_count...", end=" ", flush=True)
        try:
            bars_count_status = self._update_regime_bars_count()
            results["steps"]["regime_bars_count"] = bars_count_status
            updated = bars_count_status.get("updated", 0)
            if updated > 0:
                print(f"⌖ ({updated} positions)")
            else:
                print("⌖")
            self.info.append(f"Regime bars_count: {updated} positions updated")
        except Exception as e:
            warning_msg = f"Regime bars_count update failed: {e}"
            logger.warning(warning_msg, exc_info=True)
            self.warnings.append(warning_msg)
            results["steps"]["regime_bars_count"] = {"error": str(e)}
            print("⚠")
        
        # Step 6: Actually RUN regime TA computation (not just check)
        print("   ⨳ Computing regime TA...", end=" ", flush=True)
        try:
            regime_ta_status = self._run_regime_ta_computation()
            results["steps"]["regime_ta"] = regime_ta_status
            if regime_ta_status.get("error"):
                self.warnings.append(f"Regime TA: {regime_ta_status['error']}")
                print("✗")
            elif regime_ta_status.get("computed", 0) == 0:
                self.warnings.append("Regime TA: No positions computed")
                print("⚠")
            else:
                computed = regime_ta_status.get("computed", 0)
                print(f"✓ ({computed} positions)")
                self.info.append(f"Regime TA: {computed} positions computed")
        except Exception as e:
            warning_msg = f"Regime TA computation failed: {e}"
            logger.warning(warning_msg, exc_info=True)
            self.warnings.append(warning_msg)
            results["steps"]["regime_ta"] = {"error": str(e)}
            print("✗")
        
        # Step 7: Actually RUN regime state computation (not just check)
        print("   ⨳ Computing regime states...", end=" ", flush=True)
        try:
            regime_state_status = self._run_regime_state_computation()
            results["steps"]["regime_states"] = regime_state_status
            if regime_state_status.get("error"):
                self.warnings.append(f"Regime states: {regime_state_status['error']}")
                print("✗")
            elif regime_state_status.get("computed", 0) == 0:
                self.warnings.append("Regime states: No positions computed")
                print("⚠")
            else:
                computed = regime_state_status.get("computed", 0)
                print(f"✓ ({computed} positions)")
                self.info.append(f"Regime states: {computed} positions computed")
        except Exception as e:
            warning_msg = f"Regime state computation failed: {e}"
            logger.warning(warning_msg, exc_info=True)
            self.warnings.append(warning_msg)
            results["steps"]["regime_states"] = {"error": str(e)}
            print("✗")
        
        results["completed_at"] = datetime.now(timezone.utc).isoformat()
        results["errors"] = self.errors
        results["warnings"] = self.warnings
        results["info"] = self.info
        
        # Determine overall status
        if self.errors:
            results["status"] = "degraded" if len(self.errors) < len(REQUIRED_REGIME_DRIVERS) else "failed"
        elif self.warnings:
            results["status"] = "partial"
        else:
            results["status"] = "ok"
        
        # Print final summary with clear status
        print("")  # New line after all steps
        
        # Count working vs failed components
        working = []
        degraded = []
        failed = []
        
        for step_name, step_result in results["steps"].items():
            if step_result.get("error"):
                failed.append(step_name)
            elif step_result.get("computed", 0) == 0 and step_name in ["regime_ta", "regime_states"]:
                degraded.append(step_name)
            elif step_result.get("status") == "ok" or step_result.get("computed", 0) > 0:
                working.append(step_name)
            elif "warning" in str(step_result.get("status", "")).lower() or step_result.get("status") == "partial":
                degraded.append(step_name)
        
        # Print summary
        if results["status"] == "ok":
            print(f"   ✓ Bootstrap complete - All systems operational ({len(working)}/{len(results['steps'])} components)")
        elif results["status"] == "partial":
            print(f"   ⚠ Bootstrap complete - {len(working)} working, {len(degraded)} degraded ({len(self.warnings)} warnings)")
            if degraded:
                print(f"      Degraded: {', '.join(degraded[:3])}{'...' if len(degraded) > 3 else ''}")
        elif results["status"] == "degraded":
            print(f"   ⚠ Bootstrap degraded - {len(working)} working, {len(failed)} failed ({len(self.errors)} errors)")
            if failed:
                print(f"      Failed: {', '.join(failed[:3])}{'...' if len(failed) > 3 else ''}")
        else:
            print(f"   ✗ Bootstrap failed - {len(failed)}/{len(results['steps'])} components failed")
            if failed:
                print(f"      Failed: {', '.join(failed[:3])}{'...' if len(failed) > 3 else ''}")
        
        # Show current market state
        self._display_market_summary()
        
        logger.info(f"Bootstrap complete: {results['status']} ({len(working)} working, {len(degraded)} degraded, {len(failed)} failed)")
        return results
    
    def _display_market_summary(self) -> None:
        """Display current market state: prices, regime states, wallet balances."""
        print("")
        print("   ┌─────────────────────────────────────────────────────────────┐")
        print("   │                     MARKET STATE                            │")
        print("   ├─────────────────────────────────────────────────────────────┤")
        
        # Get current prices from regime_price_data_ohlc
        try:
            btc_result = (
                self.sb.table("regime_price_data_ohlc")
                .select("close_usd, timestamp")
                .eq("driver", "BTC")
                .eq("timeframe", "1h")
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            btc_price = f"${float(btc_result.data[0]['close_usd']):,.0f}" if btc_result.data else "N/A"
        except Exception:
            btc_price = "N/A"
        
        # Get ALT composite price
        try:
            alt_result = (
                self.sb.table("regime_price_data_ohlc")
                .select("close_usd, timestamp")
                .eq("driver", "ALT")
                .eq("timeframe", "1h")
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            alt_price = f"${float(alt_result.data[0]['close_usd']):,.0f}" if alt_result.data else "N/A"
        except Exception:
            alt_price = "N/A"
        
        # Get dominance levels (try 1h first, fall back to 1m if not available)
        try:
            btcd_result = (
                self.sb.table("regime_price_data_ohlc")
                .select("close_usd")
                .eq("driver", "BTC.d")
                .eq("timeframe", "1h")
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            if btcd_result.data:
                btc_dom = f"{float(btcd_result.data[0]['close_usd']):.1f}%"
            else:
                # Fall back to 1m data (dominance collected per minute)
                btcd_1m = (
                    self.sb.table("regime_price_data_ohlc")
                    .select("close_usd")
                    .eq("driver", "BTC.d")
                    .eq("timeframe", "1m")
                    .order("timestamp", desc=True)
                    .limit(1)
                    .execute()
                )
                btc_dom = f"{float(btcd_1m.data[0]['close_usd']):.1f}%" if btcd_1m.data else "N/A"
        except Exception:
            btc_dom = "N/A"
        
        try:
            usdtd_result = (
                self.sb.table("regime_price_data_ohlc")
                .select("close_usd")
                .eq("driver", "USDT.d")
                .eq("timeframe", "1h")
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            if usdtd_result.data:
                usdt_dom = f"{float(usdtd_result.data[0]['close_usd']):.1f}%"
            else:
                # Fall back to 1m data
                usdtd_1m = (
                    self.sb.table("regime_price_data_ohlc")
                    .select("close_usd")
                    .eq("driver", "USDT.d")
                    .eq("timeframe", "1m")
                    .order("timestamp", desc=True)
                    .limit(1)
                    .execute()
                )
                usdt_dom = f"{float(usdtd_1m.data[0]['close_usd']):.1f}%" if usdtd_1m.data else "N/A"
        except Exception:
            usdt_dom = "N/A"
        
        print(f"   │  BTC: {btc_price:<12} ALT: {alt_price:<12}                  │")
        print(f"   │  BTC.d: {btc_dom:<10} USDT.d: {usdt_dom:<10}                  │")
        print("   ├─────────────────────────────────────────────────────────────┤")
        
        # Get regime states for drivers - show all timeframes
        try:
            # Query regime driver positions with timeframe
            regime_positions = (
                self.sb.table("lowcap_positions")
                .select("token_ticker, state, timeframe, bars_count, status")
                .eq("status", "regime_driver")
                .execute()
            )
            
            # Group by driver and timeframe
            states_by_tf = {}  # {driver: {timeframe: state}}
            bars_by_tf = {}    # {driver: {timeframe: bars_count}}
            
            if regime_positions.data:
                for pos in regime_positions.data:
                    ticker = pos.get("token_ticker", "")
                    tf = pos.get("timeframe", "")
                    state = pos.get("state", "S4")
                    bars = pos.get("bars_count", 0)
                    
                    if ticker not in states_by_tf:
                        states_by_tf[ticker] = {}
                        bars_by_tf[ticker] = {}
                    states_by_tf[ticker][tf] = state
                    bars_by_tf[ticker][tf] = bars
            
            # Helper to format state with bars check
            def fmt_state(driver: str, tf: str) -> str:
                if driver not in states_by_tf or tf not in states_by_tf[driver]:
                    return "?"
                state = states_by_tf[driver][tf]
                bars = bars_by_tf[driver].get(tf, 0)
                if bars >= 333:
                    return state
                return f"?({bars})"
            
            # Display regime states for key drivers across timeframes
            # Format: Driver: 1m/1h/1d (regime timeframes, now stored directly)
            btc_states = f"BTC: {fmt_state('BTC','1m')}/{fmt_state('BTC','1h')}/{fmt_state('BTC','1d')}"
            alt_states = f"ALT: {fmt_state('ALT','1m')}/{fmt_state('ALT','1h')}/{fmt_state('ALT','1d')}"
            
            print(f"   │  Regime (1m/1h/1d): {btc_states:<18} {alt_states:<18}│")
            
            # Show dominance separately (they have different dynamics)
            btcd_states = f"BTC.d: {fmt_state('BTC.d','1m')}/{fmt_state('BTC.d','1h')}/{fmt_state('BTC.d','1d')}"
            usdtd_states = f"USDT.d: {fmt_state('USDT.d','1m')}/{fmt_state('USDT.d','1h')}/{fmt_state('USDT.d','1d')}"
            print(f"   │  Dominance:         {btcd_states:<18} {usdtd_states:<18}│")
        except Exception as e:
            logger.debug(f"Regime states fetch error: {e}")
            print(f"   │  Regime States: Error ({str(e)[:30]})                    │")
        
        print("   ├─────────────────────────────────────────────────────────────┤")
        
        # Get wallet balance
        try:
            wallet_result = (
                self.sb.table("wallet_balances")
                .select("chain, balance, usdc_balance")
                .eq("chain", "solana")
                .limit(1)
                .execute()
            )
            if wallet_result.data:
                sol_bal = float(wallet_result.data[0].get("balance", 0))
                usdc_bal = float(wallet_result.data[0].get("usdc_balance", 0) or 0)
                print(f"   │  Wallet: {sol_bal:.4f} SOL, ${usdc_bal:,.2f} USDC              │")
            else:
                print("   │  Wallet: No data                                           │")
        except Exception:
            print("   │  Wallet: N/A                                               │")
        
        print("   └─────────────────────────────────────────────────────────────┘")
        print("")
    
    # -------------------------------------------------------------------------
    # Private bootstrap methods
    # -------------------------------------------------------------------------
    
    def _check_database_tables(self) -> Dict[str, Any]:
        """Check that critical database tables exist."""
        required_tables = [
            "regime_price_data_ohlc",
            "lowcap_positions",
            "wallet_balances",
            "majors_price_data_ohlc",
            "lowcap_price_data_ohlc",
            "phase_state",
        ]
        
        missing = []
        existing = []
        
        for table in required_tables:
            try:
                # Check if table exists by selecting with limit 0 (doesn't need specific columns)
                result = self.sb.table(table).select("*").limit(0).execute()
                existing.append(table)
            except Exception as e:
                # Table might not exist or we don't have access
                error_str = str(e).lower()
                if "does not exist" in error_str or "relation" in error_str or "table" in error_str:
                    missing.append(table)
                else:
                    # Other error - assume table exists but query failed
                    existing.append(table)
        
        if missing:
            return {
                "status": "partial",
                "existing": existing,
                "missing_tables": missing,
                "warning": f"Missing tables: {', '.join(missing)}. System may not function correctly."
            }
        else:
            return {
                "status": "ok",
                "existing": existing,
                "missing_tables": [],
            }
    
    def _bootstrap_wallet_balances(self) -> bool:
        """Bootstrap wallet balances by collecting initial balances for all chains.
        
        Note: This checks if data exists. Full wallet balance collection (including USDC)
        happens via scheduled_price_collector which runs after bootstrap completes.
        """
        try:
            # Check if there's existing wallet data
            result = self.sb.table('wallet_balances').select('chain, balance, usdc_balance, last_updated').limit(10).execute()
            
            if result.data:
                # Check if data is recent (within last hour)
                from datetime import datetime, timedelta, timezone
                now = datetime.now(timezone.utc)
                recent_count = 0
                for row in result.data:
                    last_updated_str = row.get('last_updated')
                    if last_updated_str:
                        try:
                            last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
                            if (now - last_updated).total_seconds() < 3600:  # Within last hour
                                recent_count += 1
                        except Exception:
                            pass
                
                if recent_count > 0:
                    logger.info(f"Wallet balances table has {recent_count} recent entries")
                    return True
                else:
                    logger.info("Wallet balances exist but are stale - scheduled_price_collector will refresh")
                    return False
            else:
                # No data - scheduled_price_collector will populate it
                logger.info("Wallet balances table is empty - will be populated by scheduled_price_collector")
                return False
                
        except Exception as e:
            logger.error(f"Wallet balance check failed: {e}", exc_info=True)
            return False
    
    def _check_wallet_balances(self) -> Dict[str, Any]:
        """Check wallet balances table has recent data."""
        try:
            # First verify table exists and is accessible
            try:
                test_result = (
                    self.sb.table("wallet_balances")
                    .select("chain")
                    .limit(1)
                    .execute()
                )
            except Exception as table_error:
                error_str = str(table_error).lower()
                logger.error(f"wallet_balances table access error: {table_error}", exc_info=True)
                if "does not exist" in error_str or "relation" in error_str or "table" in error_str:
                    return {
                        "status": "no_table",
                        "error": str(table_error),
                        "warning": "wallet_balances table does not exist - run wallet_balances_schema.sql"
                    }
                elif "column" in error_str and "does not exist" in error_str:
                    return {
                        "status": "error",
                        "error": str(table_error),
                        "warning": f"Schema mismatch: {str(table_error)[:150]}"
                    }
                # Other error - log full details
                return {
                    "status": "error",
                    "error": str(table_error),
                    "warning": f"Table access error: {str(table_error)[:150]}"
                }
            
            # Table exists, check for data with last_updated
            result = (
                self.sb.table("wallet_balances")
                .select("last_updated")
                .order("last_updated", desc=True)
                .limit(1)
                .execute()
            )
            
            if not result.data:
                return {"status": "no_data", "warning": "No wallet balance data found (table is empty)"}
            
            latest_str = result.data[0].get("last_updated")
            if not latest_str:
                return {"status": "no_data", "warning": "Wallet balances exist but last_updated is null"}
            
            latest = datetime.fromisoformat(latest_str.replace("Z", "+00:00"))
            age_minutes = (datetime.now(timezone.utc) - latest).total_seconds() / 60
            
            if age_minutes > 10:
                return {"status": "stale", "warning": f"Wallet balances {age_minutes:.1f} minutes old"}
            
            return {"status": "ok", "age_minutes": age_minutes}
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Wallet balance check error: {error_msg}", exc_info=True)
            return {"error": error_msg, "status": "error"}
    
    def _check_price_data_collection(self) -> Dict[str, Any]:
        """Check that price data collection is working (majors and lowcaps)."""
        try:
            # Check majors
            majors_result = (
                self.sb.table("majors_price_data_ohlc")
                .select("timestamp")
                .eq("timeframe", "1m")
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            
            # Check lowcaps
            lowcaps_result = (
                self.sb.table("lowcap_price_data_ohlc")
                .select("timestamp")
                .eq("timeframe", "1m")
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            
            status_parts = []
            
            if majors_result.data:
                majors_ts = datetime.fromisoformat(majors_result.data[0]["timestamp"].replace("Z", "+00:00"))
                majors_age = (datetime.now(timezone.utc) - majors_ts).total_seconds() / 60
                if majors_age < 5:
                    status_parts.append("majors:ok")
                else:
                    status_parts.append(f"majors:stale({majors_age:.1f}m)")
            else:
                status_parts.append("majors:no_data")
            
            if lowcaps_result.data:
                lowcaps_ts = datetime.fromisoformat(lowcaps_result.data[0]["timestamp"].replace("Z", "+00:00"))
                lowcaps_age = (datetime.now(timezone.utc) - lowcaps_ts).total_seconds() / 60
                if lowcaps_age < 5:
                    status_parts.append("lowcaps:ok")
                else:
                    status_parts.append(f"lowcaps:stale({lowcaps_age:.1f}m)")
            else:
                status_parts.append("lowcaps:no_data")
            
            return {"status": ", ".join(status_parts)}
        except Exception as e:
            return {"error": str(e)}
    
    def _check_hyperliquid_ws(self) -> Dict[str, Any]:
        """Check Hyperliquid WS - verify actual data flow, not just DB existence."""
        import os
        
        # Check if HL WS is enabled
        if os.getenv("HL_INGEST_ENABLED", "0") != "1":
            return {"status": "disabled", "info": "HL WS not enabled"}
        
        try:
            # Check for recent HL data (within last 5 minutes)
            result = (
                self.sb.table("majors_price_data_ohlc")
                .select("timestamp, source, token_contract")
                .eq("source", "hyperliquid")
                .order("timestamp", desc=True)
                .limit(10)
                .execute()
            )
            
            if not result.data:
                return {"status": "no_data", "warning": "No Hyperliquid data found - WS may not be running"}
            
            # Check most recent data age
            latest_ts = datetime.fromisoformat(result.data[0]["timestamp"].replace("Z", "+00:00"))
            age_minutes = (datetime.now(timezone.utc) - latest_ts).total_seconds() / 60
            
            # Count unique tokens (should have multiple if WS is working)
            unique_tokens = len(set(row["token_contract"] for row in result.data))
            
            if age_minutes < 5:
                return {
                    "status": "ok",
                    "age_minutes": age_minutes,
                    "tokens": unique_tokens,
                    "info": f"HL WS active ({unique_tokens} tokens, {age_minutes:.1f}m old)"
                }
            elif age_minutes < 30:
                return {
                    "status": "stale",
                    "warning": f"HL data {age_minutes:.1f} minutes old - WS may be slow",
                    "tokens": unique_tokens
                }
            else:
                return {
                    "status": "no_data",
                    "warning": f"HL data {age_minutes:.1f} minutes old - WS likely not running",
                    "tokens": unique_tokens
                }
        except Exception as e:
            logger.error(f"HL WS check error: {e}", exc_info=True)
            return {"error": str(e), "status": "error"}
    
    def _bootstrap_regime_positions(self) -> Dict[str, Any]:
        """Ensure all regime driver positions exist."""
        from src.intelligence.lowcap_portfolio_manager.jobs.regime_ta_tracker import (
            RegimeTATracker,
        )
        
        created = []
        missing_required = []
        missing_optional = []
        
        # Map regime TF to position TF (now that schema allows '1d', we use it directly)
        tf_map = {"1d": "1d", "1h": "1h", "1m": "1m"}
        
        for driver in REQUIRED_REGIME_DRIVERS + OPTIONAL_REGIME_DRIVERS:
            for regime_tf in REGIME_TIMEFRAMES:
                position_tf = tf_map[regime_tf]
                
                # Check if position exists
                result = (
                    self.sb.table("lowcap_positions")
                    .select("id")
                    .eq("token_ticker", driver)
                    .eq("timeframe", position_tf)
                    .eq("status", "regime_driver")
                    .eq("book_id", self.book_id)
                    .limit(1)
                    .execute()
                )
                
                if not result.data:
                    # Create position using RegimeTATracker helper
                    try:
                        tracker = RegimeTATracker(timeframe=regime_tf, book_id=self.book_id)
                        position = tracker._ensure_regime_position(driver)
                        if position:
                            created.append(f"{driver}/{regime_tf}")
                        else:
                            if driver in REQUIRED_REGIME_DRIVERS:
                                missing_required.append(f"{driver}/{regime_tf}")
                            else:
                                missing_optional.append(f"{driver}/{regime_tf}")
                    except Exception as e:
                        logger.error(f"Failed to create {driver}/{regime_tf}: {e}")
                        if driver in REQUIRED_REGIME_DRIVERS:
                            missing_required.append(f"{driver}/{regime_tf}")
                        else:
                            missing_optional.append(f"{driver}/{regime_tf}")
        
        status_parts = []
        if created:
            status_parts.append(f"created:{len(created)}")
        if missing_required:
            status_parts.append(f"missing_required:{len(missing_required)}")
        if missing_optional:
            status_parts.append(f"missing_optional:{len(missing_optional)}")
        
        return {
            "status": ", ".join(status_parts) if status_parts else "ok",
            "created": created,
            "missing_required": missing_required,
            "missing_optional": missing_optional,
        }
    
    def _bootstrap_regime_price_data(self) -> Dict[str, Any]:
        """Bootstrap regime price data (actively backfill, check for gaps, get current data)."""
        from src.intelligence.lowcap_portfolio_manager.jobs.regime_price_collector import (
            RegimePriceCollector,
        )
        
        collector = RegimePriceCollector(book_id=self.book_id)
        status_parts = []
        gaps_found = []
        backfilled_bars = 0
        errors = []
        
        # Check all drivers for gaps and backfill needs
        for driver in REQUIRED_REGIME_DRIVERS + OPTIONAL_REGIME_DRIVERS:
            for tf in REGIME_TIMEFRAMES:
                # Check for gaps in data
                gaps = self._check_data_gaps(driver, tf)
                if gaps:
                    gaps_found.extend([f"{driver}/{tf}:{g}" for g in gaps])
                
                # Check if we need backfill for majors (BTC, SOL, ETH, BNB)
                # Only check BTC - if BTC needs backfill, backfill all majors at once
                if driver == "BTC":
                    needs_backfill, days_needed = self._check_backfill_needed(driver, tf)
                    if needs_backfill:
                        # Backfill all majors from Binance (BTC, SOL, ETH, BNB)
                        stop_progress = None
                        try:
                            logger.info(f"Backfilling majors/{tf} ({days_needed} days)...")
                            # Show progress indicator
                            stop_progress = self._show_backfill_progress("majors", tf, days_needed)
                            backfill_result = collector.backfill_majors_from_binance(days=days_needed, timeframes=[tf])
                            # Stop progress indicator
                            if stop_progress:
                                stop_progress.set()
                                time.sleep(0.3)  # Let last glyph show
                            bars_written = backfill_result.get("bars_written", 0)
                            backfilled_bars += bars_written
                            if bars_written > 0:
                                status_parts.append(f"majors/{tf}:backfilled({bars_written} bars)")
                            else:
                                status_parts.append(f"majors/{tf}:backfill_no_bars")
                        except Exception as e:
                            # Stop progress indicator on error
                            if stop_progress:
                                stop_progress.set()
                                time.sleep(0.2)  # Let progress clear
                            logger.warning(f"Backfill failed for majors/{tf}: {e}", exc_info=True)
                            status_parts.append(f"majors/{tf}:backfill_failed")
                            errors.append(f"majors/{tf}: {str(e)[:100]}")
        
        # Compute ALT composite from backfilled data
        alt_errors = []
        if backfilled_bars > 0:
            for tf in REGIME_TIMEFRAMES:
                try:
                    collector._compute_alt_composite(tf, days=90)
                    status_parts.append(f"ALT/{tf}:computed")
                except Exception as e:
                    error_msg = f"ALT/{tf}: {str(e)[:100]}"
                    logger.warning(f"ALT composite computation failed for {tf}: {e}", exc_info=True)
                    alt_errors.append(error_msg)
                    status_parts.append(f"ALT/{tf}:failed")
            if not alt_errors:
                status_parts.append("ALT:all_computed")
        else:
            alt_errors.append("No backfilled bars - cannot compute ALT composite")
            status_parts.append("ALT:skipped_no_backfill")
        
        # Collect current prices for all timeframes
        for tf in REGIME_TIMEFRAMES:
            try:
                collector.run(timeframe=tf)
                status_parts.append(f"current_{tf}:collected")
            except Exception as e:
                logger.warning(f"Current {tf} collection failed: {e}")
                status_parts.append(f"current_{tf}:failed")
        
        # Collect dominance (1m only) and roll up to 1h/1d
        try:
            # First collect dominance at 1m (only collected when timeframe=1m)
            collector.run(timeframe="1m")
            # Then roll up to 1h and 1d
            collector.rollup_dominance_to_ohlc("1h")
            collector.rollup_dominance_to_ohlc("1d")
            status_parts.append("dominance:collected_and_rolled_up")
        except Exception as e:
            logger.warning(f"Dominance collection/rollup failed: {e}")
            status_parts.append(f"dominance:failed({str(e)[:30]})")
        
        if gaps_found:
            status_parts.append(f"gaps:{len(gaps_found)}")
        
        return {
            "status": ", ".join(status_parts) if status_parts else "ok",
            "backfilled_bars": backfilled_bars,
            "gaps": gaps_found,
        }
    
    def _check_data_gaps(self, driver: str, timeframe: str) -> List[str]:
        """Check for gaps in regime price data."""
        gaps = []
        try:
            result = (
                self.sb.table("regime_price_data_ohlc")
                .select("timestamp")
                .eq("driver", driver)
                .eq("timeframe", timeframe)
                .eq("book_id", self.book_id)
                .order("timestamp", desc=False)
                .limit(1000)  # Check recent 1000 bars
                .execute()
            )
            
            if len(result.data) < 2:
                return gaps
            
            # Calculate expected interval
            interval_seconds = {"1m": 60, "1h": 3600, "1d": 86400}.get(timeframe, 3600)
            
            for i in range(1, len(result.data)):
                prev_ts = datetime.fromisoformat(result.data[i-1]["timestamp"].replace("Z", "+00:00"))
                curr_ts = datetime.fromisoformat(result.data[i]["timestamp"].replace("Z", "+00:00"))
                gap_seconds = (curr_ts - prev_ts).total_seconds()
                
                # Allow 10% tolerance
                if gap_seconds > interval_seconds * 1.1:
                    gap_count = int(gap_seconds / interval_seconds) - 1
                    if gap_count > 0:
                        gaps.append(f"{gap_count} missing")
        except Exception as e:
            logger.debug(f"Gap check failed for {driver}/{timeframe}: {e}")
        
        return gaps
    
    def _show_backfill_progress(self, driver: str, timeframe: str, days: int) -> threading.Event:
        """Show animated glyph progress indicator for backfill.
        
        Returns:
            threading.Event that can be set to stop the progress indicator
        """
        # Start progress indicator in background thread
        stop_progress = threading.Event()
        
        def progress_loop():
            glyph_idx = 0
            while not stop_progress.is_set():
                glyph = GLYPH_STREAM[glyph_idx % len(GLYPH_STREAM)]
                sys.stdout.write(f"\r   ⨳ Bootstrapping regime price data... {driver}/{timeframe} {glyph}")
                sys.stdout.flush()
                glyph_idx += 1
                if stop_progress.wait(0.2):  # Update every 200ms
                    break
            # Clear the progress line when done
            sys.stdout.write("\r   ⨳ Bootstrapping regime price data...")
            sys.stdout.flush()
        
        progress_thread = threading.Thread(target=progress_loop, daemon=True)
        progress_thread.start()
        
        return stop_progress
    
    def _check_backfill_needed(self, driver: str, timeframe: str) -> Tuple[bool, int]:
        """Check if backfill is needed and how many days (capped at MAX_BARS_TO_BACKFILL)."""
        try:
            # Check bar count
            count_result = (
                self.sb.table("regime_price_data_ohlc")
                .select("timestamp", count="exact")
                .eq("driver", driver)
                .eq("timeframe", timeframe)
                .eq("book_id", self.book_id)
                .execute()
            )
            bar_count = count_result.count if hasattr(count_result, "count") else 0
            min_bars = MIN_BARS_FOR_UPTREND.get(timeframe, 333)
            max_bars = MAX_BARS_TO_BACKFILL.get(timeframe, 666)
            
            # Need backfill if we have less than minimum bars
            if bar_count < min_bars:
                # Calculate days needed to reach max_bars (not min_bars, to have buffer)
                bars_needed = max_bars - bar_count
                
                # Convert bars to days based on timeframe
                if timeframe == "1m":
                    days_needed = max(1, int(bars_needed / (24 * 60)))  # At least 1 day
                elif timeframe == "1h":
                    days_needed = max(1, int(bars_needed / 24))  # At least 1 day
                elif timeframe == "1d":
                    days_needed = max(1, bars_needed)  # At least 1 day
                else:
                    days_needed = 1
                
                # Cap at reasonable limits
                days_needed = min(days_needed, {"1m": 2, "1h": 30, "1d": 730}.get(timeframe, 30))
                return True, days_needed
            
            return False, 0
        except Exception:
            # Default: backfill enough for min_bars
            min_bars = MIN_BARS_FOR_UPTREND.get(timeframe, 333)
            if timeframe == "1m":
                return True, 1  # 1 day = 1440 bars, enough for min
            elif timeframe == "1h":
                return True, 15  # 15 days = 360 bars, enough for min
            else:  # 1d
                return True, 365  # 1 year = 365 bars, enough for min
    
    def _run_regime_ta_computation(self) -> Dict[str, Any]:
        """Actually RUN regime TA computation and verify results."""
        from src.intelligence.lowcap_portfolio_manager.jobs.regime_ta_tracker import (
            RegimeTATracker,
        )
        
        computed = 0
        failed = []
        insufficient_data = []
        
        for tf in REGIME_TIMEFRAMES:
            try:
                tracker = RegimeTATracker(timeframe=tf, book_id=self.book_id)
                updated = tracker.run()
                computed += updated
                
                if updated == 0:
                    # Check why nothing was computed
                    for driver in REQUIRED_REGIME_DRIVERS:
                        bar_count = self._count_regime_bars(driver, tf)
                        min_bars = MIN_BARS_FOR_UPTREND.get(tf, 333)
                        if bar_count < min_bars:
                            insufficient_data.append(f"{driver}/{tf}({bar_count}/{min_bars} bars)")
            except Exception as e:
                logger.error(f"TA computation failed for {tf}: {e}", exc_info=True)
                failed.append(f"{tf}:{str(e)[:50]}")
        
        status_parts = []
        if computed > 0:
            status_parts.append(f"computed:{computed}")
        if failed:
            status_parts.append(f"failed:{len(failed)}")
        if insufficient_data:
            status_parts.append(f"insufficient_data:{len(insufficient_data)}")
        
        return {
            "status": ", ".join(status_parts) if status_parts else "ok",
            "computed": computed,
            "failed": failed,
            "insufficient_data": insufficient_data,
        }
    
    def _check_regime_ta(self) -> Dict[str, Any]:
        """Check that regime TA is computed (or can be computed)."""
        status_parts = []
        
        for driver in REQUIRED_REGIME_DRIVERS:
            for tf in REGIME_TIMEFRAMES:
                # Check if TA exists
                result = (
                    self.sb.table("lowcap_positions")
                    .select("features")
                    .eq("token_ticker", driver)
                    .eq("timeframe", {"1d": "1d", "1h": "1h", "1m": "1m"}[tf])
                    .eq("status", "regime_driver")
                    .eq("book_id", self.book_id)
                    .limit(1)
                    .execute()
                )
                
                if result.data:
                    features = result.data[0].get("features") or {}
                    ta = features.get("ta") or {}
                    if ta:
                        status_parts.append(f"{driver}/{tf}:ok")
                    else:
                        # Check if we have enough bars to compute TA
                        bar_count = self._count_regime_bars(driver, tf)
                        min_bars = MIN_BARS_FOR_UPTREND.get(tf, 333)
                        if bar_count >= min_bars:
                            status_parts.append(f"{driver}/{tf}:needs_compute({bar_count} bars)")
                        else:
                            status_parts.append(f"{driver}/{tf}:insufficient_data({bar_count}/{min_bars})")
                else:
                    status_parts.append(f"{driver}/{tf}:no_position")
        
        return {"status": ", ".join(status_parts)}
    
    def _run_regime_state_computation(self) -> Dict[str, Any]:
        """Actually RUN regime state computation (uptrend engine) and verify results."""
        from src.intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v4 import (
            UptrendEngineV4,
        )
        
        computed = 0
        failed = []
        
        # Map regime TF to position TF (now that schema allows '1d', we use it directly)
        tf_map = {"1d": "1d", "1h": "1h", "1m": "1m"}
        
        for regime_tf in REGIME_TIMEFRAMES:
            position_tf = tf_map[regime_tf]
            try:
                engine = UptrendEngineV4(timeframe=position_tf)
                updated = engine.run(include_regime_drivers=True)
                computed += updated
            except Exception as e:
                logger.error(f"Uptrend engine failed for {regime_tf}: {e}", exc_info=True)
                failed.append(f"{regime_tf}:{str(e)[:50]}")
        
        status_parts = []
        if computed > 0:
            status_parts.append(f"computed:{computed}")
        if failed:
            status_parts.append(f"failed:{len(failed)}")
        
        return {
            "status": ", ".join(status_parts) if status_parts else "ok",
            "computed": computed,
            "failed": failed,
        }
    
    def _check_regime_states(self) -> Dict[str, Any]:
        """Check that regime states are computed (or can be computed)."""
        status_parts = []
        
        for driver in REQUIRED_REGIME_DRIVERS:
            for tf in REGIME_TIMEFRAMES:
                result = (
                    self.sb.table("lowcap_positions")
                    .select("features, state")
                    .eq("token_ticker", driver)
                    .eq("timeframe", {"1d": "1d", "1h": "1h", "1m": "1m"}[tf])
                    .eq("status", "regime_driver")
                    .eq("book_id", self.book_id)
                    .limit(1)
                    .execute()
                )
                
                if result.data:
                    features = result.data[0].get("features") or {}
                    uptrend = features.get("uptrend_engine_v4") or {}
                    state = uptrend.get("state") or result.data[0].get("state") or "unknown"
                    
                    if state != "unknown":
                        status_parts.append(f"{driver}/{tf}:{state}")
                    else:
                        status_parts.append(f"{driver}/{tf}:no_state")
                else:
                    status_parts.append(f"{driver}/{tf}:no_position")
        
        return {"status": ", ".join(status_parts)}
    
    def _count_regime_bars(self, driver: str, timeframe: str) -> int:
        """Count regime bars for a driver/timeframe."""
        try:
            result = (
                self.sb.table("regime_price_data_ohlc")
                .select("timestamp", count="exact")
                .eq("driver", driver)
                .eq("timeframe", timeframe)
                .eq("book_id", self.book_id)
                .execute()
            )
            return result.count if hasattr(result, "count") else 0
        except Exception:
            return 0
    
    def _update_regime_bars_count(self) -> Dict[str, Any]:
        """Update bars_count for all regime driver positions based on regime_price_data_ohlc."""
        updated = 0
        errors = []
        
        # Map regime TF to position TF (now that schema allows '1d', we use it directly)
        tf_map = {"1d": "1d", "1h": "1h", "1m": "1m"}
        
        for driver in REQUIRED_REGIME_DRIVERS + OPTIONAL_REGIME_DRIVERS:
            for regime_tf in REGIME_TIMEFRAMES:
                position_tf = tf_map[regime_tf]
                
                try:
                    # Count bars in regime_price_data_ohlc
                    bars_count = self._count_regime_bars(driver, regime_tf)
                    
                    # Find the regime driver position
                    result = (
                        self.sb.table("lowcap_positions")
                        .select("id, bars_count")
                        .eq("token_ticker", driver)
                        .eq("timeframe", position_tf)
                        .eq("status", "regime_driver")
                        .eq("book_id", self.book_id)
                        .limit(1)
                        .execute()
                    )
                    
                    if result.data:
                        position_id = result.data[0]["id"]
                        current_bars_count = result.data[0].get("bars_count", 0)
                        
                        # Only update if different
                        if bars_count != current_bars_count:
                            self.sb.table("lowcap_positions").update({
                                "bars_count": bars_count
                            }).eq("id", position_id).execute()
                            updated += 1
                            logger.debug(f"Updated bars_count for {driver}/{regime_tf}: {current_bars_count} → {bars_count}")
                    else:
                        # Position doesn't exist - should have been created in _bootstrap_regime_positions
                        logger.warning(f"Regime driver position not found: {driver}/{position_tf}")
                        errors.append(f"{driver}/{regime_tf}:no_position")
                        
                except Exception as e:
                    error_msg = f"{driver}/{regime_tf}: {str(e)[:50]}"
                    logger.error(f"Failed to update bars_count for {driver}/{regime_tf}: {e}", exc_info=True)
                    errors.append(error_msg)
        
        status_parts = []
        if updated > 0:
            status_parts.append(f"updated:{updated}")
        if errors:
            status_parts.append(f"errors:{len(errors)}")
        
        return {
            "status": ", ".join(status_parts) if status_parts else "ok",
            "updated": updated,
            "errors": errors,
        }


def main() -> None:
    """CLI entry point for bootstrap."""
    import argparse
    
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="Bootstrap System")
    args = parser.parse_args()
    
    bootstrap = BootstrapSystem()
    results = bootstrap.bootstrap_all()
    
    print("\n" + "=" * 70)
    print("BOOTSTRAP RESULTS")
    print("=" * 70)
    print(f"\nStatus: {results['status']}")
    
    if results.get("info"):
        print("\n✓ Info:")
        for msg in results["info"]:
            print(f"  {msg}")
    
    if results.get("warnings"):
        print("\n⚠ Warnings:")
        for msg in results["warnings"]:
            print(f"  {msg}")
    
    if results.get("errors"):
        print("\n✗ Errors:")
        for msg in results["errors"]:
            print(f"  {msg}")
    
    print("\n" + "=" * 70)
    
    # Exit with error code if critical failures
    if results["status"] == "failed":
        exit(1)


if __name__ == "__main__":
    main()

