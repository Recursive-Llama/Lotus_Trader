# Kernel Resonance System Specification

*Source: Enhanced formula integration with Alpha Detector system*

## Overview

The Kernel Resonance System implements a sophisticated two-layer detector selection approach that combines Simons-style core metrics with phase-aligned resonance scoring. This system enhances the traditional selection score (S_i) with kernel resonance (Δφ) to create a more predictive and regime-aware selection mechanism.

**Important**: This system operates on **signal quality metrics** for detector selection. Trade profitability analysis (psi_score) is handled separately by the trading system and fed back as performance feedback.

## Mathematical Foundation

### Core Selection Layer (Simons) - Signal Quality Metrics (sq_* namespace)
```python
# Signal quality score (NOT trade profitability)
sq_score = w_accuracy * sq_accuracy + w_precision * sq_precision + w_stability * sq_stability + w_orthogonality * sq_orthogonality - w_cost * sq_cost
```

### Phase Resonance Layer (Kernel) (kr_* namespace)
```python
# Kernel resonance components
kr_hbar = σ(zscore(Page_Hinkley_statistic))        # Market surprise/structural breaks
kr_coherence = spectral_coherence(signal, returns)  # Spectral coherence with returns
kr_phi = |corr(PnL, opportunity_factor)|           # Field resonance/regime alignment
kr_theta = entropy_penalty(memberships)            # Context complexity penalty
kr_rho = complexity_penalty(strategy_dsl)          # Recursive depth penalty
kr_emergence = improvement_slope(sq_score)         # Emergence potential
kr_novelty = embedding_distance(embedding, cohort) # Novelty in embedding space

# Kernel resonance calculation
kr_delta_phi = kr_hbar * kr_coherence * (
    kr_phi**alpha * kr_novelty**beta * kr_emergence**gamma
) / ((1 - kr_theta)**delta * (1 - kr_rho)**epsilon + 1e-6)
```

### Final Selection Score (det_* namespace)
```python
# Geometric blend of both layers
det_sigma = sq_score**u * kr_delta_phi**(1-u)

# Uncertainty abstention
det_abstained = (det_uncert > tau_U) OR (dq_status != 'ok')
```

## Implementation Details

### Database Schema Integration

The system extends the existing `detector_metrics_daily` table with kernel resonance fields:

```sql
-- Signal Quality Metrics (sq_* namespace)
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
```

### State-Space Process Implementation

**Kernel State Variables (per detector i):**
- `kr_phi_i(t)` = field alignment
- `kr_theta_i(t)` = context complexity  
- `kr_rho_i(t)` = recursive depth/complexity

**Update Rules (discrete time):**
```python
# State updates
kr_phi_i(t)   = kr_phi_i(t-1) * kr_rho_i(t)
kr_theta_i(t) = kr_theta_i(t-1) + kr_hbar(t) * Σ_j [ kr_phi_j(t) * kr_rho_j(t) ]
kr_rho_i(t+1) = σ( kr_rho_i(t) + α * kr_delta_phi_i(t) - λ * kr_rho_i(t) )

# Sigmoid function
σ(x) = 1 / (1 + e^{-x})
```

**Interpretation:**
- `kr_hbar(t)` couples detectors via surprise (structural breaks raise `kr_theta` globally)
- Complexity grows only when resonance paid for it (`kr_delta_phi_i(t) > 0`), and decays via λ

### Kairos & Entrainment Implementation

**Market Spectrum Analysis:**
```python
# Market spectrum (Fourier/Wavelet)
X(ω_k,t) = market_spectrum(frequency_k, time_t)

# Detector weight
W_i(t) = kr_phi_i(t) * kr_theta_i(t) * kr_rho_i(t)
```

**Kairos Score (Timing):**
```python
det_kairos_i(t) = [ Σ_k |X(ω_k,t)| * cos( angle(X(ω_k,t)) - phase_i(ω_k) ) * w_k ] / [ Σ_k |X(ω_k,t)| * w_k ] * W_i(t) / ( max_j W_j(t) + ε )
```

**Entrainment (Ensemble Coherence):**
```python
det_entrain_r(t) * e^{i Ψ(t)} = (1/M) * Σ_{m=1..M} e^{i φ_m(t)}
```

### Execution Gate Implementation

**Complete Gate Logic:**
```python
# Trade only if all conditions are met
Trade only if:
  det_kairos_i(t) ≥ τ_K
  det_entrain_r(t) ≥ τ_r
  det_uncert_i(t) ≤ τ_U
  and data quality ok
```

### Observer Effect & Regularization

**Contraction Mapping:**
```python
# Braid/prior update operator must be a contraction
|| T(p) - T(q) || ≤ L || p - q ||, with L < 1 (weight-decay / early-stop)
```

**Witness Penalty (Crowding):**
```python
# If detector's capital share or selection frequency is high
if detector_capital_share > threshold:
    kr_coherence_i(t) *= 0.95  # Slight shrinkage
    kr_phi_i(t) *= 0.95
```

