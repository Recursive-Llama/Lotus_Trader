"""
Fixed Event-Driven Learning System

Super simple: Every strand triggers the learning system via database trigger.
Learning system decides if it needs to context inject a module.
No polling, no complexity.

This version uses mock modules to avoid import path issues.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class EventDrivenLearningSystemFixed:
    """
    Fixed Event-Driven Learning System
    
    Super simple architecture:
    1. Every strand triggers learning system via database trigger
    2. Learning system decides if it needs to context inject a module
    3. No polling, no complexity
    4. Uses mock modules to avoid import issues
    """
    
    def __init__(self, supabase_manager, llm_client, prompt_manager=None):
        """
        Initialize event-driven learning system
        
        Args:
            supabase_manager: Database manager
            llm_client: LLM client for analysis
            prompt_manager: Prompt manager for LLM calls (optional)
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        self.running = False
        self.last_processed_time = datetime.now(timezone.utc)
        
        # Module subscriptions - what each module needs
        self.module_subscriptions = {
            'cil': ['pattern'],  # CIL needs pattern strands
            'ctp': ['prediction_review'],  # CTP needs prediction review strands
            'dm': ['conditional_trading_plan'],  # DM needs trading plan strands
            'td': ['trading_decision'],  # TD needs decision strands
            'rdi': ['execution_outcome'],  # RDI needs execution outcome strands
            'decision_maker_lowcap': ['social_lowcap'],  # Decision Maker Lowcap needs social lowcap strands
            'trader_lowcap': ['decision_lowcap']  # Trader Lowcap needs decision lowcap strands
        }
        
        # Track processing to avoid loops
        self.processing_strands = set()
        
    async def process_strand_event(self, strand: Dict[str, Any]) -> bool:
        """
        Process a strand that was just created (called by database trigger)
        
        Args:
            strand: Strand that was just created
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            strand_id = strand.get('id')
            strand_kind = strand.get('kind')
            
            # Avoid processing the same strand twice
            if strand_id in self.processing_strands:
                return True
            
            self.processing_strands.add(strand_id)
            
            logger.info(f"🎯 Processing strand event: {strand_id} ({strand_kind})")
            
            # 1. Process strand through learning system
            await self._process_strand_learning(strand)
            
            # 2. Check if any modules need to be triggered
            await self._check_module_triggers(strand)
            
            # Clean up
            self.processing_strands.discard(strand_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing strand event: {e}")
            self.processing_strands.discard(strand_id)
            return False
    
    async def _process_strand_learning(self, strand: Dict[str, Any]) -> None:
        """Process strand through learning system"""
        try:
            # Import learning system
            from centralized_learning_system import CentralizedLearningSystem
            
            learning_system = CentralizedLearningSystem(
                self.supabase_manager, self.llm_client, self.prompt_manager
            )
            
            # Process strand through learning
            await learning_system.process_strand(strand)
            
            logger.info(f"✅ Processed {strand.get('id')} through learning system")
            
        except Exception as e:
            logger.error(f"Error processing strand learning: {e}")
    
    async def _check_module_triggers(self, strand: Dict[str, Any]) -> None:
        """Check if any modules need to be triggered by this strand"""
        try:
            strand_kind = strand.get('kind')
            
            # Find modules that subscribe to this strand type
            target_modules = []
            for module, subscribed_types in self.module_subscriptions.items():
                if strand_kind in subscribed_types:
                    target_modules.append(module)
            
            if not target_modules:
                logger.debug(f"No modules subscribed to {strand_kind}")
                return
            
            # Trigger each module
            for module in target_modules:
                await self._trigger_module(module, strand)
            
        except Exception as e:
            logger.error(f"Error checking module triggers: {e}")
    
    async def _trigger_module(self, module: str, strand: Dict[str, Any]) -> None:
        """Trigger a specific module with context"""
        try:
            logger.info(f"🚀 Triggering {module.upper()} with {strand.get('kind')} strand")
            
            # Get context for the module
            context = await self._get_context_for_module(module, strand)
            
            # Call the module directly
            success = await self._call_module(module, strand, context)
            
            if success:
                logger.info(f"✅ Successfully triggered {module.upper()}")
            else:
                logger.warning(f"⚠️  Failed to trigger {module.upper()}")
            
        except Exception as e:
            logger.error(f"Error triggering module {module}: {e}")
    
    async def _get_context_for_module(self, module: str, strand: Dict[str, Any]) -> Dict[str, Any]:
        """Get context for a specific module"""
        try:
            # Import learning system
            from centralized_learning_system import CentralizedLearningSystem
            
            learning_system = CentralizedLearningSystem(
                self.supabase_manager, self.llm_client, self.prompt_manager
            )
            
            # Get context from learning system
            context = await learning_system.get_context_for_module(module, {})
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting context for module {module}: {e}")
            return {}
    
    async def _call_module(self, module: str, strand: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Call the actual module with context"""
        try:
            if module == 'cil':
                return await self._call_cil_module(strand, context)
            elif module == 'ctp':
                return await self._call_ctp_module(strand, context)
            elif module == 'dm':
                return await self._call_dm_module(strand, context)
            elif module == 'td':
                return await self._call_td_module(strand, context)
            elif module == 'rdi':
                return await self._call_rdi_feedback(strand, context)
            elif module == 'decision_maker_lowcap':
                return await self._call_decision_maker_lowcap_module(strand, context)
            elif module == 'trader_lowcap':
                return await self._call_trader_lowcap_module(strand, context)
            else:
                logger.warning(f"Unknown module: {module}")
                return False
                
        except Exception as e:
            logger.error(f"Error calling module {module}: {e}")
            return False
    
    async def _call_cil_module(self, strand: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Call CIL module to process pattern strands"""
        try:
            # Import clean CIL module
            from clean_cil_module import CleanCILModule
            
            # Initialize CIL
            cil = CleanCILModule(self.supabase_manager, self.llm_client)
            
            # Process pattern strand (handles both predictions and reviews)
            success = await cil.process_pattern_strand(strand)
            
            return success
            
        except Exception as e:
            logger.error(f"Error calling CIL module: {e}")
            return False
    
    async def _call_ctp_module(self, strand: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Call CTP module to process prediction review strands"""
        try:
            # Use mock CTP module to avoid import issues
            ctp = MockCTPModule(self.supabase_manager, self.llm_client)
            
            # Process prediction review strand
            success = await ctp.process_prediction_review(strand, context)
            
            return success
            
        except Exception as e:
            logger.error(f"Error calling CTP module: {e}")
            return False
    
    async def _call_dm_module(self, strand: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Call Decision Maker module to process trading plan strands"""
        try:
            # Use mock DM module to avoid import issues
            dm = MockDMModule(self.supabase_manager, self.llm_client)
            
            # Process trading plan strand
            success = await dm.process_trading_plan(strand, context)
            
            return success
            
        except Exception as e:
            logger.error(f"Error calling DM module: {e}")
            return False
    
    async def _call_td_module(self, strand: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Call Trader module to process decision strands"""
        try:
            # Use mock TD module to avoid import issues
            td = MockTDModule(self.supabase_manager, self.llm_client)
            
            # Process decision strand
            success = await td.process_trading_decision(strand, context)
            
            return success
            
        except Exception as e:
            logger.error(f"Error calling TD module: {e}")
            return False
    
    async def _call_rdi_feedback(self, strand: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Provide feedback to RDI from execution outcomes"""
        try:
            # RDI runs on 5-minute heartbeat, but we can provide feedback
            logger.info(f"📊 Providing feedback to RDI from execution outcome: {strand.get('id')}")
            
            # Update RDI's learning based on outcomes
            await self._update_rdi_learning(strand, context)
            
            return True
            
        except Exception as e:
            logger.error(f"Error providing RDI feedback: {e}")
            return False
    
    async def _update_rdi_learning(self, outcome_strand: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Update RDI learning based on execution outcomes"""
        try:
            # This would update RDI's pattern recognition based on actual outcomes
            logger.info(f"🔄 Updating RDI learning with outcome: {outcome_strand.get('id')}")
            
        except Exception as e:
            logger.error(f"Error updating RDI learning: {e}")


# --- Mock Modules to avoid import issues ---

class MockCTPModule:
    """Mock CTP module for testing"""
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
    
    async def process_prediction_review(self, strand: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Process prediction review and create conditional trading plan"""
        try:
            self.logger.info(f"🎯 Mock CTP processing prediction review: {strand.get('id')}")
            
            # Create conditional trading plan strand
            plan_id = f"ctp_plan_{int(datetime.now().timestamp())}"
            plan_strand = {
                'id': plan_id,
                'kind': 'conditional_trading_plan',
                'module': 'alpha',
                'agent_id': 'ctp',
                'symbol': strand.get('symbol', 'UNKNOWN'),
                'timeframe': strand.get('timeframe', '1h'),
                'session_bucket': 'GLOBAL',
                'regime': 'bullish',
                'tags': ['conditional_trading_plan', 'dm', 'plan_strand'],
                'content': {
                    'plan_type': 'conditional_entry',
                    'entry_conditions': ['price_above_50000', 'volume_spike'],
                    'exit_conditions': ['target_hit', 'stop_loss'],
                    'risk_reward_ratio': 2.5,
                    'position_size': 0.02,
                    'confidence': 0.8,
                    'prediction_review_id': strand.get('id')
                },
                'confidence': 0.8,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Insert into database
            result = self.supabase_manager.client.table('ad_strands').insert(plan_strand).execute()
            if result.data:
                self.logger.info(f"✅ Created conditional trading plan: {plan_id}")
                return True
            else:
                self.logger.error(f"❌ Failed to create conditional trading plan")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in mock CTP processing: {e}")
            return False


class MockDMModule:
    """Mock Decision Maker module for testing"""
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
    
    async def process_trading_plan(self, strand: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Process trading plan and create trading decision"""
        try:
            self.logger.info(f"🎯 Mock DM processing trading plan: {strand.get('id')}")
            
            # Create trading decision strand
            decision_id = f"dm_decision_{int(datetime.now().timestamp())}"
            decision_strand = {
                'id': decision_id,
                'kind': 'trading_decision',
                'module': 'alpha',
                'agent_id': 'dm',
                'symbol': strand.get('symbol', 'UNKNOWN'),
                'timeframe': strand.get('timeframe', '1h'),
                'session_bucket': 'GLOBAL',
                'regime': 'bullish',
                'tags': ['trading_decision', 'td', 'decision_strand'],
                'content': {
                    'decision_type': 'execute_trade',
                    'action': 'buy',
                    'quantity': 0.02,
                    'entry_price': 50000.0,
                    'target_price': 52500.0,
                    'stop_loss': 48000.0,
                    'confidence': 0.85,
                    'plan_id': strand.get('id')
                },
                'confidence': 0.85,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Insert into database
            result = self.supabase_manager.client.table('ad_strands').insert(decision_strand).execute()
            if result.data:
                self.logger.info(f"✅ Created trading decision: {decision_id}")
                return True
            else:
                self.logger.error(f"❌ Failed to create trading decision")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in mock DM processing: {e}")
            return False


class MockTDModule:
    """Mock Trader module for testing"""
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
    
    async def process_trading_decision(self, strand: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Process trading decision and create execution outcome"""
        try:
            self.logger.info(f"🎯 Mock TD processing trading decision: {strand.get('id')}")
            
            # Create execution outcome strand
            outcome_id = f"td_outcome_{int(datetime.now().timestamp())}"
            outcome_strand = {
                'id': outcome_id,
                'kind': 'execution_outcome',
                'module': 'alpha',
                'agent_id': 'td',
                'symbol': strand.get('symbol', 'UNKNOWN'),
                'timeframe': strand.get('timeframe', '1h'),
                'session_bucket': 'GLOBAL',
                'regime': 'bullish',
                'tags': ['execution_outcome', 'rdi', 'outcome_strand'],
                'content': {
                    'outcome_type': 'success',
                    'executed_price': 50050.0,
                    'final_price': 52500.0,
                    'return_pct': 4.9,
                    'execution_quality': 'excellent',
                    'slippage': 0.001,
                    'decision_id': strand.get('id')
                },
                'confidence': 0.9,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Insert into database
            result = self.supabase_manager.client.table('ad_strands').insert(outcome_strand).execute()
            if result.data:
                self.logger.info(f"✅ Created execution outcome: {outcome_id}")
                return True
            else:
                self.logger.error(f"❌ Failed to create execution outcome")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in mock TD processing: {e}")
            return False
    
    async def _call_decision_maker_lowcap_module(self, strand: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Call Decision Maker Lowcap module to process social lowcap strands"""
        try:
            # Import the simplified Decision Maker Lowcap
            from intelligence.decision_maker_lowcap.decision_maker_lowcap_simple import DecisionMakerLowcapSimple
            
            # Initialize Decision Maker Lowcap
            dml = DecisionMakerLowcapSimple(self.supabase_manager)
            
            # Process the social lowcap strand
            decision = dml.make_decision(strand)
            
            if decision:
                self.logger.info(f"✅ Decision Maker Lowcap created decision: {decision.get('id')}")
                return True
            else:
                self.logger.info(f"❌ Decision Maker Lowcap rejected signal: {strand.get('id')}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error calling Decision Maker Lowcap: {e}")
            return False
    
    async def _call_trader_lowcap_module(self, strand: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Call Trader Lowcap module to process decision lowcap strands"""
        try:
            # Import the simplified Trader Lowcap
            from intelligence.trader_lowcap.trader_lowcap_simple_v2 import TraderLowcapSimpleV2
            
            # Initialize Trader Lowcap
            trader = TraderLowcapSimpleV2(self.supabase_manager)
            
            # Process the decision lowcap strand
            position = trader.execute_decision(strand)
            
            if position:
                self.logger.info(f"✅ Trader Lowcap created position: {position.get('position_id')}")
                return True
            else:
                self.logger.info(f"❌ Trader Lowcap failed to execute: {strand.get('id')}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error calling Trader Lowcap: {e}")
            return False
