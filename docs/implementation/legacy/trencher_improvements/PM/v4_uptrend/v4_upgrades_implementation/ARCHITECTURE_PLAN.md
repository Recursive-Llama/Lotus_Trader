# Uptrend Engine v4 + Portfolio Manager Integration Plan

## Overview

This document outlines the integration plan for three major areas:
1. **Multi-Timeframe Support**: Dynamic timeframe selection + multi-timeframe analysis
2. **Portfolio Manager Integration**: Wire Uptrend Engine v4 into PM decision-making
3. **System Integration**: End-to-end data flow and module communication

---

## 1. TIMEFRAMES

### Current State
- **Hardcoded 1h**: All modules (uptrend engine, TA tracker, backfill) use `timeframe='1h'`
- **Token age limitation**: Tokens < 14 days old don't have enough 1h bars
- **TIMEFRAMES_AGNOSTIC_PLAN.md**: Outdated - only handles single timeframe selection

### Requirements
1. **Dynamic timeframe selection** for newer tokens:
   - <24 hours old → 1m timeframe
   - <3 days old → 5m timeframe
   - <7 days old → 15m timeframe
   - 14+ days old → 1h timeframe (current)

2. **Multi-timeframe analysis** for ALL tokens:
   - Run uptrend engine on multiple timeframes simultaneously
   - Each timeframe = independent cycle analysis
   - Same chart behavior, different time scales
   - **No aggregation needed** - each timeframe gives different signals independently
   - Can overlap (e.g., 1h + 15m + 5m for same token)

### Architecture Decisions

#### A. Geometry - Timeframe Dependent (Confirmed)
- Each timeframe has its own geometry/S/R levels
- More accurate for cycle-specific support/resistance
- Geometry is cycle-specific, so timeframe-dependent is correct

#### B. TA Storage Strategy - Dynamic Suffix (Confirmed)
- Store as `ema20_1h`, `ema20_5m`, `ema20_15m`, etc.
- Each timeframe tracked separately
- Engine reads specific timeframe suffix
- Simple and straightforward - just extra database columns

#### C. Timeframe Selection
**For Newer Tokens (Dynamic)**:
```python
def get_timeframe_for_token_age(age_hours: float) -> str:
    """Select primary timeframe based on token age."""
    if age_hours >= 336:  # 14 days
        return '1h'
    elif age_hours >= 168:  # 7 days
        return '15m'
    elif age_hours >= 72:  # 3 days
        return '5m'
    else:
        return '1m'
```

**For Multi-Timeframe (All Tokens)**:
- Run engine multiple times for same token with different timeframes
- Store results separately: `features.uptrend_engine_v4_1h`, `features.uptrend_engine_v4_5m`, etc.
- **No aggregation needed** - each timeframe provides independent signals
- PM can read primary timeframe (or multiple timeframes if needed)
- Simple approach: just extra TA/Geometry/Engine runs, extra DB columns

### Implementation Plan

#### Phase 1: Backfill Updates
- Update `geckoterminal_backfill.py`:
  - Add `timeframe` parameter (defaults to '1h' for backward compat)
  - Map timeframe to GeckoTerminal endpoint
  - Store with correct `timeframe` field in database

#### Phase 2: TA Tracker Updates
- Update `ta_tracker.py`:
  - Accept `timeframe` parameter
  - Store TA with dynamic suffix: `ema20_{timeframe}`
  - Can run multiple times for different timeframes
  - Just extra columns, not big module changes

#### Phase 3: Geometry Updates
- Update `geometry_build_daily.py`:
  - Accept `timeframe` parameter
  - Build geometry per timeframe
  - Store as `features.geometry_1h`, `features.geometry_5m`, etc.
  - Just extra runs, extra columns

