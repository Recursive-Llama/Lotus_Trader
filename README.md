# Lotus Trader V3 ⚘⟁

*Universal trend detection and adaptive trading system that learns from outcomes across all markets*

## ⚘ **What is Lotus Trader?**

Lotus Trader is a **universal trend detection and trading system** built around a core innovation: **Uptrend Engine v4** - a state machine that detects uptrends and downtrends in any market using only OHLCV data.

**The Core Philosophy**: All markets, charts, and timeframes are more similar than they are different. The same human behavior and market dynamics that create trends in crypto tokens also create trends in stocks, perps, prediction markets, and any other market. The engine doesn't care what the asset is - it only needs OHLCV bars.

**Key Innovation**: Multiple pipelines feed into one universal engine. Each pipeline handles its own data ingestion and execution, but they all share the same trend detection core and learning system.

### **Why This Matters**

- **One engine for all markets** - Same trend detection works on crypto, stocks, perps, prediction markets
- **One learning system for all markets** - Outcomes from all pipelines feed into unified learning
- **Works with any OHLCV data** - No market-specific logic, just price bars
- **Learns from real outcomes, not predictions** - Outcome-first exploration discovers what actually worked
- **Simple architecture → scalable intelligence** - Add new pipelines without changing the core engine

---

## ⚘ **Core Architecture**

Lotus Trader V3 has four core components:

1. **A universal trend engine** - Uptrend Engine v4 detects trends in any market
2. **A regime-driven A/E system** - Market regime detection using Uptrend Engine states from multiple drivers
3. **An outcome-first learning system** - Learns from what worked, not what was predicted

Each component is described below.

### **The Universal Engine**

*Summary:* One clean state machine that works on any OHLCV data.

**Uptrend Engine v4** is the heart of the system. It's a clean state machine (S0→S1→S2→S3) that:

- **Works on any OHLCV data** - Crypto tokens, stocks, perps, prediction markets, forex - doesn't matter
- **Detects both uptrends and downtrends** - Universal trend detection, not just one direction
- **Emits signals, doesn't make decisions** - Clean separation: engine signals, Portfolio Manager decides
- **Multi-timeframe by design** - Each token/asset gets 4 independent positions (1m, 15m, 1h, 4h) from day one
- **Single source of truth** - `ta_utils.py` ensures production and backtesting use identical calculations

**Why multi-timeframe matters**: The whole point is that all markets and timeframes are more similar than different. The same EMA state transitions (S0→S1→S2→S3) work on 1-minute crypto charts and 4-hour stock charts because they're driven by the same human behavior and market dynamics.

### **The Regime Engine**

*Summary:* Market regime detection using Uptrend Engine states from multiple drivers to compute A/E scores.

**Regime Engine** replaces the old phase-based A/E calculation system. Instead of using string phases like "dip", "good", "euphoria", it uses **Uptrend Engine states** (S0/S1/S2/S3) from multiple market drivers to compute Aggressiveness (A) and Exit Assertiveness (E) scores.

**Five Regime Drivers** (tracked across 3 timeframes):
1. **BTC** - Bitcoin trend (affects all tokens, weight: 1.0)
2. **ALT** - Altcoin composite (SOL/ETH/BNB/HYPE average, weight: 1.5)
3. **BUCKET** - Market cap bucket composites (nano/small/mid/big, weight: 3.0)
4. **BTC.d** - BTC dominance (inverted - uptrend = risk-off, weight: -1.0)
5. **USDT.d** - USDT dominance (inverted, 3x weight - uptrend = strong risk-off, weight: -3.0)

**Three Timeframes**:
- **Macro (1d)** - Slow shifts, big picture (weight: 0.50)
- **Meso (1h)** - Main operational timeframe (weight: 0.40)
- **Micro (1m)** - Tactical adjustments (weight: 0.10)

**How it works**:
1. Regime Price Collector gathers OHLC data for all drivers
2. Regime TA Tracker computes technical indicators
3. Uptrend Engine computes states/flags for each driver
4. Regime Mapper converts states → ΔA/ΔE deltas
5. Driver weights and timeframe multipliers applied
6. Final A/E scores computed for each token

**Total**: 5 drivers × 3 timeframes = **15 regime channels** per token, all feeding into A/E calculation.

### **Pipeline Architecture**

*Summary:* Each market has different ingestion + execution requirements, but the trend engine is universal.

