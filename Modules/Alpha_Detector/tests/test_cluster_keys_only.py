#!/usr/bin/env python3
"""
Test Cluster Keys Only

This test ONLY focuses on cluster key assignment and errors out if it's not working.
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
from intelligence.system_control.central_intelligence_layer.multi_cluster_grouping_engine import MultiClusterGroupingEngine
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class ClusterKeysOnlyTest:
    """Test ONLY cluster key assignment"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.llm_client = OpenRouterClient()
        self.prediction_engine = PredictionEngine(self.supabase_manager, self.llm_client)
        self.cluster_engine = MultiClusterGroupingEngine(self.supabase_manager)
    
    async def run_test(self):
        """Run cluster keys test - ERROR if not working"""
        print("🔍 CLUSTER KEYS ONLY TEST")
        print("=" * 30)
        
        try:
            # Step 1: Clear database
            await self.step_1_clear_database()
            
            # Step 2: Create ONE strand using PredictionEngine
            await self.step_2_create_one_strand()
            
            # Step 3: Check cluster keys - ERROR if not working
            await self.step_3_check_cluster_keys()
            
            print("✅ CLUSTER KEYS ARE WORKING!")
            
        except Exception as e:
            print(f"❌ CLUSTER KEYS NOT WORKING: {e}")
            import traceback
            traceback.print_exc()
            exit(1)
    
    async def step_1_clear_database(self):
        """Clear database"""
        print("\n🧹 Clearing Database")
        self.supabase_manager.client.table('ad_strands').delete().neq('id', 'dummy').execute()
        print("✅ Database cleared!")
    
    async def step_2_create_one_strand(self):
        """Create ONE strand using PredictionEngine"""
        print("\n📊 Creating ONE strand with PredictionEngine")
        
        prediction = {
            'id': f"pred_btc_{uuid.uuid4().hex[:8]}",
            'pattern_group': {
                'asset': 'BTC',
                'timeframe': '1h',
                'group_type': 'single_single',
                'patterns': [{'pattern_type': 'volume_spike', 'confidence': 0.85}]
            },
            'confidence': 0.85,
            'method': 'code'
        }
        
        outcome = {
            'success': True,
            'return_pct': 3.2,
            'max_drawdown': 0.8,
            'duration_hours': 20.0
        }
        
        try:
            strand_id = await self.prediction_engine.create_prediction_review_strand(prediction, outcome)
            if strand_id and not strand_id.startswith('error:'):
                print(f"✅ Created strand: {strand_id}")
            else:
                raise Exception(f"Failed to create strand: {strand_id}")
        except Exception as e:
            raise Exception(f"Error creating strand: {e}")
    
    async def step_3_check_cluster_keys(self):
        """Check cluster keys - ERROR if not working"""
        print("\n🔍 Checking cluster keys")
        
        # Get the strand
        result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'prediction_review').execute()
        strands = result.data
        
        if not strands:
            raise Exception("No strands found in database!")
        
        strand = strands[0]
        print(f"📊 Found strand: {strand.get('id', 'N/A')[:20]}...")
        
        # Check content.cluster_keys
        content = strand.get('content', {})
        cluster_keys = content.get('cluster_keys', [])
        print(f"📊 Content cluster_keys: {len(cluster_keys)} keys")
        
        if not cluster_keys:
            raise Exception("❌ NO CLUSTER KEYS IN CONTENT!")
        
        for key in cluster_keys:
            print(f"  - {key}")
        
        # Check cluster_key field
        cluster_key_field = strand.get('cluster_key', [])
        print(f"📊 cluster_key field: {len(cluster_key_field)} keys")
        
        if not cluster_key_field:
            print("⚠️  cluster_key field is empty - this is expected, clustering system should populate it")
        else:
            for key in cluster_key_field:
                print(f"  - {key}")
        
        # Test cluster key extraction
        print(f"\n🔍 Testing cluster key extraction:")
        for cluster_type in self.cluster_engine.cluster_types.keys():
            cluster_key = self.cluster_engine._extract_cluster_key(cluster_type, strand)
            print(f"  {cluster_type}: {cluster_key}")
            if not cluster_key:
                raise Exception(f"❌ Could not extract cluster key for {cluster_type}!")
        
        print("✅ All cluster key extractions working!")


if __name__ == "__main__":
    test = ClusterKeysOnlyTest()
    asyncio.run(test.run_test())
