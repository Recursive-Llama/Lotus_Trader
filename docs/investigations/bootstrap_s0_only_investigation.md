# Bootstrap to S0 Only - Investigation

## Current State

### Bootstrap Logic (uptrend_engine_v4.py, lines 1452-1536)

When a position has **no previous state** (`prev_state == ""` or `None`), the engine bootstraps using this logic:

1. **Check S3 Order** (full bullish EMA alignment):
   - If `_check_s3_order()` returns `True` → **Bootstrap to S3**
   - Sets `s3_start_ts` immediately
   - Computes S3 scores (OX, DX, EDX)
   - Position can immediately trigger buy signals (`first_dip_buy_flag`, `buy_flag`)

2. **Else Check S0 Order** (full bearish EMA alignment):
   - If `_check_s0_order()` returns `True` → **Bootstrap to S0**
   - Position waits (no buys)
   - Only transitions to S1 when: `fast_band_above_60 AND price > EMA60`

3. **Else** → **Bootstrap to S4** (watch-only, ambiguous EMA alignment)
   - Stays in S4 until clear S0 or S3 order emerges
   - Can transition directly: S4 → S3 or S4 → S0 (lines 1788-1852)

### What Happens When Bootstrapping to S3

**Immediate Effects:**
- `s3_start_ts` is set to current timestamp
- S3 scores are computed (OX, DX, EDX)
- Position is in "full uptrend" state immediately

**On First Tick After Bootstrap:**
- Can trigger `first_dip_buy_flag` if:
  - Within first 6 bars: price near EMA20/30 (0.5 ATR)
  - Within first 12 bars: price near EMA60 (0.5 ATR)
  - Slope OK and TS + SR >= 0.50
- Can trigger `buy_flag` (DX buy) if:
  - Price <= EMA144 (discount zone)
  - DX >= threshold (adaptive)
  - Slope OK and TS + SR >= 0.60
  - Not in emergency exit zone

**Result:** Positions that bootstrap to S3 can start buying **immediately** without going through the normal S0 → S1 → S2 → S3 progression.

### What Happens When Bootstrapping to S0

**Immediate Effects:**
- Position is in "pure downtrend" state
- No buy signals are generated
- Position waits

**State Progression:**
- S0 → S1: When `fast_band_above_60 AND price > EMA60`
- S1 → S2: When `price > EMA333`
- S2 → S3: When S3 order appears

**Result:** Positions that bootstrap to S0 must wait for proper trend emergence before any buys.

## Proposed Change: Bootstrap to S0 Only

### Goal
Force all positions to start in S0, requiring them to go through the full state progression (S0 → S1 → S2 → S3) before entering S3. This ensures:
- No immediate S3 entries
- All positions must wait for proper trend confirmation
- Consistent entry behavior regardless of initial EMA alignment

### Required Changes

**Simple approach - just 2 changes:**

#### 1. Remove S3 Bootstrap Check (uptrend_engine_v4.py)

**Location:** Lines 1460-1494

**Current Code:**
```python
if self._check_s3_order(ema_vals):
    logger.info("Bootstrap→S3: %s/%s (timeframe=%s, full bullish alignment)", ...)
    # Bootstrap to S3: Record S3 start timestamp
    current_ts = last.get("ts") or _now_iso()
    self._set_s3_start_ts(pid, features, current_ts)
    # ... compute S3 scores, build payload, write features
    continue
```

**Change:** Remove this entire block. Positions with S3 order will fall through to S0 check (if S0 order) or S4 (if neither).

#### 2. Block S4 → S3 Transition (uptrend_engine_v4.py)

**Location:** Lines 1795-1821

**Current Code:**
```python
elif prev_state == "S4":
    if self._check_s3_order(ema_vals):
        # Transition S4 → S3
        current_ts = last.get("ts") or _now_iso()
        self._set_s3_start_ts(pid, features, current_ts)
        # ... build S3 payload
        payload = self._build_payload("S3", ...)
```

**Change:** Remove S4 → S3 transition, stay in S4 until S0 order appears:
```python
elif prev_state == "S4":
    if self._check_s0_order(ema_vals):
        # Only transition to S0 (existing logic)
        logger.info("Bootstrap→S0: %s/%s (timeframe=%s, full bearish alignment)", ...)
        payload = self._build_payload("S0", ...)
    elif self._check_s3_order(ema_vals):
        # S3 order detected but stay in S4 - wait for S0 order
        logger.debug("S4: %s/%s (timeframe=%s, S3 order detected but waiting for S0 order)", 
                    contract, chain, self.timeframe)
        # Stay in S4 - don't transition
        payload = self._build_payload("S4", ...)
    else:
        # Neither order - stay in S4
        payload = self._build_payload("S4", ...)
```

