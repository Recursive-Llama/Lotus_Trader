# Braiding System Design - Complete Learning System Roadmap

**Status**: Design Complete - Complete Roadmap for All Remaining Learning System Work

**Purpose**: This document is the complete roadmap for everything left to implement in the learning system. It covers:
1. DM Braiding (exploratory layer on top of existing coefficients)
2. PM Braiding (primary learning mechanism for PM)
3. LLM Learning Layer (hypothesis generation and semantic feature extraction)

**What's Already Done** (see [LEARNING_SYSTEM_V4.md](./LEARNING_SYSTEM_V4.md)):
- ✅ Phase 1: Basic coefficient updates from `position_closed` strands
- ✅ Phase 2: EWMA with temporal decay, interaction patterns, importance bleed
- ✅ Social Ingest infrastructure (ignored_tokens, chain_counts, metadata)

**What's Left** (this document):
- DM Braiding System
- PM Braiding System  
- LLM Learning Layer

---

## Overview

**Key Principle**: Outcome-First Exploration
- Start with outcomes (big wins, big losses, long/short holds)
- Work backwards to find patterns (what contexts/signals led to these outcomes)
- Braid similar outcomes together to discover common patterns
- Use insights to gently tune decision-making (not replace it)

**System Architecture**:
- **DM Learning**: Coefficients (prescriptive) ✅ COMPLETE + Braiding (exploratory) ⏸️ TODO
- **PM Learning**: Braiding only (no coefficients - too complex for PM's sequential actions) ⏸️ TODO
- **LLM Learning Layer**: Hypothesis generation, semantic tags, pattern recognition ⏸️ TODO

---

## 1. Data Structure for PM Learning

### 1.1 Enhanced `completed_trades` JSONB

**Current structure** (already implemented):
```json
{
  "type": "buy" | "sell",
  "tokens": 1000,
  "usd": 50.0,
  "price": 0.05,
  "timestamp": "2024-01-01T12:00:00Z",
  "tx_hash": "0x..."
}
```

**Enhanced structure** (for learning):
```json
{
  "type": "add" | "trim" | "emergency_exit",
  "tokens": 1000,
  "usd": 50.0,
  "price": 0.05,
  "timestamp": "2024-01-01T12:00:00Z",
  "tx_hash": "0x...",
  "action_context": {
    // A/E Scores
    "a_final": 0.5,
    "e_final": 0.3,
    "a_bucket": "med",  // low/med/high (0-0.3, 0.3-0.7, 0.7-1.0)
    "e_bucket": "low",
    
    // Uptrend Engine State & Signals
    "state": "S1" | "S2" | "S3",
    "buy_signal": false,
    "buy_flag": true,
    "first_dip_buy_flag": false,
    "trim_flag": false,
    "emergency_exit": false,
    "reclaimed_ema333": false,
    
    // Engine Scores
    "ts_score": 0.65,      // Trend Strength
    "dx_score": 0.75,      // S3 DX score
    "ox_score": 0.60,      // S3 OX score
    "edx_score": 0.55,     // S3 EDX score
    
    // EMA Slopes (from TA Tracker)
    "ema_slopes": {
      "ema60_slope": 0.02,
      "ema144_slope": 0.01,
      "ema250_slope": 0.005,
      "ema333_slope": 0.0
    },
    
    // Entry Zone Conditions
    "entry_zone_ok": true,
    "slope_ok": true,
    "ts_ok": true,
    
    // S/R Levels
    "sr_levels": [0.04, 0.05, 0.06],
    "current_sr_level": 0.05,
    "sr_level_changed": false,
    
    // Action Details
    "size_frac": 0.30,
    "size_bucket": "med",  // small/med/large (0-0.2, 0.2-0.5, 0.5-1.0)
    "entry_multiplier": 1.0,
    "trim_multiplier": 1.0,
    
    // Timing
    "bars_since_entry": 0,      // For first entry
    "bars_since_last_action": 0,
    "bars_until_exit": null     // Don't know yet
  }
}
```

### 1.2 Trade Summary (on Position Closure)

**Enhanced trade summary** (already partially implemented):
```json
{
  "entry_context": {...},  // From position.entry_context
  "entry_price": 0.05,
  "exit_price": 0.10,
  "entry_timestamp": "2024-01-01T12:00:00Z",
  "exit_timestamp": "2024-01-15T12:00:00Z",
  "decision_type": "emergency_exit",
  "rr": 2.0,
  "return": 1.0,
  "max_drawdown": -0.2,
  "max_gain": 1.5,
  
  // New: Outcome Classification
  "outcome_class": "big_win",  // big_win | big_loss | small_win | small_loss | breakeven
  "hold_time_bars": 144,
  "hold_time_days": 14,
  "hold_time_class": "medium",  // short | medium | long (<7d, 7-30d, >30d)
  
  // New: Counterfactual Analysis
  "could_enter_better": {
    "best_entry_price": 0.04,      // Lowest price in whole trade window
    "best_entry_timestamp": "2024-01-02T06:00:00Z",
    "best_entry_bars_after_actual": 12,
    "signals_at_best_entry": {
      "state": "S1",
      "ts_score": 0.70,
      "buy_signal": true,
      "a_final": 0.6,
      "e_final": 0.2
    },
    "missed_rr": 0.5  // Additional R/R if we entered at best price
  },
  
  "could_exit_better": {
    "best_exit_price": 0.12,       // Highest price in whole trade window
    "best_exit_timestamp": "2024-01-10T18:00:00Z",
    "best_exit_bars_before_actual": 6,
    "signals_at_best_exit": {
      "state": "S2",
      "ox_score": 0.75,
      "trim_flag": true,
      "e_final": 0.8
    },
    "missed_rr": 0.2  // Additional R/R if we exited at best price
  },
  
  // New: Action Sequence Analysis
  "action_sequence": [
    {
      "action": "add",
      "timestamp": "2024-01-01T12:00:00Z",
      "context": {...},  // Full action_context from completed_trades
      "rr_at_action": 0.0,  // R/R at this point in the trade
      "did_it_help": null   // Calculated after closure
    },
    {
      "action": "trim",
      "timestamp": "2024-01-08T12:00:00Z",
      "context": {...},
      "rr_at_action": 0.8,
      "did_it_help": true  // Price went down after trim
    }
  ]
}
```

---

## 2. Braiding System Architecture

### 2.1 Core Concept

**Braiding = Matching + Combining + Compressing**

1. **Match**: Find similar outcomes (e.g., all big wins with hold_time < 7 days)
2. **Combine**: Try different dimension combinations (A/E × signals × timing × outcomes)
3. **Compress**: Similar patterns compress into a single braid
4. **Discover**: Patterns emerge from the data (not predefined)

### 2.2 Braiding Process

**Step 1: Outcome Classification**
- Classify all completed trades by outcome:
  - `big_win`: R/R > 2.0
  - `big_loss`: R/R < -1.0
  - `small_win`: 0.5 < R/R <= 2.0
  - `small_loss`: -1.0 <= R/R < 0
  - `breakeven`: -0.1 < R/R < 0.1
- Also classify by hold time: `short` (<7d), `medium` (7-30d), `long` (>30d)

**Step 2: Dimension Extraction**
- Extract dimensions from action contexts, but **only braid on whitelisted dimensions** (see Dimension Policy below)
- Available dimensions include:
  - A/E buckets (low/med/high)
  - Engine signals (buy_signal, buy_flag, trim_flag, etc.)
  - Engine scores (TS, DX, OX, EDX) - bucketed
  - EMA slopes - bucketed (negative/flat/positive)
  - States (S1/S2/S3)
  - Action types (add/trim/exit)
  - Size buckets (small/med/large)
  - Timing (bars_since_entry, bars_until_exit)

**Dimension Policy** (controls combinatorial explosion via incremental edge filtering):

**Approach**: Start with broader whitelist, let incremental edge scores filter out redundant patterns.

- **DM Braiding**: Braid on: `curator`, `chain`, `mcap_bucket`, `age_bucket`, `intent`, `mapping_confidence`, `timeframe`, `mcap_vol_ratio_bucket`
  - Include all potentially meaningful dimensions
  - Incremental edge check will filter: if a pattern doesn't add value beyond its parents, it's naturally pruned
  - Dimensions that never contribute to high-edge patterns will effectively be ignored
  
- **PM Braiding**: Braid on: `state`, `a_bucket`, `e_bucket`, `buy_flag`, `trim_flag`, `action_type`, `ts_score_bucket`, `size_bucket`, `bars_since_entry_bucket`, `reclaimed_ema333`, `first_dip_buy_flag`, `emergency_exit`, `dx_score_bucket`, `ox_score_bucket`, `edx_score_bucket`
  - Include all engine signals and flags - we don't know which matter until we test
  - If `reclaimed_ema333` or `first_dip_buy_flag` consistently lead to big wins, incremental edge will surface that
  - If they don't add value, incremental edge will filter them out

**Controls** (not dimension exclusion):
- **Max subset size**: K=3 (patterns up to 3 dimensions)
- **Outcome as required dimension**: All patterns must include `outcome_class` (patterns are always "(context subset) + outcome_class")
- **Incremental edge check**: Patterns with `incremental_edge <= 0` are redundant (parent explains them)
- **Minimum sample size**: Patterns need `n >= n_min` to be considered
- **Edge score threshold**: Patterns need `|edge_raw| >= edge_min` to become lessons

**Key insight**: We don't need to pre-exclude dimensions. The incremental edge mechanism naturally filters out dimensions that don't add predictive value.

**Step 3: Braid Creation**
- Start with outcome groups: "All big wins"
- For each outcome group, try different dimension combinations:
  - "Big wins where A=med, E=low, buy_flag=True, S1"
  - "Big wins where A=high, E=med, TS>0.6, slopes_positive"
  - "Big wins where we added early (bars_since_entry=0), then trimmed at resistance"
- Create braids for patterns that cluster together (similar outcomes with similar contexts)

**Step 4: Pattern Discovery**
- For each braid, calculate:
  - `avg_rr`: Average R/R for this pattern
  - `avg_hold_time`: Average hold time
  - `win_rate`: % of trades that were wins
  - `variance`: How consistent is this pattern? (low variance = reliable, high variance = risky)
  - `sample_size`: How many trades match this pattern?

**Step 5: Insight Generation**
- High R/R + Low Variance + High Sample Size = Reliable pattern
- High R/R + High Variance = Risky pattern (sometimes big win, sometimes big loss)
- Low R/R + High Sample Size = Bad pattern (avoid this)
- Counterfactual insights: "Could we have entered 6 bars later? What signals were showing then?"

---

## 3. DM Braiding System

### 3.1 Purpose

**DM already has coefficients** (prescriptive learning). Braiding adds **exploratory discovery**:
- Find unexpected patterns coefficients might miss
- Discover new levers or interactions to track
- Validate coefficient patterns
- Find anomalies (e.g., "This curator usually good, but fails in these contexts")

### 3.2 Data Source

**From `position_closed` strands**:
- Entry context (curator, chain, mcap_bucket, vol_bucket, age_bucket, intent, etc.)
- Completed trade (R/R, return, max_drawdown, max_gain)
- Timeframe

### 3.3 Braiding Dimensions

**Entry Context Dimensions**:
- Curator
- Chain
- MCap bucket
- Vol bucket
- Age bucket
- Intent (hi_buy, med_buy, profit, sell, etc.)
- Mapping confidence
- Timeframe

**Outcome Dimensions**:
- R/R (big_win, big_loss, etc.)
- Hold time (short, medium, long)
- Max drawdown
- Max gain

### 3.4 Example Braids

**Braid 1**: "All big wins with curator=detweiler × chain=base × intent=hi_buy"
- Pattern: This combination consistently leads to big wins
- Insight: Maybe we should increase allocation for this combination

**Braid 2**: "All big losses with curator=X × mcap<100k × age<7d"
- Pattern: This curator fails on very new, very small tokens
- Insight: Maybe we should lower allocation or skip these

**Braid 3**: "All trades with intent=hi_buy × vol>1M × timeframe=1h"
- Pattern: High intent + high vol + 1h timeframe = good outcomes
- Insight: Maybe we should track vol as a lever in coefficients

---

## 4. PM Braiding System

### 4.1 Purpose

**PM has no coefficients** (too complex). Braiding is the **primary learning mechanism**:
- Find patterns in action sequences
- Discover optimal entry/exit timing
- Find counterfactual improvements
- Understand when actions help vs hurt

### 4.2 Data Source

**From `completed_trades` JSONB** (after position closure):
- All actions (add, trim, emergency_exit) with full action_context
- Final trade summary with outcome classification
- Counterfactual analysis (could enter/exit better)
- Action sequence analysis

### 4.3 Braiding Dimensions

**Action Context Dimensions**:
- A/E buckets (low/med/high)
- Engine signals (buy_signal, buy_flag, trim_flag, etc.)
- Engine scores (TS, DX, OX, EDX) - bucketed
- EMA slopes - bucketed
- States (S1/S2/S3)
- Action types (add/trim/exit)
- Size buckets (small/med/large)
- Timing (bars_since_entry, bars_until_exit)

**Outcome Dimensions**:
- Final R/R (big_win, big_loss, etc.)
- Hold time (short, medium, long)
- Action outcomes (did this add help? did this trim help?)

### 4.4 Example Braids

**Braid 1**: "All big wins where we added at A=med, E=low, buy_flag=True, S1, TS>0.6"
- Pattern: This entry pattern consistently leads to big wins
- Insight: Maybe we should increase entry size for this pattern

**Braid 2**: "All trades where we emergency exited, then had to rebuy"
- Pattern: We're exiting too early in these contexts
- Insight: Look at signals 6 bars before exit - what were they? Can we hold longer?

**Braid 3**: "All big wins where we trimmed at E=high, OX>0.65, then price went up"
- Pattern: We're trimming too early at resistance
- Insight: Maybe we should hold longer when OX is high and E is high

**Braid 4**: "All trades where we could have entered 6+ bars later for better price"
- Pattern: We're entering too early in these contexts
- Insight: What signals were showing at the better entry point? Can we wait for those?

**Braid 5**: "All trades where we added early (bars_since_entry=0), then trimmed, then added again"
- Pattern: This sequence leads to good outcomes
- Insight: Maybe we should actively look for this pattern

---

## 5. Implementation Plan

### 5.1 Phase 1: Data Collection (Now)

**What to do**:
1. Enhance `completed_trades` to include full `action_context` for each action
2. Enhance trade summary to include outcome classification and counterfactual analysis
3. Store all this data when position closes

**Complexity**: Low - just extend existing JSONB structure

**Timeline**: Can do now, doesn't block anything

### 5.2 Phase 2: Pure Math Braiding System (Next)

**What to build**:
1. Outcome classification service (classify trades: big_win, big_loss, etc.)
2. Dimension extraction service (extract A/E buckets, signals, scores, etc. from action_context)
3. Pattern query engine (SQL queries: "Find all big wins where A=med, E=low, buy_flag=True")
4. Pattern statistics calculator (avg_rr, win_rate, sample_size, variance)
5. Pattern storage (store query results in `learning_braids` table)

**Complexity**: Low-Medium - just SQL queries and aggregations, no clustering algorithms needed

**Timeline**: Build once we have enough data (10+ closed trades minimum)

**How it works**:
- When position closes → PM emits `position_closed` strand
- Braiding system runs immediately (not weekly!)
- Queries different dimension combinations to find patterns
- Stores results (just numbers: avg_rr, win_rate, n, variance)
- No complex algorithms - just SQL WHERE clauses and GROUP BY

### 5.3 Phase 3: Integration (Future)

**What to do**:
1. Feed braiding insights back into decision-making (gentle tuning)
2. Use insights to suggest new levers for DM coefficients
3. Use insights to adjust PM action sizes/thresholds

**Complexity**: Medium - requires careful integration to avoid breaking existing logic

**Timeline**: After braiding system is built and validated

---

## 6. Key Design Decisions

### 6.1 Why Outcome-First?

**Answer**: We know what we want (high R/R, short time). Start there, work backwards to find what leads to it.

### 6.2 Why Braiding Instead of Coefficients for PM?

**Answer**: PM has sequential actions (add → trim → exit), not just entry → exit. Coefficients can't handle sequences or counterfactuals well. Braiding can explore sequences and find "what if" patterns.

### 6.3 Why Both Coefficients and Braiding for DM?

**Answer**: 
- Coefficients: Fast, prescriptive, handles sparse data well
- Braiding: Exploratory, finds unexpected patterns, validates coefficients
- They complement each other

### 6.4 How to Use Insights?

**Answer**: Gentle tuning only:
- Don't replace decision logic
- Adjust sizes/thresholds by small amounts (max 10%)
- Validate insights with more data before applying
- Keep it conservative

---

## 7. Implementation Details

### 7.1 How Often to Run Braiding?

**Answer**: Run immediately when new `position_closed` strand is emitted (not weekly!)

**Flow**:
1. Position closes → PM emits `position_closed` strand
2. Math layer processes strand → Updates coefficients (already happens)
3. **Braiding system processes strand immediately** → Queries patterns, stores results
4. LLM layer processes strand (future) → Generates hypotheses

**Why immediately**: 
- Low frequency (1-2 per day max)
- Keeps analysis fresh
- No batching needed

### 7.2 How Many Patterns to Query?

**Answer**: We don't "create braids" - we query different dimension combinations to see what works.

**Approach**:
- Start with outcome groups: "All big wins", "All big losses"
- For each outcome, try different dimension combinations:
  - "Big wins where A=med, E=low, buy_flag=True, S1"
  - "Big wins where A=high, E=med, TS>0.6"
  - "Big wins where we added early, then trimmed at resistance"
- Query each combination, calculate stats, store if significant

**We query patterns, not pre-create braids.**

### 7.3 What Does a Braid Look Like?

**Answer**: A braid is just stored query results (numbers):

```sql
-- learning_braids table
{
  "pattern_key": "big_win|A=med|E=low|buy_flag=True|S1",
  "outcome_class": "big_win",
  "dimensions": {
    "a_bucket": "med",
    "e_bucket": "low",
    "buy_flag": true,
    "state": "S1"
  },
  "stats": {
    "avg_rr": 2.3,
    "win_rate": 0.85,
    "sample_size": 12,
    "variance": 0.4,
    "avg_hold_time_days": 5.2
  },
  "last_updated": "2024-01-15T10:00:00Z"
}
```

**It's just numbers - no complex structure needed.**

### 7.4 How to Store Braids?

**Answer**: New `learning_braids` table with pattern_key and stats.

```sql
CREATE TABLE learning_braids (
    pattern_key TEXT PRIMARY KEY,  -- "big_win|state=S1|A=med|buy_flag=true"
    module TEXT NOT NULL,           -- 'dm' | 'pm' (explicit module, not just in family_id)
    dimensions JSONB NOT NULL,     -- { outcome_class: "big_win", state: "S1", a_bucket: "med", buy_flag: true }
    stats JSONB NOT NULL,          -- { n, sum_rr, sum_rr_squared, avg_rr, variance, win_rate, avg_hold_time_days }
    family_id TEXT NOT NULL,       -- "pm|add|S1|big_win" (computed from core dimensions)
    parent_keys TEXT[],            -- Array of parent pattern_keys for incremental edge calculation
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_learning_braids_module ON learning_braids(module);
CREATE INDEX idx_learning_braids_family ON learning_braids(family_id);
CREATE INDEX idx_learning_braids_pattern ON learning_braids(pattern_key);  -- Already PK, but explicit for clarity
```

### 7.5 How to Query Braids?

**Answer**: SQL queries with JSONB indexing. No materialized views needed.

**Example query**:
```sql
-- Find all big wins where A=med, E=low, buy_flag=True
SELECT * FROM learning_braids
WHERE outcome_class = 'big_win'
  AND dimensions->>'a_bucket' = 'med'
  AND dimensions->>'e_bucket' = 'low'
  AND (dimensions->>'buy_flag')::boolean = true
ORDER BY stats->>'avg_rr' DESC;
```

### 7.6 How to Validate Patterns?

**Answer**: Minimum sample size + statistical significance.

**Criteria**:
- Minimum 10 samples (to avoid noise)
- Statistical significance (p-value < 0.05) if we want to be strict
- Or just: high sample size + consistent results = reliable pattern

### 7.7 Baseline Segmentation (Not Global R/R)

**Problem**: A 50k mcap, 1m token and BTC on 4h live in completely different universes. Comparing patterns against a single global R/R baseline distorts edge scores.

**Why pure `rr_global` is not enough**:
- High-vol microcaps will naturally have fatter tails (higher average R/R and variance)
- BTC/ETH, higher-cap, higher-timeframe trades might look "worse" just because they're calmer
- A pattern like "big wins on 50k mcap, 1m timeframe" will get a huge edge simply because that domain is more explosive, not because the pattern is objectively good within that domain

**What we actually care about**: "Does this pattern outperform the normal R/R for this type of trade?" where "type" = at least `mcap_bucket + timeframe`, and maybe `chain` later.

**Solution**: Use **segmented baselines** by `(mcap_bucket, timeframe)`.

**How it works**:
- Each pattern is compared against a **segment baseline** defined by:
  - `module` (dm/pm)
  - `mcap_bucket`
  - `timeframe`
- If there aren't enough samples for `(mcap_bucket, timeframe)`, fall back hierarchically:
  1. Try segment baseline `(mcap_bucket, timeframe)` - if `n >= N_MIN_SEG` (e.g., 10), use it
  2. Fall back to looser segments: mcap-only baseline, timeframe-only baseline
  3. If multiple fallbacks available, use weighted average (weighted by sample size)
  4. Final fallback: global baseline (use as ultimate fallback, not primary)
- Edge score becomes: `edge_raw = (avg_rr_pattern - rr_segment) * coherence * log(1+n)`

**Storage**: Baselines stored in `learning_configs` or a `learning_baselines` table with `(module, mcap_bucket, timeframe, stats)`.

**For PM**: Can use same segment logic (timeframe from position, mcap_bucket from entry_context). If too noisy initially, start with timeframe-only baseline.

**Example**:
- A 2.0 R/R on a 50k, 1m token is compared to the average R/R you usually get on 50k, 1m trades
- A 0.8 R/R on BTC 4h is compared to the average BTC 4h baseline
- Now "edge" actually means: "Does this pattern outperform the usual behaviour for trades like this?"

### 7.8 Lesson Lifecycle

**Status transitions**:

**Candidate → Active**:
- When `n >= N_promote` (e.g., 20) **and**
- `edge_raw > edge_promote` (e.g., 0.5) **and**
- Still positive over last `M` occurrences (e.g., last 10 trades)

**Active → Deprecated**:
- When over last `M_deprecate` trades (e.g., 20) where the lesson fired:
  - `edge_recent < 0` or `edge_recent < threshold` (e.g., 0.2)

**Deprecated → (archived/deleted)**:
- After some time period (e.g., 30 days) with no reactivation

### 7.9 Action-Level vs Trade-Level Outcomes

**In v1**: Braids are anchored on **trade-level** `outcome_class` (final R/R of the entire position).

**`did_it_help` field**: Used only for reporting and LLM commentary. Not used as a braiding dimension in v1.

**Future enhancement**: May introduce `action_outcome` as a PM dimension (e.g., `did_help_bucket = helped | neutral | hurt`), allowing braids like `"trim_flag=true, state=S2, did_help=false"`.

---

## 8. LLM Learning Layer

### 8.1 Purpose

**LLM Learning Layer** adds qualitative intelligence parallel to the math layer. It provides semantic interpretation, hypothesis generation, and pattern recognition that pure numbers can't see.

**Key principle**: LLM is **inside** the Learning System as a parallel subsystem. It reads the same data as the math layer and writes proposals/interpretations back to the database. Math layer remains the spine; LLM adds eyes and language.

**The Golden Rule**: 
> **LLM ≠ math. LLM ≠ statistics. LLM = structure + semantic intelligence.**

Everything numerical must stay in:
- `learning_braids`
- `learning_lessons`
- edge scores
- incremental_edge
- R/R outcomes
- sample sizes

The LLM should **never** replace the math layer. But an LLM **can**:
- Reshape structure
- Discover new representation
- Propose new abstractions
- Combine patterns semantically
- Detect meta-patterns we don't bucket
- Understand temporal "regimes"
- Propose new bucket boundaries
- Propose new family cores
- Detect contradictions / conflicts
- Evaluate whether lessons are coherent

### 8.2 Build-in Strategy: Phased Enablement

**Build infrastructure from Day 1, enable features gradually:**

**Phase 1 (Day 1)**: Build infrastructure, limited scope
- ✅ Build all 5 levels (infrastructure ready)
- ✅ Enable: Level 1 (Commentary) + Level 2 (Semantic Features)
- ⏸️ Disable: Level 3, 4, 5 (code exists, but not executed)
- ✅ Log everything (all LLM outputs stored)
- ⏸️ No decision impact (LLM outputs logged but not used)

**Phase 2 (After 10+ closed trades)**: Enable Level 5
- ✅ Enable Level 5 (Hypothesis Generation)
- ✅ Math layer tests hypotheses
- ⏸️ Still no decision impact (just testing)

**Phase 3 (After 50+ closed trades)**: Enable Level 3
- ✅ Enable Level 3 (Family Optimization)
- ✅ Math validates family proposals
- ⏸️ Still limited decision impact

**Phase 4 (After 100+ closed trades)**: Enable Level 4
- ✅ Enable Level 4 (Semantic Compression)
- ✅ Full system active

**Why build-in from Day 1:**
- Early validation of prompts/architecture
- Historical outputs to compare as data grows
- Iterate on prompts while data is manageable
- See which levels produce value early
- Avoid big integration later

### 8.3 Architecture

**Learning System Structure**:
```
Learning System
├── Math Layer (✅ COMPLETE)
│   ├── Reads: completed_trades, entry_context
│   ├── Computes: R/R, updates coefficients
│   └── Writes: learning_coefficients, learning_braids, learning_lessons
│
└── LLM Layer (✅ BUILD FROM DAY 1, phased enablement)
    ├── Reads: learning_coefficients, learning_braids, learning_lessons, completed_trades, strands, context
    ├── Interprets: patterns, anomalies, narratives, structure
    └── Writes: llm_learning table (hypotheses, reports, semantic tags, family proposals, semantic patterns)
```

**Communication**: Both layers communicate through database (no API calls). LLM reads what math writes, and vice versa.

### 8.4 Five Levels of LLM Integration

The LLM layer operates at five levels, from safest to most powerful:

#### Level 1: Commentary + Interpretation (⚘ Safe, Basic)

**Status**: ✅ Enable from Day 1

**What it does**:
- LLM reads `learning_braids` + `learning_lessons`
- Generates natural-language insights
- Writes regime summaries
- Provides qualitative explanations

**Output**: Reports stored in `llm_learning` table with `kind='report'`

**Use case**: Human-readable summaries of what the system is learning

**Example**:
- "Most of your 'S1 + med A + buy_flag' entries have been strong. Edge suggests a +7% size boost here. It looks like early S1 momentum is systematically under-allocated."

#### Level 2: Semantic Dimension Extraction (⚘ Powerful + Safe)

**Status**: ✅ Enable from Day 1

**What it does**:
- LLM creates new **semantic features** that math can test
- Extracts narrative tags: "AI narrative", "memecoin revival", "L2 rotation", "DEX meta"
- Extracts style tags: "insider-coded tweet", "urgent tone", "catalyst reference"
- Extracts project tags: "has roadmap", "no team", "trending on CT"

**How it works**:
- LLM reads token names, curator messages, project descriptions from strands
- Extracts semantic tags as **hypotheses** (not active levers yet)
- Stores in `llm_learning` table with `kind='semantic_tag'`, `status='hypothesis'`
- Math layer measures correlation: Does "AI narrative" tag correlate with R/R outcomes?
- If validated (statistically significant), tag becomes a learned coefficient in `learning_coefficients`

**Key**: Tags start as hypotheses, measured but not applied until validated

**Example**:
- LLM extracts: Token mentions "AI", "GPT", "neural" → tag: "AI narrative"
- Math layer measures: Trades with "AI narrative" tag → average R/R = 1.3×
- If significant: Add `learning_coefficients` row: `module='dm', scope='lever', name='semantic_tag', key='ai_narrative'`

#### Level 3: Family Core Optimization (⚘ Extremely Powerful)

**Status**: ⏸️ Enable after 50+ closed trades

**What it does**:
- LLM proposes new **family definitions** (reshapes how braids are grouped)
- Current families are deterministic: `{module, action_type, state, outcome_class}`
- LLM can propose better groupings based on observed patterns

**How it works**:
- LLM analyzes braids and observes: "S1 and S2 behave similarly for adds → merge"
- LLM proposes new family core: `{module, action_type, state_merged, outcome_class}`
- Math layer tests: Does merged family have better edge? More coherent patterns?
- If validated → update `family_id` for matching braids

**Impact**: Changes how braids are grouped and compressed, which patterns belong together

**Example**:
- Current: `pm|add|S1|big_win` and `pm|add|S2|big_win` are separate families
- LLM proposes: Merge to `pm|add|S1_S2_merged|big_win`
- Math validates: Merged family has better edge, more samples
- Result: Update family_id for all matching braids

#### Level 4: Semantic Pattern Compression (⚘ Very Strong)

**Status**: ⏸️ Enable after 100+ closed trades

**What it does**:
- LLM performs **semantic compression** (not just syntactic)
- Reads 30 braids in a family that look unrelated but share a narrative
- Proposes conceptual patterns that span multiple dimensional combinations

**How it works**:
- LLM reads braids: `{A=med, buy_flag=true, S1}`, `{A=high, dx>0.65, first_dip_buy_flag}`, `{A=med, ts_good, reclaimed_ema333}`
- LLM infers: "These are all manifestations of early-momentum reclaim scenarios"
- LLM proposes semantic pattern: `{momentum_reclaim: true}` with components
- Math layer tests: Does this semantic pattern have edge?
- If validated → Create lesson with semantic trigger

**Impact**: Lessons become conceptual patterns, not just bucket intersections

**Example**:
```json
{
  "semantic_pattern": "momentum_reclaim",
  "components": [
    {"pattern": "A=med|buy_flag=true|S1", "edge": 1.8},
    {"pattern": "A=high|dx>0.65|first_dip_buy", "edge": 1.9},
    {"pattern": "A=med|ts_good|reclaimed_ema333", "edge": 1.7}
  ],
  "conceptual_summary": "Early reclaim momentum plays have strong RR across S1/S2 when A>=med",
  "proposed_trigger": {"momentum_reclaim": true}
}
```

#### Level 5: Hypothesis Auto-Generation (⚘ Ultimate Power)

**Status**: ✅ Enable after 10+ closed trades

**What it does**:
- LLM helps the system **grow its own structure**
- Proposes new tests, bucket boundaries, interaction patterns
- Math layer auto-tests against historical data

**How it works**:
- LLM proposes: "Test whether rising OX + falling EDX is predictive"
- LLM proposes: "Test age<2d vs age<7d split — it looks meaningful"
- LLM proposes: "Test diagonal break + volatility compression sequence"
- Math layer tests each hypothesis against historical `completed_trades` data
- If validated → Promote to active lever or lesson

**Impact**: Self-growing intelligence — braiding system becomes fertile ground, LLM plants seeds, math decides which grow

**Example**:
- LLM proposes: "Test `{curator=detweiler, chain=base, age<3d}` interaction"
- Math layer queries: All historical trades matching this pattern
- Computes: Average R/R = 1.9×, n=8, p-value < 0.05
- Result: Promote to `learning_coefficients` as active interaction pattern

### 8.5 Where LLM Adds Value (Original Design)

#### 1. Pattern Recognition in Coefficients

**Primary focus**: Analyze coefficient drift, interaction patterns, and performance clusters to identify qualitative shifts.

**What it does**:
- Reads `learning_coefficients` table (all modules, all scopes)
- Analyzes recent coefficient changes, interaction pattern performance
- Generates hypotheses about why certain patterns are emerging/declining
- Proposes new interaction keys to test

**Example**:
- Math layer shows: `{curator=detweiler, chain=base, age<7d}` → 1.8× R/R
- LLM observes: "Base chain new listings from detweiler consistently outperform; likely early momentum capture"
- LLM proposes: Test `{curator=detweiler, chain=base, age<3d}` as new interaction key

#### 2. Semantic Feature Extraction (Hypothesis Phase)

**What it does**:
- Reads token names, curator messages, project descriptions from strands
- Extracts narrative tags: "AI narrative", "memecoin revival", "L2 rotation", "DEX meta"
- Creates semantic tags as **hypotheses** (not active levers yet)

**How it works**:
- Semantic tags are stored in `llm_learning` table with `status='hypothesis'`
- Math layer measures correlation: Does "AI narrative" tag correlate with R/R outcomes?
- If validated (statistically significant), tag becomes a learned coefficient in `learning_coefficients`
- **Key**: Tags start as hypotheses, measured but not applied until validated

**Example**:
- LLM extracts: Token mentions "AI", "GPT", "neural" → tag: "AI narrative"
- Math layer measures: Trades with "AI narrative" tag → average R/R = 1.3×
- If significant: Add `learning_coefficients` row: `module='dm', scope='lever', name='semantic_tag', key='ai_narrative'`

#### 3. Anomaly Detection & Regime Interpretation

**What it does**:
- Analyzes clusters of recent outcomes
- Generates natural language summaries of regime shifts
- Identifies anomalies that numeric deltas can't articulate

**Example output**:
- "Base chain new listings failing despite strong volume; volatility regime likely changing"
- "Detweiler's recent picks underperforming; curator edge may be fading or market rotated"

#### 4. Hypothesis Auto-Testing

**Key insight**: Hypotheses don't need implementation to be tested - they can be measured against historical data.

**How it works**:
- LLM proposes hypothesis (new interaction key, semantic tag, bucket boundary)
- Math layer auto-tests against historical `completed_trades` data
- If hypothesis shows statistical significance → promote to active coefficient
- If not → keep as hypothesis, continue measuring

**Example**:
- LLM proposes: "Test `{curator=detweiler, chain=base, age<3d}` interaction"
- Math layer queries: All historical trades matching this pattern
- Computes: Average R/R = 1.9×, n=8, p-value < 0.05
- Result: Promote to `learning_coefficients` as active interaction pattern

### 8.4 Database Schema

**Single table approach**: `llm_learning` table (consolidates hypotheses, reports, semantic tags)

```sql
CREATE TABLE llm_learning (
    id SERIAL PRIMARY KEY,
    kind TEXT NOT NULL,  -- 'hypothesis' | 'report' | 'semantic_tag' | 'regime_interpretation'
    module TEXT,         -- 'dm' | 'pm' | 'global' (which module this relates to)
    status TEXT NOT NULL,  -- 'hypothesis' | 'validated' | 'rejected' | 'active'
    content JSONB NOT NULL,  -- Kind-specific structure
    test_results JSONB,     -- Auto-test results (if kind='hypothesis')
    created_at TIMESTAMPTZ DEFAULT NOW(),
    validated_at TIMESTAMPTZ,
    notes TEXT
);

CREATE INDEX idx_llm_learning_kind_status ON llm_learning(kind, status);
CREATE INDEX idx_llm_learning_module ON llm_learning(module);
```

**Content structures**:

**Hypothesis** (`kind='hypothesis'`):
```json
{
  "type": "interaction_pattern" | "semantic_tag" | "bucket_boundary",
  "proposal": {
    "interaction_key": "curator=detweiler|chain=base|age<3d",
    "or": "semantic_tag": "ai_narrative",
    "or": "bucket": {"name": "mcap", "new_boundaries": ["<500k", "500k-2m", "2m+"]}
  },
  "reasoning": "LLM's explanation of why this might work",
  "test_query": "SQL or description of how to test this"
}
```

**Semantic Tag** (`kind='semantic_tag'`):
```json
{
  "tag": "ai_narrative",
  "extracted_from": ["token_name", "curator_message", "project_description"],
  "confidence": 0.85,
  "applies_to": ["position_id_123", "position_id_456"]
}
```

**Report** (`kind='report'`):
```json
{
  "type": "regime_interpretation" | "anomaly_detection" | "coefficient_summary",
  "summary": "Natural language interpretation",
  "coefficients_analyzed": ["module", "scope", "name"],
  "time_window": "2024-01-01 to 2024-01-15"
}
```

### 8.5 Execution Flow

**Trigger**: On every closed trade (1-2 per day max, not expensive)

**Flow**:
1. Position closes → PM emits `position_closed` strand
2. Math layer processes strand → Updates coefficients (as now)
3. LLM layer processes strand → Reads updated coefficients + completed_trade data
4. LLM analyzes:
   - Coefficient drift since last analysis
   - New interaction patterns emerging
   - Semantic features in token/curator data
5. LLM generates:
   - Hypotheses (new patterns to test)
   - Semantic tags (narrative extraction)
   - Reports (regime interpretations)
6. LLM writes to `llm_learning` table
7. Math layer auto-tests hypotheses against historical data
8. If validated → Promote to `learning_coefficients` (semantic tags become active levers)

### 8.6 Key Design Decisions

1. **Single table**: `llm_learning` consolidates all LLM outputs (simpler than separate tables)
2. **Run on every closed trade**: Low frequency (1-2/day), not expensive, keeps analysis fresh
3. **Auto-testing**: Hypotheses tested against historical data automatically (no manual approval needed for testing)
4. **Semantic tags as hypotheses first**: Tags measured but not applied until validated statistically
5. **Focus on pattern recognition**: LLM's primary job is analyzing coefficients, not extracting narratives (though it does both)
6. **Pure math braiding first**: LLM layer is optional enhancement - braiding system works without it

### 8.7 Integration with Math Layer

**How semantic tags become levers**:
1. LLM extracts semantic tag → stores in `llm_learning` with `status='hypothesis'`
2. Math layer measures: All trades with this tag → average R/R
3. If statistically significant → Create `learning_coefficients` row:
   - `module='dm', scope='lever', name='semantic_tag', key='ai_narrative'`
4. Tag becomes active lever in allocation formula

**How hypotheses become coefficients**:
1. LLM proposes interaction pattern → stores in `llm_learning`
2. Math layer auto-tests against historical data
3. If validated → Create `learning_coefficients` row with learned weight
4. Hypothesis becomes active interaction pattern

### 8.9 Phased Enablement Schedule

**Build infrastructure from Day 1, enable features gradually:**

| Phase | Trigger | Enabled Levels | Decision Impact |
|-------|--------|----------------|----------------|
| **Phase 1** | Day 1 | Level 1 (Commentary) + Level 2 (Semantic Features) | None (logging only) |
| **Phase 2** | 10+ closed trades | + Level 5 (Hypothesis Generation) | None (testing only) |
| **Phase 3** | 50+ closed trades | + Level 3 (Family Optimization) | Limited (validated proposals only) |
| **Phase 4** | 100+ closed trades | + Level 4 (Semantic Compression) | Full (all levels active) |

**Why build-in from Day 1:**
- ✅ Early validation of prompts/architecture
- ✅ Historical outputs to compare as data grows
- ✅ Iterate on prompts while data is manageable
- ✅ See which levels produce value early
- ✅ Avoid big integration later

**Safety limits:**
- All LLM outputs are logged but not used until validated by math layer
- Enablement flags control which levels execute
- Math layer validates everything before it affects decisions

---

## 9. Complete Implementation Roadmap

### Phase 1: Data Collection (Now)

**What to do**:
1. Enhance `completed_trades` to include full `action_context` for each action
2. Enhance trade summary to include outcome classification and counterfactual analysis
3. Store all this data when position closes

**Complexity**: Low - just extend existing JSONB structure

**Timeline**: Can do now, doesn't block anything

### Phase 2: Pure Math Braiding System (Next)

**Priority**: **PM Braiding is MORE CRITICAL than DM Braiding**
- PM has NO learning system currently (this is the primary learning mechanism)
- DM already has coefficients working (braiding is additive, not critical)

**What to build**:
1. Outcome classification service (classify trades: big_win, big_loss, etc.)
2. Dimension extraction service (extract A/E buckets, signals, scores from action_context)
3. Pattern query engine (SQL queries: "Find all big wins where A=med, E=low, buy_flag=True")
4. Pattern statistics calculator (avg_rr, win_rate, sample_size, variance)
5. Pattern storage (store query results in `learning_braids` table)

**Complexity**: Low-Medium - just SQL queries and aggregations, no clustering algorithms

**Timeline**: Build once we have enough data (10+ closed trades minimum)

**How it works**:
- When position closes → PM emits `position_closed` strand
- Braiding system runs immediately (not weekly!)
- Queries different dimension combinations to find patterns
- Stores results (just numbers: avg_rr, win_rate, n, variance)
- No complex algorithms - just SQL WHERE clauses and GROUP BY

**DM Braiding**: Can be added later (same system, different data source). PM braiding is more critical.

### Phase 3: Integration (After Phase 2)

**What to do**:
1. Feed braiding insights back into decision-making (gentle tuning)
2. Use insights to suggest new levers for DM coefficients
3. Use insights to adjust PM action sizes/thresholds

**Complexity**: Medium - requires careful integration to avoid breaking existing logic

**Timeline**: After braiding system is built and validated

### Phase 4: LLM Learning Layer (Build from Day 1, Phased Enablement)

**What to build** (all from Day 1):
1. LLM analysis service (reads coefficients, braids, lessons, completed_trades, strands)
2. Hypothesis generation service (Level 5)
3. Semantic tag extraction service (Level 2)
4. Family optimization service (Level 3)
5. Semantic compression service (Level 4)
6. Report generation service (Level 1)
7. Auto-testing service (math layer tests LLM hypotheses)
8. Enablement flags (control which levels execute)

**Complexity**: High - requires LLM integration, prompt engineering, validation logic

**Timeline**: 
- **Infrastructure**: Build from Day 1 (Phase 1)
- **Enablement**: Phased based on data availability (see Section 8.9)

**Prerequisites**:
- Math layer stable and proven (✅ COMPLETE)
- Braiding system infrastructure (✅ Build in Phase 2)
- Enablement flags to control feature activation

**Key**: Build all infrastructure from Day 1, but enable features gradually as data grows and confidence increases.

---

## 10. Concrete Implementation Pipeline

### 10.1 Data Model Clarifications

**Entry vs Exit Stats**:
- ✅ **mcap_bucket, vol_bucket, age_bucket are captured at ENTRY** (when DM creates position)
- ✅ Stored in `entry_context` JSONB at position creation
- ✅ For braiding: Use entry stats (what conditions existed when we entered)
- ✅ This is already implemented correctly

**Multiple Curators/Intents**:
- ✅ Each position is created from **one social signal** (one curator, one intent)
- ✅ `curator_sources` array can track additional curators, but primary curator is used for learning
- ✅ For braiding: Use **primary curator** + **intent from that signal**
- ✅ Future enhancement: Could track multiple curators if needed

**Coefficients vs Braiding**:
- ✅ All DM dimensions (mcap_bucket, vol_bucket, age_bucket, intent, curator, chain, mapping_confidence) are tracked in `learning_coefficients` table
- ✅ Braiding uses the same dimensions but discovers patterns coefficients might miss
- ✅ Braiding is exploratory, coefficients are prescriptive

### 10.2 Three-Stage Pipeline

**Stage 1: Braids = Pattern Aggregates**
- One braid = one row in `learning_braids` table
- Each row = aggregated stats across all trades matching that pattern
- Pattern key = unique identifier (e.g., `"big_win|state=S1|A=med|buy_flag=true"`)
- Stats = streaming aggregates (n, avg_rr, variance, win_rate, etc.)

**Stage 2: Edges = Strong Patterns**
- Compute edge score: `edge_raw(p) = (rr_p - rr_global) * coherence * log(1+n)`
- Filter to patterns with `n >= n_min` and `|edge_raw| >= edge_min`
- Check incremental edge vs parents (does extra dimension add value?)

**Stage 3: Lessons = Compressed Rules**
- Group braids into families (by core dimensions)
- Compress to simplest patterns that explain most edge
- Store in `learning_lessons` table with triggers and effects
- Only lessons are used at decision-time (not raw braids)

### 10.3 Dimension Inventory

**DM Dimensions** (from `entry_context`):
- `curator` (string)
- `chain` (string: solana, ethereum, base, bsc)
- `mcap_bucket` (string: <500k, 500k-1m, 1m-2m, 2m-5m, 5m-10m, 10m-50m, 50m+)
- `vol_bucket` (string: <10k, 10k-50k, 50k-100k, 100k-250k, 250k-500k, 500k-1m, 1m+)
- `age_bucket` (string: <1d, 1-3d, 3-7d, 7-14d, 14-30d, 30-90d, 90d+)
- `intent` (string: hi_buy, med_buy, profit, sell, research_positive, etc.)
- `mapping_confidence` (string: high, med, low)
- `mcap_vol_ratio_bucket` (string: <0.1, 0.1-0.5, 0.5-1.0, 1.0-2.0, 2.0-5.0, 5.0+)
- `timeframe` (string: 1m, 15m, 1h, 4h)

**PM Dimensions** (from `action_context` - needs implementation):
- `a_bucket` (string: low, med, high) - **needs bucketing**
- `e_bucket` (string: low, med, high) - **needs bucketing**
- `state` (string: S1, S2, S3)
- `buy_signal` (boolean)
- `buy_flag` (boolean)
- `first_dip_buy_flag` (boolean)
- `trim_flag` (boolean)
- `emergency_exit` (boolean)
- `reclaimed_ema333` (boolean)
- `ts_score_bucket` (string: low, med, high) - **needs bucketing** (<0.3, 0.3-0.7, >0.7)
- `dx_score_bucket` (string: low, med, high) - **needs bucketing**
- `ox_score_bucket` (string: low, med, high) - **needs bucketing**
- `edx_score_bucket` (string: low, med, high) - **needs bucketing**
- `ema_slopes_bucket` (string: negative, flat, positive) - **needs bucketing**
- `size_bucket` (string: small, med, large) - **needs bucketing** (0-0.2, 0.2-0.5, 0.5-1.0)
- `bars_since_entry_bucket` (string: 0, 1-5, 6-20, 21+) - **needs bucketing**
- `action_type` (string: add, trim, emergency_exit)

**Outcome Dimensions** (from `completed_trades`):
- `outcome_class` (string: big_win, big_loss, small_win, small_loss, breakeven)
- `hold_time_class` (string: short, medium, long)
- `rr` (float)
- `return` (float)
- `max_drawdown` (float)
- `max_gain` (float)

**Note**: See [BRAIDING_IMPLEMENTATION_GUIDE.md](./BRAIDING_IMPLEMENTATION_GUIDE.md) for detailed bucketing rules and implementation.

---

## 11. Next Steps & Priorities

### What to Do Before Relaunch?

**Critical (do before relaunch)**:
1. ✅ **Phase 1: Data Collection** - Enhance `completed_trades` with full `action_context`
   - This is needed for PM learning to work
   - Low complexity, doesn't block anything
   - **Do this now**

**Important (do soon after relaunch)**:
2. ⏸️ **Phase 2: PM Braiding System** - Build pure math braiding for PM
   - PM has NO learning system currently - this is critical
   - Start once we have 10+ closed trades
   - **Priority: HIGH** (PM learning is more important than DM braiding)

**Nice to Have (can wait)**:
3. ⏸️ **DM Braiding System** - Add exploratory layer to DM
   - DM already has coefficients working
   - Braiding is additive, not critical
   - Can be added later (same system, different data source)
   - **Priority: MEDIUM** (additive learning, not critical)

**Future Enhancement**:
4. ⏸️ **LLM Learning Layer** - Add hypothesis generation
   - After braiding system has run for 2-3 months
   - After we have 50+ closed trades
   - **Priority: LOW** (future enhancement)

### Recommendation

**Before Relaunch**:
- ✅ Phase 1: Data Collection (do now)

**After Relaunch (once we have 10+ closed trades)**:
- ⏸️ Phase 2: PM Braiding System (HIGH priority - PM has no learning)
- ⏸️ Phase 3: Integration (after braiding is validated)
- ⏸️ DM Braiding (can wait - DM already has coefficients)

**Future**:
- ⏸️ Phase 4: LLM Layer (after braiding has run for 2-3 months)

### Implementation Guide

For detailed implementation steps, see [BRAIDING_IMPLEMENTATION_GUIDE.md](./BRAIDING_IMPLEMENTATION_GUIDE.md).

