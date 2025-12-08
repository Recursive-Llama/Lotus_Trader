# Agreed Changes Checklist

**Date**: 2025-12-05  
**Status**: Ready to implement

---

## Summary

All changes discussed and agreed upon. This is the complete list of what we're implementing.

---

## 1. Remove Event Subscriptions (CRITICAL FIX)

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

**Problem**: Event handlers causing PM Core Tick 1h to run every 12-15 seconds instead of hourly

**Changes**:
- Remove `_subscribe_events()` function (lines 2954-2990)
- Remove call to `_subscribe_events()` in `main()` (line 3002)

**Impact**: Fixes excessive `emergency_exit` actions (488 in 24 hours → should be ~24)

### Also Remove Event Emissions (Cleanup)

**Files**: 
- `src/intelligence/lowcap_portfolio_manager/jobs/tracker.py` (line 266)
- `src/intelligence/lowcap_portfolio_manager/spiral/persist.py` (line 48)

**Changes**:
- Remove `bus.emit("phase_transition", {...})` from tracker.py
- Remove `emit("phase_transition", {...})` from spiral/persist.py

**Why**: No one subscribes to these events anymore, so emissions are wasted computation

**Note**: Keep `events/bus.py` infrastructure (might be used elsewhere)

---

## 2. Fix Scheduler Timing

**File**: `src/run_trade.py`

**Problem**: Geometry Builder runs AFTER PM Core Tick, causing stale geometry data

**Changes**:
- Move Geometry Builder from :07 to :05 (before PM Core Tick at :06)
- Lines 729-733: Change `_schedule_hourly(7, ...)` to `_schedule_hourly(5, ...)`

**Impact**: PM Core Tick uses fresh geometry data

---

## 3. Set Bar Limits to 9999

### TA Tracker

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/ta_tracker.py`

**Change**:
- Line 193: Change `.limit(400)` to `.limit(9999)`

**Impact**: Better coverage (7 days for 1m vs 6.7 hours), still very fast (~3-5ms)

### Geometry Builder

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/geometry_build_daily.py`

**Change**:
- Line 1020: Change from `bars = self._fetch_bars(contract, chain, now, None)` 
- To:
  ```python
  bars = self._fetch_bars(contract, chain, now, None)
  if len(bars) > 9999:
      bars = bars[-9999:]  # Keep most recent 9999 bars
  ```

**Impact**: Prevents processing 100K+ bars, limits to reasonable amount

---

## 4. Remove Swing Point Coordinates

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/geometry_build_daily.py`

**Change**:
- Lines 1464-1468: Remove `"coordinates": swing_points` from swing_points dict
- Keep only `"highs"` and `"lows"` counts

**Before**:
```python
"swing_points": {
    "highs": len(swing_highs),
    "lows": len(swing_lows),
    "coordinates": swing_points  # Remove this
}
```

**After**:
```python
"swing_points": {
    "highs": len(swing_highs),
    "lows": len(swing_lows)
}
```

**Impact**: -40% reduction in features size, prevents unbounded growth

---

## 5. Remove Diagonal Calculations

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/geometry_build_daily.py`

**Problem**: Diagonals are computed but never used in trading decisions

**Changes**:
- Remove `_detect_trends_proper()` call (line 1078)
- Remove `_generate_trendlines_for_segment()` calls (lines 1084-1100+)
- Remove `diagonals` from geometry dict (line 1462)
- Remove diagonal-related code in geometry builder

**Keep**:
- S/R levels (used for trim cooldown)
- Swing point counts (for diagnostics)
- Current trend type (for context)

**Impact**: 50-80% reduction in geometry computation time (Theil-Sen is O(n²))

---

