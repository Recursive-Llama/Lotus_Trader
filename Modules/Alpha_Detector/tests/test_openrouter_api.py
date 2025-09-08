#!/usr/bin/env python3
"""
Test OpenRouter API Connection

Test the actual OpenRouter API with real credentials
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables from .env file
def load_env_file(env_path):
    """Load environment variables from .env file"""
    if not os.path.exists(env_path):
        print(f"❌ .env file not found at {env_path}")
        return False
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
    
    return True

def test_openrouter_api():
    """Test OpenRouter API connection"""
    print("🔌 Testing OpenRouter API Connection...")
    
    try:
        from llm_integration.openrouter_client import OpenRouterClient
        
        # Initialize client
        client = OpenRouterClient()
        print(f"✅ Client initialized with model: {client.model}")
        
        # Test connection
        print("Testing API connection...")
        if client.test_connection():
            print("✅ OpenRouter API connection successful!")
            
            # Test a simple completion
            print("Testing simple completion...")
            result = client.generate_completion(
                "What is 2+2? Answer in one word.",
                max_tokens=10,
                temperature=0.1
            )
            print(f"✅ Test completion: {result['content']}")
            print(f"   Response time: {result['response_time']:.2f}s")
            print(f"   Tokens used: {result['usage']}")
            
            return True
        else:
            print("❌ OpenRouter API connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing OpenRouter API: {e}")
        return False

def test_signal_analysis():
    """Test signal analysis with LLM"""
    print("\n📊 Testing Signal Analysis with LLM...")
    
    try:
        from llm_integration.openrouter_client import OpenRouterClient
        from llm_integration.prompt_manager import PromptManager
        
        # Initialize components
        client = OpenRouterClient()
        manager = PromptManager("src/llm_integration/prompt_templates")
        
        # Get signal analysis template
        prompt_text = manager.get_prompt_text('signal_analysis')
        system_message = manager.get_system_message('signal_analysis')
        
        # Create test signal data
        signal_data = {
            "symbol": "BTC",
            "direction": "long",
            "confidence": 0.8,
            "strength": 0.7,
            "timeframe": "1h",
            "regime": "trending_up",
            "patterns": ["breakout", "volume_spike"],
            "features": {
                "rsi": 65,
                "macd_bullish": True,
                "volume_ratio": 1.5
            }
        }
        
        # Format prompt
        formatted_prompt = prompt_text.format(context=str(signal_data))
        
        print("Generating signal analysis...")
        result = client.generate_completion(
            prompt=formatted_prompt,
            system_message=system_message,
            max_tokens=1000,
            temperature=0.3
        )
        
        print(f"✅ Signal analysis generated:")
        print(f"   Response time: {result['response_time']:.2f}s")
        print(f"   Content length: {len(result['content'])} characters")
        print(f"   First 200 chars: {result['content'][:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing signal analysis: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing OpenRouter API Integration...\n")
    
    # Load environment variables
    env_path = Path(__file__).parent.parent.parent / ".env"
    if not load_env_file(env_path):
        print("❌ Failed to load environment variables")
        return False
    
    print(f"✅ Loaded environment variables from {env_path}")
    
    # Run tests
    tests = [
        test_openrouter_api,
        test_signal_analysis
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All OpenRouter API tests passed!")
        return True
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
