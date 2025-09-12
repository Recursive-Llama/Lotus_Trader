"""
Conditional Trading Planner (CTP) Module

A Trading Strategy Intelligence Engine that transforms Prediction Reviews into 
sophisticated conditional trading plans and learns from trade execution outcomes.

Key Functions:
1. Trading Plan Creation - Analyzes prediction reviews to create conditional trading plans
2. Learning from Trade Execution - Uses CIL learning system to improve strategies

Data Flow:
CIL → prediction_review → CTP → conditional_trading_plan → DM → Trader → trade_outcome → CTP Learning
"""

from .ctp_agent import ConditionalTradingPlannerAgent
from .prediction_review_analyzer import PredictionReviewAnalyzer
from .trading_plan_generator import TradingPlanGenerator
from .trade_outcome_processor import TradeOutcomeProcessor
from .ctp_learning_system import CTPLearningSystem

__all__ = [
    'ConditionalTradingPlannerAgent',
    'PredictionReviewAnalyzer', 
    'TradingPlanGenerator',
    'TradeOutcomeProcessor',
    'CTPLearningSystem'
]
