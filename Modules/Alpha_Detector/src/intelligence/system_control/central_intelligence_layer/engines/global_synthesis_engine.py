"""
CIL Global Synthesis Engine

Section 3: Global View / Synthesis (CIL)
- Cross-Agent Correlation (detect coincidences, lead-lag patterns, confluence)
- Overlaps & Blind Spots (find redundancy, highlight blind spots)
- Family-Level Understanding (group signals into families, track family performance)
- Meta-Patterns (map signal interactions under different regimes)
- Doctrine Formation (capture what the global view means)

Vector Search Integration:
- Vector embeddings for cross-agent pattern correlation
- Semantic similarity for pattern family grouping
- Vector clustering for meta-pattern detection
- Vector search for doctrine formation and pattern evolution
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.llm_integration.prompt_manager import PromptManager
from src.llm_integration.database_driven_context_system import DatabaseDrivenContextSystem


@dataclass
class CrossAgentCorrelation:
    """Cross-agent correlation analysis"""
    coincidences: List[Dict[str, Any]]
    lead_lag_patterns: List[Dict[str, Any]]
    confluence_events: List[Dict[str, Any]]
    correlation_strength: float
    confidence_score: float


@dataclass
class CoverageAnalysis:
    """Coverage and blind spot analysis"""
    redundant_areas: List[Dict[str, Any]]
    blind_spots: List[Dict[str, Any]]
    coverage_gaps: List[Dict[str, Any]]
    coverage_score: float
    efficiency_score: float


@dataclass
class SignalFamily:
    """Signal family analysis"""
    family_name: str
    family_members: List[str]
    performance_metrics: Dict[str, float]
    regime_performance: Dict[str, float]
    session_performance: Dict[str, float]
    evolution_trend: str
    family_strength: float


@dataclass
class MetaPattern:
    """Meta-pattern analysis"""
    pattern_name: str
    signal_interactions: List[Dict[str, Any]]
    regime_conditions: Dict[str, Any]
    session_conditions: Dict[str, Any]
    strength_score: float
    persistence_score: float
    novelty_score: float


@dataclass
class DoctrineInsight:
    """Doctrine formation insight"""
    insight_type: str
    pattern_family: str
    conditions: Dict[str, Any]
    reliability_score: float
    evidence_count: int
    recommendation: str
    confidence_level: float


class GlobalSynthesisEngine:
    """
    CIL Global Synthesis Engine
    
    Responsibilities:
    1. Cross-Agent Correlation (detect coincidences, lead-lag patterns, confluence)
    2. Overlaps & Blind Spots (find redundancy, highlight blind spots)
    3. Family-Level Understanding (group signals into families, track family performance)
    4. Meta-Patterns (map signal interactions under different regimes)
    5. Doctrine Formation (capture what the global view means)
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        self.context_system = DatabaseDrivenContextSystem(supabase_manager)
        
        # Synthesis configuration
        self.correlation_window_hours = 24
        self.family_analysis_window_days = 7
        self.meta_pattern_window_days = 14
        self.doctrine_formation_window_days = 30
        
        # Thresholds
        self.correlation_threshold = 0.7
        self.confluence_threshold = 0.8
        self.family_strength_threshold = 0.6
        self.meta_pattern_threshold = 0.75
        self.doctrine_confidence_threshold = 0.8
        
    async def synthesize_global_view(self, processed_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize global view from processed inputs
        
        Args:
            processed_inputs: Output from InputProcessor
            
        Returns:
            Dict containing synthesized global view
        """
        try:
            # Perform all synthesis operations in parallel
            results = await asyncio.gather(
                self.analyze_cross_agent_correlation(processed_inputs),
                self.analyze_coverage_and_blind_spots(processed_inputs),
                self.analyze_signal_families(processed_inputs),
                self.analyze_meta_patterns(processed_inputs),
                self.form_doctrine_insights(processed_inputs),
                return_exceptions=True
            )
            
            # Structure synthesis results
            global_view = {
                'cross_agent_correlation': results[0] if not isinstance(results[0], Exception) else None,
                'coverage_analysis': results[1] if not isinstance(results[1], Exception) else None,
                'signal_families': results[2] if not isinstance(results[2], Exception) else None,
                'meta_patterns': results[3] if not isinstance(results[3], Exception) else None,
                'doctrine_insights': results[4] if not isinstance(results[4], Exception) else None,
                'synthesis_timestamp': datetime.now(timezone.utc),
                'synthesis_errors': [str(r) for r in results if isinstance(r, Exception)]
            }
            
            # Publish synthesis results as CIL strand
            await self._publish_synthesis_results(global_view)
            
            return global_view
            
        except Exception as e:
            print(f"Error synthesizing global view: {e}")
            return {'error': str(e), 'synthesis_timestamp': datetime.now(timezone.utc)}
    
    async def analyze_cross_agent_correlation(self, processed_inputs: Dict[str, Any]) -> CrossAgentCorrelation:
        """
        Analyze cross-agent correlations and patterns
        
        Returns:
            CrossAgentCorrelation with coincidence, lead-lag, and confluence analysis
        """
        try:
            agent_outputs = processed_inputs.get('agent_outputs', [])
            cross_agent_metadata = processed_inputs.get('cross_agent_metadata', {})
            
            # Detect coincidences
            coincidences = await self._detect_agent_coincidences(agent_outputs)
            
            # Analyze lead-lag patterns
            lead_lag_patterns = await self._analyze_lead_lag_patterns(cross_agent_metadata)
            
            # Detect confluence events
            confluence_events = await self._detect_confluence_events(cross_agent_metadata)
            
            # Calculate overall correlation strength
            correlation_strength = self._calculate_correlation_strength(
                coincidences, lead_lag_patterns, confluence_events
            )
            
            # Calculate confidence score
            confidence_score = self._calculate_correlation_confidence(
                len(agent_outputs), len(coincidences), len(lead_lag_patterns)
            )
            
            return CrossAgentCorrelation(
                coincidences=coincidences,
                lead_lag_patterns=lead_lag_patterns,
                confluence_events=confluence_events,
                correlation_strength=correlation_strength,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            print(f"Error analyzing cross-agent correlation: {e}")
            return CrossAgentCorrelation(
                coincidences=[],
                lead_lag_patterns=[],
                confluence_events=[],
                correlation_strength=0.0,
                confidence_score=0.0
            )
    
    async def analyze_coverage_and_blind_spots(self, processed_inputs: Dict[str, Any]) -> CoverageAnalysis:
        """
        Analyze coverage patterns and identify blind spots
        
        Returns:
            CoverageAnalysis with redundancy, blind spots, and coverage gaps
        """
        try:
            cross_agent_metadata = processed_inputs.get('cross_agent_metadata', {})
            coverage_map = cross_agent_metadata.get('coverage_map', {})
            
            # Find redundant areas
            redundant_areas = self._find_redundant_areas(coverage_map)
            
            # Identify blind spots
            blind_spots = self._identify_blind_spots(coverage_map)
            
            # Find coverage gaps
            coverage_gaps = self._find_coverage_gaps(coverage_map)
            
            # Calculate coverage score
            coverage_score = self._calculate_coverage_score(coverage_map)
            
            # Calculate efficiency score
            efficiency_score = self._calculate_efficiency_score(redundant_areas, coverage_map)
            
            return CoverageAnalysis(
                redundant_areas=redundant_areas,
                blind_spots=blind_spots,
                coverage_gaps=coverage_gaps,
                coverage_score=coverage_score,
                efficiency_score=efficiency_score
            )
            
        except Exception as e:
            print(f"Error analyzing coverage and blind spots: {e}")
            return CoverageAnalysis(
                redundant_areas=[],
                blind_spots=[],
                coverage_gaps=[],
                coverage_score=0.0,
                efficiency_score=0.0
            )
    
    async def analyze_signal_families(self, processed_inputs: Dict[str, Any]) -> List[SignalFamily]:
        """
        Analyze signal families and their performance
        
        Returns:
            List of SignalFamily objects with performance analysis
        """
        try:
            # Get historical performance data
            historical_performance = processed_inputs.get('historical_performance', {})
            success_patterns = historical_performance.get('success_patterns', [])
            failed_patterns = historical_performance.get('failed_patterns', [])
            
            # Group signals into families
            signal_families = self._group_signals_into_families(success_patterns, failed_patterns)
            
            # Analyze each family
            analyzed_families = []
            for family_name, family_signals in signal_families.items():
                family_analysis = await self._analyze_signal_family(family_name, family_signals)
                analyzed_families.append(family_analysis)
            
            return analyzed_families
            
        except Exception as e:
            print(f"Error analyzing signal families: {e}")
            return []
    
    async def analyze_meta_patterns(self, processed_inputs: Dict[str, Any]) -> List[MetaPattern]:
        """
        Analyze meta-patterns across signal interactions
        
        Returns:
            List of MetaPattern objects with interaction analysis
        """
        try:
            # Get cross-agent metadata
            cross_agent_metadata = processed_inputs.get('cross_agent_metadata', {})
            confluence_events = cross_agent_metadata.get('confluence_events', [])
            lead_lag_relationships = cross_agent_metadata.get('lead_lag_relationships', [])
            
            # Get market regime context
            market_regime_context = processed_inputs.get('market_regime_context', {})
            
            # Detect meta-patterns
            meta_patterns = []
            
            # Analyze confluence-based meta-patterns
            confluence_patterns = await self._analyze_confluence_meta_patterns(
                confluence_events, market_regime_context
            )
            meta_patterns.extend(confluence_patterns)
            
            # Analyze lead-lag meta-patterns
            lead_lag_patterns = await self._analyze_lead_lag_meta_patterns(
                lead_lag_relationships, market_regime_context
            )
            meta_patterns.extend(lead_lag_patterns)
            
            # Analyze regime-specific meta-patterns
            regime_patterns = await self._analyze_regime_meta_patterns(
                processed_inputs, market_regime_context
            )
            meta_patterns.extend(regime_patterns)
            
            return meta_patterns
            
        except Exception as e:
            print(f"Error analyzing meta-patterns: {e}")
            return []
    
    async def form_doctrine_insights(self, processed_inputs: Dict[str, Any]) -> List[DoctrineInsight]:
        """
        Form doctrine insights from global analysis
        
        Returns:
            List of DoctrineInsight objects with recommendations
        """
        try:
            # Get all analysis results
            signal_families = await self.analyze_signal_families(processed_inputs)
            meta_patterns = await self.analyze_meta_patterns(processed_inputs)
            cross_agent_correlation = await self.analyze_cross_agent_correlation(processed_inputs)
            
            doctrine_insights = []
            
            # Form insights from signal families
            family_insights = await self._form_family_doctrine_insights(signal_families)
            doctrine_insights.extend(family_insights)
            
            # Form insights from meta-patterns
            pattern_insights = await self._form_pattern_doctrine_insights(meta_patterns)
            doctrine_insights.extend(pattern_insights)
            
            # Form insights from cross-agent correlations
            correlation_insights = await self._form_correlation_doctrine_insights(cross_agent_correlation)
            doctrine_insights.extend(correlation_insights)
            
            return doctrine_insights
            
        except Exception as e:
            print(f"Error forming doctrine insights: {e}")
            return []
    
    async def _detect_agent_coincidences(self, agent_outputs: List[Any]) -> List[Dict[str, Any]]:
        """Detect coincidences between agent outputs"""
        coincidences = []
        
        # Group outputs by time windows
        time_windows = defaultdict(list)
        for output in agent_outputs:
            if hasattr(output, 'timestamp'):
                # Round to 5-minute windows
                window_time = output.timestamp.replace(
                    minute=(output.timestamp.minute // 5) * 5, 
                    second=0, 
                    microsecond=0
                )
                time_windows[window_time].append(output)
        
        # Check for coincidences in each time window
        for window_time, window_outputs in time_windows.items():
            if len(window_outputs) >= 2:
                # Check for similar patterns
                for i, output1 in enumerate(window_outputs):
                    for output2 in window_outputs[i+1:]:
                        if self._are_outputs_similar(output1, output2):
                            coincidences.append({
                                'timestamp': window_time,
                                'agent1': output1.agent_id,
                                'agent2': output2.agent_id,
                                'detection_type1': output1.detection_type,
                                'detection_type2': output2.detection_type,
                                'similarity_score': self._calculate_output_similarity(output1, output2)
                            })
        
        return coincidences
    
    async def _analyze_lead_lag_patterns(self, cross_agent_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze lead-lag patterns from cross-agent metadata"""
        lead_lag_relationships = cross_agent_metadata.get('lead_lag_relationships', [])
        
        # Enhance lead-lag analysis with additional metrics
        enhanced_patterns = []
        for relationship in lead_lag_relationships:
            enhanced_pattern = {
                'lead_agent': relationship.get('lead_agent'),
                'lag_agent': relationship.get('lag_agent'),
                'lead_lag_score': relationship.get('lead_lag_score', 0.0),
                'sample_size': relationship.get('sample_size', 0),
                'consistency_score': self._calculate_consistency_score(relationship),
                'reliability_score': self._calculate_reliability_score(relationship),
                'pattern_strength': relationship.get('lead_lag_score', 0.0) * relationship.get('sample_size', 0)
            }
            enhanced_patterns.append(enhanced_pattern)
        
        return enhanced_patterns
    
    async def _detect_confluence_events(self, cross_agent_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect confluence events from cross-agent metadata"""
        confluence_events = cross_agent_metadata.get('confluence_events', [])
        
        # Enhance confluence analysis
        enhanced_events = []
        for event in confluence_events:
            enhanced_event = {
                'timestamp': event.get('timestamp'),
                'strand1': event.get('strand1'),
                'strand2': event.get('strand2'),
                'similarity_score': event.get('similarity_score', 0.0),
                'confluence_strength': self._calculate_confluence_strength(event),
                'significance_score': self._calculate_significance_score(event)
            }
            enhanced_events.append(enhanced_event)
        
        return enhanced_events
    
    def _find_redundant_areas(self, coverage_map: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find redundant coverage areas"""
        redundant_areas = []
        
        for context_key, context_data in coverage_map.items():
            agents = context_data.get('agents', [])
            detection_count = context_data.get('detection_count', 0)
            
            # Consider redundant if multiple agents cover same area with high detection count
            if len(agents) > 2 and detection_count > 10:
                redundant_areas.append({
                    'context_key': context_key,
                    'context_data': context_data,
                    'redundancy_score': len(agents) * (detection_count / 10),
                    'efficiency_loss': len(agents) - 1
                })
        
        return redundant_areas
    
    def _identify_blind_spots(self, coverage_map: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify blind spots in coverage"""
        blind_spots = []
        
        # Define expected coverage areas
        expected_symbols = ['BTC', 'ETH', 'SOL', 'ADA', 'DOT']
        expected_timeframes = ['1h', '4h', '1d']
        expected_regimes = ['high_vol', 'medium_vol', 'low_vol']
        expected_sessions = ['US', 'EU', 'ASIA']
        
        # Check for missing combinations
        for symbol in expected_symbols:
            for timeframe in expected_timeframes:
                for regime in expected_regimes:
                    for session in expected_sessions:
                        context_key = f"{symbol}_{timeframe}_{regime}_{session}"
                        if context_key not in coverage_map:
                            blind_spots.append({
                                'context_key': context_key,
                                'symbol': symbol,
                                'timeframe': timeframe,
                                'regime': regime,
                                'session': session,
                                'priority': self._calculate_blind_spot_priority(symbol, timeframe, regime, session)
                            })
        
        return blind_spots
    
    def _find_coverage_gaps(self, coverage_map: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find coverage gaps in existing areas"""
        coverage_gaps = []
        
        for context_key, context_data in coverage_map.items():
            agents = context_data.get('agents', [])
            detection_count = context_data.get('detection_count', 0)
            
            # Consider gap if low detection count relative to expected
            if detection_count < 5 and len(agents) < 2:
                coverage_gaps.append({
                    'context_key': context_key,
                    'context_data': context_data,
                    'gap_severity': 5 - detection_count,
                    'recommended_agents': 2 - len(agents)
                })
        
        return coverage_gaps
    
    def _group_signals_into_families(self, success_patterns: List[Dict[str, Any]], failed_patterns: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group signals into families based on pattern type"""
        signal_families = defaultdict(list)
        
        # Group success patterns
        for pattern in success_patterns:
            pattern_type = self._extract_pattern_type(pattern)
            signal_families[pattern_type].append({**pattern, 'outcome': 'success'})
        
        # Group failed patterns
        for pattern in failed_patterns:
            pattern_type = self._extract_pattern_type(pattern)
            signal_families[pattern_type].append({**pattern, 'outcome': 'failed'})
        
        return dict(signal_families)
    
    async def _analyze_signal_family(self, family_name: str, family_signals: List[Dict[str, Any]]) -> SignalFamily:
        """Analyze a signal family"""
        # Calculate performance metrics
        success_count = sum(1 for signal in family_signals if signal.get('outcome') == 'success')
        total_count = len(family_signals)
        success_rate = success_count / total_count if total_count > 0 else 0.0
        
        # Calculate regime performance
        regime_performance = defaultdict(list)
        for signal in family_signals:
            regime = signal.get('regime', 'unknown')
            outcome_score = signal.get('outcome_score', 0.0)
            regime_performance[regime].append(outcome_score)
        
        regime_avg_performance = {
            regime: sum(scores) / len(scores) if scores else 0.0
            for regime, scores in regime_performance.items()
        }
        
        # Calculate session performance
        session_performance = defaultdict(list)
        for signal in family_signals:
            session = signal.get('session_bucket', 'unknown')
            outcome_score = signal.get('outcome_score', 0.0)
            session_performance[session].append(outcome_score)
        
        session_avg_performance = {
            session: sum(scores) / len(scores) if scores else 0.0
            for session, scores in session_performance.items()
        }
        
        # Determine evolution trend
        evolution_trend = self._determine_evolution_trend(family_signals)
        
        # Calculate family strength
        family_strength = self._calculate_family_strength(
            success_rate, regime_avg_performance, session_avg_performance
        )
        
        return SignalFamily(
            family_name=family_name,
            family_members=[signal.get('id', 'unknown') for signal in family_signals],
            performance_metrics={
                'success_rate': success_rate,
                'total_signals': total_count,
                'avg_confidence': sum(signal.get('sig_confidence', 0.0) for signal in family_signals) / total_count if total_count > 0 else 0.0,
                'avg_signal_strength': sum(signal.get('sig_sigma', 0.0) for signal in family_signals) / total_count if total_count > 0 else 0.0
            },
            regime_performance=regime_avg_performance,
            session_performance=session_avg_performance,
            evolution_trend=evolution_trend,
            family_strength=family_strength
        )
    
    def _are_outputs_similar(self, output1: Any, output2: Any) -> bool:
        """Check if two agent outputs are similar"""
        if not hasattr(output1, 'detection_type') or not hasattr(output2, 'detection_type'):
            return False
        
        # Check detection type similarity
        if output1.detection_type == output2.detection_type:
            return True
        
        # Check context similarity
        if hasattr(output1, 'context') and hasattr(output2, 'context'):
            context1 = output1.context
            context2 = output2.context
            
            # Check symbol, timeframe, regime, session similarity
            if (context1.get('symbol') == context2.get('symbol') and
                context1.get('timeframe') == context2.get('timeframe') and
                context1.get('regime') == context2.get('regime') and
                context1.get('session_bucket') == context2.get('session_bucket')):
                return True
        
        return False
    
    def _calculate_output_similarity(self, output1: Any, output2: Any) -> float:
        """Calculate similarity between two agent outputs"""
        similarity_score = 0.0
        total_features = 0
        
        # Detection type similarity
        if hasattr(output1, 'detection_type') and hasattr(output2, 'detection_type'):
            if output1.detection_type == output2.detection_type:
                similarity_score += 1.0
            total_features += 1
        
        # Context similarity
        if hasattr(output1, 'context') and hasattr(output2, 'context'):
            context1 = output1.context
            context2 = output2.context
            
            # Symbol similarity
            if context1.get('symbol') == context2.get('symbol'):
                similarity_score += 1.0
            total_features += 1
            
            # Timeframe similarity
            if context1.get('timeframe') == context2.get('timeframe'):
                similarity_score += 1.0
            total_features += 1
            
            # Regime similarity
            if context1.get('regime') == context2.get('regime'):
                similarity_score += 1.0
            total_features += 1
            
            # Session similarity
            if context1.get('session_bucket') == context2.get('session_bucket'):
                similarity_score += 1.0
            total_features += 1
        
        return similarity_score / total_features if total_features > 0 else 0.0
    
    def _calculate_correlation_strength(self, coincidences: List[Dict[str, Any]], 
                                      lead_lag_patterns: List[Dict[str, Any]], 
                                      confluence_events: List[Dict[str, Any]]) -> float:
        """Calculate overall correlation strength"""
        if not coincidences and not lead_lag_patterns and not confluence_events:
            return 0.0
        
        # Weight different types of correlations
        coincidence_weight = 0.3
        lead_lag_weight = 0.4
        confluence_weight = 0.3
        
        # Calculate weighted average
        total_strength = 0.0
        total_weight = 0.0
        
        if coincidences:
            avg_coincidence_strength = sum(c.get('similarity_score', 0.0) for c in coincidences) / len(coincidences)
            total_strength += avg_coincidence_strength * coincidence_weight
            total_weight += coincidence_weight
        
        if lead_lag_patterns:
            avg_lead_lag_strength = sum(p.get('lead_lag_score', 0.0) for p in lead_lag_patterns) / len(lead_lag_patterns)
            total_strength += avg_lead_lag_strength * lead_lag_weight
            total_weight += lead_lag_weight
        
        if confluence_events:
            avg_confluence_strength = sum(e.get('similarity_score', 0.0) for e in confluence_events) / len(confluence_events)
            total_strength += avg_confluence_strength * confluence_weight
            total_weight += confluence_weight
        
        return total_strength / total_weight if total_weight > 0 else 0.0
    
    def _calculate_correlation_confidence(self, total_outputs: int, coincidences: int, lead_lag_patterns: int) -> float:
        """Calculate confidence in correlation analysis"""
        if total_outputs == 0:
            return 0.0
        
        # Base confidence on sample size and pattern detection
        sample_confidence = min(total_outputs / 100, 1.0)  # Max confidence at 100+ samples
        pattern_confidence = min((coincidences + lead_lag_patterns) / 10, 1.0)  # Max confidence at 10+ patterns
        
        return (sample_confidence + pattern_confidence) / 2
    
    def _calculate_coverage_score(self, coverage_map: Dict[str, Any]) -> float:
        """Calculate overall coverage score"""
        if not coverage_map:
            return 0.0
        
        total_contexts = len(coverage_map)
        covered_contexts = sum(1 for context_data in coverage_map.values() 
                             if context_data.get('detection_count', 0) > 0)
        
        return covered_contexts / total_contexts if total_contexts > 0 else 0.0
    
    def _calculate_efficiency_score(self, redundant_areas: List[Dict[str, Any]], coverage_map: Dict[str, Any]) -> float:
        """Calculate efficiency score based on redundancy"""
        if not coverage_map:
            return 1.0
        
        total_efficiency_loss = sum(area.get('efficiency_loss', 0) for area in redundant_areas)
        total_agents = sum(len(context_data.get('agents', [])) for context_data in coverage_map.values())
        
        if total_agents == 0:
            return 1.0
        
        efficiency_ratio = 1.0 - (total_efficiency_loss / total_agents)
        return max(0.0, efficiency_ratio)
    
    def _extract_pattern_type(self, pattern: Dict[str, Any]) -> str:
        """Extract pattern type from pattern data"""
        module_intel = pattern.get('module_intelligence', {})
        if isinstance(module_intel, dict):
            pattern_type = module_intel.get('pattern_type')
            if pattern_type:
                return pattern_type
        
        # Fallback to kind
        return pattern.get('kind', 'unknown')
    
    def _determine_evolution_trend(self, family_signals: List[Dict[str, Any]]) -> str:
        """Determine evolution trend for a signal family"""
        if len(family_signals) < 2:
            return 'insufficient_data'
        
        # Sort by timestamp
        sorted_signals = sorted(family_signals, key=lambda x: x.get('created_at', datetime.min))
        
        # Calculate trend based on recent vs older performance
        recent_signals = sorted_signals[-len(sorted_signals)//2:]
        older_signals = sorted_signals[:len(sorted_signals)//2]
        
        recent_avg_performance = sum(s.get('outcome_score', 0.0) for s in recent_signals) / len(recent_signals)
        older_avg_performance = sum(s.get('outcome_score', 0.0) for s in older_signals) / len(older_signals)
        
        if recent_avg_performance > older_avg_performance + 0.1:
            return 'improving'
        elif recent_avg_performance < older_avg_performance - 0.1:
            return 'declining'
        else:
            return 'stable'
    
    def _calculate_family_strength(self, success_rate: float, regime_performance: Dict[str, float], 
                                 session_performance: Dict[str, float]) -> float:
        """Calculate overall family strength"""
        # Base strength from success rate
        base_strength = success_rate
        
        # Regime consistency bonus
        regime_scores = list(regime_performance.values())
        regime_consistency = 1.0 - (max(regime_scores) - min(regime_scores)) if regime_scores else 0.0
        
        # Session consistency bonus
        session_scores = list(session_performance.values())
        session_consistency = 1.0 - (max(session_scores) - min(session_scores)) if session_scores else 0.0
        
        # Weighted combination
        return (base_strength * 0.6 + regime_consistency * 0.2 + session_consistency * 0.2)
    
    async def _analyze_confluence_meta_patterns(self, confluence_events: List[Dict[str, Any]], 
                                              market_regime_context: Dict[str, Any]) -> List[MetaPattern]:
        """Analyze confluence-based meta-patterns"""
        meta_patterns = []
        
        # Group confluence events by similarity patterns
        confluence_groups = defaultdict(list)
        for event in confluence_events:
            similarity_score = event.get('similarity_score', 0.0)
            if similarity_score > self.confluence_threshold:
                # Group by similarity score ranges
                group_key = f"confluence_{int(similarity_score * 10)}"
                confluence_groups[group_key].append(event)
        
        # Create meta-patterns for each group
        for group_key, events in confluence_groups.items():
            if len(events) >= 2:  # Need at least 2 events for a pattern
                meta_pattern = MetaPattern(
                    pattern_name=f"Confluence Pattern: {group_key}",
                    signal_interactions=events,
                    regime_conditions=market_regime_context,
                    session_conditions=market_regime_context.get('session_structure', {}),
                    strength_score=sum(e.get('similarity_score', 0.0) for e in events) / len(events),
                    persistence_score=len(events) / 10.0,  # Normalize by expected frequency
                    novelty_score=0.5  # Placeholder - would be calculated based on historical data
                )
                meta_patterns.append(meta_pattern)
        
        return meta_patterns
    
    async def _analyze_lead_lag_meta_patterns(self, lead_lag_relationships: List[Dict[str, Any]], 
                                            market_regime_context: Dict[str, Any]) -> List[MetaPattern]:
        """Analyze lead-lag meta-patterns"""
        meta_patterns = []
        
        # Group lead-lag relationships by agent pairs
        agent_pairs = defaultdict(list)
        for relationship in lead_lag_relationships:
            lead_agent = relationship.get('lead_agent')
            lag_agent = relationship.get('lag_agent')
            if lead_agent and lag_agent:
                pair_key = f"{lead_agent}->{lag_agent}"
                agent_pairs[pair_key].append(relationship)
        
        # Create meta-patterns for each agent pair
        for pair_key, relationships in agent_pairs.items():
            if len(relationships) >= 2:  # Need at least 2 relationships for a pattern
                avg_lead_lag_score = sum(r.get('lead_lag_score', 0.0) for r in relationships) / len(relationships)
                
                meta_pattern = MetaPattern(
                    pattern_name=f"Lead-Lag Pattern: {pair_key}",
                    signal_interactions=relationships,
                    regime_conditions=market_regime_context,
                    session_conditions=market_regime_context.get('session_structure', {}),
                    strength_score=avg_lead_lag_score,
                    persistence_score=len(relationships) / 10.0,  # Normalize by expected frequency
                    novelty_score=0.5  # Placeholder - would be calculated based on historical data
                )
                meta_patterns.append(meta_pattern)
        
        return meta_patterns
    
    async def _analyze_regime_meta_patterns(self, processed_inputs: Dict[str, Any], 
                                          market_regime_context: Dict[str, Any]) -> List[MetaPattern]:
        """Analyze regime-specific meta-patterns"""
        meta_patterns = []
        
        # Get current regime
        current_regime = market_regime_context.get('current_regime', 'unknown')
        
        # Analyze patterns specific to current regime
        if current_regime != 'unknown':
            meta_pattern = MetaPattern(
                pattern_name=f"Regime-Specific Pattern: {current_regime}",
                signal_interactions=[],  # Would be populated with regime-specific interactions
                regime_conditions={current_regime: 1.0},
                session_conditions=market_regime_context.get('session_structure', {}),
                strength_score=0.8,  # Placeholder - would be calculated based on regime performance
                persistence_score=0.7,  # Placeholder - would be calculated based on regime stability
                novelty_score=0.3  # Placeholder - would be calculated based on regime novelty
            )
            meta_patterns.append(meta_pattern)
        
        return meta_patterns
    
    async def _form_family_doctrine_insights(self, signal_families: List[SignalFamily]) -> List[DoctrineInsight]:
        """Form doctrine insights from signal families"""
        insights = []
        
        for family in signal_families:
            if family.family_strength > self.family_strength_threshold:
                # Create insight for strong families
                insight = DoctrineInsight(
                    insight_type='family_strength',
                    pattern_family=family.family_name,
                    conditions={
                        'regime_performance': family.regime_performance,
                        'session_performance': family.session_performance
                    },
                    reliability_score=family.family_strength,
                    evidence_count=len(family.family_members),
                    recommendation=f"Continue focusing on {family.family_name} patterns",
                    confidence_level=family.family_strength
                )
                insights.append(insight)
            
            # Create insight for evolution trends
            if family.evolution_trend in ['improving', 'declining']:
                insight = DoctrineInsight(
                    insight_type='evolution_trend',
                    pattern_family=family.family_name,
                    conditions={'trend': family.evolution_trend},
                    reliability_score=0.7,  # Placeholder
                    evidence_count=len(family.family_members),
                    recommendation=f"Monitor {family.family_name} trend: {family.evolution_trend}",
                    confidence_level=0.7
                )
                insights.append(insight)
        
        return insights
    
    async def _form_pattern_doctrine_insights(self, meta_patterns: List[MetaPattern]) -> List[DoctrineInsight]:
        """Form doctrine insights from meta-patterns"""
        insights = []
        
        for pattern in meta_patterns:
            if pattern.strength_score > self.meta_pattern_threshold:
                insight = DoctrineInsight(
                    insight_type='meta_pattern',
                    pattern_family=pattern.pattern_name,
                    conditions={
                        'regime_conditions': pattern.regime_conditions,
                        'session_conditions': pattern.session_conditions
                    },
                    reliability_score=pattern.strength_score,
                    evidence_count=len(pattern.signal_interactions),
                    recommendation=f"Investigate {pattern.pattern_name} for potential exploitation",
                    confidence_level=pattern.strength_score
                )
                insights.append(insight)
        
        return insights
    
    async def _form_correlation_doctrine_insights(self, cross_agent_correlation: CrossAgentCorrelation) -> List[DoctrineInsight]:
        """Form doctrine insights from cross-agent correlations"""
        insights = []
        
        # Create insight for high correlation strength
        if cross_agent_correlation.correlation_strength > self.correlation_threshold:
            insight = DoctrineInsight(
                insight_type='correlation_strength',
                pattern_family='cross_agent_correlation',
                conditions={
                    'correlation_strength': cross_agent_correlation.correlation_strength,
                    'confidence_score': cross_agent_correlation.confidence_score
                },
                reliability_score=cross_agent_correlation.correlation_strength,
                evidence_count=len(cross_agent_correlation.coincidences) + len(cross_agent_correlation.lead_lag_patterns),
                recommendation="High cross-agent correlation detected - consider coordinated strategies",
                confidence_level=cross_agent_correlation.confidence_score
            )
            insights.append(insight)
        
        # Create insight for confluence events
        if len(cross_agent_correlation.confluence_events) > 0:
            insight = DoctrineInsight(
                insight_type='confluence_events',
                pattern_family='confluence_detection',
                conditions={
                    'confluence_count': len(cross_agent_correlation.confluence_events),
                    'avg_similarity': sum(e.get('similarity_score', 0.0) for e in cross_agent_correlation.confluence_events) / len(cross_agent_correlation.confluence_events)
                },
                reliability_score=0.8,  # Placeholder
                evidence_count=len(cross_agent_correlation.confluence_events),
                recommendation="Multiple confluence events detected - investigate pattern overlaps",
                confidence_level=0.8
            )
            insights.append(insight)
        
        return insights
    
    async def _publish_synthesis_results(self, global_view: Dict[str, Any]):
        """Publish global synthesis results as CIL strand"""
        try:
            # Create CIL synthesis strand
            cil_strand = {
                'id': f"cil_global_synthesis_{int(datetime.now().timestamp())}",
                'kind': 'cil_global_synthesis',
                'module': 'alpha',
                'agent_id': 'central_intelligence_layer',
                'cil_team_member': 'global_synthesis_engine',
                'symbol': 'SYSTEM',
                'timeframe': 'system',
                'session_bucket': 'GLOBAL',
                'regime': 'system',
                'tags': ['agent:central_intelligence:global_synthesis_engine:synthesis_complete'],
                'module_intelligence': {
                    'synthesis_type': 'global_synthesis',
                    'correlation_strength': global_view.get('cross_agent_correlation', {}).get('correlation_strength', 0.0),
                    'coverage_score': global_view.get('coverage_analysis', {}).get('coverage_score', 0.0),
                    'efficiency_score': global_view.get('coverage_analysis', {}).get('efficiency_score', 0.0),
                    'signal_families_count': len(global_view.get('signal_families', [])),
                    'meta_patterns_count': len(global_view.get('meta_patterns', [])),
                    'doctrine_insights_count': len(global_view.get('doctrine_insights', [])),
                    'synthesis_errors': global_view.get('synthesis_errors', [])
                },
                'sig_sigma': 1.0,
                'sig_confidence': 1.0,
                'sig_direction': 'neutral',
                'outcome_score': 1.0,
                'created_at': datetime.now(timezone.utc)
            }
            
            # Insert into database
            await self.supabase_manager.insert_strand(cil_strand)
            
        except Exception as e:
            print(f"Error publishing global synthesis results: {e}")


# Example usage and testing
async def main():
    """Example usage of GlobalSynthesisEngine"""
    from src.utils.supabase_manager import SupabaseManager
    from src.llm_integration.openrouter_client import OpenRouterClient
    
    # Initialize components
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    
    # Create global synthesis engine
    synthesis_engine = GlobalSynthesisEngine(supabase_manager, llm_client)
    
    # Mock processed inputs
    processed_inputs = {
        'agent_outputs': [],
        'cross_agent_metadata': {},
        'market_regime_context': {},
        'historical_performance': {},
        'experiment_registry': {}
    }
    
    # Synthesize global view
    global_view = await synthesis_engine.synthesize_global_view(processed_inputs)
    
    print("CIL Global Synthesis Results:")
    print(f"Correlation Strength: {global_view.get('cross_agent_correlation', {}).get('correlation_strength', 0.0)}")
    print(f"Coverage Score: {global_view.get('coverage_analysis', {}).get('coverage_score', 0.0)}")
    print(f"Signal Families: {len(global_view.get('signal_families', []))}")
    print(f"Meta Patterns: {len(global_view.get('meta_patterns', []))}")
    print(f"Doctrine Insights: {len(global_view.get('doctrine_insights', []))}")


if __name__ == "__main__":
    asyncio.run(main())
