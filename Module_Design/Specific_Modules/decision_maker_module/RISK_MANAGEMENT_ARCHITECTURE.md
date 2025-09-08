# Decision Maker Module - Risk Management Architecture

*Comprehensive risk management system for the Decision Maker Module*

## Executive Summary

This document provides the complete risk management architecture for the Decision Maker Module, including portfolio risk assessment, Value at Risk (VaR) calculations, risk limits, and crypto-specific risk factors.

## 1. Portfolio Risk Mathematics

### 1.1 Value at Risk (VaR) Calculation

```python
import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Optional, Tuple

class PortfolioRiskEngine:
    """Advanced portfolio risk management engine"""
    
    def __init__(self, confidence_level: float = 0.95, time_horizon: int = 1):
        self.confidence_level = confidence_level
        self.time_horizon = time_horizon
        self.risk_limits = self._initialize_risk_limits()
    
    def calculate_var(self, portfolio_returns: np.ndarray, method: str = 'historical') -> float:
        """Calculate Value at Risk using specified method"""
        
        if method == 'historical':
            return self._calculate_historical_var(portfolio_returns)
        elif method == 'parametric':
            return self._calculate_parametric_var(portfolio_returns)
        elif method == 'monte_carlo':
            return self._calculate_monte_carlo_var(portfolio_returns)
        else:
            raise ValueError(f"Unknown VaR method: {method}")
    
    def _calculate_historical_var(self, returns: np.ndarray) -> float:
        """Calculate VaR using historical simulation"""
        # Sort returns in ascending order
        sorted_returns = np.sort(returns)
        
        # Calculate VaR as percentile
        var_index = int((1 - self.confidence_level) * len(sorted_returns))
        var = -sorted_returns[var_index]
        
        return var
    
    def _calculate_parametric_var(self, returns: np.ndarray) -> float:
        """Calculate VaR using parametric method (assumes normal distribution)"""
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        # Z-score for confidence level
        z_score = stats.norm.ppf(1 - self.confidence_level)
        
        # VaR calculation
        var = -(mean_return + z_score * std_return)
        
        return var
    
    def _calculate_monte_carlo_var(self, returns: np.ndarray, n_simulations: int = 10000) -> float:
        """Calculate VaR using Monte Carlo simulation"""
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        # Generate random returns
        random_returns = np.random.normal(mean_return, std_return, n_simulations)
        
        # Calculate VaR
        var = self._calculate_historical_var(random_returns)
        
        return var
    
    def calculate_conditional_var(self, returns: np.ndarray, var: float) -> float:
        """Calculate Conditional VaR (Expected Shortfall)"""
        # Returns worse than VaR
        tail_returns = returns[returns <= -var]
        
        if len(tail_returns) == 0:
            return var
        
        # Average of tail returns
        cvar = -np.mean(tail_returns)
        return cvar
    
    def calculate_portfolio_var(self, positions: List[Dict], market_data: Dict) -> Dict:
        """Calculate portfolio VaR"""
        
        # Portfolio weights and returns
        weights = np.array([pos['weight'] for pos in positions])
        expected_returns = np.array([pos['expected_return'] for pos in positions])
        cov_matrix = market_data['covariance_matrix']
        
        # Portfolio expected return
        portfolio_return = np.dot(weights, expected_returns)
        
        # Portfolio variance
        portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
        portfolio_volatility = np.sqrt(portfolio_variance)
        
        # Calculate VaR
        var_95 = self.calculate_var(np.random.normal(portfolio_return, portfolio_volatility, 1000))
        cvar_95 = self.calculate_conditional_var(np.random.normal(portfolio_return, portfolio_volatility, 1000), var_95)
        
        return {
            'portfolio_return': portfolio_return,
            'portfolio_volatility': portfolio_volatility,
            'var_95': var_95,
            'cvar_95': cvar_95,
            'var_95_percent': var_95 / sum(pos['value'] for pos in positions) * 100,
            'cvar_95_percent': cvar_95 / sum(pos['value'] for pos in positions) * 100
        }
```

