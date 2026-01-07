# Hyperliquid Implementation - Final Readiness Check

**Date**: 2025-12-31  
**Status**: Pre-Implementation Readiness Assessment

---

## ✅ Documentation & Specs (Complete)

1. ✅ **Pre-Implementation Checklist**: `docs/investigations/hyperliquid_pre_implementation_checklist.md`
   - All decisions finalized
   - All contradictions resolved
   - All bugs fixed

2. ✅ **Execution Intent Spec**: `docs/investigations/execution_intent_interface_spec.md`
   - Complete interface specification
   - BaseExecutor pattern defined

3. ✅ **Integration Design**: `docs/implementation/hyperliquid_integration_design.md`
   - Architecture overview
   - Implementation phases

4. ✅ **Tick Cursor Table Spec**: `docs/investigations/hyperliquid_tick_cursor_table_spec.md`
   - Gate A implementation spec
   - Table schema defined

5. ✅ **Candle Snapshot Verified**: `docs/investigations/hyperliquid_candle_snapshot_verified.md`
   - API format confirmed
   - Test results documented

---

## ✅ Test Files (Complete)

1. ✅ **Candle Subscriptions**: `tests/hyperliquid/test_candle_subscriptions.py`
   - Verified WebSocket candles work

2. ✅ **Candle Intervals**: `tests/hyperliquid/test_candle_intervals.py`
   - Verified 15m, 1h, 4h intervals work

3. ✅ **Candle Snapshot**: `tests/hyperliquid/test_candle_snapshot.py`
   - Verified historical data API format

4. ✅ **Token Discovery**: `tests/hyperliquid/test_token_discovery.py`
   - Verified 224 tokens + HIP-3 markets

5. ✅ **HIP-3 WebSocket**: `tests/hyperliquid/test_hip3_websocket.py`
   - Verified HIP-3 markets accessible

---

## ⚠️ Code Components (Need Implementation)

### Phase 1: Data Infrastructure

1. ❌ **Database Schema**: `hyperliquid_price_data_ohlc`
   - **Status**: Need to create
   - **Location**: `src/database/hyperliquid_price_data_ohlc_schema.sql`
   - **Based on**: `lowcap_price_data_ohlc_schema.sql` (simplified - no native prices)

2. ❌ **Price Table Helper**: Simple helper function
   - **Status**: Need to create
   - **Location**: `src/intelligence/lowcap_portfolio_manager/data/price_table_helper.py`
   - **Purpose**: Returns correct table name based on `(token_chain, book_id)`

3. ❌ **TA Tracker Updates**: Use price table helper
   - **Status**: Need to update
   - **Location**: `src/intelligence/lowcap_portfolio_manager/jobs/ta_tracker.py`
   - **Change**: Replace hardcoded `"lowcap_price_data_ohlc"` with `get_price_table_name(chain, book_id)`

4. ❌ **Geometry Builder Updates**: Use price table helper
   - **Status**: Need to update
   - **Location**: `src/intelligence/lowcap_portfolio_manager/jobs/geometry_build_daily.py`
   - **Change**: Replace hardcoded `"lowcap_price_data_ohlc"` with `get_price_table_name(chain, book_id)`

5. ❌ **Uptrend Engine Updates**: Use price table helper
   - **Status**: Need to update
   - **Location**: `src/intelligence/lowcap_portfolio_manager/jobs/uptrend_engine_v4.py`
   - **Change**: Replace hardcoded `"lowcap_price_data_ohlc"` with `get_price_table_name(chain, book_id)`

### Phase 2: Token Discovery

7. ❌ **HyperliquidTokenDiscovery**: Query and classify markets
   - **Status**: Need to create
   - **Location**: `src/intelligence/lowcap_portfolio_manager/ingest/hyperliquid_token_discovery.py`
   - **Features**:
     - Query main DEX (`type="meta"`)
     - Query HIP-3 DEXs (`type="perpDexs"` → `type="meta", dex="<name>"`)
     - Classify at discovery: `book_id='perps'` or `book_id='stock_perps'`
     - Cache dex/index mappings for asset ID computation

### Phase 3: WebSocket Ingestion

8. ❌ **HyperliquidCandleWSIngester**: Candle stream ingester
   - **Status**: Need to create
   - **Location**: `src/intelligence/lowcap_portfolio_manager/ingest/hyperliquid_candle_ws.py`
   - **Based on**: `src/intelligence/lowcap_portfolio_manager/ingest/hyperliquid_ws.py` (majors)
   - **Features**:
     - Subscribe to `candle` streams (NOT `trades`)
     - Filter complete candles (timestamp change detection)
     - Activity gate: `volume > 0` OR `trade_count > 0`
     - Backpressure, reconnection, subscription diffing

### Phase 4: Historical Backfill

