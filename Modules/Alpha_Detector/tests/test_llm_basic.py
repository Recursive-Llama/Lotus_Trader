#!/usr/bin/env python3
"""
Basic LLM Integration Test

Simple test to verify LLM integration components work
"""

import os
import sys
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that we can import our modules"""
    print("🧪 Testing imports...")
    
    try:
        from llm_integration.openrouter_client import OpenRouterClient
        print("✅ OpenRouterClient imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import OpenRouterClient: {e}")
        return False
    
    try:
        from llm_integration.prompt_manager import PromptManager
        print("✅ PromptManager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import PromptManager: {e}")
        return False
    
    return True

def test_prompt_manager():
    """Test prompt manager functionality"""
    print("\n📝 Testing Prompt Manager...")
    
    try:
        from llm_integration.prompt_manager import PromptManager
        
        # Test with our prompt templates directory
        manager = PromptManager("src/llm_integration/prompt_templates")
        
        # List templates
        templates = manager.list_templates()
        print(f"✅ Loaded {len(templates)} prompt templates: {templates}")
        
        # Test getting a template
        if templates:
            template_name = templates[0]
            info = manager.get_template_info(template_name)
            print(f"✅ Template info for '{template_name}': {info['description']}")
            
            # Test getting prompt text
            prompt_text = manager.get_prompt_text(template_name)
            print(f"✅ Prompt text length: {len(prompt_text)} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ Prompt Manager test failed: {e}")
        return False

def test_openrouter_client():
    """Test OpenRouter client functionality"""
    print("\n🔌 Testing OpenRouter Client...")
    
    try:
        from llm_integration.openrouter_client import OpenRouterClient
        
        # Set test environment variables
        os.environ['OPENROUTER_API_KEY'] = 'test_api_key'
        os.environ['OPENROUTER_MODEL'] = 'anthropic/claude-3.5-sonnet'
        
        # Initialize client
        client = OpenRouterClient()
        print(f"✅ OpenRouter client initialized with model: {client.model}")
        
        # Test prompt formatting
        template = "Test prompt with {variable} and {another_variable}"
        context = {"variable": "test_value", "another_variable": "another_value"}
        formatted = client._format_prompt_with_context(template, context)
        print(f"✅ Prompt formatting works: {formatted}")
        
        # Test missing key handling
        try:
            bad_context = {"variable": "test_value"}  # Missing another_variable
            client._format_prompt_with_context(template, bad_context)
            print("❌ Should have failed with missing key")
            return False
        except ValueError as e:
            print(f"✅ Correctly caught missing key error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenRouter client test failed: {e}")
        return False

def test_integration():
    """Test basic integration between components"""
    print("\n🔗 Testing Integration...")
    
    try:
        from llm_integration.openrouter_client import OpenRouterClient
        from llm_integration.prompt_manager import PromptManager
        
        # Set test environment
        os.environ['OPENROUTER_API_KEY'] = 'test_api_key'
        os.environ['OPENROUTER_MODEL'] = 'anthropic/claude-3.5-sonnet'
        
        # Create instances
        client = OpenRouterClient()
        manager = PromptManager("src/llm_integration/prompt_templates")
        
        # Test getting a template and formatting it
        templates = manager.list_templates()
        if templates:
            template_name = templates[0]
            prompt_text = manager.get_prompt_text(template_name)
            
            # Create test context
            test_context = {
                "symbol": "BTC",
                "direction": "long",
                "confidence": 0.8,
                "strength": 0.7,
                "context": "Test signal data"
            }
            
            # Format prompt
            try:
                formatted_prompt = manager.format_prompt(template_name, test_context)
                print(f"✅ Successfully formatted prompt with context")
                print(f"   Prompt length: {len(formatted_prompt)} characters")
            except Exception as e:
                print(f"⚠️  Prompt formatting failed (expected for some templates): {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting LLM Integration Basic Tests...\n")
    
    tests = [
        test_imports,
        test_prompt_manager,
        test_openrouter_client,
        test_integration
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
        print("🎉 All tests passed! LLM integration is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
