# Retry Strategy Discussion - Emergency Exits & Sells

## Current State

### Existing Retry Logic (Old System)
- **Location**: `src/intelligence/trader_lowcap/solana_executor.py:69-88`
- **Pattern**: Single retry with higher slippage (300 bps = 3%)
- **Triggers**: "Simulation failed" or "custom program error"
- **Limitation**: Only in old executor, not in PM executor

### PM Executor (Current)
- **No retry logic** for emergency exits
- **No retry logic** for regular trims
- Fails immediately on Jupiter errors

## Key Questions to Answer

### 1. Which Errors Are Retryable?

**Retryable (Transient Issues):**
- ✅ `Simulation failed` / `custom program error: 0x1788` (slippage/liquidity - can retry with higher slippage)
- ✅ `This event loop is already running` (async bug - should be fixed, but could retry once)
- ✅ Network timeouts / connection errors
- ✅ Rate limiting (429 errors)

**NOT Retryable (Permanent Issues):**
- ❌ `No tokens to sell (total_quantity is 0)` (position already closed)
- ❌ `Insufficient balance` (fundamental issue, won't change)
- ❌ Invalid token address / contract errors
- ❌ Authentication/authorization errors

**Edge Cases:**
- ⚠️ `Insufficient liquidity` - Could be transient (wait and retry) or permanent (token is dead)
- ⚠️ `Slippage tolerance exceeded` - Could retry with higher slippage, but how high is too high?

### 2. How Many Retries?

**Options:**
- **Option A**: Single retry (like current old system)
  - Pros: Simple, fast, low risk
  - Cons: Might miss recoverable errors
  
- **Option B**: 2-3 retries with exponential backoff
  - Pros: Better chance of success on transient errors
  - Cons: Slower, more complex, risk of getting stuck
  
- **Option C**: Different retry counts for different error types
  - Pros: Most flexible
  - Cons: Most complex

**Recommendation**: Start with **Option A** (single retry) for emergency exits, expand if needed.

### 3. What to Change on Retry?

**Slippage Increase:**
- Current: 50 bps (0.5%)
- Retry 1: 300 bps (3%) - matches old system
- Retry 2: 500 bps (5%) - if we add more retries
- Retry 3: 1000 bps (10%) - maximum reasonable slippage

**Amount Adjustment:**
- Should we reduce amount on retry? (e.g., sell 95% instead of 100%)
- Pros: Better chance of success, less impact if price moves
- Cons: Leaves dust, position not fully closed

**Wait Time:**
- Immediate retry? (price might not have changed)
- Short delay? (1-2 seconds - let price settle)
- Longer delay? (5-10 seconds - but emergency exit should be fast)

**Recommendation**: 
- Increase slippage to 300 bps on first retry
- No amount reduction (we want full exit)
- No delay (emergency exit should be fast)

### 4. Different Strategies for Emergency Exit vs Trim?

**Emergency Exit (size_frac = 1.0):**
- **Priority**: High - need to exit quickly
- **Risk tolerance**: Higher slippage acceptable (3-5%)
- **Retry count**: 1-2 retries max (don't want to get stuck)
- **Speed**: Fast - no delays between retries

**Trim (size_frac < 1.0):**
- **Priority**: Medium - taking profit, not urgent
- **Risk tolerance**: Lower slippage (want good price)
- **Retry count**: Maybe 1 retry, or skip if fails
- **Speed**: Can wait a bit between retries

**Recommendation**: 
- Emergency exit: Aggressive retry (1-2 retries, higher slippage, no delay)
- Trim: Conservative retry (1 retry, moderate slippage increase, optional delay)

### 5. Backoff Strategy

**Options:**
- **No backoff**: Retry immediately
- **Fixed delay**: Wait 1-2 seconds
- **Exponential backoff**: 1s, 2s, 4s (for multiple retries)
- **Price-based**: Wait for next price update (15m/1h bar)

**Recommendation**: 
- Emergency exit: No backoff (immediate retry)
- Trim: Optional 1-2 second delay

### 6. Risk Management

**Infinite Loop Prevention:**
- Maximum retry count (hard limit)
- Timeout (don't retry if too much time has passed)
- Position state check (don't retry if position already closed)

**Slippage Limits:**
- Maximum slippage cap (e.g., 10% = 1000 bps)
- Alert if slippage exceeds threshold
- Log slippage for analysis

**Position Tracking:**
- Check `total_quantity` before each retry
- Don't retry if position is already closed
- Update position state after each attempt

### 7. Logging & Observability

**What to Log:**
- Retry attempt number
- Error that triggered retry
- Slippage used on retry
- Success/failure of retry
- Final outcome

**Metrics to Track:**
- Retry success rate
- Average slippage on retries
- Most common retry triggers
- Time to successful execution

## Proposed Implementation Strategy

### Phase 1: Emergency Exit Retry (Simple)
```python
# In _execute_solana_sell_token_to_usdc()
if not result.get('success'):
    error = result.get('error', '')
    
    # Check if retryable
    is_retryable = (
        'Simulation failed' in error or 
        'custom program error' in error or
        '0x1788' in error
    )
    
    if is_retryable and slippage_bps < 300:
        # Single retry with higher slippage
        logger.info(f"Retrying sell with higher slippage (300 bps)")
        result = loop.run_until_complete(
            self.js_solana_client.execute_jupiter_swap(
                input_mint=token_contract,
                output_mint=USDC_MINT,
                amount=tokens_raw,
                slippage_bps=300  # 3%
            )
        )
```

### Phase 2: Enhanced Retry (If Needed)
- Add retry counter
- Add error categorization
- Add different strategies for emergency_exit vs trim
- Add logging/metrics

## Open Questions

1. **Should we retry async errors?** (Now that we've fixed the bug, probably not needed, but could add as safety net)

2. **Should emergency_exit retry with reduced amount?** (e.g., 95% instead of 100% to leave small dust)
   - Pro: Better chance of success
   - Con: Position not fully closed, requires manual cleanup

3. **Should we track retry success rate?** (To know if retries are actually helping)

4. **Should we alert on repeated failures?** (If emergency exit fails after retries, this is critical)

5. **Should we have different slippage for different token types?** (Token-2022 tax tokens might need higher slippage)

## Recommendations

**Start Simple:**
1. Add single retry for emergency exits only
2. Retry on simulation/slippage errors only
3. Increase slippage to 300 bps on retry
4. No delay, no amount reduction
5. Log retry attempts

**Expand Later (If Needed):**
- Add retry for trims
- Add multiple retry attempts
- Add backoff strategy
- Add amount reduction option
- Add metrics tracking

**Critical:**
- Always check position state before retry (don't retry if already closed)
- Hard limit on retry count (prevent infinite loops)
- Maximum slippage cap (don't accept terrible prices)
- Alert on critical failures (emergency exit stuck)