#### Phase 4: Uptrend Engine Updates
- Update `uptrend_engine_v4.py`:
  - Add `timeframe` parameter to `__init__()`
  - Replace all `_1h` suffix references with dynamic suffix
  - Update `_calculate_window_boundaries()` to use timeframe-specific seconds
  - Update all OHLC queries to filter by `timeframe`
  - Store results per timeframe: `features.uptrend_engine_v4_1h`, `features.uptrend_engine_v4_5m`, etc.

#### Phase 5: Price Tracking Updates
- Update ongoing price tracking (5m OHLCV):
  - Already supports multiple timeframes in database
  - Just ensure correct timeframe is being tracked

#### Phase 6: Backtester Updates
- Update `backtest_uptrend_v4.py`:
  - Determine timeframe based on token age
  - Pass timeframe to engine
  - Update all queries to use timeframe

### Data Management
- **Storage**: Database already supports multiple timeframes (has `timeframe` column)
- **Backfill**: Run backfill for each required timeframe
- **TA Calculation**: Run TA tracker per timeframe (extra runs, extra columns)
- **Geometry**: Run geometry builder per timeframe (extra runs, extra columns)
- **Engine**: Run engine per timeframe (extra runs, extra columns)
- **PM**: Read primary timeframe (or multiple if needed)
- **No aggregation needed** - each timeframe is independent

---

## 2. PORTFOLIO MANAGER INTEGRATION

### Current State Analysis

#### What's Working:
1. **A/E Scores**: `compute_levers()` correctly computes continuous A/E with:
   - Global components (phase, cut pressure)
   - Per-token components (intent, age, market cap)
   - Continuous position sizing

2. **PM Core Tick**: `pm_core_tick.py`:
   - Computes A/E for each position
   - Calls `plan_actions()` to generate decisions
   - Writes to `ad_strands` table

3. **PM Executor**: `pm/executor.py`:
   - Subscribes to `decision_approved` events
   - Executes PM decisions (add, trim, etc.)
   - Uses idempotency to prevent duplicate executions

#### What's Missing:
1. **Uptrend Engine v4 Integration**: 
   - `plan_actions()` in `actions.py` uses OLD geometry-based logic
   - Does NOT use Uptrend Engine v4 signals (buy_signal, buy_flag, first_dip_buy_flag, etc.)
   - Does NOT use Uptrend Engine v4 states (S1, S2, S3)
   - Does NOT use Uptrend Engine v4 scores (TS, DX, OX, EDX)

2. **Entry/Exit Gates**: 
   - Current `plan_actions()` uses geometry breaks (sr_break, diag_break)
   - Should use Uptrend Engine v4 signals + A/E scores for gating

### Integration Architecture

#### Critical Fix: Payload Structure
**WRONG** (what was in the review):
```python
uptrend = features.get("uptrend_engine_v4") or {}
payload = uptrend.get("payload", {}) or {}  # ❌ WRONG
state = payload.get("state", "")
```

**CORRECT**:
```python
# The payload IS the uptrend_engine_v4 value (stored directly)
uptrend = features.get("uptrend_engine_v4") or {}  # This IS the payload
state = uptrend.get("state", "")
buy_signal = uptrend.get("buy_signal", False)
buy_flag = uptrend.get("buy_flag", False)
# No nested "payload" key!
```

