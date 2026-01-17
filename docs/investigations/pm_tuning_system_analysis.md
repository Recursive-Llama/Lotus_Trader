# PM Tuning System Analysis

**Date**: 2025-01-XX  
**Purpose**: Deep dive into PM Tuning system - what it does, current state, what's working, what's not

---

## System Overview

The PM Tuning system adjusts **thresholds** (TS, SR, halo, slope guards, DX suppression) based on historical win/miss rates. It's separate from PM Strength (which adjusts sizing).

### Flow

```
Episode Events → TuningMiner → Learning Lessons → Override Materializer → PM Overrides
```

1. **Episode Events** (`pattern_episode_events`): Logs opportunities (S1 entry, S2 entry, S3 retest) with decisions (acted/skipped) and outcomes (success/failure)
2. **TuningMiner**: Mines patterns, calculates rates (WR, FPR, MR, DR), writes to `learning_lessons`
3. **Override Materializer**: Filters actionable lessons, converts to threshold multipliers, writes to `pm_overrides`
4. **PM Runtime**: Reads `pm_overrides` and applies threshold adjustments

---

## Current Database State

### Pattern Episode Events

- **Total**: 276 events
- **With Outcomes**: 104 events (ready for mining)
- **Pending**: 170 events (waiting for episode outcomes)

**By Pattern**:
- `module=pm|pattern_key=uptrend.S1.entry`: 274 total, 104 with outcomes ✅ (passes N_MIN=33)
- `module=pm|pattern_key=uptrend.S1.buy_flag`: 2 total, 0 with outcomes ⚠️

**Key Finding**: Main pattern has 104 events with outcomes, which is >33, so should create lessons.

### Scope Distribution (S1.entry pattern)

All 104 events share most scope values:
- `chain`: solana (104)
- `timeframe`: 15m=57, 1m=46, 1h=1
- `bucket`: micro=55, nano=32, mid=13, big=2, large=2

**Scope Slicing Impact**:
- Global slice (all 104): ✅ Would create lesson
- `timeframe=15m` (57 events): ✅ Would create lesson
- `timeframe=1m` (46 events): ✅ Would create lesson
- `timeframe=1h` (1 event): ❌ Pruned (<33)
- `bucket=micro` (55 events): ✅ Would create lesson
- `bucket=nano` (32 events): ⚠️ Just below threshold

### Learning Lessons

- **Current**: 0 lessons found
- **Expected**: Should have at least 1 lesson (global slice for S1.entry)

**Problem**: TuningMiner logic shows it SHOULD create lessons, but none exist. Possible causes:
1. TuningMiner hasn't run
2. TuningMiner ran but failed silently
3. Pattern key format mismatch (see below)

### PM Overrides

- **Current**: 0 overrides
- **Expected**: 0 (no lessons to materialize)

---

## Critical Issues

### 🚨 Issue #1: Pattern Key Format Mismatch

**Problem**: 
- Episode events use: `module=pm|pattern_key=uptrend.S1.entry`
- TuningMiner expects: `pm.uptrend.S1.entry` (based on `DX_PATTERN_KEYS` and `S2_PATTERN_KEYS`)

**Impact**: 
- TuningMiner groups by `pattern_key`, so it will group correctly
- But the pattern key format is inconsistent across the system

**Evidence**:
```python
# tuning_miner.py
self.DX_PATTERN_KEYS = {"pm.uptrend.S3.dx"}
self.S2_PATTERN_KEYS = {"pm.uptrend.S2.buy_flag", "pm.uptrend.S2.entry"}

# But episode events have:
pattern_key = "module=pm|pattern_key=uptrend.S1.entry"
```

### 🚨 Issue #2: TuningMiner Is NOT Scheduled

**Evidence**: 
- Logic shows we should have lessons (104 events > 33)
- But 0 lessons exist
- **TuningMiner is NOT scheduled in `run_social_trading.py` or `run_trade.py`**
- Only `lesson_builder_job('pm')` is scheduled (for PM Strength, not Tuning)
- Override Materializer is scheduled but has nothing to materialize

**Impact**: 
- TuningMiner never runs → no tuning lessons created → no tuning overrides
- System is collecting episode data but not learning from it

### 🚨 Issue #3: N_MIN=33 May Be Too High

**Current State**:
- Main pattern: 104 events ✅ (passes)
- But scope slices:
  - `bucket=nano`: 32 events ⚠️ (just below)
  - `timeframe=1h`: 1 event ❌ (way below)
  - `bucket_rank_position=1`: 29 events ⚠️ (below)
  - `bucket_rank_position=3`: 30 events ⚠️ (below)

**Impact**: Many valid scope slices are pruned, reducing learning granularity.

**Consideration**: Reducing N_MIN would allow more granular learning but requires investigation of statistical significance.

---

## How The System Works

### 1. Episode Event Logging

**Location**: `pm_core_tick.py::_log_episode_event()`

