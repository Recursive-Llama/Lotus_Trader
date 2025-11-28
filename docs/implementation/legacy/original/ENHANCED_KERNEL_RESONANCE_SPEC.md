# Enhanced Kernel Resonance Specification - Trading Intelligence System

*Source: [build_docs_v1/KERNEL_RESONANCE_SPEC.md](../build_docs_v1/KERNEL_RESONANCE_SPEC.md) + Trading Intelligence System Integration*

## Overview

The Enhanced Kernel Resonance System implements a sophisticated two-layer detector selection approach that combines Simons-style core metrics with phase-aligned resonance scoring. This system enhances the traditional selection score (S_i) with kernel resonance (Δφ) to create a more predictive and regime-aware selection mechanism, now integrated with **DSI evidence** and **module intelligence**.

**Important**: This system operates on **signal quality metrics** for detector selection. Trade profitability analysis (psi_score) is handled separately by the trading system and fed back as performance feedback.

## Mathematical Foundation

### Core Selection Layer (Simons) - Signal Quality Metrics (sq_* namespace)

```python
# Signal quality score (NOT trade profitability)
sq_score = w_accuracy * sq_accuracy + w_precision * sq_precision + w_stability * sq_stability + w_orthogonality * sq_orthogonality - w_cost * sq_cost
```

#### **Detailed Calculations**

**sq_accuracy (directional hit rate, confidence-weighted):**
```python
# Windowing: use a pinned evaluation window per detector (e.g., 60d, bar-aligned)
# Let r_t→t+h be forward return for horizon h
# Let s_t be the detector's standardized signal

sq_accuracy = Σ_t 1{sign(s_t) = sign(r_t→t+h)} ⋅ |s_t| / Σ_t |s_t|
```

**sq_precision (signal sharpness via slope t-stat):**
```python
# Regression: r_t→t+h = β*s_t + ε_t
# sq_precision = |β̂| / SE(β̂) clipped to [0, T_max]
# Optionally rescale to [0,1] by logistic on the t-stat

sq_precision = clip01(t_stat(beta, se).logistic())
```

**sq_stability (consistency over time):**
```python
# Rolling window correlation of signal with future returns
# sq_stability = mean(corr(s_t, r_t→t+h)) over rolling windows

sq_stability = mean([corr(s_t[i:i+w], r_t→t+h[i:i+w]) for i in range(0, len(s_t)-w, step)])
```

**sq_orthogonality (uniqueness vs active cohort):**
```python
# sq_orthogonality = 1 - max(corr(s_i, s_j)) for j ≠ i in active cohort

sq_orthogonality = 1 - max([corr(s_i, s_j) for j in active_cohort if j != i])
```

**sq_cost (trading cost penalty):**
```python
# sq_cost = estimated_slippage / signal_strength
# Higher cost = lower score

sq_cost = min(estimated_slippage / (|s_t| + ε), 1.0)
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

# Dynamic adjustment based on market conditions and module state
def calculate_dynamic_adjustment(kr_hbar, kr_coherence, kr_theta, kr_rho, kr_phi, t):
    """Calculate dynamic adjustment to kernel resonance"""
    surprise_threshold = kr_hbar
    resonance_wave = kr_coherence * np.sin(2 * np.pi * kr_phi * t)
    context_integral = kr_theta * kr_rho * kr_phi
    return surprise_threshold * resonance_wave * context_integral

# Apply dynamic adjustment
dynamic_adjustment = calculate_dynamic_adjustment(
    kr_hbar, kr_coherence, kr_theta, kr_rho, kr_phi, current_time
)

kr_delta_phi = kr_delta_phi + dynamic_adjustment
```

#### **Detailed Component Calculations**

