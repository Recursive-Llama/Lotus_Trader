# run_trade.py Requirements Specification

**Purpose**: Authoritative reference for building `src/run_trade.py` correctly.

**Sources**:
- `docs/implementation/legacy/trencher_improvements/PM/v4_uptrend/v4_ongoing/v4_Learning/final_stages/PM_Learning_Flow_Test_Plan.md` (authoritative)
- Test harnesses (`tests/flow/*`) (working examples)
- `src/run_social_trading.py` (outdated structure reference)
- `src/run_trade.py` (current skeleton)

---

## 1. Component Initialization (Order Matters)

### 1.0 Environment Setup
```python
# MUST be first, before any imports that use environment variables
from dotenv import load_dotenv
load_dotenv()
```

### 1.1 Core Infrastructure
```python
1. SupabaseManager() 
   - Must be first (everything depends on it)
   
2. OpenRouterClient() 
   - LLM client for social ingest and learning
   
3. JupiterClient() + WalletManager()
   - Trading infrastructure
   - Wire: wallet_manager.trader = trader (after trader init)
   - Wire: supabase_manager.wallet_manager = wallet_manager
```

### 1.2 Intelligence Layer
```python
4. UniversalLearningSystem(
     supabase_manager=...,
     llm_client=...,
     llm_config=None
   )
   - Core learning orchestrator
   
5. SocialIngestModule(
     supabase_manager=...,
     llm_client=...,
     config_path="src/config/twitter_curators.yaml"
   )
   - Wire: social_ingest.learning_system = learning_system
   
6. DecisionMakerLowcapSimple(
     supabase_manager=...,
     config=...,
     learning_system=...
   )
   - Wire: learning_system.set_decision_maker(decision_maker)
   
7. TraderLowcapSimpleV2(
     supabase_manager=...,
     config=trader_config  # includes lotus_buyback if present
   )
   - Wire: learning_system.trader = trader
   - Wire: wallet_manager.trader = trader
```

### 1.3 Monitoring & Execution
```python
8. ScheduledPriceCollector(
     supabase_manager=...,
     price_oracle=trader.price_oracle
   )
   - Price data collection
   
9. PositionMonitor(
     supabase_manager=...,
     trader=trader
   )
   - Position monitoring and exit execution
   
10. PM Executor Registration (conditional)
    if os.getenv("ACTIONS_ENABLED", "0") == "1":
        from intelligence.lowcap_portfolio_manager.pm.executor import register_pm_executor
        sb_client = supabase_manager.db_manager.client if hasattr(...) else supabase_manager.client
        register_pm_executor(trader, sb_client)  # NOTE: trader FIRST, then sb_client
```

### 1.4 Real-time Monitoring
```python
11. StrandMonitor(supabase_manager)
    - Supabase Realtime subscription to ad_strands
    - Call: strand_monitor.start() (synchronous, sets up subscription)
```

---

## 2. Async Task Startup (Must Run Concurrently)

### 2.1 Social Media Monitoring
```python
# CORRECT PATTERN (from run_social_trading.py):
from intelligence.social_ingest.run_social_monitor import SocialMediaMonitor

social_monitor = SocialMediaMonitor()
social_monitor.social_ingest.learning_system = learning_system
await social_monitor.start_monitoring()  # This is an async method that runs forever

# WRONG (current run_trade.py):
# self.social_ingest.run()  # This method doesn't exist!
```

**IMPORTANT: Output Suppression (Architecture)**
- **Design Principle**: Terminal = Strand feed + minimal status. All detailed messages go to log files.
- `SocialMediaMonitor` produces verbose per-curator loop output every 30 seconds:
  - `⟡ Checking @handle...` → **SUPPRESS** (log to `logs/social_ingest.log`)
  - `∴ Checked @handle` → **SUPPRESS** (log to `logs/social_ingest.log`)
  - `⧖ Waiting 30 seconds before next curator...` → **SUPPRESS** (log to `logs/social_ingest.log`)
