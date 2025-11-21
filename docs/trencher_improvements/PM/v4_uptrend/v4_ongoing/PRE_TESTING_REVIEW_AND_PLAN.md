# Pre-Testing Review & Testing Plan

**Status**: Planning Phase  
**Date**: 2025-11-07  
**Updated**: 2025-11-15 (aligned with Flow Testing Ethos)

---

## ⚠️ CRITICAL: Read This First

**Before writing any tests, read `FLOW_TESTING_ETHOS.md`.**

**Core Principle**: Turn the system on. Inject a packet. Query the database. That's it.

**The system runs itself** (scheduled jobs, event processing). **The test just observes** (inject packet, query database).

**DO NOT**:
- Orchestrate the system (don't call functions directly)
- Mock everything (only mock Uptrend Engine signals)
- Build test infrastructure (just query the database)
- Follow traditional unit testing patterns (this is a data pipeline)

**DO**:
- Turn the system on (scheduled jobs running)
- Inject one packet at ingress
- Query the database at each step
- Follow the packet through using IDs
- Know exactly where it dies if it dies

See `FLOW_TESTING_ETHOS.md` for complete details.

---

## Part 1: Comprehensive Code & Document Review Checklist

**Purpose**: Verify implementation matches design before testing begins

**How to Use This Section**:
1. **Go through each subsection in order** (1.1 → 1.8)
2. **For each checkbox item**:
   - Read the item description
   - Find the relevant code/file in the codebase
   - Verify it matches the description
   - Check the box if it matches, or note the gap
3. **Document gaps** in a separate "Gaps Found" section (see below)
4. **Fix gaps** before moving to Part 2 (Testing Plan)

**Tools Needed**:
- Code editor/IDE (to read source files)
- Database client (to verify schemas)
- Git (to check file locations)
- grep/codebase search (to find implementations)

**Output**: 
- Completed checklist (all items verified)
- List of gaps found (if any)
- Fixes applied (if any)

---

### 1.1 Database Schema Verification

#### ✅ Schema Files Exist
- [ ] `lowcap_positions_v4_schema.sql` - Has `entry_context` and `completed_trades` JSONB columns
- [ ] `learning_configs_schema.sql` - Exists and properly structured
- [ ] `learning_coefficients_schema.sql` - Exists and properly structured
- [ ] `curators_schema.sql` - Has `chain_counts` JSONB column
- [ ] `ad_strands_schema.sql` - Supports `kind='position_closed'` (TEXT column)
- [ ] `wallet_balances_schema.sql` - Has `usdc_balance` column
- [ ] `pm_thresholds_schema.sql` - Exists for tunable thresholds

#### ✅ Schema Alignment
- [ ] `entry_context` structure matches what Decision Maker populates
- [ ] `completed_trades` structure matches what PM writes
- [ ] `learning_coefficients` table structure matches CoefficientUpdater writes
- [ ] `learning_configs` structure matches global R/R baseline storage
- [ ] All indexes exist for performance-critical queries

### 1.2 Learning System Implementation

#### ✅ Phase 1: Basic Strand Processing
- [ ] `UniversalLearningSystem.process_strand_event()` handles `kind='position_closed'`
- [ ] `_process_position_closed_strand()` extracts `entry_context` and `completed_trades`
- [ ] `_update_coefficients_from_closed_trade()` calls coefficient updater
- [ ] Global R/R baseline updates correctly

#### ✅ Phase 2: EWMA & Interaction Patterns
- [ ] `CoefficientUpdater` class exists and is initialized
- [ ] `BucketVocabulary` class exists and is initialized
- [ ] `calculate_decay_weight()` implements exponential decay correctly
- [ ] `update_coefficient_ewma()` uses τ₁=14d and τ₂=90d correctly
- [ ] `generate_interaction_key()` creates consistent hashed keys
- [ ] `update_interaction_pattern()` updates interaction coefficients
- [ ] `apply_importance_bleed()` downweights overlapping single-factor weights
- [ ] Bucket normalization works for all bucket types (mcap, vol, age, ratio)

#### ✅ Phase 3: Decision Maker Integration
- [ ] `CoefficientReader` class exists and is initialized in Decision Maker
- [ ] `_build_entry_context_for_learning()` calculates all buckets correctly
- [ ] `_calculate_allocation_with_curator()` uses learned coefficients
- [ ] `calculate_allocation_multiplier()` applies all weights correctly
- [ ] `apply_importance_bleed()` is called when interaction patterns exist
- [ ] `get_timeframe_weights()` reads timeframe coefficients correctly
- [ ] `normalize_timeframe_weights()` normalizes to sum to 1.0
- [ ] Fallback to static multipliers works when no learned data exists

### 1.3 Decision Maker Implementation

#### ✅ Position Creation
- [ ] Creates 4 positions per token (1m, 15m, 1h, 4h)
- [ ] Calculates `total_allocation_usd` from current balance
- [ ] Splits allocation using learned timeframe weights (or defaults)
- [ ] Sets `status` based on `bars_count` (dormant vs watchlist)
- [ ] Populates `entry_context` JSONB with all lever values:
  - [ ] `curator` (curator ID)
  - [ ] `chain` (token chain)
  - [ ] `mcap_bucket` (from BucketVocabulary)
  - [ ] `vol_bucket` (from BucketVocabulary)
  - [ ] `age_bucket` (from BucketVocabulary)
  - [ ] `mcap_vol_ratio_bucket` (from BucketVocabulary)
  - [ ] `intent` (from intent_analysis)
  - [ ] `mapping_confidence` (from token_data)
  - [ ] Raw values: `mcap_at_entry`, `vol_at_entry`, `age_at_entry`

#### ✅ Allocation Calculation
- [ ] Uses `CoefficientReader.calculate_allocation_multiplier()`
- [ ] Applies learned coefficients to base allocation
- [ ] Falls back to static multipliers if learning system unavailable
- [ ] Clamps allocation to reasonable bounds (0.1% - 20%)
- [ ] Logs learned multiplier for debugging

### 1.4 Portfolio Manager Implementation

#### ✅ Position Closure Detection
- [ ] `_check_position_closure()` detects full exits correctly
- [ ] Checks `size_frac >= 1.0` OR `decision_type == "emergency_exit"`
- [ ] Verifies `total_quantity == 0` after execution
- [ ] Only processes successful executions

#### ✅ R/R Calculation
- [ ] `_calculate_rr_metrics()` queries `lowcap_price_data_ohlc` correctly
- [ ] Filters by position's `timeframe` (not hardcoded)
- [ ] Calculates `min_price` and `max_price` from OHLC data
- [ ] Calculates `return`, `max_drawdown`, `max_gain`, `rr` correctly
- [ ] Handles edge cases (no data, division by zero, infinite values)

#### ✅ Completed Trades Storage
- [ ] Writes `completed_trades` JSONB array correctly
- [ ] Includes all required fields:
  - [ ] `entry_context` (from position)
  - [ ] `entry_price` (avg_entry_price)
  - [ ] `exit_price` (avg_exit_price)
  - [ ] `entry_timestamp` (first_entry_timestamp)
  - [ ] `exit_timestamp` (closed_at)
  - [ ] `rr`, `return`, `max_drawdown`, `max_gain`
  - [ ] `decision_type` (trim/emergency_exit)
- [ ] Updates position `status='watchlist'` and `closed_at`

#### ✅ Position Closed Strand Emission
- [ ] Emits strand with `kind='position_closed'`
- [ ] Includes `position_id`, `token`, `chain`, `timeframe`
- [ ] Includes `entry_context` (for learning)
- [ ] Includes `completed_trades` array (for learning)
- [ ] Strand is inserted into `ad_strands` table
- [ ] **CRITICAL**: Learning system processes strand (via database trigger + queue OR direct call)
  - [ ] **Current Flow**: PM inserts strand → Database trigger `strand_learning_trigger` fires → Inserts into `learning_queue`
  - [ ] **Gap Identified**: `UniversalLearningSystem` has `process_strand_event()` but no scheduled job processes `learning_queue`
  - [ ] **Solution Options**:
    - **Option A**: Add scheduled job in `run_social_trading.py` to process `learning_queue` and call `process_strand_event()` for each strand
    - **Option B**: PM calls `learning_system.process_strand_event()` directly after inserting strand (like Social Ingest does)
  - [ ] **Recommendation**: Option B (direct call) is simpler and more reliable - matches existing pattern

#### ✅ Execution History Tracking
- [ ] `_update_execution_history()` updates `pm_execution_history` correctly
- [ ] Tracks `last_s1_buy`, `last_s2_buy`, `last_s3_buy`, `last_trim`, `last_reclaim_buy`
- [ ] Stores `timestamp`, `price`, `size_frac`, `signal` for each execution
- [ ] Updates `prev_state` for state transition detection

### 1.5 Data Flow Verification

#### ✅ Complete Learning Loop
1. [ ] **Decision Maker** creates positions with `entry_context` populated
2. [ ] **PM** executes trades, tracks execution history
3. [ ] **PM** detects position closure, computes R/R, writes `completed_trades`
4. [ ] **PM** emits `position_closed` strand
5. [ ] **CRITICAL GAP**: **Learning System** processes strand via `process_strand_event()`
   - [ ] **Current State**: 
     - PM inserts strand → Database trigger fires → Inserts into `learning_queue`
     - BUT: No scheduled job processes `learning_queue` to call `process_strand_event()`
     - **Gap**: Strands get queued but never processed
   - [ ] **Solution**: 
     - **Option A**: Add scheduled job to process `learning_queue` (every 1-5 minutes)
     - **Option B**: PM calls `learning_system.process_strand_event()` directly after inserting strand (simpler, matches Social Ingest pattern)
   - [ ] **Recommendation**: Option B - PM should call learning system directly (like Social Ingest and Decision Maker do)
6. [ ] **Learning System** updates coefficients (single-factor + interaction)
7. [ ] **Learning System** updates global R/R baseline
8. [ ] **Decision Maker** uses updated coefficients for next allocation

#### ✅ Bucket Consistency
- [ ] Decision Maker uses `BucketVocabulary` to create buckets
- [ ] Learning System uses `BucketVocabulary` to normalize buckets
- [ ] Same bucket values used in both places (no mismatch)
- [ ] Bucket vocabulary matches schema documentation

### 1.6 Document Alignment

#### ✅ COMPLETE_INTEGRATION_PLAN.md
- [ ] PM-Executor flow matches actual implementation
- [ ] Position closure detection matches actual code
- [ ] R/R calculation matches actual implementation
- [ ] Strand emission structure matches actual code
- [ ] Timeframe scheduling matches `run_social_trading.py`
- [ ] Learning system references are correct

#### ✅ LEARNING_SYSTEM_V4.md
- [ ] Database schema matches actual schema files
- [ ] Coefficient update logic matches CoefficientUpdater
- [ ] Allocation formula matches CoefficientReader
- [ ] Entry context structure matches Decision Maker output
- [ ] Completed trades structure matches PM output
- [ ] Phase 1, 2, 3 descriptions match actual implementation

### 1.7 Edge Cases & Error Handling

#### ✅ Missing Data Handling
- [ ] No `entry_context` in position → Learning system handles gracefully
- [ ] No `completed_trades` in strand → Learning system skips gracefully
- [ ] No R/R in completed_trade → Learning system skips gracefully
- [ ] No OHLC data for R/R calculation → PM handles gracefully
- [ ] No learned coefficients → Decision Maker falls back to static multipliers
- [ ] No timeframe weights → Decision Maker uses default splits

#### ✅ Data Quality
- [ ] Bucket normalization handles invalid bucket values
- [ ] EWMA handles missing timestamps gracefully
- [ ] Coefficient updates handle division by zero
- [ ] Weight clamping prevents extreme multipliers
- [ ] Importance bleed only applies when interaction is significant

### 1.8 Integration Points

#### ✅ Learning System Initialization
- [ ] `UniversalLearningSystem` initialized in `run_social_trading.py`
- [ ] `CoefficientUpdater` and `BucketVocabulary` initialized correctly
- [ ] Learning system passed to Decision Maker
- [ ] Learning system processes strands from all sources

#### ✅ Decision Maker Initialization
- [ ] `CoefficientReader` initialized in Decision Maker
- [ ] `BucketVocabulary` initialized in Decision Maker
- [ ] Decision Maker can read coefficients even if empty (fallback works)

#### ✅ PM Initialization
- [ ] PM Executor initialized correctly
- [ ] PM can detect position closure
- [ ] PM can compute R/R metrics
- [ ] PM can emit strands

---

## Part 1: Walkthrough Process

**How to Execute Part 1 Review**:

### Step 1: Set Up Review Environment
1. Open codebase in IDE
2. Open database client (connect to dev/test database)
3. Open this document side-by-side
4. Create a "Gaps Found" document to track issues

### Step 2: Review Each Subsection (1.1 → 1.8)

**For each subsection (e.g., 1.1 Database Schema Verification)**:

1. **Read the subsection title and description**
   - Understand what you're verifying

2. **For each checkbox item**:
   - **Find the relevant file/code**:
     - Schema files: `src/database/*_schema.sql`
     - Code files: Use grep/codebase search to find implementations
     - Example: For "entry_context structure", search for `entry_context` in Decision Maker code
   
   - **Verify the implementation**:
     - Read the actual code/schema
     - Compare to the checklist description
     - Check if it matches
   
   - **Check the box or note the gap**:
     - ✅ If it matches: Check the box
     - ❌ If it doesn't match: Note the gap in "Gaps Found" document
     - ⚠️ If unclear: Note the question, investigate further

3. **Document findings**:
   - Add to "Gaps Found" document:
     ```
     ## Gap: [Section] - [Item]
     **Issue**: [What's wrong]
     **Location**: [File/line]
     **Expected**: [What should be]
     **Actual**: [What is]
     **Fix**: [How to fix]
     ```

### Step 3: Example Walkthrough (1.1 Database Schema Verification)

**Example: Verifying `entry_context` structure**

1. **Find the schema file**:
   ```bash
   # Search for schema file
   find src/database -name "*positions*schema.sql"
   # Result: src/database/lowcap_positions_v4_schema.sql
   ```

2. **Read the schema**:
   ```sql
   -- Open src/database/lowcap_positions_v4_schema.sql
   -- Look for entry_context column
   entry_context JSONB,  -- Line 88
   ```

3. **Verify it exists**: ✅ Column exists

4. **Find what Decision Maker populates**:
   ```bash
   # Search for where entry_context is set
   grep -r "entry_context" src/intelligence/decision_maker*
   # Find: decision_maker_lowcap_simple.py
   ```

5. **Read the code**:
   ```python
   # Open decision_maker_lowcap_simple.py
   # Find _build_entry_context_for_learning()
   # Verify it populates all required fields
   ```

6. **Compare to checklist**:
   - Checklist says: `curator`, `chain`, `mcap_bucket`, etc.
   - Code does: [verify each field]
   - Match? ✅ or ❌

7. **Check the box or note gap**

### Step 4: After Reviewing All Subsections

1. **Review "Gaps Found" document**:
   - Prioritize critical gaps (block testing)
   - Fix critical gaps first
   - Document fixes applied

2. **Update checklist**:
   - Re-check items after fixes
   - Mark all items as complete

3. **Move to Part 2** (Testing Plan) only after:
   - All critical gaps fixed
   - All checklist items verified
   - Implementation matches design

### Step 5: Quick Reference - Where to Find Things

**Schema Files**:
- `src/database/*_schema.sql` - All database schemas

**Learning System**:
- `src/intelligence/universal_learning/universal_learning_system.py` - Main learning system
- `src/intelligence/universal_learning/coefficient_updater.py` - Coefficient updates
- `src/intelligence/universal_learning/coefficient_reader.py` - Coefficient reading
- `src/intelligence/universal_learning/bucket_vocabulary.py` - Bucket normalization

**Decision Maker**:
- `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py` - Decision Maker
- Search for: `_build_entry_context_for_learning()`, `_calculate_allocation_with_curator()`

**Portfolio Manager**:
- `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py` - PM Core Tick
- Search for: `_check_position_closure()`, `_calculate_rr_metrics()`

**Database Queries** (for verification):
```sql
-- Check if entry_context column exists
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'lowcap_positions' AND column_name = 'entry_context';

-- Check if learning_coefficients table exists
SELECT table_name 
FROM information_schema.tables 
WHERE table_name = 'learning_coefficients';

-- Check if position_closed strands exist
SELECT COUNT(*) FROM ad_strands WHERE kind = 'position_closed';
```

---

## Part 2: Comprehensive Testing Plan

### 2.1 Testing Philosophy

**⚠️ READ `FLOW_TESTING_ETHOS.md` FIRST**

**Core Principle**: Turn the system on. Inject a packet. Query the database. That's it.

**Flow Testing** (Primary approach - follow one packet through):
- **Turn the system on** (scheduled jobs, event processing running)
- Inject real(ish) data at ingress point
- **Let the system process it** (don't orchestrate, don't call functions directly)
- Follow it through the entire pipeline using existing IDs/queries
- Query the database at each step to see what happened
- Know exactly where it dies if it dies (not just "step 3 failed")
- Test the path, not just outcomes
- If we can't follow a packet through, the system is missing something

**Component Testing** (Secondary - only for isolated utilities):
- Test individual modules (BucketVocabulary, CoefficientUpdater, etc.) in isolation
- Only for pure functions/utilities that don't depend on the system
- Fast, isolated, focused
- **NOT the primary approach** - flow testing is primary

**Flow Testing Mindset**:
- **Turn the system on** (scheduled jobs running, event processing active)
- Question: "If I feed real(ish) data into ingress A, how far does it travel before it dies?"
- Pass condition: "It reaches sink Z with the expected shape/side-effects."
- **System processes it automatically** - test just queries to see what happened
- Use existing IDs (strand IDs, position IDs) to trace the path
- Use database queries to follow: signal → decision → positions → closure → learning
- If we can't trace it, add the missing link (system gap, not testing gap)
- **DO NOT orchestrate** - don't call functions directly, let the system run

**Production-Like Testing**:
- **Turn the system on** (scheduled jobs running like production)
- Test with real database (or production-like test database)
- Test with actual data flow (not mocked)
- **System runs itself** - scheduled jobs, event processing, etc.
- Test end-to-end scenarios (not isolated units)
- Test error conditions and edge cases
- Test with realistic data volumes and timing
- **Test just observes** - inject packet, query database, see what happened

**Test Data Strategy**:
- **Component Tests (Layer 1)**: Use mock data (isolated, fast, focused)
- **Flow Tests (Layer 2)**: Use real data wherever possible, mock only when necessary
  - Real tokens from `token_registry_backup.json` (tokens you've already tracked)
  - Real curators from `twitter_curators.yaml` (your actual curators)
  - Real execution with small amounts (e.g., $5-10 per trade, not testnet)
  - Real OHLC data (fetched via backfill or existing data)
  
**Uptrend Engine Testing Strategy**:
- **Test Engine Itself**: Run with real data (TA Tracker + Engine with real OHLC)
  - Verify engine computes state/flags/scores correctly from real TA data
  - Test engine state machine transitions (S0→S1→S2→S3)
  - Test engine flag logic (buy_signal, buy_flag, first_dip_buy_flag, trim_flag, emergency_exit)
  - Test engine score calculations (ox, dx, edx, ts, ts_with_boost, sr_boost)
  
- **Test PM/Executor**: Mock full engine payload (because real signals may take days/weeks)
  - Mock complete `features.uptrend_engine_v4` payload with various combinations:
    - Different states (S0, S1, S2, S3)
    - Different flags (buy_signal, buy_flag, first_dip_buy_flag, trim_flag, emergency_exit, exit_position)
    - Different scores (ox, dx, edx, ts, ts_with_boost, sr_boost)
    - Different A/E scores (a_final, e_final) - independent of engine
  - Test how PM combines engine signals + A/E scores to make decisions
  - Test PM position sizing logic (entry size from A score, trim size from E score)
  - Test PM execution history tracking (prevents duplicate executions)
  - Test PM profit/allocation multipliers (affects sizing)

**Critical Understanding**:
- Engine emits complex payload: `{state, flags, scores, diagnostics}` - NOT just boolean flags
- PM combines: Engine signals (when to act) + A/E scores (how much to act) + Position state (multipliers)
- Testing suite must understand full complexity, not treat as simple "buy_flag=True"

### 2.2 Test Environment Setup

#### ⚠️ CRITICAL: Turn the System On
1. **Start the actual system** (like production):
   - Scheduled jobs running (decision_maker, pm_core_tick, etc.)
   - Event processing active
   - System orchestrates itself
   - **Test doesn't orchestrate - system does**

#### Database Setup
1. **Create test database** (separate from production)
2. **Run all schema migrations**:
   - `lowcap_positions_v4_schema.sql`
   - `learning_configs_schema.sql`
   - `learning_coefficients_schema.sql`
   - `curators_schema.sql` (with `chain_counts`)
   - `ad_strands_schema.sql`
   - `wallet_balances_schema.sql` (with `usdc_balance`)
   - `pm_thresholds_schema.sql`
   - All price data schemas
3. **Seed test data**:
   - Real curators from `twitter_curators.yaml` (pick one, e.g., "0xdetweiler")
   - Real tokens from `token_registry_backup.json` (pick one, e.g., POLYTALE on Solana)
   - Real wallet balance (Solana USDC balance, e.g., $15-25 - enough for one position at a time since we buy then sell)
   - Real OHLC data (fetched via backfill or seed from GeckoTerminal API)
   - **Majors data** (required for SPIRAL engine):
     - Run Hyperliquid WS ingest (or seed `majors_trades_ticks` with real data)
     - Run majors rollup (1m → `majors_price_data_1m`)
     - Run majors OHLC rollup (1m → 15m → 1h → 4h → `majors_price_data_ohlc`)
     - Verify majors data exists for: BTC, SOL, ETH, BNB, HYPE
   - **For Engine Testing (Test Scenario 1)**: Run TA Tracker + Uptrend Engine with real data
   - **For PM/Executor Testing (Test Scenario 9)**: Mock full engine payload (see Test Scenario 9 below)

#### Test Configuration
- Use test database (separate from production)
- Use real API keys (GeckoTerminal, DexScreener, etc.) - needed for real data fetching
- Use real wallet addresses (with small amounts for execution)
- Enable debug logging
- Set up test monitoring/alerts

### 2.3 Test Scenarios (End-to-End Data Flow)

#### Test Scenario 1A: Uptrend Engine Testing (Real Data, No Execution) ✅ **COMPLETE**

**Status**: ✅ **PASSED** (2025-11-12)  
**Execution Time**: ~43 seconds  
**Test File**: `src/tests/flow/test_scenario_1a_engine.py::TestScenario1AEngine::test_engine_computation_with_real_data`

**Flow Testing Approach**: Test engine computation with real OHLC data

**Objective**: Verify Uptrend Engine computes state/flags/scores correctly from real TA data

**Flow Test Definition**:
- **Ingress**: Position with real OHLC data
- **Payload**: Real OHLC data (666 bars target, 333 minimum for all timeframes)
- **Expected Path**: 
  1. Position created with real token ✅
  2. OHLC data backfilled (synchronous, all 4 timeframes) ✅
  3. TA Tracker processes position (populates `features.ta`) ✅
  4. Uptrend Engine processes position (computes `features.uptrend_engine_v4`) ✅
  5. Engine payload validated ✅
- **Required Side-Effects**: 
  - `features.ta` populated with EMA, ATR, RSI, slopes, etc. ✅
  - `features.uptrend_engine_v4` populated with state, flags, scores, diagnostics ✅
- **Timeout**: 5 minutes (actual: ~43 seconds)
- **Drop Reasons Allowed**: None (completed successfully)

**Results**:
- ✅ **Backfill**: All 4 timeframes backfilled successfully
  - 1m: 666 bars (target achieved)
  - 15m: 666 bars (target achieved)
  - 1h: 665 bars (above minimum)
  - 4h: 365 bars (above minimum)
- ✅ **TA Tracker**: All 4 timeframes processed
  - Fixed: 1m minimum bars reduced from 4320 to 333 (matches backfill minimum)
  - All timeframes: EMA, ATR, RSI, slopes, separations populated
- ✅ **Uptrend Engine**: All 4 timeframes computed
  - States: S0, S4 (varies by timeframe based on EMA order)
  - Flags: buy_flag, trim_flag, emergency_exit, etc. populated
  - Scores: ts, ts_with_boost, sr_boost computed correctly
- ✅ **Validation**: All engine payloads validated (state, flags, scores, diagnostics, price)

**Fixes Applied**:
1. ✅ Backfill made synchronous (removed async wrapper)
2. ✅ Backfill targets 666 bars with 333 minimum (updated from 300)
3. ✅ TA Tracker minimum for 1m reduced from 4320 to 333 bars
4. ✅ Comprehensive logging added to test
5. ✅ Test assertions updated to expect 333+ bars (from 290+)

**Setup**:
1. Pick real token from `token_registry_backup.json` (e.g., POLYTALE on Solana)
2. Seed test database with:
   - Real token (from registry, with real contract address)
   - Real OHLC data (350+ bars for 1h timeframe - fetch via backfill or GeckoTerminal API)
   - Create test position with `status='watchlist'`, `bars_count >= 350`

**Flow Test Steps**:

1. **Run TA Tracker**:
   - Process position to populate `features.ta`
   - **Query**: `SELECT features->'ta' FROM lowcap_positions WHERE id = [position_id]`
   - **Assert**: `features.ta` populated with:
     - EMA values (ema60, ema144, ema333)
     - Slopes (ema60_slope, ema144_slope, ema333_slope)
     - ATR (atr)
     - RSI (rsi)
     - Other TA indicators

2. **Run Uptrend Engine**:
   - Process position to compute `features.uptrend_engine_v4`
   - **Query**: `SELECT features->'uptrend_engine_v4' FROM lowcap_positions WHERE id = [position_id]`
   - **Assert**: `uptrend_engine_v4` populated with complete payload:
     - `state`: "S0", "S1", "S2", or "S3" (based on real EMA order)
     - `flags`: Object with `buy_signal`, `buy_flag`, `first_dip_buy_flag`, `trim_flag`, `emergency_exit`, `exit_position`, `reclaimed_ema333` (all boolean)
     - `scores`: Object with `ox`, `dx`, `edx`, `ts`, `ts_with_boost`, `sr_boost` (all float)
     - `diagnostics`: Object with condition checks, slope values, etc.

3. **Verify Engine Logic**:
   - **Verify State**: State matches EMA order (e.g., if ema60 > ema144 > ema333, state should be "S3")
   - **Verify Flags**: Flags set correctly based on real conditions (e.g., if state="S1" and conditions met, `buy_signal=true`)
   - **Verify Scores**: Scores computed correctly from TA data (e.g., `ts` from trend strength calculation)

**Success Criteria**:
- Engine computes state correctly from EMA order
- Flags set correctly based on state and conditions
- Scores computed correctly from TA data
- No errors in logs

**Note**: This tests the Engine itself. For PM/Executor testing with guaranteed execution, use Scenario 1B.

#### Test Scenario 1B: Complete Learning Loop Flow Test (PM/Executor with Mocked Engine)

**Flow Testing Approach**: Follow one signal through the entire pipeline with mocked engine payloads

**Objective**: Follow one signal through the complete learning loop and verify it reaches the sink

**Flow Test Definition**:
- **Ingress**: Social signal (tweet mentioning token)
- **Payload**: Real tweet data (or recorded real data, unmodified)
- **Expected Path**: 
  1. `social_lowcap` strand created (ID: `test_signal_001`)
  2. `decision_lowcap` strand created (linked to `test_signal_001`)
  3. 4 positions created (linked to decision)
  4. Positions backfilled and processed
  5. Engine payload mocked (for guaranteed execution)
  6. PM executes trade (real execution, $5-10)
  7. Position closes (mocked exit signal)
  8. `position_closed` strand created (linked to position)
  9. Learning system processes strand
  10. Coefficients updated
- **Required Side-Effects**: 
  - 4 positions in database with `entry_context`
  - `position_closed` strand in database
  - Coefficients updated in `learning_coefficients` table
  - Global R/R baseline updated
- **Timeout**: 20 minutes (allows for backfill, real execution, blockchain confirmation)
- **Drop Reasons Allowed**: None (should complete successfully)

**Setup**:
1. Pick real token from `token_registry_backup.json` (e.g., POLYTALE on Solana):
   - Token: "POLYTALE"
   - Contract: "B8bFLQUZg9exegB1RWV9D7eRsQw1EjyfKU22jf1fpump"
   - Chain: "solana"
   
2. Pick real curator from `twitter_curators.yaml` (e.g., "0xdetweiler")

3. Seed test database with:
   - Real curator (from YAML, with chain_counts if needed)
   - Real token (from registry, with real contract address)
   - Real wallet balance ($15-25 USDC on Solana - enough for one position at a time, fees are ~$0.001 per transaction)
   - Real OHLC data (350+ bars for 1h timeframe - fetch via backfill or GeckoTerminal API)
   - Run TA Tracker (populates `features.ta` with EMA, ATR, RSI, etc. from real OHLC)
   - Run Uptrend Engine (computes `features.uptrend_engine_v4` state and flags from real TA data)
   - Empty `learning_coefficients` table (cold start)

**Flow Test Steps** (Follow `test_signal_001` through):

**⚠️ CRITICAL: System must be running** (scheduled jobs, event processing active). Test just observes.

1. **Inject Signal** (`test_signal_001`):
   - Create real social signal (tweet mentioning POLYTALE token from real curator)
   - **Let the system process it** (don't call decision_maker.make_decision() directly)
   - Wait a bit (5-10 seconds) for scheduled job to pick it up
   - **Query**: `SELECT * FROM ad_strands WHERE id = 'test_signal_001' AND kind = 'social_lowcap'`
   - **Assert**: `social_lowcap` strand exists with ID `test_signal_001`
   - **Verify**: Token extracted to real contract, chain resolved to "solana"

2. **Follow to Decision** (System processes automatically):
   - Wait a bit (5-10 seconds) for decision_maker scheduled job to process
   - **Query**: `SELECT * FROM ad_strands WHERE kind = 'decision_lowcap' AND content->>'source_strand_id' = 'test_signal_001'`
   - **Assert**: Decision strand exists (system created it automatically)
   - **Verify**: 5 checks passed, allocation calculated
   - **If not found**: "Packet died at step 2: System didn't process signal → decision"

3. **Follow to Positions** (System creates automatically):
   - **Query**: `SELECT * FROM lowcap_positions WHERE token_contract = 'B8bFLQUZg9exegB1RWV9D7eRsQw1EjyfKU22jf1fpump' AND created_at > [signal_time]`
   - **Assert**: 4 positions created (1m, 15m, 1h, 4h) with real contract address
   - **Verify**: `entry_context` populated with all required fields:
     - `curator` (curator ID, e.g., "0xdetweiler")
     - `chain` (token chain, e.g., "solana")
     - `mcap_bucket` (from BucketVocabulary, e.g., "100k-500k")
     - `vol_bucket` (from BucketVocabulary, e.g., "50k-200k")
     - `age_bucket` (from BucketVocabulary, e.g., "<7d")
     - `mcap_vol_ratio_bucket` (from BucketVocabulary)
     - `intent` (from intent_analysis)
     - `mapping_confidence` (from token_data)
     - Raw values: `mcap_at_entry`, `vol_at_entry`, `age_at_entry`
   - **Verify**: `alloc_cap_usd` split using default percentages (cold start, no learned data):
     - **Expected default splits**: `1m: 5% (0.05)`, `15m: 12.5% (0.125)`, `1h: 70% (0.70)`, `4h: 12.5% (0.125)`
     - **Assert**: `position_1m.alloc_cap_usd == total_allocation_usd * 0.05` (±0.01)
     - **Assert**: `position_15m.alloc_cap_usd == total_allocation_usd * 0.125` (±0.01)
     - **Assert**: `position_1h.alloc_cap_usd == total_allocation_usd * 0.70` (±0.01)
     - **Assert**: `position_4h.alloc_cap_usd == total_allocation_usd * 0.125` (±0.01)
     - **Assert**: Splits sum to 1.0: `sum([0.05, 0.125, 0.70, 0.125]) == 1.0`
     - **Assert**: Total matches: `sum(alloc_cap_usd) == total_allocation_usd` (±0.01)
   - **Wait Condition**: Poll every 5 seconds, max 30 seconds for positions to be created

4. **Follow to Backfill**:
   - **Query**: `SELECT bars_count FROM lowcap_positions WHERE id IN [position_ids]`
   - **Assert**: `bars_count` updated (350+ for watchlist status)
   - **Verify**: OHLC data exists in `lowcap_price_data_ohlc` for all 4 timeframes
   - **Wait Condition**: Poll every 10 seconds, max 2 minutes for `bars_count > 0`

5. **Mock Engine Payload** (For Guaranteed Execution):
   - **Mock**: Seed `features.uptrend_engine_v4` with buy signal payload:
     ```json
     {
       "state": "S1",
       "buy_signal": true,
       "buy_flag": false,
       "first_dip_buy_flag": false,
       "trim_flag": false,
       "emergency_exit": false,
       "exit_position": false,
       "scores": {
         "ts": 0.65,
         "ts_with_boost": 0.70,
         "sr_boost": 0.05
       },
       "price": 0.0001,
       "diagnostics": {
         "buy_check": {
           "entry_zone_ok": true,
           "slope_ok": true,
           "ts_ok": true
         }
       }
     }
     ```
   - **Query**: `UPDATE lowcap_positions SET features = jsonb_set(features, '{uptrend_engine_v4}', '[mocked_payload]'::jsonb) WHERE id = [1h_position_id]`
   - **Verify**: Mocked payload exists in `features.uptrend_engine_v4`

6. **Follow to PM Execution** (System processes automatically - Real Execution):
   - **System processes**: PM scheduled job runs, reads mocked `features.uptrend_engine_v4` payload
   - **System computes**: PM computes `a_final` and `e_final` from phase, cut_pressure, intent, age, mcap
   - **System combines**: PM combines engine flags + A/E scores + position state
   - **System executes**: PM executes real trade (small amount, e.g., $5-10) via Executor
   - **Wait**: Wait for next PM tick (60 seconds) or trigger if needed
   - **Query**: `SELECT features->'pm_execution_history' FROM lowcap_positions WHERE id = [1h_position_id]`
   - **Assert**: Execution history tracked with real transaction hash, includes:
     - `last_s1_buy` (or `last_s2_buy`, `last_s3_buy` depending on state)
     - `timestamp`, `price`, `size_frac`, `signal` type
   - **Verify**: Position `status='active'`, `total_quantity` > 0 (real token amount)
   - **Verify**: Real execution succeeded (check wallet balance, transaction on-chain)
   - **If not found**: "Packet died at step 6: PM didn't execute (system didn't process)"
   - **Wait Condition**: Poll every 5 seconds, max 60 seconds for transaction confirmation

7. **Follow to Position Closure** (System processes automatically - Mocked Exit Signal):
   - **Mock Engine Exit Signal**: Update `features.uptrend_engine_v4` with exit signal:
     ```json
     {
       "state": "S3",
       "buy_signal": false,
       "buy_flag": false,
       "trim_flag": false,
       "emergency_exit": true,
       "exit_position": false
     }
     ```
   - **System processes**: PM scheduled job runs, reads `emergency_exit=True` from mocked engine state
   - **System executes**: PM executes real exit trade (sells real token amount, `size_frac=1.0`)
   - **Wait**: Wait for next PM tick (60 seconds) or trigger if needed
   - **Query**: `SELECT * FROM lowcap_positions WHERE id = [1h_position_id]`
   - **Assert**: `status='watchlist'`, `closed_at` set (timestamp), `total_quantity == 0`
   - **Assert**: `completed_trades` JSONB array populated with one completed trade object containing:
     - `entry_context` (from position's `entry_context`)
     - `entry_price` (from `avg_entry_price`)
     - `exit_price` (from `avg_exit_price`)
     - `entry_timestamp` (from `first_entry_timestamp`)
     - `exit_timestamp` (from `closed_at`)
     - `rr` (calculated R/R ratio, float)
     - `return` (percentage return, float)
     - `max_drawdown` (maximum drawdown, float)
     - `max_gain` (maximum gain, float)
     - `decision_type` (e.g., "emergency_exit")
   - **Query**: `SELECT * FROM ad_strands WHERE kind = 'position_closed' AND position_id = [1h_position_id]`
   - **Assert**: `position_closed` strand exists with:
     - `entry_context` (matches position's `entry_context`)
     - `completed_trades` (matches position's `completed_trades`)
     - `position_id`, `token`, `chain`, `timeframe`
   - **Wait Condition**: Poll every 5 seconds, max 1 minute for position closure

8. **Follow to Learning** (System processes automatically - NO MOCKING):
   - **System processes**: Learning system processes `position_closed` strand automatically (PM calls it directly)
   - **Wait**: Wait a bit (5-10 seconds) for learning system to process
   - **Query**: `SELECT * FROM learning_coefficients WHERE module = 'dm' AND scope = 'lever' AND name = 'curator' AND key = '0xdetweiler'`
   - **Assert**: Coefficient exists with:
     - `weight` clamped between 0.5 and 2.0 (WEIGHT_MIN to WEIGHT_MAX)
     - `rr_short` and `rr_long` both equal to trade R/R (new coefficient, n=1)
     - `n` = 1 (first trade for this lever)
   - **Query**: `SELECT config_data->'global_rr' FROM learning_configs WHERE module_id = 'decision_maker'`
   - **Assert**: Global R/R baseline updated with real R/R from trade:
     - `rr_short` = trade R/R (new baseline, first trade)
     - `rr_long` = trade R/R (new baseline, first trade)
   - **Verify**: EWMA applied correctly:
     - For new coefficient: `rr_short == rr_long == trade_rr` (both start at trade R/R)
     - Decay formula: `decay_weight = exp(-delta_t / tau)` where `tau_short=14 days`, `tau_long=90 days`
     - Weight calculation: `weight = clamp(rr_short / global_rr_short, 0.5, 2.0)`
   - **If not found**: "Packet died at step 8: Learning system didn't process strand"
   - **Wait Condition**: Poll every 5 seconds, max 30 seconds for coefficients to be updated

9. **Verify Sink Reached**:
   - **Sink Definition**: Coefficients updated AND global R/R baseline updated
   - **Query**: Verify both conditions met
   - **Assert**: Packet reached sink successfully

**If Packet Dies**:
- Identify exact failure point: "Packet `test_signal_001` died at step 6 (PM execution)"
- Query database to see what state exists: "Decision created? Positions created? Which position failed?"
- This tells us exactly where the pipeline broke, not just "something failed"
- **Check**: Was the system running? Did scheduled jobs process it? Query to see what the system actually did.

**Success Criteria**:
- Packet `test_signal_001` reached sink (coefficients updated)
- All expected path steps completed (can query and verify each step)
- Required side-effects present (positions, strands, coefficients)
- If packet died, we know exactly where (step number and database state)

**Flow Test Diagnostics**:
- If step 2 fails: "Packet died at decision creation" → Check why Decision Maker rejected
- If step 3 fails: "Packet died at position creation" → Check allocation/balance issues
- If step 6 fails: "Packet died at PM execution" → Check executor/balance issues
- If step 8 fails: "Packet died at learning processing" → Check strand structure/learning system

#### Test Scenario 2: Cold Start (No Learned Data)

**Objective**: Verify system works when no learned data exists

**Setup**:
- Empty `learning_coefficients` table
- Empty `learning_configs` table

**Steps**:
1. Create social signal
2. Decision Maker evaluates
3. Verify allocation uses static multipliers (fallback)
4. Verify timeframe splits use defaults (5%, 12.5%, 70%, 12.5%)
5. Verify no errors thrown

**Success Criteria**:
- System works without learned data
- Fallback logic works correctly
- No errors in logs

#### Test Scenario 3: Bucket Normalization

**Objective**: Verify bucket vocabulary consistency

**Setup**:
- Create test positions with various bucket formats
- Some with standard buckets, some with non-standard

**Steps**:
1. Decision Maker creates positions with buckets
2. Position closes
3. Learning system processes strand
4. Verify buckets normalized correctly
5. Verify coefficients match normalized buckets

**Success Criteria**:
- All buckets normalized to standard format
- Coefficients match normalized buckets
- No bucket mismatches

#### Test Scenario 4: EWMA Temporal Decay

**Objective**: Verify EWMA weights recent trades more heavily using temporal decay (TAU_SHORT=14 days, TAU_LONG=90 days)

**Setup**:
1. Create 3 test positions with different `first_entry_timestamp` values:
   - Position 1: `first_entry_timestamp = now() - timedelta(days=30)`, R/R = 1.5
   - Position 2: `first_entry_timestamp = now() - timedelta(days=7)`, R/R = 2.0
   - Position 3: `first_entry_timestamp = now() - timedelta(days=1)`, R/R = 1.0
2. Manually insert `completed_trades` JSONB for each position:
   ```json
   // Position 1 (30 days ago)
   [{
     "rr": 1.5,
     "entry_timestamp": "2024-10-08T00:00:00Z",
     "exit_timestamp": "2024-10-09T00:00:00Z",
     "entry_price": 0.001,
     "exit_price": 0.0015,
     "return": 0.5,
     "max_drawdown": 0.1,
     "max_gain": 0.5
   }]
   
   // Position 2 (7 days ago)
   [{
     "rr": 2.0,
     "entry_timestamp": "2024-11-01T00:00:00Z",
     "exit_timestamp": "2024-11-02T00:00:00Z",
     "entry_price": 0.001,
     "exit_price": 0.002,
     "return": 1.0,
     "max_drawdown": 0.05,
     "max_gain": 1.0
   }]
   
   // Position 3 (1 day ago)
   [{
     "rr": 1.0,
     "entry_timestamp": "2024-11-06T00:00:00Z",
     "exit_timestamp": "2024-11-07T00:00:00Z",
     "entry_price": 0.001,
     "exit_price": 0.001,
     "return": 0.0,
     "max_drawdown": 0.2,
     "max_gain": 0.0
   }]
   ```
3. Create `position_closed` strands for each position (with `entry_context` and `completed_trades`)

**Steps**:
1. Process trades in order (oldest to newest) via `learning_system.process_strand_event()`
2. After each trade, query coefficient:
   ```sql
   SELECT * FROM learning_coefficients 
   WHERE module = 'dm' AND scope = 'lever' AND name = 'curator' AND key = '[test_curator]'
   ```
3. Verify EWMA updates after each trade

**Expected Behavior**:

**After Trade 1 (30 days ago, R/R=1.5)**:
- New coefficient: `rr_short = 1.5`, `rr_long = 1.5`, `n = 1`
- Weight: `weight = clamp(1.5 / global_rr_short, 0.5, 2.0)` (where `global_rr_short = 1.5`)

**After Trade 2 (7 days ago, R/R=2.0)**:
- Decay weight for 7 days ago with TAU_SHORT=14: `exp(-7/14) ≈ 0.61` (moderate)
- Decay weight for 7 days ago with TAU_LONG=90: `exp(-7/90) ≈ 0.93` (high)
- `rr_short` should move toward 2.0 more than `rr_long` (faster memory)
- Expected: `rr_short` closer to 2.0 than `rr_long`
- `n = 2`

**After Trade 3 (1 day ago, R/R=1.0)**:
- Decay weight for 1 day ago with TAU_SHORT=14: `exp(-1/14) ≈ 0.93` (high)
- Decay weight for 1 day ago with TAU_LONG=90: `exp(-1/90) ≈ 0.99` (very high)
- `rr_short` should move more toward 1.0 than `rr_long` (recent trade affects short-term more)
- Expected: `rr_short` closer to 1.0 than `rr_long`
- `n = 3`

**Success Criteria**:
- **Weight Bounds**: All coefficient weights clamped between 0.5 and 2.0 (WEIGHT_MIN to WEIGHT_MAX)
- **EWMA Decay Pattern**: 
  - Recent trades (1 day ago) affect `rr_short` more than `rr_long` (faster memory)
  - Decay weights decrease with time: `exp(-delta_t / tau)` where `tau_short=14 days`, `tau_long=90 days`
  - `rr_short` more responsive to recent trades than `rr_long`
- **Decay Weight Verification**:
  - `w_short_recent > w_short_old` (recent trade affects short-term more)
  - `w_long_recent > w_long_old` (recent trade affects long-term more)
  - `w_short_recent > w_long_recent` (short-term more responsive to recent trade)
- **Final State**: After all 3 trades:
  - `rr_short` closer to recent R/R values (1.0) than `rr_long`
  - `rr_long` closer to average of all R/R values (1.5, 2.0, 1.0)
  - `n = 3` (counter incremented correctly)

#### Test Scenario 5: Interaction Patterns & Importance Bleed

**Objective**: Verify interaction patterns and importance bleed work correctly

**Setup**:
- Create test trades with matching interaction patterns
- Create test trades with overlapping single-factor coefficients

**Steps**:
1. Process trades with interaction pattern: `curator=A|chain=base|age<7d`
2. Verify interaction coefficient created
3. Verify single-factor coefficients (curator=A, chain=base) updated
4. Verify importance bleed applied (single-factor weights downweighted)
5. Verify next allocation uses interaction weight + adjusted single-factor weights

**Success Criteria**:
- Interaction pattern coefficient created
- Single-factor weights adjusted by importance bleed
- Allocation multiplier reflects both interaction and adjusted single-factor weights

#### Test Scenario 6: Timeframe Weight Learning

**Objective**: Verify timeframe weights are learned and applied

**Setup**:
- Create test trades on different timeframes
- Vary R/R outcomes by timeframe

**Steps**:
1. Close positions on 1m, 15m, 1h, 4h timeframes
2. Verify timeframe coefficients updated
3. Create new position
4. Verify timeframe splits use learned weights (normalized)
5. Verify splits sum to 1.0

**Success Criteria**:
- Timeframe coefficients created per timeframe
- Learned weights normalized correctly
- Allocation splits reflect learned performance

#### Test Scenario 7: Error Handling

**Objective**: Verify system handles errors gracefully

**Test Cases**:
1. **Missing entry_context**:
   - Position closes without `entry_context`
   - Verify learning system skips gracefully (logs warning)

2. **Missing completed_trades**:
   - Strand has no `completed_trades`
   - Verify learning system skips gracefully

3. **Missing R/R metric**:
   - Completed trade has no `rr` field
   - Verify learning system skips gracefully

4. **No OHLC data**:
   - Position closes but no OHLC data available
   - Verify PM handles gracefully (logs warning, sets R/R to None)

5. **Database connection failure**:
   - Simulate database error during coefficient update
   - Verify error logged, system continues

**Success Criteria**:
- All error cases handled gracefully
- No crashes or unhandled exceptions
- Errors logged clearly

#### Test Scenario 8: Multi-Timeframe Position Model

**Objective**: Verify 4 positions per token work independently

**Setup**:
- Create test token
- Create 4 positions (1m, 15m, 1h, 4h)

**Steps**:
1. Verify each position has independent:
   - `alloc_cap_usd`
   - `entry_context`
   - `features.uptrend_engine_v4`
   - `features.pm_execution_history`
2. Execute trades on different timeframes
3. Verify each position tracks independently
4. Close positions on different timeframes
5. Verify each closure emits separate `position_closed` strand
6. Verify learning system processes each separately

**Success Criteria**:
- Positions are independent
- Each timeframe learns separately
- No cross-contamination

#### Test Scenario 9: PM/Executor Testing with Mocked Engine Payload

**Objective**: Test PM decision logic and Executor integration with various engine signal combinations

**Why Mock Engine Payload**:
- Real engine signals may take days/weeks to appear
- Need to test various combinations of state/flags/scores + A/E scores
- Need to test PM's decision logic without waiting for real market conditions

**Setup**:
- Create test position with real token (from registry)
- Seed real OHLC data (for PM's price queries)
- Mock `features.uptrend_engine_v4` payload (complete structure, not just flags)
- Set various A/E scores (a_final, e_final)

**Test Cases** (Mock different engine payloads):

**Test Case 9.1: S1 Initial Entry (buy_signal)**
```json
{
  "state": "S1",
  "buy_signal": true,
  "buy_flag": false,
  "first_dip_buy_flag": false,
  "trim_flag": false,
  "emergency_exit": false,
  "exit_position": false,
  "scores": {
    "ts": 0.65,
    "ts_with_boost": 0.70,
    "sr_boost": 0.05
  },
  "price": 0.0001,
  "diagnostics": {
    "buy_check": {
      "entry_zone_ok": true,
      "slope_ok": true,
      "ts_ok": true,
      "ema60_slope": 0.003,
      "ema144_slope": 0.001
    }
  }
}
```
- A/E scores: `a_final=0.5`, `e_final=0.3`
- **Expected**: PM creates `add` action with size based on `a_final`
- **Verify**: Entry size calculated correctly, execution history updated

**Test Case 9.2: S2 Retest Buy (buy_flag)**
```json
{
  "state": "S2",
  "buy_signal": false,
  "buy_flag": true,
  "first_dip_buy_flag": false,
  "trim_flag": false,
  "emergency_exit": false,
  "scores": {
    "ox": 0.45,
    "ts": 0.60,
    "ts_with_boost": 0.65
  }
}
```
- A/E scores: `a_final=0.7`, `e_final=0.4`
- **Expected**: PM creates `add` action (S2 retest buy)
- **Verify**: Entry size uses `a_final` + profit/allocation multipliers

**Test Case 9.3: S3 DX Buy (buy_flag)**
```json
{
  "state": "S3",
  "buy_signal": false,
  "buy_flag": true,
  "first_dip_buy_flag": false,
  "trim_flag": false,
  "emergency_exit": false,
  "scores": {
    "ox": 0.50,
    "dx": 0.75,
    "edx": 0.40,
    "ts": 0.65,
    "ts_with_boost": 0.70
  }
}
```
- A/E scores: `a_final=0.6`, `e_final=0.3`
- **Expected**: PM creates `add` action (S3 DX buy)
- **Verify**: Entry size uses `a_final` + entry multiplier (profit/allocation based)

**Test Case 9.4: S3 First Dip Buy (first_dip_buy_flag)**
```json
{
  "state": "S3",
  "buy_signal": false,
  "buy_flag": false,
  "first_dip_buy_flag": true,
  "trim_flag": false,
  "emergency_exit": false,
  "scores": {
    "ox": 0.40,
    "dx": 0.60,
    "edx": 0.35,
    "ts": 0.55,
    "ts_with_boost": 0.60
  }
}
```
- A/E scores: `a_final=0.8`, `e_final=0.2`
- **Expected**: PM creates `add` action (S3 first dip buy)
- **Verify**: Entry size uses `a_final` + entry multiplier

**Test Case 9.5: S2/S3 Trim (trim_flag)**
```json
{
  "state": "S3",
  "buy_signal": false,
  "buy_flag": false,
  "first_dip_buy_flag": false,
  "trim_flag": true,
  "emergency_exit": false,
  "scores": {
    "ox": 0.70,
    "dx": 0.50,
    "edx": 0.45,
    "ts": 0.60
  }
}
```
- A/E scores: `a_final=0.4`, `e_final=0.7`
- Position state: `profit_ratio=0.5`, `allocation_deployed_ratio=0.6`
- **Expected**: PM creates `trim` action with size based on `e_final` + trim multiplier
- **Verify**: Trim size calculated correctly, cooldown logic works

**Test Case 9.6: S3 Emergency Exit (emergency_exit)**
```json
{
  "state": "S3",
  "buy_signal": false,
  "buy_flag": false,
  "first_dip_buy_flag": false,
  "trim_flag": false,
  "emergency_exit": true,
  "exit_position": false,
  "scores": {
    "ox": 0.50,
    "dx": 0.40,
    "edx": 0.60,
    "ts": 0.45
  }
}
```
- A/E scores: `a_final=0.2`, `e_final=0.9`
- **Expected**: PM creates `emergency_exit` action with `size_frac=1.0`
- **Verify**: Full exit executed, position closed, `completed_trades` populated

**Test Case 9.7: Global Exit (exit_position)**
```json
{
  "state": "S1",
  "buy_signal": false,
  "buy_flag": false,
  "trim_flag": false,
  "emergency_exit": false,
  "exit_position": true,
  "exit_reason": "fast_band_at_bottom"
}
```
- **Expected**: PM creates `emergency_exit` action with `size_frac=1.0` (highest precedence)
- **Verify**: Exit executed regardless of A/E scores

**Test Case 9.8: No Action (Hold)**
```json
{
  "state": "S1",
  "buy_signal": false,
  "buy_flag": false,
  "trim_flag": false,
  "emergency_exit": false,
  "scores": {
    "ts": 0.50,
    "ts_with_boost": 0.55
  }
}
```
- A/E scores: `a_final=0.3`, `e_final=0.2`
- **Expected**: PM returns empty actions list (no strand emitted)
- **Verify**: No execution, no strand created

**Test Case 9.9: A/E Score Variations**
- Test with various A/E score combinations:
  - Low A (0.1) + Low E (0.1) → Small entries, small trims
  - High A (0.9) + Low E (0.1) → Large entries, small trims
  - Low A (0.1) + High E (0.9) → Small entries, large trims
  - High A (0.9) + High E (0.9) → Large entries, large trims
- **Verify**: Position sizing reflects A/E scores correctly

**Test Case 9.10: Execution History Tracking**
- Mock engine payload with `buy_flag=true` (S2)
- Execute buy
- Mock engine payload again with `buy_flag=true` (same state)
- **Expected**: PM does NOT execute again (already executed in this state)
- **Verify**: Execution history prevents duplicate executions

**Test Case 9.11: State Transition Resets**
- Mock engine: S2 with `buy_flag=true` → Execute buy
- Mock engine: S3 with `buy_flag=true` (state transitioned)
- **Expected**: PM executes buy again (state transition resets buy eligibility)
- **Verify**: Execution history tracks state transitions

**Test Case 9.12: Trim Cooldown Logic**
- Mock engine: S3 with `trim_flag=true` → Execute trim
- Mock engine: S3 with `trim_flag=true` (3 bars later, same S/R level)
- **Expected**: PM executes trim again (cooldown expired)
- Mock engine: S3 with `trim_flag=true` (1 bar later, same S/R level)
- **Expected**: PM does NOT execute (cooldown not expired)
- Mock engine: S3 with `trim_flag=true` (1 bar later, NEW S/R level)
- **Expected**: PM executes trim (S/R level changed, cooldown bypassed)
- **Verify**: Cooldown logic works correctly

**Success Criteria**:
- PM correctly interprets engine payload (not just boolean flags)
- PM correctly combines engine signals + A/E scores
- PM correctly calculates position sizing from A/E scores
- PM correctly tracks execution history
- PM correctly applies profit/allocation multipliers
- Executor executes trades correctly
- All combinations tested and verified

#### Test Scenario 10: Majors Data Flow Test (SPIRAL Engine Dependency)

**Flow Testing Approach**: Follow majors data through ingestion → rollup → SPIRAL consumption

**Objective**: Verify majors data pipeline works end-to-end and SPIRAL engine can access it

**Flow Test Definition**:
- **Ingress**: Hyperliquid WebSocket feed (or seeded `majors_trades_ticks`)
- **Payload**: Real trade ticks for majors (BTC, SOL, ETH, BNB, HYPE)
- **Expected Path**:
  1. Trade ticks ingested into `majors_trades_ticks`
  2. 1m OHLC rolled up into `majors_price_data_1m`
  3. OHLC rolled up to higher timeframes (15m, 1h, 4h) into `majors_price_data_ohlc`
  4. SPIRAL engine queries majors data for phase detection
  5. Returns computed (`r_btc`, `r_alt`, `r_port`)
- **Required Side-Effects**:
  - `majors_trades_ticks` populated with recent data
  - `majors_price_data_1m` populated with 1m bars
  - `majors_price_data_ohlc` populated with 15m, 1h, 4h bars
  - SPIRAL engine can compute returns successfully
- **Timeout**: 10 minutes (allows for data ingestion and rollup)
- **Drop Reasons Allowed**: None (should complete successfully)

**Setup**:
1. **Start Hyperliquid WebSocket ingest** (or seed `majors_trades_ticks` with real historical data)
   - Tokens: BTC, SOL, ETH, BNB, HYPE
   - Time range: Last 7 days (enough for rollup and SPIRAL calculations)

2. **Verify ingestion**:
   - **Query**: `SELECT COUNT(*), MIN(ts), MAX(ts) FROM majors_trades_ticks WHERE token IN ('BTC', 'SOL', 'ETH', 'BNB', 'HYPE')`
   - **Assert**: Data exists for all 5 tokens, timestamps are recent

**Flow Test Steps**:

1. **Follow to 1m Rollup**:
   - **Run**: `rollup.py` main() (or scheduled job)
   - **Query**: `SELECT COUNT(*), token FROM majors_price_data_1m WHERE ts >= NOW() - INTERVAL '7 days' GROUP BY token`
   - **Assert**: 1m bars exist for all 5 tokens (BTC, SOL, ETH, BNB, HYPE)
   - **Verify**: Each token has sufficient bars (e.g., 7 days = ~10,080 bars)
   - **Verify**: OHLC values are valid (high >= low, close within high/low range)

2. **Follow to OHLC Rollup**:
   - **Run**: `rollup_ohlc.py` for majors data source (15m, 1h, 4h timeframes)
   - **Query**: `SELECT COUNT(*), token_contract, timeframe FROM majors_price_data_ohlc WHERE timestamp >= NOW() - INTERVAL '7 days' GROUP BY token_contract, timeframe`
   - **Assert**: OHLC data exists for all 5 tokens across all timeframes (15m, 1h, 4h)
   - **Verify**: 15m bars = ~1m bars / 15 (approximately)
   - **Verify**: 1h bars = ~1m bars / 60 (approximately)
   - **Verify**: 4h bars = ~1m bars / 240 (approximately)
   - **Verify**: OHLC values are valid (high >= low, close within high/low range)

3. **Follow to SPIRAL Engine Consumption**:
   - **Run**: `ReturnsComputer.compute()` (or SPIRAL phase detection)
   - **Query**: Verify SPIRAL can access majors data:
     ```python
     # SPIRAL queries majors_price_data_1m for:
     # - BTC close (r_btc)
     # - Alt basket closes (SOL, ETH, BNB, HYPE) for r_alt
     # - Portfolio NAV for r_port
     ```
   - **Assert**: `ReturnsResult` contains:
     - `r_btc`: Valid log return (not None, not 0.0 unless no price change)
     - `r_alt`: Valid log return (equal-weighted alt basket)
     - `r_port`: Valid log return (from portfolio_bands.nav_usd)
     - `closes_now`: Dict with BTC, SOL, ETH, BNB, HYPE closes
     - `closes_prev`: Dict with previous closes
   - **Verify**: Returns are computed correctly (log(now) - log(prev))
   - **Verify**: Alt basket is equal-weighted mean of SOL, ETH, BNB, HYPE

4. **Follow to Phase Detection** (if SPIRAL phase detection is active):
   - **Run**: SPIRAL phase detection using returns
   - **Query**: Check if phase state is computed (if stored in database)
   - **Assert**: Phase detection can access majors data and compute phases
   - **Verify**: Phases are valid (macro/meso/micro phases)

**Success Criteria**:
- Majors data ingestion works (Hyperliquid WS or seeded data)
- 1m rollup works correctly
- OHLC rollup works for all timeframes (15m, 1h, 4h)
- SPIRAL engine can query majors data successfully
- Returns are computed correctly (`r_btc`, `r_alt`, `r_port`)
- Phase detection can access majors data (if implemented)

**Failure Points**:
- **If packet dies at step 1**: Hyperliquid WS not running, or `majors_trades_ticks` not seeded
- **If packet dies at step 2**: Rollup job not running, or insufficient data in `majors_trades_ticks`
- **If packet dies at step 3**: OHLC rollup job not running, or `majors_price_data_1m` missing
- **If packet dies at step 4**: SPIRAL engine can't query majors data, or data format mismatch

**Note**: This test is critical because SPIRAL engine depends on majors data for phase detection, which affects A/E scores and PM decision-making. Without majors data, the entire system cannot function correctly.

#### Test Scenario 11: SPIRAL Engine Testing (A/E Score Computation)

**Flow Testing Approach**: Test SPIRAL engine phase detection and A/E score calculation

**Objective**: Verify SPIRAL engine computes A/E scores correctly from phase, cut_pressure, intent, age, and mcap

**Flow Test Definition**:
- **Ingress**: Majors data (from Scenario 10) + test position
- **Payload**: Real majors data + test position with various phase states
- **Expected Path**:
  1. Majors data available (from Scenario 10)
  2. Portfolio bands NAV data available
  3. SPIRAL computes phase detection (macro/meso/micro phases)
  4. SPIRAL computes A/E scores from phase + cut_pressure + intent + age + mcap
  5. A/E scores validated
- **Required Side-Effects**:
  - Phase state computed (if stored in database)
  - A/E scores computed correctly
  - A/E scores clamped to 0.0-1.0 range
- **Timeout**: 5 minutes
- **Drop Reasons Allowed**: None (should complete successfully)

**Setup**:
1. **Prerequisites**: Scenario 10 must pass (majors data available)
2. Seed test database with:
   - Majors data (from Scenario 10)
   - Portfolio bands with NAV data (`portfolio_bands.nav_usd`)
   - Test position with various attributes:
     - `intent` (e.g., "research_positive", "pump_negative")
     - `age_at_entry` (e.g., 3 days)
     - `mcap_at_entry` (e.g., 1,500,000)
   - Various phase states (macro/meso/micro phases)

**Flow Test Steps**:

1. **Verify Majors Data Available**:
   - **Query**: `SELECT COUNT(*) FROM majors_price_data_1m WHERE token IN ('BTC', 'SOL', 'ETH', 'BNB', 'HYPE') AND ts >= NOW() - INTERVAL '7 days'`
   - **Assert**: Data exists for all 5 tokens
   - **Query**: `SELECT nav_usd FROM portfolio_bands ORDER BY timestamp DESC LIMIT 1`
   - **Assert**: NAV data exists

2. **Test Phase Detection** (if implemented):
   - **Run**: SPIRAL phase detection
   - **Query**: Check if phase state is computed (if stored in database)
   - **Assert**: Phase detection can access majors data and compute phases
   - **Verify**: Phases are valid (macro/meso/micro phases)

3. **Test A Score Calculation**:
   - **Run**: SPIRAL computes `a_final` from:
     - Phase (macro/meso/micro)
     - Cut pressure
     - Intent (research_positive, pump_negative, etc.)
     - Age (days since launch)
     - Market cap (mcap_at_entry)
   - **Assert**: `a_final` computed correctly:
     - `a_final` clamped between 0.0 and 1.0
     - `a_final` reflects phase (higher in favorable phases)
     - `a_final` reflects intent (higher for research_positive, lower for pump_negative)
     - `a_final` reflects age (higher for newer tokens)
     - `a_final` reflects mcap (varies by mcap bucket)

4. **Test E Score Calculation**:
   - **Run**: SPIRAL computes `e_final` from:
     - Phase (macro/meso/micro)
     - Cut pressure
   - **Assert**: `e_final` computed correctly:
     - `e_final` clamped between 0.0 and 1.0
     - `e_final` reflects phase (higher in favorable phases)
     - `e_final` reflects cut pressure (higher with more pressure)

5. **Test A/E Score with Missing Data**:
   - **Run**: SPIRAL computes A/E scores with missing majors data
   - **Assert**: Fallback values used (e.g., `a_final=0.5`, `e_final=0.3`)
   - **Verify**: No errors thrown, system continues

**Test Cases**:

**Test Case 11.1: Favorable Phase + Research Positive Intent**
- Phase: Favorable (e.g., macro=uptrend, meso=accumulation)
- Intent: "research_positive"
- Age: 3 days
- MCap: 1,500,000
- **Expected**: `a_final` high (e.g., 0.7-0.9), `e_final` moderate (e.g., 0.4-0.6)

**Test Case 11.2: Unfavorable Phase + Pump Negative Intent**
- Phase: Unfavorable (e.g., macro=downtrend, meso=distribution)
- Intent: "pump_negative"
- Age: 30 days
- MCap: 10,000,000
- **Expected**: `a_final` low (e.g., 0.1-0.3), `e_final` low (e.g., 0.2-0.4)

**Test Case 11.3: Missing Majors Data**
- Majors data: None or incomplete
- **Expected**: Fallback A/E scores (e.g., `a_final=0.5`, `e_final=0.3`)
- **Verify**: No errors, system continues

**Success Criteria**:
- SPIRAL can access majors data successfully
- Phase detection works (if implemented)
- A/E scores computed correctly from all inputs
- A/E scores clamped to 0.0-1.0 range
- Missing data handled gracefully with fallback values
- No errors in logs

### 2.4 Module-Level Testing (Component Tests - Layer 1)

**Purpose**: Test individual components in isolation before flow testing

#### Test Module: BucketVocabulary

**Test Cases**:
1. `get_mcap_bucket()` - Test all bucket boundaries
2. `get_vol_bucket()` - Test all bucket boundaries
3. `get_age_bucket()` - Test all bucket boundaries
4. `get_mcap_vol_ratio_bucket()` - Test all bucket boundaries
5. `normalize_bucket()` - Test normalization of various formats

**Success Criteria**:
- All buckets calculated correctly
- Edge cases handled (boundary values)
- Normalization works for various formats

#### Test Module: CoefficientUpdater

**Test Cases**:
1. `calculate_decay_weight()` - Test decay over time
2. `update_coefficient_ewma()` - Test EWMA updates
3. `generate_interaction_key()` - Test key generation consistency
4. `update_interaction_pattern()` - Test interaction updates
5. `apply_importance_bleed()` - Test bleed calculation

**Success Criteria**:
- Decay weights decrease with time
- EWMA updates reflect recent trades more
- Interaction keys are consistent
- Importance bleed applied correctly

#### Test Module: CoefficientReader

**Test Cases**:
1. `get_lever_weights()` - Test reading all levers
2. `get_interaction_weight()` - Test reading interaction patterns
3. `apply_importance_bleed()` - Test bleed application
4. `calculate_allocation_multiplier()` - Test multiplier calculation
5. `get_timeframe_weights()` - Test timeframe weight reading
6. `normalize_timeframe_weights()` - Test normalization

**Success Criteria**:
- All weights read correctly
- Multiplier calculation correct
- Fallback works when no data

#### Test Module: Decision Maker

**Test Cases**:
1. `_build_entry_context_for_learning()` - Test bucket calculation
2. `_calculate_allocation_with_curator()` - Test allocation with learned coefficients
3. `_create_positions_for_token()` - Test position creation with entry_context
4. Fallback to static multipliers when no learned data

**Success Criteria**:
- Entry context populated correctly
- Allocation uses learned coefficients
- Fallback works correctly

#### Test Module: PM Core Tick

**Test Cases**:
1. `_calculate_rr_metrics()` - Test R/R calculation from OHLC
2. `_check_position_closure()` - Test closure detection
3. `_update_position_after_execution()` - Test position updates
4. `_update_execution_history()` - Test execution history tracking
5. Strand emission with correct structure

**Success Criteria**:
- R/R calculated correctly
- Closure detected correctly
- Execution history tracked correctly

#### Test Module: Majors Data Ingestion & Rollup

**Test Cases**:
1. **Hyperliquid WS Ingest**:
   - Test trade tick ingestion into `majors_trades_ticks`
   - Test handling of missing/invalid ticks
   - Test timestamp alignment (UTC-aligned bars)

2. **1m Rollup**:
   - Test rollup from `majors_trades_ticks` to `majors_price_data_1m`
   - Test OHLC calculation (open, high, low, close)
   - Test volume aggregation
   - Test handling of gaps in data

3. **OHLC Rollup**:
   - Test rollup from `majors_price_data_1m` to `majors_price_data_ohlc` (15m, 1h, 4h)
   - Test OHLC aggregation (open = first open, high = max high, low = min low, close = last close)
   - Test volume summation across timeframes
   - Test handling of incomplete bars

4. **SPIRAL Returns Computer**:
   - Test querying `majors_price_data_1m` for BTC close
   - Test querying `majors_price_data_1m` for alt basket (SOL, ETH, BNB, HYPE)
   - Test log return calculation (`r_btc`, `r_alt`)
   - Test portfolio return calculation (`r_port` from `portfolio_bands.nav_usd`)
   - Test handling of missing data (returns 0.0 or None)

**Success Criteria**:
- Trade ticks ingested correctly
- 1m OHLC calculated correctly
- Higher timeframe OHLC rolled up correctly
- SPIRAL can query majors data successfully
- Returns computed correctly
- Missing data handled gracefully

### 2.5 Integration Testing (Component Integration - Layer 1)

**Purpose**: Test how components work together, but still focused on specific integration points

#### Test: Decision Maker → Learning System

**Objective**: Verify Decision Maker creates positions that learning system can process

**Steps**:
1. Decision Maker creates position with `entry_context`
2. Position closes
3. Learning system processes `position_closed` strand
4. Verify `entry_context` from strand matches position's `entry_context`
5. Verify coefficients updated for all levers in `entry_context`

**Success Criteria**:
- Entry context preserved through closure
- Learning system can extract all lever values
- Coefficients updated correctly

#### Test: PM → Learning System

**Objective**: Verify PM emits strands that learning system can process

**Steps**:
1. PM closes position
2. PM computes R/R and writes `completed_trades`
3. PM emits `position_closed` strand
4. **CRITICAL**: Verify learning system is triggered
   - **If Option A (Queue)**: Verify scheduled job processes `learning_queue` and calls `process_strand_event()`
   - **If Option B (Direct)**: Verify PM calls `learning_system.process_strand_event()` directly
5. Learning system processes strand
6. Verify `completed_trades` from strand matches position's `completed_trades`
7. Verify R/R used for coefficient updates

**Success Criteria**:
- Strand emitted correctly
- Learning system triggered (direct call or queue)
- Completed trades preserved in strand
- Learning system can extract R/R
- Coefficients updated with correct R/R

**Current Flow**:
- PM inserts strand into `ad_strands` table
- Database trigger `strand_learning_trigger` fires automatically
- Trigger inserts into `learning_queue` table with status='pending'
- **Gap**: No scheduled job processes `learning_queue` to call `process_strand_event()`

**Solution Options**:
- **Option A**: Add scheduled job in `run_social_trading.py`:
  ```python
  async def process_learning_queue_job():
      # Get pending strands from learning_queue
      # For each strand, call learning_system.process_strand_event()
      # Update queue status
  ```
- **Option B**: PM calls `learning_system.process_strand_event()` directly after inserting strand (simpler, matches Social Ingest/Decision Maker pattern)

**Recommendation**: Option B - Direct call is simpler and more reliable

#### Test: Learning System → Decision Maker

**Objective**: Verify Decision Maker uses updated coefficients

**Steps**:
1. Create test coefficients in `learning_coefficients` table
2. Decision Maker evaluates new signal
3. Verify `CoefficientReader` reads coefficients
4. Verify allocation multiplier uses coefficients
5. Verify allocation reflects learned performance

**Success Criteria**:
- Coefficients read correctly
- Allocation reflects learned performance
- Logs show coefficient usage

### 2.6 Performance Testing

#### Test: Coefficient Update Performance

**Objective**: Verify coefficient updates are fast enough

**Steps**:
1. Process 100 `position_closed` strands
2. Measure time per update
3. Verify updates complete in < 1 second each

**Success Criteria**:
- Updates complete quickly
- No database locks
- No performance degradation

#### Test: Allocation Calculation Performance

**Objective**: Verify allocation calculation is fast enough

**Steps**:
1. Create 1000 test coefficients
2. Decision Maker calculates allocation
3. Measure time per calculation
4. Verify calculation completes in < 100ms

**Success Criteria**:
- Calculation is fast
- No performance issues with many coefficients

### 2.7 Data Integrity Testing

#### Test: Database Consistency

**Objective**: Verify database state is always consistent

**Checks**:
1. All positions have `entry_context` when created
2. All closed positions have `completed_trades`
3. All `position_closed` strands have matching position data
4. All coefficients have valid weights (0.5-2.0)
5. All timeframe weights normalize to 1.0

**Success Criteria**:
- No orphaned data
- No inconsistent states
- All foreign keys valid

### 2.8 Regression Testing

#### Test: Backward Compatibility

**Objective**: Verify system works with old data

**Steps**:
1. Load test database with old position data (without `entry_context`)
2. Verify system handles missing `entry_context` gracefully
3. Verify new positions get `entry_context` populated
4. Verify old positions can still be processed

**Success Criteria**:
- System handles old data gracefully
- New features work with new data
- No breaking changes

---

## Part 3: Test Execution Strategy

### 3.1 Test Order

**⚠️ READ `FLOW_TESTING_ETHOS.md` FIRST**

**Primary Approach: Flow Testing** (Turn system on, inject packet, query database)

1. **Flow Tests** (Follow one packet through entire pipeline - PRIMARY):
   - **Turn the system on** (scheduled jobs running)
   - Inject packet at ingress
   - **Let system process it** (don't orchestrate)
   - Query database at each step
   - Follow packet through using IDs

**Secondary Approach: Component Testing** (Only for isolated utilities)

2. **Unit Tests** (Isolated modules - SECONDARY, only for pure functions):
   - BucketVocabulary tests (pure function)
   - CoefficientUpdater tests (pure function)
   - CoefficientReader tests (pure function)
   - **NOT for Decision Maker, PM, Learning System** - these are tested via flow tests

3. **Flow Tests** (Follow one packet through entire pipeline):
   - **Majors data flow (Scenario 10)** - Run FIRST (SPIRAL depends on majors data)
     - Follow majors data through ingestion → rollup → SPIRAL consumption
     - Verify SPIRAL can compute returns (`r_btc`, `r_alt`, `r_port`)
   - **SPIRAL engine testing (Scenario 11)** - Run AFTER Scenario 10 (depends on majors data)
     - Test SPIRAL phase detection and A/E score computation
   - **Uptrend Engine testing (Scenario 1A)** - Test engine with real data (no execution)
     - Verify engine computes state/flags/scores correctly
   - **Complete learning loop flow (Scenario 1B)** - Follow `test_signal_001` through with mocked engine
     - Full pipeline: signal → decision → positions → execution → closure → learning
   - Cold start flow (Scenario 2) - Follow signal through with no learned data
   - Multi-timeframe flow (Scenario 8) - Follow signal through all 4 timeframes
   - Error handling flow (Scenario 7) - Inject errors, see where packet dies

**Layer 3: Validation**
4. **Performance & Data Integrity**:
   - Performance tests
   - Data integrity checks
   - Regression tests

**Flow Test Principles**:
- **Turn the system on** (scheduled jobs, event processing running)
- **System runs itself** - test just observes
- Use real data wherever possible (real tokens, real curators, real execution)
- **Test Engine Itself**: Run real components (TA Tracker, Uptrend Engine) with real data
- **Test PM/Executor**: Mock engine payload to test various combinations without waiting days/weeks
- Mock full engine payload structure (state, flags, scores, diagnostics) - NOT just boolean flags
- Understand complexity: Engine emits `{state, flags, scores, diagnostics}`, PM combines with A/E scores
- Use existing IDs (strand IDs, position IDs) to trace paths
- Use database queries to follow: signal → decision → positions → closure → learning
- If we can't trace a packet through, the system is missing a link (add it)
- Know exactly where packet died: "Packet `test_signal_001` died at step 6 (PM execution)"
- Real execution with small amounts (e.g., $5-10 per trade) - tests actual system, not mocks
- **DO NOT orchestrate** - don't call functions directly, let scheduled jobs process it

### 3.2 Test Data Management

**Test Database**:
- Separate test database (not production)
- Reset between test runs (or use transactions)
- Seed with realistic test data
- Clean up after tests

**Test Tokens** (Flow Tests Only):
- Use real tokens from `token_registry_backup.json` (tokens you've already tracked)
- Use real chains (Solana, Base, etc. - not testnet)
- Use real wallet addresses (with small amounts for execution)
- Use real contract addresses (from registry)

**Test Curators** (Flow Tests Only):
- Use real curators from `twitter_curators.yaml` (your actual curators)
- Use real curator IDs (e.g., "0xdetweiler", "louiscooper")
- Set up chain_counts if needed (or use existing data)

### 3.5 Test Data Fixtures

**Test Token: POLYTALE**
- Contract: `B8bFLQUZg9exegB1RWV9D7eRsQw1EjyfKU22jf1fpump`
- Chain: `solana`
- Token Ticker: `POLYTALE`
- Expected mcap_bucket: `"100k-500k"` (verify at test time - may vary)
- Expected vol_bucket: `"50k-200k"` (verify at test time - may vary)
- Expected age_bucket: `"<7d"` (verify at test time - may vary)
- Minimum OHLC bars required: 350 (for 1h timeframe)
- Source: `token_registry_backup.json`

**Test Curator: 0xdetweiler**
- Curator ID: `0xdetweiler`
- Expected chain_counts: `{"solana": 5, "base": 3}` (verify at test time - may vary)
- Test tweet format: `"Check out $POLYTALE on Solana! 🚀"`
- Source: `twitter_curators.yaml`

**Test Wallet**:
- Address: `[test_wallet_address]` (store in test config, not in code)
- Initial balance: $15-25 USDC on Solana
- Private key: `[stored in test config, not in code]`
- Network: Mainnet (not testnet) for real execution testing

**Test Database Connection**:
- Database URL: `[test_database_url]` (separate from production)
- Connection pool: 5 connections
- Transaction isolation: `READ_COMMITTED`

### 3.6 Test Automation Structure

**Test Framework**: pytest with async support

**Test Organization**:
```
tests/
├── unit/                    # Component tests (Layer 1)
│   ├── test_bucket_vocabulary.py
│   ├── test_coefficient_updater.py
│   ├── test_coefficient_reader.py
│   └── test_decision_maker.py
├── integration/             # Integration tests (Layer 1)
│   ├── test_dm_learning_system.py
│   ├── test_pm_learning_system.py
│   └── test_learning_dm.py
├── flow/                    # Flow tests (Layer 2)
│   ├── test_scenario_1a_engine.py
│   ├── test_scenario_1b_learning_loop.py
│   ├── test_scenario_2_cold_start.py
│   ├── test_scenario_4_ewma.py
│   ├── test_scenario_9_pm_executor.py
│   ├── test_scenario_10_majors_data.py
│   └── test_scenario_11_spiral.py
└── fixtures/                # Test data fixtures
    ├── test_tokens.json
    ├── test_curators.yaml
    └── test_ohlc_data.json
```

**Test Database Management**:
- Use pytest fixtures for database setup/teardown
- Use transactions for isolation (rollback after each test)
- Seed data via fixtures
- Clean up after tests

**Test Execution**:
```bash
# Run component tests
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run flow tests (requires test database)
pytest tests/flow/ -v -m flow

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

**Test Fixtures Example**:
```python
# conftest.py
import pytest
from src.database import get_test_db_connection

@pytest.fixture(scope="function")
def test_db():
    """Create test database connection with transaction rollback"""
    conn = get_test_db_connection()
    conn.begin()
    yield conn
    conn.rollback()
    conn.close()

@pytest.fixture
def test_token():
    """Test token fixture"""
    return {
        "contract": "B8bFLQUZg9exegB1RWV9D7eRsQw1EjyfKU22jf1fpump",
        "chain": "solana",
        "ticker": "POLYTALE"
    }

@pytest.fixture
def test_curator():
    """Test curator fixture"""
    return {
        "id": "0xdetweiler",
        "chain_counts": {"solana": 5, "base": 3}
    }
```

**Wait Conditions Helper**:
```python
# test_helpers.py
import time
from typing import Callable, Optional

def wait_for_condition(
    condition: Callable[[], bool],
    timeout: int = 30,
    poll_interval: int = 5,
    error_message: str = "Condition not met within timeout"
) -> bool:
    """Wait for condition to be true, polling at intervals"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition():
            return True
        time.sleep(poll_interval)
    raise TimeoutError(error_message)
```

**Example Usage**:
```python
# In flow test
def test_scenario_1b_learning_loop(test_db, test_token, test_curator):
    # ... test steps ...
    
    # Wait for positions to be created
    wait_for_condition(
        lambda: len(get_positions(test_token["contract"])) == 4,
        timeout=30,
        poll_interval=5,
        error_message="Positions not created within 30 seconds"
    )
```

### 3.3 Test Validation

**Component Tests (Layer 1)**:
- Function return values correct
- Edge cases handled
- Error conditions handled

**Flow Tests (Layer 2)**:
- **Path Validation**: Can we query and verify each step in the path?
  - Query: "Did signal create decision?" → "Did decision create positions?" → etc.
- **Sink Validation**: Did packet reach required sinks?
  - Query: "Are coefficients updated?" → "Is global R/R updated?"
- **Failure Point Identification**: If packet died, where exactly?
  - Query database at each step to see what exists
  - Example: "Packet died at step 6" → Query shows: decision exists, positions exist, but no execution history

**Automated Checks**:
- Database state validation (queries following the path)
- Coefficient value validation (ranges, types)
- Allocation calculation validation (formulas)
- R/R calculation validation (formulas)
- Path completeness (can we trace signal through all steps?)

**Manual Checks**:
- Log review (verify expected behavior)
- Database inspection (verify data written correctly, verify path exists)
- Allocation inspection (verify learned coefficients used)

### 3.4 Test Reporting

**Test Results Document**:
- Test scenario name
- Pass/fail status
- Issues found
- Fixes applied
- Validation evidence (logs, database queries)

**Success Criteria**:
- All critical scenarios pass
- All edge cases handled
- Performance acceptable
- Data integrity maintained

---

## Part 4: Pre-Testing Checklist

### 4.1 Code Review Complete
- [ ] All Phase 1, 2, 3 code reviewed
- [ ] All integration points verified
- [ ] All edge cases identified
- [ ] All error handling verified
- [ ] **CRITICAL**: PM → Learning System integration verified (strand processing trigger)
  - [ ] **Gap Identified**: PM inserts strand but learning system not triggered
  - [ ] **Fix Required**: Either add scheduled job to process `learning_queue` OR PM calls `process_strand_event()` directly
  - [ ] **Recommendation**: PM should call `learning_system.process_strand_event()` directly (matches existing pattern)

### 4.2 Document Review Complete
- [ ] COMPLETE_INTEGRATION_PLAN.md reviewed
- [ ] LEARNING_SYSTEM_V4.md reviewed
- [ ] All cross-references verified
- [ ] All inconsistencies resolved

### 4.3 Test Environment Ready
- [ ] Test database created
- [ ] All schemas applied
- [ ] Test data prepared
- [ ] ] Test configuration set up

### 4.4 Test Plan Approved
- [ ] Test scenarios defined
- [ ] Test data strategy defined
- [ ] Test execution strategy defined
- [ ] Success criteria defined

---

## Critical Gaps Identified

### Gap 1: PM → Learning System Integration

**Issue**: PM inserts `position_closed` strands into `ad_strands` table, which triggers database insert into `learning_queue`, but there's no mechanism to process the queue and call `UniversalLearningSystem.process_strand_event()`.

**Current Flow**:
1. PM inserts strand → `ad_strands` table
2. Database trigger → Inserts into `learning_queue` (status='pending')
3. **Gap**: No scheduled job processes queue → Strands never processed

**Solution Options**:
- **Option A**: Add scheduled job to process `learning_queue` every 1-5 minutes
- **Option B**: PM calls `learning_system.process_strand_event()` directly after inserting strand (recommended - matches Social Ingest/Decision Maker pattern)

**Recommendation**: **Option B** - Direct call is simpler, more reliable, and matches existing code patterns.

**Implementation**:
```python
# In pm_core_tick.py, after inserting position_closed strand:
self.sb.table("ad_strands").insert(position_closed_strand).execute()

# Add direct call to learning system (if available)
if hasattr(self, 'learning_system') and self.learning_system:
    try:
        await self.learning_system.process_strand_event(position_closed_strand)
    except Exception as e:
        logger.error(f"Error processing position_closed strand in learning system: {e}")
```

**Note**: PM Core Tick doesn't currently have access to `learning_system` instance. Need to:
1. Pass `learning_system` to `PMCoreTick.__init__()`, OR
2. Get `learning_system` instance from `run_social_trading.py` context, OR
3. Create new `UniversalLearningSystem` instance in PM Core Tick

---

## Next Steps

### Step 1: Fix Critical Gaps (Before Testing) ✅ **COMPLETE**
1. ✅ **Fix PM → Learning System Integration**
   - ✅ Add `learning_system` parameter to `PMCoreTick.__init__()`
   - ✅ Pass `learning_system` from `run_social_trading.py` when creating `PMCoreTick`
   - ✅ Call `learning_system.process_strand_event()` after inserting `position_closed` strand
   - ⏳ Verify learning system processes `position_closed` strands correctly (needs testing)

2. ✅ **Remove learning_queue infrastructure**
   - ✅ Removed `learning_queue` table from schema
   - ✅ Removed queue insert logic from trigger
   - ✅ Deprecated `process_learning_queue()` methods
   - ✅ All modules now use direct `process_strand_event()` calls

### Step 2: Complete Code Review (Part 1)
- Go through each checklist item
- Verify implementation matches design
- Fix any gaps found

### Step 3: Complete Document Review (Part 1)
- Verify documents match implementation
- Update documents if needed
- Resolve any inconsistencies

### Step 4: Set Up Test Environment (Part 3.2)
- Create test database
- Apply schemas
- Seed test data

### Step 5: Execute Tests (Part 2)
- Run tests in order (Unit → Integration → E2E)
- Document results
- Fix issues found

### Step 6: Validate Results (Part 3.3)
- Verify all tests pass
- Verify data integrity
- Verify performance acceptable

---

**Status**: ✅ Critical gaps fixed - Ready for code review and testing preparation

**Completed**:
- ✅ PM → Learning System integration (direct call implemented)
- ✅ Learning queue removed (cleanup complete)

**Next**: Code review (Part 1) → Document review → Test environment setup → Testing

