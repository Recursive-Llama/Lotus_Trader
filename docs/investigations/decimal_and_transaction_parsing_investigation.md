# Decimal and Transaction Parsing Investigation

## Key Findings

### 1. The Decimal Problem

**What We Know:**
- Logs show: `tokens_received=14.898822091` (from buy)
- Wallet shows: `14897` tokens (actual)
- **1000x difference** - confirms decimal issue

**What Happened:**
- Jupiter returned `outputAmount: 14898822091` (raw)
- We called `get_token_decimals()` which returned `9` (or defaulted to 9)
- We calculated: `14898822091 / 10^9 = 14.898822091` ❌
- **Should be**: `14898822091 / 10^6 = 14898.822091` ✅

**The Issue:**
- Token likely has **6 decimals**, not 9
- `get_token_decimals()` either:
  1. Failed and defaulted to 9
  2. Returned wrong value
  3. Token mint account doesn't exist or is inaccessible

### 2. Why Emergency Exit Failed

**The Problem:**
- Database stored: `14.898822` tokens (wrong - used 9 decimals)
- Wallet has: `14897` tokens (actual)
- When emergency exit runs:
  - Calculates: `tokens_to_sell = 14.898822 * 1.0 = 14.898822`
  - Converts to raw: `14.898822 * 10^9 = 14898822000` (if using 9 decimals)
  - But if token has 6 decimals, that's actually `14898.822` tokens
  - **We're trying to sell MORE than we have!** (14898.822 > 14897)
  - Simulation fails because we don't have enough tokens

**OR:**
- We're using wrong decimals for conversion, so the raw amount is wrong
- Jupiter simulation fails because the amount doesn't match what we actually have

### 3. Current Flow Issues

#### Issue 1: `get_token_decimals()` May Fail
**Location**: `js_solana_client.py:261-330`

**What Could Go Wrong:**
1. **Mint account doesn't exist**: Returns default 9
2. **RPC error**: Returns default 9
3. **Network timeout**: Returns default 9
4. **Token is not SPL token**: Returns default 9

**Code:**
```javascript
catch (error) {
    // If we can't get decimals, return a default of 9
    if (error.message.includes('could not find account') || 
        error.message.includes('Account does not exist') ||
        error.message === '') {
        return {
            success: true,
            decimals: 9,  // ⚠️ DEFAULT - might be wrong!
            mint: '{mint_address}'
        };
    }
}
```

**Problem**: We silently default to 9 without logging or validation!

#### Issue 2: We Use Quote Amount, Not Actual Transaction Amount
**Location**: `js_solana_client.py:205-211`

**What We Return:**
```javascript
return {
    success: true,
    signature: signature,
    inputAmount: quoteResponse.data.inAmount,      // From QUOTE (before execution)
    outputAmount: quoteResponse.data.outAmount,     // From QUOTE (before execution) ⚠️
    priceImpact: quoteResponse.data.priceImpactPct
};
```

**Problem**: 
- `outputAmount` is from the **quote** (simulation/estimate)
- **NOT from the actual transaction**
- Actual amount received may differ due to:
  - Slippage
  - Fees
  - Price movement between quote and execution
  - Route changes

### 4. Solution: Parse Transaction for Actual Amount

**We Already Have This!** - In `lifi_executor.mjs`

**Location**: `scripts/lifi_sandbox/src/lifi_executor.mjs:263-346`

**Function**: `deriveSolanaTokenDelta(parsedTx, mint, owner)`

**What It Does:**
1. Gets parsed transaction: `getParsedTransaction(txHash)`
2. Reads `preTokenBalances` and `postTokenBalances` from transaction metadata
3. Calculates delta: `postRaw - preRaw`
4. **Gets decimals from transaction metadata**: `postEntry.uiTokenAmount?.decimals`
5. Converts: `amount = rawDelta / (10 ** decimals)`

**Key Advantages:**
1. ✅ **Actual amount received** (not quote)
2. ✅ **Decimals from transaction** (not separate query)
3. ✅ **Accounts for fees/slippage** automatically
4. ✅ **More reliable** - transaction is source of truth

