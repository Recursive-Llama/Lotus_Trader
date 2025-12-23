# How Transaction Parsing Should Work

## Current Flow (WRONG)

1. Execute swap via Jupiter
2. Get result: `{ signature: tx_hash, outputAmount: quote_amount }`
3. **Use `outputAmount` from quote** (ESTIMATE) ❌
4. Try to get decimals separately (may fail)
5. Convert: `quote_amount / 10^decimals` (WRONG if decimals wrong)

**Problem**: We use quote amount (estimate) and wrong decimals

## How It SHOULD Work

1. Execute swap via Jupiter
2. Get result: `{ signature: tx_hash, outputAmount: quote_amount }`
3. **Use `tx_hash` we already have** ✅
4. Parse transaction: `getParsedTransaction(tx_hash)`
5. Extract actual amount from `postTokenBalances - preTokenBalances`
6. **Get decimals from transaction metadata** (always correct) ✅
7. Use actual amount (not quote)

**Result**: We get actual amount received, correct decimals, matches wallet

## The Key Point

**We ALREADY HAVE the transaction hash!** It's returned from `execute_jupiter_swap()` as `signature`.

We should:
1. Execute swap → get `tx_hash`
2. **Immediately parse that transaction** → get actual amount
3. Use actual amount (not quote)

No need to "go get" the hash - we have it right there!

## Implementation

After swap succeeds:
```python
# We have this:
tx_hash = result.get('signature')  # ✅ We have this!

# We should do this:
actual_amount = parse_transaction_for_actual_amount(tx_hash, token_contract, wallet_address)
# Returns: { amount: 14897.0, decimals: 6, rawAmount: "14897000000" }

# Use actual amount (not quote):
tokens_received = actual_amount['amount']  # ✅ Actual, not estimate
token_decimals = actual_amount['decimals']  # ✅ From transaction, always correct
```

## Why This Fixes Both Issues

1. **Decimal issue**: Transaction metadata has correct decimals (no need to query mint)
2. **Quote vs actual**: We use actual amount from transaction (not quote estimate)

## Test

The test should show:
- Execute a swap (or use existing tx_hash from logs)
- Parse transaction immediately using that hash
- Compare: quote amount vs actual amount
- Show the difference

No manual hash needed - use the one from swap execution!

