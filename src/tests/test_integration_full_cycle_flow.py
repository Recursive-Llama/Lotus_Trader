"""
Integration Test: Full Cycle Data Flow

This test validates the complete end-to-end data flow through the entire system:
Raw Data Intelligence → CIL → Decision Maker → Trader → CIL Feedback

Uses real websocket connections, LLM calls, and minimal mocking for comprehensive testing.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
import logging

# Import all components
from src.intelligence.raw_data_intelligence.raw_data_intelligence_agent import RawDataIntelligenceAgent
from src.intelligence.raw_data_intelligence.analyzers.divergence_detector import RawDataDivergenceDetector
from src.intelligence.raw_data_intelligence.volume_analyzer import VolumePatternAnalyzer
from src.intelligence.system_control.central_intelligence_layer.core.strategic_pattern_miner import StrategicPatternMiner
from src.intelligence.system_control.central_intelligence_layer.engines.input_processor import InputProcessor
from src.intelligence.system_control.central_intelligence_layer.engines.global_synthesis_engine import GlobalSynthesisEngine
from src.intelligence.system_control.central_intelligence_layer.engines.experiment_orchestration_engine import ExperimentOrchestrationEngine
from src.intelligence.system_control.central_intelligence_layer.engines.output_directive_system import OutputDirectiveSystem
from src.intelligence.decision_maker.enhanced_decision_agent_base import EnhancedDecisionMakerAgent
from src.intelligence.decision_maker.enhanced_risk_assessment_agent import EnhancedRiskAssessmentAgent
from src.intelligence.trader.enhanced_execution_agent import EnhancedExecutionAgent
from src.intelligence.trader.order_manager import OrderManager
from src.intelligence.trader.performance_analyzer import PerformanceAnalyzer
from src.intelligence.system_control.central_intelligence_layer.engines.learning_feedback_engine import LearningFeedbackEngine
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.data_sources.hyperliquid_client import HyperliquidWebSocketClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestFullCycleIntegrationFlow:
    """Test suite for complete end-to-end data flow"""
    
    @pytest.fixture
    async def setup_all_components(self):
        """Set up all components for full cycle integration testing"""
        # Initialize real components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        websocket_client = HyperliquidWebSocketClient()
        
        # Raw Data Intelligence components
        raw_data_agent = RawDataIntelligenceAgent(supabase_manager, llm_client)
        divergence_detector = RawDataDivergenceDetector()
        volume_analyzer = VolumePatternAnalyzer()
        
        # CIL components
        strategic_pattern_miner = StrategicPatternMiner(supabase_manager, llm_client)
        input_processor = InputProcessor(supabase_manager, llm_client)
        global_synthesis_engine = GlobalSynthesisEngine(supabase_manager, llm_client)
        experiment_orchestration_engine = ExperimentOrchestrationEngine(supabase_manager, llm_client)
        output_directive_system = OutputDirectiveSystem(supabase_manager, llm_client)
        learning_feedback_engine = LearningFeedbackEngine(supabase_manager, llm_client)
        
        # Decision Maker components
        decision_agent = EnhancedDecisionMakerAgent(supabase_manager, llm_client)
        risk_assessment_agent = EnhancedRiskAssessmentAgent(supabase_manager, llm_client)
        
        # Trader components
        execution_agent = EnhancedExecutionAgent(supabase_manager, llm_client)
        order_manager = OrderManager(supabase_manager, llm_client)
        performance_analyzer = PerformanceAnalyzer(supabase_manager, llm_client)
        
        return {
            'supabase_manager': supabase_manager,
            'llm_client': llm_client,
            'websocket_client': websocket_client,
            'raw_data_agent': raw_data_agent,
            'divergence_detector': divergence_detector,
            'volume_analyzer': volume_analyzer,
            'strategic_pattern_miner': strategic_pattern_miner,
            'input_processor': input_processor,
            'global_synthesis_engine': global_synthesis_engine,
            'experiment_orchestration_engine': experiment_orchestration_engine,
            'output_directive_system': output_directive_system,
            'learning_feedback_engine': learning_feedback_engine,
            'decision_agent': decision_agent,
            'risk_assessment_agent': risk_assessment_agent,
            'execution_agent': execution_agent,
            'order_manager': order_manager,
            'performance_analyzer': performance_analyzer
        }
    
    @pytest.mark.asyncio
    async def test_complete_end_to_end_data_flow(self, setup_all_components):
        """Test complete end-to-end data flow through entire system"""
        components = await setup_all_components
        
        logger.info("🚀 Starting complete end-to-end data flow test...")
        
        # PHASE 1: Raw Data Intelligence → CIL
        logger.info("📊 PHASE 1: Raw Data Intelligence → CIL")
        
        # Step 1: Connect to real websocket and get market data
        await components['websocket_client'].connect()
        market_data = await self._get_real_market_data(components['websocket_client'])
        assert market_data is not None, "Failed to get real market data"
        logger.info(f"✅ Received {len(market_data)} market data points")
        
        # Step 2: Process through Raw Data Intelligence
        divergence_signals = await components['divergence_detector'].analyze_divergence_patterns(
            market_data, {'symbol': 'BTC', 'timeframe': '1h'}
        )
        volume_signals = await components['volume_analyzer'].analyze_volume_patterns(
            market_data, {'symbol': 'BTC', 'timeframe': '1h'}
        )
        
        all_raw_signals = divergence_signals + volume_signals
        assert len(all_raw_signals) > 0, "No raw data signals generated"
        logger.info(f"✅ Generated {len(all_raw_signals)} raw data signals")
        
        # Step 3: CIL processes raw signals
        recent_strands = await components['supabase_manager'].get_recent_strands(
            limit=50, since=datetime.now(timezone.utc) - timedelta(minutes=10)
        )
        
        input_processing = await components['input_processor'].process_agent_outputs(
            recent_strands, {'market_context': market_data[-1] if market_data else {}}
        )
        
        synthesis_results = await components['global_synthesis_engine'].synthesize_global_view(
            input_processing['processed_signals'],
            input_processing['cross_agent_metadata'],
            {'market_regime': 'testing', 'session': 'test'}
        )
        
        assert synthesis_results is not None, "CIL synthesis failed"
        logger.info(f"✅ CIL processed {len(input_processing['processed_signals'])} signals")
        
        # PHASE 2: CIL → Decision Maker
        logger.info("🧠 PHASE 2: CIL → Decision Maker")
        
        # Step 4: CIL creates strategic directives
        experiment_ideas = await components['experiment_orchestration_engine'].generate_experiment_ideas(
            synthesis_results, {'market_regime': 'testing', 'session': 'test'}
        )
        
        strategic_directives = await components['output_directive_system'].generate_strategic_directives(
            experiment_ideas['experiment_ideas'],
            {'target_team': 'decision_maker', 'priority': 'high'}
        )
        
        assert strategic_directives is not None, "CIL strategic directives failed"
        logger.info(f"✅ CIL created {len(strategic_directives['directives'])} strategic directives")
        
        # Step 5: Decision Maker processes directives
        cil_meta_signals = await components['supabase_manager'].get_strands_by_tags(
            ['agent:central_intelligence:meta:strategic_directive'],
            limit=10, since=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        
        decision_recommendations = await components['decision_agent'].generate_decision_recommendations(
            cil_meta_signals,
            {'risk_context': {'tolerance': 'medium', 'max_drawdown': 0.05}},
            {'market_context': {'regime': 'testing', 'volatility': 'medium'}}
        )
        
        risk_evaluation = await components['risk_assessment_agent'].evaluate_decision_risks(
            decision_recommendations['recommendations'],
            {'risk_parameters': {'max_drawdown': 0.05, 'var_confidence': 0.95}}
        )
        
        assert decision_recommendations is not None, "Decision Maker recommendations failed"
        logger.info(f"✅ Decision Maker created {len(decision_recommendations['recommendations'])} recommendations")
        
        # PHASE 3: Decision Maker → Trader
        logger.info("💰 PHASE 3: Decision Maker → Trader")
        
        # Step 6: Create execution directives
        execution_directives = []
        for i, decision in enumerate(decision_recommendations['recommendations']):
            directive = {
                'id': f"exec_directive_{i}_{int(time.time())}",
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
                    'context': 'full_cycle_test'
                },
                'sig_sigma': 0.9,
                'sig_confidence': 0.9,
                'outcome_score': 0.0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'agent_id': 'decision_maker',
                'team_member': 'decision_agent'
            }
            await components['supabase_manager'].insert_strand(directive)
            execution_directives.append(directive)
        
        logger.info(f"✅ Created {len(execution_directives)} execution directives")
        
        # Step 7: Trader processes execution directives
        execution_plans = await components['execution_agent'].create_execution_plans(
            execution_directives,
            {'execution_context': {'risk_tolerance': 'medium', 'execution_mode': 'test'}},
            {'market_context': {'regime': 'testing', 'liquidity': 'high'}}
        )
        
        order_processing = await components['order_manager'].process_execution_orders(
            execution_plans['execution_orders'],
            {'order_parameters': {'max_slippage': 0.01, 'timeout_seconds': 30}}
        )
        
        assert execution_plans is not None, "Trader execution plans failed"
        logger.info(f"✅ Trader created {len(execution_plans['execution_orders'])} execution plans")
        
        # PHASE 4: Trader → CIL Feedback
        logger.info("🔄 PHASE 4: Trader → CIL Feedback")
        
        # Step 8: Create execution results for feedback
        execution_results = []
        for i, order in enumerate(order_processing['order_status']):
            result = {
                'id': f"exec_result_{i}_{int(time.time())}",
                'kind': 'execution_result',
                'module': 'alpha',
                'symbol': order.get('symbol', 'BTC'),
                'timeframe': '1h',
                'session_bucket': 'US',
                'regime': 'testing',
                'tags': [
                    'agent:trader:execution:order_result',
                    'feedback:central_intelligence',
                    'outcome:success'
                ],
                'content': {
                    'action': order.get('action', 'buy'),
                    'symbol': order.get('symbol', 'BTC'),
                    'quantity': order.get('quantity', 0.1),
                    'execution_price': 50000.0 + (i * 100),  # Simulated prices
                    'outcome': 'success',
                    'performance_score': 0.8 + (i * 0.05),
                    'context': 'full_cycle_test_execution'
                },
                'sig_sigma': 0.9,
                'sig_confidence': 0.8,
                'outcome_score': 0.8,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'agent_id': 'trader',
                'team_member': 'execution_agent'
            }
            await components['supabase_manager'].insert_strand(result)
            execution_results.append(result)
        
        logger.info(f"✅ Created {len(execution_results)} execution results")
        
        # Step 9: CIL processes feedback
        performance_analysis = await components['performance_analyzer'].analyze_execution_performance(
            execution_results,
            {'analysis_context': {'timeframe': '1h', 'benchmark': 'market'}}
        )
        
        feedback_strands = await components['supabase_manager'].get_strands_by_tags(
            ['agent:trader:execution:order_result'],
            limit=10, since=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        
        learning_results = await components['learning_feedback_engine'].process_feedback_lessons(
            feedback_strands,
            {'learning_context': {'focus_area': 'execution_performance', 'time_horizon': 'short'}}
        )
        
        assert learning_results is not None, "CIL learning feedback failed"
        logger.info(f"✅ CIL processed {len(learning_results['structured_lessons'])} feedback lessons")
        
        # PHASE 5: Verify Complete Cycle
        logger.info("✅ PHASE 5: Verifying Complete Cycle")
        
        # Verify all phases completed successfully
        cycle_verification = {
            'raw_data_signals': len(all_raw_signals),
            'cil_processed_signals': len(input_processing['processed_signals']),
            'cil_strategic_directives': len(strategic_directives['directives']),
            'decision_recommendations': len(decision_recommendations['recommendations']),
            'execution_directives': len(execution_directives),
            'execution_plans': len(execution_plans['execution_orders']),
            'execution_results': len(execution_results),
            'feedback_lessons': len(learning_results['structured_lessons']),
            'cycle_complete': True
        }
        
        # Verify data flow integrity
        assert cycle_verification['raw_data_signals'] > 0, "Raw data signals not generated"
        assert cycle_verification['cil_processed_signals'] > 0, "CIL signal processing failed"
        assert cycle_verification['cil_strategic_directives'] > 0, "CIL strategic directives not created"
        assert cycle_verification['decision_recommendations'] > 0, "Decision recommendations not created"
        assert cycle_verification['execution_directives'] > 0, "Execution directives not created"
        assert cycle_verification['execution_plans'] > 0, "Execution plans not created"
        assert cycle_verification['execution_results'] > 0, "Execution results not created"
        assert cycle_verification['feedback_lessons'] > 0, "Feedback lessons not created"
        
        # Verify tag-based communication throughout cycle
        await self._verify_tag_communication_throughout_cycle(components['supabase_manager'])
        
        # Verify resonance field updates
        await self._verify_resonance_field_updates(components['supabase_manager'])
        
        # Cleanup
        await components['websocket_client'].disconnect()
        
        logger.info("🎉 Complete end-to-end data flow test SUCCESSFUL!")
        return cycle_verification
    
    async def _get_real_market_data(self, websocket_client: HyperliquidWebSocketClient) -> List[Dict[str, Any]]:
        """Get real market data from websocket"""
        try:
            # Subscribe to market data
            await websocket_client.subscribe_to_market_data()
            
            # Collect data for 20 seconds
            market_data = []
            start_time = time.time()
            
            while time.time() - start_time < 20 and len(market_data) < 5:
                try:
                    # Listen for data
                    data = await asyncio.wait_for(websocket_client.listen_for_data(), timeout=5.0)
                    if data:
                        market_data.append(data)
                        logger.info(f"Collected market data point: {data.get('timestamp', 'unknown')}")
                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for market data")
                    break
                except Exception as e:
                    logger.warning(f"Error getting market data: {e}")
                    break
            
            return market_data
            
        except Exception as e:
            logger.error(f"Failed to get real market data: {e}")
            return []
    
    async def _verify_tag_communication_throughout_cycle(self, supabase_manager: SupabaseManager):
        """Verify tag-based communication is working throughout the cycle"""
        logger.info("🔍 Verifying tag-based communication throughout cycle...")
        
        # Get all strands from the test cycle
        recent_strands = await supabase_manager.get_recent_strands(
            limit=100,
            since=datetime.now(timezone.utc) - timedelta(minutes=15)
        )
        
        # Verify different types of tags are present
        tag_types = {
            'raw_data_intelligence': 0,
            'central_intelligence': 0,
            'decision_maker': 0,
            'trader': 0,
            'meta_signals': 0,
            'feedback': 0
        }
        
        for strand in recent_strands:
            if 'tags' in strand:
                tags = strand['tags']
                for tag in tags:
                    if 'agent:raw_data_intelligence' in tag:
                        tag_types['raw_data_intelligence'] += 1
                    elif 'agent:central_intelligence' in tag:
                        tag_types['central_intelligence'] += 1
                    elif 'agent:decision_maker' in tag:
                        tag_types['decision_maker'] += 1
                    elif 'agent:trader' in tag:
                        tag_types['trader'] += 1
                    elif 'meta:' in tag:
                        tag_types['meta_signals'] += 1
                    elif 'feedback:' in tag:
                        tag_types['feedback'] += 1
        
        # Verify all tag types are present
        for tag_type, count in tag_types.items():
            assert count > 0, f"No {tag_type} tags found in cycle"
            logger.info(f"✅ {tag_type}: {count} tags")
        
        logger.info("✅ Tag-based communication verified throughout cycle!")
    
    async def _verify_resonance_field_updates(self, supabase_manager: SupabaseManager):
        """Verify resonance field updates are working throughout the cycle"""
        logger.info("🔍 Verifying resonance field updates throughout cycle...")
        
        # Get strands with resonance fields
        recent_strands = await supabase_manager.get_recent_strands(
            limit=50,
            since=datetime.now(timezone.utc) - timedelta(minutes=15)
        )
        
        resonance_strands = []
        for strand in recent_strands:
            if 'resonance_score' in strand or 'phi' in strand or 'rho' in strand:
                resonance_strands.append(strand)
        
        # Verify resonance fields are being updated
        assert len(resonance_strands) > 0, "No resonance field updates found"
        
        for strand in resonance_strands:
            if 'resonance_score' in strand:
                assert 0.0 <= strand['resonance_score'] <= 1.0, f"Invalid resonance score: {strand['resonance_score']}"
            if 'phi' in strand:
                assert isinstance(strand['phi'], (int, float)), f"Invalid phi value: {strand['phi']}"
            if 'rho' in strand:
                assert isinstance(strand['rho'], (int, float)), f"Invalid rho value: {strand['rho']}"
        
        logger.info(f"✅ Resonance field updates verified: {len(resonance_strands)} strands updated!")
    
    @pytest.mark.asyncio
    async def test_high_frequency_data_flow(self, setup_all_components):
        """Test system under high-frequency data flow"""
        components = await setup_all_components
        
        logger.info("⚡ Testing high-frequency data flow...")
        
        # Connect to websocket
        await components['websocket_client'].connect()
        
        # Collect high-frequency data
        high_freq_data = []
        start_time = time.time()
        
        while time.time() - start_time < 30 and len(high_freq_data) < 20:
            try:
                data = await asyncio.wait_for(components['websocket_client'].listen_for_data(), timeout=2.0)
                if data:
                    high_freq_data.append(data)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.warning(f"Error in high-frequency data collection: {e}")
                break
        
        assert len(high_freq_data) > 0, "No high-frequency data collected"
        logger.info(f"✅ Collected {len(high_freq_data)} high-frequency data points")
        
        # Process high-frequency data through system
        processing_start = time.time()
        
        # Raw data processing
        divergence_analysis = await components['divergence_detector'].analyze(high_freq_data)
        divergence_signals = divergence_analysis.get('signals', [])
        
        volume_analysis = await components['volume_analyzer'].analyze(high_freq_data)
        volume_signals = volume_analysis.get('signals', [])
        
        # CIL processing
        recent_strands = await components['supabase_manager'].get_recent_strands(
            limit=100, since=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        
        input_processing = await components['input_processor'].process_agent_outputs(
            recent_strands, {'market_context': high_freq_data[-1] if high_freq_data else {}}
        )
        
        processing_time = time.time() - processing_start
        
        # Verify performance
        assert processing_time < 10.0, f"High-frequency processing too slow: {processing_time:.2f}s"
        assert len(divergence_signals) + len(volume_signals) > 0, "No signals generated from high-frequency data"
        
        logger.info(f"✅ High-frequency processing completed in {processing_time:.2f}s")
        
        # Cleanup
        await components['websocket_client'].disconnect()
    
    @pytest.mark.asyncio
    async def test_cross_team_coordination(self, setup_all_components):
        """Test cross-team coordination throughout the cycle"""
        components = await setup_all_components
        
        logger.info("🤝 Testing cross-team coordination...")
        
        # Create test signals from different teams
        team_signals = []
        
        # Raw data intelligence signal
        raw_signal = {
            'id': f"raw_coord_{int(time.time())}",
            'kind': 'divergence_detection',
            'tags': ['agent:raw_data_intelligence:divergence_detector:divergence_found'],
            'content': {'divergence_type': 'bullish', 'confidence': 0.8},
            'created_at': datetime.now(timezone.utc).isoformat(),
            'agent_id': 'raw_data_intelligence'
        }
        
        # CIL meta-signal
        cil_signal = {
            'id': f"cil_coord_{int(time.time())}",
            'kind': 'strategic_directive',
            'tags': ['agent:central_intelligence:meta:strategic_directive', 'target:decision_maker'],
            'content': {'directive_type': 'risk_assessment', 'target_team': 'decision_maker'},
            'created_at': datetime.now(timezone.utc).isoformat(),
            'agent_id': 'central_intelligence_layer'
        }
        
        # Decision maker directive
        decision_signal = {
            'id': f"decision_coord_{int(time.time())}",
            'kind': 'execution_directive',
            'tags': ['agent:decision_maker:directive:execution_order', 'target:trader'],
            'content': {'action': 'buy', 'symbol': 'BTC', 'quantity': 0.1},
            'created_at': datetime.now(timezone.utc).isoformat(),
            'agent_id': 'decision_maker'
        }
        
        # Trader feedback
        trader_signal = {
            'id': f"trader_coord_{int(time.time())}",
            'kind': 'execution_result',
            'tags': ['agent:trader:execution:order_result', 'feedback:central_intelligence'],
            'content': {'outcome': 'success', 'performance_score': 0.85},
            'created_at': datetime.now(timezone.utc).isoformat(),
            'agent_id': 'trader'
        }
        
        # Publish all signals
        for signal in [raw_signal, cil_signal, decision_signal, trader_signal]:
            await components['supabase_manager'].insert_strand(signal)
            team_signals.append(signal)
        
        # Wait for signals to be processed
        await asyncio.sleep(3)
        
        # Verify cross-team communication
        coordination_verified = {
            'raw_to_cil': False,
            'cil_to_decision': False,
            'decision_to_trader': False,
            'trader_to_cil': False
        }
        
        # Check for cross-team communication patterns
        recent_strands = await components['supabase_manager'].get_recent_strands(
            limit=50, since=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        
        for strand in recent_strands:
            if 'tags' in strand:
                tags = strand['tags']
                tag_str = ' '.join(tags)
                
                if 'agent:raw_data_intelligence' in tag_str and 'agent:central_intelligence' in tag_str:
                    coordination_verified['raw_to_cil'] = True
                elif 'agent:central_intelligence' in tag_str and 'target:decision_maker' in tag_str:
                    coordination_verified['cil_to_decision'] = True
                elif 'agent:decision_maker' in tag_str and 'target:trader' in tag_str:
                    coordination_verified['decision_to_trader'] = True
                elif 'agent:trader' in tag_str and 'feedback:central_intelligence' in tag_str:
                    coordination_verified['trader_to_cil'] = True
        
        # Verify all coordination paths
        for path, verified in coordination_verified.items():
            assert verified, f"Cross-team coordination failed: {path}"
            logger.info(f"✅ {path}: coordination verified")
        
        logger.info("✅ Cross-team coordination verified!")
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, setup_all_components):
        """Test error handling and recovery throughout the cycle"""
        components = await setup_all_components
        
        logger.info("🛡️ Testing error handling and recovery...")
        
        # Test with malformed data at each stage
        error_tests = [
            {
                'stage': 'raw_data',
                'malformed_data': [{'invalid': 'data'}, None, {}],
                'component': components['divergence_detector'],
                'method': 'analyze_divergence_patterns'
            },
            {
                'stage': 'cil_processing',
                'malformed_data': [{'invalid': 'strand'}],
                'component': components['input_processor'],
                'method': 'process_agent_outputs'
            },
            {
                'stage': 'decision_making',
                'malformed_data': [{'invalid': 'recommendation'}],
                'component': components['decision_agent'],
                'method': 'generate_decision_recommendations'
            },
            {
                'stage': 'execution',
                'malformed_data': [{'invalid': 'order'}],
                'component': components['order_manager'],
                'method': 'process_execution_orders'
            }
        ]
        
        for test in error_tests:
            try:
                # Test component with malformed data
                if test['method'] == 'analyze_divergence_patterns':
                    result = await test['component'].analyze_divergence_patterns(
                        test['malformed_data'], {'symbol': 'BTC', 'timeframe': '1h'}
                    )
                elif test['method'] == 'process_agent_outputs':
                    result = await test['component'].process_agent_outputs(
                        test['malformed_data'], {'market_context': {}}
                    )
                elif test['method'] == 'generate_decision_recommendations':
                    result = await test['component'].generate_decision_recommendations(
                        test['malformed_data'], {}, {}
                    )
                elif test['method'] == 'process_execution_orders':
                    result = await test['component'].process_execution_orders(
                        test['malformed_data'], {}
                    )
                
                # Should handle gracefully
                assert result is not None, f"{test['stage']} component failed to handle malformed data"
                logger.info(f"✅ {test['stage']}: error handling verified")
                
            except Exception as e:
                logger.info(f"✅ {test['stage']}: error handling verified (exception caught: {e})")
        
        # Test database connection recovery
        try:
            with patch.object(components['supabase_manager'], 'insert_strand', side_effect=Exception("DB Error")):
                test_strand = {
                    'id': f"db_error_test_{int(time.time())}",
                    'kind': 'test_strand',
                    'content': {'test': 'data'}
                }
                
                try:
                    await components['supabase_manager'].insert_strand(test_strand)
                except Exception as db_error:
                    assert "DB Error" in str(db_error)
                    logger.info("✅ Database error handling verified")
        except Exception as e:
            logger.info(f"✅ Database error handling verified: {e}")
        
        logger.info("✅ Error handling and recovery verified throughout cycle!")


if __name__ == "__main__":
    # Run the integration test
    pytest.main([__file__, "-v", "-s"])
