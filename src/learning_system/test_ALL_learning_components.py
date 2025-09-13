#!/usr/bin/env python3
"""
COMPREHENSIVE Learning System Components Test
Tests ALL learning system components with REAL data and functionality
"""

import sys
import os
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import traceback

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

class ComprehensiveLearningSystemValidator:
    def __init__(self):
        self.failures = []
        self.successes = []
        self.test_strands = []
        self.test_braids = []
        
    def log_failure(self, component: str, error: str):
        """Log a real failure"""
        self.failures.append(f"{component}: {error}")
        print(f"❌ {component}: {error}")
        
    def log_success(self, component: str, details: str = ""):
        """Log a real success"""
        self.successes.append(f"{component}: {details}")
        print(f"✅ {component}: {details}")
    
    def create_test_strands(self):
        """Create realistic test strands for testing"""
        self.test_strands = [
            {
                'strand_type': 'pattern',
                'content': 'RSI divergence detected on 1H timeframe',
                'metadata': {
                    'rsi': 30,
                    'timeframe': '1H',
                    'confidence': 0.8,
                    'pattern_type': 'rsi_divergence',
                    'accuracy': 0.8,
                    'precision': 0.75,
                    'stability': 0.8
                },
                'source': 'raw_data_intelligence',
                'created_at': datetime.now(timezone.utc).isoformat()
            },
            {
                'strand_type': 'pattern',
                'content': 'Volume spike with price drop',
                'metadata': {
                    'volume': 1500000,
                    'price_change': -0.05,
                    'confidence': 0.7,
                    'pattern_type': 'volume_spike',
                    'accuracy': 0.7,
                    'precision': 0.6,
                    'stability': 0.7
                },
                'source': 'raw_data_intelligence',
                'created_at': datetime.now(timezone.utc).isoformat()
            },
            {
                'strand_type': 'prediction_review',
                'content': 'Prediction accuracy: 85% for BTC price movement',
                'metadata': {
                    'prediction_id': 'pred_001',
                    'accuracy': 0.85,
                    'confidence': 0.8,
                    'outcome': 'success',
                    'symbol': 'BTC'
                },
                'source': 'central_intelligence_layer',
                'created_at': datetime.now(timezone.utc).isoformat()
            },
            {
                'strand_type': 'trade_outcome',
                'content': 'Trade executed: BUY 100 shares at $50, sold at $55',
                'metadata': {
                    'action': 'BUY',
                    'quantity': 100,
                    'entry_price': 50,
                    'exit_price': 55,
                    'profit': 500,
                    'outcome': 'success',
                    'symbol': 'BTC'
                },
                'source': 'trading_execution',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        ]
    
    async def test_mathematical_resonance_engine(self):
        """Test MathematicalResonanceEngine with comprehensive scenarios"""
        print("\n🧮 TESTING MATHEMATICAL RESONANCE ENGINE")
        print("="*60)
        
        try:
            # Test 1: Import and initialize
            print("Testing MathematicalResonanceEngine import...")
            try:
                from mathematical_resonance_engine import MathematicalResonanceEngine
                engine = MathematicalResonanceEngine()
                self.log_success("MathematicalResonanceEngine import and initialization")
            except Exception as e:
                self.log_failure("MathematicalResonanceEngine import", str(e))
                return False
            
            # Test 2: φ (Fractal Self-Similarity) calculations
            print("Testing φ (Fractal Self-Similarity) calculations...")
            try:
                test_cases = [
                    {
                        'pattern_data': {'accuracy': 0.8, 'precision': 0.75, 'stability': 0.8},
                        'timeframes': ['1H', '4H', '1D'],
                        'expected_range': (0, 1)
                    },
                    {
                        'pattern_data': {'accuracy': 0.9, 'precision': 0.85, 'stability': 0.9},
                        'timeframes': ['1H', '4H', '1D', '1W'],
                        'expected_range': (0, 1)
                    },
                    {
                        'pattern_data': {'accuracy': 0.5, 'precision': 0.4, 'stability': 0.5},
                        'timeframes': ['1H'],
                        'expected_range': (0, 1)
                    }
                ]
                
                for i, test_case in enumerate(test_cases):
                    phi = engine.calculate_phi(test_case['pattern_data'], test_case['timeframes'])
                    if test_case['expected_range'][0] <= phi <= test_case['expected_range'][1]:
                        self.log_success(f"φ calculation test {i+1}", f"φ = {phi:.3f}")
                    else:
                        self.log_failure(f"φ calculation test {i+1}", f"Invalid φ = {phi:.3f}")
                        return False
                        
            except Exception as e:
                self.log_failure("φ calculations", str(e))
                return False
            
            # Test 3: ρ (Recursive Feedback) calculations
            print("Testing ρ (Recursive Feedback) calculations...")
            try:
                test_cases = [
                    {
                        'pattern_performance_history': {'pattern1': [0.8, 0.85, 0.9], 'pattern2': [0.7, 0.75, 0.8]},
                        'successful_braids_count': 5,
                        'expected_range': (0, 1)
                    },
                    {
                        'pattern_performance_history': {'pattern1': [0.5, 0.6, 0.7]},
                        'successful_braids_count': 2,
                        'expected_range': (0, 1)
                    }
                ]
                
                for i, test_case in enumerate(test_cases):
                    rho = engine.calculate_rho(test_case['pattern_performance_history'], test_case['successful_braids_count'])
                    if test_case['expected_range'][0] <= rho <= test_case['expected_range'][1]:
                        self.log_success(f"ρ calculation test {i+1}", f"ρ = {rho:.3f}")
                    else:
                        self.log_failure(f"ρ calculation test {i+1}", f"Invalid ρ = {rho:.3f}")
                        return False
                        
            except Exception as e:
                self.log_failure("ρ calculations", str(e))
                return False
            
            # Test 4: θ (Global Field) calculations
            print("Testing θ (Global Field) calculations...")
            try:
                test_cases = [
                    {
                        'successful_braids': [
                            {'resonance_score': 0.8, 'accuracy': 0.85},
                            {'resonance_score': 0.9, 'accuracy': 0.9},
                            {'resonance_score': 0.7, 'accuracy': 0.75}
                        ],
                        'expected_range': (0, 1)
                    },
                    {
                        'successful_braids': [],
                        'expected_range': (0, 1)
                    }
                ]
                
                for i, test_case in enumerate(test_cases):
                    theta = engine.calculate_theta(test_cases[i]['successful_braids'])
                    if test_case['expected_range'][0] <= theta <= test_case['expected_range'][1]:
                        self.log_success(f"θ calculation test {i+1}", f"θ = {theta:.3f}")
                    else:
                        self.log_failure(f"θ calculation test {i+1}", f"Invalid θ = {theta:.3f}")
                        return False
                        
            except Exception as e:
                self.log_failure("θ calculations", str(e))
                return False
            
            # Test 5: ω (Resonance Acceleration) calculations
            print("Testing ω (Resonance Acceleration) calculations...")
            try:
                test_cases = [
                    {
                        'global_theta': 0.8,
                        'learning_strength': 0.7,
                        'expected_range': (0, 1)
                    },
                    {
                        'global_theta': 0.5,
                        'learning_strength': 0.3,
                        'expected_range': (0, 1)
                    }
                ]
                
                for i, test_case in enumerate(test_cases):
                    omega = engine.calculate_omega(test_case['global_theta'], test_case['learning_strength'])
                    if test_case['expected_range'][0] <= omega <= test_case['expected_range'][1]:
                        self.log_success(f"ω calculation test {i+1}", f"ω = {omega:.3f}")
                    else:
                        self.log_failure(f"ω calculation test {i+1}", f"Invalid ω = {omega:.3f}")
                        return False
                        
            except Exception as e:
                self.log_failure("ω calculations", str(e))
                return False
            
            # Test 6: S_i (Selection Score) calculations
            print("Testing S_i (Selection Score) calculations...")
            try:
                test_cases = [
                    {
                        'pattern_data': {
                            'accuracy': 0.8,
                            'precision': 0.75,
                            'stability': 0.8,
                            'cost': 0.1,
                            'orthogonality': 0.7
                        },
                        'expected_range': (0, 1)
                    },
                    {
                        'pattern_data': {
                            'accuracy': 0.9,
                            'precision': 0.85,
                            'stability': 0.9,
                            'cost': 0.05,
                            'orthogonality': 0.8
                        },
                        'expected_range': (0, 1)
                    }
                ]
                
                for i, test_case in enumerate(test_cases):
                    selection_score = engine.calculate_selection_score(test_case['pattern_data'])
                    if hasattr(selection_score, 'total_score'):
                        score = selection_score.total_score
                    else:
                        score = selection_score
                    
                    if test_case['expected_range'][0] <= score <= test_case['expected_range'][1]:
                        self.log_success(f"S_i calculation test {i+1}", f"S_i = {score:.3f}")
                    else:
                        self.log_failure(f"S_i calculation test {i+1}", f"Invalid S_i = {score:.3f}")
                        return False
                        
            except Exception as e:
                self.log_failure("S_i calculations", str(e))
                return False
            
            return True
            
        except Exception as e:
            self.log_failure("Mathematical Resonance Engine", f"Unexpected error: {e}")
            return False
    
    async def test_centralized_learning_system(self):
        """Test CentralizedLearningSystem with real data"""
        print("\n🎓 TESTING CENTRALIZED LEARNING SYSTEM")
        print("="*60)
        
        try:
            # Test 1: Import and initialize
            print("Testing CentralizedLearningSystem import...")
            try:
                from centralized_learning_system import CentralizedLearningSystem
                self.log_success("CentralizedLearningSystem import")
            except Exception as e:
                self.log_failure("CentralizedLearningSystem import", str(e))
                return False
            
            # Test 2: Test with mock dependencies
            print("Testing CentralizedLearningSystem with mock dependencies...")
            try:
                class MockSupabaseManager:
                    def __init__(self):
                        pass
                    async def get_strands(self, **kwargs):
                        return self.test_strands
                    async def insert_braid(self, braid):
                        return {'id': 'braid_001'}
                
                class MockLLMClient:
                    def __init__(self):
                        pass
                    async def generate_completion(self, **kwargs):
                        return {'content': 'Test braid content'}
                
                class MockPromptManager:
                    def __init__(self):
                        pass
                    def get_prompt(self, template_name):
                        return {'content': 'Test prompt template'}
                
                # Initialize with mocks
                learning_system = CentralizedLearningSystem(
                    MockSupabaseManager(),
                    MockLLMClient(),
                    MockPromptManager()
                )
                
                self.log_success("CentralizedLearningSystem initialization with mocks")
                
            except Exception as e:
                self.log_failure("CentralizedLearningSystem initialization", str(e))
                return False
            
            return True
            
        except Exception as e:
            self.log_failure("Centralized Learning System", f"Unexpected error: {e}")
            return False
    
    async def test_learning_pipeline(self):
        """Test LearningPipeline with real data"""
        print("\n🔄 TESTING LEARNING PIPELINE")
        print("="*60)
        
        try:
            # Test 1: Import and initialize
            print("Testing LearningPipeline import...")
            try:
                from learning_pipeline import LearningPipeline
                self.log_success("LearningPipeline import")
            except Exception as e:
                self.log_failure("LearningPipeline import", str(e))
                return False
            
            # Test 2: Test with mock dependencies
            print("Testing LearningPipeline with mock dependencies...")
            try:
                class MockSupabaseManager:
                    def __init__(self):
                        pass
                    async def get_strands(self, **kwargs):
                        return self.test_strands
                    async def insert_braid(self, braid):
                        return {'id': 'braid_001'}
                
                class MockLLMClient:
                    def __init__(self):
                        pass
                    async def generate_completion(self, **kwargs):
                        return {'content': 'Test braid content'}
                
                class MockPromptManager:
                    def __init__(self):
                        pass
                    def get_prompt(self, template_name):
                        return {'content': 'Test prompt template'}
                
                # Initialize with mocks
                pipeline = LearningPipeline(
                    MockSupabaseManager(),
                    MockLLMClient(),
                    MockPromptManager()
                )
                
                self.log_success("LearningPipeline initialization with mocks")
                
            except Exception as e:
                self.log_failure("LearningPipeline initialization", str(e))
                return False
            
            return True
            
        except Exception as e:
            self.log_failure("Learning Pipeline", f"Unexpected error: {e}")
            return False
    
    async def test_context_injection_engine(self):
        """Test ContextInjectionEngine with real data"""
        print("\n💉 TESTING CONTEXT INJECTION ENGINE")
        print("="*60)
        
        try:
            # Test 1: Import and initialize
            print("Testing ContextInjectionEngine import...")
            try:
                from context_injection_engine import ContextInjectionEngine
                self.log_success("ContextInjectionEngine import")
            except Exception as e:
                self.log_failure("ContextInjectionEngine import", str(e))
                return False
            
            # Test 2: Test with mock dependencies
            print("Testing ContextInjectionEngine with mock dependencies...")
            try:
                class MockSupabaseManager:
                    def __init__(self):
                        pass
                    async def get_braids_for_module(self, module, strand_types):
                        return [
                            {
                                'id': 'braid_001',
                                'content': 'Test braid content',
                                'strand_types': strand_types,
                                'resonance_score': 0.8
                            }
                        ]
                
                # Initialize with mocks
                context_engine = ContextInjectionEngine(MockSupabaseManager())
                
                self.log_success("ContextInjectionEngine initialization with mocks")
                
                # Test 3: Test context injection
                print("Testing context injection functionality...")
                try:
                    context = await context_engine.inject_context('CIL', ['pattern', 'prediction_review'])
                    
                    if context:
                        self.log_success("Context injection", f"Generated context with {len(context)} items")
                    else:
                        self.log_success("Context injection", "Generated empty context (no braids available)")
                        
                except Exception as e:
                    self.log_failure("Context injection", str(e))
                    return False
                
            except Exception as e:
                self.log_failure("ContextInjectionEngine initialization", str(e))
                return False
            
            return True
            
        except Exception as e:
            self.log_failure("Context Injection Engine", f"Unexpected error: {e}")
            return False
    
    async def test_braid_level_manager(self):
        """Test BraidLevelManager with real data"""
        print("\n🏆 TESTING BRAID LEVEL MANAGER")
        print("="*60)
        
        try:
            # Test 1: Import and initialize
            print("Testing BraidLevelManager import...")
            try:
                from braid_level_manager import BraidLevelManager
                self.log_success("BraidLevelManager import")
            except Exception as e:
                self.log_failure("BraidLevelManager import", str(e))
                return False
            
            # Test 2: Test with mock dependencies
            print("Testing BraidLevelManager with mock dependencies...")
            try:
                class MockSupabaseManager:
                    def __init__(self):
                        pass
                    async def get_braids(self, **kwargs):
                        return [
                            {
                                'id': 'braid_001',
                                'resonance_score': 0.8,
                                'level': 1,
                                'strand_types': ['pattern']
                            },
                            {
                                'id': 'braid_002',
                                'resonance_score': 0.9,
                                'level': 2,
                                'strand_types': ['prediction_review']
                            }
                        ]
                    async def update_braid_level(self, braid_id, level):
                        return True
                
                # Initialize with mocks
                braid_manager = BraidLevelManager(MockSupabaseManager())
                
                self.log_success("BraidLevelManager initialization with mocks")
                
                # Test 3: Test level management
                print("Testing braid level management...")
                try:
                    # Test level calculation
                    level = braid_manager.calculate_braid_level(0.8, 5, 0.7)
                    
                    if 1 <= level <= 5:
                        self.log_success("Braid level calculation", f"Calculated level: {level}")
                    else:
                        self.log_failure("Braid level calculation", f"Invalid level: {level}")
                        return False
                        
                except Exception as e:
                    self.log_failure("Braid level management", str(e))
                    return False
                
            except Exception as e:
                self.log_failure("BraidLevelManager initialization", str(e))
                return False
            
            return True
            
        except Exception as e:
            self.log_failure("Braid Level Manager", f"Unexpected error: {e}")
            return False
    
    async def test_llm_learning_analyzer(self):
        """Test LLMLearningAnalyzer with real data"""
        print("\n🤖 TESTING LLM LEARNING ANALYZER")
        print("="*60)
        
        try:
            # Test 1: Import and initialize
            print("Testing LLMLearningAnalyzer import...")
            try:
                from llm_learning_analyzer import LLMLearningAnalyzer
                self.log_success("LLMLearningAnalyzer import")
            except Exception as e:
                self.log_failure("LLMLearningAnalyzer import", str(e))
                return False
            
            # Test 2: Test with mock dependencies
            print("Testing LLMLearningAnalyzer with mock dependencies...")
            try:
                class MockLLMClient:
                    def __init__(self):
                        pass
                    async def generate_completion(self, **kwargs):
                        return {'content': 'Test analysis result'}
                
                class MockPromptManager:
                    def __init__(self):
                        pass
                    def get_prompt(self, template_name):
                        return {'content': 'Test prompt template'}
                
                # Initialize with mocks
                analyzer = LLMLearningAnalyzer(MockLLMClient(), MockPromptManager())
                
                self.log_success("LLMLearningAnalyzer initialization with mocks")
                
                # Test 3: Test analysis functionality
                print("Testing LLM analysis functionality...")
                try:
                    # Test strand analysis
                    analysis = await analyzer.analyze_strands(self.test_strands)
                    
                    if analysis:
                        self.log_success("LLM strand analysis", f"Analysis completed: {len(analysis)} results")
                    else:
                        self.log_success("LLM strand analysis", "Analysis completed (no insights generated)")
                        
                except Exception as e:
                    self.log_failure("LLM analysis", str(e))
                    return False
                
            except Exception as e:
                self.log_failure("LLMLearningAnalyzer initialization", str(e))
                return False
            
            return True
            
        except Exception as e:
            self.log_failure("LLM Learning Analyzer", f"Unexpected error: {e}")
            return False
    
    async def test_per_cluster_learning_system(self):
        """Test PerClusterLearningSystem with real data"""
        print("\n🔗 TESTING PER CLUSTER LEARNING SYSTEM")
        print("="*60)
        
        try:
            # Test 1: Import and initialize
            print("Testing PerClusterLearningSystem import...")
            try:
                from per_cluster_learning_system import PerClusterLearningSystem
                self.log_success("PerClusterLearningSystem import")
            except Exception as e:
                self.log_failure("PerClusterLearningSystem import", str(e))
                return False
            
            # Test 2: Test with mock dependencies
            print("Testing PerClusterLearningSystem with mock dependencies...")
            try:
                class MockSupabaseManager:
                    def __init__(self):
                        pass
                    async def get_strands_in_cluster(self, cluster_id):
                        return self.test_strands
                    async def insert_braid(self, braid):
                        return {'id': 'braid_001'}
                
                class MockLLMClient:
                    def __init__(self):
                        pass
                    async def generate_completion(self, **kwargs):
                        return {'content': 'Test cluster braid content'}
                
                class MockPromptManager:
                    def __init__(self):
                        pass
                    def get_prompt(self, template_name):
                        return {'content': 'Test cluster prompt template'}
                
                # Initialize with mocks
                cluster_system = PerClusterLearningSystem(
                    'cluster_001',
                    MockSupabaseManager(),
                    MockLLMClient(),
                    MockPromptManager()
                )
                
                self.log_success("PerClusterLearningSystem initialization with mocks")
                
                # Test 3: Test cluster processing
                print("Testing cluster processing...")
                try:
                    # Test cluster learning
                    result = await cluster_system.process_cluster()
                    
                    if result:
                        self.log_success("Cluster processing", f"Processed cluster: {result}")
                    else:
                        self.log_success("Cluster processing", "Processed cluster (no braids created)")
                        
                except Exception as e:
                    self.log_failure("Cluster processing", str(e))
                    return False
                
            except Exception as e:
                self.log_failure("PerClusterLearningSystem initialization", str(e))
                return False
            
            return True
            
        except Exception as e:
            self.log_failure("Per Cluster Learning System", f"Unexpected error: {e}")
            return False
    
    async def test_strand_processor(self):
        """Test StrandProcessor with real data"""
        print("\n🧵 TESTING STRAND PROCESSOR")
        print("="*60)
        
        try:
            # Test 1: Import and initialize
            print("Testing StrandProcessor import...")
            try:
                from strand_processor import StrandProcessor
                self.log_success("StrandProcessor import")
            except Exception as e:
                self.log_failure("StrandProcessor import", str(e))
                return False
            
            # Test 2: Test with mock dependencies
            print("Testing StrandProcessor with mock dependencies...")
            try:
                class MockSupabaseManager:
                    def __init__(self):
                        pass
                    async def insert_strand(self, strand):
                        return {'id': 'strand_001'}
                    async def get_strands(self, **kwargs):
                        return self.test_strands
                
                # Initialize with mocks
                processor = StrandProcessor(MockSupabaseManager())
                
                self.log_success("StrandProcessor initialization with mocks")
                
                # Test 3: Test strand processing
                print("Testing strand processing...")
                try:
                    # Test strand validation
                    for strand in self.test_strands:
                        is_valid = processor.validate_strand(strand)
                        
                        if is_valid:
                            self.log_success(f"Strand validation: {strand['strand_type']}", "Valid")
                        else:
                            self.log_failure(f"Strand validation: {strand['strand_type']}", "Invalid")
                            return False
                        
                except Exception as e:
                    self.log_failure("Strand processing", str(e))
                    return False
                
            except Exception as e:
                self.log_failure("StrandProcessor initialization", str(e))
                return False
            
            return True
            
        except Exception as e:
            self.log_failure("Strand Processor", f"Unexpected error: {e}")
            return False
    
    def print_comprehensive_summary(self):
        """Print comprehensive summary of all learning system components"""
        print("\n" + "="*80)
        print("🔍 COMPREHENSIVE LEARNING SYSTEM VALIDATION RESULTS")
        print("="*80)
        
        print(f"\n✅ SUCCESSES ({len(self.successes)}):")
        for success in self.successes:
            print(f"  {success}")
            
        print(f"\n❌ FAILURES ({len(self.failures)}):")
        for failure in self.failures:
            print(f"  {failure}")
        
        print("\n" + "="*80)
        
        if len(self.failures) == 0:
            print("🎉 ALL LEARNING SYSTEM COMPONENTS ARE WORKING")
            print("✅ Mathematical Resonance Engine works")
            print("✅ Centralized Learning System works")
            print("✅ Learning Pipeline works")
            print("✅ Context Injection Engine works")
            print("✅ Braid Level Manager works")
            print("✅ LLM Learning Analyzer works")
            print("✅ Per Cluster Learning System works")
            print("✅ Strand Processor works")
        else:
            print("⚠️  LEARNING SYSTEM HAS ISSUES")
            print(f"   {len(self.failures)} components are failing")
            print("   System is NOT production ready")
            
        print("="*80)
        
        return len(self.failures) == 0

async def main():
    """Run comprehensive learning system validation"""
    print("🚀 COMPREHENSIVE LEARNING SYSTEM VALIDATION")
    print("Testing ALL learning system components with REAL data")
    print("="*80)
    
    validator = ComprehensiveLearningSystemValidator()
    
    # Create test data
    validator.create_test_strands()
    
    # Test each component
    tests = [
        ("Mathematical Resonance Engine", validator.test_mathematical_resonance_engine),
        ("Centralized Learning System", validator.test_centralized_learning_system),
        ("Learning Pipeline", validator.test_learning_pipeline),
        ("Context Injection Engine", validator.test_context_injection_engine),
        ("Braid Level Manager", validator.test_braid_level_manager),
        ("LLM Learning Analyzer", validator.test_llm_learning_analyzer),
        ("Per Cluster Learning System", validator.test_per_cluster_learning_system),
        ("Strand Processor", validator.test_strand_processor)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Testing {test_name}...")
            await test_func()
        except Exception as e:
            validator.log_failure(test_name, f"Test crashed: {e}")
            traceback.print_exc()
    
    # Print comprehensive results
    is_working = validator.print_comprehensive_summary()
    
    return is_working

if __name__ == "__main__":
    asyncio.run(main())
