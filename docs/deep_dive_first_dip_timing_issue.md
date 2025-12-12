# Deep Dive: First-Dip Buy Timing & Coordination Issues

## Executive Summary

**Root Cause**: Timing/coordination gap between Uptrend Engine and PM Core, plus delayed 15m bar rollups causing `bars_since_s3` to be stuck.

**Impact**: 
- LASHI 15m: First-dip buy flagged but never executed (timing gap)
- FACY 15m: First-dip buy never triggered (bars stuck, then window expired)
- 15m bars delayed by 1+ hours (rollup catch-up running late)

---

## 1. System Architecture & Scheduling

### Current Pipeline Flow (15m timeframe)

```
Every 15 minutes at :00, :15, :30, :45:
1. Rollup 15m (creates new 15m OHLC bars)
2. TA Tracker 15m (computes technical indicators)
3. Uptrend Engine 15m (detects state, computes scores, sets flags)
4. PM Core 15m (reads flags, creates actions/strands)
```

**Scheduler Configuration** (`src/run_trade.py:774`):
```python
tasks.append(asyncio.create_task(self._schedule_aligned(15, 0, 
    lambda: self._wrap_ta_then_uptrend_then_pm("15m"), 
    "TA→Uptrend→PM 15m")))
```

**Key Point**: All components run sequentially in the same pipeline, but only at 15-minute boundaries.

---

## 2. LASHI 15m First-Dip Buy Failure

### Timeline

| Time | Event | Status |
|------|-------|--------|
| 18:15:04 | Rollup 15m started | ✅ |
| 18:15:36 | TA→Uptrend→PM 15m completed | ✅ PM Core ran here |
| 18:18:57 | **Engine standalone run** - LASHI entered S3 (Bootstrap→S3) | ⚠️ Outside pipeline |
| 18:19:41 | **Engine standalone run** - First-dip buy TRIGGERED | ⚠️ Flag set, but PM Core already ran |
| 18:30:00 | Next scheduled PM Core run | ❌ Flag stale by then |

### Root Cause

**The engine is running standalone runs outside the scheduled pipeline.**

Evidence:
- Engine log at 18:18:57: `Processing position: 6m6TjSDEbbpcEYEyvb2ksdRd9CFYENRU6yAZ4J7jpump/solana (timeframe=15m, status=watchlist, prev_state=(none))`
- This is **3 minutes after** the scheduled pipeline completed
- The engine is being called from somewhere else (possibly 1m pipeline or manual trigger)

### Why It Failed

1. Engine set `first_dip_buy_flag=True` at 18:19:41
2. PM Core had already run at 18:15:36 (before the flag was set)
3. Next PM Core run was at 18:30:00 (10 minutes later)
4. By 18:30:00, the flag may have been stale or conditions changed
5. **No action was created, no strand was written**

### Current State

- `first_dip_buy_taken: True` (flag was set and marked as taken)
- `total_quantity: 0` (no tokens were bought)
- `last_s3_buy: None` (no execution history)
- **0 strands created**

---

## 3. FACY 15m First-Dip Buy Never Triggered

### Timeline

| Time | Event | bars_since_s3 | Status |
|------|-------|---------------|--------|
| 16:30:00 | FACY entered S3 | 0 | ✅ |
| 18:21:14 - 18:56:14 | Multiple engine runs | **0 (stuck!)** | ❌ `current_ts` stuck at 16:30:00 |
| 19:00:05 | Bars finally advanced | 5 | ✅ Rollup caught up |
| 19:30:07 | Current state | 6 | ⚠️ At boundary for option 1 (0-6 bars) |
| 19:45:07 | Current state | 7 | ❌ Outside option 1 window |

### Root Cause

**15m bars were delayed by 1+ hours, causing `bars_since_s3` to be stuck at 0.**

Evidence:
- FACY entered S3 at 16:30:00
- `current_ts` stayed at 16:30:00 from 18:21 to 18:56 (35+ minutes)
- Rollup finally created 17:15, 17:30, 17:45, 18:00 bars at 19:02-19:04 (catch-up mechanism)
- First-dip window: bars 0-6 (option 1) or 0-12 (option 2)
- By the time bars advanced, FACY was already at bar 5-7

### Why It Never Triggered

1. **Bars stuck**: `bars_since_s3=0` for 35+ minutes (no new 15m bars)
2. **Window expired**: When bars finally advanced, FACY was at bar 5-7
3. **Conditions not met**: Even at bar 6, price/EMA/TS/slope conditions may not have been met
4. **No flag set**: `first_dip_buy_flag: False` in current state

### Current State

- `first_dip_buy_taken: None` (never triggered)
- `first_dip_buy_flag: False` (conditions not met)
- `bars_since_s3: 7` (outside option 1 window, still within option 2)
- **Window may have expired or conditions never met**

---

## 4. Why 15m Bars Took So Long to Update

### Rollup Schedule

**Normal Rollup** (scheduled at :00, :15, :30, :45):
- 18:15:04 - Rollup for 17:15:00 boundary ✅
- 18:30:00 - Rollup for 17:30:00 boundary ✅
- 19:00:00 - Rollup for 18:00:00 boundary ✅

**Catch-Up Mechanism** (runs hourly at :02):
- 19:02:00 - Catch-up started
- 19:02:40 - **Rolling up 17:15:00 boundary** (47 minutes late!)
- 19:02:53 - **Rolling up 17:30:00 boundary** (32 minutes late!)

### Root Cause

