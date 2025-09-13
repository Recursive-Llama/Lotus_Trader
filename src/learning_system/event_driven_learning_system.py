"""
Event-Driven Learning System

Super simple: Every strand triggers the learning system via database trigger.
Learning system decides if it needs to context inject a module.
No polling, no complexity.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class EventDrivenLearningSystem:
    """
    Event-Driven Learning System
    
    Super simple architecture:
    1. Every strand triggers learning system via database trigger
    2. Learning system decides if it needs to context inject a module
    3. No polling, no complexity
    """
    
    def __init__(self, supabase_manager, llm_client, prompt_manager):
        """
        Initialize event-driven learning system
        
        Args:
            supabase_manager: Database manager
            llm_client: LLM client for analysis
            prompt_manager: Prompt manager for LLM calls
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        
        # Module subscriptions - what each module needs
        self.module_subscriptions = {
            'cil': ['pattern'],  # CIL needs pattern strands
            'ctp': ['prediction_review'],  # CTP needs prediction review strands
            'dm': ['conditional_trading_plan'],  # DM needs trading plan strands
            'td': ['trading_decision'],  # TD needs decision strands
            'rdi': ['execution_outcome']  # RDI needs execution outcome strands
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
            # Import CTP module
            from Modules.Alpha_Detector.src.intelligence.conditional_trading_planner.conditional_trading_planner import ConditionalTradingPlanner
            
            # Initialize CTP
            ctp = ConditionalTradingPlanner(self.supabase_manager)
            
            # Process prediction review strand
            await ctp.process_prediction_review(strand, context)
            
            return True
            
        except Exception as e:
            logger.error(f"Error calling CTP module: {e}")
            return False
    
    async def _call_dm_module(self, strand: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Call Decision Maker module to process trading plan strands"""
        try:
            # Import DM module
            from Modules.Alpha_Detector.src.intelligence.decision_maker.decision_maker import DecisionMaker
            
            # Initialize DM
            dm = DecisionMaker(self.supabase_manager)
            
            # Process trading plan strand
            await dm.process_trading_plan(strand, context)
            
            return True
            
        except Exception as e:
            logger.error(f"Error calling DM module: {e}")
            return False
    
    async def _call_td_module(self, strand: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Call Trader module to process decision strands"""
        try:
            # Import TD module
            from Modules.Alpha_Detector.src.intelligence.trader.trader import Trader
            
            # Initialize TD
            td = Trader(self.supabase_manager)
            
            # Process decision strand
            await td.process_trading_decision(strand, context)
            
            return True
            
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
