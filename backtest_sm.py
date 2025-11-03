#!/usr/bin/env python3
"""
Safe SM Backtesting Script
Extends UptrendEngine without modifying production code
"""

import os
import json
import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import the production UptrendEngine and supporting classes
from src.intelligence.lowcap_portfolio_manager.jobs.uptrend_engine import UptrendEngine
from src.intelligence.lowcap_portfolio_manager.jobs.geometry_build_daily import GeometryBuilder
from src.intelligence.lowcap_portfolio_manager.jobs.ta_tracker import TATracker

logger = logging.getLogger(__name__)


class BacktestUptrendEngine(UptrendEngine):
    """
    Safe backtesting version of UptrendEngine.
    Inherits from production class but overrides methods for historical analysis.
    """
    
    def __init__(self, target_ts: Optional[datetime] = None):
        super().__init__()
        self.target_ts = target_ts or datetime.now(timezone.utc)
        
    def _latest_close_1h(self, contract: str, chain: str) -> Dict[str, Any]:
        """
        Override to filter data by target timestamp for backtesting.
        """
        query = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, close_native, low_native")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", "1h")
            .lte("timestamp", self.target_ts.isoformat())  # Key difference: filter by target_ts
        )
        
        row = (
            query
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        
        if row:
            r = row[0]
            return {
                "ts": str(r.get("timestamp")),
                "close": float(r.get("close_native") or 0.0),
                "low": float(r.get("low_native") or 0.0),
            }
        return {"ts": None, "close": 0.0, "low": 0.0}
    
    def _fetch_ohlc_1h_series(self, contract: str, chain: str, limit: int = 120) -> List[Dict[str, Any]]:
        """
        Override to filter OHLC data by target timestamp for backtesting.
        """
        query = (
            self.sb.table("lowcap_price_data_ohlc")
            .select("timestamp, open_native, high_native, low_native, close_native, volume")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", "1h")
            .lte("timestamp", self.target_ts.isoformat())  # Key difference: filter by target_ts
        )
        
        rows = (
            query
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        
        # Convert to list of dicts with proper typing
        result = []
        for row in rows:
            result.append({
                "timestamp": str(row.get("timestamp")),
                "open": float(row.get("open_native") or 0.0),
                "high": float(row.get("high_native") or 0.0),
                "low": float(row.get("low_native") or 0.0),
                "close": float(row.get("close_native") or 0.0),
                "volume": float(row.get("volume") or 0.0),
            })
        
        return result
    
    def run_at_timestamp(self, contract: str, chain: str) -> Dict[str, Any]:
        """
        Run uptrend engine analysis for a specific token at a specific timestamp.
        Used for backtesting - does not update database, only returns results.
        """
        try:
            # Get position features (geometry, etc.) - use current state
            pos_res = (
                self.sb.table("lowcap_positions")
                .select("features")
                .eq("token_contract", contract)
                .eq("token_chain", chain)
                .eq("status", "active")
                .limit(1)
                .execute()
            )
            
            if not pos_res.data:
                return {"error": f"No active position found for {contract}"}
                
            features = pos_res.data[0].get("features") or {}
            
            # Compute scores/state at target timestamp
            ss = self._score_and_state(contract, chain, features)
            payload = self._unified_payload(ss["state"], features)
            payload["scores"] = ss["scores"]
            payload["flag"] = ss["flags"]
            payload["levels"].update(ss["levels"])
            if ss.get("supports"):
                payload["supports"] = ss["supports"]
            
            # Update emergency exit block
            payload = self._update_emergency_exit(payload, features, contract, chain)
            
            # Add timestamp info
            payload["analysis_ts"] = self.target_ts.isoformat()
            payload["contract"] = contract
            payload["chain"] = chain
            
            return payload
            
        except Exception as e:
            logger.error(f"Error in run_at_timestamp for {contract}: {e}")
            return {"error": str(e)}


def prepare_features_for_backtest(contract: str, chain: str) -> bool:
    """
    Run geometry and TA jobs to populate features for backtesting.
    Returns True if successful, False otherwise.
    """
    try:
        logger.info(f"Preparing features for {contract} on {chain}")
        
        # Run geometry builder
        logger.info("Running geometry_build_daily...")
        geometry_builder = GeometryBuilder()
        geometry_updated = geometry_builder.build()
        logger.info(f"Geometry builder updated {geometry_updated} positions")
        
        # Run TA tracker  
        logger.info("Running ta_tracker...")
        ta_tracker = TATracker()
        ta_updated = ta_tracker.run()
        logger.info(f"TA tracker updated {ta_updated} positions")
        
        return True
        
    except Exception as e:
        logger.error(f"Error preparing features: {e}")
        return False


def backtest_token(contract: str, chain: str, start_ts: datetime, end_ts: datetime, interval_hours: int = 1) -> List[Dict[str, Any]]:
    """
    Run backtest for a token over a time range.
    
    Args:
        contract: Token contract address
        chain: Token chain (e.g., 'solana')
        start_ts: Start timestamp for backtest
        end_ts: End timestamp for backtest
        interval_hours: Hours between analysis points
        
    Returns:
        List of analysis results for each timestamp
    """
    results = []
    current_ts = start_ts
    
    while current_ts <= end_ts:
        engine = BacktestUptrendEngine(current_ts)
        result = engine.run_at_timestamp(contract, chain)
        
        if "error" not in result:
            results.append(result)
            logger.info(f"Analyzed {contract} at {current_ts.isoformat()}: State={result.get('state', 'Unknown')}")
        else:
            logger.warning(f"Failed to analyze {contract} at {current_ts.isoformat()}: {result['error']}")
        
        current_ts += timedelta(hours=interval_hours)
    
    return results


def generate_backtest_chart(results: List[Dict[str, Any]], contract: str, chain: str) -> str:
    """
    Generate a comprehensive chart showing price, geometry, TA, states, and signals.
    """
    if not results:
        logger.warning("No results to chart")
        return ""
    
    try:
        # Extract data for plotting
        timestamps = []
        prices = []
        states = []
        state_colors = {'S0': 'gray', 'S1': 'green', 'S2': 'blue', 'S3': 'orange', 'S4': 'red', 'S5': 'purple'}
        
        for result in results:
            if 'analysis_ts' in result:
                timestamps.append(datetime.fromisoformat(result['analysis_ts'].replace('Z', '+00:00')))
                prices.append(result.get('levels', {}).get('current_price', 0.0))
                states.append(result.get('state', 'S0'))
        
        if not timestamps:
            logger.warning("No valid timestamps for charting")
            return ""
        
        # Create the chart
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [3, 1, 1]})
        
        # Price chart with state colors
        ax1.plot(timestamps, prices, 'b-', linewidth=2, alpha=0.7, label='Price')
        
        # Color code by state
        for i, (ts, price, state) in enumerate(zip(timestamps, prices, states)):
            color = state_colors.get(state, 'gray')
            ax1.scatter(ts, price, color=color, s=50, alpha=0.8, zorder=5)
        
        ax1.set_ylabel('Price (Native)')
        ax1.set_title(f'{contract[:8]} Backtest Results - States & Signals')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # State timeline
        state_numeric = {'S0': 0, 'S1': 1, 'S2': 2, 'S3': 3, 'S4': 4, 'S5': 5}
        state_values = [state_numeric.get(s, 0) for s in states]
        ax2.plot(timestamps, state_values, 'o-', linewidth=2, markersize=6)
        ax2.set_ylabel('State')
        ax2.set_ylim(-0.5, 5.5)
        ax2.set_yticks(range(6))
        ax2.set_yticklabels(['S0', 'S1', 'S2', 'S3', 'S4', 'S5'])
        ax2.grid(True, alpha=0.3)
        
        # State transitions
        transitions = []
        for i in range(1, len(states)):
            if states[i] != states[i-1]:
                transitions.append((timestamps[i], states[i-1], states[i]))
        
        for ts, from_state, to_state in transitions:
            ax2.annotate(f'{from_state}→{to_state}', 
                        xy=(ts, state_numeric[to_state]), 
                        xytext=(ts, state_numeric[to_state] + 0.5),
                        ha='center', va='bottom', fontsize=8,
                        arrowprops=dict(arrowstyle='->', color='red', alpha=0.7))
        
        # Buy/Sell signals (placeholder - would need to implement signal detection)
        ax3.plot(timestamps, [0] * len(timestamps), 'k-', alpha=0.3)
        ax3.set_ylabel('Signals')
        ax3.set_ylim(-1.5, 1.5)
        ax3.set_yticks([-1, 0, 1])
        ax3.set_yticklabels(['SELL', 'HOLD', 'BUY'])
        ax3.grid(True, alpha=0.3)
        
        # Format x-axis
        for ax in [ax1, ax2, ax3]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save chart
        chart_filename = f"backtest_chart_{contract[:8]}_{int(datetime.now().timestamp())}.png"
        plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
        plt.close(fig)
        
        logger.info(f"Chart saved as {chart_filename}")
        return chart_filename
        
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return ""


