#!/usr/bin/env python3
"""
Test the Learning System Core Functionality

This test focuses on testing the core learning system components that we can actually test:
1. Strand processing logic
2. Resonance calculations
3. Context injection logic
4. Module-specific scoring
"""

import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add the necessary paths
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/src')

class LearningSystemCoreTest:
    """Test the core learning system functionality"""
    
    def __init__(self):
        self.test_results = []
        self.failures = []
        
    def log_success(self, test_name: str, details: str = ""):
        """Log a successful test"""
        self.test_results.append(f"✅ {test_name}: {details}")
        print(f"✅ {test_name}: {details}")
        
    def log_failure(self, test_name: str, error: str):
        """Log a failed test"""
        self.failures.append(f"❌ {test_name}: {error}")
        print(f"❌ {test_name}: {error}")
    
    def test_strand_processor(self):
        """Test strand processing logic"""
        print("\n🧪 Testing Strand Processor...")
        print("=" * 60)
        
        try:
            from strand_processor import StrandProcessor
            
            # Initialize strand processor
            processor = StrandProcessor()
            
            # Test strand type detection
            test_strands = [
                {'kind': 'pattern', 'source': 'raw_data_intelligence'},
                {'kind': 'prediction_review', 'source': 'central_intelligence_layer'},
                {'kind': 'conditional_trading_plan', 'source': 'conditional_trading_planner'},
                {'kind': 'trading_decision', 'source': 'decision_maker'},
                {'kind': 'execution_outcome', 'source': 'trader'}
            ]
            
            for strand in test_strands:
                try:
                    # Test if strand type is supported
                    is_supported = processor.is_learning_supported(strand['kind'])
                    
                    if is_supported:
                        self.log_success(f"Strand type support: {strand['kind']}", "Supported")
                    else:
                        self.log_failure(f"Strand type support: {strand['kind']}", "Not supported")
                    
                    # Test learning configuration retrieval
                    from strand_processor import StrandType
                    try:
                        strand_type_enum = StrandType(strand['kind'])
                        config = processor.get_learning_config(strand_type_enum)
                    except ValueError:
                        config = None
                    
                    if config:
                        self.log_success(f"Learning config for {strand['kind']}", f"Got config: {config}")
                    else:
                        self.log_failure(f"Learning config for {strand['kind']}", "No config returned")
                        
                except Exception as e:
                    self.log_failure(f"Strand processing for {strand['kind']}", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Strand processor", f"Error: {e}")
            return False
    
    def test_mathematical_resonance_engine(self):
        """Test mathematical resonance calculations"""
        print("\n🧪 Testing Mathematical Resonance Engine...")
        print("=" * 60)
        
        try:
            from mathematical_resonance_engine import MathematicalResonanceEngine
            
            # Initialize resonance engine
            engine = MathematicalResonanceEngine()
            
            # Test module-specific resonance calculations
            modules = ['rdi', 'cil', 'ctp', 'dm', 'td']
            
            for module in modules:
                try:
                    # Create test strand for this module with module-specific fields
                    if module == 'rdi':
                        test_strand = {
                            'id': f'test_{module}_strand',
                            'kind': 'pattern',
                            'module_intelligence': {
                                'pattern_type': 'test_pattern',
                                'analyzer': 'test_analyzer',
                                'confidence': 0.8,
                                'significance': 'high'
                            },
                            'content': {
                                'description': f'Test {module} pattern',
                                'success': True,
                                'confidence': 0.8
                            },
                            'metadata': {'confidence': 0.8}
                        }
                    elif module == 'cil':
                        test_strand = {
                            'id': f'test_{module}_strand',
                            'kind': 'prediction_review',
                            'content': {
                                'description': f'Test {module} prediction',
                                'success': True,
                                'confidence': 0.8
                            },
                            'metadata': {'confidence': 0.8}
                        }
                    elif module == 'ctp':
                        test_strand = {
                            'id': f'test_{module}_strand',
                            'kind': 'conditional_trading_plan',
                            'content': {
                                'description': f'Test {module} plan',
                                'success': True,
                                'confidence': 0.8,
                                'profitability': 0.15,
                                'risk_adjusted_return': 0.12,
                                'plan_type': 'long_position',
                                'strategy': 'momentum'
                            },
                            'metadata': {'confidence': 0.8}
                        }
                    elif module == 'dm':
                        test_strand = {
                            'id': f'test_{module}_strand',
                            'kind': 'trading_decision',
                            'content': {
                                'description': f'Test {module} decision',
                                'success': True,
                                'confidence': 0.8,
                                'outcome_quality': 0.85,
                                'risk_management_effectiveness': 0.90,
                                'decision_type': 'execute_trade',
                                'decision_factors': ['technical', 'fundamental', 'risk']
                            },
                            'metadata': {'confidence': 0.8}
                        }
                    elif module == 'td':
                        test_strand = {
                            'id': f'test_{module}_strand',
                            'kind': 'execution_outcome',
                            'content': {
                                'description': f'Test {module} execution',
                                'success': True,
                                'confidence': 0.8,
                                'execution_success': 0.95,
                                'slippage_minimization': 0.88,
                                'execution_method': 'market_order',
                                'strategy': 'immediate'
                            },
                            'metadata': {'confidence': 0.8}
                        }
                    else:
                        test_strand = {
                            'id': f'test_{module}_strand',
                            'kind': 'pattern',
                            'content': {
                                'description': f'Test {module} pattern',
                                'success': True,
                                'confidence': 0.8
                            },
                            'metadata': {'confidence': 0.8}
                        }
                    
                    # Calculate module-specific resonance
                    resonance = engine.calculate_module_resonance(test_strand, module)
                    
                    if isinstance(resonance, dict) and 'phi' in resonance:
                        phi = resonance.get('phi', 0)
                        rho = resonance.get('rho', 0)
                        theta = resonance.get('theta', 0)
                        omega = resonance.get('omega', 0)
                        
                        self.log_success(f"Resonance calculation for {module.upper()}", 
                                       f"φ={phi:.3f}, ρ={rho:.3f}, θ={theta:.3f}, ω={omega:.3f}")
                    else:
                        self.log_failure(f"Resonance calculation for {module.upper()}", 
                                       f"Invalid result: {resonance}")
                        
                except Exception as e:
                    self.log_failure(f"Resonance calculation for {module.upper()}", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Mathematical resonance engine", f"Error: {e}")
            return False
    
    def test_module_specific_scoring(self):
        """Test module-specific scoring system"""
        print("\n🧪 Testing Module-Specific Scoring...")
        print("=" * 60)
        
        try:
            from module_specific_scoring import ModuleSpecificScoring
            
            # Initialize scoring system
            scoring = ModuleSpecificScoring()
            
            # Test scoring for each module
            modules = ['cil', 'ctp', 'dm', 'td', 'rdi']
            
            for module in modules:
                try:
                    # Create test data for this module with correct field names
                    if module == 'cil':
                        test_data = {
                            'prediction_weight': 0.8,
                            'confidence_weight': 0.75,
                            'success_weight': 1.0
                        }
                    elif module == 'ctp':
                        test_data = {
                            'plan_quality_weight': 0.8,
                            'risk_assessment_weight': 0.75,
                            'execution_weight': 0.85
                        }
                    elif module == 'dm':
                        test_data = {
                            'decision_quality_weight': 0.8,
                            'risk_management_weight': 0.75,
                            'portfolio_impact_weight': 0.85
                        }
                    elif module == 'td':
                        test_data = {
                            'trade_quality_weight': 0.8,
                            'execution_weight': 0.75,
                            'risk_weight': 0.85
                        }
                    elif module == 'rdi':
                        test_data = {
                            'pattern_quality_weight': 0.8,
                            'confidence_weight': 0.75,
                            'accuracy_weight': 0.85
                        }
                    else:
                        test_data = {
                            'confidence': 0.8,
                            'accuracy': 0.75,
                            'success': True,
                            'quality': 0.85
                        }
                    
                    # Calculate module score
                    score = scoring.calculate_module_score(module, test_data)
                    
                    if isinstance(score, (int, float)) and 0 <= score <= 1:
                        self.log_success(f"Module scoring for {module.upper()}", f"Score: {score:.3f}")
                    else:
                        self.log_failure(f"Module scoring for {module.upper()}", f"Invalid score: {score}")
                        
                except Exception as e:
                    self.log_failure(f"Module scoring for {module.upper()}", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Module-specific scoring", f"Error: {e}")
            return False
    
    async def test_context_injection_engine(self):
        """Test context injection engine logic"""
        print("\n🧪 Testing Context Injection Engine...")
        print("=" * 60)
        
        try:
            from context_injection_engine import ContextInjectionEngine
            
            # Create mock supabase manager
            class MockSupabaseManager:
                async def get_strands_by_type(self, strand_type: str):
                    return [
                        {
                            'id': f'strand_{strand_type}_001',
                            'kind': strand_type,
                            'content': f'Test {strand_type} content',
                            'metadata': {'confidence': 0.8}
                        }
                    ]
                
                async def get_braids_by_strand_types(self, strand_types: List[str]):
                    return [
                        {
                            'id': 'braid_001',
                            'strand_types': strand_types,
                            'content': f'Test braid for {strand_types}',
                            'metadata': {'quality': 0.9}
                        }
                    ]
            
            # Initialize context injection engine
            context_engine = ContextInjectionEngine(MockSupabaseManager())
            
            # Test context injection for different modules
            modules = [
                ('cil', ['prediction_review']),
                ('ctp', ['prediction_review', 'trade_outcome']),
                ('dm', ['trading_decision']),
                ('td', ['execution_outcome'])
            ]
            
            for module, strand_types in modules:
                try:
                    # Test context retrieval with await
                    context = await context_engine.get_context_for_module(module, strand_types)
                    
                    if context and len(context) > 0:
                        self.log_success(f"Context injection for {module.upper()}", 
                                       f"Got {len(context)} context items")
                    else:
                        self.log_failure(f"Context injection for {module.upper()}", 
                                       f"No context returned")
                        
                except Exception as e:
                    self.log_failure(f"Context injection for {module.upper()}", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Context injection engine", f"Error: {e}")
            return False
    
    def test_learning_pipeline_components(self):
        """Test learning pipeline component integration"""
        print("\n🧪 Testing Learning Pipeline Components...")
        print("=" * 60)
        
        try:
            # Test individual components
            from multi_cluster_grouping_engine import MultiClusterGroupingEngine
            from per_cluster_learning_system import PerClusterLearningSystem
            from llm_learning_analyzer import LLMLearningAnalyzer
            from braid_level_manager import BraidLevelManager
            
            # Test component initialization
            components = [
                ('MultiClusterGroupingEngine', MultiClusterGroupingEngine),
                ('PerClusterLearningSystem', PerClusterLearningSystem),
                ('LLMLearningAnalyzer', LLMLearningAnalyzer),
                ('BraidLevelManager', BraidLevelManager)
            ]
            
            for name, component_class in components:
                try:
                    # Test component can be instantiated
                    if name == 'MultiClusterGroupingEngine':
                        instance = component_class(None)  # Mock supabase manager
                    elif name == 'PerClusterLearningSystem':
                        instance = component_class(None, None)  # Mock supabase and llm
                    elif name == 'LLMLearningAnalyzer':
                        instance = component_class(None, None)  # Mock llm and prompt manager
                    elif name == 'BraidLevelManager':
                        instance = component_class(None)  # Mock supabase manager
                    
                    self.log_success(f"Component initialization: {name}", "Initialized successfully")
                    
                except Exception as e:
                    self.log_failure(f"Component initialization: {name}", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Learning pipeline components", f"Error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all core learning system tests"""
        print("🚀 LEARNING SYSTEM CORE FUNCTIONALITY TESTING")
        print("Testing the core learning system components and logic")
        print("=" * 80)
        
        self.test_strand_processor()
        self.test_mathematical_resonance_engine()
        self.test_module_specific_scoring()
        await self.test_context_injection_engine()
        self.test_learning_pipeline_components()
        
        # Summary
        print("\n" + "=" * 80)
        print("🔍 LEARNING SYSTEM CORE TEST RESULTS")
        print("=" * 80)
        
        print(f"\n✅ SUCCESSES ({len(self.test_results)}):")
        for result in self.test_results:
            print(f"  {result}")
        
        print(f"\n❌ FAILURES ({len(self.failures)}):")
        for failure in self.failures:
            print(f"  {failure}")
        
        print(f"\n⚡ PERFORMANCE METRICS:")
        print(f"  Total tests: {len(self.test_results) + len(self.failures)}")
        print(f"  Success rate: {len(self.test_results) / (len(self.test_results) + len(self.failures)) * 100:.1f}%")
        
        if self.failures:
            print(f"\n⚠️  LEARNING SYSTEM HAS ISSUES")
            print(f"   {len(self.failures)} components are failing")
            print(f"   Need to fix remaining issues before production")
        else:
            print(f"\n🎉 ALL CORE TESTS PASSED")
            print(f"   Learning system core functionality is working correctly")

if __name__ == "__main__":
    import asyncio
    test = LearningSystemCoreTest()
    asyncio.run(test.run_all_tests())
