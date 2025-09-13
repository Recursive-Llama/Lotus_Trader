#!/usr/bin/env python3
"""
REAL Production Validation Test
Tests the ACTUAL data flow with REAL components - no mocking, no lies
"""

import sys
import os
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import traceback

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

class RealProductionValidator:
    def __init__(self):
        self.failures = []
        self.successes = []
        
    def log_failure(self, component: str, error: str):
        """Log a real failure"""
        self.failures.append(f"{component}: {error}")
        print(f"❌ {component}: {error}")
        
    def log_success(self, component: str, details: str = ""):
        """Log a real success"""
        self.successes.append(f"{component}: {details}")
        print(f"✅ {component}: {details}")
        
    async def test_real_llm_integration(self):
        """Test ACTUAL LLM integration - no mocking"""
        print("\n🧠 TESTING REAL LLM INTEGRATION")
        print("="*50)
        
        try:
            # Test 1: Can we import the actual LLM client?
            print("Testing OpenRouterClient import...")
            try:
                from Modules.Alpha_Detector.src.llm_integration.openrouter_client import OpenRouterClient
                self.log_success("OpenRouterClient import")
            except Exception as e:
                self.log_failure("OpenRouterClient import", str(e))
                return False
                
            # Test 2: Can we initialize it?
            print("Testing OpenRouterClient initialization...")
            try:
                client = OpenRouterClient()
                self.log_success("OpenRouterClient initialization")
            except Exception as e:
                self.log_failure("OpenRouterClient initialization", str(e))
                return False
                
            # Test 3: Can we make a REAL API call?
            print("Testing REAL API call...")
            try:
                # Use the ACTUAL method signature from the code
                response = client.generate_completion(
                    prompt="What is 2+2? Answer in one word.",
                    model="openai/gpt-4o-mini",
                    max_tokens=10
                )
                
                if response and 'content' in response:
                    self.log_success(f"REAL API call", f"Response: {response['content']}")
                else:
                    self.log_failure("REAL API call", "No valid response received")
                    return False
                    
            except Exception as e:
                self.log_failure("REAL API call", str(e))
                return False
                
            return True
            
        except Exception as e:
            self.log_failure("LLM Integration", f"Unexpected error: {e}")
            return False
    
    async def test_real_database_integration(self):
        """Test ACTUAL database integration - no mocking"""
        print("\n🗄️ TESTING REAL DATABASE INTEGRATION")
        print("="*50)
        
        try:
            # Test 1: Can we import the database client?
            print("Testing SupabaseClient import...")
            try:
                from Modules.Alpha_Detector.src.database.supabase_client import SupabaseClient
                self.log_success("SupabaseClient import")
            except Exception as e:
                self.log_failure("SupabaseClient import", str(e))
                return False
                
            # Test 2: Can we initialize it?
            print("Testing SupabaseClient initialization...")
            try:
                db_client = SupabaseClient()
                self.log_success("SupabaseClient initialization")
            except Exception as e:
                self.log_failure("SupabaseClient initialization", str(e))
                return False
                
            # Test 3: Can we make a REAL database call?
            print("Testing REAL database call...")
            try:
                # Try to insert a test strand
                test_strand = {
                    "strand_type": "test",
                    "content": "Test strand for validation",
                    "metadata": {"test": True},
                    "source": "test_validator",
                    "created_at": datetime.now().isoformat()
                }
                
                result = db_client.insert_strand(test_strand)
                
                if result:
                    self.log_success("REAL database insert", f"Strand ID: {result.get('id', 'unknown')}")
                else:
                    self.log_failure("REAL database insert", "No result returned")
                    return False
                    
            except Exception as e:
                self.log_failure("REAL database call", str(e))
                return False
                
            return True
            
        except Exception as e:
            self.log_failure("Database Integration", f"Unexpected error: {e}")
            return False
    
    async def test_real_prompt_system(self):
        """Test ACTUAL prompt system - no mocking"""
        print("\n📝 TESTING REAL PROMPT SYSTEM")
        print("="*50)
        
        try:
            # Test 1: Can we import the prompt manager?
            print("Testing PromptManager import...")
            try:
                from Modules.Alpha_Detector.src.llm_integration.prompt_manager import PromptManager
                self.log_success("PromptManager import")
            except Exception as e:
                self.log_failure("PromptManager import", str(e))
                return False
                
            # Test 2: Can we initialize it?
            print("Testing PromptManager initialization...")
            try:
                prompt_manager = PromptManager()
                self.log_success("PromptManager initialization")
            except Exception as e:
                self.log_failure("PromptManager initialization", str(e))
                return False
                
            # Test 3: Can we get a REAL prompt?
            print("Testing REAL prompt retrieval...")
            try:
                # Use the ACTUAL method name from the code
                prompt_data = prompt_manager.get_prompt("pattern_analysis")
                
                if prompt_data and 'content' in prompt_data:
                    self.log_success("REAL prompt retrieval", f"Found prompt with {len(prompt_data['content'])} characters")
                else:
                    self.log_failure("REAL prompt retrieval", "No valid prompt data")
                    return False
                    
            except Exception as e:
                self.log_failure("REAL prompt retrieval", str(e))
                return False
                
            return True
            
        except Exception as e:
            self.log_failure("Prompt System", f"Unexpected error: {e}")
            return False
    
    async def test_real_complete_data_flow(self):
        """Test the ACTUAL complete data flow - no mocking"""
        print("\n🔄 TESTING REAL COMPLETE DATA FLOW")
        print("="*50)
        
        try:
            # Step 1: Get real market data
            print("Step 1: Getting real market data...")
            try:
                import requests
                response = requests.get("https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT")
                market_data = response.json()
                
                if 'symbol' in market_data:
                    self.log_success("Real market data", f"Got data for {market_data['symbol']}")
                else:
                    self.log_failure("Real market data", "Invalid market data received")
                    return False
                    
            except Exception as e:
                self.log_failure("Real market data", str(e))
                return False
            
            # Step 2: Process into strands
            print("Step 2: Processing into strands...")
            try:
                from src.learning_system.centralized_learning_system import CentralizedLearningSystem
                
                # Create test strands from market data
                strands = [{
                    "strand_type": "pattern",
                    "content": f"Price change: {market_data.get('priceChangePercent', '0')}%",
                    "metadata": {
                        "price_change": float(market_data.get('priceChangePercent', 0)),
                        "volume": float(market_data.get('volume', 0)),
                        "symbol": market_data.get('symbol', 'BTCUSDT')
                    },
                    "source": "binance_api",
                    "created_at": datetime.now().isoformat()
                }]
                
                self.log_success("Strand creation", f"Created {len(strands)} strands")
                
            except Exception as e:
                self.log_failure("Strand creation", str(e))
                return False
            
            # Step 3: Calculate resonance
            print("Step 3: Calculating resonance...")
            try:
                from src.learning_system.mathematical_resonance_engine import MathematicalResonanceEngine
                
                engine = MathematicalResonanceEngine()
                pattern_data = {
                    "accuracy": 0.8,
                    "precision": 0.75,
                    "stability": 0.8
                }
                timeframes = ["1H", "4H", "1D"]
                
                phi = engine.calculate_phi(pattern_data, timeframes)
                
                if 0 <= phi <= 1:
                    self.log_success("Resonance calculation", f"φ = {phi:.3f}")
                else:
                    self.log_failure("Resonance calculation", f"Invalid φ = {phi:.3f}")
                    return False
                    
            except Exception as e:
                self.log_failure("Resonance calculation", str(e))
                return False
            
            # Step 4: Generate LLM insights
            print("Step 4: Generating LLM insights...")
            try:
                from Modules.Alpha_Detector.src.llm_integration.openrouter_client import OpenRouterClient
                from Modules.Alpha_Detector.src.llm_integration.prompt_manager import PromptManager
                
                client = OpenRouterClient()
                prompt_manager = PromptManager()
                
                # Get a real prompt
                prompt_data = prompt_manager.get_prompt("pattern_analysis")
                prompt_text = prompt_data.get('content', '')
                
                # Format with real data
                formatted_prompt = prompt_text.format(strands=strands)
                
                # Make real LLM call
                llm_response = client.generate_completion(
                    prompt=formatted_prompt,
                    model="openai/gpt-4o-mini",
                    max_tokens=200
                )
                
                if llm_response and 'content' in llm_response:
                    self.log_success("LLM insights", f"Generated insights: {llm_response['content'][:100]}...")
                else:
                    self.log_failure("LLM insights", "No valid LLM response")
                    return False
                    
            except Exception as e:
                self.log_failure("LLM insights", str(e))
                return False
            
            # Step 5: Store in database
            print("Step 5: Storing in database...")
            try:
                from Modules.Alpha_Detector.src.database.supabase_client import SupabaseClient
                
                db_client = SupabaseClient()
                
                # Store the strand
                strand_result = db_client.insert_strand(strands[0])
                
                if strand_result:
                    self.log_success("Database storage", f"Stored strand with ID: {strand_result.get('id', 'unknown')}")
                else:
                    self.log_failure("Database storage", "Failed to store strand")
                    return False
                    
            except Exception as e:
                self.log_failure("Database storage", str(e))
                return False
            
            self.log_success("Complete data flow", "All steps completed successfully")
            return True
            
        except Exception as e:
            self.log_failure("Complete data flow", f"Unexpected error: {e}")
            return False
    
    def print_honest_summary(self):
        """Print an honest summary of what actually works"""
        print("\n" + "="*80)
        print("🔍 HONEST PRODUCTION READINESS ASSESSMENT")
        print("="*80)
        
        print(f"\n✅ SUCCESSES ({len(self.successes)}):")
        for success in self.successes:
            print(f"  {success}")
            
        print(f"\n❌ FAILURES ({len(self.failures)}):")
        for failure in self.failures:
            print(f"  {failure}")
        
        print("\n" + "="*80)
        
        if len(self.failures) == 0:
            print("🎉 SYSTEM IS ACTUALLY PRODUCTION READY")
        else:
            print("⚠️  SYSTEM IS NOT PRODUCTION READY")
            print(f"   {len(self.failures)} critical components are failing")
            
        print("="*80)
        
        return len(self.failures) == 0

async def main():
    """Run honest production validation"""
    print("🚀 HONEST PRODUCTION VALIDATION")
    print("Testing ACTUAL components with REAL data - no mocking, no lies")
    print("="*80)
    
    validator = RealProductionValidator()
    
    # Test each component honestly
    tests = [
        ("LLM Integration", validator.test_real_llm_integration),
        ("Database Integration", validator.test_real_database_integration),
        ("Prompt System", validator.test_real_prompt_system),
        ("Complete Data Flow", validator.test_real_complete_data_flow)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Testing {test_name}...")
            await test_func()
        except Exception as e:
            validator.log_failure(test_name, f"Test crashed: {e}")
            traceback.print_exc()
    
    # Print honest results
    is_ready = validator.print_honest_summary()
    
    return is_ready

if __name__ == "__main__":
    asyncio.run(main())