**That's it!** 
- S4 only exists during bootstrap (temporary state)
- Positions wait in S4 until S0 order appears
- Once in S0, positions can transition normally: S0 → S1 → S2 → S3
- No position ever returns to S4 after having a real state

#### 5. Update Backtester (backtest_uptrend_v4.py)

**Location:** Lines 364-386

**Current Code:**
```python
if not prev_state or prev_state == "":
    if self._check_s3_order(ema_vals):
        prev_state = "S3"
        # Set S3 start timestamp
        # ...
```

**Change:** Remove S3 bootstrap, use same logic as production:
```python
if not prev_state or prev_state == "":
    if self._check_s0_order(ema_vals):
        prev_state = "S0"
        # Track has_been_s0
        if "uptrend_engine_v4_meta" not in features:
            features["uptrend_engine_v4_meta"] = {}
        features["uptrend_engine_v4_meta"]["has_been_s0"] = True
    elif self._check_s3_order(ema_vals):
        # Bootstrap to S4 if S3 order (must go through S0 first)
        prev_state = "S4"
    else:
        prev_state = "S4"
```

### Impact Analysis

#### Positive Impacts
1. **Consistent Entry Behavior:** All positions start from S0, ensuring uniform entry logic
2. **No Immediate S3 Entries:** Prevents positions from buying immediately when in strong uptrend
3. **Proper Trend Confirmation:** Forces positions to wait for S0 → S1 → S2 → S3 progression
4. **Simpler Mental Model:** All positions follow the same state progression

#### Potential Issues
1. **Missed Opportunities:** Positions in strong uptrends (S3 order) will wait for S0 first, potentially missing early entries
2. **S4 Limbo:** Positions with persistent S3 order but no S0 order might stay in S4 until S0 order appears
3. **Learning System Impact:** Historical positions that bootstrapped to S3 will have different behavior than new positions
4. **Backtesting:** Historical backtests will need to be re-run to account for new bootstrap behavior

#### Edge Cases to Consider
1. **Position with S3 order, no S0 order ever appears:**
   - Position stays in S4 indefinitely
   - **Solution:** Could add timeout (e.g., after N bars in S4 with S3 order, force to S0)

2. **Position bootstraps to S4, then S3 order appears before S0:**
   - With our change, S4 → S3 is blocked until has_been_s0 = True
   - Position must wait for S0 order first
   - **Solution:** This is the desired behavior

3. **Position in S0, S3 order appears:**
   - Normal S0 → S1 → S2 → S3 progression
   - **Solution:** This works as expected

### Testing Requirements

1. **Unit Tests:**
   - Test bootstrap with S3 order → should go to S4 (or S0 if forced)
   - Test bootstrap with S0 order → should go to S0
   - Test bootstrap with neither → should go to S4
   - Test S4 → S3 transition blocked without has_been_s0
   - Test S4 → S3 transition allowed with has_been_s0 = True

2. **Integration Tests:**
   - Test full position lifecycle: bootstrap → S0 → S1 → S2 → S3
   - Test position that bootstraps with S3 order → S4 → S0 → S1 → S2 → S3
   - Verify no immediate S3 buys after bootstrap

3. **Backtesting:**
   - Re-run backtests with new bootstrap logic
   - Compare results to previous runs
   - Verify no positions bootstrap directly to S3

### Files to Modify

1. **`src/intelligence/lowcap_portfolio_manager/jobs/uptrend_engine_v4.py`**
   - Remove S3 bootstrap block (lines 1460-1494)
   - Modify S4 → S3 transition (lines 1788-1818)
   - Add `has_been_s0` tracking in all S0 entry points

2. **`tools/backtester/v4/code/backtest_uptrend_v4.py`**
   - Update bootstrap logic (lines 364-386)

3. **Tests** (if they exist)
   - Update bootstrap tests
   - Add tests for new S4 → S3 blocking logic

### Summary

**Complexity:** Low
- Remove S3 bootstrap block (one code block)
- Remove S4 → S3 transition (stay in S4 when S3 order appears)
- Update backtester (same changes)

**Risk:** Low
- Simple, clear change
- All positions must go through S0 first
- No complex state tracking needed

**Recommendation:**
The change is **very simple** - just 2 code modifications:
1. Remove S3 bootstrap (lines 1460-1494) - if S3 order, fall through to S4
2. Remove S4 → S3 transition (lines 1795-1821) - if S3 order in S4, stay in S4 until S0 order appears

This ensures all positions bootstrap to S0 (or wait in S4 until S0 order appears), requiring the full S0 → S1 → S2 → S3 progression before any S3 entries.

