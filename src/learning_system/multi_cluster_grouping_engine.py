"""
Multi-Cluster Grouping Engine

Groups strands into clusters based on their characteristics and learning requirements.
This engine provides the clustering functionality needed by the learning pipeline.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class ClusterType(Enum):
    """Types of clusters for strand grouping"""
    PATTERN_TIMEFRAME = "pattern_timeframe"
    ASSET = "asset"
    TIMEFRAME = "timeframe"
    OUTCOME = "outcome"
    PATTERN = "pattern"
    METHOD = "method"
    PLAN_TYPE = "plan_type"


class MultiClusterGroupingEngine:
    """
    Multi-Cluster Grouping Engine for strand clustering
    
    Groups strands into clusters based on their characteristics and learning requirements.
    This provides the clustering functionality needed by the learning pipeline.
    """
    
    def __init__(self, supabase_manager):
        """
        Initialize multi-cluster grouping engine
        
        Args:
            supabase_manager: Database manager for strand operations
        """
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(__name__)
        
        # Import universal clustering for actual clustering logic
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'Modules', 'Alpha_Detector', 'src', 'intelligence', 'universal_learning'))
        from universal_clustering import UniversalClustering
        
        self.universal_clustering = UniversalClustering(supabase_manager)
    
    async def get_strand_clusters(
        self, 
        strand: Dict[str, Any], 
        strand_type: str,
        min_cluster_size: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get clusters for a specific strand type
        
        Args:
            strand: The strand to find clusters for
            strand_type: Type of strand (pattern, prediction_review, etc.)
            min_cluster_size: Minimum cluster size to consider
            
        Returns:
            Dictionary of cluster_type -> list of strands in that cluster
        """
        try:
            # Get all strands of the same type
            all_strands = await self._get_strands_by_type(strand_type)
            if not all_strands:
                return {}
            
            # Use universal clustering to group strands
            clusters = await self.universal_clustering.cluster_strands(
                all_strands, 
                strand_kind=strand_type,
                braid_level=1  # Only cluster level 1 strands
            )
            
            # Convert to the expected format
            result = {}
            for cluster in clusters:
                cluster_type = self._determine_cluster_type(cluster, strand_type)
                if cluster_type not in result:
                    result[cluster_type] = []
                
                # Add strands from this cluster
                for strand_data in cluster.strands:
                    result[cluster_type].append(strand_data)
            
            # Filter out clusters that are too small
            filtered_result = {
                cluster_type: strands 
                for cluster_type, strands in result.items() 
                if len(strands) >= min_cluster_size
            }
            
            self.logger.info(f"Found {len(filtered_result)} clusters for {strand_type}")
            return filtered_result
            
        except Exception as e:
            self.logger.error(f"Error getting clusters for {strand_type}: {e}")
            return {}
    
    async def _get_strands_by_type(self, strand_type: str) -> List[Dict[str, Any]]:
        """Get all strands of a specific type"""
        try:
            result = self.supabase_manager.supabase.table('AD_strands').select('*').eq('kind', strand_type).execute()
            return result.data if result.data else []
        except Exception as e:
            self.logger.error(f"Error getting strands by type {strand_type}: {e}")
            return []
    
    def _determine_cluster_type(self, cluster, strand_type: str) -> str:
        """Determine the cluster type based on cluster characteristics"""
        try:
            # For now, use a simple mapping based on strand type
            # This could be enhanced to analyze cluster characteristics
            cluster_type_mapping = {
                'pattern': ClusterType.PATTERN_TIMEFRAME.value,
                'prediction_review': ClusterType.METHOD.value,
                'conditional_trading_plan': ClusterType.PLAN_TYPE.value,
                'trading_decision': ClusterType.OUTCOME.value,
                'trade_outcome': ClusterType.OUTCOME.value,
                'execution_outcome': ClusterType.OUTCOME.value,
                'portfolio_outcome': ClusterType.OUTCOME.value
            }
            
            return cluster_type_mapping.get(strand_type, ClusterType.PATTERN.value)
            
        except Exception as e:
            self.logger.error(f"Error determining cluster type: {e}")
            return ClusterType.PATTERN.value
    
    async def get_cluster_statistics(self, strand_type: str) -> Dict[str, Any]:
        """Get statistics about clusters for a strand type"""
        try:
            clusters = await self.get_strand_clusters({}, strand_type)
            
            stats = {
                'total_clusters': len(clusters),
                'cluster_sizes': [len(strands) for strands in clusters.values()],
                'average_cluster_size': sum(len(strands) for strands in clusters.values()) / len(clusters) if clusters else 0,
                'strand_type': strand_type
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting cluster statistics for {strand_type}: {e}")
            return {'total_clusters': 0, 'cluster_sizes': [], 'average_cluster_size': 0, 'strand_type': strand_type}
