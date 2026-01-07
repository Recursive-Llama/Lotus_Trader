# Hyperliquid Integration - Feedback Corrections

**Date**: 2025-12-31  
**Source**: External feedback on implementation checklist  
**Status**: Critical corrections before implementation

---

## Critical Corrections

### 0. ✅ Hyperliquid DOES Have Historical Candles

**Correction**: Hyperliquid supports historical OHLC via `candleSnapshot` endpoint

**Previous Assumption** (WRONG):
> ❌ No historical data API — HL only provides real-time WebSocket

**Correct Approach**:
- ✅ Use Hyperliquid `candleSnapshot` for backfill (primary source)
- ✅ Matches actual venue feed (more accurate)
- ✅ Fallback to Binance only if HL doesn't have the asset

**Benefits**:
- No need to build/maintain 224-symbol Binance mapping table
- More accurate (same venue as trading)
- Simpler implementation

**Implementation**:
```python
# Hyperliquid candleSnapshot endpoint
POST https://api.hyperliquid.xyz/info
{
    "type": "candleSnapshot",
    "coin": "BTC",  # or "xyz:TSLA" for HIP-3
    "interval": "15m",  # or "1h", "4h"
    "n": 100  # number of candles (up to ~5000)
}
```

**Note**: Need to test correct format (may need `req` wrapper or different structure)

---

### 1. Market Selection - Activity Gate

**Correction**: Add activity gate for persistence

**Current Plan**: Subscribe to all markets, persist all bars

**Better Approach**:
- ✅ Subscribe to all markets (within limits)
- ✅ Only persist bars for markets with activity (N candles in last X hours)
- Prevents bloat from illiquid/no-trade markets

**Implementation**:
```python
class HyperliquidCandleWSIngester:
    def _should_persist(self, coin: str, candle_count_last_hour: int) -> bool:
        """Only persist if market has activity"""
        MIN_CANDLES_PER_HOUR = 2  # At least 2 candles per hour
        return candle_count_last_hour >= MIN_CANDLES_PER_HOUR
```

---

### 2. WebSocket - Use Candle Streams, Not Trades

**Correction**: Use `candle` subscription type, not `trades`

**Previous Plan**: Use trades, aggregate to candles

**Correct Approach**:
- ✅ Subscribe to `candle` streams directly
- ✅ Much lower message volume
- ✅ Pre-aggregated OHLC data

**WebSocket Subscription**:
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

**Benefits**:
- Lower message volume (already tested - ~20 messages/min total)
- No aggregation needed
- Direct OHLC data

---

### 3. HIP-3 Asset ID - Stable Mapping Cache

**Correction**: Cache dex/index mappings in DB

**Current Plan**: Compute asset ID on-the-fly

**Better Approach**:
- ✅ Cache `perpDexs` list (dex ordering/index)
- ✅ Cache `meta(dex=...)` universe (coin index per dex)
- ✅ Store in DB for stable lookup
- ✅ Executor uses cached mappings

**Implementation**:
```python
# On startup/discovery:
dex_mappings = {
    "main": {"index": 0, "universe": [...]},
    "xyz": {"index": 1, "universe": [...]},
    "flx": {"index": 2, "universe": [...]},
    # ...
}

# Store in DB or memory cache
# Executor uses cached mappings to compute asset IDs
```

---

### 4. Stock Detection - Classify at Discovery Time

**Correction**: Don't use string matching, classify at discovery

**Previous Approach** (WRONG):
```python
is_stock = ":" in token_contract and any(
    stock_ticker in token_contract.upper() 
    for stock_ticker in ["TSLA", "AAPL", ...]
)
```

**Problems**:
- Will miss most tickers
- Will misclassify
- Fragile

**Correct Approach**:
- ✅ Classify markets at discovery time
- ✅ Store `market_kind` or set `book_id` based on known HIP-3 DEXs
- ✅ Regime logic: `if book_id == 'stocks': return neutral A/E`

**Implementation**:
```python
# At discovery time:
HIP3_STOCK_DEXS = ["xyz", "flx", "vntl"]  # Known stock DEXs

for dex in hip3_dexs:
    if dex["name"] in HIP3_STOCK_DEXS:
        # All markets from these DEXs are stocks
        for market in dex_markets:
            market["book_id"] = "stocks"
            market["market_kind"] = "hip3_stock"
    else:
        # Skip (we're not using HIP-3 crypto)
        continue
```

---

### 5. Market Hours Gate - Two Gates

