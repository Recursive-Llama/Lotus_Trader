"""
LLM Integration Module for Alpha Detector

This module provides LLM integration capabilities including:
- OpenRouter API client
- Prompt management system
- Context management
- Information injection
- Learning management
"""

from .openrouter_client import OpenRouterClient
from .prompt_manager import PromptManager
from .context_indexer import ContextIndexer
from .pattern_clusterer import PatternClusterer
from .database_driven_context_system import DatabaseDrivenContextSystem

# LLM Services Management
from .llm_services_manager import LLMServicesManager
from .service_registry import ServiceRegistry
from .llm_management_interface import LLMManagementInterface

# Central Intelligence Router & Agent Communication
from .central_intelligence_router import CentralIntelligenceRouter, RoutingDecision, AgentCapability
from .agent_communication_protocol import AgentCommunicationProtocol, StrandMessage, AgentResponse
from .agent_discovery_system import AgentDiscoverySystem, ContentTypeMapping, AgentMatch
from .tag_conventions import TagConventionSystem, TagType, Priority, MessageType

# Note: Context management will be implemented in Phase 1A Day 3
# from .context_manager import ContextManager

__all__ = [
    'OpenRouterClient',
    'PromptManager',
    'ContextIndexer',
    'PatternClusterer',
    'DatabaseDrivenContextSystem',
    'LLMServicesManager',
    'ServiceRegistry',
    'LLMManagementInterface',
    'CentralIntelligenceRouter',
    'RoutingDecision',
    'AgentCapability',
    'AgentCommunicationProtocol',
    'StrandMessage',
    'AgentResponse',
    'AgentDiscoverySystem',
    'ContentTypeMapping',
    'AgentMatch',
    'TagConventionSystem',
    'TagType',
    'Priority',
    'MessageType'
    # 'ContextManager'
]
