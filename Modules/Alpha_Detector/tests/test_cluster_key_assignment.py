#!/usr/bin/env python3
"""
Test Cluster Key Assignment in Isolation

This test focuses specifically on how cluster keys should be assigned to strands.
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

from intelligence.system_control.central_intelligence_layer.multi_cluster_grouping_engine import MultiClusterGroupingEngine
from src.utils.supabase_manager import SupabaseManager


class ClusterKeyAssignmentTest:
    """Test cluster key assignment in isolation"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.cluster_engine = MultiClusterGroupingEngine(self.supabase_manager)
    
    async def run_test(self):
        """Run cluster key assignment test"""
        print("🔍 CLUSTER KEY ASSIGNMENT TEST")
        print("=" * 40)
        
        try:
            # Step 1: Clear database
            await self.step_1_clear_database()
            
            # Step 2: Create test strands
            await self.step_2_create_test_strands()
            
            # Step 3: Test cluster key extraction
            await self.step_3_test_cluster_extraction()
            
            # Step 4: Test automatic cluster assignment
            await self.step_4_test_automatic_assignment()
            
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
    
    async def step_2_create_test_strands(self):
        """Create test strands with different cluster types"""
        print("\n📊 STEP 2: Creating Test Strands")
        print("-" * 35)
        
        test_strands = [
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
                'cluster_key': []  # This should be auto-assigned
            },
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
                    'success': False,
                    'confidence': 0.65,
                    'return_pct': -1.5,
                    'max_drawdown': 2.1,
                    'method': 'llm',
                    'group_type': 'single_single',
                    'group_signature': 'ETH_4h_momentum'
                },
                'module_intelligence': {
                    'cluster_type': 'pattern_timeframe',
                    'cluster_key': 'ETH_4h_momentum',
                    'braid_level': 1
                },
                'cluster_key': []  # This should be auto-assigned
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
        
        print(f"\n📊 Created {inserted_count}/2 test strands")
    
    async def step_3_test_cluster_extraction(self):
        """Test how cluster keys should be extracted from strands"""
        print("\n🔍 STEP 3: Testing Cluster Key Extraction")
        print("-" * 45)
        
        # Get the test strands
        result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').execute()
        strands = result.data
        
        print(f"📊 Retrieved {len(strands)} strands")
        
        for i, strand in enumerate(strands):
            print(f"\n🔍 STRAND {i+1}: {strand.get('id', 'N/A')[:20]}...")
            print(f"  Symbol: {strand.get('symbol', 'N/A')}")
            print(f"  Current cluster_key: {strand.get('cluster_key', [])}")
            
            # Test cluster key extraction for each cluster type
            print(f"  Testing cluster key extraction:")
            
            for cluster_type in self.cluster_engine.cluster_types.keys():
                cluster_key = self.cluster_engine._extract_cluster_key(cluster_type, strand)
                print(f"    {cluster_type}: {cluster_key}")
    
    async def step_4_test_automatic_assignment(self):
        """Test automatic cluster key assignment"""
        print("\n🎯 STEP 4: Testing Automatic Cluster Assignment")
        print("-" * 50)
        
        # Get the test strands
        result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').execute()
        strands = result.data
        
        print(f"📊 Processing {len(strands)} strands for cluster assignment")
        
        for strand in strands:
            print(f"\n🔍 Processing: {strand.get('id', 'N/A')[:20]}...")
            
            # Calculate what cluster keys this strand should have
            expected_cluster_keys = []
            
            for cluster_type in self.cluster_engine.cluster_types.keys():
                cluster_key = self.cluster_engine._extract_cluster_key(cluster_type, strand)
                if cluster_key:
                    expected_cluster_keys.append({
                        'cluster_type': cluster_type,
                        'cluster_key': cluster_key,
                        'braid_level': strand.get('braid_level', 1),
                        'consumed': False
                    })
            
            print(f"  Expected cluster keys: {expected_cluster_keys}")
            
            # Update the strand with cluster keys
            try:
                update_result = self.supabase_manager.client.table('ad_strands').update({
                    'cluster_key': expected_cluster_keys
                }).eq('id', strand['id']).execute()
                
                if update_result.data:
                    print(f"  ✅ Updated cluster keys successfully")
                else:
                    print(f"  ❌ Failed to update cluster keys")
                    
            except Exception as e:
                print(f"  ❌ Error updating cluster keys: {e}")
        
        # Verify the updates
        print(f"\n🔍 Verifying cluster key assignments:")
        result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').execute()
        strands = result.data
        
        for strand in strands:
            print(f"  {strand.get('id', 'N/A')[:20]}...: {strand.get('cluster_key', [])}")


if __name__ == "__main__":
    test = ClusterKeyAssignmentTest()
    asyncio.run(test.run_test())