- **Keep at startup**: Show curator list (all Twitter curators being monitored) - glyphs only
- **Suppress during loop**: All per-curator checking messages (every 30 seconds)
- **Solution**: Add `quiet=True` parameter to `SocialMediaMonitor`:
  - If `quiet=False` (default): Show everything (current behavior, for debugging)
  - If `quiet=True`: Show startup info (curator count + list), suppress all loop messages
- Show startup status: `[⟡] Social Ingest... Listening`
  - Then list: `   Twitter: N curators (@handle1, @handle2, ...)`
  - Then: `   Telegram: active`
- Strand monitor will show signals reactively: `⟡  SOCIAL   | {curator} → {symbol}`
- **All detailed operational messages**: Log to `logs/social_ingest.log` (see Section 11)

### 2.2 Price Collection & Position Monitoring
```python
# CORRECT:
await price_collector.start_collection(interval_minutes=1)
await position_monitor.start_monitoring(check_interval=30)

# WRONG (current run_trade.py):
# position_monitor.start()  # Wrong method name!
```

### 2.3 Learning System
```python
# From original: start_learning_system() is just a placeholder
# Learning system processes strands reactively via UniversalLearningSystem
# No explicit "start" needed, but original had it as a task placeholder
```

### 2.4 Hyperliquid WebSocket (Conditional)
```python
if os.getenv("HL_INGEST_ENABLED", "0") == "1":
    from intelligence.lowcap_portfolio_manager.ingest.hyperliquid_ws import HyperliquidWSIngester
    ing = HyperliquidWSIngester()
    asyncio.create_task(ing.run())  # Runs in background
```

---

## 3. Scheduled Jobs (PM Jobs)

### 3.1 Seed Phase (Run Once at Startup)
**CRITICAL**: Must run in this exact order before recurring jobs. Each job should have individual error handling so one failure doesn't stop the others:
```python
async def seed_pm_once():
    try:
        await asyncio.to_thread(dom_main)
    except Exception as e:
        print(f"PM seed (dominance) error: {e}")
    try:
        await asyncio.to_thread(feat_main)
    except Exception as e:
        print(f"PM seed (features/phase) error: {e}")
    try:
        await asyncio.to_thread(bands_main)
    except Exception as e:
        print(f"PM seed (bands) error: {e}")
    try:
        await asyncio.to_thread(lambda: pm_core_main(timeframe="1h", learning_system=learning_system))
    except Exception as e:
        print(f"PM seed (core) error: {e}")
```

### 3.2 Recurring Schedule

#### Every 1 Minute
- `ta_tracker_main(timeframe="1m")`
- `GenericOHLCRollup().rollup_timeframe(DataSource.LOWCAPS, Timeframe.M1)` (convert 1m price points to OHLC)
- `OneMinuteRollup().roll_minute()` (majors tick → 1m conversion)
- `uptrend_engine_main(timeframe="1m")`
- `pm_core_main(timeframe="1m", learning_system=learning_system)`

#### Every 5 Minutes (Aligned)
- `feat_main()` (Tracker) - at :00
- `GenericOHLCRollup().rollup_timeframe(..., Timeframe.M5)` - at :00
- `pattern_scope_aggregator_job()` - at :02
  ```python
  # Requires service client:
  async def pattern_scope_aggregator_job():
      sb_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
      await run_aggregator(sb_client=sb_client)
  ```

#### Every 15 Minutes (Aligned)
- `ta_tracker_main(timeframe="15m")` - at :00
- `GenericOHLCRollup().rollup_timeframe(..., Timeframe.M15)` - at :00
- `uptrend_engine_main(timeframe="15m")` - at :00
- `pm_core_main(timeframe="15m", learning_system=learning_system)` - at :00

#### Every 1 Hour (Aligned)
- `uptrend_engine_main(timeframe="1h")` - at :01
- `nav_main()` - at :02
- `dom_main()` - at :03
- `GenericOHLCRollup().rollup_timeframe(..., Timeframe.H1)` - at :04
- `bands_main()` - at :05
- `ta_tracker_main(timeframe="1h")` - at :06
- `pm_core_main(timeframe="1h", learning_system=learning_system)` - at :06
- `geom_daily_main(timeframe="1m")` - at :07
- `geom_daily_main(timeframe="15m")` - at :07
- `geom_daily_main(timeframe="1h")` - at :07
- `geom_daily_main(timeframe="4h")` - at :07
- `update_bars_count_main()` - at :07
- `build_lessons_from_pattern_scope_stats(sb_client, module='pm')` - at :08
- `build_lessons_from_pattern_scope_stats(sb_client, module='dm')` - at :09
- `run_override_materializer(sb_client=sb_client)` - at :10

