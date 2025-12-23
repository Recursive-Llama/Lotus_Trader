# Buy Flow - Decimal Handling Trace

## Current Flow (Step by Step)

### 1. Entry Point: `_execute_add()`
- **Location**: `executor.py:1445`
- **Input**: 
  - `usdc_amount`: float (e.g., 4.47)
  - `token_contract`: string (e.g., "3nB5Ucpmcpruez9rgfEQNdd2eC9Nnj1VrDuheLQ3pump")
- **Action**: Calls `_execute_solana_buy_usdc_to_token()`

### 2. Buy Execution: `_execute_solana_buy_usdc_to_token()`
- **Location**: `executor.py:562`
- **Input**:
  - `usdc_amount`: 4.47 (float)
  - `token_contract`: "3nB5Ucpmcpruez9rgfEQNdd2eC9Nnj1VrDuheLQ3pump"
  - `slippage_bps`: 50 (default)

#### Step 2a: Convert USDC to Raw
```python
usdc_amount_raw = int(usdc_amount * 1_000_000)  # USDC has 6 decimals
# 4.47 * 1_000_000 = 4,470,000
```

#### Step 2b: Execute Jupiter Swap
- **Calls**: `js_solana_client.execute_jupiter_swap()`
- **Input**: 
  - `input_mint`: USDC_MINT ("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
  - `output_mint`: token_contract
  - `amount`: 4,470,000 (raw USDC)
  - `slippage_bps`: 50

#### Step 2c: What Jupiter Returns
- **Location**: `js_solana_client.py:205-211`
- **Returns from JavaScript**:
```javascript
return {
    success: true,
    signature: signature,
    inputAmount: quoteResponse.data.inAmount,      // Raw USDC input
    outputAmount: quoteResponse.data.outAmount,     // Raw token output
    priceImpact: quoteResponse.data.priceImpactPct
};
```

**KEY QUESTION**: What format is `quoteResponse.data.outAmount`?
- It's from Jupiter's quote API response
- Jupiter quote API returns amounts in **raw units** (smallest unit of the token)
- **We don't know the decimals yet** - we haven't queried the token

#### Step 2d: Get Token Decimals
- **Location**: `executor.py:631-633` (AFTER swap)
- **Calls**: `js_solana_client.get_token_decimals(token_contract)`
- **Location**: `js_solana_client.py:261`
- **What it does**:
  - Uses `@solana/spl-token` `getMint()` to query the token's mint account
  - Returns: `{ success: true, decimals: <number> }`
  - **If it fails**: Returns `{ success: true, decimals: 9 }` (defaults to 9)

**PROBLEM**: If `get_token_decimals()` fails or returns wrong value, we default to 9 decimals

#### Step 2e: Convert Raw to Human-Readable
- **Location**: `executor.py:682`
```python
tokens_received = float(output_amount_raw) / (10 ** token_decimals)
```

**Example with KEY token**:
- `output_amount_raw` from Jupiter: `14898822091` (from logs)
- If `token_decimals = 9` (wrong): `14898822091 / 10^9 = 14.898822091` ❌
- If `token_decimals = 6` (correct): `14898822091 / 10^6 = 14898.822091` ✅
- Wallet shows: `14897` tokens

**The 1.8 token difference** (14898.8 vs 14897) could be:
- Fees deducted
- Slippage
- Rounding

### 3. What Information Do We Have?

#### From Jupiter:
- `outputAmount`: Raw amount in token's smallest units
- **Does NOT include decimals** - we must query separately

#### From `get_token_decimals()`:
- Token's actual decimals from on-chain mint account
- **But**: If query fails, defaults to 9 (which might be wrong!)

#### From Transaction:
- We have the transaction signature
- We could parse the transaction to see actual token balance changes
- But we're not doing this currently

## The Problem

1. **We get decimals AFTER the swap** - but we need them to convert correctly
2. **If `get_token_decimals()` fails, we default to 9** - but token might have 6 decimals
3. **We don't verify the conversion makes sense** - we just trust the decimals
4. **We don't check what Jupiter actually returned** - we assume `outAmount` is in raw units

## What We Should Check

1. **Does Jupiter quote API return decimals info?**
   - Check Jupiter API docs
   - Look at actual quote response structure

2. **Can we verify decimals from the transaction?**
   - Parse transaction to see actual balance changes
   - Compare with what we calculated

3. **Can we validate the conversion?**
   - If price is way off (< $0.0001 or > $1000), decimals are probably wrong
   - We know USDC spent, so we can calculate expected price

4. **What if `get_token_decimals()` fails?**
   - Should we try alternative methods?
   - Should we try common decimals (6, 8, 9, 18) and see which makes sense?

## Next Steps

1. **Check Jupiter API response** - does it include decimals?
2. **Check if `get_token_decimals()` is actually working** - look at logs
3. **Add validation** - check if converted amount makes sense
4. **Consider parsing transaction** - get actual balance change from on-chain data

