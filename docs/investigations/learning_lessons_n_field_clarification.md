# Learning Lessons `n` Field Clarification

## Question
Why are we seeing `n=71`, `n=57` etc. in `learning_lessons` when we thought this was only from closed trades and we didn't have 50+ closed trades?

## Answer: `n` Represents Actions (Events), Not Trades

**Key Finding**: The `n` field in `learning_lessons` represents the **number of actions (events)** in `pattern_trade_events`, **NOT the number of closed trades**.

### The Data Flow

1. **Closed Trades → `pattern_trade_events`**
   - When a trade closes, `pattern_scope_aggregator.py` processes the `position_closed` strand
   - It creates **one row per action** in `pattern_trade_events`:
     - Entry action (1 per trade)
     - Add actions (N per trade - scaling in)
     - Trim actions (M per trade - scaling out)
     - Exit action (1 per trade)

2. **`pattern_trade_events` → `learning_lessons`**
   - `lesson_builder_v5.py` mines lessons from `pattern_trade_events`
   - Groups events by `(pattern_key, action_category, scope_subset)`
   - Sets `n = len(events)` for that group

### Actual Data from Your System

From investigation on 2025-01-XX:

- **Total Closed Trades**: 19
- **Total Events in `pattern_trade_events`**: 197
- **Average Events per Trade**: 10.4
- **Events per Trade Distribution**:
  - 1 event: 7 trades (36.8%)
  - 2 events: 2 trades (10.5%)
  - 3 events: 1 trade (5.3%)
  - 5 events: 2 trades (10.5%)
  - 7 events: 1 trade (5.3%)
  - 8+ events: 6 trades (31.6%)

- **By Action Category**:
  - Add: 138 events (70.1%)
  - Trim: 22 events (11.2%)
  - Entry: 19 events (9.6%)
  - Exit: 18 events (9.1%)

- **Add Actions Specifically**:
  - Total: 138 add events
  - From: 10 trades (some trades have no add actions)
  - Average: 13.8 add actions per trade (for trades with adds)
  - Distribution:
    - 1 add: 1 trade (10.0%)
    - 2 adds: 2 trades (20.0%)
    - 3 adds: 1 trade (10.0%)
    - 5 adds: 2 trades (20.0%)
    - 6+ adds: 4 trades (40.0%)

### Why `n=71`, `n=57` Makes Sense

**Example: `n=71` for `uptrend.S3.add`**
- This means there are **71 "add" actions** with pattern `uptrend.S3.add` in `pattern_trade_events`
- These 71 actions come from multiple trades (likely 1-2 trades with many add actions)
- **NOT 71 closed trades**

**Example: `n=57` for `uptrend.S3.add` with specific scope**
- This is a **subset** of the 71 events, filtered by scope_subset
- Still represents 57 actions, not 57 trades

### Verification

We verified that the `n` values in `learning_lessons` exactly match the count of matching events in `pattern_trade_events`:

```
Lesson: uptrend.S3.add, scope={...}, n=56
  → Actual matching events: 56 ✅ MATCH

Lesson: uptrend.S2.add, scope={}, n=64
  → Actual matching events: 64 ✅ MATCH

Lesson: uptrend.S3.add, scope={...}, n=57
  → Actual matching events: 57 ✅ MATCH
```

### Why This Design Makes Sense

1. **More Granular Learning**: Learning from individual actions gives more data points than learning from trades
   - 19 trades → 197 events = 10.4x more data points
   - This provides better statistical power for learning

2. **Action-Specific Patterns**: Different actions (entry, add, trim, exit) may have different patterns
   - Entry actions might be good in one context
   - Add actions might be good in another context
   - Learning at the action level captures these nuances

3. **Scaling Behavior**: The system uses scaling (multiple adds per trade)
   - Some trades have 1-2 adds
   - Some trades have 10+ adds
   - Learning from each add action separately captures scaling behavior

### Database Schema

**`pattern_trade_events`**:
```sql
CREATE TABLE pattern_trade_events (
    id BIGSERIAL PRIMARY KEY,
    pattern_key TEXT NOT NULL,
    action_category TEXT NOT NULL,  -- 'entry', 'add', 'trim', 'exit'
    scope JSONB NOT NULL,
    rr FLOAT NOT NULL,
    trade_id UUID NOT NULL,          -- Links to parent trade
    timestamp TIMESTAMPTZ NOT NULL
);
```

**Key Point**: One row per **action**, not per trade. Multiple rows can have the same `trade_id`.

**`learning_lessons`**:
```sql
CREATE TABLE learning_lessons (
    id BIGSERIAL PRIMARY KEY,
    module TEXT NOT NULL,
    pattern_key TEXT NOT NULL,
    action_category TEXT NOT NULL,
    scope_subset JSONB NOT NULL,
    n INTEGER NOT NULL,              -- ← Count of events (actions), not trades
    stats JSONB NOT NULL,
    ...
);
```

### Code Reference

**`lesson_builder_v5.py::mine_lessons()`**:
```python
# Groups events by (pattern_key, action_category, scope_subset)
for (pk, cat), group_df in grouped:
    # ...
    stats = compute_lesson_stats(slice_events, global_baseline_rr)
    lesson = {
        "n": stats['n'],  # ← This is len(events), not len(trades)
        ...
    }
```

**`lesson_builder_v5.py::compute_lesson_stats()`**:
```python
def compute_lesson_stats(events: List[Dict[str, Any]], ...):
    rrs = [float(e['rr']) for e in events]
    n = len(rrs)  # ← Count of events, not trades
    ...
```

### Conclusion

**The `n` field in `learning_lessons` = Number of actions (events) in `pattern_trade_events`, NOT the number of closed trades.**

This is **correct behavior**:
- ✅ Each trade can have multiple actions (entry, adds, trims, exit)
- ✅ Learning from actions provides more data points than learning from trades
- ✅ Action-level learning captures scaling behavior and action-specific patterns
- ✅ With 19 closed trades, having 71 add actions is completely normal

**If you see `n=71`**, that means you have **71 actions** (likely from 1-2 trades with many add actions), not 71 closed trades.

### Related Investigation

See also: `docs/investigations/learning_lessons_n_field_investigation.md` (which discusses the tuning_rates system, but the same principle applies to pm_strength lessons).

