"""
Decision Maker Lowcap - Simplified Version

Simple 4-step decision process:
1. Do we already have this token?
2. How well has this trader performed?
3. How much capital do we have to buy?
4. Decision: allocate 2-6% (4% default)
"""

import logging
import uuid
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from config.allocation_manager import AllocationManager

logger = logging.getLogger(__name__)


class DecisionMakerLowcapSimple:
    """
    Simplified Decision Maker Lowcap
    
    Simple 4-step decision process for social lowcap trading.
    """
    
    def __init__(self, supabase_manager, config: Dict[str, Any] = None, learning_system=None):
        """
        Initialize Simplified Decision Maker Lowcap
        
        Args:
            supabase_manager: Database manager for positions and curators
            config: Configuration dictionary
            learning_system: Reference to Universal Learning System for callbacks
        """
        self.supabase_manager = supabase_manager
        self.learning_system = learning_system
        self.logger = logging.getLogger(__name__)
        
        # Simple configuration
        self.config = config or self._get_default_config()
        self.allocation_manager = AllocationManager(self.config)
        self.book_id = self.config.get('book_id', 'social')
        
        # Get trading config section
        trading_config = self.config.get('trading', {})
        
        # No need for dollar amounts - we work with percentages only
        self.min_curator_score = trading_config.get('min_curator_score', 0.6)
        self.max_exposure_pct = trading_config.get('max_exposure_pct', 100.0)  # 100% max exposure for lowcap portfolio
        self.max_positions = trading_config.get('max_positions', 69)  # Maximum number of active positions
        
        # Note: Token ignore list moved to Social Ingest for early filtering
        
        # Minimum volume requirements by chain
        self.min_volume_requirements = self.config.get('min_volume_requirements', {
            'solana': 100000,    # $100k on Solana
            'ethereum': 25000,   # $25k on Ethereum
            'base': 25000,       # $25k on Base
        })
        
        self.logger.info(f"Simplified Decision Maker Lowcap initialized for book: {self.book_id}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'book_id': 'social',
            # No dollar amounts needed - percentage-based only
            'min_curator_score': 0.6,  # Minimum curator score to approve
            'max_exposure_pct': 100.0,  # 100% max exposure for lowcap portfolio
            'max_positions': 69,  # Maximum number of active positions
            # Note: Allocation percentages are now handled by AllocationManager
        }
    
    async def make_decision(self, social_signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Make simple allocation decision based on 4-step process with a visible checklist
        """
        try:
            curator_id = social_signal['signal_pack']['curator']['id']
            token_data = social_signal['signal_pack']['token']
            venue_data = social_signal['signal_pack']['venue']
            
            token_ticker = token_data.get('ticker', 'UNKNOWN').upper()
            chain = token_data.get('chain', '').lower()
            volume_24h = venue_data.get('vol24h_usd', 0)
            min_volume = self.min_volume_requirements.get(chain, 0)
            supported_chains = ['solana', 'ethereum', 'base', 'bsc']

            self.logger.info(f"Making decision for {curator_id} -> {token_ticker}")

            # Evaluate all criteria
            criteria = []

            # Note: Token ignore filtering now handled in Social Ingest (early filtering)

            # 1) Supported chain
            chain_pass = chain in supported_chains
            criteria.append({
                'name': 'supported_chain',
                'passed': chain_pass,
                'detail': f"Chain {chain} not supported; allowed: {supported_chains}" if not chain_pass else f"Chain {chain} supported"
            })

            # Volume check removed - handled in social ingest

            # 2) Not already holding token
            already_holding = await self._already_has_token(token_data.get('contract', ''), token_data.get('chain', ''))
            hold_pass = not already_holding
            criteria.append({
                'name': 'not_already_holding',
                'passed': hold_pass,
                'detail': f"Already holding {token_ticker}" if not hold_pass else "No existing position"
            })

            # 3) Curator score >= min
            curator_score = await self._get_curator_score(curator_id)
            score_pass = curator_score >= self.min_curator_score
            criteria.append({
                'name': 'curator_score',
                'passed': score_pass,
                'detail': f"Curator {curator_score:.2f} < {self.min_curator_score}" if not score_pass else f"Curator {curator_score:.2f} >= {self.min_curator_score}"
            })

            # 4) Intent analysis indicates buy signal
            intent_analysis = social_signal.get('signal_pack', {}).get('intent_analysis')
            buy_intent_types = {
                'adding_to_position',
                'research_positive', 
                'new_discovery',
                'comparison_highlighted',
                'other_positive'
            }
            
            intent_pass = False
            intent_type = 'unknown'
            if intent_analysis:
                intent_data = intent_analysis.get('intent_analysis', {})
                intent_type = intent_data.get('intent_type', 'unknown')
                intent_pass = intent_type in buy_intent_types
            
            criteria.append({
                'name': 'intent_analysis_buy',
                'passed': intent_pass,
                'detail': f"Intent type '{intent_type}' not in buy signals" if not intent_pass else f"Intent type '{intent_type}' indicates buy signal"
            })

            # 5) Portfolio capacity available
            capital_pass = await self._has_capital_for_allocation()
            criteria.append({
                'name': 'portfolio_capacity',
                'passed': capital_pass,
                'detail': "Insufficient capital - portfolio at max exposure" if not capital_pass else "Capacity available"
            })

            failed = [c for c in criteria if not c['passed']]

            # Checklist summary at INFO; full details at DEBUG
            passed_count = sum(1 for c in criteria if c['passed'])
            failed = [c for c in criteria if not c['passed']]
            if failed:
                failed_names = ", ".join(c['name'] for c in failed)
                print(f"decision | Checklist: {passed_count}/{len(criteria)} passed (failed: {failed_names})")
                # Detailed reasons at DEBUG
                for c in criteria:
                    self.logger.debug(f"check {c['name']}: {'pass' if c['passed'] else 'fail'} - {c['detail']}")
            else:
                print(f"decision | Checklist: {passed_count}/{len(criteria)} passed (solana, not holding, curator {curator_score:.2f}, intent {intent_type}, capacity)")
                for c in criteria:
                    self.logger.debug(f"check {c['name']}: pass - {c['detail']}")

            if failed:
                reason_text = "; ".join(c['detail'] for c in failed)
                print(f"decision | REJECTED {token_ticker} ({chain}) reasons: {reason_text}")
                return await self._create_rejection_decision(social_signal, reason_text)

            # All checks passed → approve
            # Extract intent analysis from signal pack
            intent_analysis = social_signal.get('signal_pack', {}).get('intent_analysis')
            allocation_pct = self._calculate_allocation(curator_score, intent_analysis, token_data)
            decision = await self._create_approval_decision(social_signal, allocation_pct, curator_score, intent_analysis)
            
            # Enhanced logging with intent information
            if intent_analysis:
                intent_type = intent_analysis.get('intent_analysis', {}).get('intent_type', 'unknown')
                multiplier = intent_analysis.get('intent_analysis', {}).get('allocation_multiplier', 1.0)
                print(f"decision | APPROVED {token_ticker} alloc {allocation_pct}% (curator {curator_score:.2f}, intent: {intent_type}, {multiplier}x)")
            else:
                print(f"decision | APPROVED {token_ticker} alloc {allocation_pct}% (curator {curator_score:.2f})")
            return decision
            
        except Exception as e:
            print(f"❌ Decision Maker Error: {e}")
            self.logger.error(f"Failed to make decision: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _already_has_token(self, token_contract: str, token_chain: str) -> bool:
        """
        Step 1: Check if we already have this token
        
        Args:
            token_contract: Token contract address
            token_chain: Token chain (solana, ethereum, etc.)
            
        Returns:
            True if we already have this token
        """
        try:
            # Query active positions for this token using execute_query
            query = """
                SELECT * FROM lowcap_positions 
                WHERE token_contract = %s AND token_chain = %s AND status = 'active'
            """
            result = await self.supabase_manager.execute_query(query, [token_contract, token_chain])
            
            has_position = len(result) > 0
            
            if has_position:
                self.logger.info(f"Already holding {token_contract} on {token_chain}")
            
            return has_position
            
        except Exception as e:
            self.logger.error(f"Error checking existing token: {e}")
            return False  # Assume we don't have it if we can't check
    
    async def _get_curator_score(self, curator_id: str) -> float:
        """
        Step 2: Get curator performance score
        
        Args:
            curator_id: Curator identifier
            
        Returns:
            Curator performance score (0.0 to 1.0)
        """
        try:
            # Get curator performance from database using execute_query
            query = """
                SELECT final_weight, win_rate, total_signals 
                FROM curators 
                WHERE curator_id = %s
            """
            result = await self.supabase_manager.execute_query(query, [curator_id])
            
            if not result:
                self.logger.warning(f"Curator {curator_id} not found in database")
                return 0.5  # Default score for unknown curators
            
            curator = result[0]
            
            # Handle nested result structure from execute_query
            if 'result' in curator:
                curator = curator['result']
            
            # Use final_weight as primary score, fallback to win_rate
            score = curator.get('final_weight', curator.get('win_rate', 0.5))
            
            # Ensure score is between 0 and 1
            score = max(0.0, min(1.0, score))
            
            self.logger.info(f"Curator {curator_id} score: {score:.2f}")
            return score
            
        except Exception as e:
            self.logger.error(f"Error getting curator score for {curator_id}: {e}")
            return 0.5  # Default score on error
    
    async def _has_capital_for_allocation(self) -> bool:
        """
        Step 3: Check if we have capital for new allocation
        
        Returns:
            True if we have capital available
        """
        try:
            # Get current portfolio exposure
            # Use execute_query instead of rpc
            query = "SELECT * FROM lowcap_positions WHERE book_id = %s AND status = 'active'"
            result = await self.supabase_manager.execute_query(query, [self.book_id])
            
            if not result:
                self.logger.warning("Could not get portfolio summary")
                return True  # Assume we have capital if we can't check
            
            # For now, just check if we have fewer than max_positions
            current_positions = len(result)
            has_capital = current_positions < self.max_positions
            
            if not has_capital:
                self.logger.info(f"Portfolio at max positions: {current_positions} >= {self.max_positions}")
            
            return has_capital
            
        except Exception as e:
            self.logger.error(f"Error checking portfolio capacity: {e}")
            return True  # Assume we have capital if we can't check
    
    def _calculate_allocation(self, curator_score: float, intent_analysis: Dict[str, Any] = None, token_data: Dict[str, Any] = None) -> float:
        """
        Step 4: Calculate allocation percentage (2-6%) with intent multiplier and market cap multiplier
        
        Args:
            curator_score: Curator performance score (0.0 to 1.0)
            intent_analysis: Intent analysis from Stage 2 (optional)
            token_data: Token data containing market cap (optional)
            
        Returns:
            Allocation percentage (6.0 to 20.0)
        """
        try:
            # Use centralized allocation manager
            base_allocation = self.allocation_manager.get_social_curator_allocation(
                curator_score, test_mode=False
            )
            
            # Apply intent multiplier if available
            allocation = base_allocation
            if intent_analysis:
                intent_data = intent_analysis.get('intent_analysis', {})
                multiplier = intent_data.get('allocation_multiplier', 1.0)
                intent_type = intent_data.get('intent_type', 'unknown')
                
                # Apply multiplier
                allocation = base_allocation * multiplier
                
                # Log intent-based adjustment
                self.logger.info(f"Intent adjustment: {intent_type} -> {multiplier}x multiplier")
                self.logger.info(f"Allocation: {base_allocation}% -> {allocation}% (curator score: {curator_score:.2f})")
            
            # Apply market cap multiplier if available
            if token_data:
                market_cap = token_data.get('market_cap')
                if market_cap and market_cap > 0:
                    market_cap_multiplier = self._get_market_cap_multiplier(market_cap)
                    allocation = allocation * market_cap_multiplier
                    self.logger.info(f"Market cap multiplier: ${market_cap:,.0f} -> {market_cap_multiplier}x")
                    self.logger.info(f"Allocation after market cap: {allocation:.2f}%")
                
                # Apply age multiplier if available
                age_days = token_data.get('age_days')
                if age_days is not None:
                    age_multiplier = self._get_age_multiplier(age_days)
                    allocation = allocation * age_multiplier
                    self.logger.info(f"Age multiplier: {age_days} days -> {age_multiplier}x")
                    self.logger.info(f"Final allocation: {allocation:.2f}% (curator score: {curator_score:.2f})")
            
            # AllocationManager already handles proper bounds and logic
            return allocation
            
        except Exception as e:
            self.logger.error(f"Error calculating allocation: {e}")
            # Fallback to acceptable allocation if error occurs
            return self.allocation_manager.get_social_curator_allocation(0.5)  # 0.5 score = acceptable
    
    def _get_market_cap_multiplier(self, market_cap: float) -> float:
        """Get allocation multiplier based on market cap"""
        if market_cap < 1_000_000:  # < $1M
            return 0.5
        elif market_cap < 10_000_000:  # $1M - $10M
            return 1.0
        elif market_cap < 100_000_000:  # $10M - $100M
            return 1.33
        else:  # $100M+
            return 1.5
    
    def _get_age_multiplier(self, age_days: int) -> float:
        """Get allocation multiplier based on token age"""
        if age_days < 1:  # < 24 hours
            return 0.5
        elif age_days < 2:  # < 48 hours  
            return 0.6
        elif age_days < 3:  # < 72 hours
            return 0.9
        else:  # 3+ days
            return 1.0
    
    async def _create_approval_decision(self, social_signal: Dict[str, Any], allocation_pct: float, curator_score: float, intent_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create approval decision strand"""
        token_data = social_signal['signal_pack']['token']
        venue_data = social_signal['signal_pack']['venue']
        # No dollar amounts - percentage-based only
        
        decision = {
            "id": str(uuid.uuid4()),
            "module": "decision_maker_lowcap",
            "kind": "decision_lowcap",
            "symbol": social_signal.get('symbol'),
            "session_bucket": social_signal.get('session_bucket'),
            "parent_id": social_signal.get('id'),
            "signal_pack": social_signal.get('signal_pack'),
            "module_intelligence": social_signal.get('module_intelligence'),
            "sig_confidence": social_signal.get('sig_confidence'),
            "sig_direction": social_signal.get('sig_direction'),
            "confidence": social_signal.get('confidence'),
            "content": {
                "source_kind": "social_lowcap",
                "source_strand_id": social_signal.get('id'),
                "curator_id": social_signal['signal_pack']['curator']['id'],
                "token": token_data,
                "venue": venue_data,
                "action": "approve",
                "allocation_pct": allocation_pct,
                "curator_confidence": curator_score,
                "reasoning": self._build_approval_reasoning(curator_score, allocation_pct, intent_analysis)
            },
            "tags": ["decision", "social_lowcap", "approved", "simple"],
            "status": "active"
        }
        
        # Create strand in database
        try:
            created_decision = await self.supabase_manager.create_strand(decision)
            self.logger.info(f"✅ APPROVED: {social_signal['signal_pack']['curator']['id']} -> {allocation_pct}%")
            
            # Trigger learning system to process the decision strand
            print(f"🔄 Decision Maker: Checking if learning system is available...")
            print(f"🔄 Decision Maker: hasattr learning_system: {hasattr(self, 'learning_system')}")
            print(f"🔄 Decision Maker: learning_system is not None: {self.learning_system is not None}")
            
            if hasattr(self, 'learning_system') and self.learning_system:
                print(f"🔄 Triggering learning system for decision strand...")
                print(f"🔄 Decision strand ID: {created_decision.get('id')}")
                print(f"🔄 Decision strand kind: {created_decision.get('kind')}")
                print(f"🔄 Decision strand action: {created_decision.get('content', {}).get('action')}")
                print(f"🔄 Decision strand tags: {created_decision.get('tags', [])}")
                try:
                    # Use await for sequential processing - wait for completion
                    print(f"   🔄 Calling learning system with await...")
                    result = await self.learning_system.process_strand_event(created_decision)
                    print(f"   ✅ Learning system completed: {result}")
                except Exception as e:
                    print(f"   ❌ Error calling learning system: {e}")
                    import traceback
                    print(f"   Traceback: {traceback.format_exc()}")
            else:
                print(f"🔄 No learning system available for decision strand callback")
            
            return created_decision
        except Exception as e:
            self.logger.error(f"Failed to create approval decision: {e}")
            return None
    
    def _build_approval_reasoning(self, curator_score: float, allocation_pct: float, intent_analysis: Dict[str, Any] = None) -> str:
        """Build detailed reasoning for approval decision including intent analysis"""
        try:
            base_reasoning = f"Approved: Curator score {curator_score:.2f}, allocating {allocation_pct}%"
            
            if intent_analysis:
                intent_data = intent_analysis.get('intent_analysis', {})
                intent_type = intent_data.get('intent_type', 'unknown')
                multiplier = intent_data.get('allocation_multiplier', 1.0)
                
                if multiplier != 1.0:
                    base_reasoning += f" (Intent: {intent_type}, {multiplier}x multiplier applied)"
                else:
                    base_reasoning += f" (Intent: {intent_type})"
            
            return base_reasoning
            
        except Exception as e:
            self.logger.error(f"Error building approval reasoning: {e}")
            return f"Approved: Curator score {curator_score:.2f}, allocating {allocation_pct}%"
    
    async def _create_rejection_decision(self, social_signal: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Create rejection decision strand"""
        decision = {
            "id": str(uuid.uuid4()),
            "module": "decision_maker_lowcap",
            "kind": "decision_lowcap",
            "symbol": social_signal.get('symbol'),
            "session_bucket": social_signal.get('session_bucket'),
            "parent_id": social_signal.get('id'),
            "signal_pack": social_signal.get('signal_pack'),
            "module_intelligence": social_signal.get('module_intelligence'),
            "sig_confidence": social_signal.get('sig_confidence'),
            "sig_direction": social_signal.get('sig_direction'),
            "confidence": social_signal.get('confidence'),
            "content": {
                "source_kind": "social_lowcap",
                "source_strand_id": social_signal.get('id'),
                "curator_id": social_signal['signal_pack']['curator']['id'],
                "token": social_signal['signal_pack']['token'],
                "venue": social_signal['signal_pack']['venue'],
                "action": "reject",
                "allocation_pct": 0,
                "curator_confidence": 0,
                "reasoning": reason
            },
            "tags": ["decision", "social_lowcap", "rejected", "simple"],
            "status": "active"
        }
        
        # Create strand in database
        try:
            created_decision = await self.supabase_manager.create_strand(decision)
            self.logger.info(f"❌ REJECTED: {social_signal['signal_pack']['curator']['id']} -> {reason}")
            return created_decision
        except Exception as e:
            self.logger.error(f"Failed to create rejection decision: {e}")
            return None
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get simple portfolio summary"""
        try:
            # Use execute_query instead of rpc
            query = "SELECT * FROM lowcap_positions WHERE book_id = %s AND status = 'active'"
            result = await self.supabase_manager.execute_query(query, [self.book_id])
            
            if result.data:
                portfolio = result.data[0]
                return {
                    "book_id": self.book_id,
                    "book_nav": self.book_nav,
                    "total_positions": portfolio.get('total_positions', 0),
                    "active_positions": portfolio.get('active_positions', 0),
                    "current_exposure_pct": portfolio.get('current_exposure_pct', 0.0),
                    "total_pnl_usd": portfolio.get('total_pnl_usd', 0.0),
                    "avg_pnl_pct": portfolio.get('avg_pnl_pct', 0.0)
                }
            else:
                return {
                    "book_id": self.book_id,
                    "book_nav": self.book_nav,
                    "total_positions": 0,
                    "active_positions": 0,
                    "current_exposure_pct": 0.0,
                    "total_pnl_usd": 0.0,
                    "avg_pnl_pct": 0.0
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get portfolio summary: {e}")
            return {"error": str(e)}


# Example usage
if __name__ == "__main__":
    # Mock supabase manager for testing
    class MockSupabaseManager:
        def rpc(self, function_name, params):
            print(f"RPC call: {function_name} with params: {params}")
            return {'data': []}
        
        def table(self, table_name):
            class MockTable:
                def select(self, columns):
                    return self
                def eq(self, column, value):
                    return self
                def execute(self):
                    return {'data': []}
            return MockTable()
        
        def create_strand(self, strand):
            print(f"Created strand: {strand['kind']} - {strand['content']['action']}")
            return strand
    
    # Test the simplified decision maker
    dml = DecisionMakerLowcapSimple(MockSupabaseManager())
    
    # Mock social signal
    social_signal = {
        'id': 'test_strand_123',
        'content': {
            'curator_id': '0xdetweiler',
            'token': {
                'ticker': 'PEPE',
                'contract': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
                'chain': 'solana'
            },
            'venue': {
                'dex': 'Raydium',
                'chain': 'solana',
                'liq_usd': 50000
            }
        }
    }
    
    # Make decision
    decision = dml.make_decision(social_signal)
    print(f"Decision result: {decision}")