### 1.2 Risk Metrics Calculation

```python
class RiskMetricsCalculator:
    """Calculate comprehensive risk metrics"""
    
    def __init__(self):
        self.risk_metrics = {}
    
    def calculate_max_drawdown(self, portfolio_values: np.ndarray) -> float:
        """Calculate maximum drawdown"""
        peak = np.maximum.accumulate(portfolio_values)
        drawdown = (portfolio_values - peak) / peak
        max_drawdown = np.min(drawdown)
        
        return abs(max_drawdown)
    
    def calculate_sharpe_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        excess_returns = returns - risk_free_rate
        sharpe_ratio = np.mean(excess_returns) / np.std(returns) if np.std(returns) > 0 else 0
        
        return sharpe_ratio
    
    def calculate_sortino_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio (downside deviation)"""
        excess_returns = returns - risk_free_rate
        downside_returns = returns[returns < risk_free_rate] - risk_free_rate
        downside_deviation = np.std(downside_returns) if len(downside_returns) > 0 else 0
        
        sortino_ratio = np.mean(excess_returns) / downside_deviation if downside_deviation > 0 else 0
        
        return sortino_ratio
    
    def calculate_calmar_ratio(self, returns: np.ndarray, max_drawdown: float) -> float:
        """Calculate Calmar ratio"""
        annual_return = np.mean(returns) * 252  # Assuming daily returns
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0
        
        return calmar_ratio
    
    def calculate_concentration_risk(self, weights: np.ndarray) -> float:
        """Calculate concentration risk (Herfindahl index)"""
        concentration_risk = np.sum(weights ** 2)
        
        return concentration_risk
    
    def calculate_correlation_risk(self, positions: List[Dict], correlation_threshold: float = 0.7) -> Dict:
        """Calculate correlation risk between positions"""
        correlation_risks = []
        
        for i, pos1 in enumerate(positions):
            for j, pos2 in enumerate(positions[i+1:], i+1):
                correlation = pos1.get('correlation', {}).get(pos2['symbol'], 0)
                
                if abs(correlation) > correlation_threshold:
                    correlation_risks.append({
                        'symbol1': pos1['symbol'],
                        'symbol2': pos2['symbol'],
                        'correlation': correlation,
                        'risk_level': 'high' if abs(correlation) > 0.8 else 'medium'
                    })
        
        return {
            'correlation_risks': correlation_risks,
            'max_correlation': max([cr['correlation'] for cr in correlation_risks]) if correlation_risks else 0,
            'high_correlation_count': len([cr for cr in correlation_risks if cr['risk_level'] == 'high'])
        }
```

## 2. Risk Assessment for Trading Plans

### 2.1 Plan Risk Assessment

