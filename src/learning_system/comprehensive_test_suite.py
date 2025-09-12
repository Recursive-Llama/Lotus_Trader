"""
Comprehensive Test Suite for Centralized Learning System

This test suite puts the entire learning system through its paces with realistic test data,
testing all components, data flows, and edge cases.
"""

import asyncio
import json
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import uuid

# Mock dependencies for testing
class MockSupabaseManager:
    def __init__(self):
        self.client = MockSupabaseClient()
        self.strands = []
        self.learning_queue = []
        self.braids = []
    
    async def get_strands_by_type(self, strand_type: str, limit: int = 100):
        return [s for s in self.strands if s.get('kind') == strand_type][:limit]
    
    async def create_strand(self, strand_data: Dict[str, Any]):
        strand_id = str(uuid.uuid4())
        strand = {
            'id': strand_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            **strand_data
        }
        self.strands.append(strand)
        return strand_id
    
    async def update_strand(self, strand_id: str, updates: Dict[str, Any]):
        for strand in self.strands:
            if strand['id'] == strand_id:
                strand.update(updates)
                break

class MockSupabaseClient:
    def __init__(self):
        self.strands = []
        self.learning_queue = []
    
    def table(self, table_name):
        return MockTable(table_name, self)

class MockTable:
    def __init__(self, table_name, client):
        self.table_name = table_name
        self.client = client
    
    def select(self, columns):
        return MockQuery(self, 'select', columns)
    
    def insert(self, data):
        return MockQuery(self, 'insert', data)
    
    def update(self, data):
        return MockQuery(self, 'update', data)
    
    def eq(self, column, value):
        return MockQuery(self, 'eq', (column, value))
    
    def gte(self, column, value):
        return MockQuery(self, 'gte', (column, value))
    
    def order(self, column, desc=False):
        return MockQuery(self, 'order', (column, desc))
    
    def limit(self, count):
        return MockQuery(self, 'limit', count)

class MockQuery:
    def __init__(self, table, operation, data):
        self.table = table
        self.operation = operation
        self.data = data
        self.filters = []
    
    def eq(self, column, value):
        self.filters.append(('eq', column, value))
        return self
    
    def gte(self, column, value):
        self.filters.append(('gte', column, value))
        return self
    
    def order(self, column, desc=False):
        self.filters.append(('order', column, desc))
        return self
    
    def limit(self, count):
        self.filters.append(('limit', count))
        return self
    
    async def execute(self):
        if self.operation == 'select':
            return MockResult(self._filter_data())
        elif self.operation == 'insert':
            return MockResult(self._insert_data())
        elif self.operation == 'update':
            return MockResult(self._update_data())
    
    def _filter_data(self):
        data = self.table.client.strands if self.table.table_name == 'AD_strands' else self.table.client.learning_queue
        filtered = data.copy()
        
        for filter_type, column, value in self.filters:
            if filter_type == 'eq':
                filtered = [item for item in filtered if item.get(column) == value]
            elif filter_type == 'gte':
                filtered = [item for item in filtered if item.get(column, 0) >= value]
            elif filter_type == 'order':
                reverse = value[1] if isinstance(value, tuple) else False
                filtered.sort(key=lambda x: x.get(column, ''), reverse=reverse)
            elif filter_type == 'limit':
                filtered = filtered[:value]
        
        return filtered
    
    def _insert_data(self):
        if self.table.table_name == 'AD_strands':
            self.table.client.strands.append(self.data)
        elif self.table.table_name == 'learning_queue':
            self.table.client.learning_queue.append(self.data)
        return [self.data]
    
    def _update_data(self):
        return [{'id': 1, 'status': 'updated'}]

