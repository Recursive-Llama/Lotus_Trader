# Learning Queue Removal

**Date**: 2025-01-XX

**Status**: ✅ **Complete** - Learning queue removed, strands now processed directly

---

## Summary

The `learning_queue` table and related infrastructure have been removed. Strands are now processed directly via `learning_system.process_strand_event()` calls, matching the pattern used by Social Ingest and Decision Maker.

---

## What Was Removed

### Database Schema (`ad_strands_schema.sql`)

1. **`learning_queue` table** - Removed entirely
   - Table definition
   - Indexes (`idx_learning_queue_status`, `idx_learning_queue_created_at`)
   - DROP statement

2. **`trigger_learning_system()` function** - Updated
   - Removed: Queue insert logic (`INSERT INTO learning_queue`)
   - Kept: Resonance scores calculation (still used)

### Python Code

1. **`learning_pipeline.py`** - `process_learning_queue()` method
   - Marked as DEPRECATED
   - Returns empty results for backward compatibility
   - All queue processing logic removed

2. **`centralized_learning_system.py`** - `process_learning_queue()` method
   - Marked as DEPRECATED
   - Returns empty results for backward compatibility

---

## Why It Was Removed

1. **Not Used**: No scheduled job processed the queue
2. **Redundant**: Social Ingest and Decision Maker bypass it with direct calls
3. **Confusing**: Infrastructure existed but nothing consumed it
4. **Direct Pattern**: All modules now use direct `process_strand_event()` calls

---

## Current Pattern

**All modules now follow this pattern:**

```python
# After creating strand:
if self.learning_system:
    await self.learning_system.process_strand_event(strand)
```

**Modules using direct calls:**
- ✅ Social Ingest (`social_ingest_basic.py`)
- ✅ Decision Maker (`decision_maker_lowcap_simple.py`)
- ✅ Portfolio Manager (`pm_core_tick.py`) - **NEW**

---

## Migration Notes

### For Existing Databases

If you have an existing database with `learning_queue` table:

```sql
-- Drop the table and trigger
DROP TABLE IF EXISTS learning_queue CASCADE;
DROP TRIGGER IF EXISTS strand_learning_trigger ON ad_strands;
DROP FUNCTION IF EXISTS trigger_learning_system() CASCADE;

-- Recreate trigger without queue logic
CREATE OR REPLACE FUNCTION trigger_learning_system()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate resonance scores (will be implemented in Python)
    PERFORM calculate_module_resonance_scores(NEW.id, NEW.kind, NEW.content, NEW.module_intelligence);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER strand_learning_trigger
    AFTER INSERT ON ad_strands
    FOR EACH ROW
    EXECUTE FUNCTION trigger_learning_system();
```

### For New Databases

The updated `ad_strands_schema.sql` no longer includes `learning_queue`, so new databases will be created correctly.

---

## Backward Compatibility

The `process_learning_queue()` methods are kept but marked as DEPRECATED:
- They return empty results (`{'processed': 0, 'successful': 0, 'failed': 0}`)
- Any code calling them will continue to work but won't process anything
- This allows gradual migration if needed

---

## Testing

After removal, verify:
- ✅ Strands are still created in `ad_strands` table
- ✅ Resonance scores are still calculated (via trigger)
- ✅ Learning system processes strands via direct calls
- ✅ No errors from deprecated `process_learning_queue()` calls

---

## Related Files

- `src/database/ad_strands_schema.sql` - Schema updated
- `src/intelligence/universal_learning/pipeline/learning_pipeline.py` - Method deprecated
- `src/intelligence/universal_learning/systems/centralized_learning_system.py` - Method deprecated
- `docs/trencher_improvements/PM/v4_uptrend/PM_LEARNING_SYSTEM_GAP_ANALYSIS.md` - Gap analysis

---

**Status**: ✅ **Complete** - Learning queue removed, direct processing pattern established

