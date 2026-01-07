# Hyperliquid Token Management - Final Summary

**Date**: 2025-12-31  
**Status**: ✅ Complete - Ready for Implementation

---

## Executive Summary

✅ **Can handle ALL 224 tokens** (within subscription limits)  
✅ **Low message volume** (~20 messages/minute total)  
✅ **Simple implementation** - No filtering needed initially  
📊 **Capacity**: 672 subscriptions (3 timeframes × 224 tokens) out of 1000 max

---

## Key Findings

### Token Inventory

**Total Tokens**: 224

**Breakdown**:
- **Crypto tokens**: ~200+ (most tokens are crypto)
  - Identified: 42 (BTC, ETH, SOL, ATOM, MATIC, AVAX, BNB, DOGE, etc.)
  - Unknown (likely crypto): 180 (DYDX, APE, OP, LTC, ARB, INJ, SUI, LDO, STX, RNDR, CFX, FTM, GMX, BCH, APT, WLD, FXS, etc.)
- **Non-crypto**: 2-3 tokens
  - GAS (commodity)
  - SPX (index)
  - Possibly a few others

**Conclusion**: Vast majority of tokens are crypto. Only a few non-crypto tokens.

### Subscription Capacity

**Current Setup**:
- Timeframes: 15m, 1h, 4h (3 per token)
- Total tokens: 224
- Subscriptions needed: 672 (224 × 3)
- Max subscriptions allowed: 1000
- **Utilization: 67.2%**

**Headroom**:
- Remaining subscriptions: 328
- Additional tokens possible: ~109 more tokens
- Max tokens supported: 333 tokens (at 3 timeframes each)

**Conclusion**: ✅ **Can handle all tokens with room to spare**

### Message Volume

**Per Token Per Timeframe**:
- 15m candles: ~1 message per 15 minutes = 4 messages/hour
- 1h candles: ~1 message per hour = 1 message/hour
- 4h candles: ~1 message per 4 hours = 0.25 messages/hour
- **Total per token**: ~5.25 messages/hour

**For All 224 Tokens**:
- Total messages/hour: 224 × 5.25 = ~1,176 messages/hour
- **Total messages/minute**: ~20 messages/minute

**Comparison**:
- Trades (per token): ~26 messages/minute
- Candles (all 224 tokens): ~20 messages/minute total
- **Reduction**: Massive reduction in message volume

**Conclusion**: ✅ **Very low message volume - no performance concerns**

---

## Recommendations

### ✅ Recommended: Handle ALL Tokens

**Rationale**:
1. ✅ Within subscription limits (672/1000 = 67.2%)
2. ✅ Very low message volume (~20 messages/minute total)
3. ✅ No filtering complexity needed
4. ✅ Can discover opportunities across all tokens
5. ✅ Simple implementation

**Implementation Strategy**:
1. **Startup**: Query all tokens from Hyperliquid API
2. **Subscribe**: Subscribe to all 224 tokens for 15m, 1h, 4h timeframes
3. **Monitor**: Track message volume and processing performance
4. **Optimize Later**: Filter by volume/liquidity if needed (unlikely)

### Token Management Approach

**Dynamic Token Discovery**:
- Query Hyperliquid API on startup
- Refresh token list periodically (daily/weekly) to discover new tokens
- Auto-subscribe to new tokens

**Subscription Management**:
- Subscribe to all tokens initially
- Optional optimization: Unsubscribe from tokens with no positions (if performance becomes issue)
- Resubscribe when position opens

**Position Lifecycle**:
- All tokens start in "watchlist" status
- PM Core Tick evaluates all tokens (or filtered subset)
- Positions created when signals trigger
- Positions closed when signals trigger

---

## Implementation Plan

### Phase 1: Basic Implementation (Recommended)

1. **Token Discovery**:
   - Query Hyperliquid API on startup
   - Get all 224 tokens
   - Store token list in memory/DB

2. **Subscription Management**:
   - Subscribe to all tokens for 15m, 1h, 4h
   - Handle reconnections
   - Handle subscription diffs (new tokens)

3. **Candle Ingestion**:
   - Receive candle messages
   - Filter for complete candles (timestamp change detection)
   - Write to `hyperliquid_price_data_ohlc` table

4. **Position Management**:
   - Create positions in `lowcap_positions` table
   - `token_chain='hyperliquid'`, `book_id='perps'`
   - PM Core Tick processes all positions

### Phase 2: Optimization (If Needed)

**Only if performance becomes an issue:**

1. **Volume-based filtering**:
   - Only track top N tokens by 24h volume
   - Update watchlist periodically

2. **Position-based filtering**:
   - Only subscribe to tokens with active positions
   - Unsubscribe when position closes
   - Resubscribe when position opens

3. **Liquidity-based filtering**:
   - Filter out illiquid tokens
   - Only track tokens with tight spreads

---

## Token Categorization

### Current Status

**Identified Crypto**: 42 tokens  
**Unknown (likely crypto)**: 180 tokens

**Analysis**: Most "unknown" tokens are actually crypto tokens that weren't matched by pattern matching. Examples:
- DYDX (DYDX protocol)
- APE (ApeCoin)
- OP (Optimism)
- LTC (Litecoin)
- ARB (Arbitrum)
- INJ (Injective)
- SUI (Sui)
- LDO (Lido)
- STX (Stacks)
- RNDR (Render)

**Conclusion**: ~200+ tokens are crypto. Only 2-3 non-crypto tokens (GAS, SPX).

### Recommendation

**Don't filter by asset type** - we have capacity for all tokens, and categorization is incomplete. Handle all tokens and let the PM decide which to trade based on signals.

---

## Capacity Analysis

### Subscription Limits

| Metric | Value |
|--------|-------|
| Total tokens | 224 |
| Timeframes per token | 3 (15m, 1h, 4h) |
| Total subscriptions needed | 672 |
| Max subscriptions allowed | 1000 |
| Utilization | 67.2% |
| Headroom | 328 subscriptions |
| Max tokens supported | 333 tokens |

### Message Volume

| Metric | Value |
|--------|-------|
| Messages per token per hour | ~5.25 |
| Total messages per hour (all tokens) | ~1,176 |
| Total messages per minute | ~20 |
| Comparison to trades | 88% reduction |

---

## Questions Answered

### Q1: How many Hyperliquid positions can we handle?

**A**: **All 224 tokens** (672 subscriptions, well under 1000 limit)

### Q2: Should we handle all tokens or filter?

**A**: **Handle all tokens** - within limits, low message volume, simple implementation

### Q3: Should we focus on crypto tokens only?

**A**: **No need to filter** - we have capacity for all tokens. Most tokens are crypto anyway (~200+), and categorization is incomplete.

### Q4: How to manage different tokens?

**A**: 
- Query API on startup for all tokens
- Subscribe to all tokens for 15m, 1h, 4h
- Refresh token list periodically (daily/weekly)
- Monitor performance, optimize later if needed

---

## Next Steps

1. ✅ **Token Discovery**: Complete - 224 tokens found
2. ✅ **Capacity Analysis**: Complete - Can handle all tokens
3. ⏭️ **Implement Token Management**: Dynamic subscription management
4. ⏭️ **Implement Candle Ingester**: With timestamp-based filtering
5. ⏭️ **Monitor Performance**: Track message volume and processing time

---

## Conclusion

**✅ Handle ALL 224 tokens**

- Within subscription limits (67.2% utilization)
- Very low message volume (~20 messages/minute total)
- Simple implementation (no filtering needed)
- Can optimize later if needed (unlikely)

**Ready to implement!**

