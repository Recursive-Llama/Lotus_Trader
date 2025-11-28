# Enhanced Signal Publication Specification - Trading Intelligence System

*Source: [build_docs_v1/SIGNAL_PUBLICATION_CONTRACT.md](../build_docs_v1/SIGNAL_PUBLICATION_CONTRACT.md) + Trading Intelligence System Integration*

## Overview

A clean, versioned Signal Bus schema + API that emits "eligible" signals (with provenance, gates, and proofs) to whatever trading stack listens. This is the **detection → downstream** interface for the Trading Intelligence System.

## Core Principle

**Signals only, no trading decisions.** We emit standardized signal intent and eligibility, not trade instructions. The system generates **complete trading plans** with DSI validation and module intelligence, but publishes them as **signals** for downstream consumption.

## Signal Bus Schema v2.0.0

### Complete Signal Payload
```json
{
  "schema_ver": "sigbus-2.0.0",
  "asof_ts": "2025-01-15T14:30:00.000Z",
  "detector_id": "meanrev_hp_v5",
  "symbol": "BTC-USD",
  "horizon": "1h",
  "signal": 0.37,
  "det_sigma": 0.48,
  "curated_sigma": 0.52,
  "enhanced_sigma": 0.58,
  "eligibility": {
    "publish": true,
    "vetoes": [],
    "gates": {
      "kr_hbar": 0.62,
      "kr_coherence": 0.55,
      "det_kairos": 0.58,
      "det_entrain_r": 0.50,
      "det_uncert": 0.07,
      "dsi_evidence": 0.75,
      "module_intelligence": 0.68
    }
  },
  "provenance": {
    "window": "2025-06-01..2025-09-01",
    "recipe_hash": "sha256:...",
    "data_fingerprint": "sha256:...",
    "dsi_fingerprint": "sha256:...",
    "module_fingerprint": "sha256:..."
  },
  "card_ref": "detector_cards/meanrev_hp_v5.md",
  "residual_analysis": {
    "residual_type": "kalman",
    "residual_value": 2.3,
    "residual_percentile": 0.95,
    "regime_context": "high_volatility"
  },
  "dsi_evidence": {
    "mx_evidence": 0.75,
    "mx_confirm": true,
    "mx_confidence": 0.82,
    "expert_contributions": {
      "fsm": {"evidence": 0.8, "confidence": 0.9},
      "classifier": {"evidence": 0.7, "confidence": 0.8},
      "anomaly": {"evidence": 0.6, "confidence": 0.7},
      "divergence": {"evidence": 0.9, "confidence": 0.85}
    }
  },
  "module_intelligence": {
    "learning_rate": 0.01,
    "innovation_score": 0.75,
    "collaboration_score": 0.68,
    "specialization_index": 0.82
  },
  "trading_plan": {
    "signal_strength": 0.75,
    "direction": "long",
    "entry_conditions": ["price > 49500", "volume > 1.5x avg"],
    "entry_price": 49500,
    "position_size": 0.05,
    "stop_loss": 48500,
    "take_profit": 51000,
    "time_horizon": "1h",
    "risk_reward_ratio": 1.5,
    "confidence_score": 0.82,
    "execution_notes": "Enter on breakout above 49500 with volume confirmation"
  },
  "llm_context": {
    "primary_pattern": "mean_reversion",
    "secondary_patterns": ["volume_spike", "support_break"],
    "market_context": "high_volatility_regime",
    "confidence_factors": ["strong_volume", "clear_support", "dsi_confirmation"],
    "risk_factors": ["high_volatility", "regime_uncertainty"]
  }
}
```

## Event Schemas

### 1. Trading Plan Event
```json
{
  "event_type": "trading_plan",
  "event_version": "2.0.0",
  "timestamp": "2025-01-15T14:30:00.000Z",
  "event_id": "tp_20250115_143000_001",
  "trading_plan": {
    "plan_id": "tp_meanrev_hp_v5_001",
    "detector_id": "meanrev_hp_v5",
    "symbol": "BTC-USD",
    "timeframe": "1h",
    "signal_strength": 0.75,
    "direction": "long",
    "entry_conditions": ["price > 49500", "volume > 1.5x avg"],
    "entry_price": 49500,
    "position_size": 0.05,
    "stop_loss": 48500,
    "take_profit": 51000,
    "time_horizon": "1h",
    "risk_reward_ratio": 1.5,
    "confidence_score": 0.82,
    "dsi_validation": {
      "mx_evidence": 0.75,
      "mx_confirm": true,
      "mx_confidence": 0.82
    },
    "module_intelligence": {
      "learning_rate": 0.01,
      "innovation_score": 0.75,
      "collaboration_score": 0.68
    },
    "execution_notes": "Enter on breakout above 49500 with volume confirmation",
    "valid_until": "2025-01-15T15:30:00.000Z"
  },
  "provenance": {
    "detector_recipe": "sha256:...",
    "data_fingerprint": "sha256:...",
    "dsi_fingerprint": "sha256:...",
    "module_fingerprint": "sha256:..."
  }
}
```