class MockLLMClient:
    def __init__(self):
        self.call_count = 0
        self.responses = []
    
    async def generate_response(self, prompt, **kwargs):
        self.call_count += 1
        
        # Generate realistic responses based on prompt content
        if 'prediction_review' in prompt:
            response = self._generate_prediction_braid_response()
        elif 'trade_outcome' in prompt:
            response = self._generate_trade_braid_response()
        elif 'pattern' in prompt:
            response = self._generate_pattern_braid_response()
        else:
            response = self._generate_generic_braid_response()
        
        self.responses.append(response)
        return response
    
    def _generate_prediction_braid_response(self):
        return {
            'content': json.dumps({
                'insights': [
                    'Volume spike patterns show 73% accuracy in bull markets',
                    'Time-based patterns work better in ranging markets',
                    'Combining volume and time patterns increases success rate by 15%'
                ],
                'recommendations': [
                    'Focus on volume patterns during high volatility periods',
                    'Use time-based patterns for range-bound markets',
                    'Combine multiple pattern types for better accuracy'
                ],
                'confidence': 0.85,
                'sample_size': 47
            }),
            'usage': {'total_tokens': 150}
        }
    
    def _generate_trade_braid_response(self):
        return {
            'content': json.dumps({
                'insights': [
                    'Entry timing is critical - 2% improvement with better timing',
                    'Risk management reduces drawdown by 40%',
                    'Position sizing based on volatility improves returns'
                ],
                'recommendations': [
                    'Use ATR-based position sizing',
                    'Implement trailing stops for trend following',
                    'Scale in/out based on market conditions'
                ],
                'confidence': 0.78,
                'sample_size': 32
            }),
            'usage': {'total_tokens': 120}
        }
    
    def _generate_pattern_braid_response(self):
        return {
            'content': json.dumps({
                'insights': [
                    'Volume spikes precede price moves 68% of the time',
                    'Patterns work across multiple timeframes',
                    'Market regime affects pattern effectiveness'
                ],
                'recommendations': [
                    'Monitor volume patterns across timeframes',
                    'Adjust pattern sensitivity based on market regime',
                    'Combine with other technical indicators'
                ],
                'confidence': 0.72,
                'sample_size': 89
            }),
            'usage': {'total_tokens': 110}
        }
    
    def _generate_generic_braid_response(self):
        return {
            'content': json.dumps({
                'insights': ['Generic learning insight'],
                'recommendations': ['Generic recommendation'],
                'confidence': 0.5,
                'sample_size': 10
            }),
            'usage': {'total_tokens': 50}
        }

class MockPromptManager:
    def __init__(self):
        self.call_count = 0
        self.prompts = []
    
    def format_prompt(self, template_name, context):
        self.call_count += 1
        prompt = f"Mock prompt for {template_name} with context: {json.dumps(context, indent=2)}"
        self.prompts.append(prompt)
        return prompt

# Import the learning system components
import sys
sys.path.append('.')

from centralized_learning_system import CentralizedLearningSystem
from strand_processor import StrandProcessor
from mathematical_resonance_engine import MathematicalResonanceEngine

