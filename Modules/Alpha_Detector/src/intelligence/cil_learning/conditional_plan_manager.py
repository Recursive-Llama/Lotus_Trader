"""
Conditional Plan Manager for CIL Learning System

This module manages conditional trading plans and their evolution.
It creates, updates, and deprecates trading plans based on learning insights.

Features:
1. Create conditional plans from cluster analysis
2. Update existing plans with learning insights
3. Deprecate plans and create new versions
4. Track plan performance and evolution
5. Generate actionable trading strategies
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)


class PlanStatus(Enum):
    """Conditional plan status"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    TESTING = "testing"
    RETIRED = "retired"


class PlanType(Enum):
    """Conditional plan type"""
    ENTRY_SIGNAL = "entry_signal"
    EXIT_SIGNAL = "exit_signal"
    RISK_MANAGEMENT = "risk_management"
    POSITION_SIZING = "position_sizing"
    TIMING_OPTIMIZATION = "timing_optimization"


@dataclass
class ConditionalPlan:
    """Conditional trading plan"""
    plan_id: str
    plan_type: PlanType
    cluster_key: str
    symbol: str
    timeframe: str
    pattern_type: str
    strength_range: str
    rr_profile: str
    market_conditions: str
    conditions: Dict[str, Any]
    actions: Dict[str, Any]
    parameters: Dict[str, Any]
    status: PlanStatus
    version: int
    success_rate: float
    avg_rr: float
    sample_size: int
    created_at: datetime
    updated_at: datetime
    replaces_id: Optional[str] = None
    replaced_by_id: Optional[str] = None


