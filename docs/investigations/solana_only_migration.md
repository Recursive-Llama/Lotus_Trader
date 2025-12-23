# Solana-Only Migration Guide

## Overview

We've simplified the system to trade **Solana-only** using Jupiter directly, removing cross-chain complexity and Li.Fi issues.

## Changes Made

### 1. Social Ingest - Chain Filtering
**File:** `src/intelligence/social_ingest/social_ingest_basic.py`

**Change:** Only allows Solana chains
```python
self.allowed_chains = ['solana']  # Was: ['solana', 'ethereum', 'base', 'bsc']
```

**Easy Revert:** Just add chains back to the list:
```python
self.allowed_chains = ['solana', 'ethereum', 'base', 'bsc']
```

### 2. PMExecutor - Solana-Only Execution
**File:** `src/intelligence/lowcap_portfolio_manager/pm/executor.py`

**Changes:**
- Added `SolanaExecutor` initialization
- Added chain validation (rejects non-Solana)
- Will use Jupiter directly for Solana trades (implementation in progress)

**Chain Validation:**
```python
# SOLANA ONLY - Reject non-Solana chains
if chain not in self.allowed_chains:
    return {"status": "error", "error": f"Chain '{chain}' not allowed. Only Solana is supported."}
```

## Testing

### Test Script: `test_solana_jupiter_execution.py`

Tests Solana buy/sell execution in isolation to verify:
- ✅ Jupiter swaps work correctly
- ✅ Token decimals are handled properly
- ✅ Price calculations are accurate
- ✅ PnL tracking works
- ✅ All reporting data is correct

### Usage

**Buy test:**
```bash
python test_solana_jupiter_execution.py --token <TOKEN_MINT> --amount 10.0
```

**Sell test:**
```bash
python test_solana_jupiter_execution.py --token <TOKEN_MINT> --sell-amount 0.001
```

**Full round trip (buy then sell):**
```bash
python test_solana_jupiter_execution.py --token <TOKEN_MINT> --amount 10.0 --round-trip
```

**With custom slippage:**
```bash
python test_solana_jupiter_execution.py --token <TOKEN_MINT> --amount 10.0 --slippage 100
```

### What It Tests

1. **Buy Execution (USDC → Token)**
   - Converts USDC amount to raw units (6 decimals)
   - Executes Jupiter swap
   - Gets token decimals correctly
   - Calculates tokens received
   - Calculates price per token
   - Reports all metrics

2. **Sell Execution (Token → USDC)**
   - Gets token decimals
   - Converts tokens to raw units
   - Executes Jupiter swap
   - Calculates USDC received
   - Calculates price per token
   - Reports all metrics

3. **Round Trip Test**
   - Buys token with USDC
   - Sells all tokens back for USDC
   - Calculates PnL (including fees/slippage)
   - Verifies end-to-end flow

### Example Output

```
============================================================
TEST: Buy <TOKEN> with $10.00 USDC
============================================================
📊 Executing Jupiter swap: USDC → Token
   USDC Amount: $10.00 (10000000 raw)
   Token Mint: <TOKEN_MINT>
   Slippage: 50 bps (0.5%)

✅ Buy Execution Successful!
   TX Hash: <tx_hash>
   USDC Spent: $10.00
   Tokens Received: 0.123456
   Token Decimals: 9
   Price per Token: $81.00000000
   Price Impact: 0.15%
```

## Next Steps

1. ✅ Test buy/sell in isolation (this script)
2. ⏳ Integrate Jupiter execution into PMExecutor
3. ⏳ Update position tracking to use Jupiter results
4. ⏳ Verify PnL calculations match expectations
5. ⏳ Test with real positions

## Reverting to Multi-Chain

If you want to re-enable multi-chain trading:

1. **Social Ingest:**
   ```python
   self.allowed_chains = ['solana', 'ethereum', 'base', 'bsc']
   # Add back volume/liquidity requirements for other chains
   ```

2. **PMExecutor:**
   - Remove chain validation check
   - Li.Fi code is still there, just not used for Solana
   - Will automatically use Li.Fi for non-Solana chains

3. **No code deletion** - All Li.Fi code remains intact, just disabled for Solana

## Benefits

- ✅ **Simpler** - No cross-chain complexity
- ✅ **More reliable** - Jupiter is proven and stable
- ✅ **Better errors** - Clear error messages from Jupiter
- ✅ **Faster** - Direct swaps, no bridging
- ✅ **Lower fees** - No bridge fees
- ✅ **Easier debugging** - Single chain to troubleshoot