### 2. DSI Evidence Event
```json
{
  "event_type": "dsi_evidence",
  "event_version": "2.0.0",
  "timestamp": "2025-01-15T14:30:00.000Z",
  "event_id": "dsi_20250115_143000_001",
  "dsi_evidence": {
    "evidence_id": "dsi_meanrev_hp_v5_001",
    "detector_id": "meanrev_hp_v5",
    "symbol": "BTC-USD",
    "mx_evidence": 0.75,
    "mx_confirm": true,
    "mx_confidence": 0.82,
    "expert_contributions": {
      "fsm": {
        "evidence_score": 0.8,
        "confidence": 0.9,
        "pattern_matches": 3,
        "expert_type": "grammar_fsm"
      },
      "classifier": {
        "evidence_score": 0.7,
        "confidence": 0.8,
        "prediction_class": "signal",
        "expert_type": "sequence_classifier"
      },
      "anomaly": {
        "evidence_score": 0.6,
        "confidence": 0.7,
        "is_anomaly": true,
        "expert_type": "anomaly_scorer"
      },
      "divergence": {
        "evidence_score": 0.9,
        "confidence": 0.85,
        "divergence_signals": {
          "price_rsi": 0.8,
          "price_macd": 0.7,
          "volume": 0.9
        },
        "expert_type": "divergence_verifier"
      }
    },
    "microtape_tokens": [
      {
        "token_id": "mt_001",
        "timestamp": "2025-01-15T14:29:45.000Z",
        "features": {
          "bid_ask_spread": 0.0001,
          "volume_imbalance": 0.2,
          "trade_intensity": 0.8,
          "vpin": 0.6
        },
        "feature_hash": "sha256:..."
      }
    ],
    "fusion_method": "bayesian",
    "fusion_weights": {
      "fsm": 0.25,
      "classifier": 0.25,
      "anomaly": 0.25,
      "divergence": 0.25
    }
  },
  "provenance": {
    "microtape_hash": "sha256:...",
    "expert_weights_hash": "sha256:...",
    "fusion_config_hash": "sha256:..."
  }
}
```

### 3. Module Intelligence Event
```json
{
  "event_type": "module_intelligence",
  "event_version": "2.0.0",
  "timestamp": "2025-01-15T14:30:00.000Z",
  "event_id": "mi_20250115_143000_001",
  "module_intelligence": {
    "module_id": "alpha_detector_001",
    "module_type": "alpha_detector",
    "learning_rate": 0.01,
    "innovation_score": 0.75,
    "collaboration_score": 0.68,
    "specialization_index": 0.82,
    "performance_metrics": {
      "signal_quality": 0.85,
      "trading_plan_quality": 0.78,
      "dsi_integration": 0.82,
      "module_communication": 0.75
    },
    "learning_progress": {
      "epochs_completed": 1000,
      "loss_reduction": 0.15,
      "accuracy_improvement": 0.08,
      "convergence_rate": 0.95
    },
    "innovation_metrics": {
      "novel_patterns": 5,
      "experimental_features": 3,
      "successful_innovations": 2,
      "innovation_rate": 0.4
    },
    "collaboration_metrics": {
      "messages_sent": 150,
      "messages_received": 200,
      "knowledge_shared": 0.75,
      "collaboration_effectiveness": 0.82
    }
  },
  "provenance": {
    "module_config_hash": "sha256:...",
    "learning_config_hash": "sha256:...",
    "collaboration_config_hash": "sha256:..."
  }
}
```

### 4. Module Replication Event
```json
{
  "event_type": "module_replication",
  "event_version": "2.0.0",
  "timestamp": "2025-01-15T14:30:00.000Z",
  "event_id": "mr_20250115_143000_001",
  "module_replication": {
    "replication_id": "mr_alpha_detector_001",
    "parent_module_id": "alpha_detector_001",
    "replication_trigger": "performance_threshold",
    "replication_reason": "High performance and innovation scores",
    "replication_config": {
      "inheritance_rate": 0.8,
      "mutation_rate": 0.1,
      "recombination_rate": 0.1,
      "max_parents": 3
    },
    "new_module_config": {
      "module_id": "alpha_detector_002",
      "module_type": "alpha_detector",
      "specialization": "high_volatility_regimes",
      "learning_rate": 0.012,
      "innovation_weight": 0.3
    },
    "validation_status": "pending",
    "expected_activation": "2025-01-15T15:00:00.000Z"
  },
  "provenance": {
    "parent_config_hash": "sha256:...",
    "replication_config_hash": "sha256:...",
    "validation_config_hash": "sha256:..."
  }
}
```

