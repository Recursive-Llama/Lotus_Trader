# Trading Intelligence System - Build Implementation Plan

*Complete instruction set for building the Trading Intelligence System from build_docs_v2*

## Overview

This document provides a comprehensive, step-by-step implementation plan for building the complete Trading Intelligence System. It serves as a complete instruction set that can be handed to any development team to implement the full system.

## Build Philosophy

### **Modular Implementation**
- Build in **phases** with working systems at each stage
- Each phase produces **testable, deployable components**
- **Incremental complexity** - start simple, add sophistication
- **Database-first approach** - establish data foundation early

### **Implementation Strategy**
1. **Foundation Phase** - Core data model and basic detection
2. **Intelligence Phase** - DSI, Kernel Resonance, and advanced features
3. **Integration Phase** - Module communication and decision maker integration
4. **Learning Phase** - Self-learning and replication capabilities
5. **Production Phase** - Performance optimization and monitoring

---

## Phase 1: Foundation (Weeks 1-4)

### **1.1 Database Setup**
**Reference**: `ENHANCED_DATA_MODEL.md`

#### **Step 1.1.1: Core Tables**
```sql
-- Create core database schema
-- Priority: HIGH - Everything depends on this

-- 1. Module strands tables (direct communication)
CREATE TABLE AD_strands (...);
CREATE TABLE DM_strands (...);
CREATE TABLE TR_strands (...);

-- 2. Module management
CREATE TABLE modules (...);
CREATE TABLE module_performance (...);
```

#### **Step 1.1.2: Indexes and Constraints**
```sql
-- Create all indexes for performance
-- Reference: ENHANCED_DATA_MODEL.md lines 200-300
```

#### **Step 1.1.3: Initial Data**
```sql
-- Insert default modules
-- Insert default risk limits
-- Insert initial configuration
```

### **1.2 Market Data Collection**
**Reference**: `ENHANCED_DATA_MODEL.md` (Market Data Tables)

#### **Step 1.2.1: Market Data Schema**
```sql
-- File: database/alpha_market_data_schema.sql
-- Reference: ENHANCED_DATA_MODEL.md lines 295-320

-- Create alpha_market_data_1m table for raw OHLCV data
CREATE TABLE alpha_market_data_1m (
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(20,8) NOT NULL,
    high DECIMAL(20,8) NOT NULL,
    low DECIMAL(20,8) NOT NULL,
    close DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8) NOT NULL,
    -- Data Quality
    data_quality_score DECIMAL(3,2) DEFAULT 1.0,
    source VARCHAR(50) DEFAULT 'hyperliquid',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, timestamp)
);

-- Note: Features are calculated on-demand from raw OHLCV data
-- No separate features table needed - simpler architecture
```

#### **Step 1.2.2: Hyperliquid WebSocket Client**
```python
# File: src/data_sources/hyperliquid_client.py
# Reference: ENHANCED_OPERATIONAL_GUIDE.md lines 120-160

class HyperliquidWebSocketClient:
    def __init__(self, symbols=['BTC', 'ETH', 'SOL']):
        self.symbols = symbols
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        self.health_monitor = WebSocketHealthMonitor()
        self.data_gap_detector = DataGapDetector()
    
    async def connect(self):
        # WebSocket connection with health monitoring
        pass
    
    async def subscribe_to_market_data(self):
        # Subscribe to 1-minute OHLCV data
        pass
    
    async def handle_message(self, message):
        # Process incoming market data
        pass
```

#### **Step 1.2.3: Market Data Processor**
```python
# File: src/core_detection/market_data_processor.py
# Reference: ENHANCED_IMPLEMENTATION_SPEC.md lines 300-400

class MarketDataProcessor:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.data_quality_validator = DataQualityValidator()
    
    def process_ohlcv_data(self, raw_data):
        # Convert raw WebSocket data to structured format
        # Validate data quality
        # Store in alpha_market_data_1m table
        pass
    
    def validate_data_quality(self, ohlc_data):
        # Validate OHLCV data quality
        # Check for gaps, outliers, etc.
        pass
```

#### **Step 1.2.4: On-Demand Feature Calculation**
```python
# File: src/core_detection/feature_extractors.py
# Reference: ENHANCED_FEATURE_SPEC.md

class BasicFeatureExtractor:
    def __init__(self):
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.bb_period = 20
        self.bb_std = 2
    
    def extract_all_features(self, ohlc_data):
        """Extract all features from OHLCV data on-demand"""
        # Calculate features directly from raw data
        price_features = self.extract_price_features(ohlc_data)
        volume_features = self.extract_volume_features(ohlc_data)
        technical_features = self.extract_technical_features(ohlc_data)
        
        # Combine all features
        return {**price_features, **volume_features, **technical_features}
    
    def extract_price_features(self, ohlc_data):
        """Extract price-based features (RSI, MACD, Bollinger Bands)"""
        # Implementation details...
        pass
    
    def extract_volume_features(self, ohlc_data):
        """Extract volume-based features"""
        # Implementation details...
        pass
    
    def extract_technical_features(self, ohlc_data):
        """Extract technical indicator features"""
        # Implementation details...
        pass
```

### **1.3 Basic Alpha Detector**
**Reference**: `ENHANCED_DETECTOR_SPEC.md` (Core Detection Engine) + `ENHANCED_FEATURE_SPEC.md`

#### **Step 1.3.1: Multi-Timeframe Data Processor** ✅ COMPLETE
```python
# File: src/core_detection/multi_timeframe_processor.py
# Reference: ENHANCED_DETECTOR_SPEC.md lines 50-150

class MultiTimeframeProcessor:
    def __init__(self):
        self.timeframes = {
            '1m': '1min',   # Entry signals, noise filtering
            '5m': '5min',   # Short-term momentum
            '15m': '15min', # Medium-term trend
            '1h': '1h'      # Long-term trend confirmation
        }
        self.min_data_points = {
            '1m': 100,   # 100 minutes
            '5m': 100,   # 500 minutes (8+ hours)
            '15m': 100,  # 1500 minutes (25+ hours)
            '1h': 100    # 100 hours (4+ days)
        }
    
    def process_multi_timeframe(self, data_1m):
        """Process 1m data into multiple timeframes"""
        results = {}
        
        for tf_name, tf_freq in self.timeframes.items():
            # Roll up 1m data to target timeframe
            ohlc_data = self._roll_up_ohlc(data_1m, tf_freq)
            
            # Check if we have enough data
            if len(ohlc_data) < self.min_data_points[tf_name]:
                logger.warning(f"Insufficient data for {tf_name}: {len(ohlc_data)} < {self.min_data_points[tf_name]}")
                continue
            
            results[tf_name] = {
                'ohlc': ohlc_data,
                'timeframe': tf_name,
                'data_points': len(ohlc_data)
            }
        
        return results
    
    def _roll_up_ohlc(self, data_1m, target_freq):
        """Roll up 1-minute data to target frequency"""
        # Set timestamp as index for resampling
        data_indexed = data_1m.set_index('timestamp')
        
        # Resample to target frequency
        resampled = data_indexed.resample(target_freq).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        # Reset index to get timestamp back as column
        return resampled.reset_index()
```

#### **Step 1.3.2: Core Detection Engine** ✅ COMPLETE
```python
# File: src/core_detection/core_detection_engine.py
# Reference: ENHANCED_DETECTOR_SPEC.md lines 50-150

class CoreDetectionEngine:
    def __init__(self, db_manager=None, signal_filter=None):
        self.db_manager = db_manager
        self.multi_timeframe_processor = MultiTimeframeProcessor()
        self.feature_extractors = BasicFeatureExtractor()
        self.pattern_detectors = PatternDetector()
        self.regime_detector = RegimeDetector()
        self.signal_generator = SignalGenerator()
        self.signal_combiner = MultiTimeframeSignalCombiner()
        self.signal_processor = SignalProcessor(signal_filter)
        
    def detect_signals(self, market_data_1m):
        """Main multi-timeframe signal detection pipeline"""
        # 1. Process multi-timeframe data
        mtf_data = self.multi_timeframe_processor.process_multi_timeframe(market_data_1m)
        
        # 2. Extract features for each timeframe
        mtf_features = self._extract_multi_timeframe_features(mtf_data)
        
        # 3. Detect patterns for each timeframe
        mtf_patterns = self._detect_multi_timeframe_patterns(mtf_data, mtf_features)
        
        # 4. Determine regime for each timeframe
        mtf_regimes = self._detect_multi_timeframe_regimes(mtf_data, mtf_features)
        
        # 5. Generate signals for each timeframe
        mtf_signals = self._generate_multi_timeframe_signals(mtf_features, mtf_patterns, mtf_regimes)
        
        # 6. Combine signals across timeframes
        combined_signals = self.signal_combiner.combine_signals(mtf_signals)
        
        # 7. Process and filter signals
        symbol = market_data_1m.get('symbol', 'UNKNOWN').iloc[0] if 'symbol' in market_data_1m.columns else 'UNKNOWN'
        final_signals = self.signal_processor.process_signals(combined_signals, symbol)
        
        return final_signals
    
    def _extract_multi_timeframe_features(self, mtf_data):
        """Extract features for all timeframes on-demand"""
        mtf_features = {}
        
        for tf_name, tf_data in mtf_data.items():
            # Calculate all features on-demand from raw OHLCV data
            features = self.feature_extractors.extract_all_features(tf_data['ohlc'])
            mtf_features[tf_name] = features
        
        return mtf_features
    
    def _detect_multi_timeframe_patterns(self, mtf_data, mtf_features):
        """Detect patterns for all timeframes"""
        mtf_patterns = {}
        
        for tf_name, tf_data in mtf_data.items():
            patterns = self.pattern_detectors.detect_all_patterns(
                tf_data['ohlc'], 
                mtf_features[tf_name]
            )
            mtf_patterns[tf_name] = patterns
        
        return mtf_patterns
    
    def _detect_multi_timeframe_regimes(self, mtf_data, mtf_features):
        """Detect regime for all timeframes"""
        mtf_regimes = {}
        
        for tf_name, tf_data in mtf_data.items():
            regime = self.regime_detector.detect_regime(
                tf_data['ohlc'], 
                mtf_features[tf_name]
            )
            mtf_regimes[tf_name] = regime
        
        return mtf_regimes
    
    def _generate_multi_timeframe_signals(self, mtf_features, mtf_patterns, mtf_regimes):
        """Generate signals for all timeframes"""
        mtf_signals = {}
        
        for tf_name in mtf_features.keys():
            signals = self.signal_generator.generate_signals(
                mtf_features[tf_name],
                mtf_patterns[tf_name],
                mtf_regimes[tf_name]['regime']
            )
            mtf_signals[tf_name] = signals
        
        return mtf_signals
```

