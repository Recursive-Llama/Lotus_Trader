# Hyperliquid Token Management Investigation

**Date**: 2025-12-31  
**Goal**: Understand token availability, capacity limits, and management strategy for Hyperliquid positions

---

## Questions to Answer

1. **What tokens are available on Hyperliquid?**
   - How many total tokens?
   - What asset types (crypto, stocks, commodities, etc.)?
   - How to query available tokens?

2. **How many positions can we handle?**
   - WebSocket subscription limits (1000 subscriptions)
   - Message volume per token
   - Database/processing capacity

3. **Token management strategy:**
   - Handle all tokens or filter?
   - Filter by asset type (crypto only)?
   - Filter by volume/liquidity?
   - Dynamic watchlist management?

4. **Timeframe focus:**
   - User preference: 15m, 1h, 4h only
   - How many subscriptions per token (3 timeframes = 3 subscriptions)?

---

## Investigation Plan

### Step 1: Query Available Tokens
- Use Hyperliquid API to get all available tokens
- Categorize by asset type
- Count total tokens

### Step 2: Analyze Subscription Capacity
- Calculate: 1000 subscriptions / 3 timeframes = ~333 tokens max
- Test actual subscription behavior
- Measure message volume per token

### Step 3: Token Categorization
- Identify crypto tokens vs other asset types
- Check volume/liquidity metrics
- Identify high-priority tokens

### Step 4: Management Strategy
- Propose filtering approach
- Dynamic watchlist management
- Position lifecycle (watchlist → active → closed)

---

## Test Scripts Needed

1. **Token Discovery Script**: Query all available tokens
2. **Subscription Capacity Test**: Test how many subscriptions work
3. **Message Volume Analysis**: Measure messages per token per timeframe
4. **Token Categorization**: Classify tokens by type

---

## Expected Outcomes

1. **Token Inventory**: Complete list of available tokens with metadata
2. **Capacity Limits**: Maximum positions we can handle
3. **Management Strategy**: Recommended approach for token selection
4. **Implementation Plan**: How to manage tokens dynamically

