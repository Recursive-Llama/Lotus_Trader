"""
LLM Client for Learning System

This module provides a unified interface for LLM integration in the learning system.
It supports multiple LLM providers and provides fallback mechanisms.

Features:
1. Multiple LLM provider support (OpenAI, Anthropic, etc.)
2. Fallback mechanisms when LLM is unavailable
3. Response parsing and validation
4. Rate limiting and error handling
"""

import logging
from typing import Dict, List, Any, Optional, Union
from abc import ABC, abstractmethod
import asyncio
import json
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstract base class for LLM clients"""
    
    @abstractmethod
    async def generate_completion(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """Generate completion from LLM"""
        pass
    
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding from text"""
        pass


class OpenAILLMClient(LLMClient):
    """OpenAI LLM client implementation"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize OpenAI client
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o-mini)
        """
        self.api_key = api_key
        self.model = model
        self.logger = logging.getLogger(__name__)
        
        # Import OpenAI client
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=api_key)
        except ImportError:
            self.logger.error("OpenAI library not installed. Install with: pip install openai")
            self.client = None
    
    async def generate_completion(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """Generate completion using OpenAI"""
        try:
            if not self.client:
                raise Exception("OpenAI client not initialized")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert AI assistant helping with market analysis and trading strategy development."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Error generating OpenAI completion: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI"""
        try:
            if not self.client:
                raise Exception("OpenAI client not initialized")
            
            response = await self.client.embeddings.create(
                model="text-embedding-3-large",
                input=text
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            self.logger.error(f"Error generating OpenAI embedding: {e}")
            raise


class AnthropicLLMClient(LLMClient):
    """Anthropic LLM client implementation"""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        """
        Initialize Anthropic client
        
        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-3-haiku-20240307)
        """
        self.api_key = api_key
        self.model = model
        self.logger = logging.getLogger(__name__)
        
        # Import Anthropic client
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError:
            self.logger.error("Anthropic library not installed. Install with: pip install anthropic")
            self.client = None
    
    async def generate_completion(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """Generate completion using Anthropic"""
        try:
            if not self.client:
                raise Exception("Anthropic client not initialized")
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            self.logger.error(f"Error generating Anthropic completion: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Anthropic (not supported, use OpenAI)"""
        raise NotImplementedError("Anthropic does not support embeddings. Use OpenAI for embeddings.")


class MockLLMClient(LLMClient):
    """Mock LLM client for testing and fallback"""
    
    def __init__(self):
        """Initialize mock client"""
        self.logger = logging.getLogger(__name__)
    
    async def generate_completion(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """Generate mock completion"""
        try:
            # Simple mock response based on prompt content
            if "raw data intelligence" in prompt.lower():
                return """
# Raw Data Intelligence Braid Lesson

## Pattern Summary
This braid contains multiple volume spike patterns in BTC 1h timeframe.

## Key Conditions
- High volume spikes (2x+ normal volume)
- Strong price momentum
- Clear trend continuation signals

## Actionable Insights
- Volume spikes often precede significant price moves
- Best performance in trending markets
- Risk management is crucial during high volatility

## Risk Factors
- False breakouts can occur
- Market manipulation possible
- High volatility increases risk

## Confidence Level
High (80%+ based on historical performance)
"""
            elif "trading plan" in prompt.lower():
                return """
# Trading Plan Braid

## Strategy Overview
Consolidated trading strategy based on multiple successful plans.

## Entry Conditions
- Volume spike + price momentum
- Clear trend direction
- Risk/reward ratio > 2:1

## Exit Rules
- Target: 2x risk
- Stop loss: 1x risk
- Time-based exit after 4 hours

## Risk Management
- Maximum 2% position size
- Never risk more than 1% per trade
- Use trailing stops for winners

## Market Conditions
- Best in trending markets
- Avoid during news events
- Monitor for regime changes

## Performance Expectations
- 60% win rate
- 2.5:1 average R/R
- 15% monthly returns target
"""
            else:
                return """
# Universal Braid Lesson

## Pattern Summary
This braid contains multiple market intelligence strands showing consistent patterns.

## Key Insights
- Patterns show high persistence and moderate novelty
- Market conditions favor these strategies
- Risk management is essential

## Recommendations
- Monitor for similar patterns
- Implement with proper risk management
- Update based on market changes

## Confidence Level
Moderate to High based on sample size and consistency
"""
                
        except Exception as e:
            self.logger.error(f"Error generating mock completion: {e}")
            return "Error generating mock completion"
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate mock embedding"""
        # Return a mock embedding vector
        return [0.1] * 1536


class LLMClientManager:
    """Manages multiple LLM clients with fallback"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LLM client manager
        
        Args:
            config: Configuration dictionary with client settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.clients = []
        self.current_client_index = 0
        
        # Initialize clients based on config
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize available LLM clients"""
        try:
            # OpenAI client
            if self.config.get('openai', {}).get('api_key'):
                openai_client = OpenAILLMClient(
                    api_key=self.config['openai']['api_key'],
                    model=self.config['openai'].get('model', 'gpt-4o-mini')
                )
                self.clients.append(openai_client)
                self.logger.info("OpenAI client initialized")
            
            # Anthropic client
            if self.config.get('anthropic', {}).get('api_key'):
                anthropic_client = AnthropicLLMClient(
                    api_key=self.config['anthropic']['api_key'],
                    model=self.config['anthropic'].get('model', 'claude-3-haiku-20240307')
                )
                self.clients.append(anthropic_client)
                self.logger.info("Anthropic client initialized")
            
            # Always add mock client as fallback
            mock_client = MockLLMClient()
            self.clients.append(mock_client)
            self.logger.info("Mock client initialized as fallback")
            
            if len(self.clients) == 1:  # Only mock client
                self.logger.warning("Only mock client available. LLM features will be limited.")
                
        except Exception as e:
            self.logger.error(f"Error initializing LLM clients: {e}")
            # Add mock client as fallback
            self.clients = [MockLLMClient()]
    
    async def generate_completion(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """Generate completion with fallback"""
        for i in range(len(self.clients)):
            try:
                client = self.clients[self.current_client_index]
                result = await client.generate_completion(prompt, max_tokens, temperature)
                self.logger.info(f"Generated completion using client {self.current_client_index}")
                return result
                
            except Exception as e:
                self.logger.warning(f"Client {self.current_client_index} failed: {e}")
                self.current_client_index = (self.current_client_index + 1) % len(self.clients)
                continue
        
        # If all clients fail, return error message
        self.logger.error("All LLM clients failed")
        return "Error: All LLM clients are unavailable"
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding with fallback"""
        for i in range(len(self.clients)):
            try:
                client = self.clients[self.current_client_index]
                result = await client.generate_embedding(text)
                self.logger.info(f"Generated embedding using client {self.current_client_index}")
                return result
                
            except Exception as e:
                self.logger.warning(f"Client {self.current_client_index} failed for embedding: {e}")
                self.current_client_index = (self.current_client_index + 1) % len(self.clients)
                continue
        
        # If all clients fail, return mock embedding
        self.logger.error("All LLM clients failed for embedding")
        return [0.1] * 1536
    
    def get_available_clients(self) -> List[str]:
        """Get list of available client types"""
        return [type(client).__name__ for client in self.clients]


# Example usage and testing
if __name__ == "__main__":
    # Test the LLM client manager
    config = {
        'openai': {
            'api_key': 'test_key',
            'model': 'gpt-4o-mini'
        }
    }
    
    async def test_llm_client():
        manager = LLMClientManager(config)
        
        # Test completion
        prompt = "Analyze these market patterns and create a trading strategy."
        completion = await manager.generate_completion(prompt)
        print(f"Completion: {completion}")
        
        # Test embedding
        embedding = await manager.generate_embedding("test text")
        print(f"Embedding length: {len(embedding)}")
        
        # Test available clients
        clients = manager.get_available_clients()
        print(f"Available clients: {clients}")
    
    import asyncio
    asyncio.run(test_llm_client())
