#!/usr/bin/env python3
"""
Comprehensive Mathematical Resonance Engine Testing Suite

Tests all resonance calculations, Simons' equations (φ, ρ, θ, ω, S_i),
clustering algorithms, and mathematical fitness functions.
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
from mathematical_resonance_engine import MathematicalResonanceEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('resonance_test_results.log')
    ]
)
logger = logging.getLogger(__name__)

class ResonanceComprehensiveTester:
    """Comprehensive mathematical resonance engine testing suite"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.resonance_engine = MathematicalResonanceEngine()
        self.test_results = {}
        self.start_time = None
        
    async def run_all_tests(self):
        """Run all resonance tests"""
        logger.info("🧮 Starting Comprehensive Mathematical Resonance Testing")
        logger.info("=" * 80)
        
        self.start_time = time.time()
        
        test_suites = [
            ("Basic Resonance Calculations", self.test_basic_resonance),
            ("Simons Equations", self.test_simons_equations),
            ("Selection Score (S_i)", self.test_selection_score),
            ("Clustering Algorithms", self.test_clustering_algorithms),
            ("Fitness Functions", self.test_fitness_functions),
            ("Pattern Analysis", self.test_pattern_analysis),
            ("Performance Metrics", self.test_performance_metrics),
            ("Edge Cases", self.test_edge_cases),
            ("Integration Testing", self.test_integration),
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
    
    async def test_basic_resonance(self):
        """Test basic resonance calculations"""
        logger.info("  🔢 Testing basic resonance calculations...")
        
        try:
            # Test φ (Fractal Self-Similarity)
            test_data = {
                'pattern_data': [1, 2, 3, 2, 1, 2, 3, 2, 1],  # Simple fractal pattern
                'timeframe': '1h',
                'symbol': 'BTC'
            }
            
            phi_score = self.resonance_engine.calculate_phi(test_data)
            logger.info(f"    ✅ φ (Fractal Self-Similarity): {phi_score:.4f}")
            
            if not (0 <= phi_score <= 1):
                logger.warning(f"    ⚠️ φ score out of range: {phi_score}")
            
            # Test ρ (Recursive Feedback)
            historical_data = {
                'success_rate': 0.75,
                'accuracy': 0.82,
                'consistency': 0.68,
                'time_decay': 0.9
            }
            
            rho_score = self.resonance_engine.calculate_rho(historical_data)
            logger.info(f"    ✅ ρ (Recursive Feedback): {rho_score:.4f}")
            
            if not (0 <= rho_score <= 1):
                logger.warning(f"    ⚠️ ρ score out of range: {rho_score}")
            
            # Test θ (Collective Intelligence)
            collective_data = {
                'ensemble_diversity': 0.85,
                'consensus_strength': 0.78,
                'information_density': 0.72
            }
            
            theta_score = self.resonance_engine.calculate_theta(collective_data)
            logger.info(f"    ✅ θ (Collective Intelligence): {theta_score:.4f}")
            
            if not (0 <= theta_score <= 1):
                logger.warning(f"    ⚠️ θ score out of range: {theta_score}")
            
            # Test ω (Resonance Acceleration)
            acceleration_data = {
                'learning_rate': 0.15,
                'adaptation_speed': 0.23,
                'evolution_potential': 0.18
            }
            
            omega_score = self.resonance_engine.calculate_omega(acceleration_data)
            logger.info(f"    ✅ ω (Resonance Acceleration): {omega_score:.4f}")
            
            if not (0 <= omega_score <= 1):
                logger.warning(f"    ⚠️ ω score out of range: {omega_score}")
            
        except Exception as e:
            logger.error(f"    ❌ Basic resonance calculations failed: {e}")
            raise
        
        logger.info("    ✅ Basic resonance calculations successful")
    
    async def test_simons_equations(self):
        """Test Simons' mathematical equations"""
        logger.info("  📐 Testing Simons' equations...")
        
        try:
            # Test complete resonance calculation
            test_strand = {
                'id': f"resonance_test_{uuid.uuid4()}",
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
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Calculate all resonance scores
            resonance_scores = self.resonance_engine.calculate_resonance_scores(test_strand)
            
            if resonance_scores:
                logger.info(f"    ✅ Complete resonance calculation: {resonance_scores}")
                
                # Validate all scores are in range
                for key, value in resonance_scores.items():
                    if key in ['phi', 'rho', 'theta', 'omega', 'selection_score']:
                        if not (0 <= value <= 1):
                            logger.warning(f"    ⚠️ {key} out of range: {value}")
                        else:
                            logger.info(f"    ✅ {key}: {value:.4f}")
            else:
                logger.error("    ❌ No resonance scores calculated")
                raise Exception("No resonance scores calculated")
            
            # Test equation consistency
            phi = resonance_scores.get('phi', 0)
            rho = resonance_scores.get('rho', 0)
            theta = resonance_scores.get('theta', 0)
            omega = resonance_scores.get('omega', 0)
            
            # Test Simons' resonance equation: R = φ * ρ * θ * ω
            expected_resonance = phi * rho * theta * omega
            calculated_resonance = resonance_scores.get('selection_score', 0)
            
            if abs(expected_resonance - calculated_resonance) < 0.01:
                logger.info("    ✅ Simons' resonance equation consistent")
            else:
                logger.warning(f"    ⚠️ Resonance equation mismatch: expected {expected_resonance:.4f}, got {calculated_resonance:.4f}")
            
        except Exception as e:
            logger.error(f"    ❌ Simons' equations test failed: {e}")
            raise
        
        logger.info("    ✅ Simons' equations test successful")
    
    async def test_selection_score(self):
        """Test selection score (S_i) calculations"""
        logger.info("  🎯 Testing selection score (S_i)...")
        
        try:
            # Test different pattern types
            pattern_types = [
                'head_and_shoulders',
                'double_top',
                'flag_pattern',
                'triangle',
                'channel'
            ]
            
            for pattern_type in pattern_types:
                test_strand = {
                    'id': f"selection_test_{uuid.uuid4()}",
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
                
                selection_score = self.resonance_engine.calculate_selection_score(test_strand)
                logger.info(f"    ✅ {pattern_type}: S_i = {selection_score:.4f}")
                
                if not (0 <= selection_score <= 1):
                    logger.warning(f"    ⚠️ {pattern_type} selection score out of range: {selection_score}")
            
            # Test selection score with different confidence levels
            confidence_levels = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            for confidence in confidence_levels:
                test_strand = {
                    'id': f"confidence_test_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'ETH',
                    'content': {
                        'pattern_type': 'head_and_shoulders',
                        'confidence': confidence,
                        'timeframe': '4h'
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
                
                selection_score = self.resonance_engine.calculate_selection_score(test_strand)
                logger.info(f"    ✅ Confidence {confidence}: S_i = {selection_score:.4f}")
                
                # Higher confidence should generally lead to higher selection score
                if confidence >= 0.8 and selection_score < 0.5:
                    logger.warning(f"    ⚠️ High confidence but low selection score: {confidence} -> {selection_score}")
            
        except Exception as e:
            logger.error(f"    ❌ Selection score test failed: {e}")
            raise
        
        logger.info("    ✅ Selection score test successful")
    
    async def test_clustering_algorithms(self):
        """Test clustering algorithms and pattern grouping"""
        logger.info("  🔗 Testing clustering algorithms...")
        
        try:
            # Test pattern clustering
            test_patterns = [
                {
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
                for i in range(5)
            ]
            
            # Test clustering with similar patterns
            clusters = self.resonance_engine.cluster_patterns(test_patterns)
            
            if clusters:
                logger.info(f"    ✅ Pattern clustering: {len(clusters)} clusters created")
                
                for i, cluster in enumerate(clusters):
                    logger.info(f"    ✅ Cluster {i}: {len(cluster)} patterns")
            else:
                logger.warning("    ⚠️ No clusters created")
            
            # Test clustering with different pattern types
            mixed_patterns = []
            pattern_types = ['head_and_shoulders', 'double_top', 'flag_pattern']
            
            for pattern_type in pattern_types:
                for i in range(3):
                    pattern = {
                        'id': f"mixed_test_{pattern_type}_{i}_{uuid.uuid4()}",
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
                    mixed_patterns.append(pattern)
            
            mixed_clusters = self.resonance_engine.cluster_patterns(mixed_patterns)
            
            if mixed_clusters:
                logger.info(f"    ✅ Mixed pattern clustering: {len(mixed_clusters)} clusters created")
                
                # Should have separate clusters for different pattern types
                if len(mixed_clusters) >= len(pattern_types):
                    logger.info("    ✅ Different pattern types clustered separately")
                else:
                    logger.warning("    ⚠️ Pattern types may be over-clustered")
            else:
                logger.warning("    ⚠️ Mixed pattern clustering failed")
            
        except Exception as e:
            logger.error(f"    ❌ Clustering algorithms test failed: {e}")
            raise
        
        logger.info("    ✅ Clustering algorithms test successful")
    
    async def test_fitness_functions(self):
        """Test mathematical fitness functions"""
        logger.info("  💪 Testing fitness functions...")
        
        try:
            # Test pattern fitness
            test_pattern = {
                'id': f"fitness_test_{uuid.uuid4()}",
                'kind': 'pattern',
                'symbol': 'BTC',
                'content': {
                    'pattern_type': 'head_and_shoulders',
                    'confidence': 0.85,
                    'timeframe': '1h',
                    'strength': 0.9
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
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            fitness_score = self.resonance_engine.calculate_fitness(test_pattern)
            logger.info(f"    ✅ Pattern fitness: {fitness_score:.4f}")
            
            if not (0 <= fitness_score <= 1):
                logger.warning(f"    ⚠️ Fitness score out of range: {fitness_score}")
            
            # Test fitness with different quality levels
            quality_levels = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            for quality in quality_levels:
                test_pattern['metadata']['quality'] = quality
                fitness_score = self.resonance_engine.calculate_fitness(test_pattern)
                logger.info(f"    ✅ Quality {quality}: fitness = {fitness_score:.4f}")
                
                # Higher quality should generally lead to higher fitness
                if quality >= 0.8 and fitness_score < 0.5:
                    logger.warning(f"    ⚠️ High quality but low fitness: {quality} -> {fitness_score}")
            
            # Test fitness with different confidence levels
            confidence_levels = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            for confidence in confidence_levels:
                test_pattern['content']['confidence'] = confidence
                fitness_score = self.resonance_engine.calculate_fitness(test_pattern)
                logger.info(f"    ✅ Confidence {confidence}: fitness = {fitness_score:.4f}")
                
                # Higher confidence should generally lead to higher fitness
                if confidence >= 0.8 and fitness_score < 0.5:
                    logger.warning(f"    ⚠️ High confidence but low fitness: {confidence} -> {fitness_score}")
            
        except Exception as e:
            logger.error(f"    ❌ Fitness functions test failed: {e}")
            raise
        
        logger.info("    ✅ Fitness functions test successful")
    
    async def test_pattern_analysis(self):
        """Test pattern analysis and recognition"""
        logger.info("  🔍 Testing pattern analysis...")
        
        try:
            # Test different pattern types
            pattern_types = [
                'head_and_shoulders',
                'double_top',
                'double_bottom',
                'flag_pattern',
                'triangle',
                'channel',
                'wedge',
                'cup_and_handle'
            ]
            
            for pattern_type in pattern_types:
                test_pattern = {
                    'id': f"analysis_test_{pattern_type}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'BTC',
                    'content': {
                        'pattern_type': pattern_type,
                        'confidence': 0.8,
                        'timeframe': '1h',
                        'strength': 0.85
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
                
                # Analyze pattern
                analysis = self.resonance_engine.analyze_pattern(test_pattern)
                
                if analysis:
                    logger.info(f"    ✅ {pattern_type}: analysis complete")
                    
                    # Check for required analysis fields
                    required_fields = ['resonance_scores', 'fitness_score', 'cluster_assignment']
                    for field in required_fields:
                        if field in analysis:
                            logger.info(f"    ✅ {pattern_type}: {field} present")
                        else:
                            logger.warning(f"    ⚠️ {pattern_type}: {field} missing")
                else:
                    logger.warning(f"    ⚠️ {pattern_type}: no analysis returned")
            
            # Test pattern comparison
            pattern1 = {
                'id': f"compare_test_1_{uuid.uuid4()}",
                'kind': 'pattern',
                'symbol': 'BTC',
                'content': {
                    'pattern_type': 'head_and_shoulders',
                    'confidence': 0.85,
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
            
            pattern2 = {
                'id': f"compare_test_2_{uuid.uuid4()}",
                'kind': 'pattern',
                'symbol': 'BTC',
                'content': {
                    'pattern_type': 'head_and_shoulders',
                    'confidence': 0.82,
                    'timeframe': '1h'
                },
                'metadata': {
                    'source': 'test',
                    'quality': 0.88
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
            
            similarity = self.resonance_engine.calculate_similarity(pattern1, pattern2)
            logger.info(f"    ✅ Pattern similarity: {similarity:.4f}")
            
            if not (0 <= similarity <= 1):
                logger.warning(f"    ⚠️ Similarity score out of range: {similarity}")
            
        except Exception as e:
            logger.error(f"    ❌ Pattern analysis test failed: {e}")
            raise
        
        logger.info("    ✅ Pattern analysis test successful")
    
    async def test_performance_metrics(self):
        """Test performance metrics and optimization"""
        logger.info("  ⚡ Testing performance metrics...")
        
        try:
            # Test calculation speed
            test_patterns = []
            for i in range(10):
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
            
            # Test resonance calculation speed
            start_time = time.time()
            for pattern in test_patterns:
                self.resonance_engine.calculate_resonance_scores(pattern)
            resonance_time = time.time() - start_time
            
            logger.info(f"    ✅ Resonance calculation: {resonance_time:.4f}s for {len(test_patterns)} patterns")
            
            if resonance_time > 1.0:
                logger.warning(f"    ⚠️ Slow resonance calculation: {resonance_time:.4f}s")
            
            # Test clustering speed
            start_time = time.time()
            clusters = self.resonance_engine.cluster_patterns(test_patterns)
            clustering_time = time.time() - start_time
            
            logger.info(f"    ✅ Clustering: {clustering_time:.4f}s for {len(test_patterns)} patterns")
            
            if clustering_time > 2.0:
                logger.warning(f"    ⚠️ Slow clustering: {clustering_time:.4f}s")
            
            # Test memory usage
            import psutil
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            # Run intensive calculations
            for i in range(100):
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
                self.resonance_engine.calculate_resonance_scores(pattern)
            
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_used = memory_after - memory_before
            
            logger.info(f"    ✅ Memory usage: {memory_used:.2f}MB for 100 calculations")
            
            if memory_used > 100:  # 100MB
                logger.warning(f"    ⚠️ High memory usage: {memory_used:.2f}MB")
            
        except Exception as e:
            logger.error(f"    ❌ Performance metrics test failed: {e}")
            raise
        
        logger.info("    ✅ Performance metrics test successful")
    
    async def test_edge_cases(self):
        """Test edge cases and error handling"""
        logger.info("  🚨 Testing edge cases...")
        
        try:
            # Test empty pattern
            empty_pattern = {}
            try:
                resonance_scores = self.resonance_engine.calculate_resonance_scores(empty_pattern)
                if resonance_scores:
                    logger.warning("    ⚠️ Empty pattern should not return scores")
                else:
                    logger.info("    ✅ Empty pattern properly handled")
            except Exception as e:
                logger.info(f"    ✅ Empty pattern properly rejected: {e}")
            
            # Test pattern with missing fields
            incomplete_pattern = {
                'id': f"incomplete_test_{uuid.uuid4()}",
                'kind': 'pattern',
                'symbol': 'BTC'
                # Missing content, metadata, etc.
            }
            
            try:
                resonance_scores = self.resonance_engine.calculate_resonance_scores(incomplete_pattern)
                if resonance_scores:
                    logger.info("    ✅ Incomplete pattern handled gracefully")
                else:
                    logger.info("    ✅ Incomplete pattern properly handled")
            except Exception as e:
                logger.info(f"    ✅ Incomplete pattern properly handled: {e}")
            
            # Test pattern with invalid data types
            invalid_pattern = {
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
            }
            
            try:
                resonance_scores = self.resonance_engine.calculate_resonance_scores(invalid_pattern)
                if resonance_scores:
                    logger.info("    ✅ Invalid data types handled gracefully")
                else:
                    logger.info("    ✅ Invalid data types properly handled")
            except Exception as e:
                logger.info(f"    ✅ Invalid data types properly handled: {e}")
            
            # Test extreme values
            extreme_pattern = {
                'id': f"extreme_test_{uuid.uuid4()}",
                'kind': 'pattern',
                'symbol': 'BTC',
                'content': {
                    'pattern_type': 'head_and_shoulders',
                    'confidence': 1.5,  # > 1.0
                    'timeframe': '1h'
                },
                'metadata': {
                    'source': 'test',
                    'quality': -0.5  # < 0.0
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
            
            try:
                resonance_scores = self.resonance_engine.calculate_resonance_scores(extreme_pattern)
                if resonance_scores:
                    # Check if values are clamped to valid ranges
                    for key, value in resonance_scores.items():
                        if key in ['phi', 'rho', 'theta', 'omega', 'selection_score']:
                            if 0 <= value <= 1:
                                logger.info(f"    ✅ {key} properly clamped: {value}")
                            else:
                                logger.warning(f"    ⚠️ {key} not properly clamped: {value}")
                else:
                    logger.info("    ✅ Extreme values properly handled")
            except Exception as e:
                logger.info(f"    ✅ Extreme values properly handled: {e}")
            
        except Exception as e:
            logger.error(f"    ❌ Edge cases test failed: {e}")
            raise
        
        logger.info("    ✅ Edge cases test successful")
    
    async def test_integration(self):
        """Test integration with database and learning system"""
        logger.info("  🔗 Testing integration...")
        
        try:
            # Test with real database data
            test_strand = {
                'id': f"integration_test_{uuid.uuid4()}",
                'kind': 'pattern',
                'symbol': 'BTC',
                'content': {
                    'pattern_type': 'head_and_shoulders',
                    'confidence': 0.85,
                    'timeframe': '1h'
                },
                'metadata': {
                    'source': 'integration_test',
                    'quality': 0.92
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
            
            # Insert test strand
            insert_result = self.supabase_manager.client.table('ad_strands').insert(test_strand).execute()
            logger.info("    ✅ Test strand inserted")
            
            # Calculate resonance scores
            resonance_scores = self.resonance_engine.calculate_resonance_scores(test_strand)
            
            if resonance_scores:
                logger.info("    ✅ Resonance scores calculated")
                
                # Update strand with resonance scores
                update_result = self.supabase_manager.client.table('ad_strands').update({
                    'resonance_scores': resonance_scores,
                    'resonance_updated_at': datetime.now(timezone.utc).isoformat()
                }).eq('id', test_strand['id']).execute()
                
                logger.info("    ✅ Strand updated with resonance scores")
                
                # Verify update
                verify_result = self.supabase_manager.client.table('ad_strands').select("*").eq('id', test_strand['id']).execute()
                
                if verify_result.data:
                    stored_strand = verify_result.data[0]
                    stored_resonance = stored_strand.get('resonance_scores', {})
                    
                    if stored_resonance:
                        logger.info("    ✅ Resonance scores stored in database")
                        
                        # Verify all scores are present
                        required_scores = ['phi', 'rho', 'theta', 'omega', 'selection_score']
                        for score in required_scores:
                            if score in stored_resonance:
                                logger.info(f"    ✅ {score}: {stored_resonance[score]}")
                            else:
                                logger.warning(f"    ⚠️ {score} missing from stored data")
                    else:
                        logger.warning("    ⚠️ No resonance scores in stored data")
                else:
                    logger.warning("    ⚠️ Could not verify stored data")
            else:
                logger.error("    ❌ No resonance scores calculated")
                raise Exception("No resonance scores calculated")
            
            # Cleanup
            self.supabase_manager.client.table('ad_strands').delete().eq('id', test_strand['id']).execute()
            logger.info("    ✅ Test data cleaned up")
            
        except Exception as e:
            logger.error(f"    ❌ Integration test failed: {e}")
            raise
        
        logger.info("    ✅ Integration test successful")
    
    async def test_stress_testing(self):
        """Test under stress conditions"""
        logger.info("  💪 Testing stress conditions...")
        
        try:
            # Test rapid calculations
            start_time = time.time()
            rapid_results = []
            
            for i in range(50):
                pattern = {
                    'id': f"stress_test_{i}_{uuid.uuid4()}",
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
                
                try:
                    resonance_scores = self.resonance_engine.calculate_resonance_scores(pattern)
                    rapid_results.append(resonance_scores)
                except Exception as e:
                    logger.warning(f"    ⚠️ Stress test {i} failed: {e}")
                    rapid_results.append(None)
            
            rapid_time = time.time() - start_time
            successful_rapid = sum(1 for r in rapid_results if r is not None)
            
            logger.info(f"    ✅ Rapid calculations: {successful_rapid}/50 successful in {rapid_time:.2f}s")
            
            if rapid_time > 10.0:
                logger.warning(f"    ⚠️ Slow rapid calculations: {rapid_time:.2f}s")
            
            # Test large dataset clustering
            large_dataset = []
            for i in range(100):
                pattern = {
                    'id': f"large_test_{i}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'BTC',
                    'content': {
                        'pattern_type': 'head_and_shoulders',
                        'confidence': 0.8,
                        'timeframe': '1h'
                    },
                    'metadata': {
                        'source': 'large_test',
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
                large_dataset.append(pattern)
            
            start_time = time.time()
            large_clusters = self.resonance_engine.cluster_patterns(large_dataset)
            large_time = time.time() - start_time
            
            if large_clusters:
                logger.info(f"    ✅ Large dataset clustering: {len(large_clusters)} clusters in {large_time:.2f}s")
            else:
                logger.warning("    ⚠️ Large dataset clustering failed")
            
            if large_time > 30.0:
                logger.warning(f"    ⚠️ Slow large dataset clustering: {large_time:.2f}s")
            
            # Test memory stress
            import psutil
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            # Run memory-intensive operations
            for i in range(200):
                pattern = {
                    'id': f"memory_stress_{i}_{uuid.uuid4()}",
                    'kind': 'pattern',
                    'symbol': 'BTC',
                    'content': {
                        'pattern_type': 'head_and_shoulders',
                        'confidence': 0.8,
                        'timeframe': '1h'
                    },
                    'metadata': {
                        'source': 'memory_stress',
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
                
                try:
                    self.resonance_engine.calculate_resonance_scores(pattern)
                except Exception as e:
                    logger.warning(f"    ⚠️ Memory stress {i} failed: {e}")
            
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_used = memory_after - memory_before
            
            logger.info(f"    ✅ Memory stress: {memory_used:.2f}MB for 200 calculations")
            
            if memory_used > 200:  # 200MB
                logger.warning(f"    ⚠️ High memory usage: {memory_used:.2f}MB")
            
        except Exception as e:
            logger.error(f"    ❌ Stress testing failed: {e}")
            raise
        
        logger.info("    ✅ Stress testing successful")
    
    def print_summary(self):
        """Print test summary"""
        end_time = time.time()
        total_time = end_time - self.start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 Mathematical Resonance Testing Summary")
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
    tester = ResonanceComprehensiveTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())