Multiple pipelines feed OHLCV data into the same engine. Pipelines exist because each market has different ingestion + execution requirements — but the trend engine is universal.

```
Lowcap Pipeline:
  Social Ingest (Twitter/Telegram) 
    → Decision Maker 
    → OHLCV Data Collection 
    → Uptrend Engine v4 
    → Portfolio Manager 
    → Lowcap Executor (Li.Fi - multi-chain)

Perps Pipeline:
  Market Data Ingest 
    → Decision Maker 
    → OHLCV Data Collection 
    → Uptrend Engine v4 
    → Portfolio Manager 
    → Perps Executor (Hyperliquid)

Prediction Pipeline:
  Market Data Ingest 
    → Decision Maker 
    → OHLCV Data Collection 
    → Uptrend Engine v4 
    → Portfolio Manager 
    → Prediction Executor (Polymarket, etc.)
```

**Each pipeline**:
- Has its own data ingestion (social signals, market data, etc.)
- Has its own executor (Li.Fi for multi-chain, Hyperliquid SDK, etc.)
- **Shares the same Uptrend Engine v4** (universal trend detection)
- **Shares the same Portfolio Manager** (decision-making logic)
- **Shares the same Learning System** (outcome-first learning across all pipelines)

---

## 𓂀 **The Learning System**

*Summary:* Outcome-first learning — pattern × action × scope → outcome → edge → lessons → behaviour.

Lotus Trader learns from outcomes, not from predictions. Every learning cycle follows the same atomic process:

**pattern × action × scope → outcome → edge → lessons → behaviour**

The system measures what is true, not what is plausible. Math governs truth. LLM intelligence interprets meaning and evolves structure.

### **Outcome-First Learning**

**The Key Principle**: Start with outcomes, work backwards to discover patterns within specific scopes.

**What is a scope?** A precise slice of reality — the contextual lens through which a pattern is measured. Scopes encode timeframe, volatility regime, liquidity state, market-cap tier, venue type, and trend maturity. The same pattern behaves differently in different scopes.

**Learning Flow**:
1. **Position closes** → PM computes R/R from OHLCV data
2. **Event recorded** → `position_closed` strand created in `ad_strands` table
3. **Pattern extraction** → Pattern, action, and scope extracted from trade context
4. **Event aggregation** → `pattern_scope_aggregator` collects events into `pattern_trade_events`
5. **Statistics computed** → `pattern_scope_stats` table stores aggregated edge metrics
6. **Lessons mined** → `lesson_builder_v5` discovers lessons from pattern scope statistics
7. **Overrides materialized** → `override_materializer` converts lessons to PM overrides
8. **Behaviour updated** → PM applies overrides at runtime

### **The Two-Layer Learning Architecture**

#### **Math Recursion — the structural core**

The math layer evaluates behaviour within each scope using a composite edge field:

**edge = ΔRR × reliability × (support + magnitude + time + stability) × decay**

Each component contributes:
- **ΔRR** — improvement over global baseline (multiplicative)
- **reliability** — variance and consistency (multiplicative)
- **support** — how many times pattern observed (additive)
- **magnitude** — typical reward (additive)
- **time** — confirmation speed (additive)
- **stability** — how edge behaves over time (additive)
- **decay** — penalizes degrading patterns (multiplicative)

Only when this field is strong and stable within a scope does Lotus promote a pattern into a lesson.

#### **LLM Recursion — the interpretive mind**

The LLM layer reasons about meaning:
- Why did edge decay?
- What structural boundary changed?
- Which narrative or regime shift altered behaviour?
- What hypothesis should be tested next?

Math learns **what happens**. LLMs learn **why it happens** and **how the system should evolve**.

### **Three Types of Lessons**

When a pattern repeatedly produces edge inside a scope, Lotus distils that lesson into three distinct behavioural channels:

#### **1. PM Strength Lessons** ✅ Active

**Purpose**: Encode **how aggressively to size** within a scope.

**How it works**:
- Pattern that shows strong edge in scope `{4h, micro, high-vol}` might learn PM strength multiplier of 2.5x
- Same pattern in scope `{1m, major, low-vol}` might learn 0.6x
- PM strength is clamped between 0.3x and 3.0x
- Learned per pattern×scope combination
- Applied at runtime to modulate position sizing

**Example**:
```
Pattern: uptrend.S1.buy_flag
Scope: {timeframe: "4h", mcap_bucket: "micro", vol_bucket: "high"}
PM Strength: 2.5x (size at 2.5× base allocation)
```

