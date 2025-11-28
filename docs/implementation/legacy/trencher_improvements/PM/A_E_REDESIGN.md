# A/E Score Redesign Document

## Overview

This document outlines the redesign of the A (Add Appetite) and E (Exit Assertiveness) scoring system. The system moves from discrete modes to continuous 0-1 scoring with both global portfolio-level and per-token components. A/E scores are **independent** of the Uptrend Engine state machine - they determine risk appetite, while the Uptrend Engine provides entry/exit gates.

## Current State Analysis

### What's Already Implemented

#### 1. **Base A/E Computation** (`src/intelligence/lowcap_portfolio_manager/pm/levers.py`)
- **Meso Phase Policy**: Maps market phases to base A/E values
- **Macro Adjustment**: Applies portfolio-level phase multipliers
- **Cut Pressure**: Modulates A/E based on portfolio risk state
- **TA/Intent Deltas**: Applies technical analysis and social sentiment adjustments

#### 2. **Uptrend Engine** (`src/intelligence/lowcap_portfolio_manager/jobs/uptrend_engine.py`)
- **State Machine**: S0-S5 states with sophisticated scoring
- **Support Persistence**: Multi-tier support system with boosts
- **Euphoria Detection**: Complex euphoria curve calculation
- **Emergency Exit**: Independent failsafe system
- **Event System**: Real-time state transition events

#### 3. **Integration Points**
- **PM Core Tick**: Uses `compute_levers()` for A/E calculation
- **Strand Logging**: Records A_value/E_value in decision strands
- **Position Features**: Caches uptrend engine state in `features.uptrend_engine`

### What Needs to Change

#### 1. **Remove Technical Analysis from A/E**
Technical analysis (RSI, volume, geometry) should NOT be part of A/E calculation.

#### 2. **Add Age and Market Cap Components**
New token age and market cap should affect A/E scores.

#### 3. **Continuous Scoring Implementation**
Current system still uses discrete mode mapping instead of pure continuous scoring.

#### 4. **Uptrend Engine Integration**
The PM should combine A/E scores and Uptrend Engine for entry/exit gating, not modify A/E scores.

## Proposed Architecture

### Global A/E Components (Portfolio-Level)

#### 1. **Market Phase Component** (Existing)
```python
def _compute_global_phase_component(phase_macro: str, phase_meso: str) -> Tuple[float, float]:
    """
    Base A/E from market phases (existing implementation)
    Returns: (a_base, e_base) in [0,1]
    """
    # Meso phase policy (existing)
    a_pol, e_pol = _map_meso_policy(phase_meso)
    
    # Macro adjustment (existing)
    a_mac, e_mac = _apply_macro(a_pol, e_pol, phase_macro)
    
    return a_mac, e_mac
```

#### 2. **Portfolio Risk Component** (Existing)
```python
def _compute_global_risk_component(cut_pressure: float) -> Tuple[float, float]:
    """
    Portfolio-level risk adjustments (existing implementation)
    Returns: (a_multiplier, e_multiplier)
    """
    # Cut pressure modulation (existing)
    a_cp = 1.0 - 0.33 * cut_pressure
    e_cp = 1.0 + 0.33 * cut_pressure
    
    return a_cp, e_cp
```

### Per-Token A/E Components

#### 1. **Intent Component** (Existing)
```python
def _compute_intent_component(features: Dict[str, Any]) -> Tuple[float, float]:
    """
    Intent adjustments (existing implementation)
    Returns: (a_delta, e_delta)
    """
    intent = features.get("intent_metrics", {})
    
    a_delta = 0.0
    e_delta = 0.0
    
    # Intent channels (existing logic)
    a_delta += 0.25 * float(intent.get("hi_buy", 0.0))
    e_delta -= 0.10 * float(intent.get("hi_buy", 0.0))
    
    a_delta += 0.15 * float(intent.get("med_buy", 0.0))
    e_delta -= 0.05 * float(intent.get("med_buy", 0.0))
    
    a_delta -= 0.15 * float(intent.get("profit", 0.0))
    e_delta += 0.15 * float(intent.get("profit", 0.0))
    
    a_delta -= 0.25 * float(intent.get("sell", 0.0))
    e_delta += 0.35 * float(intent.get("sell", 0.0))
    
    a_delta -= 0.30 * float(intent.get("mock", 0.0))
    e_delta += 0.50 * float(intent.get("mock", 0.0))
    
    return a_delta, e_delta
```