**Mean Reversion:**
```python
# Mean-revert kr_theta
kr_theta(t+1) = kr_theta(t) + kr_hbar*S - η*(kr_theta(t) - θ_bar)
```

### Sanity Constraints

**State Variable Clipping:**
```python
# Clip all state variables to [0,1]
kr_phi_i(t) = clip(kr_phi_i(t), 0, 1)
kr_theta_i(t) = clip(kr_theta_i(t), 0, 1)
kr_rho_i(t) = clip(kr_rho_i(t), 0, 1)
```

**Regularization:**
```python
# Regularize kr_rho with λ; ensure linearized spectral radius < 1
kr_rho_i(t+1) = kr_rho_i(t) + α * kr_delta_phi_i(t) - λ * kr_rho_i(t)
```

### Computation Pipeline

1. **Data Collection**: Gather detector performance, market regime, and embedding data
2. **Component Calculation**: Compute each kernel resonance component
3. **Kernel Integration**: Calculate delta_phi using the kernel formula
4. **Selection Scoring**: Blend psi_score and delta_phi into sigma_select
5. **Uncertainty Assessment**: Calculate disagreement variance across detector variants
6. **Abstention Decision**: Determine if execution should be abstained

### Configuration Parameters

```yaml
kernel_resonance:
  # Geometric blend weights
  u: 0.6                    # Weight for Simons core (psi_score)
  
  # Phase resonance weights
  alpha: 1.0                # Field resonance (phi_field) weight
  beta: 0.8                 # Novelty (nov_novelty) weight  
  gamma: 0.8                # Emergence (kx_emergence) weight
  delta: 0.7                # Context complexity penalty weight
  epsilon: 0.7              # Depth complexity penalty weight
  
  # Selection thresholds
  sigma_min: 0.35           # Minimum sigma_select for promotion
  sigma_deprecate: 0.05     # Sigma threshold for deprecation
  uncertainty_max: 0.3      # Maximum uncertainty for execution
  
  # Computation parameters
  surprise_window: 252      # Days for structural break detection
  coherence_bands: [0.1, 0.9]  # Frequency bands for spectral coherence
  novelty_embedding_dim: 1536  # Embedding dimension for novelty
  emergence_slope_window: 30   # Days for emergence slope calculation
```

## Operator Guidelines

### Daily Monitoring
- **sigma_select**: Final selection score (geometric blend of psi_score + delta_phi)
- **delta_phi**: Kernel resonance (surprise × coherence × field alignment × novelty × emergence)
- **uncert_disagreement**: Uncertainty variance across detector variants
- **abstained**: Abstention decisions due to high uncertainty

### Operator Heuristics
- **Low surprise (ℏ), high coherence (ψ(ω))**: Favor high psi_score incumbents
- **High surprise spikes**: Prioritize high novelty (N) and emergence (⚘) detectors
- **High uncertainty**: Abstain from execution, let cohort resolve
- **Regime breaks**: Bias toward high field resonance (φ) detectors

### Alerts
- "Kernel resonance degradation" when delta_phi < 0.2
- "High uncertainty detected" when uncert_disagreement > 0.3
- "Selection score divergence" when sigma_select vs psi_score differ > 0.3

## Integration with Existing System

### Detector Lifecycle
1. **Experimental**: Detectors start with basic psi_score calculation
2. **Active**: Enhanced with kernel resonance components
3. **Promotion**: Based on sigma_select (not just psi_score)
4. **Deprecation**: Based on sigma_select degradation
5. **Abstention**: Automatic when uncertainty exceeds threshold

### Curator Integration
- **Performance Monitoring**: Track both psi_score and delta_phi trends
- **Proposal Generation**: Suggest detector tuning based on kernel resonance
- **Regime Adaptation**: Adjust weights based on market regime changes
- **Uncertainty Management**: Monitor and respond to high disagreement periods

## Benefits

1. **Enhanced Selection**: More sophisticated detector selection than simple S_i
2. **Regime Awareness**: Phase-aligned selection that adapts to market conditions
3. **Uncertainty Management**: Automatic abstention during high uncertainty periods
4. **Novelty Preservation**: Explicit tracking and reward of novel detector approaches
5. **Emergence Detection**: Identification of detectors with learning potential
6. **Complexity Management**: Penalties for over-engineered detectors

## Future Enhancements

1. **Dynamic Weighting**: Adaptive weights based on market regime
2. **Multi-Scale Resonance**: Different resonance calculations for different timeframes
3. **Cross-Asset Resonance**: Resonance calculations across asset classes
4. **Temporal Resonance**: Time-of-day and seasonal resonance patterns
5. **Ensemble Resonance**: Resonance calculations for detector ensembles

---

*This specification integrates the enhanced kernel resonance formula with the Alpha Detector system, providing a more sophisticated and regime-aware approach to detector selection and management.*
