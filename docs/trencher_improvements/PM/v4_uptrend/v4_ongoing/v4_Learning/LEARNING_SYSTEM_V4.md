# Learning System v4 - Module-by-Module Analysis

**Status**: Complete - Systematic analysis of learning requirements per module

**Purpose**: Determine what each module needs to learn (or doesn't need to learn) for v4, and set up infrastructure for future learning.

## Implementation Status

**Phase 1 (Basic Coefficient Updates)**: ✅ **COMPLETE**
- Processes `position_closed` strands
- Updates single-factor coefficients using simple averaging
- Updates global R/R baseline

**Phase 2 (EWMA + Interaction Patterns + Importance Bleed)**: ✅ **COMPLETE**
- EWMA with temporal decay (TAU_SHORT=14 days, TAU_LONG=90 days)
- Interaction pattern tracking and updates
- Importance bleed to prevent double-counting
- All implemented in `CoefficientUpdater` and `UniversalLearningSystem`

**Social Ingest Infrastructure**: ✅ **COMPLETE**
- `ignored_tokens` loaded from `learning_configs` table (with fallback)
- `chain_counts` column in `curators` table (already exists)
- Chain detection uses curator chain prior as small weight
- Metadata added to strands (mapping_reason, confidence_grade, mapping_status)
- Chain_counts incremented on successful strand creation

**Remaining Work**: See [BRAIDING_SYSTEM_DESIGN.md](./BRAIDING_SYSTEM_DESIGN.md) for DM/PM Braiding and LLM Learning Layer

---

## Summary: Which Modules Need Learning?

**Modules that need learning**:
1. ✅ **Decision Maker**: Learn which levers (curator, chain, mcap, vol, age, intent, etc.) correlate with R/R outcomes → adjust allocation sizing
2. ✅ **Portfolio Manager**: Learn how to combine A/E scores with Uptrend Engine signals → adjust action sizes/thresholds

**Modules that don't need learning** (at this stage):
3. ✅ **Social Ingest**: Deterministic token detection/resolution (no learning needed)
4. ✅ **Uptrend Engine**: Deterministic signal generator (learning happens downstream in PM)
5. ✅ **Trader/Executor**: Pure execution (learning happens upstream in DM/PM)

**Key insight**: Learning is focused on **decision-making** (DM/PM), not on **signal generation** (Engine) or **execution** (Trader).

### Complete Learning Feedback Loop

**The critical loop** (simplest but most important):

```
1. DM/PM makes decision → PM calls executor.execute()
2. Executor executes trade → Returns results to PM (no database writes)
3. Position opens → PM stores entry context (levers at entry) in entry_context JSONB
4. Position closes → PM decides full exit, executor confirms, PM computes R/R, writes completed_trades JSONB
5. PM emits strand with kind='position_closed' → Contains completed_trade data
6. Learning system processes strand → Updates coefficients
7. Next decision uses updated coefficients → Better allocation
```

**For detailed PM-Executor flow and implementation**, see [COMPLETE_INTEGRATION_PLAN.md](./COMPLETE_INTEGRATION_PLAN.md) section "PM → Executor Flow & Price Tracking".

**PM's critical role**:
- **Must detect position closure** (PM decides full exit + executor confirms)
- **Must compute R/R metrics** from OHLCV data
- **Must write `completed_trades` JSONB** when position closes
- **Must emit strand** with `kind='position_closed'` containing completed_trade data
- **Must include `entry_context`** (levers at entry) in strand for learning
- **Without this, learning loop breaks** - no feedback, no updates

**Executor's role**:
- **Only executes trades** - returns results (tx_hash, tokens_sold, actual_price, slippage)
- **Does NOT write to database** - PM does all database writes
- **Does NOT manage position state** - PM manages position state

**This is the feedback loop** - PM closes the circle by providing outcomes to the learning system via strands.

---

## Table of Contents

1. [Learning Infrastructure](#learning-infrastructure)
2. [Social Ingest Module](#social-ingest-module)
3. [Decision Maker Module](#decision-maker-module)
4. [Portfolio Manager Module](#portfolio-manager-module)
5. [Uptrend Engine Module](#uptrend-engine-module)
6. [Trader/Executor Module](#traderexecutor-module)

---

## Learning Infrastructure

### `learning_configs` Table

**Purpose**: Store module-specific configuration that can be updated by the system (future learning) or manually.

**Structure**:
```sql
CREATE TABLE learning_configs (
    module_id TEXT PRIMARY KEY,  -- e.g., 'social_ingest', 'decision_maker', 'pm'
    config_data JSONB NOT NULL,   -- Module-specific config structure
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT,              -- 'system' | 'manual' | 'learning_system'
    notes TEXT
);
```

**Rationale**: 
- One row per module = simple queries (`SELECT config_data FROM learning_configs WHERE module_id = 'social_ingest'`)
- JSONB = flexible structure per module
- Easy to update: `UPDATE learning_configs SET config_data = jsonb_set(...) WHERE module_id = 'social_ingest'`
- Can add versioning later if needed

**Alternative considered**: Key-value table (`module_id + key + value`) - more normalized but more complex queries. JSONB is better for module-specific structures.

**Usage examples**:
- `social_ingest`: `ambiguous_terms`, `major_tokens`
- `decision_maker`: `global_rr` (baseline for normalization), `bucket_definitions` (mcap buckets, vol buckets, etc.)
- `portfolio_manager`: (future) exit strategy configs, rebalancing thresholds
- `uptrend_engine`: (future) signal thresholds, pattern recognition configs

**Key point**: This is for **configuration** (editable settings), not learned coefficients (which go in `learning_coefficients` table).

### `learning_coefficients` Table (vs. `learning_configs`)

**Distinction**:
- **`learning_configs`**: Module-specific **configuration** (editable settings, thresholds, lists)
- **`learning_coefficients`**: **Learned performance data** (R/R averages, weights, sample counts)

**Why separate tables**:
- Configs = what the system uses to operate (ambiguous terms, bucket definitions)
- Coefficients = what the system learns from outcomes (performance weights)
- Different update patterns: configs updated manually/by system, coefficients updated by learning loop

**One table per module?**:
- **No** - we use one `learning_configs` table with one row per module (JSONB for flexibility)
- **No** - we use one `learning_coefficients` table with multiple rows per module (one row per lever/interaction pattern)

**This makes all configs easy to adjust** (as you requested):
- `SELECT config_data FROM learning_configs WHERE module_id = 'social_ingest'` → get all ingest configs
- `UPDATE learning_configs SET config_data = jsonb_set(config_data, '{ambiguous_terms,ICM}', '{"rule":"suppress"}') WHERE module_id = 'social_ingest'` → update one config

---

## Social Ingest Module

### Current Role (v4)

**Core job**: Detect token mentions, resolve correct token (chain + contract), package clean signal for DM.

**Key change from v3**: Tokens go to **watchlist** first (not immediate buy), so less critical to filter perfectly. DM can reject later.

### Learning Requirements: **NONE** (for now)

**Why**: Deterministic detection and resolution is sufficient. Future learning can improve ambiguous term detection and curator chain priors, but not required for v4.

### Changes Needed

#### 1. Expose Ambiguous Terms (was `ignored_tokens`)

**Current**: Hardcoded list in `social_ingest_basic.py` (lines 53-76)

**v4**: Store in `learning_configs` table

```json
{
  "module_id": "social_ingest",
  "config_data": {
    "ambiguous_terms": {
      "ICM": {"rule": "suppress", "notes": "Ambiguous - could be many tokens"},
      "LIGHTER": {"rule": "suppress", "notes": "Ambiguous term"},
      "TRUMP": {"rule": "suppress", "notes": "Problematic/ambiguous"},
      // ... etc
    },
    "major_tokens": {
      "SOL": {"rule": "hard_block", "notes": "Major token"},
      "ETH": {"rule": "hard_block", "notes": "Major token"},
      // ... etc
    }
  }
}
```

**Implementation**:
- Read from `learning_configs` at startup
- Fallback to hardcoded list if table empty (backward compat)
- No dynamic updates yet (future: learning system can propose additions)

#### 2. Volume/Liquidity → NOTE, Don't BLOCK

**Current**: Hard filters that reject tokens (lines 450-470)

**v4**: Calculate but don't block. Add to strand metadata.

**Changes**:
- Remove `return None` for volume/liquidity/ratio checks
- Keep calculations
- Add to strand: `volume_health`, `liquidity_health`, `liq_mcap_ratio`
- Still block: chain not allowed, market cap == 0

**Rationale**: DM can evaluate these metrics. Ingest just packages the data.

#### 3. Curator Chain Prior (Simple Counting)

**Purpose**: Use curator's historical chain preference as small weight in chain detection.

**Implementation**:
- Add `chain_counts JSONB` to `curators` table: `{"solana": 27, "ethereum": 5, "base": 9, "bsc": 0}`
- Update `_detect_chain()` to use curator prior as small score weight (not tiebreaker)
- When strand successfully created: increment curator's chain count atomically

**Example**:
```python
# In _detect_chain(), if text cues ambiguous:
curator_chain_counts = curator.get('chain_counts', {})
if curator_chain_counts:
    # Add small weight (e.g., 0.1x normalized proportion)
    chain_score += 0.1 * (curator_chain_counts.get(chain, 0) / sum(curator_chain_counts.values()))
```

**Update point**: After successful strand creation, increment:
```python
# After strand created successfully
await supabase_manager.client.table('curators').update({
    'chain_counts': jsonb_set(
        chain_counts, 
        f'{{{chain}}}', 
        str((chain_counts.get(chain, 0) + 1))
    )
}).eq('curator_id', curator_id).execute()
```

#### 4. Chain Resolution Enforcement

**Requirement**: Must have chain resolved before emitting strand.

**Current**: `_detect_chain()` can return empty string → token rejected

**v4**: Explicit check - if no contract AND no chain resolved → don't emit, log `mapping_status='chain_unresolved'`

**Logic**:
- **If contract address provided** → Chain always resolved (comes from DexScreener API response)
- **If ticker only** → Must resolve chain via:
  - Text cues ("on Solana", "Base chain", etc.)
  - Curator chain prior (chain_counts)
  - DexScreener best match (if unambiguous)
- **If ambiguous** → Don't emit, log `mapping_status='chain_unresolved'`

**Key point**: Contract = chain always known. Ticker-only = must resolve via other means.

#### 5. Add Metadata to Strand

**New fields in strand**:

```python
{
    "mapping_reason": "contract_link" | "ticker+chain_phrase" | "curator_chain_prior" | "ticker_only",
    "confidence_grade": "high" | "med" | "low",  # Confidence in token identification
    "volume_health": {"vol24h": 150000, "min_required": 100000, "meets_threshold": true},
    "liquidity_health": {"liquidity": 50000, "min_required": 20000, "meets_threshold": true},
    "liq_mcap_ratio": 4.5,  # percentage
    "mapping_status": "resolved" | "ambiguous_term" | "chain_unresolved" | "no_contract_match"
}
```

**`confidence_grade` logic** (confidence in token identification):
- `high`: Contract address provided (unambiguous)
- `med`: $TICKER (exact cashtag, less ambiguous)
- `low`: Bare TICKER (no $, no contract, most ambiguous)

**Note**: We already have `identifier_used` ("contract" | "ticker") in signal_pack. `confidence_grade` is similar but more granular (distinguishes $TICKER from bare TICKER).

**`mapping_reason` logic** (HOW we resolved the chain+contract):
- `contract_link`: Found contract address in message → chain from DexScreener
- `ticker+chain_phrase`: Found ticker + explicit chain mention ("on Solana", "Base chain", etc.)
- `curator_chain_prior`: Used curator's historical chain preference (chain_counts)
- `ticker_only`: Just ticker, no other cues (chain from DexScreener best match)

### LLM Prompt Integration

**Current LLM Prompt** (`token_extraction`):
- Extracts: `token_name`, `ticker_source`, `contract_address`, `network`, `chain_context`
- Already asks LLM to "Pay attention to chain context" if mentioned in message

**v4 Changes to Prompt**: **NONE REQUIRED**

**Why**:
- LLM's job: Extract what's **in the message text** (network if mentioned, chain context)
- Our code's job: **Resolve chain** using multiple sources (LLM output + text cues + curator prior)
- Separation of concerns: LLM extracts, we resolve

**Flow**:
1. **LLM extracts** `network` and `chain_context` from message (if mentioned)
2. **`_detect_chain()` combines**:
   - LLM's `network` field (if provided)
   - Text cues from `additional_info` (keywords like "on Solana")
   - **(NEW)** Curator `chain_counts` prior (small weight, not tiebreaker)
3. **DexScreener API** also provides chain (from contract or best match)
4. **Final resolution**: Use DexScreener chain if contract, otherwise use `_detect_chain()` result

**Key Point**: We don't pass curator chain_counts to LLM because:
- LLM should extract what's **actually said** in the message
- Curator prior is our **resolution logic**, not something LLM should use
- We want LLM to be unbiased, then we apply our priors

**Ambiguous Terms**: We don't tell LLM about ambiguous terms because:
- LLM might extract "ICM" as a token (that's fine)
- We filter it out after extraction (line 214 check)
- This keeps LLM prompt simple and focused on extraction

### Summary: Social Ingest Changes

**Status**: ✅ **COMPLETE**

**Implemented changes**:
1. ✅ Expose ambiguous_terms in `learning_configs` table (read at startup, fallback to hardcoded)
2. ⏸️ Change volume/liquidity from BLOCK to NOTE (future enhancement - currently still blocks)
3. ✅ `chain_counts` column already exists in curators table
4. ✅ Update `_detect_chain()` to accept curator parameter and use chain_counts as small weight
   - **Note**: Curator passed through call chain: `process_social_signal()` → `_verify_token_with_dexscreener()` → `_detect_chain()`
5. ✅ Increment curator chain_counts on successful strand creation
6. ✅ Add `mapping_reason`, `confidence_grade`, `mapping_status` to strand metadata
7. ✅ Track how chain was resolved (returns `mapping_reason` from `_detect_chain()`)

**LLM Prompt Changes**: **NONE** - prompt already extracts network/chain_context. Our code handles resolution.

**No learning required** - all deterministic. Infrastructure set up for future learning.

---

## Decision Maker Module

### Current Role (v4)

**Core job**: Evaluate social signals, set initial allocation, create positions.

**Key change from v3**: Tokens go to **watchlist** first (not immediate buy), so DM can be more exploratory. Learning system will guide allocation sizing over time.

### Learning Requirements: **YES** (Core Learning Module)

**Why**: DM needs to learn which conditions (curator, chain, mcap, vol, age, intent, confidence) correlate with better risk/reward outcomes. This drives allocation sizing.

### Learning Philosophy

**Not rules → learned relationships**

- Observe how each **lever** correlates with realized R/R from closed trades
- Use those relationships to bias allocations **toward what has worked**, not cap what looks risky
- Every lever carries a **performance coefficient**, updated from closed-trade data
- **Edge lives in intersections** — combinations that consistently deliver high R/R

### Levers (Performance Factors)

| Lever | What it measures | What the system learns |
|-------|------------------|------------------------|
| **Curator** | Information quality | Historical R/R per curator (and optionally per chain) |
| **Market cap** | Size of project | R/R profile per cap bucket (e.g., <2M > 2-5M > 5-10M) |
| **Volume** | Turnover energy | Relationship between volume and realized R/R |
| **Mcap/Volume ratio** | Velocity proxy | High ratio = stagnant, low ratio = money rotating fast |
| **Chain** | Execution environment | Average R/R by chain (and by cap bucket) |
| **Age** | Time since launch | Whether new listings outperform mature ones |
| **Intent type** | Social signal strength | Which intents lead to better outcomes |
| **Mapping confidence** | Certainty of identification | How uncertainty affects edge (or adds to it) |

**Each lever starts with neutral weight = 1.0** and drifts toward observed R/R ratio.

### Two Layers of Learning

#### 1. Single-Factor Coefficients (Surface View)

Each lever on its own drifts toward its average R/R contribution:
- `factor_weight = R/R_avg / R/R_global`
- Example: If Base chain averages 1.4× R/R vs global 1.0× → `chain_weight['base'] = 1.4`

**Purpose**: Keep system stable and interpretable. Explains "in general, low caps perform better than large," "Base performs better than BSC," etc.

#### 2. Interaction Patterns (Deep View)

Most alpha hides in **combinations** that keep repeating as high-R/R environments.

**Example patterns**:
- `{curator=0xdetweiler, chain=Base, volume>250k, mcap<2m, age<7d}` → 1.8× R/R
- `{curator=eleetmo, chain=Ethereum, volume<100k, mcap>5m}` → 0.6× R/R

**How it works**:
- Store context keys (hashed combinations) → R/R outcomes
- Also keep **marginal slices**: `{curator, chain}`, `{chain}`, etc.
- Variable importance emerges from variance: if R/R changes a lot when age_bucket changes → age matters

**Not ML** — just pattern counting with lightweight clustering or hashed keys.

### Allocation Formula

```
initial_allocation = base_allocation × ∏(factor_weight[lever])
→ normalized to portfolio constraints
```

**Example**:
- Base: 4%
- Curator (0xdetweiler): 1.3×
- Chain (Base): 1.4×
- Intent (research_positive): 1.2×
- Mcap bucket (<2M): 1.5×
- Vol bucket (>250k): 1.1×
- Age bucket (<7d): 1.3×
- Mapping confidence (high): 1.0×
- **Product**: 4% × 1.3 × 1.4 × 1.2 × 1.5 × 1.1 × 1.3 × 1.0 = **18.7%**
- **Normalized**: Clamp to portfolio constraints (e.g., max 10% per position)

### Weight Calibration

**Prevent extreme multipliers**:

```python
weight = clamp((rr_avg_short / rr_global_short), w_min, w_max)
# Then normalize the product (geometric mean) to keep allocations in sane band
# Example: w_min = 0.5, w_max = 2.0
```

**Purpose**: Keep weights in reasonable bounds (e.g., 0.5-2.0×) before portfolio constraints.

### Importance Bleed (Anti-Double-Counting)

**When interaction weight is active, lightly downweight overlapping single-factor weights**:

```python
# If interaction pattern {curator=A, chain=Base} has weight 1.5
# Then shrink curator=A and chain=Base single weights toward 1.0 by small α
# Example: α = 0.2 → curator=A: 1.3 → 1.24, chain=Base: 1.4 → 1.32
```

**Purpose**: Avoid double-counting. If the interaction pattern already captures the synergy, don't also apply full single-factor weights.

### Temporal Dimension ("Lately")

**Time-decayed weights**:

- Every closed trade contributes with weight: `w = e^(-Δt / τ)`
- **Two time constants**:
  - **Short τ₁ (fast memory)** — how it's performing *right now* (e.g., 14 days)
  - **Long τ₂ (slow memory)** — long-term baseline (e.g., 90 days)
- When short ≫ long = **hot** (performing better than usual)
- When short ≪ long = **cold** (performing worse than usual)

**Purpose**: System adapts to recent performance while maintaining long-term baseline.

### Measuring Outcomes (R/R Calculation)

**Pure risk/reward from closed trades**:

**Data source**: `lowcap_price_data_ohlc` table (OHLCV bars for the position's timeframe)

**Query window**: Between `first_entry_timestamp` and `closed_at`

**SQL query** (example):
```sql
SELECT 
  MIN(low_native) as min_price,
  MAX(high_native) as max_price
FROM lowcap_price_data_ohlc
WHERE token_contract = $1
  AND chain = $2
  AND timeframe = $3  -- Position's timeframe (1m, 15m, 1h, 4h)
  AND timestamp >= $4  -- first_entry_timestamp
  AND timestamp <= $5  -- closed_at
```

**Calculations**:
```python
# Get prices from OHLCV data
min_price = MIN(low_native)  # Lowest price between entry and exit
max_price = MAX(high_native)  # Highest price between entry and exit
entry_price = avg_entry_price  # From positions table
exit_price = avg_exit_price  # From positions table

# Calculate metrics
return = (exit_price - entry_price) / entry_price
max_drawdown = (entry_price - min_price) / entry_price  # Always positive (entry >= min)
max_gain = (max_price - entry_price) / entry_price  # Always positive (max >= entry)

# Risk/Reward ratio
rr = return / max_drawdown  # Bounded/smoothed as needed (handle division by zero)
```

**Why both min and max prices?**
- **Max drawdown**: Measures worst-case risk (how far it dropped from entry)
- **Max gain**: Measures unrealized potential (how high it went before exit)
- **Both useful**: Max gain tells us if we exited too late (we could have exited at max_price but didn't). To know if we exited too early, we'd need to track price after exit.

**Note on system complexity**:
- The actual system uses a more complex position management strategy:
  - Big initial entry
  - Small trims
  - Re-entries
  - More small trims
  - Final emergency exit at the end
- This simplified model (single entry_price, single exit_price) is a simplification for learning purposes
- We could track actual profit (accounting for all trims/re-entries), but the current approach is good enough to start
- Future enhancement: Consider actual profit tracking for more accurate R/R calculation

**Where to store closed trade data**:

**Option: `completed_trades` JSONB in `lowcap_positions` table**

When position is fully closed (`status: active → watchlist`), compute R/R from OHLCV data and store trade summary:

```json
{
  "completed_trades": [
    {
      "entry_timestamp": "2024-01-15T10:00:00Z",
      "exit_timestamp": "2024-01-20T14:30:00Z",
      "entry_price": 0.0015,
      "exit_price": 0.0032,
      "min_price": 0.0012,  // From OHLCV: MIN(low_native) between entry and exit
      "max_price": 0.0045,  // From OHLCV: MAX(high_native) between entry and exit
      "min_price_timestamp": "2024-01-16T08:15:00Z",  // When min_price occurred
      "max_price_timestamp": "2024-01-19T14:30:00Z",  // When max_price occurred
      "timeframe": "1h",  // From position: which timeframe this trade was on
      "entry_context": {
        "curator": "0xdetweiler",
        "chain": "base",
        "mcap_bucket": "1m-2m",
        "vol_bucket": "250k-500k",
        "age_bucket": "3-7d",
        "intent": "research_positive",
        "mapping_confidence": "high",
        "mcap_vol_ratio_bucket": "0.5-1.0"
      },
      "rr": 1.42,
      "return": 1.13,
      "max_drawdown": 0.20,
      "max_gain": 2.0  // (max_price - entry_price) / entry_price
    }
  ]
}
```

**Computation flow** (PM responsibility):
1. **PM decides full exit** → `decision_type: "trim"` with `size_frac=1.0` OR `decision_type: "emergency_exit"`
2. **PM calls executor.execute()** → Executor executes trade, returns results (tx_hash, tokens_sold, actual_price, execution_status)
3. **PM checks**: If decision was full exit AND executor confirmed successful execution → Position is closed
4. **PM updates position table**: 
   - Updates `total_quantity` based on executor results
   - Updates `total_investment_native`, `total_extracted_native`
   - Sets `status='watchlist'`, `closed_at=now()`
5. **PM queries OHLCV data**: `lowcap_price_data_ohlc` for bars between `first_entry_timestamp` and `closed_at`
6. **PM computes R/R metrics**: `min_price`, `max_price`, return, max_drawdown, max_gain, R/R ratio
7. **PM writes `completed_trades` JSONB** to `lowcap_positions` table
8. **PM emits strand** with `kind='position_closed'` containing completed_trade data
9. **Learning system processes strand** → Updates coefficients

**Key point**: PM knows position is closed because it **decided** to do a full exit and executor **confirmed** it executed. PM doesn't "detect" closure by checking `total_quantity` - it knows from the decision + execution confirmation.

**Edge case**: If PM requests full exit (`size_frac=1.0` or `emergency_exit`) but executor returns results showing remaining tokens left → This is a problem to investigate (executor should have sold everything). However, PM still treats it as closed if executor confirmed the full exit was executed successfully. The remaining tokens would be dust or indicate an execution issue that needs investigation.

**Critical**: 
- **Executor does NOT write to database** - only executes and returns results to PM
- **PM does all database writes** - position updates, completed_trades JSONB, strands
- **Learning system processes `kind='position_closed'` strands** - needs to be wired to handle this strand type

**Alternative**: Store in `learning_coefficients` table as raw trade records (but that's mixing raw data with coefficients - not ideal).

**Recommendation**: `completed_trades` JSONB in positions table. Learning system reads from there to update coefficients.

**Tag each closed trade with**:
- All lever values at entry (stored in `entry_context`)
- **Timeframe** (from position: `1m`, `15m`, `1h`, `4h`) - needed for per-timeframe learning
- Interaction pattern key (hashed combination, computed from entry_context)

**Update coefficients**:
- Each lever/pattern tracks: `R/R_avg_short`, `R/R_avg_long`, `sample_count`
- Slow EWMA toward observed R/R mean
- `factor_weight = R/R_avg_short / R/R_global_short` (clamped)

**Global R/R (`R/R_global_short`)**:

**What it is**: Average R/R across ALL closed trades (using short-term decay, τ₁ = 14 days).

**Why we need it**: To normalize individual lever weights.

**Example**:
- Global average R/R = 1.0 (baseline)
- Base chain trades average R/R = 1.4
- Weight = 1.4 / 1.0 = 1.4× (Base performs 40% better than average)

**Without normalization**: We'd have absolute R/R values, but no way to compare "is this lever good or bad relative to everything else?"

**Calculation**:
```python
# Compute global R/R average (all closed trades, time-decayed)
rr_global_short = weighted_average(all_closed_trades, decay=τ₁)
rr_global_long = weighted_average(all_closed_trades, decay=τ₂)

# Then for each lever:
factor_weight = clamp((rr_avg_short / rr_global_short), w_min, w_max)
```

**Update frequency**: Recompute `rr_global_short` and `rr_global_long` whenever coefficients are updated (on every closed position).

**Where to store global R/R**:

**Option: `learning_coefficients` table with special row**:

```sql
-- Global R/R baseline (used for normalization)
('dm', 'global', 'baseline', 'all_trades', 1.0, 1.05, 0.98, 150, '2024-01-15T10:00:00Z')
```

**Or**: Store in `learning_configs.dm.global_rr` JSONB:
```json
{
  "rr_short": 1.05,
  "rr_long": 0.98,
  "n": 150,
  "updated_at": "2024-01-15T10:00:00Z"
}
```

**Recommendation**: Store in `learning_configs.dm.global_rr` (it's config-like, not a lever coefficient).

### Coefficient Update Frequency

**When to update**: **On every closed position**

**Flow**:
1. PM decides full exit → `decision_type: "trim"` with `size_frac=1.0` OR `decision_type: "emergency_exit"`
2. PM calls executor.execute() → Executor confirms successful execution
3. PM knows position is closed (from decision + execution confirmation) → Updates `status='watchlist'`, `closed_at=now()`
4. PM computes R/R from OHLCV data and writes `completed_trades` JSONB with trade summary
5. PM emits strand with `kind='position_closed'` containing completed_trade data
6. Learning system processes strand:
   - **Reads `completed_trade` data from strand** (not from positions table directly)
   - Strand contains: `completed_trade` (R/R metrics), `entry_context` (levers at entry), `timeframe`
   - Updates coefficients for all levers/interaction patterns that match
   - Updates global R/R baseline in `learning_configs.dm.global_rr`
   - Recalculates weights: `weight = clamp((rr_avg_short / rr_global_short), w_min, w_max)`

**Note**: Learning system processes strands via `process_strand_event()` - needs to be wired to handle `kind='position_closed'` strands.

**Why on every close**:
- Immediate feedback loop
- System adapts quickly to recent performance
- No batching complexity
- Each trade is independent event

**Performance**: Should be fast (just reading JSONB, computing R/R, updating a few coefficient rows).

### Shared Learning Table

**One table for all modules**:

```sql
CREATE TABLE learning_coefficients (
    module TEXT NOT NULL,           -- 'dm', 'pm', 'ingest', etc.
    scope TEXT NOT NULL,             -- 'lever' | 'interaction'
    name TEXT NOT NULL,              -- 'curator', 'chain', 'cap', 'vol', 'age', 'intent', 'mapping_confidence', or 'interaction'
    key TEXT NOT NULL,               -- Bucket or hashed combo (e.g., 'cap:<2m' or 'curator=detweiler|chain=base|age<7d|vol>250k')
    weight FLOAT NOT NULL,           -- Current multiplier (already clipped to system-wide bounds)
    rr_short FLOAT,                  -- Short-term R/R average (τ₁)
    rr_long FLOAT,                   -- Long-term R/R average (τ₂)
    n INTEGER DEFAULT 0,            -- Sample count
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (module, scope, name, key)
);
```

**Benefits**:
- One table total (no per-module tables)
- Decision Maker rows live beside (future) PM rows, separated by `module` column
- Everyone uses same mechanics (R/R short/long, decay), just different name/key rows
- Easy queries: `WHERE module='dm' AND scope='lever'`

**Indexes**:
```sql
CREATE INDEX idx_learning_coefficients_module_scope ON learning_coefficients(module, scope);
CREATE INDEX idx_learning_coefficients_module_name ON learning_coefficients(module, name);
```

### Bucket Vocabulary

**Standardized buckets for consistency**:

**Market Cap**:
- `<500k`, `500k-1m`, `1m-2m`, `2m-5m`, `5m-10m`, `10m-50m`, `50m+`

**Volume (24h)**:
- `<10k`, `10k-50k`, `50k-100k`, `100k-250k`, `250k-500k`, `500k-1m`, `1m+`

**Age (days since launch)**:
- `<1d`, `1-3d`, `3-7d`, `7-14d`, `14-30d`, `30-90d`, `90d+`

**Mcap/Volume Ratio**:
- `<0.1`, `0.1-0.5`, `0.5-1.0`, `1.0-2.0`, `2.0-5.0`, `5.0+`

**Purpose**: Consistent bucketing enables pattern matching and aggregation.

### PM Dynamic Recalculation

**Shared formula approach**:

- **DM**: Sets initial allocation using current coefficients at entry
- **PM**: Can recalculate dynamically using:
  - Same formula and coefficients (from `learning_coefficients` table)
  - Updated token data (current mcap, vol, age, etc.)
- **PM scales position** toward new target if liquidity allows

**Example**:
- Entry: $500k mcap → formula says 6%
- 2 weeks later: $5M mcap → same formula says 9%
- PM scales position toward 9% (within portfolio constraints)

**Benefits**:
- No round-trip to DM
- Continuous adaptation
- Same math = consistent

**Recalculation triggers** (future):
- When token features change significantly (mcap ×2, vol ×3, etc.)
- Periodic (daily/weekly)
- Or every PM tick (if lightweight enough)

### LLM Prompt Integration

**No prompt changes needed**:

- **Prompt sets base allocation** (e.g., 4% default, or suggests range)
- **Math layer applies learned multipliers** on top
- Prompt = "what should we allocate?" → base answer
- Coefficients = learned adjustments based on what works

**Current intent system**:

**How intents are used now** (lines 328-334 in `decision_maker_lowcap_simple.py`):
- LLM provides `allocation_multiplier` (static, 1.0-2.0 range) in `intent_analysis`
- DM applies it: `allocation = base_allocation * multiplier`
- Example: `research_positive` might have 1.5× multiplier from LLM

**v4 change**:
- **Remove static multiplier** from LLM (or keep as fallback if no learned data)
- **Learn coefficient** from closed trades: track R/R by `intent_type`
- `intent_weight['research_positive'] = R/R_avg_short / R/R_global_short`
- Use learned weight instead of (or combined with) LLM's static multiplier

**Keep LLM's intent classification** (we still need to know which intent it is), but weight it by observed performance.

### Entry Context Storage

**Where to store lever values at entry**:

**Question**: Store in `alloc_policy` JSONB or separate `entry_context` JSONB?

**Answer**: **Separate `entry_context` JSONB column** (recommended)

**Why**:
- `alloc_policy` is for allocation configuration (timeframe splits, thresholds)
- `entry_context` is for learning data (lever values at entry time)
- Separation of concerns: config vs. data

**Structure**:
```sql
ALTER TABLE lowcap_positions ADD COLUMN IF NOT EXISTS entry_context JSONB;
```

**Populated when**: DM creates position (when `decision_lowcap` strand is approved).

**Contents**: All lever values at entry time (see "Update: `lowcap_positions` table" section above).

**Alternative**: Store in `alloc_policy` JSONB under `entry_context` key, but separate column is cleaner.

### Summary: Decision Maker Changes

**Learning infrastructure**:
1. ✅ Create `learning_coefficients` table (shared across modules)
2. ✅ Define bucket vocabulary (mcap, vol, age, mcap/vol ratio)
3. ✅ Implement R/R calculation from closed trades
4. ✅ Implement coefficient update logic (EWMA with temporal decay)
5. ✅ Implement weight calibration (clamp + normalize)
6. ✅ Implement importance bleed (anti-double-counting for interactions)

**Allocation logic**:
1. ✅ Update allocation formula to use learned coefficients
2. ✅ Apply weight calibration and importance bleed
3. ✅ Normalize to portfolio constraints
4. ✅ Enable PM to recalculate using same formula

**No prompt changes** - prompt provides base, math provides multipliers.

**Learning happens from**: Closed trades → R/R calculation → coefficient updates → allocation adjustments.

**Per-timeframe learning** (see PM section for details):
- **Pure math, not in DM prompt**: DM prompt sets `total_allocation_usd` (total for the token)
- **Math layer splits** across timeframes using learned weights
- Track R/R by timeframe (1m, 15m, 1h, 4h) for all closed trades
- Learn which timeframes perform best
- Adjust allocation splits for **new positions** based on learned weights
- **Storage**: `learning_coefficients` table: `module='dm', scope='timeframe', name='1m|15m|1h|4h'`
- **Implementation**: 
  - DM prompt → sets `total_allocation_usd` (e.g., 1000 USD)
  - Math layer → reads learned timeframe weights, normalizes, applies splits
  - Result: `alloc_cap_usd[1m] = 1000 * normalized_weight[1m]`, etc.
  - **No prompt changes needed** - prompt provides total, math provides splits

---

## Portfolio Manager Module

**Status**: Analysis in progress

### Current Architecture (What PM Actually Does)

**From code analysis** (`pm_core_tick.py`, `levers.py`, `actions.py`):

1. **A/E Computation** (`levers.py`):
   - A (add appetite) and E (exit assertiveness) are continuous [0,1] scores
   - Computed from: meso phase → macro phase → cut_pressure → intent deltas → age/mcap boosts
   - A/E represents "how risk-on is the environment" (global + per-token)

2. **Action Planning** (`actions.py`):
   - Takes A/E + geometry flags (sr_break, diag_break, at_support, etc.)
   - Maps A to mode: aggressive (A>=0.7), normal (A>=0.3), patient (A<0.3)
   - Uses geometry flags to trigger actions (adds, trims, holds)
   - **Gap**: Uptrend Engine v4 flags/scores are available in `features.uptrend_engine_v4` but **not explicitly used** in `actions.py`

3. **Uptrend Engine v4** (`uptrend_engine_v4.py`):
   - Emits flags: `buy_flag`, `trim_flag`, `first_dip_buy_flag`, `emergency_exit`, `reclaimed_ema333`
   - Emits scores: `ox`, `dx`, `edx`, `ts`, `ts_with_boost`
   - Writes to `features.uptrend_engine_v4` (available but not consumed by actions.py)

**Key Insight**: PM is currently a **reactive gate** that combines:
- A/E (environmental risk-on/risk-off)
- Geometry flags (structure breaks, support/resistance)
- But **NOT** Uptrend Engine signals (yet)

### What Should PM Learn?

**Two learning dimensions**:

#### 1. **Reactive Learning: A/E × Signal Strength Interaction**

**Current gap**: Uptrend Engine emits signals, but PM doesn't use them.

**What to learn**: How to combine A/E with Uptrend Engine flags/scores.

**Example questions**:
- When A/E is low (0.3) but Uptrend Engine says `buy_flag=True` with `dx=0.75` → should we still add?
- When A/E is high (0.8) but Uptrend Engine says `emergency_exit=True` → should we trim more aggressively?
- When A/E is medium (0.5) and Uptrend Engine says `trim_flag=True` with `ox=0.70` → is the current trim size (from E) correct?

**Learning approach**:
- For each closed trade, log:
  - `a_at_entry`, `e_at_entry` (from levers)
  - `uptrend_flags_at_entry`: `buy_flag`, `trim_flag`, `first_dip_buy_flag`, `emergency_exit`
  - `uptrend_scores_at_entry`: `ox`, `dx`, `edx`, `ts`
  - `action_taken`: `add`, `trim`, `hold` (from actions.py)
  - `action_size_frac`: size fraction used
  - `rr_outcome`: R/R from closed trade

- Learn coefficients:
  - `pm_coefficient[a_bucket, e_bucket, signal_type, signal_strength]` → R/R outcome
  - Example: `pm_coefficient[a=0.7, e=0.3, signal=buy_flag, strength=dx>0.7]` = 1.4× (high R/R)
  - Example: `pm_coefficient[a=0.3, e=0.7, signal=trim_flag, strength=ox>0.65]` = 0.8× (low R/R, maybe trimmed too early)

**Implementation**:
- Add Uptrend Engine flag/score checks to `actions.py`
- Use learned coefficients to adjust action sizes or thresholds
- Store in `learning_coefficients` table: `module='pm', scope='reactive', name='a_e_signal_interaction'`

#### 2. **Threshold Calibration: A/E Mode Boundaries**

**Current**: Hard thresholds (A>=0.7 = aggressive, A>=0.3 = normal, A<0.3 = patient)

**What to learn**: Are these thresholds optimal?

**Learning approach**:
- Track R/R outcomes by A/E buckets
- If A=0.65 consistently performs like "aggressive" → lower threshold to 0.65
- If A=0.35 consistently performs like "patient" → raise threshold to 0.35

**Implementation**:
- Store in `learning_configs.pm.mode_thresholds`:
  ```json
  {
    "aggressive_threshold": 0.7,  // Learned from outcomes
    "normal_threshold": 0.3,      // Learned from outcomes
    "mode_sizes": {
      "aggressive": 0.50,  // Learned from outcomes
      "normal": 0.33,
      "patient": 0.10
    }
  }
  ```

#### 3. **Timing Efficiency (Future Enhancement)**

**What to learn**: Did we enter at the right time within the signal window?

**Approach**: Same as discussed earlier (timing_gain vs. realised_gain)

**Implementation**: Add to `completed_trades` JSONB, learn from timing_efficiency ratios.

#### 4. **Per-Timeframe Learning (Future Enhancement)**

**What to learn**: Which timeframes (1m, 15m, 1h, 4h) perform best?

**Current allocation splits** (see [COMPLETE_INTEGRATION_PLAN.md](./COMPLETE_INTEGRATION_PLAN.md) section "Timeframe Strategy"):
- Decision Maker sets `total_allocation_usd` for the token
- Each timeframe position gets: `alloc_cap_usd = total_allocation_usd * timeframe_percentage`
- **Default splits**: `1m`: 5%, `15m`: 12.5%, `1h`: 70%, `4h`: 12.5% (stored in `alloc_policy` JSONB)

**Learning approach**:
- Track R/R by timeframe for all closed trades
- Each timeframe gets a performance coefficient: `timeframe_weight = R/R_avg_short / R/R_global_short`
- Adjust allocation splits for **new positions** based on learned weights

**Two implementation options**:

**Option A: DM Learning (Recommended)**
- **Where**: Decision Maker adjusts allocation splits when creating new positions
- **When**: DM creates 4 positions per token, uses learned weights instead of fixed percentages
- **Important**: **Pure math, not in DM prompt**
  - DM prompt sets `total_allocation_usd` (total for the token)
  - Math layer splits across timeframes using learned weights
  - **No prompt changes needed** - prompt provides total, math provides splits
- **Formula**:
  ```python
  # Step 1: DM prompt sets total_allocation_usd (e.g., 1000 USD)
  total_allocation_usd = dm_prompt_output['allocation_usd']  # From LLM
  
  # Step 2: Math layer gets learned weights
  weights = {
    '1m': get_coefficient('dm', 'timeframe', '1m'),  # e.g., 0.8
    '15m': get_coefficient('dm', 'timeframe', '15m'),  # e.g., 1.4
    '1h': get_coefficient('dm', 'timeframe', '1h'),  # e.g., 1.1
    '4h': get_coefficient('dm', 'timeframe', '4h'),  # e.g., 0.9
  }
  
  # Step 3: Normalize weights (so they sum to 1.0)
  total_weight = sum(weights.values())
  normalized = {tf: w / total_weight for tf, w in weights.items()}
  
  # Step 4: Apply to allocation (math layer, not prompt)
  alloc_cap_usd[tf] = total_allocation_usd * normalized[tf]
  ```
- **Storage**: `learning_coefficients` table: `module='dm', scope='timeframe', name='1m|15m|1h|4h'`
- **Update**: On every closed trade, update timeframe R/R averages

**Option B: PM Dynamic Rebalancing**
- **Where**: PM periodically rebalances existing positions
- **When**: PM tick checks if allocation splits should be adjusted
- **Formula**: Same as Option A, but applied to existing positions
- **Complexity**: Higher (need to handle partial exits/re-entries, position size changes)
- **Use case**: If we want to dynamically shift capital between timeframes mid-trade

**Recommendation**: **Option A (DM Learning)**
- Simpler (only affects new positions)
- Cleaner separation of concerns (DM = allocation, PM = management)
- No need to rebalance existing positions (they were sized correctly at entry)

**Implementation**:
- Store in `learning_coefficients` table: `module='dm', scope='timeframe', name='1m|15m|1h|4h'`
- Track R/R per timeframe in `completed_trades` JSONB (already includes `timeframe` from position)
- Update coefficients on every closed trade (same as other DM levers)
- DM reads coefficients when creating positions, applies normalized weights

### Summary: PM Learning Priorities

**Phase 1 (Start Here)**:
1. ✅ **Reactive learning**: A/E × Uptrend Engine signal interaction
   - Learn how to combine A/E with Uptrend Engine flags/scores
   - Adjust action sizes/thresholds based on learned coefficients
   - **Requires**: Integrating Uptrend Engine flags into `actions.py` (currently missing)

**Phase 2 (After Phase 1)**:
2. ✅ **Threshold calibration**: A/E mode boundaries
   - Learn optimal A/E thresholds and mode sizes
   - Store in `learning_configs.pm.mode_thresholds`

**Phase 3 (Future)**:
3. ⏸️ **Timing efficiency**: Entry timing within signal windows
4. ⏸️ **Per-timeframe learning**: Allocation splits by timeframe

### Critical Gap: Uptrend Engine Integration

**Current state**: Uptrend Engine v4 emits flags/scores, but `actions.py` doesn't use them.

**Planned fix** (see [COMPLETE_INTEGRATION_PLAN.md](./COMPLETE_INTEGRATION_PLAN.md)):
- **Status**: Documented but not yet implemented
- **Required change**: Create `plan_actions_v4()` function using Uptrend Engine v4 signals
- **File**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py`
- **Implementation**: See [COMPLETE_INTEGRATION_PLAN.md](./COMPLETE_INTEGRATION_PLAN.md) section "New PM Decision Flow" (lines 783-1004)

**What `plan_actions_v4()` will do**:
- Read Uptrend Engine flags: `buy_signal`, `buy_flag`, `trim_flag`, `first_dip_buy_flag`, `emergency_exit`, `reclaimed_ema333`
- Read Uptrend Engine scores: `ox`, `dx`, `edx`, `ts`
- Combine with A/E scores to make decisions
- Use state (S1, S2, S3) for context

**Learning integration** (after `plan_actions_v4()` is implemented):
- Once Uptrend Engine signals are integrated, add learned coefficients to adjust action sizes/thresholds
- Example integration:
```python
# In plan_actions_v4(), after reading Uptrend Engine flags:
uptrend = features.get("uptrend_engine_v4") or {}
buy_flag = uptrend.get("buy_flag", False)
trim_flag = uptrend.get("trim_flag", False)
ox = uptrend.get("scores", {}).get("ox", 0.0)
dx = uptrend.get("scores", {}).get("dx", 0.0)
emergency_exit = uptrend.get("emergency_exit", False)

# Use learned coefficients to adjust action sizes:
if buy_flag and dx > 0.7:
    # Learned: high dx + buy_flag = boost add size
    learned_boost = get_pm_coefficient(a_final, e_final, "buy_flag", dx)
    size_frac *= learned_boost

if emergency_exit:
    # Learned: emergency_exit = more aggressive trim
    learned_trim_mult = get_pm_coefficient(a_final, e_final, "emergency_exit", 1.0)
    trim_size *= learned_trim_mult
```

**Note**: Learning system should wait until `plan_actions_v4()` is implemented before adding learned coefficients (Phase 1 of PM learning).

### Future Enhancement: Uptrend Engine Flags/Scores at Key Price Points

**Note for future PM learning**:
- Store Uptrend Engine flags/scores at `min_price_timestamp` and `max_price_timestamp`
- Learn: "Did we exit when uptrend signals were still strong?"
- Learn: "Did we hold through drawdowns when uptrend signals were weak?"
- This is more advanced and can be added later (PM learning, not DM learning)

---

## Uptrend Engine Module

**Status**: ✅ **No learning required** (at this stage)

**Why**:
- **Deterministic signal generator**: Emits flags/scores based on technical analysis (EMA states, TS, OX/DX/EDX)
- **Thresholds are tunable**: Constants class allows manual adjustment (TS_THRESHOLD, OX_SELL_THRESHOLD, etc.)
- **Learning happens downstream**: PM learns how to use the signals (A/E × signal interaction)
- **Not a decision maker**: Engine doesn't make trading decisions, it just emits signals

**Future considerations** (not needed now):
- Could learn optimal thresholds (TS_THRESHOLD, DX_BUY_THRESHOLD, etc.) from outcomes
- But this is more "calibration" than "learning" - can be done manually or via A/B testing
- The real learning is in PM (how to use the signals), not in the engine (how to generate them)

**Conclusion**: Engine stays deterministic. PM learns how to interpret and act on engine signals.

---

## Trader/Executor Module

**Status**: ✅ **No learning required** (at this stage), but **critical role in feedback loop**

### Executor's Role: Pure Execution

**Why executor doesn't need learning**:
- **Pure execution**: Gets price, executes trade, returns results
- **Operational concern**: Handles transaction signing, submission, confirmation
- **No decision logic**: Doesn't make trading decisions, just executes them
- **Error handling**: Already handles failures, retries, slippage

**Future considerations** (not needed now):
- The real learning is in DM/PM (what to trade, when to trade), not in executor (how to execute)

### Critical Role: Feedback Loop (Learning System Input)

**This is the most important part of the learning loop** - PM must emit strands when positions close.

**For detailed PM-Executor flow and implementation**, see [COMPLETE_INTEGRATION_PLAN.md](./COMPLETE_INTEGRATION_PLAN.md) section "PM → Executor Flow & Price Tracking" (lines 356-677).

**Summary of flow** (when position fully closes, `status: active → watchlist`):
1. **PM decides full exit** → `decision_type: "trim"` with `size_frac=1.0` OR `decision_type: "emergency_exit"`
2. **PM calls executor.execute()** → Executor executes trade, returns results (tx_hash, tokens_sold, actual_price, slippage, execution_status)
3. **PM checks**: If decision was full exit AND executor confirmed successful execution → Position is closed
4. **PM updates position table**: Updates `total_quantity`, `total_investment_native`, `total_extracted_native`, sets `status='watchlist'`, `closed_at=now()`
5. **PM computes R/R from OHLCV** → Queries `lowcap_price_data_ohlc`, computes min_price, max_price, R/R metrics
6. **PM writes `completed_trades` JSONB** → Stores trade summary in `lowcap_positions.completed_trades`
7. **PM emits strand** with `kind='position_closed'` → Contains completed_trade data for learning system

**Implementation** (PM side - see COMPLETE_INTEGRATION_PLAN.md for full code):
```python
# In pm_core_tick.py, after executor returns results:
if decision["decision_type"] in ["trim", "emergency_exit"]:
    result = executor.execute(decision, position)
    
    # Check if this was a full exit decision
    is_full_exit = (
        decision["decision_type"] == "emergency_exit" or
        (decision["decision_type"] == "trim" and decision.get("size_frac", 0) >= 1.0)
    )
    
    # Update position table (executor just returns results, PM does all writes)
    new_total_quantity = position['total_quantity'] - result['tokens_sold']
    update_position(position_id, {
        'total_quantity': new_total_quantity,
        'total_investment_native': updated_investment,
        'total_extracted_native': updated_extracted,
    })
    
    # If full exit was requested AND executor confirmed successful execution
    if is_full_exit and result.get('status') == 'success':
        # Note: If there are still tokens left after full exit, that's a problem to investigate
        # But we still treat it as closed since executor confirmed the full exit executed
        
        # Compute R/R from OHLCV
        completed_trade = compute_rr_from_ohlcv(position)
        
        # Write completed_trades JSONB
        position['completed_trades'].append(completed_trade)
        update_position(position_id, {
            'status': 'watchlist',
            'closed_at': datetime.now(timezone.utc),
            'completed_trades': position['completed_trades']
        })
        
        # Emit strand for learning system
        emit_strand({
            'kind': 'position_closed',
            'token': position['token_contract'],
            'position_id': position_id,
            'completed_trade': completed_trade,
            'entry_context': position['entry_context'],
            'timeframe': position['timeframe']
        })
```

**Learning system processing**:
- **Learning system must be wired** to process `kind='position_closed'` strands
- When learning system receives `position_closed` strand:
  - Reads `completed_trade` data from strand
  - Updates coefficients for all levers/interaction patterns
  - Updates global R/R baseline
  - Recalculates weights

**Why this matters**:
- **Learning system needs closed trade data** to update coefficients
- **PM is the source of truth** for position closure (manages position state)
- **Executor only executes** - returns results, doesn't write to database
- **Without this strand, learning loop breaks** - no feedback, no coefficient updates

**Note**: `completed_trades` JSONB is storage; the strand is the **event** that triggers learning system processing.

**Conclusion**: Executor stays operational (no learning, no database writes). PM manages position state and emits strands. Learning system processes strands to update coefficients.

---

---

## Future Enhancement: LLM Learning Layer

**Status**: Post-v4 enhancement (after math layer is stable and proven)

**Purpose**: Add qualitative intelligence layer that runs parallel to math layer, providing semantic interpretation, hypothesis generation, and pattern recognition that pure numbers can't see.

**Key principle**: LLM is **inside** the Learning System as a parallel subsystem. It reads the same data as the math layer and writes proposals/interpretations back to the database. Math layer remains the spine; LLM adds eyes and language.

### Architecture

**Learning System Structure**:
```
Learning System
├── Math Layer (current v4 focus)
│   ├── Reads: completed_trades, entry_context
│   ├── Computes: R/R, updates coefficients
│   └── Writes: learning_coefficients table
│
└── LLM Layer (future enhancement)
    ├── Reads: learning_coefficients, completed_trades, strands, context
    ├── Interprets: patterns, anomalies, narratives
    └── Writes: llm_learning table (hypotheses, reports, semantic tags)
```

**Communication**: Both layers communicate through database (no API calls). LLM reads what math writes, and vice versa.

### Where LLM Adds Value

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

### Database Schema

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

### Execution Flow

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

### Key Design Decisions

1. **Single table**: `llm_learning` consolidates all LLM outputs (simpler than separate tables)
2. **Run on every closed trade**: Low frequency (1-2/day), not expensive, keeps analysis fresh
3. **Auto-testing**: Hypotheses tested against historical data automatically (no manual approval needed for testing)
4. **Semantic tags as hypotheses first**: Tags measured but not applied until validated statistically
5. **Focus on pattern recognition**: LLM's primary job is analyzing coefficients, not extracting narratives (though it does both)

### Integration with Math Layer

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

### When to Implement

**Prerequisites**:
- Math layer stable and proven (v4 complete)
- Sufficient closed trades for pattern recognition (50+ trades minimum)
- Coefficient updates working reliably

**Why wait**:
- Math layer is foundation - must be solid first
- LLM layer adds complexity - better to add after core is proven
- Need historical data for LLM to analyze effectively

**Recommendation**: Implement after v4 math layer has run for 2-3 months and accumulated sufficient closed trades.

---

## Future Learning Opportunities

### Social Ingest (Future)

1. **Ambiguous Terms Auto-Detection**:
   - Scan positions table for tokens never traded
   - Assess why (was it bad ingest? ambiguous term?)
   - Propose additions to ambiguous_terms list

2. **Curator Chain Prior Refinement**:
   - Weight by recency (recent posts matter more)
   - Weight by success (chains that led to approved decisions)
   - But not needed for v4 - simple counting is fine

---

## Database Schema Changes

### New Table: `learning_configs`

**Purpose**: Store module-specific configuration that can be updated by the system (future learning) or manually.

```sql
CREATE TABLE learning_configs (
    module_id TEXT PRIMARY KEY,
    config_data JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT,  -- 'system' | 'manual' | 'learning_system'
    notes TEXT
);

CREATE INDEX idx_learning_configs_module ON learning_configs(module_id);
```

**Used by**: Social Ingest (ambiguous_terms), future modules

### New Table: `learning_coefficients`

**Purpose**: Shared learning table for all modules. Stores performance coefficients (weights) learned from closed trades.

```sql
CREATE TABLE learning_coefficients (
    module TEXT NOT NULL,           -- 'dm', 'pm', 'ingest', etc.
    scope TEXT NOT NULL,             -- 'lever' | 'interaction'
    name TEXT NOT NULL,              -- 'curator', 'chain', 'cap', 'vol', 'age', 'intent', 'mapping_confidence', or 'interaction'
    key TEXT NOT NULL,               -- Bucket or hashed combo (e.g., 'cap:<2m' or 'curator=detweiler|chain=base|age<7d|vol>250k')
    weight FLOAT NOT NULL,           -- Current multiplier (already clipped to system-wide bounds)
    rr_short FLOAT,                  -- Short-term R/R average (τ₁, e.g., 14 days)
    rr_long FLOAT,                   -- Long-term R/R average (τ₂, e.g., 90 days)
    n INTEGER DEFAULT 0,            -- Sample count
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (module, scope, name, key)
);

CREATE INDEX idx_learning_coefficients_module_scope ON learning_coefficients(module, scope);
CREATE INDEX idx_learning_coefficients_module_name ON learning_coefficients(module, name);
```

**Used by**: Decision Maker (primary), Portfolio Manager (recalculation), future modules

**Example rows**:
```sql
-- Single-factor coefficient
('dm', 'lever', 'chain', 'base', 1.4, 1.35, 1.2, 45, '2024-01-15T10:00:00Z')

-- Interaction pattern
('dm', 'interaction', 'interaction', 'curator=detweiler|chain=base|age<7d|vol>250k', 1.8, 1.75, 1.5, 12, '2024-01-15T10:00:00Z')
```

### Update: `curators` table

```sql
-- Add chain_counts JSONB column
ALTER TABLE curators ADD COLUMN IF NOT EXISTS chain_counts JSONB DEFAULT '{}'::jsonb;

-- Example structure:
-- chain_counts: {"solana": 27, "ethereum": 5, "base": 9, "bsc": 0}
```

**Used by**: Social Ingest (chain resolution with curator prior)

### Update: `ad_strands` table (for social_lowcap strands)

**New fields in `signal_pack` or `module_intelligence`** (JSONB - no schema change needed):
- `mapping_reason`: TEXT (enum: contract_link, ticker+chain_phrase, curator_chain_prior, ticker_only)
- `confidence_grade`: TEXT (enum: high|med|low)
- `volume_health`: JSONB `{"vol24h": 150000, "min_required": 100000, "meets_threshold": true}`
- `liquidity_health`: JSONB `{"liquidity": 50000, "min_required": 20000, "meets_threshold": true}`
- `liq_mcap_ratio`: FLOAT (percentage)
- `mapping_status`: TEXT (enum: resolved, ambiguous_term, chain_unresolved, no_contract_match)

**Note**: These can live in `signal_pack` JSONB - no schema change needed.

### Update: `lowcap_positions` table (for closed trades)

**Fields for R/R calculation** (already exist):
- ✅ `avg_entry_price`: FLOAT (weighted average entry price)
- ✅ `avg_exit_price`: FLOAT (weighted average exit price)
- ✅ `first_entry_timestamp`: TIMESTAMPTZ (query start point)
- ✅ `closed_at`: TIMESTAMPTZ (query end point)
- ✅ `timeframe`: TEXT (which OHLCV timeframe to query: 1m, 15m, 1h, 4h)
- ✅ `token_contract`: TEXT (for OHLCV query)
- ✅ `token_chain`: TEXT (for OHLCV query)

**Note**: We don't need to store `min_price_after_entry` in the positions table - we compute it from OHLCV data when the position closes and store it in `completed_trades` JSONB.

**Fields for tagging closed trades with lever values**:

**Option: `entry_context` JSONB column** (recommended)

Store lever values at position creation (when DM approves):

```sql
ALTER TABLE lowcap_positions ADD COLUMN IF NOT EXISTS entry_context JSONB;
```

**Structure**:
```json
{
  "curator": "0xdetweiler",
  "chain": "base",
  "mcap_bucket": "1m-2m",
  "vol_bucket": "250k-500k",
  "age_bucket": "3-7d",
  "intent": "research_positive",
  "mapping_confidence": "high",
  "mcap_vol_ratio_bucket": "0.5-1.0",
  "mcap_at_entry": 1500000,
  "vol_at_entry": 350000,
  "age_at_entry": 5
}
```

**Alternative**: Store in `alloc_policy` JSONB (but that's for allocation config, not entry context).

**Store completed trades**:

**Option: `completed_trades` JSONB column** (recommended)

When position fully closes, store trade summary:

```sql
ALTER TABLE lowcap_positions ADD COLUMN IF NOT EXISTS completed_trades JSONB DEFAULT '[]'::jsonb;
```

**Structure**: Array of completed trade objects (see "Measuring Outcomes" section above).

**Why JSONB in positions table**:
- Keeps trade data with position (easy to query)
- Learning system can scan `WHERE closed_at IS NOT NULL` to find completed trades
- No separate table needed
- Can query: `SELECT completed_trades FROM lowcap_positions WHERE closed_at IS NOT NULL`

**Alternative**: Separate `closed_trades` table - but JSONB is simpler for now.

---

## Implementation Checklist

### Critical: Wire Learning System to Process `position_closed` Strands

**Required**: Learning system must be updated to process `kind='position_closed'` strands.

**Current state**: Learning system processes strands via `process_strand_event()`, but may not handle `position_closed` strands yet.

**What needs to be done**:
- Update `UniversalLearningSystem.process_strand_event()` or add handler for `kind='position_closed'`
- When `position_closed` strand is received:
  - Extract `completed_trade` data from strand
  - Extract `entry_context` from strand (levers at entry)
  - Update coefficients for all matching levers/interaction patterns
  - Update global R/R baseline
  - Recalculate weights

**Without this, learning loop is broken** - no coefficient updates happen.

**Note**: COMPLETE_INTEGRATION_PLAN.md has been updated to reflect:
1. ✅ **Removed "demote"** - Uses "trim" with `size_frac=1.0` or "emergency_exit" instead
2. ✅ **Executor doesn't write to database** - Executor only executes and returns results; PM does all database writes
3. ✅ **PM updates position status** - PM decides full exit + executor confirms, then PM updates `status='watchlist'`

---

## Implementation Checklist (Detailed)

### Social Ingest

- [ ] Create `learning_configs` table
- [ ] Migrate `ignored_tokens` to `learning_configs.social_ingest.ambiguous_terms`
- [ ] Update `social_ingest_basic.py` to read from `learning_configs` at startup
- [ ] Add `chain_counts` column to `curators` table
- [ ] Update `_detect_chain()` to accept curator parameter and use chain_counts as small weight
- [ ] Remove volume/liquidity BLOCK logic (change to NOTE - remove `return None` lines)
- [ ] Add health metrics (`volume_health`, `liquidity_health`, `liq_mcap_ratio`) to strand output
- [ ] Add `mapping_reason` and `confidence_grade` to strand
- [ ] Increment curator `chain_counts` on successful strand creation
- [ ] Add explicit chain resolution check (don't emit if unresolved)

### Decision Maker

- [ ] Create `learning_coefficients` table (shared across modules)
- [ ] Define bucket vocabulary (mcap, vol, age, mcap/vol ratio) - standardize buckets
- [ ] Implement R/R calculation from closed trades:
  - [ ] Track entry/exit prices, max drawdown in `lowcap_positions`
  - [ ] Store lever values at entry (curator, chain, mcap_bucket, vol_bucket, age_bucket, intent, mapping_confidence, mcap_vol_ratio_bucket)
  - [ ] Compute R/R on position close: `R = (exit/entry) - 1`, `DD = |min_price - entry| / entry`, `R/R = R / DD`
- [x] Implement coefficient update logic:
  - [x] EWMA with temporal decay (short τ₁ = 14 days, long τ₂ = 90 days) ✅ COMPLETE
  - [x] Update `rr_short`, `rr_long`, `n` for each lever/interaction pattern ✅ COMPLETE
  - [x] Calculate `weight = clamp((rr_short / rr_global_short), w_min, w_max)` ✅ COMPLETE
- [x] Implement weight calibration (clamp to [0.5, 2.0] then normalize product) ✅ COMPLETE
- [x] Implement importance bleed (downweight overlapping single-factor weights when interaction pattern active) ✅ COMPLETE
- [ ] Update allocation formula to use learned coefficients:
  - [ ] Read coefficients from `learning_coefficients` table
  - [ ] Apply weight calibration and importance bleed
  - [ ] Calculate: `allocation = base × ∏(factor_weight[lever])`
  - [ ] Normalize to portfolio constraints
- [ ] Enable PM to recalculate using same formula (shared math, updated token data)

### Portfolio Manager

- [ ] **CRITICAL**: Implement position closure detection and strand emission:
  - [ ] After executor returns results, check if decision was full exit (`size_frac=1.0` or `emergency_exit`) AND executor confirmed success
  - [ ] If closed: Query OHLCV data from `lowcap_price_data_ohlc` (between `first_entry_timestamp` and `closed_at`)
  - [ ] Compute R/R metrics: `min_price`, `max_price`, return, max_drawdown, max_gain, R/R ratio
  - [ ] Write `completed_trades` JSONB to `lowcap_positions` table
  - [ ] Update position: `status='watchlist'`, `closed_at=now()`
  - [ ] **Emit strand** with `kind='position_closed'` containing:
    - `completed_trade` (R/R metrics, entry/exit prices, timestamps)
    - `entry_context` (levers at entry from `entry_context` JSONB)
    - `timeframe`, `token_contract`, `chain`, `position_id`
- [ ] Ensure executor does NOT write to database (only returns results)
- [ ] Ensure PM does all database writes (position updates, completed_trades, strands)
- [ ] Store `entry_context` JSONB when position is created (DM sets this)

### Learning System

- [ ] **CRITICAL**: Wire learning system to process `kind='position_closed'` strands:
  - [ ] Update `UniversalLearningSystem.process_strand_event()` to handle `position_closed` strands
  - [ ] Extract `completed_trade` and `entry_context` from strand
  - [ ] Update coefficients for all matching levers/interaction patterns
  - [ ] Update global R/R baseline
  - [ ] Recalculate weights

---

## Notes

- **Learning System v4 Philosophy**: Minimal learning, maximum infrastructure for future learning
- **Deterministic First**: All modules work deterministically; learning enhances, doesn't replace
- **Auditable**: All decisions traceable via strands with full context
- **Future-Ready**: Infrastructure (tables, metadata) set up for learning system to use later

