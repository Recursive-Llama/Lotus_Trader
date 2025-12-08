# Features Column Analysis: Size, Complexity, and Growth

**Date**: 2025-12-05  
**Example**: 1m timeframe position features column

---

## Current Structure Breakdown

### 1. **TA (Technical Analysis)** - ~200 lines
**Status**: ✅ **Reasonable size, current state only**

- `atr`, `ema`, `meta`, `volume`, `momentum`, `ema_slopes`, `separations`
- All with `_1m` suffix (timeframe-specific)
- **Replaced each run** - stores only current state
- **Growth**: Constant (doesn't accumulate)

### 2. **Geometry** - ~500+ lines ⚠️
**Status**: ⚠️ **Problematic - contains historical data**

#### Components:
- **`levels.sr_levels`**: 12 S/R levels with full metadata (~150 lines)
  - ✅ **OK** - Current computed levels, replaced each run
  
- **`diagonals`**: 2 diagonal lines with metadata (~50 lines)
  - ✅ **OK** - Current computed diagonals, replaced each run
  
- **`swing_points.coordinates`**: **135 swing points** with full coordinates (~300+ lines) ⚠️
  - ❌ **PROBLEM** - Stores ALL historical swing points
  - Each point: `{"type": "low", "index": 6, "price": 0.001018..., "timestamp": "2025-11-25T10:02:00+00:00"}`
  - **Grows over time** - accumulates as position ages
  - **NOT USED** - No code reads these coordinates

- **`swing_points.highs`**: Count (67)
- **`swing_points.lows`**: Count (68)
- **`current_trend`**: Current trend type
- **`trend_segments`**: Count

### 3. **Uptrend Engine v4** - ~50 lines
**Status**: ✅ **Current state only, replaced each run**

- Current state, EMAs, scores, diagnostics
- **Replaced each run** - stores only current snapshot
- **Growth**: Constant (doesn't accumulate)

### 4. **Uptrend Episode Meta** - ~10 lines
**Status**: ✅ **Minimal, current state**

- Episode tracking metadata
- **Growth**: Constant

### 5. **Uptrend Engine v4 Meta** - ~5 lines
**Status**: ✅ **Minimal, current state**

- S3 start timestamp
- **Growth**: Constant

---

## Problem: Swing Points Coordinates

### Current Behavior

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/geometry_build_daily.py:1464-1467`

```python
"swing_points": {
    "highs": len(swing_highs),      # Count: 67
    "lows": len(swing_lows),        # Count: 68
    "coordinates": swing_points      # ALL 135 points with full coordinates
}
```

### Issues

1. **Unbounded Growth**
   - Geometry Builder fetches **ALL available bars** (line 1020: `_fetch_bars(contract, chain, now, None)`)
   - Default lookback: 14 days, but it uses ALL available data
   - For 1m timeframe: Could be 20,000+ bars over 14 days
   - Swing points accumulate: 135 now, could be 500+ for older positions

2. **Not Used**
   - ✅ **Used for computation**: Swing points are used to compute S/R levels and diagonals
   - ❌ **Not used after computation**: No code reads `swing_points.coordinates` after geometry is computed
   - Searched: `pm_core_tick.py`, `actions.py` - no references to `swing_points.coordinates`

3. **Storage Waste**
   - Each swing point: ~100 bytes (type, index, price, timestamp)
   - 135 points: ~13.5 KB
   - 500 points: ~50 KB
   - Multiplied by all active positions = significant storage

4. **Query Performance**
   - Larger JSONB = slower queries
   - Supabase JSONB operations get slower as size grows
   - Indexes on `features` column become less efficient

---

## What Actually Needs to Be Stored?

### ✅ Keep (Current State)
1. **TA** - Current technical indicators (replaced each run)
2. **Geometry.levels** - Computed S/R levels (replaced each run)
3. **Geometry.diagonals** - Computed diagonal lines (replaced each run)
4. **Geometry.current_trend** - Current trend type
5. **Uptrend Engine v4** - Current state/scores (replaced each run)
6. **Episode meta** - Current episode tracking

### ❌ Remove (Historical Data)
1. **Geometry.swing_points.coordinates** - Raw swing point coordinates
   - **Reason**: Not used after computation
   - **Alternative**: Keep only counts (`highs`, `lows`)

### 🤔 Consider (Future Use)
1. **Historical snapshots** - If needed for backtesting/analysis
   - **Solution**: Store in separate `position_history` table
   - **Not in `features`** - Keep `features` for current state only

---

## Growth Projection

### Current (1m position, ~10 days old)
- TA: ~200 lines (constant)
- Geometry: ~500 lines (135 swing points)
- Uptrend Engine: ~50 lines (constant)
- Episode Meta: ~10 lines (constant)
- **Total**: ~760 lines

### Projected (1m position, 30 days old)
- TA: ~200 lines (constant)
- Geometry: ~1,200 lines (400+ swing points) ⚠️
- Uptrend Engine: ~50 lines (constant)
- Episode Meta: ~10 lines (constant)
- **Total**: ~1,460 lines (**+92% growth**)

### Projected (1m position, 90 days old)
- TA: ~200 lines (constant)
- Geometry: ~3,000+ lines (1,000+ swing points) ⚠️⚠️
- Uptrend Engine: ~50 lines (constant)
- Episode Meta: ~10 lines (constant)
- **Total**: ~3,260+ lines (**+329% growth**)

**Conclusion**: Features column will grow **unbounded** as positions age, primarily due to swing point coordinates.

---

## Recommendations

### Immediate Fix: Remove Swing Point Coordinates

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/geometry_build_daily.py:1464-1468`

**Change from:**
```python
"swing_points": {
    "highs": len(swing_highs),
    "lows": len(swing_lows),
    "coordinates": swing_points  # Remove this
}
```

**Change to:**
```python
"swing_points": {
    "highs": len(swing_highs),
    "lows": len(swing_lows)
    # Remove coordinates - not used after computation
}
```

**Impact**:
- ✅ Reduces features size by ~300-500 lines per position
- ✅ Prevents unbounded growth
- ✅ No functional impact (coordinates not used)
- ✅ Faster queries (smaller JSONB)

### Future Consideration: Historical Data Storage

If historical snapshots are needed:

1. **Create `position_history` table**:
   ```sql
   CREATE TABLE position_history (
       id BIGSERIAL PRIMARY KEY,
       position_id TEXT NOT NULL,
       snapshot_type TEXT NOT NULL,  -- 'geometry', 'ta', 'uptrend'
       snapshot_data JSONB NOT NULL,
       created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
   );
   ```

2. **Store historical snapshots separately**:
   - Keep `features` for current state only
   - Store historical snapshots in `position_history` table
   - Query when needed for analysis/backtesting

3. **Benefits**:
   - ✅ `features` stays small and fast
   - ✅ Historical data available when needed
   - ✅ Can archive old history without affecting current state

---

## Current vs. Proposed Structure

### Current (with coordinates)
```json
{
  "ta": {...},                    // ~200 lines
  "geometry": {
    "levels": {...},              // ~150 lines
    "diagonals": {...},           // ~50 lines
    "swing_points": {
      "highs": 67,
      "lows": 68,
      "coordinates": [...]        // ~300 lines ⚠️
    }
  },
  "uptrend_engine_v4": {...},    // ~50 lines
  "uptrend_episode_meta": {...}  // ~10 lines
}
```
**Total**: ~760 lines

### Proposed (without coordinates)
```json
{
  "ta": {...},                    // ~200 lines
  "geometry": {
    "levels": {...},              // ~150 lines
    "diagonals": {...},           // ~50 lines
    "swing_points": {
      "highs": 67,
      "lows": 68
      // No coordinates
    }
  },
  "uptrend_engine_v4": {...},    // ~50 lines
  "uptrend_episode_meta": {...}  // ~10 lines
}
```
**Total**: ~460 lines (**-40% reduction**)

---

## Other Potential Optimizations

### 1. S/R Levels Metadata
Currently stores full metadata for each level:
- `id`, `type`, `price`, `fib_id`, `source`, `strength`, `fib_level`, `confidence`, `order_desc`, `correlation`, `price_native_raw`, `take_profit_target`, `price_rounded_native`

**Question**: Do we need all this metadata, or just:
- `price`, `strength`, `confidence` (for PM decisions)
- Remove: `fib_id`, `source`, `fib_level`, `correlation`, `price_native_raw`, `price_rounded_native` (for display only?)

**Impact**: Could reduce S/R levels from ~150 lines to ~80 lines

### 2. Diagonal Metadata
Currently stores full metadata for each diagonal:
- `type`, `slope`, `r2_score`, `intercept`, `confidence`, `points_count`, `anchor_time_iso`

**Question**: Do we need all this, or just:
- `slope`, `intercept`, `confidence` (for break detection)
- Remove: `r2_score`, `points_count`, `anchor_time_iso` (for computation only?)

**Impact**: Could reduce diagonals from ~50 lines to ~30 lines

### 3. TA Data
Currently stores all EMAs, slopes, separations, etc.

**Question**: Do we need all timeframes, or just the position's timeframe?
- For 1m position: Only need `_1m` suffixed data
- Remove: Other timeframe data (if any)

**Impact**: Minimal (already timeframe-specific)

---

## Summary

### Critical Issue
**Swing point coordinates are causing unbounded growth** in the features column.

### Solution
**Remove `swing_points.coordinates`** - they're not used after computation.

### Impact
- ✅ **-40% reduction** in features size immediately
- ✅ **Prevents unbounded growth** as positions age
- ✅ **No functional impact** (coordinates not used)
- ✅ **Faster queries** (smaller JSONB)

### Future
Consider storing historical snapshots in a separate `position_history` table if needed for analysis/backtesting.

---

**Recommendation**: **Remove swing point coordinates immediately** - this is low-risk, high-impact optimization.

