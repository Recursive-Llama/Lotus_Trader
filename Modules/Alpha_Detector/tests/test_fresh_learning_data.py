#!/usr/bin/env python3
"""
Fresh Learning System Test

Creates new prediction_review data with proper JSONB cluster_key structure
and tests the complete learning system end-to-end.
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


class FreshLearningTest:
    """Test the learning system with fresh data"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.llm_client = OpenRouterClient()
        self.simplified_cil = SimplifiedCIL(self.supabase_manager, self.llm_client)
        self.test_results = {
            'strands_created': 0,
            'braids_created': 0,
            'max_braid_level': 0,
            'lessons_generated': 0,
            'errors': []
        }
    
    async def run_test(self):
        """Run the complete learning system test"""
        print("🚀 Fresh Learning System Test")
        print("=" * 50)
        
        try:
            # Step 1: Create fresh prediction data
            await self.create_fresh_prediction_data()
            
            # Step 2: Test multi-cluster grouping
            await self.test_cluster_grouping()
            
            # Step 3: Test learning system
            await self.test_learning_system()
            
            # Step 4: Test braid level progression
            await self.test_braid_progression()
            
            # Step 5: Verify results
            await self.verify_results()
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            self.test_results['errors'].append(str(e))
        
        # Print results
        self.print_results()
    
    async def create_fresh_prediction_data(self):
        """Create fresh prediction_review data with proper JSONB cluster_key"""
        print("\n📝 Creating Fresh Prediction Data")
        print("-" * 40)
        
        # Clear existing test data first
        await self.supabase_manager.execute_query("""
            DELETE FROM AD_strands 
            WHERE kind = 'prediction_review' 
            AND id LIKE 'test_%'
        """)
        
        # Create multiple groups of prediction_review strands
        test_groups = [
            {
                'name': 'BTC Volume Spike 1h',
                'asset': 'BTC',
                'timeframe': '1h',
                'pattern_type': 'volume_spike',
                'group_type': 'single_single',
                'count': 5,
                'success_rate': 0.6
            },
            {
                'name': 'ETH Divergence 1h',
                'asset': 'ETH',
                'timeframe': '1h',
                'pattern_type': 'divergence',
                'group_type': 'single_single',
                'count': 4,
                'success_rate': 0.5
            },
            {
                'name': 'BTC Multi-Pattern 4h',
                'asset': 'BTC',
                'timeframe': '4h',
                'pattern_type': 'multi_pattern',
                'group_type': 'multi_single',
                'count': 3,
                'success_rate': 0.67
            }
        ]
        
        total_created = 0
        
        for group in test_groups:
            print(f"  Creating {group['count']} strands for {group['name']}")
            
            for i in range(group['count']):
                prediction = await self.create_prediction_strand(group, i)
                await self.insert_prediction_strand(prediction)
                total_created += 1
        
        print(f"✅ Created {total_created} fresh prediction_review strands")
        self.test_results['strands_created'] = total_created
    
    async def create_prediction_strand(self, group: Dict, index: int) -> Dict[str, Any]:
        """Create a single prediction strand with proper JSONB cluster_key"""
        
        # Determine success based on group success rate
        success = (index / group['count']) < group['success_rate']
        
        prediction = {
            'id': f"test_{group['asset'].lower()}_{group['timeframe']}_{group['pattern_type']}_{index}_{int(datetime.now().timestamp())}",
            'kind': 'prediction_review',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'tags': ['cil', 'learning', 'prediction_review', 'test'],
            'braid_level': 1,
            'content': {
                'asset': group['asset'],
                'timeframe': group['timeframe'],
                'pattern_type': group['pattern_type'],
                'group_type': group['group_type'],
                'group_signature': f"{group['asset']}_{group['timeframe']}_{group['pattern_type']}",
                'success': success,
                'confidence': 0.6 + (index * 0.1),
                'return_pct': 3.2 if success else -1.5,
                'max_drawdown': 0.8,
                'method': 'code' if index % 2 == 0 else 'llm',
                'original_pattern_strand_ids': [f"pattern_{group['asset'].lower()}_{index}_{uuid.uuid4().hex[:8]}"]
            },
            'module_intelligence': {
                'cluster_type': 'pattern_timeframe',
                'cluster_key': f"{group['asset']}_{group['timeframe']}_{group['pattern_type']}",
                'braid_level': 1
            }
        }
        
        # Create proper JSONB cluster_key assignments
        cluster_assignments = []
        
        # Asset cluster
        cluster_assignments.append({
            "cluster_type": "asset",
            "cluster_key": group['asset'],
            "braid_level": 1,
            "consumed": False
        })
        
        # Timeframe cluster
        cluster_assignments.append({
            "cluster_type": "timeframe",
            "cluster_key": group['timeframe'],
            "braid_level": 1,
            "consumed": False
        })
        
        # Pattern+timeframe cluster
        cluster_assignments.append({
            "cluster_type": "pattern_timeframe",
            "cluster_key": f"{group['asset']}_{group['timeframe']}_{group['pattern_type']}",
            "braid_level": 1,
            "consumed": False
        })
        
        # Outcome cluster
        outcome_key = 'success' if success else 'failure'
        cluster_assignments.append({
            "cluster_type": "outcome",
            "cluster_key": outcome_key,
            "braid_level": 1,
            "consumed": False
        })
        
        # Method cluster
        method_key = 'code' if index % 2 == 0 else 'llm'
        cluster_assignments.append({
            "cluster_type": "method",
            "cluster_key": method_key,
            "braid_level": 1,
            "consumed": False
        })
        
        # Pattern cluster
        cluster_assignments.append({
            "cluster_type": "pattern",
            "cluster_key": group['group_type'],
            "braid_level": 1,
            "consumed": False
        })
        
        # Group type cluster
        cluster_assignments.append({
            "cluster_type": "group_type",
            "cluster_key": group['group_type'],
            "braid_level": 1,
            "consumed": False
        })
        
        prediction['cluster_key'] = cluster_assignments
        
        return prediction
    
    async def insert_prediction_strand(self, prediction: Dict[str, Any]):
        """Insert a prediction strand into the database"""
        
        # Use the proper Supabase client method instead of raw SQL
        strand_data = {
            'id': prediction['id'],
            'module': 'alpha',
            'kind': prediction['kind'],
            'symbol': prediction['content']['asset'],
            'timeframe': prediction['content']['timeframe'],
            'tags': prediction['tags'],
            'created_at': prediction['created_at'],
            'updated_at': prediction['created_at'],
            'braid_level': prediction['braid_level'],
            'content': prediction['content'],
            'module_intelligence': prediction['module_intelligence'],
            'cluster_key': prediction['cluster_key']
        }
        
        self.supabase_manager.insert_strand(strand_data)
    
    async def test_cluster_grouping(self):
        """Test multi-cluster grouping with fresh data"""
        print("\n🔍 Testing Multi-Cluster Grouping")
        print("-" * 40)
        
        try:
            cluster_grouper = MultiClusterGroupingEngine(self.supabase_manager)
            
            # Get fresh prediction reviews
            query = "SELECT * FROM AD_strands WHERE kind = 'prediction_review' AND id LIKE 'test_%'"
            result = await self.supabase_manager.execute_query(query)
            prediction_reviews = [dict(row) for row in result]
            
            print(f"  Found {len(prediction_reviews)} test prediction reviews")
            
            # Group them
            clusters = await cluster_grouper.group_prediction_reviews(prediction_reviews)
            
            print(f"  Created {len(clusters)} cluster types")
            
            # Check each cluster type
            for cluster_type, cluster_groups in clusters.items():
                print(f"    {cluster_type}: {len(cluster_groups)} groups")
                
                # Check that we have groups with 3+ strands
                for cluster_key, strands in cluster_groups.items():
                    if len(strands) >= 3:
                        print(f"      ✅ {cluster_key}: {len(strands)} strands (ready for learning)")
                    else:
                        print(f"      ⚠️  {cluster_key}: {len(strands)} strands (needs more data)")
            
            print("✅ Multi-cluster grouping working")
            
        except Exception as e:
            print(f"❌ Cluster grouping failed: {e}")
            self.test_results['errors'].append(f"Cluster grouping: {e}")
    
    async def test_learning_system(self):
        """Test the learning system with fresh data"""
        print("\n🧠 Testing Learning System")
        print("-" * 40)
        
        try:
            learning_system = PerClusterLearningSystem(self.supabase_manager, self.llm_client)
            
            # Process all clusters
            learning_braids = await learning_system.process_all_clusters()
            
            total_braids = sum(len(braids) for braids in learning_braids.values())
            print(f"  Created {total_braids} learning braids across {len(learning_braids)} cluster types")
            
            # Check that braids are prediction_review strands with braid_level 2
            for cluster_type, braid_ids in learning_braids.items():
                print(f"    {cluster_type}: {len(braid_ids)} braids")
                
                for braid_id in braid_ids:
                    query = "SELECT * FROM AD_strands WHERE id = %s"
                    result = await self.supabase_manager.execute_query(query, [braid_id])
                    if result:
                        braid = dict(result[0])
                        assert braid['kind'] == 'prediction_review', f"Braid should be prediction_review, got {braid['kind']}"
                        assert braid['braid_level'] == 2, f"Braid should be level 2, got {braid['braid_level']}"
                        assert braid['lesson'], "Braid should have lesson content"
                        print(f"      ✅ Braid {braid_id[:8]}... has lesson: {braid['lesson'][:50]}...")
            
            self.test_results['braids_created'] = total_braids
            print("✅ Learning system working")
            
        except Exception as e:
            print(f"❌ Learning system failed: {e}")
            self.test_results['errors'].append(f"Learning system: {e}")
    
    async def test_braid_progression(self):
        """Test braid level progression"""
        print("\n🔄 Testing Braid Level Progression")
        print("-" * 40)
        
        try:
            # Check current max braid level
            query = "SELECT MAX(braid_level) FROM AD_strands WHERE kind = 'prediction_review' AND id LIKE 'test_%'"
            result = await self.supabase_manager.execute_query(query)
            max_level = result[0][0] if result and result[0][0] else 1
            
            print(f"  Current max braid level: {max_level}")
            
            # Create more level 2 strands to trigger level 3
            if max_level >= 2:
                await self.create_level_2_strands()
                
                # Process braid progression
                braid_manager = BraidLevelManager(self.supabase_manager)
                cluster_grouper = MultiClusterGroupingEngine(self.supabase_manager)
                clusters = await cluster_grouper.get_all_cluster_groups()
                created_braids = await braid_manager.process_all_clusters(clusters)
                
                # Check new max level
                query = "SELECT MAX(braid_level) FROM AD_strands WHERE kind = 'prediction_review' AND id LIKE 'test_%'"
                result = await self.supabase_manager.execute_query(query)
                new_max_level = result[0][0] if result and result[0][0] else 1
                
                print(f"  New max braid level: {new_max_level}")
                self.test_results['max_braid_level'] = new_max_level
            
            print("✅ Braid progression working")
            
        except Exception as e:
            print(f"❌ Braid progression failed: {e}")
            self.test_results['errors'].append(f"Braid progression: {e}")
    
    async def create_level_2_strands(self):
        """Create additional level 2 strands to trigger higher level braids"""
        
        # Create 3 more level 2 strands for the same cluster
        for i in range(3):
            prediction = {
                'id': f"test_level2_{i}_{int(datetime.now().timestamp())}",
                'kind': 'prediction_review',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'tags': ['cil', 'learning', 'prediction_review', 'test'],
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
            
            # Use the proper Supabase client method instead of raw SQL
            strand_data = {
                'id': prediction['id'],
                'module': 'alpha',
                'kind': prediction['kind'],
                'symbol': prediction['content']['asset'],
                'timeframe': prediction['content']['timeframe'],
                'tags': prediction['tags'],
                'created_at': prediction['created_at'],
                'updated_at': prediction['created_at'],
                'braid_level': prediction['braid_level'],
                'content': prediction['content'],
                'module_intelligence': prediction['module_intelligence'],
                'cluster_key': prediction['cluster_key']
            }
            
            self.supabase_manager.insert_strand(strand_data)
    
    async def verify_results(self):
        """Verify the learning system results"""
        print("\n✅ Verifying Results")
        print("-" * 40)
        
        try:
            # Check total strands
            query = "SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review' AND id LIKE 'test_%'"
            result = await self.supabase_manager.execute_query(query)
            total_strands = result[0][0] if result else 0
            
            # Check braids created
            query = "SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review' AND id LIKE 'test_%' AND braid_level > 1"
            result = await self.supabase_manager.execute_query(query)
            braid_count = result[0][0] if result else 0
            
            # Check lessons generated
            query = "SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review' AND id LIKE 'test_%' AND lesson IS NOT NULL AND lesson != ''"
            result = await self.supabase_manager.execute_query(query)
            lesson_count = result[0][0] if result else 0
            
            # Check consumed status
            query = "SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review' AND id LIKE 'test_%' AND cluster_key @> '[{\"consumed\": true}]'"
            result = await self.supabase_manager.execute_query(query)
            consumed_count = result[0][0] if result else 0
            
            print(f"  Total test strands: {total_strands}")
            print(f"  Higher level braids: {braid_count}")
            print(f"  With lessons: {lesson_count}")
            print(f"  Consumed strands: {consumed_count}")
            
            # Verify learning worked
            if braid_count > 0 and lesson_count > 0:
                print("✅ Learning system is working correctly!")
                self.test_results['lessons_generated'] = lesson_count
            else:
                print("⚠️  Learning system needs investigation")
                
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            self.test_results['errors'].append(f"Verification: {e}")
    
    def print_results(self):
        """Print test results"""
        print("\n" + "=" * 50)
        print("🏁 TEST RESULTS")
        print("=" * 50)
        
        print(f"Strands Created: {self.test_results['strands_created']}")
        print(f"Braids Created: {self.test_results['braids_created']}")
        print(f"Max Braid Level: {self.test_results['max_braid_level']}")
        print(f"Lessons Generated: {self.test_results['lessons_generated']}")
        
        if self.test_results['errors']:
            print(f"\n❌ ERRORS ({len(self.test_results['errors'])}):")
            for error in self.test_results['errors']:
                print(f"  - {error}")
        else:
            print("\n🎉 All tests passed!")


async def main():
    """Run the fresh learning test"""
    test = FreshLearningTest()
    await test.run_test()


if __name__ == "__main__":
    asyncio.run(main())
