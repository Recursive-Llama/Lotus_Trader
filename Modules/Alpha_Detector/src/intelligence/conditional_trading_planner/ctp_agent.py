"""
Conditional Trading Planner Agent

Main orchestrator for the CTP module that coordinates:
1. Prediction Review Analysis
2. Trading Plan Generation  
3. Trade Outcome Learning
4. Learning System Integration
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from .prediction_review_analyzer import PredictionReviewAnalyzer
from .trading_plan_generator import TradingPlanGenerator
from .trade_outcome_processor import TradeOutcomeProcessor
from .ctp_learning_system import CTPLearningSystem


class ConditionalTradingPlannerAgent:
    """
    Main CTP agent that orchestrates trading plan creation and learning from trade outcomes.
    
    Dual Functions:
    1. Trading Plan Creation: prediction_review → conditional_trading_plan
    2. Learning from Trade Execution: trade_outcome → trade_outcome braids
    """
    
    def __init__(self, supabase_manager, llm_client):
        """
        Initialize CTP agent with required dependencies.
        
        Args:
            supabase_manager: Database manager for strand operations
            llm_client: LLM client for analysis and plan generation
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(f"{__name__}.ctp_agent")
        
        # Initialize CTP components
        self.prediction_analyzer = PredictionReviewAnalyzer(supabase_manager, llm_client)
        self.plan_generator = TradingPlanGenerator(supabase_manager, llm_client)
        self.outcome_processor = TradeOutcomeProcessor(supabase_manager, llm_client)
        self.learning_system = CTPLearningSystem(supabase_manager, llm_client)
        
        self.logger.info("CTP Agent initialized successfully")
    
    async def process_prediction_review(self, prediction_review_id: str) -> Optional[str]:
        """
        Process a new prediction review and create conditional trading plan.
        
        Args:
            prediction_review_id: ID of the prediction review strand
            
        Returns:
            ID of created conditional trading plan, or None if failed
        """
        try:
            self.logger.info(f"Processing prediction review: {prediction_review_id}")
            
            # Step 1: Analyze prediction review
            analysis = await self.prediction_analyzer.analyze_prediction_review(prediction_review_id)
            if not analysis:
                self.logger.error(f"Failed to analyze prediction review: {prediction_review_id}")
                return None
            
            # Step 2: Generate conditional trading plan
            trading_plan_id = await self.plan_generator.create_conditional_trading_plan(analysis)
            if not trading_plan_id:
                self.logger.error(f"Failed to create trading plan for: {prediction_review_id}")
                return None
            
            self.logger.info(f"Created trading plan: {trading_plan_id}")
            return trading_plan_id
            
        except Exception as e:
            self.logger.error(f"Error processing prediction review {prediction_review_id}: {e}")
            return None
    
    async def process_trade_outcome(self, trade_outcome_id: str) -> bool:
        """
        Process a trade outcome for learning and create trade outcome braids.
        
        Args:
            trade_outcome_id: ID of the trade outcome strand
            
        Returns:
            True if processing successful, False otherwise
        """
        try:
            self.logger.info(f"Processing trade outcome: {trade_outcome_id}")
            
            # Step 1: Process trade outcome
            outcome_data = await self.outcome_processor.process_trade_outcome(trade_outcome_id)
            if not outcome_data:
                self.logger.error(f"Failed to process trade outcome: {trade_outcome_id}")
                return False
            
            # Step 2: Run learning system on trade outcomes
            learning_result = await self.learning_system.process_trade_outcome_learning()
            if not learning_result:
                self.logger.warning("Learning system processing completed with warnings")
            
            self.logger.info(f"Successfully processed trade outcome: {trade_outcome_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing trade outcome {trade_outcome_id}: {e}")
            return False
    
    async def run_learning_cycle(self) -> Dict[str, Any]:
        """
        Run a complete learning cycle on all available trade outcomes.
        
        Returns:
            Dictionary with learning cycle results
        """
        try:
            self.logger.info("Starting CTP learning cycle")
            
            # Process all trade outcomes for learning
            result = await self.learning_system.process_all_trade_outcomes()
            
            self.logger.info(f"CTP learning cycle completed: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in CTP learning cycle: {e}")
            return {"error": str(e), "success": False}
    
    async def get_trading_plan_performance(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Get performance metrics for a specific trading plan.
        
        Args:
            plan_id: ID of the trading plan
            
        Returns:
            Performance metrics dictionary, or None if not found
        """
        try:
            return await self.plan_generator.get_plan_performance(plan_id)
        except Exception as e:
            self.logger.error(f"Error getting plan performance for {plan_id}: {e}")
            return None
    
    async def get_learning_insights(self, cluster_type: str = None, cluster_key: str = None) -> List[Dict[str, Any]]:
        """
        Get learning insights from trade outcome analysis.
        
        Args:
            cluster_type: Optional cluster type filter
            cluster_key: Optional cluster key filter
            
        Returns:
            List of learning insights
        """
        try:
            return await self.learning_system.get_learning_insights(cluster_type, cluster_key)
        except Exception as e:
            self.logger.error(f"Error getting learning insights: {e}")
            return []
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get current CTP system status and statistics.
        
        Returns:
            System status dictionary
        """
        try:
            return {
                "status": "active",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "components": {
                    "prediction_analyzer": "ready",
                    "plan_generator": "ready", 
                    "outcome_processor": "ready",
                    "learning_system": "ready"
                },
                "statistics": await self._get_system_statistics()
            }
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _get_system_statistics(self) -> Dict[str, Any]:
        """Get system statistics for status reporting."""
        try:
            # Get counts of different strand types
            prediction_reviews = self.supabase_manager.client.table('ad_strands').select('id').eq('kind', 'prediction_review').execute()
            trading_plans = self.supabase_manager.client.table('ad_strands').select('id').eq('kind', 'conditional_trading_plan').execute()
            trade_outcomes = self.supabase_manager.client.table('ad_strands').select('id').eq('kind', 'trade_outcome').execute()
            
            return {
                "prediction_reviews": len(prediction_reviews.data),
                "trading_plans": len(trading_plans.data),
                "trade_outcomes": len(trade_outcomes.data),
                "learning_braids": len([s for s in trade_outcomes.data if s.get('braid_level', 1) > 1])
            }
        except Exception as e:
            self.logger.warning(f"Error getting system statistics: {e}")
            return {"error": "Failed to get statistics"}