#### 2. **Age Component** (New)
```python
def _compute_age_component(features: Dict[str, Any]) -> Tuple[float, float]:
    """
    Token age adjustments based on launch date
    Returns: (a_boost, e_boost) as multipliers
    """
    # Calculate age from stored launch_date
    launch_date_str = features.get("launch_date")
    if not launch_date_str:
        return 1.0, 1.0  # No boost if no launch date
    
    try:
        launch_date = datetime.fromisoformat(launch_date_str.replace('Z', '+00:00'))
        age_h = (datetime.now(timezone.utc) - launch_date).total_seconds() / 3600
    except:
        return 1.0, 1.0  # No boost on error
    
    if age_h < 6:
        return 1.15, 1.15  # +15% boost for <6 hours
    elif age_h < 12:
        return 1.10, 1.10  # +10% boost for <12 hours
    elif age_h < 72:  # 3 days
        return 1.05, 1.05  # +5% boost for <3 days
    else:
        return 1.0, 1.0    # No boost for >3 days
```

#### 3. **Market Cap Component** (New)
```python
def _compute_market_cap_component(features: Dict[str, Any]) -> Tuple[float, float]:
    """
    Market cap adjustments
    Returns: (a_boost, e_boost) as multipliers
    """
    market_cap = float(features.get("market_cap", 0.0))
    
    if market_cap < 100000:  # <$100k
        return 1.15, 1.15  # +15% boost
    elif market_cap < 500000:  # <$500k
        return 1.10, 1.10  # +10% boost
    elif market_cap < 1000000:  # <$1m
        return 1.05, 1.05  # +5% boost
    else:
        return 1.0, 1.0    # No boost for >$1m
```

## Data Sources & Integration

### **Age Source**
- **Source**: DexScreener API `pairCreatedAt` field during token ingest
- **Storage**: Store as `pair_created_at` in `lowcap_positions.features.pair_created_at` (ISO8601 format)
- **Computation**: Calculate `age_h` from `pair_created_at` to current time for A/E age component

### **Market Cap Source**
- **Source**: DexScreener API `marketCap` field from `lowcap_price_data_1m.market_cap`
- **Storage**: Cache latest value in `lowcap_positions.features.market_cap`
- **Usage**: Apply market cap buckets ($100k/$500k/$1m) for A/E boosts

### **Intent Aggregation**
- **Source**: Aggregate from `AD_strands` table by token over sliding window (24h)
- **Storage**: Store computed `intent_metrics` in `lowcap_positions.features.intent_metrics`
- **Frequency Weighting**: `1 + log(mention_count)` with exponential decay for recency
- **Curator Weighting**: Multiply intent strength by `curator.final_weight`
- **Intent → A/E Mapping**:
  - `hi_buy`: +0.25 A, -0.10 E
  - `med_buy`: +0.15 A, -0.05 E  
  - `profit`: -0.15 A, +0.15 E
  - `sell`: -0.25 A, +0.35 E
  - `mock`: -0.30 A, +0.50 E (stronger than profit - mocking = "get out")

### **Cut Pressure with 9-Position Target**
- **Above 9 positions**: Exponential dampening - `A *= exp(-0.10 * (n-9))`, `E *= exp(+0.10 * (n-9))`
- **Below 9 positions**: Linear easing - `A *= min(1, 1 + 0.05 * (9-n))`, `E *= max(0, 1 - 0.05 * (9-n))`

### **Micro Phase Usage**
- **A/E Formula**: Uses Macro + Meso phases only
- **Micro Phase**: Used as decision-layer timing nudge (brief cool-down, priority bump), not in A/E calculation

## Implementation Plan

### Phase 1: Remove Technical Analysis from A/E
1. **Remove TA components** from current `compute_levers()`
2. **Keep existing intent logic** as-is
3. **Test A/E computation** without TA influence

### Phase 2: Add Age and Market Cap Components
1. **Wire DexScreener launch_date** → `features.launch_date`
2. **Implement age component** with launch_date calculation
3. **Implement market cap component** with $100k/$500k/$1m buckets
4. **Test combined age + market cap effects**

### Phase 3: Intent Aggregation System
1. **Implement AD_strands aggregation** by token over 24h window
2. **Add frequency + curator weighting** to intent scores
3. **Store intent_metrics** in position features
4. **Update intent deltas** with corrected mock severity

