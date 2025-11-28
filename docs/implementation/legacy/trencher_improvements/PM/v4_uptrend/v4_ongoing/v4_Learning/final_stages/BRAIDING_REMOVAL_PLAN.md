# Braiding System Removal Plan

## Dependencies Found

### Active Dependencies (Need Replacement):
1. **`actions.py`** - Uses `_apply_lessons_sync()` which calls `apply_lessons_to_action_size()` from braiding_system
   - Called on lines: 619, 667, 733, 775
   - **Problem**: This applies old braiding lessons, THEN v5 overrides are applied on top (conflicting!)
   - **Solution**: Remove `_apply_lessons_sync()` calls - v5 overrides already handle this

2. **`universal_learning_system.py`** - Calls braiding functions on every position_closed strand
   - Lines 551-586: `process_position_closed_for_braiding()` and `build_lessons_from_braids()`
   - **Solution**: Replace with pattern_scope_aggregator call


---

## Removal Steps

### Step 1: Remove Old Lesson Application from actions.py

**File**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py`

**Changes**:
1. Remove import: `from .braiding_system import apply_lessons_to_action_size`
2. Remove function: `_apply_lessons_sync()`
3. Remove all calls to `_apply_lessons_sync()`:
   - Line 619: `trim_size = _apply_lessons_sync(...)` → Remove (v5 overrides handle this)
   - Line 667: `entry_size = _apply_lessons_sync(...)` → Remove
   - Line 733: `entry_size = _apply_lessons_sync(...)` → Remove
   - Line 775: `rebuy_size = _apply_lessons_sync(...)` → Remove

**Note**: `_apply_v5_overrides_to_action()` already applies size adjustments via `apply_pattern_strength_overrides()`, so old lessons are redundant and conflicting.

---

### Step 2: Replace Braiding with Pattern Scope Aggregator in universal_learning_system.py

**File**: `src/intelligence/universal_learning/universal_learning_system.py`

**Changes**:
1. Remove import: `from intelligence.lowcap_portfolio_manager.pm.braiding_system import process_position_closed_for_braiding`
2. Remove import: `from src.intelligence.lowcap_portfolio_manager.pm.braiding_system import build_lessons_from_braids`
3. Add import: `from intelligence.lowcap_portfolio_manager.jobs.pattern_scope_aggregator import process_position_closed_strand`
4. Replace lines 549-586:
   ```python
   # OLD:
   await process_position_closed_for_braiding(...)
   await build_lessons_from_braids(...)
   
   # NEW:
   await process_position_closed_strand(
       sb_client=self.supabase_manager.client,
       strand=strand
   )
   ```

**Benefits**:
- Real-time aggregation (immediate learning)
- Compatible lesson format (works with override system)
- Single source of truth

---

### Step 3: Remove/Deprecate Braiding Files

**Files to Remove** (after confirming no other dependencies):
- `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py`
- `src/intelligence/lowcap_portfolio_manager/jobs/braiding_lesson_builder.py` (if exists)

**Files to Keep** (but mark as deprecated):
- Keep for now if other systems query `learning_braids` for stats
- Can remove later once all reporting is updated

---

### Step 4: Update Pattern Scope Aggregator for Real-Time Use

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pattern_scope_aggregator.py`

**Current**: Designed for scheduled batch processing
**Needed**: Optimize for real-time incremental updates

**Changes**:
1. Ensure `process_position_closed_strand()` is efficient for single-strand processing
2. Consider adding batching/caching if performance becomes an issue
3. Keep scheduled job as backup/cleanup (runs less frequently)

**Note**: Pattern scope aggregator already uses streaming aggregation (Welford's algorithm), so it should handle real-time updates well.

---

## Real-Time vs Scheduled: Recommendation

### Current State:
- **Braiding**: Real-time (called on every position_closed)
- **Pattern Scope Aggregator**: Scheduled (every 2 hours)

### Recommendation: **Hybrid Approach**

1. **Real-time aggregation** (on position_closed):
   - Call `process_position_closed_strand()` immediately
   - Updates `pattern_scope_stats` incrementally
   - Fast learning feedback

2. **Scheduled lesson building** (every 6 hours):
   - `lesson_builder_v5` reads from `pattern_scope_stats`
   - Builds lessons when stats are mature (n >= n_min)
   - Less frequent = more stable lessons

3. **Scheduled override materialization** (every 2 hours):
   - `override_materializer` reads from `learning_lessons`
   - Writes to `learning_configs` for runtime
   - Frequent enough for responsive updates

**Benefits**:
- ✅ Fast aggregation (real-time)
- ✅ Stable lessons (scheduled, only when mature)
- ✅ Responsive overrides (scheduled, but frequent)

---

## Implementation Status

✅ **Step 1 Complete**: Removed old lesson application from `actions.py`
- Removed import: `from .braiding_system import apply_lessons_to_action_size`
- Removed function: `_apply_lessons_sync()`
- Removed all 4 calls to `_apply_lessons_sync()` (lines 589, 634, 703, 745)
- v5 overrides now handle all size adjustments

✅ **Step 2 Complete**: Replaced braiding with pattern scope aggregator in `universal_learning_system.py`
- Removed import: `from intelligence.lowcap_portfolio_manager.pm.braiding_system import process_position_closed_for_braiding`
- Removed import: `from src.intelligence.lowcap_portfolio_manager.pm.braiding_system import build_lessons_from_braids`
- Added import: `from intelligence.lowcap_portfolio_manager.jobs.pattern_scope_aggregator import process_position_closed_strand`
- Replaced braiding calls with `process_position_closed_strand()` call
- Now processes position_closed strands in real-time for pattern scope aggregation

✅ **Step 3 Complete**: Removed braiding files
- ✅ Deleted `braiding_system.py` (no longer imported)
- ✅ Deleted `braiding_lesson_builder.py` (scheduled job for old system)
- ✅ Kept `braiding_helpers.py` (still used by `actions.py` and `pm_core_tick.py` for utility functions)

---

## Database Cleanup (Optional, Later)

After confirming everything works:
1. Archive `learning_braids` table (backup, then drop)
2. Clean up old braiding lessons from `learning_lessons`:
   ```sql
   DELETE FROM learning_lessons 
   WHERE pattern_key IS NULL OR action_category IS NULL;
   ```

