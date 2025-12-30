# Scaling In/Out & A/E v2 Implementation Plan

**Date**: 2025-12-29  
**Status**: Ready for Implementation (v3 - authoritative definitions locked)  
**Scope**: Three interconnected systems

---

## Overview

This document covers implementation of:

1. **Scaling In/Out Rework** — Trim pool, sizing changes, gating changes
2. **A/E Posture System v2** — Flag-driven, Strength as first-class
3. **Episode Token-Gating (Blocking)** — Deterministic safety latch, NOT learned
4. **Tuning System** — Mined, generalized learning for mechanics

---

# AUTHORITATIVE DEFINITIONS (Read First)

> **These definitions are final. All implementation must follow them.**

## Market Attempt Ordering

An **attempt** is the atomic unit of trend lifecycle:

- **Attempt begins**: `S0 → S1`
- **Attempt ends**: `S3` (success) or `S0` (failure)
- **It is impossible to reach S3 without passing through S2 at least once**

Flip-flops (`S1 ↔ S2`) do **not** end the attempt. They are normal oscillations within a single attempt.

## Episode Definitions

### S1 Episode
- **Start**: `S0 → S1` (attempt begins)
- **End**: Attempt ends (`S3` or `S0`)
- **Success**: Attempt ends at S3
- **Failure**: Attempt ends at S0

### S2 Episode
- **Start**: First `S1 → S2` within the attempt (set `s2_started = True`)
- **End**: Attempt ends (`S3` or `S0`)
- **Success**: Attempt ends at S3 (always implies S2 started, since S3 requires S2)
- **Failure**: Attempt ends at S0 **and** `s2_started == True`
- **Flip-flops** (`S2 ↔ S1`) do **not** end the episode

### Key Booleans (Track Per Attempt)
```python
# In position.features.attempt_tracking
{
    "attempt_active": True,           # S0 → S1 happened, not yet terminal
    "s2_started": False,              # S1 → S2 has occurred at least once
    "entered_s1": False,              # We took an S1 entry this attempt
    "entered_s2": False,              # We took an S2 entry this attempt
}
```

## Emergency vs Terminal Failure

| Event | What It Is | What It Is NOT |
|-------|------------|----------------|
| **Emergency exit** | Risk protection event (EMA333 break) | NOT attempt failure |
| **Terminal failure** | Attempt ends at S0 | NOT the same as emergency |

Emergency can happen during S3 without the attempt immediately failing.
Terminal failure only happens when structure fully collapses to S0.

## The 4-Quadrant Outcome Model

Every episode outcome is classified by:

| Decision | Attempt Outcome | Meaning | Blocking? | Learning? |
|----------|-----------------|---------|-----------|-----------|
| **Acted** | **Failed** | Bad call | ✅ YES | ✅ YES (failure) |
| **Acted** | **Succeeded** | Good call | ❌ NO | ✅ YES (success) |
| **Skipped** | **Failed** | Correct skip | ❌ NO | ✅ YES (correct_skip) |
| **Skipped** | **Succeeded** | Missed opportunity | ❌ NO | ✅ YES (missed) |

**Blocking only triggers on acted + failed.**
**Success can be observed without participating.**

## Trim Pool Rule (Single Boolean)

> **"Has recovery started on this pool?"**

- **Recovery starts**: First S2 dip buy OR first DX buy
- **Before recovery starts**: Trims accumulate into pool
- **After recovery starts**: New trim wipes old pool, creates fresh

**Explicit**: Once `recovery_started=True`, the pool remainder is **never carried forward**. The next trim overwrites it completely — that remainder becomes locked profit.

No partial carry-over. No mixing. One boolean.

## Extraction Ratio (E Dampening Rule)

> **E should care more about what we've taken out than how big the position still is.**

```
extraction_ratio = total_extracted_usd / total_allocation_usd
```

| Extraction | Multiplier | Meaning |
|------------|------------|---------|
| 0% | **1.5** | Full risk — trim aggressively |
| 50%+ | **1.0** | Half extracted — moderate trims |
| 100%+ | **0.3** | House money — ride the trend |
| 300%+ | **0.1** | Big winner — very selective trims |

This enforces a trend-following truth: **as a trend proves itself, trimming should slow down — not speed up.**

## Anti-Requirements (Do NOT Implement)

- ❌ **No `recovery_cycles` table** — All signals go through `pattern_episode_events`
- ❌ **No fabricated S2 levers** — Use existing: `s2_halo_mult`, `ts_min`, slope guards
- ❌ **No token-specific tuning** — Tuning uses coarse scope only

---

# PART 1: Scaling In/Out

## 1.1 Bug Fix: S2/S3 Buy History Recording

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`  
**Location**: `_update_execution_history()` method, lines ~1665-1694

### Current (Broken)
```python
if decision_type in ["add", "entry"]:
    if "s1" in signal.lower() or "buy_signal" in signal.lower():
        execution_history["last_s1_buy"] = {...}
    elif "s2" in signal.lower():  # ❌ Never matches "buy_flag"
        execution_history["last_s2_buy"] = {...}
    elif "s3" in signal.lower():  # ❌ Never matches "buy_flag"
        execution_history["last_s3_buy"] = {...}
```

### Fixed
```python
if decision_type in ["add", "entry"]:
    state = (reasons.get("state") or "").upper()
    
    # Log warning if state is missing (so we catch it early)
    if not state:
        pm_logger.warning(
            "BUY_HISTORY_NO_STATE: %s signal=%s reasons=%s (fallback to signal parsing)",
            token_ticker, signal, reasons
        )
    
    if "buy_signal" in signal.lower() or state == "S1":
        execution_history["last_s1_buy"] = {...}
    elif state == "S2":
        execution_history["last_s2_buy"] = {...}
    elif state == "S3":
        execution_history["last_s3_buy"] = {...}
    elif "reclaimed" in signal.lower() or "ema333" in signal.lower():
        execution_history["last_reclaim_buy"] = {...}
```

**Note**: If `state` is missing from `reasons`, we log a warning (once per token per day throttle recommended) and fall back to signal parsing. This catches any action paths where `reasons` lacks state.

---

## 1.2 S1 Entry Sizing Update

**File**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py`  
**Function**: `_a_to_entry_size()`

### Current
```python
if state == "S1" and buy_signal:
    if a_final >= 0.7:
        return 0.50  # Aggressive
    elif a_final >= 0.3:
        return 0.30  # Normal
    else:
        return 0.10  # Patient
```

### New
```python
if state == "S1" and buy_signal:
    if a_final >= 0.7:
        return 0.90  # Aggressive
    elif a_final >= 0.3:
        return 0.60  # Normal
    else:
        return 0.30  # Patient
```