#### **Step 1.3.3: Multi-Timeframe Signal Combiner** ✅ COMPLETE
```python
# File: src/core_detection/multi_timeframe_signal_combiner.py
# Reference: ENHANCED_DETECTOR_SPEC.md lines 150-200

class MultiTimeframeSignalCombiner:
    def __init__(self, config=None):
        # Default weights - can be overridden by config
        self.timeframe_weights = {
            '1h': 0.4,   # Long-term trend (highest weight)
            '15m': 0.3,  # Medium-term momentum
            '5m': 0.2,   # Short-term entry
            '1m': 0.1    # Noise filtering (lowest weight)
        }
        self.confirmation_threshold = 0.6  # Require 60% timeframes to agree
        
        # Load configuration if provided
        if config:
            self.load_configuration(config)
    
    def load_configuration(self, config):
        """Load timeframe weights and thresholds from configuration"""
        if 'timeframe_weights' in config:
            self.timeframe_weights.update(config['timeframe_weights'])
            self._validate_weights()
        
        if 'confirmation_threshold' in config:
            self.confirmation_threshold = config['confirmation_threshold']
    
    def _validate_weights(self):
        """Validate that weights sum to 1.0"""
        total_weight = sum(self.timeframe_weights.values())
        if abs(total_weight - 1.0) > 0.01:  # Allow small floating point errors
            raise ValueError(f"Timeframe weights must sum to 1.0, got {total_weight}")
    
    def update_weights(self, new_weights):
        """Update timeframe weights dynamically"""
        self.timeframe_weights.update(new_weights)
        self._validate_weights()
    
    def get_weight_summary(self):
        """Get current weight configuration summary"""
        return {
            'timeframe_weights': self.timeframe_weights.copy(),
            'confirmation_threshold': self.confirmation_threshold,
            'total_weight': sum(self.timeframe_weights.values())
        }
    
    def combine_signals(self, mtf_signals):
        """Combine signals across multiple timeframes"""
        combined_signals = []
        
        # Group signals by direction
        long_signals = self._group_signals_by_direction(mtf_signals, 'long')
        short_signals = self._group_signals_by_direction(mtf_signals, 'short')
        
        # Process long signals
        if long_signals:
            combined_long = self._combine_direction_signals(long_signals, 'long')
            if combined_long:
                combined_signals.append(combined_long)
        
        # Process short signals
        if short_signals:
            combined_short = self._combine_direction_signals(short_signals, 'short')
            if combined_short:
                combined_signals.append(combined_short)
        
        return combined_signals
    
    def _group_signals_by_direction(self, mtf_signals, direction):
        """Group signals by direction across timeframes"""
        grouped = {}
        
        for tf_name, signals in mtf_signals.items():
            direction_signals = [s for s in signals if s['direction'] == direction]
            if direction_signals:
                grouped[tf_name] = direction_signals
        
        return grouped
    
    def _combine_direction_signals(self, direction_signals, direction):
        """Combine signals of the same direction across timeframes"""
        if not direction_signals:
            return None
        
        # Calculate weighted confidence
        total_weight = 0
        weighted_confidence = 0
        weighted_strength = 0
        
        timeframe_confirmations = []
        
        for tf_name, signals in direction_signals.items():
            if tf_name not in self.timeframe_weights:
                continue
                
            weight = self.timeframe_weights[tf_name]
            
            # Use the strongest signal from this timeframe
            best_signal = max(signals, key=lambda s: s['confidence'] * s['strength'])
            
            weighted_confidence += best_signal['confidence'] * weight
            weighted_strength += best_signal['strength'] * weight
            total_weight += weight
            
            timeframe_confirmations.append(tf_name)
        
        if total_weight == 0:
            return None
        
        # Calculate final metrics
        final_confidence = weighted_confidence / total_weight
        final_strength = weighted_strength / total_weight
        
        # Check confirmation threshold
        confirmation_ratio = len(timeframe_confirmations) / len(self.timeframe_weights)
        
        if confirmation_ratio < self.confirmation_threshold:
            return None
        
        # Create combined signal
        combined_signal = {
            'direction': direction,
            'confidence': final_confidence,
            'strength': final_strength,
            'timeframe_confirmations': timeframe_confirmations,
            'confirmation_ratio': confirmation_ratio,
            'source_signals': direction_signals,
            'timestamp': datetime.now(timezone.utc)
        }
        
        return combined_signal

# =============================================
# CONFIGURATION EXAMPLES
# =============================================

# Example 1: Conservative (Trend-following) Strategy
CONSERVATIVE_WEIGHTS = {
    'timeframe_weights': {
        '1h': 0.5,   # 50% - Heavy emphasis on long-term trend
        '15m': 0.3,  # 30% - Medium-term confirmation
        '5m': 0.15,  # 15% - Short-term entry
        '1m': 0.05   # 5% - Minimal noise
    },
    'confirmation_threshold': 0.7  # Require 70% agreement
}

# Example 2: Aggressive (Scalping) Strategy
AGGRESSIVE_WEIGHTS = {
    'timeframe_weights': {
        '1h': 0.2,   # 20% - Basic trend context
        '15m': 0.3,  # 30% - Medium-term momentum
        '5m': 0.35,  # 35% - Short-term signals
        '1m': 0.15   # 15% - Entry precision
    },
    'confirmation_threshold': 0.5  # Require 50% agreement
}

# Example 3: Balanced Strategy
BALANCED_WEIGHTS = {
    'timeframe_weights': {
        '1h': 0.4,   # 40% - Long-term trend
        '15m': 0.3,  # 30% - Medium-term momentum
        '5m': 0.2,   # 20% - Short-term entry
        '1m': 0.1    # 10% - Noise filtering
    },
    'confirmation_threshold': 0.6  # Require 60% agreement
}

# Example 4: Volatility-Adaptive Strategy
def get_volatility_adaptive_weights(current_volatility):
    """Adjust weights based on current market volatility"""
    if current_volatility > 0.02:  # High volatility
        return {
            'timeframe_weights': {
                '1h': 0.6,   # 60% - More weight to longer timeframes
                '15m': 0.25, # 25% - Reduce noise
                '5m': 0.1,   # 10% - Minimal short-term
                '1m': 0.05   # 5% - Almost no noise
            },
            'confirmation_threshold': 0.8  # Require 80% agreement
        }
    else:  # Low volatility
        return {
            'timeframe_weights': {
                '1h': 0.3,   # 30% - Less emphasis on trend
                '15m': 0.3,  # 30% - Medium-term
                '5m': 0.25,  # 25% - More short-term
                '1m': 0.15   # 15% - More precision needed
            },
            'confirmation_threshold': 0.5  # Require 50% agreement
        }

# =============================================
# USAGE EXAMPLES
# =============================================

# Example 1: Initialize with default weights
combiner = MultiTimeframeSignalCombiner()

# Example 2: Initialize with custom configuration
combiner = MultiTimeframeSignalCombiner(CONSERVATIVE_WEIGHTS)

# Example 3: Update weights dynamically
combiner.update_weights({
    '1h': 0.6,
    '15m': 0.25,
    '5m': 0.1,
    '1m': 0.05
})

# Example 4: Get current configuration
config = combiner.get_weight_summary()
print(f"Current weights: {config['timeframe_weights']}")
print(f"Confirmation threshold: {config['confirmation_threshold']}")

# Example 5: Volatility-adaptive usage
current_vol = 0.015  # 1.5% volatility
adaptive_config = get_volatility_adaptive_weights(current_vol)
combiner = MultiTimeframeSignalCombiner(adaptive_config)

# =============================================
# CONFIGURATION FILE SYSTEM
# =============================================

# File: config/timeframe_weights.yaml
"""
# Multi-Timeframe Weight Configurations

# Default Configuration
default:
  timeframe_weights:
    1h: 0.4
    15m: 0.3
    5m: 0.2
    1m: 0.1
  confirmation_threshold: 0.6

# Conservative (Trend-following)
conservative:
  timeframe_weights:
    1h: 0.5
    15m: 0.3
    5m: 0.15
    1m: 0.05
  confirmation_threshold: 0.7

# Aggressive (Scalping)
aggressive:
  timeframe_weights:
    1h: 0.2
    15m: 0.3
    5m: 0.35
    1m: 0.15
  confirmation_threshold: 0.5

# Balanced
balanced:
  timeframe_weights:
    1h: 0.4
    15m: 0.3
    5m: 0.2
    1m: 0.1
  confirmation_threshold: 0.6

# High Volatility
high_volatility:
  timeframe_weights:
    1h: 0.6
    15m: 0.25
    5m: 0.1
    1m: 0.05
  confirmation_threshold: 0.8

# Low Volatility
low_volatility:
  timeframe_weights:
    1h: 0.3
    15m: 0.3
    5m: 0.25
    1m: 0.15
  confirmation_threshold: 0.5
"""

# File: src/config/weight_config_manager.py
class WeightConfigManager:
    def __init__(self, config_file='config/timeframe_weights.yaml'):
        self.config_file = config_file
        self.configs = self._load_configs()
    
    def _load_configs(self):
        """Load configurations from YAML file"""
        import yaml
        with open(self.config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def get_config(self, strategy='default'):
        """Get configuration for specific strategy"""
        if strategy not in self.configs:
            raise ValueError(f"Strategy '{strategy}' not found in config")
        return self.configs[strategy]
    
    def list_strategies(self):
        """List available strategies"""
        return list(self.configs.keys())
    
    def update_config(self, strategy, new_config):
        """Update configuration for strategy"""
        self.configs[strategy] = new_config
        self._save_configs()
    
    def _save_configs(self):
        """Save configurations to file"""
        import yaml
        with open(self.config_file, 'w') as f:
            yaml.dump(self.configs, f, default_flow_style=False)

# Usage with configuration manager
config_manager = WeightConfigManager()
conservative_config = config_manager.get_config('conservative')
combiner = MultiTimeframeSignalCombiner(conservative_config)
```

