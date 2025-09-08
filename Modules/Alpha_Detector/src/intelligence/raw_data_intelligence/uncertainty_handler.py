"""
Uncertainty Handler for Raw Data Intelligence

Handles uncertainty-driven curiosity for organic exploration. Embraces uncertainty as the 
default state and valuable exploration driver, not something to be avoided or hidden.

Key Philosophy: Uncertainty is the default state - being unsure is valuable information 
that drives exploration. Low confidence results are not failures, they are curiosity opportunities.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np

from src.utils.supabase_manager import SupabaseManager


class UncertaintyHandler:
    """
    Handles uncertainty-driven curiosity for organic exploration
    
    Key Principles:
    - Uncertainty is the DEFAULT state, not exception
    - Low confidence results are opportunities, not failures
    - Being unsure is valuable information that drives exploration
    - Uncertainty resolution accelerates learning and growth
    """
    
    def __init__(self, supabase_manager: SupabaseManager):
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(__name__)
        
        # Uncertainty detection parameters
        self.confidence_threshold = 0.7  # Below this = uncertainty opportunity
        self.data_sufficiency_threshold = 50  # Below this = data insufficiency uncertainty
        self.pattern_clarity_threshold = 0.6  # Below this = pattern clarity uncertainty
        
        # Uncertainty types for exploration
        self.uncertainty_types = [
            "data_insufficiency",
            "pattern_clarity", 
            "confidence_low",
            "contradictory_signals",
            "novel_pattern",
            "threshold_boundary",
            "cross_validation_failure"
        ]
    
    async def detect_uncertainty(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect uncertainty that drives organic exploration - uncertainty is valuable!
        
        Args:
            analysis_result: Analysis results from raw data intelligence agent
            
        Returns:
            Dictionary with uncertainty detection results
        """
        try:
            uncertainty_analysis = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'uncertainty_detected': False,
                'uncertainty_types': [],
                'uncertainty_details': {},
                'exploration_opportunities': [],
                'confidence_score': 0.0,
                'uncertainty_priority': 'low'
            }
            
            # 1. Assess pattern clarity (uncertainty is good if identified)
            pattern_clarity = self._assess_pattern_clarity(analysis_result)
            if pattern_clarity['uncertainty_detected']:
                uncertainty_analysis['uncertainty_types'].append('pattern_clarity')
                uncertainty_analysis['uncertainty_details']['pattern_clarity'] = pattern_clarity
                uncertainty_analysis['exploration_opportunities'].extend(pattern_clarity['exploration_opportunities'])
            
            # 2. Evaluate data sufficiency (insufficient data = exploration opportunity)
            data_sufficiency = self._evaluate_data_sufficiency(analysis_result)
            if data_sufficiency['uncertainty_detected']:
                uncertainty_analysis['uncertainty_types'].append('data_insufficiency')
                uncertainty_analysis['uncertainty_details']['data_sufficiency'] = data_sufficiency
                uncertainty_analysis['exploration_opportunities'].extend(data_sufficiency['exploration_opportunities'])
            
            # 3. Calculate confidence levels (low confidence = curiosity driver)
            confidence_analysis = self._analyze_confidence_levels(analysis_result)
            if confidence_analysis['uncertainty_detected']:
                uncertainty_analysis['uncertainty_types'].append('confidence_low')
                uncertainty_analysis['uncertainty_details']['confidence_analysis'] = confidence_analysis
                uncertainty_analysis['exploration_opportunities'].extend(confidence_analysis['exploration_opportunities'])
            
            # 4. Identify uncertainty types that drive exploration
            additional_uncertainties = self._identify_additional_uncertainties(analysis_result)
            uncertainty_analysis['uncertainty_types'].extend(additional_uncertainties['types'])
            uncertainty_analysis['uncertainty_details'].update(additional_uncertainties['details'])
            uncertainty_analysis['exploration_opportunities'].extend(additional_uncertainties['exploration_opportunities'])
            
            # 5. Treat uncertainty as DEFAULT state, not exception
            uncertainty_analysis['uncertainty_detected'] = len(uncertainty_analysis['uncertainty_types']) > 0
            uncertainty_analysis['confidence_score'] = self._calculate_uncertainty_confidence(uncertainty_analysis)
            uncertainty_analysis['uncertainty_priority'] = self._determine_uncertainty_priority(uncertainty_analysis)
            
            return uncertainty_analysis
            
        except Exception as e:
            self.logger.error(f"Uncertainty detection failed: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'uncertainty_detected': True,  # Even errors are uncertainty opportunities!
                'uncertainty_types': ['system_error'],
                'exploration_opportunities': ['investigate_system_error']
            }
    
    async def publish_uncertainty_strand(self, uncertainty_data: Dict[str, Any]) -> str:
        """
        Publish uncertainty as specialized strand for organic resolution
        
        Args:
            uncertainty_data: Uncertainty analysis results
            
        Returns:
            Strand ID of published uncertainty strand
        """
        try:
            # Create uncertainty strand with positive framing
            strand_content = {
                'uncertainty_types': uncertainty_data.get('uncertainty_types', []),
                'uncertainty_details': uncertainty_data.get('uncertainty_details', {}),
                'exploration_opportunities': uncertainty_data.get('exploration_opportunities', []),
                'confidence_score': uncertainty_data.get('confidence_score', 0.0),
                'uncertainty_priority': uncertainty_data.get('uncertainty_priority', 'low'),
                'timestamp': uncertainty_data.get('timestamp'),
                'agent': 'raw_data_intelligence',
                'uncertainty_positive_framing': True,
                'exploration_driver': True
            }
            
            # Set uncertainty type and exploration priority
            primary_uncertainty_type = uncertainty_data.get('uncertainty_types', ['general'])[0]
            
            # Tag for natural clustering and resolution
            tags = f"uncertainty:raw_data:{primary_uncertainty_type}:{uncertainty_data.get('uncertainty_priority', 'low')}:exploration_opportunity"
            
            # Include resolution suggestions and exploration directions
            resolution_suggestions = self._generate_resolution_suggestions(uncertainty_data)
            strand_content['resolution_suggestions'] = resolution_suggestions
            strand_content['exploration_directions'] = self._generate_exploration_directions(uncertainty_data)
            
            # Emphasize that uncertainty is valuable information
            strand_content['uncertainty_value'] = {
                'learning_opportunity': True,
                'exploration_driver': True,
                'growth_catalyst': True,
                'intelligence_enhancer': True
            }
            
            # Publish to AD_strands table
            strand_id = await self._publish_to_strands(strand_content, tags)
            
            if strand_id:
                self.logger.info(f"Published uncertainty strand (exploration opportunity): {strand_id}")
                self.logger.info(f"Uncertainty types: {uncertainty_data.get('uncertainty_types', [])}")
                self.logger.info(f"Exploration opportunities: {len(uncertainty_data.get('exploration_opportunities', []))}")
            
            return strand_id
            
        except Exception as e:
            self.logger.error(f"Failed to publish uncertainty strand: {e}")
            return None
    
    async def handle_uncertainty_resolution(self, uncertainty_id: str, resolution_data: Dict[str, Any]):
        """
        Handle uncertainty resolution through organic exploration
        
        Args:
            uncertainty_id: ID of uncertainty strand to resolve
            resolution_data: Data about resolution attempt
        """
        try:
            # Update uncertainty strand with resolution progress
            update_data = {
                'resolution_attempted': True,
                'resolution_timestamp': datetime.now(timezone.utc).isoformat(),
                'resolution_data': resolution_data,
                'resolution_progress': resolution_data.get('progress', 0.0),
                'learning_gained': resolution_data.get('learning_gained', {}),
                'new_insights': resolution_data.get('new_insights', [])
            }
            
            # Execute exploration actions based on uncertainty
            exploration_results = await self._execute_exploration_actions(uncertainty_id, resolution_data)
            update_data['exploration_results'] = exploration_results
            
            # Track resolution progress and learning
            learning_summary = self._summarize_learning_gained(resolution_data, exploration_results)
            update_data['learning_summary'] = learning_summary
            
            # Report resolution results and new insights gained
            resolution_strand = await self._publish_resolution_results(uncertainty_id, update_data)
            
            # Celebrate uncertainty as learning opportunity
            if resolution_strand:
                self.logger.info(f"Uncertainty resolution completed: {uncertainty_id}")
                self.logger.info(f"Learning gained: {learning_summary.get('key_insights', [])}")
                self.logger.info(f"Exploration results: {len(exploration_results.get('new_discoveries', []))}")
            
            return resolution_strand
            
        except Exception as e:
            self.logger.error(f"Failed to handle uncertainty resolution: {e}")
            return None
    
    def _assess_pattern_clarity(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Assess pattern clarity and identify clarity-related uncertainties"""
        try:
            clarity_analysis = {
                'uncertainty_detected': False,
                'clarity_score': 0.0,
                'clarity_issues': [],
                'exploration_opportunities': []
            }
            
            # Check pattern confidence levels
            confidence = analysis_result.get('confidence', 0.0)
            if confidence < self.pattern_clarity_threshold:
                clarity_analysis['uncertainty_detected'] = True
                clarity_analysis['clarity_issues'].append('low_pattern_confidence')
                clarity_analysis['exploration_opportunities'].append('investigate_pattern_clarity')
            
            # Check for contradictory signals
            patterns = analysis_result.get('patterns', [])
            if len(patterns) > 1:
                # Look for contradictory patterns
                pattern_types = [p.get('type', '') for p in patterns]
                if len(set(pattern_types)) < len(pattern_types):
                    clarity_analysis['uncertainty_detected'] = True
                    clarity_analysis['clarity_issues'].append('contradictory_patterns')
                    clarity_analysis['exploration_opportunities'].append('resolve_pattern_contradictions')
            
            # Check analysis completeness
            analysis_components = analysis_result.get('analysis_components', {})
            if len(analysis_components) < 3:  # Expect at least 3 analysis components
                clarity_analysis['uncertainty_detected'] = True
                clarity_analysis['clarity_issues'].append('incomplete_analysis')
                clarity_analysis['exploration_opportunities'].append('expand_analysis_scope')
            
            clarity_analysis['clarity_score'] = confidence
            return clarity_analysis
            
        except Exception as e:
            self.logger.error(f"Pattern clarity assessment failed: {e}")
            return {'uncertainty_detected': True, 'clarity_issues': ['assessment_error'], 'exploration_opportunities': ['investigate_assessment_error']}
    
    def _evaluate_data_sufficiency(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate data sufficiency and identify insufficiency-related uncertainties"""
        try:
            sufficiency_analysis = {
                'uncertainty_detected': False,
                'data_points': analysis_result.get('data_points', 0),
                'sufficiency_issues': [],
                'exploration_opportunities': []
            }
            
            data_points = sufficiency_analysis['data_points']
            
            if data_points < self.data_sufficiency_threshold:
                sufficiency_analysis['uncertainty_detected'] = True
                sufficiency_analysis['sufficiency_issues'].append('insufficient_data_points')
                sufficiency_analysis['exploration_opportunities'].append('collect_more_data')
            
            # Check for data quality issues
            if 'error' in analysis_result:
                sufficiency_analysis['uncertainty_detected'] = True
                sufficiency_analysis['sufficiency_issues'].append('data_quality_error')
                sufficiency_analysis['exploration_opportunities'].append('investigate_data_quality')
            
            # Check for missing analysis components
            expected_components = ['volume', 'divergences', 'microstructure', 'time_based', 'cross_asset']
            analysis_components = analysis_result.get('analysis_components', {})
            missing_components = [comp for comp in expected_components if comp not in analysis_components]
            
            if missing_components:
                sufficiency_analysis['uncertainty_detected'] = True
                sufficiency_analysis['sufficiency_issues'].append('missing_analysis_components')
                sufficiency_analysis['exploration_opportunities'].extend([f'analyze_{comp}' for comp in missing_components])
            
            return sufficiency_analysis
            
        except Exception as e:
            self.logger.error(f"Data sufficiency evaluation failed: {e}")
            return {'uncertainty_detected': True, 'sufficiency_issues': ['evaluation_error'], 'exploration_opportunities': ['investigate_evaluation_error']}
    
    def _analyze_confidence_levels(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze confidence levels and identify confidence-related uncertainties"""
        try:
            confidence_analysis = {
                'uncertainty_detected': False,
                'confidence_score': analysis_result.get('confidence', 0.0),
                'confidence_issues': [],
                'exploration_opportunities': []
            }
            
            confidence = confidence_analysis['confidence_score']
            
            if confidence < self.confidence_threshold:
                confidence_analysis['uncertainty_detected'] = True
                confidence_analysis['confidence_issues'].append('low_confidence')
                confidence_analysis['exploration_opportunities'].append('investigate_low_confidence_causes')
            
            # Check for confidence inconsistencies across components
            analysis_components = analysis_result.get('analysis_components', {})
            component_confidences = []
            
            for component, data in analysis_components.items():
                if isinstance(data, dict) and 'confidence' in data:
                    component_confidences.append(data['confidence'])
            
            if len(component_confidences) > 1:
                confidence_std = np.std(component_confidences)
                if confidence_std > 0.3:  # High variance in confidence
                    confidence_analysis['uncertainty_detected'] = True
                    confidence_analysis['confidence_issues'].append('inconsistent_confidence')
                    confidence_analysis['exploration_opportunities'].append('investigate_confidence_inconsistency')
            
            return confidence_analysis
            
        except Exception as e:
            self.logger.error(f"Confidence level analysis failed: {e}")
            return {'uncertainty_detected': True, 'confidence_issues': ['analysis_error'], 'exploration_opportunities': ['investigate_analysis_error']}
    
    def _identify_additional_uncertainties(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Identify additional uncertainty types that drive exploration"""
        try:
            additional_uncertainties = {
                'types': [],
                'details': {},
                'exploration_opportunities': []
            }
            
            # Check for novel patterns (uncertainty about new patterns)
            patterns = analysis_result.get('patterns', [])
            for pattern in patterns:
                if pattern.get('novelty_score', 0) > 0.7:
                    additional_uncertainties['types'].append('novel_pattern')
                    additional_uncertainties['exploration_opportunities'].append('investigate_novel_pattern')
                    break
            
            # Check for threshold boundary conditions
            significant_patterns = analysis_result.get('significant_patterns', [])
            for pattern in significant_patterns:
                severity = pattern.get('severity', 'low')
                if severity == 'medium':  # On the boundary
                    additional_uncertainties['types'].append('threshold_boundary')
                    additional_uncertainties['exploration_opportunities'].append('investigate_threshold_boundary')
                    break
            
            # Check for cross-validation failures
            if 'cross_validation' in analysis_result:
                cv_results = analysis_result['cross_validation']
                if cv_results.get('failed', False):
                    additional_uncertainties['types'].append('cross_validation_failure')
                    additional_uncertainties['exploration_opportunities'].append('investigate_cross_validation_failure')
            
            return additional_uncertainties
            
        except Exception as e:
            self.logger.error(f"Additional uncertainty identification failed: {e}")
            return {'types': ['identification_error'], 'details': {}, 'exploration_opportunities': ['investigate_identification_error']}
    
    def _calculate_uncertainty_confidence(self, uncertainty_analysis: Dict[str, Any]) -> float:
        """Calculate confidence in uncertainty detection"""
        try:
            uncertainty_types = uncertainty_analysis.get('uncertainty_types', [])
            exploration_opportunities = uncertainty_analysis.get('exploration_opportunities', [])
            
            # Higher confidence if more uncertainty types detected
            type_confidence = min(1.0, len(uncertainty_types) * 0.2)
            
            # Higher confidence if more exploration opportunities identified
            opportunity_confidence = min(1.0, len(exploration_opportunities) * 0.1)
            
            # Base confidence for uncertainty detection
            base_confidence = 0.5
            
            return min(1.0, base_confidence + type_confidence + opportunity_confidence)
            
        except Exception as e:
            self.logger.error(f"Uncertainty confidence calculation failed: {e}")
            return 0.5
    
    def _determine_uncertainty_priority(self, uncertainty_analysis: Dict[str, Any]) -> str:
        """Determine priority level for uncertainty"""
        try:
            uncertainty_types = uncertainty_analysis.get('uncertainty_types', [])
            exploration_opportunities = uncertainty_analysis.get('exploration_opportunities', [])
            
            # High priority if multiple uncertainty types
            if len(uncertainty_types) >= 3:
                return 'high'
            
            # High priority if many exploration opportunities
            if len(exploration_opportunities) >= 5:
                return 'high'
            
            # Medium priority if some uncertainty detected
            if len(uncertainty_types) >= 1:
                return 'medium'
            
            return 'low'
            
        except Exception as e:
            self.logger.error(f"Uncertainty priority determination failed: {e}")
            return 'low'
    
    def _generate_resolution_suggestions(self, uncertainty_data: Dict[str, Any]) -> List[str]:
        """Generate resolution suggestions for uncertainty"""
        try:
            suggestions = []
            uncertainty_types = uncertainty_data.get('uncertainty_types', [])
            
            for uncertainty_type in uncertainty_types:
                if uncertainty_type == 'data_insufficiency':
                    suggestions.append('Collect additional market data')
                    suggestions.append('Expand data collection timeframe')
                elif uncertainty_type == 'pattern_clarity':
                    suggestions.append('Apply additional pattern detection algorithms')
                    suggestions.append('Increase analysis granularity')
                elif uncertainty_type == 'confidence_low':
                    suggestions.append('Investigate confidence calculation methods')
                    suggestions.append('Validate analysis assumptions')
                elif uncertainty_type == 'contradictory_signals':
                    suggestions.append('Resolve signal contradictions')
                    suggestions.append('Apply signal fusion techniques')
                elif uncertainty_type == 'novel_pattern':
                    suggestions.append('Investigate novel pattern characteristics')
                    suggestions.append('Compare with historical patterns')
                elif uncertainty_type == 'threshold_boundary':
                    suggestions.append('Investigate threshold sensitivity')
                    suggestions.append('Test alternative threshold values')
                elif uncertainty_type == 'cross_validation_failure':
                    suggestions.append('Investigate cross-validation methodology')
                    suggestions.append('Apply alternative validation techniques')
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Resolution suggestion generation failed: {e}")
            return ['Investigate uncertainty resolution methods']
    
    def _generate_exploration_directions(self, uncertainty_data: Dict[str, Any]) -> List[str]:
        """Generate exploration directions for uncertainty"""
        try:
            directions = []
            exploration_opportunities = uncertainty_data.get('exploration_opportunities', [])
            
            for opportunity in exploration_opportunities:
                if 'investigate' in opportunity:
                    directions.append(f'Investigation: {opportunity}')
                elif 'collect' in opportunity:
                    directions.append(f'Data Collection: {opportunity}')
                elif 'analyze' in opportunity:
                    directions.append(f'Analysis: {opportunity}')
                elif 'resolve' in opportunity:
                    directions.append(f'Resolution: {opportunity}')
                else:
                    directions.append(f'Exploration: {opportunity}')
            
            return directions
            
        except Exception as e:
            self.logger.error(f"Exploration direction generation failed: {e}")
            return ['General uncertainty exploration']
    
    async def _publish_to_strands(self, content: Dict[str, Any], tags: str) -> Optional[str]:
        """Publish content to AD_strands table"""
        try:
            # This would integrate with the existing strand publishing system
            # For now, return a mock strand ID
            strand_id = f"uncertainty_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(content)) % 10000}"
            
            # In real implementation, this would call:
            # strand_id = await self.supabase_manager.publish_strand(content, tags)
            
            return strand_id
            
        except Exception as e:
            self.logger.error(f"Failed to publish to strands: {e}")
            return None
    
    async def _execute_exploration_actions(self, uncertainty_id: str, resolution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute exploration actions based on uncertainty"""
        try:
            exploration_results = {
                'actions_taken': [],
                'new_discoveries': [],
                'learning_gained': {},
                'exploration_success': False
            }
            
            # Mock exploration actions - in real implementation, these would be actual actions
            exploration_results['actions_taken'] = [
                'investigated_uncertainty_causes',
                'applied_additional_analysis_methods',
                'collected_additional_data'
            ]
            
            exploration_results['new_discoveries'] = [
                'identified_new_pattern_type',
                'discovered_data_quality_issue',
                'found_analysis_improvement_opportunity'
            ]
            
            exploration_results['learning_gained'] = {
                'uncertainty_causes': ['data_insufficiency', 'method_limitation'],
                'improvement_areas': ['data_collection', 'analysis_methods'],
                'new_insights': ['pattern_detection_enhancement', 'confidence_calculation_improvement']
            }
            
            exploration_results['exploration_success'] = True
            
            return exploration_results
            
        except Exception as e:
            self.logger.error(f"Exploration action execution failed: {e}")
            return {'actions_taken': [], 'new_discoveries': [], 'learning_gained': {}, 'exploration_success': False}
    
    def _summarize_learning_gained(self, resolution_data: Dict[str, Any], exploration_results: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize learning gained from uncertainty resolution"""
        try:
            learning_summary = {
                'key_insights': [],
                'improvement_areas': [],
                'new_capabilities': [],
                'uncertainty_resolution_success': False
            }
            
            # Extract key insights
            learning_gained = exploration_results.get('learning_gained', {})
            learning_summary['key_insights'] = learning_gained.get('new_insights', [])
            learning_summary['improvement_areas'] = learning_gained.get('improvement_areas', [])
            learning_summary['new_capabilities'] = learning_gained.get('new_capabilities', [])
            
            # Determine success
            learning_summary['uncertainty_resolution_success'] = exploration_results.get('exploration_success', False)
            
            return learning_summary
            
        except Exception as e:
            self.logger.error(f"Learning summary generation failed: {e}")
            return {'key_insights': [], 'improvement_areas': [], 'new_capabilities': [], 'uncertainty_resolution_success': False}
    
    async def _publish_resolution_results(self, uncertainty_id: str, update_data: Dict[str, Any]) -> Optional[str]:
        """Publish uncertainty resolution results"""
        try:
            resolution_content = {
                'uncertainty_id': uncertainty_id,
                'resolution_data': update_data,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'agent': 'raw_data_intelligence',
                'resolution_type': 'uncertainty_exploration',
                'learning_celebration': True
            }
            
            tags = f"uncertainty_resolution:raw_data:{uncertainty_id}:learning_opportunity"
            
            resolution_strand_id = await self._publish_to_strands(resolution_content, tags)
            
            return resolution_strand_id
            
        except Exception as e:
            self.logger.error(f"Failed to publish resolution results: {e}")
            return None
