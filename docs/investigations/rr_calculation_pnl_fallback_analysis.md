# R/R Calculation - PnL-Based Fallback Analysis

## Current R/R Calculation Requirements

### What Data Is Needed

**Location**: `_calculate_rr_metrics()` (lines 2073-2221)

**Required Data**:
1. **OHLC Bars**: At least 1 bar that overlaps with `[entry_timestamp, exit_timestamp]`
2. **Bar Fields**: `low_usd`, `high_usd` (from `lowcap_price_data_ohlc` table)
3. **Entry/Exit Prices**: `entry_price`, `exit_price` (from position data)

**Minimum Requirement**: 
- **At least 1 overlapping OHLC bar** (but more bars = more accurate)
- If no overlapping bars → returns `None` for all metrics

**Current Failure Handling** (line 2153-2163):
```python
if not ohlc_data:
    logger.warning(f"No OHLCV data found for R/R calculation...")
    return {
        "rr": None,
        "return": None,
        "max_drawdown": None,
        "max_gain": None
    }
```

---

## R/R Calculation Formula

### Current Formula (OHLC-Based)

```python
# 1. Find min_price (lowest low from OHLC bars during trade)
min_price = min(entry_price, all_bar_lows)

# 2. Calculate return percentage
return_pct = (exit_price - entry_price) / entry_price

# 3. Calculate max drawdown
max_drawdown = (entry_price - min_price) / entry_price

# 4. Calculate R/R ratio
rr = return_pct / max_drawdown  # (if max_drawdown > 0)
```

**Key Insight**: We need `min_price` (lowest price during trade) to calculate `max_drawdown`.

---

## PnL-Based Fallback Analysis

### Available PnL Data

From position table (before wipe):
- `total_allocation_usd` - Total USD invested
- `total_extracted_usd` - Total USD extracted
- `total_tokens_bought` - Total tokens bought
- `total_tokens_sold` - Total tokens sold
- `avg_entry_price` - Weighted average entry price
- `avg_exit_price` - Weighted average exit price
- `rpnl_usd` - Realized P&L
- `total_pnl_usd` - Total P&L

### What We CAN Calculate from PnL

✅ **Return Percentage**:
```python
return_pct = (total_extracted_usd - total_allocation_usd) / total_allocation_usd
# OR
return_pct = (avg_exit_price - avg_entry_price) / avg_entry_price
```

✅ **Max Gain** (if we had max_price):
```python
max_gain = (max_price - avg_entry_price) / avg_entry_price
# But we don't have max_price from PnL alone
```

❌ **Max Drawdown**:
```python
max_drawdown = (avg_entry_price - min_price) / avg_entry_price
# We DON'T have min_price from PnL alone
```

❌ **R/R Ratio**:
```python
rr = return_pct / max_drawdown
# Can't calculate without max_drawdown
```

---

## The Problem: Missing `min_price`

**Why We Need OHLC Data**:
- `min_price` = lowest price during the entire trade period
- This requires scanning all OHLC bars between entry and exit
- **PnL data doesn't track intra-trade price movements** - only entry/exit averages

**Example**:
- Entry: $1.00 (bought 100 tokens = $100)
- During trade: Price dropped to $0.50 (min_price)
- Exit: $1.20 (sold 100 tokens = $120)
- PnL: $20 profit (20% return)
- Max drawdown: (1.00 - 0.50) / 1.00 = 50%
- R/R: 20% / 50% = 0.4

**From PnL alone**, we only know:
- Entry: $1.00
- Exit: $1.20
- Return: 20%
- **But we don't know it dropped to $0.50** → can't calculate max_drawdown → can't calculate R/R

---

## Fallback Options

### Option 1: Conservative Estimate (Use Entry Price as Min)

**Assumption**: If we don't have OHLC data, assume no drawdown (min_price = entry_price).

