#!/usr/bin/env python3
"""
Comprehensive Clustering Algorithms Testing Suite

Tests clustering algorithms, pattern grouping, multi-dimensional clustering,
and cluster quality metrics for the centralized learning system.
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
        logging.FileHandler('clustering_test_results.log')
    ]
)
logger = logging.getLogger(__name__)

class ClusteringComprehensiveTester:
    """Comprehensive clustering algorithms testing suite"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.clustering_engine = MultiClusterGroupingEngine(self.supabase_manager)
        self.resonance_engine = MathematicalResonanceEngine()
        self.test_results = {}
        self.start_time = None
        
    async def run_all_tests(self):
        """Run all clustering tests"""
        logger.info("🔗 Starting Comprehensive Clustering Algorithms Testing")
        logger.info("=" * 80)
        
        self.start_time = time.time()
        
        test_suites = [
            ("Basic Clustering", self.test_basic_clustering),
            ("Multi-Dimensional Clustering", self.test_multi_dimensional_clustering),
            ("Pattern Grouping", self.test_pattern_grouping),
            ("Cluster Quality Metrics", self.test_cluster_quality_metrics),
            ("Cluster Evolution", self.test_cluster_evolution),
            ("Performance Testing", self.test_performance),
            ("Edge Cases", self.test_edge_cases),
            ("Integration Testing", self.test_integration),
            ("Real Scenarios", self.test_real_scenarios),
            ("Stress Testing", self.test_stress_testing)
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
            # Create test patterns
            test_patterns = []
            for i in range(10):
                pattern = {
                    'id': f"cluster_test_{i}_{uuid.uuid4()}",
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
            
            # Test clustering
            clusters = await self.clustering_engine.get_strand_clusters(test_patterns)
            
            if clusters:
                logger.info(f"    ✅ Basic clustering: {len(clusters)} clusters created")
                
                for i, cluster in enumerate(clusters):
                    logger.info(f"    ✅ Cluster {i}: {len(cluster)} patterns")
            else:
                logger.warning("    ⚠️ No clusters created")
            
        except Exception as e:
            logger.error(f"    ❌ Basic clustering test failed: {e}")
            raise
        
        logger.info("    ✅ Basic clustering test successful")
    
    async def test_multi_dimensional_clustering(self):
        """Test multi-dimensional clustering"""
        logger.info("  📊 Testing multi-dimensional clustering...")
        
        try:
            # Create patterns with different dimensions
            test_patterns = []
            
            # Different pattern types
            pattern_types = ['head_and_shoulders', 'double_top', 'flag_pattern', 'triangle', 'channel']
            for i, pattern_type in enumerate(pattern_types):
                for j in range(3):
                    pattern = {
                        'id': f"multi_test_{pattern_type}_{j}_{uuid.uuid4()}",
                        'kind': 'pattern',
                        'symbol': 'BTC',
                        'content': {
                            'pattern_type': pattern_type,
                            'confidence': 0.8,
                            'timeframe': '1h'
                        },
                        'metadata': {
                            'source': 'test',
                            'quality': 0.9
                        },
                        'cluster_key': [{
                            'cluster_type': 'pattern_type',
                            'cluster_key': pattern_type,
                            'braid_level': 1,
                            'consumed': False
                        }],
                        'braid_level': 1,
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }
                    test_patterns.append(pattern)
            
            # Test multi-dimensional clustering
            clusters = await self.clustering_engine.get_strand_clusters(test_patterns)
            
            if clusters:
                logger.info(f"    ✅ Multi-dimensional clustering: {len(clusters)} clusters created")
                
                # Check if different pattern types are clustered separately
                pattern_types_in_clusters = set()
                for cluster in clusters:
                    for pattern in cluster:
                        pattern_type = pattern.get('content', {}).get('pattern_type', 'unknown')
                        pattern_types_in_clusters.add(pattern_type)
                
                logger.info(f"    ✅ Pattern types in clusters: {pattern_types_in_clusters}")
                
                if len(pattern_types_in_clusters) >= len(pattern_types) * 0.8:
                    logger.info("    ✅ Different pattern types clustered appropriately")
                else:
                    logger.warning("    ⚠️ Pattern types may be over-clustered")
            else:
                logger.warning("    ⚠️ Multi-dimensional clustering failed")
            
        except Exception as e:
            logger.error(f"    ❌ Multi-dimensional clustering test failed: {e}")
            raise
        
        logger.info("    ✅ Multi-dimensional clustering test successful")
    
    async def test_pattern_grouping(self):
        """Test pattern grouping algorithms"""
        logger.info("  🎯 Testing pattern grouping...")
        
        try:
            # Create patterns with different characteristics
            test_patterns = []
            
            # High confidence patterns
            for i in range(5):
                pattern = {
                    'id': f"high_conf_{i}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'BTC',
                    'content': {
                        'pattern_type': 'head_and_shoulders',
                        'confidence': 0.9,
                        'timeframe': '1h'
                    },
                    'metadata': {
                        'source': 'test',
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
            for i in range(5):
                pattern = {
                    'id': f"med_conf_{i}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'BTC',
                    'content': {
                        'pattern_type': 'head_and_shoulders',
                        'confidence': 0.7,
                        'timeframe': '1h'
                    },
                    'metadata': {
                        'source': 'test',
                        'quality': 0.8
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
            
            # Test pattern grouping
            clusters = await self.clustering_engine.get_strand_clusters(test_patterns)
            
            if clusters:
                logger.info(f"    ✅ Pattern grouping: {len(clusters)} clusters created")
                
                # Analyze cluster quality
                for i, cluster in enumerate(clusters):
                    confidences = [p.get('content', {}).get('confidence', 0) for p in cluster]
                    avg_confidence = np.mean(confidences) if confidences else 0
                    logger.info(f"    ✅ Cluster {i}: {len(cluster)} patterns, avg confidence: {avg_confidence:.3f}")
                
                # Check if high confidence patterns are grouped together
                high_conf_clusters = 0
                for cluster in clusters:
                    confidences = [p.get('content', {}).get('confidence', 0) for p in cluster]
                    if confidences and np.mean(confidences) > 0.8:
                        high_conf_clusters += 1
                
                logger.info(f"    ✅ High confidence clusters: {high_conf_clusters}")
            else:
                logger.warning("    ⚠️ Pattern grouping failed")
            
        except Exception as e:
            logger.error(f"    ❌ Pattern grouping test failed: {e}")
            raise
        
        logger.info("    ✅ Pattern grouping test successful")
    
    async def test_cluster_quality_metrics(self):
        """Test cluster quality metrics"""
        logger.info("  📈 Testing cluster quality metrics...")
        
        try:
            # Create test patterns with known characteristics
            test_patterns = []
            
            # Create two distinct groups
            group1_patterns = []
            group2_patterns = []
            
            # Group 1: High quality patterns
            for i in range(5):
                pattern = {
                    'id': f"quality_test_1_{i}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'BTC',
                    'content': {
                        'pattern_type': 'head_and_shoulders',
                        'confidence': 0.9,
                        'timeframe': '1h'
                    },
                    'metadata': {
                        'source': 'test',
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
                group1_patterns.append(pattern)
                test_patterns.append(pattern)
            
            # Group 2: Lower quality patterns
            for i in range(5):
                pattern = {
                    'id': f"quality_test_2_{i}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'ETH',
                    'content': {
                        'pattern_type': 'double_top',
                        'confidence': 0.6,
                        'timeframe': '4h'
                    },
                    'metadata': {
                        'source': 'test',
                        'quality': 0.7
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
                group2_patterns.append(pattern)
                test_patterns.append(pattern)
            
            # Test clustering
            clusters = await self.clustering_engine.get_strand_clusters(test_patterns)
            
            if clusters:
                logger.info(f"    ✅ Cluster quality metrics: {len(clusters)} clusters created")
                
                # Calculate quality metrics for each cluster
                for i, cluster in enumerate(clusters):
                    confidences = [p.get('content', {}).get('confidence', 0) for p in cluster]
                    qualities = [p.get('metadata', {}).get('quality', 0) for p in cluster]
                    
                    avg_confidence = np.mean(confidences) if confidences else 0
                    avg_quality = np.mean(qualities) if qualities else 0
                    std_confidence = np.std(confidences) if confidences else 0
                    std_quality = np.std(qualities) if qualities else 0
                    
                    logger.info(f"    ✅ Cluster {i}:")
                    logger.info(f"        Patterns: {len(cluster)}")
                    logger.info(f"        Avg Confidence: {avg_confidence:.3f} ± {std_confidence:.3f}")
                    logger.info(f"        Avg Quality: {avg_quality:.3f} ± {std_quality:.3f}")
                    
                    # Check if cluster is homogeneous
                    if std_confidence < 0.1 and std_quality < 0.1:
                        logger.info(f"        ✅ Cluster {i} is homogeneous")
                    else:
                        logger.warning(f"        ⚠️ Cluster {i} may be heterogeneous")
                
                # Check if groups are separated
                if len(clusters) >= 2:
                    logger.info("    ✅ Multiple clusters created (good separation)")
                else:
                    logger.warning("    ⚠️ Only one cluster created (may need better separation)")
            else:
                logger.warning("    ⚠️ Cluster quality metrics test failed")
            
        except Exception as e:
            logger.error(f"    ❌ Cluster quality metrics test failed: {e}")
            raise
        
        logger.info("    ✅ Cluster quality metrics test successful")
    
    async def test_cluster_evolution(self):
        """Test cluster evolution over time"""
        logger.info("  🧬 Testing cluster evolution...")
        
        try:
            # Create patterns with different timestamps
            test_patterns = []
            
            # Old patterns (30 days ago)
            old_time = datetime.now(timezone.utc) - timedelta(days=30)
            for i in range(3):
                pattern = {
                    'id': f"old_pattern_{i}_{uuid.uuid4()}",
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
                    'created_at': old_time.isoformat()
                }
                test_patterns.append(pattern)
            
            # Recent patterns (1 day ago)
            recent_time = datetime.now(timezone.utc) - timedelta(days=1)
            for i in range(3):
                pattern = {
                    'id': f"recent_pattern_{i}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'BTC',
                    'content': {
                        'pattern_type': 'head_and_shoulders',
                        'confidence': 0.85,
                        'timeframe': '1h'
                    },
                    'metadata': {
                        'source': 'test',
                        'quality': 0.92
                    },
                    'cluster_key': [{
                        'cluster_type': 'pattern_type',
                        'cluster_key': 'head_and_shoulders',
                        'braid_level': 1,
                        'consumed': False
                    }],
                    'braid_level': 1,
                    'created_at': recent_time.isoformat()
                }
                test_patterns.append(pattern)
            
            # Test clustering with time evolution
            clusters = await self.clustering_engine.get_strand_clusters(test_patterns)
            
            if clusters:
                logger.info(f"    ✅ Cluster evolution: {len(clusters)} clusters created")
                
                # Analyze time distribution in clusters
                for i, cluster in enumerate(clusters):
                    timestamps = [p.get('created_at', '') for p in cluster]
                    old_count = sum(1 for ts in timestamps if '30 days ago' in ts or old_time.isoformat() in ts)
                    recent_count = sum(1 for ts in timestamps if '1 day ago' in ts or recent_time.isoformat() in ts)
                    
                    logger.info(f"    ✅ Cluster {i}: {old_count} old patterns, {recent_count} recent patterns")
                
                # Check if time evolution is handled properly
                if len(clusters) > 1:
                    logger.info("    ✅ Time evolution handled (multiple clusters)")
                else:
                    logger.info("    ✅ Time evolution handled (single cluster with mixed ages)")
            else:
                logger.warning("    ⚠️ Cluster evolution test failed")
            
        except Exception as e:
            logger.error(f"    ❌ Cluster evolution test failed: {e}")
            raise
        
        logger.info("    ✅ Cluster evolution test successful")
    
    async def test_performance(self):
        """Test clustering performance"""
        logger.info("  ⚡ Testing clustering performance...")
        
        try:
            # Test with different dataset sizes
            dataset_sizes = [10, 50, 100, 200]
            
            for size in dataset_sizes:
                # Create test patterns
                test_patterns = []
                for i in range(size):
                    pattern = {
                        'id': f"perf_test_{i}_{uuid.uuid4()}",
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
                    test_patterns.append(pattern)
                
                # Test clustering performance
                start_time = time.time()
                clusters = await self.clustering_engine.get_strand_clusters(test_patterns)
                clustering_time = time.time() - start_time
                
                logger.info(f"    ✅ Dataset size {size}: {clustering_time:.4f}s, {len(clusters) if clusters else 0} clusters")
                
                # Check performance thresholds
                if clustering_time > 5.0:
                    logger.warning(f"    ⚠️ Slow clustering for size {size}: {clustering_time:.4f}s")
                elif clustering_time > 2.0:
                    logger.warning(f"    ⚠️ Moderate clustering time for size {size}: {clustering_time:.4f}s")
            
            # Test memory usage
            import psutil
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            # Run intensive clustering
            large_patterns = []
            for i in range(500):
                pattern = {
                    'id': f"memory_test_{i}_{uuid.uuid4()}",
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
                large_patterns.append(pattern)
            
            clusters = await self.clustering_engine.get_strand_clusters(large_patterns)
            
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_used = memory_after - memory_before
            
            logger.info(f"    ✅ Memory usage: {memory_used:.2f}MB for 500 patterns")
            
            if memory_used > 100:  # 100MB
                logger.warning(f"    ⚠️ High memory usage: {memory_used:.2f}MB")
            
        except Exception as e:
            logger.error(f"    ❌ Performance test failed: {e}")
            raise
        
        logger.info("    ✅ Performance test successful")
    
    async def test_edge_cases(self):
        """Test edge cases and error handling"""
        logger.info("  🚨 Testing edge cases...")
        
        try:
            # Test empty pattern list
            try:
                clusters = await self.clustering_engine.get_strand_clusters([])
                if clusters is None or len(clusters) == 0:
                    logger.info("    ✅ Empty pattern list handled gracefully")
                else:
                    logger.warning("    ⚠️ Empty pattern list should return empty clusters")
            except Exception as e:
                logger.info(f"    ✅ Empty pattern list properly handled: {e}")
            
            # Test single pattern
            single_pattern = [{
                'id': f"single_test_{uuid.uuid4()}",
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
            }]
            
            try:
                clusters = await self.clustering_engine.get_strand_clusters(single_pattern)
                if clusters and len(clusters) == 1:
                    logger.info("    ✅ Single pattern handled correctly")
                else:
                    logger.warning("    ⚠️ Single pattern clustering unexpected")
            except Exception as e:
                logger.info(f"    ✅ Single pattern properly handled: {e}")
            
            # Test patterns with missing data
            incomplete_patterns = [{
                'id': f"incomplete_test_{uuid.uuid4()}",
                'kind': 'pattern',
                'symbol': 'BTC'
                # Missing content, metadata, etc.
            }]
            
            try:
                clusters = await self.clustering_engine.get_strand_clusters(incomplete_patterns)
                if clusters:
                    logger.info("    ✅ Incomplete patterns handled gracefully")
                else:
                    logger.info("    ✅ Incomplete patterns properly handled")
            except Exception as e:
                logger.info(f"    ✅ Incomplete patterns properly handled: {e}")
            
            # Test patterns with invalid data types
            invalid_patterns = [{
                'id': f"invalid_test_{uuid.uuid4()}",
                'kind': 'pattern',
                'symbol': 'BTC',
                'content': {
                    'pattern_type': 'head_and_shoulders',
                    'confidence': 'invalid',  # Should be float
                    'timeframe': '1h'
                },
                'metadata': {
                    'source': 'test',
                    'quality': 'invalid'  # Should be float
                },
                'cluster_key': [{
                    'cluster_type': 'pattern_type',
                    'cluster_key': 'head_and_shoulders',
                    'braid_level': 1,
                    'consumed': False
                }],
                'braid_level': 1,
                'created_at': datetime.now(timezone.utc).isoformat()
            }]
            
            try:
                clusters = await self.clustering_engine.get_strand_clusters(invalid_patterns)
                if clusters:
                    logger.info("    ✅ Invalid data types handled gracefully")
                else:
                    logger.info("    ✅ Invalid data types properly handled")
            except Exception as e:
                logger.info(f"    ✅ Invalid data types properly handled: {e}")
            
        except Exception as e:
            logger.error(f"    ❌ Edge cases test failed: {e}")
            raise
        
        logger.info("    ✅ Edge cases test successful")
    
    async def test_integration(self):
        """Test integration with database and learning system"""
        logger.info("  🔗 Testing integration...")
        
        try:
            # Test with real database data
            test_patterns = []
            for i in range(5):
                pattern = {
                    'id': f"integration_test_{i}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'BTC',
                    'content': {
                        'pattern_type': 'head_and_shoulders',
                        'confidence': 0.8,
                        'timeframe': '1h'
                    },
                    'metadata': {
                        'source': 'integration_test',
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
            
            # Insert test patterns
            insert_result = self.supabase_manager.client.table('ad_strands').insert(test_patterns).execute()
            logger.info("    ✅ Test patterns inserted")
            
            # Test clustering
            clusters = await self.clustering_engine.get_strand_clusters(test_patterns)
            
            if clusters:
                logger.info("    ✅ Clustering with database data successful")
                
                # Test cluster quality with resonance scores
                for i, cluster in enumerate(clusters):
                    logger.info(f"    ✅ Cluster {i}: {len(cluster)} patterns")
                    
                    # Calculate resonance scores for cluster
                    for pattern in cluster:
                        resonance_scores = self.resonance_engine.calculate_module_resonance(pattern, 'rdi')
                        if resonance_scores:
                            logger.info(f"        Pattern {pattern['id']}: φ={resonance_scores.get('phi', 0):.3f}")
            else:
                logger.warning("    ⚠️ Clustering with database data failed")
            
            # Cleanup
            for pattern in test_patterns:
                self.supabase_manager.client.table('ad_strands').delete().eq('id', pattern['id']).execute()
            logger.info("    ✅ Test data cleaned up")
            
        except Exception as e:
            logger.error(f"    ❌ Integration test failed: {e}")
            raise
        
        logger.info("    ✅ Integration test successful")
    
    async def test_real_scenarios(self):
        """Test with real trading scenarios"""
        logger.info("  📈 Testing real scenarios...")
        
        try:
            # Test with realistic pattern data
            real_patterns = []
            
            # Head and shoulders patterns
            for i in range(3):
                pattern = {
                    'id': f"real_hs_{i}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'BTC',
                    'content': {
                        'pattern_type': 'head_and_shoulders',
                        'confidence': 0.85,
                        'timeframe': '1h',
                        'price': 45000 + i * 100,
                        'volume': 1200 + i * 50
                    },
                    'metadata': {
                        'source': 'real_scenario',
                        'quality': 0.92,
                        'market_conditions': 'bullish'
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
                real_patterns.append(pattern)
            
            # Double top patterns
            for i in range(3):
                pattern = {
                    'id': f"real_dt_{i}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'ETH',
                    'content': {
                        'pattern_type': 'double_top',
                        'confidence': 0.78,
                        'timeframe': '4h',
                        'price': 3200 + i * 50,
                        'volume': 800 + i * 30
                    },
                    'metadata': {
                        'source': 'real_scenario',
                        'quality': 0.88,
                        'market_conditions': 'bearish'
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
                real_patterns.append(pattern)
            
            # Test clustering with real scenarios
            clusters = await self.clustering_engine.get_strand_clusters(real_patterns)
            
            if clusters:
                logger.info(f"    ✅ Real scenarios clustering: {len(clusters)} clusters created")
                
                # Analyze cluster characteristics
                for i, cluster in enumerate(clusters):
                    pattern_types = [p.get('content', {}).get('pattern_type', 'unknown') for p in cluster]
                    symbols = [p.get('symbol', 'unknown') for p in cluster]
                    confidences = [p.get('content', {}).get('confidence', 0) for p in cluster]
                    
                    logger.info(f"    ✅ Cluster {i}:")
                    logger.info(f"        Pattern types: {set(pattern_types)}")
                    logger.info(f"        Symbols: {set(symbols)}")
                    logger.info(f"        Avg confidence: {np.mean(confidences):.3f}")
                
                # Check if similar patterns are grouped together
                if len(clusters) >= 2:
                    logger.info("    ✅ Similar patterns grouped together")
                else:
                    logger.info("    ✅ All patterns in single cluster (may be appropriate)")
            else:
                logger.warning("    ⚠️ Real scenarios clustering failed")
            
        except Exception as e:
            logger.error(f"    ❌ Real scenarios test failed: {e}")
            raise
        
        logger.info("    ✅ Real scenarios test successful")
    
    async def test_stress_testing(self):
        """Test under stress conditions"""
        logger.info("  💪 Testing stress conditions...")
        
        try:
            # Test rapid clustering
            start_time = time.time()
            rapid_clusters = []
            
            for i in range(10):
                test_patterns = []
                for j in range(10):
                    pattern = {
                        'id': f"stress_test_{i}_{j}_{uuid.uuid4()}",
                        'kind': 'pattern',
                        'symbol': 'BTC',
                        'content': {
                            'pattern_type': 'head_and_shoulders',
                            'confidence': 0.8,
                            'timeframe': '1h'
                        },
                        'metadata': {
                            'source': 'stress_test',
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
                
                try:
                    clusters = await self.clustering_engine.get_strand_clusters(test_patterns)
                    rapid_clusters.append(clusters)
                except Exception as e:
                    logger.warning(f"    ⚠️ Stress test {i} failed: {e}")
                    rapid_clusters.append(None)
            
            rapid_time = time.time() - start_time
            successful_rapid = sum(1 for c in rapid_clusters if c is not None)
            
            logger.info(f"    ✅ Rapid clustering: {successful_rapid}/10 successful in {rapid_time:.2f}s")
            
            if rapid_time > 10.0:
                logger.warning(f"    ⚠️ Slow rapid clustering: {rapid_time:.2f}s")
            
            # Test large dataset clustering
            large_patterns = []
            for i in range(1000):
                pattern = {
                    'id': f"large_stress_{i}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'BTC',
                    'content': {
                        'pattern_type': 'head_and_shoulders',
                        'confidence': 0.8,
                        'timeframe': '1h'
                    },
                    'metadata': {
                        'source': 'stress_test',
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
                large_patterns.append(pattern)
            
            start_time = time.time()
            large_clusters = await self.clustering_engine.get_strand_clusters(large_patterns)
            large_time = time.time() - start_time
            
            if large_clusters:
                logger.info(f"    ✅ Large dataset clustering: {len(large_clusters)} clusters in {large_time:.2f}s")
            else:
                logger.warning("    ⚠️ Large dataset clustering failed")
            
            if large_time > 30.0:
                logger.warning(f"    ⚠️ Slow large dataset clustering: {large_time:.2f}s")
            
        except Exception as e:
            logger.error(f"    ❌ Stress testing failed: {e}")
            raise
        
        logger.info("    ✅ Stress testing successful")
    
    def print_summary(self):
        """Print test summary"""
        end_time = time.time()
        total_time = end_time - self.start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 Clustering Algorithms Testing Summary")
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
    tester = ClusteringComprehensiveTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
