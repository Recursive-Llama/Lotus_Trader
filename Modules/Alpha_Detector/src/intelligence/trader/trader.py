"""
Trader Module

Elegant, focused Trader that executes approved trading decisions from DM
and manages the complete execution lifecycle. Integrates with the centralized
learning system for continuous improvement.

Key Features:
- Execute approved trading decisions
- Position management and P&L tracking
- Venue selection and execution optimization
- Performance monitoring and feedback
- Context injection from learning system
- Module-specific resonance scoring
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.llm_integration.prompt_manager import PromptManager
from src.learning_system.module_specific_scoring import ModuleSpecificScoring
from src.learning_system.centralized_learning_system import CentralizedLearningSystem


class ExecutionStatus(Enum):
    """Execution status types"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VenueType(Enum):
    """Trading venue types"""
    HYPERLIQUID = "hyperliquid"
    BINANCE = "binance"
    COINBASE = "coinbase"
    FALLBACK = "fallback"


class Trader:
    """
    Elegant Trader for executing approved trading decisions
    
    Core Responsibilities:
    1. Execute approved trading decisions from DM
    2. Manage positions and track P&L
    3. Optimize execution through venue selection
    4. Monitor performance and provide feedback
    5. Learn from execution outcomes and patterns
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(f"{__name__}.trader")
        
        # Learning system integration
        self.module_scoring = ModuleSpecificScoring(supabase_manager)
        self.learning_system = CentralizedLearningSystem(supabase_manager, llm_client, None)
        
        # Prompt system integration
        self.prompt_manager = PromptManager()
        
        # Execution state
        self.active_positions = {}
        self.execution_history = []
        self.venue_performance = {
            VenueType.HYPERLIQUID: {'success_rate': 0.95, 'avg_slippage': 0.001},
            VenueType.BINANCE: {'success_rate': 0.92, 'avg_slippage': 0.002},
            VenueType.COINBASE: {'success_rate': 0.90, 'avg_slippage': 0.003},
            VenueType.FALLBACK: {'success_rate': 0.85, 'avg_slippage': 0.005}
        }
        
        # Performance tracking
        self.performance_metrics = {
            'total_trades': 0,
            'successful_trades': 0,
            'total_pnl': 0.0,
            'avg_slippage': 0.0,
            'execution_speed_ms': 0.0
        }
    
    async def execute_decision(self, trading_decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an approved trading decision
        
        Args:
            trading_decision: Approved trading decision from DM
            
        Returns:
            Execution result with status and details
        """
        try:
            decision_id = trading_decision.get('decision_id')
            self.logger.info(f"Executing trading decision: {decision_id}")
            
            # Get context from learning system
            context = await self.get_execution_context()
            
            # 1. Validate decision
            validation = self._validate_decision(trading_decision)
            if not validation['valid']:
                return self._create_execution_result(ExecutionStatus.FAILED, validation['reason'])
            
            # 2. Select optimal venue
            venue = self._select_venue(trading_decision, context)
            
            # 3. Execute trade
            execution_result = await self._execute_trade(trading_decision, venue, context)
            
            # 4. Create execution outcome strand
            strand_id = await self._create_execution_strand(trading_decision, execution_result, context)
            
            # 5. Update performance metrics
            self._update_performance_metrics(execution_result)
            
            # 6. Track execution
            self.execution_history.append({
                'decision_id': decision_id,
                'execution_id': execution_result['execution_id'],
                'status': execution_result['status'],
                'timestamp': datetime.now(timezone.utc),
                'strand_id': strand_id
            })
            
            return execution_result
            
        except Exception as e:
            self.logger.error(f"Error executing trading decision: {e}")
            return self._create_execution_result(ExecutionStatus.FAILED, f"Execution error: {str(e)}")
    
    def _validate_decision(self, trading_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Validate trading decision before execution"""
        try:
            required_fields = ['decision_id', 'symbol', 'side', 'quantity', 'budget_allocation']
            
            for field in required_fields:
                if field not in trading_decision:
                    return {'valid': False, 'reason': f"Missing required field: {field}"}
            
            # Check budget allocation
            budget = trading_decision.get('budget_allocation', 0)
            if budget <= 0:
                return {'valid': False, 'reason': "Invalid budget allocation"}
            
            # Check symbol format
            symbol = trading_decision.get('symbol', '')
            if not symbol or len(symbol) < 3:
                return {'valid': False, 'reason': "Invalid symbol format"}
            
            return {'valid': True, 'reason': 'Decision validated successfully'}
            
        except Exception as e:
            self.logger.error(f"Error validating decision: {e}")
            return {'valid': False, 'reason': f"Validation error: {str(e)}"}
    
    def _select_venue(self, trading_decision: Dict[str, Any], context: Dict[str, Any]) -> VenueType:
        """Select optimal trading venue based on context and performance"""
        try:
            # Use LLM for complex venue selection if needed
            if self._should_use_llm_venue_selection(trading_decision, context):
                return self._llm_venue_selection(trading_decision, context)
            
            symbol = trading_decision.get('symbol', '')
            side = trading_decision.get('side', 'buy')
            quantity = trading_decision.get('quantity', 0)
            
            # Context-based venue selection
            context_venue_performance = context.get('venue_performance', {})
            pattern_accuracy = context.get('pattern_accuracy', 0.5)
            
            # Base venue selection logic
            if symbol.endswith('USDT') and quantity > 1000:
                # Large orders prefer Hyperliquid for better execution
                if context_venue_performance.get('hyperliquid', {}).get('success_rate', 0.95) > 0.9:
                    return VenueType.HYPERLIQUID
                else:
                    return VenueType.BINANCE
            elif pattern_accuracy > 0.8:
                # High confidence patterns use primary venue
                return VenueType.HYPERLIQUID
            else:
                # Lower confidence or smaller orders use secondary venue
                return VenueType.BINANCE
                
        except Exception as e:
            self.logger.error(f"Error selecting venue: {e}")
            return VenueType.HYPERLIQUID  # Default fallback
    
    async def _execute_trade(self, trading_decision: Dict[str, Any], 
                           venue: VenueType, 
                           context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actual trade"""
        try:
            execution_id = f"td_exec_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
            start_time = datetime.now(timezone.utc)
            
            # Simulate trade execution (replace with actual venue integration)
            execution_details = {
                'execution_id': execution_id,
                'venue': venue.value,
                'symbol': trading_decision.get('symbol'),
                'side': trading_decision.get('side'),
                'quantity': trading_decision.get('quantity'),
                'price': self._get_current_price(trading_decision.get('symbol')),
                'slippage': self._calculate_slippage(venue, trading_decision),
                'fees': self._calculate_fees(venue, trading_decision),
                'execution_time_ms': 0
            }
            
            # Simulate execution delay
            await asyncio.sleep(0.1)  # 100ms execution time
            
            end_time = datetime.now(timezone.utc)
            execution_details['execution_time_ms'] = (end_time - start_time).total_seconds() * 1000
            
            # Determine execution status
            if execution_details['slippage'] < 0.01:  # Less than 1% slippage
                status = ExecutionStatus.COMPLETED
            else:
                status = ExecutionStatus.COMPLETED  # Still completed but with higher slippage
            
            return {
                'execution_id': execution_id,
                'status': status.value,
                'execution_details': execution_details,
                'venue_performance': self.venue_performance[venue],
                'context_insights': {
                    'slippage_performance': context.get('slippage_performance', 0.5),
                    'timing_insights': context.get('timing_insights', 0.5),
                    'venue_performance': context.get('venue_performance', {}),
                    'pattern_recognition_accuracy': context.get('pattern_accuracy', 0.5),
                    'conditional_action_execution': context.get('conditional_action_execution', 0.5)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            return {
                'execution_id': f"error_{uuid.uuid4().hex[:8]}",
                'status': ExecutionStatus.FAILED.value,
                'execution_details': {},
                'error': str(e)
            }
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price for symbol (placeholder)"""
        # This would integrate with actual price feeds
        return 50000.0  # Placeholder price
    
    def _calculate_slippage(self, venue: VenueType, trading_decision: Dict[str, Any]) -> float:
        """Calculate expected slippage for venue and trade"""
        try:
            base_slippage = self.venue_performance[venue]['avg_slippage']
            quantity = trading_decision.get('quantity', 0)
            
            # Larger orders have more slippage
            size_multiplier = min(1.0 + (quantity / 10000), 2.0)
            
            return base_slippage * size_multiplier
            
        except Exception as e:
            self.logger.error(f"Error calculating slippage: {e}")
            return 0.01  # 1% default slippage
    
    def _calculate_fees(self, venue: VenueType, trading_decision: Dict[str, Any]) -> float:
        """Calculate trading fees for venue"""
        try:
            quantity = trading_decision.get('quantity', 0)
            price = self._get_current_price(trading_decision.get('symbol', ''))
            trade_value = quantity * price
            
            # Venue-specific fee rates
            fee_rates = {
                VenueType.HYPERLIQUID: 0.0001,  # 0.01%
                VenueType.BINANCE: 0.001,       # 0.1%
                VenueType.COINBASE: 0.005,      # 0.5%
                VenueType.FALLBACK: 0.01        # 1%
            }
            
            fee_rate = fee_rates.get(venue, 0.001)
            return trade_value * fee_rate
            
        except Exception as e:
            self.logger.error(f"Error calculating fees: {e}")
            return 0.0
    
    async def _create_execution_strand(self, trading_decision: Dict[str, Any], 
                                     execution_result: Dict[str, Any],
                                     context: Dict[str, Any]) -> str:
        """Create execution outcome strand in database"""
        try:
            execution_id = execution_result['execution_id']
            
            execution_data = {
                "id": execution_id,
                "module": "td",
                "kind": "execution_outcome",
                "symbol": trading_decision.get('symbol', 'UNKNOWN'),
                "timeframe": trading_decision.get('timeframe', '1h'),
                "tags": ['td', 'execution_outcome', execution_result['status']],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "braid_level": 1,
                "lesson": "",
                "content": {
                    "execution_id": execution_id,
                    "decision_id": trading_decision.get('decision_id'),
                    "status": execution_result['status'],
                    "execution_details": execution_result['execution_details'],
                    "venue_performance": execution_result.get('venue_performance', {}),
                    "context_insights": execution_result.get('context_insights', {}),
                    "created_at": datetime.now(timezone.utc).isoformat()
                },
                "module_intelligence": {
                    "execution_type": execution_result['status'],
                    "venue": execution_result['execution_details'].get('venue', 'unknown'),
                    "slippage": execution_result['execution_details'].get('slippage', 0.0),
                    "execution_time_ms": execution_result['execution_details'].get('execution_time_ms', 0),
                    "confidence": trading_decision.get('confidence', 0.5)
                }
            }
            
            # Calculate module-specific resonance scores
            try:
                scores = await self.module_scoring.calculate_module_scores(execution_data, 'td')
                execution_data['persistence_score'] = scores.get('persistence_score', 0.5)
                execution_data['novelty_score'] = scores.get('novelty_score', 0.5)
                execution_data['surprise_rating'] = scores.get('surprise_rating', 0.5)
                execution_data['resonance_score'] = scores.get('resonance_score', 0.5)
                
                execution_data['content']['resonance_scores'] = {
                    'phi': scores.get('phi', 0.5),
                    'rho': scores.get('rho', 0.5),
                    'theta': scores.get('theta', 0.5),
                    'omega': scores.get('omega', 0.5)
                }
                
                self.logger.info(f"Calculated TD resonance scores: φ={scores.get('phi', 0.5):.3f}, ρ={scores.get('rho', 0.5):.3f}, θ={scores.get('theta', 0.5):.3f}, ω={scores.get('omega', 0.5):.3f}")
                
            except Exception as e:
                self.logger.warning(f"Failed to calculate resonance scores: {e}")
                execution_data['persistence_score'] = 0.5
                execution_data['novelty_score'] = 0.5
                execution_data['surprise_rating'] = 0.5
                execution_data['resonance_score'] = 0.5
            
            # Store in database
            result = self.supabase_manager.insert_strand(execution_data)
            
            if result:
                self.logger.info(f"Created execution outcome strand: {execution_id}")
                return execution_id
            else:
                raise Exception("Failed to insert execution outcome strand")
                
        except Exception as e:
            self.logger.error(f"Error creating execution outcome strand: {e}")
            return f"error: {str(e)}"
    
    def _create_execution_result(self, status: ExecutionStatus, reason: str = "") -> Dict[str, Any]:
        """Create execution result"""
        return {
            'execution_id': f"error_{uuid.uuid4().hex[:8]}",
            'status': status.value,
            'execution_details': {},
            'reason': reason
        }
    
    def _update_performance_metrics(self, execution_result: Dict[str, Any]):
        """Update performance metrics based on execution result"""
        try:
            self.performance_metrics['total_trades'] += 1
            
            if execution_result['status'] == ExecutionStatus.COMPLETED.value:
                self.performance_metrics['successful_trades'] += 1
            
            # Update average slippage
            execution_details = execution_result.get('execution_details', {})
            if 'slippage' in execution_details:
                current_avg = self.performance_metrics['avg_slippage']
                total_trades = self.performance_metrics['total_trades']
                new_slippage = execution_details['slippage']
                
                self.performance_metrics['avg_slippage'] = (
                    (current_avg * (total_trades - 1) + new_slippage) / total_trades
                )
            
            # Update execution speed
            if 'execution_time_ms' in execution_details:
                current_avg = self.performance_metrics['execution_speed_ms']
                total_trades = self.performance_metrics['total_trades']
                new_time = execution_details['execution_time_ms']
                
                self.performance_metrics['execution_speed_ms'] = (
                    (current_avg * (total_trades - 1) + new_time) / total_trades
                )
                
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
    
    async def get_execution_context(self, context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get context for TD execution from the learning system"""
        try:
            return await self.learning_system.get_context_for_module('td', context_data)
        except Exception as e:
            self.logger.error(f"Error getting execution context: {e}")
            return {}
    
    async def update_venue_performance(self, venue: VenueType, success: bool, slippage: float):
        """Update venue performance metrics"""
        try:
            venue_data = self.venue_performance[venue]
            
            # Update success rate (simple moving average)
            current_rate = venue_data['success_rate']
            venue_data['success_rate'] = (current_rate * 0.9) + (1.0 if success else 0.0) * 0.1
            
            # Update average slippage
            current_slippage = venue_data['avg_slippage']
            venue_data['avg_slippage'] = (current_slippage * 0.9) + slippage * 0.1
            
            self.logger.info(f"Updated {venue.value} performance: success_rate={venue_data['success_rate']:.3f}, avg_slippage={venue_data['avg_slippage']:.4f}")
            
        except Exception as e:
            self.logger.error(f"Error updating venue performance: {e}")
    
    def _should_use_llm_venue_selection(self, trading_decision: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Determine if LLM should be used for venue selection"""
        try:
            # Use LLM for complex or high-value executions
            quantity = trading_decision.get('quantity', 0)
            budget = trading_decision.get('budget_allocation', 0)
            
            # High value trades
            if budget > 5000 or quantity > 500:
                return True
            
            # Complex market conditions
            market_volatility = context.get('market_volatility', 'normal')
            if market_volatility == 'high':
                return True
            
            # Low confidence patterns
            pattern_accuracy = context.get('pattern_accuracy', 0.5)
            if pattern_accuracy < 0.6:
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error determining LLM venue selection need: {e}")
            return False
    
    def _llm_venue_selection(self, trading_decision: Dict[str, Any], context: Dict[str, Any]) -> VenueType:
        """Use LLM for venue selection analysis"""
        try:
            # Get prompt template
            prompt_template = self.prompt_manager.get_prompt('execution_analysis')
            
            # Prepare context variables
            context_vars = {
                'decision_id': trading_decision.get('decision_id', 'unknown'),
                'symbol': trading_decision.get('symbol', 'UNKNOWN'),
                'side': trading_decision.get('side', 'buy'),
                'quantity': trading_decision.get('quantity', 0),
                'budget_allocation': trading_decision.get('budget_allocation', 0),
                'approved_leverage': trading_decision.get('approved_leverage', 1),
                'current_price': self._get_current_price(trading_decision.get('symbol', '')),
                'market_volatility': context.get('market_volatility', 'normal'),
                'order_size': trading_decision.get('quantity', 0),
                'time_sensitivity': context.get('time_sensitivity', 'normal'),
                'hyperliquid_success': self.venue_performance[VenueType.HYPERLIQUID]['success_rate'] * 100,
                'hyperliquid_slippage': self.venue_performance[VenueType.HYPERLIQUID]['avg_slippage'] * 100,
                'binance_success': self.venue_performance[VenueType.BINANCE]['success_rate'] * 100,
                'binance_slippage': self.venue_performance[VenueType.BINANCE]['avg_slippage'] * 100,
                'coinbase_success': self.venue_performance[VenueType.COINBASE]['success_rate'] * 100,
                'coinbase_slippage': self.venue_performance[VenueType.COINBASE]['avg_slippage'] * 100,
                'execution_success_rate': context.get('execution_success_rate', 0.5) * 100,
                'slippage_performance': context.get('slippage_performance', 0.5) * 100,
                'timing_insights': context.get('timing_insights', 0.5) * 100,
                'pattern_accuracy': context.get('pattern_accuracy', 0.5) * 100,
                'conditional_execution': context.get('conditional_execution', 0.5) * 100
            }
            
            # Generate LLM response (synchronous for now)
            # Note: This would need to be async in real implementation
            response = "hyperliquid"  # Placeholder - would call LLM here
            
            # Parse response to determine venue
            if 'hyperliquid' in response.lower():
                return VenueType.HYPERLIQUID
            elif 'binance' in response.lower():
                return VenueType.BINANCE
            elif 'coinbase' in response.lower():
                return VenueType.COINBASE
            else:
                return VenueType.HYPERLIQUID  # Default fallback
                
        except Exception as e:
            self.logger.error(f"Error in LLM venue selection: {e}")
            return VenueType.HYPERLIQUID  # Default fallback
    
    async def get_execution_statistics(self) -> Dict[str, Any]:
        """Get execution statistics for monitoring"""
        try:
            total_trades = self.performance_metrics['total_trades']
            successful_trades = self.performance_metrics['successful_trades']
            
            return {
                'total_trades': total_trades,
                'successful_trades': successful_trades,
                'failed_trades': total_trades - successful_trades,
                'success_rate': successful_trades / total_trades if total_trades > 0 else 0,
                'avg_slippage': self.performance_metrics['avg_slippage'],
                'avg_execution_speed_ms': self.performance_metrics['execution_speed_ms'],
                'venue_performance': self.venue_performance,
                'active_positions': len(self.active_positions)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting execution statistics: {e}")
            return {}
