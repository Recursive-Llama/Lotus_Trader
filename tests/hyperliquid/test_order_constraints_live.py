"""
Live constraint tests for Hyperliquid orders (no fills expected).

Prereqs:
- Env vars: HL_ACCOUNT_ADDRESS, HL_AGENT_SK
- .venv active

Tests (all expected to be rejected by HL, no fills):
1) Min notional: $5 BTC IOC -> expect "Order must have minimum value of $10."
2) Tick size: BTC IOC with off-tick price -> expect "Price must be divisible by tick size."
3) Reduce-only with zero position: BTC reduce-only IOC -> expect "Reduce only order would increase position."
"""

import os
import json
import requests
from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants

INFO_URL = "https://api.hyperliquid.xyz/info"
PERP_DEXS = ["", "xyz", "flx", "vntl", "hyna", "km"]
BTC = "BTC"


def env_or_raise(key: str) -> str:
    v = os.environ.get(key)
    if not v:
        raise RuntimeError(f"Missing env var: {key}")
    return v


def book_tops(coin: str):
    resp = requests.post(INFO_URL, json={"type": "l2Book", "coin": coin}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    bids, asks = data["levels"][0], data["levels"][1]
    return float(bids[0]["px"]), float(asks[0]["px"])


def main():
    account = env_or_raise("HL_ACCOUNT_ADDRESS")
    sk = env_or_raise("HL_AGENT_SK")
    wallet = Account.from_key(sk)

    info = Info(constants.MAINNET_API_URL, skip_ws=True, perp_dexs=PERP_DEXS)
    exch = Exchange(wallet=wallet, base_url=constants.MAINNET_API_URL, account_address=account, perp_dexs=PERP_DEXS)

    print("== user_state (for sanity) ==")
    state = info.user_state(account)
    print(json.dumps(state.get("assetPositions", []), indent=2))

    best_bid, best_ask = book_tops(BTC)

    # 1) Min notional fail: ~$5 notional, on-tick price, IOC
    price_tick = round(best_ask)  # integer tick
    # size must align to szDecimals; pad slightly and round to 5 decimals
    sz = round(5.0 / price_tick + 1e-7, 5)  # ~$5
    print("\n== Test 1: Min notional ($5) ==")
    res = exch.order(
        name=BTC,
        is_buy=True,
        sz=sz,
        limit_px=price_tick,
        order_type={"limit": {"tif": "Ioc"}},
        reduce_only=False,
    )
    print(json.dumps(res, indent=2))

    # 2) Tick size fail: off-tick price (adds decimals), notional ~$11 to clear min
    off_tick_px = best_ask + 0.123  # should violate integer tick
    sz2 = round(11.0 / best_ask + 1e-7, 5)
    print("\n== Test 2: Tick size (off-tick price) ==")
    res = exch.order(
        name=BTC,
        is_buy=True,
        sz=sz2,
        limit_px=off_tick_px,
        order_type={"limit": {"tif": "Ioc"}},
        reduce_only=False,
    )
    print(json.dumps(res, indent=2))

    # 3) Reduce-only on zero position
    print("\n== Test 3: Reduce-only on zero position ==")
    res = exch.order(
        name=BTC,
        is_buy=False,
        sz=sz,
        limit_px=price_tick,
        order_type={"limit": {"tif": "Ioc"}},
        reduce_only=True,
    )
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()