```python
class TradingPlanRiskAssessment:
    """Risk assessment for individual trading plans"""
    
    def __init__(self, risk_engine: PortfolioRiskEngine):
        self.risk_engine = risk_engine
        self.risk_limits = self._initialize_risk_limits()
    
    def assess_plan_risk(self, trading_plan: Dict, current_portfolio: Dict) -> Dict:
        """Assess risk impact of trading plan"""
        
        # 1. Position size risk
        position_risk = self._assess_position_size_risk(trading_plan, current_portfolio)
        
        # 2. Portfolio impact risk
        portfolio_impact_risk = self._assess_portfolio_impact_risk(trading_plan, current_portfolio)
        
        # 3. Correlation risk
        correlation_risk = self._assess_correlation_risk(trading_plan, current_portfolio)
        
        # 4. Liquidity risk
        liquidity_risk = self._assess_liquidity_risk(trading_plan)
        
        # 5. Market risk
        market_risk = self._assess_market_risk(trading_plan)
        
        # 6. Calculate overall risk score
        overall_risk_score = self._calculate_overall_risk_score(
            position_risk, portfolio_impact_risk, correlation_risk, 
            liquidity_risk, market_risk
        )
        
        # 7. Determine risk approval
        risk_approved = self._determine_risk_approval(overall_risk_score, trading_plan)
        
        return {
            'overall_score': overall_risk_score,
            'position_risk': position_risk,
            'portfolio_impact_risk': portfolio_impact_risk,
            'correlation_risk': correlation_risk,
            'liquidity_risk': liquidity_risk,
            'market_risk': market_risk,
            'risk_approved': risk_approved,
            'hard_veto': overall_risk_score < 0.3,
            'veto_reason': 'Risk limits exceeded' if overall_risk_score < 0.3 else None
        }
    
    def _assess_position_size_risk(self, trading_plan: Dict, current_portfolio: Dict) -> Dict:
        """Assess position size risk"""
        position_size = trading_plan.get('position_size', 0)
        symbol = trading_plan.get('symbol', '')
        
        # Check against maximum position size
        max_position_size = self.risk_limits['max_position_size']
        position_size_ratio = position_size / max_position_size
        
        # Check against current portfolio concentration
        current_concentration = current_portfolio.get('concentration', {}).get(symbol, 0)
        new_concentration = current_concentration + position_size
        
        # Calculate position size score
        if position_size_ratio > 1.0:
            score = 0.0  # Exceeds limit
        elif position_size_ratio > 0.8:
            score = 0.3  # Close to limit
        elif new_concentration > 0.3:
            score = 0.5  # High concentration
        else:
            score = 1.0  # Within limits
        
        return {
            'score': score,
            'position_size_ratio': position_size_ratio,
            'new_concentration': new_concentration,
            'within_limits': position_size_ratio <= 1.0 and new_concentration <= 0.3
        }
    
    def _assess_portfolio_impact_risk(self, trading_plan: Dict, current_portfolio: Dict) -> Dict:
        """Assess portfolio impact risk"""
        
        # Simulate portfolio with new position
        simulated_portfolio = self._simulate_portfolio_with_position(trading_plan, current_portfolio)
        
        # Calculate VaR impact
        current_var = current_portfolio.get('var_95', 0.02)
        new_var = simulated_portfolio.get('var_95', 0.02)
        var_impact = (new_var - current_var) / current_var if current_var > 0 else 0
        
        # Calculate volatility impact
        current_volatility = current_portfolio.get('volatility', 0.15)
        new_volatility = simulated_portfolio.get('volatility', 0.15)
        volatility_impact = (new_volatility - current_volatility) / current_volatility if current_volatility > 0 else 0
        
        # Calculate impact score
        if var_impact > 0.2:  # 20% increase in VaR
            score = 0.0
        elif var_impact > 0.1:  # 10% increase in VaR
            score = 0.3
        elif var_impact > 0.05:  # 5% increase in VaR
            score = 0.6
        else:
            score = 1.0
        
        return {
            'score': score,
            'var_impact': var_impact,
            'volatility_impact': volatility_impact,
            'acceptable_impact': var_impact <= 0.1
        }
    
    def _assess_correlation_risk(self, trading_plan: Dict, current_portfolio: Dict) -> Dict:
        """Assess correlation risk with existing positions"""
        symbol = trading_plan.get('symbol', '')
        current_positions = current_portfolio.get('positions', [])
        
        # Calculate correlations with existing positions
        correlations = []
        for position in current_positions:
            if position['symbol'] != symbol:
                correlation = position.get('correlations', {}).get(symbol, 0)
                correlations.append({
                    'symbol': position['symbol'],
                    'correlation': correlation,
                    'weight': position.get('weight', 0)
                })
        
        # Calculate weighted correlation
        if correlations:
            weighted_correlation = sum(c['correlation'] * c['weight'] for c in correlations) / sum(c['weight'] for c in correlations)
            max_correlation = max(abs(c['correlation']) for c in correlations)
        else:
            weighted_correlation = 0
            max_correlation = 0
        
        # Calculate correlation score
        if max_correlation > 0.8:
            score = 0.0  # High correlation
        elif max_correlation > 0.6:
            score = 0.3  # Medium correlation
        elif max_correlation > 0.4:
            score = 0.6  # Low correlation
        else:
            score = 1.0  # Very low correlation
        
        return {
            'score': score,
            'weighted_correlation': weighted_correlation,
            'max_correlation': max_correlation,
            'correlations': correlations,
            'low_correlation': max_correlation <= 0.4
        }
    
    def _assess_liquidity_risk(self, trading_plan: Dict) -> Dict:
        """Assess liquidity risk for trading plan"""
        symbol = trading_plan.get('symbol', '')
        position_size = trading_plan.get('position_size', 0)
        
        # Get liquidity data (simplified)
        liquidity_data = self._get_liquidity_data(symbol)
        
        # Calculate liquidity impact
        daily_volume = liquidity_data.get('daily_volume', 0)
        position_value = position_size * liquidity_data.get('price', 0)
        
        if daily_volume > 0:
            volume_impact = position_value / daily_volume
        else:
            volume_impact = 1.0  # No liquidity data
        
        # Calculate liquidity score
        if volume_impact > 0.1:  # 10% of daily volume
            score = 0.0  # High impact
        elif volume_impact > 0.05:  # 5% of daily volume
            score = 0.3  # Medium impact
        elif volume_impact > 0.01:  # 1% of daily volume
            score = 0.6  # Low impact
        else:
            score = 1.0  # Very low impact
        
        return {
            'score': score,
            'volume_impact': volume_impact,
            'daily_volume': daily_volume,
            'position_value': position_value,
            'low_impact': volume_impact <= 0.01
        }
    
    def _assess_market_risk(self, trading_plan: Dict) -> Dict:
        """Assess market risk for trading plan"""
        symbol = trading_plan.get('symbol', '')
        direction = trading_plan.get('direction', 'neutral')
        
        # Get market data
        market_data = self._get_market_data(symbol)
        
        # Calculate volatility
        volatility = market_data.get('volatility', 0.2)
        
        # Calculate regime risk
        regime = market_data.get('regime', 'normal')
        regime_risk = self._calculate_regime_risk(regime, direction)
        
        # Calculate market risk score
        if volatility > 0.5:  # Very high volatility
            score = 0.0
        elif volatility > 0.3:  # High volatility
            score = 0.3
        elif volatility > 0.2:  # Medium volatility
            score = 0.6
        else:
            score = 1.0
        
        # Adjust for regime risk
        score *= regime_risk
        
        return {
            'score': score,
            'volatility': volatility,
            'regime': regime,
            'regime_risk': regime_risk,
            'low_volatility': volatility <= 0.2
        }
    
    def _calculate_overall_risk_score(self, position_risk: Dict, portfolio_impact_risk: Dict,
                                    correlation_risk: Dict, liquidity_risk: Dict, market_risk: Dict) -> float:
        """Calculate overall risk score"""
        
        # Weighted combination of risk factors
        weights = {
            'position': 0.25,
            'portfolio_impact': 0.25,
            'correlation': 0.20,
            'liquidity': 0.15,
            'market': 0.15
        }
        
        overall_score = (
            position_risk['score'] * weights['position'] +
            portfolio_impact_risk['score'] * weights['portfolio_impact'] +
            correlation_risk['score'] * weights['correlation'] +
            liquidity_risk['score'] * weights['liquidity'] +
            market_risk['score'] * weights['market']
        )
        
        return overall_score
    
    def _determine_risk_approval(self, overall_score: float, trading_plan: Dict) -> bool:
        """Determine if trading plan passes risk approval"""
        
        # Hard limits
        if overall_score < 0.3:
            return False  # Hard veto
        
        # Additional checks
        position_size = trading_plan.get('position_size', 0)
        if position_size > self.risk_limits['max_position_size']:
            return False
        
        # Risk score threshold
        return overall_score >= 0.5
```