def main():
    """Main backtest execution for META token"""
    logging.basicConfig(level=logging.INFO)
    
    # META token details
    contract = "METAwkXcqyXKy1AtsSgJ8JiUHwGCafnZL38n3vYmeta"
    chain = "solana"
    
    logger.info(f"Starting comprehensive backtest for {contract}")
    
    # Step 1: Prepare features (run geometry and TA jobs)
    logger.info("Step 1: Preparing features...")
    if not prepare_features_for_backtest(contract, chain):
        logger.error("Failed to prepare features. Aborting backtest.")
        return
    
    # Step 2: Run backtest
    logger.info("Step 2: Running backtest analysis...")
    end_ts = datetime.now(timezone.utc)
    start_ts = end_ts - timedelta(days=14)
    
    logger.info(f"Backtest period: {start_ts.isoformat()} to {end_ts.isoformat()}")
    
    results = backtest_token(contract, chain, start_ts, end_ts, interval_hours=1)
    
    # Step 3: Save results
    logger.info("Step 3: Saving results...")
    output_file = f"backtest_results_{contract}_{int(end_ts.timestamp())}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"Backtest completed. Results saved to {output_file}")
    logger.info(f"Total analysis points: {len(results)}")
    
    # Step 4: Print summary
    states = {}
    for result in results:
        state = result.get('state', 'Unknown')
        states[state] = states.get(state, 0) + 1
    
    print("\nState Distribution:")
    for state, count in sorted(states.items()):
        print(f"  {state}: {count} hours")
    
    # Step 5: Generate chart
    logger.info("Step 5: Generating chart...")
    chart_file = generate_backtest_chart(results, contract, chain)
    if chart_file:
        print(f"\nChart saved as: {chart_file}")
    
    print(f"\nBacktest complete! Check {output_file} for detailed results.")


if __name__ == "__main__":
    main()
