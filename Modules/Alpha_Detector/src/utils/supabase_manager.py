"""
Supabase client manager for Alpha Detector Module
Phase 1: Foundation - Database connection using Supabase client
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

class SupabaseManager:
    """Supabase client manager for Alpha Detector Module"""
    
    def __init__(self):
        # Load environment variables from the correct path
        # Go up from src/utils/supabase_manager.py to the project root
        # File structure: project_root/Modules/Alpha_Detector/src/utils/supabase_manager.py
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        env_path = os.path.join(project_root, '.env')
        load_dotenv(env_path)
        
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in environment variables")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        logger.info("Supabase client initialized")
    
    def test_connection(self) -> bool:
        """Test Supabase connection"""
        try:
            result = self.client.table('ad_strands').select('*').limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase connection test failed: {e}")
            return False
    
    def insert_strand(self, strand_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a strand into ad_strands table"""
        try:
            result = self.client.table('ad_strands').insert(strand_data).execute()
            if result.data:
                logger.info(f"Inserted strand: {result.data[0]['id']}")
                return result.data[0]
            else:
                raise Exception("No data returned from insert")
        except Exception as e:
            logger.error(f"Failed to insert strand: {e}")
            raise
    
    def get_strand_by_id(self, strand_id: str) -> Optional[Dict[str, Any]]:
        """Get a strand by ID"""
        try:
            result = self.client.table('ad_strands').select('*').eq('id', strand_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get strand {strand_id}: {e}")
            return None
    
    def get_recent_strands(self, limit: int = 100, days: int = 7, since: datetime = None) -> List[Dict[str, Any]]:
        """Get recent strands"""
        try:
            query = self.client.table('ad_strands').select('*')
            
            # Add date filtering if since parameter is provided
            if since:
                query = query.gte('created_at', since.isoformat())
            else:
                # Use days parameter as fallback
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
                query = query.gte('created_at', cutoff_date.isoformat())
            
            result = query.order('created_at', desc=True).limit(limit).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get recent strands: {e}")
            return []
    
    def get_strands_by_symbol(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get strands by symbol"""
        try:
            result = self.client.table('ad_strands').select('*').eq('symbol', symbol).order('created_at', desc=True).limit(limit).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get strands for symbol {symbol}: {e}")
            return []
    
    def get_strands_by_tags(self, tags: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """Get strands by tags"""
        try:
            # Note: This is a simplified version - you might want to use proper JSONB queries
            result = self.client.table('ad_strands').select('*').order('created_at', desc=True).limit(limit).execute()
            # Filter by tags in Python (not ideal for large datasets)
            filtered_data = [row for row in result.data if any(tag in row.get('tags', []) for tag in tags)]
            return filtered_data
        except Exception as e:
            logger.error(f"Failed to get strands by tags: {e}")
            return []
    
    def update_strand(self, strand_id: str, updates: Dict[str, Any]) -> bool:
        """Update a strand"""
        try:
            result = self.client.table('ad_strands').update(updates).eq('id', strand_id).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Failed to update strand {strand_id}: {e}")
            return False
    
    def delete_strand(self, strand_id: str) -> bool:
        """Delete a strand"""
        try:
            result = self.client.table('ad_strands').delete().eq('id', strand_id).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Failed to delete strand {strand_id}: {e}")
            return False
    
    async def execute_query(self, query: str, params: List[Any] = None) -> List[Dict[str, Any]]:
        """
        Execute a raw SQL query
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result rows as dictionaries
        """
        try:
            # For Supabase, we'll use the RPC (Remote Procedure Call) approach
            # or convert the query to use the Supabase client methods
            
            # For now, let's implement a simple version that handles basic SELECT queries
            if query.strip().upper().startswith('SELECT'):
                # Extract table name and basic query structure
                # This is a simplified implementation - in production you'd want more robust parsing
                
                # For the specific query used in InputProcessor, let's handle it directly
                if 'AD_strands' in query and 'agent_id IS NOT NULL' in query:
                    # This is the query from InputProcessor
                    cutoff_time = params[0] if params else None
                    
                    # Use Supabase client to get recent strands with agent_id
                    result = self.client.table('ad_strands').select(
                        'id, agent_id, kind, module_intelligence, sig_sigma, sig_confidence, '
                        'outcome_score, tags, created_at, symbol, timeframe, regime, session_bucket'
                    ).not_.is_('agent_id', 'null').gte('created_at', cutoff_time.isoformat() if cutoff_time else '').order('created_at', desc=True).execute()
                    
                    return result.data if result.data else []
                
                # Generic fallback - try to execute as RPC
                # Note: This would require setting up RPC functions in Supabase
                logger.warning(f"Generic query execution not fully implemented: {query}")
                return []
            
            else:
                logger.warning(f"Non-SELECT queries not supported: {query}")
                return []
                
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return []

# Global Supabase manager instance - removed to avoid import-time instantiation
