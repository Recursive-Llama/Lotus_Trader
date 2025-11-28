# Complete Integration Plan - Uptrend Engine v4 + Portfolio Manager

**Status**: Consolidated plan combining Architecture Plan, Token Flow Trace, and Timeframe Strategy

**Related Documents**:
- **Learning System Design**: See [`LEARNING_SYSTEM_V4.md`](./LEARNING_SYSTEM_V4.md) for detailed learning system architecture, schema changes, and implementation checklist
- **Database Schema Details**: See [`LEARNING_SYSTEM_V4.md`](./LEARNING_SYSTEM_V4.md) section "Database Schema Changes" for `learning_configs`, `learning_coefficients`, `entry_context`, and `completed_trades` schemas

---

## Build Order (Quick Reference)

**Step 1: Database Schema** (Start Here)
1. Update `lowcap_positions_v4_schema.sql`: Add `entry_context` and `completed_trades` JSONB columns
2. Create `learning_configs_schema.sql` (new table)
3. Create `learning_coefficients_schema.sql` (new table)
4. Update `curators_schema.sql`: Add `chain_counts` JSONB column
5. Verify `ad_strands` supports `kind='position_closed'` (already supported)

**Step 2: Code Implementation**
- Follow [Implementation Priority](#implementation-priority) section below
- See [`LEARNING_SYSTEM_V4.md`](./LEARNING_SYSTEM_V4.md) for learning system implementation details

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
6. **PM Core Tick** (runs timeframe-specifically: 1m=1min, 15m=15min, 1h=1hr, 4h=4hr)
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

#### 6. **PM Frequency Must Match Timeframe** ⚠️ **CRITICAL**
- **Current**: Hourly at :06 UTC (wrong - doesn't match timeframes)
- **Issue**: PM must run at same rate as timeframe being checked, otherwise misses signals
- **Fix**: Run PM timeframe-specifically:
  - **1m timeframe**: Every 1 minute
  - **15m timeframe**: Every 15 minutes
  - **1h timeframe**: Every 1 hour
  - **4h timeframe**: Every 4 hours
- **Implementation**: Run PM separately per timeframe, grouped by timeframe (processes all positions of that timeframe)

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
       └─> If approved:
           ├─> Calculates total_allocation_usd (from allocation_pct and balance)
           ├─> Creates 4 positions in lowcap_positions table (one per timeframe: 1m, 15m, 1h, 4h)
           │   ├─> Each position: alloc_cap_usd = total_allocation_usd * timeframe_percentage
           │   ├─> Sets status: 'watchlist' (if bars_count >= 350) or 'dormant' (if bars_count < 350)
           │   └─> Stores allocation splits in alloc_policy JSONB
       └─> Creates decision_lowcap strand (approve/reject)
           └─> Returns to Learning System

4. Learning System
   └─> Triggers Trader (if approved)

5. Trader Service (v4 simplified)
   └─> Validates decision was approved
   └─> Checks if positions already exist (idempotency)
   └─> Triggers async backfill for all 4 timeframes (1m, 15m, 1h, 4h) ⚠️
   └─> **Note**: No longer creates positions (Decision Maker does this)
   └─> **Note**: No first buy execution (PM handles all entries via signals)

6. Scheduled Jobs (Parallel, Independent)
   ├─> TA Tracker (every 5 min) - writes features.ta (1h only) ⚠️
   ├─> Geometry Builder (daily at :10 UTC) - writes features.geometry (1h only) ⚠️
   ├─> Uptrend Engine v4 (timeframe-specific: 1m=1min, 15m=15min, 1h=1hr, 4h=4hr) ✅
   ├─> Price Tracking (every 1 min) - writes to price tables ✅
   ├─> OHLC Conversion & Rollup (timeframe-specific) - converts 1m price points → 1m OHLC, rolls up to 15m/1h/4h ✅
   ├─> Bars Count Update (hourly) - updates bars_count for dormant positions, flips dormant → watchlist ✅
   └─> Backfill Gap Scan (hourly) - fills missing 1h bars ⚠️

7. PM Core Tick (timeframe-specific: 1m=1min, 15m=15min, 1h=1hr, 4h=4hr) ⚠️
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
| Uptrend Engine v4 | Timeframe-specific (1m=1min, 15m=15min, 1h=1hr, 4h=4hr) | ✅ Scheduled |
| Price Tracking | Every 1 min | ✅ Working |
| OHLC Conversion & Rollup | Timeframe-specific (1m=1min, 15m=15min, 1h=1hr, 4h=4hr) | ✅ Working |
| Bars Count Update | Hourly | ✅ Working |
| PM Core Tick | Timeframe-specific (1m=1min, 15m=15min, 1h=1hr, 4h=4hr) | ⚠️ Must match timeframe |
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
- **Periodic `bars_count` Update Job** (hourly):
  - Processes **only `dormant` positions** (watchlist positions are skipped)
  - Counts actual OHLC bars in `lowcap_price_data_ohlc` for each position's **specific timeframe**:
    - 15m position → counts 15m bars
    - 1h position → counts 1h bars
    - Each position has its own `bars_count` for its timeframe
  - Updates `bars_count` if changed
  - Auto-flips `dormant → watchlist` when `bars_count >= 350` for that timeframe
  - **Once a position reaches `watchlist`, it's no longer processed by this job** (already has enough data)
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

### 1m Timeframe Data Source (CRITICAL - Different from Rollup)

**Key Point**: 1m OHLC conversion is **different** from rolling up to higher timeframes.

**Data Flow**:
1. **Price Collection**: `scheduled_price_collector.py` collects 1m price points → stores in `lowcap_price_data_1m` (raw price data)
2. **1m OHLC Conversion** (special case - not a rollup):
   - Convert 1m price points → 1m OHLC bars
   - **Open**: Previous candle's close price (from previous 1m OHLC bar)
   - **Close**: Current candle's price (from `lowcap_price_data_1m`)
   - **High**: `max(open, close)` (highest of the two prices)
   - **Low**: `min(open, close)` (lowest of the two prices)
   - **Volume**: Sum of volumes for the 1-minute window (if available)
   - **Why different**: We're creating OHLC from price points, not aggregating multiple bars
3. **OHLC Rollup** (standard aggregation):
   - Roll up 1m OHLC → 15m OHLC (aggregate 15 bars)
   - Roll up 1m OHLC → 1h OHLC (aggregate 60 bars)
   - Roll up 1m OHLC → 4h OHLC (aggregate 240 bars)
   - Standard logic: Open=first bar's open, Close=last bar's close, High=max(highs), Low=min(lows), Volume=sum(volumes)

**Storage**: All timeframes (1m, 15m, 1h, 4h) stored in `lowcap_price_data_ohlc` with `timeframe` column

**Usage**: PM and Uptrend Engine read from `lowcap_price_data_ohlc` (filtered by `timeframe`), NOT from `lowcap_price_data_1m`

**⚠️ CRITICAL VERIFICATION NEEDED**:
- **Action Item**: Verify 1m price data → 1m OHLC conversion uses correct logic (Open=previous close, Close=current price)
- **Test**: Ensure 1m OHLC conversion produces valid bars that engine can process
- **Test**: Ensure rollup from 1m → 15m → 1h → 4h works correctly
- **Edge Cases**: Handle gaps, missing data, volume calculation, first bar (no previous close)
- **Must verify before Phase 0 implementation**

### Timeframe Implementation Requirements

**Modules that need timeframe support**:

1. **Backfill** (`geckoterminal_backfill.py`):
   - Add `timeframe` parameter (default '1h' for backward compat)
   - Map timeframe to GeckoTerminal endpoint (1m, 15m, 1h, 4h)
   - **Fetches correct timeframe directly from API** (no rollup - rollup is only for ongoing data collection)
   - Store with correct `timeframe` field in `lowcap_price_data_ohlc`

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
   - **Price Tracking**: Collects 1m price data every 1 minute → stores in `lowcap_price_data_1m` (raw price points)
   - **1m OHLC Conversion** (CRITICAL - different from rollup):
     - Convert 1m price points → 1m OHLC bars
     - **Open**: Previous candle's close price (or first price if no previous candle)
     - **Close**: Current candle's price (from `lowcap_price_data_1m`)
     - **High**: `max(open, close)` (highest of the two)
     - **Low**: `min(open, close)` (lowest of the two)
     - **Volume**: Sum of volumes for the 1-minute window (if available)
     - **Why different**: This is creating OHLC from price points, not rolling up to higher timeframe
   - **OHLC Rollup**: Rolls up 1m OHLC → 15m OHLC → 1h OHLC → 4h OHLC
     - Uses standard OHLC rollup logic: Open=first bar's open, Close=last bar's close, High=max(highs), Low=min(lows), Volume=sum(volumes)
   - **Storage**: All timeframes stored in `lowcap_price_data_ohlc` with correct `timeframe` column (1m, 15m, 1h, 4h)
   - **Usage**: PM and Uptrend Engine read from `lowcap_price_data_ohlc` (not `lowcap_price_data_1m`)

6. **Bars Count Update** (`update_bars_count.py`):
   - **Purpose**: Periodically update `bars_count` for `dormant` positions and auto-flip `dormant → watchlist` when threshold reached
   - **Frequency**: Hourly (runs once per hour for all dormant positions)
   - **Process**:
     - Queries **only `dormant` positions** (watchlist positions are skipped - already have enough data)
     - For each dormant position:
       - Counts actual OHLC bars in `lowcap_price_data_ohlc` for that position's **specific timeframe**:
         - Filters by `token_contract`, `chain`, and `timeframe` (position's timeframe)
         - 15m position → counts 15m bars
         - 1h position → counts 1h bars
         - Each position has its own `bars_count` for its timeframe
       - Updates `bars_count` if changed
       - Auto-flips `dormant → watchlist` when `bars_count >= 350` for that timeframe
     - **Once a position reaches `watchlist`, it's no longer processed by this job**
   - **Why needed**: Ongoing OHLC conversion/rollup jobs add new bars, but don't update position `bars_count` or trigger status transitions
   - **Efficiency**: Uses caching to avoid duplicate counts for positions sharing same token/chain/timeframe

7. **PM** (`pm_core_tick.py`):
   - Processes positions grouped by status: `watchlist` + `active` only (skips `dormant`)
   - Each position already has its timeframe (read from position row)
   - Reads `features.uptrend_engine_v4` (no timeframe suffix needed - stored per position)
   - **Frequency**: Timeframe-specific (runs at same rate as timeframe being checked)
     - **1m timeframe**: Every 1 minute
     - **15m timeframe**: Every 15 minutes
     - **1h timeframe**: Every 1 hour
     - **4h timeframe**: Every 4 hours
   - **Implementation**: Run PM separately per timeframe, grouped by timeframe (not by token)
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
   - Store per position: `features.pm_execution_history` (tracks last execution per signal type - **REQUIRED**)
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

**Note**: This section details the PM-Executor interaction. For learning system integration, see [`LEARNING_SYSTEM_V4.md`](./LEARNING_SYSTEM_V4.md) section "Complete Learning Feedback Loop".

### Current Flow

#### Step 1: PM Core Tick
**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

**Schedule**: Timeframe-specific (runs at same rate as timeframe being checked)
- **1m timeframe**: Every 1 minute
- **15m timeframe**: Every 15 minutes
- **1h timeframe**: Every 1 hour
- **4h timeframe**: Every 4 hours
- **Implementation**: Run PM separately per timeframe, grouped by timeframe (processes all positions of that timeframe)

**What happens**:
1. Gets all active positions
2. Reads portfolio phase (meso, macro) and cut pressure
3. For each position:
   - Reads `features.uptrend_engine_v4` (expects engine to have run)
   - Calls `compute_levers()` to compute A/E scores
   - Calls `plan_actions()` to generate decisions
   - **Writes to `ad_strands` table** with decision (only for actions, not holds):
     ```json
     {
       "kind": "pm_action",
       "token": "contract_address",
       "position_id": "uuid",
       "timeframe": "1h",
       "chain": "base",
       "timestamp": "2024-01-15T10:06:00Z",
       "decision_type": "add|trim|emergency_exit",
       "size_frac": 0.25,
       "reasons": {
         "flag": "buy_signal",  // or "buy_flag", "trim_flag", "emergency_exit", "first_dip_buy_flag", "reclaimed_ema333"
         "state": "S1",
         "a_score": 0.75,
         "ts_score": 0.65
       },
       "lever_diag": {
         "a_final": 0.75,
         "e_final": 0.30,
         "phase_meso": "uptrend",
         "cut_pressure": 0.15
       },
       "execution_result": {
         // Added after execution (from executor return)
         "status": "success",
         "tx_hash": "...",
         "price": 0.0015,
         "tokens_bought": 1000,
         "slippage": 0.02
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

**What happens** (CORRECTED DESIGN):
1. **PM Core Tick directly calls executor** (no events):
   ```python
   result = executor.execute(decision, position)
   ```
2. **Executor executes** (executor does NOT write to database):
   - Gets position from database (revalidation)
   - **Gets latest price** from `lowcap_price_data_ohlc` table (filtered by position's timeframe)
     - For 1m positions: Reads 1m OHLC bars
     - For 15m positions: Reads 15m OHLC bars
     - For 1h positions: Reads 1h OHLC bars
     - For 4h positions: Reads 4h OHLC bars
   - **Checks balance** on target chain (USDC + native gas)
   - Executes based on `decision_type`:
     - **`"add"`**: 
       - Calculates `notional_usd = total_allocation_usd * size_frac`
       - Executes trade using Li.Fi SDK (USDC → token swap)
       - Returns `{"status": "success", "tx_hash": "...", "tokens_bought": ..., "price": ..., "slippage": ...}`
     - **`"trim"`**: 
       - Calculates `tokens_to_sell = total_quantity * size_frac`
       - Executes trade using Li.Fi SDK (token → USDC swap)
       - Returns `{"status": "success", "tx_hash": "...", "tokens_sold": ..., "price": ..., "slippage": ...}`
     - **`"emergency_exit"`**: 
       - Same as trim with `size_frac = 1.0` (full exit)
       - Returns execution result
   - **After execution**: Checks if rebalancing needed (bridge funds if balance below threshold)
   - **Execution is immediate** (synchronous) - no price condition checking
   - **Returns execution result** (success/error, tx_hash, tokens, price, slippage)
   - **Executor does NOT write to database** - only returns results to PM
   - **Note**: See [Fund Management & Bridging Strategy](#fund-management--bridging-strategy) for detailed bridging logic

3. **PM updates position table** (PM does all database writes):
   - Updates `total_quantity` based on executor results
   - Updates `total_investment_native`, `total_extracted_native`
   - Updates `total_tokens_bought`, `total_tokens_sold`
   - Updates `features.pm_execution_history` (tracks last execution per signal type)
   - If position fully closed: Sets `status='watchlist'`, `closed_at=now()`, computes R/R, writes `completed_trades` JSONB

4. **PM emits strand after execution** (non-blocking):
   - Includes execution result in strand
   - Learning system can analyze: decision → execution → outcome
   - Written asynchronously (doesn't block execution)

**Key Points**:
- **Price source**: `lowcap_price_data_ohlc` (OHLC bars for position's timeframe: 1m, 15m, 1h, 4h)
- **Execution timing**: Immediate (direct call, no event overhead)
- **Error handling**: Direct exception propagation (easier to debug)
- **Executor role**: Only executes trades, returns results (no database writes)
- **PM role**: Does all database writes (position updates, execution history, strands)
- **Strands**: Written after execution with results (better for learning)

**Why Direct Call**:
- More reliable (no event system to fail)
- Faster (direct function call)
- Simpler (fewer moving parts)
- Better error handling (exceptions propagate)
- Still has audit trail (strands written after)

---

## Fund Management & Bridging Strategy

**Status**: v4 enhancement using Li.Fi SDK for unified cross-chain execution

**Related**: See [`scripts/lifi_sandbox/README.md`](../../../scripts/lifi_sandbox/README.md) for Li.Fi SDK integration details

### Overview

**Problem**: Different ecosystems have different tokens. Most trading happens on Solana, but we need to support Base, BSC, and Ethereum. Maintaining separate balances on all chains is capital inefficient.

**Solution**: Centralized fund management with on-demand bridging using Li.Fi SDK.

### Fund Management Strategy

#### Home Base Chain
- **Primary**: Solana (configurable, but Solana is default)
- **Rationale**: Most trading happens on Solana, lowest fees, fast execution
- **Allocation Calculation**: All `total_allocation_usd` calculations are based on **USDC balance on Solana** (home base)

#### Per-Chain Reserves (Pre-Positioned)
Each chain maintains minimum reserves to support at least 1 trade:

- **Base**: $100 USDC + $15 ETH (for gas)
- **BSC**: $100 USDC + $15 BNB (for gas)
- **Ethereum**: $100 USDC + $15 ETH (for gas)
- **Solana**: All remaining USDC + SOL (for gas)

**Initial Setup**: Bridge $100 USDC + $15 native token to each chain on system startup.

**Maintenance Thresholds**:
- **USDC minimum**: $100 per chain (aim to keep above this)
- **Native gas minimum**: $15 per chain (pre-positioned), top-up threshold is $10 (swap from USDC on same chain when below $10)
- **Auto-rebalancing**: When a position opens, bridge additional funds to maintain buffer
- **Gas management**: Use USDC on chain to swap for native gas (primary method), or bridge $100 native if completely out of gas

### Bridging Rules

#### Minimum Bridge Size
- **Minimum**: $100 USDC (configurable)
- **Rationale**: Bridge fees are acceptable above this threshold; below this, fees become significant percentage

#### Bridging Strategy (All Timeframes)
**Same strategy for all timeframes** (1m, 15m, 1h, 4h):
- Pre-positioned funds for at least 1 trade per chain
- Bridge additional funds when depleted (after trade executes)
- Execute trade first, then bridge more if needed (non-blocking)

**Flow**:
1. **Check balance** on target chain
2. **If sufficient**: Execute trade immediately
3. **If insufficient**: 
   - Execute trade using pre-positioned funds
   - **After execution**: Trigger bridge to replenish (async, non-blocking)
   - Bridge amount: `notional_usd + buffer` to maintain $100+ USDC reserve

#### Gas Token Management
**Hybrid Strategy**:
- **Pre-positioned**: $15 native token per chain (ETH, BNB, SOL)
- **Primary method**: Swap USDC → native on the same chain (using USDC already on that chain)
- **Fallback**: Bridge $100 native token from Solana if completely out of gas, then swap $85 → USDC on arrival

**Gas Top-Up Flow**:
1. Check native balance on target chain
2. **If < $10** (threshold):
   - **First**: Check if USDC balance on that chain is sufficient
   - **If USDC available**: Swap USDC → native on same chain (using Li.Fi SDK spot swap, amount: $10-15)
   - **If no USDC available AND no gas**: 
     - Bridge $100 native token (ETH/BNB) from Solana (meets $100 minimum bridge size)
     - Once bridge completes: Swap $85 → USDC on target chain, keep $15 for gas
     - **Rationale**: This gives us both gas AND USDC on the target chain, meeting minimum bridge size
3. **Rationale**: 
   - Use existing USDC on chain first (no bridge needed)
   - If completely out of gas: Bridge $100 native, then swap most of it to USDC
   - Avoids constant small bridges for gas

### Executor Integration

**Related**: See [`scripts/lifi_sandbox/README.md`](../../../scripts/lifi_sandbox/README.md) for detailed Li.Fi SDK integration, test suite, and implementation guide.

#### Li.Fi SDK Integration

**Unified Execution Layer**:
- **Single SDK**: One interface for all chains (Solana, Base, BSC, Ethereum)
- **USDC Support**: Native USDC → token swaps (no native currency conversion needed)
- **Cross-Chain**: Built-in bridging when needed
- **Route Finding**: SDK finds optimal routes automatically
- **Transaction Capture**: Use `updateRouteHook` to capture txHash immediately
- **Confirmation**: Use our own RPC for fast, reliable confirmation (SDK confirmation can be slow)

**Key SDK Methods**:
- `getQuote()`: Find optimal route for swap
- `executeRoute()`: Execute swap/bridge with `updateRouteHook` for txHash capture
- **Input**: USDC amount, target token, chain
- **Output**: Transaction hash, execution status, actual tokens received

**Implementation Details**:
- See [`scripts/lifi_sandbox/README.md`](../../../scripts/lifi_sandbox/README.md) for:
  - Wallet setup (Solana + EVM)
  - Transaction capture hook pattern
  - Confirmation polling strategy
  - Cross-chain bridge handling
  - Error handling and retry logic

#### Enhanced Execution Flow

```python
def execute(decision, position):
    chain = position['token_chain']
    timeframe = position['timeframe']
    notional_usd = calculate_notional(decision, position)
    
    # Check USDC balance on target chain
    usdc_balance = get_balance(chain, 'USDC')
    
    # Execute trade (always use pre-positioned funds)
    if usdc_balance < notional_usd:
        # Should not happen if rebalancing works correctly
        # But if it does, we still try to execute (may fail)
        logger.warning(f"Insufficient USDC on {chain}: ${usdc_balance} < ${notional_usd}")
    
    # Execute trade immediately (non-blocking on bridge)
    result = execute_trade(decision, position)
    
    # After execution: Check if rebalancing needed
    if result.status == "success":
        # Check if balance is below threshold
        remaining_balance = usdc_balance - notional_usd
        if remaining_balance < MIN_USDC_RESERVE:  # $100
            # Trigger bridge to replenish (async, non-blocking)
            bridge_amount = MIN_USDC_RESERVE + notional_usd  # Bridge enough for next trade + buffer
            if bridge_amount >= MIN_BRIDGE_SIZE:  # $100
                bridge_usdc_async(
                    source_chain='solana',
                    target_chain=chain,
                    amount=bridge_amount
                )
        
        # Check native gas balance (use USDC on chain first, bridge native if completely out)
        native_balance = get_balance(chain, 'native')
        if native_balance < MIN_NATIVE_RESERVE:  # $10 (threshold)
            # First try: Swap USDC → native on same chain (if USDC available)
            usdc_on_chain = get_balance(chain, 'USDC')
            if usdc_on_chain >= GAS_SWAP_AMOUNT:  # $10-15
                swap_usdc_to_native_async(chain, amount=GAS_SWAP_AMOUNT)
            else:
                # Fallback: Bridge $100 native token from Solana (meets minimum bridge size)
                # Once bridge completes: Swap $85 → USDC, keep $15 for gas
                # This gives us both gas AND USDC on target chain
                bridge_native_async(
                    source_chain='solana',
                    target_chain=chain,
                    amount=100.0  # Bridge $100 native (ETH/BNB)
                )
                # After bridge completes: swap $85 → USDC, keep $15 for gas
                # (This happens in bridge completion callback)
    
    return result
```

#### Bridge Failure Handling

**Strategy**: Retry with exponential backoff, but avoid infinite loops.

**Implementation**:
- **Retry limit**: 3 attempts (configurable)
- **Backoff**: Exponential (1s, 2s, 4s)
- **Failure handling**: 
  - Log error and continue (trade already executed)
  - Alert if balance remains below threshold after retries
  - Manual intervention may be required

**Note**: Bridge failures don't block trades (we always have pre-positioned funds). Worst case: We execute trade, bridge fails, need to manually top up later.

### Balance Tracking

#### Database Schema
**Table**: `wallet_balances` (already exists)

**Structure**:
```sql
wallet_balances (
    chain TEXT PRIMARY KEY,        -- 'solana', 'ethereum', 'base', 'bsc'
    balance FLOAT NOT NULL,        -- Current native token balance (for gas)
    balance_usd FLOAT,            -- Current USD value of native balance
    usdc_balance FLOAT,           -- Current USDC balance (NEW - for tracking USDC separately per chain)
    wallet_address TEXT,
    last_updated TIMESTAMPTZ DEFAULT NOW()
)
```

**Tracking**:
- **USDC per chain**: Yes, tracked separately in `usdc_balance` column (one row per chain)
- **Native per chain**: Tracked in `balance` column (one row per chain)
- **Updates**: After each trade execution, after each bridge completion, periodic reconciliation (hourly)

### Allocation Calculation

**Critical Change**: All allocation calculations use **Solana USDC balance** as the base.

**Decision Maker Flow**:
1. Get USDC balance from Solana (`wallet_balances` where `chain='solana'`)
2. Calculate `total_allocation_usd = (allocation_pct / 100.0) * solana_usdc_balance`
3. Create positions with this allocation
4. Each position's `alloc_cap_usd` is based on this Solana-based total

**Rationale**: 
- Centralized capital management
- All allocations relative to home base balance
- Pre-positioned funds on other chains are operational reserves, not part of allocation calculation

### Implementation Checklist

1. **Update `wallet_balances` schema**: Add `usdc_balance` column
2. **Update balance tracking**: Track USDC separately from native tokens
3. **Implement bridge checks**: In executor, check balances before/after execution
4. **Implement auto-rebalancing**: Bridge funds when balance drops below threshold
5. **Update allocation calculation**: Use Solana USDC balance as base
6. **Add bridge failure handling**: Retry logic with exponential backoff
7. **Add monitoring**: Alert when balances below threshold for extended period

### Future Enhancements

- **Dynamic rebalancing**: Adjust reserves based on trading frequency per chain
- **Bridge cost optimization**: Batch multiple small bridges into one larger bridge
- **Cross-chain position management**: Bridge profits back to Solana automatically
- **Gas price optimization**: Time gas top-ups based on network congestion

---

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
   └─> Makes decision: add/trim/emergency_exit/hold
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
    # Only execute and emit strands for actions (not holds)
    if decision["decision_type"] not in ["hold", None]:
        # Execute immediately (direct call)
        result = executor.execute(decision, position)
        
        # PM updates position table (executor just returns results, PM does all writes)
        new_total_quantity = position['total_quantity'] + result.get('tokens_bought', 0) - result.get('tokens_sold', 0)
        update_position(position_id, {
            'total_quantity': new_total_quantity,
            'total_investment_native': updated_investment,
            'total_extracted_native': updated_extracted,
            'total_tokens_bought': updated_tokens_bought,
            'total_tokens_sold': updated_tokens_sold,
        })
        
        # Update execution history
        exec_history = position.get('features', {}).get('pm_execution_history', {})
        exec_history['prev_state'] = current_state
        if decision["decision_type"] == "add":
            signal_type = decision["reasons"].get("flag", "unknown")  # Flag is now a string field
            exec_history[f'last_{current_state.lower()}_buy'] = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'price': result.get('price'),
                'size_frac': decision.get('size_frac'),
                'signal': signal_type
            }
        elif decision["decision_type"] == "trim":
            # Get current S/R level
            sr_levels = features.get("geometry", {}).get("levels", {}).get("sr_levels", [])
            current_sr_level = None
            if sr_levels and result.get('price'):
                closest_sr = min(sr_levels, key=lambda x: abs(float(x.get("price", 0)) - result.get('price')))
                current_sr_level = float(closest_sr.get("price", 0))
            
            exec_history['last_trim'] = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'price': result.get('price'),
                'size_frac': decision.get('size_frac'),
                'signal': 'trim_flag',
                'sr_level_price': current_sr_level
            }
        
        # Update features with execution history
        position['features']['pm_execution_history'] = exec_history
        update_position(position_id, {'features': position['features']})
        
        # Check if position fully closed (for final exits only: emergency_exit with size_frac=1.0)
        # Note: This applies to ANY full exit (emergency_exit OR trim with size_frac=1.0)
        is_full_exit = (
            decision["decision_type"] == "emergency_exit" or
            (decision["decision_type"] == "trim" and decision.get("size_frac", 0) >= 1.0)
        )
        if is_full_exit and new_total_quantity == 0:
            # Compute R/R from OHLCV, write completed_trades, emit position_closed strand
            # (See LEARNING_SYSTEM_V4.md for full flow)
            # This includes: R/R calculation, completed_trades JSONB, position_closed strand with all learning data
            completed_trade = compute_rr_from_ohlcv(position)
            position['completed_trades'].append(completed_trade)
            update_position(position_id, {
                'status': 'watchlist',
                'closed_at': datetime.now(timezone.utc),
                'completed_trades': position['completed_trades']
            })
            # Emit position_closed strand with all learning data
            # (See LEARNING_SYSTEM_V4.md section "Critical Role: Feedback Loop" for complete structure)
            emit_strand({
                'kind': 'position_closed',
                'position_id': position_id,
                'token': position['token_contract'],
                'chain': position['token_chain'],
                'timeframe': position['timeframe'],
                'completed_trade': completed_trade,  # Includes: entry/exit prices, min/max prices, R/R, return, max_drawdown, max_gain
                'entry_context': position['entry_context']  # Includes: curator, chain, mcap_bucket, vol_bucket, age_bucket, intent, mapping_confidence, etc.
            })
        
        # Write strand after execution (with result, non-blocking)
        # Strand includes: kind, token, position_id, timeframe, chain, decision_type, size_frac, reasons, execution_result
        write_strand_async({
            'kind': 'pm_action',
            'token': position['token_contract'],
            'position_id': position_id,
            'timeframe': position['timeframe'],
            'chain': position['token_chain'],
            'decision_type': decision['decision_type'],
            'size_frac': decision.get('size_frac'),
            'reasons': decision.get('reasons', {}),
            'execution_result': result
        })
    # Hold decisions: No strand emitted (no action taken)
```

**Strands for Learning**:
- Strands written **after execution** (with execution results)
- **Only for actions** (add, trim, emergency_exit) - no strands for holds
- Strand includes: `kind='pm_action'`, `position_id`, `timeframe`, `chain`, `token`, `decision_type`, `reasons.flag`, `execution_result`
- Learning system can analyze: decision → execution → outcome
- Non-blocking write (doesn't slow down execution)
- Better for learning (has actual execution results)

**Naming Issue**:
- Events path deprecated (e.g., `decision_approved`); direct call is the only supported path

### Data Flow Summary

```
1. Price Tracking (every 1 min)
   └─> Writes to lowcap_price_data_1m (raw price points)

2. OHLC Conversion & Rollup (every 1 min)
   └─> Converts 1m price points → 1m OHLC bars (Open=previous close, Close=current price, High/Low=max/min)
   └─> Rolls up 1m OHLC → 15m OHLC (every 15 min)
   └─> Rolls up 1m OHLC → 1h OHLC (every 1 hour)
   └─> Rolls up 1m OHLC → 4h OHLC (every 4 hours)
   └─> All stored in lowcap_price_data_ohlc with timeframe column

3. Uptrend Engine (timeframe-specific)
   └─> 1m: Every 1 minute
   └─> 15m: Every 15 minutes
   └─> 1h: Every 1 hour
   └─> 4h: Every 4 hours
   └─> Reads OHLC data from lowcap_price_data_ohlc (filtered by timeframe)
   └─> Checks price conditions
   └─> Writes signals to features.uptrend_engine_v4

4. PM Core Tick (timeframe-specific)
   └─> 1m: Every 1 minute
   └─> 15m: Every 15 minutes
   └─> 1h: Every 1 hour
   └─> 4h: Every 4 hours
   └─> Processes all positions of that timeframe (watchlist + active)
   └─> Reads features.uptrend_engine_v4
   └─> Reads features.pm_execution_history (for signal tracking)
   └─> Computes A/E scores
   └─> Calculates profit/allocation multipliers
   └─> plan_actions_v4() generates decisions (checks execution history, applies multipliers)
   └─> Calls executor.execute() → Executor returns results (no database writes)
   └─> PM updates position table (total_quantity, execution_history, etc.)
   └─> If position closed: Computes R/R, writes completed_trades, emits position_closed strand
   └─> Writes strand after execution (async, with results)

5. PM Executor (direct call)
   └─> Gets latest price from lowcap_price_data_ohlc (filtered by position's timeframe)
   └─> Executes trade immediately
   └─> Returns results to PM (tx_hash, price, tokens, slippage)
   └─> Does NOT write to database (PM does all database writes)
```

### What PM Outputs

**PM Core Tick outputs**:
- `ad_strands` table rows (only for actions, not holds) with:
  - `kind`: "pm_action" (or "position_closed" for final exits)
  - `position_id`: UUID linking to position
  - `timeframe`: Position's timeframe (1m, 15m, 1h, 4h)
  - `chain`: Position's chain (base, solana, ethereum, bsc)
  - `token`: Contract address
  - `decision_type`: "add", "trim", "emergency_exit"
  - `size_frac`: Fraction of allocation (for adds) or position (for trims)
  - `reasons`: Dict with `flag` (string: "buy_signal", "buy_flag", "trim_flag", "emergency_exit", "first_dip_buy_flag", "reclaimed_ema333"), state, scores, etc.
  - `lever_diag`: Dict with A/E scores and phase info
  - `execution_result`: Dict with tx_hash, price, tokens, slippage (added after execution)

**PM Executor**:
- Invoked directly by PM (no event bus)
- Gets latest price from `lowcap_price_data_ohlc` (filtered by position's timeframe)
- Executes via Li.Fi SDK (unified cross-chain execution)
- Handles bridging automatically (USDC → token swaps, cross-chain bridges)
- See [Fund Management & Bridging Strategy](#fund-management--bridging-strategy) for details

---

## Portfolio Manager Integration

### Current State

#### What's Working:
- ✅ A/E scores computed correctly (`compute_levers()`)
- ✅ PM Core Tick runs timeframe-specifically (1m=1min, 15m=15min, 1h=1hr, 4h=4hr)
- ✅ PM Executor callable (direct execution path)
- ✅ Decision types supported (`add`, `trim`, `emergency_exit`, `hold`)

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

**Key Logic**:
- **Signal Persistence**: Flags are recomputed each tick by engine (don't persist). PM must track execution history to prevent duplicate executions.
- **Buy Signal Tracking**: 
  - S1: One-time initial entry (only when transitioning S0 → S1). S2 → S1 doesn't reset (S1 buy only happens once).
  - S2/S3: Reset when we trim OR state transitions S2 → S3
  - **Trim Signal Tracking**: 
    - 1 trim per 3-bar cooldown (timeframe-specific: 1m=3min, 15m=45min, 1h=3hr, 4h=12hr), OR
    - Price moves to next S/R level (up or down) and signal fires again
- **Profit/Allocation Multipliers**: Applied in `plan_actions_v4()` based on current position state

```python
def plan_actions_v4(position: Dict[str, Any], a_final: float, e_final: float, phase_meso: str) -> List[Dict[str, Any]]:
    """
    New PM action planning using Uptrend Engine v4 signals + A/E scores.
    
    Includes:
    - Signal execution tracking (prevents duplicate executions)
    - Profit/allocation multipliers (affects sizing)
    - Cooldown logic (trims: 3 bars per timeframe or new S/R level)
    """
    features = position.get("features") or {}
    uptrend = features.get("uptrend_engine_v4") or {}  # This IS the payload
    exec_history = features.get("pm_execution_history") or {}
    
    state = uptrend.get("state", "")
    prev_state = exec_history.get("prev_state", "")
    actions = []
    
    # Calculate profit/allocation multipliers (used for sizing)
    total_allocation_usd = float(position.get("total_allocation_usd") or 0.0)
    total_extracted_native = float(position.get("total_extracted_native") or 0.0)
    total_quantity = float(position.get("total_quantity") or 0.0)
    current_price = float(uptrend.get("price") or 0.0)
    current_position_value = total_quantity * current_price if current_price > 0 else 0.0
    
    # Entry multiplier (for S2/S3 only, S1 uses base size)
    profit_ratio = total_extracted_native / total_allocation_usd if total_allocation_usd > 0 else 0.0
    if profit_ratio >= 1.0:
        entry_multiplier = 0.3  # 100%+ profit: smaller buys
    elif profit_ratio >= 0.0:
        entry_multiplier = 1.0  # Breakeven: normal buys
    else:
        entry_multiplier = 1.5  # In loss: larger buys to average down
    
    # Trim multiplier
    allocation_deployed_ratio = current_position_value / total_allocation_usd if total_allocation_usd > 0 else 0.0
    if allocation_deployed_ratio >= 0.8:
        trim_multiplier = 3.0  # Nearly maxed out: take more profit
    elif profit_ratio >= 1.0:
        trim_multiplier = 0.3  # 100%+ profit: take less profit
    elif profit_ratio >= 0.0:
        trim_multiplier = 1.0  # Breakeven: normal trims
    else:
        trim_multiplier = 0.5  # In loss: smaller trims, preserve capital
    
    # Exit Precedence (highest priority)
    if uptrend.get("exit_position"):
        # Full exit - emergency or structural invalidation
        actions.append({
            "decision_type": "emergency_exit",  # Changed from "demote"
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
            "decision_type": "emergency_exit",  # Changed from "demote"
            "size_frac": 1.0,
            "reasons": {"emergency_exit": True, "e_score": e_final, "state": state}
        })
        return actions
    
    # Trim Flags (S2/S3) - Check cooldown and S/R level
    if uptrend.get("trim_flag"):
        # Check if we can trim (cooldown or new S/R level)
        last_trim = exec_history.get("last_trim", {})
        last_trim_ts = last_trim.get("timestamp")
        last_trim_sr_level = last_trim.get("sr_level_price")
        
        # Get current S/R level (closest to price)
        sr_levels = features.get("geometry", {}).get("levels", {}).get("sr_levels", [])
        current_sr_level = None
        if sr_levels and current_price > 0:
            closest_sr = min(sr_levels, key=lambda x: abs(float(x.get("price", 0)) - current_price))
            current_sr_level = float(closest_sr.get("price", 0))
        
        can_trim = False
        if not last_trim_ts:
            # Never trimmed before
            can_trim = True
        else:
            # Check cooldown (3 bars for position's timeframe)
            # Query OHLC data to count bars since last trim
            timeframe = position.get("timeframe", "1h")  # Position's timeframe
            bars_since_trim = count_bars_since(last_trim_ts, contract, chain, timeframe)
            cooldown_expired = bars_since_trim >= 3
            
            # Check if price moved to new S/R level
            sr_level_changed = False
            if last_trim_sr_level and current_sr_level:
                # Price moved to different S/R level (up or down)
                sr_level_changed = abs(current_sr_level - last_trim_sr_level) > (current_price * 0.01)  # 1% threshold
            
            can_trim = cooldown_expired or sr_level_changed
        
        if can_trim:
            trim_size = _e_to_trim_size(e_final) * trim_multiplier
            trim_size = min(trim_size, 1.0)  # Cap at 100%
        actions.append({
            "decision_type": "trim",
            "size_frac": trim_size,
            "reasons": {
                    "flag": "trim_flag",  # Changed from "trim_flag": True
                "state": state,
                "e_score": e_final,
                "ox_score": uptrend.get("scores", {}).get("ox", 0.0),
                    "trim_multiplier": trim_multiplier,
                    "cooldown_expired": cooldown_expired if last_trim_ts else True,
                    "sr_level_changed": sr_level_changed if last_trim_ts else False,
            }
        })
        return actions
    
    # Entry Gates (S1, S2, S3) - Check execution history
    buy_signal = uptrend.get("buy_signal", False)  # S1
    buy_flag = uptrend.get("buy_flag", False)  # S2 retest or S3 DX
    first_dip_buy_flag = uptrend.get("first_dip_buy_flag", False)  # S3 first dip
    
    # S1: One-time initial entry (only on S0 → S1 transition)
    if buy_signal and state == "S1":
        last_s1_buy = exec_history.get("last_s1_buy")
        if not last_s1_buy:
            # Never bought in S1, and we're in S1 (transitioned from S0)
            entry_size = _a_to_entry_size(a_final, state, buy_signal=True, buy_flag=False, first_dip_buy_flag=False)
        if entry_size > 0:
            actions.append({
                "decision_type": "add",
                "size_frac": entry_size,
                "reasons": {
                        "flag": "buy_signal",  # Changed from "buy_signal": True
                        "state": state,
                        "a_score": a_final,
                        "ts_score": uptrend.get("scores", {}).get("ts", 0.0),
                    }
                })
                return actions
    
    # S2/S3: Reset on trim or state transition
    if (buy_flag or first_dip_buy_flag) and state in ["S2", "S3"]:
        last_buy = exec_history.get(f"last_{state.lower()}_buy", {})
        last_trim_ts = exec_history.get("last_trim", {}).get("timestamp")
        state_transitioned = (prev_state != state)  # State changed (S2 → S3 or S3 → S2)
        
        # Reset conditions: trim happened OR state transitioned
        can_buy = False
        if not last_buy:
            # Never bought in this state
            can_buy = True
        elif state_transitioned:
            # State transitioned (S2 → S3 or S3 → S2) - reset buy eligibility
            can_buy = True
        elif last_trim_ts:
            # Check if trim happened after last buy
            last_buy_ts = last_buy.get("timestamp")
            if last_buy_ts:
                from datetime import datetime, timezone
                trim_dt = datetime.fromisoformat(last_trim_ts.replace("Z", "+00:00"))
                buy_dt = datetime.fromisoformat(last_buy_ts.replace("Z", "+00:00"))
                if trim_dt > buy_dt:
                    # Trim happened after last buy - reset buy eligibility
                    can_buy = True
        
        if can_buy:
            entry_size = _a_to_entry_size(a_final, state, buy_signal=False, buy_flag=buy_flag, first_dip_buy_flag=first_dip_buy_flag)
            entry_size = entry_size * entry_multiplier  # Apply profit/allocation multiplier
            if entry_size > 0:
                # Determine which flag triggered this buy
                flag_type = "buy_flag" if buy_flag else ("first_dip_buy_flag" if first_dip_buy_flag else "unknown")
                actions.append({
                    "decision_type": "add",
                    "size_frac": entry_size,
                    "reasons": {
                        "flag": flag_type,  # Changed from separate boolean fields
                    "state": state,
                    "a_score": a_final,
                    "ts_score": uptrend.get("scores", {}).get("ts", 0.0),
                    "dx_score": uptrend.get("scores", {}).get("dx", 0.0),
                        "entry_multiplier": entry_multiplier,
                }
            })
            return actions
    
    # Reclaimed EMA333 (S3 auto-rebuy)
    if state == "S3" and uptrend.get("reclaimed_ema333"):
        # Check if we already rebought on this reclaim
        last_reclaim_buy = exec_history.get("last_reclaim_buy", {})
        if not last_reclaim_buy or last_reclaim_buy.get("reclaimed_at") != uptrend.get("ts"):
            rebuy_size = _a_to_entry_size(a_final, state, False, False, False) * entry_multiplier
        if rebuy_size > 0:
            actions.append({
                "decision_type": "add",
                "size_frac": rebuy_size,
                "reasons": {
                    "flag": "reclaimed_ema333",  # Changed from "reclaimed_ema333": True
                    "state": state,
                    "a_score": a_final,
                    "entry_multiplier": entry_multiplier,
                }
            })
            return actions
    
    # Default: No action (don't emit strand for holds)
    return actions  # Empty list = no action, no strand
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
- **Implementation**: Applied in `plan_actions_v4()` - recalculated after each execution

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
- **Implementation**: Applied in `plan_actions_v4()` - recalculated after each execution

**Trim Cooldown Logic**:
- **Cooldown**: 3 bars minimum between trims (timeframe-specific)
  - **1m timeframe**: 3 bars = 3 minutes
  - **15m timeframe**: 3 bars = 45 minutes
  - **1h timeframe**: 3 bars = 3 hours
  - **4h timeframe**: 3 bars = 12 hours
- **OR**: Price moves to next S/R level (up or down) and signal fires again
- **Tracking**: `pm_execution_history.last_trim` stores timestamp, S/R level price, and bar count
- **Reset**: Trim allowed if cooldown expired (3 bars for position's timeframe) OR S/R level changed
- **Implementation**: Track bars since last trim using position's timeframe (query `lowcap_price_data_ohlc` for bars since last trim timestamp)

**Tunable Trim Thresholds** (Future):
- Each E level can have different OX thresholds
- More aggressive = lower OX thresholds for trims

#### Exit Types

- **Emergency exit** = Full exit (`emergency_exit` with `size_frac: 1.0`) - Changed from "demote"
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

#### Execution History Tracking (Required for Signal Persistence)

**New field**: `features.pm_execution_history` JSONB (no schema change needed)

**Purpose**: Track last execution per signal type to prevent duplicate executions.

**Structure**:
```json
{
  "pm_execution_history": {
    "prev_state": "S2",  // Previous state (for detecting state transitions)
    "last_s1_buy": {
      "timestamp": "2024-01-15T10:00:00Z",
      "price": 0.0015,
      "size_frac": 0.50,
      "signal": "buy_signal"
    },
    "last_s2_buy": {
      "timestamp": "2024-01-15T12:00:00Z",
      "price": 0.0018,
      "size_frac": 0.25,
      "signal": "buy_flag"
    },
    "last_s3_buy": {
      "timestamp": "2024-01-15T14:00:00Z",
      "price": 0.0020,
      "size_frac": 0.15,
      "signal": "buy_flag"
    },
    "last_trim": {
      "timestamp": "2024-01-15T16:00:00Z",
      "price": 0.0032,
      "size_frac": 0.10,
      "signal": "trim_flag",
      "sr_level_price": 0.0030  // S/R level price at time of trim
    },
    "last_reclaim_buy": {
      "timestamp": "2024-01-15T18:00:00Z",
      "price": 0.0025,
      "size_frac": 0.15,
      "reclaimed_at": "2024-01-15T18:00:00Z"  // When EMA333 was reclaimed
    },
    "executions": [
      // Full history of all executions (optional, for audit)
      {
        "type": "buy",
        "timestamp": "2024-01-15T10:00:00Z",
        "price": 0.0015,
        "tokens": 1000,
        "usd": 1.5,
        "signal": "buy_signal",
        "state": "S1"
      },
      {
        "type": "trim",
        "timestamp": "2024-01-15T16:00:00Z",
        "price": 0.0032,
        "tokens": 100,
        "usd": 0.32,
        "signal": "trim_flag",
        "state": "S3"
      }
    ]
  }
}
```

**Update Logic**:
- After each execution, PM updates `pm_execution_history`:
  - Sets `last_{state}_buy` or `last_trim` with timestamp, price, size_frac, signal
  - Updates `prev_state` to current state (for next tick's state transition detection)
  - Optionally appends to `executions` array (for full audit trail)
  - For trims: Stores `sr_level_price` (closest S/R level at time of trim)

**Usage in `plan_actions_v4()`**:
- Read `pm_execution_history` to check if signal already executed
- S1: Check `last_s1_buy` - if exists, don't buy again (one-time only)
- S2/S3: Check `last_{state}_buy` - reset if trim happened OR state transitioned
- Trims: Check `last_trim` - allow if cooldown expired (3 hours) OR S/R level changed

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

#### 3. Fix Backfill to Support All 4 Timeframes
**File**: `src/intelligence/trader_lowcap/trader_service.py`
- **Note**: Positions are already created by Decision Maker (4 positions per token: 1m, 15m, 1h, 4h)
- Trigger backfill for all 4 timeframes (async, non-blocking) for the newly created positions
- Backfill logic per timeframe:
  - **1m**: Backfill 1m OHLC data (directly from API)
  - **15m**: Backfill 15m OHLC data (directly from API - GeckoTerminal 15m endpoint)
  - **1h**: Backfill 1h OHLC data (directly from API - GeckoTerminal 1h endpoint)
  - **4h**: Backfill 4h OHLC data (directly from API - GeckoTerminal 4h endpoint)
- **Note**: Backfill fetches correct timeframe directly from API (no rollup). Rollup is only for ongoing data collection.
- Update `bars_count` per position as data arrives

#### 4. Make TA Tracker Multi-Timeframe
**File**: `src/intelligence/lowcap_portfolio_manager/jobs/ta_tracker.py`
- Add `timeframe` parameter
- Store with dynamic suffix
- Run multiple times for different timeframes

#### 5. Update PM Frequency (Timeframe-Specific)
**File**: `src/run_social_trading.py`
- Change PM Core Tick to timeframe-specific scheduling:
  - **1m timeframe**: Every 1 minute
  - **15m timeframe**: Every 15 minutes
  - **1h timeframe**: Every 1 hour
  - **4h timeframe**: Every 4 hours
- **Implementation**: Run PM separately per timeframe, grouped by timeframe (processes all positions of that timeframe)
- **Reason**: PM must run at same rate as timeframe being checked, otherwise misses signals

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

1. **Database Schema Updates** (CRITICAL - do first):
   - **Update `lowcap_positions_v4_schema.sql`**:
     - Add `entry_context JSONB` column (for learning system - stores lever values at entry)
     - Add `completed_trades JSONB DEFAULT '[]'::jsonb` column (for learning system - stores closed trade summaries)
     - Verify `features` JSONB exists (for `pm_execution_history` tracking)
   - **Create `learning_configs_schema.sql`** (new table for module-specific configs)
   - **Create `learning_coefficients_schema.sql`** (new table for learned performance coefficients)
   - **Update `curators_schema.sql`**: Add `chain_counts JSONB DEFAULT '{}'::jsonb` column
   - **Verify `ad_strands` schema** supports `kind='position_closed'` (already supported via `kind` TEXT column)
   - **For detailed schema specifications**, see [`LEARNING_SYSTEM_V4.md`](./LEARNING_SYSTEM_V4.md) section "Database Schema Changes"

2. **Verify 1m OHLC Conversion** (CRITICAL - before implementation):
   - Test 1m price data → 1m OHLC conversion works correctly
   - Verify rollup produces valid OHLC bars engine can process
   - Test edge cases (gaps, missing data, volume calculation)
   - Document any limitations or fixes needed

3. **Update Decision Maker** to create 4 positions per token:
   - Decision Maker calculates `allocation_pct` (e.g., 4%)
   - **Gets current balance** (from wallet) to calculate `total_allocation_usd = (allocation_pct * balance) / 100.0`
   - Creates 4 positions in `lowcap_positions` table (one per timeframe: 1m, 15m, 1h, 4h)
   - For each position: `alloc_cap_usd = total_allocation_usd * timeframe_percentage`
     - 1m: `total_allocation_usd * 0.05`
     - 15m: `total_allocation_usd * 0.125`
     - 1h: `total_allocation_usd * 0.70`
     - 4h: `total_allocation_usd * 0.125`
   - Set `status` based on `bars_count` (dormant if < 350, watchlist if >= 350)
   - Store allocation splits in `alloc_policy` JSONB
   - **Note**: Most tokens will start with all positions at `watchlist` (if they have enough data)
   - **Note**: Positions created atomically with decision (no gap between decision and positions)

4. **Update Backfill** to support all 4 timeframes per token:
   - **CRITICAL**: Each new token gets 4 positions (one per timeframe: 1m, 15m, 1h, 4h)
   - Trigger backfill for all 4 timeframes (async, non-blocking)
   - Backfill logic (directly from GeckoTerminal API - no rollup):
     - **1m timeframe**: Backfill 1m OHLC data (from GeckoTerminal 1m endpoint)
     - **15m timeframe**: Backfill 15m OHLC data (from GeckoTerminal 15m endpoint)
     - **1h timeframe**: Backfill 1h OHLC data (from GeckoTerminal 1h endpoint)
     - **4h timeframe**: Backfill 4h OHLC data (from GeckoTerminal 4h endpoint)
   - **Note**: Backfill fetches correct timeframe directly from API (no rollup). Rollup is only for ongoing data collection (1m price points → 1m OHLC → rollup to 15m/1h/4h).
   - **Backfill updates `bars_count` immediately** after inserting data (one-time update per backfill)
   - **Auto-flip `dormant → watchlist`** when `bars_count >= 350` for that timeframe (handled by backfill)
   - **Note**: Most tokens will have enough data for at least some timeframes → those positions start at `watchlist` immediately
   - **Ongoing updates**: The periodic `bars_count` update job (hourly) handles updates from ongoing OHLC conversion/rollup jobs (see "Bars Count Update" section above)

5. **Update OHLC Conversion & Rollup** to handle all timeframes:
   - **1m OHLC Conversion** (CRITICAL - different from rollup):
     - Convert 1m price points → 1m OHLC bars
     - Open = previous candle's close (or first price if no previous)
     - Close = current candle's price
     - High = max(open, close)
     - Low = min(open, close)
     - Volume = sum of volumes for 1-minute window
   - **OHLC Rollup** (standard aggregation):
     - Roll up 1m OHLC → 15m OHLC (aggregate 15 bars)
     - Roll up 1m OHLC → 1h OHLC (aggregate 60 bars)
     - Roll up 1m OHLC → 4h OHLC (aggregate 240 bars)
   - **Storage**: All timeframes (1m, 15m, 1h, 4h) in `lowcap_price_data_ohlc` with `timeframe` column
   - **Usage**: PM and Uptrend Engine read from `lowcap_price_data_ohlc` (NOT `lowcap_price_data_1m`)

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
10. **Update PM frequency** (timeframe-specific):
    - **1m timeframe**: Every 1 minute
    - **15m timeframe**: Every 15 minutes
    - **1h timeframe**: Every 1 hour
    - **4h timeframe**: Every 4 hours
    - **Implementation**: Run PM separately per timeframe, grouped by timeframe
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
9. ✅ **PM frequency** - Timeframe-specific (1m=1min, 15m=15min, 1h=1hr, 4h=4hr) - runs at same rate as timeframe being checked
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

4. Backfill (async, non-blocking) → For all 4 timeframes per token
   └─> **CRITICAL**: Each new token gets 4 positions (one per timeframe: 1m, 15m, 1h, 4h)
   └─> Triggers backfill for all 4 timeframes (1m, 15m, 1h, 4h)
   └─> Backfill per timeframe:
       ├─> 1m: Backfill 1m OHLC data (directly from API - GeckoTerminal 1m endpoint)
       ├─> 15m: Backfill 15m OHLC data (directly from API - GeckoTerminal 15m endpoint)
       ├─> 1h: Backfill 1h OHLC data (directly from API - GeckoTerminal 1h endpoint)
       └─> 4h: Backfill 4h OHLC data (directly from API - GeckoTerminal 4h endpoint)
   └─> **Note**: Backfill fetches correct timeframe directly from API (no rollup). Rollup is only for ongoing data collection.
   └─> Stores in lowcap_price_data_ohlc with correct timeframe
   └─> Updates bars_count per position as data arrives

5. Data Pipeline (continuous)
   └─> Price Tracking → Collects 1m price points every 1 minute → stores in `lowcap_price_data_1m`
   └─> OHLC Conversion → Converts 1m price points → 1m OHLC bars (Open=previous close, Close=current price, High/Low=max/min)
   └─> OHLC Rollup → Rolls up 1m OHLC → 15m OHLC → 1h OHLC → 4h OHLC (all stored in `lowcap_price_data_ohlc` with `timeframe` column)
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

8. PM Core Tick (timeframe-specific) → Processes only watchlist + active positions of that timeframe
   └─> **1m**: Every 1 minute
   └─> **15m**: Every 15 minutes
   └─> **1h**: Every 1 hour
   └─> **4h**: Every 4 hours
   └─> Processes all positions of that timeframe (watchlist + active)
   └─> Reads engine flags from features.uptrend_engine_v4
   └─> Reads execution history from features.pm_execution_history
   └─> Computes A/E scores
   └─> Calculates profit/allocation multipliers
   └─> plan_actions_v4() makes decisions (checks execution history, applies multipliers)
   └─> Calls executor.execute() → Executor returns results (no database writes)
   └─> PM updates position table (total_quantity, execution_history, etc.)
   └─> For watchlist positions: First buy updates status → 'active'
   └─> For active positions: Adds/trims/exits
   └─> If position closed: Computes R/R, writes completed_trades, emits position_closed strand
   └─> Writes strand after execution (async, with results)

9. Executor → Executes trades
   └─> Tags all orders with position_id (ensures emergency exits only touch that TF's holdings)
   └─> Returns results to PM (tx_hash, price, tokens, slippage)
   └─> Does NOT write to database (PM does all database writes)
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

### 5. Emergency Exit (No "Demote")

**Current State**:
- **Old system**: Had "demote" which sold 80%, kept moon bag
- **v4**: Simplified - only "trim" (partial) and "emergency_exit" (full exit)

**Decision**: 
- **Remove "demote"** - Use "emergency_exit" for full exits
- **Keep "trim"** for partial exits
- **Emergency exit = full exit** (confirmed)

---

### 6. Strands Only for Actions (No Hold Strands)

**Decision**: Only emit strands when actions are taken (add, trim, emergency_exit). No strands for holds.

**Rationale**:
- Reduces noise (holds are the default state)
- Focuses learning on actual decisions and outcomes
- Strands are for actions, not inaction

**Content for action strands**:
- `kind`: "pm_action" (or "position_closed" for final exits)
- `position_id`: Links to position (can look up curator via position)
- `timeframe`: Position's timeframe
- `chain`: Position's chain
- `token`: Contract address
- `decision_type`: "add", "trim", "emergency_exit"
- `reasons.flag`: String identifying which flag triggered ("buy_signal", "buy_flag", "trim_flag", "emergency_exit", "first_dip_buy_flag", "reclaimed_ema333")
- `execution_result`: Results from executor (tx_hash, price, tokens, slippage)

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
           ├─> PM updates position table (total_quantity, execution_history, etc.)
           ├─> If position closed: Computes R/R, writes completed_trades, emits position_closed strand
           └─> Write strand after execution [async, with results]

4. Executor (per-chain)
   └─> Executes trade (via chain-specific executor)
   └─> Returns results to PM (tx_hash, actual price, slippage, tokens_bought/sold)
   └─> Does NOT write to database (PM does all database writes)

5. Strands (for learning)
   └─> Buy strand: decision + execution result (kind='pm_action', flag='buy_signal'|'buy_flag'|'first_dip_buy_flag'|'reclaimed_ema333')
   └─> Trim strand: decision + execution result (kind='pm_action', flag='trim_flag')
   └─> Emergency exit strand: decision + execution result (kind='pm_action', flag='emergency_exit')
   └─> Position closed strand: completed_trade data (kind='position_closed', includes R/R, entry_context, all learning data)
   └─> No hold strands (only actions emit strands)
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
14. ✅ **Execution history tracking** - `features.pm_execution_history` prevents duplicate signal executions
15. ✅ **Signal reset logic** - S1 one-time, S2/S3 reset on trim or state transition, trims reset on cooldown (3hr) or S/R level change
16. ✅ **Profit/allocation multipliers** - Applied in `plan_actions_v4()`, recalculated after each execution
17. ✅ **Executor pattern** - Executor only executes and returns results; PM does all database writes (applies to all trades, not just final exits)
18. ✅ **No hold strands** - Only actions emit strands (reduces noise, focuses on decisions)
19. ✅ **Database reorganization** - Archive old schemas, drop tables, recreate fresh minimal schemas
20. ✅ **1m OHLC verification needed** - Must verify 1m price data → 1m OHLC conversion before Phase 0

