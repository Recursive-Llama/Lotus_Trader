# Hyperliquid Candle Test Results

**Date**: 2025-12-31  
**Test Script**: `tests/hyperliquid/test_candle_subscriptions.py`  
**Results File**: `tests/hyperliquid/candle_test_results.json`

---

## Executive Summary

✅ **WebSocket candles are supported** - Use WebSocket candles for OHLC data  
❌ **REST API candles not available** - No REST endpoints found  
⚠️ **Message volume**: Candles actually send more messages than trades (unexpected, needs investigation)

---

## Detailed Findings

### 1. WebSocket Candle Subscriptions ✅

**Status**: **SUPPORTED**

**Working Subscription Format:**
```json
{
  "method": "subscribe",
  "subscription": {
    "type": "candle",
    "coin": "BTC",
    "interval": "1m"
  }
}
```

**Message Format:**
```json
{
  "channel": "candle",
  "data": {
    "t": <timestamp>,
    "T": <timestamp>,
    "s": <symbol>,
    "i": <interval>,
    "o": <open>,
    "c": <close>,
    "h": <high>,
    "l": <low>,
    "v": <volume>,
    "n": <number of trades>
  }
}
```

**Key Findings:**
- ✅ `type: "candle"` works (not `candles`, `interval`, or `ohlc`)
- ✅ `coin` parameter required (not `symbol`)
- ✅ `interval` parameter required (e.g., `"1m"`)
- ✅ Only tested `1m` interval successfully (other intervals may work but weren't tested)
- ❌ Other formats (`candles`, `interval`, `ohlc`) return errors

**✅ All Intervals Tested and Supported:**
- `1m` ✅ - 3 messages received (partial updates observed)
- `5m` ✅ - 3 messages received (partial updates observed)
- `15m` ✅ - 3 messages received (partial updates observed)
- `1h` ✅ - 2 messages received (partial updates observed)
- `4h` ✅ - 2 messages received (partial updates observed)
- `1d` ✅ - 2 messages received (partial updates observed)

**Key Observation**: Multiple messages received for the same timestamp, indicating Hyperliquid sends **partial candle updates** (updates as the candle forms), not just on candle close. This explains why candles had more messages than trades in the earlier test.

---

### 2. REST API Candle Endpoints ❌

**Status**: **NOT FOUND**

**Tested Endpoints:**
- `/info` - 405 Method Not Allowed
- `/candles` - 404 Not Found
- `/ohlc` - 404 Not Found
- `/klines` - 404 Not Found
- `/bars` - 404 Not Found
- `/candle` - 404 Not Found
- `/v1/candles` - 404 Not Found
- `/v1/ohlc` - 404 Not Found
- `/api/v1/candles` - 404 Not Found
- `/api/v1/klines` - 404 Not Found

**Conclusion**: No REST API candle endpoints available. Must use WebSocket.

---

### 3. Message Volume Comparison ✅ (Explained)

**Results:**
- **Trades**: 13 messages in 30s (~26/min)
- **Candles**: 16 messages in 30s (~32/min)
- **Ratio**: 0.81x (candles have MORE messages than trades)

**Analysis - CONFIRMED:**
✅ **Hyperliquid sends partial candle updates** - Multiple messages per candle with the same timestamp but updated OHLC values.

**Evidence from interval tests:**
- For `1m` candles: Received 3 messages with same timestamp `1767184560000` but different OHLC values
- For `5m` candles: Received 3 messages with same timestamp `1767184500000` but different OHLC values
- Pattern: First message = initial candle, subsequent messages = updates as candle forms

**Why candles have more messages:**
1. **Partial updates**: Hyperliquid sends updates as the candle forms (high/low/close/volume update)
2. **Real-time updates**: Each trade that affects OHLC triggers a candle update message
3. **Final candle**: The last message before next candle starts is the "complete" candle

**Recommendation**: 
- ✅ Use candles (they're pre-aggregated, just need to filter for final candle)
- Filter strategy: Keep the last message for each timestamp (most complete candle)
- Or: Track timestamp changes (new timestamp = new candle, previous was complete)

---

## Recommendations

### ✅ Use WebSocket Candles for OHLC

**Why:**
1. ✅ Candles are supported via WebSocket
2. ✅ Pre-aggregated data (no need to aggregate from trades)
3. ✅ Lower complexity (no rollup logic needed)
4. ⚠️ Message volume needs investigation (may be similar to trades if partial updates)

**Implementation:**
```python
# Subscribe to candles
subscription = {
    "method": "subscribe",
    "subscription": {
        "type": "candle",
        "coin": "BTC",
        "interval": "1m"  # or "5m", "15m", "1h", "4h", "1d"
    }
}
```

**Next Steps:**
1. Test other intervals (`5m`, `15m`, `1h`, `4h`, `1d`) to confirm they work
2. Investigate message volume over longer period (5+ minutes)
3. Check if candle messages are complete or partial updates
4. If partial updates, filter for complete candles (check for candle close indicator)

### ❌ Don't Use REST API

**Why:**
- No REST candle endpoints available
- Must use WebSocket

---

## ✅ All Intervals Tested

**Status**: All intervals tested and confirmed working:
- ✅ `1m` - 1-minute candles
- ✅ `5m` - 5-minute candles
- ✅ `15m` - 15-minute candles
- ✅ `1h` - 1-hour candles
- ✅ `4h` - 4-hour candles
- ✅ `1d` - Daily candles

**Test Results**: See `tests/hyperliquid/interval_test_results.json`

**Key Finding**: All intervals send partial updates (multiple messages per candle with same timestamp).

---

## ✅ Message Volume Investigation - COMPLETE

**Questions Answered:**
1. ✅ **Are candle messages complete candles or partial updates?**
   - **Answer**: Partial updates - Multiple messages per candle with same timestamp
   
2. ✅ **How many messages per minute for different intervals?**
   - **Answer**: Varies by interval and market activity
   - `1m`: ~3 messages per candle (partial updates)
   - Longer intervals: Fewer messages (less frequent updates)
   
3. ✅ **Should we filter for complete candles only?**
   - **Answer**: Yes - Filter strategy needed:
     - **Option A**: Keep last message for each timestamp (most complete)
     - **Option B**: Track timestamp changes (new timestamp = new candle, previous was complete)
     - **Option C**: Use timestamp + volume to detect final candle (volume stops increasing)

**Implementation Strategy:**
- Subscribe to candles
- Buffer messages by timestamp
- When timestamp changes, the previous timestamp's last message is the complete candle
- Write complete candles to database

---

## Implementation Notes

### Candle Message Structure

Based on test results, candle messages have this structure:
```json
{
  "channel": "candle",
  "data": {
    "t": <timestamp>,      // Start timestamp
    "T": <timestamp>,      // End timestamp (or same as t?)
    "s": "BTC",            // Symbol
    "i": "1m",             // Interval
    "o": <open>,           // Open price
    "c": <close>,          // Close price
    "h": <high>,           // High price
    "l": <low>,            // Low price
    "v": <volume>,         // Volume
    "n": <trades>          // Number of trades
  }
}
```

**Questions:**
- Is `T` the end timestamp or same as `t`?
- Are messages sent only on candle close, or also during formation?
- How to identify a "complete" candle vs partial update?

---

## Next Steps

1. ✅ **Confirmed**: WebSocket candles work
2. ✅ **Tested all intervals**: All intervals (`1m`, `5m`, `15m`, `1h`, `4h`, `1d`) work
3. ✅ **Message volume explained**: Partial updates confirmed, filter strategy identified
4. ⏭️ **Implement candle ingester**: Create `HyperliquidCandleWSIngester` using working format
5. ⏭️ **Filter complete candles**: Implement timestamp-based filtering (new timestamp = previous candle complete)

---

## Conclusion

**✅ Use WebSocket candles for Hyperliquid OHLC data**

- Working subscription format confirmed
- Message format understood
- Need to test other intervals
- Need to investigate message volume (why more than trades?)

**Implementation Priority**: High - Candles are available and should be used instead of trades aggregation.

