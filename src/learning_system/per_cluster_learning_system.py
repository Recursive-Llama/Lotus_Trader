"""
Per-Cluster Learning System

Handles learning analysis and braid creation for individual clusters of strands.
This system processes clusters through the learning pipeline to create intelligent braids.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


class PerClusterLearningSystem:
    """
    Per-Cluster Learning System
    
    Handles learning analysis and braid creation for individual clusters of strands.
    This system processes clusters through the learning pipeline to create intelligent braids.
    """
    
    def __init__(self, supabase_manager, llm_client=None):
        """
        Initialize per-cluster learning system
        
        Args:
            supabase_manager: Database manager for strand operations
            llm_client: LLM client for analysis and braid creation
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # Import universal learning system for actual learning logic
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'Modules', 'Alpha_Detector', 'src', 'intelligence', 'universal_learning'))
        from universal_learning_system import UniversalLearningSystem
        
        self.universal_learning = UniversalLearningSystem(supabase_manager, llm_client)
    
    async def process_cluster(
        self, 
        cluster_strands: List[Dict[str, Any]], 
        cluster_type: str,
        strand_type: str
    ) -> bool:
        """
        Process a cluster of strands through the learning system
        
        Args:
            cluster_strands: List of strands in the cluster
            cluster_type: Type of cluster (pattern_timeframe, method, etc.)
            strand_type: Type of strands (pattern, prediction_review, etc.)
            
        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            if not cluster_strands:
                self.logger.warning(f"Empty cluster for {strand_type}")
                return False
            
            self.logger.info(f"Processing cluster of {len(cluster_strands)} {strand_type} strands")
            
            # Process each strand through universal learning
            success_count = 0
            for strand in cluster_strands:
                try:
                    # Calculate resonance scores for the strand
                    await self._calculate_strand_resonance(strand)
                    
                    # Process through universal learning system
                    success = await self.universal_learning.process_strand(strand)
                    if success:
                        success_count += 1
                        
                except Exception as e:
                    self.logger.error(f"Error processing strand {strand.get('id')}: {e}")
                    continue
            
            success_rate = success_count / len(cluster_strands) if cluster_strands else 0
            self.logger.info(f"Processed {success_count}/{len(cluster_strands)} strands successfully ({success_rate:.2%})")
            
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Error processing cluster {cluster_type}: {e}")
            return False
    
    async def _calculate_strand_resonance(self, strand: Dict[str, Any]) -> None:
        """Calculate resonance scores for a strand"""
        try:
            # Import module-specific scoring
            from module_specific_scoring import ModuleSpecificScoring
            
            module_scoring = ModuleSpecificScoring(self.supabase_manager)
            
            # Calculate module-specific scores
            persistence, novelty, surprise = await module_scoring.calculate_module_scores(strand)
            
            # Update strand with calculated scores
            strand['persistence_score'] = persistence
            strand['novelty_score'] = novelty
            strand['surprise_rating'] = surprise
            
            # Calculate overall resonance score
            resonance_score = (persistence + novelty + surprise) / 3
            strand['resonance_score'] = resonance_score
            
        except Exception as e:
            self.logger.error(f"Error calculating resonance for strand {strand.get('id')}: {e}")
            # Set default scores
            strand['persistence_score'] = 0.5
            strand['novelty_score'] = 0.5
            strand['surprise_rating'] = 0.5
            strand['resonance_score'] = 0.5
    
    async def create_braid_from_cluster(
        self, 
        cluster_strands: List[Dict[str, Any]], 
        cluster_type: str,
        strand_type: str
    ) -> Optional[str]:
        """
        Create a braid from a cluster of strands
        
        Args:
            cluster_strands: List of strands in the cluster
            cluster_type: Type of cluster
            strand_type: Type of strands
            
        Returns:
            Braid ID if successful, None otherwise
        """
        try:
            if len(cluster_strands) < 3:
                self.logger.warning(f"Cluster too small for braid creation: {len(cluster_strands)} strands")
                return None
            
            # Calculate average scores for the cluster
            avg_persistence = sum(s.get('persistence_score', 0.5) for s in cluster_strands) / len(cluster_strands)
            avg_novelty = sum(s.get('novelty_score', 0.5) for s in cluster_strands) / len(cluster_strands)
            avg_surprise = sum(s.get('surprise_rating', 0.5) for s in cluster_strands) / len(cluster_strands)
            avg_resonance = (avg_persistence + avg_novelty + avg_surprise) / 3
            
            # Create braid data
            braid_data = {
                'id': str(uuid.uuid4()),
                'kind': f'{strand_type}_braid',
                'agent_id': 'learning_system',
                'braid_level': 2,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'persistence_score': avg_persistence,
                'novelty_score': avg_novelty,
                'surprise_rating': avg_surprise,
                'resonance_score': avg_resonance,
                'cluster_type': cluster_type,
                'source_strands': [s['id'] for s in cluster_strands],
                'strand_count': len(cluster_strands),
                'content': {
                    'cluster_analysis': f"Braid created from {len(cluster_strands)} {strand_type} strands",
                    'cluster_type': cluster_type,
                    'average_scores': {
                        'persistence': avg_persistence,
                        'novelty': avg_novelty,
                        'surprise': avg_surprise,
                        'resonance': avg_resonance
                    }
                }
            }
            
            # Save braid to database
            result = self.supabase_manager.supabase.table('AD_strands').insert(braid_data).execute()
            
            if result.data:
                braid_id = result.data[0]['id']
                self.logger.info(f"Created braid {braid_id} from {len(cluster_strands)} {strand_type} strands")
                return braid_id
            else:
                self.logger.error("Failed to create braid in database")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating braid from cluster: {e}")
            return None
    
    async def get_cluster_learning_statistics(self, strand_type: str) -> Dict[str, Any]:
        """Get learning statistics for a strand type"""
        try:
            # Get all braids of this type
            result = self.supabase_manager.supabase.table('AD_strands').select('*').eq('kind', f'{strand_type}_braid').execute()
            braids = result.data if result.data else []
            
            stats = {
                'total_braids': len(braids),
                'average_braid_size': sum(b.get('strand_count', 0) for b in braids) / len(braids) if braids else 0,
                'average_resonance': sum(b.get('resonance_score', 0) for b in braids) / len(braids) if braids else 0,
                'strand_type': strand_type
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting learning statistics for {strand_type}: {e}")
            return {'total_braids': 0, 'average_braid_size': 0, 'average_resonance': 0, 'strand_type': strand_type}
