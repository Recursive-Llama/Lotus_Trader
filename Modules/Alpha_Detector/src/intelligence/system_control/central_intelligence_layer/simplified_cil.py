"""
Simplified CIL - Main Orchestrator

Simplified Central Intelligence Layer with 5 core components:
1. Prediction Engine - Main prediction creation and tracking
2. Learning System - Continuous learning from predictions
3. Prediction Tracker - Track all predictions and outcomes
4. Outcome Analysis - Analyze completed predictions
5. Conditional Plan Manager - Create trading plans from confident patterns
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from .prediction_engine import PredictionEngine
from .engines.learning_feedback_engine import LearningFeedbackEngine
from .engines.prediction_outcome_tracker import PredictionOutcomeTracker
from .core.cil_plan_composer import CILPlanComposer


class SimplifiedCIL:
    """
    Simplified Central Intelligence Layer
    
    Main orchestrator that processes pattern_overview strands and creates predictions
    with continuous learning and plan generation.
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(f"{__name__}.simplified_cil")
        
        # Core components
        self.prediction_engine = PredictionEngine(supabase_manager, llm_client)
        self.learning_system = LearningFeedbackEngine(supabase_manager, llm_client)
        self.prediction_tracker = PredictionOutcomeTracker(supabase_manager, llm_client)
        self.outcome_analyzer = OutcomeAnalyzer(supabase_manager)
        self.plan_manager = CILPlanComposer(supabase_manager, llm_client)
        
        # CIL state
        self.is_running = False
        self.last_processing_time = None
        
        # Processing intervals
        self.pattern_processing_interval = timedelta(minutes=5)  # Process every 5 minutes
        self.learning_interval = timedelta(minutes=10)  # Learning every 10 minutes
        
    async def start(self):
        """Start the simplified CIL system"""
        try:
            self.is_running = True
            self.logger.info("Starting Simplified CIL system")
            
            # Start background tasks
            asyncio.create_task(self._pattern_processing_loop())
            asyncio.create_task(self._learning_loop())
            
            self.logger.info("Simplified CIL system started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting Simplified CIL: {e}")
            self.is_running = False
    
    async def stop(self):
        """Stop the simplified CIL system"""
        self.is_running = False
        self.logger.info("Simplified CIL system stopped")
    
    async def _pattern_processing_loop(self):
        """Background loop to process pattern_overview strands"""
        while self.is_running:
            try:
                await self.process_pattern_overviews()
                await asyncio.sleep(self.pattern_processing_interval.total_seconds())
            except Exception as e:
                self.logger.error(f"Error in pattern processing loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _learning_loop(self):
        """Background loop for continuous learning"""
        while self.is_running:
            try:
                await self.process_learning_cycle()
                await asyncio.sleep(self.learning_interval.total_seconds())
            except Exception as e:
                self.logger.error(f"Error in learning loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def process_pattern_overviews(self):
        """Process all pending pattern_overview strands"""
        try:
            # Get pattern_overview strands tagged for CIL
            overview_strands = await self.get_cil_tagged_overviews()
            
            if not overview_strands:
                return
            
            self.logger.info(f"Processing {len(overview_strands)} pattern overviews")
            
            # Process each overview
            for overview_strand in overview_strands:
                try:
                    prediction_ids = await self.prediction_engine.process_pattern_overview(overview_strand)
                    
                    if prediction_ids:
                        self.logger.info(f"Created {len(prediction_ids)} predictions from overview {overview_strand.get('id')}")
                        
                        # Start tracking predictions
                        for prediction_id in prediction_ids:
                            await self.prediction_tracker.track_prediction(prediction_id)
                    
                except Exception as e:
                    self.logger.error(f"Error processing overview {overview_strand.get('id')}: {e}")
            
            self.last_processing_time = datetime.now(timezone.utc)
            
        except Exception as e:
            self.logger.error(f"Error processing pattern overviews: {e}")
    
    async def process_learning_cycle(self):
        """Process learning cycle for completed predictions"""
        try:
            # Get completed predictions
            completed_predictions = await self.get_completed_predictions()
            
            if not completed_predictions:
                return
            
            self.logger.info(f"Processing learning cycle for {len(completed_predictions)} completed predictions")
            
            # Process each completed prediction
            for prediction in completed_predictions:
                try:
                    # Analyze outcome
                    analysis = await self.outcome_analyzer.analyze_completed_prediction(prediction['id'])
                    
                    # Update learning system
                    await self.learning_system.process_prediction_outcome(analysis)
                    
                    # Check if we should create conditional plans
                    if self.should_create_conditional_plan(analysis):
                        await self.plan_manager.create_conditional_plan(analysis)
                    
                except Exception as e:
                    self.logger.error(f"Error processing prediction {prediction['id']}: {e}")
            
        except Exception as e:
            self.logger.error(f"Error in learning cycle: {e}")
    
    async def get_cil_tagged_overviews(self) -> List[Dict[str, Any]]:
        """Get pattern_overview strands tagged for CIL processing"""
        try:
            query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'pattern_overview' 
                AND 'cil' = ANY(tags)
                AND created_at > %s
                ORDER BY created_at DESC
                LIMIT 50
            """
            
            # Get overviews from last hour
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
            result = await self.supabase_manager.execute_query(query, [cutoff_time])
            
            return [dict(row) for row in result]
            
        except Exception as e:
            self.logger.error(f"Error getting CIL tagged overviews: {e}")
            return []
    
    async def get_completed_predictions(self) -> List[Dict[str, Any]]:
        """Get completed predictions for learning"""
        try:
            query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'prediction' 
                AND tracking_status = 'completed'
                AND created_at > %s
                ORDER BY created_at DESC
                LIMIT 100
            """
            
            # Get predictions from last 24 hours
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            result = await self.supabase_manager.execute_query(query, [cutoff_time])
            
            return [dict(row) for row in result]
            
        except Exception as e:
            self.logger.error(f"Error getting completed predictions: {e}")
            return []
    
    def should_create_conditional_plan(self, analysis: Dict[str, Any]) -> bool:
        """Determine if we should create a conditional plan based on analysis"""
        # TODO: Implement conditional plan logic
        success_rate = analysis.get('success_rate', 0.0)
        confidence = analysis.get('confidence', 0.0)
        
        return success_rate >= 0.6 and confidence >= 0.7
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            'is_running': self.is_running,
            'last_processing_time': self.last_processing_time,
            'prediction_engine_status': 'active',
            'learning_system_status': 'active',
            'prediction_tracker_status': 'active',
            'outcome_analyzer_status': 'active',
            'plan_manager_status': 'active'
        }


class OutcomeAnalyzer:
    """Analyze completed predictions for learning"""
    
    def __init__(self, supabase_manager: SupabaseManager):
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(f"{__name__}.outcome_analyzer")
    
    async def analyze_completed_prediction(self, prediction_id: str) -> Dict[str, Any]:
        """Analyze a completed prediction"""
        try:
            # Get prediction data
            prediction = await self.get_prediction(prediction_id)
            
            if not prediction:
                return {'error': 'Prediction not found'}
            
            # Analyze outcome
            analysis = {
                'prediction_id': prediction_id,
                'success_rate': self.calculate_success_rate(prediction),
                'confidence': prediction.get('confidence', 0.0),
                'outcome_score': prediction.get('outcome_score', 0.0),
                'pattern_group': prediction.get('pattern_group', {}),
                'context_metadata': prediction.get('context_metadata', {}),
                'analysis_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing prediction {prediction_id}: {e}")
            return {'error': str(e)}
    
    async def get_prediction(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        """Get prediction data from database"""
        try:
            query = "SELECT * FROM AD_strands WHERE id = %s AND kind = 'prediction'"
            result = await self.supabase_manager.execute_query(query, [prediction_id])
            
            if result:
                return dict(result[0])
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting prediction {prediction_id}: {e}")
            return None
    
    def calculate_success_rate(self, prediction: Dict[str, Any]) -> float:
        """Calculate success rate for prediction"""
        # TODO: Implement success rate calculation
        return prediction.get('outcome_score', 0.0)
