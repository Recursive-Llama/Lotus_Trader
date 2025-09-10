# Alpha Data Detector - System Overview

*Source: [alpha_detector_build_convo.md](../alpha_detector_build_convo.md)*

## What This System Does

The Alpha Data Detector is an **evolutionary signal ecosystem** that:
- Ingests Hyperliquid data (WebSocket + REST)
- **Manufactures residuals** using predictive models on a time lattice (1m → 15m → 1h)
- **Breeds diverse detectors** that consume different residual combinations
- **Measures fitness** through selection scores (edge, stability, orthogonality, cost)
- **Evolves continuously** through mutation, recombination, and natural selection
- **Generates complete trading plans** with microstructure intelligence validation
- **Provides deep signal intelligence** through MicroTape analysis and micro-expert ecosystem
- Emits versioned events with severity scoring and regime context

**Key Principle**: This system **cultivates alpha** through evolutionary pressure—it generates complete trading plans with microstructure intelligence validation, enabling downstream systems to make informed decisions.

## Discovery as Selection (Why This Works)

Alpha emerges when we:
1. **Generate diverse hypotheses** (detectors/residuals)
2. **Measure them under identical conditions**
3. **Select for edge that persists**
4. **Reseed from survivors**

Let `D_i` be a detector's signal and `R` the residual stack available to it. We score detectors on edge, stability, orthogonality, and cost:

**Edge**: `IR_i = E[P_i] / σ(P_i)`
**Stability**: `1 - σ(rolling-IR_i) / |E[rolling-IR_i]| + ε`
**Orthogonality**: `1 - max_{j≠i} |ρ(P_i, P_j)|`
**Cost**: `slippage_i + fees_i + turnover_i · impact`

A single Selection Score drives promotion/retirement:
`S_i = w_e·Edge_i + w_s·Stability_i + w_o·Orthogonality_i - w_c·Cost_i`

**Rule**: No stories. Selection flows from `S_i` over controlled windows.

## Evolutionary System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   Evolution Lab  │    │   Outputs       │
│                 │    │                  │    │                 │
│ • HL WebSocket  │───▶│ • Residual DNA   │───▶│ • Event Bus     │
│ • HL REST       │    │ • Detector Species│    │ • Storage       │
│ • Context APIs  │    │ • Selection Engine│    │ • APIs          │
│                 │    │ • Mutation Lab   │    │                 │
│                 │    │ • Cohort Manager │    │                 │
│                 │    │ • Lifecycle Gates│    │                 │
│                 │    │ • Fitness Metrics│    │                 │
│                 │    │ • Breeding Pool  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Core Components

### 1. Data Ingestion
- **WebSocket**: trades, candles, BBO, L2Book (optional)
- **REST**: OI, funding, contexts, metadata
- **Time Lattice**: 1-minute base cadence with 15m/1h rollups

### 2. Feature Computation
- **Raw Features**: OHLC, volume, returns, CVD, OI, basis, spreads
- **Residual Manufacturing**: 8 residual factories (Cross-sectional, Kalman, Flow, Network, Carry, Breadth, Vol, Seasonality)
- **Regime Classification**: ATR percentiles, ADX bands, session phases, market regimes
- **Cross-Asset Context**: breadth, relative strength, leadership

### 3. Event Detection
- **6 Signal Classes**: spikes, shifts, quadrants, divergences, synchrony, rotation
- **Residual Triggers**: All detectors trigger on residuals from predictive models
- **Regime Gates**: ATR percentile, ADX bands, session phase, market regime controls
- **Severity Scoring**: 0-100 with debouncing, novelty decay, and regime boosts
- **Budget Controls**: per-class and global event limits

### 4. Self-Improvement
- **Curator**: monitors drift, proposes config changes
- **Replay System**: validates changes before applying
- **Versioning**: complete provenance for every event

## Quick Start Path

1. **Phase 0** (Weeks 1-2): Basic ingestion + 3 spike detectors
2. **Phase 1** (Weeks 3-5): Full feature set + all detector classes
3. **Phase 2** (Weeks 6-7): Rollups + retention
4. **Phase 3** (Weeks 8-10): Microstructure + positioning
5. **Phase 4** (Weeks 11-13): Curator + replays
6. **Phase 5** (Weeks 14-16): Hardening + extensibility

## Working Documents

- **[Feature Specifications](FEATURE_SPEC.md)** - All feature definitions and formulas
- **[Detector Catalog](DETECTOR_SPEC.md)** - Signal classes and triggers
- **[Data Model](DATA_MODEL.md)** - Database schemas and storage
- **[API Contracts](API_CONTRACTS.md)** - Event schemas and interfaces
- **[Operator Guide](OPERATOR_GUIDE.md)** - How to run and monitor
- **[Implementation Plan](IMPLEMENTATION_PLAN.md)** - Phases and milestones
- **[Configuration Management](CONFIG_MANAGEMENT.md)** - Packs and versioning

## Key Design Principles

1. **Residual Manufacturing**: Predict expected values, compute residuals, not simple z-scores
2. **Regime Awareness**: All signals respect market regime gates for quality
3. **Determinism**: Same inputs → bit-identical outputs
4. **Additive Evolution**: Only add, never remove or change
5. **Separation of Concerns**: Detection vs. decision making
6. **Operational Safety**: Graceful degradation under stress
7. **Complete Provenance**: Every event is fully traceable

## Success Criteria

- **Latency**: End-to-end p95 < 450ms
- **Reliability**: 99.9% availability
- **Quality**: 95%+ DQ ok-rate on majors
- **Determinism**: Bit-identical replay capability

---

*For complete technical specifications, see [alpha_detector_build_convo.md](../alpha_detector_build_convo.md)*
