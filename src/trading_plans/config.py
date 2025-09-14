"""
Trading Plan Configuration Manager
Phase 1.4.6: Configuration and Risk Management
"""

import yaml
import os
from typing import Dict, Any, Optional
from decimal import Decimal


class TradingPlanConfig:
    """Configuration manager for trading plan generation"""
    
    def __init__(self, config_file: str = 'config/trading_plans.yaml'):
        """Initialize configuration manager"""
        self.config_file = config_file
        self.config = self._load_config()
        self.risk_config = self.config['risk_management']
        self.position_sizing = self.config['position_sizing']
        self.time_horizons = self.config['time_horizons']
        self.signal_thresholds = self.config['signal_thresholds']
        self.validation_rules = self.config['validation']
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")
    
    def get_risk_config(self, signal_strength: float) -> Dict[str, Any]:
        """Get risk configuration based on signal strength"""
        if signal_strength >= self.signal_thresholds['high_confidence']:
            return self.risk_config['high_confidence']
        elif signal_strength >= self.signal_thresholds['medium_confidence']:
            return self.risk_config['medium_confidence']
        else:
            return self.risk_config['low_confidence']
    
    def get_position_size_percentage(self, signal_strength: float, 
                                   volatility: float = 1.0, correlation: float = 1.0) -> float:
        """Calculate position size as percentage based on signal strength and market conditions"""
        base_size = self.position_sizing['base_percentage']
        max_size = self.position_sizing['max_percentage']
        
        # Base position size from signal strength
        strength_multiplier = signal_strength
        calculated_size = base_size * strength_multiplier
        
        # Apply volatility adjustment
        if self.position_sizing['volatility_adjustment']:
            volatility_adjustment = 1.0 / max(volatility, 0.1)  # Reduce size for high volatility
            calculated_size *= volatility_adjustment
        
        # Apply correlation adjustment
        if self.position_sizing['correlation_adjustment']:
            correlation_adjustment = 1.0 / max(correlation, 0.1)  # Reduce size for high correlation
            calculated_size *= correlation_adjustment
        
        # Apply maximum size limit
        final_size = min(calculated_size, max_size)
        
        # Return as percentage (0.0 to 1.0)
        return float(final_size)
    
    def get_time_horizon(self, timeframe: str) -> str:
        """Get time horizon for given timeframe"""
        return self.time_horizons.get(timeframe, '1h')
    
    def get_entry_strategy(self, signal_type: str = 'default') -> str:
        """Get entry strategy configuration"""
        strategies = self.config['entry_strategies']
        return strategies.get(signal_type, strategies['default'])
    
    def get_execution_venue(self, priority: str = 'primary') -> str:
        """Get execution venue configuration"""
        venues = self.config['execution_venues']
        return venues.get(priority, venues['primary'])
    
    def get_slippage_tolerance(self, volatility_regime: str = 'default') -> float:
        """Get slippage tolerance based on volatility regime"""
        slippage_config = self.config['slippage_tolerance']
        return slippage_config.get(volatility_regime, slippage_config['default'])
    
    def validate_trading_plan(self, plan_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate trading plan against configuration rules"""
        validation = self.validation_rules
        
        # Validate entry price
        entry_price = plan_data.get('entry_price', 0)
        if not (validation['min_entry_price'] <= entry_price <= validation['max_entry_price']):
            return False, f"Entry price {entry_price} outside valid range"
        
        # Validate position size
        position_size = plan_data.get('position_size', 0)
        if not (validation['min_position_size'] <= position_size <= validation['max_position_size']):
            return False, f"Position size {position_size} outside valid range"
        
        # Validate risk-reward ratio
        risk_reward = plan_data.get('risk_reward_ratio', 0)
        if not (validation['min_risk_reward'] <= risk_reward <= validation['max_risk_reward']):
            return False, f"Risk-reward ratio {risk_reward} outside valid range"
        
        # Validate confidence score
        confidence = plan_data.get('confidence_score', 0)
        if not (validation['min_confidence'] <= confidence <= validation['max_confidence']):
            return False, f"Confidence score {confidence} outside valid range"
        
        # Validate strength score
        strength = plan_data.get('strength_score', 0)
        if not (validation['min_strength'] <= strength <= validation['max_strength']):
            return False, f"Strength score {strength} outside valid range"
        
        return True, None
    
    def get_risk_limits(self) -> Dict[str, float]:
        """Get risk limits configuration"""
        return self.config['risk_limits']
    
    def get_market_context_weights(self) -> Dict[str, float]:
        """Get market context weights for position sizing"""
        return self.config['market_context_weights']
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update configuration with new values"""
        self.config.update(new_config)
        self._save_config()
    
    def _save_config(self) -> None:
        """Save current configuration to file"""
        with open(self.config_file, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, indent=2)
    
    def reload_config(self) -> None:
        """Reload configuration from file"""
        self.config = self._load_config()
        self.risk_config = self.config['risk_management']
        self.position_sizing = self.config['position_sizing']
        self.time_horizons = self.config['time_horizons']
        self.signal_thresholds = self.config['signal_thresholds']
        self.validation_rules = self.config['validation']


# Global configuration instance
_config_instance: Optional[TradingPlanConfig] = None


def get_config() -> TradingPlanConfig:
    """Get global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = TradingPlanConfig()
    return _config_instance


def reload_config() -> None:
    """Reload global configuration"""
    global _config_instance
    if _config_instance is not None:
        _config_instance.reload_config()


if __name__ == "__main__":
    # Test the configuration manager
    print("🧪 Testing Trading Plan Configuration Manager...")
    
    try:
        config = TradingPlanConfig()
        print("✅ Configuration loaded successfully")
        
        # Test risk configuration selection
        high_risk = config.get_risk_config(0.9)
        medium_risk = config.get_risk_config(0.7)
        low_risk = config.get_risk_config(0.5)
        
        print(f"✅ Risk configurations:")
        print(f"   High confidence: max_position_size={high_risk['max_position_size']}")
        print(f"   Medium confidence: max_position_size={medium_risk['max_position_size']}")
        print(f"   Low confidence: max_position_size={low_risk['max_position_size']}")
        
        # Test position sizing
        account_balance = Decimal("10000")
        position_size = config.get_position_size(0.8, account_balance, volatility=1.5, correlation=0.7)
        print(f"✅ Position sizing: {position_size} (account: {account_balance})")
        
        # Test validation
        valid_plan = {
            'entry_price': 50000,
            'position_size': 0.1,
            'risk_reward_ratio': 2.0,
            'confidence_score': 0.8,
            'strength_score': 0.7
        }
        
        is_valid, error = config.validate_trading_plan(valid_plan)
        print(f"✅ Plan validation: {'PASS' if is_valid else 'FAIL'}")
        if error:
            print(f"   Error: {error}")
        
        # Test invalid plan
        invalid_plan = {
            'entry_price': -1000,  # Invalid negative price
            'position_size': 0.1,
            'risk_reward_ratio': 2.0,
            'confidence_score': 0.8,
            'strength_score': 0.7
        }
        
        is_valid, error = config.validate_trading_plan(invalid_plan)
        print(f"✅ Invalid plan validation: {'PASS' if is_valid else 'FAIL'}")
        if error:
            print(f"   Error: {error}")
        
        print("\n🎉 Configuration manager working correctly!")
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
