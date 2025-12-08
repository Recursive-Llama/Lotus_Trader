# System Architecture Questions & Answers

**Date**: 2025-12-05  
**Status**: Discussion - No changes yet

---

## 1. TA Tracker Frequency

**Question**: TA Tracker runs every minute for 1m positions, every 15mins for 15m positions, etc.?

**Answer**: ✅ **Yes, correct**

- **1m**: Every 60 seconds (line 697)
- **15m**: Every 15 minutes, aligned to :00 (line 716)
- **1h**: Every hour at :06 (line 726)
- **4h**: Every 4 hours at :00 (line 741)

Each timeframe processes only positions for that timeframe.

---

## 2. Ordering: TA Before Uptrend Engine & PM Core Tick

**Question**: We need to make sure TA Tracker runs before Uptrend Engine and PM Core Tick?

**Answer**: ✅ **Yes, critical dependency**

**Current Schedule (1m)**:
```
Every 60 seconds:
- TA Tracker 1m (line 697)
- Uptrend Engine 1m (line 706)  ⚠️ No guarantee it runs after TA
- PM Core Tick 1m (line 708)     ⚠️ No guarantee it runs after TA
```

**Problem**: They're separate async tasks - no ordering guarantee.

**Solution Options**:
1. **Strict ordering** - Run sequentially in same task
2. **Fallback** - Uptrend Engine computes EMAs if TA is stale
3. **Both** - Ordering + fallback (most robust)

---

## 3. Why Have TA Tracker If Uptrend Engine Can Compute EMAs?

**Question**: If we're thinking about making Uptrend Engine compute EMAs itself as backup, why do we even need TA Tracker? Would it be simpler for Uptrend Engine to do this?

**Answer**: **Good architectural question - here's the trade-off:**

### Option A: Keep TA Tracker (Current)

**Pros**:
- ✅ **Separation of concerns**: TA Tracker = data preparation, Uptrend Engine = state machine
- ✅ **Reusability**: TA data used by multiple systems (Uptrend Engine, PM Core Tick, learning system)
- ✅ **Single source of truth**: All TA computed in one place
- ✅ **Efficiency**: Compute once, use many times

**Cons**:
- ⚠️ **Dependency**: Uptrend Engine depends on TA Tracker
- ⚠️ **Complexity**: Two systems to maintain

### Option B: Uptrend Engine Computes EMAs

**Pros**:
- ✅ **Self-contained**: No external dependencies
- ✅ **Simpler**: One less system
- ✅ **Always fresh**: EMAs computed from latest data

**Cons**:
- ❌ **Duplicate computation**: If PM Core Tick or learning system needs TA, they'd also compute it
- ❌ **Code duplication**: EMA computation logic in multiple places
- ❌ **Heavier Uptrend Engine**: More responsibility = more complexity

### Recommendation: **Keep TA Tracker + Add Fallback**

**Why**:
1. **TA is used by multiple systems**:
   - Uptrend Engine (EMAs, ATR, RSI, slopes)
   - PM Core Tick (reads TA for diagnostics)
   - Learning system (pattern matching uses TA)
   - Backtester (needs TA for historical analysis)

2. **Strict ordering is better than duplication**:
   - Run TA Tracker → Uptrend Engine → PM Core Tick sequentially
   - Add fallback in Uptrend Engine only as safety net

3. **Architecture principle**: 
   - Data preparation (TA) should be separate from decision logic (Uptrend Engine)
   - Makes system more maintainable and testable

**Implementation**:
- Run TA Tracker, then Uptrend Engine, then PM Core Tick in sequence
- Add fallback in Uptrend Engine: if TA is stale (>2 minutes), compute EMAs itself

---

## 4. Bar Limits: 999-3333 Bars?

**Question**: I think we should limit both TA and Geometry but talk to me on how many bars is too many. I would say we want at least 999 bars for both, maybe we do 3333 bars for each? I see you are saying 20k bars, but I do think that TA and geometry should do the same amount of bars right?