#### Every 4 Hours (Aligned)
- `ta_tracker_main(timeframe="4h")` - at :00
- `GenericOHLCRollup().rollup_timeframe(..., Timeframe.H4)` - at :00
- `uptrend_engine_main(timeframe="4h")` - at :00
- `pm_core_main(timeframe="4h", learning_system=learning_system)` - at :00

### 3.3 Learning Jobs (Require Service Client)
These jobs need `SUPABASE_SERVICE_ROLE_KEY`:
```python
def _create_service_client():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    return create_client(supabase_url, supabase_key)

# Used by:
# - pattern_scope_aggregator_job()
# - lesson_builder_job(module)
# - override_materializer_job()
```

---

## 4. Task Management & Shutdown

### 4.1 Task Storage & Running Flag
```python
self.tasks = []  # Store all async tasks for graceful shutdown
self.running = False  # Flag for graceful shutdown coordination
```

### 4.2 Signal Handlers
```python
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def signal_handler(signum, frame):
    print(f"\n∅ Received signal {signum}, shutting down...")
    sys.exit(0)
```

### 4.3 Graceful Shutdown
```python
async def shutdown(self):
    self.running = False
    for task in self.tasks:
        if not task.done():
            task.cancel()
    await asyncio.gather(*self.tasks, return_exceptions=True)
```

### 4.4 Error Handling
```python
# Use return_exceptions=True to prevent one task failure from killing all
await asyncio.gather(*tasks, return_exceptions=True)
```

---

## 5. Critical Issues in Current run_trade.py

### 5.1 Social Ingest (Line 457)
- ❌ `self.social_ingest.run()` - Method doesn't exist
- ✅ Use `SocialMediaMonitor` pattern (see 2.1)
- ⚠️ **GAP**: `SocialMediaMonitor` produces verbose per-curator loop output every 30 seconds
- ✅ Add `quiet=True` parameter to `SocialMediaMonitor`:
  - Keep: Startup curator list (show all curators being monitored) - glyphs only
  - Suppress: All per-curator checking messages during loop
- ✅ Show startup status with curator list, then suppress all loop messages
- ✅ Strand monitor provides reactive confirmation when signals arrive
- ✅ All operational details log to `logs/social_ingest.log` (see Section 11)

### 5.2 Price Collector (Missing)
- ❌ Never started
- ✅ Add: `await self.price_collector.start_collection(interval_minutes=1)`

### 5.3 Position Monitor (Line 460)
- ❌ `self.position_monitor.start()` - Wrong method name
- ✅ Use: `await self.position_monitor.start_monitoring(check_interval=30)`

### 5.4 PM Executor Registration (Line 273)
- ❌ `register_pm_executor(sb_client, self.trader)` - Arguments swapped
- ✅ Use: `register_pm_executor(self.trader, sb_client)`

### 5.5 Hyperliquid WS (Missing)
- ❌ Entire component missing
- ✅ Add conditional startup (see 2.4)

### 5.6 Learning System Task (Not Needed)
- ❌ Original had placeholder task, but it's not actually needed
- ✅ Learning system is event-driven, no explicit "start" required
- ✅ Remove placeholder task (was just for consistency in original)

### 5.7 Signal Handlers (Missing)
- ❌ Only KeyboardInterrupt in main block
- ✅ Add proper signal handlers (see 4.2)

### 5.8 Shutdown Method (Missing)
- ❌ No graceful shutdown
- ✅ Add shutdown() method (see 4.3)

### 5.9 Task Management (Incomplete)
- ❌ Doesn't store tasks for shutdown
- ✅ Store all tasks in self.tasks list

