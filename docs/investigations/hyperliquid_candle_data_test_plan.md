# Hyperliquid Candle Data Test Plan

**Date**: 2025-01-XX  
**Goal**: Determine if Hyperliquid provides candle/OHLC data via WebSocket or REST, or if we need to aggregate from trades

---

## Test Objectives

1. **Check WebSocket candle subscription availability**
   - Does Hyperliquid WS support candle/interval subscriptions?
   - What timeframes are available?
   - What's the message format?

2. **Check REST API candle endpoints**
   - Does Hyperliquid REST API provide OHLC/candle data?
   - What's the rate limit?
   - What timeframes are available?

3. **Compare approaches**
   - Trades aggregation (current approach)
   - WebSocket candles (if available)
   - REST API candles (if available)

---

## Test 1: WebSocket Candle Subscription

### Test Script

**Location**: `tests/hyperliquid/test_candle_subscriptions.py`

**Run**:
```bash
python tests/hyperliquid/test_candle_subscriptions.py
```

**What it tests**:
- Multiple subscription formats: `candle`, `candles`, `interval`, `ohlc`
- Multiple parameter names: `coin`, `symbol`, `interval`, `timeframe`
- Multiple intervals: `1m`, `5m`, `15m`, `1h`, `4h`, `1d`
- Message format detection
- Error handling

**Output**:
- Console: Real-time test results
- File: `tests/hyperliquid/candle_test_results.json` (detailed results)

### Expected Outcomes

**If candles work:**
- Receive candle messages with OHLC data
- Format: `{"channel": "candle", "data": {"coin": "BTC", "t": timestamp, "o": open, "h": high, "l": low, "c": close, "v": volume}}`

**If candles don't work:**
- Error message or no response
- Fall back to trades aggregation

---

## Test 2: REST API Candle Endpoints

### Test Script

**Location**: `tests/hyperliquid/test_candle_subscriptions.py` (included in main test)

**What it tests**:
- Multiple endpoint patterns: `/candles`, `/ohlc`, `/klines`, `/bars`, etc.
- Multiple parameter patterns: `symbol`, `coin`, `pair`, `market`
- Response format detection
- Rate limit testing (makes 10 rapid requests)

**Output**:
- Console: Endpoint test results
- File: `candle_test_results.json` (includes REST results)

### Expected Outcomes

**If REST candles exist:**
- Endpoint returns OHLC data
- Check rate limits (requests/min)
- Check available timeframes

**If REST candles don't exist:**
- 404 or error response
- Fall back to trades aggregation

---

## Test 3: Compare Approaches

### Approach A: Trades Aggregation (Current)

**Pros:**
- ✅ Always available (trades are always streamed)
- ✅ High resolution (every trade)
- ✅ Can compute any timeframe

**Cons:**
- ❌ High inbound message volume
- ❌ CPU/memory intensive (aggregation)
- ❌ More complex (need rollup logic)

### Approach B: WebSocket Candles (If Available)

**Pros:**
- ✅ Lower message volume (one per bar)
- ✅ Pre-aggregated (no computation needed)
- ✅ Simpler ingestion

**Cons:**
- ❌ Limited timeframes (if HL only supports certain intervals)
- ❌ Less flexible (can't compute custom timeframes)

### Approach C: REST API Candles (If Available)

**Pros:**
- ✅ Simple polling (no WebSocket complexity)
- ✅ Pre-aggregated
- ✅ Reliable (HTTP is simpler than WS)

**Cons:**
- ❌ Rate limits (need to check)
- ❌ Less real-time (polling delay)
- ❌ More API calls (one per symbol per poll)

---

## Test Plan

### Step 1: Run Comprehensive Test
```bash
python tests/hyperliquid/test_candle_subscriptions.py
```

**What it does**:
1. Tests WebSocket candle subscriptions (multiple formats, intervals)
2. Tests REST API candle endpoints (multiple patterns)
3. Compares message volume (trades vs candles)
4. Checks official documentation links
5. Saves detailed results to JSON

### Step 2: Review Results
1. Check `tests/hyperliquid/candle_test_results.json`
2. Review console output for summary
3. Check which subscription formats work (if any)
4. Check which REST endpoints work (if any)

### Step 3: Manual Documentation Check
1. Visit: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket
2. Look for candle/interval subscription types
3. Visit: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api
4. Look for candle/OHLC REST endpoints

### Step 4: Decision
Based on test results:

**If WebSocket candles work:**
- Use WebSocket candles for OHLC
- Lower message volume
- Real-time updates

**If REST candles work:**
- Use REST API polling for OHLC
- Simpler than WebSocket
- Check rate limits

**If neither works:**
- Use trades aggregation (current approach)
- Optimize aggregation (batch processing)
- Monitor inbound message volume

**Hybrid approach (if applicable):**
- Candles for active positions (real-time)
- REST polling for watchlist (lower frequency)

---

## Implementation Notes

### If Candles Available

**WebSocket Approach:**
```python
# Subscribe to candles
subscription = {
    "method": "subscribe",
    "subscription": {
        "type": "candle",
        "coin": "BTC",
        "interval": "1m"
    }
}
```

**REST Approach:**
```python
# Poll candles endpoint
def fetch_candles(symbol: str, interval: str, limit: int = 100):
    url = f"https://api.hyperliquid.xyz/candles"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    response = requests.get(url, params=params)
    return response.json()
```

### If Candles Not Available

**Stick with trades aggregation:**
- Current approach works
- Optimize aggregation (batch processing, efficient rollup)
- Monitor inbound message volume
- Use backpressure/bounded queues

---

## Success Criteria

**Test is successful if:**
1. ✅ We can subscribe to candles via WebSocket OR
2. ✅ We can fetch candles via REST API OR
3. ✅ We confirm candles don't exist and stick with trades

**Decision made:**
- Clear path forward (candles or trades)
- Performance characteristics understood
- Implementation approach chosen

---

## Next Steps

1. **Run tests** (WebSocket candles, REST API)
2. **Document findings** (what works, what doesn't)
3. **Make decision** (candles vs trades)
4. **Update design doc** with chosen approach