**Answer**: **Good point - let's align them**

### Current State

**TA Tracker**:
- **Limit**: 400 bars (line 193)
- **1m**: 400 bars = ~6.7 hours
- **15m**: 400 bars = ~10 days
- **1h**: 400 bars = ~16.7 days
- **4h**: 400 bars = ~66.7 days

**Geometry Builder**:
- **Limit**: **NONE** (fetches ALL data) ⚠️
- **1m, 14 days**: ~20,160 bars
- **1m, 90 days**: ~129,600 bars

### Your Proposal: 999-3333 Bars

**Analysis**:

**999 bars**:
- **1m**: 999 bars = ~16.7 hours
- **15m**: 999 bars = ~10.4 days
- **1h**: 999 bars = ~41.6 days
- **4h**: 999 bars = ~166.7 days

**3333 bars**:
- **1m**: 3333 bars = ~55.5 hours (~2.3 days)
- **15m**: 3333 bars = ~34.7 days
- **1h**: 3333 bars = ~138.9 days (~4.6 months)
- **4h**: 3333 bars = ~555.5 days (~1.5 years)

### Recommendation: **3333 bars for both**

**Why**:
1. ✅ **Consistent**: TA and Geometry use same data window
2. ✅ **Sufficient for EMAs**: EMA333 needs 333+ bars, 3333 gives 10x buffer
3. ✅ **Sufficient for geometry**: Enough swing points for S/R levels and diagonals
4. ✅ **Reasonable computation**: 3333 bars is manageable (not 100K+)

**Trade-off**:
- **1m timeframe**: 3333 bars = ~2.3 days (might miss longer-term structure)
- **But**: Geometry changes slowly, hourly recomputation is fine
- **Alternative**: Use timeframe-specific limits (1m: 3333, 1h: 999)

### Implementation

**TA Tracker** (line 193):
```python
.limit(3333)  # Change from 400
```

**Geometry Builder** (line 1020):
```python
# Change from:
bars = self._fetch_bars(contract, chain, now, None)

# To:
bars = self._fetch_bars(contract, chain, now, None)
bars = bars[-3333:] if len(bars) > 3333 else bars  # Hard limit
```

---

## 5. Additive vs Recompute

**Question**: Is there no way we can make it "additive" right? You know what I mean, is it best to recompute everything?

**Answer**: **Depends on the calculation**

### TA Tracker: **Can be additive** (but not worth it)

**EMAs are incremental**:
- EMA(n) = α × price(n) + (1-α) × EMA(n-1)
- **Could**: Store last EMA value, compute only new bars
- **But**: Only saves ~7 operations per new bar (7 EMAs)
- **Complexity**: Need to track last EMA values, handle gaps, etc.
- **Verdict**: ❌ **Not worth it** - recompute is simpler and fast enough

**Other TA** (RSI, ATR, ADX, slopes):
- Need full history for accurate calculation
- **Verdict**: ❌ **Must recompute**

### Geometry Builder: **Must recompute**

**Why**:
1. **Swing detection**: Needs to scan all bars to find pivots
2. **S/R clustering**: Needs all swing points to cluster properly
3. **Diagonals**: Needs all swing points to fit trendlines
4. **Trend changes**: Need full history to detect trend reversals

**Could we be additive?**:
- ❌ **No** - Adding one new bar could:
  - Create new swing point that changes clustering
  - Change trend direction
  - Invalidate previous diagonals

**Verdict**: ✅ **Recompute is correct** - geometry is structural analysis, needs full picture

### Recommendation

**Keep recompute approach**:
- ✅ **Simpler**: No state to track
- ✅ **Correct**: Always uses full data
- ✅ **Fast enough**: 3333 bars is manageable
- ✅ **Reliable**: No edge cases from incremental updates

