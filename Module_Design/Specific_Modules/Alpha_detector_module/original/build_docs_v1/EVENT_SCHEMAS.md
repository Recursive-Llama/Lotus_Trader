# Event Schemas & Database Integration

*Source: [alpha_detector_build_convo.md §11](../alpha_detector_build_convo.md#event-contract--publication)*

## Database-Only Architecture

**No APIs - Everything through PostgreSQL database with triggers and notifications.**

### Database Tables for Evolutionary Management

**All detector management happens through database tables:**

```sql
-- Detector registry (lifecycle management)
INSERT INTO detector_registry (detector_id, lifecycle_state, created_at, parent_id, recipe)
VALUES ('momentum_trend_v3', 'experimental', NOW(), NULL, '{"inputs": ["z_ret_residual_m_1"], "hyperparams": {"threshold": 2.0}}');

-- Cohort snapshots (leaderboards)
INSERT INTO cohort_snapshot (snapshot_ts, universe, top_k, bottom_k, promotions, retirements)
VALUES (NOW(), 'crypto_v1', '{"momentum_trend_v3": {"S_i": 0.42}}', '{}', '[]', '[]');

-- Residual registry (residual management)
INSERT INTO residual_registry (residual_id, recipe, validation_r2, stationarity_test)
VALUES ('cross_sectional_v2', '{"nodes": [...], "edges": [...]}', 0.23, 0.05);
```

### Database-Only Integration

**All integration is through the database - no APIs needed.**

The system uses PostgreSQL triggers and `pg_notify` for real-time updates:

```sql
-- Trading system writes performance data directly to database
INSERT INTO signal_performance (detector_id, signal_id, pnl, success, timestamp)
VALUES ('momentum_trend_v3', 'sig_123', 0.023, true, NOW());

-- This triggers a database event that the Curator listens to
NOTIFY curator_updates, 'signal_performance_updated';
```

**Backtesting** runs internally and writes results to `backtest_results` table.

**Dead Branches** are automatically logged to `dead_branches_log` table when detectors fail.

**No external APIs** - everything is database-driven with PostgreSQL's built-in event system.

## Event Schema (v0.1)

*Source: [alpha_detector_build_convo.md §11.1](../alpha_detector_build_convo.md#event-schema-v01)*

### Core Event Structure

```json
{
  "v": "0.1",
  "event_id": "uuid-v7",
  "emitted_at": "2025-09-03T09:30:00Z",
  "exchange_ts": "2025-09-03T09:30:00Z",
  "ingest_ts": "2025-09-03T09:30:00.142Z",
  "symbol": "BTC",
  "asset_uid": 101,
  "tf": "1m",
  "class": "spike",
  "subtype": "vol_spike_m_1",
  "window_sec": 60,
  "severity": 74,
  "novelty": { "first_seen_at": "2025-09-03T09:29:00Z" },
  "debounce_key": "BTC:spike:1m",
  "coalesced": ["price_spike_up_m_1"],
  "local_state": { /* ... */ },
  "market_frame": { /* ... */ },
  "membership": { /* ... */ },
  "provenance": { /* ... */ },
  "attachments": { /* ... */ }
}
```

### Required Fields

- `v`, `event_id`, `emitted_at`, `exchange_ts`
- `symbol`, `asset_uid`, `tf`, `class`, `subtype`
- `severity`, `debounce_key`
- `local_state.dq.status`
- `market_frame.leader`
- `membership.*`
- `provenance.*`

### Optional Fields

- `coalesced` - Present when multiple subtypes coalesced
- `attachments` - Additional context
- `market_frame.rs_top`/`rs_bottom` - RS rankings

## Local State Payload

*Source: [alpha_detector_build_convo.md §9.8](../alpha_detector_build_convo.md#local-state-payload-what-to-include)*

### Basic Features Payload
```json
{
  "local_state": {
    "features": {
      "ret_s_30": 0.0042,
      "ret_m_1": 0.0031,
      "z_ret_abs_m_1": 2.9,
      "v_total_m_1": 18000000,
      "z_vol_m_1": 3.6,
      "oi_roc_m_5": 0.012,
      "z_oi_roc_m_5": 2.1,
      "spread_mean_m_1": 0.75,
      "z_spread_m_1": 0.9,
      "cvd_slope_m_5": 0.7,
      "basis_bp_m_5": 18.4,
      "z_basis_m_5": 1.3
    },
    "flags": {
      "is_price_spike_up_m_1": true,
      "is_oi_spike_up_m_5": true
    },
    "dq": {
      "status": "ok",
      "ingest_lag_ms": 142,
      "book_staleness_ms": 41,
      "oi_staleness_ms": 1800
    }
  }
}
```

### Comprehensive Signal Pack Payload (Phase 1 Addition)

**Pattern Detection Events with Full Context:**
```json
{
  "local_state": {
    "features": {
      // Basic price/volume features
      "ret_m_1": 0.0031,
      "z_vol_residual_m_1": 2.8,
      "vol_prediction_m_1": 12000000,
      "vol_prediction_std_m_1": 3000000,
      "v_total_m_1": 18000000,
      
      // Pattern detection features
      "diagonal_support_break": true,
      "diagonal_line_strength": 0.78,
      "pattern_strength_score": 0.82,
      "pattern_completion_pct": 0.85,
      
      // Support/resistance context
      "near_support": true,
      "level_strength": 0.82,
      "level_age": 15,
      "level_touches": 4,
      "diagonal_support_distance": 0.01,
      
      // Divergence context
      "price_rsi_divergence_strength": 0.75,
      "hidden_momentum_bull_strength": 0.68,
      "rsi_divergence_type": "bearish",
      
      // Momentum indicators (residual-based)
      "rsi_14": 45.2,
      "z_rsi_residual_14": 2.1,
      "rsi_prediction_14": 52.3,
      "macd_line": -120.5,
      "z_macd_residual": 1.8,
      "macd_prediction": -95.2,
      "adx_14": 28.7,
      "trend_strength": 0.65,
      
      // Regime classification
      "atr_percentile_252": 65.2,
      "volatility_regime": "medium",
      "trend_regime": "trending",
      "session_phase": "us",
      "market_regime": "normal",
      
      // Volume confirmation
      "pattern_volume_confirmation": true,
      "volume_ratio": 2.3,
      "volume_absorption_score": 0.68
    },
    "flags": {
      "is_diagonal_support_break": true,
      "is_volume_spike": true,
      "is_divergence_bearish": true,
      "pattern_time_confirmation": true
    },
    "signal_pack": {
      "primary_pattern": "diagonal_support_break",
      "pattern_strength": 0.82,
      "confirmation_factors": {
        "volume": true,
        "time": true,
        "strength": true,
        "divergence": true
      },
      "levels": {
        "support": [49500, 49200, 48800],
        "resistance": [50500, 50800, 51200],
        "nearest_support": 49500,
        "nearest_resistance": 50500,
        "distance_to_support": 0.01,
        "distance_to_resistance": 0.02
      },
      "divergences": [
        {
          "type": "price_rsi_bearish",
          "strength": 0.75,
          "timeframe": "5m",
          "context": "trending_up"
        },
        {
          "type": "hidden_momentum_bullish",
          "strength": 0.68,
          "timeframe": "15m",
          "context": "continuation"
        }
      ],
      "volume": {
        "spike": true,
        "ratio": 2.3,
        "confirmation": true,
        "absorption_score": 0.68
      },
      "pattern_analysis": {
        "completion_pct": 0.85,
        "breakout_strength": 0.78,
        "pattern_age": 15,
        "validation_pending": false
      },
      "llm_context": {
        "signal_type": "pattern_detection",
        "pattern_detected": "diagonal_support_break",
        "direction": "bearish",
        "price_level": 49500,
        "level_type": "support",
        "level_strength": 0.82,
        "distance_from_level": 0.01,
        "volume_confirmation": true,
        "volume_ratio": 2.3,
        "residual_analysis": {
          "volume_residual": 2.8,
          "volume_prediction": 12000000,
          "rsi_residual": 2.1,
          "rsi_prediction": 52.3,
          "macd_residual": 1.8,
          "macd_prediction": -95.2,
          "cross_sectional_residual": 1.9,
          "kalman_residual": 2.3
        },
        "regime_context": {
          "atr_percentile": 65.2,
          "volatility_regime": "medium",
          "trend_regime": "trending",
          "session_phase": "us",
          "market_regime": "normal",
          "regime_confidence": 0.85
        },
        "divergences": [
          {
            "type": "price_rsi",
            "direction": "bearish",
            "strength": 0.75,
            "timeframe": "5m",
            "residual_based": true
          }
        ],
        "points_of_interest": {
          "support_levels": [49500, 49200, 48800],
          "resistance_levels": [50500, 50800, 51200],
          "pattern_completion": 0.85,
          "breakout_strength": 0.78,
          "residual_significance": "high"
        },
        "confidence_score": 0.82,
        "residual_quality": "high",
        "model_performance": {
          "volume_model_r2": 0.73,
          "rsi_model_r2": 0.68,
          "cross_sectional_model_r2": 0.81
        }
      }
    },
    "dq": {
      "status": "ok",
      "ingest_lag_ms": 142,
      "book_staleness_ms": 41,
      "oi_staleness_ms": 1800
    }
  }
}
```

## Market Frame Context

*Source: [alpha_detector_build_convo.md §6](../alpha_detector_build_convo.md#cross-asset-context-builder)*

```json
{
  "market_frame": {
    "leader": "BTC",
    "dominance_share": 0.42,
    "shock_count_5s": 4,
    "rs_top": ["SOL","HYPE","APT","SEI","ENA"],
    "rs_bottom": ["XRP","ADA","ARB","DOGE","DOT"],
    "return_dispersion_m_5": 0.006,
    "vol_dispersion_m_5": 0.92,
    "time_to_next_funding_sec": 2143
  }
}
```

## Membership Context

```json
{
  "membership": {
    "is_in_universe": true,
    "is_hot": true,
    "universe_rev": 3127
  }
}
```

## Provenance Information

*Source: [alpha_detector_build_convo.md §13](../alpha_detector_build_convo.md#provenance--versioning)*

```json
{
  "provenance": {
    "producer": "alpha-detector@v1.0.0",
    "feature_pack": "v1.0",
    "detector_pack": "v0.1",
    "config_hash": "sha256:...",
    "git_commit": "...",
    "universe_policy_rev": 17,
    "source_lag_ms": 128,
    "clock_skew_ms": 73
  }
}
```

## Event Bus Interface

*Source: [alpha_detector_build_convo.md §11.3](../alpha_detector_build_convo.md#publication-channel--delivery)*

### Topic Structure
- **Live Events**: `alpha.events.v0`
- **Replay Events**: `alpha.events.replay.v0`
- **Dead Letter Queue**: `alpha.events.dlq`

### Partitioning
- **Key**: `asset_uid` (keeps per-asset order)
- **Semantics**: At-least-once delivery
- **Deduplication**: Consumer must dedupe on `event_id`

### Ordering & Dedupe
*Source: [alpha_detector_build_convo.md §11.4](../alpha_detector_build_convo.md#ordering--dedupe)*

- **Event ID**: UUIDv7 (time-ordered)
- **Per-partition**: Preserve publish order
- **Consumer**: Ignore older `emitted_at` for same `debounce_key`

## Read API (Optional)

*Source: [alpha_detector_build_convo.md §11.6](../alpha_detector_build_convo.md#contract-evolution)*

### Endpoints

```http
GET /snapshots/latest?asset=BTC&tf=1m
GET /market/frame?tf=1m&ts=2025-09-03T09:30:00Z
GET /events?symbol=BTC&since=2025-09-03T09:00:00Z&class=spike
GET /health
GET /status
```

### Response Examples

#### Feature Snapshot
```json
{
  "asset_uid": 101,
  "symbol": "BTC",
  "tf": "1m",
  "exchange_ts": "2025-09-03T09:30:00Z",
  "open": 64231.5,
  "high": 64320.0,
  "low": 64188.0,
  "close": 64295.0,
  "mid_close": 64294.6,
  "ret_m_1": 0.0010,
  "z_vol_m_1": 3.6,
  "dq_status": "ok",
  "is_in_universe": true,
  "is_hot": true
}
```

#### Market Snapshot
```json
{
  "tf": "1m",
  "exchange_ts": "2025-09-03T09:30:00Z",
  "leader": "BTC",
  "dominance_share": 0.42,
  "shock_count_5s": 4,
  "rs_top": ["SOL","HYPE","APT","SEI","ENA"],
  "return_dispersion_m_5": 0.0062,
  "dq_status": "ok"
}
```

## Data Types & Bounds

*Source: [alpha_detector_build_convo.md §11.2](../alpha_detector_build_convo.md#types--bounds)*

- **severity**: Integer 0–100
- **Floats**: Finite, non-NaN
- **Arrays**: Max 16 elements (e.g., `rs_top`)
- **Strings**: ASCII or UTF-8
- **Enums**: Only specified values for `subtype`/`class`/`tf`

## Contract Evolution

*Source: [alpha_detector_build_convo.md §11.6](../alpha_detector_build_convo.md#contract-evolution)*

### Backward Compatibility
- **Additive only**: New fields added, never removed
- **Unknown fields**: Consumers must ignore
- **Breaking changes**: New topic `alpha.events.v1`

### Versioning Strategy
- **Event schema**: `v0.1` → `v0.2` (additive) → `v1.0` (breaking)
- **Feature packs**: `v1.0` → `v1.1` (additive) → `v2.0` (breaking)
- **Detector packs**: `v0.1` → `v0.2` (additive) → `v1.0` (breaking)

## Comprehensive Signal Pack Strategy

### Signal Pack Philosophy
**Every event includes comprehensive context optimized for LLM consumption - SIGNALS ONLY, NO TRADING DECISIONS:**

1. **Signal Detection**: What pattern/divergence/spike was detected
2. **Direction**: Bullish/bearish (chart-based observation only)
3. **Level Context**: Support/resistance levels, distances, strength scores
4. **Divergence Context**: All detected divergences with strength scores
5. **Volume Confirmation**: Volume spikes, ratios, absorption scores
6. **Momentum Context**: RSI, MACD, ADX, trend strength
7. **Points of Interest**: Key levels, pattern completion, breakout strength
8. **LLM Context**: Structured, machine-readable context for analysis

### Signal Pack Benefits
- **LLM Optimized**: Structured, machine-readable context for AI analysis
- **Complete Context**: All pattern, level, divergence, and volume context in structured format
- **Signal Detection**: Clear pattern detection with confidence scores
- **Points of Interest**: Key levels, divergences, and market context for analysis
- **Chart Analysis**: Bullish/bearish direction based on chart patterns only
- **Analysis Ready**: All information needed for market analysis and signal evaluation

### Signal Pack Categories
- **Pattern Events**: Chart patterns with full level and volume context
- **Divergence Events**: Divergences with pattern and momentum context
- **Breakout Events**: Level breakouts with volume and divergence confirmation
- **Spike Events**: Volume/price spikes with market context
- **Shift Events**: Regime changes with breadth and leadership context

## Consumer Integration

### Required Consumer Logic
1. **Deduplication**: Use `event_id` (UUIDv7)
2. **Filtering**: Respect `dq.status` and severity thresholds
3. **Ordering**: Handle per-asset ordering, not global
4. **Unknown fields**: Ignore gracefully
5. **Error handling**: Dead letter queue for malformed events
6. **Signal Pack Processing**: Extract and process comprehensive context from `signal_pack` field

### Example Consumer (Python)
```python
import json
from typing import Dict, Any

class EventConsumer:
    def __init__(self, min_severity: int = 65):
        self.min_severity = min_severity
        self.seen_events = set()
    
    def process_event(self, event_json: str) -> None:
        event = json.loads(event_json)
        
        # Dedupe
        if event['event_id'] in self.seen_events:
            return
        self.seen_events.add(event['event_id'])
        
        # Filter
        if event['severity'] < self.min_severity:
            return
        
        if event['local_state']['dq']['status'] != 'ok':
            return
        
        # Process
        self.handle_signal(event)
    
    def handle_signal(self, event: Dict[str, Any]) -> None:
        class_type = event['class']
        subtype = event['subtype']
        severity = event['severity']
        
        # Extract signal pack if available
        signal_pack = event.get('local_state', {}).get('signal_pack', {})
        
        # Route by class/subtype
        if class_type == 'pattern':
            self.handle_pattern(event, signal_pack)
        elif class_type == 'divergence':
            self.handle_divergence(event, signal_pack)
        elif class_type == 'spike':
            self.handle_spike(event, signal_pack)
        elif class_type == 'shift':
            self.handle_shift(event, signal_pack)
        # ... etc
    
    def handle_pattern(self, event: Dict[str, Any], signal_pack: Dict[str, Any]) -> None:
        """Handle pattern events with LLM-optimized context"""
        # Extract LLM context (primary source)
        llm_context = signal_pack.get('llm_context', {})
        
        # Extract structured data for LLM processing
        signal_type = llm_context.get('signal_type', 'unknown')
        pattern_detected = llm_context.get('pattern_detected', 'unknown')
        direction = llm_context.get('direction', 'unknown')
        price_level = llm_context.get('price_level', 0)
        level_type = llm_context.get('level_type', 'unknown')
        level_strength = llm_context.get('level_strength', 0)
        volume_confirmation = llm_context.get('volume_confirmation', False)
        volume_ratio = llm_context.get('volume_ratio', 1.0)
        confidence_score = llm_context.get('confidence_score', 0)
        
        # Extract divergences for LLM analysis
        divergences = llm_context.get('divergences', [])
        
        # Extract points of interest for analysis
        points_of_interest = llm_context.get('points_of_interest', {})
        support_levels = points_of_interest.get('support_levels', [])
        resistance_levels = points_of_interest.get('resistance_levels', [])
        pattern_completion = points_of_interest.get('pattern_completion', 0)
        breakout_strength = points_of_interest.get('breakout_strength', 0)
        
        # Create LLM-ready context
        llm_ready_context = {
            "signal_type": signal_type,
            "pattern_detected": pattern_detected,
            "direction": direction,
            "price_level": price_level,
            "level_type": level_type,
            "level_strength": level_strength,
            "volume_confirmation": volume_confirmation,
            "volume_ratio": volume_ratio,
            "divergences": divergences,
            "points_of_interest": points_of_interest,
            "confidence_score": confidence_score
        }
        
        # Process for LLM consumption
        self.process_llm_signal(llm_ready_context)
    
    def process_llm_signal(self, context: Dict[str, Any]) -> None:
        """Process LLM-optimized signal context"""
        # This is where LLM would consume the structured data for analysis
        print(f"Signal Detected: {context['pattern_detected']} {context['direction']} at {context['price_level']}")
        print(f"Pattern: {context['pattern_detected']}, Confidence: {context['confidence_score']}")
        print(f"Volume: {context['volume_ratio']}x, Confirmation: {context['volume_confirmation']}")
        print(f"Support Levels: {context['points_of_interest'].get('support_levels', [])}")
        print(f"Resistance Levels: {context['points_of_interest'].get('resistance_levels', [])}")
        print(f"Pattern Completion: {context['points_of_interest'].get('pattern_completion', 0)}")
        print(f"Breakout Strength: {context['points_of_interest'].get('breakout_strength', 0)}")
```

## Trading Feedback Integration (Phase 6 Addition)

*Source: [alpha_detector_build_convo.md §14.7](../alpha_detector_build_convo.md#artifacts-tables)*

### Database-Only Feedback Approach

**Trading System → Database → Curator**

The trading system writes performance data directly to the database, which triggers Curator analysis via database notifications.

### Trading System Integration

#### Signal Performance Recording
```sql
-- Trading system writes signal outcomes directly to database
INSERT INTO signal_performance (
    signal_id, event_id, signal_type, direction, price_level, timestamp,
    action_taken, entry_price, exit_price, pnl, hold_time_minutes,
    max_drawdown, max_favorable, volatility_regime, trend_direction, volume_regime
) VALUES (
    'evt_abc123', '550e8400-e29b-41d4-a716-446655440000',
    'pattern.diagonal_support_break', 'bearish', 49500.0, '2025-01-03T14:30:00Z',
    'short_entry', 49450.0, 49200.0, 250.0, 45,
    -50.0, 300.0, 'medium', 'down', 'high'
);
```

#### Batch Performance Updates
```sql
-- Trading system can also update multiple signals at once
INSERT INTO signal_performance (signal_id, event_id, signal_type, direction, price_level, timestamp, action_taken, entry_price, exit_price, pnl, hold_time_minutes, volatility_regime, trend_direction, volume_regime)
VALUES 
    ('evt_abc123', '550e8400-e29b-41d4-a716-446655440000', 'pattern.diagonal_support_break', 'bearish', 49500.0, '2025-01-03T14:30:00Z', 'short_entry', 49450.0, 49200.0, 250.0, 45, 'medium', 'down', 'high'),
    ('evt_def456', '550e8400-e29b-41d4-a716-446655440001', 'div.price_rsi_bear_m_5', 'bearish', 49400.0, '2025-01-03T14:35:00Z', 'short_entry', 49350.0, 49100.0, 150.0, 30, 'medium', 'down', 'high');
```

### Database Triggers & Notifications

#### Performance Update Trigger
```sql
-- Database trigger fires when performance data is inserted
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
```

#### Detector Performance Aggregation Trigger
```sql
-- Aggregate performance metrics by detector and regime
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
```

### Curator Integration

#### Database Notification Listener
```python
# Curator listens for database notifications
async def listen_for_performance_updates():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.add_listener('curator_performance_update', handle_performance_update)
    
async def handle_performance_update(connection, pid, channel, payload):
    signal_id = payload
    # Analyze performance and generate proposals if needed
    await analyze_signal_performance(signal_id)

async def analyze_signal_performance(signal_id: str):
    """Analyze signal performance and generate proposals if needed"""
    # Get performance data
    performance = await get_signal_performance(signal_id)
    
    # Check if detector needs tuning
    if performance['accuracy'] < 0.55:
        await generate_performance_proposal(performance)
    
    # Check for regime-specific issues
    if performance['regime_performance_drop'] > 0.15:
        await generate_regime_proposal(performance)
```

### Performance Query Views

#### Detector Performance Summary
```sql
-- View for easy performance querying
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
```

#### Real-time Performance Monitoring
```sql
-- Query for real-time performance monitoring
SELECT 
    detector_id,
    market_regime,
    AVG(accuracy) as avg_accuracy,
    AVG(f1_score) as avg_f1_score,
    COUNT(*) as signal_count
FROM detector_performance_summary
WHERE time_window >= NOW() - INTERVAL '24 hours'
GROUP BY detector_id, market_regime
HAVING AVG(accuracy) < 0.55 OR AVG(f1_score) < 0.45;
```

---

*For complete event schemas and API specifications, see [alpha_detector_build_convo.md §11](../alpha_detector_build_convo.md#event-contract--publication)*
