# Hyperliquid WebSocket Implementation Review

**Date**: 2025-12-31  
**Status**: Critical Issues Found - Needs Fixes

---

## Critical Issues

### 1. ❌ Symbol Discovery - NOT Dynamic

**Current Implementation**:
- Uses `HL_CANDLE_SYMBOLS` env var (default: "BTC,ETH,SOL")
- Hardcoded list, not dynamic
- Does NOT automatically discover from positions table

**Problem**: When we create a new Hyperliquid position, the ingester won't subscribe to it automatically.

**Expected Behavior** (from design docs):
- Query `lowcap_positions` for `token_chain='hyperliquid'`
- Subscribe to all symbols from positions
- Update subscriptions dynamically when positions change

**Fix Needed**: Implement dynamic symbol discovery from positions table.

---

### 2. ❌ WebSocket NOT Tested

**Status**: We've created the ingester but haven't tested it with live WebSocket.

**What We Need to Test**:
- [ ] Connection establishment
- [ ] Subscription to multiple symbols
- [ ] Message reception
- [ ] Partial update filtering (timestamp change detection)
- [ ] Database writes
- [ ] Reconnection handling
- [ ] Subscription limits

---

### 3. ⚠️ Subscription Limits Unknown

**Questions**:
- How many subscriptions can one WebSocket handle?
- Is there a rate limit on subscriptions?
- What happens if we subscribe to 224 main DEX + ~36 HIP-3 stock_perps = 260 symbols?
- Each symbol × 3 timeframes = 780 subscriptions total

**From Design Docs**:
- Mentioned "up to 1,000 subscriptions" but not verified
- Need to test actual limits

---

### 4. ⚠️ Comparison with Existing Implementation

**Existing `hyperliquid_ws.py`** (Majors):
- Purpose: Regime data (BTC, ETH, BNB, SOL, HYPE)
- Subscribes to: `trades` (not candles)
- Writes to: `majors_trades_ticks`
- Fixed symbols: 5 symbols
- Pattern: Simple, fixed list

**New `hyperliquid_candle_ws.py`** (Trading):
- Purpose: Trading positions data
- Subscribes to: `candle` (not trades)
- Writes to: `hyperliquid_price_data_ohlc`
- Symbols: Should be dynamic (but currently hardcoded)
- Pattern: Should discover from positions table

**Key Differences**:
- ✅ Different subscription type (candles vs trades) - correct
- ✅ Different table - correct
- ❌ Should be dynamic but currently hardcoded - needs fix
- ✅ Similar reconnection pattern - good

---

## Implementation Gaps

### Missing Features

1. **Dynamic Symbol Discovery**
   ```python
   def _get_trading_symbols(self) -> List[str]:
       """Get all Hyperliquid tokens from positions table"""
       res = (
           self.sb.table("lowcap_positions")
           .select("token_contract")
           .eq("token_chain", "hyperliquid")
           .in_("book_id", ["perps", "stock_perps"])
           .in_("status", ["watchlist", "active", "dormant"])
           .execute()
       )
       return [row["token_contract"] for row in (res.data or [])]
   ```

2. **Subscription Diffing**
   - Track current subscriptions
   - Compare with desired (from positions)
   - Only subscribe/unsubscribe changes
   - Prevents unnecessary re-subscriptions

3. **Activity Gate**
   - Only persist candles for markets with activity
   - Check volume > 0 or trades > 0
   - Prevents database bloat

4. **Rate Limiting**
   - Batch subscriptions with delays
   - Respect server limits
   - Handle subscription errors gracefully

---

## Testing Plan

### Phase 1: Basic WebSocket Test
- [ ] Connect to WebSocket
- [ ] Subscribe to 1 symbol (BTC 15m)
- [ ] Receive messages
- [ ] Verify partial update filtering
- [ ] Write to database

### Phase 2: Multi-Symbol Test
- [ ] Subscribe to 10 symbols × 3 timeframes = 30 subscriptions
- [ ] Monitor message volume
- [ ] Verify all symbols receive data
- [ ] Check database writes

### Phase 3: Scale Test
- [ ] Subscribe to 50 symbols × 3 timeframes = 150 subscriptions
- [ ] Monitor performance
- [ ] Check for errors/limits
- [ ] Verify reconnection works

### Phase 4: Full Scale Test
- [ ] Subscribe to all 224 main DEX + 36 HIP-3 stock_perps = 260 symbols
- [ ] 260 × 3 timeframes = 780 subscriptions
- [ ] Monitor message volume (expected: ~3 messages/candle × 260 symbols = high volume)
- [ ] Verify system handles load

---

## Recommendations

### Immediate Fixes

1. **Add Dynamic Symbol Discovery**
   - Query positions table on startup
   - Refresh periodically (every 5-10 minutes)
   - Subscribe to all discovered symbols

2. **Add Subscription Diffing**
   - Track active subscriptions
   - Only subscribe/unsubscribe changes
   - Handle reconnections efficiently

3. **Test WebSocket Before Production**
   - Start with small scale (10 symbols)
   - Gradually increase
   - Monitor for limits/errors

4. **Add Activity Gate**
   - Only persist active markets
   - Prevents database bloat
   - Log skipped markets

### Before Production

- [ ] Test WebSocket with live connection
- [ ] Verify subscription limits
- [ ] Test reconnection handling
- [ ] Test with 100+ symbols
- [ ] Monitor message volume and performance
- [ ] Verify database writes are efficient

---

## Next Steps

1. **Fix Symbol Discovery** - Make it dynamic from positions table
2. **Test WebSocket** - Create test script to verify functionality
3. **Check Limits** - Test with increasing number of subscriptions
4. **Add Subscription Diffing** - Only subscribe/unsubscribe changes
5. **Add Activity Gate** - Filter inactive markets

