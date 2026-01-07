# Hyperliquid Integration - Final Design

**Date**: 2025-01-XX  
**Status**: Final Design - Ready for Implementation  
**Related Docs**: See [Investigation Documents](#related-investigation-documents)

---

## Executive Summary

Add Hyperliquid perpetual futures trading to Lotus Trader using the same universal PM logic, with venue-specific execution adapters. Architecture uses ExecutionIntent pattern for clean separation between PM (universal) and executors (venue-specific).

---

## Architecture Overview

```
Price Data (hyperliquid_price_data_ohlc)
    ↓
PriceDataReader (routes by token_chain)
    ↓
TA Tracker → Geometry Builder → Uptrend Engine (all universal)
    ↓
PM Core Tick (universal A/E + plan_actions_v4)
    ↓
ExecutionIntent (universal, venue-agnostic)
    ↓
ExecutorFactory → HyperliquidExecutor
    ↓
ExecutionPlan → ExecutionResult
```

**Key Principle**: Algorithms are universal, only data source and execution differ.

---

## Final Decisions

### 1. Data Architecture

**Table Structure:**
- **Option A (Recommended)**: One unified table `price_data_ohlc(chain, book_id, symbol, timeframe, ts, o, h, l, c, v)`
  - Pros: Simple routing, unified queries, fewer migrations
  - Cons: Bigger table, needs good indexing/partitioning
- **Option B**: Separate tables per asset class (if different schemas needed)
  - `crypto_spot_price_data_ohlc`, `perps_price_data_ohlc`, `equities_price_data_ohlc`
  - Pros: Different schemas per class, easier TTL/retention
  - Cons: Routing code grows, cross-asset queries harder

**Routing:**
- `PriceDataReader` routes by `(chain, book_id)` tuple
- `chain`: Venue namespace (hyperliquid, solana, nyse, etc.)
- `book_id`: Asset class (perps, onchain_crypto, stocks, etc.)

**Position Schema:**
- `token_chain = "hyperliquid"` (venue namespace)
- `book_id = "perps"` (asset class)
- `token_contract = "BTC"` (ticker, not address)

**WebSocket:**
- Separate WS for trading tokens (not majors)
- One socket, many subscriptions (up to 1,000)
- Backpressure, reconnection, subscription diffing
- **Data Source Decision**: Test Hyperliquid for candle subscriptions
  - If candles available: Use candles for OHLC (lower message volume)
  - If candles not available: Aggregate from trades (current approach)
  - See: `docs/investigations/hyperliquid_candle_data_test_plan.md`

### 2. PM Architecture

**PM Core = Universal:**
- A/E computation: Universal (regime-based)
- `plan_actions_v4()`: Universal (signal-based)
- Produces: `ExecutionIntent` (venue-agnostic)

**Executor = Venue-Specific:**
- `prepare(intent, position) -> ExecutionPlan | Skip`
- `execute(plan, position) -> ExecutionResult`
- All constraints in executor (market hours, min notional, leverage caps, etc.)

**Two Gates (Not Just Executor):**

**Gate A: Scheduler / Tick Eligibility** (data/time gate)
- "Should I run PM tick for this chain/book_id/timeframe right now?"
- For equities: Only run when new bars available within trading sessions
- For crypto/perps: Always run (24/7)
- Belongs **above PM** (scheduler or data reader layer)
- Prevents pointless PM runs when nothing can update

**Gate B: Execution Feasibility** (executor gate)
- "Even if PM produced intent, can I place order now?"
- Belongs in **executor.prepare()**
- Handles: market closed, reduce-only, min notional, leverage caps, venue maintenance, etc.
- Universal safety net when PM emits something but execution isn't allowed

**PM stays deterministic**: Scheduler decides when to call it, executor decides if execution is allowed

### 3. ExecutionIntent Interface

**PM Output:**
```python
@dataclass
class ExecutionIntent:
    action: ActionType  # HOLD, ADD, TRIM, EXIT, etc.
    size_frac: float
    urgency: str
    priority: int
    reason_codes: List[str]
    state: str
    a_final: float
    e_final: float
    # ... position context
```

**Executor Interface:**
```python
class BaseExecutor:
    def prepare(intent, position) -> ExecutionPlan
    def execute(plan, position) -> ExecutionResult
```

See: `docs/investigations/execution_intent_interface_spec.md`

### 4. Naming Conventions

**token_chain**: "Venue namespace" (not literally a chain)
- On-chain: actual chain (solana, ethereum)
- CEX: venue (hyperliquid, binance)
- Equities: exchange (nyse, nasdaq)

**book_id**: Asset class / venue type
- `onchain_crypto`, `perps`, `spot_crypto`
- `stocks`, `commodities`, `fx`, `bonds`

### 5. Universality Guarantees

**Universal (No Changes Needed):**
- TA Tracker algorithms (EMAs, ATR, ADX, RSI)
- Geometry Builder (swing detection, S/R, trendlines)
- Uptrend Engine (state machine, signals)
- PM Core logic (A/E, plan_actions_v4)

**Needs Abstraction:**
- `PriceDataReader`: Routes to correct OHLC table by `(chain, book_id)`
- `ExecutorFactory`: Routes to correct executor by `(chain, book_id)`
- **Scheduler Gate**: Tick eligibility check (new bars / trading session)

**Venue-Specific:**
- Data tables (one per asset class)
- Executors (one per venue)
- Regime drivers (different per asset class)

### 6. Trading Constraints & Order Construction (Live Test Findings)

- **Market emulation**: No explicit market flag. Use limit IOC crossed through top-of-book with a small buffer (e.g., 0.5–1%) and round to the asset’s tick.  
  - Main DEX (e.g., BTC): integer price ticks enforced.  
  - HIP-3 (e.g., `xyz:TSLA`): 2-decimal prices worked in tests.  
- **Min notional**: Observed $10 minimum per order (BTC and HIP-3). Executor must enforce per-asset min notional before submitting.  
- **Reduce-only**: HL rejects reduce-only if it would increase size. Only send reduce-only when it strictly decreases/flat.  
- **Sizing**: Size is in contracts; format with `szDecimals`. Ensure formatting does not zero-out tiny sizes.  
- **HIP-3 routing**: Initialize `Info/Exchange` with `perp_dexs` including `""` plus builder DEX names (e.g., `["", "xyz", "flx", "vntl", "hyna", "km"]`) so HIP-3 symbols resolve.  
- **Error handling**: Map common errors to actionable skips, not retries:  
  - “Price must be divisible by tick size.”  
  - “Order must have minimum value of $10.”  
  - “Reduce only order would increase position.”  
- **Leverage**: SDK order call doesn’t take leverage directly; control exposure via size (or separate leverage config if added later).

### 6. Time Normalization Contract

**Two Clocks:**
- **trading_time index**: Bar number / session bars (what indicators should often use)
- **wall_time**: Actual timestamps (what reality uses)

**Gap Representation (Don't Forward-Fill):**
- Represent gaps explicitly, don't create fake bars
- On each bar, compute gap metrics:
  - `gap_detected`: bool
  - `gap_return_pct = (open - prev_close) / prev_close`
  - `gap_duration = wall_time - prev_wall_time`
  - `session_id` and `is_session_open_bar`

**Indicator Variants:**
- **Session ATR**: Computed only on within-session bars (ignores overnight gaps)
- **Full ATR**: Includes gap via true range (captures real discontinuity)
- Same idea applies to volatility halos / thresholding

**Benefits:**
- Geometry treats gaps as real structure (often correct)
- Uptrend thresholds choose session vs full depending on signal type
- No synthetic bars, explicit gap representation

### 7. Risk Constraints Framework

**Decision Framework:**
- **PM-Level**: If risk affects "should I trade?" → universal risk layer
- **Executor-Level**: If risk affects "how do I execute?" → venue-specific safety

**Current Approach:**
- Start executor-level (leverage caps, reduce-only)
- Promote to PM-level if it materially changes PM behavior

---

## Implementation Phases

### Phase 1: ExecutionIntent Interface (Critical)
1. Create `ExecutionIntent` dataclass
2. Update `plan_actions_v4()` to return `ExecutionIntent` objects
3. Create `BaseExecutor` interface with `prepare()` / `execute()`
4. Update PM Core Tick to use new interface

### Phase 2: Data Infrastructure
1. ✅ Create `hyperliquid_price_data_ohlc` table (see `src/database/hyperliquid_price_data_ohlc_schema.sql`)
2. Create `PriceDataReader` abstraction
3. Update TA Tracker, Geometry Builder, Uptrend Engine to use `PriceDataReader`
4. Test data routing

### Phase 3: Hyperliquid Executor
1. Create `HyperliquidExecutor` (dry-run mode)
2. Implement `prepare()` (constraints, market hours, etc.)
3. Implement `execute()` (Hyperliquid API calls)
4. Test executor routing

### Phase 4: WebSocket Infrastructure
1. Create `HyperliquidTradingWSIngester` (separate from majors)
2. Add backpressure (bounded queues)
3. Add reconnection logic (exponential backoff)
4. Add subscription diffing
5. Test with 10-20 tokens

### Phase 5: End-to-End Testing
1. Create test positions (`token_chain='hyperliquid'`, `book_id='perps'`)
2. Test full cycle: Data → TA → Engine → PM → Executor
3. Verify learning system receives position_closed strands
4. Verify scopes separate correctly

### Phase 6: Production Enablement
1. Enable live execution (remove dry-run)
2. Start with small allocations
3. Monitor performance
4. Scale up token count gradually

---

## Related Investigation Documents

**Exploration & Thinking:**
- `docs/investigations/hyperliquid_integration_architecture.md` - Initial architecture exploration
- `docs/investigations/pm_routing_logic_discussion.md` - PM routing options analysis
- `docs/investigations/hyperliquid_pm_routing_rethink.md` - PM routing rethink after feedback
- `docs/investigations/multi_asset_class_architecture.md` - How architecture scales to equities, commodities, etc.

**Analysis & Validation:**
- `docs/investigations/ta_geometry_universality_analysis.md` - TA/Geometry universality proof
- `docs/investigations/architecture_refinements.md` - Response to feedback and corrections

**Specifications:**
- `docs/investigations/execution_intent_interface_spec.md` - ExecutionIntent interface specification

---

## Key Design Principles

1. **Algorithms are universal** - TA, Geometry, Uptrend Engine, PM logic work on any price series
2. **Data source is abstracted** - `PriceDataReader` routes to correct table
3. **Execution is abstracted** - `ExecutorFactory` routes to correct executor
4. **Scoping separates** - `token_chain` + `book_id` = perfect learning system separation
5. **PM stays deterministic** - All execution constraints in executor, not PM

---

## Pre-Integration Testing Checklist

### ✅ Completed Tests

1. **Trading API** ✅
   - Asset ID computation (main DEX + HIP-3) - Verified
   - Order placement format - Verified
   - Min notional ($10) - Verified
   - Tick size constraints - Verified
   - Reduce-only logic - Verified
   - Market emulation (limit IOC) - Verified
   - HIP-3 routing (perp_dexs initialization) - Verified

2. **Price Data Collection** ✅
   - WebSocket candle subscriptions (all intervals) - Verified
   - Historical backfill (`candleSnapshot`) - Verified
   - Partial update behavior - Documented
   - HIP-3 market format (`{dex}:{coin}`) - Verified

### ⚠️ Pre-Integration Tests Needed

**Note**: Trading constraints (min notional $10, tick size, reduce-only) are already verified via live tests. Focus on implementation validation.

1. **Price Data Collection - Production Validation** (After WS ingester built)
   - [ ] Partial update filtering with real WS stream (timestamp change detection)
   - [ ] Message volume with 100+ symbols (backpressure handling)
   - [ ] Reconnection handling (resubscribe all markets)
   - [ ] Activity gate (only persist markets with volume/trades)
   - [ ] Backfill completeness (no gaps, proper stitching with live data)

2. **Integration Tests** (After components built)
   - [ ] PriceDataReader routing (`chain="hyperliquid"`, `book_id="perps"|"stock_perps"`)
   - [ ] TA Tracker reads from PriceDataReader (no direct table access)
   - [ ] ExecutorFactory routes to HyperliquidExecutor
   - [ ] Position schema (`token_chain`, `book_id`, `token_contract`)

3. **End-to-End Dry-Run** (After all components built)
   - [ ] PM Core Tick → ExecutionIntent → HyperliquidExecutor (dry-run)
   - [ ] Verify field mapping (size_frac → contract size)
   - [ ] Verify constraint guards (implement min notional, tick size, reduce-only checks)
   - [ ] Verify error handling (skip on constraint violations)

4. **Database & Reconciliation** (After executor built)
   - [ ] Transaction recording (size_contracts, price, notional_usd with correct precision)
   - [ ] Position reconciliation (user_state query matches recorded fills)

---

## Open Questions

1. **Order Types**: Market orders only (via limit IOC), or support limit GTC orders?
2. **Slippage Handling**: How does Hyperliquid handle slippage for perps? (Market IOC should minimize)
3. **Position Sizing**: Same sizing logic as Solana, or different multipliers?
4. **Regime Drivers**: Do Hyperliquid positions use same crypto regime drivers? (Yes for `book_id="perps"`, neutral for `book_id="stock_perps"`)
5. **Scheduler Gate Implementation**: How to check "new bar available" for tick eligibility? (Query latest `ts` in `hyperliquid_price_data_ohlc`)

---

## Next Steps

1. **Pre-Integration Testing**: Run all tests in checklist above
2. **Implement**: Create `BaseExecutor` interface and `ExecutionIntent` dataclass
3. **Implement**: Create `HyperliquidExecutor` with all constraint guards
4. **Implement**: Create `PriceDataReader` abstraction
5. **Implement**: Create `HyperliquidCandleWSIngester` with partial update filtering
6. **Test**: End-to-end dry-run with test positions
7. **Integrate**: Wire into PM Core Tick

---

## Summary

**Architecture is universal and scales to all asset classes.**

- ✅ PM logic is universal (A/E, plan_actions_v4)
- ✅ TA/Geometry algorithms are universal
- ✅ Data source abstracted (PriceDataReader)
- ✅ Execution abstracted (ExecutorFactory)
- ✅ Clean separation (ExecutionIntent pattern)
- ✅ Production-ready design

**Ready for implementation.**

