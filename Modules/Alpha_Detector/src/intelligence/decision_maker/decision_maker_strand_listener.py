"""
Decision Maker Strand Listener

This module handles Decision Maker's responsibility to listen for CIL-tagged strands
and process strategic risk insights automatically. Decision Maker receives insights
that were already tagged by CIL and applies them to decision making.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone, timedelta
import json

class DecisionMakerStrandListener:
    """
    Handles Decision Maker's listening for CIL-tagged strands and processing insights.
    
    This is Decision Maker's responsibility - to listen for CIL insights that were
    already tagged for Decision Maker and process them automatically.
    """

    def __init__(self, supabase_manager: Any):
        self.logger = logging.getLogger(__name__)
        self.supabase_manager = supabase_manager
        self.insight_handlers = {}  # Registered insight handlers
        self.active_listeners = {}  # Active listening tasks
        self.received_insights = {}  # Cache of received insights
        
        # Decision Maker specific tags to listen for
        self.decision_maker_tags = [
            'dm:risk_guidance',
            'dm:execute',
            'dm:risk_level_high',
            'dm:risk_level_medium', 
            'dm:risk_level_low',
            'dm:strategy_*',  # Will match any strategy type
            'cil:strategic_insight'
        ]
        
    async def start_listening(self):
        """Start listening for CIL-tagged strands."""
        self.logger.info("Starting Decision Maker strand listening...")
        
        # Start listening for each tag type
        for tag in self.decision_maker_tags:
            if tag.endswith('*'):
                # Handle wildcard tags
                base_tag = tag[:-1]  # Remove the *
                await self._start_wildcard_listener(base_tag)
            else:
                await self._start_tag_listener(tag)
        
        self.logger.info("Decision Maker strand listening started successfully")
    
    async def stop_listening(self):
        """Stop all listening tasks."""
        self.logger.info("Stopping Decision Maker strand listening...")
        
        for listener_id, task in self.active_listeners.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.active_listeners.clear()
        self.logger.info("Decision Maker strand listening stopped")
    
    async def _start_tag_listener(self, tag: str):
        """Start listening for a specific tag."""
        listener_id = f"listener_{tag}"
        
        async def listen_for_tag():
            while True:
                try:
                    # Query for strands with this tag
                    strands = await self._query_strands_by_tag(tag)
                    
                    for strand in strands:
                        await self._process_cil_strand(strand)
                    
                    # Wait before next check
                    await asyncio.sleep(5)  # Check every 5 seconds
                    
                except Exception as e:
                    self.logger.error(f"Error in tag listener {tag}: {e}")
                    await asyncio.sleep(10)  # Wait longer on error
        
        # Start the listener task
        task = asyncio.create_task(listen_for_tag())
        self.active_listeners[listener_id] = task
        
        self.logger.info(f"Started listener for tag: {tag}")
    
    async def _start_wildcard_listener(self, base_tag: str):
        """Start listening for wildcard tags."""
        listener_id = f"wildcard_listener_{base_tag}"
        
        async def listen_for_wildcard():
            while True:
                try:
                    # Query for strands with tags starting with base_tag
                    strands = await self._query_strands_by_wildcard_tag(base_tag)
                    
                    for strand in strands:
                        await self._process_cil_strand(strand)
                    
                    # Wait before next check
                    await asyncio.sleep(5)  # Check every 5 seconds
                    
                except Exception as e:
                    self.logger.error(f"Error in wildcard listener {base_tag}: {e}")
                    await asyncio.sleep(10)  # Wait longer on error
        
        # Start the listener task
        task = asyncio.create_task(listen_for_wildcard())
        self.active_listeners[listener_id] = task
        
        self.logger.info(f"Started wildcard listener for base tag: {base_tag}")
    
    async def _query_strands_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Query strands by specific tag."""
        try:
            # Query AD_strands table for strands with this tag
            query = """
                SELECT * FROM AD_strands 
                WHERE tags @> %s 
                AND created_at > NOW() - INTERVAL '1 hour'
                ORDER BY created_at DESC
                LIMIT 10
            """
            
            result = await self.supabase_manager.execute_query(query, [json.dumps([tag])])
            return result if result else []
            
        except Exception as e:
            self.logger.error(f"Error querying strands by tag {tag}: {e}")
            return []
    
    async def _query_strands_by_wildcard_tag(self, base_tag: str) -> List[Dict[str, Any]]:
        """Query strands by wildcard tag pattern."""
        try:
            # Query AD_strands table for strands with tags starting with base_tag
            query = """
                SELECT * FROM AD_strands 
                WHERE EXISTS (
                    SELECT 1 FROM jsonb_array_elements_text(tags) AS tag
                    WHERE tag LIKE %s
                )
                AND created_at > NOW() - INTERVAL '1 hour'
                ORDER BY created_at DESC
                LIMIT 10
            """
            
            pattern = f"{base_tag}%"
            result = await self.supabase_manager.execute_query(query, [pattern])
            return result if result else []
            
        except Exception as e:
            self.logger.error(f"Error querying strands by wildcard tag {base_tag}: {e}")
            return []
    
    async def _process_cil_strand(self, strand: Dict[str, Any]):
        """Process a CIL strand that was tagged for Decision Maker."""
        try:
            strand_id = strand.get('id')
            if strand_id in self.received_insights:
                # Already processed this strand
                return
            
            # Extract strand information
            module = strand.get('module', '')
            kind = strand.get('kind', '')
            content = strand.get('content', {})
            tags = strand.get('tags', [])
            
            # Only process strands from CIL
            if module != 'cil' and 'central_intelligence' not in str(tags):
                return
            
            self.logger.info(f"Processing CIL strand for Decision Maker: {strand_id}")
            
            # Process based on strand kind
            if kind == 'strategic_risk_insight':
                await self._process_risk_insight_strand(strand)
            elif kind == 'cil_output_directive':
                await self._process_directive_strand(strand)
            elif kind == 'cil_global_synthesis':
                await self._process_synthesis_strand(strand)
            else:
                await self._process_generic_cil_strand(strand)
            
            # Mark as processed
            self.received_insights[strand_id] = {
                'strand': strand,
                'processed_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing CIL strand {strand.get('id', 'unknown')}: {e}")
    
    async def _process_risk_insight_strand(self, strand: Dict[str, Any]):
        """Process a strategic risk insight strand from CIL."""
        try:
            content = strand.get('content', {})
            insights = content.get('insights', {})
            
            self.logger.info(f"Processing risk insights from CIL: {insights.get('insight_id', 'unknown')}")
            
            # Extract risk insights
            risk_assessment = insights.get('risk_assessment', {})
            risk_parameters = insights.get('risk_parameters', {})
            execution_constraints = insights.get('execution_constraints', {})
            strategic_guidance = insights.get('strategic_guidance', {})
            
            # Apply risk insights to Decision Maker
            await self._apply_risk_insights({
                'risk_assessment': risk_assessment,
                'risk_parameters': risk_parameters,
                'execution_constraints': execution_constraints,
                'strategic_guidance': strategic_guidance,
                'source_strand_id': strand.get('id'),
                'received_at': datetime.now(timezone.utc).isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Error processing risk insight strand: {e}")
    
    async def _process_directive_strand(self, strand: Dict[str, Any]):
        """Process a directive strand from CIL."""
        try:
            content = strand.get('content', {})
            
            self.logger.info(f"Processing directive from CIL: {strand.get('id', 'unknown')}")
            
            # Check if this directive is for Decision Maker
            target_module = content.get('target_module', '')
            if target_module == 'decision_maker':
                await self._apply_cil_directive({
                    'directive': content,
                    'source_strand_id': strand.get('id'),
                    'received_at': datetime.now(timezone.utc).isoformat()
                })
            
        except Exception as e:
            self.logger.error(f"Error processing directive strand: {e}")
    
    async def _process_synthesis_strand(self, strand: Dict[str, Any]):
        """Process a global synthesis strand from CIL."""
        try:
            content = strand.get('content', {})
            
            self.logger.info(f"Processing global synthesis from CIL: {strand.get('id', 'unknown')}")
            
            # Extract synthesis insights relevant to Decision Maker
            synthesis_insights = {
                'synthesis_data': content,
                'source_strand_id': strand.get('id'),
                'received_at': datetime.now(timezone.utc).isoformat()
            }
            
            await self._apply_synthesis_insights(synthesis_insights)
            
        except Exception as e:
            self.logger.error(f"Error processing synthesis strand: {e}")
    
    async def _process_generic_cil_strand(self, strand: Dict[str, Any]):
        """Process a generic CIL strand."""
        try:
            self.logger.info(f"Processing generic CIL strand: {strand.get('id', 'unknown')}")
            
            # Extract any relevant information for Decision Maker
            generic_insights = {
                'strand_data': strand,
                'source_strand_id': strand.get('id'),
                'received_at': datetime.now(timezone.utc).isoformat()
            }
            
            await self._apply_generic_insights(generic_insights)
            
        except Exception as e:
            self.logger.error(f"Error processing generic CIL strand: {e}")
    
    async def _apply_risk_insights(self, insights: Dict[str, Any]):
        """Apply risk insights from CIL to Decision Maker."""
        try:
            # Call registered risk insight handler
            if 'risk_insights' in self.insight_handlers:
                handler = self.insight_handlers['risk_insights']
                await handler(insights)
            
            self.logger.info(f"Applied risk insights from CIL: {insights.get('source_strand_id', 'unknown')}")
            
        except Exception as e:
            self.logger.error(f"Error applying risk insights: {e}")
    
    async def _apply_cil_directive(self, directive: Dict[str, Any]):
        """Apply CIL directive to Decision Maker."""
        try:
            # Call registered directive handler
            if 'cil_directive' in self.insight_handlers:
                handler = self.insight_handlers['cil_directive']
                await handler(directive)
            
            self.logger.info(f"Applied CIL directive: {directive.get('source_strand_id', 'unknown')}")
            
        except Exception as e:
            self.logger.error(f"Error applying CIL directive: {e}")
    
    async def _apply_synthesis_insights(self, insights: Dict[str, Any]):
        """Apply synthesis insights from CIL to Decision Maker."""
        try:
            # Call registered synthesis handler
            if 'synthesis_insights' in self.insight_handlers:
                handler = self.insight_handlers['synthesis_insights']
                await handler(insights)
            
            self.logger.info(f"Applied synthesis insights from CIL: {insights.get('source_strand_id', 'unknown')}")
            
        except Exception as e:
            self.logger.error(f"Error applying synthesis insights: {e}")
    
    async def _apply_generic_insights(self, insights: Dict[str, Any]):
        """Apply generic insights from CIL to Decision Maker."""
        try:
            # Call registered generic handler
            if 'generic_insights' in self.insight_handlers:
                handler = self.insight_handlers['generic_insights']
                await handler(insights)
            
            self.logger.info(f"Applied generic insights from CIL: {insights.get('source_strand_id', 'unknown')}")
            
        except Exception as e:
            self.logger.error(f"Error applying generic insights: {e}")
    
    def register_insight_handler(self, insight_type: str, handler: Callable):
        """Register a handler for a specific type of insight."""
        self.insight_handlers[insight_type] = handler
        self.logger.info(f"Registered insight handler for type: {insight_type}")
    
    def unregister_insight_handler(self, insight_type: str):
        """Unregister a handler for a specific type of insight."""
        if insight_type in self.insight_handlers:
            del self.insight_handlers[insight_type]
            self.logger.info(f"Unregistered insight handler for type: {insight_type}")
    
    async def get_received_insights(self, insight_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get received insights, optionally filtered by type."""
        if insight_type:
            return [
                insight for insight in self.received_insights.values()
                if insight.get('strand', {}).get('kind') == insight_type
            ]
        else:
            return list(self.received_insights.values())
    
    async def clear_old_insights(self, hours: int = 24):
        """Clear insights older than specified hours."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_timestamp = cutoff_time.isoformat()
        
        old_insights = [
            insight_id for insight_id, insight in self.received_insights.items()
            if insight.get('processed_at', '') < cutoff_timestamp
        ]
        
        for insight_id in old_insights:
            del self.received_insights[insight_id]
        
        self.logger.info(f"Cleared {len(old_insights)} old insights")
    
    def get_listener_summary(self) -> Dict[str, Any]:
        """Get summary of listener activity."""
        return {
            'active_listeners': len(self.active_listeners),
            'received_insights': len(self.received_insights),
            'registered_handlers': len(self.insight_handlers),
            'listener_tags': self.decision_maker_tags,
            'last_activity': datetime.now(timezone.utc).isoformat()
        }
