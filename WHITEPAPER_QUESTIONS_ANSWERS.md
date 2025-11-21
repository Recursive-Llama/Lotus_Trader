# Whitepaper Questions - Answers from Codebase

**Status**: Assessment of what information exists in the codebase vs. what's missing for a complete whitepaper.

---

## ✅ **1. FORMAL DEFINITIONS - What EXISTS in Codebase**

### **1.1 Trend Behaviour** ✅ **FULLY DOCUMENTED**

**Trend States (S0/S1/S2/S3)**:
- **S0 (Pure Downtrend)**: Perfect bearish EMA order
  - `EMA20 < EMA60 AND EMA30 < EMA60` (fast band below mid)
  - `EMA60 < EMA144 < EMA250 < EMA333` (slow descending)
  - Source: `docs/trencher_improvements/PM/v4_uptrend/v4_upgrades_implementation/UPTREND_ENGINE_V4_SPEC.md:115-143`

- **S1 (Primer)**: Fast band above EMA60, price above EMA60
  - Entry: `EMA20 > EMA60 AND EMA30 > EMA60 AND Price > EMA60`
  - Source: Same spec, lines 147-166

- **S2 (Defensive)**: Price above EMA333, not yet full alignment
  - Source: Same spec, lines 100-109

- **S3 (Trending)**: Full bullish alignment - all EMAs above EMA333
  - Source: Same spec, lines 102-103

**State Transitions**: Fully documented in multiple spec files
- S0→S1: `fast_band_above_60 AND price > EMA60`
- S1→S2: `price > EMA333`
- S2→S3: All EMAs above EMA333
- Global Exit: `fast_band_at_bottom` (overrides all states)

**Reclaim Definition**: ✅ **FOUND**
- `reclaimed_ema333`: Price transitions from < EMA333 to >= EMA333 (in S3)
- Source: `src/intelligence/lowcap_portfolio_manager/jobs/uptrend_engine_v4.py:1636-1642`

**Exhaustion Definition**: ✅ **FOUND**
- Exhaustion signal: `sigmoid(-vo_z_1h / 1.0)` where `vo_z_1h` is volume Z-score
- Used in DX calculation: `0.25 * exhaustion`
- Source: `src/intelligence/lowcap_portfolio_manager/jobs/uptrend_engine_v4.py:1183`

### **1.2 Behavioural Features** ✅ **MOSTLY DOCUMENTED**

**TS (Trend Strength)**:
- Formula: `0.6 * sigmoid(rsi_slope_10, k=0.5) + 0.4 * sigmoid(adx_slope_10, k=0.3) if adx >= 18 else 0.0`
- Source: `docs/trencher_improvements/PM/v4_uptrend/v4_upgrades_implementation/UPTREND_ENGINE_V4_SPEC.md:369-374`

**OX (Overextension)**:
- Components: Rail scores (distance from EMAs), expansion, ATR surge, fragility
- Formula: Weighted sum with EDX boost in S3
- Source: `docs/trencher_improvements/PM/v6_uptrend/UPTREND_ENGINE_V6_SPEC.md:137-156`

**DX (Deep Zone)**:
- Formula: `exp(-3.0 * x)` where `x = (price - EMA333) / (EMA144 - EMA333)`
- Components: Location, compression multiplier, exhaustion, relief, curl
- Source: `docs/trencher_improvements/PM/v6_uptrend/UPTREND_ENGINE_V6_SPEC.md:160-165`

**EDX (Expansion Decay Index)**:
- 3-window S3-relative approach:
  1. Slow-Field Momentum (30%): EMA250/333 slopes, RSI trend, ADX trend
  2. Structure Failure (25%): ZigZag HH/HL ratio
  3. Participation Decay (20%): AVWAP slope
  4. EMA Structure Compression (10%): EMA144-333, EMA250-333 separations
