# A/E Score Computation - Complete Breakdown

**Date**: 2025-01-XX  
**Purpose**: Understand A/E numeric ranges, transformations, and how strength should be applied

---

## Executive Summary

**A/E Ranges**: `[0.0, 1.0]` (always clamped)  
**Base Values**: `A_base = 0.5`, `E_base = 0.5`  
**Computation**: Linear accumulation with clamping (NOT sigmoid)  
**Current Strength Application**: **ADDITION** (`a_final = a_base + strength_effect`)  
**Proposed Strength Application**: **MULTIPLICATION** (`a_final = a_base * a_multiplier`)

**Key Finding**: A/E are already clamped to [0,1], so multiplication vs addition behaves differently. Need to understand which is better.

---

## Part 1: A/E Score Ranges

### Confirmed: [0.0, 1.0]

**Evidence from code**:

```128:129:src/intelligence/lowcap_portfolio_manager/pm/ae_calculator_v2.py
    # Clamp before strength (strength added later)
    A = max(0.0, min(1.0, A))
    E = max(0.0, min(1.0, E))
```

```141:142:src/intelligence/lowcap_portfolio_manager/pm/levers.py
    # Final calculation (bucket multiplier affects A, inverse affects E)
    a_final = _clamp(a_regime * bucket_multiplier, 0.0, 1.0)
    e_final = _clamp(e_regime / max(bucket_multiplier, 0.2), 0.0, 1.0)
```

```43:53:src/intelligence/lowcap_portfolio_manager/jobs/regime_ae_calculator.py
    # Neutral baseline for A/E
    A_BASE: float = 0.5
    E_BASE: float = 0.5
    
    # Intent delta cap (capped at ±0.4 per original design)
    INTENT_CAP: float = 0.4
    
    # Final A/E clamp range
    A_MIN: float = 0.0
    A_MAX: float = 1.0
    E_MIN: float = 0.0
    E_MAX: float = 1.0
```

**Conclusion**: A/E scores are **always** in range `[0.0, 1.0]`, clamped at multiple points.

---

## Part 2: A/E Computation Methods

### Method 1: A/E v2 (Flag-Driven)

**Location**: `src/intelligence/lowcap_portfolio_manager/pm/ae_calculator_v2.py::compute_ae_v2()`

**Process**:

1. **Start with base**:
   ```python
   A = config.a_base  # 0.5
   E = config.e_base  # 0.5
   ```

2. **Accumulate flag effects**:
   ```python
   for driver, weight in config.driver_weights.items():
       flags = regime_flags.get(driver, {})
       for flag_type in ["buy", "trim", "emergency"]:
           if flags.get(flag_type):
               effect = config.flag_effects.get(flag_type, 0)
               # effect = 0.15 (buy), 0.20 (trim), 0.40 (emergency)
               
               if flag_type == "buy":
                   if is_inverse:
                       delta_a = -effect * weight  # Risk-off
                       delta_e = +effect * weight
                   else:
                       delta_a = +effect * weight  # Risk-on
                       delta_e = -effect * weight
               
               A += delta_a
               E += delta_e
   ```

3. **Clamp**:
   ```python
   A = max(0.0, min(1.0, A))
   E = max(0.0, min(1.0, E))
   ```

**Example**:
- Base: `A = 0.5`, `E = 0.5`
- USDT.d buy flag (inverse, weight=1.0, effect=0.15):
  - `delta_a = -0.15 * 1.0 = -0.15`
  - `delta_e = +0.15 * 1.0 = +0.15`
- Result: `A = 0.35`, `E = 0.65` (clamped)

**Key Point**: **Linear accumulation** (add/subtract), then clamp. **NOT sigmoid**.

### Method 2: Legacy (Regime-Driven)

**Location**: `src/intelligence/lowcap_portfolio_manager/pm/levers.py::compute_levers()`

**Process**:

1. **Calculate intent deltas**:
   ```python
   intent_delta_a = (
       0.25 * hi_buy +
       0.15 * med_buy -
       0.15 * profit -
       0.25 * sell -
       0.30 * mock
   )
   intent_delta_a = _clamp(intent_delta_a, -0.4, 0.4)
   ```

2. **Calculate regime A/E**:
   ```python
   calculator = RegimeAECalculator()
   a_regime, e_regime = calculator.compute_ae_for_token(
       token_bucket=position_bucket,
       exec_timeframe=exec_timeframe,
       intent_delta_a=intent_delta_a,
       intent_delta_e=intent_delta_e,
   )
   ```

3. **Apply bucket multiplier**:
   ```python
   bucket_multiplier = _compute_bucket_multiplier(...)
   a_final = _clamp(a_regime * bucket_multiplier, 0.0, 1.0)
   e_final = _clamp(e_regime / max(bucket_multiplier, 0.2), 0.0, 1.0)
   ```

