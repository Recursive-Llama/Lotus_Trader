"""
Multi-Cluster Grouping Engine - Phase 4

Groups prediction reviews into 7 different cluster types for comprehensive learning.
Each cluster type provides a different perspective on the data for learning insights.
Now supports JSONB cluster_key with consumed status tracking.
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
                    # Check if strand is not consumed for this cluster
                    if not self._is_strand_consumed_for_cluster(review, cluster_name, cluster_key):
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
    
    def _is_strand_consumed_for_cluster(self, strand: Dict[str, Any], cluster_type: str, cluster_key: str) -> bool:
        """Check if strand is consumed for specific cluster"""
        
        cluster_assignments = strand.get('cluster_key', [])
        
        for assignment in cluster_assignments:
            if (assignment.get('cluster_type') == cluster_type and 
                assignment.get('cluster_key') == cluster_key):
                return assignment.get('consumed', False)
        
        return False
    
    def _extract_cluster_key(self, cluster_name: str, review: Dict[str, Any]) -> str:
        """Extract cluster key from prediction review based on cluster type
        
        Reads from both 'content' and 'module_intelligence' fields for robust data access.
        Falls back gracefully if either field is missing.
        """
        
        # Try content first, then fall back to module_intelligence
        content = review.get('content', {})
        module_intelligence = review.get('module_intelligence', {})
        
        # Helper function to get value from either field
        def get_value(key: str, default=''):
            # Try content first
            if isinstance(content, dict) and content.get(key) is not None:
                return content.get(key, default)
            # Fall back to module_intelligence
            if isinstance(module_intelligence, dict) and module_intelligence.get(key) is not None:
                return module_intelligence.get(key, default)
            return default
        
        if cluster_name == 'pattern_timeframe':
            # Pattern + Timeframe: group_signature + asset
            group_signature = get_value('group_signature')
            asset = get_value('asset')
            return f"{asset}_{group_signature}" if group_signature and asset else None
            
        elif cluster_name == 'asset':
            # Asset only
            return get_value('asset')
            
        elif cluster_name == 'timeframe':
            # Timeframe only
            return get_value('timeframe')
            
        elif cluster_name == 'outcome':
            # Success or Failure
            success = get_value('success', False)
            # Handle both boolean and string values
            if isinstance(success, str):
                success = success.lower() in ('true', '1', 'yes')
            return 'success' if success else 'failure'
            
        elif cluster_name == 'pattern':
            # Pattern only (group_type)
            return get_value('group_type')
            
        elif cluster_name == 'group_type':
            # Group Type (single_single, multi_single, etc.)
            return get_value('group_type')
            
        elif cluster_name == 'method':
            # Method (Code vs LLM)
            return get_value('method')
            
        else:
            self.logger.warning(f"Unknown cluster type: {cluster_name}")
            return None
    
    async def assign_strand_to_clusters(self, strand: Dict[str, Any]) -> Dict[str, Any]:
        """Assign strand to all relevant clusters"""
        
        cluster_assignments = []
        
        for cluster_type in self.cluster_types.keys():
            cluster_key = self._extract_cluster_key(cluster_type, strand)
            if cluster_key:
                cluster_assignments.append({
                    "cluster_type": cluster_type,
                    "cluster_key": cluster_key,
                    "braid_level": strand.get('braid_level', 1),
                    "consumed": False
                })
        
        strand['cluster_key'] = cluster_assignments
        return strand
    
    async def mark_strand_consumed_for_cluster(self, strand_id: str, cluster_type: str, cluster_key: str) -> bool:
        """Mark strand as consumed for specific cluster using Direct Supabase Client"""
        
        try:
            # Get current strand using Direct Supabase Client
            result = self.supabase_manager.client.table('ad_strands').select('*').eq('id', strand_id).execute()
            
            if not result.data:
                return False
            
            strand = result.data[0]
            cluster_assignments = strand.get('cluster_key', [])
            
            # Update consumed status for specific cluster
            for assignment in cluster_assignments:
                if (assignment.get('cluster_type') == cluster_type and 
                    assignment.get('cluster_key') == cluster_key):
                    assignment['consumed'] = True
                    break
            
            # Update strand in database using Direct Supabase Client
            self.supabase_manager.client.table('ad_strands').update({
                'cluster_key': cluster_assignments
            }).eq('id', strand_id).execute()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error marking strand consumed: {e}")
            return False
    
    async def get_cluster_groups(self, cluster_type: str, cluster_key: str) -> List[Dict[str, Any]]:
        """Get all prediction reviews in a specific cluster group using Direct Supabase Client"""
        
        try:
            # Use Direct Supabase Client instead of RPC
            if cluster_type == 'pattern_timeframe':
                # Split cluster_key into asset and group_signature
                parts = cluster_key.split('_', 1)
                if len(parts) == 2:
                    asset, group_signature = parts
                    result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').eq('content->>asset', asset).eq('content->>group_signature', group_signature).execute()
                else:
                    result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').eq('content->>group_signature', cluster_key).execute()
            elif cluster_type == 'asset':
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').eq('content->>asset', cluster_key).execute()
            elif cluster_type == 'timeframe':
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').eq('content->>timeframe', cluster_key).execute()
            elif cluster_type == 'outcome':
                success_value = cluster_key == 'success'
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').eq('content->>success', success_value).execute()
            elif cluster_type == 'pattern':
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').eq('content->>group_type', cluster_key).execute()
            elif cluster_type == 'group_type':
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').eq('content->>group_type', cluster_key).execute()
            elif cluster_type == 'method':
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').eq('content->>method', cluster_key).execute()
            else:
                self.logger.error(f"Unknown cluster type: {cluster_type}")
                return []
            
            return result.data if result.data else []
            
        except Exception as e:
            self.logger.error(f"Error getting cluster groups for {cluster_type}:{cluster_key}: {e}")
            return []
    
    
    async def get_all_cluster_groups(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Get all cluster groups across all cluster types using Supabase client"""
        
        all_clusters = {}
        
        try:
            # Get all prediction_review strands
            result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').execute()
            
            if not result.data:
                self.logger.warning("No prediction_review strands found")
                return {}
            
            prediction_reviews = result.data
            self.logger.info(f"Found {len(prediction_reviews)} prediction_review strands")
            
            # Group by each cluster type
            for cluster_type in self.cluster_types.keys():
                cluster_groups = {}
                
                # Group prediction reviews by cluster type
                for review in prediction_reviews:
                    try:
                        # Ensure review has the required structure
                        if not isinstance(review, dict):
                            self.logger.warning(f"Review is not a dict: {type(review)}")
                            continue
                        
                        # Ensure we have data to work with (either content or module_intelligence)
                        if not review.get('content') and not review.get('module_intelligence'):
                            self.logger.warning(f"Review missing both content and module_intelligence: {review.get('id', 'unknown')}")
                            continue
                        
                        cluster_key = self._extract_cluster_key(cluster_type, review)
                        
                        if cluster_key:
                            # Check if strand is not consumed for this cluster
                            if not self._is_strand_consumed_for_cluster(review, cluster_type, cluster_key):
                                if cluster_key not in cluster_groups:
                                    cluster_groups[cluster_key] = []
                                cluster_groups[cluster_key].append(review)
                    
                    except Exception as e:
                        self.logger.warning(f"Error processing review for cluster {cluster_type}: {e}")
                        continue
                
                # Filter groups with at least 3 reviews (learning threshold)
                filtered_groups = {k: v for k, v in cluster_groups.items() if len(v) >= 3}
                all_clusters[cluster_type] = filtered_groups
                
                self.logger.info(f"Cluster {cluster_type}: {len(cluster_groups)} total groups, {len(filtered_groups)} with 3+ reviews")
            
            return all_clusters
            
        except Exception as e:
            self.logger.error(f"Error getting all cluster groups: {e}")
            return {}
    
    
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