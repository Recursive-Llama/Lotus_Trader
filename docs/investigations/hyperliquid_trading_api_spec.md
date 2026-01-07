# Hyperliquid Trading API - Detailed Specification

**Date**: 2025-12-31  
**Status**: Specification Document  
**Based on**: Hyperliquid API Documentation + Test Results

---

## API Endpoints

### 1. Info Endpoint (No Auth Required)

**URL**: `POST https://api.hyperliquid.xyz/info`

**Purpose**: Query market data, account info, positions (read-only)

**Common Request Types**:
- `{"type": "meta"}` - Main DEX universe
- `{"type": "meta", "dex": "<dex_name>"}` - HIP-3 DEX universe
- `{"type": "perpDexs"}` - List of HIP-3 DEXs
- `{"type": "clearinghouseState", "user": "0x<address>"}` - Account state (positions, balances)
- `{"type": "candleSnapshot", "req": {...}}` - Historical candles
- `{"type": "metaAndAssetCtxs"}` - Market context (mark price, funding, OI)

---

### 2. Exchange Endpoint (Auth Required)

**URL**: `POST https://api.hyperliquid.xyz/exchange`

**Purpose**: Place orders, manage positions

**Authentication**: Wallet signature required

---

## Asset ID Computation

### Main DEX Assets

**Formula**: Asset ID = index in `universe` array (0-based)

**Example**:
- BTC at index 0 → Asset ID = 0
- ETH at index 1 → Asset ID = 1

**Query**:
```json
POST /info
{"type": "meta"}
```

**Response**:
```json
{
  "universe": [
    {"name": "BTC", "szDecimals": 5, "maxLeverage": 40, "marginTableId": 56},
    {"name": "ETH", "szDecimals": 4, "maxLeverage": 25, "marginTableId": 55},
    ...
  ]
}
```

### HIP-3 Assets

**Formula**: `asset_id = 100000 + dex_index * 10000 + coin_index`

**Steps**:
1. Query `{"type": "perpDexs"}` to get DEX list
2. Find DEX index in array (0-based)
3. Query `{"type": "meta", "dex": "<dex_name>"}` to get DEX universe
4. Find coin index in DEX universe (look for `"dex:coin"` format)
5. Compute: `100000 + dex_index * 10000 + coin_index`

**Example**: `xyz:TSLA`
- DEX "xyz" at index 1 in perpDexs
- Coin "xyz:TSLA" at index 1 in xyz universe
- Asset ID = 100000 + 1 * 10000 + 1 = 110001

---

## Asset Metadata

Each asset in universe has:

```typescript
{
  name: string;              // "BTC" or "xyz:TSLA"
  szDecimals: number;        // Decimal places for size (e.g., 5 for BTC)
  maxLeverage: number;       // Maximum leverage (e.g., 40 for BTC)
  marginTableId: number;    // Margin table reference
  isDelisted?: boolean;     // If asset is delisted
  onlyIsolated?: boolean;    // If only isolated margin allowed
  marginMode?: string;       // Margin mode (e.g., "strictIsolated")
  growthMode?: string;       // Growth mode (e.g., "enabled")
}
```

**Key Fields**:
- `szDecimals`: Critical for order size formatting (must match decimals)
- `maxLeverage`: Maximum leverage allowed (0.0 for spot, or 1-50x for perps)
- `onlyIsolated`: If true, only isolated margin allowed

---

## Order Format (Expected)

Based on typical perpetual exchange APIs and Hyperliquid structure:

### Request Structure

```json
{
  "action": {
    "type": "order",
    "orders": [
      {
        "a": 0,                    // Asset ID (integer)
        "b": true,                 // Buy (true) or Sell (false)
        "p": "100000",             // Price (string, for limit orders)
        "s": "0.1",                // Size (string, in contracts, with szDecimals)
        "r": false,                // Reduce-only (true = only close position)
        "t": {                     // Order type
          "limit": {
            "tif": "Gtc"           // Time-in-force: "Gtc", "Ioc", "Alo"
          }
        }
      }
    ],
    "grouping": "na"               // Order grouping: "na" (none)
  },
  "nonce": 1234567890,             // Nonce (timestamp or counter)
  "signature": {
    "r": "0x...",                  // Signature r component
    "s": "0x...",                  // Signature s component
    "v": 27                        // Signature v component
  }
}
```

### Order Types

**Market Order**:
```json
{
  "t": {
    "market": {}
  }
}
```

