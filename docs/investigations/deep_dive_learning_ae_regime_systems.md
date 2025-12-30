# Deep Dive: Learning Systems, A/E System, and Regime/Market Systems

**Date**: 2025-01-XX  
**Purpose**: Comprehensive technical deep dive into three interconnected systems

---

## Table of Contents

1. [Learning Systems Deep Dive](#1-learning-systems-deep-dive)
2. [A/E System Deep Dive](#2-ae-system-deep-dive)
3. [Regime and Market System Deep Dive](#3-regime-and-market-system-deep-dive)
4. [System Interconnections](#4-system-interconnections)

---

# 1. Learning Systems Deep Dive

## 1.1 Architecture Overview

The learning system is a **multi-layered, outcome-first learning architecture** that processes trading outcomes to improve future decisions. It operates in **real-time** (when positions close) and **periodically** (via scheduled jobs).

### Core Philosophy: Outcome-First Exploration

The system works **backwards from outcomes** (big wins, big losses) to discover what led to success. It does NOT learn from signals—it learns from **what actually happened**.

**Key Principle**: Start with outcomes (R/R > 2.0 = big win), work backwards to find patterns, then gently tune decision-making (not replacement).

## 1.2 Three Main Layers

### Layer 1: Event Collection (Real-Time)

**Trigger**: When a position closes

**Process**:
1. PM Core Tick creates a `position_closed` strand in `ad_strands` table
2. Strand contains:
   - `entry_context`: Full context at entry (regime states, A/E values, timeframe, bucket, etc.)
   - `completed_trades`: Trade outcomes with R/R metrics, PnL, timestamps
3. UniversalLearningSystem.process_strand_event() is called automatically

**Data Structure**:
```python
position_closed_strand = {
    'kind': 'position_closed',
    'content': {
        'entry_context': {
            'regime_states': {...},  # BTC/ALT/bucket/BTC.d/USDT.d × macro/meso/micro
            'A_value': 0.65,
            'E_value': 0.45,
            'timeframe': '1h',
            'bucket': 'nano',
            'pattern_key': 'pm.uptrend.S1.buy_flag',
            # ... full context
        },
        'completed_trades': [{
            'rr': 2.3,  # Risk/Reward ratio
            'pnl_usd': 1250.50,
            'exit_timestamp': '2025-01-15T10:30:00Z',
            'summary': {...}
        }]
    }
}
```

### Layer 2: Pattern Mining (Periodic)

**Schedule**: Every 6 hours (Lesson Builder), Every 2 hours (Override Materializer)

**Process**:
1. **Pattern Scope Aggregator** (real-time + periodic backup):
   - Reads `position_closed` strands
   - Extracts pattern_key, action_category, scope, R/R, PnL
   - Writes one row per action to `pattern_trade_events` (fact table)

2. **Lesson Builder** (every 6 hours):
   - Reads `pattern_trade_events`
   - Mines patterns with N ≥ 33 samples
   - Calculates edge stats, decay metadata, half-lives
   - Writes aggregated lessons to `learning_lessons`

3. **Override Materializer** (every 2 hours):
   - Reads `learning_lessons`
   - Filters for actionable edges (significant edge, acceptable decay)
   - Writes to `pm_overrides`
   - PM Executor reads these at runtime

### Layer 3: Lesson Application (Real-Time)

**Process**:
- PM Executor reads `pm_overrides` when making decisions
- Applies pattern strength multipliers to position sizing
- Adjusts thresholds based on learned patterns

## 1.3 Three Parallel Learning Paths

When a position closes, three parallel paths execute simultaneously:

### Path 1: Coefficient Updates

**Component**: `CoefficientUpdater`

**Purpose**: Learn which timeframes correlate with better R/R outcomes

**How it works**:
- Updates timeframe weights in `learning_configs` table
- Uses EWMA (Exponentially Weighted Moving Average) with temporal decay
- Formula: `factor_weight = R/R_avg / R/R_global`
- Only updates timeframe weights (controls DM allocation split across timeframes)

**Storage**: `learning_configs` table
```json
{
  "module_id": "decision_maker",
  "config_data": {
    "timeframe_weights": {
      "1h": {
        "weight": 1.15,  # 1h trades average 15% better R/R
        "rr_short": 1.08,
        "rr_long": 1.05,
        "n": 42
      },
      "4h": {
        "weight": 0.92,  # 4h trades average 8% worse R/R
        "rr_short": 0.95,
        "rr_long": 0.89,
        "n": 28
      }
    },
    "global_rr": {
      "rr_short": 1.05,
      "rr_long": 0.98,
      "n": 150
    }
  }
}
```

**Temporal Decay**:
- Short-term decay (TAU_SHORT): Recent trades weighted more heavily
- Long-term decay (TAU_LONG): Maintains baseline over time
- Prevents system from overreacting to recent noise

### Path 2: Pattern Scope Aggregation

**Component**: `pattern_scope_aggregator.py`

**Purpose**: Extract and store raw trade events for pattern mining

**How it works**:
1. Reads `position_closed` strand
2. Extracts pattern_key (e.g., "pm.uptrend.S1.buy_flag")
3. Extracts action_category ("entry", "add", "trim", "exit")
4. Extracts full scope context:
   - Regime states: `btc_macro`, `btc_meso`, `btc_micro`, `alt_macro`, etc.
   - Token attributes: `chain`, `mcap_bucket`, `vol_bucket`, `age_bucket`
   - Trading context: `timeframe`, `A_mode`, `E_mode`, `intent`
5. Writes one row per action to `pattern_trade_events`

**Storage**: `pattern_trade_events` table (fact table)
```sql
CREATE TABLE pattern_trade_events (
    pattern_key TEXT NOT NULL,           -- "pm.uptrend.S1.buy_flag"
    action_category TEXT NOT NULL,       -- "entry", "add", "trim", "exit"
    scope JSONB NOT NULL,                -- Full context at action time
    rr FLOAT,                            -- Realized R/R for this action
    pnl_usd FLOAT,                       -- Realized PnL
    trade_id TEXT,                       -- Links to parent trade
    created_at TIMESTAMPTZ
);
```

**Scope Dimensions** (15 regime dimensions + 12 token dimensions):
- Regime: `btc_macro`, `btc_meso`, `btc_micro`, `alt_macro`, `alt_meso`, `alt_micro`, `bucket_macro`, `bucket_meso`, `bucket_micro`, `btcd_macro`, `btcd_meso`, `btcd_micro`, `usdtd_macro`, `usdtd_meso`, `usdtd_micro`
- Token: `curator`, `chain`, `mcap_bucket`, `vol_bucket`, `age_bucket`, `intent`, `mcap_vol_ratio_bucket`, `market_family`, `timeframe`, `A_mode`, `E_mode`, `bucket_leader`, `bucket_rank_position`

### Path 3: LLM Research Layer

**Component**: `LLMResearchLayer`

**Purpose**: Generate semantic hypotheses and reports from trade outcomes

**How it works**:
- Processes position_closed strands with LLM
- Generates hypotheses, reports, semantic tags
- Stores in `llm_learning` table
- Currently only Level 1 and 2 enabled by default

**Storage**: `llm_learning` table
```json
{
  "kind": "hypothesis",
  "level": 1,
  "module": "pm",
  "status": "hypothesis",
  "content": {
    "hypothesis": "S1 entries in nano bucket during BTC macro S3 show 2.3× R/R",
    "evidence": [...],
    "confidence": 0.78
  }
}
```

## 1.4 Pattern Mining Pipeline

### Step 1: Pattern Scope Aggregation (Real-Time + Periodic)

**Real-Time**: Called from `UniversalLearningSystem._process_position_closed_strand()`

**Periodic Backup**: Runs every 5 minutes to catch any missed events

**Output**: `pattern_trade_events` (raw fact table)

### Step 2: Lesson Builder (Every 6 Hours)

**Component**: `lesson_builder_v5.py`

**Process**:
1. Reads `pattern_trade_events`
2. Groups by (pattern_key, action_category, scope_subset)
3. Filters for N ≥ 33 samples (statistical significance)
4. Calculates:
   - `avg_rr`: Average R/R
   - `edge_raw`: Raw edge (avg_rr - 1.0)
   - `decay_meta`: Decay metadata (half-life, decay rate)
   - `win_rate`: Win rate
   - `variance`: Variance in outcomes
5. Writes to `learning_lessons`

**Storage**: `learning_lessons` table
```json
{
  "module": "pm",
  "pattern_key": "pm.uptrend.S1.buy_flag",
  "action_category": "entry",
  "scope_subset": {"chain": "solana", "mcap_bucket": "nano"},
  "n": 45,
  "stats": {
    "avg_rr": 1.85,
    "edge_raw": 0.85,
    "win_rate": 0.67,
    "variance": 0.42,
    "decay_halflife_hours": 120
  },
  "status": "active"
}
```

**Decay Calculation**:
- Uses exponential decay toward zero
- Handles both positive and negative R/R
- Estimates half-life: how long until pattern edge decays to 50%

### Step 3: Override Materializer (Every 2 Hours)

**Component**: `override_materializer.py`

**Process**:
1. Reads `learning_lessons`
2. Filters for actionable edges:
   - Significant edge (edge_raw > threshold)
   - Acceptable decay (decay_halflife_hours > minimum)
   - Sufficient samples (n ≥ 33)
3. Converts lessons to overrides:
   - `size_multiplier`: How much to adjust position sizing
   - `threshold_adjustments`: How to adjust entry/exit gates
4. Writes to `pm_overrides`

**Storage**: `pm_overrides` table
```json
{
  "pattern_key": "pm.uptrend.S1.buy_flag",
  "action_category": "entry",
  "scope": {"chain": "solana", "mcap_bucket": "nano"},
  "size_multiplier": 1.15,  # 15% larger positions
  "threshold_adjustments": {
    "ts_threshold": -0.02  # Lower TS threshold by 0.02
  },
  "status": "active"
}
```

### Step 4: Runtime Application

**Component**: `overrides.py` (called from PM Executor)

**Process**:
1. When PM Executor makes a decision, it calls `apply_pattern_strength_overrides()`
2. Looks up matching overrides for current pattern_key, action_category, scope
3. Applies size_multiplier to position sizing
4. Applies threshold_adjustments to entry/exit gates

**Example**:
```python
# Base position size: 5% of portfolio
# Pattern: pm.uptrend.S1.buy_flag, entry, scope={chain: solana, mcap_bucket: nano}
# Override: size_multiplier = 1.15
# Final position size: 5% × 1.15 = 5.75% of portfolio
```

## 1.5 Regime-Specific Learning

**Component**: `regime_weight_learner.py`

**Purpose**: Learn which patterns work better in which regimes

**How it works**:
1. Groups `pattern_trade_events` by regime signature
2. Regime signature format: `"macro=Recover|meso=Dip|bucket_rank=1"`
3. For each (pattern_key, action_category, regime_signature):
   - Computes edge stats
   - Learns regime-specific weights for meta-factors:
     - `time_efficiency`: How quickly pattern confirms
     - `field_coherence`: How consistent pattern is across tokens
     - `recurrence`: How often pattern repeats
     - `variance`: How stable pattern is
4. Stores in `learning_regime_weights` table

**Usage**: Used by Lesson Builder to compute adaptive edge scores that adjust based on current regime

## 1.6 Database Schema Summary

### Core Tables

1. **`ad_strands`** (Input)
   - Stores `position_closed` strands
   - Written by: PM Core Tick
   - Read by: UniversalLearningSystem

2. **`learning_configs`** (Coefficient Storage)
   - Stores timeframe weights, global R/R baseline
   - Written by: CoefficientUpdater
   - Read by: Decision Maker

3. **`pattern_trade_events`** (Fact Table)
   - One row per trade action
   - Written by: Pattern Scope Aggregator
   - Read by: Lesson Builder

4. **`learning_lessons`** (Mined Patterns)
   - Aggregated patterns with edge stats
   - Written by: Lesson Builder
   - Read by: Override Materializer

5. **`pm_overrides`** (Actionable Rules)
   - Filtered lessons ready for runtime
   - Written by: Override Materializer
   - Read by: PM Executor

6. **`llm_learning`** (LLM Research Outputs)
   - Hypotheses, reports, semantic tags
   - Written by: LLMResearchLayer
   - Read by: Analytics/Dashboards

7. **`learning_regime_weights`** (Regime-Specific Weights)
   - Regime-specific meta-factor weights
   - Written by: Regime Weight Learner
   - Read by: Lesson Builder

## 1.7 Key Algorithms

### EWMA with Temporal Decay

**Formula**:
```python
# Calculate decay weight
w = exp(-(current_time - trade_time) / TAU)

# EWMA update
alpha = w / (w + 1.0)
new_value = (1 - alpha) * old_value + alpha * new_observation
```

**Parameters**:
- `TAU_SHORT`: Short-term decay constant (recent trades weighted more)
- `TAU_LONG`: Long-term decay constant (maintains baseline)

### Decay Half-Life Estimation

**Formula**:
```python
# Linear regression on log-transformed R/R over time
log_rr = log(rr_values)
time_points = [hours_since_pattern_start]

# Fit: log_rr = a + b * time
# Half-life = -log(2) / b
```

**Interpretation**: How many hours until pattern edge decays to 50% of original

### Edge Score Calculation

**Formula**:
```python
edge_score = (
    time_efficiency_weight * time_efficiency +
    field_coherence_weight * field_coherence +
    recurrence_weight * recurrence +
    variance_weight * variance
) * edge_raw * decay_multiplier
```

**Regime-Adaptive**: Weights adjust based on current regime (from `learning_regime_weights`)

---

# 2. A/E System Deep Dive

## 2.1 Core Concept

**A (Aggressiveness)**: How much appetite to add new positions or increase existing positions  
**E (Exitness)**: How assertive to be about exiting positions or trimming

Both are continuous values in [0, 1]:
- A = 0.0: No new positions, reduce existing
- A = 1.0: Maximum position sizing, aggressive adds
- E = 0.0: Hold positions, don't exit
- E = 1.0: Aggressive exits, trim heavily

## 2.2 Architecture

The A/E system is **regime-driven**, replacing the old phase-based approach. It uses **Uptrend Engine states** from multiple market drivers to compute A/E scores.

### Inputs

1. **Regime Driver States** (5 drivers × 3 timeframes = 15 channels):
   - BTC trend (affects all tokens)
   - ALT composite trend (affects all tokens)
   - BUCKET composite (affects only that bucket)
   - BTC.d dominance (inverted - uptrend = risk-off)
   - USDT.d dominance (inverted, 3× weight - uptrend = strong risk-off)

2. **Intent Deltas** (per-token):
   - `hi_buy`: High buy intent → +A, -E
   - `med_buy`: Medium buy intent → +A (smaller), -E (smaller)
   - `profit`: Profit-taking intent → -A, +E
   - `sell`: Sell intent → -A, +E
   - `mock`: Mock/sarcasm → -A, +E (strongest negative)

3. **Bucket Multiplier** (bucket ordering/rank):
   - Based on bucket phase, rank, slope, confidence
   - Affects A (multiplier) and E (inverse)

### Outputs

- `A_value`: Final aggressiveness score [0, 1]
- `E_value`: Final exitness score [0, 1]
- `position_size_frac`: Position sizing fraction (derived from A)
- `diagnostics`: Full breakdown of components

## 2.3 Calculation Flow

### Step 1: Start from Neutral Baseline

```python
A_base = 0.5
E_base = 0.5
```

### Step 2: Compute Regime-Based A/E

**Component**: `RegimeAECalculator.compute_ae_for_token()`

**Process**:
1. Read regime driver states from `lowcap_positions` (status='regime_driver')
2. For each driver (BTC, ALT, bucket, BTC.d, USDT.d) and timeframe (1d, 1h, 1m):
   - Get Uptrend Engine state (S0/S1/S2/S3)
   - Get flags (buy_signal, buy_flag, trim_flag, first_dip_buy_flag)
   - Get transitions (S3→S0, S2→S0, S1→S0)
   - Compute ΔA/ΔE from state/flag/transition tables
3. Apply timeframe weights (macro=0.50, meso=0.40, micro=0.10)
4. Apply execution timeframe multipliers (based on trading timeframe)
5. Apply driver weights (BTC=1.0, ALT=1.5, BUCKET=3.0, BTC.d=-1.0, USDT.d=-3.0)
6. Sum all contributions

**State Delta Tables**:

| State | ΔA_base | ΔE_base | Meaning |
|-------|---------|---------|---------|
| S0    | -0.30   | +0.30   | Downtrend/bad - strong risk-off |
| S1    | +0.25   | -0.15   | Early uptrend - best asymmetry |
| S2    | +0.10   | +0.05   | No man's land - cautious |
| S3    | +0.20   | -0.05   | Confirmed uptrend - good environment |

**Flag Delta Tables**:

| State + Flag | ΔA_flag | ΔE_flag | Meaning |
|--------------|---------|---------|---------|
| S1 + buy_signal | +0.20 | -0.10 | Strong "go" signal |
| S2 + trim_flag | -0.20 | +0.25 | Respect trims in no man's land |
| S3 + trim_flag | -0.25 | +0.30 | Biggest harvest (S3 extension) |
| S3 + first_dip_buy_flag | +0.15 | -0.10 | First dip buy in S3 |

**Transition Delta Tables** (Emergency Exits):

| Transition | ΔA_trans | ΔE_trans | Meaning |
|-----------|----------|----------|---------|
| S1 → S0 | -0.40 | +0.40 | Early uptrend failure |
| S2 → S0 | -0.35 | +0.35 | No man's land collapse |
| S3 → S0 | -0.50 | +0.50 | Confirmed trend nuked (biggest risk-off) |

**Driver Weights**:

| Driver | Weight | Notes |
|--------|--------|-------|
| BTC | 1.0 | Weakest positive driver |
| ALT | 1.5 | Stronger alt environment indicator |
| BUCKET | 3.0 | Strongest local signal (most predictive) |
| BTC.d | -1.0 | Inverted (BTC dominance up = alts suffer) |
| USDT.d | -3.0 | Strong inverted (USDT dominance up = risk-off) |

**Timeframe Weights**:

| Timeframe | Weight | Notes |
|-----------|--------|-------|
| Macro (1d) | 0.50 | Slowest, strongest influence |
| Meso (1h) | 0.40 | Main operational timeframe |
| Micro (1m) | 0.10 | Tactical adjustments |

**Execution Timeframe Multipliers**:

| Exec TF | Macro | Meso | Micro |
|---------|-------|------|-------|
| 1m | 0.05 | 0.35 | 0.60 |
| 5m | 0.10 | 0.50 | 0.40 |
| 15m | 0.15 | 0.55 | 0.30 |
| 1h | 0.30 | 0.55 | 0.15 |
| 4h | 0.55 | 0.40 | 0.05 |
| 1d | 0.80 | 0.18 | 0.02 |

**Example Calculation**:

For a token in nano bucket, trading on 1h timeframe:

```
A_regime = 0.5  # Base
E_regime = 0.5  # Base

# BTC macro S3 (confirmed uptrend)
ΔA = +0.20, ΔE = -0.05
Weight = 1.0 (BTC) × 0.50 (macro) × 0.30 (1h exec TF) = 0.15
A_regime += 0.20 × 0.15 = 0.03
E_regime += -0.05 × 0.15 = -0.0075

# ALT meso S1 + buy_signal
ΔA = +0.25 + 0.20 = +0.45, ΔE = -0.15 + (-0.10) = -0.25
Weight = 1.5 (ALT) × 0.40 (meso) × 0.55 (1h exec TF) = 0.33
A_regime += 0.45 × 0.33 = 0.1485
E_regime += -0.25 × 0.33 = -0.0825

# Nano bucket meso S3 + trim_flag
ΔA = +0.20 + (-0.25) = -0.05, ΔE = -0.05 + 0.30 = +0.25
Weight = 3.0 (BUCKET) × 0.40 (meso) × 0.55 (1h exec TF) = 0.66
A_regime += -0.05 × 0.66 = -0.033
E_regime += 0.25 × 0.66 = 0.165

# USDT.d macro S1 (uptrend in stables = risk-off)
ΔA = +0.25, ΔE = -0.15
Weight = -3.0 (USDT.d inverted) × 0.50 (macro) × 0.30 (1h exec TF) = -0.45
# Inverted: positive state → negative effect
A_regime += 0.25 × (-0.45) = -0.1125
E_regime += -0.15 × (-0.45) = +0.0675

# Final regime scores
A_regime = 0.5 + 0.03 + 0.1485 - 0.033 - 0.1125 = 0.535
E_regime = 0.5 - 0.0075 - 0.0825 + 0.165 + 0.0675 = 0.6425
```

### Step 3: Compute Intent Deltas

**Component**: `compute_levers()` in `pm/levers.py`

**Formula**:
```python
intent_delta_a = (
    0.25 * hi_buy +
    0.15 * med_buy -
    0.15 * profit -
    0.25 * sell -
    0.30 * mock
)

intent_delta_e = (
    -0.10 * hi_buy -
    0.05 * med_buy +
    0.15 * profit +
    0.35 * sell +
    0.50 * mock
)
```

**Capping**: Intent deltas are capped at ±0.4 per original design

### Step 4: Apply Bucket Multiplier

**Component**: `_compute_bucket_multiplier()` in `pm/levers.py`

**Process**:
1. Get bucket phase, rank, slope, confidence from bucket context
2. Compute multiplier based on rank adjustments and slope weight
3. Clamp to [min_multiplier, max_multiplier] (typically [0.7, 1.3])

**Formula**:
```python
multiplier = 1.0
if confidence >= min_confidence:
    multiplier += rank_adjustment
    multiplier += slope_weight * slope
multiplier = clamp(multiplier, min_mult, max_mult)
```

**Application**:
```python
A_final = clamp(A_regime * bucket_multiplier, 0.0, 1.0)
E_final = clamp(E_regime / max(bucket_multiplier, 0.2), 0.0, 1.0)
```

### Step 5: Compute Position Sizing

**Component**: `_compute_position_sizing()` in `pm/levers.py`

**Formula**:
```python
# Linear interpolation: A=0.0 → 10%, A=1.0 → 60%
position_size_frac = 0.10 + (A_final * 0.50)
```

**Example**:
- A_final = 0.65 → position_size_frac = 0.10 + (0.65 × 0.50) = 0.425 = 42.5% of portfolio

## 2.4 Integration Points

### Called From

**PM Core Tick** (`pm_core_tick.py`):
- Calls `compute_levers()` for every position
- Uses A/E to determine:
  - Position sizing
  - Entry/exit gates
  - Trim logic

### Uses

**Uptrend Engine V4**:
- Provides S0/S1/S2/S3 states
- Provides flags (buy_signal, trim_flag, etc.)
- Provides transitions (S3→S0, etc.)

**Regime System**:
- Provides regime driver states
- Provides bucket composites
- Provides dominance data

## 2.5 Key Design Decisions

### Why Regime-Driven?

**Old System**: Phase-based (string phases like "dip", "good", "euphoria")
- Problems:
  - Subjective
  - Hard to learn from
  - Doesn't capture multi-timeframe dynamics

**New System**: Regime-driven (Uptrend Engine states)
- Benefits:
  - Objective (EMA-based state machine)
  - Learnable (states are discrete, can track performance)
  - Multi-timeframe (macro/meso/micro)
  - Multi-driver (BTC/ALT/bucket/dominance)

### Why 5 Drivers × 3 Timeframes?

**15 regime channels** per token provides:
- Global context (BTC, ALT)
- Local context (bucket)
- Risk-off signals (BTC.d, USDT.d)
- Multi-timeframe perspective (macro/meso/micro)

### Why Driver Weights?

**Hierarchy of Influence**:
- Bucket (3.0×): Most predictive locally
- ALT (1.5×): Strong alt environment indicator
- BTC (1.0×): General crypto regime
- USDT.d (-3.0×): Strongest risk-off signal
- BTC.d (-1.0×): Moderate risk-off signal

### Why Execution Timeframe Multipliers?

**Adaptive Regime Sensitivity**:
- 1m trading: Micro regime matters most (60%)
- 1h trading: Meso regime matters most (55%)
- 1d trading: Macro regime matters most (80%)

This ensures regime signals are weighted appropriately for the trading timeframe.

---

# 3. Regime and Market System Deep Dive

## 3.1 Core Concept

The regime system is a **market regime detection and A/E scoring system** that replaces the old phase-based approach. It uses **Uptrend Engine states** (S0/S1/S2/S3) from multiple market drivers to compute Aggressiveness (A) and Exitness (E) scores.

### What is a Regime?

A **regime** is the current market state as detected by the Uptrend Engine across multiple drivers and timeframes. It's not a single value—it's a **15-channel system** (5 drivers × 3 timeframes) that provides a comprehensive view of market conditions.

## 3.2 System Architecture

The regime system consists of **4 main components**:

### Component 1: Regime Price Collector

**File**: `regime_price_collector.py`

**Purpose**: Collects OHLC data for all regime drivers

**What it does**:
1. **BTC**: Reads from `majors_price_data_ohlc` (written by Hyperliquid WS or Binance backfill)
2. **ALT**: Computes composite from SOL/ETH/BNB/HYPE in `majors_price_data_ohlc`
3. **Buckets**: Computes composites from tokens in each bucket (reads from `lowcap_price_data_ohlc`)
4. **Dominance**: Fetches BTC.d and USDT.d from CoinGecko API (1m only, then rolls up to 1h/1d)

**Output**: Writes to `regime_price_data_ohlc` table

**Schedule**:
- 1m: Every minute (via `run_trade.py`)
- 1h: Every hour (via `run_trade.py`)
- 1d: Daily (via `run_trade.py`)

**Data Structure**:
```sql
CREATE TABLE regime_price_data_ohlc (
    driver TEXT NOT NULL,              -- 'BTC', 'ALT', 'nano', 'small', 'mid', 'big', 'BTC.d', 'USDT.d'
    timeframe TEXT NOT NULL,           -- '1m', '1h', '1d'
    timestamp TIMESTAMPTZ NOT NULL,
    book_id TEXT NOT NULL DEFAULT 'onchain_crypto',
    open_usd NUMERIC NOT NULL,
    high_usd NUMERIC NOT NULL,
    low_usd NUMERIC NOT NULL,
    close_usd NUMERIC NOT NULL,
    volume NUMERIC NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'binance',  -- 'binance', 'composite', 'coingecko'
    component_count INT,                      -- Number of tokens in composite
    PRIMARY KEY (driver, book_id, timeframe, timestamp)
);
```

### Component 2: Regime TA Tracker

**File**: `regime_ta_tracker.py`

**Purpose**: Computes technical analysis indicators for regime drivers

**What it does**:
1. Reads OHLC from `regime_price_data_ohlc`
2. Computes EMAs (20, 30, 50, 60, 144, 250, 333), slopes, ATR, ADX, RSI, separations
3. Writes TA data to `lowcap_positions` table (status='regime_driver')

**Output**: Updates `features.ta` in regime driver positions

**Schedule**: Runs after price collection (via `regime_runner.py`)

**Data Structure**:
```json
{
  "token_contract": "regime_btc",
  "token_chain": "regime",
  "token_ticker": "BTC",
  "timeframe": "1d",
  "status": "regime_driver",
  "features": {
    "ta": {
      "ema20": 45230.50,
      "ema30": 45120.30,
      "ema60": 44980.10,
      "ema144": 44800.20,
      "ema250": 44650.40,
      "ema333": 44500.60,
      "slopes": {...},
      "atr": 1250.30,
      "adx": 28.5,
      "rsi": 62.3
    }
  }
}
```

### Component 3: Uptrend Engine V4

**File**: `uptrend_engine_v4.py`

**Purpose**: Computes S0/S1/S2/S3 states and flags for regime drivers

**What it does**:
1. Reads TA data from regime driver positions
2. Runs Uptrend Engine state machine
3. Computes states (S0/S1/S2/S3), flags (buy, trim, rebuy), transitions
4. Writes to `features.uptrend_engine_v4` in regime driver positions

**Output**: Updates `features.uptrend_engine_v4` in regime driver positions

**Schedule**: Runs after TA tracker (via `regime_runner.py`)

**State Machine**:

```
S0 (Pure Downtrend)
  ↓
S1 (Primer) → Buy Signal (direct, no S2 state)
  ↓
S2 (Defensive - price > EMA333)
  ↓
S3 (Trending - full bullish alignment)
```

**State Definitions**:

- **S0**: Pure Downtrend
  - Perfect bearish EMA order
  - EMA20 < EMA60 AND EMA30 < EMA60 (fast band below mid)
  - EMA60 < EMA144 < EMA250 < EMA333 (slow descending)
  - Transition to S1: fast_band_above_60 AND price > EMA60

- **S1**: Primer (Early Uptrend)
  - Fast band above EMA60, price above EMA60
  - Best asymmetry zone
  - Buy signals fire directly from S1

- **S2**: Defensive Regime
  - Price > EMA333 but not full alignment
  - "No man's land" - not confirmed, not cheap
  - Respect trim flags strongly

- **S3**: Full Uptrend
  - Strong alignment: EMA20 > EMA60, EMA30 > EMA60, EMA60 > EMA144 > EMA250 > EMA333
  - Confirmed trend
  - Trim/reload cycles happen here

**Data Structure**:
```json
{
  "features": {
    "uptrend_engine_v4": {
      "state": "S3",
      "buy_signal": false,
      "buy_flag": false,
      "trim_flag": true,
      "first_dip_buy_flag": false,
      "emergency_exit": false,
      "prev_state": "S2",
      "scores": {
        "ts": 0.72,
        "ox": 0.68,
        "dx": 0.55,
        "edx": 0.42
      }
    }
  }
}
```

### Component 4: Regime A/E Calculator

**File**: `regime_ae_calculator.py`

**Purpose**: Computes final A/E scores from regime states

**What it does**:
1. Reads regime driver states from `lowcap_positions` (status='regime_driver')
2. Applies state/flag/transition delta tables
3. Applies driver weights and timeframe multipliers
4. Sums contributions across all drivers/timeframes
5. Adds intent deltas (capped at ±0.4)
6. Returns final A/E scores

**Output**: Used by `compute_levers()` in `pm/levers.py`

**Schedule**: Called on-demand when `compute_levers()` is invoked

## 3.3 Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Price Collection (regime_price_collector.py)             │
│    - Collects BTC from majors_price_data_ohlc               │
│    - Computes ALT composite from SOL/ETH/BNB/HYPE           │
│    - Computes bucket composites from lowcap_price_data_ohlc │
│    - Fetches dominance from CoinGecko                        │
│    └─> Writes to regime_price_data_ohlc                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. TA Computation (regime_ta_tracker.py)                     │
│    - Reads OHLC from regime_price_data_ohlc                  │
│    - Computes EMAs, slopes, ATR, ADX, RSI                    │
│    └─> Updates features.ta in lowcap_positions               │
│        (status='regime_driver')                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Uptrend Engine (uptrend_engine_v4.py)                    │
│    - Reads TA from regime driver positions                   │
│    - Computes S0/S1/S2/S3 states                            │
│    - Computes flags (buy, trim, rebuy)                      │
│    - Detects transitions (S3→S0, etc.)                      │
│    └─> Updates features.uptrend_engine_v4                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. A/E Calculation (regime_ae_calculator.py)                 │
│    - Reads states from regime driver positions               │
│    - Applies delta tables (state/flags/transitions)           │
│    - Applies driver weights (BTC=1.0, ALT=1.5, etc.)        │
│    - Applies timeframe multipliers                          │
│    - Sums contributions                                      │
│    - Adds intent deltas                                      │
│    └─> Returns (A, E) scores                                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Usage (pm/levers.py -> compute_levers())                 │
│    - Called for each token in PM Core Tick                  │
│    - Uses A/E to determine position sizing and exit logic    │
└─────────────────────────────────────────────────────────────┘
```

## 3.4 Regime Drivers

### Driver 1: BTC (Bitcoin Trend)

**Affects**: All tokens (global driver)

**Weight**: 1.0 (weakest positive driver)

**Purpose**: Sets general crypto regime

**Data Source**: `majors_price_data_ohlc` (BTC/USD)

### Driver 2: ALT (Altcoin Composite)

**Affects**: All tokens (global driver)

**Weight**: 1.5 (stronger alt environment indicator)

**Purpose**: Shows real alt-cycle strength

**Data Source**: Composite of SOL/ETH/BNB/HYPE from `majors_price_data_ohlc`

**Calculation**:
```python
# Equal-weighted average of SOL, ETH, BNB, HYPE
alt_composite = (SOL_price + ETH_price + BNB_price + HYPE_price) / 4
```

### Driver 3: BUCKET (Market Cap Bucket Composite)

**Affects**: Only tokens in that bucket (local driver)

**Weight**: 3.0 (strongest positive driver, most predictive locally)

**Purpose**: Most predictive signal for tokens in that bucket

**Data Source**: Composite of tokens in bucket from `lowcap_price_data_ohlc`

**Buckets**: nano, small, mid, big

**Calculation**:
```python
# Equal-weighted average of all tokens in bucket
bucket_composite = mean([token_price for token in bucket])
```

### Driver 4: BTC.d (BTC Dominance)

**Affects**: All tokens (global driver, inverted)

**Weight**: -1.0 (negative - uptrend = risk-off for alts)

**Purpose**: Detects capital rotation to BTC (bad for alts)

**Data Source**: CoinGecko API (BTC dominance %)

**Inversion**: When BTC.d trends up (S1/S2/S3), it means:
- Capital rotating to BTC
- Alts suffering
- A↓, E↑ (risk-off)

### Driver 5: USDT.d (USDT Dominance)

**Affects**: All tokens (global driver, inverted, strongest)

**Weight**: -3.0 (strongest risk-off driver)

**Purpose**: Detects flight to safety (cash inflow)

**Data Source**: CoinGecko API (USDT dominance %)

**Inversion**: When USDT.d trends up (S1/S2/S3), it means:
- Capital flowing to stablecoins
- Strong risk-off
- A↓↓↓, E↑↑↑ (strongest risk-off signal)

## 3.5 Timeframe Structure

### Macro (1d)

**Weight**: 0.50 (strongest influence)

**Purpose**: Slow shifts, big picture

**Interpretation**: Sets background climate

**Example**: Macro BTC S3 → fundamentally bullish environment

### Meso (1h)

**Weight**: 0.40 (main operational timeframe)

**Purpose**: Main operational timeframe

**Interpretation**: Drives the "breathing" of the system

**Example**: Meso ALT S1 + buy_signal → strong alt environment

### Micro (1m)

**Weight**: 0.10 (tactical adjustments)

**Purpose**: Tactical adjustments

**Interpretation**: Should never dominate A/E

**Example**: Micro bucket S2 trim_flag → short-term caution

## 3.6 State/Flag/Transition System

### States

| State | Meaning | A Effect | E Effect |
|-------|---------|----------|----------|
| S0 | Downtrend/bad | ↓↓ | ↑↑ |
| S1 | Early uptrend/best asymmetry | ↑↑ | ↓ |
| S2 | No man's land | ↓ (vs S1) | ↑ (vs S1) |
| S3 | Confirmed uptrend | ↑ | ↓ (slight) |

### Flags

| Flag | State | A Effect | E Effect | Meaning |
|------|-------|----------|----------|---------|
| buy_signal | S1 | ↑↑ | ↓ | Strong "go" signal |
| trim_flag | S2 | ↓ | ↑↑ | Respect trims in no man's land |
| trim_flag | S3 | ↓↓ | ↑↑↑ | Biggest harvest (S3 extension) |
| first_dip_buy_flag | S3 | ↑ | ↓ | First dip buy in S3 |

### Transitions (Emergency Exits)

| Transition | A Effect | E Effect | Meaning |
|------------|----------|----------|---------|
| S3→S0 | ↓↓↓ | ↑↑↑ | Nuclear event - trend broke hard |
| S2→S0 | ↓↓ | ↑↑ | Risk-off pulse |
| S1→S0 | ↓ | ↑ | Early failure |

## 3.7 Integration with Uptrend Engine

The regime system **depends entirely on Uptrend Engine V4** for state detection. The Uptrend Engine:

1. **Detects States**: S0/S1/S2/S3 based on EMA structure
2. **Computes Flags**: buy_signal, trim_flag, first_dip_buy_flag
3. **Detects Transitions**: S3→S0, S2→S0, S1→S0
4. **Computes Scores**: TS, OX, DX, EDX

The regime system then:
1. **Reads States**: From `features.uptrend_engine_v4` in regime driver positions
2. **Maps to A/E**: Uses state/flag/transition delta tables
3. **Applies Weights**: Driver weights and timeframe multipliers
4. **Sums Contributions**: Across all drivers/timeframes

## 3.8 Market System Connection

The **market system** is the broader context that the regime system operates within. It includes:

1. **Price Data Collection**: 
   - Majors (BTC, SOL, ETH, BNB, HYPE) → `majors_price_data_ohlc`
   - Lowcaps → `lowcap_price_data_ohlc`
   - Dominance → CoinGecko API

2. **TA Computation**:
   - EMAs, slopes, ATR, ADX, RSI
   - Stored in `features.ta` for all positions

3. **Uptrend Engine**:
   - Runs on all positions (including regime drivers)
   - Computes states, flags, transitions
   - Stored in `features.uptrend_engine_v4`

4. **Regime System**:
   - Uses Uptrend Engine outputs for regime drivers
   - Computes A/E scores
   - Feeds into Portfolio Manager

The regime system is **part of the market system**, not separate from it. It's the layer that:
- Aggregates market signals (BTC, ALT, bucket, dominance)
- Converts them to actionable A/E scores
- Feeds them into decision-making

---

# 4. System Interconnections

## 4.1 How Learning System Connects to A/E System

### Connection Point 1: Regime States in Learning Scope

**What**: Learning system tracks regime states as part of pattern scope

**How**:
- When a position closes, `pattern_scope_aggregator.py` extracts regime states from `entry_context`
- Regime states are stored in `pattern_trade_events.scope` as:
  - `btc_macro`, `btc_meso`, `btc_micro`
  - `alt_macro`, `alt_meso`, `alt_micro`
  - `bucket_macro`, `bucket_meso`, `bucket_micro`
  - `btcd_macro`, `btcd_meso`, `btcd_micro`
  - `usdtd_macro`, `usdtd_meso`, `usdtd_micro`

**Why**: Allows learning system to discover patterns like "S1 entries in nano bucket during BTC macro S3 show 2.3× R/R"

**Example**:
```json
{
  "pattern_key": "pm.uptrend.S1.buy_flag",
  "action_category": "entry",
  "scope": {
    "btc_macro": "S3",
    "btc_meso": "S1",
    "alt_meso": "S1",
    "bucket_meso": "S1",
    "mcap_bucket": "nano",
    "chain": "solana"
  },
  "rr": 2.3
}
```

### Connection Point 2: Regime-Specific Learning

**What**: Learning system learns regime-specific weights

**How**:
- `regime_weight_learner.py` groups patterns by regime signature
- Learns which meta-factors (time_efficiency, field_coherence, recurrence, variance) matter in which regimes
- Stores in `learning_regime_weights` table

**Why**: Different patterns work better in different regimes. For example:
- High volatility regime: time_efficiency matters more
- Narrative-driven regime: field_coherence matters less (micros vs majors diverge)

**Example**:
```json
{
  "pattern_key": "pm.uptrend.S1.buy_flag",
  "action_category": "entry",
  "regime_signature": "macro=S3|meso=S1|bucket_rank=1",
  "weights": {
    "time_efficiency": 0.8,
    "field_coherence": 0.3,
    "recurrence": 0.5,
    "variance": 0.7
  }
}
```

### Connection Point 3: A/E Values in Learning Scope

**What**: Learning system tracks A/E values at entry

**How**:
- `pattern_scope_aggregator.py` extracts A/E values from `entry_context`
- Stored in `pattern_trade_events.scope` as `A_mode` and `E_mode` (discretized)

**Why**: Allows learning system to discover patterns like "High A (0.7+) entries in S1 show better R/R"

**Example**:
```json
{
  "scope": {
    "A_mode": "high",  # Discretized from A_value = 0.72
    "E_mode": "low",   # Discretized from E_value = 0.35
    "btc_meso": "S1"
  }
}
```

## 4.2 How Learning System Connects to Regime System

### Connection Point 1: Regime States Feed Learning

**What**: Regime system provides states that learning system tracks

**How**:
- Regime system computes states (S0/S1/S2/S3) for all regime drivers
- These states are stored in `lowcap_positions.features.uptrend_engine_v4` for regime drivers
- When a position closes, PM Core Tick reads these states and includes them in `entry_context`
- Learning system extracts these states and stores them in pattern scope

**Why**: Learning system needs to know what regime conditions led to good/bad outcomes

### Connection Point 2: Learning System Could Adjust Regime Weights (Future)

**What**: Learning system could learn optimal driver weights and timeframe multipliers

**How** (not yet implemented):
- Track R/R outcomes by regime driver contribution
- Learn which drivers are more predictive in which conditions
- Adjust driver weights dynamically

**Why**: Current weights are fixed (BTC=1.0, ALT=1.5, BUCKET=3.0, etc.), but they could be learned

## 4.3 How A/E System Connects to Regime System

### Connection Point 1: Regime System Computes A/E

**What**: Regime system is the primary driver of A/E scores

**How**:
- `RegimeAECalculator.compute_ae_for_token()` reads regime driver states
- Applies state/flag/transition delta tables
- Applies driver weights and timeframe multipliers
- Returns regime-based A/E scores

**Why**: A/E system is regime-driven, not phase-driven

### Connection Point 2: A/E System Uses Uptrend Engine

**What**: A/E system depends on Uptrend Engine for state detection

**How**:
- Uptrend Engine runs on regime drivers (BTC, ALT, bucket, BTC.d, USDT.d)
- Computes states (S0/S1/S2/S3), flags, transitions
- Stores in `features.uptrend_engine_v4`
- A/E calculator reads these states

**Why**: Uptrend Engine provides objective, learnable state detection

### Connection Point 3: A/E Values Feed Back into Learning

**What**: A/E values at entry are tracked by learning system

**How**:
- When position closes, `entry_context` includes A/E values
- Learning system extracts these and stores in pattern scope
- Can discover patterns like "High A entries in S1 show better R/R"

**Why**: Creates feedback loop: A/E affects decisions → decisions create outcomes → outcomes inform learning → learning could adjust A/E (future)

## 4.4 Complete Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ MARKET SYSTEM                                                │
│ - Price data collection (majors, lowcaps, dominance)      │
│ - TA computation (EMAs, slopes, ATR, ADX, RSI)             │
│ - Uptrend Engine (state detection for all positions)       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ REGIME SYSTEM                                                │
│ - Regime price collector (BTC, ALT, bucket, dominance)     │
│ - Regime TA tracker (TA for regime drivers)                │
│ - Uptrend Engine (states for regime drivers)               │
│ - Regime A/E calculator (A/E from regime states)           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ A/E SYSTEM                                                    │
│ - compute_levers() (combines regime A/E + intent + bucket)  │
│ - Position sizing (derived from A)                         │
│ - Entry/exit gates (derived from A/E)                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ PORTFOLIO MANAGER                                             │
│ - Makes trading decisions using A/E                         │
│ - Creates positions, adds, trims, exits                     │
│ - Tracks outcomes (R/R, PnL)                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ LEARNING SYSTEM                                              │
│ - Processes position_closed strands                         │
│ - Extracts regime states, A/E values, outcomes              │
│ - Mines patterns (pattern_trade_events → learning_lessons)   │
│ - Creates overrides (pm_overrides)                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ FEEDBACK LOOP                                                 │
│ - Overrides adjust position sizing                          │
│ - (Future: Could adjust regime weights, A/E deltas)         │
└─────────────────────────────────────────────────────────────┘
```

## 4.5 Key Integration Points

### 1. Position Closure → Learning

**Trigger**: Position closes

**Flow**:
1. PM Core Tick creates `position_closed` strand
2. Includes `entry_context` with:
   - Regime states (15 channels)
   - A/E values
   - Pattern key, scope, timeframe
3. UniversalLearningSystem processes strand
4. Three parallel paths:
   - Coefficient updates (timeframe weights)
   - Pattern scope aggregation (pattern_trade_events)
   - LLM research layer (hypotheses)

### 2. Regime States → A/E

**Trigger**: Every PM Core Tick (for each position)

**Flow**:
1. `compute_levers()` called
2. `RegimeAECalculator.compute_ae_for_token()` reads regime driver states
3. Applies state/flag/transition deltas
4. Applies weights and multipliers
5. Returns regime-based A/E
6. Adds intent deltas
7. Applies bucket multiplier
8. Returns final A/E

### 3. Learning → Overrides

**Trigger**: Periodic (every 2 hours)

**Flow**:
1. Override Materializer reads `learning_lessons`
2. Filters for actionable edges
3. Creates `pm_overrides` with:
   - `size_multiplier` (adjusts position sizing)
   - `threshold_adjustments` (adjusts entry/exit gates)
4. PM Executor reads overrides at runtime
5. Applies to decisions

### 4. Regime States → Learning Scope

**Trigger**: Position closure

**Flow**:
1. PM Core Tick reads regime states from `lowcap_positions`
2. Includes in `entry_context.regime_states`
3. Pattern Scope Aggregator extracts regime states
4. Stores in `pattern_trade_events.scope` (15 regime dimensions)
5. Lesson Builder groups by regime signature
6. Learns regime-specific patterns

## 4.6 Future Integration Possibilities

### 1. Learned Regime Weights

**Current**: Fixed driver weights (BTC=1.0, ALT=1.5, BUCKET=3.0, etc.)

**Future**: Learn optimal weights from outcomes
- Track R/R by driver contribution
- Adjust weights dynamically
- Store in `learning_configs`

### 2. Learned A/E Deltas

**Current**: Fixed state/flag/transition delta tables

**Future**: Learn optimal deltas from outcomes
- Track R/R by state/flag combinations
- Adjust deltas dynamically
- Store in `learning_configs`

### 3. Regime-Aware Overrides

**Current**: Overrides are pattern+scope based

**Future**: Overrides could be regime-aware
- Different overrides for different regimes
- Example: "S1 entries in nano bucket during BTC macro S3: +20% size"

---

# Summary

## Learning Systems

- **Architecture**: Three-layer (Event Collection, Pattern Mining, Lesson Application)
- **Philosophy**: Outcome-first exploration (learn from what worked, not signals)
- **Three Paths**: Coefficient updates, pattern scope aggregation, LLM research
- **Output**: Overrides that adjust position sizing and thresholds

## A/E System

- **Architecture**: Regime-driven (replaces phase-based)
- **Inputs**: 15 regime channels (5 drivers × 3 timeframes) + intent + bucket
- **Calculation**: State/flag/transition deltas → weights/multipliers → sum → clamp
- **Output**: A/E scores [0, 1] → position sizing, entry/exit gates

## Regime and Market System

- **Architecture**: 4 components (Price Collector, TA Tracker, Uptrend Engine, A/E Calculator)
- **Drivers**: BTC, ALT, BUCKET, BTC.d, USDT.d (5 drivers × 3 timeframes = 15 channels)
- **States**: S0 (downtrend), S1 (early uptrend), S2 (no man's land), S3 (confirmed uptrend)
- **Output**: Regime-based A/E scores

## Interconnections

- **Learning → A/E**: Regime states tracked in learning scope, A/E values tracked in learning scope
- **Regime → A/E**: Regime system computes A/E scores
- **A/E → Learning**: A/E values at entry feed into learning system
- **Learning → Regime**: (Future) Could learn optimal regime weights and deltas

All three systems work together to create a self-improving trading system that adapts to market conditions and learns from outcomes.