- Source: `src/intelligence/lowcap_portfolio_manager/jobs/uptrend_engine_v4.py:676-980`

**Time Efficiency**: ✅ **FOUND**
- Definition: `time_efficiency = 1.0 / (1.0 + max(avg_time_to_payback_days, 0.0))`
- Time to payback: Days from first meaningful allocation to first +1R touch
- Source: `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py:393`

**Field Coherence**: ✅ **FOUND**
- Definition: `field_coherence = segments_positive / segments_tested`
- Measures pattern consistency across market segments (mcap_bucket × timeframe)
- Source: `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py:163-220`

**Recurrence**: ✅ **FOUND**
- Formula: Exponential moving average of edge_raw
  - `alpha = 1.0 - exp(-delta_days / tau_days)` where `tau_days = 30.0`
  - `recurrence_new = alpha * edge_raw + (1 - alpha) * previous`
- Source: `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py:305-318`

**Emergence**: ✅ **FOUND**
- Formula: `(incremental_edge / (1.0 + variance)) * (1.0 / sqrt(max(n, 3)))`
- Detects new patterns with high signal-to-noise ratio
- Source: `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py:321-327`

**A-mode / E-mode (Add/Exit Appetite)**: ✅ **FOUND**
- **A (Add Appetite)**: Continuous 0-1 score
  - Components: Meso phase policy, macro adjustment, cut pressure, intent deltas, age boost, mcap boost, bucket multiplier
  - Formula: `a_final = clamp(a_base * a_boost * bucket_multiplier, 0.0, 1.0)`
  - Source: `src/intelligence/lowcap_portfolio_manager/pm/levers.py:215-272`

- **E (Exit Assertiveness)**: Continuous 0-1 score
  - Similar structure to A, with inverse logic for exits
  - Source: Same file

**Volatility Normalization**: ✅ **FOUND (via ATR)**
- ATR is used extensively to normalize price distances
- Examples: "price within 1×ATR of EMA60", "0.5×ATR of EMA333", "price within 1×ATR of S/R level"
- This IS volatility normalization - distances measured in ATR units rather than absolute price
- Source: `src/intelligence/lowcap_portfolio_manager/jobs/uptrend_engine_v4.py` (multiple uses of ATR for distance normalization)

