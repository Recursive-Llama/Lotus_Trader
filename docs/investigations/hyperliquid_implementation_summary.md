# Hyperliquid Integration - Implementation Summary

**Date**: 2025-12-31  
**Status**: Pre-Implementation - All Bases Covered

---

## Your Questions Answered

### 1. Should we do all markets from the start?

**Answer**: ✅ **Yes, start with all markets**

**Rationale**:
- **Total markets**: ~282 (224 main DEX + ~58 HIP-3)
- **Subscriptions needed**: ~846 (3 timeframes × 282)
- **Max allowed**: 1000 subscriptions
- **Utilization**: 84.6% (well within limits)
- **Message volume**: ~20 messages/minute total (very low)

**Benefits**:
- Simple implementation (no filtering logic)
- Can discover opportunities across all markets
- Can filter later if needed (volume, liquidity, activity)

---

### 2. Stocks shouldn't be affected by regime stuff, right?

**Answer**: ✅ **Correct - stocks should NOT use crypto regime**

**Current Regime System**:
- Regime drivers: BTC, ALT, nano, small, mid, big, BTC.d, USDT.d
- All are **crypto-specific**
- Used for A/E calculation in `RegimeAECalculator.compute_ae_for_token()`

**For Stocks**:
- ❌ **No crypto regime** - Stocks have different drivers (SPX, sectors, VIX, etc.)
- ✅ **Neutral A/E** - Return (0.5, 0.5) or base A/E only
- PM still works (uses A/E for sizing, but no regime influence)

**Implementation**:
```python
# In RegimeAECalculator.compute_ae_for_token()
# Check if position is stock (HIP-3 equity)
if position and ":" in position.get("token_contract", ""):
    token_contract = position["token_contract"]
    # Check if it's a stock ticker
    stock_tickers = ["TSLA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "SPACEX"]
    if any(ticker in token_contract.upper() for ticker in stock_tickers):
        return (0.5, 0.5)  # Neutral A/E for stocks

# Otherwise, use crypto regime logic
```

**Alternative**: Check `book_id` if we set it to `'stocks'` for HIP-3 equities

---

### 3. HIP-3 markets don't overlap with base Hyperliquid markets, right?

**Answer**: ✅ **Correct - No overlap**

**Format Difference**:
- **Main DEX**: `token_contract='BTC'` (just coin name)
- **HIP-3**: `token_contract='xyz:TSLA'` (dex:coin format)

**No Conflicts**:
- Different formats = no naming conflicts
- WebSocket subscriptions use different coin names
- Database can store both (different `token_contract` values)

**Example**:
- Main DEX: `BTC` (Bitcoin)
- HIP-3: `hyna:BTC` (Bitcoin on HyENA DEX)
- These are **different markets** (different order books, different prices potentially)

---

### 4. Historical data - Hyperliquid doesn't provide it, right?

**Answer**: ✅ **Correct - No historical data API**

**Current Approach** (from `regime_price_collector.py`):
- Uses Binance REST API for historical backfill
- Backfills up to 666 bars per timeframe
- Called on bootstrap/startup

**For Hyperliquid**:

**Crypto Markets (Main DEX + HIP-3 crypto)**:
- ✅ **Use Binance backfill** (same symbols: BTC, ETH, SOL, etc.)
- Map Hyperliquid symbol → Binance symbol (usually same)
- Backfill on position creation or bootstrap

