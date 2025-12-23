# Emergency Exit Investigation

**Date**: 2025-12-05  
**Issue**: Emergency exit triggering incorrectly and missing S1 emergency exit

---

## Expected Behavior

### 1. S1 → S0 Emergency Exit
**When**: In S1, holding tokens, and we go into full S0 bearish EMA order  
**Action**: 
- Set `emergency_exit = True`
- Transition S1 → S0
- **Both happen at the same time**

**Full S0 Bearish Order**:
- Fast band below mid: `EMA20 < EMA60 AND EMA30 < EMA60`
- Slow descending: `EMA60 < EMA144 < EMA250 < EMA333`

### 2. S3 Emergency Exit (Two Separate Things)
**Part 1 - Emergency Exit Flag**:
- **When**: In S3, price goes below EMA333
- **Action**: Set `emergency_exit = True` (flag only, **no state change**)
- **State**: Stays in S3

**Part 2 - State Transition**:
- **When**: In S3, all EMAs break below EMA333 (full bearish order)
- **Action**: Transition S3 → S0 with `exit_position: True`
- **State**: Changes to S0

**These are TWO separate events** - emergency exit flag happens first, then later the state transition.

---

## Current Implementation Issues

### Issue 1: Global "Fast Band at Bottom" Override (WRONG)

**Location**: `uptrend_engine_v4.py` lines 1376-1395

```python
# Global exit precedence: fast band at bottom (overrides all states)
if self._check_fast_band_at_bottom(ema_vals):
    payload = self._build_payload(
        "S0",
        contract,
        chain,
        price,
        ema_vals,
        features,
        {
            "exit_position": True,
            "exit_reason": "fast_band_at_bottom",
        },
        prev_state=prev_state,
    )
    # ... transition to S0
    continue
```

**Problem**:
- This check happens **BEFORE** state-specific logic
- It triggers for **ANY state** (S1, S2, S3)
- It sets `exit_position: True` which triggers emergency_exit in `plan_actions_v4()`
- It **overrides** state-specific emergency exit logic

**What `_check_fast_band_at_bottom()` checks**:
```python
def _check_fast_band_at_bottom(self, ema_vals: Dict[str, float]) -> bool:
    """Check if fast band (20/30) is at the bottom (below all other EMAs)."""
    ema20 = ema_vals.get("ema20", 0.0)
    ema30 = ema_vals.get("ema30", 0.0)
    ema60 = ema_vals.get("ema60", 0.0)
    ema144 = ema_vals.get("ema144", 0.0)
    ema250 = ema_vals.get("ema250", 0.0)
    ema333 = ema_vals.get("ema333", 0.0)
    
    # Fast band below all others
    return (ema20 < ema60 and ema30 < ema60 and 
            ema20 < ema144 and ema30 < ema144 and
            ema20 < ema250 and ema30 < ema250 and
            ema20 < ema333 and ema30 < ema333)
```

**Why This Is Wrong**:
- This condition can be true even when we're in S3 and price is still above EMA333
- It doesn't check if we're holding tokens
- It doesn't respect state-specific emergency exit logic
- It triggers emergency_exit when it shouldn't

---

### Issue 2: Missing S1 → S0 Emergency Exit

**Location**: `uptrend_engine_v4.py` lines 1442-1485

**Current S1 Logic**:
```python
elif prev_state == "S1":
    # Check buy signal conditions
    buy_check = self._check_buy_signal_conditions(...)
    
    # S1 → S2: Price > EMA333 (flip-flop, not an exit)
    if price > ema_vals.get("ema333", 0.0):
        # Transition to S2
        ...
    else:
        # Stay in S1
        ...
```

**Problem**:
- **No check for S1 → S0 transition**
- **No check for full S0 bearish EMA order**
- **No emergency_exit flag set when transitioning to S0**

**What Should Happen**:
```python
elif prev_state == "S1":
    # Check if we should exit to S0 (full bearish order)
    if self._check_s0_order(ema_vals):
        # S1 → S0: Full bearish order + holding tokens = emergency exit
        # TODO: Need to check if holding tokens (total_quantity > 0)
        payload = self._build_payload(
            "S0",
            contract,
            chain,
            price,
            ema_vals,
            features,
            {
                "exit_position": True,
                "exit_reason": "s1_to_s0_bearish_order",
                "emergency_exit": True,  # MISSING
            },
            prev_state=prev_state,
        )
        # ... transition
    elif price > ema_vals.get("ema333", 0.0):
        # S1 → S2
        ...
    else:
        # Stay in S1
        ...
```

**Missing**:
1. Check for full S0 bearish order (`_check_s0_order()`)
2. Set `emergency_exit: True` when transitioning S1 → S0 with tokens held
3. Check if position has tokens (`total_quantity > 0`)

---

### Issue 3: S3 Emergency Exit Logic (Partially Correct)

**Location**: `uptrend_engine_v4.py` lines 1632-1694

**Current S3 Logic**:
```python
elif prev_state == "S3":
    # S3 → S0: All EMAs break below EMA333
    all_below_333 = (
        ema_vals.get("ema20", 0.0) < ema_vals.get("ema333", 0.0) and
        ema_vals.get("ema30", 0.0) < ema_vals.get("ema333", 0.0) and
        ema_vals.get("ema60", 0.0) < ema_vals.get("ema333", 0.0) and
        ema_vals.get("ema144", 0.0) < ema_vals.get("ema333", 0.0) and
        ema_vals.get("ema250", 0.0) < ema_vals.get("ema333", 0.0)
    )
    
    if all_below_333:
        # Transition to S0
        payload = self._build_payload(
            "S0",
            ...
            {"exit_position": True, "exit_reason": "all_emas_below_333"},
            ...
        )
    else:
        # Stay in S3: Compute scores, check emergency exit
        ...
        # Emergency exit: price < EMA333 (flag only, no state change)
        emergency_exit = price < ema333_val
        ...
```

