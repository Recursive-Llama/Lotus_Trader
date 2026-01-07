# Hyperliquid Checklist - Final Fixes Applied

**Date**: 2025-12-31  
**Status**: All Critical Fixes Applied

---

## Fixes Applied

### ✅ 1. Backfill Strategy - HL Primary, Binance Fallback Only

**Before**: Contradictory - said HL primary but still recommended Binance for crypto

**After**: 
- ✅ **Primary**: Hyperliquid `candleSnapshot` for ALL markets (main DEX + HIP-3)
- ✅ **Fallback**: Binance only if HL doesn't have asset (rare, optional)
- ✅ **No symbol mapping needed** - use same symbols as HL

---

### ✅ 2. Code Pattern Bug - Fixed candleSnapshot Format

**Before**: Incorrect format with `n=5000`
```python
json={"type": "candleSnapshot", "coin": coin, "interval": interval, "n": n}
```

**After**: Correct format with `req` wrapper and `startTime/endTime`
```python
json={
    "type": "candleSnapshot",
    "req": {
        "coin": coin,
        "interval": interval,
        "startTime": start_time,  # epoch milliseconds
        "endTime": end_time,      # epoch milliseconds
    }
}
```

---

### ✅ 3. Stock Classification - Renamed to `stock_perps`

**Before**: Confusing - called them "stocks" but they're perpetual futures

**After**:
- ✅ Renamed to `book_id='stock_perps'` (synthetic equities, perpetual futures)
- ✅ Clarified: These are NOT real equities (NYSE/NASDAQ)
- ✅ Real equities (future): Will use `book_id='stocks'`
- ✅ Can backfill stock_perps via `candleSnapshot` (they trade 24/7)

---

### ✅ 4. Market Counts - Clarified Discovered vs Subscribed

**Before**: Counts drifting (282 → 260 → 224+36)

**After**:
- ✅ **Total Discovered**: ~282 markets (all HIP-3 DEXs)
- ✅ **Total Subscribed**: ~260 markets (224 crypto + ~36 stock_perps)
  - Skip HIP-3 crypto (main DEX has all crypto)
  - Skip other HIP-3 markets (km indices/bonds) - for now

---

### ✅ 5. Activity Gate - Use Volume/Trades, Not Candle Count

**Before**: "N candles in last X hours"

**After**:
- ✅ Persist only if `volume > 0` OR `trade_count > 0` for last K completed bars
- ✅ Prevents bloat from dead/illiquid markets
- ✅ Based on actual activity, not just bar presence

---

### ✅ 6. Gate A - Per Symbol/Timeframe, Not Per Position

**Before**: Used `position_id` for last processed tracking

**After**:
- ✅ Store last processed timestamp per `(chain, book_id, symbol, timeframe)`
- ✅ Use tick cursor table: `hyperliquid_tick_cursors`
- ✅ Generic tracking independent of position table
- ✅ Works for multiple positions per symbol

**Table Schema**:
```sql
CREATE TABLE hyperliquid_tick_cursors (
    token_chain TEXT NOT NULL,
    book_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    last_processed_ts TIMESTAMPTZ NOT NULL,
    CONSTRAINT unique_chain_book_symbol_tf UNIQUE (token_chain, book_id, symbol, timeframe)
);
```

---

### ✅ 7. Stock Detection - Remove String Matching

**Before**: Had ticker substring detection as fallback
```python
is_stock = ":" in token_contract and any(
    stock_ticker in token_contract.upper() 
    for stock_ticker in ["TSLA", "AAPL", ...]
)
```

**After**:
- ✅ **Only use `book_id`** - classified at discovery time
- ✅ No string matching - removed all ticker substring detection
- ✅ Clean and robust

---

## Summary

All critical fixes applied:
1. ✅ HL primary, Binance fallback only
2. ✅ Correct candleSnapshot format
3. ✅ Renamed to `stock_perps` (clarified vs real equities)
4. ✅ Clarified market counts (discovered vs subscribed)
5. ✅ Activity gate uses volume/trades
6. ✅ Gate A per symbol/timeframe (tick cursor table)
7. ✅ Removed string matching (use book_id only)

**Checklist is now locked and ready for implementation.**