**kr_hbar (Market Surprise/Structural Breaks):**
```python
# Page-Hinkley statistic for structural break detection
def page_hinkley_statistic(returns, threshold=0.1):
    cumulative_sum = np.cumsum(returns - np.mean(returns))
    max_deviation = np.max(cumulative_sum)
    min_deviation = np.min(cumulative_sum)
    ph_stat = max_deviation - min_deviation
    return ph_stat

# Normalize using z-score and sigmoid
kr_hbar = σ((page_hinkley_statistic(returns) - mean_ph) / std_ph)
```

**kr_coherence (Spectral Coherence with Returns):**
```python
# Spectral coherence between signal and returns
def spectral_coherence(signal, returns, frequencies):
    coherence_values = []
    for freq in frequencies:
        # Compute coherence at specific frequency
        signal_fft = np.fft.fft(signal)
        returns_fft = np.fft.fft(returns)
        
        # Cross-spectral density
        cross_spectrum = signal_fft * np.conj(returns_fft)
        signal_power = np.abs(signal_fft)**2
        returns_power = np.abs(returns_fft)**2
        
        # Coherence
        coherence = np.abs(cross_spectrum)**2 / (signal_power * returns_power + 1e-10)
        coherence_values.append(coherence)
    
    return np.mean(coherence_values)

kr_coherence = spectral_coherence(signal, returns, coherence_bands)
```

**kr_phi (Field Resonance/Regime Alignment):**
```python
# Correlation between PnL and opportunity factor
def field_resonance(pnl_series, opportunity_factor):
    # Opportunity factor: market regime indicator
    correlation = np.corrcoef(pnl_series, opportunity_factor)[0, 1]
    return np.abs(correlation)

kr_phi = field_resonance(pnl_series, opportunity_factor)
```

**kr_theta (Context Complexity Penalty):**
```python
# Entropy penalty for complex memberships
def entropy_penalty(memberships):
    # memberships: array of detector memberships in different regimes
    probabilities = memberships / np.sum(memberships)
    entropy = -np.sum(probabilities * np.log(probabilities + 1e-10))
    max_entropy = np.log(len(probabilities))
    normalized_entropy = entropy / max_entropy
    return normalized_entropy

kr_theta = entropy_penalty(memberships)
```

**kr_rho (Recursive Depth Penalty):**
```python
# Complexity penalty for strategy DSL depth
def complexity_penalty(strategy_dsl):
    # Count nested operations in strategy DSL
    depth = count_nested_operations(strategy_dsl)
    max_depth = 10  # Maximum allowed depth
    penalty = min(depth / max_depth, 1.0)
    return penalty

kr_rho = complexity_penalty(strategy_dsl)
```

**kr_emergence (Emergence Potential):**
```python
# Improvement slope of sq_score over time
def improvement_slope(sq_score_history, window=30):
    if len(sq_score_history) < window:
        return 0.0
    
    recent_scores = sq_score_history[-window:]
    slope = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
    return max(slope, 0.0)  # Only positive slopes

kr_emergence = improvement_slope(sq_score_history)
```

**kr_novelty (Novelty in Embedding Space):**
```python
# Distance from detector embedding to cohort centroid
def embedding_distance(detector_embedding, cohort_embeddings):
    centroid = np.mean(cohort_embeddings, axis=0)
    distance = np.linalg.norm(detector_embedding - centroid)
    max_distance = np.max([np.linalg.norm(emb - centroid) for emb in cohort_embeddings])
    normalized_distance = distance / (max_distance + 1e-10)
    return normalized_distance

kr_novelty = embedding_distance(detector_embedding, cohort_embeddings)
```

### Final Selection Score (det_* namespace)

```python
# Geometric blend of both layers
det_sigma = sq_score**u * kr_delta_phi**(1-u)

# Uncertainty abstention
det_abstained = (det_uncert > tau_U) OR (dq_status != 'ok')
```

#### **Enhanced Selection with DSI Integration**

