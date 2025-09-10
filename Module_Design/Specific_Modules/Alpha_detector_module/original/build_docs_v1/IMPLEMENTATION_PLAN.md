# Implementation Plan & Roadmap

*Source: [alpha_detector_build_convo.md §24-25](../alpha_detector_build_convo.md#phase-roadmap--milestones)*

## Overview

The implementation follows an evolutionary approach over 16 weeks, with each phase representing a different environment for detector breeding and selection. The system evolves from a simple testbed to a full production ecosystem.

## DSI Integration v0.0 (Weeks 0-1)

**Environment**: MicroTape tokenization + micro-expert ecosystem setup.
**Focus**: Deep Signal Intelligence foundation and integration.
**Control**: DSI evidence validation and expert weight learning.

### Scope
- MicroTape tokenization system (Hyperliquid data → structured events)
- 5 FSM experts for basic microstructure patterns
- DSI evidence fusion and integration with kernel resonance
- Trading plan generation framework

### Milestones
- **M0.0**: MicroTape processing < 2ms latency
- **M0.1**: FSM experts detecting basic patterns (wick patterns, order book depletion)
- **M0.2**: DSI evidence boosting kernel resonance scores

### Gate Criteria
- DSI latency < 10ms total
- Evidence accuracy > 70% correlation with detector performance
- No degradation in existing detector performance

## Testbed v0.1 (Weeks 2-4)

**Environment**: Run 10 detectors + 5 residuals + DSI in parallel on a pinned 90d window.
**Focus**: Metrics & leaderboard pipeline (daily snapshots) with DSI enhancement.
**Control**: Lifecycle state changes by manual API (promotion/deprecate).

### Scope
- WS ingest (trades, candle, BBO)
- 1m assembly for price/volume + DQ fields
- Minimal normalization (vol/ret_abs) with warm-up
- Basic spike detectors: `spike.vol_spike_m_1`, `spike.price_spike_*`
- Event publication to staging topic only

### Milestones
- **M0.1**: First snapshots written, p95 < 300ms on 10 symbols
- **M0.2**: Events visible in staging; golden minutes pack defined

### Gate Criteria
- Golden minutes CI passes (bit-identical)
- SLOs met on 10 symbols

### Deliverables
- [ ] Basic WS client with reconnection
- [ ] 1m feature builder (price/volume only)
- [ ] **Complete ETL pipeline** (detailed calculation methods for all components)

### ETL Implementation Pseudocode
```python
for each eval_window t:
    # 1) compute Simons quality
    sq_accuracy  = weighted_hit_rate(sign(s), sign(fwd_ret), weights=abs(s))
    beta, se     = ols(fwd_ret ~ s)             # precision
    sq_precision = clip01(t_stat(beta, se).logistic())
    sq_stability = 1 - sd(rolling_IR(P)) / (abs(mean(rolling_IR(P))) + 1e-6)
    sq_orthog    = 1 - max_abs_corr(P_i, P_actives)
    sq_cost      = fees + slippage_bps*turnover + kappa*turnover**2
    sq_score     = wa*sq_accuracy + wp*sq_precision + ws*sq_stability \
                   + wo*sq_orthog - wc*sq_cost

    # 2) kernel parts
    kr_hbar      = logistic(zscore(page_hinkley(logRV)))
    kr_coherence = band_coherence(s, fwd_ret, band=B_i)
    kr_phi       = abs(partial_corr(P_i, OpportunityFactor | P_actives))
    kr_theta     = 1 - support(s, τ_s) * (1 - regime_entropy()/Hmax)
    kr_rho       = σ(αd*depth(recipe) + βd*nodes(recipe))
    kr_novelty   = median_cosine_distance(embed(i), embeds_active)
    kr_emergence = logistic(slope(det_sigma_history) + λ*median_xfer(det_sigma))

    kr_delta_phi = kr_hbar * kr_coherence * (
                     kr_phi**α * kr_novelty**β * kr_emergence**γ
                   ) / ((1-kr_theta)**δ * (1-kr_rho)**ε + 1e-6)

    # 3) blend & gates
    det_sigma    = sq_score**u * kr_delta_phi**(1-u)
    det_kairos   = kairos_alignment(market_spectrum, phase_i, W=kr_phi*kr_theta*kr_rho)
    det_entrain_r= kuramoto_order(phases_of_market_modes)
    det_uncert   = var(child_signals(siblings_of_i))

    # 4) state updates
    kr_phi   = clip01(kr_phi_prev * kr_rho)
    kr_theta = clip01(kr_theta_prev + kr_hbar * sum_j(kr_phi_j*kr_rho_j) - η*(kr_theta_prev - θ_bar))
    kr_rho   = clip01(σ(kr_rho + α_gain*kr_delta_phi - λ_decay*kr_rho))

    # 5) crowding penalty
    penalty  = 1 / (1 + c * share_i**p)
    kr_coherence *= penalty

    # 6) write metrics (detector table). Optionally mirror det_sigma/kairos/r onto trades.
```

*Source: [alpha_detector_build_convo.md §24.1](../alpha_detector_build_convo.md#phase-0--bootstrap-weeks-12)*

### Scope
- WS ingest (trades, candle, BBO)
- 1m assembly for price/volume + DQ fields
- Minimal normalization (vol/ret_abs) with warm-up
- Basic spike detectors: `spike.vol_spike_m_1`, `spike.price_spike_*`
- Event publication to staging topic only

### Milestones
- **M0.1**: First snapshots written, p95 < 300ms on 10 symbols
- **M0.2**: Events visible in staging; golden minutes pack defined

### Gate Criteria
- Golden minutes CI passes (bit-identical)
- SLOs met on 10 symbols

### Deliverables
- [ ] Basic WS client with reconnection
- [ ] 1m feature builder (price/volume only)
- [ ] Simple baseline computation
- [ ] 3 spike detectors in shadow mode
- [ ] Event publisher to staging topic
- [ ] Basic metrics and health checks

## Selection v0.2 (Weeks 3-5)

**Environment**: Enforce gates from Config.
**Focus**: Auto-promote/auto-deprecate jobs (nightly).
**Control**: Mutation service + weekly reseeding cron.

### Scope
- **Residual-first feature pack v1.0** (all feature families with predictive models)
- **8 residual factories** (Cross-sectional, Kalman, Flow, Network, Carry, Breadth, Vol, Seasonality)
- **Regime classification system** (ATR, ADX, session, market regime gates)
- Event catalogue v0.1 (all 6 classes with residual triggers)
- Severity/novelty/debounce with budgets and regime boosts
- Market snapshot builder
- Universe policy & hotlist
- Storage schemas live

### Milestones
- **M1.1**: All detectors shadowed; severity histograms stable
- **M1.2**: Live events to `alpha.events.v0` for Top-10

### Gate Criteria
- Replay CI (last 24h) within tolerances
- Suppression < 5%
- DQ ok-rate ≥ 95% on Top-10

### Deliverables
- [ ] Complete feature computation (all families)
- [ ] **Momentum indicators** (RSI, MACD, Stochastic, ADX, HMA, ATR)
- [ ] **Swing detection** infrastructure (mechanical swing finding)
- [ ] **Advanced trend features** (HMA slope, ATR percentiles, volatility regime)
- [ ] **Divergence detection framework** (context-aware, trigger-based)
- [ ] **Pattern detection framework** (candlestick, chart patterns, support/resistance)
- [ ] **Residual manufacturing system** (8 residual factories with predictive models)
- [ ] **Regime classification system** (ATR, ADX, session, market regime gates)
- [ ] **Kernel resonance system** (enhanced two-layer selection with sq_score + kr_delta_phi)
- [ ] Robust baseline system with persistence
- [ ] All detector classes implemented (including advanced divergence and pattern detectors)
- [ ] Market context builder
- [ ] Universe management system
- [ ] Production event bus
- [ ] Complete storage schema

### Divergence Detection Requirements (Phase 1 Addition)

**Critical Features Needed:**
- [ ] **Momentum Indicators**: RSI (14,21,50), MACD (12,26,9), Stochastic (14), ROC (10,20)
- [ ] **Trend Indicators**: ADX (14,21), HMA (100), ATR (14,21)
- [ ] **Swing Detection**: Mechanical swing high/low detection with confirmation
- [ ] **Context Gates**: Trend filters, volatility gates, level proximity
- [ ] **Divergence Scoring**: Quantified divergence strength with proper weighting

**Advanced Divergence Types:**
- [ ] **Hidden Momentum Divergence** (continuation signals) - Priority #1
- [ ] **Delta/Volume Divergence** (microstructure absorption) - Priority #2  
- [ ] **Classic RSI/MACD Divergence** (reversal signals) - Priority #3
- [ ] **Breadth Divergence** (market structure) - Phase 2

**Implementation Strategy:**
- [ ] **Mechanical Detection**: No visual line drawing, fixed algorithms
- [ ] **Context-Aware**: Trend/volatility/level gates for robustness
- [ ] **Trigger-Based**: Break/reclaim triggers, not just predictions
- [ ] **Regime-Specific**: Know when each divergence type works best

### Residual Manufacturing Requirements (Phase 1 Addition)

**Critical Features Needed:**
- [ ] **8 Residual Factories**: Cross-sectional, Kalman, Flow, Network, Carry, Breadth, Vol, Seasonality
- [ ] **Predictive Models**: Daily ridge regression, state-space models, flow-fit models
- [ ] **Regime Classification**: ATR percentiles, ADX bands, session phases, market regimes
- [ ] **Residual Calculation**: (actual - predicted) / prediction_std with proper normalization
- [ ] **Model Training**: Purged CV, FDR controls, rolling OOS validation

**Residual Factory Details:**
- [ ] **Cross-Sectional**: Market/sector/size/liquidity factor models
- [ ] **Kalman**: State-space models with trend/volatility regimes
- [ ] **Order Flow**: Queue imbalance, depth slope, MO intensity models
- [ ] **Basis/Carry**: Funding/OI/volatility models for perp-spot basis
- [ ] **Lead-Lag Network**: Cointegration and correlation models across assets
- [ ] **Breadth/Market Mode**: Market-wide regime classification models
- [ ] **Volatility Surface**: Term structure and skew models for vol prediction
- [ ] **Seasonality**: Time-of-day, day-of-week, seasonal effect models

**Regime Gate Implementation:**
- [ ] **ATR Percentile Gates**: Only trade in normal volatility (20th-90th percentile)
- [ ] **ADX Band Gates**: Only trade in trending markets (ADX 12-35)
- [ ] **Session Phase Gates**: Only trade during active hours (US/EU overlap, Asia open)
- [ ] **Market Regime Gates**: Only trade in appropriate market conditions

**Implementation Strategy:**
- [ ] **Residual-First**: Build all detectors with residual triggers from ground up
- [ ] **Model Integration**: Integrate predictive models into feature computation
- [ ] **Regime-Aware**: All detectors respect regime gates for signal quality
- [ ] **Performance Monitoring**: Track model performance and regime effectiveness

### Integration Strategy with Existing Codebase (Phase 1 Addition)

**Existing Codebase Assessment:**
- [ ] **Current Structure**: 20-minute basic structure with z-score detectors
- [ ] **Feature Builder**: Basic feature computation with OHLC, volume, returns
- [ ] **Detector Classes**: Spike, Shift, Quadrant, Divergence, Synchrony, Rotation
- [ ] **Data Models**: Pydantic models for FeatureSnapshot, AnomalyEvent
- [ ] **WebSocket Integration**: Hyperliquid WebSocket client working
- [ ] **Database Schema**: Basic schema with feature storage

**Integration Approach:**
- [ ] **Preserve Architecture**: Keep existing class structure and data flow
- [ ] **Enhance Feature Builder**: Add residual factories to existing feature computation
- [ ] **Upgrade Detectors**: Replace z-score logic with residual triggers
- [ ] **Extend Data Models**: Add residual fields to existing Pydantic models
- [ ] **Maintain Backward Compatibility**: Support both z-score and residual modes during transition

**Feature Builder Integration:**
```python
class EnhancedFeatureBuilder(FeatureBuilder):
    def __init__(self):
        super().__init__()
        self.residual_factories = {
            'cross_sectional': CrossSectionalResidualFactory(),
            'kalman': KalmanResidualFactory(),
            'order_flow': OrderFlowResidualFactory(),
            'basis_carry': BasisCarryResidualFactory(),
            'lead_lag_network': LeadLagNetworkResidualFactory(),
            'breadth_market_mode': BreadthMarketModeResidualFactory(),
            'volatility_surface': VolatilitySurfaceResidualFactory(),
            'seasonality': SeasonalityResidualFactory()
        }
    
    def build_enhanced_snapshot(self, acc: AccumulatorData, exchange_ts: datetime) -> FeatureSnapshot:
        # 1. Build basic features (existing logic)
        snapshot = self._build_snapshot_for_symbol(acc, exchange_ts)
        
        # 2. Add residual features
        residual_features = self._compute_residual_features(snapshot)
        snapshot = snapshot.copy(update=residual_features)
        
        # 3. Add regime classification
        regime_features = self._compute_regime_features(snapshot)
        snapshot = snapshot.copy(update=regime_features)
        
        return snapshot
```

**Detector Integration:**
```python
class ResidualSpikeDetector(SpikeDetector):
    def __init__(self, feature: str, threshold: float, secondary_feature: str = None):
        super().__init__(feature, threshold, secondary_feature)
        self.residual_mode = True  # Enable residual mode
    
    def check_trigger(self, snapshot: FeatureSnapshot) -> Tuple[bool, int]:
        # 1. Check data quality gates (existing logic)
        if not self._check_dq_gates(snapshot):
            return False, 0
        
        # 2. Check regime gates (new)
        if not self._check_regime_gates(snapshot):
            return False, 0
        
        # 3. Use residual features instead of z-scores
        if self.residual_mode:
            primary_residual = getattr(snapshot, f'z_{self.feature}_residual_m_1')
            if primary_residual is None:
                return False, 0
            if abs(primary_residual) < self.threshold:
                return False, 0
        else:
            # Fallback to z-score mode
            primary_z = getattr(snapshot, f'z_{self.feature}_m_1')
            if primary_z is None:
                return False, 0
            if abs(primary_z) < self.threshold:
                return False, 0
        
        # 4. Calculate severity with regime boost
        severity = self.calculate_severity(
            primary_residual=primary_residual if self.residual_mode else primary_z,
            secondary_residual=getattr(snapshot, f'z_{self.secondary_feature}_residual_m_1') if self.residual_mode else getattr(snapshot, f'z_{self.secondary_feature}_m_1'),
            regime_boost=self._get_regime_boost(snapshot)
        )
        
        return True, severity
```

**Data Model Extensions:**
```python
class EnhancedFeatureSnapshot(FeatureSnapshot):
    # Residual Features
    z_cross_sectional_residual_m_1: Optional[float] = None
    cross_sectional_prediction_m_1: Optional[float] = None
    cross_sectional_prediction_std_m_1: Optional[float] = None
    factor_loadings: Optional[Dict] = None
    
    z_kalman_residual_m_1: Optional[float] = None
    kalman_state: Optional[List[float]] = None
    kalman_innovation: Optional[float] = None
    kalman_prediction_std_m_1: Optional[float] = None
    
    # ... other residual features
    
    # Regime Classification
    atr_percentile_252: Optional[float] = None
    volatility_regime: Optional[str] = None
    trend_regime: Optional[str] = None
    session_phase: Optional[str] = None
    market_regime: Optional[str] = None
    liquidity_regime: Optional[str] = None
```

**Database Schema Migration:**
```sql
-- Add residual feature columns
ALTER TABLE feature_snapshots ADD COLUMN z_cross_sectional_residual_m_1 FLOAT;
ALTER TABLE feature_snapshots ADD COLUMN cross_sectional_prediction_m_1 FLOAT;
ALTER TABLE feature_snapshots ADD COLUMN cross_sectional_prediction_std_m_1 FLOAT;
ALTER TABLE feature_snapshots ADD COLUMN factor_loadings JSONB;

-- Add regime classification columns
ALTER TABLE feature_snapshots ADD COLUMN atr_percentile_252 FLOAT;
ALTER TABLE feature_snapshots ADD COLUMN volatility_regime VARCHAR(20);
ALTER TABLE feature_snapshots ADD COLUMN trend_regime VARCHAR(20);
ALTER TABLE feature_snapshots ADD COLUMN session_phase VARCHAR(20);
ALTER TABLE feature_snapshots ADD COLUMN market_regime VARCHAR(20);
ALTER TABLE feature_snapshots ADD COLUMN liquidity_regime VARCHAR(20);

-- Add indexes for performance
CREATE INDEX idx_feature_snapshots_residuals ON feature_snapshots (z_cross_sectional_residual_m_1, z_kalman_residual_m_1);
CREATE INDEX idx_feature_snapshots_regime ON feature_snapshots (volatility_regime, trend_regime, market_regime);
```

**Configuration Management:**
```yaml
# Enable residual mode
residual_mode:
  enabled: true
  transition_period_days: 30
  fallback_to_zscore: true

# Residual factory configuration
residual_factories:
  cross_sectional:
    enabled: true
    retrain_frequency: "1d"
    lookback_days: 252
  
  kalman:
    enabled: true
    retrain_frequency: "1d"
    state_dimension: 3
  
  # ... other factories

# Regime gate configuration
regime_gates:
  atr_percentile:
    enabled: true
    min_value: 20
    max_value: 90
  
  adx_bands:
    enabled: true
    min_value: 12
    max_value: 35
  
  # ... other gates
```

**Testing Strategy:**
- [ ] **Unit Tests**: Test each residual factory in isolation
- [ ] **Integration Tests**: Test feature builder with residual factories
- [ ] **Detector Tests**: Test detectors with residual triggers
- [ ] **Regression Tests**: Ensure existing functionality still works
- [ ] **Performance Tests**: Measure latency impact of residual computation
- [ ] **A/B Testing**: Compare z-score vs residual performance

**Deployment Strategy:**
- [ ] **Phase 1**: Deploy residual factories alongside existing z-score logic
- [ ] **Phase 2**: Enable residual mode for testing with subset of symbols
- [ ] **Phase 3**: Gradually migrate all symbols to residual mode
- [ ] **Phase 4**: Remove z-score logic after validation period
- [ ] **Monitoring**: Track performance metrics throughout transition

### Model Training Implementation Details (Phase 1 Addition)

**Purged Cross-Validation Implementation:**
- [ ] **Time Series Split**: Use `TimeSeriesSplit` with purged gaps to prevent data leakage
- [ ] **Purge Windows**: 5-day purge before test period, 5-day purge after test period
- [ ] **Rolling Validation**: 252-day training window, 21-day test window
- [ ] **Performance Metrics**: R², MAE, RMSE, Sharpe ratio for each fold
- [ ] **Model Selection**: Best model based on average OOS performance across folds

**False Discovery Rate Control:**
- [ ] **Benjamini-Hochberg Procedure**: Control FDR at α=0.05 level
- [ ] **P-value Calculation**: Use permutation tests for feature significance
- [ ] **Multiple Testing**: Adjust for multiple comparisons across features and time
- [ ] **Feature Selection**: Only include features with FDR-adjusted p-values < 0.05

**Rolling Out-of-Sample Validation:**
- [ ] **Expanding Window**: Start with 252 days, expand by 1 day each iteration
- [ ] **Walk-Forward Analysis**: Retrain models every 21 days using expanding window
- [ ] **Performance Tracking**: Track model performance degradation over time
- [ ] **Retrain Triggers**: Retrain when performance drops below threshold

**Model Retraining Schedule:**
- [ ] **Cross-Sectional**: Daily retraining at market close
- [ ] **Kalman**: Daily retraining with 30-day lookback
- [ ] **Order Flow**: Hourly retraining with 60-minute lookback
- [ ] **Basis/Carry**: Daily retraining with 30-day lookback
- [ ] **Lead-Lag Network**: Daily retraining with 252-day lookback
- [ ] **Breadth/Market Mode**: Daily retraining with 30-day lookback
- [ ] **Volatility Surface**: Daily retraining with 30-day lookback
- [ ] **Seasonality**: Weekly retraining with 252-day lookback

**Training Data Management:**
- [ ] **Data Quality Gates**: Only train on data with DQ status = OK
- [ ] **Outlier Handling**: Use IQR method to remove extreme outliers
- [ ] **Missing Data**: Forward-fill for gaps < 5 minutes, skip for larger gaps
- [ ] **Feature Engineering**: Compute all features before training
- [ ] **Target Variable**: Use forward returns at multiple horizons (1m, 5m, 30m, 4h, 1d)

**Model Performance Monitoring:**
- [ ] **R² Score**: Track R² score for each factory over time
- [ ] **MAE/RMSE**: Monitor prediction accuracy
- [ ] **Sharpe Ratio**: Track risk-adjusted returns of predictions
- [ ] **Regime Performance**: Track performance by market regime
- [ ] **Feature Importance**: Monitor feature importance changes over time
- [ ] **Model Drift**: Detect when model performance degrades significantly

**Retraining Triggers:**
- [ ] **Performance Threshold**: Retrain when R² < 0.1 for 3 consecutive days
- [ ] **Regime Change**: Retrain when market regime changes significantly
- [ ] **Feature Drift**: Retrain when feature distributions change significantly
- [ ] **Scheduled Retraining**: Daily retraining for all factories
- [ ] **Emergency Retraining**: Immediate retraining on model failure

### Pattern Detection Requirements (Phase 1 Addition)

**Critical Features Needed:**
- [ ] **Candlestick Patterns**: Doji, hammer, shooting star, engulfing, harami, three soldiers/crows
- [ ] **Support/Resistance Detection**: Level identification, breakout detection, reclaim detection
- [ ] **Chart Patterns**: Wedges, flags, triangles, head & shoulders, double tops/bottoms
- [ ] **Pattern Confirmation**: Volume confirmation, time confirmation, strength scoring
- [ ] **Level Detection**: Prior day/week/month highs/lows, VWAP levels, round numbers, Fibonacci

**Pattern Detection Types:**
- [ ] **Candlestick Patterns** (single bar) - Priority #1
- [ ] **Support/Resistance Breakouts** (multi-bar) - Priority #2
- [ ] **Chart Patterns** (multi-bar) - Priority #3
- [ ] **Pattern Confirmation** (volume, time, strength) - Priority #4

**Implementation Strategy:**
- [ ] **Mechanical Detection**: Fixed algorithms for pattern recognition
- [ ] **Volume Confirmation**: Volume spikes confirm pattern breakouts
- [ ] **Time Confirmation**: Patterns need sufficient time development
- [ ] **Strength Scoring**: Quantified pattern strength and completion percentage
- [ ] **Target/Stop Loss**: Automated target and stop loss calculation

## Orthogonality & Cost v0.3 (Weeks 6-7)

**Environment**: Rolling correlation vs actives; turnover & impact estimator; incorporate into S_i.
**Focus**: Diversity maintenance and cost control.
**Control**: Automated orthogonality checks and cost monitoring.

*Source: [alpha_detector_build_convo.md §24.3](../alpha_detector_build_convo.md#phase-2--rollups--retention-weeks-67)*

### Scope
- 15m & 1h rollups (recompute, not average)
- Retention/pruning jobs (1m 90d, 15m 1y, 1h 3y)
- Partitioning & compression
- Index hygiene

### Milestones
- **M2.1**: Rollups validated (Σ volume equalities, OHLC enclosure)
- **M2.2**: Storage footprint matches plan ±15%

### Gate Criteria
- Rollup validation suite green
- Query latency (recent cross-section) < 100ms p95

### Deliverables
- [ ] Rollup computation engine
- [ ] Retention/pruning automation
- [ ] Partitioning strategy implemented
- [ ] Compression enabled
- [ ] Query optimization

## Operator Rituals v0.4 (Weeks 8-10)

**Environment**: UI/CLI to prune, annotate, and embargo narrative overrides.
**Focus**: Operator stewardship and manual intervention capabilities.
**Control**: Audit trail on every lifecycle decision.

*Source: [alpha_detector_build_convo.md §24.4](../alpha_detector_build_convo.md#phase-3--microstructure--positioning-weeks-810)*

### Scope
- L2-based features (spread_p95, OBI, depth) guarded by DQ
- OI polling cadence; positioning detectors
- Basis/funding detectors with staleness rules

### Milestones
- **M3.1**: L2-guarded detectors produce stable signals
- **M3.2**: OI freshness ≥ 95% within 20s

### Gate Criteria
- Suppression due to DQ < 10% for micro detectors
- Severity distributions healthy

### Deliverables
- [ ] L2 order book processing
- [ ] OI polling system
- [ ] Positioning detectors
- [ ] Basis/funding detectors
- [ ] DQ gates for micro features

## Prod Pilot v1.0 (Weeks 11-13)

**Environment**: Canary routing: % of capital to active cohort; guardrails on dq_status, universe churn.
**Focus**: Production deployment with evolutionary controls.
**Control**: Gradual rollout with performance monitoring.

*Source: [alpha_detector_build_convo.md §24.5](../alpha_detector_build_convo.md#phase-4--curator--replays-weeks-1113)*

### Scope
- **Curator v0.1** (statistical monitors, proposals, budget/threshold diffs)
- **Dead Branches System** (failure logging, pattern recognition, institutional memory)
- **Backtesting Framework** (quick validation, lightweight testing, early feedback)
- **Trader Feedback Integration** (real P&L data, live performance metrics)
- Replay harness (golden minutes + recent day)
- Config epochs, canary & rollback workflows

### Milestones
- **M4.1**: First proposals generated & applied via canary
- **M4.2**: Weekly Curator report produced automatically

### Gate Criteria
- Zero hot-path mutations
- Proposals only via replay-approved packs

### Deliverables
- [ ] Curator monitoring system
- [ ] Proposal generation
- [ ] Replay harness
- [ ] Config management system
- [ ] Canary/rollback workflows

## Phase 5 — Hardening & Extensibility (Weeks 14-16)

*Source: [alpha_detector_build_convo.md §24.6](../alpha_detector_build_convo.md#phase-5--hardening--extensibility-weeks-1416)*

### Scope
- Failure runbooks exercised
- Shadow new detectors (divergence/synchrony/rotation refinements)
- Extensibility plumbing (extras_json → promotion path)
- Security posture (RBAC, secrets, audit)

### Milestones
- **M5.1**: Incident game-day pass
- **M5.2**: New feature promoted from extras_json to column via FP minor bump

### Gate Criteria
- All SLOs met at 35 symbols
- Ops dashboard complete
- Audit trail validated

### Deliverables
- [ ] Incident response procedures
- [ ] Security hardening
- [ ] Extensibility framework
- [ ] Complete operational documentation
- [ ] Performance optimization

## Phase 6 — Trading Feedback Integration (Weeks 17-19)

*Source: [alpha_detector_build_convo.md §14.7](../alpha_detector_build_convo.md#artifacts-tables)*

### Scope
- Database-only trading feedback integration
- Performance-based Curator monitoring
- Signal performance tracking and aggregation
- Market regime analysis and detector tuning

### Milestones
- **M6.1**: Trading system writes performance data to database
- **M6.2**: Curator generates performance-based proposals
- **M6.3**: Detector thresholds auto-adjust based on performance

### Gate Criteria
- Database processes 1000+ performance records/hour
- Performance metrics calculated within 5 minutes
- Curator proposals include performance evidence

### Deliverables
- [ ] Signal performance tracking tables
- [ ] Database triggers for performance updates
- [ ] Performance-based Curator monitors
- [ ] Market regime analysis
- [ ] Automated detector tuning
- [ ] Performance dashboard

### Trading Feedback Requirements (Phase 6 Addition)

**Critical Features Needed:**
- [ ] **Signal Performance Tracking**: Individual signal outcome recording in database
- [ ] **Detector Performance Aggregation**: Performance metrics by detector and regime
- [ ] **Market Regime Analysis**: Performance breakdown by market conditions
- [ ] **Performance-Based Proposals**: Curator proposals based on real trading results
- [ ] **Automated Tuning**: Threshold adjustments based on performance degradation

**Database Implementation:**
- [ ] **signal_performance table**: Store individual signal outcomes
- [ ] **detector_performance table**: Aggregate performance metrics
- [ ] **Database triggers**: Notify Curator of new performance data
- [ ] **Performance views**: Query performance metrics efficiently

**Performance Monitoring:**
- [ ] **Accuracy Tracking**: Signal direction accuracy over time
- [ ] **Precision/Recall**: Signal quality metrics by detector
- [ ] **Regime Performance**: Performance breakdown by market regime
- [ ] **Drawdown Analysis**: Risk metrics for each detector

## Phase 7 — Advanced Performance Intelligence (Weeks 20-22)

*Source: [alpha_detector_build_convo.md §14.6](../alpha_detector_build_convo.md#llm-assisted-analyses-offline-bounded)*

### Scope
- Machine learning integration for performance prediction
- Advanced regime detection and adaptation
- A/B testing framework for new detectors
- Dynamic weight optimization

### Milestones
- **M7.1**: ML models predict detector performance
- **M7.2**: A/B testing framework operational
- **M7.3**: Dynamic detector weights based on performance

### Gate Criteria
- ML predictions improve detector selection by 15%
- A/B tests complete within 48 hours
- Dynamic weights reduce false positives by 20%

### Deliverables
- [ ] ML performance prediction models
- [ ] A/B testing framework
- [ ] Dynamic weight optimization
- [ ] Advanced regime detection
- [ ] Performance forecasting

## Acceptance Criteria

*Source: [alpha_detector_build_convo.md §25](../alpha_detector_build_convo.md#acceptance-criteria--exit-checklist)*

### Functional Acceptance (v1.0)
- [ ] WS ingest stable across all feeds
- [ ] 1m snapshots contain all v1.0 columns with correct naming & units
- [ ] DQ fields present and accurate; warm-up honored
- [ ] Baselines persist & restore; z-means in [-0.2, +0.2] and z-std in [0.8, 1.2]
- [ ] All v0.1 detectors enabled; triggers match spec
- [ ] Event payloads conform to schema; UUIDv7, provenance filled
- [ ] Market snapshots written per minute with all context

### Non-Functional Acceptance
- [ ] Latency: end-to-end p95 < 450ms, p99 < 800ms at 35 symbols
- [ ] Reliability: Availability 99.9%/30d of hot path
- [ ] Determinism: Golden minutes replay produces bit-identical payloads
- [ ] Storage: Daily growth within ±20% of plan

### Operational Acceptance
- [ ] Dashboards: ingest, pipeline, events, curator; all panels populated
- [ ] Alerts: WS flap, latency breach, DQ deterioration, event flood, drift
- [ ] Runbooks: WS reconnect, latency spike, DB outage, event flood; tested
- [ ] RBAC: least-privilege service roles active; audit logs on config changes

### Security Acceptance
- [ ] Secrets in vault; no secrets in logs or repos
- [ ] TLS enforced; egress allow-list to HL endpoints
- [ ] Backups/DR tested (restore dry-run)
- [ ] Image signing/verification configured; deps pinned

## Exit Checklist

*Source: [alpha_detector_build_convo.md §25.7](../alpha_detector_build_convo.md#exit-checklist-one-page)*

- [ ] SLOs hit at 35 symbols; degraded modes verified
- [ ] v1.0 feature columns present; names & units validated
- [ ] Event payload contract v0.1 validated by consumer tests
- [ ] Budgets & debounce functioning; suppression < 5%
- [ ] Registries populated; packs versioned; config_hash stable
- [ ] Golden minutes: bit-identical; last-day replay within bounds
- [ ] Retention/pruning running; storage growth within plan
- [ ] Dashboards/alerts live; runbooks tested
- [ ] RBAC, secrets, TLS, backups, image signing verified
- [ ] Change log updated; go-live decision recorded

## Risk Mitigation

### Technical Risks
- **Non-determinism**: Use canonical JSON, decimal quantization, fixed seeds
- **Performance**: Enable detector deferral, reduce universe size under load
- **Data Quality**: Implement comprehensive DQ gates and monitoring

### Operational Risks
- **WS Instability**: Exponential backoff, graceful degradation
- **DB Outages**: Write-ahead logging, batch recovery
- **Config Errors**: Replay validation, canary deployments

### Business Risks
- **Scope Creep**: Strict phase gates, clear acceptance criteria
- **Timeline Pressure**: Phased delivery, early value demonstration
- **Integration Issues**: Clear API contracts, consumer examples

---

*For complete roadmap and milestone details, see [alpha_detector_build_convo.md §24-25](../alpha_detector_build_convo.md#phase-roadmap--milestones)*
