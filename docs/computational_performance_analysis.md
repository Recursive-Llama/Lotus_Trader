# Computational Performance Analysis

**Date**: 2025-12-05  
**Focus**: Identify heaviest tasks and unnecessary work

---

## Executive Summary

**Critical Issues Found:**
1. **Geometry Builder fetches ALL historical data** (no limit) - could be 100,000+ bars for old positions
2. **Theil-Sen fitting is O(n²)** - 400M+ operations for 20K bars
3. **Swing point coordinates stored but never used** - wasted computation
4. **Geometry Builder runs hourly** - recomputes everything even if nothing changed

---

## 1. Geometry Builder - CRITICAL PERFORMANCE ISSUE

### Current Behavior

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/geometry_build_daily.py`

**Line 1020**: `bars = self._fetch_bars(contract, chain, now, None)`
- **Fetches ALL available data** (no limit!)
- `lookback_days` is set (line 50) but **never used** (line 1020 passes `None`)

### Computational Complexity

#### Data Fetching
- **1m timeframe, 14 days**: ~20,160 bars (14 * 24 * 60)
- **1m timeframe, 90 days**: ~129,600 bars
- **1m timeframe, 1 year**: ~525,600 bars ⚠️⚠️⚠️

#### Swing Detection (Line 1031)
- **Complexity**: O(n) where n = number of bars
- **Operations**: ~20,160 for 14 days, ~129,600 for 90 days
- **Status**: ✅ Reasonable

#### Clustering (Line 1041)
- **Complexity**: O(n²) worst case where n = number of swing points
- **Operations**: 
  - 135 swing points: ~18,225 operations
  - 500 swing points: ~250,000 operations
  - 1,000 swing points: ~1,000,000 operations
- **Status**: ⚠️ Could be optimized (currently reasonable for ~100-200 swings)

#### Theil-Sen Fitting (Line 794-809) - **CRITICAL**
- **Complexity**: O(n²) - computes all pairwise slopes
- **Operations per trendline**:
  - 10 points: 45 operations
  - 50 points: 1,225 operations
  - 100 points: 4,950 operations
  - 200 points: 19,900 operations
- **Multiple trendlines per position**: 2-10+ trendlines
- **Total operations**: Could be 50,000-200,000+ per position
- **Status**: ⚠️⚠️ **HEAVY** - but necessary for robust fitting

#### Trend Detection (Line 1078)
- **Complexity**: O(n) - iterates through bars
- **Operations**: ~20,160 for 14 days
- **Status**: ✅ Reasonable

### Redundancy Issues

1. **Recomputes everything hourly** even if:
   - No new bars since last run
   - Geometry hasn't changed
   - Position is dormant

2. **Stores swing point coordinates** (line 1467) but:
   - Never used after computation
   - Wasted storage and serialization time

3. **Fetches ALL historical data** instead of:
   - Using `lookback_days` limit (currently ignored)
   - Or limiting to reasonable amount (e.g., 5,000 bars max)

### Recommendations

#### High Priority
1. **Fix data fetching** - Use `lookback_days` or add hard limit:
   ```python
   # Line 1020 - CHANGE FROM:
   bars = self._fetch_bars(contract, chain, now, None)
   
   # TO:
   lookback_minutes = self.lookback_days * 24 * 60
   bars = self._fetch_bars(contract, chain, now, lookback_minutes)
   # OR add hard limit:
   bars = self._fetch_bars(contract, chain, now, lookback_minutes)
   if len(bars) > 5000:  # Hard limit
       bars = bars[-5000:]  # Keep most recent 5000 bars
   ```

2. **Remove swing point coordinates** - Not used, saves computation and storage

3. **Add change detection** - Skip recomputation if:
   - No new bars since last geometry update
   - Position hasn't changed significantly

#### Medium Priority
4. **Optimize Theil-Sen** - Use approximate method for large point sets:
   - Sample subset of points for initial fit
   - Or use RANSAC for outlier rejection
   - Or limit to recent points only

5. **Cache intermediate results** - If geometry hasn't changed, reuse previous swing points

---

## 2. TA Tracker - MODERATE

### Current Behavior

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/ta_tracker.py`

**Line 193**: `.limit(400)` - **Limits to 400 bars** ✅

### Computational Complexity

#### Data Fetching
- **Always fetches 400 bars max** - reasonable
- **1m**: 400 bars = ~6.7 hours
- **15m**: 400 bars = ~10 days
- **1h**: 400 bars = ~16.7 days
- **4h**: 400 bars = ~66.7 days

#### EMA Calculations (Lines 219-225)
- **Complexity**: O(n) where n = 400
- **Operations**: 7 EMAs × 400 = 2,800 operations
- **Status**: ✅ Very efficient

