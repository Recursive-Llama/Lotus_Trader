# PM System Investigation Summary

**Date**: 2025-12-05  
**Investigation Focus**: PM Core Tick scheduling, event handlers, and data flow dependencies

---

## Executive Summary

This investigation revealed several critical issues with the PM system:
1. **Event handlers are broken** - causing PM Core Tick 1h to run every 12-15 seconds instead of hourly
2. **Scheduler timing misalignment** - Geometry Builder runs AFTER PM Core Tick, causing stale data
3. **Event system is redundant** - scheduled runs already handle the same data
4. **Tracker.py has unused components** - writes data that's never consumed

---

## 1. Critical Issue: Event Handlers Causing Excessive PM Core Tick Runs

### Problem
PM Core Tick 1h was running every 12-15 seconds instead of once per hour, causing 488 `emergency_exit` actions in 24 hours for the same positions.

### Root Cause
**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py` (lines 2954-2990)

The `_subscribe_events()` function:
1. Subscribes to events (`phase_transition`, `structure_change`, `sr_break_detected`, `ema_trail_breach`)
2. Event handlers call `PMCoreTick().run()` **without a timeframe**, defaulting to `"1h"` (line 46)
3. `_subscribe_events()` is called in `main()` (line 3002), which runs for **each timeframe** (1m, 15m, 1h, 4h)
4. This causes **multiple handlers to register** (one per timeframe run)
5. When events fire, **all handlers run**, each triggering PM Core Tick 1h

### Evidence
- `pm_core.log` shows PM Core Tick 1h running hourly at :06 (correct scheduled runs)
- `ad_strands` shows `emergency_exit` actions every 12-15 seconds (event-driven runs)
- Event-driven runs don't log, making them invisible in logs

### Events Status
- `phase_transition` - **Actually emitted** by `tracker.py` (every 5 minutes) and `spiral/persist.py` (on phase changes)
- `structure_change` - **Never emitted** (dead code)
- `sr_break_detected` - **Never emitted** (dead code)
- `ema_trail_breach` - **Never emitted** (dead code)

### Recommendation
**Remove event subscriptions entirely**. Scheduled runs are sufficient and already handle the same data.

---

## 2. Scheduler Timing Issues

### Current Schedule (1h Timeframe)

```
:01 - Uptrend Engine 1h
:01 - Regime 1h
:02 - NAV
:04 - Rollup 1h (OHLC data)
:06 - TA Tracker 1h → writes features.ta
:06 - PM Core Tick 1h → reads features.ta, features.geometry, features.uptrend_engine_v4
:07 - Geometry Builder 1h → writes features.geometry (levels, diagonals)
```

### Problem
**Geometry Builder runs AFTER PM Core Tick**, meaning PM Core Tick uses stale geometry data from the previous hour.

### Current Schedule (All Timeframes)

**1 Minute Jobs:**
- TA Tracker 1m
- OHLC Rollup 1m
- Majors Rollup
- Uptrend Engine 1m
- Regime 1m
- PM Core Tick 1m

**5 Minute Jobs (Aligned to :00):**
- Tracker (feat_main) - portfolio-level phase computation
- Rollup 5m
- Pattern Aggregator (:02)

**15 Minute Jobs (Aligned to :00):**
- TA Tracker 15m
- Rollup 15m
- Uptrend Engine 15m
- PM Core Tick 15m

**Hourly Jobs:**
- :01 - Uptrend Engine 1h, Regime 1h
- :02 - NAV
- :04 - Rollup 1h
- :06 - TA Tracker 1h, PM Core Tick 1h
- :07 - Geometry Builder (all timeframes: 1m, 15m, 1h, 4h), Bars Count
- :08 - Lesson Builder PM
- :09 - Lesson Builder DM
- :10 - Override Materializer

**4 Hour Jobs (Aligned to :00):**
- TA Tracker 4h
- Rollup 4h
- Uptrend Engine 4h
- PM Core Tick 4h

### Recommendation
**Move Geometry Builder to :05** (before PM Core Tick at :06) to ensure fresh geometry data.

---

## 3. Geometry System Architecture

### Two-Part System

#### Part 1: Geometry Builder (`geometry_build_daily.py`)
- **Schedule**: Hourly at :07 (all timeframes)
- **Purpose**: Computes S/R levels and diagonals from scratch
- **Output**: Writes `features.geometry.levels` and `features.geometry.diagonals`
- **Frequency**: Once per hour (sufficient for structural changes)

#### Part 2: Geometry Tracker (`tracker.py` lines 389-686)
- **Schedule**: Every 5 minutes (if `GEOMETRY_TRACKER_ENABLED=1`)
- **Purpose**: Updates break flags by comparing latest price to stored levels
- **Output**: Updates `features.geometry` with:
  - `sr_break`, `sr_strength`
  - `diag_break`, `diag_strength`
  - `diag_status` (breakout/retrace state machine)
  - `tracker_trend`, `tracker_trend_changed`
- **Status**: **Disabled by default** (`GEOMETRY_TRACKER_ENABLED=0`)

### How PM Core Tick Uses Geometry

**File**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py`

