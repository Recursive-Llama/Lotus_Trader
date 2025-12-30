# Learning Lessons `n` Field Investigation

## Question
Why are we seeing `n=71`, `n=57` etc. in `learning_lessons` when we thought this was only from closed trades and we don't have 50+ closed trades?

## Answer: There Are TWO Learning Systems in `learning_lessons`

**Key Finding**: The `learning_lessons` table contains lessons from **TWO different learning systems**:

1. **Old System (`pm_strength` lessons)**: Created by `lesson_builder_v5` from `pattern_trade_events` (closed trades)
2. **New System (`tuning_rates` lessons)**: Created by `tuning_miner` from `pattern_episode_events` (episode windows)

**Your `n=71, n=57` values are from `pm_strength` lessons**, which DO come from closed trades (via `pattern_trade_events`).

---

## System 1: `pm_strength` Lessons (Old System)

### Data Source: `pattern_trade_events` (Closed Trades)

### Key Finding
The `n` field in `learning_lessons` represents the **number of episode events (windows)**, not closed trades.

### Data Flow

#### 1. Episode Windows → `pattern_episode_events`
- **Episodes** (S1, S2, S3) are opportunity periods that can have **multiple windows**
- Each **window** is a specific opportunity window (e.g., `buy_signal=True` for S1, `buy_flag=True` for S2, `price < ema144` for S3)
- When a window closes, it's logged as an event in `pattern_episode_events`
- Each event records: `decision` (acted/skipped), `outcome` (success/failure), `factors` (signal values)

#### 2. Episode Window Lifecycle

**S1 Episode Example**:
```
S0 → S1 (episode starts)
  ├─ Window 1: entry_zone_ok=True → samples captured → window closes → event logged
  ├─ Window 2: entry_zone_ok=True → samples captured → window closes → event logged
  ├─ Window 3: entry_zone_ok=True → samples captured → window closes → event logged
  └─ Episode ends (S1 → S2 or S1 → S0)
```

**S3 Episode Example**:
```
S2 → S3 (episode starts)
  ├─ Window 1: price < ema144 → samples captured → window closes → event logged
  ├─ Window 2: price < ema144 → samples captured → window closes → event logged
  ├─ Window 3: price < ema144 → samples captured → window closes → event logged
  └─ Episode ends (S3 → S0)
```

#### 3. Window Opening/Closing Logic

**S1 Windows** (`pm_core_tick.py::_process_episode_logging`):
- **Opens**: When `state == "S1"` AND `entry_zone_ok == True`
- **Closes**: When `entry_zone_ok == False` OR episode ends
- **Logged**: When window closes via `_finalize_active_window()` → `_log_episode_event()`

**S2 Windows** (Phase 7):
- **Opens**: When `state == "S2"` AND `buy_flag == True` AND `entry_zone_ok == True`
- **Closes**: When `buy_flag == False` OR episode ends
- **Logged**: Same as S1

**S3 Windows**:
- **Opens**: When `state == "S3"` AND `price < ema144` (in retest band)
- **Closes**: When `price >= ema144` OR episode ends
- **Logged**: Same as S1

#### 4. Tuning Miner Aggregation

**Location**: `tuning_miner.py::_process_slice()`

The miner:
1. Fetches all `pattern_episode_events` from last 90 days with outcomes
2. Groups by `pattern_key` and `scope_subset` (recursive Apriori-like search)
3. For each group, calculates:
   - `n = len(group)` ← **This is the count of events (windows), not trades**
   - `n_acted = len(acted_events)`
   - `n_skipped = len(skipped_events)`
   - Win Rate, Miss Rate, False Positive Rate, Dodge Rate

**Example Calculation**:
```python
# If you have 10 S1 episodes, each with 5-7 windows:
# - Episode 1: 6 windows → 6 events
# - Episode 2: 5 windows → 5 events
# - Episode 3: 7 windows → 7 events
# - ... (10 episodes total)
# Total: 60 events → n=60 in learning_lessons
```

### Why This Makes Sense

1. **Episodes ≠ Trades**: An episode is an opportunity period, not a trade. One episode can have many windows (opportunities).

2. **Windows = Decision Points**: Each window is a decision point where we could act or skip. This is what we're learning from.

3. **More Data = Better Learning**: Having 50-70 windows gives us more statistical power than 10 closed trades.

4. **Outcome Backfilling**: When an episode ends, all windows in that episode get their outcomes backfilled:
   ```python
   # In pm_core_tick.py::_update_episode_outcomes_from_meta()
   windows = episode.get("windows", [])
   db_ids = [w.get("db_id") for w in windows if w.get("db_id")]
   _update_episode_outcome(db_ids, outcome)  # Updates all window events
   ```

### Database Schema