---

## 1.3 Trim Sizing Update

**File**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py`  
**Function**: `_e_to_trim_size()`

### Current
```python
def _e_to_trim_size(e_final: float) -> float:
    if e_final >= 0.7:
        return 0.10  # Aggressive
    elif e_final >= 0.3:
        return 0.05  # Normal
    else:
        return 0.03  # Patient
```

### New
```python
def _e_to_trim_size(e_final: float) -> float:
    if e_final >= 0.7:
        return 0.60  # Aggressive
    elif e_final >= 0.3:
        return 0.30  # Normal
    else:
        return 0.15  # Patient
```

---

## 1.4 Trim Multiplier: Extraction-Based (REFINED)

**File**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py`  
**Location**: `plan_actions_v4()`, lines ~379-389

### The Key Insight

> **E (exit pressure) should care more about what we've already taken out than how big the position still is.**

This lets us "ride the trend" once we've de-risked, instead of over-trimming winners.

### Signal for E Modification

| Signal | Effect on E |
|--------|-------------|
| **Extraction ratio** | High extraction → dampen E (ride trend) |

**Demoted signals (not used):**
- Crowding ratio — handled by 1.5× at 0% extraction
- Trim pool size — not a good proxy for "should we trim?"

### Correct Definition
```python
# ============================================
# 1. EXTRACTION RATIO (primary - dampens E)
# ============================================
# How much have we already taken out vs put in?
extraction_ratio = total_extracted_usd / total_allocation_usd if total_allocation_usd > 0 else 0.0

# Extraction-based trim multiplier
# More extraction = less urgency to trim = ride the trend
if extraction_ratio >= 3.0:
    extraction_multiplier = 0.1   # Big winner - very selective trims
elif extraction_ratio >= 1.0:
    extraction_multiplier = 0.3   # House money - ride the trend
elif extraction_ratio >= 0.5:
    extraction_multiplier = 1.0   # Half extracted - moderate
else:
    extraction_multiplier = 1.5   # Full risk - trim aggressively

# ============================================
# 2. CROWDING RATIO (secondary - removed)
# ============================================
# With the new extraction-based curve, crowding is already handled:
# - 0% extraction already gets 1.5× (aggressive early trimming)
# - No need to double-amplify
# 
# If you want to re-add crowding later:
# net_capital_in_trade = total_allocation_usd - total_extracted_usd
# capital_deployed_ratio = net_capital_in_trade / max_allocation_usd
# if capital_deployed_ratio >= 0.8 and extraction_ratio < 0.5:
#     crowding_multiplier = 1.25  # Optional boost

# ============================================
# FINAL TRIM MULTIPLIER
# ============================================
trim_multiplier = extraction_multiplier  # Extraction-based only

# Log for visibility
pm_logger.debug(
    "TRIM_MULT: %s extraction_ratio=%.2f → multiplier=%.2f",
    token_ticker, extraction_ratio, trim_multiplier
)
```

### What This Enforces

| Phase | Extraction | Multiplier | Behavior |
|-------|------------|------------|----------|
| Early | 0% | **1.5** | Trim aggressively, reduce risk |
| Mid | 50%+ | **1.0** | Moderate trims |
| Late | 100%+ | **0.3** | Ride the trend |
| Big winner | 300%+ | **0.1** | Very selective trims |

**Key insight**: The multiplier curve is all you need. No separate crowding logic required.

**Implementation note**: Pass `wallet_balance` as a parameter to `plan_actions_v4()` from the caller (e.g., `pm_core_tick`). This ensures consistent value across all positions in a single tick.

### Also Update
```python
max_trim_frac = float(os.getenv("PM_MAX_TRIM_FRAC", "0.9"))  # (was 0.5)
```

---

## 1.5 Trim Pool Data Model (CORRECTED)

**File**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py`  
**Location**: `plan_actions_v4()` - add to execution_history structure

### Data Structure (Simplified)
```python
# In execution_history (stored in position.features.pm_execution_history)
"trim_pool": {
    "usd_basis": 0.0,           # Pool value for sizing (frozen at recovery start)
    "recovery_started": False,  # Has S2 or DX started using this pool?
    "dx_count": 0,              # 0-3 DX buys used from this pool
    "dx_last_price": None,      # Last DX fill price (for step ladder)
    "dx_next_arm": None,        # Next price level to arm DX
}
```

> **Note**: Removed `usd_accumulated` and `s2_used`.
> - `usd_basis` is what we size from (updated on each trim until recovery starts)
> - `s2_used` is redundant: S2 clears the pool immediately, so there's nothing left to track

### Pool Lifecycle

```python
def _empty_pool():
    """Return empty pool structure."""
    return {
        "usd_basis": 0.0,
        "recovery_started": False,
        "dx_count": 0,
        "dx_last_price": None,
        "dx_next_arm": None,
    }


def on_trim(execution_history, trim_usd):
    """Called when a trim happens."""
    pool = execution_history.get("trim_pool") or _empty_pool()
    
    if pool.get("recovery_started", False):
        # Recovery already started - new trim creates FRESH pool
        # Old pool remainder becomes locked profit (done, gone)
        execution_history["trim_pool"] = {
            "usd_basis": trim_usd,
            "recovery_started": False,
            "dx_count": 0,
            "dx_last_price": None,
            "dx_next_arm": None,
        }
    else:
        # No recovery yet - ACCUMULATE into usd_basis
        pool["usd_basis"] = pool.get("usd_basis", 0) + trim_usd
        execution_history["trim_pool"] = pool


def on_s2_dip_buy(execution_history, rebuy_usd):
    """Called when S2 dip buy happens. Clears pool immediately."""
    pool = execution_history.get("trim_pool") or _empty_pool()
    pool_basis = pool.get("usd_basis", 0)
    
    # Unused portion becomes locked profit (not tracked, just gone)
    locked_profit = pool_basis - rebuy_usd
    
    # Clear pool entirely (S2 is one-shot)
    execution_history["trim_pool"] = _empty_pool()
    
    return locked_profit


def on_dx_buy(execution_history, fill_price, atr, dx_atr_mult=6.0):
    """Called when DX buy happens. Uses STEP LADDER (each arm anchored to last fill)."""
    pool = execution_history.get("trim_pool") or _empty_pool()
    
    pool["recovery_started"] = True
    pool["dx_count"] = pool.get("dx_count", 0) + 1
    pool["dx_last_price"] = fill_price
    # STEP LADDER: next arm is 6×ATR below THIS fill (arms walk down with fills)
    pool["dx_next_arm"] = fill_price - (dx_atr_mult * atr)
    
    # If 3 DX buys done, clear pool (remainder is locked profit)
    if pool["dx_count"] >= 3:
        execution_history["trim_pool"] = _empty_pool()
    else:
        execution_history["trim_pool"] = pool
