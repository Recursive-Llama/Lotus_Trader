"""
Module Listener
Phase 1.5.2: Listen for feedback from Decision Maker and Trader
"""

import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable
from queue import Queue

from src.utils.supabase_manager import SupabaseManager

logger = logging.getLogger(__name__)


class ModuleListener:
    """
    Listens for feedback from Decision Maker and Trader modules
    Processes incoming messages and triggers appropriate handlers
    """
    
    def __init__(self, db_manager: Optional[SupabaseManager] = None):
        self.db_manager = db_manager or SupabaseManager()
        self.module_type = 'alpha'
        self.is_listening = False
        self.listen_thread = None
        self.message_queue = Queue()
        
        # Message handlers
        self.handlers = {
            'decision_feedback': self._handle_decision_feedback,
            'execution_feedback': self._handle_execution_feedback,
            'intelligence_update': self._handle_intelligence_update,
            'error_notification': self._handle_error_notification
        }
        
        # Feedback storage
        self.feedback_history = []
        self.max_feedback_history = 1000
    
    def start_listening(self, check_interval: float = 5.0):
        """
        Start listening for messages from other modules
        
        Args:
            check_interval: Seconds between database checks
        """
        if self.is_listening:
            logger.warning("Module listener is already running")
            return
        
        self.is_listening = True
        self.listen_thread = threading.Thread(
            target=self._listen_loop,
            args=(check_interval,),
            daemon=True
        )
        self.listen_thread.start()
        
        logger.info("Module listener started")
    
    def stop_listening(self):
        """Stop listening for messages"""
        self.is_listening = False
        if self.listen_thread:
            self.listen_thread.join(timeout=5.0)
        
        logger.info("Module listener stopped")
    
    def _listen_loop(self, check_interval: float):
        """Main listening loop"""
        last_check_time = datetime.now(timezone.utc)
        
        while self.is_listening:
            try:
                current_time = datetime.now(timezone.utc)
                
                # Check for new messages from Decision Maker
                self._check_decision_maker_messages(last_check_time)
                
                # Check for new messages from Trader
                self._check_trader_messages(last_check_time)
                
                # Process queued messages
                self._process_message_queue()
                
                last_check_time = current_time
                time.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Error in listening loop: {e}")
                time.sleep(check_interval)
    
    def _check_decision_maker_messages(self, since_time: datetime):
        """Check for new messages from Decision Maker"""
        try:
            # Query DM_strands for messages tagged for Alpha Detector
            messages = self.db_manager.query(
                "DM_strands",
                select="*",
                filter=f"created_at.gte.{since_time.isoformat()},tags.cs.['alpha:feedback']",
                order="created_at.desc",
                limit=10
            )
            
            if messages:
                for message in messages:
                    self._process_decision_maker_message(message)
                    
        except Exception as e:
            logger.error(f"Error checking Decision Maker messages: {e}")
    
    def _check_trader_messages(self, since_time: datetime):
        """Check for new messages from Trader"""
        try:
            # Query TR_strands for messages tagged for Alpha Detector
            messages = self.db_manager.query(
                "TR_strands",
                select="*",
                filter=f"created_at.gte.{since_time.isoformat()},tags.cs.['alpha:execution_feedback']",
                order="created_at.desc",
                limit=10
            )
            
            if messages:
                for message in messages:
                    self._process_trader_message(message)
                    
        except Exception as e:
            logger.error(f"Error checking Trader messages: {e}")
    
    def _process_decision_maker_message(self, message: Dict[str, Any]):
        """Process message from Decision Maker"""
        try:
            message_type = self._determine_message_type(message)
            
            if message_type in self.handlers:
                self.message_queue.put({
                    'type': message_type,
                    'source': 'decision_maker',
                    'data': message,
                    'timestamp': datetime.now(timezone.utc)
                })
                
                logger.info(f"Queued Decision Maker message: {message_type}")
            else:
                logger.warning(f"Unknown Decision Maker message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error processing Decision Maker message: {e}")
    
    def _process_trader_message(self, message: Dict[str, Any]):
        """Process message from Trader"""
        try:
            message_type = self._determine_message_type(message)
            
            if message_type in self.handlers:
                self.message_queue.put({
                    'type': message_type,
                    'source': 'trader',
                    'data': message,
                    'timestamp': datetime.now(timezone.utc)
                })
                
                logger.info(f"Queued Trader message: {message_type}")
            else:
                logger.warning(f"Unknown Trader message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error processing Trader message: {e}")
    
    def _determine_message_type(self, message: Dict[str, Any]) -> str:
        """Determine message type from message data"""
        try:
            tags = message.get('tags', [])
            
            if 'alpha:decision_feedback' in tags:
                return 'decision_feedback'
            elif 'alpha:execution_feedback' in tags:
                return 'execution_feedback'
            elif 'alpha:intelligence_update' in tags:
                return 'intelligence_update'
            elif 'alpha:error_notification' in tags:
                return 'error_notification'
            else:
                return 'unknown'
                
        except Exception as e:
            logger.error(f"Error determining message type: {e}")
            return 'unknown'
    
    def _process_message_queue(self):
        """Process queued messages"""
        while not self.message_queue.empty():
            try:
                message = self.message_queue.get_nowait()
                self._handle_message(message)
            except Exception as e:
                logger.error(f"Error processing queued message: {e}")
    
    def _handle_message(self, message: Dict[str, Any]):
        """Handle a single message"""
        try:
            message_type = message['type']
            handler = self.handlers.get(message_type)
            
            if handler:
                handler(message)
                self._store_feedback(message)
            else:
                logger.warning(f"No handler for message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def _handle_decision_feedback(self, message: Dict[str, Any]):
        """Handle decision feedback from Decision Maker"""
        try:
            data = message['data']
            decision_data = data.get('dm_decision', {})
            
            logger.info(f"Received decision feedback: {data.get('id', 'unknown')}")
            logger.debug(f"Decision data: {decision_data}")
            
            # Process decision feedback
            # This is where we would update our learning systems
            # For now, just log the feedback
            
        except Exception as e:
            logger.error(f"Error handling decision feedback: {e}")
    
    def _handle_execution_feedback(self, message: Dict[str, Any]):
        """Handle execution feedback from Trader"""
        try:
            data = message['data']
            execution_data = data.get('tr_execution', {})
            outcome_data = data.get('tr_outcome', {})
            
            logger.info(f"Received execution feedback: {data.get('id', 'unknown')}")
            logger.debug(f"Execution data: {execution_data}")
            logger.debug(f"Outcome data: {outcome_data}")
            
            # Process execution feedback
            # This is where we would update our performance metrics
            # For now, just log the feedback
            
        except Exception as e:
            logger.error(f"Error handling execution feedback: {e}")
    
    def _handle_intelligence_update(self, message: Dict[str, Any]):
        """Handle intelligence update from other modules"""
        try:
            data = message['data']
            intelligence_data = data.get('module_intelligence', {})
            
            logger.info(f"Received intelligence update: {data.get('id', 'unknown')}")
            logger.debug(f"Intelligence data: {intelligence_data}")
            
            # Process intelligence update
            # This is where we would integrate external intelligence
            # For now, just log the update
            
        except Exception as e:
            logger.error(f"Error handling intelligence update: {e}")
    
    def _handle_error_notification(self, message: Dict[str, Any]):
        """Handle error notification from other modules"""
        try:
            data = message['data']
            error_data = data.get('error_details', {})
            
            logger.warning(f"Received error notification: {data.get('id', 'unknown')}")
            logger.warning(f"Error details: {error_data}")
            
            # Process error notification
            # This is where we would handle system errors
            # For now, just log the error
            
        except Exception as e:
            logger.error(f"Error handling error notification: {e}")
    
    def _store_feedback(self, message: Dict[str, Any]):
        """Store feedback in history"""
        try:
            self.feedback_history.append(message)
            
            # Limit history size
            if len(self.feedback_history) > self.max_feedback_history:
                self.feedback_history = self.feedback_history[-self.max_feedback_history:]
                
        except Exception as e:
            logger.error(f"Error storing feedback: {e}")
    
    def get_feedback_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent feedback history"""
        return self.feedback_history[-limit:]
    
    def get_listener_status(self) -> Dict[str, Any]:
        """Get listener status and statistics"""
        return {
            'is_listening': self.is_listening,
            'message_queue_size': self.message_queue.qsize(),
            'feedback_history_size': len(self.feedback_history),
            'handlers_registered': list(self.handlers.keys()),
            'last_check': datetime.now(timezone.utc).isoformat()
        }
