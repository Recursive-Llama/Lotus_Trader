# Hyperliquid Integration - Pre-Implementation Checklist

**Date**: 2025-12-31  
**Status**: Pre-Implementation Review  
**Goal**: Cover all bases before starting implementation

---

## Questions to Answer

### 1. Market Selection Strategy

**Q: Should we do all markets from the start?**

**Current Findings**:
- **Main DEX**: 224 crypto tokens
- **HIP-3 DEXs**: ~58 total markets discovered
  - xyz: 29 markets (stocks)
  - flx: 9 markets (stocks)
  - vntl: 6 markets (stocks)
  - hyna: 8 markets (crypto - skip, main DEX has all crypto)
  - km: 6 markets (indices/bonds - skip for now)
- **Subscribed Markets**: ~260 markets (224 crypto + ~36 stocks from xyz/flx/vntl)
- **Subscriptions needed**: ~780 (3 timeframes × 260)
- **Max allowed**: 1000 subscriptions
- **Within limits**: ✅

**Recommendation**: 
- ✅ **Start with all markets** - Within subscription limits, low message volume
- ✅ **Activity Gate**: Only persist bars for markets with actual activity
  - Persist only if `volume > 0` OR `trade_count > 0` for last K completed bars
  - Prevents bloat from dead/illiquid markets
  - Gate in writer, not subscriber

**HIP-3 Overlap Check**:
- ✅ **No overlap** - HIP-3 markets use `{dex}:{coin}` format (e.g., `xyz:TSLA`)
- Main DEX uses just coin name (e.g., `BTC`)
- Different formats = no conflicts

---

### 2. Regime Drivers for Stocks

**Q: Stocks shouldn't be affected by crypto regime stuff, right?**

**Current Regime System**:
- Regime drivers: BTC, ALT, nano, small, mid, big, BTC.d, USDT.d
- All are **crypto-specific** (Bitcoin, altcoins, market cap buckets, dominance)
- Used for A/E calculation: `RegimeAECalculator.compute_ae_for_token()`

**For Stocks/Equities**:
- ❌ **Should NOT use crypto regime drivers**
- Stocks have different drivers: SPX, sector indices, VIX, etc.
- Or: No regime drivers at all (neutral A/E)

**Implementation Options**:

**Option A: No Regime for Stocks** (Simplest)
- Stocks get neutral A/E (0.5, 0.5) or base A/E only
- No regime deltas applied
- PM still works (uses A/E for sizing, but no regime influence)

**Option B: Separate Stock Regime System** (Future)
- Create stock regime drivers (SPX, sector indices, etc.)
- Separate regime calculator for stocks
- More complex, but more accurate

**Recommendation**: **Option A** - Start with no regime for stocks
- PM logic still works (A/E can be neutral)
- Can add stock regime later if needed
- Simpler implementation

**Code Changes Needed**:
- `RegimeAECalculator.compute_ae_for_token()` should check `book_id` or position type
- If `book_id='stocks'` or position is equity (HIP-3 stock), return neutral A/E
- Or: Skip regime calculation entirely for non-crypto positions

**Current Flow** (from `pm_core_tick.py`):
```python
# Line ~3461: compute_ae_v2() is called
a_base, e_base, ae_diag = compute_ae_v2(regime_flags, token_bucket)

# compute_ae_v2() calls RegimeAECalculator.compute_ae_for_token()
# Which uses token_bucket to determine bucket driver
```

**For Stocks**:
- `token_bucket` would be None or not applicable
- `RegimeAECalculator.compute_ae_for_token()` should check if position is stock
- Return neutral A/E (0.5, 0.5) or base A/E only

---

### 3. Historical Data / Backfilling

**Q: How do we get historical data? Hyperliquid doesn't provide historical, right?**

**Correction**: ✅ **Hyperliquid DOES have historical candles** via `candleSnapshot` endpoint

**Current Approach (Binance)**:
- `regime_price_collector.py` has `backfill_majors_from_binance()`
- Backfills up to 666 bars per timeframe
- Uses Binance REST API (free, no auth)
- Called on bootstrap/startup