```

### Key Rules
1. **Trims accumulate** into `usd_basis` UNTIL recovery starts
2. **New trim after recovery** creates fresh pool (old pool remainder is locked profit)
3. **S2 dip buy** clears pool immediately (one-shot, remainder locked)
4. **DX buys** use step ladder (each arm anchored to last fill), count up to 3, then clear
5. **Sizing always from `usd_basis`** — the frozen value at recovery start

### DX Ladder Type: STEP LADDER (Explicit Choice)

| Ladder Type | Description | Arms Move With Price? |
|-------------|-------------|----------------------|
| **Step Ladder (CHOSEN)** | Each arm anchored to last fill | Yes, walk down with fills |
| Fixed Ladder | All arms anchored to first fill | No, fixed at start |

We chose Step Ladder because:
- Arms naturally space out as price falls
- Tuning `dx_atr_mult` has consistent meaning regardless of which arm we're on
- Easier to reason about: "always 6×ATR below last buy"

---

## 1.6 S2 Dip Buy Gating (Trim Pool Required)

**File**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py`  
**Location**: `plan_actions_v4()`, S2 buy handling

### New Gating Logic
```python
if buy_flag and state == "S2":
    is_flat = total_quantity <= 0
    pool = exec_history.get("trim_pool") or {}
    pool_basis = pool.get("usd_basis", 0)
    has_pool = pool_basis > 0
    recovery_started = pool.get("recovery_started", False)
    
    # S2 dip allowed if: flat OR (has pool AND DX not started)
    # Note: no "s2_used" check needed - S2 clears pool immediately
    can_s2_dip = is_flat or (has_pool and not recovery_started)
    
    if can_s2_dip:
        if is_flat:
            # Case 1: Flat - use remaining allocation
            base_size = _a_to_entry_size(a_final, state, False, True, False)
            notional = usd_alloc_remaining * base_size
        else:
            # Case 2: Post-trim - size from pool_basis (NOT decrementing balance)
            if a_final >= 0.7:
                rebuy_frac = 0.60
            elif a_final >= 0.3:
                rebuy_frac = 0.30
            else:
                rebuy_frac = 0.10
            
            notional = pool_basis * rebuy_frac
            notional = min(notional, usd_alloc_remaining)  # Safety cap
        
        # Create action...
        # After execution, call on_s2_dip_buy() which clears the pool
```

---

## 1.7 DX Buy Gating (6×ATR Ladder, Tunable)

**File**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py`  
**Location**: `plan_actions_v4()`, S3 buy handling

### New Gating Logic
```python
if buy_flag and state == "S3":
    # DX zone check: EMA144 < price < EMA333
    ema144 = uptrend.get("ema", {}).get("ema144", 0)
    ema333 = uptrend.get("ema", {}).get("ema333", 0)
    price = uptrend.get("price", 0)
    in_dx_zone = ema144 < price < ema333
    
    pool = exec_history.get("trim_pool") or {}
    pool_basis = pool.get("usd_basis", 0)
    has_pool = pool_basis > 0
    dx_count = pool.get("dx_count", 0)
    dx_next_arm = pool.get("dx_next_arm")
    recovery_started = pool.get("recovery_started", False)
    
    # DX gating: in zone, has pool, < 3 DX, price at or below arm (or first buy)
    # Note: no s2_used check - if S2 used, pool is cleared so has_pool = False
    can_dx = (
        in_dx_zone and
        has_pool and
        dx_count < 3 and
        (dx_next_arm is None or price <= dx_next_arm)
    )
    
    if can_dx:
        # Per-buy sizing from pool_basis (NOT decrementing)
        if a_final >= 0.7:
            dx_frac = 0.20  # 3 buys × 20% ≈ 60% total
        elif a_final >= 0.3:
            dx_frac = 0.10  # 3 buys × 10% ≈ 30% total
        else:
            dx_frac = 0.0333  # 3 buys × 3.33% ≈ 10% total
        
        notional = pool_basis * dx_frac
        notional = min(notional, usd_alloc_remaining)  # Safety cap
        
        # Get tunable ATR multiplier (default 6.0)
        # TODO: Integrate with tuning system
        dx_atr_mult = tuned_controls.get("dx_atr_mult", 6.0)
        atr = uptrend.get("atr", 0)
        
        # Create action...
        # After execution, call on_dx_buy(fill_price, atr, dx_atr_mult)
```

### Tuning Integration (Future)

Add `dx_atr_mult` to the existing tuning override system:
```python
# In apply_pattern_execution_overrides():
apply_override('tuning_dx_atr', 'dx_atr_mult', 2.0, 12.0)  # Range: 2-12× ATR
```

This allows learning to adjust ladder spacing per pattern.

---

## 1.8 Remove first_dip_buy_flag

**Files to modify**:
- `src/intelligence/lowcap_portfolio_manager/pm/actions.py`
- `src/intelligence/lowcap_portfolio_manager/jobs/uptrend_engine_v4.py`

### In actions.py
Remove all references to `first_dip_buy_flag`:
- Line ~339: Remove from flag extraction
- Line ~643-650: Remove log detection
- Line ~874, 922, 926, 950: Remove from conditionals

### In uptrend_engine_v4.py
Remove first_dip_buy_flag computation (search for `first_dip_buy_flag`).

---

## 1.9 EMA333 Reclaim Rebuy (FIXED - Based on Exit Value)

**File**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py`  
**Location**: `plan_actions_v4()`, reclaimed_ema333 handling (~lines 1003-1078)

### New Logic (Fixed)
```python
if state == "S3" and uptrend.get("reclaimed_ema333"):
    last_emergency = exec_history.get("last_emergency_exit", {})
    rebuy_used = last_emergency.get("rebuy_used", False)
    exit_value_usd = last_emergency.get("exit_value_usd", 0)
    
    if last_emergency and not rebuy_used and exit_value_usd > 0:
        # Fractional rebuy sizing - BASED ON EXIT VALUE, not remaining allocation
        if a_final >= 0.7:
            rebuy_frac = 0.60
        elif a_final >= 0.3:
            rebuy_frac = 0.30
        else:
            rebuy_frac = 0.10
        
        rebuy_notional = exit_value_usd * rebuy_frac
        rebuy_notional = min(rebuy_notional, usd_alloc_remaining)  # Safety cap
        
        # Create action with rebuy_notional...
        
        # Mark rebuy as used (one-time)
        exec_history["last_emergency_exit"]["rebuy_used"] = True
```

