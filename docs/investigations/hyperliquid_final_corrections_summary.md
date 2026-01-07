# Hyperliquid Integration - Final Corrections Summary

**Date**: 2025-12-31  
**Status**: All Critical Corrections Applied

---

## Critical Corrections Applied

### ✅ 0. Hyperliquid Historical Candles - VERIFIED

**Correction**: Hyperliquid DOES have historical candles via `candleSnapshot`

**Status**: ✅ **VERIFIED WORKING**

**Correct Format**:
```json
{
  "type": "candleSnapshot",
  "req": {
    "coin": "BTC",  // or "xyz:TSLA" for HIP-3
    "interval": "15m",
    "startTime": 1766587690943,  // epoch milliseconds
    "endTime": 1767192490943     // epoch milliseconds
  }
}
```

**Key Requirements**:
- ✅ Must include `req` wrapper
- ✅ Timestamps in epoch milliseconds
- ✅ For HIP-3: Use `coin: "xyz:TSLA"` format directly

**Test Results**:
- ✅ Main DEX (BTC, ETH): Working
- ✅ HIP-3 Stocks (xyz:TSLA): Working
- ✅ Returns up to ~5000 candles

**Action**: Use Hyperliquid `candleSnapshot` as primary backfill source

---

### ✅ 1. Market Selection - Activity Gate

**Correction**: Add activity gate for persistence

**Implementation**:
- Subscribe to all markets (within limits)
- Only persist bars for markets with activity (N candles in last X hours)
- Prevents bloat from illiquid markets

**Code**:
```python
def _should_persist(self, coin: str, candle_count_last_hour: int) -> bool:
    MIN_CANDLES_PER_HOUR = 2
    return candle_count_last_hour >= MIN_CANDLES_PER_HOUR
```

---

### ✅ 2. WebSocket - Use Candle Streams

**Correction**: Use `candle` subscription type, NOT `trades`

**Implementation**:
```json
{
    "method": "subscribe",
    "subscription": {
        "type": "candle",  // NOT "trades"
        "coin": "BTC",
        "interval": "15m"
    }
}
```

**Benefits**: Much lower message volume, pre-aggregated OHLC

---

### ✅ 3. HIP-3 Asset ID - Stable Cache

**Correction**: Cache dex/index mappings in DB

**Implementation**:
- Cache `perpDexs` list (dex ordering)
- Cache `meta(dex=...)` universe (coin index)
- Store in DB for stable lookup
- Executor uses cached mappings

---

### ✅ 4. Stock Classification - At Discovery Time

**Correction**: Classify at discovery, NOT string matching

**Implementation**:
```python
HIP3_STOCK_DEXS = ["xyz", "flx", "vntl"]

for dex in hip3_dexs:
    if dex["name"] in HIP3_STOCK_DEXS:
        for market in dex_markets:
            market["book_id"] = "stocks"
```

**Regime Logic**:
```python
if book_id == "stocks":
    return (0.5, 0.5)  # Neutral A/E
```

---

### ✅ 5. Market Hours - Two Gates

**Correction**: Two separate gates

**Gate A: Scheduler** - Check for new bar before running PM tick
**Gate B: Executor** - `prepare()` returns Skip if execution not feasible

**Note**: Equities on Hyperliquid trade 24/7 (perpetual futures), so no gaps yet

---

### ✅ 6. Gaps - Not Needed Yet

**Correction**: Equities trade 24/7 on Hyperliquid

**Status**: No gap handling needed for now
- Equities are perpetual futures (24/7 trading)
- No market hours gaps
- No session boundaries
- Future: Add gap handling when we add traditional equities (NYSE, NASDAQ)

---

## Updated Implementation Plan

### Historical Backfill

**Primary**: Hyperliquid `candleSnapshot` (need to verify format)
**Fallback**: Binance (if `candleSnapshot` doesn't work)

### WebSocket

**Type**: `candle` subscriptions (NOT `trades`)
**Activity Gate**: Only persist bars for active markets

### Stock Classification

**Method**: Classify at discovery time
**Storage**: `book_id='stocks'` for HIP-3 equities

### Two Gates

**Gate A**: Scheduler checks for new bar
**Gate B**: Executor `prepare()` returns Skip

---

## Open Questions

1. ✅ **candleSnapshot Format**: **VERIFIED** - Correct format confirmed and tested

---

## Next Steps

1. ✅ **candleSnapshot verified**: Format confirmed, tested, working
2. ✅ **Update checklist**: All corrections applied ✅
3. ⏭️ **Start implementation**: Begin with data infrastructure