**For Hyperliquid**:
- ✅ **Use Hyperliquid `candleSnapshot`** (primary source) - **VERIFIED WORKING**
  - Endpoint: `POST https://api.hyperliquid.xyz/info`
  - Format: `{"type": "candleSnapshot", "req": {"coin": "BTC", "interval": "15m", "startTime": <epoch_millis>, "endTime": <epoch_millis>}}`
  - Returns up to ~5000 candles
  - Matches actual venue feed (more accurate)
  - Works for both main DEX (`"coin": "BTC"`) and HIP-3 (`"coin": "xyz:TSLA"`)
- ✅ **Fallback to Binance** only if HL doesn't have the asset

**Benefits**:
- No need to build/maintain 224-symbol Binance mapping table
- More accurate (same venue as trading)
- Simpler implementation
- Works for all markets (main DEX + HIP-3)

**Implementation Strategy**:

**For All Hyperliquid Markets (Main DEX + HIP-3)**:
- ✅ **Primary**: Use Hyperliquid `candleSnapshot` for backfill
  - Works for all markets (main DEX crypto + HIP-3 stock_perps)
  - No symbol mapping needed
  - More accurate (same venue as trading)
  - Backfill on position creation or bootstrap
- ✅ **Fallback**: Binance only if HL doesn't have asset (rare)
  - Only needed if asset not available on Hyperliquid
  - Optional cross-venue reference

**Note**: HIP-3 "stocks" are actually **stock perpetual futures** (synthetic equities), not real equities. They trade 24/7 on Hyperliquid, so we can backfill them via `candleSnapshot` just like crypto.

**Code Pattern** (VERIFIED - Hyperliquid candleSnapshot):
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
                "startTime": start_time,  # epoch milliseconds
                "endTime": end_time,      # epoch milliseconds
            }
        }
    )
    
    if response.status_code == 200:
        candles = response.json()  # List of candles
        # Candle structure: {"t": <start_ts>, "T": <end_ts>, "s": <symbol>, 
        #                    "i": <interval>, "o": <open>, "c": <close>, 
        #                    "h": <high>, "l": <low>, "v": <volume>, "n": <trades>}
        # Write to hyperliquid_price_data_ohlc
        return candles
    else:
        logger.error(f"candleSnapshot failed: {response.status_code} - {response.text}")
        return []

# Note: To get max ~5000 candles, calculate time window based on interval:
# - 15m: ~52 days (5000 * 15min = 75,000min = 52 days)
# - 1h: ~208 days (5000 hours)
# - 4h: ~833 days (5000 * 4h)
```

**Fallback Pattern** (Binance - only if HL doesn't have asset):
```python
def backfill_from_binance_fallback(
    symbol: str,  # Only if asset not on Hyperliquid
    timeframes: List[str] = ["15m", "1h", "4h"],
) -> Dict[str, Any]:
    """Fallback to Binance only if HL doesn't have asset (rare)"""
    # Similar to regime_price_collector.backfill_majors_from_binance()
    # Only used if candleSnapshot fails or asset not found
