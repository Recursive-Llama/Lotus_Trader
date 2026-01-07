"""
Live Hyperliquid trading smoke tests.

What it does:
- Uses official hyperliquid-python-sdk
- Reads env vars (no secrets printed):
  - HL_ACCOUNT_ADDRESS: funded main wallet
  - HL_AGENT_SK: agent wallet private key
- Exercises:
  1) user_state query (auth check)
  2) BTC market buy (no leverage), reduce-only market sell to flatten
  3) BTC limit buy, then reduce-only market sell to flatten
  4) BTC market buy at 2x leverage, then reduce-only market sell to flatten
  5) HIP3 market buy (xyz:TSLA), reduce-only sell, limit buy, reduce-only sell

Notes:
- Keeps notional small (~$5) per leg.
- Uses mid price from l2Book to size orders.
- Reduce-only closes positions without opening new ones.
"""

import os
import time
import math
import json
from typing import Optional, Tuple

import requests
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants


INFO_URL = "https://api.hyperliquid.xyz/info"

# Targets
BTC_COIN = "BTC"
HIP3_COIN = "xyz:TSLA"

NOTIONAL = 5.0  # USD per leg
HIP3_NOTIONAL = 10.0  # HIP3 enforces $10 min
PERP_DEXS = ["", "xyz", "flx", "vntl", "hyna", "km"]


