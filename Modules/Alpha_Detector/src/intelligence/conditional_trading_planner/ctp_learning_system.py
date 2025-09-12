"""
CTP Learning System

Reuses CIL learning infrastructure to analyze trade outcomes and create 
learning braids for strategy improvement.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

# Import CIL learning components
from ..system_control.central_intelligence_layer.multi_cluster_grouping_engine import MultiClusterGroupingEngine
from ..system_control.central_intelligence_layer.per_cluster_learning_system import PerClusterLearningSystem
from ..system_control.central_intelligence_layer.llm_learning_analyzer import LLMLearningAnalyzer
from ..system_control.central_intelligence_layer.braid_level_manager import BraidLevelManager


class CTPLearningSystem:
    """
    CTP Learning System that reuses CIL learning infrastructure.
    
    Responsibilities:
    1. Group trade outcomes into clusters using CIL system
    2. Analyze clusters with CTP-specific LLM prompts
    3. Create trade_outcome braids for strategy improvement
    4. Provide learning insights for trading plan optimization
    """
    
    def __init__(self, supabase_manager, llm_client):
        """
        Initialize CTP learning system with CIL components.
        
        Args:
            supabase_manager: Database manager for strand operations
            llm_client: LLM client for analysis
        """
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.logger = logging.getLogger(f"{__name__}.ctp_learning")
        
        # Initialize CIL learning components for trade outcomes
        self.cluster_grouper = MultiClusterGroupingEngine(supabase_manager)
        self.learning_system = PerClusterLearningSystem(supabase_manager, llm_client)
        self.llm_analyzer = CTPLLMLearningAnalyzer(llm_client, supabase_manager)
        self.braid_manager = BraidLevelManager(supabase_manager)
        
        self.logger.info("CTP Learning System initialized with CIL components")
    
    async def process_trade_outcome_learning(self) -> Dict[str, Any]:
        """
        Process trade outcomes for learning and create braids.
        
        Returns:
            Dictionary with learning results
        """
        try:
            self.logger.info("Starting CTP trade outcome learning")
            
            # Step 1: Get all trade outcome clusters
            clusters = await self._get_trade_outcome_clusters()
            
            if not clusters:
                self.logger.warning("No trade outcome clusters found")
                return {"clusters_processed": 0, "braids_created": 0}
            
            # Step 2: Process clusters for learning (with parallel processing)
            results = {}
            total_braids = 0
            
            # Collect all clusters that need processing
            clusters_to_process = []
            for cluster_type, cluster_groups in clusters.items():
                self.logger.info(f"Found {cluster_type} clusters: {len(cluster_groups)} groups")
                
                for cluster_key, trade_outcomes in cluster_groups.items():
                    if len(trade_outcomes) >= 3:  # Minimum threshold for learning
                        clusters_to_process.append((cluster_type, cluster_key, trade_outcomes))
            
            self.logger.info(f"Processing {len(clusters_to_process)} clusters in parallel...")
            
            # Process clusters in parallel (limit to 5 concurrent to avoid overwhelming LLM)
            import asyncio
            semaphore = asyncio.Semaphore(5)  # Limit concurrent LLM calls
            
            async def process_single_cluster(cluster_type, cluster_key, trade_outcomes):
                async with semaphore:
                    try:
                        learning_braid = await self.llm_analyzer.analyze_trade_outcome_cluster(
                            cluster_type, cluster_key, trade_outcomes
                        )
                        return cluster_type, cluster_key, learning_braid
                    except Exception as e:
                        self.logger.error(f"Error processing cluster {cluster_type}:{cluster_key}: {e}")
                        return cluster_type, cluster_key, None
            
            # Process all clusters in parallel
            cluster_tasks = [
                process_single_cluster(cluster_type, cluster_key, trade_outcomes)
                for cluster_type, cluster_key, trade_outcomes in clusters_to_process
            ]
            
            cluster_results = await asyncio.gather(*cluster_tasks, return_exceptions=True)
            
            # Organize results by cluster type
            for result in cluster_results:
                if isinstance(result, Exception):
                    self.logger.error(f"Cluster processing failed: {result}")
                    continue
                
                cluster_type, cluster_key, learning_braid = result
                
                if cluster_type not in results:
                    results[cluster_type] = []
                
                if learning_braid:
                    results[cluster_type].append(learning_braid['id'])
                    total_braids += 1
            
            self.logger.info(f"CTP learning completed: {total_braids} braids created")
            return {
                "clusters_processed": sum(len(groups) for groups in clusters.values()),
                "braids_created": total_braids,
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Error in CTP trade outcome learning: {e}")
            return {"error": str(e), "success": False}
    
    async def process_all_trade_outcomes(self) -> Dict[str, Any]:
        """
        Process all available trade outcomes for learning.
        
        Returns:
            Dictionary with learning results
        """
        try:
            self.logger.info("Processing all trade outcomes for learning")
            
            # Use the same process as CIL but for trade outcomes
            result = await self.learning_system.process_all_clusters()
            
            self.logger.info(f"All trade outcomes processed: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing all trade outcomes: {e}")
            return {"error": str(e), "success": False}
    
    async def _get_trade_outcome_clusters(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Get trade outcome clusters using CIL clustering system.
        
        Returns:
            Dictionary of clusters by type and key
        """
        try:
            # Get all trade outcome strands
            result = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'trade_outcome').execute()
            
            if not result.data:
                return {}
            
            trade_outcomes = result.data
            
            # Group by cluster types (same as CIL but for trade outcomes)
            clusters = {
                'pattern_timeframe': {},
                'asset': {},
                'timeframe': {},
                'outcome': {},
                'pattern': {},
                'group_type': {},
                'method': {}
            }
            
            for trade_outcome in trade_outcomes:
                # Extract cluster keys for each trade outcome
                cluster_keys = self._extract_trade_outcome_cluster_keys(trade_outcome)
                
                for cluster_type, cluster_key in cluster_keys.items():
                    if cluster_key not in clusters[cluster_type]:
                        clusters[cluster_type][cluster_key] = []
                    clusters[cluster_type][cluster_key].append(trade_outcome)
            
            # Filter out clusters with less than 3 trade outcomes
            filtered_clusters = {}
            for cluster_type, cluster_groups in clusters.items():
                filtered_groups = {k: v for k, v in cluster_groups.items() if len(v) >= 3}
                if filtered_groups:
                    filtered_clusters[cluster_type] = filtered_groups
            
            return filtered_clusters
            
        except Exception as e:
            self.logger.error(f"Error getting trade outcome clusters: {e}")
            return {}
    
    def _extract_trade_outcome_cluster_keys(self, trade_outcome: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract cluster keys from trade outcome strand.
        
        Args:
            trade_outcome: Trade outcome strand data
            
        Returns:
            Dictionary mapping cluster types to cluster keys
        """
        try:
            content = trade_outcome.get('content', {})
            module_intelligence = trade_outcome.get('module_intelligence', {})
            
            # Helper function to get value from either field
            def get_value(key: str, default=''):
                if content.get(key) is not None:
                    return str(content.get(key, default))
                return str(module_intelligence.get(key, default))
            
            # Extract cluster keys
            asset = get_value('asset', 'unknown')
            timeframe = get_value('timeframe', 'unknown')
            success = get_value('success', 'false').lower() == 'true'
            method = get_value('execution_method', 'unknown')
            
            # Create group signature for pattern_timeframe
            group_signature = f"{asset}_{timeframe}_trade_execution"
            
            return {
                'pattern_timeframe': group_signature,
                'asset': asset,
                'timeframe': timeframe,
                'outcome': 'success' if success else 'failure',
                'pattern': 'trade_execution',
                'group_type': 'trade_execution',
                'method': method
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting trade outcome cluster keys: {e}")
            return {}
    
    async def get_learning_insights(self, cluster_type: str = None, cluster_key: str = None) -> List[Dict[str, Any]]:
        """
        Get learning insights from trade outcome analysis.
        
        Args:
            cluster_type: Optional cluster type filter
            cluster_key: Optional cluster key filter
            
        Returns:
            List of learning insights
        """
        try:
            # Query for trade outcome braids (braid_level > 1)
            query = self.supabase_manager.client.table('ad_strands').select('*').eq('kind', 'trade_outcome').gt('braid_level', 1)
            
            if cluster_type:
                query = query.contains('content', {'cluster_type': cluster_type})
            
            if cluster_key:
                query = query.contains('content', {'cluster_key': cluster_key})
            
            result = query.order('created_at', desc=True).execute()
            
            insights = []
            for braid in result.data:
                content = braid.get('content', {})
                insights.append({
                    "braid_id": braid['id'],
                    "braid_level": braid.get('braid_level', 1),
                    "cluster_type": content.get('cluster_type', 'unknown'),
                    "cluster_key": content.get('cluster_key', 'unknown'),
                    "lesson": braid.get('lesson', ''),
                    "created_at": braid.get('created_at'),
                    "learning_insights": content.get('learning_insights', {})
                })
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error getting learning insights: {e}")
            return []
    
    async def get_learning_insights_for_clusters(self, cluster_keys: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get learning insights for specific cluster keys (used in trading plan generation).
        
        Args:
            cluster_keys: List of cluster key dictionaries from prediction review
            
        Returns:
            Dictionary mapping cluster keys to learning insights
        """
        try:
            insights_by_cluster = {}
            
            for cluster_key in cluster_keys:
                cluster_type = cluster_key.get('cluster_type')
                cluster_key_value = cluster_key.get('cluster_key')
                
                if cluster_type and cluster_key_value:
                    # Get insights for this specific cluster
                    insights = await self.get_learning_insights(cluster_type, cluster_key_value)
                    insights_by_cluster[f"{cluster_type}:{cluster_key_value}"] = insights
            
            return insights_by_cluster
            
        except Exception as e:
            self.logger.error(f"Error getting learning insights for clusters: {e}")
            return {}
    
    async def get_learning_statistics(self) -> Dict[str, Any]:
        """
        Get CTP learning system statistics.
        
        Returns:
            Dictionary with learning statistics
        """
        try:
            # Get trade outcome counts by braid level
            result = self.supabase_manager.client.table('ad_strands').select('braid_level').eq('kind', 'trade_outcome').execute()
            
            braid_levels = {}
            for strand in result.data:
                level = strand.get('braid_level', 1)
                braid_levels[level] = braid_levels.get(level, 0) + 1
            
            # Get learning insights count
            insights_result = self.supabase_manager.client.table('ad_strands').select('id').eq('kind', 'trade_outcome').gt('braid_level', 1).execute()
            
            return {
                "total_trade_outcomes": len(result.data),
                "learning_braids": len(insights_result.data),
                "braid_level_distribution": braid_levels,
                "highest_braid_level": max(braid_levels.keys()) if braid_levels else 1
            }
            
        except Exception as e:
            self.logger.error(f"Error getting learning statistics: {e}")
            return {"error": str(e)}


class CTPLLMLearningAnalyzer(LLMLearningAnalyzer):
    """
    CTP-specific LLM Learning Analyzer that extends CIL's analyzer.
    
    Uses CTP-specific prompts for trade execution analysis while reusing
    the core infrastructure from CIL's LLMLearningAnalyzer.
    """
    
    def create_cluster_analysis_prompt(self, cluster_data: Dict[str, Any]) -> str:
        """
        Create CTP-specific LLM prompt for trade execution analysis.
        
        Args:
            cluster_data: Cluster data for analysis
            
        Returns:
            CTP-specific analysis prompt
        """
        try:
            # Prepare context for the trade outcome braiding prompt
            strand_summary = self._format_trade_outcome_strands(cluster_data)
            context = {
                'strand_summary': strand_summary
            }
            
            # Use centralized prompt for trade outcome analysis
            return self.prompt_manager.format_prompt('trade_outcome_braiding', context)
            
        except Exception as e:
            self.logger.error(f"Error creating CTP analysis prompt: {e}")
            return "Error creating analysis prompt"
    
    def _format_trade_outcome_strands(self, cluster_data: Dict[str, Any]) -> str:
        """
        Format trade outcome strands for the braiding prompt.
        
        Args:
            cluster_data: Cluster data containing trade outcomes
            
        Returns:
            Formatted strand summary string
        """
        try:
            summary_parts = []
            
            # Add cluster metadata
            summary_parts.append(f"CLUSTER: {cluster_data['cluster_key']}")
            summary_parts.append(f"SUCCESS RATE: {cluster_data['success_rate']:.2%}")
            summary_parts.append(f"AVG RETURN: {cluster_data['avg_return']:.2%}")
            summary_parts.append(f"AVG DURATION: {cluster_data['avg_duration']:.1f} hours")
            summary_parts.append("")
            
            # Add individual trade outcomes
            summary_parts.append("TRADE OUTCOMES:")
            for i, outcome in enumerate(cluster_data['trade_outcomes'], 1):
                summary_parts.append(f"\nTrade {i}:")
                summary_parts.append(f"  - Pattern: {outcome.get('pattern_type', 'Unknown')}")
                summary_parts.append(f"  - Entry: {outcome.get('entry_price', 'N/A')}")
                summary_parts.append(f"  - Exit: {outcome.get('exit_price', 'N/A')}")
                summary_parts.append(f"  - Return: {outcome.get('return_pct', 0):.2%}")
                summary_parts.append(f"  - Duration: {outcome.get('duration_hours', 0):.1f}h")
                summary_parts.append(f"  - Leverage: {outcome.get('leverage', 1)}x")
                summary_parts.append(f"  - Success: {outcome.get('success', False)}")
                
                # Add conditional logic details if available
                if 'conditional_logic' in outcome:
                    summary_parts.append(f"  - Conditional Logic: {outcome['conditional_logic']}")
                if 'reference_point' in outcome:
                    summary_parts.append(f"  - Reference Point: {outcome['reference_point']}")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            self.logger.error(f"Error formatting trade outcome strands: {e}")
            return "Error formatting trade outcome data"
    
    def format_trade_outcome_details(self, trade_outcomes: List[Dict[str, Any]]) -> str:
        """
        Format trade outcome details for LLM analysis.
        
        Args:
            trade_outcomes: List of trade outcome data
            
        Returns:
            Formatted string for LLM prompt
        """
        try:
            if not trade_outcomes:
                return "No trade outcome data available"
            
            formatted = []
            for i, trade in enumerate(trade_outcomes[:10]):  # Limit to 10 examples
                content = trade.get('content', {})
                module_intelligence = trade.get('module_intelligence', {})
                
                # Helper function to get value
                def get_value(key: str, default='N/A'):
                    if content.get(key) is not None:
                        return content.get(key, default)
                    return module_intelligence.get(key, default)
                
                formatted.append(
                    f"  {i+1}. Success: {get_value('success')}, "
                    f"Return: {get_value('return_pct')}%, "
                    f"Entry: {get_value('entry_price')}, "
                    f"Exit: {get_value('exit_price')}, "
                    f"Duration: {get_value('duration_hours')}h, "
                    f"Method: {get_value('execution_method')}"
                )
            
            return "\n".join(formatted)
            
        except Exception as e:
            self.logger.error(f"Error formatting trade outcome details: {e}")
            return "Error formatting trade outcome data"
    
    async def analyze_trade_outcome_cluster(self, cluster_type: str, cluster_key: str, trade_outcomes: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Analyze a cluster of trade outcomes and create learning braid.
        
        Args:
            cluster_type: Type of cluster (asset, timeframe, outcome, etc.)
            cluster_key: Specific cluster key value
            trade_outcomes: List of trade outcome strands in this cluster
            
        Returns:
            Learning braid data, or None if failed
        """
        try:
            self.logger.info(f"Analyzing trade outcome cluster: {cluster_type}:{cluster_key} with {len(trade_outcomes)} outcomes")
            
            # Prepare cluster data for analysis
            cluster_data = self._prepare_trade_outcome_cluster_data(cluster_type, cluster_key, trade_outcomes)
            
            # Create CTP-specific analysis prompt
            prompt = self.create_cluster_analysis_prompt(cluster_data)
            
            # Call LLM for analysis
            llm_response = await self.llm_client.generate_completion(prompt, max_tokens=1000, temperature=0.7)
            
            # Parse learning insights
            learning_insights = self._parse_trade_outcome_insights(llm_response)
            
            # Create learning braid
            braid_data = await self._create_trade_outcome_learning_braid(
                cluster_type, cluster_key, trade_outcomes, learning_insights, llm_response
            )
            
            return braid_data
            
        except Exception as e:
            self.logger.error(f"Error analyzing trade outcome cluster {cluster_type}:{cluster_key}: {e}")
            return None
    
    def _prepare_trade_outcome_cluster_data(self, cluster_type: str, cluster_key: str, trade_outcomes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare cluster data for trade outcome analysis."""
        try:
            # Calculate cluster metrics
            total_outcomes = len(trade_outcomes)
            success_count = sum(1 for trade in trade_outcomes 
                              if trade.get('content', {}).get('success', False))
            success_rate = success_count / total_outcomes if total_outcomes > 0 else 0
            
            # Calculate average metrics
            returns = [trade.get('content', {}).get('return_pct', 0) for trade in trade_outcomes]
            durations = [trade.get('content', {}).get('duration_hours', 0) for trade in trade_outcomes]
            
            avg_return = sum(returns) / len(returns) if returns else 0
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return {
                "cluster_type": cluster_type,
                "cluster_key": cluster_key,
                "total_outcomes": total_outcomes,
                "success_count": success_count,
                "success_rate": success_rate,
                "avg_return": avg_return,
                "avg_duration": avg_duration,
                "trade_outcomes": trade_outcomes
            }
            
        except Exception as e:
            self.logger.error(f"Error preparing trade outcome cluster data: {e}")
            return {}
    
    def _parse_trade_outcome_insights(self, llm_response: str) -> Dict[str, Any]:
        """Parse learning insights from LLM response for trade outcomes."""
        try:
            # For now, store the full response as insights
            # In the future, we could parse specific sections
            return {
                "llm_response": llm_response,
                "insights_type": "trade_execution_analysis",
                "parsed_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing trade outcome insights: {e}")
            return {"error": str(e)}
    
    async def _create_trade_outcome_learning_braid(self, cluster_type: str, cluster_key: str, 
                                                 trade_outcomes: List[Dict[str, Any]], 
                                                 learning_insights: Dict[str, Any], 
                                                 llm_response: str) -> Optional[Dict[str, Any]]:
        """Create a learning braid from trade outcome cluster analysis."""
        try:
            # Generate unique braid ID
            braid_id = f"trade_outcome_braid_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            # Create braid data
            braid_data = {
                "id": braid_id,
                "module": "ctp",
                "kind": "trade_outcome",
                "symbol": trade_outcomes[0].get('symbol', 'UNKNOWN') if trade_outcomes else 'UNKNOWN',
                "timeframe": trade_outcomes[0].get('timeframe', '1h') if trade_outcomes else '1h',
                "tags": ['ctp', 'trade_outcome', 'learning_braid', cluster_type],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "braid_level": 2,  # This is a level 2 braid
                "lesson": llm_response,
                "content": {
                    "cluster_type": cluster_type,
                    "cluster_key": cluster_key,
                    "learning_insights": learning_insights,
                    "source_trade_outcomes": [trade['id'] for trade in trade_outcomes],
                    "braid_level": 2,
                    "created_at": datetime.now(timezone.utc).isoformat()
                },
                "module_intelligence": {
                    "braid_type": "trade_outcome_learning",
                    "cluster_analysis": {
                        "cluster_type": cluster_type,
                        "cluster_key": cluster_key,
                        "source_count": len(trade_outcomes)
                    },
                    "learning_insights": learning_insights
                },
                "cluster_key": self._create_braid_cluster_keys(cluster_type, cluster_key)
            }
            
            # Store in database
            result = self.supabase_manager.insert_strand(braid_data)
            
            if result:
                self.logger.info(f"Created trade outcome learning braid: {braid_id}")
                return braid_data
            else:
                self.logger.error(f"Failed to store trade outcome learning braid: {braid_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating trade outcome learning braid: {e}")
            return None
    
    def _create_braid_cluster_keys(self, cluster_type: str, cluster_key: str) -> List[Dict[str, Any]]:
        """Create cluster keys for a trade outcome braid."""
        try:
            return [{
                "cluster_type": cluster_type,
                "cluster_key": cluster_key,
                "braid_level": 2,
                "consumed": False
            }]
        except Exception as e:
            self.logger.error(f"Error creating braid cluster keys: {e}")
            return []
