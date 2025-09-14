"""
Tag Convention System

Standardized tagging system for agent communication through the AD_strands table.
This system provides consistent, parseable tags that enable intelligent routing
and communication between LLM agents.
"""

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class TagType(Enum):
    """Types of tags in the system"""
    AGENT_ROUTING = "agent_routing"
    AGENT_DIRECT = "agent_direct"
    SYSTEM_WIDE = "system_wide"
    INTELLIGENCE_LEVEL = "intelligence_level"
    MESSAGE_TYPE = "message_type"
    PRIORITY = "priority"
    CONTENT_TYPE = "content_type"
    RESPONSE = "response"
    ESCALATION = "escalation"


class Priority(Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageType(Enum):
    """Types of messages in the system"""
    INFORMATION = "information"
    ACTION_REQUIRED = "action_required"
    ESCALATION = "escalation"
    PERFORMANCE_ALERT = "performance_alert"
    LEARNING_OPPORTUNITY = "learning_opportunity"
    SYSTEM_CONTROL = "system_control"
    RESPONSE = "response"
    ERROR = "error"


@dataclass
class TagStructure:
    """Represents the structure of a tag"""
    tag_type: TagType
    pattern: str
    description: str
    example: str
    required_fields: List[str]
    optional_fields: List[str]


class TagConventionSystem:
    """
    Standardized tagging system for agent communication
    
    Provides methods to:
    - Create standardized tags for different communication scenarios
    - Parse and validate existing tags
    - Extract information from tags
    - Generate routing information from tags
    """
    
    def __init__(self):
        self.tag_structures = self._initialize_tag_structures()
        self.tag_patterns = self._compile_tag_patterns()
    
    def _initialize_tag_structures(self) -> Dict[TagType, TagStructure]:
        """Initialize the standard tag structures"""
        return {
            TagType.AGENT_ROUTING: TagStructure(
                tag_type=TagType.AGENT_ROUTING,
                pattern=r"agent:([^:]+):routed_from:([^:]+):([^:]+)(?::priority:([^:]+))?(?::content:([^:]+))?",
                description="Tag for messages routed by the Central Intelligence Router",
                example="agent:threshold_manager:routed_from:strand_123:pattern_detected",
                required_fields=["target_agent", "source_strand_id", "routing_reason"],
                optional_fields=["priority", "content_type"]
            ),
            
            TagType.AGENT_DIRECT: TagStructure(
                tag_type=TagType.AGENT_DIRECT,
                pattern=r"agent:([^:]+):([^:]+):from:([^:]+)",
                description="Tag for direct agent-to-agent communication",
                example="agent:threshold_manager:threshold_analysis:from:pattern_detector",
                required_fields=["target_agent", "action_type", "source_agent"],
                optional_fields=["priority", "message_id"]
            ),
            
            TagType.SYSTEM_WIDE: TagStructure(
                tag_type=TagType.SYSTEM_WIDE,
                pattern=r"system:([^:]+)(?::(.+))?",
                description="Tag for system-wide messages and alerts",
                example="system:escalation_required:performance_degradation",
                required_fields=["system_action"],
                optional_fields=["details", "priority"]
            ),
            
            TagType.INTELLIGENCE_LEVEL: TagStructure(
                tag_type=TagType.INTELLIGENCE_LEVEL,
                pattern=r"intelligence:([^:]+):([^:]+)(?::(.+))?",
                description="Tag for intelligence level communication",
                example="intelligence:raw_data:pattern_detected:volume_spike",
                required_fields=["intelligence_level", "action_type"],
                optional_fields=["details", "confidence"]
            ),
            
            TagType.MESSAGE_TYPE: TagStructure(
                tag_type=TagType.MESSAGE_TYPE,
                pattern=r"message:([^:]+)(?::(.+))?",
                description="Tag for message type classification",
                example="message:action_required:threshold_update",
                required_fields=["message_type"],
                optional_fields=["subtype", "priority"]
            ),
            
            TagType.PRIORITY: TagStructure(
                tag_type=TagType.PRIORITY,
                pattern=r"priority:([^:]+)",
                description="Tag for message priority",
                example="priority:urgent",
                required_fields=["priority_level"],
                optional_fields=[]
            ),
            
            TagType.CONTENT_TYPE: TagStructure(
                tag_type=TagType.CONTENT_TYPE,
                pattern=r"content:([^:]+)(?::(.+))?",
                description="Tag for content type classification",
                example="content:pattern_detection:rsi_divergence",
                required_fields=["content_type"],
                optional_fields=["subtype", "details"]
            ),
            
            TagType.RESPONSE: TagStructure(
                tag_type=TagType.RESPONSE,
                pattern=r"response:([^:]+):to:([^:]+)",
                description="Tag for response messages",
                example="response:acknowledgment:to:message_456",
                required_fields=["response_type", "original_message_id"],
                optional_fields=["responding_agent"]
            ),
            
            TagType.ESCALATION: TagStructure(
                tag_type=TagType.ESCALATION,
                pattern=r"escalation:([^:]+)(?::(.+))?",
                description="Tag for escalation messages",
                example="escalation:performance_alert:threshold_breach",
                required_fields=["escalation_type"],
                optional_fields=["details", "severity"]
            )
        }
    
    def _compile_tag_patterns(self) -> Dict[TagType, re.Pattern]:
        """Compile regex patterns for tag parsing"""
        return {
            tag_type: re.compile(structure.pattern)
            for tag_type, structure in self.tag_structures.items()
        }
    
    def create_agent_routing_tag(self, target_agent: str, source_strand_id: str,
                               routing_reason: str, priority: str = "normal",
                               content_type: str = None) -> str:
        """
        Create a tag for agent routing by the Central Intelligence Router
        
        Args:
            target_agent: Name of the target agent
            source_strand_id: ID of the source strand
            routing_reason: Reason for routing
            priority: Priority level
            content_type: Optional content type
            
        Returns:
            Formatted routing tag
        """
        base_tag = f"agent:{target_agent}:routed_from:{source_strand_id}:{routing_reason}"
        
        if priority != "normal":
            base_tag += f":priority:{priority}"
        
        if content_type:
            base_tag += f":content:{content_type}"
        
        return base_tag
    
    def create_agent_direct_tag(self, target_agent: str, action_type: str,
                              source_agent: str, priority: str = "normal",
                              message_id: str = None) -> str:
        """
        Create a tag for direct agent-to-agent communication
        
        Args:
            target_agent: Name of the target agent
            action_type: Type of action required
            source_agent: Name of the source agent
            priority: Priority level
            message_id: Optional message ID
            
        Returns:
            Formatted direct communication tag
        """
        base_tag = f"agent:{target_agent}:{action_type}:from:{source_agent}"
        
        if priority != "normal":
            base_tag += f":priority:{priority}"
        
        if message_id:
            base_tag += f":id:{message_id}"
        
        return base_tag
    
    def create_system_wide_tag(self, system_action: str, details: str = None,
                             priority: str = "normal") -> str:
        """
        Create a tag for system-wide messages
        
        Args:
            system_action: System action type
            details: Optional details
            priority: Priority level
            
        Returns:
            Formatted system-wide tag
        """
        base_tag = f"system:{system_action}"
        
        if details:
            base_tag += f":{details}"
        
        if priority != "normal":
            base_tag += f":priority:{priority}"
        
        return base_tag
    
    def create_intelligence_level_tag(self, intelligence_level: str, action_type: str,
                                    details: str = None, confidence: float = None) -> str:
        """
        Create a tag for intelligence level communication
        
        Args:
            intelligence_level: Intelligence level (raw_data, indicator, pattern, system)
            action_type: Type of action
            details: Optional details
            confidence: Optional confidence score
            
        Returns:
            Formatted intelligence level tag
        """
        base_tag = f"intelligence:{intelligence_level}:{action_type}"
        
        if details:
            base_tag += f":{details}"
        
        if confidence is not None:
            base_tag += f":confidence:{confidence:.2f}"
        
        return base_tag
    
    def create_message_type_tag(self, message_type: str, subtype: str = None,
                              priority: str = "normal") -> str:
        """
        Create a tag for message type classification
        
        Args:
            message_type: Type of message
            subtype: Optional subtype
            priority: Priority level
            
        Returns:
            Formatted message type tag
        """
        base_tag = f"message:{message_type}"
        
        if subtype:
            base_tag += f":{subtype}"
        
        if priority != "normal":
            base_tag += f":priority:{priority}"
        
        return base_tag
    
    def create_priority_tag(self, priority_level: str) -> str:
        """
        Create a priority tag
        
        Args:
            priority_level: Priority level (low, normal, high, urgent)
            
        Returns:
            Formatted priority tag
        """
        return f"priority:{priority_level}"
    
    def create_content_type_tag(self, content_type: str, subtype: str = None,
                              details: str = None) -> str:
        """
        Create a content type tag
        
        Args:
            content_type: Type of content
            subtype: Optional subtype
            details: Optional details
            
        Returns:
            Formatted content type tag
        """
        base_tag = f"content:{content_type}"
        
        if subtype:
            base_tag += f":{subtype}"
        
        if details:
            base_tag += f":{details}"
        
        return base_tag
    
    def create_response_tag(self, response_type: str, original_message_id: str,
                          responding_agent: str = None) -> str:
        """
        Create a response tag
        
        Args:
            response_type: Type of response
            original_message_id: ID of the original message
            responding_agent: Optional responding agent name
            
        Returns:
            Formatted response tag
        """
        base_tag = f"response:{response_type}:to:{original_message_id}"
        
        if responding_agent:
            base_tag += f":from:{responding_agent}"
        
        return base_tag
    
    def create_escalation_tag(self, escalation_type: str, details: str = None,
                            severity: str = None) -> str:
        """
        Create an escalation tag
        
        Args:
            escalation_type: Type of escalation
            details: Optional details
            severity: Optional severity level
            
        Returns:
            Formatted escalation tag
        """
        base_tag = f"escalation:{escalation_type}"
        
        if details:
            base_tag += f":{details}"
        
        if severity:
            base_tag += f":severity:{severity}"
        
        return base_tag
    
    def parse_tag(self, tag: str) -> Optional[Dict[str, Any]]:
        """
        Parse a tag and extract its components
        
        Args:
            tag: Tag string to parse
            
        Returns:
            Dictionary with parsed tag information or None if invalid
        """
        for tag_type, pattern in self.tag_patterns.items():
            match = pattern.match(tag)
            if match:
                structure = self.tag_structures[tag_type]
                groups = match.groups()
                
                # Map groups to field names
                parsed_data = {
                    'tag_type': tag_type.value,
                    'valid': True,
                    'structure': structure.description
                }
                
                # Add required fields
                for i, field in enumerate(structure.required_fields):
                    if i < len(groups) and groups[i]:
                        parsed_data[field] = groups[i]
                
                # Add optional fields if present
                for i, field in enumerate(structure.optional_fields):
                    field_index = len(structure.required_fields) + i
                    if field_index < len(groups) and groups[field_index]:
                        parsed_data[field] = groups[field_index]
                
                return parsed_data
        
        return {
            'tag_type': 'unknown',
            'valid': False,
            'error': 'Tag does not match any known pattern'
        }
    
    def extract_agent_info(self, tag: str) -> Optional[Dict[str, str]]:
        """
        Extract agent information from a tag
        
        Args:
            tag: Tag string to parse
            
        Returns:
            Dictionary with agent information or None if not found
        """
        parsed = self.parse_tag(tag)
        if not parsed or not parsed.get('valid'):
            return None
        
        agent_info = {}
        
        if 'target_agent' in parsed:
            agent_info['target_agent'] = parsed['target_agent']
        
        if 'source_agent' in parsed:
            agent_info['source_agent'] = parsed['source_agent']
        
        if 'responding_agent' in parsed:
            agent_info['responding_agent'] = parsed['responding_agent']
        
        return agent_info if agent_info else None
    
    def extract_priority(self, tag: str) -> Optional[str]:
        """
        Extract priority information from a tag
        
        Args:
            tag: Tag string to parse
            
        Returns:
            Priority level or None if not found
        """
        parsed = self.parse_tag(tag)
        if not parsed or not parsed.get('valid'):
            return None
        
        return parsed.get('priority_level') or parsed.get('priority')
    
    def extract_content_type(self, tag: str) -> Optional[str]:
        """
        Extract content type information from a tag
        
        Args:
            tag: Tag string to parse
            
        Returns:
            Content type or None if not found
        """
        parsed = self.parse_tag(tag)
        if not parsed or not parsed.get('valid'):
            return None
        
        return parsed.get('content_type')
    
    def is_agent_tag(self, tag: str) -> bool:
        """
        Check if a tag is related to agent communication
        
        Args:
            tag: Tag string to check
            
        Returns:
            True if tag is agent-related
        """
        parsed = self.parse_tag(tag)
        if not parsed or not parsed.get('valid'):
            return False
        
        return parsed['tag_type'] in ['agent_routing', 'agent_direct']
    
    def is_system_tag(self, tag: str) -> bool:
        """
        Check if a tag is a system-wide tag
        
        Args:
            tag: Tag string to check
            
        Returns:
            True if tag is system-wide
        """
        parsed = self.parse_tag(tag)
        if not parsed or not parsed.get('valid'):
            return False
        
        return parsed['tag_type'] == 'system_wide'
    
    def is_escalation_tag(self, tag: str) -> bool:
        """
        Check if a tag is an escalation tag
        
        Args:
            tag: Tag string to check
            
        Returns:
            True if tag is an escalation
        """
        parsed = self.parse_tag(tag)
        if not parsed or not parsed.get('valid'):
            return False
        
        return parsed['tag_type'] == 'escalation'
    
    def get_tag_examples(self) -> Dict[str, List[str]]:
        """
        Get examples of all tag types
        
        Returns:
            Dictionary of tag examples by type
        """
        examples = {}
        
        for tag_type, structure in self.tag_structures.items():
            examples[tag_type.value] = [
                structure.example,
                f"Example: {structure.description}"
            ]
        
        return examples
    
    def validate_tag(self, tag: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a tag against the convention system
        
        Args:
            tag: Tag string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        parsed = self.parse_tag(tag)
        
        if not parsed:
            return False, "Tag could not be parsed"
        
        if not parsed.get('valid'):
            return False, parsed.get('error', 'Unknown validation error')
        
        return True, None