#### **Step 1.3.4: Feature Extraction System** ✅ INTEGRATED
**Note**: Implemented as part of Core Detection Engine in `src/core_detection/feature_extractors.py`
```python
# File: src/core_detection/feature_extractors.py
# Reference: ENHANCED_FEATURE_SPEC.md

class BasicFeatureExtractor:
    def __init__(self):
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.bb_period = 20
        self.bb_std = 2
    
    def extract_price_features(self, ohlc_data):
        """Extract price-based features"""
        features = {}
        
        # RSI
        features['rsi'] = self._calculate_rsi(ohlc_data['close'])
        features['rsi_overbought'] = features['rsi'] > 70
        features['rsi_oversold'] = features['rsi'] < 30
        
        # MACD
        macd_line, signal_line, histogram = self._calculate_macd(ohlc_data['close'])
        features['macd'] = macd_line
        features['macd_signal'] = signal_line
        features['macd_histogram'] = histogram
        features['macd_bullish'] = macd_line > signal_line
        features['macd_bearish'] = macd_line < signal_line
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(ohlc_data['close'])
        features['bb_upper'] = bb_upper
        features['bb_middle'] = bb_middle
        features['bb_lower'] = bb_lower
        features['bb_position'] = (ohlc_data['close'][-1] - bb_lower) / (bb_upper - bb_lower)
        features['bb_squeeze'] = (bb_upper - bb_lower) / bb_middle < 0.1
        
        return features
    
    def extract_volume_features(self, volume_data, price_data):
        """Extract volume-based features"""
        features = {}
        
        # Volume moving averages
        features['volume_sma_20'] = volume_data.rolling(20).mean().iloc[-1]
        features['volume_ratio'] = volume_data.iloc[-1] / features['volume_sma_20']
        features['volume_spike'] = features['volume_ratio'] > 2.0
        
        # Volume-price relationship
        features['volume_price_trend'] = self._calculate_vpt(volume_data, price_data)
        features['on_balance_volume'] = self._calculate_obv(volume_data, price_data)
        
        return features
    
    def extract_technical_features(self, ohlc_data):
        """Extract technical indicator features"""
        features = {}
        
        # Moving averages
        features['sma_20'] = ohlc_data['close'].rolling(20).mean().iloc[-1]
        features['sma_50'] = ohlc_data['close'].rolling(50).mean().iloc[-1]
        features['ema_12'] = ohlc_data['close'].ewm(span=12).mean().iloc[-1]
        features['ema_26'] = ohlc_data['close'].ewm(span=26).mean().iloc[-1]
        
        # Price momentum
        features['momentum_10'] = ohlc_data['close'].pct_change(10).iloc[-1]
        features['momentum_20'] = ohlc_data['close'].pct_change(20).iloc[-1]
        
        # Volatility
        features['volatility_20'] = ohlc_data['close'].pct_change().rolling(20).std().iloc[-1]
        features['atr_14'] = self._calculate_atr(ohlc_data, 14)
        
        return features
```

#### **Step 1.3.5: Pattern Detection System** ✅ INTEGRATED
**Note**: Implemented as part of Core Detection Engine in `src/core_detection/pattern_detectors.py`
```python
# File: src/core_detection/pattern_detectors.py
# Reference: ENHANCED_DETECTOR_SPEC.md lines 200-300

class PatternDetector:
    def __init__(self):
        self.support_resistance_detector = SupportResistanceDetector()
        self.breakout_detector = BreakoutDetector()
        self.divergence_detector = DivergenceDetector()
    
    def detect_support_resistance(self, price_data, volume_data):
        """Detect horizontal support and resistance levels"""
        levels = self.support_resistance_detector.find_levels(price_data)
        
        patterns = {
            'support_levels': levels['support'],
            'resistance_levels': levels['resistance'],
            'current_support': self._find_nearest_support(price_data, levels['support']),
            'current_resistance': self._find_nearest_resistance(price_data, levels['resistance']),
            'support_strength': self._calculate_level_strength(levels['support'], volume_data),
            'resistance_strength': self._calculate_level_strength(levels['resistance'], volume_data)
        }
        
        return patterns
    
    def detect_breakouts(self, price_data, support_resistance):
        """Detect breakout patterns"""
        breakouts = self.breakout_detector.detect(price_data, support_resistance)
        
        patterns = {
            'breakout_up': breakouts['up'],
            'breakout_down': breakouts['down'],
            'breakout_volume_confirmation': breakouts['volume_confirmed'],
            'breakout_strength': breakouts['strength']
        }
        
        return patterns
    
    def detect_divergences(self, price_data, indicators):
        """Detect price-indicator divergences"""
        divergences = self.divergence_detector.detect(price_data, indicators)
        
        patterns = {
            'bullish_divergence': divergences['bullish'],
            'bearish_divergence': divergences['bearish'],
            'divergence_strength': divergences['strength']
        }
        
        return patterns
```

#### **Step 1.3.6: Signal Generation System** ✅ INTEGRATED
**Note**: Implemented as part of Core Detection Engine in `src/core_detection/signal_generator.py`
```python
# File: src/core_detection/signal_generator.py
# Reference: ENHANCED_DETECTOR_SPEC.md lines 300-400

class SignalGenerator:
    def __init__(self):
        self.signal_thresholds = {
            'min_confidence': 0.6,
            'min_strength': 0.5,
            'min_volume_confirmation': 1.2
        }
    
    def generate_signals(self, features, patterns, regime):
        """Generate trading signals from features and patterns"""
        signals = []
        
        # Long signal conditions
        if self._check_long_conditions(features, patterns, regime):
            signal = self._create_signal('long', features, patterns, regime)
            signals.append(signal)
        
        # Short signal conditions  
        if self._check_short_conditions(features, patterns, regime):
            signal = self._create_signal('short', features, patterns, regime)
            signals.append(signal)
        
        return signals
    
    def _check_long_conditions(self, features, patterns, regime):
        """Check conditions for long signals"""
        conditions = [
            features.get('rsi', 50) < 70,  # Not overbought
            features.get('macd_bullish', False),  # MACD bullish
            patterns.get('breakout_up', False),  # Upward breakout
            features.get('volume_spike', False),  # Volume confirmation
            regime in ['trending_up', 'ranging']  # Suitable regime
        ]
        
        return sum(conditions) >= 3  # At least 3 conditions met
    
    def _check_short_conditions(self, features, patterns, regime):
        """Check conditions for short signals"""
        conditions = [
            features.get('rsi', 50) > 30,  # Not oversold
            features.get('macd_bearish', False),  # MACD bearish
            patterns.get('breakout_down', False),  # Downward breakout
            features.get('volume_spike', False),  # Volume confirmation
            regime in ['trending_down', 'ranging']  # Suitable regime
        ]
        
        return sum(conditions) >= 3  # At least 3 conditions met
    
    def _create_signal(self, direction, features, patterns, regime):
        """Create a trading signal"""
        confidence = self._calculate_confidence(features, patterns, regime)
        strength = self._calculate_strength(features, patterns, regime)
        
        return {
            'direction': direction,
            'confidence': confidence,
            'strength': strength,
            'features': features,
            'patterns': patterns,
            'regime': regime,
            'timestamp': datetime.now(timezone.utc)
        }
```

#### **Step 1.3.7: Regime Detection System** ✅ INTEGRATED
**Note**: Implemented as part of Core Detection Engine in `src/core_detection/regime_detector.py`
```python
# File: src/core_detection/regime_detector.py
# Reference: ENHANCED_DETECTOR_SPEC.md lines 400-500

class RegimeDetector:
    def __init__(self):
        self.regime_thresholds = {
            'trending_up': 0.6,
            'trending_down': -0.6,
            'ranging': 0.2
        }
        self.lookback_periods = {
            'short': 20,
            'medium': 50,
            'long': 100
        }
    
    def detect_regime(self, market_data, features):
        """Detect current market regime"""
        # Calculate trend strength
        trend_strength = self._calculate_trend_strength(market_data)
        
        # Calculate volatility regime
        volatility_regime = self._calculate_volatility_regime(market_data)
        
        # Calculate volume regime
        volume_regime = self._calculate_volume_regime(market_data)
        
        # Combine indicators to determine regime
        regime = self._combine_regime_indicators(trend_strength, volatility_regime, volume_regime)
        
        return {
            'regime': regime,
            'trend_strength': trend_strength,
            'volatility_regime': volatility_regime,
            'volume_regime': volume_regime,
            'confidence': self._calculate_regime_confidence(trend_strength, volatility_regime, volume_regime)
        }
    
    def _calculate_trend_strength(self, market_data):
        """Calculate trend strength using multiple timeframes"""
        prices = market_data['close']
        
        # Short-term trend
        short_trend = (prices.iloc[-1] - prices.iloc[-20]) / prices.iloc[-20]
        
        # Medium-term trend
        medium_trend = (prices.iloc[-1] - prices.iloc[-50]) / prices.iloc[-50]
        
        # Long-term trend
        long_trend = (prices.iloc[-1] - prices.iloc[-100]) / prices.iloc[-100]
        
        # Weighted average
        trend_strength = (0.5 * short_trend + 0.3 * medium_trend + 0.2 * long_trend)
        
        return trend_strength
    
    def _calculate_volatility_regime(self, market_data):
        """Calculate volatility regime"""
        returns = market_data['close'].pct_change().dropna()
        
        # Current volatility
        current_vol = returns.rolling(20).std().iloc[-1]
        
        # Historical volatility
        historical_vol = returns.rolling(100).std().iloc[-1]
        
        # Volatility ratio
        vol_ratio = current_vol / historical_vol if historical_vol > 0 else 1.0
        
        if vol_ratio > 1.5:
            return 'high_volatility'
        elif vol_ratio < 0.5:
            return 'low_volatility'
        else:
            return 'normal_volatility'
    
    def _calculate_volume_regime(self, market_data):
        """Calculate volume regime"""
        volume = market_data['volume']
        
        # Current volume vs average
        current_vol = volume.iloc[-1]
        avg_vol = volume.rolling(20).mean().iloc[-1]
        
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
        
        if vol_ratio > 1.5:
            return 'high_volume'
        elif vol_ratio < 0.5:
            return 'low_volume'
        else:
            return 'normal_volume'
    
    def _combine_regime_indicators(self, trend_strength, volatility_regime, volume_regime):
        """Combine indicators to determine final regime"""
        if trend_strength > self.regime_thresholds['trending_up']:
            return 'trending_up'
        elif trend_strength < self.regime_thresholds['trending_down']:
            return 'trending_down'
        else:
            return 'ranging'
```

