# Uptrend Engine Build Plan

Note: Canonical S0–S5 definitions, thresholds, constants, unified payload schema, and event hooks are defined in `SM_UPTREND.MD`. This plan references that spec and avoids duplicating parameters.

## 🎯 **Executive Summary**

**Purpose**: Build a sophisticated uptrend detection and management system that integrates with the existing PM architecture.

**Core Philosophy**: "Detect high-probability uptrend opportunities, size them appropriately based on market context, and manage them with precision."

**Integration Strategy**: Uptrend Engine provides opportunity detection, PM Core handles market context and risk management through A/E levers.

## 📊 **System Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Geometry      │    │   TA Tracker    │    │ Uptrend Engine  │    │   PM Core       │
│   Builder       │───▶│   (Enhanced)    │───▶│   (New)         │───▶│   (Enhanced)    │
│   (Daily)       │    │   (5min)        │    │   (5min)        │    │   (1h)          │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │                        │
         ▼                        ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ S/R Levels      │    │ RSI/EMA/ATR     │    │ S0-S5 States    │    │ A/E Levers      │
│ Diagonals       │    │ ADX/VO_z        │    │ Setup A/B/C     │    │ Position Sizing │
│ Fib Levels      │    │ Compression     │    │ R/R Ratios      │    │ Risk Management │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 **Component Specifications**

### **1. Enhanced TA Tracker** (5-minute job)

**New Features to Add:**
- **ADX(14) on 1h**: Trend strength and phase discrimination
- **Compression Detection**: ATR slope tracking for energy accumulation
- **VO_z**: Implement 1h log-volume EWMA z with winsorization and caps per `SM_UPTREND.MD`; keep 15m VO_z windows for setup confirmation
- **AVWAP(flip)**: Anchor at S1 breakout close per `SM_UPTREND.MD`; include fakeout reset (24 bars)
- **ZigZag/Geometry**: ATR-adaptive λ=1.2×ATR, backstep=3, min leg=4 bars; expose pivots/legs and channel distances (see SM for details)
---> Should we remove OBV?

**Implementation:**
```python
# Add to ta_tracker.py
def _adx(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
    # ADX calculation implementation
    
def _compression_pulse(atr_series: List[float], window: int = 200) -> Dict[str, Any]:
    # ATR slope tracking for compression/expansion detection
    
def _vo_z_window(volumes: List[float], window: int = 20, threshold: float = 2.0) -> bool:
    # Detect clustered volume spikes
```

**Output Enhancement:**
```json
{
  "ta": {
    "rsi": {"value": 54.2, "divergence": "bull"},
    "ema": {"ema_20_1h": 0.0000062, "ema_50_1h": 0.0000065, "ema_200_1h": 0.0000060},
    "adx": {"value": 28.5, "trend_strength": "emerging"},
    "atr": {"atr_1h": 0.0000008, "compression_slope": -0.02, "compression_state": "coiling"},
    "volume": {"vo_z_15m": 0.9, "vo_z_window": true, "window_bars": 20},
    "avwap": {"flip_anchor": "2025-01-22T10:00:00Z", "current_price": 0.0000065}
  }
}
```

### **2. Uptrend Engine** (New 5-minute job)

**Purpose**: Detect and rank uptrend opportunities using S0–S5 state machine (as defined in `SM_UPTREND.MD`).

**State Machine Implementation:**
```python
class UptrendEngine:
    def __init__(self):
        self.states = {
            'S0': 'downtrend',
            'S1': 'flip_probe', 
            'S2': 'flip_confirmed',
            'S3': 'continuation',
            'S4': 'euphoria_overextension',
            'S5': 'reentry_cooling'
        }
    
    def evaluate_position(self, position: Dict[str, Any]) -> Dict[str, Any]:
        # S0-S5 state evaluation
        # Setup A/B/C detection
        # R/R calculation
        # Confidence scoring
```