**Optimize instead**:
- Limit to 3333 bars (not 100K+)
- Skip if no new bars (change detection)
- Remove unused data (swing coordinates)

---

## 6. Diagonals: Do We Use Them?

**Question**: So we don't actually use diagonals anymore right? We just use EMAs and the horizontal S/R, would it be best to just remove the diagonal calculations, would that save us much?

**Answer**: **Let me check...**

### Where Diagonals Are Referenced

**PM Core Tick** (line 2607):
- `"diag_break"` in `preferred_order` list
- **But**: This is just for **logging/ordering reasons**, not decision logic

**Actions** (`plan_actions_v4`):
- ❌ **No references to `diag_break` or `diagonal`**
- Uses: `sr_levels`, `at_support`, but **not diagonals**

**Uptrend Engine**:
- ❌ **No references to diagonals**
- Uses: EMAs, S/R levels, but **not diagonals**

**Tracker** (if enabled):
- Updates `diag_break` flags in geometry
- But these flags are **not used** by PM Core Tick or Actions

### Conclusion: **Diagonals are NOT used for decisions**

**They're computed and stored, but**:
- ❌ Not used in `plan_actions_v4()`
- ❌ Not used in Uptrend Engine state machine
- ❌ Not used in PM Core Tick decisions
- ✅ Only used for logging/display (if at all)

### Computational Cost

**Geometry Builder diagonal computation**:
- **Trend detection**: O(n) - scans all bars
- **Swing point clustering**: O(n²) - clusters swing points
- **Theil-Sen fitting**: O(n²) per trendline - **HEAVY**
- **Multiple trendlines**: 2-10+ per position

**Savings if removed**:
- **Trend detection**: ~20K operations (can keep for S/R)
- **Diagonal fitting**: ~50K-200K operations per position ⚠️
- **Total**: **Significant savings** (50-80% of geometry computation)

### Recommendation: **Remove diagonal calculations**

**Why**:
1. ✅ **Not used** - No code reads diagonals for decisions
2. ✅ **Heavy computation** - Theil-Sen is O(n²), expensive
3. ✅ **Simpler code** - Less complexity
4. ✅ **Faster geometry** - 50-80% reduction in computation time

**Keep**:
- S/R levels (used for trim cooldown)
- Swing point counts (for diagnostics)
- Current trend type (for context)

**Remove**:
- Diagonal trendline fitting
- `diag_break` flags
- `diag_status` state machine
- `diag_levels` projections

---

## 7. Swing Points: Don't Need Them?

**Question**: So we don't need the swing points it seems right?

**Answer**: ✅ **Correct - we don't need the coordinates**

**What we need**:
- ✅ **Swing point counts** (`highs`, `lows`) - for diagnostics
- ❌ **Swing point coordinates** - not used after computation

**Why coordinates are computed**:
- Used **during** computation to:
  - Cluster into S/R levels
  - Fit diagonal trendlines (if we keep them)
- **Not used after** computation

**Recommendation**: **Remove coordinates, keep counts**

---

## 8. Change Detection: Does It Add Complexity?

**Question**: Does change detection add complexity? Because any position that is active or in watchlist will be changing. And positions that are dormant we need to monitor to see when they have at least 33 bars, right? We do this correct?

**Answer**: **Good point - let me clarify**

