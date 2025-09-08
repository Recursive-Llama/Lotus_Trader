"""
Volume Pattern Analyzer

Analyzes volume patterns in raw OHLCV data to detect unusual volume spikes,
volume-price relationships, and volume-based market structure changes.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import logging
from scipy import stats


class VolumePatternAnalyzer:
    """
    Analyzes volume patterns in raw OHLCV data
    
    Focuses on:
    - Volume spikes and anomalies
    - Volume-price relationships
    - Volume trend analysis
    - Volume clustering patterns
    - Institutional vs retail volume patterns
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Analysis parameters
        self.volume_spike_threshold = 2.0  # Standard deviations above mean
        self.volume_trend_window = 20  # Window for trend analysis
        self.volume_cluster_threshold = 0.7  # Correlation threshold for clustering
        
    async def analyze(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze volume patterns
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with volume analysis results
        """
        try:
            analysis_results = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data_points': len(market_data),
                'significant_volume_spike': False,
                'spike_details': {},
                'confidence': 0.0,
                'patterns': []
            }
            
            if market_data.empty or 'volume' not in market_data.columns:
                return analysis_results
            
            # 1. Volume Spike Detection
            spike_results = self._detect_volume_spikes(market_data)
            analysis_results['volume_spikes'] = spike_results
            
            # 2. Volume-Price Relationship Analysis
            volume_price_results = self._analyze_volume_price_relationship(market_data)
            analysis_results['volume_price_relationship'] = volume_price_results
            
            # 3. Volume Trend Analysis
            volume_trend_results = self._analyze_volume_trends(market_data)
            analysis_results['volume_trends'] = volume_trend_results
            
            # 4. Volume Clustering Analysis
            volume_clustering_results = self._analyze_volume_clustering(market_data)
            analysis_results['volume_clustering'] = volume_clustering_results
            
            # 5. Volume Distribution Analysis
            volume_distribution_results = self._analyze_volume_distribution(market_data)
            analysis_results['volume_distribution'] = volume_distribution_results
            
            # 6. Institutional vs Retail Volume Analysis
            institutional_analysis = self._analyze_institutional_volume(market_data)
            analysis_results['institutional_volume'] = institutional_analysis
            
            # 7. Detect significant patterns
            significant_patterns = self._identify_significant_volume_patterns(analysis_results)
            analysis_results['significant_volume_spike'] = len(significant_patterns) > 0
            analysis_results['spike_details'] = significant_patterns
            
            # 8. Calculate overall confidence
            analysis_results['confidence'] = self._calculate_volume_analysis_confidence(analysis_results)
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Volume pattern analysis failed: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _detect_volume_spikes(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect volume spikes and anomalies
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Volume spike detection results
        """
        try:
            results = {
                'spikes_detected': 0,
                'spike_details': [],
                'average_volume': 0.0,
                'volume_std': 0.0,
                'max_volume': 0.0,
                'spike_threshold': 0.0
            }
            
            volume_data = market_data['volume']
            
            # Calculate basic statistics
            results['average_volume'] = volume_data.mean()
            results['volume_std'] = volume_data.std()
            results['max_volume'] = volume_data.max()
            
            # Calculate spike threshold
            results['spike_threshold'] = results['average_volume'] + (self.volume_spike_threshold * results['volume_std'])
            
            # Detect spikes
            spikes = volume_data[volume_data > results['spike_threshold']]
            results['spikes_detected'] = len(spikes)
            
            # Analyze each spike
            for idx, volume in spikes.items():
                spike_magnitude = (volume - results['average_volume']) / results['volume_std']
                
                # Get price context for the spike
                price_context = {}
                if 'close' in market_data.columns:
                    price_context['price_at_spike'] = market_data.loc[idx, 'close']
                    if idx > 0:
                        price_context['price_change'] = market_data.loc[idx, 'close'] - market_data.loc[idx-1, 'close']
                
                # Get timestamp context
                timestamp_context = {}
                if 'timestamp' in market_data.columns:
                    timestamp_context['spike_time'] = market_data.loc[idx, 'timestamp']
                
                results['spike_details'].append({
                    'index': idx,
                    'volume': volume,
                    'magnitude': spike_magnitude,
                    'severity': 'high' if spike_magnitude > 3.0 else 'medium' if spike_magnitude > 2.0 else 'low',
                    'price_context': price_context,
                    'timestamp_context': timestamp_context
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Volume spike detection failed: {e}")
            return {'error': str(e)}
    
    def _analyze_volume_price_relationship(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze relationship between volume and price movements
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Volume-price relationship analysis results
        """
        try:
            results = {
                'correlation': 0.0,
                'correlation_strength': 'weak',
                'volume_price_patterns': [],
                'confirmation_rate': 0.0
            }
            
            if 'close' not in market_data.columns or 'volume' not in market_data.columns:
                return results
            
            # Calculate price changes
            market_data = market_data.copy()
            market_data['price_change'] = market_data['close'].pct_change()
            market_data['price_change_abs'] = market_data['price_change'].abs()
            
            # Calculate volume changes
            market_data['volume_change'] = market_data['volume'].pct_change()
            market_data['volume_change_abs'] = market_data['volume_change'].abs()
            
            # Calculate correlation
            valid_data = market_data.dropna()
            if len(valid_data) > 1:
                correlation = valid_data['volume_change_abs'].corr(valid_data['price_change_abs'])
                results['correlation'] = correlation if not np.isnan(correlation) else 0.0
                
                # Determine correlation strength
                if abs(results['correlation']) > 0.7:
                    results['correlation_strength'] = 'strong'
                elif abs(results['correlation']) > 0.4:
                    results['correlation_strength'] = 'moderate'
                else:
                    results['correlation_strength'] = 'weak'
            
            # Analyze volume-price confirmation patterns
            if len(valid_data) > 0:
                # Count cases where volume and price move in same direction
                same_direction = ((valid_data['volume_change'] > 0) & (valid_data['price_change'] > 0)) | \
                               ((valid_data['volume_change'] < 0) & (valid_data['price_change'] < 0))
                
                results['confirmation_rate'] = same_direction.sum() / len(valid_data)
                
                # Detect patterns
                if results['correlation'] > 0.5:
                    results['volume_price_patterns'].append({
                        'type': 'positive_volume_price_correlation',
                        'strength': results['correlation_strength'],
                        'correlation': results['correlation']
                    })
                
                if results['confirmation_rate'] > 0.6:
                    results['volume_price_patterns'].append({
                        'type': 'high_volume_price_confirmation',
                        'rate': results['confirmation_rate']
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Volume-price relationship analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_volume_trends(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze volume trends over time
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Volume trend analysis results
        """
        try:
            results = {
                'trend_direction': 'neutral',
                'trend_strength': 0.0,
                'trend_consistency': 0.0,
                'trend_breakpoints': [],
                'trend_patterns': []
            }
            
            if 'volume' not in market_data.columns:
                return results
            
            volume_data = market_data['volume']
            
            if len(volume_data) < self.volume_trend_window:
                return results
            
            # Calculate rolling averages
            short_window = min(5, len(volume_data) // 4)
            long_window = min(self.volume_trend_window, len(volume_data) // 2)
            
            short_ma = volume_data.rolling(window=short_window).mean()
            long_ma = volume_data.rolling(window=long_window).mean()
            
            # Determine trend direction
            recent_short = short_ma.iloc[-1] if not pd.isna(short_ma.iloc[-1]) else 0
            recent_long = long_ma.iloc[-1] if not pd.isna(long_ma.iloc[-1]) else 0
            
            if recent_short > recent_long * 1.05:
                results['trend_direction'] = 'increasing'
            elif recent_short < recent_long * 0.95:
                results['trend_direction'] = 'decreasing'
            else:
                results['trend_direction'] = 'neutral'
            
            # Calculate trend strength
            if recent_long > 0:
                results['trend_strength'] = abs(recent_short - recent_long) / recent_long
            
            # Calculate trend consistency
            ma_diff = short_ma - long_ma
            consistent_trend = (ma_diff > 0).sum() if results['trend_direction'] == 'increasing' else (ma_diff < 0).sum()
            results['trend_consistency'] = consistent_trend / len(ma_diff.dropna()) if len(ma_diff.dropna()) > 0 else 0
            
            # Detect trend breakpoints
            ma_diff_sign = np.sign(ma_diff)
            sign_changes = (ma_diff_sign != ma_diff_sign.shift()).sum()
            results['trend_breakpoints'] = sign_changes
            
            # Detect patterns
            if results['trend_strength'] > 0.2:
                results['trend_patterns'].append({
                    'type': 'strong_volume_trend',
                    'direction': results['trend_direction'],
                    'strength': results['trend_strength']
                })
            
            if results['trend_consistency'] > 0.8:
                results['trend_patterns'].append({
                    'type': 'consistent_volume_trend',
                    'direction': results['trend_direction'],
                    'consistency': results['trend_consistency']
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Volume trend analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_volume_clustering(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze volume clustering patterns
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Volume clustering analysis results
        """
        try:
            results = {
                'clusters_detected': 0,
                'cluster_details': [],
                'clustering_strength': 0.0,
                'cluster_patterns': []
            }
            
            if 'volume' not in market_data.columns or len(market_data) < 10:
                return results
            
            volume_data = market_data['volume']
            
            # Simple clustering based on volume percentiles
            q25, q50, q75 = volume_data.quantile([0.25, 0.5, 0.75])
            
            # Define clusters
            low_volume = volume_data[volume_data <= q25]
            medium_volume = volume_data[(volume_data > q25) & (volume_data <= q75)]
            high_volume = volume_data[volume_data > q75]
            
            results['clusters_detected'] = 3
            results['cluster_details'] = [
                {
                    'cluster': 'low',
                    'count': len(low_volume),
                    'percentage': len(low_volume) / len(volume_data) * 100,
                    'avg_volume': low_volume.mean()
                },
                {
                    'cluster': 'medium',
                    'count': len(medium_volume),
                    'percentage': len(medium_volume) / len(volume_data) * 100,
                    'avg_volume': medium_volume.mean()
                },
                {
                    'cluster': 'high',
                    'count': len(high_volume),
                    'percentage': len(high_volume) / len(volume_data) * 100,
                    'avg_volume': high_volume.mean()
                }
            ]
            
            # Calculate clustering strength (how well separated the clusters are)
            cluster_separation = (q75 - q25) / volume_data.std()
            results['clustering_strength'] = min(1.0, cluster_separation / 2.0)
            
            # Detect patterns
            if results['clustering_strength'] > 0.7:
                results['cluster_patterns'].append({
                    'type': 'strong_volume_clustering',
                    'strength': results['clustering_strength']
                })
            
            # Check for unusual cluster distribution
            high_volume_pct = len(high_volume) / len(volume_data) * 100
            if high_volume_pct > 30:  # More than 30% high volume
                results['cluster_patterns'].append({
                    'type': 'excessive_high_volume_cluster',
                    'percentage': high_volume_pct
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Volume clustering analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_volume_distribution(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze volume distribution characteristics
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Volume distribution analysis results
        """
        try:
            results = {
                'distribution_type': 'normal',
                'skewness': 0.0,
                'kurtosis': 0.0,
                'outliers': 0,
                'distribution_patterns': []
            }
            
            if 'volume' not in market_data.columns:
                return results
            
            volume_data = market_data['volume']
            
            # Calculate distribution statistics
            results['skewness'] = volume_data.skew()
            results['kurtosis'] = volume_data.kurtosis()
            
            # Determine distribution type
            if abs(results['skewness']) > 1.0:
                results['distribution_type'] = 'highly_skewed'
            elif abs(results['skewness']) > 0.5:
                results['distribution_type'] = 'moderately_skewed'
            else:
                results['distribution_type'] = 'approximately_normal'
            
            # Detect outliers using IQR method
            Q1 = volume_data.quantile(0.25)
            Q3 = volume_data.quantile(0.75)
            IQR = Q3 - Q1
            outlier_threshold = 1.5 * IQR
            outliers = volume_data[(volume_data < Q1 - outlier_threshold) | (volume_data > Q3 + outlier_threshold)]
            results['outliers'] = len(outliers)
            
            # Detect patterns
            if results['skewness'] > 2.0:
                results['distribution_patterns'].append({
                    'type': 'right_skewed_volume',
                    'skewness': results['skewness']
                })
            
            if results['kurtosis'] > 5.0:
                results['distribution_patterns'].append({
                    'type': 'high_kurtosis_volume',
                    'kurtosis': results['kurtosis']
                })
            
            if results['outliers'] > len(volume_data) * 0.1:  # More than 10% outliers
                results['distribution_patterns'].append({
                    'type': 'excessive_volume_outliers',
                    'outlier_count': results['outliers'],
                    'outlier_percentage': results['outliers'] / len(volume_data) * 100
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Volume distribution analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_institutional_volume(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze potential institutional vs retail volume patterns
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Institutional volume analysis results
        """
        try:
            results = {
                'institutional_likelihood': 0.0,
                'large_trade_percentage': 0.0,
                'volume_concentration': 0.0,
                'institutional_patterns': []
            }
            
            if 'volume' not in market_data.columns:
                return results
            
            volume_data = market_data['volume']
            
            # Calculate large trade percentage (trades above 2 standard deviations)
            volume_mean = volume_data.mean()
            volume_std = volume_data.std()
            large_trade_threshold = volume_mean + 2 * volume_std
            
            large_trades = volume_data[volume_data > large_trade_threshold]
            results['large_trade_percentage'] = len(large_trades) / len(volume_data) * 100
            
            # Calculate volume concentration (Gini coefficient approximation)
            sorted_volumes = volume_data.sort_values()
            n = len(sorted_volumes)
            if n > 1:
                cumsum = sorted_volumes.cumsum()
                results['volume_concentration'] = (n + 1 - 2 * sum((n + 1 - i) * y for i, y in enumerate(cumsum, 1)) / cumsum.iloc[-1]) / n
            
            # Calculate institutional likelihood (heuristic)
            results['institutional_likelihood'] = (
                min(1.0, results['large_trade_percentage'] / 20.0) * 0.4 +  # Large trades
                min(1.0, results['volume_concentration'] * 2.0) * 0.6  # Volume concentration
            )
            
            # Detect patterns
            if results['large_trade_percentage'] > 15:
                results['institutional_patterns'].append({
                    'type': 'high_large_trade_percentage',
                    'percentage': results['large_trade_percentage']
                })
            
            if results['volume_concentration'] > 0.6:
                results['institutional_patterns'].append({
                    'type': 'high_volume_concentration',
                    'concentration': results['volume_concentration']
                })
            
            if results['institutional_likelihood'] > 0.7:
                results['institutional_patterns'].append({
                    'type': 'likely_institutional_activity',
                    'likelihood': results['institutional_likelihood']
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Institutional volume analysis failed: {e}")
            return {'error': str(e)}
    
    def _identify_significant_volume_patterns(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify significant volume patterns from analysis results
        
        Args:
            analysis_results: Complete volume analysis results
            
        Returns:
            List of significant volume patterns
        """
        significant_patterns = []
        
        try:
            # Check for significant volume spikes
            volume_spikes = analysis_results.get('volume_spikes', {})
            if volume_spikes.get('spikes_detected', 0) > 0:
                for spike in volume_spikes.get('spike_details', []):
                    if spike.get('magnitude', 0) > 2.5:  # Significant spike
                        significant_patterns.append({
                            'type': 'volume_spike',
                            'severity': spike.get('severity', 'medium'),
                            'magnitude': spike.get('magnitude', 0),
                            'details': spike,
                            'confidence': 0.8
                        })
            
            # Check for strong volume-price correlation
            volume_price = analysis_results.get('volume_price_relationship', {})
            if volume_price.get('correlation', 0) > 0.6:
                significant_patterns.append({
                    'type': 'strong_volume_price_correlation',
                    'severity': 'high' if volume_price.get('correlation', 0) > 0.8 else 'medium',
                    'correlation': volume_price.get('correlation', 0),
                    'details': volume_price,
                    'confidence': 0.7
                })
            
            # Check for strong volume trends
            volume_trends = analysis_results.get('volume_trends', {})
            if volume_trends.get('trend_strength', 0) > 0.3:
                significant_patterns.append({
                    'type': 'strong_volume_trend',
                    'severity': 'high' if volume_trends.get('trend_strength', 0) > 0.5 else 'medium',
                    'direction': volume_trends.get('trend_direction', 'neutral'),
                    'strength': volume_trends.get('trend_strength', 0),
                    'details': volume_trends,
                    'confidence': 0.6
                })
            
            # Check for institutional activity
            institutional = analysis_results.get('institutional_volume', {})
            if institutional.get('institutional_likelihood', 0) > 0.7:
                significant_patterns.append({
                    'type': 'institutional_volume_activity',
                    'severity': 'high' if institutional.get('institutional_likelihood', 0) > 0.8 else 'medium',
                    'likelihood': institutional.get('institutional_likelihood', 0),
                    'details': institutional,
                    'confidence': 0.7
                })
            
        except Exception as e:
            self.logger.error(f"Failed to identify significant volume patterns: {e}")
        
        return significant_patterns
    
    def _calculate_volume_analysis_confidence(self, analysis_results: Dict[str, Any]) -> float:
        """
        Calculate confidence in the volume analysis results
        
        Args:
            analysis_results: Complete volume analysis results
            
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
            analysis_components = ['volume_spikes', 'volume_price_relationship', 'volume_trends', 
                                 'volume_clustering', 'volume_distribution', 'institutional_volume']
            completed_analyses = sum(1 for component in analysis_components if component in analysis_results)
            completeness_confidence = completed_analyses / len(analysis_components)
            confidence_factors.append(completeness_confidence)
            
            # Pattern consistency factor
            significant_patterns = analysis_results.get('spike_details', [])
            if len(significant_patterns) > 0:
                # Higher confidence if patterns are consistent
                pattern_types = [pattern.get('type', '') for pattern in significant_patterns]
                unique_types = len(set(pattern_types))
                consistency_confidence = min(0.9, 0.5 + (len(significant_patterns) - unique_types) * 0.1)
                confidence_factors.append(consistency_confidence)
            else:
                confidence_factors.append(0.8)  # High confidence in "no significant patterns" result
            
            # Calculate weighted average
            return sum(confidence_factors) / len(confidence_factors)
            
        except Exception as e:
            self.logger.error(f"Volume analysis confidence calculation failed: {e}")
            return 0.5  # Default confidence
    
    async def configure(self, configuration: Dict[str, Any]) -> bool:
        """
        Configure the volume analyzer with LLM-determined parameters
        
        Args:
            configuration: Configuration parameters from LLM
            
        Returns:
            True if configuration successful
        """
        try:
            # Update configurable parameters
            if 'volume_threshold' in configuration:
                self.volume_threshold = max(1.0, min(5.0, configuration['volume_threshold']))
                self.logger.info(f"Updated volume_threshold to {self.volume_threshold}")
            
            if 'spike_detection' in configuration:
                self.spike_detection = configuration['spike_detection']
                self.logger.info(f"Updated spike_detection to {self.spike_detection}")
            
            # Update other parameters if provided
            if 'volume_window' in configuration:
                self.volume_window = max(5, min(50, configuration['volume_window']))
                self.logger.info(f"Updated volume_window to {self.volume_window}")
            
            if 'anomaly_threshold' in configuration:
                self.anomaly_threshold = max(1.5, min(5.0, configuration['anomaly_threshold']))
                self.logger.info(f"Updated anomaly_threshold to {self.anomaly_threshold}")
            
            self.logger.info(f"Successfully configured VolumePatternAnalyzer with {len(configuration)} parameters")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure VolumePatternAnalyzer: {e}")
            return False
    
    def get_configurable_parameters(self) -> Dict[str, Any]:
        """
        Get current configurable parameters
        
        Returns:
            Dictionary of current parameter values
        """
        return {
            'volume_threshold': self.volume_threshold,
            'spike_detection': self.spike_detection,
            'volume_window': self.volume_window,
            'anomaly_threshold': self.anomaly_threshold
        }
