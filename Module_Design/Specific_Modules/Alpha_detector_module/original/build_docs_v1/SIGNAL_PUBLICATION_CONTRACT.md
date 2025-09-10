# Signal Publication Contract

*Source: [alpha_detector_build_convo.md](../alpha_detector_build_convo.md) + Enhanced Signal Bus Design*

## Overview

A clean, versioned Signal Bus schema + API that emits "eligible" signals (with provenance, gates, and proofs) to whatever trading stack listens. This is the **detection → downstream** interface.

## Core Principle

**Signals only, no trading decisions.** We emit standardized signal intent and eligibility, not trade instructions.

## Signal Bus Schema v1.0.0

### Complete Signal Payload
```json
{
  "schema_ver": "sigbus-1.0.0",
  "asof_ts": "2025-01-15T14:30:00.000Z",
  "detector_id": "meanrev_hp_v5",
  "symbol": "BTC-USD",
  "horizon": "1h",
  "signal": 0.37,                 // standardized intent ∈ [-1,1]
  "det_sigma": 0.48,              // machine score
  "curated_sigma": 0.52,          // after curator nudges
  "eligibility": {
    "publish": true,
    "vetoes": [],                 // names if any
    "gates": {
      "kr_hbar": 0.62,
      "kr_coherence": 0.55,
      "det_kairos": 0.58,
      "det_entrain_r": 0.50,
      "det_uncert": 0.07
    }
  },
  "provenance": {
    "window": "2025-06-01..2025-09-01",
    "recipe_hash": "sha256:...",
    "data_fingerprint": "sha256:..."
  },
  "card_ref": "detector_cards/meanrev_hp_v5.md",
  "residual_analysis": {
    "residual_type": "kalman",
    "residual_value": 2.3,
    "residual_percentile": 0.95,
    "regime_context": "high_volatility"
  },
  "llm_context": {
    "primary_pattern": "mean_reversion",
    "level_context": "broke_support_at_49500",
    "divergence_context": "rsi_bearish_divergence",
    "volume_confirmation": "volume_spike_2.3x",
    "momentum_context": "rsi_oversold_25",
    "target_analysis": "support_zone_48500-49000",
    "context_summary": "Mean reversion signal: Broke rising support at 49500, 10% above support zone, volume spike 2.3x, RSI divergence bearish. Residual analysis shows 2.3σ Kalman residual in high volatility regime."
  }
}
```

## Field Specifications

### Core Signal Fields
- **`signal`**: Standardized intent ∈ [-1,1] where:
  - `+1.0` = Strong bullish signal
  - `0.0` = Neutral/no signal  
  - `-1.0` = Strong bearish signal
- **`det_sigma`**: Machine-computed selection score (0-1)
- **`curated_sigma`**: Final score after curator influence (0-1)
- **`horizon`**: Signal validity window (1h, 4h, 1d, etc.)

### Eligibility Fields
- **`publish`**: Boolean - whether signal is eligible for publication
- **`vetoes`**: Array of curator types that vetoed this signal
- **`gates`**: All gate values that determined eligibility

### Provenance Fields
- **`window`**: Training/evaluation window used
- **`recipe_hash`**: SHA256 of detector recipe/configuration
- **`data_fingerprint`**: SHA256 of input data used
- **`card_ref`**: Path to detector card documentation

### Context Fields
- **`residual_analysis`**: Residual manufacturing details
- **`llm_context`**: Structured context for LLM consumption

## Publication Gates (Detection-Only)

### Gate Logic
```python
def is_eligible_for_publication(signal_data):
    # Hard vetoes (block publication)
    if signal_data['eligibility']['vetoes']:
        return False
    
    # Gate thresholds
    gates = signal_data['eligibility']['gates']
    if (gates['det_kairos'] < tau_K or
        gates['det_entrain_r'] < tau_r or
        gates['det_uncert'] > tau_U):
        return False
    
    # Data quality
    if signal_data['dq_status'] != 'ok':
        return False
    
    # Curated score threshold
    if signal_data['curated_sigma'] < tau_publish:
        return False
    
    return True
```

