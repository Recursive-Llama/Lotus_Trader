"""
Agent Discovery System

Discovers agent capabilities and maps them to content types for intelligent routing.
This system enables the Central Intelligence Router to find the most relevant agents
for specific types of content and tasks.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import json
import uuid

from src.utils.supabase_manager import SupabaseManager


@dataclass
class AgentCapability:
    """Represents an agent's capabilities and specializations"""
    agent_name: str
    capabilities: List[str]
    specializations: List[str]
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = 'active'  # 'active', 'inactive', 'error'
    registration_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = '1.0'


@dataclass
class ContentTypeMapping:
    """Maps content types to relevant agent capabilities"""
    content_type: str
    required_capabilities: List[str]
    preferred_capabilities: List[str]
    excluded_capabilities: List[str] = field(default_factory=list)
    priority_agents: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentMatch:
    """Represents a match between content and an agent"""
    agent_name: str
    match_score: float
    matching_capabilities: List[str]
    matching_specializations: List[str]
    reasoning: str
    confidence: float


class AgentDiscoverySystem:
    """
    Discovers agent capabilities and maps them to content types
    
    This system enables intelligent agent discovery by:
    1. Registering agent capabilities and specializations
    2. Mapping content types to required capabilities
    3. Finding the best agents for specific content
    4. Learning from agent performance and routing effectiveness
    5. Maintaining agent status and activity tracking
    """
    
    def __init__(self, supabase_manager: SupabaseManager):
        self.supabase_manager = supabase_manager
        self.agent_capabilities: Dict[str, AgentCapability] = {}
        self.content_type_mappings: Dict[str, ContentTypeMapping] = {}
        self.agent_performance_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize default content type mappings
        self._initialize_default_mappings()
    
    def _initialize_default_mappings(self):
        """Initialize default content type mappings"""
        default_mappings = {
            'pattern_detection': ContentTypeMapping(
                content_type='pattern_detection',
                required_capabilities=['pattern_detection', 'signal_detection'],
                preferred_capabilities=['pattern_analysis', 'technical_analysis'],
                priority_agents=[]
            ),
            'threshold_management': ContentTypeMapping(
                content_type='threshold_management',
                required_capabilities=['threshold_management', 'parameter_control'],
                preferred_capabilities=['system_control', 'optimization'],
                priority_agents=[]
            ),
            'parameter_optimization': ContentTypeMapping(
                content_type='parameter_optimization',
                required_capabilities=['parameter_optimization', 'weight_optimization'],
                preferred_capabilities=['system_control', 'performance_analysis'],
                priority_agents=[]
            ),
            'performance_analysis': ContentTypeMapping(
                content_type='performance_analysis',
                required_capabilities=['performance_analysis', 'learning'],
                preferred_capabilities=['optimization', 'feedback_analysis'],
                priority_agents=[]
            ),
            'learning_opportunity': ContentTypeMapping(
                content_type='learning_opportunity',
                required_capabilities=['learning', 'lesson_generation'],
                preferred_capabilities=['pattern_clustering', 'context_analysis'],
                priority_agents=[]
            ),
            'raw_data_intelligence': ContentTypeMapping(
                content_type='raw_data_intelligence',
                required_capabilities=['raw_data_analysis', 'market_microstructure'],
                preferred_capabilities=['volume_analysis', 'time_based_patterns'],
                priority_agents=[]
            ),
            'indicator_intelligence': ContentTypeMapping(
                content_type='indicator_intelligence',
                required_capabilities=['indicator_analysis', 'divergence_detection'],
                preferred_capabilities=['rsi_analysis', 'macd_analysis', 'bollinger_analysis'],
                priority_agents=[]
            ),
            'system_control': ContentTypeMapping(
                content_type='system_control',
                required_capabilities=['system_control', 'parameter_management'],
                preferred_capabilities=['threshold_control', 'dial_management'],
                priority_agents=[]
            )
        }
        
        self.content_type_mappings.update(default_mappings)
        self.logger.info("Initialized default content type mappings")
    
    async def register_agent_capabilities(self, agent_name: str, capabilities: List[str],
                                  specializations: List[str] = None, version: str = '1.0') -> bool:
        """
        Register an agent's capabilities and specializations
        
        Args:
            agent_name: Name of the agent
            capabilities: List of capabilities (e.g., ['pattern_detection', 'threshold_management'])
            specializations: List of specializations (e.g., ['rsi_analysis', 'macd_patterns'])
            version: Agent version
            
        Returns:
            True if registration successful
        """
        try:
            # Create agent capability record
            agent_capability = AgentCapability(
                agent_name=agent_name,
                capabilities=capabilities or [],
                specializations=specializations or [],
                version=version
            )
            
            # Store in memory
            self.agent_capabilities[agent_name] = agent_capability
            
            # Store in database for persistence
            await self._store_agent_capabilities(agent_capability)
            
            # Update content type mappings with new agent
            self._update_content_type_mappings(agent_name, capabilities, specializations)
            
            self.logger.info(f"Registered agent '{agent_name}' with capabilities: {capabilities}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register agent '{agent_name}': {e}")
            return False
    
    async def _store_agent_capabilities(self, agent_capability: AgentCapability):
        """
        Store agent capabilities in database for persistence
        
        Args:
            agent_capability: Agent capability record to store
        """
        try:
            # Create database record
            capability_record = {
                'agent_name': agent_capability.agent_name,
                'capabilities': json.dumps(agent_capability.capabilities),
                'specializations': json.dumps(agent_capability.specializations),
                'performance_metrics': json.dumps(agent_capability.performance_metrics),
                'status': agent_capability.status,
                'version': agent_capability.version,
                'registration_time': agent_capability.registration_time.isoformat(),
                'last_active': agent_capability.last_active.isoformat()
            }
            
            # Insert or update in database
            result = self.supabase_manager.client.table('agent_capabilities').upsert(
                capability_record, on_conflict='agent_name'
            ).execute()
            
            if not result.data:
                self.logger.error(f"Failed to store capabilities for agent '{agent_capability.agent_name}'")
                
        except Exception as e:
            self.logger.error(f"Failed to store agent capabilities: {e}")
    
    def _update_content_type_mappings(self, agent_name: str, capabilities: List[str],
                                    specializations: List[str]):
        """
        Update content type mappings with new agent information
        
        Args:
            agent_name: Name of the agent
            capabilities: Agent capabilities
            specializations: Agent specializations
        """
        try:
            # Update each content type mapping
            for content_type, mapping in self.content_type_mappings.items():
                # Check if agent has required capabilities
                has_required = any(cap in capabilities for cap in mapping.required_capabilities)
                
                if has_required:
                    # Add to priority agents if not already present
                    if agent_name not in mapping.priority_agents:
                        mapping.priority_agents.append(agent_name)
                        mapping.last_updated = datetime.now(timezone.utc)
                        
        except Exception as e:
            self.logger.error(f"Failed to update content type mappings: {e}")
    
    def find_agents_for_content(self, content_type: str, content_vector: Optional[Any] = None,
                              max_agents: int = 5) -> List[AgentMatch]:
        """
        Find the best agents for specific content type
        
        Args:
            content_type: Type of content to find agents for
            content_vector: Optional vector embedding of content for similarity matching
            max_agents: Maximum number of agents to return
            
        Returns:
            List of agent matches sorted by relevance score
        """
        try:
            # Get content type mapping
            mapping = self.content_type_mappings.get(content_type)
            if not mapping:
                self.logger.warning(f"No mapping found for content type: {content_type}")
                return []
            
            # Find matching agents
            agent_matches = []
            
            for agent_name, capability in self.agent_capabilities.items():
                if capability.status != 'active':
                    continue
                
                # Calculate match score
                match_score, matching_capabilities, matching_specializations = self._calculate_match_score(
                    capability, mapping, content_vector
                )
                
                if match_score > 0.0:
                    # Generate reasoning for the match
                    reasoning = self._generate_match_reasoning(
                        agent_name, capability, mapping, match_score
                    )
                    
                    # Calculate confidence
                    confidence = self._calculate_confidence(
                        capability, match_score, matching_capabilities
                    )
                    
                    agent_match = AgentMatch(
                        agent_name=agent_name,
                        match_score=match_score,
                        matching_capabilities=matching_capabilities,
                        matching_specializations=matching_specializations,
                        reasoning=reasoning,
                        confidence=confidence
                    )
                    
                    agent_matches.append(agent_match)
            
            # Sort by match score and return top agents
            agent_matches.sort(key=lambda x: x.match_score, reverse=True)
            return agent_matches[:max_agents]
            
        except Exception as e:
            self.logger.error(f"Failed to find agents for content type '{content_type}': {e}")
            return []
    
    def _calculate_match_score(self, capability: AgentCapability, mapping: ContentTypeMapping,
                             content_vector: Optional[Any] = None) -> Tuple[float, List[str], List[str]]:
        """
        Calculate match score between agent capability and content type mapping
        
        Args:
            capability: Agent capability information
            mapping: Content type mapping
            content_vector: Optional content vector for similarity matching
            
        Returns:
            Tuple of (match_score, matching_capabilities, matching_specializations)
        """
        match_score = 0.0
        matching_capabilities = []
        matching_specializations = []
        
        # Check required capabilities (high weight)
        required_matches = 0
        for req_cap in mapping.required_capabilities:
            if req_cap in capability.capabilities:
                required_matches += 1
                matching_capabilities.append(req_cap)
                match_score += 0.4  # High weight for required capabilities
        
        # Must have at least one required capability
        if required_matches == 0:
            return 0.0, [], []
        
        # Check preferred capabilities (medium weight)
        for pref_cap in mapping.preferred_capabilities:
            if pref_cap in capability.capabilities:
                matching_capabilities.append(pref_cap)
                match_score += 0.2  # Medium weight for preferred capabilities
        
        # Check specializations (medium weight)
        for spec in capability.specializations:
            if spec in mapping.preferred_capabilities:
                matching_specializations.append(spec)
                match_score += 0.15  # Medium weight for specializations
        
        # Check excluded capabilities (negative weight)
        for excl_cap in mapping.excluded_capabilities:
            if excl_cap in capability.capabilities:
                match_score -= 0.3  # Negative weight for excluded capabilities
        
        # Boost score for priority agents
        if capability.agent_name in mapping.priority_agents:
            match_score += 0.1
        
        # Apply performance metrics boost
        performance_boost = capability.performance_metrics.get('routing_effectiveness', 0.5)
        match_score += performance_boost * 0.1
        
        # Normalize score to 0.0-1.0 range
        match_score = min(1.0, max(0.0, match_score))
        
        return match_score, matching_capabilities, matching_specializations
    
    def _generate_match_reasoning(self, agent_name: str, capability: AgentCapability,
                                mapping: ContentTypeMapping, match_score: float) -> str:
        """
        Generate human-readable reasoning for agent match
        
        Args:
            agent_name: Name of the agent
            capability: Agent capability information
            mapping: Content type mapping
            match_score: Calculated match score
            
        Returns:
            Human-readable reasoning string
        """
        reasoning_parts = []
        
        # Add required capability matches
        required_matches = [cap for cap in mapping.required_capabilities if cap in capability.capabilities]
        if required_matches:
            reasoning_parts.append(f"Has required capabilities: {', '.join(required_matches)}")
        
        # Add preferred capability matches
        preferred_matches = [cap for cap in mapping.preferred_capabilities if cap in capability.capabilities]
        if preferred_matches:
            reasoning_parts.append(f"Has preferred capabilities: {', '.join(preferred_matches)}")
        
        # Add specialization matches
        spec_matches = [spec for spec in capability.specializations if spec in mapping.preferred_capabilities]
        if spec_matches:
            reasoning_parts.append(f"Has relevant specializations: {', '.join(spec_matches)}")
        
        # Add priority agent status
        if agent_name in mapping.priority_agents:
            reasoning_parts.append("Is a priority agent for this content type")
        
        # Add performance information
        performance = capability.performance_metrics.get('routing_effectiveness', 0.5)
        if performance > 0.7:
            reasoning_parts.append("Has high routing effectiveness")
        elif performance < 0.3:
            reasoning_parts.append("Has low routing effectiveness")
        
        return "; ".join(reasoning_parts) if reasoning_parts else "Basic capability match"
    
    def _calculate_confidence(self, capability: AgentCapability, match_score: float,
                            matching_capabilities: List[str]) -> float:
        """
        Calculate confidence in the agent match
        
        Args:
            capability: Agent capability information
            match_score: Calculated match score
            matching_capabilities: List of matching capabilities
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = match_score  # Start with match score
        
        # Boost confidence for agents with more matching capabilities
        capability_boost = min(0.2, len(matching_capabilities) * 0.05)
        confidence += capability_boost
        
        # Boost confidence for active agents
        if capability.status == 'active':
            confidence += 0.1
        
        # Apply performance metrics
        performance = capability.performance_metrics.get('routing_effectiveness', 0.5)
        confidence += (performance - 0.5) * 0.2
        
        # Normalize to 0.0-1.0 range
        return min(1.0, max(0.0, confidence))
    
    async def update_agent_performance(self, agent_name: str, performance_data: Dict[str, Any]):
        """
        Update agent performance metrics based on routing results
        
        Args:
            agent_name: Name of the agent
            performance_data: Performance data to update
        """
        try:
            if agent_name not in self.agent_capabilities:
                self.logger.warning(f"Agent '{agent_name}' not found for performance update")
                return
            
            # Update performance metrics
            capability = self.agent_capabilities[agent_name]
            
            # Update existing metrics
            for metric, value in performance_data.items():
                if metric in capability.performance_metrics:
                    # Use exponential moving average for continuous metrics
                    alpha = 0.1  # Smoothing factor
                    capability.performance_metrics[metric] = (
                        alpha * value + (1 - alpha) * capability.performance_metrics[metric]
                    )
                else:
                    capability.performance_metrics[metric] = value
            
            # Update last active time
            capability.last_active = datetime.now(timezone.utc)
            
            # Store updated performance in database
            await self._store_agent_capabilities(capability)
            
            # Store performance history
            if agent_name not in self.agent_performance_history:
                self.agent_performance_history[agent_name] = []
            
            performance_record = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'performance_data': performance_data,
                'updated_metrics': capability.performance_metrics
            }
            
            self.agent_performance_history[agent_name].append(performance_record)
            
            # Keep only last 100 performance records
            if len(self.agent_performance_history[agent_name]) > 100:
                self.agent_performance_history[agent_name] = self.agent_performance_history[agent_name][-100:]
            
            self.logger.info(f"Updated performance for agent '{agent_name}': {performance_data}")
            
        except Exception as e:
            self.logger.error(f"Failed to update agent performance: {e}")
    
    def get_agent_status(self) -> Dict[str, Any]:
        """
        Get status of all registered agents
        
        Returns:
            Dictionary of agent status information
        """
        return {
            agent_name: {
                'capabilities': capability.capabilities,
                'specializations': capability.specializations,
                'status': capability.status,
                'last_active': capability.last_active.isoformat(),
                'performance_metrics': capability.performance_metrics,
                'version': capability.version
            }
            for agent_name, capability in self.agent_capabilities.items()
        }
    
    def get_content_type_mappings(self) -> Dict[str, Any]:
        """
        Get all content type mappings
        
        Returns:
            Dictionary of content type mappings
        """
        return {
            content_type: {
                'required_capabilities': mapping.required_capabilities,
                'preferred_capabilities': mapping.preferred_capabilities,
                'excluded_capabilities': mapping.excluded_capabilities,
                'priority_agents': mapping.priority_agents,
                'last_updated': mapping.last_updated.isoformat()
            }
            for content_type, mapping in self.content_type_mappings.items()
        }
    
    def get_discovery_stats(self) -> Dict[str, Any]:
        """
        Get discovery system statistics
        
        Returns:
            Dictionary of discovery statistics
        """
        active_agents = len([a for a in self.agent_capabilities.values() if a.status == 'active'])
        total_agents = len(self.agent_capabilities)
        
        return {
            'total_agents': total_agents,
            'active_agents': active_agents,
            'inactive_agents': total_agents - active_agents,
            'content_types': len(self.content_type_mappings),
            'total_capabilities': sum(len(a.capabilities) for a in self.agent_capabilities.values()),
            'total_specializations': sum(len(a.specializations) for a in self.agent_capabilities.values()),
            'performance_records': sum(len(records) for records in self.agent_performance_history.values())
        }