**When**:
- S1 Entry: State transition `S2 → S1` (retest phase)
- S2 Entry: State transition `S1 → S2` (first time)
- S3 Retest: State transition to `S3`

**What's Logged**:
- `pattern_key`: e.g., `module=pm|pattern_key=uptrend.S1.entry`
- `decision`: `acted` or `skipped`
- `factors`: Signal values at decision time (TS, DX, halo, etc.)
- `outcome`: `success`, `failure`, or `null` (pending)

**Outcome Updates**:
- Updated when episode ends (success/failure determined)
- Location: `pm_core_tick.py::_update_episode_outcome()`

### 2. TuningMiner

**Location**: `tuning_miner.py`

**Process**:
1. Fetch events with outcomes (last 90 days)
2. Recursive Apriori mining:
   - Start with global slice (all events for pattern)
   - Recursively add scope dimensions
   - Prune slices with n < N_MIN
3. Calculate rates for each slice:
   - **WR** (Win Rate): `success_acted / acted`
   - **FPR** (False Positive Rate): `failure_acted / acted`
   - **MR** (Miss Rate): `success_skipped / skipped`
   - **DR** (Dodge Rate): `failure_skipped / skipped`
4. Write to `learning_lessons` with `lesson_type='tuning_rates'`

**Special Cases**:
- **DX Ladder Tuning**: Uses `dx_count` distribution on successful recoveries
- **S2 Tuning**: Uses same levers as S1 (halo, ts_min, slope guards)

### 3. Override Materializer

**Location**: `override_materializer.py::materialize_tuning_overrides()`

**Process**:
1. Read `learning_lessons` with `lesson_type='tuning_rates'`
2. Calculate **pressure**: `n_misses - n_fps`
   - Positive pressure → Too many misses → Loosen thresholds
   - Negative pressure → Too many FPs → Tighten thresholds
3. Calculate multipliers:
   - `mult_threshold = exp(-ETA * pressure)` (for TS, DX)
   - `mult_halo = exp(+ETA * pressure)` (for halo distance)
4. Write to `pm_overrides` with `action_category`:
   - `tuning_ts_min` (S1, S3)
   - `tuning_s2_ts_min` (S2)
   - `tuning_halo` (S1)
   - `tuning_s2_halo` (S2)
   - `tuning_dx_min` (S3)
   - `tuning_dx_atr_mult` (DX ladder)

### 4. PM Runtime Application

**Location**: `overrides.py` (called from PM Executor)

**Process**:
1. Read `pm_overrides` matching current pattern/scope
2. Apply multipliers to threshold calculations
3. Adjust entry/exit gates accordingly

---

## Patterns We Have

### Current Patterns (with outcomes)

1. **S1 Entry** (`module=pm|pattern_key=uptrend.S1.entry`):
   - 104 events with outcomes
   - 7 acted (2 success, 5 failure) → WR=28.6%, FPR=71.4%
   - 97 skipped (8 success, 89 failure) → MR=8.2%, DR=91.8%
   - **Pressure**: 8 misses - 5 FPs = +3 (slight pressure to loosen)

### Patterns Close to Threshold

- `bucket=nano`: 32 events (need 1 more)
- `bucket_rank_position=1`: 29 events (need 4 more)
- `bucket_rank_position=3`: 30 events (need 3 more)

---

## What's Working

✅ Episode event logging is working (276 events logged)  
✅ Outcome updates are happening (104 events have outcomes)  
✅ Data quality is good (sufficient events for main pattern)  
✅ Scope slicing logic is sound (would create multiple lessons)

## What's Not Working

❌ **TuningMiner not creating lessons** (0 lessons despite 104 events)  
❌ **Pattern key format inconsistency** (may cause matching issues)  
❌ **N_MIN=33 may be too high** (prunes valid scope slices)  
❌ **No overrides** (expected, but blocked by missing lessons)

---

## Next Steps

1. **Schedule TuningMiner**
   - Add TuningMiner to scheduler (e.g., hourly at :09, after Lesson Builder)
   - Test run manually first to verify it creates lessons
   - Verify pattern key matching works correctly

2. **Investigate N_MIN threshold**
   - Analyze statistical significance at lower N values
   - Consider reducing N_MIN (e.g., to 20 or 25)
   - Evaluate impact on learning granularity

3. **Fix pattern key format consistency**
   - Standardize pattern key format across system
   - Update TuningMiner pattern key checks if needed

4. **Test full flow**
   - Run TuningMiner → verify lessons created
   - Run Override Materializer → verify overrides created
   - Test PM runtime application of overrides

---

## Key Insights

1. **We have enough data** (104 events > 33) but lessons aren't being created
2. **Scope slicing would create multiple lessons** (global + timeframe slices)
3. **N_MIN=33 is borderline** - many scope slices are just below threshold
4. **System architecture is sound** - the flow makes sense, just needs to be triggered/fixed

