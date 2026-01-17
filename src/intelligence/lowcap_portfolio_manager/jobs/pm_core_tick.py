from __future__ import annotations

import asyncio
import os
import logging
import uuid
import statistics
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

from supabase import create_client, Client  # type: ignore
from src.intelligence.lowcap_portfolio_manager.pm.actions import (
    plan_actions_v4,
    _get_pool,
    _on_trim,
    _on_s2_dip_buy,
    _on_dx_buy,
)
from src.intelligence.lowcap_portfolio_manager.pm.levers import compute_levers
from src.intelligence.lowcap_portfolio_manager.pm.ae_calculator_v2 import (
    compute_ae_v2,
    apply_strength_to_ae,
    extract_regime_flags,
    AEConfig,
)
from src.intelligence.lowcap_portfolio_manager.pm.executor import PMExecutor
from src.intelligence.lowcap_portfolio_manager.pm.config import load_pm_config, fetch_and_merge_db_config
from src.intelligence.lowcap_portfolio_manager.pm.exposure import ExposureLookup, ExposureConfig
from src.intelligence.lowcap_portfolio_manager.regime.bucket_context import fetch_bucket_phase_snapshot
from src.intelligence.lowcap_portfolio_manager.pm.pattern_keys_v5 import (
    generate_canonical_pattern_key,
    build_unified_scope,
    map_action_type_to_category,
    extract_controls_from_action
)
from src.intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v4 import Constants
from src.intelligence.lowcap_portfolio_manager.pm.bucketing_helpers import (
    bucket_a_e, bucket_score, bucket_ema_slopes, bucket_size, bucket_bars_since_entry,
    classify_outcome, classify_hold_time
)
from src.intelligence.lowcap_portfolio_manager.jobs.regime_ae_calculator import BUCKET_DRIVERS
from src.intelligence.lowcap_portfolio_manager.learning.trajectory_classifier import record_position_trajectory
from src.intelligence.lowcap_portfolio_manager.pm.episode_blocking import (
    record_attempt_failure,
    record_episode_success,
)


logger = logging.getLogger("pm_core")


def bucket_cf_improvement(missed_rr: Optional[float]) -> str:
    if missed_rr is None or missed_rr < 0.5:
        return "none"
    if missed_rr < 1.0:
        return "small"
    if missed_rr < 2.0:
        return "medium"
    return "large"


# Removed: _map_meso_to_policy() - no longer used (replaced by regime engine)


