"""
CIL Prediction Review Creator

This is the missing piece! When CIL predictions are finalized,
this creates prediction_review strands for the learning system.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CILPredictionReviewCreator:
    """
    Creates prediction_review strands when CIL predictions are finalized
    
    This is the missing piece in the CIL data flow:
    1. CIL creates predictions (kind: 'prediction')
    2. PredictionTracker tracks them until completion
    3. When finalized, THIS creates prediction_review strands (kind: 'prediction_review')
    4. Learning system processes prediction_review strands
    """
    
    def __init__(self, supabase_manager, llm_client):
        """
        Initialize prediction review creator
        
        Args:
            supabase_manager: Database manager
            llm_client: LLM client for analysis
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # Import prediction engine for review creation
        from Modules.Alpha_Detector.src.intelligence.system_control.central_intelligence_layer.prediction_engine import PredictionEngine
        self.prediction_engine = PredictionEngine(supabase_manager, llm_client)
    
    async def create_prediction_review_from_finalized_prediction(self, prediction_strand: Dict[str, Any]) -> Optional[str]:
        """
        Create prediction_review strand from finalized prediction
        
        Args:
            prediction_strand: Finalized prediction strand with outcome data
            
        Returns:
            prediction_review strand ID if created successfully, None otherwise
        """
        try:
            prediction_id = prediction_strand.get('id')
            self.logger.info(f"Creating prediction review for finalized prediction: {prediction_id}")
            
            # Extract prediction data
            prediction_data = prediction_strand.get('prediction_data', {})
            outcome_data = prediction_strand.get('outcome_data', {})
            
            if not prediction_data or not outcome_data:
                self.logger.error(f"Missing prediction or outcome data for {prediction_id}")
                return None
            
            # Create outcome dictionary for prediction engine
            outcome = {
                'success': self._determine_success(outcome_data),
                'return_pct': self._calculate_return_pct(prediction_data, outcome_data),
                'max_drawdown': outcome_data.get('max_drawdown', 0.0),
                'duration_hours': outcome_data.get('duration_minutes', 0) / 60,
                'outcome_type': outcome_data.get('outcome', 'expired'),
                'final_price': outcome_data.get('final_price', 0.0),
                'final_at': outcome_data.get('final_at', '')
            }
            
            # Create prediction dictionary for prediction engine
            prediction = {
                'id': prediction_id,
                'pattern_group': self._extract_pattern_group(prediction_strand),
                'code_prediction': self._extract_code_prediction(prediction_data),
                'llm_prediction': self._extract_llm_prediction(prediction_data),
                'confidence': prediction_data.get('confidence', 0.5),
                'method': prediction_data.get('method', 'unknown')
            }
            
            # Use prediction engine to create review strand
            review_strand_id = await self.prediction_engine.create_prediction_review_strand(prediction, outcome)
            
            if review_strand_id:
                self.logger.info(f"✅ Created prediction_review strand: {review_strand_id}")
                return review_strand_id
            else:
                self.logger.error(f"❌ Failed to create prediction_review strand for {prediction_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating prediction review: {e}")
            return None
    
    def _determine_success(self, outcome_data: Dict[str, Any]) -> bool:
        """Determine if prediction was successful"""
        outcome_type = outcome_data.get('outcome', 'expired')
        return outcome_type in ['target_hit', 'TARGET_HIT']
    
    def _calculate_return_pct(self, prediction_data: Dict[str, Any], outcome_data: Dict[str, Any]) -> float:
        """Calculate return percentage"""
        try:
            entry_price = prediction_data.get('entry_price', 0.0)
            final_price = outcome_data.get('final_price', 0.0)
            
            if entry_price == 0:
                return 0.0
            
            return ((final_price - entry_price) / entry_price) * 100
            
        except Exception as e:
            self.logger.error(f"Error calculating return percentage: {e}")
            return 0.0
    
    def _extract_pattern_group(self, prediction_strand: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pattern group from prediction strand"""
        try:
            content = prediction_strand.get('content', {})
            pattern_group = content.get('pattern_group', {})
            
            if not pattern_group:
                # Create minimal pattern group if missing
                return {
                    'asset': prediction_strand.get('symbol', 'UNKNOWN'),
                    'timeframe': prediction_strand.get('timeframe', '1h'),
                    'group_type': 'single_single',
                    'patterns': [{'pattern_type': 'unknown', 'confidence': 0.5}]
                }
            
            return pattern_group
            
        except Exception as e:
            self.logger.error(f"Error extracting pattern group: {e}")
            return {
                'asset': prediction_strand.get('symbol', 'UNKNOWN'),
                'timeframe': prediction_strand.get('timeframe', '1h'),
                'group_type': 'single_single',
                'patterns': [{'pattern_type': 'unknown', 'confidence': 0.5}]
            }
    
    def _extract_code_prediction(self, prediction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract code prediction from prediction data"""
        try:
            content = prediction_data.get('content', {})
            code_prediction = content.get('code_prediction', {})
            
            if not code_prediction:
                # Create minimal code prediction if missing
                return {
                    'method': 'code',
                    'target_price': prediction_data.get('target_price', 0.0),
                    'stop_loss': prediction_data.get('stop_loss', 0.0),
                    'confidence': prediction_data.get('confidence', 0.5),
                    'direction': 'long',
                    'duration_hours': 20
                }
            
            return code_prediction
            
        except Exception as e:
            self.logger.error(f"Error extracting code prediction: {e}")
            return {
                'method': 'code',
                'target_price': prediction_data.get('target_price', 0.0),
                'stop_loss': prediction_data.get('stop_loss', 0.0),
                'confidence': prediction_data.get('confidence', 0.5),
                'direction': 'long',
                'duration_hours': 20
            }
    
    def _extract_llm_prediction(self, prediction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract LLM prediction from prediction data"""
        try:
            content = prediction_data.get('content', {})
            llm_prediction = content.get('llm_prediction', {})
            
            if not llm_prediction:
                # Create minimal LLM prediction if missing
                return {
                    'method': 'llm',
                    'target_price': prediction_data.get('target_price', 0.0),
                    'stop_loss': prediction_data.get('stop_loss', 0.0),
                    'confidence': prediction_data.get('confidence', 0.5),
                    'direction': 'long',
                    'duration_hours': 20,
                    'reasoning': 'LLM prediction based on pattern analysis'
                }
            
            return llm_prediction
            
        except Exception as e:
            self.logger.error(f"Error extracting LLM prediction: {e}")
            return {
                'method': 'llm',
                'target_price': prediction_data.get('target_price', 0.0),
                'stop_loss': prediction_data.get('stop_loss', 0.0),
                'confidence': prediction_data.get('confidence', 0.5),
                'direction': 'long',
                'duration_hours': 20,
                'reasoning': 'LLM prediction based on pattern analysis'
            }
    
    async def process_finalized_predictions(self) -> int:
        """
        Process all finalized predictions and create prediction_review strands
        
        Returns:
            Number of prediction_review strands created
        """
        try:
            # Get all finalized predictions
            result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction').eq('tracking_status', 'completed').execute()
            
            if not result.data:
                self.logger.info("No finalized predictions found")
                return 0
            
            created_count = 0
            
            for prediction_strand in result.data:
                try:
                    # Check if prediction_review already exists
                    review_exists = await self._check_review_exists(prediction_strand['id'])
                    if review_exists:
                        self.logger.debug(f"Prediction review already exists for {prediction_strand['id']}")
                        continue
                    
                    # Create prediction review
                    review_id = await self.create_prediction_review_from_finalized_prediction(prediction_strand)
                    if review_id:
                        created_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing prediction {prediction_strand['id']}: {e}")
                    continue
            
            self.logger.info(f"Created {created_count} prediction_review strands from finalized predictions")
            return created_count
            
        except Exception as e:
            self.logger.error(f"Error processing finalized predictions: {e}")
            return 0
    
    async def _check_review_exists(self, prediction_id: str) -> bool:
        """Check if prediction review already exists for this prediction"""
        try:
            result = self.supabase_manager.client.table('ad_strands').select('id').eq('kind', 'prediction_review').contains('content', {'prediction_id': prediction_id}).execute()
            return len(result.data) > 0
            
        except Exception as e:
            self.logger.error(f"Error checking if review exists: {e}")
            return False