**Example:**
```javascript
const parsedTx = await client.getParsedTransaction(txHash, {
    commitment: 'finalized',
    maxSupportedTransactionVersion: 0,
});

const delta = deriveSolanaTokenDelta(parsedTx, tokenAddress, walletAddress);
// Returns: { amount: 14897.0, rawAmount: "14897000000", decimals: 6 }
```

### 5. Why Transaction Parsing is Better

**vs. Querying Mint Account:**
- ✅ Transaction has actual decimals used
- ✅ Transaction has actual amounts received
- ✅ No separate RPC call needed
- ✅ Works even if mint account is inaccessible

**vs. Using Quote Amount:**
- ✅ Actual amount (not estimate)
- ✅ Accounts for slippage/fees
- ✅ Matches what's in wallet

### 6. What We Should Do

#### Option A: Parse Transaction (Recommended)
1. After swap succeeds, parse the transaction
2. Extract actual token delta from `preTokenBalances` / `postTokenBalances`
3. Use decimals from transaction metadata
4. Use actual amount received

**Pros:**
- Most accurate
- Gets decimals automatically
- Accounts for all fees/slippage

**Cons:**
- Requires transaction to be finalized (small delay)
- Slightly more complex

#### Option B: Fix `get_token_decimals()` + Validate
1. Make `get_token_decimals()` more robust
2. Add validation: check if price makes sense
3. Try alternative decimals if price is wrong
4. Log warnings when defaulting

**Pros:**
- Simpler
- Faster (no need to wait for transaction)

**Cons:**
- Still uses quote amount (not actual)
- May still fail for some tokens

#### Option C: Both (Best)
1. Use quote amount initially (fast)
2. Parse transaction after it's finalized (accurate)
3. Update position with actual amount

**Pros:**
- Fast initial response
- Accurate final amount
- Best of both worlds

**Cons:**
- More complex
- Requires async update

### 7. Testing Plan

#### Test 1: Check `get_token_decimals()` for KEY Token
```bash
# Test if we can get decimals for KEY token
node -e "
const { Connection, PublicKey } = require('@solana/web3.js');
const { getMint } = require('@solana/spl-token');

async function test() {
    const connection = new Connection('https://api.mainnet-beta.solana.com');
    const mint = new PublicKey('3nB5Ucpmcpruez9rgfEQNdd2eC9Nnj1VrDuheLQ3pump');
    try {
        const mintInfo = await getMint(connection, mint);
        console.log('Decimals:', mintInfo.decimals);
    } catch (e) {
        console.error('Error:', e.message);
    }
}
test();
"
```

#### Test 2: Parse Actual Transaction
```bash
# Get the buy transaction hash from logs: JZwa5cNq...
# Parse it and see actual amount received
```

#### Test 3: Compare Quote vs Actual
- Get quote amount from Jupiter
- Execute swap
- Parse transaction
- Compare: quote amount vs actual amount
- Check if difference explains the issue

### 8. Questions to Answer

1. **Does `get_token_decimals()` work for KEY token?**
   - Test it directly
   - Check if it returns 6 or 9

2. **What does Jupiter quote return vs actual transaction?**
   - Compare quote `outAmount` vs actual balance change
   - Check if slippage/fees explain difference

3. **Should we parse transaction for all swaps?**
   - Yes - it's more accurate
   - We already have the code (in LiFi executor)
   - Just need to integrate it

4. **Is transaction parsing more complex?**
   - Not really - we have the code
   - Just need to call `getParsedTransaction()` and use `deriveSolanaTokenDelta()`

## Recommendations

1. **Immediate**: Add transaction parsing to get actual amount received
2. **Short-term**: Fix `get_token_decimals()` to be more robust and log failures
3. **Long-term**: Always use transaction parsing for accuracy, use quote only for estimates

## Next Steps

1. Test `get_token_decimals()` for KEY token
2. Parse the actual buy transaction (JZwa5cNq...) to see what we actually received
3. Compare quote vs actual amounts
4. Implement transaction parsing in `_execute_solana_buy_usdc_to_token()`

