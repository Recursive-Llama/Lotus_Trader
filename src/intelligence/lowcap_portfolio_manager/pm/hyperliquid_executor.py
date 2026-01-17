"""
Hyperliquid Executor - Venue-specific order execution for Hyperliquid perps.

Responsibilities:
- Convert ExecutionIntent → concrete order parameters
- Apply venue constraints (min notional, tick size, reduce-only)
- Execute orders via Hyperliquid SDK
- Handle errors and return results

Constraints (from live testing):
- Min notional: $10 per order
- Tick size: Integer for main DEX (BTC), 2 decimals for HIP-3
- Market orders: Emulated via limit IOC with price buffer
- Reduce-only: Only valid when it would decrease position
- Size: Formatted with szDecimals per asset

Env/config:
- HL_ACCOUNT_ADDRESS: Main wallet address
- HL_AGENT_SK: Agent wallet private key
- HL_MIN_NOTIONAL: Min order notional in USD (default 10)
- HL_MARKET_BUFFER_PCT: Price buffer for market orders (default 0.5)
- HL_DRY_RUN: "1" to skip actual order execution
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import math

logger = logging.getLogger(__name__)

# Try to import Hyperliquid SDK
try:
    from eth_account import Account
    from hyperliquid.exchange import Exchange
    from hyperliquid.info import Info
    from hyperliquid.utils import constants
    HL_SDK_AVAILABLE = True
except ImportError:
    HL_SDK_AVAILABLE = False
    logger.warning("Hyperliquid SDK not available - executor will run in dry-run mode only")


@dataclass
class ExecutionResult:
    """Result of an execution attempt."""
    success: bool
    order_id: Optional[str] = None
    filled_size: float = 0.0
    filled_price: float = 0.0
    error: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


class HyperliquidExecutor:
    """
    Executor for Hyperliquid perpetual futures.
    
    Handles:
    - Main DEX assets (BTC, ETH, etc.)
    - HIP-3 assets (xyz:TSLA, etc.)
    """
    
    # Default constraints
    DEFAULT_MIN_NOTIONAL = 10.0
    DEFAULT_MARKET_BUFFER_PCT = 0.5  # 0.5% through top of book
    
    # HIP-3 DEXs to include for symbol resolution
    HIP3_DEXS = ["", "xyz", "flx", "vntl", "hyna", "km"]
    
    def __init__(self, dry_run: bool = None) -> None:
        """
        Initialize the executor.
        
        Args:
            dry_run: If True, skip actual order execution. If None, reads from HL_DRY_RUN env.
        """
        if dry_run is None:
            dry_run = os.getenv("HL_DRY_RUN", "0") == "1"
        
        self.dry_run = dry_run
        self.min_notional = float(os.getenv("HL_MIN_NOTIONAL", str(self.DEFAULT_MIN_NOTIONAL)))
        self.market_buffer_pct = float(os.getenv("HL_MARKET_BUFFER_PCT", str(self.DEFAULT_MARKET_BUFFER_PCT)))
        
        # SDK components (lazy init)
        self._info: Optional[Info] = None
        self._exchange: Optional[Exchange] = None
        self._account_address: Optional[str] = None
        
        # Asset metadata cache
        self._sz_decimals: Dict[str, int] = {}
        self._max_leverage: Dict[str, float] = {}
    
    def _init_sdk(self) -> bool:
        """Initialize Hyperliquid SDK if not already done."""
        if not HL_SDK_AVAILABLE:
            return False
        
        if self._info is not None:
            return True
        
        try:
            account_address = os.getenv("HL_ACCOUNT_ADDRESS", "")
            agent_sk = os.getenv("HL_AGENT_SK", "")
            
            if not account_address or not agent_sk:
                logger.warning("HL_ACCOUNT_ADDRESS and HL_AGENT_SK not set - SDK not initialized")
                return False
            
            self._account_address = account_address
            
            # Initialize Info with all DEXs for symbol resolution
            self._info = Info(
                constants.MAINNET_API_URL,
                skip_ws=True,
                perp_dexs=self.HIP3_DEXS
            )
            
            # Initialize Exchange
            wallet = Account.from_key(agent_sk)
            self._exchange = Exchange(
                wallet=wallet,
                base_url=constants.MAINNET_API_URL,
                account_address=account_address,
                perp_dexs=self.HIP3_DEXS
            )
            
            logger.info("HyperliquidExecutor: SDK initialized for %s", account_address[:10] + "...")
            return True
        
        except Exception as e:
            logger.error("HyperliquidExecutor: Failed to initialize SDK: %s", e)
            return False
    
    def _get_sz_decimals(self, symbol: str) -> int:
        """Get size decimals for a symbol."""
        if symbol in self._sz_decimals:
            return self._sz_decimals[symbol]
        
        # Query from SDK
        if self._info:
            try:
                # SDK caches this in asset_to_sz_decimals
                asset_id = self._info.name_to_asset.get(symbol)
                if asset_id is not None:
                    sz_dec = self._info.asset_to_sz_decimals.get(asset_id, 5)
                    self._sz_decimals[symbol] = sz_dec
                    return sz_dec
            except Exception:
                pass
        
        # Default: 5 for BTC-like, 3 for HIP-3
        if ":" in symbol:
            return 3  # HIP-3 default
        return 5  # Main DEX default
    
    def _get_best_prices(self, symbol: str) -> Tuple[Optional[float], Optional[float]]:
        """Get best bid and ask prices for a symbol."""
        if not self._info:
            return None, None
        
        try:
            import requests
            book = requests.post(
                "https://api.hyperliquid.xyz/info",
                json={"type": "l2Book", "coin": symbol},
                timeout=10
            ).json()
            levels = book.get("levels", [])
            
            if len(levels) >= 2:
                # levels[0] = bids, levels[1] = asks (or vice versa)
                # Need to determine which is which
                bids = levels[0]
                asks = levels[1]
                
                if bids and asks:
                    best_bid = float(bids[0].get("px", 0))
                    best_ask = float(asks[0].get("px", 0))
                    return best_bid, best_ask
        except Exception as e:
            logger.debug("Failed to get order book for %s: %s", symbol, e)
        
        return None, None
    
    def _round_price(self, price: float, symbol: str) -> float:
        """Round price to valid tick size."""
        # For main DEX (BTC, ETH, etc.): integer ticks
        # For HIP-3: 2 decimal places (observed in testing)
        if ":" in symbol:
            return round(price, 2)
        else:
            return float(int(price))
    
    def _format_size(self, size: float, symbol: str) -> str:
        """Format size with correct decimals for the asset."""
        sz_decimals = self._get_sz_decimals(symbol)
        return f"{size:.{sz_decimals}f}"
    
    def _check_constraints(
        self,
        symbol: str,
        side: str,
        size_usd: float,
        reduce_only: bool,
        current_position_size: float,
    ) -> Optional[str]:
        """
        Check if order passes venue constraints.
        
        Returns:
            None if order passes, or skip reason string if it should be skipped.
        """
        # Min notional check
        if size_usd < self.min_notional:
            return f"Below min notional: ${size_usd:.2f} < ${self.min_notional}"
        
        # Reduce-only check
        if reduce_only:
            if current_position_size == 0:
                return "Reduce-only on zero position"
            
            # Check if order would increase position
            is_buy = side.lower() == "buy"
            position_is_long = current_position_size > 0
            
            # Reduce-only buy only valid if short; reduce-only sell only valid if long
            if is_buy and position_is_long:
                return "Reduce-only buy would increase long position"
            if not is_buy and not position_is_long:
                return "Reduce-only sell would increase short position"
        
        return None
    
    def get_position_size(self, symbol: str) -> float:
        """Get current position size for a symbol."""
        if not self._init_sdk():
            return 0.0
        
        if not self._account_address:
            return 0.0
        
        try:
            state = self._info.user_state(self._account_address)
            positions = state.get("assetPositions", [])
            
            for pos in positions:
                position = pos.get("position", {})
                coin = position.get("coin", "")
                if coin == symbol:
                    szi = position.get("szi", "0")
                    return float(szi)
        except Exception as e:
            logger.warning("Failed to get position for %s: %s", symbol, e)
        
        return 0.0
    
    def get_margin_balance(self) -> Optional[float]:
        """
        Get Hyperliquid margin balance (available USDC collateral).
        
        Returns:
            Margin balance in USD, or None if unable to fetch
        """
        if not self._init_sdk():
            return None
        
        if not self._account_address:
            return None
        
        try:
            state = self._info.user_state(self._account_address)
            cross_margin = state.get("crossMarginSummary", {})
            
            # accountValue represents total account value (margin + unrealized PnL)
            # For available margin, we want the raw USD balance
            # totalRawUsd might be better - need to verify which represents available margin
            account_value = cross_margin.get("accountValue")
            total_raw_usd = cross_margin.get("totalRawUsd")
            
            # Use totalRawUsd if available (raw margin), otherwise accountValue
            # accountValue includes unrealized PnL which we don't want for allocation
            margin_balance = total_raw_usd if total_raw_usd is not None else account_value
            
            if margin_balance is not None:
                return float(margin_balance)
            
            logger.warning("Hyperliquid user_state did not return margin balance")
            return None
        except Exception as e:
            logger.warning("Failed to get Hyperliquid margin balance: %s", e)
            return None
    
    def execute_market_order(
        self,
        symbol: str,
        side: str,
        notional_usd: float,
        reduce_only: bool = False,
        current_position_size: Optional[float] = None,
    ) -> ExecutionResult:
        """
        Execute a market order (emulated via limit IOC).
        
        Args:
            symbol: Symbol to trade (e.g., "BTC" or "xyz:TSLA")
            side: "buy" or "sell"
            notional_usd: Order size in USD
            reduce_only: If True, only reduce position
            current_position_size: Current position size (optional, will query if not provided)
        
        Returns:
            ExecutionResult with order details or error
        """
        # Get current position if not provided
        if current_position_size is None:
            current_position_size = self.get_position_size(symbol)
        
        # Check constraints
        skip_reason = self._check_constraints(
            symbol, side, notional_usd, reduce_only, current_position_size
        )
        if skip_reason:
            return ExecutionResult(
                success=False,
                skipped=True,
                skip_reason=skip_reason
            )
        
        # Get best prices for market emulation
        if not self._init_sdk():
            if self.dry_run:
                return ExecutionResult(
                    success=True,
                    skipped=True,
                    skip_reason="Dry run - SDK not initialized"
                )
            return ExecutionResult(success=False, error="SDK not available")
        
        best_bid, best_ask = self._get_best_prices(symbol)
        if best_bid is None or best_ask is None:
            return ExecutionResult(success=False, error="Could not get order book")
        
        # Calculate limit price with buffer
        is_buy = side.lower() == "buy"
        if is_buy:
            # Buy: cross the ask with buffer
            limit_price = best_ask * (1 + self.market_buffer_pct / 100)
        else:
            # Sell: cross the bid with buffer
            limit_price = best_bid * (1 - self.market_buffer_pct / 100)
        
        # Round to tick size
        limit_price = self._round_price(limit_price, symbol)
        
        # Calculate size in contracts
        # Use mid price for size calculation
        mid_price = (best_bid + best_ask) / 2
        size_contracts = notional_usd / mid_price
        
        # Format size with correct decimals
        sz_decimals = self._get_sz_decimals(symbol)
        size_contracts = round(size_contracts, sz_decimals)
        
        # Check if size is valid after rounding
        if size_contracts <= 0:
            return ExecutionResult(
                success=False,
                skipped=True,
                skip_reason=f"Size rounds to zero with {sz_decimals} decimals"
            )
        
        # Dry run
        if self.dry_run:
            logger.info(
                "[DRY RUN] %s %s: size=%.{%d}f @ %.2f (notional=$%.2f)",
                side.upper(), symbol, size_contracts, sz_decimals, limit_price, notional_usd
            )
            return ExecutionResult(
                success=True,
                filled_size=size_contracts,
                filled_price=mid_price,
                skipped=True,
                skip_reason="Dry run"
            )
        
        # Execute order
        try:
            result = self._exchange.order(
                name=symbol,
                is_buy=is_buy,
                sz=size_contracts,
                limit_px=limit_price,
                order_type={"limit": {"tif": "Ioc"}},  # Immediate-or-cancel
                reduce_only=reduce_only,
            )
            
            # Parse result
            if result.get("status") == "ok":
                statuses = result.get("response", {}).get("data", {}).get("statuses", [])
                if statuses:
                    status = statuses[0]
                    
                    if "filled" in status:
                        filled = status["filled"]
                        return ExecutionResult(
                            success=True,
                            order_id=str(filled.get("oid")),
                            filled_size=float(filled.get("totalSz", 0)),
                            filled_price=float(filled.get("avgPx", 0)),
                        )
                    elif "resting" in status:
                        # Order is resting (shouldn't happen with IOC)
                        return ExecutionResult(
                            success=True,
                            order_id=str(status["resting"].get("oid")),
                            filled_size=0,
                            filled_price=0,
                        )
                    elif "error" in status:
                        return ExecutionResult(
                            success=False,
                            error=status["error"]
                        )
            
            return ExecutionResult(
                success=False,
                error=f"Unexpected response: {result}"
            )
        
        except Exception as e:
            logger.error("Order execution failed for %s: %s", symbol, e)
            return ExecutionResult(success=False, error=str(e))
    
    def execute_limit_order(
        self,
        symbol: str,
        side: str,
        notional_usd: float,
        limit_price: float,
        reduce_only: bool = False,
        current_position_size: Optional[float] = None,
        time_in_force: str = "Gtc",
    ) -> ExecutionResult:
        """
        Execute a limit order.
        
        Args:
            symbol: Symbol to trade
            side: "buy" or "sell"
            notional_usd: Order size in USD
            limit_price: Limit price
            reduce_only: If True, only reduce position
            current_position_size: Current position size (optional)
            time_in_force: "Gtc" (good-till-cancel), "Ioc", or "Alo"
        
        Returns:
            ExecutionResult with order details or error
        """
        # Get current position if not provided
        if current_position_size is None:
            current_position_size = self.get_position_size(symbol)
        
        # Check constraints
        skip_reason = self._check_constraints(
            symbol, side, notional_usd, reduce_only, current_position_size
        )
        if skip_reason:
            return ExecutionResult(
                success=False,
                skipped=True,
                skip_reason=skip_reason
            )
        
        if not self._init_sdk():
            if self.dry_run:
                return ExecutionResult(
                    success=True,
                    skipped=True,
                    skip_reason="Dry run - SDK not initialized"
                )
            return ExecutionResult(success=False, error="SDK not available")
        
        # Round price to tick size
        limit_price = self._round_price(limit_price, symbol)
        
        # Calculate size in contracts
        size_contracts = notional_usd / limit_price
        sz_decimals = self._get_sz_decimals(symbol)
        size_contracts = round(size_contracts, sz_decimals)
        
        if size_contracts <= 0:
            return ExecutionResult(
                success=False,
                skipped=True,
                skip_reason=f"Size rounds to zero with {sz_decimals} decimals"
            )
        
        is_buy = side.lower() == "buy"
        
        # Dry run
        if self.dry_run:
            logger.info(
                "[DRY RUN] LIMIT %s %s: size=%.{%d}f @ %.2f (notional=$%.2f)",
                side.upper(), symbol, size_contracts, sz_decimals, limit_price, notional_usd
            )
            return ExecutionResult(
                success=True,
                filled_size=0,  # Limit order, not filled yet
                filled_price=limit_price,
                skipped=True,
                skip_reason="Dry run"
            )
        
        # Execute order
        try:
            result = self._exchange.order(
                name=symbol,
                is_buy=is_buy,
                sz=size_contracts,
                limit_px=limit_price,
                order_type={"limit": {"tif": time_in_force}},
                reduce_only=reduce_only,
            )
            
            # Parse result (similar to market order)
            if result.get("status") == "ok":
                statuses = result.get("response", {}).get("data", {}).get("statuses", [])
                if statuses:
                    status = statuses[0]
                    
                    if "filled" in status:
                        filled = status["filled"]
                        return ExecutionResult(
                            success=True,
                            order_id=str(filled.get("oid")),
                            filled_size=float(filled.get("totalSz", 0)),
                            filled_price=float(filled.get("avgPx", 0)),
                        )
                    elif "resting" in status:
                        return ExecutionResult(
                            success=True,
                            order_id=str(status["resting"].get("oid")),
                            filled_size=0,
                            filled_price=limit_price,
                        )
                    elif "error" in status:
                        return ExecutionResult(
                            success=False,
                            error=status["error"]
                        )
            
            return ExecutionResult(
                success=False,
                error=f"Unexpected response: {result}"
            )
        
        except Exception as e:
            logger.error("Limit order failed for %s: %s", symbol, e)
            return ExecutionResult(success=False, error=str(e))
    
    def cancel_order(self, symbol: str, order_id: int) -> bool:
        """Cancel an order by ID."""
        if not self._init_sdk() or self.dry_run:
            return True
        
        try:
            result = self._exchange.cancel(symbol, order_id)
            return result.get("status") == "ok"
        except Exception as e:
            logger.error("Cancel failed for %s oid=%d: %s", symbol, order_id, e)
            return False