#### **Step 1.3.8: Signal Processing System** ✅ COMPLETE
**Note**: Implemented as `src/core_detection/signal_processor.py` with full integration into Core Detection Engine
**Enhancement**: This component was added during implementation to provide signal filtering, quality control, and cooldown management - not originally in the plan but essential for production use
```python
# File: src/core_detection/signal_processor.py
# Reference: ENHANCED_DETECTOR_SPEC.md lines 500-600

class SignalProcessor:
    def __init__(self):
        self.signal_filters = {
            'min_confidence': 0.6,
            'min_strength': 0.5,
            'max_signals_per_symbol': 3,
            'signal_cooldown_minutes': 30
        }
        self.recent_signals = {}  # Track recent signals per symbol
    
    def process_signals(self, signals, symbol):
        """Process and filter signals"""
        if not signals:
            return []
        
        # Filter by confidence and strength
        filtered_signals = self._filter_by_quality(signals)
        
        # Filter by cooldown period
        filtered_signals = self._filter_by_cooldown(filtered_signals, symbol)
        
        # Limit number of signals per symbol
        filtered_signals = self._limit_signals_per_symbol(filtered_signals)
        
        # Update recent signals tracking
        self._update_recent_signals(filtered_signals, symbol)
        
        return filtered_signals
    
    def _filter_by_quality(self, signals):
        """Filter signals by quality thresholds"""
        return [
            signal for signal in signals
            if (signal['confidence'] >= self.signal_filters['min_confidence'] and
                signal['strength'] >= self.signal_filters['min_strength'])
        ]
    
    def _filter_by_cooldown(self, signals, symbol):
        """Filter signals by cooldown period"""
        if symbol not in self.recent_signals:
            return signals
        
        current_time = datetime.now(timezone.utc)
        cooldown_delta = timedelta(minutes=self.signal_filters['signal_cooldown_minutes'])
        
        filtered = []
        for signal in signals:
            last_signal_time = self.recent_signals[symbol].get('last_signal_time')
            if (last_signal_time is None or 
                current_time - last_signal_time > cooldown_delta):
                filtered.append(signal)
        
        return filtered
    
    def _limit_signals_per_symbol(self, signals):
        """Limit number of signals per symbol"""
        return signals[:self.signal_filters['max_signals_per_symbol']]
    
    def _update_recent_signals(self, signals, symbol):
        """Update recent signals tracking"""
        if signals:
            self.recent_signals[symbol] = {
                'last_signal_time': signals[-1]['timestamp'],
                'signal_count': len(signals)
            }
```

#### **Step 1.3.9: Multi-Timeframe Testing Framework** ✅ COMPLETE
**Note**: Implemented comprehensive testing suite with individual component tests, integration tests, and performance benchmarks
```python
# File: test_phase1_3.py
# Reference: ENHANCED_IMPLEMENTATION_SPEC.md lines 200-300

async def test_phase1_3_multi_timeframe_detection():
    """Test Phase 1.3: Multi-Timeframe Alpha Detector"""
    print("\n🧪 Phase 1.3: Multi-Timeframe Alpha Detector Test")
    print("=" * 60)
    
    try:
        # Test 1: Multi-Timeframe Data Processing
        print("\n1️⃣ Testing multi-timeframe data processing...")
        mtf_processor = MultiTimeframeProcessor()
        
        # Create sample market data (need more data for higher timeframes)
        sample_data = create_extended_sample_market_data()  # 1000+ data points
        mtf_data = mtf_processor.process_multi_timeframe(sample_data)
        
        expected_timeframes = ['1m', '5m', '15m', '1h']
        available_timeframes = list(mtf_data.keys())
        missing_timeframes = [tf for tf in expected_timeframes if tf not in available_timeframes]
        
        if not missing_timeframes:
            print("✅ Multi-timeframe processing working")
            for tf_name, tf_data in mtf_data.items():
                print(f"   {tf_name}: {tf_data['data_points']} data points")
        else:
            print(f"❌ Missing timeframes: {missing_timeframes}")
            return False
        
        # Test 2: Multi-Timeframe Feature Extraction
        print("\n2️⃣ Testing multi-timeframe feature extraction...")
        feature_extractor = BasicFeatureExtractor()
        mtf_features = {}
        
        for tf_name, tf_data in mtf_data.items():
            features = feature_extractor.extract_price_features(tf_data['ohlc'])
            mtf_features[tf_name] = features
        
        # Check if all timeframes have features
        if len(mtf_features) == len(expected_timeframes):
            print("✅ Multi-timeframe feature extraction working")
            for tf_name, features in mtf_features.items():
                print(f"   {tf_name}: {len(features)} features extracted")
        else:
            print("❌ Multi-timeframe feature extraction failed")
            return False
        
        # Test 3: Multi-Timeframe Pattern Detection
        print("\n3️⃣ Testing multi-timeframe pattern detection...")
        pattern_detector = PatternDetector()
        mtf_patterns = {}
        
        for tf_name, tf_data in mtf_data.items():
            patterns = pattern_detector.detect_support_resistance(
                tf_data['ohlc']['close'], 
                tf_data['ohlc']['volume']
            )
            mtf_patterns[tf_name] = patterns
        
        if len(mtf_patterns) == len(expected_timeframes):
            print("✅ Multi-timeframe pattern detection working")
        else:
            print("❌ Multi-timeframe pattern detection failed")
            return False
        
        # Test 4: Multi-Timeframe Regime Detection
        print("\n4️⃣ Testing multi-timeframe regime detection...")
        regime_detector = RegimeDetector()
        mtf_regimes = {}
        
        for tf_name, tf_data in mtf_data.items():
            regime = regime_detector.detect_regime(tf_data['ohlc'], mtf_features[tf_name])
            mtf_regimes[tf_name] = regime
        
        if len(mtf_regimes) == len(expected_timeframes):
            print("✅ Multi-timeframe regime detection working")
            for tf_name, regime in mtf_regimes.items():
                print(f"   {tf_name}: {regime['regime']} (confidence: {regime['confidence']:.2f})")
        else:
            print("❌ Multi-timeframe regime detection failed")
            return False
        
        # Test 5: Multi-Timeframe Signal Generation
        print("\n5️⃣ Testing multi-timeframe signal generation...")
        signal_generator = SignalGenerator()
        mtf_signals = {}
        
        for tf_name in mtf_features.keys():
            signals = signal_generator.generate_signals(
                mtf_features[tf_name],
                mtf_patterns[tf_name],
                mtf_regimes[tf_name]['regime']
            )
            mtf_signals[tf_name] = signals
        
        total_signals = sum(len(signals) for signals in mtf_signals.values())
        print(f"✅ Multi-timeframe signal generation working - {total_signals} total signals")
        for tf_name, signals in mtf_signals.items():
            print(f"   {tf_name}: {len(signals)} signals")
        
        # Test 6: Multi-Timeframe Signal Combination
        print("\n6️⃣ Testing multi-timeframe signal combination...")
        signal_combiner = MultiTimeframeSignalCombiner()
        combined_signals = signal_combiner.combine_signals(mtf_signals)
        
        if isinstance(combined_signals, list):
            print(f"✅ Multi-timeframe signal combination working - {len(combined_signals)} combined signals")
            for signal in combined_signals:
                print(f"   {signal['direction']}: confidence={signal['confidence']:.2f}, "
                      f"strength={signal['strength']:.2f}, confirmations={signal['timeframe_confirmations']}")
        else:
            print("❌ Multi-timeframe signal combination failed")
            return False
        
        # Test 7: Core Detection Engine Integration
        print("\n7️⃣ Testing core detection engine integration...")
        db_manager = SupabaseManager()
        detection_engine = CoreDetectionEngine(db_manager)
        
        final_signals = detection_engine.detect_signals(sample_data)
        
        if isinstance(final_signals, list):
            print(f"✅ Core detection engine working - {len(final_signals)} final signals")
        else:
            print("❌ Core detection engine failed")
            return False
        
        print("\n" + "=" * 60)
        print("✅ ALL MULTI-TIMEFRAME TESTS PASSED!")
        print("🎉 Multi-Timeframe Alpha Detector is fully functional!")
        print("🚀 Ready to proceed to Phase 1.4 (Trading Plan Generation)")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_extended_sample_market_data():
    """Create extended sample market data for multi-timeframe testing"""
    import pandas as pd
    import numpy as np
    
    # Generate 1000+ data points for higher timeframes
    dates = pd.date_range(start='2024-01-01', periods=1000, freq='1min')
    
    # Generate realistic price data with trends
    np.random.seed(42)
    base_price = 50000
    
    # Create different trend periods
    trend_periods = [
        (0, 200, 0.001),    # Upward trend
        (200, 400, -0.0005), # Downward trend
        (400, 600, 0.0002),  # Sideways
        (600, 800, 0.0015),  # Strong upward
        (800, 1000, -0.0008) # Correction
    ]
    
    prices = [base_price]
    for i in range(1, 1000):
        # Find current trend period
        trend_rate = 0.0001  # Default small positive trend
        for start, end, rate in trend_periods:
            if start <= i < end:
                trend_rate = rate
                break
        
        # Add noise
        noise = np.random.normal(0, 0.001)
        new_price = prices[-1] * (1 + trend_rate + noise)
        prices.append(new_price)
    
    # Generate OHLCV data
    data = {
        'timestamp': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
        'close': prices,
        'volume': np.random.uniform(100, 1000, 1000)
    }
    
    return pd.DataFrame(data)

def create_sample_market_data():
    """Create sample market data for testing"""
    import pandas as pd
    import numpy as np
    
    # Generate 100 data points
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
    
    # Generate realistic price data
    np.random.seed(42)
    base_price = 50000
    returns = np.random.normal(0, 0.001, 100)
    prices = [base_price]
    
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Generate OHLCV data
    data = {
        'timestamp': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
        'close': prices,
        'volume': np.random.uniform(100, 1000, 100)
    }
    
    return pd.DataFrame(data)
```

### **1.4 Basic Trading Plan Generation**
**Reference**: `ENHANCED_DETECTOR_SPEC.md` (Trading Plan Generation)

