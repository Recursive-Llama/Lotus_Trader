"""
Shared TA calculation utilities.

Used by both ta_tracker.py (production) and backtesters to ensure identical calculations.
This prevents drift between production and backtesting.

All functions are deterministic and pure (no side effects).
"""

from __future__ import annotations

from typing import Any, Dict, List


def ema_series(vals: List[float], span: int) -> List[float]:
    """
    Compute EMA series from price values.
    
    Initializes with first value (not SMA), matching ta_tracker behavior.
    
    Args:
        vals: List of price values (typically closes)
        span: EMA period
        
    Returns:
        List of EMA values (same length as input)
    """
    if not vals:
        return []
    alpha = 2.0 / (span + 1)
    out = [vals[0]]  # Initialize with first value (not SMA)
    for v in vals[1:]:
        out.append(alpha * v + (1 - alpha) * out[-1])
    return out


def lin_slope(vals: List[float], win: int) -> float:
    """
    Compute linear regression slope over a window.
    
    Uses least squares regression on the last `win` values.
    
    Args:
        vals: List of values
        win: Window size for regression
        
    Returns:
        Raw slope (price change per bar)
    """
    n = min(win, len(vals))
    if n < 3:
        return 0.0
    xs = list(range(n))
    ys = vals[-n:]
    xbar = sum(xs) / n
    ybar = sum(ys) / n
    num = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys))
    den = sum((x - xbar) ** 2 for x in xs) or 1.0
    return num / den


def ema_slope_normalized(ema_series: List[float], window: int = 10) -> float:
    """
    Compute normalized EMA slope as %/bar.
    
    This is the standard slope calculation used by ta_tracker:
    - Raw slope from linear regression over `window` bars
    - Normalized by dividing by latest EMA value
    - Returns % change per bar (e.g., 0.001 = 0.1% per bar)
    
    Args:
        ema_series: List of EMA values
        window: Regression window size (default 10)
        
    Returns:
        Normalized slope as %/bar (e.g., 0.00316 = 0.316% per bar)
    """
    if not ema_series or len(ema_series) < window:
        return 0.0
    if len(ema_series) < 3:  # Need at least 3 points for regression
        return 0.0
    
    latest_ema = ema_series[-1]
    if latest_ema <= 0.0:
        return 0.0
    
    raw_slope = lin_slope(ema_series, window)
    return raw_slope / max(latest_ema, 1e-9)


def ema_slope_delta(ema_series: List[float], window: int = 10, lag: int = 10) -> float:
    """
    Compute slope acceleration (delta between recent and past slope).
    
    Used for d_ema*_slope calculations (acceleration/deceleration).
    
    Args:
        ema_series: List of EMA values
        window: Regression window size
        lag: How far back to compare (default 10)
        
    Returns:
        Slope delta (recent_slope - past_slope) as %/bar
    """
    if len(ema_series) < window + lag:
        return 0.0
    
    latest_ema = ema_series[-1]
    if latest_ema <= 0.0:
        return 0.0
    
    # Recent slope (last window bars)
    recent_slope = lin_slope(ema_series, window) / max(latest_ema, 1e-9)
    
    # Past slope (window bars ending at lag)
    if len(ema_series) >= lag + window:
        past_series = ema_series[:-(lag)]  # Remove last lag bars
        past_ema = past_series[-1] if past_series else latest_ema
        past_slope = lin_slope(past_series, window) / max(past_ema, 1e-9)
    else:
        past_slope = 0.0
    
    return recent_slope - past_slope


def rsi(values: List[float], period: int = 14) -> float:
    """
    Compute RSI (Relative Strength Index).
    
    Args:
        values: List of price values
        period: RSI period (default 14)
        
    Returns:
        RSI value (0-100)
    """
    if len(values) <= period:
        return 50.0
    gains: List[float] = []
    losses: List[float] = []
    for i in range(len(values) - period, len(values)):
        ch = values[i] - values[i - 1]
        gains.append(max(0.0, ch))
        losses.append(max(0.0, -ch))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period or 1e-9
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def zscore(window: List[float], value: float) -> float:
    """
    Compute z-score of a value relative to a window.
    
    Args:
        window: List of values for mean/std calculation
        value: Value to compute z-score for
        
    Returns:
        Z-score (how many standard deviations from mean)
    """
    if not window:
        return 0.0
    mean = sum(window) / len(window)
    if len(window) < 2:
        return 0.0
    variance = sum((x - mean) ** 2 for x in window) / len(window)
    std = variance ** 0.5
    if std == 0.0:
        return 0.0
    return (value - mean) / std


def wilder_ema(prev: float, new: float, period: int) -> float:
    """
    Wilder's smoothing (EMA variant).
    
    Args:
        prev: Previous smoothed value
        new: New raw value
        period: Smoothing period
        
    Returns:
        New smoothed value
    """
    return ((period - 1) * prev + new) / period


