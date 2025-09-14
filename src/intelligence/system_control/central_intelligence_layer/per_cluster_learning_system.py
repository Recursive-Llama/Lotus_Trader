"""
Per-Cluster Learning System - Phase 4

Each cluster learns independently with 3+ prediction threshold.
Integrates with LLM Learning Analyzer for comprehensive cluster analysis.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from .multi_cluster_grouping_engine import MultiClusterGroupingEngine
from .llm_learning_analyzer import LLMLearningAnalyzer


class PerClusterLearningSystem:
    """
    Per-cluster learning system that processes each cluster independently
    
    Responsibilities:
    1. Process learning for each cluster type independently
    2. Check learning thresholds per cluster
    3. Trigger LLM analysis for qualifying clusters
    4. Create learning braids from insights
    5. Update context system with new learnings
    """
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(f"{__name__}.per_cluster_learning")
        
        # Initialize components
        self.cluster_grouper = MultiClusterGroupingEngine(supabase_manager)
        self.llm_analyzer = LLMLearningAnalyzer(llm_client, supabase_manager)
        
        # Learning thresholds
        self.cluster_thresholds = {
            'min_predictions_for_learning': 3,     # 3+ prediction reviews
            'min_confidence': 0.1,                 # Very low threshold
            'min_sample_size': 3,                  # Need at least 3 data points
            'learn_from_failures': True,           # Failures are valuable!
            'learn_from_successes': True           # Successes confirm patterns
        }
    
    async def process_all_clusters(self) -> Dict[str, List[str]]:
        """
        Process learning for all cluster types
        
        Returns:
            Dictionary with cluster types as keys and created learning braid IDs as values
        """
        try:
            self.logger.info("Starting per-cluster learning process")
            
            # Get all cluster groups
            cluster_groups = await self.cluster_grouper.get_all_cluster_groups()
            
            # Process each cluster type
            all_learning_braids = {}
            
            for cluster_type, clusters in cluster_groups.items():
                self.logger.info(f"Processing {cluster_type} clusters: {len(clusters)} groups")
                
                cluster_braids = []
                for cluster_key, prediction_reviews in clusters.items():
                    if self.meets_learning_thresholds(prediction_reviews):
                        learning_braid = await self.process_cluster_learning(
                            cluster_type, cluster_key, prediction_reviews
                        )
                        if learning_braid:
                            cluster_braids.append(learning_braid['id'])
                
                all_learning_braids[cluster_type] = cluster_braids
                self.logger.info(f"Created {len(cluster_braids)} learning braids for {cluster_type}")
            
            self.logger.info(f"Per-cluster learning complete: {sum(len(braids) for braids in all_learning_braids.values())} total braids created")
            return all_learning_braids
            
        except Exception as e:
            self.logger.error(f"Error in per-cluster learning process: {e}")
            return {}
    
    async def process_cluster_learning(self, cluster_type: str, cluster_key: str, 
                                     prediction_reviews: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Process learning for a specific cluster
        
        Args:
            cluster_type: Type of cluster (pattern_timeframe, asset, etc.)
            cluster_key: Specific cluster key (BTC, success, etc.)
            prediction_reviews: List of prediction review strands
            
        Returns:
            Learning braid strand with insights, or None if learning failed
        """
        try:
            self.logger.info(f"Processing learning for {cluster_type}:{cluster_key} with {len(prediction_reviews)} reviews")
            
            # Check if meets learning thresholds
            if not self.meets_learning_thresholds(prediction_reviews):
                self.logger.info(f"Cluster {cluster_type}:{cluster_key} does not meet learning thresholds")
                return None
            
            # Analyze cluster for learning insights using LLM
            learning_braid = await self.llm_analyzer.analyze_cluster_for_learning(
                cluster_type, cluster_key, prediction_reviews
            )
            
            if learning_braid:
                # Mark source strands as consumed for this specific cluster
                for strand in prediction_reviews:
                    await self.cluster_grouper.mark_strand_consumed_for_cluster(
                        strand['id'], cluster_type, cluster_key
                    )
                
                # Update context system with new learnings
                await self.update_context_system(learning_braid)
                
                self.logger.info(f"Successfully created learning braid for {cluster_type}:{cluster_key}")
            
            return learning_braid
            
        except Exception as e:
            self.logger.error(f"Error processing cluster learning for {cluster_type}:{cluster_key}: {e}")
            return None
    
    def meets_learning_thresholds(self, prediction_reviews: List[Dict[str, Any]]) -> bool:
        """
        Check if cluster meets learning thresholds
        
        Args:
            prediction_reviews: List of prediction review strands
            
        Returns:
            True if cluster meets learning thresholds, False otherwise
        """
        try:
            # Check minimum predictions threshold
            if len(prediction_reviews) < self.cluster_thresholds['min_predictions_for_learning']:
                return False
            
            # Check confidence threshold (very low - learn from everything)
            confidences = [pr.get('content', {}).get('confidence', 0) for pr in prediction_reviews]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            if avg_confidence < self.cluster_thresholds['min_confidence']:
                return False
            
            # Check sample size threshold
            if len(prediction_reviews) < self.cluster_thresholds['min_sample_size']:
                return False
            
            # Check if we should learn from this cluster (success/failure)
            success_count = sum(1 for pr in prediction_reviews if pr.get('content', {}).get('success', False))
            failure_count = len(prediction_reviews) - success_count
            
            # Learn from failures if enabled
            if not self.cluster_thresholds['learn_from_failures'] and failure_count > 0:
                return False
            
            # Learn from successes if enabled
            if not self.cluster_thresholds['learn_from_successes'] and success_count > 0:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking learning thresholds: {e}")
            return False
    
    async def update_context_system(self, learning_braid: Dict[str, Any]) -> bool:
        """
        Update context system with new learning braid
        
        Args:
            learning_braid: Learning braid strand with insights
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # For now, just log the update
            # In a full implementation, this would update the context system
            # to make the learning insights available for future predictions
            
            self.logger.info(f"Updated context system with learning braid: {learning_braid['id']}")
            
            # TODO: Implement actual context system update
            # This could involve:
            # 1. Indexing the learning braid in the context system
            # 2. Updating pattern recognition weights
            # 3. Updating prediction confidence calculations
            # 4. Updating similarity matching algorithms
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating context system: {e}")
            return False
    
    
    async def get_learning_statistics(self) -> Dict[str, Any]:
        """Get statistics about the learning system"""
        
        try:
            # Get cluster statistics
            cluster_groups = await self.cluster_grouper.get_all_cluster_groups()
            cluster_stats = self.cluster_grouper.get_cluster_statistics(cluster_groups)
            
            # Get learning braid count using Direct Supabase Client
            result = self.supabase_manager.client.table('ad_strands').select('id', count='exact').eq('kind', 'prediction_review').gte('braid_level', 2).execute()
            learning_braid_count = result.count if result.count else 0
            
            return {
                'learning_braids': learning_braid_count,
                'cluster_statistics': cluster_stats,
                'learning_thresholds': self.cluster_thresholds,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting learning statistics: {e}")
            return {
                'learning_braids': 0,
                'braid_statistics': {},
                'cluster_statistics': {},
                'learning_thresholds': self.cluster_thresholds,
                'error': str(e)
            }
    
    async def process_single_cluster_type(self, cluster_type: str) -> List[str]:
        """
        Process learning for a single cluster type
        
        Args:
            cluster_type: Type of cluster to process
            
        Returns:
            List of created learning braid IDs
        """
        try:
            self.logger.info(f"Processing single cluster type: {cluster_type}")
            
            # Get clusters for this type
            cluster_groups = await self.cluster_grouper.get_all_cluster_groups()
            
            if cluster_type not in cluster_groups:
                self.logger.warning(f"Cluster type {cluster_type} not found")
                return []
            
            clusters = cluster_groups[cluster_type]
            cluster_braids = []
            
            for cluster_key, prediction_reviews in clusters.items():
                if self.meets_learning_thresholds(prediction_reviews):
                    learning_braid = await self.process_cluster_learning(
                        cluster_type, cluster_key, prediction_reviews
                    )
                    if learning_braid:
                        cluster_braids.append(learning_braid['id'])
            
            self.logger.info(f"Created {len(cluster_braids)} learning braids for {cluster_type}")
            return cluster_braids
            
        except Exception as e:
            self.logger.error(f"Error processing single cluster type {cluster_type}: {e}")
            return []
    
    def update_learning_thresholds(self, new_thresholds: Dict[str, Any]) -> bool:
        """
        Update learning thresholds
        
        Args:
            new_thresholds: New threshold values
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Validate new thresholds
            for key, value in new_thresholds.items():
                if key in self.cluster_thresholds:
                    if key == 'min_predictions_for_learning' and value < 1:
                        self.logger.warning(f"Invalid threshold for {key}: {value}")
                        return False
                    if key == 'min_confidence' and (value < 0 or value > 1):
                        self.logger.warning(f"Invalid threshold for {key}: {value}")
                        return False
                    if key == 'min_sample_size' and value < 1:
                        self.logger.warning(f"Invalid threshold for {key}: {value}")
                        return False
            
            # Update thresholds
            self.cluster_thresholds.update(new_thresholds)
            
            self.logger.info(f"Updated learning thresholds: {new_thresholds}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating learning thresholds: {e}")
            return False