### Gate Thresholds
```yaml
gates:
  tau_K: 0.55          # kairos threshold
  tau_r: 0.45          # entrainment threshold  
  tau_U: 0.15          # uncertainty threshold
  tau_publish: 0.35    # minimum curated_sigma
```

## Signal Bus API

### Publication Endpoint
```python
POST /signal-bus/publish
{
    "detector_id": "uuid",
    "symbol": "BTC-USD", 
    "signal_data": { /* full signal payload */ }
}

# Response
{
    "published": true,
    "signal_id": "uuid",
    "published_at": "2025-01-15T14:30:00.000Z"
}
```

### Subscription Endpoint
```python
GET /signal-bus/subscribe
{
    "symbols": ["BTC-USD", "ETH-USD"],
    "horizons": ["1h", "4h"],
    "min_curated_sigma": 0.4
}

# Response: Stream of signal events
```

### Signal History
```python
GET /signal-bus/history/{detector_id}
GET /signal-bus/history/{symbol}
GET /signal-bus/history?start=2025-01-01&end=2025-01-15
```

## Database Schema

### Signal Bus Table
```sql
CREATE TABLE signal_bus (
    id UUID PRIMARY KEY,
    schema_ver TEXT NOT NULL,
    asof_ts TIMESTAMP NOT NULL,
    detector_id UUID REFERENCES detector_registry(id),
    symbol TEXT NOT NULL,
    horizon TEXT NOT NULL,
    signal FLOAT8 NOT NULL,  -- [-1,1]
    det_sigma FLOAT8 NOT NULL,
    curated_sigma FLOAT8 NOT NULL,
    eligibility JSONB NOT NULL,
    provenance JSONB NOT NULL,
    card_ref TEXT,
    residual_analysis JSONB,
    llm_context JSONB,
    published_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_signal_bus_symbol_ts ON signal_bus(symbol, asof_ts);
CREATE INDEX idx_signal_bus_detector_ts ON signal_bus(detector_id, asof_ts);
CREATE INDEX idx_signal_bus_curated_sigma ON signal_bus(curated_sigma);
```

## Integration Points

### Downstream Systems
- **Trading System**: Subscribes to signals, makes trading decisions
- **Risk Management**: Monitors signal quality and frequency
- **Portfolio Management**: Aggregates signals across symbols
- **Research**: Analyzes signal performance and patterns

### Upstream Systems
- **Alpha Detector**: Generates raw signals
- **Curator Layer**: Applies governance and vetos
- **Kernel Resonance**: Computes selection scores

## Versioning Strategy

### Schema Versioning
- **Major**: Breaking changes to required fields
- **Minor**: New optional fields, enhanced context
- **Patch**: Bug fixes, documentation updates

### Backward Compatibility
- New fields are optional
- Old clients can ignore unknown fields
- Deprecation warnings for old schema versions

## Monitoring & Alerting

### Signal Quality Metrics
- **Publication rate**: Signals published per hour
- **Veto rate**: Percentage of signals vetoed by curators
- **Gate pass rate**: Percentage passing all gates
- **Latency**: Time from detection to publication

### System Health
- **Schema validation errors**: Malformed signals
- **Missing provenance**: Incomplete detector cards
- **Gate failures**: Threshold violations
- **Curator timeouts**: Delayed curator decisions

## Security & Compliance

### Access Control
- **Read access**: Downstream systems, research
- **Write access**: Alpha Detector, Curator Layer
- **Admin access**: System operators, auditors

### Audit Trail
- All signal publications are logged
- Curator actions are tracked
- Provenance is cryptographically verified
- Full history is retained for compliance

## Implementation Notes

### Performance
- Signal bus is optimized for high-frequency reads
- Batch processing for historical queries
- Caching for frequently accessed signals

### Reliability
- At-least-once delivery guarantees
- Dead letter queue for failed publications
- Circuit breakers for downstream failures

### Scalability
- Horizontal scaling via partitioning
- Message queuing for high throughput
- Compression for large context payloads
