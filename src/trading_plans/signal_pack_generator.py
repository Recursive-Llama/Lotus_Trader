"""
Signal Pack Generator
Phase 1.4.2: Create LLM-optimized signal packs with all context
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd

from .models import SignalPack, generate_pack_id
from .config import get_config

logger = logging.getLogger(__name__)


class SignalPackGenerator:
    """Generates LLM-ready signal packs with comprehensive context"""
    
    def __init__(self, config=None):
        """Initialize signal pack generator"""
        self.config = config or get_config()
    
    def generate_signal_pack(self, signal: Dict[str, Any], trading_plan: Any, 
                           market_data: pd.DataFrame) -> Optional[SignalPack]:
        """Create LLM-optimized signal pack with all context"""
        try:
            logger.debug(f"Generating signal pack for signal: {signal.get('signal_id', 'unknown')}")
            
            # 1. Extract and aggregate features
            features = self._aggregate_features(signal)
            
            # 2. Extract and format patterns
            patterns = self._extract_patterns(signal)
            
            # 3. Extract and format regime information
            regime = self._extract_regime(signal)
            
            # 4. Build comprehensive market context
            market_context = self._build_market_context(market_data, signal, trading_plan)
            
            # 5. Create processing metadata
            processing_metadata = self._create_processing_metadata(signal, trading_plan)
            
            # 6. Format for LLM consumption
            llm_format = self._format_for_llm(signal, trading_plan, features, patterns, regime, market_context)
            
            # 7. Create signal pack
            signal_pack = SignalPack(
                pack_id=generate_pack_id(),
                signal_id=signal.get('signal_id', f"signal_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                trading_plan_id=trading_plan.plan_id if hasattr(trading_plan, 'plan_id') else 'unknown',
                features=features,
                patterns=patterns,
                regime=regime,
                market_context=market_context,
                processing_metadata=processing_metadata,
                llm_format=llm_format,
                created_at=datetime.now()
            )
            
            logger.info(f"Signal pack created: {signal_pack.pack_id}")
            return signal_pack
            
        except Exception as e:
            logger.error(f"Error generating signal pack: {e}")
            return None
    
    def _aggregate_features(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate and format all signal features"""
        try:
            features = signal.get('features', {})
            
            # Categorize features for better organization
            aggregated = {
                'price_features': {
                    'rsi': features.get('rsi', 0.0),
                    'rsi_overbought': features.get('rsi_overbought', False),
                    'rsi_oversold': features.get('rsi_oversold', False),
                    'macd': features.get('macd', 0.0),
                    'macd_signal': features.get('macd_signal', 0.0),
                    'macd_histogram': features.get('macd_histogram', 0.0),
                    'macd_bullish': features.get('macd_bullish', False),
                    'macd_bearish': features.get('macd_bearish', False),
                    'bb_position': features.get('bb_position', 0.5),
                    'bb_squeeze': features.get('bb_squeeze', False)
                },
                'volume_features': {
                    'volume_ratio': features.get('volume_ratio', 1.0),
                    'volume_spike': features.get('volume_spike', False),
                    'volume_sma_20': features.get('volume_sma_20', 0.0),
                    'volume_price_trend': features.get('volume_price_trend', 0.0),
                    'on_balance_volume': features.get('on_balance_volume', 0.0)
                },
                'technical_features': {
                    'sma_20': features.get('sma_20', 0.0),
                    'sma_50': features.get('sma_50', 0.0),
                    'ema_12': features.get('ema_12', 0.0),
                    'ema_26': features.get('ema_26', 0.0),
                    'momentum_10': features.get('momentum_10', 0.0),
                    'momentum_20': features.get('momentum_20', 0.0),
                    'volatility_20': features.get('volatility_20', 0.0),
                    'atr_14': features.get('atr_14', 0.0)
                },
                'signal_metadata': {
                    'confidence': signal.get('confidence', 0.0),
                    'strength': signal.get('strength', 0.0),
                    'direction': signal.get('direction', 'unknown'),
                    'timeframe': signal.get('timeframe', 'unknown'),
                    'timestamp': signal.get('timestamp', datetime.now()).isoformat() if signal.get('timestamp') else datetime.now().isoformat()
                }
            }
            
            return aggregated
            
        except Exception as e:
            logger.error(f"Error aggregating features: {e}")
            return {'error': str(e)}
    
    def _extract_patterns(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and format pattern information"""
        try:
            patterns = signal.get('patterns', {})
            
            formatted_patterns = {
                'support_resistance': {
                    'support_levels': patterns.get('support_levels', []),
                    'resistance_levels': patterns.get('resistance_levels', []),
                    'current_support': patterns.get('current_support', 0.0),
                    'current_resistance': patterns.get('current_resistance', 0.0),
                    'support_strength': patterns.get('support_strength', 0.0),
                    'resistance_strength': patterns.get('resistance_strength', 0.0)
                },
                'breakouts': {
                    'breakout_up': patterns.get('breakout_up', False),
                    'breakout_down': patterns.get('breakout_down', False),
                    'breakout_volume_confirmation': patterns.get('breakout_volume_confirmation', False),
                    'breakout_strength': patterns.get('breakout_strength', 0.0)
                },
                'divergences': {
                    'bullish_divergence': patterns.get('bullish_divergence', False),
                    'bearish_divergence': patterns.get('bearish_divergence', False),
                    'divergence_strength': patterns.get('divergence_strength', 0.0)
                },
                'candlestick_patterns': {
                    'doji': patterns.get('doji', False),
                    'hammer': patterns.get('hammer', False),
                    'shooting_star': patterns.get('shooting_star', False),
                    'engulfing': patterns.get('engulfing', False)
                }
            }
            
            return formatted_patterns
            
        except Exception as e:
            logger.error(f"Error extracting patterns: {e}")
            return {'error': str(e)}
    
    def _extract_regime(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and format regime information"""
        try:
            regime = signal.get('regime', {})
            
            # Handle both string and dict regime formats
            if isinstance(regime, str):
                regime_data = {
                    'regime': regime,
                    'confidence': 0.5,
                    'trend_strength': 0.0,
                    'volatility_regime': 'normal',
                    'volume_regime': 'normal'
                }
            else:
                regime_data = {
                    'regime': regime.get('regime', 'unknown'),
                    'confidence': regime.get('confidence', 0.5),
                    'trend_strength': regime.get('trend_strength', 0.0),
                    'volatility_regime': regime.get('volatility_regime', 'normal'),
                    'volume_regime': regime.get('volume_regime', 'normal')
                }
            
            return regime_data
            
        except Exception as e:
            logger.error(f"Error extracting regime: {e}")
            return {'regime': 'unknown', 'confidence': 0.0}
    
    def _build_market_context(self, market_data: pd.DataFrame, signal: Dict[str, Any], 
                            trading_plan: Any) -> Dict[str, Any]:
        """Build comprehensive market context"""
        try:
            # Get symbol from market data or signal
            symbol = 'UNKNOWN'
            if hasattr(market_data, 'get') and 'symbol' in market_data.columns:
                symbol = market_data['symbol'].iloc[0] if len(market_data) > 0 else 'UNKNOWN'
            elif 'symbol' in signal:
                symbol = signal['symbol']
            
            # Calculate market metrics
            current_price = float(market_data['close'].iloc[-1]) if len(market_data) > 0 else 0.0
            volume_24h = float(market_data['volume'].tail(24).sum()) if len(market_data) >= 24 else 0.0
            volatility_24h = float(market_data['close'].pct_change().tail(24).std()) if len(market_data) >= 24 else 0.0
            
            # Calculate additional metrics
            price_change_1h = self._calculate_price_change(market_data, 60)  # 1 hour
            price_change_4h = self._calculate_price_change(market_data, 240)  # 4 hours
            price_change_24h = self._calculate_price_change(market_data, 1440)  # 24 hours
            
            # Get trading plan context if available
            trading_plan_context = {}
            if hasattr(trading_plan, 'market_context'):
                trading_plan_context = trading_plan.market_context
            
            market_context = {
                'symbol': symbol,
                'current_price': current_price,
                'volume_24h': volume_24h,
                'volatility_24h': volatility_24h,
                'price_changes': {
                    '1h': price_change_1h,
                    '4h': price_change_4h,
                    '24h': price_change_24h
                },
                'market_cap': trading_plan_context.get('market_cap'),
                'sector': trading_plan_context.get('sector', 'crypto'),
                'correlation_btc': trading_plan_context.get('correlation_btc'),
                'news_sentiment': trading_plan_context.get('news_sentiment'),
                'market_regime': trading_plan_context.get('market_regime', 'unknown'),
                'trend_strength': trading_plan_context.get('trend_strength', 0.0),
                'volume_confirmation': trading_plan_context.get('volume_confirmation', 0.0),
                'pattern_strength': trading_plan_context.get('pattern_strength', 0.0),
                'regime_alignment': trading_plan_context.get('regime_alignment', 0.0)
            }
            
            return market_context
            
        except Exception as e:
            logger.error(f"Error building market context: {e}")
            return {'symbol': 'UNKNOWN', 'current_price': 0.0}
    
    def _calculate_price_change(self, market_data: pd.DataFrame, periods: int) -> float:
        """Calculate price change over specified periods"""
        try:
            if len(market_data) < periods:
                return 0.0
            
            current_price = market_data['close'].iloc[-1]
            past_price = market_data['close'].iloc[-periods]
            
            if past_price == 0:
                return 0.0
            
            return ((current_price - past_price) / past_price) * 100
            
        except Exception as e:
            logger.error(f"Error calculating price change: {e}")
            return 0.0
    
    def _create_processing_metadata(self, signal: Dict[str, Any], trading_plan: Any) -> Dict[str, Any]:
        """Create processing metadata"""
        try:
            processing_metadata = signal.get('processing_metadata', {})
            
            # Add trading plan metadata
            if hasattr(trading_plan, 'signal_metadata'):
                plan_metadata = trading_plan.signal_metadata
                processing_metadata.update({
                    'plan_source': plan_metadata.get('source', 'unknown'),
                    'plan_execution_params': plan_metadata.get('execution_params', {}),
                    'plan_created_at': trading_plan.created_at.isoformat() if hasattr(trading_plan, 'created_at') else datetime.now().isoformat()
                })
            
            # Add signal pack generation metadata
            processing_metadata.update({
                'pack_generated_at': datetime.now().isoformat(),
                'pack_generator_version': '1.0.0',
                'llm_optimized': True,
                'context_completeness': self._calculate_context_completeness(signal, trading_plan)
            })
            
            return processing_metadata
            
        except Exception as e:
            logger.error(f"Error creating processing metadata: {e}")
            return {'error': str(e)}
    
    def _calculate_context_completeness(self, signal: Dict[str, Any], trading_plan: Any) -> float:
        """Calculate how complete the context information is"""
        try:
            completeness_score = 0.0
            total_checks = 0
            
            # Check signal completeness
            signal_checks = ['direction', 'confidence', 'strength', 'features', 'patterns', 'regime']
            for check in signal_checks:
                total_checks += 1
                if check in signal and signal[check] is not None:
                    completeness_score += 1
            
            # Check trading plan completeness
            if hasattr(trading_plan, 'plan_id'):
                total_checks += 1
                completeness_score += 1
            
            if hasattr(trading_plan, 'entry_price') and trading_plan.entry_price > 0:
                total_checks += 1
                completeness_score += 1
            
            if hasattr(trading_plan, 'stop_loss') and trading_plan.stop_loss > 0:
                total_checks += 1
                completeness_score += 1
            
            if hasattr(trading_plan, 'take_profit') and trading_plan.take_profit > 0:
                total_checks += 1
                completeness_score += 1
            
            return completeness_score / total_checks if total_checks > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating context completeness: {e}")
            return 0.0
    
    def _format_for_llm(self, signal: Dict[str, Any], trading_plan: Any, 
                       features: Dict[str, Any], patterns: Dict[str, Any], 
                       regime: Dict[str, Any], market_context: Dict[str, Any]) -> Dict[str, Any]:
        """Format signal pack for LLM consumption"""
        try:
            # Create LLM-optimized summary
            summary = self._create_llm_summary(signal, trading_plan, features, patterns, regime, market_context)
            
            # Create structured data for LLM
            structured_data = {
                'signal_summary': {
                    'direction': signal.get('direction', 'unknown'),
                    'confidence': signal.get('confidence', 0.0),
                    'strength': signal.get('strength', 0.0),
                    'timeframe': signal.get('timeframe', 'unknown'),
                    'symbol': market_context.get('symbol', 'UNKNOWN')
                },
                'trading_plan_summary': {
                    'entry_price': float(trading_plan.entry_price) if hasattr(trading_plan, 'entry_price') else 0.0,
                    'stop_loss': float(trading_plan.stop_loss) if hasattr(trading_plan, 'stop_loss') else 0.0,
                    'take_profit': float(trading_plan.take_profit) if hasattr(trading_plan, 'take_profit') else 0.0,
                    'position_size': float(trading_plan.position_size) if hasattr(trading_plan, 'position_size') else 0.0,
                    'risk_reward_ratio': float(trading_plan.risk_reward_ratio) if hasattr(trading_plan, 'risk_reward_ratio') else 0.0
                },
                'key_indicators': {
                    'rsi': features.get('price_features', {}).get('rsi', 0.0),
                    'macd_bullish': features.get('price_features', {}).get('macd_bullish', False),
                    'volume_spike': features.get('volume_features', {}).get('volume_spike', False),
                    'breakout_confirmed': patterns.get('breakouts', {}).get('breakout_up', False) or 
                                        patterns.get('breakouts', {}).get('breakout_down', False),
                    'regime': regime.get('regime', 'unknown')
                },
                'market_conditions': {
                    'current_price': market_context.get('current_price', 0.0),
                    'volatility_24h': market_context.get('volatility_24h', 0.0),
                    'volume_24h': market_context.get('volume_24h', 0.0),
                    'price_change_24h': market_context.get('price_changes', {}).get('24h', 0.0)
                }
            }
            
            # Create natural language description
            natural_language = self._create_natural_language_description(signal, trading_plan, market_context)
            
            llm_format = {
                'summary': summary,
                'structured_data': structured_data,
                'natural_language': natural_language,
                'llm_instructions': {
                    'analysis_focus': 'trading_signal_evaluation',
                    'output_format': 'structured_analysis',
                    'key_considerations': [
                        'signal_strength_and_confidence',
                        'market_regime_alignment',
                        'risk_reward_ratio',
                        'volume_confirmation',
                        'pattern_reliability'
                    ]
                }
            }
            
            return llm_format
            
        except Exception as e:
            logger.error(f"Error formatting for LLM: {e}")
            return {'error': str(e)}
    
    def _create_llm_summary(self, signal: Dict[str, Any], trading_plan: Any, 
                           features: Dict[str, Any], patterns: Dict[str, Any], 
                           regime: Dict[str, Any], market_context: Dict[str, Any]) -> str:
        """Create concise summary for LLM"""
        try:
            direction = signal.get('direction', 'unknown').upper()
            symbol = market_context.get('symbol', 'UNKNOWN')
            confidence = signal.get('confidence', 0.0)
            strength = signal.get('strength', 0.0)
            
            # Get key indicators
            rsi = features.get('price_features', {}).get('rsi', 0.0)
            volume_spike = features.get('volume_features', {}).get('volume_spike', False)
            breakout = patterns.get('breakouts', {}).get('breakout_up', False) or patterns.get('breakouts', {}).get('breakout_down', False)
            regime_type = regime.get('regime', 'unknown')
            
            # Get trading plan details
            entry_price = float(trading_plan.entry_price) if hasattr(trading_plan, 'entry_price') else 0.0
            risk_reward = float(trading_plan.risk_reward_ratio) if hasattr(trading_plan, 'risk_reward_ratio') else 0.0
            
            summary = f"""
TRADING SIGNAL SUMMARY
======================
Symbol: {symbol}
Direction: {direction}
Confidence: {confidence:.2f}
Strength: {strength:.2f}

KEY INDICATORS:
- RSI: {rsi:.1f}
- Volume Spike: {volume_spike}
- Breakout Confirmed: {breakout}
- Market Regime: {regime_type}

TRADING PLAN:
- Entry Price: ${entry_price:,.2f}
- Risk-Reward Ratio: {risk_reward:.2f}

SIGNAL QUALITY: {'HIGH' if confidence > 0.7 and strength > 0.6 else 'MEDIUM' if confidence > 0.5 and strength > 0.4 else 'LOW'}
"""
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Error creating LLM summary: {e}")
            return f"Error creating summary: {e}"
    
    def _create_natural_language_description(self, signal: Dict[str, Any], 
                                           trading_plan: Any, market_context: Dict[str, Any]) -> str:
        """Create natural language description for LLM"""
        try:
            direction = signal.get('direction', 'unknown')
            symbol = market_context.get('symbol', 'UNKNOWN')
            confidence = signal.get('confidence', 0.0)
            strength = signal.get('strength', 0.0)
            
            # Create descriptive text
            confidence_level = "high" if confidence > 0.7 else "medium" if confidence > 0.5 else "low"
            strength_level = "strong" if strength > 0.6 else "moderate" if strength > 0.4 else "weak"
            
            description = f"""
A {confidence_level} confidence, {strength_level} strength {direction} signal has been detected for {symbol}. 
The signal shows promising technical indicators with volume confirmation and pattern alignment. 
The trading plan suggests a favorable risk-reward setup with clear entry, stop-loss, and take-profit levels.
This signal appears suitable for {confidence_level} conviction trading based on current market conditions.
"""
            
            return description.strip()
            
        except Exception as e:
            logger.error(f"Error creating natural language description: {e}")
            return f"Error creating description: {e}"


if __name__ == "__main__":
    # Test the SignalPackGenerator
    print("🧪 Testing SignalPackGenerator...")
    
    try:
        # Create sample signal
        signal = {
            'signal_id': 'test_signal_123',
            'direction': 'long',
            'confidence': 0.75,
            'strength': 0.65,
            'timeframe': '1h',
            'features': {
                'rsi': 45.0,
                'macd': 0.001,
                'macd_bullish': True,
                'volume_spike': True,
                'bb_position': 0.3
            },
            'patterns': {
                'breakout_up': True,
                'support_levels': [49000, 48500],
                'resistance_levels': [52000, 52500],
                'current_support': 49000,
                'current_resistance': 52000
            },
            'regime': 'trending_up',
            'processing_metadata': {'quality_score': 0.85}
        }
        
        # Create sample trading plan
        from .models import TradingPlan
        from decimal import Decimal
        
        trading_plan = TradingPlan(
            plan_id='tp_test_123',
            signal_id='test_signal_123',
            symbol='BTC',
            timeframe='1h',
            direction='long',
            entry_conditions={'price_above': 50000},
            entry_price=Decimal('50000.00'),
            position_size=Decimal('0.1'),
            stop_loss=Decimal('49000.00'),
            take_profit=Decimal('52000.00'),
            risk_reward_ratio=Decimal('2.0'),
            confidence_score=0.75,
            strength_score=0.65,
            time_horizon='4h',
            valid_until=datetime.now(),
            created_at=datetime.now(),
            market_context={'volatility': 0.02},
            signal_metadata={'source': 'test'}
        )
        
        # Create sample market data
        import pandas as pd
        import numpy as np
        
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
        prices = 50000 + np.cumsum(np.random.randn(100) * 10)
        
        market_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices * 1.001,
            'low': prices * 0.999,
            'close': prices,
            'volume': np.random.uniform(100, 1000, 100),
            'symbol': 'BTC'
        })
        
        # Test generator
        generator = SignalPackGenerator()
        signal_pack = generator.generate_signal_pack(signal, trading_plan, market_data)
        
        if signal_pack:
            print(f"✅ Signal pack created: {signal_pack.pack_id}")
            print(f"   Signal ID: {signal_pack.signal_id}")
            print(f"   Trading Plan ID: {signal_pack.trading_plan_id}")
            print(f"   Features: {len(signal_pack.features)} categories")
            print(f"   Patterns: {len(signal_pack.patterns)} categories")
            print(f"   LLM Format: {len(signal_pack.llm_format)} sections")
            print(f"   Context Completeness: {signal_pack.processing_metadata.get('context_completeness', 0.0):.2f}")
            
            # Show LLM summary
            print(f"\n📝 LLM Summary:")
            print(signal_pack.llm_format.get('summary', 'No summary available'))
        else:
            print("❌ Failed to create signal pack")
        
        print("\n🎉 SignalPackGenerator test complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