#### New PM Decision Flow:
```python
def plan_actions_v4(position: Dict[str, Any], a_final: float, e_final: float, phase_meso: str) -> List[Dict[str, Any]]:
    """
    New PM action planning using Uptrend Engine v4 signals + A/E scores.
    """
    features = position.get("features") or {}
    uptrend = features.get("uptrend_engine_v4") or {}  # This IS the payload
    
    state = uptrend.get("state", "")
    
    actions = []
    
    # Exit Precedence (highest priority)
    if uptrend.get("exit_position"):
        # Full exit - emergency or structural invalidation
        actions.append({
            "decision_type": "demote",  # Full exit = demote with size_frac: 1.0
            "size_frac": 1.0,
            "reasons": {
                "exit_reason": uptrend.get("exit_reason"),
                "state": state,
            }
        })
        return actions
    
    # Emergency Exit Handling (S3 only)
    # v4 simplified: emergency_exit = full exit (no bounce protocol complexity)
    # Get out faster, rebuy on reclaim - more risk of getting chopped, but less complex
    if state == "S3" and uptrend.get("emergency_exit"):
        # Emergency exit = full exit
        actions.append({
            "decision_type": "demote",  # Full exit = demote with size_frac: 1.0
            "size_frac": 1.0,
            "reasons": {"emergency_exit": True, "e_score": e_final, "state": state}
        })
        return actions
    
    # Trim Flags (S2/S3)
    if uptrend.get("trim_flag"):
        # E-driven trim size
        trim_size = _e_to_trim_size(e_final)
        actions.append({
            "decision_type": "trim",
            "size_frac": trim_size,
            "reasons": {
                "trim_flag": True,
                "state": state,
                "e_score": e_final,
                "ox_score": uptrend.get("scores", {}).get("ox", 0.0),
            }
        })
        return actions
    
    # Entry Gates (S1, S2, S3)
    buy_signal = uptrend.get("buy_signal", False)  # S1
    buy_flag = uptrend.get("buy_flag", False)  # S2 retest or S3 DX
    first_dip_buy_flag = uptrend.get("first_dip_buy_flag", False)  # S3 first dip
    
    if buy_signal or buy_flag or first_dip_buy_flag:
        # A-driven entry size
        entry_size = _a_to_entry_size(a_final, state, buy_signal, buy_flag, first_dip_buy_flag)
        
        if entry_size > 0:
            actions.append({
                "decision_type": "add",
                "size_frac": entry_size,
                "reasons": {
                    "buy_signal": buy_signal,
                    "buy_flag": buy_flag,
                    "first_dip_buy_flag": first_dip_buy_flag,
                    "state": state,
                    "a_score": a_final,
                    "ts_score": uptrend.get("scores", {}).get("ts", 0.0),
                    "dx_score": uptrend.get("scores", {}).get("dx", 0.0),
                }
            })
            return actions
    
    # Reclaimed EMA333 (S3 auto-rebuy)
    if state == "S3" and uptrend.get("reclaimed_ema333"):
        # Auto-rebuy after emergency exit
        rebuy_size = _a_to_entry_size(a_final, state, False, False, False)
        if rebuy_size > 0:
            actions.append({
                "decision_type": "add",
                "size_frac": rebuy_size,
                "reasons": {
                    "reclaimed_ema333": True,
                    "state": state,
                    "a_score": a_final,
                }
            })
            return actions
    
    # Default: Hold
    actions.append({
        "decision_type": "hold",
        "size_frac": 0.0,
        "reasons": {"state": state}
    })
    return actions


def _a_to_entry_size(a_final: float, state: str, buy_signal: bool, buy_flag: bool, first_dip_buy_flag: bool) -> float:
    """
    Convert A score to entry size based on A/E aggressiveness levels.
    
    Position sizing relationship:
    - Aggressive = 100% of allocation total (starts with 50% buy)
    - Normal = 60% of allocation (starts with 30% buy)
    - Patient = 30% of allocation (starts with 10% buy)
    
    A score determines aggressiveness:
    - A >= 0.7: Aggressive (50% initial entry)
    - A >= 0.3: Normal (30% initial entry)
    - A < 0.3: Patient (10% initial entry)
    """
    if a_final >= 0.7:
        # Aggressive: 50% initial entry
        base_size = 0.50
    elif a_final >= 0.3:
        # Normal: 30% initial entry
        base_size = 0.30
    else:
        # Patient: 10% initial entry
        base_size = 0.10
    
    # Adjust by signal type (small adjustments)
    if first_dip_buy_flag:
        # First dip buy: slightly smaller (early entry)
        return base_size * 0.9
    elif buy_signal or buy_flag:
        # S1/S2/S3: full base size
        return base_size
    else:
        return 0.0


def _e_to_trim_size(e_final: float) -> float:
    """
    Convert E score to trim size.
    
    E-driven trim sizes:
    - E >= 0.7: Aggressive (60% trim)
    - E >= 0.3: Normal (30% trim)
    - E < 0.3: Patient (15% trim)
    """
    if e_final >= 0.7:
        return 0.60  # Aggressive
    elif e_final >= 0.3:
        return 0.30  # Normal
    else:
        return 0.15  # Patient
```