## Signal Bus API

### 1. Signal Publication Endpoint
```http
POST /api/v2/signals/publish
Content-Type: application/json

{
  "signal": {
    "schema_ver": "sigbus-2.0.0",
    "detector_id": "meanrev_hp_v5",
    "symbol": "BTC-USD",
    "signal": 0.37,
    "enhanced_sigma": 0.58,
    "trading_plan": { ... },
    "dsi_evidence": { ... },
    "module_intelligence": { ... }
  }
}
```

**Response:**
```json
{
  "status": "success",
  "signal_id": "sig_20250115_143000_001",
  "publication_time": "2025-01-15T14:30:00.000Z",
  "eligibility": {
    "publish": true,
    "vetoes": [],
    "gates": { ... }
  }
}
```

### 2. Signal Query Endpoint
```http
GET /api/v2/signals?symbol=BTC-USD&timeframe=1h&limit=100
```

**Response:**
```json
{
  "status": "success",
  "signals": [
    {
      "signal_id": "sig_20250115_143000_001",
      "detector_id": "meanrev_hp_v5",
      "symbol": "BTC-USD",
      "signal": 0.37,
      "enhanced_sigma": 0.58,
      "timestamp": "2025-01-15T14:30:00.000Z",
      "trading_plan": { ... },
      "dsi_evidence": { ... }
    }
  ],
  "pagination": {
    "total": 1000,
    "page": 1,
    "limit": 100,
    "has_more": true
  }
}
```

### 3. DSI Evidence Query Endpoint
```http
GET /api/v2/dsi/evidence?detector_id=meanrev_hp_v5&symbol=BTC-USD&limit=50
```

**Response:**
```json
{
  "status": "success",
  "evidence": [
    {
      "evidence_id": "dsi_meanrev_hp_v5_001",
      "detector_id": "meanrev_hp_v5",
      "symbol": "BTC-USD",
      "mx_evidence": 0.75,
      "mx_confirm": true,
      "mx_confidence": 0.82,
      "timestamp": "2025-01-15T14:30:00.000Z",
      "expert_contributions": { ... }
    }
  ]
}
```

### 4. Module Intelligence Query Endpoint
```http
GET /api/v2/modules/intelligence?module_type=alpha_detector&limit=20
```

**Response:**
```json
{
  "status": "success",
  "modules": [
    {
      "module_id": "alpha_detector_001",
      "module_type": "alpha_detector",
      "learning_rate": 0.01,
      "innovation_score": 0.75,
      "collaboration_score": 0.68,
      "performance_metrics": { ... },
      "last_updated": "2025-01-15T14:30:00.000Z"
    }
  ]
}
```

## Provenance Tracking

### 1. Recipe Hashing
```python
def generate_recipe_hash(detector_config, feature_config, dsi_config, module_config):
    """Generate SHA256 hash of detector recipe"""
    recipe_data = {
        'detector_config': detector_config,
        'feature_config': feature_config,
        'dsi_config': dsi_config,
        'module_config': module_config,
        'timestamp': datetime.now().isoformat()
    }
    
    recipe_string = json.dumps(recipe_data, sort_keys=True)
    return hashlib.sha256(recipe_string.encode()).hexdigest()
```

### 2. Data Fingerprinting
```python
def generate_data_fingerprint(features, dsi_evidence, module_intelligence):
    """Generate SHA256 hash of data used"""
    data_fingerprint = {
        'features_hash': hashlib.sha256(features.tobytes()).hexdigest(),
        'dsi_evidence_hash': hashlib.sha256(json.dumps(dsi_evidence, sort_keys=True).encode()).hexdigest(),
        'module_intelligence_hash': hashlib.sha256(json.dumps(module_intelligence, sort_keys=True).encode()).hexdigest(),
        'timestamp': datetime.now().isoformat()
    }
    
    fingerprint_string = json.dumps(data_fingerprint, sort_keys=True)
    return hashlib.sha256(fingerprint_string.encode()).hexdigest()
```

### 3. DSI Fingerprinting
```python
def generate_dsi_fingerprint(microtape_tokens, expert_outputs, fusion_config):
    """Generate SHA256 hash of DSI evidence"""
    dsi_data = {
        'microtape_tokens': [token['feature_hash'] for token in microtape_tokens],
        'expert_outputs': expert_outputs,
        'fusion_config': fusion_config,
        'timestamp': datetime.now().isoformat()
    }
    
    dsi_string = json.dumps(dsi_data, sort_keys=True)
    return hashlib.sha256(dsi_string.encode()).hexdigest()
```

