#!/usr/bin/env python3
"""
Simple Learning System Test

This test creates proper prediction review strands with all required fields
and tests the learning system with clean data.
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

from intelligence.system_control.central_intelligence_layer.per_cluster_learning_system import PerClusterLearningSystem
from intelligence.system_control.central_intelligence_layer.multi_cluster_grouping_engine import MultiClusterGroupingEngine
from intelligence.system_control.central_intelligence_layer.llm_learning_analyzer import LLMLearningAnalyzer
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class SimpleLearningTest:
    """Test the learning system with clean, proper data"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.llm_client = OpenRouterClient()
        self.test_results = {
            'strands_created': 0,
            'clusters_found': 0,
            'braids_created': 0,
            'errors': []
        }
    
    async def run_test(self):
        """Run the simple learning test"""
        print("🧪 Simple Learning System Test")
        print("=" * 35)
        
        try:
            # Stage 1: Create clean prediction review strands
            await self.create_clean_prediction_strands()
            
            # Stage 2: Test clustering
            await self.test_clustering()
            
            # Stage 3: Test learning system
            await self.test_learning_system()
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            self.test_results['errors'].append(str(e))
        
        # Print results
        self.print_results()
    
    async def create_clean_prediction_strands(self):
        """Create clean prediction review strands with all required fields"""
        print("\n📊 Creating Clean Prediction Review Strands")
        print("-" * 45)
        
        try:
            # Create 6 prediction review strands for BTC 1h volume spikes
            prediction_strands = []
            
            for i in range(6):
                strand_id = f"clean_pred_{i+1}_{uuid.uuid4().hex[:8]}"
                
                # Create complete, clean data structure
                strand_data = {
                    'id': strand_id,
                    'module': 'alpha',
                    'kind': 'prediction_review',
                    'symbol': 'BTC',
                    'timeframe': '1h',
                    'tags': ['cil', 'prediction', 'test', 'clean'],
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat(),
                    'braid_level': 1,
                    'lesson': '',
                    'content': {
                        'asset': 'BTC',
                        'timeframe': '1h',
                        'pattern_type': 'volume_spike',
                        'success': i % 2 == 0,  # Alternate success/failure
                        'confidence': 0.7 + (i * 0.05),  # Varying confidence
                        'return_pct': 2.0 + (i * 0.5) if i % 2 == 0 else -1.0 - (i * 0.2),
                        'max_drawdown': 0.5 + (i * 0.1),
                        'method': 'code' if i % 2 == 0 else 'llm',
                        'group_type': 'single_single',
                        'group_signature': 'BTC_1h_volume_spike',
                        'original_pattern_strand_ids': [f"pattern_btc_{i}_{uuid.uuid4().hex[:8]}"]
                    },
                    'module_intelligence': {
                        'cluster_type': 'pattern_timeframe',
                        'cluster_key': 'BTC_1h_volume_spike'
                    },
                    'cluster_key': [
                        {"cluster_type": "asset", "cluster_key": "BTC", "braid_level": 1, "consumed": False},
                        {"cluster_type": "timeframe", "cluster_key": "1h", "braid_level": 1, "consumed": False},
                        {"cluster_type": "pattern_timeframe", "cluster_key": "BTC_1h_volume_spike", "braid_level": 1, "consumed": False},
                        {"cluster_type": "outcome", "cluster_key": "success" if i % 2 == 0 else "failure", "braid_level": 1, "consumed": False},
                        {"cluster_type": "method", "cluster_key": "code" if i % 2 == 0 else "llm", "braid_level": 1, "consumed": False}
                    ]
                }
                
                prediction_strands.append(strand_data)
            
            # Insert all strands
            inserted_count = 0
            for strand in prediction_strands:
                try:
                    result = self.supabase_manager.insert_strand(strand)
                    if result:
                        inserted_count += 1
                except Exception as e:
                    print(f"    ❌ Failed to insert {strand['id']}: {e}")
            
            print(f"  ✅ Inserted {inserted_count}/{len(prediction_strands)} clean prediction strands")
            self.test_results['strands_created'] = inserted_count
            
        except Exception as e:
            print(f"  ❌ Failed to create clean strands: {e}")
            self.test_results['errors'].append(f"Clean strands: {e}")
    
    async def test_clustering(self):
        """Test the clustering system"""
        print("\n🔄 Testing Clustering System")
        print("-" * 30)
        
        try:
            # Initialize clustering engine
            cluster_grouper = MultiClusterGroupingEngine(self.supabase_manager)
            
            # Get all cluster groups
            cluster_groups = await cluster_grouper.get_all_cluster_groups()
            
            total_clusters = sum(len(groups) for groups in cluster_groups.values())
            print(f"  ✅ Found {total_clusters} clusters across all types")
            
            # Show cluster breakdown
            for cluster_type, groups in cluster_groups.items():
                if groups:
                    print(f"    {cluster_type}: {len(groups)} groups")
                    for group_key, strands in groups.items():
                        print(f"      - {group_key}: {len(strands)} strands")
            
            self.test_results['clusters_found'] = total_clusters
            
        except Exception as e:
            print(f"  ❌ Clustering failed: {e}")
            self.test_results['errors'].append(f"Clustering: {e}")
    
    async def test_learning_system(self):
        """Test the learning system"""
        print("\n🧠 Testing Learning System")
        print("-" * 30)
        
        try:
            # Initialize learning system
            learning_system = PerClusterLearningSystem(self.supabase_manager, self.llm_client)
            
            # Process all clusters
            result = await learning_system.process_all_clusters()
            
            # Count created braids
            total_braids = sum(len(braids) for braids in result.values())
            print(f"  ✅ Created {total_braids} learning braids")
            
            # Show braid breakdown
            for cluster_type, braids in result.items():
                if braids:
                    print(f"    {cluster_type}: {len(braids)} braids")
            
            self.test_results['braids_created'] = total_braids
            
        except Exception as e:
            print(f"  ❌ Learning system failed: {e}")
            self.test_results['errors'].append(f"Learning system: {e}")
    
    def print_results(self):
        """Print test results"""
        print("\n" + "=" * 50)
        print("🏁 SIMPLE LEARNING TEST RESULTS")
        print("=" * 50)
        
        print(f"\n📊 SUMMARY:")
        print(f"  Strands Created: {self.test_results['strands_created']}")
        print(f"  Clusters Found: {self.test_results['clusters_found']}")
        print(f"  Braids Created: {self.test_results['braids_created']}")
        
        if self.test_results['errors']:
            print(f"\n❌ ERRORS ({len(self.test_results['errors'])}):")
            for error in self.test_results['errors']:
                print(f"  - {error}")
        else:
            print("\n🎉 No errors found!")
        
        # Overall assessment
        if self.test_results['braids_created'] > 0:
            print("\n🎉 Learning system is working!")
        else:
            print("\n⚠️  Learning system needs more work.")


async def main():
    """Run the simple learning test"""
    test = SimpleLearningTest()
    await test.run_test()


if __name__ == "__main__":
    asyncio.run(main())
