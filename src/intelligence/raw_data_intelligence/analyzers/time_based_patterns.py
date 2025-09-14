"""
Time-Based Pattern Detector

Analyzes time-based patterns in raw OHLCV data to detect intraday patterns,
session-based anomalies, and time-dependent market behavior.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
import logging


class TimeBasedPatternDetector:
    """
    Detects time-based patterns in raw OHLCV data
    
    Focuses on:
    - Intraday patterns (hourly, daily patterns)
    - Session-based analysis (Asian, European, US sessions)
    - Time-of-day effects
    - Day-of-week patterns
    - Market opening/closing effects
    - Time-based volatility patterns
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Analysis parameters
        self.session_threshold = 0.1  # 10% threshold for session analysis
        self.time_pattern_confidence_threshold = 0.6
        self.volatility_window = 20  # Window for volatility analysis
        
    async def analyze(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze time-based patterns
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with time-based pattern analysis results
        """
        try:
            analysis_results = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data_points': len(market_data),
                'significant_time_pattern': False,
                'pattern_details': {},
                'confidence': 0.0,
                'patterns': []
            }
            
            if market_data.empty or 'timestamp' not in market_data.columns:
                return analysis_results
            
            # Convert timestamp to datetime if needed
            market_data = market_data.copy()
            market_data['timestamp'] = pd.to_datetime(market_data['timestamp'])
            
            # 1. Intraday Pattern Analysis
            intraday_results = self._analyze_intraday_patterns(market_data)
            analysis_results['intraday_patterns'] = intraday_results
            
            # 2. Session-Based Analysis
            session_results = self._analyze_trading_sessions(market_data)
            analysis_results['trading_sessions'] = session_results
            
            # 3. Day-of-Week Analysis
            dow_results = self._analyze_day_of_week_patterns(market_data)
            analysis_results['day_of_week_patterns'] = dow_results
            
            # 4. Time-of-Day Effects
            tod_results = self._analyze_time_of_day_effects(market_data)
            analysis_results['time_of_day_effects'] = tod_results
            
            # 5. Market Opening/Closing Effects
            open_close_results = self._analyze_market_open_close_effects(market_data)
            analysis_results['open_close_effects'] = open_close_results
            
            # 6. Time-Based Volatility Analysis
            volatility_results = self._analyze_time_based_volatility(market_data)
            analysis_results['time_based_volatility'] = volatility_results
            
            # 7. Detect significant patterns
            significant_patterns = self._identify_significant_time_patterns(analysis_results)
            analysis_results['significant_time_pattern'] = len(significant_patterns) > 0
            analysis_results['pattern_details'] = significant_patterns
            
            # 8. Calculate overall confidence based on whether patterns were found
            if analysis_results['significant_time_pattern']:
                analysis_results['confidence'] = self._calculate_time_analysis_confidence(analysis_results)
            else:
                analysis_results['confidence'] = 0.0
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Time-based pattern analysis failed: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _analyze_intraday_patterns(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze intraday patterns (hourly patterns)
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Intraday pattern analysis results
        """
        try:
            results = {
                'hourly_patterns': {},
                'peak_hours': [],
                'low_activity_hours': [],
                'pattern_strength': 0.0,
                'patterns': []
            }
            
            # Extract hour from timestamp
            market_data['hour'] = market_data['timestamp'].dt.hour
            
            # Group by hour and analyze
            hourly_stats = market_data.groupby('hour').agg({
                'volume': ['mean', 'std', 'count'],
                'close': ['mean', 'std'] if 'close' in market_data.columns else ['mean']
            }).round(4)
            
            # Replace NaN values with 0
            hourly_stats = hourly_stats.fillna(0)
            
            # Flatten column names
            hourly_stats.columns = ['_'.join(col).strip() for col in hourly_stats.columns]
            
            # Calculate pattern strength with NaN handling
            if 'volume_mean' in hourly_stats.columns:
                volume_by_hour = hourly_stats['volume_mean']
                volume_std = volume_by_hour.std()
                volume_mean = volume_by_hour.mean()
                
                # Handle NaN values
                if np.isnan(volume_std):
                    volume_std = 0.0
                if np.isnan(volume_mean):
                    volume_mean = 0.0
                
                results['pattern_strength'] = volume_std / volume_mean if volume_mean > 0 else 0
                
                # Identify peak and low activity hours
                volume_threshold_high = volume_mean + volume_std
                volume_threshold_low = volume_mean - volume_std
                
                results['peak_hours'] = volume_by_hour[volume_by_hour > volume_threshold_high].index.tolist()
                results['low_activity_hours'] = volume_by_hour[volume_by_hour < volume_threshold_low].index.tolist()
            
            # Store hourly patterns
            results['hourly_patterns'] = hourly_stats.to_dict('index')
            
            # Detect patterns
            if results['pattern_strength'] > 0.3:
                results['patterns'].append({
                    'type': 'strong_intraday_pattern',
                    'strength': results['pattern_strength'],
                    'peak_hours': results['peak_hours'],
                    'low_hours': results['low_activity_hours']
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Intraday pattern analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_trading_sessions(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze trading session patterns (Asian, European, US)
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Trading session analysis results
        """
        try:
            results = {
                'session_analysis': {},
                'session_rankings': {},
                'session_patterns': []
            }
            
            # Define trading sessions (UTC times)
            sessions = {
                'asian': {'start': 0, 'end': 8},      # 00:00 - 08:00 UTC
                'european': {'start': 8, 'end': 16},   # 08:00 - 16:00 UTC
                'us': {'start': 16, 'end': 24}         # 16:00 - 24:00 UTC
            }
            
            # Extract hour from timestamp
            market_data['hour'] = market_data['timestamp'].dt.hour
            
            # Analyze each session
            for session_name, session_times in sessions.items():
                session_data = market_data[
                    (market_data['hour'] >= session_times['start']) & 
                    (market_data['hour'] < session_times['end'])
                ]
                
                if not session_data.empty:
                    # Calculate session stats with NaN handling
                    volume_mean = session_data['volume'].mean() if 'volume' in session_data.columns else 0
                    volume_std = session_data['volume'].std() if 'volume' in session_data.columns else 0
                    
                    # Handle NaN values
                    if np.isnan(volume_mean):
                        volume_mean = 0.0
                    if np.isnan(volume_std):
                        volume_std = 0.0
                    
                    session_stats = {
                        'data_points': len(session_data),
                        'volume_mean': volume_mean,
                        'volume_std': volume_std,
                        'price_volatility': 0.0
                    }
                    
                    # Calculate price volatility if close price available
                    if 'close' in session_data.columns:
                        price_changes = session_data['close'].pct_change().abs()
                        session_stats['price_volatility'] = price_changes.mean()
                    
                    results['session_analysis'][session_name] = session_stats
            
            # Rank sessions by activity
            if results['session_analysis']:
                volume_ranking = sorted(
                    results['session_analysis'].items(),
                    key=lambda x: x[1]['volume_mean'],
                    reverse=True
                )
                results['session_rankings']['by_volume'] = [item[0] for item in volume_ranking]
                
                volatility_ranking = sorted(
                    results['session_analysis'].items(),
                    key=lambda x: x[1]['price_volatility'],
                    reverse=True
                )
                results['session_rankings']['by_volatility'] = [item[0] for item in volatility_ranking]
            
            # Detect patterns
            if len(results['session_analysis']) > 1:
                volumes = [stats['volume_mean'] for stats in results['session_analysis'].values()]
                if volumes:
                    volume_ratio = max(volumes) / min(volumes) if min(volumes) > 0 else 0
                    if volume_ratio > 2.0:  # One session has 2x more volume
                        results['session_patterns'].append({
                            'type': 'session_volume_imbalance',
                            'ratio': volume_ratio,
                            'most_active': results['session_rankings']['by_volume'][0]
                        })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Trading session analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_day_of_week_patterns(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze day-of-week patterns
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Day-of-week pattern analysis results
        """
        try:
            results = {
                'dow_patterns': {},
                'weekend_effect': False,
                'monday_effect': False,
                'friday_effect': False,
                'patterns': []
            }
            
            # Extract day of week
            market_data['day_of_week'] = market_data['timestamp'].dt.day_name()
            market_data['dow_num'] = market_data['timestamp'].dt.dayofweek
            
            # Group by day of week
            dow_stats = market_data.groupby('day_of_week').agg({
                'volume': ['mean', 'std', 'count'],
                'close': ['mean', 'std'] if 'close' in market_data.columns else ['mean']
            }).round(4)
            
            # Flatten column names
            dow_stats.columns = ['_'.join(col).strip() for col in dow_stats.columns]
            results['dow_patterns'] = dow_stats.to_dict('index')
            
            # Check for specific day effects
            if 'volume_mean' in dow_stats.columns:
                volume_by_dow = dow_stats['volume_mean']
                
                # Monday effect (lower volume on Monday)
                if 'Monday' in volume_by_dow.index:
                    monday_volume = volume_by_dow['Monday']
                    avg_volume = volume_by_dow.mean()
                    if monday_volume < avg_volume * 0.9:  # 10% lower
                        results['monday_effect'] = True
                        results['patterns'].append({
                            'type': 'monday_effect',
                            'monday_volume': monday_volume,
                            'average_volume': avg_volume
                        })
                
                # Friday effect (higher volume on Friday)
                if 'Friday' in volume_by_dow.index:
                    friday_volume = volume_by_dow['Friday']
                    avg_volume = volume_by_dow.mean()
                    if friday_volume > avg_volume * 1.1:  # 10% higher
                        results['friday_effect'] = True
                        results['patterns'].append({
                            'type': 'friday_effect',
                            'friday_volume': friday_volume,
                            'average_volume': avg_volume
                        })
                
                # Weekend effect (check if weekend data exists)
                weekend_days = ['Saturday', 'Sunday']
                weekend_volume = volume_by_dow[volume_by_dow.index.isin(weekend_days)].mean()
                if not pd.isna(weekend_volume) and weekend_volume > 0:
                    results['weekend_effect'] = True
                    results['patterns'].append({
                        'type': 'weekend_effect',
                        'weekend_volume': weekend_volume,
                        'weekday_volume': volume_by_dow[~volume_by_dow.index.isin(weekend_days)].mean()
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Day-of-week pattern analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_time_of_day_effects(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze time-of-day effects
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Time-of-day effects analysis results
        """
        try:
            results = {
                'morning_effect': False,
                'afternoon_effect': False,
                'evening_effect': False,
                'time_periods': {},
                'patterns': []
            }
            
            # Define time periods
            time_periods = {
                'morning': {'start': 6, 'end': 12},    # 06:00 - 12:00
                'afternoon': {'start': 12, 'end': 18},  # 12:00 - 18:00
                'evening': {'start': 18, 'end': 24},    # 18:00 - 24:00
                'night': {'start': 0, 'end': 6}         # 00:00 - 06:00
            }
            
            # Extract hour from timestamp
            market_data['hour'] = market_data['timestamp'].dt.hour
            
            # Analyze each time period
            for period_name, period_times in time_periods.items():
                period_data = market_data[
                    (market_data['hour'] >= period_times['start']) & 
                    (market_data['hour'] < period_times['end'])
                ]
                
                if not period_data.empty:
                    # Calculate period stats with NaN handling
                    volume_mean = period_data['volume'].mean() if 'volume' in period_data.columns else 0
                    volume_std = period_data['volume'].std() if 'volume' in period_data.columns else 0
                    
                    # Handle NaN values
                    if np.isnan(volume_mean):
                        volume_mean = 0.0
                    if np.isnan(volume_std):
                        volume_std = 0.0
                    
                    period_stats = {
                        'data_points': len(period_data),
                        'volume_mean': volume_mean,
                        'volume_std': volume_std,
                        'price_volatility': 0.0
                    }
                    
                    # Calculate price volatility if close price available
                    if 'close' in period_data.columns:
                        price_changes = period_data['close'].pct_change().abs()
                        period_stats['price_volatility'] = price_changes.mean()
                    
                    results['time_periods'][period_name] = period_stats
            
            # Check for specific time effects
            if results['time_periods']:
                volumes = {period: stats['volume_mean'] for period, stats in results['time_periods'].items()}
                avg_volume = sum(volumes.values()) / len(volumes) if volumes else 0
                
                # Morning effect
                if 'morning' in volumes and volumes['morning'] > avg_volume * 1.1:
                    results['morning_effect'] = True
                    results['patterns'].append({
                        'type': 'morning_effect',
                        'morning_volume': volumes['morning'],
                        'average_volume': avg_volume
                    })
                
                # Afternoon effect
                if 'afternoon' in volumes and volumes['afternoon'] > avg_volume * 1.1:
                    results['afternoon_effect'] = True
                    results['patterns'].append({
                        'type': 'afternoon_effect',
                        'afternoon_volume': volumes['afternoon'],
                        'average_volume': avg_volume
                    })
                
                # Evening effect
                if 'evening' in volumes and volumes['evening'] > avg_volume * 1.1:
                    results['evening_effect'] = True
                    results['patterns'].append({
                        'type': 'evening_effect',
                        'evening_volume': volumes['evening'],
                        'average_volume': avg_volume
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Time-of-day effects analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_market_open_close_effects(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze market opening and closing effects
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Market open/close effects analysis results
        """
        try:
            results = {
                'opening_effect': False,
                'closing_effect': False,
                'open_close_stats': {},
                'patterns': []
            }
            
            # Extract hour and minute from timestamp
            market_data['hour'] = market_data['timestamp'].dt.hour
            market_data['minute'] = market_data['timestamp'].dt.minute
            
            # Define opening and closing periods (first and last hour of trading)
            # Assuming 24/7 crypto trading, we'll look at the first and last hours of each day
            daily_data = market_data.groupby(market_data['timestamp'].dt.date)
            
            opening_volumes = []
            closing_volumes = []
            
            for date, day_data in daily_data:
                if len(day_data) > 0:
                    # First hour of the day
                    first_hour = day_data['hour'].min()
                    opening_data = day_data[day_data['hour'] == first_hour]
                    if not opening_data.empty and 'volume' in opening_data.columns:
                        opening_volumes.append(opening_data['volume'].mean())
                    
                    # Last hour of the day
                    last_hour = day_data['hour'].max()
                    closing_data = day_data[day_data['hour'] == last_hour]
                    if not closing_data.empty and 'volume' in closing_data.columns:
                        closing_volumes.append(closing_data['volume'].mean())
            
            # Calculate opening and closing statistics
            if opening_volumes:
                results['open_close_stats']['opening'] = {
                    'volume_mean': np.mean(opening_volumes),
                    'volume_std': np.std(opening_volumes),
                    'count': len(opening_volumes)
                }
            
            if closing_volumes:
                results['open_close_stats']['closing'] = {
                    'volume_mean': np.mean(closing_volumes),
                    'volume_std': np.std(closing_volumes),
                    'count': len(closing_volumes)
                }
            
            # Check for opening and closing effects
            if 'opening' in results['open_close_stats'] and 'closing' in results['open_close_stats']:
                opening_vol = results['open_close_stats']['opening']['volume_mean']
                closing_vol = results['open_close_stats']['closing']['volume_mean']
                avg_vol = (opening_vol + closing_vol) / 2
                
                # Opening effect (higher volume at market open)
                if opening_vol > avg_vol * 1.2:
                    results['opening_effect'] = True
                    results['patterns'].append({
                        'type': 'opening_effect',
                        'opening_volume': opening_vol,
                        'average_volume': avg_vol
                    })
                
                # Closing effect (higher volume at market close)
                if closing_vol > avg_vol * 1.2:
                    results['closing_effect'] = True
                    results['patterns'].append({
                        'type': 'closing_effect',
                        'closing_volume': closing_vol,
                        'average_volume': avg_vol
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Market open/close effects analysis failed: {e}")
            return {'error': str(e)}
    
    def _analyze_time_based_volatility(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze time-based volatility patterns
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Time-based volatility analysis results
        """
        try:
            results = {
                'volatility_by_hour': {},
                'volatility_by_day': {},
                'volatility_trend': 'stable',
                'high_volatility_periods': [],
                'patterns': []
            }
            
            if 'close' not in market_data.columns:
                return results
            
            # Calculate price changes
            market_data['price_change'] = market_data['close'].pct_change().abs()
            
            # Extract time components
            market_data['hour'] = market_data['timestamp'].dt.hour
            market_data['day_of_week'] = market_data['timestamp'].dt.day_name()
            
            # Volatility by hour
            hourly_volatility = market_data.groupby('hour')['price_change'].agg(['mean', 'std', 'count'])
            # Convert to dict and handle NaN values
            hourly_dict = hourly_volatility.to_dict('index')
            for hour, stats in hourly_dict.items():
                if np.isnan(stats['std']):
                    stats['std'] = 0.0
                if np.isnan(stats['mean']):
                    stats['mean'] = 0.0
            results['volatility_by_hour'] = hourly_dict
            
            # Volatility by day of week
            daily_volatility = market_data.groupby('day_of_week')['price_change'].agg(['mean', 'std', 'count'])
            # Convert to dict and handle NaN values
            daily_dict = daily_volatility.to_dict('index')
            for day, stats in daily_dict.items():
                if np.isnan(stats['std']):
                    stats['std'] = 0.0
                if np.isnan(stats['mean']):
                    stats['mean'] = 0.0
            results['volatility_by_day'] = daily_dict
            
            # Calculate volatility trend
            if len(market_data) >= self.volatility_window:
                recent_volatility = market_data['price_change'].tail(self.volatility_window).mean()
                earlier_volatility = market_data['price_change'].head(self.volatility_window).mean()
                
                if recent_volatility > earlier_volatility * 1.1:
                    results['volatility_trend'] = 'increasing'
                elif recent_volatility < earlier_volatility * 0.9:
                    results['volatility_trend'] = 'decreasing'
                else:
                    results['volatility_trend'] = 'stable'
            
            # Identify high volatility periods
            if 'volatility_by_hour' in results and results['volatility_by_hour']:
                avg_volatility = np.mean([stats['mean'] for stats in results['volatility_by_hour'].values()])
                high_vol_threshold = avg_volatility * 1.5
                
                for hour, stats in results['volatility_by_hour'].items():
                    if stats['mean'] > high_vol_threshold:
                        results['high_volatility_periods'].append({
                            'hour': hour,
                            'volatility': stats['mean'],
                            'threshold': high_vol_threshold
                        })
            
            # Detect patterns
            if results['volatility_trend'] != 'stable':
                results['patterns'].append({
                    'type': 'volatility_trend',
                    'trend': results['volatility_trend']
                })
            
            if len(results['high_volatility_periods']) > 0:
                results['patterns'].append({
                    'type': 'high_volatility_periods',
                    'count': len(results['high_volatility_periods']),
                    'periods': results['high_volatility_periods']
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Time-based volatility analysis failed: {e}")
            return {'error': str(e)}
    
    def _identify_significant_time_patterns(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify significant time-based patterns from analysis results
        
        Args:
            analysis_results: Complete time-based analysis results
            
        Returns:
            List of significant time patterns
        """
        significant_patterns = []
        
        try:
            # Check for strong intraday patterns
            intraday = analysis_results.get('intraday_patterns', {})
            if intraday.get('pattern_strength', 0) > 0.5:
                significant_patterns.append({
                    'type': 'strong_intraday_pattern',
                    'severity': 'high' if intraday.get('pattern_strength', 0) > 0.7 else 'medium',
                    'strength': intraday.get('pattern_strength', 0),
                    'peak_hours': intraday.get('peak_hours', []),
                    'details': intraday,
                    'confidence': 0.8
                })
            
            # Check for session imbalances
            sessions = analysis_results.get('trading_sessions', {})
            if sessions.get('session_patterns'):
                for pattern in sessions['session_patterns']:
                    if pattern.get('type') == 'session_volume_imbalance':
                        significant_patterns.append({
                            'type': 'session_imbalance',
                            'severity': 'high' if pattern.get('ratio', 0) > 3.0 else 'medium',
                            'ratio': pattern.get('ratio', 0),
                            'most_active': pattern.get('most_active', ''),
                            'details': pattern,
                            'confidence': 0.7
                        })
            
            # Check for day-of-week effects
            dow = analysis_results.get('day_of_week_patterns', {})
            if dow.get('patterns'):
                for pattern in dow['patterns']:
                    significant_patterns.append({
                        'type': f"dow_{pattern.get('type', 'effect')}",
                        'severity': 'medium',
                        'details': pattern,
                        'confidence': 0.6
                    })
            
            # Check for time-of-day effects
            tod = analysis_results.get('time_of_day_effects', {})
            if tod.get('patterns'):
                for pattern in tod['patterns']:
                    significant_patterns.append({
                        'type': f"tod_{pattern.get('type', 'effect')}",
                        'severity': 'medium',
                        'details': pattern,
                        'confidence': 0.6
                    })
            
            # Check for open/close effects
            open_close = analysis_results.get('open_close_effects', {})
            if open_close.get('patterns'):
                for pattern in open_close['patterns']:
                    significant_patterns.append({
                        'type': f"market_{pattern.get('type', 'effect')}",
                        'severity': 'medium',
                        'details': pattern,
                        'confidence': 0.6
                    })
            
            # Check for volatility patterns
            volatility = analysis_results.get('time_based_volatility', {})
            if volatility.get('patterns'):
                for pattern in volatility['patterns']:
                    if pattern.get('type') == 'high_volatility_periods':
                        significant_patterns.append({
                            'type': 'high_volatility_periods',
                            'severity': 'high' if pattern.get('count', 0) > 5 else 'medium',
                            'count': pattern.get('count', 0),
                            'details': pattern,
                            'confidence': 0.7
                        })
            
        except Exception as e:
            self.logger.error(f"Failed to identify significant time patterns: {e}")
        
        return significant_patterns
    
    def _calculate_time_analysis_confidence(self, analysis_results: Dict[str, Any]) -> float:
        """
        Calculate confidence in the time-based analysis results
        
        Args:
            analysis_results: Complete time-based analysis results
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            confidence_factors = []
            
            # Data quality factor
            data_points = analysis_results.get('data_points', 0)
            if data_points > 1000:  # Need more data for time analysis
                confidence_factors.append(0.9)
            elif data_points > 500:
                confidence_factors.append(0.7)
            elif data_points > 200:
                confidence_factors.append(0.5)
            else:
                confidence_factors.append(0.3)
            
            # Analysis completeness factor
            analysis_components = ['intraday_patterns', 'trading_sessions', 'day_of_week_patterns', 
                                 'time_of_day_effects', 'open_close_effects', 'time_based_volatility']
            completed_analyses = sum(1 for component in analysis_components if component in analysis_results)
            completeness_confidence = completed_analyses / len(analysis_components)
            confidence_factors.append(completeness_confidence)
            
            # Pattern consistency factor
            significant_patterns = analysis_results.get('pattern_details', [])
            if len(significant_patterns) > 0:
                # Higher confidence if patterns are consistent across time dimensions
                pattern_types = [pattern.get('type', '') for pattern in significant_patterns]
                unique_types = len(set(pattern_types))
                consistency_confidence = min(0.9, 0.5 + (len(significant_patterns) - unique_types) * 0.1)
                confidence_factors.append(consistency_confidence)
            else:
                confidence_factors.append(0.8)  # High confidence in "no significant patterns" result
            
            # Calculate weighted average
            return sum(confidence_factors) / len(confidence_factors)
            
        except Exception as e:
            self.logger.error(f"Time analysis confidence calculation failed: {e}")
            return 0.5  # Default confidence
    
    async def configure(self, configuration: Dict[str, Any]) -> bool:
        """
        Configure the time-based pattern detector with LLM-determined parameters
        
        Args:
            configuration: Configuration parameters from LLM
            
        Returns:
            True if configuration successful
        """
        try:
            # Update configurable parameters
            if 'session_threshold' in configuration:
                self.session_threshold = max(0.1, min(1.0, configuration['session_threshold']))
                self.logger.info(f"Updated session_threshold to {self.session_threshold}")
            
            if 'pattern_sensitivity' in configuration:
                self.pattern_sensitivity = max(0.1, min(2.0, configuration['pattern_sensitivity']))
                self.logger.info(f"Updated pattern_sensitivity to {self.pattern_sensitivity}")
            
            # Update other parameters if provided
            if 'intraday_window' in configuration:
                self.intraday_window = max(5, min(100, configuration['intraday_window']))
                self.logger.info(f"Updated intraday_window to {self.intraday_window}")
            
            if 'anomaly_threshold' in configuration:
                self.anomaly_threshold = max(1.5, min(5.0, configuration['anomaly_threshold']))
                self.logger.info(f"Updated anomaly_threshold to {self.anomaly_threshold}")
            
            self.logger.info(f"Successfully configured TimeBasedPatternDetector with {len(configuration)} parameters")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure TimeBasedPatternDetector: {e}")
            return False
    
    def get_configurable_parameters(self) -> Dict[str, Any]:
        """
        Get current configurable parameters
        
        Returns:
            Dictionary of current parameter values
        """
        return {
            'session_threshold': self.session_threshold,
            'pattern_sensitivity': self.pattern_sensitivity,
            'intraday_window': self.intraday_window,
            'anomaly_threshold': self.anomaly_threshold
        }
