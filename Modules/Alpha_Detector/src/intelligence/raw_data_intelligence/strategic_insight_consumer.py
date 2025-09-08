"""
Strategic Insight Consumer for Raw Data Intelligence

Handles natural consumption of CIL strategic insights. Enables agents to naturally benefit 
from CIL's panoramic view by consuming valuable meta-signals, strategic confluence events, 
and cross-team pattern insights for enhanced analysis and decision-making.

Key Concepts:
- CIL Meta-Signal Consumption: Natural subscription to valuable CIL insights
- Strategic Confluence Events: Cross-team pattern detection and analysis
- Panoramic View Benefits: Leveraging CIL's cross-team perspective
- Organic Insight Application: Natural integration of strategic insights
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np

from src.utils.supabase_manager import SupabaseManager


class StrategicInsightConsumer:
    """
    Handles natural consumption of CIL strategic insights
    
    Enables agents to:
    - Consume valuable CIL insights naturally
    - Subscribe to strategic meta-signals organically
    - Benefit from CIL's panoramic view
    - Contribute to strategic analysis
    - Apply insights naturally when valuable
    """
    
    def __init__(self, supabase_manager: SupabaseManager):
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(__name__)
        
        # Strategic insight consumption parameters
        self.insight_relevance_threshold = 0.6  # Minimum relevance for insight consumption
        self.meta_signal_confidence_threshold = 0.7  # Minimum confidence for meta-signal subscription
        self.confluence_strength_threshold = 0.8  # Minimum strength for confluence events
        self.insight_application_threshold = 0.5  # Minimum threshold for applying insights
        
        # CIL meta-signal types
        self.meta_signal_types = [
            'strategic_confluence',
            'experiment_insights',
            'doctrine_updates',
            'cross_team_patterns',
            'resonance_insights',
            'uncertainty_resolution',
            'motif_evolution',
            'strategic_planning'
        ]
        
        # Strategic insight categories
        self.insight_categories = [
            'market_structure',
            'pattern_evolution',
            'risk_assessment',
            'opportunity_identification',
            'strategy_optimization',
            'doctrine_guidance'
        ]
        
        # Insight consumption tracking
        self.consumed_insights = []
        self.applied_insights = []
        self.insight_effectiveness = {}
    
    async def consume_cil_insights(self, pattern_type: str) -> List[Dict[str, Any]]:
        """
        Naturally consume valuable CIL insights for pattern type
        
        Args:
            pattern_type: Type of pattern to find insights for
            
        Returns:
            List of relevant CIL insights
        """
        try:
            self.logger.info(f"Consuming CIL insights for pattern type: {pattern_type}")
            
            # 1. Query CIL meta-signals
            cil_meta_signals = await self._query_cil_meta_signals(pattern_type)
            
            # 2. Find high-resonance strategic insights
            high_resonance_insights = await self._filter_high_resonance_insights(cil_meta_signals)
            
            # 3. Apply insights to analysis naturally
            applicable_insights = await self._filter_applicable_insights(high_resonance_insights, pattern_type)
            
            # 4. Benefit from CIL's panoramic view
            panoramic_insights = await self._extract_panoramic_insights(applicable_insights)
            
            # 5. Track insight consumption
            await self._track_insight_consumption(applicable_insights, pattern_type)
            
            self.logger.info(f"Consumed {len(applicable_insights)} CIL insights for {pattern_type}")
            return applicable_insights
            
        except Exception as e:
            self.logger.error(f"CIL insight consumption failed: {e}")
            return []
    
    async def subscribe_to_valuable_meta_signals(self, meta_signal_types: List[str]) -> Dict[str, Any]:
        """
        Subscribe to valuable CIL meta-signals organically
        
        Args:
            meta_signal_types: Types of meta-signals to subscribe to
            
        Returns:
            Subscription results and active subscriptions
        """
        try:
            self.logger.info(f"Subscribing to valuable meta-signals: {meta_signal_types}")
            
            subscription_results = {
                'subscription_timestamp': datetime.now(timezone.utc).isoformat(),
                'subscribed_types': [],
                'active_subscriptions': [],
                'subscription_confidence': {},
                'expected_insights': {}
            }
            
            # 1. Listen for strategic confluence events
            if 'strategic_confluence' in meta_signal_types:
                confluence_subscription = await self._subscribe_to_confluence_events()
                subscription_results['subscribed_types'].append('strategic_confluence')
                subscription_results['active_subscriptions'].append(confluence_subscription)
            
            # 2. Listen for valuable experiment insights
            if 'experiment_insights' in meta_signal_types:
                experiment_subscription = await self._subscribe_to_experiment_insights()
                subscription_results['subscribed_types'].append('experiment_insights')
                subscription_results['active_subscriptions'].append(experiment_subscription)
            
            # 3. Listen for doctrine updates
            if 'doctrine_updates' in meta_signal_types:
                doctrine_subscription = await self._subscribe_to_doctrine_updates()
                subscription_results['subscribed_types'].append('doctrine_updates')
                subscription_results['active_subscriptions'].append(doctrine_subscription)
            
            # 4. Apply insights naturally when valuable
            natural_application = await self._setup_natural_insight_application(subscription_results)
            subscription_results['natural_application'] = natural_application
            
            self.logger.info(f"Subscribed to {len(subscription_results['subscribed_types'])} meta-signal types")
            return subscription_results
            
        except Exception as e:
            self.logger.error(f"Meta-signal subscription failed: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    async def contribute_to_strategic_analysis(self, analysis_data: Dict[str, Any]) -> str:
        """
        Contribute to CIL strategic analysis through natural insights
        
        Args:
            analysis_data: Analysis data to contribute to strategic analysis
            
        Returns:
            Strategic insight strand ID
        """
        try:
            self.logger.info("Contributing to CIL strategic analysis")
            
            # 1. Provide raw data perspective
            raw_data_perspective = await self._extract_raw_data_perspective(analysis_data)
            
            # 2. Contribute mechanism insights
            mechanism_insights = await self._extract_mechanism_insights(analysis_data)
            
            # 3. Suggest valuable experiments
            experiment_suggestions = await self._suggest_valuable_experiments(analysis_data)
            
            # 4. Create strategic insight strand
            strategic_insight = {
                'insight_id': self._generate_insight_id(analysis_data),
                'contribution_type': 'raw_data_strategic_analysis',
                'raw_data_perspective': raw_data_perspective,
                'mechanism_insights': mechanism_insights,
                'experiment_suggestions': experiment_suggestions,
                'analysis_data': analysis_data,
                'contribution_timestamp': datetime.now(timezone.utc).isoformat(),
                'contributor_agent': analysis_data.get('agent', 'unknown'),
                'strategic_relevance': await self._calculate_strategic_relevance(analysis_data),
                'insight_confidence': analysis_data.get('confidence', 0.0)
            }
            
            # 5. Publish strategic insight strand
            insight_strand_id = await self._publish_strategic_insight(strategic_insight)
            
            if insight_strand_id:
                self.logger.info(f"Contributed strategic insight: {insight_strand_id}")
                self.logger.info(f"Strategic relevance: {strategic_insight['strategic_relevance']}")
                self.logger.info(f"Experiment suggestions: {len(experiment_suggestions)}")
            
            return insight_strand_id
            
        except Exception as e:
            self.logger.error(f"Strategic analysis contribution failed: {e}")
            return None
    
    async def _query_cil_meta_signals(self, pattern_type: str) -> List[Dict[str, Any]]:
        """Query CIL meta-signals for pattern type"""
        try:
            # Mock implementation - in real system, this would query CIL meta-signals
            cil_meta_signals = [
                {
                    'meta_signal_id': f'cil_signal_{pattern_type}_1',
                    'signal_type': 'strategic_confluence',
                    'pattern_type': pattern_type,
                    'confidence': 0.8,
                    'resonance_score': 0.9,
                    'strategic_insight': f'High confluence detected for {pattern_type} patterns',
                    'cross_team_evidence': ['volume_team', 'divergence_team', 'microstructure_team'],
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                {
                    'meta_signal_id': f'cil_signal_{pattern_type}_2',
                    'signal_type': 'experiment_insights',
                    'pattern_type': pattern_type,
                    'confidence': 0.7,
                    'resonance_score': 0.8,
                    'strategic_insight': f'Experiment results show {pattern_type} effectiveness',
                    'experiment_results': {'success_rate': 0.75, 'sample_size': 100},
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            ]
            
            return cil_meta_signals
            
        except Exception as e:
            self.logger.error(f"CIL meta-signal query failed: {e}")
            return []
    
    async def _filter_high_resonance_insights(self, meta_signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter high-resonance strategic insights"""
        try:
            high_resonance_insights = []
            
            for signal in meta_signals:
                resonance_score = signal.get('resonance_score', 0.0)
                confidence = signal.get('confidence', 0.0)
                
                # High resonance if both resonance and confidence are above thresholds
                if resonance_score >= self.insight_relevance_threshold and confidence >= self.meta_signal_confidence_threshold:
                    high_resonance_insights.append(signal)
            
            return high_resonance_insights
            
        except Exception as e:
            self.logger.error(f"High resonance insight filtering failed: {e}")
            return []
    
    async def _filter_applicable_insights(self, insights: List[Dict[str, Any]], pattern_type: str) -> List[Dict[str, Any]]:
        """Filter insights applicable to pattern type"""
        try:
            applicable_insights = []
            
            for insight in insights:
                # Check if insight is applicable to pattern type
                insight_pattern_type = insight.get('pattern_type', '')
                if insight_pattern_type == pattern_type or insight_pattern_type == 'general':
                    applicable_insights.append(insight)
            
            return applicable_insights
            
        except Exception as e:
            self.logger.error(f"Applicable insight filtering failed: {e}")
            return []
    
    async def _extract_panoramic_insights(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract panoramic insights from CIL's cross-team perspective"""
        try:
            panoramic_insights = []
            
            for insight in insights:
                # Extract cross-team perspective
                cross_team_evidence = insight.get('cross_team_evidence', [])
                if cross_team_evidence:
                    panoramic_insight = {
                        'original_insight': insight,
                        'panoramic_perspective': {
                            'cross_team_consensus': len(cross_team_evidence),
                            'team_diversity': len(set(cross_team_evidence)),
                            'panoramic_confidence': insight.get('confidence', 0.0) * 1.1,  # Boost for cross-team
                            'strategic_significance': 'high' if len(cross_team_evidence) >= 3 else 'medium'
                        }
                    }
                    panoramic_insights.append(panoramic_insight)
            
            return panoramic_insights
            
        except Exception as e:
            self.logger.error(f"Panoramic insight extraction failed: {e}")
            return []
    
    async def _track_insight_consumption(self, insights: List[Dict[str, Any]], pattern_type: str):
        """Track insight consumption for learning"""
        try:
            consumption_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'pattern_type': pattern_type,
                'insights_consumed': len(insights),
                'insight_types': [insight.get('signal_type', 'unknown') for insight in insights],
                'average_confidence': np.mean([insight.get('confidence', 0.0) for insight in insights]) if insights else 0.0,
                'average_resonance': np.mean([insight.get('resonance_score', 0.0) for insight in insights]) if insights else 0.0
            }
            
            self.consumed_insights.append(consumption_entry)
            
            # Keep only recent consumption history
            if len(self.consumed_insights) > 100:
                self.consumed_insights = self.consumed_insights[-100:]
            
        except Exception as e:
            self.logger.error(f"Insight consumption tracking failed: {e}")
    
    async def _subscribe_to_confluence_events(self) -> Dict[str, Any]:
        """Subscribe to strategic confluence events"""
        try:
            subscription = {
                'subscription_id': f'confluence_sub_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'subscription_type': 'strategic_confluence',
                'filter_criteria': {
                    'min_confluence_strength': self.confluence_strength_threshold,
                    'min_team_count': 2,
                    'pattern_types': ['volume', 'divergence', 'microstructure']
                },
                'subscription_timestamp': datetime.now(timezone.utc).isoformat(),
                'active': True
            }
            
            return subscription
            
        except Exception as e:
            self.logger.error(f"Confluence event subscription failed: {e}")
            return {}
    
    async def _subscribe_to_experiment_insights(self) -> Dict[str, Any]:
        """Subscribe to valuable experiment insights"""
        try:
            subscription = {
                'subscription_id': f'experiment_sub_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'subscription_type': 'experiment_insights',
                'filter_criteria': {
                    'min_experiment_confidence': 0.7,
                    'min_sample_size': 50,
                    'experiment_types': ['durability', 'stack', 'lead_lag', 'ablation']
                },
                'subscription_timestamp': datetime.now(timezone.utc).isoformat(),
                'active': True
            }
            
            return subscription
            
        except Exception as e:
            self.logger.error(f"Experiment insight subscription failed: {e}")
            return {}
    
    async def _subscribe_to_doctrine_updates(self) -> Dict[str, Any]:
        """Subscribe to doctrine updates"""
        try:
            subscription = {
                'subscription_id': f'doctrine_sub_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'subscription_type': 'doctrine_updates',
                'filter_criteria': {
                    'doctrine_types': ['positive', 'negative', 'neutral'],
                    'min_evidence_count': 5,
                    'update_confidence': 0.8
                },
                'subscription_timestamp': datetime.now(timezone.utc).isoformat(),
                'active': True
            }
            
            return subscription
            
        except Exception as e:
            self.logger.error(f"Doctrine update subscription failed: {e}")
            return {}
    
    async def _setup_natural_insight_application(self, subscription_results: Dict[str, Any]) -> Dict[str, Any]:
        """Setup natural insight application"""
        try:
            natural_application = {
                'application_id': f'natural_app_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'application_type': 'natural_insight_integration',
                'application_rules': {
                    'auto_apply_threshold': self.insight_application_threshold,
                    'confidence_boost_factor': 1.2,
                    'resonance_enhancement': True,
                    'uncertainty_reduction': True
                },
                'application_timestamp': datetime.now(timezone.utc).isoformat(),
                'active': True
            }
            
            return natural_application
            
        except Exception as e:
            self.logger.error(f"Natural insight application setup failed: {e}")
            return {}
    
    async def _extract_raw_data_perspective(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract raw data perspective for strategic analysis"""
        try:
            raw_data_perspective = {
                'data_quality': analysis_data.get('data_points', 0),
                'analysis_confidence': analysis_data.get('confidence', 0.0),
                'pattern_significance': len(analysis_data.get('significant_patterns', [])),
                'uncertainty_level': analysis_data.get('uncertainty_analysis', {}).get('uncertainty_detected', False),
                'resonance_contribution': analysis_data.get('resonance', {}).get('enhanced_score', 0.0),
                'temporal_characteristics': analysis_data.get('temporal', {}),
                'cross_validation_results': analysis_data.get('cross_validation', {})
            }
            
            return raw_data_perspective
            
        except Exception as e:
            self.logger.error(f"Raw data perspective extraction failed: {e}")
            return {}
    
    async def _extract_mechanism_insights(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract mechanism insights from analysis data"""
        try:
            mechanism_insights = []
            
            # Extract insights from patterns
            patterns = analysis_data.get('patterns', [])
            for pattern in patterns:
                if pattern.get('confidence', 0.0) > 0.7:
                    mechanism_insight = {
                        'mechanism_type': pattern.get('type', 'unknown'),
                        'confidence': pattern.get('confidence', 0.0),
                        'mechanism_description': f"High confidence {pattern.get('type', 'pattern')} detected",
                        'causal_factors': self._infer_causal_factors(pattern),
                        'predictive_value': pattern.get('severity', 'low')
                    }
                    mechanism_insights.append(mechanism_insight)
            
            # Extract insights from analysis components
            analysis_components = analysis_data.get('analysis_components', {})
            for component, data in analysis_components.items():
                if isinstance(data, dict) and data.get('confidence', 0.0) > 0.7:
                    mechanism_insight = {
                        'mechanism_type': f'{component}_analysis',
                        'confidence': data.get('confidence', 0.0),
                        'mechanism_description': f"Strong {component} analysis results",
                        'causal_factors': [component],
                        'predictive_value': 'medium'
                    }
                    mechanism_insights.append(mechanism_insight)
            
            return mechanism_insights
            
        except Exception as e:
            self.logger.error(f"Mechanism insight extraction failed: {e}")
            return []
    
    async def _suggest_valuable_experiments(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest valuable experiments based on analysis"""
        try:
            experiment_suggestions = []
            
            # Suggest experiments based on uncertainty
            uncertainty_analysis = analysis_data.get('uncertainty_analysis', {})
            if uncertainty_analysis.get('uncertainty_detected', False):
                uncertainty_experiment = {
                    'experiment_type': 'uncertainty_resolution',
                    'hypothesis': 'Resolve uncertainty through targeted data collection',
                    'methodology': 'Increase data granularity and apply additional analysis methods',
                    'expected_outcome': 'Reduced uncertainty and improved pattern clarity',
                    'priority': 'high'
                }
                experiment_suggestions.append(uncertainty_experiment)
            
            # Suggest experiments based on pattern confidence
            patterns = analysis_data.get('patterns', [])
            for pattern in patterns:
                if pattern.get('confidence', 0.0) > 0.8:
                    pattern_experiment = {
                        'experiment_type': 'pattern_validation',
                        'hypothesis': f"Validate high-confidence {pattern.get('type', 'pattern')}",
                        'methodology': 'Cross-validate with additional data sources',
                        'expected_outcome': 'Confirmed pattern reliability',
                        'priority': 'medium'
                    }
                    experiment_suggestions.append(pattern_experiment)
            
            # Suggest experiments based on resonance
            resonance = analysis_data.get('resonance', {})
            if resonance.get('enhanced_score', 0.0) > 0.8:
                resonance_experiment = {
                    'experiment_type': 'resonance_enhancement',
                    'hypothesis': 'Enhance resonance through pattern optimization',
                    'methodology': 'Apply resonance-based pattern selection',
                    'expected_outcome': 'Improved pattern effectiveness',
                    'priority': 'medium'
                }
                experiment_suggestions.append(resonance_experiment)
            
            return experiment_suggestions
            
        except Exception as e:
            self.logger.error(f"Experiment suggestion failed: {e}")
            return []
    
    async def _calculate_strategic_relevance(self, analysis_data: Dict[str, Any]) -> float:
        """Calculate strategic relevance of analysis data"""
        try:
            strategic_relevance = 0.0
            
            # Base relevance from confidence
            confidence = analysis_data.get('confidence', 0.0)
            strategic_relevance += confidence * 0.3
            
            # Relevance from significant patterns
            significant_patterns = analysis_data.get('significant_patterns', [])
            pattern_relevance = min(0.3, len(significant_patterns) * 0.1)
            strategic_relevance += pattern_relevance
            
            # Relevance from resonance
            resonance = analysis_data.get('resonance', {})
            resonance_relevance = resonance.get('enhanced_score', 0.0) * 0.2
            strategic_relevance += resonance_relevance
            
            # Relevance from uncertainty (uncertainty can be strategically valuable)
            uncertainty_analysis = analysis_data.get('uncertainty_analysis', {})
            if uncertainty_analysis.get('uncertainty_detected', False):
                uncertainty_relevance = 0.2  # Uncertainty is strategically valuable
                strategic_relevance += uncertainty_relevance
            
            return min(1.0, strategic_relevance)
            
        except Exception as e:
            self.logger.error(f"Strategic relevance calculation failed: {e}")
            return 0.0
    
    def _infer_causal_factors(self, pattern: Dict[str, Any]) -> List[str]:
        """Infer causal factors from pattern"""
        try:
            pattern_type = pattern.get('type', '').lower()
            causal_factors = []
            
            if 'volume' in pattern_type:
                causal_factors.extend(['institutional_flow', 'retail_sentiment', 'market_microstructure'])
            elif 'divergence' in pattern_type:
                causal_factors.extend(['momentum_exhaustion', 'sentiment_shift', 'institutional_positioning'])
            elif 'microstructure' in pattern_type:
                causal_factors.extend(['order_flow_imbalance', 'market_maker_behavior', 'liquidity_provision'])
            else:
                causal_factors.extend(['market_sentiment', 'technical_factors', 'institutional_flow'])
            
            return causal_factors
            
        except Exception as e:
            self.logger.error(f"Causal factor inference failed: {e}")
            return []
    
    def _generate_insight_id(self, analysis_data: Dict[str, Any]) -> str:
        """Generate unique insight ID"""
        try:
            pattern_type = analysis_data.get('type', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return f"strategic_insight_{pattern_type}_{timestamp}"
        except Exception as e:
            self.logger.error(f"Insight ID generation failed: {e}")
            return f"strategic_insight_unknown_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def _publish_strategic_insight(self, strategic_insight: Dict[str, Any]) -> Optional[str]:
        """Publish strategic insight to database"""
        try:
            # Mock implementation - in real system, this would publish to AD_strands table
            insight_id = strategic_insight.get('insight_id', 'unknown')
            strand_id = f"strategic_insight_{insight_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            return strand_id
            
        except Exception as e:
            self.logger.error(f"Strategic insight publishing failed: {e}")
            return None
    
    def get_insight_consumption_summary(self) -> Dict[str, Any]:
        """Get summary of insight consumption"""
        try:
            if not self.consumed_insights:
                return {'total_insights_consumed': 0, 'consumption_summary': 'No insights consumed yet'}
            
            total_insights = sum(entry['insights_consumed'] for entry in self.consumed_insights)
            avg_confidence = np.mean([entry['average_confidence'] for entry in self.consumed_insights])
            avg_resonance = np.mean([entry['average_resonance'] for entry in self.consumed_insights])
            
            return {
                'total_insights_consumed': total_insights,
                'consumption_entries': len(self.consumed_insights),
                'average_confidence': avg_confidence,
                'average_resonance': avg_resonance,
                'recent_consumption': self.consumed_insights[-5:] if self.consumed_insights else []
            }
            
        except Exception as e:
            self.logger.error(f"Insight consumption summary failed: {e}")
            return {'error': str(e)}
