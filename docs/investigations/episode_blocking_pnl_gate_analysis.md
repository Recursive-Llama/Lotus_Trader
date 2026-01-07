# Episode Blocking with P&L Gate - Analysis

**Question**: Should we only block on failure if we actually lost money (exited at a loss)?

---

## Current Behavior

**When blocking happens**:
- Attempt ends at S0 (failure to reach S3)
- We entered S1 or S2 (we actually acted)
- **Blocks regardless of P&L**

**Example scenarios**:
1. Entered S1, price went up, we sold at profit, then trend collapsed → **BLOCKS** (even though we made money)
2. Entered S1, price went down, we exited at loss → **BLOCKS** (correct)
3. Entered S1, price went sideways, we exited at breakeven → **BLOCKS** (even though no loss)

---

## Proposed Behavior

**Only block if**:
- Attempt ends at S0 (failure to reach S3)
- We entered S1 or S2 (we actually acted)
- **AND we lost money** (P&L < 0)

**Example scenarios**:
1. Entered S1, price went up, we sold at profit, then trend collapsed → **NO BLOCK** (we made money, so it's fine)
2. Entered S1, price went down, we exited at loss → **BLOCKS** (correct)
3. Entered S1, price went sideways, we exited at breakeven → **NO BLOCK** (no loss, so it's fine)

---

## Complexity Analysis

### ✅ **Easy Part: P&L is Available**

**When `record_attempt_failure()` is called**:
- We're in `_process_episode_logging()` during S0 transition
- Position dict is available with P&L data:
  - `rpnl_usd` - Realized P&L (from sells)
  - `total_pnl_usd` - Total P&L (realized + unrealized)
  - `total_extracted_usd` - Total USD extracted
  - `total_allocation_usd` - Total USD allocated

**Location**: `pm_core_tick.py:1357-1367` (S1 failure) and `1438-1448` (S2 failure)

**We have access to position data** - can check P&L before blocking.

---

### ⚠️ **Edge Cases to Consider**

#### 1. **Unrealized vs Realized Loss**

**Scenario**: We entered but haven't sold yet (total_quantity > 0)

**Options**:
- **Option A**: Use `total_pnl_usd` (includes unrealized)
  - ✅ More accurate (includes current position value)
  - ⚠️ But position might recover later
  - ⚠️ Price might be stale

- **Option B**: Use `rpnl_usd` (realized only)
  - ✅ Only counts actual losses from sells
  - ❌ Misses unrealized losses (we're still holding at a loss)

- **Option C**: Use `total_extracted_usd - total_allocation_usd`
  - ✅ Simple calculation
  - ✅ Only counts what we've actually extracted vs allocated
  - ⚠️ Doesn't account for current position value

**Recommendation**: Use `total_pnl_usd` (realized + unrealized) because:
- If we're at S0, the trend is broken
- Current position value is likely lower than entry
- We want to block if we're underwater, even if we haven't sold yet

#### 2. **Breakeven (P&L = 0)**

**Question**: Should we block if P&L = 0?

**Options**:
- **Option A**: Block if P&L <= 0 (include breakeven)
  - More conservative
  - Treats breakeven as "not good enough"

- **Option B**: Block only if P&L < 0 (exclude breakeven)
  - More lenient
  - Breakeven is acceptable

**Recommendation**: Block if P&L < 0 (exclude breakeven) because:
- Breakeven means we didn't lose money
- The attempt didn't work out, but we didn't get hurt
- Less aggressive blocking = more opportunities

#### 3. **Partial Sells**

**Scenario**: We entered, sold some at profit, but still holding some when trend collapses

**Example**:
- Allocated: $100
- Sold: $50 worth at $60 profit
- Still holding: $50 worth (now worth $30)
- Total P&L: $60 (realized) + $30 (unrealized) - $100 (allocated) = -$10

**Should we block?**
- We made money on the sell ($60 profit)
- But overall we're down ($10 loss)
- **Recommendation**: Block (we're overall down)

---

## Implementation Complexity

### **Difficulty: LOW** ✅

**Changes needed**:

1. **Modify `record_attempt_failure()` signature**:
   ```python
   def record_attempt_failure(
       sb_client,
       token_contract: str,
       token_chain: str,
       timeframe: str,
       entered_s1: bool,
       entered_s2: bool,
       total_pnl_usd: float = 0.0,  # NEW parameter
       book_id: str = "onchain_crypto"
   ) -> None:
   ```

2. **Add P&L check**:
   ```python
   # Only block if we lost money
   if total_pnl_usd >= 0:
       logger.debug(
           "EPISODE_BLOCK: Skipping block (P&L >= 0) | %s/%s tf=%s | P&L=$%.2f",
           token_contract[:12], token_chain, timeframe, total_pnl_usd
       )
       return
   ```

3. **Pass P&L when calling**:
   ```python
   # In pm_core_tick.py when calling record_attempt_failure()
   total_pnl_usd = float(position.get("total_pnl_usd", 0.0))
   
   record_attempt_failure(
       sb_client=self.sb,
       token_contract=position.get("token_contract", ""),
       token_chain=position.get("token_chain", ""),
       timeframe=position.get("timeframe", ""),
       entered_s1=entered_s1,
       entered_s2=entered_s2,
       total_pnl_usd=total_pnl_usd,  # NEW
       book_id=position.get("book_id", "onchain_crypto")
   )
   ```

**Lines to modify**:
- `episode_blocking.py`: ~5 lines (add parameter, add check)
- `pm_core_tick.py`: ~2 lines (pass P&L value)

**Total complexity**: Very low - simple parameter addition and conditional check

---

## Trade-offs

### ✅ **Pros of P&L Gate**

1. **More accurate blocking**: Only blocks when we actually lost money
2. **Less aggressive**: Doesn't block profitable attempts that failed to reach S3
3. **Better risk management**: Focuses on actual losses, not just failed attempts
4. **More opportunities**: Allows re-entry after profitable attempts that didn't reach S3

### ⚠️ **Cons of P&L Gate**

1. **Timing sensitivity**: P&L might be stale if price updates are delayed
2. **Unrealized losses**: If we're holding at a loss but haven't sold, we might not block when we should
3. **Partial sells**: Complex scenarios where we made money on some sells but lost overall
4. **Edge case handling**: Need to decide on breakeven, partial sells, etc.

---

## Recommendation

### **YES, implement it** ✅

**Why**:
1. **Low complexity** - Simple parameter addition
2. **Better logic** - Only blocks when we actually lost money
3. **More opportunities** - Doesn't block profitable attempts
4. **P&L is available** - We have the data when we need it

**Implementation details**:
- Use `total_pnl_usd` (realized + unrealized)
- Block only if `total_pnl_usd < 0` (exclude breakeven)
- Add logging to show why blocking was skipped (P&L >= 0)

**Edge case handling**:
- If `total_pnl_usd` is None or missing, default to blocking (conservative)
- Log when blocking is skipped due to P&L gate

---

## Alternative: Hybrid Approach

**Option**: Block if either:
1. P&L < 0 (lost money), OR
2. P&L = 0 AND we never sold anything (breakeven with no activity)

**Rationale**: 
- If we made money, don't block
- If we lost money, block
- If we broke even but never sold, block (no activity = failed attempt)

**Complexity**: Slightly higher (need to check if we sold anything)

**Recommendation**: Start with simple P&L < 0 check, can add hybrid later if needed.

---

## Summary

**Is it tricky?** No - very straightforward ✅

**Is it worth it?** Yes - better logic, low complexity ✅

**Implementation**: ~10 lines of code changes, low risk

**Recommendation**: Implement P&L gate with `total_pnl_usd < 0` check

