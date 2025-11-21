# v5 Meta-Learning Implementation Plan

**Status**: Draft - implementation roadmap for regime-adaptive (v5.1-v5.3) layers.

**Purpose**: Document how we evolve from the fixed-weight v4 enhancements to the adaptive v5 meta-learning stack outlined in Section 7 of `V4_LEARNING_ENHANCEMENTS.md`.

## 1. Overview

v4 added the core measurement multipliers:
- Time efficiency
- Field coherence
- Recurrence depth
- Emergence tracking (advisory)

v5 extends that foundation with meta-learners that adapt the weights/factors themselves based on regime and decay behavior:
1. **v5.1 Meta-Factor Weight Learning** – learn regime-specific weights for time/field/recurrence/variance.
2. **v5.2 Alpha Half-Life Modeling** – estimate decay curves and half-lives for patterns/lessons.
3. **v5.3 Pattern Orthogonalization** – de-correlate patterns via latent factors and prevent double-counting.

Each phase layers on top of the v4 stats already stored per braid/lesson.

### 1.1 Canonical inputs (v4.5 foundation)

- **Pattern identity** – `module|pattern_key=family.state.motif` from `PATTERN_KEY_SCOPE_SPEC.md`.
- **Action category** – `entry`, `add`, `trim`, `exit` stored alongside every action so edge histories stay class-specific.
- **Scope JSON** – seven canonical dims (`market_family`, `regime`, `bucket`, `timeframe`, `A_mode`, `E_mode`, subset of dims in use) captured post-plan, referencing `CAP_BUCKET_REGIME_SPEC.md` outputs.
- **Controls** – actual applied signals + execution knobs so lever adjustments can be evaluated.
- **`pattern_scope_stats`** – aggregation table keyed by `(pattern_key, action_category, scope_mask)` that v5 consumes for training and QA.

## 2. Phase v5.1 – Meta-Factor Weight Learning

### 2.0 Regime Inputs (v5 foundation)

- **Composite phases** – `macro/meso/micro` now derive from the low-cap composite (nano→large buckets, XL excluded). Each record still exposes `phase`, `score`, and `ts`, so the learner can treat `score` as a continuous feature and `phase` as a categorical label.
- **Bucket context** – `phase_state_bucket` stores per-bucket regime stats (`phase`, `score`, `slope`, `confidence`, `population`). `_get_regime_context()` also exposes `bucket_rank` (sorted by meso score) so we know the current risk ladder.
- **Token tagging** – `token_cap_bucket` provides the current cap bucket per token×chain; PM Core joins it to positions and logs it with trade outcomes.

These upgrades let us build richer regime signatures such as `macro=Recover|meso=Dip|bucket_rank=micro>nano>mid>big|position_bucket=micro`, and include numeric signals like macro/meso scores or top-bucket slope/confidence.

### 2.1 Goal
Learn regime-specific weights for existing multipliers so the edge formula adapts to current market conditions (volatility regimes, trend states, narrative phases, timeframe distribution) **per action_category**.

### 2.2 Key Steps
1. **Regime Detection Inputs** – reuse `regime_context` (macro/meso/micro) plus additional signals (volatility percentile, trend slope, timeframe dominance). 
2. **Baseline Data** – for every entry/add/trim/exit event, capture:
   - `pattern_key`, `action_category`, scope JSON, applied controls,
   - full regime snapshot (global phases, bucket rank, position bucket),
   - the v4 multipliers applied and realized edge metrics.  
   This becomes the training set per regime signature and category.
3. **Learning Process** – periodically (e.g. daily cron):
   - Group samples by regime signature (macro/meso/micro + bucket context).
   - Measure which multipliers correlated most with realized edge improvements (EWMA or regression).
   - Update weight vectors per signature and track metadata such as `n_samples`, decay half-life, confidence.
4. **Serving the Weights** – store in a new `learning_regime_weights` table keyed by `(regime_signature, action_category)` (e.g., `"recover|dip|micro-risk_on|entry"`). At inference, detect the current signature and fetch the learned weights (fallback to defaults if insufficient data).
5. **Edge Formula Update** – modify `compute_edge_score()` to detect the current regime + action_category, fetch learned weights, and scale each multiplier accordingly (fallback to default 0.5/0.5 curve if insufficient data).

### 2.3 Deliverables
- Regime weight table + CRUD helpers.
- Batch job / function to update weights.
- `compute_edge_score()` adaptation to use learned weights.
- Monitoring dashboard/logging for weight sanity.

## 3. Phase v5.2 – Alpha Half-Life Modeling

### 3.1 Goal
Quantify how quickly each pattern/lesson decays after discovery/activation (half-life in days). Use this to down-weight or retire short-lived alphas and prioritize long-lived ones.

### 3.2 Key Steps
1. **Data Collection** – track `edge_raw` time series for each `(pattern_key, action_category, scope subset)` (already partially in recurrence stats). Need to persist richer history (or summary) for curve fitting.
2. **Decay Model** – fit an exponential decay `edge(t) = edge_0 * exp(-lambda * t)`, derive `half_life = ln(2)/lambda`.
3. **Storage** – add `half_life_days`, `decay_rate`, `edge_at_birth`, `edge_current` to stats.
4. **Usage** – treat half-life as another multiplier (`half_life_multiplier = 0.5 + 0.5 * tanh(half_life_days / target)`), or use as QA gate for lesson promotion/deprecation.
5. **Cron/Batch** – run weekly to refit curves using the latest history.

### 3.3 Deliverables
- Historical edge capture (maybe via `edge_history` array capped at N entries or delta snapshots).
- Decay fitting logic (robust to gaps/outliers).
- Stats extension + multiplier in lesson builder.
- QA hooks (flagging short half-life lessons for review).

## 4. Phase v5.3 – Pattern Orthogonalization

### 4.1 Goal
Detect when multiple patterns/lessons are effectively measuring the same underlying behavior and de-duplicate or cluster them into latent factors.

### 4.2 Key Steps
1. **Match Set Representation** – for each braid/lesson, maintain identifiers of trades it matched (or hashed sample sets) so we can compute co-occurrence, grouped by action_category to avoid conflating entries with trims.
2. **Correlation Matrix** – periodically compute pairwise overlap/correlation among braids within the same family and across families.
3. **Clustering** – run hierarchical or threshold-based clustering to form latent factors.
4. **Storage** – new `learning_latent_factors` table capturing pattern keys per cluster, representative pattern, and correlation stats.
5. **Usage** – before activating a new lesson, check if it’s redundant with an existing cluster; optionally roll up into a composite lesson.

### 4.3 Deliverables
- Match-set extraction pipeline (likely via analytics job hitting Supabase).
- Clustering/orthogonalization service.
- Latent factor storage + auditing tools.
- Hooks in lesson builder to consult latent factors before promoting new lessons.

## 5. Dependencies & Tracking
- The v5 phases depend on v4 stats already implemented (time_efficiency, field_coherence, recurrence_score, emergence_score).
- Each phase can be rolled out independently; start with v5.1 and progress sequentially.
- After each phase, update docs + dashboards, and monitor for regressions.

## 6. Next Steps
1. Finalize specs for v5.1 (regime detection granularity, weight learning algorithm, table schema).
2. Implement experimental pipeline and validate weights offline before enabling in production edge formula.
3. Repeat for v5.2 and v5.3 with similar sandbox-first approach.
4. Integrate findings back into LLM research prompts once math layer validates them.

