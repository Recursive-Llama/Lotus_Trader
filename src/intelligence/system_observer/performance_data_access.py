"""
Performance Data Access Layer
Provides functions to query performance data from database
This is the foundation layer for System Observer (Phase 1) and Level 1 (future)
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from supabase import Client

logger = logging.getLogger(__name__)


class PerformanceDataAccess:
    """Access performance data from database"""
    
    def __init__(self, sb_client: Client):
        self.sb = sb_client
    
    # ============================================================
    # 1. Current Balance
    # ============================================================
    
    def get_current_balance(self) -> Dict[str, Any]:
        """Get current balance (USDC + active positions)"""
        try:
            # Get USDC from all chains
            wallet_rows = (
                self.sb.table("wallet_balances")
                .select("chain, usdc_balance")
                .execute()
            ).data or []
            
            usdc_by_chain = {
                row["chain"]: float(row.get("usdc_balance", 0) or 0) 
                for row in wallet_rows
            }
            usdc_total = sum(usdc_by_chain.values())
            
            # Get active positions
            position_rows = (
                self.sb.table("lowcap_positions")
                .select("id, token_ticker, current_usd_value")
                .eq("status", "active")
                .execute()
            ).data or []
            
            active_positions_value = sum(
                float(row.get("current_usd_value", 0) or 0) 
                for row in position_rows
            )
            
            return {
                "total_balance_usd": usdc_total + active_positions_value,
                "usdc_total": usdc_total,
                "usdc_by_chain": usdc_by_chain,
                "active_positions_value": active_positions_value,
                "active_positions_count": len(position_rows),
                "active_positions": [
                    {
                        "id": row["id"],
                        "ticker": row.get("token_ticker"),
                        "value_usd": float(row.get("current_usd_value", 0) or 0)
                    }
                    for row in position_rows
                ]
            }
        except Exception as e:
            logger.error(f"Error getting current balance: {e}", exc_info=True)
            return {"error": str(e)}
    
    def get_portfolio_pnl(self) -> Dict[str, Any]:
        """Get detailed PnL breakdown: starting capital, deployed, unrealized, realized, total"""
        try:
            # 1. Get starting balance (from first valid snapshot after wallet sync)
            # Skip first snapshot if it was taken before wallet balance was synced
            all_snapshots = (
                self.sb.table("wallet_balance_snapshots")
                .select("*")
                .order("captured_at")  # Ascending (oldest first)
                .execute()
            ).data or []
            
            starting_snapshot = None
            starting_usdc = None
            starting_balance = None
            
            if all_snapshots:
                # If we have multiple snapshots, check if first one looks suspicious
                # (e.g., different USDC in second snapshot suggests first was pre-sync)
                if len(all_snapshots) > 1:
                    first_usdc = float(all_snapshots[0].get("usdc_total", 0) or 0)
                    second_usdc = float(all_snapshots[1].get("usdc_total", 0) or 0)
                    first_positions = int(all_snapshots[0].get("active_positions_count", 0) or 0)
                    
                    # If first snapshot has no positions and USDC differs significantly, use second
                    if first_positions == 0 and abs(first_usdc - second_usdc) > 0.01:
                        starting_snapshot = all_snapshots[1]
                    else:
                        starting_snapshot = all_snapshots[0]
                else:
                    starting_snapshot = all_snapshots[0]
                
                starting_usdc = float(starting_snapshot.get("usdc_total", 0) or 0)
                starting_balance = float(starting_snapshot.get("total_balance_usd", 0) or 0)
            
            # 2. Get current USDC
            wallet_rows = (
                self.sb.table("wallet_balances")
                .select("chain, usdc_balance")
                .execute()
            ).data or []
            current_usdc = sum(float(row.get("usdc_balance", 0) or 0) for row in wallet_rows)
            
            # 3. Get active positions with cost basis
            position_rows = (
                self.sb.table("lowcap_positions")
                .select("id, token_ticker, token_contract, token_chain, timeframe, total_allocation_usd, total_extracted_usd, current_usd_value, total_pnl_usd, total_pnl_pct, rpnl_usd")
                .eq("status", "active")
                .execute()
            ).data or []
            
            positions_detail = []
            total_deployed = 0.0
            total_extracted = 0.0  # Total USD extracted (not PnL, but actual amount)
            total_current_value = 0.0
            total_unrealized_pnl = 0.0
            total_realized_pnl = 0.0
            
            for pos in position_rows:
                allocated = float(pos.get("total_allocation_usd", 0) or 0)
                current_value = float(pos.get("current_usd_value", 0) or 0)
                extracted = float(pos.get("total_extracted_usd", 0) or 0)
                realized_pnl = float(pos.get("rpnl_usd", 0) or 0)  # Already calculated: total_pnl - unrealized
                total_pnl = float(pos.get("total_pnl_usd", 0) or 0)
                total_pnl_pct = float(pos.get("total_pnl_pct", 0) or 0)
                
                # Unrealized = Total PnL - Realized (or use: current_value - (allocated - extracted))
                # The DB already calculates: total_pnl = current_value + extracted - allocated
                # So: unrealized = total_pnl - rpnl_usd
                unrealized_pnl = total_pnl - realized_pnl
                
                total_deployed += allocated
                total_extracted += extracted
                total_current_value += current_value
                total_unrealized_pnl += unrealized_pnl
                total_realized_pnl += realized_pnl
                
                positions_detail.append({
                    "id": pos["id"],
                    "ticker": pos.get("token_ticker"),
                    "contract": pos.get("token_contract"),
                    "chain": pos.get("token_chain"),
                    "timeframe": pos.get("timeframe"),
                    "allocated_usd": allocated,
                    "extracted_usd": extracted,
                    "current_value_usd": current_value,
                    "unrealized_pnl_usd": unrealized_pnl,
                    "unrealized_pnl_pct": (unrealized_pnl / allocated * 100) if allocated > 0 else 0,
                    "realized_pnl_usd": realized_pnl,  # From trims/partial exits (already calculated in DB)
                    "total_pnl_usd": total_pnl,
                    "total_pnl_pct": total_pnl_pct
                })
            
            # 4. Get realized PnL from closed trades
            closed_trades = self.get_closed_trades_over_period(None)  # All time
            realized_from_closed = sum(t["rpnl_usd"] for t in closed_trades)
            total_realized_pnl += realized_from_closed
            
            # 5. Calculate total PnL
            # Total PnL = Current Total Balance - Starting Balance
            # This is the most accurate method as it uses actual balance snapshots
            if starting_balance is None:
                # Fallback: estimate from starting USDC
                starting_balance = starting_usdc if starting_usdc is not None else (current_usdc + total_deployed)
            
            current_total_balance = current_usdc + total_current_value
            total_pnl = current_total_balance - starting_balance
            
            return {
                "starting_usdc": starting_usdc,
                "starting_balance": starting_balance,
                "current_usdc": current_usdc,
                "current_total_balance": current_total_balance,
                "capital_deployed": total_deployed,
                "capital_extracted": total_extracted,  # Total USD extracted (actual amount, not PnL)
                "positions_current_value": total_current_value,
                "unrealized_pnl_usd": total_unrealized_pnl,
                "unrealized_pnl_pct": (total_unrealized_pnl / total_deployed * 100) if total_deployed > 0 else 0,
                "realized_pnl_usd": total_realized_pnl,
                "realized_from_closed_trades": realized_from_closed,
                "realized_from_partial_exits": total_realized_pnl - realized_from_closed,
                "total_pnl_usd": total_pnl,
                "total_pnl_pct": (total_pnl / starting_balance * 100) if starting_balance > 0 else 0,
                "positions": positions_detail,
                "closed_trades_count": len(closed_trades)
            }
        except Exception as e:
            logger.error(f"Error getting portfolio PnL: {e}", exc_info=True)
            return {"error": str(e)}
    
    # ============================================================
    # 2. Historical PnL (from snapshots)
    # ============================================================
    
    def get_pnl_over_period(self, hours: int) -> Dict[str, Any]:
        """Get PnL change over time period using snapshots"""
        try:
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(hours=hours)
            
            # Get latest snapshot (any type)
            current = (
                self.sb.table("wallet_balance_snapshots")
                .select("*")
                .order("captured_at", desc=True)
                .limit(1)
                .execute()
            ).data
            
            if not current:
                return {"error": "No snapshots available"}
            
            current = current[0]
            
            # Get snapshot at cutoff time (or closest before)
            # Try daily first, then weekly, then monthly
            past = (
                self.sb.table("wallet_balance_snapshots")
                .select("*")
                .lte("captured_at", cutoff.isoformat())
                .order("captured_at", desc=True)
                .limit(1)
                .execute()
            ).data
            
            if not past:
                return {"error": f"No snapshot found before {cutoff.isoformat()}"}
            
            past = past[0]
            
            pnl_usd = float(current["total_balance_usd"]) - float(past["total_balance_usd"])
            pnl_pct = (pnl_usd / float(past["total_balance_usd"]) * 100) if float(past["total_balance_usd"]) > 0 else 0
            
            return {
                "period_hours": hours,
                "starting_balance": float(past["total_balance_usd"]),
                "ending_balance": float(current["total_balance_usd"]),
                "pnl_usd": pnl_usd,
                "pnl_pct": pnl_pct,
                "starting_timestamp": past["captured_at"],
                "ending_timestamp": current["captured_at"]
            }
        except Exception as e:
            logger.error(f"Error getting PnL over period: {e}", exc_info=True)
            return {"error": str(e)}
    
    # ============================================================
    # 3. Closed Trades Extraction
    # ============================================================
    
    def _extract_entry_state_from_pattern_key(self, pattern_key: str) -> Optional[str]:
        """Extract state (S1/S2/S3) from pattern_key"""
        if not pattern_key:
            return None
        
        try:
            # Format: "module=pm|pattern_key=uptrend.S1.entry"
            parts = pattern_key.split("|")
            if len(parts) == 2:
                pattern_part = parts[1]  # "pattern_key=uptrend.S1.entry"
                if "=" in pattern_part:
                    pattern_core = pattern_part.split("=", 1)[1]  # "uptrend.S1.entry"
                    state = pattern_core.split(".")[1]  # "S1"
                    if state in ["S1", "S2", "S3"]:
                        return state
        except Exception:
            pass
        
        return None
    
    def get_closed_trades_over_period(self, hours: Optional[int] = None) -> List[Dict[str, Any]]:
        """Extract all closed trades, optionally filtered by time window"""
        try:
            # Query all positions with completed_trades
            positions = (
                self.sb.table("lowcap_positions")
                .select("id, token_ticker, token_contract, token_chain, timeframe, completed_trades")
                .not_.is_("completed_trades", "null")
                .neq("completed_trades", "[]")
                .execute()
            ).data or []
            
            all_trades = []
            cutoff = None
            if hours:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            for pos in positions:
                completed_trades = pos.get("completed_trades", [])
                if not isinstance(completed_trades, list):
                    continue
                
                for trade in completed_trades:
                    summary = trade.get("summary", {})
                    exit_ts_str = summary.get("exit_timestamp")
                    
                    if not exit_ts_str:
                        continue
                    
                    try:
                        exit_ts = datetime.fromisoformat(exit_ts_str.replace("Z", "+00:00"))
                    except Exception:
                        continue
                    
                    # Filter by time window if specified
                    if cutoff and exit_ts < cutoff:
                        continue
                    
                    # Extract entry state from first entry action
                    entry_state = None
                    actions = trade.get("actions", [])
                    for action in actions:
                        if action.get("action_category") == "entry" or action.get("decision_type") == "entry":
                            pattern_key = action.get("pattern_key", "")
                            entry_state = self._extract_entry_state_from_pattern_key(pattern_key)
                            break
                    
                    # Fallback to summary pattern_key if no action found
                    if not entry_state:
                        pattern_key = summary.get("pattern_key", "")
                        entry_state = self._extract_entry_state_from_pattern_key(pattern_key)
                    
                    # Determine if first buy
                    is_first_buy = (
                        summary.get("decision_type") == "entry" or
                        summary.get("action_category") == "entry" or
                        (actions and actions[0].get("action_category") == "entry")
                    )
                    
                    # Get timeframe from scope or position
                    scope = summary.get("scope", {})
                    timeframe = scope.get("timeframe") or pos.get("timeframe", "1h")
                    
                    all_trades.append({
                        "position_id": pos["id"],
                        "token_ticker": pos.get("token_ticker"),
                        "token_contract": pos.get("token_contract"),
                        "token_chain": pos.get("token_chain"),
                        "timeframe": timeframe,
                        "exit_timestamp": exit_ts.isoformat(),
                        "entry_timestamp": summary.get("entry_timestamp"),
                        "rpnl_usd": float(summary.get("rpnl_usd", 0) or 0),
                        "rpnl_pct": float(summary.get("rpnl_pct", 0) or 0),
                        "total_pnl_usd": float(summary.get("total_pnl_usd", 0) or 0),
                        "entry_state": entry_state,  # "S1", "S2", "S3", or None
                        "is_first_buy": is_first_buy
                    })
            
            return sorted(all_trades, key=lambda x: x["exit_timestamp"], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting closed trades: {e}", exc_info=True)
            return []
    
    # ============================================================
    # 4. Performance Breakdown
    # ============================================================
    
    def get_performance_breakdown(self, hours: Optional[int] = None) -> Dict[str, Any]:
        """Get performance breakdown by timeframe and entry state"""
        try:
            trades = self.get_closed_trades_over_period(hours)
            
            if not trades:
                return {
                    "by_timeframe": {},
                    "by_entry_state": {},
                    "total_trades": 0,
                    "total_pnl_usd": 0
                }
            
            # By timeframe
            by_timeframe = {}
            for tf in ["1m", "15m", "1h", "4h"]:
                tf_trades = [t for t in trades if t["timeframe"] == tf]
                wins = [t for t in tf_trades if t["rpnl_usd"] > 0]
                
                by_timeframe[tf] = {
                    "count": len(tf_trades),
                    "win_rate": len(wins) / len(tf_trades) if tf_trades else 0,
                    "avg_roi_pct": sum([t["rpnl_pct"] for t in tf_trades]) / len(tf_trades) if tf_trades else 0,
                    "total_pnl_usd": sum([t["rpnl_usd"] for t in tf_trades])
                }
            
            # By entry state (first buys only)
            first_buys = [t for t in trades if t["is_first_buy"]]
            by_entry_state = {}
            for state in ["S1", "S2", "S3"]:
                state_trades = [t for t in first_buys if t["entry_state"] == state]
                by_entry_state[state] = {
                    "count": len(state_trades),
                    "avg_return_pct": sum([t["rpnl_pct"] for t in state_trades]) / len(state_trades) if state_trades else 0,
                    "total_pnl_usd": sum([t["rpnl_usd"] for t in state_trades])
                }
            
            return {
                "by_timeframe": by_timeframe,
                "by_entry_state": by_entry_state,
                "total_trades": len(trades),
                "total_pnl_usd": sum([t["rpnl_usd"] for t in trades])
            }
            
        except Exception as e:
            logger.error(f"Error getting performance breakdown: {e}", exc_info=True)
            return {"error": str(e)}