```

---

### 4. Data Architecture

**Q: Table structure - unified or separate?**

**Current State**:
- `lowcap_price_data_ohlc` - Solana tokens
- `majors_price_data_ohlc` - Hyperliquid majors (for market understanding)
- `regime_price_data_ohlc` - Regime drivers

**For Hyperliquid Trading**:
- **Option A**: Unified table `price_data_ohlc(chain, book_id, ...)`
- **Option B**: Separate table `hyperliquid_price_data_ohlc`

**Recommendation**: **Option B** (Separate table)
- Matches current pattern (separate tables per source)
- Easier to manage TTL/retention per asset class
- Clear separation of concerns
- `PriceDataReader` routes by `(chain, book_id)` anyway

**Schema**:
```sql
CREATE TABLE hyperliquid_price_data_ohlc (
    token TEXT NOT NULL,  -- "BTC" or "xyz:TSLA"
    timeframe TEXT NOT NULL,  -- "15m", "1h", "4h"
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

---

### 5. Token Discovery & Management

**Q: How do we discover and manage tokens dynamically?**

**Current Approach** (Solana):
- Tokens come from social signals (Twitter/Telegram)
- Positions created on-demand
- Backfill triggered on position creation

**For Hyperliquid**:
- **Main DEX**: Query `type="meta"` on startup → 224 crypto tokens
- **HIP-3 DEXs**: Query `type="perpDexs"` → then `type="meta", dex="<name>"` for each
- **Total Discovered**: ~282 markets (all HIP-3 DEXs)
- **Total Subscribed**: ~260 markets (224 crypto + ~36 stocks from xyz/flx/vntl)
  - Skip HIP-3 crypto (hyna, etc.) - main DEX has all crypto
  - Skip other HIP-3 markets (km indices/bonds) - for now

**Discovery Strategy**:
1. **Startup**: Query all DEXs, get all markets
2. **Classification**: Classify at discovery time
   - Main DEX: `book_id='perps'`
   - HIP-3 stock DEXs (xyz, flx, vntl): `book_id='stock_perps'`
   - HIP-3 crypto: Skip (main DEX has all crypto)
3. **Periodic Refresh**: Re-query daily/weekly to discover new markets
4. **Subscription Management**: Subscribe to subscribed markets for 15m, 1h, 4h
5. **Position Creation**: Same as Solana (on-demand from signals or manual)

**Implementation**:
- Create `HyperliquidTokenDiscovery` class
- Query on startup, store in memory/DB
- Refresh periodically
- Use for subscription management

---

### 6. Regime Driver Selection

**Q: How do we determine which regime driver to use?**

**Current Logic**:
- `RegimeAECalculator.compute_ae_for_token()` takes `token_bucket` parameter
- Maps bucket to regime driver: `BUCKET_DRIVERS = {"nano": "nano", "small": "small", ...}`
- Uses bucket driver states for A/E calculation

**For Hyperliquid**:
- **Crypto (Main DEX)**: Use same logic (bucket-based regime)
- **HIP-3 Stocks**: No regime (neutral A/E)

**Code Changes**:
```python
def compute_ae_for_token(
    self,
    token_bucket: Optional[str] = None,
    exec_timeframe: str = "1h",
    book_id: Optional[str] = None,  # Check book_id
    ...
) -> Tuple[float, float]:
    # Check book_id (classified at discovery time)
    if book_id == 'stock_perps':
        return (0.5, 0.5)  # Neutral A/E for stock perpetuals
    
    # Otherwise, use crypto regime logic
    ...
```

**Note**: Classification happens at discovery time, not via string matching. No ticker substring detection needed.

---

### 7. Position Schema

**Q: How do we identify Hyperliquid positions?**

**Schema**:
- `token_chain = "hyperliquid"` (venue namespace)
- `book_id = "perps"` (for main DEX crypto)
- `book_id = "stock_perps"` (for HIP-3 stock perpetuals - synthetic equities)
- `token_contract = "BTC"` or `"xyz:TSLA"` (ticker or dex:coin)

**Recommendation**: **Use book_id to differentiate**
- **Main DEX Crypto**: `token_chain='hyperliquid'`, `book_id='perps'`, `token_contract='BTC'`
- **HIP-3 Stock Perps**: `token_chain='hyperliquid'`, `book_id='stock_perps'`, `token_contract='xyz:TSLA'`
- **HIP-3 Crypto**: Don't use (main DEX has all crypto)

**Note**: HIP-3 "stocks" are actually **stock perpetual futures** (synthetic equities), not real equities. They trade 24/7 on Hyperliquid, so we use `book_id='stock_perps'` to distinguish from real equities (future: `book_id='stocks'` for NYSE/NASDAQ).

**Implementation**:
- Check `book_id` in regime calculator
- If `book_id='stock_perps'` → return neutral A/E (0.5, 0.5)
- If `book_id='perps'` → use crypto regime

---

### 8. WebSocket Subscription Management

**Q: How do we manage subscriptions dynamically?**

**Requirements**:
- Subscribe to all markets on startup
- Handle reconnections
- Subscription diffing (only subscribe/unsubscribe changes)
- Backpressure (bounded queues)

**Implementation**:
- `HyperliquidCandleWSIngester` class
- Query all markets on startup
- Subscribe to all for 15m, 1h, 4h
- Track active subscriptions
- On reconnection: Resubscribe to all
- On new market discovery: Subscribe to new markets

---

### 9. Historical Data Backfill Strategy

**Q: When and how do we backfill?**

**Current Pattern** (from `regime_price_collector.py`):
- Backfill on bootstrap/startup
- Backfill up to 666 bars per timeframe
- Use Binance REST API

**For Hyperliquid**:

**For All Hyperliquid Markets**:
- ✅ **Primary**: Use Hyperliquid `candleSnapshot` for backfill
  - Works for all markets (main DEX crypto + HIP-3 stock_perps)
  - No symbol mapping needed
  - More accurate (same venue as trading)
  - Backfill on position creation or bootstrap
- ✅ **Fallback**: Binance only if HL doesn't have asset (rare)
  - Only needed if asset not available on Hyperliquid
  - Optional cross-venue reference

**Note**: HIP-3 "stocks" are actually **stock perpetual futures** (synthetic equities), not real equities. They trade 24/7 on Hyperliquid, so we can backfill them via `candleSnapshot` just like crypto.

**Code Pattern** (CORRECT - verified format):
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
                "startTime": start_time,  # epoch milliseconds
                "endTime": end_time,      # epoch milliseconds
            }
        }
    )
    
    if response.status_code == 200:
        candles = response.json()  # List of candles
        return candles
    else:
        logger.error(f"candleSnapshot failed: {response.status_code}")
        return []
