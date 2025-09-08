"""
Database connection and utilities for Alpha Detector Module
Phase 1: Foundation - Database setup and connection
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database manager for Alpha Detector Module"""
    
    def __init__(self):
        self.connection_params = self._get_connection_params()
        self.connection = None
    
    def _get_connection_params(self) -> Dict[str, str]:
        """Get database connection parameters from environment"""
        # Use the base Supabase URL as hostname
        supabase_url = os.getenv('SUPABASE_URL', '')
        if supabase_url:
            # Extract hostname from Supabase URL
            hostname = supabase_url.replace('https://', '').replace('http://', '')
        else:
            # Fallback to the known working hostname
            hostname = 'uanwkcczaakybpljxmym.supabase.co'
        
        return {
            'host': hostname,
            'port': '5432',
            'database': 'postgres',
            'user': 'postgres.uanwkcczaakybpljxmym',
            'password': os.getenv('SUPABASE_DB_PASSWORD'),
            'sslmode': 'require'
        }
    
    def connect(self):
        """Establish database connection"""
        try:
            # Try connection string format first
            connection_string = f"postgresql://{self.connection_params['user']}:{self.connection_params['password']}@{self.connection_params['host']}:{self.connection_params['port']}/{self.connection_params['database']}?sslmode=require"
            
            self.connection = psycopg2.connect(
                connection_string,
                cursor_factory=RealDictCursor
            )
            logger.info("Database connection established")
            return self.connection
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            # Try fallback to individual parameters
            try:
                self.connection = psycopg2.connect(
                    **self.connection_params,
                    cursor_factory=RealDictCursor
                )
                logger.info("Database connection established (fallback)")
                return self.connection
            except Exception as e2:
                logger.error(f"Database connection failed (fallback): {e2}")
                raise
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursor"""
        if not self.connection:
            self.connect()
        
        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_insert(self, query: str, params: tuple = None) -> str:
        """Execute an INSERT query and return the ID"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()['id'] if cursor.description else None
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute an UPDATE/DELETE query and return affected rows"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result[0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

class AlphaDetectorDB:
    """Alpha Detector specific database operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def insert_strand(self, strand_data: Dict[str, Any]) -> str:
        """Insert a strand into AD_strands table"""
        query = """
            INSERT INTO AD_strands (
                id, module, kind, symbol, timeframe, session_bucket, regime, tags,
                sig_sigma, sig_confidence, sig_direction, trading_plan, signal_pack,
                dsi_evidence, regime_context, event_context, module_intelligence, curator_feedback,
                accumulated_score, source_strands, clustering_columns, lesson, braid_level
            ) VALUES (
                %(id)s, %(module)s, %(kind)s, %(symbol)s, %(timeframe)s, %(session_bucket)s, %(regime)s, %(tags)s,
                %(sig_sigma)s, %(sig_confidence)s, %(sig_direction)s, %(trading_plan)s, %(signal_pack)s,
                %(dsi_evidence)s, %(regime_context)s, %(event_context)s, %(module_intelligence)s, %(curator_feedback)s,
                %(accumulated_score)s, %(source_strands)s, %(clustering_columns)s, %(lesson)s, %(braid_level)s
            ) RETURNING id
        """
        return self.db.execute_insert(query, strand_data)
    
    def get_strand_by_id(self, strand_id: str) -> Optional[Dict[str, Any]]:
        """Get a strand by ID"""
        query = "SELECT * FROM AD_strands WHERE id = %s"
        results = self.db.execute_query(query, (strand_id,))
        return results[0] if results else None
    
    def get_recent_strands(self, limit: int = 100, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent strands"""
        query = """
            SELECT * FROM AD_strands 
            WHERE created_at >= NOW() - INTERVAL '%s days'
            ORDER BY created_at DESC 
            LIMIT %s
        """
        return self.db.execute_query(query, (days, limit))
    
    def get_strands_by_symbol(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get strands by symbol"""
        query = """
            SELECT * FROM AD_strands 
            WHERE symbol = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        """
        return self.db.execute_query(query, (symbol, limit))
    
    def get_strands_by_tags(self, tags: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """Get strands by tags"""
        query = """
            SELECT * FROM AD_strands 
            WHERE tags @> %s
            ORDER BY created_at DESC 
            LIMIT %s
        """
        return self.db.execute_query(query, (tags, limit))
    
    def update_strand(self, strand_id: str, updates: Dict[str, Any]) -> bool:
        """Update a strand"""
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)
        
        values.append(strand_id)
        
        query = f"""
            UPDATE AD_strands 
            SET {', '.join(set_clauses)}, updated_at = NOW()
            WHERE id = %s
        """
        
        affected_rows = self.db.execute_update(query, tuple(values))
        return affected_rows > 0
    
    def delete_strand(self, strand_id: str) -> bool:
        """Delete a strand"""
        query = "DELETE FROM AD_strands WHERE id = %s"
        affected_rows = self.db.execute_update(query, (strand_id,))
        return affected_rows > 0

# Global database manager instance
db_manager = DatabaseManager()
alpha_db = AlphaDetectorDB(db_manager)
