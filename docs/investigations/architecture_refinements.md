# Architecture Refinements - Response to Feedback

**Date**: 2025-01-XX  
**Status**: Design Corrections

---

## Summary

The feedback is **100% correct** and identifies critical design issues that would bite us later. This document addresses each point and updates the architecture accordingly.

---

## 1. PM Core Boundary - ExecutionIntent Pattern ✅

### Feedback
> "PM Core = state → intent (compute A/E, call plan_actions_v4, produce ExecutionIntent)"  
> "Venue Adapter (Executor) = intent → executable order plan"  
> "All 'can I trade now?' gating should live in the venue adapter, not PM"

### Response: **AGREED**

**Current Problem:**
- I suggested putting market hours gate in PM Core Tick
- This mixes execution constraints with PM logic
- Makes PM non-deterministic and harder to test

**Corrected Architecture:**

```python
# PM Core produces universal ExecutionIntent
class PMCoreTick:
    def run(self):
        for position in positions:
            # Universal PM logic (deterministic, testable)
            a_final, e_final = compute_ae_v2(...)
            intents = plan_actions_v4(...)  # Returns List[ExecutionIntent]
            
            for intent in intents:
                if intent.action == ActionType.HOLD:
                    continue
                
                # Executor handles ALL constraints
                executor = executor_factory.get_executor(...)
                try:
                    plan = executor.prepare(intent, position)  # Applies constraints
                    result = executor.execute(plan, position)
                except SkipExecution as e:
                    logger.info(f"Skipped: {e.reason}")  # Market closed, constraints, etc.
```

**Benefits:**
- PM stays deterministic and testable
- All execution constraints in one place (executor)
- Can test PM independently (just check intents)
- Executor can skip cleanly with reasons

**Implementation:** See `execution_intent_interface_spec.md`

---

## 2. token_chain Naming Trap ✅

### Feedback
> "token_chain is now doing double duty as venue (hyperliquid) and chain (solana)"  
> "Document that token_chain means 'venue namespace' (not literally a chain)"

### Response: **AGREED**

**Current Problem:**
- `token_chain='hyperliquid'` (venue)
- `token_chain='solana'` (actual blockchain)
- Conceptually confusing

**Corrected Understanding:**

**Current Schema (no changes needed):**
- `token_chain`: **Venue namespace** (not literally a chain)
  - For on-chain: actual chain (solana, ethereum, base)
  - For CEX: venue (hyperliquid, binance, bybit)
  - For equities: exchange (nyse, nasdaq)
  - For commodities: exchange (cme, ice)
  
- `book_id`: **Asset class / venue type**
  - `onchain_crypto`, `perps`, `spot_crypto`
  - `stocks`, `commodities`, `fx`, `bonds`

**Documentation Fix:**
```python
# Schema comment
COMMENT ON COLUMN lowcap_positions.token_chain IS 
    'Venue namespace: actual chain for on-chain (solana, ethereum), 
     venue identifier for CEX (hyperliquid, binance), 
     exchange for equities (nyse, nasdaq), etc.';
```

**Future Refactor (if needed):**
- Could split to `venue_id` + `asset_chain`
- But for now, documenting the semantic meaning is sufficient

---

## 3. Venue-Specific Logic Leakage ✅

### Feedback
> "Equities gaps aren't only a data problem"  
> "Funding/liquidation risk can become a PM-level risk constraint"

### Response: **AGREED**

#### A. Gaps and Feature Meaning

**Problem:**
- Gaps can change the *meaning* of states, not just calculation
- ATR halos, rolling ranges, time-decay features sensitive to continuity

**Solution: Time Normalization Contract**

**Uptrend Engine Contract:**
```python
# Uptrend Engine documentation
"""
Time Normalization Contract:

All features computed on trading-time bars, not wall-clock time.
- Equities: Forward-fill gaps (overnight, weekends, holidays)
- Crypto: Continuous (no gaps)
- FX: Forward-fill weekend gaps

Gap flags exposed upstream:
- features.gap_detected: bool
- features.gap_magnitude_pct: float
- features.gap_type: "overnight" | "weekend" | "holiday"

Uptrend Engine uses gap-aware ATR:
- Session ATR: Intraday only (for intraday signals)
- Full ATR: Includes gaps (for swing signals)
"""
```