**Counterfactual Logic**: ✅ **FULLY IMPLEMENTED**
- Computes `missed_entry_rr` and `missed_exit_rr` (lines 992-993)
- Creates `could_enter_better` and `could_exit_better` objects (lines 999-1008)
- Buckets via `bucket_cf_improvement()` (lines 997-998)
- Stores in `trade_summary` (lines 1051-1052)
- Used in `lesson_builder_v5.py` to set execution levers (lines 217-242)
- Source: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py:989-1054`

### **1.3 Market Context Dimensions** ✅ **FULLY DOCUMENTED**

**Macro/Meso/Micro Phases**:
- Phases: `Good`, `Recover`, `Dip`, `Double-Dip`, `Oh-Shit`, `Euphoria`, `Chop`, `Unknown`
- Source: `docs/trencher_improvements/PM/v4_uptrend/v4_ongoing/v4_Learning/final_stages/PATTERN_KEY_SCOPE_SPEC.md:44-46`

**Cap Buckets**:
- `nano`: < $100k
- `micro`: $100k – $5m
- `mid`: $5m – $50m
- `big`: $50m – $500m
- `large`: $500m – $1b
- `xl`: > $1b
- Source: `docs/trencher_improvements/PM/v4_uptrend/v4_ongoing/v4_Learning/final_stages/CAP_BUCKET_REGIME_SPEC.md:9-16`

**Age Buckets**: ⚠️ **IMPLICIT**
- Age-based boosts exist in A/E calculation (<6h, <12h, <72h)
- But no formal "age bucket" classification found
- Source: `src/intelligence/lowcap_portfolio_manager/pm/levers.py:83-106`

**Volatility States**: ❌ **NOT FOUND**
- No explicit volatility state classification

**Market Families**: ✅ **FOUND**
- Values: `lowcaps`, `perps`, `majors`
- Source: `docs/trencher_improvements/PM/v4_uptrend/v4_ongoing/v4_Learning/final_stages/PATTERN_KEY_SCOPE_SPEC.md:49`

**Timeframes**: ✅ **FOUND**
- Values: `1m`, `15m`, `1h`, `4h`
- Source: Same spec, line 51

---

## ✅ **2. ENGINE SPECIFICATION - What EXISTS in Codebase**

### **2.1 The Universal Engine** ✅ **FULLY DOCUMENTED**

**EMA-Based Reconstruction**:
- Uses 6 EMAs: EMA20, EMA30, EMA60, EMA144, EMA250, EMA333
- Band-based order checking (fast band = EMA20/30, mid = EMA60, slow = EMA144/250/333)
- Source: Multiple spec files and `src/intelligence/lowcap_portfolio_manager/jobs/uptrend_engine_v4.py`

**State Transitions**:
- Fully documented with preconditions and invariants
- State machine diagram exists in specs
- Source: `docs/trencher_improvements/PM/v6_uptrend/UPTREND_ENGINE_V6_SPEC.md:17-23`

**Computational Complexity**: ❌ **NOT DOCUMENTED**
- No complexity analysis found

### **2.2 Momentum Signatures** ✅ **FULLY DOCUMENTED**

**TS/OX/DX/EDX**: All formulas documented (see 1.2 above)

**Inputs, Outputs, Interpretation**: ✅ **FOUND**
- Each signal has documented thresholds, ranges, and interpretation
- Source: Multiple spec files

**Failure Modes**: ⚠️ **PARTIALLY DOCUMENTED**
- Some failure modes mentioned (insufficient data, edge cases)
- But not comprehensive failure mode analysis

### **2.3 Multi-Timeframe Position System** ✅ **FULLY DOCUMENTED**

**Independent Positions**:
- Each token gets 4 independent positions (1m, 15m, 1h, 4h)
- Each has own allocation, entries, exits, PnL
- Source: `docs/trencher_improvements/PM/v4_uptrend/v4_ongoing/COMPLETE_INTEGRATION_PLAN.md:163-211`

**Why Not Multi-Timeframe Analysis**:
- Documented: Each timeframe maintains its own trend "life"
- Source: `README.md:198-211`

**Cross-Timeframe Conflict Handling**: ⚠️ **IMPLICIT**
- Positions are independent, so conflicts don't arise
- But no explicit conflict resolution documented

---

## ✅ **3. LEARNING SYSTEM - What EXISTS in Codebase**

### **3.1 Outcome Classification** ✅ **FULLY DOCUMENTED**

**R/R Calculation**:
- Formula: `rr = return_pct / max_drawdown` (if max_drawdown > 0)
- Bounded to [-10, 10]
- Source: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py:803-826`

**Drawdown Calculation**:
- `max_drawdown = (entry_price - min_price) / entry_price`
- Source: Same file, lines 800-801

**Time Efficiency**: ✅ **FOUND** (see 1.2)

**Counterfactuals**: ⚠️ **NOT IMPLEMENTED** (see 1.2)

**Global Baselines**: ✅ **FOUND**
- Segment baselines computed per (mcap_bucket, timeframe)
- Source: `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py:666-743`

### **3.2 Pattern System** ✅ **FULLY DOCUMENTED**

**Pattern Key Construction**:
- Format: `<module>.<family>.<state>.<motif>`
- Example: `pm.uptrend.S1.buy_flag`
- Source: `docs/trencher_improvements/PM/v4_uptrend/v4_ongoing/v4_Learning/final_stages/PATTERN_KEY_SCOPE_SPEC.md:19-34`

