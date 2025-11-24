"""
Helper functions for PM: bucketing and outcome classification.

These functions are used to:
1. Bucket continuous values into discrete categories for pattern matching
2. Classify trade outcomes for learning systems

Used by:
- actions.py: Building action context for pattern matching
- pm_core_tick.py: Building action context for learning strands
"""

from typing import Dict, Any, Optional


# ============================================================================
# Bucketing Functions
# ============================================================================

def bucket_a_e(score: float) -> str:
    """Bucket A/E score into low/med/high.
    
    Args:
        score: A or E score (0-1)
    
    Returns:
        'low', 'med', or 'high'
    """
    if score < 0.3:
        return "low"
    elif score < 0.7:
        return "med"
    else:
        return "high"


def bucket_score(score: float) -> str:
    """Bucket engine score (TS/DX/OX/EDX) into low/med/high.
    
    Args:
        score: Engine score (0-1)
    
    Returns:
        'low', 'med', or 'high'
    """
    if score < 0.3:
        return "low"
    elif score < 0.7:
        return "med"
    else:
        return "high"


def bucket_ema_slopes(slopes: Dict[str, float]) -> str:
    """Bucket EMA slopes into negative/flat/positive.
    
    Uses average of all slopes, or checks if majority are positive/negative.
    
    Args:
        slopes: Dict with ema60_slope, ema144_slope, ema250_slope, ema333_slope
    
    Returns:
        'negative', 'flat', or 'positive'
    """
    if not slopes:
        return "flat"
    
    # Use key slopes (60, 144, 250, 333) if available
    key_slopes = []
    for key in ["ema60_slope", "ema144_slope", "ema250_slope", "ema333_slope"]:
        if key in slopes:
            key_slopes.append(slopes[key])
    
    if not key_slopes:
        return "flat"
    
    avg_slope = sum(key_slopes) / len(key_slopes)
    
    if avg_slope < -0.001:
        return "negative"
    elif avg_slope > 0.001:
        return "positive"
    else:
        return "flat"


def bucket_size(size_frac: float) -> str:
    """Bucket action size into small/med/large.
    
    Args:
        size_frac: Size fraction (0-1)
    
    Returns:
        'small', 'med', or 'large'
    """
    if size_frac < 0.2:
        return "small"
    elif size_frac < 0.5:
        return "med"
    else:
        return "large"


def bucket_bars_since_entry(bars: int) -> str:
    """Bucket bars since entry into timing buckets.
    
    Args:
        bars: Number of bars since entry
    
    Returns:
        '0', '1-5', '6-20', or '21+'
    """
    if bars == 0:
        return "0"
    elif bars <= 5:
        return "1-5"
    elif bars <= 20:
        return "6-20"
    else:
        return "21+"


# ============================================================================
# Outcome Classification
# ============================================================================

def classify_outcome(rr: float) -> str:
    """Classify trade outcome based on R/R.
    
    Args:
        rr: Risk/reward ratio
    
    Returns:
        'big_win', 'big_loss', 'small_win', 'small_loss', or 'breakeven'
    """
    if rr > 2.0:
        return "big_win"
    elif rr < -1.0:
        return "big_loss"
    elif rr > 0.5:
        return "small_win"
    elif rr < 0:
        return "small_loss"
    else:
        return "breakeven"


def classify_hold_time(hold_time_days: float) -> str:
    """Classify hold time into short/medium/long.
    
    Args:
        hold_time_days: Hold time in days
    
    Returns:
        'short', 'medium', or 'long'
    """
    if hold_time_days < 7:
        return "short"
    elif hold_time_days <= 30:
        return "medium"
    else:
        return "long"

