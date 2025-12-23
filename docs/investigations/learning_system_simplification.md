# Learning System Simplification

## Changes Made

### ✅ Improved Lesson Builder with Exponential Decay

**What Changed**:
- Enhanced `fit_decay_curve()` in `lesson_builder_v5.py` to use **exponential decay** instead of simple linear
- Added `estimate_half_life()` function that fits: `edge(t) = edge_0 * exp(-lambda * t)`
- Computes `half_life_hours = ln(2) / lambda` directly during lesson building
- Stores `half_life_hours` in `decay_meta` and writes to `learning_lessons.decay_halflife_hours`

**Benefits**:
- More accurate decay modeling (exponential vs linear)
- Half-life computed at lesson creation time (no separate job needed)
- Simpler system (one place for decay computation)

**Code Location**: `src/intelligence/lowcap_portfolio_manager/jobs/lesson_builder_v5.py`
- `estimate_half_life()` - Exponential decay fitting
- `fit_decay_curve()` - Now uses exponential decay

---

### ✅ Removed Redundant Meta-Learning Jobs

**What Was Removed**:
1. **Regime Weight Learner** - Not integrated into runtime
2. **Half-Life Estimator** - Now computed in lesson builder
3. **Latent Factor Clusterer** - Not integrated into runtime

**What Remains**:
- Pattern Scope Aggregator (every 2h)
- Lesson Builder (every 6h) - **Now with exponential decay**
- Override Materializer (every 2h)

**Code Changes**:
- `v5_learning_scheduler.py` - Removed imports and scheduling for meta-learning jobs
- Removed `v5_meta_learning_enabled` feature flag

---

## Why This Is Better

### Before (Complex)
```
Lesson Builder (linear decay)
    ↓
Half-Life Estimator (separate job, exponential decay)
    ↓
Regime Weight Learner (separate job, not used)
    ↓
Latent Factor Clusterer (separate job, not used)
```

### After (Simple)
```
Lesson Builder (exponential decay with half-life)
    ↓
Override Materializer
```

**Benefits**:
1. **Less Complexity**: One job does decay computation (not two)
2. **No Redundancy**: Removed jobs that weren't integrated
3. **Better Decay**: Exponential decay is more accurate than linear
4. **Clearer System**: Easier to understand what's happening

---

## Technical Details

### Exponential Decay Formula

**Model**: `edge(t) = edge_0 * exp(-lambda * t)`

**Fitting**:
- Take log: `ln(edge) = ln(edge_0) - lambda * t`
- Linear regression on `(t, ln(edge))` → get `lambda`
- Half-life: `half_life_hours = ln(2) / lambda`

**Implementation**:
```python
def estimate_half_life(edge_history: List[Tuple[float, datetime]]) -> Optional[float]:
    # Fit exponential decay curve
    # Return half_life_hours = ln(2) / lambda
```

**Usage in Decay Multiplier**:
- Short half-life (< 7 days) → Apply decay multiplier (0.5 to 1.0)
- Long half-life (≥ 7 days) → Stable pattern (multiplier = 1.0)

---

## What Still Works

✅ **Pattern Mining**: Lesson builder mines patterns from `pattern_trade_events`  
✅ **Decay Detection**: Exponential decay with half-life computation  
✅ **Override Creation**: Override materializer creates actionable overrides  
✅ **Regime-Specific Patterns**: Learning system learns patterns with regime in scope  

---

## What Was Removed (And Why)

### Regime Weight Learner
- **What it did**: Learned which metrics (time_efficiency, etc.) matter in different regimes
- **Why removed**: Not integrated into runtime - weights were computed but never used
- **Alternative**: Learning system already learns regime-specific patterns (regime in scope)

### Half-Life Estimator (Separate Job)
- **What it did**: Estimated half-life from edge history snapshots
- **Why removed**: Now computed directly in lesson builder during mining
- **Better**: No need for separate job or edge history table

### Latent Factor Clusterer
- **What it did**: Grouped overlapping patterns to prevent double-counting
- **Why removed**: Not integrated - override materializer doesn't use clustering
- **Alternative**: Each pattern creates separate override (works fine)

---

## Migration Notes

### Database Tables
- `learning_regime_weights` - Still exists but not populated (can be dropped if desired)
- `learning_edge_history` - Still exists but not needed (half-life computed from events)
- `learning_latent_factors` - Still exists but not populated (can be dropped if desired)

### Code Files
- `regime_weight_learner.py` - Still exists but not scheduled
- `half_life_estimator.py` - Still exists but not scheduled (estimate_half_life moved to lesson_builder)
- `latent_factor_clusterer.py` - Still exists but not scheduled

**Recommendation**: Can delete these files if you want, or keep them for reference.

---

## Summary

**Simplified from**: 6 jobs (3 core + 3 meta-learning)  
**To**: 3 jobs (pattern aggregator, lesson builder, override materializer)

**Improved**: Lesson builder now uses exponential decay with half-life computation  
**Removed**: Redundant meta-learning jobs that weren't integrated

**Result**: Simpler, clearer system that does the same job better.

