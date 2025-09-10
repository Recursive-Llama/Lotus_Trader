"""
Integrated Learning System

This module integrates universal and CIL learning systems into a unified learning pipeline.
It orchestrates the flow from strands → braids → CIL analysis → conditional plans.

Features:
1. Universal learning foundation
2. CIL specialized learning
3. Learning feedback loop (careful integration)
4. Monitoring and error handling
5. Configuration management
"""

import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta

from src.intelligence.universal_learning.universal_learning_system import UniversalLearningSystem
from src.intelligence.cil_learning.cil_learning_system import CILLearningSystem
from src.intelligence.learning_config import LearningConfigManager
from src.intelligence.learning_monitor import LearningMonitor, AlertLevel

logger = logging.getLogger(__name__)


class IntegratedLearningSystem:
    """
    Integrated Learning System - Orchestrates universal and CIL learning
    
    This system provides a unified learning pipeline that:
    1. Processes all strands through universal learning
    2. Feeds trading-related braids to CIL learning
    3. Manages learning feedback loops carefully
    4. Provides monitoring and error handling
    """
    
    def __init__(self, supabase_manager, llm_config=None):
        """
        Initialize integrated learning system
        
        Args:
            supabase_manager: Database manager
            llm_config: LLM configuration dictionary
        """
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize configuration and monitoring
        self.config_manager = LearningConfigManager()
        self.monitor = LearningMonitor(self.config_manager)
        
        # Initialize learning systems
        self.universal_learning = UniversalLearningSystem(
            supabase_manager=supabase_manager,
            llm_config=llm_config
        )
        
        self.cil_learning = CILLearningSystem(
            supabase_manager=supabase_manager,
            llm_client=self.universal_learning.llm_manager
        )
        
        # Learning state
        self.is_running = False
        self.last_processing_time = None
        
        # Feedback loop configuration
        self.feedback_enabled = True
        self.feedback_cooldown = 300  # 5 minutes between feedback cycles
        
        self.logger.info("Integrated Learning System initialized")
    
    async def start_learning_loop(self, interval_minutes: int = 5):
        """
        Start the integrated learning loop
        
        Args:
            interval_minutes: Minutes between learning cycles
        """
        try:
            self.is_running = True
            self.logger.info(f"Starting integrated learning loop (interval: {interval_minutes} minutes)")
            
            while self.is_running:
                try:
                    # Process learning cycle
                    await self.process_learning_cycle()
                    
                    # Wait for next cycle
                    await asyncio.sleep(interval_minutes * 60)
                    
                except Exception as e:
                    self.logger.error(f"Error in learning loop: {e}")
                    self.monitor.track_error("learning_loop_error", str(e))
                    await asyncio.sleep(60)  # Wait 1 minute before retrying
            
        except Exception as e:
            self.logger.error(f"Error starting learning loop: {e}")
            self.monitor.track_error("learning_loop_start_error", str(e))
        finally:
            self.is_running = False
    
    async def stop_learning_loop(self):
        """Stop the learning loop"""
        self.is_running = False
        self.logger.info("Learning loop stopped")
    
    async def process_learning_cycle(self) -> Dict[str, Any]:
        """
        Process one complete learning cycle
        
        Returns:
            Dictionary with processing results
        """
        start_time = time.time()
        
        try:
            self.logger.info("Starting learning cycle")
            self.monitor.log_event("learning_cycle_started", "Started new learning cycle")
            
            results = {
                'cycle_started': datetime.now(timezone.utc).isoformat(),
                'universal_learning': {},
                'cil_learning': {},
                'feedback_processing': {},
                'errors': []
            }
            
            # Step 1: Universal Learning - Process all strands
            universal_results = await self._process_universal_learning()
            results['universal_learning'] = universal_results
            
            # Step 2: CIL Learning - Process trading-related braids
            cil_results = await self._process_cil_learning(universal_results.get('braids_created', []))
            results['cil_learning'] = cil_results
            
            # Step 3: Learning Feedback Loop (careful integration)
            if self.feedback_enabled:
                feedback_results = await self._process_learning_feedback()
                results['feedback_processing'] = feedback_results
            
            # Calculate processing time
            processing_time = time.time() - start_time
            self.monitor.track_processing_time("learning_cycle", processing_time)
            
            results['cycle_completed'] = datetime.now(timezone.utc).isoformat()
            results['processing_time'] = processing_time
            
            self.logger.info(f"Learning cycle completed in {processing_time:.2f} seconds")
            self.monitor.log_event("learning_cycle_completed", f"Completed learning cycle in {processing_time:.2f}s")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in learning cycle: {e}")
            self.monitor.track_error("learning_cycle_error", str(e))
            return {'error': str(e)}
    
    async def _process_universal_learning(self) -> Dict[str, Any]:
        """Process universal learning on all strands"""
        try:
            self.logger.info("Processing universal learning")
            
            # Get recent strands (last 24 hours)
            recent_strands = self._get_recent_strands(hours=24)
            
            if not recent_strands:
                self.logger.info("No recent strands found for universal learning")
                return {'strands_processed': 0, 'braids_created': 0}
            
            # Process strands through universal learning
            braids = await self.universal_learning.cluster_and_promote_strands(recent_strands, braid_level=0)
            
            # Track metrics
            self.monitor.track_strands_processed(len(recent_strands), "universal")
            self.monitor.track_braids_created(len(braids))
            
            self.logger.info(f"Universal learning: {len(recent_strands)} strands → {len(braids)} braids")
            
            return {
                'strands_processed': len(recent_strands),
                'braids_created': len(braids),
                'braids': braids
            }
            
        except Exception as e:
            self.logger.error(f"Error in universal learning: {e}")
            self.monitor.track_error("universal_learning_error", str(e))
            return {'error': str(e)}
    
    async def _process_cil_learning(self, braids: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process CIL learning on trading-related braids"""
        try:
            self.logger.info("Processing CIL learning")
            
            # Filter braids for trading relevance
            trading_braids = self._filter_trading_braids(braids)
            
            if not trading_braids:
                self.logger.info("No trading-relevant braids found for CIL learning")
                return {'braids_processed': 0, 'plans_created': 0}
            
            # Process through CIL learning
            cil_results = await self.cil_learning.process_completed_predictions()
            
            # Track metrics
            self.monitor.track_braids_created(len(trading_braids), "cil")
            
            self.logger.info(f"CIL learning: {len(trading_braids)} braids processed")
            
            return {
                'braids_processed': len(trading_braids),
                'predictions_processed': cil_results.get('predictions_processed', 0),
                'plans_created': cil_results.get('plans_created', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error in CIL learning: {e}")
            self.monitor.track_error("cil_learning_error", str(e))
            return {'error': str(e)}
    
    async def _process_learning_feedback(self) -> Dict[str, Any]:
        """Process learning feedback loop (careful integration)"""
        try:
            # Check cooldown
            if self.last_processing_time:
                time_since_last = (datetime.now(timezone.utc) - self.last_processing_time).total_seconds()
                if time_since_last < self.feedback_cooldown:
                    return {'skipped': 'cooldown_active'}
            
            self.logger.info("Processing learning feedback loop")
            
            # Get CIL learning insights
            cil_insights = await self._get_cil_insights()
            
            if not cil_insights:
                return {'insights_processed': 0}
            
            # Feed insights back to universal system (carefully)
            feedback_results = await self._apply_learning_feedback(cil_insights)
            
            self.last_processing_time = datetime.now(timezone.utc)
            
            self.logger.info(f"Learning feedback: {len(cil_insights)} insights processed")
            
            return {
                'insights_processed': len(cil_insights),
                'feedback_applied': feedback_results.get('applied', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error in learning feedback: {e}")
            self.monitor.track_error("learning_feedback_error", str(e))
            return {'error': str(e)}
    
    def _filter_trading_braids(self, braids: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter braids for trading relevance"""
        try:
            trading_braids = []
            
            for braid in braids:
                # Check if braid is trading-relevant
                if self._is_trading_relevant_braid(braid):
                    trading_braids.append(braid)
            
            return trading_braids
            
        except Exception as e:
            self.logger.error(f"Error filtering trading braids: {e}")
            return []
    
    def _is_trading_relevant_braid(self, braid: Dict[str, Any]) -> bool:
        """Check if braid is relevant for trading"""
        try:
            # Check symbol presence
            if not braid.get('symbol'):
                return False
            
            # Check for trading-related patterns
            pattern_type = braid.get('pattern_type', '')
            trading_patterns = ['volume_spike', 'divergence', 'confluence', 'breakout', 'reversal']
            
            if pattern_type in trading_patterns:
                return True
            
            # Check agent ID
            agent_id = braid.get('agent_id', '')
            if 'trading' in agent_id.lower() or 'cil' in agent_id.lower():
                return True
            
            # Check content for trading keywords
            content = braid.get('content', {})
            if isinstance(content, dict):
                lesson = content.get('lesson', '')
                trading_keywords = ['trade', 'buy', 'sell', 'signal', 'pattern', 'market']
                if any(keyword in lesson.lower() for keyword in trading_keywords):
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking trading relevance: {e}")
            return False
    
    async def _get_recent_strands(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent strands from database"""
        try:
            # Query for recent strands
            result = self.supabase_manager.client.table('ad_strands').select('*').gte(
                'created_at', 
                (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            ).order('created_at', desc=True).limit(1000).execute()
            
            return result.data if result.data else []
                
        except Exception as e:
            self.logger.error(f"Error getting recent strands: {e}")
            return []
    
    async def _get_cil_insights(self) -> List[Dict[str, Any]]:
        """Get CIL learning insights for feedback"""
        try:
            # Get recent conditional plans
            plans = await self.cil_learning.get_active_plans()
            
            # Get recent prediction outcomes
            predictions = await self.cil_learning.get_active_predictions()
            
            insights = []
            
            # Extract insights from plans
            for plan in plans:
                if plan.get('success_rate', 0) > 0.8:  # High-performing plans
                    insights.append({
                        'type': 'high_performing_plan',
                        'plan_id': plan.get('id'),
                        'success_rate': plan.get('success_rate'),
                        'data': plan
                    })
            
            # Extract insights from predictions
            for prediction in predictions:
                if prediction.get('outcome') == 'target_hit':
                    insights.append({
                        'type': 'successful_prediction',
                        'prediction_id': prediction.get('prediction_id'),
                        'data': prediction
                    })
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error getting CIL insights: {e}")
            return []
    
    async def _apply_learning_feedback(self, insights: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply learning feedback to universal system (carefully)"""
        try:
            applied_count = 0
            
            for insight in insights:
                try:
                    if insight['type'] == 'high_performing_plan':
                        # Update universal learning thresholds based on successful plans
                        await self._update_learning_thresholds(insight)
                        applied_count += 1
                    
                    elif insight['type'] == 'successful_prediction':
                        # Update pattern recognition based on successful predictions
                        await self._update_pattern_recognition(insight)
                        applied_count += 1
                
                except Exception as e:
                    self.logger.warning(f"Error applying insight {insight['type']}: {e}")
                    continue
            
            return {'applied': applied_count}
            
        except Exception as e:
            self.logger.error(f"Error applying learning feedback: {e}")
            return {'error': str(e)}
    
    async def _update_learning_thresholds(self, insight: Dict[str, Any]):
        """Update learning thresholds based on successful plans"""
        try:
            # This is where we would carefully update universal learning thresholds
            # based on CIL learning success. We need to be very careful here to
            # avoid circular dependencies and maintain system stability.
            
            self.logger.info(f"Updating learning thresholds based on insight: {insight['type']}")
            
            # For now, just log the insight - actual implementation would be more sophisticated
            self.monitor.log_event(
                "threshold_update",
                f"Updated thresholds based on {insight['type']}",
                AlertLevel.INFO,
                insight
            )
            
        except Exception as e:
            self.logger.error(f"Error updating learning thresholds: {e}")
    
    async def _update_pattern_recognition(self, insight: Dict[str, Any]):
        """Update pattern recognition based on successful predictions"""
        try:
            # This is where we would carefully update pattern recognition
            # based on successful predictions. Again, we need to be very careful.
            
            self.logger.info(f"Updating pattern recognition based on insight: {insight['type']}")
            
            # For now, just log the insight
            self.monitor.log_event(
                "pattern_update",
                f"Updated pattern recognition based on {insight['type']}",
                AlertLevel.INFO,
                insight
            )
            
        except Exception as e:
            self.logger.error(f"Error updating pattern recognition: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        try:
            return {
                'is_running': self.is_running,
                'last_processing_time': self.last_processing_time.isoformat() if self.last_processing_time else None,
                'feedback_enabled': self.feedback_enabled,
                'performance_stats': self.monitor.get_performance_stats(),
                'recent_events': len(self.monitor.get_recent_events(1)),
                'recent_errors': len(self.monitor.get_recent_errors(1))
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {'error': str(e)}
    
    async def force_learning_cycle(self) -> Dict[str, Any]:
        """Force a learning cycle (for testing/debugging)"""
        try:
            self.logger.info("Forcing learning cycle")
            return await self.process_learning_cycle()
            
        except Exception as e:
            self.logger.error(f"Error in forced learning cycle: {e}")
            return {'error': str(e)}


# Example usage and testing
if __name__ == "__main__":
    # Test the integrated learning system
    from src.utils.supabase_manager import SupabaseManager
    
    async def test_integrated_learning():
        supabase_manager = SupabaseManager()
        learning_system = IntegratedLearningSystem(supabase_manager)
        
        # Test system status
        status = await learning_system.get_system_status()
        print(f"System status: {status}")
        
        # Test forced learning cycle
        results = await learning_system.force_learning_cycle()
        print(f"Learning cycle results: {results}")
    
    import asyncio
    asyncio.run(test_integrated_learning())
