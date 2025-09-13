"""
Clean CIL Module - Option 2 Implementation

CIL handles both:
1. Processing pattern strands → creating predictions
2. Checking finalized predictions → creating prediction_review strands

This is the cleanest approach - one module, one responsibility, event-driven.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CleanCILModule:
    """
    Clean CIL Module - Option 2 Implementation
    
    Single responsibility: Process pattern strands and create prediction reviews
    Triggered by: pattern strands from RDI
    Creates: predictions + prediction_review strands
    """
    
    def __init__(self, supabase_manager, llm_client):
        """
        Initialize clean CIL module
        
        Args:
            supabase_manager: Database manager
            llm_client: LLM client manager for analysis
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # Import required components
        from Modules.Alpha_Detector.src.intelligence.system_control.central_intelligence_layer.prediction_engine import PredictionEngine
        from cil_prediction_review_creator import CILPredictionReviewCreator
        
        self.prediction_engine = PredictionEngine(supabase_manager, llm_client)
        self.review_creator = CILPredictionReviewCreator(supabase_manager, llm_client)
    
    async def process_pattern_strand(self, pattern_strand: Dict[str, Any]) -> bool:
        """
        Process a pattern strand - this is the main entry point
        
        Args:
            pattern_strand: Pattern strand from RDI
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            strand_id = pattern_strand.get('id')
            self.logger.info(f"🎯 CIL processing pattern strand: {strand_id}")
            
            # 1. Process pattern strand → create predictions
            prediction_ids = await self.prediction_engine.process_pattern_overview(pattern_strand)
            
            if prediction_ids:
                self.logger.info(f"✅ Created {len(prediction_ids)} predictions from pattern {strand_id}")
                
                # Start tracking predictions
                for prediction_id in prediction_ids:
                    await self._start_tracking_prediction(prediction_id)
            else:
                self.logger.warning(f"⚠️  No predictions created from pattern {strand_id}")
            
            # 2. Check for finalized predictions → create prediction_review strands
            review_count = await self.review_creator.process_finalized_predictions()
            
            if review_count > 0:
                self.logger.info(f"✅ Created {review_count} prediction_review strands from finalized predictions")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error processing pattern strand {strand_id}: {e}")
            return False
    
    async def _start_tracking_prediction(self, prediction_id: str) -> None:
        """Start tracking a prediction for future review"""
        try:
            # Update prediction status to 'tracking'
            await self.supabase_manager.client.table('ad_strands').update({
                'tracking_status': 'tracking',
                'tracking_started_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', prediction_id).execute()
            
            self.logger.debug(f"Started tracking prediction: {prediction_id}")
            
        except Exception as e:
            self.logger.error(f"Error starting prediction tracking: {e}")
    
    async def get_module_status(self) -> Dict[str, Any]:
        """Get current module status"""
        try:
            # Get counts of different strand types
            pattern_count = await self._get_strand_count('pattern')
            prediction_count = await self._get_strand_count('prediction')
            review_count = await self._get_strand_count('prediction_review')
            
            return {
                'module': 'CIL',
                'status': 'active',
                'pattern_strands': pattern_count,
                'prediction_strands': prediction_count,
                'prediction_review_strands': review_count,
                'last_processed': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting module status: {e}")
            return {'module': 'CIL', 'status': 'error', 'error': str(e)}
    
    async def _get_strand_count(self, kind: str) -> int:
        """Get count of strands by kind"""
        try:
            result = self.supabase_manager.client.table('ad_strands').select('id', count='exact').eq('kind', kind).execute()
            return result.count or 0
        except Exception as e:
            self.logger.error(f"Error getting strand count for {kind}: {e}")
            return 0
