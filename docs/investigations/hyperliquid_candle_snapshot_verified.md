# Hyperliquid candleSnapshot - Verified Working

**Date**: 2025-12-31  
**Status**: ✅ **VERIFIED - Format Confirmed**

---

## Correct API Format

**Endpoint**: `POST https://api.hyperliquid.xyz/info`

**Request Body**:
```json
{
  "type": "candleSnapshot",
  "req": {
    "coin": "BTC",
    "interval": "15m",
    "startTime": 1766587690943,
    "endTime": 1767192490943
  }
}
```

**Key Requirements**:
- ✅ `type` must be exactly `"candleSnapshot"` (case-sensitive)
- ✅ Must include `req` wrapper (not top-level fields)
- ✅ Keys: `coin`, `interval`, `startTime`, `endTime`
- ✅ Timestamps are **epoch milliseconds** (not seconds, not ISO strings)
- ✅ For HIP-3: Use `coin: "xyz:TSLA"` format directly (no separate `dex` field)

---

## Test Results

### ✅ Main DEX - BTC 15m
- **Status**: 200 OK
- **Candles**: 673 candles (7 days)
- **Structure**: `{"t": <start_ts>, "T": <end_ts>, "s": "BTC", "i": "15m", "o": <open>, "c": <close>, "h": <high>, "l": <low>, "v": <volume>, "n": <trades>}`

### ✅ Main DEX - ETH 1h
- **Status**: 200 OK
- **Candles**: 169 candles (7 days)
- **Structure**: Same as BTC

### ✅ HIP-3 Stock - xyz:TSLA 1h
- **Status**: 200 OK
- **Candles**: 169 candles (7 days)
- **Structure**: Same format, `"s": "xyz:TSLA"`

---

## Supported Intervals

From Hyperliquid docs:
- `"1m"`, `"3m"`, `"5m"`, `"15m"`, `"30m"`, `"1h"`, `"2h"`, `"4h"`, `"8h"`, `"12h"`, `"1d"`, `"3d"`, `"1w"`, `"1M"`

**For our use case**: `"15m"`, `"1h"`, `"4h"` ✅

---

## Candle Structure

```json
{
  "t": 1766587500000,      // Start timestamp (epoch milliseconds)
  "T": 1766588399999,      // End timestamp (epoch milliseconds)
  "s": "BTC",              // Symbol (or "xyz:TSLA" for HIP-3)
  "i": "15m",              // Interval
  "o": "86975.0",          // Open (string)
  "c": "86974.0",          // Close (string)
  "h": "87261.0",          // High (string)
  "l": "86746.0",          // Low (string)
  "v": "602.51908",        // Volume (string)
  "n": 7483                // Number of trades (integer)
}
```

---

## Implementation

### Backfill Function

```python
def backfill_from_hyperliquid(
    coin: str,  # "BTC" or "xyz:TSLA"
    interval: str,  # "15m", "1h", "4h"
    days: int = 90,  # Number of days to backfill
) -> List[Dict[str, Any]]:
    """Backfill from Hyperliquid candleSnapshot endpoint"""
    from datetime import datetime, timezone, timedelta
    
    # Calculate time range (epoch milliseconds)
    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_time = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    
    response = requests.post(
        "https://api.hyperliquid.xyz/info",
        json={
            "type": "candleSnapshot",
            "req": {
                "coin": coin,
                "interval": interval,
                "startTime": start_time,
                "endTime": end_time,
            }
        }
    )
    
    if response.status_code == 200:
        candles = response.json()
        # Transform and write to hyperliquid_price_data_ohlc
        return candles
    else:
        logger.error(f"candleSnapshot failed: {response.status_code}")
        return []
```

### Data Transformation

```python
def transform_candle(candle: Dict[str, Any]) -> Dict[str, Any]:
    """Transform Hyperliquid candle to our schema"""
    return {
        "token": candle["s"],  # "BTC" or "xyz:TSLA"
        "timeframe": candle["i"],  # "15m", "1h", "4h"
        "ts": datetime.fromtimestamp(candle["t"] / 1000, tz=timezone.utc),
        "open": float(candle["o"]),
        "high": float(candle["h"]),
        "low": float(candle["l"]),
        "close": float(candle["c"]),
        "volume": float(candle["v"]),
        "trades": candle["n"],
    }
```

---

## Limits

- **Max candles**: ~5000 (most recent)
- **Time range**: Use `startTime` and `endTime` to control range
- **Rate limits**: Unknown, but should be reasonable for backfill

---

## Benefits

1. ✅ **No symbol mapping needed** - Use same symbols as Hyperliquid
2. ✅ **Works for all markets** - Main DEX and HIP-3
3. ✅ **Accurate data** - Same venue as trading
4. ✅ **Simple implementation** - Single endpoint, clear format

---

## Conclusion

✅ **candleSnapshot is verified and working**

- Correct format confirmed
- Works for main DEX and HIP-3
- Ready for implementation

