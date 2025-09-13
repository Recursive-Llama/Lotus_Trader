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
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'Modules', 'Alpha_Detector', 'src'))
from utils.supabase_manager import SupabaseManager
from llm_integration.openrouter_client import OpenRouterClient
from .prediction_engine import PredictionEngine
from .per_cluster_learning_system import PerClusterLearningSystem
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'Modules', 'Alpha_Detector', 'src'))
from intelligence.advanced_cil.legacy_cil.engines.prediction_outcome_tracker import PredictionOutcomeTracker
from intelligence.advanced_cil.legacy_cil.core.cil_plan_composer import CILPlanComposer


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
        self.learning_system = PerClusterLearningSystem(supabase_manager, llm_client)
        self.prediction_tracker = PredictionOutcomeTracker(supabase_manager, llm_client)
        self.outcome_analyzer = OutcomeAnalyzer(supabase_manager)
        self.plan_manager = CILPlanComposer(supabase_manager, llm_client)
        
        # CIL state
        self.is_running = False
        self.last_processing_time = None
        
        # Processing intervals
        self.pattern_processing_interval = timedelta(minutes=5)  # Process every 5 minutes
        self.learning_interval = timedelta(minutes=10)  # Learning every 10 minutes
        
        # Learning thresholds - learn from both success and failure
        self.learning_thresholds = {
            'min_predictions_for_learning': 3,  # Any 3 predictions (success or failure)
            'min_confidence': 0.1,  # Very low threshold - include all attempts
            'min_sample_size': 3  # Minimum sample size for statistical significance
        }
        
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
                    
                    # Update learning system - process all clusters
                    await self.learning_system.process_all_clusters()
                    
                    # Check if we should create conditional plans
                    if self.should_create_conditional_plan(analysis):
                        await self.plan_manager.create_conditional_plan(analysis)
                    
                except Exception as e:
                    self.logger.error(f"Error processing prediction {prediction['id']}: {e}")
            
            # Process group-level learning
            await self.process_group_learning()
            
        except Exception as e:
            self.logger.error(f"Error in learning cycle: {e}")
    
    async def process_group_learning(self):
        """Process group-level learning for pattern groups"""
        try:
            # Get all pattern groups that have predictions
            pattern_groups = await self.get_pattern_groups_with_predictions()
            
            for pattern_group in pattern_groups:
                try:
                    # Analyze group performance
                    group_analysis = await self.outcome_analyzer.analyze_prediction_group(pattern_group)
                    
                    # Update learning system with group insights
                    await self.learning_system.process_all_clusters()
                    
                    # Check if group meets learning thresholds
                    if self.meets_learning_thresholds(group_analysis):
                        await self.trigger_group_learning(pattern_group, group_analysis)
                    
                except Exception as e:
                    self.logger.error(f"Error processing group learning for {pattern_group}: {e}")
            
        except Exception as e:
            self.logger.error(f"Error in group learning: {e}")
    
    async def process_patterns(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process patterns and create predictions"""
        try:
            predictions = []
            for pattern in patterns:
                # Create prediction from pattern
                prediction = await self.prediction_engine.create_prediction_from_pattern(pattern)
                if prediction:
                    predictions.append(prediction)
            return predictions
        except Exception as e:
            self.logger.error(f"Error processing patterns: {e}")
            return []
    
    async def get_pattern_groups_with_predictions(self) -> List[Dict[str, Any]]:
        """Get all pattern groups that have predictions"""
        try:
            # This would query for unique pattern groups from predictions
            # For now, return empty list since database queries aren't working
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting pattern groups: {e}")
            return []
    
    def meets_learning_thresholds(self, group_analysis: Dict[str, Any]) -> bool:
        """Check if group meets learning thresholds - learn from both success and failure"""
        try:
            total_predictions = group_analysis.get('total_predictions', 0)
            avg_confidence = group_analysis.get('avg_confidence', 0.0)
            
            # Learn from any predictions (success or failure) as long as we have enough data
            return (total_predictions >= self.learning_thresholds['min_predictions_for_learning'] and
                    avg_confidence >= self.learning_thresholds['min_confidence'])
            
        except Exception as e:
            self.logger.error(f"Error checking learning thresholds: {e}")
            return False
    
    async def trigger_group_learning(self, pattern_group: Dict[str, Any], group_analysis: Dict[str, Any]):
        """Trigger learning for a pattern group that meets thresholds"""
        try:
            self.logger.info(f"Triggering group learning for {pattern_group['asset']} {pattern_group['group_type']}")
            
            # Create learning strand
            learning_strand = {
                'id': f"learning_{int(datetime.now().timestamp())}",
                'kind': 'learning_insight',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'tags': ['cil', 'learning', 'pattern_group'],
                'content': {
                    'pattern_group': pattern_group,
                    'group_analysis': group_analysis,
                    'learning_type': 'pattern_group_insight',
                    'confidence_level': group_analysis.get('avg_confidence', 0.0),
                    'success_rate': group_analysis.get('success_rate', 0.0),
                    'total_predictions': group_analysis.get('total_predictions', 0)
                },
                'metadata': {
                    'asset': pattern_group['asset'],
                    'group_type': pattern_group['group_type'],
                    'timeframe': pattern_group.get('timeframe', 'N/A'),
                    'learning_quality': self.assess_learning_quality(group_analysis)
                }
            }
            
            # Store learning strand
            await self.supabase_manager.execute_query("""
                INSERT INTO AD_strands (id, kind, created_at, tags, content, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [
                learning_strand['id'],
                learning_strand['kind'],
                learning_strand['created_at'],
                learning_strand['tags'],
                json.dumps(learning_strand['content']),
                json.dumps(learning_strand['metadata'])
            ])
            
            self.logger.info(f"Created learning strand: {learning_strand['id']}")
            
        except Exception as e:
            self.logger.error(f"Error triggering group learning: {e}")
    
    def assess_learning_quality(self, group_analysis: Dict[str, Any]) -> str:
        """Assess the quality of learning based on group analysis"""
        try:
            total_predictions = group_analysis.get('total_predictions', 0)
            success_rate = group_analysis.get('success_rate', 0.0)
            avg_confidence = group_analysis.get('avg_confidence', 0.0)
            
            if total_predictions >= 10 and success_rate >= 0.6 and avg_confidence >= 0.7:
                return 'high_quality'
            elif total_predictions >= 5 and success_rate >= 0.5 and avg_confidence >= 0.5:
                return 'medium_quality'
            else:
                return 'low_quality'
                
        except Exception as e:
            self.logger.error(f"Error assessing learning quality: {e}")
            return 'unknown'
    
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
        
        # Analysis thresholds
        self.analysis_thresholds = {
            'min_predictions_for_analysis': 3,
            'min_success_rate': 0.4,
            'min_confidence': 0.3
        }
    
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
                'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
                'analysis_quality': self.assess_analysis_quality(prediction)
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing prediction {prediction_id}: {e}")
            return {'error': str(e)}
    
    async def analyze_prediction_group(self, pattern_group: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze all predictions for a pattern group"""
        try:
            # Get all predictions for this pattern group
            predictions = await self.get_predictions_for_group(pattern_group)
            
            if not predictions:
                return {'error': 'No predictions found for group'}
            
            # Analyze group performance
            group_analysis = {
                'pattern_group': pattern_group,
                'total_predictions': len(predictions),
                'successful_predictions': len([p for p in predictions if p.get('outcome_score', 0) > 0]),
                'avg_confidence': sum(p.get('confidence', 0) for p in predictions) / len(predictions),
                'avg_outcome_score': sum(p.get('outcome_score', 0) for p in predictions) / len(predictions),
                'success_rate': self.calculate_group_success_rate(predictions),
                'confidence_trend': self.calculate_confidence_trend(predictions),
                'outcome_trend': self.calculate_outcome_trend(predictions),
                'analysis_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            return group_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing prediction group: {e}")
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
    
    async def get_predictions_for_group(self, pattern_group: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get all predictions for a pattern group"""
        try:
            # Create group signature
            from .prediction_engine import PatternGroupingSystem
            grouping_system = PatternGroupingSystem()
            group_signature = grouping_system.create_group_signature(pattern_group)
            
            query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'prediction' 
                AND content->>'pattern_group'->>'group_signature' = %s
                AND content->>'pattern_group'->>'asset' = %s
                ORDER BY created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query, [
                group_signature,
                pattern_group['asset']
            ])
            
            return [dict(row) for row in result]
            
        except Exception as e:
            self.logger.error(f"Error getting predictions for group: {e}")
            return []
    
    def calculate_success_rate(self, prediction: Dict[str, Any]) -> float:
        """Calculate success rate for prediction"""
        outcome_score = prediction.get('outcome_score', 0.0)
        return 1.0 if outcome_score > 0 else 0.0
    
    def calculate_group_success_rate(self, predictions: List[Dict[str, Any]]) -> float:
        """Calculate success rate for a group of predictions"""
        if not predictions:
            return 0.0
        
        successful = len([p for p in predictions if p.get('outcome_score', 0) > 0])
        return successful / len(predictions)
    
    def calculate_confidence_trend(self, predictions: List[Dict[str, Any]]) -> str:
        """Calculate confidence trend over time"""
        if len(predictions) < 2:
            return 'insufficient_data'
        
        # Sort by creation time
        sorted_predictions = sorted(predictions, key=lambda x: x.get('created_at', ''))
        
        # Calculate trend
        early_confidence = sum(p.get('confidence', 0) for p in sorted_predictions[:len(predictions)//2])
        late_confidence = sum(p.get('confidence', 0) for p in sorted_predictions[len(predictions)//2:])
        
        if late_confidence > early_confidence * 1.1:
            return 'increasing'
        elif late_confidence < early_confidence * 0.9:
            return 'decreasing'
        else:
            return 'stable'
    
    def calculate_outcome_trend(self, predictions: List[Dict[str, Any]]) -> str:
        """Calculate outcome trend over time"""
        if len(predictions) < 2:
            return 'insufficient_data'
        
        # Sort by creation time
        sorted_predictions = sorted(predictions, key=lambda x: x.get('created_at', ''))
        
        # Calculate trend
        early_outcomes = sum(p.get('outcome_score', 0) for p in sorted_predictions[:len(predictions)//2])
        late_outcomes = sum(p.get('outcome_score', 0) for p in sorted_predictions[len(predictions)//2:])
        
        if late_outcomes > early_outcomes * 1.1:
            return 'improving'
        elif late_outcomes < early_outcomes * 0.9:
            return 'declining'
        else:
            return 'stable'
    
    def assess_analysis_quality(self, prediction: Dict[str, Any]) -> str:
        """Assess the quality of analysis based on available data"""
        confidence = prediction.get('confidence', 0.0)
        outcome_score = prediction.get('outcome_score', 0.0)
        context_metadata = prediction.get('context_metadata', {})
        
        # Check if we have enough historical data
        sample_size = context_metadata.get('exact_count', 0) + context_metadata.get('similar_count', 0)
        
        if sample_size >= self.analysis_thresholds['min_predictions_for_analysis']:
            if confidence >= self.analysis_thresholds['min_confidence']:
                return 'high_quality'
            else:
                return 'medium_quality'
        else:
            return 'low_quality'
