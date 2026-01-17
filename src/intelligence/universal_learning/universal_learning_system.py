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
# Note: pattern_scope_aggregator removed (deprecated - moved to _deprecated/)
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
            
            # Learning System v2: Extract ROI (rpnl_pct) instead of R/R
            if isinstance(completed_trade, dict):
                # Prefer rpnl_pct (Learning System v2), fallback to rr for legacy
                roi = completed_trade.get('rpnl_pct')
                if roi is None:
                    roi = completed_trade.get('total_pnl_pct')  # Alternative key
                if roi is None and 'summary' in completed_trade:
                    summary = completed_trade.get('summary', {})
                    roi = summary.get('rpnl_pct') or summary.get('rr')  # Legacy fallback
                # Also check trade_summary in content as fallback
                if roi is None:
                    trade_summary = content.get('trade_summary', {})
                    roi = trade_summary.get('rpnl_pct') or trade_summary.get('rr')
            else:
                roi = None
            
            if roi is None:
                self.logger.warning(f"No ROI metric found in completed_trade, skipping coefficient update")
                return
            
            # Update coefficients from this closed trade
            await self._update_coefficients_from_closed_trade(
                entry_context=entry_context,
                completed_trade=completed_trade,
                timeframe=timeframe
            )
            
            # Note: Pattern scope aggregation removed (deprecated)
            # The old pattern_trade_events table is no longer used
            
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
        2. Updates global ROI baseline (needed for timeframe weight normalization)
        
        Learning System v2: Uses ROI (rpnl_pct) instead of R/R.
        Only timeframe weights are updated - these control DM allocation split across timeframes.
        
        Args:
            entry_context: Lever values at entry (not used for updates, but kept for compatibility)
            completed_trade: Trade summary with ROI metrics
            timeframe: Timeframe for this trade (15m, 1h, 4h) - 1m removed in v2
        """
        try:
            # Learning System v2: Use ROI instead of R/R
            roi = completed_trade.get('rpnl_pct') or completed_trade.get('total_pnl_pct')
            if roi is None and isinstance(completed_trade, dict) and 'summary' in completed_trade:
                summary = completed_trade.get('summary', {})
                roi = summary.get('rpnl_pct') or summary.get('rr')  # Legacy fallback
            
            if roi is None:
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
            
            self.logger.info(f"Updating timeframe weight for ROI={roi:.3f}%, timeframe={timeframe}, trade_timestamp={trade_timestamp.isoformat()}")
            
            # Learning System v2: Skip 1m timeframe (removed from allocation)
            if timeframe == '1m':
                self.logger.debug(f"Skipping 1m timeframe (removed in v2)")
                return
            
            # Update timeframe weight (only coefficient we actually use - stored in learning_configs)
            if timeframe:
                self.coefficient_updater.update_coefficient_ewma(
                    module='dm',
                    scope='lever',
                    name='timeframe',
                    key=timeframe,
                    rr_value=roi,  # Still using rr_value param name for backward compat
                    trade_timestamp=trade_timestamp
                )
                self.logger.info(f"Updated timeframe weight for {timeframe} (ROI={roi:.3f}%)")
            else:
                self.logger.warning(f"No timeframe provided for coefficient update")
                    
            # Update global ROI baseline using EWMA (needed for timeframe weight normalization)
            await self._update_global_roi_baseline_ewma(roi, trade_timestamp)
            
            self.logger.info(f"Updated timeframe coefficient and global ROI baseline from closed trade")
            
        except Exception as e:
            self.logger.error(f"Error updating coefficients from closed trade: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def _update_global_roi_baseline_ewma(self, roi_value: float, trade_timestamp: datetime) -> None:
        """
        Learning System v2: Update global ROI baseline in learning_configs table using EWMA.
        
        Args:
            roi_value: ROI value (rpnl_pct) from closed trade
            trade_timestamp: Timestamp of the closed trade
        """
        try:
            sb = self.supabase_manager.client
            current_timestamp = datetime.now(timezone.utc)
            
            # Get existing global ROI config
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
                global_roi = config_data.get('global_roi', config_data.get('global_rr', {}))  # Migrate from rr
                
                current_roi_short = global_roi.get('roi_short', global_roi.get('rr_short', 0.0))
                current_roi_long = global_roi.get('roi_long', global_roi.get('rr_long', 0.0))
                current_n = global_roi.get('n', 0)
                
                # Calculate decay weights
                w_short = self.coefficient_updater.calculate_decay_weight(trade_timestamp, current_timestamp, self.coefficient_updater.TAU_SHORT)
                w_long = self.coefficient_updater.calculate_decay_weight(trade_timestamp, current_timestamp, self.coefficient_updater.TAU_LONG)
                
                # EWMA update
                alpha_short = w_short / (w_short + 1.0)
                alpha_long = w_long / (w_long + 1.0)
                
                new_roi_short = (1 - alpha_short) * current_roi_short + alpha_short * roi_value
                new_roi_long = (1 - alpha_long) * current_roi_long + alpha_long * roi_value
                new_n = current_n + 1
                
                # Update config with new global_roi key (v2)
                config_data['global_roi'] = {
                    'roi_short': new_roi_short,
                    'roi_long': new_roi_long,
                    'n': new_n,
                    'updated_at': current_timestamp.isoformat()
                }
                
                sb.table("learning_configs").update({
                    "config_data": config_data,
                    "updated_at": current_timestamp.isoformat(),
                    "updated_by": "learning_system_v2"
                }).eq("module_id", "decision_maker").execute()
                
                self.logger.debug(f"Updated global ROI baseline (EWMA): roi_short={new_roi_short:.3f}%, roi_long={new_roi_long:.3f}%, n={new_n}")
            else:
                # Create new config
                config_data = {
                    'global_roi': {
                        'roi_short': roi_value,
                        'roi_long': roi_value,
                        'n': 1,
                        'updated_at': current_timestamp.isoformat()
                    }
                }
                
                sb.table("learning_configs").insert({
                    "module_id": "decision_maker",
                    "config_data": config_data,
                    "updated_at": current_timestamp.isoformat(),
                    "updated_by": "learning_system_v2"
                }).execute()
                
                self.logger.debug(f"Created new global ROI baseline: roi_short={roi_value:.3f}%, n=1")
                
        except Exception as e:
            self.logger.error(f"Error updating global ROI baseline: {e}")
    
    async def _get_global_roi_short(self) -> Optional[float]:
        """
        Learning System v2: Get global ROI short-term baseline from learning_configs.
        
        Returns:
            Global ROI short-term value (%), or None if not found
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
                # Try new key first, fallback to legacy
                global_roi = config_data.get('global_roi', config_data.get('global_rr', {}))
                return global_roi.get('roi_short', global_roi.get('rr_short'))
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting global ROI baseline: {e}")
            return None
    
    # Legacy braid candidate methods removed - not used by lowcap system
    # The lowcap system uses learning_braids table directly, not braid_candidate flags
