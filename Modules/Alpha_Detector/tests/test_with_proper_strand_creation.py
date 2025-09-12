#!/usr/bin/env python3
"""
Test with Proper Strand Creation

This test uses the actual PredictionEngine to create strands with proper cluster key assignment.
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

from intelligence.system_control.central_intelligence_layer.prediction_engine import PredictionEngine
from intelligence.system_control.central_intelligence_layer.simplified_cil import SimplifiedCIL
from intelligence.system_control.central_intelligence_layer.per_cluster_learning_system import PerClusterLearningSystem
from intelligence.system_control.central_intelligence_layer.multi_cluster_grouping_engine import MultiClusterGroupingEngine
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class TestWithProperStrandCreation:
    """Test using proper strand creation methods"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.llm_client = OpenRouterClient()
        self.prediction_engine = PredictionEngine(self.supabase_manager, self.llm_client)
        self.learning_system = PerClusterLearningSystem(self.supabase_manager, self.llm_client)
        self.cluster_engine = MultiClusterGroupingEngine(self.supabase_manager)
    
    async def run_test(self):
        """Run test with proper strand creation"""
        print("🎯 TEST WITH PROPER STRAND CREATION")
        print("=" * 40)
        
        try:
            # Step 1: Clear database
            await self.step_1_clear_database()
            
            # Step 2: Create prediction review strands using PredictionEngine
            await self.step_2_create_strands_with_prediction_engine()
            
            # Step 3: Verify cluster keys are assigned
            await self.step_3_verify_cluster_keys()
            
            # Step 4: Test clustering
            await self.step_4_test_clustering()
            
            # Step 5: Test braid creation
            await self.step_5_test_braid_creation()
            
            # Step 6: Verify results
            await self.step_6_verify_results()
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def step_1_clear_database(self):
        """Clear database"""
        print("\n🧹 STEP 1: Clearing Database")
        print("-" * 30)
        
        result = self.supabase_manager.client.table('ad_strands').select('id', count='exact').execute()
        before_count = result.count
        print(f"📊 Strands before: {before_count}")
        
        self.supabase_manager.client.table('ad_strands').delete().neq('id', 'dummy').execute()
        
        result = self.supabase_manager.client.table('ad_strands').select('id', count='exact').execute()
        after_count = result.count
        print(f"📊 Strands after: {after_count}")
        print("✅ Database cleared!")
    
    async def step_2_create_strands_with_prediction_engine(self):
        """Create prediction review strands using the actual PredictionEngine"""
        print("\n📊 STEP 2: Creating Strands with PredictionEngine")
        print("-" * 50)
        
        # Create test predictions and outcomes
        test_data = [
            {
                'prediction': {
                    'id': f"pred_btc_1_{uuid.uuid4().hex[:8]}",
                    'pattern_group': {
                        'asset': 'BTC',
                        'timeframe': '1h',
                        'group_type': 'single_single',
                        'patterns': [{'pattern_type': 'volume_spike', 'confidence': 0.85}]
                    },
                    'confidence': 0.85,
                    'method': 'code'
                },
                'outcome': {
                    'success': True,
                    'return_pct': 3.2,
                    'max_drawdown': 0.8,
                    'duration_hours': 20.0
                }
            },
            {
                'prediction': {
                    'id': f"pred_btc_2_{uuid.uuid4().hex[:8]}",
                    'pattern_group': {
                        'asset': 'BTC',
                        'timeframe': '1h',
                        'group_type': 'single_single',
                        'patterns': [{'pattern_type': 'volume_spike', 'confidence': 0.75}]
                    },
                    'confidence': 0.75,
                    'method': 'code'
                },
                'outcome': {
                    'success': False,
                    'return_pct': -1.5,
                    'max_drawdown': 2.1,
                    'duration_hours': 20.0
                }
            },
            {
                'prediction': {
                    'id': f"pred_btc_3_{uuid.uuid4().hex[:8]}",
                    'pattern_group': {
                        'asset': 'BTC',
                        'timeframe': '1h',
                        'group_type': 'single_single',
                        'patterns': [{'pattern_type': 'volume_spike', 'confidence': 0.92}]
                    },
                    'confidence': 0.92,
                    'method': 'llm'
                },
                'outcome': {
                    'success': True,
                    'return_pct': 4.1,
                    'max_drawdown': 0.5,
                    'duration_hours': 20.0
                }
            },
            {
                'prediction': {
                    'id': f"pred_eth_1_{uuid.uuid4().hex[:8]}",
                    'pattern_group': {
                        'asset': 'ETH',
                        'timeframe': '4h',
                        'group_type': 'single_single',
                        'patterns': [{'pattern_type': 'momentum', 'confidence': 0.78}]
                    },
                    'confidence': 0.78,
                    'method': 'code'
                },
                'outcome': {
                    'success': True,
                    'return_pct': 2.8,
                    'max_drawdown': 1.2,
                    'duration_hours': 80.0
                }
            },
            {
                'prediction': {
                    'id': f"pred_eth_2_{uuid.uuid4().hex[:8]}",
                    'pattern_group': {
                        'asset': 'ETH',
                        'timeframe': '4h',
                        'group_type': 'single_single',
                        'patterns': [{'pattern_type': 'momentum', 'confidence': 0.88}]
                    },
                    'confidence': 0.88,
                    'method': 'code'
                },
                'outcome': {
                    'success': True,
                    'return_pct': 3.5,
                    'max_drawdown': 0.9,
                    'duration_hours': 80.0
                }
            }
        ]
        
        # Create prediction review strands using PredictionEngine
        created_strands = []
        for i, data in enumerate(test_data):
            try:
                print(f"  Creating strand {i+1}/5...")
                
                # Use the actual PredictionEngine method
                strand_id = await self.prediction_engine.create_prediction_review_strand(
                    data['prediction'], 
                    data['outcome']
                )
                
                if strand_id and not strand_id.startswith('error:'):
                    created_strands.append(strand_id)
                    print(f"    ✅ Created: {strand_id}")
                else:
                    print(f"    ❌ Failed: {strand_id}")
                    
            except Exception as e:
                print(f"    ❌ Error creating strand {i+1}: {e}")
        
        print(f"\n📊 Created {len(created_strands)}/5 prediction review strands")
        
        # Verify database state
        result = self.supabase_manager.client.table('ad_strands').select('id', count='exact').execute()
        total_strands = result.count
        print(f"📊 Total strands in database: {total_strands}")
    
    async def step_3_verify_cluster_keys(self):
        """Verify that cluster keys were automatically assigned"""
        print("\n🔍 STEP 3: Verifying Cluster Keys")
        print("-" * 35)
        
        # Get all prediction review strands
        result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').execute()
        strands = result.data
        
        print(f"📊 Found {len(strands)} prediction review strands")
        
        for i, strand in enumerate(strands):
            print(f"\n🔍 STRAND {i+1}: {strand.get('id', 'N/A')[:20]}...")
            
            # Check if cluster keys are in content
            content = strand.get('content', {})
            cluster_keys = content.get('cluster_keys', [])
            
            print(f"  Content cluster_keys: {len(cluster_keys)} keys")
            for key in cluster_keys:
                print(f"    - {key}")
            
            # Check if cluster_key field is populated
            cluster_key_field = strand.get('cluster_key', [])
            print(f"  cluster_key field: {len(cluster_key_field)} keys")
            for key in cluster_key_field:
                print(f"    - {key}")
    
    async def step_4_test_clustering(self):
        """Test clustering with properly assigned cluster keys"""
        print("\n🔍 STEP 4: Testing Clustering")
        print("-" * 30)
        
        # Get all cluster groups
        clusters = await self.cluster_engine.get_all_cluster_groups()
        
        print(f"📊 Found {len(clusters)} cluster types:")
        for cluster_type, groups in clusters.items():
            print(f"  {cluster_type}: {len(groups)} groups")
            for group_key, reviews in groups.items():
                print(f"    {group_key}: {len(reviews)} reviews")
                if len(reviews) >= 3:
                    print(f"      ✅ Ready for braiding (≥3 reviews)")
                else:
                    print(f"      ❌ Not ready for braiding (<3 reviews)")
    
    async def step_5_test_braid_creation(self):
        """Test braid creation"""
        print("\n🎯 STEP 5: Testing Braid Creation")
        print("-" * 35)
        
        print("  Running learning system...")
        try:
            # Run learning system
            result = await self.learning_system.process_all_clusters()
            
            if result:
                print(f"  ✅ Learning cycle completed")
                print(f"  📊 Result: {result}")
            else:
                print(f"  ❌ Learning cycle failed")
                
        except Exception as e:
            print(f"  ❌ Error in learning cycle: {e}")
            import traceback
            traceback.print_exc()
    
    async def step_6_verify_results(self):
        """Verify final results"""
        print("\n🔍 STEP 6: Verifying Results")
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
        
        # Count braids created
        braids_created = len([s for s in all_strands if s.get('braid_level', 0) > 1])
        print(f"🎯 Braids created: {braids_created}")
        
        # Show braid details
        if braids_created > 0:
            print(f"\n📋 Braid Details:")
            braid_strands = [s for s in all_strands if s.get('braid_level', 0) > 1]
            for i, braid in enumerate(braid_strands):
                content = braid.get('content', {})
                cluster_type = content.get('cluster_type', 'unknown')
                cluster_key = content.get('cluster_key', 'unknown')
                print(f"  {i+1}. {braid.get('id', 'N/A')[:20]}... - {cluster_type}:{cluster_key}")


if __name__ == "__main__":
    test = TestWithProperStrandCreation()
    asyncio.run(test.run_test())
