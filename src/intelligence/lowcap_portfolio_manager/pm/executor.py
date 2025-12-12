from __future__ import annotations

import os
import json
import time
import logging
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set, Tuple

from supabase import Client  # type: ignore

# Local event bus
from src.intelligence.lowcap_portfolio_manager.events.bus import subscribe

logger = logging.getLogger(__name__)

# Try to import web3 for EVM contract calls
try:
    from web3 import Web3
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    logger.warning("web3 not available - cannot fetch token decimals from contract directly")


_idem_cache: Dict[str, float] = {}


def _idem_key(token: str, decision_type: str) -> str:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0).isoformat()
    return f"{token}:{decision_type}:{now}"


def _idem_allow(key: str, ttl_s: int = 180) -> bool:
    now = time.time()
    # evict old
    to_del = [k for k, t in _idem_cache.items() if now - t > ttl_s]
    for k in to_del:
        _idem_cache.pop(k, None)
    if key in _idem_cache:
        return False
    _idem_cache[key] = now
    return True


def _get_position(sb: Client, token_contract: str) -> Dict[str, Any]:
    rows = (
        sb.table("lowcap_positions")
        .select("id, token_chain, token_ticker, total_quantity, features")
        .eq("token_contract", token_contract)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else {}


def _latest_price(sb: Client, token_contract: str, chain: str) -> Tuple[Optional[float], Optional[float]]:
    """Return (price_usd, price_native) from latest 1m bar if present."""
    try:
        row = (
            sb.table("lowcap_price_data_1m")
            .select("price_usd, price_native")
            .eq("token_contract", token_contract)
            .eq("chain", chain)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not row:
            return None, None
        r = row[0]
        return (float(r.get("price_usd") or 0.0) or None, float(r.get("price_native") or 0.0) or None)
    except Exception:
        return None, None


def _latest_price_ohlc(sb: Client, token_contract: str, chain: str, timeframe: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Return (price_usd, price_native) from latest OHLC bar for specific timeframe.
    
    Args:
        sb: Supabase client
        token_contract: Token contract address
        chain: Chain (solana, ethereum, base, bsc)
        timeframe: Timeframe (1m, 15m, 1h, 4h)
    
    Returns:
        Tuple of (price_usd, price_native) or (None, None) if not found
        Note: price_native is the token price in native currency (e.g., token price in SOL, BNB, ETH)
    """
    try:
        row = (
            sb.table("lowcap_price_data_ohlc")
            .select("close_usd, close_native")
            .eq("token_contract", token_contract)
            .eq("chain", chain)
            .eq("timeframe", timeframe)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not row:
            return None, None
        r = row[0]
        return (float(r.get("close_usd") or 0.0) or None, float(r.get("close_native") or 0.0) or None)
    except Exception as e:
        logger.warning(f"Error fetching OHLC price for {token_contract} {timeframe}: {e}")
        return None, None


def _get_native_usd_rate(sb: Client, chain: str) -> float:
    """
    Get native currency USD rate (e.g., SOL/USD, BNB/USD, ETH/USD) for converting USD to native.
    
    Args:
        sb: Supabase client
        chain: Chain (solana, ethereum, base, bsc)
    
    Returns:
        Native currency USD rate (e.g., SOL price in USD) or 0.0 if not found
    """
    try:
        # Map chains to their native token contracts
        native_contracts = {
            'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
            'base': '0x4200000000000000000000000000000000000006',      # WETH (Base)
            'bsc': '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c',       # WBNB
            'solana': 'So11111111111111111111111111111111111111112'      # SOL
        }
        
        native_contract = native_contracts.get(chain.lower())
        if not native_contract:
            logger.warning(f"Unknown chain for native USD rate: {chain}")
            return 0.0
        
        # Use Ethereum WETH price for both Ethereum and Base
        lookup_chain = 'ethereum' if chain.lower() in ['ethereum', 'base'] else chain.lower()
        
        # Get latest native token price from database
        result = sb.table('lowcap_price_data_1m').select(
            'price_usd'
        ).eq('token_contract', native_contract).eq('chain', lookup_chain).order(
            'timestamp', desc=True
        ).limit(1).execute()
        
        if result.data and len(result.data) > 0:
            return float(result.data[0].get('price_usd', 0))
        else:
            logger.warning(f"No native token price found in database for {chain}")
            return 0.0
            
    except Exception as e:
        logger.warning(f"Error getting native USD rate for {chain}: {e}")
        return 0.0


def register_pm_executor(trader: Any, sb: Client) -> None:
    """Subscribe to decision_approved and execute PM decisions (non-hold) when enabled.

    trader: live trader instance with chain executors available
    sb: Supabase client for lookups
    """
    if os.getenv("ACTIONS_ENABLED", "0") != "1":
        return
    canary = set([s.strip() for s in os.getenv("PM_CANARY_SYMBOLS", "").split(",") if s.strip()])

    def on_decision(payload: Dict[str, Any]) -> None:
        try:
            decision_type = str(payload.get("decision_type") or "").lower()
            token = str(payload.get("token") or "")
            if not token or decision_type in {"", "hold"}:
                return
            # Canary filter
            if canary:
                tkr_row = _get_position(sb, token)
                if not tkr_row:
                    return
                ticker = (tkr_row.get("token_ticker") or "").upper()
                if ticker and ticker not in canary:
                    return
            key = _idem_key(token, decision_type)
            if not _idem_allow(key):
                return

            # Minimal revalidation/sizing
            pos = _get_position(sb, token)
            if not pos:
                return
            chain = str(pos.get("token_chain") or "").lower()
            total_qty = float(pos.get("total_quantity") or 0.0)
            price_usd, price_native = _latest_price(sb, token, chain)

            # Execute per decision type
            if decision_type == "trim" or decision_type == "trail":
                # size_frac = fraction of remaining bag (we use strand reasons-based sizing elsewhere);
                # here rely on a conservative 0.20 if missing
                size_frac = float(payload.get("size_frac") or 0.20)
                tokens_to_sell = max(0.0, total_qty * size_frac)
                if tokens_to_sell <= 0:
                    return
                # Call chain executor (best-effort)
                try:
                    if chain == "bsc" and getattr(trader, "bsc_executor", None):
                        trader.bsc_executor.execute_sell(token, tokens_to_sell, float(price_usd or 0.0))
                    elif chain == "base" and getattr(trader, "base_executor", None):
                        trader.base_executor.execute_sell(token, tokens_to_sell, float(price_usd or 0.0))
                    elif chain == "ethereum" and getattr(trader, "eth_executor", None):
                        trader.eth_executor.execute_sell(token, tokens_to_sell, float(price_usd or 0.0))
                    elif chain == "solana" and getattr(trader, "sol_executor", None):
                        # solana executor likely async; skip in sync bus
                        pass
                except Exception:
                    return

            elif decision_type == "add" or decision_type == "trend_add":
                # size_frac for add is fraction of DM cap; try to derive USD notional from positions total_allocation_usd or BOOK_NAV
                try:
                    alloc_usd = float(pos.get("total_allocation_usd") or 0.0)
                except Exception:
                    alloc_usd = 0.0
                if alloc_usd <= 0.0:
                    try:
                        nav = float(os.getenv("BOOK_NAV", "0") or 0)
                        pct = float(pos.get("total_allocation_pct") or 0.0)
                        alloc_usd = nav * (pct / 100.0) if nav > 0 and pct > 0 else 0.0
                    except Exception:
                        alloc_usd = 0.0
                size_frac = float(payload.get("size_frac") or 0.0)
                notional_usd = max(0.0, alloc_usd * size_frac)
                if notional_usd <= 0 or not price_usd:
                    return
                # Convert to tokens amount for EVM sells/buys; for buys, many executors expect native spend; skip conversion details here
                tokens_to_buy = notional_usd / float(price_usd)
                try:
                    if chain == "bsc" and getattr(trader, "bsc_executor", None):
                        # If executor requires native spend, a separate conversion is needed; using token amount path if supported
                        trader.bsc_executor.execute_buy(token, notional_usd)  # best-effort: many executors accept USD notionals
                    elif chain == "base" and getattr(trader, "base_executor", None):
                        trader.base_executor.execute_buy(token, notional_usd)
                    elif chain == "ethereum" and getattr(trader, "eth_executor", None):
                        trader.eth_executor.execute_buy(token, notional_usd)
                    elif chain == "solana" and getattr(trader, "sol_executor", None):
                        # solana executor likely async; skip in sync bus
                        pass
                except Exception:
                    return
        except Exception:
            return

    subscribe("decision_approved", on_decision)


# ============================================================================
# Direct Executor Interface (v4 - PM calls directly, no events)
# ============================================================================

class PMExecutor:
    """
    Direct executor interface for Portfolio Manager.
    
    Uses Li.Fi SDK (via Node.js) for unified cross-chain execution.
    Accepts USDC amounts and handles bridging automatically.
    """
    
    def __init__(self, trader: Any, sb_client: Client):
        """
        Initialize PM Executor.
        
        Args:
            trader: Trader instance (kept for compatibility, but not used for execution)
            sb_client: Supabase client for price lookups and balance tracking
        """
        self.trader = trader
        self.sb = sb_client
        
        # Path to Li.Fi executor script
        script_dir = Path(__file__).parent.parent.parent.parent.parent / "scripts" / "lifi_sandbox" / "src"
        self.lifi_executor_path = script_dir / "lifi_executor.mjs"
        
        if not self.lifi_executor_path.exists():
            logger.error(f"Li.Fi executor script not found at {self.lifi_executor_path}")
        
        # Gas management configuration
        self.native_gas_target_usd = float(os.getenv("NATIVE_GAS_TARGET_USD", "15.0"))  # Target native token amount (~$15)
        self.native_gas_min_usd = float(os.getenv("NATIVE_GAS_MIN_USD", "5.0"))  # Minimum before top-up (~$5)
        self.home_chain = os.getenv("HOME_CHAIN", "solana").lower()  # Home chain where all USDC is kept
        
        # Token decimals cache (to avoid repeated lookups)
        self._decimals_cache: Dict[Tuple[str, str], int] = {}
    
    def _get_chain_id(self, chain: str) -> str:
        """Map chain name to Li.Fi chain identifier."""
        chain_map = {
            "solana": "solana",
            "sol": "solana",
            "ethereum": "ethereum",
            "eth": "ethereum",
            "base": "base",
            "bsc": "bsc",
        }
        return chain_map.get(chain.lower(), chain.lower())
    
    def _get_token_decimals(self, token_contract: str, chain: str) -> int:
        """
        Get token decimals by calling the contract directly.
        
        Args:
            token_contract: Token contract address
            chain: Chain name (ethereum, base, bsc)
        
        Returns:
            Token decimals (defaults to 18 if not found)
        """
        cache_key = (token_contract.lower(), chain.lower())
        
        # Check cache first
        if cache_key in self._decimals_cache:
            return self._decimals_cache[cache_key]
        
        # For EVM chains, fetch decimals directly from contract
        if chain.lower() in ['ethereum', 'eth', 'base', 'bsc']:
            if not WEB3_AVAILABLE:
                logger.warning(f"web3 not available, cannot fetch decimals for {token_contract} on {chain}")
                decimals = 18
                self._decimals_cache[cache_key] = decimals
                return decimals
            
            try:
                # Get RPC URL from environment
                rpc_env_map = {
                    'ethereum': ['ETH_RPC_URL', 'ETHEREUM_RPC_URL'],
                    'eth': ['ETH_RPC_URL', 'ETHEREUM_RPC_URL'],
                    'base': ['BASE_RPC_URL'],
                    'bsc': ['BSC_RPC_URL'],
                }
                
                rpc_url = None
                for env_var in rpc_env_map.get(chain.lower(), []):
                    rpc_url = os.getenv(env_var)
                    if rpc_url:
                        break
                
                if not rpc_url:
                    logger.warning(f"No RPC URL found for {chain}, cannot fetch decimals")
                    decimals = 18
                    self._decimals_cache[cache_key] = decimals
                    return decimals
                
                # Connect to chain and call decimals()
                w3 = Web3(Web3.HTTPProvider(rpc_url))
                
                # ERC20 decimals() function ABI
                decimals_abi = [{
                    "constant": True,
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function"
                }]
                
                contract = w3.eth.contract(
                    address=Web3.to_checksum_address(token_contract),
                    abi=decimals_abi
                )
                
                decimals = int(contract.functions.decimals().call())
                logger.info(f"Fetched decimals for {token_contract} on {chain}: {decimals}")
                self._decimals_cache[cache_key] = decimals
                return decimals
                
            except Exception as e:
                logger.warning(f"Could not fetch decimals from contract for {token_contract} on {chain}: {e}")
                # Default to 18 decimals (most common)
                decimals = 18
                self._decimals_cache[cache_key] = decimals
                return decimals
        
        # For Solana, we'd need different logic (not implemented here)
        # Default to 18 for unknown chains
        decimals = 18
        self._decimals_cache[cache_key] = decimals
        return decimals
    
    def _get_balance(self, chain: str, token: str = "USDC") -> float:
        """
        Get balance for a chain and token from wallet_balances table.
        
        Args:
            chain: Chain name (solana, ethereum, base, bsc)
            token: Token symbol ("USDC" for USDC, "native" for native token)
        
        Returns:
            Balance in USD (for USDC) or native amount (for native token)
        """
        try:
            result = self.sb.table("wallet_balances").select("*").eq("chain", chain.lower()).limit(1).execute()
            if not result.data:
                return 0.0
            
            row = result.data[0]
            if token.upper() == "USDC":
                # USDC balance - only on home chain (Solana)
                if "usdc_balance" in row:
                    return float(row.get("usdc_balance", 0.0))
                else:
                    # Fallback: use balance_usd (which should represent USDC value)
                    return float(row.get("balance_usd", 0.0))
            elif token.lower() == "native":
                # Native token balance (for gas)
                return float(row.get("balance", 0.0))
            else:
                return 0.0
        except Exception as e:
            logger.warning(f"Error getting balance for {chain} {token}: {e}")
            return 0.0
    
    def _get_solana_usdc_balance(self) -> float:
        """Get USDC balance on Solana (home chain) - all capital is here."""
        return self._get_balance(self.home_chain, "USDC")
    
    def _check_solana_usdc_sufficient(self, required_usd: float) -> bool:
        """Check if Solana has sufficient USDC for the trade."""
        solana_usdc = self._get_solana_usdc_balance()
        if solana_usdc < required_usd:
            logger.error(f"Insufficient USDC on Solana: ${solana_usdc:.2f} < ${required_usd:.2f}")
            return False
        return True
    
    def _check_and_topup_gas(self, chain: str) -> bool:
        """
        Check native token balance and top up if below minimum.
        
        Args:
            chain: Target chain to check
        
        Returns:
            True if gas is sufficient or top-up succeeded, False otherwise
        """
        if chain.lower() == self.home_chain.lower():
            # Home chain doesn't need gas top-up (we have native token there)
            return True
        
        # Get current native token balance
        native_balance = self._get_balance(chain, "native")
        
        # Get native token USD rate
        try:
            native_usd_rate = _get_native_usd_rate(self.sb, chain)
            native_balance_usd = float(native_balance) * native_usd_rate if native_usd_rate > 0 else 0.0
        except Exception as e:
            logger.warning(f"Could not get native USD rate for {chain}: {e}")
            native_balance_usd = 0.0
        
        # Check if we need to top up
        if native_balance_usd >= self.native_gas_min_usd:
            return True  # Gas is sufficient
        
        # Calculate top-up amount (target - current, but at least $5)
        topup_amount_usd = max(self.native_gas_target_usd - native_balance_usd, self.native_gas_min_usd)
        
        # Check Solana USDC balance
        solana_usdc = self._get_solana_usdc_balance()
        if solana_usdc < topup_amount_usd:
            logger.warning(f"Insufficient Solana USDC for gas top-up: ${solana_usdc:.2f} < ${topup_amount_usd:.2f}")
            # Still allow trade to proceed, just log warning
            return True
        
        logger.info(f"Topping up gas on {chain}: ${topup_amount_usd:.2f} (current: ${native_balance_usd:.2f})")
        
        # Convert USD to USDC amount (6 decimals)
        usdc_amount = str(int(topup_amount_usd * 1_000_000))
        
        # Get native token address for target chain
        native_token_map = {
            "ethereum": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
            "base": "0x4200000000000000000000000000000000000006",  # WETH
            "bsc": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
        }
        native_token = native_token_map.get(chain.lower())
        if not native_token:
            logger.warning(f"No native token mapping for {chain}, skipping gas top-up")
            return True
        
        # Execute cross-chain swap: Solana USDC → Target Chain Native Token
        result = self._call_lifi_executor(
            action="swap",
            chain=chain,  # Target chain
            from_token="USDC",
            to_token=native_token,
            amount=usdc_amount,
            slippage=0.5,
            from_chain=self.home_chain,  # Source: Solana
            to_chain=chain  # Target: destination chain
        )
        
        if not result.get("success"):
            logger.warning(f"Gas top-up failed: {result.get('error')}, but allowing trade to proceed")
            return True  # Don't block trade if gas top-up fails
        
        logger.info(f"Gas top-up successful: {result.get('tx_hash')}")
        
        # Update wallet balances after top-up
        self._update_balance_after_trade(self.home_chain, "USDC", -topup_amount_usd)
        # Native token balance will be updated by scheduled job
        
        return True
    
    def _update_balance_after_trade(self, chain: str, token: str, amount_change: float) -> None:
        """
        Update wallet balance in database after a trade or bridge.
        
        Args:
            chain: Chain name
            token: Token symbol ("USDC" or "native")
            amount_change: Amount change (positive for increase, negative for decrease)
        """
        try:
            # Get current balance
            result = self.sb.table("wallet_balances").select("*").eq("chain", chain.lower()).limit(1).execute()
            
            if not result.data:
                # Create new entry
                self.sb.table("wallet_balances").insert({
                    "chain": chain.lower(),
                    "balance": amount_change if token.lower() == "native" else 0.0,
                    "usdc_balance": amount_change if token.upper() == "USDC" else 0.0,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }).execute()
            else:
                # Update existing entry
                current = result.data[0]
                updates: Dict[str, Any] = {
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
                
                if token.upper() == "USDC":
                    # Check if usdc_balance column exists
                    if "usdc_balance" in current:
                        current_usdc = float(current.get("usdc_balance", 0.0))
                        updates["usdc_balance"] = max(0.0, current_usdc + amount_change)
                    else:
                        # Column doesn't exist yet - update balance_usd as fallback
                        logger.warning(f"usdc_balance column not found in wallet_balances, using balance_usd as fallback")
                        current_usd = float(current.get("balance_usd", 0.0))
                        updates["balance_usd"] = max(0.0, current_usd + amount_change)
                elif token.lower() == "native":
                    current_native = float(current.get("balance", 0.0))
                    updates["balance"] = max(0.0, current_native + amount_change)
                
                self.sb.table("wallet_balances").update(updates).eq("chain", chain.lower()).execute()
                
        except Exception as e:
            logger.warning(f"Error updating wallet balance for {chain} {token}: {e}")
    
    def _call_lifi_executor(
        self, 
        action: str, 
        chain: str, 
        from_token: str, 
        to_token: str, 
        amount: str, 
        slippage: float = 0.5,
        from_chain: str = None,
        to_chain: str = None
    ) -> Dict[str, Any]:
        """
        Call Li.Fi executor Node.js script via subprocess.
        
        Args:
            action: "swap" or "bridge"
            chain: Chain name (for swaps, ignored for bridges)
            from_token: Source token (USDC or contract address)
            to_token: Target token (contract address)
            amount: Amount in token's smallest unit (e.g., "1000000" for 1 USDC with 6 decimals)
            slippage: Slippage tolerance (default 0.5%)
            from_chain: Source chain (for bridges, required)
            to_chain: Target chain (for bridges, required)
        
        Returns:
            Result dict from Li.Fi executor
        """
        if not self.lifi_executor_path.exists():
            return {
                "success": False,
                "error": f"Li.Fi executor script not found at {self.lifi_executor_path}"
            }
        
        input_data = {
            "action": action,
            "fromToken": from_token,
            "toToken": to_token,
            "amount": amount,
            "slippage": slippage,
            "dryRun": False,
        }
        
        # For swaps, support both single-chain and cross-chain
        if action == "swap":
            if from_chain and to_chain and from_chain.lower() != to_chain.lower():
                # Cross-chain swap: specify fromChain and toChain
                input_data["fromChain"] = self._get_chain_id(from_chain)
                input_data["toChain"] = self._get_chain_id(to_chain)
            else:
                # Single-chain swap: use chain parameter
                input_data["chain"] = self._get_chain_id(chain)
        # For bridges, use fromChain and toChain
        elif action == "bridge":
            if not from_chain or not to_chain:
                return {
                    "success": False,
                    "error": "from_chain and to_chain required for bridge action"
                }
            input_data["fromChain"] = self._get_chain_id(from_chain)
            input_data["toChain"] = self._get_chain_id(to_chain)
        
        # Retry logic for failed executions
        max_retries = 2
        retry_delay = 2.0  # seconds
        
        for attempt in range(max_retries + 1):
            try:
                # Call Node.js script with JSON input
                result = subprocess.run(
                    ["node", str(self.lifi_executor_path), json.dumps(input_data)],
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    cwd=str(self.lifi_executor_path.parent.parent)
                )
                
                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout or "Unknown error"
                    logger.warning(f"Li.Fi executor failed (attempt {attempt + 1}/{max_retries + 1}): {error_msg}")
                    
                    # Retry on certain errors (network issues, timeouts)
                    if attempt < max_retries and any(keyword in error_msg.lower() for keyword in ["timeout", "network", "connection", "econnrefused"]):
                        time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                        continue
                    
                    return {
                        "success": False,
                        "error": f"Li.Fi executor failed: {error_msg}"
                    }
                
                # Parse JSON output
                # Note: The script may output non-JSON lines (e.g., dotenv messages) before the JSON
                try:
                    stdout_lines = result.stdout.strip().split('\n')
                    json_line = None
                    
                    # Find the line that starts with '{' (the JSON output)
                    for line in stdout_lines:
                        line_stripped = line.strip()
                        if line_stripped.startswith('{'):
                            json_line = line_stripped
                            break
                    
                    if not json_line:
                        logger.error(f"Li.Fi executor returned no JSON output. stdout: {result.stdout[:500]}")
                        return {
                            "success": False,
                            "error": "Li.Fi executor returned no JSON output"
                        }
                    
                    output = json.loads(json_line)
                    
                    # Harden logging: surface executor-level errors even when JSON parses
                    if not output.get("success", False):
                        # For "No transaction hash captured" errors, capture more stderr (contains diagnostics)
                        error_msg = output.get("error", "")
                        is_tx_hash_error = "No transaction hash captured" in error_msg
                        stderr_limit = 2000 if is_tx_hash_error else 500
                        stdout_limit = 1000 if is_tx_hash_error else 500
                        
                        logger.warning(
                            "Li.Fi executor returned error output (action=%s, chain=%s, from=%s, to=%s, amount=%s): %s | stdout=%s | stderr=%s",
                            action,
                            input_data.get("chain") or f"{input_data.get('fromChain')}->{input_data.get('toChain')}",
                            from_token,
                            to_token,
                            amount,
                            error_msg,
                            (result.stdout or "")[:stdout_limit],
                            (result.stderr or "")[:stderr_limit],
                        )
                        
                        # For tx hash errors, also extract and log diagnostic JSON from stderr
                        if is_tx_hash_error:
                            for line in result.stderr.split('\n'):
                                if '[LiFi]' in line and ('Diagnostics:' in line or 'Route structure:' in line):
                                    logger.warning(f"Li.Fi executor diagnostic: {line}")
                    
                    return output
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Li.Fi executor output: {e}")
                    logger.error(f"Raw stdout (first 1000 chars): {result.stdout[:1000]}")
                    logger.error(f"Raw stderr (first 1000 chars): {result.stderr[:1000]}")
                    logger.error(f"Return code: {result.returncode}")
                    return {
                        "success": False,
                        "error": f"Failed to parse executor output: {e}. stdout: {result.stdout[:200]}"
                    }
                
            except subprocess.TimeoutExpired:
                logger.warning(f"Li.Fi executor timed out (attempt {attempt + 1}/{max_retries + 1})")
                if attempt < max_retries:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                return {
                    "success": False,
                    "error": "Li.Fi executor timed out after retries"
                }
            except Exception as e:
                logger.error(f"Error calling Li.Fi executor (attempt {attempt + 1}/{max_retries + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Should not reach here, but just in case
        return {
            "success": False,
            "error": "Li.Fi executor failed after all retries"
        }
    
    def execute(self, decision: Dict[str, Any], position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a trading decision directly using Li.Fi SDK.
        
        Args:
            decision: Decision dict from plan_actions_v4() with:
                - decision_type: "entry", "add", "trim", "emergency_exit"
                - size_frac: Fraction of allocation (add) or position (trim)
                - reasons: Dict with flag, state, scores, etc.
            position: Position dict with:
                - id: Position ID
                - token_contract: Token contract address
                - token_chain: Chain (solana, ethereum, base, bsc)
                - timeframe: Timeframe (1m, 15m, 1h, 4h)
                - total_allocation_usd: Total allocation for this position
                - total_quantity: Current tokens held
        
        Returns:
            Execution result dict with:
                - status: "success" | "error"
                - tx_hash: Transaction hash (if successful)
                - tokens_bought: Tokens bought (for adds)
                - tokens_sold: Tokens sold (for trims/exits)
                - price: Execution price (USD)
                - price_native: Execution price (native)
                - slippage: Slippage percentage
                - error: Error message (if failed)
        """
        decision_type = decision.get("decision_type", "").lower()
        token_contract = position.get("token_contract", "")
        chain = position.get("token_chain", "").lower()
        timeframe = position.get("timeframe", "1h")
        size_frac = float(decision.get("size_frac", 0.0))
        token_label = position.get("token_ticker") or token_contract
        logger.info("EXEC START: %s %s/%s tf=%s size_frac=%.4f", decision_type, token_label, chain, timeframe, size_frac)
        
        if not token_contract or not decision_type or decision_type == "hold":
            result = {
                "status": "error",
                "error": "Invalid decision or missing token contract"
            }
            logger.warning("EXEC SKIP: %s %s/%s (%s)", decision_type, token_label, chain, result["error"])
            return result
        
        # Get latest price from OHLC table (timeframe-specific)
        price_usd, price_native = _latest_price_ohlc(self.sb, token_contract, chain, timeframe)
        
        if not price_usd:
            result = {
                "status": "error",
                "error": f"No price data available for {token_contract} {timeframe}"
            }
            logger.warning("EXEC SKIP: %s %s/%s (%s)", decision_type, token_label, chain, result["error"])
            return result
        
        # Execute based on decision type
        if decision_type in ["add", "entry"]:
            result = self._execute_add(decision, position, chain, token_contract, price_usd, price_native, size_frac)
            status = result.get("status")
            if status == "success":
                logger.info("EXEC OK: add/entry %s/%s tf=%s bought=%.6f price=%.8f",
                            token_label, chain, timeframe, result.get("tokens_bought", 0.0), result.get("price") or 0.0)
            else:
                logger.error("EXEC FAIL: add/entry %s/%s tf=%s err=%s",
                             token_label, chain, timeframe, result.get("error", "unknown"))
            return result
        elif decision_type in ["trim", "emergency_exit"]:
            result = self._execute_sell(decision, position, chain, token_contract, price_usd, price_native, size_frac)
            status = result.get("status")
            if status == "success":
                logger.info("EXEC OK: sell %s/%s tf=%s sold=%.6f price=%.8f",
                            token_label, chain, timeframe, result.get("tokens_sold", 0.0), result.get("price") or 0.0)
            else:
                logger.error("EXEC FAIL: sell %s/%s tf=%s err=%s",
                             token_label, chain, timeframe, result.get("error", "unknown"))
            return result
        else:
            result = {
                "status": "error",
                "error": f"Unsupported decision type: {decision_type}"
            }
            logger.warning("EXEC SKIP: %s %s/%s (%s)", decision_type, token_label, chain, result["error"])
            return result
    
    def _execute_add(
        self,
        decision: Dict[str, Any],
        position: Dict[str, Any],
        chain: str,
        token_contract: str,
        price_usd: float,
        price_native: float,
        size_frac: float
    ) -> Dict[str, Any]:
        """
        Execute a buy order using cross-chain swap from Solana USDC → target chain token.
        
        Always uses cross-chain swap from Solana (home chain) to target chain.
        No pre-bridging needed - Li.Fi handles bridge + swap in one transaction.
        """
        try:
            # Calculate notional USD from usd_alloc_remaining (remaining capacity)
            usd_alloc_remaining = float(position.get("usd_alloc_remaining") or 0.0)
            if usd_alloc_remaining <= 0:
                return {
                    "status": "error",
                    "error": "No remaining allocation available for this position"
                }
            
            # size_frac is a percentage of usd_alloc_remaining (e.g., 0.30 = 30% of remaining)
            notional_usd = usd_alloc_remaining * size_frac
            if notional_usd <= 0:
                return {
                    "status": "error",
                    "error": "Invalid size_frac or allocation"
                }
            
            # Check Solana USDC balance (all capital is on Solana)
            if not self._check_solana_usdc_sufficient(notional_usd):
                return {
                    "status": "error",
                    "error": f"Insufficient USDC on Solana (home chain)"
                }
            
            # Check and top up gas on target chain if needed
            self._check_and_topup_gas(chain)
            
            # Convert USD to USDC amount (6 decimals)
            usdc_amount = str(int(notional_usd * 1_000_000))
            
            # Execute cross-chain swap: Solana USDC → Target Chain Token
            # Li.Fi automatically handles bridge + swap in one transaction
            result = self._call_lifi_executor(
                action="swap",
                chain=chain,  # Target chain
                from_token="USDC",
                to_token=token_contract,
                amount=usdc_amount,
                slippage=0.5,  # 0.5% slippage tolerance
                from_chain=self.home_chain,  # Source: Solana
                to_chain=chain  # Target: destination chain
            )
            
            if not result.get("success"):
                return {
                    "status": "error",
                    "error": result.get("error", "Li.Fi cross-chain swap failed")
                }
            
            # Extract results
            tx_hash = result.get("tx_hash")
            token_decimals = result.get("to_token_decimals")
            try:
                token_decimals = int(token_decimals) if token_decimals is not None else None
            except (TypeError, ValueError):
                token_decimals = None

            if token_decimals is not None:
                cache_key = (token_contract.lower(), chain.lower())
                self._decimals_cache[cache_key] = token_decimals

            tokens_field = result.get("tokens_received")
            tokens_received_raw = result.get("tokens_received_raw")
            to_token_decimals = result.get("to_token_decimals")
            
            # Parse tokens_received - Li.Fi should return human-readable amount, but verify
            tokens_received = float(tokens_field or 0.0)
            
            # Log what we received from Li.Fi for debugging
            logger.info(
                f"Li.Fi execution result for {token_contract} on {chain}: "
                f"tokens_received={tokens_received} (type={type(tokens_field).__name__}, raw_value={tokens_field}), "
                f"tokens_received_raw={tokens_received_raw}, to_token_decimals={to_token_decimals}, "
                f"notional_usd={notional_usd}, price_from_lifi={result.get('price')}"
            )
            
            # CRITICAL: If we have tokens_received_raw, always prefer it over tokens_received
            # Li.Fi's tokens_received may use wrong decimals, but raw value is always correct
            # Fetch correct decimals from the contract and recalculate
            if tokens_received_raw:
                try:
                    raw_value = float(tokens_received_raw)
                    
                    # Fetch correct decimals from the contract
                    correct_decimals = self._get_token_decimals(token_contract, chain)
                    
                    # Recalculate using correct decimals
                    recalculated = raw_value / (10 ** correct_decimals)
                    
                    # Check if there's a discrepancy
                    if tokens_received > 0:
                        diff_pct = abs(recalculated - tokens_received) / max(recalculated, tokens_received) * 100
                        if diff_pct > 1.0:  # More than 1% difference
                            logger.warning(
                                f"Decimal mismatch for {token_contract} on {chain}: "
                                f"Li.Fi reported={tokens_received} (using decimals={to_token_decimals}), "
                                f"correct={recalculated} (using decimals={correct_decimals} from contract), "
                                f"raw={tokens_received_raw}"
                            )
                    else:
                        # tokens_received is suspiciously small or zero
                        logger.warning(
                            f"Li.Fi reported suspicious tokens_received={tokens_received} for {token_contract} on {chain}. "
                            f"Recalculating from raw={tokens_received_raw} using correct decimals={correct_decimals} from contract"
                        )
                    
                    # Always use the recalculated value with correct decimals
                    tokens_received = recalculated
                    # Update token_decimals for consistency
                    if token_decimals is None or token_decimals != correct_decimals:
                        token_decimals = correct_decimals
                        cache_key = (token_contract.lower(), chain.lower())
                        self._decimals_cache[cache_key] = correct_decimals
                            
                except (ValueError, TypeError, ZeroDivisionError) as e:
                    logger.warning(f"Failed to recalculate tokens from raw for {token_contract} on {chain}: {e}")
            
            # Calculate price: USD spent / tokens received
            # Since this is a full execution (not partial), use notional_usd
            actual_price = float(result.get("price", price_usd))
            if tokens_received > 0:
                actual_price = notional_usd / tokens_received
            else:
                logger.error(f"Invalid tokens_received={tokens_received} for {token_contract} on {chain}")
            
            slippage = float(result.get("slippage", 0.0))
            
            # Update wallet balance (subtract USDC from Solana)
            self._update_balance_after_trade(self.home_chain, "USDC", -notional_usd)
            
            return {
                "status": "success",
                "tx_hash": tx_hash,
                "tokens_bought": tokens_received,
                "tokens_bought_raw": result.get("tokens_received_raw"),
                "token_decimals": token_decimals,
                "price": actual_price,
                "price_native": price_native,
                "notional_usd": notional_usd,  # USD amount that was intended and executed
                "slippage": slippage
            }
                
        except Exception as e:
            logger.error(f"Error executing buy for {token_contract}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _execute_sell(
        self,
        decision: Dict[str, Any],
        position: Dict[str, Any],
        chain: str,
        token_contract: str,
        price_usd: float,
        price_native: float,
        size_frac: float
    ) -> Dict[str, Any]:
        """
        Execute a sell order using cross-chain swap: target chain token → Solana USDC.
        
        Always swaps back to Solana USDC (home chain) - all proceeds go to Solana.
        Li.Fi handles bridge + swap in one transaction.
        """
        try:
            # Calculate tokens to sell
            total_quantity = float(position.get("total_quantity") or 0.0)
            if total_quantity <= 0:
                return {
                    "status": "error",
                    "error": "No tokens to sell (total_quantity is 0)"
                }
            
            tokens_to_sell = total_quantity * size_frac
            if tokens_to_sell <= 0:
                return {
                    "status": "error",
                    "error": "Invalid size_frac or quantity"
                }
            
            # Get token decimals (prefer cached/features)
            token_decimals = None
            features = position.get("features") if isinstance(position.get("features"), dict) else {}
            if isinstance(features, dict):
                token_decimals = features.get("token_decimals")
            if token_decimals is not None:
                try:
                    token_decimals = int(token_decimals)
                except (TypeError, ValueError):
                    token_decimals = None
            if token_decimals is None:
                token_decimals = self._get_token_decimals(token_contract, chain)
            
            # Convert tokens to smallest unit
            token_amount = str(int(tokens_to_sell * (10 ** token_decimals)))
            
            # Execute cross-chain swap: Target Chain Token → Solana USDC
            # Li.Fi automatically handles swap + bridge in one transaction
            result = self._call_lifi_executor(
                action="swap",
                chain=chain,  # Source chain (where token is)
                from_token=token_contract,
                to_token="USDC",
                amount=token_amount,
                slippage=0.5,  # 0.5% slippage tolerance
                from_chain=chain,  # Source: token's chain
                to_chain=self.home_chain  # Target: Solana (home chain)
            )
            
            if not result.get("success"):
                return {
                    "status": "error",
                    "error": result.get("error", "Li.Fi cross-chain swap failed")
                }
            
            # Extract results
            tx_hash = result.get("tx_hash")
            usdc_received = float(result.get("tokens_received", 0.0))  # USDC received on Solana
            actual_usd = usdc_received  # USDC received is already in USD
            actual_price = float(result.get("price", price_usd))
            if tokens_to_sell > 0:
                actual_price = actual_usd / tokens_to_sell
            slippage = float(result.get("slippage", 0.0))
            token_decimals = result.get("from_token_decimals")
            try:
                token_decimals = int(token_decimals) if token_decimals is not None else None
            except (TypeError, ValueError):
                token_decimals = None
            if token_decimals is not None:
                cache_key = (token_contract.lower(), chain.lower())
                self._decimals_cache[cache_key] = token_decimals
            
            # Calculate expected vs actual
            expected_usd = tokens_to_sell * price_usd
            actual_usd = usdc_received  # USDC received is already in USD
            
            # Update wallet balance (add USDC to Solana)
            self._update_balance_after_trade(self.home_chain, "USDC", actual_usd)
            
            return {
                "status": "success",
                "tx_hash": tx_hash,
                "tokens_sold": tokens_to_sell,
                "price": actual_price,
                "price_native": price_native,
                "expected_usd": expected_usd,
                "actual_usd": actual_usd,
                "slippage": slippage
            }
                
        except Exception as e:
            logger.error(f"Error executing sell for {token_contract}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }



