# Complete Token Flow Trace - From Social Signal to Execution

This document traces the **actual code flow** of a token from social signal ingestion through to execution, identifying what's missing, what's extra, and how it all connects.

---

## 🎯 **Step-by-Step Flow**

### **Step 1: Social Signal Ingestion**

**File**: `src/intelligence/social_ingest/social_ingest_basic.py`

**What happens**:
1. Social monitor detects a message from a curator
2. LLM extracts token information (ticker, contract, chain, etc.)
3. Token is verified with DexScreener API (volume, liquidity, market cap checks)
4. Curator intent is analyzed (buy signal vs. other)
5. **Creates `social_lowcap` strand** in database with:
   - `kind: "social_lowcap"`
   - `target_agent: "decision_maker_lowcap"`
   - `tags: ["curated", "social_signal", "dm_candidate", "verified"]`
   - Signal pack with token, venue, curator info
6. **Calls `learning_system.process_strand_event(created_strand)`** (line 1158)

**Status**: ✅ **Working** - This is wired up in `run_social_trading.py`

---

### **Step 2: Learning System Processing**

**File**: `src/intelligence/universal_learning/universal_learning_system.py`

**What happens**:
1. `process_strand_event()` is called with the `social_lowcap` strand
2. Calculates strand scores (persistence, novelty, surprise)
3. Updates strand in database with scores
4. Checks `_should_trigger_decision_maker()`:
   - Returns `True` if `kind == 'social_lowcap'` AND `'dm_candidate' in tags` AND `target_agent == 'decision_maker_lowcap'`
5. If should trigger, calls `_trigger_decision_maker(strand)`
6. `_trigger_decision_maker()`:
   - Gets reference to `self.decision_maker` (passed in during initialization)
   - Calls `await self.decision_maker.make_decision(strand)`

**Status**: ✅ **Working** - Learning system is initialized and decision_maker is passed in

---

### **Step 3: Decision Maker Evaluation**

**File**: `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py`

**What happens**:
1. `make_decision()` evaluates the social signal with 5 criteria:
   - ✅ Supported chain (solana, ethereum, base, bsc)
   - ✅ Not already holding token
   - ✅ Curator score >= min (0.6)
   - ✅ Intent analysis indicates buy signal
   - ✅ Portfolio capacity available
2. If all pass, calculates allocation percentage (2-6%, with intent/market cap multipliers)
3. **Creates `decision_lowcap` strand** with:
   - `kind: "decision_lowcap"`
   - `content.action: "approve"` (or "reject")
   - `tags: ["decision", "social_lowcap", "approved"]` (if approved)
   - Allocation percentage and USD amount
4. Returns decision strand (or None if rejected)

**Status**: ✅ **Working** - Decision maker creates decision strands

---

### **Step 4: Learning System → Trader Trigger**

**File**: `src/intelligence/universal_learning/universal_learning_system.py`

**What happens**:
1. After Decision Maker returns, learning system checks `_should_trigger_trader()`:
   - Returns `True` if `kind == 'decision_lowcap'` AND `action == 'approve'` AND `'approved' in tags`
2. If should trigger, calls `_trigger_trader(strand)`:
   - Uses shared `self.trader` instance (TraderLowcapSimpleV2)
   - Calls `await self.trader.service.execute_decision(decision_strand)`

**Status**: ✅ **Working** - Trader is triggered after decision approval

---

### **Step 5: Trader Creates Position**

**File**: `src/intelligence/trader_lowcap/trader_service.py` (method: `execute_decision`)

