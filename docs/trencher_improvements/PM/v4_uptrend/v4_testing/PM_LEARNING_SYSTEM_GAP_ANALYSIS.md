# PM → Learning System Integration Gap Analysis

**Status**: Critical gap identified - learning loop is broken

**Date**: 2025-01-XX

---

## Executive Summary

The Portfolio Manager (PM) correctly emits `position_closed` strands when positions close, but these strands are **never processed by the learning system**. This breaks the entire learning feedback loop - no coefficient updates happen, no learning occurs.

**Root Cause**: PM inserts strands into the database, but there's no mechanism to trigger the learning system to process them.

---

## Current Flow (What Happens Now)

### Step 1: PM Detects Position Closure ✅
**Location**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py:398-541`

**What happens**:
1. PM executes full exit (`size_frac=1.0` or `emergency_exit`)
2. Executor confirms successful execution
3. PM checks `total_quantity == 0` (position fully closed)
4. PM computes R/R metrics from OHLCV data
5. PM writes `completed_trades` JSONB to `lowcap_positions` table
6. PM updates position: `status='watchlist'`, `closed_at=now()`
7. **PM emits strand** with `kind='position_closed'`:
   ```python
   position_closed_strand = {
       "kind": "position_closed",
       "position_id": position_id,
       "token": position.get("token_contract"),
       "timeframe": position.get("timeframe"),
       "chain": position.get("token_chain"),
       "ts": datetime.now(timezone.utc).isoformat(),
       "entry_context": entry_context,
       "completed_trades": completed_trades,
       "decision_type": decision_type,
   }
   self.sb.table("ad_strands").insert(position_closed_strand).execute()
   ```

**Status**: ✅ **This works correctly**

### Step 2: Database Trigger Fires ✅
**Location**: `src/database/ad_strands_schema.sql:330-333`

**What happens**:
1. Database trigger `strand_learning_trigger` fires on INSERT to `ad_strands`
2. Trigger calls `trigger_learning_system()` function
3. Function inserts into `learning_queue` table:
   ```sql
   INSERT INTO learning_queue (strand_id, strand_type, created_at)
   VALUES (NEW.id, NEW.kind, NOW());
   ```

**Status**: ✅ **This works correctly** - strands get queued

### Step 3: Learning Queue Processing ❌
**Location**: **MISSING**

**What should happen**:
1. Scheduled job or direct call processes `learning_queue` table
2. For each pending strand, fetch from `ad_strands` table
3. Call `learning_system.process_strand_event(strand)`

**Status**: ❌ **This doesn't exist** - no scheduled job, no queue processing

### Step 4: Learning System Processing ✅ (Code exists, but never called)
**Location**: `src/intelligence/universal_learning/universal_learning_system.py:289-314`

**What should happen**:
1. `process_strand_event()` receives `position_closed` strand
2. Detects `strand_kind == 'position_closed'`
3. Calls `_process_position_closed_strand(strand)`
4. Extracts `completed_trade` and `entry_context` from strand
5. Updates coefficients for all matching levers/interaction patterns
6. Updates global R/R baseline

**Status**: ✅ **Code exists and works** - but it's never called because Step 3 is missing

---

## The Gap: Missing Connection

**The Problem**:
- PM inserts strand → Database trigger queues it → **Nothing processes the queue**
- Learning system has the handler → **But it's never invoked**

**Why This Breaks Everything**:
- No coefficient updates → Decision Maker uses stale/neutral weights
- No learning occurs → System doesn't improve over time
- Feedback loop is broken → No adaptation to what works/doesn't work

---

## Comparison: How Other Modules Do It

### Social Ingest Pattern ✅
**Location**: `src/intelligence/social_ingest/social_ingest_basic.py:1158`

```python
# After creating strand:
if self.learning_system:
    asyncio.create_task(self.learning_system.process_strand_event(created_strand))
```

**Key**: Social Ingest has `learning_system` instance and calls it directly

### Decision Maker Pattern ✅
**Location**: `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py:639`

```python
# After creating decision strand:
result = await self.learning_system.process_strand_event(created_decision)
```

**Key**: Decision Maker has `learning_system` instance and calls it directly

### PM Pattern ❌
**Location**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py:534`

```python
# After creating position_closed strand:
self.sb.table("ad_strands").insert(position_closed_strand).execute()
# ... that's it - no call to learning_system
```

**Key**: PM doesn't have `learning_system` instance and doesn't call it

---

## Solution Options

### Option A: Add Scheduled Job to Process Learning Queue

