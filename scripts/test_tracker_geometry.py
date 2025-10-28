#!/usr/bin/env python3
"""
Test harness for the geometry tracker logic.

- Projects stored diagonals to 'now' using slope/intercept/anchor_time_iso
- Computes SR and diagonal break flags against latest 15m close
- Seeds tracker_trend from geometry.current_trend; may flip on valid breakout
- Prints a concise report and optionally persists updates (--write)

Usage examples:
  ./scripts/test_tracker_geometry.py --limit 3
  ./scripts/test_tracker_geometry.py --contract 0xABC... --chain solana --write
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

from dotenv import load_dotenv  # type: ignore

# Ensure project root is on sys.path when invoked as a standalone script
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.intelligence.lowcap_portfolio_manager.spiral.persist import SpiralPersist
from src.intelligence.lowcap_portfolio_manager.pm.config import load_pm_config


def _project_price(diag: dict, now: datetime) -> Optional[float]:
    try:
        slope = float(diag.get("slope", 0.0))
        intercept = float(diag.get("intercept", 0.0))
        anchor_time = diag.get("anchor_time_iso")
        if not anchor_time:
            return None
        t0 = datetime.fromisoformat(str(anchor_time).replace("Z", "+00:00"))
        hours_since_anchor = (now - t0).total_seconds() / 3600.0
        return slope * hours_since_anchor + intercept
    except Exception:
        return None


def _pick_best(diag_items: List[Tuple[str, dict]]) -> Optional[Tuple[str, dict]]:
    if not diag_items:
        return None
    return max(
        diag_items,
        key=lambda kv: (
            float(kv[1].get("confidence", 0.0)),
            float(kv[1].get("r2_score", 0.0)),
        ),
    )


def _fetch_latest_15m(sb, contract: str, chain: str, now: datetime) -> Tuple[Optional[datetime], float]:
    rows = (
        sb.table("lowcap_price_data_ohlc")
        .select("timestamp, close_native")
        .eq("token_contract", contract)
        .eq("chain", chain)
        .eq("timeframe", "15m")
        .lte("timestamp", now.isoformat())
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return None, 0.0
    ts = datetime.fromisoformat(str(rows[0]["timestamp"]).replace("Z", "+00:00"))
    close = float(rows[0].get("close_native") or 0.0)
    return ts, close


def _evaluate_for_position(sp: SpiralPersist, position: dict, write: bool, now: datetime) -> Dict[str, Any]:
    pid = position.get("id")
    contract = position.get("token_contract")
    chain = position.get("token_chain")
    features = position.get("features") or {}
    geometry = (features.get("geometry") if isinstance(features, dict) else None) or {}
    result: Dict[str, Any] = {"position_id": pid, "contract": contract, "chain": chain}

    if not geometry:
        result["error"] = "no geometry"
        return result

    sb = sp.sb
    bar_ts, close = _fetch_latest_15m(sb, contract, chain, now)
    if bar_ts is None:
        result["error"] = "no 15m bar"
        return result

    # SR levels split
    sr_levels = ((geometry.get("levels") or {}).get("sr_levels") or [])
    supports: List[dict] = []
    resistances: List[dict] = []
    for lvl in sr_levels:
        price_lvl = float(lvl.get("price", 0.0))
        if close > price_lvl:
            supports.append(lvl)
        else:
            resistances.append(lvl)
    sr_nearest = None
    if supports or resistances:
        sr_nearest = min(supports + resistances, key=lambda x: abs(close - float(x.get("price", 0.0))))
    sr_break = "none"
    sr_strength = 0.0
    if sr_nearest:
        plc = float(sr_nearest.get("price", 0.0))
        eps = max(1e-6, 0.002 * close)
        if close > plc + eps:
            sr_break = "bull"
            sr_strength = 0.5 + 0.05 * float(sr_nearest.get("strength", 1))
        elif close < plc - eps:
            sr_break = "bear"
            sr_strength = 0.5 + 0.05 * float(sr_nearest.get("strength", 1))

    # Trends: seed from geometry
    current_trend = geometry.get("current_trend", {})
    geometry_trend = current_trend.get("trend_type")
    tracker_trend = geometry_trend
    tracker_trend_changed = False
    tracker_trend_change_time = None

    # Projection of diagonals
    diags = geometry.get("diagonals") or {}
    diag_levels: Dict[str, Any] = {}
    low_lines = [(k, v) for k, v in diags.items() if "lows" in k]
    high_lines = [(k, v) for k, v in diags.items() if "highs" in k]

    if tracker_trend == "uptrend":
        best_low = _pick_best([kv for kv in low_lines if "uptrend" in kv[0]])
        best_high = _pick_best([kv for kv in high_lines if "uptrend" in kv[0]])
        if best_low:
            px = _project_price(best_low[1], now)
            if px is not None:
                diag_levels["diag_support"] = {"price": px, "strength": float(best_low[1].get("confidence", 1.0))}
        if best_high:
            px = _project_price(best_high[1], now)
            if px is not None:
                diag_levels["diag_resistance"] = {"price": px, "strength": float(best_high[1].get("confidence", 1.0))}
    elif tracker_trend == "downtrend":
        best_high = _pick_best([kv for kv in high_lines if "downtrend" in kv[0]])
        if best_high:
            px = _project_price(best_high[1], now)
            if px is not None:
                diag_levels["diag_resistance"] = {"price": px, "strength": float(best_high[1].get("confidence", 1.0))}
        best_low = _pick_best([kv for kv in low_lines if "downtrend" in kv[0]])
        if best_low:
            px = _project_price(best_low[1], now)
            if px is not None:
                diag_levels.setdefault("diag_support", {"price": px, "strength": float(best_low[1].get("confidence", 1.0))})

    # Replicate tracker breakout state machine at a high level for flip detection
    cfg = load_pm_config()
    tol = float((cfg.get("geom") or {}).get("break_tol_pct", 0.0075))

    # Compute above/below status for each diagonal
    diag_status: Dict[str, Any] = {}
    for k, v in diags.items():
        px = _project_price(v, bar_ts)
        if px is None:
            continue
        diag_status[k] = {
            "projected_price_native": px,
            "above_below": "above" if close > px else "below",
            "distance_pct": (close - px) / px if px else 0.0,
        }

    diag_break = "none"
    diag_strength = 0.0

    if tracker_trend == "downtrend":
        # bull flip if any downtrend highs are broken to the upside beyond tolerance
        for k, st in diag_status.items():
            if ("downtrend" in k) and ("highs" in k) and st.get("above_below") == "above":
                tracker_trend = "uptrend"
                tracker_trend_changed = True
                tracker_trend_change_time = now.isoformat()
                diag_break = "bull"
                break
    elif tracker_trend == "uptrend":
        for k, st in diag_status.items():
            if ("uptrend" in k) and ("lows" in k) and st.get("above_below") == "below":
                tracker_trend = "downtrend"
                tracker_trend_changed = True
                tracker_trend_change_time = now.isoformat()
                diag_break = "bear"
                break

    updates = {
        "geometry_trend": geometry_trend,
        "tracker_trend": tracker_trend,
        "tracker_trend_changed": tracker_trend_changed,
        "tracker_trend_change_time": tracker_trend_change_time,
        "sr_break": sr_break,
        "sr_strength": sr_strength,
        "diag_break": diag_break,
        "diag_strength": diag_strength,
        "sr_levels": {
            "closest_support": {
                "price": float(min(supports, key=lambda x: abs(close - float(x.get("price", 0.0))))["price"]) if supports else None,
                "strength": float(min(supports, key=lambda x: abs(close - float(x.get("price", 0.0))))["strength"]) if supports else None,
            },
            "closest_resistance": {
                "price": float(min(resistances, key=lambda x: abs(close - float(x.get("price", 0.0))))["price"]) if resistances else None,
                "strength": float(min(resistances, key=lambda x: abs(close - float(x.get("price", 0.0))))["strength"]) if resistances else None,
            },
        },
        "diag_levels": diag_levels,
        "diag_status": diag_status,
        "bar_ts": bar_ts.isoformat(),
        "bar_close": close,
        "tracked_at": now.isoformat(),
    }

    if write:
        try:
            sp.write_features_token_geometry(pid, updates)
        except Exception:
            pass

    result.update(updates)
    return result


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser(description="Test geometry tracker projections and flags")
    ap.add_argument("--contract", type=str, default=None, help="Filter by token contract")
    ap.add_argument("--chain", type=str, default=None, help="Filter by chain")
    ap.add_argument("--limit", type=int, default=3, help="Max positions to test")
    ap.add_argument("--write", action="store_true", help="Persist updates back to DB")
    ap.add_argument("--json", action="store_true", help="Output JSON only (no pretty text)")
    args = ap.parse_args()

    sp = SpiralPersist()
    now = datetime.now(timezone.utc)

    q = sp.sb.table("lowcap_positions").select("id,token_contract,token_chain,token_ticker,features").eq("status", "active")
    if args.contract:
        q = q.eq("token_contract", args.contract)
    if args.chain:
        q = q.eq("chain", args.chain)
    rows = q.limit(max(1, args.limit)).execute().data or []
    out = []
    for r in rows:
        out.append(_evaluate_for_position(sp, r, args.write, now))

    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        for item in out:
            name = item.get("contract") or item.get("position_id")
            print("\n==", name, "==")
            print("bar:", item.get("bar_ts"), "close:", f"{item.get('bar_close'):.10f}" if item.get("bar_close") else None)
            print("geometry_trend:", item.get("geometry_trend"), "tracker_trend:", item.get("tracker_trend"), "changed:", item.get("tracker_trend_changed"))
            print("sr_break:", item.get("sr_break"), "sr_strength:", f"{item.get('sr_strength'):.3f}")
            print("diag_break:", item.get("diag_break"), "diag_strength:", f"{item.get('diag_strength'):.3f}")
            print("diag_levels:", json.dumps(item.get("diag_levels") or {}, indent=2))


if __name__ == "__main__":
    main()