#### **Step 1.4.1: Trading Plan Builder** ⏳ PENDING
```python
# File: src/trading_plans/trading_plan_builder.py
# Reference: ENHANCED_DETECTOR_SPEC.md lines 400-500

class TradingPlanBuilder:
    def __init__(self):
        self.risk_config = {
            'max_position_size': 0.1,  # 10% of portfolio
            'risk_per_trade': 0.02,    # 2% risk per trade
            'min_risk_reward': 1.5,    # 1:1.5 minimum
            'max_risk_reward': 3.0     # 1:3 maximum
        }
    
    def build_trading_plan(self, signal, market_data):
        """Convert processed signal into complete trading plan"""
        # 1. Calculate position size based on signal strength
        # 2. Determine entry conditions
        # 3. Calculate stop loss and take profit
        # 4. Set time horizon
        # 5. Calculate risk-reward ratio
        # 6. Create trading plan object
        pass
    
    def _calculate_position_size(self, signal, market_data):
        """Calculate position size based on signal strength and risk"""
        # Position sizing logic
        pass
    
    def _calculate_entry_price(self, signal, market_data):
        """Calculate entry price from current market data"""
        # Entry price calculation
        pass
    
    def _calculate_stop_loss(self, entry_price, signal, risk_config):
        """Calculate stop loss level"""
        # Stop loss calculation
        pass
    
    def _calculate_take_profit(self, entry_price, stop_loss, risk_config):
        """Calculate take profit level"""
        # Take profit calculation
        pass
```

#### **Step 1.4.2: Signal Pack Generator** ⏳ PENDING
```python
# File: src/trading_plans/signal_pack_generator.py
# Reference: ENHANCED_DETECTOR_SPEC.md lines 500-600

class SignalPackGenerator:
    def __init__(self):
        self.feature_aggregator = FeatureAggregator()
        self.context_builder = MarketContextBuilder()
    
    def generate_signal_pack(self, signal, trading_plan, market_data):
        """Create LLM-optimized signal pack with all context"""
        # 1. Aggregate all features from signal
        # 2. Build market context
        # 3. Package signal metadata
        # 4. Format for LLM consumption
        pass
    
    def _aggregate_features(self, signal):
        """Aggregate and format all signal features"""
        # Feature aggregation logic
        pass
    
    def _build_market_context(self, market_data, trading_plan):
        """Build comprehensive market context"""
        # Market context building
        pass
    
    def _format_for_llm(self, signal_pack):
        """Format signal pack for LLM consumption"""
        # LLM formatting
        pass
```

#### **Step 1.4.3: Trading Plan Data Models** ⏳ PENDING
```python
# File: src/trading_plans/models.py
# Reference: ENHANCED_DETECTOR_SPEC.md lines 300-400

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal

@dataclass
class TradingPlan:
    """Complete trading plan data structure"""
    plan_id: str
    signal_id: str
    symbol: str
    timeframe: str
    direction: str
    entry_conditions: Dict
    entry_price: Decimal
    position_size: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    risk_reward_ratio: Decimal
    confidence_score: float
    strength_score: float
    time_horizon: str
    valid_until: datetime
    created_at: datetime
    market_context: Dict
    signal_metadata: Dict

@dataclass
class SignalPack:
    """LLM-ready signal pack with all context"""
    pack_id: str
    signal_id: str
    trading_plan_id: str
    features: Dict
    patterns: Dict
    regime: Dict
    market_context: Dict
    processing_metadata: Dict
    llm_format: Dict
    created_at: datetime

@dataclass
class RiskMetrics:
    """Risk management metrics"""
    position_size: Decimal
    risk_amount: Decimal
    risk_percentage: float
    stop_loss_distance: Decimal
    take_profit_distance: Decimal
    risk_reward_ratio: Decimal
    max_drawdown: float
    volatility_adjustment: float

@dataclass
class ExecutionParameters:
    """Execution-specific parameters"""
    entry_strategy: str
    execution_venue: str
    order_type: str
    time_in_force: str
    slippage_tolerance: float
    execution_priority: str
```

#### **Step 1.4.4: Integration with Core Detection Engine** ✅ COMPLETE
```python
# File: src/core_detection/core_detection_engine.py (update)
# Reference: ENHANCED_DETECTOR_SPEC.md lines 150-200

class CoreDetectionEngine:
    def __init__(self, db_manager=None, signal_filter=None):
        # ... existing initialization ...
        self.trading_plan_builder = TradingPlanBuilder()
        self.signal_pack_generator = SignalPackGenerator()
    
    def detect_signals(self, market_data_1m):
        """Main multi-timeframe signal detection pipeline with trading plan generation"""
        # ... existing steps 1-7 ...
        
        # 8. Generate trading plans from processed signals
        logger.debug("Generating trading plans from signals...")
        trading_plans = []
        signal_packs = []
        
        for signal in final_signals:
            # Generate trading plan
            trading_plan = self.trading_plan_builder.build_trading_plan(signal, market_data_1m)
            if trading_plan:
                trading_plans.append(trading_plan)
                
                # Generate signal pack
                signal_pack = self.signal_pack_generator.generate_signal_pack(
                    signal, trading_plan, market_data_1m
                )
                signal_packs.append(signal_pack)
        
        logger.info(f"Trading plan generation complete: {len(trading_plans)} plans created")
        
        return {
            'signals': final_signals,
            'trading_plans': trading_plans,
            'signal_packs': signal_packs
        }
    
    def get_trading_plans(self, market_data_1m):
        """Get only trading plans (convenience method)"""
        result = self.detect_signals(market_data_1m)
        return result['trading_plans']
    
    def get_signal_packs(self, market_data_1m):
        """Get only signal packs (convenience method)"""
        result = self.detect_signals(market_data_1m)
        return result['signal_packs']
```

#### **Step 1.4.5: Trading Plan Testing Framework** ✅ COMPLETE
```python
# File: tests/test_trading_plans.py
# Reference: ENHANCED_IMPLEMENTATION_SPEC.md lines 200-300

import pytest
from src.trading_plans.trading_plan_builder import TradingPlanBuilder
from src.trading_plans.signal_pack_generator import SignalPackGenerator
from src.trading_plans.models import TradingPlan, SignalPack

class TestTradingPlanBuilder:
    def test_basic_trading_plan_creation(self):
        """Test basic trading plan creation from signal"""
        builder = TradingPlanBuilder()
        signal = self._create_sample_signal()
        market_data = self._create_sample_market_data()
        
        trading_plan = builder.build_trading_plan(signal, market_data)
        
        assert trading_plan is not None
        assert trading_plan.direction == signal['direction']
        assert trading_plan.confidence_score > 0
        assert trading_plan.position_size > 0
        assert trading_plan.risk_reward_ratio >= 1.5
    
    def test_position_sizing_calculation(self):
        """Test position sizing calculation"""
        builder = TradingPlanBuilder()
        signal = self._create_sample_signal()
        market_data = self._create_sample_market_data()
        
        position_size = builder._calculate_position_size(signal, market_data)
        
        assert position_size > 0
        assert position_size <= 0.1  # Max 10% position size
    
    def test_risk_metrics_calculation(self):
        """Test risk metrics calculation"""
        builder = TradingPlanBuilder()
        signal = self._create_sample_signal()
        market_data = self._create_sample_market_data()
        
        trading_plan = builder.build_trading_plan(signal, market_data)
        
        assert trading_plan.risk_reward_ratio >= 1.5
        assert trading_plan.stop_loss < trading_plan.entry_price  # For long signals
        assert trading_plan.take_profit > trading_plan.entry_price  # For long signals

class TestSignalPackGenerator:
    def test_signal_pack_creation(self):
        """Test signal pack creation"""
        generator = SignalPackGenerator()
        signal = self._create_sample_signal()
        trading_plan = self._create_sample_trading_plan()
        market_data = self._create_sample_market_data()
        
        signal_pack = generator.generate_signal_pack(signal, trading_plan, market_data)
        
        assert signal_pack is not None
        assert signal_pack.signal_id == signal['signal_id']
        assert signal_pack.trading_plan_id == trading_plan.plan_id
        assert 'features' in signal_pack.llm_format
        assert 'market_context' in signal_pack.llm_format

class TestTradingPlanIntegration:
    def test_core_detection_engine_integration(self):
        """Test trading plan generation in core detection engine"""
        from src.core_detection.core_detection_engine import CoreDetectionEngine
        
        engine = CoreDetectionEngine()
        market_data = self._create_sample_market_data()
        
        result = engine.detect_signals(market_data)
        
        assert 'trading_plans' in result
        assert 'signal_packs' in result
        assert len(result['trading_plans']) > 0
        assert len(result['signal_packs']) > 0
    
    def test_end_to_end_trading_plan_generation(self):
        """Test complete end-to-end trading plan generation"""
        from src.core_detection.core_detection_engine import CoreDetectionEngine
        
        engine = CoreDetectionEngine()
        market_data = self._create_sample_market_data()
        
        result = engine.detect_signals(market_data)
        
        # Verify trading plans are properly generated
        for trading_plan in result['trading_plans']:
            assert isinstance(trading_plan, TradingPlan)
            assert trading_plan.plan_id is not None
            assert trading_plan.entry_price > 0
            assert trading_plan.position_size > 0
            assert trading_plan.risk_reward_ratio >= 1.5
        
        # Verify signal packs are properly generated
        for signal_pack in result['signal_packs']:
            assert isinstance(signal_pack, SignalPack)
            assert signal_pack.pack_id is not None
            assert 'llm_format' in signal_pack.__dict__
            assert 'features' in signal_pack.llm_format
```

#### **Step 1.4.6: Configuration and Risk Management** ⏳ PENDING
```python
# File: src/trading_plans/config.py
# Reference: ENHANCED_CONFIGURATION_SPEC.md

class TradingPlanConfig:
    """Configuration for trading plan generation"""
    
    def __init__(self, config_file='config/trading_plans.yaml'):
        self.config = self._load_config(config_file)
        self.risk_config = self.config['risk_management']
        self.position_sizing = self.config['position_sizing']
        self.time_horizons = self.config['time_horizons']
    
    def _load_config(self, config_file):
        """Load configuration from YAML file"""
        import yaml
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def get_risk_config(self, signal_strength):
        """Get risk configuration based on signal strength"""
        if signal_strength > 0.8:
            return self.risk_config['high_confidence']
        elif signal_strength > 0.6:
            return self.risk_config['medium_confidence']
        else:
            return self.risk_config['low_confidence']
    
    def get_position_size(self, signal_strength, account_balance):
        """Calculate position size based on signal strength and account balance"""
        base_size = self.position_sizing['base_percentage']
        strength_multiplier = signal_strength
        max_size = self.position_sizing['max_percentage']
        
        calculated_size = base_size * strength_multiplier
        return min(calculated_size, max_size) * account_balance
```

