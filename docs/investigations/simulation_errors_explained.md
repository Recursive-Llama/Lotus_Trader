# Solana Transaction Simulation Errors - Explained

## What is Transaction Simulation?

**Transaction simulation** is Solana's way of testing a transaction **before** actually sending it to the network. It's like a "dry run" that checks if the transaction would succeed.

### How It Works

1. **Before sending**: Solana runs the transaction through a virtual execution environment
2. **Checks**: 
   - Will the transaction execute successfully?
   - Do you have enough balance?
   - Will slippage be within tolerance?
   - Are all accounts valid?
   - Will the program logic execute correctly?
3. **If simulation fails**: Transaction is **NOT sent** - you get an error immediately
4. **If simulation passes**: Transaction is sent to the network

### In Our Code

Looking at `js_solana_client.py`:
```javascript
const signature = await connection.sendTransaction(transaction, {
    skipPreflight: false,  // ← This means "run simulation first"
    preflightCommitment: 'processed'
});
```

**`skipPreflight: false`** means:
- ✅ Run simulation first (preflight check)
- ✅ Only send transaction if simulation passes
- ❌ If simulation fails, throw error immediately (transaction never sent)

## Why Simulation Fails

### Common Causes

1. **Slippage Tolerance Exceeded** (most common)
   - Price moved between quote and execution
   - Example: Quote said you'd get 100 tokens, but simulation shows you'd only get 95
   - Error: `custom program error: 0x1788` (Jupiter's slippage error)

2. **Insufficient Liquidity**
   - Not enough tokens in the pool for your trade size
   - Especially common with large positions or low-liquidity tokens

3. **Decimal/Precision Issues** (we fixed this)
   - If we had `14.898822123456789` tokens and tried to convert to raw units
   - Could cause rounding errors that make simulation fail
   - **Fixed**: We now round to 4 decimal places before conversion

4. **Account State Issues**
   - Token account doesn't exist or isn't initialized
   - Account balance changed between quote and execution
   - Account is frozen or has restrictions

5. **Program Logic Errors**
   - Jupiter program itself rejects the transaction
   - Route calculation issues
   - Invalid instruction parameters

## Error 0x1788 Specifically

**0x1788** is Jupiter's error code for:
- Slippage tolerance exceeded
- Route calculation failed
- Insufficient output amount

**Most likely cause for KEY token:**
- Price moved significantly between quote and execution
- Large position size (14.898822 tokens) hitting liquidity limits
- Low liquidity pool for this token

**Could decimal places have been the issue?**
- Possibly, but less likely:
  - We had `14.898822` tokens (6 decimal places)
  - Converting to raw units: `14.898822 * 10^9 = 14898822000` (if 9 decimals)
  - This should be fine, but rounding to 4 decimals (`14.8988`) is safer
  - **We fixed it anyway**, so we'll see if it helps

## Why Simulation Errors Are "Safe" to Retry

**Key Point**: Simulation happens **BEFORE** the transaction is sent.

### What This Means:
- ✅ **No transaction sent** = No on-chain activity
- ✅ **No gas fees spent** = No cost for failed simulation
- ✅ **No state changes** = Nothing happened, safe to retry
- ✅ **Just a check** = Like asking "would this work?" before doing it

### Why We Could Retry More:
- **No risk**: We're not sending anything, just checking
- **Price might settle**: Wait a moment, price might stabilize
- **Liquidity might improve**: Pool might get more liquidity
- **Network might be busy**: Retry when network is less congested

### Current Retry Strategy:
- 3 attempts total (initial + 2 retries)
- Increasing slippage: 50 → 300 → 600 bps
- 1 second delay between retries

### Could We Do More?
**Yes, but with limits:**
- Maybe 5-10 attempts for simulation errors only
- Keep increasing slippage (but cap at reasonable level, e.g., 10% = 1000 bps)
- Add longer delays between retries (let price settle)
- **But**: Don't retry forever - if it fails 10 times, something is wrong

## Confirmation Timeout Behavior

### Current Code
```javascript
const confirmation = await connection.confirmTransaction(signature, 'confirmed');
```

**What `confirmTransaction` does:**
- Waits for transaction to be confirmed on-chain
- Default timeout: **~30-60 seconds** (depends on Solana web3.js version)
- If timeout: Returns error or null
- If confirmed: Returns confirmation object

### Your 3-Minute Example
You said "no confirmation in 3 minutes means definitely failure" - this is a good heuristic:
- Solana transactions usually confirm in **~1-5 seconds**
- If it takes longer than **30-60 seconds**, something is likely wrong
- **3 minutes** is very conservative (most transactions fail or succeed much faster)

### Current Behavior
1. **Simulation passes** → Transaction sent → `confirmTransaction` waits
2. **If confirmed within timeout** → Success ✅
3. **If timeout** → Error returned → Triggers our retry logic ✅
4. **If transaction fails on-chain** → Error returned → Triggers our retry logic ✅

**This is actually what we want!** The timeout handles the "wait to know it failed" part automatically.

### Do We Need Explicit 3-Minute Timeout?
**Probably not**, because:
- `confirmTransaction` already has a timeout (30-60s default)
- If it times out, we get an error and retry
- If we want longer timeout, we can add it, but 3 minutes is probably overkill
- Most failures happen much faster (simulation fails immediately, or transaction fails within seconds)

## Summary

### Simulation Errors:
- **What they are**: Pre-flight checks before sending transaction
- **Why they fail**: Slippage, liquidity, price movement, precision issues
- **Why safe to retry**: No transaction sent, no cost, just a check
- **Could retry more**: Yes, especially for simulation-only errors (maybe 5-10 attempts)

### Decimal Places:
- **Could have been the issue**: Possibly, but less likely
- **We fixed it**: Rounding to 4 decimal places before conversion
- **Will help**: Especially for expensive tokens with small amounts

### Confirmation Timeout:
- **Current behavior**: `confirmTransaction` already waits with timeout
- **Default timeout**: ~30-60 seconds (varies by Solana web3.js version)
- **This is fine**: If it times out, we get error and retry
- **3 minutes**: Probably overkill, but we could add it if needed

## Recommendation

1. **Keep current retry strategy** (3 attempts) for now
2. **Monitor logs** to see:
   - How often simulation errors happen
   - How often retries succeed
   - What slippage levels work
3. **Consider more retries for simulation-only errors**:
   - If error is "Simulation failed" (not "Transaction failed")
   - Maybe 5-10 attempts with increasing slippage
   - Add longer delays (2-5 seconds) to let price settle
4. **Track metrics**:
   - Retry success rate
   - Average slippage needed
   - Which errors are most common

