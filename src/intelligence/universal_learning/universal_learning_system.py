"""
Universal Learning System

This module provides the core universal learning system that works with all strand types.
It integrates universal scoring and clustering to create a unified learning pipeline.

The system implements:
1. Universal scoring for all strands
2. Two-tier clustering (column + pattern)
3. Threshold-based promotion to braids
4. Integration with existing learning system

This is the foundation that CIL specialized learning builds upon.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone

from .universal_scoring import UniversalScoring
from .universal_clustering import UniversalClustering, Cluster
from .coefficient_updater import CoefficientUpdater
from .bucket_vocabulary import BucketVocabulary
from llm_integration.prompt_manager import PromptManager
from llm_integration.openrouter_client import OpenRouterClient
from intelligence.lowcap_portfolio_manager.pm.braiding_system import process_position_closed_for_braiding
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
        self.scoring = UniversalScoring(supabase_manager)
        self.clustering = UniversalClustering()
        self.coefficient_updater = CoefficientUpdater(supabase_manager.client)
        self.bucket_vocab = BucketVocabulary()
        
        # Initialize LLM Learning Layer (build from day 1, phased enablement)
        self.llm_research_layer = LLMResearchLayer(
            sb_client=supabase_manager.client,
            llm_client=llm_client,
            enablement=None  # Uses defaults, can be updated later
        )
        
        # Learning configuration
        self.promotion_thresholds = {
            'min_strands': 5,
            'min_avg_persistence': 0.6,
            'min_avg_novelty': 0.5,
            'min_avg_surprise': 0.4
        }
    
    def set_decision_maker(self, decision_maker):
        """Set the decision maker instance to use"""
        self.decision_maker = decision_maker
    
    async def process_strands_into_braid(self, strands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a cluster of strands into a braid using the learning system
        
        This method integrates with the existing learning system to create braids.
        It takes strands directly (no conversion needed) and creates a braid.
        
        Args:
            strands: List of strand dictionaries to process into braid
            
        Returns:
            Braid strand dictionary
        """
        try:
            if not strands:
                return {}
            
            # Calculate scores for all strands if not already present
            for strand in strands:
                if 'persistence_score' not in strand:
                    self.scoring.update_strand_scores(strand)
            
            # Create braid from strands
            braid = await self._create_braid_from_strands(strands)
            
            self.logger.info(f"Created braid from {len(strands)} strands")
            return braid
            
        except Exception as e:
            self.logger.error(f"Error processing strands into braid: {e}")
            return {}
    
    async def cluster_and_promote_strands(self, strands: List[Dict[str, Any]], braid_level: int = 0) -> List[Dict[str, Any]]:
        """
        Complete clustering and promotion flow
        
        This is the main method that:
        1. Calculates scores for all strands
        2. Clusters strands using two-tier clustering
        3. Promotes qualifying clusters to braids
        
        Args:
            strands: List of strand dictionaries to process
            braid_level: Braid level to cluster (0=strand, 1=braid, 2=metabraid, etc.)
            
        Returns:
            List of created braids
        """
        try:
            if not strands:
                return []
            
            # Step 1: Calculate scores for all strands
            self.logger.info(f"Calculating scores for {len(strands)} strands")
            for strand in strands:
                self.scoring.update_strand_scores(strand)
            
            # Step 2: Cluster strands using two-tier clustering
            self.logger.info(f"Clustering {len(strands)} strands at braid level {braid_level}")
            clusters = self.clustering.cluster_strands(strands, braid_level)
            
            # Step 3: Check thresholds and promote to braids
            braids = []
            for cluster in clusters:
                if self.clustering.cluster_meets_threshold(cluster, self.promotion_thresholds):
                    self.logger.info(f"Cluster {cluster.cluster_key} meets threshold, promoting to braid")
                    braid = await self.process_strands_into_braid(cluster.strands)
                    if braid:
                        braids.append(braid)
                else:
                    self.logger.debug(f"Cluster {cluster.cluster_key} does not meet threshold")
            
            self.logger.info(f"Created {len(braids)} braids from {len(strands)} strands")
            return braids
            
        except Exception as e:
            self.logger.error(f"Error in cluster and promote strands: {e}")
            return []
    
    async def _create_braid_from_strands(self, strands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a braid strand from a cluster of strands
        
        Args:
            strands: List of strand dictionaries to create braid from
            
        Returns:
            Braid strand dictionary
        """
        try:
            if not strands:
                return {}
            
            # Calculate average scores
            avg_persistence = sum(s.get('persistence_score', 0.0) for s in strands) / len(strands)
            avg_novelty = sum(s.get('novelty_score', 0.0) for s in strands) / len(strands)
            avg_surprise = sum(s.get('surprise_rating', 0.0) for s in strands) / len(strands)
            
            # Generate braid ID
            braid_id = f"braid_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{len(strands)}"
            
            # Create braid strand
            braid = {
                'id': braid_id,
                'kind': 'braid',
                'braid_level': 1,  # Braids are level 1
                'source_strands': strands,
                'persistence_score': avg_persistence,
                'novelty_score': avg_novelty,
                'surprise_rating': avg_surprise,
                'created_at': datetime.now(timezone.utc),
                'agent_id': 'universal_learning_system',
                'module': 'alpha',
                'tags': {'learning': True, 'braid': True},
                'content': {
                    'type': 'braid',
                    'source_count': len(strands),
                    'avg_persistence': avg_persistence,
                    'avg_novelty': avg_novelty,
                    'avg_surprise': avg_surprise,
                    'created_from': 'universal_learning_system'
                }
            }
            
            # Determine braid type based on strand types
            braid_type = self._determine_braid_type(strands)
            
            # Generate LLM lesson using braiding prompts
            lesson = await self.braiding_prompts.generate_braid_lesson(strands, braid_type)
            braid['lesson'] = lesson
            braid['content']['lesson'] = lesson
            braid['content']['braid_type'] = braid_type
            
            return braid
            
        except Exception as e:
            self.logger.error(f"Error creating braid from strands: {e}")
            return {}
    
    def _determine_braid_type(self, strands: List[Dict[str, Any]]) -> str:
        """
        Determine braid type based on strand types
        
        Args:
            strands: List of strands to analyze
            
        Returns:
            Braid type string
        """
        try:
            if not strands:
                return 'universal_braid'
            
            # Get unique agent IDs
            agent_ids = set(s.get('agent_id', 'unknown') for s in strands)
            kinds = set(s.get('kind', 'unknown') for s in strands)
            
            # Determine type based on majority
            if len(agent_ids) == 1:
                agent_id = list(agent_ids)[0]
                if agent_id == 'raw_data_intelligence':
                    return 'raw_data_intelligence'
                elif agent_id == 'central_intelligence_layer':
                    return 'central_intelligence_layer'
                elif 'trading' in agent_id.lower():
                    return 'trading_plan'
            
            # Check for trading plans
            if 'trading_plan' in kinds:
                return 'trading_plan'
            
            # Mixed types
            if len(agent_ids) > 1 or len(kinds) > 1:
                return 'mixed_braid'
            
            # Default to universal
            return 'universal_braid'
            
        except Exception as e:
            self.logger.error(f"Error determining braid type: {e}")
            return 'universal_braid'
    
    
    async def save_braid_to_database(self, braid: Dict[str, Any]) -> bool:
        """
        Save braid to database
        
        Args:
            braid: Braid dictionary to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Save to AD_strands table
            result = self.supabase_manager.client.table('ad_strands').insert(braid).execute()
            
            if result.data:
                self.logger.info(f"Saved braid {braid['id']} to database")
                return True
            else:
                self.logger.error(f"Failed to save braid {braid['id']} to database")
                return False
                
        except Exception as e:
            self.logger.error(f"Error saving braid to database: {e}")
            return False
    
    async def process_strand_event(self, strand: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single strand event from social ingest or other modules
        
        This method is called when a new strand is created and needs to be processed
        by the learning system. It handles scoring, clustering, and triggering downstream modules.
        
        Args:
            strand: Strand dictionary to process
            
        Returns:
            Processed strand dictionary
        """
        try:
            strand_kind = strand.get('kind', 'unknown')
            strand_id = strand.get('id', 'unknown')
            
            print(f"🧠 Universal Learning System: Processing strand {strand_id} - {strand_kind}")
            self.logger.info(f"Processing strand event: {strand_id} - {strand_kind}")
            
            # CRITICAL: Handle position_closed strands for learning system
            if strand_kind == 'position_closed':
                print(f"🧠 Learning System: Detected position_closed strand - processing for coefficient updates")
                await self._process_position_closed_strand(strand)
                self.logger.info(f"Successfully processed position_closed strand: {strand_id}")
                return strand
            
            # Calculate scores for the strand (skip for position_closed - they don't need scoring)
            print(f"🧠 Calculating scores for strand...")
            self.scoring.update_strand_scores(strand)
            
            # Update strand in database with scores
            if strand.get('id'):
                self.supabase_manager.update_strand(
                    strand['id'], 
                    {
                        'persistence_score': strand.get('persistence_score', 0.0),
                        'novelty_score': strand.get('novelty_score', 0.0),
                        'surprise_rating': strand.get('surprise_rating', 0.0)
                    }
                )
            
            # Check if this strand should trigger the Decision Maker
            print(f"🧠 Checking if should trigger Decision Maker...")
            should_trigger = self._should_trigger_decision_maker(strand)
            print(f"🧠 Should trigger Decision Maker: {should_trigger}")
            if should_trigger:
                print(f"🧠 Triggering Decision Maker...")
                await self._trigger_decision_maker(strand)
                print(f"🧠 Decision Maker completed - strand processed")
            
            # Check if this strand should trigger the Trader
            print(f"🧠 Checking if should trigger Trader...")
            should_trigger_trader = self._should_trigger_trader(strand)
            print(f"🧠 Should trigger Trader: {should_trigger_trader}")
            if should_trigger_trader:
                print(f"🧠 Triggering Trader...")
                await self._trigger_trader(strand)
                print(f"🧠 Trader completed - strand processed")
            
            # Legacy braid candidate check removed - not used by lowcap system
            
            self.logger.info(f"Successfully processed strand event: {strand_id}")
            return strand
            
        except Exception as e:
            self.logger.error(f"Error processing strand event: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            print(f"❌ Error processing strand event: {e}")
            print(f"❌ Traceback: {traceback.format_exc()}")
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
        
        print(f"🧠 Trader trigger check: kind={kind}, action={action}, tags={tags}")
        
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
        
        print(f"🧠 Trader trigger result: {should_trigger} (decision_approval={decision_approval}, gem_bot_auto={gem_bot_auto})")
        return should_trigger
    
    async def _trigger_decision_maker(self, strand: Dict[str, Any]) -> None:
        """Trigger the Decision Maker with the strand"""
        try:
            parent_id_short = (strand.get('id', '')[:8] + '…') if strand.get('id') else 'unknown'
            print(f"decision | Triggering for social strand {parent_id_short}")
            
            # Import here to avoid circular imports
            from intelligence.decision_maker_lowcap.decision_maker_lowcap_simple import DecisionMakerLowcapSimple
            print(f"🧠 Decision Maker: Import successful")
            
            # Check if decision maker is available
            if not self.decision_maker:
                print(f"🧠 Decision Maker: Not available - skipping strand processing")
                return
            
            # Process the strand with decision maker
            print(f"🧠 Decision Maker: Processing strand {strand.get('id', 'unknown')}")
            self.logger.info(f"Triggering Decision Maker for strand: {strand.get('id', 'unknown')}")
            result = await self.decision_maker.make_decision(strand)
            if result:
                child_id_short = (result.get('id', '')[:8] + '…') if result.get('id') else 'unknown'
                print(f"decision | Strand {child_id_short} (from {parent_id_short}) → action: {result.get('content', {}).get('action')}")
            else:
                print(f"decision | No decision created (rejected)")
            
        except Exception as e:
            print(f"🧠 Decision Maker: ERROR - {e}")
            self.logger.error(f"Error triggering Decision Maker: {e}")
            import traceback
            traceback.print_exc()
    
    async def _trigger_trader(self, strand: Dict[str, Any]) -> None:
        """Trigger the Trader with the decision strand"""
        try:
            dec_id_short = (strand.get('id', '')[:8] + '…') if strand.get('id') else 'unknown'
            print(f"trader | Triggered by decision {dec_id_short}")
            
            # Use shared trader instance if available, otherwise initialize
            if not hasattr(self, 'trader') or self.trader is None:
                # Import lazily and select V2 when enabled to avoid importing legacy V1
                # Use V2 trader (improved Base trading and modular design)
                from intelligence.trader_lowcap.trader_lowcap_simple_v2 import TraderLowcapSimpleV2 as TraderClass
                print(f"🧠 Trader: Import successful")
                print(f"🧠 Trader: No shared trader found, initializing new one...")
                try:
                    # Use default config for trader
                    trader_config = {
                        'book_id': 'social',
                        'book_nav': 100000.0,
                        'max_position_size_pct': 2.0,
                        'entry_strategy': 'three_entry',
                        'exit_strategy': 'staged_exit'
                    }
                    self.trader = TraderClass(
                        self.supabase_manager, 
                        trader_config
                    )
                    
                    # Initialize Jupiter client for trader
                    from trading.jupiter_client import JupiterClient
                    self.trader.jupiter_client = JupiterClient()
                    
                    print(f"🧠 Trader: Initialized successfully")
                except Exception as e:
                    print(f"🧠 Trader: ERROR during initialization: {e}")
                    import traceback
                    traceback.print_exc()
                    return
            else:
                print(f"🧠 Trader: Using shared trader instance")
            
            # Process the strand with trader based on type
            strand_kind = strand.get('kind')
            print(f"🧠 Trader: Processing {strand_kind} strand {strand.get('id', 'unknown')}")
            self.logger.info(f"Triggering Trader for {strand_kind} strand: {strand.get('id', 'unknown')}")
            
            # Route to appropriate trader method based on strand type
            if strand_kind in ['gem_bot_conservative', 'gem_bot_risky_test']:
                print(f"🧠 Trader: Gem Bot disabled - skipping {strand_kind} strand")
                result = "DISABLED"
                # GEM BOT DISABLED - Commented out for safety
                # print(f"🧠 Trader: Calling execute_gem_bot_strand for {strand_kind}")
                # try:
                #     result = await self.trader.execute_gem_bot_strand(strand)
                #     print(f"🧠 Trader: execute_gem_bot_strand result: {result}")
                # except Exception as e:
                #     print(f"🧠 Trader: ERROR in execute_gem_bot_strand: {e}")
                #     import traceback
                #     traceback.print_exc()
                #     result = None
            else:
                # Default to decision execution for decision_lowcap strands
                print(f"🧠 Trader: Calling execute_decision for {strand_kind}")
                result = await self.trader.execute_decision(strand)
            if result:
                # One-line summary with native unit price (SOL/ETH)
                chain = (strand.get('signal_pack', {}).get('token', {}) or {}).get('chain')
                unit = 'SOL' if chain == 'solana' else ('BNB' if chain == 'bsc' else 'ETH')
                alloc_native = result.get('allocation_native')
                price_val = result.get('current_price')
                alloc_str = f"{alloc_native:.6f}" if isinstance(alloc_native, (int, float)) else str(alloc_native)
                price_str = f"{price_val:.6f}" if isinstance(price_val, (int, float)) else "n/a"
                print(f"trader | TRADE OK: buy {result.get('token_ticker')} on {chain} @ {strand.get('signal_pack', {}).get('venue', {}).get('dex')} | qty {alloc_str} native | price {price_str} {unit} | alloc {result.get('allocation_pct')}% | position_id {result.get('position_id')}")
            else:
                print(f"trader | NOOP: trade not executed")
            
        except Exception as e:
            print(f"🧠 Trader: ERROR - {e}")
            self.logger.error(f"Error triggering Trader: {e}")
            import traceback
            traceback.print_exc()
    
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
            
            # Extract R/R metrics
            rr = completed_trade.get('rr')
            if rr is None:
                self.logger.warning(f"No R/R metric found in completed_trade, skipping coefficient update")
                return
            
            # Update coefficients from this closed trade
            await self._update_coefficients_from_closed_trade(
                entry_context=entry_context,
                completed_trade=completed_trade,
                timeframe=timeframe
            )
            
            # Process braiding system (pattern discovery)
            try:
                await process_position_closed_for_braiding(
                    sb_client=self.supabase_manager.client,
                    strand=strand
                )
                self.logger.info(f"Successfully processed position_closed strand for braiding")
                
                # Build lessons from braids after every closed trade (keeps lessons fresh)
                try:
                    from src.intelligence.lowcap_portfolio_manager.pm.braiding_system import build_lessons_from_braids
                    lessons_created = await build_lessons_from_braids(
                        sb_client=self.supabase_manager.client,
                        module='pm',
                        n_min=10,
                        edge_min=0.5,
                        incremental_min=0.1,
                        max_lessons_per_family=3
                    )
                    self.logger.info(f"Built {lessons_created} PM lessons from braids")
                    
                    # Also build DM lessons if we have DM data
                    if entry_context.get('curator'):
                        lessons_created_dm = await build_lessons_from_braids(
                            sb_client=self.supabase_manager.client,
                            module='dm',
                            n_min=10,
                            edge_min=0.5,
                            incremental_min=0.1,
                            max_lessons_per_family=3
                        )
                        self.logger.info(f"Built {lessons_created_dm} DM lessons from braids")
                except Exception as e:
                    self.logger.warning(f"Error building lessons from braids: {e}")
                    # Don't fail the whole process if lesson building fails
            except Exception as e:
                self.logger.error(f"Error processing braiding system: {e}")
                # Don't fail the whole process if braiding fails
            
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
        Update learning coefficients from a closed trade (Phase 2: EWMA + Interaction Patterns).
        
        This method:
        1. Normalizes bucket values using BucketVocabulary
        2. Updates single-factor coefficients using EWMA with temporal decay
        3. Updates interaction patterns
        4. Applies importance bleed to avoid double-counting
        5. Updates global R/R baseline
        
        Args:
            entry_context: Lever values at entry (curator, chain, mcap_bucket, vol_bucket, etc.)
            completed_trade: Trade summary with R/R metrics
            timeframe: Timeframe for this trade (1m, 15m, 1h, 4h)
        """
        try:
            rr = completed_trade.get('rr')
            if rr is None:
                return
            
            # Get trade timestamp
            exit_timestamp_str = completed_trade.get('exit_timestamp')
            if exit_timestamp_str:
                try:
                    trade_timestamp = datetime.fromisoformat(exit_timestamp_str.replace('Z', '+00:00'))
                except:
                    trade_timestamp = datetime.now(timezone.utc)
            else:
                trade_timestamp = datetime.now(timezone.utc)
            
            self.logger.info(f"Updating coefficients for R/R={rr:.3f}, timeframe={timeframe}, trade_timestamp={trade_timestamp.isoformat()}")
            
            # Normalize bucket values using BucketVocabulary
            normalized_context = entry_context.copy()
            if entry_context.get('mcap_bucket'):
                normalized_context['mcap_bucket'] = self.bucket_vocab.normalize_bucket('mcap', entry_context['mcap_bucket'])
            if entry_context.get('vol_bucket'):
                normalized_context['vol_bucket'] = self.bucket_vocab.normalize_bucket('vol', entry_context['vol_bucket'])
            if entry_context.get('age_bucket'):
                normalized_context['age_bucket'] = self.bucket_vocab.normalize_bucket('age', entry_context['age_bucket'])
            if entry_context.get('mcap_vol_ratio_bucket'):
                normalized_context['mcap_vol_ratio_bucket'] = self.bucket_vocab.normalize_bucket('mcap_vol_ratio', entry_context['mcap_vol_ratio_bucket'])
            
            # Extract lever values from normalized entry_context
            curator = normalized_context.get('curator')
            chain = normalized_context.get('chain')
            mcap_bucket = normalized_context.get('mcap_bucket')
            vol_bucket = normalized_context.get('vol_bucket')
            age_bucket = normalized_context.get('age_bucket')
            intent = normalized_context.get('intent')
            mapping_confidence = normalized_context.get('mapping_confidence')
            mcap_vol_ratio_bucket = normalized_context.get('mcap_vol_ratio_bucket')
            
            # Update single-factor coefficients using EWMA
            levers_to_update = []
            
            if curator:
                levers_to_update.append(('curator', curator))
            if chain:
                levers_to_update.append(('chain', chain))
            if mcap_bucket:
                levers_to_update.append(('cap', mcap_bucket))
            if vol_bucket:
                levers_to_update.append(('vol', vol_bucket))
            if age_bucket:
                levers_to_update.append(('age', age_bucket))
            if intent:
                levers_to_update.append(('intent', intent))
            if mapping_confidence:
                levers_to_update.append(('mapping_confidence', mapping_confidence))
            if mcap_vol_ratio_bucket:
                levers_to_update.append(('mcap_vol_ratio', mcap_vol_ratio_bucket))
            
            # Update timeframe coefficient
            if timeframe:
                levers_to_update.append(('timeframe', timeframe))
            
            # Update each lever coefficient using EWMA
            for lever_name, lever_key in levers_to_update:
                self.coefficient_updater.update_coefficient_ewma(
                    module='dm',
                    scope='lever',
                    name=lever_name,
                    key=lever_key,
                    rr_value=rr,
                    trade_timestamp=trade_timestamp
                )
            
            # Update interaction pattern
            interaction_result = self.coefficient_updater.update_interaction_pattern(
                entry_context=normalized_context,
                rr_value=rr,
                trade_timestamp=trade_timestamp
            )
            
            # Apply importance bleed if interaction pattern exists and is significant
            if interaction_result:
                interaction_weight = interaction_result.get('weight', 1.0)
                if abs(interaction_weight - 1.0) >= 0.1:  # Only apply if interaction is significant
                    adjusted_weights = self.coefficient_updater.apply_importance_bleed(
                        entry_context=normalized_context,
                        interaction_weight=interaction_weight
                    )
                    
                    # Update single-factor weights with bleed applied
                    for lever_name, (lever_key, adjusted_weight) in adjusted_weights.items():
                        # Update the weight in the database
                        self.supabase_manager.client.table("learning_coefficients").update({
                            "weight": adjusted_weight,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }).eq("module", "dm").eq("scope", "lever").eq("name", lever_name).eq("key", lever_key).execute()
                        
                        self.logger.debug(f"Applied importance bleed to {lever_name}.{lever_key}: weight adjusted to {adjusted_weight:.3f}")
            
            # Update global R/R baseline using EWMA
            await self._update_global_rr_baseline_ewma(rr, trade_timestamp)
            
            self.logger.info(f"Updated {len(levers_to_update)} single-factor coefficient(s) and interaction pattern from closed trade")
            
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
    
    async def process_strands_batch(self, strands: List[Dict[str, Any]], save_to_db: bool = True) -> Dict[str, Any]:
        """
        Process a batch of strands through the complete learning pipeline
        
        Args:
            strands: List of strand dictionaries to process
            save_to_db: Whether to save created braids to database
            
        Returns:
            Dictionary with processing results
        """
        try:
            results = {
                'input_strands': len(strands),
                'created_braids': [],
                'errors': []
            }
            
            # Process strands at different braid levels
            for braid_level in [0, 1, 2]:  # strands, braids, metabraids
                self.logger.info(f"Processing braid level {braid_level}")
                
                # Filter strands for this braid level
                level_strands = [s for s in strands if s.get('braid_level', 0) == braid_level]
                
                if not level_strands:
                    continue
                
                # Cluster and promote
                braids = await self.cluster_and_promote_strands(level_strands, braid_level)
                
                # Save to database if requested
                if save_to_db:
                    for braid in braids:
                        success = await self.save_braid_to_database(braid)
                        if success:
                            results['created_braids'].append(braid)
                        else:
                            results['errors'].append(f"Failed to save braid {braid.get('id', 'unknown')}")
                else:
                    results['created_braids'].extend(braids)
            
            self.logger.info(f"Batch processing complete: {len(results['created_braids'])} braids created")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in batch processing: {e}")
            results['errors'].append(str(e))
            return results


# Example usage and testing
if __name__ == "__main__":
    # Test the universal learning system
    from utils.supabase_manager import SupabaseManager
    
    # Initialize components
    supabase_manager = SupabaseManager()
    learning_system = UniversalLearningSystem(supabase_manager)
    
    # Test strands
    test_strands = [
        {
            'id': 'strand_1',
            'kind': 'signal',
            'agent_id': 'raw_data_intelligence',
            'timeframe': '1h',
            'regime': 'bull',
            'pattern_type': 'divergence',
            'braid_level': 0,
            'sig_confidence': 0.8,
            'sig_sigma': 0.7
        },
        {
            'id': 'strand_2',
            'kind': 'signal',
            'agent_id': 'raw_data_intelligence',
            'timeframe': '1h',
            'regime': 'bull',
            'pattern_type': 'divergence',
            'braid_level': 0,
            'sig_confidence': 0.7,
            'sig_sigma': 0.6
        }
    ]
    
    # Test processing
    import asyncio
    
    async def test_learning():
        results = await learning_system.process_strands_batch(test_strands, save_to_db=False)
        print(f"Processing results: {results}")
    
    asyncio.run(test_learning())
