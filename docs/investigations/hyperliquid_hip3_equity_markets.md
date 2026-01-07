# Hyperliquid HIP-3 Equity Markets - Complete List

**Date**: 2025-12-31  
**Status**: ✅ Equity Markets Found!

---

## Summary

✅ **HIP-3 equity markets ARE available**  
✅ **Tesla (TSLA) found** - Multiple DEXs  
✅ **SpaceX found** - On Ventuals DEX  
✅ **Many other stocks available** - Apple, Microsoft, Google, Amazon, Nvidia, Meta, etc.

---

## HIP-3 DEXs Found

### DEX 0: main (null)
- Standard Hyperliquid markets (224 crypto tokens)

### DEX 1: xyz (XYZ) - **29 Markets**

**Equity Markets**:
- `xyz:TSLA` - Tesla
- `xyz:NVDA` - Nvidia
- `xyz:META` - Meta (Facebook)
- `xyz:AAPL` - Apple
- `xyz:MSFT` - Microsoft
- `xyz:GOOGL` - Google
- `xyz:AMZN` - Amazon
- `xyz:AMD` - AMD
- `xyz:INTC` - Intel
- `xyz:ORCL` - Oracle
- `xyz:NFLX` - Netflix
- `xyz:HOOD` - Robinhood
- `xyz:COIN` - Coinbase
- `xyz:PLTR` - Palantir
- `xyz:MSTR` - MicroStrategy
- `xyz:COST` - Costco
- `xyz:LLY` - Eli Lilly
- `xyz:MU` - Micron
- `xyz:SNDK` - Sandisk
- `xyz:SKHX` - ?
- `xyz:TSM` - Taiwan Semiconductor
- `xyz:RIVN` - Rivian
- `xyz:BABA` - Alibaba

**Commodities/Forex**:
- `xyz:GOLD` - Gold
- `xyz:SILVER` - Silver
- `xyz:JPY` - Japanese Yen
- `xyz:EUR` - Euro

**Indices**:
- `xyz:XYZ100` - XYZ 100 Index
- `xyz:CRCL` - ?

### DEX 2: flx (Felix Exchange) - **9 Markets**

**Equity Markets**:
- `flx:TSLA` - Tesla
- `flx:NVDA` - Nvidia

**Crypto**:
- `flx:COIN` - Coinbase
- `flx:XMR` - Monero

**Commodities**:
- `flx:GOLD` - Gold
- `flx:SILVER` - Silver
- `flx:OIL` - Oil
- `flx:GAS` - Gas

**Other**:
- `flx:CRCL` - ?

### DEX 3: vntl (Ventuals) - **6 Markets** ⭐

**AI/Equity Markets**:
- `vntl:SPACEX` - **SpaceX** ✅
- `vntl:OPENAI` - OpenAI
- `vntl:ANTHROPIC` - Anthropic

**Indices**:
- `vntl:MAG7` - Magnificent 7
- `vntl:SEMIS` - Semiconductors
- `vntl:ROBOT` - Robotics

### DEX 4: hyna (HyENA) - **8 Markets**

**Crypto Only**:
- `hyna:BTC`, `hyna:ETH`, `hyna:HYPE`, `hyna:SOL`, `hyna:LIT`, `hyna:ZEC`, `hyna:XRP`, `hyna:LIGHTER`

### DEX 5: km (Markets by Kinetiq) - **6 Markets**

**Indices/Bonds**:
- `km:US500` - US 500
- `km:USTECH` - US Tech
- `km:SMALL2000` - Small Cap 2000
- `km:USBOND` - US Bonds
- `km:BABA` - Alibaba
- `km:EUR` - Euro

---

## Key Findings

### ✅ Tesla Available
- `xyz:TSLA` (XYZ DEX)
- `flx:TSLA` (Felix Exchange)

### ✅ SpaceX Available
- `vntl:SPACEX` (Ventuals DEX)

### ✅ Major Tech Stocks Available
- Apple, Microsoft, Google, Amazon, Nvidia, Meta, AMD, Intel, Oracle, Netflix, etc.

### ✅ AI Companies Available
- OpenAI, Anthropic (on Ventuals)

---

## Access Method

### WebSocket Subscription Format

**HIP-3 markets use**: `{dex}:{coin}` format

**Examples**:
```json
{
  "method": "subscribe",
  "subscription": {
    "type": "candle",
    "coin": "xyz:TSLA",  // Tesla on XYZ DEX
    "interval": "15m"
  }
}
```

```json
{
  "method": "subscribe",
  "subscription": {
    "type": "candle",
    "coin": "vntl:SPACEX",  // SpaceX on Ventuals DEX
    "interval": "1h"
  }
}
```

### Asset ID Computation

**Formula**: `asset = 100000 + perp_dex_index * 10000 + index_in_meta`

**Example for `xyz:TSLA`**:
- DEX index: 1 (xyz is at index 1 in perpDexs)
- Market index: 1 (TSLA is at index 1 in xyz universe)
- Asset ID = `100000 + 1 * 10000 + 1 = 110001`

---

## Implementation Notes

### Token Discovery

1. **Query all DEXs**: `type="perpDexs"`
2. **For each HIP-3 DEX**:
   - Query markets: `type="meta", dex="<name>"`
   - Format as `{dex}:{coin}`
   - Store DEX index for asset ID computation

### Subscription Management

**Total Markets**:
- Main DEX: 224 tokens
- xyz DEX: 29 markets
- flx DEX: 9 markets
- vntl DEX: 6 markets
- hyna DEX: 8 markets
- km DEX: 6 markets
- **Total**: ~282 markets

**For 3 timeframes (15m, 1h, 4h)**:
- Total subscriptions: ~846 (well under 1000 limit)

### Recommendation

**Option 1: All Markets** (Recommended)
- Subscribe to all markets from all DEXs
- Within subscription limits
- Can discover opportunities across all asset classes

**Option 2: Crypto Only**
- Main DEX only (224 tokens)
- Skip HIP-3 DEXs

**Option 3: Selective**
- Main DEX + specific HIP-3 DEXs (e.g., xyz for stocks, vntl for SpaceX)

---

## Next Steps

1. ✅ **Discovery Complete** - Found all HIP-3 DEXs and markets
2. ⏭️ **Test WebSocket** - Verify `{dex}:{coin}` format works for candles
3. ⏭️ **Implement Discovery** - Add HIP-3 DEX discovery to token management
4. ⏭️ **Test Asset IDs** - Verify asset ID computation for trading

---

## Conclusion

✅ **HIP-3 equity markets ARE accessible**  
✅ **Tesla and SpaceX available**  
✅ **Same WebSocket/API infrastructure**  
✅ **Use `{dex}:{coin}` format for subscriptions**

**Ready to implement!**

