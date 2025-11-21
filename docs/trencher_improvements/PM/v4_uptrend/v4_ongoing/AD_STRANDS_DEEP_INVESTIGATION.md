# ad_strands Deep Investigation

**Date**: 2025-11-15  
**Status**: Investigation In Progress - No Changes  
**Purpose**: Understand actual data flow, storage behavior, and query patterns

---

## Critical Questions to Answer

1. **What happens when you insert fields that aren't columns?**
   - Does Supabase reject the insert?
   - Does it silently ignore extra fields?
   - Does it store them somewhere (metadata JSONB)?

2. **How does data actually flow?**
   - PM creates strand dict → inserts to DB → passes dict to learning system
   - Learning system reads from dict, NOT database
   - But tests query database - what do they actually get back?

3. **What's the actual structure of stored vs passed data?**
   - `position_closed` strands: `position_id` in `content` JSONB
   - `pm_action` strands: `position_id` as top-level (not a column!)
   - Learning system reads: `strand.get('entry_context')` - from dict, not DB

---

## Data Flow Analysis

### position_closed Strand Flow

**Step 1: PM Creates Strand Dict** (`pm_core_tick.py:909-926`):
```python
position_closed_strand = {
    "id": "...",
    "module": "pm",
    "kind": "position_closed",
    "symbol": token_ticker,
    "timeframe": timeframe,
    "content": {  # ✅ In content JSONB
        "position_id": position_id,
        "entry_context": {...},
        "completed_trades": [...]
    },
    "tags": [...],
    "target_agent": "learning_system"
}
```

**Step 2: PM Inserts to Database** (`pm_core_tick.py:928`):
```python
self.sb.table("ad_strands").insert(position_closed_strand).execute()
```
- ✅ This should work - all fields are valid columns or JSONB

**Step 3: PM Passes Dict to Learning System** (`pm_core_tick.py:940`):
```python
asyncio.run(self.learning_system.process_strand_event(position_closed_strand))
```
- ✅ Learning system gets the dict directly, not from DB

**Step 4: Learning System Reads from Dict** (`universal_learning_system.py:538-540`):
```python
entry_context = strand.get('entry_context', {})  # ❌ WRONG - it's in content!
completed_trades = strand.get('completed_trades', [])  # ❌ WRONG - it's in content!
timeframe = strand.get('timeframe', '1h')  # ✅ Correct - top level
```

**WAIT - THIS IS A BUG!** The learning system is reading `entry_context` and `completed_trades` from the top level, but PM puts them in `content` JSONB!

**Step 5: Braiding System Reads from Dict** (`braiding_system.py:260-262`):
```python
entry_context = strand.get('entry_context', {})  # ❌ WRONG - it's in content!
completed_trades = strand.get('completed_trades', [])  # ❌ WRONG - it's in content!
```

**THIS IS ALSO A BUG!** Both learning system and braiding system are reading from wrong location!

---

### pm_action Strand Flow

**Step 1: PM Creates Strand Dict** (`pm_core_tick.py:1017-1031`):
```python
strand = {
    "kind": "pm_action",
    "token": token,  # ❌ Not a column!
    "position_id": position_id,  # ❌ Not a column!
    "timeframe": timeframe,  # ✅ Valid column
    "chain": chain,  # ❌ Not a column!
    "ts": now.isoformat(),
    "decision_type": ...,
    "size_frac": ...,
    ...
}
```

**Step 2: PM Inserts to Database** (`pm_core_tick.py:1049`):
```python
self.sb.table("ad_strands").insert(rows).execute()
```

**Question**: What happens here? Does Supabase:
- A) Reject with error: "column 'position_id' does not exist"
- B) Silently ignore `position_id`, `chain`, `token` fields
- C) Store them in `metadata` JSONB (if it exists)
- D) Something else?

**We need to test this or check logs to see what actually happens.**

---

## Key Findings So Far

### Finding 1: Learning System Reads Wrong Location

**PM Code** (puts data in `content`):
```python
"content": {
    "entry_context": entry_context,
    "completed_trades": completed_trades,
    ...
}
```

**Learning System Code** (reads from top level):
```python
entry_context = strand.get('entry_context', {})  # ❌ Should be strand.get('content', {}).get('entry_context')
completed_trades = strand.get('completed_trades', [])  # ❌ Should be strand.get('content', {}).get('completed_trades')
```

**This means learning system is getting empty dicts!** The data is in `content` but code reads from top level.

### Finding 2: pm_action Strands Missing Required Fields

**Current**:
```python
{
    "kind": "pm_action",
    "token": token,  # Not a column
    "position_id": position_id,  # Not a column
    ...
}
```

**Missing**:
- `id` - Required primary key!
- `module` - Should be "pm"
- `symbol` - Should be token ticker
- `tags` - Required field
- `target_agent` - Should be "learning_system"

**This will either fail or create incomplete records.**

### Finding 3: Test Query Issue

**Test Code** (`test_scenario_1b_v4_learning_verification.py:88`):
```python
.eq("position_id", position_id)  # ❌ position_id is not a column
```

**But**: If `position_id` is in `content` JSONB, query should be:
```python
.eq("content->>'position_id'", position_id)  # ✅ Correct JSONB query
```

**OR**: If we use `lifecycle_id = position_id`, query could be:
```python
.eq("lifecycle_id", position_id)  # ✅ If we set lifecycle_id
```

---

## What We Need to Verify

1. **Does `pm_action` insert actually work?**
   - Check if there are any errors in logs
   - Check if `pm_action` strands exist in database
   - Check what fields they actually have when queried

2. **What does learning system actually receive?**
   - When PM passes `position_closed_strand` dict, does it have `entry_context` at top level or in `content`?
   - If it's in `content`, why does learning system code read from top level?

3. **What gets stored vs what gets passed?**
   - PM creates dict → inserts to DB → passes same dict to learning system
   - But if DB rejects/ignores some fields, the dict still has them
   - So learning system might work even if DB insert is broken

---

## Next Steps for Investigation

1. **Check actual database records**:
   - Query `ad_strands` for `kind='pm_action'` and see what fields exist
   - Query `ad_strands` for `kind='position_closed'` and see structure

2. **Check logs for insert errors**:
   - Look for any Supabase errors about unknown columns
   - Check if `pm_action` inserts are failing silently

3. **Trace actual data**:
   - Add logging to see what learning system actually receives
   - Verify if `entry_context` is at top level or in `content` when passed

4. **Understand Supabase behavior**:
   - Test: What happens when you insert a field that's not a column?
   - Does it error, ignore, or store somewhere?

---

## Hypothesis

**My current hypothesis**:
1. Supabase **silently ignores** fields that aren't columns (doesn't error, just drops them)
2. `pm_action` strands are being inserted but `position_id`, `chain`, `token` are being dropped
3. Learning system works because it reads from the **dict that was passed**, not from database
4. But tests fail because they query the **database**, which doesn't have `position_id` as a column
5. Learning system code has a bug - it reads `entry_context` from top level, but PM puts it in `content`

**But I need to verify this before making recommendations.**

