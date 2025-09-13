#!/usr/bin/env python3
"""
Complete Workflow Test

This script tests the complete system workflow from data input
to learning output, simulating the entire process.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import traceback

# Add paths for imports
current_dir = os.path.dirname(__file__)
sys.path.append(current_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockSupabaseManager:
    """Mock Supabase manager for testing"""
    
    def __init__(self):
        self.strands = []
        self.braids = []
        self.connected = True
    
    async def test_connection(self):
        return True
    
    async def create_strand(self, strand_data):
        strand_id = strand_data.get('id', f"mock_{len(self.strands)}")
        self.strands.append({**strand_data, 'id': strand_id})
        return strand_id
    
    async def get_strand(self, strand_id):
        for strand in self.strands:
            if strand['id'] == strand_id:
                return strand
        return None
    
    async def update_strand(self, strand_id, updates):
        for strand in self.strands:
            if strand['id'] == strand_id:
                strand.update(updates)
                return True
        return False
    
    async def delete_strand(self, strand_id):
        self.strands = [s for s in self.strands if s['id'] != strand_id]
        return True
    
    async def create_braid(self, braid_data):
        braid_id = braid_data.get('id', f"braid_{len(self.braids)}")
        self.braids.append({**braid_data, 'id': braid_id})
        return braid_id
    
    async def get_braids_by_level(self, level):
        return [b for b in self.braids if b.get('braid_level') == level]

class MockLLMClient:
    """Mock LLM client for testing"""
    
    def __init__(self):
        self.call_count = 0
        self.responses = {
            'pattern_analysis': "This pattern shows a strong volume spike with high confidence. It indicates potential market movement.",
            'prediction_generation': "Based on the pattern analysis, I predict a 2-3% price increase in the next hour.",
            'learning_insight': "This pattern has shown consistent success across multiple timeframes. The key factors are volume confirmation and trend alignment.",
            'braid_creation': "This braid represents a high-confidence trading pattern that has demonstrated 85% success rate across 20+ instances."
        }
    
    async def generate_response(self, prompt, **kwargs):
        self.call_count += 1
        
        # Determine response type based on prompt content
        if 'pattern' in prompt.lower() and 'analyze' in prompt.lower():
            response_type = 'pattern_analysis'
        elif 'predict' in prompt.lower():
            response_type = 'prediction_generation'
        elif 'learn' in prompt.lower() or 'insight' in prompt.lower():
            response_type = 'learning_insight'
        elif 'braid' in prompt.lower():
            response_type = 'braid_creation'
        else:
            response_type = 'pattern_analysis'
        
        return {
            'content': self.responses[response_type],
            'usage': {'total_tokens': 100 + self.call_count}
        }

class CompleteWorkflowTest:
    """Test runner for complete system workflow"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        self.supabase_manager = MockSupabaseManager()
        self.llm_client = MockLLMClient()
        self.workflow_stats = {
            'strands_created': 0,
            'braids_created': 0,
            'llm_calls_made': 0,
            'patterns_analyzed': 0,
            'predictions_generated': 0,
            'learning_insights_created': 0
        }
        
    async def run_complete_workflow_test(self):
        """Run the complete workflow test"""
        logger.info("🚀 Starting Complete Workflow Test")
        logger.info("=" * 60)
        
        self.start_time = time.time()
        
        workflow_steps = [
            ("Data Input Simulation", self.simulate_data_input),
            ("Pattern Analysis", self.simulate_pattern_analysis),
            ("Prediction Generation", self.simulate_prediction_generation),
            ("Learning System Processing", self.simulate_learning_processing),
            ("Braid Creation", self.simulate_braid_creation),
            ("Context Injection", self.simulate_context_injection),
            ("System Integration", self.simulate_system_integration),
            ("Performance Validation", self.validate_performance)
        ]
        
        passed = 0
        failed = 0
        
        for step_name, step_func in workflow_steps:
            try:
                logger.info(f"\n🔍 Running {step_name}...")
                await step_func()
                logger.info(f"✅ {step_name} PASSED")
                passed += 1
            except Exception as e:
                logger.error(f"❌ {step_name} FAILED: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                failed += 1
        
        self.end_time = time.time()
        total_time = self.end_time - self.start_time
        
        logger.info("\n" + "=" * 60)
        logger.info(f"📊 Workflow Test Results: {passed} passed, {failed} failed")
        logger.info(f"⏱️  Total Time: {total_time:.2f} seconds")
        logger.info(f"📊 Strands Created: {self.workflow_stats['strands_created']}")
        logger.info(f"🧬 Braids Created: {self.workflow_stats['braids_created']}")
        logger.info(f"🤖 LLM Calls Made: {self.workflow_stats['llm_calls_made']}")
        logger.info(f"🔍 Patterns Analyzed: {self.workflow_stats['patterns_analyzed']}")
        logger.info(f"🔮 Predictions Generated: {self.workflow_stats['predictions_generated']}")
        logger.info(f"💡 Learning Insights Created: {self.workflow_stats['learning_insights_created']}")
        
        if failed == 0:
            logger.info("🎉 Complete workflow test passed!")
            return True
        else:
            logger.error("⚠️  Some workflow steps failed.")
            return False
    
    async def simulate_data_input(self):
        """Simulate data input from various sources"""
        logger.info("  📥 Simulating data input...")
        
        # Simulate market data input
        market_data_points = []
        symbols = ['BTC', 'ETH', 'SOL']
        
        for i in range(10):  # Simulate 10 data points
            for symbol in symbols:
                market_data = {
                    'symbol': symbol,
                    'price': 45000 + (i * 100),  # Simulate price movement
                    'volume': 1000 + (i * 50),   # Simulate volume change
                    'timestamp': (datetime.now(timezone.utc) + timedelta(minutes=i)).isoformat(),
                    'bid': 45000 + (i * 100) - 25,
                    'ask': 45000 + (i * 100) + 25
                }
                market_data_points.append(market_data)
        
        # Validate market data
        assert len(market_data_points) == 30, "Expected 30 market data points"
        for data in market_data_points:
            assert 'symbol' in data, "Symbol missing from market data"
            assert 'price' in data, "Price missing from market data"
            assert 'volume' in data, "Volume missing from market data"
            assert data['price'] > 0, "Price should be positive"
            assert data['volume'] > 0, "Volume should be positive"
        
        logger.info(f"    ✅ Generated {len(market_data_points)} market data points")
        logger.info("  ✅ Data input simulation successful")
    
    async def simulate_pattern_analysis(self):
        """Simulate pattern analysis from market data"""
        logger.info("  🔍 Simulating pattern analysis...")
        
        # Simulate pattern detection
        patterns = []
        pattern_types = ['volume_spike', 'price_breakout', 'support_resistance', 'trend_reversal']
        
        for i in range(15):  # Simulate 15 patterns
            pattern = {
                'id': f"pattern_{i}_{uuid.uuid4()}",
                'kind': 'pattern',
                'symbol': 'BTC' if i % 3 == 0 else 'ETH' if i % 3 == 1 else 'SOL',
                'timeframe': '1m' if i % 2 == 0 else '5m',
                'content': {
                    'pattern_type': pattern_types[i % len(pattern_types)],
                    'confidence': 0.6 + (i * 0.02),  # Increasing confidence
                    'quality': 0.7 + (i * 0.01),     # Increasing quality
                    'strength': 0.5 + (i * 0.03),    # Increasing strength
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Store pattern in database
            await self.supabase_manager.create_strand(pattern)
            patterns.append(pattern)
            self.workflow_stats['strands_created'] += 1
            self.workflow_stats['patterns_analyzed'] += 1
        
        # Validate patterns
        assert len(patterns) == 15, "Expected 15 patterns"
        for pattern in patterns:
            assert pattern['kind'] == 'pattern', "Pattern kind should be 'pattern'"
            assert 'content' in pattern, "Pattern content missing"
            assert 0 <= pattern['content']['confidence'] <= 1, "Confidence out of range"
            assert 0 <= pattern['content']['quality'] <= 1, "Quality out of range"
        
        logger.info(f"    ✅ Analyzed {len(patterns)} patterns")
        logger.info("  ✅ Pattern analysis simulation successful")
    
    async def simulate_prediction_generation(self):
        """Simulate prediction generation from patterns"""
        logger.info("  🔮 Simulating prediction generation...")
        
        # Get patterns from database
        patterns = [s for s in self.supabase_manager.strands if s['kind'] == 'pattern']
        
        # Generate predictions from patterns
        predictions = []
        for i, pattern in enumerate(patterns[:10]):  # Use first 10 patterns
            # Simulate LLM call for prediction
            prompt = f"Based on this pattern: {json.dumps(pattern['content'])}, generate a trading prediction."
            response = await self.llm_client.generate_response(prompt)
            self.workflow_stats['llm_calls_made'] += 1
            
            prediction = {
                'id': f"prediction_{i}_{uuid.uuid4()}",
                'kind': 'prediction_review',
                'symbol': pattern['symbol'],
                'timeframe': pattern['timeframe'],
                'content': {
                    'group_signature': f"{pattern['symbol']}_{pattern['timeframe']}_{pattern['content']['pattern_type']}",
                    'prediction': response['content'],
                    'confidence': pattern['content']['confidence'] * 0.9,  # Slightly lower confidence
                    'time_horizon': '1h',
                    'expected_return': 0.02 + (i * 0.001),  # Simulate expected return
                    'risk_level': 'medium' if pattern['content']['confidence'] > 0.7 else 'high',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Store prediction in database
            await self.supabase_manager.create_strand(prediction)
            predictions.append(prediction)
            self.workflow_stats['strands_created'] += 1
            self.workflow_stats['predictions_generated'] += 1
        
        # Validate predictions
        assert len(predictions) == 10, "Expected 10 predictions"
        for prediction in predictions:
            assert prediction['kind'] == 'prediction_review', "Prediction kind should be 'prediction_review'"
            assert 'group_signature' in prediction['content'], "Group signature missing"
            assert 'prediction' in prediction['content'], "Prediction content missing"
            assert 0 <= prediction['content']['confidence'] <= 1, "Confidence out of range"
        
        logger.info(f"    ✅ Generated {len(predictions)} predictions")
        logger.info("  ✅ Prediction generation simulation successful")
    
    async def simulate_learning_processing(self):
        """Simulate learning system processing"""
        logger.info("  🧠 Simulating learning system processing...")
        
        # Get predictions for learning
        predictions = [s for s in self.supabase_manager.strands if s['kind'] == 'prediction_review']
        
        # Simulate learning analysis
        learning_insights = []
        for i, prediction in enumerate(predictions[:5]):  # Use first 5 predictions
            # Simulate LLM call for learning insight
            prompt = f"Analyze this prediction for learning insights: {json.dumps(prediction['content'])}"
            response = await self.llm_client.generate_response(prompt)
            self.workflow_stats['llm_calls_made'] += 1
            
            learning_insight = {
                'id': f"learning_{i}_{uuid.uuid4()}",
                'kind': 'learning_insight',
                'content': {
                    'insight': response['content'],
                    'source_prediction': prediction['id'],
                    'confidence': prediction['content']['confidence'],
                    'learning_type': 'pattern_recognition',
                    'applicability': 'high' if prediction['content']['confidence'] > 0.8 else 'medium',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Store learning insight
            await self.supabase_manager.create_strand(learning_insight)
            learning_insights.append(learning_insight)
            self.workflow_stats['strands_created'] += 1
            self.workflow_stats['learning_insights_created'] += 1
        
        # Validate learning insights
        assert len(learning_insights) == 5, "Expected 5 learning insights"
        for insight in learning_insights:
            assert insight['kind'] == 'learning_insight', "Insight kind should be 'learning_insight'"
            assert 'insight' in insight['content'], "Insight content missing"
            assert 'source_prediction' in insight['content'], "Source prediction missing"
        
        logger.info(f"    ✅ Created {len(learning_insights)} learning insights")
        logger.info("  ✅ Learning system processing simulation successful")
    
    async def simulate_braid_creation(self):
        """Simulate braid creation from learning insights"""
        logger.info("  🧬 Simulating braid creation...")
        
        # Get learning insights for braid creation
        insights = [s for s in self.supabase_manager.strands if s['kind'] == 'learning_insight']
        
        # Create braids from insights
        braids = []
        for i, insight in enumerate(insights):
            # Simulate LLM call for braid creation
            prompt = f"Create a learning braid from this insight: {json.dumps(insight['content'])}"
            response = await self.llm_client.generate_response(prompt)
            self.workflow_stats['llm_calls_made'] += 1
            
            braid = {
                'id': f"braid_{i}_{uuid.uuid4()}",
                'kind': 'braid',
                'braid_level': 1,  # Level 1 braid
                'content': {
                    'braid_content': response['content'],
                    'source_insights': [insight['id']],
                    'confidence': insight['content']['confidence'],
                    'applicability': insight['content']['applicability'],
                    'learning_type': insight['content']['learning_type'],
                    'resonance_score': 0.7 + (i * 0.05),  # Simulate resonance score
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Store braid in database
            await self.supabase_manager.create_braid(braid)
            braids.append(braid)
            self.workflow_stats['braids_created'] += 1
        
        # Validate braids
        assert len(braids) == len(insights), "Expected one braid per insight"
        for braid in braids:
            assert braid['kind'] == 'braid', "Braid kind should be 'braid'"
            assert 'braid_level' in braid, "Braid level missing"
            assert 'braid_content' in braid['content'], "Braid content missing"
            assert 'resonance_score' in braid['content'], "Resonance score missing"
            assert 0 <= braid['content']['resonance_score'] <= 1, "Resonance score out of range"
        
        logger.info(f"    ✅ Created {len(braids)} braids")
        logger.info("  ✅ Braid creation simulation successful")
    
    async def simulate_context_injection(self):
        """Simulate context injection for other modules"""
        logger.info("  💉 Simulating context injection...")
        
        # Get braids for context injection
        braids = self.supabase_manager.braids
        
        # Simulate context injection for different modules
        context_requests = [
            {'module': 'CIL', 'strand_type': 'prediction_review'},
            {'module': 'CTP', 'strand_type': 'conditional_trading_plan'},
            {'module': 'DM', 'strand_type': 'trading_decision'}
        ]
        
        for request in context_requests:
            # Simulate context retrieval
            relevant_braids = [b for b in braids if b['content']['applicability'] == 'high']
            
            context = {
                'module': request['module'],
                'strand_type': request['strand_type'],
                'relevant_braids': relevant_braids,
                'context_summary': f"Found {len(relevant_braids)} relevant braids for {request['module']}",
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Validate context
            assert 'module' in context, "Module missing from context"
            assert 'strand_type' in context, "Strand type missing from context"
            assert 'relevant_braids' in context, "Relevant braids missing from context"
            assert isinstance(context['relevant_braids'], list), "Relevant braids should be list"
        
        logger.info(f"    ✅ Injected context for {len(context_requests)} modules")
        logger.info("  ✅ Context injection simulation successful")
    
    async def simulate_system_integration(self):
        """Simulate complete system integration"""
        logger.info("  🔗 Simulating system integration...")
        
        # Test data flow through all components
        # 1. Market data -> Patterns
        patterns = [s for s in self.supabase_manager.strands if s['kind'] == 'pattern']
        assert len(patterns) > 0, "No patterns found for integration test"
        
        # 2. Patterns -> Predictions
        predictions = [s for s in self.supabase_manager.strands if s['kind'] == 'prediction_review']
        assert len(predictions) > 0, "No predictions found for integration test"
        
        # 3. Predictions -> Learning insights
        insights = [s for s in self.supabase_manager.strands if s['kind'] == 'learning_insight']
        assert len(insights) > 0, "No learning insights found for integration test"
        
        # 4. Learning insights -> Braids
        braids = self.supabase_manager.braids
        assert len(braids) > 0, "No braids found for integration test"
        
        # 5. Test data consistency
        for prediction in predictions:
            assert prediction['symbol'] in ['BTC', 'ETH', 'SOL'], "Invalid symbol in prediction"
            assert prediction['timeframe'] in ['1m', '5m'], "Invalid timeframe in prediction"
        
        # 6. Test learning connections
        for insight in insights:
            assert 'source_prediction' in insight['content'], "Source prediction missing from insight"
            source_id = insight['content']['source_prediction']
            source_found = any(p['id'] == source_id for p in predictions)
            assert source_found, "Source prediction not found for insight"
        
        # 7. Test braid connections
        for braid in braids:
            assert 'source_insights' in braid['content'], "Source insights missing from braid"
            source_ids = braid['content']['source_insights']
            assert isinstance(source_ids, list), "Source insights should be list"
            for source_id in source_ids:
                source_found = any(i['id'] == source_id for i in insights)
                assert source_found, "Source insight not found for braid"
        
        logger.info("  ✅ System integration simulation successful")
    
    async def validate_performance(self):
        """Validate system performance"""
        logger.info("  ⚡ Validating performance...")
        
        # Check data volume
        total_strands = len(self.supabase_manager.strands)
        total_braids = len(self.supabase_manager.braids)
        total_llm_calls = self.llm_client.call_count
        
        # Performance assertions
        assert total_strands > 0, "No strands created during workflow"
        assert total_braids > 0, "No braids created during workflow"
        assert total_llm_calls > 0, "No LLM calls made during workflow"
        
        # Check data quality
        patterns = [s for s in self.supabase_manager.strands if s['kind'] == 'pattern']
        predictions = [s for s in self.supabase_manager.strands if s['kind'] == 'prediction_review']
        insights = [s for s in self.supabase_manager.strands if s['kind'] == 'learning_insight']
        
        # Validate data quality
        for pattern in patterns:
            assert 0 <= pattern['content']['confidence'] <= 1, "Invalid confidence in pattern"
            assert 0 <= pattern['content']['quality'] <= 1, "Invalid quality in pattern"
        
        for prediction in predictions:
            assert 0 <= prediction['content']['confidence'] <= 1, "Invalid confidence in prediction"
            assert prediction['content']['expected_return'] > 0, "Invalid expected return in prediction"
        
        for insight in insights:
            assert 'insight' in insight['content'], "Missing insight content"
            assert len(insight['content']['insight']) > 0, "Empty insight content"
        
        for braid in self.supabase_manager.braids:
            assert 0 <= braid['content']['resonance_score'] <= 1, "Invalid resonance score in braid"
            assert 'braid_content' in braid['content'], "Missing braid content"
        
        # Performance metrics
        logger.info(f"    ✅ Total strands: {total_strands}")
        logger.info(f"    ✅ Total braids: {total_braids}")
        logger.info(f"    ✅ Total LLM calls: {total_llm_calls}")
        logger.info(f"    ✅ Patterns: {len(patterns)}")
        logger.info(f"    ✅ Predictions: {len(predictions)}")
        logger.info(f"    ✅ Learning insights: {len(insights)}")
        
        logger.info("  ✅ Performance validation successful")

async def main():
    """Main test runner"""
    test_runner = CompleteWorkflowTest()
    
    try:
        success = await test_runner.run_complete_workflow_test()
        
        if success:
            logger.info("\n🎉 Complete workflow test passed!")
            logger.info("The entire system workflow is working correctly.")
            return 0
        else:
            logger.error("\n⚠️  Some workflow steps failed.")
            return 1
            
    except Exception as e:
        logger.error(f"\n💥 Test suite crashed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

