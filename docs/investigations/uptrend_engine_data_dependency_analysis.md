# Uptrend Engine Data Dependency Analysis

**Date**: 2025-12-05  
**Question**: If TA Tracker doesn't run, does Uptrend Engine see new candles?

---

## Current Schedule (1m Timeframe)

```
Every 60 seconds:
- TA Tracker 1m (line 697)
- Uptrend Engine 1m (line 706)
- PM Core Tick 1m (line 708)

Hourly at :07:
- Geometry Builder 1m
```

**Note**: TA Tracker and Uptrend Engine run at the **same frequency** (every 60 seconds), but they're **separate scheduled tasks** - not guaranteed to run in order.

---

## How Uptrend Engine Gets Data

### 1. Price Data

**Line 1291**: `last = self._latest_close_1h(contract, chain)`

**Implementation** (lines 224-245):
```python
def _latest_close_1h(self, contract: str, chain: str) -> Dict[str, Any]:
    """Get latest close price (bar close for deterministic checks) - timeframe-specific."""
    row = (
        self.sb.table("lowcap_price_data_ohlc")
        .select("timestamp, close_usd, low_usd")
        .eq("token_contract", contract)
        .eq("chain", chain)
        .eq("timeframe", self.timeframe)
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
```

**Source**: **Directly from database** (`lowcap_price_data_ohlc` table)

**Result**: ✅ **Uptrend Engine sees new candles even if TA Tracker doesn't run**

### 2. EMA Data

**Line 1285**: `ta = self._read_ta(features)`

**Line 1289**: `ema_vals = self._get_ema_values(ta)`

**Implementation** (lines 199-210):
```python
def _get_ema_values(self, ta: Dict[str, Any]) -> Dict[str, float]:
    """Extract EMA values from TA block (timeframe-specific)."""
    ema = ta.get("ema") or {}
    suffix = self.ta_suffix
    return {
        "ema20": float(ema.get(f"ema20{suffix}") or 0.0),
        "ema30": float(ema.get(f"ema30{suffix}") or 0.0),
        "ema60": float(ema.get(f"ema60{suffix}") or 0.0),
        "ema144": float(ema.get(f"ema144{suffix}") or 0.0),
        "ema250": float(ema.get(f"ema250{suffix}") or 0.0),
        "ema333": float(ema.get(f"ema333{suffix}") or 0.0),
    }
```

**Source**: **From `features.ta`** (written by TA Tracker)

**Result**: ❌ **Uptrend Engine uses STALE EMAs if TA Tracker doesn't run**

---

## The Problem: Data Mismatch

### Scenario: TA Tracker Fails/Delayed

**What happens**:
1. New candle closes (e.g., 10:01:00)
2. TA Tracker fails to run (or delayed)
3. Uptrend Engine runs at 10:01:00
4. **Price**: Fetches new price from database (10:01:00 candle) ✅
5. **EMAs**: Reads old EMAs from `features.ta` (computed from 10:00:00 candle) ❌

**Result**: **Data mismatch** - new price compared to old EMAs

### Impact

**State machine logic** (lines 1310-1358):
- Compares **new price** to **old EMAs**
- Could cause **incorrect state transitions**
- Example:
  - Old EMAs: `ema20=0.001, ema60=0.0011` (from 1 minute ago)
  - New price: `0.0012` (current)
  - State check: `price > ema20` and `price > ema60` → **S3** ✅ (correct by luck)
  - But if price dropped: `0.0009` → **S0** ❌ (wrong - EMAs haven't updated yet)

**Emergency exit logic** (line 1686):
- Checks `price < ema333_val`
- If EMAs are stale, could trigger false emergency exits

---

## Current Behavior: Race Condition Risk

### If TA Tracker Runs Before Uptrend Engine

✅ **Correct**: 
- TA Tracker updates `features.ta` with new EMAs
- Uptrend Engine reads fresh EMAs
- Price and EMAs are from same candle

### If Uptrend Engine Runs Before TA Tracker

❌ **Problem**:
- Uptrend Engine reads old EMAs from `features.ta`
- Fetches new price from database
- **Mismatch**: New price vs. old EMAs

### If TA Tracker Fails/Skips

❌ **Problem**:
- Uptrend Engine keeps running
- Uses increasingly stale EMAs
- Compares new prices to old EMAs
- **State transitions become incorrect**

---

## Solutions

### Option 1: Uptrend Engine Computes EMAs Itself (Recommended)

**Pros**:
- ✅ No dependency on TA Tracker
- ✅ Always uses fresh EMAs
- ✅ Price and EMAs always from same data

**Cons**:
- ⚠️ Duplicate computation (TA Tracker also computes EMAs)
- ⚠️ More code in Uptrend Engine

**Implementation**:
```python
# In Uptrend Engine, fetch recent bars and compute EMAs
bars = self._fetch_recent_ohlc(contract, chain, limit=400)
closes = [b["close_usd"] for b in bars]
ema20 = ema_series(closes, 20)[-1]
ema30 = ema_series(closes, 30)[-1]
# ... etc
```

### Option 2: Ensure TA Tracker Runs Before Uptrend Engine

**Pros**:
- ✅ No duplicate computation
- ✅ Single source of truth (TA Tracker)

**Cons**:
- ⚠️ Requires strict scheduling order
- ⚠️ Still fails if TA Tracker errors

**Implementation**:
- Make Uptrend Engine wait for TA Tracker to complete
- Or run them sequentially in same task

### Option 3: Uptrend Engine Falls Back to Computing EMAs

**Pros**:
- ✅ Best of both worlds
- ✅ Uses TA Tracker if available, computes if not

**Cons**:
- ⚠️ More complex logic

**Implementation**:
```python
ta = self._read_ta(features)
if not ta or ta.get("updated_at") < recent_threshold:
    # TA Tracker hasn't run recently - compute EMAs ourselves
    ema_vals = self._compute_ema_values(contract, chain)
else:
    ema_vals = self._get_ema_values(ta)
```

---

## Recommendation

**Option 3 (Fallback)** is best:
1. **Primary**: Use TA Tracker EMAs (if fresh)
2. **Fallback**: Compute EMAs if TA Tracker is stale/missing
3. **Benefit**: Resilient to TA Tracker failures, no duplicate work when working correctly

**Check freshness**:
```python
ta_updated = ta.get("meta", {}).get("updated_at")
if ta_updated:
    ta_age = (now - datetime.fromisoformat(ta_updated)).total_seconds()
    if ta_age > 120:  # More than 2 minutes old
        # Compute EMAs ourselves
```

---

## Geometry Dependency

**Question**: Does Uptrend Engine need fresh geometry?

**Answer**: **No** - Geometry is used for:
- S/R levels (line 1302): `sr_levels = self._read_sr_levels(features)`
- Used for diagnostics/context, not state machine logic
- Geometry changes slowly (hourly updates are fine)

**Status**: ✅ **No issue** - Geometry can be stale without affecting state machine

---

## Summary

### Current State
- ✅ **Price**: Uptrend Engine sees new candles (fetches directly)
- ❌ **EMAs**: Uptrend Engine uses stale EMAs if TA Tracker doesn't run
- ✅ **Geometry**: Can be stale (not critical for state machine)

### Problem
**Data mismatch**: New price compared to old EMAs = incorrect state transitions

### Solution
**Add fallback**: If TA Tracker is stale/missing, Uptrend Engine computes EMAs itself

---

**End of Analysis**

