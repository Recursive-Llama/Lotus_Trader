"""
Decision Maker Module

Elegant, focused Decision Maker that evaluates conditional trading plans from CTP
and makes risk-based budget allocation decisions. Integrates with the centralized
learning system for continuous improvement.

Key Features:
- Risk assessment and budget allocation
- Leverage score to actual leverage conversion
- Portfolio risk management
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


class DecisionType(Enum):
    """Decision types for trading plans"""
    APPROVE = "approved"
    REJECT = "rejected"


class MarketRegime(Enum):
    """Market regime types"""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


class DecisionMaker:
    """
    Elegant Decision Maker for risk assessment and budget allocation
    
    Core Responsibilities:
    1. Evaluate conditional trading plans from CTP
    2. Assess portfolio risk and allocate budget
    3. Convert leverage scores to actual leverage
    4. Make approve/reject decisions with reasoning
    5. Learn from portfolio outcomes and past decisions
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(f"{__name__}.decision_maker")
        
        # Learning system integration
        self.module_scoring = ModuleSpecificScoring(supabase_manager)
        self.learning_system = CentralizedLearningSystem(supabase_manager, llm_client, None)
        
        # Prompt system integration
        self.prompt_manager = PromptManager()
        
        # Portfolio state
        self.portfolio_state = {
            'total_capital': 100000,
            'available_capital': 25000,
            'open_positions': [],
            'risk_limits': {
                'max_portfolio_risk': 0.15,
                'max_single_position_risk': 0.05,
                'max_leverage': 3
            }
        }
        
        # Market regime
        self.current_market_regime = MarketRegime.SIDEWAYS
        
        # Decision tracking
        self.decision_history = []
    
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
            
            # 1. Risk assessment
            risk_assessment = self._assess_risk(trading_plan)
            
            # 2. Leverage conversion
            actual_leverage = self._convert_leverage_score(trading_plan.get('leverage_score', 0.5))
            
            # 3. Budget allocation
            budget_allocation = self._calculate_budget(trading_plan, risk_assessment, actual_leverage)
            
            # 4. Make decision
            decision = self._make_decision(trading_plan, risk_assessment, budget_allocation, context)
            
            # 5. Create decision strand
            strand_id = await self._create_decision_strand(trading_plan, decision, risk_assessment, budget_allocation)
            
            # 6. Track decision
            self.decision_history.append({
                'plan_id': trading_plan.get('plan_id'),
                'decision': decision['decision'],
                'timestamp': datetime.now(timezone.utc),
                'strand_id': strand_id
            })
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error evaluating trading plan: {e}")
            return self._create_rejection_decision(f"Evaluation error: {str(e)}")
    
    def _assess_risk(self, trading_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Assess portfolio risk for trading plan"""
        try:
            plan_risk = trading_plan.get('risk_score', 0.5)
            leverage_score = trading_plan.get('leverage_score', 0.5)
            actual_leverage = self._convert_leverage_score(leverage_score)
            
            proposed_risk = plan_risk * actual_leverage
            current_risk = self._calculate_current_portfolio_risk()
            total_risk = current_risk + proposed_risk
            
            return {
                'proposed_risk': proposed_risk,
                'current_risk': current_risk,
                'total_risk': total_risk,
                'within_limits': (
                    proposed_risk <= self.portfolio_state['risk_limits']['max_single_position_risk'] and
                    total_risk <= self.portfolio_state['risk_limits']['max_portfolio_risk']
                )
            }
            
        except Exception as e:
            self.logger.error(f"Error assessing risk: {e}")
            return {'proposed_risk': 1.0, 'within_limits': False}
    
    def _convert_leverage_score(self, leverage_score: float) -> int:
        """Convert CTP leverage score (0.0-1.0) to actual leverage"""
        try:
            # Base leverage: 1x to 5x range
            base_leverage = 1 + int(leverage_score * 4)
            
            # Market regime adjustments
            adjustments = {
                MarketRegime.BULL_MARKET: 1.2,
                MarketRegime.BEAR_MARKET: 0.7,
                MarketRegime.SIDEWAYS: 1.0,
                MarketRegime.HIGH_VOLATILITY: 0.6,
                MarketRegime.LOW_VOLATILITY: 1.3
            }
            
            adjustment = adjustments.get(self.current_market_regime, 1.0)
            adjusted_leverage = int(base_leverage * adjustment)
            
            # Apply portfolio limits
            max_leverage = self.portfolio_state['risk_limits']['max_leverage']
            return min(adjusted_leverage, max_leverage)
            
        except Exception as e:
            self.logger.error(f"Error converting leverage score: {e}")
            return 1
    
    def _calculate_budget(self, trading_plan: Dict[str, Any], 
                         risk_assessment: Dict[str, Any], 
                         actual_leverage: int) -> Dict[str, Any]:
        """Calculate budget allocation for trading plan"""
        try:
            available_cash = self.portfolio_state['available_capital']
            max_position_value = available_cash * actual_leverage
            
            # Risk-based position sizing
            plan_risk = trading_plan.get('risk_score', 0.5)
            risk_per_dollar = plan_risk / max_position_value if max_position_value > 0 else 1.0
            max_safe_position = self.portfolio_state['risk_limits']['max_single_position_risk'] / risk_per_dollar
            
            allocated_budget = min(max_position_value, max_safe_position)
            
            # Minimum budget threshold
            min_budget = 1000
            if allocated_budget < min_budget:
                allocated_budget = 0
            
            return {
                'budget_amount': allocated_budget,
                'leverage': actual_leverage,
                'max_position_value': max_position_value,
                'approved': allocated_budget >= min_budget
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating budget: {e}")
            return {'budget_amount': 0, 'approved': False}
    
    def _make_decision(self, trading_plan: Dict[str, Any], 
                      risk_assessment: Dict[str, Any], 
                      budget_allocation: Dict[str, Any],
                      context: Dict[str, Any]) -> Dict[str, Any]:
        """Make final decision on trading plan"""
        try:
            # Use LLM for complex decision analysis if needed
            if self._should_use_llm_analysis(trading_plan, risk_assessment, context):
                return await self._llm_decision_analysis(trading_plan, risk_assessment, budget_allocation, context)
            
            # Standard decision criteria
            within_risk_limits = risk_assessment['within_limits']
            budget_approved = budget_allocation['approved']
            
            # Context-based adjustments
            context_success_rate = context.get('success_rate', 0.5)
            context_risk_effectiveness = context.get('risk_effectiveness', 0.5)
            
            # Decision logic
            if not within_risk_limits:
                return self._create_rejection_decision("Exceeds portfolio risk limits")
            elif not budget_approved:
                return self._create_rejection_decision("Budget allocation too small")
            elif context_success_rate < 0.3:
                return self._create_rejection_decision("Historical success rate too low")
            elif context_risk_effectiveness < 0.4:
                return self._create_rejection_decision("Risk management effectiveness too low")
            else:
                return self._create_approval_decision(trading_plan, budget_allocation, context)
                
        except Exception as e:
            self.logger.error(f"Error making decision: {e}")
            return self._create_rejection_decision(f"Decision error: {str(e)}")
    
    def _create_approval_decision(self, trading_plan: Dict[str, Any], 
                                budget_allocation: Dict[str, Any],
                                context: Dict[str, Any]) -> Dict[str, Any]:
        """Create approval decision"""
        return {
            'decision': DecisionType.APPROVE.value,
            'reasoning': 'Plan approved based on risk assessment and historical performance',
            'budget_allocation': budget_allocation['budget_amount'],
            'approved_leverage': budget_allocation['leverage'],
            'risk_limits': {
                'max_position_size': self.portfolio_state['risk_limits']['max_single_position_risk'],
                'max_risk_score': trading_plan.get('risk_score', 0.5)
            },
            'context_insights': {
                'success_rate': context.get('success_rate', 0.5),
                'risk_effectiveness': context.get('risk_effectiveness', 0.5),
                'allocation_success': context.get('allocation_success', 0.5),
                'leverage_accuracy': context.get('leverage_accuracy', 0.5)
            }
        }
    
    def _create_rejection_decision(self, reasoning: str) -> Dict[str, Any]:
        """Create rejection decision"""
        return {
            'decision': DecisionType.REJECT.value,
            'reasoning': reasoning,
            'budget_allocation': 0,
            'approved_leverage': 1,
            'risk_limits': {},
            'context_insights': {}
        }
    
    async def _create_decision_strand(self, trading_plan: Dict[str, Any], 
                                    decision: Dict[str, Any],
                                    risk_assessment: Dict[str, Any],
                                    budget_allocation: Dict[str, Any]) -> str:
        """Create trading decision strand in database"""
        try:
            decision_id = f"dm_decision_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
            
            decision_data = {
                "id": decision_id,
                "module": "dm",
                "kind": "trading_decision",
                "symbol": trading_plan.get('symbol', 'UNKNOWN'),
                "timeframe": trading_plan.get('timeframe', '1h'),
                "tags": ['dm', 'trading_decision', decision['decision']],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "braid_level": 1,
                "lesson": "",
                "content": {
                    "decision_id": decision_id,
                    "plan_id": trading_plan.get('plan_id'),
                    "decision": decision['decision'],
                    "reasoning": decision['reasoning'],
                    "budget_allocation": decision['budget_allocation'],
                    "approved_leverage": decision['approved_leverage'],
                    "risk_limits": decision['risk_limits'],
                    "execution_instructions": {
                        "max_position_size": decision['risk_limits'].get('max_position_size', 0.05),
                        "leverage_limit": decision['approved_leverage'],
                        "risk_monitoring": "continuous"
                    },
                    "context_insights": decision.get('context_insights', {}),
                    "created_at": datetime.now(timezone.utc).isoformat()
                },
                "module_intelligence": {
                    "decision_type": decision['decision'],
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
                
                decision_data['content']['resonance_scores'] = {
                    'phi': scores.get('phi', 0.5),
                    'rho': scores.get('rho', 0.5),
                    'theta': scores.get('theta', 0.5),
                    'omega': scores.get('omega', 0.5)
                }
                
                self.logger.info(f"Calculated DM resonance scores: φ={scores.get('phi', 0.5):.3f}, ρ={scores.get('rho', 0.5):.3f}, θ={scores.get('theta', 0.5):.3f}, ω={scores.get('omega', 0.5):.3f}")
                
            except Exception as e:
                self.logger.warning(f"Failed to calculate resonance scores: {e}")
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
        """Get context for DM decisions from the learning system"""
        try:
            return await self.learning_system.get_context_for_module('dm', context_data)
        except Exception as e:
            self.logger.error(f"Error getting decision context: {e}")
            return {}
    
    def _calculate_current_portfolio_risk(self) -> float:
        """Calculate current portfolio risk from open positions"""
        try:
            total_risk = 0.0
            for position in self.portfolio_state['open_positions']:
                position_risk = position.get('risk_score', 0.0) * position.get('leverage', 1)
                total_risk += position_risk
            return min(total_risk, 1.0)
        except Exception as e:
            self.logger.error(f"Error calculating portfolio risk: {e}")
            return 0.0
    
    async def update_portfolio_state(self, new_state: Dict[str, Any]):
        """Update portfolio state with new information"""
        try:
            self.portfolio_state.update(new_state)
            self.logger.info("Portfolio state updated")
        except Exception as e:
            self.logger.error(f"Error updating portfolio state: {e}")
    
    async def update_market_regime(self, new_regime: MarketRegime):
        """Update current market regime"""
        try:
            self.current_market_regime = new_regime
            self.logger.info(f"Market regime updated to: {new_regime.value}")
        except Exception as e:
            self.logger.error(f"Error updating market regime: {e}")
    
    def _should_use_llm_analysis(self, trading_plan: Dict[str, Any], 
                                risk_assessment: Dict[str, Any], 
                                context: Dict[str, Any]) -> bool:
        """Determine if LLM analysis should be used for complex decisions"""
        try:
            # Use LLM for high-value or complex decisions
            budget = trading_plan.get('budget_allocation', 0)
            risk_score = trading_plan.get('risk_score', 0.5)
            
            # High budget or high risk decisions
            if budget > 10000 or risk_score > 0.7:
                return True
            
            # Complex market conditions
            if self.current_market_regime in [MarketRegime.HIGH_VOLATILITY, MarketRegime.BEAR_MARKET]:
                return True
            
            # Low confidence context
            context_success_rate = context.get('success_rate', 0.5)
            if context_success_rate < 0.4:
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error determining LLM analysis need: {e}")
            return False
    
    async def _llm_decision_analysis(self, trading_plan: Dict[str, Any], 
                                   risk_assessment: Dict[str, Any], 
                                   budget_allocation: Dict[str, Any],
                                   context: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM for complex decision analysis"""
        try:
            # Get prompt template
            prompt_template = self.prompt_manager.get_prompt('decision_analysis')
            
            # Prepare context variables
            context_vars = {
                'plan_id': trading_plan.get('plan_id', 'unknown'),
                'symbol': trading_plan.get('symbol', 'UNKNOWN'),
                'side': trading_plan.get('side', 'buy'),
                'quantity': trading_plan.get('quantity', 0),
                'risk_score': trading_plan.get('risk_score', 0.5),
                'leverage_score': trading_plan.get('leverage_score', 0.5),
                'budget_allocation': budget_allocation.get('budget_amount', 0),
                'total_capital': self.portfolio_state['total_capital'],
                'available_capital': self.portfolio_state['available_capital'],
                'current_risk': risk_assessment.get('current_risk', 0.0),
                'max_single_risk': self.portfolio_state['risk_limits']['max_single_position_risk'],
                'max_portfolio_risk': self.portfolio_state['risk_limits']['max_portfolio_risk'],
                'max_leverage': self.portfolio_state['risk_limits']['max_leverage'],
                'market_regime': self.current_market_regime.value,
                'volatility_level': 'high' if self.current_market_regime == MarketRegime.HIGH_VOLATILITY else 'normal',
                'recent_performance': context.get('recent_performance', 'neutral'),
                'success_rate': context.get('success_rate', 0.5) * 100,
                'risk_effectiveness': context.get('risk_effectiveness', 0.5) * 100,
                'portfolio_impact': context.get('portfolio_impact', 0.5) * 100,
                'allocation_success': context.get('allocation_success', 0.5) * 100,
                'leverage_accuracy': context.get('leverage_accuracy', 0.5) * 100
            }
            
            # Generate LLM response
            response = await self.llm_client.generate_response(
                prompt_template=prompt_template,
                context=context_vars
            )
            
            # Parse LLM response to determine decision
            if 'approve' in response.lower() or 'approved' in response.lower():
                return self._create_approval_decision(trading_plan, budget_allocation, context)
            else:
                # Extract rejection reason from LLM response
                reason = self._extract_rejection_reason(response)
                return self._create_rejection_decision(reason)
                
        except Exception as e:
            self.logger.error(f"Error in LLM decision analysis: {e}")
            # Fallback to standard decision logic
            return self._create_rejection_decision(f"LLM analysis error: {str(e)}")
    
    def _extract_rejection_reason(self, llm_response: str) -> str:
        """Extract rejection reason from LLM response"""
        try:
            # Simple extraction - look for key phrases
            if 'risk' in llm_response.lower():
                return "Risk assessment concerns identified"
            elif 'budget' in llm_response.lower():
                return "Budget allocation issues identified"
            elif 'leverage' in llm_response.lower():
                return "Leverage concerns identified"
            else:
                return "LLM analysis identified concerns"
        except Exception as e:
            self.logger.error(f"Error extracting rejection reason: {e}")
            return "Analysis identified concerns"
    
    async def get_decision_statistics(self) -> Dict[str, Any]:
        """Get decision statistics for monitoring"""
        try:
            total_decisions = len(self.decision_history)
            approved_decisions = len([d for d in self.decision_history if d['decision'] == 'approved'])
            
            return {
                'total_decisions': total_decisions,
                'approved_decisions': approved_decisions,
                'rejected_decisions': total_decisions - approved_decisions,
                'approval_rate': approved_decisions / total_decisions if total_decisions > 0 else 0,
                'current_portfolio_risk': self._calculate_current_portfolio_risk(),
                'available_capital': self.portfolio_state['available_capital'],
                'market_regime': self.current_market_regime.value
            }
            
        except Exception as e:
            self.logger.error(f"Error getting decision statistics: {e}")
            return {}
