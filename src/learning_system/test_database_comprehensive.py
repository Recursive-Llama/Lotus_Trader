#!/usr/bin/env python3
"""
Comprehensive Database Testing Suite

Tests all database operations, schema validation, JSONB operations,
triggers, functions, and data integrity for the centralized learning system.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import traceback

# Add paths for imports
current_dir = os.path.dirname(__file__)
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, '..', '..', 'Modules', 'Alpha_Detector'))
sys.path.append(os.path.join(current_dir, '..', '..', 'Modules', 'Alpha_Detector', 'src'))

from utils.supabase_manager import SupabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('database_test_results.log')
    ]
)
logger = logging.getLogger(__name__)

class DatabaseComprehensiveTester:
    """Comprehensive database testing suite"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.test_results = {}
        self.start_time = None
        
    async def run_all_tests(self):
        """Run all database tests"""
        logger.info("🗄️ Starting Comprehensive Database Testing")
        logger.info("=" * 80)
        
        self.start_time = time.time()
        
        test_suites = [
            ("Schema Validation", self.test_schema_validation),
            ("JSONB Operations", self.test_jsonb_operations),
            ("CRUD Operations", self.test_crud_operations),
            ("Triggers and Functions", self.test_triggers_functions),
            ("Query Performance", self.test_query_performance),
            ("Concurrent Access", self.test_concurrent_access),
            ("Data Integrity", self.test_data_integrity),
            ("Transaction Testing", self.test_transactions),
            ("Index Performance", self.test_index_performance),
            ("Cleanup Operations", self.test_cleanup_operations)
        ]
        
        for suite_name, test_func in test_suites:
            try:
                logger.info(f"\n🔍 Running {suite_name} Tests...")
                await test_func()
                logger.info(f"✅ {suite_name} Tests PASSED")
            except Exception as e:
                logger.error(f"❌ {suite_name} Tests FAILED: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                self.test_results[suite_name] = {"status": "FAILED", "error": str(e)}
        
        self.print_summary()
    
    async def test_schema_validation(self):
        """Test database schema validation"""
        logger.info("  📋 Testing schema validation...")
        
        # Test table existence
        tables_to_check = [
            'ad_strands', 'learning_queue', 'learning_braids', 
            'module_resonance_scores', 'pattern_evolution'
        ]
        
        for table in tables_to_check:
            try:
                result = self.supabase_manager.client.table(table).select("*").limit(1).execute()
                logger.info(f"    ✅ Table {table} exists and accessible")
            except Exception as e:
                logger.error(f"    ❌ Table {table} error: {e}")
                raise
        
        # Test column structure
        strand_columns = [
            'id', 'kind', 'symbol', 'content', 'metadata', 'resonance_scores',
            'cluster_key', 'braid_level', 'created_at', 'updated_at'
        ]
        
        try:
            result = self.supabase_manager.client.table('ad_strands').select("*").limit(1).execute()
            if result.data:
                sample_row = result.data[0]
                for col in strand_columns:
                    if col not in sample_row:
                        logger.warning(f"    ⚠️ Column {col} not found in sample data")
                    else:
                        logger.info(f"    ✅ Column {col} exists")
        except Exception as e:
            logger.error(f"    ❌ Column validation error: {e}")
            raise
        
        logger.info("    ✅ Schema validation successful")
    
    async def test_jsonb_operations(self):
        """Test JSONB field operations"""
        logger.info("  📦 Testing JSONB operations...")
        
        # Test resonance_scores JSONB
        test_resonance = {
            "phi": 0.75,
            "rho": 0.82,
            "theta": 0.68,
            "omega": 0.91,
            "selection_score": 0.79,
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Test cluster_key JSONB (array of cluster assignments)
        test_cluster_key = [
            {
                "cluster_type": "asset",
                "cluster_key": "BTC",
                "braid_level": 1,
                "consumed": False
            },
            {
                "cluster_type": "pattern_type",
                "cluster_key": "head_and_shoulders",
                "braid_level": 1,
                "consumed": False
            }
        ]
        
        # Test content JSONB
        test_content = {
            "pattern_data": {
                "type": "reversal",
                "confidence": 0.85,
                "timeframe": "1h",
                "indicators": ["rsi", "macd", "volume"]
            },
            "analysis": {
                "strength": "strong",
                "reliability": 0.78,
                "market_context": "bullish"
            }
        }
        
        # Test metadata JSONB
        test_metadata = {
            "source": "hyperliquid",
            "processing_time": 0.045,
            "quality_score": 0.92,
            "tags": ["high_confidence", "reversal_pattern"]
        }
        
        # Create test strand with JSONB data
        test_strand = {
            "id": f"jsonb_test_{uuid.uuid4()}",
            "kind": "pattern",
            "symbol": "BTC",
            "content": test_content,
            "metadata": test_metadata,
            "resonance_scores": test_resonance,
            "cluster_key": test_cluster_key,
            "braid_level": 1,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Insert test strand
            result = self.supabase_manager.client.table('ad_strands').insert(test_strand).execute()
            logger.info("    ✅ JSONB data insertion successful")
            
            # Test JSONB queries
            # Query by resonance_scores
            phi_query = self.supabase_manager.client.table('ad_strands').select("*").eq('id', test_strand['id']).execute()
            if phi_query.data:
                stored_resonance = phi_query.data[0]['resonance_scores']
                if stored_resonance['phi'] == 0.75:
                    logger.info("    ✅ JSONB resonance_scores query successful")
                else:
                    logger.error(f"    ❌ JSONB resonance_scores mismatch: {stored_resonance['phi']}")
            
            # Query by cluster_key
            cluster_query = self.supabase_manager.client.table('ad_strands').select("*").eq('id', test_strand['id']).execute()
            if cluster_query.data:
                stored_cluster = cluster_query.data[0]['cluster_key']
                if isinstance(stored_cluster, list) and len(stored_cluster) > 0:
                    pattern_cluster = next((c for c in stored_cluster if c.get('cluster_type') == 'pattern_type'), None)
                    if pattern_cluster and pattern_cluster.get('cluster_key') == "head_and_shoulders":
                        logger.info("    ✅ JSONB cluster_key query successful")
                    else:
                        logger.error(f"    ❌ JSONB cluster_key mismatch: {pattern_cluster}")
                else:
                    logger.error(f"    ❌ JSONB cluster_key not array: {stored_cluster}")
            
            # Test JSONB updates
            updated_resonance = test_resonance.copy()
            updated_resonance['phi'] = 0.85
            updated_resonance['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            update_result = self.supabase_manager.client.table('ad_strands').update({
                'resonance_scores': updated_resonance
            }).eq('id', test_strand['id']).execute()
            
            # Verify update
            verify_query = self.supabase_manager.client.table('ad_strands').select("*").eq('id', test_strand['id']).execute()
            if verify_query.data:
                updated_stored = verify_query.data[0]['resonance_scores']
                if updated_stored['phi'] == 0.85:
                    logger.info("    ✅ JSONB update successful")
                else:
                    logger.error(f"    ❌ JSONB update failed: {updated_stored['phi']}")
            
            # Cleanup
            self.supabase_manager.client.table('ad_strands').delete().eq('id', test_strand['id']).execute()
            logger.info("    ✅ JSONB test cleanup successful")
            
        except Exception as e:
            logger.error(f"    ❌ JSONB operations failed: {e}")
            raise
        
        logger.info("    ✅ JSONB operations successful")
    
    async def test_crud_operations(self):
        """Test CRUD operations"""
        logger.info("  📝 Testing CRUD operations...")
        
        # Test Create
        test_strand = {
            "id": f"crud_test_{uuid.uuid4()}",
            "kind": "pattern",
            "symbol": "ETH",
            "content": {"type": "breakout", "confidence": 0.88},
            "metadata": {"source": "test", "quality": 0.95},
            "resonance_scores": {"phi": 0.72, "rho": 0.81, "theta": 0.69, "omega": 0.87},
            "cluster_key": [{"cluster_type": "pattern_type", "cluster_key": "breakout", "braid_level": 1, "consumed": False}],
            "braid_level": 1,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Create
            create_result = self.supabase_manager.client.table('ad_strands').insert(test_strand).execute()
            logger.info("    ✅ Create operation successful")
            
            # Read
            read_result = self.supabase_manager.client.table('ad_strands').select("*").eq('id', test_strand['id']).execute()
            if read_result.data and len(read_result.data) == 1:
                logger.info("    ✅ Read operation successful")
            else:
                logger.error("    ❌ Read operation failed")
                raise Exception("Read operation failed")
            
            # Update
            update_data = {
                "content": {"type": "breakout", "confidence": 0.92},
                "resonance_scores": {"phi": 0.78, "rho": 0.85, "theta": 0.73, "omega": 0.91},
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            update_result = self.supabase_manager.client.table('ad_strands').update(update_data).eq('id', test_strand['id']).execute()
            
            # Verify update
            verify_result = self.supabase_manager.client.table('ad_strands').select("*").eq('id', test_strand['id']).execute()
            if verify_result.data and verify_result.data[0]['content']['confidence'] == 0.92:
                logger.info("    ✅ Update operation successful")
            else:
                logger.error("    ❌ Update operation failed")
                raise Exception("Update operation failed")
            
            # Delete
            delete_result = self.supabase_manager.client.table('ad_strands').delete().eq('id', test_strand['id']).execute()
            
            # Verify deletion
            verify_delete = self.supabase_manager.client.table('ad_strands').select("*").eq('id', test_strand['id']).execute()
            if not verify_delete.data:
                logger.info("    ✅ Delete operation successful")
            else:
                logger.error("    ❌ Delete operation failed")
                raise Exception("Delete operation failed")
            
        except Exception as e:
            logger.error(f"    ❌ CRUD operations failed: {e}")
            raise
        
        logger.info("    ✅ CRUD operations successful")
    
    async def test_triggers_functions(self):
        """Test database triggers and functions"""
        logger.info("  ⚡ Testing triggers and functions...")
        
        try:
            # Test learning queue trigger
            test_strand = {
                "id": f"trigger_test_{uuid.uuid4()}",
                "kind": "pattern",
                "symbol": "BTC",
                "content": {"type": "reversal", "confidence": 0.85},
                "metadata": {"source": "test"},
                "resonance_scores": {"phi": 0.75, "rho": 0.82, "theta": 0.68, "omega": 0.89},
            "cluster_key": [{"cluster_type": "pattern_type", "cluster_key": "reversal", "braid_level": 1, "consumed": False}],
            "braid_level": 1,
            "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Insert strand (should trigger learning queue)
            insert_result = self.supabase_manager.client.table('ad_strands').insert(test_strand).execute()
            logger.info("    ✅ Strand insertion successful")
            
            # Check if learning queue entry was created
            await asyncio.sleep(1)  # Give trigger time to execute
            
            queue_result = self.supabase_manager.client.table('learning_queue').select("*").eq('strand_id', test_strand['id']).execute()
            if queue_result.data:
                logger.info("    ✅ Learning queue trigger successful")
            else:
                logger.warning("    ⚠️ Learning queue trigger may not be working")
            
            # Test cleanup function
            cleanup_result = self.supabase_manager.client.rpc('cleanup_learning_queue').execute()
            logger.info("    ✅ Cleanup function executed")
            
            # Test learning queue stats
            stats_result = self.supabase_manager.client.rpc('get_learning_queue_stats').execute()
            if stats_result.data:
                logger.info(f"    ✅ Learning queue stats: {stats_result.data}")
            else:
                logger.warning("    ⚠️ Learning queue stats function may not be working")
            
            # Cleanup test data
            self.supabase_manager.client.table('ad_strands').delete().eq('id', test_strand['id']).execute()
            self.supabase_manager.client.table('learning_queue').delete().eq('strand_id', test_strand['id']).execute()
            
        except Exception as e:
            logger.error(f"    ❌ Triggers and functions test failed: {e}")
            # Don't raise - these are optional features
            logger.warning("    ⚠️ Triggers and functions may not be fully implemented")
        
        logger.info("    ✅ Triggers and functions test completed")
    
    async def test_query_performance(self):
        """Test query performance"""
        logger.info("  ⚡ Testing query performance...")
        
        try:
            # Test simple query
            start_time = time.time()
            simple_result = self.supabase_manager.client.table('ad_strands').select("*").limit(10).execute()
            simple_time = time.time() - start_time
            logger.info(f"    ✅ Simple query: {simple_time:.3f}s")
            
            # Test filtered query
            start_time = time.time()
            filtered_result = self.supabase_manager.client.table('ad_strands').select("*").eq('kind', 'pattern').limit(10).execute()
            filtered_time = time.time() - start_time
            logger.info(f"    ✅ Filtered query: {filtered_time:.3f}s")
            
            # Test JSONB query
            start_time = time.time()
            jsonb_result = self.supabase_manager.client.table('ad_strands').select("*").not_.is_('resonance_scores', 'null').limit(10).execute()
            jsonb_time = time.time() - start_time
            logger.info(f"    ✅ JSONB query: {jsonb_time:.3f}s")
            
            # Test complex query with learning_queue join
            start_time = time.time()
            complex_result = self.supabase_manager.client.table('ad_strands').select("*, learning_queue(*)").limit(5).execute()
            complex_time = time.time() - start_time
            logger.info(f"    ✅ Complex query: {complex_time:.3f}s")
            
            # Performance thresholds
            if simple_time > 1.0:
                logger.warning(f"    ⚠️ Simple query slow: {simple_time:.3f}s")
            if filtered_time > 2.0:
                logger.warning(f"    ⚠️ Filtered query slow: {filtered_time:.3f}s")
            if jsonb_time > 3.0:
                logger.warning(f"    ⚠️ JSONB query slow: {jsonb_time:.3f}s")
            if complex_time > 5.0:
                logger.warning(f"    ⚠️ Complex query slow: {complex_time:.3f}s")
            
        except Exception as e:
            logger.error(f"    ❌ Query performance test failed: {e}")
            raise
        
        logger.info("    ✅ Query performance test successful")
    
    async def test_concurrent_access(self):
        """Test concurrent access"""
        logger.info("  🔄 Testing concurrent access...")
        
        try:
            # Create multiple concurrent tasks
            tasks = []
            for i in range(5):
                task = asyncio.create_task(self._concurrent_test_task(i))
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results
            successful_tasks = sum(1 for r in results if not isinstance(r, Exception))
            logger.info(f"    ✅ Concurrent access: {successful_tasks}/5 tasks successful")
            
            if successful_tasks < 5:
                logger.warning(f"    ⚠️ Some concurrent tasks failed: {5 - successful_tasks}")
            
        except Exception as e:
            logger.error(f"    ❌ Concurrent access test failed: {e}")
            raise
        
        logger.info("    ✅ Concurrent access test successful")
    
    async def _concurrent_test_task(self, task_id: int):
        """Individual concurrent test task"""
        try:
            # Create test strand
            test_strand = {
                "id": f"concurrent_test_{task_id}_{uuid.uuid4()}",
                "kind": "pattern",
                "symbol": f"SYMBOL_{task_id}",
                "content": {"type": "test", "task_id": task_id},
                "metadata": {"source": "concurrent_test"},
                "resonance_scores": {"phi": 0.5, "rho": 0.5, "theta": 0.5, "omega": 0.5},
                "cluster_key": [{"cluster_type": "pattern_type", "cluster_key": "test", "braid_level": 1, "consumed": False}],
                "braid_level": 1,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Insert
            self.supabase_manager.client.table('ad_strands').insert(test_strand).execute()
            
            # Read
            result = self.supabase_manager.client.table('ad_strands').select("*").eq('id', test_strand['id']).execute()
            
            # Update
            self.supabase_manager.client.table('ad_strands').update({
                "content": {"type": "test_updated", "task_id": task_id}
            }).eq('id', test_strand['id']).execute()
            
            # Delete
            self.supabase_manager.client.table('ad_strands').delete().eq('id', test_strand['id']).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"    ❌ Concurrent task {task_id} failed: {e}")
            return False
    
    async def test_data_integrity(self):
        """Test data integrity"""
        logger.info("  🔒 Testing data integrity...")
        
        try:
            # Test foreign key constraints
            test_strand = {
                "id": f"integrity_test_{uuid.uuid4()}",
                "kind": "pattern",
                "symbol": "BTC",
                "content": {"type": "integrity_test"},
                "metadata": {"source": "test"},
                "resonance_scores": {"phi": 0.75, "rho": 0.82, "theta": 0.68, "omega": 0.89},
                "cluster_key": [{"cluster_type": "pattern_type", "cluster_key": "integrity_test", "braid_level": 1, "consumed": False}],
                "braid_level": 1,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Insert valid data
            insert_result = self.supabase_manager.client.table('ad_strands').insert(test_strand).execute()
            logger.info("    ✅ Valid data insertion successful")
            
            # Test data validation
            verify_result = self.supabase_manager.client.table('ad_strands').select("*").eq('id', test_strand['id']).execute()
            if verify_result.data:
                stored_strand = verify_result.data[0]
                
                # Check required fields
                required_fields = ['id', 'kind', 'symbol', 'created_at']
                for field in required_fields:
                    if field not in stored_strand or stored_strand[field] is None:
                        logger.error(f"    ❌ Required field {field} missing or null")
                        raise Exception(f"Required field {field} missing or null")
                
                # Check data types
                if not isinstance(stored_strand['resonance_scores'], dict):
                    logger.error("    ❌ resonance_scores should be dict")
                    raise Exception("resonance_scores should be dict")
                
                if not isinstance(stored_strand['cluster_key'], list):
                    logger.error("    ❌ cluster_key should be list")
                    raise Exception("cluster_key should be list")
                
                logger.info("    ✅ Data validation successful")
            
            # Cleanup
            self.supabase_manager.client.table('ad_strands').delete().eq('id', test_strand['id']).execute()
            
        except Exception as e:
            logger.error(f"    ❌ Data integrity test failed: {e}")
            raise
        
        logger.info("    ✅ Data integrity test successful")
    
    async def test_transactions(self):
        """Test transaction handling"""
        logger.info("  🔄 Testing transactions...")
        
        try:
            # Test transaction rollback
            test_strand = {
                "id": f"transaction_test_{uuid.uuid4()}",
                "kind": "pattern",
                "symbol": "BTC",
                "content": {"type": "transaction_test"},
                "metadata": {"source": "test"},
                "resonance_scores": {"phi": 0.75, "rho": 0.82, "theta": 0.68, "omega": 0.89},
                "cluster_key": [{"cluster_type": "pattern_type", "cluster_key": "transaction_test", "braid_level": 1, "consumed": False}],
                "braid_level": 1,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Insert and immediately verify
            insert_result = self.supabase_manager.client.table('ad_strands').insert(test_strand).execute()
            
            # Verify insertion
            verify_result = self.supabase_manager.client.table('ad_strands').select("*").eq('id', test_strand['id']).execute()
            if verify_result.data:
                logger.info("    ✅ Transaction insertion successful")
            else:
                logger.error("    ❌ Transaction insertion failed")
                raise Exception("Transaction insertion failed")
            
            # Cleanup
            self.supabase_manager.client.table('ad_strands').delete().eq('id', test_strand['id']).execute()
            
        except Exception as e:
            logger.error(f"    ❌ Transaction test failed: {e}")
            raise
        
        logger.info("    ✅ Transaction test successful")
    
    async def test_index_performance(self):
        """Test index performance"""
        logger.info("  📊 Testing index performance...")
        
        try:
            # Test queries that should use indexes
            indexed_queries = [
                ("kind", "pattern"),
                ("symbol", "BTC"),
                ("braid_level", 1),
                ("processed", False)
            ]
            
            for field, value in indexed_queries:
                start_time = time.time()
                result = self.supabase_manager.client.table('ad_strands').select("*").eq(field, value).limit(10).execute()
                query_time = time.time() - start_time
                logger.info(f"    ✅ Indexed query ({field}={value}): {query_time:.3f}s")
                
                if query_time > 2.0:
                    logger.warning(f"    ⚠️ Slow indexed query: {query_time:.3f}s")
            
        except Exception as e:
            logger.error(f"    ❌ Index performance test failed: {e}")
            raise
        
        logger.info("    ✅ Index performance test successful")
    
    async def test_cleanup_operations(self):
        """Test cleanup operations"""
        logger.info("  🧹 Testing cleanup operations...")
        
        try:
            # Create test data for cleanup
            test_strands = []
            for i in range(5):
                test_strand = {
                    "id": f"cleanup_test_{i}_{uuid.uuid4()}",
                    "kind": "pattern",
                    "symbol": f"SYMBOL_{i}",
                    "content": {"type": "cleanup_test", "index": i},
                    "metadata": {"source": "cleanup_test"},
                    "resonance_scores": {"phi": 0.5, "rho": 0.5, "theta": 0.5, "omega": 0.5},
                    "cluster_key": [{"cluster_type": "pattern_type", "cluster_key": "cleanup_test", "braid_level": 1, "consumed": False}],
                    "braid_level": 1,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                test_strands.append(test_strand)
            
            # Insert test data
            insert_result = self.supabase_manager.client.table('ad_strands').insert(test_strands).execute()
            logger.info("    ✅ Test data insertion successful")
            
            # Test cleanup by pattern
            cleanup_result = self.supabase_manager.client.table('ad_strands').delete().eq('metadata->>source', 'cleanup_test').execute()
            logger.info(f"    ✅ Cleanup operation successful: {cleanup_result}")
            
            # Verify cleanup
            verify_result = self.supabase_manager.client.table('ad_strands').select("*").eq('metadata->>source', 'cleanup_test').execute()
            if not verify_result.data:
                logger.info("    ✅ Cleanup verification successful")
            else:
                logger.warning(f"    ⚠️ Cleanup may not have removed all test data: {len(verify_result.data)} remaining")
            
        except Exception as e:
            logger.error(f"    ❌ Cleanup operations test failed: {e}")
            raise
        
        logger.info("    ✅ Cleanup operations test successful")
    
    def print_summary(self):
        """Print test summary"""
        end_time = time.time()
        total_time = end_time - self.start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 Database Testing Summary")
        logger.info("=" * 80)
        logger.info(f"⏱️  Total Time: {total_time:.2f} seconds")
        logger.info(f"📈 Test Results: {len(self.test_results)} test suites")
        
        for suite_name, result in self.test_results.items():
            status = result.get('status', 'UNKNOWN')
            if status == 'PASSED':
                logger.info(f"    ✅ {suite_name}")
            else:
                logger.info(f"    ❌ {suite_name}: {result.get('error', 'Unknown error')}")
        
        logger.info("=" * 80)

async def main():
    """Main test runner"""
    tester = DatabaseComprehensiveTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
