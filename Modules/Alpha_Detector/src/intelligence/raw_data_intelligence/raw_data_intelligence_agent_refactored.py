"""
Raw Data Intelligence Agent (Refactored)

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

from .team_coordination import TeamCoordination
from .llm_coordination import LLMCoordination
from .strand_creation import StrandCreation
from src.core_detection.multi_timeframe_processor import MultiTimeframeProcessor


class RawDataIntelligenceAgent:
    """
    Raw Data Intelligence Agent (Refactored)
    
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
        
        # Initialize refactored components
        self.team_coordination = TeamCoordination()
        self.llm_coordination = LLMCoordination(llm_client)
        self.strand_creation = StrandCreation(supabase_manager)
        
        # Multi-timeframe processor
        self.multi_timeframe_processor = MultiTimeframeProcessor()
        
        # Timeframe-dependent analysis windows
        self.timeframe_windows = {
            '1m': timedelta(hours=4),    # 240 candles
            '5m': timedelta(hours=20),   # 240 candles  
            '15m': timedelta(hours=60),  # 240 candles
            '1h': timedelta(days=10)     # 240 candles
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
                        await self._publish_findings(analysis_results, market_data)
                
                # Sleep for 5 minutes before next analysis
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
        Enhanced multi-timeframe raw data analysis - PROCESSES ONE ASSET AT A TIME
        
        Args:
            market_data_1m: DataFrame with 1-minute OHLCV data
            
        Returns:
            Dictionary with coordinated analysis results for all assets
        """
        try:
            # Get unique symbols
            symbols = market_data_1m['symbol'].unique().tolist() if 'symbol' in market_data_1m.columns else ['UNKNOWN']
            
            # Limit to max 20 assets to avoid overwhelming the system
            if len(symbols) > 20:
                self.logger.warning(f"Too many assets ({len(symbols)}), processing only first 20")
                symbols = symbols[:20]
            
            all_asset_results = {}
            
            # Process each asset individually
            for symbol in symbols:
                self.logger.info(f"Processing asset: {symbol}")
                
                # Filter data for this symbol
                symbol_data = market_data_1m[market_data_1m['symbol'] == symbol].copy()
                
                if symbol_data.empty:
                    self.logger.warning(f"No data for symbol {symbol}")
                    continue
                
                # Analyze this single asset
                asset_result = await self._analyze_single_asset(symbol_data)
                all_asset_results[symbol] = asset_result
            
            # Create overall summary
            overall_results = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data_points': len(market_data_1m),
                'symbols': symbols,
                'asset_count': len(all_asset_results),
                'asset_results': all_asset_results,
                'total_patterns': sum(len(result.get('significant_patterns', [])) for result in all_asset_results.values()),
                'analysis_summary': self._create_analysis_summary(all_asset_results)
            }
            
            # Store analysis history
            self.analysis_history.append(overall_results)
            if len(self.analysis_history) > 100:  # Keep last 100 analyses
                self.analysis_history = self.analysis_history[-100:]
            
            self.last_analysis_time = datetime.now(timezone.utc)
            
            return overall_results
            
        except Exception as e:
            self.logger.error(f"Enhanced raw data analysis failed: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    async def _analyze_single_asset(self, symbol_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze a single asset with all team members
        
        Args:
            symbol_data: DataFrame with 1-minute OHLCV data for one symbol
            
        Returns:
            Dictionary with analysis results for this asset
        """
        try:
            symbol = symbol_data['symbol'].iloc[0] if 'symbol' in symbol_data.columns else 'UNKNOWN'
            
            # 1. Roll up to multiple timeframes for this asset
            multi_timeframe_data = self.multi_timeframe_processor.process_multi_timeframe(symbol_data)
            
            analysis_results = {
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'data_points': len(symbol_data),
                'significant_patterns': [],
                'team_analysis': {},
                'coordinated_insights': [],
                'cil_recommendations': []
            }
            
            # 2. COORDINATE analysis from different team members for this asset
            team_analysis = await self.team_coordination.coordinate_team_analysis(symbol_data, multi_timeframe_data)
            analysis_results['team_analysis'] = team_analysis
            
            # 3. USE LLM FOR META-ANALYSIS AND COORDINATION for this asset
            llm_coordination_results = await self.llm_coordination.perform_llm_coordination(team_analysis, analysis_results, symbol_data)
            analysis_results.update(llm_coordination_results)
            
            # 4. Publish findings for this asset
            await self._publish_findings(analysis_results, symbol_data)
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Single asset analysis failed for {symbol}: {e}")
            return {'error': str(e), 'symbol': symbol, 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    def _create_analysis_summary(self, all_asset_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create summary of analysis across all assets
        
        Args:
            all_asset_results: Results from all assets
            
        Returns:
            Summary statistics and insights
        """
        try:
            total_assets = len(all_asset_results)
            assets_with_patterns = 0
            total_patterns = 0
            pattern_types = set()
            confidence_scores = []
            
            for symbol, result in all_asset_results.items():
                if 'error' not in result:
                    patterns = result.get('significant_patterns', [])
                    if patterns:
                        assets_with_patterns += 1
                        total_patterns += len(patterns)
                        for pattern in patterns:
                            pattern_types.add(pattern.get('type', 'unknown'))
                    
                    # Collect confidence scores
                    team_analysis = result.get('team_analysis', {})
                    for analyzer, analysis in team_analysis.items():
                        if 'error' not in analysis:
                            confidence = analysis.get('confidence', 0)
                            confidence_scores.append(confidence)
            
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            return {
                'total_assets_analyzed': total_assets,
                'assets_with_patterns': assets_with_patterns,
                'pattern_detection_rate': assets_with_patterns / total_assets if total_assets > 0 else 0,
                'total_patterns_found': total_patterns,
                'unique_pattern_types': list(pattern_types),
                'average_confidence': avg_confidence,
                'high_confidence_assets': sum(1 for scores in confidence_scores if scores > 0.7),
                'analysis_quality': 'excellent' if avg_confidence > 0.8 else 'good' if avg_confidence > 0.6 else 'moderate'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create analysis summary: {e}")
            return {'error': str(e)}
    
    async def _publish_findings(self, analysis_results: Dict[str, Any], market_data: pd.DataFrame):
        """
        Publish findings as strands - LLM-COORDINATED approach:
        1. Individual strands per team member analysis
        2. Overview strand with LLM meta-analysis results
        3. Overview strand tags CIL for further processing
        
        Args:
            analysis_results: Analysis results with LLM coordination
            market_data: Market data for context
        """
        try:
            team_analysis = analysis_results.get('team_analysis', {})
            meta_analysis = analysis_results.get('meta_analysis', {})
            cil_recommendations = analysis_results.get('cil_recommendations', [])
            
            self.logger.info(f"Publishing team analysis from {len(team_analysis)} analyzers")
            
            # 1. CREATE INDIVIDUAL STRANDS - one per team member analysis
            individual_strand_ids = []
            
            for analyzer_name, analysis in team_analysis.items():
                if 'error' not in analysis:
                    individual_strand_id = await self.strand_creation.create_individual_analyzer_strand(
                        analyzer_name, analysis, analysis_results, market_data
                    )
                    if individual_strand_id:
                        individual_strand_ids.append(individual_strand_id)
            
            # 2. CREATE OVERVIEW STRAND - with LLM meta-analysis results
            overview_strand_id = await self.strand_creation.create_overview_strand_with_llm_results(
                individual_strand_ids, team_analysis, meta_analysis, 
                cil_recommendations, analysis_results, market_data
            )
            
            self.logger.info(f"Published {len(individual_strand_ids)} individual strands and 1 overview strand")
            
            return {
                'individual_strands': individual_strand_ids,
                'overview_strand': overview_strand_id,
                'total_strands': len(individual_strand_ids) + 1
            }
            
        except Exception as e:
            self.logger.error(f"Failed to publish findings: {e}")
            return {'error': str(e)}
    
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
                # Use team coordination for volume analysis
                team_analysis = await self.team_coordination.coordinate_team_analysis(market_data, {})
                volume_results = team_analysis.get('volume', {})
                
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
                # Use team coordination for microstructure analysis
                team_analysis = await self.team_coordination.coordinate_team_analysis(market_data, {})
                microstructure_results = team_analysis.get('microstructure', {})
                
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
            'last_analysis_time': self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            'analysis_count': len(self.analysis_history),
            'communication_stats': self.communication_protocol.get_communication_stats()
        }