```python
def _calculate_rr_from_pnl(
    total_allocation_usd: float,
    total_extracted_usd: float,
    avg_entry_price: float,
    avg_exit_price: float
) -> Dict[str, Any]:
    """Calculate R/R from PnL data when OHLC is unavailable."""
    
    if total_allocation_usd <= 0 or avg_entry_price <= 0:
        return {"rr": None, "return": None, "max_drawdown": None}
    
    # Calculate return
    return_pct = (total_extracted_usd - total_allocation_usd) / total_allocation_usd
    
    # Conservative assumption: no drawdown (min_price = entry_price)
    # This gives max_drawdown = 0, so R/R = infinity (perfect trade)
    # But we bound it to a reasonable value
    max_drawdown = 0.0
    
    # If return is positive, R/R is infinite (perfect trade)
    # If return is negative, we can't calculate R/R (division by zero)
    if return_pct > 0:
        # Perfect trade (no drawdown) - bound to max R/R
        rr = 33.0  # Use max bound as conservative estimate
    elif return_pct < 0:
        # Loss trade - can't calculate R/R without drawdown
        # Use conservative estimate: assume 10% drawdown
        max_drawdown = 0.10
        rr = return_pct / max_drawdown
    else:
        rr = 0.0
    
    return {
        "rr": max(-33.0, min(33.0, rr)),
        "return": return_pct,
        "max_drawdown": max_drawdown,
        "max_gain": (avg_exit_price - avg_entry_price) / avg_entry_price if avg_entry_price > 0 else None
    }
```

**Pros**:
- ✅ Always produces a value
- ✅ Simple to implement
- ✅ Conservative (assumes best case for wins, worst case for losses)

**Cons**:
- ❌ Inaccurate for trades with significant drawdown
- ❌ Overestimates R/R for winning trades
- ❌ Underestimates R/R for losing trades

---

### Option 2: Skip Trade If R/R Can't Be Calculated

**Current Behavior** (line 2396-2403):
```python
rr_value = rr_metrics.get("rr")
if rr_value is None:
    logger.warning(f"Could not calculate R/R for position {position_id}")
    rr = 0.0  # Defaults to neutral
```

**Alternative**: Skip the trade entirely if R/R can't be calculated.

```python
rr_value = rr_metrics.get("rr")
if rr_value is None:
    logger.error(
        f"Cannot close position {position_id}: R/R calculation failed. "
        f"OHLC data missing or corrupted. Skipping closure."
    )
    return False  # Don't close the trade
```

**Pros**:
- ✅ Prevents inaccurate data from entering learning system
- ✅ Forces investigation of data quality issues
- ✅ Cleaner learning data

**Cons**:
- ❌ Trade stays open indefinitely if OHLC data never arrives
- ❌ Could block learning system if many trades have missing data
- ❌ Need manual intervention to close stuck positions

---

### Option 3: Use Historical Average Drawdown

**Assumption**: Use average drawdown from similar trades as estimate.

```python
def _estimate_drawdown_from_history(
    token_contract: str,
    chain: str,
    timeframe: str,
    return_pct: float
) -> float:
    """Estimate max_drawdown from historical trades."""
    
    # Query recent completed trades for this token
    recent_trades = (
        self.sb.table("lowcap_positions")
        .select("completed_trades")
        .eq("token_contract", token_contract)
        .eq("token_chain", chain)
        .eq("timeframe", timeframe)
        .not_.is_("completed_trades", "null")
        .order("closed_at", desc=True)
        .limit(10)
        .execute()
    ).data
    
    # Extract max_drawdown from completed_trades
    drawdowns = []
    for pos in recent_trades:
        trades = pos.get("completed_trades", [])
        for trade in trades:
            summary = trade.get("summary", {})
            if summary.get("max_drawdown") is not None:
                drawdowns.append(summary["max_drawdown"])
    
    if drawdowns:
        avg_drawdown = sum(drawdowns) / len(drawdowns)
        return avg_drawdown
    else:
        # Default: 10% drawdown (conservative)
        return 0.10
```

**Pros**:
- ✅ More accurate than Option 1
- ✅ Uses actual historical data
- ✅ Adapts to token-specific volatility

