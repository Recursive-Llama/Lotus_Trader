# System Architecture: How PM Core Ticks & Uptrend Engine Work

## Overview

The system has two main components that work together:
1. **Uptrend Engine**: Detects market state (S0-S4), computes scores, sets flags
2. **PM Core Tick**: Reads flags, makes trading decisions, creates actions/strands

---

## 1. Uptrend Engine: What It Does

### Purpose
- **Detects state** using EMA hierarchy (S0, S1, S2, S3, S4)
- **Computes scores** (TS, OX, DX, EDX) for decision-making
- **Sets flags** (`buy_flag`, `first_dip_buy_flag`, `emergency_exit`, etc.)
- **Writes to database**: Updates `features.uptrend_engine_v4` with current state

### What Triggers It

**Scheduled Runs** (Primary):
- **15m**: Every 15 minutes at :00, :15, :30, :45 (aligned)
- **1h**: Every hour at :06 (aligned)
- **1m**: Every 1 minute (interval)
- **4h**: Every 4 hours at :00 (aligned)

**Immediate Triggers** (Secondary):
- **When new position is created**: Decision Maker triggers engine immediately after backfilling data
  - Location: `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py:909-926`
  - This is why we see standalone runs at 18:18:57 (3 minutes after scheduled pipeline)

### How It Works

```python
def run(self, include_regime_drivers: bool = False) -> int:
    # 1. Get all active positions for this timeframe
    positions = self._active_positions(include_regime_drivers=include_regime_drivers)
    
    # 2. For each position:
    for p in positions:
        # 3. Read previous state from features.uptrend_engine_v4
        prev_state = prev_payload.get("prev_state") or prev_payload.get("state")
        
        # 4. Get latest OHLC bar timestamp
        current_ts = last.get("ts")  # From _latest_close_1h()
        
        # 5. Check EMA order to determine new state
        if prev_state == "S3":
            # Stay in S3: Compute scores, check first-dip buy
            s3_scores = self._compute_s3_scores(...)
            first_dip_check = self._check_first_dip_buy(...)
            first_dip_buy_flag = first_dip_check.get("first_dip_buy_flag", False)
            
            # 6. Build payload with flags
            extra_data = {
                "first_dip_buy_flag": first_dip_buy_flag,
                "buy_flag": dx_buy_ok,
                ...
            }
            
        # 7. Write to database
        features["uptrend_engine_v4"] = payload
        self._write_features(pid, features)
```

**Key Point**: Engine **only writes flags to database**. It does NOT create actions or execute trades.

---

## 2. PM Core Tick: What It Does

### Purpose
- **Reads flags** from `features.uptrend_engine_v4`
- **Makes trading decisions** using `plan_actions_v4()`
- **Creates actions/strands** (entry, add, trim, exit)
- **Executes actions** via PM Executor (if enabled)

### What Triggers It

**Scheduled Runs Only** (No immediate triggers):
- **15m**: Every 15 minutes at :00, :15, :30, :45 (aligned)
- **1h**: Every hour at :06 (aligned)
- **1m**: Every 1 minute (interval)
- **4h**: Every 4 hours at :00 (aligned)

**Key Point**: PM Core **only runs on schedule**. It does NOT run when engine sets flags.

### How It Works

```python
def run(self) -> int:
    # 1. Get all active positions for this timeframe
    positions = self._active_positions()
    
    # 2. For each position:
    for p in positions:
        # 3. Read flags from features.uptrend_engine_v4
        uptrend = features.get("uptrend_engine_v4") or {}
        first_dip_buy_flag = uptrend.get("first_dip_buy_flag", False)
        buy_flag = uptrend.get("buy_flag", False)
        
        # 4. Compute A/E scores (regime-driven aggressiveness/exit assertiveness)
        le = compute_levers(...)
        a_final = le["A_value"]
        e_final = le["E_value"]
        
        # 5. Make trading decisions
        actions = plan_actions_v4(
            p, a_final, e_final, regime_state_str, self.sb,
            ...
        )
        
        # 6. Execute actions (create strands, trigger executor)
        for act in actions:
            # Create strand in database
            # Trigger PM Executor to execute trade
```

**Key Point**: PM Core **only reads flags that exist at the time it runs**. If engine sets a flag between scheduled runs, PM Core misses it.

---

## 3. The Pipeline Flow (15m Example)

### Scheduled Pipeline (Every 15 minutes at :00, :15, :30, :45)

```
18:15:00 - Rollup 15m
  └─> Creates new 15m OHLC bars (17:15:00 boundary)

18:15:01 - TA Tracker 15m
  └─> Computes technical indicators (EMAs, ATR, etc.)

18:15:02 - Uptrend Engine 15m
  └─> Detects state, computes scores, sets flags
  └─> Writes to features.uptrend_engine_v4

18:15:03 - PM Core Tick 15m
  └─> Reads flags from features.uptrend_engine_v4
  └─> Makes decisions, creates actions/strands
  └─> Executes trades (if enabled)
```

**This is the normal flow - everything runs sequentially in the same pipeline.**

---

## 4. The Problem: Standalone Engine Runs

### What Happens

**Scenario**: New position created at 18:18:00

```
18:18:00 - Decision Maker creates position
  └─> Backfills OHLC data
  └─> **Immediately triggers TA Tracker + Uptrend Engine** (line 909-926)
      └─> Engine runs at 18:18:57
      └─> Sets first_dip_buy_flag=True at 18:19:41
      └─> **But PM Core already ran at 18:15:36!**
      └─> Next PM Core run is at 18:30:00 (10 minutes later)
      └─> Flag is stale by then, no action created
```

