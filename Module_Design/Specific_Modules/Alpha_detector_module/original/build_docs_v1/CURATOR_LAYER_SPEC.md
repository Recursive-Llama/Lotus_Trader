# Curator Layer Specification

*Source: [alpha_detector_build_convo.md](../alpha_detector_build_convo.md) + Enhanced Governance Design*

## Overview

The Curator Layer provides **governed human/agent stewardship** through a council of small, bounded curators. Each curator has a narrow mandate and limited levers—so stewardship improves selection without narrative creep.

## Core Principle

**Numbers in charge, curators can tilt, not overturn.**

Keep machine score `det_sigma` as the anchor. Curators can only:
- **Block** (binary veto flags), or  
- **Apply bounded log-space nudges** that cannot overwhelm the machine score

## Curator Roles (Narrow, Composable)

### 1. Data Curator
**Mandate**: Provenance, freshness, nulls, outliers
- **Hard veto**: DQ breach
- **Soft nudge**: Data quality improvements

### 2. Leakage Curator  
**Mandate**: Future leakage, label bleed, look-ahead transforms
- **Hard veto**: Any leak test fails
- **Soft nudge**: Feature engineering improvements

### 3. Diversity Curator
**Mandate**: Orthogonality & novelty targets
- **Soft nudge**: Prioritize underrepresented clusters
- **Hard veto**: Cohort correlation cap breach

### 4. Regime Curator
**Mandate**: Validates kr_hbar, det_entrain_r sanity; suggests exploration/exploitation mix
- **Soft nudge only**: No veto power
- **Focus**: Market regime alignment

### 5. Ethics/Compliance Curator
**Mandate**: Domain-specific exclusions (if any)
- **Hard veto**: When policy hit
- **Soft nudge**: Compliance improvements

### 6. Mutation Curator
**Mandate**: Controls breeding recipes (jitter ranges, recombine rules) given current weather
- **Soft nudge only**: No veto power
- **Focus**: Evolutionary parameters

### 7. Adversarial Curator (Red Team)
**Mandate**: Stress tests (simulated gaps, microstructure noise, slippage shocks)
- **Hard veto**: If fragility above cap
- **Soft nudge**: Robustness improvements

### 8. Explainability Curator
**Mandate**: Validates detector cards are complete & reproducible
- **Hard veto**: On missing proofs
- **Soft nudge**: Documentation improvements

## Curator Math (Bounded Influence)

### Curator Contributions
Define curator contributions `c_{j,i} ∈ [-κ_j, +κ_j]` with small caps (e.g., `κ_j ≤ 0.15`).

### Final Curated Score
```python
log Σ̃_i = log(det_sigma_i) + Σ_{j∈soft} c_{j,i}
```

### Publication Decision
Publish if:
- No hard veto flags, AND
- `Σ̃_i ≥ τ_publish`

## Curator KPIs (So We Know It Works)

### Performance Metrics
- **False promotion rate**: Promoted→deprecated quickly
- **Survival uplift**: Days above threshold vs. baseline
- **Diversity index**: Effective number of active species
- **Audit pass rate**: Pre- vs post-curation
- **Time-to-publish**: Latency added by curation

### Quality Metrics
- **Veto accuracy**: How often vetoes prevent failures
- **Nudge effectiveness**: Impact of soft nudges on performance
- **Curator agreement**: Inter-curator consensus rates

## Database Schema

### Curator Actions Table
```sql
CREATE TABLE curator_actions (
    id UUID PRIMARY KEY,
    detector_id UUID REFERENCES detector_registry(id),
    curator_type TEXT NOT NULL,  -- 'data', 'leakage', 'diversity', etc.
    action_type TEXT NOT NULL,   -- 'veto', 'nudge', 'approve'
    contribution FLOAT8,         -- c_{j,i} for nudges
    reason TEXT,
    evidence JSONB,             -- Supporting data
    created_at TIMESTAMP DEFAULT NOW(),
    curator_version TEXT        -- For audit trail
);
```

### Curator KPIs Table
```sql
CREATE TABLE curator_kpis (
    id UUID PRIMARY KEY,
    curator_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value FLOAT8,
    measurement_window_start TIMESTAMP,
    measurement_window_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## API Endpoints

### Curator Actions
```python
# Soft nudge (bounded contribution)
POST /curation/propose
{
    "detector_id": "uuid",
    "curator_type": "diversity", 
    "contribution": 0.05,  # Must be ≤ κ_j
    "reason": "Underrepresented cluster",
    "evidence": {...}
}

# Hard veto (blocks publication)
POST /curation/veto
{
    "detector_id": "uuid",
    "curator_type": "leakage",
    "reason": "Future leakage detected",
    "evidence": {...}
}

# Get curation summary
GET /curation/summary/{detector_id}
```

## Implementation Notes

### Bounded Influence Enforcement
- All curator contributions are capped by `κ_j`
- Hard vetoes are binary and absolute
- Soft nudges are additive in log-space only
- Full audit trail for all curator actions

### Curator Training
- Each curator has specific training on their domain
- Regular calibration against ground truth
- Performance feedback loops
- Rotation to prevent bias

### Escalation Paths
- Curator disagreements go to arbitration
- System can override curators in extreme cases
- All overrides are logged and reviewed

## Integration with Existing System

The Curator Layer sits between the **Kernel Resonance System** and **Signal Publication**:

1. **Kernel Resonance** computes `det_sigma`
2. **Curator Layer** applies bounded influence → `curated_sigma`
3. **Signal Publication** emits signals based on `curated_sigma`

This maintains the mathematical integrity while adding human oversight where needed.
