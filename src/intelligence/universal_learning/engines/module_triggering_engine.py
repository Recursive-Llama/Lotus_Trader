"""
Module Triggering Engine

Manages the triggering of modules based on strand creation.
Implements the data flow: RDI → CIL → CTP → DM → TD
Each module is triggered when relevant strands are created.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class ModuleTriggeringEngine:
    """
    Module Triggering Engine
    
    Manages the triggering of modules based on strand creation.
    Implements the data flow: RDI → CIL → CTP → DM → TD
    """
    
    def __init__(self, supabase_manager, learning_system):
        """
        Initialize module triggering engine
        
        Args:
            supabase_manager: Database manager for strand operations
            learning_system: Learning system for context injection
        """
        self.supabase_manager = supabase_manager
        self.learning_system = learning_system
        self.logger = logging.getLogger(__name__)
        
        # Module triggering configuration
        self.module_triggers = {
            'pattern': ['cil'],  # Pattern strands trigger CIL
            'prediction_review': ['ctp'],  # Prediction review strands trigger CTP
            'conditional_trading_plan': ['dm'],  # Trading plan strands trigger DM
            'trading_decision': ['td'],  # Decision strands trigger TD
            'execution_outcome': ['rdi'],  # Execution outcome strands provide feedback to RDI
            'decision_lowcap': ['trader_lowcap'],  # Decision lowcap strands trigger Trader Lowcap
            'social_lowcap': ['decision_maker_lowcap']  # Social lowcap strands trigger Decision Maker Lowcap
        }
        
        # Module processing intervals (in seconds)
        self.processing_intervals = {
            'rdi': 300,  # 5 minutes
            'cil': 60,   # 1 minute (immediate response)
            'ctp': 60,   # 1 minute (immediate response)
            'dm': 60,    # 1 minute (immediate response)
            'td': 60,    # 1 minute (immediate response)
            'decision_maker_lowcap': 5,  # 5 seconds (immediate social response)
            'trader_lowcap': 10  # 10 seconds (immediate execution)
        }
        
        # Track last processing times
        self.last_processing = {}
        
        # Module status
        self.is_running = False
        
    async def start(self):
        """Start the module triggering engine"""
        try:
            self.is_running = True
            self.logger.info("Module triggering engine started")
            
            # Start the main triggering loop
            asyncio.create_task(self._triggering_loop())
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start module triggering engine: {e}")
            return False
    
    async def stop(self):
        """Stop the module triggering engine"""
        try:
            self.is_running = False
            self.logger.info("Module triggering engine stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop module triggering engine: {e}")
            return False
    
    async def _triggering_loop(self):
        """Main triggering loop that monitors for new strands"""
        self.logger.info("Starting module triggering loop")
        
        while self.is_running:
            try:
                # Check for new strands and trigger appropriate modules
                await self._process_new_strands()
                
                # Sleep for 30 seconds before next check
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                self.logger.info("Module triggering loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in module triggering loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _process_new_strands(self):
        """Process new strands and trigger appropriate modules"""
        try:
            # Get strands from the last 5 minutes
            five_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
            
            # Get recent strands
            recent_strands = self.supabase_manager.get_strands_by_type('pattern', limit=50)
            recent_strands.extend(self.supabase_manager.get_strands_by_type('prediction_review', limit=50))
            recent_strands.extend(self.supabase_manager.get_strands_by_type('conditional_trading_plan', limit=50))
            recent_strands.extend(self.supabase_manager.get_strands_by_type('trading_decision', limit=50))
            recent_strands.extend(self.supabase_manager.get_strands_by_type('execution_outcome', limit=50))
            
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
            self.logger.error(f"Error processing new strands: {e}")
    
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
            self.logger.error(f"Error checking strand timestamp: {e}")
            return False
    
    async def _trigger_module(self, module: str, strand_type: str, strands: List[Dict[str, Any]]):
        """Trigger a specific module with relevant strands"""
        try:
            # Check if module should be triggered (rate limiting)
            if not self._should_trigger_module(module):
                return
            
            self.logger.info(f"Triggering {module.upper()} with {len(strands)} {strand_type} strands")
            
            # Get context for the module
            context = await self.learning_system.get_context_for_module(module, {})
            
            # Create trigger event
            trigger_event = {
                'module': module,
                'strand_type': strand_type,
                'strands': strands,
                'context': context,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'trigger_id': f"trigger_{module}_{strand_type}_{datetime.now().timestamp()}"
            }
            
            # Process the trigger
            await self._process_module_trigger(trigger_event)
            
            # Update last processing time
            self.last_processing[module] = datetime.now(timezone.utc)
            
        except Exception as e:
            self.logger.error(f"Error triggering module {module}: {e}")
    
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
            self.logger.error(f"Error checking module trigger rate: {e}")
            return True
    
    async def _process_module_trigger(self, trigger_event: Dict[str, Any]):
        """Process a module trigger event by calling the actual module"""
        try:
            module = trigger_event['module']
            strand_type = trigger_event['strand_type']
            strands = trigger_event['strands']
            context = trigger_event['context']
            
            # Log the trigger
            self.logger.info(f"Processing trigger for {module.upper()}: {len(strands)} {strand_type} strands")
            
            # Call the actual module method
            success = await self._call_module_method(module, strand_type, strands, context)
            
            if success:
                self.logger.info(f"Successfully triggered {module.upper()}")
            else:
                self.logger.warning(f"Failed to trigger {module.upper()}")
            
        except Exception as e:
            self.logger.error(f"Error processing module trigger: {e}")
    
    async def _call_module_method(self, module: str, strand_type: str, strands: List[Dict[str, Any]], context: Dict[str, Any]) -> bool:
        """Call the actual module method with context"""
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
                self.logger.warning(f"Unknown module: {module}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error calling module {module}: {e}")
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
            self.logger.error(f"Error calling CIL module: {e}")
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
            self.logger.error(f"Error calling CTP module: {e}")
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
            self.logger.error(f"Error calling DM module: {e}")
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
            self.logger.error(f"Error calling TD module: {e}")
            return False
    
    async def _call_rdi_feedback(self, strands: List[Dict[str, Any]], context: Dict[str, Any]) -> bool:
        """Provide feedback to RDI from execution outcomes"""
        try:
            # RDI doesn't need to be called - it runs on 5-minute heartbeat
            # But we can update its learning based on outcomes
            self.logger.info(f"Providing feedback to RDI from {len(strands)} execution outcomes")
            
            # Update RDI's learning based on outcomes
            for strand in strands:
                # Update RDI's pattern recognition based on outcomes
                await self._update_rdi_learning(strand, context)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error providing RDI feedback: {e}")
            return False
    
    async def _update_rdi_learning(self, outcome_strand: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Update RDI learning based on execution outcomes"""
        try:
            # This would update RDI's pattern recognition based on actual outcomes
            # For now, just log the feedback
            self.logger.info(f"Updating RDI learning with outcome: {outcome_strand.get('id')}")
            
        except Exception as e:
            self.logger.error(f"Error updating RDI learning: {e}")
    
    async def get_triggering_status(self) -> Dict[str, Any]:
        """Get current triggering status"""
        try:
            status = {
                'is_running': self.is_running,
                'module_triggers': self.module_triggers,
                'processing_intervals': self.processing_intervals,
                'last_processing': {
                    module: time.isoformat() if time else None
                    for module, time in self.last_processing.items()
                }
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting triggering status: {e}")
            return {'error': str(e)}
    
    async def force_trigger_module(self, module: str, strand_type: str = None) -> bool:
        """Force trigger a specific module (for testing)"""
        try:
            if strand_type:
                # Get recent strands of specific type
                strands = self.supabase_manager.get_strands_by_type(strand_type, limit=10)
                if strands:
                    await self._trigger_module(module, strand_type, strands)
                    return True
            else:
                # Get recent strands of any type that would trigger this module
                for trigger_strand_type, trigger_modules in self.module_triggers.items():
                    if module in trigger_modules:
                        strands = self.supabase_manager.get_strands_by_type(trigger_strand_type, limit=10)
                        if strands:
                            await self._trigger_module(module, trigger_strand_type, strands)
                            return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error force triggering module {module}: {e}")
            return False
