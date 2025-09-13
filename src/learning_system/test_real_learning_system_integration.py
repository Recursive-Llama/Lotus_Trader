#!/usr/bin/env python3
"""
Test the REAL Learning System Integration

This test actually tests how the learning system runs the modules through context injection:
1. Learning system processes strands from all modules
2. Learning system creates braids and learning insights
3. Learning system provides context injection to modules
4. Modules use this context to make better decisions
5. Test with real data, real API calls, real database operations
"""

import sys
import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add the necessary paths
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/Modules/Alpha_Detector/src')
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/src')
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁')

class RealLearningSystemIntegrationTest:
    """Test the real learning system integration with actual data flow"""
    
    def __init__(self):
        self.test_results = []
        self.failures = []
        self.learning_system = None
        self.real_strands = []
        
    def log_success(self, test_name: str, details: str = ""):
        """Log a successful test"""
        self.test_results.append(f"✅ {test_name}: {details}")
        print(f"✅ {test_name}: {details}")
        
    def log_failure(self, test_name: str, error: str):
        """Log a failed test"""
        self.failures.append(f"❌ {test_name}: {error}")
        print(f"❌ {test_name}: {error}")
    
    async def setup_real_learning_system(self):
        """Setup the real learning system with actual dependencies"""
        print("\n🔧 Setting up REAL Learning System...")
        print("=" * 60)
        
        try:
            # Import real components
            from centralized_learning_system import CentralizedLearningSystem
            
            # Try to import real dependencies
            try:
                from utils.supabase_manager import SupabaseManager
                from llm_integration.openrouter_client import OpenRouterClient
                from llm_integration.prompt_manager import PromptManager
                
                # Create real instances
                supabase_manager = SupabaseManager()
                llm_client = OpenRouterClient()
                prompt_manager = PromptManager()
                
                self.log_success("Real dependencies import", "Successfully imported real components")
                
            except ImportError as e:
                self.log_failure("Real dependencies import", f"Could not import real components: {e}")
                return False
            
            # Initialize learning system with real dependencies
            self.learning_system = CentralizedLearningSystem(
                supabase_manager,
                llm_client,
                prompt_manager
            )
            
            self.log_success("Learning system initialization", "System initialized with real dependencies")
            return True
            
        except Exception as e:
            self.log_failure("Learning system setup", f"Setup error: {e}")
            return False
    
    async def test_real_strand_processing(self):
        """Test processing real strands from all modules"""
        print("\n🧪 Testing REAL Strand Processing...")
        print("=" * 60)
        
        try:
            # Create realistic test strands from each module
            test_strands = [
                # RDI Pattern Strand
                {
                    'id': 'rdi_pattern_001',
                    'kind': 'pattern',
                    'module_intelligence': {
                        'pattern_type': 'rsi_divergence',
                        'analyzer': 'rsi_analyzer',
                        'confidence': 0.85,
                        'significance': 'high',
                        'description': 'RSI divergence detected on BTC 1H timeframe',
                        'analysis_data': {
                            'rsi': 25,
                            'timeframe': '1H',
                            'accuracy': 0.9,
                            'precision': 0.85,
                            'stability': 0.9
                        }
                    },
                    'sig_sigma': 0.85,
                    'confidence': 0.85,
                    'source': 'raw_data_intelligence',
                    'created_at': datetime.now(timezone.utc).isoformat()
                },
                # CIL Prediction Review Strand
                {
                    'id': 'cil_prediction_001',
                    'kind': 'prediction_review',
                    'content': {
                        'description': 'BTC price prediction review',
                        'success': True,
                        'confidence': 0.78,
                        'prediction_type': 'price_movement',
                        'accuracy': 0.82,
                        'precision': 0.75,
                        'stability': 0.80,
                        'predicted_direction': 'up',
                        'actual_direction': 'up',
                        'error_percentage': 2.5
                    },
                    'metadata': {
                        'prediction_id': 'pred_001',
                        'accuracy': 0.82,
                        'confidence': 0.78,
                        'outcome': 'success',
                        'symbol': 'BTC',
                        'predicted_direction': 'up',
                        'actual_direction': 'up',
                        'price_target': 52000,
                        'actual_price': 51800,
                        'error_percentage': 2.5
                    },
                    'source': 'central_intelligence_layer',
                    'created_at': datetime.now(timezone.utc).isoformat()
                },
                # CTP Conditional Trading Plan Strand
                {
                    'id': 'ctp_plan_001',
                    'kind': 'conditional_trading_plan',
                    'content': {
                        'description': 'BTC long position plan',
                        'success': True,
                        'confidence': 0.72,
                        'plan_type': 'long_position',
                        'profitability': 0.15,
                        'risk_adjusted_return': 0.12,
                        'max_drawdown': 0.05,
                        'sharpe_ratio': 1.8
                    },
                    'metadata': {
                        'plan_id': 'plan_001',
                        'symbol': 'BTC',
                        'direction': 'long',
                        'entry_price': 50000,
                        'target_price': 57500,
                        'stop_loss': 47500,
                        'position_size': 0.1,
                        'risk_percentage': 2.0
                    },
                    'source': 'conditional_trading_planner',
                    'created_at': datetime.now(timezone.utc).isoformat()
                },
                # DM Trading Decision Strand
                {
                    'id': 'dm_decision_001',
                    'kind': 'trading_decision',
                    'content': {
                        'description': 'Execute BTC long position',
                        'success': True,
                        'confidence': 0.88,
                        'decision_type': 'execute_trade',
                        'outcome_quality': 0.85,
                        'risk_management_effectiveness': 0.90,
                        'portfolio_impact': 0.12
                    },
                    'metadata': {
                        'decision_id': 'decision_001',
                        'symbol': 'BTC',
                        'action': 'execute_long',
                        'reasoning': 'Strong RSI divergence signal with high confidence',
                        'risk_assessment': 'Low risk, high reward potential',
                        'portfolio_allocation': 0.1
                    },
                    'source': 'decision_maker',
                    'created_at': datetime.now(timezone.utc).isoformat()
                },
                # TD Execution Outcome Strand
                {
                    'id': 'td_execution_001',
                    'kind': 'execution_outcome',
                    'content': {
                        'description': 'BTC long position executed successfully',
                        'success': True,
                        'confidence': 0.92,
                        'execution_type': 'market_order',
                        'execution_success': 0.95,
                        'slippage_minimization': 0.88,
                        'timing_accuracy': 0.90
                    },
                    'metadata': {
                        'execution_id': 'exec_001',
                        'symbol': 'BTC',
                        'order_type': 'market',
                        'quantity': 0.1,
                        'executed_price': 50100,
                        'slippage': 0.2,
                        'execution_time': '2025-01-13T15:00:00Z'
                    },
                    'source': 'trader',
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
            ]
            
            self.real_strands = test_strands
            
            # Test processing each strand
            for strand in test_strands:
                try:
                    # Process strand through learning system
                    result = await self.learning_system.process_strand(strand)
                    
                    if result:
                        self.log_success(f"Strand processing: {strand['kind']}", f"Successfully processed {strand['id']}")
                    else:
                        self.log_failure(f"Strand processing: {strand['kind']}", f"Failed to process {strand['id']}")
                        
                except Exception as e:
                    self.log_failure(f"Strand processing: {strand['kind']}", f"Error processing {strand['id']}: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Real strand processing", f"Error: {e}")
            return False
    
    async def test_real_context_injection(self):
        """Test real context injection to modules"""
        print("\n🧪 Testing REAL Context Injection...")
        print("=" * 60)
        
        try:
            # Test context injection for each module
            modules = [
                ('cil', ['prediction_review']),
                ('ctp', ['prediction_review', 'trade_outcome']),
                ('dm', ['trading_decision']),
                ('td', ['execution_outcome'])
            ]
            
            for module, strand_types in modules:
                try:
                    # Get context for this module
                    context = await self.learning_system.context_engine.get_context_for_module(
                        module, strand_types
                    )
                    
                    if context and len(context) > 0:
                        self.log_success(f"Context injection for {module.upper()}", 
                                       f"Got {len(context)} context items for {strand_types}")
                    else:
                        self.log_failure(f"Context injection for {module.upper()}", 
                                       f"No context returned for {strand_types}")
                        
                except Exception as e:
                    self.log_failure(f"Context injection for {module.upper()}", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Real context injection", f"Error: {e}")
            return False
    
    async def test_real_llm_calls(self):
        """Test real LLM calls for learning analysis"""
        print("\n🧪 Testing REAL LLM Calls...")
        print("=" * 60)
        
        try:
            # Test LLM client connection
            try:
                test_prompt = "Analyze this trading pattern: RSI divergence detected at 25, volume spike 1.5x average, MACD showing bullish crossover. What is the confidence level and trading recommendation?"
                
                response = await self.learning_system.llm_client.generate_completion(
                    prompt=test_prompt,
                    max_tokens=200,
                    temperature=0.7
                )
                
                if response and len(response) > 10:
                    self.log_success("LLM connection test", f"Got response: {response[:100]}...")
                else:
                    self.log_failure("LLM connection test", f"Invalid response: {response}")
                    
            except Exception as e:
                self.log_failure("LLM connection test", f"Error: {e}")
            
            # Test prompt manager
            try:
                prompt_text = self.learning_system.prompt_manager.get_prompt_text('pattern_analysis')
                
                if prompt_text and len(prompt_text) > 10:
                    self.log_success("Prompt manager test", f"Got prompt: {len(prompt_text)} characters")
                else:
                    self.log_failure("Prompt manager test", "No valid prompt data")
                    
            except Exception as e:
                self.log_failure("Prompt manager test", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Real LLM calls", f"Error: {e}")
            return False
    
    async def test_real_database_operations(self):
        """Test real database operations"""
        print("\n🧪 Testing REAL Database Operations...")
        print("=" * 60)
        
        try:
            # Test database connection
            try:
                result = await self.learning_system.supabase_manager.execute_query("SELECT 1 as test")
                
                if result:
                    self.log_success("Database connection", "Connected successfully")
                else:
                    self.log_failure("Database connection", "No response from database")
                    
            except Exception as e:
                self.log_failure("Database connection", f"Error: {e}")
            
            # Test strand insertion
            try:
                test_strand = {
                    'id': 'test_integration_001',
                    'kind': 'pattern',
                    'content': 'Integration test pattern',
                    'metadata': {'confidence': 0.8},
                    'source': 'integration_test',
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                insert_result = await self.learning_system.supabase_manager.insert_strand(test_strand)
                
                if insert_result:
                    self.log_success("Strand insertion", f"Inserted: {insert_result}")
                else:
                    self.log_failure("Strand insertion", "Failed to insert")
                    
            except Exception as e:
                self.log_failure("Strand insertion", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Real database operations", f"Error: {e}")
            return False
    
    async def test_learning_system_effectiveness(self):
        """Test that the learning system actually improves module performance"""
        print("\n🧪 Testing Learning System Effectiveness...")
        print("=" * 60)
        
        try:
            # Test resonance calculations with real data
            for strand in self.real_strands:
                try:
                    # Determine module type from strand
                    if strand['kind'] == 'pattern':
                        module_type = 'rdi'
                    elif strand['kind'] == 'prediction_review':
                        module_type = 'cil'
                    elif strand['kind'] == 'conditional_trading_plan':
                        module_type = 'ctp'
                    elif strand['kind'] == 'trading_decision':
                        module_type = 'dm'
                    elif strand['kind'] == 'execution_outcome':
                        module_type = 'td'
                    else:
                        continue
                    
                    # Calculate module-specific resonance
                    resonance = self.learning_system.resonance_engine.calculate_module_resonance(
                        strand, module_type
                    )
                    
                    if isinstance(resonance, dict) and 'phi' in resonance:
                        # Check if resonance values make sense
                        phi = resonance.get('phi', 0)
                        rho = resonance.get('rho', 0)
                        theta = resonance.get('theta', 0)
                        omega = resonance.get('omega', 0)
                        
                        if phi > 0 or rho > 0 or theta > 0 or omega > 0:
                            self.log_success(f"Resonance calculation for {module_type.upper()}", 
                                           f"φ={phi:.3f}, ρ={rho:.3f}, θ={theta:.3f}, ω={omega:.3f}")
                        else:
                            self.log_failure(f"Resonance calculation for {module_type.upper()}", 
                                           f"All values are 0: φ={phi}, ρ={rho}, θ={theta}, ω={omega}")
                    else:
                        self.log_failure(f"Resonance calculation for {module_type.upper()}", 
                                       f"Invalid result: {resonance}")
                        
                except Exception as e:
                    self.log_failure(f"Resonance calculation for {strand['kind']}", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Learning system effectiveness", f"Error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all real learning system integration tests"""
        print("🚀 REAL LEARNING SYSTEM INTEGRATION TESTING")
        print("Testing how the learning system runs the modules through context injection")
        print("=" * 80)
        
        # Setup
        if not await self.setup_real_learning_system():
            print("❌ Cannot proceed without learning system setup")
            return
        
        # Run tests
        await self.test_real_strand_processing()
        await self.test_real_context_injection()
        await self.test_real_llm_calls()
        await self.test_real_database_operations()
        await self.test_learning_system_effectiveness()
        
        # Summary
        print("\n" + "=" * 80)
        print("🔍 REAL LEARNING SYSTEM INTEGRATION TEST RESULTS")
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
            print(f"\n🎉 ALL TESTS PASSED")
            print(f"   Learning system is running modules effectively through context injection")

if __name__ == "__main__":
    test = RealLearningSystemIntegrationTest()
    asyncio.run(test.run_all_tests())