def atr_wilder(bars: List[Dict[str, Any]], period: int = 14) -> float:
    """
    Compute ATR (Average True Range) using Wilder's smoothing.
    
    Args:
        bars: List of bar dicts with 'h', 'l', 'c' keys
        period: ATR period (default 14)
        
    Returns:
        ATR value
    """
    if len(bars) < 2:
        return 0.0
    
    trs: List[float] = []
    for i in range(1, len(bars)):
        h = float(bars[i].get("h", bars[i].get("high_native", 0.0)))
        l = float(bars[i].get("l", bars[i].get("low_native", 0.0)))
        prev_c = float(bars[i - 1].get("c", bars[i - 1].get("close_native", 0.0)))
        tr = max(h - l, abs(h - prev_c), abs(prev_c - l))
        trs.append(tr)
    
    if not trs:
        return 0.0
    
    atr = sum(trs[:period]) / min(period, len(trs))
    for tr in trs[period:]:
        atr = wilder_ema(atr, tr, period)
    
    return atr


def atr_series_wilder(bars: List[Dict[str, Any]], period: int = 14) -> List[float]:
    """
    Compute ATR series using Wilder's smoothing.
    
    Matches ta_tracker.py implementation exactly.
    
    Args:
        bars: List of bar dicts with 'h', 'l', 'c' keys (or 'high_native', 'low_native', 'close_native')
        period: ATR period (default 14)
        
    Returns:
        List of ATR values (same length as input bars)
    """
    if len(bars) < 2:
        return []
    
    trs: List[float] = []
    prev_c = float(bars[0].get("c", bars[0].get("close_native", 0.0)))
    for b in bars[1:]:
        h = float(b.get("h", b.get("high_native", 0.0)))
        l = float(b.get("l", b.get("low_native", 0.0)))
        tr = max(h - l, abs(h - prev_c), abs(prev_c - l))
        trs.append(tr)
        prev_c = float(b.get("c", b.get("close_native", 0.0)))
    
    if not trs:
        return []
    
    atrs: List[float] = []
    atr = sum(trs[:period]) / max(1, min(period, len(trs)))
    atrs.append(atr)
    
    for tr in trs[period:]:
        atr = wilder_ema(atr, tr, period)
        atrs.append(atr)
    
    # Align to closes length (matches ta_tracker padding)
    pad = len(bars) - 1 - len(atrs)
    if pad > 0:
        atrs = [atrs[0]] * pad + atrs
    return [atrs[0]] + atrs


def adx_series_wilder(bars: List[Dict[str, Any]], period: int = 14) -> List[float]:
    """
    Compute ADX (Average Directional Index) series using Wilder's smoothing.
    
    Matches ta_tracker.py implementation exactly.
    
    Args:
        bars: List of bar dicts with 'h', 'l', 'c' keys (or 'high_native', 'low_native', 'close_native')
        period: ADX period (default 14)
        
    Returns:
        List of ADX values
    """
    n = len(bars)
    if n < period + 2:
        return []
    
    trs: List[float] = []
    plus_dm: List[float] = []
    minus_dm: List[float] = []
    
    for i in range(1, n):
        # Handle both 'h'/'l'/'c' and 'high_native'/'low_native'/'close_native' formats
        h_curr = float(bars[i].get("h", bars[i].get("high_native", 0.0)))
        h_prev = float(bars[i - 1].get("h", bars[i - 1].get("high_native", 0.0)))
        l_curr = float(bars[i].get("l", bars[i].get("low_native", 0.0)))
        l_prev = float(bars[i - 1].get("l", bars[i - 1].get("low_native", 0.0)))
        c_prev = float(bars[i - 1].get("c", bars[i - 1].get("close_native", 0.0)))
        
        up_move = h_curr - h_prev
        down_move = l_prev - l_curr
        plus_dm.append(up_move if (up_move > down_move and up_move > 0) else 0.0)
        minus_dm.append(down_move if (down_move > up_move and down_move > 0) else 0.0)
        tr = max(
            h_curr - l_curr,
            abs(h_curr - c_prev),
            abs(c_prev - l_curr),
        )
        trs.append(tr)
    
    # Wilder smoothing iteratively to build ADX series (matches ta_tracker exactly)
    atr = sum(trs[:period]) / period
    pdm = sum(plus_dm[:period]) / period
    mdm = sum(minus_dm[:period]) / period
    pdi = 100.0 * (pdm / max(atr, 1e-9))
    mdi = 100.0 * (mdm / max(atr, 1e-9))
    dx_vals: List[float] = [100.0 * (abs(pdi - mdi) / max(pdi + mdi, 1e-9))]
    adx_vals: List[float] = []
    
    # Seed ADX (ta_tracker uses first DX value as seed)
    seed = dx_vals[0] if dx_vals else 0.0
    adx_vals.append(seed)
    
    for i in range(period, len(trs)):
        atr = wilder_ema(atr, trs[i], period)
        pdm = wilder_ema(pdm, plus_dm[i], period)
        mdm = wilder_ema(mdm, minus_dm[i], period)
        pdi = 100.0 * (pdm / max(atr, 1e-9))
        mdi = 100.0 * (mdm / max(atr, 1e-9))
        dx = 100.0 * (abs(pdi - mdi) / max(pdi + mdi, 1e-9))
        prev_adx = adx_vals[-1] if adx_vals else seed
        adx_vals.append(wilder_ema(prev_adx, dx, period))
    
    # Align length to bars (matches ta_tracker padding)
    pad = len(bars) - len(adx_vals)
    if pad > 0:
        adx_vals = [adx_vals[0]] * pad + adx_vals
    
    return adx_vals

