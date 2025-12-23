"""
Universal Learning System

This module provides the core universal learning system that works with all strand types.
It processes strands and triggers downstream modules (Decision Maker, PM).

The system implements:
1. Strand event processing (position_closed, social signals, decisions)
2. Coefficient updates from closed trades (timeframe weights)
3. Integration with existing learning system (pattern scope aggregation, LLM research layer)

This is the foundation that CIL specialized learning builds upon.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone

from .coefficient_updater import CoefficientUpdater
from llm_integration.prompt_manager import PromptManager
from llm_integration.openrouter_client import OpenRouterClient
from intelligence.lowcap_portfolio_manager.jobs.pattern_scope_aggregator import process_position_closed_strand
from intelligence.lowcap_portfolio_manager.pm.llm_research_layer import LLMResearchLayer

logger = logging.getLogger(__name__)


class UniversalLearningSystem:
    """
    Universal Learning System for all strand types
    
    This is the foundation learning system that works with all strands.
    CIL specialized learning builds on top of this.
    """
    
    def __init__(self, supabase_manager, llm_client=None, llm_config=None):
        """
        Initialize universal learning system
        
        Args:
            supabase_manager: Database manager
            llm_client: LLM client for braid creation (optional)
            llm_config: LLM configuration dictionary (optional)
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        self.decision_maker = None  # Will be set externally
        
        # Initialize LLM components
        if llm_config and not llm_client:
            self.llm_manager = OpenRouterClient()
            self.prompt_manager = PromptManager()
        elif llm_client:
            self.llm_manager = llm_client
            self.prompt_manager = PromptManager()
        else:
            self.llm_manager = None
            self.prompt_manager = None
        
        # Initialize components
        self.coefficient_updater = CoefficientUpdater(supabase_manager.client)
        
        # Initialize LLM Learning Layer (build from day 1, phased enablement)
        self.llm_research_layer = LLMResearchLayer(
            sb_client=supabase_manager.client,
            llm_client=llm_client,
            enablement=None  # Uses defaults, can be updated later
        )
    
    def set_decision_maker(self, decision_maker):
        """Set the decision maker instance to use"""
        self.decision_maker = decision_maker
    
    async def process_strand_event(self, strand: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single strand event from social ingest or other modules
        
        This method is called when a new strand is created and needs to be processed
        by the learning system. It handles position_closed strands for learning updates
        and triggers downstream modules (Decision Maker, Trader).
        
        Args:
            strand: Strand dictionary to process
            
        Returns:
            Processed strand dictionary
        """
        try:
            strand_kind = strand.get('kind', 'unknown')
            strand_id = strand.get('id', 'unknown')
            
            self.logger.info(f"Processing strand event: {strand_id} - {strand_kind}")
            
            # CRITICAL: Handle position_closed strands for learning system
            if strand_kind == 'position_closed':
                self.logger.info(f"Detected position_closed strand - processing for coefficient updates")
                await self._process_position_closed_strand(strand)
                self.logger.info(f"Successfully processed position_closed strand: {strand_id}")
                return strand
            
            # Legacy scoring system removed - no longer updating persistence/novelty/surprise scores
            # (These columns don't exist in the current schema)
            
            # Check if this strand should trigger the Decision Maker
            self.logger.debug("Checking if should trigger Decision Maker")
            should_trigger = self._should_trigger_decision_maker(strand)
            self.logger.debug(f"Should trigger Decision Maker: {should_trigger}")
            if should_trigger:
                self.logger.info("Triggering Decision Maker")
                await self._trigger_decision_maker(strand)
                self.logger.info("Decision Maker completed - strand processed")
            
            # Check if this strand should trigger the Trader
            self.logger.debug("Checking if should trigger Trader")
            should_trigger_trader = self._should_trigger_trader(strand)
            self.logger.debug(f"Should trigger Trader: {should_trigger_trader}")
            if should_trigger_trader:
                self.logger.info("Triggering Trader")
                await self._trigger_trader(strand)
                self.logger.info("Trader completed - strand processed")
            
            # Legacy braid candidate check removed - not used by lowcap system
            
            self.logger.info(f"Successfully processed strand event: {strand_id}")
            return strand
            
        except Exception as e:
            self.logger.error(f"Error processing strand event: {e}", exc_info=True)
            return strand
    
    def _should_trigger_decision_maker(self, strand: Dict[str, Any]) -> bool:
        """Check if strand should trigger the Decision Maker"""
        # Trigger if it's a social signal with dm_candidate tag
        return (
            strand.get('kind') == 'social_lowcap' and 
            'dm_candidate' in strand.get('tags', []) and
            strand.get('target_agent') == 'decision_maker_lowcap'
        )
    
    def _should_trigger_trader(self, strand: Dict[str, Any]) -> bool:
        """Check if strand should trigger the Trader"""
        # Trigger if it's a decision_lowcap strand with approval action
        # OR if it's a gem_bot_conservative strand (auto-approved)
        kind = strand.get('kind')
        content = strand.get('content') or {}
        action = content.get('action')
        tags = strand.get('tags', [])
        
        self.logger.debug(f"Trader trigger check: kind={kind}, action={action}, tags={tags}")
        
        # Standard decision_lowcap approval
        decision_approval = (
            kind == 'decision_lowcap' and
            action == 'approve' and
            'approved' in tags
        )
        
        # Gem Bot columns (auto-approved)
        gem_bot_auto = (
            kind in ['gem_bot_conservative', 'gem_bot_risky_test'] and
            'auto_approved' in tags
        )
        
        should_trigger = decision_approval or gem_bot_auto
        
        self.logger.debug(f"Trader trigger result: {should_trigger} (decision_approval={decision_approval}, gem_bot_auto={gem_bot_auto})")
        return should_trigger
    
    async def _trigger_decision_maker(self, strand: Dict[str, Any]) -> None:
        """Trigger the Decision Maker with the strand"""
        try:
            parent_id_short = (strand.get('id', '')[:8] + '…') if strand.get('id') else 'unknown'
            self.logger.info(f"Triggering Decision Maker for social strand {parent_id_short}")
            
            # Import here to avoid circular imports
            from intelligence.decision_maker_lowcap.decision_maker_lowcap_simple import DecisionMakerLowcapSimple
            self.logger.debug("Decision Maker: Import successful")
            
            # Check if decision maker is available
            if not self.decision_maker:
                self.logger.warning("Decision Maker: Not available - skipping strand processing")
                return
            
            # Process the strand with decision maker
            self.logger.debug(f"Decision Maker: Processing strand {strand.get('id', 'unknown')}")
            self.logger.info(f"Triggering Decision Maker for strand: {strand.get('id', 'unknown')}")
            result = await self.decision_maker.make_decision(strand)
            if result:
                child_id_short = (result.get('id', '')[:8] + '…') if result.get('id') else 'unknown'
                self.logger.info(f"Decision created: Strand {child_id_short} (from {parent_id_short}) → action: {result.get('content', {}).get('action')}")
            else:
                self.logger.info(f"No decision created (rejected) for strand {parent_id_short}")
            
        except Exception as e:
            self.logger.error(f"Decision Maker: ERROR - {e}", exc_info=True)
            self.logger.error(f"Error triggering Decision Maker: {e}")
            import traceback
            traceback.print_exc()
    
    async def _trigger_trader(self, strand: Dict[str, Any]) -> None:
        """Trigger the Trader with the decision strand"""
        self.logger.debug("Trader: Disabled in simplified PM stack – skipping strand.")
        self.logger.info(
            "Trader trigger skipped for strand %s (legacy trader inactive)",
            strand.get('id'),
        )
        return
    
    async def _process_position_closed_strand(self, strand: Dict[str, Any]) -> None:
        """
        Process a position_closed strand to update learning coefficients.
        
        This is the critical feedback loop: when a position closes, we extract
        the completed trade data and entry context, then update coefficients
        for all matching levers and interaction patterns.
        
        Args:
            strand: position_closed strand dictionary with completed_trades and entry_context
        """
        try:
            self.logger.info(f"Processing position_closed strand for learning updates")
            
            # Extract data from strand (entry_context and completed_trades are now in content JSONB)
            content = strand.get('content', {})
            entry_context = content.get('entry_context', {})
            completed_trades = content.get('completed_trades', [])
            timeframe = strand.get('timeframe', '1h')
            
            if not completed_trades:
                self.logger.warning(f"No completed_trades found in position_closed strand")
                return
            
            # Get the most recent completed trade (last one in array)
            completed_trade = completed_trades[-1] if isinstance(completed_trades, list) else completed_trades
            
            # Extract R/R metrics - handle both flat structure and nested structure (summary.rr)
            if isinstance(completed_trade, dict):
                # Check if rr is directly in completed_trade or in summary
                rr = completed_trade.get('rr')
                if rr is None and 'summary' in completed_trade:
                    summary = completed_trade.get('summary', {})
                    rr = summary.get('rr')
                # Also check trade_summary in content as fallback
                if rr is None:
                    trade_summary = content.get('trade_summary', {})
                    rr = trade_summary.get('rr')
            else:
                rr = None
            
            if rr is None:
                self.logger.warning(f"No R/R metric found in completed_trade, skipping coefficient update")
                return
            
            # Update coefficients from this closed trade
            await self._update_coefficients_from_closed_trade(
                entry_context=entry_context,
                completed_trade=completed_trade,
                timeframe=timeframe
            )
            
            # Process pattern scope aggregation (real-time learning)
            try:
                rows_updated = await process_position_closed_strand(
                    sb_client=self.supabase_manager.client,
                    strand=strand
                )
                self.logger.info(
                    "Successfully processed position_closed strand for pattern scope "
                    f"aggregation ({rows_updated} rows updated)"
                )
            except Exception as e:
                self.logger.error(f"Error processing pattern scope aggregation: {e}")
                # Don't fail the whole process if aggregation fails
            
            # Process LLM Learning Layer (semantic and structural intelligence)
            try:
                # Extract token data and curator message from strand if available
                token_data = strand.get('token_data', {})
                curator_message = strand.get('curator_message', '')
                
                await self.llm_research_layer.process(
                    position_closed_strand=strand,
                    token_data=token_data,
                    curator_message=curator_message
                )
                self.logger.info(f"Successfully processed LLM learning layer")
            except Exception as e:
                self.logger.error(f"Error processing LLM learning layer: {e}")
                # Don't fail the whole process if LLM layer fails
            
            self.logger.info(f"Successfully updated coefficients from position_closed strand")
            
        except Exception as e:
            self.logger.error(f"Error processing position_closed strand: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def _update_coefficients_from_closed_trade(
        self,
        entry_context: Dict[str, Any],
        completed_trade: Dict[str, Any],
        timeframe: str
    ) -> None:
        """
        Update learning coefficients from a closed trade.
        
        This method:
        1. Updates timeframe weight using EWMA with temporal decay (stored in learning_configs)
        2. Updates global R/R baseline (needed for timeframe weight normalization)
        
        Only timeframe weights are updated - these control DM allocation split across timeframes.
        
        Args:
            entry_context: Lever values at entry (not used for updates, but kept for compatibility)
            completed_trade: Trade summary with R/R metrics
            timeframe: Timeframe for this trade (1m, 15m, 1h, 4h)
        """
        try:
            # Handle both flat structure and nested structure (summary.rr)
            rr = completed_trade.get('rr')
            if rr is None and isinstance(completed_trade, dict) and 'summary' in completed_trade:
                summary = completed_trade.get('summary', {})
                rr = summary.get('rr')
            
            if rr is None:
                return
            
            # Get trade timestamp - check both locations
            exit_timestamp_str = completed_trade.get('exit_timestamp')
            if not exit_timestamp_str and isinstance(completed_trade, dict) and 'summary' in completed_trade:
                summary = completed_trade.get('summary', {})
                exit_timestamp_str = summary.get('exit_timestamp')
            if exit_timestamp_str:
                try:
                    trade_timestamp = datetime.fromisoformat(exit_timestamp_str.replace('Z', '+00:00'))
                except:
                    trade_timestamp = datetime.now(timezone.utc)
            else:
                trade_timestamp = datetime.now(timezone.utc)
            
            self.logger.info(f"Updating timeframe weight for R/R={rr:.3f}, timeframe={timeframe}, trade_timestamp={trade_timestamp.isoformat()}")
            
            # Update timeframe weight (only coefficient we actually use - stored in learning_configs)
            if timeframe:
                self.coefficient_updater.update_coefficient_ewma(
                    module='dm',
                    scope='lever',
                    name='timeframe',
                    key=timeframe,
                    rr_value=rr,
                    trade_timestamp=trade_timestamp
                )
                self.logger.info(f"Updated timeframe weight for {timeframe} (R/R={rr:.3f})")
            else:
                self.logger.warning(f"No timeframe provided for coefficient update")
                    
            # Update global R/R baseline using EWMA (needed for timeframe weight normalization)
            await self._update_global_rr_baseline_ewma(rr, trade_timestamp)
            
            self.logger.info(f"Updated timeframe coefficient and global R/R baseline from closed trade")
            
        except Exception as e:
            self.logger.error(f"Error updating coefficients from closed trade: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def _update_global_rr_baseline_ewma(self, rr_value: float, trade_timestamp: datetime) -> None:
        """
        Update global R/R baseline in learning_configs table using EWMA.
        
        Args:
            rr_value: R/R value from closed trade
            trade_timestamp: Timestamp of the closed trade
        """
        try:
            sb = self.supabase_manager.client
            current_timestamp = datetime.now(timezone.utc)
            
            # Get existing global R/R config
            existing = (
                sb.table("learning_configs")
                .select("config_data")
                .eq("module_id", "decision_maker")
                .limit(1)
                .execute()
            ).data
            
            if existing and len(existing) > 0:
                # Update existing config using EWMA
                config_data = existing[0].get('config_data', {})
                global_rr = config_data.get('global_rr', {})
                
                current_rr_short = global_rr.get('rr_short', 1.0)
                current_rr_long = global_rr.get('rr_long', 1.0)
                current_n = global_rr.get('n', 0)
                
                # Calculate decay weights
                w_short = self.coefficient_updater.calculate_decay_weight(trade_timestamp, current_timestamp, self.coefficient_updater.TAU_SHORT)
                w_long = self.coefficient_updater.calculate_decay_weight(trade_timestamp, current_timestamp, self.coefficient_updater.TAU_LONG)
                
                # EWMA update
                alpha_short = w_short / (w_short + 1.0)
                alpha_long = w_long / (w_long + 1.0)
                
                new_rr_short = (1 - alpha_short) * current_rr_short + alpha_short * rr_value
                new_rr_long = (1 - alpha_long) * current_rr_long + alpha_long * rr_value
                new_n = current_n + 1
                
                # Update config
                config_data['global_rr'] = {
                    'rr_short': new_rr_short,
                    'rr_long': new_rr_long,
                    'n': new_n,
                    'updated_at': current_timestamp.isoformat()
                }
                
                sb.table("learning_configs").update({
                    "config_data": config_data,
                    "updated_at": current_timestamp.isoformat(),
                    "updated_by": "learning_system"
                }).eq("module_id", "decision_maker").execute()
                
                self.logger.debug(f"Updated global R/R baseline (EWMA): rr_short={new_rr_short:.3f}, rr_long={new_rr_long:.3f}, n={new_n}")
            else:
                # Create new config
                config_data = {
                    'global_rr': {
                        'rr_short': rr_value,
                        'rr_long': rr_value,
                        'n': 1,
                        'updated_at': current_timestamp.isoformat()
                    }
                }
                
                sb.table("learning_configs").insert({
                    "module_id": "decision_maker",
                    "config_data": config_data,
                    "updated_at": current_timestamp.isoformat(),
                    "updated_by": "learning_system"
                }).execute()
                
                self.logger.debug(f"Created new global R/R baseline: rr_short={rr_value:.3f}, n=1")
                
        except Exception as e:
            self.logger.error(f"Error updating global R/R baseline: {e}")
    
    async def _get_global_rr_short(self) -> Optional[float]:
        """
        Get global R/R short-term baseline from learning_configs.
        
        Returns:
            Global R/R short-term value, or None if not found
        """
        try:
            sb = self.supabase_manager.client
            
            result = (
                sb.table("learning_configs")
                .select("config_data")
                .eq("module_id", "decision_maker")
                .limit(1)
                .execute()
            ).data
            
            if result and len(result) > 0:
                config_data = result[0].get('config_data', {})
                global_rr = config_data.get('global_rr', {})
                return global_rr.get('rr_short')
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting global R/R baseline: {e}")
            return None
    
    # Legacy braid candidate methods removed - not used by lowcap system
    # The lowcap system uses learning_braids table directly, not braid_candidate flags
