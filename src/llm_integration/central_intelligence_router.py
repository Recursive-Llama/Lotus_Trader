"""
Central Intelligence Router

The "conductor" of the LLM agent orchestra. Monitors all strands in the AD_strands table,
uses vector search to find relevant connections, and routes information intelligently
between agents through the database.

This component enables database-centric agent communication without requiring
separate communication infrastructure.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json
import uuid

from src.utils.supabase_manager import SupabaseManager
from .database_driven_context_system import DatabaseDrivenContextSystem
from .context_indexer import ContextIndexer
from .pattern_clusterer import PatternClusterer


@dataclass
class RoutingDecision:
    """Represents a routing decision made by the Central Intelligence Router"""
    target_agent: str
    source_strand_id: str
    routing_reason: str
    similarity_score: float
    confidence: float
    tags: str
    content: Dict[str, Any]
    timestamp: datetime


@dataclass
class AgentCapability:
    """Represents an agent's capabilities and specializations"""
    agent_name: str
    capabilities: List[str]
    specializations: List[str]
    performance_metrics: Dict[str, float]
    last_active: datetime
    status: str  # 'active', 'inactive', 'error'


class CentralIntelligenceRouter:
    """
    The "conductor" of the LLM agent orchestra.
    
    Monitors all strands in AD_strands table, uses vector search to find relevant
    connections, and routes information intelligently between agents through the database.
    """
    
    def __init__(self, supabase_manager: SupabaseManager, context_system: DatabaseDrivenContextSystem):
        self.supabase_manager = supabase_manager
        self.context_system = context_system
        self.agent_capabilities: Dict[str, AgentCapability] = {}
        self.routing_history: List[RoutingDecision] = []
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self.routing_stats = {
            'total_routes': 0,
            'successful_routes': 0,
            'failed_routes': 0,
            'average_similarity_score': 0.0,
            'average_confidence': 0.0
        }
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
    def register_agent_capabilities(self, agent_name: str, capabilities: List[str], 
                                  specializations: List[str] = None) -> bool:
        """
        Register an agent's capabilities and specializations
        
        Args:
            agent_name: Name of the agent
            capabilities: List of capabilities (e.g., ['pattern_detection', 'threshold_management'])
            specializations: List of specializations (e.g., ['rsi_analysis', 'macd_patterns'])
            
        Returns:
            True if registration successful
        """
        try:
            self.agent_capabilities[agent_name] = AgentCapability(
                agent_name=agent_name,
                capabilities=capabilities or [],
                specializations=specializations or [],
                performance_metrics={},
                last_active=datetime.now(timezone.utc),
                status='active'
            )
            
            self.logger.info(f"Registered agent '{agent_name}' with capabilities: {capabilities}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register agent '{agent_name}': {e}")
            return False
    
    def start_monitoring(self) -> bool:
        """
        Start monitoring AD_strands table for new entries
        
        Returns:
            True if monitoring started successfully
        """
        try:
            if self.is_monitoring:
                self.logger.warning("Monitoring already active")
                return True
                
            self.is_monitoring = True
            self.monitoring_task = asyncio.create_task(self._monitor_strands())
            
            self.logger.info("Central Intelligence Router monitoring started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
            self.is_monitoring = False
            return False
    
    def stop_monitoring(self) -> bool:
        """
        Stop monitoring AD_strands table
        
        Returns:
            True if monitoring stopped successfully
        """
        try:
            if not self.is_monitoring:
                self.logger.warning("Monitoring not active")
                return True
                
            self.is_monitoring = False
            
            if self.monitoring_task:
                self.monitoring_task.cancel()
                self.monitoring_task = None
            
            self.logger.info("Central Intelligence Router monitoring stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop monitoring: {e}")
            return False
    
    async def _monitor_strands(self):
        """
        Continuously monitor AD_strands for new entries and route them
        """
        self.logger.info("Starting strand monitoring loop")
        
        while self.is_monitoring:
            try:
                # Get recent strands (last 5 minutes)
                recent_strands = await self._get_recent_strands()
                
                for strand in recent_strands:
                    # Check if this strand needs routing
                    if self._needs_routing(strand):
                        await self._route_strand(strand)
                
                # Update agent status
                await self._update_agent_status()
                
                # Sleep for 30 seconds before next check
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                self.logger.info("Strand monitoring cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in strand monitoring: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _get_recent_strands(self) -> List[Dict[str, Any]]:
        """
        Get recent strands from AD_strands table
        
        Returns:
            List of recent strand records
        """
        try:
            # Get strands from last 5 minutes
            five_minutes_ago = datetime.now(timezone.utc).timestamp() - 300
            
            result = self.supabase_manager.client.table('AD_strands').select('*').gte(
                'created_at', five_minutes_ago
            ).order('created_at', desc=True).limit(100).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            self.logger.error(f"Failed to get recent strands: {e}")
            return []
    
    def _needs_routing(self, strand: Dict[str, Any]) -> bool:
        """
        Determine if a strand needs routing to other agents
        
        Args:
            strand: Strand record from database
            
        Returns:
            True if strand needs routing
        """
        # Don't route strands that are already routed
        if 'routed_from' in str(strand.get('tags', '')):
            return False
            
        # Don't route strands from the central router itself
        if strand.get('source_agent') == 'central_router':
            return False
            
        # Route strands that contain actionable information
        content = strand.get('content', {})
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except:
                content = {'text': content}
        
        # Check for routing indicators
        routing_indicators = [
            'pattern_detected', 'threshold_analysis', 'parameter_update',
            'escalation_required', 'learning_opportunity', 'performance_alert'
        ]
        
        tags = str(strand.get('tags', '')).lower()
        for indicator in routing_indicators:
            if indicator in tags:
                return True
                
        return False
    
    async def _route_strand(self, source_strand: Dict[str, Any]) -> List[RoutingDecision]:
        """
        Route a strand to relevant agents using vector search
        
        Args:
            source_strand: Source strand to route
            
        Returns:
            List of routing decisions made
        """
        try:
            # Create context vector for the source strand
            strand_context = self._prepare_strand_context(source_strand)
            strand_vector = self.context_system.context_indexer.create_context_vector(strand_context)
            
            # Find similar historical patterns using vector search
            similar_patterns = await self._find_similar_patterns(strand_vector)
            
            # Determine which agents need this information
            relevant_agents = self._find_relevant_agents(source_strand, similar_patterns)
            
            # Create routing decisions
            routing_decisions = []
            for agent_info in relevant_agents:
                decision = await self._create_routing_decision(
                    source_strand, agent_info, similar_patterns
                )
                if decision:
                    routing_decisions.append(decision)
                    await self._execute_routing_decision(decision)
            
            # Update routing statistics
            self._update_routing_stats(routing_decisions)
            
            return routing_decisions
            
        except Exception as e:
            self.logger.error(f"Failed to route strand {source_strand.get('id')}: {e}")
            return []
    
    def _prepare_strand_context(self, strand: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare strand data for context vector creation
        
        Args:
            strand: Strand record from database
            
        Returns:
            Prepared context dictionary
        """
        content = strand.get('content', {})
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except:
                content = {'text': content}
        
        return {
            'strand_id': strand.get('id'),
            'content': content,
            'tags': strand.get('tags', ''),
            'source_agent': strand.get('source_agent', ''),
            'created_at': strand.get('created_at'),
            'strand_type': self._classify_strand_type(strand)
        }
    
    def _classify_strand_type(self, strand: Dict[str, Any]) -> str:
        """
        Classify the type of strand for routing purposes
        
        Args:
            strand: Strand record from database
            
        Returns:
            Strand type classification
        """
        tags = str(strand.get('tags', '')).lower()
        content = str(strand.get('content', '')).lower()
        
        if 'pattern' in tags or 'pattern' in content:
            return 'pattern_detection'
        elif 'threshold' in tags or 'threshold' in content:
            return 'threshold_management'
        elif 'parameter' in tags or 'parameter' in content:
            return 'parameter_optimization'
        elif 'performance' in tags or 'performance' in content:
            return 'performance_analysis'
        elif 'learning' in tags or 'learning' in content:
            return 'learning_opportunity'
        else:
            return 'general_information'
    
    async def _find_similar_patterns(self, strand_vector) -> List[Dict[str, Any]]:
        """
        Find similar historical patterns using vector search
        
        Args:
            strand_vector: Vector embedding of the strand
            
        Returns:
            List of similar patterns with similarity scores
        """
        try:
            # Use the context system to find similar patterns
            similar_contexts = self.context_system.get_relevant_context({
                'vector': strand_vector,
                'search_type': 'similarity_search'
            })
            
            return similar_contexts.get('similar_situations', [])
            
        except Exception as e:
            self.logger.error(f"Failed to find similar patterns: {e}")
            return []
    
    def _find_relevant_agents(self, source_strand: Dict[str, Any], 
                            similar_patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find agents that should receive this strand based on content and patterns
        
        Args:
            source_strand: Source strand to route
            similar_patterns: Similar historical patterns
            
        Returns:
            List of relevant agents with routing information
        """
        relevant_agents = []
        strand_type = self._classify_strand_type(source_strand)
        
        # Find agents based on strand type and capabilities
        for agent_name, capability in self.agent_capabilities.items():
            if capability.status != 'active':
                continue
                
            # Check if agent has relevant capabilities
            relevance_score = self._calculate_agent_relevance(
                agent_name, capability, strand_type, similar_patterns
            )
            
            if relevance_score > 0.3:  # Threshold for relevance
                relevant_agents.append({
                    'agent_name': agent_name,
                    'capability': capability,
                    'relevance_score': relevance_score,
                    'routing_reason': self._determine_routing_reason(
                        agent_name, capability, strand_type
                    )
                })
        
        # Sort by relevance score
        relevant_agents.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return relevant_agents[:5]  # Limit to top 5 most relevant agents
    
    def _calculate_agent_relevance(self, agent_name: str, capability: AgentCapability,
                                 strand_type: str, similar_patterns: List[Dict[str, Any]]) -> float:
        """
        Calculate how relevant an agent is for a given strand
        
        Args:
            agent_name: Name of the agent
            capability: Agent capability information
            strand_type: Type of strand being routed
            similar_patterns: Similar historical patterns
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        relevance_score = 0.0
        
        # Base relevance from capabilities
        capability_mapping = {
            'pattern_detection': ['pattern_detection', 'pattern_analysis', 'signal_detection'],
            'threshold_management': ['threshold_management', 'parameter_control', 'system_control'],
            'parameter_optimization': ['parameter_optimization', 'weight_optimization', 'system_control'],
            'performance_analysis': ['performance_analysis', 'learning', 'optimization'],
            'learning_opportunity': ['learning', 'lesson_generation', 'pattern_clustering'],
            'general_information': ['general_analysis', 'context_analysis']
        }
        
        relevant_capabilities = capability_mapping.get(strand_type, [])
        for cap in relevant_capabilities:
            if cap in capability.capabilities:
                relevance_score += 0.3
        
        # Boost relevance based on specializations
        for specialization in capability.specializations:
            if specialization in str(similar_patterns):
                relevance_score += 0.2
        
        # Boost relevance based on recent performance
        performance_score = capability.performance_metrics.get('routing_effectiveness', 0.5)
        relevance_score += performance_score * 0.2
        
        # Ensure score is between 0.0 and 1.0
        return min(1.0, max(0.0, relevance_score))
    
    def _determine_routing_reason(self, agent_name: str, capability: AgentCapability,
                                strand_type: str) -> str:
        """
        Determine the reason for routing to a specific agent
        
        Args:
            agent_name: Name of the agent
            capability: Agent capability information
            strand_type: Type of strand being routed
            
        Returns:
            Human-readable routing reason
        """
        if strand_type in capability.capabilities:
            return f"Agent specializes in {strand_type}"
        elif any(spec in capability.specializations for spec in ['rsi', 'macd', 'bollinger']):
            return f"Agent has technical indicator expertise"
        elif 'learning' in capability.capabilities:
            return f"Agent handles learning opportunities"
        else:
            return f"Agent has general analysis capabilities"
    
    async def _create_routing_decision(self, source_strand: Dict[str, Any],
                                     agent_info: Dict[str, Any],
                                     similar_patterns: List[Dict[str, Any]]) -> Optional[RoutingDecision]:
        """
        Create a routing decision for a specific agent
        
        Args:
            source_strand: Source strand to route
            agent_info: Information about the target agent
            similar_patterns: Similar historical patterns
            
        Returns:
            Routing decision or None if routing should not occur
        """
        try:
            # Calculate confidence based on similarity and agent relevance
            avg_similarity = sum(p.get('similarity', 0.0) for p in similar_patterns) / max(1, len(similar_patterns))
            confidence = (avg_similarity + agent_info['relevance_score']) / 2
            
            # Only route if confidence is above threshold
            if confidence < 0.4:
                return None
            
            # Create routing tags
            tags = f"agent:{agent_info['agent_name']}:routed_from:{source_strand.get('id')}:{agent_info['routing_reason']}"
            
            # Prepare content for routing
            routed_content = {
                'original_strand_id': source_strand.get('id'),
                'original_content': source_strand.get('content'),
                'routing_reason': agent_info['routing_reason'],
                'similar_patterns': similar_patterns[:3],  # Top 3 similar patterns
                'routing_metadata': {
                    'routed_at': datetime.now(timezone.utc).isoformat(),
                    'routing_confidence': confidence,
                    'source_agent': source_strand.get('source_agent', 'unknown')
                }
            }
            
            return RoutingDecision(
                target_agent=agent_info['agent_name'],
                source_strand_id=source_strand.get('id'),
                routing_reason=agent_info['routing_reason'],
                similarity_score=avg_similarity,
                confidence=confidence,
                tags=tags,
                content=routed_content,
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create routing decision: {e}")
            return None
    
    async def _execute_routing_decision(self, decision: RoutingDecision) -> bool:
        """
        Execute a routing decision by creating a new strand
        
        Args:
            decision: Routing decision to execute
            
        Returns:
            True if routing executed successfully
        """
        try:
            # Create new strand in AD_strands table
            new_strand = {
                'content': json.dumps(decision.content),
                'tags': decision.tags,
                'source_agent': 'central_router',
                'target_agent': decision.target_agent,
                'routing_metadata': {
                    'routing_decision_id': str(uuid.uuid4()),
                    'source_strand_id': decision.source_strand_id,
                    'routing_reason': decision.routing_reason,
                    'similarity_score': decision.similarity_score,
                    'confidence': decision.confidence,
                    'routed_at': decision.timestamp.isoformat()
                }
            }
            
            # Insert into database
            result = self.supabase_manager.client.table('AD_strands').insert(new_strand).execute()
            
            if result.data:
                self.routing_history.append(decision)
                self.logger.info(f"Successfully routed strand to {decision.target_agent}")
                return True
            else:
                self.logger.error(f"Failed to insert routed strand for {decision.target_agent}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to execute routing decision: {e}")
            return False
    
    async def _update_agent_status(self):
        """
        Update the status of registered agents based on recent activity
        """
        try:
            # Check for agent activity in the last hour
            one_hour_ago = datetime.now(timezone.utc).timestamp() - 3600
            
            for agent_name, capability in self.agent_capabilities.items():
                # Check if agent has been active recently
                recent_activity = self.supabase_manager.client.table('AD_strands').select('id').eq(
                    'source_agent', agent_name
                ).gte('created_at', one_hour_ago).limit(1).execute()
                
                if recent_activity.data:
                    capability.last_active = datetime.now(timezone.utc)
                    capability.status = 'active'
                else:
                    # Mark as inactive if no activity for more than 2 hours
                    if (datetime.now(timezone.utc) - capability.last_active).total_seconds() > 7200:
                        capability.status = 'inactive'
                        
        except Exception as e:
            self.logger.error(f"Failed to update agent status: {e}")
    
    def _update_routing_stats(self, routing_decisions: List[RoutingDecision]):
        """
        Update routing statistics
        
        Args:
            routing_decisions: List of routing decisions made
        """
        if not routing_decisions:
            return
            
        self.routing_stats['total_routes'] += len(routing_decisions)
        self.routing_stats['successful_routes'] += len(routing_decisions)
        
        # Update average scores
        total_similarity = sum(d.similarity_score for d in routing_decisions)
        total_confidence = sum(d.confidence for d in routing_decisions)
        
        if self.routing_stats['total_routes'] > 0:
            self.routing_stats['average_similarity_score'] = (
                (self.routing_stats['average_similarity_score'] * (self.routing_stats['total_routes'] - len(routing_decisions)) + 
                 total_similarity) / self.routing_stats['total_routes']
            )
            self.routing_stats['average_confidence'] = (
                (self.routing_stats['average_confidence'] * (self.routing_stats['total_routes'] - len(routing_decisions)) + 
                 total_confidence) / self.routing_stats['total_routes']
            )
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """
        Get current routing statistics
        
        Returns:
            Dictionary of routing statistics
        """
        return {
            **self.routing_stats,
            'active_agents': len([a for a in self.agent_capabilities.values() if a.status == 'active']),
            'total_agents': len(self.agent_capabilities),
            'is_monitoring': self.is_monitoring,
            'recent_routes': len(self.routing_history[-10:])  # Last 10 routes
        }
    
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
                'performance_metrics': capability.performance_metrics
            }
            for agent_name, capability in self.agent_capabilities.items()
        }
