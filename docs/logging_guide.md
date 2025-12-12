# Logging Guide

**Purpose**: Complete reference for all log files in the Lotus Trader system, their locations, what they contain, and how to use them for debugging.

---

## Log File Locations

All log files are stored in the `logs/` directory at the project root. Logs are automatically rotated when they exceed 10MB, with 3 backup files kept (e.g., `rollup.log`, `rollup.log.1`, `rollup.log.2`, `rollup.log.3`).

**Full path**: `/Users/bruce/Documents/Lotus_Trader⚘⟁/logs/` (or `./logs/` from project root)

---

## How to Access Logs

### Method 1: Command Line (Recommended)

From the project root directory:

```bash
# View the last 50 lines of a log file
tail -n 50 logs/rollup.log

# Follow a log file in real-time (updates as new entries are written)
tail -f logs/rollup.log

# View entire log file (use with caution for large files)
cat logs/rollup.log

# Open log file in your default text editor
open logs/rollup.log  # macOS
# or
code logs/rollup.log  # VS Code
```

### Method 2: File System

Navigate to the `logs/` directory in your file explorer or IDE:
- **Path**: `logs/` (relative to project root)
- Open any `.log` file in your text editor
- Note: Logs are plain text files, readable by any text editor

### Method 3: IDE/Editor

If using VS Code, Cursor, or similar:
1. Open the `logs/` folder in your file explorer sidebar
2. Click on any `.log` file to view it
3. Use search (Cmd+F / Ctrl+F) to find specific entries

### Method 4: Terminal Search

Search across logs without opening files:

```bash
# Search for a term in a specific log
grep "search_term" logs/rollup.log

# Search across all logs
grep "search_term" logs/*.log

# Search with case-insensitive matching
grep -i "error" logs/system.log
```

**Note**: For real-time monitoring, use `tail -f logs/rollup.log` in a separate terminal window to watch logs as they're written.

---

## Log Files Overview

### 1. `logs/system.log`
**Purpose**: General system-level events, errors, and warnings.

**Contains**:
- System startup/shutdown events
- Component initialization errors
- Fatal errors that crash the system
- Hyperliquid WebSocket status warnings
- Social media monitoring startup messages
- Price collector startup messages
- Strand monitor status

**When to check**:
- System crashes or unexpected shutdowns
- Component initialization failures
- General system health monitoring

**Example entries**:
```
2025-12-10 12:55:43,973 - system - INFO - Social media monitoring started (quiet mode)
2025-12-10 12:55:43,974 - system - INFO - Price collector started
2025-12-10 12:51:59,415 - system - WARNING - Hyperliquid WS: No Hyperliquid data found - WS may not be running
```

---

### 2. `logs/schedulers.log`
**Purpose**: Tracks all scheduled job executions and their completion status.

**Contains**:
- Job start/completion timestamps
- Job names (e.g., "Rollup 15m", "TA→Uptrend→PM 1m", "Regime 1m")
- Job execution duration (implicit via timestamps)
- Pattern aggregator runs
- Tracker runs

**When to check**:
- Verify jobs are running on schedule
- Identify missing or delayed job executions
- Debug scheduling issues

**Example entries**:
```
2025-12-10 16:30:09,357 - schedulers - INFO - Starting Rollup 15m
2025-12-10 16:30:20,007 - schedulers - INFO - Rollup 15m completed
2025-12-10 16:30:09,357 - schedulers - INFO - Starting TA→Uptrend→PM 15m
2025-12-10 16:30:31,312 - schedulers - INFO - TA→Uptrend→PM 15m completed
```

---

### 3. `logs/rollup.log`
**Purpose**: Detailed logging for OHLC data rollup operations (1m, 5m, 15m, 1h, 4h, 1d).

