# Hyperliquid Trading API - Summary

**Date**: 2025-12-31  
**Status**: Initial Exploration Complete  
**Next**: Review Hyperliquid docs for auth & order format

---

## What We Know

### ✅ Asset ID Computation

**Main DEX**:
- Asset ID = index in `universe` array
- BTC = 0, ETH = 1, etc.

**HIP-3**:
- Asset ID = `100000 + dex_index * 10000 + coin_index`
- Query `perpDexs` → find dex_index
- Query `meta(dex="...")` → find coin_index in DEX universe
- HIP-3 tokens use full format `"dex:coin"` in universe

### ✅ Asset Metadata

Each asset has:
- `name`: Token name (e.g., "BTC", "xyz:TSLA")
- `szDecimals`: Decimal places for size (e.g., 5 for BTC)
- `maxLeverage`: Maximum leverage (e.g., 40 for BTC)
- `marginTableId`: Margin table reference

### ⚠️ What We Need to Learn

1. **Authentication**:
   - How to sign orders? (wallet signature?)
   - What's the signature format?
   - Do we need nonces?

2. **Order Format**:
   - Exact field names and structure
   - Size format (contracts? notional USD?)
   - Order types (market, limit, stop)
   - How to specify leverage (0.0 for spot?)

3. **Position Management**:
   - How to query positions?
   - How to close positions (reduce-only)?
   - Position fields (size, entry price, PnL)

4. **Constraints**:
   - Min notional per market?
   - Leverage limits (already have maxLeverage)
   - Reduce-only rules

5. **Testing**:
   - Is testnet available?
   - Can we use dry-run mode?
   - How to test without real execution?

---

## Next Steps

1. **Review Hyperliquid Docs**:
   - Check `/exchange` endpoint docs
   - Understand authentication method
   - Understand order format

2. **Set Up Testing**:
   - Set up wallet connection (if needed)
   - Test with smallest possible amounts
   - Or use testnet if available

3. **Document Findings**:
   - Update `hyperliquid_trading_api_findings.md` with complete API structure
   - Document all field names and formats
   - Document error handling

4. **Create Executor**:
   - Based on findings, create `HyperliquidExecutor`
   - Start with dry-run mode
   - Test order placement
   - Test position management

---

## Resources

- Hyperliquid Docs: https://hyperliquid.gitbook.io/hyperliquid-docs/
- API Reference: Check `/exchange` endpoint
- Testnet: Check if available

