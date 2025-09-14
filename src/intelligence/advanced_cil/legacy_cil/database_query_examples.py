"""
Database Query Examples - Phase 4

Comprehensive SQL query examples for all 7 cluster types in the multi-cluster learning system.
These queries are used by the MultiClusterGroupingEngine and other components.
"""

from typing import List, Dict, Any


class DatabaseQueryExamples:
    """
    Database query examples for multi-cluster learning system
    
    Provides SQL queries for all 7 cluster types:
    1. Pattern + Timeframe (exact group signature)
    2. Asset only
    3. Timeframe only
    4. Success or Failure
    5. Pattern only (no timeframe)
    6. Group Type (single_single, multi_single, etc.)
    7. Method (Code vs LLM)
    """
    
    @staticmethod
    def get_cluster_queries() -> Dict[str, str]:
        """Get all cluster query templates"""
        
        return {
            # 1. Pattern + Timeframe (Exact Match)
            'pattern_timeframe': """
                SELECT * FROM AD_strands 
                WHERE kind = 'prediction_review' 
                AND content->>'group_signature' = %s
                AND content->>'asset' = %s
                ORDER BY created_at DESC
            """,
            
            # 2. Asset Only
            'asset': """
                SELECT * FROM AD_strands 
                WHERE kind = 'prediction_review' 
                AND content->>'asset' = %s
                ORDER BY created_at DESC
            """,
            
            # 3. Timeframe Only
            'timeframe': """
                SELECT * FROM AD_strands 
                WHERE kind = 'prediction_review' 
                AND content->>'timeframe' = %s
                ORDER BY created_at DESC
            """,
            
            # 4. Success/Failure
            'outcome': """
                SELECT * FROM AD_strands 
                WHERE kind = 'prediction_review' 
                AND content->>'success' = %s
                ORDER BY created_at DESC
            """,
            
            # 5. Pattern Only (No Timeframe)
            'pattern': """
                SELECT * FROM AD_strands 
                WHERE kind = 'prediction_review' 
                AND content->>'group_type' = %s
                ORDER BY created_at DESC
            """,
            
            # 6. Group Type
            'group_type': """
                SELECT * FROM AD_strands 
                WHERE kind = 'prediction_review' 
                AND content->>'group_type' = %s
                ORDER BY created_at DESC
            """,
            
            # 7. Method (Code vs LLM)
            'method': """
                SELECT * FROM AD_strands 
                WHERE kind = 'prediction_review' 
                AND content->>'method' = %s
                ORDER BY created_at DESC
            """
        }
    
    @staticmethod
    def get_cluster_key_queries() -> Dict[str, str]:
        """Get queries to extract unique cluster keys for each cluster type"""
        
        return {
            # 1. Pattern + Timeframe Keys
            'pattern_timeframe_keys': """
                SELECT DISTINCT 
                    CONCAT(content->>'asset', '_', content->>'group_signature') as cluster_key
                FROM AD_strands 
                WHERE kind = 'prediction_review' 
                AND content->>'group_signature' IS NOT NULL
                AND content->>'asset' IS NOT NULL
                ORDER BY cluster_key
            """,
            
            # 2. Asset Keys
            'asset_keys': """
                SELECT DISTINCT content->>'asset' as cluster_key
                FROM AD_strands 
                WHERE kind = 'prediction_review' 
                AND content->>'asset' IS NOT NULL
                ORDER BY cluster_key
            """,
            
            # 3. Timeframe Keys
            'timeframe_keys': """
                SELECT DISTINCT content->>'timeframe' as cluster_key
                FROM AD_strands 
                WHERE kind = 'prediction_review' 
                AND content->>'timeframe' IS NOT NULL
                ORDER BY cluster_key
            """,
            
            # 4. Outcome Keys
            'outcome_keys': """
                SELECT DISTINCT 
                    CASE 
                        WHEN content->>'success' = 'true' THEN 'success'
                        ELSE 'failure'
                    END as cluster_key
                FROM AD_strands 
                WHERE kind = 'prediction_review' 
                AND content->>'success' IS NOT NULL
                ORDER BY cluster_key
            """,
            
            # 5. Pattern Keys
            'pattern_keys': """
                SELECT DISTINCT content->>'group_type' as cluster_key
                FROM AD_strands 
                WHERE kind = 'prediction_review' 
                AND content->>'group_type' IS NOT NULL
                ORDER BY cluster_key
            """,
            
            # 6. Group Type Keys
            'group_type_keys': """
                SELECT DISTINCT content->>'group_type' as cluster_key
                FROM AD_strands 
                WHERE kind = 'prediction_review' 
                AND content->>'group_type' IS NOT NULL
                ORDER BY cluster_key
            """,
            
            # 7. Method Keys
            'method_keys': """
                SELECT DISTINCT content->>'method' as cluster_key
                FROM AD_strands 
                WHERE kind = 'prediction_review' 
                AND content->>'method' IS NOT NULL
                ORDER BY cluster_key
            """
        }
    
    @staticmethod
    def get_original_pattern_queries() -> Dict[str, str]:
        """Get queries for retrieving original pattern strands"""
        
        return {
            # Get pattern strands by IDs
            'patterns_by_ids': """
                SELECT * FROM AD_strands 
                WHERE id = ANY(%s) AND kind = 'pattern'
                ORDER BY created_at DESC
            """,
            
            # Get pattern strands by prediction ID
            'patterns_by_prediction': """
                SELECT p.* FROM AD_strands p
                JOIN AD_strands pr ON pr.content->>'prediction_id' = p.id
                WHERE pr.id = %s AND p.kind = 'pattern'
                ORDER BY p.created_at DESC
            """,
            
            # Get all pattern strands for an asset
            'patterns_by_asset': """
                SELECT * FROM AD_strands 
                WHERE kind = 'pattern' 
                AND content->>'symbol' = %s
                ORDER BY created_at DESC
            """,
            
            # Get pattern strands by type
            'patterns_by_type': """
                SELECT * FROM AD_strands 
                WHERE kind = 'pattern' 
                AND content->>'pattern_type' = %s
                ORDER BY created_at DESC
            """
        }
    
    @staticmethod
    def get_braid_queries() -> Dict[str, str]:
        """Get queries for braid level progression"""
        
        return {
            # Get braids by cluster
            'braids_by_cluster': """
                SELECT * FROM AD_strands 
                WHERE kind = 'braid'
                AND content->>'cluster_type' = %s
                AND content->>'cluster_key' = %s
                ORDER BY content->>'braid_level'::int, created_at DESC
            """,
            
            # Get braids by level
            'braids_by_level': """
                SELECT * FROM AD_strands 
                WHERE kind = 'braid'
                AND content->>'braid_level' = %s
                ORDER BY created_at DESC
            """,
            
            # Get braids by cluster and level
            'braids_by_cluster_and_level': """
                SELECT * FROM AD_strands 
                WHERE kind = 'braid'
                AND content->>'cluster_type' = %s
                AND content->>'cluster_key' = %s
                AND content->>'braid_level' = %s
                ORDER BY created_at DESC
            """,
            
            # Get braid statistics
            'braid_statistics': """
                SELECT 
                    content->>'braid_level' as braid_level,
                    content->>'cluster_type' as cluster_type,
                    COUNT(*) as count
                FROM AD_strands 
                WHERE kind = 'braid'
                GROUP BY content->>'braid_level', content->>'cluster_type'
                ORDER BY content->>'braid_level'::int
            """,
            
            # Get strands with braid references
            'strands_with_braids': """
                SELECT * FROM AD_strands 
                WHERE kind = 'prediction_review'
                AND content->>'braid_references' IS NOT NULL
                ORDER BY created_at DESC
            """
        }
    
    @staticmethod
    def get_learning_braid_queries() -> Dict[str, str]:
        """Get queries for learning braids"""
        
        return {
            # Get learning braids by cluster
            'learning_braids_by_cluster': """
                SELECT * FROM AD_strands 
                WHERE kind = 'learning_braid'
                AND content->>'cluster_type' = %s
                AND content->>'cluster_key' = %s
                ORDER BY created_at DESC
            """,
            
            # Get all learning braids
            'all_learning_braids': """
                SELECT * FROM AD_strands 
                WHERE kind = 'learning_braid'
                ORDER BY created_at DESC
            """,
            
            # Get learning braids by cluster type
            'learning_braids_by_type': """
                SELECT * FROM AD_strands 
                WHERE kind = 'learning_braid'
                AND content->>'cluster_type' = %s
                ORDER BY created_at DESC
            """,
            
            # Get learning braid count
            'learning_braid_count': """
                SELECT COUNT(*) as count
                FROM AD_strands 
                WHERE kind = 'learning_braid'
            """,
            
            # Get learning braid statistics
            'learning_braid_statistics': """
                SELECT 
                    content->>'cluster_type' as cluster_type,
                    COUNT(*) as count
                FROM AD_strands 
                WHERE kind = 'learning_braid'
                GROUP BY content->>'cluster_type'
                ORDER BY count DESC
            """
        }
    
    @staticmethod
    def get_cluster_key_queries_with_cluster_keys() -> Dict[str, str]:
        """Get queries using cluster_keys array for efficient querying"""
        
        return {
            # Query by cluster key in cluster_keys array
            'by_cluster_key': """
                SELECT * FROM AD_strands 
                WHERE kind = 'prediction_review'
                AND content->>'cluster_keys' ? %s
                ORDER BY created_at DESC
            """,
            
            # Query by multiple cluster keys
            'by_multiple_cluster_keys': """
                SELECT * FROM AD_strands 
                WHERE kind = 'prediction_review'
                AND content->>'cluster_keys' ?| %s
                ORDER BY created_at DESC
            """,
            
            # Query by cluster key pattern
            'by_cluster_key_pattern': """
                SELECT * FROM AD_strands 
                WHERE kind = 'prediction_review'
                AND EXISTS (
                    SELECT 1 FROM jsonb_array_elements_text(content->>'cluster_keys') as key
                    WHERE key LIKE %s
                )
                ORDER BY created_at DESC
            """,
            
            # Get unique cluster keys from cluster_keys array
            'extract_cluster_keys': """
                SELECT DISTINCT key
                FROM AD_strands,
                LATERAL jsonb_array_elements_text(content->>'cluster_keys') as key
                WHERE kind = 'prediction_review'
                ORDER BY key
            """
        }
    
    @staticmethod
    def get_analytics_queries() -> Dict[str, str]:
        """Get queries for analytics and reporting"""
        
        return {
            # Prediction review statistics
            'prediction_review_stats': """
                SELECT 
                    content->>'asset' as asset,
                    content->>'group_type' as group_type,
                    content->>'timeframe' as timeframe,
                    content->>'method' as method,
                    content->>'success' as success,
                    COUNT(*) as count,
                    AVG((content->>'return_pct')::float) as avg_return,
                    AVG((content->>'confidence')::float) as avg_confidence,
                    AVG((content->>'max_drawdown')::float) as avg_drawdown
                FROM AD_strands 
                WHERE kind = 'prediction_review'
                GROUP BY 
                    content->>'asset',
                    content->>'group_type',
                    content->>'timeframe',
                    content->>'method',
                    content->>'success'
                ORDER BY count DESC
            """,
            
            # Success rate by cluster type
            'success_rate_by_cluster': """
                SELECT 
                    content->>'asset' as asset,
                    content->>'group_type' as group_type,
                    COUNT(*) as total_predictions,
                    SUM(CASE WHEN content->>'success' = 'true' THEN 1 ELSE 0 END) as successful_predictions,
                    ROUND(
                        SUM(CASE WHEN content->>'success' = 'true' THEN 1 ELSE 0 END)::float / COUNT(*)::float * 100, 2
                    ) as success_rate
                FROM AD_strands 
                WHERE kind = 'prediction_review'
                GROUP BY content->>'asset', content->>'group_type'
                HAVING COUNT(*) >= 3
                ORDER BY success_rate DESC
            """,
            
            # Method performance comparison
            'method_performance': """
                SELECT 
                    content->>'method' as method,
                    COUNT(*) as total_predictions,
                    SUM(CASE WHEN content->>'success' = 'true' THEN 1 ELSE 0 END) as successful_predictions,
                    ROUND(
                        SUM(CASE WHEN content->>'success' = 'true' THEN 1 ELSE 0 END)::float / COUNT(*)::float * 100, 2
                    ) as success_rate,
                    AVG((content->>'return_pct')::float) as avg_return,
                    AVG((content->>'confidence')::float) as avg_confidence
                FROM AD_strands 
                WHERE kind = 'prediction_review'
                GROUP BY content->>'method'
                ORDER BY success_rate DESC
            """,
            
            # Timeframe performance
            'timeframe_performance': """
                SELECT 
                    content->>'timeframe' as timeframe,
                    COUNT(*) as total_predictions,
                    SUM(CASE WHEN content->>'success' = 'true' THEN 1 ELSE 0 END) as successful_predictions,
                    ROUND(
                        SUM(CASE WHEN content->>'success' = 'true' THEN 1 ELSE 0 END)::float / COUNT(*)::float * 100, 2
                    ) as success_rate,
                    AVG((content->>'return_pct')::float) as avg_return
                FROM AD_strands 
                WHERE kind = 'prediction_review'
                GROUP BY content->>'timeframe'
                ORDER BY success_rate DESC
            """
        }
    
    @staticmethod
    def get_example_queries() -> List[Dict[str, str]]:
        """Get example queries with parameters for testing"""
        
        return [
            {
                'name': 'BTC Volume Spike Predictions',
                'description': 'Get all BTC volume spike predictions',
                'query': """
                    SELECT * FROM AD_strands 
                    WHERE kind = 'prediction_review' 
                    AND content->>'asset' = 'BTC'
                    AND content->>'group_type' = 'single_single'
                    AND content->>'group_signature' LIKE '%volume_spike%'
                    ORDER BY created_at DESC
                """,
                'parameters': []
            },
            {
                'name': 'Successful Predictions Last 24 Hours',
                'description': 'Get all successful predictions from last 24 hours',
                'query': """
                    SELECT * FROM AD_strands 
                    WHERE kind = 'prediction_review' 
                    AND content->>'success' = 'true'
                    AND created_at >= NOW() - INTERVAL '24 hours'
                    ORDER BY created_at DESC
                """,
                'parameters': []
            },
            {
                'name': 'High Confidence Predictions',
                'description': 'Get predictions with confidence > 0.7',
                'query': """
                    SELECT * FROM AD_strands 
                    WHERE kind = 'prediction_review' 
                    AND (content->>'confidence')::float > 0.7
                    ORDER BY (content->>'confidence')::float DESC
                """,
                'parameters': []
            },
            {
                'name': 'Pattern Group Performance',
                'description': 'Get performance stats for specific pattern group',
                'query': """
                    SELECT 
                        content->>'group_signature' as group_signature,
                        COUNT(*) as total_predictions,
                        SUM(CASE WHEN content->>'success' = 'true' THEN 1 ELSE 0 END) as successful_predictions,
                        ROUND(
                            SUM(CASE WHEN content->>'success' = 'true' THEN 1 ELSE 0 END)::float / COUNT(*)::float * 100, 2
                        ) as success_rate,
                        AVG((content->>'return_pct')::float) as avg_return
                    FROM AD_strands 
                    WHERE kind = 'prediction_review'
                    AND content->>'group_signature' = %s
                    GROUP BY content->>'group_signature'
                """,
                'parameters': ['BTC_1h_volume_spike_divergence']
            }
        ]
