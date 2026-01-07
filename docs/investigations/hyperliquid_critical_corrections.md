# Hyperliquid Integration - Critical Corrections

**Date**: 2025-12-31  
**Status**: Pre-Implementation Corrections

---

## Critical Issues Identified

### 1. Message Volume - Candle Close Synchronization ⚠️

**Question**: If all 15m candles close at the same time (every 15 minutes), will we get a burst of messages all at once? Is that an issue?

**Analysis**:
- **15m candles close**: Every 15 minutes (:00, :15, :30, :45)
- **For 282 markets**: All candles close at the same time
- **Message burst**: ~282 messages in a few seconds (one per market)
- **Then**: Partial updates as candles form (spread over 15 minutes)

**Potential Issues**:
1. **Database write burst**: 282 writes at once could bottleneck
2. **Processing burst**: All positions get new bars simultaneously
3. **PM Core Tick**: All positions evaluated at once (could be slow)

**Mitigation Strategies**:

**Option A: Batch Writes** (Recommended)
- Buffer candle messages
- Write in batches (e.g., 50 candles per batch)
- Spread writes over a few seconds

**Option B: Queue with Workers**
- Use bounded queue
- Multiple workers process candles
- Smooths out the burst

**Option C: Accept the Burst**
- Modern databases handle 282 writes easily
- PM Core Tick already processes all positions
- May not be an issue in practice

**Recommendation**: **Start with Option C** (accept burst), monitor, add batching if needed.

**Test**: Monitor database write performance and PM Core Tick processing time during candle closes.

---

### 2. Regime vs PM Strength - Clarification ✅

**Correction**: I was confusing two separate systems:

**A. Regime (A/E Calculation)**:
- Uses crypto regime drivers (BTC, ALT, buckets, dominance)
- Computes base A/E scores
- **For stocks**: Should return neutral A/E (0.5, 0.5)
- **Code**: `RegimeAECalculator.compute_ae_for_token()` or `compute_ae_v2()`

**B. PM Strength (Learning System)**:
- Learned pattern strength from historical outcomes
- Applied AFTER base A/E calculation
- **For stocks**: Should still work (learns from stock patterns)
- **Code**: `apply_strength_to_ae()` or `apply_pattern_strength_overrides()`

**Key Point**: 
- **Regime**: Stocks get neutral (no crypto regime influence)
- **PM Strength**: Stocks still get learning (pattern-based strength)

**Implementation**:
```python
# In PM Core Tick:
# 1. Compute base A/E (regime)
if is_stock:
    a_base, e_base = (0.5, 0.5)  # Neutral (no crypto regime)
else:
    a_base, e_base = compute_ae_v2(regime_flags, token_bucket)  # Crypto regime

# 2. Apply PM strength (learning system) - WORKS FOR BOTH
strength_mult = get_pm_strength(pattern_key, position)  # Still works for stocks!
a_final, e_final = apply_strength_to_ae(a_base, e_base, strength_mult)
```

**Conclusion**: 
- ✅ Stocks: No crypto regime (neutral A/E)
- ✅ Stocks: Still get PM strength (learning system works)

---

### 3. Book ID for Stocks ✅

**Correction**: Use `book_id='stocks'` for HIP-3 equities

**Schema**:
- **Main DEX Crypto**: `token_chain='hyperliquid'`, `book_id='perps'`, `token_contract='BTC'`
- **HIP-3 Stocks**: `token_chain='hyperliquid'`, `book_id='stocks'`, `token_contract='xyz:TSLA'`
- **HIP-3 Crypto**: Don't use (Hyperliquid main DEX has all crypto)

**Implementation**:
```python
# In RegimeAECalculator or compute_ae_v2()
if book_id == 'stocks':
    return (0.5, 0.5)  # Neutral A/E (no crypto regime)
```

---

### 4. HIP-3 Markets - Only Stocks, Not Crypto ✅

**Correction**: Don't use HIP-3 for crypto markets

**Rationale**:
- Hyperliquid main DEX already has all crypto markets (224 tokens)
- HIP-3 crypto markets (like `hyna:BTC`) are redundant
- Only use HIP-3 for stocks/equities (Tesla, SpaceX, etc.)

**Market Selection**:
- **Main DEX**: All 224 crypto tokens ✅
- **HIP-3**: Only stocks/equities (xyz:TSLA, xyz:AAPL, vntl:SPACEX, etc.) ✅
- **HIP-3 Crypto**: Skip (hyna:BTC, hyna:ETH, etc.) ❌

**Total Markets**:
- Main DEX: 224 crypto
- HIP-3 Stocks: ~30-40 stocks (from xyz, flx, vntl DEXs)
- **Total**: ~260 markets (not 282)

**Subscriptions**:
- 260 markets × 3 timeframes = 780 subscriptions
- Still well under 1000 limit ✅

---

### 5. Binance Symbol Mapping ⚠️

