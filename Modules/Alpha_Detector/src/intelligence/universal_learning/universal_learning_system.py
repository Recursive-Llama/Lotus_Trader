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

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'Modules', 'Alpha_Detector', 'src'))
from intelligence.universal_learning.universal_scoring import UniversalScoring
from intelligence.universal_learning.universal_clustering import UniversalClustering, Cluster
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'Modules', 'Alpha_Detector', 'src'))
from intelligence.llm_integration.braiding_prompts import BraidingPrompts
from intelligence.llm_integration.llm_client import LLMClientManager

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
            self.llm_manager = LLMClientManager(llm_config)
            self.braiding_prompts = BraidingPrompts(self.llm_manager)
        elif llm_client:
            self.llm_manager = llm_client
            self.braiding_prompts = BraidingPrompts(llm_client)
        else:
            self.llm_manager = None
            self.braiding_prompts = BraidingPrompts()
        
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
    from src.utils.supabase_manager import SupabaseManager
    
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
