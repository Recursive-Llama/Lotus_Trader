# PM Routing & Architecture Rethink

**Date**: 2025-01-XX  
**Status**: Design Phase

---

## Key Corrections & Insights

### 1. Testing = Production Approach ✅

**You're absolutely right** - if we're testing, we should test the production approach. No point in testing one thing and using another.

**Decision**: Pick ONE approach that works for both testing and production.

---

### 2. PM Logic Universality - Deep Dive

**Question**: Is PM logic truly universal, or does it need venue-specific adaptations?

**Current PM Logic Flow:**
```
1. Compute A/E scores (regime-based, universal)
2. Call plan_actions_v4() (signal-based, universal)
3. Execute decision (venue-specific)
```

**Where Venue-Specific Logic Might Be Needed:**

#### A. Market Hours / Trading Windows
- **Equities**: Market open/close, pre-market, after-hours
- **Crypto**: 24/7 (no restrictions)
- **Hyperliquid Perps**: 24/7 (no restrictions)

**Impact**: PM should check "can I trade right now?" before making decisions
- This is a **pre-decision gate**, not core PM logic
- Could be: `venue.can_trade_now()` check

#### B. Execution Constraints
- **Equities**: Order types, settlement (T+2), margin rules
- **Crypto Spot**: Immediate settlement, different slippage
- **Perps**: Leverage, funding rates, liquidation risk

**Impact**: This is **executor-level**, not PM-level
- PM decides "what to do" (add/trim/hold)
- Executor decides "how to do it" (order type, leverage, etc.)

#### C. Data Availability
- **Equities**: Gaps (overnight, weekends)
- **Crypto**: Continuous data
- **Perps**: Continuous data

**Impact**: This is **data layer**, not PM logic
- Uptrend Engine handles gaps (forward-fill, gap-aware ATR)
- PM just reads the data

#### D. Position Sizing Rules
- **Equities**: Fractional shares, round lots
- **Crypto**: Any amount
- **Perps**: Contract sizes, leverage limits

**Impact**: This is **executor-level** (sizing constraints)
- PM computes `size_frac` (universal)
- Executor applies venue-specific constraints

**Conclusion**: **PM Core Logic is Universal**
- A/E computation: Universal
- `plan_actions_v4()`: Universal (signal-based)
- Decision making: Universal

**What's Venue-Specific:**
- Pre-decision gates (market hours)
- Execution (executor)
- Data handling (data layer)

**Recommendation**: Keep PM logic universal, add venue-specific **gates** if needed

---

### 3. Book ID Correction

**Correction**: `book_id='perps'` (not 'spot')

**Architecture:**
- `book_id = 'perps'` (venue type: perpetual futures)
- `token_chain = 'hyperliquid'` (specific exchange)
- Future: `token_chain = 'binance'`, `token_chain = 'bybit'` (all with `book_id='perps'`)

**Schema:**
```sql
-- Example positions:
-- Solana on-chain token (current)
token_chain='solana', book_id='onchain_crypto'

-- Hyperliquid perp
token_chain='hyperliquid', book_id='perps'

-- Future Binance perp
token_chain='binance', book_id='perps'
```

**Learning System Scoping:**
- Scopes automatically separate by `(token_chain, book_id)`
- Same learning system, different scopes = perfect separation

---

### 4. Hyperliquid WebSocket Deep Dive

**Current Implementation Analysis:**

From `hyperliquid_ws.py`:
```python
async def _subscribe(self, ws: Any, symbols: List[str]) -> None:
    for idx, sym in enumerate(symbols):
        msg = {
            "method": "subscribe",
            "subscription": {"type": "trades", "coin": sym},
        }
        await ws.send(json.dumps(msg))
        logger.info("Subscribed to trades for %s", sym)
```

**Key Observations:**
1. **One WebSocket Connection**: Single connection, multiple subscriptions
2. **Sequential Subscriptions**: Subscribes to each symbol one by one
3. **No Limit Checks**: Code doesn't check subscription limits
4. **All Messages on Same Socket**: All tick data comes through one connection

**Hyperliquid Limits (from research):**
- **100 WebSocket connections per IP**
- **1,000 subscriptions per IP** (across all connections)
- **2,000 messages sent to Hyperliquid per minute** (across all connections)

**Implications:**
- ✅ **One socket can handle many tokens** (up to 1,000 subscriptions per IP)
- ✅ **We can subscribe to all trading tokens on one socket**
- ✅ **No need for multiple socket instances** (unless we need >1,000 tokens)
- ⚠️ **Message rate limit**: 2,000 messages/min = ~33 messages/second
  - Each subscription = 1 message
  - Subscribing to 100 tokens = 100 messages (well under limit)

**Recommendation:**
1. **Use ONE WebSocket connection** for all Hyperliquid trading tokens
2. **Subscribe to all tokens we're tracking** (from positions table)
3. **Monitor subscription count** (stay under 1,000)
4. **If we need >1,000 tokens**: Use REST API polling for additional tokens