def env_or_raise(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise RuntimeError(f"Missing env var: {key}")
    return val


def book_tops(coin: str) -> Tuple[float, float]:
    """Return (best_bid, best_ask)."""
    payload = {"type": "l2Book", "coin": coin}
    resp = requests.post(INFO_URL, json=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    levels = data.get("levels", [])
    if not levels or len(levels) < 2 or not levels[0] or not levels[1]:
        raise RuntimeError(f"No book levels for {coin}")
    bids = levels[0]
    asks = levels[1]
    best_bid = float(bids[0]["px"])
    best_ask = float(asks[0]["px"])
    return best_bid, best_ask


def sz_decimals(coin: str, dex: Optional[str] = None) -> int:
    """Get size decimals from meta. Uses dex param for HIP3."""
    if dex:
        payload = {"type": "meta", "dex": dex}
    else:
        payload = {"type": "meta"}
    resp = requests.post(INFO_URL, json=payload, timeout=10)
    resp.raise_for_status()
    meta = resp.json()
    universe = meta.get("universe", [])
    target_name = f"{dex}:{coin}" if dex else coin
    for asset in universe:
        name = asset.get("name")
        if name == target_name or (dex and name == coin):
            return int(asset.get("szDecimals", 4))
    raise RuntimeError(f"Could not find szDecimals for {target_name}")


def format_size(notional_usd: float, price: float, decimals: int) -> float:
    raw = notional_usd / price
    # ensure non-zero
    sized = float(f"{raw:.{decimals}f}")
    if sized == 0.0:
        sized = max(10 ** (-decimals), 0.000001)
    return sized


def place_market(exchange: Exchange, coin: str, is_buy: bool, sz: float, best_bid: float, best_ask: float, reduce_only: bool):
    """
    Hyperliquid has no explicit market flag; emulate with limit IOC crossing the book.
    """
    buffer = 0.005  # 0.5% through the book
    if ":" in coin:
        round_fn = lambda x: round(x, 2)
    else:
        round_fn = lambda x: round(x)  # integer tick for main dex (per order errors)
    if is_buy:
        limit_px = round_fn(best_ask * (1 + buffer))
    else:
        limit_px = round_fn(best_bid * (1 - buffer))
    return exchange.order(
        name=coin,
        is_buy=is_buy,
        sz=sz,
        limit_px=limit_px,
        order_type={"limit": {"tif": "Ioc"}},
        reduce_only=reduce_only,
    )


def place_limit(exchange: Exchange, coin: str, is_buy: bool, sz: float, limit_px: float, reduce_only: bool):
    return exchange.order(
        name=coin,
        is_buy=is_buy,
        sz=sz,
        limit_px=limit_px,
        order_type={"limit": {"tif": "Gtc"}},
        reduce_only=reduce_only,
    )


def run_sequence():
    account = env_or_raise("HL_ACCOUNT_ADDRESS")
    agent_sk = env_or_raise("HL_AGENT_SK")

    wallet = Account.from_key(agent_sk)
    info = Info(constants.MAINNET_API_URL, skip_ws=True, perp_dexs=PERP_DEXS)
    exch = Exchange(
        wallet=wallet,
        base_url=constants.MAINNET_API_URL,
        account_address=account,  # funded main wallet
        perp_dexs=PERP_DEXS,
    )

    print("== Env ==")
    print(f"Account: {account}")
    print(f"Using agent SK from env (hidden)")

    print("\n== Auth check: user_state ==")
    state = info.user_state(account)
    print(json.dumps({k: state.get(k) for k in ["crossMarginSummary", "assetPositions"]}, indent=2))

    # --- BTC market buy / sell ---
    print("\n== BTC market buy (no leverage) ==")
    best_bid, best_ask = book_tops(BTC_COIN)
    btc_mid = (best_bid + best_ask) / 2.0
    btc_dec = sz_decimals(BTC_COIN)
    btc_sz = format_size(NOTIONAL, btc_mid, btc_dec)
    res = place_market(exch, BTC_COIN, True, btc_sz, best_bid, best_ask, reduce_only=False)
    print(json.dumps(res, indent=2))

    print("\n== BTC reduce-only market sell ==")
    res = place_market(exch, BTC_COIN, False, btc_sz, best_bid, best_ask, reduce_only=True)
    print(json.dumps(res, indent=2))

    # --- BTC limit buy / reduce-only market sell ---
    print("\n== BTC limit buy (no leverage) ==")
    limit_px = round(btc_mid * 0.998)  # integer tick
    res = place_limit(exch, BTC_COIN, True, btc_sz, limit_px, reduce_only=False)
    print(json.dumps(res, indent=2))

    print("\n== BTC reduce-only market sell (post-limit) ==")
    best_bid, best_ask = book_tops(BTC_COIN)
    res = place_market(exch, BTC_COIN, False, btc_sz, best_bid, best_ask, reduce_only=True)
    print(json.dumps(res, indent=2))

    # --- BTC higher-size test (simulate leverage by doubling notional) ---
    print("\n== BTC market buy (2x notional test) ==")
    best_bid, best_ask = book_tops(BTC_COIN)
    btc_sz_2x = format_size(NOTIONAL * 2, (best_bid + best_ask) / 2.0, btc_dec)
    res = place_market(exch, BTC_COIN, True, btc_sz_2x, best_bid, best_ask, reduce_only=False)
    print(json.dumps(res, indent=2))

    print("\n== BTC reduce-only market sell (2x) ==")
    best_bid, best_ask = book_tops(BTC_COIN)
    res = place_market(exch, BTC_COIN, False, btc_sz_2x, best_bid, best_ask, reduce_only=True)
    print(json.dumps(res, indent=2))

    # --- HIP3 tests ---
    dex_name, hip3_sym = HIP3_COIN.split(":", 1)
    print(f"\n== HIP3 market buy ({HIP3_COIN}) ==")
    hip_bid, hip_ask = book_tops(HIP3_COIN)
    hip_mid = (hip_bid + hip_ask) / 2.0
    hip_dec = sz_decimals(hip3_sym, dex=dex_name)
    hip_sz = format_size(HIP3_NOTIONAL, hip_mid, hip_dec)
    res = place_market(exch, HIP3_COIN, True, hip_sz, hip_bid, hip_ask, reduce_only=False)
    print(json.dumps(res, indent=2))

    print(f"\n== HIP3 reduce-only market sell ({HIP3_COIN}) ==")
    hip_bid, hip_ask = book_tops(HIP3_COIN)
    res = place_market(exch, HIP3_COIN, False, hip_sz, hip_bid, hip_ask, reduce_only=True)
    print(json.dumps(res, indent=2))

    print(f"\n== HIP3 limit buy ({HIP3_COIN}) ==")
    hip_limit_px = round(hip_mid * 0.997, 2)
    res = place_limit(exch, HIP3_COIN, True, hip_sz, hip_limit_px, reduce_only=False)
    print(json.dumps(res, indent=2))

    print(f"\n== HIP3 reduce-only market sell ({HIP3_COIN}) ==")
    hip_bid, hip_ask = book_tops(HIP3_COIN)
    res = place_market(exch, HIP3_COIN, False, hip_sz, hip_bid, hip_ask, reduce_only=True)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    run_sequence()

