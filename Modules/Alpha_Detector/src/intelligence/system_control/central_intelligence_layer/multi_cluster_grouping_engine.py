"""
Multi-Cluster Grouping Engine - Phase 4

Groups prediction reviews into 7 different cluster types for comprehensive learning.
Each cluster type provides a different perspective on the data for learning insights.
"""

import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime, timezone


class MultiClusterGroupingEngine:
    """
    Groups prediction reviews into 7 cluster types for multi-dimensional learning
    
    Cluster Types:
    1. Pattern + Timeframe (exact group signature)
    2. Asset only
    3. Timeframe only
    4. Success or Failure
    5. Pattern only (no timeframe)
    6. Group Type (single_single, multi_single, etc.)
    7. Method (Code vs LLM)
    """
    
    def __init__(self, supabase_manager):
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(f"{__name__}.multi_cluster_grouping")
        
        # Define cluster types and their query fields
        self.cluster_types = {
            'pattern_timeframe': 'group_signature + asset',
            'asset': 'asset',
            'timeframe': 'timeframe', 
            'outcome': 'success',
            'pattern': 'group_type',
            'group_type': 'group_type',
            'method': 'method'
        }
    
    async def group_prediction_reviews(self, prediction_reviews: List[Dict[str, Any]]) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Group prediction reviews into 7 cluster types
        
        Args:
            prediction_reviews: List of prediction review strands
            
        Returns:
            Dictionary with cluster types as keys and grouped reviews as values
        """
        try:
            self.logger.info(f"Grouping {len(prediction_reviews)} prediction reviews into clusters")
            
            clusters = {}
            
            # Group by each cluster type
            for cluster_name, query_field in self.cluster_types.items():
                clusters[cluster_name] = await self._group_by_cluster_type(
                    cluster_name, query_field, prediction_reviews
                )
            
            self.logger.info(f"Created {len(clusters)} cluster types with {sum(len(groups) for groups in clusters.values())} total groups")
            return clusters
            
        except Exception as e:
            self.logger.error(f"Error grouping prediction reviews: {e}")
            return {}
    
    async def _group_by_cluster_type(self, cluster_name: str, query_field: str, prediction_reviews: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group prediction reviews by specific cluster type"""
        
        groups = {}
        
        for review in prediction_reviews:
            try:
                # Extract cluster key based on cluster type
                cluster_key = self._extract_cluster_key(cluster_name, review)
                
                if cluster_key:
                    if cluster_key not in groups:
                        groups[cluster_key] = []
                    groups[cluster_key].append(review)
                    
            except Exception as e:
                self.logger.warning(f"Error processing review for cluster {cluster_name}: {e}")
                continue
        
        # Filter groups with at least 3 reviews (learning threshold)
        filtered_groups = {k: v for k, v in groups.items() if len(v) >= 3}
        
        self.logger.info(f"Cluster {cluster_name}: {len(groups)} total groups, {len(filtered_groups)} with 3+ reviews")
        return filtered_groups
    
    def _extract_cluster_key(self, cluster_name: str, review: Dict[str, Any]) -> str:
        """Extract cluster key from prediction review based on cluster type"""
        
        content = review.get('content', {})
        
        if cluster_name == 'pattern_timeframe':
            # Pattern + Timeframe: group_signature + asset
            group_signature = content.get('group_signature', '')
            asset = content.get('asset', '')
            return f"{asset}_{group_signature}" if group_signature and asset else None
            
        elif cluster_name == 'asset':
            # Asset only
            return content.get('asset', '')
            
        elif cluster_name == 'timeframe':
            # Timeframe only
            return content.get('timeframe', '')
            
        elif cluster_name == 'outcome':
            # Success or Failure
            success = content.get('success', False)
            return 'success' if success else 'failure'
            
        elif cluster_name == 'pattern':
            # Pattern only (group_type)
            return content.get('group_type', '')
            
        elif cluster_name == 'group_type':
            # Group Type (single_single, multi_single, etc.)
            return content.get('group_type', '')
            
        elif cluster_name == 'method':
            # Method (Code vs LLM)
            return content.get('method', '')
            
        else:
            self.logger.warning(f"Unknown cluster type: {cluster_name}")
            return None
    
    async def get_cluster_groups(self, cluster_type: str, cluster_key: str) -> List[Dict[str, Any]]:
        """Get all prediction reviews in a specific cluster group"""
        
        try:
            query = self._build_cluster_query(cluster_type, cluster_key)
            result = await self.supabase_manager.execute_query(query, [cluster_key])
            
            return [dict(row) for row in result]
            
        except Exception as e:
            self.logger.error(f"Error getting cluster groups for {cluster_type}:{cluster_key}: {e}")
            return []
    
    def _build_cluster_query(self, cluster_type: str, cluster_key: str) -> str:
        """Build SQL query for specific cluster type and key"""
        
        base_query = "SELECT * FROM AD_strands WHERE kind = 'prediction_review'"
        
        if cluster_type == 'pattern_timeframe':
            # Split cluster_key into asset and group_signature
            parts = cluster_key.split('_', 1)
            if len(parts) == 2:
                asset, group_signature = parts
                return f"{base_query} AND content->>'asset' = %s AND content->>'group_signature' = %s"
            else:
                return f"{base_query} AND content->>'group_signature' = %s"
                
        elif cluster_type == 'asset':
            return f"{base_query} AND content->>'asset' = %s"
            
        elif cluster_type == 'timeframe':
            return f"{base_query} AND content->>'timeframe' = %s"
            
        elif cluster_type == 'outcome':
            success_value = 'true' if cluster_key == 'success' else 'false'
            return f"{base_query} AND content->>'success' = %s"
            
        elif cluster_type == 'pattern':
            return f"{base_query} AND content->>'group_type' = %s"
            
        elif cluster_type == 'group_type':
            return f"{base_query} AND content->>'group_type' = %s"
            
        elif cluster_type == 'method':
            return f"{base_query} AND content->>'method' = %s"
            
        else:
            raise ValueError(f"Unknown cluster type: {cluster_type}")
    
    async def get_all_cluster_groups(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Get all cluster groups across all cluster types"""
        
        all_clusters = {}
        
        for cluster_type in self.cluster_types.keys():
            try:
                # Get all unique cluster keys for this type
                cluster_keys = await self._get_cluster_keys(cluster_type)
                
                cluster_groups = {}
                for cluster_key in cluster_keys:
                    groups = await self.get_cluster_groups(cluster_type, cluster_key)
                    if groups:  # Only include non-empty groups
                        cluster_groups[cluster_key] = groups
                
                all_clusters[cluster_type] = cluster_groups
                
            except Exception as e:
                self.logger.error(f"Error getting cluster groups for {cluster_type}: {e}")
                all_clusters[cluster_type] = {}
        
        return all_clusters
    
    async def _get_cluster_keys(self, cluster_type: str) -> List[str]:
        """Get all unique cluster keys for a specific cluster type"""
        
        try:
            if cluster_type == 'pattern_timeframe':
                query = """
                    SELECT DISTINCT 
                        CONCAT(content->>'asset', '_', content->>'group_signature') as cluster_key
                    FROM AD_strands 
                    WHERE kind = 'prediction_review' 
                    AND content->>'group_signature' IS NOT NULL
                    AND content->>'asset' IS NOT NULL
                """
            elif cluster_type == 'asset':
                query = """
                    SELECT DISTINCT content->>'asset' as cluster_key
                    FROM AD_strands 
                    WHERE kind = 'prediction_review' 
                    AND content->>'asset' IS NOT NULL
                """
            elif cluster_type == 'timeframe':
                query = """
                    SELECT DISTINCT content->>'timeframe' as cluster_key
                    FROM AD_strands 
                    WHERE kind = 'prediction_review' 
                    AND content->>'timeframe' IS NOT NULL
                """
            elif cluster_type == 'outcome':
                query = """
                    SELECT DISTINCT 
                        CASE 
                            WHEN content->>'success' = 'true' THEN 'success'
                            ELSE 'failure'
                        END as cluster_key
                    FROM AD_strands 
                    WHERE kind = 'prediction_review' 
                    AND content->>'success' IS NOT NULL
                """
            elif cluster_type == 'pattern':
                query = """
                    SELECT DISTINCT content->>'group_type' as cluster_key
                    FROM AD_strands 
                    WHERE kind = 'prediction_review' 
                    AND content->>'group_type' IS NOT NULL
                """
            elif cluster_type == 'group_type':
                query = """
                    SELECT DISTINCT content->>'group_type' as cluster_key
                    FROM AD_strands 
                    WHERE kind = 'prediction_review' 
                    AND content->>'group_type' IS NOT NULL
                """
            elif cluster_type == 'method':
                query = """
                    SELECT DISTINCT content->>'method' as cluster_key
                    FROM AD_strands 
                    WHERE kind = 'prediction_review' 
                    AND content->>'method' IS NOT NULL
                """
            else:
                raise ValueError(f"Unknown cluster type: {cluster_type}")
            
            result = await self.supabase_manager.execute_query(query)
            return [row[0] for row in result if row[0]]
            
        except Exception as e:
            self.logger.error(f"Error getting cluster keys for {cluster_type}: {e}")
            return []
    
    def get_cluster_statistics(self, clusters: Dict[str, Dict[str, List[Dict[str, Any]]]]) -> Dict[str, Any]:
        """Get statistics about cluster groupings"""
        
        stats = {
            'total_cluster_types': len(clusters),
            'total_groups': sum(len(groups) for groups in clusters.values()),
            'total_reviews': sum(
                sum(len(group) for group in groups.values()) 
                for groups in clusters.values()
            ),
            'cluster_type_breakdown': {}
        }
        
        for cluster_type, groups in clusters.items():
            stats['cluster_type_breakdown'][cluster_type] = {
                'group_count': len(groups),
                'review_count': sum(len(group) for group in groups.values()),
                'avg_reviews_per_group': sum(len(group) for group in groups.values()) / len(groups) if groups else 0
            }
        
        return stats
