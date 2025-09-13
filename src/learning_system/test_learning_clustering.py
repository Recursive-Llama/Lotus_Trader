#!/usr/bin/env python3
"""
Test Learning and Clustering Functionality

This test focuses on testing the actual learning and clustering components:
1. Strand clustering
2. Learning analysis with LLM
3. Braid creation
4. Context injection
"""

import sys
import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add the necessary paths
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/src')

class LearningClusteringTest:
    """Test the learning and clustering functionality"""
    
    def __init__(self):
        self.test_results = []
        self.failures = []
        
    def log_success(self, test_name: str, details: str = ""):
        """Log a successful test"""
        self.test_results.append(f"✅ {test_name}: {details}")
        print(f"✅ {test_name}: {details}")
        
    def log_failure(self, test_name: str, error: str):
        """Log a failed test"""
        self.failures.append(f"❌ {test_name}: {error}")
        print(f"❌ {test_name}: {error}")
    
    def test_strand_clustering(self):
        """Test strand clustering functionality"""
        print("\n🧪 Testing Strand Clustering...")
        print("=" * 60)
        
        try:
            from multi_cluster_grouping_engine import MultiClusterGroupingEngine
            
            # Create mock supabase manager
            class MockSupabaseManager:
                def __init__(self):
                    self.strands = []
                
                async def get_strands_by_type(self, strand_type: str, limit: int = 100):
                    return [s for s in self.strands if s.get('kind') == strand_type]
                
                async def insert_braid(self, braid_data: Dict[str, Any]):
                    return {'id': f'braid_{len(self.strands)}', 'success': True}
            
            # Initialize clustering engine
            clustering_engine = MultiClusterGroupingEngine(MockSupabaseManager())
            
            # Create test strands for clustering
            test_strands = [
                {
                    'id': 'pattern_001',
                    'kind': 'pattern',
                    'content': {
                        'pattern_type': 'rsi_divergence',
                        'confidence': 0.85,
                        'asset': 'BTC',
                        'timeframe': '1H'
                    },
                    'metadata': {'confidence': 0.85}
                },
                {
                    'id': 'pattern_002',
                    'kind': 'pattern',
                    'content': {
                        'pattern_type': 'rsi_divergence',
                        'confidence': 0.90,
                        'asset': 'ETH',
                        'timeframe': '1H'
                    },
                    'metadata': {'confidence': 0.90}
                },
                {
                    'id': 'pattern_003',
                    'kind': 'pattern',
                    'content': {
                        'pattern_type': 'macd_crossover',
                        'confidence': 0.75,
                        'asset': 'BTC',
                        'timeframe': '4H'
                    },
                    'metadata': {'confidence': 0.75}
                }
            ]
            
            # Test clustering
            try:
                clusters = clustering_engine.cluster_strands(test_strands)
                
                if clusters and len(clusters) > 0:
                    self.log_success("Strand clustering", f"Created {len(clusters)} clusters")
                    
                    # Test cluster quality
                    for i, cluster in enumerate(clusters):
                        if 'strands' in cluster and len(cluster['strands']) > 0:
                            self.log_success(f"Cluster {i+1} quality", f"Contains {len(cluster['strands'])} strands")
                        else:
                            self.log_failure(f"Cluster {i+1} quality", "Empty cluster")
                else:
                    self.log_failure("Strand clustering", "No clusters created")
                    
            except Exception as e:
                self.log_failure("Strand clustering", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Strand clustering setup", f"Error: {e}")
            return False
    
    async def test_llm_learning_analyzer(self):
        """Test LLM learning analyzer"""
        print("\n🧪 Testing LLM Learning Analyzer...")
        print("=" * 60)
        
        try:
            from llm_learning_analyzer import LLMLearningAnalyzer
            
            # Create mock LLM client and prompt manager
            class MockLLMClient:
                async def generate_completion(self, prompt: str, max_tokens: int = 200, temperature: float = 0.7):
                    return f"Mock LLM analysis: {prompt[:50]}..."
            
            class MockPromptManager:
                def get_prompt_text(self, template_name: str):
                    return f"Mock prompt for {template_name}: Analyze the following data..."
            
            # Initialize analyzer
            analyzer = LLMLearningAnalyzer(MockLLMClient(), MockPromptManager())
            
            # Test learning analysis
            test_strands = [
                {
                    'id': 'strand_001',
                    'kind': 'pattern',
                    'content': {
                        'pattern_type': 'rsi_divergence',
                        'confidence': 0.85,
                        'description': 'RSI divergence detected'
                    }
                },
                {
                    'id': 'strand_002',
                    'kind': 'pattern',
                    'content': {
                        'pattern_type': 'rsi_divergence',
                        'confidence': 0.90,
                        'description': 'Another RSI divergence'
                    }
                }
            ]
            
            try:
                # Test learning analysis
                analysis = await analyzer.analyze_cluster(test_strands, 'pattern_cluster', 'pattern')
                
                if analysis and len(analysis) > 0:
                    self.log_success("LLM learning analysis", f"Generated analysis: {analysis}")
                else:
                    self.log_failure("LLM learning analysis", "No analysis generated")
                    
            except Exception as e:
                self.log_failure("LLM learning analysis", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("LLM learning analyzer setup", f"Error: {e}")
            return False
    
    async def test_braid_creation(self):
        """Test braid creation and management"""
        print("\n🧪 Testing Braid Creation...")
        print("=" * 60)
        
        try:
            from braid_level_manager import BraidLevelManager
            
            # Create mock supabase manager
            class MockSupabaseManager:
                def __init__(self):
                    self.braids = []
                
                async def insert_braid(self, braid_data: Dict[str, Any]):
                    braid_id = f'braid_{len(self.braids)}'
                    self.braids.append({**braid_data, 'id': braid_id})
                    return {'id': braid_id, 'success': True}
                
                async def get_braids_by_strand_types(self, strand_types: List[str]):
                    return [b for b in self.braids if any(st in b.get('strand_types', []) for st in strand_types)]
            
            # Initialize braid manager
            braid_manager = BraidLevelManager(MockSupabaseManager())
            
            # Test braid creation
            test_braid_data = {
                'strand_types': ['pattern'],
                'content': 'Test braid content',
                'metadata': {
                    'quality': 0.85,
                    'confidence': 0.80,
                    'strand_count': 3
                },
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            try:
                # Test braid creation with correct parameters
                test_strands = [
                    {
                        'id': 'strand_001',
                        'kind': 'pattern',
                        'content': {'pattern_type': 'rsi_divergence', 'confidence': 0.85}
                    }
                ]
                
                result = await braid_manager.create_braid(test_strands, 'pattern', 2)
                
                if result:
                    self.log_success("Braid creation", f"Created braid: {result}")
                else:
                    self.log_failure("Braid creation", "Failed to create braid")
                    
                # Test braid retrieval
                braids = await braid_manager.get_braids_by_strand_types(['pattern'])
                
                if braids and len(braids) > 0:
                    self.log_success("Braid retrieval", f"Retrieved {len(braids)} braids")
                else:
                    self.log_failure("Braid retrieval", "No braids retrieved")
                    
            except Exception as e:
                self.log_failure("Braid management", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Braid creation setup", f"Error: {e}")
            return False
    
    async def test_learning_pipeline_integration(self):
        """Test the complete learning pipeline integration"""
        print("\n🧪 Testing Learning Pipeline Integration...")
        print("=" * 60)
        
        try:
            from learning_pipeline import LearningPipeline
            
            # Create mock dependencies
            class MockSupabaseManager:
                def __init__(self):
                    self.strands = []
                    self.braids = []
                
                async def get_strands_by_type(self, strand_type: str, limit: int = 100):
                    return [s for s in self.strands if s.get('kind') == strand_type]
                
                async def insert_braid(self, braid_data: Dict[str, Any]):
                    braid_id = f'braid_{len(self.braids)}'
                    self.braids.append({**braid_data, 'id': braid_id})
                    return {'id': braid_id, 'success': True}
            
            class MockLLMClient:
                async def generate_completion(self, prompt: str, max_tokens: int = 200, temperature: float = 0.7):
                    return f"Mock LLM analysis: {prompt[:50]}..."
            
            class MockPromptManager:
                def get_prompt_text(self, template_name: str):
                    return f"Mock prompt for {template_name}: Analyze the following data..."
            
            # Initialize learning pipeline
            pipeline = LearningPipeline(
                MockSupabaseManager(),
                MockLLMClient(),
                MockPromptManager()
            )
            
            # Test complete pipeline
            test_strands = [
                {
                    'id': 'strand_001',
                    'kind': 'pattern',
                    'content': {
                        'pattern_type': 'rsi_divergence',
                        'confidence': 0.85,
                        'description': 'RSI divergence detected'
                    }
                }
            ]
            
            try:
                # Test pipeline processing
                result = await pipeline.process_strands(test_strands)
                
                if result and result.get('success'):
                    self.log_success("Learning pipeline", f"Processed {len(test_strands)} strands")
                else:
                    self.log_failure("Learning pipeline", "Pipeline processing failed")
                    
            except Exception as e:
                self.log_failure("Learning pipeline", f"Error: {e}")
            
            return True
            
        except Exception as e:
            self.log_failure("Learning pipeline setup", f"Error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all learning and clustering tests"""
        print("🚀 LEARNING AND CLUSTERING FUNCTIONALITY TESTING")
        print("Testing the actual learning and clustering components")
        print("=" * 80)
        
        self.test_strand_clustering()
        await self.test_llm_learning_analyzer()
        await self.test_braid_creation()
        await self.test_learning_pipeline_integration()
        
        # Summary
        print("\n" + "=" * 80)
        print("🔍 LEARNING AND CLUSTERING TEST RESULTS")
        print("=" * 80)
        
        print(f"\n✅ SUCCESSES ({len(self.test_results)}):")
        for result in self.test_results:
            print(f"  {result}")
        
        print(f"\n❌ FAILURES ({len(self.failures)}):")
        for failure in self.failures:
            print(f"  {failure}")
        
        print(f"\n⚡ PERFORMANCE METRICS:")
        print(f"  Total tests: {len(self.test_results) + len(self.failures)}")
        print(f"  Success rate: {len(self.test_results) / (len(self.test_results) + len(self.failures)) * 100:.1f}%")
        
        if self.failures:
            print(f"\n⚠️  LEARNING SYSTEM HAS ISSUES")
            print(f"   {len(self.failures)} components are failing")
            print(f"   Need to fix remaining issues before production")
        else:
            print(f"\n🎉 ALL LEARNING TESTS PASSED")
            print(f"   Learning and clustering functionality is working correctly")

if __name__ == "__main__":
    test = LearningClusteringTest()
    asyncio.run(test.run_all_tests())