**Analysis**:
- ✅ **Correct**: Emergency exit flag (`price < EMA333`) is set in S3 without state change
- ✅ **Correct**: State transition to S0 happens separately when `all_below_333`
- ⚠️ **Issue**: The global "fast band at bottom" check (line 1376) might trigger BEFORE this S3 logic runs

**What Should Happen**:
1. **First**: Price drops below EMA333 → Set `emergency_exit = True`, stay in S3
2. **Later**: All EMAs break below EMA333 → Transition S3 → S0 with `exit_position: True`

**Current Flow**:
- Global check at line 1376 might catch "fast band at bottom" before S3 logic runs
- This would trigger emergency_exit incorrectly

---

## How plan_actions_v4() Handles Emergency Exit

**Location**: `pm/actions.py` lines 346-387

**Current Logic**:
```python
# Exit Precedence (highest priority)
if uptrend.get("exit_position"):
    # Full exit - emergency or structural invalidation
    action = {
        "decision_type": "emergency_exit",
        "size_frac": 1.0,
        ...
    }
    return [action]

# Emergency Exit Handling (any state)
if uptrend.get("emergency_exit"):
    # Full exit (sell all tokens)
    action = {
        "decision_type": "emergency_exit",
        "size_frac": 1.0,
        ...
    }
    return [action]
```

**Problem**:
- `exit_position: True` triggers emergency_exit (line 347)
- `emergency_exit: True` also triggers emergency_exit (line 370)
- The global "fast band at bottom" sets `exit_position: True`, which triggers emergency_exit even when it shouldn't

---

## Summary of Issues

### Critical Issues

1. **Global "Fast Band at Bottom" Override** (Line 1376)
   - ❌ Triggers emergency_exit for ANY state
   - ❌ Happens BEFORE state-specific logic
   - ❌ Doesn't check if holding tokens
   - ❌ Overrides correct state-specific emergency exit logic

2. **Missing S1 → S0 Emergency Exit** (Line 1442)
   - ❌ No check for full S0 bearish order in S1
   - ❌ No S1 → S0 transition logic
   - ❌ No `emergency_exit` flag set when S1 → S0 with tokens held

### Partially Correct

3. **S3 Emergency Exit** (Line 1632)
   - ✅ Emergency exit flag set correctly (`price < EMA333`)
   - ✅ State transition happens separately (`all_below_333`)
   - ⚠️ But global check might override it

---

## Required Fixes

### Fix 1: Remove Global "Fast Band at Bottom" Override
- Remove the global check at line 1376
- Let state-specific logic handle emergency exits

### Fix 2: Add S1 → S0 Emergency Exit
- Check for full S0 bearish order in S1
- If true AND holding tokens → Set `emergency_exit: True` and transition S1 → S0
- Both happen at the same time

### Fix 3: Add Token Check to S3 → S0 Transition
- **Location**: Line 1657 (S3 → S0 transition)
- **Current**: Sets `exit_position: True` regardless of tokens
- **Change**: Only set `exit_position: True` if `total_quantity > 0`
- **Rationale**: No need to trigger exit if we're not holding tokens (double-check)

### Fix 4: Token Holdings Check (SIMPLE - RECOMMENDED)
- **Complexity**: Very simple - just 2 changes
- **Change 1**: Add `total_quantity` to select statement (line 139)
  ```python
  .select("id,token_contract,token_chain,features,status,total_quantity")
  ```
- **Change 2**: Check tokens before setting emergency_exit in **both places**:
  
  **S1 → S0 logic** (line ~1442):
  ```python
  total_quantity = float(p.get("total_quantity", 0.0))
  if self._check_s0_order(ema_vals) and total_quantity > 0:
      # Set emergency_exit only if holding tokens
      emergency_exit = True
  ```
  
  **S3 emergency_exit flag** (line 1686):
  ```python
  total_quantity = float(p.get("total_quantity", 0.0))
  # Emergency exit: price < EMA333 (flag only, no state change)
  emergency_exit = (price < ema333_val) and (total_quantity > 0)
  ```
- **Rationale**: 
  - Better to only set emergency_exit when we actually have tokens to sell
  - Prevents unnecessary flags for empty positions
  - Very simple implementation (just add field to select, check before setting flag)
  - **Consistency**: Check tokens in both S1 and S3 emergency exit logic

---

## Code Locations

- **Global "Fast Band at Bottom"**: `uptrend_engine_v4.py:1376-1395`
- **S1 State Logic**: `uptrend_engine_v4.py:1442-1485`
- **S3 State Logic**: `uptrend_engine_v4.py:1632-1694`
- **S3 Emergency Exit Flag**: `uptrend_engine_v4.py:1685-1686`
- **plan_actions_v4 Emergency Exit**: `pm/actions.py:346-387`
- **`_check_s0_order()`**: `uptrend_engine_v4.py:494-512`
- **`_check_fast_band_at_bottom()`**: `uptrend_engine_v4.py:542-551`

---

**End of Investigation**

