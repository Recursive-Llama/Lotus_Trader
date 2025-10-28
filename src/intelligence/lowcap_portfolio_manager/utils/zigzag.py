from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def detect_swings(
    closes: List[float],
    atr: List[float],
    highs: Optional[List[float]] = None,
    lows: Optional[List[float]] = None,
    lambda_mult: float = 1.2,
    backstep: int = 3,
    min_leg_bars: int = 4,
    illiquid_guard_ratio: float = 0.003,
    wick_relaxer_atr: float = 0.25,
) -> Dict[str, Any]:
    """ATR-adaptive ZigZag swing detection.

    - Threshold per leg: λ = lambda_mult × ATR at pivot start
    - backstep: pivot must hold for N bars without being exceeded
    - min_leg_bars: ignore legs shorter than N bars
    - wick_relaxer: if highs/lows provided, allow pivot if intrabar extreme exceeds λ by ≥ wick_relaxer_atr × ATR
    - illiquid guard: if mean(ATR/close) < illiquid_guard_ratio, bump lambda by +0.2

    Returns a dict with pivots and leg stats suitable for S3 continuation quality.
    """
    n = len(closes)
    if n == 0 or len(atr) != n:
        return {"pivots": [], "up_legs": [], "down_legs": []}

    # Illiquid guard
    import statistics

    ratio_vals: List[float] = []
    for i in range(n):
        c = closes[i]
        a = atr[i]
        if c > 0:
            ratio_vals.append(a / c)
    eff_lambda = lambda_mult
    if ratio_vals and statistics.fmean(ratio_vals) < illiquid_guard_ratio:
        eff_lambda += 0.2

    pivots: List[Tuple[int, str]] = []  # (index, 'H'|'L')

    # Initialize with first point as tentative pivot
    last_pivot_idx = 0
    last_pivot_price = closes[0]
    direction: Optional[str] = None  # 'up' or 'down'

    def crossed_threshold(curr_price: float, base_price: float, base_atr: float, want_up: bool) -> bool:
        thresh = eff_lambda * base_atr
        if want_up:
            return (curr_price - base_price) >= thresh
        return (base_price - curr_price) >= thresh

    # Track local extremes for backstep validation
    local_high_idx = 0
    local_low_idx = 0
    local_high = closes[0]
    local_low = closes[0]

    for i in range(1, n):
        px = closes[i]
        if px > local_high:
            local_high = px
            local_high_idx = i
        if px < local_low:
            local_low = px
            local_low_idx = i

        # If direction not set, wait until a threshold move defines first leg
        if direction is None:
            base_atr = atr[last_pivot_idx]
            if crossed_threshold(px, last_pivot_price, base_atr, want_up=True):
                direction = 'up'
                # set a local low pivot at last_pivot_idx
                pivots.append((last_pivot_idx, 'L'))
            elif crossed_threshold(px, last_pivot_price, base_atr, want_up=False):
                direction = 'down'
                pivots.append((last_pivot_idx, 'H'))
            continue

        # Direction is set: watch for reversal beyond ATR threshold from current local extreme
        if direction == 'up':
            # Potential high pivot at local_high_idx if we reverse down enough
            base_atr = atr[local_high_idx]
            want_down = crossed_threshold(px, local_high, base_atr, want_up=False)
            # wick relaxer using lows if provided
            relaxed = False
            if lows is not None and highs is not None:
                # Use current low vs local_high as proxy of reversal distance with wick bump
                low_now = lows[i]
                relaxed = (local_high - low_now) >= (eff_lambda * base_atr - wick_relaxer_atr * base_atr)
            if want_down or relaxed:
                # backstep validation: require that local high held backstep bars ago
                if i - local_high_idx >= max(1, backstep):
                    # Ensure min leg length
                    if not pivots or (local_high_idx - pivots[-1][0]) >= min_leg_bars:
                        pivots.append((local_high_idx, 'H'))
                        # reset tracking for next leg
                        last_pivot_idx = local_high_idx
                        last_pivot_price = closes[last_pivot_idx]
                        direction = 'down'
                        local_low = px
                        local_low_idx = i
        else:  # direction == 'down'
            base_atr = atr[local_low_idx]
            want_up = crossed_threshold(px, local_low, base_atr, want_up=True)
            relaxed = False
            if lows is not None and highs is not None:
                high_now = highs[i]
                relaxed = (high_now - local_low) >= (eff_lambda * base_atr - wick_relaxer_atr * base_atr)
            if want_up or relaxed:
                if i - local_low_idx >= max(1, backstep):
                    if not pivots or (local_low_idx - pivots[-1][0]) >= min_leg_bars:
                        pivots.append((local_low_idx, 'L'))
                        last_pivot_idx = local_low_idx
                        last_pivot_price = closes[last_pivot_idx]
                        direction = 'up'
                        local_high = px
                        local_high_idx = i

    # Ensure last extreme is captured if missing long tail
    if direction == 'up' and (not pivots or pivots[-1][1] != 'H'):
        if n - 1 - local_high_idx >= backstep and (not pivots or (local_high_idx - pivots[-1][0]) >= min_leg_bars):
            pivots.append((local_high_idx, 'H'))
    if direction == 'down' and (not pivots or pivots[-1][1] != 'L'):
        if n - 1 - local_low_idx >= backstep and (not pivots or (local_low_idx - pivots[-1][0]) >= min_leg_bars):
            pivots.append((local_low_idx, 'L'))

    # Build legs and metrics
    up_legs: List[Dict[str, Any]] = []
    down_legs: List[Dict[str, Any]] = []
    def leg_amplitude_atr(i0: int, i1: int) -> float:
        if i0 < 0 or i0 >= n or i1 < 0 or i1 >= n:
            return 0.0
        num = abs(closes[i1] - closes[i0])
        den = atr[i0] if atr[i0] > 0 else 1.0
        return num / den

    for k in range(1, len(pivots)):
        i_prev, type_prev = pivots[k - 1]
        i_curr, type_curr = pivots[k]
        duration = max(0, i_curr - i_prev)
        amp = leg_amplitude_atr(i_prev, i_curr)
        entry = {"start": i_prev, "end": i_curr, "amplitude_atr": amp, "duration_bars": duration}
        if type_prev == 'L' and type_curr == 'H':
            up_legs.append(entry)
        elif type_prev == 'H' and type_curr == 'L':
            down_legs.append(entry)

    return {"pivots": pivots, "up_legs": up_legs, "down_legs": down_legs}


