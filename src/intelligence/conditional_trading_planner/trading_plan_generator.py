"""
Trading Plan Generator

Creates conditional trading plans based on prediction review analysis and 
historical performance data.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from ...llm_integration.prompt_manager import PromptManager
from src.intelligence.universal_learning.module_specific_scoring import ModuleSpecificScoring
from src.intelligence.universal_learning.centralized_learning_system import CentralizedLearningSystem


class TradingPlanGenerator:
    """
    Generates conditional trading plans from prediction review analysis.
    
    Responsibilities:
    1. Create conditional trading rules based on pattern analysis
    2. Incorporate historical performance data
    3. Generate risk management rules
    4. Store trading plans as strands
    """
    
    def __init__(self, supabase_manager, llm_client, learning_system=None, prompt_manager=None):
        """
        Initialize trading plan generator.
        
        Args:
            supabase_manager: Database manager for strand operations
            llm_client: LLM client for plan generation
            learning_system: CTP learning system for trade outcome insights
            prompt_manager: Prompt manager for centralized prompt handling
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.learning_system = learning_system
        self.prompt_manager = prompt_manager or PromptManager()
        self.logger = logging.getLogger(f"{__name__}.plan_generator")
        
        # Learning system integration
        self.module_scoring = ModuleSpecificScoring(supabase_manager)
        self.centralized_learning = CentralizedLearningSystem(supabase_manager, llm_client, None)
    
    async def create_conditional_trading_plan(self, analysis: Dict[str, Any]) -> Optional[str]:
        """
        Create a conditional trading plan from prediction review analysis.
        
        Args:
            analysis: Analysis data from PredictionReviewAnalyzer
            
        Returns:
            ID of created trading plan strand, or None if failed
        """
        try:
            self.logger.info(f"Creating trading plan for: {analysis.get('prediction_review_id')}")
            
            # Step 1: Get trade outcome learning insights for the same clusters
            trade_outcome_insights = await self._get_trade_outcome_insights(analysis)
            
            # Step 2: Generate trading rules based on analysis and trade outcome insights
            trading_rules = await self._generate_trading_rules(analysis, trade_outcome_insights)
            
            # Step 3: Generate management rules
            management_rules = await self._generate_management_rules(analysis, trade_outcome_insights)
            
            # Step 4: Generate performance expectations
            performance_expectations = self._generate_performance_expectations(analysis, trade_outcome_insights)
            
            # Step 5: Create trading plan strand
            trading_plan_id = await self._create_trading_plan_strand(
                analysis, trading_rules, management_rules, performance_expectations, trade_outcome_insights
            )
            
            if trading_plan_id:
                self.logger.info(f"Created trading plan: {trading_plan_id}")
            
            return trading_plan_id
            
        except Exception as e:
            self.logger.error(f"Error creating trading plan: {e}")
            return None
    
    async def _get_trade_outcome_insights(self, analysis: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get trade outcome learning insights for the same clusters as the prediction review.
        
        Args:
            analysis: Analysis data from PredictionReviewAnalyzer
            
        Returns:
            Dictionary mapping cluster keys to learning insights
        """
        try:
            if not self.learning_system:
                self.logger.warning("No learning system available for trade outcome insights")
                return {}
            
            # Get cluster keys from prediction review
            cluster_keys = analysis.get('prediction_review_cluster_keys', [])
            
            if not cluster_keys:
                self.logger.warning("No cluster keys available for trade outcome insights")
                return {}
            
            # Get learning insights for these clusters
            insights = await self.learning_system.get_learning_insights_for_clusters(cluster_keys)
            
            self.logger.info(f"Retrieved trade outcome insights for {len(insights)} clusters")
            return insights
            
        except Exception as e:
            self.logger.error(f"Error getting trade outcome insights: {e}")
            return {}
    
    async def _generate_trading_rules(self, analysis: Dict[str, Any], trade_outcome_insights: Dict[str, List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Generate trading rules based on pattern analysis, historical performance, and trade outcome insights.
        
        Args:
            analysis: Analysis data from PredictionReviewAnalyzer
            trade_outcome_insights: Trade outcome learning insights for the same clusters
            
        Returns:
            Dictionary with trading rules
        """
        try:
            pattern_info = analysis.get('pattern_info', {})
            historical_performance = analysis.get('historical_performance', {})
            
            # Basic trading rules based on pattern type
            trading_rules = {
                "direction": self._determine_direction(pattern_info),
                "entry_condition": self._determine_entry_condition(pattern_info),
                "stop_loss": self._determine_stop_loss(pattern_info, historical_performance),
                "target_price": self._determine_target_price(pattern_info, historical_performance)
            }
            
            # Add advanced rules if historical data is available
            if historical_performance:
                trading_rules.update(self._generate_advanced_rules(pattern_info, historical_performance))
            
            # Incorporate trade outcome learning insights
            if trade_outcome_insights:
                trading_rules.update(self._incorporate_trade_outcome_insights(trade_outcome_insights))
            
            return trading_rules
            
        except Exception as e:
            self.logger.error(f"Error generating trading rules: {e}")
            return {}
    
    def _determine_direction(self, pattern_info: Dict[str, Any]) -> str:
        """Determine trading direction based on pattern type."""
        pattern_types = pattern_info.get('pattern_types', [])
        
        # Volume spike patterns are typically bullish
        if 'volume_spike' in pattern_types:
            return 'long'
        
        # Divergence patterns depend on type
        if 'divergence' in pattern_types:
            return 'long'  # Assume bullish divergence for now
        
        # Default to long for most patterns
        return 'long'
    
    def _determine_entry_condition(self, pattern_info: Dict[str, Any]) -> str:
        """Determine entry condition based on pattern type."""
        pattern_types = pattern_info.get('pattern_types', [])
        
        if 'volume_spike' in pattern_types:
            return 'price_breaks_above_volume_spike_level'
        elif 'divergence' in pattern_types:
            return 'price_breaks_above_divergence_level'
        else:
            return 'price_breaks_above_support_level'
    
    def _determine_stop_loss(self, pattern_info: Dict[str, Any], historical_performance: Dict[str, Any]) -> str:
        """Determine stop loss based on pattern and historical performance."""
        # Use historical average drawdown if available
        for cluster_metrics in historical_performance.values():
            if isinstance(cluster_metrics, dict) and 'avg_drawdown' in cluster_metrics:
                avg_drawdown = abs(cluster_metrics['avg_drawdown'])
                if avg_drawdown > 0:
                    return f"{avg_drawdown:.1f}%_below_entry"
        
        # Default stop loss
        return "2%_below_entry"
    
    def _determine_target_price(self, pattern_info: Dict[str, Any], historical_performance: Dict[str, Any]) -> str:
        """Determine target price based on pattern and historical performance."""
        # Use historical average return if available
        for cluster_metrics in historical_performance.values():
            if isinstance(cluster_metrics, dict) and 'avg_return' in cluster_metrics:
                avg_return = cluster_metrics['avg_return']
                if avg_return > 0:
                    return f"{avg_return:.1f}%_above_entry"
        
        # Default target price
        return "6%_above_entry"
    
    def _generate_advanced_rules(self, pattern_info: Dict[str, Any], historical_performance: Dict[str, Any]) -> Dict[str, Any]:
        """Generate advanced trading rules based on historical performance."""
        advanced_rules = {}
        
        # Find the best performing cluster for advanced rules
        best_cluster = None
        best_success_rate = 0
        
        for cluster_name, metrics in historical_performance.items():
            if isinstance(metrics, dict) and metrics.get('success_rate', 0) > best_success_rate:
                best_success_rate = metrics['success_rate']
                best_cluster = metrics
        
        if best_cluster and best_cluster.get('success_rate', 0) > 0.6:
            # High success rate - use more aggressive targets
            if best_cluster.get('avg_return', 0) > 5:
                advanced_rules['entry_strategy'] = 'limit_order_at_support'
                advanced_rules['target_price'] = 'resistance_level'
        
        return advanced_rules
    
    async def _generate_management_rules(self, analysis: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate management rules based on pattern analysis.
        
        Args:
            analysis: Analysis data from PredictionReviewAnalyzer
            
        Returns:
            Dictionary with management rules
        """
        try:
            pattern_info = analysis.get('pattern_info', {})
            pattern_types = pattern_info.get('pattern_types', [])
            
            management_rules = {}
            
            # Volume spike specific rules
            if 'volume_spike' in pattern_types:
                management_rules['if_volume_spikes_again'] = 'take_50%_profit'
                management_rules['if_price_drops_1%'] = 'add_another_position'
            
            # Divergence specific rules
            if 'divergence' in pattern_types:
                management_rules['if_divergence_weakens'] = 'exit_immediately'
                management_rules['if_breaks_resistance'] = 'move_stop_to_breakeven'
            
            # General management rules
            management_rules.update({
                'if_breaks_resistance': 'move_stop_to_breakeven',
                'if_reversal_pattern': 'exit_early'
            })
            
            return management_rules
            
        except Exception as e:
            self.logger.error(f"Error generating management rules: {e}")
            return {}
    
    def _generate_performance_expectations(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate performance expectations based on historical data.
        
        Args:
            analysis: Analysis data from PredictionReviewAnalyzer
            
        Returns:
            Dictionary with performance expectations
        """
        try:
            historical_performance = analysis.get('historical_performance', {})
            
            # Calculate overall performance metrics
            all_metrics = [metrics for metrics in historical_performance.values() 
                          if isinstance(metrics, dict)]
            
            if all_metrics:
                avg_success_rate = sum(m.get('success_rate', 0) for m in all_metrics) / len(all_metrics)
                avg_return = sum(m.get('avg_return', 0) for m in all_metrics) / len(all_metrics)
                avg_duration = sum(m.get('avg_duration', 0) for m in all_metrics) / len(all_metrics)
                
                # Calculate R/R ratio
                avg_drawdown = sum(m.get('avg_drawdown', 0) for m in all_metrics) / len(all_metrics)
                rr_ratio = abs(avg_return / avg_drawdown) if avg_drawdown != 0 else 2.0
                
                return {
                    "success_rate": round(avg_success_rate, 3),
                    "avg_return": round(avg_return, 3),
                    "r_r_ratio": round(rr_ratio, 2),
                    "avg_duration_hours": round(avg_duration, 1)
                }
            else:
                # Default expectations if no historical data
                return {
                    "success_rate": 0.5,
                    "avg_return": 0.03,
                    "r_r_ratio": 2.0,
                    "avg_duration_hours": 4.0
                }
                
        except Exception as e:
            self.logger.error(f"Error generating performance expectations: {e}")
            return {
                "success_rate": 0.5,
                "avg_return": 0.03,
                "r_r_ratio": 2.0,
                "avg_duration_hours": 4.0
            }
    
    async def _create_trading_plan_strand(self, analysis: Dict[str, Any], trading_rules: Dict[str, Any], 
                                        management_rules: Dict[str, Any], performance_expectations: Dict[str, Any]) -> Optional[str]:
        """
        Create and store trading plan strand in database.
        
        Args:
            analysis: Analysis data
            trading_rules: Generated trading rules
            management_rules: Generated management rules
            performance_expectations: Performance expectations
            
        Returns:
            ID of created strand, or None if failed
        """
        try:
            pattern_info = analysis.get('pattern_info', {})
            
            # Generate unique plan ID
            plan_id = f"ctp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Create trading plan data
            trading_plan_data = {
                "id": plan_id,
                "module": "ctp",
                "kind": "conditional_trading_plan",
                "symbol": pattern_info.get('asset', 'UNKNOWN'),
                "timeframe": pattern_info.get('timeframe', '1h'),
                "tags": ['ctp', 'trading_plan', 'conditional'],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "braid_level": 1,
                "lesson": "",
                "content": {
                    "plan_id": plan_id,
                    "trigger_conditions": {
                        "group_signature": pattern_info.get('group_signature', 'unknown'),
                        "min_confidence": pattern_info.get('confidence', 0.7),
                        "min_pattern_count": 1
                    },
                    "trading_rules": trading_rules,
                    "management_rules": management_rules,
                    "performance_expectations": performance_expectations,
                    "source_prediction_review": analysis.get('prediction_review_id'),
                    "source_prediction_review_cluster_keys": analysis.get('prediction_review_cluster_keys', []),
                    "created_at": datetime.now(timezone.utc).isoformat()
                },
                "module_intelligence": {
                    "plan_type": "conditional_trading_plan",
                    "pattern_info": pattern_info,
                    "historical_performance": analysis.get('historical_performance', {}),
                    "confidence": pattern_info.get('confidence', 0.0)
                },
                "cluster_key": self._inherit_cluster_keys_from_prediction_review(analysis)
            }
            
            # Calculate module-specific resonance scores
            try:
                scores = await self.module_scoring.calculate_module_scores(trading_plan_data, 'ctp')
                trading_plan_data['persistence_score'] = scores.get('persistence_score', 0.5)
                trading_plan_data['novelty_score'] = scores.get('novelty_score', 0.5)
                trading_plan_data['surprise_rating'] = scores.get('surprise_rating', 0.5)
                trading_plan_data['resonance_score'] = scores.get('resonance_score', 0.5)
                
                # Store resonance scores in content for detailed tracking
                trading_plan_data['content']['resonance_scores'] = {
                    'phi': scores.get('phi', 0.5),
                    'rho': scores.get('rho', 0.5),
                    'theta': scores.get('theta', 0.5),
                    'omega': scores.get('omega', 0.5)
                }
                
                self.logger.info(f"Calculated CTP resonance scores: φ={scores.get('phi', 0.5):.3f}, ρ={scores.get('rho', 0.5):.3f}, θ={scores.get('theta', 0.5):.3f}, ω={scores.get('omega', 0.5):.3f}")
                
            except Exception as e:
                self.logger.warning(f"Failed to calculate resonance scores: {e}")
                # Set default scores
                trading_plan_data['persistence_score'] = 0.5
                trading_plan_data['novelty_score'] = 0.5
                trading_plan_data['surprise_rating'] = 0.5
                trading_plan_data['resonance_score'] = 0.5
            
            # Store in database
            result = self.supabase_manager.insert_strand(trading_plan_data)
            
            if result:
                return plan_id
            else:
                self.logger.error(f"Failed to store trading plan: {plan_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating trading plan strand: {e}")
            return None
    
    async def get_plan_context(self, context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get context for CTP trading plans from the learning system
        
        Args:
            context_data: Additional context data for filtering
            
        Returns:
            Context dictionary with relevant insights for CTP plans
        """
        try:
            return await self.centralized_learning.get_context_for_module('ctp', context_data)
        except Exception as e:
            self.logger.error(f"Error getting plan context: {e}")
            return {}
    
    async def enhance_plan_with_context(self, plan_data: Dict[str, Any], context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Enhance trading plan with context from the learning system
        
        Args:
            plan_data: Trading plan data to enhance
            context_data: Additional context data for filtering
            
        Returns:
            Enhanced plan with context insights
        """
        try:
            # Get context from learning system
            context = await self.get_plan_context(context_data)
            
            if context:
                # Add context to plan
                plan_data['context_insights'] = {
                    'success_rate': context.get('success_rate', 0.0),
                    'strategies': context.get('strategies', []),
                    'risk_insights': context.get('risk_insights', []),
                    'adaptations': context.get('adaptations', []),
                    'data_sources': context.get('data_sources', []),
                    'context_timestamp': context.get('context_timestamp', '')
                }
                
                self.logger.info(f"Enhanced plan with context: {len(context.get('strategies', []))} strategies, {context.get('success_rate', 0.0):.1f}% success rate")
            
            return plan_data
            
        except Exception as e:
            self.logger.error(f"Error enhancing plan with context: {e}")
            return plan_data
    
    async def get_plan_performance(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Get performance metrics for a specific trading plan.
        
        Args:
            plan_id: ID of the trading plan
            
        Returns:
            Performance metrics dictionary, or None if not found
        """
        try:
            # Get trading plan strand
            result = self.supabase_manager.client.table('ad_strands').select('*').eq('id', plan_id).eq('kind', 'conditional_trading_plan').execute()
            
            if not result.data:
                return None
            
            plan_strand = result.data[0]
            content = plan_strand.get('content', {})
            
            return {
                "plan_id": plan_id,
                "status": content.get('status', 'unknown'),
                "performance_expectations": content.get('performance_expectations', {}),
                "created_at": plan_strand.get('created_at'),
                "updated_at": plan_strand.get('updated_at')
            }
            
        except Exception as e:
            self.logger.error(f"Error getting plan performance for {plan_id}: {e}")
            return None
    
    def _inherit_cluster_keys_from_prediction_review(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Inherit cluster keys from the source prediction review.
        
        Args:
            analysis: Analysis data containing prediction review information
            
        Returns:
            List of cluster keys inherited from prediction review
        """
        try:
            # Get cluster keys from the prediction review analysis
            prediction_review_cluster_keys = analysis.get('prediction_review_cluster_keys', [])
            
            if prediction_review_cluster_keys:
                # Return the cluster keys from the prediction review
                return prediction_review_cluster_keys
            else:
                # If no cluster keys available, create basic ones from pattern info
                pattern_info = analysis.get('pattern_info', {})
                cluster_keys = []
                
                if pattern_info.get('group_signature'):
                    cluster_keys.append({
                        "cluster_type": "pattern_timeframe",
                        "cluster_key": pattern_info['group_signature'],
                        "braid_level": 1,
                        "consumed": False
                    })
                
                if pattern_info.get('asset'):
                    cluster_keys.append({
                        "cluster_type": "asset",
                        "cluster_key": pattern_info['asset'],
                        "braid_level": 1,
                        "consumed": False
                    })
                
                if pattern_info.get('timeframe'):
                    cluster_keys.append({
                        "cluster_type": "timeframe",
                        "cluster_key": pattern_info['timeframe'],
                        "braid_level": 1,
                        "consumed": False
                    })
                
                return cluster_keys
                
        except Exception as e:
            self.logger.error(f"Error inheriting cluster keys: {e}")
            return []