### 5.10 Error Handling (Incomplete)
- ❌ No return_exceptions=True in gather
- ✅ Add exception handling (see 4.4)

### 5.11 Environment Variables (Missing)
- ❌ No `load_dotenv()` call
- ✅ Add `from dotenv import load_dotenv` and `load_dotenv()` at top of file

### 5.12 Seed Phase Error Handling (Too Coarse)
- ❌ One try/except wrapping all seed jobs - one failure stops all
- ✅ Use individual try/except per job (see 3.1)

### 5.13 Pattern Aggregator Client (Wrong Client)
- ❌ Line 413: Uses `self.supabase_manager.client` directly
- ✅ Must use service client with `SUPABASE_SERVICE_ROLE_KEY` (see 3.3)

### 5.14 Running Flag (Missing)
- ❌ No `self.running` flag for shutdown coordination
- ✅ Add `self.running = False` in `__init__`, set to `True` in `run()`, check in loops

---

## 6. Scheduling Helper Functions

The original uses nested helper functions within `start_pm_jobs()`. Current `run_trade.py` has them as class methods, which is fine, but verify:

- `_schedule_at_interval()` - For 1-minute jobs
- `_schedule_aligned()` - For 5/15-minute aligned jobs
- `_schedule_hourly()` - For hourly jobs at specific offsets
- `_schedule_4h()` - For 4-hour jobs

**Verify**: All timing logic matches original exactly.

---

## 7. Configuration

### 7.1 Config Structure
```python
{
    'trading': {
        'book_nav': float(os.getenv('BOOK_NAV', '100000.0')),
        'max_exposure_pct': 20.0,
        'min_curator_score': 0.6,
        'default_allocation_pct': 4.0,
        'min_allocation_pct': 2.0,
        'max_allocation_pct': 6.0,
        'slippage_pct': 1.0
    },
    'lotus_buyback': {
        'enabled': True,
        'lotus_contract': "...",
        'buyback_pct': 0.10
    }
}
```

### 7.2 Environment Variables
**CRITICAL**: Must call `load_dotenv()` at the very top of the file (before any imports that use env vars).

Required variables:
- `ACTIONS_ENABLED` - Enable PM executor (default: "0")
- `HL_INGEST_ENABLED` - Enable Hyperliquid WS (default: "0")
- `SUPABASE_URL` - Required
- `SUPABASE_KEY` - Required (regular client)
- `SUPABASE_SERVICE_ROLE_KEY` - Required for learning jobs (aggregator, lesson builder, materializer)
- `BOOK_NAV` - Portfolio NAV

---

## 8. Terminal Output Architecture

### 8.1 Design Principle
**Terminal = Strand Feed + Minimal Status**
- Primary output: `ad_strands` via StrandMonitor (real-time business events)
- Secondary output: Startup checklist + critical errors only
- All detailed operational messages go to log files

