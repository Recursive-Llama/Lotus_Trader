"""
Decision Maker Core Module

Implements the core Decision Maker functionality as described in CTP_DM_TRADER_ARCHITECTURE.md:
- Risk assessment and budget allocation
- Leverage decision logic
- Trading plan evaluation and approval
- Integration with centralized learning system
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.intelligence.universal_learning.module_specific_scoring import ModuleSpecificScoring
from src.intelligence.universal_learning.centralized_learning_system import CentralizedLearningSystem


class DecisionType(Enum):
    """Decision types for trading plans"""
    APPROVE = "approved"
    REJECT = "rejected"
    MODIFY = "modified"


class MarketRegime(Enum):
    """Market regime types"""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


class DecisionMakerCore:
    """
    Core Decision Maker module for risk assessment and budget allocation
    
    Responsibilities:
    1. Evaluate conditional trading plans from CTP
    2. Assess portfolio risk and allocate budget
    3. Convert leverage scores to actual leverage
    4. Make approve/reject decisions with reasoning
    5. Learn from portfolio outcomes and past decisions
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(f"{__name__}.decision_maker_core")
        
        # Learning system integration
        self.module_scoring = ModuleSpecificScoring(supabase_manager)
        self.learning_system = CentralizedLearningSystem(supabase_manager, llm_client, None)
        
        # Risk limits and portfolio state
        self.portfolio_state = {
            'total_capital': 100000,
            'available_capital': 25000,
            'open_positions': [],
            'open_orders': [],
            'risk_limits': {
                'max_portfolio_risk': 0.15,
                'max_single_position_risk': 0.05,
                'max_leverage': 3
            }
        }
        
        # Market regime detection
        self.current_market_regime = MarketRegime.SIDEWAYS
        
        # Decision tracking
        self.decision_history = []
        self.learning_thresholds = {
            'min_decisions_for_learning': 5,
            'min_success_rate': 0.4,
            'min_sample_size': 3
        }
    
    async def evaluate_trading_plan(self, trading_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a conditional trading plan and make a decision
        
        Args:
            trading_plan: Conditional trading plan from CTP
            
        Returns:
            Decision result with approval/rejection and reasoning
        """
        try:
            self.logger.info(f"Evaluating trading plan: {trading_plan.get('plan_id', 'unknown')}")
            
            # Get context from learning system
            context = await self.get_decision_context()
            
            # 1. Portfolio risk assessment
            risk_assessment = await self.assess_portfolio_risk(trading_plan)
            
            # 2. Convert leverage score to actual leverage
            actual_leverage = self.convert_leverage_score_to_actual(
                trading_plan.get('leverage_score', 0.5),
                self.current_market_regime
            )
            
            # 3. Calculate budget allocation
            budget_allocation = self.calculate_budget_allocation(
                trading_plan, risk_assessment, actual_leverage
            )
            
            # 4. Make decision based on risk and context
            decision_result = await self.make_decision(
                trading_plan, risk_assessment, budget_allocation, actual_leverage, context
            )
            
            # 5. Create trading decision strand
            decision_strand_id = await self.create_trading_decision_strand(
                trading_plan, decision_result, risk_assessment, budget_allocation, actual_leverage
            )
            
            # 6. Update decision history
            self.decision_history.append({
                'plan_id': trading_plan.get('plan_id'),
                'decision': decision_result['decision'],
                'timestamp': datetime.now(timezone.utc),
                'strand_id': decision_strand_id
            })
            
            return decision_result
            
        except Exception as e:
            self.logger.error(f"Error evaluating trading plan: {e}")
            return {
                'decision': 'rejected',
                'reasoning': f'Evaluation error: {str(e)}',
                'budget_allocation': 0,
                'approved_leverage': 1
            }
    
    async def assess_portfolio_risk(self, trading_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess if trading plan fits within portfolio risk limits
        
        Args:
            trading_plan: Trading plan to assess
            
        Returns:
            Risk assessment result
        """
        try:
            # Get plan risk score
            plan_risk_score = trading_plan.get('risk_score', 0.5)
            leverage_score = trading_plan.get('leverage_score', 0.5)
            
            # Convert leverage score to actual leverage
            actual_leverage = self.convert_leverage_score_to_actual(leverage_score, self.current_market_regime)
            
            # Calculate proposed position risk
            proposed_risk = plan_risk_score * actual_leverage
            
            # Check against portfolio limits
            single_position_limit = self.portfolio_state['risk_limits']['max_single_position_risk']
            portfolio_limit = self.portfolio_state['risk_limits']['max_portfolio_risk']
            
            # Calculate current portfolio risk
            current_portfolio_risk = self.calculate_current_portfolio_risk()
            total_risk = current_portfolio_risk + proposed_risk
            
            # Risk assessment result
            risk_assessment = {
                'proposed_risk': proposed_risk,
                'current_portfolio_risk': current_portfolio_risk,
                'total_risk': total_risk,
                'single_position_limit': single_position_limit,
                'portfolio_limit': portfolio_limit,
                'within_single_position_limit': proposed_risk <= single_position_limit,
                'within_portfolio_limit': total_risk <= portfolio_limit,
                'leverage_approved': actual_leverage <= self.portfolio_state['risk_limits']['max_leverage']
            }
            
            return risk_assessment
            
        except Exception as e:
            self.logger.error(f"Error assessing portfolio risk: {e}")
            return {
                'proposed_risk': 1.0,  # High risk if error
                'within_single_position_limit': False,
                'within_portfolio_limit': False,
                'leverage_approved': False
            }
    
    def convert_leverage_score_to_actual(self, leverage_score: float, market_regime: MarketRegime) -> int:
        """
        Convert CTP leverage score (0.0-1.0) to actual leverage based on market conditions
        
        Args:
            leverage_score: 0.0-1.0 score from CTP
            market_regime: Current market regime
            
        Returns:
            Actual leverage multiplier (1x, 2x, 3x, etc.)
        """
        try:
            # Base leverage from score (1x to 5x range)
            base_leverage = 1 + int(leverage_score * 4)
            
            # Market regime adjustments
            regime_adjustments = {
                MarketRegime.BULL_MARKET: 1.2,
                MarketRegime.BEAR_MARKET: 0.7,
                MarketRegime.SIDEWAYS: 1.0,
                MarketRegime.HIGH_VOLATILITY: 0.6,
                MarketRegime.LOW_VOLATILITY: 1.3
            }
            
            adjustment = regime_adjustments.get(market_regime, 1.0)
            adjusted_leverage = int(base_leverage * adjustment)
            
            # Apply portfolio risk limits
            max_leverage = self.portfolio_state['risk_limits']['max_leverage']
            final_leverage = min(adjusted_leverage, max_leverage)
            
            # Ensure minimum leverage
            return max(final_leverage, 1)
            
        except Exception as e:
            self.logger.error(f"Error converting leverage score: {e}")
            return 1  # Conservative default
    
    def calculate_budget_allocation(self, trading_plan: Dict[str, Any], 
                                  risk_assessment: Dict[str, Any], 
                                  actual_leverage: int) -> Dict[str, Any]:
        """
        Calculate budget allocation for the trading plan
        
        Args:
            trading_plan: Trading plan to allocate budget for
            risk_assessment: Risk assessment result
            actual_leverage: Approved leverage
            
        Returns:
            Budget allocation result
        """
        try:
            # Get available capital
            available_cash = self.portfolio_state['available_capital']
            
            # Calculate max position value with leverage
            max_position_value = available_cash * actual_leverage
            
            # Calculate position size based on risk
            plan_risk_score = trading_plan.get('risk_score', 0.5)
            risk_per_dollar = plan_risk_score / max_position_value if max_position_value > 0 else 1.0
            max_safe_position = self.portfolio_state['risk_limits']['max_single_position_risk'] / risk_per_dollar
            
            # Final budget allocation
            allocated_budget = min(max_position_value, max_safe_position)
            
            # Apply minimum budget threshold
            min_budget = 1000  # Minimum $1000 allocation
            if allocated_budget < min_budget:
                allocated_budget = 0  # Reject if too small
            
            return {
                'budget_amount': allocated_budget,
                'leverage': actual_leverage,
                'max_position_value': max_position_value,
                'risk_per_dollar': risk_per_dollar,
                'allocation_approved': allocated_budget >= min_budget
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating budget allocation: {e}")
            return {
                'budget_amount': 0,
                'leverage': 1,
                'allocation_approved': False
            }
    
    async def make_decision(self, trading_plan: Dict[str, Any], 
                          risk_assessment: Dict[str, Any], 
                          budget_allocation: Dict[str, Any], 
                          actual_leverage: int,
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make final decision on trading plan
        
        Args:
            trading_plan: Trading plan to decide on
            risk_assessment: Risk assessment result
            budget_allocation: Budget allocation result
            actual_leverage: Approved leverage
            context: Learning context
            
        Returns:
            Decision result
        """
        try:
            # Decision criteria
            within_risk_limits = (risk_assessment['within_single_position_limit'] and 
                                risk_assessment['within_portfolio_limit'])
            allocation_approved = budget_allocation['allocation_approved']
            leverage_approved = risk_assessment['leverage_approved']
            
            # Context-based adjustments
            context_success_rate = context.get('success_rate', 0.5)
            context_risk_effectiveness = context.get('risk_effectiveness', 0.5)
            
            # Decision logic
            if not within_risk_limits:
                decision = DecisionType.REJECT
                reasoning = "Exceeds portfolio risk limits"
            elif not allocation_approved:
                decision = DecisionType.REJECT
                reasoning = "Budget allocation too small or unavailable"
            elif not leverage_approved:
                decision = DecisionType.REJECT
                reasoning = "Leverage exceeds maximum allowed"
            elif context_success_rate < 0.3:
                decision = DecisionType.REJECT
                reasoning = "Historical success rate too low"
            elif context_risk_effectiveness < 0.4:
                decision = DecisionType.REJECT
                reasoning = "Risk management effectiveness too low"
            else:
                decision = DecisionType.APPROVE
                reasoning = "Plan approved based on risk assessment and historical performance"
            
            return {
                'decision': decision.value,
                'reasoning': reasoning,
                'budget_allocation': budget_allocation['budget_amount'],
                'approved_leverage': actual_leverage,
                'risk_limits': {
                    'max_position_size': self.portfolio_state['risk_limits']['max_single_position_risk'],
                    'max_risk_score': trading_plan.get('risk_score', 0.5)
                },
                'context_insights': {
                    'success_rate': context_success_rate,
                    'risk_effectiveness': context_risk_effectiveness,
                    'allocation_success': context.get('allocation_success', 0.5),
                    'leverage_accuracy': context.get('leverage_accuracy', 0.5)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error making decision: {e}")
            return {
                'decision': 'rejected',
                'reasoning': f'Decision error: {str(e)}',
                'budget_allocation': 0,
                'approved_leverage': 1
            }
    
    async def create_trading_decision_strand(self, trading_plan: Dict[str, Any], 
                                           decision_result: Dict[str, Any],
                                           risk_assessment: Dict[str, Any],
                                           budget_allocation: Dict[str, Any],
                                           actual_leverage: int) -> str:
        """
        Create trading decision strand in database
        
        Args:
            trading_plan: Original trading plan
            decision_result: Decision result
            risk_assessment: Risk assessment
            budget_allocation: Budget allocation
            actual_leverage: Approved leverage
            
        Returns:
            Strand ID of created trading decision
        """
        try:
            # Generate decision ID
            decision_id = f"dm_decision_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
            
            # Create trading decision data
            decision_data = {
                "id": decision_id,
                "module": "dm",
                "kind": "trading_decision",
                "symbol": trading_plan.get('symbol', 'UNKNOWN'),
                "timeframe": trading_plan.get('timeframe', '1h'),
                "tags": ['dm', 'trading_decision', decision_result['decision']],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "braid_level": 1,
                "lesson": "",
                "content": {
                    "decision_id": decision_id,
                    "plan_id": trading_plan.get('plan_id'),
                    "decision": decision_result['decision'],
                    "reasoning": decision_result['reasoning'],
                    "budget_allocation": decision_result['budget_allocation'],
                    "approved_leverage": decision_result['approved_leverage'],
                    "risk_limits": decision_result['risk_limits'],
                    "execution_instructions": {
                        "max_position_size": decision_result['risk_limits']['max_position_size'],
                        "leverage_limit": decision_result['approved_leverage'],
                        "risk_monitoring": "continuous"
                    },
                    "context_insights": decision_result.get('context_insights', {}),
                    "created_at": datetime.now(timezone.utc).isoformat()
                },
                "module_intelligence": {
                    "decision_type": decision_result['decision'],
                    "risk_assessment": risk_assessment,
                    "budget_allocation": budget_allocation,
                    "market_regime": self.current_market_regime.value,
                    "confidence": trading_plan.get('risk_score', 0.5)
                }
            }
            
            # Calculate module-specific resonance scores
            try:
                scores = await self.module_scoring.calculate_module_scores(decision_data, 'dm')
                decision_data['persistence_score'] = scores.get('persistence_score', 0.5)
                decision_data['novelty_score'] = scores.get('novelty_score', 0.5)
                decision_data['surprise_rating'] = scores.get('surprise_rating', 0.5)
                decision_data['resonance_score'] = scores.get('resonance_score', 0.5)
                
                # Store resonance scores in content for detailed tracking
                decision_data['content']['resonance_scores'] = {
                    'phi': scores.get('phi', 0.5),
                    'rho': scores.get('rho', 0.5),
                    'theta': scores.get('theta', 0.5),
                    'omega': scores.get('omega', 0.5)
                }
                
                self.logger.info(f"Calculated DM resonance scores: φ={scores.get('phi', 0.5):.3f}, ρ={scores.get('rho', 0.5):.3f}, θ={scores.get('theta', 0.5):.3f}, ω={scores.get('omega', 0.5):.3f}")
                
            except Exception as e:
                self.logger.warning(f"Failed to calculate resonance scores: {e}")
                # Set default scores
                decision_data['persistence_score'] = 0.5
                decision_data['novelty_score'] = 0.5
                decision_data['surprise_rating'] = 0.5
                decision_data['resonance_score'] = 0.5
            
            # Store in database
            result = self.supabase_manager.insert_strand(decision_data)
            
            if result:
                self.logger.info(f"Created trading decision strand: {decision_id}")
                return decision_id
            else:
                raise Exception("Failed to insert trading decision strand")
                
        except Exception as e:
            self.logger.error(f"Error creating trading decision strand: {e}")
            return f"error: {str(e)}"
    
    async def get_decision_context(self, context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get context for DM decisions from the learning system
        
        Args:
            context_data: Additional context data for filtering
            
        Returns:
            Context dictionary with relevant insights for DM decisions
        """
        try:
            return await self.learning_system.get_context_for_module('dm', context_data)
        except Exception as e:
            self.logger.error(f"Error getting decision context: {e}")
            return {}
    
    def calculate_current_portfolio_risk(self) -> float:
        """
        Calculate current portfolio risk from open positions
        
        Returns:
            Current portfolio risk as a percentage
        """
        try:
            # This is a simplified calculation
            # In a real implementation, this would calculate actual portfolio risk
            total_risk = 0.0
            for position in self.portfolio_state['open_positions']:
                position_risk = position.get('risk_score', 0.0) * position.get('leverage', 1)
                total_risk += position_risk
            
            return min(total_risk, 1.0)  # Cap at 100%
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio risk: {e}")
            return 0.0
    
    async def update_portfolio_state(self, new_state: Dict[str, Any]):
        """
        Update portfolio state with new information
        
        Args:
            new_state: Updated portfolio state
        """
        try:
            self.portfolio_state.update(new_state)
            self.logger.info("Portfolio state updated")
        except Exception as e:
            self.logger.error(f"Error updating portfolio state: {e}")
    
    async def update_market_regime(self, new_regime: MarketRegime):
        """
        Update current market regime
        
        Args:
            new_regime: New market regime
        """
        try:
            self.current_market_regime = new_regime
            self.logger.info(f"Market regime updated to: {new_regime.value}")
        except Exception as e:
            self.logger.error(f"Error updating market regime: {e}")
    
    async def get_decision_statistics(self) -> Dict[str, Any]:
        """
        Get decision statistics for monitoring
        
        Returns:
            Decision statistics
        """
        try:
            total_decisions = len(self.decision_history)
            approved_decisions = len([d for d in self.decision_history if d['decision'] == 'approved'])
            rejected_decisions = len([d for d in self.decision_history if d['decision'] == 'rejected'])
            
            return {
                'total_decisions': total_decisions,
                'approved_decisions': approved_decisions,
                'rejected_decisions': rejected_decisions,
                'approval_rate': approved_decisions / total_decisions if total_decisions > 0 else 0,
                'current_portfolio_risk': self.calculate_current_portfolio_risk(),
                'available_capital': self.portfolio_state['available_capital'],
                'market_regime': self.current_market_regime.value
            }
            
        except Exception as e:
            self.logger.error(f"Error getting decision statistics: {e}")
            return {}
