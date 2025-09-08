"""
Agent Communication Protocol

Standardized protocol for LLM agents to communicate through the database
using the AD_strands table. This enables database-centric agent communication
without requiring separate communication infrastructure.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import json
import uuid

from src.utils.supabase_manager import SupabaseManager


@dataclass
class StrandMessage:
    """Represents a message sent through the strand system"""
    content: Dict[str, Any]
    tags: str
    source_agent: str
    target_agent: Optional[str] = None
    message_type: str = 'information'
    priority: str = 'normal'  # 'low', 'normal', 'high', 'urgent'
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AgentResponse:
    """Represents a response from an agent"""
    response_id: str
    original_message_id: str
    responding_agent: str
    response_content: Dict[str, Any]
    response_type: str  # 'acknowledgment', 'action_taken', 'escalation', 'error'
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class AgentCommunicationProtocol:
    """
    Standardized protocol for agent communication through database
    
    Provides a clean interface for agents to:
    - Publish findings and information
    - Listen for messages directed to them
    - Tag other agents directly (when they know who to contact)
    - Respond to messages
    - Handle different message types and priorities
    """
    
    def __init__(self, agent_name: str, supabase_manager: SupabaseManager):
        self.agent_name = agent_name
        self.supabase_manager = supabase_manager
        self.is_listening = False
        self.listening_task: Optional[asyncio.Task] = None
        self.message_handlers: Dict[str, callable] = {}
        self.response_callbacks: Dict[str, callable] = {}
        
        # Message tracking
        self.sent_messages: Dict[str, StrandMessage] = {}
        self.received_messages: List[StrandMessage] = []
        self.pending_responses: Dict[str, datetime] = {}
        
        # Initialize logging
        self.logger = logging.getLogger(f"{__name__}.{agent_name}")
        
        # Register default message handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default message handlers for common message types"""
        self.message_handlers.update({
            'information': self._handle_information_message,
            'action_required': self._handle_action_required_message,
            'escalation': self._handle_escalation_message,
            'performance_alert': self._handle_performance_alert_message,
            'learning_opportunity': self._handle_learning_opportunity_message,
            'system_control': self._handle_system_control_message
        })
    
    def register_message_handler(self, message_type: str, handler: callable):
        """
        Register a custom message handler for a specific message type
        
        Args:
            message_type: Type of message to handle
            handler: Function to handle the message
        """
        self.message_handlers[message_type] = handler
        self.logger.info(f"Registered handler for message type: {message_type}")
    
    def register_response_callback(self, message_id: str, callback: callable):
        """
        Register a callback for when a response is received for a specific message
        
        Args:
            message_id: ID of the message to wait for response
            callback: Function to call when response is received
        """
        self.response_callbacks[message_id] = callback
        self.pending_responses[message_id] = datetime.now(timezone.utc)
        self.logger.info(f"Registered response callback for message: {message_id}")
    
    async def publish_finding(self, content: Dict[str, Any], tags: Optional[str] = None,
                            priority: str = 'normal', expires_at: Optional[datetime] = None) -> str:
        """
        Publish a finding or information to the database
        
        Args:
            content: Content of the finding
            tags: Optional tags for the message
            priority: Priority level ('low', 'normal', 'high', 'urgent')
            expires_at: Optional expiration time for the message
            
        Returns:
            Message ID of the published message
        """
        try:
            message_id = str(uuid.uuid4())
            
            # Create default tags if not provided
            if not tags:
                tags = f"agent:{self.agent_name}:finding"
            
            # Create strand message
            message = StrandMessage(
                content=content,
                tags=tags,
                source_agent=self.agent_name,
                message_type='information',
                priority=priority,
                expires_at=expires_at,
                metadata={
                    'message_id': message_id,
                    'published_at': datetime.now(timezone.utc).isoformat(),
                    'agent_version': '1.0'
                }
            )
            
            # Store message
            self.sent_messages[message_id] = message
            
            # Create database record
            strand_record = {
                'content': json.dumps(content),
                'tags': tags,
                'source_agent': self.agent_name,
                'message_metadata': {
                    'message_id': message_id,
                    'message_type': 'information',
                    'priority': priority,
                    'expires_at': expires_at.isoformat() if expires_at else None,
                    'published_at': datetime.now(timezone.utc).isoformat()
                }
            }
            
            # Insert into database
            result = self.supabase_manager.client.table('AD_strands').insert(strand_record).execute()
            
            if result.data:
                self.logger.info(f"Published finding with message ID: {message_id}")
                return message_id
            else:
                self.logger.error(f"Failed to publish finding: {message_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to publish finding: {e}")
            return None
    
    async def tag_other_agent(self, target_agent: str, content: Dict[str, Any],
                            action_type: str, priority: str = 'normal') -> str:
        """
        Directly tag another agent with a message
        
        Args:
            target_agent: Name of the target agent
            content: Content of the message
            action_type: Type of action required
            priority: Priority level
            
        Returns:
            Message ID of the sent message
        """
        try:
            message_id = str(uuid.uuid4())
            
            # Create tags for direct agent communication
            tags = f"agent:{target_agent}:{action_type}:from:{self.agent_name}"
            
            # Create strand message
            message = StrandMessage(
                content=content,
                tags=tags,
                source_agent=self.agent_name,
                target_agent=target_agent,
                message_type=action_type,
                priority=priority,
                metadata={
                    'message_id': message_id,
                    'direct_communication': True,
                    'action_type': action_type,
                    'sent_at': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Store message
            self.sent_messages[message_id] = message
            
            # Create database record
            strand_record = {
                'content': json.dumps(content),
                'tags': tags,
                'source_agent': self.agent_name,
                'target_agent': target_agent,
                'message_metadata': {
                    'message_id': message_id,
                    'message_type': action_type,
                    'priority': priority,
                    'direct_communication': True,
                    'sent_at': datetime.now(timezone.utc).isoformat()
                }
            }
            
            # Insert into database
            result = self.supabase_manager.client.table('AD_strands').insert(strand_record).execute()
            
            if result.data:
                self.logger.info(f"Tagged agent '{target_agent}' with message ID: {message_id}")
                return message_id
            else:
                self.logger.error(f"Failed to tag agent '{target_agent}': {message_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to tag agent '{target_agent}': {e}")
            return None
    
    async def respond_to_message(self, original_message_id: str, response_content: Dict[str, Any],
                               response_type: str = 'acknowledgment') -> str:
        """
        Respond to a received message
        
        Args:
            original_message_id: ID of the original message
            response_content: Content of the response
            response_type: Type of response ('acknowledgment', 'action_taken', 'escalation', 'error')
            
        Returns:
            Response ID
        """
        try:
            response_id = str(uuid.uuid4())
            
            # Create response tags
            tags = f"agent:{self.agent_name}:response:{response_type}:to:{original_message_id}"
            
            # Create response content
            response_data = {
                'response_id': response_id,
                'original_message_id': original_message_id,
                'responding_agent': self.agent_name,
                'response_content': response_content,
                'response_type': response_type,
                'responded_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Create database record
            strand_record = {
                'content': json.dumps(response_data),
                'tags': tags,
                'source_agent': self.agent_name,
                'message_metadata': {
                    'response_id': response_id,
                    'original_message_id': original_message_id,
                    'response_type': response_type,
                    'responded_at': datetime.now(timezone.utc).isoformat()
                }
            }
            
            # Insert into database
            result = self.supabase_manager.client.table('AD_strands').insert(strand_record).execute()
            
            if result.data:
                self.logger.info(f"Responded to message {original_message_id} with response ID: {response_id}")
                return response_id
            else:
                self.logger.error(f"Failed to respond to message {original_message_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to respond to message {original_message_id}: {e}")
            return None
    
    def start_listening(self) -> bool:
        """
        Start listening for messages directed to this agent
        
        Returns:
            True if listening started successfully
        """
        try:
            if self.is_listening:
                self.logger.warning("Already listening for messages")
                return True
                
            self.is_listening = True
            self.listening_task = asyncio.create_task(self._listen_for_messages())
            
            self.logger.info(f"Agent '{self.agent_name}' started listening for messages")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start listening: {e}")
            self.is_listening = False
            return False
    
    def stop_listening(self) -> bool:
        """
        Stop listening for messages
        
        Returns:
            True if listening stopped successfully
        """
        try:
            if not self.is_listening:
                self.logger.warning("Not currently listening")
                return True
                
            self.is_listening = False
            
            if self.listening_task:
                self.listening_task.cancel()
                self.listening_task = None
            
            self.logger.info(f"Agent '{self.agent_name}' stopped listening for messages")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop listening: {e}")
            return False
    
    async def _listen_for_messages(self):
        """
        Continuously listen for messages directed to this agent
        """
        self.logger.info(f"Starting message listening loop for agent '{self.agent_name}'")
        
        while self.is_listening:
            try:
                # Get messages directed to this agent
                messages = await self._get_messages_for_agent()
                
                for message in messages:
                    await self._process_message(message)
                
                # Check for responses to our sent messages
                await self._check_for_responses()
                
                # Sleep for 10 seconds before next check
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                self.logger.info(f"Message listening cancelled for agent '{self.agent_name}'")
                break
            except Exception as e:
                self.logger.error(f"Error in message listening: {e}")
                await asyncio.sleep(30)  # Wait longer on error
    
    async def _get_messages_for_agent(self) -> List[Dict[str, Any]]:
        """
        Get messages directed to this agent
        
        Returns:
            List of message records
        """
        try:
            # Get messages from last 2 minutes
            two_minutes_ago = datetime.now(timezone.utc).timestamp() - 120
            
            # Query for messages tagged for this agent
            result = self.supabase_manager.client.table('AD_strands').select('*').or_(
                f"target_agent.eq.{self.agent_name},tags.like.agent:{self.agent_name}%"
            ).gte('created_at', two_minutes_ago).order('created_at', desc=True).limit(50).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            self.logger.error(f"Failed to get messages for agent: {e}")
            return []
    
    async def _process_message(self, message_record: Dict[str, Any]):
        """
        Process a received message
        
        Args:
            message_record: Message record from database
        """
        try:
            # Parse message content
            content = message_record.get('content', {})
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except:
                    content = {'text': content}
            
            # Extract message metadata
            metadata = message_record.get('message_metadata', {})
            message_type = metadata.get('message_type', 'information')
            message_id = metadata.get('message_id', message_record.get('id'))
            
            # Create strand message object
            strand_message = StrandMessage(
                content=content,
                tags=message_record.get('tags', ''),
                source_agent=message_record.get('source_agent', 'unknown'),
                target_agent=message_record.get('target_agent'),
                message_type=message_type,
                priority=metadata.get('priority', 'normal'),
                expires_at=datetime.fromisoformat(metadata['expires_at']) if metadata.get('expires_at') else None,
                metadata=metadata
            )
            
            # Check if message has expired
            if strand_message.expires_at and datetime.now(timezone.utc) > strand_message.expires_at:
                self.logger.warning(f"Received expired message: {message_id}")
                return
            
            # Store received message
            self.received_messages.append(strand_message)
            
            # Handle the message
            await self._handle_message(strand_message)
            
        except Exception as e:
            self.logger.error(f"Failed to process message: {e}")
    
    async def _handle_message(self, message: StrandMessage):
        """
        Handle a received message based on its type
        
        Args:
            message: Strand message to handle
        """
        try:
            message_type = message.message_type
            
            # Get appropriate handler
            handler = self.message_handlers.get(message_type, self._handle_unknown_message)
            
            # Execute handler
            await handler(message)
            
        except Exception as e:
            self.logger.error(f"Failed to handle message: {e}")
    
    async def _handle_information_message(self, message: StrandMessage):
        """Handle information messages"""
        self.logger.info(f"Received information message from {message.source_agent}")
        # Default: acknowledge receipt
        await self.respond_to_message(
            message.metadata.get('message_id', ''),
            {'status': 'received', 'agent': self.agent_name},
            'acknowledgment'
        )
    
    async def _handle_action_required_message(self, message: StrandMessage):
        """Handle action required messages"""
        self.logger.info(f"Received action required message from {message.source_agent}")
        # Default: acknowledge and indicate action will be taken
        await self.respond_to_message(
            message.metadata.get('message_id', ''),
            {'status': 'action_acknowledged', 'agent': self.agent_name},
            'acknowledgment'
        )
    
    async def _handle_escalation_message(self, message: StrandMessage):
        """Handle escalation messages"""
        self.logger.warning(f"Received escalation message from {message.source_agent}")
        # Default: acknowledge escalation
        await self.respond_to_message(
            message.metadata.get('message_id', ''),
            {'status': 'escalation_received', 'agent': self.agent_name},
            'acknowledgment'
        )
    
    async def _handle_performance_alert_message(self, message: StrandMessage):
        """Handle performance alert messages"""
        self.logger.warning(f"Received performance alert from {message.source_agent}")
        # Default: acknowledge alert
        await self.respond_to_message(
            message.metadata.get('message_id', ''),
            {'status': 'alert_received', 'agent': self.agent_name},
            'acknowledgment'
        )
    
    async def _handle_learning_opportunity_message(self, message: StrandMessage):
        """Handle learning opportunity messages"""
        self.logger.info(f"Received learning opportunity from {message.source_agent}")
        # Default: acknowledge learning opportunity
        await self.respond_to_message(
            message.metadata.get('message_id', ''),
            {'status': 'learning_opportunity_received', 'agent': self.agent_name},
            'acknowledgment'
        )
    
    async def _handle_system_control_message(self, message: StrandMessage):
        """Handle system control messages"""
        self.logger.info(f"Received system control message from {message.source_agent}")
        # Default: acknowledge system control
        await self.respond_to_message(
            message.metadata.get('message_id', ''),
            {'status': 'system_control_received', 'agent': self.agent_name},
            'acknowledgment'
        )
    
    async def _handle_unknown_message(self, message: StrandMessage):
        """Handle unknown message types"""
        self.logger.warning(f"Received unknown message type from {message.source_agent}: {message.message_type}")
        # Default: acknowledge with error
        await self.respond_to_message(
            message.metadata.get('message_id', ''),
            {'status': 'unknown_message_type', 'agent': self.agent_name},
            'error'
        )
    
    async def _check_for_responses(self):
        """
        Check for responses to messages we sent
        """
        try:
            # Get responses from last 5 minutes
            five_minutes_ago = datetime.now(timezone.utc).timestamp() - 300
            
            # Query for responses to our messages
            result = self.supabase_manager.client.table('AD_strands').select('*').like(
                'tags', f'%response%to:%'
            ).gte('created_at', five_minutes_ago).order('created_at', desc=True).limit(20).execute()
            
            if result.data:
                for response_record in result.data:
                    await self._process_response(response_record)
                    
        except Exception as e:
            self.logger.error(f"Failed to check for responses: {e}")
    
    async def _process_response(self, response_record: Dict[str, Any]):
        """
        Process a response to one of our messages
        
        Args:
            response_record: Response record from database
        """
        try:
            # Parse response content
            content = response_record.get('content', {})
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except:
                    content = {'text': content}
            
            # Extract original message ID
            original_message_id = content.get('original_message_id')
            if not original_message_id:
                return
            
            # Check if we have a callback for this message
            if original_message_id in self.response_callbacks:
                callback = self.response_callbacks[original_message_id]
                await callback(content, response_record)
                
                # Remove from pending responses
                del self.response_callbacks[original_message_id]
                if original_message_id in self.pending_responses:
                    del self.pending_responses[original_message_id]
                
                self.logger.info(f"Processed response to message {original_message_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to process response: {e}")
    
    def get_communication_stats(self) -> Dict[str, Any]:
        """
        Get communication statistics for this agent
        
        Returns:
            Dictionary of communication statistics
        """
        return {
            'agent_name': self.agent_name,
            'is_listening': self.is_listening,
            'sent_messages': len(self.sent_messages),
            'received_messages': len(self.received_messages),
            'pending_responses': len(self.pending_responses),
            'registered_handlers': len(self.message_handlers),
            'active_callbacks': len(self.response_callbacks)
        }
