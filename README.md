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

## 🎯 **Core Architecture**

Lotus Trader V3 has three core components:

1. **A universal trend engine** - Uptrend Engine v4 detects trends in any market
2. **A cross-pipeline architecture** - Multiple pipelines share one engine and learning system
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

## 🧠 **The Learning System**

*Summary:* Outcome-first exploration — start with what worked, discover what led to it, gently tune decision-making.

Lotus Trader learns from outcomes, not from signals. The learning system works backwards from what actually happened to discover what led to success.

**Example:**
After analyzing 24 big wins, the system discovers that 78% happened when:
- S1 entry (primer state)
- TS > 0.55 (trend strength threshold)
- Market cap < $10M
- Token age < 10 days

The Portfolio Manager increases allocation for this pattern by +6% (gentle tuning, not replacement).

### **Outcome-First Exploration**

**The Key Principle**: Start with outcomes (big wins, big losses), work backwards to find patterns.

**What is a big win?** A completed trade with R/R > 2.0 (risk/reward ratio - return divided by max drawdown). The system classifies all closed positions as: big_win, big_loss, small_win, small_loss, or breakeven based on their R/R outcome.

1. **Position closes** → PM computes R/R from OHLCV data
2. **Outcome classified** → big_win, big_loss, small_win, small_loss, breakeven
3. **Pattern discovery** → "What contexts/signals led to these outcomes?"
4. **Braiding** → Similar outcomes braided together to discover common patterns
5. **Insights applied** → Gentle tuning of decision-making (not replacement)

### **Three Layers of Learning**

#### **1. Coefficients (Decision Maker Learning)** ✅ Complete

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

#### **2. Braiding (Portfolio Manager Learning)** ⏸️ Coming

**Purpose**: Learn from action sequences (add → trim → exit), discover optimal timing, find counterfactual improvements.

**How it works**:
- **Outcome classification**: Classify all completed trades by outcome and hold time
- **Dimension extraction**: Extract A/E scores, engine signals, scores, timing from `action_context`
- **Pattern querying**: "Find all big wins where A=med, E=low, buy_flag=True, S1, TS>0.6"
- **Pattern statistics**: Calculate avg_rr, win_rate, sample_size, variance for each pattern
- **Counterfactual analysis**: "Could we have entered 6 bars later? What signals were showing then?"

**Example braid lesson:**
```
Pattern: big_win | A=med | E=low | buy_flag=True | S1 | TS>0.6
Stats: avg_rr=2.3, win_rate=0.85, sample_size=12
Lesson: Increase entry size by +8% when this pattern matches
```

**Why braiding for PM**: PM has sequential actions (add → trim → exit), not just entry → exit. Coefficients can't handle sequences or counterfactuals well. Braiding can explore sequences and find "what if" patterns.

#### **3. LLM Learning Layer** ⏸️ Coming (Build from Day 1, Phased Enablement)

**Purpose**: Add qualitative intelligence parallel to the math layer - semantic interpretation, hypothesis generation, pattern recognition.

**Five Levels** (phased enablement):
1. **Commentary** (Day 1): Natural-language insights, regime summaries
2. **Semantic Features** (Day 1): Extract narrative tags ("AI narrative", "memecoin revival") as hypotheses
3. **Family Optimization** (50+ trades): Propose better braid groupings based on observed patterns
4. **Semantic Compression** (100+ trades): Conceptual patterns that span multiple dimensional combinations
5. **Hypothesis Generation** (10+ trades): Propose new tests, bucket boundaries, interaction patterns

**The Golden Rule**: LLM ≠ math. LLM ≠ statistics. LLM = structure + semantic intelligence. Everything numerical stays in the math layer. LLM reshapes structure, discovers new representations, proposes new abstractions.

---

## 📊 **How It Works**

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
- **A/E scores** (Add Appetite, Exit Assertiveness) - influenced by market phases, portfolio risk, token age, market cap, social intent
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

## 🚀 **Getting Started**

### **Prerequisites**

