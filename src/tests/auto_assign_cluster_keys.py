#!/usr/bin/env python3
"""
Auto-Assign Cluster Keys

This script automatically assigns cluster keys to all strands that don't have them.
"""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.intelligence.system_control.central_intelligence_layer.multi_cluster_grouping_engine import MultiClusterGroupingEngine
from src.utils.supabase_manager import SupabaseManager


class AutoClusterKeyAssigner:
    """Automatically assign cluster keys to strands"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.cluster_engine = MultiClusterGroupingEngine(self.supabase_manager)
    
    async def assign_cluster_keys_to_all_strands(self):
        """Assign cluster keys to all strands that don't have them"""
        print("🔧 AUTO-ASSIGNING CLUSTER KEYS")
        print("=" * 35)
        
        try:
            # Get all strands
            result = self.supabase_manager.client.table('ad_strands').select('*').execute()
            all_strands = result.data
            
            print(f"📊 Total strands: {len(all_strands)}")
            
            # Filter strands that need cluster key assignment
            strands_needing_assignment = []
            for strand in all_strands:
                cluster_key = strand.get('cluster_key', [])
                if not cluster_key or len(cluster_key) == 0:
                    strands_needing_assignment.append(strand)
            
            print(f"📊 Strands needing cluster key assignment: {len(strands_needing_assignment)}")
            
            if not strands_needing_assignment:
                print("✅ All strands already have cluster keys assigned!")
                return
            
            # Process each strand
            updated_count = 0
            for strand in strands_needing_assignment:
                success = await self.assign_cluster_keys_to_strand(strand)
                if success:
                    updated_count += 1
                    print(f"  ✅ Updated: {strand.get('id', 'N/A')[:20]}...")
                else:
                    print(f"  ❌ Failed: {strand.get('id', 'N/A')[:20]}...")
            
            print(f"\n🎯 Successfully updated {updated_count}/{len(strands_needing_assignment)} strands")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    async def assign_cluster_keys_to_strand(self, strand: dict) -> bool:
        """Assign cluster keys to a specific strand"""
        try:
            # Calculate cluster keys for this strand
            cluster_keys = []
            
            for cluster_type in self.cluster_engine.cluster_types.keys():
                cluster_key = self.cluster_engine._extract_cluster_key(cluster_type, strand)
                if cluster_key:
                    cluster_keys.append({
                        'cluster_type': cluster_type,
                        'cluster_key': cluster_key,
                        'braid_level': strand.get('braid_level', 1),
                        'consumed': False
                    })
            
            # Update the strand
            update_result = self.supabase_manager.client.table('ad_strands').update({
                'cluster_key': cluster_keys
            }).eq('id', strand['id']).execute()
            
            return bool(update_result.data)
            
        except Exception as e:
            print(f"    Error assigning cluster keys to {strand.get('id', 'N/A')}: {e}")
            return False


if __name__ == "__main__":
    assigner = AutoClusterKeyAssigner()
    asyncio.run(assigner.assign_cluster_keys_to_all_strands())
