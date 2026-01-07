# Hyperliquid Trading API - Findings

**Date**: 2025-12-31  
**Status**: In Progress  
**Purpose**: Document findings from testing Hyperliquid trading API

---

## Test Results

### ✅ Test 1: Info Endpoint

**Status**: ✅ Working

**Findings**:
- `/info` endpoint accessible without auth
- `type="meta"` returns universe with asset metadata
- Each asset has: `name`, `szDecimals`, `maxLeverage`, `marginTableId`
- Example: BTC has `maxLeverage: 40`, `szDecimals: 5`

**Response Structure**:
```json
{
  "universe": [
    {
      "name": "BTC",
      "szDecimals": 5,
      "maxLeverage": 40,
      "marginTableId": 56
    },
    ...
  ],
  "marginTables": [...],
  "collateralToken": {...}
}
```

---

### ✅ Test 2: Asset ID Computation

**Status**: ✅ Verified

**Findings**:

**Main DEX Assets**:
- Asset ID = index in universe array (0-based)
- Example: BTC is at index 0, so asset ID = 0
- ETH is at index 1, so asset ID = 1

**HIP-3 Assets**:
- Asset ID formula: `100000 + dex_index * 10000 + coin_index`
- HIP-3 tokens in universe use full format: `"dex:coin"` (e.g., `"xyz:TSLA"`)
- Steps:
  1. Query `type="perpDexs"` to get DEX list
  2. Find DEX index in perpDexs array
  3. Query `type="meta", dex="<dex_name>"` to get DEX universe
  4. Find coin index in DEX universe (look for `"dex:coin"` format)
  5. Compute: `100000 + dex_index * 10000 + coin_index`

**Example**:
- DEX "xyz" at index 1 in perpDexs
- Coin "xyz:TSLA" at index 1 in xyz universe
- Asset ID = 100000 + 1 * 10000 + 1 = 110001

**Key Fields from Assets**:
- `szDecimals`: Decimal places for size (important for order formatting)
- `maxLeverage`: Maximum leverage allowed
- `marginTableId`: Margin table reference

---

### ⚠️ Test 3: Account Info

**Status**: Requires Auth

**Findings**:
- Account queries require authentication
- Likely uses wallet signature (not API key)
- Need to check Hyperliquid docs for exact auth method

**Next Steps**:
- Review Hyperliquid docs for auth
- Set up wallet connection
- Test account info queries

---

### ⚠️ Test 4: Order Placement

**Status**: Requires Auth

**Findings**:
- Order placement requires authentication
- Need to verify exact order format
- Need to understand signature requirements

**Next Steps**:
- Review Hyperliquid docs for order format
- Test with small amounts (or testnet)
- Document exact field names and formats

---

### ⚠️ Test 5: Position Queries

**Status**: Requires Auth

**Findings**:
- Position queries require authentication
- Need to verify endpoint and format

**Next Steps**:
- Test position queries with auth
- Document response structure

---

### ✅ Test 6: Error Handling

**Status**: In Progress

**Findings**:
- Invalid requests return error responses
- Need to document error formats

**Next Steps**:
- Test various error cases
- Document error codes and messages

---

## Key Questions to Answer

1. **Authentication**:
   - [ ] How do we authenticate? (wallet signature? API key?)
   - [ ] What's the signature format?
   - [ ] Do we need to generate nonces?

2. **Order Format**:
   - [ ] Exact field names?
   - [ ] Asset ID format (integer? string?)
   - [ ] Size format (contracts? notional USD?)
   - [ ] Order types (market, limit, stop)?

3. **Constraints**:
   - [ ] Min notional per market?
   - [ ] Leverage limits?
   - [ ] Reduce-only rules?

4. **Testing**:
   - [ ] Is testnet available?
   - [ ] Can we use dry-run mode?
   - [ ] How to test without real execution?

---

## Resources

- Hyperliquid Docs: https://hyperliquid.gitbook.io/hyperliquid-docs/
- API Reference: [To be added]
- Testnet: [To be checked]

---

## Implementation Notes

**For Executor**:
- Need to implement asset ID computation
- Need to implement wallet signature
- Need to handle order formatting
- Need to handle error responses

**For Testing**:
- Start with testnet if available
- Use smallest possible amounts
- Test all error cases
- Document all findings

