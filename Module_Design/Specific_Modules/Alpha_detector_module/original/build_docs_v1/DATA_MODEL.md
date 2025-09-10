# Data Model & Storage Design

*Source: [alpha_detector_build_convo.md §12](../alpha_detector_build_convo.md#storage-design--schema-strategy)*

## Overview

The system uses a wide, columns-first approach with three main table types: feature snapshots, market snapshots, and anomaly events. All tables are designed for fast queries, efficient storage, and easy evolution.

## Field Namespace Policy

**Clear separation between system layers:**

| Prefix | Layer | Examples | Purpose |
|--------|-------|----------|---------|
| `psi_*` | Trader outcome composites | `psi_score`, `psi_core` | Trade profitability analysis |
| `sq_*` | Simons signal quality | `sq_score`, `sq_stability` | Signal quality assessment |
| `kr_*` | Kernel/phase resonance | `kr_hbar`, `kr_coherence` | Phase-aligned resonance |
| `det_*` | Selection score & gates | `det_sigma`, `det_kairos` | Detector selection & execution |

## Core Tables

### 0. Evolutionary Metadata Tables

#### detector_registry
```sql
detector_id TEXT PRIMARY KEY        -- Unique detector identifier
version TEXT                        -- Semantic version (semver)
lifecycle_state ENUM(               -- Current lifecycle state
  'experimental', 'active', 'deprecated', 'archived'
)
parent_id TEXT                      -- Parent detector for mutations (nullable)
inputs JSONB                        -- Data requirements
residuals_used JSONB                -- List of residual_ids consumed
hyperparams JSONB                   -- Detector hyperparameters
created_at TIMESTAMPTZ              -- Creation timestamp
deployed_at TIMESTAMPTZ             -- Deployment timestamp
retired_at TIMESTAMPTZ              -- Retirement timestamp
```

#### detector_metrics_daily
```sql
detector_id TEXT                    -- Foreign key to detector_registry
asof_date DATE                      -- Metrics date
pnl FLOAT8                          -- Daily P&L
vol FLOAT8                          -- Daily volatility
ir FLOAT8                           -- Information ratio
t_stat FLOAT8                       -- T-statistic (HAC/Newey-West)
stability FLOAT8                    -- Stability metric
orthogonality_max_abs_corr FLOAT8   -- Max correlation vs active cohort
cost_estimate FLOAT8                -- Estimated trading costs
turnover FLOAT8                     -- Portfolio turnover

-- Enhanced Selection Scores (Phase 1 Addition)
-- Alpha Detector Signal Quality Metrics (sq_* namespace)
sq_score FLOAT8,                    -- Simons signal quality score (0-1)
sq_accuracy FLOAT8,                 -- Signal accuracy (0-1)
sq_precision FLOAT8,                -- Signal precision (0-1)
sq_stability FLOAT8,                -- Signal stability (0-1)
sq_orthogonality FLOAT8,            -- Signal orthogonality (0-1)
sq_cost FLOAT8,                     -- Signal cost (0-1)

-- Kernel Resonance Components (kr_* namespace)
kr_hbar FLOAT8,                     -- Market surprise/structural breaks (0-1)
kr_coherence FLOAT8,                -- Spectral coherence (0-1)
kr_phi FLOAT8,                      -- Field resonance/regime alignment (0-1)
kr_theta FLOAT8,                    -- Context complexity penalty (0-1)
kr_rho FLOAT8,                      -- Recursive depth penalty (0-1)
kr_emergence FLOAT8,                -- Emergence potential (0-1)
kr_novelty FLOAT8,                  -- Novelty in embedding space (0-1)
kr_delta_phi FLOAT8,                -- Kernel resonance (0-1)

-- Detector Selection & Gates (det_* namespace)
det_sigma FLOAT8,                   -- Final selection score (0-1)
det_kairos FLOAT8,                  -- Kairos score (0-1)
det_entrain_r FLOAT8,               -- Entrainment order (0-1)
det_uncert FLOAT8,                  -- Uncertainty variance (0-1)
det_abstained BOOLEAN,              -- Abstention decision

-- State-Space Process Variables (per detector)
kr_phi_state FLOAT8,                -- Field alignment state (0-1)
kr_theta_state FLOAT8,              -- Context complexity state (0-1)
kr_rho_state FLOAT8,                -- Recursive depth state (0-1)

-- Deep Signal Intelligence Features
mx_evidence FLOAT8,                 -- Fused evidence score (0-1)
mx_confirm BOOLEAN,                 -- Binary confirmation flag
mx_expert_contributions JSONB,      -- Individual expert outputs
mx_microtape_hash TEXT,             -- MicroTape input hash
mx_evidence_boost FLOAT8,           -- Evidence boost factor
mx_confirm_rate FLOAT8,             -- Confirmation rate
mx_expert_survival_rate FLOAT8,     -- Expert survival rate
mx_latency_p50 INTEGER,             -- Processing latency (ms)

selection_score FLOAT8,             -- Legacy field (use sigma_select)
dq_status_rollup TEXT               -- Data quality status rollup
universe_overlap_pct FLOAT8         -- Universe overlap percentage
```

#### residual_registry
```sql
residual_id TEXT PRIMARY KEY        -- Unique residual identifier
version TEXT                        -- Semantic version
recipe JSONB                        -- DAG recipe for reproducibility
parent_id TEXT                      -- Parent residual for mutations
validation_r2 FLOAT8                -- Validation R² score
stationarity_test FLOAT8            -- ADF p-value
created_at TIMESTAMPTZ              -- Creation timestamp
```

#### cohort_snapshot
```sql
snapshot_ts TIMESTAMPTZ PRIMARY KEY -- Snapshot timestamp
universe TEXT                       -- Universe name/hash
top_k JSONB                         -- Top K detectors with S_i scores
bottom_k JSONB                      -- Bottom K detectors with S_i scores
promotions JSONB                    -- Detectors promoted this period
retirements JSONB                   -- Detectors retired this period
```

#### dead_branches_log
```sql
detector_id TEXT PRIMARY KEY        -- Failed detector identifier
failure_date TIMESTAMPTZ            -- When it failed
failure_category TEXT               -- [performance|correlation|cost|dq|regime|complexity|leakage]
failure_reason TEXT                 -- Brief factual description
lesson_learned TEXT                 -- What we learned
snapshot_ref TEXT                   -- Link to failure analysis
prevention_strategy TEXT            -- How to avoid this failure
pattern_tags JSONB                  -- Tags for pattern recognition
```

#### backtest_results
```sql
detector_id TEXT                    -- Detector being tested
backtest_ts TIMESTAMPTZ             -- When backtest was run
data_window_start TIMESTAMPTZ       -- Start of test data
data_window_end TIMESTAMPTZ         -- End of test data
ir FLOAT8                           -- Information ratio
sharpe FLOAT8                       -- Sharpe ratio
max_drawdown FLOAT8                 -- Maximum drawdown
win_rate FLOAT8                     -- Win rate
avg_trade_pnl FLOAT8                -- Average trade P&L
total_trades INT4                   -- Total number of trades
backtest_config JSONB               -- Backtest configuration used
```

### 1. features_snapshot
*Source: [alpha_detector_build_convo.md §12.1.A](../alpha_detector_build_convo.md#features_snapshot)*

**Grain**: `(asset_uid, tf, exchange_ts)`
**Primary Key**: `(asset_uid, tf, exchange_ts)`

#### Identity & Membership
```sql
asset_uid INT8           -- Canonical asset ID
symbol TEXT              -- Display symbol
tf ENUM('1m','15m','1h') -- Timeframe
exchange_ts TIMESTAMPTZ  -- Lattice label (bar close)
ingest_ts TIMESTAMPTZ    -- First write time
is_in_universe BOOL      -- Universe membership
is_hot BOOL              -- Hotlist membership
universe_rev INT4        -- Universe revision
```

#### Price/Returns/Volatility
```sql
open, high, low, close DECIMAL(38,12)
mid_close DECIMAL(38,12)
ret_s_30, ret_m_1, ret_m_5, ret_m_15 DECIMAL(38,12)
ret_abs_m_1 DECIMAL(38,12)
rv_m_1 DECIMAL(38,12)                    -- Realized vol proxy
atr_proxy_m_1 DECIMAL(38,12)             -- ATR proxy
```

#### Flow/CVD
```sql
v_buy_m_1, v_sell_m_1, v_total_m_1 DECIMAL(38,12)
trade_count_m_1 INT4
cvd_delta_m_1 DECIMAL(38,12)
cvd_level DECIMAL(38,12)                 -- Daily anchored
cvd_slope_m_5 DECIMAL(38,12)
```

#### Positioning (OI & Liquidations)
```sql
oi_open, oi_close, oi_min, oi_max DECIMAL(38,12)
oi_delta_m_5, oi_roc_m_5 DECIMAL(38,12)
liq_count_m_5 INT4
liq_notional_m_5 DECIMAL(38,12)
oi_staleness_ms INT4
```

#### Perp State (Funding & Basis)
```sql
funding_h_1 DECIMAL(38,12)
basis_bp_m_5 DECIMAL(38,12)
time_to_next_funding_sec INT4
```

#### Microstructure
```sql
spread_mean_m_1, spread_p95_m_1 DECIMAL(38,12)
obi_top5_mean_m_1 DECIMAL(38,12)
depth_top5_quote_median_m_1 DECIMAL(38,12)
```

#### Momentum Indicators (Phase 1 Addition)
```sql
rsi_14, rsi_21, rsi_50 DECIMAL(38,12)
macd_line, macd_signal, macd_histogram DECIMAL(38,12)
stoch_k_14, stoch_d_14 DECIMAL(38,12)
roc_10, roc_20 DECIMAL(38,12)
adx_14, adx_21 DECIMAL(38,12)
hma_100 DECIMAL(38,12)
atr_14, atr_21 DECIMAL(38,12)
```

#### Swing Detection (Phase 1 Addition)
```sql
swing_highs JSONB                    -- Array of swing high points
swing_lows JSONB                     -- Array of swing low points
swing_high_times JSONB               -- Timestamps of swing highs
swing_low_times JSONB                -- Timestamps of swing lows
current_swing_high DECIMAL(38,12)    -- Most recent swing high
current_swing_low DECIMAL(38,12)     -- Most recent swing low
swing_validation_pending BOOL        -- Swings awaiting confirmation
```

#### Advanced Trend Features (Phase 1 Addition)
```sql
hma_100_slope DECIMAL(38,12)        -- HMA slope (trend direction)
atr_percentile_252 DECIMAL(38,12)    -- ATR percentile over 252 periods
trend_strength DECIMAL(38,12)        -- Composite trend strength
volatility_regime TEXT               -- 'low'|'medium'|'high'
```

#### Level Detection (Phase 2 Addition)
```sql
prior_day_high, prior_day_low DECIMAL(38,12)
weekly_high, weekly_low DECIMAL(38,12)
vwap_session, vwap_weekly DECIMAL(38,12)
level_proximity_score DECIMAL(38,12)
```

#### Breadth Features (Phase 2 Addition)
```sql
pct_above_ma50, pct_above_ma200 DECIMAL(38,12)
nh_nl INT4                           -- New highs minus new lows
advance_decline_ratio DECIMAL(38,12)
breadth_composite DECIMAL(38,12)
```

#### Residual Features (Phase 1 Addition)
```sql
-- Price/Returns Residuals
z_ret_residual_m_1, ret_prediction_m_1, ret_prediction_std_m_1 DECIMAL(38,12)
q_ret_residual_m_1 DECIMAL(38,12)

-- Volume Residuals
z_vol_residual_m_1, vol_prediction_m_1, vol_prediction_std_m_1 DECIMAL(38,12)
q_vol_residual_m_1 DECIMAL(38,12)

-- OI Residuals
z_oi_residual_m_5, oi_prediction_m_5, oi_prediction_std_m_5 DECIMAL(38,12)
q_oi_residual_m_5 DECIMAL(38,12)

-- Spread Residuals
z_spread_residual_m_1, spread_prediction_m_1, spread_prediction_std_m_1 DECIMAL(38,12)

-- Basis Residuals
z_basis_residual_m_5, basis_prediction_m_5, basis_prediction_std_m_5 DECIMAL(38,12)

-- Momentum Residuals
z_rsi_residual_14, z_macd_residual, z_stoch_residual_14 DECIMAL(38,12)
rsi_prediction_14, macd_prediction, stoch_prediction_14 DECIMAL(38,12)
momentum_prediction_std DECIMAL(38,12)
q_rsi_residual_14, q_macd_residual, q_stoch_residual_14 DECIMAL(38,12)

-- Cross-Sectional Residuals
z_cross_sectional_residual_m_1, cross_sectional_prediction_m_1 DECIMAL(38,12)
factor_loadings JSONB
residual_rank DECIMAL(38,12)

-- Time-Series Residuals
z_kalman_residual_m_1, kalman_state, kalman_innovation DECIMAL(38,12)
kalman_prediction_std DECIMAL(38,12)

-- Order Flow Residuals
z_flow_residual_m_1, flow_prediction_m_1, flow_prediction_std_m_1 DECIMAL(38,12)
flow_features JSONB

-- Basis/Carry Residuals
z_carry_residual_m_5, carry_prediction_m_5, carry_prediction_std_m_5 DECIMAL(38,12)
carry_features JSONB

-- Lead-Lag Network Residuals
z_network_residual_m_1, network_prediction_m_1, network_prediction_std_m_1 DECIMAL(38,12)
network_features JSONB

-- Breadth/Market Mode Residuals
z_breadth_residual_m_5, breadth_prediction_m_5, breadth_prediction_std_m_5 DECIMAL(38,12)
market_mode TEXT

-- Volatility Surface Residuals
z_vol_surface_residual_m_1, vol_surface_prediction_m_1, vol_surface_prediction_std_m_1 DECIMAL(38,12)
vol_surface_features JSONB

-- Seasonality Residuals
z_seasonal_residual_m_1, seasonal_prediction_m_1, seasonal_prediction_std_m_1 DECIMAL(38,12)
seasonal_features JSONB
```

#### Cheap Flags
```sql
is_vol_spike_m_1 BOOL
is_price_spike_up_m_1, is_price_spike_down_m_1 BOOL
is_oi_spike_up_m_5, is_oi_spike_down_m_5 BOOL
is_spread_stress_m_1 BOOL
is_liq_cluster_m_5 BOOL
is_divergence_bullish_m_5, is_divergence_bearish_m_5 BOOL
```

#### Pattern Detection Features (Phase 1 Addition)
```sql
-- Candlestick Patterns
is_doji, is_hammer, is_shooting_star BOOL
is_bull_engulfing, is_bear_engulfing BOOL
is_harami_bull, is_harami_bear BOOL
is_three_white_soldiers, is_three_black_crows BOOL

-- Support/Resistance Detection
near_support, near_resistance BOOL
support_breakout, resistance_breakout BOOL
support_reclaim, resistance_reclaim BOOL
level_strength, level_age, level_touches DECIMAL(38,12)

-- Chart Patterns
is_falling_wedge, is_rising_wedge BOOL
is_bull_flag, is_bear_flag BOOL
is_ascending_triangle, is_descending_triangle, is_symmetrical_triangle BOOL
is_head_shoulders, is_inverse_head_shoulders BOOL
is_double_top, is_double_bottom BOOL

-- Diagonal Trend Line Detection
diagonal_support_slope, diagonal_resistance_slope DECIMAL(38,12)
diagonal_channel_width DECIMAL(38,12)
diagonal_support_break, diagonal_resistance_break, diagonal_channel_break BOOL
diagonal_line_strength, diagonal_touches, diagonal_age DECIMAL(38,12)
diagonal_support_distance, diagonal_resistance_distance DECIMAL(38,12)
diagonal_convergence_rate DECIMAL(38,12)

-- Pattern Confirmation
pattern_volume_confirmation, pattern_time_confirmation BOOL
pattern_strength_score, pattern_completion_pct DECIMAL(38,12)
pattern_target_price, pattern_stop_loss DECIMAL(38,12)
pattern_risk_reward DECIMAL(38,12)

-- Level Detection
prior_day_high, prior_day_low DECIMAL(38,12)
weekly_high, weekly_low DECIMAL(38,12)
monthly_high, monthly_low DECIMAL(38,12)
vwap_session, vwap_weekly, vwap_monthly DECIMAL(38,12)
round_number_levels, fibonacci_levels, pivot_points JSONB

-- Pattern History Storage
pattern_history JSONB                    -- Array of recent patterns detected
swing_point_history JSONB               -- Array of swing highs/lows
level_history JSONB                     -- Array of significant levels
breakout_history JSONB                  -- Array of recent breakouts
pattern_performance JSONB               -- Array of pattern success rates

#### Regime Classification Features (Phase 1 Addition)
```sql
-- Volatility Regime
atr_percentile_252 DECIMAL(38,12)       -- ATR percentile over 252 periods (0-100)
volatility_regime TEXT                  -- "low" | "medium" | "high"
vol_regime_confidence DECIMAL(38,12)    -- Confidence in volatility regime (0-1)

-- Trend Regime
adx_14, adx_21 DECIMAL(38,12)           -- Average Directional Index (0-100)
trend_regime TEXT                       -- "trending" | "ranging"
trend_direction TEXT                    -- "up" | "down" | "sideways"
trend_strength DECIMAL(38,12)           -- Composite trend strength score (0-1)

-- Session Phase
session_phase TEXT                      -- "asia" | "europe" | "us" | "overlap"
time_of_day INT2                        -- Hour of day (0-23)
day_of_week INT2                        -- Day of week (0-6)
is_market_open BOOL                     -- Active trading hours

-- Market Regime
market_regime TEXT                      -- Composite market regime classification
regime_confidence DECIMAL(38,12)        -- Confidence in regime classification (0-1)
regime_duration INT4                    -- Time in current regime (minutes)
regime_transition_prob DECIMAL(38,12)   -- Probability of regime transition (0-1)

-- Liquidity Regime
liquidity_regime TEXT                   -- "high" | "medium" | "low"
spread_regime TEXT                      -- Classification based on spread percentiles
volume_regime TEXT                      -- Classification based on volume percentiles
depth_regime TEXT                       -- Classification based on order book depth
```

#### Divergence Detection Features (Phase 1 Addition)
```sql
-- Hidden Momentum Divergence
hidden_momentum_bull_strength, hidden_momentum_bear_strength DECIMAL(38,12)
hidden_momentum_trigger BOOL
hidden_momentum_context_score DECIMAL(38,12)

-- Classic RSI/MACD Divergence
price_rsi_divergence_strength, price_macd_divergence_strength DECIMAL(38,12)
rsi_divergence_type, macd_divergence_type TEXT

-- Delta/Volume Divergence
delta_volume_divergence_strength DECIMAL(38,12)
cumulative_delta_divergence DECIMAL(38,12)
volume_absorption_score DECIMAL(38,12)
```

#### Normalized Pattern Features
```sql
z_pattern_strength, z_level_proximity, z_volume_confirmation DECIMAL(38,12)
q_pattern_strength, q_level_proximity DECIMAL(38,12)
```

#### Data Quality
```sql
dq_status ENUM('ok','partial','stale')
ingest_lag_ms INT2
dropped_ticks INT2
book_staleness_ms INT2
warmup BOOL
```

#### Provenance
```sql
feature_pack TEXT
pack_rev INT2
source TEXT('ws'|'candle_snapshot'|'backfill')
```

#### Extensibility
```sql
extras_json JSONB  -- Experimental fields
```

### 2. market_snapshot
*Source: [alpha_detector_build_convo.md §12.1.B](../alpha_detector_build_convo.md#market_snapshot)*

**Grain**: `(tf, exchange_ts)`
**Primary Key**: `(tf, exchange_ts)`

```sql
tf ENUM('1m','15m','1h')
exchange_ts TIMESTAMPTZ
leader TEXT
dominance_share DECIMAL(38,12)
shock_count_5s INT2
rs_top JSONB(≤5)           -- Top 5 by RS
rs_bottom JSONB(≤5)        -- Bottom 5 by RS
return_dispersion_m_5 DECIMAL(38,12)
vol_dispersion_m_5 DECIMAL(38,12)
excluded_count INT2
approx BOOL
time_to_next_funding_sec INT4
dq_status ENUM('ok','partial','stale')
universe_rev INT4
```

### 3. anomaly_event
*Source: [alpha_detector_build_convo.md §12.1.C](../alpha_detector_build_convo.md#anomaly_event)*

**Grain**: Append-only
**Primary Key**: `(event_id UUID)`

```sql
event_id UUID PRIMARY KEY
emitted_at TIMESTAMPTZ
exchange_ts TIMESTAMPTZ
asset_uid INT8
symbol TEXT
tf ENUM('1m','15m','1h')
class TEXT('spike'|'shift'|'quadrant'|'divergence'|'synchrony'|'rotation')
subtype TEXT
severity INT2
is_in_universe BOOL
is_hot BOOL
universe_rev INT4
feature_pack TEXT
detector_pack TEXT
config_hash TEXT
git_commit TEXT
universe_policy_rev INT4
source_lag_ms INT4
clock_skew_ms INT4
replay_of BOOL
payload JSONB              -- Complete event JSON
```

## State & Registry Tables

### baseline_state
*Source: [alpha_detector_build_convo.md §12.2](../alpha_detector_build_convo.md#baseline_state)*

```sql
asset_uid INT8
tf ENUM('1m','15m','1h')
feature_name TEXT
mu DECIMAL(38,12)           -- Robust mean
sigma DECIMAL(38,12)        -- Robust scale
n_samples INT4
updated_at TIMESTAMPTZ
quantile_state BYTEA        -- Quantile sketch state
PRIMARY KEY (asset_uid, tf, feature_name)
```

### feature_registry
```sql
feature_name TEXT PRIMARY KEY
window TEXT
formula TEXT
inputs TEXT[]
units TEXT
pack TEXT
added_at TIMESTAMPTZ
deprecated_at TIMESTAMPTZ
notes TEXT
```

### detector_registry
```sql
detector_id TEXT PRIMARY KEY
version TEXT
inputs TEXT[]
preconditions TEXT[]
trigger TEXT
cooldown_sec INT4
half_life_sec INT4
severity_weights JSONB
enabled BOOL
added_at TIMESTAMPTZ
deprecated_at TIMESTAMPTZ
```

### universe_audit
```sql
rev INT4 PRIMARY KEY
ts TIMESTAMPTZ
added TEXT[]
removed TEXT[]
reasons JSONB
params JSONB
```

### hotlist_state
```sql
asset_uid INT8 PRIMARY KEY
hot_reason ENUM('vol_spike'|'oi_spike'|'basis_jolt'|'manual')
hot_started_at TIMESTAMPTZ
hot_expires_at TIMESTAMPTZ
```

## Indexes

### features_snapshot
- `PRIMARY KEY (asset_uid, tf, exchange_ts)`
- `(asset_uid, exchange_ts DESC)`
- `PARTIAL INDEX ON (dq_status != 'ok')`
- `PARTIAL INDEX ON (is_hot = true)`

### anomaly_event
- `(asset_uid, exchange_ts DESC)`
- `(class, subtype, emitted_at DESC)`
- `GIN ON payload`

## Partitioning Strategy

*Source: [alpha_detector_build_convo.md §12.4](../alpha_detector_build_convo.md#retention--pruning)*

- **Partition by**: `(tf, month)`
- **1m**: Keep ~90 days
- **15m**: Keep ~1 year  
- **1h**: Keep ~3 years
- **Compression**: Enable after 7 days

## Data Types & Precision

- **Prices/Ratios**: `DECIMAL(38,12)` or `DOUBLE` with care
- **Counts**: `INT4`/`INT2`
- **Timestamps**: `TIMESTAMPTZ` (UTC)
- **Enums**: For `tf`, `dq_status`, `class`, `subtype`

## Idempotency & Conflict Policy

*Source: [alpha_detector_build_convo.md §12.5](../alpha_detector_build_convo.md#idempotency--conflict-policy)*

- **features_snapshot**: `UPSERT` on `(asset_uid, tf, exchange_ts)`
- **market_snapshot**: `UPSERT` on `(tf, exchange_ts)`
- **anomaly_event**: `INSERT ONLY` (duplicates rejected by PK)

## Query Patterns

*Source: [alpha_detector_build_convo.md §12.7](../alpha_detector_build_convo.md#query-patterns-design-for-them)*

```sql
-- Recent state per asset
SELECT * FROM features_snapshot 
WHERE asset_uid = ? AND tf = '1m' 
ORDER BY exchange_ts DESC LIMIT 120;

-- Event search by class/subtype
SELECT * FROM anomaly_event 
WHERE class = ? AND subtype = ? 
AND emitted_at BETWEEN ? AND ?;

-- Cross-section join
SELECT * FROM features_snapshot f
JOIN market_snapshot m ON f.exchange_ts = m.exchange_ts
WHERE f.exchange_ts = now_floor();
```

## Evolution Strategy

*Source: [alpha_detector_build_convo.md §12.6](../alpha_detector_build_convo.md#overflow--promotion)*

1. **Experimental fields**: Land in `extras_json`
2. **Promotion**: Move to typed columns in next Feature Pack minor
3. **Backfill**: Forward only (no historical retrofits)
4. **Deprecation**: Mark in registry, keep nullable until major version

## Curator Tables (Phase 4 Addition)

*Source: [alpha_detector_build_convo.md §12.2](../alpha_detector_build_convo.md#state--registry-tables)*

```sql
-- Curator run tracking
CREATE TABLE curator_runs (
    run_id UUID PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    inputs_hash VARCHAR(64) NOT NULL,
    config_hash VARCHAR(64) NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Curator insights (append-only)
CREATE TABLE insights (
    insight_id UUID PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL,
    scope VARCHAR(64) NOT NULL, -- 'global', 'asset', 'detector_class'
    kind VARCHAR(64) NOT NULL, -- 'drift', 'budget', 'dq', 'co_occurrence', 'performance'
    evidence JSONB NOT NULL,
    recommendation JSONB,
    author VARCHAR(128),
    status VARCHAR(32) DEFAULT 'active', -- 'active', 'resolved', 'superseded'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Configuration proposals
CREATE TABLE config_proposals (
    proposal_id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    target VARCHAR(64) NOT NULL, -- 'detector_pack', 'feature_pack', 'universe_policy'
    diff JSONB NOT NULL,
    rationale TEXT NOT NULL,
    evidence JSONB,
    status VARCHAR(32) DEFAULT 'proposed', -- 'proposed', 'applied', 'rejected', 'superseded'
    applied_at TIMESTAMPTZ,
    applied_by VARCHAR(128),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Replay results
CREATE TABLE replay_results (
    proposal_id UUID NOT NULL REFERENCES config_proposals(proposal_id),
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    metrics JSONB NOT NULL, -- event counts, severity distributions, etc.
    passed BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (proposal_id, window_start, window_end)
);

-- Weekly reports (optional)
CREATE TABLE weekly_reports (
    report_id UUID PRIMARY KEY,
    week_start TIMESTAMPTZ NOT NULL,
    week_end TIMESTAMPTZ NOT NULL,
    summary TEXT NOT NULL,
    key_insights JSONB,
    config_changes JSONB,
    performance_metrics JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Trading Feedback Tables (Phase 5 Addition)

*Source: [alpha_detector_build_convo.md §14.7](../alpha_detector_build_convo.md#artifacts-tables)*

```sql
-- Individual signal performance tracking
CREATE TABLE signal_performance (
    signal_id VARCHAR(64) PRIMARY KEY,
    event_id UUID NOT NULL REFERENCES anomaly_event(event_id),
    signal_type VARCHAR(64) NOT NULL, -- 'pattern.diagonal_support_break', 'div.price_rsi_bear_m_5', etc.
    direction VARCHAR(16) NOT NULL, -- 'bullish', 'bearish'
    price_level DECIMAL(20,8) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    
    -- Trading outcome
    action_taken VARCHAR(32), -- 'long_entry', 'short_entry', 'no_action', 'rejected'
    entry_price DECIMAL(20,8),
    exit_price DECIMAL(20,8),
    pnl DECIMAL(20,8),
    hold_time_minutes INTEGER,
    max_drawdown DECIMAL(20,8),
    max_favorable DECIMAL(20,8),
    
    -- Market context
    volatility_regime VARCHAR(16), -- 'low', 'medium', 'high'
    trend_direction VARCHAR(16), -- 'up', 'down', 'sideways'
    volume_regime VARCHAR(16), -- 'low', 'medium', 'high'
    
    -- Performance metrics
    accuracy DECIMAL(5,4), -- 0.0 to 1.0
    precision DECIMAL(5,4),
    recall DECIMAL(5,4),
    f1_score DECIMAL(5,4),
    sharpe_ratio DECIMAL(8,4),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Detector performance aggregation
CREATE TABLE detector_performance (
    detector_id VARCHAR(64) NOT NULL,
    time_window TIMESTAMPTZ NOT NULL,
    market_regime VARCHAR(16) NOT NULL,
    
    -- Performance metrics
    accuracy DECIMAL(5,4), -- 0.0 to 1.0
    precision DECIMAL(5,4),
    recall DECIMAL(5,4),
    f1_score DECIMAL(5,4),
    sharpe_ratio DECIMAL(8,4),
    max_drawdown DECIMAL(5,4),
    win_rate DECIMAL(5,4),
    avg_win DECIMAL(20,8),
    avg_loss DECIMAL(20,8),
    
    -- Sample sizes
    total_signals INTEGER,
    profitable_signals INTEGER,
    losing_signals INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (detector_id, time_window, market_regime)
);

-- Database triggers for performance analysis
CREATE OR REPLACE FUNCTION trigger_curator_performance_analysis()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate performance metrics
    UPDATE signal_performance 
    SET 
        accuracy = CASE WHEN (direction = 'bullish' AND pnl > 0) OR (direction = 'bearish' AND pnl < 0) THEN 1.0 ELSE 0.0 END,
        precision = CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END,
        recall = CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END,
        f1_score = CASE WHEN pnl > 0 AND ((direction = 'bullish' AND pnl > 0) OR (direction = 'bearish' AND pnl < 0)) THEN 1.0 ELSE 0.0 END
    WHERE signal_id = NEW.signal_id;
    
    -- Notify Curator of new performance data
    PERFORM pg_notify('curator_performance_update', NEW.signal_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER signal_performance_trigger
    AFTER INSERT ON signal_performance
    FOR EACH ROW
    EXECUTE FUNCTION trigger_curator_performance_analysis();

-- Detector performance aggregation trigger
CREATE OR REPLACE FUNCTION aggregate_detector_performance()
RETURNS TRIGGER AS $$
DECLARE
    detector_id VARCHAR(64);
    market_regime VARCHAR(16);
    time_window TIMESTAMPTZ;
BEGIN
    -- Extract detector ID from signal type
    detector_id = split_part(NEW.signal_type, '.', 1) || '.' || split_part(NEW.signal_type, '.', 2);
    market_regime = NEW.volatility_regime || '_' || NEW.trend_direction;
    time_window = date_trunc('hour', NEW.timestamp);
    
    -- Upsert aggregated performance
    INSERT INTO detector_performance (
        detector_id, time_window, market_regime,
        total_signals, profitable_signals, losing_signals,
        accuracy, precision, recall, f1_score
    )
    SELECT 
        detector_id, time_window, market_regime,
        COUNT(*), 
        COUNT(*) FILTER (WHERE pnl > 0),
        COUNT(*) FILTER (WHERE pnl <= 0),
        AVG(accuracy), AVG(precision), AVG(recall), AVG(f1_score)
    FROM signal_performance 
    WHERE signal_type LIKE detector_id || '%' 
    AND volatility_regime = split_part(market_regime, '_', 1)
    AND trend_direction = split_part(market_regime, '_', 2)
    AND date_trunc('hour', timestamp) = time_window
    ON CONFLICT (detector_id, time_window, market_regime) 
    DO UPDATE SET
        total_signals = EXCLUDED.total_signals,
        profitable_signals = EXCLUDED.profitable_signals,
        losing_signals = EXCLUDED.losing_signals,
        accuracy = EXCLUDED.accuracy,
        precision = EXCLUDED.precision,
        recall = EXCLUDED.recall,
        f1_score = EXCLUDED.f1_score;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER detector_performance_trigger
    AFTER INSERT ON signal_performance
    FOR EACH ROW
    EXECUTE FUNCTION aggregate_detector_performance();

-- Performance monitoring view
CREATE VIEW detector_performance_summary AS
SELECT 
    detector_id,
    time_window,
    market_regime,
    total_signals,
    profitable_signals,
    losing_signals,
    accuracy,
    precision,
    recall,
    f1_score,
    win_rate,
    avg_win,
    avg_loss
FROM detector_performance
ORDER BY time_window DESC, accuracy DESC;

-- Deep Signal Intelligence Tables
CREATE TABLE dsi_experts (
    expert_id TEXT PRIMARY KEY,
    expert_type TEXT NOT NULL,  -- 'fsm', 'classifier', 'anomaly', 'divergence'
    spec JSONB NOT NULL,        -- Expert specification
    version TEXT NOT NULL,
    latency_p50 REAL,           -- 50th percentile latency
    auc_oos REAL,               -- Out-of-sample AUC
    contrib_det_sigma REAL,     -- Contribution to det_sigma
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE dsi_annotations (
    id UUID PRIMARY KEY,
    asset_uid INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    mx_evidence REAL NOT NULL,      -- Fused evidence score
    mx_confirm BOOLEAN NOT NULL,    -- Binary confirmation
    expert_contributions JSONB,     -- Individual expert outputs
    microtape_hash TEXT,           -- Hash of input MicroTape
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dsi_annotations_asset_time ON dsi_annotations(asset_uid, timestamp);
CREATE INDEX idx_dsi_annotations_evidence ON dsi_annotations(mx_evidence);

-- Trading Plan Tables
CREATE TABLE trading_plans (
    id UUID PRIMARY KEY,
    detector_id UUID REFERENCES detector_registry(id),
    symbol TEXT NOT NULL,
    signal_strength FLOAT8 NOT NULL,     -- Signal confidence [0,1]
    direction TEXT NOT NULL,             -- 'long', 'short', 'neutral'
    entry_conditions JSONB NOT NULL,     -- Trigger conditions
    entry_price FLOAT8,                  -- Target entry price
    position_size FLOAT8,                -- Position size as % of portfolio
    stop_loss FLOAT8,                    -- Stop loss price
    take_profit FLOAT8,                  -- Take profit price
    time_horizon TEXT NOT NULL,          -- '1m', '5m', '15m', '1h', '4h', '1d'
    risk_reward_ratio FLOAT8,            -- Risk/reward ratio
    confidence_score FLOAT8 NOT NULL,    -- Overall confidence [0,1]
    microstructure_evidence JSONB,       -- DSI evidence
    regime_context JSONB,                -- Market regime context
    execution_notes TEXT,                -- Execution instructions
    valid_until TIMESTAMP NOT NULL,      -- Plan expiration
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trading_plans_detector ON trading_plans(detector_id);
CREATE INDEX idx_trading_plans_symbol ON trading_plans(symbol);
CREATE INDEX idx_trading_plans_valid_until ON trading_plans(valid_until);
```

---

*For complete storage specifications and schemas, see [alpha_detector_build_convo.md §12](../alpha_detector_build_convo.md#storage-design--schema-strategy)*