### 8.2 Startup Checklist (Glyphs Only - No Emojis)
```
⚘⟁⌖ Lotus Trencher System Initializing...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   [⋻] Supabase Manager... OK
   [∴] LLM Client... OK
   [🜄] Trading Core (Jupiter/Wallet)... OK
   [𓂀] Universal Learning System... Active
   [⟡] Social Ingest... Listening
      Twitter: 5 curators (@0xdetweiler, @LouisCooper_, @zinceth, @Cryptotrissy, @CryptoxHunter)
      Telegram: active
   [∆φ] Decision Maker... Ready
   [🜄] Trader (V2) & Dependencies... OK
   [⩜] Scheduled Price Collector... OK
   [⩜] Position Monitor... OK
   [⚡] PM Executor... Registered (or [⋇] Disabled if ACTIONS_ENABLED=0)
   [⟖] Strand Monitor... Started
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 8.3 What Gets Suppressed (Module Prints)
- ❌ `SocialMediaMonitor`: Per-curator loop messages → Use `quiet=True`, log to `logs/social_ingest.log`
- ❌ `SocialIngestModule`: Signal creation prints → Strand monitor shows this, log to `logs/social_ingest.log`
- ❌ `UniversalLearningSystem`: Processing prints → Strand monitor shows this, log to `logs/learning_system.log`
- ✅ PM jobs: Already use `logger` → Go to `logs/pm_core.log` (correct)
- ✅ Decision Maker: Already use `logger` → Go to `logs/decision_maker.log` (correct)
- ✅ Trader: Already use `logger` → Go to `logs/trader.log` (correct)

### 8.4 What Stays Visible
- ✅ Startup checklist (one-time, glyphs only)
- ✅ Strand monitor output (real-time business events)
- ✅ Critical errors (system failures, initialization failures)
- ✅ Scheduler startup confirmation

---

## 9. Logging Strategy

### 9.1 Log File Structure
All detailed operational messages go to segregated log files:

```
logs/
├── social_ingest.log      # Twitter/Telegram monitoring details, signal extraction
├── decision_maker.log     # Decision logic, allocation calculations, rejections
├── pm_core.log            # PM Core Tick execution, position updates, actions
├── trader.log             # Trade execution, Li.Fi bridge calls, wallet operations
├── learning_system.log    # Strand processing, module triggering, learning events
├── price_collector.log    # Price collection cycles, API calls, updates
├── position_monitor.log   # Position checks, exit triggers, P&L updates
├── schedulers.log         # Job execution, timing, errors
└── system.log             # System-wide events, initialization, critical errors
```

### 9.2 Logging Levels
- **INFO**: Normal operations, successful actions, status updates
- **WARNING**: Recoverable issues, missing data, fallbacks
- **ERROR**: Failures that don't crash the system, API errors
- **CRITICAL**: System failures, initialization failures (also print to console)

### 9.3 Module Logging Guidelines

#### Social Ingest (`logs/social_ingest.log`)
- Include: Curator checks, signal extraction, token verification, strand creation
- Suppress from console: All operational messages (strand monitor shows results)
- Example: `INFO - Checking curator @0xdetweiler`, `INFO - Extracted token: BANK (Solana)`

#### Decision Maker (`logs/decision_maker.log`)
- Include: Signal evaluation, allocation calculations, rejection reasons, approval logic
- Suppress from console: All operational messages (strand monitor shows decisions)
- Example: `INFO - Evaluating signal for BANK`, `INFO - Approved: 4.0% allocation`

#### PM Core (`logs/pm_core.log`)
- Include: Position processing, action planning, execution results, state transitions
- Suppress from console: All operational messages (strand monitor shows actions)
- Example: `INFO - Processing position BANK (1h)`, `INFO - Action: ENTRY, size_frac: 0.25`

#### Trader (`logs/trader.log`)
- Include: Trade execution, bridge calls, wallet operations, transaction hashes
- Suppress from console: All operational messages (strand monitor shows position_closed)
- Example: `INFO - Executing entry for BANK`, `INFO - Bridge tx: 0xabc123...`

#### Learning System (`logs/learning_system.log`)
- Include: Strand processing, module triggering, learning events
- Suppress from console: All operational messages (strand monitor shows all strands)
- Example: `INFO - Processing strand: social_lowcap`, `INFO - Triggering Decision Maker`

#### Price Collector (`logs/price_collector.log`)
- Include: Collection cycles, API calls, price updates, wallet balance updates
- Suppress from console: All operational messages
- Example: `INFO - Collecting prices for 3 active positions`, `INFO - Updated BANK price: $0.015`

#### Position Monitor (`logs/position_monitor.log`)
- Include: Position checks, exit triggers, P&L calculations
- Suppress from console: All operational messages
- Example: `INFO - Checking position BANK`, `INFO - Exit trigger: stop_loss`

#### Schedulers (`logs/schedulers.log`)
- Include: Job execution, timing, errors, seed phase progress
- Suppress from console: All operational messages (startup confirmation only)
- Example: `INFO - Running seed job: dom_main`, `INFO - Scheduled job: nav_main at :02`

#### System (`logs/system.log`)
- Include: Initialization, component startup, critical errors, shutdown
- Console: Critical errors only (also print to console)
- Example: `INFO - Initializing SupabaseManager`, `CRITICAL - Initialization failed: ...`

### 9.4 Log Format & Rotation
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

Example:
```
2025-01-15 14:23:45,123 - social_ingest - INFO - Checking curator @0xdetweiler
2025-01-15 14:23:47,456 - social_ingest - INFO - Extracted token: BANK (Solana)
2025-01-15 14:23:48,789 - social_ingest - INFO - Created social_lowcap strand: abc123...
```

**Log Rotation** (Future Enhancement):
- Use `RotatingFileHandler` or `TimedRotatingFileHandler` to prevent log files from growing indefinitely
- Rotate daily or when file reaches 10MB
- Keep last 7 days of logs

### 9.5 Silent Failure Prevention (Critical)

**The Problem**: When code crashes before reaching logging statements, we get no logs. This is the worst debugging scenario.

**Solutions**:

#### 9.5.1 Comprehensive Exception Handling
```python
# WRONG - Silent failure if exception occurs:
def some_job():
    result = risky_operation()  # If this crashes, no log!
    logger.info(f"Result: {result}")