## 3. Risk Limits and Monitoring

### 3.1 Risk Limits Management

```python
class RiskLimitsManager:
    """Manage risk limits and monitoring"""
    
    def __init__(self):
        self.risk_limits = self._initialize_risk_limits()
        self.current_risk_state = {}
        self.risk_alerts = []
    
    def _initialize_risk_limits(self) -> Dict:
        """Initialize risk limits"""
        return {
            'max_position_size': 0.1,        # 10% max per position
            'max_portfolio_var': 0.02,       # 2% max portfolio VaR
            'max_portfolio_cvar': 0.03,      # 3% max portfolio CVaR
            'max_drawdown': 0.1,             # 10% max drawdown
            'max_concentration': 0.3,        # 30% max concentration
            'max_correlation': 0.7,          # 70% max correlation
            'max_volatility': 0.5,           # 50% max volatility
            'min_liquidity_ratio': 0.01      # 1% min liquidity ratio
        }
    
    def check_risk_limits(self, trading_plan: Dict, current_portfolio: Dict) -> Dict:
        """Check if trading plan violates risk limits"""
        
        violations = []
        warnings = []
        
        # Check position size limit
        position_size = trading_plan.get('position_size', 0)
        if position_size > self.risk_limits['max_position_size']:
            violations.append({
                'type': 'position_size',
                'limit': self.risk_limits['max_position_size'],
                'actual': position_size,
                'severity': 'high'
            })
        
        # Check concentration limit
        symbol = trading_plan.get('symbol', '')
        current_concentration = current_portfolio.get('concentration', {}).get(symbol, 0)
        new_concentration = current_concentration + position_size
        
        if new_concentration > self.risk_limits['max_concentration']:
            violations.append({
                'type': 'concentration',
                'limit': self.risk_limits['max_concentration'],
                'actual': new_concentration,
                'severity': 'high'
            })
        
        # Check VaR limit
        simulated_portfolio = self._simulate_portfolio_with_position(trading_plan, current_portfolio)
        new_var = simulated_portfolio.get('var_95', 0)
        
        if new_var > self.risk_limits['max_portfolio_var']:
            violations.append({
                'type': 'portfolio_var',
                'limit': self.risk_limits['max_portfolio_var'],
                'actual': new_var,
                'severity': 'high'
            })
        
        # Check correlation limit
        correlations = self._get_position_correlations(trading_plan, current_portfolio)
        max_correlation = max([abs(c['correlation']) for c in correlations]) if correlations else 0
        
        if max_correlation > self.risk_limits['max_correlation']:
            warnings.append({
                'type': 'correlation',
                'limit': self.risk_limits['max_correlation'],
                'actual': max_correlation,
                'severity': 'medium'
            })
        
        return {
            'violations': violations,
            'warnings': warnings,
            'within_limits': len(violations) == 0,
            'risk_score': self._calculate_risk_score(violations, warnings)
        }
    
    def update_risk_state(self, current_portfolio: Dict):
        """Update current risk state"""
        self.current_risk_state = {
            'portfolio_var': current_portfolio.get('var_95', 0),
            'portfolio_cvar': current_portfolio.get('cvar_95', 0),
            'max_drawdown': current_portfolio.get('max_drawdown', 0),
            'concentration': current_portfolio.get('concentration', {}),
            'volatility': current_portfolio.get('volatility', 0),
            'last_updated': datetime.now(timezone.utc)
        }
    
    def generate_risk_alerts(self, risk_state: Dict) -> List[Dict]:
        """Generate risk alerts based on current state"""
        alerts = []
        
        # VaR alert
        if risk_state['portfolio_var'] > self.risk_limits['max_portfolio_var'] * 0.8:
            alerts.append({
                'type': 'var_warning',
                'message': f"Portfolio VaR approaching limit: {risk_state['portfolio_var']:.4f}",
                'severity': 'medium' if risk_state['portfolio_var'] < self.risk_limits['max_portfolio_var'] else 'high'
            })
        
        # Concentration alert
        max_concentration = max(risk_state['concentration'].values()) if risk_state['concentration'] else 0
        if max_concentration > self.risk_limits['max_concentration'] * 0.8:
            alerts.append({
                'type': 'concentration_warning',
                'message': f"Portfolio concentration approaching limit: {max_concentration:.4f}",
                'severity': 'medium' if max_concentration < self.risk_limits['max_concentration'] else 'high'
            })
        
        # Drawdown alert
        if risk_state['max_drawdown'] > self.risk_limits['max_drawdown'] * 0.8:
            alerts.append({
                'type': 'drawdown_warning',
                'message': f"Portfolio drawdown approaching limit: {risk_state['max_drawdown']:.4f}",
                'severity': 'medium' if risk_state['max_drawdown'] < self.risk_limits['max_drawdown'] else 'high'
            })
        
        return alerts
```

