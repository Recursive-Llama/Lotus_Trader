# Hyperliquid Price Data Collection - Review & Gaps

**Date**: 2025-12-31  
**Status**: Review Complete - Ready for Implementation  
**Purpose**: Identify gaps and risks before integration

---

## What We've Tested ✅

### 1. WebSocket Candle Subscriptions ✅
- **Status**: All intervals tested and working
- **Intervals**: `1m`, `5m`, `15m`, `1h`, `4h`, `1d` all supported
- **Format**: `{"method": "subscribe", "subscription": {"type": "candle", "coin": "BTC", "interval": "15m"}}`
- **Message Format**: `{"channel": "candle", "data": {"t": <ts>, "s": "BTC", "i": "15m", "o": <open>, "h": <high>, "l": <low>, "c": <close>, "v": <volume>, "n": <trades>}}`
- **HIP-3 Support**: Works with `{dex}:{coin}` format (e.g., `"xyz:TSLA"`)

### 2. Historical Backfill ✅
- **Status**: `candleSnapshot` verified working
- **Format**: `{"type": "candleSnapshot", "req": {"coin": "BTC", "interval": "15m", "startTime": <ms>, "endTime": <ms>}}`
- **Works For**: Main DEX (BTC, ETH, etc.) and HIP-3 (`xyz:TSLA`, etc.)
- **Limits**: ~5000 candles max, timestamps in epoch milliseconds

### 3. Partial Updates ✅
- **Finding**: Hyperliquid sends multiple messages per candle with same timestamp
- **Strategy**: Timestamp change detection (when `t` changes, previous candle is complete)
- **Impact**: Need buffering logic to extract complete candles

---

## Integration Points

### Existing Infrastructure

**Current Pattern** (from `hyperliquid_ws.py`):
- `HyperliquidWSIngester` for majors (BTC, ETH, BNB, SOL, HYPE)
- Ingests **trades** (not candles)
- Writes to `majors_trades_ticks` table
- Different purpose (regime data, not trading data)

**What We Need**:
- `HyperliquidCandleWSIngester` for **trading tokens**
- Ingests **candles** (not trades)
- Writes to `hyperliquid_price_data_ohlc` table
- Used by TA Tracker, Geometry Builder, Uptrend Engine

### Table Schema

**Proposed**: `hyperliquid_price_data_ohlc`
```sql
CREATE TABLE hyperliquid_price_data_ohlc (
    token TEXT NOT NULL,           -- "BTC" or "xyz:TSLA"
    timeframe TEXT NOT NULL,       -- "15m", "1h", "4h"
    ts TIMESTAMPTZ NOT NULL,       -- Start of candle (from "t")
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume FLOAT NOT NULL,
    trades INTEGER,                 -- From "n" field
    CONSTRAINT unique_token_timeframe_ts UNIQUE (token, timeframe, ts)
);
```

**Alignment Check**:
- ✅ Matches `lowcap_price_data_ohlc` schema pattern
- ✅ `PriceDataReader` will route by `(chain="hyperliquid", book_id="perps"|"stock_perps")`
- ✅ TA Tracker, Geometry Builder, Uptrend Engine use `PriceDataReader` (no changes needed)

---

## Gaps & Risks

### 1. ⚠️ Partial Update Filtering - Not Tested in Production

**Risk**: Filtering logic needs real-world validation

**What We Know**:
- Multiple messages per candle with same timestamp
- Strategy: Buffer by timestamp, write when timestamp changes

**What We Need to Test**:
- [ ] Filtering logic with real WS stream (not just test script)
- [ ] Edge cases: rapid timestamp changes, missing messages
- [ ] Performance: buffer size, memory usage with many symbols

**Mitigation**:
- Implement timestamp change detection
- Add logging to track filtering behavior
- Monitor for duplicate candles or missing candles

---

### 2. ⚠️ HIP-3 Market Discovery & Subscription Management

**Risk**: HIP-3 markets may change, subscriptions need dynamic management

**What We Know**:
- 6 HIP-3 DEXs discovered: `xyz`, `flx`, `vntl`, `hyna`, `km`
- HIP-3 format: `{dex}:{coin}` (e.g., `xyz:TSLA`)
- Need to query `perpDexs` and `meta(dex=...)` on startup

**What We Need to Test**:
- [ ] Market discovery on startup (query all DEXs)
- [ ] Subscription diffing (only subscribe/unsubscribe changes)
- [ ] Reconnection handling (resubscribe to all on reconnect)
- [ ] New market detection (periodic refresh)

**Mitigation**:
- Implement `HyperliquidTokenDiscovery` class
- Cache market list, refresh periodically (daily/weekly)
- Track active subscriptions, diff on changes

---

### 3. ⚠️ Message Volume & Backpressure

**Risk**: High message volume could overwhelm system

**What We Know**:
- 1m candles: ~3 messages per candle (partial updates)
- For 100 symbols: ~300 messages/minute for 1m
- For 15m/1h/4h: Much lower volume

**What We Need to Test**:
- [ ] Message volume with 100+ symbols
- [ ] Backpressure handling (bounded queues)
- [ ] Database write performance (batch writes)
- [ ] Memory usage with buffering

**Mitigation**:
- Bounded queues per symbol (max 100 messages)
- Batch writes (flush every N messages or every T seconds)
- Drop oldest messages if queue full (with logging)

---

### 4. ⚠️ Activity Gate - Not Tested

**Risk**: Persisting all markets could bloat database with illiquid markets

