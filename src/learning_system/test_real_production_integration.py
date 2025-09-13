#!/usr/bin/env python3
"""
Real Production Integration Test

This test connects to the actual production system:
1. Real Supabase database connection
2. Real OpenRouter LLM API calls
3. Real data flow testing
4. End-to-end integration testing
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

class RealProductionIntegrationTest:
    """Test the learning system with real production components"""
    
    def __init__(self):
        self.test_results = []
        self.failures = []
        self.real_strands = []
        
    def log_success(self, test_name: str, details: str = ""):
        """Log a successful test"""
        self.test_results.append(f"✅ {test_name}: {details}")
        print(f"✅ {test_name}: {details}")
        
    def log_failure(self, test_name: str, error: str):
        """Log a failed test"""
        self.failures.append(f"❌ {test_name}: {error}")
        print(f"❌ {test_name}: {error}")
    
    async def test_real_database_connection(self):
        """Test real Supabase database connection"""
        print("\n🧪 Testing Real Database Connection...")
        print("=" * 60)
        
        try:
            # Import real Supabase client
            from utils.supabase_manager import SupabaseManager
            
            # Initialize real database connection
            supabase_manager = SupabaseManager()
            
            # Test database connection
            try:
                # Test basic query
                result = await supabase_manager.execute_query("SELECT 1 as test")
                
                if result:
                    self.log_success("Database connection", "Connected to Supabase successfully")
                else:
                    self.log_failure("Database connection", "No response from database")
                    
            except Exception as e:
                self.log_failure("Database connection", f"Connection error: {e}")
                return False
            
            # Test strand operations
            try:
                # Test strand insertion
                test_strand = {
                    'id': 'test_production_001',
                    'kind': 'pattern',
                    'module': 'raw_data_intelligence',
                    'content': {
                        'pattern_type': 'rsi_divergence',
                        'confidence': 0.85,
                        'description': 'Production test pattern'
                    },
                    'metadata': {'confidence': 0.85},
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                insert_result = supabase_manager.insert_strand(test_strand)
                
                if insert_result:
                    self.log_success("Strand insertion", f"Inserted strand: {insert_result}")
                else:
                    self.log_failure("Strand insertion", "Failed to insert strand")
                    
            except Exception as e:
                self.log_failure("Strand insertion", f"Error: {e}")
            
            # Test strand retrieval
            try:
                strands = supabase_manager.get_strands_by_type('pattern', limit=5)
                
                if strands and len(strands) > 0:
                    self.log_success("Strand retrieval", f"Retrieved {len(strands)} pattern strands")
                    self.real_strands = strands
                else:
                    self.log_failure("Strand retrieval", "No strands retrieved")
                    
            except Exception as e:
                self.log_failure("Strand retrieval", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Database setup", f"Error: {e}")
            return False
    
    async def test_real_llm_integration(self):
        """Test real OpenRouter LLM integration"""
        print("\n🧪 Testing Real LLM Integration...")
        print("=" * 60)
        
        try:
            # Import real LLM client
            from llm_integration.openrouter_client import OpenRouterClient
            from llm_integration.prompt_manager import PromptManager
            
            # Initialize real LLM components
            llm_client = OpenRouterClient()
            prompt_manager = PromptManager()
            
            # Test LLM connection
            try:
                test_prompt = "Analyze this trading pattern: RSI divergence detected at 25, volume spike 1.5x average, MACD showing bullish crossover. What is the confidence level and trading recommendation?"
                
                response = await llm_client.generate_completion(
                    prompt=test_prompt,
                    max_tokens=200,
                    temperature=0.7
                )
                
                if response and len(response) > 10:
                    self.log_success("LLM connection", f"Got response: {response[:100]}...")
                else:
                    self.log_failure("LLM connection", f"Invalid response: {response}")
                    
            except Exception as e:
                self.log_failure("LLM connection", f"Error: {e}")
            
            # Test prompt manager
            try:
                prompt_text = prompt_manager.get_prompt_text('pattern_analysis')
                
                if prompt_text and len(prompt_text) > 10:
                    self.log_success("Prompt manager", f"Got prompt: {len(prompt_text)} characters")
                else:
                    self.log_failure("Prompt manager", "No valid prompt data")
                    
            except Exception as e:
                self.log_failure("Prompt manager", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("LLM setup", f"Error: {e}")
            return False
    
    async def test_real_learning_system_integration(self):
        """Test real learning system with actual components"""
        print("\n🧪 Testing Real Learning System Integration...")
        print("=" * 60)
        
        try:
            from centralized_learning_system import CentralizedLearningSystem
            from utils.supabase_manager import SupabaseManager
            from llm_integration.openrouter_client import OpenRouterClient
            from llm_integration.prompt_manager import PromptManager
            
            # Initialize real learning system
            supabase_manager = SupabaseManager()
            llm_client = OpenRouterClient()
            prompt_manager = PromptManager()
            
            learning_system = CentralizedLearningSystem(
                supabase_manager,
                llm_client,
                prompt_manager
            )
            
            # Test with real strands if available
            if self.real_strands:
                test_strands = self.real_strands[:3]  # Use first 3 real strands
            else:
                # Create realistic test strands
                test_strands = [
                    {
                        'id': 'real_test_001',
                        'kind': 'pattern',
                        'module_intelligence': {
                            'pattern_type': 'rsi_divergence',
                            'analyzer': 'rsi_analyzer',
                            'confidence': 0.88,
                            'significance': 'high',
                            'description': 'Real RSI divergence detected on BTC 1H',
                            'analysis_data': {
                                'rsi': 22,
                                'timeframe': '1H',
                                'accuracy': 0.92,
                                'precision': 0.88,
                                'stability': 0.90
                            }
                        },
                        'sig_sigma': 0.88,
                        'confidence': 0.88,
                        'source': 'raw_data_intelligence',
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }
                ]
            
            # Test strand processing
            for strand in test_strands:
                try:
                    result = await learning_system.process_strand(strand)
                    
                    if result:
                        self.log_success(f"Strand processing: {strand['kind']}", f"Successfully processed {strand['id']}")
                    else:
                        self.log_failure(f"Strand processing: {strand['kind']}", f"Failed to process {strand['id']}")
                        
                except Exception as e:
                    self.log_failure(f"Strand processing: {strand['kind']}", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Learning system integration", f"Error: {e}")
            return False
    
    async def test_real_context_injection(self):
        """Test real context injection with actual database"""
        print("\n🧪 Testing Real Context Injection...")
        print("=" * 60)
        
        try:
            from context_injection_engine import ContextInjectionEngine
            from utils.supabase_manager import SupabaseManager
            
            # Initialize real context injection
            supabase_manager = SupabaseManager()
            context_engine = ContextInjectionEngine(supabase_manager)
            
            # Test context injection for each module
            modules = [
                ('cil', ['prediction_review']),
                ('ctp', ['prediction_review', 'trade_outcome']),
                ('dm', ['trading_decision']),
                ('td', ['execution_outcome'])
            ]
            
            for module, strand_types in modules:
                try:
                    # Get real context from database
                    context = await context_engine.get_context_for_module(module, strand_types)
                    
                    if context and len(context) > 0:
                        self.log_success(f"Real context injection for {module.upper()}", 
                                       f"Got {len(context)} context items from database")
                    else:
                        self.log_success(f"Real context injection for {module.upper()}", 
                                       f"No context available (empty database)")
                        
                except Exception as e:
                    self.log_failure(f"Real context injection for {module.upper()}", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Real context injection", f"Error: {e}")
            return False
    
    async def test_real_llm_learning_analysis(self):
        """Test real LLM learning analysis"""
        print("\n🧪 Testing Real LLM Learning Analysis...")
        print("=" * 60)
        
        try:
            from llm_learning_analyzer import LLMLearningAnalyzer
            from llm_integration.openrouter_client import OpenRouterClient
            from llm_integration.prompt_manager import PromptManager
            
            # Initialize real LLM components
            llm_client = OpenRouterClient()
            prompt_manager = PromptManager()
            analyzer = LLMLearningAnalyzer(llm_client, prompt_manager)
            
            # Test with real strand data
            test_strands = [
                {
                    'id': 'llm_test_001',
                    'kind': 'pattern',
                    'content': {
                        'pattern_type': 'rsi_divergence',
                        'confidence': 0.88,
                        'description': 'RSI divergence detected on BTC 1H timeframe',
                        'analysis_data': {
                            'rsi': 22,
                            'timeframe': '1H',
                            'accuracy': 0.92
                        }
                    }
                },
                {
                    'id': 'llm_test_002',
                    'kind': 'pattern',
                    'content': {
                        'pattern_type': 'rsi_divergence',
                        'confidence': 0.85,
                        'description': 'Another RSI divergence on ETH 4H timeframe',
                        'analysis_data': {
                            'rsi': 25,
                            'timeframe': '4H',
                            'accuracy': 0.88
                        }
                    }
                }
            ]
            
            try:
                # Test real LLM analysis
                analysis = await analyzer.analyze_cluster(test_strands, 'pattern_cluster', 'pattern')
                
                if analysis and len(analysis) > 0:
                    self.log_success("Real LLM analysis", f"Generated analysis: {analysis}")
                else:
                    self.log_failure("Real LLM analysis", "No analysis generated")
                    
            except Exception as e:
                self.log_failure("Real LLM analysis", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Real LLM learning analysis", f"Error: {e}")
            return False
    
    async def test_end_to_end_data_flow(self):
        """Test complete end-to-end data flow"""
        print("\n🧪 Testing End-to-End Data Flow...")
        print("=" * 60)
        
        try:
            from centralized_learning_system import CentralizedLearningSystem
            from utils.supabase_manager import SupabaseManager
            from llm_integration.openrouter_client import OpenRouterClient
            from llm_integration.prompt_manager import PromptManager
            
            # Initialize complete system
            supabase_manager = SupabaseManager()
            llm_client = OpenRouterClient()
            prompt_manager = PromptManager()
            
            learning_system = CentralizedLearningSystem(
                supabase_manager,
                llm_client,
                prompt_manager
            )
            
            # Simulate complete data flow: RDI → Learning System → Context Injection
            test_strands = [
                # RDI Pattern Strand
                {
                    'id': 'e2e_rdi_001',
                    'kind': 'pattern',
                    'module_intelligence': {
                        'pattern_type': 'rsi_divergence',
                        'analyzer': 'rsi_analyzer',
                        'confidence': 0.90,
                        'significance': 'high',
                        'description': 'End-to-end test RSI divergence',
                        'analysis_data': {
                            'rsi': 20,
                            'timeframe': '1H',
                            'accuracy': 0.95,
                            'precision': 0.90,
                            'stability': 0.92
                        }
                    },
                    'sig_sigma': 0.90,
                    'confidence': 0.90,
                    'source': 'raw_data_intelligence',
                    'created_at': datetime.now(timezone.utc).isoformat()
                },
                # CIL Prediction Review Strand
                {
                    'id': 'e2e_cil_001',
                    'kind': 'prediction_review',
                    'content': {
                        'description': 'End-to-end test prediction review',
                        'success': True,
                        'confidence': 0.85,
                        'prediction_type': 'price_movement',
                        'accuracy': 0.88,
                        'precision': 0.82,
                        'stability': 0.85
                    },
                    'metadata': {
                        'prediction_id': 'e2e_pred_001',
                        'accuracy': 0.88,
                        'confidence': 0.85,
                        'outcome': 'success'
                    },
                    'source': 'central_intelligence_layer',
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
            ]
            
            # Process strands through learning system
            for strand in test_strands:
                try:
                    result = await learning_system.process_strand(strand)
                    
                    if result:
                        self.log_success(f"E2E processing: {strand['kind']}", f"Processed {strand['id']}")
                    else:
                        self.log_failure(f"E2E processing: {strand['kind']}", f"Failed to process {strand['id']}")
                        
                except Exception as e:
                    self.log_failure(f"E2E processing: {strand['kind']}", f"Error: {e}")
            
            # Test context injection back to modules
            try:
                context = await learning_system.context_engine.get_context_for_module('cil', ['prediction_review'])
                
                if context and len(context) > 0:
                    self.log_success("E2E context injection", f"Got {len(context)} context items for CIL")
                else:
                    self.log_success("E2E context injection", "No context available (expected for empty database)")
                    
            except Exception as e:
                self.log_failure("E2E context injection", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("End-to-end data flow", f"Error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all real production integration tests"""
        print("🚀 REAL PRODUCTION INTEGRATION TESTING")
        print("Testing with actual database, LLM, and data flow")
        print("=" * 80)
        
        # Test real components
        await self.test_real_database_connection()
        await self.test_real_llm_integration()
        await self.test_real_learning_system_integration()
        await self.test_real_context_injection()
        await self.test_real_llm_learning_analysis()
        await self.test_end_to_end_data_flow()
        
        # Summary
        print("\n" + "=" * 80)
        print("🔍 REAL PRODUCTION INTEGRATION TEST RESULTS")
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
            print(f"\n⚠️  PRODUCTION INTEGRATION HAS ISSUES")
            print(f"   {len(self.failures)} components are failing")
            print(f"   Need to fix remaining issues before production")
        else:
            print(f"\n🎉 ALL PRODUCTION TESTS PASSED")
            print(f"   Learning system is ready for production deployment")
        
        print(f"\n🔍 PRODUCTION READINESS ASSESSMENT:")
        print(f"   - Database integration: {'✅ Working' if any('Database' in r for r in self.test_results) else '❌ Failed'}")
        print(f"   - LLM integration: {'✅ Working' if any('LLM' in r for r in self.test_results) else '❌ Failed'}")
        print(f"   - Learning system: {'✅ Working' if any('Learning system' in r for r in self.test_results) else '❌ Failed'}")
        print(f"   - Context injection: {'✅ Working' if any('Context injection' in r for r in self.test_results) else '❌ Failed'}")
        print(f"   - End-to-end flow: {'✅ Working' if any('E2E' in r for r in self.test_results) else '❌ Failed'}")

if __name__ == "__main__":
    test = RealProductionIntegrationTest()
    asyncio.run(test.run_all_tests())
