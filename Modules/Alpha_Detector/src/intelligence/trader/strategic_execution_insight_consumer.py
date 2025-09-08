"""
Strategic Execution Insight Consumer

Handles natural consumption of CIL strategic execution insights.
Enables Trader agents to naturally benefit from CIL's panoramic execution view
and contribute to strategic execution analysis.

Key Features:
- CIL execution insight consumption for execution type
- Valuable execution meta-signal subscription
- Strategic execution analysis contribution
- Panoramic execution view integration
- Cross-team execution pattern awareness
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionInsightType(Enum):
    """Types of execution insights from CIL"""
    EXECUTION_CONFLUENCE = "execution_confluence"
    EXECUTION_EXPERIMENT_INSIGHT = "execution_experiment_insight"
    EXECUTION_DOCTRINE_UPDATE = "execution_doctrine_update"
    EXECUTION_STRATEGIC_ANALYSIS = "execution_strategic_analysis"
    EXECUTION_CROSS_TEAM_PATTERN = "execution_cross_team_pattern"
    EXECUTION_META_SIGNAL = "execution_meta_signal"


@dataclass
class ExecutionInsightData:
    """Execution insight data from CIL"""
    insight_id: str
    insight_type: ExecutionInsightType
    execution_type: str
    insight_content: Dict[str, Any]
    confidence_score: float
    relevance_score: float
    applicability_score: float
    source_teams: List[str]
    created_at: datetime
    expires_at: Optional[datetime]


class StrategicExecutionInsightConsumer:
    """Handles natural consumption of CIL strategic execution insights"""
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.insight_cache = {}
        self.subscription_patterns = {}
        self.insight_history = []
        
    async def consume_cil_execution_insights(self, execution_type: str) -> List[Dict[str, Any]]:
        """
        Naturally consume valuable CIL execution insights for execution type
        
        Args:
            execution_type: Type of execution to get insights for
            
        Returns:
            List of relevant CIL execution insights
        """
        try:
            # Query CIL execution meta-signals from AD_strands
            cil_meta_signals = await self._query_cil_execution_meta_signals(execution_type)
            
            # Find high-resonance strategic execution insights
            high_resonance_insights = await self._filter_high_resonance_insights(cil_meta_signals)
            
            # Apply execution insights to analysis naturally
            applicable_insights = await self._filter_applicable_insights(
                high_resonance_insights, execution_type
            )
            
            # Benefit from CIL's panoramic execution view
            enriched_insights = await self._enrich_insights_with_panoramic_view(applicable_insights)
            
            # Cache insights for future use
            self._cache_insights(execution_type, enriched_insights)
            
            logger.info(f"Consumed {len(enriched_insights)} CIL execution insights for {execution_type}")
            
            return enriched_insights
            
        except Exception as e:
            logger.error(f"Error consuming CIL execution insights: {e}")
            return []
    
    async def subscribe_to_valuable_execution_meta_signals(self, execution_meta_signal_types: List[str]):
        """
        Subscribe to valuable CIL execution meta-signals organically
        
        Args:
            execution_meta_signal_types: Types of execution meta-signals to subscribe to
        """
        try:
            # Listen for strategic execution confluence events
            confluence_subscription = await self._create_confluence_subscription(execution_meta_signal_types)
            
            # Listen for valuable execution experiment insights
            experiment_subscription = await self._create_experiment_subscription(execution_meta_signal_types)
            
            # Listen for execution doctrine updates
            doctrine_subscription = await self._create_doctrine_subscription(execution_meta_signal_types)
            
            # Apply execution insights naturally when valuable
            await self._setup_natural_insight_application(confluence_subscription, experiment_subscription, doctrine_subscription)
            
            # Store subscription patterns
            self.subscription_patterns[execution_meta_signal_types[0]] = {
                'confluence': confluence_subscription,
                'experiment': experiment_subscription,
                'doctrine': doctrine_subscription,
                'created_at': datetime.now()
            }
            
            logger.info(f"Subscribed to {len(execution_meta_signal_types)} execution meta-signal types")
            
        except Exception as e:
            logger.error(f"Error subscribing to execution meta-signals: {e}")
    
    async def contribute_to_strategic_execution_analysis(self, execution_analysis_data: Dict[str, Any]):
        """
        Contribute to CIL strategic execution analysis through natural insights
        
        Args:
            execution_analysis_data: Execution analysis data to contribute
        """
        try:
            # Provide execution perspective
            execution_perspective = await self._provide_execution_perspective(execution_analysis_data)
            
            # Contribute execution mechanism insights
            mechanism_insights = await self._contribute_execution_mechanism_insights(execution_analysis_data)
            
            # Suggest valuable execution experiments
            experiment_suggestions = await self._suggest_valuable_execution_experiments(execution_analysis_data)
            
            # Create strategic execution insight strand in AD_strands
            strategic_insight_strand = {
                'module': 'trader',
                'kind': 'strategic_execution_contribution',
                'content': {
                    'execution_perspective': execution_perspective,
                    'mechanism_insights': mechanism_insights,
                    'experiment_suggestions': experiment_suggestions,
                    'analysis_data': execution_analysis_data,
                    'contribution_type': 'strategic_execution_analysis',
                    'insight_quality': self._assess_insight_quality(execution_analysis_data),
                    'applicability_score': self._calculate_applicability_score(execution_analysis_data)
                },
                'tags': [
                    'trader:strategic_contribution',
                    'trader:execution_analysis',
                    'cil:strategic_contribution',
                    'trader:mechanism_insights'
                ],
                'sig_confidence': execution_analysis_data.get('confidence', 0.5),
                'outcome_score': execution_analysis_data.get('success_score', 0.5),
                'created_at': datetime.now().isoformat()
            }
            
            # Publish strategic insight strand
            insight_id = await self._publish_strategic_insight_strand(strategic_insight_strand)
            
            # Track contribution history
            self._track_contribution_history(insight_id, strategic_insight_strand)
            
            logger.info(f"Contributed to strategic execution analysis: {insight_id}, "
                       f"insight quality: {strategic_insight_strand['content']['insight_quality']:.3f}")
            
            return insight_id
            
        except Exception as e:
            logger.error(f"Error contributing to strategic execution analysis: {e}")
            return ""
    
    async def _query_cil_execution_meta_signals(self, execution_type: str) -> List[Dict[str, Any]]:
        """Query CIL execution meta-signals from AD_strands table"""
        try:
            # Search for CIL meta-signals related to execution
            meta_signals = await self._search_cil_meta_signals(execution_type)
            
            # Filter for execution-related signals
            execution_signals = [
                signal for signal in meta_signals 
                if self._is_execution_related_signal(signal, execution_type)
            ]
            
            return execution_signals
            
        except Exception as e:
            logger.error(f"Error querying CIL execution meta-signals: {e}")
            return []
    
    async def _filter_high_resonance_insights(self, cil_meta_signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter for high-resonance strategic execution insights"""
        try:
            high_resonance_insights = []
            
            for signal in cil_meta_signals:
                # Check resonance metrics
                resonance_score = signal.get('content', {}).get('resonance_metrics', {}).get('phi', 0.5)
                confidence_score = signal.get('sig_confidence', 0.5)
                
                # High resonance threshold
                if resonance_score > 0.7 and confidence_score > 0.6:
                    high_resonance_insights.append(signal)
            
            return high_resonance_insights
            
        except Exception as e:
            logger.error(f"Error filtering high-resonance insights: {e}")
            return []
    
    async def _filter_applicable_insights(self, insights: List[Dict[str, Any]], execution_type: str) -> List[Dict[str, Any]]:
        """Filter insights for applicability to execution type"""
        try:
            applicable_insights = []
            
            for insight in insights:
                # Check if insight is applicable to execution type
                applicability = await self._assess_insight_applicability(insight, execution_type)
                
                if applicability > 0.6:  # 60% applicability threshold
                    insight['applicability_score'] = applicability
                    applicable_insights.append(insight)
            
            return applicable_insights
            
        except Exception as e:
            logger.error(f"Error filtering applicable insights: {e}")
            return []
    
    async def _enrich_insights_with_panoramic_view(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich insights with CIL's panoramic execution view"""
        try:
            enriched_insights = []
            
            for insight in insights:
                # Add panoramic context
                panoramic_context = await self._get_panoramic_execution_context(insight)
                
                # Add cross-team perspective
                cross_team_perspective = await self._get_cross_team_execution_perspective(insight)
                
                # Enrich insight
                enriched_insight = insight.copy()
                enriched_insight['panoramic_context'] = panoramic_context
                enriched_insight['cross_team_perspective'] = cross_team_perspective
                enriched_insight['enrichment_timestamp'] = datetime.now().isoformat()
                
                enriched_insights.append(enriched_insight)
            
            return enriched_insights
            
        except Exception as e:
            logger.error(f"Error enriching insights with panoramic view: {e}")
            return insights
    
    async def _provide_execution_perspective(self, execution_analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide execution perspective for strategic analysis"""
        try:
            perspective = {
                'execution_quality_analysis': self._analyze_execution_quality(execution_analysis_data),
                'venue_selection_insights': self._analyze_venue_selection(execution_analysis_data),
                'timing_optimization_insights': self._analyze_timing_optimization(execution_analysis_data),
                'market_impact_analysis': self._analyze_market_impact(execution_analysis_data),
                'risk_assessment': self._assess_execution_risk(execution_analysis_data),
                'performance_metrics': self._extract_performance_metrics(execution_analysis_data)
            }
            
            return perspective
            
        except Exception as e:
            logger.error(f"Error providing execution perspective: {e}")
            return {}
    
    async def _contribute_execution_mechanism_insights(self, execution_analysis_data: Dict[str, Any]) -> List[str]:
        """Contribute execution mechanism insights"""
        try:
            mechanism_insights = []
            
            # Analyze execution mechanisms
            if 'execution_quality' in execution_analysis_data:
                quality = execution_analysis_data['execution_quality']
                if quality > 0.8:
                    mechanism_insights.append("High execution quality results from optimal venue selection and timing")
                elif quality < 0.3:
                    mechanism_insights.append("Low execution quality indicates venue or timing optimization opportunities")
            
            # Analyze venue selection mechanisms
            if 'venue_performance' in execution_analysis_data:
                venue_perf = execution_analysis_data['venue_performance']
                mechanism_insights.append(f"Venue performance patterns: {venue_perf}")
            
            # Analyze timing mechanisms
            if 'timing_analysis' in execution_analysis_data:
                timing = execution_analysis_data['timing_analysis']
                mechanism_insights.append(f"Timing optimization insights: {timing}")
            
            # Analyze market impact mechanisms
            if 'market_impact' in execution_analysis_data:
                impact = execution_analysis_data['market_impact']
                mechanism_insights.append(f"Market impact mechanisms: {impact}")
            
            return mechanism_insights
            
        except Exception as e:
            logger.error(f"Error contributing execution mechanism insights: {e}")
            return []
    
    async def _suggest_valuable_execution_experiments(self, execution_analysis_data: Dict[str, Any]) -> List[str]:
        """Suggest valuable execution experiments"""
        try:
            experiment_suggestions = []
            
            # Suggest experiments based on analysis gaps
            if 'execution_quality' in execution_analysis_data:
                quality = execution_analysis_data['execution_quality']
                if quality < 0.7:
                    experiment_suggestions.append("Experiment with alternative execution strategies to improve quality")
            
            # Suggest venue experiments
            if 'venue_coverage' in execution_analysis_data:
                coverage = execution_analysis_data['venue_coverage']
                if coverage < 0.8:
                    experiment_suggestions.append("Experiment with additional venues to improve coverage")
            
            # Suggest timing experiments
            if 'timing_optimization' in execution_analysis_data:
                timing = execution_analysis_data['timing_optimization']
                if timing < 0.6:
                    experiment_suggestions.append("Experiment with timing optimization algorithms")
            
            # Suggest market impact experiments
            if 'market_impact' in execution_analysis_data:
                impact = execution_analysis_data['market_impact']
                if impact > 0.005:  # High impact
                    experiment_suggestions.append("Experiment with impact reduction strategies")
            
            return experiment_suggestions
            
        except Exception as e:
            logger.error(f"Error suggesting valuable execution experiments: {e}")
            return []
    
    def _assess_insight_quality(self, execution_analysis_data: Dict[str, Any]) -> float:
        """Assess the quality of execution insights"""
        try:
            quality_score = 0.0
            
            # Data completeness
            required_fields = ['execution_quality', 'venue_performance', 'timing_analysis']
            completeness = sum(1 for field in required_fields if field in execution_analysis_data) / len(required_fields)
            quality_score += completeness * 0.4
            
            # Analysis depth
            analysis_depth = len(execution_analysis_data.get('detailed_analysis', {}))
            quality_score += min(analysis_depth / 10.0, 1.0) * 0.3
            
            # Confidence level
            confidence = execution_analysis_data.get('confidence', 0.5)
            quality_score += confidence * 0.3
            
            return max(0.0, min(1.0, quality_score))
            
        except Exception as e:
            logger.error(f"Error assessing insight quality: {e}")
            return 0.5
    
    def _calculate_applicability_score(self, execution_analysis_data: Dict[str, Any]) -> float:
        """Calculate applicability score for execution analysis"""
        try:
            applicability = 0.0
            
            # Execution type relevance
            if 'execution_type' in execution_analysis_data:
                applicability += 0.3
            
            # Market condition relevance
            if 'market_conditions' in execution_analysis_data:
                applicability += 0.2
            
            # Venue relevance
            if 'venue' in execution_analysis_data:
                applicability += 0.2
            
            # Strategy relevance
            if 'execution_strategy' in execution_analysis_data:
                applicability += 0.2
            
            # Timeliness
            if 'timestamp' in execution_analysis_data:
                applicability += 0.1
            
            return max(0.0, min(1.0, applicability))
            
        except Exception as e:
            logger.error(f"Error calculating applicability score: {e}")
            return 0.5
    
    def _cache_insights(self, execution_type: str, insights: List[Dict[str, Any]]):
        """Cache insights for future use"""
        self.insight_cache[execution_type] = {
            'insights': insights,
            'cached_at': datetime.now(),
            'access_count': 0
        }
    
    def _track_contribution_history(self, insight_id: str, strategic_insight_strand: Dict[str, Any]):
        """Track contribution history"""
        self.insight_history.append({
            'insight_id': insight_id,
            'strand': strategic_insight_strand,
            'contributed_at': datetime.now()
        })
        
        # Keep only last 100 contributions
        if len(self.insight_history) > 100:
            self.insight_history = self.insight_history[-100:]
    
    # Helper methods for analysis
    def _analyze_execution_quality(self, execution_analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze execution quality"""
        return {
            'overall_quality': execution_analysis_data.get('execution_quality', 0.5),
            'quality_trend': execution_analysis_data.get('quality_trend', 'stable'),
            'quality_factors': execution_analysis_data.get('quality_factors', [])
        }
    
    def _analyze_venue_selection(self, execution_analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze venue selection"""
        return {
            'venue_performance': execution_analysis_data.get('venue_performance', {}),
            'venue_selection_quality': execution_analysis_data.get('venue_selection_quality', 0.5),
            'venue_optimization_opportunities': execution_analysis_data.get('venue_optimization_opportunities', [])
        }
    
    def _analyze_timing_optimization(self, execution_analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze timing optimization"""
        return {
            'timing_analysis': execution_analysis_data.get('timing_analysis', {}),
            'timing_optimization_score': execution_analysis_data.get('timing_optimization_score', 0.5),
            'timing_improvement_opportunities': execution_analysis_data.get('timing_improvement_opportunities', [])
        }
    
    def _analyze_market_impact(self, execution_analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market impact"""
        return {
            'market_impact': execution_analysis_data.get('market_impact', 0.0),
            'impact_analysis': execution_analysis_data.get('impact_analysis', {}),
            'impact_optimization_opportunities': execution_analysis_data.get('impact_optimization_opportunities', [])
        }
    
    def _assess_execution_risk(self, execution_analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess execution risk"""
        return {
            'risk_score': execution_analysis_data.get('risk_score', 0.5),
            'risk_factors': execution_analysis_data.get('risk_factors', []),
            'risk_mitigation_opportunities': execution_analysis_data.get('risk_mitigation_opportunities', [])
        }
    
    def _extract_performance_metrics(self, execution_analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract performance metrics"""
        return {
            'success_rate': execution_analysis_data.get('success_rate', 0.5),
            'average_fill_time': execution_analysis_data.get('average_fill_time', 0.0),
            'slippage_metrics': execution_analysis_data.get('slippage_metrics', {}),
            'performance_trend': execution_analysis_data.get('performance_trend', 'stable')
        }
    
    # Database interaction methods (to be implemented based on existing patterns)
    async def _search_cil_meta_signals(self, execution_type: str) -> List[Dict[str, Any]]:
        """Search CIL meta-signals in AD_strands"""
        # Implementation will follow existing database patterns
        return []
    
    def _is_execution_related_signal(self, signal: Dict[str, Any], execution_type: str) -> bool:
        """Check if signal is execution-related"""
        # Implementation will follow existing patterns
        return True
    
    async def _assess_insight_applicability(self, insight: Dict[str, Any], execution_type: str) -> float:
        """Assess insight applicability to execution type"""
        # Implementation will follow existing patterns
        return 0.7
    
    async def _get_panoramic_execution_context(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """Get panoramic execution context from CIL"""
        # Implementation will follow existing patterns
        return {}
    
    async def _get_cross_team_execution_perspective(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """Get cross-team execution perspective"""
        # Implementation will follow existing patterns
        return {}
    
    async def _create_confluence_subscription(self, execution_meta_signal_types: List[str]) -> str:
        """Create confluence subscription"""
        # Implementation will follow existing patterns
        return f"confluence_sub_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def _create_experiment_subscription(self, execution_meta_signal_types: List[str]) -> str:
        """Create experiment subscription"""
        # Implementation will follow existing patterns
        return f"experiment_sub_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def _create_doctrine_subscription(self, execution_meta_signal_types: List[str]) -> str:
        """Create doctrine subscription"""
        # Implementation will follow existing patterns
        return f"doctrine_sub_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def _setup_natural_insight_application(self, confluence_sub: str, experiment_sub: str, doctrine_sub: str):
        """Setup natural insight application"""
        # Implementation will follow existing patterns
        pass
    
    async def _publish_strategic_insight_strand(self, strategic_insight_strand: Dict[str, Any]) -> str:
        """Publish strategic insight strand to AD_strands"""
        # Implementation will follow existing database patterns
        return f"strategic_insight_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
