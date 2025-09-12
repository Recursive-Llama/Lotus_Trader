#!/usr/bin/env python3
"""
Comprehensive Learning System Test Suite

This test suite puts the prediction and learning system through its paces:
- Creates real prediction data that triggers braid creation
- Tests multiple braid levels (1 → 2 → 3 → 4...)
- Verifies data flows through the entire system
- Tests context retrieval for predictions
- Finds cracks in the implementation

Unlike previous tests that only checked for exceptions, this tests actual functionality.
"""

import asyncio
import json
import sys
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from intelligence.system_control.central_intelligence_layer.simplified_cil import SimplifiedCIL
from intelligence.system_control.central_intelligence_layer.multi_cluster_grouping_engine import MultiClusterGroupingEngine
from intelligence.system_control.central_intelligence_layer.per_cluster_learning_system import PerClusterLearningSystem
from intelligence.system_control.central_intelligence_layer.llm_learning_analyzer import LLMLearningAnalyzer
from intelligence.system_control.central_intelligence_layer.braid_level_manager import BraidLevelManager
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class ComprehensiveLearningTest:
    """Comprehensive test suite for the learning system"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.llm_client = OpenRouterClient()
        self.simplified_cil = SimplifiedCIL(self.supabase_manager, self.llm_client)
        self.test_results = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'braids_created': 0,
            'max_braid_level': 0,
            'errors': []
        }
    
    async def run_all_tests(self):
        """Run all comprehensive tests"""
        print("🚀 Starting Comprehensive Learning System Tests")
        print("=" * 60)
        
        try:
            # Test 1: Create prediction data that will trigger braid creation
            await self.test_create_prediction_data()
            
            # Test 2: Test multi-cluster grouping
            await self.test_multi_cluster_grouping()
            
            # Test 3: Test learning system with real data
            await self.test_learning_system_with_real_data()
            
            # Test 4: Test braid level progression
            await self.test_braid_level_progression()
            
            # Test 5: Test context retrieval for predictions
            await self.test_context_retrieval()
            
            # Test 6: Test consumed status tracking
            await self.test_consumed_status_tracking()
            
            # Test 7: Test cross-cluster preservation
            await self.test_cross_cluster_preservation()
            
            # Test 8: Test LLM learning analysis
            await self.test_llm_learning_analysis()
            
            # Test 9: Test data flow integrity
            await self.test_data_flow_integrity()
            
            # Test 10: Test edge cases and error handling
            await self.test_edge_cases()
            
        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            self.test_results['errors'].append(f"Test suite failure: {e}")
        
        # Print final results
        self.print_test_results()
    
    async def test_create_prediction_data(self):
        """Test 1: Create prediction data that will trigger braid creation"""
        print("\n🧪 Test 1: Creating Prediction Data")
        print("-" * 40)
        
        try:
            # Create multiple prediction_review strands that will cluster together
            prediction_data = await self.create_test_prediction_data()
            
            # Verify data was created
            query = "SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review'"
            result = await self.supabase_manager.execute_query(query)
            count = result[0][0] if result else 0
            
            assert count >= 15, f"Expected at least 15 prediction_review strands, got {count}"
            
            print(f"✅ Created {count} prediction_review strands")
            self.test_results['tests_passed'] += 1
            
        except Exception as e:
            print(f"❌ Failed to create prediction data: {e}")
            self.test_results['tests_failed'] += 1
            self.test_results['errors'].append(f"Test 1: {e}")
        
        self.test_results['tests_run'] += 1
    
    async def create_test_prediction_data(self) -> List[Dict[str, Any]]:
        """Create comprehensive test prediction data"""
        
        # Create prediction data that will cluster in multiple ways
        prediction_data = []
        
        # Group 1: BTC 1h volume_spike patterns (should cluster by asset + timeframe + pattern)
        for i in range(5):
            prediction = {
                'id': f"pred_btc_1h_vol_{i}_{int(datetime.now().timestamp())}",
                'kind': 'prediction_review',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'tags': ['cil', 'learning', 'prediction_review'],
                'braid_level': 1,
                'content': {
                    'asset': 'BTC',
                    'timeframe': '1h',
                    'pattern_type': 'volume_spike',
                    'group_type': 'single_single',
                    'group_signature': 'BTC_1h_volume_spike',
                    'success': i % 3 == 0,  # 2/5 success rate
                    'confidence': 0.6 + (i * 0.1),
                    'return_pct': 2.5 if i % 3 == 0 else -1.2,
                    'max_drawdown': 0.8,
                    'method': 'code' if i % 2 == 0 else 'llm',
                    'original_pattern_strand_ids': [f"pattern_{i}_{uuid.uuid4().hex[:8]}"]
                },
                'module_intelligence': {
                    'cluster_type': 'pattern_timeframe',
                    'cluster_key': 'BTC_1h_volume_spike',
                    'braid_level': 1
                }
            }
            prediction_data.append(prediction)
        
        # Group 2: ETH 1h divergence patterns (should cluster by asset + timeframe + pattern)
        for i in range(4):
            prediction = {
                'id': f"pred_eth_1h_div_{i}_{int(datetime.now().timestamp())}",
                'kind': 'prediction_review',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'tags': ['cil', 'learning', 'prediction_review'],
                'braid_level': 1,
                'content': {
                    'asset': 'ETH',
                    'timeframe': '1h',
                    'pattern_type': 'divergence',
                    'group_type': 'single_single',
                    'group_signature': 'ETH_1h_divergence',
                    'success': i % 2 == 0,  # 2/4 success rate
                    'confidence': 0.7 + (i * 0.05),
                    'return_pct': 3.2 if i % 2 == 0 else -0.9,
                    'max_drawdown': 0.6,
                    'method': 'llm' if i % 2 == 0 else 'code',
                    'original_pattern_strand_ids': [f"pattern_eth_{i}_{uuid.uuid4().hex[:8]}"]
                },
                'module_intelligence': {
                    'cluster_type': 'pattern_timeframe',
                    'cluster_key': 'ETH_1h_divergence',
                    'braid_level': 1
                }
            }
            prediction_data.append(prediction)
        
        # Group 3: BTC 4h multi patterns (should cluster by asset + timeframe)
        for i in range(3):
            prediction = {
                'id': f"pred_btc_4h_multi_{i}_{int(datetime.now().timestamp())}",
                'kind': 'prediction_review',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'tags': ['cil', 'learning', 'prediction_review'],
                'braid_level': 1,
                'content': {
                    'asset': 'BTC',
                    'timeframe': '4h',
                    'pattern_type': 'multi_pattern',
                    'group_type': 'multi_single',
                    'group_signature': 'BTC_4h_volume_spike_divergence',
                    'success': i == 0,  # 1/3 success rate
                    'confidence': 0.8 + (i * 0.1),
                    'return_pct': 4.1 if i == 0 else -2.3,
                    'max_drawdown': 1.2,
                    'method': 'code',
                    'original_pattern_strand_ids': [f"pattern_btc_4h_{i}_{uuid.uuid4().hex[:8]}"]
                },
                'module_intelligence': {
                    'cluster_type': 'pattern_timeframe',
                    'cluster_key': 'BTC_4h_volume_spike_divergence',
                    'braid_level': 1
                }
            }
            prediction_data.append(prediction)
        
        # Group 4: Success outcomes (should cluster by outcome)
        for i in range(3):
            prediction = {
                'id': f"pred_success_{i}_{int(datetime.now().timestamp())}",
                'kind': 'prediction_review',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'tags': ['cil', 'learning', 'prediction_review'],
                'braid_level': 1,
                'content': {
                    'asset': 'ADA',
                    'timeframe': '1h',
                    'pattern_type': 'volume_spike',
                    'group_type': 'single_single',
                    'group_signature': 'ADA_1h_volume_spike',
                    'success': True,  # All successful
                    'confidence': 0.9,
                    'return_pct': 5.2,
                    'max_drawdown': 0.3,
                    'method': 'llm',
                    'original_pattern_strand_ids': [f"pattern_ada_{i}_{uuid.uuid4().hex[:8]}"]
                },
                'module_intelligence': {
                    'cluster_type': 'pattern_timeframe',
                    'cluster_key': 'ADA_1h_volume_spike',
                    'braid_level': 1
                }
            }
            prediction_data.append(prediction)
        
        # Insert all prediction data
        for prediction in prediction_data:
            await self.insert_prediction_strand(prediction)
        
        return prediction_data
    
    async def insert_prediction_strand(self, prediction: Dict[str, Any]):
        """Insert a prediction strand into the database"""
        
        # Assign to clusters
        cluster_assignments = []
        
        # Asset cluster
        cluster_assignments.append({
            "cluster_type": "asset",
            "cluster_key": prediction['content']['asset'],
            "braid_level": prediction['braid_level'],
            "consumed": False
        })
        
        # Timeframe cluster
        cluster_assignments.append({
            "cluster_type": "timeframe",
            "cluster_key": prediction['content']['timeframe'],
            "braid_level": prediction['braid_level'],
            "consumed": False
        })
        
        # Pattern+timeframe cluster
        cluster_assignments.append({
            "cluster_type": "pattern_timeframe",
            "cluster_key": prediction['content']['group_signature'],
            "braid_level": prediction['braid_level'],
            "consumed": False
        })
        
        # Outcome cluster
        outcome_key = 'success' if prediction['content']['success'] else 'failure'
        cluster_assignments.append({
            "cluster_type": "outcome",
            "cluster_key": outcome_key,
            "braid_level": prediction['braid_level'],
            "consumed": False
        })
        
        # Method cluster
        cluster_assignments.append({
            "cluster_type": "method",
            "cluster_key": prediction['content']['method'],
            "braid_level": prediction['braid_level'],
            "consumed": False
        })
        
        # Pattern cluster
        cluster_assignments.append({
            "cluster_type": "pattern",
            "cluster_key": prediction['content']['group_type'],
            "braid_level": prediction['braid_level'],
            "consumed": False
        })
        
        # Group type cluster
        cluster_assignments.append({
            "cluster_type": "group_type",
            "cluster_key": prediction['content']['group_type'],
            "braid_level": prediction['braid_level'],
            "consumed": False
        })
        
        # Update prediction with cluster assignments
        prediction['cluster_key'] = cluster_assignments
        
        # Insert into database
        await self.supabase_manager.execute_query("""
            INSERT INTO AD_strands (id, kind, created_at, tags, braid_level, content, module_intelligence, cluster_key)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, [
            prediction['id'],
            prediction['kind'],
            prediction['created_at'],
            prediction['tags'],
            prediction['braid_level'],
            json.dumps(prediction['content']),
            json.dumps(prediction['module_intelligence']),
            json.dumps(prediction['cluster_key'])
        ])
    
    async def test_multi_cluster_grouping(self):
        """Test 2: Test multi-cluster grouping"""
        print("\n🧪 Test 2: Multi-Cluster Grouping")
        print("-" * 40)
        
        try:
            cluster_grouper = MultiClusterGroupingEngine(self.supabase_manager)
            
            # Get all prediction reviews
            query = "SELECT * FROM AD_strands WHERE kind = 'prediction_review'"
            result = await self.supabase_manager.execute_query(query)
            prediction_reviews = [dict(row) for row in result]
            
            # Group them
            clusters = await cluster_grouper.group_prediction_reviews(prediction_reviews)
            
            # Verify we have clusters
            assert len(clusters) == 7, f"Expected 7 cluster types, got {len(clusters)}"
            
            # Check each cluster type
            for cluster_type, cluster_groups in clusters.items():
                assert isinstance(cluster_groups, dict), f"Cluster {cluster_type} should be a dict"
                print(f"  {cluster_type}: {len(cluster_groups)} groups")
                
                # Check that we have groups with 3+ strands
                for cluster_key, strands in cluster_groups.items():
                    assert len(strands) >= 3, f"Cluster {cluster_type}:{cluster_key} should have 3+ strands, got {len(strands)}"
            
            print("✅ Multi-cluster grouping working correctly")
            self.test_results['tests_passed'] += 1
            
        except Exception as e:
            print(f"❌ Multi-cluster grouping failed: {e}")
            self.test_results['tests_failed'] += 1
            self.test_results['errors'].append(f"Test 2: {e}")
        
        self.test_results['tests_run'] += 1
    
    async def test_learning_system_with_real_data(self):
        """Test 3: Test learning system with real data"""
        print("\n🧪 Test 3: Learning System with Real Data")
        print("-" * 40)
        
        try:
            learning_system = PerClusterLearningSystem(self.supabase_manager, self.llm_client)
            
            # Process all clusters
            learning_braids = await learning_system.process_all_clusters()
            
            # Verify learning braids were created
            total_braids = sum(len(braids) for braids in learning_braids.values())
            assert total_braids > 0, f"Expected learning braids to be created, got {total_braids}"
            
            print(f"✅ Created {total_braids} learning braids across {len(learning_braids)} cluster types")
            
            # Check that braids are prediction_review strands with braid_level 2
            for cluster_type, braid_ids in learning_braids.items():
                for braid_id in braid_ids:
                    query = "SELECT * FROM AD_strands WHERE id = %s"
                    result = await self.supabase_manager.execute_query(query, [braid_id])
                    if result:
                        braid = dict(result[0])
                        assert braid['kind'] == 'prediction_review', f"Braid should be prediction_review, got {braid['kind']}"
                        assert braid['braid_level'] == 2, f"Braid should be level 2, got {braid['braid_level']}"
                        assert braid['lesson'], "Braid should have lesson content"
            
            self.test_results['braids_created'] = total_braids
            self.test_results['tests_passed'] += 1
            
        except Exception as e:
            print(f"❌ Learning system failed: {e}")
            self.test_results['tests_failed'] += 1
            self.test_results['errors'].append(f"Test 3: {e}")
        
        self.test_results['tests_run'] += 1
    
    async def test_braid_level_progression(self):
        """Test 4: Test braid level progression"""
        print("\n🧪 Test 4: Braid Level Progression")
        print("-" * 40)
        
        try:
            # Create more level 2 strands to trigger level 3 braids
            await self.create_level_2_strands()
            
            # Process braid progression
            braid_manager = BraidLevelManager(self.supabase_manager)
            
            # Get all clusters
            cluster_grouper = MultiClusterGroupingEngine(self.supabase_manager)
            clusters = await cluster_grouper.get_all_cluster_groups()
            
            # Process braid creation
            created_braids = await braid_manager.process_all_clusters(clusters)
            
            # Check for higher level braids
            query = "SELECT MAX(braid_level) FROM AD_strands WHERE kind = 'prediction_review'"
            result = await self.supabase_manager.execute_query(query)
            max_level = result[0][0] if result and result[0][0] else 1
            
            assert max_level >= 2, f"Expected braid levels >= 2, got {max_level}"
            
            print(f"✅ Achieved braid level {max_level}")
            self.test_results['max_braid_level'] = max_level
            self.test_results['tests_passed'] += 1
            
        except Exception as e:
            print(f"❌ Braid level progression failed: {e}")
            self.test_results['tests_failed'] += 1
            self.test_results['errors'].append(f"Test 4: {e}")
        
        self.test_results['tests_run'] += 1
    
    async def create_level_2_strands(self):
        """Create additional level 2 strands to trigger higher level braids"""
        
        # Create 3 more level 2 strands for the same cluster
        for i in range(3):
            prediction = {
                'id': f"pred_level2_{i}_{int(datetime.now().timestamp())}",
                'kind': 'prediction_review',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'tags': ['cil', 'learning', 'prediction_review'],
                'braid_level': 2,
                'content': {
                    'asset': 'BTC',
                    'timeframe': '1h',
                    'pattern_type': 'volume_spike',
                    'group_type': 'single_single',
                    'group_signature': 'BTC_1h_volume_spike',
                    'success': i % 2 == 0,
                    'confidence': 0.8,
                    'return_pct': 3.5 if i % 2 == 0 else -1.0,
                    'max_drawdown': 0.5,
                    'method': 'code',
                    'lesson': f"Level 2 learning insights {i}",
                    'source_cluster': 'BTC_1h_volume_spike'
                },
                'module_intelligence': {
                    'cluster_type': 'pattern_timeframe',
                    'cluster_key': 'BTC_1h_volume_spike',
                    'braid_level': 2
                }
            }
            
            # Assign to clusters
            cluster_assignments = [
                {"cluster_type": "asset", "cluster_key": "BTC", "braid_level": 2, "consumed": False},
                {"cluster_type": "timeframe", "cluster_key": "1h", "braid_level": 2, "consumed": False},
                {"cluster_type": "pattern_timeframe", "cluster_key": "BTC_1h_volume_spike", "braid_level": 2, "consumed": False}
            ]
            prediction['cluster_key'] = cluster_assignments
            
            await self.supabase_manager.execute_query("""
                INSERT INTO AD_strands (id, kind, created_at, tags, braid_level, content, module_intelligence, cluster_key)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                prediction['id'],
                prediction['kind'],
                prediction['created_at'],
                prediction['tags'],
                prediction['braid_level'],
                json.dumps(prediction['content']),
                json.dumps(prediction['module_intelligence']),
                json.dumps(prediction['cluster_key'])
            ])
    
    async def test_context_retrieval(self):
        """Test 5: Test context retrieval for predictions"""
        print("\n🧪 Test 5: Context Retrieval")
        print("-" * 40)
        
        try:
            # Test retrieving learning insights for specific patterns
            query = """
                SELECT lesson, content, braid_level
                FROM AD_strands 
                WHERE kind = 'prediction_review'
                AND braid_level > 1
                AND content->>'asset' = 'BTC'
                AND content->>'timeframe' = '1h'
                ORDER BY braid_level DESC, created_at DESC
            """
            
            result = await self.supabase_manager.execute_query(query)
            learning_insights = [dict(row) for row in result]
            
            assert len(learning_insights) > 0, "Should have learning insights for BTC 1h"
            
            # Verify insights have lesson content
            for insight in learning_insights:
                assert insight['lesson'], "Learning insight should have lesson content"
                assert insight['braid_level'] > 1, "Should be higher than level 1"
            
            print(f"✅ Retrieved {len(learning_insights)} learning insights for BTC 1h")
            self.test_results['tests_passed'] += 1
            
        except Exception as e:
            print(f"❌ Context retrieval failed: {e}")
            self.test_results['tests_failed'] += 1
            self.test_results['errors'].append(f"Test 5: {e}")
        
        self.test_results['tests_run'] += 1
    
    async def test_consumed_status_tracking(self):
        """Test 6: Test consumed status tracking"""
        print("\n🧪 Test 6: Consumed Status Tracking")
        print("-" * 40)
        
        try:
            # Check that some strands are marked as consumed
            query = """
                SELECT COUNT(*) 
                FROM AD_strands 
                WHERE kind = 'prediction_review'
                AND cluster_key @> '[{"consumed": true}]'
            """
            
            result = await self.supabase_manager.execute_query(query)
            consumed_count = result[0][0] if result else 0
            
            assert consumed_count > 0, f"Expected some strands to be consumed, got {consumed_count}"
            
            print(f"✅ {consumed_count} strands marked as consumed")
            self.test_results['tests_passed'] += 1
            
        except Exception as e:
            print(f"❌ Consumed status tracking failed: {e}")
            self.test_results['tests_failed'] += 1
            self.test_results['errors'].append(f"Test 6: {e}")
        
        self.test_results['tests_run'] += 1
    
    async def test_cross_cluster_preservation(self):
        """Test 7: Test cross-cluster preservation"""
        print("\n🧪 Test 7: Cross-Cluster Preservation")
        print("-" * 40)
        
        try:
            # Check that strands exist in multiple clusters
            query = """
                SELECT id, cluster_key
                FROM AD_strands 
                WHERE kind = 'prediction_review'
                AND braid_level = 1
                LIMIT 5
            """
            
            result = await self.supabase_manager.execute_query(query)
            strands = [dict(row) for row in result]
            
            for strand in strands:
                cluster_assignments = json.loads(strand['cluster_key']) if isinstance(strand['cluster_key'], str) else strand['cluster_key']
                assert len(cluster_assignments) > 1, f"Strand should be in multiple clusters, got {len(cluster_assignments)}"
                
                # Check that some are consumed, some are not
                consumed_count = sum(1 for c in cluster_assignments if c.get('consumed', False))
                assert consumed_count < len(cluster_assignments), "Strand should not be consumed in all clusters"
            
            print("✅ Cross-cluster preservation working correctly")
            self.test_results['tests_passed'] += 1
            
        except Exception as e:
            print(f"❌ Cross-cluster preservation failed: {e}")
            self.test_results['tests_failed'] += 1
            self.test_results['errors'].append(f"Test 7: {e}")
        
        self.test_results['tests_run'] += 1
    
    async def test_llm_learning_analysis(self):
        """Test 8: Test LLM learning analysis"""
        print("\n🧪 Test 8: LLM Learning Analysis")
        print("-" * 40)
        
        try:
            # Check that LLM analysis was performed
            query = """
                SELECT lesson, content
                FROM AD_strands 
                WHERE kind = 'prediction_review'
                AND braid_level > 1
                AND lesson IS NOT NULL
                AND lesson != ''
                LIMIT 3
            """
            
            result = await self.supabase_manager.execute_query(query)
            llm_insights = [dict(row) for row in result]
            
            assert len(llm_insights) > 0, "Should have LLM-generated insights"
            
            for insight in llm_insights:
                assert insight['lesson'], "Should have lesson content"
                assert len(insight['lesson']) > 10, "Lesson should be substantial"
            
            print(f"✅ LLM analysis generated {len(llm_insights)} insights")
            self.test_results['tests_passed'] += 1
            
        except Exception as e:
            print(f"❌ LLM learning analysis failed: {e}")
            self.test_results['tests_failed'] += 1
            self.test_results['errors'].append(f"Test 8: {e}")
        
        self.test_results['tests_run'] += 1
    
    async def test_data_flow_integrity(self):
        """Test 9: Test data flow integrity"""
        print("\n🧪 Test 9: Data Flow Integrity")
        print("-" * 40)
        
        try:
            # Test that data flows correctly through the system
            # 1. Check that prediction_review strands exist
            query1 = "SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review'"
            result1 = await self.supabase_manager.execute_query(query1)
            prediction_count = result1[0][0] if result1 else 0
            
            # 2. Check that some have braid_level > 1
            query2 = "SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review' AND braid_level > 1"
            result2 = await self.supabase_manager.execute_query(query2)
            braid_count = result2[0][0] if result2 else 0
            
            # 3. Check that some have lessons
            query3 = "SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review' AND lesson IS NOT NULL AND lesson != ''"
            result3 = await self.supabase_manager.execute_query(query3)
            lesson_count = result3[0][0] if result3 else 0
            
            # 4. Check that some are consumed
            query4 = "SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review' AND cluster_key @> '[{\"consumed\": true}]'"
            result4 = await self.supabase_manager.execute_query(query4)
            consumed_count = result4[0][0] if result4 else 0
            
            assert prediction_count > 0, "Should have prediction_review strands"
            assert braid_count > 0, "Should have higher level braids"
            assert lesson_count > 0, "Should have lessons"
            assert consumed_count > 0, "Should have consumed strands"
            
            print(f"✅ Data flow integrity verified:")
            print(f"   - {prediction_count} prediction_review strands")
            print(f"   - {braid_count} higher level braids")
            print(f"   - {lesson_count} with lessons")
            print(f"   - {consumed_count} consumed strands")
            
            self.test_results['tests_passed'] += 1
            
        except Exception as e:
            print(f"❌ Data flow integrity failed: {e}")
            self.test_results['tests_failed'] += 1
            self.test_results['errors'].append(f"Test 9: {e}")
        
        self.test_results['tests_run'] += 1
    
    async def test_edge_cases(self):
        """Test 10: Test edge cases and error handling"""
        print("\n🧪 Test 10: Edge Cases and Error Handling")
        print("-" * 40)
        
        try:
            # Test with empty data
            empty_clusters = await self.simplified_cil.learning_system.process_all_clusters()
            assert isinstance(empty_clusters, dict), "Should handle empty data gracefully"
            
            # Test with malformed data
            malformed_prediction = {
                'id': f"malformed_{int(datetime.now().timestamp())}",
                'kind': 'prediction_review',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'tags': ['cil', 'learning', 'prediction_review'],
                'braid_level': 1,
                'content': {
                    'asset': 'MALFORMED',
                    'timeframe': '1h',
                    'success': True,
                    'confidence': 0.5
                    # Missing required fields
                },
                'module_intelligence': {},
                'cluster_key': []
            }
            
            # This should not crash the system
            await self.insert_prediction_strand(malformed_prediction)
            
            print("✅ Edge cases handled gracefully")
            self.test_results['tests_passed'] += 1
            
        except Exception as e:
            print(f"❌ Edge cases failed: {e}")
            self.test_results['tests_failed'] += 1
            self.test_results['errors'].append(f"Test 10: {e}")
        
        self.test_results['tests_run'] += 1
    
    def print_test_results(self):
        """Print comprehensive test results"""
        print("\n" + "=" * 60)
        print("🏁 COMPREHENSIVE TEST RESULTS")
        print("=" * 60)
        
        print(f"Tests Run: {self.test_results['tests_run']}")
        print(f"Tests Passed: {self.test_results['tests_passed']}")
        print(f"Tests Failed: {self.test_results['tests_failed']}")
        print(f"Braids Created: {self.test_results['braids_created']}")
        print(f"Max Braid Level: {self.test_results['max_braid_level']}")
        
        if self.test_results['errors']:
            print("\n❌ ERRORS:")
            for error in self.test_results['errors']:
                print(f"  - {error}")
        
        success_rate = (self.test_results['tests_passed'] / self.test_results['tests_run']) * 100 if self.test_results['tests_run'] > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("🎉 EXCELLENT! Learning system is working correctly!")
        elif success_rate >= 70:
            print("✅ GOOD! Learning system is mostly working with some issues.")
        else:
            print("⚠️  NEEDS WORK! Learning system has significant issues.")


async def main():
    """Run the comprehensive test suite"""
    test_suite = ComprehensiveLearningTest()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
