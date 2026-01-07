# Hyperliquid HIP-3 Market Access Investigation

**Date**: 2025-12-31  
**Question**: Are HIP-3 (third-party) markets accessible via the same API/WebSocket?

---

## What is HIP-3?

**HIP-3** enables permissionless deployment of perpetual futures markets on Hyperliquid:
- Third parties can deploy markets by staking 500,000 HYPE tokens
- Supports equities, commodities, indices, forex, and crypto
- Markets operate natively on Hyperliquid infrastructure
- Same matching engine, risk model, and settlement logic

---

## Current Findings

### Standard Universe Query

**Result**: 224 tokens found, all appear to be standard Hyperliquid markets
- No obvious HIP-3 indicators in the data structure
- All tokens have same structure: `{name, szDecimals, maxLeverage, marginTableId}`

### Key Questions

1. **Are HIP-3 markets included in the standard universe?**
   - Current test: All 224 tokens look like standard markets
   - No field indicating "HIP-3" or "third-party"
   - Possible: HIP-3 markets are in the same universe, just not distinguishable

2. **How to identify HIP-3 markets?**
   - No obvious metadata field
   - Might need to check `marginTableId` ranges?
   - Might need external source (HIP-3 tracker, community lists)

3. **Are there any HIP-3 markets deployed yet?**
   - Need to check HIP-3 tracker: https://hip-3.xyz
   - Check community announcements
   - Check if any equity markets exist

---

## Access Methods

### According to Documentation

1. **Same Infrastructure**: HIP-3 markets use the same Hyperliquid infrastructure
   - Same WebSocket API
   - Same REST API
   - Same matching engine

2. **Platforms**:
   - **trade[XYZ]**: Operates on Hyperliquid, offers equities/commodities
   - **Hydromancer**: Provides APIs for HIP-3 markets
   - **Trove**: First HIP-3 deployment (collectibles)

3. **API Access**: Should be accessible via standard Hyperliquid API

---

## Investigation Needed

### Test 1: Check if HIP-3 markets are in universe

**Hypothesis**: HIP-3 markets might be in the same universe but not easily identifiable

**Test**: 
- Check all 224 tokens for any that might be equities (Tesla, SpaceX, etc.)
- Look for patterns in `marginTableId` that might indicate HIP-3
- Check if any tokens have different structure

### Test 2: Check HIP-3 Tracker

**Action**: Query https://hip-3.xyz for deployed markets

### Test 3: Test WebSocket Subscription

**Action**: Try subscribing to a known HIP-3 market (if we can identify one)

### Test 4: Check External Sources

**Action**: 
- Check trade[XYZ] for available markets
- Check Hydromancer documentation
- Check Hyperliquid community/announcements

---

## Current Status

**Finding**: Standard universe query returns 224 tokens, all appear to be standard markets

**Possible Explanations**:
1. **No HIP-3 markets deployed yet** - Most likely
2. **HIP-3 markets are in universe but not distinguishable** - Need to identify them
3. **HIP-3 markets need separate discovery** - Different endpoint/query

**Next Steps**:
1. Check HIP-3 tracker for deployed markets
2. Check if any of the 224 tokens are actually HIP-3 markets (equities, etc.)
3. Test WebSocket subscription to see if HIP-3 markets work the same way

---

## Recommendation

**For Now**: 
- Focus on the 224 standard markets (all crypto)
- HIP-3 markets can be added later when:
  - We identify how to discover them
  - We confirm they're accessible via same API
  - We have a use case for equities/commodities

**Future**:
- Monitor HIP-3 tracker for new markets
- Test access when equity markets are deployed
- Add HIP-3 market discovery to token management system