**Setup Detection:**
- **Setup A**: First pullback after flip (EMA20/AVWAP retest)
- **Setup B**: Breakout-retest of levels (VO_z window confirmation)  
- **Setup C**: Channel support buy (diagonal lower bound)

**Output Format:**
```json
{
  "uptrend_engine": {
    "state": "S2",
    "state_name": "flip_confirmed",
    "setups": [
      {
        "type": "A",
        "confidence": 0.85,
        "risk_reward": 2.8,
        "entry_price": 0.0000062,
        "stop_price": 0.0000058,
        "target_price": 0.0000070
      }
    ],
    "composite_score": 78.5,
    "updated_at": "2025-01-22T15:05:00Z"
  }
}
```
Note: All state emissions follow the unified payload schema and event hooks defined in `SM_UPTREND.MD` (emit `s1_breakout`, `s2_support_touch`, `s3_sr_reclaim`, `s4_euphoria_on/off`, `s5_reentry_on/off`, `emergency_exit_on/off`).

### **3. Enhanced PM Core** (1-hour job)

**A/E Lever Integration:**
- **A (Add Appetite)**: Market phases + intent channels + cut pressure (NO TA signals)
- **E (Exit Assertiveness)**: Market phases + intent channels + cut pressure (NO TA signals)
- **Continuous 0-1 scores** instead of 3 discrete levels (patient/normal/aggressive)

**Uptrend Engine Integration:**
```python
def compute_levers(phase_macro: str, phase_meso: str, cut_pressure: float, 
                  features: Dict[str, Any]) -> Dict[str, Any]:
    # Existing A/E computation (no TA signals)
    a_pol, e_pol = _map_meso_policy(phase_meso)
    a_mac, e_mac = _apply_macro(a_pol, e_pol, phase_macro)
    a_cp, e_cp = _apply_cut_pressure(a_mac, e_mac, cut_pressure)
    
    # NEW: Apply Uptrend Engine opportunity quality
    uptrend_engine = features.get("uptrend_engine", {})
    if uptrend_engine:
        opportunity_quality = uptrend_engine.get("composite_score", 0) / 100.0
        a_final = a_cp * (0.5 + 0.5 * opportunity_quality)  # Modulate by opportunity quality
        e_final = e_cp  # E remains market-context driven
    
    return {"A_value": a_final, "E_value": e_final, "mode_display": mode}
```

**Position Sizing Integration:**
```python
def plan_actions(position: Dict[str, Any], a_final: float, e_final: float, 
                phase_meso: str) -> List[Dict[str, Any]]:
    uptrend_engine = position.get("features", {}).get("uptrend_engine", {})
    
    if uptrend_engine.get("setups"):
        # Use Uptrend Engine setups instead of basic geometry flags
        for setup in uptrend_engine["setups"]:
            if setup["confidence"] >= 0.7:  # High confidence threshold
                size_frac = a_final * setup["confidence"] * 0.1  # A/E modulated sizing
                return [{
                    "decision_type": "add",
                    "size_frac": size_frac,
                    "reasons": {
                        "uptrend_engine": True,
                        "setup_type": setup["type"],
                        "confidence": setup["confidence"],
                        "risk_reward": setup["risk_reward"]
                    }
                }]
```

## 🔄 **Data Flow Integration**

### **Phase 1: Enhanced TA Tracker**
1. **Extend `ta_tracker.py`** with ADX, compression detection, VO_z windows
2. **Add AVWAP(flip) computation** and storage
3. **Test TA enhancements** independently

### **Phase 2: Uptrend Engine**
1. **Create `uptrend_engine.py`** with S0-S5 state machine
2. **Implement Setup A/B/C detection** logic (use SM S3 continuation_quality refinements: pullback quality, retest absorption, channel awareness)
3. **Build composite scoring system** for opportunity ranking
4. **Test state machine** on historical data