#### ATR/ADX (Lines 230-233)
- **Complexity**: O(n) where n = 400
- **Operations**: ~400 operations each
- **Status**: ✅ Efficient

#### Volume Z-Score (Lines 236-269)
- **Complexity**: O(n) where n = 400
- **Operations**: 
  - Winsorization: O(n log n) = ~2,400 operations
  - EWMA: O(n) = 400 operations
  - Total: ~2,800 operations
- **Status**: ✅ Reasonable

#### RSI (Lines 272-277)
- **Complexity**: O(n) where n = 400
- **Operations**: ~400 operations
- **Status**: ✅ Efficient

### Redundancy Issues

1. **Runs per timeframe** (1m, 15m, 1h, 4h) - but:
   - Each timeframe processes different positions
   - No redundancy (correct behavior)

2. **Recomputes everything each run** - but:
   - Only 400 bars, very fast
   - Current state needed (not historical)
   - ✅ Acceptable

### Recommendations

**No changes needed** - TA Tracker is well-optimized:
- ✅ Limits data fetch (400 bars)
- ✅ Efficient algorithms (O(n))
- ✅ Reasonable computation time

---

## 3. Uptrend Engine - LIGHT

### Current Behavior

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/uptrend_engine_v4.py`

### Computational Complexity

#### Data Reading
- **Reads TA from features** (already computed) - ✅ No redundant computation
- **Reads geometry from features** (already computed) - ✅ No redundant computation
- **Fetches latest price** (1 query) - ✅ Minimal

#### State Machine Logic
- **Complexity**: O(1) - simple comparisons
- **Operations**: ~50-100 comparisons per position
- **Status**: ✅ Very efficient

#### Score Calculations
- **Complexity**: O(1) - simple math operations
- **Operations**: ~20-30 operations per position
- **Status**: ✅ Very efficient

### Redundancy Issues

**None** - Uptrend Engine is well-optimized:
- ✅ Uses pre-computed TA and geometry
- ✅ Minimal computation
- ✅ Fast execution

### Recommendations

**No changes needed** - Uptrend Engine is efficient.

---

## 4. PM Core Tick - LIGHT-MODERATE

### Current Behavior

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

### Computational Complexity

#### Data Reading
- **Reads features** (already computed) - ✅ No redundant computation
- **Fetches regime context** (1 query) - ✅ Minimal
- **Fetches token buckets** (1 query) - ✅ Minimal

#### Lever Computation
- **Complexity**: O(1) - simple calculations
- **Operations**: ~50-100 operations per position
- **Status**: ✅ Efficient

#### Action Planning
- **Complexity**: O(1) - simple logic
- **Operations**: ~100-200 operations per position
- **Status**: ✅ Efficient

### Redundancy Issues

**None** - PM Core Tick is well-optimized:
- ✅ Uses pre-computed data
- ✅ Minimal computation
- ✅ Fast execution

### Recommendations

**No changes needed** - PM Core Tick is efficient.

---

## 5. Tracker (feat_main) - MODERATE

### Current Behavior

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/tracker.py`

**Schedule**: Every 5 minutes

### Computational Complexity

#### Portfolio-Level Calculations
- **Complexity**: O(n) where n = number of positions
- **Operations**: ~1,000-5,000 operations per run
- **Status**: ✅ Reasonable

#### Phase Computation
- **Complexity**: O(1) - simple calculations
- **Operations**: ~100-200 operations
- **Status**: ✅ Efficient

#### Geometry Tracker (if enabled)
- **Complexity**: O(n) where n = number of active positions
- **Operations**: ~50-100 operations per position
- **Status**: ✅ Reasonable (but currently disabled)

### Redundancy Issues

1. **Writes unused data**:
   - `phase_state` (PORTFOLIO) - not used
   - `portfolio_context` - not used
   - **Recommendation**: Remove unused writes

### Recommendations

1. **Remove unused writes** - Save computation and storage
2. **No other changes needed** - Tracker is reasonably efficient

---

## 6. Summary: Computational Heaviness Ranking

### 🔴 CRITICAL (Needs Optimization)
1. **Geometry Builder** - Fetches ALL historical data, O(n²) Theil-Sen fitting
   - **Impact**: Could process 100,000+ bars for old positions
   - **Fix**: Limit data fetch, remove unused coordinates

### 🟡 MODERATE (Acceptable)
2. **TA Tracker** - Well-optimized, 400 bar limit
3. **Tracker** - Portfolio-level, reasonable

### 🟢 LIGHT (Efficient)
4. **Uptrend Engine** - Uses pre-computed data
5. **PM Core Tick** - Uses pre-computed data