**Scope Definition**:
- 10 dimensions: macro_phase, meso_phase, micro_phase, bucket_leader, bucket_rank_position, market_family, bucket, timeframe, A_mode, E_mode
- Source: Same spec, lines 38-56

**Category Assignment**:
- Categories: `entry`, `add`, `trim`, `exit`
- Source: `src/intelligence/lowcap_portfolio_manager/pm/pattern_keys_v5.py:16-45`

**Pattern Stats Aggregation**:
- Aggregated in `pattern_scope_stats` table
- Stats include: avg_rr, variance, edge_raw, time_efficiency, field_coherence, recurrence_score
- Source: `src/database/pattern_scope_stats_schema.sql`

**Recurrence Logic**: ✅ **FOUND** (see 1.2)

**Coherence Logic**: ✅ **FOUND** (see 1.2)

### **3.3 Braid Formation** ✅ **FULLY DOCUMENTED**

**When Pattern Becomes Braid**:
- Threshold: 3+ strands of level N create braid of level N+1
- Source: `src/intelligence/system_control/central_intelligence_layer/braid_level_manager.py:32`

**How Braids Merge**:
- Clustering-based: Two-tier clustering system
- Source: `src/intelligence/universal_learning/universal_learning_system.py:122-167`

**How Braids Store Structure**:
- Dimensions stored in JSONB, stats aggregated
- Source: `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py:330-450`

**Braid Decay**: ⚠️ **PARTIALLY DOCUMENTED**
- Decay functions exist for lessons (v5.2)
- But braid-specific decay not explicitly documented

### **3.4 Lesson System** ✅ **FULLY DOCUMENTED**

**Capital Multipliers**:
- `size_mult`: 0.5-1.5 (scales position size)
- `entry_aggression_mult`: 0.7-1.3 (biases add appetite)
- `exit_aggression_mult`: 0.7-1.3 (biases exit assertiveness)
- Source: `src/intelligence/lowcap_portfolio_manager/jobs/lesson_builder_v5.py:167-211`

**Execution Levers**:
- `entry_delay_bars`, `phase1_frac_mult`, `trim_delay_mult`, `trail_mult`, `signal_thresholds`
- Source: Same file, lines 214-250

**Bounding Functions**:
- All multipliers clamped to bounds
- Learning rate: `max(-0.10, min(0.10, (edge_raw / edge_scale) * learning_rate))`
- Source: Same file, lines 188-189

**Learning Rates**:
- Default: `0.02` (2% max change per epoch)
- Edge scale: `20.0`
- Source: Same file, lines 171-172

**Decay Functions**:
- Exponential decay with half-life
- Formula: `decayed_value = apply_decay(value, lesson_strength, decay_halflife_hours, lesson_age_hours)`
- Source: `src/intelligence/lowcap_portfolio_manager/jobs/override_materializer.py:275-296`

**Reversal-to-Neutral Mechanisms**: ⚠️ **IMPLICIT**
- Decay back toward 1.0 when no fresh evidence
- But not explicitly documented

**Regime-Conditioning Logic**: ✅ **FOUND**
- Regime weights stored in `learning_regime_weights` table
- Weights adjust time_efficiency, field_coherence, recurrence multipliers per regime
- Source: `src/intelligence/lowcap_portfolio_manager/jobs/pattern_scope_aggregator.py:279-331`

---

## ✅ **4. SEPARATION OF CONCERNS - What EXISTS in Codebase**

### **4.1 What the Math Layer Controls** ✅ **FULLY DOCUMENTED**

**Authoritative Decisions**:
- All trading decisions, capital allocation, risk adjustments
- Source: `docs/trencher_improvements/PM/v4_uptrend/v4_ongoing/v4_Learning/BRAIDING_SYSTEM_DESIGN.md:688-733`

**Updates and Validations**:
- All pattern stats, edge calculations, lesson creation
- Source: Multiple implementation files

### **4.2 What the LLM Layer Does** ✅ **FULLY DOCUMENTED**