```python
# Enhanced sigma with DSI evidence boost
det_enhanced_sigma = det_sigma * (1 + β_mx * mx_evidence) * (1 + γ_module * module_intelligence)

# DSI evidence boost factor
β_mx = 0.3  # DSI evidence weight
γ_module = 0.2  # Module intelligence weight

# Module intelligence contribution
module_intelligence = (
    learning_rate * 0.5 +
    innovation_score * 0.3 +
    collaboration_score * 0.2
)
```

## State-Space Process Implementation

### Kernel State Variables (per detector i)

- `kr_phi_i(t)` = field alignment
- `kr_theta_i(t)` = context complexity  
- `kr_rho_i(t)` = recursive depth/complexity

### Update Rules (discrete time)

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

## Observer Effect & Regularization

### Contraction Mapping

```python
# Braid/prior update operator must be a contraction
||| T(p) - T(q) || ≤ L || p - q ||, with L < 1 (weight-decay / early-stop)
```

### Witness Penalty (Crowding)

```python
# If detector's capital share or selection frequency is high
if detector_capital_share > threshold:
    kr_coherence_i(t) *= 0.95  # Slight shrinkage
    kr_phi_i(t) *= 0.95
```

### Mean Reversion

```python
# Mean-revert kr_theta
kr_theta(t+1) = kr_theta(t) + kr_hbar*S - η*(kr_theta(t) - θ_bar)
```

## Sanity Constraints

### State Variable Clipping

```python
# Clip all state variables to [0,1]
kr_phi_i(t) = clip(kr_phi_i(t), 0, 1)
kr_theta_i(t) = clip(kr_theta_i(t), 0, 1)
kr_rho_i(t) = clip(kr_rho_i(t), 0, 1)
```

### Regularization

```python
# Regularize kr_rho with λ; ensure linearized spectral radius < 1
kr_rho_i(t+1) = kr_rho_i(t) + α * kr_delta_phi_i(t) - λ * kr_rho_i(t)
```

## Computation Pipeline

1. **Data Collection**: Gather detector performance, market regime, and embedding data
2. **Component Calculation**: Compute each kernel resonance component
3. **Kernel Integration**: Calculate delta_phi using the kernel formula
4. **Selection Scoring**: Blend sq_score and delta_phi into sigma_select
5. **DSI Enhancement**: Apply DSI evidence boost
6. **Module Intelligence**: Apply module intelligence boost
7. **Uncertainty Assessment**: Calculate disagreement variance across detector variants
8. **Abstention Decision**: Determine if execution should be abstained

## Configuration Parameters

```yaml
kernel_resonance:
  # Geometric blend weights
  u: 0.6                    # Weight for Simons core (sq_score)
  
  # Phase resonance weights
  alpha: 1.0                # Field resonance (kr_phi) weight
  beta: 0.8                 # Novelty (kr_novelty) weight  
  gamma: 0.8                # Emergence (kr_emergence) weight
  delta: 0.7                # Context complexity penalty weight
  epsilon: 0.7              # Depth complexity penalty weight
  
  # DSI Integration weights
  beta_mx: 0.3              # DSI evidence boost weight
  gamma_module: 0.2         # Module intelligence boost weight
  
  # Selection thresholds
  sigma_min: 0.35           # Minimum sigma_select for promotion
  sigma_deprecate: 0.05     # Sigma threshold for deprecation
  uncertainty_max: 0.3      # Maximum uncertainty for execution
  
  # Computation parameters
  surprise_window: 252      # Days for structural break detection
  coherence_bands: [0.1, 0.9]  # Frequency bands for spectral coherence
  novelty_embedding_dim: 1536  # Embedding dimension for novelty
  emergence_slope_window: 30   # Days for emergence slope calculation
  
  # State space parameters
  alpha_state: 0.1          # State update learning rate
  lambda_decay: 0.05        # State decay rate
  eta_mean_reversion: 0.1   # Mean reversion rate
```