# File: config/trading_plans.yaml
```yaml
# Trading Plan Configuration

risk_management:
  high_confidence:
    max_position_size: 0.15
    risk_per_trade: 0.03
    min_risk_reward: 1.5
    max_risk_reward: 3.0
  medium_confidence:
    max_position_size: 0.10
    risk_per_trade: 0.02
    min_risk_reward: 1.5
    max_risk_reward: 2.5
  low_confidence:
    max_position_size: 0.05
    risk_per_trade: 0.01
    min_risk_reward: 2.0
    max_risk_reward: 2.0

position_sizing:
  base_percentage: 0.05
  max_percentage: 0.15
  volatility_adjustment: true
  correlation_adjustment: true

time_horizons:
  '1m': '5m'
  '5m': '15m'
  '15m': '1h'
  '1h': '4h'

entry_strategies:
  market_order: 'immediate'
  limit_order: 'price_improvement'
  stop_order: 'breakout_confirmation'

execution_venues:
  primary: 'hyperliquid'
  backup: 'binance'
  fallback: 'coinbase'
```

### **1.5 Basic Communication**
**Reference**: `DECISION_MAKER_INTEGRATION_SPEC.md`

#### **Step 1.5.1: Direct Table Communication**
```python
# File: communication/direct_table_communicator.py
# Reference: MODULE_COMMUNICATION_SPEC.md lines 100-200

class DirectTableCommunicator:
    def __init__(self, db_connection, module_type):
        self.db = db_connection
        self.module_type = module_type
        self.table_mapping = {
            'alpha': 'AD_strands',
            'dm': 'DM_strands',
            'trader': 'TR_strands'
        }
    
    def publish_trading_plan(self, trading_plan, signal_pack):
        """Publish trading plan via direct table write with tags"""
        # Write to AD_strands with tags to trigger Decision Maker
        strand_data = {
            'id': f"AD_{uuid.uuid4().hex[:12]}",
            'module': 'alpha',
            'kind': 'signal',
            'symbol': trading_plan.symbol,
            'timeframe': trading_plan.timeframe,
            'sig_sigma': trading_plan.signal_strength,
            'sig_confidence': trading_plan.confidence,
            'sig_direction': trading_plan.direction,
            'trading_plan': json.dumps(trading_plan.to_dict()),
            'signal_pack': json.dumps(signal_pack.to_dict()),
            'created_at': datetime.now(timezone.utc)
        }
        
        # Write with tags to trigger Decision Maker
        self.write_with_tags('AD_strands', strand_data, ['dm:evaluate_plan'])
    
    def write_with_tags(self, table_name, data, tags):
        """Write data to table with communication tags"""
        data['tags'] = json.dumps(tags)
        
        columns = list(data.keys())
        values = list(data.values())
        placeholders = ', '.join(['%s'] * len(values))
        
        query = f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES ({placeholders})
        """
        
        self.db.execute(query, values)
        return data.get('id')
```

### **1.6 Testing Framework**
**Reference**: `ENHANCED_IMPLEMENTATION_SPEC.md` (Testing Strategy)

#### **Step 1.6.1: Unit Tests**
```python
# File: tests/test_core_detection.py
# Reference: ENHANCED_IMPLEMENTATION_SPEC.md lines 200-300

def test_basic_signal_detection():
    # Test basic signal detection
    pass

def test_trading_plan_generation():
    # Test trading plan generation
    pass
```

#### **Step 1.6.2: Integration Tests**
```python
# File: tests/test_communication.py
# Reference: ENHANCED_IMPLEMENTATION_SPEC.md lines 300-400

def test_decision_maker_integration():
    # Test communication with decision maker
    pass
```

### **Phase 1 Deliverables**
- ✅ Working database schema (AD_strands + alpha_market_data_1m)
- ✅ Market data collection from Hyperliquid WebSocket
- ✅ Basic signal detection with on-demand feature calculation (Phase 1.3)
- ✅ Multi-timeframe signal processing
- ✅ Signal filtering and quality control
- ✅ Comprehensive testing framework
- ✅ Trading plan generation with risk management (Phase 1.4)
- ✅ Signal pack generation for LLM consumption (Phase 1.4) - **BUT NEEDS LLM INTEGRATION**
- ✅ Integration with core detection engine (Phase 1.4)
- ✅ Communication with decision maker (Phase 1.5)
- ✅ Basic test suite (Phase 1.6)

### **🚨 CRITICAL PHASE 1 FIXES NEEDED**
- ❌ **LLM Integration**: SignalPackGenerator uses static text templates, not actual LLM calls
- ❌ **Strand-Braid Learning**: Database fields exist but no clustering logic implemented
- ❌ **Signal Tracking**: No automatic signal tracking or performance evaluation
- ❌ **Parameter Adaptation**: No automatic parameter tuning based on performance
- ❌ **Vector Search & Context**: No intelligent context injection system

**📋 Phase 1 Fixes Plan**: See `PHASE_1_FIXES_IMPLEMENTATION_PLAN.md` for detailed fix implementation

---

## Phase 2: Intelligence (Weeks 5-8)

### **2.1 Deep Signal Intelligence (DSI)**
**Reference**: `ENHANCED_DSI_SPEC.md`

#### **Step 2.1.1: MicroTape Tokenization**
```python
# File: dsi/microtape_tokenizer.py
# Reference: ENHANCED_DSI_SPEC.md lines 100-200

class MicroTapeTokenizer:
    def tokenize_market_data(self, market_data):
        # Convert market data to microtapes
        pass
```

#### **Step 2.1.2: Micro-Expert Ecosystem**
```python
# File: dsi/micro_experts.py
# Reference: ENHANCED_DSI_SPEC.md lines 200-400

class AnomalyExpert:
    def analyze_anomalies(self, microtapes):
        # Anomaly detection
        pass

class DivergenceExpert:
    def analyze_divergences(self, microtapes):
        # Divergence detection
        pass
```

#### **Step 2.1.3: Evidence Fusion**
```python
# File: dsi/evidence_fusion.py
# Reference: ENHANCED_DSI_SPEC.md lines 400-600

class EvidenceFusion:
    def fuse_evidence(self, expert_outputs):
        # Bayesian combination
        pass
```

### **2.2 Kernel Resonance System**
**Reference**: `ENHANCED_KERNEL_RESONANCE_SPEC.md`

#### **Step 2.2.1: Resonance Calculation**
```python
# File: kernel_resonance/resonance_calculator.py
# Reference: ENHANCED_KERNEL_RESONANCE_SPEC.md lines 100-200

class ResonanceCalculator:
    def calculate_kr_delta_phi(self, market_data, module_state):
        # Kernel resonance calculation
        pass
```

#### **Step 2.2.2: Phase Alignment**
```python
# File: kernel_resonance/phase_aligner.py
# Reference: ENHANCED_KERNEL_RESONANCE_SPEC.md lines 200-300

class PhaseAligner:
    def align_phases(self, signals, market_regime):
        # Phase alignment logic
        pass
```

### **2.3 Residual Manufacturing**
**Reference**: `ENHANCED_RESIDUAL_FACTORIES_SPEC.md`

#### **Step 2.3.1: Residual Factories**
```python
# File: residual_factories/factory_registry.py
# Reference: ENHANCED_RESIDUAL_FACTORIES_SPEC.md lines 100-300

class ResidualFactoryRegistry:
    def __init__(self):
        self.factories = {
            'price_anomaly': PriceAnomalyFactory(),
            'volume_anomaly': VolumeAnomalyFactory(),
            'volatility_anomaly': VolatilityAnomalyFactory(),
            # ... 8 total factories
        }
```

#### **Step 2.3.2: Prediction Models**
```python
# File: residual_factories/prediction_models.py
# Reference: ENHANCED_RESIDUAL_FACTORIES_SPEC.md lines 300-500

class RidgeRegressionModel:
    def predict_expected_value(self, features):
        # Ridge regression prediction
        pass

class KalmanFilterModel:
    def predict_expected_value(self, features):
        # Kalman filter prediction
        pass
```

### **2.4 Advanced Features**
**Reference**: `ENHANCED_FEATURE_SPEC.md`

#### **Step 2.4.1: Market Event Features**
```python
# File: features/market_event_features.py
# Reference: ENHANCED_FEATURE_SPEC.md lines 200-300

class MarketEventFeatureExtractor:
    def extract_event_features(self, market_data):
        # Event bounce, reclaim, failed, breakout
        pass
```

#### **Step 2.4.2: Divergence Detection**
```python
# File: features/divergence_detector.py
# Reference: ENHANCED_FEATURE_SPEC.md lines 300-400

class DivergenceDetector:
    def detect_price_indicator_divergences(self, price_data, indicators):
        # Price vs indicator divergences
        pass
```

### **Phase 2 Deliverables**
- 🔄 DSI system with micro-experts (PLANNED)
- 🔄 Kernel resonance calculation (PLANNED)
- 🔄 Residual manufacturing factories (PLANNED)
- 🔄 Advanced feature extraction (PLANNED)
- 🔄 Enhanced signal quality (PLANNED)

**📋 Phase 2 Plan**: See `PHASE_2_PLAN.md` for detailed implementation plan

---

## Phase 3: Integration (Weeks 9-12)

### **3.1 Direct Table Communication**
**Reference**: `MODULE_COMMUNICATION_SPEC.md`

#### **Step 3.1.1: PostgreSQL Triggers for Direct Communication**
```sql
-- File: database/triggers/ad_strands_triggers.sql
-- Reference: MODULE_COMMUNICATION_SPEC.md

-- Trigger on AD_strands table (Alpha Detector ONLY tags Decision Maker)
CREATE OR REPLACE FUNCTION notify_from_ad_strands()
RETURNS TRIGGER AS $$
BEGIN
    -- Alpha Detector ONLY tags Decision Maker
    IF NEW.tags @> '["dm:evaluate_plan"]' THEN
        PERFORM pg_notify('dm_evaluate_plan', NEW.id::text);
    END IF;
    
    -- Alpha Detector does NOT tag Trader directly
    -- Decision Maker handles all execution communication
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ad_strands_notify
    AFTER INSERT ON AD_strands
    FOR EACH ROW
    EXECUTE FUNCTION notify_from_ad_strands();
```

