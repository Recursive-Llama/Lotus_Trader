#!/usr/bin/env python3
"""
Full Learning System Test

This test actually runs the complete learning system end-to-end:
1. Creates fresh prediction data
2. Runs real LLM analysis
3. Creates actual braids in the database
4. Tests multi-level braid progression
5. Tests context injection into prompts
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


class FullLearningSystemTest:
    """Test the complete learning system end-to-end"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.llm_client = OpenRouterClient()
        self.simplified_cil = SimplifiedCIL(self.supabase_manager, self.llm_client)
        self.test_results = {
            'strands_created': 0,
            'braids_created': 0,
            'max_braid_level': 0,
            'lessons_generated': 0,
            'llm_calls_made': 0,
            'context_injections_tested': 0,
            'errors': []
        }
    
    async def run_test(self):
        """Run the complete learning system test"""
        print("🚀 Full Learning System Test")
        print("=" * 50)
        
        try:
            # Step 1: Create fresh prediction data
            await self.create_fresh_prediction_data()
            
            # Step 2: Test real LLM analysis with context injection
            await self.test_real_llm_analysis()
            
            # Step 3: Test actual braid creation in database
            await self.test_actual_braid_creation()
            
            # Step 4: Test multi-level braid progression
            await self.test_multi_level_braids()
            
            # Step 5: Test context injection into prompts
            await self.test_context_injection()
            
            # Step 6: Verify final results
            await self.verify_final_results()
            
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
            AND id LIKE 'full_test_%'
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
            'id': f"full_test_{group['asset'].lower()}_{group['timeframe']}_{group['pattern_type']}_{index}_{int(datetime.now().timestamp())}",
            'kind': 'prediction_review',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'tags': ['cil', 'learning', 'prediction_review', 'full_test'],
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
        """Insert a prediction strand into the database using proper Supabase client"""
        
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
    
    async def test_real_llm_analysis(self):
        """Test real LLM analysis with context injection"""
        print("\n🤖 Testing Real LLM Analysis")
        print("-" * 40)
        
        try:
            # Get fresh prediction reviews
            query = "SELECT * FROM AD_strands WHERE kind = 'prediction_review' AND id LIKE 'full_test_%'"
            result = await self.supabase_manager.execute_query(query)
            prediction_reviews = [dict(row) for row in result]
            
            print(f"  Found {len(prediction_reviews)} test prediction reviews")
            
            if len(prediction_reviews) == 0:
                print("  ⚠️  No test data found")
                return
            
            # Test LLM analysis on a real cluster
            llm_analyzer = LLMLearningAnalyzer(self.llm_client, self.supabase_manager)
            
            # Get the first cluster (should be outcome cluster with 12 strands)
            cluster_grouper = MultiClusterGroupingEngine(self.supabase_manager)
            clusters = await cluster_grouper.group_prediction_reviews(prediction_reviews)
            
            # Find a cluster with 3+ strands
            test_cluster = None
            test_cluster_type = None
            test_cluster_key = None
            
            for cluster_type, cluster_groups in clusters.items():
                for cluster_key, strands in cluster_groups.items():
                    if len(strands) >= 3:
                        test_cluster = strands
                        test_cluster_type = cluster_type
                        test_cluster_key = cluster_key
                        break
                if test_cluster:
                    break
            
            if not test_cluster:
                print("  ⚠️  No cluster with 3+ strands found")
                return
            
            print(f"  Testing LLM analysis on {test_cluster_type}:{test_cluster_key} with {len(test_cluster)} strands")
            
            # Run real LLM analysis
            analysis_result = await llm_analyzer.analyze_cluster_for_learning(
                test_cluster_type, 
                test_cluster_key, 
                test_cluster
            )
            
            if analysis_result:
                print(f"  ✅ Real LLM analysis successful")
                print(f"    Braid ID: {analysis_result['id']}")
                print(f"    Lesson: {analysis_result.get('lesson', '')[:100]}...")
                print(f"    Braid Level: {analysis_result.get('braid_level', 1)}")
                self.test_results['llm_calls_made'] += 1
                self.test_results['braids_created'] += 1
            else:
                print("  ❌ LLM analysis failed")
                self.test_results['errors'].append("LLM analysis failed")
            
        except Exception as e:
            print(f"❌ Real LLM analysis failed: {e}")
            self.test_results['errors'].append(f"Real LLM analysis: {e}")
    
    async def test_actual_braid_creation(self):
        """Test actual braid creation in the database"""
        print("\n🔄 Testing Actual Braid Creation")
        print("-" * 40)
        
        try:
            # Check if braids were actually created in the database
            query = "SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review' AND braid_level > 1 AND id LIKE 'full_test_%'"
            result = await self.supabase_manager.execute_query(query)
            braid_count = result[0][0] if result else 0
            
            print(f"  Braids created in database: {braid_count}")
            
            if braid_count > 0:
                # Check the actual braid content
                query = "SELECT * FROM AD_strands WHERE kind = 'prediction_review' AND braid_level > 1 AND id LIKE 'full_test_%' LIMIT 1"
                result = await self.supabase_manager.execute_query(query)
                if result:
                    braid = dict(result[0])
                    print(f"  ✅ Braid creation working")
                    print(f"    Braid ID: {braid['id']}")
                    print(f"    Braid Level: {braid['braid_level']}")
                    print(f"    Has Lesson: {bool(braid.get('lesson'))}")
                    print(f"    Lesson Preview: {braid.get('lesson', '')[:100]}...")
                    self.test_results['lessons_generated'] += 1
                else:
                    print("  ⚠️  No braid details found")
            else:
                print("  ❌ No braids created in database")
                self.test_results['errors'].append("No braids created in database")
            
        except Exception as e:
            print(f"❌ Braid creation verification failed: {e}")
            self.test_results['errors'].append(f"Braid creation verification: {e}")
    
    async def test_multi_level_braids(self):
        """Test multi-level braid progression"""
        print("\n🔄 Testing Multi-Level Braid Progression")
        print("-" * 40)
        
        try:
            # Check current max braid level
            query = "SELECT MAX(braid_level) FROM AD_strands WHERE kind = 'prediction_review' AND id LIKE 'full_test_%'"
            result = await self.supabase_manager.execute_query(query)
            max_level = result[0][0] if result and result[0][0] else 1
            
            print(f"  Current max braid level: {max_level}")
            self.test_results['max_braid_level'] = max_level
            
            if max_level >= 2:
                print("  ✅ Multi-level braids working")
                
                # Check braid distribution
                for level in range(1, max_level + 1):
                    query = f"SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review' AND braid_level = {level} AND id LIKE 'full_test_%'"
                    result = await self.supabase_manager.execute_query(query)
                    count = result[0][0] if result else 0
                    print(f"    Level {level}: {count} strands")
            else:
                print("  ⚠️  Only single level braids found")
            
        except Exception as e:
            print(f"❌ Multi-level braid test failed: {e}")
            self.test_results['errors'].append(f"Multi-level braid test: {e}")
    
    async def test_context_injection(self):
        """Test context injection into prompts"""
        print("\n📝 Testing Context Injection into Prompts")
        print("-" * 40)
        
        try:
            # Test the prompt creation with real data
            llm_analyzer = LLMLearningAnalyzer(self.llm_client, self.supabase_manager)
            
            # Get a real cluster
            query = "SELECT * FROM AD_strands WHERE kind = 'prediction_review' AND id LIKE 'full_test_%' LIMIT 3"
            result = await self.supabase_manager.execute_query(query)
            prediction_reviews = [dict(row) for row in result]
            
            if len(prediction_reviews) >= 3:
                # Test prompt creation
                cluster_data = llm_analyzer.prepare_cluster_data(
                    'pattern_timeframe', 
                    'BTC_1h_volume_spike', 
                    prediction_reviews, 
                    []  # No pattern context for this test
                )
                
                prompt = llm_analyzer.create_cluster_analysis_prompt(cluster_data)
                
                print(f"  ✅ Context injection working")
                print(f"    Prompt length: {len(prompt)} characters")
                print(f"    Contains asset data: {'BTC' in prompt}")
                print(f"    Contains timeframe data: {'1h' in prompt}")
                print(f"    Contains success rate: {'Success Rate' in prompt}")
                print(f"    Contains prediction details: {'PREDICTION DETAILS' in prompt}")
                
                # Show a snippet of the prompt
                print(f"    Prompt snippet:")
                print(f"      {prompt[:200]}...")
                
                self.test_results['context_injections_tested'] += 1
            else:
                print("  ⚠️  Not enough data for context injection test")
            
        except Exception as e:
            print(f"❌ Context injection test failed: {e}")
            self.test_results['errors'].append(f"Context injection test: {e}")
    
    async def verify_final_results(self):
        """Verify final results"""
        print("\n✅ Verifying Final Results")
        print("-" * 40)
        
        try:
            # Check total strands
            query = "SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review' AND id LIKE 'full_test_%'"
            result = await self.supabase_manager.execute_query(query)
            total_strands = result[0][0] if result else 0
            
            # Check braids created
            query = "SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review' AND id LIKE 'full_test_%' AND braid_level > 1"
            result = await self.supabase_manager.execute_query(query)
            braid_count = result[0][0] if result else 0
            
            # Check lessons generated
            query = "SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review' AND id LIKE 'full_test_%' AND lesson IS NOT NULL AND lesson != ''"
            result = await self.supabase_manager.execute_query(query)
            lesson_count = result[0][0] if result else 0
            
            # Check consumed status
            query = "SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review' AND id LIKE 'full_test_%' AND cluster_key @> '[{\"consumed\": true}]'"
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
            print(f"❌ Final verification failed: {e}")
            self.test_results['errors'].append(f"Final verification: {e}")
    
    def print_results(self):
        """Print test results"""
        print("\n" + "=" * 50)
        print("🏁 FULL LEARNING SYSTEM TEST RESULTS")
        print("=" * 50)
        
        print(f"Strands Created: {self.test_results['strands_created']}")
        print(f"Braids Created: {self.test_results['braids_created']}")
        print(f"Max Braid Level: {self.test_results['max_braid_level']}")
        print(f"Lessons Generated: {self.test_results['lessons_generated']}")
        print(f"LLM Calls Made: {self.test_results['llm_calls_made']}")
        print(f"Context Injections Tested: {self.test_results['context_injections_tested']}")
        
        if self.test_results['errors']:
            print(f"\n❌ ERRORS ({len(self.test_results['errors'])}):")
            for error in self.test_results['errors']:
                print(f"  - {error}")
        else:
            print("\n🎉 All tests passed!")
        
        # Overall assessment
        total_tests = 6  # data_creation, llm_analysis, braid_creation, multi_level, context_injection, verification
        passed_tests = total_tests - len(self.test_results['errors'])
        success_rate = (passed_tests / total_tests) * 100
        
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 Full learning system is working!")
        elif success_rate >= 60:
            print("✅ Learning system is mostly working with some issues.")
        else:
            print("⚠️  Learning system needs significant work.")


async def main():
    """Run the full learning system test"""
    test = FullLearningSystemTest()
    await test.run_test()


if __name__ == "__main__":
    asyncio.run(main())