## Database Schema Integration

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
det_enhanced_sigma FLOAT8,          -- Enhanced selection score with DSI (0-1)
det_kairos FLOAT8,                  -- Kairos score (0-1)
det_entrain_r FLOAT8,               -- Entrainment order (0-1)
det_uncert FLOAT8,                  -- Uncertainty variance (0-1)
det_abstained BOOLEAN,              -- Abstention decision

-- DSI Integration
mx_evidence_boost FLOAT8,           -- DSI evidence boost factor
module_intelligence_boost FLOAT8,   -- Module intelligence boost factor
```

## Operator Guidelines

### Daily Monitoring
- **det_enhanced_sigma**: Final selection score with DSI and module intelligence
- **kr_delta_phi**: Kernel resonance (surprise × coherence × field alignment × novelty × emergence)
- **uncert_disagreement**: Uncertainty variance across detector variants
- **abstained**: Abstention decisions due to high uncertainty

### Operator Heuristics
- **Low surprise (ℏ), high coherence (ψ(ω))**: Favor high sq_score incumbents
- **High surprise spikes**: Prioritize high novelty (N) and emergence (⚘) detectors
- **High uncertainty**: Abstain from execution, let cohort resolve
- **Regime breaks**: Bias toward high field resonance (φ) detectors
- **DSI evidence**: Boost detectors with strong microstructure validation
- **Module intelligence**: Favor detectors with high learning and innovation

### Alerts
- "Kernel resonance degradation" when kr_delta_phi < 0.2
- "High uncertainty detected" when det_uncert > 0.3
- "Selection score divergence" when det_enhanced_sigma vs sq_score differ > 0.3
- "DSI evidence low" when mx_evidence < 0.3
- "Module intelligence degraded" when module_intelligence < 0.5

## Integration with Trading Intelligence System

### Detector Lifecycle
1. **Experimental**: Detectors start with basic sq_score calculation
2. **Active**: Enhanced with kernel resonance components
3. **DSI Integration**: Enhanced with microstructure evidence
4. **Module Intelligence**: Enhanced with learning and innovation
5. **Promotion**: Based on det_enhanced_sigma (not just sq_score)
6. **Deprecation**: Based on det_enhanced_sigma degradation
7. **Abstention**: Automatic when uncertainty exceeds threshold

### Curator Integration
- **Performance Monitoring**: Track sq_score, kr_delta_phi, and det_enhanced_sigma trends
- **DSI Validation**: Monitor microstructure evidence quality
- **Module Intelligence**: Track learning effectiveness and innovation
- **Proposal Generation**: Suggest detector tuning based on kernel resonance
- **Regime Adaptation**: Adjust weights based on market regime changes
- **Uncertainty Management**: Monitor and respond to high disagreement periods

## Benefits

1. **Enhanced Selection**: More sophisticated detector selection than simple S_i
2. **Regime Awareness**: Phase-aligned selection that adapts to market conditions
3. **DSI Integration**: Microstructure validation for all selections
4. **Module Intelligence**: Learning and innovation-driven selection
5. **Uncertainty Management**: Automatic abstention during high uncertainty periods
6. **Novelty Preservation**: Explicit tracking and reward of novel detector approaches
7. **Emergence Detection**: Identification of detectors with learning potential
8. **Complexity Management**: Penalties for over-engineered detectors

## Future Enhancements

1. **Dynamic Weighting**: Adaptive weights based on market regime
2. **Multi-Scale Resonance**: Different resonance calculations for different timeframes
3. **Cross-Asset Resonance**: Resonance calculations across asset classes
4. **Temporal Resonance**: Time-of-day and seasonal resonance patterns
5. **Ensemble Resonance**: Resonance calculations for detector ensembles
6. **Real-time DSI**: Continuous microstructure analysis
7. **Module Collaboration**: Inter-module intelligence sharing

---

*This enhanced specification integrates the sophisticated kernel resonance formula with the Trading Intelligence System, providing microstructure validation, module intelligence, and regime-aware detector selection.*