**HIP-3 Stocks**:
- ❌ **No Binance equivalent** (stocks aren't on Binance)
- ✅ **Start fresh** (no backfill initially)
  - Let data accumulate over time
  - System works with partial data (needs ~300 bars for full TA)
  - Can add data source later if needed (Alpha Vantage, Yahoo Finance, etc.)

**Code Pattern** (similar to `regime_price_collector.backfill_majors_from_binance()`):
```python
def backfill_hyperliquid_crypto_from_binance(
    symbol: str,  # "BTC", "ETH", etc.
    timeframes: List[str] = ["15m", "1h", "4h"],
    days: int = 90,
) -> Dict[str, Any]:
    """Backfill Hyperliquid crypto markets from Binance"""
    # Map symbol (should be same: BTC→BTC, ETH→ETH)
    # Fetch from Binance REST API
    # Write to hyperliquid_price_data_ohlc
```

---

## Complete Implementation Plan

### Phase 1: Data Infrastructure

1. **Create Table**: `hyperliquid_price_data_ohlc`
   - Same schema as `lowcap_price_data_ohlc`
   - Fields: `token`, `timeframe`, `ts`, `o`, `h`, `l`, `c`, `v`, `trades`

2. **Create PriceDataReader Abstraction**
   - Routes by `(chain, book_id)` tuple
   - Returns OHLC data from correct table
   - Used by TA Tracker, Geometry Builder, Uptrend Engine

3. **Update Components to Use PriceDataReader**
   - TA Tracker: Read from `PriceDataReader` instead of direct table
   - Geometry Builder: Read from `PriceDataReader`
   - Uptrend Engine: Read from `PriceDataReader`

### Phase 2: Token Discovery

1. **Create HyperliquidTokenDiscovery Class**
   - Query all DEXs: `type="perpDexs"`
   - For each DEX: Query markets `type="meta", dex="<name>"`
   - Store token list with metadata

2. **Token Management**
   - Query on startup
   - Refresh periodically (daily/weekly)
   - Track active subscriptions

### Phase 3: WebSocket Ingestion

1. **Create HyperliquidCandleWSIngester**
   - Subscribe to all markets for 15m, 1h, 4h
   - Use `{dex}:{coin}` format for HIP-3 markets
   - Filter complete candles (timestamp change detection)
   - Write to `hyperliquid_price_data_ohlc`
   - Backpressure, reconnection, subscription diffing

### Phase 4: Historical Backfill

1. **Crypto Markets**: Binance backfill
   - Create `backfill_hyperliquid_crypto_from_binance()`
   - Map Hyperliquid → Binance symbols
   - Backfill on position creation

2. **Stocks**: Start fresh (no backfill initially)

### Phase 5: Regime Logic

1. **Update RegimeAECalculator**
   - Check if position is stock (HIP-3 equity)
   - Return neutral A/E for stocks
   - Use crypto regime for crypto markets

2. **Update PM Core Tick**
   - Pass position to A/E calculator
   - Handle neutral A/E for stocks

### Phase 6: Executor

1. **Create HyperliquidExecutor**
   - Implement `prepare()` (constraints, asset ID computation)
   - Implement `execute()` (Hyperliquid API calls)
   - Handle HIP-3 asset IDs (formula: `100000 + dex_index * 10000 + coin_index`)

2. **Create ExecutorFactory**
   - Route by `(token_chain, book_id)`
   - Return appropriate executor

### Phase 7: PM Integration

1. **Update PM Core Tick**
   - Use `ExecutorFactory` for routing
   - Handle `ExecutionIntent` pattern
   - Test end-to-end

---

## Key Decisions Summary

| Decision | Answer | Rationale |
|----------|--------|-----------|
| **All markets?** | ✅ Yes | Within limits, low message volume |
| **HIP-3 overlap?** | ✅ No | Different formats (`BTC` vs `xyz:TSLA`) |
| **Stocks regime?** | ❌ No | Neutral A/E, no crypto regime |
| **Historical data?** | Binance for crypto, fresh for stocks | Hyperliquid has no historical API |
| **Table structure?** | Separate `hyperliquid_price_data_ohlc` | Matches current pattern |
| **Timeframes?** | 15m, 1h, 4h only | User preference |

---

## Code Changes Required

### 1. Regime Calculator (Stocks = No Regime)

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/regime_ae_calculator.py`

```python
def compute_ae_for_token(
    self,
    token_bucket: Optional[str] = None,
    exec_timeframe: str = "1h",
    position: Optional[Dict[str, Any]] = None,  # NEW
    ...
) -> Tuple[float, float]:
    # Check if position is stock
    if position:
        token_contract = position.get("token_contract", "")
        # HIP-3 stocks have format "xyz:TSLA", "vntl:SPACEX"
        stock_tickers = ["TSLA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "SPACEX", "OPENAI", "ANTHROPIC"]
        is_stock = ":" in token_contract and any(
            ticker in token_contract.upper() for ticker in stock_tickers
        )
        if is_stock:
            return (0.5, 0.5)  # Neutral A/E
    
    # Crypto regime logic (existing)
    ...
```

### 2. PriceDataReader Abstraction

**File**: `src/intelligence/lowcap_portfolio_manager/data/price_data_reader.py` (new)

```python
class PriceDataReader:
    """Routes to correct OHLC table based on (chain, book_id)"""
    
    def get_ohlc(
        self,
        token: str,
        timeframe: str,
        chain: str,
        book_id: str,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        # Route to correct table
        if chain == "solana" and book_id == "onchain_crypto":
            table = "lowcap_price_data_ohlc"
        elif chain == "hyperliquid" and book_id == "perps":
            table = "hyperliquid_price_data_ohlc"
        else:
            raise ValueError(f"Unknown chain/book_id: {chain}/{book_id}")
        
        # Query table
        ...
```

### 3. Historical Backfill

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/hyperliquid_backfill.py` (new)

```python
def backfill_hyperliquid_crypto_from_binance(
    symbol: str,
    timeframes: List[str] = ["15m", "1h", "4h"],
    days: int = 90,
) -> Dict[str, Any]:
    """Backfill Hyperliquid crypto markets from Binance"""
    # Similar to regime_price_collector.backfill_majors_from_binance()
    # Map symbol (usually same)
    # Fetch from Binance
    # Write to hyperliquid_price_data_ohlc
```

---

## Risk Assessment

### Low Risk ✅
- Data ingestion (WebSocket candles work)
- Token discovery (API works)
- PM logic (universal, no changes needed)
- TA/Geometry (universal, just need PriceDataReader)

### Medium Risk ⚠️
- Historical backfill (need to test Binance mapping)
- Regime logic (need to test stock detection)
- Executor (need to test asset ID computation)

### High Risk ❌
- None identified

---

## Testing Strategy

1. **Unit Tests**:
   - PriceDataReader routing
   - Regime calculator (stocks vs crypto)
   - Asset ID computation (HIP-3 formula)

2. **Integration Tests**:
   - WebSocket ingestion (candles)
   - Historical backfill (Binance)
   - End-to-end (data → TA → Engine → PM → Executor)

3. **Dry-Run Tests**:
   - Executor in dry-run mode
   - Full position lifecycle
   - Learning system integration

---

## Conclusion

**✅ All bases covered**

- Market selection: All markets (within limits)
- HIP-3 overlap: No conflicts (different formats)
- Regime for stocks: Neutral A/E (no crypto regime)
- Historical data: Binance for crypto, fresh for stocks
- Implementation: Clear plan, low risk

**Ready to implement!**