**Cons**:
- ❌ Complex to implement
- ❌ Requires historical data (might not exist for new tokens)
- ❌ Still an estimate, not exact

---

### Option 4: Hybrid Approach (Recommended)

**Strategy**: Try OHLC first, fallback to PnL with conservative estimate, skip if both fail.

```python
def _calculate_rr_metrics_with_fallback(
    self,
    token_contract: str,
    chain: str,
    timeframe: str,
    entry_timestamp: datetime,
    exit_timestamp: datetime,
    entry_price: float,
    exit_price: float,
    # PnL fallback data
    total_allocation_usd: float = None,
    total_extracted_usd: float = None,
    avg_entry_price: float = None,
    avg_exit_price: float = None
) -> Dict[str, Any]:
    """Calculate R/R with PnL fallback if OHLC unavailable."""
    
    # Try OHLC-based calculation first
    rr_metrics = self._calculate_rr_metrics(
        token_contract, chain, timeframe,
        entry_timestamp, exit_timestamp,
        entry_price, exit_price
    )
    
    # If OHLC calculation succeeded, return it
    if rr_metrics.get("rr") is not None:
        return rr_metrics
    
    # OHLC failed - try PnL fallback
    logger.warning(
        f"OHLC-based R/R calculation failed for {token_contract}. "
        f"Using PnL-based fallback (less accurate)."
    )
    
    if total_allocation_usd and total_extracted_usd and avg_entry_price:
        return self._calculate_rr_from_pnl(
            total_allocation_usd, total_extracted_usd,
            avg_entry_price, avg_exit_price or exit_price
        )
    
    # Both failed - return None
    logger.error(
        f"Both OHLC and PnL R/R calculations failed for {token_contract}. "
        f"Cannot calculate R/R."
    )
    return {
        "rr": None,
        "return": None,
        "max_drawdown": None,
        "max_gain": None
    }
```

**Usage in `_close_trade_on_s0_transition()`**:
```python
# Calculate R/R with fallback
rr_metrics = self._calculate_rr_metrics_with_fallback(
    token_contract=token_contract,
    chain=chain,
    timeframe=timeframe,
    entry_timestamp=entry_timestamp,
    exit_timestamp=exit_timestamp,
    entry_price=entry_price,
    exit_price=exit_price,
    # PnL fallback data
    total_allocation_usd=total_allocation_usd,
    total_extracted_usd=total_extracted_usd,
    avg_entry_price=avg_entry_price_final,
    avg_exit_price=avg_exit_price_final
)

# If R/R still can't be calculated, decide what to do
rr_value = rr_metrics.get("rr")
if rr_value is None:
    # Option A: Skip trade (most accurate)
    logger.error(f"Cannot close position {position_id}: R/R calculation failed")
    return False
    
    # Option B: Use neutral value (current behavior)
    # rr = 0.0
```

---

## Recommendation

### Best Approach: **Option 4 (Hybrid) with Skip on Failure**

1. **Try OHLC first** (most accurate)
2. **Fallback to PnL** (conservative estimate) if OHLC unavailable
3. **Skip trade** if both fail (prevents bad data)

**Rationale**:
- ✅ Captures most trades accurately (OHLC available)
- ✅ Handles edge cases gracefully (PnL fallback)
- ✅ Prevents bad data from entering learning system (skip on failure)
- ✅ Forces investigation of data quality issues

**Implementation**:
- Add `_calculate_rr_from_pnl()` method
- Modify `_calculate_rr_metrics()` to accept PnL fallback params
- Update `_close_trade_on_s0_transition()` to use hybrid approach
- Change default from `rr = 0.0` to `return False` (skip trade)

---

## Data Requirements Summary

| Data Source | Min Bars Needed | Accuracy | Availability |
|------------|----------------|----------|--------------|
| **OHLC** | 1+ overlapping bars | High | Usually available |
| **PnL** | None (already calculated) | Low (no drawdown) | Always available |
| **Hybrid** | 1+ bars OR PnL | Medium-High | Always available |

**Conclusion**: PnL-based fallback works but is less accurate. Hybrid approach is best.

