"""
Enhanced Trader Capabilities

Demonstrates enhanced Trader capabilities with full organic CIL influence.
This module showcases the complete integration of all Phase 3 components:
- Execution Doctrine Integration
- Natural CIL Execution Influence
- Seamless Organic Coordination

Key Features:
- Full organic CIL influence with doctrine integration
- Natural execution coordination through organic influence
- Seamless organic execution intelligence flow
- End-to-end organic execution intelligence demonstration
- Complete organic intelligence network participation
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from .enhanced_execution_agent import EnhancedExecutionAgent, EnhancedExecutionResult
from .execution_doctrine_integration import ExecutionDoctrineIntegration

logger = logging.getLogger(__name__)


@dataclass
class OrganicExecutionCapabilities:
    """Organic execution capabilities with full CIL influence"""
    doctrine_integration: bool
    natural_cil_influence: bool
    seamless_coordination: bool
    organic_intelligence_flow: bool
    end_to_end_integration: bool
    resonance_driven_evolution: bool
    uncertainty_driven_curiosity: bool
    motif_creation_evolution: bool
    cross_team_awareness: bool
    strategic_insight_consumption: bool


@dataclass
class OrganicExecutionIntelligence:
    """Complete organic execution intelligence state"""
    execution_capabilities: OrganicExecutionCapabilities
    doctrine_guidance: Dict[str, Any]
    cil_influence: Dict[str, Any]
    coordination_state: Dict[str, Any]
    intelligence_flow: Dict[str, Any]
    resonance_metrics: Dict[str, float]
    uncertainty_analysis: Dict[str, Any]
    motif_contributions: List[str]
    cross_team_insights: List[Dict[str, Any]]
    strategic_insights: List[Dict[str, Any]]
    timestamp: datetime


class EnhancedTraderCapabilities:
    """Enhanced Trader capabilities with full organic CIL influence"""
    
    def __init__(self, agent_name: str, supabase_manager, llm_client):
        self.agent_name = agent_name
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        
        # Initialize all organic intelligence components
        self.enhanced_execution_agent = EnhancedExecutionAgent(agent_name, supabase_manager, llm_client)
        self.execution_doctrine_integration = ExecutionDoctrineIntegration(supabase_manager, llm_client)
        
        # Organic intelligence state
        self.organic_capabilities = OrganicExecutionCapabilities(
            doctrine_integration=True,
            natural_cil_influence=True,
            seamless_coordination=True,
            organic_intelligence_flow=True,
            end_to_end_integration=True,
            resonance_driven_evolution=True,
            uncertainty_driven_curiosity=True,
            motif_creation_evolution=True,
            cross_team_awareness=True,
            strategic_insight_consumption=True
        )
        
        # Intelligence state tracking
        self.intelligence_history = []
        self.capability_evolution = []
        
        logger.info(f"Initialized Enhanced Trader Capabilities: {agent_name} with full organic CIL influence")
    
    async def demonstrate_full_organic_execution_intelligence(self, market_data: Dict[str, Any], approved_plan: Dict[str, Any]) -> OrganicExecutionIntelligence:
        """
        Demonstrate full organic execution intelligence with all capabilities
        
        Args:
            market_data: Current market data
            approved_plan: Approved trading plan from Decision Maker
            
        Returns:
            Complete organic execution intelligence state
        """
        try:
            # Step 1: Query execution doctrine for guidance
            doctrine_guidance = await self.execution_doctrine_integration.query_relevant_execution_doctrine(
                approved_plan.get('execution_type', 'market_order')
            )
            
            # Step 2: Check for contraindications
            is_contraindicated = await self.execution_doctrine_integration.check_execution_doctrine_contraindications(
                approved_plan
            )
            
            if is_contraindicated:
                logger.warning(f"Execution plan contraindicated for {self.agent_name}")
                return await self._handle_contraindicated_execution(approved_plan, doctrine_guidance)
            
            # Step 3: Execute with full organic influence
            execution_result = await self.enhanced_execution_agent.execute_with_organic_influence(
                market_data, approved_plan
            )
            
            # Step 4: Contribute to doctrine evolution
            doctrine_contribution = await self._contribute_to_doctrine_evolution(execution_result)
            
            # Step 5: Assess organic intelligence state
            organic_intelligence = await self._assess_organic_intelligence_state(
                execution_result, doctrine_guidance, doctrine_contribution
            )
            
            # Step 6: Track capability evolution
            await self._track_capability_evolution(organic_intelligence)
            
            # Step 7: Publish organic intelligence state
            await self._publish_organic_intelligence_state(organic_intelligence)
            
            logger.info(f"Demonstrated full organic execution intelligence: {self.agent_name}, "
                       f"capabilities: {len([cap for cap in organic_intelligence.execution_capabilities.__dict__.values() if cap])}")
            
            return organic_intelligence
            
        except Exception as e:
            logger.error(f"Error demonstrating full organic execution intelligence: {e}")
            return await self._handle_organic_intelligence_error(e, market_data, approved_plan)
    
    async def participate_in_organic_execution_experiments_enhanced(self, experiment_insights: Dict[str, Any]) -> Dict[str, Any]:
        """
        Participate in organic execution experiments with enhanced capabilities
        
        Args:
            experiment_insights: Insights from CIL-driven experiments
            
        Returns:
            Enhanced experiment participation results
        """
        try:
            # Check experiment safety with doctrine integration
            is_safe = await self.execution_doctrine_integration.check_execution_doctrine_contraindications(
                experiment_insights
            )
            
            if not is_safe:
                logger.warning(f"Experiment contraindicated for {self.agent_name}")
                return await self._handle_unsafe_experiment(experiment_insights)
            
            # Participate in experiment with enhanced capabilities
            experiment_results = await self.enhanced_execution_agent.participate_in_organic_execution_experiments(
                experiment_insights
            )
            
            # Contribute experiment results to doctrine
            doctrine_contribution = await self.execution_doctrine_integration.contribute_to_execution_doctrine(
                experiment_results
            )
            
            # Assess experiment impact on organic intelligence
            intelligence_impact = await self._assess_experiment_intelligence_impact(
                experiment_results, doctrine_contribution
            )
            
            # Track experiment learning
            await self._track_experiment_learning(experiment_results, intelligence_impact)
            
            logger.info(f"Participated in organic execution experiment: {self.agent_name}, "
                       f"doctrine contribution: {doctrine_contribution}")
            
            return {
                'experiment_results': experiment_results,
                'doctrine_contribution': doctrine_contribution,
                'intelligence_impact': intelligence_impact,
                'learning_insights': await self._extract_experiment_learning_insights(experiment_results)
            }
            
        except Exception as e:
            logger.error(f"Error participating in organic execution experiments enhanced: {e}")
            return {'error': str(e), 'experiment_insights': experiment_insights}
    
    async def get_organic_intelligence_status(self) -> Dict[str, Any]:
        """Get current organic intelligence status"""
        try:
            # Get enhanced agent metrics
            agent_metrics = await self.enhanced_execution_agent._get_agent_specific_metrics()
            
            # Get doctrine integration status
            doctrine_status = await self._get_doctrine_integration_status()
            
            # Get organic capabilities status
            capabilities_status = self._get_capabilities_status()
            
            # Get intelligence flow status
            intelligence_flow_status = await self._get_intelligence_flow_status()
            
            # Compile comprehensive status
            status = {
                'agent_name': self.agent_name,
                'organic_capabilities': capabilities_status,
                'agent_metrics': agent_metrics,
                'doctrine_integration': doctrine_status,
                'intelligence_flow': intelligence_flow_status,
                'capability_evolution_count': len(self.capability_evolution),
                'intelligence_history_count': len(self.intelligence_history),
                'timestamp': datetime.now().isoformat()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting organic intelligence status: {e}")
            return {'error': str(e), 'agent_name': self.agent_name}
    
    async def _contribute_to_doctrine_evolution(self, execution_result: EnhancedExecutionResult) -> str:
        """Contribute execution result to doctrine evolution"""
        try:
            # Prepare execution evidence for doctrine contribution
            execution_evidence = {
                'execution_result': execution_result,
                'execution_type': 'enhanced_organic_execution',
                'success_rate': execution_result.success_score,
                'execution_quality': execution_result.success_score,
                'confidence': execution_result.resonance_metrics.get('phi', 0.5),
                'novelty_score': self._calculate_novelty_score(execution_result),
                'pattern_strength': self._calculate_pattern_strength(execution_result),
                'generality_score': self._calculate_generality_score(execution_result),
                'innovation_score': self._calculate_innovation_score(execution_result)
            }
            
            # Contribute to doctrine
            doctrine_contribution_id = await self.execution_doctrine_integration.contribute_to_execution_doctrine(
                execution_evidence
            )
            
            return doctrine_contribution_id
            
        except Exception as e:
            logger.error(f"Error contributing to doctrine evolution: {e}")
            return ""
    
    async def _assess_organic_intelligence_state(self, execution_result: EnhancedExecutionResult, 
                                               doctrine_guidance: Dict[str, Any], 
                                               doctrine_contribution: str) -> OrganicExecutionIntelligence:
        """Assess complete organic intelligence state"""
        try:
            # Get CIL influence data
            cil_influence = execution_result.organic_influence
            
            # Get coordination state
            coordination_state = execution_result.cross_team_coordination
            
            # Get intelligence flow data
            intelligence_flow = {
                'data_driven_heartbeat': True,
                'resonance_enhanced_scoring': True,
                'uncertainty_driven_exploration': execution_result.uncertainty_exploration.get('overall_uncertainty', 0.5) > 0.7,
                'motif_contribution': len(execution_result.motif_contributions) > 0,
                'cross_team_coordination': len(execution_result.cross_team_coordination) > 0,
                'strategic_insight_consumption': len(execution_result.cil_insights_applied) > 0,
                'doctrine_integration': doctrine_contribution != "",
                'organic_evolution': True
            }
            
            # Create organic intelligence state
            organic_intelligence = OrganicExecutionIntelligence(
                execution_capabilities=self.organic_capabilities,
                doctrine_guidance=doctrine_guidance,
                cil_influence=cil_influence,
                coordination_state=coordination_state,
                intelligence_flow=intelligence_flow,
                resonance_metrics=execution_result.resonance_metrics,
                uncertainty_analysis=execution_result.uncertainty_exploration,
                motif_contributions=execution_result.motif_contributions,
                cross_team_insights=execution_result.cross_team_coordination.get('confluence_patterns', []),
                strategic_insights=execution_result.cil_insights_applied,
                timestamp=datetime.now()
            )
            
            return organic_intelligence
            
        except Exception as e:
            logger.error(f"Error assessing organic intelligence state: {e}")
            return await self._create_default_organic_intelligence_state()
    
    async def _track_capability_evolution(self, organic_intelligence: OrganicExecutionIntelligence):
        """Track capability evolution over time"""
        try:
            evolution_entry = {
                'timestamp': datetime.now(),
                'organic_intelligence': organic_intelligence,
                'capability_scores': self._calculate_capability_scores(organic_intelligence),
                'evolution_metrics': self._calculate_evolution_metrics(organic_intelligence)
            }
            
            self.capability_evolution.append(evolution_entry)
            
            # Keep only last 100 evolution entries
            if len(self.capability_evolution) > 100:
                self.capability_evolution = self.capability_evolution[-100:]
            
            # Track intelligence history
            self.intelligence_history.append(organic_intelligence)
            
            # Keep only last 50 intelligence states
            if len(self.intelligence_history) > 50:
                self.intelligence_history = self.intelligence_history[-50:]
            
        except Exception as e:
            logger.error(f"Error tracking capability evolution: {e}")
    
    async def _publish_organic_intelligence_state(self, organic_intelligence: OrganicExecutionIntelligence):
        """Publish organic intelligence state to AD_strands"""
        try:
            # Create organic intelligence strand
            intelligence_strand = {
                'module': 'trader',
                'kind': 'organic_execution_intelligence',
                'content': {
                    'organic_intelligence': organic_intelligence,
                    'execution_capabilities': organic_intelligence.execution_capabilities.__dict__,
                    'doctrine_guidance': organic_intelligence.doctrine_guidance,
                    'cil_influence': organic_intelligence.cil_influence,
                    'coordination_state': organic_intelligence.coordination_state,
                    'intelligence_flow': organic_intelligence.intelligence_flow,
                    'resonance_metrics': organic_intelligence.resonance_metrics,
                    'uncertainty_analysis': organic_intelligence.uncertainty_analysis,
                    'motif_contributions': organic_intelligence.motif_contributions,
                    'cross_team_insights': organic_intelligence.cross_team_insights,
                    'strategic_insights': organic_intelligence.strategic_insights,
                    'agent_name': self.agent_name,
                    'intelligence_state': 'full_organic_integration'
                },
                'tags': [
                    f'trader:{self.agent_name}',
                    'trader:organic_intelligence',
                    'trader:full_integration',
                    'trader:doctrine_integration',
                    'trader:natural_cil_influence',
                    'trader:seamless_coordination',
                    'cil:organic_intelligence_network'
                ],
                'sig_confidence': organic_intelligence.resonance_metrics.get('phi', 0.5),
                'outcome_score': self._calculate_organic_intelligence_score(organic_intelligence),
                'created_at': datetime.now().isoformat()
            }
            
            # Publish to AD_strands
            strand_id = await self._publish_strand_to_database(intelligence_strand)
            
            logger.info(f"Published organic intelligence state: {strand_id}")
            
        except Exception as e:
            logger.error(f"Error publishing organic intelligence state: {e}")
    
    def _calculate_novelty_score(self, execution_result: EnhancedExecutionResult) -> float:
        """Calculate novelty score for execution result"""
        try:
            # Base novelty from organic influence
            novelty = 0.0
            
            # CIL insights novelty
            if execution_result.cil_insights_applied:
                novelty += 0.3
            
            # Motif contributions novelty
            if execution_result.motif_contributions:
                novelty += 0.2
            
            # Cross-team coordination novelty
            if execution_result.cross_team_coordination:
                novelty += 0.2
            
            # Uncertainty exploration novelty
            if execution_result.uncertainty_exploration.get('overall_uncertainty', 0) > 0.7:
                novelty += 0.3
            
            return max(0.0, min(1.0, novelty))
            
        except Exception as e:
            logger.error(f"Error calculating novelty score: {e}")
            return 0.0
    
    def _calculate_pattern_strength(self, execution_result: EnhancedExecutionResult) -> float:
        """Calculate pattern strength for execution result"""
        try:
            # Base strength from resonance
            strength = execution_result.resonance_metrics.get('phi', 0.5)
            
            # Boost from success
            if execution_result.success:
                strength += 0.2
            
            # Boost from high success score
            if execution_result.success_score > 0.8:
                strength += 0.1
            
            return max(0.0, min(1.0, strength))
            
        except Exception as e:
            logger.error(f"Error calculating pattern strength: {e}")
            return 0.5
    
    def _calculate_generality_score(self, execution_result: EnhancedExecutionResult) -> float:
        """Calculate generality score for execution result"""
        try:
            # Base generality from cross-team coordination
            generality = 0.0
            
            if execution_result.cross_team_coordination:
                generality += 0.4
            
            # Boost from strategic insights
            if execution_result.strategic_insights:
                generality += 0.3
            
            # Boost from motif contributions
            if execution_result.motif_contributions:
                generality += 0.3
            
            return max(0.0, min(1.0, generality))
            
        except Exception as e:
            logger.error(f"Error calculating generality score: {e}")
            return 0.0
    
    def _calculate_innovation_score(self, execution_result: EnhancedExecutionResult) -> float:
        """Calculate innovation score for execution result"""
        try:
            # Base innovation from organic influence
            innovation = 0.0
            
            # Innovation from uncertainty exploration
            if execution_result.uncertainty_exploration.get('overall_uncertainty', 0) > 0.7:
                innovation += 0.4
            
            # Innovation from CIL insights
            if execution_result.cil_insights_applied:
                innovation += 0.3
            
            # Innovation from cross-team coordination
            if execution_result.cross_team_coordination:
                innovation += 0.3
            
            return max(0.0, min(1.0, innovation))
            
        except Exception as e:
            logger.error(f"Error calculating innovation score: {e}")
            return 0.0
    
    def _calculate_capability_scores(self, organic_intelligence: OrganicExecutionIntelligence) -> Dict[str, float]:
        """Calculate capability scores from organic intelligence"""
        try:
            capabilities = organic_intelligence.execution_capabilities
            
            return {
                'doctrine_integration': 1.0 if capabilities.doctrine_integration else 0.0,
                'natural_cil_influence': 1.0 if capabilities.natural_cil_influence else 0.0,
                'seamless_coordination': 1.0 if capabilities.seamless_coordination else 0.0,
                'organic_intelligence_flow': 1.0 if capabilities.organic_intelligence_flow else 0.0,
                'end_to_end_integration': 1.0 if capabilities.end_to_end_integration else 0.0,
                'resonance_driven_evolution': 1.0 if capabilities.resonance_driven_evolution else 0.0,
                'uncertainty_driven_curiosity': 1.0 if capabilities.uncertainty_driven_curiosity else 0.0,
                'motif_creation_evolution': 1.0 if capabilities.motif_creation_evolution else 0.0,
                'cross_team_awareness': 1.0 if capabilities.cross_team_awareness else 0.0,
                'strategic_insight_consumption': 1.0 if capabilities.strategic_insight_consumption else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error calculating capability scores: {e}")
            return {}
    
    def _calculate_evolution_metrics(self, organic_intelligence: OrganicExecutionIntelligence) -> Dict[str, float]:
        """Calculate evolution metrics from organic intelligence"""
        try:
            return {
                'resonance_evolution': organic_intelligence.resonance_metrics.get('phi', 0.5),
                'intelligence_flow_strength': sum(organic_intelligence.intelligence_flow.values()) / len(organic_intelligence.intelligence_flow),
                'doctrine_integration_strength': organic_intelligence.doctrine_guidance.get('doctrine_confidence', 0.5),
                'coordination_strength': len(organic_intelligence.cross_team_insights) / 10.0,  # Normalize
                'motif_contribution_strength': len(organic_intelligence.motif_contributions) / 5.0,  # Normalize
                'strategic_insight_strength': len(organic_intelligence.strategic_insights) / 10.0  # Normalize
            }
            
        except Exception as e:
            logger.error(f"Error calculating evolution metrics: {e}")
            return {}
    
    def _calculate_organic_intelligence_score(self, organic_intelligence: OrganicExecutionIntelligence) -> float:
        """Calculate overall organic intelligence score"""
        try:
            # Base score from capabilities
            capability_scores = self._calculate_capability_scores(organic_intelligence)
            base_score = sum(capability_scores.values()) / len(capability_scores)
            
            # Boost from resonance
            resonance_boost = organic_intelligence.resonance_metrics.get('phi', 0.5) * 0.2
            
            # Boost from intelligence flow
            flow_boost = sum(organic_intelligence.intelligence_flow.values()) / len(organic_intelligence.intelligence_flow) * 0.2
            
            # Boost from doctrine integration
            doctrine_boost = organic_intelligence.doctrine_guidance.get('doctrine_confidence', 0.5) * 0.1
            
            total_score = base_score + resonance_boost + flow_boost + doctrine_boost
            
            return max(0.0, min(1.0, total_score))
            
        except Exception as e:
            logger.error(f"Error calculating organic intelligence score: {e}")
            return 0.5
    
    # Helper methods for status and assessment
    async def _get_doctrine_integration_status(self) -> Dict[str, Any]:
        """Get doctrine integration status"""
        return {
            'integration_active': True,
            'doctrine_cache_size': len(self.execution_doctrine_integration.doctrine_cache),
            'evolution_history_size': len(self.execution_doctrine_integration.doctrine_evolution_history),
            'contraindication_cache_size': len(self.execution_doctrine_integration.contraindication_cache)
        }
    
    def _get_capabilities_status(self) -> Dict[str, Any]:
        """Get capabilities status"""
        return {
            'total_capabilities': len([cap for cap in self.organic_capabilities.__dict__.values() if cap]),
            'active_capabilities': self.organic_capabilities.__dict__,
            'capability_evolution_count': len(self.capability_evolution)
        }
    
    async def _get_intelligence_flow_status(self) -> Dict[str, Any]:
        """Get intelligence flow status"""
        return {
            'data_driven_heartbeat': True,
            'organic_coordination': True,
            'resonance_enhancement': True,
            'uncertainty_exploration': True,
            'motif_evolution': True,
            'cross_team_awareness': True,
            'strategic_insight_consumption': True,
            'doctrine_integration': True
        }
    
    async def _assess_experiment_intelligence_impact(self, experiment_results: Dict[str, Any], doctrine_contribution: str) -> Dict[str, Any]:
        """Assess experiment impact on organic intelligence"""
        return {
            'experiment_success': experiment_results.get('success', False),
            'doctrine_contribution_id': doctrine_contribution,
            'intelligence_enhancement': True,
            'learning_acceleration': True,
            'capability_evolution': True
        }
    
    async def _track_experiment_learning(self, experiment_results: Dict[str, Any], intelligence_impact: Dict[str, Any]):
        """Track experiment learning"""
        # Implementation for tracking experiment learning
        pass
    
    async def _extract_experiment_learning_insights(self, experiment_results: Dict[str, Any]) -> List[str]:
        """Extract learning insights from experiment results"""
        insights = []
        
        if experiment_results.get('success', False):
            insights.append("Experiment successful - valuable execution pattern identified")
        
        if experiment_results.get('novelty_score', 0) > 0.7:
            insights.append("High novelty experiment - new execution approach discovered")
        
        if experiment_results.get('generality_score', 0) > 0.7:
            insights.append("High generality experiment - broadly applicable execution pattern")
        
        return insights
    
    async def _handle_contraindicated_execution(self, approved_plan: Dict[str, Any], doctrine_guidance: Dict[str, Any]) -> OrganicExecutionIntelligence:
        """Handle contraindicated execution"""
        return await self._create_default_organic_intelligence_state()
    
    async def _handle_unsafe_experiment(self, experiment_insights: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unsafe experiment"""
        return {
            'experiment_safe': False,
            'contraindication_reason': 'Experiment contraindicated by doctrine',
            'experiment_insights': experiment_insights
        }
    
    async def _handle_organic_intelligence_error(self, error: Exception, market_data: Dict[str, Any], approved_plan: Dict[str, Any]) -> OrganicExecutionIntelligence:
        """Handle organic intelligence errors"""
        return await self._create_default_organic_intelligence_state()
    
    async def _create_default_organic_intelligence_state(self) -> OrganicExecutionIntelligence:
        """Create default organic intelligence state"""
        return OrganicExecutionIntelligence(
            execution_capabilities=self.organic_capabilities,
            doctrine_guidance={},
            cil_influence={},
            coordination_state={},
            intelligence_flow={},
            resonance_metrics={'phi': 0.5, 'rho': 0.5, 'theta': 0.5},
            uncertainty_analysis={},
            motif_contributions=[],
            cross_team_insights=[],
            strategic_insights=[],
            timestamp=datetime.now()
        )
    
    # Database interaction methods (to be implemented based on existing patterns)
    async def _publish_strand_to_database(self, strand: Dict[str, Any]) -> str:
        """Publish strand to AD_strands table"""
        # Implementation will follow existing database patterns
        return f"strand_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
