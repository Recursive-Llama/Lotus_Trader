"""
Raw Data Intelligence Agent

The main agent for raw data intelligence that monitors OHLCV data for patterns
that traditional indicators miss. This agent operates at the most fundamental
level of market data analysis.
"""

import asyncio
import logging
from datetime import datetime, timezone
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
                
                # Sleep for 60 seconds before next analysis
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                self.logger.info("Raw data analysis loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in raw data analysis loop: {e}")
                await asyncio.sleep(120)  # Wait longer on error
    
    async def _get_recent_market_data(self) -> Optional[pd.DataFrame]:
        """
        Get recent market data from the database
        
        Returns:
            DataFrame with recent OHLCV data or None if no data
        """
        try:
            # Get data from last 2 hours
            two_hours_ago = datetime.now(timezone.utc).timestamp() - 7200
            
            result = self.supabase_manager.client.table('alpha_market_data_1m').select('*').gte(
                'timestamp', two_hours_ago
            ).order('timestamp', desc=True).limit(1000).execute()
            
            if result.data:
                df = pd.DataFrame(result.data)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                return df
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get recent market data: {e}")
            return None
    
    async def _analyze_raw_data(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform comprehensive raw data analysis
        
        Args:
            market_data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with analysis results
        """
        try:
            analysis_results = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data_points': len(market_data),
                'symbols': market_data['symbol'].unique().tolist() if 'symbol' in market_data.columns else [],
                'significant_patterns': [],
                'analysis_components': {}
            }
            
            # 1. Market Microstructure Analysis
            microstructure_results = await self._analyze_market_microstructure(market_data)
            analysis_results['analysis_components']['microstructure'] = microstructure_results
            
            # 2. Volume Pattern Analysis
            volume_results = await self._analyze_volume_patterns(market_data)
            analysis_results['analysis_components']['volume'] = volume_results
            
            # 3. Time-based Pattern Analysis
            time_results = await self._analyze_time_based_patterns(market_data)
            analysis_results['analysis_components']['time_based'] = time_results
            
            # 4. Cross-asset Analysis
            cross_asset_results = await self._analyze_cross_asset_patterns(market_data)
            analysis_results['analysis_components']['cross_asset'] = cross_asset_results
            
            # 5. Raw Data Divergence Analysis
            divergence_results = await self._analyze_raw_data_divergences(market_data)
            analysis_results['analysis_components']['divergences'] = divergence_results
            
            # 6. LLM-Enhanced Pattern Detection
            llm_results = await self._llm_enhanced_analysis(market_data, analysis_results)
            analysis_results['analysis_components']['llm_enhanced'] = llm_results
            
            # 7. Identify significant patterns
            significant_patterns = self._identify_significant_patterns(analysis_results)
            analysis_results['significant_patterns'] = significant_patterns
            
            # Store analysis history
            self.analysis_history.append(analysis_results)
            if len(self.analysis_history) > 100:  # Keep last 100 analyses
                self.analysis_history = self.analysis_history[-100:]
            
            self.last_analysis_time = datetime.now(timezone.utc)
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Failed to analyze raw data: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
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
        Publish significant findings to other agents
        
        Args:
            analysis_results: Analysis results with significant patterns
        """
        try:
            significant_patterns = analysis_results.get('significant_patterns', [])
            
            for pattern in significant_patterns:
                # Create content for publication
                content = {
                    'pattern_type': pattern['type'],
                    'severity': pattern['severity'],
                    'confidence': pattern['confidence'],
                    'details': pattern['details'],
                    'analysis_timestamp': analysis_results['timestamp'],
                    'agent': self.agent_name,
                    'data_points': analysis_results['data_points'],
                    'symbols': analysis_results['symbols']
                }
                
                # Create appropriate tags
                tags = f"intelligence:raw_data:{pattern['type']}:{pattern['severity']}"
                
                # Publish finding
                message_id = await self.communication_protocol.publish_finding(
                    content, tags, priority=pattern['severity']
                )
                
                if message_id:
                    self.logger.info(f"Published {pattern['type']} finding: {message_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to publish findings: {e}")
    
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
