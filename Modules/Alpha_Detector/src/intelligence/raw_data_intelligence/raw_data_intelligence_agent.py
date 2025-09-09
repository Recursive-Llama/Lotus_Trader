"""
Raw Data Intelligence Agent

The main agent for raw data intelligence that monitors OHLCV data for patterns
that traditional indicators miss. This agent operates at the most fundamental
level of market data analysis.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
import pandas as pd
import numpy as np

from src.llm_integration.agent_communication_protocol import AgentCommunicationProtocol
from src.llm_integration.agent_discovery_system import AgentDiscoverySystem
from src.llm_integration.openrouter_client import OpenRouterClient
from src.llm_integration.prompt_manager import PromptManager
from src.llm_integration.database_driven_context_system import DatabaseDrivenContextSystem
from src.utils.supabase_manager import SupabaseManager

from .market_microstructure import MarketMicrostructureAnalyzer
from .volume_analyzer import VolumePatternAnalyzer
from .time_based_patterns import TimeBasedPatternDetector
from .cross_asset_analyzer import CrossAssetPatternAnalyzer
from .divergence_detector import RawDataDivergenceDetector
from src.core_detection.multi_timeframe_processor import MultiTimeframeProcessor


class RawDataIntelligenceAgent:
    """
    Raw Data Intelligence Agent
    
    Monitors raw OHLCV data for patterns that traditional indicators miss.
    This agent focuses on:
    - Market microstructure analysis
    - Volume pattern detection
    - Time-based patterns
    - Cross-asset correlations
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        
        # Enhanced LLM control capabilities
        self.context_system = DatabaseDrivenContextSystem(supabase_manager)
        
        # Agent identification
        self.agent_name = "raw_data_intelligence"
        self.capabilities = [
            "raw_data_analysis",
            "market_microstructure", 
            "volume_analysis",
            "time_based_patterns",
            "cross_asset_analysis",
            "divergence_detection"
        ]
        self.specializations = [
            "ohlcv_patterns",
            "volume_spikes",
            "time_based_patterns",
            "market_microstructure",
            "cross_asset_correlations",
            "price_volume_divergences",
            "price_momentum_divergences",
            "cross_asset_divergences"
        ]
        
        # Communication protocol
        self.communication_protocol = AgentCommunicationProtocol(
            self.agent_name, self.supabase_manager
        )
        
        # Analysis components
        self.microstructure_analyzer = MarketMicrostructureAnalyzer()
        self.volume_analyzer = VolumePatternAnalyzer()
        self.time_pattern_detector = TimeBasedPatternDetector()
        self.cross_asset_analyzer = CrossAssetPatternAnalyzer()
        self.divergence_detector = RawDataDivergenceDetector()
        
        # Multi-timeframe processor
        self.multi_timeframe_processor = MultiTimeframeProcessor()
        
        # Timeframe-dependent analysis windows
        self.timeframe_windows = {
            '1m': timedelta(hours=4),    # 240 candles
            '5m': timedelta(hours=20),   # 240 candles  
            '15m': timedelta(hours=60),  # 240 candles
            '1h': timedelta(days=10)     # 240 candles
        }
        
        # Enhanced thresholds for different timeframes
        self.timeframe_thresholds = {
            '1m': {
                'divergence_threshold': 0.25,  # 25%
                'volume_spike_threshold': 4.0,  # 4x average
                'confidence_threshold': 0.85   # 85%
            },
            '5m': {
                'divergence_threshold': 0.20,  # 20%
                'volume_spike_threshold': 3.5,  # 3.5x average
                'confidence_threshold': 0.80   # 80%
            },
            '15m': {
                'divergence_threshold': 0.15,  # 15%
                'volume_spike_threshold': 3.0,  # 3x average
                'confidence_threshold': 0.75   # 75%
            },
            '1h': {
                'divergence_threshold': 0.10,  # 10%
                'volume_spike_threshold': 2.5,  # 2.5x average
                'confidence_threshold': 0.70   # 70%
            }
        }
        
        # Tool registry for LLM control
        self.available_tools = {
            'divergence_detector': {
                'class': 'RawDataDivergenceDetector',
                'configurable_parameters': ['lookback_period', 'threshold', 'smoothing_factor'],
                'methods': ['detect_divergences', 'configure', 'adjust_sensitivity'],
                'documentation': 'Detects price-volume and momentum divergences'
            },
            'volume_analyzer': {
                'class': 'VolumePatternAnalyzer',
                'configurable_parameters': ['volume_threshold', 'spike_detection'],
                'methods': ['analyze_volume', 'detect_spikes'],
                'documentation': 'Analyzes volume patterns and detects anomalies'
            },
            'microstructure_analyzer': {
                'class': 'MarketMicrostructureAnalyzer',
                'configurable_parameters': ['order_flow_threshold', 'price_impact_sensitivity'],
                'methods': ['analyze_microstructure', 'detect_anomalies'],
                'documentation': 'Analyzes market microstructure patterns'
            },
            'time_pattern_detector': {
                'class': 'TimeBasedPatternDetector',
                'configurable_parameters': ['session_threshold', 'pattern_sensitivity'],
                'methods': ['detect_time_patterns', 'analyze_sessions'],
                'documentation': 'Detects time-based market patterns'
            },
            'cross_asset_analyzer': {
                'class': 'CrossAssetPatternAnalyzer',
                'configurable_parameters': ['correlation_threshold', 'arbitrage_sensitivity'],
                'methods': ['analyze_correlations', 'detect_arbitrage'],
                'documentation': 'Analyzes cross-asset patterns and correlations'
            }
        }
        
        # Agent state
        self.is_running = False
        self.last_analysis_time = None
        self.analysis_history = []
        
        # Initialize logging
        self.logger = logging.getLogger(f"{__name__}.{self.agent_name}")
        
        # Register message handlers
        self._register_message_handlers()
    
    def _register_message_handlers(self):
        """Register custom message handlers"""
        self.communication_protocol.register_message_handler(
            "raw_data_analysis_request", self._handle_raw_data_analysis_request
        )
        self.communication_protocol.register_message_handler(
            "volume_analysis_request", self._handle_volume_analysis_request
        )
        self.communication_protocol.register_message_handler(
            "microstructure_analysis_request", self._handle_microstructure_analysis_request
        )
    
    async def start(self, discovery_system: AgentDiscoverySystem) -> bool:
        """
        Start the Raw Data Intelligence Agent
        
        Args:
            discovery_system: Agent discovery system for registration
            
        Returns:
            True if started successfully
        """
        try:
            # Register agent capabilities
            await discovery_system.register_agent_capabilities(
                self.agent_name, self.capabilities, self.specializations
            )
            
            # Start communication protocol
            self.communication_protocol.start_listening()
            
            # Start analysis loop
            self.is_running = True
            asyncio.create_task(self._analysis_loop())
            
            self.logger.info(f"Raw Data Intelligence Agent started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Raw Data Intelligence Agent: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        Stop the Raw Data Intelligence Agent
        
        Returns:
            True if stopped successfully
        """
        try:
            self.is_running = False
            self.communication_protocol.stop_listening()
            
            self.logger.info(f"Raw Data Intelligence Agent stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop Raw Data Intelligence Agent: {e}")
            return False
    
    async def _analysis_loop(self):
        """
        Main analysis loop that continuously monitors raw data
        """
        self.logger.info("Starting raw data analysis loop")
        
        while self.is_running:
            try:
                # Get recent market data
                market_data = await self._get_recent_market_data()
                
                if market_data is not None and not market_data.empty:
                    # Perform comprehensive raw data analysis
                    analysis_results = await self._analyze_raw_data(market_data)
                    
                    # Publish findings if significant patterns detected
                    if analysis_results.get('significant_patterns'):
                        await self._publish_findings(analysis_results)
                
                # Sleep for 5 minutes before next analysis (less frequent)
                await asyncio.sleep(300)
                
            except asyncio.CancelledError:
                self.logger.info("Raw data analysis loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in raw data analysis loop: {e}")
                await asyncio.sleep(120)  # Wait longer on error
    
    async def _get_recent_market_data(self) -> Optional[pd.DataFrame]:
        """
        Get recent market data from the database with extended window for multi-timeframe analysis
        
        Returns:
            DataFrame with recent OHLCV data or None if no data
        """
        try:
            # Get data from last 4 hours (extended window for multi-timeframe analysis)
            four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=4)
            
            result = self.supabase_manager.client.table('alpha_market_data_1m').select('*').gte(
                'timestamp', four_hours_ago.isoformat()
            ).order('timestamp', desc=True).limit(2000).execute()  # More data for rollup
            
            if result.data:
                df = pd.DataFrame(result.data)
                # Handle timestamp conversion with proper format handling
                try:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')
                except:
                    # Fallback to mixed format parsing
                    df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
                return df
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get recent market data: {e}")
            return None
    
    async def _analyze_raw_data(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform enhanced multi-timeframe raw data analysis
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Use enhanced multi-timeframe analysis
            return await self._analyze_raw_data_enhanced(market_data)
            
        except Exception as e:
            self.logger.error(f"Failed to analyze raw data: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    async def _analyze_raw_data_enhanced(self, market_data_1m: pd.DataFrame) -> Dict[str, Any]:
        """
        Enhanced multi-timeframe raw data analysis
        
        Args:
            market_data_1m: DataFrame with 1-minute OHLCV data
            
        Returns:
            Dictionary with enhanced analysis results
        """
        try:
            # 1. Roll up to multiple timeframes
            multi_timeframe_data = self.multi_timeframe_processor.process_multi_timeframe(market_data_1m)
            
            analysis_results = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data_points': len(market_data_1m),
                'symbols': market_data_1m['symbol'].unique().tolist() if 'symbol' in market_data_1m.columns else [],
                'significant_patterns': [],
                'timeframe_analysis': {},
                'cross_timeframe_patterns': [],
                'analysis_components': {}
            }
            
            # 2. Analyze each timeframe
            for timeframe, data in multi_timeframe_data.items():
                timeframe_analysis = await self._analyze_timeframe_enhanced(
                    data['ohlc'], timeframe, multi_timeframe_data
                )
                analysis_results['timeframe_analysis'][timeframe] = timeframe_analysis
            
            # 3. Cross-timeframe pattern detection
            cross_timeframe_patterns = await self._detect_cross_timeframe_patterns(
                analysis_results['timeframe_analysis']
            )
            analysis_results['cross_timeframe_patterns'] = cross_timeframe_patterns
            
            # 4. Legacy analysis components for backward compatibility
            analysis_results['analysis_components'] = {
                'microstructure': analysis_results['timeframe_analysis'].get('1m', {}).get('microstructure_analysis', {}),
                'volume': analysis_results['timeframe_analysis'].get('1m', {}).get('volume_analysis', {}),
                'time_based': analysis_results['timeframe_analysis'].get('1m', {}).get('time_based_analysis', {}),
                'cross_asset': analysis_results['timeframe_analysis'].get('1m', {}).get('cross_asset_analysis', {}),
                'divergences': analysis_results['timeframe_analysis'].get('1m', {}).get('divergence_analysis', {})
            }
            
            # 5. LLM-Enhanced Pattern Detection
            llm_results = await self._llm_enhanced_analysis(market_data_1m, analysis_results)
            analysis_results['analysis_components']['llm_enhanced'] = llm_results
            
            # 6. Identify significant patterns with enhanced filtering and historical context
            significant_patterns = await self._identify_significant_patterns_enhanced(analysis_results)
            analysis_results['significant_patterns'] = significant_patterns
            
            # Store analysis history
            self.analysis_history.append(analysis_results)
            if len(self.analysis_history) > 100:  # Keep last 100 analyses
                self.analysis_history = self.analysis_history[-100:]
            
            self.last_analysis_time = datetime.now(timezone.utc)
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Enhanced raw data analysis failed: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    async def _analyze_timeframe_enhanced(self, market_data: pd.DataFrame, 
                                        timeframe: str, 
                                        all_timeframes: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze single timeframe with cross-timeframe context"""
        try:
            # Get thresholds for this timeframe
            thresholds = self.timeframe_thresholds.get(timeframe, self.timeframe_thresholds['1m'])
            
            # Calculate baselines for this timeframe
            baselines = self._calculate_timeframe_baselines(market_data, timeframe)
            
            # Calculate cross-timeframe baselines
            cross_timeframe_baselines = self._calculate_cross_timeframe_baselines(
                market_data, timeframe, all_timeframes
            )
            
            analysis = {
                'timeframe': timeframe,
                'data_points': len(market_data),
                'baselines': baselines,
                'cross_timeframe_baselines': cross_timeframe_baselines,
                'volume_analysis': await self._analyze_volume_enhanced(market_data, baselines, cross_timeframe_baselines, thresholds),
                'microstructure_analysis': await self._analyze_microstructure_enhanced(market_data, baselines, thresholds),
                'institutional_flow_analysis': await self._analyze_institutional_flow_enhanced(market_data, baselines, thresholds),
                'divergence_analysis': await self._analyze_divergences_enhanced(market_data, baselines, thresholds)
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Timeframe analysis failed for {timeframe}: {e}")
            return {'error': str(e), 'timeframe': timeframe}
    
    def _calculate_timeframe_baselines(self, market_data: pd.DataFrame, timeframe: str) -> Dict[str, Any]:
        """Calculate proper statistical baselines for pattern detection"""
        try:
            baselines = {
                'timeframe': timeframe,
                'volume': {},
                'price': {},
                'volatility': {}
            }
            
            # Volume baselines
            if 'volume' in market_data.columns and len(market_data) > 0:
                volume = market_data['volume']
                baselines['volume'] = {
                    'mean': volume.mean(),
                    'std': volume.std(),
                    'median': volume.median(),
                    'percentile_95': volume.quantile(0.95),
                    'rolling_mean_20': volume.rolling(20).mean().iloc[-1] if len(volume) >= 20 else volume.mean(),
                    'rolling_std_20': volume.rolling(20).std().iloc[-1] if len(volume) >= 20 else volume.std(),
                    'current': volume.iloc[-1] if len(volume) > 0 else 0
                }
            
            # Price baselines
            if 'close' in market_data.columns and len(market_data) > 0:
                close = market_data['close']
                price_change = close.pct_change()
                baselines['price'] = {
                    'current': close.iloc[-1],
                    'mean': close.mean(),
                    'volatility': price_change.std(),
                    'rolling_volatility_20': price_change.rolling(20).std().iloc[-1] if len(price_change) >= 20 else price_change.std(),
                    'current_change': price_change.iloc[-1] if len(price_change) > 0 else 0
                }
            
            return baselines
            
        except Exception as e:
            self.logger.error(f"Failed to calculate baselines for {timeframe}: {e}")
            return {}
    
    def _calculate_cross_timeframe_baselines(self, current_data: pd.DataFrame, 
                                           current_timeframe: str, 
                                           all_timeframes: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate baselines across multiple timeframes"""
        try:
            cross_baselines = {}
            
            # Get current timeframe metrics
            current_volume = current_data['volume'].iloc[-1] if len(current_data) > 0 and 'volume' in current_data.columns else 0
            current_price = current_data['close'].iloc[-1] if len(current_data) > 0 and 'close' in current_data.columns else 0
            
            # Compare against other timeframes
            for tf_name, tf_data in all_timeframes.items():
                if tf_name == current_timeframe:
                    continue
                
                tf_ohlc = tf_data['ohlc']
                if len(tf_ohlc) > 0 and 'volume' in tf_ohlc.columns and 'close' in tf_ohlc.columns:
                    # Volume comparison
                    tf_volume_avg = tf_ohlc['volume'].mean()
                    tf_volume_std = tf_ohlc['volume'].std()
                    
                    # Price comparison
                    tf_price_avg = tf_ohlc['close'].mean()
                    tf_price_std = tf_ohlc['close'].std()
                    
                    cross_baselines[tf_name] = {
                        'volume_ratio': current_volume / tf_volume_avg if tf_volume_avg > 0 else 0,
                        'volume_z_score': (current_volume - tf_volume_avg) / tf_volume_std if tf_volume_std > 0 else 0,
                        'price_ratio': current_price / tf_price_avg if tf_price_avg > 0 else 0,
                        'price_z_score': (current_price - tf_price_avg) / tf_price_std if tf_price_std > 0 else 0
                    }
            
            return cross_baselines
            
        except Exception as e:
            self.logger.error(f"Failed to calculate cross-timeframe baselines: {e}")
            return {}
    
    async def _detect_cross_timeframe_patterns(self, timeframe_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect patterns that span multiple timeframes"""
        try:
            cross_timeframe_patterns = []
            
            # Look for volume patterns across timeframes
            volume_patterns = {}
            for tf, analysis in timeframe_analysis.items():
                if 'volume_analysis' in analysis and analysis['volume_analysis'].get('significant_volume_spike'):
                    volume_patterns[tf] = analysis['volume_analysis']
            
            # If volume spikes detected across multiple timeframes, it's significant
            if len(volume_patterns) >= 2:
                cross_timeframe_patterns.append({
                    'type': 'cross_timeframe_volume_spike',
                    'timeframes': list(volume_patterns.keys()),
                    'confidence': min(1.0, len(volume_patterns) * 0.3),
                    'details': volume_patterns
                })
            
            # Look for institutional flow across timeframes
            institutional_patterns = {}
            for tf, analysis in timeframe_analysis.items():
                if 'institutional_flow_analysis' in analysis and analysis['institutional_flow_analysis'].get('detected'):
                    institutional_patterns[tf] = analysis['institutional_flow_analysis']
            
            if len(institutional_patterns) >= 2:
                cross_timeframe_patterns.append({
                    'type': 'cross_timeframe_institutional_flow',
                    'timeframes': list(institutional_patterns.keys()),
                    'confidence': min(1.0, len(institutional_patterns) * 0.4),
                    'details': institutional_patterns
                })
            
            return cross_timeframe_patterns
            
        except Exception as e:
            self.logger.error(f"Failed to detect cross-timeframe patterns: {e}")
            return []
    
    async def _analyze_volume_enhanced(self, market_data: pd.DataFrame, 
                                     baselines: Dict[str, Any], 
                                     cross_timeframe_baselines: Dict[str, Any],
                                     thresholds: Dict[str, float]) -> Dict[str, Any]:
        """Enhanced volume analysis with proper baselines"""
        try:
            volume_analysis = {
                'significant_volume_spike': False,
                'confidence': 0.0,
                'details': {},
                'cross_timeframe_confirmation': False
            }
            
            if 'volume' not in baselines or not baselines['volume']:
                return volume_analysis
            
            volume_baseline = baselines['volume']
            current_volume = volume_baseline.get('current', 0)
            volume_avg = volume_baseline.get('rolling_mean_20', volume_baseline.get('mean', 0))
            volume_std = volume_baseline.get('rolling_std_20', volume_baseline.get('std', 0))
            
            # Calculate volume spike ratio
            volume_ratio = current_volume / volume_avg if volume_avg > 0 else 0
            volume_z_score = (current_volume - volume_avg) / volume_std if volume_std > 0 else 0
            
            # Check if volume spike meets threshold
            volume_spike_threshold = thresholds.get('volume_spike_threshold', 4.0)
            if volume_ratio >= volume_spike_threshold:
                volume_analysis['significant_volume_spike'] = True
                volume_analysis['confidence'] = min(1.0, (volume_ratio - volume_spike_threshold) / volume_spike_threshold)
                volume_analysis['details'] = {
                    'volume_ratio': volume_ratio,
                    'volume_z_score': volume_z_score,
                    'current_volume': current_volume,
                    'baseline_volume': volume_avg
                }
                
                # Check cross-timeframe confirmation
                cross_timeframe_confirmations = 0
                for tf, cross_baseline in cross_timeframe_baselines.items():
                    if cross_baseline.get('volume_ratio', 0) >= 1.5:  # 50% above other timeframes
                        cross_timeframe_confirmations += 1
                
                if cross_timeframe_confirmations >= 1:
                    volume_analysis['cross_timeframe_confirmation'] = True
                    volume_analysis['confidence'] = min(1.0, volume_analysis['confidence'] + 0.2)
            
            return volume_analysis
            
        except Exception as e:
            self.logger.error(f"Enhanced volume analysis failed: {e}")
            return {'significant_volume_spike': False, 'confidence': 0.0}
    
    async def _analyze_microstructure_enhanced(self, market_data: pd.DataFrame, 
                                             baselines: Dict[str, Any],
                                             thresholds: Dict[str, float]) -> Dict[str, Any]:
        """Enhanced microstructure analysis"""
        try:
            microstructure_analysis = {
                'anomalies_detected': False,
                'confidence': 0.0,
                'details': {}
            }
            
            if len(market_data) < 10:
                return microstructure_analysis
            
            # Analyze order flow patterns
            market_data_copy = market_data.copy()
            market_data_copy['price_change'] = market_data_copy['close'].pct_change()
            
            # Calculate buying vs selling pressure
            positive_changes = market_data_copy[market_data_copy['price_change'] > 0]
            negative_changes = market_data_copy[market_data_copy['price_change'] < 0]
            
            buying_pressure = positive_changes['volume'].sum() if not positive_changes.empty else 0
            selling_pressure = negative_changes['volume'].sum() if not negative_changes.empty else 0
            total_volume = market_data_copy['volume'].sum()
            
            if total_volume > 0:
                net_flow = (buying_pressure - selling_pressure) / total_volume
                flow_imbalance = abs(net_flow)
                
                # Detect significant flow imbalance
                if flow_imbalance > 0.3:  # 30% imbalance
                    microstructure_analysis['anomalies_detected'] = True
                    microstructure_analysis['confidence'] = min(1.0, (flow_imbalance - 0.3) / 0.4)
                    microstructure_analysis['details'] = {
                        'flow_imbalance': flow_imbalance,
                        'net_flow': net_flow,
                        'direction': 'buying' if net_flow > 0 else 'selling',
                        'buying_pressure': buying_pressure,
                        'selling_pressure': selling_pressure
                    }
            
            return microstructure_analysis
            
        except Exception as e:
            self.logger.error(f"Enhanced microstructure analysis failed: {e}")
            return {'anomalies_detected': False, 'confidence': 0.0}
    
    async def _analyze_institutional_flow_enhanced(self, market_data: pd.DataFrame, 
                                                 baselines: Dict[str, Any],
                                                 thresholds: Dict[str, float]) -> Dict[str, Any]:
        """Enhanced institutional flow detection"""
        try:
            institutional_flow = {
                'detected': False,
                'confidence': 0.0,
                'flow_type': 'unknown',
                'details': {}
            }
            
            if len(market_data) < 20 or 'volume' not in baselines or not baselines['volume']:
                return institutional_flow
            
            # Get current metrics
            current_volume = baselines['volume'].get('current', 0)
            volume_avg = baselines['volume'].get('rolling_mean_20', baselines['volume'].get('mean', 0))
            volume_std = baselines['volume'].get('rolling_std_20', baselines['volume'].get('std', 0))
            
            # Calculate price impact
            price_changes = market_data['close'].pct_change().dropna()
            recent_price_impact = abs(price_changes.iloc[-1]) if len(price_changes) > 0 else 0
            
            # Institutional flow criteria: Large volume with price impact
            volume_z_score = (current_volume - volume_avg) / volume_std if volume_std > 0 else 0
            
            # Require 3+ standard deviations volume with 0.5%+ price impact
            if volume_z_score > 3.0 and recent_price_impact > 0.005:
                institutional_flow['detected'] = True
                institutional_flow['confidence'] = min(1.0, (volume_z_score - 3.0) / 2.0 + (recent_price_impact - 0.005) / 0.01)
                institutional_flow['flow_type'] = 'large_institutional'
                institutional_flow['details'] = {
                    'volume_z_score': volume_z_score,
                    'price_impact': recent_price_impact,
                    'volume_magnitude': current_volume / volume_avg if volume_avg > 0 else 0,
                    'current_volume': current_volume,
                    'baseline_volume': volume_avg
                }
            
            return institutional_flow
            
        except Exception as e:
            self.logger.error(f"Institutional flow analysis failed: {e}")
            return {'detected': False, 'confidence': 0.0}
    
    async def _analyze_divergences_enhanced(self, market_data: pd.DataFrame, 
                                          baselines: Dict[str, Any],
                                          thresholds: Dict[str, float]) -> Dict[str, Any]:
        """Enhanced divergence analysis"""
        try:
            divergence_analysis = {
                'divergences_detected': 0,
                'confidence': 0.0,
                'details': []
            }
            
            if len(market_data) < 20:
                return divergence_analysis
            
            # Price-volume divergence analysis
            price_changes = market_data['close'].pct_change().dropna()
            volume_changes = market_data['volume'].pct_change().dropna()
            
            if len(price_changes) > 0 and len(volume_changes) > 0:
                # Calculate correlation between price and volume changes
                correlation = price_changes.corr(volume_changes)
                
                # Detect divergence (negative correlation with significant magnitude)
                divergence_threshold = thresholds.get('divergence_threshold', 0.25)
                if correlation < -divergence_threshold:
                    divergence_analysis['divergences_detected'] += 1
                    divergence_analysis['confidence'] = min(1.0, abs(correlation) / divergence_threshold)
                    divergence_analysis['details'].append({
                        'type': 'price_volume_divergence',
                        'correlation': correlation,
                        'severity': 'high' if abs(correlation) > 0.5 else 'medium'
                    })
            
            return divergence_analysis
            
        except Exception as e:
            self.logger.error(f"Enhanced divergence analysis failed: {e}")
            return {'divergences_detected': 0, 'confidence': 0.0}
    
    async def _analyze_market_microstructure(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze market microstructure patterns"""
        try:
            return await self.microstructure_analyzer.analyze(market_data)
        except Exception as e:
            self.logger.error(f"Market microstructure analysis failed: {e}")
            return {'error': str(e)}
    
    async def _analyze_volume_patterns(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze volume patterns"""
        try:
            return await self.volume_analyzer.analyze(market_data)
        except Exception as e:
            self.logger.error(f"Volume pattern analysis failed: {e}")
            return {'error': str(e)}
    
    async def _analyze_time_based_patterns(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze time-based patterns"""
        try:
            return await self.time_pattern_detector.analyze(market_data)
        except Exception as e:
            self.logger.error(f"Time-based pattern analysis failed: {e}")
            return {'error': str(e)}
    
    async def _analyze_cross_asset_patterns(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze cross-asset patterns"""
        try:
            return await self.cross_asset_analyzer.analyze(market_data)
        except Exception as e:
            self.logger.error(f"Cross-asset pattern analysis failed: {e}")
            return {'error': str(e)}
    
    async def _analyze_raw_data_divergences(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze raw data divergences"""
        try:
            return await self.divergence_detector.analyze(market_data)
        except Exception as e:
            self.logger.error(f"Raw data divergence analysis failed: {e}")
            return {'error': str(e)}
    
    async def _llm_enhanced_analysis(self, market_data: pd.DataFrame, 
                                   analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to enhance raw data analysis
        
        Args:
            market_data: Market data DataFrame
            analysis_results: Results from technical analysis
            
        Returns:
            LLM-enhanced analysis results
        """
        try:
            # Prepare context for LLM
            context = {
                'market_data_summary': {
                    'symbols': market_data['symbol'].unique().tolist() if 'symbol' in market_data.columns else [],
                    'time_range': {
                        'start': market_data['timestamp'].min().isoformat() if 'timestamp' in market_data.columns else None,
                        'end': market_data['timestamp'].max().isoformat() if 'timestamp' in market_data.columns else None
                    },
                    'data_points': len(market_data)
                },
                'technical_analysis': analysis_results['analysis_components'],
                'analysis_timestamp': analysis_results['timestamp']
            }
            
            # Get LLM prompt for raw data analysis
            prompt = self.prompt_manager.get_prompt(
                'raw_data_intelligence', 'comprehensive_analysis'
            )
            
            # Format prompt with context
            formatted_prompt = self.prompt_manager.format_prompt(
                prompt, context=context
            )
            
            # Get LLM analysis
            llm_response = await self.llm_client.complete(
                formatted_prompt,
                max_tokens=1000,
                temperature=0.3
            )
            
            return {
                'llm_analysis': llm_response,
                'context_used': context,
                'prompt_used': formatted_prompt[:200] + "..." if len(formatted_prompt) > 200 else formatted_prompt
            }
            
        except Exception as e:
            self.logger.error(f"LLM-enhanced analysis failed: {e}")
            return {'error': str(e)}
    
    def _identify_significant_patterns(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify significant patterns from analysis results
        
        Args:
            analysis_results: Complete analysis results
            
        Returns:
            List of significant patterns
        """
        significant_patterns = []
        
        try:
            # Check for significant volume patterns
            volume_analysis = analysis_results.get('analysis_components', {}).get('volume', {})
            if volume_analysis.get('significant_volume_spike'):
                significant_patterns.append({
                    'type': 'volume_spike',
                    'severity': volume_analysis.get('spike_severity', 'medium'),
                    'details': volume_analysis.get('spike_details', {}),
                    'confidence': volume_analysis.get('confidence', 0.5)
                })
            
            # Check for microstructure anomalies
            microstructure_analysis = analysis_results.get('analysis_components', {}).get('microstructure', {})
            if microstructure_analysis.get('anomalies_detected'):
                significant_patterns.append({
                    'type': 'microstructure_anomaly',
                    'severity': microstructure_analysis.get('anomaly_severity', 'medium'),
                    'details': microstructure_analysis.get('anomaly_details', {}),
                    'confidence': microstructure_analysis.get('confidence', 0.5)
                })
            
            # Check for time-based patterns
            time_analysis = analysis_results.get('analysis_components', {}).get('time_based', {})
            if time_analysis.get('significant_time_pattern'):
                significant_patterns.append({
                    'type': 'time_based_pattern',
                    'severity': time_analysis.get('pattern_severity', 'medium'),
                    'details': time_analysis.get('pattern_details', {}),
                    'confidence': time_analysis.get('confidence', 0.5)
                })
            
            # Check for cross-asset correlations
            cross_asset_analysis = analysis_results.get('analysis_components', {}).get('cross_asset', {})
            if cross_asset_analysis.get('significant_correlation'):
                significant_patterns.append({
                    'type': 'cross_asset_correlation',
                    'severity': cross_asset_analysis.get('correlation_severity', 'medium'),
                    'details': cross_asset_analysis.get('correlation_details', {}),
                    'confidence': cross_asset_analysis.get('confidence', 0.5)
                })
            
            # Check for raw data divergences
            divergence_analysis = analysis_results.get('analysis_components', {}).get('divergences', {})
            if divergence_analysis.get('divergences_detected', 0) > 0:
                significant_patterns.append({
                    'type': 'raw_data_divergences',
                    'severity': 'high' if divergence_analysis.get('divergences_detected', 0) > 3 else 'medium',
                    'details': divergence_analysis.get('divergence_details', []),
                    'confidence': divergence_analysis.get('confidence', 0.5)
                })
            
            # Check LLM insights
            llm_analysis = analysis_results.get('analysis_components', {}).get('llm_enhanced', {})
            if llm_analysis.get('llm_analysis'):
                # Parse LLM response for significant insights
                llm_insights = self._parse_llm_insights(llm_analysis['llm_analysis'])
                if llm_insights:
                    significant_patterns.append({
                        'type': 'llm_insight',
                        'severity': llm_insights.get('severity', 'medium'),
                        'details': llm_insights.get('details', {}),
                        'confidence': llm_insights.get('confidence', 0.5)
                    })
            
        except Exception as e:
            self.logger.error(f"Failed to identify significant patterns: {e}")
        
        return significant_patterns
    
    async def _identify_significant_patterns_enhanced(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Enhanced pattern identification with multi-timeframe validation
        
        Args:
            analysis_results: Complete enhanced analysis results
            
        Returns:
            List of significant patterns with enhanced filtering
        """
        significant_patterns = []
        
        try:
            # Get cross-timeframe patterns first (highest priority)
            cross_timeframe_patterns = analysis_results.get('cross_timeframe_patterns', [])
            for pattern in cross_timeframe_patterns:
                if pattern.get('pattern_clarity', 0.0) >= 0.7:  # High clarity threshold for cross-timeframe
                    significant_patterns.append({
                        'type': pattern['type'],
                        'timeframe': 'multi',
                        'severity': 'high',
                        'details': pattern['details'],
                        'pattern_clarity': pattern['pattern_clarity'],
                        'z_score': pattern.get('z_score', 0.0),
                        'statistical_significance': pattern.get('statistical_significance', 0.0),
                        'cross_timeframe': True,
                        'team_member': pattern.get('team_member', 'raw_data_intelligence_agent')
                    })
            
            # Check individual timeframe patterns
            timeframe_analysis = analysis_results.get('timeframe_analysis', {})
            for timeframe, analysis in timeframe_analysis.items():
                thresholds = self.timeframe_thresholds.get(timeframe, self.timeframe_thresholds['1m'])
                confidence_threshold = thresholds['confidence_threshold']
                
                # Check volume patterns
                volume_analysis = analysis.get('volume_analysis', {})
                if volume_analysis.get('pattern_clarity', 0.0) >= confidence_threshold:
                    significant_patterns.append({
                        'type': 'volume_spike',
                        'timeframe': timeframe,
                        'severity': 'high' if volume_analysis.get('pattern_clarity', 0.0) >= 0.9 else 'medium',
                        'details': volume_analysis,
                        'pattern_clarity': volume_analysis.get('pattern_clarity', 0.0),
                        'z_score': volume_analysis.get('z_score', 0.0),
                        'statistical_significance': volume_analysis.get('statistical_significance', 0.0),
                        'cross_timeframe_confirmation': volume_analysis.get('cross_timeframe_confirmation', False),
                        'team_member': 'volume_analyzer'
                    })
                
                # Check microstructure patterns
                microstructure_analysis = analysis.get('microstructure_analysis', {})
                if microstructure_analysis.get('pattern_clarity', 0.0) >= confidence_threshold:
                    significant_patterns.append({
                        'type': 'microstructure_anomaly',
                        'timeframe': timeframe,
                        'severity': 'high' if microstructure_analysis.get('pattern_clarity', 0.0) >= 0.9 else 'medium',
                        'details': microstructure_analysis,
                        'pattern_clarity': microstructure_analysis.get('pattern_clarity', 0.0),
                        'z_score': microstructure_analysis.get('z_score', 0.0),
                        'statistical_significance': microstructure_analysis.get('statistical_significance', 0.0),
                        'team_member': 'microstructure_analyzer'
                    })
                
                # Check institutional flow patterns
                institutional_flow = analysis.get('institutional_flow_analysis', {})
                if institutional_flow.get('pattern_clarity', 0.0) >= confidence_threshold:
                    significant_patterns.append({
                        'type': 'institutional_flow',
                        'timeframe': timeframe,
                        'severity': 'high' if institutional_flow.get('pattern_clarity', 0.0) >= 0.9 else 'medium',
                        'details': institutional_flow,
                        'pattern_clarity': institutional_flow.get('pattern_clarity', 0.0),
                        'z_score': institutional_flow.get('z_score', 0.0),
                        'statistical_significance': institutional_flow.get('statistical_significance', 0.0),
                        'team_member': 'institutional_flow_analyzer'
                    })
                
                # Check divergence patterns
                divergence_analysis = analysis.get('divergence_analysis', {})
                if divergence_analysis.get('pattern_clarity', 0.0) >= confidence_threshold:
                    significant_patterns.append({
                        'type': 'divergence',
                        'timeframe': timeframe,
                        'severity': 'high' if divergence_analysis.get('pattern_clarity', 0.0) >= 0.9 else 'medium',
                        'details': divergence_analysis,
                        'pattern_clarity': divergence_analysis.get('pattern_clarity', 0.0),
                        'z_score': divergence_analysis.get('z_score', 0.0),
                        'statistical_significance': divergence_analysis.get('statistical_significance', 0.0),
                        'team_member': 'divergence_detector'
                    })
            
            # Add historical context validation to each pattern
            validated_patterns = []
            for pattern in significant_patterns:
                # Get pattern details
                pattern_type = pattern.get('type', 'unknown')
                symbol = pattern.get('symbol', 'BTC')
                timeframe = pattern.get('timeframe', '1m')
                
                # Validate pattern frequency
                frequency_validation = await self._validate_pattern_frequency(pattern_type, symbol, timeframe)
                
                # Add historical context to pattern
                pattern['historical_context'] = {
                    'frequency_validation': frequency_validation,
                    'is_historically_valid': frequency_validation.get('is_valid', True)
                }
                
                # Only include patterns that pass historical validation
                if frequency_validation.get('is_valid', True):
                    validated_patterns.append(pattern)
                else:
                    self.logger.info(f"Filtered out {pattern_type} pattern for {symbol} {timeframe} - too frequent")
            
            # Sort by pattern clarity (highest first)
            validated_patterns.sort(key=lambda x: x.get('pattern_clarity', 0.0), reverse=True)
            
            # Limit to top 3 most significant patterns to reduce noise
            significant_patterns = validated_patterns[:3]
            
        except Exception as e:
            self.logger.error(f"Failed to identify significant patterns: {e}")
        
        return significant_patterns
    
    def _parse_llm_insights(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """
        Parse LLM response for significant insights
        
        Args:
            llm_response: LLM response text
            
        Returns:
            Parsed insights or None
        """
        try:
            # Simple parsing - in a real implementation, this would be more sophisticated
            if any(keyword in llm_response.lower() for keyword in ['significant', 'unusual', 'anomaly', 'alert']):
                return {
                    'severity': 'high' if any(keyword in llm_response.lower() for keyword in ['critical', 'urgent', 'severe']) else 'medium',
                    'details': {'llm_insight': llm_response[:200] + "..." if len(llm_response) > 200 else llm_response},
                    'confidence': 0.7  # Default confidence for LLM insights
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to parse LLM insights: {e}")
            return None
    
    async def _publish_findings(self, analysis_results: Dict[str, Any]):
        """
        Publish significant findings to the database as strands
        
        Args:
            analysis_results: Analysis results with significant patterns
        """
        try:
            significant_patterns = analysis_results.get('significant_patterns', [])
            self.logger.info(f"Publishing {len(significant_patterns)} significant patterns")
            
            # Create individual pattern strands for each team member
            pattern_strands = []
            
            for i, pattern in enumerate(significant_patterns):
                self.logger.info(f"Publishing pattern {i+1}: {pattern.get('type', 'unknown')}")
                
                # Extract statistical measurements
                statistical_measurements = self._extract_statistical_measurements(pattern)
                
                # Create individual pattern strand
                pattern_strand = {
                    'id': f"raw_data_{pattern['type']}_{int(datetime.now().timestamp())}_{i}",
                    'kind': 'intelligence',  # Raw data creates intelligence strands, not signals
                    'module': 'alpha',
                    'agent_id': 'raw_data_intelligence',
                    'team_member': pattern.get('team_member', 'raw_data_intelligence_agent'),
                    'symbol': pattern.get('symbol', 'BTC'),
                    'timeframe': pattern.get('timeframe', '1m'),
                    'session_bucket': 'GLOBAL',
                    'regime': 'unknown',
                    'tags': [f"intelligence:raw_data:{pattern['type']}:{pattern.get('severity', 'medium')}", 'cil'],
                    'module_intelligence': {
                        'pattern_type': pattern['type'],
                        'statistical_measurements': statistical_measurements,
                        'analysis_timestamp': analysis_results['timestamp'],
                        'data_points': int(analysis_results.get('data_points', 0)),
                        'symbols': analysis_results.get('symbols', []),
                        'timeframe_analysis': analysis_results.get('timeframe_analysis', {}),
                        'cross_timeframe_patterns': analysis_results.get('cross_timeframe_patterns', [])
                    },
                    'sig_sigma': statistical_measurements.get('z_score', 0.0),  # Statistical significance
                    'confidence': statistical_measurements.get('pattern_clarity', 0.0),  # Pattern strength/clarity
                    'sig_direction': 'neutral',  # Raw data doesn't predict direction
                    'sig_confidence': None,  # Not used by raw data intelligence
                    'prediction_score': None,  # Not used by raw data intelligence
                    'outcome_score': None,  # Not used by raw data intelligence
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                pattern_strands.append(pattern_strand)
                
                # Publish individual pattern strand
                try:
                    result = self.supabase_manager.insert_strand(pattern_strand)
                    self.logger.info(f"Published {pattern['type']} pattern to database: {pattern_strand['id']}")
                except Exception as insert_error:
                    self.logger.error(f"Failed to insert pattern strand {pattern_strand['id']}: {insert_error}")
                    raise
            
            # Create compilation strand (RMC summary)
            if pattern_strands:
                await self._publish_compilation_strand(pattern_strands, analysis_results)
                
        except Exception as e:
            self.logger.error(f"Failed to publish findings: {e}")
    
    def _extract_statistical_measurements(self, pattern: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract statistical measurements from pattern data
        
        Args:
            pattern: Pattern data
            
        Returns:
            Dictionary with statistical measurements
        """
        try:
            details = pattern.get('details', {})
            
            # Extract statistical measurements based on pattern type
            if pattern['type'] == 'volume_spike':
                return {
                    'volume_ratio': details.get('volume_ratio', 1.0),
                    'z_score': details.get('z_score', 0.0),
                    'baseline_volume': details.get('baseline_volume', 0.0),
                    'current_volume': details.get('current_volume', 0.0),
                    'statistical_significance': details.get('statistical_significance', 0.0),
                    'pattern_clarity': details.get('pattern_clarity', 0.0),
                    'cross_timeframe_confirmation': details.get('cross_timeframe_confirmation', False),
                    'timeframes_confirmed': details.get('timeframes_confirmed', [])
                }
            elif pattern['type'] == 'divergence':
                return {
                    'divergence_strength': details.get('divergence_strength', 0.0),
                    'correlation_coefficient': details.get('correlation_coefficient', 0.0),
                    'statistical_significance': details.get('statistical_significance', 0.0),
                    'pattern_clarity': details.get('pattern_clarity', 0.0),
                    'divergence_type': details.get('divergence_type', 'unknown'),
                    'lookback_period': details.get('lookback_period', 0)
                }
            else:
                # Generic statistical measurements
                return {
                    'statistical_significance': details.get('statistical_significance', 0.0),
                    'pattern_clarity': details.get('pattern_clarity', 0.0),
                    'z_score': details.get('z_score', 0.0),
                    'correlation': details.get('correlation', 0.0),
                    'baseline_value': details.get('baseline_value', 0.0),
                    'current_value': details.get('current_value', 0.0)
                }
                
        except Exception as e:
            self.logger.error(f"Failed to extract statistical measurements: {e}")
            return {
                'statistical_significance': 0.0,
                'pattern_clarity': 0.0,
                'z_score': 0.0
            }
    
    async def _publish_compilation_strand(self, pattern_strands: List[Dict[str, Any]], analysis_results: Dict[str, Any]):
        """
        Publish compilation strand (RMC summary) to CIL
        
        Args:
            pattern_strands: List of individual pattern strands
            analysis_results: Full analysis results
        """
        try:
            # Create compilation strand
            compilation_strand = {
                'id': f"raw_data_compilation_{int(datetime.now().timestamp())}",
                'kind': 'intelligence',
                'module': 'alpha',
                'agent_id': 'raw_data_intelligence',
                'team_member': 'raw_data_intelligence_agent',
                'symbol': 'SYSTEM',
                'timeframe': 'system',
                'session_bucket': 'GLOBAL',
                'regime': 'system',
                'tags': ['intelligence:raw_data:compilation:5min_summary', 'cil'],
                'module_intelligence': {
                    'compilation_type': 'pattern_summary',
                    'period': '5_minutes',
                    'total_patterns': len(pattern_strands),
                    'pattern_links': [strand['id'] for strand in pattern_strands],
                    'pattern_types': list(set(pattern.get('type', 'unknown') for pattern in analysis_results.get('significant_patterns', []))),
                    'symbols_analyzed': analysis_results.get('symbols', []),
                    'timeframe_analysis': analysis_results.get('timeframe_analysis', {}),
                    'cross_timeframe_patterns': analysis_results.get('cross_timeframe_patterns', []),
                    'analysis_timestamp': analysis_results['timestamp'],
                    'data_points': int(analysis_results.get('data_points', 0))
                },
                'sig_sigma': 1.0,  # System compilation always has max signal strength
                'confidence': 1.0,  # System compilation always has max confidence
                'sig_direction': 'neutral',
                'sig_confidence': None,
                'prediction_score': None,
                'outcome_score': None,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Publish compilation strand
            result = self.supabase_manager.insert_strand(compilation_strand)
            self.logger.info(f"Published compilation strand to CIL: {compilation_strand['id']}")
            
        except Exception as e:
            self.logger.error(f"Failed to publish compilation strand: {e}")
            raise
    
    # ===== HISTORICAL CONTEXT METHODS =====
    
    async def _get_historical_patterns(self, pattern_type: str, symbol: str, timeframe: str, lookback_days: int = 30) -> List[Dict[str, Any]]:
        """
        Get historical patterns for validation and context
        
        Args:
            pattern_type: Type of pattern to search for
            symbol: Symbol to search for
            timeframe: Timeframe to search for
            lookback_days: Number of days to look back
            
        Returns:
            List of historical patterns
        """
        try:
            lookback_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            
            result = self.supabase_manager.client.table('ad_strands').select('*').eq(
                'kind', 'intelligence'
            ).eq('agent_id', 'raw_data_intelligence').eq('symbol', symbol).eq('timeframe', timeframe).eq(
                'pattern_type', pattern_type
            ).gte('created_at', lookback_date.isoformat()).order('created_at', desc=True).limit(100).execute()
            
            if result.data:
                # Pattern type is now filtered at database level
                historical_patterns = result.data
                
                self.logger.info(f"Found {len(historical_patterns)} historical {pattern_type} patterns for {symbol} {timeframe}")
                return historical_patterns
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to get historical patterns: {e}")
            return []
    
    async def _validate_pattern_frequency(self, pattern_type: str, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Validate pattern frequency to avoid false positives
        Focus on rapid repetition rather than total count
        
        Args:
            pattern_type: Type of pattern to validate
            symbol: Symbol to validate
            timeframe: Timeframe to validate
            
        Returns:
            Validation results with frequency analysis
        """
        try:
            # Get historical patterns from last 24 hours for rapid repetition check
            historical_patterns_24h = await self._get_historical_patterns(pattern_type, symbol, timeframe, 1)
            
            if not historical_patterns_24h:
                return {
                    'is_valid': True,
                    'frequency_analysis': {
                        'recent_count': 0,
                        'frequency_score': 1.0,
                        'validation_reason': 'no_recent_patterns',
                        'warning': None
                    }
                }
            
            # Calculate frequency metrics
            recent_count_24h = len(historical_patterns_24h)
            
            # Check for rapid repetition (3+ patterns in 1 hour)
            if recent_count_24h >= 3:
                # Check if they're clustered in time
                recent_times = []
                for pattern in historical_patterns_24h[-3:]:  # Last 3 patterns
                    try:
                        if isinstance(pattern.get('created_at'), str):
                            pattern_time = datetime.fromisoformat(pattern['created_at'].replace('Z', '+00:00'))
                        else:
                            pattern_time = pattern.get('created_at')
                        recent_times.append(pattern_time)
                    except:
                        continue
                
                if len(recent_times) >= 3:
                    time_span = (recent_times[-1] - recent_times[0]).total_seconds() / 3600  # hours
                    
                    if time_span < 1.0:  # 3+ patterns in less than 1 hour
                        return {
                            'is_valid': False,
                            'frequency_analysis': {
                                'recent_count': recent_count_24h,
                                'time_span_hours': time_span,
                                'frequency_score': 0.0,
                                'validation_reason': 'rapid_repetition',
                                'warning': f'3+ {pattern_type} patterns in {time_span:.1f} hours - possible noise'
                            }
                        }
            
            # Check for excessive frequency (30+ patterns in 1 day)
            if recent_count_24h >= 30:
                return {
                    'is_valid': False,
                    'frequency_analysis': {
                        'recent_count': recent_count_24h,
                        'frequency_score': 0.0,
                        'validation_reason': 'excessive_frequency',
                        'warning': f'30+ {pattern_type} patterns in 24 hours - excessive frequency'
                    }
                }
            
            # Calculate frequency score (penalize if more than 10 in 24 hours)
            frequency_score = max(0.0, 1.0 - (recent_count_24h / 20.0))
            
            # Determine warning level
            warning = None
            if recent_count_24h >= 20:
                warning = f'High frequency: {recent_count_24h} {pattern_type} patterns in 24 hours'
            elif recent_count_24h >= 10:
                warning = f'Moderate frequency: {recent_count_24h} {pattern_type} patterns in 24 hours'
            
            return {
                'is_valid': True,
                'frequency_analysis': {
                    'recent_count': recent_count_24h,
                    'frequency_score': frequency_score,
                    'validation_reason': 'acceptable_frequency',
                    'warning': warning
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to validate pattern frequency: {e}")
            return {
                'is_valid': True,
                'frequency_analysis': {
                    'recent_count': 0,
                    'frequency_score': 1.0,
                    'validation_reason': 'validation_error',
                    'warning': f'Validation error: {str(e)}'
                }
            }
    
    async def _get_historical_baselines(self, symbol: str, timeframe: str, lookback_days: int = 90) -> Dict[str, Any]:
        """
        Get historical baselines for better statistical calculations
        
        Args:
            symbol: Symbol to get baselines for
            timeframe: Timeframe to get baselines for
            lookback_days: Number of days to look back (default 90 for 3 months)
            
        Returns:
            Historical baseline statistics
        """
        try:
            lookback_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            
            # Get historical patterns for baseline calculation
            result = self.supabase_manager.client.table('ad_strands').select('*').eq(
                'kind', 'intelligence'
            ).eq('agent_id', 'raw_data_intelligence').eq('symbol', symbol).eq('timeframe', timeframe).gte(
                'created_at', lookback_date.isoformat()
            ).order('created_at', desc=True).limit(500).execute()
            
            if not result.data:
                return {
                    'volume_baseline': None,
                    'price_baseline': None,
                    'correlation_baseline': None,
                    'sample_size': 0,
                    'baseline_quality': 'insufficient_data'
                }
            
            # Extract statistical measurements from historical patterns
            z_scores = []
            volume_ratios = []
            correlations = []
            
            for strand in result.data:
                module_intelligence = strand.get('module_intelligence', {})
                if isinstance(module_intelligence, dict):
                    statistical_measurements = module_intelligence.get('statistical_measurements', {})
                    if isinstance(statistical_measurements, dict):
                        if 'z_score' in statistical_measurements:
                            z_scores.append(statistical_measurements['z_score'])
                        if 'volume_ratio' in statistical_measurements:
                            volume_ratios.append(statistical_measurements['volume_ratio'])
                        if 'correlation' in statistical_measurements:
                            correlations.append(statistical_measurements['correlation'])
            
            # Calculate baselines
            baselines = {
                'volume_baseline': {
                    'mean_ratio': np.mean(volume_ratios) if volume_ratios else 1.0,
                    'std_ratio': np.std(volume_ratios) if volume_ratios else 0.0,
                    'sample_size': len(volume_ratios)
                } if volume_ratios else None,
                'z_score_baseline': {
                    'mean_z': np.mean(z_scores) if z_scores else 0.0,
                    'std_z': np.std(z_scores) if z_scores else 1.0,
                    'sample_size': len(z_scores)
                } if z_scores else None,
                'correlation_baseline': {
                    'mean_correlation': np.mean(correlations) if correlations else 0.0,
                    'std_correlation': np.std(correlations) if correlations else 0.0,
                    'sample_size': len(correlations)
                } if correlations else None,
                'sample_size': len(result.data),
                'baseline_quality': 'good' if len(result.data) >= 50 else 'moderate' if len(result.data) >= 20 else 'poor'
            }
            
            self.logger.info(f"Calculated historical baselines for {symbol} {timeframe}: {baselines['sample_size']} samples, quality: {baselines['baseline_quality']}")
            return baselines
            
        except Exception as e:
            self.logger.error(f"Failed to get historical baselines: {e}")
            return {
                'volume_baseline': None,
                'price_baseline': None,
                'correlation_baseline': None,
                'sample_size': 0,
                'baseline_quality': 'error'
            }
    
    def _serialize_for_json(self, obj):
        """Serialize object for JSON compatibility"""
        import numpy as np
        
        if isinstance(obj, dict):
            return {k: self._serialize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_for_json(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif hasattr(obj, '__dict__'):
            return self._serialize_for_json(obj.__dict__)
        else:
            return obj
    
    # Message handlers
    async def _handle_raw_data_analysis_request(self, message):
        """Handle raw data analysis requests from other agents"""
        try:
            self.logger.info(f"Received raw data analysis request: {message.metadata.get('message_id')}")
            
            # Perform analysis
            market_data = await self._get_recent_market_data()
            if market_data is not None:
                analysis_results = await self._analyze_raw_data(market_data)
                
                # Respond with analysis results
                await self.communication_protocol.respond_to_message(
                    message.metadata.get('message_id', ''),
                    {
                        'analysis_results': analysis_results,
                        'status': 'completed',
                        'agent': self.agent_name
                    },
                    'action_taken'
                )
            else:
                await self.communication_protocol.respond_to_message(
                    message.metadata.get('message_id', ''),
                    {
                        'status': 'no_data_available',
                        'agent': self.agent_name
                    },
                    'error'
                )
                
        except Exception as e:
            self.logger.error(f"Failed to handle raw data analysis request: {e}")
    
    async def _handle_volume_analysis_request(self, message):
        """Handle volume analysis requests from other agents"""
        try:
            self.logger.info(f"Received volume analysis request: {message.metadata.get('message_id')}")
            
            # Perform volume analysis
            market_data = await self._get_recent_market_data()
            if market_data is not None:
                volume_results = await self._analyze_volume_patterns(market_data)
                
                await self.communication_protocol.respond_to_message(
                    message.metadata.get('message_id', ''),
                    {
                        'volume_analysis': volume_results,
                        'status': 'completed',
                        'agent': self.agent_name
                    },
                    'action_taken'
                )
            else:
                await self.communication_protocol.respond_to_message(
                    message.metadata.get('message_id', ''),
                    {
                        'status': 'no_data_available',
                        'agent': self.agent_name
                    },
                    'error'
                )
                
        except Exception as e:
            self.logger.error(f"Failed to handle volume analysis request: {e}")
    
    async def _handle_microstructure_analysis_request(self, message):
        """Handle microstructure analysis requests from other agents"""
        try:
            self.logger.info(f"Received microstructure analysis request: {message.metadata.get('message_id')}")
            
            # Perform microstructure analysis
            market_data = await self._get_recent_market_data()
            if market_data is not None:
                microstructure_results = await self._analyze_market_microstructure(market_data)
                
                await self.communication_protocol.respond_to_message(
                    message.metadata.get('message_id', ''),
                    {
                        'microstructure_analysis': microstructure_results,
                        'status': 'completed',
                        'agent': self.agent_name
                    },
                    'action_taken'
                )
            else:
                await self.communication_protocol.respond_to_message(
                    message.metadata.get('message_id', ''),
                    {
                        'status': 'no_data_available',
                        'agent': self.agent_name
                    },
                    'error'
                )
                
        except Exception as e:
            self.logger.error(f"Failed to handle microstructure analysis request: {e}")
    
    def get_agent_status(self) -> Dict[str, Any]:
        """
        Get current agent status
        
        Returns:
            Dictionary with agent status information
        """
        return {
            'agent_name': self.agent_name,
            'is_running': self.is_running,
            'capabilities': self.capabilities,
            'specializations': self.specializations,
            'available_tools': list(self.available_tools.keys()),
            'last_analysis_time': self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            'analysis_count': len(self.analysis_history),
            'communication_stats': self.communication_protocol.get_communication_stats()
        }
    
    # ===== ENHANCED LLM CONTROL METHODS =====
    
    async def get_context(self, analysis_type: str, data: Union[pd.DataFrame, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get relevant context from database using intelligent context injection
        
        Args:
            analysis_type: Type of analysis being performed
            data: Market data or analysis data
            
        Returns:
            Enhanced context with relevant lessons and patterns
        """
        try:
            # Prepare context request
            context_request = {
                'agent_name': self.agent_name,
                'analysis_type': analysis_type,
                'data': data,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'capabilities': self.capabilities,
                'available_tools': list(self.available_tools.keys())
            }
            
            # Get relevant context from database
            context = await self.context_system.get_relevant_context(context_request)
            
            self.logger.debug(f"Retrieved context for {analysis_type}: {len(context.get('generated_lessons', []))} lessons")
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to get context for {analysis_type}: {e}")
            return {
                'current_analysis': context_request,
                'generated_lessons': [],
                'similar_situations': [],
                'pattern_clusters': [],
                'error': str(e)
            }
    
    async def decide_tool_usage(self, context: Dict[str, Any], market_data: Union[pd.DataFrame, Dict[str, Any]]) -> Dict[str, Any]:
        """
        LLM decides what tools to use and how to configure them
        
        Args:
            context: Context from database
            market_data: Current market data
            
        Returns:
            Tool usage decision with configurations
        """
        try:
            # Prepare tool decision context
            tool_context = {
                'available_tools': self.available_tools,
                'capabilities': self.capabilities,
                'context': context,
                'market_data': market_data,
                'agent_name': self.agent_name
            }
            
            # Get LLM tool decision
            tool_decision = await self.llm_client.decide_tool_usage(tool_context)
            
            self.logger.info(f"LLM decided to use {len(tool_decision.get('tools_to_use', []))} tools")
            
            return tool_decision
            
        except Exception as e:
            self.logger.error(f"Failed to decide tool usage: {e}")
            # Fallback to using all available tools with default config
            return {
                'tools_to_use': list(self.available_tools.keys()),
                'tool_configurations': {tool: {} for tool in self.available_tools.keys()},
                'reasoning': f"Fallback due to error: {e}",
                'confidence': 0.3
            }
    
    async def store_results(self, results: Dict[str, Any], tool_decision: Dict[str, Any]) -> Optional[str]:
        """
        Store analysis results as strand for learning
        
        Args:
            results: Analysis results
            tool_decision: Tool usage decision
            
        Returns:
            Strand ID if successful, None otherwise
        """
        try:
            # Create strand content
            strand_content = {
                'analysis_results': results,
                'tool_decision': tool_decision,
                'agent_name': self.agent_name,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Create strand
            strand = {
                'content': strand_content,
                'tags': f"agent:{self.agent_name}:analysis:enhanced",
                'source_agent': self.agent_name,
                'analysis_type': results.get('analysis_type', 'unknown'),
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Store in database
            strand_id = await self.supabase_manager.create_strand(strand)
            
            if strand_id:
                self.logger.info(f"Stored analysis results as strand: {strand_id}")
                
                # Store in analysis history
                self.analysis_history.append({
                    'strand_id': strand_id,
                    'timestamp': datetime.now(timezone.utc),
                    'results': results,
                    'tool_decision': tool_decision
                })
                
                # Keep only last 100 analyses
                if len(self.analysis_history) > 100:
                    self.analysis_history = self.analysis_history[-100:]
            
            return strand_id
            
        except Exception as e:
            self.logger.error(f"Failed to store results: {e}")
            return None
    
    async def configure_tool(self, tool_name: str, configuration: Dict[str, Any]) -> bool:
        """
        Configure a specific tool based on LLM decision
        
        Args:
            tool_name: Name of the tool to configure
            configuration: Configuration parameters
            
        Returns:
            True if configuration successful
        """
        try:
            if tool_name not in self.available_tools:
                self.logger.warning(f"Tool {tool_name} not available to {self.agent_name}")
                return False
            
            # Get tool instance
            tool_instance = getattr(self, tool_name, None)
            if tool_instance is None:
                self.logger.warning(f"Tool instance {tool_name} not found")
                return False
            
            # Configure tool if it has configure method
            if hasattr(tool_instance, 'configure'):
                await tool_instance.configure(configuration)
                self.logger.info(f"Configured {tool_name} with {len(configuration)} parameters")
                return True
            else:
                self.logger.warning(f"Tool {tool_name} does not support configuration")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to configure tool {tool_name}: {e}")
            return False
    
    async def execute_enhanced_analysis(self, market_data: Union[pd.DataFrame, Dict[str, Any]], 
                                      analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Execute enhanced analysis with LLM control
        
        Args:
            market_data: Market data to analyze
            analysis_type: Type of analysis to perform
            
        Returns:
            Enhanced analysis results
        """
        try:
            # 1. Get relevant context from database
            context = await self.get_context(analysis_type, market_data)
            
            # 2. LLM decides what tools to use and how to configure them
            tool_decision = await self.decide_tool_usage(context, market_data)
            
            # 3. Configure tools based on LLM decision
            configured_tools = []
            for tool_name, config in tool_decision.get('tool_configurations', {}).items():
                if tool_name in tool_decision.get('tools_to_use', []):
                    success = await self.configure_tool(tool_name, config)
                    if success:
                        configured_tools.append(tool_name)
            
            # 4. Execute analysis with configured tools
            results = await self._execute_analysis_with_tools(
                market_data, tool_decision, configured_tools
            )
            
            # 5. Store results as strand for learning
            strand_id = await self.store_results(results, tool_decision)
            
            # 6. Update last analysis time
            self.last_analysis_time = datetime.now(timezone.utc)
            
            return {
                'analysis_results': results,
                'tool_decision': tool_decision,
                'configured_tools': configured_tools,
                'context_used': context,
                'strand_id': strand_id,
                'timestamp': self.last_analysis_time.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to execute enhanced analysis: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def _execute_analysis_with_tools(self, market_data: Union[pd.DataFrame, Dict[str, Any]], 
                                         tool_decision: Dict[str, Any], 
                                         configured_tools: List[str]) -> Dict[str, Any]:
        """
        Execute analysis with configured tools
        
        Args:
            market_data: Market data
            tool_decision: Tool usage decision
            configured_tools: List of successfully configured tools
            
        Returns:
            Analysis results
        """
        try:
            analysis_results = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data_points': len(market_data) if hasattr(market_data, '__len__') else 1,
                'symbols': market_data['symbol'].unique().tolist() if hasattr(market_data, 'columns') and 'symbol' in market_data.columns else [],
                'significant_patterns': [],
                'analysis_components': {},
                'tools_used': configured_tools,
                'confidence': tool_decision.get('confidence', 0.5)
            }
            
            # Execute analysis with each configured tool
            for tool_name in configured_tools:
                try:
                    if tool_name == 'divergence_detector':
                        result = await self._analyze_raw_data_divergences(market_data)
                        analysis_results['analysis_components']['divergences'] = result
                    elif tool_name == 'volume_analyzer':
                        result = await self._analyze_volume_patterns(market_data)
                        analysis_results['analysis_components']['volume'] = result
                    elif tool_name == 'microstructure_analyzer':
                        result = await self._analyze_market_microstructure(market_data)
                        analysis_results['analysis_components']['microstructure'] = result
                    elif tool_name == 'time_pattern_detector':
                        result = await self._analyze_time_based_patterns(market_data)
                        analysis_results['analysis_components']['time_based'] = result
                    elif tool_name == 'cross_asset_analyzer':
                        result = await self._analyze_cross_asset_patterns(market_data)
                        analysis_results['analysis_components']['cross_asset'] = result
                        
                except Exception as e:
                    self.logger.error(f"Failed to execute {tool_name}: {e}")
                    analysis_results['analysis_components'][tool_name] = {'error': str(e)}
            
            # Identify significant patterns
            significant_patterns = self._identify_significant_patterns(analysis_results)
            analysis_results['significant_patterns'] = significant_patterns
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Failed to execute analysis with tools: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    # ===== LLM-CONTROLLED SYSTEM MANAGEMENT METHODS =====
    
    async def llm_configure_divergence_detection(self, market_conditions: Dict[str, Any], 
                                               performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        LLM configures divergence detection parameters
        
        Args:
            market_conditions: Current market conditions
            performance_data: Recent performance data
            
        Returns:
            Configuration decision
        """
        try:
            # Get configurable parameters
            configurable_params = self.available_tools['divergence_detector']['configurable_parameters']
            
            # Prepare configuration context
            config_context = {
                'market_conditions': market_conditions,
                'performance_data': performance_data,
                'available_parameters': configurable_params,
                'tool_documentation': self.available_tools['divergence_detector']['documentation'],
                'agent_name': self.agent_name
            }
            
            # Get LLM configuration decision
            config_decision = await self.llm_client.optimize_divergence_detection(config_context)
            
            # Apply configuration
            if config_decision.get('optimized_config'):
                await self.configure_tool('divergence_detector', config_decision['optimized_config'])
            
            # Store configuration decision as strand
            await self.store_results({
                'action': 'divergence_detection_configuration',
                'config': config_decision
            }, config_decision)
            
            return config_decision
            
        except Exception as e:
            self.logger.error(f"Failed to configure divergence detection: {e}")
            return {'error': str(e)}
    
    async def llm_configure_volume_analysis(self, market_conditions: Dict[str, Any], 
                                          performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        LLM configures volume analysis parameters
        
        Args:
            market_conditions: Current market conditions
            performance_data: Recent performance data
            
        Returns:
            Configuration decision
        """
        try:
            # Get configurable parameters
            configurable_params = self.available_tools['volume_analyzer']['configurable_parameters']
            
            # Prepare configuration context
            config_context = {
                'market_conditions': market_conditions,
                'performance_data': performance_data,
                'available_parameters': configurable_params,
                'tool_documentation': self.available_tools['volume_analyzer']['documentation'],
                'agent_name': self.agent_name
            }
            
            # Get LLM configuration decision
            config_decision = await self.llm_client.optimize_volume_analysis(config_context)
            
            # Apply configuration
            if config_decision.get('optimized_config'):
                await self.configure_tool('volume_analyzer', config_decision['optimized_config'])
            
            # Store configuration decision as strand
            await self.store_results({
                'action': 'volume_analysis_configuration',
                'config': config_decision
            }, config_decision)
            
            return config_decision
            
        except Exception as e:
            self.logger.error(f"Failed to configure volume analysis: {e}")
            return {'error': str(e)}
    
    async def llm_configure_microstructure_analysis(self, market_conditions: Dict[str, Any], 
                                                  performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        LLM configures microstructure analysis parameters
        
        Args:
            market_conditions: Current market conditions
            performance_data: Recent performance data
            
        Returns:
            Configuration decision
        """
        try:
            # Get configurable parameters
            configurable_params = self.available_tools['microstructure_analyzer']['configurable_parameters']
            
            # Prepare configuration context
            config_context = {
                'market_conditions': market_conditions,
                'performance_data': performance_data,
                'available_parameters': configurable_params,
                'tool_documentation': self.available_tools['microstructure_analyzer']['documentation'],
                'agent_name': self.agent_name
            }
            
            # Get LLM configuration decision
            config_decision = await self.llm_client.optimize_microstructure_analysis(config_context)
            
            # Apply configuration
            if config_decision.get('optimized_config'):
                await self.configure_tool('microstructure_analyzer', config_decision['optimized_config'])
            
            # Store configuration decision as strand
            await self.store_results({
                'action': 'microstructure_analysis_configuration',
                'config': config_decision
            }, config_decision)
            
            return config_decision
            
        except Exception as e:
            self.logger.error(f"Failed to configure microstructure analysis: {e}")
            return {'error': str(e)}
    
    async def llm_configure_time_based_patterns(self, market_conditions: Dict[str, Any], 
                                              performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        LLM configures time-based pattern detection parameters
        
        Args:
            market_conditions: Current market conditions
            performance_data: Recent performance data
            
        Returns:
            Configuration decision
        """
        try:
            # Get configurable parameters
            configurable_params = self.available_tools['time_pattern_detector']['configurable_parameters']
            
            # Prepare configuration context
            config_context = {
                'market_conditions': market_conditions,
                'performance_data': performance_data,
                'available_parameters': configurable_params,
                'tool_documentation': self.available_tools['time_pattern_detector']['documentation'],
                'agent_name': self.agent_name
            }
            
            # Get LLM configuration decision
            config_decision = await self.llm_client.optimize_time_pattern_detection(config_context)
            
            # Apply configuration
            if config_decision.get('optimized_config'):
                await self.configure_tool('time_pattern_detector', config_decision['optimized_config'])
            
            # Store configuration decision as strand
            await self.store_results({
                'action': 'time_pattern_detection_configuration',
                'config': config_decision
            }, config_decision)
            
            return config_decision
            
        except Exception as e:
            self.logger.error(f"Failed to configure time-based patterns: {e}")
            return {'error': str(e)}
    
    async def llm_configure_cross_asset_analysis(self, market_conditions: Dict[str, Any], 
                                               performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        LLM configures cross-asset analysis parameters
        
        Args:
            market_conditions: Current market conditions
            performance_data: Recent performance data
            
        Returns:
            Configuration decision
        """
        try:
            # Get configurable parameters
            configurable_params = self.available_tools['cross_asset_analyzer']['configurable_parameters']
            
            # Prepare configuration context
            config_context = {
                'market_conditions': market_conditions,
                'performance_data': performance_data,
                'available_parameters': configurable_params,
                'tool_documentation': self.available_tools['cross_asset_analyzer']['documentation'],
                'agent_name': self.agent_name
            }
            
            # Get LLM configuration decision
            config_decision = await self.llm_client.optimize_cross_asset_analysis(config_context)
            
            # Apply configuration
            if config_decision.get('optimized_config'):
                await self.configure_tool('cross_asset_analyzer', config_decision['optimized_config'])
            
            # Store configuration decision as strand
            await self.store_results({
                'action': 'cross_asset_analysis_configuration',
                'config': config_decision
            }, config_decision)
            
            return config_decision
            
        except Exception as e:
            self.logger.error(f"Failed to configure cross-asset analysis: {e}")
            return {'error': str(e)}
