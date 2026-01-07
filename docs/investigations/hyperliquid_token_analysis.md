# Hyperliquid Token Analysis - Results

**Date**: 2025-12-31  
**Test**: `tests/hyperliquid/test_token_discovery.py`

---

## Executive Summary

✅ **Can handle ALL 224 tokens** (within subscription limits)  
⚠️ **Categorization incomplete** - 180 tokens marked as "unknown" (likely crypto)  
📊 **Capacity**: 672 subscriptions needed (3 timeframes × 224 tokens), well under 1000 limit

---

## Token Inventory

### Total Tokens: 224

### Categorized Tokens: 44
- **Crypto**: 42 tokens (BTC, ETH, SOL, ATOM, MATIC, AVAX, BNB, DOGE, kPEPE, CRV, etc.)
- **Commodities**: 1 token (GAS)
- **Indices**: 1 token (SPX)

### Unknown Tokens: 180
**Examples**: DYDX, APE, OP, LTC, ARB, INJ, SUI, LDO, STX, RNDR, etc.

**Analysis**: Most "unknown" tokens are likely crypto tokens that weren't matched by our pattern matching. Common crypto tokens in the unknown list:
- DYDX (DYDX protocol token)
- APE (ApeCoin)
- OP (Optimism)
- LTC (Litecoin)
- ARB (Arbitrum)
- INJ (Injective)
- SUI (Sui)
- LDO (Lido)
- STX (Stacks)
- RNDR (Render)

**Conclusion**: The vast majority of tokens are crypto. Only a few non-crypto tokens (GAS, SPX).

---

## Subscription Capacity Analysis

### Current Setup
- **Timeframes**: 15m, 1h, 4h (3 per token)
- **Total tokens**: 224
- **Subscriptions needed**: 672 (224 × 3)
- **Max subscriptions allowed**: 1000
- **Utilization**: 67.2%

### Capacity Headroom
- **Remaining subscriptions**: 328
- **Additional tokens possible**: ~109 more tokens (if needed)
- **Max tokens supported**: 333 tokens (at 3 timeframes each)

### Conclusion
✅ **Can handle all 224 tokens with room to spare**

---

## Token Management Strategy

### Option 1: Handle All Tokens ✅ (Recommended)

**Pros:**
- ✅ Within subscription limits (672/1000)
- ✅ No filtering logic needed
- ✅ Can discover opportunities across all tokens
- ✅ Simple implementation

**Cons:**
- ⚠️ More positions to manage
- ⚠️ More database writes
- ⚠️ More PM ticks to process

**Recommendation**: **Start with all tokens**, monitor performance, filter later if needed.

### Option 2: Crypto Only

**Pros:**
- ✅ Focus on crypto (main expertise)
- ✅ Fewer tokens to manage (~42-200 depending on categorization)
- ✅ Lower message volume

**Cons:**
- ❌ Need to maintain crypto token list
- ❌ Miss opportunities in other tokens
- ❌ Categorization incomplete (180 "unknown" likely crypto)

**Recommendation**: **Not recommended** - categorization is incomplete, and we have capacity.

### Option 3: Filtered Approach

**Filter by:**
- Volume/liquidity (top N tokens)
- Manual watchlist
- Asset type (crypto only, but categorization incomplete)

**Recommendation**: **Not needed initially** - we have capacity for all tokens.

---

## Implementation Strategy

### Phase 1: All Tokens (Recommended)

1. **Subscribe to all 224 tokens** for 15m, 1h, 4h timeframes
2. **Monitor performance**:
   - Message volume per token
   - Database write performance
   - PM tick processing time
3. **Dynamic filtering** (if needed later):
   - Filter by volume (top N by 24h volume)
   - Filter by liquidity (min spread requirements)
   - Filter by position status (only active positions)

### Phase 2: Optimization (If Needed)

If performance becomes an issue:

1. **Volume-based filtering**:
   - Only track tokens with 24h volume > threshold
   - Update watchlist periodically (daily/weekly)

2. **Position-based filtering**:
   - Only subscribe to tokens with active positions
   - Unsubscribe when position closes
   - Resubscribe when position opens

3. **Liquidity-based filtering**:
   - Only track tokens with tight spreads
   - Filter out illiquid tokens

---

## Token Discovery & Management

### Dynamic Token List

**Current Approach**: Query Hyperliquid API on startup

**Recommended Approach**:
1. **Startup**: Query all tokens from Hyperliquid API
2. **Periodic Refresh**: Re-query daily/weekly to discover new tokens
3. **Subscription Management**: 
   - Subscribe to all tokens initially
   - Unsubscribe from tokens with no positions (optional optimization)
   - Resubscribe when position opens

### Token Metadata

**Available from API**:
- Token name/symbol
- Max leverage
- Size decimals
- Margin requirements
- Volume/liquidity (from market data)

**Use for**:
- Filtering (volume, liquidity)
- Position sizing (leverage limits)
- Risk management (margin requirements)

---

## Message Volume Estimation

### Per Token Per Timeframe

**15m candles**: ~1 message per 15 minutes = 4 messages/hour
**1h candles**: ~1 message per hour = 1 message/hour  
**4h candles**: ~1 message per 4 hours = 0.25 messages/hour

**Total per token**: ~5.25 messages/hour

### For All 224 Tokens

**Total messages/hour**: 224 × 5.25 = ~1,176 messages/hour = ~20 messages/minute

**Comparison to trades**:
- Trades: ~26 messages/minute per token
- Candles (all tokens): ~20 messages/minute total
- **Reduction**: Massive reduction in message volume

---

## Recommendations

### ✅ Recommended: Handle All Tokens

**Rationale**:
1. ✅ Within subscription limits (672/1000)
2. ✅ Low message volume (~20 messages/minute total)
3. ✅ No filtering complexity needed
4. ✅ Can discover opportunities across all tokens
5. ✅ Simple implementation

**Implementation**:
1. Query all tokens from Hyperliquid API on startup
2. Subscribe to all tokens for 15m, 1h, 4h timeframes
3. Monitor performance
4. Optimize later if needed (volume/liquidity filtering)

### ⚠️ Future Optimization (If Needed)

If performance becomes an issue:

1. **Volume-based filtering**: Only track top N tokens by volume
2. **Position-based filtering**: Only subscribe to tokens with active positions
3. **Liquidity-based filtering**: Filter out illiquid tokens

---

## Next Steps

1. ✅ **Token Discovery**: Complete - 224 tokens found
2. ✅ **Capacity Analysis**: Complete - Can handle all tokens
3. ⏭️ **Improve Categorization**: Better pattern matching for crypto tokens
4. ⏭️ **Implement Token Management**: Dynamic subscription management
5. ⏭️ **Monitor Performance**: Track message volume and processing time

---

## Questions to Answer

1. **Q**: Should we handle all tokens or filter?
   - **A**: Handle all tokens initially (within limits, low message volume)

2. **Q**: How to manage token list dynamically?
   - **A**: Query API on startup, refresh periodically, subscribe to all

3. **Q**: What about non-crypto tokens (GAS, SPX)?
   - **A**: Include them - we have capacity, and they might be interesting

4. **Q**: How to handle new tokens added to Hyperliquid?
   - **A**: Periodic refresh (daily/weekly) to discover new tokens

---

## Conclusion

**✅ Handle ALL 224 tokens**

- Within subscription limits (672/1000)
- Low message volume (~20 messages/minute total)
- Simple implementation
- Can optimize later if needed

**Ready to implement!**

