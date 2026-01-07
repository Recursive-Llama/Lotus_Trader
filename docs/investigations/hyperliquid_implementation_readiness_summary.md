# Hyperliquid Implementation - Ready to Start ✅

**Date**: 2025-12-31  
**Status**: ✅ **ALL SYSTEMS GO**

---

## ✅ Complete Readiness Checklist

### Documentation & Specs
- ✅ Pre-Implementation Checklist (finalized, all bugs fixed)
- ✅ Execution Intent Interface Spec
- ✅ Integration Design Document
- ✅ Tick Cursor Table Spec
- ✅ Candle Snapshot API Verified

### Test Files
- ✅ Candle subscriptions tested
- ✅ Candle intervals tested (15m, 1h, 4h)
- ✅ Historical data API tested
- ✅ Token discovery tested (224 crypto + HIP-3)
- ✅ HIP-3 WebSocket tested

### Existing Code (Reference)
- ✅ PM Executor (Solana) - pattern reference
- ✅ PM Core Tick - current flow understood
- ✅ plan_actions_v4 - current output understood
- ✅ Hyperliquid WS (Majors) - pattern reference
- ✅ RegimeAECalculator - location found, update needed

---

## 📋 Implementation Plan (7 Phases)

### Phase 1: Data Infrastructure ⏭️ START HERE
1. Create `hyperliquid_price_data_ohlc` schema
2. Create `price_table_helper.py` (simple helper function)
3. Update TA Tracker, Geometry Builder, Uptrend Engine to use helper

### Phase 2: Token Discovery
5. Create `HyperliquidTokenDiscovery`
6. Test discovery and classification

### Phase 3: WebSocket Ingestion
7. Create `HyperliquidCandleWSIngester`
8. Test WebSocket ingestion

### Phase 4: Historical Backfill
9. Create backfill function (candleSnapshot)
10. Test backfill

### Phase 5: Execution Infrastructure
11. Create `ExecutionIntent` dataclass
12. Create `BaseExecutor` interface
13. Create `ExecutorFactory`
14. Create `HyperliquidExecutor`

### Phase 6: PM Integration
15. Update `plan_actions_v4()` to return ExecutionIntent
16. Update PM Core Tick (ExecutorFactory + Gate A)
17. Update regime calculator (check book_id for stock_perps)

### Phase 7: Testing
18. Create test positions
19. Test end-to-end flow
20. Verify learning system

---

## 🔑 Key Implementation Details

### Current PM Core Tick Flow
```python
# Line ~3550: plan_actions_v4() returns List[Dict]
actions = plan_actions_v4(...)

# Line ~3615: Direct executor call
exec_result = self.executor.execute(act, p)
```

### Target Flow
```python
# plan_actions_v4() returns List[ExecutionIntent]
intents = plan_actions_v4(...)

# Gate A: Check for new bar (tick cursor table)
if not should_run_pm_tick(chain, book_id, symbol, timeframe):
    continue

# ExecutorFactory routes to correct executor
executor = executor_factory.get_executor(token_chain, book_id)
plan = executor.prepare(intent, position)
result = executor.execute(plan, position)
```

### Regime Calculator Location
- **File**: `src/intelligence/lowcap_portfolio_manager/jobs/regime_ae_calculator.py`
- **Method**: `compute_ae_for_token()` (line ~179)
- **Update**: Check `book_id` parameter, return neutral A/E for `book_id='stock_perps'`

### A/E v2 Location
- **File**: `src/intelligence/lowcap_portfolio_manager/pm/ae_calculator_v2.py`
- **Method**: `compute_ae_v2()` (line ~54)
- **Update**: Check `book_id` in regime flags extraction, return neutral for stock_perps

---

## ✅ All Decisions Finalized

1. ✅ **Book ID**: `book_id='perps'` (crypto), `book_id='stock_perps'` (HIP-3 stocks)
2. ✅ **Historical Data**: Hyperliquid `candleSnapshot` (primary), Binance (fallback)
3. ✅ **WebSocket**: Candle subscriptions (NOT trades)
4. ✅ **Activity Gate**: `volume > 0` OR `trade_count > 0`
5. ✅ **Gate A**: Tick cursor table per `(chain, book_id, symbol, timeframe)`
6. ✅ **Regime**: Neutral A/E for stock_perps (PM strength still works)
7. ✅ **Execution**: ExecutionIntent pattern with ExecutorFactory

---

## 🚀 Ready to Start Implementation

**No blocking dependencies** - All specs complete, all decisions finalized.

**Recommended Start**: Phase 1 (Data Infrastructure)

**First File to Create**: `src/database/hyperliquid_price_data_ohlc_schema.sql`

---

## 📝 Notes

- **Incremental**: Each phase builds on previous
- **Test as you go**: Use existing test files
- **Dry-run first**: Start executor in dry-run mode
- **Reference existing**: Use Solana executor and majors WS as patterns