### Integration Points

#### 1. PM Core Tick Updates
- `pm_core_tick.py` already calls `plan_actions()` - just need to update `plan_actions()` to use v4 signals
- Ensure Uptrend Engine v4 runs before PM (or PM reads cached state from features)

#### 2. Uptrend Engine v4 Payload Structure
The engine already provides (stored directly in `features.uptrend_engine_v4`):
- `state`: S0, S1, S2, S3, S4
- `buy_signal`: S1 entry
- `buy_flag`: S2 retest or S3 DX buy
- `first_dip_buy_flag`: S3 first dip
- `trim_flag`: S2/S3 trim
- `emergency_exit`: S3 emergency (full exit)
- `reclaimed_ema333`: S3 auto-rebuy
- `exit_position`: Full exit
- `scores`: TS, DX, OX, EDX

#### 3. A/E Score Integration
- A/E scores already computed correctly
- Just need to use them for position sizing and entry/exit gates
- No changes needed to `compute_levers()`

#### 4. Decision Types
- `"add"` - Buy/add position
- `"trim"` - Sell portion
- `"demote"` - Sell 80% (moon-bag) OR full exit (size_frac: 1.0)
- `"hold"` - No action
- `"trend_add"` - Special add (from trend_redeploy)
- **Emergency exit = full exit** = `"demote"` with `size_frac: 1.0`
- **Rest is trims** = `"trim"` with appropriate `size_frac`

### Migration Strategy
1. **Create `plan_actions_v4()`** alongside existing `plan_actions()`
2. **Feature flag**: Use `PLAN_ACTIONS_V4=true` to enable new logic
3. **Parallel run**: Run both, compare outputs
4. **Gradual migration**: Enable for subset of positions first
5. **Full migration**: Switch to v4 once validated

---

## 3. SYSTEM INTEGRATION

### Corrected Data Flow

**Conceptual Dependencies** (data flow):
```
Token Ingest (Social Signals)
  ↓
Decision Maker (Learning System orchestrates)
  ↓
Position Table + max allocation (watchlist table)
  ↓
Backfill + TA + Geometry + Ongoing Price Tracking (5m OHLCV)
  ↓
Uptrend Engine v4 (state machine + signals)
  ↓
PM Core Tick (A/E + actions)
  ↓
PM Executor / Price Monitor (executes actions)
```

**Actual Execution** (parallel schedules, eventual consistency):
- **Position Creation**: Triggers async backfill (non-blocking)
- **TA Tracker**: Runs every 5 minutes (independent schedule)
- **Geometry Builder**: Runs daily at :10 UTC (independent schedule)
- **Uptrend Engine v4**: ⚠️ **MISSING** - needs to be scheduled (every 5 minutes recommended)
- **PM Core Tick**: Runs hourly at :06 UTC (independent schedule)
- **Price Tracking**: Continuous 5m OHLCV collection (independent)

**Key Points**:
- Execution is **parallel/eventual consistency**, not strictly sequential
- Each job runs independently on its schedule
- PM reads whatever is available in `features` (may be incomplete for new positions)
- System is designed to handle missing data gracefully
- **CRITICAL**: Uptrend Engine v4 must be scheduled before PM can use its signals

### Key Components

#### Token Ingest
- **Social Ingest**: `social_ingest_basic.py` is wired up in `run_social_trading.py`
- Creates `social_lowcap` strands
- Learning system processes strands and triggers Decision Maker

#### Decision Maker
- Creates positions in `lowcap_positions` table
- Sets `max_allocation_pct` and `total_allocation_usd`
- Position table is now more of a watchlist

