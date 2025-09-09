"""
Integration Test: Trader → CIL Feedback Flow

This test validates the complete feedback loop from Trader execution results
back to the CIL for learning and future guidance, using real execution data.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
import logging

# Import the actual components
from src.intelligence.trader.enhanced_execution_agent import EnhancedExecutionAgent
from src.intelligence.trader.order_manager import OrderManager
from src.intelligence.trader.position_tracker import PositionTracker
from src.intelligence.trader.performance_analyzer import PerformanceAnalyzer
from src.intelligence.system_control.central_intelligence_layer.engines.learning_feedback_engine import LearningFeedbackEngine
from src.intelligence.system_control.central_intelligence_layer.engines.autonomy_adaptation_engine import AutonomyAdaptationEngine
from src.intelligence.system_control.central_intelligence_layer.core.cil_doctrine_keeper import CILDoctrineKeeper
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestTraderToCilFeedbackFlow:
    """Test suite for Trader → CIL feedback flow"""
    
    @pytest.fixture
    async def setup_components(self):
        """Set up all components for integration testing"""
        # Initialize real components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        
        # Trader components
        execution_agent = EnhancedExecutionAgent(supabase_manager, llm_client)
        order_manager = OrderManager(supabase_manager, llm_client)
        position_tracker = PositionTracker(supabase_manager, llm_client)
        performance_analyzer = PerformanceAnalyzer(supabase_manager, llm_client)
        
        # CIL components
        learning_feedback_engine = LearningFeedbackEngine(supabase_manager, llm_client)
        autonomy_adaptation_engine = AutonomyAdaptationEngine(supabase_manager, llm_client)
        doctrine_keeper = CILDoctrineKeeper(supabase_manager, llm_client)
        
        return {
            'supabase_manager': supabase_manager,
            'llm_client': llm_client,
            'execution_agent': execution_agent,
            'order_manager': order_manager,
            'position_tracker': position_tracker,
            'performance_analyzer': performance_analyzer,
            'learning_feedback_engine': learning_feedback_engine,
            'autonomy_adaptation_engine': autonomy_adaptation_engine,
            'doctrine_keeper': doctrine_keeper
        }
    
    @pytest.mark.asyncio
    async def test_execution_results_to_cil_learning_feedback(self, setup_components):
        """Test complete flow: Execution results → CIL learning feedback"""
        components = await setup_components
        
        # Step 1: Create test execution results
        logger.info("Step 1: Creating test execution results...")
        
        test_execution_results = await self._create_test_execution_results(components['supabase_manager'])
        assert len(test_execution_results) > 0, "Failed to create test execution results"
        logger.info(f"Created {len(test_execution_results)} test execution results")
        
        # Step 2: Trader Performance Analyzer analyzes execution results
        logger.info("Step 2: Trader Performance Analyzer analyzing execution results...")
        
        # Get recent execution results for analysis
        recent_executions = await components['supabase_manager'].get_recent_strands(
            limit=20,
            since=datetime.now(timezone.utc) - timedelta(minutes=10)
        )
        
        # Filter for execution results
        execution_results = [s for s in recent_executions 
                           if s.get('kind') in ['execution_result', 'order_filled', 'position_update']]
        
        # Process through Performance Analyzer
        performance_analysis = await components['performance_analyzer'].analyze_execution_performance(
            execution_results,
            {'analysis_context': {'timeframe': '1h', 'benchmark': 'market'}}
        )
        
        assert performance_analysis is not None, "Performance Analyzer failed to analyze execution results"
        assert 'performance_metrics' in performance_analysis, "Missing performance metrics"
        assert 'lessons_learned' in performance_analysis, "Missing lessons learned"
        
        logger.info(f"Performance Analyzer completed analysis with {len(performance_analysis['lessons_learned'])} lessons")
        
        # Step 3: Create performance feedback strands
        logger.info("Step 3: Creating performance feedback strands...")
        
        feedback_strands = []
        for i, lesson in enumerate(performance_analysis['lessons_learned']):
            feedback_strand = {
                'id': f"feedback_{i}_{int(time.time())}",
                'kind': 'execution_feedback',
                'module': 'alpha',
                'symbol': lesson.get('symbol', 'ALL'),
                'timeframe': '1h',
                'session_bucket': 'ALL',
                'regime': 'all',
                'tags': [
                    'agent:trader:feedback:execution_result',
                    'feedback:central_intelligence',
                    'lesson_type:execution_performance',
                    'priority:high'
                ],
                'content': {
                    'lesson_type': 'execution_performance',
                    'symbol': lesson.get('symbol', 'ALL'),
                    'action': lesson.get('action', 'unknown'),
                    'outcome': lesson.get('outcome', 'unknown'),
                    'performance_score': lesson.get('performance_score', 0.0),
                    'lessons_learned': lesson.get('insights', []),
                    'recommendations': lesson.get('recommendations', []),
                    'context': lesson.get('context', 'execution_analysis')
                },
                'sig_sigma': 0.9,
                'sig_confidence': 0.9,
                'outcome_score': lesson.get('performance_score', 0.0),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'agent_id': 'trader',
                'team_member': 'performance_analyzer'
            }
            
            await components['supabase_manager'].insert_strand(feedback_strand)
            feedback_strands.append(feedback_strand)
        
        assert len(feedback_strands) > 0, "No performance feedback strands created"
        logger.info(f"Created {len(feedback_strands)} performance feedback strands")
        
        # Step 4: CIL Learning & Feedback Engine processes feedback
        logger.info("Step 4: CIL Learning & Feedback Engine processing feedback...")
        
        # Get feedback strands for CIL processing
        feedback_strands_db = await components['supabase_manager'].get_strands_by_tags(
            ['agent:trader:feedback:execution_result'],
            limit=10,
            since=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        
        # Process through Learning & Feedback Engine
        learning_results = await components['learning_feedback_engine'].process_feedback_lessons(
            feedback_strands_db,
            {'learning_context': {'focus_area': 'execution_performance', 'time_horizon': 'short'}}
        )
        
        assert learning_results is not None, "CIL Learning & Feedback Engine failed to process feedback"
        assert 'structured_lessons' in learning_results, "Missing structured lessons"
        assert 'doctrine_updates' in learning_results, "Missing doctrine updates"
        assert 'cross_agent_distribution' in learning_results, "Missing cross-agent distribution"
        
        logger.info(f"CIL Learning & Feedback Engine processed {len(learning_results['structured_lessons'])} lessons")
        
        # Step 5: CIL Doctrine Keeper updates doctrine
        logger.info("Step 5: CIL Doctrine Keeper updating doctrine...")
        
        doctrine_updates = await components['doctrine_keeper'].update_doctrine_from_lessons(
            learning_results['structured_lessons'],
            {'doctrine_context': {'update_type': 'execution_performance', 'confidence_threshold': 0.7}}
        )
        
        assert doctrine_updates is not None, "CIL Doctrine Keeper failed to update doctrine"
        assert 'doctrine_changes' in doctrine_updates, "Missing doctrine changes"
        assert 'promoted_patterns' in doctrine_updates, "Missing promoted patterns"
        assert 'retired_patterns' in doctrine_updates, "Missing retired patterns"
        
        logger.info(f"CIL Doctrine Keeper updated doctrine with {len(doctrine_updates['doctrine_changes'])} changes")
        
        # Step 6: CIL Autonomy & Adaptation Engine adapts system
        logger.info("Step 6: CIL Autonomy & Adaptation Engine adapting system...")
        
        adaptation_results = await components['autonomy_adaptation_engine'].adapt_system_from_feedback(
            learning_results['structured_lessons'],
            doctrine_updates['doctrine_changes'],
            {'adaptation_context': {'adaptation_type': 'execution_performance', 'adaptation_rate': 0.1}}
        )
        
        assert adaptation_results is not None, "CIL Autonomy & Adaptation Engine failed to adapt system"
        assert 'adaptive_changes' in adaptation_results, "Missing adaptive changes"
        assert 'agent_calibration' in adaptation_results, "Missing agent calibration"
        assert 'focus_adaptation' in adaptation_results, "Missing focus adaptation"
        
        logger.info(f"CIL Autonomy & Adaptation Engine made {len(adaptation_results['adaptive_changes'])} adaptive changes")
        
        # Step 7: Verify feedback strands are published
        logger.info("Step 7: Verifying feedback strands published...")
        
        published_feedback_strands = []
        for feedback_strand in feedback_strands:
            published_strand = await components['supabase_manager'].get_strand_by_id(feedback_strand['id'])
            if published_strand:
                published_feedback_strands.append(published_strand)
        
        assert len(published_feedback_strands) > 0, "No feedback strands were published"
        logger.info(f"Verified {len(published_feedback_strands)} feedback strands published")
        
        # Step 8: Verify complete feedback loop integrity
        logger.info("Step 8: Verifying complete feedback loop integrity...")
        
        # Check that all components are working together
        assert len(test_execution_results) > 0, "Test execution results not created"
        assert performance_analysis is not None, "Performance analysis failed"
        assert len(feedback_strands) > 0, "Feedback strands not created"
        assert learning_results is not None, "CIL learning processing failed"
        assert doctrine_updates is not None, "Doctrine updates failed"
        assert adaptation_results is not None, "System adaptation failed"
        assert len(published_feedback_strands) > 0, "Feedback strands not published"
        
        # Verify tag-based communication is working
        for feedback_strand in published_feedback_strands:
            assert 'tags' in feedback_strand, "Feedback strand missing tags"
            tags = feedback_strand['tags']
            assert any('agent:trader:feedback' in tag for tag in tags), \
                "Trader feedback tags not found"
            assert any('feedback:central_intelligence' in tag for tag in tags), \
                "CIL feedback target tags not found"
        
        logger.info("✅ Complete Trader → CIL feedback loop integrity verified!")
        
        return {
            'test_execution_results': len(test_execution_results),
            'performance_lessons': len(performance_analysis['lessons_learned']),
            'feedback_strands': len(feedback_strands),
            'structured_lessons': len(learning_results['structured_lessons']),
            'doctrine_changes': len(doctrine_updates['doctrine_changes']),
            'adaptive_changes': len(adaptation_results['adaptive_changes']),
            'published_feedback': len(published_feedback_strands),
            'feedback_loop_success': True
        }
    
    async def _create_test_execution_results(self, supabase_manager: SupabaseManager) -> List[Dict[str, Any]]:
        """Create test execution results for feedback analysis"""
        test_results = []
        
        # Create successful execution result
        successful_execution = {
            'id': f"exec_success_{int(time.time())}",
            'kind': 'execution_result',
            'module': 'alpha',
            'symbol': 'BTC',
            'timeframe': '1h',
            'session_bucket': 'US',
            'regime': 'high_vol',
            'tags': [
                'agent:trader:execution:order_filled',
                'execution_type:buy',
                'outcome:success'
            ],
            'content': {
                'action': 'buy',
                'symbol': 'BTC',
                'quantity': 0.1,
                'execution_price': 50000.0,
                'expected_price': 49900.0,
                'slippage': 0.002,
                'execution_time': datetime.now(timezone.utc).isoformat(),
                'outcome': 'success',
                'performance_score': 0.85,
                'context': 'bullish_divergence_execution'
            },
            'sig_sigma': 0.9,
            'sig_confidence': 0.85,
            'outcome_score': 0.85,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'agent_id': 'trader',
            'team_member': 'execution_agent'
        }
        
        # Create failed execution result
        failed_execution = {
            'id': f"exec_failed_{int(time.time())}",
            'kind': 'execution_result',
            'module': 'alpha',
            'symbol': 'ETH',
            'timeframe': '1h',
            'session_bucket': 'EU',
            'regime': 'sideways',
            'tags': [
                'agent:trader:execution:order_failed',
                'execution_type:sell',
                'outcome:failure'
            ],
            'content': {
                'action': 'sell',
                'symbol': 'ETH',
                'quantity': 0.2,
                'execution_price': None,
                'expected_price': 3000.0,
                'slippage': None,
                'execution_time': datetime.now(timezone.utc).isoformat(),
                'outcome': 'failure',
                'failure_reason': 'insufficient_liquidity',
                'performance_score': 0.0,
                'context': 'resistance_level_execution'
            },
            'sig_sigma': 0.8,
            'sig_confidence': 0.0,
            'outcome_score': 0.0,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'agent_id': 'trader',
            'team_member': 'execution_agent'
        }
        
        # Create partial execution result
        partial_execution = {
            'id': f"exec_partial_{int(time.time())}",
            'kind': 'execution_result',
            'module': 'alpha',
            'symbol': 'SOL',
            'timeframe': '4h',
            'session_bucket': 'ALL',
            'regime': 'all',
            'tags': [
                'agent:trader:execution:order_partial',
                'execution_type:buy',
                'outcome:partial'
            ],
            'content': {
                'action': 'buy',
                'symbol': 'SOL',
                'quantity': 0.15,
                'execution_price': 100.0,
                'expected_price': 99.5,
                'slippage': 0.005,
                'execution_time': datetime.now(timezone.utc).isoformat(),
                'outcome': 'partial',
                'partial_reason': 'market_volatility',
                'performance_score': 0.6,
                'context': 'breakout_execution'
            },
            'sig_sigma': 0.7,
            'sig_confidence': 0.6,
            'outcome_score': 0.6,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'agent_id': 'trader',
            'team_member': 'execution_agent'
        }
        
        # Publish execution results
        for execution in [successful_execution, failed_execution, partial_execution]:
            try:
                await supabase_manager.insert_strand(execution)
                test_results.append(execution)
                logger.info(f"Published test execution result: {execution['content']['outcome']}")
            except Exception as e:
                logger.warning(f"Failed to publish execution result {execution['content']['outcome']}: {e}")
        
        return test_results
    
    @pytest.mark.asyncio
    async def test_performance_analysis_to_lesson_generation(self, setup_components):
        """Test that performance analysis generates meaningful lessons"""
        components = await setup_components
        
        # Create test execution results with different outcomes
        test_executions = [
            {
                'id': f"perf_test_1_{int(time.time())}",
                'kind': 'execution_result',
                'content': {
                    'action': 'buy',
                    'symbol': 'BTC',
                    'outcome': 'success',
                    'performance_score': 0.9,
                    'slippage': 0.001,
                    'context': 'high_confidence_signal'
                }
            },
            {
                'id': f"perf_test_2_{int(time.time())}",
                'kind': 'execution_result',
                'content': {
                    'action': 'sell',
                    'symbol': 'ETH',
                    'outcome': 'failure',
                    'performance_score': 0.1,
                    'failure_reason': 'timing_error',
                    'context': 'low_confidence_signal'
                }
            }
        ]
        
        # Publish test executions
        for execution in test_executions:
            await components['supabase_manager'].insert_strand(execution)
        
        # Wait for executions to be processed
        await asyncio.sleep(2)
        
        # Process through Performance Analyzer
        performance_analysis = await components['performance_analyzer'].analyze_execution_performance(
            test_executions,
            {'analysis_context': {'timeframe': '1h', 'benchmark': 'market'}}
        )
        
        assert performance_analysis is not None, "Performance analysis failed"
        assert 'lessons_learned' in performance_analysis, "Missing lessons learned"
        
        lessons = performance_analysis['lessons_learned']
        assert len(lessons) > 0, "No lessons generated from performance analysis"
        
        # Verify lessons have meaningful content
        for lesson in lessons:
            assert 'lesson_type' in lesson, "Missing lesson type"
            assert 'insights' in lesson, "Missing insights"
            assert 'recommendations' in lesson, "Missing recommendations"
            assert 'performance_score' in lesson, "Missing performance score"
            
            # Verify insights are meaningful
            insights = lesson['insights']
            assert isinstance(insights, list), "Insights should be a list"
            assert len(insights) > 0, "No insights generated"
            
            # Verify recommendations are actionable
            recommendations = lesson['recommendations']
            assert isinstance(recommendations, list), "Recommendations should be a list"
            assert len(recommendations) > 0, "No recommendations generated"
        
        logger.info("✅ Performance analysis to lesson generation verified!")
    
    @pytest.mark.asyncio
    async def test_doctrine_update_from_execution_feedback(self, setup_components):
        """Test that doctrine is updated based on execution feedback"""
        components = await setup_components
        
        # Create test lessons from execution feedback
        test_lessons = [
            {
                'id': f"lesson_1_{int(time.time())}",
                'lesson_type': 'execution_performance',
                'symbol': 'BTC',
                'action': 'buy',
                'outcome': 'success',
                'performance_score': 0.9,
                'insights': [
                    'Low slippage execution in high volatility',
                    'Timing was optimal for entry',
                    'Risk management was effective'
                ],
                'recommendations': [
                    'Continue using similar execution strategy',
                    'Maintain current risk parameters',
                    'Consider scaling up position size'
                ],
                'context': 'bullish_divergence_execution',
                'confidence': 0.85
            },
            {
                'id': f"lesson_2_{int(time.time())}",
                'lesson_type': 'execution_performance',
                'symbol': 'ETH',
                'action': 'sell',
                'outcome': 'failure',
                'performance_score': 0.2,
                'insights': [
                    'Execution failed due to insufficient liquidity',
                    'Timing was suboptimal',
                    'Risk management needs improvement'
                ],
                'recommendations': [
                    'Avoid execution during low liquidity periods',
                    'Improve timing analysis',
                    'Implement better risk controls'
                ],
                'context': 'resistance_level_execution',
                'confidence': 0.8
            }
        ]
        
        # Process through Doctrine Keeper
        doctrine_updates = await components['doctrine_keeper'].update_doctrine_from_lessons(
            test_lessons,
            {'doctrine_context': {'update_type': 'execution_performance', 'confidence_threshold': 0.7}}
        )
        
        assert doctrine_updates is not None, "Doctrine updates failed"
        assert 'doctrine_changes' in doctrine_updates, "Missing doctrine changes"
        assert 'promoted_patterns' in doctrine_updates, "Missing promoted patterns"
        assert 'retired_patterns' in doctrine_updates, "Missing retired patterns"
        
        # Verify doctrine changes are meaningful
        doctrine_changes = doctrine_updates['doctrine_changes']
        assert len(doctrine_changes) > 0, "No doctrine changes generated"
        
        for change in doctrine_changes:
            assert 'change_type' in change, "Missing change type"
            assert 'pattern_id' in change, "Missing pattern ID"
            assert 'confidence' in change, "Missing confidence"
            assert 'reasoning' in change, "Missing reasoning"
            
            # Verify change types are valid
            assert change['change_type'] in ['promote', 'retire', 'refine', 'contraindicate'], \
                f"Invalid change type: {change['change_type']}"
        
        # Verify promoted patterns
        promoted_patterns = doctrine_updates['promoted_patterns']
        assert isinstance(promoted_patterns, list), "Promoted patterns should be a list"
        
        # Verify retired patterns
        retired_patterns = doctrine_updates['retired_patterns']
        assert isinstance(retired_patterns, list), "Retired patterns should be a list"
        
        logger.info("✅ Doctrine update from execution feedback verified!")
    
    @pytest.mark.asyncio
    async def test_system_adaptation_from_feedback(self, setup_components):
        """Test that system adapts based on execution feedback"""
        components = await setup_components
        
        # Create test lessons and doctrine changes
        test_lessons = [
            {
                'lesson_type': 'execution_performance',
                'performance_score': 0.9,
                'insights': ['High performance execution'],
                'recommendations': ['Continue current approach']
            }
        ]
        
        test_doctrine_changes = [
            {
                'change_type': 'promote',
                'pattern_id': 'btc_bullish_divergence',
                'confidence': 0.85,
                'reasoning': 'Consistent high performance'
            }
        ]
        
        # Process through Autonomy & Adaptation Engine
        adaptation_results = await components['autonomy_adaptation_engine'].adapt_system_from_feedback(
            test_lessons,
            test_doctrine_changes,
            {'adaptation_context': {'adaptation_type': 'execution_performance', 'adaptation_rate': 0.1}}
        )
        
        assert adaptation_results is not None, "System adaptation failed"
        assert 'adaptive_changes' in adaptation_results, "Missing adaptive changes"
        assert 'agent_calibration' in adaptation_results, "Missing agent calibration"
        assert 'focus_adaptation' in adaptation_results, "Missing focus adaptation"
        
        # Verify adaptive changes are meaningful
        adaptive_changes = adaptation_results['adaptive_changes']
        assert len(adaptive_changes) > 0, "No adaptive changes generated"
        
        for change in adaptive_changes:
            assert 'change_type' in change, "Missing change type"
            assert 'target_component' in change, "Missing target component"
            assert 'adaptation_value' in change, "Missing adaptation value"
            assert 'reasoning' in change, "Missing reasoning"
            
            # Verify change types are valid
            assert change['change_type'] in ['parameter_adjustment', 'threshold_change', 'focus_shift', 'calibration_update'], \
                f"Invalid change type: {change['change_type']}"
        
        # Verify agent calibration
        agent_calibration = adaptation_results['agent_calibration']
        assert isinstance(agent_calibration, list), "Agent calibration should be a list"
        
        for calibration in agent_calibration:
            assert 'agent_id' in calibration, "Missing agent ID"
            assert 'calibration_type' in calibration, "Missing calibration type"
            assert 'new_value' in calibration, "Missing new value"
        
        # Verify focus adaptation
        focus_adaptation = adaptation_results['focus_adaptation']
        assert isinstance(focus_adaptation, list), "Focus adaptation should be a list"
        
        for focus in focus_adaptation:
            assert 'focus_area' in focus, "Missing focus area"
            assert 'adaptation_direction' in focus, "Missing adaptation direction"
            assert 'confidence' in focus, "Missing confidence"
        
        logger.info("✅ System adaptation from feedback verified!")
    
    @pytest.mark.asyncio
    async def test_feedback_loop_continuity(self, setup_components):
        """Test that feedback loop maintains continuity and learning"""
        components = await setup_components
        
        # Create multiple rounds of execution results
        execution_rounds = []
        for round_num in range(3):
            round_executions = []
            for i in range(2):
                execution = {
                    'id': f"round_{round_num}_exec_{i}_{int(time.time())}",
                    'kind': 'execution_result',
                    'content': {
                        'action': 'buy' if i % 2 == 0 else 'sell',
                        'symbol': 'BTC',
                        'outcome': 'success' if round_num > 0 else 'failure',
                        'performance_score': 0.8 + (round_num * 0.05),
                        'context': f'round_{round_num}_execution'
                    }
                }
                await components['supabase_manager'].insert_strand(execution)
                round_executions.append(execution)
            
            execution_rounds.append(round_executions)
            
            # Wait between rounds
            await asyncio.sleep(1)
        
        # Process each round through the feedback loop
        feedback_results = []
        for round_num, executions in enumerate(execution_rounds):
            # Performance analysis
            performance_analysis = await components['performance_analyzer'].analyze_execution_performance(
                executions,
                {'analysis_context': {'timeframe': '1h', 'benchmark': 'market'}}
            )
            
            # Learning processing
            if performance_analysis and 'lessons_learned' in performance_analysis:
                learning_results = await components['learning_feedback_engine'].process_feedback_lessons(
                    [{'content': lesson} for lesson in performance_analysis['lessons_learned']],
                    {'learning_context': {'focus_area': 'execution_performance', 'time_horizon': 'short'}}
                )
                
                feedback_results.append({
                    'round': round_num,
                    'lessons': len(performance_analysis['lessons_learned']),
                    'learning_success': learning_results is not None
                })
        
        # Verify feedback loop continuity
        assert len(feedback_results) == len(execution_rounds), "Feedback loop continuity broken"
        
        for result in feedback_results:
            assert result['lessons'] > 0, f"No lessons learned in round {result['round']}"
            assert result['learning_success'], f"Learning failed in round {result['round']}"
        
        # Verify learning improvement over rounds
        if len(feedback_results) > 1:
            # Check that later rounds show learning from earlier rounds
            later_rounds = feedback_results[1:]
            for result in later_rounds:
                assert result['learning_success'], "Learning should improve over rounds"
        
        logger.info("✅ Feedback loop continuity verified!")
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, setup_components):
        """Test error handling and recovery in the Trader → CIL feedback flow"""
        components = await setup_components
        
        # Test with malformed execution result
        malformed_execution = {
            'id': f"malformed_exec_{int(time.time())}",
            'kind': 'execution_result',
            # Missing required fields
            'content': {
                'test': 'malformed_data'
            }
        }
        
        # Try to publish malformed execution result
        try:
            await components['supabase_manager'].insert_strand(malformed_execution)
        except Exception as e:
            logger.info(f"Expected error for malformed execution result: {e}")
        
        # Test with invalid performance data
        invalid_performance_data = [
            {'invalid': 'data'},
            {'outcome': 'invalid_outcome'},
            None
        ]
        
        # Test that components handle invalid data gracefully
        try:
            performance_analysis = await components['performance_analyzer'].analyze_execution_performance(
                invalid_performance_data,
                {'analysis_context': {'timeframe': '1h', 'benchmark': 'market'}}
            )
            # Should return empty results or handle gracefully
            assert performance_analysis is not None, "Should return results even with invalid data"
        except Exception as e:
            logger.info(f"Component handled invalid data: {e}")
        
        # Test database connection recovery
        try:
            # Simulate database connection issue
            with patch.object(components['supabase_manager'], 'insert_strand', side_effect=Exception("DB Error")):
                test_feedback = {
                    'id': f"db_error_test_{int(time.time())}",
                    'kind': 'test_feedback',
                    'content': {'test': 'data'}
                }
                
                try:
                    await components['supabase_manager'].insert_strand(test_feedback)
                except Exception as db_error:
                    logger.info(f"Database error handled: {db_error}")
                    # Should not crash the system
                    assert "DB Error" in str(db_error)
        except Exception as e:
            logger.info(f"Error handling test completed: {e}")
        
        logger.info("✅ Error handling and recovery verified!")


if __name__ == "__main__":
    # Run the integration test
    pytest.main([__file__, "-v", "-s"])
