"""
CIL Learning System

This module integrates all CIL learning components into a unified system.
It orchestrates prediction tracking, outcome analysis, and conditional plan management.

Features:
1. Integrate prediction tracking with market data
2. Process completed predictions through outcome analysis
3. Generate and update conditional plans
4. Coordinate with universal learning system
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import asyncio

from .cil_clustering import CILClustering
from .prediction_tracker import PredictionTracker, PredictionStatus, PredictionOutcome
from .outcome_analysis_engine import OutcomeAnalysisEngine, AnalysisType
from .conditional_plan_manager import ConditionalPlanManager, PlanStatus, PlanType

logger = logging.getLogger(__name__)


class CILLearningSystem:
    """
    CIL Learning System - Orchestrates all CIL learning components
    
    This system coordinates prediction tracking, outcome analysis, and conditional plan management
    to create a complete learning loop for trading strategies.
    """
    
    def __init__(self, supabase_manager, llm_client=None):
        """
        Initialize CIL learning system
        
        Args:
            supabase_manager: Database manager
            llm_client: LLM client for advanced analysis (optional)
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.clustering = CILClustering()
        self.prediction_tracker = PredictionTracker(supabase_manager)
        self.outcome_analysis = OutcomeAnalysisEngine(supabase_manager, llm_client)
        self.plan_manager = ConditionalPlanManager(supabase_manager, llm_client)
        
        # System configuration
        self.update_interval_minutes = 5
        self.analysis_batch_size = 10
        self.min_predictions_for_analysis = 5
    
    async def start_learning_loop(self) -> None:
        """
        Start the main learning loop
        
        This runs continuously to:
        1. Update active predictions with current prices
        2. Process completed predictions for analysis
        3. Generate/update conditional plans
        4. Clean up expired predictions
        """
        self.logger.info("Starting CIL learning loop")
        
        while True:
            try:
                # Update all active predictions
                updated_count = await self.prediction_tracker.update_all_predictions()
                self.logger.info(f"Updated {updated_count} active predictions")
                
                # Process completed predictions for analysis
                analysis_count = await self.process_completed_predictions()
                self.logger.info(f"Processed {analysis_count} completed predictions")
                
                # Clean up expired predictions
                cleanup_count = await self.prediction_tracker.cleanup_expired_predictions()
                if cleanup_count > 0:
                    self.logger.info(f"Cleaned up {cleanup_count} expired predictions")
                
                # Wait before next update
                await asyncio.sleep(self.update_interval_minutes * 60)
                
            except Exception as e:
                self.logger.error(f"Error in learning loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def process_completed_predictions(self) -> int:
        """
        Process completed predictions for learning analysis
        
        Returns:
            Number of predictions processed
        """
        try:
            # Get completed predictions from database
            completed_predictions = await self._get_completed_predictions()
            
            if len(completed_predictions) < self.min_predictions_for_analysis:
                return 0
            
            # Group predictions by cluster key for batch analysis
            clustered_predictions = await self._cluster_predictions_for_analysis(completed_predictions)
            
            processed_count = 0
            for cluster_key, predictions in clustered_predictions.items():
                if len(predictions) >= self.min_predictions_for_analysis:
                    # Analyze this cluster
                    analysis_result = await self.outcome_analysis.analyze_outcome_batch(cluster_key, predictions)
                    
                    if 'error' not in analysis_result:
                        # Generate plan evolution
                        evolution = await self.outcome_analysis.generate_plan_evolution(cluster_key, analysis_result)
                        
                        # Create or update conditional plan
                        if 'error' not in evolution:
                            plan_result = await self.plan_manager.create_conditional_plan(analysis_result)
                            if 'error' not in plan_result:
                                processed_count += len(predictions)
                                self.logger.info(f"Created/updated plan for cluster {cluster_key}")
            
            return processed_count
            
        except Exception as e:
            self.logger.error(f"Error processing completed predictions: {e}")
            return 0
    
    async def track_new_prediction(self, prediction_strand: Dict[str, Any]) -> bool:
        """
        Track a new prediction
        
        Args:
            prediction_strand: Strand dictionary with prediction data
            
        Returns:
            True if tracking started successfully, False otherwise
        """
        try:
            # Start tracking the prediction
            success = await self.prediction_tracker.track_prediction(prediction_strand)
            
            if success:
                self.logger.info(f"Started tracking prediction {prediction_strand['id']}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error tracking new prediction: {e}")
            return False
    
    async def get_active_predictions(self) -> List[Dict[str, Any]]:
        """
        Get all active predictions
        
        Returns:
            List of active prediction data
        """
        try:
            predictions = await self.prediction_tracker.get_active_predictions()
            return [
                {
                    'prediction_id': p.prediction_id,
                    'symbol': p.symbol,
                    'timeframe': p.timeframe,
                    'entry_price': p.entry_price,
                    'target_price': p.target_price,
                    'stop_loss': p.stop_loss,
                    'current_price': p.current_price,
                    'max_drawdown': p.max_drawdown,
                    'time_remaining': p.time_remaining,
                    'status': p.status.value,
                    'created_at': p.created_at.isoformat()
                }
                for p in predictions
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting active predictions: {e}")
            return []
    
    async def get_active_plans(self, symbol: Optional[str] = None, timeframe: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all active conditional plans
        
        Args:
            symbol: Filter by symbol (optional)
            timeframe: Filter by timeframe (optional)
            
        Returns:
            List of active plan data
        """
        try:
            return await self.plan_manager.get_active_plans(symbol, timeframe)
            
        except Exception as e:
            self.logger.error(f"Error getting active plans: {e}")
            return []
    
    async def force_analysis(self, cluster_key: str) -> Dict[str, Any]:
        """
        Force analysis of a specific cluster
        
        Args:
            cluster_key: Clustering key to analyze
            
        Returns:
            Analysis results
        """
        try:
            # Get predictions for this cluster
            predictions = await self._get_predictions_by_cluster(cluster_key)
            
            if len(predictions) < self.min_predictions_for_analysis:
                return {'error': f'Insufficient predictions: {len(predictions)} < {self.min_predictions_for_analysis}'}
            
            # Analyze the cluster
            analysis_result = await self.outcome_analysis.analyze_outcome_batch(cluster_key, predictions)
            
            if 'error' not in analysis_result:
                # Generate plan evolution
                evolution = await self.outcome_analysis.generate_plan_evolution(cluster_key, analysis_result)
                
                # Create or update conditional plan
                if 'error' not in evolution:
                    plan_result = await self.plan_manager.create_conditional_plan(analysis_result)
                    analysis_result['plan_result'] = plan_result
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error in force analysis: {e}")
            return {'error': str(e)}
    
    async def _get_completed_predictions(self) -> List[Dict[str, Any]]:
        """Get completed predictions from database"""
        try:
            # Query for completed predictions
            result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction').eq('tracking_status', 'completed').execute()
            
            if result.data:
                return result.data
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting completed predictions: {e}")
            return []
    
    async def _cluster_predictions_for_analysis(self, predictions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Cluster predictions for batch analysis"""
        try:
            clustered = {}
            
            for prediction in predictions:
                # Generate cluster key based on trading characteristics
                cluster_key = self._generate_prediction_cluster_key(prediction)
                
                if cluster_key not in clustered:
                    clustered[cluster_key] = []
                
                clustered[cluster_key].append(prediction)
            
            return clustered
            
        except Exception as e:
            self.logger.error(f"Error clustering predictions: {e}")
            return {}
    
    async def _get_predictions_by_cluster(self, cluster_key: str) -> List[Dict[str, Any]]:
        """Get predictions by cluster key"""
        try:
            # Query for predictions with this cluster key
            result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction').eq('cluster_key', cluster_key).execute()
            
            if result.data:
                return result.data
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting predictions by cluster: {e}")
            return []
    
    def _generate_prediction_cluster_key(self, prediction: Dict[str, Any]) -> str:
        """Generate cluster key for prediction"""
        try:
            key_parts = [
                prediction.get('symbol', 'unknown'),
                prediction.get('timeframe', 'unknown'),
                prediction.get('pattern_type', 'unknown'),
                prediction.get('strength_range', 'unknown'),
                prediction.get('rr_profile', 'unknown'),
                prediction.get('market_conditions', 'unknown')
            ]
            
            return '_'.join(str(part) for part in key_parts)
            
        except Exception as e:
            self.logger.error(f"Error generating cluster key: {e}")
            return 'unknown_cluster'


# Example usage and testing
if __name__ == "__main__":
    # Test the CIL learning system
    from src.utils.supabase_manager import SupabaseManager
    
    async def test_cil_learning_system():
        supabase_manager = SupabaseManager()
        learning_system = CILLearningSystem(supabase_manager)
        
        # Test prediction tracking
        prediction_strand = {
            'id': 'test_prediction_1',
            'kind': 'prediction',
            'symbol': 'BTC',
            'timeframe': '1h',
            'pattern_type': 'volume_spike',
            'strength_range': 'strong',
            'rr_profile': 'moderate',
            'market_conditions': 'moderate_volatility',
            'prediction_data': {
                'entry_price': 50000.0,
                'target_price': 52000.0,
                'stop_loss': 48000.0,
                'max_time': 120
            }
        }
        
        # Test tracking
        success = await learning_system.track_new_prediction(prediction_strand)
        print(f"Prediction tracking started: {success}")
        
        # Test getting active predictions
        active_predictions = await learning_system.get_active_predictions()
        print(f"Active predictions: {len(active_predictions)}")
        
        # Test getting active plans
        active_plans = await learning_system.get_active_plans()
        print(f"Active plans: {len(active_plans)}")
    
    import asyncio
    asyncio.run(test_cil_learning_system())
