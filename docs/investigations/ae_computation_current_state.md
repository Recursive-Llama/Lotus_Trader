# A/E Computation - Current State

**Date**: 2025-01-XX  
**Purpose**: Clarify which A/E computation method is actually being used

---

## Current Implementation

**Location**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py:3630-3667`

```python
# Compute A/E - use v2 if enabled, otherwise legacy compute_levers
use_ae_v2 = pm_cfg.get("feature_flags", {}).get("ae_v2_enabled", False)

if use_ae_v2:
    # A/E v2: Flag-driven, strength is first-class
    regime_flags = extract_regime_flags(self.sb, token_bucket, book_id)
    a_base, e_base, ae_diag = compute_ae_v2(regime_flags, token_bucket)
    a_final = a_base
    e_final = e_base
else:
    # Legacy: compute_levers (regime-driven A + intent deltas + bucket multiplier)
    le = compute_levers(
        features,
        bucket_context=regime_context,
        position_bucket=token_bucket,
        bucket_config=bucket_cfg,
        exec_timeframe=self.timeframe,
    )
    a_final = float(le["A_value"])
    e_final = float(le["E_value"])
    position_size_frac = float(le.get("position_size_frac", 0.33))
```

**Default**: `ae_v2_enabled = False` → Uses **Legacy method** (`compute_levers`)

**To Enable v2**: Set `feature_flags.ae_v2_enabled = True` in PM config

---

## Method 1: Legacy (Currently Used by Default)

**Function**: `compute_levers()`  
**Location**: `src/intelligence/lowcap_portfolio_manager/pm/levers.py`

### How It Works

1. **Calculate intent deltas**:
   ```python
   intent_delta_a = (
       0.25 * hi_buy +
       0.15 * med_buy -
       0.15 * profit -
       0.25 * sell -
       0.30 * mock
   )
   intent_delta_a = clamp(intent_delta_a, -0.4, 0.4)
   ```

2. **Calculate regime A/E** (via `RegimeAECalculator`):
   ```python
   calculator = RegimeAECalculator()
   a_regime, e_regime = calculator.compute_ae_for_token(
       token_bucket=position_bucket,
       exec_timeframe=exec_timeframe,
       intent_delta_a=intent_delta_a,
       intent_delta_e=intent_delta_e,
   )
   ```
   
   **RegimeAECalculator Process**:
   - Reads regime driver states from DB (BTC, ALT, bucket, BTC.d, USDT.d)
   - For each driver × timeframe (macro/meso/micro):
     - Gets state (S0-S4)
     - Gets flags (buy, trim, emergency)
     - Calculates deltas from lookup tables
     - Applies driver weights and timeframe weights
   - Sums all deltas: `a_total = 0.5 + Σ(weighted_deltas)`
   - Adds intent deltas (capped at ±0.4)
   - Clamps to [0, 1]

3. **Apply bucket multiplier**:
   ```python
   bucket_multiplier = _compute_bucket_multiplier(...)
   a_final = clamp(a_regime * bucket_multiplier, 0.0, 1.0)
   e_final = clamp(e_regime / max(bucket_multiplier, 0.2), 0.0, 1.0)
   ```

4. **Calculate position sizing**:
   ```python
   position_size_frac = 0.10 + (a_final * 0.50)
   ```

**Key Characteristics**:
- Uses **multiplication** for bucket adjustment
- Uses **addition** for regime/intent deltas
- Final range: `[0.0, 1.0]` (clamped)
- Base: `0.5` (from `RegimeConstants.A_BASE`)

---

## Method 2: A/E v2 (Flag-Driven, Not Enabled by Default)

**Function**: `compute_ae_v2()`  
**Location**: `src/intelligence/lowcap_portfolio_manager/pm/ae_calculator_v2.py`

### How It Works

1. **Start with base**:
   ```python
   A = 0.5
   E = 0.5
   ```

2. **Extract regime flags**:
   ```python
   regime_flags = extract_regime_flags(sb, token_bucket, book_id)
   # Returns: {
   #   "usdtd": {"buy": True, "trim": False, "emergency": False},
   #   "bucket": {"buy": False, "trim": True, "emergency": False},
   #   ...
   # }
   ```

3. **Accumulate flag effects** (linear addition):
   ```python
   for driver, weight in driver_weights.items():
       flags = regime_flags.get(driver, {})
       for flag_type in ["buy", "trim", "emergency"]:
           if flags.get(flag_type):
               effect = flag_effects[flag_type]  # 0.15, 0.20, 0.40
               
               if flag_type == "buy":
                   if is_inverse:  # usdtd, btcd
                       delta_a = -effect * weight  # Risk-off
                       delta_e = +effect * weight
                   else:
                       delta_a = +effect * weight  # Risk-on
                       delta_e = -effect * weight
               
               A += delta_a
               E += delta_e
   ```

4. **Clamp**:
   ```python
   A = max(0.0, min(1.0, A))
   E = max(0.0, min(1.0, E))
   ```

**Key Characteristics**:
- Uses **addition only** (no multiplication)
- Simpler: just flags → deltas → sum → clamp
- Final range: `[0.0, 1.0]` (clamped)
- Base: `0.5` (from `AEConfig.a_base`)

---

## Comparison

| Aspect | Legacy (`compute_levers`) | v2 (`compute_ae_v2`) |
|--------|--------------------------|---------------------|
| **Status** | ✅ **Currently Used** (default) | ⚠️  Available but disabled by default |
| **Method** | Regime states + intent + bucket multiplier | Flag-driven (simpler) |
| **Computation** | Addition (regime/intent) + Multiplication (bucket) | Addition only |
| **Complexity** | More complex (5 drivers × 3 timeframes × states/flags) | Simpler (just flags) |
| **Base** | 0.5 | 0.5 |
| **Range** | [0.0, 1.0] (clamped) | [0.0, 1.0] (clamped) |
| **Bucket Effect** | Multiplicative | Not applied (would need separate step) |

---

## Which One is Actually Running?

**Answer**: **Legacy (`compute_levers`)** is currently running.

**Evidence**:
- Default: `ae_v2_enabled = False` (when flag not found)
- No PM config in `learning_configs` table (checked database)
- No `feature_flags` in `pm_config.jsonc` file
- Code comment: "Legacy: compute_levers"
- No v2 logs found (would log `"AE_V2: ..."`)

**Current State**:
- Config loaded from: `src/config/pm_config.jsonc` (no `feature_flags` key)
- DB config: None (no PM entry in `learning_configs`)
- Result: `pm_cfg.get("feature_flags", {}).get("ae_v2_enabled", False)` → `False`

**To Enable v2**: Need to add to database:
```sql
INSERT INTO learning_configs (module_id, config_data) 
VALUES ('pm', '{"feature_flags": {"ae_v2_enabled": true}}')
ON CONFLICT (module_id) DO UPDATE 
SET config_data = jsonb_set(config_data, '{feature_flags,ae_v2_enabled}', 'true');
```

**To Check**: Look for logs:
- Legacy: No specific log (uses `compute_levers`)
- v2: Logs `"AE_V2: %s bucket=%s | flags → A=%.3f E=%.3f"`

---

## Summary

**Currently Used**: Legacy method (`compute_levers`)
- Regime-driven (5 drivers × 3 timeframes)
- Intent deltas (capped at ±0.4)
- Bucket multiplier (multiplicative)
- Range: [0.0, 1.0], Base: 0.5

**Available but Disabled**: v2 method (`compute_ae_v2`)
- Flag-driven (simpler)
- Just flags → deltas → sum → clamp
- Range: [0.0, 1.0], Base: 0.5

**For Strength Application**: Both methods produce A/E in [0.0, 1.0] range, so multiplication vs addition behavior is the same regardless of which method is used.

