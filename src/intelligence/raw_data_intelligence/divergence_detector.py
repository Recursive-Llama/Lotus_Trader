"""
Raw Data Divergence Detector

Detects divergences at the raw data level, focusing on fundamental price-volume,
price-momentum, and cross-asset divergences that traditional indicators might miss.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import logging


class RawDataDivergenceDetector:
    """
    Detects divergences at the raw data level
    
    Focuses on:
    - Price-Volume Divergences
    - Price-Momentum Divergences  
    - Cross-Asset Divergences
    - Time-Based Divergences
    - Market Microstructure Divergences
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Analysis parameters
        self.divergence_threshold = 0.1  # 10% threshold for divergence detection
        self.momentum_window = 14  # Window for momentum calculation
        self.volume_threshold = 1.5  # Volume threshold multiplier
        self.correlation_threshold = 0.7  # Correlation threshold for cross-asset analysis
        
        # Configurable parameters for LLM control
        self.lookback_period = 20  # Lookback period for divergence detection
        self.smoothing_factor = 0.3  # Smoothing factor for price/volume data
        self.threshold = 0.1  # Divergence threshold
        
    async def analyze(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze raw data divergences
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with divergence analysis results
        """
        try:
            analysis_results = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data_points': len(market_data),
                'divergences_detected': 0,
                'divergence_details': [],
                'confidence': 0.0,
                'patterns': []
            }
            
            if market_data.empty:
                return analysis_results
            
            # 1. Price-Volume Divergence Analysis
            price_volume_results = self._analyze_price_volume_divergences(market_data)
            analysis_results['price_volume_divergences'] = price_volume_results
            
            # 2. Price-Momentum Divergence Analysis
            price_momentum_results = self._analyze_price_momentum_divergences(market_data)
            analysis_results['price_momentum_divergences'] = price_momentum_results
            
            # 3. Cross-Asset Divergence Analysis
            cross_asset_results = self._analyze_cross_asset_divergences(market_data)
            analysis_results['cross_asset_divergences'] = cross_asset_results
            
            # 4. Time-Based Divergence Analysis
            time_based_results = self._analyze_time_based_divergences(market_data)
            analysis_results['time_based_divergences'] = time_based_results
            
            # 5. Market Microstructure Divergence Analysis
            microstructure_results = self._analyze_microstructure_divergences(market_data)
            analysis_results['microstructure_divergences'] = microstructure_results
            
            # 6. Detect significant divergences
            significant_divergences = self._identify_significant_divergences(analysis_results)
            analysis_results['divergences_detected'] = len(significant_divergences)
            analysis_results['divergence_details'] = significant_divergences
            
            # 7. Calculate pattern clarity and confidence
            analysis_results['pattern_clarity'] = self._calculate_divergence_pattern_clarity(analysis_results)
            
            # 8. Set confidence based on whether patterns were found
            if analysis_results['divergences_detected'] > 0:
                analysis_results['confidence'] = analysis_results['pattern_clarity']
            else:
                analysis_results['confidence'] = 0.0
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Raw data divergence analysis failed: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _analyze_price_volume_divergences(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze price-volume divergences
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Price-volume divergence analysis results
        """
        try:
            results = {
                'divergences_found': 0,
                'divergence_details': [],
                'patterns': []
            }
            
            if 'close' not in market_data.columns or 'volume' not in market_data.columns:
                return results
            
            # Calculate price and volume changes
            market_data = market_data.copy()
            market_data['price_change'] = market_data['close'].pct_change()
            market_data['volume_change'] = market_data['volume'].pct_change()
            
            # Calculate rolling averages for smoothing
            market_data['price_ma'] = market_data['price_change'].rolling(window=5).mean()
            market_data['volume_ma'] = market_data['volume_change'].rolling(window=5).mean()
            
            # Detect divergences
            for i in range(10, len(market_data)):  # Need enough data for comparison
                current_price = market_data['price_ma'].iloc[i]
                current_volume = market_data['volume_ma'].iloc[i]
                
                # Look back for comparison
                lookback_start = max(0, i - 10)
                lookback_end = i - 1
                
                if lookback_end > lookback_start:
                    lookback_price = market_data['price_ma'].iloc[lookback_start:lookback_end]
                    lookback_volume = market_data['volume_ma'].iloc[lookback_start:lookback_end]
                    
                    # Calculate trends
                    price_trend = lookback_price.mean()
                    volume_trend = lookback_volume.mean()
                    
                    # Detect bullish divergence (price down, volume up)
                    if (current_price < price_trend * 0.9 and 
                        current_volume > volume_trend * 1.1):
                        results['divergences_found'] += 1
                        results['divergence_details'].append({
                            'type': 'bullish_price_volume_divergence',
                            'timestamp': market_data.index[i] if hasattr(market_data.index, 'iloc') else i,
                            'price_change': current_price,
                            'volume_change': current_volume,
                            'price_trend': price_trend,
                            'volume_trend': volume_trend,
                            'strength': abs(current_price - price_trend) + abs(current_volume - volume_trend),
                            'confidence': min(1.0, abs(current_price - price_trend) / abs(price_trend) + 
                                            abs(current_volume - volume_trend) / abs(volume_trend))
                        })
                    
                    # Detect bearish divergence (price up, volume down)
                    elif (current_price > price_trend * 1.1 and 
                          current_volume < volume_trend * 0.9):
                        results['divergences_found'] += 1
                        results['divergence_details'].append({
                            'type': 'bearish_price_volume_divergence',
                            'timestamp': market_data.index[i] if hasattr(market_data.index, 'iloc') else i,
                            'price_change': current_price,
                            'volume_change': current_volume,
                            'price_trend': price_trend,
                            'volume_trend': volume_trend,
                            'strength': abs(current_price - price_trend) + abs(current_volume - volume_trend),
                            'confidence': min(1.0, abs(current_price - price_trend) / abs(price_trend) + 
                                            abs(current_volume - volume_trend) / abs(volume_trend))
                        })
            
            # Detect patterns
            if results['divergences_found'] > 0:
                bullish_divs = [d for d in results['divergence_details'] if 'bullish' in d['type']]
                bearish_divs = [d for d in results['divergence_details'] if 'bearish' in d['type']]
                
                if len(bullish_divs) > len(bearish_divs):
                    results['patterns'].append({
                        'type': 'predominantly_bullish_divergences',
                        'bullish_count': len(bullish_divs),
                        'bearish_count': len(bearish_divs)
                    })
                elif len(bearish_divs) > len(bullish_divs):
                    results['patterns'].append({
                        'type': 'predominantly_bearish_divergences',
                        'bullish_count': len(bullish_divs),
                        'bearish_count': len(bearish_divs)
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Price-volume divergence analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_price_momentum_divergences(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze price-momentum divergences
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Price-momentum divergence analysis results
        """
        try:
            results = {
                'divergences_found': 0,
                'divergence_details': [],
                'patterns': []
            }
            
            if 'close' not in market_data.columns:
                return results
            
            # Calculate price momentum
            market_data = market_data.copy()
            market_data['price_momentum'] = market_data['close'].pct_change(periods=self.momentum_window)
            market_data['price_change'] = market_data['close'].pct_change()
            
            # Calculate rolling averages
            market_data['momentum_ma'] = market_data['price_momentum'].rolling(window=5).mean()
            market_data['price_ma'] = market_data['price_change'].rolling(window=5).mean()
            
            # Detect divergences
            for i in range(self.momentum_window + 10, len(market_data)):
                current_momentum = market_data['momentum_ma'].iloc[i]
                current_price = market_data['price_ma'].iloc[i]
                
                # Look back for comparison
                lookback_start = max(0, i - 10)
                lookback_end = i - 1
                
                if lookback_end > lookback_start:
                    lookback_momentum = market_data['momentum_ma'].iloc[lookback_start:lookback_end]
                    lookback_price = market_data['price_ma'].iloc[lookback_start:lookback_end]
                    
                    # Calculate trends
                    momentum_trend = lookback_momentum.mean()
                    price_trend = lookback_price.mean()
                    
                    # Detect bullish divergence (price down, momentum up)
                    if (current_price < price_trend * 0.9 and 
                        current_momentum > momentum_trend * 1.1):
                        results['divergences_found'] += 1
                        results['divergence_details'].append({
                            'type': 'bullish_price_momentum_divergence',
                            'timestamp': market_data.index[i] if hasattr(market_data.index, 'iloc') else i,
                            'price_change': current_price,
                            'momentum': current_momentum,
                            'price_trend': price_trend,
                            'momentum_trend': momentum_trend,
                            'strength': abs(current_price - price_trend) + abs(current_momentum - momentum_trend),
                            'confidence': min(1.0, abs(current_price - price_trend) / abs(price_trend) + 
                                            abs(current_momentum - momentum_trend) / abs(momentum_trend))
                        })
                    
                    # Detect bearish divergence (price up, momentum down)
                    elif (current_price > price_trend * 1.1 and 
                          current_momentum < momentum_trend * 0.9):
                        results['divergences_found'] += 1
                        results['divergence_details'].append({
                            'type': 'bearish_price_momentum_divergence',
                            'timestamp': market_data.index[i] if hasattr(market_data.index, 'iloc') else i,
                            'price_change': current_price,
                            'momentum': current_momentum,
                            'price_trend': price_trend,
                            'momentum_trend': momentum_trend,
                            'strength': abs(current_price - price_trend) + abs(current_momentum - momentum_trend),
                            'confidence': min(1.0, abs(current_price - price_trend) / abs(price_trend) + 
                                            abs(current_momentum - momentum_trend) / abs(momentum_trend))
                        })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Price-momentum divergence analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_cross_asset_divergences(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze cross-asset divergences
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Cross-asset divergence analysis results
        """
        try:
            results = {
                'divergences_found': 0,
                'divergence_details': [],
                'patterns': []
            }
            
            if 'symbol' not in market_data.columns or 'close' not in market_data.columns:
                return results
            
            symbols = market_data['symbol'].unique()
            
            if len(symbols) < 2:
                return results
            
            # Calculate price changes for each symbol
            market_data = market_data.copy()
            market_data['price_change'] = market_data.groupby('symbol')['close'].pct_change()
            
            # Group by timestamp to analyze cross-asset movements
            timestamp_groups = market_data.groupby('timestamp')
            
            for timestamp, group in timestamp_groups:
                if len(group) >= 2:  # Need at least 2 symbols
                    price_changes = group.set_index('symbol')['price_change'].dropna()
                    
                    if len(price_changes) >= 2:
                        # Calculate correlation between symbols
                        symbol_pairs = []
                        for i, symbol1 in enumerate(price_changes.index):
                            for j, symbol2 in enumerate(price_changes.index):
                                if i < j:
                                    symbol_pairs.append((symbol1, symbol2))
                        
                        # Check for divergences in symbol pairs
                        for symbol1, symbol2 in symbol_pairs:
                            change1 = price_changes[symbol1]
                            change2 = price_changes[symbol2]
                            
                            # Calculate expected correlation (simplified)
                            if abs(change1) > 0.01 and abs(change2) > 0.01:  # Significant moves
                                # Check if moves are in opposite directions when they should be correlated
                                if (change1 > 0 and change2 < 0) or (change1 < 0 and change2 > 0):
                                    # This could be a divergence if these assets are normally correlated
                                    results['divergences_found'] += 1
                                    results['divergence_details'].append({
                                        'type': 'cross_asset_divergence',
                                        'timestamp': timestamp,
                                        'symbol1': symbol1,
                                        'symbol2': symbol2,
                                        'change1': change1,
                                        'change2': change2,
                                        'divergence_strength': abs(change1) + abs(change2),
                                        'confidence': min(1.0, (abs(change1) + abs(change2)) / 0.1)  # Normalize
                                    })
            
            # Detect patterns
            if results['divergences_found'] > 0:
                # Group by symbol pairs
                symbol_pair_divergences = {}
                for div in results['divergence_details']:
                    pair = tuple(sorted([div['symbol1'], div['symbol2']]))
                    if pair not in symbol_pair_divergences:
                        symbol_pair_divergences[pair] = 0
                    symbol_pair_divergences[pair] += 1
                
                # Find most frequent diverging pairs
                if symbol_pair_divergences:
                    most_frequent_pair = max(symbol_pair_divergences.items(), key=lambda x: x[1])
                    results['patterns'].append({
                        'type': 'frequent_cross_asset_divergence',
                        'symbol_pair': most_frequent_pair[0],
                        'divergence_count': most_frequent_pair[1]
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Cross-asset divergence analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_time_based_divergences(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze time-based divergences
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Time-based divergence analysis results
        """
        try:
            results = {
                'divergences_found': 0,
                'divergence_details': [],
                'patterns': []
            }
            
            if 'timestamp' not in market_data.columns or 'close' not in market_data.columns:
                return results
            
            # Extract time components
            market_data = market_data.copy()
            market_data['timestamp'] = pd.to_datetime(market_data['timestamp'])
            market_data['hour'] = market_data['timestamp'].dt.hour
            market_data['day_of_week'] = market_data['timestamp'].dt.dayofweek
            
            # Calculate price changes
            market_data['price_change'] = market_data['close'].pct_change()
            
            # Analyze hourly patterns
            hourly_stats = market_data.groupby('hour')['price_change'].agg(['mean', 'std', 'count'])
            
            # Find hours with unusual patterns
            overall_mean = market_data['price_change'].mean()
            overall_std = market_data['price_change'].std()
            
            for hour, stats in hourly_stats.iterrows():
                if stats['count'] > 5:  # Need enough data
                    hour_mean = stats['mean']
                    hour_std = stats['std']
                    
                    # Check for significant deviation from overall pattern
                    if abs(hour_mean - overall_mean) > overall_std * 2:
                        results['divergences_found'] += 1
                        results['divergence_details'].append({
                            'type': 'hourly_price_divergence',
                            'hour': hour,
                            'hour_mean': hour_mean,
                            'overall_mean': overall_mean,
                            'deviation': abs(hour_mean - overall_mean),
                            'confidence': min(1.0, abs(hour_mean - overall_mean) / overall_std)
                        })
            
            # Analyze day-of-week patterns
            dow_stats = market_data.groupby('day_of_week')['price_change'].agg(['mean', 'std', 'count'])
            
            for dow, stats in dow_stats.iterrows():
                if stats['count'] > 10:  # Need enough data
                    dow_mean = stats['mean']
                    
                    # Check for significant deviation from overall pattern
                    if abs(dow_mean - overall_mean) > overall_std * 1.5:
                        results['divergences_found'] += 1
                        results['divergence_details'].append({
                            'type': 'day_of_week_price_divergence',
                            'day_of_week': dow,
                            'dow_mean': dow_mean,
                            'overall_mean': overall_mean,
                            'deviation': abs(dow_mean - overall_mean),
                            'confidence': min(1.0, abs(dow_mean - overall_mean) / overall_std)
                        })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Time-based divergence analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_microstructure_divergences(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze market microstructure divergences
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Microstructure divergence analysis results
        """
        try:
            results = {
                'divergences_found': 0,
                'divergence_details': [],
                'patterns': []
            }
            
            if 'close' not in market_data.columns or 'volume' not in market_data.columns:
                return results
            
            # Calculate microstructure metrics
            market_data = market_data.copy()
            market_data['price_change'] = market_data['close'].pct_change()
            market_data['volume_change'] = market_data['volume'].pct_change()
            
            # Calculate price impact (price change per unit volume)
            market_data['price_impact'] = market_data['price_change'] / (market_data['volume_change'] + 1e-8)
            
            # Calculate rolling averages
            market_data['price_impact_ma'] = market_data['price_impact'].rolling(window=10).mean()
            market_data['volume_ma'] = market_data['volume'].rolling(window=10).mean()
            
            # Detect microstructure divergences
            for i in range(20, len(market_data)):
                current_impact = market_data['price_impact_ma'].iloc[i]
                current_volume = market_data['volume_ma'].iloc[i]
                
                # Look back for comparison
                lookback_start = max(0, i - 20)
                lookback_end = i - 1
                
                if lookback_end > lookback_start:
                    lookback_impact = market_data['price_impact_ma'].iloc[lookback_start:lookback_end]
                    lookback_volume = market_data['volume_ma'].iloc[lookback_start:lookback_end]
                    
                    # Calculate trends
                    impact_trend = lookback_impact.mean()
                    volume_trend = lookback_volume.mean()
                    
                    # Detect unusual price impact patterns
                    if abs(current_impact - impact_trend) > abs(impact_trend) * 2:
                        results['divergences_found'] += 1
                        results['divergence_details'].append({
                            'type': 'microstructure_price_impact_divergence',
                            'timestamp': market_data.index[i] if hasattr(market_data.index, 'iloc') else i,
                            'current_impact': current_impact,
                            'impact_trend': impact_trend,
                            'current_volume': current_volume,
                            'volume_trend': volume_trend,
                            'divergence_strength': abs(current_impact - impact_trend),
                            'confidence': min(1.0, abs(current_impact - impact_trend) / abs(impact_trend))
                        })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Microstructure divergence analysis failed: {e}")
            return {'error': str(e)}
    
    def _identify_significant_divergences(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify significant divergences from analysis results
        
        Args:
            analysis_results: Complete divergence analysis results
            
        Returns:
            List of significant divergences
        """
        significant_divergences = []
        
        try:
            # Check price-volume divergences
            price_volume = analysis_results.get('price_volume_divergences', {})
            for div in price_volume.get('divergence_details', []):
                if div.get('confidence', 0) > 0.7:  # High confidence threshold
                    significant_divergences.append({
                        'type': div['type'],
                        'severity': 'high' if div.get('confidence', 0) > 0.8 else 'medium',
                        'confidence': div.get('confidence', 0),
                        'strength': div.get('strength', 0),
                        'details': div
                    })
            
            # Check price-momentum divergences
            price_momentum = analysis_results.get('price_momentum_divergences', {})
            for div in price_momentum.get('divergence_details', []):
                if div.get('confidence', 0) > 0.7:
                    significant_divergences.append({
                        'type': div['type'],
                        'severity': 'high' if div.get('confidence', 0) > 0.8 else 'medium',
                        'confidence': div.get('confidence', 0),
                        'strength': div.get('strength', 0),
                        'details': div
                    })
            
            # Check cross-asset divergences
            cross_asset = analysis_results.get('cross_asset_divergences', {})
            for div in cross_asset.get('divergence_details', []):
                if div.get('confidence', 0) > 0.6:  # Lower threshold for cross-asset
                    significant_divergences.append({
                        'type': div['type'],
                        'severity': 'high' if div.get('confidence', 0) > 0.8 else 'medium',
                        'confidence': div.get('confidence', 0),
                        'strength': div.get('divergence_strength', 0),
                        'details': div
                    })
            
            # Check time-based divergences
            time_based = analysis_results.get('time_based_divergences', {})
            for div in time_based.get('divergence_details', []):
                if div.get('confidence', 0) > 0.6:
                    significant_divergences.append({
                        'type': div['type'],
                        'severity': 'medium',  # Time-based divergences are typically medium severity
                        'confidence': div.get('confidence', 0),
                        'strength': div.get('deviation', 0),
                        'details': div
                    })
            
            # Check microstructure divergences
            microstructure = analysis_results.get('microstructure_divergences', {})
            for div in microstructure.get('divergence_details', []):
                if div.get('confidence', 0) > 0.7:
                    significant_divergences.append({
                        'type': div['type'],
                        'severity': 'high' if div.get('confidence', 0) > 0.8 else 'medium',
                        'confidence': div.get('confidence', 0),
                        'strength': div.get('divergence_strength', 0),
                        'details': div
                    })
            
        except Exception as e:
            self.logger.error(f"Failed to identify significant divergences: {e}")
        
        return significant_divergences
    
    def _calculate_divergence_pattern_clarity(self, analysis_results: Dict[str, Any]) -> float:
        """
        Calculate pattern clarity (statistical strength) of divergence patterns
        
        Args:
            analysis_results: Complete divergence analysis results
            
        Returns:
            Pattern clarity score between 0.0 and 1.0
        """
        try:
            clarity_factors = []
            
            # Data quality factor
            data_points = analysis_results.get('data_points', 0)
            if data_points > 100:
                clarity_factors.append(0.9)
            elif data_points > 50:
                clarity_factors.append(0.7)
            elif data_points > 20:
                clarity_factors.append(0.5)
            else:
                clarity_factors.append(0.3)
            
            # Analysis completeness factor
            analysis_components = ['price_volume_divergences', 'price_momentum_divergences', 
                                 'cross_asset_divergences', 'time_based_divergences', 'microstructure_divergences']
            completed_analyses = sum(1 for component in analysis_components if component in analysis_results)
            completeness_clarity = completed_analyses / len(analysis_components)
            clarity_factors.append(completeness_clarity)
            
            # Divergence consistency factor
            significant_divergences = analysis_results.get('divergence_details', [])
            if len(significant_divergences) > 0:
                # Higher clarity if divergences are consistent across different types
                divergence_types = [div.get('type', '') for div in significant_divergences]
                unique_types = len(set(divergence_types))
                consistency_clarity = min(0.9, 0.5 + (len(significant_divergences) - unique_types) * 0.1)
                clarity_factors.append(consistency_clarity)
            else:
                clarity_factors.append(0.8)  # High clarity in "no significant divergences" result
            
            # Calculate weighted average
            return sum(clarity_factors) / len(clarity_factors)
            
        except Exception as e:
            self.logger.error(f"Divergence pattern clarity calculation failed: {e}")
            return 0.5  # Default clarity
    
    async def configure(self, configuration: Dict[str, Any]) -> bool:
        """
        Configure the divergence detector with LLM-determined parameters
        
        Args:
            configuration: Configuration parameters from LLM
            
        Returns:
            True if configuration successful
        """
        try:
            # Update configurable parameters
            if 'lookback_period' in configuration:
                self.lookback_period = max(5, min(100, configuration['lookback_period']))
                self.logger.info(f"Updated lookback_period to {self.lookback_period}")
            
            if 'threshold' in configuration:
                self.threshold = max(0.01, min(0.5, configuration['threshold']))
                self.divergence_threshold = self.threshold  # Sync with main threshold
                self.logger.info(f"Updated threshold to {self.threshold}")
            
            if 'smoothing_factor' in configuration:
                self.smoothing_factor = max(0.1, min(1.0, configuration['smoothing_factor']))
                self.logger.info(f"Updated smoothing_factor to {self.smoothing_factor}")
            
            # Update other parameters if provided
            if 'momentum_window' in configuration:
                self.momentum_window = max(5, min(50, configuration['momentum_window']))
                self.logger.info(f"Updated momentum_window to {self.momentum_window}")
            
            if 'volume_threshold' in configuration:
                self.volume_threshold = max(1.0, min(5.0, configuration['volume_threshold']))
                self.logger.info(f"Updated volume_threshold to {self.volume_threshold}")
            
            if 'correlation_threshold' in configuration:
                self.correlation_threshold = max(0.3, min(0.95, configuration['correlation_threshold']))
                self.logger.info(f"Updated correlation_threshold to {self.correlation_threshold}")
            
            self.logger.info(f"Successfully configured RawDataDivergenceDetector with {len(configuration)} parameters")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure RawDataDivergenceDetector: {e}")
            return False
    
    def get_configurable_parameters(self) -> Dict[str, Any]:
        """
        Get current configurable parameters
        
        Returns:
            Dictionary of current parameter values
        """
        return {
            'lookback_period': self.lookback_period,
            'threshold': self.threshold,
            'smoothing_factor': self.smoothing_factor,
            'momentum_window': self.momentum_window,
            'volume_threshold': self.volume_threshold,
            'correlation_threshold': self.correlation_threshold
        }
    
    def adjust_sensitivity(self, sensitivity: float) -> bool:
        """
        Adjust overall sensitivity of divergence detection
        
        Args:
            sensitivity: Sensitivity factor (0.1 = very sensitive, 2.0 = less sensitive)
            
        Returns:
            True if adjustment successful
        """
        try:
            # Adjust threshold based on sensitivity
            self.threshold = max(0.01, min(0.5, 0.1 / sensitivity))
            self.divergence_threshold = self.threshold
            
            # Adjust volume threshold
            self.volume_threshold = max(1.0, min(5.0, 1.5 / sensitivity))
            
            self.logger.info(f"Adjusted sensitivity to {sensitivity}, new threshold: {self.threshold}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to adjust sensitivity: {e}")
            return False