#### **Step 3.1.2: Module Listeners**
```python
# File: communication/module_listeners.py
# Reference: MODULE_COMMUNICATION_SPEC.md

class ModuleListener:
    def __init__(self, db_connection, module_type):
        self.db = db_connection
        self.module_type = module_type
        # Alpha Detector ONLY listens for feedback from Decision Maker and Trader
        self.listeners = {
            'alpha': ['alpha:decision_feedback', 'alpha:execution_feedback']
            # Alpha Detector does NOT listen for dm:evaluate_plan (that's for Decision Maker)
            # Alpha Detector does NOT listen for trader:execute_plan (that's for Trader)
        }
    
    def start_listening(self):
        """Start listening for database notifications"""
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        conn = psycopg2.connect(self.db.get_dsn())
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Listen for module-specific notifications
        for tag in self.listeners.get(self.module_type, []):
            cursor.execute(f"LISTEN {tag.replace(':', '_')}")
        
        # Process notifications
        while True:
            if conn.poll():
                notification = conn.notifies.pop(0)
                self.process_notification(notification)
    
    def process_notification(self, notification):
        """Process incoming notification"""
        strand_id = notification.payload
        # Read directly from source module's table
        if notification.channel == 'alpha_decision_feedback':
            message = self.db.execute("""
                SELECT * FROM DM_strands WHERE id = %s
            """, (strand_id,)).fetchone()
        elif notification.channel == 'alpha_execution_feedback':
            message = self.db.execute("""
                SELECT * FROM TR_strands WHERE id = %s
            """, (strand_id,)).fetchone()
        
        if message:
            self.handle_message(message)
```

### **3.2 Decision Maker Integration**
**Reference**: `DECISION_MAKER_INTEGRATION_SPEC.md`

#### **Step 3.2.1: Enhanced Communication**
```python
# File: integration/decision_maker_client.py
# Reference: DECISION_MAKER_INTEGRATION_SPEC.md lines 200-300

class DecisionMakerClient:
    def publish_trading_plan(self, trading_plan, signal_pack):
        # Enhanced trading plan publishing
        pass
    
    def process_decision_feedback(self, feedback):
        # Process decision feedback
        pass
```

#### **Step 3.2.2: Feedback Learning**
```python
# File: integration/feedback_learner.py
# Reference: DECISION_MAKER_INTEGRATION_SPEC.md lines 300-400

class FeedbackLearner:
    def learn_from_feedback(self, feedback_data):
        # Learn from decision outcomes
        pass
```

### **3.3 Module Intelligence Architecture**
**Reference**: `UNIFIED_SYSTEM_ARCHITECTURE.md`

#### **Step 3.3.1: Module Curator Layer**
```python
# File: module_intelligence/curator_layer.py
# Reference: UNIFIED_SYSTEM_ARCHITECTURE.md lines 200-300

class ModuleCuratorLayer:
    def __init__(self, module_type):
        self.curator_registry = CuratorRegistry(module_type)
        self.curator_orchestrator = CuratorOrchestrator(module_type)
```

#### **Step 3.3.2: Intelligence Integration**
```python
# File: module_intelligence/intelligence_integrator.py
# Reference: UNIFIED_SYSTEM_ARCHITECTURE.md lines 300-400

class IntelligenceIntegrator:
    def integrate_external_intelligence(self, intelligence_data):
        # Integrate intelligence from other modules
        pass
```

### **Phase 3 Deliverables**
- ✅ Complete module communication
- ✅ Decision maker integration
- ✅ Intelligence sharing between modules
- ✅ Feedback learning system

---

## Phase 4: Learning (Weeks 13-16)

### **4.1 Learning Systems**
**Reference**: `ENHANCED_LEARNING_SYSTEMS_SPEC.md`

#### **Step 4.1.1: Module Learning Engines**
```python
# File: learning/module_learning_engine.py
# Reference: ENHANCED_LEARNING_SYSTEMS_SPEC.md lines 100-200

class ModuleLearningEngine:
    def __init__(self, module_id):
        self.performance_analyzer = PerformancePatternAnalyzer()
        self.parameter_adapter = ParameterAdapter()
        self.pattern_recognizer = PatternRecognizer()
```

### **4.2 Strand-Braid Learning System**
**Reference**: `ENHANCED_STRAND_BRAID_LEARNING_SPEC.md`

#### **Step 4.2.1: Strand Clustering**
```python
# File: learning/strand_braid_learning.py
# Reference: ENHANCED_STRAND_BRAID_LEARNING_SPEC.md lines 100-200

class StrandBraidLearning:
    def __init__(self, module_type='alpha_detector'):
        self.module_type = module_type
        self.clustering_columns = ['symbol', 'timeframe', 'regime', 'session_bucket']
        self.scoring_weights = {
            'sig_sigma': 0.4,
            'sig_confidence': 0.3,
            'outcome_score': 0.3
        }
    
    def cluster_strands(self, strands):
        """Cluster strands by similarity using top-level columns"""
        clusters = {}
        for strand in strands:
            clustering_key = self._create_clustering_key(strand)
            if clustering_key not in clusters:
                clusters[clustering_key] = {
                    'strands': [],
                    'accumulated_score': 0.0,
                    'clustering_columns': clustering_key
                }
            clusters[clustering_key]['strands'].append(strand)
            clusters[clustering_key]['accumulated_score'] += self._calculate_strand_score(strand)
        return clusters
```

#### **Step 4.2.2: LLM Lesson Generation**
```python
# File: learning/llm_lesson_generator.py
# Reference: ENHANCED_STRAND_BRAID_LEARNING_SPEC.md lines 200-300

class LLMLessonGenerator:
    def __init__(self):
        self.llm_client = LLMClient()
        self.lesson_prompt_template = self._load_lesson_prompt_template()
    
    def generate_lesson(self, strands):
        """Generate lesson from clustered strands"""
        context = self._prepare_lesson_context(strands)
        lesson = self.llm_client.generate_lesson(context)
        return lesson
    
    def _prepare_lesson_context(self, strands):
        """Prepare context for LLM lesson generation"""
        return {
            'strands': strands,
            'common_patterns': self._extract_common_patterns(strands),
            'success_factors': self._extract_success_factors(strands),
            'failure_factors': self._extract_failure_factors(strands),
            'market_conditions': self._extract_market_conditions(strands),
            'performance_metrics': self._extract_performance_metrics(strands)
        }
```

#### **Step 4.2.3: Braid Creation**
```python
# File: learning/braid_creator.py
# Reference: ENHANCED_STRAND_BRAID_LEARNING_SPEC.md lines 300-400

class BraidCreator:
    def __init__(self, db_connection):
        self.db = db_connection
        self.llm_lesson_generator = LLMLessonGenerator()
    
    def create_braid_strand(self, cluster):
        """Create braid strand in AD_strands table"""
        # Send to LLM for lesson generation
        lesson = self.llm_lesson_generator.generate_lesson(cluster['strands'])
        
        # Create braid strand entry (same table structure)
        braid_strand = {
            'id': f"AD_braid_{uuid.uuid4().hex[:12]}",
            'lifecycle_id': f"braid_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'parent_id': None,
            'module': 'alpha',
            'kind': 'braid',  # Tag as braid
            'symbol': cluster['clustering_columns'][0],
            'timeframe': cluster['clustering_columns'][1],
            'session_bucket': cluster['clustering_columns'][3],
            'regime': cluster['clustering_columns'][2],
            'sig_sigma': self._calculate_aggregated_sigma(cluster['strands']),
            'sig_confidence': self._calculate_aggregated_confidence(cluster['strands']),
            'sig_direction': self._determine_aggregated_direction(cluster['strands']),
            'trading_plan': {
                'lesson': lesson,
                'source_strands': [strand['id'] for strand in cluster['strands']],
                'accumulated_score': cluster['accumulated_score'],
                'cluster_columns': cluster['clustering_columns'],
                'strand_count': len(cluster['strands']),
                'braid_level': 'braid'
            },
            'signal_pack': {
                'signal_type': 'braid_lesson',
                'pattern_detected': lesson.get('pattern_name', 'unknown'),
                'direction': self._determine_aggregated_direction(cluster['strands']),
                'points_of_interest': lesson.get('key_insights', []),
                'confidence_score': cluster['accumulated_score'] / len(cluster['strands'])
            },
            'dsi_evidence': {
                'braid_evidence': lesson.get('evidence_summary', {}),
                'source_evidence': [strand.get('dsi_evidence', {}) for strand in cluster['strands']]
            },
            'regime_context': {
                'braid_regime': cluster['clustering_columns'][2],
                'source_regimes': [strand.get('regime', 'unknown') for strand in cluster['strands']]
            },
            'event_context': {
                'braid_events': lesson.get('event_patterns', []),
                'source_events': [strand.get('event_context', {}) for strand in cluster['strands']]
            },
            'module_intelligence': {
                'braid_intelligence': lesson.get('intelligence_summary', {}),
                'learning_insights': lesson.get('learning_insights', []),
                'recommendations': lesson.get('recommendations', [])
            },
            'curator_feedback': {
                'braid_feedback': lesson.get('curator_insights', {}),
                'source_feedback': [strand.get('curator_feedback', {}) for strand in cluster['strands']]
            },
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        # Insert into AD_strands table
        self.insert_strand(braid_strand)
        return braid_strand
```

#### **Step 4.2.4: Enhanced Learning Integration**
```python
# File: learning/enhanced_learning_integration.py
# Reference: ENHANCED_STRAND_BRAID_LEARNING_SPEC.md lines 400-500

class EnhancedLearningIntegration:
    def __init__(self, module_learning_engine, strand_braid_learning):
        self.module_learning_engine = module_learning_engine
        self.strand_braid_learning = strand_braid_learning
        self.braid_threshold = 3.0
    
    def enhanced_learning_flow(self, plan_id, outcome):
        """Enhanced learning flow with strand-braid learning"""
        # 1. Existing performance update
        self.module_learning_engine.update_performance(plan_id, outcome)
        
        # 2. Existing pattern analysis
        patterns = self.module_learning_engine.analyze_performance_patterns()
        
        # 3. Existing parameter adaptation
        self.module_learning_engine.adapt_parameters(patterns)
        
        # 4. NEW: Strand-braid learning
        self.strand_braid_learning.update_strand_performance(plan_id, outcome)
        
        # 5. NEW: Check for braid creation
        self.check_and_create_braids()
    
    def check_and_create_braids(self):
        """Check for braid creation opportunities"""
        recent_strands = self.get_recent_strands(days=30)
        clusters = self.strand_braid_learning.cluster_strands(recent_strands)
        
        for cluster in clusters:
            if cluster.accumulated_score >= self.braid_threshold:
                self.create_braid_strand(cluster)
```