9. ❌ **Backfill Function**: Hyperliquid candleSnapshot
   - **Status**: Need to create
   - **Location**: `src/intelligence/lowcap_portfolio_manager/ingest/hyperliquid_backfill.py`
   - **Format**: Verified in `docs/investigations/hyperliquid_candle_snapshot_verified.md`
   - **Features**:
     - Use `candleSnapshot` endpoint
     - Transform candles to schema
     - Write to `hyperliquid_price_data_ohlc`

### Phase 5: Regime Logic

10. ❌ **RegimeAECalculator Updates**: Check book_id
    - **Status**: Need to update
    - **Location**: Find and update regime calculator
    - **Change**: Return neutral A/E (0.5, 0.5) for `book_id='stock_perps'`
    - **Note**: Remove any ticker substring detection

### Phase 6: Executor

11. ❌ **ExecutionIntent Dataclass**: Universal intent interface
    - **Status**: Need to create
    - **Location**: `src/intelligence/lowcap_portfolio_manager/pm/execution_intent.py`
    - **Spec**: `docs/investigations/execution_intent_interface_spec.md`

12. ❌ **BaseExecutor Interface**: Abstract executor
    - **Status**: Need to create
    - **Location**: `src/intelligence/lowcap_portfolio_manager/pm/base_executor.py`
    - **Spec**: `docs/investigations/execution_intent_interface_spec.md`

13. ❌ **ExecutorFactory**: Route to correct executor
    - **Status**: Need to create
    - **Location**: `src/intelligence/lowcap_portfolio_manager/pm/executor_factory.py`
    - **Features**: Route by `(token_chain, book_id)`

14. ❌ **HyperliquidExecutor**: Hyperliquid-specific executor
    - **Status**: Need to create
    - **Location**: `src/intelligence/lowcap_portfolio_manager/pm/hyperliquid_executor.py`
    - **Features**:
      - Implement `prepare()` (constraints, asset ID computation)
      - Implement `execute()` (Hyperliquid API calls)
      - Handle HIP-3 asset IDs

### Phase 7: PM Integration

15. ❌ **plan_actions_v4 Updates**: Return ExecutionIntent
    - **Status**: Need to update
    - **Location**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py`
    - **Change**: Return `List[ExecutionIntent]` instead of `List[Dict]`

16. ❌ **PM Core Tick Updates**: Use ExecutorFactory + Gate A
    - **Status**: Need to update
    - **Location**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`
    - **Changes**:
      - Add Gate A: Check for new bar (tick cursor table)
      - Use ExecutorFactory to route
      - Handle ExecutionIntent objects
      - Handle ExecutionResult objects

---

## ✅ Existing Code (Ready to Use)

1. ✅ **PM Executor (Solana)**: `src/intelligence/lowcap_portfolio_manager/pm/executor.py`
   - Can use as reference for HyperliquidExecutor
   - Pattern: Direct execution, no events

2. ✅ **PM Core Tick**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`
   - Current flow: `plan_actions_v4()` → `executor.execute()`
   - Need to update to use ExecutorFactory + ExecutionIntent

3. ✅ **plan_actions_v4**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py`
   - Current: Returns `List[Dict]`
   - Need to update to return `List[ExecutionIntent]`

4. ✅ **Hyperliquid WS (Majors)**: `src/intelligence/lowcap_portfolio_manager/ingest/hyperliquid_ws.py`
   - Can use as reference for candle WS ingester
   - Pattern: WebSocket connection, subscription, message handling

---

## 📋 Implementation Order

### Step 1: Data Infrastructure (Foundation)
1. Create `hyperliquid_price_data_ohlc` schema
2. Create `price_table_helper.py` (simple helper function)
3. Update TA Tracker, Geometry Builder, Uptrend Engine to use helper

### Step 2: Token Discovery (Know What to Trade)
5. Create `HyperliquidTokenDiscovery`
6. Test discovery and classification

### Step 3: Data Ingestion (Get Price Data)
7. Create `HyperliquidCandleWSIngester`
8. Test WebSocket ingestion

### Step 4: Historical Data (Backfill)
9. Create backfill function
10. Test backfill

### Step 5: Execution Infrastructure (How to Trade)
11. Create `ExecutionIntent` dataclass
12. Create `BaseExecutor` interface
13. Create `ExecutorFactory`
14. Create `HyperliquidExecutor`

### Step 6: PM Integration (Wire It All Together)
15. Update `plan_actions_v4()` to return ExecutionIntent
16. Update PM Core Tick to use ExecutorFactory + Gate A
17. Update regime calculator for stock_perps

### Step 7: Testing (Verify It Works)
18. Create test positions
19. Test end-to-end flow
20. Verify learning system

---

## ✅ Ready to Start?

**YES** - All specs are complete, all decisions finalized, all test files created.

**Next Action**: Begin with Step 1 (Data Infrastructure)

---

## Notes

- **No blocking dependencies**: Can start implementation immediately
- **Incremental approach**: Each phase builds on previous
- **Test as you go**: Use existing test files to verify each component
- **Dry-run first**: Start with dry-run mode for executor

