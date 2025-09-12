#!/usr/bin/env python3
"""
Database Fix Test

This test fixes the database insertion issues by using the proper Supabase client methods
instead of the broken raw SQL approach.
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

from intelligence.system_control.central_intelligence_layer.llm_learning_analyzer import LLMLearningAnalyzer
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class DatabaseFixTest:
    """Test and fix database insertion issues"""
    
    def __init__(self):
        self.supabase_manager = SupabaseManager()
        self.llm_client = OpenRouterClient()
        self.test_results = {
            'insertions_attempted': 0,
            'insertions_successful': 0,
            'braids_created': 0,
            'errors': []
        }
    
    async def run_test(self):
        """Run the database fix test"""
        print("🔧 Database Fix Test")
        print("=" * 40)
        
        try:
            # Test 1: Fix LLMLearningAnalyzer database insertion
            await self.test_llm_analyzer_fix()
            
            # Test 2: Test direct braid creation
            await self.test_direct_braid_creation()
            
            # Test 3: Verify results
            await self.verify_results()
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            self.test_results['errors'].append(str(e))
        
        # Print results
        self.print_results()
    
    async def test_llm_analyzer_fix(self):
        """Fix LLMLearningAnalyzer database insertion"""
        print("\n🔧 Fixing LLMLearningAnalyzer Database Insertion")
        print("-" * 50)
        
        try:
            # Create a fixed version of the LLMLearningAnalyzer
            class FixedLLMLearningAnalyzer(LLMLearningAnalyzer):
                """Fixed version that uses proper Supabase client methods"""
                
                async def store_learning_braid(self, learning_braid: Dict[str, Any]) -> bool:
                    """Store learning braid using proper Supabase client method"""
                    
                    try:
                        # Use the proper Supabase client method instead of raw SQL
                        strand_data = {
                            'id': learning_braid['id'],
                            'module': 'alpha',
                            'kind': learning_braid['kind'],
                            'symbol': learning_braid['content'].get('asset', 'UNKNOWN'),
                            'timeframe': learning_braid['content'].get('timeframe', '1h'),
                            'tags': learning_braid['tags'],
                            'created_at': learning_braid['created_at'],
                            'updated_at': learning_braid['created_at'],
                            'braid_level': learning_braid['braid_level'],
                            'lesson': learning_braid['lesson'],
                            'content': learning_braid['content'],
                            'module_intelligence': learning_braid['module_intelligence'],
                            'cluster_key': learning_braid.get('cluster_key', [])
                        }
                        
                        result = self.supabase_manager.insert_strand(strand_data)
                        
                        if result:
                            self.logger.info(f"Stored learning braid: {learning_braid['id']}")
                            return True
                        else:
                            self.logger.error(f"Failed to store learning braid: {learning_braid['id']}")
                            return False
                            
                    except Exception as e:
                        self.logger.error(f"Error storing learning braid: {e}")
                        return False
            
            # Test the fixed analyzer
            fixed_analyzer = FixedLLMLearningAnalyzer(self.llm_client, self.supabase_manager)
            
            # Create sample cluster data
            sample_cluster = [
                {
                    'id': 'test_1',
                    'content': {
                        'asset': 'BTC',
                        'timeframe': '1h',
                        'pattern_type': 'volume_spike',
                        'success': True,
                        'confidence': 0.8,
                        'return_pct': 3.2,
                        'method': 'code'
                    },
                    'module_intelligence': {
                        'cluster_type': 'pattern_timeframe',
                        'cluster_key': 'BTC_1h_volume_spike'
                    }
                },
                {
                    'id': 'test_2',
                    'content': {
                        'asset': 'BTC',
                        'timeframe': '1h',
                        'pattern_type': 'volume_spike',
                        'success': False,
                        'confidence': 0.6,
                        'return_pct': -1.5,
                        'method': 'llm'
                    },
                    'module_intelligence': {
                        'cluster_type': 'pattern_timeframe',
                        'cluster_key': 'BTC_1h_volume_spike'
                    }
                },
                {
                    'id': 'test_3',
                    'content': {
                        'asset': 'BTC',
                        'timeframe': '1h',
                        'pattern_type': 'volume_spike',
                        'success': True,
                        'confidence': 0.9,
                        'return_pct': 4.1,
                        'method': 'code'
                    },
                    'module_intelligence': {
                        'cluster_type': 'pattern_timeframe',
                        'cluster_key': 'BTC_1h_volume_spike'
                    }
                }
            ]
            
            print("  Testing fixed LLM analyzer...")
            
            # Run the fixed analysis
            analysis_result = await fixed_analyzer.analyze_cluster_for_learning(
                'pattern_timeframe', 
                'BTC_1h_volume_spike', 
                sample_cluster
            )
            
            if analysis_result:
                print(f"  ✅ Fixed LLM analyzer working")
                print(f"    Braid ID: {analysis_result['id']}")
                print(f"    Braid Level: {analysis_result['braid_level']}")
                print(f"    Has Lesson: {bool(analysis_result.get('lesson'))}")
                self.test_results['insertions_successful'] += 1
                self.test_results['braids_created'] += 1
            else:
                print("  ❌ Fixed LLM analyzer failed")
                self.test_results['errors'].append("Fixed LLM analyzer failed")
            
            self.test_results['insertions_attempted'] += 1
            
        except Exception as e:
            print(f"❌ LLM analyzer fix failed: {e}")
            self.test_results['errors'].append(f"LLM analyzer fix: {e}")
    
    async def test_direct_braid_creation(self):
        """Test direct braid creation using proper Supabase client"""
        print("\n🔄 Testing Direct Braid Creation")
        print("-" * 40)
        
        try:
            # Create a test braid directly
            braid_id = f"test_braid_{uuid.uuid4().hex[:8]}"
            braid_data = {
                'id': braid_id,
                'module': 'alpha',
                'kind': 'prediction_review',
                'symbol': 'BTC',
                'timeframe': '1h',
                'tags': ['cil', 'learning', 'braid', 'test'],
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'braid_level': 2,
                'lesson': 'Test lesson: BTC 1h volume spikes show higher success rates when combined with code-based analysis.',
                'content': {
                    'asset': 'BTC',
                    'timeframe': '1h',
                    'pattern_type': 'volume_spike',
                    'group_type': 'single_single',
                    'group_signature': 'BTC_1h_volume_spike',
                    'success': True,
                    'confidence': 0.77,
                    'return_pct': 1.93,
                    'max_drawdown': 0.8,
                    'method': 'code',
                    'source_cluster': 'BTC_1h_volume_spike',
                    'source_strand_ids': ['test_1', 'test_2', 'test_3']
                },
                'module_intelligence': {
                    'cluster_type': 'pattern_timeframe',
                    'cluster_key': 'BTC_1h_volume_spike',
                    'braid_level': 2,
                    'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
                    'confidence': 0.8
                },
                'cluster_key': [
                    {"cluster_type": "asset", "cluster_key": "BTC", "braid_level": 2, "consumed": False},
                    {"cluster_type": "timeframe", "cluster_key": "1h", "braid_level": 2, "consumed": False},
                    {"cluster_type": "pattern_timeframe", "cluster_key": "BTC_1h_volume_spike", "braid_level": 2, "consumed": False}
                ]
            }
            
            print(f"  Creating test braid: {braid_id}")
            
            # Insert using proper Supabase client method
            result = self.supabase_manager.insert_strand(braid_data)
            
            if result:
                print(f"  ✅ Direct braid creation successful")
                print(f"    Braid ID: {result['id']}")
                print(f"    Braid Level: {result['braid_level']}")
                print(f"    Has Lesson: {bool(result.get('lesson'))}")
                self.test_results['insertions_successful'] += 1
                self.test_results['braids_created'] += 1
            else:
                print("  ❌ Direct braid creation failed")
                self.test_results['errors'].append("Direct braid creation failed")
            
            self.test_results['insertions_attempted'] += 1
            
        except Exception as e:
            print(f"❌ Direct braid creation failed: {e}")
            self.test_results['errors'].append(f"Direct braid creation: {e}")
    
    async def verify_results(self):
        """Verify the results"""
        print("\n✅ Verifying Results")
        print("-" * 40)
        
        try:
            # Check if braids were actually created
            query = "SELECT COUNT(*) FROM AD_strands WHERE kind = 'prediction_review' AND braid_level > 1 AND (id LIKE 'test_%' OR id LIKE 'pred_%')"
            result = await self.supabase_manager.execute_query(query)
            braid_count = result[0][0] if result else 0
            
            print(f"  Braids with level > 1: {braid_count}")
            
            if braid_count > 0:
                # Check the actual braid content
                query = "SELECT * FROM AD_strands WHERE kind = 'prediction_review' AND braid_level > 1 AND (id LIKE 'test_%' OR id LIKE 'pred_%') LIMIT 1"
                result = await self.supabase_manager.execute_query(query)
                if result:
                    braid = dict(result[0])
                    print(f"  ✅ Braid verification successful")
                    print(f"    Braid ID: {braid['id']}")
                    print(f"    Braid Level: {braid['braid_level']}")
                    print(f"    Has Lesson: {bool(braid.get('lesson'))}")
                    print(f"    Lesson Preview: {braid.get('lesson', '')[:100]}...")
                else:
                    print("  ⚠️  No braid details found")
            else:
                print("  ❌ No braids found in database")
                self.test_results['errors'].append("No braids found in database")
            
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            self.test_results['errors'].append(f"Verification: {e}")
    
    def print_results(self):
        """Print test results"""
        print("\n" + "=" * 40)
        print("🏁 DATABASE FIX TEST RESULTS")
        print("=" * 40)
        
        print(f"Insertions Attempted: {self.test_results['insertions_attempted']}")
        print(f"Insertions Successful: {self.test_results['insertions_successful']}")
        print(f"Braids Created: {self.test_results['braids_created']}")
        
        if self.test_results['errors']:
            print(f"\n❌ ERRORS ({len(self.test_results['errors'])}):")
            for error in self.test_results['errors']:
                print(f"  - {error}")
        else:
            print("\n🎉 All database fixes working!")
        
        # Overall assessment
        success_rate = (self.test_results['insertions_successful'] / self.test_results['insertions_attempted']) * 100 if self.test_results['insertions_attempted'] > 0 else 0
        
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 Database issues are fixed!")
        elif success_rate >= 50:
            print("✅ Database issues are mostly fixed.")
        else:
            print("⚠️  Database issues need more work.")


async def main():
    """Run the database fix test"""
    test = DatabaseFixTest()
    await test.run_test()


if __name__ == "__main__":
    asyncio.run(main())