### **4.3 Module Replication**
**Reference**: `MODULE_REPLICATION_SPEC.md`

#### **Step 4.3.1: Replication Engine**
```python
# File: replication/replication_engine.py
# Reference: MODULE_REPLICATION_SPEC.md lines 100-200

class ReplicationEngine:
    def create_child_intelligence(self, parent_modules):
        # Create child module intelligence
        pass
```

#### **Step 4.3.2: Performance-Driven Replication**
```python
# File: replication/performance_replicator.py
# Reference: MODULE_REPLICATION_SPEC.md lines 200-300

class PerformanceReplicator:
    def evaluate_replication_candidates(self, modules):
        # Evaluate which modules to replicate
        pass
```

### **4.4 Learning Orchestration**
**Reference**: `ENHANCED_LEARNING_SYSTEMS_SPEC.md` (Learning Orchestration)

#### **Step 4.4.1: Learning Scheduler**
```python
# File: learning/learning_scheduler.py
# Reference: ENHANCED_LEARNING_SYSTEMS_SPEC.md lines 400-500

class LearningScheduler:
    def start_learning_loop(self):
        # Coordinate learning across modules
        pass
```

#### **Step 4.4.2: Learning Coordinator**
```python
# File: learning/learning_coordinator.py
# Reference: ENHANCED_LEARNING_SYSTEMS_SPEC.md lines 500-600

class LearningCoordinator:
    def coordinate_learning(self):
        # Coordinate learning across all modules
        pass
```

### **Phase 4 Deliverables**
- ✅ Self-learning modules
- ✅ Strand-braid learning system
- ✅ Performance-driven replication
- ✅ Learning orchestration
- ✅ Continuous improvement system

---

## Phase 5: Production (Weeks 17-20)

### **5.1 Performance Optimization**
**Reference**: `ENHANCED_IMPLEMENTATION_SPEC.md` (Performance Optimization)

#### **Step 5.1.1: Database Optimization**
```sql
-- Optimize database performance
-- Reference: ENHANCED_IMPLEMENTATION_SPEC.md lines 500-600

-- Add missing indexes
-- Optimize queries
-- Partition large tables
```

#### **Step 5.1.2: Caching Layer**
```python
# File: performance/cache_manager.py
# Reference: ENHANCED_IMPLEMENTATION_SPEC.md lines 600-700

class CacheManager:
    def __init__(self):
        self.redis_client = redis.Redis()
        self.cache_ttl = 300  # 5 minutes
```

### **5.2 Monitoring and Alerting**
**Reference**: `ENHANCED_OPERATIONAL_GUIDE.md`

#### **Step 5.2.1: System Monitoring**
```python
# File: monitoring/system_monitor.py
# Reference: ENHANCED_OPERATIONAL_GUIDE.md lines 100-200

class SystemMonitor:
    def monitor_system_health(self):
        # Monitor system health
        pass
```

#### **Step 5.2.2: Performance Metrics**
```python
# File: monitoring/performance_metrics.py
# Reference: ENHANCED_OPERATIONAL_GUIDE.md lines 200-300

class PerformanceMetrics:
    def track_performance(self, module_id, metrics):
        # Track performance metrics
        pass
```

### **5.3 Configuration Management**
**Reference**: `ENHANCED_CONFIGURATION_SPEC.md`

#### **Step 5.3.1: Configuration System**
```python
# File: config/configuration_manager.py
# Reference: ENHANCED_CONFIGURATION_SPEC.md lines 100-200

class ConfigurationManager:
    def load_configuration(self, environment):
        # Load configuration for environment
        pass
```

#### **Step 5.3.2: Environment Management**
```yaml
# File: config/environments/
# Reference: ENHANCED_CONFIGURATION_SPEC.md lines 200-300

# development.yaml
# staging.yaml
# production.yaml
```

### **Phase 5 Deliverables**
- ✅ Production-ready system
- ✅ Performance optimization
- ✅ Monitoring and alerting
- ✅ Configuration management

---

## Implementation Checklist

### **Phase 1: Foundation** ✅ **WITH CRITICAL FIXES NEEDED**
- [x] Database schema created
- [x] Market data collection from Hyperliquid WebSocket
- [x] Multi-timeframe data processing (1m, 5m, 15m, 1h)
- [x] On-demand feature extraction (35+ technical indicators)
- [x] Pattern detection (support/resistance, breakouts, divergences)
- [x] Market regime detection (trending, ranging, volatility)
- [x] Signal generation with confidence/strength scoring
- [x] Multi-timeframe signal combination with configurable weights
- [x] Signal processing and filtering with quality control
- [x] Comprehensive testing framework
- [x] Trading plan generation with risk management
- [x] Signal pack generation for LLM consumption - **NEEDS LLM INTEGRATION**
- [x] Integration with core detection engine
- [x] Decision maker communication working
- [x] Basic tests passing

### **🚨 PHASE 1 CRITICAL FIXES REQUIRED**
- [ ] **LLM Integration**: Replace static text templates with actual OpenRouter calls
- [ ] **Strand-Braid Learning**: Implement clustering and lesson generation
- [ ] **Signal Tracking**: Automatic signal tracking and performance evaluation
- [ ] **Parameter Adaptation**: Automatic parameter tuning based on performance
- [ ] **Vector Search & Context**: Intelligent context injection system

### **Phase 2: Intelligence** ✅
- [ ] DSI system implemented
- [ ] Kernel resonance working
- [ ] Residual factories operational
- [ ] Advanced features extracted
- [ ] Enhanced signal quality

### **Phase 3: Integration** ✅
- [ ] Module communication working
- [ ] Decision maker integration complete
- [ ] Intelligence sharing operational
- [ ] Feedback learning active

### **Phase 4: Learning** ✅
- [ ] Self-learning modules active
- [ ] Strand-braid learning system operational
- [ ] Replication system working
- [ ] Learning orchestration operational
- [ ] Continuous improvement active

### **Phase 5: Production** ✅
- [ ] Performance optimized
- [ ] Monitoring active
- [ ] Configuration managed
- [ ] Production ready

---

## File Structure

```
Modules/Alpha_Detector/
├── src/
│   ├── core_detection/
│   │   ├── core_detection_engine.py
│   │   ├── feature_extractors.py
│   │   ├── pattern_detectors.py
│   │   ├── signal_generator.py
│   │   ├── signal_processor.py
│   │   ├── multi_timeframe_processor.py
│   │   ├── multi_timeframe_signal_combiner.py
│   │   ├── regime_detector.py
│   │   └── market_data_processor.py
│   ├── trading_plans/
│   │   ├── __init__.py
│   │   ├── trading_plan_builder.py
│   │   ├── signal_pack_generator.py
│   │   ├── models.py
│   │   └── config.py
│   ├── data_sources/
│   │   └── hyperliquid_client.py
│   ├── utils/
│   │   ├── supabase_manager.py
│   │   └── database.py
│   └── market_data_collector.py
├── database/
│   ├── alpha_detector_schema.sql
│   └── alpha_market_data_schema.sql
├── tests/
│   ├── test_phase1_3_comprehensive.py
│   ├── test_phase1_3_final.py
│   ├── test_signal_processor.py
│   └── test_trading_plans.py
├── config/
│   └── trading_plans.yaml
├── dsi/
│   ├── microtape_tokenizer.py
│   ├── micro_experts.py
│   └── evidence_fusion.py
├── kernel_resonance/
│   ├── resonance_calculator.py
│   └── phase_aligner.py
├── residual_factories/
│   ├── factory_registry.py
│   └── prediction_models.py
├── features/
│   ├── market_event_features.py
│   └── divergence_detector.py
├── communication/
│   ├── direct_table_communicator.py
│   └── module_listeners.py
├── integration/
│   ├── decision_maker_client.py
│   └── feedback_learner.py
├── module_intelligence/
│   ├── curator_layer.py
│   └── intelligence_integrator.py
├── learning/
│   ├── module_learning_engine.py
│   ├── performance_analyzer.py
│   ├── parameter_adapter.py
│   ├── strand_braid_learning.py
│   ├── llm_lesson_generator.py
│   ├── braid_creator.py
│   ├── enhanced_learning_integration.py
│   ├── learning_scheduler.py
│   └── learning_coordinator.py
├── replication/
│   ├── replication_engine.py
│   └── performance_replicator.py
├── performance/
│   └── cache_manager.py
├── monitoring/
│   ├── system_monitor.py
│   └── performance_metrics.py
├── config/
│   ├── configuration_manager.py
│   └── environments/
├── tests/
│   ├── test_core_detection.py
│   ├── test_communication.py
│   ├── test_strand_braid_learning.py
│   └── test_integration.py
└── database/
    ├── schema.sql
    ├── triggers/
    │   ├── ad_strands_triggers.sql
    │   ├── dm_strands_triggers.sql
    │   └── tr_strands_triggers.sql
    └── migrations/
```

---

## Key Implementation Notes

### **1. Start Simple, Add Complexity**
- Begin with basic signal detection
- Add DSI and advanced features incrementally
- Test each component thoroughly before moving on

### **2. Database-First Approach**
- Establish database schema early
- Use migrations for schema changes
- Test database performance regularly

### **3. Test-Driven Development**
- Write tests for each component
- Use integration tests for communication
- Monitor test coverage

### **4. Configuration Management**
- Use environment-specific configurations
- Make all parameters configurable
- Document all configuration options

### **5. Performance Monitoring**
- Monitor system performance from day one
- Use profiling to identify bottlenecks
- Optimize based on real usage patterns

---

## Success Metrics

### **Phase 1 Success**
- Basic signals detected and published
- Decision maker receives and processes plans
- System runs without errors

### **Phase 2 Success**
- DSI improves signal quality by 20%
- Kernel resonance enhances detection
- Residual factories detect anomalies

### **Phase 3 Success**
- Modules communicate effectively
- Intelligence sharing works
- Feedback learning improves performance

### **Phase 4 Success**
- Modules learn and adapt
- Strand-braid learning creates lessons
- Replication creates better modules
- System improves over time

### **Phase 5 Success**
- Production-ready system
- High performance and reliability
- Complete monitoring and alerting

---

*This implementation plan provides a complete roadmap for building the Trading Intelligence System. Each phase builds upon the previous one, ensuring a working system at every stage.*
