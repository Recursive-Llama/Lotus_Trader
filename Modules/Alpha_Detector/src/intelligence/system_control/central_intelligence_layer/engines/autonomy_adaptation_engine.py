"""
CIL Autonomy & Adaptation Engine

Section 6: Autonomy & Adaptation (CIL)
- Unified Engine (Code + LLM working together)
- Self-Reflection (CIL reviews its own orchestration choices)
- Adaptive Focus (shifts exploration budgets dynamically)
- Doctrine Evolution (adapts doctrine as lessons accumulate)
- Agent Calibration (adjusts agent autonomy, tunes thresholds)
- Resilience to Change (adapts search compass as market regimes shift)

Vector Search Integration:
- Vector analysis for adaptive focus and agent calibration
- Vector embeddings for self-reflection and orchestration review
- Vector search for resilience patterns and regime adaptation
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.llm_integration.prompt_manager import PromptManager
from src.llm_integration.database_driven_context_system import DatabaseDrivenContextSystem


class AutonomyLevel(Enum):
    """Agent autonomy levels"""
    STRICT = "strict"
    BOUNDED = "bounded"
    EXPLORATORY = "exploratory"


class AdaptationType(Enum):
    """Adaptation types"""
    FOCUS_SHIFT = "focus_shift"
    THRESHOLD_ADJUSTMENT = "threshold_adjustment"
    BUDGET_REALLOCATION = "budget_reallocation"
    DOCTRINE_UPDATE = "doctrine_update"
    AGENT_CALIBRATION = "agent_calibration"


@dataclass
class SelfReflection:
    """Self-reflection result"""
    reflection_id: str
    reflection_type: str
    orchestration_choices: Dict[str, Any]
    performance_metrics: Dict[str, float]
    improvement_areas: List[str]
    adaptation_recommendations: List[str]
    confidence_level: float
    created_at: datetime


@dataclass
class AdaptiveFocus:
    """Adaptive focus configuration"""
    focus_id: str
    pattern_family: str
    exploration_budget: float
    priority_score: float
    adaptation_rationale: str
    time_horizon: str
    success_metrics: Dict[str, float]
    created_at: datetime


@dataclass
class AgentCalibration:
    """Agent calibration settings"""
    agent_id: str
    autonomy_level: AutonomyLevel
    threshold_settings: Dict[str, float]
    exploration_budget: float
    performance_targets: Dict[str, float]
    calibration_rationale: str
    created_at: datetime


class AutonomyAdaptationEngine:
    """
    CIL Autonomy & Adaptation Engine
    
    Responsibilities:
    1. Unified Engine (Code + LLM working together)
    2. Self-Reflection (CIL reviews its own orchestration choices)
    3. Adaptive Focus (shifts exploration budgets dynamically)
    4. Doctrine Evolution (adapts doctrine as lessons accumulate)
    5. Agent Calibration (adjusts agent autonomy, tunes thresholds)
    6. Resilience to Change (adapts search compass as market regimes shift)
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        self.context_system = DatabaseDrivenContextSystem(supabase_manager)
        
        # Adaptation configuration
        self.reflection_interval_hours = 6
        self.adaptation_threshold = 0.7
        self.autonomy_adjustment_rate = 0.1
        self.focus_shift_threshold = 0.8
        self.doctrine_evolution_rate = 0.05
        
        # Agent capabilities and current settings
        self.agent_capabilities = {
            'raw_data_intelligence': {'max_autonomy': AutonomyLevel.EXPLORATORY, 'current_budget': 0.3},
            'indicator_intelligence': {'max_autonomy': AutonomyLevel.BOUNDED, 'current_budget': 0.25},
            'pattern_intelligence': {'max_autonomy': AutonomyLevel.EXPLORATORY, 'current_budget': 0.25},
            'system_control': {'max_autonomy': AutonomyLevel.STRICT, 'current_budget': 0.2}
        }
        
    async def process_autonomy_adaptation(self, learning_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process autonomy and adaptation based on learning results
        
        Args:
            learning_results: Output from LearningFeedbackEngine
            
        Returns:
            Dict containing autonomy and adaptation results
        """
        try:
            # Perform adaptation operations in parallel
            results = await asyncio.gather(
                self.perform_self_reflection(learning_results),
                self.adapt_focus_dynamically(learning_results),
                self.evolve_doctrine(learning_results),
                self.calibrate_agents(learning_results),
                self.assess_resilience_to_change(learning_results),
                return_exceptions=True
            )
            
            # Structure adaptation results
            adaptation_results = {
                'self_reflections': results[0] if not isinstance(results[0], Exception) else [],
                'adaptive_focus': results[1] if not isinstance(results[1], Exception) else [],
                'doctrine_evolution': results[2] if not isinstance(results[2], Exception) else [],
                'agent_calibrations': results[3] if not isinstance(results[3], Exception) else [],
                'resilience_assessment': results[4] if not isinstance(results[4], Exception) else {},
                'adaptation_timestamp': datetime.now(timezone.utc),
                'adaptation_errors': [str(r) for r in results if isinstance(r, Exception)]
            }
            
            # Publish adaptation results as CIL strand
            await self._publish_adaptation_results(adaptation_results)
            
            return adaptation_results
            
        except Exception as e:
            print(f"Error processing autonomy adaptation: {e}")
            return {'error': str(e), 'adaptation_timestamp': datetime.now(timezone.utc)}
    
    async def perform_self_reflection(self, learning_results: Dict[str, Any]) -> List[SelfReflection]:
        """
        Perform self-reflection on orchestration choices
        
        Returns:
            List of SelfReflection objects
        """
        try:
            reflections = []
            
            # Get learning components for reflection
            improvement_assessment = learning_results.get('improvement_assessment', {})
            improvement_metrics = improvement_assessment.get('improvement_metrics', {})
            system_sharpening = improvement_assessment.get('system_sharpening', {})
            
            # Reflect on orchestration performance
            orchestration_choices = {
                'experiment_ideas_generated': learning_results.get('experiment_ideas', []),
                'experiment_designs_created': learning_results.get('experiment_designs', []),
                'experiment_assignments_made': learning_results.get('experiment_assignments', []),
                'doctrine_updates_generated': learning_results.get('doctrine_updates', [])
            }
            
            # Calculate performance metrics
            performance_metrics = {
                'learning_rate': improvement_metrics.get('system_learning_rate', 0.0),
                'doctrine_evolution_rate': improvement_metrics.get('doctrine_evolution_rate', 0.0),
                'pattern_discovery_rate': improvement_metrics.get('pattern_discovery_rate', 0.0),
                'knowledge_retention_rate': improvement_metrics.get('knowledge_retention_rate', 0.0),
                'accuracy_improvement': system_sharpening.get('accuracy_improvement', 0.0),
                'efficiency_improvement': system_sharpening.get('efficiency_improvement', 0.0),
                'novelty_improvement': system_sharpening.get('novelty_improvement', 0.0),
                'resilience_improvement': system_sharpening.get('resilience_improvement', 0.0)
            }
            
            # Identify improvement areas
            improvement_areas = self._identify_improvement_areas(performance_metrics)
            
            # Generate adaptation recommendations
            adaptation_recommendations = await self._generate_adaptation_recommendations(
                performance_metrics, improvement_areas
            )
            
            # Calculate confidence level
            confidence_level = self._calculate_reflection_confidence(performance_metrics)
            
            # Create self-reflection
            reflection = SelfReflection(
                reflection_id=f"REFLECTION_{int(datetime.now().timestamp())}",
                reflection_type="orchestration_review",
                orchestration_choices=orchestration_choices,
                performance_metrics=performance_metrics,
                improvement_areas=improvement_areas,
                adaptation_recommendations=adaptation_recommendations,
                confidence_level=confidence_level,
                created_at=datetime.now(timezone.utc)
            )
            
            reflections.append(reflection)
            
            return reflections
            
        except Exception as e:
            print(f"Error performing self-reflection: {e}")
            return []
    
    async def adapt_focus_dynamically(self, learning_results: Dict[str, Any]) -> List[AdaptiveFocus]:
        """
        Adapt focus dynamically based on learning results
        
        Returns:
            List of AdaptiveFocus objects
        """
        try:
            adaptive_focuses = []
            
            # Get learning components
            improvement_assessment = learning_results.get('improvement_assessment', {})
            improvement_metrics = improvement_assessment.get('improvement_metrics', {})
            system_sharpening = improvement_assessment.get('system_sharpening', {})
            
            # Analyze pattern families for focus adaptation
            pattern_families = self._analyze_pattern_families(learning_results)
            
            for family, metrics in pattern_families.items():
                # Calculate priority score
                priority_score = self._calculate_family_priority(metrics, system_sharpening)
                
                # Determine if focus should be adapted
                if priority_score > self.focus_shift_threshold:
                    # Calculate new exploration budget
                    current_budget = self.agent_capabilities.get(family, {}).get('current_budget', 0.25)
                    new_budget = self._calculate_adaptive_budget(current_budget, priority_score)
                    
                    # Generate adaptation rationale
                    adaptation_rationale = self._generate_focus_rationale(family, metrics, priority_score)
                    
                    # Define success metrics
                    success_metrics = {
                        'learning_rate': improvement_metrics.get('system_learning_rate', 0.0),
                        'pattern_discovery_rate': improvement_metrics.get('pattern_discovery_rate', 0.0),
                        'accuracy_improvement': system_sharpening.get('accuracy_improvement', 0.0)
                    }
                    
                    # Create adaptive focus
                    adaptive_focus = AdaptiveFocus(
                        focus_id=f"FOCUS_{family}_{int(datetime.now().timestamp())}",
                        pattern_family=family,
                        exploration_budget=new_budget,
                        priority_score=priority_score,
                        adaptation_rationale=adaptation_rationale,
                        time_horizon="24_hours",
                        success_metrics=success_metrics,
                        created_at=datetime.now(timezone.utc)
                    )
                    
                    adaptive_focuses.append(adaptive_focus)
            
            return adaptive_focuses
            
        except Exception as e:
            print(f"Error adapting focus dynamically: {e}")
            return []
    
    async def evolve_doctrine(self, learning_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evolve doctrine based on accumulated lessons
        
        Returns:
            List of doctrine evolution updates
        """
        try:
            doctrine_evolutions = []
            
            # Get doctrine updates from learning results
            doctrine_updates = learning_results.get('doctrine_updates', [])
            
            for update in doctrine_updates:
                # Analyze doctrine update for evolution
                evolution_type = self._determine_doctrine_evolution_type(update)
                
                if evolution_type:
                    # Create doctrine evolution
                    evolution = {
                        'evolution_id': f"DOCTRINE_EVOL_{int(datetime.now().timestamp())}",
                        'evolution_type': evolution_type,
                        'pattern_family': update.pattern_family,
                        'rationale': update.rationale,
                        'evidence': update.evidence,
                        'confidence_level': update.confidence_level,
                        'evolution_rate': self.doctrine_evolution_rate,
                        'created_at': datetime.now(timezone.utc)
                    }
                    
                    doctrine_evolutions.append(evolution)
            
            return doctrine_evolutions
            
        except Exception as e:
            print(f"Error evolving doctrine: {e}")
            return []
    
    async def calibrate_agents(self, learning_results: Dict[str, Any]) -> List[AgentCalibration]:
        """
        Calibrate agent autonomy and thresholds
        
        Returns:
            List of AgentCalibration objects
        """
        try:
            agent_calibrations = []
            
            # Get learning components
            improvement_assessment = learning_results.get('improvement_assessment', {})
            system_sharpening = improvement_assessment.get('system_sharpening', {})
            
            # Calibrate each agent
            for agent_id, capabilities in self.agent_capabilities.items():
                # Calculate performance metrics for agent
                agent_metrics = self._calculate_agent_metrics(agent_id, learning_results)
                
                # Determine if calibration is needed
                if self._needs_calibration(agent_metrics, system_sharpening):
                    # Calculate new autonomy level
                    new_autonomy = self._calculate_adaptive_autonomy(agent_id, agent_metrics)
                    
                    # Calculate new threshold settings
                    new_thresholds = self._calculate_adaptive_thresholds(agent_id, agent_metrics)
                    
                    # Calculate new exploration budget
                    new_budget = self._calculate_adaptive_budget(
                        capabilities['current_budget'], 
                        agent_metrics.get('performance_score', 0.5)
                    )
                    
                    # Define performance targets
                    performance_targets = {
                        'accuracy_target': 0.8,
                        'efficiency_target': 0.7,
                        'novelty_target': 0.6,
                        'resilience_target': 0.75
                    }
                    
                    # Generate calibration rationale
                    calibration_rationale = self._generate_calibration_rationale(
                        agent_id, agent_metrics, new_autonomy, new_thresholds
                    )
                    
                    # Create agent calibration
                    calibration = AgentCalibration(
                        agent_id=agent_id,
                        autonomy_level=new_autonomy,
                        threshold_settings=new_thresholds,
                        exploration_budget=new_budget,
                        performance_targets=performance_targets,
                        calibration_rationale=calibration_rationale,
                        created_at=datetime.now(timezone.utc)
                    )
                    
                    agent_calibrations.append(calibration)
            
            return agent_calibrations
            
        except Exception as e:
            print(f"Error calibrating agents: {e}")
            return []
    
    async def assess_resilience_to_change(self, learning_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess resilience to change and market regime shifts
        
        Returns:
            Dict containing resilience assessment
        """
        try:
            # Get learning components
            improvement_assessment = learning_results.get('improvement_assessment', {})
            improvement_metrics = improvement_assessment.get('improvement_metrics', {})
            system_sharpening = improvement_assessment.get('system_sharpening', {})
            
            # Calculate resilience metrics
            resilience_metrics = {
                'adaptation_rate': improvement_metrics.get('doctrine_evolution_rate', 0.0),
                'learning_persistence': improvement_metrics.get('knowledge_retention_rate', 0.0),
                'pattern_stability': system_sharpening.get('resilience_improvement', 0.0),
                'system_flexibility': system_sharpening.get('efficiency_improvement', 0.0)
            }
            
            # Assess regime shift resilience
            regime_resilience = self._assess_regime_shift_resilience(resilience_metrics)
            
            # Generate resilience recommendations
            resilience_recommendations = await self._generate_resilience_recommendations(
                resilience_metrics, regime_resilience
            )
            
            return {
                'resilience_metrics': resilience_metrics,
                'regime_resilience': regime_resilience,
                'resilience_recommendations': resilience_recommendations,
                'assessment_timestamp': datetime.now(timezone.utc)
            }
            
        except Exception as e:
            print(f"Error assessing resilience to change: {e}")
            return {'error': str(e), 'assessment_timestamp': datetime.now(timezone.utc)}
    
    def _identify_improvement_areas(self, performance_metrics: Dict[str, float]) -> List[str]:
        """Identify areas for improvement"""
        improvement_areas = []
        
        if performance_metrics.get('learning_rate', 0.0) < 0.5:
            improvement_areas.append('learning_rate')
        
        if performance_metrics.get('doctrine_evolution_rate', 0.0) < 0.3:
            improvement_areas.append('doctrine_evolution')
        
        if performance_metrics.get('pattern_discovery_rate', 0.0) < 0.4:
            improvement_areas.append('pattern_discovery')
        
        if performance_metrics.get('accuracy_improvement', 0.0) < 0.6:
            improvement_areas.append('accuracy')
        
        if performance_metrics.get('efficiency_improvement', 0.0) < 0.5:
            improvement_areas.append('efficiency')
        
        return improvement_areas
    
    async def _generate_adaptation_recommendations(self, performance_metrics: Dict[str, float], 
                                                 improvement_areas: List[str]) -> List[str]:
        """Generate adaptation recommendations"""
        recommendations = []
        
        for area in improvement_areas:
            if area == 'learning_rate':
                recommendations.append("Increase learning rate by exploring more novel patterns")
            elif area == 'doctrine_evolution':
                recommendations.append("Accelerate doctrine evolution by promoting more patterns")
            elif area == 'pattern_discovery':
                recommendations.append("Enhance pattern discovery through cross-agent collaboration")
            elif area == 'accuracy':
                recommendations.append("Improve accuracy by focusing on high-confidence patterns")
            elif area == 'efficiency':
                recommendations.append("Enhance efficiency by consolidating similar patterns")
        
        return recommendations
    
    def _calculate_reflection_confidence(self, performance_metrics: Dict[str, float]) -> float:
        """Calculate confidence level for self-reflection"""
        # Base confidence on overall performance
        avg_performance = sum(performance_metrics.values()) / len(performance_metrics)
        return min(avg_performance, 1.0)
    
    def _analyze_pattern_families(self, learning_results: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Analyze pattern families for focus adaptation"""
        # This would typically analyze the learning results to identify pattern families
        # For now, return mock data
        return {
            'divergence': {'performance': 0.8, 'novelty': 0.7, 'persistence': 0.9},
            'volume_analysis': {'performance': 0.6, 'novelty': 0.8, 'persistence': 0.7},
            'correlation_analysis': {'performance': 0.7, 'novelty': 0.6, 'persistence': 0.8},
            'pattern_recognition': {'performance': 0.9, 'novelty': 0.9, 'persistence': 0.8}
        }
    
    def _calculate_family_priority(self, metrics: Dict[str, float], system_sharpening: Dict[str, Any]) -> float:
        """Calculate priority score for pattern family"""
        # Weighted combination of metrics
        performance = metrics.get('performance', 0.0)
        novelty = metrics.get('novelty', 0.0)
        persistence = metrics.get('persistence', 0.0)
        
        # Include system sharpening metrics
        accuracy_improvement = system_sharpening.get('accuracy_improvement', 0.0)
        novelty_improvement = system_sharpening.get('novelty_improvement', 0.0)
        
        # Calculate priority score
        priority = (performance * 0.3 + novelty * 0.3 + persistence * 0.2 + 
                   accuracy_improvement * 0.1 + novelty_improvement * 0.1)
        
        return min(priority, 1.0)
    
    def _calculate_adaptive_budget(self, current_budget: float, priority_score: float) -> float:
        """Calculate adaptive exploration budget"""
        # Adjust budget based on priority score
        adjustment = (priority_score - 0.5) * self.autonomy_adjustment_rate
        new_budget = current_budget + adjustment
        
        # Ensure budget stays within bounds
        return max(0.1, min(0.5, new_budget))
    
    def _generate_focus_rationale(self, family: str, metrics: Dict[str, float], priority_score: float) -> str:
        """Generate rationale for focus adaptation"""
        return f"Focus adapted for {family} based on priority score {priority_score:.2f} " \
               f"(performance: {metrics.get('performance', 0.0):.2f}, " \
               f"novelty: {metrics.get('novelty', 0.0):.2f}, " \
               f"persistence: {metrics.get('persistence', 0.0):.2f})"
    
    def _determine_doctrine_evolution_type(self, update: Any) -> Optional[str]:
        """Determine doctrine evolution type"""
        update_type = getattr(update, 'update_type', 'unknown')
        
        if update_type == 'promote':
            return 'doctrine_affirmation'
        elif update_type == 'retire':
            return 'doctrine_retirement'
        elif update_type == 'refine':
            return 'doctrine_refinement'
        elif update_type == 'contraindicate':
            return 'doctrine_contraindication'
        else:
            return None
    
    def _calculate_agent_metrics(self, agent_id: str, learning_results: Dict[str, Any]) -> Dict[str, float]:
        """Calculate performance metrics for agent"""
        # This would typically analyze agent-specific performance
        # For now, return mock metrics
        return {
            'performance_score': 0.7,
            'accuracy': 0.8,
            'efficiency': 0.6,
            'novelty': 0.7,
            'resilience': 0.75
        }
    
    def _needs_calibration(self, agent_metrics: Dict[str, float], system_sharpening: Dict[str, Any]) -> bool:
        """Check if agent needs calibration"""
        performance_score = agent_metrics.get('performance_score', 0.0)
        return performance_score < self.adaptation_threshold
    
    def _calculate_adaptive_autonomy(self, agent_id: str, agent_metrics: Dict[str, float]) -> AutonomyLevel:
        """Calculate adaptive autonomy level for agent"""
        performance_score = agent_metrics.get('performance_score', 0.0)
        
        if performance_score > 0.8:
            return AutonomyLevel.EXPLORATORY
        elif performance_score > 0.6:
            return AutonomyLevel.BOUNDED
        else:
            return AutonomyLevel.STRICT
    
    def _calculate_adaptive_thresholds(self, agent_id: str, agent_metrics: Dict[str, float]) -> Dict[str, float]:
        """Calculate adaptive threshold settings for agent"""
        performance_score = agent_metrics.get('performance_score', 0.0)
        
        # Adjust thresholds based on performance
        base_threshold = 0.7
        adjustment = (performance_score - 0.5) * 0.2
        
        return {
            'confidence_threshold': base_threshold + adjustment,
            'similarity_threshold': base_threshold + adjustment,
            'success_threshold': base_threshold + adjustment
        }
    
    def _generate_calibration_rationale(self, agent_id: str, agent_metrics: Dict[str, float], 
                                      autonomy_level: AutonomyLevel, thresholds: Dict[str, float]) -> str:
        """Generate rationale for agent calibration"""
        return f"Agent {agent_id} calibrated to {autonomy_level.value} autonomy " \
               f"based on performance score {agent_metrics.get('performance_score', 0.0):.2f}. " \
               f"Thresholds adjusted to {thresholds}"
    
    def _assess_regime_shift_resilience(self, resilience_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Assess resilience to regime shifts"""
        adaptation_rate = resilience_metrics.get('adaptation_rate', 0.0)
        learning_persistence = resilience_metrics.get('learning_persistence', 0.0)
        pattern_stability = resilience_metrics.get('pattern_stability', 0.0)
        system_flexibility = resilience_metrics.get('system_flexibility', 0.0)
        
        # Calculate overall resilience score
        resilience_score = (adaptation_rate + learning_persistence + pattern_stability + system_flexibility) / 4
        
        return {
            'resilience_score': resilience_score,
            'adaptation_capability': adaptation_rate,
            'learning_persistence': learning_persistence,
            'pattern_stability': pattern_stability,
            'system_flexibility': system_flexibility
        }
    
    async def _generate_resilience_recommendations(self, resilience_metrics: Dict[str, float], 
                                                 regime_resilience: Dict[str, Any]) -> List[str]:
        """Generate resilience recommendations"""
        recommendations = []
        
        resilience_score = regime_resilience.get('resilience_score', 0.0)
        
        if resilience_score < 0.6:
            recommendations.append("Improve system resilience through enhanced adaptation mechanisms")
        
        if resilience_metrics.get('adaptation_rate', 0.0) < 0.5:
            recommendations.append("Increase adaptation rate for better regime shift response")
        
        if resilience_metrics.get('learning_persistence', 0.0) < 0.7:
            recommendations.append("Enhance learning persistence for long-term stability")
        
        return recommendations
    
    async def _publish_adaptation_results(self, adaptation_results: Dict[str, Any]):
        """Publish adaptation results as CIL strand"""
        try:
            # Create CIL adaptation strand
            cil_strand = {
                'id': f"cil_autonomy_adaptation_{int(datetime.now().timestamp())}",
                'kind': 'cil_autonomy_adaptation',
                'module': 'alpha',
                'agent_id': 'central_intelligence_layer',
                'cil_team_member': 'autonomy_adaptation_engine',
                'symbol': 'SYSTEM',
                'timeframe': 'system',
                'session_bucket': 'GLOBAL',
                'regime': 'system',
                'tags': ['agent:central_intelligence:autonomy_adaptation_engine:adaptation_complete'],
                'module_intelligence': {
                    'adaptation_type': 'autonomy_adaptation',
                    'self_reflections_count': len(adaptation_results.get('self_reflections', [])),
                    'adaptive_focus_count': len(adaptation_results.get('adaptive_focus', [])),
                    'doctrine_evolutions_count': len(adaptation_results.get('doctrine_evolution', [])),
                    'agent_calibrations_count': len(adaptation_results.get('agent_calibrations', [])),
                    'resilience_assessment': adaptation_results.get('resilience_assessment', {}),
                    'adaptation_errors': adaptation_results.get('adaptation_errors', [])
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
            print(f"Error publishing adaptation results: {e}")


# Example usage and testing
async def main():
    """Example usage of AutonomyAdaptationEngine"""
    from src.utils.supabase_manager import SupabaseManager
    from src.llm_integration.openrouter_client import OpenRouterClient
    
    # Initialize components
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    
    # Create autonomy adaptation engine
    adaptation_engine = AutonomyAdaptationEngine(supabase_manager, llm_client)
    
    # Mock learning results
    learning_results = {
        'improvement_assessment': {
            'improvement_metrics': {
                'system_learning_rate': 0.8,
                'doctrine_evolution_rate': 0.6,
                'pattern_discovery_rate': 0.7,
                'knowledge_retention_rate': 0.9
            },
            'system_sharpening': {
                'accuracy_improvement': 0.8,
                'efficiency_improvement': 0.7,
                'novelty_improvement': 0.6,
                'resilience_improvement': 0.75
            }
        },
        'doctrine_updates': [],
        'experiment_ideas': [],
        'experiment_designs': [],
        'experiment_assignments': []
    }
    
    # Process autonomy adaptation
    adaptation_results = await adaptation_engine.process_autonomy_adaptation(learning_results)
    
    print("CIL Autonomy & Adaptation Results:")
    print(f"Self Reflections: {len(adaptation_results.get('self_reflections', []))}")
    print(f"Adaptive Focus: {len(adaptation_results.get('adaptive_focus', []))}")
    print(f"Doctrine Evolutions: {len(adaptation_results.get('doctrine_evolution', []))}")
    print(f"Agent Calibrations: {len(adaptation_results.get('agent_calibrations', []))}")
    print(f"Resilience Assessment: {adaptation_results.get('resilience_assessment', {})}")


if __name__ == "__main__":
    asyncio.run(main())
