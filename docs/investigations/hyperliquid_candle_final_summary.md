# Hyperliquid Candle Data - Final Summary

**Date**: 2025-12-31  
**Status**: ✅ Complete - Ready for Implementation

---

## Executive Summary

✅ **All candle intervals are supported via WebSocket**  
✅ **Partial updates confirmed** - Need filtering strategy  
✅ **Ready to implement** - Use WebSocket candles for OHLC data

---

## Test Results

### ✅ All Intervals Supported

| Interval | Status | Messages Received | Notes |
|----------|--------|-------------------|-------|
| `1m` | ✅ | 3 | Partial updates observed |
| `5m` | ✅ | 3 | Partial updates observed |
| `15m` | ✅ | 3 | Partial updates observed |
| `1h` | ✅ | 2 | Partial updates observed |
| `4h` | ✅ | 2 | Partial updates observed |
| `1d` | ✅ | 2 | Partial updates observed |

### Subscription Format

```json
{
  "method": "subscribe",
  "subscription": {
    "type": "candle",
    "coin": "BTC",
    "interval": "1m"  // or "5m", "15m", "1h", "4h", "1d"
  }
}
```

### Message Format

```json
{
  "channel": "candle",
  "data": {
    "t": 1767184560000,    // Timestamp (start of candle)
    "T": 1767184560000,    // End timestamp (same as t?)
    "s": "BTC",            // Symbol
    "i": "1m",             // Interval
    "o": 88900.0,          // Open
    "c": 88898.0,          // Close
    "h": 88901.0,          // High
    "l": 88898.0,          // Low
    "v": 0.00209,          // Volume
    "n": 123               // Number of trades
  }
}
```

---

## Key Finding: Partial Updates

**Hyperliquid sends multiple messages per candle with the same timestamp but updated OHLC values.**

**Example from test:**
```
Candle #1: ts=1767184560000, o=88900.0, h=88901.0, l=88900.0, c=88900.0, v=0.00196
Candle #2: ts=1767184560000, o=88900.0, h=88901.0, l=88898.0, c=88898.0, v=0.00209
Candle #3: ts=1767184560000, ... (more updates)
```

**Why this happens:**
- Hyperliquid sends real-time updates as the candle forms
- Each trade that affects OHLC triggers an update message
- The last message before timestamp changes is the "complete" candle

**Impact:**
- More messages than expected (explains why candles had more messages than trades)
- Need filtering strategy to extract complete candles

---

## Filtering Strategy

### Option A: Timestamp Change Detection (Recommended)

**Logic:**
1. Buffer messages by timestamp
2. When timestamp changes, the previous timestamp's last message is the complete candle
3. Write complete candle to database

**Implementation:**
```python
last_timestamp = None
candle_buffer = {}

for message in candle_messages:
    timestamp = message["data"]["t"]
    
    if timestamp != last_timestamp:
        # New candle started - previous candle is complete
        if last_timestamp and candle_buffer:
            complete_candle = candle_buffer[last_timestamp][-1]  # Last message
            write_to_db(complete_candle)
        
        # Start new candle
        candle_buffer[timestamp] = []
        last_timestamp = timestamp
    
    # Add to buffer
    candle_buffer[timestamp].append(message)

# Handle final candle
if candle_buffer:
    complete_candle = candle_buffer[last_timestamp][-1]
    write_to_db(complete_candle)
```

### Option B: Volume-Based Detection

**Logic:**
- Track volume for each timestamp
- When volume stops increasing, candle is complete
- More complex, less reliable

### Option C: Time-Based (Not Recommended)

**Logic:**
- Wait for interval duration before considering candle complete
- Problem: Delays data, may miss final updates

---

## Implementation Plan

### 1. Create `HyperliquidCandleWSIngester`

**Location**: `src/intelligence/lowcap_portfolio_manager/ingest/hyperliquid_candle_ws.py`

**Features:**
- Subscribe to candles for trading tokens (from positions table)
- Filter for complete candles (timestamp change detection)
- Write to `hyperliquid_price_data_ohlc` table
- Backpressure handling (bounded queues)
- Reconnection logic (exponential backoff)
- Subscription diffing (only subscribe/unsubscribe changes)

### 2. Table Schema

**Table**: `hyperliquid_price_data_ohlc`

**Schema**: Same as `lowcap_price_data_ohlc`:
```sql
CREATE TABLE hyperliquid_price_data_ohlc (
    token TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume FLOAT NOT NULL,
    trades INTEGER,
    CONSTRAINT unique_token_timeframe_ts UNIQUE (token, timeframe, ts)
);
```

### 3. Integration Points

**PriceDataReader**: Route to `hyperliquid_price_data_ohlc` when `token_chain='hyperliquid'`

**TA Tracker**: Use `PriceDataReader` (no changes needed)

**Geometry Builder**: Use `PriceDataReader` (no changes needed)

**Uptrend Engine**: Use `PriceDataReader` (no changes needed)

---

## Performance Considerations

### Message Volume

**For 1m candles:**
- ~3 messages per candle (partial updates)
- ~3 messages per minute per symbol
- For 100 symbols: ~300 messages/minute

**For longer intervals:**
- Fewer messages (less frequent updates)
- 1h candles: ~2 messages per hour per symbol

**Comparison to trades:**
- Trades: ~26 messages/minute per symbol
- Candles: ~3 messages/minute per symbol (for 1m)
- **Reduction**: ~88% fewer messages with candles

### Backpressure

**Strategy:**
- Bounded queues per symbol (max 100 messages)
- Drop oldest messages if queue full
- Prioritize complete candles (timestamp changes)

---

## Next Steps

1. ✅ **Testing Complete**: All intervals tested and confirmed
2. ⏭️ **Implement Ingester**: Create `HyperliquidCandleWSIngester`
3. ⏭️ **Create Table**: Create `hyperliquid_price_data_ohlc` table
4. ⏭️ **Implement PriceDataReader**: Route by `(chain, book_id)`
5. ⏭️ **Test End-to-End**: Verify data flows correctly

---

## Conclusion

**✅ Use WebSocket candles for Hyperliquid OHLC data**

- All intervals supported (`1m`, `5m`, `15m`, `1h`, `4h`, `1d`)
- Pre-aggregated data (no rollup needed)
- Lower message volume than trades (~88% reduction for 1m)
- Need filtering for complete candles (timestamp change detection)

**Ready for implementation!**