#### Data Pipeline
- **Backfill**: Runs for required timeframes (based on token age)
- **TA Tracker**: Computes EMAs, ATR, RSI, etc. per timeframe
- **Geometry Builder**: Builds S/R levels per timeframe
- **Price Tracking**: Ongoing 5m OHLCV collection
- **Uptrend Engine**: Runs per timeframe, stores results per timeframe

#### PM Core Tick
- Reads uptrend engine state from `features.uptrend_engine_v4`
- Computes A/E scores
- Calls `plan_actions()` to generate decisions
- Writes to `ad_strands` table

#### PM Executor
- Subscribes to `decision_approved` events (via event bus)
- Executes decisions immediately (synchronous execution)
- Uses idempotency to prevent duplicate executions
- Handles `add`, `trim`, `demote` decision types

#### Event Bus / Learning Layer
- **Learning System** (`UniversalLearningSystem`) is the orchestrator
- Processes strands and triggers downstream modules
- Event bus: `subscribe("decision_approved", ...)` pattern
- See `run_social_trading.py` for how it all wires together

### Buy Condition Execution

**Current Approach**: Synchronous execution
- PM runs hourly (or on events)
- Checks current Uptrend Engine signals
- If conditions are met (e.g., `buy_signal=True`), executes immediately
- No explicit "buy at retest of EMA60" condition tracking

**How it works**:
- Engine checks `abs(price - EMA60) <= 1.0 * ATR` when it runs
- If condition is met, sets `buy_signal=True`
- PM reads signal and executes if A score allows
- No need for separate price monitoring for conditional buys (engine handles it)

**Future consideration** (to finalize):
- Could add explicit conditional buy tracking (e.g., "buy when price retests EMA60")
- Would require price monitor to watch conditions and trigger execution
- For now, synchronous approach works (engine checks conditions, PM executes)

### Module Communication

#### Event System
- Uptrend Engine can emit `uptrend_state_change` events (if needed)
- PM subscribes to events and recomputes actions
- PM Executor subscribes to `decision_approved` events
- Learning System orchestrates strand processing

#### Data Flow
- All modules read/write to `lowcap_positions.features`
- Uptrend Engine writes to `features.uptrend_engine_v4` (or `features.uptrend_engine_v4_1h`, etc.)
- PM reads from `features.uptrend_engine_v4`
- PM writes to `ad_strands` table
- PM Executor reads from `ad_strands` and executes

### Required Updates for Multi-Timeframe

**Only these modules need timeframe support**:
1. **Backfill**: Run for each required timeframe
2. **TA Tracker**: Run per timeframe, store with suffix
3. **Geometry Builder**: Run per timeframe, store per timeframe
4. **Price Tracking**: Already supports multiple timeframes (5m OHLCV)
5. **Uptrend Engine**: Run per timeframe, store results per timeframe
6. **PM**: Read primary timeframe (or multiple if needed)
7. **PM Executor**: No changes needed (works with PM decisions)

**Key Insight**: Just extra runs, extra database columns - not big module changes!

### Cleanup Tasks

#### Remove Old System Components
1. **Old Uptrend Engines**:
   - `uptrend_engine.py` (v1) - archive
   - `uptrend_engine_v2.py` (v2) - archive
   - `uptrend_engine_v3.py` (v3) - keep for reference, mark as deprecated

2. **Old PM Logic**:
   - Update `plan_actions()` to use v4 signals (or create v4 version)
   - Remove geometry-based entry/exit logic (replaced by uptrend engine)

3. **Old Backtesters**:
   - `backtester/v2/` - archive
   - `backtester/v3/` - archive
   - Keep `backtester/v4/` as active

4. **Old Social Ingest**:
   - `social_ingest_module.py` - not used (replaced by `social_ingest_basic.py`)

### New Token Onboarding Flow

**Status**: Already implemented!

1. **Token Ingest** (Social Ingest)
   - Creates `social_lowcap` strand
   - Learning system processes strand

