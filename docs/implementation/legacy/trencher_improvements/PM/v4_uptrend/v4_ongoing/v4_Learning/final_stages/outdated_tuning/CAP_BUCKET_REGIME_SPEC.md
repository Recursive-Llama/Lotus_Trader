# Cap-Bucket Regime Spec (Draft)

## 0. Purpose

Extend the SPIRAL phase framework so our regime signals reflect the actual low-cap universe we trade. We add market-cap cohort tracking (nano → large), compute bucket-specific residual scores, and wire those signals into PM levers (A/E) plus downstream consumers.

## 1. Market-Cap Buckets

| Bucket | Market Cap (USD) | Notes |
| --- | --- | --- |
| `nano` | `< $100k` | Highly illiquid; only include if ≥ min population |
| `micro` | `$100k – $5m` | Primary hunting ground |
| `mid` | `$5m – $50m` | Still low-float but more liquid |
| `big` | `$50m – $500m` | Crossover names |
| `large` | `$500m – $1b` | Upper bound of lowcap mandate |
| `xl` | `> $1b` | Reference only (not part of composite) |

- Nightly tagging job writes `token_cap_bucket(token_id, bucket, mc_usd, updated_at)`.
- Skip scoring a bucket if it has < `bucket_min_members` tradable tokens (configurable, default 8) or if median volume < threshold.
- `xl` bucket is computed for telemetry but excluded from low-cap composite and A/E multipliers.

## 2. Data Pipeline

1. **Token metadata**  
   - Source: existing OHLC → metadata ingest (`rollup_ohlc`, etc.).  
   - Responsibilities: update market cap, circulating supply, and assign bucket per token.  
   - Storage: `token_cap_bucket` table (new) with indexes on `bucket` and `updated_at`.

2. **Bucket return series**  
   - For each bucket with sufficient members:  
     - Build hourly closes by equal-weight (default) or liquidity-weight average of members.  
     - Compute log returns `r_bucket`.  
     - Compute residuals vs BTC (`r_bucket - r_btc`) and vs alt basket (`r_bucket - r_alt`).  
     - Cache 7 days of hourly data for SPIRAL scoring.

3. **Composite low-cap series**  
   - Weighted blend of `nano`→`large` buckets reflecting trading focus (config: `composite_bucket_weights`).  
   - Exclude `xl`.  
   - Acts as the “portfolio” stream for global macro/meso/micro phases.

4. **Scoring (per bucket + composite)**  
   - Reuse SPIRAL functions: `stream_metrics → compute_lens_scores → compute_phase_scores`.  
   - Horizons: `micro`, `meso`, `macro` (same presets as today).  
   - Outputs: `phase`, `score`, `slope`, `curvature`, `delta`, `confidence`, `population_count`.

5. **Persistence**  
   - `phase_state` (existing): now stores composite low-cap phases (replacing NAV-only input).  
   - `phase_state_bucket` (new):  
     ```sql
     CREATE TABLE phase_state_bucket (
       bucket TEXT NOT NULL CHECK (bucket IN ('nano','micro','mid','big','large','xl')),
       horizon TEXT NOT NULL CHECK (horizon IN ('macro','meso','micro')),
       ts TIMESTAMPTZ NOT NULL,
       phase TEXT NOT NULL,
       score DOUBLE PRECISION NOT NULL,
       slope DOUBLE PRECISION,
       curvature DOUBLE PRECISION,
       delta_res DOUBLE PRECISION,
       confidence DOUBLE PRECISION,
       population_count INTEGER NOT NULL,
       PRIMARY KEY (bucket, horizon, ts)
     );
     ```
   - No historical backfill required; start recording prospectively.

## 3. Regime Context Consumption

`_get_regime_context()` now returns:
```json
{
  "macro": {...},    // composite low-cap phase (existing shape)
  "meso": {...},
  "micro": {...},
  "bucket_phases": {
    "nano": {"phase": "Good", "score": 0.62, "slope": 0.11, "confidence": 0.78},
    ...
  },
  "bucket_rank": ["micro","nano","mid","big","large","xl"],  // by score desc
  "bucket_population": {"micro": 42, ...}
}
```

