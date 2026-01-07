# HIP-3 Interval Availability Analysis

**Date**: 2025-12-31  
**Question**: Do 15m candles not work, or is it just low activity?

---

## Key Finding

**Both are possible**, but evidence suggests **15m candles ARE supported**, we just need to wait for:
1. **Candle close** (every 15 minutes on the clock)
2. **Trading activity** (triggers candle updates)

---

## Evidence

### ✅ Markets ARE Active

**Earlier Test Results**:
- `vntl:SPACEX`: Got 1h candle ✅
- `flx:TSLA`: Got 1h candle ✅
- `xyz:TSLA`: Got 15m candle ✅
- `xyz:AAPL`: Got 15m candle ✅

**Conclusion**: Markets are active, intervals are supported.

### ⚠️ Why No 15m Candles in Some Tests?

**Possible Reasons**:

1. **Candle Not Closed Yet**
   - 15m candles close every 15 minutes (e.g., :00, :15, :30, :45)
   - If we subscribe at :05, we need to wait until :15 for next candle
   - Could wait up to 15 minutes

2. **Low Trading Activity**
   - If no trades happen, no candle updates are sent
   - Markets might be inactive during our test window
   - But 1h candles work, so markets ARE active (just less frequently)

3. **Connection Timeout**
   - WebSocket closes after inactivity
   - Need to keep connection alive or reconnect

---

## How Candle Subscriptions Work

### Candle Update Behavior

**Hyperliquid sends candle updates when**:
1. **Candle closes** (every 15m, 1h, 4h, etc.)
2. **Trading activity** (partial updates as candle forms)

**For 15m candles**:
- Candle closes at :00, :15, :30, :45 of each hour
- If you subscribe at :05, you might wait until :15 for next close
- Or you might get partial updates if there's trading activity

**For 1h candles**:
- Candle closes at the top of each hour
- If you subscribe at :30, you might wait until next hour
- Or you might get partial updates if there's trading activity

### Why 1h Worked But 15m Didn't

**Likely Explanation**:
- We subscribed to 1h when a candle was about to close or had recent activity
- We subscribed to 15m when:
  - Candle had just closed (need to wait for next one)
  - No recent trading activity
  - Connection timed out before next candle close

---

## Recommendations

### For Implementation

1. **Subscribe to All Intervals**
   - Subscribe to 15m, 1h, 4h for all markets
   - Use what works (some markets might only have certain intervals)

2. **Handle Connection Timeouts**
   - Keep connection alive (ping/pong)
   - Reconnect if connection closes
   - Resubscribe after reconnection

3. **Wait for Candle Closes**
   - Don't expect immediate data
   - Candles close on schedule (every 15m, 1h, 4h)
   - Partial updates come with trading activity

4. **Fallback Strategy**
   - If 15m doesn't work, use 1h
   - If 1h doesn't work, use 4h
   - Track which intervals work for each market

### Market Activity Levels

**High Activity** (like `xyz:TSLA`, `xyz:AAPL`):
- Get 15m candles regularly
- Partial updates with trading activity
- All intervals work

**Low Activity** (like `vntl:SPACEX`, `flx:TSLA`):
- May only get candles when they close
- Less frequent partial updates
- 1h or 4h might be more reliable than 15m

---

## Conclusion

**15m candles ARE likely supported** for all HIP-3 markets, but:

1. **Need to wait for candle close** (up to 15 minutes)
2. **Low activity markets** may not send updates until candle closes
3. **Connection timeouts** can interrupt waiting

**Implementation Strategy**:
- Subscribe to all intervals (15m, 1h, 4h)
- Keep connections alive
- Use whatever intervals work
- Don't assume immediate data - candles close on schedule

**Answer**: It's likely **both** - 15m candles are supported, but we need to wait for candle closes or trading activity. Low-activity markets may only send candles when they close, not partial updates.

