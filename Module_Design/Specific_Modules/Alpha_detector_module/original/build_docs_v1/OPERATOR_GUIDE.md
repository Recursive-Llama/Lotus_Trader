# Operator's Guide

*Source: [alpha_detector_build_convo.md §17-18](../alpha_detector_build_convo.md#operational-envelope)*

## How It Actually Runs

### Life of a Minute

Think of the system as a conveyor belt that ticks once per minute:

1. **WS Ingest** → Per-asset accumulators (trades, BBO, optionally L2)
2. **Minute Close** → Bar closes with lateness watermark (~1-1.5s)
3. **Feature Build** → Raw features → baselines → z/quantiles → DQ
4. **Snapshot Write** → UPSERT to `features_snapshot`
5. **Market Context** → Build breadth/leader/RS for timestamp
6. **Detector Pass** → Evaluate rules on finished 1m row
7. **Event Publish** → Score, debounce, and send events

## Run Modes

*Source: [alpha_detector_build_convo.md §17.2](../alpha_detector_build_convo.md#degradation-paths-graceful-explicit)*

### 1. Dry-Run
- **What**: Ingest + build + write snapshots
- **Detectors**: Compute but don't publish (log candidates)
- **Goal**: Prove bars are correct and fast enough

### 2. Shadow
- **What**: Detectors write to internal table/topic
- **Goal**: Sanity-check counts, severities, suppression

### 3. Canary
- **What**: Real publications for few high-liquidity symbols
- **Goal**: Confirm behavior under real flow

### 4. Production
- **What**: Full Top-N + hotlist with all controls
- **Goal**: Live system with budgets, cooldowns, gates

### 5. Replay
- **What**: Offline, deterministic validation
- **Goal**: Guarantee bit-identical reproduction

## First Hour Checklist

*Source: [alpha_detector_build_convo.md §3](../alpha_detector_build_convo.md#turn-it-on--the-first-hour-concretely)*

### 0-10 minutes
- [ ] Start WS ingest for 3-5 symbols (BTC/ETH/SOL)
- [ ] Verify 1m rows appear ~150-300ms after minute close
- [ ] Check DQ ≥95% ok (no trades? BBO still gives mid_close)

### 10-20 minutes
- [ ] Watch baselines warm (z_* = NULL until ~200 samples)
- [ ] Confirm `ingest_lag_ms` p95 < 300ms
- [ ] Check `book_staleness_ms` typically < 1000ms on majors

### 20-40 minutes (dry-run)
- [ ] Enable 3 spike detectors in shadow
- [ ] See shadowed candidates on active names
- [ ] Verify suppression = 0 (not publishing)

### 40-60 minutes (canary)
- [ ] Flip canary on BTC/ETH for spikes only
- [ ] Confirm events show up <150ms after snapshot write
- [ ] Check budget utilization < 0.5 for spike class
- [ ] Verify no events during `dq_status != ok` minutes

## Health Indicators

### 1. Pipeline Latency
*Source: [alpha_detector_build_convo.md §17.1](../alpha_detector_build_convo.md#latency--throughput-targets-top-n--25--hotlist--10)*

- **Green**: Bar finalize p95 < 300ms; end-to-end p95 < 450ms
- **Amber**: p95 300-500ms → detector deferrals may kick in
- **Red**: p95 > 500ms → fix before widening scope

### 2. Data Quality
*Source: [alpha_detector_build_convo.md §8](../alpha_detector_build_convo.md#data-quality--safety-rails)*

- **Green**: ≥95% 1m rows `dq=ok` on majors; few nulls outside L2
- **Amber**: Growing `book_staleness_ms`, OI staleness >20s
- **Red**: Frequent stale → events sparse; check WS and clock skew

### 3. Event Health
*Source: [alpha_detector_build_convo.md §10](../alpha_detector_build_convo.md#severity-novelty--debounce-model)*

- **Green**: Class mix close to defaults; suppression <5%; severities p50 ~60-70
- **Amber**: Floods (budgets hit) or droughts → thresholds need tuning
- **Red**: Everything suppressed for DQ/illiquidity → guardrails too tight

### 4. Baseline Drift
*Source: [alpha_detector_build_convo.md §4](../alpha_detector_build_convo.md#baseline--normalization-strategy)*

- **Green**: |mean| ≤ 0.2, std in [0.8,1.2]
- **Amber/Red**: Drift means normalizer off; Curator will propose tweaks

## Troubleshooting

*Source: [alpha_detector_build_convo.md §21](../alpha_detector_build_convo.md#failure-modes--mitigations)*

| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| No 1m rows | WS not subscribed, wrong symbol alias, clocking issue | Check subscriptions; verify alias map and exchange timestamps |
| Rows exist but `dq=stale` | No BBO/trades, WS gap | Reconnect WS; don't backfill ticks; accept partial minutes |
| `z_*` are NULL forever | Warm-up never completes, DQ not ok, baseline not persisted | Confirm min_samples ~200; ensure baseline_state updates only on `dq=ok` |
| Events flood | Thresholds too low, IQR clamp off, budgets mis-set | Raise class thresholds/cooldowns; ensure clamp applied in scoring |
| Events drought | Gates too tight, warm-up, DQ partial | Lower `v_min`/`spread_cap` for top tiers; confirm warm-up complete |
| Latency > 500ms | Too many symbols, L2 heavy, slow DB | Disable L2 features; reduce universe to Top-10; enable detector deferral |
| OI/basis NULL often | REST cadence too slow, rate-limited | Shorten cadence with jitter; suppress OI/basis detectors until fresh |

## Monitoring Dashboards

*Source: [alpha_detector_build_convo.md §18.2](../alpha_detector_build_convo.md#dashboards-four-panes)*

### 1. Ingest Health
- WS rates, reconnects
- `book_staleness_ms`, `oi_staleness_ms`
- Clock skew trends

### 2. Minute Pipeline
- Finalize latency (`alpha_bar_finalize_latency_ms`)
- Write errors, DQ split
- Null rates by feature

### 3. Events
- Triggers vs published vs suppressed
- Severity distributions by class
- Budget utilization

### 4. Curator & Drift
- Z-mean/std by feature
- Replay pass/fail rates
- Proposal queue status

### 5. Trading Performance (Phase 6 Addition)
- Detector accuracy by regime
- Signal performance trends
- Drawdown monitoring
- Performance-based proposals

### 6. Residual Model Performance (Phase 1 Addition)
- Model prediction accuracy (R², MAE, RMSE)
- Residual distribution analysis
- Model retraining status and frequency
- Regime gate effectiveness
- Cross-sectional model performance
- Kalman filter innovation analysis
- Order flow model accuracy
- Basis/carry model performance
- Lead-lag network correlations
- Breadth/market mode classification
- Volatility surface model fit
- Seasonality model effectiveness

## Key Metrics

*Source: [alpha_detector_build_convo.md §18.1](../alpha_detector_build_convo.md#metrics-prometheus-style-names)*

### Ingest
```
hl_ws_messages_total{feed,type}
hl_ws_disconnects_total{feed}
alpha_ingest_book_staleness_ms{symbol}
```

### Assembly
```
alpha_bar_finalize_latency_ms{tf}
alpha_snapshot_writes_total{tf,status}
alpha_baseline_updates_total{feature,tf}
```

### Quality
```
alpha_dq_status_count{status}
alpha_null_rate{feature}
alpha_clock_skew_ms
```

### Detectors & Events
```
alpha_detector_triggers_total{class,subtype}
alpha_event_published_total{class}
alpha_event_suppressed_total{reason}
alpha_severity_histogram{class}
```

### Trading Performance (Phase 6 Addition)
```
alpha_signal_accuracy{detector_id,market_regime}
alpha_signal_precision{detector_id,market_regime}
alpha_signal_f1_score{detector_id,market_regime}
alpha_detector_win_rate{detector_id}
alpha_detector_max_drawdown{detector_id}
alpha_performance_proposals_total{status}
```

### Residual Models (Phase 1 Addition)
```
alpha_residual_model_r2{model_type,feature}
alpha_residual_model_mae{model_type,feature}
alpha_residual_model_rmse{model_type,feature}
alpha_residual_model_retrain_total{model_type,status}
alpha_residual_model_prediction_latency_ms{model_type}
alpha_regime_gate_effectiveness{gate_type,regime}
alpha_cross_sectional_model_performance{feature}
alpha_kalman_innovation_std{feature}
alpha_order_flow_model_accuracy{feature}
alpha_basis_carry_model_r2{feature}
alpha_lead_lag_correlation{asset_pair}
alpha_breadth_classification_accuracy{market_mode}
alpha_vol_surface_model_fit{term_structure}
alpha_seasonal_model_effectiveness{seasonal_period}
```

## Alerts

*Source: [alpha_detector_build_convo.md §18.3](../alpha_detector_build_convo.md#alerts-examples)*

- **WS flap**: `hl_ws_disconnects_total` rate > 3/5m
- **Latency breach**: `alpha_bar_finalize_latency_ms_p95` > 500 for 5m
- **DQ deterioration**: `alpha_dq_status_count{status="stale"}` > 1% for 15m
- **Event flood**: `alpha_event_published_total` > global cap for 1m
- **Drift**: |mean(z_vol_m_1)| > 0.2 for 60m on any top-tier asset
- **Curator stalled**: No replay_pass in 48h
- **Performance degradation**: Signal accuracy < 0.55 for 24h on any detector
- **Drawdown alert**: Max drawdown > 0.25 for any detector
- **Regime performance**: Detector accuracy drops > 0.15 when market regime changes
- **Residual model degradation**: Model R² < 0.3 for 2h on any model type
- **Model retrain failure**: Model retrain fails 3 times in 24h
- **Regime gate ineffectiveness**: Regime gate blocks > 80% of signals for 1h
- **Cross-sectional model drift**: Cross-sectional model performance drops > 0.2 for 4h
- **Kalman filter instability**: Kalman innovation std > 3σ for 30m
- **Order flow model accuracy**: Order flow model accuracy < 0.4 for 2h

## Deployment Topology

*Source: [alpha_detector_build_convo.md §17.6](../alpha_detector_build_convo.md#deployment-topology)*

### Processes
- **ingest**: WS & accumulators
- **builder**: Assembly + rollups
- **detector**: Events
- **curator**: Out-of-band intelligence
- **publisher**: Bus/DB writers

### Scaling
- Horizontal by asset shards (`hash(asset_uid) % S`)
- Blue/green or canary deployments
- 10% assets → observe metrics → roll

## SLAs/SLOs

*Source: [alpha_detector_build_convo.md §17.7](../alpha_detector_build_convo.md#slas--slos-starter)*

- **Availability**: 99.9%/30d (hot path)
- **Minute completion p95**: ≤ 300ms
- **Event suppression**: ≤ 5% of attempted
- **DQ ok-rate**: ≥ 95% of minutes for top-tier assets

## What "Healthy" Looks Like

*Source: [alpha_detector_build_convo.md §11](../alpha_detector_build_convo.md#what-healthy-looks-like-quick-heuristics)*

- **Latency**: Bar finalize p95 ~200-300ms; event publish p95 ~100-150ms
- **DQ**: ok ≥ 95% on majors; partial mainly due to OI/L2; stale ≪ 1%
- **Events**: Per-class counts within budgets; suppression < 5%; severities bell-curvy around 60-70
- **Drift**: z-means ≈ 0, z-std ≈ 1; no large, persistent bias
- **Stability**: Universe churn ≤ 5/hour; hotlist TTLs expiring as expected

## Operator Rituals (Evolutionary Stewardship)

### Daily (15 min)
- Open the cohort leaderboard; scan top/bottom
- Confirm dq_status health; no story-based overrides
- Approve auto promotions/retirements unless data-quality flags

### Weekly (45 min)
- Review reseeding children; prune obvious degenerates (e.g., turnover>cap×2)
- Tag survivors with short factual notes ("Works on high-vol spikes; cost marginal")
- Schedule a limited manual mutation round if diversity is dropping

### Monthly (60 min)
- Diversity check: asset, horizon, transform families
- Identify monocultures; bias reseeding toward underrepresented traits

## Override Ethics

Never keep a detector because its story "ought to work."

If you must override, you must write the rule and register it in config (embargo), with expiry. Overrides are rare, logged, and reviewable.

## Kill Criteria (Zero Regret)

**Automated Retirement - No Appeals Process:**
- S_i below deprecate threshold for 15/30 days → **immediate retirement**
- dq_status breaches >10% eval days → **immediate retirement** & open ingest ticket
- Cost explosions (impact>cap×2 for a week) → **immediate retirement**
- Correlation >0.6 with existing active detector → **immediate retirement**
- Complexity >10 hyperparameters → **immediate retirement**

**Zero Regret Principle**: If the numbers say it's dead, it's dead. No second chances, no "but it might work next month."

## Diversity Monitoring

**Prevent Monocultures**: Actively monitor and maintain genetic diversity.

### Daily Diversity Check
- **Asset diversity**: Ensure detectors cover different asset classes
- **Horizon diversity**: Mix of 1m, 5m, 15m, 1h detectors
- **Residual diversity**: Different residual factory combinations
- **Regime diversity**: Detectors for different market regimes

### Weekly Diversity Report
```yaml
diversity_metrics:
  asset_coverage: 0.85              # % of asset classes covered
  horizon_distribution: [0.3, 0.4, 0.2, 0.1]  # 1m, 5m, 15m, 1h
  residual_factory_usage:           # Usage of each residual factory
    cross_sectional: 0.4
    kalman: 0.3
    order_flow: 0.2
    # ... other factories
  regime_coverage: 0.9              # % of market regimes covered
```

### Monoculture Prevention
- **Bias reseeding** toward underrepresented traits
- **Force retirement** of overrepresented detector types
- **Manual mutation** when diversity drops below threshold

## Promotion Discipline

- No promotion without min_samples and universe stability
- No more than K=20 actives per class; excess waits in a queue—scarcity forces selection

## Kernel Resonance Monitoring (Phase 1 Addition)

**Enhanced Selection System**: Monitor both signal quality core (sq_score) and phase resonance (kr_delta_phi) for optimal detector selection.

### Daily Kernel Metrics
- **det_sigma**: Final selection score (geometric blend of sq_score + kr_delta_phi)
- **kr_delta_phi**: Kernel resonance (kr_hbar × kr_coherence × kr_phi × kr_novelty × kr_emergence)
- **det_uncert**: Uncertainty variance across detector variants
- **det_abstained**: Abstention decisions due to high uncertainty

### Operator Heuristics

**High Cohesion & Timing:**
- **High det_entrain_r & high det_kairos**: Scale top det_sigma detectors
- **Low det_entrain_r & high kr_hbar**: Prefer high kr_novelty / high kr_emergence (explore), smaller size
- **Rising kr_theta with flat det_sigma**: Simplify (reduce kr_rho, swap residuals)

**Regime-Based Selection:**
- **Low surprise (kr_hbar), high coherence (kr_coherence)**: Favor high sq_score incumbents
- **High surprise spikes**: Prioritize high novelty (kr_novelty) and emergence (kr_emergence) detectors
- **High uncertainty**: Abstain from execution, let cohort resolve
- **Regime breaks**: Bias toward high field resonance (kr_phi) detectors

**State Management:**
- **Monitor kr_phi, kr_theta, kr_rho evolution** over time
- **Watch for kr_theta mean reversion** patterns
- **Track complexity growth** (kr_rho) vs. resonance payoff
- **Adjust witness penalties** based on detector crowding

**Enhanced Operator Heuristics:**
- **High det_entrain_r & high det_kairos**: Scale top det_sigma detectors
- **Low det_entrain_r & high kr_hbar**: Prefer high kr_novelty / high kr_emergence (explore), smaller size
- **Rising kr_theta with flat det_sigma**: Simplify (reduce kr_rho, swap residuals)
- **Promotions/retirements are based on det_sigma, not on psi_***

**Note**: These are signal quality metrics for detector selection. Trade profitability analysis (psi_score) is handled separately by the trading system.

### Kernel Resonance Alerts
- "Kernel resonance degradation" when kr_delta_phi < 0.2
- "High uncertainty detected" when det_uncert > 0.3
- "Selection score divergence" when det_sigma vs sq_score differ > 0.3

## Performance and Scalability Considerations (Phase 1 Addition)

### Computational Requirements

**Residual Factory Performance:**
- **Cross-Sectional Factory**: O(n²p) complexity where n = number of assets, p = number of features
- **Kalman Factory**: O(n³) complexity where n = state dimension (typically 3)
- **Order Flow Factory**: O(n) complexity where n = number of trades per minute
- **Basis/Carry Factory**: O(n) complexity where n = number of time points
- **Lead-Lag Network**: O(n²k) complexity where n = number of assets, k = max lag
- **Breadth/Market Mode**: O(n) complexity where n = number of assets
- **Volatility Surface**: O(n) complexity where n = number of strikes
- **Seasonality Factory**: O(n) complexity where n = number of time points

**Memory Requirements per Symbol:**
- **Cross-Sectional**: ~1KB per minute (factor loadings + residuals)
- **Kalman**: ~2KB per minute (state vector + covariance matrix)
- **Order Flow**: ~0.5KB per minute (flow features)
- **Basis/Carry**: ~0.5KB per minute (carry features)
- **Lead-Lag Network**: ~1KB per minute (correlation matrix)
- **Breadth/Market Mode**: ~0.5KB per minute (regime classification)
- **Volatility Surface**: ~1KB per minute (vol surface)
- **Seasonality**: ~0.5KB per minute (seasonal effects)
- **Total per Symbol**: ~7KB per minute = ~420KB per hour = ~10MB per day

**Latency Impact:**
- **Feature Computation**: +2-5ms per symbol (existing features)
- **Residual Computation**: +3-8ms per symbol (8 residual factories)
- **Regime Classification**: +1-2ms per symbol (regime gates)
- **Total Additional Latency**: +4-10ms per symbol
- **End-to-End Latency**: 200-300ms (existing) + 4-10ms (residuals) = 204-310ms

### Scalability Considerations

**Horizontal Scaling:**
- **Symbol Partitioning**: Distribute symbols across multiple detector instances
- **Factory Parallelization**: Run residual factories in parallel threads
- **Database Sharding**: Partition feature snapshots by symbol or time
- **Load Balancing**: Distribute WebSocket connections across instances

**Vertical Scaling:**
- **CPU Requirements**: 4-8 cores for 100 symbols with all residual factories
- **Memory Requirements**: 8-16GB RAM for 100 symbols with 7-day retention
- **Storage Requirements**: ~1GB per symbol per day for feature snapshots
- **Network Requirements**: 100Mbps for WebSocket data + database writes

**Performance Optimization:**
- **Caching**: Cache model predictions and regime classifications
- **Batch Processing**: Process multiple symbols in batches
- **Async Processing**: Use asyncio for I/O operations
- **Database Optimization**: Use prepared statements and connection pooling
- **Memory Management**: Implement circular buffers for temporary data

### Monitoring and Alerting

**Performance Metrics:**
- `residual_factory_prediction_latency` - Prediction latency by factory
- `residual_factory_memory_usage` - Memory usage by factory
- `residual_factory_cpu_usage` - CPU usage by factory
- `residual_factory_throughput` - Events processed per second
- `residual_factory_error_rate` - Error rate by factory

**Alerting Rules:**
```yaml
alerts:
  - alert: ResidualFactoryHighLatency
    expr: residual_factory_prediction_latency > 10
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Residual factory {{ $labels.factory_name }} latency above threshold"
  
  - alert: ResidualFactoryHighMemoryUsage
    expr: residual_factory_memory_usage > 1000000000  # 1GB
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Residual factory {{ $labels.factory_name }} memory usage high"
  
  - alert: ResidualFactoryHighCPUUsage
    expr: residual_factory_cpu_usage > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Residual factory {{ $labels.factory_name }} CPU usage high"
  
  - alert: ResidualFactoryHighErrorRate
    expr: residual_factory_error_rate > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Residual factory {{ $labels.factory_name }} error rate high"
```

### Capacity Planning

**Resource Requirements by Scale:**
- **10 Symbols**: 2 cores, 4GB RAM, 10GB storage/day
- **50 Symbols**: 4 cores, 8GB RAM, 50GB storage/day
- **100 Symbols**: 8 cores, 16GB RAM, 100GB storage/day
- **500 Symbols**: 16 cores, 32GB RAM, 500GB storage/day
- **1000 Symbols**: 32 cores, 64GB RAM, 1TB storage/day

**Scaling Thresholds:**
- **CPU Usage**: Scale horizontally when > 70% CPU usage
- **Memory Usage**: Scale horizontally when > 80% memory usage
- **Latency**: Scale horizontally when p95 latency > 500ms
- **Error Rate**: Scale horizontally when error rate > 1%

### Performance Testing

**Load Testing:**
- **Symbol Load**: Test with 10, 50, 100, 500, 1000 symbols
- **Event Rate**: Test with 1x, 2x, 5x, 10x normal event rate
- **Concurrent Users**: Test with 1, 5, 10, 20 concurrent API users
- **Data Volume**: Test with 1 day, 7 days, 30 days of historical data

**Performance Benchmarks:**
- **Target Latency**: p95 < 300ms for 100 symbols
- **Target Throughput**: > 1000 events/second
- **Target Memory**: < 16GB for 100 symbols
- **Target CPU**: < 70% for 100 symbols

**Stress Testing:**
- **Peak Load**: 2x normal load for 1 hour
- **Sustained Load**: 1.5x normal load for 24 hours
- **Failure Recovery**: Test recovery from component failures
- **Data Corruption**: Test handling of corrupted data

### Optimization Strategies

**Code Optimization:**
- **Vectorization**: Use NumPy vectorized operations
- **Compilation**: Use Numba for critical loops
- **Caching**: Cache expensive computations
- **Lazy Loading**: Load data only when needed

**Database Optimization:**
- **Indexing**: Create indexes on frequently queried columns
- **Partitioning**: Partition tables by time or symbol
- **Connection Pooling**: Reuse database connections
- **Query Optimization**: Use prepared statements and efficient queries

**System Optimization:**
- **Process Isolation**: Run each factory in separate process
- **Memory Mapping**: Use memory-mapped files for large datasets
- **Compression**: Compress stored data
- **Deduplication**: Remove duplicate data

---

*For complete operational specifications, see [alpha_detector_build_convo.md §17-18](../alpha_detector_build_convo.md#operational-envelope)*