- Decision makers, collectors, and research layers can now see which cohort leads.  
- Rotation detection (optional): when ranking order changes, emit `bucket_rotation` events for telemetry.
- Pattern scope logging consumes `regime` (macro/meso/micro composite) and `bucket` from this snapshot so every action inherits the same canonical context.

### 3.1 Regime Label Format

- Every consumer (logging, overrides, lessons) receives `regime_label = "macro=<phase>|meso=<phase>|micro=<phase>|bucket_leader=<bucket>"`.
- `<phase>` is always one of `{Good, Recover, Dip, Double-Dip, Oh-Shit, Euphoria, Chop}` (case-stable, camel-cased).  
  - Example: `macro=Recover|meso=Dip|micro=Good|bucket_leader=micro`.
- `<bucket_leader>` mirrors the first element of `bucket_rank` for that snapshot (e.g., `micro`, `nano`).
- We also expose `bucket_rank_position` per bucket so downstream scope logging can record the traded token’s position in the ladder (1 = leader). Example: if `token_cap_bucket = mid` and `bucket_rank = ["micro","nano","mid",...]`, then `bucket_rank_position = 3`.
- If any phase is missing, we emit the placeholder `Unknown` to keep the label parseable.
- This exact label is what `PATTERN_KEY_SCOPE_SPEC.md` refers to for the `regime` scope dimension, ensuring consistent matching across systems.

## 4. Lever Integration (A/E)

1. **Config (`pm_config`)**  
   ```json
   {
     "bucket_order_multipliers": {
       "rank_adjustments": {
         "1": 0.12,
         "2": 0.06,
         "3": 0.02,
         "4": -0.02,
         "5": -0.06,
         "6": -0.12
       },
       "slope_weight": 0.4,
       "min_confidence": 0.4
     },
     "bucket_phase_min_population": 8,
     "composite_bucket_weights": {
       "nano": 0.15,
       "micro": 0.30,
       "mid": 0.25,
       "big": 0.20,
       "large": 0.10
     }
   }
   ```
   - Ranks beyond present buckets default to 0.  
   - `slope_weight` amplifies adjustments when slope is strongly positive/negative.  
   - All values adjustable via Supabase config.

2. **Per-position multiplier**  
   - Determine position’s bucket from metadata.  
   - Find bucket rank + slope from `bucket_phases`.  
   - Compute `bucket_multiplier = 1 + rank_adjustment[rank] + slope_weight * clipped_slope`.  
   - Clamp multiplier to `[bucket_multiplier_min, bucket_multiplier_max]` (config).  
   - Apply to `A` (add appetite) and invert for `E` (exit assertiveness). The resulting `A_mode` / `E_mode` (patient/normal/aggressive) is what we log into the pattern scope. Example:  
     - `A = A * bucket_multiplier`  
     - `E = E / bucket_multiplier` (or `E = E * (2 - bucket_multiplier)` for smoother effect).

3. **Global bias**  
   - Optionally compute a weighted average of bucket multipliers (exposure-weighted) to nudge overall A/E baseline.

## 5. Interfaces & Events

- **Regime API**: expose `bucket_phases` via Supabase RPC or cached JSON for LLM layer and dashboards.  
- **Events** (optional, config-driven):  
  - `bucket_rotation`: fired when ranking order changes; payload includes old/new order, slope deltas.  
  - `bucket_extreme`: fired when a bucket hits `Euphoria` or `Oh-Shit` with high confidence.

## 6. Rollout Plan

1. Implement metadata tagging + ensure OHLC ingest stores MC per token.  
2. Add bucket return series + scoring to `tracker` job (behind feature flag).  
3. Create `phase_state_bucket` and start writing prospective data.  
4. Update `_get_regime_context` to include bucket info.  
5. Update `compute_levers` to read multipliers from `pm_config` and apply per-position adjustments (defaults set to near-neutral).  
6. Validate live metrics for ~1–2 weeks, then gradually increase multiplier strengths via config.  
7. Document signals for LLM prompts and dashboards.

## 7. Future Extensions

- Additional groupings (chains, semantic tags) can plug into the same pipeline by treating each grouping as another “bucket.”  
- Meta-learning (v5.1) can ingest `bucket_phases` as features when learning regime-specific weights.  
- Could add “sector composite” phases (e.g., `solana_lowcaps`) using identical logic once watchlists are ready.