**The catch-up mechanism is filling gaps from earlier boundaries that were missed.**

Evidence:
- Normal rollup at 18:15 created 17:15 bar ✅
- Normal rollup at 18:30 created 17:30 bar ✅
- But catch-up at 19:02 is **re-rolling 17:15 and 17:30** boundaries

**Possible reasons**:
1. Rollup job failed/crashed earlier and catch-up is filling gaps
2. Rollup job ran but didn't create bars for all tokens (insufficient 1m data)
3. Catch-up is being too aggressive and re-processing boundaries

### Impact

- `current_ts` stuck at old timestamps (16:30:00, 17:15:00, etc.)
- `bars_since_s3` stuck at 0 for extended periods
- First-dip buy windows expire before bars advance
- Engine keeps processing stale data

---

## 5. What We're Overlooking

### A. Engine Running Standalone

**Issue**: Engine is being called outside the scheduled pipeline.

**Possible sources**:
1. 1m pipeline may be triggering 15m engine runs
2. Manual/CLI calls to engine
3. Other systems calling engine directly

**Fix needed**: 
- Ensure engine only runs within scheduled pipeline
- Or ensure PM Core re-checks flags on next tick even if set between ticks

### B. PM Core Only Runs on Schedule

**Issue**: PM Core only processes flags at 15-minute boundaries.

**Problem**: If engine sets a flag between scheduled runs, PM Core misses it.

**Fix options**:
1. **Option 1**: Have engine trigger PM Core immediately when critical flags are set
2. **Option 2**: Have PM Core re-check flags from last tick on each run
3. **Option 3**: Ensure engine only runs within pipeline (no standalone runs)

### C. Rollup Catch-Up Too Aggressive

**Issue**: Catch-up is re-processing boundaries that were already rolled up.

**Problem**: Creates duplicate work and delays new boundaries.

**Fix needed**:
- Improve catch-up logic to skip boundaries that already have bars
- Better detection of which tokens need catch-up vs. which are just missing 1m data

### D. No Persistence of "Pending" Flags

**Issue**: Flags set between PM Core runs are lost if conditions change.

**Problem**: First-dip buy flag set at 18:19:41, but by 18:30:00 conditions may have changed.

**Fix needed**:
- Persist "pending" first-dip buy flags in position metadata
- PM Core checks pending flags even if current conditions don't meet threshold

---

## 6. Options & Recommendations

### Option 1: Immediate PM Core Trigger (Recommended)

**When engine sets `first_dip_buy_flag=True`, immediately trigger PM Core for that position.**

Pros:
- No missed signals
- Immediate execution
- Works even with standalone engine runs

Cons:
- More complex coordination
- Potential for duplicate runs if scheduled tick also fires

### Option 2: Persist Pending Flags

**Store "pending" first-dip buy flags in position metadata, PM Core checks on next tick.**

Pros:
- Simple to implement
- Works with existing schedule
- Flags persist across ticks

Cons:
- Still delayed (up to 15 minutes)
- May execute on stale conditions

### Option 3: Ensure Engine Only Runs in Pipeline

**Remove standalone engine runs, ensure all runs are within scheduled pipeline.**

Pros:
- Guaranteed coordination
- Simpler architecture
- No timing gaps

Cons:
- May miss real-time signals
- Need to find and remove standalone calls

### Option 4: Hybrid Approach

**Combine Option 1 + Option 2:**
- Immediate trigger for critical flags (first-dip buy)
- Persist pending flags as backup
- Ensure scheduled pipeline still runs normally

---

## 7. Immediate Actions Needed

1. **Investigate standalone engine runs**: Find why engine runs at 18:18:57 outside pipeline
2. **Fix rollup catch-up**: Ensure it doesn't re-process boundaries that already have bars
3. **Add flag persistence**: Store pending first-dip buy flags in metadata
4. **Add immediate PM Core trigger**: When first-dip buy flag is set, trigger PM Core immediately
5. **Improve logging**: Add INFO-level logs for all first-dip buy checks (not just triggers/blocks)

---

## 8. FACY Deep Dive: Why It Didn't Trigger

### Current Conditions Check

FACY is at `bars_since_s3=7`:
- **Option 1**: Requires bars <= 6 ❌ (FACY is at 7)
- **Option 2**: Requires bars <= 12 ✅ (FACY is at 7, still valid)

**But `first_dip_buy_flag: False`**, so conditions weren't met even for option 2.

**Possible reasons**:
1. Price not within 0.5*ATR of EMA60 (option 2 requirement)
2. TS + S/R boost < 0.50 (required threshold)
3. Slope not OK (EMA144_slope <= 0.0 AND EMA250_slope < 0.0)
4. Price < EMA333 (emergency exit territory)

**Conclusion**: FACY's first-dip buy was **correctly not triggered** - conditions weren't met. The issue was the delayed bars preventing it from being evaluated earlier when conditions might have been met.

---

## 9. Summary

**LASHI**: Timing gap - flag set after PM Core ran, never processed.

**FACY**: Delayed bars - stuck at bar 0 for 35+ minutes, window expired before conditions could be evaluated.

**15m Bars**: Catch-up mechanism re-processing old boundaries, causing delays.

**Root Issues**:
1. Engine running standalone outside pipeline
2. PM Core only runs on schedule (misses between-tick flags)
3. Rollup catch-up too aggressive/re-processing boundaries
4. No persistence of pending flags

**Recommended Fix**: Immediate PM Core trigger + flag persistence + fix rollup catch-up logic.