## 4. Crypto-Specific Risk Factors

### 4.1 Crypto Risk Assessment

```python
class CryptoRiskAssessment:
    """Crypto-specific risk assessment"""
    
    def __init__(self):
        self.crypto_risk_factors = self._initialize_crypto_risk_factors()
    
    def assess_crypto_risks(self, trading_plan: Dict, market_data: Dict) -> Dict:
        """Assess crypto-specific risks"""
        
        symbol = trading_plan.get('symbol', '')
        
        # 1. Volatility risk
        volatility_risk = self._assess_volatility_risk(symbol, market_data)
        
        # 2. Liquidity risk
        liquidity_risk = self._assess_crypto_liquidity_risk(symbol, market_data)
        
        # 3. Regulatory risk
        regulatory_risk = self._assess_regulatory_risk(symbol, market_data)
        
        # 4. Technology risk
        technology_risk = self._assess_technology_risk(symbol, market_data)
        
        # 5. Market manipulation risk
        manipulation_risk = self._assess_manipulation_risk(symbol, market_data)
        
        # 6. Calculate overall crypto risk score
        overall_score = self._calculate_crypto_risk_score(
            volatility_risk, liquidity_risk, regulatory_risk, 
            technology_risk, manipulation_risk
        )
        
        return {
            'overall_score': overall_score,
            'volatility_risk': volatility_risk,
            'liquidity_risk': liquidity_risk,
            'regulatory_risk': regulatory_risk,
            'technology_risk': technology_risk,
            'manipulation_risk': manipulation_risk,
            'crypto_approved': overall_score >= 0.5
        }
    
    def _assess_volatility_risk(self, symbol: str, market_data: Dict) -> Dict:
        """Assess crypto volatility risk"""
        volatility = market_data.get('volatility', 0.3)
        
        # Crypto volatility is typically higher than traditional assets
        if volatility > 0.8:  # 80% volatility
            score = 0.0
        elif volatility > 0.6:  # 60% volatility
            score = 0.3
        elif volatility > 0.4:  # 40% volatility
            score = 0.6
        else:
            score = 1.0
        
        return {
            'score': score,
            'volatility': volatility,
            'risk_level': 'high' if volatility > 0.6 else 'medium' if volatility > 0.4 else 'low'
        }
    
    def _assess_crypto_liquidity_risk(self, symbol: str, market_data: Dict) -> Dict:
        """Assess crypto liquidity risk"""
        daily_volume = market_data.get('daily_volume', 0)
        market_cap = market_data.get('market_cap', 0)
        
        # Calculate liquidity metrics
        volume_ratio = daily_volume / market_cap if market_cap > 0 else 0
        
        if volume_ratio > 0.1:  # 10% daily volume
            score = 1.0
        elif volume_ratio > 0.05:  # 5% daily volume
            score = 0.6
        elif volume_ratio > 0.01:  # 1% daily volume
            score = 0.3
        else:
            score = 0.0
        
        return {
            'score': score,
            'volume_ratio': volume_ratio,
            'daily_volume': daily_volume,
            'market_cap': market_cap,
            'risk_level': 'low' if volume_ratio > 0.05 else 'medium' if volume_ratio > 0.01 else 'high'
        }
    
    def _assess_regulatory_risk(self, symbol: str, market_data: Dict) -> Dict:
        """Assess regulatory risk for crypto asset"""
        regulatory_status = market_data.get('regulatory_status', 'unknown')
        
        # Regulatory risk scoring
        if regulatory_status == 'approved':
            score = 1.0
        elif regulatory_status == 'pending':
            score = 0.6
        elif regulatory_status == 'restricted':
            score = 0.3
        else:  # unknown or banned
            score = 0.0
        
        return {
            'score': score,
            'regulatory_status': regulatory_status,
            'risk_level': 'low' if score > 0.8 else 'medium' if score > 0.4 else 'high'
        }
    
    def _assess_technology_risk(self, symbol: str, market_data: Dict) -> Dict:
        """Assess technology risk for crypto asset"""
        network_health = market_data.get('network_health', 0.5)
        security_score = market_data.get('security_score', 0.5)
        
        # Combined technology score
        tech_score = (network_health + security_score) / 2
        
        if tech_score > 0.8:
            score = 1.0
        elif tech_score > 0.6:
            score = 0.6
        elif tech_score > 0.4:
            score = 0.3
        else:
            score = 0.0
        
        return {
            'score': score,
            'network_health': network_health,
            'security_score': security_score,
            'tech_score': tech_score,
            'risk_level': 'low' if tech_score > 0.8 else 'medium' if tech_score > 0.6 else 'high'
        }
    
    def _assess_manipulation_risk(self, symbol: str, market_data: Dict) -> Dict:
        """Assess market manipulation risk"""
        manipulation_indicators = market_data.get('manipulation_indicators', {})
        
        # Check various manipulation indicators
        price_spike = manipulation_indicators.get('price_spike', 0)
        volume_spike = manipulation_indicators.get('volume_spike', 0)
        order_book_imbalance = manipulation_indicators.get('order_book_imbalance', 0)
        
        # Calculate manipulation risk score
        manipulation_score = (price_spike + volume_spike + order_book_imbalance) / 3
        
        if manipulation_score < 0.2:
            score = 1.0  # Low manipulation risk
        elif manipulation_score < 0.5:
            score = 0.6  # Medium manipulation risk
        elif manipulation_score < 0.8:
            score = 0.3  # High manipulation risk
        else:
            score = 0.0  # Very high manipulation risk
        
        return {
            'score': score,
            'manipulation_score': manipulation_score,
            'price_spike': price_spike,
            'volume_spike': volume_spike,
            'order_book_imbalance': order_book_imbalance,
            'risk_level': 'low' if manipulation_score < 0.2 else 'medium' if manipulation_score < 0.5 else 'high'
        }
    
    def _calculate_crypto_risk_score(self, volatility_risk: Dict, liquidity_risk: Dict,
                                   regulatory_risk: Dict, technology_risk: Dict, 
                                   manipulation_risk: Dict) -> float:
        """Calculate overall crypto risk score"""
        
        # Weighted combination of crypto risk factors
        weights = {
            'volatility': 0.25,
            'liquidity': 0.25,
            'regulatory': 0.20,
            'technology': 0.15,
            'manipulation': 0.15
        }
        
        overall_score = (
            volatility_risk['score'] * weights['volatility'] +
            liquidity_risk['score'] * weights['liquidity'] +
            regulatory_risk['score'] * weights['regulatory'] +
            technology_risk['score'] * weights['technology'] +
            manipulation_risk['score'] * weights['manipulation']
        )
        
        return overall_score
```

This provides the complete risk management architecture for the Decision Maker Module with comprehensive risk assessment, limits management, and crypto-specific risk factors!