```

---

### 10. Scheduler Gate Implementation

**Q: How do we check "new bar available" for tick eligibility?**

**Current**: PM Core Tick runs on schedule (every 15m, 1h, 4h)

**Two Gates Design**:

**Gate A: Scheduler / Tick Eligibility** (Simplified)
- **Simpler approach**: PM runs on schedule (every 15m/1h/4h)
- If candles arrive on schedule, PM naturally sees new data when it runs
- **No cursor table needed** - PM is idempotent, can run multiple times safely
- If duplicate processing becomes an issue later, add lightweight check (compare latest bar timestamp to last run time)
- Equities: Bars won't advance outside sessions (natural gate)
- Crypto/perps: Bars always advance (24/7)
- **Note**: Stock perpetuals on Hyperliquid trade 24/7 (perpetual futures), so no gaps yet

**Gate B: Executor `prepare()` → `Skip`**
- Safety net: Even if tick ran, execution can be blocked
- Handles: market closed, reduce-only, min size, margin caps, venue maintenance
- **Don't remove Skip** - it's future-proofing

**Implementation**:
```python
# Gate A: Scheduler (Simplified - just run on schedule)
# PM runs every 15m/1h/4h based on timeframe
# If candles arrive on schedule, PM naturally sees new data
# No cursor table needed - PM is idempotent

# Gate B: Executor
def prepare(intent, position) -> ExecutionPlan | SkipReason:
    if market_closed():
        return SkipReason("market_closed")
    # ...
