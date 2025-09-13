"""
Decision Maker Lowcap (DML)

Portfolio-aware decision making for social lowcap trades.
Learns from curator performance and TDL execution outcomes.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import yaml
import os

logger = logging.getLogger(__name__)


class DecisionMakerLowcap:
    """
    Decision Maker Lowcap - Portfolio-aware decision making with learning
    
    This module:
    - Reads social_lowcap strands from Social Ingest
    - Gets curator context from learning system
    - Makes allocation decisions based on curator performance
    - Tracks portfolio capacity and risk limits
    - Creates decision_lowcap strands for TDL
    - Learns from TDL execution outcomes
    """
    
    def __init__(self, supabase_manager, learning_system, context_engine, llm_client, config_path: str = None):
        """
        Initialize Decision Maker Lowcap
        
        Args:
            supabase_manager: Database manager for strands and positions
            learning_system: Centralized learning system
            context_engine: Context injection engine
            llm_client: LLM client for decision making
            config_path: Path to DML configuration file
        """
        self.supabase_manager = supabase_manager
        self.learning_system = learning_system
        self.context_engine = context_engine
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        if config_path and os.path.exists(config_path):
            self.config = self._load_config(config_path)
        else:
            self.config = self._get_default_config()
        
        self.book_id = self.config['dm_lowcap']['book']
        self.allocation_bands = self.config['dm_lowcap']['allocation_bands']
        self.risk_limits = self.config['dm_lowcap']['risk_limits']
        
        self.logger.info(f"Decision Maker Lowcap initialized for book: {self.book_id}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load DML configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load DML config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default DML configuration"""
        return {
            'dm_lowcap': {
                'book': 'social',
                'allocation_bands': {
                    'excellent_curator': [3.0, 5.0],  # 3-5% of book
                    'good_curator': [1.0, 3.0],       # 1-3% of book
                    'new_curator': [0.5, 1.0]         # 0.5-1% of book
                },
                'risk_limits': {
                    'max_concurrent_positions': 8,
                    'max_daily_allocation_pct': 20,
                    'min_curator_score': 0.6,
                    'min_liquidity_usd': 5000
                }
            }
        }
    
    def make_decision(self, social_signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Make allocation decision based on social signal and curator performance
        
        Args:
            social_signal: social_lowcap strand from Social Ingest
            
        Returns:
            Created decision strand or None if rejected
        """
        try:
            curator_id = social_signal['content']['curator_id']
            token_data = social_signal['content']['token']
            venue_data = social_signal['content']['venue']
            
            # Get curator context from learning system
            curator_context = self.context_engine.get_context_for_module(
                'decision_maker_lowcap',
                {'curator_id': curator_id}
            )
            
            # Check portfolio capacity
            portfolio_capacity = self._get_portfolio_capacity()
            if portfolio_capacity <= 0:
                self.logger.info(f"No portfolio capacity available for {curator_id}")
                return self._create_rejection_decision(social_signal, "No portfolio capacity")
            
            # Check risk limits
            if not self._check_risk_limits():
                self.logger.info(f"Risk limits exceeded for {curator_id}")
                return self._create_rejection_decision(social_signal, "Risk limits exceeded")
            
            # Check venue requirements
            if venue_data.get('liq_usd', 0) < self.risk_limits['min_liquidity_usd']:
                self.logger.info(f"Insufficient liquidity for {curator_id}: {venue_data.get('liq_usd', 0)}")
                return self._create_rejection_decision(social_signal, "Insufficient liquidity")
            
            # Calculate curator score and allocation
            curator_score = curator_context.get('curator_score', 0.5)
            allocation_pct = self._calculate_allocation(curator_score, curator_context)
            
            if allocation_pct <= 0:
                self.logger.info(f"Allocation too low for {curator_id}: {allocation_pct}")
                return self._create_rejection_decision(social_signal, "Allocation too low")
            
            # Create decision strand
            decision = {
                "module": "decision_maker_lowcap",
                "kind": "decision_lowcap",
                "content": {
                    "source_kind": "social_lowcap",
                    "source_strand_id": social_signal['id'],
                    "curator_id": curator_id,
                    "token": token_data,
                    "venue": venue_data,
                    "action": "approve",
                    "allocation_pct": allocation_pct,
                    "allocation_usd": allocation_pct * self._get_book_nav(),
                    "curator_confidence": curator_score,
                    "reasoning": f"Curator score: {curator_score:.2f}, Allocation: {allocation_pct:.1f}%",
                    "portfolio_context": {
                        "available_capacity_pct": portfolio_capacity,
                        "planned_positions": self._get_planned_positions_count(),
                        "current_exposure_pct": self._get_current_exposure_pct(),
                        "book_nav": self._get_book_nav()
                    }
                },
                "tags": ["decision", "social_lowcap", "approved"],
                "status": "active"
            }
            
            # Create strand in database
            created_decision = self.supabase_manager.create_strand(decision)
            
            self.logger.info(f"Created decision_lowcap strand: {curator_id} -> {allocation_pct:.1f}%")
            return created_decision
            
        except Exception as e:
            self.logger.error(f"Failed to make decision for {social_signal.get('content', {}).get('curator_id', 'unknown')}: {e}")
            return None
    
    def _get_curator_context(self, curator_id: str) -> Dict[str, Any]:
        """Get curator context from learning system"""
        try:
            return self.context_engine.get_context_for_module(
                'decision_maker_lowcap',
                {'curator_id': curator_id}
            )
        except Exception as e:
            self.logger.error(f"Failed to get curator context for {curator_id}: {e}")
            return {}
    
    def _get_portfolio_capacity(self) -> float:
        """Get available portfolio capacity as percentage"""
        try:
            # Get current exposure
            current_exposure = self._get_current_exposure_pct()
            
            # Get daily limit
            daily_limit = self.risk_limits['max_daily_allocation_pct']
            
            # Calculate available capacity
            available_capacity = daily_limit - current_exposure
            
            return max(0, available_capacity)
        except Exception as e:
            self.logger.error(f"Failed to get portfolio capacity: {e}")
            return 0
    
    def _get_current_exposure_pct(self) -> float:
        """Get current exposure as percentage of book NAV"""
        try:
            # Get active positions for this book
            active_positions = self.supabase_manager.get_active_positions(self.book_id)
            
            total_exposure = sum(pos.get('current_exposure_usd', 0) for pos in active_positions)
            book_nav = self._get_book_nav()
            
            return (total_exposure / book_nav * 100) if book_nav > 0 else 0
        except Exception as e:
            self.logger.error(f"Failed to get current exposure: {e}")
            return 0
    
    def _get_planned_positions_count(self) -> int:
        """Get count of planned positions (pending approvals)"""
        try:
            # Get pending decisions for this book
            pending_decisions = self.supabase_manager.get_pending_decisions(self.book_id)
            return len(pending_decisions)
        except Exception as e:
            self.logger.error(f"Failed to get planned positions count: {e}")
            return 0
    
    def _get_book_nav(self) -> float:
        """Get book net asset value (mock for now)"""
        # This would integrate with actual portfolio API
        return 100000.0  # Mock $100k book NAV
    
    def _check_risk_limits(self) -> bool:
        """Check if risk limits are satisfied"""
        try:
            # Check concurrent positions limit
            active_count = len(self.supabase_manager.get_active_positions(self.book_id))
            if active_count >= self.risk_limits['max_concurrent_positions']:
                return False
            
            # Check daily allocation limit
            current_exposure = self._get_current_exposure_pct()
            if current_exposure >= self.risk_limits['max_daily_allocation_pct']:
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to check risk limits: {e}")
            return False
    
    def _calculate_allocation(self, curator_score: float, curator_context: Dict[str, Any]) -> float:
        """
        Calculate allocation percentage based on curator performance
        
        Args:
            curator_score: Curator performance score (0-1)
            curator_context: Additional curator context
            
        Returns:
            Allocation percentage (0-5)
        """
        try:
            # Use LLM for intelligent allocation decision if available
            if hasattr(self.llm_client, 'get_prompt'):
                return asyncio.run(self._llm_allocation_decision(curator_score, curator_context))
            
            # Fallback to rule-based allocation
            return self._rule_based_allocation(curator_score, curator_context)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate allocation: {e}")
            return 0
    
    async def _llm_allocation_decision(self, curator_score: float, curator_context: Dict[str, Any]) -> float:
        """Use LLM for intelligent allocation decision"""
        try:
            # Get prompt template
            prompt_data = self.llm_client.get_prompt('decision_maker_lowcap', 'allocation_decision')
            
            # Format prompt with context
            prompt = prompt_data['prompt'].format(
                token_ticker=curator_context.get('token_ticker', 'UNKNOWN'),
                token_chain=curator_context.get('token_chain', 'solana'),
                curator_handle=curator_context.get('curator_handle', 'UNKNOWN'),
                curator_weight=curator_context.get('curator_weight', 1.0),
                curator_score=curator_score,
                venue_dex=curator_context.get('venue_dex', 'Unknown'),
                liquidity_usd=curator_context.get('liquidity_usd', 0),
                volume_24h=curator_context.get('volume_24h', 0),
                book_nav=self._get_book_nav(),
                current_exposure_pct=self._get_current_exposure_pct(),
                available_capacity_pct=self._get_portfolio_capacity(),
                active_positions=len(self.supabase_manager.get_active_positions(self.book_id)),
                planned_positions=self._get_planned_positions_count(),
                max_concurrent=self.risk_limits['max_concurrent_positions'],
                max_daily_pct=self.risk_limits['max_daily_allocation_pct'],
                min_curator_score=self.risk_limits['min_curator_score'],
                min_liquidity=self.risk_limits['min_liquidity_usd']
            )
            
            # Generate response
            response = await self.llm_client.generate_async(prompt, system_message=prompt_data.get('system_message', ''))
            
            # Parse response
            decision = json.loads(response)
            return decision.get('allocation_pct', 0.0)
            
        except Exception as e:
            self.logger.error(f"Error in LLM allocation decision: {e}")
            return self._rule_based_allocation(curator_score, curator_context)
    
    def _rule_based_allocation(self, curator_score: float, curator_context: Dict[str, Any]) -> float:
        """Fallback rule-based allocation calculation"""
        try:
            # Determine curator category
            if curator_score >= 0.8:
                category = 'excellent_curator'
            elif curator_score >= 0.6:
                category = 'good_curator'
            else:
                category = 'new_curator'
            
            # Get allocation band for category
            allocation_band = self.allocation_bands.get(category, [0.5, 1.0])
            min_allocation, max_allocation = allocation_band
            
            # Calculate allocation based on curator score
            # Higher scores get higher allocations within the band
            score_factor = (curator_score - 0.5) / 0.5  # Normalize to 0-1
            allocation = min_allocation + (max_allocation - min_allocation) * score_factor
            
            # Apply portfolio capacity constraint
            portfolio_capacity = self._get_portfolio_capacity()
            allocation = min(allocation, portfolio_capacity)
            
            return max(0, allocation)
        except Exception as e:
            self.logger.error(f"Failed to calculate rule-based allocation: {e}")
            return 0
    
    def _create_rejection_decision(self, social_signal: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Create a rejection decision strand"""
        return {
            "module": "decision_maker_lowcap",
            "kind": "decision_lowcap",
            "content": {
                "source_kind": "social_lowcap",
                "source_strand_id": social_signal['id'],
                "curator_id": social_signal['content']['curator_id'],
                "token": social_signal['content']['token'],
                "venue": social_signal['content']['venue'],
                "action": "reject",
                "allocation_pct": 0,
                "allocation_usd": 0,
                "curator_confidence": 0,
                "reasoning": reason,
                "portfolio_context": {
                    "available_capacity_pct": self._get_portfolio_capacity(),
                    "planned_positions": self._get_planned_positions_count(),
                    "current_exposure_pct": self._get_current_exposure_pct(),
                    "book_nav": self._get_book_nav()
                }
            },
            "tags": ["decision", "social_lowcap", "rejected"],
            "status": "active"
        }
    
    def process_learning_feedback(self, execution_outcome: Dict[str, Any]):
        """
        Process learning feedback from TDL execution outcomes
        
        Args:
            execution_outcome: Execution outcome data for learning
        """
        try:
            # This would integrate with the learning system
            # to update curator performance scores and allocation accuracy
            self.logger.info(f"Processing learning feedback for execution: {execution_outcome.get('id', 'unknown')}")
            
            # The learning system will automatically process this through strands
            # and update curator performance scores via context injection
            
        except Exception as e:
            self.logger.error(f"Failed to process learning feedback: {e}")
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary for monitoring"""
        try:
            return {
                "book_id": self.book_id,
                "book_nav": self._get_book_nav(),
                "current_exposure_pct": self._get_current_exposure_pct(),
                "available_capacity_pct": self._get_portfolio_capacity(),
                "active_positions": len(self.supabase_manager.get_active_positions(self.book_id)),
                "planned_positions": self._get_planned_positions_count(),
                "risk_limits": self.risk_limits
            }
        except Exception as e:
            self.logger.error(f"Failed to get portfolio summary: {e}")
            return {}
