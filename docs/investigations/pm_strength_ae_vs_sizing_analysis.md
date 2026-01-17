# PM Strength: A/E vs Sizing - Deep Dive Analysis

**Date**: 2025-01-XX  
**Status**: Investigation - Understanding Current Implementation vs Intended Design

---

## Executive Summary

**Current Implementation**:
- ✅ PM Strength affects **position sizing** (`position_size_frac`)
- ✅ A/E scores **already affect sizing** through the formula: `position_size_frac = 0.10 + (a_final * 0.50)`
- ✅ Strength is applied **after** A/E has been used to calculate base sizing
- ⚠️  `apply_strength_to_ae()` function exists but is **never called**

**Key Insight**: 
- **A/E → Sizing**: A/E scores are calculated early and used to compute base `position_size_frac`
- **Pattern → Strength**: Pattern is known later (when action is determined), so strength can be looked up
- **Strength → Sizing**: Strength is applied to the sizing that was already calculated from A/E

**Why This Design Makes Sense**:
- A/E is calculated **before** pattern is known (from regime flags, bucket context)
- Pattern is determined **after** action type is decided (when we know state, signals)
- Strength lookup requires pattern, so it happens **after** A/E calculation
- Applying strength directly to sizing (derived from A/E) achieves the same effect as adjusting A/E first

---

## Part 1: Current Implementation Flow - The Complete Picture

### How It Actually Works Now

**Step 1: A/E Computation** (`pm_core_tick.py:3630-3655`)
```python
if use_ae_v2:
    regime_flags = extract_regime_flags(self.sb, token_bucket, book_id)
    a_base, e_base, ae_diag = compute_ae_v2(regime_flags, token_bucket)
    
    a_final = a_base
    e_final = e_base
    position_size_frac = 0.33  # Default, will be overridden
```

**Step 2: Base Sizing Calculation** (Multiple places)

**Option A: From A/E formula** (`actions.py:444`)
```python
position_size_frac = 0.10 + (a_final * 0.50)  # Linear: A=0.0 → 10%, A=1.0 → 60%
```

**Option B: From A/E thresholds** (`actions.py:_a_to_entry_size()`)
```python
if a_final >= 0.7:
    return 0.90  # Aggressive: 90% of remaining allocation
elif a_final >= 0.3:
    return 0.60  # Normal: 60% of remaining allocation
else:
    return 0.30  # Patient: 30% of remaining allocation
```

**Option C: From levers** (`levers.py:_compute_position_sizing()`)
```python
def _compute_position_sizing(a_final: float) -> float:
    return 0.10 + (a_final * 0.50)  # Same linear formula
```

**Key Point**: A/E scores **directly determine** base sizing before strength is applied.

**Step 3: Action Planning** (`plan_actions_v4()`)
- Uses `a_final` and `e_final` to determine action type and base sizing
- Pattern is determined **after** action type is known (state, signals, etc.)

**Step 4: Strength Override Application** (`_apply_v5_overrides_to_action()`)
```python
# Pattern is now known, so strength can be looked up
adjusted_levers, strength_mult = apply_pattern_strength_overrides(...)

# Strength is applied to sizing that was already calculated from A/E
action["size_frac"] = action.get("size_frac", 0.0) * final_mult
```

**Result**: 
- A/E → Base sizing (calculated early, before pattern is known)
- Pattern → Strength lookup (happens later, when pattern is known)
- Strength → Final sizing (applied to sizing derived from A/E)

**Why This Works**:
- A/E affects sizing through the formula: `position_size_frac = f(a_final)`
- Strength multiplies the result: `final_size = position_size_frac * strength_mult`
- This is equivalent to: `final_size = f(a_final) * strength_mult`
- Which is the same as adjusting A/E first, then calculating sizing

---

## Part 2: Intended Design (from Documentation)

### How It Should Work

**From `docs/implementation/scaling_ae_v2_implementation.md`**:

**Stage 1: Compute base A/E from flags**
```python
regime_flags = extract_regime_flags(self.sb, token_bucket, self.book_id)
a_base, e_base, ae_diag = compute_ae_v2(regime_flags, token_bucket)
```

**Stage 2: Apply strength after action determined**
```python
# After determining action type, before sizing:
_, strength_mult = apply_pattern_strength_overrides(...)

# Apply strength to A/E
a_final, e_final, strength_diag = apply_strength_to_ae(
    a_base, e_base, strength_mult, pattern_key
)
```

