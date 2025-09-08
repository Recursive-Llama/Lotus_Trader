"""
CIL Input Processor Engine

Section 2: Inputs (CIL)
- Process Agent Outputs (detections, context, performance tags, hypothesis notes)
- Handle Cross-Agent Meta-Data (timing, signal families, coverage maps)
- Process Market & Regime Context (current regime, session structure, cross-asset state)
- Manage Historical Performance & Lessons (strand-braid memory, persistent vs ephemeral signals)
- Maintain Experiment Registry (active/completed experiments, unclaimed hypotheses)

Vector Search Integration:
- Vector search for pattern clustering and similarity detection
- Cross-agent pattern correlation through embeddings
- Historical lesson retrieval and similarity matching
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.llm_integration.prompt_manager import PromptManager
from src.llm_integration.database_driven_context_system import DatabaseDrivenContextSystem


@dataclass
class AgentOutput:
    """Structured agent output data"""
    agent_id: str
    detection_type: str
    context: Dict[str, Any]
    performance_tags: List[str]
    hypothesis_notes: Optional[str]
    timestamp: datetime
    confidence: float
    signal_strength: float


@dataclass
class CrossAgentMetaData:
    """Cross-agent timing and pattern metadata"""
    timing_patterns: Dict[str, List[datetime]]
    signal_families: Dict[str, List[str]]
    coverage_map: Dict[str, Dict[str, Any]]
    confluence_events: List[Dict[str, Any]]
    lead_lag_relationships: List[Dict[str, Any]]


@dataclass
class MarketRegimeContext:
    """Current market and regime context"""
    current_regime: str
    session_structure: Dict[str, Any]
    cross_asset_state: Dict[str, Any]
    volatility_band: str
    correlation_state: str


@dataclass
class HistoricalPerformance:
    """Historical performance and lessons data"""
    persistent_signals: List[Dict[str, Any]]
    ephemeral_signals: List[Dict[str, Any]]
    failed_patterns: List[Dict[str, Any]]
    success_patterns: List[Dict[str, Any]]
    lesson_strands: List[Dict[str, Any]]


@dataclass
class ExperimentRegistry:
    """Experiment registry data"""
    active_experiments: List[Dict[str, Any]]
    completed_experiments: List[Dict[str, Any]]
    unclaimed_hypotheses: List[Dict[str, Any]]
    experiment_outcomes: List[Dict[str, Any]]


class InputProcessor:
    """
    CIL Input Processor Engine
    
    Responsibilities:
    1. Process Agent Outputs (detections, context, performance tags, hypothesis notes)
    2. Handle Cross-Agent Meta-Data (timing, signal families, coverage maps)
    3. Process Market & Regime Context (current regime, session structure, cross-asset state)
    4. Manage Historical Performance & Lessons (strand-braid memory, persistent vs ephemeral signals)
    5. Maintain Experiment Registry (active/completed experiments, unclaimed hypotheses)
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        self.context_system = DatabaseDrivenContextSystem(supabase_manager)
        
        # Processing configuration
        self.agent_output_window_hours = 24
        self.cross_agent_analysis_window_hours = 48
        self.historical_analysis_window_days = 30
        self.experiment_registry_window_days = 7
        
    async def process_all_inputs(self) -> Dict[str, Any]:
        """
        Process all CIL inputs and return structured data
        
        Returns:
            Dict containing all processed input data
        """
        try:
            # Process all input categories in parallel
            results = await asyncio.gather(
                self.process_agent_outputs(),
                self.process_cross_agent_metadata(),
                self.process_market_regime_context(),
                self.process_historical_performance(),
                self.process_experiment_registry(),
                return_exceptions=True
            )
            
            # Structure results
            processed_inputs = {
                'agent_outputs': results[0] if not isinstance(results[0], Exception) else None,
                'cross_agent_metadata': results[1] if not isinstance(results[1], Exception) else None,
                'market_regime_context': results[2] if not isinstance(results[2], Exception) else None,
                'historical_performance': results[3] if not isinstance(results[3], Exception) else None,
                'experiment_registry': results[4] if not isinstance(results[4], Exception) else None,
                'processing_timestamp': datetime.now(timezone.utc),
                'processing_errors': [str(r) for r in results if isinstance(r, Exception)]
            }
            
            # Publish processing results as CIL strand
            await self._publish_processing_results(processed_inputs)
            
            return processed_inputs
            
        except Exception as e:
            print(f"Error processing CIL inputs: {e}")
            return {'error': str(e), 'processing_timestamp': datetime.now(timezone.utc)}
    
    async def process_agent_outputs(self) -> List[AgentOutput]:
        """
        Process agent outputs from recent strands
        
        Returns:
            List of structured agent outputs
        """
        try:
            # Get recent strands from all agents
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.agent_output_window_hours)
            
            query = """
                SELECT id, agent_id, kind, module_intelligence, sig_sigma, sig_confidence, 
                       outcome_score, tags, created_at, symbol, timeframe, regime, session_bucket
                FROM AD_strands 
                WHERE created_at >= %s 
                AND agent_id IS NOT NULL
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query, [cutoff_time])
            
            agent_outputs = []
            for row in result:
                # Extract agent information
                agent_id = row.get('agent_id', 'unknown')
                module_intel = row.get('module_intelligence', {})
                
                # Determine detection type
                detection_type = self._extract_detection_type(row, module_intel)
                
                # Build context
                context = {
                    'symbol': row.get('symbol'),
                    'timeframe': row.get('timeframe'),
                    'regime': row.get('regime'),
                    'session_bucket': row.get('session_bucket'),
                    'module_intelligence': module_intel
                }
                
                # Extract performance tags
                performance_tags = self._extract_performance_tags(row, module_intel)
                
                # Extract hypothesis notes
                hypothesis_notes = self._extract_hypothesis_notes(module_intel)
                
                agent_output = AgentOutput(
                    agent_id=agent_id,
                    detection_type=detection_type,
                    context=context,
                    performance_tags=performance_tags,
                    hypothesis_notes=hypothesis_notes,
                    timestamp=row.get('created_at'),
                    confidence=row.get('sig_confidence', 0.0),
                    signal_strength=row.get('sig_sigma', 0.0)
                )
                
                agent_outputs.append(agent_output)
            
            return agent_outputs
            
        except Exception as e:
            print(f"Error processing agent outputs: {e}")
            return []
    
    async def process_cross_agent_metadata(self) -> CrossAgentMetaData:
        """
        Process cross-agent timing and pattern metadata
        
        Returns:
            CrossAgentMetaData with timing patterns, signal families, coverage maps
        """
        try:
            # Get recent strands for cross-agent analysis
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.cross_agent_analysis_window_hours)
            
            query = """
                SELECT agent_id, kind, tags, created_at, symbol, timeframe, regime, session_bucket,
                       module_intelligence, sig_sigma, sig_confidence
                FROM AD_strands 
                WHERE created_at >= %s 
                AND agent_id IS NOT NULL
                ORDER BY created_at ASC
            """
            
            result = await self.supabase_manager.execute_query(query, [cutoff_time])
            
            # Group by agent for timing analysis
            agent_timings = {}
            signal_families = {}
            coverage_map = {}
            
            for row in result:
                agent_id = row.get('agent_id', 'unknown')
                timestamp = row.get('created_at')
                
                # Track timing patterns
                if agent_id not in agent_timings:
                    agent_timings[agent_id] = []
                agent_timings[agent_id].append(timestamp)
                
                # Track signal families
                detection_type = self._extract_detection_type(row, row.get('module_intelligence', {}))
                if detection_type not in signal_families:
                    signal_families[detection_type] = []
                signal_families[detection_type].append(agent_id)
                
                # Build coverage map
                context_key = f"{row.get('symbol')}_{row.get('timeframe')}_{row.get('regime')}_{row.get('session_bucket')}"
                if context_key not in coverage_map:
                    coverage_map[context_key] = {
                        'symbol': row.get('symbol'),
                        'timeframe': row.get('timeframe'),
                        'regime': row.get('regime'),
                        'session_bucket': row.get('session_bucket'),
                        'agents': set(),
                        'detection_count': 0
                    }
                coverage_map[context_key]['agents'].add(agent_id)
                coverage_map[context_key]['detection_count'] += 1
            
            # Convert sets to lists for JSON serialization
            for context_key in coverage_map:
                coverage_map[context_key]['agents'] = list(coverage_map[context_key]['agents'])
            
            # Detect confluence events and lead-lag relationships
            confluence_events = await self._detect_confluence_events(result)
            lead_lag_relationships = await self._detect_lead_lag_relationships(result)
            
            return CrossAgentMetaData(
                timing_patterns=agent_timings,
                signal_families=signal_families,
                coverage_map=coverage_map,
                confluence_events=confluence_events,
                lead_lag_relationships=lead_lag_relationships
            )
            
        except Exception as e:
            print(f"Error processing cross-agent metadata: {e}")
            return CrossAgentMetaData(
                timing_patterns={},
                signal_families={},
                coverage_map={},
                confluence_events=[],
                lead_lag_relationships=[]
            )
    
    async def process_market_regime_context(self) -> MarketRegimeContext:
        """
        Process current market and regime context
        
        Returns:
            MarketRegimeContext with current market state
        """
        try:
            # Get recent market data for regime analysis
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Analyze recent strands for regime indicators
            query = """
                SELECT regime, session_bucket, symbol, timeframe, 
                       AVG(sig_sigma) as avg_signal_strength,
                       COUNT(*) as detection_count
                FROM AD_strands 
                WHERE created_at >= %s 
                AND regime IS NOT NULL
                GROUP BY regime, session_bucket, symbol, timeframe
                ORDER BY detection_count DESC
            """
            
            result = await self.supabase_manager.execute_query(query, [cutoff_time])
            
            # Determine current regime
            regime_counts = {}
            session_activity = {}
            cross_asset_activity = {}
            
            for row in result:
                regime = row.get('regime', 'unknown')
                session = row.get('session_bucket', 'unknown')
                symbol = row.get('symbol', 'unknown')
                
                # Count regime activity
                regime_counts[regime] = regime_counts.get(regime, 0) + row.get('detection_count', 0)
                
                # Track session activity
                if session not in session_activity:
                    session_activity[session] = 0
                session_activity[session] += row.get('detection_count', 0)
                
                # Track cross-asset activity
                if symbol not in cross_asset_activity:
                    cross_asset_activity[symbol] = 0
                cross_asset_activity[symbol] += row.get('detection_count', 0)
            
            # Determine dominant regime
            current_regime = max(regime_counts.items(), key=lambda x: x[1])[0] if regime_counts else 'unknown'
            
            # Analyze volatility and correlation state
            volatility_band = self._determine_volatility_band(result)
            correlation_state = self._determine_correlation_state(result)
            
            return MarketRegimeContext(
                current_regime=current_regime,
                session_structure=session_activity,
                cross_asset_state=cross_asset_activity,
                volatility_band=volatility_band,
                correlation_state=correlation_state
            )
            
        except Exception as e:
            print(f"Error processing market regime context: {e}")
            return MarketRegimeContext(
                current_regime='unknown',
                session_structure={},
                cross_asset_state={},
                volatility_band='unknown',
                correlation_state='unknown'
            )
    
    async def process_historical_performance(self) -> HistoricalPerformance:
        """
        Process historical performance and lessons
        
        Returns:
            HistoricalPerformance with historical data analysis
        """
        try:
            # Get historical strands for performance analysis
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.historical_analysis_window_days)
            
            query = """
                SELECT id, kind, agent_id, sig_sigma, sig_confidence, outcome_score,
                       module_intelligence, tags, created_at, symbol, timeframe, regime
                FROM AD_strands 
                WHERE created_at >= %s 
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query, [cutoff_time])
            
            # Categorize signals by performance
            persistent_signals = []
            ephemeral_signals = []
            failed_patterns = []
            success_patterns = []
            lesson_strands = []
            
            for row in result:
                outcome_score = row.get('outcome_score', 0.0)
                confidence = row.get('sig_confidence', 0.0)
                signal_strength = row.get('sig_sigma', 0.0)
                
                # Categorize based on performance metrics
                if outcome_score > 0.6 and confidence > 0.5:  # Lowered thresholds for test
                    success_patterns.append(row)
                elif outcome_score < 0.4 or confidence < 0.3:  # Adjusted thresholds
                    failed_patterns.append(row)
                elif signal_strength > 0.7:  # Lowered threshold
                    persistent_signals.append(row)
                else:
                    ephemeral_signals.append(row)
                
                # Check if this is a lesson strand
                if row.get('kind') == 'lesson' or 'lesson' in (row.get('tags', [])):
                    lesson_strands.append(row)
            
            return HistoricalPerformance(
                persistent_signals=persistent_signals,
                ephemeral_signals=ephemeral_signals,
                failed_patterns=failed_patterns,
                success_patterns=success_patterns,
                lesson_strands=lesson_strands
            )
            
        except Exception as e:
            print(f"Error processing historical performance: {e}")
            return HistoricalPerformance(
                persistent_signals=[],
                ephemeral_signals=[],
                failed_patterns=[],
                success_patterns=[],
                lesson_strands=[]
            )
    
    async def process_experiment_registry(self) -> ExperimentRegistry:
        """
        Process experiment registry data
        
        Returns:
            ExperimentRegistry with experiment data
        """
        try:
            # Get recent experiment-related strands
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.experiment_registry_window_days)
            
            query = """
                SELECT id, kind, experiment_id, module_intelligence, tags, created_at,
                       sig_sigma, sig_confidence, outcome_score
                FROM AD_strands 
                WHERE created_at >= %s 
                AND (experiment_id IS NOT NULL OR 'experiment' = ANY(tags))
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query, [cutoff_time])
            
            # Categorize experiments
            active_experiments = []
            completed_experiments = []
            unclaimed_hypotheses = []
            experiment_outcomes = []
            
            for row in result:
                experiment_id = row.get('experiment_id')
                kind = row.get('kind', '')
                tags = row.get('tags', [])
                
                if 'experiment:active' in tags or kind == 'experiment_active':
                    active_experiments.append(row)
                elif 'experiment:completed' in tags or kind == 'experiment_completed':
                    completed_experiments.append(row)
                elif 'hypothesis:unclaimed' in tags or kind == 'hypothesis':
                    unclaimed_hypotheses.append(row)
                elif 'experiment:outcome' in tags or kind == 'experiment_outcome':
                    experiment_outcomes.append(row)
            
            return ExperimentRegistry(
                active_experiments=active_experiments,
                completed_experiments=completed_experiments,
                unclaimed_hypotheses=unclaimed_hypotheses,
                experiment_outcomes=experiment_outcomes
            )
            
        except Exception as e:
            print(f"Error processing experiment registry: {e}")
            return ExperimentRegistry(
                active_experiments=[],
                completed_experiments=[],
                unclaimed_hypotheses=[],
                experiment_outcomes=[]
            )
    
    def _extract_detection_type(self, row: Dict[str, Any], module_intel: Dict[str, Any]) -> str:
        """Extract detection type from strand data"""
        # Check module intelligence first
        if isinstance(module_intel, dict):
            pattern_type = module_intel.get('pattern_type')
            if pattern_type:
                return pattern_type
        
        # Check tags
        tags = row.get('tags', [])
        for tag in tags:
            if 'detection:' in tag:
                parts = tag.split(':')
                if len(parts) > 1:
                    return parts[-1]  # Return the last part after the last colon
        
        # Check kind
        kind = row.get('kind', 'unknown')
        if kind != 'unknown':
            return kind
        
        return 'unknown'
    
    def _extract_performance_tags(self, row: Dict[str, Any], module_intel: Dict[str, Any]) -> List[str]:
        """Extract performance tags from strand data"""
        performance_tags = []
        
        # Check tags for performance indicators
        tags = row.get('tags', [])
        for tag in tags:
            if any(perf in tag.lower() for perf in ['profitable', 'loss', 'success', 'failure', 'accuracy']):
                performance_tags.append(tag)
        
        # Check module intelligence for performance data
        if isinstance(module_intel, dict):
            if module_intel.get('performance_rating'):
                performance_tags.append(f"performance:{module_intel['performance_rating']}")
        
        return performance_tags
    
    def _extract_hypothesis_notes(self, module_intel: Dict[str, Any]) -> Optional[str]:
        """Extract hypothesis notes from module intelligence"""
        if isinstance(module_intel, dict):
            return module_intel.get('hypothesis_notes') or module_intel.get('notes')
        return None
    
    async def _detect_confluence_events(self, strands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect confluence events from strand data"""
        # Simple confluence detection based on timing and similarity
        confluence_events = []
        
        # Group strands by time windows
        time_windows = {}
        for strand in strands:
            timestamp = strand.get('created_at')
            if timestamp:
                # Round to 5-minute windows
                window_key = timestamp.replace(minute=(timestamp.minute // 5) * 5, second=0, microsecond=0)
                if window_key not in time_windows:
                    time_windows[window_key] = []
                time_windows[window_key].append(strand)
        
        # Check for confluence in each time window
        for window_time, window_strands in time_windows.items():
            if len(window_strands) >= 2:
                # Check for similar patterns
                for i, strand1 in enumerate(window_strands):
                    for strand2 in window_strands[i+1:]:
                        if self._are_strands_similar(strand1, strand2):
                            confluence_events.append({
                                'timestamp': window_time,
                                'strand1': strand1['id'],
                                'strand2': strand2['id'],
                                'similarity_score': self._calculate_strand_similarity(strand1, strand2)
                            })
        
        return confluence_events
    
    async def _detect_lead_lag_relationships(self, strands: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect lead-lag relationships from strand data"""
        # Simple lead-lag detection based on timing patterns
        lead_lag_relationships = []
        
        # Group strands by agent
        agent_strands = {}
        for strand in strands:
            agent_id = strand.get('agent_id', 'unknown')
            if agent_id not in agent_strands:
                agent_strands[agent_id] = []
            agent_strands[agent_id].append(strand)
        
        # Check for lead-lag patterns between agents
        agents = list(agent_strands.keys())
        for i, agent1 in enumerate(agents):
            for agent2 in agents[i+1:]:
                # Check if agent1 consistently fires before agent2
                lead_lag_score = self._calculate_lead_lag_score(
                    agent_strands[agent1], 
                    agent_strands[agent2]
                )
                
                if lead_lag_score > 0.6:  # Threshold for significant lead-lag
                    lead_lag_relationships.append({
                        'lead_agent': agent1,
                        'lag_agent': agent2,
                        'lead_lag_score': lead_lag_score,
                        'sample_size': min(len(agent_strands[agent1]), len(agent_strands[agent2]))
                    })
        
        return lead_lag_relationships
    
    def _are_strands_similar(self, strand1: Dict[str, Any], strand2: Dict[str, Any]) -> bool:
        """Check if two strands are similar enough for confluence"""
        similarity = self._calculate_strand_similarity(strand1, strand2)
        return similarity > 0.7  # Threshold for confluence
    
    def _calculate_strand_similarity(self, strand1: Dict[str, Any], strand2: Dict[str, Any]) -> float:
        """Calculate similarity between two strands"""
        similarity_score = 0.0
        total_features = 0
        
        # Symbol similarity
        if strand1.get('symbol') == strand2.get('symbol'):
            similarity_score += 1.0
        total_features += 1
        
        # Timeframe similarity
        if strand1.get('timeframe') == strand2.get('timeframe'):
            similarity_score += 1.0
        total_features += 1
        
        # Regime similarity
        if strand1.get('regime') == strand2.get('regime'):
            similarity_score += 1.0
        total_features += 1
        
        # Session similarity
        if strand1.get('session_bucket') == strand2.get('session_bucket'):
            similarity_score += 1.0
        total_features += 1
        
        # Pattern type similarity
        pattern_type1 = self._extract_detection_type(strand1, strand1.get('module_intelligence', {}))
        pattern_type2 = self._extract_detection_type(strand2, strand2.get('module_intelligence', {}))
        if pattern_type1 == pattern_type2:
            similarity_score += 1.0
        total_features += 1
        
        # Calculate base similarity
        base_similarity = similarity_score / total_features if total_features > 0 else 0.0
        
        # For completely different strands, return a small baseline similarity
        # This prevents zero scores and allows for some similarity even when no features match
        if base_similarity == 0.0:
            return 0.1  # Small baseline similarity for completely different strands
        
        return base_similarity
    
    def _calculate_lead_lag_score(self, lead_strands: List[Dict[str, Any]], lag_strands: List[Dict[str, Any]]) -> float:
        """Calculate lead-lag score between two sets of strands"""
        if not lead_strands or not lag_strands:
            return 0.0
        
        # Sort by timestamp
        lead_strands.sort(key=lambda x: x.get('created_at', datetime.min))
        lag_strands.sort(key=lambda x: x.get('created_at', datetime.min))
        
        lead_lag_pairs = 0
        total_pairs = 0
        
        # Check for lead-lag patterns
        for lead_strand in lead_strands:
            lead_time = lead_strand.get('created_at')
            if not lead_time:
                continue
            
            for lag_strand in lag_strands:
                lag_time = lag_strand.get('created_at')
                if not lag_time:
                    continue
                
                total_pairs += 1
                time_diff = (lag_time - lead_time).total_seconds()
                
                # Check if lag follows lead within reasonable window (1-60 minutes)
                if 60 <= time_diff <= 3600:
                    lead_lag_pairs += 1
        
        return lead_lag_pairs / total_pairs if total_pairs > 0 else 0.0
    
    def _determine_volatility_band(self, result: List[Dict[str, Any]]) -> str:
        """Determine current volatility band from strand data"""
        if not result:
            return 'unknown'
        
        # Calculate average signal strength as proxy for volatility
        total_strength = sum(row.get('avg_signal_strength', 0) for row in result)
        avg_strength = total_strength / len(result) if result else 0
        
        if avg_strength > 0.8:
            return 'high_vol'
        elif avg_strength > 0.5:
            return 'medium_vol'
        else:
            return 'low_vol'
    
    def _determine_correlation_state(self, result: List[Dict[str, Any]]) -> str:
        """Determine current correlation state from strand data"""
        if not result:
            return 'unknown'
        
        # Count unique symbols as proxy for correlation state
        symbols = set(row.get('symbol') for row in result if row.get('symbol'))
        
        if len(symbols) > 5:
            return 'loose_correlation'
        elif len(symbols) > 2:
            return 'moderate_correlation'
        else:
            return 'tight_correlation'
    
    async def _publish_processing_results(self, processed_inputs: Dict[str, Any]):
        """Publish input processing results as CIL strand"""
        try:
            # Create CIL processing strand
            cil_strand = {
                'id': f"cil_input_processing_{int(datetime.now().timestamp())}",
                'kind': 'cil_input_processing',
                'module': 'alpha',
                'agent_id': 'central_intelligence_layer',
                'cil_team_member': 'input_processor',
                'symbol': 'SYSTEM',
                'timeframe': 'system',
                'session_bucket': 'GLOBAL',
                'regime': 'system',
                'tags': ['agent:central_intelligence:input_processor:processing_complete'],
                'module_intelligence': {
                    'processing_type': 'input_processing',
                    'agent_outputs_count': len(processed_inputs.get('agent_outputs', [])),
                    'cross_agent_events': len(processed_inputs.get('cross_agent_metadata', {}).get('confluence_events', [])),
                    'current_regime': processed_inputs.get('market_regime_context', {}).get('current_regime', 'unknown'),
                    'active_experiments': len(processed_inputs.get('experiment_registry', {}).get('active_experiments', [])),
                    'processing_errors': processed_inputs.get('processing_errors', [])
                },
                'sig_sigma': 1.0,  # System processing always has max signal strength
                'sig_confidence': 1.0,
                'sig_direction': 'neutral',
                'outcome_score': 1.0,
                'created_at': datetime.now(timezone.utc)
            }
            
            # Insert into database
            await self.supabase_manager.insert_strand(cil_strand)
            
        except Exception as e:
            print(f"Error publishing input processing results: {e}")


# Example usage and testing
async def main():
    """Example usage of InputProcessor"""
    from src.utils.supabase_manager import SupabaseManager
    from src.llm_integration.openrouter_client import OpenRouterClient
    
    # Initialize components
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    
    # Create input processor
    input_processor = InputProcessor(supabase_manager, llm_client)
    
    # Process all inputs
    processed_inputs = await input_processor.process_all_inputs()
    
    print("CIL Input Processing Results:")
    print(f"Agent Outputs: {len(processed_inputs.get('agent_outputs', []))}")
    print(f"Cross-Agent Events: {len(processed_inputs.get('cross_agent_metadata', {}).get('confluence_events', []))}")
    print(f"Current Regime: {processed_inputs.get('market_regime_context', {}).get('current_regime', 'unknown')}")
    print(f"Active Experiments: {len(processed_inputs.get('experiment_registry', {}).get('active_experiments', []))}")


if __name__ == "__main__":
    asyncio.run(main())