**Question**: Binance symbol is not the same - we fixed in backfill but look into that

**Current Mapping** (from `regime_price_collector.py`):
```python
MAJOR_SYMBOLS = {
    "BTC": "BTCUSDT",  # Hyperliquid: BTC, Binance: BTCUSDT
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "BNB": "BNBUSDT",
}
```

**For Hyperliquid Backfill**:
- Need to map Hyperliquid symbol → Binance symbol
- Most are same (BTC→BTCUSDT, ETH→ETHUSDT)
- But need to handle edge cases

**Implementation**:
```python
HYPERLIQUID_TO_BINANCE = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "BNB": "BNBUSDT",
    # Add more mappings as needed
    # Some tokens might not be on Binance
}

def get_binance_symbol(hyperliquid_symbol: str) -> Optional[str]:
    """Map Hyperliquid symbol to Binance symbol"""
    # Remove dex prefix if present (for HIP-3)
    if ":" in hyperliquid_symbol:
        symbol = hyperliquid_symbol.split(":")[1]
    else:
        symbol = hyperliquid_symbol
    
    # Map to Binance
    return HYPERLIQUID_TO_BINANCE.get(symbol)
```

**Edge Cases**:
- Some Hyperliquid tokens might not be on Binance
- Some might have different names
- Need to test mapping for all 224 tokens

---

## Updated Implementation Plan

### Market Selection (Corrected)

**Main DEX**: All 224 crypto tokens
- Use for all crypto trading
- Backfill from Binance

**HIP-3 DEXs**: Only stocks/equities
- xyz DEX: Stocks (TSLA, AAPL, MSFT, GOOGL, AMZN, NVDA, META, etc.)
- flx DEX: Stocks (TSLA, NVDA)
- vntl DEX: Stocks/AI (SPACEX, OPENAI, ANTHROPIC)
- Skip: HIP-3 crypto markets (hyna:BTC, etc.)

**Total**: ~260 markets (224 crypto + ~36 stocks)

---

## Updated Code Changes

### 1. Regime Calculator (Stocks = No Regime, But PM Strength Still Works)

```python
def compute_ae_for_token(
    self,
    token_bucket: Optional[str] = None,
    exec_timeframe: str = "1h",
    book_id: Optional[str] = None,  # NEW
    ...
) -> Tuple[float, float]:
    # Check book_id for stocks
    if book_id == 'stocks':
        return (0.5, 0.5)  # Neutral A/E (no crypto regime)
    
    # Crypto regime logic (existing)
    ...
```

**Note**: PM strength is applied later in `plan_actions_v4()`, so stocks still get learning.

### 2. Binance Symbol Mapping

```python
HYPERLIQUID_TO_BINANCE = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "BNB": "BNBUSDT",
    # Add all 224 mappings
    # Test each one
}

def backfill_hyperliquid_crypto_from_binance(
    symbol: str,
    timeframes: List[str] = ["15m", "1h", "4h"],
) -> Dict[str, Any]:
    # Map Hyperliquid → Binance
    binance_symbol = HYPERLIQUID_TO_BINANCE.get(symbol)
    if not binance_symbol:
        logger.warning(f"No Binance mapping for {symbol}")
        return {}
    
    # Fetch from Binance
    # Write to hyperliquid_price_data_ohlc
```

### 3. Market Selection (Skip HIP-3 Crypto)

```python
def discover_hyperliquid_markets() -> List[Dict[str, Any]]:
    markets = []
    
    # Main DEX: All crypto
    main_markets = query_main_dex()  # 224 tokens
    markets.extend(main_markets)
    
    # HIP-3 DEXs: Only stocks
    hip3_dexs = query_hip3_dexs()
    for dex in hip3_dexs:
        dex_markets = query_dex_markets(dex["name"])
        # Filter: Only stocks (skip crypto)
        stock_markets = [
            m for m in dex_markets 
            if is_stock_market(m)  # Check if TSLA, AAPL, etc.
        ]
        markets.extend(stock_markets)
    
    return markets
```

---

## Summary of Corrections

1. ✅ **Message Burst**: Accept it initially, monitor, add batching if needed
2. ✅ **PM Strength**: Still works for stocks (separate from regime)
3. ✅ **Book ID**: Use `book_id='stocks'` for HIP-3 equities
4. ✅ **HIP-3 Markets**: Only stocks, skip crypto (main DEX has all crypto)
5. ✅ **Binance Mapping**: Need proper symbol mapping (not 1:1)

---

## Next Steps

1. **Test Message Burst**: Monitor during candle closes
2. **Create Symbol Mapping**: Map all 224 Hyperliquid symbols to Binance
3. **Filter HIP-3 Markets**: Only include stocks, skip crypto
4. **Update Regime Logic**: Check `book_id='stocks'` for neutral A/E
5. **Verify PM Strength**: Confirm it works for stocks (should work automatically)

