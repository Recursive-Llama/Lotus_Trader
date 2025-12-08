# run_trade.py Design Plan

## 1. Core Philosophy
- **Reliability First**: The script must correctly initialize and schedule all components.
- **Observability**: Terminal output should be a clean, real-time "pulse" of the system via `ad_strands`, using the **Lotus Glyphic System** for semantic clarity.
- **Debuggability**: Detailed, segregated logs for when things go wrong.

## 2. Initialization Sequence
The script will initialize components in this exact order (verified against `run_social_trading.py`):

1.  **SupabaseManager**: Database connection.
2.  **OpenRouterClient**: LLM interface.
3.  **Trading Core**:
    - `JupiterClient` & `WalletManager`
    - `TraderLowcapSimpleV2` (initialized with `lotus_buyback` config support)
4.  **Intelligence Layer**:
    - `UniversalLearningSystem` (initialized FIRST)
    - `SocialIngestModule` (attached to Learning System)
    - `DecisionMakerLowcapSimple` (attached to Learning System)
    - Learning System wired with Trader and Decision Maker.
5.  **Monitoring**:
    - `ScheduledPriceCollector` (requires Wallet Manager attached to Supabase Manager)
    - `PositionMonitor`
    - `PMExecutor` (if `ACTIONS_ENABLED=1`)

## 3. Scheduling Architecture

### Seed Phase (One-shot at startup)
Must run in this specific dependency order:
1.  `dom_main` (Dominance)
2.  `feat_main` (Features/Phase - depends on Dominance)
3.  `bands_main` (Portfolio Bands - depends on Phase)
4.  `pm_core_main` (PM Core - depends on Bands & Phase)

### Recurring Schedule
**High Frequency (1m):**
- `ta_tracker_1m`, `convert_1m_ohlc`, `majors_1m_rollup`, `uptrend_engine_1m`, `pm_core_1m`

**Medium Frequency (5m):**
- `feat_main` (Tracker), `pattern_scope_aggregator`

**Standard Frequency (15m):**
- `ta_tracker_15m`, `rollup_15m`, `uptrend_engine_15m`, `pm_core_15m`

**Hourly Jobs:**
- :02 `nav_main`
- :03 `dom_main`
- :04 `rollup_1h`
- :05 `bands_main`
- :06 `ta_tracker_1h`, `pm_core_1h`
- :07 `geometry_build` (all timeframes), `update_bars_count`
- :08 `lesson_builder` (PM)
- :09 `lesson_builder` (DM)
- :10 `override_materializer`

**Low Frequency (4h):**
- `ta_tracker_4h`, `rollup_4h`, `uptrend_engine_4h`, `pm_core_4h`

## 4. Terminal Output Strategy (Glyphic System)

### Startup Status
A concise checklist indicating successful initialization:
```
⚘⟁⌖ Lotus Trencher System Initializing...
   [⋻] Supabase Manager... OK
   [∴] LLM Client... OK
   [🜄] Trader (Li.Fi/Jup)... OK
   [𓂀] Universal Learning System... Active
   [⟡] Social Ingest... Listening
   [∆φ] Decision Maker... Ready
   [⚡] PM Executor... Registered
   [↻] Schedulers... Started
...
```

### Real-time Pulse (Strands)
The console will effectively become a `tail -f` of the `ad_strands` table, using Supabase Realtime.

**Formatters:**

*   **Social Signal (`social_lowcap`)**:
    `⟡  SOCIAL   | {curator} → {symbol} ({chain}) | Conf: {confidence}`

*   **Decision (`decision_lowcap`)**:
    `∆φ DECISION | {action} {symbol} | Alloc: {allocation_pct}% | 𓂀`
    *(Note: 𓂀 appended if learning intelligence is present)*

*   **PM Action (`pm_action`)**:
    `🜄  PM EXEC  | {decision_type} {symbol} ({timeframe}) | A:{a_value} E:{e_value}`

*   **Position Closed (`position_closed`)**:
    `𐄷  CLOSED   | {symbol} | PnL: ${pnl_usd} (R:{rr})`

*   **Stage Transition (`uptrend_stage_transition`)**:
    `𒀭  STAGE    | {symbol} {from_glyph} → {to_glyph} ({timeframe})`
    *Mapping:* S0=🜁, S1=🜂, S2=🜃, S3=🜇

*   **Episode Summary (`uptrend_episode_summary`)**:
    `ᛟ  EPISODE  | {symbol} {episode_type} → {outcome} | Entered: {entered}`

*   **Fallback**:
    `⚪ STRAND   | {kind} | {symbol} | (Raw JSON)`

## 5. Logging Strategy
We will move away from a single massive log file.
- **`logs/social.log`**: Social Ingest details.
- **`logs/decision.log`**: Decision Maker logic.
- **`logs/pm.log`**: Portfolio Manager tick details.
- **`logs/trader.log`**: Execution details (Li.Fi/Jupiter).
- **`logs/system.log`**: Startup, scheduler errors, system-wide issues.

## 6. Implementation Steps
1.  Update `run_trade.py` to use the **Lotus Glyphic System**.
2.  Implement `TradingSystem` class to encapsulate initialization.
3.  Implement `StrandMonitor` class for Supabase Realtime with new formatters.
4.  Port all scheduling logic from `run_social_trading.py` (preserving strict timings).
5.  Test run.