**Intended Effect**:
- **A/E adjustment**: Good pattern (strength > 1.0) → A↑, E↓
- **Sizing adjustment**: Good pattern → larger position size

---

## Part 3: The `apply_strength_to_ae()` Function

### What It Does

```146:199:src/intelligence/lowcap_portfolio_manager/pm/ae_calculator_v2.py
def apply_strength_to_ae(
    a_base: float,
    e_base: float,
    strength_mult: float,
    pattern_key: str = "",
    config: Optional[AEConfig] = None,
) -> Tuple[float, float, Dict[str, Any]]:
    """
    Apply learned strength to A/E.
    
    Strength > 1.0 means pattern is good → A↑, E↓
    Strength < 1.0 means pattern is bad → A↓, E↑
    """
    config = config or AEConfig()
    
    # Convert multiplier to effect: 1.0 → 0, 1.5 → +0.25 (capped), 0.5 → -0.25 (capped)
    strength_effect = (strength_mult - 1.0)
    strength_effect = max(-config.strength_cap, min(config.strength_cap, strength_effect))
    
    A_final = a_base + strength_effect
    E_final = e_base - strength_effect  # Inverse: good pattern → less urgency to exit
    
    # Final clamp
    A_final = max(0.0, min(1.0, A_final))
    E_final = max(0.0, min(1.0, E_final))
    
    return A_final, E_final, diagnostics
```

### How It Would Work

**Example**:
- `a_base = 0.6`, `e_base = 0.4`
- `strength_mult = 1.5` (good pattern)
- `strength_effect = 0.5 - 1.0 = 0.5` (capped at 0.25)
- `A_final = 0.6 + 0.25 = 0.85` (more aggressive)
- `E_final = 0.4 - 0.25 = 0.15` (less urgency to exit)

**Effect**: Good patterns → higher A (more aggressive entries), lower E (less urgency to trim/exit)

### Current Status

- ✅ Function exists and is imported
- ❌ Function is **never called** in the actual flow
- ⚠️  Comment says "Strength is applied later" but it's not

---

## Part 4: Why This Design Makes Sense

### The Timing Problem

**User's Insight**: "Maybe it was done this way due to timing of when A/E are calculated?"

**The Flow**:
1. **A/E Calculated Early** (before pattern is known):
   - From regime flags, bucket context
   - Used to calculate base `position_size_frac`
   - Formula: `position_size_frac = 0.10 + (a_final * 0.50)` or thresholds

2. **Pattern Determined Later** (when action is decided):
   - State, signals, buy flags are known
   - Pattern key can be generated
   - Strength can be looked up

3. **Strength Applied to Sizing** (after pattern is known):
   - `final_size = position_size_frac * strength_mult`
   - This is mathematically equivalent to adjusting A/E first (for linear formulas)

**Why This Works**:
- **A/E → Sizing**: A/E scores directly determine base sizing through the formula
- **Pattern → Strength**: Pattern is known later, so strength lookup happens after A/E calculation
- **Strength → Sizing**: Strength multiplies the sizing that was already derived from A/E
- **Result**: Strength effectively affects sizing, which is derived from A/E

**Mathematical Equivalence** (for linear formulas):
- Current: `final_size = f(a_final) * strength_mult`
- Alternative: `final_size = f(a_final * strength_mult)` (if f is linear)
- For `f(x) = 0.10 + (x * 0.50)`: Both approaches give the same result