### Emergency Exit Recording
```python
# When emergency exit happens:
# IMPORTANT: Capture value BEFORE the sell order, not after
# This avoids slippage affecting the reclaim rebuy sizing
total_value_exited = total_quantity * current_price

exec_history["last_emergency_exit"] = {
    "timestamp": now_iso,
    "exit_value_usd": total_value_exited,  # What we intended to exit with
    "rebuy_used": False  # Not yet used for reclaim rebuy
}
```

**Note**: Use pre-execution value to ensure consistent sizing. If you use post-execution value, slippage would reduce reclaim size, which may or may not be desired.

---

# PART 2: A/E Posture System v2

## 2.1 New A/E Calculator

**New File**: `src/intelligence/lowcap_portfolio_manager/pm/ae_calculator_v2.py`

```python
"""
A/E Posture Calculator v2

Flag-driven, no regime soup. Strength is first-class.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AEConfig:
    """Configuration for A/E calculation."""
    
    # Driver weights (sum effects, higher = more influence)
    driver_weights: Dict[str, float] = None
    
    # Flag effects (base delta per flag type)
    flag_effects: Dict[str, float] = None
    
    # Strength caps
    strength_cap: float = 0.25
    
    # Base values
    a_base: float = 0.5
    e_base: float = 0.5
    
    def __post_init__(self):
        if self.driver_weights is None:
            self.driver_weights = {
                "usdtd": 1.0,    # Strongest (inverse)
                "bucket": 0.9,   # Local signal
                "btcd": 0.7,     # Inverse
                "alt": 0.5,      # Optional
                "btc": 0.3,      # Weakest
            }
        if self.flag_effects is None:
            self.flag_effects = {
                "buy": 0.15,
                "trim": 0.20,
                "emergency": 0.40,
            }


# Inverse drivers (their BUY = our risk-off)
INVERSE_DRIVERS = {"usdtd", "btcd"}


def compute_ae_v2(
    regime_flags: Dict[str, Dict[str, bool]],
    token_bucket: str = "unknown",
    config: Optional[AEConfig] = None,
) -> Tuple[float, float, Dict[str, Any]]:
    """
    Compute A/E from active flags.
    
    Args:
        regime_flags: Dict of driver -> {"buy": bool, "trim": bool, "emergency": bool}
                     Drivers: "usdtd", "bucket", "btcd", "alt", "btc"
        token_bucket: For logging
        config: Optional configuration (uses defaults if None)
    
    Returns:
        Tuple of (A, E, diagnostics)
    """
    config = config or AEConfig()
    
    A = config.a_base
    E = config.e_base
    
    diagnostics = {
        "base": {"A": config.a_base, "E": config.e_base},
        "flag_contributions": [],
    }
    
    for driver, weight in config.driver_weights.items():
        flags = regime_flags.get(driver, {})
        is_inverse = driver in INVERSE_DRIVERS
        
        for flag_type in ["buy", "trim", "emergency"]:
            if not flags.get(flag_type):
                continue
            
            effect = config.flag_effects.get(flag_type, 0)
            
            # Determine direction
            if flag_type == "buy":
                if is_inverse:
                    delta_a = -effect * weight  # Risk-off
                    delta_e = +effect * weight
                else:
                    delta_a = +effect * weight  # Risk-on
                    delta_e = -effect * weight
            
            elif flag_type == "trim":
                if is_inverse:
                    delta_a = +effect * weight  # Risk-on (dominance falling)
                    delta_e = -effect * weight
                else:
                    delta_a = -effect * weight  # Risk-off
                    delta_e = +effect * weight
            
            elif flag_type == "emergency":
                # Emergency is always risk-off (reduce exposure)
                delta_a = -effect * weight
                delta_e = +effect * weight
            
            A += delta_a
            E += delta_e
            
            diagnostics["flag_contributions"].append({
                "driver": driver,
                "flag": flag_type,
                "weight": weight,
                "inverse": is_inverse,
                "delta_a": round(delta_a, 4),
                "delta_e": round(delta_e, 4),
            })
    
    # Clamp before strength (strength added later)
    A = max(0.0, min(1.0, A))
    E = max(0.0, min(1.0, E))
    
    diagnostics["after_flags"] = {"A": round(A, 4), "E": round(E, 4)}
    
    # Log computation
    active_flags = {d: [f for f, v in fl.items() if v] for d, fl in regime_flags.items() if any(fl.values())}
    logger.info(
        "A/E COMPUTED: bucket=%s | flags=%s | base: A=%.3f E=%.3f | after_flags: A=%.3f E=%.3f",
        token_bucket,
        active_flags,
        config.a_base, config.e_base,
        A, E,
    )
    
    return A, E, diagnostics


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
    
    Args:
        a_base: Base A from flags
        e_base: Base E from flags
        strength_mult: Learned strength multiplier (1.0 = neutral)
        pattern_key: For logging
        config: Optional configuration
    
    Returns:
        Tuple of (A_final, E_final, diagnostics)
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
    
    diagnostics = {
        "strength_mult": round(strength_mult, 4),
        "strength_effect": round(strength_effect, 4),
        "a_base": round(a_base, 4),
        "e_base": round(e_base, 4),
        "A_final": round(A_final, 4),
        "E_final": round(E_final, 4),
    }
    
    logger.info(
        "STRENGTH APPLIED: pattern=%s | strength=%.3f (effect=%.3f) | A: %.3f → %.3f | E: %.3f → %.3f",
        pattern_key,
        strength_mult, strength_effect,
        a_base, A_final,
        e_base, E_final,
    )
    
    return A_final, E_final, diagnostics
```

---

## 2.2 Regime Flag Extraction

**In `ae_calculator_v2.py`**:

```python
def extract_regime_flags(
    sb_client,
    token_bucket: str,
    book_id: str = "onchain_crypto",
) -> Dict[str, Dict[str, bool]]:
    """
    Extract current flags from regime driver positions.
    
    Returns:
        Dict of driver -> {"buy": bool, "trim": bool, "emergency": bool}
    """
    flags = {}
    
    # Map bucket to driver name
    bucket_driver = token_bucket  # "nano", "small", "mid", "big"
    
    # Drivers to check
    drivers = {
        "usdtd": "USDT.d",
        "bucket": bucket_driver,
        "btcd": "BTC.d",
        "alt": "ALT",
        "btc": "BTC",
    }
    
    for key, ticker in drivers.items():
        try:
            result = (
                sb_client.table("lowcap_positions")
                .select("features")
                .eq("token_ticker", ticker)
                .eq("status", "regime_driver")
                .eq("book_id", book_id)
                .limit(1)
                .execute()
            )
            
            if result.data:
                features = result.data[0].get("features", {})
                uptrend = features.get("uptrend_engine_v4", {})
                
                flags[key] = {
                    "buy": uptrend.get("buy_signal", False) or uptrend.get("buy_flag", False),
                    "trim": uptrend.get("trim_flag", False),
                    "emergency": uptrend.get("emergency_exit", False),
                }
            else:
                flags[key] = {"buy": False, "trim": False, "emergency": False}
        except Exception as e:
            logger.warning(f"Failed to get regime flags for {ticker}: {e}")
            flags[key] = {"buy": False, "trim": False, "emergency": False}
    
    return flags
```

---

## 2.3 Strength Lookup (FIXED - Explicit Return)

**Modify**: `src/intelligence/lowcap_portfolio_manager/pm/overrides.py`

Add explicit `strength_mult` return instead of reverse-engineering:

```python
def apply_pattern_strength_overrides(
    pattern_key: str,
    action_category: str,
    scope: Dict[str, Any],
    base_levers: Dict[str, float],
    sb_client: Optional[Client] = None,
    feature_flags: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, float], float]:  # NEW: Return (adjusted_levers, strength_mult)
    """
    Apply capital lever overrides (size_mult) from pm_overrides.
    
    Returns:
        Tuple of (adjusted levers dict, strength_mult)
    """
    # ... existing logic ...
    
    if total_weight == 0:
        return base_levers, 1.0  # Neutral strength
    
    final_mult = sum(weighted_mults) / total_weight
    final_mult = _clamp(final_mult, 0.3, 3.0)
    
    adjusted = {
        'A_value': base_levers.get('A_value', 0.5),
        'E_value': base_levers.get('E_value', 0.5),
        'position_size_frac': _clamp(
            base_levers.get('position_size_frac', 0.33) * final_mult,
            0.0, 1.0,
        ),
    }
    
    return adjusted, final_mult  # Return the actual multiplier
```

---

## 2.4 Integration into PM Core Tick

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

### Stage 1: Compute base A/E from flags (early)

```python
from src.intelligence.lowcap_portfolio_manager.pm.ae_calculator_v2 import (
    compute_ae_v2,
    extract_regime_flags,
    apply_strength_to_ae,
)

# Compute base A/E from flags
regime_flags = extract_regime_flags(self.sb, token_bucket, self.book_id)
a_base, e_base, ae_diag = compute_ae_v2(regime_flags, token_bucket)

levers = {
    "A_value": a_base,
    "E_value": e_base,
    "position_size_frac": 0.10 + (a_base * 0.50),  # Legacy
    "diagnostics": ae_diag,
    "regime_flags": regime_flags,
}
```

### Stage 2: Apply strength after action determined (in plan_actions_v4)

```python
# After determining action type, before sizing:
from src.intelligence.lowcap_portfolio_manager.pm.overrides import (
    apply_pattern_strength_overrides,
)

# Look up strength
_, strength_mult = apply_pattern_strength_overrides(
    pattern_key=pattern_key,
    action_category="entry",
    scope=scope,
    base_levers={"A_value": a_base, "E_value": e_base, "position_size_frac": 0.5},
    sb_client=sb_client,
)

# Apply to A/E
a_final, e_final, strength_diag = apply_strength_to_ae(
    a_base, e_base, strength_mult, pattern_key
)

# Now use a_final, e_final for sizing
```

---

# PART 3: Episode Token-Gating (BLOCKING — Not Learned)

> **CRITICAL DISTINCTION**: Blocking is NOT learned. It's a **deterministic runtime safety latch**.
> Tuning (Part 4) is learned. These are completely separate systems.

## 3.1 Concept

If we **acted** (took an entry) and the attempt fails (ends at S0), block re-entry for that **token + timeframe** until a successful episode is observed.

