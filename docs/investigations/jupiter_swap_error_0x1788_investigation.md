# Jupiter Swap Error 0x1788 Investigation

## Summary

**Key**: `3nB5Ucpmcpruez9rgfEQNdd2eC9Nnj1VrDuheLQ3pump` (KEY)  
**Timeframe**: 15m  
**Issue**: Emergency exit (full position sell) failing with two different errors:
1. Async event loop error: "This event loop is already running"
2. Jupiter simulation error: 0x1788

## Actual Timeline from Logs

### Dec 19 17:00:26 - Successful Entry Buy
```
EXEC START: entry KEY/solana tf=15m size_frac=0.3283 | position_qty=0.000000 status=watchlist | flag=buy_signal state=S1
EXEC OK: add/entry KEY/solana tf=15m | tx=JZwa5cNq... | tokens=14.898822 price=0.29995674 slippage=0.00%
```
- **State**: S1 (transitioned from S0→S1 earlier)
- **Result**: Successfully bought 14.898822 tokens
- **Position**: Changed from watchlist to active

### Dec 19 21:07:48 - First Emergency Exit Attempt (Failed - Async Error)
```
EXEC START: emergency_exit KEY/solana tf=15m size_frac=1.0000 | position_qty=14.898822 status=active | flag=exit_position state=S0
EXEC FAIL: sell KEY/solana tf=15m | err=This event loop is already running
```
- **State**: S0 (transitioned from S1→S0)
- **Error**: Async event loop issue
- **Position**: Still active with 14.898822 tokens

### Dec 20 13:15:25 - Second Emergency Exit Attempt (Failed - Jupiter 0x1788)
```
EXEC START: emergency_exit KEY/solana tf=15m size_frac=1.0000 | position_qty=14.898822 status=active | flag=exit_position state=S0
EXEC FAIL: sell KEY/solana tf=15m | err=Jupiter swap failed: Simulation failed. 
Message: Transaction simulation failed: Error processing Instruction 3: custom program error: 0x1788.
```
- **State**: S0 (still in S0 from previous transition)
- **Error**: Jupiter swap simulation failed with error 0x1788
- **Position**: Still active with 14.898822 tokens (sell failed)

### Dec 20 13:15:24 - Episode Summary Logged
```
ᛟ  EPISODE  | KEY (15m) s1_entry → correct_skip | Entered: False | samples:6
𒀭  STAGE    | KEY 🜂1 → 🜁0 (15m)
```
- **Episode outcome**: "correct_skip" (because `entered=False`)
- **State transition**: S1 → S0

## Error Pattern Analysis

### All Emergency Exits (size_frac=1.0)

| Token | Timeframe | Status | Error Type | Position Qty |
|-------|-----------|--------|------------|--------------|
| KEY | 15m | Failed | Async event loop | 14.898822 |
| KEY | 15m | Failed | Jupiter 0x1788 | 14.898822 |
| MACARON | 15m | Failed | No tokens (already sold) | 0.000000 |
| U1 | 15m | Failed | No tokens (already sold) | 0.000000 |
| KLED | 1h | Failed | Async event loop | 203.619431 |

### Partial Sells (size_frac < 1.0) - Trims

| Token | Timeframe | Status | size_frac | Result |
|-------|-----------|--------|-----------|--------|
| SPSC | 15m | ✅ Success | 0.1500 | Sold 127.698505 tokens |
| SPSC | 15m | ✅ Success | 0.1500 | Sold 251.192506 tokens |
| SPSC | 15m | ✅ Success | 0.0500 | Sold 213.513630 tokens |
| SPSC | 15m | ❌ Failed | 0.1500 | Async event loop error |
| RIFTS | 1h | ❌ Failed | 0.1500 | Async event loop error |
| RIFTS | 1h | ✅ Success | 0.1500 | Sold 684.564474 tokens |

**Key Finding**: Partial sells (trims) work fine when they don't hit the async error. The issue is NOT about selling all tokens vs partial - it's about two separate bugs:

1. **Async Event Loop Bug**: Affects both emergency_exit AND trim (random/intermittent)
2. **Jupiter 0x1788 Error**: Only seen on KEY emergency_exit (might be token-specific or amount-specific)

## Root Cause Analysis

### 1. Async Event Loop Error

