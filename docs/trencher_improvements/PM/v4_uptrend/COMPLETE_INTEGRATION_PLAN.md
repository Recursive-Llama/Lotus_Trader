# Complete Integration Plan - Uptrend Engine v4 + Portfolio Manager

**Status**: Consolidated plan combining Architecture Plan, Token Flow Trace, and Timeframe Strategy

---

## Table of Contents

1. [Current State & Issues](#current-state--issues)
2. [Data Flow & Token Journey](#data-flow--token-journey)
3. [Timeframe Strategy](#timeframe-strategy)
4. [Portfolio Manager Integration](#portfolio-manager-integration)
5. [System Integration & Cleanup](#system-integration--cleanup)
6. [Implementation Priority](#implementation-priority)

---

## Current State & Issues

### ✅ What's Working

1. **Social Ingest** → Learning System → Decision Maker → Trader flow
2. **Position Creation** with allocation tracking
3. **TA Tracker** (runs every 5 min, but only 1h timeframe)
4. **Geometry Builder** (runs daily, but only 1h timeframe)
5. **Price Tracking** (5m OHLCV continuous collection)
6. **PM Core Tick** (runs hourly at :06 UTC)
7. **PM Executor** (event-driven, registered)

### ❌ Critical Issues

#### 1. **Uptrend Engine v4 Not Scheduled** ❌ **CRITICAL**
- **Location**: `src/run_social_trading.py` - missing from `start_pm_jobs()`
- **Impact**: PM Core Tick expects `features.uptrend_engine_v4` but it never exists
- **Fix**: Add `schedule_5min(4, uptrend_engine_v4_main)` to `start_pm_jobs()`

#### 2. **First Buy Executes Immediately** ❌ **WRONG BEHAVIOR**
- **Location**: `src/intelligence/trader_lowcap/trader_service.py` lines 1165-1189
- **Issue**: Old system behavior - executes first buy immediately on position creation
- **Fix**: Remove immediate buy execution - let PM handle all entries via signals

#### 3. **Backfill Hardcoded to 15m** ⚠️ **SHOULD BE 1H**
- **Location**: `src/intelligence/trader_lowcap/trader_service.py` line 1128-1130
- **Issue**: Calls `backfill_token_15m` instead of `backfill_token_1h` (or dynamic)
- **Fix**: Change to `backfill_token_1h` OR make it dynamic based on token age

#### 4. **TA Tracker Hardcoded to 1h** ⚠️ **NEEDS MULTI-TIMEFRAME**
- **Location**: `src/intelligence/lowcap_portfolio_manager/jobs/ta_tracker.py` line 179
- **Issue**: `.eq("timeframe", "1h")` hardcoded
- **Impact**: Cannot analyze tokens < 14 days old
- **Fix**: Make timeframe dynamic, run multiple times for different timeframes

#### 5. **PM Uses Old Logic** ⚠️ **NEEDS FULL WIRING**
- **Location**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py`
- **Issue**: `plan_actions()` uses geometry-based logic, not Uptrend Engine v4 signals
- **Fix**: Create `plan_actions_v4()` using Uptrend Engine signals

#### 6. **PM Frequency Too Low** ⚠️ **FOR LOWER TIMEFRAMES**
- **Current**: Hourly at :06 UTC
- **Issue**: If trading on 5m/15m timeframes, hourly PM misses signals
- **Fix**: Run PM every 5 minutes (or at least more frequently)

#### 7. **Decision Maker Duplication** ⚠️ **CLEANUP NEEDED**
- **Active**: `DecisionMakerLowcapSimple` (used in `run_social_trading.py`)
- **Inactive**: `decision_maker_lowcap.py` (may exist, needs verification)
- **Fix**: Archive unused versions

---

## Data Flow & Token Journey

### Complete Flow (Conceptual Dependencies)

```
1. Token Ingest (Social Signals)
   └─> Creates social_lowcap strand
       └─> Calls learning_system.process_strand_event()

2. Learning System
   └─> Scores strand
       └─> Triggers Decision Maker (if dm_candidate tag)

3. Decision Maker (DecisionMakerLowcapSimple)
   └─> Evaluates criteria (5 checks)
       └─> Creates decision_lowcap strand (approve/reject)
           └─> Returns to Learning System

4. Learning System
   └─> Triggers Trader (if approved)

5. Trader Service
   └─> Creates position in lowcap_positions table
       ├─> Sets max_allocation_pct and total_allocation_usd
       ├─> Triggers async backfill (currently 15m, should be 1h or dynamic) ⚠️
       └─> ❌ REMOVE: First buy execution (old system behavior)

6. Scheduled Jobs (Parallel, Independent)
   ├─> TA Tracker (every 5 min) - writes features.ta (1h only) ⚠️
   ├─> Geometry Builder (daily at :10 UTC) - writes features.geometry (1h only) ⚠️
   ├─> Uptrend Engine v4 (NOT SCHEDULED!) ❌
   ├─> Price Tracking (every 1 min) - writes to price tables ✅
   ├─> Backfill Gap Scan (hourly) - fills missing 1h bars ⚠️
   └─> OHLC Rollup (every 5 min) - rolls up 1m to 5m/15m/1h ✅

7. PM Core Tick (hourly at :06 UTC, should be 5 min) ⚠️
   └─> Reads features (expects uptrend_engine_v4) ❌
       └─> Computes A/E scores
           └─> Calls plan_actions() (OLD logic, not v4) ⚠️
               └─> Executes immediately via executor (direct call)
                   └─> Writes strand after execution (async)
```

### Actual Execution (Parallel Schedules)

| Component | Schedule | Status |
|-----------|----------|--------|
| Social Ingest | Continuous | ✅ Working |
| TA Tracker | Every 5 min | ⚠️ 1h only |
| Geometry Builder | Daily at :10 UTC | ⚠️ 1h only |
| **Uptrend Engine v4** | **NOT SCHEDULED** | ❌ **MISSING** |
| Price Tracking | Every 1 min | ✅ Working |
| OHLC Rollup | Every 5 min | ✅ Working |
| PM Core Tick | Hourly at :06 UTC | ⚠️ Too infrequent |
| Backfill Gap Scan | Hourly | ⚠️ 1h only |

---

## Timeframe Strategy

### Multi-Timeframe Position Model (Final Design)

**Core Principle**: Each token gets **four independent positions** (one per timeframe) from day one.

**Timeframes**: `1m`, `15m`, `1h`, `4h`

**Key Characteristics**:
- **Each timeframe = independent position**: Different allocation, entries, exits, PnL
- **Same wallet, different inventory**: Execution layer tags orders with `position_id` to ensure emergency exits only touch that timeframe's holdings
- **No position retirement**: All TF positions persist; they start `dormant` and flip to `active` when ready
- **Gating is only data availability**: A timeframe can trade **only if it has ≥ 350 bars** (configurable per TF, but 350 is default)

**Status Flow**:
- `dormant`: < 350 bars of data for this token+timeframe (only timeframes without enough data)
- `watchlist`: Default starting position, enough data (`bars_count >= 350`), but no active position yet
- `active`: We hold this token+timeframe (`total_quantity > 0`)
- `paused`: Manual pause
- `archived`: Manual archive

**Normal Path** (for most tokens):
- Decision Maker approves → Creates 4 positions
- Each position checks `bars_count`:
  - If `bars_count >= 350` → `status = 'watchlist'` ✅ (most common)
  - If `bars_count < 350` → `status = 'dormant'` (waiting for data)
- As data arrives, `bars_count` updates → `dormant → watchlist` when threshold reached
- PM executes first buy → `watchlist → active`
- When position fully exited → `active → watchlist` (back to watchlist, not closed)

**Example**: Token < 24 hours old:
- 1m timeframe: Might have enough bars → `watchlist`
- 15m timeframe: Probably < 350 bars → `dormant` (until enough data)
- 1h timeframe: Probably < 350 bars → `dormant` (until enough data)
- 4h timeframe: Definitely < 350 bars → `dormant` (until enough data)

**Allocation Splits** (initial defaults, stored in `alloc_policy` JSONB):
- Decision Maker sets `total_allocation_usd` (total for the token)
- Each timeframe position gets: `alloc_cap_usd = total_allocation_usd * timeframe_percentage`
- Splits: `1m`: 5%, `15m`: 12.5%, `1h`: 70%, `4h`: 12.5%
- Example: If DM sets 1000 USD total → 1m gets 50 USD, 15m gets 125 USD, 1h gets 700 USD, 4h gets 125 USD

**Purpose**: Enable multi-timeframe trading from day one with zero schema churn later. Each timeframe trades independently based on its own cycle analysis.

### 1m Timeframe Data Source (VERIFICATION NEEDED)

**Question**: Can we use 1m price data (tick/price points) instead of OHLC?

**Current Understanding**: We have infrastructure, but **needs verification**:

1. **Data Source**: `lowcap_price_data_1m` table exists with `price_native` and `price_usd`
2. **Rollup System**: `GenericOHLCRollup` should convert 1m price points to OHLC:
   - **Open**: Previous bar's close (or first price in window)
   - **Close**: Last price in window
   - **High**: `max(open, close)` (or actual high if available)
   - **Low**: `min(open, close)` (or actual low if available)
   - **Volume**: Sum of volumes (if available) or use 1m volume data

3. **Current Rollup**: `rollup_ohlc.py` handles this conversion
4. **Usage**: Needed for 1m timeframe positions (one of our 4 timeframes)

**⚠️ CRITICAL VERIFICATION NEEDED**:
- **Action Item**: Verify 1m price data → 1m OHLC conversion works correctly
- **Test**: Ensure rollup produces valid OHLC bars that engine can process
- **Edge Cases**: Handle gaps, missing data, volume calculation
- **This is different from other timeframes** - must verify before Phase 0 implementation

**Implementation**: Use existing rollup system to convert 1m price data to 1m OHLC bars, then use normally. **But verify first!**

### Timeframe Implementation Requirements

**Modules that need timeframe support**:

1. **Backfill** (`geckoterminal_backfill.py`):
   - Add `timeframe` parameter (default '1h' for backward compat)
   - Map timeframe to GeckoTerminal endpoint
   - Store with correct `timeframe` field

2. **TA Tracker** (`ta_tracker.py`):
   - Accept `timeframe` parameter
   - Store with dynamic suffix: `ema20_{timeframe}`
   - Run multiple times for different timeframes (extra runs, extra columns)
   - **Frequency**: 
     - **1m timeframe**: Every 1 minute
     - **15m timeframe**: Every 15 minutes (or 5 min acceptable)
     - **1h timeframe**: Every 1 hour (or 5 min acceptable)
     - **4h timeframe**: Every 4 hours (or 1 hour acceptable)

3. **Geometry Builder** (`geometry_build_daily.py`):
   - Accept `timeframe` parameter
   - Build geometry per timeframe
   - Store as `features.geometry_{timeframe}`
   - **Frequency**: Every 1 hour for all timeframes (1m/5m/15m/1h)
     - **Reason**: Simpler scheduling; geometry is timeframe-specific and can change frequently

4. **Uptrend Engine** (`uptrend_engine_v4.py`):
   - Add `timeframe` parameter to `__init__()`
   - Replace all `_1h` suffix references with dynamic suffix
   - Update OHLC queries to filter by `timeframe`
   - Store results per timeframe: `features.uptrend_engine_v4_{timeframe}`

5. **Price Tracking & OHLC Rollup** (`scheduled_price_collector.py` + `rollup_ohlc.py`):
   - **Price Tracking**: Collects 1m price data every 1 minute → stores in `lowcap_price_data_1m`
   - **OHLC Rollup**: Rolls up 1m to 15m, 1h, 4h (for all required timeframes)
   - **1m OHLC**: Convert 1m price points to 1m OHLC bars (⚠️ VERIFICATION NEEDED)
   - Stores all timeframes in `lowcap_price_data_ohlc` with correct `timeframe` column

6. **PM** (`pm_core_tick.py`):
   - Processes positions grouped by status: `watchlist` + `active` only (skips `dormant`)
   - Each position already has its timeframe (read from position row)
   - Reads `features.uptrend_engine_v4` (no timeframe suffix needed - stored per position)
   - **Frequency**: Every 5 minutes (for lower timeframes)
   - No changes needed to executor (works with PM decisions, tags orders with position_id)

**Key Insight**: Just extra runs, extra database columns - not big module changes!

### Database Considerations

#### Schema Changes Needed

**✅ Already Supported**:
- `lowcap_price_data_ohlc` table already has `timeframe` column
- `features` JSONB column can store multiple timeframe results
- Indexes exist for timeframe queries

**⚠️ Potential Optimizations**:
1. **Add composite index** for timeframe queries (if not exists):
   ```sql
   CREATE INDEX IF NOT EXISTS idx_lowcap_ohlc_token_timeframe_ts 
     ON lowcap_price_data_ohlc (token_contract, chain, timeframe, timestamp DESC);
   ```

2. **Features Storage Strategy**:
   - Each position has its own `timeframe` column, so no suffix needed in features keys
   - Store per position: `features.uptrend_engine_v4` (position already encodes timeframe)
   - Store per position: `features.ta` (or `features.ta_{timeframe}` if multiple TFs per position later)
   - Store per position: `features.geometry` (or `features.geometry_{timeframe}` if multiple TFs per position later)
   - **No schema changes needed** - JSONB handles this, position.timeframe provides context

3. **Position Tracking** (Already Implemented):
   - `total_allocation_pct` - ✅ Already exists
   - `total_allocation_usd` - ✅ Already exists
   - `total_investment_native` - ✅ Already exists (how much bought)
   - `total_extracted_native` - ✅ Already exists (profit taken)
   - `total_quantity` - ✅ Already exists (current tokens held)
   - **No new columns needed** - all tracking already exists!

#### Database Reorganization Plan (CRITICAL)

**Objective**: Clean slate - archive old schemas, delete current tables, recreate fresh targeted tables.

**Steps**:
1. **Archive all existing schemas**:
   - Export all current schema files to `database/archive/` directory
   - Keep for reference but mark as archived
   - Includes: `lowcap_positions_schema.sql`, `lowcap_positions_simple.sql`, etc.

2. **Export token registry** (only data to preserve):
   - Export `token_symbol`, `token_name`, `token_contract`, `chain` to seed file
   - This is the ONLY data we preserve (no positions, no strands, no price cache)

3. **Drop all current tables**:
   - Drop `lowcap_positions` (legacy)
   - Drop `lowcap_positions_simple` (if exists)
   - Drop `ad_strands` (legacy)
   - Drop any price cache tables we don't need
   - Clean up any orphaned tables from migrations

4. **Recreate minimal, targeted schemas**:
   - `lowcap_positions` with:
     - `timeframe` column (enum: `1m`, `15m`, `1h`, `4h`)
     - Unique constraint: `(token_contract, chain, timeframe)`
     - `status` enum: `dormant`, `watchlist`, `active`, `paused`, `archived`
     - `bars_count` integer (updated by data layer)
     - `alloc_cap_usd` numeric (timeframe-specific allocation)
     - `alloc_policy` JSONB (timeframe-specific config, including allocation splits)
     - `features` JSONB (stores `uptrend_engine_v4`, `ta_{timeframe}`, `geometry_{timeframe}`)
     - All existing tracking columns (`total_quantity`, `total_investment_native`, etc.)
   - `position_signals` table (optional, for time-series history):
     - `position_id` FK, `timestamp`, `payload_jsonb`
     - Stores engine outputs over time for audit/learning
   - Essential price tables:
     - `lowcap_price_data_1m` (raw 1m price points)
     - `lowcap_price_data_ohlc` (OHLC bars per timeframe, with `timeframe` column)
   - Essential indexes:
     - Composite index on `(token_contract, chain, timeframe, timestamp DESC)` for OHLC queries
     - Index on `(status, timeframe)` for engine/PM queries

5. **Seed token registry back**:
   - Import preserved token symbols/names/contracts/chains
   - Positions start empty (will be created by Decision Maker on approval)

**Rationale**:
- Remove confusion from old simple/complex variants
- Eliminate schema drift from migrations
- Start fresh with clean, targeted tables
- Align schema with v4 requirements from day one
- No data loss concerns (we only preserve token registry)

---

## PM → Executor Flow & Price Tracking

### Current Flow

#### Step 1: PM Core Tick
**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

**Schedule**: Hourly at :06 UTC (should be every 5 minutes for lower timeframes)

**What happens**:
1. Gets all active positions
2. Reads portfolio phase (meso, macro) and cut pressure
3. For each position:
   - Reads `features.uptrend_engine_v4` (expects engine to have run)
   - Calls `compute_levers()` to compute A/E scores
   - Calls `plan_actions()` to generate decisions
   - **Writes to `ad_strands` table** with decision:
     ```json
     {
       "token": "contract_address",
       "timestamp": "2024-01-15T10:06:00Z",
       "decision_type": "add|trim|demote|hold",
       "size_frac": 0.25,
       "reasons": {
         "buy_signal": true,
         "state": "S1",
         "a_score": 0.75,
         "ts_score": 0.65
       },
       "lever_diag": {
         "a_final": 0.75,
         "e_final": 0.30,
         "phase_meso": "uptrend",
         "cut_pressure": 0.15
       }
     }
     ```
   - Executes immediately via executor (direct call); writes strand after execution

**Output**: `ad_strands` table rows (written after execution)

#### Step 2: Price Tracking (Continuous)
**File**: `src/trading/scheduled_price_collector.py`

**Schedule**: Every 1 minute (continuous)

**What happens**:
1. Collects 1m price data for all active positions
2. Stores in `lowcap_price_data_1m` table:
   - `price_usd` - USD price
   - `price_native` - Native token price
   - `timestamp` - 1-minute timestamp
3. Updates position P&L calculations

**Purpose**: Provides real-time price data for execution

#### Step 3: PM Executor (Direct Call)
**File**: `src/intelligence/lowcap_portfolio_manager/pm/executor.py`

**Schedule**: Direct call from PM Core Tick (not event-driven)

**What happens** (NEW DESIGN):
1. **PM Core Tick directly calls executor** (no events):
   ```python
   result = executor.execute(decision, position)
   ```
2. **Executor executes**:
   - Checks idempotency (prevents duplicate execution within 3 minutes)
   - Gets position from database (revalidation)
   - **Gets latest price** from `lowcap_price_data_1m` table (1m data)
   - Executes based on `decision_type`:
     - **`"add"` or `"trend_add"`**: 
       - Calculates `notional_usd = total_allocation_usd * size_frac`
       - Calls `chain_executor.execute_buy(contract, notional_usd)`
       - Returns `{"status": "success", "tx_hash": "...", "tokens_bought": ...}`
     - **`"trim"` or `"trail"`**: 
       - Calculates `tokens_to_sell = total_quantity * size_frac`
       - Calls `chain_executor.execute_sell(contract, tokens_to_sell, price_usd)`
       - Returns `{"status": "success", "tx_hash": "...", "tokens_sold": ...}`
     - **`"demote"`**: 
       - Same as trim but with larger size_frac (or full exit if size_frac = 1.0)
       - Returns execution result
   - **Execution is immediate** (synchronous) - no price condition checking
   - **Returns execution result** (success/error, tx_hash, etc.)

3. **PM writes strand after execution** (non-blocking):
   - Includes execution result in strand
   - Learning system can analyze: decision → execution → outcome
   - Written asynchronously (doesn't block execution)

**Key Points**:
- **Price source**: `lowcap_price_data_1m` (1-minute price data)
- **Execution timing**: Immediate (direct call, no event overhead)
- **Error handling**: Direct exception propagation (easier to debug)
- **Idempotency**: Checked in executor before executing
- **Canary mode**: Can be checked in executor
- **Strands**: Written after execution with results (better for learning)

**Why Direct Call**:
- More reliable (no event system to fail)
- Faster (direct function call)
- Simpler (fewer moving parts)
- Better error handling (exceptions propagate)
- Still has audit trail (strands written after)

### Architecture Analysis: Execution Flow Design

**Role Clarification**:
- **Uptrend Engine**: Sets flags/signals based on price conditions (technical analysis only)
- **Portfolio Manager**: Takes engine flags + A/E scores + position sizing → Makes decisions → Executes
- **These are separate concerns** - Engine doesn't have A/E info or position sizing logic

**Correct Flow**:
```
1. Uptrend Engine (every 5 min)
   └─> Checks price conditions (price <= EMA144, abs(price - EMA60) <= ATR, etc.)
   └─> Sets flags: buy_signal=True, buy_flag=True, etc.
   └─> Writes to features.uptrend_engine_v4

2. PM Core Tick (every 5 min)
   └─> Reads engine flags
   └─> Computes A/E scores
   └─> plan_actions_v4() combines: engine flags + A/E + position sizing
   └─> Makes decision: add/trim/demote/hold
   └─> ??? (execution - what's best?)

3. Execution
   └─> ??? (how should this work?)
```

**Architecture Options**:

#### Option 1: Direct Call ✅ **RECOMMENDED**
**Flow**: PM → plan_actions_v4() → executor.execute() → Write strand after
- **Pros**: 
  - ✅ **Most reliable** - no indirection, direct error handling
  - ✅ **Fastest** - direct function call
  - ✅ **Simplest** - fewest moving parts
  - ✅ **Still has audit trail** - strands written after execution (non-blocking)
  - ✅ **Clear flow** - easy to debug
- **Cons**: 
  - ⚠️ Tight coupling (PM knows about executor)
  - ⚠️ Can't easily add subscribers (but can add logging/metrics as direct calls)
- **Speed**: Fastest
- **Reliability**: Highest

#### Option 2: Events (Current Old System)
**Flow**: PM → Write strands → Emit event → Executor subscribes
- **Pros**: 
  - Separation of concerns
  - Can add more subscribers
- **Cons**: 
  - ❌ Extra indirection (event system)
  - ❌ Less reliable (event system could fail silently)
  - ❌ Harder to debug (indirect flow)
  - ❌ Bad naming: "decision_approved" doesn't make sense for buys
  - ❌ Strands written before execution (missing execution results)
- **Speed**: Fast (but event overhead)
- **Reliability**: Lower (event system can fail)

#### Option 3: Strands Only (Polling)
**Flow**: PM → Write strands → Executor polls table
- **Pros**: 
  - Decoupled
  - Audit trail
- **Cons**: 
  - ❌ Slowest (polling delay)
  - ❌ More complex (polling logic)
- **Speed**: Slowest
- **Reliability**: Medium

#### Option 4: Conditional Execution ("Execute at EMA60")
**Flow**: PM → Write "execute when price hits EMA60" → Price monitor tracks
- **Pros**: 
  - More precise timing
- **Cons**: 
  - ❌ Much more complex
  - ❌ What if condition never met? (stale orders)
  - ❌ Engine already checks conditions - redundant
- **Speed**: Variable
- **Reliability**: Lower (conditional tracking complexity)

**Recommendation**: **Direct Call (Option 1)**

**Why Direct Call is Best**:
1. **Most Reliable**: No event system to fail, direct error propagation
2. **Fastest**: Direct function call, no overhead
3. **Simplest**: Fewest moving parts, clear flow
4. **Still Has Audit Trail**: Strands written after execution with results (better for learning)
5. **We're Building New**: Can design it right from the start

**Implementation**:
```python
# In pm_core_tick.py
for decision in decisions:
    if decision["decision_type"] != "hold":
        # Execute immediately (direct call)
        result = executor.execute(decision, position)
        # Write strand after execution (with result, non-blocking)
        write_strand_async(decision, position, result)
    else:
        # Hold decisions - just write strand
        write_strand(decision, position)
```

**Strands for Learning**:
- Strands written **after execution** (with execution results)
- Learning system can analyze: decision → execution → outcome
- Non-blocking write (doesn't slow down execution)
- Better for learning (has actual execution results)

**Naming Issue**:
- Events path deprecated (e.g., `decision_approved`); direct call is the only supported path

### Data Flow Summary

```
1. Price Tracking (every 1 min)
   └─> Writes to lowcap_price_data_1m

2. Uptrend Engine (every 5 min)
   └─> Reads OHLC data (1h/5m/15m/1m)
   └─> Checks price conditions
   └─> Writes signals to features.uptrend_engine_v4

3. PM Core Tick (every 5 min, currently hourly)
   └─> Reads features.uptrend_engine_v4
   └─> Computes A/E scores
   └─> Generates decisions
   └─> Calls executor directly to execute (synchronous)
   └─> Writes strand after execution (async)

4. PM Executor (direct call)
   └─> Gets latest price from lowcap_price_data_1m
   └─> Executes trade immediately
```

### What PM Outputs

**PM Core Tick outputs**:
- `ad_strands` table rows with:
  - `decision_type`: "add", "trim", "demote", "hold"
  - `size_frac`: Fraction of allocation (for adds) or position (for trims)
  - `reasons`: Dict with signal details (buy_signal, state, scores, etc.)
  - `lever_diag`: Dict with A/E scores and phase info

**PM Executor**:
- Invoked directly by PM (no event bus)
- Gets latest price from `lowcap_price_data_1m`
- Executes via chain executors (bsc_executor, base_executor, eth_executor, sol_executor)

---

## Portfolio Manager Integration

### Current State

#### What's Working:
- ✅ A/E scores computed correctly (`compute_levers()`)
- ✅ PM Core Tick runs hourly
- ✅ PM Executor callable (direct execution path)
- ✅ Decision types supported (`add`, `trim`, `demote`, `hold`)

#### What's Missing:
- ❌ `plan_actions()` uses OLD geometry-based logic
- ❌ Does NOT use Uptrend Engine v4 signals
- ❌ Does NOT use Uptrend Engine v4 states (S1, S2, S3)
- ❌ Does NOT use Uptrend Engine v4 scores (TS, DX, OX, EDX)

### Payload Structure (CRITICAL FIX)

**WRONG** (what might be assumed):
```python
uptrend = features.get("uptrend_engine_v4") or {}
payload = uptrend.get("payload", {}) or {}  # ❌ WRONG - nested payload
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

### New PM Decision Flow

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
    # v4 simplified: emergency_exit = full exit (no bounce protocol)
    if state == "S3" and uptrend.get("emergency_exit"):
        actions.append({
            "decision_type": "demote",
            "size_frac": 1.0,
            "reasons": {"emergency_exit": True, "e_score": e_final, "state": state}
        })
        return actions
    
    # Trim Flags (S2/S3)
    if uptrend.get("trim_flag"):
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
```

### Position Sizing (A/E Driven)

**Allocation**: Set by Decision Maker (`total_allocation_pct` and `total_allocation_usd`)

#### Entry Sizes (A-driven)

**S1 Entries** (Initial entries):
- **A >= 0.7 (Aggressive)**: 50% initial allocation (target 100% allocation)
- **A >= 0.3 (Normal)**: 30% initial allocation (target 60% allocation)
- **A < 0.3 (Patient)**: 10% initial allocation (target 30% allocation)

**S2/S3 Entries** (Add-on entries):
- **A >= 0.7 (Aggressive)**: 25% initial allocation (target 50% allocation)
- **A >= 0.3 (Normal)**: 15% initial allocation (target 30% allocation)
- **A < 0.3 (Patient)**: 5% initial allocation (target 15% allocation)

**Entry Multipliers** (Allocation vs Profit):
- **Allocation Risk Multiplier**: Based on profit taken vs allocation
  - If `total_extracted_native >= total_allocation_usd * 1.0` (100% profit): **0.3x multiplier** (smaller buys)
  - If `total_extracted_native >= total_allocation_usd * 0.0` (breakeven): **1.0x multiplier** (normal buys)
  - If `total_extracted_native < 0` (in loss): **1.5x multiplier** (larger buys to average down)
- **Applied to**: S2 and S3 entries only (S1 entries use base size)

**Tunable Entry Thresholds** (Future):
- Each A/E level can have different Uptrend Engine score thresholds
- More aggressive = lower TS/DX thresholds
- Stored in config, not hardcoded

#### Trim Sizes (E-driven)

**Base Trim Sizes**:
- **E >= 0.7 (Aggressive)**: 10% trim
- **E >= 0.3 (Normal)**: 50% trim
- **E < 0.3 (Patient)**: 3% trim

**Trim Multipliers** (Allocation Risk):
- **Allocation Risk Multiplier**: Based on allocation deployed vs profit taken
  - If `current_position_value >= total_allocation_usd * 0.8` (nearly maxed out): **3.0x multiplier** (take more profit)
  - If `total_extracted_native >= total_allocation_usd * 1.0` (100% profit recouped): **0.3x multiplier** (take less profit)
  - If `total_extracted_native >= total_allocation_usd * 0.0` (breakeven): **1.0x multiplier** (normal trims)
  - If `total_extracted_native < 0` (in loss): **0.5x multiplier** (smaller trims, preserve capital)

**Tunable Trim Thresholds** (Future):
- Each E level can have different OX thresholds
- More aggressive = lower OX thresholds for trims

#### Exit Types

- **Emergency exit** = Full exit (`demote` with `size_frac: 1.0`)
- **Rest is trims** = `trim` with appropriate `size_frac` and multiplier

#### Position Tracking (Already Implemented)

**Database Columns** (already exist):
- `total_allocation_pct` - Total allocation percentage from Decision Maker ✅
- `total_allocation_usd` - Total allocation USD amount ✅
- `total_quantity` - Current tokens held ✅
- `total_investment_native` - Total native currency invested (how much bought) ✅
- `total_extracted_native` - Total native currency extracted (profit taken) ✅
- `total_tokens_bought` - Total tokens bought across all entries ✅
- `total_tokens_sold` - Total tokens sold across all exits ✅

**Calculated Values** (for multipliers):
- `current_position_value` = `total_quantity * current_price`
- `allocation_deployed_pct` = `current_position_value / total_allocation_usd`
- `profit_taken_pct` = `total_extracted_native / total_allocation_usd`

---

## System Integration & Cleanup

### Required Updates

#### 1. Schedule Uptrend Engine v4
**File**: `src/run_social_trading.py`
```python
# In start_pm_jobs():
from intelligence.lowcap_portfolio_manager.jobs.uptrend_engine_v4 import main as uptrend_engine_main
asyncio.create_task(schedule_5min(4, uptrend_engine_main))  # Run every 5 minutes
```

#### 2. Remove First Buy Execution
**File**: `src/intelligence/trader_lowcap/trader_service.py`
- Remove lines 1165-1189 (first buy execution)
- Let PM handle all entries via signals

#### 3. Fix Backfill
**File**: `src/intelligence/trader_lowcap/trader_service.py`
- Change `backfill_token_15m` to `backfill_token_1h` (or make dynamic)
- Make dynamic based on token age (see timeframe strategy)

#### 4. Make TA Tracker Multi-Timeframe
**File**: `src/intelligence/lowcap_portfolio_manager/jobs/ta_tracker.py`
- Add `timeframe` parameter
- Store with dynamic suffix
- Run multiple times for different timeframes

#### 5. Update PM Frequency
**File**: `src/run_social_trading.py`
- Change PM Core Tick from hourly to every 5 minutes (for lower timeframes)
- **Reason**: If trading on 5m/15m timeframes, hourly PM misses signals

#### 6. Update Geometry Frequency
**File**: `src/run_social_trading.py`
- Run geometry every 1 hour for all timeframes (1m/5m/15m/1h)
- **Reason**: Simpler scheduling; geometry is timeframe-specific and can change frequently

#### 7. Implement Position Sizing Multipliers
**File**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py`
- Add allocation risk multiplier calculation
- Apply to S2/S3 entries and all trims
- Use existing position tracking columns (`total_allocation_usd`, `total_investment_native`, `total_extracted_native`)

#### 8. Create `plan_actions_v4()`
**File**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py`
- Create new function using Uptrend Engine v4 signals
- Feature flag for gradual migration

### Cleanup Tasks

#### Archive Old Code:
1. **Old Uptrend Engines**:
   - `uptrend_engine.py` (v1) - archive
   - `uptrend_engine_v2.py` (v2) - archive
   - `uptrend_engine_v3.py` (v3) - mark as deprecated

2. **Old Social Ingest**:
   - `social_ingest_module.py` - archive (replaced by `social_ingest_basic.py`)

3. **Old Backtesters**:
   - `backtester/v2/` - archive
   - `backtester/v3/` - archive
   - Keep `backtester/v4/` as active

4. **Old Decision Maker**:
   - Verify which is active (should be `DecisionMakerLowcapSimple`)
   - Archive unused versions

#### Old Trader Execution System (Keep for Learning):
**Status**: Keep for now - executors can learn from this implementation

**What it does**:
- `PositionMonitor` (`position_monitor.py`) monitors positions continuously
- Checks `entries` and `exits` JSONB columns for `status='pending'`
- Executes when price targets hit:
  - `_check_planned_entries()`: Executes entries when `current_price <= target_price`
  - `_check_trend_entries()`: Executes trend entries when price targets hit
  - `_check_exits()`: Executes exits when price targets hit
- Uses `trader._service.execute_individual_entry()` and `execute_exit()`

**Split Executors**:
- **EVM chains** (Base, BSC, Ethereum): `execute_entry()` and `execute_exit()` are synchronous
- **Solana**: `execute_entry()` and `execute_exit()` are async (handled differently)

**Why keep it**:
- Good reference implementation for executor logic
- Shows how to handle price-based conditional execution
- Demonstrates EVM vs Solana differences
- Shows proper transaction confirmation and error handling

**Note**: New PM system will use direct calls (not price-based conditional), but executor internals are still valuable reference.

---

### Database Reset Plan (Preserve Token Registry Only)

**Objective**: Remove legacy tables/schemas and start clean while preserving token identifiers.

**Steps**:
1. Export token registry (symbol/name/contract/chain) to a seed file
2. Drop legacy schemas/tables (positions, strands, price cache, etc.)
3. Recreate minimal schemas, including `lowcap_positions(timeframe, status, features, ...)`
4. Seed token registry back; do not restore legacy positions/strands
5. Recreate essential indexes (token, chain, timeframe, timestamp DESC)

Rationale: Reduce confusion from old simple/complex variants; align schema to v4 requirements.

---

## Implementation Priority

### Phase 0: Critical Fixes (Must Do First) 🔴

1. **Database Reorganization** (CRITICAL - do first):
   - Archive all existing schemas to `database/archive/`
   - Export token registry (symbol/name/contract/chain) to seed file
   - Drop all current tables (positions, strands, price cache)
   - Recreate minimal schemas:
     - `lowcap_positions` with `timeframe` column (enum: 1m, 15m, 1h, 4h)
     - Unique constraint: `(token_contract, chain, timeframe)`
     - Status enum: `dormant`, `watchlist`, `active`, `paused`, `archived`
     - Add `bars_count`, `alloc_cap_usd`, `alloc_policy` JSONB
     - Create `position_signals` table for time-series history (optional)
   - Seed token registry back
   - Recreate essential indexes

2. **Verify 1m OHLC Conversion** (CRITICAL - before implementation):
   - Test 1m price data → 1m OHLC conversion works correctly
   - Verify rollup produces valid OHLC bars engine can process
   - Test edge cases (gaps, missing data, volume calculation)
   - Document any limitations or fixes needed

3. **Update Decision Maker** to create 4 positions per token:
   - Decision Maker sets `total_allocation_usd` (total for the token)
   - Create positions for 1m, 15m, 1h, 4h timeframes
   - For each position: `alloc_cap_usd = total_allocation_usd * timeframe_percentage`
     - 1m: `total_allocation_usd * 0.05`
     - 15m: `total_allocation_usd * 0.125`
     - 1h: `total_allocation_usd * 0.70`
     - 4h: `total_allocation_usd * 0.125`
   - Set `status` based on `bars_count` (dormant if < 350, watchlist if >= 350)
   - Store allocation splits in `alloc_policy` JSONB
   - **Note**: Most tokens will start with all positions at `watchlist` (if they have enough data)

4. **Update Backfill** to support all 4 timeframes:
   - Trigger backfill for 1m, 15m, 1h, 4h (async, non-blocking)
   - Update `bars_count` per position as data arrives (✅ already tracking this)
   - Auto-flip `dormant → watchlist` when `bars_count >= 350`
   - **Note**: Most tokens will have enough data for at least some timeframes → those start at `watchlist` immediately

5. **Update OHLC Rollup** to roll up to all required timeframes:
   - Roll up 1m → 15m, 1h, 4h
   - Ensure 1m OHLC conversion works (from price points)

6. **Schedule Uptrend Engine v4** per timeframe:
   - 1m: Every 1 minute
   - 15m: Every 15 minutes
   - 1h: Every 1 hour
   - 4h: Every 4 hours
   - Group by timeframe (not by token)
   - Run for dormant positions (bootstrap state), watchlist/active (emit signals)

7. **Implement State Bootstrap** for dormant positions:
   - Run engine like a backtest to initialize state (S0, S1, S2, S3)
   - Only bootstrap to S0 or S3 (clear trends)
   - Write warmup diagnostics, no signals until `watchlist` status

8. **Remove first buy execution** from trader service
9. **Create `plan_actions_v4()`** with correct payload structure
10. **Update PM frequency** (hourly → every 5 minutes)
11. **Create `pm_thresholds` table** and 5-min cache layer
12. **Update PM to process only watchlist + active** (skip dormant)

### Phase 1: PM Integration (Highest Value) 🟠

1. Wire Uptrend Engine v4 signals into PM
2. Implement position sizing multipliers (allocation risk)
3. Implement S2/S3 entry sizes (smaller than S1)
4. Test entry/exit gates
5. Parallel run with old system

### Phase 2: Multi-Timeframe Foundation (Weeks 2-3) 🟡

1. Update backfill to support timeframes
2. Update TA tracker to support timeframes
3. Update geometry builder to support timeframes
4. Test with single timeframe first

### Phase 3: Uptrend Engine Multi-Timeframe (Week 3-4) 🟡

1. Make engine timeframe-aware
2. Run engine multiple times for different timeframes
3. Store results per timeframe
4. Test with multiple timeframes

### Phase 4: System Integration & Cleanup (Week 4-5) 🟢

1. Test end-to-end with multi-timeframe
2. Cleanup old components
3. Full migration
4. Documentation updates

---

## Questions to Finalize

1. **Buy Condition Execution**:
   - Keep synchronous approach (engine checks, PM executes)?
   - Or add explicit conditional buy tracking ("buy when price retests EMA60")?

2. **Multi-Timeframe PM Reading**:
   - Decision: Read the position's timeframe only in Phase 0 (no cross-timeframe confirmation)

3. **Geometry Frequency for Lower Timeframes**:
   - Every 6 hours for 5m/15m?
   - Or twice daily (morning/evening)?
   - Or keep daily (simpler)?

4. **Tunable Thresholds Implementation**:
   - Store in config file?
   - Or in database (features or separate config table)?
   - When to implement (Phase 1 or later)?

---

## Key Decisions Made

1. ✅ **No aggregation** - each timeframe gives independent signals
2. ✅ **Emergency exit = full exit** (v4 simplified)
3. ✅ **Position sizing** - Aggressive/Normal/Patient based on A/E
4. ✅ **S2/S3 entries smaller** - 25%/15%/5% vs S1 50%/30%/10%
5. ✅ **Allocation risk multipliers** - Based on profit taken vs allocation
6. ✅ **Geometry timeframe-dependent** (confirmed)
7. ✅ **1m data can be converted to OHLC** (using existing rollup system)
8. ✅ **DB reset planned** - Recreate minimal schemas; add `timeframe` to positions
9. ✅ **PM frequency** - Every 5 minutes (for lower timeframes)
10. ✅ **Geometry frequency** - Every 1 hour for all timeframes
11. ✅ **Gradual rollout** (feature flag, parallel run)
12. ✅ **Tunable thresholds** - Future enhancement, architecture ready

---

## Document Consolidation

**Status**: This document consolidates:
- `ARCHITECTURE_PLAN.md` - Architecture decisions and integration plan
- `TOKEN_FLOW_TRACE.md` - Complete token flow from ingestion to execution
- `TIMEFRAME_AGNOSTIC_PLAN.md` - Timeframe strategy (now integrated above)

**Recommendation**: Keep this single consolidated document, archive the others for reference.

---

## Architecture Clarifications (Final Decisions)

### 1. Strand Structure

**Decision**: Option A - One strand per action type (buy strand, sell strand, hold strand)

**Strand Types**:
- **Buy Strand**: Contains decision + execution result (tx_hash, actual price, slippage)
- **Sell Strand**: Contains decision + execution result (tx_hash, actual price, slippage)
- **Hold Strand**: Contains decision (no execution, but includes why it held)

**Strand Content**:
- All context included (S1 buy, S2 buy, S3 DX buy, first dip buy, trim, exit, etc.)
- Full engine flags and scores
- A/E scores used
- Execution results (for buy/sell strands)
- Blocked decisions: **Deferred** - Add later if needed for learning

**Writing**: Strands written **after execution** (async, non-blocking) with execution results included.

---

### 2. Executor Structure

**Decision**: Separate executors per chain (not one unified EVM executor)

**Current Structure**:
- `bsc_executor` - BSC chain only
- `base_executor` - Base chain only
- `eth_executor` - Ethereum chain only
- `sol_executor` - Solana chain only

**PM → Executor Flow**:
- PM calls executor directly (tight coupling acceptable)
- Executor writes to position table immediately after execution
- No separate execution table needed

**Future**: Adding midcaps/stocks just requires more executors (e.g., `stock_executor`), PM doesn't change.

---

### 3. New Token Onboarding Flow (Complete)

**Step-by-Step Flow**:

```
1. Social Ingest → New signal detected
   └─> Creates social_lowcap strand
   └─> Calls learning_system.process_strand_event()

2. Learning System → Scores strand
   └─> Triggers Decision Maker (if dm_candidate tag)

3. Decision Maker → Evaluates criteria
   └─> If approved: Sets total_allocation_usd and total_allocation_pct
   └─> Creates 4 positions in Position Table (one per timeframe):
       ├─> Position 1: token + 1m timeframe
       ├─> Position 2: token + 15m timeframe
       ├─> Position 3: token + 1h timeframe
       └─> Position 4: token + 4h timeframe
   └─> Each position:
       ├─> status: 'watchlist' (if bars_count >= 350) or 'dormant' (if bars_count < 350)
       │   └─> **Most tokens**: All positions start at 'watchlist' (enough data)
       │   └─> **New tokens**: Some timeframes may start 'dormant' until enough data
       ├─> alloc_cap_usd: `total_allocation_usd * timeframe_percentage` (1m: 5%, 15m: 12.5%, 1h: 70%, 4h: 12.5%)
       ├─> total_quantity: 0.0
       └─> alloc_policy: JSONB with timeframe-specific config

4. Backfill (async, non-blocking) → For all 4 timeframes
   └─> Triggers backfill for 1m, 15m, 1h, 4h
   └─> Stores in lowcap_price_data_ohlc with correct timeframe
   └─> Updates bars_count per position

5. Data Pipeline (continuous)
   └─> price_data_1m → Collected every 1 minute
   └─> OHLC Rollup → Rolls up 1m to 15m, 1h, 4h (for all required timeframes)
   └─> TA Tracker → Runs per timeframe, stores features.ta_{timeframe}
   └─> Geometry Builder → Runs per timeframe, stores features.geometry_{timeframe}

6. State Bootstrap (CRITICAL - understand current stage)
   └─> Uptrend Engine runs for dormant positions to initialize state
   └─> Walks through historical data to determine **where we are in the cycle right now** (S0, S1, S2, S3)
   └─> Like a backtest, but specifically about understanding current stage (not just simulation)
   └─> Only bootstrap to S0 or S3 (clear trends) - can't bootstrap to S1/S2 (transition states require context)
   └─> Writes warmup diagnostics, no signals yet (position still dormant)
   └─> When bars_count >= 350: Position flips dormant → watchlist (now ready to trade)

7. Uptrend Engine (per timeframe, grouped by timeframe)
   └─> Runs for all positions of that timeframe (dormant, watchlist, active)
   └─> For watchlist/active: Emits signals, writes to features.uptrend_engine_v4
   └─> For dormant: Continues bootstrapping, writes diagnostics only

8. PM Core Tick → Processes only watchlist + active positions
   └─> Reads engine flags from features.uptrend_engine_v4
   └─> Computes A/E scores
   └─> plan_actions_v4() makes decisions
   └─> For watchlist positions: First buy updates status → 'active'
   └─> For active positions: Adds/trims/exits

9. Executor → Executes trades
   └─> Tags all orders with position_id (ensures emergency exits only touch that TF's holdings)
   └─> Updates position total_quantity, total_investment_native, etc.
```

**Status Field Definitions**:
- `'dormant'`: < 350 bars of data for this token+timeframe (or configurable threshold)
- `'watchlist'`: Default starting position, enough data, but no active position yet (`total_quantity = 0`)
- `'active'`: We hold this token+timeframe (`total_quantity > 0`)
- `'paused'`: Manual pause
- `'archived'`: Manual archive

**Key Points**:
- **4 positions per token from day one** - no schema churn later
- **State bootstrap required** - need to know where we are in the cycle before trading
- **Only start signals in S0 or S3** - clear trends only (matches backtest behavior)
- **Position ID tagging** - execution layer ensures emergency exits only touch that timeframe's holdings

---

### 4. Uptrend Engine Frequency & Scheduling

**Decision**: Run engine per timeframe, grouped by timeframe (not by token)

**Schedule**:
- **1m timeframe**: Every 1 minute
- **15m timeframe**: Every 15 minutes
- **1h timeframe**: Every 1 hour
- **4h timeframe**: Every 4 hours

**Implementation**:
- Separate loops per timeframe (not per token)
- Each run processes **all positions for that timeframe** (watchlist + active + dormant)
- For **dormant** positions: Run engine to bootstrap/initialize state (like a backtest) - writes warmup diagnostics, no signals
- For **watchlist/active** positions: Run engine normally, emit signals
- Store results per position: `features.uptrend_engine_v4_{timeframe}` (each position already has its own timeframe)

**Why run engine for dormant positions?**
- Need to bootstrap state machine (know where we are in the cycle) before position becomes active
- Like running a backtest: walk through historical data to initialize state (S0, S1, S2, S3)
- Only start emitting signals when position transitions `dormant → watchlist → active`
- PM ignores dormant positions entirely (no trades until active)

---

### 5. Demote vs Emergency Exit

**Current State**:
- **Demote** (old system): Sells 80%, keeps moon bag (line 156 in `actions.py`)
- **Emergency Exit** (v4): Full exit (100%) when price < EMA333

**Decision**: 
- **Remove "demote"** - Use "emergency_exit" for full exits
- **Keep "trim"** for partial exits
- **Emergency exit = full exit** (confirmed)

---

### 6. Hold Strand

**Trigger**: When no buy/trim/exit conditions are met (default action)

**Content**:
- Decision: "hold"
- Reasons: Why it held (no buy signals, no trim signals, no exit signals)
- A/E scores used
- Engine flags checked

**Purpose**: Learning/audit - understand why PM didn't act

---

### 7. Execution Writes

**Decision**: Executor writes directly to position table (no separate execution table)

**Flow**:
1. Executor executes trade (via chain-specific executor)
2. Gets tx_hash, actual price, slippage
3. Calls `position_repository.mark_entry_executed()` or `mark_exit_executed()`
4. Updates `entries` or `exits` JSONB array in position table
5. Updates `total_quantity`, `total_investment_native`, etc.

**Timing**: Writes happen **immediately after execution** (synchronous, part of execution flow)

---

### 8. A/E Caching

**Decision**: Cache computed A/E in `features.pm_a_e`

**Structure**:
```json
{
  "pm_a_e": {
    "A_value": 0.65,
    "E_value": 0.45,
    "cached_at": "2024-01-15T12:00:00Z",
    "components": {
      "global": {...},
      "per_token": {...}
    }
  }
}
```

**Logic**:
- PM checks cache first
- If cache exists and < 5 min old → Use cached values
- If cache missing or stale → Recompute and update cache

**Update Frequency**:
- Global components (phase, cut_pressure): Update when phase changes (hourly checks)
- Per-token components (intent, age, mcap): Update when social signals come in (intent), daily (age), price updates (mcap)

---

### 10. BTC.d and USDT.d (Dominance) - NOT A/E Scores

**What they are**:
- **BTC.d**: Bitcoin dominance (% of total crypto market cap)
- **USDT.d**: Tether dominance (% of total crypto market cap)

**How they're calculated**:
- **Source**: `dominance_ingest_1h.py` fetches from CoinGecko API hourly
- **Metrics computed**:
  - Current levels: `btc_dom_level`, `usdt_dom_level`
  - 7-day deltas: `btc_dom_delta`, `usdt_dom_delta`, `dominance_delta` (BTC - USDT)
  - Z-scores over 90d window:
    - `btc_dom_level_z`, `btc_dom_slope_z`, `btc_dom_curv_z`
    - `usdt_dom_level_z`, `usdt_dom_slope_z`, `usdt_dom_curv_z`
- **Storage**: Written to `portfolio_bands` table hourly

**How they affect the system**:
- **NOT directly in A/E scores** (despite comment in `levers.py`)
- **Used in phase detection** (`tracker.py`):
  - Dominance metrics feed into phase calculation (Macro/Meso/Micro)
  - Phases (dip, recover, euphoria, etc.) then influence A/E scores
  - Indirect effect: Dominance → Phase → A/E scores

**Current Usage**:
- Dominance deltas/z-scores stored in `portfolio_bands` but not directly read by `compute_levers()`
- Phases read from `phase_state` table (which may use dominance in calculation)
- A/E scores use phases, not dominance directly

**Note**: The comment in `levers.py` says "dominance/cut_pressure shape A/E only" but dominance is actually used indirectly through phases, not directly in A/E calculation.

---

### 11. Database Cleanup & Status Field

**Decision**: Audit and clean up schemas, remove unused fields, **fix status field**

**Critical Fix Needed**:
1. **Status Field Values**:
   - Current: `'active'`, `'closed'`, `'partial'`, `'stopped'`
   - **Problem**: `'active'` is used for both watchlist entries AND actual positions
   - **Solution**: Add `'watchlist'` status, remove `'closed'` and `'partial'`
   - **New Status Options**:
     - `'watchlist'` - Decision Maker approved, max allocation set, no position yet (`total_quantity = 0`)
       - Also used when position fully exited (goes back to watchlist, not `'closed'`)
     - `'active'` - Has actual position (`total_quantity > 0`)
       - Includes partial exits (still holding some tokens)
       - Only full exits → back to `'watchlist'`
     - `'stopped'` - Position stopped (optional, for manual stops)

2. **Update Code**:
   - `trader_service.py` line 1083: Change `status='active'` to `status='watchlist'` when creating entry
   - `uptrend_engine_v4.py`: Query ALL entries (not just `status='active'`)
   - `pm_core_tick.py`: Query ALL entries (not just `status='active'`)
   - Update status to `'active'` when first buy is executed

**Action Items**:
1. **Audit position schemas**:
   - `lowcap_positions_schema.sql` (main one)
   - `lowcap_positions_simple.sql` (check if duplicate)
   - Archive unused ones
2. **Remove unused fields** (if any):
   - Review all fields in `lowcap_positions` table
   - Remove fields that are no longer used
3. **Add missing fields** (if any):
   - Ensure `features` JSONB has enough space for multi-timeframe data
   - Check if any new fields needed for v4

**Status**: To be done in Phase 0 (critical fix)

---

### 12. Priority Positions (Future Enhancement)

**Decision**: Not needed now, but architecture supports it

**Future Implementation**:
- Add `priority` field to `lowcap_positions` table
- High priority: Tokens close to exit/entry conditions
- Low priority: Tokens far from any action
- PM can optimize by processing high priority first

**Status**: Deferred - not needed for initial implementation

---

### 13. Position Identity and Timeframes

**Decision**: A position is identified by (token_contract, chain, timeframe).

**Implications**:
- Each timeframe is an independent tradable instrument for the same token
- `lowcap_positions` includes a `timeframe` column; primary key (or unique index) covers (token_contract, chain, timeframe)
- Uptrend Engine writes signals per timeframe (e.g., `features.uptrend_engine_v4_5m`)
- PM reads only the features for the position's timeframe; no cross-timeframe confirmation in Phase 0
- Opening positions on multiple timeframes means separate rows (one per timeframe)

**Why now**: Avoids future rework; DB reset accommodates schema change cleanly

---

### 14. Tunable Thresholds in Database

**Decision**: Store tunable thresholds in a DB table for live updates and future auto-tuning.

**Table (example)**: `pm_thresholds`
- Columns: `key` (text), `value` (jsonb/float), `timeframe` (text), `phase` (text, nullable), `min_version` (int, nullable), `updated_at`, `updated_by`
- Caching: 5 minutes in-process; fallback precedence = env → DB → code defaults

**Usage**: Thresholds for TS/DX/OX per A/E regime and timeframe; read in PM/Engine at runtime

---

## Final Architecture Summary

### Simplified Flow (CORRECTED)

```
1. Social Ingest → Decision Maker
   └─> Decision Maker evaluates tokens
   └─> Creates entry in Position Table:
       ├─> status='watchlist' (NOT 'active')
       ├─> total_quantity=0.0
       └─> total_allocation_pct: Set by Decision Maker

2. Uptrend Engine (scheduled per timeframe)
   └─> Gets ALL entries from Position Table (watchlist + active)
   └─> For each entry:
       └─> Checks price conditions
       └─> Sets flags per stage:
           ├─> S1: `buy_signal` (entry at EMA60)
           ├─> S2: `trim_flag`, `buy_flag` (retest at EMA333)
           ├─> S3: `trim_flag`, `buy_flag`, `first_dip_buy_flag`, `emergency_exit`, `reclaimed_ema333`
           └─> Global: `exit_position` (fast band at bottom)
       └─> Writes to features.uptrend_engine_v4_{timeframe}

3. PM Core Tick (every 5 min)
   └─> Gets ALL entries from Position Table (watchlist + active)
   └─> For each entry:
       ├─> Computes A/E (checks cache first, recomputes if stale)
       ├─> Reads engine flags (from features)
       ├─> plan_actions_v4() combines: flags + A/E + sizing
       └─> Makes decision:
           ├─> Watchlist entry + buy_flag=True → Execute first buy
           │   └─> Update status='active', update total_quantity, update sell amounts, write strands
           └─> Active position → Check for adds/trims/exits
           └─> Full exit → Update status back to 'watchlist'
       └─> For non-hold decisions:
           ├─> Direct call: executor.execute(decision) [synchronous]
           └─> Write strand after execution [async, with results]

4. Executor (per-chain)
   └─> Executes trade (via chain-specific executor)
   └─> Writes to position table immediately (entries/exits JSONB)
   └─> Returns tx_hash, actual price, slippage
   └─> First buy: Updates status='active', updates total_quantity, updates sell amounts, writes strands
   └─> Full exit: Updates status back to 'watchlist'

5. Strands (for learning)
   └─> Buy strand: decision + execution result
   └─> Sell strand: decision + execution result
   └─> Hold strand: decision (no execution)
```

### Key Decisions Confirmed

1. ✅ **Multi-Timeframe Position Model** - 4 positions per token (1m, 15m, 1h, 4h) from day one
2. ✅ **Direct call** (PM → Executor) - Most reliable, simplest
3. ✅ **One table** (`lowcap_positions` with `timeframe` column) - Unique per (token, chain, timeframe)
4. ✅ **Status enum** - `dormant` (< 350 bars, only for timeframes without enough data), `watchlist` (enough data, no position - **most common starting status**), `active` (holding), `paused`, `archived`
5. ✅ **Allocation calculation** - DM sets `total_allocation_usd`, each position gets `alloc_cap_usd = total_allocation_usd * timeframe_percentage` (1m: 5%, 15m: 12.5%, 1h: 70%, 4h: 12.5%)
6. ✅ **Engine scheduling** - Per timeframe, grouped by timeframe (1m every 1m, 15m every 15m, 1h every 1h, 4h every 4h)
7. ✅ **State bootstrap required** - Run engine like backtest for dormant positions to understand current stage (where we are in cycle right now) - only bootstrap to S0/S3 (clear trends)
8. ✅ **Uptrend Engine & PM** - Engine processes all positions (dormant, watchlist, active); PM only processes watchlist + active
9. ✅ **A/E cached** in `features.pm_a_e` - Always fresh, fast reads
10. ✅ **Strands after execution** - Better for learning (includes results)
11. ✅ **Position ID tagging** - Executor tags all orders with position_id (ensures emergency exits only touch that TF's holdings)
12. ✅ **Separate executors per chain** - Clean separation, easy to extend
13. ✅ **Emergency exit = full exit** - Simplified v4 approach (removed "demote")
14. ✅ **Hold strands** - For learning/audit
15. ✅ **Executor writes directly** - No execution table needed
16. ✅ **Database reorganization** - Archive old schemas, drop tables, recreate fresh minimal schemas
17. ✅ **1m OHLC verification needed** - Must verify 1m price data → 1m OHLC conversion before Phase 0