2. **Decision Maker**
   - Evaluates strand
   - Creates position in `lowcap_positions` table
   - Sets `max_allocation_pct` and `total_allocation_usd`

3. **Backfill** (all required timeframes)
   - Runs backfill for each timeframe based on token age
   - Stores in `lowcap_price_data_ohlc` with correct `timeframe`

4. **TA Tracker** (per timeframe)
   - Runs TA tracker for each timeframe
   - Stores with timeframe suffix

5. **Geometry Builder** (per timeframe)
   - Runs geometry builder for each timeframe
   - Stores per timeframe

6. **Uptrend Engine** (per timeframe)
   - Runs engine for each timeframe
   - Stores results per timeframe

7. **PM Core Tick**
   - Reads uptrend engine state (primary timeframe)
   - Computes A/E scores
   - Generates actions

8. **PM Executor / Price Monitor**
   - Executes actions when conditions are met

---

## Implementation Priority

### Phase 0: Uptrend Engine Scheduling (CRITICAL - Must Do First)
1. **Add Uptrend Engine v4 to `run_social_trading.py`**:
   ```python
   from intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v4 import main as uptrend_engine_main
   asyncio.create_task(schedule_5min(4, uptrend_engine_main))  # Run every 5 minutes
   ```
2. Ensure Uptrend Engine runs before PM Core Tick (or at least in parallel)
3. Test that `features.uptrend_engine_v4` is populated correctly

### Phase 1: PM Integration (Highest Value, Lowest Risk)
1. Create `plan_actions_v4()` with correct payload structure
2. Wire Uptrend Engine v4 signals into PM
3. Test entry/exit gates
4. Parallel run with old system
5. **Fix payload structure bug** (critical)

### Phase 2: Multi-Timeframe Foundation (Weeks 2-3)
1. Update backfill to support timeframes
2. Update TA tracker to support timeframes (just extra columns)
3. Update geometry builder to support timeframes (just extra runs)
4. Test with single timeframe first

### Phase 3: Uptrend Engine Multi-Timeframe (Week 3-4)
1. Make engine timeframe-aware
2. Run engine multiple times for different timeframes
3. Store results per timeframe (no aggregation)
4. Test with multiple timeframes

### Phase 4: System Integration (Week 4-5)
1. Test end-to-end with multi-timeframe
2. Cleanup old components
3. Full migration

---

## Key Decisions Made

1. **Timeframes to Support**: 
   - Start with: 1m, 5m, 15m, 1h
   - Add 4h later if needed

2. **Multi-Timeframe Strategy**:
   - **No aggregation** - each timeframe gives independent signals
   - PM reads primary timeframe (or multiple if needed)
   - Simple approach: just extra runs, extra columns

3. **Geometry Timeframe Dependency**:
   - ✅ Timeframe-dependent (confirmed)

4. **Emergency Exit**:
   - ✅ v4 simplified: emergency_exit = full exit (no bounce protocol)
   - Get out faster, rebuy on reclaim - more risk but less complex

5. **Position Sizing**:
   - ✅ Aggressive = 100% allocation (50% initial buy)
   - ✅ Normal = 60% allocation (30% initial buy)
   - ✅ Patient = 30% allocation (10% initial buy)

6. **Migration Strategy**:
   - ✅ Gradual rollout (feature flag, parallel run)

7. **Buy Condition Execution**:
   - ✅ Synchronous for now (engine checks conditions, PM executes)
   - ⏳ Future: Could add explicit conditional buy tracking (to finalize)

---

## Questions to Finalize

1. **Buy Condition Execution**:
   - Keep synchronous approach (engine checks, PM executes)?
   - Or add explicit conditional buy tracking ("buy when price retests EMA60")?
   - If conditional, how should price monitor watch conditions?

2. **Multi-Timeframe PM Reading**:
   - Start with primary timeframe only?
   - Or read multiple timeframes and use them for confirmation?