| Entry Taken | If Attempt Fails (ends at S0) | Blocks | Until |
|-------------|-------------------------------|--------|-------|
| S1 entry | S1 + S2 blocked | One successful episode observed (we don't have to participate) |
| S2 entry | S2 blocked only | One successful episode observed |

**Key Asymmetry:**
- **Failure requires acting** — if we skipped and the attempt failed, we made the right call (no block)
- **Success can be observed** — if the attempt succeeds, unblock even if we didn't participate

**Failure Definitions (Aligned with Authoritative Ordering):**
- **S1 failure** = We entered in S1 AND the attempt ended at S0 (not S3)
- **S2 failure** = We entered in S2 AND the attempt ended at S0 (and `s2_started == True`)
- **Success** = Attempt reaches S3 (regardless of whether we bought)

> Note: S2 cannot fail directly to S0. It may flip-flop to S1, but the episode only ends at terminal S3 or S0.

**Callback Locations (Explicit):**

| Callback | When to Call | Where in Code |
|----------|--------------|---------------|
| `record_entry_failure(S1)` | Attempt ends at S0 AND `entered_s1 == True` | `pm_core_tick._process_episode_logging()` |
| `record_entry_failure(S2)` | Attempt ends at S0 AND `entered_s2 == True` | `pm_core_tick._process_episode_logging()` |
| `record_episode_success()` | Attempt ends at S3 | `pm_core_tick._process_episode_logging()` |

## 3.2 Data Model

**Use a simple table for cross-position tracking:**

```sql
CREATE TABLE token_timeframe_blocks (
    token_contract TEXT NOT NULL,
    token_chain TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    book_id TEXT NOT NULL DEFAULT 'onchain_crypto',
    
    -- Block state (deterministic, not learned)
    blocked_s1 BOOLEAN DEFAULT FALSE,
    blocked_s2 BOOLEAN DEFAULT FALSE,
    
    -- Timestamps for unblock logic
    last_s1_failure_ts TIMESTAMPTZ,
    last_s2_failure_ts TIMESTAMPTZ,
    last_success_ts TIMESTAMPTZ,
    
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (token_contract, token_chain, timeframe, book_id)
);
```

## 3.3 Implementation

### On Attempt Failure (Terminal S0)
```python
def record_attempt_failure(token_contract, token_chain, timeframe, entered_s1, entered_s2, book_id="onchain_crypto"):
    """Called when attempt ends at S0. Only blocks if we actually acted."""
    now = datetime.now(timezone.utc)
    
    # Only record failure if we actually entered
    if not entered_s1 and not entered_s2:
        return  # We skipped - correct decision, no block
    
    # Build upsert payload - record ALL entries that happened
    payload = {
        "token_contract": token_contract,
        "token_chain": token_chain,
        "timeframe": timeframe,
        "book_id": book_id,
        "updated_at": now.isoformat(),
    }
    
    if entered_s1:
        # S1 failure blocks BOTH S1 and S2
        payload["blocked_s1"] = True
        payload["blocked_s2"] = True
        payload["last_s1_failure_ts"] = now.isoformat()
    
    if entered_s2:
        # S2 failure blocks S2 and records timestamp
        # (if S1 also failed, S2 is already blocked above, but we still record the timestamp)
        payload["blocked_s2"] = True
        payload["last_s2_failure_ts"] = now.isoformat()
    
    sb.table("token_timeframe_blocks").upsert(payload).execute()
```

> **Note**: Two `if`s (not `elif`) so we record BOTH timestamps if we entered in both S1 and S2.

### On Episode Success
```python
def record_episode_success(token_contract, token_chain, timeframe, book_id="onchain_crypto"):
    """Called when any episode reaches S3 (success observed)."""
    now = datetime.now(timezone.utc)
    
    # Get current block state
    result = sb.table("token_timeframe_blocks").select("*").eq(
        "token_contract", token_contract
    ).eq("token_chain", token_chain).eq("timeframe", timeframe).eq("book_id", book_id).execute()
    
    if not result.data:
        return  # No blocks to clear
    
    row = result.data[0]
    updates = {"last_success_ts": now.isoformat(), "updated_at": now.isoformat()}
    
    # Unblock S1 if success is after last S1 failure
    if row.get("blocked_s1") and row.get("last_s1_failure_ts"):
        if now > datetime.fromisoformat(row["last_s1_failure_ts"].replace("Z", "+00:00")):
            updates["blocked_s1"] = False
    
    # Unblock S2 if success is after last S2 failure
    if row.get("blocked_s2") and row.get("last_s2_failure_ts"):
        if now > datetime.fromisoformat(row["last_s2_failure_ts"].replace("Z", "+00:00")):
            updates["blocked_s2"] = False
    
    sb.table("token_timeframe_blocks").update(updates).eq(
        "token_contract", token_contract
    ).eq("token_chain", token_chain).eq("timeframe", timeframe).eq("book_id", book_id).execute()
```

### Gating Check (Single Point — Before S1/S2 Entry)
```python
def is_entry_blocked(token_contract, token_chain, timeframe, entry_state, book_id="onchain_crypto") -> bool:
    """Check if entry is blocked. Called ONCE before allowing S1/S2 entry."""
    result = sb.table("token_timeframe_blocks").select("blocked_s1, blocked_s2").eq(
        "token_contract", token_contract
    ).eq("token_chain", token_chain).eq("timeframe", timeframe).eq("book_id", book_id).execute()
    
    if not result.data:
        return False  # No blocks exist
    
    row = result.data[0]
    
    if entry_state == "S1":
        return row.get("blocked_s1", False)
    elif entry_state == "S2":
        return row.get("blocked_s2", False)
    
    return False
```

### Integration Point in plan_actions_v4()
```python
# Right before S1 entry decision:
if effective_buy_signal and state == "S1":
    if is_entry_blocked(token_contract, token_chain, timeframe, "S1"):
        pm_logger.info("BLOCKED S1 entry for %s: token blocked until success observed", token_ticker)
        return []
    # ... rest of S1 logic

# Right before S2 entry decision:
if buy_flag and state == "S2":
    if is_entry_blocked(token_contract, token_chain, timeframe, "S2"):
        pm_logger.info("BLOCKED S2 entry for %s: token blocked until success observed", token_ticker)
        # Skip to DX if pool available, or return []
    # ... rest of S2 logic
```

---

# PART 4: Tuning System (LEARNED — Separate from Blocking)

> **CRITICAL**: Tuning is learned. Blocking (Part 3) is NOT learned. 
> These are **two completely separate systems**.

## 4.1 What Gets Tuned (vs What Gets Blocked)

| System | Scope | Mechanism | Purpose |
|--------|-------|-----------|---------|
| **Blocking** | `token + chain + timeframe` | Deterministic, immediate | Risk control per-token |
| **Tuning** | `chain + bucket + timeframe` | Mined, generalized | Learn optimal mechanics |

Blocking is about "this specific token failed, don't touch it."
Tuning is about "in this environment, how strict should our gates be?"

## 4.2 What We Tune

### S1 Tuning (Existing)
- `ts_min` — Trend strength threshold
- `halo_mult` — ATR halo for entry zone

### S2 Tuning (New Episodes)

> S2 tuning tunes the **opportunity window geometry**, not a new threshold.
> halo + TS + slope guards define how often buy_flag opportunities occur and whether we accept them.

S2 already has tunable knobs:
- `s2_halo_mult` — ATR halo for S2 zone
- `ts_min` — Can reuse or split from S1
- `ema250_slope_min` — Slope guard
- `ema333_slope_min` — Slope guard

**S2 Episode Lifecycle:**
- **Start**: First `S1 → S2` within the attempt (`s2_started = True`)
- **End**: Attempt ends (`S3` or `S0`)
- **Flip-flops** (`S2 ↔ S1`) do NOT end the episode

**S2 Episode Outcomes:**
- **Success** = Attempt ends at S3 (always implies S2 started)
- **Failure** = Attempt ends at S0 **and** `s2_started == True`

### S3 DX Tuning (Split into Two — Critical)

> **These are orthogonal.** Decision tuning handles "should we DX?". Ladder tuning handles "how spaced?".
> **Ladder tuning does NOT run on failures** — weak trends are handled by decision tuning.

**A) DX Decision Tuning** — Should we take DX at all?
- **Question**: "In this environment, should we use DX recovery at all?"
- Tunes: `dx_min`, slope guards, etc.
- Uses 4-quadrant logic: acted/skipped × success/fail
- **This handles weak trends**: if DX fails often → tighten `dx_min` (reduce DX)

**B) DX Ladder Spacing Tuning** — Given DX was correct, were arms placed well?
- **Question**: "Given that DX was the right call, were the arms at good levels?"
- Tunes: `dx_atr_mult` (base = 6.0, range [2.0, 12.0])
- **ONLY runs on SUCCESSFUL recoveries** — no action on failures
- Does NOT infer trend quality (that's decision tuning's job)

**S3 DX Outcomes (for decision tuning):**
- **Success** = Trim happens after recovery started
- **Failure** = Emergency exit before any trim-after-recovery

### Ladder Update Logic (SUCCESS only)

> Ladder tuning does nothing on failures. Weak trends are handled by decision tuning.

