# Learning System Investigation: Braiding vs Pattern Scope Aggregator

## Executive Summary

**Finding: There are TWO parallel learning systems writing to the same `learning_lessons` table, but only ONE is actually used by the runtime override system.**

- **Braiding System** (old): Writes incompatible lesson format → **IGNORED by override system**
- **Pattern Scope Aggregator + Lesson Builder v5** (new): Writes compatible lesson format → **USED by override system**

## Data Flow Comparison

### System 1: Braiding System (OLD - NOT USED)

**Flow:**
```
position_closed strand 
  → braiding_system.process_position_closed_for_braiding()
    → Updates learning_braids table
    → build_lessons_from_braids()
      → Writes to learning_lessons table
```

**Called from:**
- `universal_learning_system.py` (line 551) - called on every position_closed strand

**Lesson Structure Written:**
```python
{
    'module': 'pm',
    'trigger': braid['dimensions'],  # Just dimensions dict
    'effect': {
        'size_multiplier': mult  # Simple multiplier
    },
    'stats': {...},
    'status': 'active' | 'candidate'
    # MISSING: pattern_key, action_category, scope_values, lesson_type, lesson_strength, decay_halflife_hours, latent_factor_id
}
```

**Problem:** Override materializer requires `pattern_key` and `action_category` (line 191-192). Braiding lessons are **skipped** because they don't have these fields.

---

### System 2: Pattern Scope Aggregator + Lesson Builder v5 (NEW - USED)

**Flow:**
```
position_closed strand
  → pattern_scope_aggregator.process_position_closed_strand()
    → Aggregates into pattern_scope_stats table
    → (scheduled job) lesson_builder_v5.build_lessons_from_pattern_scope_stats()
      → Writes to learning_lessons table
    → (scheduled job) override_materializer.run_override_materializer()
      → Reads learning_lessons
      → Writes to learning_configs table
        → Runtime overrides.py reads from learning_configs
```

**Called from:**
- `v5_learning_scheduler.py` - scheduled jobs (every 2-6 hours)
- **NOT called from `universal_learning_system.py`** - only scheduled jobs

**Lesson Structure Written:**
```python
{
    'module': 'pm',
    'pattern_key': pattern_key,  # REQUIRED
    'action_category': action_category,  # REQUIRED
    'scope_values': scope_values,  # REQUIRED
    'scope_dims': scope_dims,
    'trigger': scope_values,  # For backward compatibility
    'effect': {
        'capital_levers': {...},  # REQUIRED structure
        'execution_levers': {...}  # REQUIRED structure
    },
    'lesson_type': 'pm_strength' | 'pm_tuning' | 'dm_alloc',
    'lesson_strength': 0.0-1.0,
    'decay_halflife_hours': int | None,
    'latent_factor_id': str | None,
    'stats': {...},
    'status': 'active' | 'candidate'
}
```

**This format is COMPATIBLE with override_materializer.**

---

## Override Materializer Requirements

From `override_materializer.py` line 191-192:
```python
if not pattern_key or not action_category:
    continue  # SKIPS lessons without these fields
```

**Braiding lessons are skipped because they lack:**
- `pattern_key` ❌
- `action_category` ❌
- `effect.capital_levers` / `effect.execution_levers` structure ❌

---

## Tables Used

| Table | Written By | Read By | Purpose |
|-------|-----------|---------|---------|
| `learning_braids` | braiding_system | braiding_system | Pattern discovery (old) |
| `pattern_scope_stats` | pattern_scope_aggregator | lesson_builder_v5 | Pattern aggregation (new) |
| `learning_lessons` | **BOTH** systems | override_materializer | Lesson storage (shared) |
| `learning_configs` | override_materializer | overrides.py (runtime) | Runtime override config |

---

## Impact Analysis

### What Braiding System Does:
1. ✅ Processes `position_closed` strands
2. ✅ Updates `learning_braids` table (pattern discovery)
3. ✅ Writes to `learning_lessons` table
4. ❌ **Lessons are IGNORED by override system** (incompatible format)
5. ❌ **No effect on runtime behavior**

### What Pattern Scope Aggregator Does:
1. ✅ Processes `position_closed` strands
2. ✅ Updates `pattern_scope_stats` table (pattern aggregation)
3. ✅ Writes to `learning_lessons` table (compatible format)
4. ✅ **Lessons are USED by override system**
5. ✅ **Affects runtime behavior**

---

## Recommendation

**The braiding system appears to be legacy code that should be removed or updated.**

### Option 1: Remove Braiding System (Recommended)
- Braiding lessons are never used (incompatible format)
- Pattern scope aggregator provides the same functionality with better structure
- Reduces confusion and maintenance burden

### Option 2: Update Braiding System to v5 Format
- Convert braiding lessons to include `pattern_key`, `action_category`, `scope_values`
- Restructure `effect` to use `capital_levers` / `execution_levers`
- Add `lesson_type`, `lesson_strength`, etc.
- **But:** This duplicates functionality already in pattern_scope_aggregator

### Option 3: Keep Both (Not Recommended)
- Creates confusion
- Wastes compute resources
- Risk of conflicts in `learning_lessons` table

---

## Key Differences

### Timing:
- **Braiding**: Called **immediately** on every `position_closed` strand (real-time)
- **Pattern Scope Aggregator**: Called **scheduled** (every 2 hours)

### Pattern Discovery:
- **Braiding**: Uses `generate_pattern_keys()` with k=3 combinations, writes to `learning_braids`
- **Pattern Scope Aggregator**: Uses `generate_canonical_pattern_key()` + scope subsets, writes to `pattern_scope_stats`

Both generate pattern_key + scope, but:
- Braiding uses old pattern key format (dimensions dict as trigger)
- Pattern scope uses v5 format (canonical pattern_key + action_category + scope_values)

## Questions to Answer Before Removal

1. **Is `learning_braids` table used anywhere else?**
   - ✅ Checked: LLM research layer reads `learning_lessons` (v5 format only)
   - ⏳ Need to check: Other systems that might query `learning_braids` directly

2. **Are there any active braiding lessons in production?**
   - Query: `SELECT * FROM learning_lessons WHERE pattern_key IS NULL OR action_category IS NULL`
   - These would be braiding lessons (incompatible format)

3. **Does braiding system provide unique pattern discovery?**
   - Both use similar pattern generation logic
   - Braiding: `generate_pattern_keys(context, k=3)` - creates combinations
   - Pattern Scope: `generate_canonical_pattern_key()` + scope subsets
   - **Likely duplicate functionality**

4. **Is there a migration path?**
   - Could convert braiding lessons to v5 format, but:
     - Need to extract `pattern_key` from `trigger` dimensions
     - Need to infer `action_category` from context
     - Need to restructure `effect` to capital/execution levers
   - **But:** Pattern scope aggregator already does this better

---

## Next Steps

1. ✅ **Investigation complete** - Confirmed two systems exist
2. ⏳ **Check database** - Query for braiding lessons and braids
3. ⏳ **Check dependencies** - Verify nothing else uses braiding
4. ⏳ **Decision** - Remove or update braiding system
5. ⏳ **Implementation** - Execute chosen option