**`pattern_episode_events`**:
```sql
CREATE TABLE pattern_episode_events (
    id BIGSERIAL PRIMARY KEY,
    scope JSONB NOT NULL,              -- {"chain": "solana", "bucket": "micro", ...}
    pattern_key TEXT NOT NULL,         -- "pm.uptrend.S1.entry"
    episode_id TEXT NOT NULL,          -- Unique episode ID (e.g., "s1_ep_...")
    trade_id TEXT,                     -- Linked trade if acted (nullable)
    decision TEXT NOT NULL,            -- 'acted' or 'skipped'
    outcome TEXT,                      -- 'success', 'failure', 'missed', 'correct_skip'
    factors JSONB NOT NULL,            -- Signal values at decision time
    timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

**`learning_lessons`**:
```sql
CREATE TABLE learning_lessons (
    id BIGSERIAL PRIMARY KEY,
    module TEXT NOT NULL,              -- 'pm'
    pattern_key TEXT NOT NULL,         -- "pm.uptrend.S1.entry"
    action_category TEXT NOT NULL,     -- 'tuning'
    scope_subset JSONB NOT NULL,       -- {"chain": "solana", "bucket": "micro"}
    n INTEGER NOT NULL,                -- ← Number of episode events (windows)
    stats JSONB NOT NULL,              -- {wr, fpr, mr, dr, n_acted, n_skipped, ...}
    lesson_type TEXT NOT NULL,         -- 'tuning_rates'
    ...
);
```

### Example: From Episodes to Lessons

**Scenario**: 10 S1 episodes, each with varying windows:

```
Episode 1 (s1_ep_abc123):
  - Window 1: entry_zone_ok → acted → outcome: success → event logged
  - Window 2: entry_zone_ok → skipped → outcome: success → event logged
  - Window 3: entry_zone_ok → skipped → outcome: success → event logged
  → 3 events

Episode 2 (s1_ep_def456):
  - Window 1: entry_zone_ok → acted → outcome: failure → event logged
  - Window 2: entry_zone_ok → skipped → outcome: failure → event logged
  → 2 events

... (8 more episodes with 4-7 windows each)

Total: 60 events in pattern_episode_events
```

**Tuning Miner Processing**:
```python
# Groups by pattern_key="pm.uptrend.S1.entry" and scope_subset={"chain": "solana"}
group = df[df['pattern_key'] == 'pm.uptrend.S1.entry']
n = len(group)  # 60 events

# Calculates stats:
n_acted = len(group[group['decision'] == 'acted'])  # e.g., 20
n_skipped = len(group[group['decision'] == 'skipped'])  # e.g., 40
wr = len(acted_success) / n_acted  # Win rate
mr = len(skipped_success) / n_skipped  # Miss rate
```

**Result in `learning_lessons`**:
```json
{
  "module": "pm",
  "pattern_key": "pm.uptrend.S1.entry",
  "action_category": "tuning",
  "scope_subset": {"chain": "solana", "bucket": "micro"},
  "n": 60,  // ← 60 windows/events, not 10 trades
  "stats": {
    "wr": 0.65,
    "fpr": 0.35,
    "mr": 0.80,
    "dr": 0.20,
    "n_acted": 20,
    "n_skipped": 40,
    "n_total": 60
  }
}
```

### Conclusion

**`n` in `learning_lessons` = Number of episode events (windows), NOT closed trades**

This is correct behavior because:
- ✅ Episodes can have many windows (opportunities)
- ✅ Each window is a decision point (acted/skipped)
- ✅ More windows = more statistical power for learning
- ✅ The miner aggregates all windows to calculate tuning rates

**If you have `n=71`**, that means you have **71 episode windows** (opportunities) in the last 90 days for that pattern_key + scope combination, not 71 closed trades.

### Verification Query

To verify this, you can query:

```sql
-- Count episode events (windows) for a specific pattern
SELECT 
    pattern_key,
    scope->>'chain' as chain,
    scope->>'bucket' as bucket,
    COUNT(*) as event_count,
    COUNT(DISTINCT episode_id) as episode_count,
    COUNT(DISTINCT trade_id) as trade_count
FROM pattern_episode_events
WHERE pattern_key = 'pm.uptrend.S1.entry'
  AND outcome IS NOT NULL
  AND timestamp >= NOW() - INTERVAL '90 days'
GROUP BY pattern_key, scope->>'chain', scope->>'bucket';

-- Compare with learning_lessons
SELECT 
    pattern_key,
    scope_subset->>'chain' as chain,
    scope_subset->>'bucket' as bucket,
    n,
    stats->>'n_total' as n_total_from_stats
FROM learning_lessons
WHERE pattern_key = 'pm.uptrend.S1.entry'
  AND lesson_type = 'tuning_rates';
```

The `event_count` should match `n` in `learning_lessons`.