```

---

## Implementation Checklist

### Phase 1: Data Infrastructure ✅
- [ ] Create `hyperliquid_price_data_ohlc` table
- [ ] Create `price_table_helper.py` (simple helper function)
- [ ] Update TA Tracker to use `get_price_table_name()` helper
- [ ] Update Geometry Builder to use `get_price_table_name()` helper
- [ ] Update Uptrend Engine to use `get_price_table_name()` helper
- [ ] Update PM Core Tick price lookups to use `get_price_table_name()` helper

### Phase 2: Token Discovery ✅
- [ ] Create `HyperliquidTokenDiscovery` class
- [ ] Query main DEX: All 224 crypto tokens (`book_id='perps'`)
- [ ] Query HIP-3 DEXs: Only stocks (filter out crypto)
- [ ] **Classify at discovery**: Set `book_id='stock_perps'` for known stock DEXs (xyz, flx, vntl)
  - These are stock perpetual futures (synthetic equities), not real equities
  - No string matching - classification happens at discovery time
- [ ] Store token list with `book_id` and `market_kind`
- [ ] Cache HIP-3 dex/index mappings for asset ID computation
- [ ] Periodic refresh mechanism

### Phase 3: WebSocket Ingestion ✅
- [ ] Create `HyperliquidCandleWSIngester`
- [ ] Subscribe to `candle` streams (NOT `trades`) for all markets (15m, 1h, 4h)
- [ ] Filter complete candles (timestamp change detection)
- [ ] **Activity Gate**: Only persist bars for markets with actual activity
  - Persist only if `volume > 0` OR `trade_count > 0` for last K completed bars
  - Prevents bloat from dead/illiquid markets
- [ ] Write to `hyperliquid_price_data_ohlc`
- [ ] Backpressure handling
- [ ] Reconnection logic
- [ ] Subscription diffing

### Phase 4: Historical Backfill ✅
- [x] Test Hyperliquid `candleSnapshot` endpoint - **VERIFIED WORKING**
- [ ] Create `backfill_from_hyperliquid()` using `candleSnapshot`
  - Use correct format: `{"type": "candleSnapshot", "req": {...}}`
  - Timestamps in epoch milliseconds
  - Works for main DEX (`"coin": "BTC"`) and HIP-3 (`"coin": "xyz:TSLA"`)
- [ ] Backfill on position creation (all markets - main DEX crypto + HIP-3 stock_perps)
- [ ] Fallback to Binance only if HL doesn't have asset (rare, optional)
- [ ] No symbol mapping needed (use same symbols as HL)

### Phase 5: Regime Logic ✅
- [ ] Update `RegimeAECalculator` or `compute_ae_v2()` to check `book_id`
- [ ] Return neutral A/E (0.5, 0.5) for `book_id='stock_perps'`
- [ ] Use crypto regime for crypto markets (`book_id='perps'`)
- [ ] **Remove any ticker substring detection** - rely only on `book_id`
- [ ] **Note**: PM strength still works for stock_perps (applied later)

### Phase 6: Executor ✅
- [ ] Create `HyperliquidExecutor`
- [ ] Implement `prepare()` (constraints, asset ID computation, Skip reasons)
- [ ] Implement `execute()` (Hyperliquid API calls)
- [ ] Handle HIP-3 asset IDs (formula: `100000 + dex_index * 10000 + coin_index`)
- [ ] Use cached dex/index mappings (from discovery phase)

### Phase 7: PM Integration ✅
- [ ] Update PM Core Tick to use `ExecutorFactory`
- [ ] Route by `(token_chain, book_id)`
- [ ] **Gate A**: Optional - Check for new bar before running PM tick (scheduler gate)
  - **Simpler approach**: PM runs on schedule, naturally sees new data when candles arrive
  - If needed later: Compare latest bar timestamp to last run time (in-memory or lightweight cache)
  - **Skip cursor table for now** - add only if duplicate processing becomes an issue
- [ ] **Gate B**: Executor `prepare()` returns Skip if execution not feasible
- [ ] Test end-to-end

---

## Key Decisions Summary

1. ✅ **All Markets**: Start with all ~260 markets (224 crypto + ~36 stock_perps, within limits)
2. ✅ **HIP-3 Crypto**: Skip (main DEX has all crypto)
3. ✅ **HIP-3 Stock Perps**: Only from known DEXs (xyz, flx, vntl) - `book_id='stock_perps'`
4. ✅ **Stock Perps = No Regime**: Return neutral A/E for `book_id='stock_perps'` (PM strength still works)
5. ✅ **Historical Data**: Hyperliquid `candleSnapshot` (primary), Binance (fallback only)
6. ✅ **Separate Table**: `hyperliquid_price_data_ohlc` (matches current pattern)
7. ✅ **Token Discovery**: Query all DEXs, classify at discovery time (no string matching)
8. ✅ **WebSocket**: Use `candle` subscriptions (NOT `trades`), activity gate (volume/trades > 0)
9. ✅ **Timeframes**: 15m, 1h, 4h only (user preference)
10. ✅ **Two Gates**: Scheduler (new bar check per symbol/timeframe) + Executor (Skip reasons)
11. ✅ **Gaps**: Not needed yet (stock_perps trade 24/7 on Hyperliquid)

---

## Open Questions - RESOLVED

1. ✅ **Book ID for HIP-3 Stock Perps**: Use `book_id='stock_perps'` (differentiate from crypto and real equities)

2. ✅ **Historical Data**: Hyperliquid `candleSnapshot` (primary), Binance (fallback only)

3. ✅ **HIP-3 Crypto**: Don't use (main DEX has all crypto)

4. ✅ **PM Strength for Stock Perps**: Still works (separate from regime)

5. ⚠️ **Message Burst**: Accept initially, monitor, add batching if needed

6. ✅ **Binance Symbol Mapping**: Not needed (use HL `candleSnapshot` as primary)

---

## Next Steps

1. ✅ **Review Checklist**: All considerations covered
2. ⏭️ **Finalize Decisions**: Book ID, regime logic, backfill strategy
3. ⏭️ **Start Implementation**: Begin with data infrastructure