#### **2. PM Tuning Lessons** ✅ Active

**Purpose**: Encode **threshold adjustments** for Portfolio Manager's entry/exit gates.

**How it works**:
- When pattern in specific scope shows high miss rates, Lotus learns to tighten thresholds (TS, SR, halo, slope guards, DX suppression)
- When miss rates are low, thresholds can be relaxed
- PM tuning adjusts the *gates* that determine when signals fire
- Allows Lotus to learn "this pattern works, but only if we're more selective in this scope"

**Example**:
```
Pattern: uptrend.S1.buy_flag
Scope: {timeframe: "1m", mcap_bucket: "major", vol_bucket: "low"}
PM Tuning: TS threshold +0.05 (require higher trend strength)
```

#### **3. DM Allocation Lessons** ✅ Active

**Purpose**: Encode **timeframe weight splits** for Decision Maker.

**How it works**:
- When pattern shows stronger edge on 4h than 1m within a scope, Lotus learns to allocate more capital to 4h timeframe
- Creates dynamic allocation that adapts to where edge actually exists
- Updates `learning_configs` table with timeframe weights

**Example**:
```
Pattern: uptrend.S1.buy_flag
Scope: {mcap_bucket: "micro", vol_bucket: "high"}
DM Allocation: {1m: 0.2, 15m: 0.3, 1h: 0.3, 4h: 0.2}
```

### **Coefficients (Decision Maker Learning)** ✅ Active

**Purpose**: Learn which levers (curator, chain, mcap, vol, age, intent) correlate with R/R outcomes.

**How it works**:
- Each lever starts with neutral weight = 1.0
- Drifts toward observed R/R ratio: `factor_weight = R/R_avg / R/R_global`
- **Two layers**:
  - **Single-factor coefficients**: "Base chain averages 1.4× R/R" → `chain_weight['base'] = 1.4`
  - **Interaction patterns**: `{curator=detweiler, chain=base, age<7d}` → 1.8× R/R
- **Temporal dimension**: Short-term (14 days) vs long-term (90 days) memory
- **Importance bleed**: Prevents double-counting when interaction patterns are active

**Allocation formula**: `initial_allocation = base_allocation × ∏(factor_weight[lever])`

### **LLM Learning Layer** ⏸️ Infrastructure Ready (Phased Enablement)

**Purpose**: Add qualitative intelligence parallel to the math layer - semantic interpretation, hypothesis generation, pattern recognition.

**Architecture** (when enabled):
- **Overseer** — strategic mind that decides what is worth thinking about
- **Research Manager** — turns questions into safe, controlled experiments
- **Level 1** — perception layer (surfaces landscape, anomalies, edge zones)
- **Levels 2–5** — targeted investigators (semantics, structure, cross-pattern rhymes, timing)
- **Math Verification** — all hypotheses pass through statistical verification

**The Golden Rule**: LLM ≠ math. LLM ≠ statistics. LLM = structure + semantic intelligence. Everything numerical stays in the math layer. LLM reshapes structure, discovers new representations, proposes new abstractions.

---

## 🜄 **How It Works**

*Summary:* Engine emits signals, Portfolio Manager makes decisions, Executor executes trades. Clean separation of concerns.

### **Signal Emission Model**

**Uptrend Engine v4** emits signals and flags - it does NOT make trading decisions.

- **Engine responsibility**: Compute state (S0/S1/S2/S3), conditions, quality scores (TS, OX, DX, EDX), emit clear signals
- **Portfolio Manager responsibility**: Interpret signals, combine with A/E scores, make trading decisions
- **Executor responsibility**: Execute trades, return results (no database writes)

**Output format**: Structured payload with state, flags, scores, and **diagnostics** (always populated, not optional).

### **State Machine (S0→S1→S2→S3)**

- **S0 (Pure Downtrend)**: Perfect bearish EMA order - fast band below mid, slow descending
- **S1 (Primer)**: Fast band above EMA60, price above EMA60 - looking for entries at EMA60
- **S2 (Defensive)**: Price above EMA333, not yet full alignment - looking for exits at expansion (OX trims) and entries at EMA333 (retest buys)
- **S3 (Trending)**: Full bullish alignment - all EMAs above EMA333, full bullish order