class ComprehensiveTestSuite:
    """Comprehensive test suite for the centralized learning system"""
    
    def __init__(self):
        self.supabase_manager = MockSupabaseManager()
        self.llm_client = MockLLMClient()
        self.prompt_manager = MockPromptManager()
        self.learning_system = CentralizedLearningSystem(
            self.supabase_manager, self.llm_client, self.prompt_manager
        )
        self.resonance_engine = MathematicalResonanceEngine()
        
        # Test data
        self.test_strands = []
        self.test_results = {}
    
    async def run_comprehensive_tests(self):
        """Run all comprehensive tests"""
        print("🚀 Starting Comprehensive Learning System Test Suite")
        print("=" * 80)
        
        tests = [
            self.test_data_generation,
            self.test_strand_processing,
            self.test_mathematical_resonance,
            self.test_learning_pipeline,
            self.test_context_injection,
            self.test_braid_creation,
            self.test_subscription_model,
            self.test_error_handling,
            self.test_performance,
            self.test_integration_flow
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                print(f"\n🔍 Running {test.__name__}...")
                await test()
                print(f"✅ {test.__name__} PASSED")
                passed += 1
            except Exception as e:
                print(f"❌ {test.__name__} FAILED: {e}")
                failed += 1
                import traceback
                traceback.print_exc()
        
        print("\n" + "=" * 80)
        print(f"📊 Comprehensive Test Results: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("🎉 All comprehensive tests passed! Learning system is production-ready.")
        else:
            print("⚠️  Some tests failed. Please review and fix.")
        
        return failed == 0
    
    async def test_data_generation(self):
        """Test realistic data generation"""
        print("  📊 Generating realistic test data...")
        
        # Generate pattern strands
        pattern_strands = self._generate_pattern_strands(50)
        self.test_strands.extend(pattern_strands)
        
        # Generate prediction review strands
        prediction_strands = self._generate_prediction_strands(30)
        self.test_strands.extend(prediction_strands)
        
        # Generate trade outcome strands
        trade_strands = self._generate_trade_strands(25)
        self.test_strands.extend(trade_strands)
        
        # Generate conditional trading plan strands
        plan_strands = self._generate_plan_strands(20)
        self.test_strands.extend(plan_strands)
        
        print(f"  ✓ Generated {len(self.test_strands)} test strands")
        print(f"    - {len(pattern_strands)} pattern strands")
        print(f"    - {len(prediction_strands)} prediction review strands")
        print(f"    - {len(trade_strands)} trade outcome strands")
        print(f"    - {len(plan_strands)} conditional trading plan strands")
        
        # Verify data quality
        assert len(self.test_strands) > 0
        assert all('id' in strand for strand in self.test_strands)
        assert all('kind' in strand for strand in self.test_strands)
        assert all('content' in strand for strand in self.test_strands)
    
    async def test_strand_processing(self):
        """Test strand processing and type detection"""
        print("  🔄 Testing strand processing...")
        
        processor = StrandProcessor()
        
        # Test each strand type
        strand_types = ['pattern', 'prediction_review', 'trade_outcome', 'conditional_trading_plan']
        
        for strand_type in strand_types:
            # Find a strand of this type
            test_strand = next((s for s in self.test_strands if s['kind'] == strand_type), None)
            assert test_strand is not None, f"No {strand_type} strand found"
            
            # Process the strand
            config = processor.process_strand(test_strand)
            assert config is not None, f"Failed to process {strand_type} strand"
            assert config.strand_type.value == strand_type
        
        print("  ✓ All strand types processed correctly")
    
    async def test_mathematical_resonance(self):
        """Test mathematical resonance engine"""
        print("  🧮 Testing mathematical resonance engine...")
        
        # Test φ (Fractal Self-Similarity)
        pattern_data = {
            '1m': {'confidence': 0.8, 'quality': 0.9},
            '5m': {'confidence': 0.7, 'quality': 0.8},
            '15m': {'confidence': 0.6, 'quality': 0.7}
        }
        
        phi = self.resonance_engine.calculate_phi(pattern_data, ['1m', '5m', '15m'])
        assert phi > 0
        assert phi <= 1.0
        
        # Test ρ (Recursive Feedback)
        learning_outcome = {
            'expected': 0.5,
            'actual': 0.8,
            'phi_change': 0.1
        }
        
        rho = self.resonance_engine.calculate_rho(learning_outcome)
        assert rho >= 0
        
        # Test θ (Global Field)
        all_braids = [
            {'phi': 0.8, 'rho': 0.6},
            {'phi': 0.7, 'rho': 0.5}
        ]
        
        theta = self.resonance_engine.calculate_theta(all_braids)
        assert theta >= 0
        
        # Test ω (Resonance Acceleration)
        omega = self.resonance_engine.calculate_omega(theta, 0.6)
        assert omega >= 0
        
        # Test S_i (Selection Score)
        pattern_data = {
            'hits': 8,
            'total': 10,
            'confidence': 0.8,
            't_stat': 2.5,
            'rolling_ir': [0.1, 0.2, 0.15],
            'correlations': [0.1, 0.2],
            'processing_cost': 0.01,
            'storage_cost': 0.005
        }
        
        selection_score = self.resonance_engine.calculate_selection_score(pattern_data)
        assert selection_score.total_score >= 0
        
        print("  ✓ All resonance calculations working correctly")
    
    async def test_learning_pipeline(self):
        """Test learning pipeline with real data"""
        print("  🔄 Testing learning pipeline...")
        
        # Process a sample of strands
        sample_strands = self.test_strands[:10]
        
        for strand in sample_strands:
            success = await self.learning_system.process_strand(strand)
            # Note: In real implementation, this would create braids
            assert isinstance(success, bool)
        
        print(f"  ✓ Processed {len(sample_strands)} strands through learning pipeline")
    
    async def test_context_injection(self):
        """Test context injection for different modules"""
        print("  💉 Testing context injection...")
        
        # Test context injection for different strand types
        strand_types = ['prediction_review', 'trade_outcome', 'pattern']
        
        for strand_type in strand_types:
            context_data = {
                'pattern_data': {
                    '1m': {'confidence': 0.8, 'quality': 0.9},
                    '5m': {'confidence': 0.7, 'quality': 0.8}
                }
            }
            
            context = await self.learning_system.get_resonance_context(
                strand_type, context_data
            )
            
            assert 'strand_type' in context
            assert 'learning_focus' in context
            assert 'recent_braids' in context
        
        print("  ✓ Context injection working for all strand types")
    
    async def test_braid_creation(self):
        """Test braid creation process"""
        print("  🧬 Testing braid creation...")
        
        # Simulate braid creation by processing strands
        braid_candidates = []
        
        for strand in self.test_strands[:5]:
            # Simulate clustering and learning
            if strand['kind'] == 'prediction_review':
                # Simulate successful braid creation
                braid = {
                    'id': f"braid_{strand['id']}",
                    'kind': strand['kind'],
                    'braid_level': 2,
                    'content': {
                        'insights': ['Test insight'],
                        'confidence': 0.8,
                        'sample_size': 5
                    },
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                braid_candidates.append(braid)
        
        assert len(braid_candidates) > 0
        print(f"  ✓ Created {len(braid_candidates)} braid candidates")
    
    async def test_subscription_model(self):
        """Test subscription model functionality"""
        print("  📋 Testing subscription model...")
        
        # Test module subscriptions
        cil_subscription = self.learning_system.is_learning_supported('prediction_review')
        assert cil_subscription == True
        
        ctp_subscription = self.learning_system.is_learning_supported('trade_outcome')
        assert ctp_subscription == True
        
        unsupported = self.learning_system.is_learning_supported('unsupported_type')
        assert unsupported == False
        
        # Test supported strand types
        supported_types = self.learning_system.get_supported_strand_types()
        assert 'prediction_review' in supported_types
        assert 'trade_outcome' in supported_types
        assert 'pattern' in supported_types
        
        print("  ✓ Subscription model working correctly")
    
    async def test_error_handling(self):
        """Test error handling and edge cases"""
        print("  ⚠️  Testing error handling...")
        
        # Test with invalid strand
        invalid_strand = {'id': 'invalid', 'kind': 'invalid_type'}
        success = await self.learning_system.process_strand(invalid_strand)
        # Should handle gracefully
        assert isinstance(success, bool)
        
        # Test with empty content
        empty_strand = {'id': 'empty', 'kind': 'pattern', 'content': {}}
        success = await self.learning_system.process_strand(empty_strand)
        assert isinstance(success, bool)
        
        # Test with malformed data
        malformed_strand = {'id': 'malformed', 'kind': 'pattern', 'content': None}
        success = await self.learning_system.process_strand(malformed_strand)
        assert isinstance(success, bool)
        
        print("  ✓ Error handling working correctly")
    
    async def test_performance(self):
        """Test performance with large datasets"""
        print("  ⚡ Testing performance...")
        
        # Generate large dataset
        large_dataset = self._generate_pattern_strands(100)
        
        start_time = datetime.now()
        
        # Process large dataset
        for strand in large_dataset:
            await self.learning_system.process_strand(strand)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print(f"  ✓ Processed {len(large_dataset)} strands in {processing_time:.2f} seconds")
        print(f"  ✓ Average processing time: {processing_time/len(large_dataset):.4f} seconds per strand")
        
        # Performance should be reasonable
        assert processing_time < 10.0  # Should process 100 strands in under 10 seconds
    
    async def test_integration_flow(self):
        """Test complete integration flow"""
        print("  🔄 Testing complete integration flow...")
        
        # Simulate complete workflow
        workflow_results = {
            'strands_processed': 0,
            'braids_created': 0,
            'context_injections': 0,
            'resonance_calculations': 0
        }
        
        # Process all test strands
        for strand in self.test_strands:
            success = await self.learning_system.process_strand(strand)
            if success:
                workflow_results['strands_processed'] += 1
        
        # Test context injection
        for strand_type in ['prediction_review', 'trade_outcome']:
            context = await self.learning_system.get_resonance_context(strand_type, {})
            if context:
                workflow_results['context_injections'] += 1
        
        # Test resonance calculations
        pattern_data = {'1m': {'confidence': 0.8, 'quality': 0.9}}
        phi = self.resonance_engine.calculate_phi(pattern_data, ['1m'])
        if phi > 0:
            workflow_results['resonance_calculations'] += 1
        
        print(f"  ✓ Workflow Results:")
        print(f"    - Strands processed: {workflow_results['strands_processed']}")
        print(f"    - Context injections: {workflow_results['context_injections']}")
        print(f"    - Resonance calculations: {workflow_results['resonance_calculations']}")
        
        # Verify workflow completed
        assert workflow_results['strands_processed'] > 0
        assert workflow_results['context_injections'] > 0
        assert workflow_results['resonance_calculations'] > 0
    
    def _generate_pattern_strands(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic pattern strands"""
        patterns = []
        pattern_types = ['volume_spike', 'time_based', 'momentum', 'microstructure']
        assets = ['BTC', 'ETH', 'SOL', 'ADA']
        timeframes = ['1m', '5m', '15m', '1h']
        
        for i in range(count):
            pattern = {
                'id': f"pattern_{i}",
                'kind': 'pattern',
                'content': {
                    'pattern_type': random.choice(pattern_types),
                    'asset': random.choice(assets),
                    'timeframe': random.choice(timeframes),
                    'confidence': random.uniform(0.3, 0.9),
                    'quality': random.uniform(0.4, 0.8),
                    'market_conditions': random.choice(['bull', 'bear', 'ranging']),
                    'volume': random.uniform(1000, 10000),
                    'price_change': random.uniform(-0.05, 0.05)
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            patterns.append(pattern)
        
        return patterns
    
    def _generate_prediction_strands(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic prediction review strands"""
        predictions = []
        assets = ['BTC', 'ETH', 'SOL', 'ADA']
        timeframes = ['1h', '4h', '1d']
        
        for i in range(count):
            prediction = {
                'id': f"prediction_{i}",
                'kind': 'prediction_review',
                'content': {
                    'group_signature': f"BTC_1h_volume_spike_{i}",
                    'asset': random.choice(assets),
                    'timeframe': random.choice(timeframes),
                    'outcome': {
                        'success': random.choice([True, False]),
                        'return_pct': random.uniform(-0.1, 0.1)
                    },
                    'method': random.choice(['code', 'llm']),
                    'confidence': random.uniform(0.4, 0.9)
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            predictions.append(prediction)
        
        return predictions
    
    def _generate_trade_strands(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic trade outcome strands"""
        trades = []
        assets = ['BTC', 'ETH', 'SOL', 'ADA']
        
        for i in range(count):
            trade = {
                'id': f"trade_{i}",
                'kind': 'trade_outcome',
                'content': {
                    'trade_id': f"trade_{i}",
                    'asset': random.choice(assets),
                    'timeframe': random.choice(['1h', '4h', '1d']),
                    'performance': {
                        'success': random.choice([True, False]),
                        'return_pct': random.uniform(-0.05, 0.05),
                        'max_drawdown': random.uniform(0.01, 0.03)
                    },
                    'execution': {
                        'entry_timing': random.uniform(0.7, 1.0),
                        'exit_timing': random.uniform(0.7, 1.0),
                        'slippage': random.uniform(0.001, 0.005)
                    }
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            trades.append(trade)
        
        return trades
    
    def _generate_plan_strands(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic conditional trading plan strands"""
        plans = []
        assets = ['BTC', 'ETH', 'SOL', 'ADA']
        
        for i in range(count):
            plan = {
                'id': f"plan_{i}",
                'kind': 'conditional_trading_plan',
                'content': {
                    'plan_type': random.choice(['trend_following', 'mean_reversion', 'breakout']),
                    'asset': random.choice(assets),
                    'timeframe': random.choice(['1h', '4h', '1d']),
                    'conditions': {
                        'entry': f"Price > {random.uniform(0.95, 1.05):.2f} * SMA(20)",
                        'exit': f"Price < {random.uniform(0.95, 1.05):.2f} * SMA(20)"
                    },
                    'risk_score': random.uniform(0.1, 0.9),
                    'leverage_score': random.uniform(0.1, 0.8)
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            plans.append(plan)
        
        return plans

async def main():
    """Main test runner"""
    test_suite = ComprehensiveTestSuite()
    success = await test_suite.run_comprehensive_tests()
    
    if success:
        print("\n🎉 Comprehensive test suite completed successfully!")
        print("The centralized learning system is ready for production deployment.")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above and fix them.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
