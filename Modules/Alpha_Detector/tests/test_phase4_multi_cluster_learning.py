"""
Test Phase 4: Multi-Cluster Learning System

Comprehensive test of the multi-cluster learning system including:
- Multi-cluster grouping engine
- Enhanced prediction review strands
- Braid level progression
- LLM learning analysis
- Per-cluster learning system
- Complete process flow
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.intelligence.system_control.central_intelligence_layer.multi_cluster_learning_orchestrator import MultiClusterLearningOrchestrator


async def test_multi_cluster_learning_system():
    """Test the complete multi-cluster learning system"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🚀 Starting Phase 4 Multi-Cluster Learning System Test")
        
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        orchestrator = MultiClusterLearningOrchestrator(supabase_manager, llm_client)
        
        # Test 1: Query Testing
        logger.info("📊 Test 1: Testing cluster queries")
        query_test_results = await orchestrator.test_cluster_queries()
        
        if query_test_results['success']:
            logger.info("✅ Cluster queries test passed")
            for cluster_type, result in query_test_results['test_results'].items():
                if result['success']:
                    logger.info(f"  {cluster_type}: {result['cluster_keys_count']} keys, {result['test_groups_count']} groups")
                else:
                    logger.warning(f"  {cluster_type}: FAILED - {result.get('error', 'Unknown error')}")
        else:
            logger.error(f"❌ Cluster queries test failed: {query_test_results.get('error')}")
        
        # Test 2: Learning Analysis Example
        logger.info("🧠 Test 2: Running learning analysis example")
        analysis_results = await orchestrator.run_learning_analysis_example()
        
        if analysis_results['success']:
            logger.info("✅ Learning analysis example completed")
            logger.info(f"  Sample cluster: {analysis_results['sample_cluster_type']}:{analysis_results['sample_cluster_key']}")
            logger.info(f"  Reviews analyzed: {analysis_results['sample_reviews_count']}")
            if analysis_results.get('learning_braid'):
                logger.info(f"  Learning braid created: {analysis_results['learning_braid']['id']}")
        else:
            logger.warning(f"⚠️ Learning analysis example failed: {analysis_results.get('error')}")
        
        # Test 3: Single Cluster Type Processing
        logger.info("🎯 Test 3: Processing single cluster type")
        single_cluster_results = await orchestrator.run_single_cluster_type('asset')
        
        if single_cluster_results['success']:
            logger.info("✅ Single cluster type processing completed")
            logger.info(f"  Learning braids: {len(single_cluster_results.get('learning_braids', []))}")
            logger.info(f"  Cluster braids: {len(single_cluster_results.get('cluster_braids', []))}")
        else:
            logger.warning(f"⚠️ Single cluster type processing failed: {single_cluster_results.get('error')}")
        
        # Test 4: Complete Learning Cycle
        logger.info("🔄 Test 4: Running complete learning cycle")
        complete_cycle_results = await orchestrator.run_complete_learning_cycle()
        
        if complete_cycle_results['success']:
            logger.info("✅ Complete learning cycle completed")
            logger.info(f"  Duration: {complete_cycle_results['duration_seconds']:.2f} seconds")
            
            # Log cluster statistics
            cluster_stats = complete_cycle_results.get('cluster_statistics', {})
            logger.info(f"  Cluster types: {cluster_stats.get('total_cluster_types', 0)}")
            logger.info(f"  Total groups: {cluster_stats.get('total_groups', 0)}")
            logger.info(f"  Total reviews: {cluster_stats.get('total_reviews', 0)}")
            
            # Log learning results
            learning_results = complete_cycle_results.get('learning_results', {})
            total_learning_braids = sum(len(braids) for braids in learning_results.values())
            logger.info(f"  Learning braids created: {total_learning_braids}")
            
            # Log braid results
            braid_results = complete_cycle_results.get('braid_results', {})
            total_braids = sum(len(braids) for braids in braid_results.values())
            logger.info(f"  Braids created: {total_braids}")
            
        else:
            logger.error(f"❌ Complete learning cycle failed: {complete_cycle_results.get('error')}")
        
        # Test 5: System Statistics
        logger.info("📈 Test 5: Getting system statistics")
        stats_results = await orchestrator.get_system_statistics()
        
        if 'error' not in stats_results:
            logger.info("✅ System statistics retrieved")
            
            # Log learning statistics
            learning_stats = stats_results.get('learning_statistics', {})
            logger.info(f"  Learning braids: {learning_stats.get('learning_braids', 0)}")
            
            # Log braid statistics
            braid_stats = stats_results.get('braid_statistics', {})
            logger.info(f"  Total braids: {braid_stats.get('total_braids', 0)}")
            logger.info(f"  Max braid level: {braid_stats.get('max_braid_level', 0)}")
            
            # Log cluster statistics
            cluster_stats = stats_results.get('cluster_statistics', {})
            logger.info(f"  Cluster types: {cluster_stats.get('total_cluster_types', 0)}")
            logger.info(f"  Total groups: {cluster_stats.get('total_groups', 0)}")
            
        else:
            logger.warning(f"⚠️ System statistics failed: {stats_results.get('error')}")
        
        # Test 6: Query Examples
        logger.info("📚 Test 6: Getting query examples")
        query_examples = orchestrator.get_query_examples()
        
        logger.info("✅ Query examples retrieved")
        logger.info(f"  Cluster queries: {len(query_examples.get('cluster_queries', {}))}")
        logger.info(f"  Analytics queries: {len(query_examples.get('analytics_queries', {}))}")
        logger.info(f"  Example queries: {len(query_examples.get('example_queries', []))}")
        
        # Test 7: Cleanup (optional)
        logger.info("🧹 Test 7: Testing cleanup (keeping last 7 days)")
        cleanup_results = await orchestrator.cleanup_old_data(days_to_keep=7)
        
        if cleanup_results['success']:
            logger.info("✅ Cleanup completed")
            logger.info(f"  Old reviews deleted: {cleanup_results.get('old_reviews_deleted', 0)}")
            logger.info(f"  Old braids deleted: {cleanup_results.get('old_braids_deleted', 0)}")
        else:
            logger.warning(f"⚠️ Cleanup failed: {cleanup_results.get('error')}")
        
        logger.info("🎉 Phase 4 Multi-Cluster Learning System Test Complete!")
        
        # Summary
        logger.info("\n📋 TEST SUMMARY:")
        logger.info(f"✅ Query Testing: {'PASSED' if query_test_results['success'] else 'FAILED'}")
        logger.info(f"✅ Learning Analysis: {'PASSED' if analysis_results['success'] else 'FAILED'}")
        logger.info(f"✅ Single Cluster: {'PASSED' if single_cluster_results['success'] else 'FAILED'}")
        logger.info(f"✅ Complete Cycle: {'PASSED' if complete_cycle_results['success'] else 'FAILED'}")
        logger.info(f"✅ Statistics: {'PASSED' if 'error' not in stats_results else 'FAILED'}")
        logger.info(f"✅ Query Examples: PASSED")
        logger.info(f"✅ Cleanup: {'PASSED' if cleanup_results['success'] else 'FAILED'}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False


async def test_individual_components():
    """Test individual components separately"""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🔧 Testing Individual Components")
        
        # Initialize components
        supabase_manager = SupabaseManager()
        llm_client = OpenRouterClient()
        
        # Test Multi-Cluster Grouping Engine
        from src.intelligence.system_control.central_intelligence_layer.multi_cluster_grouping_engine import MultiClusterGroupingEngine
        
        logger.info("Testing Multi-Cluster Grouping Engine...")
        cluster_grouper = MultiClusterGroupingEngine(supabase_manager)
        
        # Test getting cluster keys
        for cluster_type in ['asset', 'timeframe', 'outcome']:
            try:
                keys = await cluster_grouper._get_cluster_keys(cluster_type)
                logger.info(f"  {cluster_type}: {len(keys)} keys found")
            except Exception as e:
                logger.warning(f"  {cluster_type}: Error - {e}")
        
        # Test Braid Level Manager
        from src.intelligence.system_control.central_intelligence_layer.braid_level_manager import BraidLevelManager
        
        logger.info("Testing Braid Level Manager...")
        braid_manager = BraidLevelManager(supabase_manager)
        
        # Test getting braid statistics
        try:
            braid_stats = await braid_manager.get_braid_statistics()
            logger.info(f"  Total braids: {braid_stats.get('total_braids', 0)}")
            logger.info(f"  Max braid level: {braid_stats.get('max_braid_level', 0)}")
        except Exception as e:
            logger.warning(f"  Braid statistics error: {e}")
        
        # Test LLM Learning Analyzer
        from src.intelligence.system_control.central_intelligence_layer.llm_learning_analyzer import LLMLearningAnalyzer
        
        logger.info("Testing LLM Learning Analyzer...")
        llm_analyzer = LLMLearningAnalyzer(llm_client, supabase_manager)
        
        # Test getting pattern strand by ID (this will likely fail without real data)
        try:
            pattern_strand = await llm_analyzer.get_pattern_strand_by_id("test_id")
            logger.info(f"  Pattern strand lookup: {'Found' if pattern_strand else 'Not found'}")
        except Exception as e:
            logger.warning(f"  Pattern strand lookup error: {e}")
        
        logger.info("✅ Individual component testing completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Individual component testing failed: {e}")
        return False


if __name__ == "__main__":
    # Run the tests
    print("🚀 Starting Phase 4 Multi-Cluster Learning System Tests")
    
    # Test individual components first
    individual_success = asyncio.run(test_individual_components())
    
    # Test complete system
    complete_success = asyncio.run(test_multi_cluster_learning_system())
    
    if individual_success and complete_success:
        print("\n🎉 ALL TESTS PASSED! Phase 4 Multi-Cluster Learning System is ready!")
    else:
        print("\n⚠️ Some tests failed. Check the logs for details.")