| k (dx_count) | On SUCCESS | Interpretation | Adjustment |
|--------------|------------|----------------|------------|
| 0 (opportunity existed) | YES | Arms too deep — bounce was shallow | **Pull arms higher** (↓ `dx_atr_mult`) |
| 1 | YES | Arms slightly deep | **Slight ↑** (pull arms higher) |
| 2 | YES | Arms about right | **Neutral / slight ↑** |
| 3 (frequently) | YES | Arms may be too tight / over-concentrated | **Push arms lower** (↑ `dx_atr_mult`) |

Phrasing rule:
- **Decrease `dx_atr_mult`** = smaller spacing = arms **closer together and higher up**
- **Increase `dx_atr_mult`** = larger spacing = arms **further apart and lower**

## 4.3 Scope for Tuning

Tuning uses **coarse scope** (generalized learning):
```python
tuning_scope = {
    "chain": "solana",
    "bucket": "nano",
    "timeframe": "1h",
    # Optional: "venue": "..."
}
```

**NOT token-specific.** Tuning learns mechanics per environment, not per token.

## 4.4 Episode Events for Tuning

Use existing `pattern_episode_events` table with new episode types:

```python
# S2 episode event
{
    "episode_type": "s2_entry",
    "pattern_key": "pm.uptrend.S2.buy_flag",
    "action_category": "entry",
    "scope": tuning_scope,
    "outcome": "success" | "failure" | "missed" | "correct_skip",
    "acted": True | False,
    "s2_opportunity_existed": True | False,
    # ... timing, levers considered, etc.
}

# S3 DX episode event
{
    "episode_type": "s3_dx",
    "pattern_key": "pm.uptrend.S3.dx",
    "action_category": "add",
    "scope": tuning_scope,
    "outcome": "success" | "failure" | "missed" | "correct_skip",
    "acted": True | False,
    "dx_count": 0-3,
    "dx_atr_mult_used": 6.0,
    "dx_opportunity_existed": True | False,
    "trim_after_recovery": True | False,
    "emergency_after_recovery": True | False,
    # ... etc.
}
```

## 4.5 Opportunity Flags (Critical for Skipped Outcomes)

For "skipped" to be meaningful, we must track when opportunities existed:

**S2 Opportunity:**
```python
s2_opportunity_existed = (
    state == "S2" and
    buy_flag == True and
    pool_available and
    not recovery_started
)
# Note: No s2_used check needed - if S2 was used, pool is cleared so pool_available == False
```

**DX Opportunity:**
```python
dx_opportunity_existed = (
    state == "S3" and
    in_dx_zone and  # EMA144 < price < EMA333
    buy_flag == True and
    pool_available and
    dx_count < 3
)
```

Track these **during the episode** (accumulate if opportunity appears at any point).

## 4.6 Materializer Output

Same pipeline as existing tuning:
`pattern_episode_events` → miner → `learning_lessons` → materializer → `pm_overrides`

New override channels:
- `tuning_s2_halo_mult`
- `tuning_s2_ts_min`
- `tuning_dx_atr_mult`

**Runtime Application:**
```python
tuned = apply_pattern_execution_overrides(
    pattern_key="pm.uptrend.S3.dx",
    action_category="tuning",
    scope=scope,
    plan_controls={"dx_atr_mult": 6.0, "dx_min": 60.0},
    sb_client=sb_client,
)

dx_atr_mult = tuned.get("dx_atr_mult", 6.0)
dx_atr_mult = max(2.0, min(12.0, dx_atr_mult))  # Clamp to [2, 12]
```

## 4.7 Miner Frequency

Same as existing: **every 6 hours** (or whatever your current lesson_builder cadence is).

Consistent rhythm across all tuning channels.

---

# PART 5: Implementation Order (Roadmap)

## Phase 1: Bug Fix + Trim Pool + Gating (Most Impact on Risk)
1. [ ] Fix S2/S3 buy history recording
2. [ ] Add trim pool data model with correct lifecycle
3. [ ] Implement S2 dip gating (pool required)
4. [ ] Implement DX ladder gating (6×ATR, max 3)
5. [ ] Fix crowding ratio calculation

## Phase 2: Sizing Changes
1. [ ] S1 sizing → 90/60/30
2. [ ] Trim sizing → 60/30/15
3. [ ] Trim cap → 90%
4. [ ] Trim multiplier → 1.5×

## Phase 3: EMA333 Reclaim Fix
1. [ ] Track exit_value_usd on emergency exit
2. [ ] Reclaim rebuy based on exit value
3. [ ] One-time gate (rebuy_used)

## Phase 4: A/E v2 Calculator
1. [ ] Create ae_calculator_v2.py
2. [ ] Update overrides.py to return strength_mult explicitly
3. [ ] Integrate into PM Core Tick (two-stage: flags then strength)
4. [ ] Add logging throughout

## Phase 5: Cleanup
1. [ ] Remove first_dip_buy_flag
2. [ ] Remove old regime_ae_calculator.py
3. [ ] Slim down levers.py

## Phase 6: Episode Token-Gating (Blocking — Part 3)
> **BLOCKING IS NOT LEARNED** — Deterministic, immediate, per-token

1. [ ] Create `token_timeframe_blocks` table
2. [ ] Implement `record_entry_failure()` function
3. [ ] Implement `record_episode_success()` function
4. [ ] Implement `is_entry_blocked()` check
5. [ ] Add gating check to S1/S2 entry paths in `plan_actions_v4()`
6. [ ] Hook episode end detection to call failure/success recorders

## Phase 7: Tuning System (Learned — Part 4)
> **TUNING IS LEARNED** — Mined, generalized, coarse scope

1. [ ] Add S2 episode events to `pattern_episode_events`
2. [ ] Add S3 DX episode events with `dx_count` and `dx_atr_mult_used`
3. [ ] Add opportunity flags (`s2_opportunity_existed`, `dx_opportunity_existed`)
4. [ ] Update miner to compute S2 + DX outcomes
5. [ ] Add `tuning_s2_halo_mult`, `tuning_s2_ts_min`, `tuning_dx_atr_mult` to materializer
6. [ ] Update `apply_pattern_execution_overrides()` to include new channels
7. [ ] Add clamping for `dx_atr_mult` (2.0 to 12.0)

---

# Appendix: Quick Reference

## Trim Pool State Machine

```
[No Pool] 
    │
    ▼ (trim happens)
[Pool Accumulating] ◄──── (more trims accumulate)
    │
    ├───▶ S2 dip buy ───▶ [Pool Cleared] (locked profit)
    │
    └───▶ DX buy #1 ───▶ [Recovery Started]
                              │
                              ├───▶ DX buy #2
                              │         │
                              │         └───▶ DX buy #3 ───▶ [Pool Cleared]
                              │
                              └───▶ New trim ───▶ [Fresh Pool] (old pool gone)
```