**Contains**:
- Rollup boundary checks (whether we're at a timeframe boundary)
- Bar existence checks (whether a bar already exists)
- Data availability warnings (no 1m data found, insufficient bars)
- Successful rollup operations (bars written)
- Storage errors
- Boundary timestamp calculations

**When to check**:
- 15m/1h/4h data not updating (stale OHLC data)
- Missing bars for specific timeframes
- Rollup job completing but not writing data
- Data pipeline issues

**Example entries**:
```
2025-12-10 16:30:09,357 - rollup - INFO - Rolling up lowcaps data to 15m at 2025-12-10T16:30:00+00:00 (boundary: 2025-12-10T16:30:00+00:00)
2025-12-10 16:30:09,450 - rollup - WARNING - Not enough 1m bars for lowcaps 15m rollup at 2025-12-10T16:30:00+00:00: have 5, need 15
2025-12-10 16:30:20,007 - rollup - INFO - Rolled up 42 lowcaps 15m bars at 2025-12-10T16:30:00+00:00
```

**Key log levels**:
- `INFO`: Normal operations, successful rollups
- `WARNING`: Missing data, insufficient bars, bars already exist
- `ERROR`: Database errors, storage failures

---

### 4. `logs/uptrend_engine.log`
**Purpose**: Uptrend Engine V4 state machine processing for all positions.

**Contains**:
- Position processing (contract, chain, timeframe)
- State transitions (S0, S1, S2, S3, S4)
- S3 processing details (bars_since_s3, s3_start_ts, current_ts)
- First-dip buy checks and triggers
- Score calculations (TS, OX, DX, EDX)
- Emergency exit flags
- Skipped positions (missing TA data, invalid prices)
- Exceptions during position processing

**When to check**:
- Positions stuck in S3 (bars_since_s3 not advancing)
- First-dip buys not triggering
- State transitions not happening
- Engine crashes or exceptions

**Example entries**:
```
2025-12-10 16:30:31,123 - uptrend_engine - INFO - Processing WHISTLE (6Hb2xgEhyN9iVVH3cgSxYjfN774ExzgiCftwiWdjpump/solana) timeframe=15m
2025-12-10 16:30:31,145 - uptrend_engine - INFO - S3 processing: bars_since_s3=0, s3_start_ts=2025-12-10T13:00:00+00:00, current_ts=2025-12-10T13:00:00+00:00
2025-12-10 16:30:31,167 - uptrend_engine - WARNING - Skipping position: no TA data for 6Hb2xgEhyN9iVVH3cgSxYjfN774ExzgiCftwiWdjpump/solana (1m)
```

---

### 5. `logs/pm_core.log`
**Purpose**: Portfolio Manager Core tick execution and decision-making.

**Contains**:
- PM Core tick start/completion (per timeframe)
- First-dip buy detection and blocking reasons
- Action planning (buy/sell/trim decisions)
- Emergency exit handling
- Entry size calculations
- `usd_alloc_remaining` calculations
- Execution history checks

**When to check**:
- First-dip buys detected but not executing
- Actions not being generated
- PM Core crashes
- Allocation calculations

**Example entries**:
```
2025-12-10 16:30:31,234 - pm_core - INFO - PM Core Tick (15m) starting
2025-12-10 16:30:31,456 - pm_core - INFO - PM DETECTED first_dip_buy_flag=True for WHISTLE (15m)
2025-12-10 16:30:31,467 - pm_core - INFO - PM BLOCKED first_dip_buy for WHISTLE (15m): can_buy=False (last_buy=2025-12-10T13:15:00+00:00, state_transitioned=False)
2025-12-10 16:30:31,789 - pm_core - INFO - PM Core Tick (15m) completed
```

---

### 6. `logs/price_collector.log`
**Purpose**: Price data collection from external sources.

**Contains**:
- Price collection start/completion
- Data source connections
- Collection errors
- Price point ingestion

**When to check**:
- Price data not updating
- Data source connection issues
- Ingestion failures

**Note**: This log may be empty if price collection uses a different logging mechanism or if logs have been rotated.

---

### 7. `logs/trading_prices.log`
**Purpose**: Trading price-related events.

**Contains**:
- Price updates for trading decisions
- Price validation
- Price-related errors

**Note**: This log may be empty if price logging uses a different mechanism or if logs have been rotated.

---

### 8. `logs/trading_executions.log`
**Purpose**: Trading execution events (buy/sell orders).

**Contains**:
- Order submissions
- Execution confirmations
- Execution failures
- Order status updates

**When to check**:
- Orders not executing
- Execution failures
- Order status issues

---

### 9. `logs/trading_decisions.log`
**Purpose**: Trading decision events (before execution).

**Contains**:
- Decision generation
- Decision validation
- Decision blocking reasons

**When to check**:
- Decisions not being made
- Decision logic issues

---

### 10. `logs/trading_positions.log`
**Purpose**: Position management events.

**Contains**:
- Position updates
- Position state changes
- Position validation

**When to check**:
- Position state issues
- Position updates not happening

---

### 11. `logs/trading_errors.log`
**Purpose**: Trading-specific errors.

**Contains**:
- Trading execution errors
- Trading decision errors
- Trading validation errors

**When to check**:
- Trading failures
- Trading system errors

---

### 12. `logs/social_ingest.log`
**Purpose**: Social media ingestion (Twitter/Telegram).

**Contains**:
- Social media monitoring events
- Ingested posts/tweets
- Social media connection status
- Ingestion errors

**When to check**:
- Social media data not updating
- Ingestion failures
- Connection issues

---

### 13. `logs/decision_maker.log`
**Purpose**: Decision-making module events.

**Contains**:
- Decision generation
- Decision logic execution
- Decision validation

**When to check**:
- Decision-making issues
- Decision logic problems

---

### 14. `logs/learning_system.log`
**Purpose**: Learning system events (pattern recognition, lesson building).

**Contains**:
- Pattern recognition events
- Lesson building
- Learning system updates
- Pattern matching

**When to check**:
- Learning system issues
- Pattern recognition problems
- Lesson building failures

---

### 15. `logs/trader.log`
**Purpose**: Trading execution module events.

**Contains**:
- Trade execution
- Order management
- Trading API interactions

**When to check**:
- Trading execution issues
- Order management problems
- API interaction failures

---

## Common Debugging Scenarios

### Scenario 1: 15m OHLC Data Not Updating

**Symptoms**: Positions stuck with stale 15m data, `bars_since_s3=0` in uptrend_engine.log

**Steps**:
1. Check `logs/rollup.log` for 15m rollup entries:
   ```bash
   grep "15m" logs/rollup.log | tail -n 50
   ```
2. Look for warnings like:
   - "Not at 15m boundary" → Job running at wrong time
   - "bar already exists" → Bar was already written (check timestamp)
   - "Not enough 1m bars" → Missing source data
   - "No 1m data found" → Source data pipeline broken
3. Check `logs/schedulers.log` to verify "Rollup 15m" is running:
   ```bash
   grep "Rollup 15m" logs/schedulers.log | tail -n 20
   ```
4. Verify 1m data exists in database for the affected tokens

---

### Scenario 2: First-Dip Buys Not Executing

**Symptoms**: Uptrend engine shows `first_dip_buy_flag=True` but no buy executes

**Steps**:
1. Check `logs/uptrend_engine.log` for first-dip detection:
   ```bash
   grep "first_dip_buy" logs/uptrend_engine.log | tail -n 20
   ```
2. Check `logs/pm_core.log` for PM detection and blocking:
   ```bash
   grep "first_dip_buy" logs/pm_core.log | tail -n 20
   ```
3. Look for blocking reasons:
   - "can_buy=False" → Check `last_buy`, `state_transitioned`, `last_trim_ts`
   - "entry_size=0" → Check allocation calculations
   - "no action returned" → PM logic issue

---

### Scenario 3: System Crashes or Errors

**Symptoms**: System stops running, components fail

**Steps**:
1. Check `logs/system.log` for fatal errors:
   ```bash
   grep -i "error\|exception\|fatal\|critical" logs/system.log | tail -n 50
   ```
2. Check `logs/schedulers.log` for missing job completions
3. Check component-specific logs (e.g., `logs/pm_core.log`, `logs/uptrend_engine.log`) for exceptions

---

### Scenario 4: Positions Stuck in S3

**Symptoms**: `bars_since_s3` not advancing, `current_ts` not updating

**Steps**:
1. Check `logs/uptrend_engine.log` for the position:
   ```bash
   grep "WHISTLE.*15m" logs/uptrend_engine.log | tail -n 20
   ```
2. Verify `current_ts` is advancing (should match latest OHLC timestamp)
3. If `current_ts` is stuck, check `logs/rollup.log` to see if OHLC data is updating
4. Check if TA tracker is running for that timeframe

---

## Log Rotation

Logs automatically rotate when they exceed 10MB:
- Original: `rollup.log`
- Backups: `rollup.log.1`, `rollup.log.2`, `rollup.log.3`

To view rotated logs:
```bash
# View most recent backup
cat logs/rollup.log.1

# Search across all log files (including backups)
grep "pattern" logs/rollup.log*
```

---

## Useful Commands

### View Recent Log Entries
```bash
# Last 50 lines of a log
tail -n 50 logs/rollup.log

# Follow log in real-time
tail -f logs/rollup.log

# Last 100 lines with timestamps
tail -n 100 logs/uptrend_engine.log | grep "2025-12-10"
```

### Search Logs
```bash
# Search for a specific contract
grep "6Hb2xgEhyN9iVVH3cgSxYjfN774ExzgiCftwiWdjpump" logs/uptrend_engine.log

# Search for errors
grep -i "error\|exception" logs/system.log

# Search across multiple logs
grep "15m" logs/rollup.log logs/uptrend_engine.log logs/pm_core.log
```

### Count Log Entries
```bash
# Count occurrences
grep "Rollup 15m completed" logs/schedulers.log | wc -l

# Count errors
grep -i "error" logs/system.log | wc -l
```

### Filter by Time
```bash
# Entries from today
grep "2025-12-10" logs/rollup.log

# Entries from last hour (adjust timestamp)
grep "2025-12-10 16:" logs/rollup.log
```

---

## Log Levels

All logs use standard Python logging levels:

- **DEBUG**: Detailed diagnostic information (usually disabled in production)
- **INFO**: General informational messages (normal operations)
- **WARNING**: Warning messages (potential issues, but system continues)
- **ERROR**: Error messages (operations failed, but system continues)
- **CRITICAL**: Critical errors (system may be unable to continue)

Most production logs are set to **INFO** level. To enable DEBUG logging, modify the logger configuration in `src/run_trade.py`.

---

## Adding New Loggers

To add a new logger:

1. Add to `loggers` dictionary in `src/run_trade.py`:
   ```python
   loggers = {
       # ... existing loggers ...
       'new_module': 'logs/new_module.log',
   }
   ```

2. Use in your code:
   ```python
   import logging
   logger = logging.getLogger('new_module')
   logger.info("Your log message")
   ```

3. The logger will automatically be configured with:
   - File handler to `logs/new_module.log`
   - INFO level
   - 10MB rotation with 3 backups
   - Standard formatter: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

---

## Notes

- All timestamps are in UTC
- Logs are written asynchronously (may have slight delays)
- Empty log files may indicate the component hasn't run yet or logs have been rotated
- Some components may use different logging mechanisms (check source code)

