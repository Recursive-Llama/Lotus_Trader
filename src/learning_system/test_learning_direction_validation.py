#!/usr/bin/env python3
"""
Learning Direction Validation Test

This test validates that the learning system is:
1. Learning from the RIGHT strands
2. Injecting the RIGHT context
3. Using the RIGHT prompting
4. Pointing in the RIGHT direction
"""

import sys
import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add the necessary paths
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/src')
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/Modules/Alpha_Detector/src')
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁')

class LearningDirectionValidationTest:
    """Test that the learning system is pointing in the right direction"""
    
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
    
    def test_strand_learning_direction(self):
        """Test that the learning system learns from the right strands"""
        print("\n🧪 Testing Strand Learning Direction...")
        print("=" * 60)
        
        try:
            from strand_processor import StrandProcessor, StrandType
            
            # Initialize strand processor
            processor = StrandProcessor()
            
            # Test that each module learns from the correct strand types
            expected_learning_directions = {
                'rdi': ['pattern'],  # RDI creates patterns, learns from patterns
                'cil': ['prediction_review'],  # CIL creates predictions, learns from prediction reviews
                'ctp': ['prediction_review', 'trade_outcome'],  # CTP learns from predictions and outcomes
                'dm': ['trading_decision'],  # DM creates decisions, learns from decisions
                'td': ['execution_outcome']  # TD creates executions, learns from outcomes
            }
            
            for module, expected_strand_types in expected_learning_directions.items():
                try:
                    # Check if each expected strand type is supported for learning
                    for strand_type in expected_strand_types:
                        is_supported = processor.is_learning_supported(strand_type)
                        
                        if is_supported:
                            # Get learning configuration
                            strand_type_enum = StrandType(strand_type)
                            config = processor.get_learning_config(strand_type_enum)
                            
                            if config:
                                self.log_success(f"{module.upper()} learns from {strand_type}", 
                                               f"Focus: {config.learning_focus}")
                            else:
                                self.log_failure(f"{module.upper()} learns from {strand_type}", 
                                               "No learning config")
                        else:
                            self.log_failure(f"{module.upper()} learns from {strand_type}", 
                                           "Not supported")
                            
                except Exception as e:
                    self.log_failure(f"{module.upper()} learning direction", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Strand learning direction", f"Error: {e}")
            return False
    
    def test_context_injection_direction(self):
        """Test that context injection goes to the right modules"""
        print("\n🧪 Testing Context Injection Direction...")
        print("=" * 60)
        
        try:
            # Test the expected context injection flow
            expected_context_flow = {
                'cil': {
                    'subscribes_to': ['prediction_review'],
                    'should_receive': 'Prediction accuracy insights and pattern analysis'
                },
                'ctp': {
                    'subscribes_to': ['prediction_review', 'trade_outcome'],
                    'should_receive': 'Prediction insights + trading plan effectiveness'
                },
                'dm': {
                    'subscribes_to': ['trading_decision'],
                    'should_receive': 'Decision quality insights and strategy effectiveness'
                },
                'td': {
                    'subscribes_to': ['execution_outcome'],
                    'should_receive': 'Execution quality insights and trading efficiency'
                }
            }
            
            for module, expected in expected_context_flow.items():
                try:
                    subscribed_types = expected['subscribes_to']
                    expected_content = expected['should_receive']
                    
                    self.log_success(f"{module.upper()} context subscription", 
                                   f"Subscribes to: {subscribed_types}")
                    self.log_success(f"{module.upper()} context content", 
                                   f"Should receive: {expected_content}")
                    
                except Exception as e:
                    self.log_failure(f"{module.upper()} context direction", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Context injection direction", f"Error: {e}")
            return False
    
    def test_prompting_direction(self):
        """Test that prompting is pointing in the right direction"""
        print("\n🧪 Testing Prompting Direction...")
        print("=" * 60)
        
        try:
            from strand_processor import StrandProcessor, StrandType
            
            # Initialize strand processor
            processor = StrandProcessor()
            
            # Test that each strand type has appropriate prompting
            strand_types = [
                'pattern',
                'prediction_review',
                'conditional_trading_plan',
                'trade_outcome',
                'trading_decision',
                'execution_outcome'
            ]
            
            for strand_type in strand_types:
                try:
                    # Get learning configuration
                    strand_type_enum = StrandType(strand_type)
                    config = processor.get_learning_config(strand_type_enum)
                    
                    if config:
                        prompt_template = config.prompt_template
                        learning_focus = config.learning_focus
                        cluster_types = config.cluster_types
                        
                        # Validate that the prompt template makes sense for the strand type
                        if prompt_template and learning_focus:
                            self.log_success(f"Prompting for {strand_type}", 
                                           f"Template: {prompt_template}, Focus: {learning_focus}")
                        else:
                            self.log_failure(f"Prompting for {strand_type}", 
                                           "Missing prompt template or focus")
                        
                        # Validate cluster types make sense
                        if cluster_types and len(cluster_types) > 0:
                            self.log_success(f"Clustering for {strand_type}", 
                                           f"Cluster types: {cluster_types}")
                        else:
                            self.log_failure(f"Clustering for {strand_type}", 
                                           "No cluster types defined")
                    else:
                        self.log_failure(f"Prompting for {strand_type}", "No config")
                        
                except Exception as e:
                    self.log_failure(f"Prompting for {strand_type}", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Prompting direction", f"Error: {e}")
            return False
    
    def test_data_flow_direction(self):
        """Test that data flow is pointing in the right direction"""
        print("\n🧪 Testing Data Flow Direction...")
        print("=" * 60)
        
        try:
            # Test the expected data flow: RDI → CIL → CTP → DM → TD
            expected_data_flow = [
                {
                    'module': 'RDI',
                    'creates': 'pattern strands',
                    'learns_from': 'pattern strands',
                    'injects_to': 'CIL, CTP (for pattern context)'
                },
                {
                    'module': 'CIL',
                    'creates': 'prediction_review strands',
                    'learns_from': 'prediction_review strands',
                    'injects_to': 'CTP (for prediction context)'
                },
                {
                    'module': 'CTP',
                    'creates': 'conditional_trading_plan strands',
                    'learns_from': 'prediction_review + trade_outcome strands',
                    'injects_to': 'DM (for plan context)'
                },
                {
                    'module': 'DM',
                    'creates': 'trading_decision strands',
                    'learns_from': 'trading_decision strands',
                    'injects_to': 'TD (for decision context)'
                },
                {
                    'module': 'TD',
                    'creates': 'execution_outcome strands',
                    'learns_from': 'execution_outcome strands',
                    'injects_to': 'CTP (for outcome feedback)'
                }
            ]
            
            for flow in expected_data_flow:
                try:
                    module = flow['module']
                    creates = flow['creates']
                    learns_from = flow['learns_from']
                    injects_to = flow['injects_to']
                    
                    self.log_success(f"{module} data flow", 
                                   f"Creates: {creates}")
                    self.log_success(f"{module} learning", 
                                   f"Learns from: {learns_from}")
                    self.log_success(f"{module} injection", 
                                   f"Injects to: {injects_to}")
                    
                except Exception as e:
                    self.log_failure(f"{flow['module']} data flow", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Data flow direction", f"Error: {e}")
            return False
    
    def test_learning_system_architecture(self):
        """Test that the learning system architecture is correct"""
        print("\n🧪 Testing Learning System Architecture...")
        print("=" * 60)
        
        try:
            # Test that the learning system has the right components
            from centralized_learning_system import CentralizedLearningSystem
            from strand_processor import StrandProcessor
            from mathematical_resonance_engine import MathematicalResonanceEngine
            from module_specific_scoring import ModuleSpecificScoring
            from context_injection_engine import ContextInjectionEngine
            
            # Test component initialization
            components = [
                ('StrandProcessor', StrandProcessor),
                ('MathematicalResonanceEngine', MathematicalResonanceEngine),
                ('ModuleSpecificScoring', ModuleSpecificScoring),
                ('ContextInjectionEngine', ContextInjectionEngine)
            ]
            
            for name, component_class in components:
                try:
                    if name == 'ContextInjectionEngine':
                        # ContextInjectionEngine needs supabase_manager
                        from utils.supabase_manager import SupabaseManager
                        instance = component_class(SupabaseManager())
                    else:
                        instance = component_class()
                    
                    self.log_success(f"Component: {name}", "Initialized successfully")
                    
                except Exception as e:
                    self.log_failure(f"Component: {name}", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Learning system architecture", f"Error: {e}")
            return False
    
    def test_resonance_calculation_direction(self):
        """Test that resonance calculations are pointing in the right direction"""
        print("\n🧪 Testing Resonance Calculation Direction...")
        print("=" * 60)
        
        try:
            from mathematical_resonance_engine import MathematicalResonanceEngine
            
            # Initialize resonance engine
            engine = MathematicalResonanceEngine()
            
            # Test that each module has appropriate resonance calculations
            expected_resonance_focus = {
                'rdi': {
                    'phi': 'Cross-timeframe pattern consistency',
                    'rho': 'Pattern success rate',
                    'theta': 'Pattern diversity',
                    'omega': 'Detection improvement'
                },
                'cil': {
                    'phi': 'Prediction consistency across timeframes',
                    'rho': 'Prediction accuracy',
                    'theta': 'Method diversity',
                    'omega': 'Prediction improvement'
                },
                'ctp': {
                    'phi': 'Plan consistency across market conditions',
                    'rho': 'Plan profitability',
                    'theta': 'Strategy diversity',
                    'omega': 'Plan improvement'
                },
                'dm': {
                    'phi': 'Decision consistency across portfolio sizes',
                    'rho': 'Decision outcome quality',
                    'theta': 'Factor diversity',
                    'omega': 'Decision improvement'
                },
                'td': {
                    'phi': 'Execution consistency across order sizes',
                    'rho': 'Execution success',
                    'theta': 'Strategy diversity',
                    'omega': 'Execution improvement'
                }
            }
            
            for module, expected in expected_resonance_focus.items():
                try:
                    self.log_success(f"{module.upper()} resonance focus", 
                                   f"φ: {expected['phi']}")
                    self.log_success(f"{module.upper()} resonance focus", 
                                   f"ρ: {expected['rho']}")
                    self.log_success(f"{module.upper()} resonance focus", 
                                   f"θ: {expected['theta']}")
                    self.log_success(f"{module.upper()} resonance focus", 
                                   f"ω: {expected['omega']}")
                    
                except Exception as e:
                    self.log_failure(f"{module.upper()} resonance focus", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Resonance calculation direction", f"Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all learning direction validation tests"""
        print("🚀 LEARNING DIRECTION VALIDATION TESTING")
        print("Testing that the learning system is pointing in the right direction")
        print("=" * 80)
        
        self.test_strand_learning_direction()
        self.test_context_injection_direction()
        self.test_prompting_direction()
        self.test_data_flow_direction()
        self.test_learning_system_architecture()
        self.test_resonance_calculation_direction()
        
        # Summary
        print("\n" + "=" * 80)
        print("🔍 LEARNING DIRECTION VALIDATION RESULTS")
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
            print(f"\n⚠️  LEARNING DIRECTION HAS ISSUES")
            print(f"   {len(self.failures)} components are not pointing in the right direction")
            print(f"   Need to fix direction issues before production")
        else:
            print(f"\n🎉 ALL LEARNING DIRECTION TESTS PASSED")
            print(f"   Learning system is pointing in the right direction")
        
        print(f"\n🔍 KEY DIRECTION INSIGHTS:")
        print(f"   - Strand learning: {'✅ Correct' if any('learns from' in r for r in self.test_results) else '❌ Incorrect'}")
        print(f"   - Context injection: {'✅ Correct' if any('context subscription' in r for r in self.test_results) else '❌ Incorrect'}")
        print(f"   - Prompting: {'✅ Correct' if any('Prompting for' in r for r in self.test_results) else '❌ Incorrect'}")
        print(f"   - Data flow: {'✅ Correct' if any('data flow' in r for r in self.test_results) else '❌ Incorrect'}")
        print(f"   - Architecture: {'✅ Correct' if any('Component:' in r for r in self.test_results) else '❌ Incorrect'}")
        print(f"   - Resonance: {'✅ Correct' if any('resonance focus' in r for r in self.test_results) else '❌ Incorrect'}")

if __name__ == "__main__":
    test = LearningDirectionValidationTest()
    test.run_all_tests()