## New Sizing Tables

### S1 Entry (% of remaining allocation)
| A Score | Size |
|---------|------|
| ≥ 0.7 | 90% |
| ≥ 0.3 | 60% |
| < 0.3 | 30% |

### S2/DX from Trim Pool
| A Score | S2 (one-time) | DX (per buy) |
|---------|---------------|--------------|
| ≥ 0.7 | 60% of initial | 20% of initial |
| ≥ 0.3 | 30% of initial | 10% of initial |
| < 0.3 | 10% of initial | 3.33% of initial |

### Trim (% of position)
| E Score | Size |
|---------|------|
| ≥ 0.7 | 60% |
| ≥ 0.3 | 30% |
| < 0.3 | 15% |

### Reclaim Rebuy (% of exit value)
| A Score | Size |
|---------|------|
| ≥ 0.7 | 60% |
| ≥ 0.3 | 30% |
| < 0.3 | 10% |

## Trim Multiplier Formula (Extraction-Based)

```python
extraction_ratio = total_extracted_usd / total_allocation_usd

if extraction_ratio >= 3.0:
    trim_multiplier = 0.1   # Big winner
elif extraction_ratio >= 1.0:
    trim_multiplier = 0.3   # House money
elif extraction_ratio >= 0.5:
    trim_multiplier = 1.0   # Moderate
else:
    trim_multiplier = 1.5   # Full risk
```

| Extraction | Multiplier | Meaning |
|------------|------------|---------|
| 0% | **1.5** | Full risk → trim aggressively |
| 50%+ | **1.0** | Half extracted → moderate |
| 100%+ | **0.3** | House money → ride trend |
| 300%+ | **0.1** | Big winner → very selective |

---

## Critical Distinction: Blocking vs Tuning

| Aspect | **Blocking** (Part 3) | **Tuning** (Part 4) |
|--------|----------------------|---------------------|
| **Purpose** | Risk control | Learn optimal mechanics |
| **Scope** | `token + chain + timeframe` | `chain + bucket + timeframe` |
| **Mechanism** | Deterministic, immediate | Mined, generalized |
| **Learned?** | **NO** — runtime safety latch | **YES** — lesson pipeline |
| **Update trigger** | Episode end (failure/success) | Miner runs (every 6h) |
| **What it controls** | Can we enter at all? | How strict are gates? |
| **Channels** | `blocked_s1`, `blocked_s2` | `tuning_ts_min`, `tuning_halo_mult`, `tuning_dx_atr_mult`, etc. |

**In docs/comments, always say:**
- "Blocks are NOT learned."
- "Blocks are runtime risk controls."
- "Only tuning is learned."

---

## S2/S3 Existing Levers (No Fabrication Needed)

### S2 Levers (tune the opportunity window)
- `s2_halo_mult` — ATR halo for S2 zone
- `ts_min` — Trend strength threshold (can reuse or split)
- `ema250_slope_min` — Slope guard
- `ema333_slope_min` — Slope guard

### S3 DX Levers (two dimensions)
**Decision** (should we take DX?):
- `dx_min` — DX score threshold
- slope guards

**Ladder** (how far apart?):
- `dx_atr_mult` — Base 6.0, tunable range [2.0, 12.0]

---

## Failure Definitions (Authoritative, Aligned with Episode Ordering)

> An "attempt" starts at `S0 → S1` and ends at terminal `S3` (success) or terminal `S0` (failure).
> Flip-flops (`S1 ↔ S2`) do NOT end the attempt.

| Episode | Lifecycle | Success | Failure |
|---------|-----------|---------|---------|
| **S1** | `S0 → S1` to terminal | Attempt ends at S3 | Attempt ends at S0 |
| **S2** | First `S1 → S2` to terminal | Attempt ends at S3 | Attempt ends at S0 AND `s2_started == True` |
| **S3 DX (decision)** | Recovery period | Trim after recovery | Emergency before trim |
| **S3 DX (ladder)** | Recovery period | (only tuned on success) | (no tuning on failure) |

**Key asymmetries:**
- Blocking requires **acting** — skipping a failure is a correct decision
- Success can be **observed** — unblocks even if we didn't participate
- S2 episode spans flip-flops — it only ends at terminal S3 or S0

---

## The Whole System (High-Level Summary)

### What Each Layer Does

| Layer | Job | Question It Answers |
|-------|-----|---------------------|
| **Attempt lifecycle** | Define success vs failure | "Did this trend attempt work?" |
| **Scaling logic** | Manage exposure and profit | "How much to enter/exit?" |
| **Trim pool** | Bound recovery risk | "How much can we redeploy?" |
| **Blocking** | Prevent repeated donation | "Should we try this token at all?" |
| **Decision tuning** | Decide *whether* to act | "How strict should gates be?" |
| **Spacing tuning** | Optimize *how* to act | "How should the ladder be spaced?" |

### Start-to-Finish Token Lifecycle

1. **Attempt begins**: `S0 → S1` — system considers entry
2. **S1/S2 entry**: Take position if gates pass and not blocked
3. **Flip-flops**: Normal oscillations, don't end anything
4. **S3 reached**: Trim into strength, create pool for recovery
5. **Pullback in S3**: Use pool for S2 dip buy or DX ladder
6. **Attempt ends**:
   - **S3 terminal** → success, unblock, emit positive learning signal
   - **S0 terminal** → if acted, block + emit negative signal; if skipped, emit correct_skip

### One Sentence Summary

> The system enters strong when trends form, takes real profits into a pool, uses that pool for structured recovery, blocks tokens that fail after we act, and gradually tunes mechanics per environment.

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| v1 | 2025-12-28 | Initial implementation plan |
| v2 | 2025-12-28 | Fixed mismatches (crowding ratio, trim pool lifecycle, reclaim sizing, strength plumbing) |
| v3 | 2025-12-29 | Authoritative episode ordering, blocking vs tuning separation, DX tuning split, simplified pool model |
| v3.1 | 2025-12-29 | Extraction-based E dampening (0%→1.5×, 50%→1.0×, 100%→0.3×, 300%→0.1×). Enables trend-riding once de-risked. |
| v3.2 | 2025-12-29 | Final cleanup: removed stale `s2_used` from opportunity flags, fixed `record_attempt_failure` to record both timestamps, renamed Implementation Order to PART 5, added explicit "remainder locked" sentence. |
