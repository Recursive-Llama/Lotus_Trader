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
        # File structure: project_root/src/utils/supabase_manager.py
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
    
    def get_strands_by_type(self, strand_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get strands by type (kind)"""
        try:
            result = self.client.table('ad_strands').select('*').eq('kind', strand_type).order('created_at', desc=True).limit(limit).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get strands by type {strand_type}: {e}")
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
    
    def get_braids_by_strand_types(self, strand_types: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """Get braids by strand types"""
        try:
            result = self.client.table('ad_braids').select('*').order('created_at', desc=True).limit(limit).execute()
            # Filter by strand types in Python
            filtered_data = [row for row in result.data if any(st in row.get('strand_types', []) for st in strand_types)]
            return filtered_data
        except Exception as e:
            logger.error(f"Failed to get braids by strand types: {e}")
            return []
    
    def insert_braid(self, braid_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a braid into ad_braids table"""
        try:
            result = self.client.table('ad_braids').insert(braid_data).execute()
            if result.data:
                logger.info(f"Inserted braid: {result.data[0]['id']}")
                return result.data[0]
            else:
                raise Exception("No data returned from braid insert")
        except Exception as e:
            logger.error(f"Failed to insert braid: {e}")
            raise
    
    def execute_query(self, query: str) -> Any:
        """Execute a raw SQL query"""
        try:
            # Use direct table access instead of RPC
            if "SELECT 1" in query.upper():
                # Simple test query
                result = self.client.table('ad_strands').select('id').limit(1).execute()
                return result.data
            else:
                # For other queries, try RPC but fallback to table access
                try:
                    result = self.client.rpc('execute_sql', {'query': query}).execute()
                    return result.data
                except:
                    # Fallback to table access
                    logger.warning(f"RPC failed, using fallback for query: {query}")
                    return None
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return None
    
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
        Execute a raw SQL query using Supabase RPC or fallback methods
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of result rows as dictionaries
        """
        try:
            import json
            
            # Clean up the query
            cleaned_query = query.strip()
            params = params or []
            
            # Convert params to JSONB format for RPC functions
            # The RPC function expects a JSONB array, not a JSON string
            params_jsonb = params  # Send as Python list, Supabase will convert to JSONB
            
            # Try RPC approach first
            try:
                if cleaned_query.upper().startswith('SELECT'):
                    result = self.client.rpc('execute_select_query', {
                        'query_text': cleaned_query,
                        'query_params': params_jsonb
                    }).execute()
                    return result.data if result.data else []
                    
                elif cleaned_query.upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                    result = self.client.rpc('execute_modify_query', {
                        'query_text': cleaned_query,
                        'query_params': params_jsonb
                    }).execute()
                    return result.data if result.data else []
                    
            except Exception as rpc_error:
                logger.warning(f"RPC approach failed, trying fallback: {rpc_error}")
                # Fall through to fallback methods
            
            # Fallback: Convert common queries to Supabase client methods
            return await self._execute_query_fallback(cleaned_query, params)
                
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return []
    
    async def _execute_query_fallback(self, query: str, params: List[Any]) -> List[Dict[str, Any]]:
        """Fallback method to execute queries using Supabase client methods"""
        
        try:
            # Handle specific query patterns we know we need
            if 'AD_strands' in query and 'kind =' in query:
                # Extract kind from query
                kind_match = None
                if "'prediction_review'" in query:
                    kind_match = 'prediction_review'
                elif "'pattern'" in query:
                    kind_match = 'pattern'
                elif "'braid'" in query:
                    kind_match = 'braid'
                elif "'learning_braid'" in query:
                    kind_match = 'learning_braid'
                
                if kind_match:
                    # Build Supabase query
                    supabase_query = self.client.table('ad_strands').select('*').eq('kind', kind_match)
                    
                    # Add additional filters based on query content
                    if 'content->>' in query:
                        # Handle JSONB field filters
                        if 'asset' in query and params:
                            supabase_query = supabase_query.eq('content->>asset', params[0])
                        elif 'group_signature' in query and params:
                            supabase_query = supabase_query.eq('content->>group_signature', params[0])
                        elif 'success' in query and params:
                            supabase_query = supabase_query.eq('content->>success', params[0])
                        elif 'timeframe' in query and params:
                            supabase_query = supabase_query.eq('content->>timeframe', params[0])
                        elif 'group_type' in query and params:
                            supabase_query = supabase_query.eq('content->>group_type', params[0])
                        elif 'method' in query and params:
                            supabase_query = supabase_query.eq('content->>method', params[0])
                    
                    # Add ordering
                    if 'ORDER BY' in query:
                        if 'created_at DESC' in query:
                            supabase_query = supabase_query.order('created_at', desc=True)
                        elif 'created_at ASC' in query:
                            supabase_query = supabase_query.order('created_at', desc=False)
                    
                    # Add limit
                    if 'LIMIT' in query:
                        limit_match = None
                        import re
                        limit_match = re.search(r'LIMIT\s+(\d+)', query)
                        if limit_match:
                            supabase_query = supabase_query.limit(int(limit_match.group(1)))
                    
                    result = supabase_query.execute()
                    return result.data if result.data else []
            
            # Handle COUNT queries
            elif query.upper().startswith('SELECT COUNT'):
                if 'AD_strands' in query and 'kind =' in query:
                    kind_match = None
                    if "'prediction_review'" in query:
                        kind_match = 'prediction_review'
                    elif "'braid'" in query:
                        kind_match = 'braid'
                    elif "'learning_braid'" in query:
                        kind_match = 'learning_braid'
                    
                    if kind_match:
                        result = self.client.table('ad_strands').select('*', count='exact').eq('kind', kind_match).execute()
                        return [{'count': result.count}] if result.count is not None else [{'count': 0}]
            
            # Handle INSERT queries
            elif query.upper().startswith('INSERT INTO AD_strands'):
                # Extract values from INSERT query
                import re
                values_match = re.search(r'VALUES\s*\((.*?)\)', query, re.DOTALL)
                if values_match and params:
                    # This is a simplified approach - in practice you'd want more robust parsing
                    strand_data = {
                        'id': params[0] if len(params) > 0 else None,
                        'kind': params[1] if len(params) > 1 else None,
                        'created_at': params[2] if len(params) > 2 else None,
                        'tags': params[3] if len(params) > 3 else None,
                        'content': params[4] if len(params) > 4 else None,
                        'metadata': params[5] if len(params) > 5 else None
                    }
                    
                    result = self.client.table('ad_strands').insert(strand_data).execute()
                    return result.data if result.data else []
            
            # Generic fallback - return empty result
            logger.warning(f"Query not supported in fallback: {query[:100]}...")
            return []
            
        except Exception as e:
            logger.error(f"Error in query fallback: {e}")
            return []

# Global Supabase manager instance - removed to avoid import-time instantiation
