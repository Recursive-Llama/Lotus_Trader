# Test Results: Decimal and Transaction Parsing

## Test 1: Token Decimals ✅

### Result: **SUCCESS**

**Key Token**: `3nB5Ucpmcpruez9rgfEQNdd2eC9Nnj1VrDuheLQ3pump`

**Findings:**
- ✅ Token has **6 decimals** (not 9!)
- ✅ Token is **Token-2022** (not standard SPL token)
- ✅ Owner: `TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb`

**Why `get_token_decimals()` Fails:**
- `getMint()` from `@solana/spl-token` only works for **standard SPL tokens**
- Token-2022 tokens have different owner, so `getMint()` throws `TokenInvalidAccountOwnerError`
- Our code catches this and **defaults to 9 decimals** (wrong!)

**Solution:**
- Need to handle Token-2022 tokens
- Read decimals directly from account data (offset 44)
- Or use `@solana/spl-token` Token-2022 library

**Conversion Test:**
```
Raw amount: 14898822091
Correct (6 decimals): 14898.822091 tokens ✅
Wrong (9 decimals): 14.898822 tokens ❌
Wallet shows: 14897 tokens
Difference (correct): 1.822091 (fees/slippage)
Difference (wrong): 14882.101178 (1000x off!)
```

## Test 2: Transaction Parsing (Pending)

### Status: **Ready to Test**

**What We Need:**
1. Full transaction hash (logs show truncated: `JZwa5cNq...`)
2. Wallet address (can derive from private key or get from transaction)

**What Transaction Parsing Will Show:**
- Actual amount received (not quote estimate)
- Actual decimals used (from transaction metadata)
- Accounts for fees/slippage automatically

**How to Test:**
```bash
# Get full transaction hash from logs or database
# Then run:
node test_transaction_parsing.js <full_tx_hash> [wallet_address]
```

## Summary of Issues

### Issue 1: Decimal Problem ✅ IDENTIFIED

**Root Cause:**
- Token is Token-2022, not standard SPL
- `getMint()` fails for Token-2022
- Code defaults to 9 decimals (wrong)
- Token actually has 6 decimals

**Fix:**
- Handle Token-2022 tokens in `get_token_decimals()`
- Read decimals from account data directly
- Or use Token-2022 library

### Issue 2: Quote vs Actual Amount ⏳ TO TEST

**Hypothesis:**
- We use `quoteResponse.data.outAmount` (estimate)
- Actual amount may differ due to slippage/fees
- This causes simulation errors when selling

**Fix:**
- Parse transaction to get actual amount received
- Use transaction parsing (like Li.Fi does)
- Update position with actual amount

## Next Steps

1. ✅ **Fix `get_token_decimals()`** to handle Token-2022
2. ⏳ **Test transaction parsing** with actual buy transaction
3. ⏳ **Compare quote vs actual** amounts
4. ⏳ **Implement transaction parsing** in buy/sell functions