**Location**: `src/intelligence/lowcap_portfolio_manager/pm/executor.py:648-691`

The code tries to handle async execution in a sync context:

```python
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

result = loop.run_until_complete(
    self.js_solana_client.execute_jupiter_swap(...)
)
```

**Problem**: If there's already a running event loop (which PM runs in), `asyncio.get_event_loop()` returns the running loop, but `loop.run_until_complete()` fails with "This event loop is already running" because you can't call `run_until_complete()` on a loop that's already running.

**Fix Needed**: Check if loop is running, and if so, either:
- Create a new event loop for this operation
- Use `asyncio.create_task()` and wait for it
- Use `asyncio.run()` which creates a new loop

### 2. Jupiter Error 0x1788

**Error**: `custom program error: 0x1788` during transaction simulation

**Possible Causes**:
- Slippage tolerance exceeded (price moved too much)
- Insufficient liquidity for the full position size
- Route calculation issues for large amounts
- Token account initialization issues (note "InitializeAccount3" in logs)

**Why only KEY?** Could be:
- Token-specific liquidity issues
- Amount-specific (14.898822 might be hitting a liquidity threshold)
- Timing (price volatility at that moment)

**Fix Needed**: 
- Add retry logic with higher slippage (like trim has)
- Log swap parameters (amount, slippage, route) for debugging
- Consider splitting large sells into smaller chunks

### 3. Episode "Entered: False" Explanation

The episode that ended on Dec 20 13:15 was a **NEW S1 episode** created AFTER the successful buy on Dec 19 17:00.

**Episode lifecycle:**
1. S1 episode is created when state transitions S0→S1 (with `started_at` timestamp)
2. Episode is marked as "entered" only if `last_s1_buy.timestamp >= episode.started_at`
3. The buy on Dec 19 17:00 happened during a DIFFERENT (earlier) S1 episode
4. A NEW S0→S1 transition happened later, creating a NEW episode
5. This NEW episode never had a buy (because `last_s1_buy` already existed from the Dec 19 buy, and PM doesn't buy again if `last_s1_buy` exists)
6. When this NEW episode ended (S1→S0 on Dec 20 13:15), it correctly showed "Entered: False"

**This is correct behavior** - the episode tracking is working as designed. The "correct_skip" outcome means: "We didn't enter during this episode, and the episode collapsed back to S0, so skipping was the right call."

## Current State

- **Position**: Active with 14.898822 tokens
- **Status**: `active` (not closed because sell failed)
- **State**: S0 (bearish, triggered emergency_exit)
- **Issue**: Position is stuck - can't exit because both sell attempts failed

## Recommendations

### Immediate Fixes

1. **Fix Async Event Loop Bug**:
   ```python
   # In _execute_solana_sell_token_to_usdc()
   try:
       loop = asyncio.get_event_loop()
       if loop.is_running():
           # Create new loop for this operation
           loop = asyncio.new_event_loop()
           asyncio.set_event_loop(loop)
           result = loop.run_until_complete(...)
           loop.close()
       else:
           result = loop.run_until_complete(...)
   except RuntimeError:
       loop = asyncio.new_event_loop()
       asyncio.set_event_loop(loop)
       result = loop.run_until_complete(...)
       loop.close()
   ```

2. **Add Retry Logic for Emergency Exits**:
   - Similar to trim, retry with higher slippage (300 bps) if simulation fails
   - Currently only trim has retry logic, emergency_exit doesn't

3. **Better Error Logging**:
   - Log swap parameters (amount, slippage, route) when Jupiter fails
   - Log token decimals and raw amounts for debugging

### Long-term Improvements

1. **Position Stuck Detection**: Alert when emergency_exit fails multiple times
2. **Sell Chunking**: For large positions, consider splitting into smaller sells
3. **Error Categorization**: Distinguish between retryable errors (slippage) vs non-retryable (no liquidity)

## Code Locations

- Solana sell execution: `src/intelligence/lowcap_portfolio_manager/pm/executor.py:648-691`
- Async event loop handling: `src/intelligence/lowcap_portfolio_manager/pm/executor.py:677-691`
- Jupiter swap execution: `src/trading/js_solana_client.py:134-259`
- Episode entry flag update: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py:987-1036`
- Episode outcome determination: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py:1132-1151`