**Implementation Approach:**
```python
class HyperliquidTradingWSIngester:
    def __init__(self):
        # Get tokens from positions table
        self.trading_symbols = self._get_trading_symbols()  # From lowcap_positions
    
    def _get_trading_symbols(self) -> List[str]:
        """Get all Hyperliquid tokens we're tracking from positions table"""
        res = (
            self.sb.table("lowcap_positions")
            .select("token_contract")
            .eq("token_chain", "hyperliquid")
            .eq("book_id", "perps")
            .in_("status", ["watchlist", "active", "dormant"])
            .execute()
        )
        return [row["token_contract"] for row in (res.data or [])]
    
    async def _subscribe(self, ws: Any, symbols: List[str]) -> None:
        """Subscribe to all trading symbols"""
        if len(symbols) > 1000:
            logger.warning(f"Too many symbols ({len(symbols)}), limiting to 1000")
            symbols = symbols[:1000]
        
        for sym in symbols:
            msg = {
                "method": "subscribe",
                "subscription": {"type": "trades", "coin": sym},
            }
            await ws.send(json.dumps(msg))
            logger.info("Subscribed to trades for %s", sym)
```

**Separate from Majors WS:**
- **Majors WS**: `hyperliquid_ws.py` → `majors_trades_ticks` → `majors_price_data_ohlc`
  - Purpose: Market understanding (BTC, ETH, SOL, HYPE, BNB)
  - Fixed symbols
  
- **Trading WS**: `hyperliquid_trading_ws.py` → `hyperliquid_trades_ticks` → `hyperliquid_price_data_ohlc`
  - Purpose: Trading tokens (dynamic, from positions table)
  - Dynamic symbols

---

## PM Routing - Final Recommendation

**After rethinking**: PM logic is universal, only execution differs.

**Best Approach: Executor Factory Pattern**

```python
class ExecutorFactory:
    """Routes to appropriate executor based on venue"""
    def __init__(self):
        self.executors = {
            ('solana', 'onchain_crypto'): PMExecutor(...),
            ('hyperliquid', 'perps'): HyperliquidExecutor(...),
            # Future:
            # ('binance', 'perps'): BinanceExecutor(...),
            # ('bybit', 'perps'): BybitExecutor(...),
        }
    
    def get_executor(self, token_chain: str, book_id: str):
        key = (token_chain.lower(), book_id.lower())
        executor = self.executors.get(key)
        if not executor:
            logger.warning(f"No executor for {key}")
        return executor

class PMCoreTick:
    def __init__(self, timeframe: str = "1h"):
        # ... existing init ...
        self.executor_factory = ExecutorFactory()
    
    def run(self):
        positions = self._active_positions()
        for position in positions:
            # ... existing A/E computation ...
            decision = plan_actions_v4(...)
            
            if decision['decision_type'] == 'hold':
                continue
            
            # Route to appropriate executor
            executor = self.executor_factory.get_executor(
                position['token_chain'],
                position['book_id']
            )
            
            if not executor:
                logger.warning(f"No executor for {position['token_chain']}/{position['book_id']}")
                continue
            
            # Execute (same interface for all executors)
            result = executor.execute(decision, position)
            
            # ... existing position update logic ...
```

**Why This Works:**
1. ✅ **PM logic stays universal** (no changes to A/E, plan_actions_v4)
2. ✅ **Execution is isolated** (executor factory handles routing)
3. ✅ **Easy to test** (mock executor factory)
4. ✅ **Easy to extend** (add new executor to factory)
5. ✅ **Same approach for testing and production**

**If We Need Venue-Specific PM Logic Later:**
- Add venue-specific **gates** before `plan_actions_v4()`:
  ```python
  # Check if venue allows trading right now
  if not self._can_trade_now(position):
      return [{"decision_type": "hold"}]
  
  # Universal PM logic
  decision = plan_actions_v4(...)
  ```

---

## Refactoring PM Core Tick

**Current Structure:**
- PM Core Tick does everything: fetch, compute A/E, plan actions, execute, update

**Proposed Structure (Minimal Changes):**
- Keep same structure
- Add executor factory
- Route execution only

**No Major Refactor Needed:**
- PM logic is already universal
- Just need executor routing
- Can add venue-specific gates later if needed

---

## Summary

### Architecture Decisions

1. **PM Logic**: Universal (A/E, plan_actions_v4 stay the same)
2. **Execution**: Venue-specific (executor factory routes)
3. **Book ID**: `'perps'` for Hyperliquid perps
4. **Token Chain**: `'hyperliquid'` (specific exchange)
5. **WebSocket**: One connection, many subscriptions (up to 1,000)
6. **Testing = Production**: Same approach for both

### Implementation Plan

1. **Create ExecutorFactory** (routing only)
2. **Update PM Core Tick** (add factory, route execution)
3. **Create HyperliquidExecutor** (test in dry-run)
4. **Create Hyperliquid Trading WS** (separate from majors)
5. **Test end-to-end** (same approach as production)

### Future Extensibility

- **Add venues**: Just add executor to factory
- **Add venue-specific gates**: Add `_can_trade_now()` check
- **Add more tokens**: Extend WS subscription (up to 1,000 limit)
- **Scale beyond 1,000**: Use REST API for additional tokens

---

## Next Steps

1. **Research**: Verify Hyperliquid WebSocket subscription limits
2. **Design**: Finalize ExecutorFactory interface
3. **Implement**: Create HyperliquidExecutor (dry-run mode)
4. **Test**: Verify executor routing works
5. **Integrate**: Add to PM Core Tick