class PMCoreTick:
    def __init__(self, timeframe: str = "1h", learning_system=None) -> None:
        """
        Initialize PM Core Tick for a specific timeframe.
        
        Args:
            timeframe: Timeframe to process (1m, 15m, 1h, 4h)
            learning_system: Optional learning system instance for processing position_closed strands
        """
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
        self.sb: Client = create_client(url, key)
        self.timeframe = timeframe
        self.learning_system = learning_system  # Store learning system for position_closed strand processing
        
        # Initialize PM Executor (trader=None since we use Li.Fi SDK)
        self.executor = PMExecutor(trader=None, sb_client=self.sb)
        self._exposure_lookup: Optional["ExposureLookup"] = None
        self._regime_state_cache: Dict[str, Dict[str, str]] = {}
        
        # Initialize Telegram Signal Notifier (if enabled)
        self.telegram_notifier = None
        if os.getenv("TELEGRAM_NOTIFICATIONS_ENABLED", "0") == "1":
            try:
                bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
                channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
                api_id = int(os.getenv("TELEGRAM_API_ID", "21826741"))
                api_hash = os.getenv("TELEGRAM_API_HASH", "4643cce207a1a9d56d56a5389a4f1f52")
                
                if bot_token and channel_id:
                    from src.communication.telegram_signal_notifier import TelegramSignalNotifier
                    self.telegram_notifier = TelegramSignalNotifier(
                        bot_token=bot_token,
                        channel_id=channel_id,
                        api_id=api_id,
                        api_hash=api_hash,
                        session_id=self.timeframe  # Unique session per timeframe to avoid database locks
                    )
                    logger.info("Telegram notifications enabled")
                else:
                    logger.warning("TELEGRAM_NOTIFICATIONS_ENABLED=1 but TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not set")
            except Exception as e:
                logger.warning(f"Failed to initialize Telegram notifier: {e}")

    def _fire_and_forget(self, coro, description: str = "notification") -> bool:
        """Run async notification without blocking the trading path.
        
        Uses threading to avoid event loop conflicts with Telethon client.
        Similar pattern to executor's event loop fix.
        """
        import threading
        
        logger.info(f"NOTIFICATION SCHEDULING: {description}")
        
        # Use thread with new event loop to avoid conflicts
        result_container = {"result": False, "exception": None}
        
        def _run_in_thread():
            """Run coroutine in new thread with fresh event loop."""
            try:
                # Create new event loop for this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    result = new_loop.run_until_complete(coro)
                    result_container["result"] = result
                finally:
                    new_loop.close()
            except Exception as e:
                result_container["exception"] = e
        
        thread = threading.Thread(target=_run_in_thread, daemon=True)
        thread.start()
        thread.join(timeout=10)  # 10 second timeout for notifications
        
        if thread.is_alive():
            logger.error(f"NOTIFICATION TIMEOUT: {description} (took >10s)")
            return False
        
        if result_container["exception"]:
            logger.error(f"NOTIFICATION ERROR: {description} - {result_container['exception']}", exc_info=True)
            return False
        
        result = result_container["result"]
        if result:
            logger.info(f"NOTIFICATION SUCCESS: {description}")
        else:
            logger.warning(f"NOTIFICATION FAILED: {description} (returned False)")
        return result

    def _get_regime_driver_states(self, driver: str | None) -> Dict[str, str]:
        """
        Get regime states (S0-S4) for a regime driver across macro/meso/micro (1d/1h/1m).
        
        Args:
            driver: Regime driver ticker (e.g., BTC, ALT, nano, BTC.d)
        
        Returns:
            Dict with keys: macro, meso, micro
        """
        default_state = {"macro": "S4", "meso": "S4", "micro": "S4"}
        if not driver:
            return default_state
        if driver in self._regime_state_cache:
            return self._regime_state_cache[driver]
        
        tf_mapping = {"macro": "1d", "meso": "1h", "micro": "1m"}
        try:
            states: Dict[str, str] = {}
            for horizon, pos_tf in tf_mapping.items():
                result = (
                    self.sb.table("lowcap_positions")
                    .select("state, features")
                    .eq("status", "regime_driver")
                    .eq("token_ticker", driver)
                    .eq("timeframe", pos_tf)
                    .order("updated_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if result.data:
                    row = result.data[0]
                    features = row.get("features") or {}
                    uptrend = features.get("uptrend_engine_v4") or {}
                    state = uptrend.get("state") or row.get("state", "S4")
                    states[horizon] = str(state)
                else:
                    states[horizon] = "S4"
            self._regime_state_cache[driver] = states
            return states
        except Exception as e:
            logger.warning(f"Error fetching regime states for driver {driver}: {e}")
            return default_state

    def _get_bucket_regime_state(self, bucket: str | None) -> Dict[str, str]:
        """Backward-compatible helper for bucket driver only."""
        return self._get_regime_driver_states(bucket)

    def _get_regime_states_bundle(self, token_bucket: Optional[str]) -> Dict[str, str]:
        """
        Build a flat dict of regime states (S0-S4) for BTC, ALT, BUCKET, BTC.d, USDT.d
        across macro/meso/micro horizons.
        """
        drivers = {
            "btc": "BTC",
            "alt": "ALT",
            "btcd": "BTC.d",
            "usdtd": "USDT.d",
        }
        # Bucket driver from token bucket mapping (fallback None)
        bucket_driver = None
        if token_bucket:
            bucket_driver = BUCKET_DRIVERS.get(token_bucket, token_bucket)
        drivers["bucket"] = bucket_driver
        
        bundle: Dict[str, str] = {}
        for prefix, driver in drivers.items():
            states = self._get_regime_driver_states(driver)
            bundle[f"{prefix}_macro"] = states.get("macro", "S4")
            bundle[f"{prefix}_meso"] = states.get("meso", "S4")
            bundle[f"{prefix}_micro"] = states.get("micro", "S4")
        return bundle
    
    def _get_regime_context(self) -> Dict[str, Dict[str, Any]]:
        """
        Get regime context with bucket summaries for regime_context.
        
        Note: Old phase_state table (Dip, Recover, etc.) is no longer used.
        Regime states (S0, S1, S2, S3) are now read from lowcap_positions with status='regime_driver'.
        
        Returns:
            Dict with keys: bucket_phases, bucket_rank, bucket_population.
        """
        regime_context = {}
        
        # Get bucket snapshot (still used for bucket ordering/multipliers)
        bucket_snapshot = fetch_bucket_phase_snapshot(self.sb)
        regime_context["bucket_phases"] = bucket_snapshot.get("bucket_phases", {})
        regime_context["bucket_population"] = bucket_snapshot.get("bucket_population", {})
        regime_context["bucket_rank"] = bucket_snapshot.get("bucket_rank", [])

        return regime_context

    def _swap_profit_to_lotus(self, position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Swap 10% of position profit to Lotus Coin, then transfer 69% of those tokens to holding wallet.
        
        Args:
            position: Position dict with profit information
            
        Returns:
            Dict with:
            - success: bool
            - profit_usd: float
            - swap_amount_usd: float
            - lotus_tokens: float (total received)
            - lotus_tokens_kept: float (31% kept in trading wallet)
            - lotus_tokens_transferred: float (69% sent to holding wallet)
            - swap_tx_hash: str
            - transfer_tx_hash: str (optional)
            - error: str (if failed)
        """
        try:
            # Check if buyback is enabled
            if os.getenv("LOTUS_BUYBACK_ENABLED", "0") != "1":
                return {"success": True, "skipped": True, "reason": "Buyback disabled"}
            
            # Get configuration
            lotus_contract = os.getenv("LOTUS_CONTRACT", "Ch4tXj2qf8V6a4GdpS4X3pxAELvbnkiKTHGdmXjLEXsC")
            holding_wallet = os.getenv("LOTUS_HOLDING_WALLET", "AbumtzzxomWWrm9uypY6ViRgruGdJBPFPM2vyHewTFdd")
            buyback_percentage = float(os.getenv("LOTUS_BUYBACK_PERCENTAGE", "10.0"))
            transfer_percentage = float(os.getenv("LOTUS_TRANSFER_PERCENTAGE", "69.0"))
            
            # Calculate profit
            # Use rpnl_usd (realized P&L) for fully closed positions
            profit_usd = float(position.get("rpnl_usd", 0.0))
            
            # If rpnl_usd not available or zero, calculate from extracted vs allocated
            if profit_usd == 0:
                total_extracted = float(position.get("total_extracted_usd", 0.0))
                total_allocated = float(position.get("total_allocation_usd", 0.0))
                profit_usd = total_extracted - total_allocated
            
            # Only swap if profit is positive
            if profit_usd <= 0:
                return {
                    "success": True,
                    "skipped": True,
                    "reason": f"No profit to swap (profit_usd={profit_usd:.2f})"
                }
            
            # Minimum profit gate: $1.00 minimum profit required
            # (If profit >= $1.00, then 10% buyback >= $0.10, so only one gate needed)
            min_profit_usd = float(os.getenv("LOTUS_BUYBACK_MIN_PROFIT_USD", "1.0"))
            if profit_usd < min_profit_usd:
                return {
                    "success": True,
                    "skipped": True,
                    "reason": f"Profit too small: ${profit_usd:.2f} < ${min_profit_usd:.2f} (min profit gate)"
                }
            
            # Calculate swap amount (10% of profit)
            swap_amount_usd = profit_usd * (buyback_percentage / 100.0)
            
            logger.info(f"Executing Lotus buyback: ${swap_amount_usd:.2f} (10% of ${profit_usd:.2f} profit)")
            
            # Swap USDC → Lotus Coin on Solana
            # USDC has 6 decimals, so convert to smallest unit
            usdc_amount = str(int(swap_amount_usd * 1_000_000))
            
            swap_result = self.executor._call_lifi_executor(
                action="swap",
                chain="solana",
                from_token="USDC",
                to_token=lotus_contract,
                amount=usdc_amount,
                slippage=0.5,  # 0.5% slippage tolerance
                from_chain="solana",
                to_chain="solana"
            )
            
            if not swap_result.get("success"):
                return {
                    "success": False,
                    "error": f"Swap failed: {swap_result.get('error', 'Unknown error')}",
                    "profit_usd": profit_usd,
                    "swap_amount_usd": swap_amount_usd
                }
            
            # Get Lotus tokens received from swap
            # Prefer raw amount + decimals from Li.Fi executor (already returned for SPL tokens)
            tokens_received_raw = swap_result.get("tokens_received_raw") or swap_result.get("toAmount") or swap_result.get("toAmountMin")
            token_decimals = int(swap_result.get("to_token_decimals", 9) or 9)  # SPL tokens use 9 decimals
            try:
                if tokens_received_raw:
                    lotus_tokens = float(tokens_received_raw) / (10 ** token_decimals)
                else:
                    lotus_tokens = float(swap_result.get("tokens_received", 0.0) or 0.0)
            except (ValueError, TypeError, ZeroDivisionError):
                lotus_tokens = 0.0
            
            swap_tx_hash = swap_result.get("tx_hash") or swap_result.get("txHash") or swap_result.get("tx_hash")
            
            logger.info(f"Lotus swap successful: {lotus_tokens:.6f} tokens received (tx: {swap_tx_hash})")
            
            # Transfer 69% to holding wallet
            transfer_amount = lotus_tokens * (transfer_percentage / 100.0)
            transfer_result = None
            
            if transfer_amount > 0:
                try:
                    transfer_result = self._transfer_lotus_to_holding_wallet(transfer_amount, holding_wallet)
                    if not transfer_result or not transfer_result.get("success"):
                        logger.warning(f"Lotus transfer failed: {transfer_result.get('error') if transfer_result else 'Unknown error'}")
                        # Don't fail the whole buyback if transfer fails - tokens are still in trading wallet
                except Exception as e:
                    logger.error(f"Error transferring Lotus tokens: {e}", exc_info=True)
                    # Don't fail the whole buyback if transfer fails
            
            return {
                "success": True,
                "profit_usd": profit_usd,
                "swap_amount_usd": swap_amount_usd,
                "lotus_tokens": lotus_tokens,
                "lotus_tokens_kept": lotus_tokens * (1.0 - transfer_percentage / 100.0),  # 31% kept
                "lotus_tokens_transferred": transfer_amount if transfer_result and transfer_result.get("success") else 0.0,
                "swap_tx_hash": swap_tx_hash,
                "transfer_tx_hash": transfer_result.get("tx_hash") if transfer_result else None,
                "transfer_success": transfer_result.get("success") if transfer_result else False
            }
            
        except Exception as e:
            logger.error(f"Error in Lotus buyback: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _update_buyback_totals(self, lotus_tokens: float, lotus_tokens_transferred: float) -> None:
        """
        Update cumulative buyback totals in wallet_balances table for 'lotus' chain.
        
        Args:
            lotus_tokens: Total Lotus tokens bought back in this buyback
            lotus_tokens_transferred: Total Lotus tokens transferred to holding wallet in this buyback
        """
        try:
            # Get current wallet_balances entry for 'lotus' chain
            result = self.sb.table("wallet_balances").select("*").eq("chain", "lotus").limit(1).execute()
            
            if not result.data:
                # Create new entry with buyback totals
                self.sb.table("wallet_balances").insert({
                    "chain": "lotus",
                    "balance": 0.0,  # Will be updated by WalletManager.update_lotus_wallet_balance()
                    "balance_usd": 0.0,
                    "usdc_balance": 0.0,
                    "wallet_address": os.getenv("LOTUS_HOLDING_WALLET", "AbumtzzxomWWrm9uypY6ViRgruGdJBPFPM2vyHewTFdd"),
                    "positions": {
                        "buyback_totals": {
                            "total_bought_back": float(lotus_tokens),
                            "total_transferred": float(lotus_tokens_transferred)
                        }
                    },
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }).execute()
                logger.info(f"Created new 'lotus' wallet_balances entry with buyback totals: {lotus_tokens:.6f} bought, {lotus_tokens_transferred:.6f} transferred")
            else:
                # Update existing entry - increment buyback totals
                current = result.data[0]
                positions = current.get("positions") or {}
                
                # Get current totals (default to 0 if not present)
                buyback_totals = positions.get("buyback_totals", {})
                current_total_bought = float(buyback_totals.get("total_bought_back", 0.0))
                current_total_transferred = float(buyback_totals.get("total_transferred", 0.0))
                
                # Increment totals
                new_total_bought = current_total_bought + float(lotus_tokens)
                new_total_transferred = current_total_transferred + float(lotus_tokens_transferred)
                
                # Update positions JSONB
                positions["buyback_totals"] = {
                    "total_bought_back": new_total_bought,
                    "total_transferred": new_total_transferred
                }
                
                # Update database
                self.sb.table("wallet_balances").update({
                    "positions": positions,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }).eq("chain", "lotus").execute()
                
                logger.info(
                    f"Updated buyback totals: {new_total_bought:.6f} total bought back "
                    f"({lotus_tokens:.6f} this buyback), {new_total_transferred:.6f} total transferred "
                    f"({lotus_tokens_transferred:.6f} this buyback)"
                )
                
        except Exception as e:
            logger.error(f"Error updating buyback totals in wallet_balances: {e}", exc_info=True)
            # Don't fail the buyback if this update fails
    
    def _transfer_lotus_to_holding_wallet(self, amount: float, holding_wallet: str) -> Optional[Dict[str, Any]]:
        """
        Transfer Lotus tokens to holding wallet using JSSolanaClient.
        
        Args:
            amount: Amount of Lotus tokens to transfer
            holding_wallet: Destination wallet address
            
        Returns:
            Dict with success, tx_hash, error
        """
        try:
            # Get Solana RPC URL and private key from environment
            rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
            private_key = os.getenv("SOLANA_PRIVATE_KEY")
            
            if not private_key:
                return {
                    "success": False,
                    "error": "SOLANA_PRIVATE_KEY not set"
                }
            
            # Import and create JSSolanaClient
            from trading.js_solana_client import JSSolanaClient
            js_client = JSSolanaClient(rpc_url=rpc_url, private_key=private_key)
            
            # Transfer tokens (async method, need to run in event loop)
            import asyncio
            try:
                # Check if we're in an async context
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, create a task
                    # But we're in sync context, so we'll need to use run_until_complete
                    # Actually, we can't use run_until_complete if loop is running
                    # So we'll create a new event loop
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(js_client.send_lotus_tokens(amount, holding_wallet))
                    loop.close()
                else:
                    result = loop.run_until_complete(js_client.send_lotus_tokens(amount, holding_wallet))
            except RuntimeError:
                # No event loop, create one
                result = asyncio.run(js_client.send_lotus_tokens(amount, holding_wallet))
            
            if result.get("success"):
                logger.info(f"Lotus transfer successful: {amount:.6f} tokens → {holding_wallet} (tx: {result.get('tx_hash')})")
                return {
                    "success": True,
                    "tx_hash": result.get("tx_hash") or result.get("signature"),
                    "amount": amount
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Transfer failed"),
                    "amount": amount
                }
                
        except Exception as e:
            logger.error(f"Error transferring Lotus tokens: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "amount": amount
            }

    def _positions_for_exposure(self) -> List[Dict[str, Any]]:
        """
        Fetch positions for exposure calculation.
        Only includes positions with current_usd_value > 0 (actual holdings).
        """
        try:
            res = (
                self.sb.table("lowcap_positions")
                .select("token_contract,token_chain,timeframe,status,current_usd_value,book_id,state,entry_context,features")
                .gt("current_usd_value", 0.0)  # Only positions with actual holdings
                .limit(2000)
                .execute()
            )
            return res.data or []
        except Exception as exc:
            logger.warning(f"Exposure lookup positions failed: {exc}")
            return []

    def _build_exposure_lookup(
        self,
        regime_context: Dict[str, Dict[str, Any]],
        pm_cfg: Dict[str, Any],
    ) -> Optional[ExposureLookup]:
        positions = self._positions_for_exposure()
        if not positions:
            return None
        try:
            exposure_cfg = ExposureConfig.from_pm_config(pm_cfg)
        except Exception as exc:
            logger.warning(f"Exposure config failed: {exc}")
            return None
        try:
            return ExposureLookup.build(positions, exposure_cfg, {})
        except Exception as exc:
            logger.warning(f"Exposure lookup build failed: {exc}")
            return None

    def _active_positions(self) -> List[Dict[str, Any]]:
        """
        Get positions for this timeframe (watchlist + active - skip dormant).
        
        Returns:
            List of positions matching the timeframe and status
        """
        res = (
            self.sb.table("lowcap_positions")
            .select("id,token_contract,token_chain,token_ticker,timeframe,status,features,avg_entry_price,avg_exit_price,total_allocation_usd,total_extracted_usd,total_quantity,total_tokens_bought,total_tokens_sold,total_allocation_pct,entry_context,current_trade_id,book_id")
            .eq("timeframe", self.timeframe)
            .in_("status", ["watchlist", "active"])  # Skip dormant positions
            .limit(2000)
            .execute()
        )
        return res.data or []

    def _fetch_token_buckets(self, keys: List[tuple[str, str | None]]) -> Dict[tuple[str, str | None], str]:
        contracts = sorted({k[0] for k in keys if k and k[0]})
        if not contracts:
            return {}
        try:
            res = (
                self.sb.table("token_cap_bucket")
                .select("token_contract,chain,bucket")
                .in_("token_contract", contracts)
                .execute()
            )
        except Exception as exc:
            logger.warning(f"Error fetching token cap buckets: {exc}")
            return {}
        rows = res.data or []
        out: Dict[tuple[str, str | None], str] = {}
        for row in rows:
            token = row.get("token_contract")
            chain = row.get("chain")
            bucket = row.get("bucket")
            if token and bucket:
                out[(token, chain)] = bucket
        return out

    @staticmethod
    def _generate_episode_id(prefix: str = "epi") -> str:
        return f"{prefix}_{uuid.uuid4().hex}"

    @staticmethod
    def _iso_to_datetime(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    def _ensure_episode_meta(self, features: Dict[str, Any]) -> Dict[str, Any]:
        meta = features.get("uptrend_episode_meta")
        if not isinstance(meta, dict):
            meta = {}
        meta.setdefault("s1_episode", None)
        meta.setdefault("s2_episode", None)  # Phase 7: S2 episode tracking
        meta.setdefault("s3_episode", None)
        meta.setdefault("last_consumed_s1_buy_ts", None)
        meta.setdefault("last_consumed_s2_buy_ts", None)  # Phase 7: S2 tracking
        meta.setdefault("last_consumed_s3_buy_ts", None)
        meta.setdefault("last_consumed_trim_ts", None)
        meta.setdefault("dx_episode_ids", [])  # Phase 7: Track DX episode IDs for outcome updates
        features["uptrend_episode_meta"] = meta
        return meta

    def _log_episode_event(
        self,
        window: Dict[str, Any],
        scope: Dict[str, Any],
        pattern_key: str,
        decision: str,
        factors: Dict[str, Any],
        episode_id: str,
        trade_id: Optional[str] = None,
    ) -> Optional[int]:
        """Log an episode event to pattern_episode_events table."""
        try:
            payload = {
                "scope": scope,
                "pattern_key": pattern_key,
                "episode_id": episode_id,
                "decision": decision,
                "factors": factors,
                "outcome": None, # Pending
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trade_id": trade_id
            }
            res = self.sb.table("pattern_episode_events").insert(payload).execute()
            if res.data:
                return res.data[0].get("id")
        except Exception as e:
            logger.warning(f"Failed to log episode event: {e}")
        return None

    def _update_episode_outcome(self, db_ids: List[int], outcome: str) -> None:
        """Update outcome for a list of episode event IDs."""
        if not db_ids:
            return
        try:
            self.sb.table("pattern_episode_events").update({"outcome": outcome}).in_("id", db_ids).execute()
        except Exception as e:
            logger.warning(f"Failed to update episode outcomes: {e}")

    def _update_episode_outcomes_from_meta(self, episode: Dict[str, Any], outcome: str) -> None:
        """Helper to collect db_ids from episode windows and update outcomes."""
        windows = episode.get("windows") or []
        ids = []
        for w in windows:
            if w.get("db_id"):
                ids.append(w.get("db_id"))
        if ids:
            self._update_episode_outcome(ids, outcome)

    def _sync_s3_window_outcomes_to_db(self, episode: Dict[str, Any]) -> None:
        """Helper to sync S3 window-specific outcomes to DB."""
        windows = episode.get("windows") or []
        # Group by outcome to batch updates
        by_outcome: Dict[str, List[int]] = {}
        for w in windows:
            db_id = w.get("db_id")
            outcome = w.get("outcome")
            if db_id and outcome:
                by_outcome.setdefault(outcome, []).append(db_id)
        
        for outcome, ids in by_outcome.items():
            self._update_episode_outcome(ids, outcome)

    def _capture_s1_window_sample(self, uptrend: Dict[str, Any], now: datetime, levers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        diagnostics = (uptrend.get("diagnostics") or {}).get("buy_check") or {}
        ema_vals = uptrend.get("ema") or {}
        price = float(uptrend.get("price", 0.0))
        ema60 = float(ema_vals.get("ema60", 0.0))
        atr = float(diagnostics.get("atr", 0.0))
        halo = float(diagnostics.get("halo", 0.0))
        halo_dist = None
        if atr > 0 and ema60 > 0:
            halo_dist = abs(price - ema60) / atr

        sample = {
            "ts": now.isoformat(),
            "ts_score": float(diagnostics.get("ts_score", 0.0)),
            "ts_with_boost": float(diagnostics.get("ts_with_boost", 0.0)),
            "sr_boost": float(diagnostics.get("sr_boost", 0.0)),
            "entry_zone_ok": bool(diagnostics.get("entry_zone_ok")),
            "slope_ok": bool(diagnostics.get("slope_ok")),
            "ts_ok": bool(diagnostics.get("ts_ok")),
            "ema60_slope": float(diagnostics.get("ema60_slope", 0.0)),
            "ema144_slope": float(diagnostics.get("ema144_slope", 0.0)),
            "halo": halo,
            "halo_distance": halo_dist,
            "price": price,
            "ema60": ema60,
        }
        
        if levers:
            sample["a_value"] = float(levers.get("A_value", 0.0))
            sample["position_size_frac"] = float(levers.get("position_size_frac", 0.0))
            
        return sample

    def _capture_s2_window_sample(self, uptrend: Dict[str, Any], now: datetime, levers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Capture S2 window sample for tuning learning.
        
        S2 is the "danger zone" between S1 and S3 where price is above EMA333
        but full alignment hasn't been achieved yet. S2 buy opportunities happen
        when buy_flag is set during S2 state.
        
        Phase 7: S2 episode tracking for tuning.
        """
        diagnostics = (uptrend.get("diagnostics") or {}).get("buy_check") or {}
        ema_vals = uptrend.get("ema") or {}
        scores = uptrend.get("scores") or {}
        price = float(uptrend.get("price", 0.0))
        ema60 = float(ema_vals.get("ema60", 0.0))
        ema144 = float(ema_vals.get("ema144", 0.0))
        ema333 = float(ema_vals.get("ema333", 0.0))
        atr = float(diagnostics.get("atr", 0.0))
        halo = float(diagnostics.get("halo", 0.0))
        
        # S2 halo distance: how far from EMA60 in ATR units
        halo_dist = None
        if atr > 0 and ema60 > 0:
            halo_dist = abs(price - ema60) / atr
        
        # Price position between EMA333 and EMA144 (for S2, EMA144 may be below EMA333)
        price_pos = None
        if ema333 > 0 and ema144 > 0:
            band_width = abs(ema144 - ema333)
            if band_width > 0:
                price_pos = (price - min(ema333, ema144)) / band_width
                price_pos = max(0.0, min(1.0, price_pos))

        sample = {
            "ts": now.isoformat(),
            "ts_score": float(diagnostics.get("ts_score", 0.0)),
            "ts_with_boost": float(diagnostics.get("ts_with_boost", 0.0)),
            "sr_boost": float(diagnostics.get("sr_boost", 0.0)),
            "entry_zone_ok": bool(diagnostics.get("entry_zone_ok")),
            "slope_ok": bool(diagnostics.get("slope_ok")),
            "ts_ok": bool(diagnostics.get("ts_ok")),
            "ema60_slope": float(diagnostics.get("ema60_slope", 0.0)),
            "ema144_slope": float(diagnostics.get("ema144_slope", 0.0)),
            "ema250_slope": float(diagnostics.get("ema250_slope", 0.0)),
            "ema333_slope": float(diagnostics.get("ema333_slope", 0.0)),
            "halo": halo,
            "halo_distance": halo_dist,
            "price": price,
            "price_pos": price_pos,
            "ema60": ema60,
            "ema144": ema144,
            "ema333": ema333,
            "dx_score": float(scores.get("dx", 0.0)),  # Include DX for S2 context
        }
        
        if levers:
            sample["a_value"] = float(levers.get("A_value", 0.0))
            sample["position_size_frac"] = float(levers.get("position_size_frac", 0.0))
            
        return sample

    def _capture_s3_window_sample(self, uptrend: Dict[str, Any], now: datetime, levers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        scores = uptrend.get("scores") or {}
        ema_vals = uptrend.get("ema") or {}
        diagnostics = (uptrend.get("diagnostics") or {}).get("s3_buy_check") or {}
        slopes = diagnostics or {}
        price = float(uptrend.get("price", 0.0))
        ema144 = float(ema_vals.get("ema144", 0.0))
        ema333 = float(ema_vals.get("ema333", 0.0))
        price_pos = None
        band_width = abs(ema144 - ema333)
        if band_width > 0:
            if ema144 >= ema333:
                ratio = (price - ema333) / band_width
            else:
                ratio = (price - ema144) / band_width
            ratio = max(0.0, min(1.0, ratio))
            price_pos = 1.0 - ratio if ema144 >= ema333 else ratio

        sample = {
            "ts": now.isoformat(),
            "ts_score": float(scores.get("ts", 0.0)),
            "dx_score": float(scores.get("dx", 0.0)),
            "edx_score": float(scores.get("edx", 0.0)),
            "price": price,
            "price_pos": price_pos,
            "ema144": ema144,
            "ema333": ema333,
            "ema250_slope": float(slopes.get("ema250_slope", 0.0)),
            "ema333_slope": float(slopes.get("ema333_slope", 0.0)),
        }
        
        if levers:
            sample["a_value"] = float(levers.get("A_value", 0.0))
            sample["position_size_frac"] = float(levers.get("position_size_frac", 0.0))

        return sample

    @staticmethod
    def _summarize_window_samples(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not samples:
            return {}

        def collect(key: str) -> List[float]:
            vals = []
            for s in samples:
                val = s.get(key)
                if isinstance(val, (int, float)):
                    vals.append(float(val))
            return vals

        summary: Dict[str, Any] = {}
        summary["sample_count"] = len(samples)
        metrics = [
            "ts_score",
            "ts_with_boost",
            "sr_boost",
            "dx_score",
            "edx_score",
            "price_pos",
            "ema60_slope",
            "ema144_slope",
            "ema250_slope",
            "ema333_slope",
            "halo_distance",
        ]
        for metric in metrics:
            values = collect(metric)
            if values:
                summary[metric] = {
                    "min": min(values),
                    "max": max(values),
                    "median": statistics.median(values),
                }
        summary["sample_count"] = len(samples)
        return summary

    @staticmethod
    def _make_lever_entry(lever: str, delta: float, confidence: float, severity_cap: float) -> Dict[str, Any]:
        severity_cap = max(severity_cap, 1e-6)
        severity = min(1.0, abs(delta) / severity_cap)
        direction = "tighten" if delta > 0 else "loosen"
        return {
            "lever": lever,
            "delta": delta,
            "severity": severity,
            "signal_confidence": max(0.0, min(1.0, confidence)),
            "direction": direction,
        }

    def _compute_lever_considerations(self, episode: Dict[str, Any], episode_type: str) -> List[Dict[str, Any]]:
        windows = episode.get("windows") or []
        total_samples = 0
        for w in windows:
            summary = w.get("summary") or {}
            sample_count = summary.get("sample_count") or len(w.get("samples") or [])
            total_samples += sample_count
        if total_samples <= 0:
            total_samples = len(windows) or 1

        considerations: List[Dict[str, Any]] = []

        for win in windows:
            summary = win.get("summary") or {}
            sample_count = summary.get("sample_count") or len(win.get("samples") or [])
            if sample_count <= 0:
                continue
            confidence = sample_count / max(total_samples, 1)

            if episode_type == "s1_entry":
                ts_summary = summary.get("ts_with_boost") or {}
                median_ts = ts_summary.get("median")
                if median_ts is not None:
                    delta = Constants.TS_THRESHOLD - median_ts
                    considerations.append(self._make_lever_entry("ts_min", delta, confidence, 0.10))

                sr_summary = summary.get("sr_boost") or {}
                median_sr = sr_summary.get("median")
                if median_sr is not None:
                    target_sr = Constants.SR_BOOST_MAX * 0.5
                    delta = target_sr - median_sr
                    considerations.append(self._make_lever_entry("sr_boost", delta, confidence, Constants.SR_BOOST_MAX))

                slope60 = (summary.get("ema60_slope") or {}).get("median")
                if slope60 is not None:
                    delta = 0.0 - slope60
                    considerations.append(self._make_lever_entry("ema60_slope_min", delta, confidence, 0.02))

                slope144 = (summary.get("ema144_slope") or {}).get("median")
                if slope144 is not None:
                    delta = 0.0 - slope144
                    considerations.append(self._make_lever_entry("ema144_slope_min", delta, confidence, 0.02))

                halo_dist = (summary.get("halo_distance") or {}).get("median")
                if halo_dist is not None:
                    delta = halo_dist - Constants.ENTRY_HALO_ATR_MULTIPLIER
                    considerations.append(self._make_lever_entry("halo_multiplier", delta, confidence, 0.20))

            elif episode_type == "s3_retest":
                dx_summary = summary.get("dx_score") or {}
                median_dx = dx_summary.get("median")
                if median_dx is not None:
                    delta = Constants.DX_BUY_THRESHOLD - median_dx
                    considerations.append(self._make_lever_entry("dx_min", delta, confidence, 0.10))

                edx_summary = summary.get("edx_score") or {}
                median_edx = edx_summary.get("median")
                if median_edx is not None:
                    delta = median_edx - 0.5
                    considerations.append(self._make_lever_entry("edx_supp_mult", delta, confidence, 0.20))

                slope250 = (summary.get("ema250_slope") or {}).get("median")
                if slope250 is not None:
                    delta = 0.0 - slope250
                    considerations.append(self._make_lever_entry("ema250_slope_min", delta, confidence, 0.02))

                slope333 = (summary.get("ema333_slope") or {}).get("median")
                if slope333 is not None:
                    delta = 0.0 - slope333
                    considerations.append(self._make_lever_entry("ema333_slope_min", delta, confidence, 0.02))

                price_pos = (summary.get("price_pos") or {}).get("median")
                if price_pos is not None:
                    delta = 0.5 - price_pos
                    considerations.append(self._make_lever_entry("price_band_bias", delta, confidence, 0.50))

        return considerations

    def _append_window_sample(self, window: Dict[str, Any], sample: Dict[str, Any]) -> None:
        samples = window.setdefault("samples", [])
        samples.append(sample)
        max_samples = 12
        if len(samples) > max_samples:
            trimmed = [samples[0]]
            trimmed.extend(samples[-(max_samples - 1):])
            window["samples"] = trimmed

    def _finalize_active_window(
        self, 
        episode: Dict[str, Any], 
        now: datetime,
        position: Optional[Dict[str, Any]] = None,
        regime_context: Optional[Dict[str, Any]] = None,
        token_bucket: Optional[str] = None,
        uptrend_signals: Optional[Dict[str, Any]] = None,
        levers: Optional[Dict[str, Any]] = None,
    ) -> bool:
        active = episode.get("active_window")
        if not active:
            return False
        if "ended_at" not in active:
            active["ended_at"] = now.isoformat()
        samples = active.get("samples", [])
        active["summary"] = self._summarize_window_samples(samples)
        
        # Log to pattern_episode_events if context is provided
        if not position:
            logger.debug(
                f"Skipping episode event logging: position is None | "
                f"window_id={active.get('window_id')} | episode_id={episode.get('episode_id')}"
            )
        elif not uptrend_signals:
            logger.debug(
                f"Skipping episode event logging: uptrend_signals is None | "
                f"window_id={active.get('window_id')} | episode_id={episode.get('episode_id')}"
            )
        else:
            try:
                decision = "acted" if active.get("entered") else "skipped"
                
                # Determine pattern key and scope
                window_type = active.get("window_type") # s1_buy_signal, s2_buy_flag, or None (s3)
                episode_id_str = (episode.get("episode_id") or "")
                is_s1 = window_type == "s1_buy_signal" or episode_id_str.startswith("s1_")
                is_s2 = window_type == "s2_buy_flag" or episode_id_str.startswith("s2_")
                
                # Set state and action type based on window type
                if is_s1:
                    state = "S1"
                    action_type = "entry"
                elif is_s2:
                    state = "S2"
                    action_type = "entry"  # S2 is also an entry opportunity
                else:
                    state = "S3"
                    action_type = "add"
                
                # Build scope
                pattern_key, _, scope = self._build_pattern_scope(
                    position=position,
                    uptrend_signals=uptrend_signals,
                    action_type=action_type,
                    regime_context=regime_context or {},
                    token_bucket=token_bucket,
                    state=state
                )
                
                if not pattern_key:
                    logger.warning(
                        f"Failed to generate pattern_key for episode window | "
                        f"window_id={active.get('window_id')} | window_type={window_type} | "
                        f"episode_id={episode_id_str} | state={state} | action_type={action_type}"
                    )
                elif not scope:
                    logger.warning(
                        f"Failed to generate scope for episode window | "
                        f"window_id={active.get('window_id')} | position_id={position.get('id')}"
                    )
                else:
                    # Merge levers into summary for factors
                    factors = active.get("summary") or {}
                    if levers:
                        factors["a_value"] = float(levers.get("A_value", 0.0))
                        factors["position_size_frac"] = float(levers.get("position_size_frac", 0.0))
                        
                    # Log event
                    db_id = self._log_episode_event(
                        window=active,
                        scope=scope,
                        pattern_key=pattern_key,
                        decision=decision,
                        factors=factors,
                        episode_id=active.get("window_id") or episode.get("episode_id"),
                        trade_id=position.get("current_trade_id") if decision == "acted" else None
                    )
                    if db_id:
                        active["db_id"] = db_id
                    else:
                        logger.warning(
                            f"Failed to get db_id from episode event insert | "
                            f"window_id={active.get('window_id')} | episode_id={episode_id_str} | "
                            f"decision={decision} | pattern_key={pattern_key}"
                        )
                        
            except Exception as e:
                logger.warning(
                    f"Error finalizing active window logging: {e} | "
                    f"window_id={active.get('window_id')} | episode_id={episode.get('episode_id')}",
                    exc_info=True
                )

        episode.setdefault("windows", []).append(active)
        episode["active_window"] = None
        return True

    def _compute_s3_window_outcomes(self, episode: Dict[str, Any]) -> None:
        windows = episode.get("windows") or []
        trimmed = episode.get("trimmed")
        
        for win in windows:
            if win.get("outcome"):
                continue
            
            # Success if we trimmed (actual) or if a trim signal fired (virtual/missed)
            if (win.get("entered") and win.get("trim_timestamp")) or trimmed:
                    win["outcome"] = "success"
            
            # Note: Failures are handled on S3 -> S0 transition or explicitly if needed.
            # We leave outcome as None if pending.

    def _compute_s3_episode_outcome(self, episode: Dict[str, Any]) -> str:
        windows = episode.get("windows") or []
        entered = [w for w in windows if w.get("entered")]
        if entered:
            if any(w.get("outcome") == "success" for w in entered):
                return "success"
            return "failure"
        if any((w.get("samples") or w.get("summary")) for w in windows):
            return "missed"
        return "correct_skip"

    def _build_pattern_scope(
        self,
        position: Dict[str, Any],
        uptrend_signals: Dict[str, Any],
        action_type: str,
        regime_context: Dict[str, Any],
        token_bucket: Optional[str],
        state: str,
        levers: Optional[Dict[str, Any]] = None,
        regime_states: Optional[Dict[str, str]] = None,
    ) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
        if regime_states is None:
            regime_states = self._get_regime_states_bundle(token_bucket)
        a_val = 0.5
        e_val = 0.5
        if levers:
            a_val = float(levers.get("A_value", 0.5))
            e_val = float(levers.get("E_value", 0.5))

        action_context = {
            "state": state,
            "timeframe": position.get("timeframe", self.timeframe),
            "market_family": "lowcaps",
            "buy_signal": state == "S1",
            "buy_flag": state == "S3",
            "a_final": a_val,
            "e_final": e_val,
        }
        try:
            pattern_key, action_category = generate_canonical_pattern_key(
                module="pm",
                action_type=action_type,
                action_context=action_context,
                uptrend_signals=uptrend_signals,
            )
        except Exception:
            pattern_key = None
            action_category = None

        bucket_rank = (regime_context or {}).get("bucket_rank", [])
        
        # Build entry_context for scope with available data
        # Merge position.entry_context with explicit overrides
        pos_entry_ctx = position.get("entry_context") or {}
        scope_entry_context = {
            "mcap_bucket": token_bucket or pos_entry_ctx.get("mcap_bucket"),
            "vol_bucket": pos_entry_ctx.get("vol_bucket"),
            "age_bucket": pos_entry_ctx.get("age_bucket"),
            "curator": pos_entry_ctx.get("curator"),
            "intent": pos_entry_ctx.get("intent"),
            "book_id": position.get("book_id") or pos_entry_ctx.get("book_id"),
            # Meso bins from position's entry_context
            "opp_meso_bin": pos_entry_ctx.get("opp_meso_bin"),
            "conf_meso_bin": pos_entry_ctx.get("conf_meso_bin"),
            "riskoff_meso_bin": pos_entry_ctx.get("riskoff_meso_bin"),
            "bucket_rank_meso_bin": pos_entry_ctx.get("bucket_rank_meso_bin"),
        }
        
        try:
            scope = build_unified_scope(
                position=position,
                entry_context=scope_entry_context,
                regime_context=regime_context or {},
            )
        except Exception:
            scope = {}
        return pattern_key, action_category, scope

    def _build_stage_transition_strand(
        self,
        position: Dict[str, Any],
        from_state: Optional[str],
        to_state: Optional[str],
        uptrend_signals: Dict[str, Any],
        regime_context: Dict[str, Any],
        token_bucket: Optional[str],
        now: datetime,
        episode_id: Optional[str] = None,
        levers: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        pattern_key, action_category, scope = self._build_pattern_scope(
            position=position,
            uptrend_signals=uptrend_signals,
            action_type="entry" if to_state == "S1" else "add",
            regime_context=regime_context,
            token_bucket=token_bucket,
            state=to_state or "Unknown",
            levers=levers,
        )
        position_id = position.get("id")
        timeframe = position.get("timeframe", self.timeframe)
        symbol = position.get("token_ticker") or position.get("token_contract")

        content = {
            "position_id": position_id,
            "episode_id": episode_id,
            "from_state": from_state,
            "to_state": to_state,
            "pattern_key": pattern_key,
            "action_category": action_category,
            "scope": scope,
            "ts": now.isoformat(),
        }

        strand = {
            "id": f"uptrend_stage_{position_id}_{int(now.timestamp() * 1000)}",
            "module": "pm",
            "kind": "uptrend_stage_transition",
            "symbol": symbol,
            "timeframe": timeframe,
            "position_id": position_id,
            "trade_id": position.get("current_trade_id"),
            "content": content,
            "regime_context": regime_context or {},
            "tags": ["uptrend", "stage_transition"],
            "target_agent": "learning_system",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        return strand

    def _update_episode_entry_flags(self, meta: Dict[str, Any], features: Dict[str, Any]) -> bool:
        changed = False
        execution_history = features.get("pm_execution_history") or {}
        last_s1_buy = execution_history.get("last_s1_buy") or {}
        last_ts = last_s1_buy.get("timestamp")
        if last_ts:
            episode = meta.get("s1_episode")
            consumed = meta.get("last_consumed_s1_buy_ts")
            if episode and consumed != last_ts:
                started_at = episode.get("started_at")
                started_dt = self._iso_to_datetime(started_at)
                ts_dt = self._iso_to_datetime(last_ts)
                if started_dt and ts_dt and ts_dt >= started_dt:
                    episode["entered"] = True
                    active_window = episode.get("active_window")
                    if active_window:
                        active_window["entered"] = True
                        active_window["entry_timestamp"] = last_ts
                    meta["last_consumed_s1_buy_ts"] = last_ts
                    changed = True
        # Phase 7: S2 entry flag tracking
        last_s2_buy = execution_history.get("last_s2_buy") or {}
        last_s2_ts = last_s2_buy.get("timestamp")
        if last_s2_ts:
            s2_episode = meta.get("s2_episode")
            consumed = meta.get("last_consumed_s2_buy_ts")
            if s2_episode and consumed != last_s2_ts:
                started_at = s2_episode.get("started_at")
                started_dt = self._iso_to_datetime(started_at)
                ts_dt = self._iso_to_datetime(last_s2_ts)
                if started_dt and ts_dt and ts_dt >= started_dt:
                    s2_episode["entered"] = True
                    active_window = s2_episode.get("active_window")
                    if active_window:
                        active_window["entered"] = True
                        active_window["entry_timestamp"] = last_s2_ts
                    meta["last_consumed_s2_buy_ts"] = last_s2_ts
                    changed = True
        s3_episode = meta.get("s3_episode")
        last_s3_buy = execution_history.get("last_s3_buy") or {}
        last_s3_ts = last_s3_buy.get("timestamp")
        if s3_episode and last_s3_ts:
            consumed = meta.get("last_consumed_s3_buy_ts")
            active = s3_episode.get("active_window")
            if active and consumed != last_s3_ts:
                start_dt = self._iso_to_datetime(active.get("started_at"))
                buy_dt = self._iso_to_datetime(last_s3_ts)
                if start_dt and buy_dt and buy_dt >= start_dt:
                    active["entered"] = True
                    active["entry_timestamp"] = last_s3_ts
                    meta["last_consumed_s3_buy_ts"] = last_s3_ts
                    changed = True
        last_trim = execution_history.get("last_trim") or {}
        last_trim_ts = last_trim.get("timestamp")
        if s3_episode and last_trim_ts and meta.get("last_consumed_trim_ts") != last_trim_ts:
            trim_dt = self._iso_to_datetime(last_trim_ts)
            
            # Check against episode start for Virtual Success
            episode_start = s3_episode.get("started_at")
            episode_start_ts = self._iso_to_datetime(episode_start)
            
            if trim_dt and episode_start_ts and trim_dt > episode_start_ts:
                if not s3_episode.get("trimmed"):
                    s3_episode["trimmed"] = True
                    changed = True
            
            meta["last_consumed_trim_ts"] = last_trim_ts

        return changed

    def _process_episode_logging(
        self,
        position: Dict[str, Any],
        regime_context: Dict[str, Any],
        token_bucket: Optional[str],
        now: datetime,
        levers: Dict[str, Any] = None,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        features = position.get("features") or {}
        uptrend = features.get("uptrend_engine_v4") or {}
        if not uptrend:
            return [], False

        meta = self._ensure_episode_meta(features)
        strands: List[Dict[str, Any]] = []
        changed = False

        flags_changed = self._update_episode_entry_flags(meta, features)
        changed |= flags_changed
        
        # If flags changed (e.g. trim), sync outcomes immediately for S3 windows
        if flags_changed:
            s3_episode = meta.get("s3_episode")
            if s3_episode:
                self._compute_s3_window_outcomes(s3_episode)
                self._sync_s3_window_outcomes_to_db(s3_episode)

        state = uptrend.get("state")
        prev_state = meta.get("prev_state")

        if state and prev_state is None:
            meta["prev_state"] = state
            changed = True
            prev_state = state

        if state and prev_state and prev_state != state:
            episode_id = None
            # S1 episode now only starts after S2 breakout has occurred (retest phase)
            # This ensures we only buy S1 retests after breakout confirmation
            if state == "S1" and prev_state == "S2":
                s2_episode = meta.get("s2_episode")
                if s2_episode:  # Only create S1 episode if S2 breakout has occurred
                    episode_id = self._generate_episode_id("s1")
                    meta["s1_episode"] = {
                        "episode_id": episode_id,
                        "started_at": now.isoformat(),
                        "entered": False,
                        "windows": [],
                        "active_window": None,
                    }
                    changed = True
                    logger.debug("PHASE7: Started S1 episode (retest phase) %s for position", episode_id)
            # Phase 7: S2 episode starts when transitioning to S2 from S1 (first time in attempt)
            elif state == "S2" and prev_state == "S1" and not meta.get("s2_episode"):
                episode_id = self._generate_episode_id("s2")
                meta["s2_episode"] = {
                    "episode_id": episode_id,
                    "started_at": now.isoformat(),
                    "entered": False,
                    "windows": [],
                    "active_window": None,
                }
                changed = True
                logger.debug("PHASE7: Started S2 episode %s for position", episode_id)
            elif state == "S3" and prev_state != "S3":
                episode_id = self._generate_episode_id("s3")
                meta["s3_episode"] = {
                    "episode_id": episode_id,
                    "started_at": now.isoformat(),
                    "windows": [],
                    "retest_index": 0,
                    "entered": False,
                    "active_window": None,
                }
                changed = True
            strand = self._build_stage_transition_strand(
                position=position,
                from_state=prev_state,
                to_state=state,
                uptrend_signals=uptrend,
                regime_context=regime_context,
                token_bucket=token_bucket,
                now=now,
                episode_id=episode_id,
                levers=levers,
            )
            strands.append(strand)

            s1_episode = meta.get("s1_episode")
            if s1_episode:
                if state == "S3":
                    outcome = "success"
                    # Update DB outcomes for all windows in this episode
                    self._update_episode_outcomes_from_meta(s1_episode, outcome)
                    
                    # Record episode success to unblock (if blocked)
                    try:
                        record_episode_success(
                            sb_client=self.sb,
                            token_contract=position.get("token_contract", ""),
                            token_chain=position.get("token_chain", ""),
                            timeframe=position.get("timeframe", ""),
                            book_id=position.get("book_id", "onchain_crypto")
                        )
                    except Exception as e:
                        logger.warning(f"Failed to record episode success for blocking: {e}")
                    
                    s1_episode.pop("active_window", None)
                    strands.append(
                        self._build_episode_summary_strand(
                            position=position,
                            episode=s1_episode,
                            outcome="missed" if not s1_episode.get("entered") else "success", # Keep legacy string for strand
                            regime_context=regime_context,
                            token_bucket=token_bucket,
                            now=now,
                            episode_type="s1_entry",
                            levers=levers,
                        )
                    )
                    meta["s1_episode"] = None
                    changed = True
                elif state == "S0" and prev_state in ("S1", "S2"):
                    outcome = "failure"
                    # Update DB outcomes for all windows in this episode
                    self._update_episode_outcomes_from_meta(s1_episode, outcome)

                    # Record blocking failure if we entered S1
                    if s1_episode.get("entered"):
                        try:
                            # Check if S2 also entered in this attempt (need to check s2_episode before it's cleared)
                            s2_episode = meta.get("s2_episode")
                            entered_s2 = s2_episode.get("entered", False) if s2_episode else False
                            
                            # Get P&L to check if we lost money (only block if P&L < 0)
                            total_pnl_usd = float(position.get("total_pnl_usd", 0.0) or 0.0)
                            
                            record_attempt_failure(
                                sb_client=self.sb,
                                token_contract=position.get("token_contract", ""),
                                token_chain=position.get("token_chain", ""),
                                timeframe=position.get("timeframe", ""),
                                entered_s1=True,
                                entered_s2=entered_s2,
                                total_pnl_usd=total_pnl_usd,
                                book_id=position.get("book_id", "onchain_crypto")
                            )
                        except Exception as e:
                            logger.warning(f"Failed to record attempt failure for blocking: {e}")

                    s1_episode.pop("active_window", None)
                    strands.append(
                        self._build_episode_summary_strand(
                            position=position,
                            episode=s1_episode,
                            outcome="correct_skip" if not s1_episode.get("entered") else "failure", # Keep legacy string for strand
                            regime_context=regime_context,
                            token_bucket=token_bucket,
                            now=now,
                            episode_type="s1_entry",
                            levers=levers,
                        )
                    )
                    meta["s1_episode"] = None
                    changed = True

            # Phase 7: S2 episode outcome handling
            s2_episode = meta.get("s2_episode")
            if s2_episode:
                if state == "S3":
                    # S2 episode succeeded - attempt reached S3
                    outcome = "success"
                    self._update_episode_outcomes_from_meta(s2_episode, outcome)
                    
                    # Record episode success to unblock (if blocked)
                    try:
                        record_episode_success(
                            sb_client=self.sb,
                            token_contract=position.get("token_contract", ""),
                            token_chain=position.get("token_chain", ""),
                            timeframe=position.get("timeframe", ""),
                            book_id=position.get("book_id", "onchain_crypto")
                        )
                    except Exception as e:
                        logger.warning(f"Failed to record episode success for blocking: {e}")
                    
                    s2_episode.pop("active_window", None)
                    strands.append(
                        self._build_episode_summary_strand(
                            position=position,
                            episode=s2_episode,
                            outcome="missed" if not s2_episode.get("entered") else "success",
                            regime_context=regime_context,
                            token_bucket=token_bucket,
                            now=now,
                            episode_type="s2_entry",
                            levers=levers,
                        )
                    )
                    meta["s2_episode"] = None
                    changed = True
                    logger.debug("PHASE7: S2 episode success for position")
                elif state == "S0":
                    # S2 episode failed - attempt ended at S0
                    outcome = "failure"
                    self._update_episode_outcomes_from_meta(s2_episode, outcome)
                    
                    # Record blocking failure if we entered S2
                    # Note: If S1 also failed in this attempt, it was already recorded above.
                    # Since record_attempt_failure uses upsert, calling it again is safe.
                    if s2_episode.get("entered"):
                        try:
                            # Check if S1 also entered in this attempt
                            # s1_episode may have been cleared above (set to None), so check safely
                            s1_episode = meta.get("s1_episode")
                            entered_s1 = False
                            if s1_episode:  # Check if it exists (not None)
                                entered_s1 = s1_episode.get("entered", False)
                            
                            # Get P&L to check if we lost money (only block if P&L < 0)
                            total_pnl_usd = float(position.get("total_pnl_usd", 0.0) or 0.0)
                            
                            record_attempt_failure(
                                sb_client=self.sb,
                                token_contract=position.get("token_contract", ""),
                                token_chain=position.get("token_chain", ""),
                                timeframe=position.get("timeframe", ""),
                                entered_s1=entered_s1,
                                entered_s2=True,
                                total_pnl_usd=total_pnl_usd,
                                book_id=position.get("book_id", "onchain_crypto")
                            )
                        except Exception as e:
                            logger.warning(f"Failed to record attempt failure for blocking: {e}")
                    
                    s2_episode.pop("active_window", None)
                    strands.append(
                        self._build_episode_summary_strand(
                            position=position,
                            episode=s2_episode,
                            outcome="correct_skip" if not s2_episode.get("entered") else "failure",
                            regime_context=regime_context,
                            token_bucket=token_bucket,
                            now=now,
                            episode_type="s2_entry",
                            levers=levers,
                        )
                    )
                    meta["s2_episode"] = None
                    changed = True
                    logger.debug("PHASE7: S2 episode failure for position")

            # Phase 7: Update DX episode outcomes on terminal state transitions
            dx_episode_ids = meta.get("dx_episode_ids", [])
            if dx_episode_ids:
                if state == "S3":
                    # DX episodes succeeded - recovery worked
                    self._update_episode_outcome(dx_episode_ids, "success")
                    meta["dx_episode_ids"] = []
                    changed = True
                    logger.debug("PHASE7: Updated %d DX episodes to success", len(dx_episode_ids))
                elif state == "S0":
                    # DX episodes failed - attempt ended at S0
                    self._update_episode_outcome(dx_episode_ids, "failure")
                    meta["dx_episode_ids"] = []
                    changed = True
                    logger.debug("PHASE7: Updated %d DX episodes to failure", len(dx_episode_ids))

            s3_episode = meta.get("s3_episode")
            if s3_episode and state == "S0":
                changed |= self._finalize_active_window(s3_episode, now, position, regime_context, token_bucket, uptrend, levers)
                self._compute_s3_window_outcomes(s3_episode)
                s3_outcome = self._compute_s3_episode_outcome(s3_episode)
                s3_episode["outcome"] = s3_outcome
                
                # Update DB outcomes for all windows in this episode
                # Note: S3 windows have individual outcomes based on trims, but the episode fail terminates all open ones.
                # _compute_s3_window_outcomes sets 'outcome' key in window dict.
                # We should sync these to DB.
                self._sync_s3_window_outcomes_to_db(s3_episode)

                s3_episode.pop("active_window", None)
                strands.append(
                    self._build_episode_summary_strand(
                        position=position,
                        episode=s3_episode,
                        outcome=s3_outcome,
                        regime_context=regime_context,
                        token_bucket=token_bucket,
                        now=now,
                        episode_type="s3_retest",
                        levers=levers,
                    )
                )
                meta["s3_episode"] = None
                changed = True

        if state and meta.get("prev_state") != state:
            meta["prev_state"] = state
            changed = True

        # Handle S1 windows (Trigger: Entry Zone)
        diagnostics = (uptrend.get("diagnostics") or {}).get("buy_check") or {}
        entry_zone_ok = bool(diagnostics.get("entry_zone_ok"))
        
        s1_episode = meta.get("s1_episode")
        if s1_episode:
            if state == "S1":
                active_window = s1_episode.get("active_window")
                if entry_zone_ok:
                    if not active_window:
                        active_window = {
                            "window_id": self._generate_episode_id("s1win"),
                            "window_type": "s1_buy_signal",
                            "started_at": now.isoformat(),
                            "samples": [],
                            "entered": False,
                        }
                        s1_episode["active_window"] = active_window
                        changed = True
                    sample = self._capture_s1_window_sample(uptrend, now, levers)
                    if sample:
                        self._append_window_sample(active_window, sample)
                        changed = True
                elif active_window:
                    changed |= self._finalize_active_window(s1_episode, now, position, regime_context, token_bucket, uptrend, levers)
            else:
                changed |= self._finalize_active_window(s1_episode, now, position, regime_context, token_bucket, uptrend, levers)

        # Phase 7: Handle S2 windows (Trigger: buy_flag in S2 state)
        # S2 windows open when there's a buy opportunity in S2 (the "danger zone")
        buy_flag = bool(uptrend.get("buy_flag"))
        s2_episode = meta.get("s2_episode")
        if s2_episode:
            if state == "S2":
                active_window = s2_episode.get("active_window")
                # S2 window triggers on buy_flag (opportunity to add in S2)
                s2_opportunity = buy_flag and entry_zone_ok
                if s2_opportunity:
                    if not active_window:
                        active_window = {
                            "window_id": self._generate_episode_id("s2win"),
                            "window_type": "s2_buy_flag",
                            "started_at": now.isoformat(),
                            "samples": [],
                            "entered": False,
                        }
                        s2_episode["active_window"] = active_window
                        changed = True
                        logger.debug("PHASE7: Opened S2 window for position")
                    sample = self._capture_s2_window_sample(uptrend, now, levers)
                    if sample:
                        self._append_window_sample(active_window, sample)
                        changed = True
                elif active_window:
                    changed |= self._finalize_active_window(s2_episode, now, position, regime_context, token_bucket, uptrend, levers)
            else:
                # Finalize S2 window if we left S2 state
                changed |= self._finalize_active_window(s2_episode, now, position, regime_context, token_bucket, uptrend, levers)

        # Handle S3 retest windows (Trigger: Price < EMA144)
        s3_episode = meta.get("s3_episode")
        
        ema_vals = uptrend.get("ema") or {}
        price = float(uptrend.get("price", 0.0))
        ema144 = float(ema_vals.get("ema144", 0.0))
        # In S3, EMA144 > EMA333. Price < EMA144 means we are in the band or lower (dipping).
        in_band = (price > 0 and ema144 > 0 and price < ema144)
        
        if s3_episode:
            if state == "S3":
                active_window = s3_episode.get("active_window")
                if in_band:
                    if not active_window:
                        retest_index = s3_episode.get("retest_index", 0) + 1
                        s3_episode["retest_index"] = retest_index
                        active_window = {
                            "window_id": self._generate_episode_id("s3win"),
                            "retest_index": retest_index,
                            "started_at": now.isoformat(),
                            "samples": [],
                            "entered": False,
                        }
                        s3_episode["active_window"] = active_window
                        changed = True
                    sample = self._capture_s3_window_sample(uptrend, now, levers)
                    if sample:
                        self._append_window_sample(active_window, sample)
                        changed = True
                elif active_window:
                    changed |= self._finalize_active_window(s3_episode, now, position, regime_context, token_bucket, uptrend, levers)
            else:
                changed |= self._finalize_active_window(s3_episode, now, position, regime_context, token_bucket, uptrend, levers)

        features["uptrend_episode_meta"] = meta
        position["features"] = features
        return strands, changed

    def _build_episode_summary_strand(
        self,
        position: Dict[str, Any],
        episode: Dict[str, Any],
        outcome: str,
        regime_context: Dict[str, Any],
        token_bucket: Optional[str],
        now: datetime,
        episode_type: str = "s1_entry",
        levers: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        features = position.get("features") or {}
        uptrend_signals = features.get("uptrend_engine_v4") or {}
        # Phase 7: Handle S2 episode type for tuning
        if episode_type == "s1_entry":
            action_type = "entry"
            state = "S1"
        elif episode_type == "s2_entry":
            action_type = "add"  # S2 is an add, not initial entry
            state = "S2"
        else:  # s3_retest
            action_type = "add"
            state = "S3"
        pattern_key, action_category, scope = self._build_pattern_scope(
            position=position,
            uptrend_signals=uptrend_signals,
            action_type=action_type,
            regime_context=regime_context,
            token_bucket=token_bucket,
            state=state,
            levers=levers,
        )
        position_id = position.get("id")
        timeframe = position.get("timeframe", self.timeframe)
        symbol = position.get("token_ticker") or position.get("token_contract")

        levers_considered = self._compute_lever_considerations(episode, episode_type)

        content = {
            "position_id": position_id,
            "episode_id": episode.get("episode_id"),
            "episode_type": episode_type,
            "outcome": outcome,
            "entered": episode.get("entered", False),
            "started_at": episode.get("started_at"),
            "ended_at": now.isoformat(),
            "pattern_key": pattern_key,
            "action_category": action_category,
            "scope": scope,
            "episode_edge": None,
            "windows": episode.get("windows", []),
            "levers_considered": levers_considered,
        }

        strand = {
            "id": f"uptrend_episode_{position_id}_{int(now.timestamp() * 1000)}",
            "module": "pm",
            "kind": "uptrend_episode_summary",
            "symbol": symbol,
            "timeframe": timeframe,
            "position_id": position_id,
            "trade_id": position.get("current_trade_id"),
            "content": content,
            "regime_context": regime_context or {},
            "tags": ["uptrend", "episode_summary"],
            "target_agent": "learning_system",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        return strand


    def _build_action_context(
        self,
        position: Dict[str, Any],
        action: Dict[str, Any],
        a_final: float,
        e_final: float
    ) -> Dict[str, Any]:
        """
        Build action_context for braiding system.
        
        Args:
            position: Position dict with features
            action: Action dict with decision_type, size_frac, reasons
            a_final: Final aggressiveness score
            e_final: Final exit assertiveness score
        
        Returns:
            action_context dict with all dimensions needed for braiding
        """
        features = position.get("features") or {}
        uptrend = features.get("uptrend_engine_v4") or {}
        ta = features.get("ta") or {}
        geometry = features.get("geometry") or {}
        exec_history = features.get("pm_execution_history") or {}
        
        # Get engine signals and flags
        state = uptrend.get("state", "")
        buy_signal = uptrend.get("buy_signal", False)
        buy_flag = uptrend.get("buy_flag", False)
        first_dip_buy_flag = uptrend.get("first_dip_buy_flag", False)
        trim_flag = uptrend.get("trim_flag", False)
        emergency_exit = uptrend.get("emergency_exit", False)
        reclaimed_ema333 = uptrend.get("reclaimed_ema333", False)
        
        # Get engine scores
        scores = uptrend.get("scores") or {}
        ts_score = float(scores.get("ts", 0.0))
        dx_score = float(scores.get("dx", 0.0))
        ox_score = float(scores.get("ox", 0.0))
        edx_score = float(scores.get("edx", 0.0))
        
        # Get EMA slopes
        ema_slopes_raw = ta.get("ema_slopes") or {}
        timeframe = position.get("timeframe", self.timeframe)
        ta_suffix = f"_{timeframe}" if timeframe != "1h" else ""
        
        ema_slopes = {}
        for key in ["ema60_slope", "ema144_slope", "ema250_slope", "ema333_slope"]:
            ema_slopes[key] = float(ema_slopes_raw.get(f"{key}{ta_suffix}", 0.0))
        
        # Get S/R levels
        sr_levels = geometry.get("levels", {}).get("sr_levels", []) if isinstance(geometry.get("levels"), dict) else []
        current_price = float(uptrend.get("price", 0.0))
        current_sr_level = None
        if sr_levels and current_price > 0:
            try:
                closest_sr = min(sr_levels, key=lambda x: abs(float(x.get("price", 0)) - current_price))
                current_sr_level = float(closest_sr.get("price", 0))
            except Exception:
                pass
        
        # Get timing info
        first_entry_ts = position.get("first_entry_timestamp") or position.get("created_at")
        bars_since_entry = 0
        if first_entry_ts:
            try:
                token_contract = position.get("token_contract", "")
                chain = position.get("token_chain", "").lower()
                from src.intelligence.lowcap_portfolio_manager.pm.actions import _count_bars_since
                bars_since_entry = _count_bars_since(first_entry_ts, token_contract, chain, timeframe, self.sb)
            except Exception:
                pass
        
        # Get action details
        decision_type = action.get("decision_type", "").lower()
        size_frac = float(action.get("size_frac", 0.0))
        reasons = action.get("reasons", {})
        
        # Build action_context
        action_context = {
            # A/E Scores
            "a_final": a_final,
            "e_final": e_final,
            "a_bucket": bucket_a_e(a_final),
            "e_bucket": bucket_a_e(e_final),
            
            # Uptrend Engine State & Signals
            "state": state,
            "buy_signal": buy_signal,
            "buy_flag": buy_flag,
            "first_dip_buy_flag": first_dip_buy_flag,
            "trim_flag": trim_flag,
            "emergency_exit": emergency_exit,
            "reclaimed_ema333": reclaimed_ema333,
            
            # Engine Scores
            "ts_score": ts_score,
            "dx_score": dx_score,
            "ox_score": ox_score,
            "edx_score": edx_score,
            "ts_score_bucket": bucket_score(ts_score),
            "dx_score_bucket": bucket_score(dx_score),
            "ox_score_bucket": bucket_score(ox_score),
            "edx_score_bucket": bucket_score(edx_score),
            
            # EMA Slopes
            "ema_slopes": ema_slopes,
            "ema_slopes_bucket": bucket_ema_slopes(ema_slopes),
            
            # Entry Zone Conditions (from uptrend engine diagnostics)
            "entry_zone_ok": uptrend.get("entry_zone", False),
            "slope_ok": uptrend.get("slope_ok", False),
            "ts_ok": uptrend.get("ts_ok", False),
            
            # S/R Levels
            "sr_levels": [float(x.get("price", 0)) for x in sr_levels[:5]] if sr_levels else [],
            "current_sr_level": current_sr_level,
            "sr_level_changed": reasons.get("sr_level_changed", False),
            
            # Action Details
            "action_type": decision_type,  # "add", "trim", "emergency_exit"
            "size_frac": size_frac,
            "size_bucket": bucket_size(size_frac),
            "entry_multiplier": reasons.get("entry_multiplier", 1.0),
            "trim_multiplier": reasons.get("trim_multiplier", 1.0),
            
            # Timing
            "bars_since_entry": bars_since_entry,
            "bars_since_entry_bucket": bucket_bars_since_entry(bars_since_entry),
            "bars_since_last_action": 0,  # TODO: Calculate from exec_history
            "bars_until_exit": None,  # Don't know yet
        }
        
        return action_context

    def _update_position_after_execution(
        self,
        position_id: int,
        decision_type: str,
        execution_result: Dict[str, Any],
        action: Dict[str, Any],
        position: Dict[str, Any],
        a_final: float,
        e_final: float
    ) -> None:
        """
        Update position table after execution.
        
        Args:
            position_id: Position ID
            decision_type: "add", "trim", "emergency_exit"
            execution_result: Result from executor.execute()
            action: Action dict with decision_type, size_frac, reasons
            position: Position dict with features
            a_final: Final aggressiveness score
            e_final: Final exit assertiveness score
        """
        if execution_result.get("status") != "success":
            return
        
        try:
            # Get current position
            current = (
                self.sb.table("lowcap_positions")
                .select("total_quantity,total_allocation_usd,total_extracted_usd,total_tokens_bought,total_tokens_sold,status,avg_entry_price,avg_exit_price,features,current_trade_id")
                .eq("id", position_id)
                .limit(1)
                .execute()
            ).data
            
            if not current:
                return
            
            current_pos = current[0]
            updates: Dict[str, Any] = {}
            
            # Update last_activity_timestamp on every action
            now_iso = datetime.now(timezone.utc).isoformat()
            updates["last_activity_timestamp"] = now_iso
            
            token_decimals = execution_result.get("token_decimals")
            if token_decimals is not None:
                try:
                    token_decimals = int(token_decimals)
                except (TypeError, ValueError):
                    token_decimals = None
            if token_decimals is not None:
                features = current_pos.get("features") or {}
                if features.get("token_decimals") != token_decimals:
                    features["token_decimals"] = token_decimals
                    updates["features"] = features
            
            reasons = action.get("reasons") or {}
            action_flag = (reasons.get("flag") or "").lower()
            size_frac = float(action.get("size_frac", 0.0))
            
            if decision_type in ("add", "entry"):
                # Add tokens and investment (USD tracking)
                tokens_bought = float(execution_result.get("tokens_bought", 0.0))
                notional_usd = float(execution_result.get("notional_usd", 0.0))  # Exact USD from executor tx
                entry_price = float(execution_result.get("price", 0.0))
                
                current_quantity = float(current_pos.get("total_quantity", 0.0))
                current_allocation_usd = float(current_pos.get("total_allocation_usd", 0.0))
                current_tokens_bought = float(current_pos.get("total_tokens_bought", 0.0))
                
                # Update cumulative fields (exact from executor)
                updates["total_quantity"] = current_quantity + tokens_bought
                updates["total_allocation_usd"] = current_allocation_usd + notional_usd  # Cumulative USD invested
                updates["total_tokens_bought"] = current_tokens_bought + tokens_bought
                
                # Calculate weighted average entry price (total_allocation_usd / total_tokens_bought)
                if (current_tokens_bought + tokens_bought) > 0:
                    updates["avg_entry_price"] = (current_allocation_usd + notional_usd) / (current_tokens_bought + tokens_bought)
                
                # Update status and trade tracking on first buy
                if current_pos.get("status") == "watchlist":
                    updates["status"] = "active"
                if not current_pos.get("current_trade_id"):
                    now_iso = datetime.now(timezone.utc).isoformat()
                    updates["first_entry_timestamp"] = now_iso
                    new_trade_id = str(uuid.uuid4())
                    updates["current_trade_id"] = new_trade_id
                    position["current_trade_id"] = new_trade_id
            
            elif decision_type in ["trim", "emergency_exit"]:
                # Remove tokens and add to extracted (USD tracking)
                tokens_sold = float(execution_result.get("tokens_sold", 0.0))
                actual_usd = float(execution_result.get("actual_usd", 0.0))  # Exact USD from executor tx
                exit_price = float(execution_result.get("price", 0.0))
                
                current_quantity = float(current_pos.get("total_quantity", 0.0))
                current_extracted_usd = float(current_pos.get("total_extracted_usd", 0.0))
                current_tokens_sold = float(current_pos.get("total_tokens_sold", 0.0))
                
                # Update cumulative fields (exact from executor)
                updates["total_quantity"] = max(0.0, current_quantity - tokens_sold)
                updates["total_extracted_usd"] = current_extracted_usd + actual_usd  # Cumulative USD extracted
                updates["total_tokens_sold"] = current_tokens_sold + tokens_sold
                
                # Calculate weighted average exit price (total_extracted_usd / total_tokens_sold)
                if (current_tokens_sold + tokens_sold) > 0:
                    updates["avg_exit_price"] = (current_extracted_usd + actual_usd) / (current_tokens_sold + tokens_sold)
                
                remaining_quantity = updates.get("total_quantity", current_quantity - tokens_sold)
                
                # Note: Trade closure is handled separately in _check_position_closure
                # based on state == S0 AND current_trade_id exists
                # We don't close here - just update quantities
            
            if updates:
                logger.info(
                    "pm_core_tick.exec_update decision=%s status_before=%s qty_before=%s tokens_sold=%s actual_usd=%s updates=%s",
                    decision_type,
                    current_pos.get("status"),
                    current_pos.get("total_quantity"),
                    execution_result.get("tokens_sold"),
                    execution_result.get("actual_usd"),
                    {k: updates[k] for k in ("total_quantity", "status") if k in updates},
                )
                self.sb.table("lowcap_positions").update(updates).eq("id", position_id).execute()
                # Keep position dict in sync for downstream logic (_write_strands uses trade_id)
                for key, value in updates.items():
                    position[key] = value
                
                # Recalculate P&L fields after execution (hybrid approach - update when data changes)
                try:
                    # Reload position with updated values
                    updated_pos_result = (
                        self.sb.table("lowcap_positions")
                        .select("*")
                        .eq("id", position_id)
                        .limit(1)
                        .execute()
                    )
                    if updated_pos_result.data:
                        updated_pos = updated_pos_result.data[0]
                        pnl_updates = self._recalculate_pnl_fields(updated_pos)
                        if pnl_updates:
                            self.sb.table("lowcap_positions").update(pnl_updates).eq("id", position_id).execute()
                except Exception as e:
                    logger.warning(f"Error recalculating P&L fields for position {position_id}: {e}")
                
        except Exception as e:
            logger.error(f"Error updating position {position_id} after execution: {e}")
    
    def _update_execution_history(
        self,
        position_id: int,
        decision_type: str,
        execution_result: Dict[str, Any],
        action: Dict[str, Any]
    ) -> None:
        """
        Update pm_execution_history in position features.
        
        Args:
            position_id: Position ID
            decision_type: "add", "trim", "emergency_exit"
            execution_result: Result from executor.execute()
            action: Action dict from plan_actions_v4()
        """
        if execution_result.get("status") != "success":
            return
        
        try:
            # Get current features
            current = (
                self.sb.table("lowcap_positions")
                .select("features")
                .eq("id", position_id)
                .limit(1)
                .execute()
            ).data
            
            if not current:
                return
            
            features = current[0].get("features") or {}
            execution_history = features.get("pm_execution_history") or {}
            
            # Diagnostic logging: Log pool state when loading execution_history
            pool_before = execution_history.get("trim_pool")
            if pool_before:
                logger.info(
                    "POOL_DIAG: Loaded pool from DB | position=%s | pool=%s",
                    position_id, pool_before
                )
            else:
                logger.debug(
                    "POOL_DIAG: No pool in exec_history | position=%s | exec_history_keys=%s",
                    position_id, list(execution_history.keys())
                )
            
            now_iso = datetime.now(timezone.utc).isoformat()
            price = float(execution_result.get("price", 0.0))
            size_frac = float(action.get("size_frac", 0.0))
            
            # Get signal from action reasons
            reasons = action.get("reasons") or {}
            signal = reasons.get("flag") or decision_type
            
            # Update execution history based on decision type
            if decision_type in ["add", "entry"]:
                # Determine which buy signal (S1, S2, S3, reclaimed_ema333)
                # FIX: Use reasons["state"] not signal parsing - signal is "buy_flag" not "s2"/"s3"
                state = (reasons.get("state") or "").upper()
                
                # Log warning if state is missing (so we catch it early)
                if not state and "buy_signal" not in signal.lower() and "reclaimed" not in signal.lower():
                    logger.warning(
                        "BUY_HISTORY_NO_STATE: position=%s signal=%s reasons=%s (fallback to signal parsing)",
                        position_id, signal, reasons
                    )
                
                if "buy_signal" in signal.lower() or state == "S1":
                    execution_history["last_s1_buy"] = {
                        "timestamp": now_iso,
                        "price": price,
                        "size_frac": size_frac,
                        "signal": signal,
                        "state": state or "S1"
                    }
                elif state == "S2":
                    execution_history["last_s2_buy"] = {
                        "timestamp": now_iso,
                        "price": price,
                        "size_frac": size_frac,
                        "signal": signal,
                        "state": state
                    }
                elif state == "S3":
                    execution_history["last_s3_buy"] = {
                        "timestamp": now_iso,
                        "price": price,
                        "size_frac": size_frac,
                        "signal": signal,
                        "state": state
                    }
                elif "reclaimed" in signal.lower() or "ema333" in signal.lower():
                    execution_history["last_reclaim_buy"] = {
                        "timestamp": now_iso,
                        "price": price,
                        "size_frac": size_frac,
                        "signal": signal
                    }
                
                # Update trim pool for S2/DX buys (if using pool)
                pool = _get_pool(execution_history)
                pool_basis = pool.get("usd_basis", 0)
                recovery_started = pool.get("recovery_started", False)
                
                if pool_basis > 0:
                    if state == "S2" and not recovery_started:
                        # S2 dip buy from pool - clears pool
                        notional = float(action.get("notional", 0) or execution_result.get("tokens_received", 0) * price)
                        locked = _on_s2_dip_buy(execution_history, notional)
                        logger.info(
                            "TRIM_POOL: S2 dip buy $%.2f from pool, locked $%.2f profit | position=%s",
                            notional, locked, position_id
                        )
                    elif state == "S3" and "reclaimed" not in signal.lower():
                        # DX buy from pool - updates ladder
                        atr = float((action.get("reasons") or {}).get("atr", 0) or 
                                   features.get("uptrend_engine_v4", {}).get("atr", 0))
                        dx_atr_mult = float((action.get("reasons") or {}).get("dx_atr_mult", 6.0))
                        _on_dx_buy(execution_history, price, atr, dx_atr_mult)
                        
                        pool_after = _get_pool(execution_history)
                        dx_count = pool_after.get("dx_count", 0)
                        
                        logger.info(
                            "TRIM_POOL: DX buy #%d at $%.8f, next arm at $%.8f | position=%s",
                            dx_count,
                            price,
                            pool_after.get("dx_next_arm", 0),
                            position_id
                        )
                        
                        # Log DX episode event for tuning (Phase 7)
                        try:
                            # Get position for scope
                            pos_result = self.sb.table("lowcap_positions").select(
                                "token_chain, timeframe, features"
                            ).eq("id", position_id).limit(1).execute()
                            
                            if pos_result.data:
                                pos = pos_result.data[0]
                                token_chain = pos.get("token_chain", "").lower()
                                timeframe = pos.get("timeframe", "1h")
                                
                                # Get token_bucket from features or position
                                pos_features = pos.get("features", {})
                                token_bucket = pos_features.get("token_bucket") or "unknown"
                                
                                # Build tuning scope
                                scope = {
                                    "chain": token_chain,
                                    "bucket": token_bucket,
                                    "timeframe": timeframe,
                                }
                                
                                # Log DX episode event and track ID for outcome updates
                                dx_episode_db_id = self._log_episode_event(
                                    window={},  # DX is point-in-time, not window-based
                                    scope=scope,
                                    pattern_key="pm.uptrend.S3.dx",
                                    decision="acted",  # Always 'acted' for DX since we only log on execution
                                    factors={
                                        "dx_count": dx_count,
                                        "dx_atr_mult_used": dx_atr_mult,
                                        "pool_basis": pool_after.get("usd_basis", 0),
                                        "fill_price": price,
                                        "atr": atr,
                                    },
                                    episode_id=f"dx_{position_id}_{dx_count}_{int(datetime.now().timestamp())}",
                                    trade_id=pos_features.get("current_trade_id"),
                                )
                                
                                # Track DX episode ID for later outcome updates
                                if dx_episode_db_id:
                                    episode_meta = pos_features.get("uptrend_episode_meta", {})
                                    dx_episode_ids = episode_meta.get("dx_episode_ids", [])
                                    dx_episode_ids.append(dx_episode_db_id)
                                    episode_meta["dx_episode_ids"] = dx_episode_ids
                                    pos_features["uptrend_episode_meta"] = episode_meta
                                    # Note: features will be saved in the main update below
                                    
                                logger.debug(
                                    "PHASE7: Logged DX episode event (db_id=%s) | position=%s dx_count=%d dx_atr_mult=%.1f",
                                    dx_episode_db_id, position_id, dx_count, dx_atr_mult
                                )
                        except Exception as e:
                            logger.warning(f"Failed to log DX episode event for position {position_id}: {e}")
            
            elif decision_type in ["trim", "emergency_exit"]:
                execution_history["last_trim"] = {
                    "timestamp": now_iso,
                    "price": price,
                    "size_frac": size_frac,
                    "signal": signal,
                    "sr_level_price": (action.get("reasons") or {}).get("sr_level_price"),
                }
                
                # Update trim pool - use USDC received from execution
                actual_usd = float(execution_result.get("actual_usd", 0.0))
                if actual_usd > 0:
                    pool_before = _get_pool(execution_history)
                    _on_trim(execution_history, actual_usd)
                    pool_after = _get_pool(execution_history)
                    logger.info(
                        "TRIM_POOL: Updated pool with $%.2f trim | position=%s | "
                        "pool_before=%s pool_after=%s",
                        actual_usd, position_id, pool_before, pool_after
                    )
            
            # Update prev_state if we have state info
            uptrend_engine = features.get("uptrend_engine_v4") or {}
            current_state = uptrend_engine.get("state")
            if current_state:
                execution_history["prev_state"] = current_state
            
            # Save back to features
            features["pm_execution_history"] = execution_history
            
            # Diagnostic logging: Log pool state before saving
            pool_to_save = execution_history.get("trim_pool")
            if pool_to_save:
                logger.info(
                    "POOL_DIAG: Saving pool to DB | position=%s | pool=%s",
                    position_id, pool_to_save
                )
            
            # Save to database
            update_result = self.sb.table("lowcap_positions").update({"features": features}).eq("id", position_id).execute()
            
            # Diagnostic logging: Verify save succeeded
            if pool_to_save:
                logger.info(
                    "POOL_DIAG: Pool save completed | position=%s | update_success=%s",
                    position_id, len(update_result.data) > 0 if update_result.data else False
                )
            
        except Exception as e:
            logger.error(f"Error updating execution history for position {position_id}: {e}")
    
    def _recalculate_pnl_fields(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recalculate P&L fields (hybrid approach - stored but recalculated when needed).
        
        Args:
            position: Position dict with current values
        
        Returns:
            Dict with updated P&L fields
        """
        updates: Dict[str, Any] = {}
        
        total_allocation_usd = float(position.get("total_allocation_usd") or 0.0)
        total_extracted_usd = float(position.get("total_extracted_usd") or 0.0)
        total_tokens_bought = float(position.get("total_tokens_bought") or 0.0)
        total_tokens_sold = float(position.get("total_tokens_sold") or 0.0)
        total_quantity = float(position.get("total_quantity") or 0.0)
        avg_entry_price = float(position.get("avg_entry_price") or 0.0) if position.get("avg_entry_price") is not None else 0.0
        avg_exit_price = float(position.get("avg_exit_price") or 0.0) if position.get("avg_exit_price") is not None else 0.0
        
        # Get current market price from latest OHLC
        token_contract = position.get("token_contract", "")
        token_chain = position.get("token_chain", "")
        timeframe = position.get("timeframe", self.timeframe)
        
        try:
            ohlc_result = (
                self.sb.table("lowcap_price_data_ohlc")
                .select("close_usd")
                .eq("token_contract", token_contract)
                .eq("chain", token_chain)
                .eq("timeframe", timeframe)
                .order("timestamp", desc=True)
                .limit(1)
                .execute()
            )
            market_price = float(ohlc_result.data[0].get("close_usd", 0.0)) if ohlc_result.data else 0.0
        except Exception:
            market_price = 0.0
        
        # Calculate current_usd_value (total_quantity * market_price)
        current_usd_value = total_quantity * market_price if market_price > 0 else 0.0
        updates["current_usd_value"] = current_usd_value
        
        # === "God View" PnL Calculation ===
        # 1. Total PnL first (bulletproof anchor of truth)
        # Total PnL = (qty × price) + extracted - allocated
        total_pnl_usd = current_usd_value + total_extracted_usd - total_allocation_usd
        total_pnl_pct = (total_pnl_usd / total_allocation_usd * 100.0) if total_allocation_usd > 0 else 0.0
        updates["total_pnl_usd"] = total_pnl_usd
        updates["total_pnl_pct"] = total_pnl_pct
        
        # 2. Unrealized PnL (is my current bag green or red?)
        # Unrealized = (current_price - avg_entry) × quantity
        unrealized_pnl = (market_price - avg_entry_price) * total_quantity if avg_entry_price > 0 else 0.0
        
        # 3. Realized PnL (derived from total - unrealized)
        rpnl_usd = total_pnl_usd - unrealized_pnl
        rpnl_pct = (rpnl_usd / total_allocation_usd * 100.0) if total_allocation_usd > 0 else 0.0
        updates["rpnl_usd"] = rpnl_usd
        updates["rpnl_pct"] = rpnl_pct
        
        # Calculate usd_alloc_remaining
        # Formula: (total_allocation_pct * wallet_balance) - (total_allocation_usd - total_extracted_usd)
        # NOTE: Always use Solana USDC balance (home chain) - all capital is centralized there
        total_allocation_pct = float(position.get("total_allocation_pct") or 0.0)
        
        # Note: Hyperliquid positions now have allocation set at discovery time
        # (in hyperliquid_market_discovery.py), so no fallback is needed here.
        
        if total_allocation_pct > 0:
            # Get wallet balance based on position chain
            # Hyperliquid positions use Hyperliquid margin balance
            # Solana positions use Solana USDC balance
            token_chain = position.get("token_chain", "").lower()
            home_chain = os.getenv("HOME_CHAIN", "solana").lower()
            
            if token_chain == "hyperliquid":
                # Get Hyperliquid margin balance (collateral for perpetuals)
                try:
                    wallet_result = (
                        self.sb.table("wallet_balances")
                        .select("usdc_balance,balance_usd")
                        .eq("chain", "hyperliquid")
                        .limit(1)
                        .execute()
                    )
                    if wallet_result.data:
                        row = wallet_result.data[0]
                        wallet_balance = float(row.get("usdc_balance") or row.get("balance_usd") or 0.0)
                    else:
                        wallet_balance = 0.0
                        logger.warning("No wallet_balances row found for hyperliquid, using 0.0")
                except Exception as e:
                    wallet_balance = 0.0
                    logger.warning(f"Error getting Hyperliquid balance: {e}")
                balance_chain = "hyperliquid"
            else:
                # Get Solana USDC balance (home chain - all capital is here)
                try:
                    wallet_result = (
                        self.sb.table("wallet_balances")
                        .select("usdc_balance,balance_usd")
                        .eq("chain", home_chain)
                        .limit(1)
                        .execute()
                    )
                    if wallet_result.data:
                        row = wallet_result.data[0]
                        wallet_balance = float(row.get("usdc_balance") or row.get("balance_usd") or 0.0)
                    else:
                        wallet_balance = 0.0
                        logger.warning(f"No wallet_balances row found for home chain={home_chain}, using 0.0")
                except Exception as e:
                    wallet_balance = 0.0
                    logger.warning(f"Error getting wallet balance for home chain {home_chain}: {e}")
                balance_chain = home_chain
            
            # Calculate max allocation and net deployed
            max_allocation_usd = wallet_balance * (total_allocation_pct / 100.0)
            net_deployed_usd = total_allocation_usd - total_extracted_usd
            usd_alloc_remaining = max_allocation_usd - net_deployed_usd
            
            logger.debug(f"usd_alloc_remaining calc (chain={balance_chain}): wallet_balance=${wallet_balance:.2f}, total_allocation_pct={total_allocation_pct}%, max_allocation_usd=${max_allocation_usd:.2f}, net_deployed_usd=${net_deployed_usd:.2f}, usd_alloc_remaining=${usd_alloc_remaining:.2f}")
            
            updates["usd_alloc_remaining"] = max(0.0, usd_alloc_remaining)  # Can't be negative
        else:
            updates["usd_alloc_remaining"] = 0.0
        
        # Update timestamp
        updates["pnl_last_calculated_at"] = datetime.now(timezone.utc).isoformat()
        
        return updates
    
    def _send_execution_notification(
        self,
        position: Dict[str, Any],
        decision_type: str,
        exec_result: Dict[str, Any],
        action: Dict[str, Any],
        a_final: float,
        e_final: float,
        position_status_before: str = ""
    ) -> None:
        """Send Telegram notification after successful execution (non-blocking)"""
        token_ticker = position.get("token_ticker", "")
        token_contract = position.get("token_contract", "")
        chain = position.get("token_chain", "")
        timeframe = position.get("timeframe", self.timeframe)
        
        # Log notification attempt
        logger.info(
            f"NOTIFICATION ATTEMPT: {decision_type} {token_ticker}/{chain} tf={timeframe} | "
            f"exec_status={exec_result.get('status')} | "
            f"telegram_notifier={'available' if self.telegram_notifier else 'None'}"
        )
        
        if not self.telegram_notifier:
            logger.warning(f"NOTIFICATION SKIPPED: telegram_notifier is None for {decision_type} {token_ticker}/{chain}")
            return
        
        try:
            import asyncio
            
            tx_hash = exec_result.get("tx_hash", "")
            source_tweet_url = position.get("source_tweet_url")
            
            # Get uptrend engine signals
            features = position.get("features") or {}
            uptrend = features.get("uptrend_engine_v4") or {}
            state = uptrend.get("state", "")
            reasons = action.get("reasons") or {}
            signal = reasons.get("flag", "")
            size_frac = float(action.get("size_frac", 0.0))
            
            # Get position data (after update)
            total_quantity = float(position.get("total_quantity", 0.0))
            position_value_usd = float(position.get("current_usd_value", 0.0))
            avg_entry_price_usd = float(position.get("avg_entry_price", 0.0))
            total_pnl_usd = float(position.get("total_pnl_usd", 0.0))
            total_pnl_pct = float(position.get("total_pnl_pct", 0.0))
            rpnl_usd = float(position.get("rpnl_usd", 0.0))
            rpnl_pct = float(position.get("rpnl_pct", 0.0))
            
            # Determine notification type and send
            if decision_type in ("entry", "add"):
                # Check if this is entry (first buy) or add
                # Entry = decision_type is "entry" OR position status was "watchlist" before update (first buy)
                is_entry = decision_type == "entry" or position_status_before == "watchlist"
                
                amount_usd = float(exec_result.get("notional_usd", 0.0))
                entry_price_usd = float(exec_result.get("price", 0.0))
                
                # FIX: If price is 0 or missing, calculate from notional_usd / tokens_bought
                # This handles cases where Jupiter execution doesn't return price correctly
                if entry_price_usd <= 0:
                    tokens_bought = float(exec_result.get("tokens_bought", 0.0))
                    if tokens_bought > 0 and amount_usd > 0:
                        entry_price_usd = amount_usd / tokens_bought
                        logger.info(
                            f"PRICE FALLBACK: Calculated entry price from execution | "
                            f"{token_ticker}/{chain} | "
                            f"price={entry_price_usd:.8f} (from ${amount_usd:.2f} / {tokens_bought:.6f} tokens)"
                        )
                    elif avg_entry_price_usd and avg_entry_price_usd > 0:
                        # Last resort: use position's average entry price
                        entry_price_usd = avg_entry_price_usd
                        logger.warning(
                            f"PRICE FALLBACK: Using position avg_entry_price | "
                            f"{token_ticker}/{chain} | "
                            f"price={entry_price_usd:.8f}"
                        )
                
                if is_entry:
                    # Entry notification
                    self._fire_and_forget(
                        self.telegram_notifier.send_entry_notification(
                            token_ticker=token_ticker,
                            token_contract=token_contract,
                            chain=chain,
                            timeframe=timeframe,
                            amount_usd=amount_usd,
                            entry_price_usd=entry_price_usd,
                            tx_hash=tx_hash,
                            state=state,
                            signal=signal,
                            a_score=a_final,
                            e_score=e_final,
                            allocation_pct=None,
                            source_tweet_url=source_tweet_url
                        ),
                        description="telegram entry notification"
                    )
                else:
                    # Add notification
                    self._fire_and_forget(
                        self.telegram_notifier.send_add_notification(
                            token_ticker=token_ticker,
                            token_contract=token_contract,
                            chain=chain,
                            timeframe=timeframe,
                            amount_usd=amount_usd,
                            entry_price_usd=entry_price_usd,
                            tx_hash=tx_hash,
                            state=state,
                            signal=signal,
                            a_score=a_final,
                            e_score=e_final,
                            size_frac=size_frac,
                            position_size=total_quantity,
                            position_value_usd=position_value_usd,
                            avg_entry_price_usd=avg_entry_price_usd,
                            total_pnl_usd=total_pnl_usd,
                            total_pnl_pct=total_pnl_pct,
                            rpnl_usd=rpnl_usd,
                            rpnl_pct=rpnl_pct,
                            source_tweet_url=source_tweet_url
                        ),
                        description="telegram add notification"
                    )
            elif decision_type == "trim":
                # Trim notification
                tokens_sold = float(exec_result.get("tokens_sold", 0.0))
                sell_price_usd = float(exec_result.get("price", 0.0))
                value_extracted_usd = float(exec_result.get("actual_usd", 0.0))
                remaining_tokens = total_quantity
                
                logger.info(
                    f"NOTIFICATION DATA: trim {token_ticker}/{chain} | "
                    f"tokens_sold={tokens_sold:.2f} price=${sell_price_usd:.8f} value=${value_extracted_usd:.2f} | "
                    f"remaining={remaining_tokens:.2f} position_value=${position_value_usd:.2f} | "
                    f"tx_hash={tx_hash[:8] if tx_hash else 'None'} state={state} signal={signal}"
                )
                
                self._fire_and_forget(
                    self.telegram_notifier.send_trim_notification(
                        token_ticker=token_ticker,
                        token_contract=token_contract,
                        chain=chain,
                        timeframe=timeframe,
                        tokens_sold=tokens_sold,
                        sell_price_usd=sell_price_usd,
                        value_extracted_usd=value_extracted_usd,
                        size_frac=size_frac,
                        tx_hash=tx_hash,
                        state=state,
                        signal=signal,
                        e_score=e_final,
                        remaining_tokens=remaining_tokens,
                        position_value_usd=position_value_usd,
                        total_pnl_usd=total_pnl_usd,
                        total_pnl_pct=total_pnl_pct,
                        rpnl_usd=rpnl_usd,
                        rpnl_pct=rpnl_pct,
                        source_tweet_url=source_tweet_url
                    ),
                    description=f"telegram trim notification {token_ticker}/{chain}"
                )
            elif decision_type == "emergency_exit":
                # Emergency exit notification
                tokens_sold = float(exec_result.get("tokens_sold", 0.0))
                sell_price_usd = float(exec_result.get("price", 0.0))
                value_extracted_usd = float(exec_result.get("actual_usd", 0.0))
                exit_reason = reasons.get("exit_reason", "emergency_exit")
                
                logger.info(
                    f"NOTIFICATION DATA: emergency_exit {token_ticker}/{chain} | "
                    f"tokens_sold={tokens_sold:.2f} price=${sell_price_usd:.8f} value=${value_extracted_usd:.2f} | "
                    f"tx_hash={tx_hash[:8] if tx_hash else 'None'} state={state} reason={exit_reason}"
                )
                
                self._fire_and_forget(
                    self.telegram_notifier.send_emergency_exit_notification(
                        token_ticker=token_ticker,
                        token_contract=token_contract,
                        chain=chain,
                        timeframe=timeframe,
                        tokens_sold=tokens_sold,
                        sell_price_usd=sell_price_usd,
                        value_extracted_usd=value_extracted_usd,
                        tx_hash=tx_hash,
                        state=state,
                        reason=exit_reason,
                        e_score=e_final,
                        total_pnl_usd=total_pnl_usd,
                        total_pnl_pct=total_pnl_pct,
                        rpnl_usd=rpnl_usd,
                        rpnl_pct=rpnl_pct,
                        source_tweet_url=source_tweet_url
                    ),
                    description=f"telegram emergency exit notification {token_ticker}/{chain}"
                )
        except Exception as e:
            logger.error(
                f"NOTIFICATION EXCEPTION: {decision_type} {token_ticker}/{chain} tf={timeframe} - {e}",
                exc_info=True
            )
            # Don't block execution if notification fails
    
    def _send_position_summary_notification(
        self,
        position: Dict[str, Any],
        uptrend: Dict[str, Any],
        buyback_result: Optional[Dict[str, Any]]
    ) -> None:
        """Send Position Summary notification after closure (non-blocking)"""
        token_ticker = position.get("token_ticker", "")
        token_contract = position.get("token_contract", "")
        chain = position.get("token_chain", "")
        timeframe = position.get("timeframe", self.timeframe)
        
        # Log notification attempt
        logger.info(
            f"NOTIFICATION ATTEMPT: position_summary {token_ticker}/{chain} tf={timeframe} | "
            f"telegram_notifier={'available' if self.telegram_notifier else 'None'} | "
            f"token_ticker={token_ticker} token_contract={token_contract[:8] if token_contract else 'None'} chain={chain}"
        )
        
        if not self.telegram_notifier:
            logger.warning(f"NOTIFICATION SKIPPED: telegram_notifier is None for position_summary {token_ticker}/{chain}")
            return
        
        try:
            import asyncio
            
            source_tweet_url = position.get("source_tweet_url")
            
            # Get final exit info
            features = position.get("features") or {}
            exec_history = features.get("pm_execution_history") or {}
            final_exit_type = "EMERGENCY_EXIT"  # Default, could be improved
            
            # Determine exit reason from uptrend state transition
            # Check both uptrend dict and features for exit_reason (may be set in different places)
            exit_reason_raw = uptrend.get("exit_reason", "") or features.get("uptrend_engine_v4", {}).get("exit_reason", "")
            prev_state = uptrend.get("prev_state", "")
            current_state = uptrend.get("state", "S0")
            
            # Build proper exit reason message based on actual state transition
            if exit_reason_raw == "s1_to_s0_bearish_order":
                exit_reason = "S1 → S0 transition (trend ended, not fakeout)"
            elif exit_reason_raw == "all_emas_below_333":
                exit_reason = "S3 → S0 transition (trend ended, not fakeout)"
            elif prev_state and current_state == "S0":
                # Fallback: use prev_state if available (most reliable)
                exit_reason = f"{prev_state} → S0 transition (trend ended, not fakeout)"
            else:
                # Default fallback
                exit_reason = "S0 transition (trend ended, not fakeout)"
            
            # Get position metrics
            total_allocation_usd = float(position.get("total_allocation_usd", 0.0))
            total_extracted_usd = float(position.get("total_extracted_usd", 0.0))
            rpnl_usd = float(position.get("rpnl_usd", 0.0))
            rpnl_pct = float(position.get("rpnl_pct", 0.0))
            total_pnl_usd = float(position.get("total_pnl_usd", 0.0))
            total_pnl_pct = float(position.get("total_pnl_pct", 0.0))
            
            # Calculate hold time
            first_entry = position.get("first_entry_timestamp")
            closed_at = position.get("closed_at")
            hold_time_days = None
            if first_entry and closed_at:
                try:
                    from datetime import datetime
                    entry_dt = datetime.fromisoformat(first_entry.replace('Z', '+00:00'))
                    closed_dt = datetime.fromisoformat(closed_at.replace('Z', '+00:00'))
                    hold_time_days = (closed_dt - entry_dt).total_seconds() / 86400.0
                except Exception:
                    pass
            
            # Get completed trades count
            completed_trades = position.get("completed_trades", [])
            completed_trades_count = len(completed_trades) if isinstance(completed_trades, list) else None
            
            # Get entry context
            entry_context = None
            curator = position.get("curator")
            mcap_bucket = position.get("mcap_bucket")
            if curator or mcap_bucket:
                parts = []
                if curator:
                    parts.append(f"@{curator}")
                if chain:
                    parts.append(chain)
                if mcap_bucket:
                    parts.append(mcap_bucket)
                entry_context = " / ".join(parts)
            
            # Format buyback result
            lotus_buyback = None
            if buyback_result and buyback_result.get("success"):
                lotus_buyback = {
                    "success": True,
                    "profit_usd": rpnl_usd,
                    "swap_amount_usd": buyback_result.get("swap_amount_usd", 0.0),
                    "lotus_tokens": buyback_result.get("lotus_tokens", 0.0),
                    "lotus_tokens_transferred": buyback_result.get("lotus_tokens_transferred", 0.0),
                    "swap_tx_hash": buyback_result.get("swap_tx_hash"),
                    "transfer_tx_hash": buyback_result.get("transfer_tx_hash")
                }
            elif buyback_result:
                lotus_buyback = {
                    "success": False,
                    "error": buyback_result.get("error", "Unknown error")
                }
            
            self._fire_and_forget(
                self.telegram_notifier.send_position_summary_notification(
                    token_ticker=token_ticker,
                    token_contract=token_contract,
                    chain=chain,
                    timeframe=timeframe,
                    final_exit_type=final_exit_type,
                    exit_reason=exit_reason,
                    total_allocation_usd=total_allocation_usd,
                    total_extracted_usd=total_extracted_usd,
                    rpnl_usd=rpnl_usd,
                    rpnl_pct=rpnl_pct,
                    total_pnl_usd=total_pnl_usd,
                    total_pnl_pct=total_pnl_pct,
                    hold_time_days=hold_time_days,
                    rr=None,
                    return_mult=None,
                    max_drawdown_pct=None,
                    max_gain_mult=None,
                    completed_trades=completed_trades_count,
                    entry_context=entry_context,
                    lotus_buyback=lotus_buyback,
                    source_tweet_url=source_tweet_url
                ),
                description="telegram position summary notification"
            )
        except Exception as e:
            logger.error(
                f"NOTIFICATION EXCEPTION: position_summary {token_ticker}/{chain} tf={timeframe} - {e}",
                exc_info=True
            )
            # Don't block closure if notification fails
    
    def _calculate_rr_metrics(
        self,
        token_contract: str,
        chain: str,
        timeframe: str,
        entry_timestamp: datetime,
        exit_timestamp: datetime,
        entry_price: float,
        exit_price: float
    ) -> Dict[str, Any]:
        """
        Calculate R/R metrics from OHLCV data.
        
        Args:
            token_contract: Token contract address
            chain: Chain name
            timeframe: Timeframe (1m, 15m, 1h, 4h)
            entry_timestamp: Entry timestamp
            exit_timestamp: Exit timestamp
            entry_price: Entry price
            exit_price: Exit price
        
        Returns:
            Dict with rr, return, max_drawdown, max_gain
        """
        try:
            if entry_price <= 0 or exit_price <= 0:
                return {
                    "rr": None,
                    "return": None,
                    "max_drawdown": None,
                    "max_gain": None
                }
            
            # Query OHLCV data that overlaps with entry/exit time range
            # OHLC bars represent time periods, not exact timestamps
            # For a bar with timestamp T and duration D, it covers [T, T+D)
            # We need bars where: T <= exit_timestamp AND (T + D) >= entry_timestamp
            
            # Calculate timeframe duration in hours
            timeframe_hours = {
                "1m": 1/60,
                "15m": 15/60,
                "1h": 1,
                "4h": 4,
                "1d": 24
            }.get(timeframe, 1)
            
            # Find bars that start before or at exit, and end after or at entry
            # Bar starts at timestamp, ends at timestamp + timeframe_duration
            # We want: timestamp <= exit_timestamp AND (timestamp + duration) >= entry_timestamp
            # Which simplifies to: timestamp <= exit_timestamp AND timestamp >= (entry_timestamp - duration)
            
            from datetime import timedelta
            earliest_bar_start = entry_timestamp - timedelta(hours=timeframe_hours)
            
            # Query bars that could overlap: start <= exit AND start >= (entry - duration)
            ohlc_data = (
                self.sb.table("lowcap_price_data_ohlc")
                .select("timestamp,low_usd,high_usd")
                .eq("token_contract", token_contract)
                .eq("chain", chain)
                .eq("timeframe", timeframe)
                .gte("timestamp", earliest_bar_start.isoformat())  # Bar starts at or after (entry - duration)
                .lte("timestamp", exit_timestamp.isoformat())  # Bar starts at or before exit
                .order("timestamp", desc=False)  # Order by timestamp ascending
                .execute()
            ).data
            
            # Filter to only bars that actually overlap with [entry_timestamp, exit_timestamp]
            overlapping_bars = []
            for bar in ohlc_data:
                bar_timestamp = datetime.fromisoformat(bar["timestamp"].replace('Z', '+00:00'))
                bar_end = bar_timestamp + timedelta(hours=timeframe_hours)
                # Bar overlaps if: bar_start <= exit AND bar_end >= entry
                if bar_timestamp <= exit_timestamp and bar_end >= entry_timestamp:
                    overlapping_bars.append(bar)
            
            ohlc_data = overlapping_bars
            
            if not ohlc_data:
                logger.error(
                    f"CRITICAL DATA ISSUE: No OHLCV data found for R/R calculation - "
                    f"this indicates a serious data fetching problem. "
                    f"Token: {token_contract} on {chain}, Timeframe: {timeframe} ({timeframe_hours}h duration). "
                    f"Entry: {entry_timestamp.isoformat()}, Exit: {exit_timestamp.isoformat()}. "
                    f"Query range: {earliest_bar_start.isoformat()} to {exit_timestamp.isoformat()}. "
                    f"Expected at least 1 overlapping bar but found 0. "
                    f"This trade cannot be closed until OHLC data is available."
                )
                return {
                    "rr": None,
                    "return": None,
                    "max_drawdown": None,
                    "max_gain": None
                }
            
            min_price = entry_price
            max_price = entry_price
            min_price_ts = entry_timestamp
            max_price_ts = entry_timestamp
            for bar in ohlc_data:
                bar_timestamp = datetime.fromisoformat(bar["timestamp"].replace('Z', '+00:00'))
                low_val = float(bar.get("low_usd") or entry_price)
                high_val = float(bar.get("high_usd") or entry_price)
                if low_val > 0 and low_val < min_price:
                    min_price = low_val
                    min_price_ts = bar_timestamp
                if high_val > 0 and high_val > max_price:
                    max_price = high_val
                    max_price_ts = bar_timestamp
            
            min_price = min(min_price, entry_price)
            max_price = max(max_price, entry_price)
            
            # Calculate metrics
            return_pct = (exit_price - entry_price) / entry_price if entry_price > 0 else 0.0
            max_drawdown = (entry_price - min_price) / entry_price if entry_price > 0 else 0.0
            max_gain = (max_price - entry_price) / entry_price if entry_price > 0 else 0.0
            
            # Calculate R/R ratio (return / max_drawdown)
            # Handle division by zero: if no drawdown, R/R is infinite (perfect trade)
            if max_drawdown > 0:
                rr = return_pct / max_drawdown
            else:
                # No drawdown - perfect trade (or entry was at absolute bottom)
                rr = float('inf') if return_pct > 0 else 0.0
            
            # Bound R/R to reasonable range (-33 to 33)
            # Captures extreme but realistic trades while preventing infinite values
            if rr != float('inf') and rr != float('-inf'):
                rr = max(-33.0, min(33.0, rr))
            
            return {
                "rr": rr if rr != float('inf') and rr != float('-inf') else None,
                "return": return_pct,
                "max_drawdown": max_drawdown,
                "max_gain": max_gain,
                "min_price": min_price,
                "max_price": max_price,
                "best_entry_price": min_price,
                "best_entry_timestamp": min_price_ts.isoformat() if min_price_ts else None,
                "best_exit_price": max_price,
                "best_exit_timestamp": max_price_ts.isoformat() if max_price_ts else None
            }
            
        except Exception as e:
            logger.error(f"Error calculating R/R metrics: {e}")
            return {
                "rr": None,
                "return": None,
                "max_drawdown": None,
                "max_gain": None
            }
    
    def _check_position_closure(
        self,
        position: Dict[str, Any],
        decision_type: str,
        execution_result: Dict[str, Any],
        action: Dict[str, Any]
    ) -> bool:
        """
        Check if position should be closed and handle closure.
        
        Simple rule: If state is S0 AND current_trade_id exists → close the trade.
        
        This handles:
        - S1 → S0 (full bearish EMA order)
        - S3 → S0 (all EMAs below EMA333)
        
        Args:
            position: Position dict
            decision_type: Unused (kept for compatibility)
            execution_result: Unused (kept for compatibility)
            action: Unused (kept for compatibility)
        
        Returns:
            True if position was closed, False otherwise
        """
        position_id = position.get("id")
        features = position.get("features") or {}
        uptrend = features.get("uptrend_engine_v4") or {}
        state = uptrend.get("state", "")
        
        # Simple rule: state == S0 AND current_trade_id exists → close
        if state != "S0":
            return False
        
        # Check current position state
        current = (
            self.sb.table("lowcap_positions")
            .select("status,current_trade_id")
            .eq("id", position_id)
            .limit(1)
            .execute()
        ).data
        
        if not current:
            return False
        
        current_pos = current[0]
        
        # If already closed, skip
        if current_pos.get("status") == "watchlist":
            return False
        
        # Learning System v2: Handle shadow position closure
        if current_pos.get("status") == "shadow":
            # Shadow position reached S0 - record trajectory and reset to watchlist
            try:
                # Record trajectory for learning (Phase 2)
                record_position_trajectory(
                    sb_client=self.sb,
                    position=position,
                    is_shadow=True,
                )
                
                # Reset to watchlist
                self.sb.table("lowcap_positions").update({
                    "status": "watchlist",
                }).eq("id", position_id).execute()
                logger.info(
                    "SHADOW CLOSURE: Trajectory recorded and reset to watchlist | position_id=%s",
                    position_id
                )
            except Exception as e:
                logger.warning(f"Failed to close shadow position: {e}")
            return True  # Considered "closed" for lifecycle purposes
        
        # If no trade_id, nothing to close (active positions have trade_id)
        if not current_pos.get("current_trade_id"):
            return False
        
        # State is S0 and we have an open trade → close it
        return self._close_trade_on_s0_transition(position_id, current_pos, uptrend)
    
    def _close_trade_on_s0_transition(
        self,
        position_id: int,
        current_pos: Dict[str, Any],
        uptrend: Dict[str, Any]
    ) -> bool:
        """
        Close trade when state transitions to S0 (after emergency_exit or structural exit).
        
        Args:
            position_id: Position ID
            current_pos: Current position row from DB
            uptrend: Uptrend engine state dict
        
        Returns:
            True if trade was closed, False otherwise
        """
        try:
            # Get position details for R/R calculation (including features for S3 timestamp and PnL data)
            position_details = (
                self.sb.table("lowcap_positions")
                .select("first_entry_timestamp,avg_entry_price,avg_exit_price,created_at,token_ticker,token_contract,token_chain,timeframe,current_trade_id,completed_trades,entry_context,total_quantity,features,rpnl_usd,rpnl_pct,total_extracted_usd,total_allocation_usd,total_pnl_usd,total_pnl_pct,total_tokens_bought,total_tokens_sold,current_usd_value,source_tweet_url,closed_at")
                .eq("id", position_id)
                .limit(1)
                .execute()
            ).data
            
            if not position_details:
                return False
            
            pos_details = position_details[0]
            features = pos_details.get("features") or {}
            total_quantity = float(pos_details.get("total_quantity", 0.0))
            
            # S0 means trade ended - close it regardless of tiny amounts left
            # Log warning if we have tokens left (rounding error or emergency exit issue)
            if total_quantity > 0.01:
                logger.warning(
                    f"Position {position_id} closing in S0 but has {total_quantity} tokens left. "
                    f"S0 means trade ended - closing anyway. "
                    f"TODO: Check emergency_exit execution status if needed."
                )
            # Continue with closure - S0 is the signal that trade ended
            
            # Get latest price for exit
            token_contract = pos_details.get("token_contract")
            chain = pos_details.get("token_chain")
            timeframe = pos_details.get("timeframe", self.timeframe)
            
            try:
                ohlc_result = (
                    self.sb.table("lowcap_price_data_ohlc")
                    .select("close_usd")
                    .eq("token_contract", token_contract)
                    .eq("chain", chain)
                    .eq("timeframe", timeframe)
                    .order("timestamp", desc=True)
                    .limit(1)
                    .execute()
                )
                exit_price = float(ohlc_result.data[0].get("close_usd", 0.0)) if ohlc_result.data else 0.0
            except Exception:
                exit_price = 0.0
            
            exit_timestamp = datetime.now(timezone.utc)
            entry_price = float(pos_details.get("avg_entry_price", 0.0))
            entry_context = pos_details.get("entry_context") or {}
            
            # Use first_entry_timestamp if available, otherwise created_at
            entry_timestamp_str = pos_details.get("first_entry_timestamp") or pos_details.get("created_at")
            if isinstance(entry_timestamp_str, str):
                entry_timestamp = datetime.fromisoformat(entry_timestamp_str.replace('Z', '+00:00'))
            else:
                entry_timestamp = exit_timestamp
            
            # Get decision_type from exit_reason (if available) or default to "emergency_exit"
            decision_type = uptrend.get("exit_reason", "emergency_exit")
            # Normalize exit_reason to decision_type format
            # All emergency exits should be normalized to "emergency_exit" for learning system
            if decision_type in ["all_emas_below_333", "s1_to_s0_bearish_order"]:
                decision_type = "emergency_exit"
            
            # Calculate time_to_s3: time from entry to S3 state transition
            time_to_s3 = None
            uptrend_meta = features.get("uptrend_engine_v4_meta") or {}
            s3_start_ts_str = uptrend_meta.get("s3_start_ts")
            
            if s3_start_ts_str:
                try:
                    s3_start_ts = datetime.fromisoformat(s3_start_ts_str.replace('Z', '+00:00'))
                    if s3_start_ts >= entry_timestamp:
                        time_to_s3 = (s3_start_ts - entry_timestamp).total_seconds() / (24 * 3600)
                except Exception:
                    pass
            
            # Calculate R/R from OHLCV data
            rr_metrics = self._calculate_rr_metrics(
                token_contract=token_contract,
                chain=chain,
                timeframe=timeframe,
                entry_timestamp=entry_timestamp,
                exit_timestamp=exit_timestamp,
                entry_price=entry_price,
                exit_price=exit_price
            )
            
            completed_trades = pos_details.get("completed_trades") or []
            if not isinstance(completed_trades, list):
                completed_trades = []
            
            # Calculate hold time
            hold_time_days = (exit_timestamp - entry_timestamp).total_seconds() / (24 * 3600)
            
            # Classify outcome
            rr_value = rr_metrics.get("rr")
            if rr_value is None:
                logger.error(
                    f"CRITICAL: Cannot close position {position_id} - R/R calculation failed. "
                    f"This indicates a serious data fetching issue (no OHLC data available). "
                    f"Position will remain open until OHLC data is available. "
                    f"Token: {token_contract} on {chain}, Timeframe: {timeframe}, "
                    f"Entry: {entry_timestamp.isoformat()}, Exit: {exit_timestamp.isoformat()}"
                )
                # Skip trade closure - cannot proceed without R/R data
                return False
            else:
                rr = float(rr_value)
            
            outcome_class = classify_outcome(rr)
            hold_time_class = classify_hold_time(hold_time_days)
            
            # Calculate counterfactuals (could_enter_better, could_exit_better)
            min_price = float(rr_metrics.get("min_price", entry_price))
            max_price = float(rr_metrics.get("max_price", exit_price))
            best_entry_price = float(rr_metrics.get("best_entry_price", min_price)) if rr_metrics.get("best_entry_price") is not None else min_price
            best_exit_price = float(rr_metrics.get("best_exit_price", max_price)) if rr_metrics.get("best_exit_price") is not None else max_price
            best_entry_ts = rr_metrics.get("best_entry_timestamp") or entry_timestamp.isoformat()
            best_exit_ts = rr_metrics.get("best_exit_timestamp") or exit_timestamp.isoformat()
            
            risk = entry_price - min_price
            if risk <= 0:
                risk = None
            missed_entry_rr = None
            missed_exit_rr = None
            if risk:
                missed_entry_rr = max(0.0, (entry_price - best_entry_price) / risk) if best_entry_price is not None else 0.0
                missed_exit_rr = max(0.0, (best_exit_price - exit_price) / risk) if best_exit_price is not None else 0.0
            else:
                missed_entry_rr = 0.0
                missed_exit_rr = 0.0
            
            cf_entry_bucket = bucket_cf_improvement(missed_entry_rr)
            cf_exit_bucket = bucket_cf_improvement(missed_exit_rr)
            
            could_enter_better = {
                "best_entry_price": best_entry_price,
                "best_entry_timestamp": best_entry_ts,
                "missed_rr": missed_entry_rr
            }
            could_exit_better = {
                "best_exit_price": best_exit_price,
                "best_exit_timestamp": best_exit_ts,
                "missed_rr": missed_exit_rr
            }
            
            # Get v5 fields from pm_action strands for this position
            v5_fields = {}
            try:
                action_strands = (
                    self.sb.table("ad_strands")
                    .select("content,created_at")
                    .eq("module", "pm")
                    .eq("kind", "pm_action")
                    .eq("position_id", position_id)
                    .order("created_at", desc=True)
                    .execute()
                )
                if action_strands.data and len(action_strands.data) > 0:
                    action_content = action_strands.data[0].get("content", {})
                    if action_content.get("pattern_key"):
                        v5_fields["pattern_key"] = action_content["pattern_key"]
                    if action_content.get("action_category"):
                        v5_fields["action_category"] = action_content["action_category"]
                    if action_content.get("scope"):
                        v5_fields["scope"] = action_content["scope"]
                    if action_content.get("controls"):
                        v5_fields["controls"] = action_content["controls"]
            except Exception as e:
                logger.warning(f"Error fetching v5 fields from pm_action strands: {e}")
            
            # Get PnL data before wiping (save to completed_trades, then wipe for next trade)
            rpnl_usd = float(pos_details.get("rpnl_usd", 0.0))
            rpnl_pct = float(pos_details.get("rpnl_pct", 0.0))
            total_pnl_usd = float(pos_details.get("total_pnl_usd", 0.0))
            total_pnl_pct = float(pos_details.get("total_pnl_pct", 0.0))
            total_allocation_usd = float(pos_details.get("total_allocation_usd", 0.0))
            total_extracted_usd = float(pos_details.get("total_extracted_usd", 0.0))
            total_tokens_bought = float(pos_details.get("total_tokens_bought", 0.0))
            total_tokens_sold = float(pos_details.get("total_tokens_sold", 0.0))
            avg_entry_price_final = float(pos_details.get("avg_entry_price", 0.0)) if pos_details.get("avg_entry_price") is not None else None
            avg_exit_price_final = float(pos_details.get("avg_exit_price", 0.0)) if pos_details.get("avg_exit_price") is not None else None
            current_usd_value = float(pos_details.get("current_usd_value", 0.0))
            
            # Build trade summary (same structure as original _check_position_closure)
            trade_summary = {
                "entry_context": entry_context,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "entry_timestamp": entry_timestamp.isoformat(),
                "exit_timestamp": exit_timestamp.isoformat(),
                "decision_type": decision_type,
                "rr": rr,
                "return": rr_metrics.get("return"),
                "max_drawdown": rr_metrics.get("max_drawdown"),
                "max_gain": rr_metrics.get("max_gain"),
                "could_enter_better": could_enter_better,
                "could_exit_better": could_exit_better,
                "cf_entry_improvement_bucket": cf_entry_bucket,
                "cf_exit_improvement_bucket": cf_exit_bucket,
                "outcome_class": outcome_class,
                "hold_time_bars": None,  # TODO: Calculate from OHLCV if needed
                "hold_time_days": hold_time_days,
                "hold_time_class": hold_time_class,
                "time_to_s3": time_to_s3,  # Time from entry to S3 state transition (None if never reached S3)
                # PnL data (saved to completed_trades before wiping)
                "rpnl_usd": rpnl_usd,
                "rpnl_pct": rpnl_pct,
                "total_pnl_usd": total_pnl_usd,
                "total_pnl_pct": total_pnl_pct,
                "total_allocation_usd": total_allocation_usd,
                "total_extracted_usd": total_extracted_usd,
                "total_tokens_bought": total_tokens_bought,
                "total_tokens_sold": total_tokens_sold,
                "avg_entry_price": avg_entry_price_final,
                "avg_exit_price": avg_exit_price_final,
                "current_usd_value": current_usd_value,
                # Include v5 fields for aggregation
                **v5_fields
            }
            
            trade_id = pos_details.get("current_trade_id")
            if not trade_id:
                trade_id = str(uuid.uuid4())
            trade_summary["trade_id"] = trade_id
            
            # Build actions summary
            actions_summary: List[Dict[str, Any]] = []
            try:
                action_rows = (
                    self.sb.table("ad_strands")
                    .select("id,content,created_at")
                    .eq("kind", "pm_action")
                    .eq("position_id", position_id)
                    .eq("trade_id", trade_id)
                    .order("created_at")
                    .execute()
                ).data or []
                for row in action_rows:
                    content = row.get("content") or {}
                    actions_summary.append({
                        "strand_id": row.get("id"),
                        "ts": row.get("created_at"),
                        "decision_type": content.get("decision_type"),
                        "pattern_key": content.get("pattern_key"),
                        "action_category": content.get("action_category"),
                        "scope": content.get("scope"),
                        "controls": content.get("controls")
                    })
            except Exception as e:
                logger.warning(f"Error loading pm_action strands for trade {trade_id}: {e}")
            
            trade_cycle_entry = {
                "trade_id": trade_id,
                "actions": actions_summary,
                "summary": trade_summary
            }
            completed_trades.append(trade_cycle_entry)
            
            # Calculate buyback BEFORE wiping PnL data (need PnL for profit calculation)
            # Build position dict with PnL data for buyback calculation
            # Include all fields needed for notification
            position_for_buyback = {
                "token_ticker": pos_details.get("token_ticker", ""),
                "token_contract": token_contract,
                "token_chain": chain,
                "timeframe": timeframe,
                "rpnl_usd": rpnl_usd,
                "total_extracted_usd": total_extracted_usd,
                "total_allocation_usd": total_allocation_usd,
                "total_pnl_usd": total_pnl_usd,
                "features": features,
                "source_tweet_url": pos_details.get("source_tweet_url"),
                "closed_at": exit_timestamp.isoformat(),
                "first_entry_timestamp": entry_timestamp.isoformat(),
                "completed_trades": completed_trades,
                "curator": pos_details.get("entry_context", {}).get("curator") if isinstance(pos_details.get("entry_context"), dict) else None,
                "mcap_bucket": pos_details.get("entry_context", {}).get("mcap_bucket") if isinstance(pos_details.get("entry_context"), dict) else None,
            }
            
            # Execute Lotus buyback (10% of profit → Lotus Coin, then transfer 69% to holding wallet)
            try:
                buyback_result = self._swap_profit_to_lotus(position_for_buyback)
                if buyback_result and buyback_result.get("success"):
                    logger.info(
                        f"Lotus buyback successful for position {position_id}: "
                        f"{buyback_result.get('lotus_tokens', 0):.6f} tokens, "
                        f"{buyback_result.get('lotus_tokens_transferred', 0):.6f} transferred to holding wallet"
                    )
                    # Store buyback info in position features (will be saved in main update below)
                    if not isinstance(features, dict):
                        features = {}
                    if "pm_execution_history" not in features:
                        features["pm_execution_history"] = {}
                    features["pm_execution_history"]["lotus_buyback"] = buyback_result
                    
                    # Update cumulative buyback totals in wallet_balances
                    lotus_tokens = buyback_result.get("lotus_tokens", 0.0)
                    lotus_tokens_transferred = buyback_result.get("lotus_tokens_transferred", 0.0)
                    if lotus_tokens > 0:
                        self._update_buyback_totals(lotus_tokens, lotus_tokens_transferred)
                elif buyback_result and not buyback_result.get("success"):
                    logger.warning(f"Lotus buyback failed for position {position_id}: {buyback_result.get('error')}")
            except Exception as e:
                logger.error(f"Error executing Lotus buyback for position {position_id}: {e}", exc_info=True)
                # Don't block position closure if buyback fails
                buyback_result = None
            
            # Update position: save completed_trades, wipe trade data and PnL fields (ready for next trade)
            # This happens AFTER buyback (buyback needs PnL data)
            
            # Learning System v2: Record trajectory before wiping PnL data
            try:
                record_position_trajectory(
                    sb_client=self.sb,
                    position=pos_details,  # Use pos_details which has full position data
                    is_shadow=False,
                )
            except Exception as e:
                logger.warning(f"Failed to record active position trajectory: {e}")
            
            self.sb.table("lowcap_positions").update({
                "completed_trades": completed_trades,
                "status": "watchlist",
                "closed_at": exit_timestamp.isoformat(),
                "current_trade_id": None,
                "last_activity_timestamp": exit_timestamp.isoformat(),
                "features": features,  # Includes buyback result if successful
                # Wipe PnL data (all info saved in completed_trades above, ready for next trade)
                "rpnl_usd": 0.0,
                "rpnl_pct": 0.0,
                "total_pnl_usd": 0.0,
                "total_pnl_pct": 0.0,
                "total_allocation_usd": 0.0,
                "total_extracted_usd": 0.0,
                "total_tokens_bought": 0.0,
                "total_tokens_sold": 0.0,
                "avg_entry_price": None,
                "avg_exit_price": None,
                "current_usd_value": 0.0,
                "total_quantity": 0.0,  # Also wipe quantity (should be 0 anyway, but ensure clean state)
            }).eq("id", position_id).execute()
            
            # Send Position Summary notification (non-blocking)
            # Use position_for_buyback which has PnL data (before wipe)
            # Pass uptrend to get exit_reason for proper state transition message
            self._send_position_summary_notification(position_for_buyback, uptrend, buyback_result)
            
            # Emit position_closed strand
            regime_context = self._get_regime_context()
            position_closed_strand = {
                "id": f"position_closed_{position_id}_{int(exit_timestamp.timestamp() * 1000)}",
                "module": "pm",
                "kind": "position_closed",
                "symbol": current_pos.get("token_ticker") or token_contract,
                "timeframe": timeframe,
                "position_id": position_id,
                "trade_id": trade_id,
                "content": {
                    "position_id": position_id,
                    "token_contract": token_contract,
                    "chain": chain,
                    "ts": exit_timestamp.isoformat(),
                    "entry_context": entry_context,
                    "trade_id": trade_id,
                    "trade_summary": trade_summary,
                    "completed_trades": completed_trades,  # Required by learning system
                    "decision_type": decision_type,
                    "exit_reason": uptrend.get("exit_reason", "state_transition_to_s0"),
                },
                "regime_context": regime_context,
                "tags": ["position_closed", "pm", "learning"],
                "target_agent": "learning_system",
                "created_at": exit_timestamp.isoformat(),
                "updated_at": exit_timestamp.isoformat(),
            }
            
            self.sb.table("ad_strands").insert(position_closed_strand).execute()
            logger.info(f"Position {position_id} closed on S0 transition - emitted position_closed strand")
            
            # Process strand in learning system (async call from sync context)
            # Since run() is synchronous and called from thread pool, we create a new event loop
            # Position closures are rare (1-2 per day), so blocking is acceptable
            if self.learning_system:
                try:
                    import asyncio
                    asyncio.run(self.learning_system.process_strand_event(position_closed_strand))
                    logger.info(f"Learning system processed position_closed strand: {position_id}")
                except Exception as e:
                    logger.error(f"Error processing position_closed strand in learning system: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            else:
                logger.warning(f"Learning system not available - position_closed strand not processed: {position_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error closing trade on S0 transition for position {position_id}: {e}")
            return False
    
    def _write_strands(self, position: Dict[str, Any], token: str, now: datetime, a_val: float, e_val: float, phase: str, actions: list[dict], execution_results: Dict[str, Dict[str, Any]] = None, regime_context: Dict[str, Dict[str, Any]] = None, token_bucket: Optional[str] = None) -> None:
        """
        Write strands for PM actions.
        
        Args:
            position: Position dict (for position_id, timeframe, chain)
            token: Token contract address or ticker
            now: Current timestamp
            a_val: Aggressiveness score
            e_val: Exit assertiveness score
            phase: Regime state string (e.g., "Macro S0, Meso S1, Micro S3") from bucket driver
            actions: List of action dicts
            execution_results: Execution results dict
            regime_context: Regime context with macro/meso/micro phases
            token_bucket: Token's cap bucket (e.g., "micro")
        """
        rows = []
        position_id = position.get("id")
        timeframe = position.get("timeframe", self.timeframe)
        chain = position.get("token_chain", "").lower()
        token_ticker = position.get("token_ticker") or token
        total_quantity = float(position.get("total_quantity") or 0.0)
        features = position.get("features") or {}
        logging_meta = features.get("pm_logging_meta") or {}
        logging_meta_updated = False
        exec_history = features.get("pm_execution_history") or {}
        exec_history_updated = False
        
        trade_id = position.get("current_trade_id")
        
        for act in actions:
            # Skip hold actions (only actions emit strands)
            decision_type = act.get("decision_type", "").lower()
            if decision_type == "hold" or not decision_type:
                continue
            
            # Throttle noisy trim strands when we have no position
            if decision_type == "trim" and total_quantity <= 0:
                last_no_pos_trim_ts = logging_meta.get("last_no_position_trim_ts")
                if last_no_pos_trim_ts:
                    try:
                        last_dt = datetime.fromisoformat(last_no_pos_trim_ts)
                        if now - last_dt < timedelta(minutes=9):
                            continue
                    except Exception:
                        pass
                logging_meta["last_no_position_trim_ts"] = now.isoformat()
                logging_meta_updated = True
            
            # Learning System v2: Handle shadow_entry action
            if decision_type == "shadow_entry":
                reasons = act.get("reasons") or {}
                entry_event = reasons.get("entry_event", "S2.entry")
                blocked_by = reasons.get("blocked_by", [])
                gate_margins = reasons.get("gate_margins", {})
                
                # Update position to shadow status
                shadow_updates = {
                    "status": "shadow",
                    "entry_event": entry_event,
                }
                # Store gate margins and blocked_by in features for learning (backup)
                features = position.get("features") or {}
                features["shadow_entry_data"] = {
                    "blocked_by": blocked_by,
                    "gate_margins": gate_margins,
                    "entry_event": entry_event,
                    "decision_time": now.isoformat(),
                }
                shadow_updates["features"] = features
                
                try:
                    self.sb.table("lowcap_positions").update(shadow_updates).eq("id", position_id).execute()
                    logger.info(
                        "SHADOW POSITION: Set status='shadow' | %s/%s tf=%s | entry_event=%s blocked_by=%s",
                        position.get("token_ticker"), position.get("token_chain"), 
                        position.get("timeframe"), entry_event, blocked_by
                    )
                except Exception as e:
                    logger.warning(f"Failed to update shadow position: {e}")
                
                # Build unified scope for shadow position
                pos_entry_ctx = position.get("entry_context") or {}
                shadow_entry_context = {
                    "mcap_bucket": pos_entry_ctx.get("mcap_bucket"),
                    "vol_bucket": pos_entry_ctx.get("vol_bucket"),
                    "age_bucket": pos_entry_ctx.get("age_bucket"),
                    "curator": pos_entry_ctx.get("curator"),
                    "intent": pos_entry_ctx.get("intent"),
                    "book_id": position.get("book_id") or pos_entry_ctx.get("book_id"),
                    "opp_meso_bin": pos_entry_ctx.get("opp_meso_bin"),
                    "conf_meso_bin": pos_entry_ctx.get("conf_meso_bin"),
                    "riskoff_meso_bin": pos_entry_ctx.get("riskoff_meso_bin"),
                    "bucket_rank_meso_bin": pos_entry_ctx.get("bucket_rank_meso_bin"),
                }
                try:
                    shadow_scope = build_unified_scope(
                        position=position,
                        entry_context=shadow_entry_context,
                        regime_context=regime_context or {}
                    )
                except Exception:
                    shadow_scope = {}

                # Build shadow entry strand (same structure as active entries for symmetry)
                shadow_content = {
                    "decision_type": "shadow_entry",
                    "entry_event": entry_event,
                    "blocked_by": blocked_by,
                    "gate_margins": gate_margins,
                    "token_contract": position.get("token_contract"),
                    "token_chain": position.get("token_chain"),
                    "token_ticker": position.get("token_ticker"),
                    "scope": shadow_scope,
                    "a_value": act.get("a_value", 0.5),
                    "e_value": act.get("e_value", 0.5),
                }
                
                shadow_strand = {
                    "id": f"pm_action_{position_id}_shadow_entry_{int(now.timestamp() * 1000)}",
                    "module": "pm",
                    "kind": "pm_action",
                    "symbol": position.get("token_ticker"),
                    "timeframe": position.get("timeframe"),
                    "position_id": position_id,
                    "trade_id": None,  # No trade for shadow
                    "content": shadow_content,
                    "regime_context": regime_context or {},
                    "tags": ["pm_action", "shadow_entry", "learning"],
                    "target_agent": "learning_system",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
                rows.append(shadow_strand)
                
                # Continue to next action (no execution needed for shadow)
                continue
            
            # Learning System v2: Shadow→Active conversion
            # If executing an entry action and a shadow exists for this token/tf, close the shadow
            if decision_type in ("entry", "add"):
                # Learning System v2: Store near_miss_gates/gate_margins for ACTIVE entries
                if decision_type == "entry":
                    reasons = act.get("reasons") or {}
                    if "gate_margins" in reasons:
                        features = position.get("features") or {}
                        features["gate_margins"] = reasons.get("gate_margins")
                        features["near_miss_gates"] = reasons.get("near_miss_gates")
                        # Force update of features at end of loop by setting flag
                        # We use exec_history_updated logic or just rely on it being True for entry?
                        # Let's ensure it's saved by setting a flag if we have one, or just dirtying the dict
                        # The save happens at: if logging_meta_updated or exec_history_updated: ... update(features)
                        # We'll set logging_meta_updated = True to force save if not already set
                        logging_meta_updated = True 

                try:
                    token_contract = position.get("token_contract")
                    token_chain = position.get("token_chain")
                    timeframe_pos = position.get("timeframe")
                    
                    # Check for existing shadow position
                    shadow_check = self.sb.table("lowcap_positions")\
                        .select("id")\
                        .eq("token_contract", token_contract)\
                        .eq("token_chain", token_chain)\
                        .eq("timeframe", timeframe_pos)\
                        .eq("status", "shadow")\
                        .limit(1)\
                        .execute()
                    
                    if shadow_check.data and len(shadow_check.data) > 0:
                        shadow_id = shadow_check.data[0]["id"]
                        # Close shadow without recording trajectory (active will track real outcome)
                        self.sb.table("lowcap_positions").update({
                            "status": "watchlist",
                            "entry_event": None,
                        }).eq("id", shadow_id).execute()
                        
                        logger.info(
                            "SHADOW→ACTIVE: Closed shadow position (gates passed) | "
                            "shadow_id=%s token=%s/%s tf=%s",
                            str(shadow_id)[:8], position.get("token_ticker"),
                            token_chain, timeframe_pos
                        )
                except Exception as e:
                    logger.warning(f"Failed shadow→active conversion check: {e}")
            
            # Merge lever diagnostics into reasons for audit
            lever_diag = {}
            try:
                lever_diag = (act.get("lever_diag") or {})  # actions may not include; fallback below
            except Exception:
                lever_diag = {}
            reasons = {**(act.get("reasons") or {}), **lever_diag, "regime_state": phase}  # phase is formatted string like "Macro S0, Meso S1, Micro S3"
            # Derive a simple ordered reasons list for audit (stable key order)
            preferred_order = [
                "phase_meso",
                "envelope",
                "mode",
                "sr_break",
                "diag_break",
                "sr_conf",
                "diag_conf",
                "trail",
                "obv_slope",
                "vo_z",
                "retrace_r",
                "zone",
                "std_hits",
                "strong",
                "zone_trim_count",
                "moon_bag_target",
                "moon_bag_clamped",
            ]
            reasons_ordered: list[dict] = []
            for k in preferred_order:
                if k in reasons:
                    reasons_ordered.append({"name": k, "value": reasons[k]})
            # append any remaining keys deterministically
            for k in sorted(reasons.keys()):
                if k not in {r["name"] for r in reasons_ordered}:
                    reasons_ordered.append({"name": k, "value": reasons[k]})
            
            # Extract v5 pattern key, action_category, scope, and controls
            try:
                features = position.get("features") or {}
                uptrend_signals = features.get("uptrend_engine_v4") or {}
                
                # Build action_context for pattern key generation
                action_context = {
                    "state": uptrend_signals.get("state", "Unknown"),
                    "timeframe": timeframe,
                    "a_final": a_val,
                    "e_final": e_val,
                    "buy_flag": uptrend_signals.get("buy_flag", False),
                    "first_dip_buy_flag": uptrend_signals.get("first_dip_buy_flag", False),
                    "reclaimed_ema333": uptrend_signals.get("reclaimed_ema333", False),
                    "at_support": (features.get("geometry") or {}).get("at_support", False),
                    "is_dx_buy": "dx_buy_number" in reasons,
                    "market_family": "lowcaps",  # PM only trades lowcaps
                }
                
                # Generate canonical pattern key and action_category
                pattern_key, action_category = generate_canonical_pattern_key(
                    module="pm",
                    action_type=decision_type,
                    action_context=action_context,
                    uptrend_signals=uptrend_signals
                )
                
                # Extract unified scope
                scope = build_unified_scope(
                    position=position,
                    regime_context=regime_context or {}
                )
                
                # Extract controls (signals + applied knobs)
                # Note: applied_knobs would come from plan_actions_v4 or overrides
                # For now, we'll extract what we can from the action/reasons
                applied_knobs = {
                    "entry_delay_bars": reasons.get("entry_delay_bars"),
                    "phase1_frac": reasons.get("phase1_frac"),
                    "trim_delay": reasons.get("trim_delay"),
                    "trail_speed": reasons.get("trail_speed"),
                }
                controls = extract_controls_from_action(
                    action_context=action_context,
                    uptrend_signals=uptrend_signals,
                    applied_knobs=applied_knobs
                )
            except Exception as e:
                logger.warning(f"Error extracting v5 pattern data for {token}: {e}")
                pattern_key = None
                action_category = None
                scope = {}
                controls = {}
            
            # Build content JSONB with all PM-specific operational data
            content_data = {
                "position_id": position_id,  # Include in content too
                "token_contract": token,
                "chain": chain,
                "ts": now.replace(second=0, microsecond=0, tzinfo=timezone.utc).isoformat(),
                "decision_type": act.get("decision_type"),
                "size_frac": float(act.get("size_frac", 0.0)),
                "a_value": a_val,
                "e_value": e_val,
                "reasons": {"ordered": reasons_ordered, **reasons},
                "new_token_mode": False,
            }

            learning_mults = act.get("learning_multipliers") or {}
            if learning_mults:
                content_data["learning_multipliers"] = learning_mults
                if "pm_strength" in learning_mults:
                    content_data.setdefault("pm_strength_applied", learning_mults["pm_strength"])
                if "exposure_skew" in learning_mults:
                    content_data.setdefault("exposure_skew_applied", learning_mults["exposure_skew"])
                if "combined_multiplier" in learning_mults:
                    content_data.setdefault("pm_final_multiplier", learning_mults["combined_multiplier"])
            
            # Add v5 learning fields if available
            if pattern_key:
                content_data["pattern_key"] = pattern_key
            if action_category:
                content_data["action_category"] = action_category
            if scope:
                content_data["scope"] = scope
            if controls:
                content_data["controls"] = controls
            if trade_id:
                content_data["trade_id"] = trade_id
            
            # Add gate_margins and near_miss_gates for entry actions (learning system uses these)
            if decision_type == "entry":
                if reasons.get("gate_margins"):
                    content_data["gate_margins"] = reasons.get("gate_margins")
                if reasons.get("near_miss_gates"):
                    content_data["near_miss_gates"] = reasons.get("near_miss_gates")
                if reasons.get("entry_event"):
                    content_data["entry_event"] = reasons.get("entry_event")
            
            # Add execution result if available
            if execution_results:
                exec_key = f"{position_id}:{act.get('decision_type')}"
                exec_result = execution_results.get(exec_key)
                if exec_result:
                    content_data["execution_result"] = {
                        "status": exec_result.get("status"),
                        "tx_hash": exec_result.get("tx_hash"),
                        "slippage": exec_result.get("slippage"),
                        "price": exec_result.get("price"),
                    }
            
            # Record last trim signal SR level for gating (even if no execution or no position)
            if decision_type == "trim":
                sr_level_price = reasons.get("sr_level_price")
                if sr_level_price is not None:
                    exec_history["last_trim_signal"] = {
                        "timestamp": now.isoformat(),
                        "sr_level_price": sr_level_price,
                    }
                    exec_history_updated = True
            
            # Build strand with proper ad_strands schema structure
            strand = {
                "id": f"pm_action_{position_id}_{decision_type}_{int(now.timestamp() * 1000)}",
                "module": "pm",
                "kind": "pm_action",
                "symbol": token_ticker,
                "timeframe": timeframe,
                "position_id": position_id,  # Top-level column for querying
                "trade_id": trade_id,
                "content": content_data,  # All PM-specific data in content JSONB
                "regime_context": regime_context or {},  # Macro/meso/micro phases
                "tags": ["pm_action", "execution", decision_type],
                "target_agent": "learning_system",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
            
            rows.append(strand)
        # Persist logging throttle metadata and trim signal history even if no strands were written this tick
        if logging_meta_updated or exec_history_updated:
            try:
                if logging_meta_updated:
                    features["pm_logging_meta"] = logging_meta
                if exec_history_updated:
                    features["pm_execution_history"] = exec_history
                self.sb.table("lowcap_positions").update({"features": features}).eq("id", position_id).execute()
            except Exception as e:
                logger.warning(f"Error updating features for position %s: %s", position_id, e)
        if not rows:
            return
        try:
            self.sb.table("ad_strands").insert(rows).execute()
            # Emit decision_approved events (note: realized_proceeds not available here)
            try:
                from src.intelligence.lowcap_portfolio_manager.events.bus import emit
                for r in rows:
                    decision_type_emit = r.get("content", {}).get("decision_type", "")
                    if str(decision_type_emit or "").lower() != "hold":
                        emit("decision_approved", {
                            "token": r.get("content", {}).get("token_contract"),
                            "decision_type": decision_type_emit,
                            "a_value": r.get("content", {}).get("a_value"),
                            "e_value": r.get("content", {}).get("e_value"),
                            "phase_meso": phase,
                            "realized_proceeds": 0.0,
                        })
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"strand write failed for {token}: {e}")

    def process_position(self, position: Dict[str, Any], regime_context: Optional[Dict[str, Any]] = None, pm_cfg: Optional[Dict[str, Any]] = None, exposure_lookup: Optional["ExposureLookup"] = None, bucket_map: Optional[Dict[tuple, str]] = None) -> int:
        """
        Process a single position (extracted from run() for testing).
        
        Args:
            position: Position dict from database
            regime_context: Optional pre-computed regime context (if None, will compute)
            pm_cfg: Optional pre-computed PM config (if None, will load)
            exposure_lookup: Optional pre-computed exposure lookup (if None, will build)
            bucket_map: Optional pre-computed bucket map (if None, will fetch)
        
        Returns:
            Number of strands written
        """
        now = datetime.now(timezone.utc)
        
        # Compute dependencies if not provided
        if regime_context is None:
            regime_context = self._get_regime_context()
        if pm_cfg is None:
            pm_cfg = load_pm_config()
            pm_cfg = fetch_and_merge_db_config(pm_cfg, self.sb)
        bucket_cfg = pm_cfg.get("bucket_order_multipliers") or {}
        if exposure_lookup is None:
            exposure_lookup = self._build_exposure_lookup(regime_context, pm_cfg)
        if bucket_map is None:
            token_keys = [(position.get("token_contract"), position.get("token_chain"))]
            bucket_map = self._fetch_token_buckets(token_keys)
        
        actions_enabled = (os.getenv("ACTIONS_ENABLED", "0") == "1")
        
        p = position
        token_contract = p.get("token_contract")
        token_chain = p.get("token_chain")
        token = token_contract or p.get("token_ticker") or "UNKNOWN"
        token_ticker = p.get("token_ticker") or token_contract or "UNKNOWN"
        features = p.get("features") or {}
        token_bucket = bucket_map.get((token_contract, token_chain)) or bucket_map.get((token_contract, None))
        book_id = p.get("book_id", "onchain_crypto")
        
        # Get regime states for this token's bucket across all timeframes (for logging)
        bucket_states = self._get_bucket_regime_state(token_bucket)
        # Format as string for backward compatibility with plan_actions_v4
        regime_state_str = f"Macro {bucket_states['macro']}, Meso {bucket_states['meso']}, Micro {bucket_states['micro']}"
        # Full regime bundle across drivers/horizons for scope/learning
        regime_state_bundle = self._get_regime_states_bundle(token_bucket)

        # Compute A/E - use v2 if enabled, otherwise legacy compute_levers
        use_ae_v2 = pm_cfg.get("feature_flags", {}).get("ae_v2_enabled", False)
        
        if use_ae_v2:
            # A/E v2: Flag-driven, strength is first-class
            regime_flags = extract_regime_flags(self.sb, token_bucket, book_id)
            a_base, e_base, ae_diag = compute_ae_v2(regime_flags, token_bucket)
            
            # Log A/E v2 computation
            logger.info(
                "AE_V2: %s bucket=%s | flags → A=%.3f E=%.3f | diag=%s",
                token_ticker, token_bucket, a_base, e_base, ae_diag.get("after_flags", {})
            )
            
            # Note: Strength is applied later in plan_actions_v4 when pattern is known
            a_final = a_base
            e_final = e_base
            position_size_frac = 0.33  # Default, will be overridden by A-score sizing
            
            # Build minimal levers dict for backward compatibility
            le = {
                "A_value": a_final,
                "E_value": e_final,
                "position_size_frac": position_size_frac,
                "ae_v2_diagnostics": ae_diag,
            }
        else:
            # Legacy: compute_levers (regime-driven A + intent deltas + bucket multiplier)
            le = compute_levers(
                features,
                bucket_context=regime_context,
                position_bucket=token_bucket,
                bucket_config=bucket_cfg,
                exec_timeframe=self.timeframe,
            )
            a_final = float(le["A_value"])
            e_final = float(le["E_value"])
            position_size_frac = float(le.get("position_size_frac", 0.33))

        episode_strands: List[Dict[str, Any]] = []
        meta_changed = False
        try:
            episode_strands, meta_changed = self._process_episode_logging(
                position=p,
                regime_context=regime_context,
                token_bucket=token_bucket,
                now=now,
                levers=le, # Pass levers for factor logging
            )
        except Exception as episode_err:
            logger.warning(f"Episode logging failed for position {p.get('id')}: {episode_err}")
            episode_strands = []
            meta_changed = False

        if meta_changed:
            try:
                self.sb.table("lowcap_positions").update({"features": p.get("features")}).eq("id", p.get("id")).execute()
            except Exception as update_err:
                logger.warning(f"Failed to persist episode meta for position {p.get('id')}: {update_err}")
        if episode_strands:
            try:
                self.sb.table("ad_strands").insert(episode_strands).execute()
            except Exception as strand_err:
                logger.warning(f"Failed to insert episode strands for position {p.get('id')}: {strand_err}")
        
        # Recalculate P&L fields before decisions (hybrid approach - check if stale)
        pnl_last_calculated = p.get("pnl_last_calculated_at")
        should_recalculate = False
        
        if not pnl_last_calculated:
            should_recalculate = True
        else:
            try:
                last_calc_dt = datetime.fromisoformat(pnl_last_calculated.replace("Z", "+00:00"))
                minutes_since = (now - last_calc_dt).total_seconds() / 60.0
                # Recalculate if > 5 minutes old (hybrid approach)
                should_recalculate = minutes_since > 5.0
            except Exception:
                should_recalculate = True
        
        if should_recalculate:
            try:
                pnl_updates = self._recalculate_pnl_fields(p)
                if pnl_updates:
                    self.sb.table("lowcap_positions").update(pnl_updates).eq("id", p.get("id")).execute()
                    # Update p dict with new values for this iteration
                    p.update(pnl_updates)
            except Exception as e:
                logger.warning(f"Error recalculating P&L fields for position {p.get('id')}: {e}")
        
        # Use plan_actions_v4 (legacy plan_actions removed)
        if actions_enabled:
            # Get feature flags from config (if available)
            feature_flags = pm_cfg.get("feature_flags", {})
            
            # Diagnostic logging: Log pool state when position is loaded for planning
            position_features = position.get("features") or {}
            position_exec_history = position_features.get("pm_execution_history") or {}
            position_pool = position_exec_history.get("trim_pool")
            if position_pool:
                logger.info(
                    "POOL_DIAG: Position loaded for planning | %s/%s tf=%s position_id=%s | pool=%s",
                    position.get("token_ticker", "?"), position.get("token_chain", "?"), 
                    position.get("timeframe", "?"), position.get("id", "?"), position_pool
                )
            elif position_exec_history:
                logger.debug(
                    "POOL_DIAG: Position loaded (no pool) | %s/%s tf=%s position_id=%s | exec_history_keys=%s",
                    position.get("token_ticker", "?"), position.get("token_chain", "?"),
                    position.get("timeframe", "?"), position.get("id", "?"), list(position_exec_history.keys())
                )
            
            actions = plan_actions_v4(
                p, a_final, e_final, regime_state_str, self.sb,
                regime_context=regime_context,
                token_bucket=token_bucket,
                feature_flags=feature_flags,
                exposure_lookup=exposure_lookup,
                regime_states=regime_state_bundle,
            )
            
            # Log when first-dip buy flag is set but no action returned
            features_check = p.get("features") or {}
            uptrend_check = features_check.get("uptrend_engine_v4") or {}
            first_dip_flag = uptrend_check.get("first_dip_buy_flag", False)
            if first_dip_flag and (not actions or all(a.get("decision_type", "").lower() == "hold" for a in actions)):
                ticker = p.get("token_ticker", p.get("token_contract", "?")[:20])
                logger.info("PM: first_dip_buy_flag=True but no action for %s (%s) - actions=%s", 
                           ticker, p.get("timeframe", "?"), [a.get("decision_type") for a in actions] if actions else "[]")
        else:
            actions = [{"decision_type": "hold", "size_frac": 0.0, "reasons": {}}]
        
        # Attach enhanced A/E diagnostics to each action for strand auditing
        try:
            diag = le.get("diagnostics") or {}
            for act in actions:
                act["lever_diag"] = {
                    **diag,
                    "a_e_components": {
                        "a_final": a_final,
                        "e_final": e_final,
                        "position_size_frac": position_size_frac,
                        "regime_state": bucket_states,  # Dict: {"macro": "S0", "meso": "S1", "micro": "S3"}
                        "regime_state_bundle": regime_state_bundle,
                        "regime_state_str": regime_state_str,  # Formatted string for logging
                        "token_bucket": token_bucket or "unknown",
                        "active_positions": 1  # Single position for process_position
                    }
                }
        except Exception:
            pass
        
        # Execute actions and collect results
        execution_results: Dict[str, Dict[str, Any]] = {}
        
        for act in actions:
            decision_type = act.get("decision_type", "").lower()
            
            # Skip hold actions
            if decision_type == "hold" or not decision_type:
                continue
            
            # Skip execution when no position for trims; still log strand elsewhere
            if decision_type == "trim":
                try:
                    if float(p.get("total_quantity") or 0.0) <= 0.0:
                        exec_key = f"{p.get('id')}:{decision_type}"
                        execution_results[exec_key] = {
                            "status": "skipped",
                            "error": "no_position_for_trim"
                        }
                        continue
                except Exception:
                    pass
            
            # Execute via executor
            try:
                exec_result = self.executor.execute(act, p)
                exec_key = f"{p.get('id')}:{decision_type}"
                execution_results[exec_key] = exec_result
                
                # Log execution result
                exec_status = exec_result.get("status", "unknown")
                logger.info(
                    f"EXECUTION RESULT: {decision_type} {p.get('token_ticker', '')}/{p.get('token_chain', '')} | "
                    f"status={exec_status} | "
                    f"tx_hash={exec_result.get('tx_hash', 'None')[:8] if exec_result.get('tx_hash') else 'None'}"
                )
                
                # Update position table
                if exec_status == "success":
                    # Get a_final and e_final from the action's lever_diag if available
                    lever_diag = act.get("lever_diag", {})
                    a_e_components = lever_diag.get("a_e_components", {})
                    a_final = float(a_e_components.get("a_final", 0.5))
                    e_final = float(a_e_components.get("e_final", 0.5))
                    
                    # Store position status before update (for entry detection)
                    position_status_before = p.get("status", "")
                    
                    self._update_position_after_execution(
                        p.get("id"), decision_type, exec_result, act, p, a_final, e_final
                    )
                    self._update_execution_history(p.get("id"), decision_type, exec_result, act)
                    
                    # Send Telegram notification (non-blocking)
                    # Pass position_status_before to help determine if this is an entry
                    self._send_execution_notification(p, decision_type, exec_result, act, a_final, e_final, position_status_before)
            except Exception as e:
                logger.error(f"Error executing action for position {p.get('id')}: {e}")
                execution_results[f"{p.get('id')}:{decision_type}"] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Check for position closure after all actions (state-based, not action-based)
        # This handles S0 transitions regardless of which action triggered it
        self._check_position_closure(p, "", {}, {})
            
        # Write strands with execution results
        self._write_strands(p, str(token), now, a_final, e_final, regime_state_str, actions, execution_results, regime_context, token_bucket)
        return len(actions)
    
    def run(self) -> int:
        now = datetime.now(timezone.utc)
        # Reset regime cache for this run
        self._regime_state_cache = {}
        
        # Get regime context (bucket summaries) for all PM strands
        regime_context = self._get_regime_context()
        pm_cfg = load_pm_config()
        pm_cfg = fetch_and_merge_db_config(pm_cfg, self.sb)
        bucket_cfg = pm_cfg.get("bucket_order_multipliers") or {}
        exposure_lookup = self._build_exposure_lookup(regime_context, pm_cfg)

        positions = self._active_positions()
        token_keys = [(p.get("token_contract"), p.get("token_chain")) for p in positions]
        bucket_map = self._fetch_token_buckets(token_keys)
        written = 0
        
        for p in positions:
            written += self.process_position(p, regime_context, pm_cfg, exposure_lookup, bucket_map)
        
        logger.info("pm_core_tick (%s) wrote %d strands for %d positions", self.timeframe, written, len(positions))
        return written


def main(timeframe: str = "1h", learning_system=None) -> None:
    """
    Main entry point for PM Core Tick.
    
    Args:
        timeframe: Timeframe to process (1m, 15m, 1h, 4h)
        learning_system: Optional learning system instance for processing position_closed strands
    """
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    PMCoreTick(timeframe=timeframe, learning_system=learning_system).run()


if __name__ == "__main__":
    main()