**Buy signals**:
- **From S1**: Entry zone (price within 1.0× ATR of EMA60), slope OK (EMA60 or EMA144 rising), TS gate (TS + S/R boost ≥ 0.58)
- **From S2**: Retest buys at EMA333 (same conditions, anchored to EMA333)
- **From S3**: DX buys in deep zones (DX ≥ 0.60)

**Exit signals**:
- **Global exit**: Fast band at bottom (overrides all states)
- **S2/S3 trims**: OX ≥ 0.65 (pump trims)
- **S3 emergency exit**: Price < EMA333 (flag only, doesn't change state)

### **Multi-Timeframe Positions**

**Each token/asset gets 4 independent positions from day one**:
- **1m position**: Fast signals, quick entries/exits
- **15m position**: Medium-term trends
- **1h position**: Primary trading timeframe
- **4h position**: Long-term trends

Each position has:
- Its own allocation (split from Decision Maker's total allocation)
- Its own entries/exits (independent PnL tracking)
- Its own status flow: `dormant` (< 350 bars) → `watchlist` (ready) → `active` (holding) → `watchlist` (closed)

**Why this matters**: The same trend can be in different states on different timeframes. A token might be S3 on 4h (trending) but S1 on 1m (looking for entry). The system trades each timeframe independently.

### **Portfolio Manager Integration**

**Portfolio Manager** combines:
- **Uptrend Engine signals** (state, buy_signal, buy_flag, trim_flag, scores)
- **A/E scores** (Add Appetite, Exit Assertiveness) - computed by Regime Engine from 5 drivers across 3 timeframes, plus token-level intent deltas
- **Position sizing** (entry/trim multipliers, profit multipliers, allocation multipliers)

**Decision flow**:
1. PM Core Tick runs timeframe-specifically (1m=1min, 15m=15min, 1h=1hr, 4h=4hr)
2. Fetches active/watchlist positions for timeframe
3. Computes A/E scores for each position
4. Calls `plan_actions_v4()` to generate decisions
5. Executor executes trades, returns results
6. PM updates position state, writes `completed_trades` JSONB
7. On position closure: PM computes R/R, emits `position_closed` strand
8. Learning system processes strand → Updates coefficients/braids

---

## ⚘ **Getting Started**

### **Prerequisites**

- Python 3.8+
- Node.js 16+ (for Solana transactions via Jupiter)
- PostgreSQL database (Supabase recommended)
- API keys:
  - Supabase (database)
  - OpenRouter (LLM for social ingest)
  - GeckoTerminal (price data)
  - Trading platforms (Jupiter for Solana, Li.Fi for multi-chain, Hyperliquid for perps, etc.)

### **Database Setup**

**Step 1: Create Database**

If using Supabase:
1. Create a new project at [supabase.com](https://supabase.com)
2. Note your project URL and service role key

If using local PostgreSQL:
```bash
createdb lotus_trader
```

**Step 2: Set Up Schema**

Run all schema files in `src/database/` in this order:

```bash
# Core tables (required)
psql -d lotus_trader -f src/database/ad_strands_schema.sql
psql -d lotus_trader -f src/database/lowcap_positions_v4_schema.sql
psql -d lotus_trader -f src/database/lowcap_price_data_1m_schema.sql
psql -d lotus_trader -f src/database/lowcap_price_data_ohlc_schema.sql
psql -d lotus_trader -f src/database/majors_price_data_ohlc_schema.sql
psql -d lotus_trader -f src/database/majors_trades_ticks_schema.sql
psql -d lotus_trader -f src/database/regime_price_data_ohlc_schema.sql

# Portfolio/Phase tables
psql -d lotus_trader -f src/database/portfolio_bands_schema.sql
psql -d lotus_trader -f src/database/phase_state_schema.sql
psql -d lotus_trader -f src/database/phase_state_bucket_schema.sql
psql -d lotus_trader -f src/database/token_cap_bucket_schema.sql

# Learning system tables
psql -d lotus_trader -f src/database/learning_coefficients_schema.sql
psql -d lotus_trader -f src/database/learning_configs_schema.sql
psql -d lotus_trader -f src/database/learning_baselines_schema.sql
psql -d lotus_trader -f src/database/learning_lessons_schema.sql
psql -d lotus_trader -f src/database/pattern_scope_stats_schema.sql
psql -d lotus_trader -f src/database/pattern_trade_events_schema.sql
psql -d lotus_trader -f src/database/pattern_episode_events_schema.sql

# Other tables
psql -d lotus_trader -f src/database/curators_schema.sql
psql -d lotus_trader -f src/database/wallet_balances_schema.sql
psql -d lotus_trader -f src/database/wallet_balance_snapshots_schema.sql
psql -d lotus_trader -f src/database/token_timeframe_blocks_schema.sql
psql -d lotus_trader -f src/database/pm_overrides_schema.sql
psql -d lotus_trader -f src/database/pm_thresholds_schema.sql
psql -d lotus_trader -f src/database/position_signals_schema.sql

# Optional: Learning system extensions
psql -d lotus_trader -f src/database/learning_braids_schema.sql
psql -d lotus_trader -f src/database/learning_regime_weights_schema.sql
psql -d lotus_trader -f src/database/learning_edge_history_schema.sql
psql -d lotus_trader -f src/database/learning_latent_factors_schema.sql
psql -d lotus_trader -f src/database/llm_learning_schema.sql
```

**Step 3: Run Migrations**

Apply any pending migrations:

```bash
# Apply migrations in order
psql -d lotus_trader -f src/database/migrations/2025_01_14_add_trade_id_columns.sql
psql -d lotus_trader -f src/database/migrations/2025_12_03_add_regime_driver_status.sql
psql -d lotus_trader -f src/database/migrations/2025_12_05_allow_1d_timeframe.sql
psql -d lotus_trader -f src/database/migrations/2025_12_29_add_token_timeframe_blocks.sql
```

**Step 4: Set Up Row Level Security (Optional but Recommended)**

```bash
psql -d lotus_trader -f src/database/rls_policies.sql
```

**Note**: The Bootstrap System (runs on startup) will automatically:
- Verify all tables exist
- Create regime driver positions if missing
- Backfill price data from Binance (up to 666 bars per timeframe)
- Verify data collection systems are working

### **Data Sources Setup**

**Step 1: Configure Curators**

Curators are configured in `src/config/twitter_curators.yaml`. The system automatically populates the `curators` database table from this YAML file on startup.

Edit `src/config/twitter_curators.yaml` to add or modify curators:

```yaml
curators:
  - id: "0xdetweiler"
    name: "0xDetweiler"
    platforms:
      twitter:
        handle: "@0xdetweiler"
        active: true
        priority: "high"
    tags: ["defi", "alpha", "technical"]
    notes: "Strong technical analysis and DeFi focus"
```

You can add curators for:
- **Twitter only**: Just include `twitter` platform section
- **Telegram only**: Just include `telegram` platform section  
- **Both platforms**: Include both `twitter` and `telegram` sections

The system will automatically sync these to the database `curators` table when it starts.

**Step 2: Set Up Twitter Authentication** (Required for Twitter monitoring)

Twitter monitoring uses Playwright with cookie-based authentication. You need to log in once with a headed browser, then the system runs in headless mode.

1. **First-time setup** (headed browser login):
```bash
cd src/intelligence/social_ingest
python twitter_auth_setup.py
```

This will:
- Open a browser window (headed mode)
- Navigate to Twitter login
- Wait for you to log in manually
- Save cookies to `src/config/twitter_cookies.json`
- Test the connection

2. **After setup**: The system automatically uses saved cookies in headless mode for monitoring.

**Note**: If cookies expire, re-run `twitter_auth_setup.py` to refresh them.

**Step 3: Telegram Setup** (Optional, if using Telegram curators)

For Telegram monitoring, you need:
- Telegram Bot Token (set `TELEGRAM_BOT_TOKEN` in `.env`)
- Telegram Channel IDs (configured in `twitter_curators.yaml`)

The system will automatically monitor Telegram channels listed in your curator configuration.

### **Quick Start**

```bash
# Clone the repository
git clone https://github.com/Recursive-Llama/Lotus_Trader.git
cd Lotus_Trader

# Install dependencies
pip install -r requirements.txt
npm install

# Set up environment variables
cp env.example .env
# Edit .env with your API keys:
#   - SUPABASE_URL and SUPABASE_KEY (or SUPABASE_SERVICE_ROLE_KEY)
#   - OPENROUTER_API_KEY
#   - Wallet private keys (if trading enabled)
#   - ACTIONS_ENABLED=0 (read-only) or ACTIONS_ENABLED=1 (trading enabled)

# Run the production system
python src/run_trade.py
```

**Alternative Entry Point**: `src/run_social_trading.py` is a simpler entry point for development/testing, but `src/run_trade.py` is the production system with full scheduling, bootstrap, and regime pipeline.

### **Configuration**

Key configuration files:
- `src/config/trading_plans.yaml` - Trading strategy parameters
- `src/config/twitter_curators.yaml` - Social media curators to monitor
- `src/config/context_injection.yaml` - Learning system context injection

---

## ⌖ **Backtesting**

Lotus Trader includes a comprehensive backtesting system that uses the **exact same engine** as production.

**Key features**:
- **Single source of truth**: Backtester calls `UptrendEngineV4` methods directly (no duplicate logic)
- **Diagnostics preserved**: All slope values, condition checks, missing conditions in JSON output
- **Visualization**: Charts show TS threshold markers, state transitions, buy/sell signals
- **Multi-timeframe**: Test all 4 timeframes independently
- **Consistency guarantee**: Impossible for backtester to diverge from production

**Run backtest**:
```bash
cd backtester/v4/code
python backtest_uptrend_v4.py --token CONTRACT --chain solana --timeframe 1h --start 2024-01-01 --end 2024-01-31
```

---

## ⧖ **System Status**

### **☼ Production Ready**

- ✅ **Uptrend Engine v4** - Universal trend detection (S0→S1→S2→S3 state machine)
- ✅ **Regime Engine** - Market regime detection using 5 drivers across 3 timeframes for A/E calculation
- ✅ **Bootstrap System** - Comprehensive startup verification and data backfill
- ✅ **Lowcap Pipeline** - Social ingest (Twitter/Telegram) → DM → PM → Li.Fi executor
- ✅ **Multi-timeframe positions** - 4 independent positions per token (1m, 15m, 1h, 4h)
- ✅ **Portfolio Manager v4** - Regime-driven A/E scores, signal integration, position management
- ✅ **Learning System** - Pattern × scope × action → outcome learning (PM strength, PM tuning, DM allocation lessons)
- ✅ **Coefficients** - Decision Maker learning (single-factor + interaction patterns, EWMA, importance bleed)
- ✅ **Balance Tracking** - Hierarchical snapshots (hourly, 4h, daily, weekly, monthly)
- ✅ **Backtesting** - Full backtest suite using production engine
- ✅ **Multi-chain execution** - Li.Fi SDK for unified cross-chain trading
- ✅ **Comprehensive Scheduling** - 1m, 5m, 15m, hourly, 4h, daily, weekly, monthly jobs

### **☽ In Development**

- 🔄 **LLM Learning Layer** - Semantic features, hypothesis generation, structure evolution (infrastructure ready, phased enablement)
- 🔄 **Additional Pipelines** - Perps (Hyperliquid), Prediction (Polymarket), Stocks
- 🔄 **Enhanced Learning** - Cross-pipeline learning, improved pattern discovery, scope evolution

---

## ∴ **Key Concepts**

### **Why Universal?**

The Uptrend Engine v4 works on any OHLCV data because:
- **Human behavior is universal** - The same greed, fear, and FOMO that drives crypto pumps also drives stock rallies
- **Market dynamics are universal** - Support/resistance, trend following, momentum - these patterns repeat across all markets
- **Timeframes are similar** - A 1-minute crypto chart and a 4-hour stock chart show the same EMA state transitions, just at different speeds

### **Why Multi-Timeframe?**

The same trend can be in different states on different timeframes:
- **4h S3 (trending)** + **1h S1 (primer)** = Long-term uptrend, short-term entry opportunity
- **1m S2 (defensive)** + **15m S0 (downtrend)** = Short-term bounce, medium-term decline

Each timeframe gives independent signals. The system trades each one separately.

### **Why Outcome-First Learning?**

Traditional ML starts with features and predicts outcomes. Lotus Trader starts with outcomes and discovers features:
- **We know what we want**: High R/R, short hold time
- **We work backwards**: "What pattern × action × scope combinations led to these outcomes?"
- **Patterns emerge from data**: Not predefined, discovered through statistical measurement within scopes
- **Scope-based modulation**: The same pattern behaves differently in different scopes — Lotus learns these differences precisely
- **Gentle tuning**: Insights adjust decision-making through PM strength (0.3x–3.0x), PM tuning (threshold adjustments), and DM allocation (timeframe splits)

### **System Scheduling**

The production system (`run_trade.py`) runs a comprehensive scheduling system:

**Bootstrap Phase** (on startup):
- Database table verification
- Wallet balance collection
- Price data verification
- Hyperliquid WS connection (if enabled)
- Regime driver position creation
- Regime price data backfill (up to 666 bars per timeframe)

**High Frequency (1 minute)**:
- OHLC conversion (1m price points → 1m OHLC bars)
- Majors rollup (Hyperliquid ticks → 1m OHLC)
- TA Tracker (1m)
- Uptrend Engine (1m)
- PM Core Tick (1m)
- Regime Pipeline (1m)

**Medium Frequency (5 minutes)**:
- Features/Phase Tracker
- Pattern Scope Aggregator
- OHLC Rollup (5m)

**Standard Frequency (15 minutes)**:
- TA Tracker (15m)
- OHLC Rollup (15m)
- Uptrend Engine (15m)
- PM Core Tick (15m)

**Hourly Jobs**:
- :01 - Regime Pipeline (1h)
- :02 - NAV computation
- :02 - Rollup catch-up (15m, 1h, 4h)
- :04 - OHLC Rollup (1h)
- :05 - Geometry Builder (all timeframes)
- :06 - TA Tracker (1h), PM Core Tick (1h)
- :07 - Bars count update
- :08 - Lesson Builder (PM)
- :09 - Lesson Builder (DM)
- :10 - Override Materializer
- :11 - Cap Bucket Tagging
- :12 - Bucket Tracker
- :00 - Hourly Balance Snapshot

**4-Hour Jobs**:
- :00 - OHLC Rollup (4h)
- :00 - TA Tracker (4h), PM Core Tick (4h)
- :00 - 4-Hour Balance Snapshot Rollup

**Daily Jobs**:
- 00:00 - Regime Pipeline (1d)
- 01:00 - Daily Balance Snapshot Rollup

**Weekly Jobs**:
- Sunday 01:00 - Weekly Balance Snapshot Rollup

**Monthly Jobs**:
- 1st 02:00 - Monthly Balance Snapshot Rollup

---

## ⟡ **Documentation**

### **Core Specifications**

- **[Uptrend Engine v4 Spec](./docs/trencher_improvements/PM/v4_uptrend/UPTREND_ENGINE_V4_SPEC.md)** - Complete state machine specification
- **[Lotus⚘⟁3 Whitepaper](./docs/architecture/Lotus⚘⟁3_whitepaper.md)** - Complete system philosophy and architecture

### **Architecture**

- **[Complete Integration Plan](./docs/trencher_improvements/PM/v4_uptrend/COMPLETE_INTEGRATION_PLAN.md)** - Multi-timeframe, PM integration, system flow
- **[Implementation Status](./docs/trencher_improvements/PM/v4_uptrend/IMPLEMENTATION_STATUS.md)** - What's built, what's coming
- **[Regime Engine](./docs/inprogress/Regime_engine.md)** - Market regime detection system
- **[Scaling A/E v2](./docs/implementation/scaling_ae_v2_implementation.md)** - Episode-based learning and scaling

### **System Operations**

- **[Bootstrap System](./src/intelligence/lowcap_portfolio_manager/jobs/bootstrap_system.py)** - Startup verification and data backfill
- **[Scheduling Architecture](./docs/architecture/run_trade_plan.md)** - Job scheduling and dependencies

---

## ⚘ **The Vision**

Lotus Trader is not a trading bot. It's a universal trend engine + quantitative intelligence that works on anything with OHLCV data.

Lotus Trader represents a fundamental shift from trading bots to **universal trend detection systems**.

**The Core Innovation**: One engine that works on any market, any timeframe, any asset class - because all markets are driven by the same human behavior and market dynamics.

**The Learning Innovation**: Pattern × action × scope → outcome → edge → lessons → behaviour. Not ML prediction, but statistical measurement within precise contextual scopes. Math measures truth. LLM intelligence evolves structure.

**The Architecture Innovation**: Multiple pipelines, one engine, one learning system. Each pipeline handles its own data and execution, but they all share the universal trend detection core and outcome-first learning system.

**Note**: This codebase implements **Lotus Trader⚘⟁** only. The broader Lotus⚘⟁3 system includes Lotus Seer☊ (prediction markets) and a future Meta-Agent (system-level intelligence), but those are separate implementations.

---

*Lotus Trader V3 - Universal trend detection that learns from outcomes across all markets.*