### 4. Module Fingerprinting
```python
def generate_module_fingerprint(module_config, learning_state, collaboration_state):
    """Generate SHA256 hash of module state"""
    module_data = {
        'module_config': module_config,
        'learning_state': learning_state,
        'collaboration_state': collaboration_state,
        'timestamp': datetime.now().isoformat()
    }
    
    module_string = json.dumps(module_data, sort_keys=True)
    return hashlib.sha256(module_string.encode()).hexdigest()
```

## Signal Validation

### 1. Schema Validation
```python
def validate_signal_schema(signal):
    """Validate signal against schema"""
    required_fields = [
        'schema_ver', 'asof_ts', 'detector_id', 'symbol',
        'signal', 'enhanced_sigma', 'eligibility', 'provenance'
    ]
    
    for field in required_fields:
        if field not in signal:
            return False, f"Missing required field: {field}"
    
    # Validate schema version
    if signal['schema_ver'] != 'sigbus-2.0.0':
        return False, f"Unsupported schema version: {signal['schema_ver']}"
    
    # Validate signal range
    if not -1 <= signal['signal'] <= 1:
        return False, f"Signal out of range: {signal['signal']}"
    
    # Validate enhanced sigma range
    if not 0 <= signal['enhanced_sigma'] <= 1:
        return False, f"Enhanced sigma out of range: {signal['enhanced_sigma']}"
    
    return True, "Schema validation passed"
```

### 2. Provenance Validation
```python
def validate_provenance(signal):
    """Validate signal provenance"""
    provenance = signal.get('provenance', {})
    
    # Check required provenance fields
    required_provenance = [
        'recipe_hash', 'data_fingerprint', 'dsi_fingerprint', 'module_fingerprint'
    ]
    
    for field in required_provenance:
        if field not in provenance:
            return False, f"Missing provenance field: {field}"
    
    # Validate hash formats
    for field in required_provenance:
        if not re.match(r'^sha256:[a-f0-9]{64}$', provenance[field]):
            return False, f"Invalid hash format for {field}: {provenance[field]}"
    
    return True, "Provenance validation passed"
```

### 3. DSI Evidence Validation
```python
def validate_dsi_evidence(signal):
    """Validate DSI evidence"""
    dsi_evidence = signal.get('dsi_evidence', {})
    
    if not dsi_evidence:
        return True, "No DSI evidence to validate"
    
    # Check required DSI fields
    required_dsi = ['mx_evidence', 'mx_confirm', 'mx_confidence', 'expert_contributions']
    
    for field in required_dsi:
        if field not in dsi_evidence:
            return False, f"Missing DSI field: {field}"
    
    # Validate evidence ranges
    if not 0 <= dsi_evidence['mx_evidence'] <= 1:
        return False, f"mx_evidence out of range: {dsi_evidence['mx_evidence']}"
    
    if not 0 <= dsi_evidence['mx_confidence'] <= 1:
        return False, f"mx_confidence out of range: {dsi_evidence['mx_confidence']}"
    
    return True, "DSI evidence validation passed"
```

## Performance Requirements

### Latency Targets
- **Signal Publication**: < 50ms
- **Signal Query**: < 100ms
- **DSI Evidence Query**: < 150ms
- **Module Intelligence Query**: < 200ms

### Throughput Targets
- **Signal Publication**: 1000+ signals per second
- **Signal Query**: 500+ queries per second
- **DSI Evidence Query**: 200+ queries per second
- **Module Intelligence Query**: 100+ queries per second

### Reliability Targets
- **Signal Delivery**: > 99.9% success rate
- **Data Integrity**: > 99.99% accuracy
- **Provenance Tracking**: 100% completeness
- **Schema Validation**: 100% compliance

## Configuration

```yaml
signal_publication:
  # Schema Configuration
  schema:
    version: "2.0.0"
    validation: true
    strict_mode: true
  
  # API Configuration
  api:
    base_url: "https://api.trading-intelligence.com/v2"
    timeout: 30
    retry_attempts: 3
    rate_limit: 1000  # requests per minute
  
  # Signal Bus Configuration
  signal_bus:
    primary: "redis_streams"
    backup: "postgresql"
    monitoring: true
    
    # Redis Configuration
    redis:
      host: "localhost"
      port: 6379
      db: 0
      password: null
      max_connections: 100
    
    # PostgreSQL Configuration
    postgresql:
      host: "localhost"
      port: 5432
      database: "trading_intelligence"
      username: "trading_user"
      password: "secure_password"
  
  # Provenance Configuration
  provenance:
    recipe_hashing: true
    data_fingerprinting: true
    dsi_fingerprinting: true
    module_fingerprinting: true
    audit_trail: true
  
  # Performance Configuration
  performance:
    max_signal_latency_ms: 50
    max_query_latency_ms: 200
    batch_processing: true
    parallel_processing: true
    caching: true
```

---

*This enhanced signal publication specification provides comprehensive signal bus capabilities for the Trading Intelligence System with DSI validation and module intelligence.*
