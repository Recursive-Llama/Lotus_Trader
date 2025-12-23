# Fixes Needed - Summary from Tests

## Issue 1: Token Decimals (Token-2022 Support)

### Problem
- **Token-2022 tokens** (like KEY) have different owner than standard SPL tokens
- `getMint()` from `@solana/spl-token` fails for Token-2022 → throws `TokenInvalidAccountOwnerError`
- Code defaults to **9 decimals** (wrong)
- Token actually has **6 decimals**

### Test Results
- ✅ Token has **6 decimals** (confirmed from account data)
- ❌ Code uses **9 decimals** (wrong, causes 1000x error)

### Fix Needed
**Location**: `src/trading/js_solana_client.py` - `get_token_decimals()` method

**Current Code** (lines 261-330):
```javascript
try {
    const mintInfo = await getMint(connection, mintAddress);
    return { success: true, decimals: mintInfo.decimals };
} catch (error) {
    // Defaults to 9 if account not found
    if (error.message.includes('could not find account') || ...) {
        return { success: true, decimals: 9 };  // ❌ WRONG DEFAULT
    }
}
```

**Fix**:
1. When `getMint()` fails, try reading account data directly
2. For Token-2022, decimals are at offset 44 in account data
3. Only default to 9 if we truly can't determine decimals

**Implementation**:
```javascript
try {
    const mintInfo = await getMint(connection, mintAddress);
    return { success: true, decimals: mintInfo.decimals };
} catch (splError) {
    // Try Token-2022 or read account directly
    const accountInfo = await connection.getAccountInfo(mintAddress);
    if (accountInfo && accountInfo.data.length >= 45) {
        const decimals = accountInfo.data.readUInt8(44);
        return { success: true, decimals: decimals };
    }
    // Only default if we truly can't get it
    return { success: true, decimals: 9 };
}
```

---

## Issue 2: Using Quote Amount Instead of Actual Amount

### Problem
- We use `outputAmount` from Jupiter **quote** (estimate)
- Quote is calculated **before** transaction executes
- Actual amount may differ due to:
  - Slippage
  - Fees
  - Price movement
  - Route changes

### Test Results
- ✅ Transaction parsing works perfectly
- ✅ Gets **actual amount** from transaction metadata
- ✅ Gets **correct decimals** from transaction metadata
- ✅ Matches what's in wallet

### Fix Needed
**Location**: `src/intelligence/lowcap_portfolio_manager/pm/executor.py` - `_execute_solana_buy_usdc_to_token()` method

**Current Flow** (lines 665-700):
```python
# After swap succeeds:
tx_hash = result.get('signature')  # ✅ We have this!
output_amount_raw = result.get('outputAmount', 0)  # ❌ This is from QUOTE
token_decimals = decimals_result.get('decimals', 9)  # ❌ May be wrong
tokens_received = float(output_amount_raw) / (10 ** token_decimals)  # ❌ Wrong!
```

**Fix**:
1. After swap succeeds, **immediately parse the transaction**
2. Extract actual amount from `postTokenBalances - preTokenBalances`
3. Get decimals from transaction metadata (always correct)
4. Use actual amount (not quote)

**Implementation**:
```python
# After swap succeeds:
tx_hash = result.get('signature')

# Parse transaction to get ACTUAL amount
actual_result = await self._parse_solana_transaction_for_token_delta(
    tx_hash=tx_hash,
    token_mint=token_contract,
    wallet_address=self.wallet_address
)

if actual_result:
    tokens_received = actual_result['amount']  # ✅ Actual amount
    token_decimals = actual_result['decimals']  # ✅ From transaction
    tokens_received_raw = actual_result['rawAmount']
else:
    # Fallback to quote (shouldn't happen, but safety)
    output_amount_raw = result.get('outputAmount', 0)
    token_decimals = decimals_result.get('decimals', 9)
    tokens_received = float(output_amount_raw) / (10 ** token_decimals)
```

**New Method Needed**: `_parse_solana_transaction_for_token_delta()`
- Similar to `deriveSolanaTokenDelta()` in `lifi_executor.mjs`
- Parse transaction using `getParsedTransaction()`
- Extract token balance delta from metadata
- Return: `{ amount, rawAmount, decimals }`

---

## Issue 3: Emergency Exit Failure

### Problem
- We stored wrong amount in database (14.898822 instead of 14897)
- When selling, we calculate: `14.898822 * 10^9 = 14898822000` raw
- If token has 6 decimals, that's `14898.822` tokens
- We're trying to sell **more than we have** (14898.822 > 14897)
- Simulation fails

### Root Cause
- Combination of Issue 1 (wrong decimals) + Issue 2 (quote amount)
- Database has wrong amount because we used wrong decimals

### Fix
- Fix Issues 1 & 2 → database will have correct amount
- Emergency exits will work because we'll try to sell correct amount

---

## Summary of All Fixes

### Fix 1: Handle Token-2022 Decimals
**File**: `src/trading/js_solana_client.py`
**Method**: `get_token_decimals()`
**Change**: Read decimals from account data when `getMint()` fails

### Fix 2: Parse Transaction for Actual Amount
**File**: `src/intelligence/lowcap_portfolio_manager/pm/executor.py`
**Method**: `_execute_solana_buy_usdc_to_token()`
**Change**: 
- Add `_parse_solana_transaction_for_token_delta()` method
- After swap, parse transaction immediately
- Use actual amount (not quote)

### Fix 3: Same for Sell Operations
**File**: `src/intelligence/lowcap_portfolio_manager/pm/executor.py`
**Method**: `_execute_solana_sell_token_to_usdc()`
**Change**: 
- Also parse transaction after sell
- Verify actual amount sold matches expected

### Benefits
1. ✅ **Correct decimals** - from transaction metadata (always right)
2. ✅ **Actual amounts** - not estimates (matches wallet)
3. ✅ **Emergency exits work** - we have correct amounts in database
4. ✅ **No more 1000x errors** - decimals are always correct
5. ✅ **No more simulation failures** - we sell correct amounts

---

## Implementation Order

1. **First**: Fix Token-2022 decimals (Fix 1)
   - Quick win, fixes immediate decimal issue
   - Can be done independently

2. **Second**: Add transaction parsing (Fix 2)
   - More comprehensive fix
   - Fixes both decimal AND amount issues
   - Requires new method

3. **Third**: Apply to sell operations (Fix 3)
   - Same pattern as buy
   - Ensures consistency

---

## Testing

After fixes:
1. Execute a buy → verify database has correct amount
2. Check wallet → should match database
3. Execute emergency exit → should work (correct amount)
4. Verify no more decimal errors in logs