### Phase 4: Continuous Scoring Implementation
1. **Remove discrete mode mapping** from `_mode_from_a()`
2. **Implement pure continuous scoring** with proper clamping
3. **Update position sizing** to use continuous A/E directly
4. **Update size mapping**: Patient (10%), Normal (30%), Aggressive (60%)

### Phase 5: PM Integration & Logging
1. **Add PM → AD_strands** decision logging for every action
2. **Implement SM event triggers** for PM recompute (direct calls, no strands)
3. **Add comprehensive logging** for A/E component breakdown
4. **Test entry/exit gates** with different A/E scores

## New A/E Computation Flow

```python
def compute_levers_v2(phase_macro: str, phase_meso: str, cut_pressure: float, 
                     features: Dict[str, Any]) -> Dict[str, Any]:
    """
    New continuous A/E computation with component breakdown
    """
    # Global components
    a_phase, e_phase = _compute_global_phase_component(phase_macro, phase_meso)
    a_risk, e_risk = _compute_global_risk_component(cut_pressure)
    
    # Per-token components
    a_intent, e_intent = _compute_intent_component(features)
    a_age, e_age = _compute_age_component(features)
    a_mcap, e_mcap = _compute_market_cap_component(features)
    
    # Apply 9-position cut pressure curve
    active_positions = features.get("active_positions", 0)
    if active_positions > 9:
        # Exponential dampening above 9
        excess = active_positions - 9
        a_cp *= math.exp(-0.10 * excess)
        e_cp *= math.exp(+0.10 * excess)
    elif active_positions < 9:
        # Linear easing below 9
        deficit = 9 - active_positions
        a_cp = min(1.0, a_cp * (1 + 0.05 * deficit))
        e_cp = max(0.0, e_cp * (1 - 0.05 * deficit))
    
    # Combine components
    a_base = a_phase * a_risk * a_cp
    e_base = e_phase * e_risk * e_cp
    
    a_boost = a_age * a_mcap
    e_boost = e_age * e_mcap
    
    a_delta = a_intent
    e_delta = e_intent
    
    # Final calculation
    a_final = max(0.0, min(1.0, (a_base + a_delta) * a_boost))
    e_final = max(0.0, min(1.0, (e_base + e_delta) * e_boost))
    
    return {
        "A_value": a_final,
        "E_value": e_final,
        "components": {
            "global": {"phase": (a_phase, e_phase), "risk": (a_risk, e_risk)},
            "per_token": {"intent": (a_intent, e_intent), "age": (a_age, e_age), "mcap": (a_mcap, e_mcap)}
        },
        "diagnostics": {
            "a_base": a_base, "e_base": e_base,
            "a_boost": a_boost, "e_boost": e_boost,
            "a_delta": a_delta, "e_delta": e_delta
        }
    }
```

## Uptrend Engine Integration

The Uptrend Engine uses A/E scores for entry/exit gating:

### **Entry Gates** (from SM_UPTREND.MD)
```python
# S2 Entry thresholds based on A score
# Patient (A ≤ 0.3): Higher thresholds, safer support tier, smaller size
if a_score <= 0.3:
    if trend_integrity >= 0.86 and trend_strength >= 0.72 and current_support == "diagonal":
        enter_position(size_frac=0.10)  # Patient

# Normal (A ≤ 0.6): Medium thresholds, mid support tier, medium size  
elif a_score <= 0.6:
    if trend_integrity >= 0.70 and trend_strength >= 0.58 and current_support in ["diagonal", "EMA50"]:
        enter_position(size_frac=0.30)  # Normal

# Aggressive (A > 0.6): Lower thresholds, higher support tier, larger size
else:
    if trend_integrity >= 0.50 and trend_strength >= 0.40 and current_support in ["diagonal", "EMA50", "AVWAP"]:
        enter_position(size_frac=0.60)  # Aggressive

# S3 Entry thresholds (similar logic)
# Patient (A ≤ 0.3): Higher thresholds, smaller size
if a_score <= 0.3:
    if continuation_quality >= 0.87 and trend_integrity >= 0.83:
        enter_position(size_frac=0.10)  # Patient

# Normal (A ≤ 0.6): Medium thresholds, medium size
elif a_score <= 0.6:
    if continuation_quality >= 0.75 and trend_integrity >= 0.73:
        enter_position(size_frac=0.30)  # Normal

# Aggressive (A > 0.6): Lower thresholds, larger size
else:
    if continuation_quality >= 0.60 and trend_integrity >= 0.60:
        enter_position(size_frac=0.60)  # Aggressive

# S5 Re-entry thresholds (from SM_UPTREND.MD lines 1013-1028)
# Patient (A ≤ 0.3): Higher thresholds, smaller size
if a_score <= 0.3:
    if cooldown_integrity >= 0.69 and reentry_readiness >= 0.69 and s5_active:
        enter_position(size_frac=0.10)  # Patient

# Normal (A ≤ 0.6): Medium thresholds, medium size
elif a_score <= 0.6:
    if cooldown_integrity >= 0.65 and reentry_readiness >= 0.65 and s5_active:
        enter_position(size_frac=0.30)  # Normal

# Aggressive (A > 0.6): Lower thresholds, larger size
else:
    if cooldown_integrity >= 0.60 and reentry_readiness >= 0.60 and s5_active:
        enter_position(size_frac=0.60)  # Aggressive
```

