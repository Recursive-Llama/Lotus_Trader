"""
5-minute tracker: returns, streams, lens placeholders, and phase_state writes.
This wires the pipeline end-to-end; detailed math follows SPIRAL modules.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta

from src.intelligence.lowcap_portfolio_manager.spiral.returns import ReturnsComputer
from src.intelligence.lowcap_portfolio_manager.spiral.lenses import compute_lens_scores
from src.intelligence.lowcap_portfolio_manager.spiral.phase import compute_phase_scores, label_from_score, hysteresis_label, band_distance, apply_skip_rules
from src.intelligence.lowcap_portfolio_manager.spiral.persist import SpiralPersist
from src.intelligence.lowcap_portfolio_manager.pm.config import load_pm_config
from src.intelligence.lowcap_portfolio_manager.events import bus


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    now = datetime.now(timezone.utc)

    rc = ReturnsComputer()
    rr = rc.compute(now)

    # Prepare series
    port_series = rr.series_nav_usd or []
    btc_series = rr.series_btc_close or []
    alt_series = rr.series_alt_close or []
    btc_vol = rr.series_btc_volume or []
    alt_vol = rr.series_alt_volume or []

    # Helpers for EMA, regression slope, curvature, delta, z-score
    def ema(values: list[float], span: int) -> list[float]:
        if not values:
            return []
        alpha = 2.0 / (span + 1)
        out: list[float] = [values[0]]
        for v in values[1:]:
            out.append(alpha * v + (1 - alpha) * out[-1])
        return out

    def lin_slope(values: list[float], k: int) -> float:
        n = min(k, len(values))
        if n < 3:
            return 0.0
        xs = list(range(n))
        ys = values[-n:]
        xbar = sum(xs) / n
        ybar = sum(ys) / n
        num = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys))
        den = sum((x - xbar) ** 2 for x in xs) or 1.0
        return num / den

    def curvature(values: list[float], k: int) -> float:
        n = min(k, len(values))
        if n < 6:
            return 0.0
        ys = values[-n:]
        mid = n // 2
        return lin_slope(ys[:mid], mid) - lin_slope(ys[mid:], n - mid)

    def delta(values: list[float], d: int) -> float:
        if len(values) <= d:
            return 0.0
        return values[-1] - values[-(d + 1)]

    def zscore(values: list[float], L: int, current: float) -> float:
        import statistics

        if len(values) < max(5, L):
            return 0.0
        window = values[-L:]
        mean = statistics.fmean(window)
        sd = statistics.pstdev(window) or 1.0
        return (current - mean) / sd

    def stream_metrics(series: list[float], params: dict) -> dict:
        # Smooth, then compute slope/curv/delta/level z-scored
        s = ema(series, params.get("n", 5)) if series else []
        lvl = s[-1] if s else 0.0
        sl = lin_slope(s, params.get("k", 12))
        cv = curvature(s, params.get("k", 12))
        de = delta(s, params.get("d", 6))
        return {
            "level": zscore(s, params.get("L", 30), lvl),
            "slope": zscore(s, params.get("L", 30), sl),
            "curv": zscore(s, params.get("L", 30), cv),
            "delta": zscore(s, params.get("L", 30), de),
        }

    # Volume/OBV/RSI helpers (basic)
    def obv(prices: list[float], volumes: list[float]) -> list[float]:
        out: list[float] = []
        acc = 0.0
        for i in range(len(prices)):
            if i == 0:
                out.append(0.0)
                continue
            if prices[i] > prices[i - 1]:
                acc += volumes[i]
            elif prices[i] < prices[i - 1]:
                acc -= volumes[i]
            out.append(acc)
        return out

    def rsi(prices: list[float], period: int = 14) -> float:
        if len(prices) <= period:
            return 50.0
        gains = []
        losses = []
        for i in range(len(prices) - period, len(prices)):
            ch = prices[i] - prices[i - 1]
            gains.append(max(0.0, ch))
            losses.append(max(0.0, -ch))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period or 1e-9
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    # Build three core series for streams
    series_port_btc = [p - b for p, b in zip(port_series, btc_series)]
    series_port_alt = [p - a for p, a in zip(port_series, alt_series)]
    series_rotation = [a - b for a, b in zip(alt_series, btc_series)]

    # Horizon parameter presets (hours-based; operating on hourly series)
    presets = {
        "micro": {"n": 3, "k": 8, "d": 2, "L": 14},
        "meso": {"n": 5, "k": 12, "d": 6, "L": 30},
        "macro": {"n": 7, "k": 20, "d": 24, "L": 60},
    }

    horizon_scores = {}
    horizon_labels = {}
    lens_by_horizon = {}
    streams_cache = {}

    for hz, params in presets.items():
        m_port_btc = stream_metrics(series_port_btc, params)
        m_port_alt = stream_metrics(series_port_alt, params)
        m_rotation = stream_metrics(series_rotation, params)
        m_btc = stream_metrics(btc_series, params)
        streams_cache[hz] = {
            "port_btc_level": m_port_btc["level"],
            "port_btc_slope": m_port_btc["slope"],
            "port_btc_curv": m_port_btc["curv"],
            "port_btc_delta": m_port_btc["delta"],
            "port_alt_level": m_port_alt["level"],
            "port_alt_slope": m_port_alt["slope"],
            "port_alt_curv": m_port_alt["curv"],
            "port_alt_delta": m_port_alt["delta"],
            "rotation_level": m_rotation["level"],
            "rotation_slope": m_rotation["slope"],
            "rotation_curv": m_rotation["curv"],
            "rotation_delta": m_rotation["delta"],
            "btc_level": m_btc["level"],
            "btc_slope": m_btc["slope"],
            "btc_curv": m_btc["curv"],
            "btc_delta": m_btc["delta"],
        }
        lens_scores = compute_lens_scores({
            **{f"port_btc_{k}": v for k, v in m_port_btc.items()},
            **{f"port_alt_{k}": v for k, v in m_port_alt.items()},
            **{f"rotation_{k}": v for k, v in m_rotation.items()},
            **{f"btc_{k}": v for k, v in m_btc.items()},
        })
        lens_by_horizon[hz] = lens_scores
        ps = compute_phase_scores(lens_scores.__dict__)
        score = getattr(ps, hz)
        label = label_from_score(score)
        horizon_scores[hz] = score
        horizon_labels[hz] = label

    sp = SpiralPersist()
    label_macro = horizon_labels["macro"]
    label_meso = horizon_labels["meso"]
    label_micro = horizon_labels["micro"]

    # Write macro/meso/micro for 'PORTFOLIO' with dwell/hysteresis gating
    horizons = [
        ("macro", horizon_scores["macro"], label_macro),
        ("meso", horizon_scores["meso"], label_meso),
        ("micro", horizon_scores["micro"], label_micro),
    ]
    dwell_min_h = {"macro": 72.0, "meso": 12.0, "micro": 1.0}  # hours

    for horizon, score, raw_label in horizons:
        prev = sp.get_latest_phase_state("PORTFOLIO", horizon)
        prev_label = (prev or {}).get("phase")
        gated_label = hysteresis_label(prev_label, score) if prev_label else raw_label
        gated_label = apply_skip_rules(prev_label, gated_label) if prev_label else gated_label

        # Dwell logic
        dwell_prev = float((prev or {}).get("dwell_remaining") or 0.0)
        label_to_write = gated_label
        dwell_to_write = dwell_min_h[horizon]

        if prev_label:
            if gated_label != prev_label:
                # Attempting a flip: only allow if dwell expired
                if dwell_prev > 0:
                    label_to_write = prev_label  # hold
                    dwell_to_write = max(0.0, dwell_prev - 1.0)
                else:
                    label_to_write = gated_label
                    dwell_to_write = dwell_min_h[horizon]
            else:
                # Same label → count down dwell if active
                dwell_to_write = max(0.0, dwell_prev - 1.0) if dwell_prev > 0 else 0.0

        ls = lens_by_horizon[hz]
        # Confidence: normalized band distance × dwell fraction proxy
        band_dist = band_distance(score)
        dwell_frac = 1.0 - min(1.0, dwell_to_write / max(1.0, dwell_min_h[horizon]))
        confidence = max(0.0, min(1.0, band_dist / 0.8)) * (0.5 + 0.5 * dwell_frac)

        payload = {
            "phase": label_to_write,
            "score": score,
            "slope": streams_cache[hz].get("port_btc_slope", 0.0),
            "curvature": streams_cache[hz].get("port_btc_curv", 0.0),
            "delta_res": streams_cache[hz].get("port_btc_delta", 0.0),
            "confidence": confidence,
            "dwell_remaining": dwell_to_write,
            "pending_label": None if label_to_write == gated_label else gated_label,
            "s_btcusd": ls.S_btcusd,
            "s_rotation": ls.S_rotation,
            "s_port_btc": ls.S_port_btc,
            "s_port_alt": ls.S_port_alt,
        }
        sp.write_phase_state("PORTFOLIO", horizon, now, payload)
        if prev_label and label_to_write != prev_label and dwell_prev <= 0:
            logging.getLogger(__name__).info(
                "phase_transition %s: %s -> %s (score=%.3f)", horizon, prev_label, label_to_write, score
            )
            bus.emit("phase_transition", {"token": "PORTFOLIO", "horizon": horizon, "prev": prev_label, "next": label_to_write, "score": score, "ts": now.isoformat()})

    # Persist shared portfolio-context features for active positions
    context_features = {
        "r_btc": rr.r_btc,
        "r_alt": rr.r_alt,
        "r_port": rr.r_port,
        "residual_major": rr.r_port - rr.r_btc,
        "residual_alt": rr.r_port - rr.r_alt,
        "rotation_spread": rr.r_alt - rr.r_btc,
        "vo": {
            "btc_vol_z": stream_metrics(btc_vol, presets["meso"])['level'],
            "alt_vol_z": stream_metrics(alt_vol, presets["meso"])['level'],
        },
        "obv": {
            "btc_obv_z": stream_metrics(obv(btc_series, btc_vol), presets["meso"])['level'],
            "alt_obv_z": stream_metrics(obv(alt_series, alt_vol), presets["meso"])['level'],
        },
        "rsi": {
            "btc_rsi": rsi(btc_series, 14),
            "alt_rsi": rsi(alt_series, 14),
        },
        "diagnostics": {
            "macro": {
                "S_btcusd": lens_by_horizon["macro"].S_btcusd,
                "S_rotation": lens_by_horizon["macro"].S_rotation,
                "S_port_btc": lens_by_horizon["macro"].S_port_btc,
                "S_port_alt": lens_by_horizon["macro"].S_port_alt,
                "score": horizon_scores["macro"],
                "label": horizon_labels["macro"],
            },
            "meso": {
                "S_btcusd": lens_by_horizon["meso"].S_btcusd,
                "S_rotation": lens_by_horizon["meso"].S_rotation,
                "S_port_btc": lens_by_horizon["meso"].S_port_btc,
                "S_port_alt": lens_by_horizon["meso"].S_port_alt,
                "score": horizon_scores["meso"],
                "label": horizon_labels["meso"],
            },
            "micro": {
                "S_btcusd": lens_by_horizon["micro"].S_btcusd,
                "S_rotation": lens_by_horizon["micro"].S_rotation,
                "S_port_btc": lens_by_horizon["micro"].S_port_btc,
                "S_port_alt": lens_by_horizon["micro"].S_port_alt,
                "score": horizon_scores["micro"],
                "label": horizon_labels["micro"],
            },
        },
        "updated_at": now.isoformat(),
    }
    sp.write_features_portfolio_context(context_features)

    # Light geometry tracker: compare latest price to stored levels/diagonals and update sr_*/diag_* flags
    if os.getenv("GEOMETRY_TRACKER_ENABLED", "0") == "1":
        try:
            sb = sp.sb
            positions = (
                sb.table("lowcap_positions")
                .select("id,token_contract,token_chain,features")
                .eq("status", "active")
                .limit(2000)
                .execute()
                .data
                or []
            )
            for r in positions:
                pid = r.get("id")
                contract = r.get("token_contract")
                chain = r.get("token_chain")
                features = r.get("features") or {}
                geometry = (features.get("geometry") if isinstance(features, dict) else None) or {}
                if not geometry:
                    continue
                # latest 15m OHLC bar (for diagonal breakout logic)
                bar = (
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
                )
                if not bar:
                    continue
                bar_ts = datetime.fromisoformat((bar[0]["timestamp"]).replace("Z", "+00:00"))
                close = float(bar[0]["close_native"]) if bar[0].get("close_native") is not None else 0.0
                # nearest horizontal level
                levels = geometry.get("levels") or {}
                sr_levels = levels.get("sr_levels") or []
                
                # Split S/R levels based on current price position
                supports = []
                resistances = []
                for level in sr_levels:
                    level_price = float(level.get("price", 0.0))
                    if close > level_price:
                        supports.append(level)  # Above price = support
                    else:
                        resistances.append(level)  # Below price = resistance
                
                # Find closest S/R levels
                closest_support = None
                closest_resistance = None
                if supports:
                    closest_support = min(supports, key=lambda x: abs(close - float(x.get("price", 0.0))))
                if resistances:
                    closest_resistance = min(resistances, key=lambda x: abs(close - float(x.get("price", 0.0))))
                
                # Build S/R levels output
                sr_levels_output = {}
                if closest_support:
                    sr_levels_output["closest_support"] = {
                        "price": float(closest_support.get("price", 0.0)),
                        "strength": float(closest_support.get("strength", 1))
                    }
                if closest_resistance:
                    sr_levels_output["closest_resistance"] = {
                        "price": float(closest_resistance.get("price", 0.0)),
                        "strength": float(closest_resistance.get("strength", 1))
                    }
                
                candidates = supports + resistances
                sr_break = "none"
                sr_strength = 0.0
                if candidates:
                    nearest = min(candidates, key=lambda x: abs(close - float(x.get("price", 0.0))))
                    price_lvl = float(nearest.get("price", 0.0))
                    eps = max(1e-6, 0.002 * close)
                    if close > price_lvl + eps:
                        sr_break = "bull"
                        sr_strength = 0.5 + 0.05 * float(nearest.get("strength", 1))
                    elif close < price_lvl - eps:
                        sr_break = "bear"
                        sr_strength = 0.5 + 0.05 * float(nearest.get("strength", 1))
                # diagonals: project each existing line to now using stored anchor
                diag_break = "none"
                diag_strength = 0.0
                diags = geometry.get("diagonals") or {}
                existing_status = (geometry.get("diag_status") or {}) if isinstance(geometry, dict) else {}
                
                # Seed trends from geometry BEFORE using them
                current_trend = geometry.get("current_trend", {})
                geometry_trend = current_trend.get("trend_type")
                tracker_trend = geometry_trend
                tracker_trend_changed = False
                tracker_trend_change_time = None

                # Calculate diagonal levels by projecting stored lines
                diag_levels_output = {}

                def _project(diag: dict) -> float | None:
                    try:
                        slope = float(diag.get("slope", 0.0))
                        intercept = float(diag.get("intercept", 0.0))
                        anchor_time = diag.get("anchor_time_iso")
                        if not anchor_time:
                            return None
                        t0 = datetime.fromisoformat(str(anchor_time).replace("Z", "+00:00"))
                        hours_since_anchor = (now - t0).total_seconds() / 3600
                        return slope * hours_since_anchor + intercept
                    except Exception:
                        return None

                def _pick(lines: list[tuple[str, dict]]) -> tuple[str, dict] | None:
                    if not lines:
                        return None
                    return max(lines, key=lambda x: (float(x[1].get("confidence", 0.0)), float(x[1].get("r2_score", 0.0))))

                swing_low_lines = [(k, v) for k, v in diags.items() if "lows" in k]
                swing_high_lines = [(k, v) for k, v in diags.items() if "highs" in k]

                if tracker_trend == "uptrend":
                    best_low = _pick([kv for kv in swing_low_lines if "uptrend" in kv[0]])
                    best_high = _pick([kv for kv in swing_high_lines if "uptrend" in kv[0]])
                    if best_low:
                        px = _project(best_low[1])
                        if px is not None:
                            diag_levels_output["diag_support"] = {"price": px, "strength": float(best_low[1].get("confidence", 1.0))}
                    if best_high:
                        px = _project(best_high[1])
                        if px is not None:
                            diag_levels_output["diag_resistance"] = {"price": px, "strength": float(best_high[1].get("confidence", 1.0))}
                elif tracker_trend == "downtrend":
                    best_high = _pick([kv for kv in swing_high_lines if "downtrend" in kv[0]])
                    if best_high:
                        px = _project(best_high[1])
                        if px is not None:
                            diag_levels_output["diag_resistance"] = {"price": px, "strength": float(best_high[1].get("confidence", 1.0))}
                    best_low = _pick([kv for kv in swing_low_lines if "downtrend" in kv[0]])
                    if best_low:
                        px = _project(best_low[1])
                        if px is not None:
                            diag_levels_output.setdefault("diag_support", {"price": px, "strength": float(best_low[1].get("confidence", 1.0))})

                cfg = load_pm_config()
                geom_cfg = (cfg.get("geom") or {})
                tol = float(geom_cfg.get("break_tol_pct", 0.0075))  # default 0.75%
                retr_min = float(geom_cfg.get("retrace_min", 0.68))
                retr_max = float(geom_cfg.get("retrace_max", 1.00))

                def process_line(line_key: str, line: dict, prev: dict) -> dict:
                    anchor_iso = line.get("anchor_time_iso")
                    if not anchor_iso:
                        return prev or {}
                    try:
                        t0 = datetime.fromisoformat(anchor_iso.replace("Z", "+00:00"))
                    except Exception:
                        return prev or {}
                    m = float(line.get("slope", 0.0))
                    b = float(line.get("intercept", 0.0))
                    hours_since = max(0.0, (bar_ts - t0).total_seconds() / 3600.0)
                    projected = m * hours_since + b
                    status = prev.copy() if isinstance(prev, dict) else {}
                    # Initialize
                    state = (status.get("state") or "none").lower()
                    direction = (status.get("direction") or "").lower()
                    line_at_breakout = float(status.get("line_at_breakout_native") or 0.0)
                    breakout_top = status.get("breakout_top_native")

                    # Determine above/below now
                    status["projected_price_native"] = projected
                    status["distance_pct"] = (close - projected) / projected if projected else 0.0
                    status["above_below"] = "above" if close > projected else "below"
                    status["last_checked_ts"] = now.isoformat()

                    # State machine using 15m close
                    if state == "none":
                        if close > projected * (1.0 + tol):
                            status.update({
                                "state": "breakout",
                                "direction": "bull",
                                "breakout_close_ts": bar_ts.isoformat(),
                                "line_at_breakout_native": projected,
                                "breakout_close_price_native": close,
                                "breakout_top_native": close,
                            })
                        elif close < projected * (1.0 - tol):
                            status.update({
                                "state": "breakout",
                                "direction": "bear",
                                "breakout_close_ts": bar_ts.isoformat(),
                                "line_at_breakout_native": projected,
                                "breakout_close_price_native": close,
                                "breakout_top_native": close,
                            })
                    elif state == "breakout":
                        # Update top/bottom
                        if (status.get("direction") == "bull"):
                            new_top = max(float(breakout_top or close), close)
                            status["breakout_top_native"] = new_top
                            move = new_top - float(status.get("line_at_breakout_native") or projected)
                            if move > 0:
                                low = new_top - retr_max * move
                                high = new_top - retr_min * move
                                status["retrace_zone_low_native"] = low
                                status["retrace_zone_high_native"] = high
                                if close <= high:
                                    status["state"] = "retrace_ready"
                        else:  # bear
                            new_bot = min(float(breakout_top or close), close)
                            status["breakout_top_native"] = new_bot
                            move = float(status.get("line_at_breakout_native") or projected) - new_bot
                            if move > 0:
                                high = new_bot + retr_max * move
                                low = new_bot + retr_min * move
                                status["retrace_zone_low_native"] = low
                                status["retrace_zone_high_native"] = high
                                if close >= low:
                                    status["state"] = "retrace_ready"

                    return status

                # Evaluate all diagonal lines; keep keys unchanged
                diag_status: dict = {}
                for k, v in diags.items():
                    if not isinstance(v, dict):
                        continue
                    if "slope" not in v or "intercept" not in v:
                        continue
                    prev = existing_status.get(k) if isinstance(existing_status, dict) else {}
                    diag_status[k] = process_line(k, v, prev)
                
                # Calculate diagonal strength (time-based)
                if diags:
                    # Get the oldest diagonal line to calculate trend start time
                    oldest_anchor = None
                    for line in diags.values():
                        if isinstance(line, dict) and line.get("anchor_time_iso"):
                            try:
                                anchor_time = datetime.fromisoformat(line["anchor_time_iso"].replace("Z", "+00:00"))
                                if oldest_anchor is None or anchor_time < oldest_anchor:
                                    oldest_anchor = anchor_time
                            except Exception:
                                continue
                    
                    if oldest_anchor:
                        hours_since_trend_start = (bar_ts - oldest_anchor).total_seconds() / 3600.0
                        diag_strength = 0.1 * hours_since_trend_start
                
                # Trend change detection logic
                if tracker_trend:
                    # Check for trend changes based on diagonal breaks
                    if tracker_trend == "downtrend":
                        # In downtrend: look for break above Swing High line
                        swing_high_breaks = []
                        for k, status in diag_status.items():
                            if "highs" in k and status.get("above_below") == "above":
                                swing_high_breaks.append(k)
                        
                        if swing_high_breaks:
                            # Break above Swing High in downtrend = trend change to uptrend
                            tracker_trend = "uptrend"
                            tracker_trend_changed = True
                            tracker_trend_change_time = now.isoformat()
                            diag_break = "bull"
                    
                    elif tracker_trend == "uptrend":
                        # In uptrend: look for break below Swing Low line
                        swing_low_breaks = []
                        for k, status in diag_status.items():
                            if "lows" in k and status.get("above_below") == "below":
                                swing_low_breaks.append(k)
                        
                        if swing_low_breaks:
                            # Break below Swing Low in uptrend = trend change to downtrend
                            tracker_trend = "downtrend"
                            tracker_trend_changed = True
                            tracker_trend_change_time = now.isoformat()
                            diag_break = "bear"

                updates = {
                    "sr_break": sr_break,
                    "sr_strength": sr_strength,
                    "diag_break": diag_break,
                    "diag_strength": diag_strength,
                    "diag_status": diag_status,
                    "geometry_trend": geometry_trend,
                    "tracker_trend": tracker_trend,
                    "tracker_trend_changed": tracker_trend_changed,
                    "tracker_trend_change_time": tracker_trend_change_time,
                    "sr_levels": sr_levels_output,
                    "diag_levels": diag_levels_output,
                    "tracked_at": now.isoformat(),
                }
                sp.write_features_token_geometry(pid, updates)
        except Exception as e:
            logging.getLogger(__name__).exception("geometry tracker failed: %s", e)


if __name__ == "__main__":
    main()


