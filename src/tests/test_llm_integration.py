"""
Test LLM Integration Components

Tests for OpenRouter client, prompt management, and basic LLM functionality
"""

import os
import sys
import pytest
import logging
from unittest.mock import Mock, patch
from datetime import datetime, timezone

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.llm_integration.openrouter_client import OpenRouterClient, OpenRouterAPIError
from src.llm_integration.prompt_manager import PromptManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestOpenRouterClient:
    """Test OpenRouter client functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        # Mock environment variables
        self.original_api_key = os.environ.get('OPENROUTER_API_KEY')
        self.original_model = os.environ.get('OPENROUTER_MODEL')
        
        os.environ['OPENROUTER_API_KEY'] = 'test_api_key'
        os.environ['OPENROUTER_MODEL'] = 'anthropic/claude-3.5-sonnet'
    
    def teardown_method(self):
        """Clean up test environment"""
        if self.original_api_key:
            os.environ['OPENROUTER_API_KEY'] = self.original_api_key
        elif 'OPENROUTER_API_KEY' in os.environ:
            del os.environ['OPENROUTER_API_KEY']
            
        if self.original_model:
            os.environ['OPENROUTER_MODEL'] = self.original_model
        elif 'OPENROUTER_MODEL' in os.environ:
            del os.environ['OPENROUTER_MODEL']
    
    def test_client_initialization(self):
        """Test OpenRouter client initialization"""
        client = OpenRouterClient()
        
        assert client.api_key == 'test_api_key'
        assert client.model == 'anthropic/claude-3.5-sonnet'
        assert client.base_url == "https://openrouter.ai/api/v1"
        assert client.max_tokens == 4000
    
    def test_client_initialization_without_api_key(self):
        """Test client initialization fails without API key"""
        del os.environ['OPENROUTER_API_KEY']
        
        with pytest.raises(ValueError, match="OpenRouter API key is required"):
            OpenRouterClient()
    
    @patch('requests.Session.post')
    def test_generate_completion_success(self, mock_post):
        """Test successful completion generation"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Test response from LLM'
                }
            }],
            'usage': {
                'prompt_tokens': 10,
                'completion_tokens': 5,
                'total_tokens': 15
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        client = OpenRouterClient()
        result = client.generate_completion("Test prompt", max_tokens=50)
        
        assert result['content'] == 'Test response from LLM'
        assert result['model'] == 'anthropic/claude-3.5-sonnet'
        assert 'response_time' in result
        assert 'timestamp' in result
    
    @patch('requests.Session.post')
    def test_generate_completion_api_error(self, mock_post):
        """Test API error handling"""
        # Mock API error
        mock_post.side_effect = Exception("API Error")
        
        client = OpenRouterClient()
        
        with pytest.raises(OpenRouterAPIError):
            client.generate_completion("Test prompt")
    
    def test_format_prompt_with_context(self):
        """Test prompt formatting with context"""
        client = OpenRouterClient()
        
        template = "Analyze this signal: {symbol} with confidence {confidence}"
        context = {"symbol": "BTC", "confidence": 0.8}
        
        formatted = client._format_prompt_with_context(template, context)
        
        assert "BTC" in formatted
        assert "0.8" in formatted
    
    def test_format_prompt_missing_key(self):
        """Test prompt formatting with missing key"""
        client = OpenRouterClient()
        
        template = "Analyze this signal: {symbol} with confidence {confidence}"
        context = {"symbol": "BTC"}  # Missing confidence
        
        with pytest.raises(ValueError, match="Template missing required key"):
            client._format_prompt_with_context(template, context)


class TestPromptManager:
    """Test prompt management functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        # Create temporary prompts directory
        self.test_prompts_dir = "test_prompts"
        os.makedirs(self.test_prompts_dir, exist_ok=True)
        
        # Create a test prompt file
        test_prompt_content = """
test_signal_analysis:
  description: "Test signal analysis prompt"
  category: "test"
  latest_version: "v1.0"
  created_at: "2024-01-15T00:00:00Z"
  updated_at: "2024-01-15T00:00:00Z"
  
  versions:
    v1.0:
      prompt: "Analyze signal: {symbol} with confidence {confidence}"
      system_message: "You are a test analyst"
      parameters:
        temperature: 0.7
        max_tokens: 1000
"""
        
        with open(f"{self.test_prompts_dir}/test_prompts.yaml", 'w') as f:
            f.write(test_prompt_content)
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        if os.path.exists(self.test_prompts_dir):
            shutil.rmtree(self.test_prompts_dir)
    
    def test_prompt_manager_initialization(self):
        """Test prompt manager initialization"""
        manager = PromptManager(self.test_prompts_dir)
        
        assert len(manager.prompts) > 0
        assert 'test_signal_analysis' in manager.prompts
    
    def test_get_prompt(self):
        """Test getting a prompt template"""
        manager = PromptManager(self.test_prompts_dir)
        
        prompt = manager.get_prompt('test_signal_analysis')
        
        assert prompt['prompt'] == "Analyze signal: {symbol} with confidence {confidence}"
        assert prompt['system_message'] == "You are a test analyst"
        assert prompt['parameters']['temperature'] == 0.7
    
    def test_get_prompt_text(self):
        """Test getting prompt text"""
        manager = PromptManager(self.test_prompts_dir)
        
        text = manager.get_prompt_text('test_signal_analysis')
        
        assert text == "Analyze signal: {symbol} with confidence {confidence}"
    
    def test_format_prompt(self):
        """Test formatting prompt with context"""
        manager = PromptManager(self.test_prompts_dir)
        
        context = {"symbol": "BTC", "confidence": 0.8}
        formatted = manager.format_prompt('test_signal_analysis', context)
        
        assert "BTC" in formatted
        assert "0.8" in formatted
    
    def test_list_templates(self):
        """Test listing available templates"""
        manager = PromptManager(self.test_prompts_dir)
        
        templates = manager.list_templates()
        
        assert 'test_signal_analysis' in templates
    
    def test_get_template_info(self):
        """Test getting template information"""
        manager = PromptManager(self.test_prompts_dir)
        
        info = manager.get_template_info('test_signal_analysis')
        
        assert info['name'] == 'test_signal_analysis'
        assert info['description'] == "Test signal analysis prompt"
        assert info['category'] == "test"
    
    def test_validate_template(self):
        """Test template validation"""
        manager = PromptManager(self.test_prompts_dir)
        
        # Valid context
        valid_context = {"symbol": "BTC", "confidence": 0.8}
        assert manager.validate_template('test_signal_analysis', valid_context) == True
        
        # Invalid context (missing key)
        invalid_context = {"symbol": "BTC"}
        assert manager.validate_template('test_signal_analysis', invalid_context) == False


class TestLLMIntegration:
    """Test integrated LLM functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        os.environ['OPENROUTER_API_KEY'] = 'test_api_key'
        os.environ['OPENROUTER_MODEL'] = 'anthropic/claude-3.5-sonnet'
    
    def teardown_method(self):
        """Clean up test environment"""
        if 'OPENROUTER_API_KEY' in os.environ:
            del os.environ['OPENROUTER_API_KEY']
        if 'OPENROUTER_MODEL' in os.environ:
            del os.environ['OPENROUTER_MODEL']
    
    @patch('requests.Session.post')
    def test_signal_analysis_integration(self, mock_post):
        """Test integrated signal analysis"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': '{"signal_quality": {"strength_score": 0.8, "confidence_score": 0.7}}'
                }
            }],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150}
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Create client and manager
        client = OpenRouterClient()
        manager = PromptManager("src/llm_integration/prompt_templates")
        
        # Test signal analysis
        signal_data = {
            "symbol": "BTC",
            "direction": "long",
            "confidence": 0.8,
            "strength": 0.7
        }
        
        # This would normally use a real prompt template
        # For testing, we'll use a simple format
        prompt = "Analyze signal: {symbol} {direction} confidence {confidence}"
        formatted_prompt = prompt.format(**signal_data)
        
        result = client.generate_completion(formatted_prompt, max_tokens=100)
        
        assert result['content'] is not None
        assert 'response_time' in result


def test_environment_setup():
    """Test that environment is properly set up for LLM integration"""
    # Check if we can import the modules
    try:
        from src.llm_integration.openrouter_client import OpenRouterClient
        from src.llm_integration.prompt_manager import PromptManager
        print("✅ LLM integration modules imported successfully")
    except ImportError as e:
        pytest.fail(f"Failed to import LLM integration modules: {e}")


if __name__ == "__main__":
    # Run basic tests
    print("🧪 Testing LLM Integration Components...")
    
    # Test environment setup
    test_environment_setup()
    
    # Test prompt manager
    print("\n📝 Testing Prompt Manager...")
    try:
        manager = PromptManager("src/llm_integration/prompt_templates")
        templates = manager.list_templates()
        print(f"✅ Loaded {len(templates)} prompt templates: {templates}")
    except Exception as e:
        print(f"❌ Prompt Manager test failed: {e}")
    
    # Test OpenRouter client (without API call)
    print("\n🔌 Testing OpenRouter Client...")
    try:
        # Set test environment
        os.environ['OPENROUTER_API_KEY'] = 'test_key'
        os.environ['OPENROUTER_MODEL'] = 'anthropic/claude-3.5-sonnet'
        
        client = OpenRouterClient()
        print(f"✅ OpenRouter client initialized with model: {client.model}")
        
        # Test prompt formatting
        template = "Test prompt with {variable}"
        context = {"variable": "test_value"}
        formatted = client._format_prompt_with_context(template, context)
        print(f"✅ Prompt formatting works: {formatted}")
        
    except Exception as e:
        print(f"❌ OpenRouter client test failed: {e}")
    
    print("\n🎉 LLM Integration basic tests completed!")