**Formal Scope Document**:
- 5 levels of LLM integration (Commentary, Semantic Features, Family Optimization, Semantic Compression, Hypothesis Generation)
- Source: `src/intelligence/lowcap_portfolio_manager/pm/llm_research_layer.py:1-188`

**Semantic Compression**: ✅ **FOUND**
- LLM extracts narrative tags, proposes groupings
- Source: Same file

**Latent Factor Identification**: ✅ **FOUND**
- LLM names latent factors, stores in `llm_learning` table
- Source: Same file

**Hypothesis Generation**: ✅ **FOUND**
- LLM proposes testable hypotheses
- Source: Same file

**Narrative Interpretation**: ✅ **FOUND**
- LLM provides commentary and interpretation
- Source: Same file

### **4.3 Safety Guarantees** ✅ **FULLY DOCUMENTED**

**LLM Cannot Execute Trades**: ✅ **DOCUMENTED**
- Architecture boundary: LLM writes to `llm_learning`, math layer reads and validates
- Source: `README.md:163` ("The Golden Rule: LLM ≠ math")

**LLM Cannot Change Mathematical Parameters**: ✅ **DOCUMENTED**
- LLM outputs are hypotheses, validated by math layer
- Source: `src/intelligence/lowcap_portfolio_manager/pm/llm_research_layer.py:33-34`

**LLM Cannot Override Signals**: ✅ **DOCUMENTED**
- LLM cannot modify A/E scores, engine signals, or trading decisions
- Source: Architecture docs

**LLM Cannot Validate Its Own Suggestions**: ✅ **DOCUMENTED**
- All LLM outputs must be validated by math layer (edge stats, baselines, significance tests)
- Source: `src/intelligence/lowcap_portfolio_manager/pm/llm_research_layer.py:33-34`

---

## ✅ **5. CROSS-MARKET UNIVERSALITY ARGUMENT - What EXISTS**

**Explicit Universality Arguments**: ✅ **FOUND**
- **Three explicit arguments** documented in README:
  1. **Human behavior is universal**: "The same greed, fear, and FOMO that drives crypto pumps also drives stock rallies"
  2. **Market dynamics are universal**: "Support/resistance, trend following, momentum - these patterns repeat across all markets"
  3. **Timeframes are similar**: "A 1-minute crypto chart and a 4-hour stock chart show the same EMA state transitions, just at different speeds"
- Source: `README.md:315-320` ("Why Universal?" section)

**Core Philosophy Statement**: ✅ **FOUND**
- "All markets, charts, and timeframes are more similar than they are different. The same human behavior and market dynamics that create trends in crypto tokens also create trends in stocks, perps, prediction markets, and any other market."
- Source: `README.md:9`

**Architectural Evidence**: ✅ **FOUND**
- System design demonstrates universality: "Works on any OHLCV data - Crypto tokens, stocks, perps, prediction markets, forex - doesn't matter"
- Multiple pipelines (lowcap, perps, prediction) share the same engine
- Source: `README.md:39, 79-84`

**Multi-Timeframe Evidence**: ✅ **FOUND**
- "The whole point is that all markets and timeframes are more similar than different. The same EMA state transitions (S0→S1→S2→S3) work on 1-minute crypto charts and 4-hour stock charts because they're driven by the same human behavior and market dynamics."
- Source: `README.md:45`

**What's Missing (for formal proof)**:
- Statistical validation across markets (empirical evidence)
- Formal mathematical proof of universality
- Liquidity absorption dynamics (mentioned but not formalized)
- Crowd-psychology invariants (mentioned but not formalized)
- Fractal properties (philosophical in Simons docs, not formalized)

---

## ⚠️ **6. EVALUATION METHODS - What EXISTS (PARTIAL)**

### **6.1 How Lotus Is Evaluated** ⚠️ **PARTIALLY DOCUMENTED**