class ConditionalPlanManager:
    """
    Manages conditional trading plans and their evolution
    
    This is a new CIL Engine that creates and manages actionable trading strategies
    based on learning insights from the outcome analysis engine.
    """
    
    def __init__(self, supabase_manager, llm_client=None):
        """
        Initialize conditional plan manager
        
        Args:
            supabase_manager: Database manager
            llm_client: LLM client for plan generation (optional)
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # Plan configuration
        self.min_success_rate = 0.6
        self.min_sample_size = 10
        self.max_plan_versions = 5
    
    async def create_conditional_plan(self, cluster_analysis: Dict) -> Dict[str, Any]:
        """
        Create new conditional plan from cluster analysis
        
        Args:
            cluster_analysis: Analysis results from OutcomeAnalysisEngine
            
        Returns:
            Created conditional plan dictionary
        """
        try:
            if 'error' in cluster_analysis:
                return {'error': cluster_analysis['error']}
            
            cluster_key = cluster_analysis.get('cluster_key', '')
            success_rate = cluster_analysis.get('overall_success_rate', 0.0)
            sample_size = cluster_analysis.get('sample_size', 0)
            
            # Check if plan should be created
            if success_rate < self.min_success_rate or sample_size < self.min_sample_size:
                return {
                    'error': f'Insufficient performance: success_rate={success_rate:.2f}, sample_size={sample_size}',
                    'success_rate': success_rate,
                    'sample_size': sample_size
                }
            
            # Generate plan ID
            plan_id = f"plan_{cluster_key}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            
            # Extract plan parameters from cluster analysis
            plan_parameters = self._extract_plan_parameters(cluster_analysis)
            
            # Generate plan conditions and actions
            conditions = await self._generate_plan_conditions(plan_parameters)
            actions = await self._generate_plan_actions(plan_parameters)
            
            # Create conditional plan
            plan = ConditionalPlan(
                plan_id=plan_id,
                plan_type=PlanType.ENTRY_SIGNAL,  # Default type
                cluster_key=cluster_key,
                symbol=plan_parameters.get('symbol', ''),
                timeframe=plan_parameters.get('timeframe', ''),
                pattern_type=plan_parameters.get('pattern_type', ''),
                strength_range=plan_parameters.get('strength_range', ''),
                rr_profile=plan_parameters.get('rr_profile', ''),
                market_conditions=plan_parameters.get('market_conditions', ''),
                conditions=conditions,
                actions=actions,
                parameters=plan_parameters,
                status=PlanStatus.ACTIVE,
                version=1,
                success_rate=success_rate,
                avg_rr=cluster_analysis.get('avg_rr', 0.0),
                sample_size=sample_size,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            # Save to database
            await self._save_plan_to_database(plan)
            
            self.logger.info(f"Created conditional plan {plan_id} for cluster {cluster_key}")
            return {
                'plan_id': plan_id,
                'status': 'created',
                'success_rate': success_rate,
                'sample_size': sample_size,
                'plan_type': plan.plan_type.value
            }
            
        except Exception as e:
            self.logger.error(f"Error creating conditional plan: {e}")
            return {'error': str(e)}
    
    async def update_conditional_plan(self, plan_id: str, evolution: Dict) -> Dict[str, Any]:
        """
        Update existing plan with learning insights
        
        Args:
            plan_id: ID of plan to update
            evolution: Evolution recommendations from OutcomeAnalysisEngine
            
        Returns:
            Update result dictionary
        """
        try:
            # Get existing plan
            existing_plan = await self._get_plan_from_database(plan_id)
            if not existing_plan:
                return {'error': f'Plan {plan_id} not found'}
            
            # Check if plan should be updated or deprecated
            if evolution.get('evolution_priority') == 'urgent':
                return await self.deprecate_plan(plan_id, 'urgent_evolution_required')
            
            # Update plan parameters based on evolution
            updated_parameters = self._apply_evolution_to_parameters(existing_plan, evolution)
            
            # Update plan conditions and actions
            updated_conditions = await self._generate_plan_conditions(updated_parameters)
            updated_actions = await self._generate_plan_actions(updated_parameters)
            
            # Create updated plan
            updated_plan = ConditionalPlan(
                plan_id=f"{plan_id}_v{existing_plan.version + 1}",
                plan_type=existing_plan.plan_type,
                cluster_key=existing_plan.cluster_key,
                symbol=existing_plan.symbol,
                timeframe=existing_plan.timeframe,
                pattern_type=existing_plan.pattern_type,
                strength_range=existing_plan.strength_range,
                rr_profile=existing_plan.rr_profile,
                market_conditions=existing_plan.market_conditions,
                conditions=updated_conditions,
                actions=updated_actions,
                parameters=updated_parameters,
                status=PlanStatus.ACTIVE,
                version=existing_plan.version + 1,
                success_rate=evolution.get('success_rate', existing_plan.success_rate),
                avg_rr=evolution.get('avg_rr', existing_plan.avg_rr),
                sample_size=evolution.get('sample_size', existing_plan.sample_size),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                replaces_id=plan_id
            )
            
            # Save updated plan
            await self._save_plan_to_database(updated_plan)
            
            # Update original plan to point to new version
            existing_plan.replaced_by_id = updated_plan.plan_id
            existing_plan.status = PlanStatus.DEPRECATED
            await self._update_plan_in_database(existing_plan)
            
            self.logger.info(f"Updated plan {plan_id} to version {updated_plan.version}")
            return {
                'plan_id': updated_plan.plan_id,
                'status': 'updated',
                'version': updated_plan.version,
                'replaces_id': plan_id
            }
            
        except Exception as e:
            self.logger.error(f"Error updating conditional plan {plan_id}: {e}")
            return {'error': str(e)}
    
    async def deprecate_plan(self, plan_id: str, reason: str) -> Dict[str, Any]:
        """
        Mark plan as deprecated and create new version if needed
        
        Args:
            plan_id: ID of plan to deprecate
            reason: Reason for deprecation
            
        Returns:
            Deprecation result dictionary
        """
        try:
            # Get existing plan
            existing_plan = await self._get_plan_from_database(plan_id)
            if not existing_plan:
                return {'error': f'Plan {plan_id} not found'}
            
            # Mark plan as deprecated
            existing_plan.status = PlanStatus.DEPRECATED
            existing_plan.updated_at = datetime.now(timezone.utc)
            
            # Update in database
            await self._update_plan_in_database(existing_plan)
            
            self.logger.info(f"Deprecated plan {plan_id}: {reason}")
            return {
                'plan_id': plan_id,
                'status': 'deprecated',
                'reason': reason,
                'deprecated_at': existing_plan.updated_at.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error deprecating plan {plan_id}: {e}")
            return {'error': str(e)}
    
    async def get_active_plans(self, symbol: Optional[str] = None, timeframe: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all active conditional plans
        
        Args:
            symbol: Filter by symbol (optional)
            timeframe: Filter by timeframe (optional)
            
        Returns:
            List of active plan dictionaries
        """
        try:
            # Query database for active plans
            query = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'conditional_plan').eq('status', 'active')
            
            if symbol:
                query = query.eq('symbol', symbol)
            if timeframe:
                query = query.eq('timeframe', timeframe)
            
            result = query.execute()
            
            if result.data:
                return result.data
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting active plans: {e}")
            return []
    
    def _extract_plan_parameters(self, cluster_analysis: Dict) -> Dict[str, Any]:
        """Extract plan parameters from cluster analysis"""
        try:
            # Extract basic parameters
            parameters = {
                'symbol': cluster_analysis.get('symbol', ''),
                'timeframe': cluster_analysis.get('timeframe', ''),
                'pattern_type': cluster_analysis.get('pattern_type', ''),
                'strength_range': cluster_analysis.get('strength_range', ''),
                'rr_profile': cluster_analysis.get('rr_profile', ''),
                'market_conditions': cluster_analysis.get('market_conditions', ''),
                'success_rate': cluster_analysis.get('overall_success_rate', 0.0),
                'avg_rr': cluster_analysis.get('avg_rr', 0.0),
                'sample_size': cluster_analysis.get('sample_size', 0)
            }
            
            # Extract analysis-specific parameters
            analysis_results = cluster_analysis.get('analysis_results', [])
            for analysis in analysis_results:
                if analysis.get('analysis_type') == 'rr_optimization':
                    parameters['recommended_target'] = analysis.get('recommended_target', 0.0)
                    parameters['recommended_stop'] = analysis.get('recommended_stop', 0.0)
                elif analysis.get('analysis_type') == 'timing_optimization':
                    parameters['avg_duration'] = analysis.get('avg_duration', 0.0)
                elif analysis.get('analysis_type') == 'risk_optimization':
                    parameters['avg_drawdown'] = analysis.get('avg_drawdown', 0.0)
            
            return parameters
            
        except Exception as e:
            self.logger.error(f"Error extracting plan parameters: {e}")
            return {}
    
    async def _generate_plan_conditions(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate plan conditions based on parameters"""
        try:
            conditions = {
                'pattern_type': parameters.get('pattern_type', ''),
                'strength_range': parameters.get('strength_range', ''),
                'market_conditions': parameters.get('market_conditions', ''),
                'min_confidence': 0.7,
                'min_volume_ratio': 1.5,
                'max_drawdown_threshold': 0.1
            }
            
            # Add LLM-generated conditions if available
            if self.llm_client:
                llm_conditions = await self._generate_llm_conditions(parameters)
                conditions.update(llm_conditions)
            
            return conditions
            
        except Exception as e:
            self.logger.error(f"Error generating plan conditions: {e}")
            return {}
    
    async def _generate_plan_actions(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate plan actions based on parameters"""
        try:
            actions = {
                'entry_action': 'buy',
                'target_price': parameters.get('recommended_target', 0.0),
                'stop_loss': parameters.get('recommended_stop', 0.0),
                'position_size': 'moderate',
                'max_hold_time': int(parameters.get('avg_duration', 120)),
                'exit_conditions': ['target_hit', 'stop_hit', 'time_expired']
            }
            
            # Add LLM-generated actions if available
            if self.llm_client:
                llm_actions = await self._generate_llm_actions(parameters)
                actions.update(llm_actions)
            
            return actions
            
        except Exception as e:
            self.logger.error(f"Error generating plan actions: {e}")
            return {}
    
    async def _generate_llm_conditions(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate LLM-enhanced conditions"""
        # Placeholder for LLM-generated conditions
        return {
            'llm_enhanced': True,
            'confidence_threshold': 0.8,
            'market_regime_filter': True
        }
    
    async def _generate_llm_actions(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate LLM-enhanced actions"""
        # Placeholder for LLM-generated actions
        return {
            'llm_enhanced': True,
            'dynamic_sizing': True,
            'adaptive_exits': True
        }
    
    def _apply_evolution_to_parameters(self, existing_plan: ConditionalPlan, evolution: Dict) -> Dict[str, Any]:
        """Apply evolution recommendations to plan parameters"""
        try:
            updated_parameters = existing_plan.parameters.copy()
            
            # Apply evolution recommendations
            recommendations = evolution.get('recommendations', [])
            for recommendation in recommendations:
                if 'increase target' in recommendation.lower():
                    updated_parameters['recommended_target'] = updated_parameters.get('recommended_target', 0.0) * 1.1
                elif 'tighten stop' in recommendation.lower():
                    updated_parameters['recommended_stop'] = updated_parameters.get('recommended_stop', 0.0) * 0.9
                elif 'increase position' in recommendation.lower():
                    updated_parameters['position_size'] = 'large'
                elif 'add filters' in recommendation.lower():
                    updated_parameters['min_confidence'] = updated_parameters.get('min_confidence', 0.7) + 0.1
            
            return updated_parameters
            
        except Exception as e:
            self.logger.error(f"Error applying evolution to parameters: {e}")
            return existing_plan.parameters
    
    async def _save_plan_to_database(self, plan: ConditionalPlan) -> bool:
        """Save conditional plan to database"""
        try:
            plan_data = {
                'id': plan.plan_id,
                'kind': 'conditional_plan',
                'symbol': plan.symbol,
                'timeframe': plan.timeframe,
                'pattern_type': plan.pattern_type,
                'strength_range': plan.strength_range,
                'rr_profile': plan.rr_profile,
                'market_conditions': plan.market_conditions,
                'status': plan.status.value,
                'plan_version': plan.version,
                'success_rate': plan.success_rate,
                'avg_rr': plan.avg_rr,
                'sample_size': plan.sample_size,
                'created_at': plan.created_at.isoformat(),
                'updated_at': plan.updated_at.isoformat(),
                'replaces_id': plan.replaces_id,
                'replaced_by_id': plan.replaced_by_id,
                'content': {
                    'plan_type': plan.plan_type.value,
                    'cluster_key': plan.cluster_key,
                    'conditions': plan.conditions,
                    'actions': plan.actions,
                    'parameters': plan.parameters
                }
            }
            
            result = self.supabase_manager.client.table('ad_strands').insert(plan_data).execute()
            return bool(result.data)
            
        except Exception as e:
            self.logger.error(f"Error saving plan to database: {e}")
            return False
    
    async def _get_plan_from_database(self, plan_id: str) -> Optional[ConditionalPlan]:
        """Get conditional plan from database"""
        try:
            result = self.supabase_manager.client.table('ad_strands').select('*').eq('id', plan_id).eq('kind', 'conditional_plan').execute()
            
            if not result.data:
                return None
            
            plan_data = result.data[0]
            content = plan_data.get('content', {})
            
            return ConditionalPlan(
                plan_id=plan_data['id'],
                plan_type=PlanType(content.get('plan_type', 'entry_signal')),
                cluster_key=content.get('cluster_key', ''),
                symbol=plan_data.get('symbol', ''),
                timeframe=plan_data.get('timeframe', ''),
                pattern_type=plan_data.get('pattern_type', ''),
                strength_range=plan_data.get('strength_range', ''),
                rr_profile=plan_data.get('rr_profile', ''),
                market_conditions=plan_data.get('market_conditions', ''),
                conditions=content.get('conditions', {}),
                actions=content.get('actions', {}),
                parameters=content.get('parameters', {}),
                status=PlanStatus(plan_data.get('status', 'active')),
                version=plan_data.get('plan_version', 1),
                success_rate=plan_data.get('success_rate', 0.0),
                avg_rr=plan_data.get('avg_rr', 0.0),
                sample_size=plan_data.get('sample_size', 0),
                created_at=datetime.fromisoformat(plan_data['created_at'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(plan_data['updated_at'].replace('Z', '+00:00')),
                replaces_id=plan_data.get('replaces_id'),
                replaced_by_id=plan_data.get('replaced_by_id')
            )
            
        except Exception as e:
            self.logger.error(f"Error getting plan from database: {e}")
            return None
    
    async def _update_plan_in_database(self, plan: ConditionalPlan) -> bool:
        """Update conditional plan in database"""
        try:
            update_data = {
                'status': plan.status.value,
                'plan_version': plan.version,
                'success_rate': plan.success_rate,
                'avg_rr': plan.avg_rr,
                'sample_size': plan.sample_size,
                'updated_at': plan.updated_at.isoformat(),
                'replaces_id': plan.replaces_id,
                'replaced_by_id': plan.replaced_by_id,
                'content': {
                    'plan_type': plan.plan_type.value,
                    'cluster_key': plan.cluster_key,
                    'conditions': plan.conditions,
                    'actions': plan.actions,
                    'parameters': plan.parameters
                }
            }
            
            result = self.supabase_manager.client.table('ad_strands').update(update_data).eq('id', plan.plan_id).execute()
            return bool(result.data)
            
        except Exception as e:
            self.logger.error(f"Error updating plan in database: {e}")
            return False


# Example usage and testing
if __name__ == "__main__":
    # Test the conditional plan manager
    from src.utils.supabase_manager import SupabaseManager
    
    async def test_conditional_plan_manager():
        supabase_manager = SupabaseManager()
        manager = ConditionalPlanManager(supabase_manager)
        
        # Test cluster analysis
        cluster_analysis = {
            'cluster_key': 'BTC_1h_volume_spike_strong_moderate_moderate_volatility',
            'overall_success_rate': 0.75,
            'avg_rr': 2.5,
            'sample_size': 15,
            'symbol': 'BTC',
            'timeframe': '1h',
            'pattern_type': 'volume_spike',
            'strength_range': 'strong',
            'rr_profile': 'moderate',
            'market_conditions': 'moderate_volatility'
        }
        
        # Test plan creation
        result = await manager.create_conditional_plan(cluster_analysis)
        print(f"Plan creation result: {result}")
        
        # Test plan update
        if 'plan_id' in result:
            evolution = {
                'success_rate': 0.8,
                'avg_rr': 2.8,
                'sample_size': 20,
                'recommendations': ['increase target prices', 'tighten stop losses'],
                'evolution_priority': 'medium'
            }
            update_result = await manager.update_conditional_plan(result['plan_id'], evolution)
            print(f"Plan update result: {update_result}")
    
    import asyncio
    asyncio.run(test_conditional_plan_manager())
