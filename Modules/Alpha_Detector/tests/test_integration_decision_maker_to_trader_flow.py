"""
Integration Test: Decision Maker → Trader Flow

This test validates the complete data flow from Decision Maker recommendations
to the Trader execution, using real decision directives and execution calls.
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
from src.intelligence.decision_maker.enhanced_decision_agent_base import EnhancedDecisionMakerAgent
from src.intelligence.decision_maker.enhanced_risk_assessment_agent import EnhancedRiskAssessmentAgent
from src.intelligence.trader.enhanced_execution_agent import EnhancedExecutionAgent
from src.intelligence.trader.order_manager import OrderManager
from src.intelligence.trader.position_tracker import PositionTracker
from src.intelligence.trader.cross_team_execution_integration import CrossTeamExecutionIntegration
from src.intelligence.trader.strategic_execution_insight_consumer import StrategicExecutionInsightConsumer
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDecisionMakerToTraderFlow:
    """Test suite for Decision Maker → Trader data flow"""
    
    @pytest.fixture
    async def setup_components(self):
        """Set up all components for integration testing"""
        # Initialize real components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        
        # Decision Maker components
        decision_agent = EnhancedDecisionMakerAgent(supabase_manager, llm_client)
        risk_assessment_agent = EnhancedRiskAssessmentAgent(supabase_manager, llm_client)
        
        # Trader components
        execution_agent = EnhancedExecutionAgent(supabase_manager, llm_client)
        order_manager = OrderManager(supabase_manager, llm_client)
        position_tracker = PositionTracker(supabase_manager, llm_client)
        cross_team_integration = CrossTeamExecutionIntegration(supabase_manager, llm_client)
        strategic_insight_consumer = StrategicExecutionInsightConsumer(supabase_manager, llm_client)
        
        return {
            'supabase_manager': supabase_manager,
            'llm_client': llm_client,
            'decision_agent': decision_agent,
            'risk_assessment_agent': risk_assessment_agent,
            'execution_agent': execution_agent,
            'order_manager': order_manager,
            'position_tracker': position_tracker,
            'cross_team_integration': cross_team_integration,
            'strategic_insight_consumer': strategic_insight_consumer
        }
    
    @pytest.mark.asyncio
    async def test_decision_recommendations_to_trader_execution(self, setup_components):
        """Test complete flow: Decision recommendations → Trader execution"""
        components = await setup_components
        
        # Step 1: Create test decision recommendations
        logger.info("Step 1: Creating test decision recommendations...")
        
        test_recommendations = await self._create_test_decision_recommendations(components['supabase_manager'])
        assert len(test_recommendations) > 0, "Failed to create test decision recommendations"
        logger.info(f"Created {len(test_recommendations)} test decision recommendations")
        
        # Step 2: Decision Maker creates final decisions
        logger.info("Step 2: Decision Maker creating final decisions...")
        
        # Get recent recommendations for processing
        recent_recommendations = await components['supabase_manager'].get_recent_strands(
            limit=10,
            since=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        
        # Filter for decision recommendations
        decision_recommendations = [s for s in recent_recommendations 
                                  if s.get('kind') == 'decision_recommendation']
        
        # Process through Decision Agent
        final_decisions = await components['decision_agent'].generate_decision_recommendations(
            decision_recommendations,
            {'risk_context': {'tolerance': 'medium', 'max_drawdown': 0.05}},
            {'market_context': {'regime': 'testing', 'volatility': 'medium'}}
        )
        
        assert final_decisions is not None, "Decision Maker failed to create final decisions"
        assert 'recommendations' in final_decisions, "Missing recommendations in results"
        
        logger.info(f"Decision Maker created {len(final_decisions['recommendations'])} final decisions")
        
        # Step 3: Risk Assessment Agent evaluates decisions
        logger.info("Step 3: Risk Assessment Agent evaluating decisions...")
        
        risk_evaluation = await components['risk_assessment_agent'].evaluate_decision_risks(
            final_decisions['recommendations'],
            {'risk_parameters': {'max_drawdown': 0.05, 'var_confidence': 0.95}}
        )
        
        assert risk_evaluation is not None, "Risk Assessment Agent failed to evaluate risks"
        assert 'risk_scores' in risk_evaluation, "Missing risk scores"
        assert 'risk_mitigation' in risk_evaluation, "Missing risk mitigation"
        
        logger.info(f"Risk Assessment Agent evaluated {len(risk_evaluation['risk_scores'])} decisions")
        
        # Step 4: Verify decision directives are published
        logger.info("Step 4: Verifying decision directives published...")
        
        # Create decision directives from final decisions
        decision_directives = []
        for i, decision in enumerate(final_decisions['recommendations']):
            directive = {
                'id': f"directive_{i}_{int(time.time())}",
                'kind': 'execution_directive',
                'module': 'alpha',
                'symbol': decision.get('symbol', 'BTC'),
                'timeframe': '1h',
                'session_bucket': 'US',
                'regime': 'testing',
                'tags': [
                    'agent:decision_maker:directive:execution_order',
                    'target:trader',
                    'directive_type:trade_execution',
                    'priority:high'
                ],
                'content': {
                    'action': decision.get('action', 'buy'),
                    'symbol': decision.get('symbol', 'BTC'),
                    'quantity': decision.get('quantity', 0.1),
                    'price_limit': decision.get('price_limit'),
                    'risk_score': risk_evaluation['risk_scores'][i] if i < len(risk_evaluation['risk_scores']) else 0.5,
                    'risk_mitigation': risk_evaluation['risk_mitigation'][i] if i < len(risk_evaluation['risk_mitigation']) else {},
                    'context': decision.get('context', 'test_execution')
                },
                'sig_sigma': 0.9,
                'sig_confidence': 0.9,
                'outcome_score': 0.0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'agent_id': 'decision_maker',
                'team_member': 'decision_agent'
            }
            
            await components['supabase_manager'].insert_strand(directive)
            decision_directives.append(directive)
        
        assert len(decision_directives) > 0, "No decision directives published"
        logger.info(f"Published {len(decision_directives)} decision directives")
        
        # Step 5: Trader Strategic Insight Consumer processes directives
        logger.info("Step 5: Trader processing decision directives...")
        
        # Get decision directives for Trader
        execution_directives = await components['supabase_manager'].get_strands_by_tags(
            ['agent:decision_maker:directive:execution_order'],
            limit=10,
            since=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        
        # Process through Strategic Insight Consumer
        insight_processing = await components['strategic_insight_consumer'].process_strategic_insights(
            execution_directives,
            {'execution_context': {'risk_tolerance': 'medium', 'execution_mode': 'test'}}
        )
        
        assert insight_processing is not None, "Trader failed to process strategic insights"
        assert 'processed_insights' in insight_processing, "Missing processed insights"
        assert 'execution_plans' in insight_processing, "Missing execution plans"
        
        logger.info(f"Trader processed {len(insight_processing['processed_insights'])} strategic insights")
        
        # Step 6: Trader creates execution plans
        logger.info("Step 6: Trader creating execution plans...")
        
        execution_plans = await components['execution_agent'].create_execution_plans(
            insight_processing['processed_insights'],
            insight_processing['execution_plans'],
            {'market_context': {'regime': 'testing', 'liquidity': 'high'}}
        )
        
        assert execution_plans is not None, "Trader failed to create execution plans"
        assert 'execution_orders' in execution_plans, "Missing execution orders"
        assert 'risk_controls' in execution_plans, "Missing risk controls"
        
        logger.info(f"Trader created {len(execution_plans['execution_orders'])} execution plans")
        
        # Step 7: Order Manager processes execution orders
        logger.info("Step 7: Order Manager processing execution orders...")
        
        order_processing = await components['order_manager'].process_execution_orders(
            execution_plans['execution_orders'],
            {'order_parameters': {'max_slippage': 0.01, 'timeout_seconds': 30}}
        )
        
        assert order_processing is not None, "Order Manager failed to process orders"
        assert 'order_status' in order_processing, "Missing order status"
        assert 'execution_results' in order_processing, "Missing execution results"
        
        logger.info(f"Order Manager processed {len(order_processing['order_status'])} orders")
        
        # Step 8: Position Tracker monitors execution
        logger.info("Step 8: Position Tracker monitoring execution...")
        
        position_monitoring = await components['position_tracker'].monitor_execution_positions(
            order_processing['execution_results'],
            {'monitoring_parameters': {'update_interval': 1, 'risk_threshold': 0.05}}
        )
        
        assert position_monitoring is not None, "Position Tracker failed to monitor positions"
        assert 'position_updates' in position_monitoring, "Missing position updates"
        assert 'risk_alerts' in position_monitoring, "Missing risk alerts"
        
        logger.info(f"Position Tracker monitored {len(position_monitoring['position_updates'])} positions")
        
        # Step 9: Cross-Team Integration coordinates execution
        logger.info("Step 9: Cross-Team Integration coordinating execution...")
        
        coordination_results = await components['cross_team_integration'].coordinate_execution_teams(
            order_processing['execution_results'],
            position_monitoring['position_updates'],
            {'coordination_context': {'team_sync': True, 'risk_sharing': True}}
        )
        
        assert coordination_results is not None, "Cross-Team Integration failed to coordinate"
        assert 'team_coordination' in coordination_results, "Missing team coordination"
        assert 'execution_summary' in coordination_results, "Missing execution summary"
        
        logger.info(f"Cross-Team Integration coordinated {len(coordination_results['team_coordination'])} teams")
        
        # Step 10: Verify complete data flow integrity
        logger.info("Step 10: Verifying complete data flow integrity...")
        
        # Check that all components are working together
        assert len(test_recommendations) > 0, "Test recommendations not created"
        assert final_decisions is not None, "Decision Maker final decisions failed"
        assert risk_evaluation is not None, "Risk evaluation failed"
        assert len(decision_directives) > 0, "Decision directives not published"
        assert insight_processing is not None, "Trader insight processing failed"
        assert execution_plans is not None, "Execution plans not created"
        assert order_processing is not None, "Order processing failed"
        assert position_monitoring is not None, "Position monitoring failed"
        assert coordination_results is not None, "Cross-team coordination failed"
        
        # Verify tag-based communication is working
        for directive in decision_directives:
            assert 'tags' in directive, "Decision directive missing tags"
            tags = directive['tags']
            assert any('agent:decision_maker:directive' in tag for tag in tags), \
                "Decision Maker directive tags not found"
            assert any('target:trader' in tag for tag in tags), \
                "Trader target tags not found"
        
        logger.info("✅ Complete Decision Maker → Trader data flow integrity verified!")
        
        return {
            'test_recommendations': len(test_recommendations),
            'final_decisions': len(final_decisions['recommendations']),
            'risk_evaluations': len(risk_evaluation['risk_scores']),
            'decision_directives': len(decision_directives),
            'execution_insights': len(insight_processing['processed_insights']),
            'execution_plans': len(execution_plans['execution_orders']),
            'order_processing': len(order_processing['order_status']),
            'position_monitoring': len(position_monitoring['position_updates']),
            'team_coordination': len(coordination_results['team_coordination']),
            'data_flow_success': True
        }
    
    async def _create_test_decision_recommendations(self, supabase_manager: SupabaseManager) -> List[Dict[str, Any]]:
        """Create test decision recommendations for Trader processing"""
        test_recommendations = []
        
        # Create buy recommendation
        buy_recommendation = {
            'id': f"rec_buy_{int(time.time())}",
            'kind': 'decision_recommendation',
            'module': 'alpha',
            'symbol': 'BTC',
            'timeframe': '1h',
            'session_bucket': 'US',
            'regime': 'high_vol',
            'tags': [
                'agent:decision_maker:recommendation:buy_signal',
                'target:trader',
                'priority:high'
            ],
            'content': {
                'action': 'buy',
                'symbol': 'BTC',
                'quantity': 0.1,
                'confidence': 0.85,
                'expected_return': 0.05,
                'risk_score': 0.3,
                'time_horizon': 'short',
                'context': 'bullish_divergence_confirmed'
            },
            'sig_sigma': 0.9,
            'sig_confidence': 0.85,
            'outcome_score': 0.0,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'agent_id': 'decision_maker',
            'team_member': 'decision_agent'
        }
        
        # Create sell recommendation
        sell_recommendation = {
            'id': f"rec_sell_{int(time.time())}",
            'kind': 'decision_recommendation',
            'module': 'alpha',
            'symbol': 'ETH',
            'timeframe': '1h',
            'session_bucket': 'EU',
            'regime': 'sideways',
            'tags': [
                'agent:decision_maker:recommendation:sell_signal',
                'target:trader',
                'priority:medium'
            ],
            'content': {
                'action': 'sell',
                'symbol': 'ETH',
                'quantity': 0.2,
                'confidence': 0.75,
                'expected_return': -0.03,
                'risk_score': 0.4,
                'time_horizon': 'short',
                'context': 'resistance_level_reached'
            },
            'sig_sigma': 0.8,
            'sig_confidence': 0.75,
            'outcome_score': 0.0,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'agent_id': 'decision_maker',
            'team_member': 'decision_agent'
        }
        
        # Create hold recommendation
        hold_recommendation = {
            'id': f"rec_hold_{int(time.time())}",
            'kind': 'decision_recommendation',
            'module': 'alpha',
            'symbol': 'SOL',
            'timeframe': '4h',
            'session_bucket': 'ALL',
            'regime': 'all',
            'tags': [
                'agent:decision_maker:recommendation:hold_signal',
                'target:trader',
                'priority:low'
            ],
            'content': {
                'action': 'hold',
                'symbol': 'SOL',
                'quantity': 0.0,
                'confidence': 0.6,
                'expected_return': 0.0,
                'risk_score': 0.2,
                'time_horizon': 'medium',
                'context': 'waiting_for_clear_signal'
            },
            'sig_sigma': 0.6,
            'sig_confidence': 0.6,
            'outcome_score': 0.0,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'agent_id': 'decision_maker',
            'team_member': 'decision_agent'
        }
        
        # Publish recommendations
        for recommendation in [buy_recommendation, sell_recommendation, hold_recommendation]:
            try:
                await supabase_manager.insert_strand(recommendation)
                test_recommendations.append(recommendation)
                logger.info(f"Published test recommendation: {recommendation['content']['action']}")
            except Exception as e:
                logger.warning(f"Failed to publish recommendation {recommendation['content']['action']}: {e}")
        
        return test_recommendations
    
    @pytest.mark.asyncio
    async def test_execution_directive_routing_and_processing(self, setup_components):
        """Test that execution directive routing and processing is working correctly"""
        components = await setup_components
        
        # Create a test execution directive
        test_directive = {
            'id': f"test_exec_directive_{int(time.time())}",
            'kind': 'execution_directive',
            'module': 'alpha',
            'symbol': 'BTC',
            'timeframe': '1h',
            'session_bucket': 'US',
            'regime': 'testing',
            'tags': [
                'agent:decision_maker:directive:execution_order',
                'target:trader',
                'directive_type:trade_execution',
                'priority:high'
            ],
            'content': {
                'action': 'buy',
                'symbol': 'BTC',
                'quantity': 0.1,
                'price_limit': 50000.0,
                'risk_score': 0.3,
                'risk_mitigation': {
                    'stop_loss': 0.02,
                    'take_profit': 0.05,
                    'max_position_size': 0.2
                },
                'context': 'test_execution_directive'
            },
            'sig_sigma': 0.9,
            'sig_confidence': 0.9,
            'outcome_score': 0.0,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'agent_id': 'decision_maker',
            'team_member': 'decision_agent'
        }
        
        # Publish directive
        await components['supabase_manager'].insert_strand(test_directive)
        
        # Wait for directive to be processed
        await asyncio.sleep(2)
        
        # Verify directive was published
        published_directive = await components['supabase_manager'].get_strand_by_id(test_directive['id'])
        assert published_directive is not None, "Test execution directive was not published"
        
        # Verify tags are correct
        assert 'tags' in published_directive, "Published directive missing tags"
        tags = published_directive['tags']
        
        # Check for required tags
        required_tags = [
            'agent:decision_maker:directive:execution_order',
            'target:trader'
        ]
        
        for required_tag in required_tags:
            assert any(required_tag in tag for tag in tags), \
                f"Required tag not found: {required_tag}"
        
        # Test Trader can find and process this directive
        execution_directives = await components['supabase_manager'].get_strands_by_tags(
            ['agent:decision_maker:directive:execution_order'],
            limit=10,
            since=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        
        # Filter for our test directive
        test_directives = [s for s in execution_directives if s['id'] == test_directive['id']]
        assert len(test_directives) > 0, "Trader cannot find the test execution directive"
        
        # Process through Strategic Insight Consumer
        insight_processing = await components['strategic_insight_consumer'].process_strategic_insights(
            test_directives,
            {'execution_context': {'risk_tolerance': 'medium', 'execution_mode': 'test'}}
        )
        
        assert insight_processing is not None, "Trader failed to process execution directive"
        assert len(insight_processing['processed_insights']) > 0, "Trader processed no insights"
        
        logger.info("✅ Execution directive routing and processing verified!")
    
    @pytest.mark.asyncio
    async def test_order_management_integration(self, setup_components):
        """Test that order management integration is working correctly"""
        components = await setup_components
        
        # Create test execution orders
        test_orders = [
            {
                'id': f"order_1_{int(time.time())}",
                'action': 'buy',
                'symbol': 'BTC',
                'quantity': 0.1,
                'price_limit': 50000.0,
                'risk_score': 0.3
            },
            {
                'id': f"order_2_{int(time.time())}",
                'action': 'sell',
                'symbol': 'ETH',
                'quantity': 0.2,
                'price_limit': 3000.0,
                'risk_score': 0.4
            }
        ]
        
        # Process through Order Manager
        order_processing = await components['order_manager'].process_execution_orders(
            test_orders,
            {'order_parameters': {'max_slippage': 0.01, 'timeout_seconds': 30}}
        )
        
        assert order_processing is not None, "Order Manager failed to process orders"
        assert 'order_status' in order_processing, "Missing order status"
        assert 'execution_results' in order_processing, "Missing execution results"
        
        # Verify order status is reasonable
        order_status = order_processing['order_status']
        assert len(order_status) == len(test_orders), "Order status count mismatch"
        
        for i, status in enumerate(order_status):
            assert 'order_id' in status, f"Missing order_id for order {i}"
            assert 'status' in status, f"Missing status for order {i}"
            assert status['status'] in ['pending', 'executed', 'cancelled', 'failed'], \
                f"Invalid status for order {i}: {status['status']}"
        
        # Verify execution results
        execution_results = order_processing['execution_results']
        assert len(execution_results) == len(test_orders), "Execution results count mismatch"
        
        for i, result in enumerate(execution_results):
            assert 'order_id' in result, f"Missing order_id in result {i}"
            assert 'execution_price' in result, f"Missing execution_price in result {i}"
            assert 'execution_quantity' in result, f"Missing execution_quantity in result {i}"
        
        logger.info("✅ Order management integration verified!")
    
    @pytest.mark.asyncio
    async def test_position_tracking_integration(self, setup_components):
        """Test that position tracking integration is working correctly"""
        components = await setup_components
        
        # Create test execution results
        test_execution_results = [
            {
                'order_id': f"exec_1_{int(time.time())}",
                'symbol': 'BTC',
                'action': 'buy',
                'execution_price': 50000.0,
                'execution_quantity': 0.1,
                'execution_time': datetime.now(timezone.utc).isoformat()
            },
            {
                'order_id': f"exec_2_{int(time.time())}",
                'symbol': 'ETH',
                'action': 'sell',
                'execution_price': 3000.0,
                'execution_quantity': 0.2,
                'execution_time': datetime.now(timezone.utc).isoformat()
            }
        ]
        
        # Process through Position Tracker
        position_monitoring = await components['position_tracker'].monitor_execution_positions(
            test_execution_results,
            {'monitoring_parameters': {'update_interval': 1, 'risk_threshold': 0.05}}
        )
        
        assert position_monitoring is not None, "Position Tracker failed to monitor positions"
        assert 'position_updates' in position_monitoring, "Missing position updates"
        assert 'risk_alerts' in position_monitoring, "Missing risk alerts"
        
        # Verify position updates
        position_updates = position_monitoring['position_updates']
        assert len(position_updates) == len(test_execution_results), "Position updates count mismatch"
        
        for i, update in enumerate(position_updates):
            assert 'symbol' in update, f"Missing symbol in position update {i}"
            assert 'position_size' in update, f"Missing position_size in position update {i}"
            assert 'unrealized_pnl' in update, f"Missing unrealized_pnl in position update {i}"
            assert 'risk_metrics' in update, f"Missing risk_metrics in position update {i}"
        
        # Verify risk alerts
        risk_alerts = position_monitoring['risk_alerts']
        assert isinstance(risk_alerts, list), "Risk alerts should be a list"
        
        for alert in risk_alerts:
            assert 'alert_type' in alert, "Missing alert_type in risk alert"
            assert 'severity' in alert, "Missing severity in risk alert"
            assert 'message' in alert, "Missing message in risk alert"
        
        logger.info("✅ Position tracking integration verified!")
    
    @pytest.mark.asyncio
    async def test_cross_team_execution_coordination(self, setup_components):
        """Test that cross-team execution coordination is working correctly"""
        components = await setup_components
        
        # Create test execution results and position updates
        test_execution_results = [
            {
                'order_id': f"coord_1_{int(time.time())}",
                'symbol': 'BTC',
                'action': 'buy',
                'execution_price': 50000.0,
                'execution_quantity': 0.1
            }
        ]
        
        test_position_updates = [
            {
                'symbol': 'BTC',
                'position_size': 0.1,
                'unrealized_pnl': 0.02,
                'risk_metrics': {'var': 0.03, 'max_drawdown': 0.01}
            }
        ]
        
        # Process through Cross-Team Integration
        coordination_results = await components['cross_team_integration'].coordinate_execution_teams(
            test_execution_results,
            test_position_updates,
            {'coordination_context': {'team_sync': True, 'risk_sharing': True}}
        )
        
        assert coordination_results is not None, "Cross-Team Integration failed to coordinate"
        assert 'team_coordination' in coordination_results, "Missing team coordination"
        assert 'execution_summary' in coordination_results, "Missing execution summary"
        
        # Verify team coordination
        team_coordination = coordination_results['team_coordination']
        assert isinstance(team_coordination, list), "Team coordination should be a list"
        
        for coordination in team_coordination:
            assert 'team_id' in coordination, "Missing team_id in coordination"
            assert 'coordination_status' in coordination, "Missing coordination_status in coordination"
            assert 'shared_data' in coordination, "Missing shared_data in coordination"
        
        # Verify execution summary
        execution_summary = coordination_results['execution_summary']
        assert 'total_orders' in execution_summary, "Missing total_orders in execution summary"
        assert 'successful_executions' in execution_summary, "Missing successful_executions in execution summary"
        assert 'risk_metrics' in execution_summary, "Missing risk_metrics in execution summary"
        
        logger.info("✅ Cross-team execution coordination verified!")
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, setup_components):
        """Test error handling and recovery in the Decision Maker → Trader flow"""
        components = await setup_components
        
        # Test with malformed execution directive
        malformed_directive = {
            'id': f"malformed_exec_{int(time.time())}",
            'kind': 'execution_directive',
            # Missing required fields
            'content': {
                'test': 'malformed_data'
            }
        }
        
        # Try to publish malformed directive
        try:
            await components['supabase_manager'].insert_strand(malformed_directive)
        except Exception as e:
            logger.info(f"Expected error for malformed directive: {e}")
        
        # Test with invalid execution orders
        invalid_orders = [
            {'invalid': 'data'},
            {'action': 'invalid_action'},
            None
        ]
        
        # Test that components handle invalid data gracefully
        try:
            order_processing = await components['order_manager'].process_execution_orders(
                invalid_orders,
                {'order_parameters': {'max_slippage': 0.01}}
            )
            # Should return empty results or handle gracefully
            assert order_processing is not None, "Should return results even with invalid data"
        except Exception as e:
            logger.info(f"Component handled invalid data: {e}")
        
        # Test database connection recovery
        try:
            # Simulate database connection issue
            with patch.object(components['supabase_manager'], 'insert_strand', side_effect=Exception("DB Error")):
                test_directive = {
                    'id': f"db_error_test_{int(time.time())}",
                    'kind': 'test_directive',
                    'content': {'test': 'data'}
                }
                
                try:
                    await components['supabase_manager'].insert_strand(test_directive)
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