**How it works**:
1. Add scheduled job in `run_social_trading.py` (every 1-5 minutes)
2. Job queries `learning_queue` for pending strands
3. For each strand, fetch from `ad_strands` table
4. Call `learning_system.process_strand_event(strand)`
5. Update queue status to 'completed' or 'failed'

**Pros**:
- Decouples PM from learning system (PM doesn't need learning_system instance)
- Uses existing database trigger + queue infrastructure
- Can handle backlog if learning system is slow

**Cons**:
- Adds latency (strands processed every 1-5 minutes, not immediately)
- More complex (requires queue processing logic)
- Requires new scheduled job
- Queue can accumulate if job fails

**Implementation**:
```python
# In run_social_trading.py:
async def process_learning_queue_job():
    """Process pending strands from learning_queue"""
    while True:
        try:
            # Get pending strands
            queue_items = (
                system.learning_system.supabase_manager.client
                .table('learning_queue')
                .select('*')
                .eq('status', 'pending')
                .limit(10)
                .execute()
            ).data
            
            for item in queue_items:
                strand_id = item['strand_id']
                
                # Fetch strand from ad_strands
                strand = (
                    system.learning_system.supabase_manager.client
                    .table('ad_strands')
                    .select('*')
                    .eq('id', strand_id)
                    .limit(1)
                    .execute()
                ).data
                
                if strand:
                    # Process strand
                    success = await system.learning_system.process_strand_event(strand[0])
                    
                    # Update queue status
                    status = 'completed' if success else 'failed'
                    system.learning_system.supabase_manager.client.table('learning_queue').update({
                        'status': status,
                        'processed_at': 'now()'
                    }).eq('id', item['id']).execute()
        
        except Exception as e:
            logger.error(f"Error processing learning queue: {e}")
        
        await asyncio.sleep(60)  # Run every minute

# Schedule it:
asyncio.create_task(process_learning_queue_job())
```

### Option B: PM Calls Learning System Directly (RECOMMENDED)

**How it works**:
1. Pass `learning_system` instance to `PMCoreTick.__init__()`
2. After inserting `position_closed` strand, call `learning_system.process_strand_event()` directly
3. Remove dependency on queue processing

**Pros**:
- **Immediate processing** - no latency
- **Simpler** - matches existing pattern (Social Ingest, Decision Maker)
- **More reliable** - no queue to get stuck
- **Less infrastructure** - no scheduled job needed

**Cons**:
- PM needs access to `learning_system` instance
- Couples PM to learning system (but this is fine - PM should know about learning)

**Implementation**:
```python
# 1. Update PMCoreTick.__init__():
class PMCoreTick:
    def __init__(self, timeframe: str = "1h", learning_system=None):
        # ... existing init code ...
        self.learning_system = learning_system  # NEW

# 2. Update pm_core_main() in run_social_trading.py:
def pm_core_main(timeframe: str = "1h"):
    """Main entry point for PM Core Tick"""
    pm = PMCoreTick(timeframe=timeframe, learning_system=system.learning_system)  # NEW
    pm.run()

# 3. Update _check_position_closure() in pm_core_tick.py:
# After inserting strand:
self.sb.table("ad_strands").insert(position_closed_strand).execute()

# Add direct call to learning system:
if self.learning_system:
    try:
        await self.learning_system.process_strand_event(position_closed_strand)
        logger.info(f"Learning system processed position_closed strand for {position_id}")
    except Exception as e:
        logger.error(f"Error processing position_closed strand in learning system: {e}")
```

**Note**: `_check_position_closure()` is called from `run()` which is synchronous. Need to handle async call:
- Option B1: Make `run()` async (requires updating all callers)
- Option B2: Use `asyncio.create_task()` (fire and forget, like Social Ingest)
- Option B3: Use `asyncio.run()` or `asyncio.get_event_loop().run_until_complete()` (blocking)

**Recommendation**: Option B2 (fire and forget) - matches Social Ingest pattern, non-blocking

---

## Recommendation: Option B (Direct Call)

**Why**:
1. **Matches existing pattern** - Social Ingest and Decision Maker both call `process_strand_event()` directly
2. **Simpler** - no queue processing logic, no scheduled job
3. **Immediate** - learning happens right away, no delay
4. **More reliable** - no queue to get stuck or accumulate

**Implementation Steps**:
1. ✅ Pass `learning_system` to `PMCoreTick.__init__()`
2. ✅ Update `pm_core_main()` in `run_social_trading.py` to pass `learning_system`
3. ✅ Update `_check_position_closure()` to call `learning_system.process_strand_event()` after inserting strand
4. ✅ Handle async call (use `asyncio.create_task()` for fire-and-forget)
5. ✅ Test: Verify learning system processes `position_closed` strands

---

## What Needs to Be Done

### Immediate (Critical)
1. **Pass `learning_system` to PM**
   - Update `PMCoreTick.__init__()` to accept `learning_system` parameter
   - Update `pm_core_main()` in `run_social_trading.py` to pass `system.learning_system`

2. **Call learning system after strand insertion**
   - Update `_check_position_closure()` to call `learning_system.process_strand_event()` after inserting strand
   - Use `asyncio.create_task()` for async call (fire-and-forget pattern)

3. **Verify learning system processes `position_closed` strands**
   - Test: Close a position, verify strand is emitted
   - Test: Verify `_process_position_closed_strand()` is called
   - Test: Verify coefficients are updated

### Future (Optional)
- Consider removing `learning_queue` table if not used elsewhere
- Consider removing database trigger if direct calls become standard pattern
- Document the pattern: "Modules that emit strands should call `learning_system.process_strand_event()` directly"

---

## Testing Plan

### Test 1: Strand Emission
- **Setup**: Create a test position, execute full exit
- **Verify**: `position_closed` strand is inserted into `ad_strands` table
- **Verify**: Strand contains `entry_context`, `completed_trades`, `timeframe`

### Test 2: Learning System Processing
- **Setup**: Create a test position, execute full exit
- **Verify**: `_process_position_closed_strand()` is called
- **Verify**: Coefficients are updated in `learning_coefficients` table
- **Verify**: Global R/R baseline is updated in `learning_configs` table

### Test 3: End-to-End Learning Loop
- **Setup**: Create position with specific levers (curator, chain, mcap_bucket, etc.)
- **Execute**: Close position with known R/R outcome
- **Verify**: Coefficients for matching levers are updated correctly
- **Verify**: Decision Maker uses updated coefficients for next allocation

---

## Related Files

- `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py` - PM Core Tick (emits strands)
- `src/intelligence/universal_learning/universal_learning_system.py` - Learning System (processes strands)
- `src/run_social_trading.py` - Main entry point (wires components)
- `src/database/ad_strands_schema.sql` - Database schema (trigger + queue)
- `docs/trencher_improvements/PM/v4_uptrend/LEARNING_SYSTEM_V4.md` - Learning System design doc

---

## Status

**Current**: ✅ **FIXED** - Learning loop is complete

**Implementation**: 
- ✅ `PMCoreTick.__init__()` now accepts `learning_system` parameter
- ✅ `pm_core_main()` now accepts `learning_system` parameter
- ✅ All PM job functions pass `self.learning_system` to `pm_core_main()`
- ✅ `_check_position_closure()` calls `learning_system.process_strand_event()` after inserting strand
- ✅ Uses `asyncio.run()` to handle async call from sync context (position closures are rare, blocking is acceptable)

**Result**: Learning system processes `position_closed` strands immediately when positions close

**Priority**: 🔴 **CRITICAL** - Without this, no learning occurs, system doesn't improve

---

## Implementation Summary

### Changes Made

1. **`PMCoreTick.__init__()`** (`pm_core_tick.py:41-58`):
   - Added `learning_system` parameter
   - Stores `self.learning_system` for use in position closure

2. **`_check_position_closure()`** (`pm_core_tick.py:540-555`):
   - After inserting `position_closed` strand, calls `learning_system.process_strand_event()`
   - Uses `asyncio.run()` to handle async call from sync context
   - Logs success/error appropriately

3. **`pm_core_main()`** (`pm_core_tick.py:824-834`):
   - Added `learning_system` parameter
   - Passes to `PMCoreTick.__init__()`

4. **PM Job Functions** (`run_social_trading.py:590-616`):
   - All 4 job functions (`pm_core_1m_job`, `pm_core_15m_job`, `pm_core_1h_job`, `pm_core_4h_job`) now pass `self.learning_system` to `pm_core_main()`

### Testing Checklist

- [ ] Test: Close a position, verify `position_closed` strand is emitted
- [ ] Test: Verify `_process_position_closed_strand()` is called
- [ ] Test: Verify coefficients are updated in `learning_coefficients` table
- [ ] Test: Verify global R/R baseline is updated in `learning_configs` table
- [ ] Test: Verify Decision Maker uses updated coefficients for next allocation


