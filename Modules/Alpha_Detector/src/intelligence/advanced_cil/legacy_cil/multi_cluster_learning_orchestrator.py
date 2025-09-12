"""
Multi-Cluster Learning Orchestrator - Phase 4

Main orchestrator that coordinates the complete multi-cluster learning system.
Implements the step-by-step process flow for comprehensive learning.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from .multi_cluster_grouping_engine import MultiClusterGroupingEngine
from .per_cluster_learning_system import PerClusterLearningSystem
from .braid_level_manager import BraidLevelManager
from .llm_learning_analyzer import LLMLearningAnalyzer
from .database_query_examples import DatabaseQueryExamples


class MultiClusterLearningOrchestrator:
    """
    Main orchestrator for the multi-cluster learning system
    
    Coordinates the complete process:
    1. Multi-cluster grouping
    2. Per-cluster learning with LLM analysis
    3. Braid level progression
    4. Context system updates
    5. Statistics and monitoring
    """
    
    def __init__(self, supabase_manager, llm_client):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(f"{__name__}.orchestrator")
        
        # Initialize components
        self.cluster_grouper = MultiClusterGroupingEngine(supabase_manager)
        self.learning_system = PerClusterLearningSystem(supabase_manager, llm_client)
        self.braid_manager = BraidLevelManager(supabase_manager)
        self.llm_analyzer = LLMLearningAnalyzer(llm_client, supabase_manager)
        self.query_examples = DatabaseQueryExamples()
        
        # Process statistics
        self.process_stats = {
            'total_runs': 0,
            'total_learning_braids': 0,
            'total_braids': 0,
            'last_run': None,
            'success_rate': 0.0
        }
    
    async def run_complete_learning_cycle(self) -> Dict[str, Any]:
        """
        Run the complete multi-cluster learning cycle
        
        Returns:
            Dictionary with process results and statistics
        """
        try:
            self.logger.info("Starting complete multi-cluster learning cycle")
            start_time = datetime.now(timezone.utc)
            
            # Step 1: Multi-Cluster Grouping
            self.logger.info("Step 1: Multi-cluster grouping")
            cluster_groups = await self.cluster_grouper.get_all_cluster_groups()
            cluster_stats = self.cluster_grouper.get_cluster_statistics(cluster_groups)
            
            self.logger.info(f"Created {cluster_stats['total_groups']} groups across {cluster_stats['total_cluster_types']} cluster types")
            
            # Step 2: Per-Cluster Learning
            self.logger.info("Step 2: Per-cluster learning with LLM analysis")
            learning_results = await self.learning_system.process_all_clusters()
            
            total_learning_braids = sum(len(braids) for braids in learning_results.values())
            self.logger.info(f"Created {total_learning_braids} learning braids")
            
            # Step 3: Braid Level Progression
            self.logger.info("Step 3: Braid level progression")
            braid_results = await self.braid_manager.process_all_clusters(cluster_groups)
            
            total_braids = sum(len(braids) for braids in braid_results.values())
            self.logger.info(f"Created {total_braids} braids through level progression")
            
            # Step 4: Update Process Statistics
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            self.process_stats.update({
                'total_runs': self.process_stats['total_runs'] + 1,
                'total_learning_braids': self.process_stats['total_learning_braids'] + total_learning_braids,
                'total_braids': self.process_stats['total_braids'] + total_braids,
                'last_run': end_time.isoformat(),
                'success_rate': self.calculate_success_rate(learning_results, braid_results)
            })
            
            # Step 5: Generate Results
            results = {
                'success': True,
                'duration_seconds': duration,
                'cluster_statistics': cluster_stats,
                'learning_results': learning_results,
                'braid_results': braid_results,
                'process_statistics': self.process_stats,
                'timestamp': end_time.isoformat()
            }
            
            self.logger.info(f"Complete learning cycle finished in {duration:.2f} seconds")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in complete learning cycle: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def run_single_cluster_type(self, cluster_type: str) -> Dict[str, Any]:
        """
        Run learning for a single cluster type
        
        Args:
            cluster_type: Type of cluster to process
            
        Returns:
            Dictionary with process results
        """
        try:
            self.logger.info(f"Running learning for cluster type: {cluster_type}")
            
            # Get clusters for this type
            cluster_groups = await self.cluster_grouper.get_all_cluster_groups()
            
            if cluster_type not in cluster_groups:
                return {
                    'success': False,
                    'error': f"Cluster type {cluster_type} not found",
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Process learning for this cluster type
            learning_braids = await self.learning_system.process_single_cluster_type(cluster_type)
            
            # Process braid progression for this cluster type
            cluster_braids = await self.braid_manager.process_braid_creation(
                cluster_type, list(cluster_groups[cluster_type].keys())[0]
            )
            
            return {
                'success': True,
                'cluster_type': cluster_type,
                'learning_braids': learning_braids,
                'cluster_braids': cluster_braids,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error running single cluster type {cluster_type}: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        
        try:
            # Get learning system statistics
            learning_stats = await self.learning_system.get_learning_statistics()
            
            # Get braid statistics
            braid_stats = await self.braid_manager.get_braid_statistics()
            
            # Get cluster statistics
            cluster_groups = await self.cluster_grouper.get_all_cluster_groups()
            cluster_stats = self.cluster_grouper.get_cluster_statistics(cluster_groups)
            
            return {
                'learning_statistics': learning_stats,
                'braid_statistics': braid_stats,
                'cluster_statistics': cluster_stats,
                'process_statistics': self.process_stats,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system statistics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def calculate_success_rate(self, learning_results: Dict[str, List[str]], 
                             braid_results: Dict[str, List[str]]) -> float:
        """Calculate overall success rate of the learning process"""
        
        try:
            total_learning_braids = sum(len(braids) for braids in learning_results.values())
            total_braids = sum(len(braids) for braids in braid_results.values())
            
            if total_learning_braids == 0 and total_braids == 0:
                return 0.0
            
            # Simple success rate: higher is better
            success_rate = min(1.0, (total_learning_braids + total_braids) / 10.0)
            return success_rate
            
        except Exception as e:
            self.logger.warning(f"Error calculating success rate: {e}")
            return 0.0
    
    async def test_cluster_queries(self) -> Dict[str, Any]:
        """Test all cluster queries to ensure they work correctly"""
        
        try:
            self.logger.info("Testing cluster queries")
            
            test_results = {}
            cluster_types = [
                'pattern_timeframe', 'asset', 'timeframe', 'outcome', 
                'pattern', 'group_type', 'method'
            ]
            
            for cluster_type in cluster_types:
                try:
                    # Test getting cluster keys
                    cluster_keys = await self.cluster_grouper._get_cluster_keys(cluster_type)
                    
                    # Test getting cluster groups for first key
                    if cluster_keys:
                        test_key = cluster_keys[0]
                        groups = await self.cluster_grouper.get_cluster_groups(cluster_type, test_key)
                        
                        test_results[cluster_type] = {
                            'success': True,
                            'cluster_keys_count': len(cluster_keys),
                            'test_groups_count': len(groups),
                            'test_key': test_key
                        }
                    else:
                        test_results[cluster_type] = {
                            'success': True,
                            'cluster_keys_count': 0,
                            'test_groups_count': 0,
                            'test_key': None
                        }
                        
                except Exception as e:
                    test_results[cluster_type] = {
                        'success': False,
                        'error': str(e)
                    }
            
            return {
                'success': True,
                'test_results': test_results,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error testing cluster queries: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def run_learning_analysis_example(self) -> Dict[str, Any]:
        """Run an example learning analysis to demonstrate the system"""
        
        try:
            self.logger.info("Running learning analysis example")
            
            # Get a sample cluster for analysis
            cluster_groups = await self.cluster_grouper.get_all_cluster_groups()
            
            # Find a cluster with enough data
            sample_cluster_type = None
            sample_cluster_key = None
            sample_reviews = []
            
            for cluster_type, clusters in cluster_groups.items():
                for cluster_key, reviews in clusters.items():
                    if len(reviews) >= 3:  # Need at least 3 reviews
                        sample_cluster_type = cluster_type
                        sample_cluster_key = cluster_key
                        sample_reviews = reviews
                        break
                if sample_cluster_type:
                    break
            
            if not sample_cluster_type:
                return {
                    'success': False,
                    'error': 'No clusters with sufficient data for analysis',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Run LLM analysis on the sample cluster
            learning_braid = await self.llm_analyzer.analyze_cluster_for_learning(
                sample_cluster_type, sample_cluster_key, sample_reviews
            )
            
            return {
                'success': True,
                'sample_cluster_type': sample_cluster_type,
                'sample_cluster_key': sample_cluster_key,
                'sample_reviews_count': len(sample_reviews),
                'learning_braid': learning_braid,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error running learning analysis example: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def cleanup_old_data(self, days_to_keep: int = 30) -> Dict[str, Any]:
        """Clean up old data to prevent database bloat"""
        
        try:
            self.logger.info(f"Cleaning up data older than {days_to_keep} days")
            
            # Delete old prediction reviews
            old_reviews_query = """
                DELETE FROM AD_strands 
                WHERE kind = 'prediction_review' 
                AND created_at < NOW() - INTERVAL '%s days'
            """
            
            old_reviews_result = await self.supabase_manager.execute_query(old_reviews_query, [days_to_keep])
            
            # Delete old braids
            old_braids_query = """
                DELETE FROM AD_strands 
                WHERE kind = 'braid' 
                AND created_at < NOW() - INTERVAL '%s days'
            """
            
            old_braids_result = await self.supabase_manager.execute_query(old_braids_query, [days_to_keep])
            
            return {
                'success': True,
                'old_reviews_deleted': old_reviews_result,
                'old_braids_deleted': old_braids_result,
                'days_to_keep': days_to_keep,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def get_query_examples(self) -> Dict[str, Any]:
        """Get all database query examples"""
        
        return {
            'cluster_queries': self.query_examples.get_cluster_queries(),
            'cluster_key_queries': self.query_examples.get_cluster_key_queries(),
            'original_pattern_queries': self.query_examples.get_original_pattern_queries(),
            'braid_queries': self.query_examples.get_braid_queries(),
            'learning_braid_queries': self.query_examples.get_learning_braid_queries(),
            'cluster_key_queries_with_cluster_keys': self.query_examples.get_cluster_key_queries_with_cluster_keys(),
            'analytics_queries': self.query_examples.get_analytics_queries(),
            'example_queries': self.query_examples.get_example_queries()
        }
