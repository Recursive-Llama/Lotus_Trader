"""
Enhanced Trader Agent Base

Enhanced base class for organically CIL-influenced trader agents that enables
organic intelligence coordination through resonance, uncertainty handling, and
strategic insight consumption.

Key Features:
- Organic CIL influence integration
- Execution with organic influence through resonance and insights
- Execution motif contribution for organic evolution
- Execution resonance contribution for organic evolution
- Data-driven heartbeat response
- Cross-team coordination through AD_strands
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .execution_resonance_integration import ExecutionResonanceIntegration
from .execution_uncertainty_handler import ExecutionUncertaintyHandler

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """Context for execution with organic influence"""
    market_data: Dict[str, Any]
    approved_plan: Dict[str, Any]
    cil_insights: List[Dict[str, Any]]
    resonance_metrics: Dict[str, float]
    uncertainty_analysis: Dict[str, Any]
    motif_integration: Dict[str, Any]
    timestamp: datetime


class EnhancedTraderAgent(ABC):
    """Enhanced base class for organically CIL-influenced trader agents"""
    
    def __init__(self, agent_name: str, supabase_manager, llm_client):
        self.agent_name = agent_name
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        
        # Initialize organic intelligence components
        self.execution_resonance_integration = ExecutionResonanceIntegration(
            supabase_manager, llm_client
        )
        self.execution_uncertainty_handler = ExecutionUncertaintyHandler(
            supabase_manager, llm_client
        )
        
        # Initialize motif and insight components (to be added in Phase 2)
        self.execution_motif_integration = None  # Will be initialized in Phase 2
        self.strategic_execution_insight_consumer = None  # Will be initialized in Phase 2
        
        # Agent state
        self.is_active = False
        self.last_execution_time = None
        self.execution_count = 0
        self.resonance_history = []
        
        logger.info(f"Initialized Enhanced Trader Agent: {agent_name}")
    
    async def execute_with_organic_influence(self, market_data: Dict[str, Any], approved_plan: Dict[str, Any]):
        """
        Execute with natural CIL influence through resonance and insights
        
        Args:
            market_data: Current market data
            approved_plan: Approved trading plan from Decision Maker
        """
        try:
            # Create execution context
            execution_context = await self._create_execution_context(market_data, approved_plan)
            
            # Apply execution resonance-enhanced scoring
            resonance_enhanced_plan = await self._apply_resonance_enhanced_scoring(
                approved_plan, execution_context.resonance_metrics
            )
            
            # Consume valuable CIL execution insights naturally
            cil_influenced_plan = await self._consume_cil_execution_insights(
                resonance_enhanced_plan, execution_context.cil_insights
            )
            
            # Handle execution uncertainty-driven exploration
            uncertainty_aware_plan = await self._handle_execution_uncertainty_exploration(
                cil_influenced_plan, execution_context.uncertainty_analysis
            )
            
            # Execute the plan with organic influence
            execution_result = await self._execute_plan_with_organic_influence(
                uncertainty_aware_plan, execution_context
            )
            
            # Contribute to execution motif creation
            await self._contribute_to_execution_motif(execution_result, execution_context)
            
            # Publish execution results with resonance values
            await self._publish_execution_results(execution_result, execution_context)
            
            # Update agent state
            self._update_agent_state(execution_result)
            
            logger.info(f"Executed with organic influence: {self.agent_name}, "
                       f"resonance: {execution_context.resonance_metrics.get('phi', 0):.3f}")
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Error executing with organic influence: {e}")
            return await self._handle_execution_error(e, market_data, approved_plan)
    
    async def contribute_to_execution_motif(self, execution_pattern_data: Dict[str, Any]):
        """
        Contribute execution pattern data to motif creation for organic evolution
        
        Args:
            execution_pattern_data: Execution pattern data to contribute
        """
        try:
            # Extract execution pattern invariants
            invariants = await self._extract_execution_pattern_invariants(execution_pattern_data)
            
            # Identify execution failure conditions
            failure_conditions = await self._identify_execution_failure_conditions(execution_pattern_data)
            
            # Provide execution mechanism hypotheses
            mechanism_hypotheses = await self._provide_execution_mechanism_hypotheses(
                execution_pattern_data, invariants, failure_conditions
            )
            
            # Create execution motif strand with resonance values
            motif_strand = await self._create_execution_motif_strand(
                invariants, failure_conditions, mechanism_hypotheses, execution_pattern_data
            )
            
            # Publish motif strand to AD_strands
            motif_id = await self._publish_motif_strand(motif_strand)
            
            logger.info(f"Contributed to execution motif: {motif_id}, "
                       f"invariants: {len(invariants)}, hypotheses: {len(mechanism_hypotheses)}")
            
            return motif_id
            
        except Exception as e:
            logger.error(f"Error contributing to execution motif: {e}")
            return ""
    
    async def calculate_execution_resonance_contribution(self, execution_strand_data: Dict[str, Any]):
        """
        Calculate execution resonance contribution for organic evolution
        
        Args:
            execution_strand_data: Execution strand data for resonance calculation
        """
        try:
            # Calculate execution φ, ρ values
            resonance_metrics = await self.execution_resonance_integration.calculate_execution_resonance(
                execution_strand_data
            )
            
            # Update execution telemetry
            await self._update_execution_telemetry(resonance_metrics)
            
            # Contribute to global execution θ field
            await self._contribute_to_global_execution_theta(resonance_metrics)
            
            # Enable organic execution influence through resonance
            await self._enable_organic_execution_influence(resonance_metrics)
            
            # Store resonance history
            self.resonance_history.append({
                'timestamp': datetime.now(),
                'metrics': resonance_metrics,
                'strand_data': execution_strand_data
            })
            
            logger.info(f"Calculated execution resonance contribution: "
                       f"φ={resonance_metrics.get('phi', 0):.3f}, "
                       f"ρ={resonance_metrics.get('rho', 0):.3f}")
            
            return resonance_metrics
            
        except Exception as e:
            logger.error(f"Error calculating execution resonance contribution: {e}")
            return {}
    
    async def start_organic_execution_loop(self):
        """Start the organic execution loop with data-driven heartbeat"""
        try:
            self.is_active = True
            logger.info(f"Starting organic execution loop for {self.agent_name}")
            
            while self.is_active:
                try:
                    # Wait for data-driven heartbeat or triggers
                    await self._wait_for_execution_trigger()
                    
                    # Check for new market data and approved plans
                    market_data, approved_plans = await self._check_for_execution_triggers()
                    
                    if market_data and approved_plans:
                        # Execute with organic influence for each approved plan
                        for approved_plan in approved_plans:
                            await self.execute_with_organic_influence(market_data, approved_plan)
                    
                    # Handle any pending uncertainty exploration
                    await self._handle_pending_uncertainty_exploration()
                    
                except Exception as e:
                    logger.error(f"Error in organic execution loop: {e}")
                    await asyncio.sleep(1)  # Brief pause before retry
                    
        except Exception as e:
            logger.error(f"Error starting organic execution loop: {e}")
        finally:
            self.is_active = False
            logger.info(f"Stopped organic execution loop for {self.agent_name}")
    
    async def stop_organic_execution_loop(self):
        """Stop the organic execution loop"""
        self.is_active = False
        logger.info(f"Stopping organic execution loop for {self.agent_name}")
    
    # Abstract methods to be implemented by specific trader agents
    @abstractmethod
    async def _execute_specific_plan(self, plan: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute the specific trading plan (to be implemented by subclasses)"""
        pass
    
    @abstractmethod
    async def _get_agent_specific_metrics(self) -> Dict[str, Any]:
        """Get agent-specific execution metrics"""
        pass
    
    # Helper methods for organic influence integration
    async def _create_execution_context(self, market_data: Dict[str, Any], approved_plan: Dict[str, Any]) -> ExecutionContext:
        """Create execution context with organic influence data"""
        try:
            # Get CIL insights (will be implemented in Phase 2)
            cil_insights = await self._get_cil_execution_insights(approved_plan)
            
            # Calculate resonance metrics
            resonance_metrics = await self.execution_resonance_integration.calculate_execution_resonance({
                'market_data': market_data,
                'approved_plan': approved_plan,
                'agent_name': self.agent_name
            })
            
            # Detect execution uncertainty
            uncertainty_analysis = await self.execution_uncertainty_handler.detect_execution_uncertainty({
                'market_data': market_data,
                'approved_plan': approved_plan,
                'resonance_metrics': resonance_metrics
            })
            
            # Get motif integration data (will be implemented in Phase 2)
            motif_integration = await self._get_motif_integration_data(approved_plan)
            
            return ExecutionContext(
                market_data=market_data,
                approved_plan=approved_plan,
                cil_insights=cil_insights,
                resonance_metrics=resonance_metrics,
                uncertainty_analysis=uncertainty_analysis,
                motif_integration=motif_integration,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error creating execution context: {e}")
            return ExecutionContext(
                market_data=market_data,
                approved_plan=approved_plan,
                cil_insights=[],
                resonance_metrics={},
                uncertainty_analysis={},
                motif_integration={},
                timestamp=datetime.now()
            )
    
    async def _apply_resonance_enhanced_scoring(self, plan: Dict[str, Any], resonance_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Apply resonance-enhanced scoring to the execution plan"""
        try:
            # Get base execution score
            base_score = plan.get('execution_score', 0.5)
            
            # Calculate resonance boost
            phi = resonance_metrics.get('phi', 0.5)
            rho = resonance_metrics.get('rho', 0.5)
            resonance_boost = (phi + rho) / 2.0
            
            # Apply enhancement
            enhanced_score = base_score * (1 + resonance_boost * 0.2)  # 20% max boost
            
            # Update plan with enhanced scoring
            enhanced_plan = plan.copy()
            enhanced_plan['execution_score'] = enhanced_score
            enhanced_plan['resonance_boost'] = resonance_boost
            enhanced_plan['resonance_metrics'] = resonance_metrics
            
            return enhanced_plan
            
        except Exception as e:
            logger.error(f"Error applying resonance-enhanced scoring: {e}")
            return plan
    
    async def _consume_cil_execution_insights(self, plan: Dict[str, Any], cil_insights: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Consume valuable CIL execution insights naturally"""
        try:
            # This will be fully implemented in Phase 2
            # For now, return the plan unchanged
            return plan
            
        except Exception as e:
            logger.error(f"Error consuming CIL execution insights: {e}")
            return plan
    
    async def _handle_execution_uncertainty_exploration(self, plan: Dict[str, Any], uncertainty_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Handle execution uncertainty-driven exploration"""
        try:
            # Check if uncertainty warrants exploration
            overall_uncertainty = uncertainty_analysis.get('overall_uncertainty', 0.5)
            
            if overall_uncertainty > 0.7:  # High uncertainty
                # Publish uncertainty strand for exploration
                uncertainty_strand_id = await self.execution_uncertainty_handler.publish_execution_uncertainty_strand(
                    uncertainty_analysis
                )
                
                # Add exploration flag to plan
                exploration_plan = plan.copy()
                exploration_plan['uncertainty_exploration'] = True
                exploration_plan['uncertainty_strand_id'] = uncertainty_strand_id
                exploration_plan['exploration_priority'] = uncertainty_analysis.get('exploration_priority', 0.5)
                
                logger.info(f"Added uncertainty exploration to plan: {uncertainty_strand_id}")
                return exploration_plan
            
            return plan
            
        except Exception as e:
            logger.error(f"Error handling execution uncertainty exploration: {e}")
            return plan
    
    async def _execute_plan_with_organic_influence(self, plan: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Execute the plan with organic influence"""
        try:
            # Execute the specific plan
            execution_result = await self._execute_specific_plan(plan, context)
            
            # Add organic influence metadata
            execution_result['organic_influence'] = {
                'resonance_metrics': context.resonance_metrics,
                'uncertainty_analysis': context.uncertainty_analysis,
                'cil_insights_count': len(context.cil_insights),
                'motif_integration': context.motif_integration,
                'execution_context_timestamp': context.timestamp.isoformat()
            }
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Error executing plan with organic influence: {e}")
            return {'error': str(e), 'plan': plan}
    
    async def _contribute_to_execution_motif(self, execution_result: Dict[str, Any], context: ExecutionContext):
        """Contribute execution result to motif creation"""
        try:
            # Extract execution pattern data
            execution_pattern_data = {
                'execution_result': execution_result,
                'context': context,
                'agent_name': self.agent_name,
                'timestamp': datetime.now()
            }
            
            # Contribute to motif
            await self.contribute_to_execution_motif(execution_pattern_data)
            
        except Exception as e:
            logger.error(f"Error contributing to execution motif: {e}")
    
    async def _publish_execution_results(self, execution_result: Dict[str, Any], context: ExecutionContext):
        """Publish execution results with resonance values"""
        try:
            # Create execution strand
            execution_strand = {
                'module': 'trader',
                'kind': 'order_execution',
                'content': {
                    'execution_result': execution_result,
                    'resonance_metrics': context.resonance_metrics,
                    'uncertainty_analysis': context.uncertainty_analysis,
                    'agent_name': self.agent_name
                },
                'tags': [
                    f'trader:{self.agent_name}',
                    'trader:execution_complete',
                    'trader:organic_influence'
                ],
                'sig_confidence': context.resonance_metrics.get('phi', 0.5),
                'outcome_score': execution_result.get('success_score', 0.0),
                'created_at': datetime.now().isoformat()
            }
            
            # Publish to AD_strands
            strand_id = await self._publish_strand_to_database(execution_strand)
            
            logger.info(f"Published execution results: {strand_id}")
            
        except Exception as e:
            logger.error(f"Error publishing execution results: {e}")
    
    def _update_agent_state(self, execution_result: Dict[str, Any]):
        """Update agent state after execution"""
        self.last_execution_time = datetime.now()
        self.execution_count += 1
        
        # Update resonance history
        if len(self.resonance_history) > 100:  # Keep last 100 executions
            self.resonance_history = self.resonance_history[-100:]
    
    # Placeholder methods for Phase 2 integration
    async def _get_cil_execution_insights(self, approved_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get CIL execution insights (Phase 2)"""
        return []
    
    async def _get_motif_integration_data(self, approved_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Get motif integration data (Phase 2)"""
        return {}
    
    # Database interaction methods (to be implemented based on existing patterns)
    async def _wait_for_execution_trigger(self):
        """Wait for data-driven heartbeat or triggers"""
        # Implementation will follow existing patterns
        await asyncio.sleep(1)  # 1-second heartbeat
    
    async def _check_for_execution_triggers(self) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """Check for new market data and approved plans"""
        # Implementation will follow existing database patterns
        return None, []
    
    async def _handle_pending_uncertainty_exploration(self):
        """Handle any pending uncertainty exploration"""
        # Implementation will follow existing patterns
        pass
    
    async def _handle_execution_error(self, error: Exception, market_data: Dict[str, Any], approved_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Handle execution errors gracefully"""
        return {
            'error': str(error),
            'market_data': market_data,
            'approved_plan': approved_plan,
            'agent_name': self.agent_name,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _extract_execution_pattern_invariants(self, execution_pattern_data: Dict[str, Any]) -> List[str]:
        """Extract execution pattern invariants"""
        # Implementation will follow existing patterns
        return []
    
    async def _identify_execution_failure_conditions(self, execution_pattern_data: Dict[str, Any]) -> List[str]:
        """Identify execution failure conditions"""
        # Implementation will follow existing patterns
        return []
    
    async def _provide_execution_mechanism_hypotheses(self, execution_pattern_data: Dict[str, Any], 
                                                     invariants: List[str], failure_conditions: List[str]) -> List[str]:
        """Provide execution mechanism hypotheses"""
        # Implementation will follow existing patterns
        return []
    
    async def _create_execution_motif_strand(self, invariants: List[str], failure_conditions: List[str], 
                                           mechanism_hypotheses: List[str], execution_pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create execution motif strand"""
        # Implementation will follow existing patterns
        return {}
    
    async def _publish_motif_strand(self, motif_strand: Dict[str, Any]) -> str:
        """Publish motif strand to AD_strands"""
        # Implementation will follow existing database patterns
        return f"motif_strand_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def _update_execution_telemetry(self, resonance_metrics: Dict[str, float]):
        """Update execution telemetry"""
        # Implementation will follow existing patterns
        pass
    
    async def _contribute_to_global_execution_theta(self, resonance_metrics: Dict[str, float]):
        """Contribute to global execution θ field"""
        # Implementation will follow existing patterns
        pass
    
    async def _enable_organic_execution_influence(self, resonance_metrics: Dict[str, float]):
        """Enable organic execution influence through resonance"""
        # Implementation will follow existing patterns
        pass
    
    async def _publish_strand_to_database(self, strand: Dict[str, Any]) -> str:
        """Publish strand to AD_strands table"""
        # Implementation will follow existing database patterns
        return f"strand_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