- Python 3.8+
- Node.js 16+ (for Solana transactions via Jupiter)
- PostgreSQL database (Supabase recommended)
- API keys:
  - Supabase (database)
  - OpenRouter (LLM for social ingest)
  - GeckoTerminal (price data)
  - Trading platforms (Li.Fi for multi-chain, Hyperliquid for perps, etc.)

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
# Edit .env with your API keys

# Run the lowcap pipeline
python src/run_social_trading.py
```

### **Configuration**

Key configuration files:
- `src/config/trading_plans.yaml` - Trading strategy parameters
- `src/config/twitter_curators.yaml` - Social media curators to monitor
- `src/config/context_injection.yaml` - Learning system context injection

---

## 📈 **Backtesting**

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

## 🏗️ **System Status**

### **☼ Production Ready**

- ✅ **Uptrend Engine v4** - Universal trend detection (S0→S1→S2→S3 state machine)
- ✅ **Lowcap Pipeline** - Social ingest (Twitter/Telegram) → DM → PM → Li.Fi executor
- ✅ **Multi-timeframe positions** - 4 independent positions per token (1m, 15m, 1h, 4h)
- ✅ **Portfolio Manager v4** - A/E scores, signal integration, position management
- ✅ **Learning System Phase 1 & 2** - Coefficients (single-factor + interaction patterns, EWMA, importance bleed)
- ✅ **Backtesting** - Full backtest suite using production engine
- ✅ **Multi-chain execution** - Li.Fi SDK for unified cross-chain trading

### **☽ In Development**

- 🔄 **Braiding System** - PM learning from action sequences (outcome-first exploration)
- 🔄 **LLM Learning Layer** - Semantic features, hypothesis generation (infrastructure ready, phased enablement)
- 🔄 **Additional Pipelines** - Perps (Hyperliquid), Prediction (Polymarket), Stocks
- 🔄 **Enhanced Learning** - Cross-pipeline learning, regime detection improvements

---

## 🎓 **Key Concepts**

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
- **We work backwards**: "What contexts/signals led to these outcomes?"
- **Patterns emerge from data**: Not predefined, discovered through braiding
- **Gentle tuning**: Insights adjust decision-making by small amounts (max 10%), not replacement

---

## 📚 **Documentation**

### **Core Specifications**

- **[Uptrend Engine v4 Spec](./docs/trencher_improvements/PM/v4_uptrend/UPTREND_ENGINE_V4_SPEC.md)** - Complete state machine specification
- **[Learning System v4](./docs/trencher_improvements/PM/v4_uptrend/v4_Learning/LEARNING_SYSTEM_V4.md)** - Coefficients, braiding, LLM layer
- **[Braiding System Design](./docs/trencher_improvements/PM/v4_uptrend/v4_Learning/BRAIDING_SYSTEM_DESIGN.md)** - Outcome-first exploration architecture
- **[Braiding Implementation Guide](./docs/trencher_improvements/PM/v4_uptrend/v4_Learning/BRAIDING_IMPLEMENTATION_GUIDE.md)** - Step-by-step implementation

### **Architecture**

- **[Complete Integration Plan](./docs/trencher_improvements/PM/v4_uptrend/COMPLETE_INTEGRATION_PLAN.md)** - Multi-timeframe, PM integration, system flow
- **[Implementation Status](./docs/trencher_improvements/PM/v4_uptrend/IMPLEMENTATION_STATUS.md)** - What's built, what's coming

---

## ⚘ **The Vision**

Lotus Trader is not a trading bot. It's a universal trend engine + outcome-first learner that works on anything with OHLCV data.

Lotus Trader represents a fundamental shift from trading bots to **universal trend detection systems**.

**The Core Innovation**: One engine that works on any market, any timeframe, any asset class - because all markets are driven by the same human behavior and market dynamics.

**The Learning Innovation**: Outcome-first exploration - start with what worked, discover what led to it, gently tune decision-making. Not ML prediction, but pattern discovery from outcomes.

**The Architecture Innovation**: Multiple pipelines, one engine, one learning system. Each pipeline handles its own data and execution, but they all share the universal trend detection core.

---

*Lotus Trader V3 - Universal trend detection that learns from outcomes across all markets.*
