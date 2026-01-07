"""
Balance Snapshot Job - Captures current portfolio balance hourly
Handles hierarchical rollups: hourly → 4-hour → daily → weekly → monthly
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from supabase import Client

logger = logging.getLogger(__name__)


class BalanceSnapshotJob:
    """Captures wallet balance snapshots and manages hierarchical rollups"""
    
    def __init__(self, sb_client: Client):
        self.sb = sb_client
    
    async def capture_snapshot(self, snapshot_type: str = "hourly") -> Dict[str, Any]:
        """Capture current balance snapshot
        
        Args:
            snapshot_type: 'hourly', '4hour', 'daily', 'weekly', or 'monthly'
        """
        try:
            # 1. Get USDC from all chains
            wallet_rows = (
                self.sb.table("wallet_balances")
                .select("usdc_balance")
                .execute()
            ).data or []
            
            usdc_total = sum(float(row.get("usdc_balance", 0) or 0) for row in wallet_rows)
            
            # 2. Get active positions with full details for JSONB storage
            position_rows = (
                self.sb.table("lowcap_positions")
                .select("token_ticker,token_contract,token_chain,timeframe,current_usd_value,total_pnl_usd,rpnl_usd,total_extracted_usd,total_allocation_usd")
                .eq("status", "active")
                .execute()
            ).data or []
            
            # Build positions array for JSONB column
            positions_array = []
            for pos in position_rows:
                positions_array.append({
                    "ticker": pos.get("token_ticker") or "?",
                    "contract": pos.get("token_contract") or "",
                    "chain": pos.get("token_chain") or "",
                    "timeframe": pos.get("timeframe") or "",
                    "value": float(pos.get("current_usd_value", 0) or 0),
                    "current_pnl": float(pos.get("total_pnl_usd", 0) or 0),
                    "realized_pnl": float(pos.get("rpnl_usd", 0) or 0),
                    "extracted": float(pos.get("total_extracted_usd", 0) or 0),
                    "allocated": float(pos.get("total_allocation_usd", 0) or 0)
                })
            
            active_positions_value = sum(
                float(row.get("current_usd_value", 0) or 0) 
                for row in position_rows
            )
            active_positions_count = len(position_rows)
            
            # 3. Calculate total
            total_balance = usdc_total + active_positions_value
            
            # 4. Insert snapshot with positions array
            snapshot = {
                "snapshot_type": snapshot_type,
                "total_balance_usd": total_balance,
                "usdc_total": usdc_total,
                "active_positions_value": active_positions_value,
                "active_positions_count": active_positions_count,
                "positions": positions_array,  # JSONB array of position details
                "captured_at": datetime.now(timezone.utc).isoformat()
            }
            
            result = (
                self.sb.table("wallet_balance_snapshots")
                .insert(snapshot)
                .execute()
            )
            
            logger.info(
                f"Balance snapshot captured ({snapshot_type}): ${total_balance:.2f} "
                f"(USDC: ${usdc_total:.2f}, Active: ${active_positions_value:.2f}, Count: {active_positions_count})"
            )
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Error capturing balance snapshot: {e}", exc_info=True)
            raise
    
    async def ensure_initial_snapshot(self):
        """Create first snapshot if none exists (called on startup)"""
        try:
            # Check if any snapshots exist
            existing = (
                self.sb.table("wallet_balance_snapshots")
                .select("id")
                .limit(1)
                .execute()
            )
            
            if not existing.data:
                logger.info("No snapshots found, creating initial hourly snapshot...")
                await self.capture_snapshot("hourly")
            else:
                logger.info("Snapshots already exist")
                
        except Exception as e:
            logger.error(f"Error ensuring initial snapshot: {e}", exc_info=True)
            # Don't raise - non-fatal
    
    async def rollup_4hour_snapshots(self):
        """Roll up hourly snapshots to 4-hour aggregates (run every 4 hours)"""
        try:
            # Get all hourly snapshots that haven't been rolled up
            # We'll roll up the last 4 hours worth of hourly snapshots
            cutoff = datetime.now(timezone.utc) - timedelta(hours=4)
            
            hourly_snapshots = (
                self.sb.table("wallet_balance_snapshots")
                .select("*")
                .eq("snapshot_type", "hourly")
                .lte("captured_at", cutoff.isoformat())
                .order("captured_at")
                .execute()
            ).data or []
            
            if not hourly_snapshots:
                logger.info("No hourly snapshots to roll up to 4-hour")
                return
            
            # Group by 4-hour windows (round down to nearest 4-hour boundary)
            four_hour_groups = {}
            for snapshot in hourly_snapshots:
                captured_at = datetime.fromisoformat(snapshot["captured_at"].replace("Z", "+00:00"))
                # Round down to nearest 4-hour boundary (00:00, 04:00, 08:00, 12:00, 16:00, 20:00)
                hour = captured_at.hour
                rounded_hour = (hour // 4) * 4
                window_start = captured_at.replace(hour=rounded_hour, minute=0, second=0, microsecond=0)
                window_key = window_start.isoformat()
                
                if window_key not in four_hour_groups:
                    four_hour_groups[window_key] = []
                four_hour_groups[window_key].append(snapshot)
            
            # Create 4-hour aggregates
            for window_key, snapshots in four_hour_groups.items():
                # Use first snapshot's timestamp as the window start
                window_start = datetime.fromisoformat(snapshots[0]["captured_at"].replace("Z", "+00:00"))
                window_start = window_start.replace(minute=0, second=0, microsecond=0)
                hour = window_start.hour
                window_start = window_start.replace(hour=(hour // 4) * 4)
                
                # Aggregate: average balance, average counts
                avg_balance = sum(float(s["total_balance_usd"]) for s in snapshots) / len(snapshots)
                avg_usdc = sum(float(s["usdc_total"]) for s in snapshots) / len(snapshots)
                avg_positions_value = sum(float(s["active_positions_value"]) for s in snapshots) / len(snapshots)
                avg_positions_count = sum(int(s["active_positions_count"]) for s in snapshots) / len(snapshots)
                
                # Use positions from the last snapshot in the window (most recent state)
                last_snapshot = snapshots[-1]
                positions = last_snapshot.get("positions", [])
                
                four_hour_snapshot = {
                    "snapshot_type": "4hour",
                    "total_balance_usd": avg_balance,
                    "usdc_total": avg_usdc,
                    "active_positions_value": avg_positions_value,
                    "active_positions_count": int(avg_positions_count),
                    "positions": positions,  # Positions from last snapshot in window
                    "captured_at": window_start.isoformat()
                }
                
                # Check if 4-hour snapshot already exists for this window
                existing = (
                    self.sb.table("wallet_balance_snapshots")
                    .select("id")
                    .eq("snapshot_type", "4hour")
                    .eq("captured_at", window_start.isoformat())
                    .execute()
                ).data
                
                if existing:
                    logger.debug(f"4-hour snapshot already exists for {window_start.isoformat()}, skipping")
                    continue
                
                # Insert 4-hour aggregate
                self.sb.table("wallet_balance_snapshots").insert(four_hour_snapshot).execute()
                
                # Delete rolled-up hourly snapshots
                snapshot_ids = [s["id"] for s in snapshots]
                for snapshot_id in snapshot_ids:
                    self.sb.table("wallet_balance_snapshots").delete().eq("id", snapshot_id).execute()
                
                logger.info(f"Rolled up {len(snapshots)} hourly snapshots to 4-hour aggregate for {window_start.isoformat()}")
            
        except Exception as e:
            logger.error(f"Error rolling up 4-hour snapshots: {e}", exc_info=True)
    
    async def rollup_daily_snapshots(self):
        """Roll up 4-hour snapshots to daily aggregates (run daily)"""
        try:
            # Get all 4-hour snapshots older than 24 hours that haven't been rolled up
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            
            four_hour_snapshots = (
                self.sb.table("wallet_balance_snapshots")
                .select("*")
                .eq("snapshot_type", "4hour")
                .lt("captured_at", cutoff.isoformat())
                .order("captured_at")
                .execute()
            ).data or []
            
            if not four_hour_snapshots:
                logger.info("No 4-hour snapshots to roll up to daily")
                return
            
            # Group by day (year-month-day)
            daily_groups = {}
            for snapshot in four_hour_snapshots:
                captured_at = datetime.fromisoformat(snapshot["captured_at"].replace("Z", "+00:00"))
                day_key = f"{captured_at.year}-{captured_at.month:02d}-{captured_at.day:02d}"
                
                if day_key not in daily_groups:
                    daily_groups[day_key] = []
                daily_groups[day_key].append(snapshot)
            
            # Create daily aggregates
            for day_key, snapshots in daily_groups.items():
                # Use first snapshot's timestamp as the day start
                day_start = datetime.fromisoformat(snapshots[0]["captured_at"].replace("Z", "+00:00"))
                day_start = day_start.replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Aggregate: average balance, average counts
                avg_balance = sum(float(s["total_balance_usd"]) for s in snapshots) / len(snapshots)
                avg_usdc = sum(float(s["usdc_total"]) for s in snapshots) / len(snapshots)
                avg_positions_value = sum(float(s["active_positions_value"]) for s in snapshots) / len(snapshots)
                avg_positions_count = sum(int(s["active_positions_count"]) for s in snapshots) / len(snapshots)
                
                # Use positions from the last snapshot in the day (most recent state)
                last_snapshot = snapshots[-1]
                positions = last_snapshot.get("positions", [])
                
                daily_snapshot = {
                    "snapshot_type": "daily",
                    "total_balance_usd": avg_balance,
                    "usdc_total": avg_usdc,
                    "active_positions_value": avg_positions_value,
                    "active_positions_count": int(avg_positions_count),
                    "positions": positions,  # Positions from last snapshot in day
                    "captured_at": day_start.isoformat()
                }
                
                # Check if daily snapshot already exists for this day
                existing = (
                    self.sb.table("wallet_balance_snapshots")
                    .select("id")
                    .eq("snapshot_type", "daily")
                    .eq("captured_at", day_start.isoformat())
                    .execute()
                ).data
                
                if existing:
                    logger.debug(f"Daily snapshot already exists for {day_start.isoformat()}, skipping")
                    continue
                
                # Insert daily aggregate
                self.sb.table("wallet_balance_snapshots").insert(daily_snapshot).execute()
                
                # Delete rolled-up 4-hour snapshots
                snapshot_ids = [s["id"] for s in snapshots]
                for snapshot_id in snapshot_ids:
                    self.sb.table("wallet_balance_snapshots").delete().eq("id", snapshot_id).execute()
                
                logger.info(f"Rolled up {len(snapshots)} 4-hour snapshots to daily aggregate for {day_key}")
            
        except Exception as e:
            logger.error(f"Error rolling up daily snapshots: {e}", exc_info=True)
    
    async def rollup_weekly_snapshots(self):
        """Roll up daily snapshots to weekly aggregates (run weekly)"""
        try:
            # Get all daily snapshots older than 7 days that haven't been rolled up
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            
            daily_snapshots = (
                self.sb.table("wallet_balance_snapshots")
                .select("*")
                .eq("snapshot_type", "daily")
                .lt("captured_at", cutoff.isoformat())
                .order("captured_at")
                .execute()
            ).data or []
            
            if not daily_snapshots:
                logger.info("No daily snapshots to roll up")
                return
            
            # Group by week (ISO week)
            weekly_groups = {}
            for snapshot in daily_snapshots:
                captured_at = datetime.fromisoformat(snapshot["captured_at"].replace("Z", "+00:00"))
                # Get ISO week (year, week number)
                year, week, _ = captured_at.isocalendar()
                week_key = f"{year}-W{week:02d}"
                
                if week_key not in weekly_groups:
                    weekly_groups[week_key] = []
                weekly_groups[week_key].append(snapshot)
            
            # Create weekly aggregates
            for week_key, snapshots in weekly_groups.items():
                # Use first snapshot's timestamp as the week start
                week_start = datetime.fromisoformat(snapshots[0]["captured_at"].replace("Z", "+00:00"))
                
                # Aggregate: average balance, sum counts
                avg_balance = sum(float(s["total_balance_usd"]) for s in snapshots) / len(snapshots)
                avg_usdc = sum(float(s["usdc_total"]) for s in snapshots) / len(snapshots)
                avg_positions_value = sum(float(s["active_positions_value"]) for s in snapshots) / len(snapshots)
                avg_positions_count = sum(int(s["active_positions_count"]) for s in snapshots) / len(snapshots)
                
                # Use positions from the last snapshot in the week (most recent state)
                last_snapshot = snapshots[-1]
                positions = last_snapshot.get("positions", [])
                
                weekly_snapshot = {
                    "snapshot_type": "weekly",
                    "total_balance_usd": avg_balance,
                    "usdc_total": avg_usdc,
                    "active_positions_value": avg_positions_value,
                    "active_positions_count": int(avg_positions_count),
                    "positions": positions,  # Positions from last snapshot in week
                    "captured_at": week_start.isoformat()
                }
                
                # Check if weekly snapshot already exists for this week
                existing = (
                    self.sb.table("wallet_balance_snapshots")
                    .select("id")
                    .eq("snapshot_type", "weekly")
                    .eq("captured_at", week_start.isoformat())
                    .execute()
                ).data
                
                if existing:
                    logger.debug(f"Weekly snapshot already exists for {week_key}, skipping")
                    continue
                
                # Insert weekly aggregate
                self.sb.table("wallet_balance_snapshots").insert(weekly_snapshot).execute()
                
                # Delete rolled-up daily snapshots
                snapshot_ids = [s["id"] for s in snapshots]
                for snapshot_id in snapshot_ids:
                    self.sb.table("wallet_balance_snapshots").delete().eq("id", snapshot_id).execute()
                
                logger.info(f"Rolled up {len(snapshots)} daily snapshots to weekly aggregate for {week_key}")
            
        except Exception as e:
            logger.error(f"Error rolling up weekly snapshots: {e}", exc_info=True)
    
    async def rollup_monthly_snapshots(self):
        """Roll up weekly snapshots to monthly aggregates (run monthly)"""
        try:
            # Get all weekly snapshots older than 4 weeks that haven't been rolled up
            cutoff = datetime.now(timezone.utc) - timedelta(weeks=4)
            
            weekly_snapshots = (
                self.sb.table("wallet_balance_snapshots")
                .select("*")
                .eq("snapshot_type", "weekly")
                .lt("captured_at", cutoff.isoformat())
                .order("captured_at")
                .execute()
            ).data or []
            
            if not weekly_snapshots:
                logger.info("No weekly snapshots to roll up")
                return
            
            # Group by month (year-month)
            monthly_groups = {}
            for snapshot in weekly_snapshots:
                captured_at = datetime.fromisoformat(snapshot["captured_at"].replace("Z", "+00:00"))
                month_key = f"{captured_at.year}-{captured_at.month:02d}"
                
                if month_key not in monthly_groups:
                    monthly_groups[month_key] = []
                monthly_groups[month_key].append(snapshot)
            
            # Create monthly aggregates
            for month_key, snapshots in monthly_groups.items():
                # Use first snapshot's timestamp as the month start
                month_start = datetime.fromisoformat(snapshots[0]["captured_at"].replace("Z", "+00:00"))
                month_start = month_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                # Aggregate: average balance, sum counts
                avg_balance = sum(float(s["total_balance_usd"]) for s in snapshots) / len(snapshots)
                avg_usdc = sum(float(s["usdc_total"]) for s in snapshots) / len(snapshots)
                avg_positions_value = sum(float(s["active_positions_value"]) for s in snapshots) / len(snapshots)
                avg_positions_count = sum(int(s["active_positions_count"]) for s in snapshots) / len(snapshots)
                
                # Use positions from the last snapshot in the month (most recent state)
                last_snapshot = snapshots[-1]
                positions = last_snapshot.get("positions", [])
                
                monthly_snapshot = {
                    "snapshot_type": "monthly",
                    "total_balance_usd": avg_balance,
                    "usdc_total": avg_usdc,
                    "active_positions_value": avg_positions_value,
                    "active_positions_count": int(avg_positions_count),
                    "positions": positions,  # Positions from last snapshot in month
                    "captured_at": month_start.isoformat()
                }
                
                # Check if monthly snapshot already exists for this month
                existing = (
                    self.sb.table("wallet_balance_snapshots")
                    .select("id")
                    .eq("snapshot_type", "monthly")
                    .eq("captured_at", month_start.isoformat())
                    .execute()
                ).data
                
                if existing:
                    logger.debug(f"Monthly snapshot already exists for {month_key}, skipping")
                    continue
                
                # Insert monthly aggregate
                self.sb.table("wallet_balance_snapshots").insert(monthly_snapshot).execute()
                
                # Delete rolled-up weekly snapshots
                snapshot_ids = [s["id"] for s in snapshots]
                for snapshot_id in snapshot_ids:
                    self.sb.table("wallet_balance_snapshots").delete().eq("id", snapshot_id).execute()
                
                logger.info(f"Rolled up {len(snapshots)} weekly snapshots to monthly aggregate for {month_key}")
            
        except Exception as e:
            logger.error(f"Error rolling up monthly snapshots: {e}", exc_info=True)

