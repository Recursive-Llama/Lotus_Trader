"""
Centralized System Manager

The single point of control for the entire learning system.
This manager:
1. Watches for ALL strand types
2. Triggers appropriate modules
3. Provides context injection
4. Manages the complete data flow: RDI → CIL → CTP → DM → TD
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class CentralizedSystemManager:
    """
    Centralized System Manager
    
    This is the SINGLE point of control for the entire system.
    No modules watch for strands - this manager does everything.
    """
    
    def __init__(self, supabase_manager, llm_client, prompt_manager):
        """
        Initialize the centralized system manager
        
        Args:
            supabase_manager: Database manager
            llm_client: LLM client for analysis
            prompt_manager: Prompt manager for LLM calls
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        
        # Initialize learning system
        from centralized_learning_system import CentralizedLearningSystem
        self.learning_system = CentralizedLearningSystem(
            supabase_manager, llm_client, prompt_manager
        )
        
        # Module triggering configuration
        self.module_triggers = {
            'pattern': ['cil'],  # Pattern strands → trigger CIL
            'prediction_review': ['ctp'],  # Prediction strands → trigger CTP
            'conditional_trading_plan': ['dm'],  # Plan strands → trigger DM
            'trading_decision': ['td'],  # Decision strands → trigger TD
            'execution_outcome': ['rdi']  # Outcome strands → feedback to RDI
        }
        
        # System status
        self.is_running = False
        self.last_processing = {}
        
        # Processing intervals
        self.processing_intervals = {
            'rdi': 300,  # 5 minutes
            'cil': 60,   # 1 minute
            'ctp': 60,   # 1 minute
            'dm': 60,    # 1 minute
            'td': 60     # 1 minute
        }
    
    async def start(self):
        """Start the centralized system manager"""
        try:
            self.is_running = True
            logger.info("🚀 Starting Centralized System Manager")
            
            # Start the main monitoring loop
            asyncio.create_task(self._main_loop())
            
            # Start learning system
            asyncio.create_task(self.learning_system.start_continuous_learning(30))
            
            logger.info("✅ Centralized System Manager started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start Centralized System Manager: {e}")
            return False
    
    async def stop(self):
        """Stop the centralized system manager"""
        try:
            self.is_running = False
            await self.learning_system.stop_module_triggering()
            logger.info("🛑 Centralized System Manager stopped")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error stopping Centralized System Manager: {e}")
            return False
    
    async def _main_loop(self):
        """Main monitoring loop - watches for new strands and triggers modules"""
        logger.info("🔄 Starting main monitoring loop")
        
        while self.is_running:
            try:
                # Check for new strands and trigger modules
                await self._process_new_strands()
                
                # Wait 5 seconds before next check (much faster for trading)
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                logger.info("Main loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(60)
    
    async def _process_new_strands(self):
        """Process new strands and trigger appropriate modules"""
        try:
            # Get strands from the last 5 minutes
            five_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
            
            # Get recent strands of all types
            recent_strands = []
            for strand_type in self.module_triggers.keys():
                strands = self.supabase_manager.get_strands_by_type(strand_type, limit=50)
                recent_strands.extend(strands)
            
            # Filter by recent timestamp
            recent_strands = [
                strand for strand in recent_strands
                if self._is_recent_strand(strand, five_minutes_ago)
            ]
            
            if not recent_strands:
                return
            
            # Group strands by type
            strands_by_type = {}
            for strand in recent_strands:
                strand_type = strand.get('kind', 'unknown')
                if strand_type not in strands_by_type:
                    strands_by_type[strand_type] = []
                strands_by_type[strand_type].append(strand)
            
            # Trigger modules based on strand types
            for strand_type, strands in strands_by_type.items():
                if strand_type in self.module_triggers:
                    target_modules = self.module_triggers[strand_type]
                    for module in target_modules:
                        await self._trigger_module(module, strand_type, strands)
            
        except Exception as e:
            logger.error(f"Error processing new strands: {e}")
    
    def _is_recent_strand(self, strand: Dict[str, Any], cutoff_time: datetime) -> bool:
        """Check if strand is recent enough to process"""
        try:
            created_at = strand.get('created_at', '')
            if isinstance(created_at, str):
                strand_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                strand_time = created_at
            
            return strand_time >= cutoff_time
            
        except Exception as e:
            logger.error(f"Error checking strand timestamp: {e}")
            return False
    
    async def _trigger_module(self, module: str, strand_type: str, strands: List[Dict[str, Any]]):
        """Trigger a specific module with relevant strands"""
        try:
            # Check rate limiting
            if not self._should_trigger_module(module):
                return
            
            logger.info(f"🎯 Triggering {module.upper()} with {len(strands)} {strand_type} strands")
            
            # Get context for the module
            context = await self.learning_system.get_context_for_module(module, {})
            
            # Call the module directly
            success = await self._call_module(module, strand_type, strands, context)
            
            if success:
                logger.info(f"✅ Successfully triggered {module.upper()}")
                self.last_processing[module] = datetime.now(timezone.utc)
            else:
                logger.warning(f"⚠️  Failed to trigger {module.upper()}")
            
        except Exception as e:
            logger.error(f"Error triggering module {module}: {e}")
    
    def _should_trigger_module(self, module: str) -> bool:
        """Check if module should be triggered (rate limiting)"""
        try:
            if module not in self.last_processing:
                return True
            
            last_time = self.last_processing[module]
            interval = self.processing_intervals.get(module, 60)
            
            time_since_last = (datetime.now(timezone.utc) - last_time).total_seconds()
            return time_since_last >= interval
            
        except Exception as e:
            logger.error(f"Error checking module trigger rate: {e}")
            return True
    
    async def _call_module(self, module: str, strand_type: str, strands: List[Dict[str, Any]], context: Dict[str, Any]) -> bool:
        """Call the actual module with context"""
        try:
            if module == 'cil':
                return await self._call_cil_module(strands, context)
            elif module == 'ctp':
                return await self._call_ctp_module(strands, context)
            elif module == 'dm':
                return await self._call_dm_module(strands, context)
            elif module == 'td':
                return await self._call_td_module(strands, context)
            elif module == 'rdi':
                return await self._call_rdi_feedback(strands, context)
            else:
                logger.warning(f"Unknown module: {module}")
                return False
                
        except Exception as e:
            logger.error(f"Error calling module {module}: {e}")
            return False
    
    async def _call_cil_module(self, strands: List[Dict[str, Any]], context: Dict[str, Any]) -> bool:
        """Call CIL module to process pattern strands"""
        try:
            # Import CIL module
            from Modules.Alpha_Detector.src.intelligence.system_control.central_intelligence_layer.prediction_engine import PredictionEngine
            
            # Initialize CIL
            cil = PredictionEngine(self.supabase_manager)
            
            # Process each pattern strand
            for strand in strands:
                # CIL processes pattern strands and creates predictions
                await cil.process_pattern_strand(strand, context)
            
            return True
            
        except Exception as e:
            logger.error(f"Error calling CIL module: {e}")
            return False
    
    async def _call_ctp_module(self, strands: List[Dict[str, Any]], context: Dict[str, Any]) -> bool:
        """Call CTP module to process prediction review strands"""
        try:
            # Import CTP module
            from Modules.Alpha_Detector.src.intelligence.conditional_trading_planner.conditional_trading_planner import ConditionalTradingPlanner
            
            # Initialize CTP
            ctp = ConditionalTradingPlanner(self.supabase_manager)
            
            # Process each prediction review strand
            for strand in strands:
                # CTP processes prediction reviews and creates trading plans
                await ctp.process_prediction_review(strand, context)
            
            return True
            
        except Exception as e:
            logger.error(f"Error calling CTP module: {e}")
            return False
    
    async def _call_dm_module(self, strands: List[Dict[str, Any]], context: Dict[str, Any]) -> bool:
        """Call Decision Maker module to process trading plan strands"""
        try:
            # Import DM module
            from Modules.Alpha_Detector.src.intelligence.decision_maker.decision_maker import DecisionMaker
            
            # Initialize DM
            dm = DecisionMaker(self.supabase_manager)
            
            # Process each trading plan strand
            for strand in strands:
                # DM processes trading plans and creates decisions
                await dm.process_trading_plan(strand, context)
            
            return True
            
        except Exception as e:
            logger.error(f"Error calling DM module: {e}")
            return False
    
    async def _call_td_module(self, strands: List[Dict[str, Any]], context: Dict[str, Any]) -> bool:
        """Call Trader module to process decision strands"""
        try:
            # Import TD module
            from Modules.Alpha_Detector.src.intelligence.trader.trader import Trader
            
            # Initialize TD
            td = Trader(self.supabase_manager)
            
            # Process each decision strand
            for strand in strands:
                # TD processes decisions and executes trades
                await td.process_trading_decision(strand, context)
            
            return True
            
        except Exception as e:
            logger.error(f"Error calling TD module: {e}")
            return False
    
    async def _call_rdi_feedback(self, strands: List[Dict[str, Any]], context: Dict[str, Any]) -> bool:
        """Provide feedback to RDI from execution outcomes"""
        try:
            # RDI runs on 5-minute heartbeat, but we can provide feedback
            logger.info(f"📊 Providing feedback to RDI from {len(strands)} execution outcomes")
            
            # Update RDI's learning based on outcomes
            for strand in strands:
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
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get complete system status"""
        try:
            return {
                'is_running': self.is_running,
                'module_triggers': self.module_triggers,
                'processing_intervals': self.processing_intervals,
                'last_processing': {
                    module: time.isoformat() if time else None
                    for module, time in self.last_processing.items()
                },
                'learning_system_status': await self.learning_system.get_learning_status()
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {'error': str(e)}