**Edge Score (Primary Evaluation Metric)**: ✅ **FOUND**
- Edge score: `edge_raw = (avg_rr - baseline_rr) * coherence * support * multipliers`
- This is the primary evaluation metric for pattern quality
- Includes time_efficiency, field_coherence, recurrence multipliers
- Source: `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py:746-780`

**R/R Improvement**: ✅ **FOUND**
- Part of edge calculation: `delta_rr = avg_rr - baseline_rr`
- Source: Same file

**Variance Reduction**: ✅ **FOUND**
- Variance tracked in stats, used in edge calculation
- Source: Same file

**Faster Payback**: ✅ **FOUND**
- Time efficiency metric (see 1.2)

**Recurrence Rates**: ✅ **FOUND**
- Recurrence score tracked (see 1.2)

**Cross-Market Transferability**: ❌ **NOT DOCUMENTED**
- No formal cross-market validation methodology

**Long-Term Stability**: ⚠️ **PARTIALLY DOCUMENTED**
- Decay functions exist, but no long-term stability metrics

### **6.2 Real-World Constraints** ⚠️ **PARTIALLY DOCUMENTED**

**Slippage**: ❌ **NOT DOCUMENTED**

**Latency**: ❌ **NOT DOCUMENTED**

**Liquidity Gaps**: ❌ **NOT DOCUMENTED**

**Execution Failure Modes**: ⚠️ **IMPLICIT**
- Error handling exists in code, but not formally documented

### **6.3 Failure Mode Analysis** ⚠️ **IMPLICIT, NOT EXPLICITLY DOCUMENTED**

**What Failure Mode Analysis Means**: Analysis of how the system behaves when market conditions are unfavorable or when signals fail.

**Chop-Heavy Markets**: ⚠️ **IMPLICIT**
- Global exit logic handles fast band reversals (implicit chop handling)
- But no explicit "chop detection" or "chop mode" documented

**Regime Flips**: ⚠️ **IMPLICIT**
- Regime detection exists (macro/meso/micro phases)
- But no explicit "regime flip" failure mode analysis

**Liquidity Deserts**: ❌ **NOT DOCUMENTED**

**False Early Signals**: ⚠️ **IMPLICIT**
- TS gate (TS ≥ 0.58) filters weak signals
- But no explicit "false signal" analysis documented

### **6.4 Robustness Tests** ❌ **NOT DOCUMENTED**

**Multi-Market Backtests**: ❌ **NOT DOCUMENTED**

**Cross-Regime Performance Diffusion**: ❌ **NOT DOCUMENTED**

**Family Collapses & Expansions**: ❌ **NOT DOCUMENTED**

---

## ⚠️ **7. ADDITIONAL COMPONENTS - What EXISTS (PARTIAL)**

### **7.1 Glossary** ⚠️ **SCATTERED**
- Terms exist in various docs, but no unified glossary
- Would need to compile from multiple sources

### **7.2 Diagrams** ❌ **NOT FOUND**
- No state machine diagrams in codebase
- No learning flow diagrams
- No architecture diagrams
- Specs mention diagrams but they don't exist

### **7.3 Formal Rationale for Multi-Pipeline Sharing** ⚠️ **PHILOSOPHICAL**
- README mentions it, but no scientific justification
- Source: `README.md:11-19`

### **7.4 Risk Framework** ✅ **IMPLEMENTED (via multiple mechanisms)**

**Pattern Overfitting Prevention**: ✅ **FOUND**
- **N_min thresholds**: Minimum sample sizes per subset size (10-50 samples)
  - Source: `src/intelligence/lowcap_portfolio_manager/jobs/pattern_scope_aggregator.py:42-54`
- **Edge_min thresholds**: Minimum edge score required (default 0.5)
  - Source: `src/intelligence/lowcap_portfolio_manager/jobs/lesson_builder_v5.py:332`