---

## 7. Unnecessary Work Identified

### High Impact

1. **Geometry Builder fetches ALL historical data**
   - **Current**: Fetches 100,000+ bars for old positions
   - **Should**: Limit to `lookback_days` (14 days = ~20K bars for 1m)
   - **Savings**: 80-95% reduction in data fetch and processing

2. **Swing point coordinates stored but never used**
   - **Current**: Computes and stores 135+ coordinates per position
   - **Should**: Remove coordinates, keep only counts
   - **Savings**: ~300 lines per position, faster serialization

3. **Geometry recomputed hourly even if unchanged**
   - **Current**: Recomputes everything every hour
   - **Should**: Skip if no new bars since last run
   - **Savings**: 50-90% reduction in computation (depending on position activity)

### Medium Impact

4. **Tracker writes unused data**
   - **Current**: Writes `phase_state` (PORTFOLIO) and `portfolio_context`
   - **Should**: Remove unused writes
   - **Savings**: Minimal computation, but cleaner code

### Low Impact

5. **Theil-Sen fitting for large point sets**
   - **Current**: O(n²) for all points
   - **Should**: Use approximate method or limit points
   - **Savings**: 50-80% reduction for large point sets

---

## 8. Recommended Optimizations (Priority Order)

### Priority 1: Critical Performance Fixes

1. **Fix Geometry Builder data fetching** (5 min fix)
   ```python
   # Line 1020 - Use lookback_days
   lookback_minutes = self.lookback_days * 24 * 60
   bars = self._fetch_bars(contract, chain, now, lookback_minutes)
   if len(bars) > 5000:  # Hard limit for safety
       bars = bars[-5000:]
   ```

2. **Remove swing point coordinates** (2 min fix)
   ```python
   # Line 1464-1468 - Remove coordinates
   "swing_points": {
       "highs": len(swing_highs),
       "lows": len(swing_lows)
       # Remove: "coordinates": swing_points
   }
   ```

### Priority 2: Change Detection

3. **Skip geometry recomputation if unchanged** (30 min implementation)
   ```python
   # Check if new bars since last geometry update
   last_geom_update = geometry.get("updated_at")
   if last_geom_update:
       last_bars = self._fetch_bars(contract, chain, last_geom_update, None)
       if len(last_bars) == 0:
           continue  # Skip - no new data
   ```

### Priority 3: Theil-Sen Optimization

4. **Limit points for Theil-Sen fitting** (15 min implementation)
   ```python
   # Limit to 50 points max for Theil-Sen
   if len(xs) > 50:
       # Sample evenly or use recent points
       indices = np.linspace(0, len(xs)-1, 50, dtype=int)
       xs = [xs[i] for i in indices]
       ys = [ys[i] for i in indices]
   ```

### Priority 4: Cleanup

5. **Remove unused tracker writes** (10 min fix)
   - Remove `phase_state` (PORTFOLIO) writes
   - Remove `portfolio_context` writes

---

## 9. Expected Performance Improvements

### After Priority 1 Fixes

**Geometry Builder (1m position, 90 days old)**:
- **Before**: Fetches 129,600 bars, processes all
- **After**: Fetches 20,160 bars (14 days), processes all
- **Improvement**: **84% reduction** in data fetch

**Storage per position**:
- **Before**: ~760 lines (with coordinates)
- **After**: ~460 lines (without coordinates)
- **Improvement**: **40% reduction** in storage

### After Priority 2 Fix (Change Detection)

**Geometry Builder (inactive position)**:
- **Before**: Recomputes every hour (even if no new bars)
- **After**: Skips if no new bars
- **Improvement**: **100% reduction** for inactive positions

### After Priority 3 Fix (Theil-Sen Optimization)

**Geometry Builder (position with 200 swing points)**:
- **Before**: 19,900 operations per trendline
- **After**: 1,225 operations per trendline (50 points)
- **Improvement**: **94% reduction** in Theil-Sen computation

---

## 10. Conclusion

### Critical Issues
1. ✅ **Geometry Builder fetches ALL historical data** - Easy fix, huge impact
2. ✅ **Swing point coordinates stored but unused** - Easy fix, good impact
3. ⚠️ **Geometry recomputed hourly even if unchanged** - Medium fix, good impact

### Well-Optimized Components
- ✅ TA Tracker - 400 bar limit, efficient algorithms
- ✅ Uptrend Engine - Uses pre-computed data
- ✅ PM Core Tick - Uses pre-computed data

### Recommendations
**Implement Priority 1 fixes immediately** - Low risk, high impact, easy to implement.

---

**End of Analysis**

