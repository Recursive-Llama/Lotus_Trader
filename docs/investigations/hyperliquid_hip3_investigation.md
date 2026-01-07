# Hyperliquid HIP-3 Investigation

**Date**: 2025-12-31  
**Question**: Are tokenized stocks (Tesla, SpaceX) available via HIP-3?

---

## What is HIP-3?

**HIP-3** (Hyperliquid Improvement Proposal 3) is a protocol upgrade that enables:

1. **Permissionless Market Deployment**: Anyone who stakes 500,000 HYPE tokens can launch perpetual futures markets
2. **Wide Asset Support**: Supports cryptocurrencies, **equities**, commodities, indices, and forex pairs
3. **Customizable Markets**: Independent margining, order books, and parameters
4. **Decentralized Infrastructure**: Lowers barriers to entry and trading costs

**Activated**: October 13, 2025

---

## Key Findings

### HIP-3 Supports Equities

According to documentation:
> "HIP-3 supports perpetual contracts on a wide range of assets, including cryptocurrencies, **equities**, commodities, indices, and forex pairs."

This means tokenized stocks like Tesla and SpaceX **could** be available via HIP-3 markets.

### Current Token Discovery Results

**Standard Universe Query**: 224 tokens found, all crypto/meme tokens
- No stocks found (Tesla, SpaceX, etc.)
- No HIP-3 markets visible in standard API response

**Possible Reasons**:
1. HIP-3 markets might be in a separate endpoint
2. HIP-3 markets might not be included in standard "universe" query
3. No HIP-3 equity markets have been deployed yet
4. HIP-3 markets might require different API calls

---

## Investigation Needed

### Questions to Answer

1. **Are HIP-3 markets included in the standard universe?**
   - Current test: No stocks found
   - Need to check: Separate endpoint or query parameter?

2. **How to query HIP-3 markets specifically?**
   - Is there a separate API endpoint?
   - Do we need different query parameters?
   - Are they in a different data structure?

3. **Have any equity markets been deployed via HIP-3?**
   - Check HIP-3 tracker/progress
   - Check community announcements
   - Check Hyperliquid documentation

4. **If HIP-3 markets exist, how do we discover them?**
   - Dynamic discovery mechanism
   - Separate subscription process
   - Different data structure

---

## Next Steps

1. **Check HIP-3 Tracker**: https://hip-3.xyz
2. **Query Different API Endpoints**: Look for HIP-3 specific endpoints
3. **Check Documentation**: Hyperliquid docs for HIP-3 market discovery
4. **Test WebSocket**: See if HIP-3 markets appear in WebSocket subscriptions

---

## Current Status

**Finding**: HIP-3 supports equities, but no stocks found in current token discovery

**Hypothesis**: 
- HIP-3 markets might not be in standard universe query
- May need separate discovery mechanism
- Or no equity markets deployed yet

**Action**: Need to investigate HIP-3 market discovery mechanism

