# Learning v5 Clarification - Deep Dive

## The Confusion

The comparison table showed:
- **v5 Scheduler**: Uses `run_lesson_builder` 
- **Main Scheduler**: Uses `build_lessons_from_pattern_scope_stats`

This made it seem like they were different functions. **They're actually the same!**

---

## What I Found

### 1. Function Identity

**`build_lessons_from_pattern_scope_stats`** (used by main scheduler):
```python
# In lesson_builder_v5.py:280
async def build_lessons_from_pattern_scope_stats(sb_client: Client, module: str = 'pm', **kwargs) -> int:
    """Wrapper for backward compat."""
    return await mine_lessons(sb_client, module)
```

**`run_lesson_builder`** (imported by v5 scheduler):
```python
# In v5_learning_scheduler.py:22
from .lesson_builder_v5 import run_lesson_builder
```

**Problem**: `run_lesson_builder` **doesn't exist**! The v5 scheduler has a broken import.

**Reality**: Both should be calling `mine_lessons()` - the actual v5 lesson builder.

---

### 2. Data Flow Architecture

#### v5 Architecture (Current/Correct):
```
position_closed strand
    ↓
pattern_trade_events (fact table - raw events)
    ↓
mine_lessons() (recursive Apriori mining)
    ↓
learning_lessons (mined patterns)
    ↓
override_materializer()
    ↓
pm_overrides (actionable rules)
```

#### Legacy Architecture (Old):
```
position_closed strand
    ↓
pattern_scope_stats (aggregated stats table)
    ↓
build_lessons_from_pattern_scope_stats() (legacy)
    ↓
learning_lessons
```

**Key Difference**:
- **v5**: Mines directly from raw `pattern_trade_events` (fact table)
- **Legacy**: Would read from pre-aggregated `pattern_scope_stats` table

**Current State**: The function name `build_lessons_from_pattern_scope_stats` is misleading - it actually mines from `pattern_trade_events`, not `pattern_scope_stats`.

---

### 3. Table Usage

#### `pattern_trade_events` (Fact Table - v5)
- **Purpose**: Raw fact table - one row per trade action
- **Written by**: `pattern_scope_aggregator.py` (real-time when positions close)
- **Read by**: `mine_lessons()` (v5 lesson builder)
- **Status**: ✅ **Active** - this is the v5 approach

#### `pattern_scope_stats` (Aggregated Stats - Legacy)
- **Purpose**: Pre-aggregated edge stats per (pattern_key, action_category, scope_subset)
- **Written by**: Would be written by an aggregator (if it existed)
- **Read by**: Would be read by legacy lesson builder (if it existed)
- **Status**: ❓ **Unclear** - table exists but may not be actively used

**Conclusion**: v5 uses `pattern_trade_events` directly. `pattern_scope_stats` appears to be legacy/unused.

---

## What Should We Do?

### Option A: Fix v5 Scheduler (Recommended)

**Fix the broken import**:
```python
# In v5_learning_scheduler.py:22
# Change from:
from .lesson_builder_v5 import run_lesson_builder

# To:
from .lesson_builder_v5 import mine_lessons as run_lesson_builder
# OR
from .lesson_builder_v5 import build_lessons_from_pattern_scope_stats as run_lesson_builder
```

**Then integrate v5 scheduler** into main scheduler to get:
- Proper scheduling (every 2h/6h instead of hourly)
- Meta-learning jobs (regime weights, half-life, latent factors)

### Option B: Keep Main Scheduler (Simpler)

**Keep current setup** but:
- Rename `build_lessons_from_pattern_scope_stats` to `mine_lessons` for clarity
- Add missing meta-learning jobs to main scheduler
- Adjust schedules to match v5 (every 2h/6h instead of hourly)

### Option C: Hybrid (Current State)

**Keep main scheduler** for core jobs, **add v5 scheduler** for meta-learning:
- Main scheduler: Pattern aggregator, lesson builder, override materializer
- v5 scheduler: Regime weight learner, half-life estimator, latent factor clusterer

---

## Current Status Breakdown

| Component | Status | Notes |
|-----------|--------|-------|
| `mine_lessons()` | ✅ Working | Actual v5 lesson builder |
| `build_lessons_from_pattern_scope_stats()` | ✅ Working | Wrapper that calls `mine_lessons()` |
| `run_lesson_builder()` | ❌ Missing | v5 scheduler tries to import this but it doesn't exist |
| `pattern_trade_events` | ✅ Active | Fact table used by v5 |
| `pattern_scope_stats` | ❓ Unclear | Table exists but may be unused |
| Main scheduler integration | ✅ Working | Uses correct function, wrong name |
| v5 scheduler integration | ❌ Broken | Has broken import |

---

## Recommendation

**Use v5 approach** (which is what you're already doing!):

1. **✅ FIXED: v5 scheduler import**:
   - Created `run_lesson_builder()` wrapper function that calls `build_lessons_from_pattern_scope_stats()` for both PM and DM modules
   - Wrapper handles async/sync conversion properly

2. **Integrate v5 scheduler** into main scheduler OR add missing jobs:
   - Regime weight learner (daily 01:00 UTC)
   - Half-life estimator (weekly Mon 02:00 UTC)  
   - Latent factor clusterer (weekly Mon 03:00 UTC)

3. **Optional cleanup**:
   - Rename `build_lessons_from_pattern_scope_stats` to `mine_lessons` for clarity
   - Document that `pattern_scope_stats` is legacy/unused

---

## Summary

**You're already using v5!** The confusion was:
- Function name `build_lessons_from_pattern_scope_stats` suggests it reads from `pattern_scope_stats`
- But it actually calls `mine_lessons()` which reads from `pattern_trade_events` (v5 approach)
- v5 scheduler has a broken import but would use the same function

**The main scheduler is correctly using the v5 lesson builder**, just with a misleading function name. The v5 scheduler is broken but would do the same thing if fixed.

**Action**: Fix v5 scheduler import and integrate it (or add missing meta-learning jobs to main scheduler).

