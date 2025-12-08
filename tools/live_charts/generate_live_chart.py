#!/usr/bin/env python3
"""
Generate live charts for positions to verify EMAs, geometry, and state.

Usage:
    # By position ID
    python3 generate_live_chart.py --position-id 123

    # By contract address (all timeframes for that token)
    python3 generate_live_chart.py --contract 0xABC... --chain solana

    # By contract + specific timeframe
    python3 generate_live_chart.py --contract 0xABC... --chain solana --timeframe 1h

    # All positions (watchlist + active)
    python3 generate_live_chart.py --all

    # All positions for a specific timeframe
    python3 generate_live_chart.py --all --timeframe 1h

    # By ticker symbol
    python3 generate_live_chart.py --ticker DREAMS --timeframe 1h

    # By stage/state
    python3 generate_live_chart.py --all --stage S3
    python3 generate_live_chart.py --all --timeframe 1h --stage S3
    
    # Combinations: timeframe + stage
    python3 generate_live_chart.py --all --timeframe 1m --stage S3
    python3 generate_live_chart.py --all --timeframe 15m --stage S2
    python3 generate_live_chart.py --all --timeframe 4h --stage S0
"""

from __future__ import annotations

import os
import sys
import argparse
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import matplotlib.pyplot as plt  # type: ignore
import matplotlib.dates as mdates  # type: ignore
from supabase import create_client, Client  # type: ignore
from dotenv import load_dotenv  # type: ignore

