"""
Market Microstructure Analyzer

Analyzes market microstructure patterns in raw OHLCV data to detect
anomalies, order flow patterns, and market maker behavior that traditional
indicators miss.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import logging


class MarketMicrostructureAnalyzer:
    """
    Analyzes market microstructure patterns in raw OHLCV data
    
    Focuses on:
    - Order flow patterns
    - Market maker behavior
    - Price impact analysis
    - Bid-ask spread analysis (when available)
    - Trade size distribution
    - Time between trades
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Analysis parameters
        self.volume_threshold_multiplier = 2.0  # Volume spike threshold
        self.price_impact_threshold = 0.001  # 0.1% price impact threshold
        self.anomaly_confidence_threshold = 0.7
        
    async def analyze(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze market microstructure patterns
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with microstructure analysis results
        """
        try:
            analysis_results = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data_points': len(market_data),
                'anomalies_detected': False,
                'anomaly_details': {},
                'confidence': 0.0,
                'patterns': []
            }
            
            if market_data.empty:
                return analysis_results
            
            # 1. Order Flow Analysis
            order_flow_results = self._analyze_order_flow(market_data)
            analysis_results['order_flow'] = order_flow_results
            
            # 2. Price Impact Analysis
            price_impact_results = self._analyze_price_impact(market_data)
            analysis_results['price_impact'] = price_impact_results
            
            # 3. Volume Distribution Analysis
            volume_distribution_results = self._analyze_volume_distribution(market_data)
            analysis_results['volume_distribution'] = volume_distribution_results
            
            # 4. Time-based Microstructure Analysis
            time_microstructure_results = self._analyze_time_microstructure(market_data)
            analysis_results['time_microstructure'] = time_microstructure_results
            
            # 5. Market Maker Behavior Analysis
            market_maker_results = self._analyze_market_maker_behavior(market_data)
            analysis_results['market_maker_behavior'] = market_maker_results
            
            # 6. Detect anomalies
            anomalies = self._detect_microstructure_anomalies(analysis_results)
            analysis_results['anomalies_detected'] = len(anomalies) > 0
            analysis_results['anomaly_details'] = anomalies
            
            # 7. Calculate overall confidence based on whether patterns were found
            if analysis_results['anomalies_detected']:
                analysis_results['confidence'] = self._calculate_analysis_confidence(analysis_results)
            else:
                analysis_results['confidence'] = 0.0
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Market microstructure analysis failed: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _analyze_order_flow(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze order flow patterns
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Order flow analysis results
        """
        try:
            results = {
                'buying_pressure': 0.0,
                'selling_pressure': 0.0,
                'net_flow': 0.0,
                'flow_imbalance': 0.0,
                'patterns': []
            }
            
            if 'close' not in market_data.columns or 'volume' not in market_data.columns:
                return results
            
            # Calculate price changes
            market_data = market_data.copy()
            market_data['price_change'] = market_data['close'].pct_change()
            market_data['volume_weighted_price'] = market_data['close'] * market_data['volume']
            
            # Analyze buying vs selling pressure
            positive_changes = market_data[market_data['price_change'] > 0]
            negative_changes = market_data[market_data['price_change'] < 0]
            
            if not positive_changes.empty:
                results['buying_pressure'] = positive_changes['volume'].sum()
            
            if not negative_changes.empty:
                results['selling_pressure'] = negative_changes['volume'].sum()
            
            # Calculate net flow
            total_volume = market_data['volume'].sum()
            if total_volume > 0:
                results['net_flow'] = (results['buying_pressure'] - results['selling_pressure']) / total_volume
                results['flow_imbalance'] = abs(results['net_flow'])
            
            # Detect flow patterns
            if results['flow_imbalance'] > 0.3:
                results['patterns'].append({
                    'type': 'flow_imbalance',
                    'severity': 'high' if results['flow_imbalance'] > 0.5 else 'medium',
                    'direction': 'buying' if results['net_flow'] > 0 else 'selling',
                    'magnitude': results['flow_imbalance']
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Order flow analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_price_impact(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze price impact of volume
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Price impact analysis results
        """
        try:
            results = {
                'average_price_impact': 0.0,
                'max_price_impact': 0.0,
                'volume_price_correlation': 0.0,
                'high_impact_trades': 0,
                'patterns': []
            }
            
            if 'close' not in market_data.columns or 'volume' not in market_data.columns:
                return results
            
            # Calculate price changes and volume
            market_data = market_data.copy()
            market_data['price_change'] = market_data['close'].pct_change().abs()
            market_data['volume_normalized'] = market_data['volume'] / market_data['volume'].mean()
            
            # Calculate price impact
            results['average_price_impact'] = market_data['price_change'].mean()
            results['max_price_impact'] = market_data['price_change'].max()
            
            # Calculate volume-price correlation
            if len(market_data) > 1:
                correlation = market_data['volume_normalized'].corr(market_data['price_change'])
                results['volume_price_correlation'] = correlation if not np.isnan(correlation) else 0.0
            
            # Count high impact trades
            high_impact_threshold = results['average_price_impact'] * self.volume_threshold_multiplier
            results['high_impact_trades'] = len(market_data[market_data['price_change'] > high_impact_threshold])
            
            # Detect patterns
            if results['volume_price_correlation'] > 0.5:
                results['patterns'].append({
                    'type': 'strong_volume_price_correlation',
                    'severity': 'high' if results['volume_price_correlation'] > 0.7 else 'medium',
                    'correlation': results['volume_price_correlation']
                })
            
            if results['high_impact_trades'] > len(market_data) * 0.1:  # More than 10% high impact
                results['patterns'].append({
                    'type': 'frequent_high_impact_trades',
                    'severity': 'high',
                    'count': results['high_impact_trades'],
                    'percentage': results['high_impact_trades'] / len(market_data) * 100
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Price impact analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_volume_distribution(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze volume distribution patterns
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Volume distribution analysis results
        """
        try:
            results = {
                'volume_mean': 0.0,
                'volume_std': 0.0,
                'volume_skewness': 0.0,
                'volume_kurtosis': 0.0,
                'large_trade_percentage': 0.0,
                'patterns': []
            }
            
            if 'volume' not in market_data.columns:
                return results
            
            volume_data = market_data['volume']
            
            # Basic statistics
            results['volume_mean'] = volume_data.mean()
            results['volume_std'] = volume_data.std()
            
            # Calculate skewness and kurtosis
            if len(volume_data) > 3:
                results['volume_skewness'] = volume_data.skew()
                results['volume_kurtosis'] = volume_data.kurtosis()
            
            # Large trade analysis
            large_trade_threshold = results['volume_mean'] + 2 * results['volume_std']
            large_trades = volume_data[volume_data > large_trade_threshold]
            results['large_trade_percentage'] = len(large_trades) / len(volume_data) * 100
            
            # Detect patterns
            if results['volume_skewness'] > 2.0:
                results['patterns'].append({
                    'type': 'right_skewed_volume',
                    'severity': 'high' if results['volume_skewness'] > 3.0 else 'medium',
                    'skewness': results['volume_skewness']
                })
            
            if results['volume_kurtosis'] > 5.0:
                results['patterns'].append({
                    'type': 'high_kurtosis_volume',
                    'severity': 'high' if results['volume_kurtosis'] > 10.0 else 'medium',
                    'kurtosis': results['volume_kurtosis']
                })
            
            if results['large_trade_percentage'] > 5.0:
                results['patterns'].append({
                    'type': 'frequent_large_trades',
                    'severity': 'high' if results['large_trade_percentage'] > 10.0 else 'medium',
                    'percentage': results['large_trade_percentage']
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Volume distribution analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_time_microstructure(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze time-based microstructure patterns
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Time microstructure analysis results
        """
        try:
            results = {
                'trading_frequency': 0.0,
                'time_between_trades': 0.0,
                'trading_intensity': 0.0,
                'patterns': []
            }
            
            if 'timestamp' not in market_data.columns:
                return results
            
            # Calculate time differences
            market_data = market_data.copy()
            market_data['timestamp'] = pd.to_datetime(market_data['timestamp'])
            market_data = market_data.sort_values('timestamp')
            
            time_diffs = market_data['timestamp'].diff().dt.total_seconds()
            time_diffs = time_diffs.dropna()
            
            if not time_diffs.empty:
                results['trading_frequency'] = 1.0 / time_diffs.mean() if time_diffs.mean() > 0 else 0.0
                results['time_between_trades'] = time_diffs.mean()
                results['trading_intensity'] = len(market_data) / (time_diffs.sum() / 3600)  # trades per hour
            
            # Detect patterns
            if results['trading_intensity'] > 100:  # More than 100 trades per hour
                results['patterns'].append({
                    'type': 'high_trading_intensity',
                    'severity': 'high' if results['trading_intensity'] > 500 else 'medium',
                    'intensity': results['trading_intensity']
                })
            
            # Check for clustering
            if len(time_diffs) > 10:
                time_std = time_diffs.std()
                time_mean = time_diffs.mean()
                if time_std > time_mean * 2:  # High variability
                    results['patterns'].append({
                        'type': 'irregular_trading_pattern',
                        'severity': 'medium',
                        'variability': time_std / time_mean
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Time microstructure analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_market_maker_behavior(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze potential market maker behavior patterns
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Market maker behavior analysis results
        """
        try:
            results = {
                'price_stability': 0.0,
                'volume_consistency': 0.0,
                'spread_analysis': 0.0,
                'market_making_likelihood': 0.0,
                'patterns': []
            }
            
            if 'close' not in market_data.columns or 'volume' not in market_data.columns:
                return results
            
            # Price stability analysis
            price_changes = market_data['close'].pct_change().abs()
            results['price_stability'] = 1.0 - price_changes.mean()  # Higher = more stable
            
            # Volume consistency analysis
            volume_cv = market_data['volume'].std() / market_data['volume'].mean()
            results['volume_consistency'] = 1.0 / (1.0 + volume_cv)  # Higher = more consistent
            
            # Simple spread analysis (using high-low if available)
            if 'high' in market_data.columns and 'low' in market_data.columns:
                spreads = (market_data['high'] - market_data['low']) / market_data['close']
                results['spread_analysis'] = spreads.mean()
            
            # Market making likelihood (simple heuristic)
            results['market_making_likelihood'] = (
                results['price_stability'] * 0.4 +
                results['volume_consistency'] * 0.4 +
                (1.0 - results['spread_analysis']) * 0.2  # Lower spreads = more likely market making
            )
            
            # Detect patterns
            if results['market_making_likelihood'] > 0.7:
                results['patterns'].append({
                    'type': 'potential_market_making',
                    'severity': 'high' if results['market_making_likelihood'] > 0.8 else 'medium',
                    'likelihood': results['market_making_likelihood']
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Market maker behavior analysis failed: {e}")
            return {'error': str(e)}
    
    def _detect_microstructure_anomalies(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect microstructure anomalies from analysis results
        
        Args:
            analysis_results: Complete microstructure analysis results
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        try:
            # Check for order flow anomalies
            order_flow = analysis_results.get('order_flow', {})
            if order_flow.get('flow_imbalance', 0) > 0.5:
                anomalies.append({
                    'type': 'extreme_flow_imbalance',
                    'severity': 'high',
                    'details': {
                        'imbalance': order_flow['flow_imbalance'],
                        'net_flow': order_flow['net_flow']
                    },
                    'confidence': 0.8
                })
            
            # Check for price impact anomalies
            price_impact = analysis_results.get('price_impact', {})
            if price_impact.get('max_price_impact', 0) > self.price_impact_threshold * 10:
                anomalies.append({
                    'type': 'extreme_price_impact',
                    'severity': 'high',
                    'details': {
                        'max_impact': price_impact['max_price_impact'],
                        'high_impact_trades': price_impact['high_impact_trades']
                    },
                    'confidence': 0.7
                })
            
            # Check for volume distribution anomalies
            volume_dist = analysis_results.get('volume_distribution', {})
            if volume_dist.get('large_trade_percentage', 0) > 15.0:
                anomalies.append({
                    'type': 'excessive_large_trades',
                    'severity': 'high',
                    'details': {
                        'large_trade_percentage': volume_dist['large_trade_percentage'],
                        'volume_skewness': volume_dist['volume_skewness']
                    },
                    'confidence': 0.6
                })
            
            # Check for trading intensity anomalies
            time_micro = analysis_results.get('time_microstructure', {})
            if time_micro.get('trading_intensity', 0) > 1000:  # Very high intensity
                anomalies.append({
                    'type': 'extreme_trading_intensity',
                    'severity': 'high',
                    'details': {
                        'trading_intensity': time_micro['trading_intensity'],
                        'trading_frequency': time_micro['trading_frequency']
                    },
                    'confidence': 0.7
                })
            
        except Exception as e:
            self.logger.error(f"Anomaly detection failed: {e}")
        
        return anomalies
    
    def _calculate_analysis_confidence(self, analysis_results: Dict[str, Any]) -> float:
        """
        Calculate confidence in the analysis results
        
        Args:
            analysis_results: Complete analysis results
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            confidence_factors = []
            
            # Data quality factor
            data_points = analysis_results.get('data_points', 0)
            if data_points > 100:
                confidence_factors.append(0.9)
            elif data_points > 50:
                confidence_factors.append(0.7)
            elif data_points > 20:
                confidence_factors.append(0.5)
            else:
                confidence_factors.append(0.3)
            
            # Analysis completeness factor
            analysis_components = ['order_flow', 'price_impact', 'volume_distribution', 'time_microstructure', 'market_maker_behavior']
            completed_analyses = sum(1 for component in analysis_components if component in analysis_results)
            completeness_confidence = completed_analyses / len(analysis_components)
            confidence_factors.append(completeness_confidence)
            
            # Anomaly consistency factor
            anomalies = analysis_results.get('anomaly_details', [])
            if len(anomalies) > 0:
                # Higher confidence if multiple anomalies point to same issue
                anomaly_types = [anomaly.get('type', '') for anomaly in anomalies]
                unique_types = len(set(anomaly_types))
                consistency_confidence = min(0.9, 0.5 + (len(anomalies) - unique_types) * 0.1)
                confidence_factors.append(consistency_confidence)
            else:
                confidence_factors.append(0.8)  # High confidence in "no anomalies" result
            
            # Calculate weighted average
            return sum(confidence_factors) / len(confidence_factors)
            
        except Exception as e:
            self.logger.error(f"Confidence calculation failed: {e}")
            return 0.5  # Default confidence
    
    async def configure(self, configuration: Dict[str, Any]) -> bool:
        """
        Configure the microstructure analyzer with LLM-determined parameters
        
        Args:
            configuration: Configuration parameters from LLM
            
        Returns:
            True if configuration successful
        """
        try:
            # Update configurable parameters
            if 'order_flow_threshold' in configuration:
                self.order_flow_threshold = max(0.1, min(2.0, configuration['order_flow_threshold']))
                self.logger.info(f"Updated order_flow_threshold to {self.order_flow_threshold}")
            
            if 'price_impact_sensitivity' in configuration:
                self.price_impact_sensitivity = max(0.1, min(1.0, configuration['price_impact_sensitivity']))
                self.logger.info(f"Updated price_impact_sensitivity to {self.price_impact_sensitivity}")
            
            # Update other parameters if provided
            if 'volume_distribution_threshold' in configuration:
                self.volume_distribution_threshold = max(0.1, min(1.0, configuration['volume_distribution_threshold']))
                self.logger.info(f"Updated volume_distribution_threshold to {self.volume_distribution_threshold}")
            
            if 'anomaly_threshold' in configuration:
                self.anomaly_threshold = max(1.5, min(5.0, configuration['anomaly_threshold']))
                self.logger.info(f"Updated anomaly_threshold to {self.anomaly_threshold}")
            
            self.logger.info(f"Successfully configured MarketMicrostructureAnalyzer with {len(configuration)} parameters")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure MarketMicrostructureAnalyzer: {e}")
            return False
    
    def get_configurable_parameters(self) -> Dict[str, Any]:
        """
        Get current configurable parameters
        
        Returns:
            Dictionary of current parameter values
        """
        return {
            'order_flow_threshold': self.order_flow_threshold,
            'price_impact_sensitivity': self.price_impact_sensitivity,
            'volume_distribution_threshold': self.volume_distribution_threshold,
            'anomaly_threshold': self.anomaly_threshold
        }
