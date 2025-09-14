"""
Trading Plan Builder
Phase 1.4.1: Convert processed signals into complete trading plans with risk management
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
import pandas as pd

from .models import (
    TradingPlan, RiskMetrics, ExecutionParameters, MarketContext,
    generate_plan_id, calculate_time_horizon, calculate_valid_until
)
from .config import get_config

logger = logging.getLogger(__name__)


class TradingPlanBuilder:
    """Builds complete trading plans from processed signals"""
    
    def __init__(self, config=None):
        """Initialize trading plan builder"""
        self.config = config or get_config()
        self.account_balance = Decimal("10000")  # Default account balance
        
    def build_trading_plan(self, signal: Dict[str, Any], market_data: pd.DataFrame) -> Optional[TradingPlan]:
        """Convert processed signal into complete trading plan"""
        try:
            logger.debug(f"Building trading plan for signal: {signal.get('signal_id', 'unknown')}")
            
            # 1. Extract signal information
            signal_id = signal.get('signal_id', f"signal_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            direction = signal.get('direction', 'unknown')
            confidence = signal.get('confidence', 0.0)
            strength = signal.get('strength', 0.0)
            timeframe = signal.get('timeframe', '1h')
            
            # 2. Get market context
            market_context = self._build_market_context(market_data, signal)
            
            # 3. Calculate entry price
            entry_price = self._calculate_entry_price(signal, market_data, direction)
            
            # 4. Calculate position size as percentage
            position_size_pct = self._calculate_position_size_percentage(signal, market_context)
            
            # 5. Calculate stop loss and take profit
            stop_loss, take_profit = self._calculate_stop_loss_take_profit(
                entry_price, direction, signal, market_context
            )
            
            # 6. Calculate risk-reward ratio
            risk_reward_ratio = self._calculate_risk_reward_ratio(entry_price, stop_loss, take_profit, direction)
            
            # 7. Generate entry conditions
            entry_conditions = self._generate_entry_conditions(signal, market_context)
            
            # 8. Create execution parameters
            execution_params = self._create_execution_parameters(signal, market_context)
            
            # 9. Create trading plan
            trading_plan = TradingPlan(
                plan_id=generate_plan_id(),
                signal_id=signal_id,
                symbol=market_context.get('symbol', 'UNKNOWN'),
                timeframe=timeframe,
                direction=direction,
                entry_conditions=entry_conditions,
                entry_price=entry_price,
                position_size=Decimal(str(position_size_pct)),
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=risk_reward_ratio,
                confidence_score=confidence,
                strength_score=strength,
                time_horizon=calculate_time_horizon(timeframe),
                valid_until=calculate_valid_until(timeframe),
                created_at=datetime.now(),
                market_context=market_context,
                signal_metadata={
                    'source': 'alpha_detector',
                    'features': signal.get('features', {}),
                    'patterns': signal.get('patterns', {}),
                    'regime': signal.get('regime', 'unknown'),
                    'processing_metadata': signal.get('processing_metadata', {}),
                    'execution_params': execution_params.to_dict()
                }
            )
            
            # 10. Validate trading plan (use percentage for validation)
            validation_data = trading_plan.to_dict()
            validation_data['position_size'] = position_size_pct
            
            is_valid, error = self.config.validate_trading_plan(validation_data)
            if not is_valid:
                logger.warning(f"Trading plan validation failed: {error}")
                return None
            
            logger.info(f"Trading plan created: {trading_plan.plan_id} - {direction} {trading_plan.symbol}")
            return trading_plan
            
        except Exception as e:
            logger.error(f"Error building trading plan: {e}")
            return None
    
    def _build_market_context(self, market_data: pd.DataFrame, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Build comprehensive market context"""
        try:
            # Get current price from market data
            current_price = Decimal(str(market_data['close'].iloc[-1]))
            
            # Calculate basic market metrics
            volume_24h = Decimal(str(market_data['volume'].tail(24).sum())) if len(market_data) >= 24 else Decimal("0")
            volatility_24h = float(market_data['close'].pct_change().tail(24).std()) if len(market_data) >= 24 else 0.0
            
            # Get symbol from market data or signal
            symbol = market_data.get('symbol', signal.get('symbol', 'UNKNOWN')).iloc[0] if hasattr(market_data.get('symbol'), 'iloc') else 'UNKNOWN'
            
            return {
                'symbol': symbol,
                'current_price': float(current_price),
                'volume_24h': float(volume_24h),
                'volatility_24h': volatility_24h,
                'market_cap': None,  # Not available in basic OHLCV data
                'sector': 'crypto',  # Default for crypto assets
                'correlation_btc': None,  # Would need additional data
                'news_sentiment': None,  # Would need additional data
                'market_regime': signal.get('regime', 'unknown'),
                'trend_strength': self._calculate_trend_strength(market_data),
                'volume_confirmation': self._check_volume_confirmation(market_data, signal),
                'pattern_strength': signal.get('strength', 0.0),
                'regime_alignment': self._check_regime_alignment(signal)
            }
        except Exception as e:
            logger.error(f"Error building market context: {e}")
            return {'symbol': 'UNKNOWN', 'current_price': 0.0}
    
    def _calculate_entry_price(self, signal: Dict[str, Any], market_data: pd.DataFrame, direction: str) -> Decimal:
        """Calculate entry price from current market data"""
        try:
            current_price = Decimal(str(market_data['close'].iloc[-1]))
            
            # For now, use current price as entry price
            # In a more sophisticated system, this could be:
            # - Limit order at support/resistance levels
            # - Market order for immediate execution
            # - Stop order for breakout confirmation
            
            return current_price
        except Exception as e:
            logger.error(f"Error calculating entry price: {e}")
            return Decimal("0.0")
    
    def _calculate_position_size_percentage(self, signal: Dict[str, Any], market_context: Dict[str, Any]) -> float:
        """Calculate position size based on signal strength and market conditions"""
        try:
            signal_strength = signal.get('strength', 0.0)
            confidence = signal.get('confidence', 0.0)
            
            # Get market context weights
            weights = self.config.get_market_context_weights()
            
            # Calculate weighted market context score
            market_score = (
                weights['volatility'] * (1.0 / max(market_context.get('volatility_24h', 1.0), 0.1)) +
                weights['trend_strength'] * market_context.get('trend_strength', 0.5) +
                weights['volume_confirmation'] * market_context.get('volume_confirmation', 0.5) +
                weights['pattern_strength'] * market_context.get('pattern_strength', 0.5) +
                weights['regime_alignment'] * market_context.get('regime_alignment', 0.5)
            )
            
            # Calculate position size as percentage
            position_size_pct = self.config.get_position_size_percentage(
                signal_strength=signal_strength,
                volatility=market_context.get('volatility_24h', 1.0),
                correlation=0.7  # Default correlation for crypto
            )
            
            return position_size_pct
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.01  # Minimum position size percentage
    
    def _calculate_stop_loss_take_profit(self, entry_price: Decimal, direction: str, 
                                       signal: Dict[str, Any], market_context: Dict[str, Any]) -> Tuple[Decimal, Decimal]:
        """Calculate stop loss and take profit levels"""
        try:
            # Get risk configuration based on signal strength
            risk_config = self.config.get_risk_config(signal.get('strength', 0.0))
            
            # Calculate ATR-based stop loss distance
            atr_multiplier = risk_config['stop_loss_atr_multiplier']
            take_profit_multiplier = risk_config['take_profit_atr_multiplier']
            
            # For now, use simple percentage-based stops
            # In a more sophisticated system, this would use ATR
            stop_loss_pct = Decimal(str(0.02))  # 2% stop loss
            take_profit_pct = Decimal(str(0.04))  # 4% take profit
            
            if direction == 'long':
                stop_loss = entry_price * (1 - stop_loss_pct)
                take_profit = entry_price * (1 + take_profit_pct)
            else:  # short
                stop_loss = entry_price * (1 + stop_loss_pct)
                take_profit = entry_price * (1 - take_profit_pct)
            
            return stop_loss, take_profit
            
        except Exception as e:
            logger.error(f"Error calculating stop loss/take profit: {e}")
            # Fallback to simple 2% stop, 4% target
            if direction == 'long':
                return entry_price * Decimal("0.98"), entry_price * Decimal("1.04")
            else:
                return entry_price * Decimal("1.02"), entry_price * Decimal("0.96")
    
    def _calculate_risk_reward_ratio(self, entry_price: Decimal, stop_loss: Decimal, 
                                   take_profit: Decimal, direction: str) -> Decimal:
        """Calculate risk-reward ratio"""
        try:
            if direction == 'long':
                risk = entry_price - stop_loss
                reward = take_profit - entry_price
            else:  # short
                risk = stop_loss - entry_price
                reward = entry_price - take_profit
            
            if risk <= 0:
                return Decimal("1.0")  # Minimum risk-reward ratio
            
            return reward / risk
            
        except Exception as e:
            logger.error(f"Error calculating risk-reward ratio: {e}")
            return Decimal("1.0")
    
    def _generate_entry_conditions(self, signal: Dict[str, Any], market_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate entry conditions for the trading plan"""
        return {
            'price_above': market_context.get('current_price', 0) * 0.999,  # 0.1% below current
            'price_below': market_context.get('current_price', 0) * 1.001,  # 0.1% above current
            'volume_confirmation': signal.get('features', {}).get('volume_spike', False),
            'pattern_confirmation': signal.get('patterns', {}).get('breakout_up', False) or 
                                  signal.get('patterns', {}).get('breakout_down', False),
            'regime_alignment': market_context.get('regime_alignment', 0.5) > 0.6,
            'confidence_threshold': signal.get('confidence', 0.0) >= 0.6
        }
    
    def _create_execution_parameters(self, signal: Dict[str, Any], market_context: Dict[str, Any]) -> ExecutionParameters:
        """Create execution parameters for the trading plan"""
        # Determine execution strategy based on signal strength
        signal_strength = signal.get('strength', 0.0)
        
        if signal_strength > 0.8:
            entry_strategy = 'market_order'
            execution_priority = 'high'
        elif signal_strength > 0.6:
            entry_strategy = 'limit_order'
            execution_priority = 'medium'
        else:
            entry_strategy = 'stop_order'
            execution_priority = 'low'
        
        return ExecutionParameters(
            entry_strategy=entry_strategy,
            execution_venue=self.config.get_execution_venue('primary'),
            order_type=entry_strategy,
            time_in_force='GTC',
            slippage_tolerance=self.config.get_slippage_tolerance('default'),
            execution_priority=execution_priority
        )
    
    def _calculate_trend_strength(self, market_data: pd.DataFrame) -> float:
        """Calculate trend strength from market data"""
        try:
            if len(market_data) < 20:
                return 0.5  # Neutral trend
            
            # Simple trend calculation using moving averages
            short_ma = market_data['close'].rolling(10).mean().iloc[-1]
            long_ma = market_data['close'].rolling(20).mean().iloc[-1]
            
            if long_ma == 0:
                return 0.5
            
            trend_ratio = (short_ma - long_ma) / long_ma
            return max(0.0, min(1.0, 0.5 + trend_ratio * 2))  # Normalize to 0-1
            
        except Exception as e:
            logger.error(f"Error calculating trend strength: {e}")
            return 0.5
    
    def _check_volume_confirmation(self, market_data: pd.DataFrame, signal: Dict[str, Any]) -> float:
        """Check volume confirmation for the signal"""
        try:
            if len(market_data) < 20:
                return 0.5
            
            # Check if current volume is above average
            current_volume = market_data['volume'].iloc[-1]
            avg_volume = market_data['volume'].rolling(20).mean().iloc[-1]
            
            if avg_volume == 0:
                return 0.5
            
            volume_ratio = current_volume / avg_volume
            return min(1.0, volume_ratio / 2.0)  # Normalize to 0-1
            
        except Exception as e:
            logger.error(f"Error checking volume confirmation: {e}")
            return 0.5
    
    def _check_regime_alignment(self, signal: Dict[str, Any]) -> float:
        """Check if signal aligns with current market regime"""
        try:
            regime = signal.get('regime', 'unknown')
            direction = signal.get('direction', 'unknown')
            
            # Simple regime alignment check
            if regime == 'trending_up' and direction == 'long':
                return 0.9
            elif regime == 'trending_down' and direction == 'short':
                return 0.9
            elif regime == 'ranging':
                return 0.6  # Neutral for ranging markets
            else:
                return 0.3  # Low alignment for counter-trend signals
                
        except Exception as e:
            logger.error(f"Error checking regime alignment: {e}")
            return 0.5
    
    def set_account_balance(self, balance: Decimal) -> None:
        """Set account balance for position sizing calculations"""
        self.account_balance = balance
        logger.info(f"Account balance set to: {balance}")
    
    def get_risk_metrics(self, trading_plan: TradingPlan) -> RiskMetrics:
        """Calculate risk metrics for a trading plan (percentage-based)"""
        try:
            entry_price = trading_plan.entry_price
            position_size_pct = float(trading_plan.position_size)  # Already a percentage
            stop_loss = trading_plan.stop_loss
            take_profit = trading_plan.take_profit
            direction = trading_plan.direction
            
            # Calculate risk as percentage of position
            if direction == 'long':
                stop_loss_distance = entry_price - stop_loss
                take_profit_distance = take_profit - entry_price
            else:  # short
                stop_loss_distance = stop_loss - entry_price
                take_profit_distance = entry_price - take_profit
            
            # Risk percentage = (stop loss distance / entry price) * position size percentage
            risk_percentage = float(stop_loss_distance / entry_price) * position_size_pct if entry_price > 0 else 0.0
            
            # Risk amount is now percentage-based (no absolute dollar amounts)
            risk_amount = Decimal(str(risk_percentage))  # Risk as percentage of portfolio
            
            return RiskMetrics(
                position_size=Decimal(str(position_size_pct)),
                risk_amount=risk_amount,  # Now percentage-based
                risk_percentage=risk_percentage,
                stop_loss_distance=stop_loss_distance,
                take_profit_distance=take_profit_distance,
                risk_reward_ratio=trading_plan.risk_reward_ratio,
                max_drawdown=0.15,  # Default max drawdown
                volatility_adjustment=1.0  # Default volatility adjustment
            )
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return RiskMetrics(
                position_size=Decimal("0"),
                risk_amount=Decimal("0"),
                risk_percentage=0.0,
                stop_loss_distance=Decimal("0"),
                take_profit_distance=Decimal("0"),
                risk_reward_ratio=Decimal("1.0"),
                max_drawdown=0.15,
                volatility_adjustment=1.0
            )


if __name__ == "__main__":
    # Test the TradingPlanBuilder
    print("🧪 Testing TradingPlanBuilder...")
    
    try:
        # Create sample signal
        signal = {
            'signal_id': 'test_signal_123',
            'direction': 'long',
            'confidence': 0.75,
            'strength': 0.65,
            'timeframe': '1h',
            'features': {'rsi': 45.0, 'macd': 0.001, 'volume_spike': True},
            'patterns': {'breakout_up': True, 'support': 49000},
            'regime': 'trending_up',
            'processing_metadata': {'quality_score': 0.85}
        }
        
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
        
        # Test builder
        builder = TradingPlanBuilder()
        builder.set_account_balance(Decimal("10000"))
        
        trading_plan = builder.build_trading_plan(signal, market_data)
        
        if trading_plan:
            print(f"✅ Trading plan created: {trading_plan.plan_id}")
            print(f"   Symbol: {trading_plan.symbol}")
            print(f"   Direction: {trading_plan.direction}")
            print(f"   Entry: ${trading_plan.entry_price}")
            print(f"   Stop Loss: ${trading_plan.stop_loss}")
            print(f"   Take Profit: ${trading_plan.take_profit}")
            print(f"   Position Size: {trading_plan.position_size:.2%} of portfolio")
            print(f"   Risk-Reward: {trading_plan.risk_reward_ratio}")
            print(f"   Confidence: {trading_plan.confidence_score}")
            print(f"   Strength: {trading_plan.strength_score}")
            
            # Test risk metrics
            risk_metrics = builder.get_risk_metrics(trading_plan)
            print(f"   Risk Amount: {risk_metrics.risk_amount:.2%} of portfolio")
            print(f"   Risk Percentage: {risk_metrics.risk_percentage:.2%}")
        else:
            print("❌ Failed to create trading plan")
        
        print("\n🎉 TradingPlanBuilder test complete!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
