# Hyperliquid HIP-3 Market Access - Complete Guide

**Date**: 2025-12-31  
**Status**: ✅ Access Method Confirmed

---

## How to Access HIP-3 Markets

HIP-3 (builder-deployed) perp markets use the **same Hyperliquid API**, but require:
1. Discovering perp DEXs
2. Querying metadata for a specific DEX
3. Computing asset IDs using HIP-3 formula

---

## Step-by-Step Access

### Step 1: List All Perp DEXs

**Endpoint**: `POST https://api.hyperliquid.xyz/info`  
**Payload**: `{"type": "perpDexs"}`

**Returns**: Array of DEXs with fields:
- `name`: DEX identifier
- `fullName`: Full name
- `deployer`: Deployer address
- Other metadata

**Example Response**:
```json
[
  {
    "name": "main",
    "fullName": "Hyperliquid Main DEX",
    "deployer": "..."
  },
  {
    "name": "test",
    "fullName": "Test DEX",
    "deployer": "..."
  }
]
```

### Step 2: Get Markets for a Specific DEX

**Endpoint**: `POST https://api.hyperliquid.xyz/info`  
**Payload**: `{"type": "meta", "dex": "<DEX_NAME>"}`

**Returns**: Same structure as main universe, but for that DEX

**HIP-3 Coin Format**: `{dex}:{coin}` (e.g., `test:ABC`)

### Step 3: Compute Asset ID

**Formula**: `asset = 100000 + perp_dex_index * 10000 + index_in_meta`

Where:
- `perp_dex_index`: Index of DEX in `perpDexs` list (0-based)
- `index_in_meta`: Coin's index in that DEX's `meta.universe` (0-based)

**Example**:
- DEX at index 1 in `perpDexs`
- Coin at index 0 in that DEX's universe
- Asset ID = `100000 + 1 * 10000 + 0 = 110000`

### Step 4: Place Orders

**Endpoint**: `POST https://api.hyperliquid.xyz/exchange`  
**Action**: `type="order"` with `"a": <asset_id>`

Same order schema as main DEX.

### Step 5: Market Data

**Endpoint**: `POST https://api.hyperliquid.xyz/info`  
**Payload**: `{"type": "metaAndAssetCtxs", "dex": "<DEX_NAME>"}`

Returns mark/funding/OI contexts for that DEX.

---

## WebSocket Subscriptions

**Coin Format**: Use `{dex}:{coin}` format for subscriptions

**Example**:
```json
{
  "method": "subscribe",
  "subscription": {
    "type": "candle",
    "coin": "test:ABC",  // HIP-3 format
    "interval": "15m"
  }
}
```

---

## Implementation for Lotus Trader

### Token Discovery

1. **Query all DEXs**: `type="perpDexs"`
2. **For each DEX**:
   - Query markets: `type="meta", dex="<name>"`
   - Store DEX index for asset ID computation
   - Format coins as `{dex}:{coin}`

### Subscription Management

1. **Main DEX**: Use standard coin names (BTC, ETH, etc.)
2. **HIP-3 DEXs**: Use `{dex}:{coin}` format
3. **Same WebSocket**: All subscriptions go to same WebSocket

### Asset ID Computation

**For Trading**:
- Store `perp_dex_index` for each DEX
- Store `index_in_meta` for each coin
- Compute asset ID when placing orders

**For Data**:
- Use `{dex}:{coin}` format for WebSocket subscriptions
- Use same candle/OHLC format

---

## Current Status

**Testing**: Querying all DEXs to see what's available

**Next Steps**:
1. List all DEXs
2. Check for equity markets in HIP-3 DEXs
3. Test WebSocket subscription with `{dex}:{coin}` format
4. Implement DEX discovery in token management

---

## Key Points

✅ **Same API/WebSocket** - HIP-3 markets use same infrastructure  
✅ **Different Discovery** - Need to query perpDexs first  
✅ **Different Coin Format** - `{dex}:{coin}` instead of just coin name  
✅ **Asset ID Formula** - Need to compute for trading  
✅ **Same Data Format** - Candles/OHLC work the same way

