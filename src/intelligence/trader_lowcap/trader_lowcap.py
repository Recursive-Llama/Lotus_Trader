"""
Trader Lowcap (TDL)

Specialized execution for social lowcap trades.
Implements three-way entry and progressive exit strategies.
Learns from execution outcomes and venue performance.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import yaml
import os

logger = logging.getLogger(__name__)


class TraderLowcap:
    """
    Trader Lowcap - Specialized execution with learning
    
    This module:
    - Reads decision_lowcap strands from DML
    - Executes three-way entry strategy (immediate, -20%, -50%)
    - Manages progressive exit strategy (33% at 2x, 4x, 8x)
    - Tracks positions in positions table
    - Creates execution strands for learning system
    - Learns from execution outcomes and venue performance
    """
    
    def __init__(self, supabase_manager, learning_system, context_engine, llm_client, config_path: str = None):
        """
        Initialize Trader Lowcap
        
        Args:
            supabase_manager: Database manager for strands and positions
            learning_system: Centralized learning system
            context_engine: Context injection engine
            llm_client: LLM client for execution planning
            config_path: Path to TDL configuration file
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
        
        self.book_id = self.config['trader_lowcap']['book']
        self.execution_strategy = self.config['trader_lowcap']['execution_strategy']
        self.position_splits = self.config['trader_lowcap']['position_splits']
        self.exit_strategy = self.config['trader_lowcap']['exit_strategy']
        self.exit_splits = self.config['trader_lowcap']['exit_splits']
        self.venue_preferences = self.config['trader_lowcap']['venue_preferences']
        
        self.logger.info(f"Trader Lowcap initialized for book: {self.book_id}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load TDL configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load TDL config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default TDL configuration"""
        return {
            'trader_lowcap': {
                'book': 'social',
                'execution_strategy': 'three_way_entry',
                'position_splits': {
                    'immediate': 0.33,
                    'minus_20_pct': 0.33,
                    'minus_50_pct': 0.34
                },
                'exit_strategy': 'progressive_exit',
                'exit_splits': {
                    'at_2x': 0.33,
                    'at_4x': 0.33,
                    'at_8x': 0.34
                },
                'venue_preferences': {
                    'solana': ['Raydium', 'Orca', 'Saber'],
                    'ethereum': ['Uniswap', 'Sushiswap'],
                    'base': ['BaseSwap', 'Uniswap']
                }
            }
        }
    
    async def execute_trade(self, decision: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute trade based on DML decision
        
        Args:
            decision: decision_lowcap strand from DML
            
        Returns:
            Created execution strand or None if execution failed
        """
        try:
            if decision['content']['action'] != 'approve':
                self.logger.info(f"Decision not approved, skipping execution: {decision['content']['reasoning']}")
                return None
            
            token_data = decision['content']['token']
            venue_data = decision['content']['venue']
            allocation_pct = decision['content']['allocation_pct']
            allocation_usd = decision['content']['allocation_usd']
            
            # Get execution context from learning system
            execution_context = self.context_engine.get_context_for_module(
                'trader_lowcap',
                {'token': token_data, 'venue': venue_data}
            )
            
            # Select best venue
            selected_venue = self._select_best_venue(venue_data, execution_context)
            
            # Create position in positions table
            position = {
                "book_id": self.book_id,
                "module": "trader_lowcap",
                "strand_id": decision['id'],
                "token_chain": token_data['chain'],
                "token_contract": token_data.get('contract'),
                "token_ticker": token_data['ticker'],
                "entry_strategy": self.execution_strategy,
                "exit_strategy": self.exit_strategy,
                "position_size_usd": allocation_usd,
                "entry_price": self._get_current_price(token_data),
                "primary_venue": selected_venue['dex']
            }
            
            # Add entry level details
            position.update(self._calculate_entry_levels(allocation_usd, position['entry_price']))
            
            # Add exit level details
            position.update(self._calculate_exit_levels(position['entry_price']))
            
            # Create position in database
            position_id = self.supabase_manager.create_position(position)
            
            # Create execution strand for learning system
            execution = {
                "module": "trader_lowcap",
                "kind": "execution_lowcap",
                "content": {
                    "source_decision": decision['id'],
                    "position_id": position_id,
                    "execution_strategy": self.execution_strategy,
                    "position_splits": self.position_splits,
                    "venue": selected_venue,
                    "allocation_pct": allocation_pct,
                    "allocation_usd": allocation_usd,
                    "execution_quality": 0.0,  # Will be updated after execution
                    "slippage_pct": 0.0,      # Will be updated after execution
                    "venue_effectiveness": execution_context.get('venue_effectiveness', 0.5)
                },
                "tags": ["execution", "social_lowcap", "three_way_entry"],
                "status": "active"
            }
            
            # Create strand in database
            created_execution = await self.supabase_manager.create_strand(execution)
            
            # Start execution process
            await self._start_execution(position_id, position, execution_context)
            
            self.logger.info(f"Created execution_lowcap strand: {token_data['ticker']} -> {allocation_pct:.1f}%")
            return created_execution
            
        except Exception as e:
            self.logger.error(f"Failed to execute trade for {decision.get('content', {}).get('token', {}).get('ticker', 'unknown')}: {e}")
            return None
    
    def _select_best_venue(self, venue_data: Dict[str, Any], execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select best venue for execution
        
        Args:
            venue_data: Venue data from decision
            execution_context: Execution context from learning system
            
        Returns:
            Selected venue data
        """
        try:
            # Get venue preferences for chain
            chain = venue_data.get('chain', 'solana')
            preferred_venues = self.venue_preferences.get(chain, [venue_data['dex']])
            
            # Check if current venue is preferred
            if venue_data['dex'] in preferred_venues:
                return venue_data
            
            # Get venue effectiveness from learning system
            venue_effectiveness = execution_context.get('venue_effectiveness', {})
            
            # Select best venue based on effectiveness and preferences
            best_venue = venue_data  # Default to original venue
            best_score = venue_effectiveness.get(venue_data['dex'], 0.5)
            
            for venue in preferred_venues:
                score = venue_effectiveness.get(venue, 0.5)
                if score > best_score:
                    best_score = score
                    # Update venue data (would need actual venue resolution)
                    best_venue = {
                        **venue_data,
                        'dex': venue,
                        'venue_effectiveness': score
                    }
            
            return best_venue
        except Exception as e:
            self.logger.error(f"Failed to select best venue: {e}")
            return venue_data
    
    def _calculate_entry_levels(self, total_allocation: float, entry_price: float) -> Dict[str, Any]:
        """
        Calculate entry level details for three-way entry strategy
        
        Args:
            total_allocation: Total allocation in USD
            entry_price: Current entry price
            
        Returns:
            Entry level details for position
        """
        # Use LLM for intelligent execution planning if available
        if hasattr(self.llm_client, 'get_prompt'):
            return asyncio.run(self._llm_execution_planning(total_allocation, entry_price))
        
        # Fallback to rule-based calculation
        return self._rule_based_entry_levels(total_allocation, entry_price)
    
    async def _llm_execution_planning(self, total_allocation: float, entry_price: float) -> Dict[str, Any]:
        """Use LLM for intelligent execution planning"""
        try:
            # Get prompt template
            prompt_data = self.llm_client.get_prompt('trader_lowcap', 'execution_planning')
            
            # Format prompt with context
            prompt = prompt_data['prompt'].format(
                token_ticker='UNKNOWN',  # Would be passed from decision
                token_chain='solana',
                allocation_usd=total_allocation,
                allocation_pct=(total_allocation / 100000) * 100,  # Mock book NAV
                current_price=entry_price,
                venue_dex='Raydium',
                liquidity_usd=15000,  # Mock liquidity
                volume_24h=50000,  # Mock volume
                volatility_pct=5.0,  # Mock volatility
                spread_pct=0.1,  # Mock spread
                order_book_depth='medium',
                recent_slippage_pct=0.2
            )
            
            # Generate response
            response = await self.llm_client.generate_async(prompt, system_message=prompt_data.get('system_message', ''))
            
            # Parse response
            plan = json.loads(response)
            
            # Convert LLM response to entry level format
            return {
                "entry_1_size_usd": total_allocation * plan['entry_levels'][0],
                "entry_1_price": plan['entry_prices'][0],
                "entry_2_size_usd": total_allocation * plan['entry_levels'][1],
                "entry_2_price": plan['entry_prices'][1],
                "entry_3_size_usd": total_allocation * plan['entry_levels'][2],
                "entry_3_price": plan['entry_prices'][2]
            }
            
        except Exception as e:
            self.logger.error(f"Error in LLM execution planning: {e}")
            return self._rule_based_entry_levels(total_allocation, entry_price)
    
    def _rule_based_entry_levels(self, total_allocation: float, entry_price: float) -> Dict[str, Any]:
        """Fallback rule-based entry level calculation"""
        immediate_pct = self.position_splits['immediate']
        minus_20_pct = self.position_splits['minus_20_pct']
        minus_50_pct = self.position_splits['minus_50_pct']
        
        return {
            "entry_1_size_usd": total_allocation * immediate_pct,
            "entry_1_price": entry_price,
            "entry_2_size_usd": total_allocation * minus_20_pct,
            "entry_2_price": entry_price * 0.8,  # -20% price
            "entry_3_size_usd": total_allocation * minus_50_pct,
            "entry_3_price": entry_price * 0.5   # -50% price
        }
    
    def _calculate_exit_levels(self, entry_price: float) -> Dict[str, Any]:
        """
        Calculate exit level details for progressive exit strategy
        
        Args:
            entry_price: Entry price
            
        Returns:
            Exit level details for position
        """
        at_2x_pct = self.exit_splits['at_2x']
        at_4x_pct = self.exit_splits['at_4x']
        at_8x_pct = self.exit_splits['at_8x']
        
        return {
            "exit_1_target_price": entry_price * 2,  # 2x target
            "exit_2_target_price": entry_price * 4,  # 4x target
            "exit_3_target_price": entry_price * 8   # 8x target
        }
    
    def _get_current_price(self, token_data: Dict[str, Any]) -> float:
        """
        Get current price for token (mock for now)
        
        Args:
            token_data: Token information
            
        Returns:
            Current price
        """
        # This would integrate with actual price feeds
        return 0.25  # Mock price
    
    async def _start_execution(self, position_id: str, position: Dict[str, Any], execution_context: Dict[str, Any]):
        """
        Start the execution process for three-way entry
        
        Args:
            position_id: Position ID in database
            position: Position data
            execution_context: Execution context
        """
        try:
            # Execute immediate entry (entry_1)
            await self._execute_entry_level(position_id, 1, position, execution_context)
            
            # Set up conditional entries for -20% and -50%
            self._setup_conditional_entries(position_id, position, execution_context)
            
            # Set up exit monitoring
            self._setup_exit_monitoring(position_id, position, execution_context)
            
        except Exception as e:
            self.logger.error(f"Failed to start execution for position {position_id}: {e}")
    
    async def _execute_entry_level(self, position_id: str, level: int, position: Dict[str, Any], execution_context: Dict[str, Any]):
        """
        Execute a specific entry level
        
        Args:
            position_id: Position ID
            level: Entry level (1, 2, or 3)
            position: Position data
            execution_context: Execution context
        """
        try:
            size_key = f"entry_{level}_size_usd"
            price_key = f"entry_{level}_price"
            
            size_usd = position.get(size_key, 0)
            target_price = position.get(price_key, 0)
            
            if size_usd <= 0:
                return
            
            # Mock execution (would integrate with actual DEX APIs)
            executed_price = target_price * (1 + self._get_slippage(execution_context))
            executed_timestamp = datetime.now(timezone.utc)
            
            # Update position in database
            self.supabase_manager.update_position_entry(
                position_id, 
                level, 
                executed_price, 
                executed_timestamp,
                self._get_slippage(execution_context)
            )
            
            # Create position update strand for learning
            await self._create_position_update_strand(position_id, level, "entry", executed_price, size_usd)
            
            self.logger.info(f"Executed entry level {level} for position {position_id}: {size_usd:.2f} USD at {executed_price:.4f}")
            
        except Exception as e:
            self.logger.error(f"Failed to execute entry level {level} for position {position_id}: {e}")
    
    def _setup_conditional_entries(self, position_id: str, position: Dict[str, Any], execution_context: Dict[str, Any]):
        """Set up conditional entries for -20% and -50% levels"""
        # This would set up price monitoring and conditional execution
        # For now, just log the setup
        self.logger.info(f"Set up conditional entries for position {position_id}")
    
    def _setup_exit_monitoring(self, position_id: str, position: Dict[str, Any], execution_context: Dict[str, Any]):
        """Set up exit monitoring for progressive exit strategy"""
        # This would set up price monitoring for exit targets
        # For now, just log the setup
        self.logger.info(f"Set up exit monitoring for position {position_id}")
    
    def _get_slippage(self, execution_context: Dict[str, Any]) -> float:
        """Get slippage percentage based on execution context"""
        # This would calculate actual slippage based on venue and market conditions
        return 0.001  # Mock 0.1% slippage
    
    async def _create_position_update_strand(self, position_id: str, level: int, action: str, price: float, size_usd: float):
        """Create position update strand for learning system"""
        try:
            update_strand = {
                "module": "trader_lowcap",
                "kind": "position_update",
                "content": {
                    "position_id": position_id,
                    "level": level,
                    "action": action,
                    "price": price,
                    "size_usd": size_usd,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "execution_quality": 0.9,  # Mock quality score
                    "venue_effectiveness": 0.8  # Mock venue effectiveness
                },
                "tags": ["position_update", "execution", "learning"],
                "status": "active"
            }
            
            await self.supabase_manager.create_strand(update_strand)
            
        except Exception as e:
            self.logger.error(f"Failed to create position update strand: {e}")
    
    def process_learning_feedback(self, execution_outcome: Dict[str, Any]):
        """
        Process learning feedback from execution outcomes
        
        Args:
            execution_outcome: Execution outcome data for learning
        """
        try:
            # This would integrate with the learning system
            # to update execution quality and venue effectiveness
            self.logger.info(f"Processing learning feedback for execution: {execution_outcome.get('id', 'unknown')}")
            
            # The learning system will automatically process this through strands
            # and update execution quality scores via context injection
            
        except Exception as e:
            self.logger.error(f"Failed to process learning feedback: {e}")
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary for monitoring"""
        try:
            # Get active positions for this book
            active_positions = self.supabase_manager.get_active_positions(self.book_id)
            
            # Calculate execution metrics
            total_positions = len(active_positions)
            executed_entries = sum(1 for pos in active_positions if pos.get('entry_1_executed', False))
            avg_execution_quality = sum(pos.get('execution_quality', 0) for pos in active_positions) / max(total_positions, 1)
            
            return {
                "book_id": self.book_id,
                "total_positions": total_positions,
                "executed_entries": executed_entries,
                "avg_execution_quality": avg_execution_quality,
                "execution_strategy": self.execution_strategy,
                "exit_strategy": self.exit_strategy
            }
        except Exception as e:
            self.logger.error(f"Failed to get execution summary: {e}")
            return {}