**Key Point**: Uses **multiplication** for bucket adjustment, but still clamped to [0,1].

---

## Part 3: Current Strength Application (Not Used)

### Function: `apply_strength_to_ae()`

**Location**: `src/intelligence/lowcap_portfolio_manager/pm/ae_calculator_v2.py`

**Current Implementation** (ADDITION):

```python
def apply_strength_to_ae(
    a_base: float,
    e_base: float,
    strength_mult: float,
    pattern_key: str = "",
    config: Optional[AEConfig] = None,
) -> Tuple[float, float, Dict[str, Any]]:
    config = config or AEConfig()
    
    # Convert multiplier to effect: 1.0 → 0, 1.5 → +0.25 (capped), 0.5 → -0.25 (capped)
    strength_effect = (strength_mult - 1.0)
    strength_effect = max(-config.strength_cap, min(config.strength_cap, strength_effect))
    # strength_cap = 0.25
    
    A_final = a_base + strength_effect  # ADDITION
    E_final = e_base - strength_effect  # Inverse: good pattern → less urgency to exit
    
    # Final clamp
    A_final = max(0.0, min(1.0, A_final))
    E_final = max(0.0, min(1.0, E_final))
    
    return A_final, E_final, diagnostics
```

**How It Works**:
- `strength_mult = 1.5` (good pattern)
- `strength_effect = 1.5 - 1.0 = 0.5` → capped at `0.25`
- `A_final = 0.5 + 0.25 = 0.75`
- `E_final = 0.5 - 0.25 = 0.25`

**Key Point**: Uses **ADDITION** with cap of ±0.25, then clamps to [0,1].

**Status**: Function exists but is **never called** in current flow.

---

## Part 4: Proposed Strength Application (MULTIPLICATION)

### How It Would Work

**Option A: Direct Multiplication**:
```python
a_final = a_base * a_multiplier
e_final = e_base * e_multiplier

# Then clamp
a_final = max(0.0, min(1.0, a_final))
e_final = max(0.0, min(1.0, e_final))
```

**Example**:
- `a_base = 0.5`, `a_multiplier = 1.2` (20% increase)
- `a_final = 0.5 * 1.2 = 0.6`
- `e_base = 0.5`, `e_multiplier = 0.8` (20% decrease)
- `e_final = 0.5 * 0.8 = 0.4`

**Option B: Multiplicative with Clamp**:
```python
# Apply multiplier, but ensure we don't exceed bounds
a_final = a_base * a_multiplier
if a_final > 1.0:
    a_final = 1.0
if a_final < 0.0:
    a_final = 0.0
```

**Option C: Multiplicative with Centering**:
```python
# Center around 0.5, then multiply
a_offset = (a_base - 0.5) * a_multiplier
a_final = 0.5 + a_offset
a_final = max(0.0, min(1.0, a_final))
```

---

## Part 5: Addition vs Multiplication Behavior

### Scenario: Base A = 0.5, Strength Adjustment = +20%

**Addition (Current)**:
- `strength_effect = +0.2` (capped at ±0.25)
- `a_final = 0.5 + 0.2 = 0.7`
- **Result**: Absolute increase of 0.2

**Multiplication (Proposed)**:
- `a_multiplier = 1.2`
- `a_final = 0.5 * 1.2 = 0.6`
- **Result**: Relative increase of 20% (0.1 absolute)

**Difference**: Addition gives **larger absolute change** for same "strength" signal.

### Scenario: Base A = 0.8, Strength Adjustment = +20%

**Addition**:
- `a_final = 0.8 + 0.2 = 1.0` (clamped)
- **Result**: Hits ceiling, loses information

**Multiplication**:
- `a_final = 0.8 * 1.2 = 0.96`
- **Result**: Proportional increase, stays below ceiling

**Difference**: Multiplication **preserves proportionality** better when near bounds.

### Scenario: Base A = 0.1, Strength Adjustment = +20%

**Addition**:
- `a_final = 0.1 + 0.2 = 0.3`
- **Result**: 3x increase (0.1 → 0.3)

**Multiplication**:
- `a_final = 0.1 * 1.2 = 0.12`
- **Result**: 20% increase (0.1 → 0.12)

**Difference**: Addition gives **larger relative change** when base is low.

---

## Part 6: Which is Better?

### Arguments for ADDITION

1. **Larger effect**: Same strength signal produces larger absolute change
2. **Current design**: Function already exists and uses addition
3. **Capped effect**: ±0.25 cap prevents extreme changes
4. **Works well at extremes**: Low base (0.1) gets meaningful boost

### Arguments for MULTIPLICATION

