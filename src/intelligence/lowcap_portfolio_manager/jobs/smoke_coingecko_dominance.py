"""
Quick, isolated test of CoinGecko dominance endpoints.

No dependencies required (uses urllib). Prints BTC.D and USDT.D using /global;
falls back to computing USDT.D from total market cap and tether market cap.
"""

from __future__ import annotations

import json
import sys
from urllib.request import urlopen, Request
from urllib.parse import urlencode


API = "https://api.coingecko.com/api/v3"


def get_json(path: str, params: dict | None = None) -> dict:
    url = f"{API}{path}"
    if params:
        url += f"?{urlencode(params)}"
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "LotusPM/1.0"})
    with urlopen(req, timeout=20) as resp:  # nosec - read-only public API
        return json.loads(resp.read().decode("utf-8"))


def fetch_global() -> tuple[float | None, float | None, float | None]:
    data = get_json("/global").get("data", {})
    mkt = data.get("market_cap_percentage", {}) or {}
    btc_d = mkt.get("btc")
    usdt_d = mkt.get("usdt")
    total_mc = (data.get("total_market_cap") or {}).get("usd")
    return (
        float(btc_d) if btc_d is not None else None,
        float(usdt_d) if usdt_d is not None else None,
        float(total_mc) if total_mc is not None else None,
    )


def fetch_usdt_mc() -> float | None:
    data = get_json("/coins/markets", {"vs_currency": "usd", "ids": "tether"})
    if not data:
        return None
    mc = data[0].get("market_cap")
    return float(mc) if mc is not None else None


def main() -> None:
    btc_d, usdt_d, total_mc = fetch_global()
    out = {"btc_d": btc_d, "usdt_d": usdt_d, "computed_usdt_d": None}
    if usdt_d is None and total_mc:
        usdt_mc = fetch_usdt_mc()
        if usdt_mc:
            out["computed_usdt_d"] = 100.0 * (usdt_mc / total_mc)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


