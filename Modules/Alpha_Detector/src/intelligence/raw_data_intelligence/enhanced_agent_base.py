"""
Enhanced Agent Base Class for Raw Data Intelligence

Enhanced base class that enables organic CIL influence for raw data intelligence agents.
Integrates uncertainty-driven curiosity, resonance calculations, and strategic insight consumption
to create agents that participate in the CIL's organic intelligence network.

Key Features:
- Organic CIL influence through resonance and insights
- Uncertainty-driven exploration and learning
- Motif creation and enhancement
- Strategic intelligence contribution
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

from .uncertainty_handler import UncertaintyHandler
from .resonance_integration import ResonanceIntegration
from .motif_integration import MotifIntegration
from .strategic_insight_consumer import StrategicInsightConsumer
from .cross_team_integration import CrossTeamIntegration
from .doctrine_integration import DoctrineIntegration


class EnhancedRawDataAgent:
    """
    Enhanced base class for organically CIL-influenced raw data intelligence agents
    
    This base class provides:
    - Organic CIL influence through resonance and strategic insights
    - Uncertainty-driven curiosity and exploration
    - Motif creation and pattern evolution
    - Strategic intelligence contribution
    - Natural learning and adaptation
    """
    
    def __init__(self, agent_name: str, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.agent_name = agent_name
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # Core CIL integration components
        self.resonance_integration = ResonanceIntegration(supabase_manager)
        self.uncertainty_handler = UncertaintyHandler(supabase_manager)
        
        # Phase 2 components - Strategic Intelligence Integration
        self.motif_integration = MotifIntegration(supabase_manager)
        self.strategic_insight_consumer = StrategicInsightConsumer(supabase_manager)
        self.cross_team_integration = CrossTeamIntegration(supabase_manager)
        
        # Phase 3 components - Organic Doctrine Integration
        self.doctrine_integration = DoctrineIntegration(supabase_manager)
        
        # Agent capabilities and specializations
        self.capabilities = [
            "raw_data_analysis",
            "uncertainty_driven_exploration",
            "resonance_calculation",
            "organic_cil_integration",
            "motif_creation",
            "strategic_insight_consumption",
            "cross_team_pattern_awareness",
            "doctrine_integration",
            "strategic_learning"
        ]
        
        self.specializations = [
            "pattern_detection",
            "uncertainty_identification",
            "resonance_enhancement",
            "organic_learning",
            "motif_evolution",
            "strategic_analysis",
            "cross_team_confluence",
            "doctrine_application",
            "strategic_doctrine_learning"
        ]
        
        # CIL integration state
        self.cil_integration_enabled = True
        self.uncertainty_embrace_enabled = True
        self.resonance_enhancement_enabled = True
        self.motif_integration_enabled = True
        self.strategic_insight_consumption_enabled = True
        self.cross_team_awareness_enabled = True
        self.doctrine_integration_enabled = True
        
        # Learning and adaptation tracking
        self.learning_history = []
        self.uncertainty_resolution_count = 0
        self.resonance_contributions = 0
        self.organic_insights_gained = 0
        self.motif_contributions = 0
        self.strategic_insights_consumed = 0
        self.cross_team_confluence_detections = 0
        self.doctrine_queries = 0
        self.doctrine_contributions = 0
        self.contraindication_checks = 0
    
    async def analyze_with_organic_influence(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze with natural CIL influence through resonance and insights
        
        Args:
            market_data: Market data to analyze
            
        Returns:
            Enhanced analysis results with CIL integration
        """
        try:
            self.logger.info(f"Starting organic CIL-influenced analysis for {self.agent_name}")
            
            # 1. Perform base analysis (existing functionality)
            base_analysis = await self._perform_base_analysis(market_data)
            
            # 2. Apply resonance-enhanced scoring
            if self.resonance_enhancement_enabled:
                resonance_results = await self.resonance_integration.calculate_strand_resonance(base_analysis)
                base_analysis['resonance'] = resonance_results
                base_analysis['enhanced_score'] = resonance_results.get('enhanced_score', base_analysis.get('confidence', 0.0))
            
            # 3. Consume valuable CIL insights naturally (Phase 2)
            if self.cil_integration_enabled and self.strategic_insight_consumption_enabled:
                cil_insights = await self.strategic_insight_consumer.consume_cil_insights(
                    base_analysis.get('pattern_type', 'general')
                )
                base_analysis['cil_insights'] = cil_insights
                self.strategic_insights_consumed += len(cil_insights)
            
            # 4. Contribute to motif creation (Phase 2)
            if self.cil_integration_enabled and self.motif_integration_enabled:
                motif_contribution = await self.motif_integration.create_motif_from_pattern(base_analysis)
                base_analysis['motif_contribution'] = motif_contribution
                if motif_contribution:
                    self.motif_contributions += 1
            
            # 5. Cross-team pattern awareness (Phase 2)
            if self.cil_integration_enabled and self.cross_team_awareness_enabled:
                cross_team_confluence = await self.cross_team_integration.detect_cross_team_confluence("5m")
                base_analysis['cross_team_confluence'] = cross_team_confluence
                self.cross_team_confluence_detections += len(cross_team_confluence)
            
            # 6. Doctrine integration (Phase 3)
            if self.cil_integration_enabled and self.doctrine_integration_enabled:
                doctrine_guidance = await self.doctrine_integration.query_relevant_doctrine(
                    base_analysis.get('type', 'general')
                )
                base_analysis['doctrine_guidance'] = doctrine_guidance
                self.doctrine_queries += 1
            
            # 7. Handle uncertainty-driven exploration
            if self.uncertainty_embrace_enabled:
                uncertainty_analysis = await self.uncertainty_handler.detect_uncertainty(base_analysis)
                base_analysis['uncertainty_analysis'] = uncertainty_analysis
                
                # Publish uncertainty strands if uncertainty detected
                if uncertainty_analysis.get('uncertainty_detected', False):
                    uncertainty_strand_id = await self.uncertainty_handler.publish_uncertainty_strand(uncertainty_analysis)
                    base_analysis['uncertainty_strand_id'] = uncertainty_strand_id
                    self.uncertainty_resolution_count += 1
            
            # 8. Publish results with resonance values
            enhanced_strand_id = await self._publish_enhanced_results(base_analysis)
            base_analysis['enhanced_strand_id'] = enhanced_strand_id
            
            # 9. Update learning and adaptation tracking
            await self._update_learning_tracking(base_analysis)
            
            self.logger.info(f"Completed organic CIL-influenced analysis for {self.agent_name}")
            return base_analysis
            
        except Exception as e:
            self.logger.error(f"Organic CIL-influenced analysis failed for {self.agent_name}: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'agent': self.agent_name,
                'analysis_failed': True
            }
    
    async def contribute_to_motif(self, pattern_data: Dict[str, Any]) -> str:
        """
        Contribute pattern data to motif creation for organic evolution
        
        Args:
            pattern_data: Pattern data to contribute to motif
            
        Returns:
            Motif strand ID
        """
        try:
            if not self.motif_integration:
                self.logger.warning("Motif integration not available - will be implemented in Phase 2")
                return None
            
            # Extract pattern invariants
            pattern_invariants = await self._extract_pattern_invariants(pattern_data)
            
            # Identify failure conditions
            failure_conditions = await self._identify_failure_conditions(pattern_data)
            
            # Provide mechanism hypotheses
            mechanism_hypotheses = await self._generate_mechanism_hypotheses(pattern_data)
            
            # Create motif strand with resonance values
            motif_data = {
                'pattern_invariants': pattern_invariants,
                'failure_conditions': failure_conditions,
                'mechanism_hypotheses': mechanism_hypotheses,
                'resonance_values': await self.resonance_integration.calculate_strand_resonance(pattern_data),
                'agent_contribution': self.agent_name,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            motif_strand_id = await self.motif_integration.create_motif_from_pattern(motif_data)
            
            if motif_strand_id:
                self.logger.info(f"Contributed to motif creation: {motif_strand_id}")
                self.organic_insights_gained += 1
            
            return motif_strand_id
            
        except Exception as e:
            self.logger.error(f"Motif contribution failed: {e}")
            return None
    
    async def calculate_resonance_contribution(self, strand_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate resonance contribution for organic evolution
        
        Args:
            strand_data: Strand data to calculate resonance for
            
        Returns:
            Resonance contribution results
        """
        try:
            # Calculate φ, ρ values
            resonance_results = await self.resonance_integration.calculate_strand_resonance(strand_data)
            
            # Update telemetry
            telemetry_update = {
                'agent': self.agent_name,
                'resonance_contribution': resonance_results,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Contribute to global θ field
            theta_contribution = await self._contribute_to_global_theta(resonance_results)
            telemetry_update['theta_contribution'] = theta_contribution
            
            # Enable organic influence through resonance
            organic_influence = await self._calculate_organic_influence(resonance_results)
            telemetry_update['organic_influence'] = organic_influence
            
            # Track contribution
            self.resonance_contributions += 1
            
            return telemetry_update
            
        except Exception as e:
            self.logger.error(f"Resonance contribution calculation failed: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    async def participate_in_organic_experiments(self, experiment_insights: Dict[str, Any]) -> Dict[str, Any]:
        """
        Participate in organic experiments driven by CIL insights
        
        Args:
            experiment_insights: CIL experiment insights and directives
            
        Returns:
            Experiment participation results
        """
        try:
            self.logger.info(f"Participating in organic experiment for {self.agent_name}")
            
            experiment_results = {
                'agent': self.agent_name,
                'experiment_id': experiment_insights.get('experiment_id', 'unknown'),
                'participation_timestamp': datetime.now(timezone.utc).isoformat(),
                'experiment_type': experiment_insights.get('type', 'general'),
                'results': {},
                'learning_gained': {},
                'resonance_impact': {}
            }
            
            # Execute experiments based on valuable insights
            if experiment_insights.get('type') == 'uncertainty_resolution':
                resolution_results = await self._execute_uncertainty_experiment(experiment_insights)
                experiment_results['results'] = resolution_results
            elif experiment_insights.get('type') == 'resonance_enhancement':
                enhancement_results = await self._execute_resonance_experiment(experiment_insights)
                experiment_results['results'] = enhancement_results
            else:
                general_results = await self._execute_general_experiment(experiment_insights)
                experiment_results['results'] = general_results
            
            # Track progress and results organically
            experiment_results['learning_gained'] = await self._extract_experiment_learning(experiment_results)
            
            # Contribute to experiment learning
            learning_contribution = await self._contribute_to_experiment_learning(experiment_results)
            experiment_results['learning_contribution'] = learning_contribution
            
            # Report back through natural strand system
            experiment_strand_id = await self._publish_experiment_results(experiment_results)
            experiment_results['experiment_strand_id'] = experiment_strand_id
            
            self.logger.info(f"Completed organic experiment participation for {self.agent_name}")
            return experiment_results
            
        except Exception as e:
            self.logger.error(f"Organic experiment participation failed: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    async def _perform_base_analysis(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform base analysis (existing functionality)"""
        try:
            # This would call the existing analysis methods
            # For now, return a mock analysis result
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'agent': self.agent_name,
                'confidence': 0.7,
                'patterns': [
                    {'type': 'volume_spike', 'severity': 'medium', 'confidence': 0.8},
                    {'type': 'divergence', 'severity': 'low', 'confidence': 0.6}
                ],
                'analysis_components': {
                    'volume': {'confidence': 0.8, 'patterns': 2},
                    'divergence': {'confidence': 0.6, 'patterns': 1}
                },
                'data_points': 100,
                'significant_patterns': [
                    {'type': 'volume_spike', 'severity': 'medium', 'confidence': 0.8}
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Base analysis failed: {e}")
            return {'error': str(e), 'timestamp': datetime.now(timezone.utc).isoformat()}
    
    async def _publish_enhanced_results(self, analysis_results: Dict[str, Any]) -> Optional[str]:
        """Publish enhanced results with resonance values"""
        try:
            # Create enhanced strand content
            strand_content = {
                'analysis_results': analysis_results,
                'cil_integration': {
                    'resonance_enabled': self.resonance_enhancement_enabled,
                    'uncertainty_embrace_enabled': self.uncertainty_embrace_enabled,
                    'organic_influence_active': True
                },
                'agent_capabilities': self.capabilities,
                'learning_tracking': {
                    'uncertainty_resolutions': self.uncertainty_resolution_count,
                    'resonance_contributions': self.resonance_contributions,
                    'organic_insights': self.organic_insights_gained
                }
            }
            
            # Create tags for enhanced strand
            tags = f"enhanced:raw_data:{self.agent_name}:cil_integrated:organic_influence"
            
            # Publish to strands (mock implementation)
            strand_id = f"enhanced_{self.agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            self.logger.info(f"Published enhanced results: {strand_id}")
            return strand_id
            
        except Exception as e:
            self.logger.error(f"Enhanced results publishing failed: {e}")
            return None
    
    async def _update_learning_tracking(self, analysis_results: Dict[str, Any]):
        """Update learning and adaptation tracking"""
        try:
            learning_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'analysis_confidence': analysis_results.get('confidence', 0.0),
                'enhanced_score': analysis_results.get('enhanced_score', 0.0),
                'uncertainty_detected': analysis_results.get('uncertainty_analysis', {}).get('uncertainty_detected', False),
                'resonance_contribution': analysis_results.get('resonance', {}).get('enhanced_score', 0.0),
                'patterns_detected': len(analysis_results.get('patterns', [])),
                'significant_patterns': len(analysis_results.get('significant_patterns', []))
            }
            
            self.learning_history.append(learning_entry)
            
            # Keep only recent learning history (last 100 entries)
            if len(self.learning_history) > 100:
                self.learning_history = self.learning_history[-100:]
            
        except Exception as e:
            self.logger.error(f"Learning tracking update failed: {e}")
    
    async def _extract_pattern_invariants(self, pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pattern invariants for motif creation"""
        try:
            invariants = {
                'pattern_type': pattern_data.get('type', 'unknown'),
                'severity_levels': pattern_data.get('severity', 'low'),
                'confidence_range': {
                    'min': pattern_data.get('confidence', 0.0),
                    'max': pattern_data.get('confidence', 0.0)
                },
                'temporal_characteristics': pattern_data.get('temporal', {}),
                'data_requirements': pattern_data.get('data_requirements', {})
            }
            
            return invariants
            
        except Exception as e:
            self.logger.error(f"Pattern invariant extraction failed: {e}")
            return {}
    
    async def _identify_failure_conditions(self, pattern_data: Dict[str, Any]) -> List[str]:
        """Identify failure conditions for patterns"""
        try:
            failure_conditions = []
            
            # Low confidence patterns
            if pattern_data.get('confidence', 0.0) < 0.3:
                failure_conditions.append('low_confidence')
            
            # Contradictory signals
            if 'contradictory' in str(pattern_data).lower():
                failure_conditions.append('contradictory_signals')
            
            # Insufficient data
            if pattern_data.get('data_points', 0) < 20:
                failure_conditions.append('insufficient_data')
            
            return failure_conditions
            
        except Exception as e:
            self.logger.error(f"Failure condition identification failed: {e}")
            return []
    
    async def _generate_mechanism_hypotheses(self, pattern_data: Dict[str, Any]) -> List[str]:
        """Generate mechanism hypotheses for patterns"""
        try:
            hypotheses = []
            
            pattern_type = pattern_data.get('type', 'unknown')
            
            if 'volume' in pattern_type.lower():
                hypotheses.append('institutional_trading_activity')
                hypotheses.append('retail_sentiment_shift')
            elif 'divergence' in pattern_type.lower():
                hypotheses.append('momentum_exhaustion')
                hypotheses.append('reversal_formation')
            else:
                hypotheses.append('market_structure_change')
                hypotheses.append('sentiment_shift')
            
            return hypotheses
            
        except Exception as e:
            self.logger.error(f"Mechanism hypothesis generation failed: {e}")
            return []
    
    async def _contribute_to_global_theta(self, resonance_results: Dict[str, Any]) -> float:
        """Contribute to global θ field"""
        try:
            # θ contribution based on resonance values
            phi = resonance_results.get('phi', 0.0)
            rho = resonance_results.get('rho', 0.0)
            
            theta_contribution = (phi + rho) / 2.0
            return min(1.0, theta_contribution)
            
        except Exception as e:
            self.logger.error(f"Global θ contribution failed: {e}")
            return 0.0
    
    async def _calculate_organic_influence(self, resonance_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate organic influence through resonance"""
        try:
            influence = {
                'influence_strength': 0.0,
                'influence_type': 'resonance_driven',
                'influence_confidence': 0.0
            }
            
            # Influence strength based on resonance values
            enhanced_score = resonance_results.get('enhanced_score', 0.0)
            influence['influence_strength'] = min(1.0, enhanced_score)
            
            # Influence confidence based on resonance confidence
            resonance_confidence = resonance_results.get('resonance_confidence', 0.0)
            influence['influence_confidence'] = resonance_confidence
            
            return influence
            
        except Exception as e:
            self.logger.error(f"Organic influence calculation failed: {e}")
            return {'influence_strength': 0.0, 'influence_type': 'error', 'influence_confidence': 0.0}
    
    async def _execute_uncertainty_experiment(self, experiment_insights: Dict[str, Any]) -> Dict[str, Any]:
        """Execute uncertainty resolution experiment"""
        try:
            # Mock uncertainty experiment execution
            return {
                'experiment_type': 'uncertainty_resolution',
                'resolution_attempted': True,
                'resolution_success': True,
                'learning_gained': ['uncertainty_cause_identified', 'resolution_method_improved'],
                'new_insights': ['uncertainty_patterns', 'resolution_effectiveness']
            }
            
        except Exception as e:
            self.logger.error(f"Uncertainty experiment execution failed: {e}")
            return {'error': str(e)}
    
    async def _execute_resonance_experiment(self, experiment_insights: Dict[str, Any]) -> Dict[str, Any]:
        """Execute resonance enhancement experiment"""
        try:
            # Mock resonance experiment execution
            return {
                'experiment_type': 'resonance_enhancement',
                'enhancement_applied': True,
                'enhancement_success': True,
                'resonance_improvement': 0.2,
                'new_insights': ['resonance_patterns', 'enhancement_effectiveness']
            }
            
        except Exception as e:
            self.logger.error(f"Resonance experiment execution failed: {e}")
            return {'error': str(e)}
    
    async def _execute_general_experiment(self, experiment_insights: Dict[str, Any]) -> Dict[str, Any]:
        """Execute general experiment"""
        try:
            # Mock general experiment execution
            return {
                'experiment_type': 'general',
                'experiment_completed': True,
                'results_obtained': True,
                'learning_gained': ['general_insights', 'method_improvements']
            }
            
        except Exception as e:
            self.logger.error(f"General experiment execution failed: {e}")
            return {'error': str(e)}
    
    async def _extract_experiment_learning(self, experiment_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract learning from experiment results"""
        try:
            learning = {
                'key_insights': experiment_results.get('results', {}).get('new_insights', []),
                'method_improvements': experiment_results.get('results', {}).get('learning_gained', []),
                'success_factors': [],
                'failure_factors': []
            }
            
            # Determine success/failure factors
            if experiment_results.get('results', {}).get('resolution_success', False):
                learning['success_factors'].append('uncertainty_resolution_effective')
            if experiment_results.get('results', {}).get('enhancement_success', False):
                learning['success_factors'].append('resonance_enhancement_effective')
            
            return learning
            
        except Exception as e:
            self.logger.error(f"Experiment learning extraction failed: {e}")
            return {'key_insights': [], 'method_improvements': [], 'success_factors': [], 'failure_factors': []}
    
    async def _contribute_to_experiment_learning(self, experiment_results: Dict[str, Any]) -> str:
        """Contribute to experiment learning"""
        try:
            # Create learning contribution strand
            learning_contribution = {
                'experiment_id': experiment_results.get('experiment_id'),
                'agent': self.agent_name,
                'learning_contribution': experiment_results.get('learning_gained', {}),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Mock strand ID
            contribution_id = f"learning_contribution_{self.agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            return contribution_id
            
        except Exception as e:
            self.logger.error(f"Experiment learning contribution failed: {e}")
            return None
    
    async def _publish_experiment_results(self, experiment_results: Dict[str, Any]) -> Optional[str]:
        """Publish experiment results"""
        try:
            # Create experiment results strand
            strand_content = {
                'experiment_results': experiment_results,
                'agent': self.agent_name,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Mock strand ID
            strand_id = f"experiment_{self.agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            return strand_id
            
        except Exception as e:
            self.logger.error(f"Experiment results publishing failed: {e}")
            return None
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of learning and adaptation"""
        try:
            return {
                'agent': self.agent_name,
                'uncertainty_resolutions': self.uncertainty_resolution_count,
                'resonance_contributions': self.resonance_contributions,
                'organic_insights_gained': self.organic_insights_gained,
                'motif_contributions': self.motif_contributions,
                'strategic_insights_consumed': self.strategic_insights_consumed,
                'cross_team_confluence_detections': self.cross_team_confluence_detections,
                'doctrine_queries': self.doctrine_queries,
                'doctrine_contributions': self.doctrine_contributions,
                'contraindication_checks': self.contraindication_checks,
                'learning_history_length': len(self.learning_history),
                'cil_integration_enabled': self.cil_integration_enabled,
                'uncertainty_embrace_enabled': self.uncertainty_embrace_enabled,
                'resonance_enhancement_enabled': self.resonance_enhancement_enabled,
                'motif_integration_enabled': self.motif_integration_enabled,
                'strategic_insight_consumption_enabled': self.strategic_insight_consumption_enabled,
                'cross_team_awareness_enabled': self.cross_team_awareness_enabled,
                'doctrine_integration_enabled': self.doctrine_integration_enabled,
                'recent_learning': self.learning_history[-5:] if self.learning_history else []
            }
            
        except Exception as e:
            self.logger.error(f"Learning summary generation failed: {e}")
            return {'error': str(e)}
    
    # Phase 2: Strategic Intelligence Integration Methods
    
    async def contribute_to_motif_evolution(self, pattern_data: Dict[str, Any]) -> str:
        """
        Contribute to motif evolution for organic pattern development.
        This method enables agents to participate in motif creation and enhancement.
        """
        if not self.motif_integration_enabled:
            self.logger.warning("Motif integration is disabled")
            return None
        
        try:
            self.logger.info(f"Agent {self.agent_name} contributing to motif evolution")
            
            # Create motif from pattern data
            motif_id = await self.motif_integration.create_motif_from_pattern(pattern_data)
            
            if motif_id:
                self.motif_contributions += 1
                self.logger.info(f"Created motif: {motif_id}")
            
            return motif_id
            
        except Exception as e:
            self.logger.error(f"Motif evolution contribution failed: {e}")
            return None
    
    async def enhance_existing_motif(self, motif_id: str, new_evidence: Dict[str, Any]) -> str:
        """
        Enhance existing motif with new evidence for organic growth.
        """
        if not self.motif_integration_enabled:
            self.logger.warning("Motif integration is disabled")
            return None
        
        try:
            self.logger.info(f"Agent {self.agent_name} enhancing existing motif: {motif_id}")
            
            # Enhance existing motif
            enhancement_id = await self.motif_integration.enhance_existing_motif(motif_id, new_evidence)
            
            if enhancement_id:
                self.motif_contributions += 1
                self.logger.info(f"Enhanced motif: {enhancement_id}")
            
            return enhancement_id
            
        except Exception as e:
            self.logger.error(f"Motif enhancement failed: {e}")
            return None
    
    async def query_motif_families(self, pattern_type: str) -> List[Dict[str, Any]]:
        """
        Query relevant motif families for organic pattern discovery.
        """
        if not self.motif_integration_enabled:
            self.logger.warning("Motif integration is disabled")
            return []
        
        try:
            self.logger.info(f"Agent {self.agent_name} querying motif families for: {pattern_type}")
            
            # Query motif families
            motif_families = await self.motif_integration.query_motif_families(pattern_type)
            
            self.logger.info(f"Found {len(motif_families)} relevant motif families")
            return motif_families
            
        except Exception as e:
            self.logger.error(f"Motif family query failed: {e}")
            return []
    
    async def consume_strategic_insights(self, pattern_type: str) -> List[Dict[str, Any]]:
        """
        Consume strategic insights from CIL for enhanced analysis.
        """
        if not self.strategic_insight_consumption_enabled:
            self.logger.warning("Strategic insight consumption is disabled")
            return []
        
        try:
            self.logger.info(f"Agent {self.agent_name} consuming strategic insights for: {pattern_type}")
            
            # Consume CIL insights
            insights = await self.strategic_insight_consumer.consume_cil_insights(pattern_type)
            
            self.strategic_insights_consumed += len(insights)
            self.logger.info(f"Consumed {len(insights)} strategic insights")
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Strategic insight consumption failed: {e}")
            return []
    
    async def subscribe_to_meta_signals(self, meta_signal_types: List[str]) -> Dict[str, Any]:
        """
        Subscribe to valuable CIL meta-signals organically.
        """
        if not self.strategic_insight_consumption_enabled:
            self.logger.warning("Strategic insight consumption is disabled")
            return {}
        
        try:
            self.logger.info(f"Agent {self.agent_name} subscribing to meta-signals: {meta_signal_types}")
            
            # Subscribe to meta-signals
            subscription_results = await self.strategic_insight_consumer.subscribe_to_valuable_meta_signals(meta_signal_types)
            
            self.logger.info(f"Subscribed to {len(subscription_results.get('subscribed_types', []))} meta-signal types")
            return subscription_results
            
        except Exception as e:
            self.logger.error(f"Meta-signal subscription failed: {e}")
            return {}
    
    async def contribute_to_strategic_analysis(self, analysis_data: Dict[str, Any]) -> str:
        """
        Contribute to CIL strategic analysis through natural insights.
        """
        if not self.strategic_insight_consumption_enabled:
            self.logger.warning("Strategic insight consumption is disabled")
            return None
        
        try:
            self.logger.info(f"Agent {self.agent_name} contributing to strategic analysis")
            
            # Contribute to strategic analysis
            contribution_id = await self.strategic_insight_consumer.contribute_to_strategic_analysis(analysis_data)
            
            if contribution_id:
                self.logger.info(f"Contributed to strategic analysis: {contribution_id}")
            
            return contribution_id
            
        except Exception as e:
            self.logger.error(f"Strategic analysis contribution failed: {e}")
            return None
    
    async def detect_cross_team_confluence(self, time_window: str = "5m") -> List[Dict[str, Any]]:
        """
        Detect cross-team confluence patterns for organic insights.
        """
        if not self.cross_team_awareness_enabled:
            self.logger.warning("Cross-team awareness is disabled")
            return []
        
        try:
            self.logger.info(f"Agent {self.agent_name} detecting cross-team confluence in: {time_window}")
            
            # Detect cross-team confluence
            confluence_patterns = await self.cross_team_integration.detect_cross_team_confluence(time_window)
            
            self.cross_team_confluence_detections += len(confluence_patterns)
            self.logger.info(f"Detected {len(confluence_patterns)} confluence patterns")
            
            return confluence_patterns
            
        except Exception as e:
            self.logger.error(f"Cross-team confluence detection failed: {e}")
            return []
    
    async def identify_lead_lag_patterns(self, team_pairs: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """
        Identify lead-lag patterns between teams for organic learning.
        """
        if not self.cross_team_awareness_enabled:
            self.logger.warning("Cross-team awareness is disabled")
            return []
        
        try:
            self.logger.info(f"Agent {self.agent_name} identifying lead-lag patterns for {len(team_pairs)} team pairs")
            
            # Identify lead-lag patterns
            lead_lag_patterns = await self.cross_team_integration.identify_lead_lag_patterns(team_pairs)
            
            self.logger.info(f"Identified {len(lead_lag_patterns)} lead-lag patterns")
            return lead_lag_patterns
            
        except Exception as e:
            self.logger.error(f"Lead-lag pattern identification failed: {e}")
            return []
    
    async def contribute_cross_team_insights(self, confluence_data: Dict[str, Any]) -> str:
        """
        Contribute cross-team insights to CIL strategic analysis.
        """
        if not self.cross_team_awareness_enabled:
            self.logger.warning("Cross-team awareness is disabled")
            return None
        
        try:
            self.logger.info(f"Agent {self.agent_name} contributing cross-team insights")
            
            # Contribute cross-team insights
            contribution_id = await self.cross_team_integration.contribute_to_strategic_analysis(confluence_data)
            
            if contribution_id:
                self.logger.info(f"Contributed cross-team insights: {contribution_id}")
            
            return contribution_id
            
        except Exception as e:
            self.logger.error(f"Cross-team insight contribution failed: {e}")
            return None
    
    # Phase 3: Organic Doctrine Integration Methods
    
    async def query_relevant_doctrine(self, pattern_type: str) -> Dict[str, Any]:
        """
        Query relevant doctrine for pattern type organically.
        """
        if not self.doctrine_integration_enabled:
            self.logger.warning("Doctrine integration is disabled")
            return {}
        
        try:
            self.logger.info(f"Agent {self.agent_name} querying relevant doctrine for: {pattern_type}")
            
            # Query relevant doctrine
            doctrine_guidance = await self.doctrine_integration.query_relevant_doctrine(pattern_type)
            
            self.doctrine_queries += 1
            self.logger.info(f"Retrieved doctrine guidance with {len(doctrine_guidance.get('recommendations', []))} recommendations")
            
            return doctrine_guidance
            
        except Exception as e:
            self.logger.error(f"Doctrine query failed: {e}")
            return {}
    
    async def contribute_to_doctrine(self, pattern_evidence: Dict[str, Any]) -> str:
        """
        Contribute pattern evidence to doctrine for organic learning.
        """
        if not self.doctrine_integration_enabled:
            self.logger.warning("Doctrine integration is disabled")
            return None
        
        try:
            self.logger.info(f"Agent {self.agent_name} contributing to doctrine")
            
            # Contribute to doctrine
            contribution_id = await self.doctrine_integration.contribute_to_doctrine(pattern_evidence)
            
            if contribution_id:
                self.doctrine_contributions += 1
                self.logger.info(f"Contributed to doctrine: {contribution_id}")
            
            return contribution_id
            
        except Exception as e:
            self.logger.error(f"Doctrine contribution failed: {e}")
            return None
    
    async def check_doctrine_contraindications(self, proposed_experiment: Dict[str, Any]) -> bool:
        """
        Check if proposed experiment is contraindicated organically.
        """
        if not self.doctrine_integration_enabled:
            self.logger.warning("Doctrine integration is disabled")
            return False
        
        try:
            self.logger.info(f"Agent {self.agent_name} checking doctrine contraindications")
            
            # Check contraindications
            is_contraindicated = await self.doctrine_integration.check_doctrine_contraindications(proposed_experiment)
            
            self.contraindication_checks += 1
            self.logger.info(f"Contraindication check result: {'contraindicated' if is_contraindicated else 'safe to proceed'}")
            
            return is_contraindicated
            
        except Exception as e:
            self.logger.error(f"Contraindication check failed: {e}")
            return False
    
    def get_doctrine_integration_summary(self) -> Dict[str, Any]:
        """
        Get summary of doctrine integration.
        """
        if not self.doctrine_integration_enabled:
            return {'doctrine_integration': 'disabled'}
        
        try:
            return self.doctrine_integration.get_doctrine_integration_summary()
            
        except Exception as e:
            self.logger.error(f"Doctrine integration summary failed: {e}")
            return {'error': str(e)}
