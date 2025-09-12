#!/usr/bin/env python3
"""
Test with Pattern Strands

This test creates the missing pattern strands that the learning system needs for context,
then tests the complete learning system with proper data flow.
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
from intelligence.system_control.central_intelligence_layer.per_cluster_learning_system import PerClusterLearningSystem
from intelligence.system_control.central_intelligence_layer.multi_cluster_grouping_engine import MultiClusterGroupingEngine
from intelligence.system_control.central_intelligence_layer.llm_learning_analyzer import LLMLearningAnalyzer
from intelligence.system_control.central_intelligence_layer.braid_level_manager import BraidLevelManager
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class TestWithPatternStrands:
    """Test the complete learning system with proper pattern strands"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.llm_client = OpenRouterClient()
        self.test_results = {
            'pattern_strands_created': 0,
            'prediction_strands_created': 0,
            'braids_created': 0,
            'multi_level_braids': 0,
            'errors': []
        }
    
    async def run_complete_test(self):
        """Run the complete test with pattern strands"""
        print("🚀 Complete Learning System Test with Pattern Strands")
        print("=" * 60)
        
        try:
            # Stage 1: Create pattern strands
            await self.stage_1_create_pattern_strands()
            
            # Stage 2: Create prediction_review strands with proper references
            await self.stage_2_create_prediction_strands()
            
            # Stage 3: Test learning system
            await self.stage_3_test_learning_system()
            
            # Stage 4: Test multi-level braid progression
            await self.stage_4_test_multi_level_braids()
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            self.test_results['errors'].append(str(e))
        
        # Print results
        self.print_results()
    
    async def stage_1_create_pattern_strands(self):
        """Stage 1: Create pattern strands that the learning system needs"""
        print("\n📊 Stage 1: Creating Pattern Strands")
        print("-" * 40)
        
        try:
            # Create pattern strands for BTC 1h volume spikes
            btc_patterns = [
                {
                    'id': f"pattern_btc_0_{uuid.uuid4().hex[:8]}",
                    'content': {
                        'asset': 'BTC',
                        'timeframe': '1h',
                        'pattern_type': 'volume_spike',
                        'confidence': 0.85,
                        'strength': 0.78,
                        'volume_ratio': 2.3,
                        'price_change': 0.02,
                        'group_type': 'single_single',
                        'group_signature': 'BTC_1h_volume_spike'
                    },
                    'module_intelligence': {
                        'pattern_quality': 'high',
                        'detection_method': 'code',
                        'reliability': 0.82
                    }
                },
                {
                    'id': f"pattern_btc_1_{uuid.uuid4().hex[:8]}",
                    'content': {
                        'asset': 'BTC',
                        'timeframe': '1h',
                        'pattern_type': 'volume_spike',
                        'confidence': 0.72,
                        'strength': 0.65,
                        'volume_ratio': 1.8,
                        'price_change': 0.015,
                        'group_type': 'single_single',
                        'group_signature': 'BTC_1h_volume_spike'
                    },
                    'module_intelligence': {
                        'pattern_quality': 'medium',
                        'detection_method': 'code',
                        'reliability': 0.75
                    }
                },
                {
                    'id': f"pattern_btc_2_{uuid.uuid4().hex[:8]}",
                    'content': {
                        'asset': 'BTC',
                        'timeframe': '1h',
                        'pattern_type': 'volume_spike',
                        'confidence': 0.91,
                        'strength': 0.88,
                        'volume_ratio': 2.8,
                        'price_change': 0.035,
                        'group_type': 'single_single',
                        'group_signature': 'BTC_1h_volume_spike'
                    },
                    'module_intelligence': {
                        'pattern_quality': 'high',
                        'detection_method': 'code',
                        'reliability': 0.89
                    }
                }
            ]
            
            # Create pattern strands for ETH 4h momentum
            eth_patterns = [
                {
                    'id': f"pattern_eth_0_{uuid.uuid4().hex[:8]}",
                    'content': {
                        'asset': 'ETH',
                        'timeframe': '4h',
                        'pattern_type': 'momentum',
                        'confidence': 0.78,
                        'strength': 0.72,
                        'momentum_score': 0.65,
                        'trend_strength': 0.68,
                        'group_type': 'single_single',
                        'group_signature': 'ETH_4h_momentum'
                    },
                    'module_intelligence': {
                        'pattern_quality': 'medium',
                        'detection_method': 'code',
                        'reliability': 0.76
                    }
                },
                {
                    'id': f"pattern_eth_1_{uuid.uuid4().hex[:8]}",
                    'content': {
                        'asset': 'ETH',
                        'timeframe': '4h',
                        'pattern_type': 'momentum',
                        'confidence': 0.88,
                        'strength': 0.85,
                        'momentum_score': 0.78,
                        'trend_strength': 0.82,
                        'group_type': 'single_single',
                        'group_signature': 'ETH_4h_momentum'
                    },
                    'module_intelligence': {
                        'pattern_quality': 'high',
                        'detection_method': 'code',
                        'reliability': 0.86
                    }
                },
                {
                    'id': f"pattern_eth_2_{uuid.uuid4().hex[:8]}",
                    'content': {
                        'asset': 'ETH',
                        'timeframe': '4h',
                        'pattern_type': 'momentum',
                        'confidence': 0.65,
                        'strength': 0.58,
                        'momentum_score': 0.52,
                        'trend_strength': 0.55,
                        'group_type': 'single_single',
                        'group_signature': 'ETH_4h_momentum'
                    },
                    'module_intelligence': {
                        'pattern_quality': 'medium',
                        'detection_method': 'code',
                        'reliability': 0.62
                    }
                }
            ]
            
            all_patterns = btc_patterns + eth_patterns
            
            # Insert all pattern strands
            inserted_count = 0
            for pattern in all_patterns:
                try:
                    # Prepare strand data for Supabase client
                    strand_data = {
                        'id': pattern['id'],
                        'module': 'alpha',
                        'kind': 'pattern',
                        'symbol': pattern['content']['asset'],
                        'timeframe': pattern['content']['timeframe'],
                        'tags': ['alpha', 'pattern', 'test'],
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'updated_at': datetime.now(timezone.utc).isoformat(),
                        'braid_level': 1,
                        'lesson': '',
                        'content': pattern['content'],
                        'module_intelligence': pattern['module_intelligence'],
                        'cluster_key': [
                            {"cluster_type": "asset", "cluster_key": pattern['content']['asset'], "braid_level": 1, "consumed": False},
                            {"cluster_type": "timeframe", "cluster_key": pattern['content']['timeframe'], "braid_level": 1, "consumed": False},
                            {"cluster_type": "pattern_timeframe", "cluster_key": pattern['content']['group_signature'], "braid_level": 1, "consumed": False}
                        ]
                    }
                    
                    result = self.supabase_manager.insert_strand(strand_data)
                    if result:
                        inserted_count += 1
                    
                except Exception as e:
                    print(f"    ❌ Failed to insert {pattern['id']}: {e}")
            
            print(f"  ✅ Inserted {inserted_count}/{len(all_patterns)} pattern strands")
            self.test_results['pattern_strands_created'] = inserted_count
            
        except Exception as e:
            print(f"  ❌ Stage 1 failed: {e}")
            self.test_results['errors'].append(f"Stage 1: {e}")
    
    async def stage_2_create_prediction_strands(self):
        """Stage 2: Create prediction_review strands with proper pattern references"""
        print("\n📈 Stage 2: Creating Prediction Review Strands")
        print("-" * 50)
        
        try:
            # Get the pattern strands we just created
            pattern_query = "SELECT * FROM AD_strands WHERE kind = 'pattern' ORDER BY created_at DESC LIMIT 6"
            pattern_result = await self.supabase_manager.execute_query(pattern_query)
            
            if not pattern_result:
                print("  ❌ No pattern strands found")
                return
            
            patterns = [dict(row) for row in pattern_result]
            print(f"  Found {len(patterns)} pattern strands")
            
            # Create prediction_review strands with proper pattern references
            prediction_reviews = [
                {
                    'id': f"pred_btc_1h_vol_1_{uuid.uuid4().hex[:8]}",
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
                        'group_signature': 'BTC_1h_volume_spike',
                        'original_pattern_strand_ids': [patterns[0]['id'], patterns[1]['id']]  # Reference to pattern strands
                    },
                    'module_intelligence': {
                        'cluster_type': 'pattern_timeframe',
                        'cluster_key': 'BTC_1h_volume_spike'
                    }
                },
                {
                    'id': f"pred_btc_1h_vol_2_{uuid.uuid4().hex[:8]}",
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
                        'group_signature': 'BTC_1h_volume_spike',
                        'original_pattern_strand_ids': [patterns[1]['id'], patterns[2]['id']]
                    },
                    'module_intelligence': {
                        'cluster_type': 'pattern_timeframe',
                        'cluster_key': 'BTC_1h_volume_spike'
                    }
                },
                {
                    'id': f"pred_btc_1h_vol_3_{uuid.uuid4().hex[:8]}",
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
                        'group_signature': 'BTC_1h_volume_spike',
                        'original_pattern_strand_ids': [patterns[0]['id'], patterns[2]['id']]
                    },
                    'module_intelligence': {
                        'cluster_type': 'pattern_timeframe',
                        'cluster_key': 'BTC_1h_volume_spike'
                    }
                },
                {
                    'id': f"pred_eth_4h_mom_1_{uuid.uuid4().hex[:8]}",
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
                        'group_signature': 'ETH_4h_momentum',
                        'original_pattern_strand_ids': [patterns[3]['id'], patterns[4]['id']]
                    },
                    'module_intelligence': {
                        'cluster_type': 'pattern_timeframe',
                        'cluster_key': 'ETH_4h_momentum'
                    }
                },
                {
                    'id': f"pred_eth_4h_mom_2_{uuid.uuid4().hex[:8]}",
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
                        'group_signature': 'ETH_4h_momentum',
                        'original_pattern_strand_ids': [patterns[4]['id'], patterns[5]['id']]
                    },
                    'module_intelligence': {
                        'cluster_type': 'pattern_timeframe',
                        'cluster_key': 'ETH_4h_momentum'
                    }
                },
                {
                    'id': f"pred_eth_4h_mom_3_{uuid.uuid4().hex[:8]}",
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
                        'group_signature': 'ETH_4h_momentum',
                        'original_pattern_strand_ids': [patterns[3]['id'], patterns[5]['id']]
                    },
                    'module_intelligence': {
                        'cluster_type': 'pattern_timeframe',
                        'cluster_key': 'ETH_4h_momentum'
                    }
                }
            ]
            
            # Insert all prediction_review strands
            inserted_count = 0
            for pred in prediction_reviews:
                try:
                    # Prepare strand data for Supabase client
                    strand_data = {
                        'id': pred['id'],
                        'module': 'alpha',
                        'kind': 'prediction_review',
                        'symbol': pred['content']['asset'],
                        'timeframe': pred['content']['timeframe'],
                        'tags': ['cil', 'prediction', 'test'],
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'updated_at': datetime.now(timezone.utc).isoformat(),
                        'braid_level': 1,
                        'lesson': '',
                        'content': pred['content'],
                        'module_intelligence': pred['module_intelligence'],
                        'cluster_key': [
                            {"cluster_type": "asset", "cluster_key": pred['content']['asset'], "braid_level": 1, "consumed": False},
                            {"cluster_type": "timeframe", "cluster_key": pred['content']['timeframe'], "braid_level": 1, "consumed": False},
                            {"cluster_type": "pattern_timeframe", "cluster_key": pred['module_intelligence']['cluster_key'], "braid_level": 1, "consumed": False}
                        ]
                    }
                    
                    result = self.supabase_manager.insert_strand(strand_data)
                    if result:
                        inserted_count += 1
                    
                except Exception as e:
                    print(f"    ❌ Failed to insert {pred['id']}: {e}")
            
            print(f"  ✅ Inserted {inserted_count}/{len(prediction_reviews)} prediction review strands")
            self.test_results['prediction_strands_created'] = inserted_count
            
        except Exception as e:
            print(f"  ❌ Stage 2 failed: {e}")
            self.test_results['errors'].append(f"Stage 2: {e}")
    
    async def stage_3_test_learning_system(self):
        """Stage 3: Test the learning system with proper data"""
        print("\n🧠 Stage 3: Testing Learning System")
        print("-" * 40)
        
        try:
            # Initialize learning system
            learning_system = PerClusterLearningSystem(self.supabase_manager, self.llm_client)
            
            # Process all clusters
            print("  Processing clusters for learning...")
            result = await learning_system.process_all_clusters()
            
            # Count created braids
            total_braids = sum(len(braids) for braids in result.values())
            print(f"  ✅ Created {total_braids} learning braids across all clusters")
            
            # Verify braids in database
            query = "SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review' AND braid_level > 1"
            db_result = await self.supabase_manager.execute_query(query)
            db_braid_count = db_result[0][0] if db_result else 0
            
            print(f"  ✅ Verified {db_braid_count} braids in database")
            
            self.test_results['braids_created'] = db_braid_count
            
        except Exception as e:
            print(f"  ❌ Stage 3 failed: {e}")
            self.test_results['errors'].append(f"Stage 3: {e}")
    
    async def stage_4_test_multi_level_braids(self):
        """Stage 4: Test multi-level braid progression"""
        print("\n📈 Stage 4: Testing Multi-Level Braid Progression")
        print("-" * 50)
        
        try:
            # Check current braid levels
            query = """
                SELECT braid_level, COUNT(*) as count 
                FROM AD_strands 
                WHERE kind = 'prediction_review' AND braid_level > 1
                GROUP BY braid_level 
                ORDER BY braid_level
            """
            result = await self.supabase_manager.execute_query(query)
            
            print("  Current braid level distribution:")
            for row in result:
                level, count = row[0], row[1]
                print(f"    Level {level}: {count} braids")
            
            # Check for lessons in braids
            lesson_query = """
                SELECT COUNT(*) as count 
                FROM AD_strands 
                WHERE kind = 'prediction_review' AND braid_level > 1 AND lesson IS NOT NULL AND lesson != ''
            """
            lesson_result = await self.supabase_manager.execute_query(lesson_query)
            lesson_count = lesson_result[0][0] if lesson_result else 0
            
            print(f"  ✅ Braids with lessons: {lesson_count}")
            
            self.test_results['multi_level_braids'] = len(result)
            
        except Exception as e:
            print(f"  ❌ Stage 4 failed: {e}")
            self.test_results['errors'].append(f"Stage 4: {e}")
    
    def print_results(self):
        """Print test results"""
        print("\n" + "=" * 60)
        print("🏁 COMPLETE LEARNING SYSTEM TEST RESULTS")
        print("=" * 60)
        
        print(f"\n📊 SUMMARY STATISTICS:")
        print(f"  Pattern Strands Created: {self.test_results['pattern_strands_created']}")
        print(f"  Prediction Strands Created: {self.test_results['prediction_strands_created']}")
        print(f"  Braids Created: {self.test_results['braids_created']}")
        print(f"  Multi-Level Braids: {self.test_results['multi_level_braids']}")
        
        if self.test_results['errors']:
            print(f"\n❌ ERRORS ({len(self.test_results['errors'])}):")
            for error in self.test_results['errors']:
                print(f"  - {error}")
        else:
            print("\n🎉 No errors found!")
        
        # Overall assessment
        if self.test_results['braids_created'] > 0:
            print("🎉 Learning system is working with proper data flow!")
        else:
            print("⚠️  Learning system needs more work.")


async def main():
    """Run the complete test with pattern strands"""
    test = TestWithPatternStrands()
    await test.run_complete_test()


if __name__ == "__main__":
    asyncio.run(main())
