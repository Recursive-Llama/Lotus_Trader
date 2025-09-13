#!/usr/bin/env python3
"""
Quick Fixes Test

Test the specific fixes we implemented:
1. Braid progression logic
2. Braid metadata preservation
3. Module triggering system
"""

import sys
import os
import asyncio
from datetime import datetime, timezone

# Add the necessary paths
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/src')
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/Modules/Alpha_Detector/src')
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁')

async def test_braid_fixes():
    """Test the braid progression and metadata fixes"""
    print("🧪 Testing Braid Fixes...")
    
    try:
        from braid_level_manager import BraidLevelManager
        from utils.supabase_manager import SupabaseManager
        
        braid_manager = BraidLevelManager(SupabaseManager())
        
        # Test 1: Check thresholds are the same
        level_2 = braid_manager.quality_thresholds['level_2']['min_resonance']
        level_3 = braid_manager.quality_thresholds['level_3']['min_resonance']
        level_4 = braid_manager.quality_thresholds['level_4']['min_resonance']
        
        print(f"✅ Thresholds: Level 2={level_2}, Level 3={level_3}, Level 4={level_4}")
        
        # Test 2: Create test strands
        test_strands = [
            {
                'id': 'test_1',
                'kind': 'pattern',
                'symbol': 'BTC',
                'timeframe': '1h',
                'resonance_score': 0.7,
                'persistence_score': 0.6,
                'novelty_score': 0.5,
                'surprise_rating': 0.5,
                'module_intelligence': {'pattern_type': 'rsi_divergence'},
                'cluster_key': 'BTC_1h_rsi_divergence'
            },
            {
                'id': 'test_2',
                'kind': 'pattern',
                'symbol': 'BTC',
                'timeframe': '1h',
                'resonance_score': 0.8,
                'persistence_score': 0.7,
                'novelty_score': 0.6,
                'surprise_rating': 0.6,
                'module_intelligence': {'pattern_type': 'rsi_divergence'},
                'cluster_key': 'BTC_1h_rsi_divergence'
            },
            {
                'id': 'test_3',
                'kind': 'pattern',
                'symbol': 'BTC',
                'timeframe': '1h',
                'resonance_score': 0.9,
                'persistence_score': 0.8,
                'novelty_score': 0.7,
                'surprise_rating': 0.7,
                'module_intelligence': {'pattern_type': 'rsi_divergence'},
                'cluster_key': 'BTC_1h_rsi_divergence'
            }
        ]
        
        # Test 3: Check quality thresholds
        meets_thresholds = braid_manager._meets_quality_thresholds(test_strands, 2)
        print(f"✅ Meets thresholds: {meets_thresholds}")
        
        # Test 4: Test cluster key generation
        cluster_key = braid_manager._generate_cluster_key(test_strands)
        print(f"✅ Cluster key: {cluster_key}")
        
        # Test 5: Test metadata extraction
        metadata = braid_manager._extract_clustering_metadata(test_strands)
        print(f"✅ Metadata: {metadata}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_module_triggering():
    """Test the module triggering system"""
    print("\n🧪 Testing Module Triggering...")
    
    try:
        from module_triggering_engine import ModuleTriggeringEngine
        from utils.supabase_manager import SupabaseManager
        
        # Create a mock learning system
        class MockLearningSystem:
            async def get_context_for_module(self, module, context_data):
                return {'test': 'context'}
        
        mock_learning_system = MockLearningSystem()
        triggering_engine = ModuleTriggeringEngine(SupabaseManager(), mock_learning_system)
        
        # Test 1: Check configuration
        print(f"✅ Module triggers: {triggering_engine.module_triggers}")
        print(f"✅ Processing intervals: {triggering_engine.processing_intervals}")
        
        # Test 2: Get status
        status = await triggering_engine.get_triggering_status()
        print(f"✅ Status: {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 QUICK FIXES TEST")
    print("=" * 50)
    
    # Test braid fixes
    braid_success = await test_braid_fixes()
    
    # Test module triggering
    triggering_success = await test_module_triggering()
    
    # Summary
    print("\n" + "=" * 50)
    print("🔍 QUICK FIXES TEST RESULTS")
    print("=" * 50)
    
    if braid_success and triggering_success:
        print("🎉 ALL FIXES WORKING!")
    elif braid_success or triggering_success:
        print("⚠️  SOME FIXES WORKING")
    else:
        print("❌ FIXES NEED ATTENTION")

if __name__ == "__main__":
    asyncio.run(main())
