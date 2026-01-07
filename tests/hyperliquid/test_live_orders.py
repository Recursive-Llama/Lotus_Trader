"""
Live Hyperliquid trading tests.

WARNING: This sends real orders. Use tiny notionals.

Required env vars:
- API_WALLET_ADDRESS: API/agent wallet address
- API_WALLET_PRIVATE_KEY: API/agent wallet private key (never printed)

Run with venv: source .venv/bin/activate && python tests/hyperliquid/test_live_orders.py
"""

import os
import time
from typing import Dict, Any, Optional, Tuple

from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils.signing import OrderType


# Configuration
MAIN_COIN = "BTC"
HIP3_COIN = "xyz:TSLA"

# Notional sizes in USD
MAIN_MARKET_NOTIONAL = 5.0
MAIN_LIMIT_NOTIONAL = 2.0
HIP_MARKET_NOTIONAL = 2.0

# Limit price offsets
MAIN_LIMIT_DISCOUNT = 0.99  # 1% below mid


def load_wallet() -> Tuple[Exchange, Info, Info]:
    """Create Exchange + Info clients from environment."""
    addr = os.environ.get("API_WALLET_ADDRESS")
    pk = os.environ.get("API_WALLET_PRIVATE_KEY")
    if not addr or not pk:
        raise SystemExit("Missing API_WALLET_ADDRESS or API_WALLET_PRIVATE_KEY")

    wallet = Account.from_key(pk)

    # Info clients: main + HIP (include perp_dexs for HIP routing)
    info_main = Info(skip_ws=True)
    info_hip = Info(skip_ws=True, perp_dexs=["xyz"])

    # Preload meta so Exchange knows name->asset mappings
    meta_main = info_main.meta()

    # Exchange client (include perp_dexs for HIP orders)
    ex = Exchange(wallet, meta=meta_main, perp_dexs=["xyz"], account_address=addr)

    return ex, info_main, info_hip


def get_sz_decimals(info: Info, coin: str, dex: str = "") -> int:
    """Return szDecimals for a coin, optionally specifying dex for HIP-3."""
    meta = info.meta(dex)
    for asset in meta.get("universe", []):
        if asset.get("name") == coin:
            return asset.get("szDecimals", 4)
    raise ValueError(f"szDecimals not found for {coin} (dex={dex})")


def get_mid_price(info: Info, coin: str) -> float:
    """Get mid price from L2 snapshot."""
    book = info.l2_snapshot(coin)
    bids, asks = book.get("levels", [[], []])
    if not bids or not asks:
        raise ValueError(f"No book data for {coin}")
    best_bid = float(bids[0]["px"])
    best_ask = float(asks[0]["px"])
    return (best_bid + best_ask) / 2.0


def format_size(notional: float, price: float, sz_decimals: int) -> float:
    """Convert USD notional to contract size with correct precision."""
    contracts = notional / price
    return float(f"{contracts:.{sz_decimals}f}")


def place_order(
    ex: Exchange,
    coin: str,
    is_buy: bool,
    size: float,
    price: Optional[float],
    reduce_only: bool = False,
) -> Dict[str, Any]:
    """Place a market or limit order."""
    order_type = OrderType({"market": {}}) if price is None else OrderType({"limit": {"tif": "Gtc"}})
    return ex.order(
        name=coin,
        is_buy=is_buy,
        sz=size,
        limit_px=0 if price is None else price,
        order_type=order_type,
        reduce_only=reduce_only,
    )


def run_main_tests(ex: Exchange, info: Info) -> None:
    print("\n=== MAIN DEX: BTC ===")
    sz_decimals = get_sz_decimals(info, MAIN_COIN)
    mid = get_mid_price(info, MAIN_COIN)
    print(f"Mid price: {mid}")

    # Market buy
    size = format_size(MAIN_MARKET_NOTIONAL, mid, sz_decimals)
    print(f"Market buy {MAIN_COIN}, notional ${MAIN_MARKET_NOTIONAL}, size {size}")
    resp = place_order(ex, MAIN_COIN, True, size, price=None, reduce_only=False)
    print(f"Response: {resp}")

    # Market sell reduce-only to close
    print(f"Market sell (reduce-only) {MAIN_COIN}, size {size}")
    resp = place_order(ex, MAIN_COIN, False, size, price=None, reduce_only=True)
    print(f"Response: {resp}")

    # Limit buy (near mid)
    limit_px = mid * MAIN_LIMIT_DISCOUNT
    limit_size = format_size(MAIN_LIMIT_NOTIONAL, limit_px, sz_decimals)
    print(f"Limit buy {MAIN_COIN} at {limit_px:.2f}, size {limit_size}")
    resp = place_order(ex, MAIN_COIN, True, limit_size, price=limit_px, reduce_only=False)
    print(f"Limit order response: {resp}")
    oid = None
    try:
        oid = resp.get("response", {}).get("data", {}).get("statuses", [{}])[0].get("oid")
    except Exception:
        oid = None
    time.sleep(2)
    if oid is not None:
        print(f"Cancelling limit order oid={oid}")
        cancel_resp = ex.cancel(MAIN_COIN, oid)
        print(f"Cancel response: {cancel_resp}")
    else:
        print("Could not extract oid; skipping cancel.")


def run_hip_tests(ex: Exchange, info: Info) -> None:
    print("\n=== HIP-3: xyz:TSLA ===")
    sz_decimals = get_sz_decimals(info, HIP3_COIN, dex="xyz")
    mid = get_mid_price(info, HIP3_COIN)
    print(f"Mid price: {mid}")

    size = format_size(HIP_MARKET_NOTIONAL, mid, sz_decimals)
    print(f"Market buy {HIP3_COIN}, notional ${HIP_MARKET_NOTIONAL}, size {size}")
    resp = place_order(ex, HIP3_COIN, True, size, price=None, reduce_only=False)
    print(f"Response: {resp}")

    print(f"Market sell (reduce-only) {HIP3_COIN}, size {size}")
    resp = place_order(ex, HIP3_COIN, False, size, price=None, reduce_only=True)
    print(f"Response: {resp}")


def main() -> None:
    ex, info_main, info_hip = load_wallet()

    # Main DEX tests
    run_main_tests(ex, info_main)

    # HIP-3 tests
    try:
        run_hip_tests(ex, info_hip)
    except Exception as e:
        print(f"HIP-3 test failed: {e}")


if __name__ == "__main__":
    main()