**The Issue**: Engine runs immediately when position is created, but PM Core only runs on schedule.

---

## 5. Why This Is Only An Issue On First Candle?

### First Candle Scenario

When a position is first created:
1. Decision Maker backfills data
2. **Immediately triggers engine** (to bootstrap state)
3. Engine may set `first_dip_buy_flag=True` immediately
4. But PM Core won't run until next scheduled tick (up to 15 minutes later)

**After first candle**:
- Position is already in database
- Engine only runs on schedule (no immediate triggers)
- PM Core and Engine run in same pipeline
- **No timing gap!**

### Why It's Not Always An Issue

- **Normal operation**: Engine and PM Core run in same pipeline → no gap
- **First candle only**: Engine runs immediately → PM Core runs later → gap

---

## 6. Why FACY Didn't Trigger Before Catch-Up

### Timeline Analysis

**Dec 9 (Previous Day)**:
- 19:15:04 - FACY at `bars_since_s3=3` - **First dip buy TRIGGERED** ✅
- 19:45:17 - FACY at `bars_since_s3=3` - **First dip buy TRIGGERED** ✅
- But no execution (PM Core may have blocked it)

**Dec 10 (Current Day)**:
- 16:30:00 - FACY entered S3 (new S3 entry)
- 18:21:14 - `bars_since_s3=0, current_ts=16:30:00` (stuck!)
- 18:22:14 - `bars_since_s3=0, current_ts=16:30:00` (still stuck)
- ... (stuck for 35+ minutes)
- 19:00:05 - `bars_since_s3=5, current_ts=17:45:00` (finally advanced)
- 19:30:07 - `bars_since_s3=6, current_ts=18:00:00` (at boundary)

### What Blocked It

**Before catch-up (bars stuck at 0)**:
- `bars_since_s3=0` is within first-dip window (0-6 for option 1, 0-12 for option 2)
- But `current_ts` was stuck at 16:30:00 (no new 15m bars)
- Engine kept checking, but conditions may not have been met:
  - Price not within 0.5*ATR of EMA20/30/60
  - TS + S/R boost < 0.50
  - Slope not OK
  - Price < EMA333 (emergency exit)

**After catch-up (bars advanced to 5-7)**:
- Bars finally advanced, but window may have expired
- At bar 6: Still within option 1 window (<= 6), but conditions not met
- At bar 7: Outside option 1 window, still within option 2 (<= 12), but conditions not met

### Why No "First dip buy TRIGGERED" Logs

The engine logs show:
- Dec 9: Multiple "First dip buy TRIGGERED" logs (bars=3)
- Dec 10: **No "First dip buy TRIGGERED" logs** (bars stuck, then window expired)

**Conclusion**: FACY's first-dip buy conditions were **never met** on Dec 10:
1. When bars were stuck (0), conditions weren't met
2. When bars advanced (5-7), window expired or conditions still not met

---

## 7. Options for Fixing

### Option 1: Immediate PM Core Trigger (Recommended)

**When engine sets `first_dip_buy_flag=True`, immediately trigger PM Core for that position.**

Pros:
- No missed signals
- Works even with standalone engine runs
- Immediate execution

Cons:
- More complex coordination
- Potential for duplicate runs if scheduled tick also fires

**Implementation**:
```python
# In uptrend_engine_v4.py, after setting first_dip_buy_flag=True:
if first_dip_buy_flag:
    # Trigger PM Core immediately for this position
    from intelligence.lowcap_portfolio_manager.jobs.pm_core_tick import PMCoreTick
    pm_core = PMCoreTick(timeframe=self.timeframe)
    # Process just this position
    pm_core.process_position(p)
```

### Option 2: Persist Pending Flags

**Store "pending" first-dip buy flags in position metadata, PM Core checks on next tick.**

Pros:
- Simple to implement
- Works with existing schedule
- Flags persist across ticks

Cons:
- Still delayed (up to 15 minutes)
- May execute on stale conditions

### Option 3: Remove Immediate Engine Triggers

**Don't trigger engine immediately when position is created - wait for scheduled run.**

Pros:
- Guaranteed coordination
- Simpler architecture
- No timing gaps

Cons:
- Delayed state detection (up to 15 minutes)
- May miss early signals

### Option 4: Hybrid Approach

**Combine Option 1 + Option 2:**
- Immediate trigger for critical flags (first-dip buy)
- Persist pending flags as backup
- Ensure scheduled pipeline still runs normally

---

## 8. Summary

**How It Works Currently**:
1. Engine runs on schedule (every 15m) + immediately when position created
2. PM Core runs only on schedule (every 15m)
3. Engine sets flags → writes to database
4. PM Core reads flags → makes decisions → executes

**The Problem**:
- Engine can run immediately (when position created)
- PM Core only runs on schedule
- **Timing gap**: Flag set between scheduled runs → PM Core misses it

**Why FACY Didn't Trigger**:
- Bars stuck at 0 for 35+ minutes (no new 15m bars)
- When bars advanced, conditions weren't met OR window expired
- **No "First dip buy TRIGGERED" logs** = conditions never met

**Recommended Fix**:
- Immediate PM Core trigger when engine sets `first_dip_buy_flag=True`
- Or persist pending flags for next scheduled tick

