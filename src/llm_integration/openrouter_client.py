"""
OpenRouter API Client for LLM Integration

Provides a robust client for interacting with OpenRouter API
with error handling, retry logic, and response validation.
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """
    OpenRouter API client with robust error handling and retry logic
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize OpenRouter client
        
        Args:
            api_key: OpenRouter API key (defaults to env var)
            model: Default model to use (defaults to env var)
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.model = model or os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3.5-sonnet')
        self.max_tokens = int(os.getenv('OPENROUTER_MAX_TOKENS', '4000'))
        self.base_url = "https://openrouter.ai/api/v1"
        
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable.")
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set headers
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://lotus-trader.ai",
            "X-Title": "Lotus Trader Alpha Detector"
        })
        
        logger.info(f"OpenRouter client initialized with model: {self.model}")
    
    def generate_completion(self, 
                          prompt: str, 
                          model: Optional[str] = None,
                          max_tokens: Optional[int] = None,
                          temperature: float = 0.7,
                          system_message: Optional[str] = None,
                          **kwargs) -> Dict[str, Any]:
        """
        Generate completion using OpenRouter API
        
        Args:
            prompt: The prompt to send to the model
            model: Model to use (defaults to instance model)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            system_message: Optional system message
            **kwargs: Additional parameters for the API call
            
        Returns:
            Dict containing the response and metadata
        """
        
        model = model or self.model
        max_tokens = max_tokens or self.max_tokens
        
        # Prepare messages
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare request payload
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        try:
            logger.debug(f"Sending request to OpenRouter API with model: {model}")
            start_time = time.time()
            
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=30
            )
            
            response_time = time.time() - start_time
            logger.debug(f"OpenRouter API response time: {response_time:.2f}s")
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            
            # Validate response structure
            if 'choices' not in result or not result['choices']:
                raise ValueError("Invalid response structure from OpenRouter API")
            
            choice = result['choices'][0]
            if 'message' not in choice or 'content' not in choice['message']:
                raise ValueError("Invalid message structure in OpenRouter response")
            
            # Extract content
            content = choice['message']['content']
            
            # Prepare result
            result_data = {
                'content': content,
                'model': model,
                'usage': result.get('usage', {}),
                'response_time': response_time,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'raw_response': result
            }
            
            logger.info(f"Successfully generated completion with {model} ({response_time:.2f}s)")
            return result_data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error in OpenRouter API call: {e}")
            raise OpenRouterAPIError(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in OpenRouter response: {e}")
            raise OpenRouterAPIError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in OpenRouter API call: {e}")
            raise OpenRouterAPIError(f"Unexpected error: {e}")
    
    async def generate_async(self, prompt: str, system_message: Optional[str] = None, image: Optional[bytes] = None, **kwargs) -> str:
        """
        Async wrapper for generate_completion
        
        Args:
            prompt: The prompt to send to the model
            system_message: Optional system message
            image: Optional image data (not supported in current implementation)
            **kwargs: Additional parameters
            
        Returns:
            The generated content as a string
        """
        try:
            result = self.generate_completion(
                prompt=prompt,
                system_message=system_message,
                **kwargs
            )
            return result['content']
        except Exception as e:
            logger.error(f"Error in generate_async: {e}")
            raise
    
    def generate_lesson(self, context: Dict[str, Any], prompt_template: str) -> Dict[str, Any]:
        """
        Generate a lesson from context using a prompt template
        
        Args:
            context: Context data for lesson generation
            prompt_template: Prompt template to use
            
        Returns:
            Generated lesson with metadata
        """
        
        try:
            # Format prompt with context
            formatted_prompt = self._format_prompt_with_context(prompt_template, context)
            
            # Generate completion
            result = self.generate_completion(
                prompt=formatted_prompt,
                temperature=0.3,  # Lower temperature for more consistent lessons
                max_tokens=2000
            )
            
            # Parse lesson content
            lesson_content = result['content']
            
            # Try to parse as JSON if it looks like JSON
            try:
                if lesson_content.strip().startswith('{'):
                    lesson_data = json.loads(lesson_content)
                else:
                    lesson_data = {'content': lesson_content}
            except json.JSONDecodeError:
                lesson_data = {'content': lesson_content}
            
            return {
                'lesson': lesson_data,
                'metadata': {
                    'model': result['model'],
                    'response_time': result['response_time'],
                    'timestamp': result['timestamp'],
                    'context_keys': list(context.keys())
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating lesson: {e}")
            raise OpenRouterAPIError(f"Lesson generation failed: {e}")
    
    def generate_signal_analysis(self, signal_data: Dict[str, Any], prompt_template: str) -> Dict[str, Any]:
        """
        Generate signal analysis using LLM
        
        Args:
            signal_data: Signal data to analyze
            prompt_template: Prompt template for analysis
            
        Returns:
            Analysis result with metadata
        """
        
        try:
            # Format prompt with signal data
            formatted_prompt = self._format_prompt_with_context(prompt_template, signal_data)
            
            # Generate completion
            result = self.generate_completion(
                prompt=formatted_prompt,
                temperature=0.5,  # Balanced temperature for analysis
                max_tokens=1500
            )
            
            # Parse analysis content
            analysis_content = result['content']
            
            return {
                'analysis': analysis_content,
                'metadata': {
                    'model': result['model'],
                    'response_time': result['response_time'],
                    'timestamp': result['timestamp'],
                    'signal_keys': list(signal_data.keys())
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating signal analysis: {e}")
            raise OpenRouterAPIError(f"Signal analysis generation failed: {e}")
    
    def _format_prompt_with_context(self, template: str, context: Dict[str, Any]) -> str:
        """
        Format prompt template with context data
        
        Args:
            template: Prompt template string
            context: Context data to inject
            
        Returns:
            Formatted prompt string
        """
        
        try:
            # Convert context to JSON string for injection
            context_json = json.dumps(context, indent=2, default=str)
            
            # Replace placeholders in template
            formatted_prompt = template.format(
                context=context_json,
                **context  # Also allow direct key access
            )
            
            return formatted_prompt
            
        except KeyError as e:
            logger.error(f"Missing key in prompt template: {e}")
            raise ValueError(f"Template missing required key: {e}")
        except Exception as e:
            logger.error(f"Error formatting prompt: {e}")
            raise ValueError(f"Prompt formatting failed: {e}")
    
    def test_connection(self) -> bool:
        """
        Test connection to OpenRouter API
        
        Returns:
            True if connection successful, False otherwise
        """
        
        try:
            result = self.generate_completion(
                prompt="Hello, this is a test message.",
                max_tokens=10,
                temperature=0.1
            )
            
            logger.info("OpenRouter API connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"OpenRouter API connection test failed: {e}")
            return False
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Get list of available models from OpenRouter
        
        Returns:
            List of available models
        """
        
        try:
            response = self.session.get(f"{self.base_url}/models", timeout=10)
            response.raise_for_status()
            
            result = response.json()
            return result.get('data', [])
            
        except Exception as e:
            logger.error(f"Error fetching available models: {e}")
            return []


class OpenRouterAPIError(Exception):
    """Custom exception for OpenRouter API errors"""
    pass


# Example usage and testing
if __name__ == "__main__":
    # Test the client
    try:
        client = OpenRouterClient()
        
        # Test connection
        if client.test_connection():
            print("✅ OpenRouter client connection successful")
        else:
            print("❌ OpenRouter client connection failed")
        
        # Test completion
        result = client.generate_completion(
            prompt="What is the capital of France?",
            max_tokens=50
        )
        print(f"Test completion: {result['content']}")
        
    except Exception as e:
        print(f"❌ Error testing OpenRouter client: {e}")