**Limit Order**:
```json
{
  "t": {
    "limit": {
      "tif": "Gtc"  // Good-till-cancel
      // or "Ioc"   // Immediate-or-cancel
      // or "Alo"   // Allow limit orders only
    }
  },
  "p": "100000"     // Limit price (string)
}
```

**Stop Order** (if supported):
```json
{
  "t": {
    "stop": {
      "triggerPx": "100000",  // Trigger price
      "isMarket": true,       // Market or limit stop
      "tif": "Gtc"
    }
  }
}
```

### Size Format

**Important**: Size must match `szDecimals` from asset metadata

- BTC: `szDecimals = 5` → Size: `"0.00001"` (5 decimals)
- ETH: `szDecimals = 4` → Size: `"0.0001"` (4 decimals)
- xyz:TSLA: `szDecimals = 3` → Size: `"0.001"` (3 decimals)

**Calculation**:
```python
# Convert notional USD to contract size
notional_usd = 100.0  # $100
price = 50000.0       # $50,000 per BTC
contract_size = notional_usd / price  # 0.002 BTC

# Format with szDecimals
sz_decimals = 5  # From asset metadata
formatted_size = f"{contract_size:.{sz_decimals}f}"  # "0.00200"
```

---

## Authentication

### Agent Wallet System

**Architecture**:
- **Main Wallet**: Holds funds, authorizes agent wallets
- **Agent Wallet**: Has private key, authorized by main wallet to trade
- **Security**: Agent wallet cannot withdraw funds (even if compromised)

**Setup Steps**:
1. Create Hyperliquid account (main wallet)
2. Generate API wallet (agent wallet) in Hyperliquid app
3. Authorize agent wallet for trading
4. Use agent wallet private key for API calls

### Wallet Signature

**Method**: EIP-712 signature (confirmed)

**Steps**:
1. Construct order payload
2. Generate nonce (timestamp in milliseconds)
3. Create EIP-712 typed data structure
4. Sign with agent wallet private key
5. Include signature in request

**Signature Format**:
```json
{
  "r": "0x...",  // 32 bytes hex
  "s": "0x...",  // 32 bytes hex
  "v": 27        // Recovery ID (27 or 28)
}
```

**Nonce**:
- Timestamp in milliseconds
- Must be unique per order
- Used to prevent replay attacks

### Python SDK

**Official SDK**: `hyperliquid-python-sdk`

**Installation**:
```bash
pip install hyperliquid-python-sdk
```

**Usage**:
```python
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# Info API (read-only)
info = Info(constants.MAINNET_API_URL, skip_ws=True)

# Exchange API (trading)
exchange = Exchange(
    account_address="0x<main_wallet>",
    secret_key="<agent_wallet_private_key>",
    base_url=constants.MAINNET_API_URL
)
```

**Testnet**:
- Use `constants.TESTNET_API_URL` for testing
- Testnet available for safe testing

---

## Position Management

### Query Positions

**Endpoint**: `POST /info`

**Request**:
```json
{
  "type": "clearinghouseState",
  "user": "0x<wallet_address>"
}
```

**Response** (Expected):
```json
{
  "assetPositions": [
    {
      "position": {
        "coin": "BTC",
        "entryPx": "50000.0",
        "leverage": {
          "value": "1.0"  // Leverage (1.0 = no leverage)
        },
        "liquidationPx": "45000.0",
        "marginUsed": "100.0",
        "px": "51000.0",  // Current mark price
        "szi": "0.002",   // Position size (positive = long, negative = short)
        "unrealizedPnl": "2.0"
      },
      "type": "oneWay"
    }
  ],
  "crossMaintenanceMarginUsed": "0.0",
  "crossMarginSummary": {
    "accountValue": "1000.0",
    "totalMarginUsed": "100.0",
    "totalNtlPos": "100.0",
    "totalRawUsd": "1000.0"
  }
}
```

### Close Position

**Method**: Place order with `reduceOnly: true`

**Example**:
```json
{
  "a": 0,        // Asset ID
  "b": false,    // Sell (if long position)
  "s": "0.002",  // Size to close (match position size)
  "r": true,     // Reduce-only (only close, no new position)
  "t": {
    "market": {}
  }
}
```

---

## Constraints

### Min Notional

**Unknown**: Need to test or check docs

**Likely**: $1-10 USD minimum per order

### Leverage

**From Asset Metadata**: `maxLeverage` field

**Examples**:
- BTC: maxLeverage = 40 (up to 40x)
- ETH: maxLeverage = 25 (up to 25x)
- xyz:TSLA: maxLeverage = 10 (up to 10x)

