# Li.Fi EVM Chain Issue Investigation

## Problem Summary

1. **Buy Issue**: When buying tokens on EVM chains (Ethereum, Base, BSC) via cross-chain swap from Solana, the `tokens_received` value from Li.Fi appears to be incorrect (showing tiny values like `3.57180850165e-07` instead of actual amounts like `713.647634932`).

2. **Sell Issue**: When selling tokens, the system may be trying to sell from the Solana wallet instead of the EVM wallet where the tokens actually are.

## What We Know

1. **Buy Process**:
   - Swap initiated on Solana (USDC → target token)
   - Tokens are received on EVM address (e.g., Ethereum, Base, BSC)
   - Li.Fi returns `tokens_received` which may be from the first swap (USDC → native token like ETH) not the final amount

2. **Transaction Flow**:
   - Cross-chain swap: Solana USDC → EVM native token (ETH/WETH) → EVM target token
   - There are multiple transactions involved
   - We need to parse the **destination chain's transaction** to get the final token amount

3. **Solana Solution**:
   - For Solana, we parse the transaction hash directly using `deriveSolanaTokenDelta`
   - This correctly gets the final token amount
   - We do NOT fall back to `expectedOutput` if parsing fails

4. **EVM Current Behavior**:
   - `deriveEvmTokenDelta` should parse the destination chain transaction
   - If it returns null, we currently fall back to `expectedOutput` (which may be wrong)
   - This is different from Solana behavior

## Test Plan

### Test 1: Verify Transaction Parsing
Use `test_lifi_evm_output.js` to test with a real transaction:

```bash
node test_lifi_evm_output.js <chainId> <txHash> <tokenAddress> <walletAddress>
```

**Example** (from the user's transaction):
```bash
node test_lifi_evm_output.js 1 0x... 0x9Ac9468E7E3E1D194080827226B45d0B892C77Fd 0xF67F89A8...8bd940dcF
```

This will show:
- Whether the transaction receipt is found
- Whether Transfer events for the target token are found
- What the actual token delta is
- Whether the parsing is working correctly

### Test 2: Check Li.Fi Response
We need to log what Li.Fi actually returns:
- `tokens_received` value
- `tokens_received_raw` value  
- `to_token_decimals` value
- `price` value
- Transaction hash used

### Test 3: Verify Transaction Hash
For cross-chain swaps, verify:
- Are we using `destTxHash` (destination chain) or `sourceTxHash` (source chain)?
- Is the transaction hash we're parsing actually on the destination chain?
- Does the transaction contain the final token transfer?

### Test 4: Sell Issue
Check the sell execution:
- Which wallet address is being used for the sell?
- Is it using the EVM wallet or Solana wallet?
- What does Li.Fi receive as the `from_token` and `from_chain`?

## Next Steps

1. **Run the test script** with a real transaction to see what's happening
2. **Add logging** to capture:
   - What Li.Fi returns in the JSON response
   - Which transaction hash is being used
   - What `deriveEvmTokenDelta` finds (or doesn't find)
3. **Compare with Solana** - understand exactly how Solana handles this correctly
4. **Fix the root cause** once we understand what's actually happening

## Files to Check

- `scripts/lifi_sandbox/src/lifi_executor.mjs` - Li.Fi executor
- `src/intelligence/lowcap_portfolio_manager/pm/executor.py` - Python executor wrapper
- Transaction hashes from actual swaps (check logs)