**Why Current Approach is Better**:
- **Timing**: A/E calculated before pattern is known (can't apply strength yet)
- **Simplicity**: Apply strength to final sizing, not intermediate A/E
- **Flexibility**: Strength can affect sizing differently than A/E (non-linear effects)

---

## Part 5: Design Questions

### Question 1: Should Strength Affect A/E?

**Arguments FOR**:
- Good patterns should trigger more aggressive entries (higher A)
- Good patterns should reduce exit urgency (lower E)
- A/E affects decision-making, which should be informed by learning
- Design doc intended this

**Arguments AGAINST**:
- A/E is already complex (regime flags, bucket context)
- Adding strength might make it harder to debug
- Sizing is "way more critical" - maybe that's enough?
- Current implementation works (just sizing)

### Question 2: When Should Strength Be Applied?

**Option A: Before Action Planning** (affects decision-making)
- Apply strength to A/E → use adjusted A/E for action planning
- Strength affects **when** to act

**Option B: After Action Planning** (affects sizing only)
- Use base A/E for action planning
- Apply strength to sizing only
- Current implementation

**Option C: Both** (affects decision-making AND sizing)
- Apply strength to A/E → affects decision thresholds
- Apply strength to sizing → affects position size
- Intended design

### Question 3: Should Strength Affect Trims?

**Current**: Trims skip strength (based on E-score only)

**Options**:
1. **Keep as-is**: Trims based on E-score only (no learning)
2. **Apply to trims**: Use strength to adjust trim sizing
3. **Apply to A/E for trims**: Adjust E-score based on strength

---

## Part 6: Implementation Gap

### What's Missing

**In `_apply_v5_overrides_to_action()`**:
```python
adjusted_levers, strength_mult = apply_pattern_strength_overrides(...)

# Currently: Only affects sizing
action["size_frac"] = action.get("size_frac", 0.0) * final_mult

# Missing: Apply strength to A/E
# a_final, e_final = apply_strength_to_ae(a_final, e_final, strength_mult, pattern_key)
```

**Why It's Not There**:
- `a_final` and `e_final` are passed in but not modified
- `apply_strength_to_ae()` is imported but never called
- Comment says "applied later" but it's not

---

## Part 7: Analysis - Is Current Design Correct?

### Current Design: Strength → Sizing (Derived from A/E)

**Flow**:
1. A/E calculated → `position_size_frac = f(a_final)`
2. Pattern determined → strength looked up
3. Strength applied → `final_size = position_size_frac * strength_mult`

**Mathematical Effect**:
- For linear formula: `f(x) = 0.10 + (x * 0.50)`
- Current: `final = (0.10 + a_final * 0.50) * strength_mult`
- Equivalent to: `final = 0.10 * strength_mult + a_final * 0.50 * strength_mult`

**What This Means**:
- Strength affects the **entire sizing calculation**, not just A/E
- Base sizing (10%) is also scaled by strength
- A/E-derived sizing (0.50 * a_final) is scaled by strength

### Alternative: Strength → A/E → Sizing

**Flow**:
1. A/E calculated → `a_base, e_base`
2. Pattern determined → strength looked up
3. Strength applied to A/E → `a_final = a_base + strength_effect`
4. Sizing calculated → `final_size = f(a_final)`

**Mathematical Effect**:
- `a_final = a_base + (strength_mult - 1.0) * cap` (capped at ±0.25)
- `final = 0.10 + a_final * 0.50`
- `final = 0.10 + (a_base + strength_effect) * 0.50`

**Difference**:
- Current: Base (10%) is also scaled by strength
- Alternative: Base (10%) is fixed, only A/E-derived part is affected

### Which is Better?

**Current Approach (Strength → Sizing)**:
- ✅ Simpler (one multiplication)
- ✅ Timing works (pattern known after A/E calculated)
- ✅ Affects entire sizing (base + A/E-derived)
- ✅ More direct control over final size

**Alternative (Strength → A/E → Sizing)**:
- ✅ Affects decision-making (A/E thresholds)
- ✅ More granular (only A/E-derived part affected)
- ❌ Timing issue (A/E calculated before pattern known)
- ❌ More complex (two-step process)

**Conclusion**: Current design makes sense due to timing constraints and simplicity. Strength effectively affects sizing (which is derived from A/E), achieving the same goal through a different path.

---

## Part 8: Next Steps

1. ✅ **Investigation Complete**: Understand current vs intended
2. ⏳ **Decision Needed**: Should strength affect A/E?
3. ⏳ **Implementation**: If yes, add `apply_strength_to_ae()` call
4. ⏳ **Testing**: Validate A/E adjustment doesn't break logic
5. ⏳ **Monitoring**: Track impact of A/E adjustment

---

## Appendix: Code References

- **A/E Computation**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py:3630-3655`
- **Action Planning**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py:plan_actions_v4()`
- **Override Application**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py:_apply_v5_overrides_to_action()`
- **Strength to A/E Function**: `src/intelligence/lowcap_portfolio_manager/pm/ae_calculator_v2.py:apply_strength_to_ae()`
- **Strength Override Lookup**: `src/intelligence/lowcap_portfolio_manager/pm/overrides.py:apply_pattern_strength_overrides()`