- **Incremental edge checks**: Patterns must add value beyond parents (`incremental_edge >= incremental_min`)
  - Prevents redundant patterns that don't add information
  - Source: `src/intelligence/lowcap_portfolio_manager/pm/braiding_system.py:780-843`
- **Latent factor detection (v5.3)**: Prevents double-counting correlated patterns
  - Source: `src/database/learning_latent_factors_schema.sql`

**False Lessons Prevention**: ✅ **FOUND**
- **Decay functions**: Lessons decay toward neutral (1.0) over time
  - Exponential decay: `decayed = neutral + (value - neutral) * exp(-decay_rate * age)`
  - False lessons naturally fade away as they age
  - Source: `src/intelligence/lowcap_portfolio_manager/jobs/override_materializer.py:21-54`
- **Half-life modeling (v5.2)**: Tracks pattern decay rates, identifies short-lived patterns
  - Source: `docs/trencher_improvements/PM/v4_uptrend/v4_ongoing/v4_Learning/V4_LEARNING_ENHANCEMENTS.md:879-937`
- **Learning rate bounds**: Small learning rates (2% max per epoch) prevent overreaction
  - Source: `src/intelligence/lowcap_portfolio_manager/jobs/lesson_builder_v5.py:171-172`

**Collapsing Families**: ⚠️ **IMPLICIT**
- Family ID tracking exists, but no explicit "family collapse" detection

**Decay Miscalibration**: ⚠️ **PARTIALLY ADDRESSED**
- Decay half-lives are estimated from data (v5.2)
- But no explicit "miscalibration detection" mechanism

**Cross-Market Noise Transfer**: ⚠️ **IMPLICIT**
- Field coherence metric measures pattern consistency across segments
- But no explicit "noise transfer" prevention documented

---

## ❌ **8. THEORETICAL FOUNDATIONS - What's MISSING**

**Behavioural Finance Roots**: ❌ **NOT DOCUMENTED**

**Market Microstructure Basis**: ❌ **NOT DOCUMENTED**

**Statistical Justification of Multi-Regime Cycles**: ❌ **NOT DOCUMENTED**

**Argument for Why Trends Are Fractal**: ⚠️ **PHILOSOPHICAL ONLY**
- Mentioned in Simons docs, but not formal
- Source: `docs/ip/SIMONS_RESONANCE_INTEGRATION.md:35-43`

**Universality Theory**: ✅ **EXPLICIT ARGUMENTS EXIST**
- Three explicit arguments documented:
  1. Human behavior is universal (greed, fear, FOMO)
  2. Market dynamics are universal (support/resistance, trend following, momentum)
  3. Timeframes are similar (same EMA transitions at different speeds)
- Source: `README.md:315-320`
- **What's missing**: Formal mathematical proof and statistical validation across markets

**Hybrid Symbolic–Mathematical Learning**: ⚠️ **IMPLICIT**
- System uses both, but no formal theory

---

## ⚠️ **9. DESIGN PHILOSOPHY - What EXISTS (IMPLICIT)**

**Universality Through Constraint**: ⚠️ **IMPLICIT**
- System design shows this, but not explicitly stated

**Behaviour Over Prediction**: ⚠️ **IMPLICIT**
- Outcome-first learning shows this, but not explicitly stated

**Evidence Over Expectation**: ⚠️ **IMPLICIT**
- Pattern aggregation shows this, but not explicitly stated

**Pattern Aggregation Over Forecasting**: ⚠️ **IMPLICIT**
- Braiding system shows this, but not explicitly stated

**Semantic Compression Over Feature Engineering**: ⚠️ **IMPLICIT**
- LLM layer shows this, but not explicitly stated

**Math as Authority, LLM as Amplifier**: ✅ **EXPLICITLY STATED**
- Source: `README.md:163` ("The Golden Rule")

---

## ⚠️ **10. IMPLEMENTATION NOTES - What EXISTS (PARTIAL)**