1. **Proportional**: 20% increase means 20% increase, regardless of base
2. **Preserves bounds**: Less likely to hit 0.0 or 1.0 ceiling
3. **Consistent**: Same multiplier has same relative effect everywhere
4. **Natural**: Matches how sizing works (multiplier on size_frac)

### Hybrid Approach

**Option**: Use multiplication but with **adaptive scaling**:

```python
# If base is near extremes, use addition (larger effect)
# If base is in middle, use multiplication (proportional)

if a_base < 0.3 or a_base > 0.7:
    # Near extremes: use addition for larger effect
    strength_effect = (a_multiplier - 1.0) * 0.5  # Scale down multiplier
    a_final = a_base + strength_effect
else:
    # Middle range: use multiplication for proportional effect
    a_final = a_base * a_multiplier

a_final = max(0.0, min(1.0, a_final))
```

**Complexity**: More complex, but handles both cases.

---

## Part 7: Recommendation

### For A/E Adjustment: Use MULTIPLICATION

**Reasoning**:
1. **Proportional effect**: 20% increase should mean 20% increase
2. **Preserves bounds**: Less likely to hit ceiling/floor
3. **Consistent**: Same multiplier has same relative effect
4. **Natural**: Matches how other multipliers work (sizing, exposure_skew)

**Implementation**:
```python
# Calculate a_multiplier and e_multiplier from outcomes
# (ROI determines magnitude, outcomes determine A vs E split)

a_final = a_base * a_multiplier
e_final = e_base * e_multiplier

# Clamp to bounds
a_final = max(0.0, min(1.0, a_final))
e_final = max(0.0, min(1.0, e_final))
```

**Multiplier Range**: `[0.8, 1.2]` (20% adjustment range, more conservative than sizing's [0.3, 3.0])

**Why Conservative Range**:
- A/E affects decision-making (more sensitive)
- Sizing affects position size (less sensitive)
- 20% A/E change is significant, 20% sizing change is moderate

---

## Part 8: Complete A/E Computation Flow

### Current Flow (Without Strength)

```
1. Start: A = 0.5, E = 0.5
   ↓
2. Accumulate flag effects (linear addition)
   - USDT.d buy: A -= 0.15, E += 0.15
   - Bucket trim: A -= 0.20, E += 0.20
   - ... (more flags)
   ↓
3. Clamp: A = max(0.0, min(1.0, A)), E = max(0.0, min(1.0, E))
   ↓
4. Apply bucket multiplier (multiplication)
   - a_final = clamp(a_regime * bucket_multiplier, 0.0, 1.0)
   - e_final = clamp(e_regime / bucket_multiplier, 0.0, 1.0)
   ↓
5. Use for sizing: position_size_frac = 0.10 + (a_final * 0.50)
```

### Proposed Flow (With Strength on A/E)

```
1. Start: A = 0.5, E = 0.5
   ↓
2. Accumulate flag effects (linear addition)
   ↓
3. Clamp: A = max(0.0, min(1.0, A)), E = max(0.0, min(1.0, E))
   ↓
4. Apply bucket multiplier (multiplication)
   ↓
5. Apply strength multipliers (multiplication) ← NEW
   - a_final = a_base * a_multiplier
   - e_final = e_base * e_multiplier
   - Clamp: a_final = max(0.0, min(1.0, a_final))
   ↓
6. Use for sizing: position_size_frac = 0.10 + (a_final * 0.50)
```

**Key Point**: Strength applied **after** all other adjustments, as a **final multiplier**.

---

## Part 9: Summary

### A/E Score Properties

- **Range**: `[0.0, 1.0]` (always clamped)
- **Base**: `0.5` (neutral)
- **Computation**: Linear accumulation (addition/subtraction), then clamp
- **NOT sigmoid**: No sigmoid transformation applied
- **Multiple clamps**: Clamped after flags, after bucket multiplier, after strength

### Strength Application

**Current (Not Used)**: ADDITION with ±0.25 cap
- `a_final = a_base + strength_effect`
- Larger absolute effect
- Can hit bounds more easily

**Proposed**: MULTIPLICATION with [0.8, 1.2] range
- `a_final = a_base * a_multiplier`
- Proportional effect
- Preserves bounds better

**Recommendation**: Use **multiplication** for proportional, consistent adjustments.

---

## Appendix: Code References

- **A/E v2 Computation**: `src/intelligence/lowcap_portfolio_manager/pm/ae_calculator_v2.py::compute_ae_v2()`
- **Legacy Computation**: `src/intelligence/lowcap_portfolio_manager/pm/levers.py::compute_levers()`
- **Strength Application (Not Used)**: `src/intelligence/lowcap_portfolio_manager/pm/ae_calculator_v2.py::apply_strength_to_ae()`
- **Constants**: `src/intelligence/lowcap_portfolio_manager/jobs/regime_ae_calculator.py::RegimeConstants`