# CORRECT - Always log, even on crash:
def some_job():
    try:
        logger.info("Starting job")
        result = risky_operation()
        logger.info(f"Job completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Job failed: {e}", exc_info=True)  # exc_info=True = full traceback
        raise  # Re-raise if needed, but log first
```

#### 9.5.2 Scheduler-Level Protection
All scheduled jobs MUST be wrapped:
```python
async def schedule_job(func, name):
    while True:
        try:
            logger.info(f"Starting {name}")
            await asyncio.to_thread(func)
            logger.info(f"{name} completed")
        except Exception as e:
            logger.error(f"{name} failed: {e}", exc_info=True)
            # Don't crash scheduler - log and continue
        await asyncio.sleep(interval)
```

#### 9.5.3 Entry/Exit Logging Pattern
Log at function entry AND exit (so we know if function was called):
```python
def process_position(position_id):
    logger.info(f"Processing position {position_id}")  # Entry
    try:
        # ... work ...
        logger.info(f"Position {position_id} processed successfully")  # Exit
    except Exception as e:
        logger.error(f"Position {position_id} failed: {e}", exc_info=True)  # Exit (error)
        raise
```

#### 9.5.4 Heartbeat/Health Check Logs
For long-running processes, log periodic heartbeats:
```python
# In monitoring loops:
while running:
    logger.info("Monitoring cycle started")  # Heartbeat
    try:
        # ... work ...
    except Exception as e:
        logger.error(f"Cycle failed: {e}", exc_info=True)
    logger.info("Monitoring cycle completed")  # Heartbeat
    await asyncio.sleep(interval)
```

**Detection**: If heartbeats stop, we know the process died.

#### 9.5.5 Expected Event Logging
Log expected events (not just errors):
```python
# Log when job SHOULD run:
logger.info("PM Core Tick scheduled for 14:06:00")

# Log when job starts:
logger.info("PM Core Tick started")

# Log when job completes:
logger.info("PM Core Tick completed: 3 positions processed")

# If we see "scheduled" but no "started" or "completed" → job crashed
```

#### 9.5.6 Top-Level Exception Handlers
```python
# In run_trade.py main loop:
try:
    await system.run()
except Exception as e:
    logger.critical(f"System crash: {e}", exc_info=True)
    print(f"❦ FATAL: {e}")  # Also show in console
    raise
```

#### 9.5.7 Logging Infrastructure Failures
If logging itself fails, we need a fallback:
```python
def safe_log(logger, level, message):
    try:
        getattr(logger, level)(message)
    except Exception:
        # Last resort: print to stderr
        print(f"[LOGGING FAILED] {level.upper()}: {message}", file=sys.stderr)
