#!/usr/bin/env python3
"""
Detailed Learning System Test

This test provides step-by-step detailed output to understand exactly what the learning system is doing.
"""

import asyncio
import json
import sys
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.intelligence.system_control.central_intelligence_layer.simplified_cil import SimplifiedCIL
from src.intelligence.system_control.central_intelligence_layer.per_cluster_learning_system import PerClusterLearningSystem
from src.intelligence.system_control.central_intelligence_layer.multi_cluster_grouping_engine import MultiClusterGroupingEngine
from src.intelligence.system_control.central_intelligence_layer.llm_learning_analyzer import LLMLearningAnalyzer
from src.intelligence.system_control.central_intelligence_layer.braid_level_manager import BraidLevelManager
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class DetailedLearningTest:
    """Detailed test with step-by-step output"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.llm_client = OpenRouterClient()
        self.test_results = {
            'initial_strands': 0,
            'braids_created': 0,
            'braid_levels': [],
            'clusters_processed': 0,
            'llm_calls_made': 0,
            'errors': []
        }
    
    async def run_detailed_test(self):
        """Run detailed test with step-by-step output"""
        print("🔬 DETAILED LEARNING SYSTEM TEST")
        print("=" * 50)
        print("This test will show exactly what happens step by step")
        print()
        
        try:
            # Step 1: Create initial test data
            await self.step_1_create_initial_data()
            
            # Step 2: Test clustering
            await self.step_2_test_clustering()
            
            # Step 3: Test braid creation
            await self.step_3_test_braid_creation()
            
            # Step 4: Verify results
            await self.step_4_verify_results()
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['errors'].append(str(e))
        
        # Print final summary
        self.print_final_summary()
    
    async def step_1_create_initial_data(self):
        """Step 1: Create initial test data"""
        print("📊 STEP 1: Creating Initial Test Data")
        print("-" * 40)
        
        # Create exactly 6 prediction strands (2 clusters of 3 each)
        test_data = [
            # Cluster 1: BTC 1h volume spikes (3 predictions)
            {
                'id': f"test_btc_1_{uuid.uuid4().hex[:8]}",
                'module': 'alpha',
                'kind': 'prediction_review',
                'symbol': 'BTC',
                'timeframe': '1h',
                'tags': ['cil', 'test'],
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'braid_level': 1,
                'lesson': '',
                'content': {
                    'asset': 'BTC',
                    'timeframe': '1h',
                    'pattern_type': 'volume_spike',
                    'success': True,
                    'confidence': 0.85,
                    'return_pct': 3.2,
                    'max_drawdown': 0.8,
                    'method': 'code',
                    'group_type': 'single_single',
                    'group_signature': 'BTC_1h_volume_spike'
                },
                'module_intelligence': {
                    'cluster_type': 'pattern_timeframe',
                    'cluster_key': 'BTC_1h_volume_spike',
                    'braid_level': 1
                },
                'cluster_key': []
            },
            {
                'id': f"test_btc_2_{uuid.uuid4().hex[:8]}",
                'module': 'alpha',
                'kind': 'prediction_review',
                'symbol': 'BTC',
                'timeframe': '1h',
                'tags': ['cil', 'test'],
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'braid_level': 1,
                'lesson': '',
                'content': {
                    'asset': 'BTC',
                    'timeframe': '1h',
                    'pattern_type': 'volume_spike',
                    'success': False,
                    'confidence': 0.65,
                    'return_pct': -1.5,
                    'max_drawdown': 2.1,
                    'method': 'llm',
                    'group_type': 'single_single',
                    'group_signature': 'BTC_1h_volume_spike'
                },
                'module_intelligence': {
                    'cluster_type': 'pattern_timeframe',
                    'cluster_key': 'BTC_1h_volume_spike',
                    'braid_level': 1
                },
                'cluster_key': []
            },
            {
                'id': f"test_btc_3_{uuid.uuid4().hex[:8]}",
                'module': 'alpha',
                'kind': 'prediction_review',
                'symbol': 'BTC',
                'timeframe': '1h',
                'tags': ['cil', 'test'],
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'braid_level': 1,
                'lesson': '',
                'content': {
                    'asset': 'BTC',
                    'timeframe': '1h',
                    'pattern_type': 'volume_spike',
                    'success': True,
                    'confidence': 0.92,
                    'return_pct': 4.1,
                    'max_drawdown': 0.5,
                    'method': 'code',
                    'group_type': 'single_single',
                    'group_signature': 'BTC_1h_volume_spike'
                },
                'module_intelligence': {
                    'cluster_type': 'pattern_timeframe',
                    'cluster_key': 'BTC_1h_volume_spike',
                    'braid_level': 1
                },
                'cluster_key': []
            },
            # Cluster 2: ETH 4h momentum (3 predictions)
            {
                'id': f"test_eth_1_{uuid.uuid4().hex[:8]}",
                'module': 'alpha',
                'kind': 'prediction_review',
                'symbol': 'ETH',
                'timeframe': '4h',
                'tags': ['cil', 'test'],
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'braid_level': 1,
                'lesson': '',
                'content': {
                    'asset': 'ETH',
                    'timeframe': '4h',
                    'pattern_type': 'momentum',
                    'success': True,
                    'confidence': 0.78,
                    'return_pct': 2.8,
                    'max_drawdown': 1.2,
                    'method': 'code',
                    'group_type': 'single_single',
                    'group_signature': 'ETH_4h_momentum'
                },
                'module_intelligence': {
                    'cluster_type': 'pattern_timeframe',
                    'cluster_key': 'ETH_4h_momentum',
                    'braid_level': 1
                },
                'cluster_key': []
            },
            {
                'id': f"test_eth_2_{uuid.uuid4().hex[:8]}",
                'module': 'alpha',
                'kind': 'prediction_review',
                'symbol': 'ETH',
                'timeframe': '4h',
                'tags': ['cil', 'test'],
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'braid_level': 1,
                'lesson': '',
                'content': {
                    'asset': 'ETH',
                    'timeframe': '4h',
                    'pattern_type': 'momentum',
                    'success': True,
                    'confidence': 0.88,
                    'return_pct': 3.5,
                    'max_drawdown': 0.9,
                    'method': 'code',
                    'group_type': 'single_single',
                    'group_signature': 'ETH_4h_momentum'
                },
                'module_intelligence': {
                    'cluster_type': 'pattern_timeframe',
                    'cluster_key': 'ETH_4h_momentum',
                    'braid_level': 1
                },
                'cluster_key': []
            },
            {
                'id': f"test_eth_3_{uuid.uuid4().hex[:8]}",
                'module': 'alpha',
                'kind': 'prediction_review',
                'symbol': 'ETH',
                'timeframe': '4h',
                'tags': ['cil', 'test'],
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'braid_level': 1,
                'lesson': '',
                'content': {
                    'asset': 'ETH',
                    'timeframe': '4h',
                    'pattern_type': 'momentum',
                    'success': False,
                    'confidence': 0.72,
                    'return_pct': -0.8,
                    'max_drawdown': 1.8,
                    'method': 'llm',
                    'group_type': 'single_single',
                    'group_signature': 'ETH_4h_momentum'
                },
                'module_intelligence': {
                    'cluster_type': 'pattern_timeframe',
                    'cluster_key': 'ETH_4h_momentum',
                    'braid_level': 1
                },
                'cluster_key': []
            }
        ]
        
        # Insert strands
        inserted_count = 0
        for strand in test_data:
            try:
                result = self.supabase_manager.insert_strand(strand)
                if result:
                    inserted_count += 1
                    print(f"  ✅ Inserted: {strand['id']} - {strand['content']['asset']} {strand['content']['timeframe']}")
                else:
                    print(f"  ❌ Failed: {strand['id']}")
            except Exception as e:
                print(f"  ❌ Error inserting {strand['id']}: {e}")
        
        self.test_results['initial_strands'] = inserted_count
        print(f"\n📊 Created {inserted_count}/6 initial strands")
        
        # Verify database state
        result = self.supabase_manager.client.table('ad_strands').select('id', count='exact').execute()
        total_strands = result.count
        print(f"📊 Total strands in database: {total_strands}")
    
    async def step_2_test_clustering(self):
        """Step 2: Test clustering"""
        print("\n🔍 STEP 2: Testing Clustering")
        print("-" * 30)
        
        grouping_engine = MultiClusterGroupingEngine(self.supabase_manager)
        
        # Get all cluster groups
        print("  Getting cluster groups...")
        clusters = await grouping_engine.get_all_cluster_groups()
        
        print(f"  Found {len(clusters)} cluster types:")
        for cluster_type, groups in clusters.items():
            print(f"    {cluster_type}: {len(groups)} groups")
            for group_key, reviews in groups.items():
                print(f"      {group_key}: {len(reviews)} reviews")
                if len(reviews) >= 3:
                    print(f"        ✅ Ready for braiding (≥3 reviews)")
                else:
                    print(f"        ❌ Not ready for braiding (<3 reviews)")
        
        self.test_results['clusters_processed'] = sum(len(groups) for groups in clusters.values())
    
    async def step_3_test_braid_creation(self):
        """Step 3: Test braid creation"""
        print("\n🎯 STEP 3: Testing Braid Creation")
        print("-" * 35)
        
        # Initialize learning system
        learning_system = PerClusterLearningSystem(self.supabase_manager, self.llm_client)
        
        print("  Running learning system...")
        try:
            # Run learning system
            result = await learning_system.process_all_clusters()
            
            if result:
                print(f"  ✅ Learning cycle completed")
                print(f"  📊 Result: {result}")
            else:
                print(f"  ❌ Learning cycle failed")
                
        except Exception as e:
            print(f"  ❌ Error in learning cycle: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['errors'].append(str(e))
    
    async def step_4_verify_results(self):
        """Step 4: Verify results"""
        print("\n🔍 STEP 4: Verifying Results")
        print("-" * 30)
        
        # Get all strands
        result = self.supabase_manager.client.table('ad_strands').select('*').execute()
        all_strands = result.data
        
        print(f"📊 Total strands in database: {len(all_strands)}")
        
        # Count by braid level
        braid_levels = {}
        for strand in all_strands:
            level = strand.get('braid_level', 0)
            braid_levels[level] = braid_levels.get(level, 0) + 1
        
        print(f"📈 Braid level distribution:")
        for level in sorted(braid_levels.keys()):
            count = braid_levels[level]
            print(f"  Level {level}: {count} strands")
            if level > 1:
                self.test_results['braid_levels'].append(level)
        
        # Count braids created
        braids_created = len([s for s in all_strands if s.get('braid_level', 0) > 1])
        self.test_results['braids_created'] = braids_created
        print(f"🎯 Braids created: {braids_created}")
        
        # Show detailed braid information
        if braids_created > 0:
            print(f"\n📋 Braid Details:")
            braid_strands = [s for s in all_strands if s.get('braid_level', 0) > 1]
            for i, braid in enumerate(braid_strands[:5]):  # Show first 5
                print(f"  {i+1}. ID: {braid.get('id', 'N/A')}")
                print(f"     Level: {braid.get('braid_level', 'N/A')}")
                print(f"     Content: {braid.get('content', {})}")
                print()
    
    def print_final_summary(self):
        """Print final summary"""
        print("\n" + "=" * 50)
        print("🏁 FINAL SUMMARY")
        print("=" * 50)
        
        print(f"📊 Initial strands created: {self.test_results['initial_strands']}")
        print(f"🎯 Braids created: {self.test_results['braids_created']}")
        print(f"📈 Braid levels: {sorted(self.test_results['braid_levels'])}")
        print(f"🔍 Clusters processed: {self.test_results['clusters_processed']}")
        print(f"❌ Errors: {len(self.test_results['errors'])}")
        
        if self.test_results['errors']:
            print("\n❌ ERROR DETAILS:")
            for error in self.test_results['errors']:
                print(f"  - {error}")
        
        print("\n✅ Test completed!")


if __name__ == "__main__":
    test = DetailedLearningTest()
    asyncio.run(test.run_detailed_test())
