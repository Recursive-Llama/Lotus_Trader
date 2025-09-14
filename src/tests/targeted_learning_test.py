#!/usr/bin/env python3
"""
Targeted Learning Test

Creates specific test data to predict exactly what clusters and braids should be created.
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


class TargetedLearningTest:
    """Test with predictable cluster outcomes"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.llm_client = OpenRouterClient()
        self.expected_clusters = {}
        self.expected_braids = 0
    
    async def run_targeted_test(self):
        """Run test with predictable outcomes"""
        print("🎯 TARGETED LEARNING TEST")
        print("=" * 30)
        print("Creating data to predict exact cluster outcomes")
        print()
        
        try:
            # Step 1: Create targeted test data
            await self.step_1_create_targeted_data()
            
            # Step 2: Analyze what clusters should be created
            await self.step_2_analyze_expected_clusters()
            
            # Step 3: Test clustering
            await self.step_3_test_clustering()
            
            # Step 4: Test braid creation
            await self.step_4_test_braid_creation()
            
            # Step 5: Verify results match expectations
            await self.step_5_verify_expectations()
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def step_1_create_targeted_data(self):
        """Create targeted test data with predictable clusters"""
        print("📊 STEP 1: Creating Targeted Test Data")
        print("-" * 40)
        
        # Plan: Create data that will form specific clusters
        # Cluster 1: BTC 1h volume_spike (3 strands) → 1 braid expected
        # Cluster 2: ETH 4h momentum (2 strands) → 0 braids expected (not enough)
        # Cluster 3: Success outcome (4 strands) → 1 braid expected
        # Cluster 4: Code method (3 strands) → 1 braid expected
        # Cluster 5: single_single group_type (5 strands) → 1 braid expected
        
        test_strands = [
            # BTC 1h volume_spike cluster (3 strands - enough for braid)
            {
                'id': f"btc_vol_1_{uuid.uuid4().hex[:8]}",
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
                'cluster_key': []  # Will be assigned by clustering system
            },
            {
                'id': f"btc_vol_2_{uuid.uuid4().hex[:8]}",
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
                'id': f"btc_vol_3_{uuid.uuid4().hex[:8]}",
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
            # ETH 4h momentum cluster (2 strands - not enough for braid)
            {
                'id': f"eth_mom_1_{uuid.uuid4().hex[:8]}",
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
                'id': f"eth_mom_2_{uuid.uuid4().hex[:8]}",
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
            # Success outcome cluster (4 strands - enough for braid)
            {
                'id': f"success_1_{uuid.uuid4().hex[:8]}",
                'module': 'alpha',
                'kind': 'prediction_review',
                'symbol': 'ADA',
                'timeframe': '2h',
                'tags': ['cil', 'test'],
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'braid_level': 1,
                'lesson': '',
                'content': {
                    'asset': 'ADA',
                    'timeframe': '2h',
                    'pattern_type': 'breakout',
                    'success': True,
                    'confidence': 0.75,
                    'return_pct': 2.1,
                    'max_drawdown': 0.6,
                    'method': 'code',
                    'group_type': 'single_single',
                    'group_signature': 'ADA_2h_breakout'
                },
                'module_intelligence': {
                    'cluster_type': 'pattern_timeframe',
                    'cluster_key': 'ADA_2h_breakout',
                    'braid_level': 1
                },
                'cluster_key': []
            },
            {
                'id': f"success_2_{uuid.uuid4().hex[:8]}",
                'module': 'alpha',
                'kind': 'prediction_review',
                'symbol': 'SOL',
                'timeframe': '3h',
                'tags': ['cil', 'test'],
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'braid_level': 1,
                'lesson': '',
                'content': {
                    'asset': 'SOL',
                    'timeframe': '3h',
                    'pattern_type': 'reversal',
                    'success': True,
                    'confidence': 0.82,
                    'return_pct': 3.8,
                    'max_drawdown': 1.1,
                    'method': 'llm',
                    'group_type': 'single_single',
                    'group_signature': 'SOL_3h_reversal'
                },
                'module_intelligence': {
                    'cluster_type': 'pattern_timeframe',
                    'cluster_key': 'SOL_3h_reversal',
                    'braid_level': 1
                },
                'cluster_key': []
            },
            {
                'id': f"success_3_{uuid.uuid4().hex[:8]}",
                'module': 'alpha',
                'kind': 'prediction_review',
                'symbol': 'DOT',
                'timeframe': '1h',
                'tags': ['cil', 'test'],
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'braid_level': 1,
                'lesson': '',
                'content': {
                    'asset': 'DOT',
                    'timeframe': '1h',
                    'pattern_type': 'support',
                    'success': True,
                    'confidence': 0.68,
                    'return_pct': 1.9,
                    'max_drawdown': 0.4,
                    'method': 'code',
                    'group_type': 'single_single',
                    'group_signature': 'DOT_1h_support'
                },
                'module_intelligence': {
                    'cluster_type': 'pattern_timeframe',
                    'cluster_key': 'DOT_1h_support',
                    'braid_level': 1
                },
                'cluster_key': []
            },
            {
                'id': f"success_4_{uuid.uuid4().hex[:8]}",
                'module': 'alpha',
                'kind': 'prediction_review',
                'symbol': 'LINK',
                'timeframe': '4h',
                'tags': ['cil', 'test'],
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'braid_level': 1,
                'lesson': '',
                'content': {
                    'asset': 'LINK',
                    'timeframe': '4h',
                    'pattern_type': 'resistance',
                    'success': True,
                    'confidence': 0.91,
                    'return_pct': 4.5,
                    'max_drawdown': 0.8,
                    'method': 'code',
                    'group_type': 'single_single',
                    'group_signature': 'LINK_4h_resistance'
                },
                'module_intelligence': {
                    'cluster_type': 'pattern_timeframe',
                    'cluster_key': 'LINK_4h_resistance',
                    'braid_level': 1
                },
                'cluster_key': []
            }
        ]
        
        # Insert strands
        inserted_count = 0
        for strand in test_strands:
            try:
                result = self.supabase_manager.insert_strand(strand)
                if result:
                    inserted_count += 1
                    print(f"  ✅ Inserted: {strand['id']} - {strand['content']['asset']} {strand['content']['timeframe']}")
                else:
                    print(f"  ❌ Failed: {strand['id']}")
            except Exception as e:
                print(f"  ❌ Error inserting {strand['id']}: {e}")
        
        print(f"\n📊 Created {inserted_count}/9 targeted strands")
        
        # Verify database state
        result = self.supabase_manager.client.table('ad_strands').select('id', count='exact').execute()
        total_strands = result.count
        print(f"📊 Total strands in database: {total_strands}")
    
    async def step_2_analyze_expected_clusters(self):
        """Analyze what clusters should be created"""
        print("\n🔍 STEP 2: Analyzing Expected Clusters")
        print("-" * 40)
        
        # Based on our test data, we should expect:
        self.expected_clusters = {
            'pattern_timeframe': {
                'BTC_1h_volume_spike': 3,  # Should create braid
                'ETH_4h_momentum': 2,      # Should NOT create braid (<3)
                'ADA_2h_breakout': 1,      # Should NOT create braid (<3)
                'SOL_3h_reversal': 1,      # Should NOT create braid (<3)
                'DOT_1h_support': 1,       # Should NOT create braid (<3)
                'LINK_4h_resistance': 1    # Should NOT create braid (<3)
            },
            'asset': {
                'BTC': 3,  # Should create braid
                'ETH': 2,  # Should NOT create braid (<3)
                'ADA': 1,  # Should NOT create braid (<3)
                'SOL': 1,  # Should NOT create braid (<3)
                'DOT': 1,  # Should NOT create braid (<3)
                'LINK': 1  # Should NOT create braid (<3)
            },
            'timeframe': {
                '1h': 3,  # Should create braid
                '2h': 1,  # Should NOT create braid (<3)
                '3h': 1,  # Should NOT create braid (<3)
                '4h': 3   # Should create braid
            },
            'outcome': {
                'success': 7,  # Should create braid
                'failure': 2   # Should NOT create braid (<3)
            },
            'group_type': {
                'single_single': 9  # Should create braid
            },
            'method': {
                'code': 6,  # Should create braid
                'llm': 3    # Should create braid
            }
        }
        
        print("Expected clusters (≥3 strands = braid eligible):")
        for cluster_type, groups in self.expected_clusters.items():
            print(f"  {cluster_type}:")
            for group_key, count in groups.items():
                status = "✅ Braid eligible" if count >= 3 else "❌ Not enough strands"
                print(f"    {group_key}: {count} strands - {status}")
        
        # Count expected braids
        self.expected_braids = 0
        for cluster_type, groups in self.expected_clusters.items():
            for group_key, count in groups.items():
                if count >= 3:
                    self.expected_braids += 1
        
        print(f"\n🎯 Expected braids: {self.expected_braids}")
    
    async def step_3_test_clustering(self):
        """Test clustering"""
        print("\n🔍 STEP 3: Testing Clustering")
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
    
    async def step_4_test_braid_creation(self):
        """Test braid creation"""
        print("\n🎯 STEP 4: Testing Braid Creation")
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
    
    async def step_5_verify_expectations(self):
        """Verify results match expectations"""
        print("\n🔍 STEP 5: Verifying Expectations")
        print("-" * 35)
        
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
        
        # Count braids created
        braids_created = len([s for s in all_strands if s.get('braid_level', 0) > 1])
        print(f"🎯 Braids created: {braids_created}")
        print(f"🎯 Expected braids: {self.expected_braids}")
        
        if braids_created == self.expected_braids:
            print("✅ Braid count matches expectation!")
        else:
            print(f"❌ Braid count mismatch! Expected {self.expected_braids}, got {braids_created}")
        
        # Show braid details
        if braids_created > 0:
            print(f"\n📋 Braid Details:")
            braid_strands = [s for s in all_strands if s.get('braid_level', 0) > 1]
            for i, braid in enumerate(braid_strands):
                content = braid.get('content', {})
                cluster_type = content.get('cluster_type', 'unknown')
                cluster_key = content.get('cluster_key', 'unknown')
                source_count = content.get('strand_count', 0)
                print(f"  {i+1}. {braid.get('id', 'N/A')[:20]}... - {cluster_type}:{cluster_key} (from {source_count} sources)")


if __name__ == "__main__":
    test = TargetedLearningTest()
    asyncio.run(test.run_targeted_test())
