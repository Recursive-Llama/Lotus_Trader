"""
Doctrine Integration for Raw Data Intelligence

Handles organic doctrine integration for strategic learning. Enables agents to learn from 
and contribute to strategic doctrine organically, including positive doctrine (what works), 
negative doctrine (what doesn't work), and neutral doctrine (contextual guidance).

Key Concepts:
- Positive Doctrine: Patterns and strategies that consistently work
- Negative Doctrine: Patterns and strategies that consistently fail
- Neutral Doctrine: Contextual guidance and conditional strategies
- Organic Learning: Natural integration of doctrine into agent behavior
- Strategic Evolution: Doctrine evolves based on new evidence and insights
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from collections import defaultdict

from src.utils.supabase_manager import SupabaseManager


class DoctrineIntegration:
    """
    Handles organic doctrine integration for raw data intelligence
    
    Enables agents to:
    - Query relevant doctrine for pattern types
    - Contribute pattern evidence to doctrine
    - Check doctrine contraindications
    - Learn from strategic doctrine organically
    - Contribute to doctrine evolution
    """
    
    def __init__(self, supabase_manager: SupabaseManager):
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(__name__)
        
        # Doctrine integration parameters
        self.doctrine_relevance_threshold = 0.6  # Minimum relevance for doctrine application
        self.evidence_contribution_threshold = 0.7  # Minimum confidence for doctrine contribution
        self.contraindication_strength_threshold = 0.8  # Threshold for strong contraindications
        self.doctrine_evolution_threshold = 0.9  # Threshold for doctrine evolution
        
        # Doctrine types
        self.doctrine_types = [
            'positive',  # What works consistently
            'negative',  # What doesn't work consistently
            'neutral'    # Contextual guidance
        ]
        
        # Doctrine categories
        self.doctrine_categories = [
            'pattern_recognition',
            'risk_management',
            'entry_strategies',
            'exit_strategies',
            'position_sizing',
            'market_conditions',
            'cross_asset_correlation',
            'temporal_patterns',
            'volatility_management',
            'liquidity_considerations'
        ]
        
        # Doctrine learning tracking
        self.doctrine_queries = []
        self.doctrine_contributions = []
        self.contraindication_checks = []
        self.doctrine_evolution_events = []
    
    async def query_relevant_doctrine(self, pattern_type: str) -> Dict[str, Any]:
        """
        Query relevant doctrine for pattern type organically
        
        Args:
            pattern_type: Type of pattern to find doctrine for
            
        Returns:
            Relevant doctrine with applicability guidance
        """
        try:
            self.logger.info(f"Querying relevant doctrine for pattern type: {pattern_type}")
            
            # 1. Search doctrine strands
            doctrine_strands = await self._search_doctrine_strands(pattern_type)
            
            # 2. Find applicable patterns
            applicable_doctrine = await self._find_applicable_patterns(doctrine_strands, pattern_type)
            
            # 3. Check contraindications
            contraindications = await self._check_contraindications(applicable_doctrine, pattern_type)
            
            # 4. Return doctrine guidance naturally
            doctrine_guidance = {
                'pattern_type': pattern_type,
                'positive_doctrine': applicable_doctrine.get('positive', []),
                'negative_doctrine': applicable_doctrine.get('negative', []),
                'neutral_doctrine': applicable_doctrine.get('neutral', []),
                'contraindications': contraindications,
                'applicability_score': await self._calculate_applicability_score(applicable_doctrine, pattern_type),
                'doctrine_confidence': await self._calculate_doctrine_confidence(applicable_doctrine),
                'query_timestamp': datetime.now(timezone.utc).isoformat(),
                'recommendations': await self._generate_doctrine_recommendations(applicable_doctrine, contraindications)
            }
            
            # 5. Track doctrine query
            await self._track_doctrine_query(doctrine_guidance, pattern_type)
            
            self.logger.info(f"Found {len(applicable_doctrine.get('positive', []))} positive, {len(applicable_doctrine.get('negative', []))} negative, {len(applicable_doctrine.get('neutral', []))} neutral doctrine entries")
            return doctrine_guidance
            
        except Exception as e:
            self.logger.error(f"Doctrine query failed: {e}")
            return {'error': str(e), 'pattern_type': pattern_type}
    
    async def contribute_to_doctrine(self, pattern_evidence: Dict[str, Any]) -> str:
        """
        Contribute pattern evidence to doctrine for organic learning
        
        Args:
            pattern_evidence: Pattern evidence to contribute to doctrine
            
        Returns:
            Doctrine contribution strand ID
        """
        try:
            self.logger.info("Contributing pattern evidence to doctrine")
            
            # 1. Analyze pattern persistence
            persistence_analysis = await self._analyze_pattern_persistence(pattern_evidence)
            
            # 2. Assess pattern generality
            generality_analysis = await self._assess_pattern_generality(pattern_evidence)
            
            # 3. Provide mechanism insights
            mechanism_insights = await self._provide_mechanism_insights(pattern_evidence)
            
            # 4. Determine doctrine contribution type
            contribution_type = await self._determine_contribution_type(persistence_analysis, generality_analysis, pattern_evidence)
            
            # 5. Create doctrine contribution strand
            doctrine_contribution = {
                'contribution_id': self._generate_contribution_id(pattern_evidence),
                'contribution_type': contribution_type,
                'pattern_evidence': pattern_evidence,
                'persistence_analysis': persistence_analysis,
                'generality_analysis': generality_analysis,
                'mechanism_insights': mechanism_insights,
                'doctrine_category': await self._classify_doctrine_category(pattern_evidence),
                'contribution_confidence': pattern_evidence.get('confidence', 0.0),
                'contribution_timestamp': datetime.now(timezone.utc).isoformat(),
                'contributor_agent': pattern_evidence.get('agent', 'unknown'),
                'strategic_significance': await self._calculate_strategic_significance(pattern_evidence)
            }
            
            # 6. Publish doctrine contribution strand
            contribution_strand_id = await self._publish_doctrine_contribution(doctrine_contribution)
            
            # 7. Track doctrine contribution
            await self._track_doctrine_contribution(doctrine_contribution)
            
            if contribution_strand_id:
                self.logger.info(f"Contributed to doctrine: {contribution_strand_id}")
                self.logger.info(f"Contribution type: {contribution_type}")
                self.logger.info(f"Doctrine category: {doctrine_contribution['doctrine_category']}")
            
            return contribution_strand_id
            
        except Exception as e:
            self.logger.error(f"Doctrine contribution failed: {e}")
            return None
    
    async def check_doctrine_contraindications(self, proposed_experiment: Dict[str, Any]) -> bool:
        """
        Check if proposed experiment is contraindicated organically
        
        Args:
            proposed_experiment: Proposed experiment to check for contraindications
            
        Returns:
            True if contraindicated, False if safe to proceed
        """
        try:
            self.logger.info("Checking doctrine contraindications for proposed experiment")
            
            # 1. Query negative doctrine
            negative_doctrine = await self._query_negative_doctrine(proposed_experiment)
            
            # 2. Check for similar failed experiments
            failed_experiments = await self._check_similar_failed_experiments(proposed_experiment)
            
            # 3. Assess contraindication strength
            contraindication_strength = await self._assess_contraindication_strength(negative_doctrine, failed_experiments)
            
            # 4. Return recommendation naturally
            is_contraindicated = contraindication_strength >= self.contraindication_strength_threshold
            
            contraindication_result = {
                'is_contraindicated': is_contraindicated,
                'contraindication_strength': contraindication_strength,
                'negative_doctrine_matches': len(negative_doctrine),
                'failed_experiment_matches': len(failed_experiments),
                'recommendation': 'contraindicated' if is_contraindicated else 'proceed_with_caution' if contraindication_strength > 0.5 else 'safe_to_proceed',
                'reasoning': await self._generate_contraindication_reasoning(negative_doctrine, failed_experiments, contraindication_strength),
                'check_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # 5. Track contraindication check
            await self._track_contraindication_check(contraindication_result, proposed_experiment)
            
            self.logger.info(f"Contraindication check result: {contraindication_result['recommendation']} (strength: {contraindication_strength:.2f})")
            return is_contraindicated
            
        except Exception as e:
            self.logger.error(f"Contraindication check failed: {e}")
            return False  # Default to safe if check fails
    
    async def _search_doctrine_strands(self, pattern_type: str) -> List[Dict[str, Any]]:
        """Search doctrine strands for pattern type"""
        try:
            # Mock implementation - in real system, this would query the doctrine database
            doctrine_strands = [
                {
                    'doctrine_id': f'positive_doctrine_{pattern_type}_1',
                    'doctrine_type': 'positive',
                    'pattern_type': pattern_type,
                    'doctrine_text': f'High confidence {pattern_type} patterns consistently lead to profitable outcomes',
                    'evidence_count': 25,
                    'success_rate': 0.85,
                    'confidence': 0.9,
                    'category': 'pattern_recognition',
                    'last_updated': datetime.now(timezone.utc).isoformat()
                },
                {
                    'doctrine_id': f'negative_doctrine_{pattern_type}_1',
                    'doctrine_type': 'negative',
                    'pattern_type': pattern_type,
                    'doctrine_text': f'Low confidence {pattern_type} patterns in high volatility conditions consistently fail',
                    'evidence_count': 15,
                    'failure_rate': 0.8,
                    'confidence': 0.85,
                    'category': 'risk_management',
                    'last_updated': datetime.now(timezone.utc).isoformat()
                },
                {
                    'doctrine_id': f'neutral_doctrine_{pattern_type}_1',
                    'doctrine_type': 'neutral',
                    'pattern_type': pattern_type,
                    'doctrine_text': f'{pattern_type} patterns require additional confirmation in trending markets',
                    'evidence_count': 20,
                    'applicability': 0.7,
                    'confidence': 0.75,
                    'category': 'market_conditions',
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }
            ]
            
            return doctrine_strands
            
        except Exception as e:
            self.logger.error(f"Doctrine strand search failed: {e}")
            return []
    
    async def _find_applicable_patterns(self, doctrine_strands: List[Dict[str, Any]], pattern_type: str) -> Dict[str, List[Dict[str, Any]]]:
        """Find applicable doctrine patterns"""
        try:
            applicable_doctrine = {
                'positive': [],
                'negative': [],
                'neutral': []
            }
            
            for strand in doctrine_strands:
                doctrine_type = strand.get('doctrine_type', 'neutral')
                confidence = strand.get('confidence', 0.0)
                
                # Only include high-confidence doctrine
                if confidence >= self.doctrine_relevance_threshold:
                    applicable_doctrine[doctrine_type].append(strand)
            
            return applicable_doctrine
            
        except Exception as e:
            self.logger.error(f"Applicable pattern finding failed: {e}")
            return {'positive': [], 'negative': [], 'neutral': []}
    
    async def _check_contraindications(self, applicable_doctrine: Dict[str, List[Dict[str, Any]]], pattern_type: str) -> List[Dict[str, Any]]:
        """Check for contraindications in applicable doctrine"""
        try:
            contraindications = []
            
            # Check negative doctrine for contraindications
            negative_doctrine = applicable_doctrine.get('negative', [])
            for doctrine in negative_doctrine:
                contraindication = {
                    'contraindication_type': 'negative_doctrine',
                    'doctrine_id': doctrine.get('doctrine_id'),
                    'doctrine_text': doctrine.get('doctrine_text'),
                    'failure_rate': doctrine.get('failure_rate', 0.0),
                    'confidence': doctrine.get('confidence', 0.0),
                    'severity': 'high' if doctrine.get('failure_rate', 0.0) > 0.8 else 'medium'
                }
                contraindications.append(contraindication)
            
            return contraindications
            
        except Exception as e:
            self.logger.error(f"Contraindication check failed: {e}")
            return []
    
    async def _calculate_applicability_score(self, applicable_doctrine: Dict[str, List[Dict[str, Any]]], pattern_type: str) -> float:
        """Calculate applicability score for doctrine"""
        try:
            applicability_score = 0.0
            
            # Positive doctrine contributes positively
            positive_doctrine = applicable_doctrine.get('positive', [])
            for doctrine in positive_doctrine:
                success_rate = doctrine.get('success_rate', 0.0)
                confidence = doctrine.get('confidence', 0.0)
                applicability_score += success_rate * confidence * 0.4
            
            # Negative doctrine contributes negatively
            negative_doctrine = applicable_doctrine.get('negative', [])
            for doctrine in negative_doctrine:
                failure_rate = doctrine.get('failure_rate', 0.0)
                confidence = doctrine.get('confidence', 0.0)
                applicability_score -= failure_rate * confidence * 0.3
            
            # Neutral doctrine provides context
            neutral_doctrine = applicable_doctrine.get('neutral', [])
            for doctrine in neutral_doctrine:
                applicability = doctrine.get('applicability', 0.0)
                confidence = doctrine.get('confidence', 0.0)
                applicability_score += applicability * confidence * 0.1
            
            return max(0.0, min(1.0, applicability_score))
            
        except Exception as e:
            self.logger.error(f"Applicability score calculation failed: {e}")
            return 0.0
    
    async def _calculate_doctrine_confidence(self, applicable_doctrine: Dict[str, List[Dict[str, Any]]]) -> float:
        """Calculate overall doctrine confidence"""
        try:
            all_doctrine = []
            for doctrine_type, doctrine_list in applicable_doctrine.items():
                all_doctrine.extend(doctrine_list)
            
            if not all_doctrine:
                return 0.0
            
            # Calculate weighted average confidence
            total_confidence = sum(doctrine.get('confidence', 0.0) for doctrine in all_doctrine)
            return total_confidence / len(all_doctrine)
            
        except Exception as e:
            self.logger.error(f"Doctrine confidence calculation failed: {e}")
            return 0.0
    
    async def _generate_doctrine_recommendations(self, applicable_doctrine: Dict[str, List[Dict[str, Any]]], contraindications: List[Dict[str, Any]]) -> List[str]:
        """Generate doctrine recommendations"""
        try:
            recommendations = []
            
            # Positive doctrine recommendations
            positive_doctrine = applicable_doctrine.get('positive', [])
            for doctrine in positive_doctrine:
                recommendations.append(f"Apply: {doctrine.get('doctrine_text', '')}")
            
            # Negative doctrine recommendations
            negative_doctrine = applicable_doctrine.get('negative', [])
            for doctrine in negative_doctrine:
                recommendations.append(f"Avoid: {doctrine.get('doctrine_text', '')}")
            
            # Neutral doctrine recommendations
            neutral_doctrine = applicable_doctrine.get('neutral', [])
            for doctrine in neutral_doctrine:
                recommendations.append(f"Consider: {doctrine.get('doctrine_text', '')}")
            
            # Contraindication recommendations
            for contraindication in contraindications:
                if contraindication.get('severity') == 'high':
                    recommendations.append(f"STRONG CONTRAINDICATION: {contraindication.get('doctrine_text', '')}")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Doctrine recommendation generation failed: {e}")
            return []
    
    async def _analyze_pattern_persistence(self, pattern_evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze pattern persistence for doctrine contribution"""
        try:
            persistence_analysis = {
                'persistence_score': 0.0,
                'temporal_consistency': 0.0,
                'cross_condition_consistency': 0.0,
                'evidence_strength': 0.0
            }
            
            # Analyze temporal consistency
            timestamp = pattern_evidence.get('timestamp', datetime.now(timezone.utc).isoformat())
            # Mock analysis - in real system, this would analyze historical data
            persistence_analysis['temporal_consistency'] = np.random.uniform(0.6, 0.9)
            
            # Analyze cross-condition consistency
            confidence = pattern_evidence.get('confidence', 0.0)
            persistence_analysis['cross_condition_consistency'] = confidence * 0.8
            
            # Calculate evidence strength
            data_points = pattern_evidence.get('data_points', 0)
            persistence_analysis['evidence_strength'] = min(1.0, data_points / 100.0)
            
            # Calculate overall persistence score
            persistence_analysis['persistence_score'] = (
                persistence_analysis['temporal_consistency'] * 0.4 +
                persistence_analysis['cross_condition_consistency'] * 0.4 +
                persistence_analysis['evidence_strength'] * 0.2
            )
            
            return persistence_analysis
            
        except Exception as e:
            self.logger.error(f"Pattern persistence analysis failed: {e}")
            return {'persistence_score': 0.0}
    
    async def _assess_pattern_generality(self, pattern_evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Assess pattern generality for doctrine contribution"""
        try:
            generality_analysis = {
                'generality_score': 0.0,
                'cross_asset_applicability': 0.0,
                'market_condition_robustness': 0.0,
                'timeframe_scalability': 0.0
            }
            
            # Analyze cross-asset applicability
            symbols = pattern_evidence.get('symbols', [])
            generality_analysis['cross_asset_applicability'] = min(1.0, len(symbols) / 5.0)
            
            # Analyze market condition robustness
            confidence = pattern_evidence.get('confidence', 0.0)
            generality_analysis['market_condition_robustness'] = confidence * 0.7
            
            # Analyze timeframe scalability
            timeframe = pattern_evidence.get('timeframe', '1m')
            if timeframe in ['1m', '5m']:
                generality_analysis['timeframe_scalability'] = 0.8
            elif timeframe in ['15m', '1h']:
                generality_analysis['timeframe_scalability'] = 0.9
            else:
                generality_analysis['timeframe_scalability'] = 0.6
            
            # Calculate overall generality score
            generality_analysis['generality_score'] = (
                generality_analysis['cross_asset_applicability'] * 0.3 +
                generality_analysis['market_condition_robustness'] * 0.4 +
                generality_analysis['timeframe_scalability'] * 0.3
            )
            
            return generality_analysis
            
        except Exception as e:
            self.logger.error(f"Pattern generality assessment failed: {e}")
            return {'generality_score': 0.0}
    
    async def _provide_mechanism_insights(self, pattern_evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Provide mechanism insights for doctrine contribution"""
        try:
            mechanism_insights = []
            
            pattern_type = pattern_evidence.get('type', 'unknown')
            confidence = pattern_evidence.get('confidence', 0.0)
            
            # Generate mechanism insights based on pattern type
            if 'volume' in pattern_type.lower():
                mechanism_insights.append({
                    'mechanism_type': 'volume_dynamics',
                    'insight': 'Volume patterns reflect institutional flow and retail sentiment',
                    'confidence': confidence,
                    'applicability': 'high'
                })
            elif 'divergence' in pattern_type.lower():
                mechanism_insights.append({
                    'mechanism_type': 'momentum_exhaustion',
                    'insight': 'Divergence patterns indicate momentum exhaustion and potential reversal',
                    'confidence': confidence,
                    'applicability': 'high'
                })
            elif 'microstructure' in pattern_type.lower():
                mechanism_insights.append({
                    'mechanism_type': 'order_flow',
                    'insight': 'Microstructure patterns reveal order flow dynamics and market maker behavior',
                    'confidence': confidence,
                    'applicability': 'medium'
                })
            else:
                mechanism_insights.append({
                    'mechanism_type': 'general_pattern',
                    'insight': 'General market pattern with multiple causal factors',
                    'confidence': confidence,
                    'applicability': 'medium'
                })
            
            return mechanism_insights
            
        except Exception as e:
            self.logger.error(f"Mechanism insight provision failed: {e}")
            return []
    
    async def _determine_contribution_type(self, persistence_analysis: Dict[str, Any], generality_analysis: Dict[str, Any], pattern_evidence: Dict[str, Any]) -> str:
        """Determine doctrine contribution type"""
        try:
            persistence_score = persistence_analysis.get('persistence_score', 0.0)
            generality_score = generality_analysis.get('generality_score', 0.0)
            confidence = pattern_evidence.get('confidence', 0.0)
            
            # Determine contribution type based on scores
            if persistence_score >= 0.8 and generality_score >= 0.8 and confidence >= 0.8:
                return 'positive_doctrine'
            elif persistence_score <= 0.3 or generality_score <= 0.3 or confidence <= 0.3:
                return 'negative_doctrine'
            else:
                return 'neutral_doctrine'
                
        except Exception as e:
            self.logger.error(f"Contribution type determination failed: {e}")
            return 'neutral_doctrine'
    
    async def _classify_doctrine_category(self, pattern_evidence: Dict[str, Any]) -> str:
        """Classify doctrine category"""
        try:
            pattern_type = pattern_evidence.get('type', '').lower()
            
            if 'volume' in pattern_type:
                return 'pattern_recognition'
            elif 'divergence' in pattern_type:
                return 'risk_management'
            elif 'microstructure' in pattern_type:
                return 'market_conditions'
            elif 'time' in pattern_type:
                return 'temporal_patterns'
            elif 'cross' in pattern_type:
                return 'cross_asset_correlation'
            else:
                return 'pattern_recognition'
                
        except Exception as e:
            self.logger.error(f"Doctrine category classification failed: {e}")
            return 'pattern_recognition'
    
    async def _calculate_strategic_significance(self, pattern_evidence: Dict[str, Any]) -> float:
        """Calculate strategic significance of pattern evidence"""
        try:
            strategic_significance = 0.0
            
            # Base significance from confidence
            confidence = pattern_evidence.get('confidence', 0.0)
            strategic_significance += confidence * 0.4
            
            # Significance from data points
            data_points = pattern_evidence.get('data_points', 0)
            data_significance = min(0.3, data_points / 200.0)
            strategic_significance += data_significance
            
            # Significance from pattern type
            pattern_type = pattern_evidence.get('type', '')
            if 'volume' in pattern_type.lower():
                strategic_significance += 0.2
            elif 'divergence' in pattern_type.lower():
                strategic_significance += 0.15
            else:
                strategic_significance += 0.1
            
            return min(1.0, strategic_significance)
            
        except Exception as e:
            self.logger.error(f"Strategic significance calculation failed: {e}")
            return 0.0
    
    async def _query_negative_doctrine(self, proposed_experiment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query negative doctrine for contraindications"""
        try:
            # Mock implementation - in real system, this would query negative doctrine
            negative_doctrine = [
                {
                    'doctrine_id': 'negative_doctrine_1',
                    'doctrine_text': 'High volatility conditions consistently lead to pattern failure',
                    'failure_rate': 0.85,
                    'confidence': 0.9,
                    'category': 'risk_management'
                }
            ]
            
            return negative_doctrine
            
        except Exception as e:
            self.logger.error(f"Negative doctrine query failed: {e}")
            return []
    
    async def _check_similar_failed_experiments(self, proposed_experiment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for similar failed experiments"""
        try:
            # Mock implementation - in real system, this would query failed experiments
            failed_experiments = [
                {
                    'experiment_id': 'failed_experiment_1',
                    'experiment_type': proposed_experiment.get('type', 'unknown'),
                    'failure_reason': 'High volatility conditions',
                    'failure_rate': 0.8,
                    'confidence': 0.85
                }
            ]
            
            return failed_experiments
            
        except Exception as e:
            self.logger.error(f"Failed experiment check failed: {e}")
            return []
    
    async def _assess_contraindication_strength(self, negative_doctrine: List[Dict[str, Any]], failed_experiments: List[Dict[str, Any]]) -> float:
        """Assess contraindication strength"""
        try:
            contraindication_strength = 0.0
            
            # Negative doctrine contribution
            for doctrine in negative_doctrine:
                failure_rate = doctrine.get('failure_rate', 0.0)
                confidence = doctrine.get('confidence', 0.0)
                contraindication_strength += failure_rate * confidence * 0.5
            
            # Failed experiments contribution
            for experiment in failed_experiments:
                failure_rate = experiment.get('failure_rate', 0.0)
                confidence = experiment.get('confidence', 0.0)
                contraindication_strength += failure_rate * confidence * 0.5
            
            return min(1.0, contraindication_strength)
            
        except Exception as e:
            self.logger.error(f"Contraindication strength assessment failed: {e}")
            return 0.0
    
    async def _generate_contraindication_reasoning(self, negative_doctrine: List[Dict[str, Any]], failed_experiments: List[Dict[str, Any]], contraindication_strength: float) -> str:
        """Generate contraindication reasoning"""
        try:
            reasoning_parts = []
            
            if negative_doctrine:
                reasoning_parts.append(f"Negative doctrine indicates {len(negative_doctrine)} contraindications")
            
            if failed_experiments:
                reasoning_parts.append(f"Similar experiments failed {len(failed_experiments)} times")
            
            reasoning_parts.append(f"Overall contraindication strength: {contraindication_strength:.2f}")
            
            return "; ".join(reasoning_parts)
            
        except Exception as e:
            self.logger.error(f"Contraindication reasoning generation failed: {e}")
            return "Unable to generate reasoning"
    
    def _generate_contribution_id(self, pattern_evidence: Dict[str, Any]) -> str:
        """Generate unique contribution ID"""
        try:
            pattern_type = pattern_evidence.get('type', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return f"doctrine_contribution_{pattern_type}_{timestamp}"
        except Exception as e:
            self.logger.error(f"Contribution ID generation failed: {e}")
            return f"doctrine_contribution_unknown_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def _publish_doctrine_contribution(self, doctrine_contribution: Dict[str, Any]) -> Optional[str]:
        """Publish doctrine contribution to database"""
        try:
            # Mock implementation - in real system, this would publish to AD_strands table
            contribution_id = doctrine_contribution.get('contribution_id', 'unknown')
            strand_id = f"doctrine_contribution_{contribution_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            return strand_id
            
        except Exception as e:
            self.logger.error(f"Doctrine contribution publishing failed: {e}")
            return None
    
    async def _track_doctrine_query(self, doctrine_guidance: Dict[str, Any], pattern_type: str):
        """Track doctrine query for learning"""
        try:
            query_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'pattern_type': pattern_type,
                'applicability_score': doctrine_guidance.get('applicability_score', 0.0),
                'doctrine_confidence': doctrine_guidance.get('doctrine_confidence', 0.0),
                'positive_doctrine_count': len(doctrine_guidance.get('positive_doctrine', [])),
                'negative_doctrine_count': len(doctrine_guidance.get('negative_doctrine', [])),
                'neutral_doctrine_count': len(doctrine_guidance.get('neutral_doctrine', [])),
                'contraindications_count': len(doctrine_guidance.get('contraindications', []))
            }
            
            self.doctrine_queries.append(query_entry)
            
            # Keep only recent queries
            if len(self.doctrine_queries) > 100:
                self.doctrine_queries = self.doctrine_queries[-100:]
            
        except Exception as e:
            self.logger.error(f"Doctrine query tracking failed: {e}")
    
    async def _track_doctrine_contribution(self, doctrine_contribution: Dict[str, Any]):
        """Track doctrine contribution for learning"""
        try:
            contribution_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'contribution_id': doctrine_contribution.get('contribution_id'),
                'contribution_type': doctrine_contribution.get('contribution_type'),
                'doctrine_category': doctrine_contribution.get('doctrine_category'),
                'contribution_confidence': doctrine_contribution.get('contribution_confidence', 0.0),
                'strategic_significance': doctrine_contribution.get('strategic_significance', 0.0)
            }
            
            self.doctrine_contributions.append(contribution_entry)
            
            # Keep only recent contributions
            if len(self.doctrine_contributions) > 100:
                self.doctrine_contributions = self.doctrine_contributions[-100:]
            
        except Exception as e:
            self.logger.error(f"Doctrine contribution tracking failed: {e}")
    
    async def _track_contraindication_check(self, contraindication_result: Dict[str, Any], proposed_experiment: Dict[str, Any]):
        """Track contraindication check for learning"""
        try:
            check_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'experiment_type': proposed_experiment.get('type', 'unknown'),
                'is_contraindicated': contraindication_result.get('is_contraindicated', False),
                'contraindication_strength': contraindication_result.get('contraindication_strength', 0.0),
                'recommendation': contraindication_result.get('recommendation', 'unknown')
            }
            
            self.contraindication_checks.append(check_entry)
            
            # Keep only recent checks
            if len(self.contraindication_checks) > 100:
                self.contraindication_checks = self.contraindication_checks[-100:]
            
        except Exception as e:
            self.logger.error(f"Contraindication check tracking failed: {e}")
    
    def get_doctrine_integration_summary(self) -> Dict[str, Any]:
        """Get summary of doctrine integration"""
        try:
            return {
                'doctrine_queries': len(self.doctrine_queries),
                'doctrine_contributions': len(self.doctrine_contributions),
                'contraindication_checks': len(self.contraindication_checks),
                'recent_queries': self.doctrine_queries[-5:] if self.doctrine_queries else [],
                'recent_contributions': self.doctrine_contributions[-5:] if self.doctrine_contributions else [],
                'recent_checks': self.contraindication_checks[-5:] if self.contraindication_checks else [],
                'integration_effectiveness': {
                    'avg_applicability_score': np.mean([q['applicability_score'] for q in self.doctrine_queries]) if self.doctrine_queries else 0.0,
                    'avg_contribution_confidence': np.mean([c['contribution_confidence'] for c in self.doctrine_contributions]) if self.doctrine_contributions else 0.0,
                    'contraindication_rate': np.mean([c['is_contraindicated'] for c in self.contraindication_checks]) if self.contraindication_checks else 0.0
                }
            }
            
        except Exception as e:
            self.logger.error(f"Doctrine integration summary failed: {e}")
            return {'error': str(e)}