**For Spot Trading**: Use `leverage = 0.0` or `1.0`

### Reduce-Only

**Rule**: If `reduceOnly: true`, order can only reduce position size
- Cannot open new position
- Cannot increase position size
- Can only close or reduce existing position

### Margin Modes

**Cross Margin**: Uses entire account balance as collateral
**Isolated Margin**: Allocates specific collateral to position

**Note**: Some assets have `onlyIsolated: true` (must use isolated margin)

---

## Error Handling

### Common Errors

**Insufficient Balance**:
```json
{
  "status": "err",
  "response": {
    "type": "error",
    "data": "Insufficient balance"
  }
}
```

**Invalid Asset ID**:
```json
{
  "status": "err",
  "response": {
    "type": "error",
    "data": "Invalid asset"
  }
}
```

**Invalid Size**:
```json
{
  "status": "err",
  "response": {
    "type": "error",
    "data": "Size too small" or "Invalid size format"
  }
}
```

**Market Closed / Maintenance**:
```json
{
  "status": "err",
  "response": {
    "type": "error",
    "data": "Market closed" or "Maintenance"
  }
}
```

---

## Testing Strategy

### Phase 1: Read-Only Tests (No Auth) ✅ COMPLETE
- ✅ Query universe (224 assets)
- ✅ Query perpDexs (6 DEXs)
- ✅ Compute asset IDs (main DEX + HIP-3)
- ✅ Get asset metadata (szDecimals, maxLeverage, etc.)
- ✅ Query order book
- ✅ Query market context

**Results**: See `docs/investigations/hyperliquid_trading_api_test_results.md`

### Phase 2: Auth Setup ⏭️ NEXT
- Create Hyperliquid account (main wallet)
- Generate agent wallet in Hyperliquid app
- Authorize agent wallet for trading
- Get agent wallet private key
- Test signature generation

### Phase 3: Order Tests (With Auth)
- Test order format validation
- Test small market order (testnet)
- Test limit order (testnet)
- Test reduce-only order
- Test error cases

### Phase 4: Position Tests
- Query positions
- Test position closing
- Test position updates

---

## Implementation Notes

### For Executor

1. **Asset ID Lookup**:
   - Cache universe and perpDexs on startup
   - Compute asset IDs on-demand
   - Handle both main DEX and HIP-3

2. **Size Formatting**:
   - Get `szDecimals` from asset metadata
   - Convert notional USD → contract size
   - Format with correct decimals

3. **Order Construction**:
   - Build order payload
   - Generate nonce
   - Sign with wallet
   - Send to `/exchange`

4. **Error Handling**:
   - Parse error responses
   - Handle retries (if appropriate)
   - Log errors for debugging

---

## Python SDK Integration

### Using Official SDK

**Advantages**:
- Handles authentication automatically
- Manages signatures and nonces
- Type-safe interfaces
- Built-in error handling

**Example Order Placement**:
```python
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

exchange = Exchange(
    account_address="0x<main_wallet>",
    secret_key="<agent_wallet_private_key>",
    base_url=constants.MAINNET_API_URL
)

# Place market order
result = exchange.order(
    coin="BTC",
    is_buy=True,
    sz=0.001,  # Size in contracts
    limit_px=None,  # None for market order
    order_type={"limit": {"tif": "Gtc"}},  # or {"market": {}}
    reduce_only=False,
    leverage=1.0  # 1.0 = no leverage
)
```

**Query Positions**:
```python
from hyperliquid.info import Info

info = Info(constants.MAINNET_API_URL, skip_ws=True)
user_state = info.user_state("0x<main_wallet>")
positions = user_state.get("assetPositions", [])
```

### Custom Implementation

If not using SDK, need to:
1. Implement EIP-712 signing
2. Generate nonces
3. Format orders correctly
4. Handle errors

---

## Resources

- Hyperliquid Docs: https://hyperliquid.gitbook.io/hyperliquid-docs/
- Python SDK: https://github.com/hyperliquid-dex/hyperliquid-python-sdk
- API Reference: https://docs.hypereth.io/api-reference/
- Trading Guide: https://www.hyperliquid.review/guides/api-trading
- EIP-712: Ethereum typed data signing standard

---

## Open Questions

1. **Exact Order Format**: Verify field names with SDK or docs
2. **Min Notional**: What's the minimum order size per asset?
3. **Rate Limits**: What are the API rate limits?
4. **Order Status**: How to check order status/fills?
5. **Partial Fills**: How are partial fills handled?
6. **Slippage**: How is slippage calculated and reported?

