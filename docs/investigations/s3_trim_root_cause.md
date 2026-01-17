# S3 Trim Root Cause Analysis

**Date**: 2026-01-10  
**Status**: ROOT CAUSE IDENTIFIED

---

## The Problem

S3 positions have empty `scores` dictionaries, causing `trim_flag` to never be set (since `ox >= 0.65` can never be true when `ox = 0.0`).

---

## Root Cause

**The issue is in the S2→S3 transition path.**

### Code Flow Analysis

1. **S2→S3 Transition** (lines 1673-1700):
   ```python
   elif self._check_s3_order(ema_vals):
       logger.info("S2→S3 TRANSITION: ...")
       payload = self._build_payload(
           "S3",
           contract, chain, price, ema_vals, features,
           {
               "diagnostics": {},  # S3 scores added below  ← BUT THEY'RE NOT!
           },
           prev_state=prev_state,
       )
       features["uptrend_engine_v4"] = payload
       self._write_features(pid, features)
   ```

2. **Stay in S3 Path** (lines 1803-2076):
   ```python
   elif prev_state == "S3":
       # ... check for S3→S0 transition ...
       else:
           # Stay in S3: Compute scores, check emergency exit
           s3_scores = self._compute_s3_scores(...)
           # ... compute trim_flag, buy_flag, etc. ...
           extra_data = {
               "trim_flag": trim_flag,
               "buy_flag": dx_buy_ok,
               "scores": {
                   "ox": ox,
                   "dx": dx,
                   "edx": edx,
                   ...
               },
               ...
           }
           payload = self._build_payload("S3", ..., extra_data, ...)
   ```

### The Issue

**When a position transitions S2→S3, it creates a payload with ONLY `{"diagnostics": {}}` - no scores, no flags.**

The scores are only computed in the **"Stay in S3"** path, which requires:
- `prev_state == "S3"` (line 1803)
- `not all_below_333` (line 1837)

**If the uptrend engine doesn't run again after the transition, or if there's a timing issue, the scores never get computed.**

### Evidence

From PAYAI/solana tf=15m position:
```json
{
  "state": "S3",
  "prev_state": "S2",  ← Just transitioned!
  "ts": "2026-01-09T05:31:10",
  "diagnostics": {},   ← Empty!
  // Missing: scores, trim_flag, buy_flag, etc.
}
```

This is clearly a **transition payload** that was never updated with scores.

---

## Why This Happens

1. **Position transitions S2→S3** → Creates minimal payload with just `diagnostics: {}`
2. **Engine writes this to database** → Position now has `state: S3, prev_state: S2`
3. **Next engine run** → Should see `prev_state: S3` and compute scores
4. **BUT**: If engine doesn't run again, or if there's a condition preventing the "Stay in S3" path, scores never get computed

### Possible Reasons Scores Aren't Computed

1. **Engine not running frequently enough** → Transition happens, but engine doesn't run again before next state change
2. **State transition happening immediately** → Position transitions S2→S3, then immediately S3→S0 (all EMAs below 333)
3. **Exception in `_compute_s3_scores()`** → Scores computation fails silently
4. **Condition preventing "Stay in S3" path** → Some condition causes the code to skip the else block

---

## The Fix

### Option 1: Compute Scores During Transition (Recommended)

**Modify the S2→S3 transition to compute scores immediately:**

```python
# S2 → S3: Full bullish alignment (band-based)
elif self._check_s3_order(ema_vals):
    logger.info("S2→S3 TRANSITION: %s/%s (timeframe=%s, full bullish alignment, S2 retest/trim checks stopped)", 
               contract, chain, self.timeframe)
    
    # Record S3 start timestamp
    current_ts = last.get("ts") or _now_iso()
    self._set_s3_start_ts(pid, features, current_ts)
    
    # COMPUTE S3 SCORES IMMEDIATELY (not just on "stay in S3")
    s3_scores = self._compute_s3_scores(contract, chain, price, ema_vals, ta, features)
    
    # Ensure s3_scores is a dict
    if not isinstance(s3_scores, dict):
        logger.error("s3_scores is not a dict: %s (type: %s) for %s/%s", s3_scores, type(s3_scores), contract, chain)
        s3_scores = {"ox": 0.5, "dx": 0.5, "edx": 0.5, "diagnostics": {}}
    
    ox = s3_scores.get("ox", 0.0)
    dx = s3_scores.get("dx", 0.0)
    edx = s3_scores.get("edx", 0.0)
    
    # Compute trim_flag, buy_flag, etc. (same logic as "Stay in S3")
    # ... (copy logic from lines 1979-2048)
    
    extra_data = {
        "trim_flag": trim_flag,
        "buy_flag": dx_buy_ok,
        "scores": {
            "ox": ox,
            "dx": dx,
            "edx": edx,
            ...
        },
        ...
    }
    
    payload = self._build_payload(
        "S3",
        contract, chain, price, ema_vals, features,
        extra_data,  # Include scores!
        prev_state=prev_state,
    )
```

### Option 2: Ensure Engine Runs After Transition

**Add a mechanism to ensure positions that just transitioned get processed again immediately:**

- Add a flag to mark "needs_score_computation"
- Process these positions first in the next engine run
- Or run engine twice: once for transitions, once for score computation

### Option 3: Defensive Check in "Stay in S3"

**Add a check to compute scores if they're missing:**

```python
elif prev_state == "S3":
    # ... existing checks ...
    else:
        # Stay in S3
        # DEFENSIVE: If scores are missing, compute them
        existing_payload = features.get("uptrend_engine_v4", {})
        if not existing_payload.get("scores"):
            logger.warning("S3 position missing scores, computing now: %s/%s", contract, chain)
        
        s3_scores = self._compute_s3_scores(...)
        # ... rest of logic ...
```

---

## Recommended Solution

**Option 1 is the best fix** - compute scores during the transition so positions always have complete payloads. This ensures:
- Positions have scores immediately after transitioning to S3
- No dependency on engine running again
- Consistent payload structure
- Trim flags can be set right away if conditions are met

---

## Verification

After fix, verify:
1. New S2→S3 transitions include scores in payload
2. Existing S3 positions get scores on next engine run
3. Trim flags are set when `ox >= 0.65 AND near_sr`
4. No positions stuck with empty scores