### Current Dormant Monitoring

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/update_bars_count.py`

**Runs**: Hourly at :07 (line 734)

**What it does**:
1. Counts bars for **dormant positions only**
2. Updates `bars_count`
3. Auto-flips `dormant → watchlist` when `bars_count >= 333` ✅

**PM Core Tick**:
- **Skips dormant positions** (line 415: `.in_("status", ["watchlist", "active"])`)
- Only processes `watchlist` and `active`

### Change Detection Complexity

**Your concern is valid**:

**Active/Watchlist positions**:
- ✅ **Always changing** - new bars every minute/15min/hour
- ✅ **Need fresh TA/Geometry** - for accurate decisions
- ❌ **Change detection doesn't help** - they always have new bars

**Dormant positions**:
- ✅ **Monitored separately** - `update_bars_count.py` handles this
- ✅ **Auto-flip at 333 bars** - no manual intervention needed
- ❌ **Change detection doesn't apply** - PM Core Tick doesn't process dormant

### Recommendation: **Skip change detection**

**Why**:
1. ✅ **Active/Watchlist always change** - detection would always say "recompute"
2. ✅ **Dormant handled separately** - `update_bars_count.py` monitors them
3. ✅ **Simpler code** - no need to track last update time
4. ✅ **Fast enough** - 3333 bars is manageable, recompute is fine

**Instead, optimize**:
- Limit to 3333 bars (not 100K+)
- Remove unused computations (diagonals, coordinates)
- This gives us 80-90% of the performance gain without complexity

---

## 9. Remove Unused Tracker Stuff

**Question**: We should remove the unused tracker stuff?

**Answer**: ✅ **Yes**

**Remove from `tracker.py`**:
1. **`phase_state` (PORTFOLIO) writes** (lines 218-261) - not used
2. **`portfolio_context` writes** (lines 327-387) - not used

**Keep**:
- **`phase_state_bucket` writes** (lines 268-325) - used for bucket ordering
- **Geometry tracker** (lines 389-686) - optional, currently disabled

---

## 10. What Else Are We Missing?

### Additional Considerations

1. **TA Tracker bar limit mismatch**:
   - Currently: 400 bars
   - Should be: 3333 bars (to match geometry)
   - **Impact**: TA Tracker might miss longer-term patterns

2. **Geometry Builder lookback_days ignored**:
   - Currently: Fetches ALL data (ignores `lookback_days`)
   - Should: Use `lookback_days` or hard limit to 3333 bars
   - **Impact**: Processes 100K+ bars unnecessarily

3. **Event subscriptions**:
   - Currently: Broken, causing excessive PM Core Tick runs
   - Should: Remove entirely
   - **Impact**: Fixes the 12-15 second emergency_exit issue

4. **Scheduler timing**:
   - Currently: Geometry Builder at :07 (after PM Core Tick at :06)
   - Should: Geometry Builder at :05 (before PM Core Tick)
   - **Impact**: PM Core Tick uses fresh geometry

5. **TA Tracker vs Uptrend Engine ordering**:
   - Currently: No guarantee TA runs before Uptrend Engine
   - Should: Run sequentially or add fallback
   - **Impact**: Prevents stale EMA issues

---

## Summary of Recommendations

### High Priority (Easy, High Impact)

1. ✅ **Remove event subscriptions** - Fixes excessive runs
2. ✅ **Fix Geometry Builder data limit** - Use 3333 bars max
3. ✅ **Remove swing point coordinates** - Not used
4. ✅ **Remove diagonal calculations** - Not used, heavy computation
5. ✅ **Fix scheduler timing** - Geometry before PM Core Tick
6. ✅ **Remove unused tracker writes** - Clean up code

### Medium Priority (Architecture)

7. ⚠️ **TA Tracker bar limit** - Increase to 3333 (match geometry)
8. ⚠️ **TA/Uptrend Engine ordering** - Run sequentially or add fallback

### Low Priority (Nice to Have)

9. 🤔 **Theil-Sen optimization** - Limit points if keeping diagonals (but we're removing them)
10. 🤔 **Change detection** - Skip if no new bars (but active positions always have new bars) --> no dont do this

---

## Questions for You

1. **Bar limit**: 3333 bars for both TA and Geometry? Or timeframe-specific (1m: 3333, 1h: 999)?

2. **TA Tracker vs Uptrend Engine**: Strict ordering or fallback? Or both?

3. **Diagonals**: Confirm we're not using them, then remove?
--> yes remove

4. **Change detection**: Skip it since active positions always change?
--> yes skip

---

**End of Discussion Document**

