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
from llm_integration.prompt_manager import PromptManager
from llm_integration.openrouter_client import OpenRouterClient

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
        
        # Learning configuration
        self.promotion_thresholds = {
            'min_strands': 5,
            'min_avg_persistence': 0.6,
            'min_avg_novelty': 0.5,
            'min_avg_surprise': 0.4
        }
    
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
            print(f"🧠 Universal Learning System: Processing strand {strand.get('id', 'unknown')} - {strand.get('kind', 'unknown')}")
            self.logger.info(f"Processing strand event: {strand.get('id', 'unknown')} - {strand.get('kind', 'unknown')}")
            
            # Calculate scores for the strand
            print(f"🧠 Calculating scores for strand...")
            self.scoring.update_strand_scores(strand)
            
            # Update strand in database with scores
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
            
            # Check if this strand is a braid candidate
            if self._is_braid_candidate(strand):
                await self._mark_as_braid_candidate(strand)
            
            self.logger.info(f"Successfully processed strand event: {strand.get('id', 'unknown')}")
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
            
            # Initialize decision maker if not already done
            if not hasattr(self, 'decision_maker'):
                print(f"🧠 Decision Maker: Initializing Decision Maker...")
                # Use default config since learning system doesn't have trading config
                default_config = {
                    'max_exposure_pct': 100.0,
                    'max_positions': 30,
                    'min_curator_score': 0.6,
                    'min_confidence': 0.5,
                    'min_allocation_pct': 1.0,
                    'max_allocation_pct': 5.0,
                    'default_allocation_pct': 2.0
                }
                self.decision_maker = DecisionMakerLowcapSimple(
                    self.supabase_manager, 
                    default_config
                )
                # Pass learning system to decision maker for callbacks
                self.decision_maker.learning_system = self
                print(f"🧠 Decision Maker: Initialized successfully")
            
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
    
    def _is_braid_candidate(self, strand: Dict[str, Any]) -> bool:
        """Check if strand is a candidate for braid creation"""
        # Simple criteria: high confidence and persistence
        return (
            (strand.get('confidence') or 0) > 0.8 and
            (strand.get('persistence_score') or 0) > 0.7
        )
    
    async def _mark_as_braid_candidate(self, strand: Dict[str, Any]) -> None:
        """Mark strand as braid candidate in database"""
        try:
            self.supabase_manager.update_strand(
                strand['id'], 
                {'braid_candidate': True}
            )
            self.logger.info(f"Marked strand {strand.get('id', 'unknown')} as braid candidate")
        except Exception as e:
            self.logger.error(f"Error marking strand as braid candidate: {e}")
    
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