**Correction**: Two separate gates (scheduler + executor)

**Gate A: Scheduler / Tick Eligibility**
- Only run PM when there's a **new bar** for that `(chain, book_id, symbol, timeframe)`
- Equities: Bars won't advance outside sessions (natural gate)
- Crypto/perps: Bars always advance (24/7)

**Gate B: Executor `prepare()` → `Skip`**
- Safety net: Even if tick ran, execution can be blocked
- Handles: market closed, reduce-only, min size, margin caps, venue maintenance
- **Don't remove Skip** - it's future-proofing

**Implementation**:
```python
# Gate A: Scheduler
def should_run_pm_tick(chain: str, book_id: str, symbol: str, timeframe: str) -> bool:
    """Check if new bar available"""
    latest_bar = get_latest_bar(chain, book_id, symbol, timeframe)
    last_processed = get_last_processed_bar(position_id)
    return latest_bar["ts"] > last_processed["ts"]

# Gate B: Executor
def prepare(intent: ExecutionIntent, position: Dict) -> ExecutionPlan | SkipReason:
    if market_closed():
        return SkipReason("market_closed")
    if min_notional_not_met():
        return SkipReason("min_notional")
    # ...
    return ExecutionPlan(...)
```

---

### 6. Gaps / Time Normalization - Equities Trade 24/7

**Correction**: Equities on Hyperliquid trade 24/7, no gaps to worry about yet

**Previous Plan**: Handle gaps, session boundaries, etc.

**Current Reality**:
- ✅ Equities on Hyperliquid trade 24/7 (perpetual futures)
- ✅ No market hours gaps
- ✅ No session boundaries
- ⚠️ Future: If we add traditional equities (NYSE, NASDAQ), then handle gaps

**Implementation**:
- For now: No gap handling needed
- Future: Add gap detection when we add traditional equities
- Keep gap handling code structure for future use

---

## Updated Implementation Plan

### Historical Backfill (Corrected)

**Primary**: Hyperliquid `candleSnapshot`
```python
def backfill_from_hyperliquid(
    coin: str,  # "BTC" or "xyz:TSLA"
    interval: str,  # "15m", "1h", "4h"
    n: int = 5000,  # max candles
) -> List[Dict[str, Any]]:
    """Backfill from Hyperliquid candleSnapshot"""
    response = requests.post(
        "https://api.hyperliquid.xyz/info",
        json={
            "type": "candleSnapshot",
            "coin": coin,
            "interval": interval,
            "n": n,
        }
    )
    return response.json()  # List of candles
```

**Fallback**: Binance (only if HL doesn't have asset)

---

### WebSocket Ingestion (Corrected)

**Use Candle Streams**:
```python
subscription = {
    "method": "subscribe",
    "subscription": {
        "type": "candle",  # NOT "trades"
        "coin": "BTC",
        "interval": "15m"
    }
}
```

**Activity Gate**:
- Track candle count per market per hour
- Only persist if `candle_count >= MIN_CANDLES_PER_HOUR`

---

### Stock Classification (Corrected)

**At Discovery Time**:
```python
# Known stock DEXs
HIP3_STOCK_DEXS = ["xyz", "flx", "vntl"]

for dex in hip3_dexs:
    if dex["name"] in HIP3_STOCK_DEXS:
        # All markets are stocks
        for market in dex_markets:
            market["book_id"] = "stocks"
```

**In Regime Calculator**:
```python
if book_id == "stocks":
    return (0.5, 0.5)  # Neutral A/E
else:
    # Crypto regime
    ...
```

---

## Checklist Updates Needed

1. ✅ **Historical Data**: Use Hyperliquid `candleSnapshot` (primary), Binance (fallback)
2. ✅ **WebSocket**: Use `candle` subscription type, not `trades`
3. ✅ **Activity Gate**: Only persist bars for active markets
4. ✅ **Stock Classification**: Classify at discovery time, not string matching
5. ✅ **HIP-3 Asset ID**: Cache dex/index mappings
6. ✅ **Market Hours**: Two gates (scheduler + executor)
7. ✅ **Gaps**: Not needed yet (equities trade 24/7)

---

## Next Steps

1. **Test `candleSnapshot` endpoint**: Verify correct format and response
2. **Update checklist**: Apply all corrections
3. **Implement discovery**: Classify stocks at discovery time
4. **Implement backfill**: Use Hyperliquid `candleSnapshot`
5. **Implement WS**: Use `candle` subscriptions with activity gate