### **Exit Gates**
```python
# S4 Exit thresholds based on E score
if e_score >= 0.72 and exhaustion_confirmed and geometry_touch:
    sell_fraction(0.60)  # Aggressive - higher E = sell more
elif e_score >= 0.58 and exhaustion_confirmed and geometry_touch:
    sell_fraction(0.40)  # Normal
elif e_score >= 0.40 and exhaustion_confirmed and geometry_touch:
    sell_fraction(0.30)  # Patient - lower E = sell less
```

### Emergency Exit (E-driven, full liquidation)
- Always exits 100% of position when triggered (structural invalidation).
- **Uptrend Engine**: Sets `emergency_exit.active` flag and provides bounce parameters
- **PM**: Makes actual exit decisions based on E-score + uptrend engine flags:
  - E ≥ 0.8: skip bounce; exit 100% immediately on the close below both EMA50 and diagonal
  - 0.5 ≤ E < 0.8: tightened bounce protocol (shorter T, smaller halo, stricter giveback, stronger reclaim needed)
  - E < 0.5: standard bounce protocol (default parameters)

### Chandelier Exit (E-adaptive)
- **Uptrend Engine**: Calculates `highest_close` from last 20 bars and provides in payload
- **PM**: Calculates chandelier logic using E-score:
  - k(E) = clamp(3.5 − 1.5×E, 2.0, 4.0) — higher E → tighter k
  - chandelier_broken = (close < highest_close - k×ATR)
  - On trigger, sell fraction by E bucket: Patient 15%, Normal 30%, Aggressive 60%

## Benefits of New Architecture

1. **Modularity**: Each component can be tested and tuned independently
2. **Transparency**: Full breakdown of A/E score components
3. **Flexibility**: Easy to add/remove/modify components
4. **Performance**: Component caching and selective computation
5. **Debugging**: Detailed logging of each component's contribution
6. **Continuous Scoring**: Smooth A/E transitions instead of discrete jumps
7. **Risk Management**: Better portfolio-level risk controls
8. **Clear Separation**: A/E calculation independent of uptrend engine state

## Migration Strategy

1. **Parallel Implementation**: Keep existing `compute_levers()` while implementing `compute_levers_v2()`
2. **A/B Testing**: Run both systems in parallel with feature flag
3. **Gradual Rollout**: Enable new system for subset of positions
4. **Performance Monitoring**: Track A/E score distributions and position sizing
5. **Full Migration**: Switch to new system once validated

## Success Metrics

1. **A/E Score Distribution**: Smooth distribution across [0,1] range
2. **Position Sizing**: More nuanced position sizing based on continuous A/E
3. **Entry/Exit Gates**: Proper gating based on A/E scores and uptrend engine states
4. **Performance**: No significant performance degradation
5. **Risk Management**: Better portfolio risk control with continuous E scores
6. **Debugging**: Easier troubleshooting with component breakdown

## Key Insights

- **A/E scores determine HOW MUCH to risk** (position sizing, entry aggressiveness)
- **Uptrend Engine determines WHEN to risk it** (entry/exit gates based on geometry + TA)
- **A/E calculation is independent** of uptrend engine state
- **Technical analysis is NOT part of A/E** - it's part of uptrend engine gating
- **Age and market cap boost both A and E** for newer/smaller tokens
- **Intent affects A/E directly** through existing social sentiment system

This redesign provides a clean separation between risk appetite (A/E) and entry/exit timing (Uptrend Engine) while maintaining the existing functionality and adding new capabilities.