**What We Know**:
- Some markets may have no trades for hours/days
- Activity gate: Only persist if `volume > 0` OR `trade_count > 0` for last K completed bars

**What We Need to Test**:
- [ ] Activity gate logic (volume/trade_count thresholds)
- [ ] Illiquid market behavior (no trades for hours)
- [ ] Database bloat prevention

**Mitigation**:
- Implement activity gate: `volume > 0` OR `trades > 0` for last K bars
- Log skipped markets for monitoring
- Consider TTL for inactive markets

---

### 5. ⚠️ Backfill Strategy - Not Fully Tested

**Risk**: Backfill timing and completeness

**What We Know**:
- `candleSnapshot` works for main DEX and HIP-3
- Format verified, timestamps in epoch milliseconds
- Max ~5000 candles

**What We Need to Test**:
- [ ] Backfill on position creation (trigger timing)
- [ ] Backfill completeness (no gaps)
- [ ] Backfill stitching with live WS data (no duplicates)
- [ ] Time range calculation (how many days to backfill?)

**Mitigation**:
- Backfill on position creation (triggered by executor or scheduler)
- Backfill 90 days (or configurable)
- Use `startTime`/`endTime` to control range
- Deduplicate on `(token, timeframe, ts)` when writing

---

### 6. ⚠️ Reconnection & Subscription Diffing - Not Tested

**Risk**: Reconnections could lose subscriptions or create duplicates

**What We Know**:
- Existing `HyperliquidWSIngester` has reconnection logic (exponential backoff)
- Need to resubscribe on reconnect

**What We Need to Test**:
- [ ] Reconnection handling (exponential backoff)
- [ ] Resubscription on reconnect (all markets)
- [ ] Subscription diffing (only subscribe/unsubscribe changes)
- [ ] Duplicate prevention (don't subscribe twice)

**Mitigation**:
- Track active subscriptions in memory
- On reconnect: Resubscribe to all tracked markets
- On market discovery: Only subscribe to new markets
- Log subscription changes for monitoring

---

### 7. ⚠️ Timezone & Timestamp Handling

**Risk**: Timestamp mismatches could cause data issues

**What We Know**:
- Hyperliquid timestamps: epoch milliseconds
- Candle `t` field: Start of candle (UTC)
- Need to convert to `TIMESTAMPTZ` for database

**What We Need to Test**:
- [ ] Timestamp conversion (epoch ms → TIMESTAMPTZ)
- [ ] Timezone handling (all UTC)
- [ ] Candle alignment (15m candles at :00, :15, :30, :45)

**Mitigation**:
- Convert `t` (epoch ms) to `datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)`
- Store as `TIMESTAMPTZ` in database
- Verify candle alignment matches expected intervals

---

## Implementation Checklist

### Phase 1: Core Ingester
- [ ] Create `HyperliquidCandleWSIngester` class
- [ ] Implement WebSocket connection (reuse existing pattern)
- [ ] Implement candle subscription (`type: "candle"`)
- [ ] Implement partial update filtering (timestamp change detection)
- [ ] Implement database writes (`hyperliquid_price_data_ohlc`)

### Phase 2: Market Discovery
- [ ] Create `HyperliquidTokenDiscovery` class
- [ ] Query `perpDexs` (all HIP-3 DEXs)
- [ ] Query `meta(dex=...)` for each DEX
- [ ] Cache market list (main DEX + HIP-3)
- [ ] Refresh periodically (daily/weekly)

### Phase 3: Subscription Management
- [ ] Subscribe to all markets on startup
- [ ] Track active subscriptions
- [ ] Implement reconnection handling (resubscribe)
- [ ] Implement subscription diffing (only changes)

### Phase 4: Backfill
- [ ] Create `backfill_from_hyperliquid()` function
- [ ] Implement `candleSnapshot` API calls
- [ ] Transform candles to database schema
- [ ] Deduplicate on `(token, timeframe, ts)`
- [ ] Trigger on position creation

### Phase 5: Activity Gate
- [ ] Implement activity gate logic
- [ ] Track volume/trade_count for last K bars
- [ ] Skip persistence for inactive markets
- [ ] Log skipped markets

### Phase 6: Testing
- [ ] Test with 10-20 symbols (small scale)
- [ ] Test partial update filtering (real WS stream)
- [ ] Test reconnection handling
- [ ] Test backfill completeness
- [ ] Test activity gate
- [ ] Scale to 100+ symbols

---

## Key Risks Summary

| Risk | Severity | Mitigation |
|------|----------|------------|
| Partial update filtering | Medium | Timestamp change detection, test with real stream |
| HIP-3 market discovery | Low | Query on startup, refresh periodically |
| Message volume | Medium | Bounded queues, batch writes |
| Activity gate | Low | Volume/trade_count thresholds |
| Backfill strategy | Medium | Test completeness, deduplication |
| Reconnection handling | Medium | Resubscribe on reconnect, track subscriptions |
| Timestamp handling | Low | Convert epoch ms to TIMESTAMPTZ, verify alignment |

---

## Conclusion

✅ **Data collection is well-tested and ready for implementation**

**What's Solid**:
- WebSocket candle subscriptions work
- Historical backfill (`candleSnapshot`) works
- Partial update strategy defined
- Table schema aligned with existing patterns

**What Needs Testing**:
- Partial update filtering (real WS stream)
- Reconnection & subscription management
- Backfill completeness & stitching
- Activity gate logic

**Recommendation**: Implement core ingester, test with small symbol set (10-20), then scale up.

