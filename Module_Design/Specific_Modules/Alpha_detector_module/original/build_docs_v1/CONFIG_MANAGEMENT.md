# Configuration Management

*Source: [alpha_detector_build_convo.md §19](../alpha_detector_build_convo.md#configuration-management)*

## Overview

The detector uses a declarative configuration system with versioned packs, runtime updates, and complete audit trails. All configurations are validated, versioned, and traceable.

## Lifecycle Policy & Gates

### States: experimental → active → deprecated → archived

**Global Prerequisites:**
- `min_samples_bars`: 2000 (per asset×tf) before any scoring is official
- `dq_status` must be ok for ≥95% of samples in the eval window

**Promotion Gate (experimental → active):**
- Window: rolling 60d
- `S_i ≥ τ_promote = 0.35`
- `orthogonality_max_abs_corr ≤ 0.6` vs current active set
- `turnover ≤ turnover_cap` (configurable)

**Deprecation Gate (active → deprecated):**
- Window: rolling 30d
- `S_i ≤ τ_deprecate = 0.05` for 15/30 days OR
- `dq_status` breaches >10% days

**Archive Gate (deprecated → archived):**
- After 60d with no recovery above `S_i ≥ 0.20`

**Reseeding Cadence:**
- Weekly: mutate top-K=10 actives → spawn n_children=3 each

**Mutation Knobs:**
- `jitter`: Gaussian noise on hyperparams (σ from config)
- `swap_inputs`: alternate residual stacks
- `recombine`: weighted sum of two survivor signal transforms

**Universe Policy & Hysteresis:**
- Maintain Top-N universe + hotlist_ttl_days
- Gate detectors on is_in_universe OR is_hot; exit hysteresis 3×ttl

All thresholds are configurable; defaults are provided here for reproducibility.

## Kernel Resonance Configuration (Phase 1 Addition)

**Enhanced Selection System**: Two-layer detector selection with configurable weights and thresholds.

```yaml
kernel_resonance:
  # Geometric blend weights
  u: 0.6                    # Weight for signal quality core (sq_score)
  
  # Phase resonance weights
  alpha: 1.0                # Field resonance (kr_phi) weight
  beta: 0.8                 # Novelty (kr_novelty) weight  
  gamma: 0.8                # Emergence (kr_emergence) weight
  delta: 0.7                # Context complexity penalty (kr_theta) weight
  epsilon: 0.7              # Depth complexity penalty (kr_rho) weight
  
  # Selection thresholds
  det_sigma_min: 0.35       # Minimum det_sigma for promotion
  det_sigma_deprecate: 0.05 # det_sigma threshold for deprecation
  det_uncert_max: 0.3       # Maximum uncertainty for execution
  
  # Computation parameters
  surprise_window: 252      # Days for structural break detection
  coherence_bands: [0.1, 0.9]  # Frequency bands for spectral coherence
  novelty_embedding_dim: 1536  # Embedding dimension for novelty
  emergence_slope_window: 30   # Days for emergence slope calculation
  
  # State-space process parameters
  alpha: 0.1                # Learning rate for kr_rho updates
  lambda: 0.05              # Decay rate for kr_rho regularization
  eta: 0.02                 # Mean reversion rate for kr_theta
  
  # Kairos & Entrainment parameters
  kairos_threshold: 0.6     # Minimum det_kairos for execution
  entrainment_threshold: 0.7 # Minimum det_entrain_r for execution
  uncertainty_threshold: 0.3 # Maximum det_uncert for execution
  
  # Observer effect parameters
  contraction_lipschitz: 0.8 # Maximum Lipschitz constant for braid updates
  witness_penalty_threshold: 0.15 # Capital share threshold for witness penalty
  witness_shrinkage: 0.95   # Shrinkage factor for crowded detectors
  
  # Complete configuration defaults
  weights:
    simons:
      accuracy: 0.25
      precision: 0.25
      stability: 0.20
      orthogonality: 0.20
      cost: 0.10
    blend_u: 0.6         # det_sigma blend

  kernel:
    alpha: 1.0           # φ exponent
    beta: 0.8            # novelty
    gamma: 0.8           # emergence
    delta: 0.7           # theta penalty
    epsilon: 0.7         # rho penalty

  gates:
    tau_K: 0.55          # kairos
    tau_r: 0.45          # entrainment
    tau_U: 0.15          # uncertainty
    min_samples_bars: 2000
    promote:
      det_sigma_min: 0.35
      ortho_max_abs_corr: 0.6
      window_days: 60
    deprecate:
      det_sigma_max: 0.05
      window_days: 30
    archive:
      recovery_det_sigma_min: 0.20
      cooldown_days: 60

  dynamics:
    theta:
      eta_mean_revert: 0.02
      theta_bar: 0.35
    rho:
      alpha_gain: 0.15
      lambda_decay: 0.10

# Deep Signal Intelligence Configuration
dsi:
  microtape:
    window_size: 256
    processing_cadence_ms: 100
    compression_ratio: 0.8
  
  experts:
    fsm_experts: 5
    classifier_experts: 3
    anomaly_experts: 2
    divergence_experts: 2
  
  fusion:
    confirmation_threshold: 0.6
    weight_learning_window: 30
    max_boost_factor: 0.2
  
  integration:
    kr_delta_phi_boost: true
    kr_theta_penalty_relief: true
    beta_mx: 0.1
    gamma_mx: 0.05

# Trading Plan Generation Configuration
trading_plans:
  generation:
    enabled: true
    max_plans_per_detector: 10
    plan_expiration_hours: 24
  
  validation:
    min_confidence_score: 0.6
    max_position_size: 0.1  # 10% of portfolio
    min_risk_reward_ratio: 1.5
  
  microstructure:
    evidence_required: true
    min_evidence_score: 0.4
    confirmation_required: true
```

## Scarcity Enforcement

**Scarcity Forces Selection**: Artificial limits that force difficult choices and prevent keeping mediocre detectors.

```yaml
scarcity_enforcement:
  max_active_per_class: 20          # Hard limit on active detectors per class
  queue_system: true                # Excess detectors wait in queue
  scarcity_forces_selection: true   # Forces difficult choices
  promotion_queue_limit: 5          # Max detectors waiting for promotion
  retirement_grace_period_days: 7   # Grace period before forced retirement
```

## Override Embargo System

**Prevent Bias Through Constraints**: All overrides must be temporary, justified, and automatically expire.

```yaml
override_embargo:
  enabled: true
  max_duration_days: 30             # Maximum override duration
  auto_expiry: true                 # Automatic expiration
  audit_trail: true                 # Log all overrides
  justification_required: true      # Must provide mathematical justification
  review_required: true             # Requires peer review
  escalation_threshold: 3           # Max overrides per detector per month
```

## Language Discipline

**Enforce Mathematical Thinking**: Ban narrative language, require quantification.

```yaml
language_discipline:
  banned_phrases:                   # Phrases that indicate narrative bias
    - "should work"
    - "feels different" 
    - "unlucky lately"
    - "market conditions"
    - "intuition suggests"
  
  required_quantification:          # Must include measurable metrics
    - "correlation"
    - "success_rate"
    - "regime_dependency"
    - "statistical_significance"
  
  data_story_examples:              # Examples of acceptable data stories
    - "73% success in high volatility regimes"
    - "0.67 correlation with VIX"
    - "ADX < 15 indicates trend dependency"
    - "p-value < 0.05 for regime classification"
```

## Configuration Sources

*Source: [alpha_detector_build_convo.md §19.1](../alpha_detector_build_convo.md#sources-of-truth)*

### 1. Feature Pack (FP)
- **Purpose**: Columns, formulas, windows
- **Format**: YAML/JSON in repo + `feature_registry`
- **Versioning**: Semantic (vMAJOR.MINOR)
- **Changes**: MINOR adds columns; MAJOR reserved for breaking changes

### 2. Detector Pack (DP)
- **Purpose**: Detectors, thresholds, weights, cooldowns, budgets
- **Format**: YAML/JSON in repo + `detector_registry`
- **Versioning**: Semantic (vMAJOR.MINOR)
- **Changes**: MINOR adjusts parameters; MAJOR changes taxonomy

### 3. Universe Policy
- **Purpose**: N_base, entry/exit bands, TTL mapping
- **Format**: YAML/JSON + DB
- **Versioning**: Monotonic integer (`universe_policy_rev`)

### 4. Runtime Config
- **Purpose**: Environment knobs (URLs, partitions, grace windows)
- **Format**: Environment variables, config files
- **Versioning**: Environment-specific

### 5. Secrets
- **Purpose**: API keys, database credentials
- **Format**: Vault/KMS managed
- **Versioning**: External secret management

## Configuration Loading & Updates

*Source: [alpha_detector_build_convo.md §19.2](../alpha_detector_build_convo.md#loading--update-model)*

### Boot Process
1. Load FP/DP/Universe from DB (latest active) or pinned files
2. Validate against JSON-Schema
3. Compute `config_hash` (SHA256 of normalized config)
4. Start with computed hash

### Runtime Updates
1. **New config** → validate (schema, bounds)
2. **Canary enablement** → `{enable_for: [asset_uids...]}` or `%` of assets
3. **Config epoch** → start time; both epochs run in parallel
4. **Promote** → set `active=true`, bump `detector_pack.version`
5. **Rollback** → flip to previous epoch

### Hot-Reloadable vs Deploy-Required
- **Detector Packs**: Hot-reloadable (thresholds, weights, cooldowns)
- **Feature Packs**: Deploy-required (columns, formulas)
- **Universe Policy**: Hot-reloadable
- **Runtime Config**: Environment restart

## Feature Flags & Kill-Switches

*Source: [alpha_detector_build_convo.md §19.3](../alpha_detector_build_convo.md#feature-flags--kill-switches)*

### Per-Detector Flags
```yaml
detectors:
  - id: spike.vol_spike_m_1
    enabled: true
    cooldown_override: 60  # Override default 45s
    threshold_override: 2.5  # Override default 2.5 (residual-based)
    performance_override:  # Phase 6 Addition
      accuracy_threshold: 0.60
      f1_score_threshold: 0.50
      max_drawdown_limit: 0.20
      regime_specific: true
    residual_model_override:  # Phase 1 Addition
      model_type: "cross_sectional"
      prediction_window: 60
      retrain_frequency: "daily"
      regime_gates: ["atr_percentile", "session_phase"]
```

### Residual Model Configuration (Phase 1 Addition)
```yaml
residual_models:
  cross_sectional:
    enabled: true
    retrain_frequency: "daily"
    lookback_days: 30
    features: ["market_beta", "sector_factor", "size_factor", "liquidity_factor"]
    regularization: 0.01
    regime_gates: ["atr_percentile", "session_phase"]
    
  kalman:
    enabled: true
    state_dimension: 3
    observation_dimension: 1
    process_noise: 0.01
    observation_noise: 0.1
    regime_gates: ["trend_regime", "volatility_regime"]
    
  order_flow:
    enabled: true
    features: ["queue_imbalance", "depth_slope", "mo_intensity", "cum_delta"]
    prediction_window: 60
    regime_gates: ["liquidity_regime", "session_phase"]
    
  basis_carry:
    enabled: true
    features: ["funding", "oi_roc", "realized_vol", "term_structure"]
    prediction_window: 300
    regime_gates: ["market_regime", "volatility_regime"]
    
  lead_lag_network:
    enabled: true
    correlation_threshold: 0.7
    lag_max: 5
    cointegration_test: true
    regime_gates: ["market_regime", "session_phase"]
    
  breadth_market_mode:
    enabled: true
    universe_size_min: 10
    breadth_threshold: 0.3
    regime_gates: ["market_regime", "volatility_regime"]
    
  volatility_surface:
    enabled: true
    term_structure_points: 5
    skew_points: 3
    regime_gates: ["volatility_regime", "session_phase"]
    
  seasonality:
    enabled: true
    time_features: ["hour", "day_of_week", "month"]
    seasonal_periods: [24, 168, 720]  # daily, weekly, monthly
    regime_gates: ["session_phase", "market_regime"]
```

### Per-Class Budgets
```yaml
budgets:
  per_symbol_per_minute:
    spike: 4
    shift: 2
    quadrant: 2
    divergence: 2
    sync: 2
    rotation: 1
  global_cap: 800
```

### Per-Asset Tier Overrides
```yaml
overrides:
  tiers:
    top: 
      spike: { threshold: 3.2 }
    tail: 
      spike: { threshold: 3.8, budgets: { spike: 2 } }
```

### Global Kill-Switches
```yaml
global:
  emit_events: false  # Stop all event emission
  enable_l2: false    # Disable L2 features
  enable_oi: false    # Disable OI features
```

## Environment & Promotion

*Source: [alpha_detector_build_convo.md §19.4](../alpha_detector_build_convo.md#environments--promotion)*

### Pipeline: dev → stg → prod
- **dev**: Synthetic feeds, local testing
- **stg**: Replays last 24h, staging topic
- **prod**: Live feeds, production topic

### Promotion Requirements
- [ ] Green unit/property tests
- [ ] Golden minutes equal
- [ ] Replay deltas within bounds
- [ ] SRE approval

### Time-Boxed Freezes
- Restrict config changes during high-vol windows (CPI prints)
- Emergency override available with approval

## Configuration Schemas

*Source: [alpha_detector_build_convo.md §19.5](../alpha_detector_build_convo.md#schema--example-snippets)*

### Detector Pack Schema
```yaml
detector_pack: v0.1.7
class_defaults:
  spike: 
    cooldown_sec: 45
    half_life_sec: 120
    weights: { w1: 1.0, w2: 0.5, w3: 0.4, a: 0.6 }
    publish_threshold: 65
  shift: 
    cooldown_sec: 90
    half_life_sec: 300
    weights: { w1: 0.7, w2: 0.8, w3: 0.2, a: 0.55 }
    publish_threshold: 60

detectors:
  - id: spike.vol_spike_m_1
    enabled: true
    threshold: 3.0
    inputs: [z_vol_m_1, ret_m_1, v_total_m_1]
    preconditions: [dq_ok, not_illiquid, trade_count_ge_5]
  - id: shift.basis_jolt_m_5
    enabled: true
    threshold_z: 2.5
    inputs: [z_basis_m_5, basis_bp_m_5, ret_m_5]
    preconditions: [dq_ok, basis_valid]

budgets:
  per_symbol_per_minute: { spike: 4, shift: 2, quadrant: 2, divergence: 2, sync: 2, rotation: 1 }
  global_cap: 800

overrides:
  tiers:
    top: { spike: { threshold: 3.2 } }
    tail: { spike: { threshold: 3.8 }, budgets: { spike: 2 } }
```

### Universe Policy Schema
```yaml
universe_policy_rev: 17
n_base: 25
entry_band: { n_entry: 22, k_entry: 3 }
exit_band: { n_exit: 30, k_exit: 5 }
freeze_min: 5
min_dwell_min: 30
hotlist:
  s_hot: 70
  ttl_base_min: 15
  ttl_k_min_per_point: 0.3
```

### Feature Pack Schema
```yaml
feature_pack: v1.0
version: 1.0.0
features:
  - name: ret_m_1
    window: 1m
    formula: "(mid_close - mid_close_prev) / mid_close_prev"
    inputs: [mid_close, mid_close_prev]
    units: "ratio"
    family: "price_returns"
  - name: z_vol_m_1
    window: 1m
    formula: "(vol_m_1 - baseline_mean) / baseline_scale"
    inputs: [vol_m_1, baseline_mean, baseline_scale]
    units: "z_score"
    family: "normalized"
```

## Auditing & Approvals

*Source: [alpha_detector_build_convo.md §19.6](../alpha_detector_build_convo.md#auditing--approvals)*

### Audit Trail
Every config change writes:
```json
{
  "who": "user@example.com",
  "when": "2025-09-03T09:30:00Z",
  "diff": { "old": {...}, "new": {...} },
  "rationale": "Reduce false positives on thin books",
  "env": "prod",
  "proposal_id": "prop_123"
}
```

### Approval Process
- **Optional Two-Man Rule**: Quant + SRE for prod DP changes
- **Weekly Curator Report**: Summarizes config churn & impact
- **Change Log**: Human-readable summary of all changes

## Failure-Safe Defaults

*Source: [alpha_detector_build_convo.md §19.7](../alpha_detector_build_convo.md#failure-safe-defaults)*

### Config Load Failure
- Keep last good packs
- Raise alert
- Do not halt pipeline

### Partial Apply
- Revert entire epoch
- Configs are all-or-nothing

### Validation Failures
- Reject invalid configs
- Log detailed error messages
- Suggest corrections

## Configuration Validation

### Schema Validation
- JSON-Schema for all config types
- Pydantic models for Python implementation
- Type checking and bounds validation

### Business Logic Validation
- Threshold ranges (e.g., 0 < threshold < 10)
- Budget constraints (e.g., per-symbol ≤ global)
- Dependency checks (e.g., required features exist)

### Runtime Validation
- Config hash consistency
- Feature availability checks
- Detector input validation

## What NOT to Configure

*Source: [alpha_detector_build_convo.md §19.8](../alpha_detector_build_convo.md#what-not-to-configure)*

### Schema/Columns
- Belong to Feature Pack and code migrations
- Not configurable at runtime

### Secrets/Keys
- Managed via vaults and env-specific secret stores
- Never in config files

### Core Logic
- Detector algorithms and formulas
- Data quality rules and thresholds
- Event scoring mathematics

## Performance-Based Configuration (Phase 6 Addition)

*Source: [alpha_detector_build_convo.md §14.4](../alpha_detector_build_convo.md#proposals-structured-diffs-not-code)*

### Performance Monitoring Configuration
```yaml
performance_monitoring:
  enabled: true
  accuracy_threshold: 0.60
  f1_score_threshold: 0.50
  win_rate_threshold: 0.55
  max_drawdown_limit: 0.20
  
  # Regime-specific monitoring
  regime_monitoring:
    enabled: true
    regimes: ["trending_up", "trending_down", "ranging"]
    performance_window_hours: 24
    adaptation_threshold: 0.15
```

### Performance-Based Proposals
```yaml
performance_proposals:
  auto_generate: true
  proposal_types:
    - "threshold_adjustment"
    - "cooldown_adjustment" 
    - "detector_disable"
    - "regime_specific_config"
  
  # Proposal generation rules
  rules:
    accuracy_degradation:
      threshold: 0.55
      window_hours: 24
      action: "increase_threshold"
      
    drawdown_protection:
      threshold: 0.25
      window_hours: 24
      action: "disable_detector"
      
    regime_adaptation:
      threshold: 0.15
      window_hours: 48
      action: "regime_specific_config"
```

### Regime-Specific Configuration
```yaml
regime_configs:
  pattern.diagonal_support_break:
    trending_up:
      threshold: 0.65
      cooldown_sec: 180
      enabled: true
    trending_down:
      threshold: 0.55
      cooldown_sec: 120
      enabled: true
    ranging:
      threshold: 0.80
      cooldown_sec: 300
      enabled: false  # Disable in ranging markets
```

## Configuration Examples

### Adding a New Detector
1. **Add to DP**:
```yaml
detectors:
  - id: combo.price_up_volume_up_m_1
    enabled: false  # Start in shadow
    inputs: [ret_m_1, z_ret_abs_m_1, z_vol_m_1, trade_count_m_1]
    preconditions: [dq_ok, not_illiquid, trade_count_ge_5]
    trigger: "ret_m_1 > 0 && z_ret_abs_m_1 >= 1.5 && z_vol_m_1 >= 2.5"
    performance_override:  # Phase 6 Addition
      accuracy_threshold: 0.60
      f1_score_threshold: 0.50
      max_drawdown_limit: 0.20
```

2. **Shadow Mode**: Run with `enabled: false`, log candidates
3. **Canary Mode**: Set `enabled: true` for subset of assets
4. **Promote**: Enable globally, bump DP version

### Performance-Based Detector Tuning
1. **Monitor Performance**: Curator tracks accuracy, f1_score, drawdown
2. **Generate Proposal**: When performance degrades, create performance-based proposal
3. **Replay Validation**: Test proposed changes against historical data
4. **Apply Changes**: Deploy validated performance improvements

### Regime Gate Configuration (Phase 1 Addition)
```yaml
regime_gates:
  atr_percentile:
    enabled: true
    min_percentile: 20
    max_percentile: 90
    rationale: "Only trade in normal volatility regimes"
    
  adx_bands:
    enabled: true
    min_adx: 12
    max_adx: 35
    rationale: "Only trade in trending markets"
    
  session_phase:
    enabled: true
    allowed_phases: ["us", "europe", "overlap"]
    rationale: "Only trade during active trading hours"
    
  market_regime:
    enabled: true
    allowed_regimes: ["normal", "trending"]
    rationale: "Only trade in appropriate market conditions"
    
  volatility_regime:
    enabled: true
    allowed_regimes: ["medium"]
    rationale: "Avoid extreme volatility periods"
    
  liquidity_regime:
    enabled: true
    allowed_regimes: ["medium", "high"]
    rationale: "Ensure sufficient liquidity for signals"
```

### Residual Model Training Configuration
```yaml
model_training:
  cross_sectional:
    retrain_schedule: "0 2 * * *"  # Daily at 2 AM
    lookback_days: 30
    validation_split: 0.2
    purged_cv_folds: 5
    fdr_control: true
    fdr_alpha: 0.05
    
  kalman:
    retrain_schedule: "0 3 * * *"  # Daily at 3 AM
    lookback_days: 7
    state_dimension: 3
    process_noise: 0.01
    observation_noise: 0.1
    
  order_flow:
    retrain_schedule: "*/6 * * * *"  # Every 6 hours
    lookback_hours: 24
    features: ["queue_imbalance", "depth_slope", "mo_intensity"]
    prediction_window: 60
```

### Adjusting Thresholds
1. **Propose Change**: Update threshold in DP
2. **Validate**: Run replay tests
3. **Canary**: Deploy to 10% of assets
4. **Monitor**: Check event rates and quality
5. **Promote**: Roll out to all assets

### Emergency Rollback
1. **Identify**: Last known good config epoch
2. **Revert**: Flip to previous epoch
3. **Verify**: Confirm system behavior
4. **Investigate**: Root cause analysis
5. **Document**: Update change log

---

*For complete configuration management specifications, see [alpha_detector_build_convo.md §19](../alpha_detector_build_convo.md#configuration-management)*
