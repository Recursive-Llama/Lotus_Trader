"""
Cross-Asset Pattern Analyzer

Analyzes cross-asset patterns and correlations in raw OHLCV data to detect
market-wide movements, sector rotations, and cross-asset arbitrage opportunities.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import logging
from scipy.stats import pearsonr, spearmanr


class CrossAssetPatternAnalyzer:
    """
    Analyzes cross-asset patterns and correlations
    
    Focuses on:
    - Cross-asset correlations
    - Market-wide movements
    - Sector rotation patterns
    - Cross-asset arbitrage opportunities
    - Correlation breakdowns
    - Cross-asset momentum patterns
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Analysis parameters
        self.correlation_threshold = 0.7  # Strong correlation threshold
        self.correlation_breakdown_threshold = 0.3  # Significant breakdown threshold
        self.momentum_window = 20  # Window for momentum analysis
        self.arbitrage_threshold = 0.02  # 2% arbitrage opportunity threshold
        
    async def analyze(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze cross-asset patterns
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with cross-asset analysis results
        """
        try:
            analysis_results = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data_points': len(market_data),
                'significant_correlation': False,
                'correlation_details': {},
                'confidence': 0.0,
                'patterns': []
            }
            
            if market_data.empty or 'symbol' not in market_data.columns:
                return analysis_results
            
            # 1. Cross-Asset Correlation Analysis
            correlation_results = self._analyze_cross_asset_correlations(market_data)
            analysis_results['cross_asset_correlations'] = correlation_results
            
            # 2. Market-Wide Movement Analysis
            market_wide_results = self._analyze_market_wide_movements(market_data)
            analysis_results['market_wide_movements'] = market_wide_results
            
            # 3. Sector Rotation Analysis
            sector_rotation_results = self._analyze_sector_rotation(market_data)
            analysis_results['sector_rotation'] = sector_rotation_results
            
            # 4. Cross-Asset Arbitrage Analysis
            arbitrage_results = self._analyze_cross_asset_arbitrage(market_data)
            analysis_results['cross_asset_arbitrage'] = arbitrage_results
            
            # 5. Correlation Breakdown Analysis
            breakdown_results = self._analyze_correlation_breakdowns(market_data)
            analysis_results['correlation_breakdowns'] = breakdown_results
            
            # 6. Cross-Asset Momentum Analysis
            momentum_results = self._analyze_cross_asset_momentum(market_data)
            analysis_results['cross_asset_momentum'] = momentum_results
            
            # 7. Detect significant patterns
            significant_patterns = self._identify_significant_cross_asset_patterns(analysis_results)
            analysis_results['significant_correlation'] = len(significant_patterns) > 0
            analysis_results['correlation_details'] = significant_patterns
            
            # 8. Calculate overall confidence based on whether patterns were found
            if analysis_results['significant_correlation']:
                analysis_results['confidence'] = self._calculate_cross_asset_analysis_confidence(analysis_results)
            else:
                analysis_results['confidence'] = 0.0
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Cross-asset pattern analysis failed: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _analyze_cross_asset_correlations(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze correlations between different assets
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Cross-asset correlation analysis results
        """
        try:
            results = {
                'correlation_matrix': {},
                'strong_correlations': [],
                'weak_correlations': [],
                'correlation_strength': 'weak',
                'patterns': []
            }
            
            # Get unique symbols
            symbols = market_data['symbol'].unique()
            
            if len(symbols) < 2:
                return results
            
            # Calculate price correlations
            if 'close' in market_data.columns:
                # Pivot data to get price matrix
                price_matrix = market_data.pivot(index='timestamp', columns='symbol', values='close')
                price_matrix = price_matrix.dropna()
                
                if len(price_matrix) > 1:
                    # Calculate correlation matrix
                    correlation_matrix = price_matrix.corr()
                    results['correlation_matrix'] = correlation_matrix.to_dict()
                    
                    # Find strong and weak correlations
                    for i, symbol1 in enumerate(symbols):
                        for j, symbol2 in enumerate(symbols):
                            if i < j:  # Avoid duplicates
                                correlation = correlation_matrix.loc[symbol1, symbol2]
                                
                                if not pd.isna(correlation):
                                    if abs(correlation) > self.correlation_threshold:
                                        results['strong_correlations'].append({
                                            'symbol1': symbol1,
                                            'symbol2': symbol2,
                                            'correlation': correlation,
                                            'strength': 'strong'
                                        })
                                    elif abs(correlation) < 0.3:
                                        results['weak_correlations'].append({
                                            'symbol1': symbol1,
                                            'symbol2': symbol2,
                                            'correlation': correlation,
                                            'strength': 'weak'
                                        })
                    
                    # Determine overall correlation strength
                    strong_count = len(results['strong_correlations'])
                    total_pairs = len(symbols) * (len(symbols) - 1) // 2
                    
                    if strong_count > total_pairs * 0.5:
                        results['correlation_strength'] = 'strong'
                    elif strong_count > total_pairs * 0.2:
                        results['correlation_strength'] = 'moderate'
                    else:
                        results['correlation_strength'] = 'weak'
                    
                    # Detect patterns
                    if results['correlation_strength'] == 'strong':
                        results['patterns'].append({
                            'type': 'high_cross_asset_correlation',
                            'strength': results['correlation_strength'],
                            'strong_pairs': len(results['strong_correlations'])
                        })
            
            # Calculate volume correlations
            if 'volume' in market_data.columns:
                volume_matrix = market_data.pivot(index='timestamp', columns='symbol', values='volume')
                volume_matrix = volume_matrix.dropna()
                
                if len(volume_matrix) > 1:
                    volume_correlation_matrix = volume_matrix.corr()
                    
                    # Check for volume correlation patterns
                    volume_correlations = []
                    for i, symbol1 in enumerate(symbols):
                        for j, symbol2 in enumerate(symbols):
                            if i < j:
                                vol_correlation = volume_correlation_matrix.loc[symbol1, symbol2]
                                if not pd.isna(vol_correlation) and abs(vol_correlation) > 0.5:
                                    volume_correlations.append({
                                        'symbol1': symbol1,
                                        'symbol2': symbol2,
                                        'volume_correlation': vol_correlation
                                    })
                    
                    if volume_correlations:
                        results['patterns'].append({
                            'type': 'volume_correlation_pattern',
                            'volume_correlations': volume_correlations
                        })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Cross-asset correlation analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_market_wide_movements(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze market-wide movements across all assets
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Market-wide movement analysis results
        """
        try:
            results = {
                'market_direction': 'neutral',
                'market_strength': 0.0,
                'unanimous_movements': 0,
                'divergent_movements': 0,
                'market_volatility': 0.0,
                'patterns': []
            }
            
            if 'close' not in market_data.columns:
                return results
            
            # Calculate price changes for each symbol
            market_data = market_data.copy()
            market_data['price_change'] = market_data.groupby('symbol')['close'].pct_change()
            
            # Group by timestamp to analyze market-wide movements
            market_movements = market_data.groupby('timestamp')['price_change'].agg(['mean', 'std', 'count'])
            market_movements = market_movements.dropna()
            
            if len(market_movements) > 0:
                # Determine market direction
                avg_movement = market_movements['mean'].mean()
                if avg_movement > 0.001:  # 0.1% threshold
                    results['market_direction'] = 'bullish'
                elif avg_movement < -0.001:
                    results['market_direction'] = 'bearish'
                else:
                    results['market_direction'] = 'neutral'
                
                # Calculate market strength
                results['market_strength'] = abs(avg_movement)
                
                # Calculate market volatility
                results['market_volatility'] = market_movements['std'].mean()
                
                # Count unanimous and divergent movements
                for timestamp, row in market_movements.iterrows():
                    timestamp_data = market_data[market_data['timestamp'] == timestamp]
                    price_changes = timestamp_data['price_change'].dropna()
                    
                    if len(price_changes) > 1:
                        # Check if all movements are in same direction
                        positive_moves = (price_changes > 0).sum()
                        negative_moves = (price_changes < 0).sum()
                        
                        if positive_moves == len(price_changes) or negative_moves == len(price_changes):
                            results['unanimous_movements'] += 1
                        elif positive_moves > 0 and negative_moves > 0:
                            results['divergent_movements'] += 1
                
                # Detect patterns
                if results['market_strength'] > 0.005:  # 0.5% threshold
                    results['patterns'].append({
                        'type': 'strong_market_movement',
                        'direction': results['market_direction'],
                        'strength': results['market_strength']
                    })
                
                if results['unanimous_movements'] > len(market_movements) * 0.3:
                    results['patterns'].append({
                        'type': 'frequent_unanimous_movements',
                        'count': results['unanimous_movements'],
                        'percentage': results['unanimous_movements'] / len(market_movements) * 100
                    })
                
                if results['divergent_movements'] > len(market_movements) * 0.5:
                    results['patterns'].append({
                        'type': 'frequent_divergent_movements',
                        'count': results['divergent_movements'],
                        'percentage': results['divergent_movements'] / len(market_movements) * 100
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Market-wide movement analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_sector_rotation(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze sector rotation patterns (if applicable)
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Sector rotation analysis results
        """
        try:
            results = {
                'sector_performance': {},
                'rotation_detected': False,
                'rotation_direction': 'neutral',
                'patterns': []
            }
            
            # For crypto, we can group by market cap or type
            # This is a simplified approach - in practice, you'd have proper sector classification
            
            if 'close' not in market_data.columns:
                return results
            
            # Group symbols by type (simplified sector classification)
            symbol_groups = {
                'major_crypto': ['BTC', 'ETH'],  # Major cryptocurrencies
                'altcoins': [],  # Other cryptocurrencies
                'defi': [],  # DeFi tokens
                'layer1': ['SOL', 'ADA', 'DOT'],  # Layer 1 blockchains
                'layer2': []  # Layer 2 solutions
            }
            
            # Classify symbols
            symbols = market_data['symbol'].unique()
            for symbol in symbols:
                if symbol in symbol_groups['major_crypto']:
                    continue  # Already classified
                elif symbol in symbol_groups['layer1']:
                    continue  # Already classified
                else:
                    symbol_groups['altcoins'].append(symbol)
            
            # Analyze performance by group
            market_data = market_data.copy()
            market_data['price_change'] = market_data.groupby('symbol')['close'].pct_change()
            
            for group_name, group_symbols in symbol_groups.items():
                if group_symbols:
                    group_data = market_data[market_data['symbol'].isin(group_symbols)]
                    if not group_data.empty:
                        group_performance = group_data['price_change'].mean()
                        group_volatility = group_data['price_change'].std()
                        
                        results['sector_performance'][group_name] = {
                            'performance': group_performance,
                            'volatility': group_volatility,
                            'symbol_count': len(group_symbols),
                            'data_points': len(group_data)
                        }
            
            # Detect rotation
            if len(results['sector_performance']) > 1:
                performances = {group: stats['performance'] for group, stats in results['sector_performance'].items()}
                best_performer = max(performances.items(), key=lambda x: x[1])
                worst_performer = min(performances.items(), key=lambda x: x[1])
                
                performance_spread = best_performer[1] - worst_performer[1]
                
                if performance_spread > 0.01:  # 1% spread threshold
                    results['rotation_detected'] = True
                    results['rotation_direction'] = f"from_{worst_performer[0]}_to_{best_performer[0]}"
                    
                    results['patterns'].append({
                        'type': 'sector_rotation',
                        'direction': results['rotation_direction'],
                        'spread': performance_spread,
                        'best_performer': best_performer,
                        'worst_performer': worst_performer
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Sector rotation analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_cross_asset_arbitrage(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze cross-asset arbitrage opportunities
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Cross-asset arbitrage analysis results
        """
        try:
            results = {
                'arbitrage_opportunities': [],
                'price_ratios': {},
                'arbitrage_potential': 0.0,
                'patterns': []
            }
            
            if 'close' not in market_data.columns:
                return results
            
            symbols = market_data['symbol'].unique()
            
            if len(symbols) < 2:
                return results
            
            # Calculate price ratios between assets
            price_matrix = market_data.pivot(index='timestamp', columns='symbol', values='close')
            price_matrix = price_matrix.dropna()
            
            if len(price_matrix) > 0:
                # Calculate ratios between major pairs
                major_pairs = [('BTC', 'ETH'), ('BTC', 'SOL'), ('ETH', 'SOL')]
                
                for pair in major_pairs:
                    if pair[0] in price_matrix.columns and pair[1] in price_matrix.columns:
                        ratio = price_matrix[pair[0]] / price_matrix[pair[1]]
                        ratio_mean = ratio.mean()
                        ratio_std = ratio.std()
                        
                        results['price_ratios'][f"{pair[0]}/{pair[1]}"] = {
                            'mean': ratio_mean,
                            'std': ratio_std,
                            'current': ratio.iloc[-1] if len(ratio) > 0 else 0
                        }
                        
                        # Check for arbitrage opportunities
                        if ratio_std > 0:
                            # Calculate z-score of current ratio
                            z_score = abs((ratio.iloc[-1] - ratio_mean) / ratio_std)
                            
                            if z_score > 2.0:  # 2 standard deviations from mean
                                arbitrage_potential = abs(ratio.iloc[-1] - ratio_mean) / ratio_mean
                                
                                if arbitrage_potential > self.arbitrage_threshold:
                                    results['arbitrage_opportunities'].append({
                                        'pair': f"{pair[0]}/{pair[1]}",
                                        'current_ratio': ratio.iloc[-1],
                                        'mean_ratio': ratio_mean,
                                        'arbitrage_potential': arbitrage_potential,
                                        'z_score': z_score,
                                        'direction': 'buy_' + pair[0] + '_sell_' + pair[1] if ratio.iloc[-1] > ratio_mean else 'buy_' + pair[1] + '_sell_' + pair[0]
                                    })
                
                # Calculate overall arbitrage potential
                if results['arbitrage_opportunities']:
                    results['arbitrage_potential'] = max([opp['arbitrage_potential'] for opp in results['arbitrage_opportunities']])
                    
                    results['patterns'].append({
                        'type': 'arbitrage_opportunities',
                        'count': len(results['arbitrage_opportunities']),
                        'max_potential': results['arbitrage_potential']
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Cross-asset arbitrage analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_correlation_breakdowns(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze correlation breakdowns and regime changes
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Correlation breakdown analysis results
        """
        try:
            results = {
                'breakdowns_detected': 0,
                'breakdown_details': [],
                'regime_changes': 0,
                'patterns': []
            }
            
            if 'close' not in market_data.columns:
                return results
            
            symbols = market_data['symbol'].unique()
            
            if len(symbols) < 2:
                return results
            
            # Calculate rolling correlations
            price_matrix = market_data.pivot(index='timestamp', columns='symbol', values='close')
            price_matrix = price_matrix.dropna()
            
            if len(price_matrix) > 50:  # Need sufficient data for rolling analysis
                # Calculate rolling correlation for major pairs
                major_pairs = [('BTC', 'ETH'), ('BTC', 'SOL'), ('ETH', 'SOL')]
                
                for pair in major_pairs:
                    if pair[0] in price_matrix.columns and pair[1] in price_matrix.columns:
                        # Calculate rolling correlation
                        rolling_corr = price_matrix[pair[0]].rolling(window=20).corr(price_matrix[pair[1]])
                        
                        # Detect correlation breakdowns
                        recent_corr = rolling_corr.tail(10).mean()
                        historical_corr = rolling_corr.head(20).mean()
                        
                        if not pd.isna(recent_corr) and not pd.isna(historical_corr):
                            correlation_change = abs(recent_corr - historical_corr)
                            
                            if correlation_change > self.correlation_breakdown_threshold:
                                results['breakdowns_detected'] += 1
                                results['breakdown_details'].append({
                                    'pair': f"{pair[0]}/{pair[1]}",
                                    'historical_correlation': historical_corr,
                                    'recent_correlation': recent_corr,
                                    'change': correlation_change,
                                    'direction': 'increasing' if recent_corr > historical_corr else 'decreasing'
                                })
                
                # Detect regime changes
                if results['breakdowns_detected'] > 0:
                    results['regime_changes'] = 1  # Simplified - in practice, you'd use more sophisticated regime detection
                    
                    results['patterns'].append({
                        'type': 'correlation_breakdown',
                        'count': results['breakdowns_detected'],
                        'details': results['breakdown_details']
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Correlation breakdown analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_cross_asset_momentum(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze cross-asset momentum patterns
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Cross-asset momentum analysis results
        """
        try:
            results = {
                'momentum_rankings': {},
                'momentum_divergence': 0.0,
                'momentum_patterns': [],
                'patterns': []
            }
            
            if 'close' not in market_data.columns:
                return results
            
            symbols = market_data['symbol'].unique()
            
            if len(symbols) < 2:
                return results
            
            # Calculate momentum for each symbol
            market_data = market_data.copy()
            market_data['price_change'] = market_data.groupby('symbol')['close'].pct_change()
            
            # Calculate rolling momentum
            momentum_data = market_data.groupby('symbol')['price_change'].rolling(
                window=self.momentum_window
            ).mean().reset_index(level=0, drop=True)
            
            # Get recent momentum for each symbol
            recent_momentum = {}
            for symbol in symbols:
                symbol_data = market_data[market_data['symbol'] == symbol]
                if len(symbol_data) >= self.momentum_window:
                    recent_momentum[symbol] = symbol_data['price_change'].tail(self.momentum_window).mean()
            
            # Rank by momentum
            if recent_momentum:
                sorted_momentum = sorted(recent_momentum.items(), key=lambda x: x[1], reverse=True)
                results['momentum_rankings'] = {symbol: rank for rank, (symbol, _) in enumerate(sorted_momentum, 1)}
                
                # Calculate momentum divergence
                momentum_values = list(recent_momentum.values())
                if len(momentum_values) > 1:
                    results['momentum_divergence'] = max(momentum_values) - min(momentum_values)
                
                # Detect momentum patterns
                if results['momentum_divergence'] > 0.01:  # 1% divergence threshold
                    results['momentum_patterns'].append({
                        'type': 'momentum_divergence',
                        'divergence': results['momentum_divergence'],
                        'top_performer': sorted_momentum[0][0],
                        'bottom_performer': sorted_momentum[-1][0]
                    })
                
                # Check for momentum clustering
                positive_momentum = sum(1 for momentum in momentum_values if momentum > 0)
                negative_momentum = sum(1 for momentum in momentum_values if momentum < 0)
                
                if positive_momentum > len(momentum_values) * 0.7:
                    results['momentum_patterns'].append({
                        'type': 'positive_momentum_cluster',
                        'positive_count': positive_momentum,
                        'total_count': len(momentum_values)
                    })
                elif negative_momentum > len(momentum_values) * 0.7:
                    results['momentum_patterns'].append({
                        'type': 'negative_momentum_cluster',
                        'negative_count': negative_momentum,
                        'total_count': len(momentum_values)
                    })
                
                # Add patterns to results
                results['patterns'] = results['momentum_patterns']
            
            return results
            
        except Exception as e:
            self.logger.error(f"Cross-asset momentum analysis failed: {e}")
            return {'error': str(e)}
    
    def _identify_significant_cross_asset_patterns(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify significant cross-asset patterns from analysis results
        
        Args:
            analysis_results: Complete cross-asset analysis results
            
        Returns:
            List of significant cross-asset patterns
        """
        significant_patterns = []
        
        try:
            # Check for strong correlations
            correlations = analysis_results.get('cross_asset_correlations', {})
            if correlations.get('correlation_strength') == 'strong':
                significant_patterns.append({
                    'type': 'strong_cross_asset_correlation',
                    'severity': 'high',
                    'strength': correlations.get('correlation_strength'),
                    'strong_pairs': len(correlations.get('strong_correlations', [])),
                    'details': correlations,
                    'confidence': 0.8
                })
            
            # Check for market-wide movements
            market_wide = analysis_results.get('market_wide_movements', {})
            if market_wide.get('market_strength', 0) > 0.01:  # 1% threshold
                significant_patterns.append({
                    'type': 'strong_market_wide_movement',
                    'severity': 'high' if market_wide.get('market_strength', 0) > 0.02 else 'medium',
                    'direction': market_wide.get('market_direction', 'neutral'),
                    'strength': market_wide.get('market_strength', 0),
                    'details': market_wide,
                    'confidence': 0.7
                })
            
            # Check for sector rotation
            sector_rotation = analysis_results.get('sector_rotation', {})
            if sector_rotation.get('rotation_detected'):
                significant_patterns.append({
                    'type': 'sector_rotation_detected',
                    'severity': 'medium',
                    'direction': sector_rotation.get('rotation_direction', 'neutral'),
                    'details': sector_rotation,
                    'confidence': 0.6
                })
            
            # Check for arbitrage opportunities
            arbitrage = analysis_results.get('cross_asset_arbitrage', {})
            if arbitrage.get('arbitrage_potential', 0) > 0.05:  # 5% threshold
                significant_patterns.append({
                    'type': 'significant_arbitrage_opportunity',
                    'severity': 'high',
                    'potential': arbitrage.get('arbitrage_potential', 0),
                    'opportunities': len(arbitrage.get('arbitrage_opportunities', [])),
                    'details': arbitrage,
                    'confidence': 0.8
                })
            
            # Check for correlation breakdowns
            breakdowns = analysis_results.get('correlation_breakdowns', {})
            if breakdowns.get('breakdowns_detected', 0) > 0:
                significant_patterns.append({
                    'type': 'correlation_breakdown_detected',
                    'severity': 'high' if breakdowns.get('breakdowns_detected', 0) > 2 else 'medium',
                    'breakdown_count': breakdowns.get('breakdowns_detected', 0),
                    'details': breakdowns,
                    'confidence': 0.7
                })
            
            # Check for momentum divergence
            momentum = analysis_results.get('cross_asset_momentum', {})
            if momentum.get('momentum_divergence', 0) > 0.02:  # 2% divergence threshold
                significant_patterns.append({
                    'type': 'significant_momentum_divergence',
                    'severity': 'high' if momentum.get('momentum_divergence', 0) > 0.05 else 'medium',
                    'divergence': momentum.get('momentum_divergence', 0),
                    'details': momentum,
                    'confidence': 0.6
                })
            
        except Exception as e:
            self.logger.error(f"Failed to identify significant cross-asset patterns: {e}")
        
        return significant_patterns
    
    def _calculate_cross_asset_analysis_confidence(self, analysis_results: Dict[str, Any]) -> float:
        """
        Calculate confidence in the cross-asset analysis results
        
        Args:
            analysis_results: Complete cross-asset analysis results
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            confidence_factors = []
            
            # Data quality factor
            data_points = analysis_results.get('data_points', 0)
            if data_points > 1000:  # Need more data for cross-asset analysis
                confidence_factors.append(0.9)
            elif data_points > 500:
                confidence_factors.append(0.7)
            elif data_points > 200:
                confidence_factors.append(0.5)
            else:
                confidence_factors.append(0.3)
            
            # Analysis completeness factor
            analysis_components = ['cross_asset_correlations', 'market_wide_movements', 'sector_rotation', 
                                 'cross_asset_arbitrage', 'correlation_breakdowns', 'cross_asset_momentum']
            completed_analyses = sum(1 for component in analysis_components if component in analysis_results)
            completeness_confidence = completed_analyses / len(analysis_components)
            confidence_factors.append(completeness_confidence)
            
            # Pattern consistency factor
            significant_patterns = analysis_results.get('correlation_details', [])
            if len(significant_patterns) > 0:
                # Higher confidence if patterns are consistent across different analysis types
                pattern_types = [pattern.get('type', '') for pattern in significant_patterns]
                unique_types = len(set(pattern_types))
                consistency_confidence = min(0.9, 0.5 + (len(significant_patterns) - unique_types) * 0.1)
                confidence_factors.append(consistency_confidence)
            else:
                confidence_factors.append(0.8)  # High confidence in "no significant patterns" result
            
            # Calculate weighted average
            return sum(confidence_factors) / len(confidence_factors)
            
        except Exception as e:
            self.logger.error(f"Cross-asset analysis confidence calculation failed: {e}")
            return 0.5  # Default confidence
    
    async def configure(self, configuration: Dict[str, Any]) -> bool:
        """
        Configure the cross-asset analyzer with LLM-determined parameters
        
        Args:
            configuration: Configuration parameters from LLM
            
        Returns:
            True if configuration successful
        """
        try:
            # Update configurable parameters
            if 'correlation_threshold' in configuration:
                self.correlation_threshold = max(0.3, min(0.95, configuration['correlation_threshold']))
                self.logger.info(f"Updated correlation_threshold to {self.correlation_threshold}")
            
            if 'arbitrage_sensitivity' in configuration:
                self.arbitrage_sensitivity = max(0.1, min(2.0, configuration['arbitrage_sensitivity']))
                self.logger.info(f"Updated arbitrage_sensitivity to {self.arbitrage_sensitivity}")
            
            # Update other parameters if provided
            if 'correlation_window' in configuration:
                self.correlation_window = max(10, min(200, configuration['correlation_window']))
                self.logger.info(f"Updated correlation_window to {self.correlation_window}")
            
            if 'anomaly_threshold' in configuration:
                self.anomaly_threshold = max(1.5, min(5.0, configuration['anomaly_threshold']))
                self.logger.info(f"Updated anomaly_threshold to {self.anomaly_threshold}")
            
            self.logger.info(f"Successfully configured CrossAssetPatternAnalyzer with {len(configuration)} parameters")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure CrossAssetPatternAnalyzer: {e}")
            return False
    
    def get_configurable_parameters(self) -> Dict[str, Any]:
        """
        Get current configurable parameters
        
        Returns:
            Dictionary of current parameter values
        """
        return {
            'correlation_threshold': self.correlation_threshold,
            'arbitrage_sensitivity': self.arbitrage_sensitivity,
            'correlation_window': self.correlation_window,
            'anomaly_threshold': self.anomaly_threshold
        }
