"""
Trader Team Coordinator - Coordinates all Trader Team components

This component coordinates all Trader Team components, managing the complete
execution flow from trading plan to learning contribution, and ensuring
seamless integration with the existing system architecture.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

# Import all Trader Team components
from .order_manager import OrderManager
from .performance_analyzer import PerformanceAnalyzer
from .position_tracker import PositionTracker
from .hyperliquid_integration import HyperliquidIntegration
from .venue_fallback_manager import VenueFallbackManager
from .cil_integration import CILIntegration

logger = logging.getLogger(__name__)


class TraderTeamCoordinator:
    """Coordinates all Trader Team components"""
    
    def __init__(self, supabase_manager, llm_client, hyperliquid_api_key: str = "", hyperliquid_api_secret: str = ""):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        
        # Initialize all Trader Team components
        self.order_manager = OrderManager(supabase_manager, llm_client)
        self.performance_analyzer = PerformanceAnalyzer(supabase_manager, llm_client)
        self.position_tracker = PositionTracker(supabase_manager, llm_client)
        self.hyperliquid_integration = HyperliquidIntegration(supabase_manager, llm_client, hyperliquid_api_key, hyperliquid_api_secret)
        self.venue_fallback_manager = VenueFallbackManager(supabase_manager, llm_client)
        self.cil_integration = CILIntegration(supabase_manager, llm_client)
        
        # Coordination state
        self.active_executions = {}
        self.execution_history = []
        self.team_status = {
            'order_manager': 'active',
            'performance_analyzer': 'active',
            'position_tracker': 'active',
            'hyperliquid_integration': 'active',
            'venue_fallback_manager': 'active',
            'cil_integration': 'active'
        }
        
        # Execution flow state
        self.current_executions = {}
        self.execution_metrics = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'average_execution_time': 0.0,
            'last_execution': None
        }
        
    async def execute_trading_plan(self, trading_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute complete trading plan
        
        Args:
            trading_plan: Trading plan from Decision Maker
            
        Returns:
            Dict with execution result
        """
        try:
            execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            symbol = trading_plan.get('symbol', '')
            
            logger.info(f"Starting execution of trading plan {execution_id} for {symbol}")
            
            # Initialize execution tracking
            execution_data = {
                'execution_id': execution_id,
                'trading_plan': trading_plan,
                'started_at': datetime.now(),
                'status': 'started',
                'components_used': []
            }
            
            self.current_executions[execution_id] = execution_data
            
            # Step 1: Consume CIL insights for execution context
            execution_context = {
                'symbol': symbol,
                'execution_type': 'trading_plan_execution',
                'trading_plan': trading_plan
            }
            
            cil_insights = await self.cil_integration.consume_cil_insights(execution_context)
            execution_data['cil_insights'] = cil_insights
            execution_data['components_used'].append('cil_integration')
            
            # Step 2: Monitor entry conditions
            condition_result = await self.order_manager.monitor_entry_conditions(trading_plan)
            execution_data['condition_result'] = condition_result
            execution_data['components_used'].append('order_manager')
            
            if not condition_result.get('ready', False):
                execution_data['status'] = 'waiting_for_conditions'
                execution_data['message'] = 'Waiting for entry conditions to be met'
                return execution_data
            
            # Step 3: Place order when conditions are met
            order_result = await self.order_manager.place_order_when_ready(trading_plan)
            execution_data['order_result'] = order_result
            execution_data['components_used'].append('order_manager')
            
            if not order_result.get('order_placed', False):
                execution_data['status'] = 'order_failed'
                execution_data['message'] = order_result.get('message', 'Order placement failed')
                await self._handle_execution_failure(execution_data)
                return execution_data
            
            # Step 4: Track order lifecycle
            order_id = order_result.get('order_id', '')
            order_tracking = await self.order_manager.track_order_lifecycle(order_id)
            execution_data['order_tracking'] = order_tracking
            execution_data['order_id'] = order_id
            
            # Step 5: Monitor position updates
            if order_tracking.get('order_status') == 'filled':
                position_data = {
                    'position_id': f"pos_{execution_id}",
                    'symbol': symbol,
                    'order_id': order_id,
                    'entry_price': order_result.get('filled_price', 0),
                    'quantity': trading_plan.get('order_details', {}).get('quantity', 0),
                    'side': trading_plan.get('order_details', {}).get('side', 'long')
                }
                
                position_result = await self.position_tracker.track_position_updates(position_data)
                execution_data['position_result'] = position_result
                execution_data['components_used'].append('position_tracker')
                
                # Step 6: Analyze execution quality
                execution_quality = await self.performance_analyzer.analyze_execution_quality(order_result)
                execution_data['execution_quality'] = execution_quality
                execution_data['components_used'].append('performance_analyzer')
                
                # Step 7: Contribute to learning system
                learning_contribution = await self.cil_integration.contribute_execution_learning(execution_data)
                execution_data['learning_contribution'] = learning_contribution
                execution_data['components_used'].append('cil_integration')
                
                execution_data['status'] = 'completed'
                execution_data['message'] = 'Trading plan executed successfully'
                
                # Update execution metrics
                await self._update_execution_metrics(execution_data, success=True)
                
            else:
                execution_data['status'] = 'order_pending'
                execution_data['message'] = 'Order placed but not yet filled'
            
            # Move to execution history
            execution_data['completed_at'] = datetime.now()
            self.execution_history.append(execution_data)
            
            # Remove from current executions
            if execution_id in self.current_executions:
                del self.current_executions[execution_id]
            
            # Publish execution summary strand
            await self._publish_execution_summary_strand(execution_data)
            
            logger.info(f"Completed execution {execution_id} with status: {execution_data['status']}")
            return execution_data
            
        except Exception as e:
            logger.error(f"Error executing trading plan: {e}")
            execution_data['status'] = 'error'
            execution_data['message'] = str(e)
            execution_data['error'] = str(e)
            
            await self._handle_execution_failure(execution_data)
            return execution_data
    
    async def coordinate_team_activities(self):
        """Coordinate ongoing team activities"""
        try:
            logger.info("Starting team activity coordination")
            
            # Monitor active executions
            await self._monitor_active_executions()
            
            # Update position tracking
            await self._update_position_tracking()
            
            # Analyze performance
            await self._analyze_ongoing_performance()
            
            # Contribute insights to CIL
            await self._contribute_ongoing_insights()
            
            # Handle venue fallbacks
            await self._handle_venue_fallbacks()
            
            # Update team status
            await self._update_team_status()
            
            logger.info("Completed team activity coordination")
            
        except Exception as e:
            logger.error(f"Error in team activity coordination: {e}")
    
    async def _monitor_active_executions(self):
        """Monitor active executions"""
        try:
            for execution_id, execution_data in self.current_executions.items():
                if execution_data['status'] == 'waiting_for_conditions':
                    # Re-check conditions
                    trading_plan = execution_data['trading_plan']
                    condition_result = await self.order_manager.monitor_entry_conditions(trading_plan)
                    
                    if condition_result.get('ready', False):
                        # Conditions met, place order
                        order_result = await self.order_manager.place_order_when_ready(trading_plan)
                        execution_data['order_result'] = order_result
                        
                        if order_result.get('order_placed', False):
                            execution_data['status'] = 'order_placed'
                            execution_data['order_id'] = order_result.get('order_id', '')
                        else:
                            execution_data['status'] = 'order_failed'
                            execution_data['message'] = order_result.get('message', 'Order placement failed')
                
                elif execution_data['status'] == 'order_placed':
                    # Track order status
                    order_id = execution_data.get('order_id', '')
                    if order_id:
                        order_tracking = await self.order_manager.track_order_lifecycle(order_id)
                        execution_data['order_tracking'] = order_tracking
                        
                        if order_tracking.get('order_status') == 'filled':
                            execution_data['status'] = 'order_filled'
                        elif order_tracking.get('order_status') == 'cancelled':
                            execution_data['status'] = 'order_cancelled'
            
        except Exception as e:
            logger.error(f"Error monitoring active executions: {e}")
    
    async def _update_position_tracking(self):
        """Update position tracking for all active positions"""
        try:
            # Get active positions from position tracker
            active_positions = await self.position_tracker.get_active_positions()
            
            for position_id, position_data in active_positions.get('active_positions', {}).items():
                # Update position with current market data
                updated_position = await self.position_tracker.track_position_updates(position_data)
                
                # Monitor risk metrics
                risk_result = await self.position_tracker.monitor_risk_metrics(position_data)
                
                # Publish position updates
                await self.position_tracker.publish_position_strands(updated_position)
            
        except Exception as e:
            logger.error(f"Error updating position tracking: {e}")
    
    async def _analyze_ongoing_performance(self):
        """Analyze ongoing performance"""
        try:
            # Get recent execution history
            recent_executions = self.execution_history[-10:]  # Last 10 executions
            
            for execution in recent_executions:
                if execution.get('status') == 'completed' and 'execution_quality' not in execution:
                    # Analyze execution quality for completed executions
                    order_result = execution.get('order_result', {})
                    if order_result:
                        execution_quality = await self.performance_analyzer.analyze_execution_quality(order_result)
                        execution['execution_quality'] = execution_quality
            
        except Exception as e:
            logger.error(f"Error analyzing ongoing performance: {e}")
    
    async def _contribute_ongoing_insights(self):
        """Contribute ongoing insights to CIL"""
        try:
            # Get recent execution data
            recent_executions = self.execution_history[-5:]  # Last 5 executions
            
            for execution in recent_executions:
                if execution.get('status') == 'completed':
                    # Contribute execution learning
                    await self.cil_integration.contribute_execution_learning(execution)
                    
                    # Participate in resonance calculations
                    if 'execution_quality' in execution:
                        execution_pattern = {
                            'pattern_type': 'execution_quality',
                            'execution_score': execution['execution_quality'].get('execution_score', 0),
                            'success_rate': 1.0 if execution['status'] == 'completed' else 0.0,
                            'frequency': 1
                        }
                        await self.cil_integration.participate_in_resonance(execution_pattern)
            
        except Exception as e:
            logger.error(f"Error contributing ongoing insights: {e}")
    
    async def _handle_venue_fallbacks(self):
        """Handle venue fallbacks"""
        try:
            # Check venue availability
            venue_summary = await self.venue_fallback_manager.get_venue_summary()
            
            for venue, status in venue_summary.get('availability_status', {}).items():
                if not status.get('available', True):
                    # Venue is unavailable, update status
                    await self.venue_fallback_manager.update_venue_availability(
                        venue, False, status.get('reason', 'Unknown reason')
                    )
            
        except Exception as e:
            logger.error(f"Error handling venue fallbacks: {e}")
    
    async def _update_team_status(self):
        """Update team status"""
        try:
            # Check component health
            team_status = {}
            
            # Check order manager
            try:
                active_orders = await self.order_manager.get_active_orders()
                team_status['order_manager'] = 'active' if active_orders else 'idle'
            except:
                team_status['order_manager'] = 'error'
            
            # Check performance analyzer
            try:
                execution_summary = await self.performance_analyzer.get_execution_summary()
                team_status['performance_analyzer'] = 'active'
            except:
                team_status['performance_analyzer'] = 'error'
            
            # Check position tracker
            try:
                active_positions = await self.position_tracker.get_active_positions()
                team_status['position_tracker'] = 'active'
            except:
                team_status['position_tracker'] = 'error'
            
            # Check Hyperliquid integration
            try:
                connection_status = await self.hyperliquid_integration.get_connection_status()
                team_status['hyperliquid_integration'] = 'active' if connection_status.get('websocket_connected', False) else 'disconnected'
            except:
                team_status['hyperliquid_integration'] = 'error'
            
            # Check venue fallback manager
            try:
                venue_summary = await self.venue_fallback_manager.get_venue_summary()
                team_status['venue_fallback_manager'] = 'active'
            except:
                team_status['venue_fallback_manager'] = 'error'
            
            # Check CIL integration
            try:
                cil_summary = await self.cil_integration.get_cil_integration_summary()
                team_status['cil_integration'] = 'active'
            except:
                team_status['cil_integration'] = 'error'
            
            self.team_status = team_status
            
            # Publish team status strand
            await self._publish_team_status_strand(team_status)
            
        except Exception as e:
            logger.error(f"Error updating team status: {e}")
    
    async def _handle_execution_failure(self, execution_data: Dict[str, Any]):
        """Handle execution failure"""
        try:
            execution_data['status'] = 'failed'
            execution_data['failed_at'] = datetime.now()
            
            # Update execution metrics
            await self._update_execution_metrics(execution_data, success=False)
            
            # Publish failure strand
            await self._publish_execution_failure_strand(execution_data)
            
            logger.error(f"Execution {execution_data.get('execution_id', '')} failed: {execution_data.get('message', '')}")
            
        except Exception as e:
            logger.error(f"Error handling execution failure: {e}")
    
    async def _update_execution_metrics(self, execution_data: Dict[str, Any], success: bool):
        """Update execution metrics"""
        try:
            self.execution_metrics['total_executions'] += 1
            
            if success:
                self.execution_metrics['successful_executions'] += 1
            else:
                self.execution_metrics['failed_executions'] += 1
            
            # Calculate average execution time
            if execution_data.get('started_at') and execution_data.get('completed_at'):
                execution_time = (execution_data['completed_at'] - execution_data['started_at']).total_seconds()
                total_executions = self.execution_metrics['total_executions']
                current_avg = self.execution_metrics['average_execution_time']
                self.execution_metrics['average_execution_time'] = (current_avg * (total_executions - 1) + execution_time) / total_executions
            
            self.execution_metrics['last_execution'] = datetime.now()
            
        except Exception as e:
            logger.error(f"Error updating execution metrics: {e}")
    
    async def _publish_execution_summary_strand(self, execution_data: Dict[str, Any]):
        """Publish execution summary strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'execution_summary',
                'symbol': execution_data.get('trading_plan', {}).get('symbol', ''),
                'content': {
                    'execution_id': execution_data.get('execution_id', ''),
                    'status': execution_data.get('status', ''),
                    'message': execution_data.get('message', ''),
                    'components_used': execution_data.get('components_used', []),
                    'execution_metrics': {
                        'started_at': execution_data.get('started_at', datetime.now()).isoformat(),
                        'completed_at': execution_data.get('completed_at', datetime.now()).isoformat(),
                        'duration_seconds': (execution_data.get('completed_at', datetime.now()) - execution_data.get('started_at', datetime.now())).total_seconds()
                    },
                    'summary_timestamp': datetime.now().isoformat()
                },
                'tags': ['trader:execution_summary', 'trader:coordination', 'cil:execution_insights']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published execution summary strand for {execution_data.get('execution_id', '')}")
            
        except Exception as e:
            logger.error(f"Error publishing execution summary strand: {e}")
    
    async def _publish_execution_failure_strand(self, execution_data: Dict[str, Any]):
        """Publish execution failure strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'execution_failure',
                'symbol': execution_data.get('trading_plan', {}).get('symbol', ''),
                'content': {
                    'execution_id': execution_data.get('execution_id', ''),
                    'status': execution_data.get('status', ''),
                    'message': execution_data.get('message', ''),
                    'error': execution_data.get('error', ''),
                    'components_used': execution_data.get('components_used', []),
                    'failed_at': execution_data.get('failed_at', datetime.now()).isoformat(),
                    'failure_timestamp': datetime.now().isoformat()
                },
                'tags': ['trader:execution_failure', 'trader:coordination', 'cil:execution_insights']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info(f"Published execution failure strand for {execution_data.get('execution_id', '')}")
            
        except Exception as e:
            logger.error(f"Error publishing execution failure strand: {e}")
    
    async def _publish_team_status_strand(self, team_status: Dict[str, Any]):
        """Publish team status strand to AD_strands"""
        try:
            strand_data = {
                'module': 'trader',
                'kind': 'team_status',
                'content': {
                    'team_status': team_status,
                    'execution_metrics': self.execution_metrics,
                    'active_executions_count': len(self.current_executions),
                    'execution_history_count': len(self.execution_history),
                    'status_timestamp': datetime.now().isoformat()
                },
                'tags': ['trader:team_status', 'trader:coordination', 'cil:system_status']
            }
            
            await self.supabase_manager.insert_data('AD_strands', strand_data)
            logger.info("Published team status strand")
            
        except Exception as e:
            logger.error(f"Error publishing team status strand: {e}")
    
    async def get_team_summary(self) -> Dict[str, Any]:
        """Get comprehensive team summary"""
        try:
            # Get component summaries
            order_summary = await self.order_manager.get_active_orders()
            performance_summary = await self.performance_analyzer.get_execution_summary()
            position_summary = await self.position_tracker.get_active_positions()
            hyperliquid_status = await self.hyperliquid_integration.get_connection_status()
            venue_summary = await self.venue_fallback_manager.get_venue_summary()
            cil_summary = await self.cil_integration.get_cil_integration_summary()
            
            return {
                'team_status': self.team_status,
                'execution_metrics': self.execution_metrics,
                'active_executions': len(self.current_executions),
                'execution_history_count': len(self.execution_history),
                'component_summaries': {
                    'order_manager': order_summary,
                    'performance_analyzer': performance_summary,
                    'position_tracker': position_summary,
                    'hyperliquid_integration': hyperliquid_status,
                    'venue_fallback_manager': venue_summary,
                    'cil_integration': cil_summary
                },
                'summary_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting team summary: {e}")
            return {
                'error': str(e),
                'summary_timestamp': datetime.now().isoformat()
            }
    
    async def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get execution history"""
        return self.execution_history[-limit:] if limit > 0 else self.execution_history
    
    async def get_active_executions(self) -> Dict[str, Any]:
        """Get active executions"""
        return {
            'active_executions': self.current_executions,
            'count': len(self.current_executions),
            'timestamp': datetime.now().isoformat()
        }
    
    async def cancel_execution(self, execution_id: str) -> Dict[str, Any]:
        """Cancel an active execution"""
        try:
            if execution_id not in self.current_executions:
                return {
                    'status': 'error',
                    'message': f'Execution {execution_id} not found in active executions'
                }
            
            execution_data = self.current_executions[execution_id]
            
            # Cancel order if it exists
            order_id = execution_data.get('order_id', '')
            if order_id:
                cancel_result = await self.order_manager.cancel_order(order_id)
                execution_data['cancel_result'] = cancel_result
            
            # Update execution status
            execution_data['status'] = 'cancelled'
            execution_data['cancelled_at'] = datetime.now()
            
            # Move to history
            self.execution_history.append(execution_data)
            
            # Remove from active executions
            del self.current_executions[execution_id]
            
            return {
                'status': 'success',
                'execution_id': execution_id,
                'cancelled_at': execution_data['cancelled_at'].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error cancelling execution: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