## 6. Remove Unused Tracker Writes

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/tracker.py`

**Changes**:
- Remove `phase_state` (PORTFOLIO) writes (lines 218-261)
  - Not used - replaced by regime engine states
- Remove `portfolio_context` writes (lines 327-387)
  - Not used - no code reads it

**Keep**:
- `phase_state_bucket` writes (lines 268-325) - used for bucket ordering
- Geometry tracker (lines 389-686) - optional, currently disabled

**Impact**: Cleaner code, less unnecessary computation

---

## 7. Ensure TA Tracker Runs Before Uptrend Engine

**File**: `src/run_trade.py`

**Problem**: No guarantee TA Tracker runs before Uptrend Engine (race condition)

**Options**:
- **Option A**: Run sequentially in same task (recommended)
- **Option B**: Add fallback in Uptrend Engine (compute EMAs if TA stale)

**Recommendation**: **Both** - strict ordering + fallback for safety

**Implementation**:
- Run TA Tracker → Uptrend Engine → PM Core Tick sequentially
- Add fallback in Uptrend Engine: if TA is stale (>2 minutes), compute EMAs itself

**Impact**: Prevents data mismatch (new price vs old EMAs)

---

## Summary of All Changes

### High Priority (Critical Fixes)

1. ✅ **Remove event subscriptions** - Fixes excessive PM Core Tick runs
2. ✅ **Fix scheduler timing** - Geometry Builder before PM Core Tick
3. ✅ **Set bar limits to 9999** - TA Tracker and Geometry Builder
4. ✅ **Remove swing point coordinates** - Prevents unbounded growth
5. ✅ **Remove diagonal calculations** - Not used, heavy computation

### Medium Priority (Cleanup)

6. ✅ **Remove unused tracker writes** - Clean up code
7. ⚠️ **TA/Uptrend Engine ordering** - Strict ordering + fallback

---

## Files to Modify

### 1. `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`
- Remove `_subscribe_events()` function
- Remove call to `_subscribe_events()` in `main()`

### 1b. `src/intelligence/lowcap_portfolio_manager/jobs/tracker.py`
- Remove `bus.emit("phase_transition", {...})` (line 266)

### 1c. `src/intelligence/lowcap_portfolio_manager/spiral/persist.py`
- Remove `emit("phase_transition", {...})` (line 48)

### 2. `src/run_trade.py`
- Move Geometry Builder from :07 to :05
- Ensure TA Tracker runs before Uptrend Engine (sequential execution)

### 3. `src/intelligence/lowcap_portfolio_manager/jobs/ta_tracker.py`
- Change `.limit(400)` to `.limit(9999)` (line 193)

### 4. `src/intelligence/lowcap_portfolio_manager/jobs/geometry_build_daily.py`
- Add 9999 bar limit (line 1020)
- Remove swing point coordinates (lines 1464-1468)
- Remove diagonal calculations (lines 1078-1100+, 1462)

### 5. `src/intelligence/lowcap_portfolio_manager/jobs/tracker.py`
- Remove `phase_state` (PORTFOLIO) writes (lines 218-261)
- Remove `portfolio_context` writes (lines 327-387)

### 6. `src/intelligence/lowcap_portfolio_manager/jobs/uptrend_engine_v4.py` (Optional)
- Add fallback: compute EMAs if TA is stale (>2 minutes)

---

## Expected Impact

### Performance Improvements

**Geometry Builder (1m position, 90 days old)**:
- **Before**: 129,600 bars, ~500ms-2s
- **After**: 9,999 bars, ~10-20ms
- **Improvement**: **25-100x faster**

**Storage per position**:
- **Before**: ~760 lines (with coordinates, diagonals)
- **After**: ~300 lines (without coordinates, diagonals)
- **Improvement**: **-60% reduction**

**PM Core Tick 1h runs**:
- **Before**: Every 12-15 seconds (event-driven)
- **After**: Once per hour (scheduled only)
- **Improvement**: **-95% reduction** in unnecessary runs

### Data Quality Improvements

**TA Tracker**:
- **Before**: 400 bars = 6.7 hours for 1m
- **After**: 9,999 bars = 7 days for 1m
- **Improvement**: Better coverage, catches weekly patterns

**Geometry Builder**:
- **Before**: Unlimited (could be 100K+ bars)
- **After**: 9,999 bars max
- **Improvement**: Consistent, predictable computation

---

## Testing Checklist

After implementation:

1. ✅ **Verify PM Core Tick 1h runs hourly only**
   - Check `pm_core.log` - should see runs at :06 only
   - Check `ad_strands` - should not see `emergency_exit` every 12-15 seconds

2. ✅ **Verify Geometry Builder runs before PM Core Tick**
   - Check logs - Geometry Builder at :05, PM Core Tick at :06
   - Verify PM Core Tick reads fresh geometry data

3. ✅ **Verify bar limits**
   - Check TA Tracker fetches max 9999 bars
   - Check Geometry Builder fetches max 9999 bars
   - Verify no positions processing 100K+ bars

4. ✅ **Verify features size reduction**
   - Check features column - should not have `swing_points.coordinates`
   - Check features column - should not have `diagonals`
   - Verify size is ~60% smaller

5. ✅ **Verify bucket ordering still works**
   - Check that `phase_state_bucket` is still written by Tracker
   - Verify `fetch_bucket_phase_snapshot()` still works
   - Confirm bucket multipliers in `compute_levers()` still function

6. ✅ **Verify no regressions**
   - PM Core Tick should still process positions correctly
   - Actions should still be planned and executed
   - Strands should still be written
   - Uptrend Engine should still compute states correctly

---

## Implementation Order

### Phase 1: Critical Fixes (Do First)
1. Remove event subscriptions
2. Fix scheduler timing
3. Set bar limits to 9999

### Phase 2: Cleanup (Do Second)
4. Remove swing point coordinates
5. Remove diagonal calculations
6. Remove unused tracker writes

### Phase 3: Safety (Do Third)
7. TA/Uptrend Engine ordering + fallback

---

## Questions Resolved

✅ **TA Tracker frequency**: Per timeframe (correct)
✅ **Ordering**: TA before Uptrend Engine (strict ordering + fallback)
✅ **Why TA Tracker**: Keep it (used by multiple systems) + add fallback
✅ **Bar limits**: 9999 bars for both TA and Geometry
✅ **Additive vs recompute**: Recompute (simpler, correct)
✅ **Diagonals**: Remove (not used, heavy computation)
✅ **Swing points**: Remove coordinates, keep counts
✅ **Change detection**: Skip (active positions always change)
✅ **Unused tracker**: Remove `phase_state` (PORTFOLIO) and `portfolio_context`

---

## What We're NOT Doing

❌ **Change detection** - Skip recomputation if no new bars
   - Reason: Active positions always have new bars, adds complexity

❌ **Incremental updates** - Additive TA/Geometry computation
   - Reason: Recompute is simpler and correct

❌ **Theil-Sen optimization** - Limit points for diagonal fitting
   - Reason: Removing diagonals entirely, so not needed

---

**End of Checklist**

