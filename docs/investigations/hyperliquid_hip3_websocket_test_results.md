# Hyperliquid HIP-3 WebSocket Test Results

**Date**: 2025-12-31  
**Status**: ✅ **HIP-3 Markets Work via WebSocket!**

---

## Executive Summary

✅ **HIP-3 markets ARE accessible via WebSocket**  
✅ **`{dex}:{coin}` format works**  
✅ **Same candle subscription format as main DEX**  
⚠️ **Some markets may need different intervals** (15m vs 1h)

---

## Test Results

### ✅ Working Markets

| Market | DEX | Interval | Status | Notes |
|--------|-----|----------|--------|-------|
| `xyz:TSLA` | XYZ | 15m | ✅ | Tesla - got candle data |
| `xyz:AAPL` | XYZ | 15m | ✅ | Apple - got candle data |
| `vntl:SPACEX` | Ventuals | 1h | ✅ | SpaceX - works with 1h (no 15m data) |
| `flx:TSLA` | Felix | 1h | ✅ | Tesla - works with 1h (no 15m data) |

### Key Findings

1. **Subscription Format Works**: `{dex}:{coin}` format is correct
   ```json
   {
     "method": "subscribe",
     "subscription": {
       "type": "candle",
       "coin": "xyz:TSLA",
       "interval": "15m"
     }
   }
   ```

2. **Same Message Format**: HIP-3 candles use same structure as main DEX
   ```json
   {
     "channel": "candle",
     "data": {
       "t": 1767188700000,
       "T": 1767189599999,
       "s": "xyz:TSLA",
       "i": "15m",
       "o": "457.49",
       "c": "457.38",
       "h": "457.78",
       "l": "457.38",
       "v": "9.217",
       "n": 26
     }
   }
   ```

3. **Interval Availability**: Some markets may not have all intervals
   - `xyz:TSLA`: Has 15m candles ✅
   - `vntl:SPACEX`: No 15m candles, but has 1h candles ✅
   - `flx:TSLA`: No 15m candles, but has 1h candles ✅

4. **Subscription Response**: All subscriptions get confirmation
   ```json
   {
     "channel": "subscriptionResponse",
     "data": {
       "method": "subscribe",
       "subscription": {
         "type": "candle",
         "interval": "15m",
         "coin": "xyz:TSLA"
       }
     }
   }
   ```

---

## Implementation Notes

### Subscription Strategy

**For Active Markets** (like `xyz:TSLA`, `xyz:AAPL`):
- Subscribe to 15m, 1h, 4h intervals
- Should get data for all intervals

**For Less Active Markets** (like `vntl:SPACEX`, `flx:TSLA`):
- May only have 1h or 4h candles
- Try multiple intervals, use what works
- Fallback: If 15m fails, try 1h, then 4h

### Error Handling

**"Already subscribed" Error**:
- If you try to subscribe twice, you get:
  ```json
  {
    "channel": "error",
    "data": "Already subscribed: {...}"
  }
  ```
- Solution: Track active subscriptions, don't resubscribe

**No Messages**:
- Possible reasons:
  - Market inactive (no recent trades)
  - Interval not available (try different interval)
  - Market delisted
- Solution: Try different intervals, wait longer, check market status

---

## Recommendations

### ✅ Use HIP-3 Markets

**For Implementation**:
1. **Discover all DEXs**: Query `type="perpDexs"`
2. **Get markets per DEX**: Query `type="meta", dex="<name>"`
3. **Subscribe to all**: Use `{dex}:{coin}` format
4. **Handle intervals**: Try 15m, 1h, 4h, use what works
5. **Filter complete candles**: Same timestamp-based filtering as main DEX

### Market Selection

**Active Markets** (recommended):
- `xyz:*` markets (XYZ DEX) - Most active, has 15m candles
- Major stocks: `xyz:TSLA`, `xyz:AAPL`, `xyz:MSFT`, etc.

**Less Active Markets** (use 1h/4h):
- `vntl:SPACEX` - SpaceX (1h candles)
- `flx:TSLA` - Tesla on Felix (1h candles)

---

## Conclusion

✅ **HIP-3 markets ARE accessible via WebSocket**

- Same API/WebSocket infrastructure
- Same candle format
- Just use `{dex}:{coin}` format
- Some markets may need different intervals

**Ready to implement!**