- **Line 398**: Reads `sr_levels` for trim cooldown logic
- **Line 55**: Reads `at_support` for pattern key generation
- **Line 425-427**: Checks if S/R level changed to allow trims

### Events vs Scheduled Runs

**Events would have done:**
- Trigger PM Core Tick immediately when `sr_break_detected` or `structure_change` fires

**Scheduled runs actually do:**
- Tracker updates `features.geometry` with break flags every 5 minutes
- PM Core Tick reads `features.geometry` on schedule (every 1m/15m/1h/4h)

**Conclusion**: Same data source (`features.geometry`), different timing:
- Events: Immediate response (but broken)
- Scheduled: Up to 1 hour delay (acceptable for most cases)

---

## 4. Tracker.py Analysis

### What Tracker Does

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/tracker.py`  
**Schedule**: Every 5 minutes (aligned to :00, :05, :10, etc.)

#### Component 1: Portfolio-Level Phase Computation (Lines 21-267)
- Computes macro/meso/micro phases using SPIRAL lens system
- Writes to `phase_state` table (token="PORTFOLIO")
- Writes to `phase_state_bucket` table (per bucket: nano, micro, mid, big, large)
- Emits `phase_transition` events

#### Component 2: Portfolio Context (Lines 327-387)
- Writes `features.portfolio_context` to all active positions
- Contains: `r_btc`, `r_alt`, `r_port`, `rotation_spread`, `vo`, `obv`, `rsi`, `diagnostics`, `bucket_regime`
- **Status**: **NOT USED** - No code reads `portfolio_context`

#### Component 3: Geometry Tracker (Lines 389-686)
- Updates break flags in `features.geometry`
- **Status**: **Disabled by default** (`GEOMETRY_TRACKER_ENABLED=0`)

### What's Actually Used

#### ✅ Used: `phase_state_bucket`
- **Read by**: `fetch_bucket_phase_snapshot()` in `regime/bucket_context.py`
- **Used for**: Bucket ordering/multipliers in `compute_levers()`
- **Status**: **KEEP** - Still needed

#### ❌ Not Used: `phase_state` (PORTFOLIO)
- **Read by**: Nothing (old system)
- **Replaced by**: Regime engine states (S0, S1, S2, S3) from `lowcap_positions` with `status='regime_driver'`
- **Status**: **CAN REMOVE** - Dead code

#### ❌ Not Used: `portfolio_context`
- **Read by**: Nothing
- **Status**: **CAN REMOVE** - Dead code

### Should Tracker Run Per-Timeframe?

**No.** Tracker computes **portfolio-level metrics** (not per-token), so it should run once globally, not per timeframe.

Current schedule (every 5 minutes globally) is correct.

### Recommendation

**Simplify tracker.py**:
1. **Keep**: Portfolio phase computation → `phase_state_bucket` (used for bucket ordering)
2. **Remove**: Portfolio phase → `phase_state` (PORTFOLIO) - not used
3. **Remove**: Portfolio context writing - not used
4. **Optional**: Geometry tracker (currently disabled, can keep for future use)

---

## 5. Data Flow Dependencies

### PM Core Tick Data Sources

PM Core Tick reads from:
1. `features.ta` - Written by TA Tracker (per timeframe)
2. `features.geometry` - Written by Geometry Builder (hourly) + Geometry Tracker (every 5 min, if enabled)
3. `features.uptrend_engine_v4` - Written by Uptrend Engine (per timeframe)
4. `phase_state_bucket` - Written by Tracker (every 5 minutes)
5. Regime driver positions - Written by Regime pipeline (per timeframe)

### Correct Order (1h Example)

```
:01 - Uptrend Engine 1h → features.uptrend_engine_v4
:01 - Regime 1h → regime driver positions
:04 - Rollup 1h → OHLC data
:05 - Geometry Builder 1h → features.geometry (levels, diagonals) [MOVED FROM :07]
:06 - TA Tracker 1h → features.ta
:06 - PM Core Tick 1h → reads all above
```

### Tracker Schedule (Global, Not Per-Timeframe)

```
Every 5 minutes (:00, :05, :10, etc.):
- Tracker → phase_state_bucket (used for bucket ordering)
```

---

## 6. Event System vs Scheduled Runs

### Original Intent (From Docs)

Events were meant for **immediate response** to important changes:
- `phase_transition` → Immediate A/E recomputation when phase changes
- `sr_break_detected` → Immediate A/E adjustments on S/R breaks
- `structure_change` → Immediate recompute on structure breaks
- `ema_trail_breach` → Immediate trail stop evaluation

### Current Reality

**Events are redundant:**
- Tracker already updates `features.geometry` with break flags
- PM Core Tick already reads `features.geometry` on schedule
- Same data source, just different timing

**Events are broken:**
- Default to "1h" timeframe (bug)
- Register multiple times (memory leak)
- Don't log (invisible)
- Most events never fire (dead code)

### Recommendation

**Remove event subscriptions entirely**. Scheduled runs are:
- More predictable
- Easier to debug
- Already handle the same data
- Sufficient frequency (1m/15m/1h/4h)

The only trade-off is **latency** (up to 1 hour delay for 1h timeframe), which is acceptable for most cases.

---

## 7. Recommendations Summary

### Immediate Actions

1. **Remove event subscriptions** (`_subscribe_events()` in `pm_core_tick.py`)
   - They're broken, redundant, and causing excessive runs
   - Scheduled runs already handle the same data

2. **Fix scheduler timing**
   - Move Geometry Builder from :07 to :05 (before PM Core Tick at :06)
   - Ensures PM Core Tick uses fresh geometry data

3. **Simplify tracker.py**
   - Remove `phase_state` (PORTFOLIO) writes - not used
   - Remove `portfolio_context` writes - not used
   - Keep `phase_state_bucket` writes - used for bucket ordering

### Future Considerations

1. **Geometry Tracker**
   - Currently disabled (`GEOMETRY_TRACKER_ENABLED=0`)
   - If enabled, it would update break flags every 5 minutes
   - Consider if this is needed or if hourly Geometry Builder is sufficient

2. **Event System**
   - If immediate response is needed in the future, fix the event handlers properly:
     - Only subscribe once (not per timeframe)
     - Pass correct timeframe to handlers
     - Add logging
   - Otherwise, rely on scheduled runs

3. **Phase State Cleanup**
   - `phase_state` table (PORTFOLIO) is no longer used
   - Can be deprecated/removed after confirming no other systems use it

---

## 8. Files to Modify

### High Priority

1. `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`
   - Remove `_subscribe_events()` function (lines 2954-2990)
   - Remove call to `_subscribe_events()` in `main()` (line 3002)

2. `src/run_trade.py`
   - Move Geometry Builder from :07 to :05 (lines 729-733)

### Medium Priority

3. `src/intelligence/lowcap_portfolio_manager/jobs/tracker.py`
   - Remove `phase_state` (PORTFOLIO) writes (lines 218-261)
   - Remove `portfolio_context` writes (lines 327-387)
   - Keep `phase_state_bucket` writes (lines 268-325)
   - Keep geometry tracker (lines 389-686) - optional, currently disabled

### Low Priority

4. Documentation cleanup
   - Update docs to reflect that events are not used
   - Document correct scheduler timing

---

## 9. Testing Checklist

After making changes:

1. **Verify PM Core Tick 1h runs hourly only**
   - Check `pm_core.log` - should see runs at :06 only
   - Check `ad_strands` - should not see `emergency_exit` actions every 12-15 seconds

2. **Verify Geometry Builder runs before PM Core Tick**
   - Check logs - Geometry Builder at :05, PM Core Tick at :06
   - Verify PM Core Tick reads fresh geometry data

3. **Verify bucket ordering still works**
   - Check that `phase_state_bucket` is still written by Tracker
   - Verify `fetch_bucket_phase_snapshot()` still works
   - Confirm bucket multipliers in `compute_levers()` still function

4. **Verify no regressions**
   - PM Core Tick should still process positions correctly
   - Actions should still be planned and executed
   - Strands should still be written

---

## 10. Questions for Discussion

1. **Geometry Tracker**: Should we enable it? It would update break flags every 5 minutes instead of hourly.

2. **Event Latency**: Is up to 1 hour delay acceptable for 1h timeframe positions? Or do we need immediate response for critical events?

3. **Phase State**: Can we fully remove `phase_state` table (PORTFOLIO) or are there other systems using it?

4. **Portfolio Context**: Was `portfolio_context` intended for future use, or is it truly dead code?

---

## Appendix: Key Code Locations

### Event Handlers
- `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py:2954-2990` - `_subscribe_events()`
- `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py:3002` - Call to `_subscribe_events()`
- `src/intelligence/lowcap_portfolio_manager/events/bus.py` - Event bus implementation

### Scheduler
- `src/run_trade.py:696-744` - All scheduler definitions

### Geometry System
- `src/intelligence/lowcap_portfolio_manager/jobs/geometry_build_daily.py` - Geometry Builder
- `src/intelligence/lowcap_portfolio_manager/jobs/tracker.py:389-686` - Geometry Tracker

### Tracker
- `src/intelligence/lowcap_portfolio_manager/jobs/tracker.py` - Main tracker file
- `src/intelligence/lowcap_portfolio_manager/regime/bucket_context.py` - Bucket context fetcher

### PM Core Tick
- `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py` - Main PM Core Tick
- `src/intelligence/lowcap_portfolio_manager/pm/actions.py` - Action planning (uses geometry)

---

**End of Summary**