```

### 9.6 Detection of Missing Logs

#### 9.6.1 Expected Log Patterns
Document expected log patterns per module:
- **PM Core Tick**: Should log every 1/15/60/240 minutes (depending on timeframe)
- **Price Collector**: Should log every 1 minute
- **Social Monitor**: Should log curator checks (even if quiet mode)
- **Schedulers**: Should log job start/complete for each scheduled job

#### 9.6.2 Log Monitoring Script (Future Enhancement)
Create a simple script to check for missing logs:
```python
# scripts/check_logs.py
# Checks if expected logs are present in last N minutes
# Alerts if heartbeats are missing
```

#### 9.6.3 Structured Logging (Future Enhancement)
Use structured logging (JSON) for easier pattern matching:
```python
logger.info("job_started", extra={
    "job_name": "pm_core_tick",
    "timeframe": "1h",
    "timestamp": datetime.now().isoformat()
})
```

### 9.7 Implementation Requirements
1. **Module Suppression**: All modules use `logger` instead of `print()` for operational messages
2. **Quiet Mode**: `SocialMediaMonitor` accepts `quiet=True` to suppress loop messages
3. **Strand Monitor**: Shows all business events (no need for module prints)
4. **Critical Errors**: Always visible in console + log file
5. **Startup Only**: Checklist shown once at startup (glyphs only, no emojis)
6. **Exception Handling**: All scheduled jobs wrapped in try/except with logging
7. **Entry/Exit Logging**: Critical functions log entry and exit
8. **Heartbeats**: Long-running processes log periodic heartbeats
9. **Expected Events**: Log when jobs should run, start, and complete
10. **Top-Level Handler**: Main loop has exception handler with critical logging

---

## 10. Verification Checklist

After implementation, verify:

- [ ] All components initialize in correct order
- [ ] All wire-ups are correct (learning_system, trader, wallet_manager)
- [ ] Social monitoring uses SocialMediaMonitor pattern
- [ ] Price collector starts with correct method
- [ ] Position monitor starts with correct method
- [ ] PM executor registration has correct argument order
- [ ] Hyperliquid WS starts conditionally
- [ ] Seed phase runs before recurring jobs
- [ ] All scheduled jobs match original timings
- [ ] Learning jobs use service client
- [ ] Signal handlers installed
- [ ] Shutdown method cancels all tasks
- [ ] Error handling prevents cascade failures
- [ ] Strand monitor starts correctly
- [ ] All tasks stored for shutdown
- [ ] `load_dotenv()` called at top of file
- [ ] Seed phase has individual error handling per job
- [ ] `self.running` flag initialized and used
- [ ] Pattern aggregator uses service client (not regular client)
- [ ] Twitter monitoring uses quiet mode (suppress verbose loop output)
- [ ] Curator list shown at startup (all Twitter curators listed, glyphs only)
- [ ] Per-curator checking messages suppressed during monitoring loop
- [ ] All module prints suppressed (use logger → log files)
- [ ] SocialIngestModule prints suppressed (strand monitor shows results)
- [ ] UniversalLearningSystem prints suppressed (strand monitor shows results)
- [ ] Startup checklist uses glyphs only (no emojis)
- [ ] Log files properly structured and documented (see Section 9)
- [ ] All loggers configured with correct file handlers
- [ ] Critical errors visible in both console and log files
- [ ] All scheduled jobs wrapped in try/except with logging
- [ ] Entry/exit logging for critical functions
- [ ] Heartbeat logs for long-running processes
- [ ] Expected event logging (job scheduled/started/completed)
- [ ] Top-level exception handler with critical logging
- [ ] Scheduler-level protection (jobs don't crash scheduler)

---

## 11. Testing Strategy

1. **Component Import Test**: Verify all imports work
2. **Initialization Test**: Verify all components initialize without errors
3. **Task Startup Test**: Verify all async tasks start
4. **Scheduler Test**: Verify seed jobs run, then recurring jobs start
5. **Integration Test**: Run with test harnesses to verify full flow
6. **Production Test**: Run in production with monitoring

---

## 12. Notes

- **Learning System**: Processes strands reactively, no explicit "start" needed
- **PM Executor**: Event-driven via Supabase Realtime, registered at init
- **Strand Monitor**: Synchronous subscription setup, then runs in background
- **Service Client**: Required for learning jobs (aggregator, lesson builder, materializer)
- **Seed Phase**: Critical dependency chain - must complete before recurring jobs
- **Terminal Output**: Strand feed + minimal status (all details in log files)
- **Module Prints**: Suppressed (use logger → log files, strand monitor shows results)

