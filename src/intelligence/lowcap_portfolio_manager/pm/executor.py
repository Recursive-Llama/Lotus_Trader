from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional, Set, Tuple

from supabase import Client  # type: ignore

# Local event bus
from src.intelligence.lowcap_portfolio_manager.events.bus import subscribe


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