from src.intelligence.lowcap_portfolio_manager.jobs.ta_utils import ema_series

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _forward_fill_prices(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Forward-fill missing or zero OHLC prices from the last valid price."""
    filled_rows = []
    last_valid_price = None
    
    for r in rows:
        filled_r = dict(r)
        close_val = float(r.get("close_usd") or 0.0)
        if close_val > 0:
            last_valid_price = close_val
        
        if last_valid_price and last_valid_price > 0:
            if float(r.get("open_usd") or 0.0) <= 0:
                filled_r["open_usd"] = last_valid_price
            if float(r.get("high_usd") or 0.0) <= 0:
                filled_r["high_usd"] = last_valid_price
            if float(r.get("low_usd") or 0.0) <= 0:
                filled_r["low_usd"] = last_valid_price
            if float(r.get("close_usd") or 0.0) <= 0:
                filled_r["close_usd"] = last_valid_price
        
        filled_rows.append(filled_r)
    
    return filled_rows


class LiveChartGenerator:
    """Generate charts for live positions to verify EMAs, geometry, and state."""
    
    def __init__(self):
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(url, key)
        self.output_dir = os.path.join(project_root, "tools", "live_charts", "output")
        os.makedirs(self.output_dir, exist_ok=True)
    
    def fetch_ohlc(self, contract: str, chain: str, timeframe: str, limit: int = 400) -> List[Dict[str, Any]]:
        """Fetch OHLC bars for a specific timeframe."""
        rows = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, open_usd, high_usd, low_usd, close_usd, volume")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", timeframe)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        rows.reverse()
        return _forward_fill_prices(rows)
    
    def get_positions(
        self,
        position_id: Optional[int] = None,
        contract: Optional[str] = None,
        chain: Optional[str] = None,
        ticker: Optional[str] = None,
        timeframe: Optional[str] = None,
        stage: Optional[str] = None,
        all_positions: bool = False,
        include_regime: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get positions based on query parameters."""
        query = (
            self.sb.table("lowcap_positions")
            .select("id,token_contract,token_chain,token_ticker,timeframe,features,status")
        )
        
        if position_id:
            query = query.eq("id", position_id)
        elif contract and chain:
            query = query.eq("token_contract", contract).eq("token_chain", chain)
            if timeframe:
                query = query.eq("timeframe", timeframe)
        elif ticker:
            query = query.eq("token_ticker", ticker.upper())
            if timeframe:
                query = query.eq("timeframe", timeframe)
        elif all_positions:
            statuses = ["watchlist", "active"]
            if include_regime:
                statuses.append("regime_driver")
            query = query.in_("status", statuses)
            if timeframe:
                query = query.eq("timeframe", timeframe)
        elif include_regime:
            # If explicitly asking for regime positions without --all, fetch regime drivers
            query = query.eq("status", "regime_driver")
            if timeframe:
                query = query.eq("timeframe", timeframe)
        else:
            return []
        
        res = query.limit(2000).execute()
        positions = res.data or []
        
        # Filter by stage if specified (check features.uptrend_engine_v4.state)
        if stage:
            filtered = []
            for pos in positions:
                features = pos.get("features") or {}
                uptrend = features.get("uptrend_engine_v4") or {}
                current_state = uptrend.get("state", "")
                if current_state.upper() == stage.upper():
                    filtered.append(pos)
            return filtered
        
        return positions
    
    def verify_emas(
        self,
        computed_emas: Dict[str, float],
        stored_ta: Dict[str, Any],
        timeframe: str
    ) -> Dict[str, Any]:
        """Verify computed EMAs match stored values from features.ta."""
        ta_suffix = f"_{timeframe}" if timeframe != "1h" else ""
        stored_ema = stored_ta.get("ema", {})
        
        verification = {
            "matches": {},
            "mismatches": {},
            "missing": []
        }
        
        ema_keys = ["ema20", "ema30", "ema60", "ema144", "ema250", "ema333"]
        for key in ema_keys:
            stored_key = f"{key}{ta_suffix}"
            stored_val = stored_ema.get(stored_key)
            computed_val = computed_emas.get(key)
            
            if stored_val is None:
                verification["missing"].append(key)
            elif computed_val is None:
                verification["missing"].append(key)
            else:
                stored_val = float(stored_val)
                computed_val = float(computed_val)
                diff_pct = abs(stored_val - computed_val) / max(stored_val, 1e-9) * 100
                
                # Allow 0.1% tolerance for floating point differences
                if diff_pct < 0.1:
                    verification["matches"][key] = {
                        "stored": stored_val,
                        "computed": computed_val,
                        "diff_pct": diff_pct
                    }
                else:
                    verification["mismatches"][key] = {
                        "stored": stored_val,
                        "computed": computed_val,
                        "diff_pct": diff_pct
                    }
        
        return verification
    
    def generate_chart(
        self,
        position: Dict[str, Any],
        ohlc_rows: List[Dict[str, Any]],
        verification: Dict[str, Any]
    ) -> Optional[str]:
        """Generate chart for a single position."""
        contract = position.get("token_contract", "")
        chain = position.get("token_chain", "")
        ticker = position.get("token_ticker", "") or contract[:20]
        timeframe = position.get("timeframe", "1h")
        features = position.get("features") or {}
        
        # Build chart data
        chart_times: List[datetime] = []
        chart_closes: List[float] = []
        
        for r in ohlc_rows:
            ts_str = str(r.get("timestamp", ""))
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                close = float(r.get("close_usd") or 0.0)
                if close > 0:
                    chart_times.append(ts)
                    chart_closes.append(close)
            except Exception:
                continue
        
        if not chart_times or not chart_closes:
            logger.warning(f"No valid OHLC data for {ticker} ({timeframe})")
            return None
        
        # Recompute EMAs from OHLC
        ema20_chart = ema_series(chart_closes, 20)
        ema30_chart = ema_series(chart_closes, 30)
        ema60_chart = ema_series(chart_closes, 60)
        ema144_chart = ema_series(chart_closes, 144)
        ema250_chart = ema_series(chart_closes, 250)
        ema333_chart = ema_series(chart_closes, 333)
        
        computed_emas = {
            "ema20": ema20_chart[-1] if ema20_chart else 0.0,
            "ema30": ema30_chart[-1] if ema30_chart else 0.0,
            "ema60": ema60_chart[-1] if ema60_chart else 0.0,
            "ema144": ema144_chart[-1] if ema144_chart else 0.0,
            "ema250": ema250_chart[-1] if ema250_chart else 0.0,
            "ema333": ema333_chart[-1] if ema333_chart else 0.0,
        }
        
        # Get current state from features
        uptrend = features.get("uptrend_engine_v4") or {}
        current_state = uptrend.get("state", "Unknown")
        current_price = float(uptrend.get("price", chart_closes[-1] if chart_closes else 0.0))
        
        # Get S/R levels from geometry
        geometry = features.get("geometry") or {}
        geom_levels = ((geometry.get("levels") or {}).get("sr_levels") or [])
        sr_levels: List[Dict[str, Any]] = []
        seen_prices = set()
        for geom_lvl in geom_levels[:10]:  # Top 10 S/R levels
            price = float(geom_lvl.get("price", geom_lvl.get("price_native_raw", 0.0)))
            if price > 0 and price not in seen_prices:
                strength = float(geom_lvl.get("strength", 10))
                sr_levels.append({"price": price, "strength": strength})
                seen_prices.add(price)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(24, 14))
        
        # Plot price
        ax.plot(chart_times, chart_closes, "k-", linewidth=1.5, label="Price", alpha=0.8, zorder=1)
        
        # Get y-axis range
        y_min, y_max = ax.get_ylim()
        
        # Plot EMAs
        ax.plot(chart_times, ema20_chart, "b-", linewidth=1, label="EMA20", alpha=0.6, zorder=1)
        ax.plot(chart_times, ema30_chart, "b-", linewidth=1, label="EMA30", alpha=0.6, zorder=1)
        ax.plot(chart_times, ema60_chart, "g-", linewidth=1.5, label="EMA60", alpha=0.7, zorder=1)
        ax.plot(chart_times, ema144_chart, "orange", linewidth=1.5, label="EMA144", alpha=0.7, zorder=1)
        ax.plot(chart_times, ema250_chart, "r-", linewidth=1.5, label="EMA250", alpha=0.7, zorder=1)
        ax.plot(chart_times, ema333_chart, "purple", linewidth=2, label="EMA333", alpha=0.8, zorder=1)
        
        # Plot S/R levels
        for sr in sr_levels:
            price = sr.get("price", 0.0)
            strength = sr.get("strength", 0)
            ax.axhline(y=price, color='blue', linestyle='--', alpha=0.4, linewidth=0.8, zorder=2)
            if price > 0 and len(chart_times) > 0:
                ax.text(chart_times[-1], price, f' S/R:{int(strength)}', 
                       verticalalignment='center', fontsize=7, color='blue', alpha=0.6)
        
        # Mark current state
        if current_price > 0 and len(chart_times) > 0:
            state_colors = {
                "S0": "red",
                "S1": "blue",
                "S2": "orange",
                "S3": "green",
            }
            state_color = state_colors.get(current_state, "gray")
            ax.scatter([chart_times[-1]], [current_price], c=state_color, marker="*", 
                      s=500, alpha=0.9, zorder=10, edgecolors="black", linewidths=2,
                      label=f"Current State: {current_state}")
        
        # Add verification text
        verification_text = []
        if verification.get("mismatches"):
            verification_text.append("⚠ EMA MISMATCHES:")
            for key, data in verification["mismatches"].items():
                verification_text.append(
                    f"  {key}: stored={data['stored']:.6f}, computed={data['computed']:.6f} "
                    f"(diff={data['diff_pct']:.2f}%)"
                )
        if verification.get("missing"):
            verification_text.append(f"⚠ Missing EMAs: {', '.join(verification['missing'])}")
        if verification.get("matches") and not verification.get("mismatches"):
            verification_text.append("✅ All EMAs match stored values")
        
        if verification_text:
            ax.text(0.02, 0.98, "\n".join(verification_text), transform=ax.transAxes,
                   fontsize=9, verticalalignment='top', bbox=dict(boxstyle='round', 
                   facecolor='wheat', alpha=0.8))
        
        # Add current EMA values as text
        ema_text = f"Current EMAs:\n"
        for key, val in computed_emas.items():
            ema_text += f"{key}: {val:.6f}\n"
        ax.text(0.98, 0.02, ema_text, transform=ax.transAxes,
               fontsize=8, verticalalignment='bottom', horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        ax.set_xlabel("Time", fontsize=12)
        ax.set_ylabel("Price (USD)", fontsize=12)
        title = f"Live Position Chart - {ticker} ({timeframe})"
        if current_state != "Unknown":
            title += f" - State: {current_state}"
        ax.set_title(title, fontsize=16, fontweight="bold")
        
        ax.legend(loc="upper left", fontsize=9, ncol=2, framealpha=0.9)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
        
        # Adjust x-axis locator based on timeframe
        if timeframe == "1m":
            ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
        elif timeframe == "15m":
            ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=60))
        elif timeframe == "1h":
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
        elif timeframe == "4h":
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save chart
        timestamp = int(_now_utc().timestamp())
        filename = f"live_chart_{ticker}_{timeframe}_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches="tight")
        plt.close()
        
        return filepath
    
    def generate_charts(
        self,
        position_id: Optional[int] = None,
        contract: Optional[str] = None,
        chain: Optional[str] = None,
        ticker: Optional[str] = None,
        timeframe: Optional[str] = None,
        stage: Optional[str] = None,
        all_positions: bool = False,
        include_regime: bool = False,
    ) -> List[str]:
        """Generate charts for positions matching query parameters."""
        positions = self.get_positions(
            position_id=position_id,
            contract=contract,
            chain=chain,
            ticker=ticker,
            timeframe=timeframe,
            stage=stage,
            all_positions=all_positions,
            include_regime=include_regime,
        )
        
        if not positions:
            logger.warning("No positions found matching query parameters")
            return []
        
        logger.info(f"Found {len(positions)} position(s) to chart")
        
        chart_paths = []
        for pos in positions:
            try:
                contract = pos.get("token_contract", "")
                chain = pos.get("token_chain", "")
                timeframe = pos.get("timeframe", "1h")
                ticker = pos.get("token_ticker", "") or contract[:20]
                features = pos.get("features") or {}
                
                logger.info(f"Generating chart for {ticker} ({timeframe})...")
                
                # Fetch OHLC data
                ohlc_rows = self.fetch_ohlc(contract, chain, timeframe, limit=400)
                if not ohlc_rows:
                    logger.warning(f"No OHLC data for {ticker} ({timeframe})")
                    continue
                
                # Recompute EMAs for verification
                closes = [float(r.get("close_usd", 0.0)) for r in ohlc_rows if float(r.get("close_usd", 0.0)) > 0]
                if not closes:
                    logger.warning(f"No valid closes for {ticker} ({timeframe})")
                    continue
                
                computed_emas = {
                    "ema20": ema_series(closes, 20)[-1] if len(closes) >= 20 else 0.0,
                    "ema30": ema_series(closes, 30)[-1] if len(closes) >= 30 else 0.0,
                    "ema60": ema_series(closes, 60)[-1] if len(closes) >= 60 else 0.0,
                    "ema144": ema_series(closes, 144)[-1] if len(closes) >= 144 else 0.0,
                    "ema250": ema_series(closes, 250)[-1] if len(closes) >= 250 else 0.0,
                    "ema333": ema_series(closes, 333)[-1] if len(closes) >= 333 else 0.0,
                }
                
                # Verify EMAs
                ta = features.get("ta") or {}
                verification = self.verify_emas(computed_emas, ta, timeframe)
                
                # Generate chart
                chart_path = self.generate_chart(pos, ohlc_rows, verification)
                if chart_path:
                    chart_paths.append(chart_path)
                    logger.info(f"✅ Generated chart: {os.path.basename(chart_path)}")
                    
                    # Log verification results
                    if verification.get("mismatches"):
                        logger.warning(f"⚠ EMA mismatches for {ticker} ({timeframe}): {verification['mismatches']}")
                    elif verification.get("matches"):
                        logger.info(f"✅ All EMAs verified for {ticker} ({timeframe})")
                
            except Exception as e:
                logger.error(f"Error generating chart for position {pos.get('id')}: {e}", exc_info=True)
        
        return chart_paths


