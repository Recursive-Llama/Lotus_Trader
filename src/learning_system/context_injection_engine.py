"""
Context Injection Engine

Provides intelligent context injection for modules based on their subscriptions.
Each module gets context from the strand types they subscribe to, with smart
filtering and formatting based on their specific needs.
"""

import logging
import yaml
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
import os

logger = logging.getLogger(__name__)


class ContextInjectionEngine:
    """
    Context Injection Engine for module-specific context delivery
    
    Provides intelligent context injection based on module subscriptions
    and strand type preferences. Each module gets relevant context from
    the learning system without needing to know about clustering or braids.
    """
    
    def __init__(self, supabase_manager, config_path: str = None):
        """
        Initialize context injection engine
        
        Args:
            supabase_manager: Database manager for context retrieval
            config_path: Path to context injection configuration file
        """
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), 
                '..', '..', 'Modules', 'Alpha_Detector', 'config', 'context_injection.yaml'
            )
        
        self.config = self._load_config(config_path)
        self.module_subscriptions = self.config.get('module_subscriptions', {})
        self.quality_thresholds = self.config.get('quality_thresholds', {})
        self.injection_settings = self.config.get('injection_settings', {})
        self.context_templates = self.config.get('context_templates', {})
        
        self.logger.info(f"Context injection engine initialized with {len(self.module_subscriptions)} module subscriptions")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load context injection configuration from YAML file"""
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
            return config
        except Exception as e:
            self.logger.error(f"Error loading context injection config: {e}")
            return {}
    
    async def get_context_for_module(self, module_id: str, context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get context for a specific module based on its subscriptions
        
        Args:
            module_id: Module identifier (rdi, cil, ctp, dm, td)
            context_data: Additional context data for filtering
            
        Returns:
            Context dictionary with relevant insights for the module
        """
        try:
            if module_id not in self.module_subscriptions:
                self.logger.warning(f"Unknown module: {module_id}")
                return {}
            
            module_config = self.module_subscriptions[module_id]
            subscribed_types = module_config.get('subscribed_strand_types', [])
            
            if not subscribed_types:
                self.logger.info(f"Module {module_id} has no subscribed strand types")
                return {}
            
            # Get context for each subscribed strand type
            context_results = {}
            for strand_type in subscribed_types:
                context = await self._get_context_for_strand_type(
                    strand_type, module_id, context_data
                )
                if context:
                    context_results[strand_type] = context
            
            # Format context for the module
            formatted_context = self._format_context_for_module(
                module_id, context_results, context_data
            )
            
            return formatted_context
            
        except Exception as e:
            self.logger.error(f"Error getting context for module {module_id}: {e}")
            return {}
    
    async def _get_context_for_strand_type(
        self, 
        strand_type: str, 
        module_id: str, 
        context_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Get context for a specific strand type"""
        try:
            # Query braids of this strand type
            braid_kind = f"{strand_type}_braid"
            
            # Build query with quality filters
            query = self.supabase_manager.supabase.table('AD_strands').select('*').eq('kind', braid_kind)
            
            # Apply quality thresholds
            min_braid_level = self.quality_thresholds.get('min_braid_level', 2)
            min_resonance = self.quality_thresholds.get('min_resonance_score', 0.6)
            max_age_days = self.quality_thresholds.get('max_age_days', 30)
            
            query = query.gte('braid_level', min_braid_level)
            query = query.gte('resonance_score', min_resonance)
            
            # Add date filter
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            query = query.gte('created_at', cutoff_date.isoformat())
            
            # Order by resonance score and recency
            query = query.order('resonance_score', desc=True).order('created_at', desc=True)
            
            # Limit results
            max_items = self.module_subscriptions[module_id].get('max_context_items', 10)
            query = query.limit(max_items)
            
            result = query.execute()
            braids = result.data if result.data else []
            
            if not braids:
                return {}
            
            # Extract insights from braids
            insights = []
            performance_metrics = {
                'total_braids': len(braids),
                'avg_resonance': 0.0,
                'avg_braid_level': 0.0,
                'recent_insights': []
            }
            
            total_resonance = 0
            total_level = 0
            
            for braid in braids:
                # Calculate metrics
                resonance = braid.get('resonance_score', 0.5)
                level = braid.get('braid_level', 1)
                total_resonance += resonance
                total_level += level
                
                # Extract learning insights
                content = braid.get('content', {})
                if 'learning_insights' in content:
                    insights.append(content['learning_insights'])
                
                # Extract recent insights (last 5)
                if len(insights) < 5:
                    recent_insight = {
                        'braid_id': braid.get('id'),
                        'resonance_score': resonance,
                        'braid_level': level,
                        'created_at': braid.get('created_at'),
                        'insights': content.get('learning_insights', {})
                    }
                    performance_metrics['recent_insights'].append(recent_insight)
            
            # Calculate averages
            if braids:
                performance_metrics['avg_resonance'] = total_resonance / len(braids)
                performance_metrics['avg_braid_level'] = total_level / len(braids)
            
            return {
                'strand_type': strand_type,
                'braid_count': len(braids),
                'insights': insights,
                'performance_metrics': performance_metrics,
                'context_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting context for strand type {strand_type}: {e}")
            return {}
    
    def _format_context_for_module(
        self, 
        module_id: str, 
        context_results: Dict[str, Any], 
        context_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Format context specifically for the module"""
        try:
            module_config = self.module_subscriptions[module_id]
            context_priority = module_config.get('context_priority', 'medium')
            
            # Get context template for this module
            template = self.context_templates.get(module_id, {})
            
            # Format context based on module type
            if module_id == 'cil':
                return self._format_cil_context(context_results, template)
            elif module_id == 'ctp':
                return self._format_ctp_context(context_results, template)
            elif module_id == 'dm':
                return self._format_dm_context(context_results, template)
            elif module_id == 'td':
                return self._format_td_context(context_results, template)
            else:
                return self._format_generic_context(context_results)
                
        except Exception as e:
            self.logger.error(f"Error formatting context for module {module_id}: {e}")
            return {}
    
    def _format_cil_context(self, context_results: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """Format context specifically for CIL module"""
        try:
            prediction_context = context_results.get('prediction_review', {})
            pattern_context = context_results.get('pattern_overview', {})
            
            # Calculate overall success rate
            total_braids = 0
            total_resonance = 0
            
            for context in [prediction_context, pattern_context]:
                if context:
                    metrics = context.get('performance_metrics', {})
                    total_braids += metrics.get('total_braids', 0)
                    total_resonance += metrics.get('avg_resonance', 0.5) * metrics.get('total_braids', 0)
            
            success_rate = (total_resonance / total_braids * 100) if total_braids > 0 else 0
            
            # Extract key insights
            insights = []
            approaches = []
            patterns = []
            
            for context in [prediction_context, pattern_context]:
                if context:
                    context_insights = context.get('insights', [])
                    for insight in context_insights:
                        if isinstance(insight, dict):
                            insights.append(insight.get('insights', 'No insights available'))
                            approaches.append(insight.get('recommendations', []))
                            patterns.append(insight.get('patterns', []))
            
            return {
                'module': 'cil',
                'context_type': 'prediction_enhancement',
                'success_rate': round(success_rate, 1),
                'insights': insights[:5],  # Limit to 5 insights
                'approaches': approaches[:3],  # Limit to 3 approaches
                'patterns': patterns[:3],  # Limit to 3 patterns
                'data_sources': list(context_results.keys()),
                'context_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting CIL context: {e}")
            return {}
    
    def _format_ctp_context(self, context_results: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """Format context specifically for CTP module"""
        try:
            prediction_context = context_results.get('prediction_review', {})
            trade_context = context_results.get('trade_outcome', {})
            execution_context = context_results.get('execution_outcome', {})
            
            # Calculate plan success metrics
            total_braids = 0
            total_resonance = 0
            
            for context in [prediction_context, trade_context, execution_context]:
                if context:
                    metrics = context.get('performance_metrics', {})
                    total_braids += metrics.get('total_braids', 0)
                    total_resonance += metrics.get('avg_resonance', 0.5) * metrics.get('total_braids', 0)
            
            success_rate = (total_resonance / total_braids * 100) if total_braids > 0 else 0
            
            # Extract strategies and insights
            strategies = []
            risk_insights = []
            adaptations = []
            
            for context in [prediction_context, trade_context, execution_context]:
                if context:
                    context_insights = context.get('insights', [])
                    for insight in context_insights:
                        if isinstance(insight, dict):
                            strategies.extend(insight.get('strategies', []))
                            risk_insights.extend(insight.get('risk_insights', []))
                            adaptations.extend(insight.get('adaptations', []))
            
            return {
                'module': 'ctp',
                'context_type': 'plan_enhancement',
                'success_rate': round(success_rate, 1),
                'strategies': strategies[:5],
                'risk_insights': risk_insights[:3],
                'adaptations': adaptations[:3],
                'data_sources': list(context_results.keys()),
                'context_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting CTP context: {e}")
            return {}
    
    def _format_dm_context(self, context_results: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """Format context specifically for DM module"""
        try:
            decision_context = context_results.get('trading_decision', {})
            portfolio_context = context_results.get('portfolio_outcome', {})
            plan_context = context_results.get('conditional_trading_plan', {})
            
            # Calculate decision quality metrics
            total_braids = 0
            total_resonance = 0
            
            for context in [decision_context, portfolio_context, plan_context]:
                if context:
                    metrics = context.get('performance_metrics', {})
                    total_braids += metrics.get('total_braids', 0)
                    total_resonance += metrics.get('avg_resonance', 0.5) * metrics.get('total_braids', 0)
            
            quality_score = (total_resonance / total_braids * 100) if total_braids > 0 else 0
            
            # Extract decision factors and insights
            factors = []
            risk_effectiveness = []
            portfolio_impact = []
            
            for context in [decision_context, portfolio_context, plan_context]:
                if context:
                    context_insights = context.get('insights', [])
                    for insight in context_insights:
                        if isinstance(insight, dict):
                            factors.extend(insight.get('factors', []))
                            risk_effectiveness.extend(insight.get('risk_effectiveness', []))
                            portfolio_impact.extend(insight.get('portfolio_impact', []))
            
            return {
                'module': 'dm',
                'context_type': 'decision_enhancement',
                'quality_score': round(quality_score, 1),
                'factors': factors[:5],
                'risk_effectiveness': risk_effectiveness[:3],
                'portfolio_impact': portfolio_impact[:3],
                'data_sources': list(context_results.keys()),
                'context_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting DM context: {e}")
            return {}
    
    def _format_td_context(self, context_results: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """Format context specifically for TD module"""
        try:
            execution_context = context_results.get('execution_outcome', {})
            decision_context = context_results.get('trading_decision', {})
            
            # Calculate execution success metrics
            total_braids = 0
            total_resonance = 0
            
            for context in [execution_context, decision_context]:
                if context:
                    metrics = context.get('performance_metrics', {})
                    total_braids += metrics.get('total_braids', 0)
                    total_resonance += metrics.get('avg_resonance', 0.5) * metrics.get('total_braids', 0)
            
            success_rate = (total_resonance / total_braids * 100) if total_braids > 0 else 0
            
            # Extract execution insights
            timing_insights = []
            slippage_performance = []
            venue_performance = []
            
            for context in [execution_context, decision_context]:
                if context:
                    context_insights = context.get('insights', [])
                    for insight in context_insights:
                        if isinstance(insight, dict):
                            timing_insights.extend(insight.get('timing_insights', []))
                            slippage_performance.extend(insight.get('slippage_performance', []))
                            venue_performance.extend(insight.get('venue_performance', []))
            
            return {
                'module': 'td',
                'context_type': 'execution_enhancement',
                'success_rate': round(success_rate, 1),
                'timing_insights': timing_insights[:5],
                'slippage_performance': slippage_performance[:3],
                'venue_performance': venue_performance[:3],
                'data_sources': list(context_results.keys()),
                'context_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting TD context: {e}")
            return {}
    
    def _format_generic_context(self, context_results: Dict[str, Any]) -> Dict[str, Any]:
        """Format generic context for unknown modules"""
        return {
            'module': 'unknown',
            'context_type': 'generic',
            'data_sources': list(context_results.keys()),
            'context_timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def get_module_subscriptions(self) -> Dict[str, Any]:
        """Get all module subscriptions for debugging/monitoring"""
        return self.module_subscriptions
    
    async def get_context_statistics(self) -> Dict[str, Any]:
        """Get context injection statistics"""
        try:
            stats = {
                'total_modules': len(self.module_subscriptions),
                'active_subscriptions': 0,
                'total_strand_types': 0,
                'module_breakdown': {}
            }
            
            for module_id, config in self.module_subscriptions.items():
                subscribed_types = config.get('subscribed_strand_types', [])
                stats['active_subscriptions'] += len(subscribed_types)
                stats['total_strand_types'] += len(subscribed_types)
                stats['module_breakdown'][module_id] = {
                    'subscribed_types': subscribed_types,
                    'max_context_items': config.get('max_context_items', 0),
                    'priority': config.get('context_priority', 'medium')
                }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting context statistics: {e}")
            return {}