**What happens**:
1. Validates decision (action == 'approve')
2. Checks idempotency (position doesn't already exist)
3. Gets chain-specific setup (executor, price oracle, balance)
4. Validates balance > 0
5. **Creates position in `lowcap_positions` table**:
   - `status: 'active'`
   - `total_allocation_pct`: from decision
   - `total_quantity: 0.0` (no tokens bought yet)
   - `features`: `{'pair_created_at': '', 'market_cap': 0.0, 'features_initialized_at': NOW()}`
6. **Triggers async backfill** (line 1123-1135):
   - Non-blocking: `asyncio.create_task(_run_onboarding_backfill())`
   - Calls `backfill_token_15m(contract, chain, 20160)` (14 days of 15m bars)
   - **⚠️ ISSUE**: Should be `backfill_token_1h` OR dynamic based on token age
   - **This is async, so position creation doesn't wait**
7. Creates entry plan (3 entries) and stores in position entries table
8. **❌ REMOVE: Executes first buy** (line 1165-1189):
   - **OLD SYSTEM BEHAVIOR** - This should be removed!
   - Calls chain executor: `executor.execute_buy(contract, allocated_native)`
   - Updates position with tokens bought
   - **Fix**: Let PM handle all entries via signals

**Status**: ⚠️ **PARTIAL** - Position created, backfill triggered, but first buy should NOT execute immediately

**⚠️ CRITICAL ISSUES**: 
1. Backfill is **15m timeframe** (hardcoded `backfill_token_15m`), should be 1h OR dynamic
2. **First buy executes immediately** - This is OLD system behavior, should be removed!

---

### **Step 6: Scheduled Jobs (Parallel, Independent)**

These run on their own schedules, not triggered by position creation:

#### **6A: Backfill (Triggered + Scheduled)**

**Triggered**: When position is created (currently 15m, 14 days) - **async, non-blocking**
- **⚠️ ISSUE**: Should be 1h OR dynamic based on token age
- **Fix**: Change to `backfill_token_1h` OR make dynamic

**Scheduled**: Hourly gap scan (`geckoterminal_gap_scan_1h.py`) - checks for missing 1h bars

**Status**: ⚠️ **NEEDS FIX** - Should be 1h (or dynamic), not hardcoded 15m

---

#### **6B: TA Tracker**

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/ta_tracker.py`

**Schedule**: Every 5 minutes (via `tracker.py` in `run_social_trading.py`)

**What happens**:
1. Gets all active positions from `lowcap_positions` table
2. For each position, reads OHLC data from `lowcap_price_data_ohlc`:
   - **Hardcoded**: `timeframe='1h'` (line 179)
   - Requires at least 72 bars (3 days)
3. Computes TA indicators:
   - EMAs (20, 30, 60, 144, 250, 333)
   - EMA slopes (10-bar regression)
   - ATR, RSI, ADX
   - Volume z-score
4. **Writes to `features.ta`** in position record

**Status**: ⚠️ **PARTIAL** - Only supports 1h timeframe, needs multi-timeframe support

---

#### **6C: Geometry Builder**

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/geometry_build_daily.py`

**Schedule**: Daily at :10 UTC (via `run_social_trading.py`)

**What happens**:
1. Gets all active positions
2. Reads OHLC data (1h only)
3. Builds S/R levels (diagonals, horizontal support/resistance)
4. **Writes to `features.geometry`** in position record

**Status**: ⚠️ **PARTIAL** - Only supports 1h timeframe, needs multi-timeframe support

---

#### **6D: Uptrend Engine v4**

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/uptrend_engine_v4.py`

**Schedule**: ❌ **NOT SCHEDULED** - Missing from `run_social_trading.py`!

**What should happen**:
1. Gets all active positions
2. Reads `features.ta` and `features.geometry`
3. Detects state (S0, S1, S2, S3)
4. Computes scores (TS, DX, OX, EDX)
5. Emits signals (buy_signal, buy_flag, first_dip_buy_flag, trim_flag, emergency_exit)
6. **Writes to `features.uptrend_engine_v4`** in position record

**Status**: ❌ **MISSING** - Engine exists but is not scheduled to run!

---

#### **6E: Price Tracking (5m OHLCV)**

**File**: `src/trading/scheduled_price_collector.py`

**Schedule**: Every 1 minute (via `start_position_management()` in `run_social_trading.py`)

**What happens**:
1. Collects 5m OHLCV data for active positions
2. Stores in `lowcap_price_data_1m` (or similar table)
3. Used for real-time price monitoring

**Status**: ✅ **Working** - Continuous price collection

---

### **Step 7: PM Core Tick**

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

**Schedule**: Hourly at :06 UTC (via `run_social_trading.py`) ⚠️ **TOO INFREQUENT** - Should be every 5 minutes for lower timeframes

**What happens**:
1. Gets all active positions
2. Reads portfolio phase (meso, macro) and cut pressure
3. For each position:
   - Reads `features` (expects `uptrend_engine_v4` to be there)
   - Calls `compute_levers()` to compute A/E scores
   - Calls `plan_actions()` to generate decisions
   - **Writes to `ad_strands` table** with decision
   - **Emits `decision_approved` event** (if not "hold")

**Status**: ⚠️ **PARTIAL** - Runs but `plan_actions()` uses OLD geometry-based logic, not Uptrend Engine v4 signals

**⚠️ CRITICAL ISSUE**: 
- Expects `features.uptrend_engine_v4` but Uptrend Engine is not scheduled!
- `plan_actions()` doesn't use Uptrend Engine signals yet

---

### **Step 8: PM Executor**

**File**: `src/intelligence/lowcap_portfolio_manager/pm/executor.py`

**Schedule**: Event-driven (subscribes to `decision_approved` events)

**What happens**:
1. Subscribes to `decision_approved` events (via `register_pm_executor()`)
2. When event received:
   - Checks idempotency (prevents duplicate execution)
   - Gets position from database
   - Gets latest price from `lowcap_price_data_1m`
   - Executes based on `decision_type`:
     - `"add"` or `"trend_add"`: Calls `executor.execute_buy(contract, notional_usd)`
     - `"trim"` or `"trail"`: Calls `executor.execute_sell(contract, tokens_to_sell)`
     - `"demote"`: Calls `executor.execute_sell()` with larger size

**Status**: ✅ **Working** - Executor is registered in `run_social_trading.py` (line 233-238)

**⚠️ NOTE**: Executor only runs if `ACTIONS_ENABLED=1` environment variable is set

---

## 🔍 **What's Missing**

### **1. Uptrend Engine v4 Not Scheduled** ❌ **CRITICAL**
- Engine exists but is not scheduled in `run_social_trading.py`
- PM Core Tick expects `features.uptrend_engine_v4` but it won't exist
- **Fix**: Add `schedule_5min(4, uptrend_engine_v4_main)` to `run_social_trading.py`

### **2. Multi-Timeframe Support Missing** ⚠️ **IMPORTANT**
- Backfill: Only 15m on position creation (hardcoded)
- TA Tracker: Only 1h (hardcoded `timeframe='1h'`)
- Geometry: Only 1h (assumed)
- Uptrend Engine: Only 1h (assumed)
- **Fix**: Need to add timeframe parameter to all modules

### **3. PM Integration Not Complete** ⚠️ **IMPORTANT**
- `plan_actions()` uses OLD geometry-based logic
- Doesn't use Uptrend Engine v4 signals (buy_signal, buy_flag, etc.)
- **Fix**: Need to create `plan_actions_v4()` that uses Uptrend Engine signals

### **4. PM Frequency May Be Too Low** ⚠️ **CONSIDER**
- PM runs hourly, but if we're trading on 5m/15m timeframes, we might miss signals
- **Fix**: Consider running PM every 5 minutes (or at least more frequently)

---

## 📊 **What's Extra / Not Needed**

### **1. Old Uptrend Engines** (v1, v2, v3)
- Still in codebase but not used
- Can be archived/removed

### **2. Old Social Ingest Module**
- `social_ingest_module.py` exists but not used
- `social_ingest_basic.py` is the active one

### **3. Trader V1 Code**
- Old trader code may still exist but V2 is used

### **4. Multiple Decision Maker Versions**
- `decision_maker_lowcap.py` vs `decision_maker_lowcap_simple.py`
- Need to verify which is actually used

---

## 🔄 **Complete Flow Diagram**

```
1. Social Ingest
   └─> Creates social_lowcap strand
       └─> Calls learning_system.process_strand_event()

2. Learning System
   └─> Scores strand
       └─> Triggers Decision Maker (if dm_candidate tag)

3. Decision Maker
   └─> Evaluates criteria (5 checks)
       └─> Creates decision_lowcap strand (approve/reject)
           └─> Returns to Learning System

4. Learning System
   └─> Triggers Trader (if approved)

5. Trader Service
   └─> Creates position in lowcap_positions table
       ├─> Triggers async backfill (15m only, 14 days) ⚠️
       └─> Executes first buy immediately

6. Scheduled Jobs (Parallel, Independent)
   ├─> TA Tracker (every 5 min) - writes features.ta (1h only) ⚠️
   ├─> Geometry Builder (daily) - writes features.geometry (1h only) ⚠️
   ├─> Uptrend Engine v4 (NOT SCHEDULED!) ❌
   ├─> Price Tracking (every 1 min) - writes to price tables ✅
   └─> Backfill Gap Scan (hourly) - fills missing 1h bars ⚠️

7. PM Core Tick (hourly)
   └─> Reads features (expects uptrend_engine_v4) ❌
       └─> Computes A/E scores
           └─> Calls plan_actions() (OLD logic, not v4) ⚠️
               └─> Writes to ad_strands table
                   └─> Emits decision_approved event

8. PM Executor (event-driven)
   └─> Subscribes to decision_approved events
       └─> Executes trades (add/trim/demote)
```

---

## ✅ **What's Working**

1. ✅ Social Ingest → Learning System → Decision Maker → Trader flow
2. ✅ Position creation with backfill trigger
3. ✅ First buy execution
4. ✅ TA Tracker (1h only)
5. ✅ Geometry Builder (1h only)
6. ✅ Price Tracking (5m OHLCV)
7. ✅ PM Core Tick (runs hourly)
8. ✅ PM Executor (event-driven, registered)

---

## ❌ **What's Broken / Missing**

1. ❌ **Uptrend Engine v4 not scheduled** - PM expects it but it never runs
2. ❌ **Multi-timeframe support** - Everything hardcoded to 1h (or 15m for backfill)
3. ❌ **PM uses old logic** - `plan_actions()` doesn't use Uptrend Engine signals
4. ⚠️ **Backfill only 15m** - Should be dynamic based on token age
5. ⚠️ **PM frequency** - Hourly may be too slow for lower timeframes

---

## 🎯 **Priority Fixes**

### **P0 (Critical - Must Fix)**
1. **Schedule Uptrend Engine v4** in `run_social_trading.py`
2. **Update `plan_actions()` to use Uptrend Engine v4 signals** (or create v4 version)

### **P1 (Important - Should Fix)**
3. **Add multi-timeframe support** to backfill, TA tracker, geometry, engine
4. **Fix backfill** to use dynamic timeframe based on token age
5. **Consider PM frequency** - may need to run more often

### **P2 (Nice to Have)**
6. Clean up old code (v1/v2/v3 engines, old social ingest)
7. Document event flow more clearly