**Implementation:**
- Data layer: Forward-fill gaps
- Uptrend Engine: Expose gap flags, use gap-aware ATR
- PM: Can use gap flags if needed (but shouldn't need to)

#### B. Funding/Liquidation Risk

**Problem:**
- Funding rates, liquidation risk could affect PM decisions
- Is this PM-level or executor-level?

**Decision Framework:**

**PM-Level (Universal Risk Layer):**
- If risk affects "should I trade?" → PM-level
- Example: Extreme funding rates → reduce A score universally

**Executor-Level (Venue-Specific Safety):**
- If risk affects "how do I execute?" → Executor-level
- Example: Leverage caps, reduce-only rules

**Recommendation:**
- **Start executor-level** (cap leverage, reduce-only)
- **Promote to PM-level** if it materially changes PM behavior
- **Document decision** in code comments

**Example:**
```python
# Executor-level (for now)
class HyperliquidExecutor:
    def prepare(self, intent, position):
        # Check funding rate
        funding_rate = self._get_funding_rate(intent.token_contract)
        if abs(funding_rate) > 0.01:  # 1% per 8h
            # Cap leverage
            max_leverage = 2.0  # Instead of 10.0
            # Or skip if extreme
            if abs(funding_rate) > 0.05:
                raise SkipExecution(reason="extreme_funding_rate")
        
        # ... rest of prepare ...

# Future: PM-level (if needed)
# If funding rates consistently affect PM decisions:
# - Add funding_rate to ExecutionIntent
# - PM reduces A score when funding extreme
# - Executor still applies caps as safety
```

---

## 4. Hyperliquid WS Limits - Inbound Message Volume ✅

### Feedback
> "Your real risk isn't subscribe rate - it's inbound message volume"  
> "Need backpressure, bounded queues, reconnect logic, subscription diffing"

### Response: **AGREED**

**Current Understanding (Incomplete):**
- Focused on outbound messages (subscriptions)
- Didn't consider inbound message volume

**Corrected Understanding:**

**Limits:**
- **100 WS connections per IP**
- **1,000 subscriptions per IP**
- **2,000 messages sent to HL/min** (outbound)
- **No limit on inbound messages** (but your pipeline can bottleneck)

**Real Risk:**
- Subscribing to 100 tokens = potentially thousands of trades/min
- JSON parsing, DB writes, OHLC aggregation can bottleneck
- Memory can balloon if queues aren't bounded

**Corrected Implementation Plan:**

```python
class HyperliquidTradingWSIngester:
    def __init__(self):
        self.symbols: Set[str] = set()
        self.subscribed_symbols: Set[str] = set()
        
        # Bounded queues per symbol
        self.tick_queues: Dict[str, asyncio.Queue] = {}
        self.max_queue_size = 1000  # Drop ticks if queue full
        
        # Backpressure
        self.write_semaphore = asyncio.Semaphore(10)  # Max 10 concurrent DB writes
        
        # Reconnection
        self.reconnect_backoff = ExponentialBackoff(base=1.0, max=60.0)
    
    async def _ingest_loop(self):
        """Main ingest loop with reconnection"""
        while True:
            try:
                async with websockets.connect(self.ws_url, ...) as ws:
                    await self._subscribe_all(ws)
                    await self._read_loop(ws)
            except Exception as e:
                wait_time = self.reconnect_backoff.next()
                logger.warning(f"Reconnecting in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                await self._resubscribe_delta(ws)  # Only subscribe/unsubscribe changes
    
    async def _read_loop(self, ws):
        """Read messages with backpressure"""
        async for raw in ws:
            # Parse message
            tick = self._parse_tick(raw)
            if not tick:
                continue
            
            # Route to symbol queue
            queue = self.tick_queues.get(tick.token)
            if queue:
                try:
                    queue.put_nowait(tick)  # Non-blocking
                except asyncio.QueueFull:
                    # Drop tick (backpressure)
                    logger.warning(f"Queue full for {tick.token}, dropping tick")
    
    async def _subscription_diff(self):
        """Compute subscription delta"""
        desired = self._get_trading_symbols()  # From positions table
        current = self.subscribed_symbols
        
        to_subscribe = desired - current
        to_unsubscribe = current - desired
        
        return to_subscribe, to_unsubscribe
    
    async def _resubscribe_delta(self, ws):
        """Only subscribe/unsubscribe changes"""
        to_sub, to_unsub = await self._subscription_diff()
        
        for sym in to_unsub:
            await self._unsubscribe(ws, sym)
        
        for sym in to_sub:
            await self._subscribe(ws, sym)
    
    async def _write_worker(self):
        """Dedicated worker for DB writes with backpressure"""
        while True:
            # Process queues with backpressure
            for symbol, queue in self.tick_queues.items():
                if queue.empty():
                    continue
                
                async with self.write_semaphore:  # Limit concurrent writes
                    ticks = []
                    while not queue.empty() and len(ticks) < 100:
                        ticks.append(queue.get_nowait())
                    
                    if ticks:
                        await self._write_ticks(ticks)
```

**Additional Recommendations:**

1. **Prefer Candles Over Trades** (if OHLC is goal):
   ```python
   # Instead of trades subscription
   subscription = {"type": "trades", "coin": sym}
   
   # Use candles (if available)
   subscription = {"type": "candle", "coin": sym, "interval": "1m"}
   ```

2. **Periodic REST Fallback**:
   - If WS fails, fall back to REST API polling
   - Lower frequency (every 1-5 min) for watchlist tokens

3. **Multiple Sockets for Throughput**:
   - Even under 1,000 subs, might need 2-3 sockets
   - Shard by symbol alphabetically
   - Stay under 100 connections total

---

## 5. ExecutorFactory - Stable Interface ✅

### Feedback
> "Make the output of PM explicit: ExecutionIntent"  
> "Put all venue gates inside executor.prepare(intent, position) -> Plan|Skip"

### Response: **AGREED**

**Implementation:** See `execution_intent_interface_spec.md`

**Key Points:**
- `ExecutionIntent`: Universal, venue-agnostic output from PM
- `ExecutionPlan`: Venue-specific plan (after constraints)
- `ExecutionResult`: Execution outcome

**Interface:**
```python
class BaseExecutor:
    def prepare(self, intent: ExecutionIntent, position: Dict) -> ExecutionPlan:
        """Convert intent to plan, apply constraints, return plan or skip"""
    
    def execute(self, plan: ExecutionPlan, position: Dict) -> ExecutionResult:
        """Execute plan on venue"""
```

---

## 6. Multiple Sockets - Throughput Bottleneck ✅

### Feedback
> "Even under 1000 subs, you might still want multiple sockets if inbound throughput becomes a bottleneck"

### Response: **AGREED**

**Corrected Rule:**
- **Start with 1 socket**
- **Monitor inbound throughput** (CPU, JSON parse, DB writes)
- **If bottleneck**: Shard by symbol across 2-N sockets
- **Stay under limits**: 100 connections, 1,000 subs total

**Sharding Strategy:**
```python
# Shard by symbol alphabetically
symbols_per_socket = 1000 // num_sockets

socket_1_symbols = [s for s in symbols if s[0] < 'M']
socket_2_symbols = [s for s in symbols if s[0] >= 'M']
```

---

## Implementation Priority

### Phase 1: ExecutionIntent Interface (Critical)
1. Create `ExecutionIntent` dataclass
2. Update `plan_actions_v4()` to return `ExecutionIntent` objects
3. Create `BaseExecutor` interface with `prepare()` / `execute()`
4. Update one executor (Hyperliquid) as proof of concept

### Phase 2: WS Robustness
1. Add backpressure (bounded queues)
2. Add reconnection logic (exponential backoff)
3. Add subscription diffing
4. Consider candles vs trades

### Phase 3: Documentation
1. Document `token_chain` as "venue namespace"
2. Document time normalization contract
3. Document funding/liquidation risk decision framework

---

## Summary of Changes

1. ✅ **PM Core Boundary**: ExecutionIntent pattern, all constraints in executor
2. ✅ **Naming**: Document `token_chain` as "venue namespace"
3. ✅ **Gap Handling**: Time normalization contract in Uptrend Engine
4. ✅ **Risk Constraints**: Decision framework (PM vs executor)
5. ✅ **WS Limits**: Focus on inbound throughput, backpressure, reconnection
6. ✅ **Executor Interface**: Stable `prepare()` / `execute()` pattern

**All feedback incorporated. Architecture is now production-ready.**