def main():
    parser = argparse.ArgumentParser(description="Generate live charts for positions")
    parser.add_argument("--position-id", type=int, help="Position ID")
    parser.add_argument("--contract", type=str, help="Token contract address")
    parser.add_argument("--chain", type=str, help="Token chain (solana, ethereum, base, bsc)")
    parser.add_argument("--ticker", type=str, help="Token ticker symbol")
    parser.add_argument("--timeframe", type=str, choices=["1m", "15m", "1h", "4h"], help="Timeframe filter")
    parser.add_argument("--stage", type=str, choices=["S0", "S1", "S2", "S3"], help="Filter by state/stage")
    parser.add_argument("--regime", action="store_true", help="Include regime_driver positions")
    parser.add_argument("--all", action="store_true", help="Generate charts for all positions")
    
    args = parser.parse_args()
    
    if not any([args.position_id, args.contract, args.ticker, args.all]):
        parser.print_help()
        sys.exit(1)
    
    if args.contract and not args.chain:
        logger.error("--chain is required when using --contract")
        sys.exit(1)
    
    try:
        generator = LiveChartGenerator()
        chart_paths = generator.generate_charts(
            position_id=args.position_id,
            contract=args.contract,
            chain=args.chain,
            ticker=args.ticker,
            timeframe=args.timeframe,
            stage=args.stage,
            all_positions=args.all,
            include_regime=args.regime,
        )
        
        if chart_paths:
            print(f"\n✅ Generated {len(chart_paths)} chart(s):")
            for path in chart_paths:
                print(f"  {path}")
        else:
            print("\n⚠ No charts generated")
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