**Required Data**: ✅ **FOUND**
- OHLCV data, minimum 350 bars per timeframe
- Source: `docs/trencher_improvements/PM/v4_uptrend/v4_ongoing/COMPLETE_INTEGRATION_PLAN.md:173`

**System Inputs**: ✅ **FOUND**
- OHLCV bars, token metadata, regime context
- Source: Multiple implementation files

**Execution Assumptions**: ⚠️ **IMPLICIT**
- Direct PM→Executor calls, but assumptions not explicitly documented

**Hardware Considerations**: ❌ **NOT DOCUMENTED**

**Training Cadence**: ⚠️ **PARTIALLY DOCUMENTED**
- Pattern aggregation runs periodically, but exact cadence not documented

**Learning Cycle Timings**: ⚠️ **PARTIALLY DOCUMENTED**
- Some timing info exists (decay half-lives, recurrence tau), but not comprehensive

---

## 📊 **SUMMARY: What Can Be Answered vs. What's Missing**

### ✅ **FULLY ANSWERABLE (from codebase):**
1. Trend state definitions (S0/S1/S2/S3) and transitions
2. TS/OX/DX/EDX formulas and calculations
3. Market context dimensions (phases, buckets, timeframes)
4. Universal engine architecture and state machine
5. Pattern system (keys, scopes, categories)
6. Braid formation criteria
7. Lesson system (multipliers, levers, learning rates, decay)
8. LLM layer boundaries and safety guarantees
9. Multi-timeframe position system
10. A/E mode calculations
11. Time efficiency, field coherence, recurrence, emergence formulas
12. Reclaim/exhaustion definitions

### ⚠️ **PARTIALLY ANSWERABLE (needs formalization):**
1. ~~Volatility normalization~~ ✅ **FOUND** (ATR-based distance normalization)
2. ~~Counterfactual logic~~ ✅ **FOUND** (fully implemented)
3. Evaluation methodology (edge score exists, but slippage/latency missing)
4. Design philosophy (implicit, needs explicit statement)
5. Implementation constraints (partial - hardware minimal, but execution assumptions not explicit)

### ❌ **CANNOT ANSWER (missing from codebase):**
1. ~~Cross-market universality argument~~ ✅ **FOUND** (explicit arguments exist: human behavior, market dynamics, timeframe similarity - but no formal proof/statistical validation)
2. Theoretical foundations (behavioural finance, microstructure, statistical justification)
3. Complete failure mode analysis (implicit handling exists, but not explicitly documented)
4. Robustness testing methodology (no formal test suite documented)
5. ~~Risk framework~~ ✅ **FOUND** (overfitting prevention, false lesson decay, incremental edge checks)
6. Diagrams (state machine, learning flow, architecture)
7. Complete glossary (terms scattered)
8. Hardware considerations (minimal - just API + server, but not documented)
9. Complete evaluation methodology (edge exists, but slippage/latency/liquidity gaps not documented)

---

## 🎯 **RECOMMENDATIONS**

### **For Whitepaper Writing:**

1. **Start with what exists**: Sections 1-4 can be written from codebase
2. **Formalize implicit knowledge**: Design philosophy, implementation constraints
3. **Create missing theoretical sections**: Cross-market universality, theoretical foundations
4. **Add evaluation methodology**: Robustness tests, failure modes, real-world constraints
5. **Create diagrams**: State machine, learning flow, architecture
6. **Compile glossary**: From scattered terms in codebase
7. **Document risk framework**: Pattern overfitting, false lessons, etc.

### **Priority Order:**
1. **High Priority**: Formal definitions (1.1-1.3), Engine spec (2.1-2.3), Learning system (3.1-3.4)
2. **Medium Priority**: Evaluation methods (6), Implementation notes (10), Diagrams (7.2)
3. **Low Priority**: Theoretical foundations (8), Cross-market argument (5), Risk framework (7.4)

