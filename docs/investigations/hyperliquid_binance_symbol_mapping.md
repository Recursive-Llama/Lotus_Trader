# Hyperliquid to Binance Symbol Mapping

**Date**: 2025-12-31  
**Goal**: Create accurate symbol mapping for historical backfill

---

## Current Mapping

**From `regime_price_collector.py`**:
```python
MAJOR_SYMBOLS = {
    "BTC": "BTCUSDT",
    "SOL": "SOLUSDT",
    "ETH": "ETHUSDT",
    "BNB": "BNBUSDT",
}
```

**Pattern**: Hyperliquid uses base symbol, Binance uses `{SYMBOL}USDT`

---

## Mapping Strategy

### For All 224 Hyperliquid Tokens

**General Rule**:
- Most tokens: `{SYMBOL}USDT` on Binance
- Some exceptions: Different names, not available, etc.

**Implementation**:
```python
HYPERLIQUID_TO_BINANCE = {
    # Direct mappings (most common)
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "BNB": "BNBUSDT",
    
    # Add all 224 mappings
    # Test each one
}

def get_binance_symbol(hyperliquid_symbol: str) -> Optional[str]:
    """Map Hyperliquid symbol to Binance symbol"""
    # Remove dex prefix if present (for HIP-3)
    if ":" in hyperliquid_symbol:
        symbol = hyperliquid_symbol.split(":")[1]
    else:
        symbol = hyperliquid_symbol
    
    # Map to Binance
    binance_symbol = HYPERLIQUID_TO_BINANCE.get(symbol)
    
    if not binance_symbol:
        # Try default pattern: {SYMBOL}USDT
        binance_symbol = f"{symbol}USDT"
        # Test if it exists on Binance
        if not binance_symbol_exists(binance_symbol):
            return None
    
    return binance_symbol
```

---

## Testing Required

1. **Query All Hyperliquid Tokens**: Get all 224 symbols
2. **Test Binance Mapping**: For each symbol, test if `{SYMBOL}USDT` exists
3. **Handle Exceptions**: Some tokens might not be on Binance
4. **Create Mapping Table**: Store working mappings

---

## Edge Cases

1. **Tokens Not on Binance**: Skip backfill, start fresh
2. **Different Names**: Manual mapping (e.g., `HYPE` might not be on Binance)
3. **HIP-3 Crypto**: Don't backfill (we're not using HIP-3 crypto anyway)

---

## Next Steps

1. **Create Test Script**: Query all Hyperliquid tokens, test Binance mapping
2. **Build Mapping Table**: Store working mappings
3. **Handle Missing**: Skip tokens not on Binance (start fresh)

