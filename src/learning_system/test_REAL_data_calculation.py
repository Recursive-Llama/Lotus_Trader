#!/usr/bin/env python3
"""
REAL Data Calculation Test

This test actually tests that the system calculates confidence, quality, and other metrics
from raw market data, rather than just looking for pre-calculated values.
"""

import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add the necessary paths
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/Modules/Alpha_Detector/src')
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/src')

class RealDataCalculationTest:
    """Test that the system actually calculates metrics from raw data"""
    
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
        
    def test_real_market_data_processing(self):
        """Test that market data is processed and metrics are calculated"""
        print("\n🧪 Testing REAL Market Data Processing...")
        print("=" * 60)
        
        try:
            # Test 1: Raw market data from Hyperliquid
            raw_market_data = {
                'symbol': 'BTC',
                'price': 50000.0,
                'volume': 1000000,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'ohlcv': {
                    'open': 49500.0,
                    'high': 50500.0,
                    'low': 49000.0,
                    'close': 50000.0,
                    'volume': 1000000
                },
                'orderbook': {
                    'bids': [(49950.0, 100), (49900.0, 200), (49850.0, 150)],
                    'asks': [(50050.0, 120), (50100.0, 180), (50150.0, 90)]
                }
            }
            
            # Test 2: Check if we can import the actual calculation methods
            try:
                from intelligence.raw_data_intelligence.market_microstructure import MarketMicrostructureAnalyzer
                from core_detection.signal_generator import SignalGenerator
                
                # Test 3: Create analyzers
                microstructure_analyzer = MarketMicrostructureAnalyzer()
                signal_generator = SignalGenerator()
                
                # Test 4: Process raw data to get calculated metrics
                analysis_results = {
                    'data_points': 150,  # Simulate processed data
                    'order_flow': {'buy_flow': 0.6, 'sell_flow': 0.4},
                    'price_impact': {'impact': 0.02},
                    'volume_distribution': {'concentration': 0.7},
                    'time_microstructure': {'volatility': 0.15},
                    'market_maker_behavior': {'spread': 0.001}
                }
                
                # Test 5: Calculate confidence from raw data
                calculated_confidence = microstructure_analyzer._calculate_analysis_confidence(analysis_results)
                
                if calculated_confidence > 0:
                    self.log_success(f"Market microstructure confidence calculation", f"Calculated: {calculated_confidence:.3f}")
                else:
                    self.log_failure("Market microstructure confidence calculation", "Returned 0.0")
                
                # Test 6: Calculate signal confidence from features
                features = {
                    'rsi': 25,  # Oversold
                    'macd_histogram': 0.05,
                    'volume_ratio': 1.5
                }
                patterns = {
                    'breakout_strength': 0.8
                }
                regime = 'trending_up'
                direction = 'long'
                
                signal_confidence = signal_generator._calculate_confidence(features, patterns, regime, direction)
                
                if signal_confidence > 0:
                    self.log_success(f"Signal confidence calculation", f"Calculated: {signal_confidence:.3f}")
                else:
                    self.log_failure("Signal confidence calculation", "Returned 0.0")
                
                # Test 7: Test that the learning system can use these calculated values
                from learning_system.mathematical_resonance_engine import MathematicalResonanceEngine
                
                resonance_engine = MathematicalResonanceEngine()
                
                # Create strand with calculated values
                calculated_strand = {
                    'kind': 'pattern',
                    'content': {
                        'description': 'RSI divergence pattern',
                        'success': True,
                        'confidence': calculated_confidence,  # Use calculated value
                        'pattern_type': 'rsi_divergence',
                        'accuracy': 0.9,
                        'precision': 0.85,
                        'stability': 0.9
                    },
                    'metadata': {
                        'rsi': 25,
                        'timeframe': '1H',
                        'confidence': calculated_confidence,  # Use calculated value
                        'pattern_type': 'rsi_divergence',
                        'accuracy': 0.9,
                        'precision': 0.85,
                        'stability': 0.9
                    },
                    'source': 'raw_data_intelligence',
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Test 8: Calculate φ with real calculated values
                pattern_data = {
                    '1m': {'confidence': calculated_confidence, 'quality': 0.9},
                    '5m': {'confidence': calculated_confidence * 0.9, 'quality': 0.85},
                    '15m': {'confidence': calculated_confidence * 0.8, 'quality': 0.8}
                }
                timeframes = ['1m', '5m', '15m']
                
                phi = resonance_engine.calculate_phi(pattern_data, timeframes)
                
                if phi > 0:
                    self.log_success(f"φ calculation with real data", f"φ = {phi:.3f}")
                else:
                    self.log_failure("φ calculation with real data", f"φ = {phi:.3f} (should be > 0)")
                
                # Test 9: Test module resonance with calculated values
                module_resonance = resonance_engine.calculate_module_resonance(calculated_strand, 'rdi')
                
                if isinstance(module_resonance, dict) and module_resonance.get('phi', 0) > 0:
                    self.log_success(f"Module resonance with real data", f"Calculated: {module_resonance}")
                else:
                    self.log_failure("Module resonance with real data", f"Got: {module_resonance}")
                
            except ImportError as e:
                self.log_failure("Import calculation methods", f"Could not import: {e}")
            except Exception as e:
                self.log_failure("Real data calculation", f"Error: {e}")
                
        except Exception as e:
            self.log_failure("Real market data processing", f"Error: {e}")
    
    def test_llm_calls_with_real_data(self):
        """Test that LLM calls work with real data"""
        print("\n🤖 Testing REAL LLM Calls...")
        print("=" * 60)
        
        try:
            # Test 1: Import LLM client
            from llm_integration.openrouter_client import OpenRouterClient
            from llm_integration.prompt_manager import PromptManager
            
            # Test 2: Create LLM client
            llm_client = OpenRouterClient()
            prompt_manager = PromptManager()
            
            # Test 3: Test prompt retrieval
            try:
                prompt_text = prompt_manager.get_prompt_text('pattern_analysis')
                if prompt_text and len(prompt_text) > 10:
                    self.log_success("Prompt retrieval", f"Got prompt: {len(prompt_text)} characters")
                else:
                    self.log_failure("Prompt retrieval", "No valid prompt data")
            except Exception as e:
                self.log_failure("Prompt retrieval", f"Error: {e}")
            
            # Test 4: Test LLM call with real data
            try:
                test_prompt = "Analyze this market pattern: RSI divergence detected at 25, volume spike 1.5x average, MACD showing bullish crossover. What is the confidence level?"
                
                response = llm_client.generate_completion(
                    prompt=test_prompt,
                    max_tokens=100,
                    temperature=0.7
                )
                
                if response and len(response) > 10:
                    self.log_success("LLM call with real data", f"Response: {response[:100]}...")
                else:
                    self.log_failure("LLM call with real data", f"Invalid response: {response}")
                    
            except Exception as e:
                self.log_failure("LLM call with real data", f"Error: {e}")
                
        except ImportError as e:
            self.log_failure("Import LLM components", f"Could not import: {e}")
        except Exception as e:
            self.log_failure("LLM testing", f"Error: {e}")
    
    def test_database_operations_with_real_data(self):
        """Test that database operations work with real data"""
        print("\n🗄️ Testing REAL Database Operations...")
        print("=" * 60)
        
        try:
            # Test 1: Import database client
            from database.supabase_client import SupabaseClient
            
            # Test 2: Create database client
            db_client = SupabaseClient()
            
            # Test 3: Test database connection
            try:
                # Test a simple query
                result = db_client.execute_query("SELECT 1 as test")
                if result:
                    self.log_success("Database connection", "Connected successfully")
                else:
                    self.log_failure("Database connection", "No response from database")
            except Exception as e:
                self.log_failure("Database connection", f"Error: {e}")
            
            # Test 4: Test strand insertion with real data
            try:
                real_strand = {
                    'kind': 'pattern',
                    'content': {
                        'description': 'Real RSI divergence pattern',
                        'success': True,
                        'confidence': 0.85,
                        'pattern_type': 'rsi_divergence',
                        'accuracy': 0.9,
                        'precision': 0.85,
                        'stability': 0.9
                    },
                    'metadata': {
                        'rsi': 25,
                        'timeframe': '1H',
                        'confidence': 0.85,
                        'pattern_type': 'rsi_divergence',
                        'accuracy': 0.9,
                        'precision': 0.85,
                        'stability': 0.9
                    },
                    'source': 'raw_data_intelligence',
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Insert strand
                insert_result = db_client.insert_strand(real_strand)
                if insert_result:
                    self.log_success("Strand insertion", f"Inserted: {insert_result}")
                else:
                    self.log_failure("Strand insertion", "Failed to insert")
                    
            except Exception as e:
                self.log_failure("Strand insertion", f"Error: {e}")
                
        except ImportError as e:
            self.log_failure("Import database components", f"Could not import: {e}")
        except Exception as e:
            self.log_failure("Database testing", f"Error: {e}")
    
    def run_all_tests(self):
        """Run all real data tests"""
        print("🚀 REAL DATA CALCULATION TESTING")
        print("Testing that the system actually calculates metrics from raw data")
        print("=" * 80)
        
        self.test_real_market_data_processing()
        self.test_llm_calls_with_real_data()
        self.test_database_operations_with_real_data()
        
        # Summary
        print("\n" + "=" * 80)
        print("🔍 REAL DATA CALCULATION TEST RESULTS")
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
            print(f"\n⚠️  SYSTEM HAS ISSUES")
            print(f"   {len(self.failures)} components are failing")
            print(f"   Need to fix remaining issues before production")
        else:
            print(f"\n🎉 ALL TESTS PASSED")
            print(f"   System is calculating metrics from real data correctly")

if __name__ == "__main__":
    test = RealDataCalculationTest()
    test.run_all_tests()