### **Phase 3: PM Core Integration**
1. **Enhance `levers.py`** to use Uptrend Engine outputs**
2. **Modify `actions.py`** to use Setup A/B/C and SM flags/scores; thresholds come from PM aggressiveness curves (τ_integrity/τ_strength/τ_continuation) vs SM scores
3. **Convert A/E to continuous 0-1 scores** instead of discrete levels
4. **Test integrated system** end-to-end

### **Phase 4: Optimization**
1. **Backtest parameters** on historical data
2. **Fine-tune thresholds** based on performance
3. **Optimize timing** and resource usage
4. **Deploy to production** with monitoring

## 📋 **Implementation Details**

### **Database Schema Extensions**
```sql
-- Add uptrend_engine to features
ALTER TABLE lowcap_positions 
ADD COLUMN features JSONB DEFAULT '{}';

-- Index for efficient querying
CREATE INDEX idx_features_uptrend_engine 
ON lowcap_positions USING GIN ((features->'uptrend_engine'));
```

### **Configuration Updates**
```json
{
  "uptrend_engine": {
    "adx_thresholds": {
      "compression": 20,
      "emerging": 25,
      "mature": 40
    },
    "compression_window": 200,
    "vo_z_window_size": 20,
    "vo_z_threshold": 2.0,
    "setup_confidence_min": 0.7,
    "risk_reward_min": 2.0
  }
}
```

### **Job Scheduling**
```python
# Enhanced scheduling in run_social_trading.py
schedule_5min(0, tracker_main)           # Existing tracker
schedule_5min(2, ta_tracker_main)        # Enhanced TA tracker  
schedule_5min(4, uptrend_engine_main)   # NEW: Uptrend Engine
schedule_hourly(6, pm_core_main)        # Enhanced PM Core
schedule_daily(10, geometry_main)       # Existing geometry
```

## 🎯 **Success Metrics**

### **Technical Metrics**
- **State Machine Accuracy**: >80% correct S0-S5 transitions
- **Setup Detection**: >70% of detected setups result in profitable moves
- **R/R Performance**: Average R/R >2.0 on winning trades
- **System Latency**: <30 seconds from signal to decision

### **Business Metrics**
- **Win Rate**: >60% on Setup A entries
- **Average R**: 2.5-3.0 on winning trades  
- **Maximum Drawdown**: <15% of account
- **Time in Trade**: 3-14 days average holding period

## 🚀 **Deployment Strategy**

### **Phase 1: Foundation (Week 1-2)**
- Implement ADX and compression detection in TA tracker
- Test TA enhancements independently
- Validate data quality and performance

### **Phase 2: Core Engine (Week 3-4)**
- Build Uptrend Engine with S0-S5 state machine
- Implement Setup A/B/C detection
- Test on historical data with backtesting

### **Phase 3: Integration (Week 5-6)**
- Integrate Uptrend Engine with PM Core
- Convert A/E to continuous scoring
- Test end-to-end system

### **Phase 4: Production (Week 7-8)**
- Deploy with monitoring and alerts
- Fine-tune parameters based on live performance
- Optimize for production scale

## 🔍 **Monitoring & Debugging**

### **Key Logs**
- **TA Tracker**: "ADX computed", "Compression detected", "VO_z window triggered"
- **Uptrend Engine**: "State transition S0→S1", "Setup A detected", "Composite score: 78.5"
- **PM Core**: "A/E scores: A=0.73, E=0.45", "Position sized: 0.15"

### **Data Verification**
- Check `features.ta` for ADX and compression data
- Verify `features.uptrend_engine` for state and setups
- Monitor A/E continuous scores vs discrete levels
- Track Setup A/B/C detection accuracy

### **Performance Monitoring**
- State machine transition accuracy
- Setup detection precision/recall
- R/R ratio performance
- System latency and resource usage

---

*This build plan ensures a robust, integrated uptrend detection system while preserving the sophisticated A/E and phase systems already developed.*
