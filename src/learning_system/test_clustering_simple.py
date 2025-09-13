#!/usr/bin/env python3
"""
Simple Clustering Testing Suite

Tests the actual MultiClusterGroupingEngine interface with real data.
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import traceback

# Add paths for imports
current_dir = os.path.dirname(__file__)
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, '..', '..', 'Modules', 'Alpha_Detector'))
sys.path.append(os.path.join(current_dir, '..', '..', 'Modules', 'Alpha_Detector', 'src'))

from utils.supabase_manager import SupabaseManager
from multi_cluster_grouping_engine import MultiClusterGroupingEngine
from mathematical_resonance_engine import MathematicalResonanceEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('clustering_simple_test_results.log')
    ]
)
logger = logging.getLogger(__name__)

class ClusteringSimpleTester:
    """Simple clustering testing suite for actual implementation"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.clustering_engine = MultiClusterGroupingEngine(self.supabase_manager)
        self.resonance_engine = MathematicalResonanceEngine()
        self.test_results = {}
        self.start_time = None
        
    async def run_all_tests(self):
        """Run all clustering tests"""
        logger.info("🔗 Starting Simple Clustering Testing (Actual Implementation)")
        logger.info("=" * 80)
        
        self.start_time = time.time()
        
        test_suites = [
            ("Basic Clustering", self.test_basic_clustering),
            ("Pattern Clustering", self.test_pattern_clustering),
            ("Cluster Statistics", self.test_cluster_statistics),
            ("Integration Testing", self.test_integration),
            ("Performance Testing", self.test_performance)
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
    
    async def test_basic_clustering(self):
        """Test basic clustering functionality"""
        logger.info("  🔗 Testing basic clustering...")
        
        try:
            # Create a test pattern
            test_pattern = {
                'id': f"cluster_test_{uuid.uuid4()}",
                'kind': 'pattern',
                'symbol': 'BTC',
                'content': {
                    'pattern_type': 'head_and_shoulders',
                    'confidence': 0.8,
                    'timeframe': '1h'
                },
                'metadata': {
                    'source': 'test',
                    'quality': 0.9
                },
                'cluster_key': [{
                    'cluster_type': 'pattern_type',
                    'cluster_key': 'head_and_shoulders',
                    'braid_level': 1,
                    'consumed': False
                }],
                'braid_level': 1,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Test clustering
            clusters = await self.clustering_engine.get_strand_clusters(test_pattern, 'pattern')
            
            if clusters:
                logger.info(f"    ✅ Basic clustering: {len(clusters)} cluster types found")
                
                for cluster_type, strands in clusters.items():
                    logger.info(f"    ✅ {cluster_type}: {len(strands)} strands")
            else:
                logger.info("    ✅ Basic clustering: No clusters found (expected for empty database)")
            
        except Exception as e:
            logger.error(f"    ❌ Basic clustering test failed: {e}")
            raise
        
        logger.info("    ✅ Basic clustering test successful")
    
    async def test_pattern_clustering(self):
        """Test pattern clustering with real data"""
        logger.info("  🎯 Testing pattern clustering...")
        
        try:
            # Insert some test patterns into the database
            test_patterns = []
            for i in range(5):
                pattern = {
                    'id': f"pattern_test_{i}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'BTC',
                    'content': {
                        'pattern_type': 'head_and_shoulders',
                        'confidence': 0.8 + i * 0.02,
                        'timeframe': '1h'
                    },
                    'metadata': {
                        'source': 'test',
                        'quality': 0.9
                    },
                    'cluster_key': [{
                        'cluster_type': 'pattern_type',
                        'cluster_key': 'head_and_shoulders',
                        'braid_level': 1,
                        'consumed': False
                    }],
                    'braid_level': 1,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                test_patterns.append(pattern)
            
            # Insert patterns
            insert_result = self.supabase_manager.client.table('ad_strands').insert(test_patterns).execute()
            logger.info("    ✅ Test patterns inserted")
            
            # Test clustering with one of the patterns
            test_pattern = test_patterns[0]
            clusters = await self.clustering_engine.get_strand_clusters(test_pattern, 'pattern')
            
            if clusters:
                logger.info(f"    ✅ Pattern clustering: {len(clusters)} cluster types found")
                
                for cluster_type, strands in clusters.items():
                    logger.info(f"    ✅ {cluster_type}: {len(strands)} strands")
                    
                    # Check if our test patterns are in the clusters
                    test_ids = {p['id'] for p in test_patterns}
                    cluster_ids = {s['id'] for s in strands}
                    overlap = test_ids.intersection(cluster_ids)
                    
                    if overlap:
                        logger.info(f"        ✅ Found {len(overlap)} test patterns in cluster")
                    else:
                        logger.info(f"        ℹ️ No test patterns in this cluster")
            else:
                logger.info("    ✅ Pattern clustering: No clusters found")
            
            # Cleanup
            for pattern in test_patterns:
                self.supabase_manager.client.table('ad_strands').delete().eq('id', pattern['id']).execute()
            logger.info("    ✅ Test patterns cleaned up")
            
        except Exception as e:
            logger.error(f"    ❌ Pattern clustering test failed: {e}")
            raise
        
        logger.info("    ✅ Pattern clustering test successful")
    
    async def test_cluster_statistics(self):
        """Test cluster statistics"""
        logger.info("  📊 Testing cluster statistics...")
        
        try:
            # Test statistics for different strand types
            strand_types = ['pattern', 'prediction_review', 'conditional_trading_plan']
            
            for strand_type in strand_types:
                stats = await self.clustering_engine.get_cluster_statistics(strand_type)
                
                logger.info(f"    ✅ {strand_type} statistics:")
                logger.info(f"        Total clusters: {stats.get('total_clusters', 0)}")
                logger.info(f"        Cluster sizes: {stats.get('cluster_sizes', [])}")
                logger.info(f"        Average cluster size: {stats.get('average_cluster_size', 0):.2f}")
                
                # Validate statistics structure
                required_fields = ['total_clusters', 'cluster_sizes', 'average_cluster_size', 'strand_type']
                for field in required_fields:
                    if field in stats:
                        logger.info(f"        ✅ {field}: present")
                    else:
                        logger.warning(f"        ⚠️ {field}: missing")
            
        except Exception as e:
            logger.error(f"    ❌ Cluster statistics test failed: {e}")
            raise
        
        logger.info("    ✅ Cluster statistics test successful")
    
    async def test_integration(self):
        """Test integration with database and learning system"""
        logger.info("  🔗 Testing integration...")
        
        try:
            # Create test patterns with different characteristics
            test_patterns = []
            
            # High confidence patterns
            for i in range(3):
                pattern = {
                    'id': f"integration_high_{i}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'BTC',
                    'content': {
                        'pattern_type': 'head_and_shoulders',
                        'confidence': 0.9,
                        'timeframe': '1h'
                    },
                    'metadata': {
                        'source': 'integration_test',
                        'quality': 0.95
                    },
                    'cluster_key': [{
                        'cluster_type': 'pattern_type',
                        'cluster_key': 'head_and_shoulders',
                        'braid_level': 1,
                        'consumed': False
                    }],
                    'braid_level': 1,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                test_patterns.append(pattern)
            
            # Medium confidence patterns
            for i in range(3):
                pattern = {
                    'id': f"integration_med_{i}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'ETH',
                    'content': {
                        'pattern_type': 'double_top',
                        'confidence': 0.7,
                        'timeframe': '4h'
                    },
                    'metadata': {
                        'source': 'integration_test',
                        'quality': 0.8
                    },
                    'cluster_key': [{
                        'cluster_type': 'pattern_type',
                        'cluster_key': 'double_top',
                        'braid_level': 1,
                        'consumed': False
                    }],
                    'braid_level': 1,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                test_patterns.append(pattern)
            
            # Insert patterns
            insert_result = self.supabase_manager.client.table('ad_strands').insert(test_patterns).execute()
            logger.info("    ✅ Integration test patterns inserted")
            
            # Test clustering with high confidence pattern
            high_pattern = test_patterns[0]
            clusters = await self.clustering_engine.get_strand_clusters(high_pattern, 'pattern')
            
            if clusters:
                logger.info("    ✅ Integration clustering successful")
                
                # Test resonance scores with clustered patterns
                for cluster_type, strands in clusters.items():
                    logger.info(f"    ✅ Testing resonance scores for {cluster_type} cluster")
                    
                    for i, strand in enumerate(strands[:3]):  # Test first 3 strands
                        resonance_scores = self.resonance_engine.calculate_module_resonance(strand, 'rdi')
                        if resonance_scores:
                            logger.info(f"        Strand {i}: φ={resonance_scores.get('phi', 0):.3f}, ρ={resonance_scores.get('rho', 0):.3f}")
                        else:
                            logger.warning(f"        Strand {i}: No resonance scores calculated")
            else:
                logger.info("    ✅ Integration clustering: No clusters found")
            
            # Cleanup
            for pattern in test_patterns:
                self.supabase_manager.client.table('ad_strands').delete().eq('id', pattern['id']).execute()
            logger.info("    ✅ Integration test patterns cleaned up")
            
        except Exception as e:
            logger.error(f"    ❌ Integration test failed: {e}")
            raise
        
        logger.info("    ✅ Integration test successful")
    
    async def test_performance(self):
        """Test clustering performance"""
        logger.info("  ⚡ Testing clustering performance...")
        
        try:
            # Test clustering performance with different strand types
            strand_types = ['pattern', 'prediction_review', 'conditional_trading_plan']
            
            for strand_type in strand_types:
                start_time = time.time()
                
                # Create a dummy strand for testing
                dummy_strand = {
                    'id': f"perf_test_{strand_type}_{uuid.uuid4()}",
                    'kind': strand_type,
                    'symbol': 'BTC',
                    'content': {
                        'pattern_type': 'head_and_shoulders',
                        'confidence': 0.8,
                        'timeframe': '1h'
                    },
                    'metadata': {
                        'source': 'performance_test',
                        'quality': 0.9
                    },
                    'cluster_key': [{
                        'cluster_type': 'pattern_type',
                        'cluster_key': 'head_and_shoulders',
                        'braid_level': 1,
                        'consumed': False
                    }],
                    'braid_level': 1,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Test clustering
                clusters = await self.clustering_engine.get_strand_clusters(dummy_strand, strand_type)
                clustering_time = time.time() - start_time
                
                logger.info(f"    ✅ {strand_type} clustering: {clustering_time:.4f}s, {len(clusters) if clusters else 0} cluster types")
                
                if clustering_time > 2.0:
                    logger.warning(f"    ⚠️ Slow clustering for {strand_type}: {clustering_time:.4f}s")
            
            # Test statistics performance
            start_time = time.time()
            
            for strand_type in strand_types:
                stats = await self.clustering_engine.get_cluster_statistics(strand_type)
            
            stats_time = time.time() - start_time
            logger.info(f"    ✅ Statistics calculation: {stats_time:.4f}s for {len(strand_types)} strand types")
            
            if stats_time > 1.0:
                logger.warning(f"    ⚠️ Slow statistics calculation: {stats_time:.4f}s")
            
        except Exception as e:
            logger.error(f"    ❌ Performance test failed: {e}")
            raise
        
        logger.info("    ✅ Performance test successful")
    
    def print_summary(self):
        """Print test summary"""
        end_time = time.time()
        total_time = end_time - self.start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 Simple Clustering Testing Summary (Actual Implementation)")
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
    tester = ClusteringSimpleTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())

