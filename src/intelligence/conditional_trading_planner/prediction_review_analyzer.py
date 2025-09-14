"""
Prediction Review Analyzer

Analyzes prediction review strands to extract pattern information and 
identify relevant clusters for trading plan creation.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


class PredictionReviewAnalyzer:
    """
    Analyzes prediction review strands to extract trading-relevant information.
    
    Responsibilities:
    1. Extract pattern information from prediction reviews
    2. Identify relevant clusters for historical analysis
    3. Calculate performance metrics
    4. Prepare data for trading plan generation
    """
    
    def __init__(self, supabase_manager, llm_client):
        """
        Initialize prediction review analyzer.
        
        Args:
            supabase_manager: Database manager for strand operations
            llm_client: LLM client for analysis
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(f"{__name__}.prediction_analyzer")
    
    async def analyze_prediction_review(self, prediction_review_id: str) -> Optional[Dict[str, Any]]:
        """
        Analyze a prediction review strand and extract trading-relevant information.
        
        Args:
            prediction_review_id: ID of the prediction review strand
            
        Returns:
            Analysis dictionary with pattern info, clusters, and performance metrics
        """
        try:
            self.logger.info(f"Analyzing prediction review: {prediction_review_id}")
            
            # Step 1: Get prediction review strand
            prediction_review = await self._get_prediction_review(prediction_review_id)
            if not prediction_review:
                self.logger.error(f"Prediction review not found: {prediction_review_id}")
                return None
            
            # Step 2: Extract pattern information
            pattern_info = self._extract_pattern_information(prediction_review)
            
            # Step 3: Identify relevant clusters
            relevant_clusters = await self._identify_relevant_clusters(pattern_info)
            
            # Step 4: Calculate historical performance
            historical_performance = await self._calculate_historical_performance(relevant_clusters)
            
            # Step 5: Extract cluster keys from prediction review
            cluster_keys = prediction_review.get('cluster_key', [])
            
            # Step 6: Prepare analysis result
            analysis = {
                "prediction_review_id": prediction_review_id,
                "pattern_info": pattern_info,
                "relevant_clusters": relevant_clusters,
                "historical_performance": historical_performance,
                "prediction_review_cluster_keys": cluster_keys,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.logger.info(f"Analysis completed for: {prediction_review_id}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing prediction review {prediction_review_id}: {e}")
            return None
    
    async def _get_prediction_review(self, prediction_review_id: str) -> Optional[Dict[str, Any]]:
        """Get prediction review strand from database."""
        try:
            result = self.supabase_manager.client.table('ad_strands').select('*').eq('id', prediction_review_id).eq('kind', 'prediction_review').execute()
            
            if result.data:
                return result.data[0]
            else:
                self.logger.warning(f"Prediction review not found: {prediction_review_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting prediction review {prediction_review_id}: {e}")
            return None
    
    def _extract_pattern_information(self, prediction_review: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract pattern information from prediction review strand.
        
        Args:
            prediction_review: Prediction review strand data
            
        Returns:
            Dictionary with extracted pattern information
        """
        try:
            content = prediction_review.get('content', {})
            module_intelligence = prediction_review.get('module_intelligence', {})
            
            # Helper function to get value from either field
            def get_value(key: str, default=None):
                if content.get(key) is not None:
                    return content.get(key, default)
                return module_intelligence.get(key, default)
            
            # Extract pattern information
            pattern_info = {
                "group_signature": get_value('group_signature', 'unknown'),
                "asset": get_value('asset', 'unknown'),
                "timeframe": get_value('timeframe', 'unknown'),
                "pattern_types": get_value('pattern_types', []),
                "group_type": get_value('group_type', 'unknown'),
                "method": get_value('method', 'unknown'),
                "confidence": get_value('confidence', 0.0),
                "success": get_value('success', False),
                "return_pct": get_value('return_pct', 0.0),
                "max_drawdown": get_value('max_drawdown', 0.0),
                "duration_hours": get_value('duration_hours', 0.0),
                "original_pattern_strand_ids": get_value('original_pattern_strand_ids', [])
            }
            
            return pattern_info
            
        except Exception as e:
            self.logger.error(f"Error extracting pattern information: {e}")
            return {}
    
    async def _identify_relevant_clusters(self, pattern_info: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Identify relevant clusters for historical analysis.
        
        Args:
            pattern_info: Extracted pattern information
            
        Returns:
            Dictionary mapping cluster types to cluster keys
        """
        try:
            relevant_clusters = {}
            
            # Pattern+Timeframe cluster
            if pattern_info.get('group_signature'):
                relevant_clusters['pattern_timeframe'] = [pattern_info['group_signature']]
            
            # Asset cluster
            if pattern_info.get('asset'):
                relevant_clusters['asset'] = [pattern_info['asset']]
            
            # Timeframe cluster
            if pattern_info.get('timeframe'):
                relevant_clusters['timeframe'] = [pattern_info['timeframe']]
            
            # Pattern type cluster
            if pattern_info.get('group_type'):
                relevant_clusters['pattern'] = [pattern_info['group_type']]
            
            # Group type cluster
            if pattern_info.get('group_type'):
                relevant_clusters['group_type'] = [pattern_info['group_type']]
            
            # Method cluster
            if pattern_info.get('method'):
                relevant_clusters['method'] = [pattern_info['method']]
            
            # Outcome cluster
            if pattern_info.get('success') is not None:
                outcome = 'success' if pattern_info['success'] else 'failure'
                relevant_clusters['outcome'] = [outcome]
            
            return relevant_clusters
            
        except Exception as e:
            self.logger.error(f"Error identifying relevant clusters: {e}")
            return {}
    
    async def _calculate_historical_performance(self, relevant_clusters: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Calculate historical performance metrics for relevant clusters.
        
        Args:
            relevant_clusters: Dictionary of cluster types and keys
            
        Returns:
            Dictionary with historical performance metrics
        """
        try:
            performance_metrics = {}
            
            for cluster_type, cluster_keys in relevant_clusters.items():
                for cluster_key in cluster_keys:
                    # Query historical prediction reviews for this cluster
                    historical_reviews = await self._get_historical_reviews(cluster_type, cluster_key)
                    
                    if historical_reviews:
                        metrics = self._calculate_cluster_metrics(historical_reviews)
                        performance_metrics[f"{cluster_type}_{cluster_key}"] = metrics
            
            return performance_metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating historical performance: {e}")
            return {}
    
    async def _get_historical_reviews(self, cluster_type: str, cluster_key: str) -> List[Dict[str, Any]]:
        """Get historical prediction reviews for a specific cluster."""
        try:
            # Query prediction reviews that match this cluster
            if cluster_type == 'pattern_timeframe':
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').contains('content', {'group_signature': cluster_key}).execute()
            elif cluster_type == 'asset':
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').contains('content', {'asset': cluster_key}).execute()
            elif cluster_type == 'timeframe':
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').contains('content', {'timeframe': cluster_key}).execute()
            elif cluster_type == 'pattern':
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').contains('content', {'group_type': cluster_key}).execute()
            elif cluster_type == 'group_type':
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').contains('content', {'group_type': cluster_key}).execute()
            elif cluster_type == 'method':
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').contains('content', {'method': cluster_key}).execute()
            elif cluster_type == 'outcome':
                success_value = cluster_key == 'success'
                result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').contains('content', {'success': success_value}).execute()
            else:
                return []
            
            return result.data if result.data else []
            
        except Exception as e:
            self.logger.error(f"Error getting historical reviews for {cluster_type}:{cluster_key}: {e}")
            return []
    
    def _calculate_cluster_metrics(self, historical_reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance metrics for a cluster of historical reviews."""
        try:
            if not historical_reviews:
                return {}
            
            # Helper function to get value from content or module_intelligence
            def get_value(review: Dict[str, Any], key: str, default=0):
                content = review.get('content', {})
                if content.get(key) is not None:
                    return content.get(key, default)
                module_intelligence = review.get('module_intelligence', {})
                return module_intelligence.get(key, default)
            
            # Calculate metrics
            total_reviews = len(historical_reviews)
            success_count = sum(1 for review in historical_reviews if get_value(review, 'success', False))
            success_rate = success_count / total_reviews if total_reviews > 0 else 0
            
            returns = [get_value(review, 'return_pct', 0) for review in historical_reviews]
            avg_return = sum(returns) / len(returns) if returns else 0
            
            confidences = [get_value(review, 'confidence', 0) for review in historical_reviews]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            drawdowns = [get_value(review, 'max_drawdown', 0) for review in historical_reviews]
            avg_drawdown = sum(drawdowns) / len(drawdowns) if drawdowns else 0
            
            durations = [get_value(review, 'duration_hours', 0) for review in historical_reviews]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return {
                "total_reviews": total_reviews,
                "success_count": success_count,
                "success_rate": success_rate,
                "avg_return": avg_return,
                "avg_confidence": avg_confidence,
                "avg_drawdown": avg_drawdown,
                "avg_duration": avg_duration,
                "max_return": max(returns) if returns else 0,
                "min_return": min(returns) if returns else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating cluster metrics: {e}")
            return {}
