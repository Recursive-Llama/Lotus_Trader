"""
Learning Pipeline

Unified learning pipeline that processes strands through the complete learning workflow.
Handles strand type detection, clustering, learning analysis, and braid creation.
"""

import asyncio
from typing import Dict, Any, List, Optional
from strand_processor import StrandProcessor, LearningConfig, StrandType
from .multi_cluster_grouping_engine import MultiClusterGroupingEngine
from .per_cluster_learning_system import PerClusterLearningSystem
from .llm_learning_analyzer import LLMLearningAnalyzer
from .braid_level_manager import BraidLevelManager
from mathematical_resonance_engine import MathematicalResonanceEngine


class LearningPipeline:
    """Unified learning pipeline for processing any strand type"""
    
    def __init__(
        self,
        supabase_manager,
        llm_client,
        prompt_manager
    ):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        
        # Initialize components
        self.strand_processor = StrandProcessor()
        self.clustering_engine = MultiClusterGroupingEngine(supabase_manager)
        self.learning_system = PerClusterLearningSystem(
            supabase_manager, llm_client
        )
        self.llm_analyzer = LLMLearningAnalyzer(llm_client, prompt_manager)
        self.braid_manager = BraidLevelManager(supabase_manager)
        self.resonance_engine = MathematicalResonanceEngine()
    
    async def process_strand(self, strand: Dict[str, Any]) -> bool:
        """
        Process a single strand through the learning pipeline
        
        Args:
            strand: Strand data from database
            
        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            # Step 1: Identify strand type and get learning configuration
            learning_config = self.strand_processor.process_strand(strand)
            if not learning_config:
                print(f"Learning not supported for strand type: {strand.get('kind')}")
                return False
            
            print(f"Processing {learning_config.strand_type.value} strand: {strand.get('id')}")
            
            # Step 2: Get clusters for this strand type
            clusters = await self._get_strand_clusters(strand, learning_config)
            if not clusters:
                print(f"No clusters found for strand: {strand.get('id')}")
                return False
            
            # Step 3: Process each cluster through learning
            success_count = 0
            for cluster_type, cluster_data in clusters.items():
                if len(cluster_data) >= learning_config.min_cluster_size:
                    success = await self._process_cluster(
                        cluster_data, cluster_type, learning_config
                    )
                    if success:
                        success_count += 1
            
            print(f"Successfully processed {success_count}/{len(clusters)} clusters")
            return success_count > 0
            
        except Exception as e:
            print(f"Error processing strand {strand.get('id')}: {e}")
            return False
    
    async def _get_strand_clusters(
        self, 
        strand: Dict[str, Any], 
        learning_config: LearningConfig
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get clusters for a strand based on its learning configuration
        
        Args:
            strand: The strand to cluster
            learning_config: Learning configuration for this strand type
            
        Returns:
            Dictionary of cluster_type -> list of strands
        """
        clusters = {}
        
        for cluster_type in learning_config.cluster_types:
            try:
                cluster_strands = await self.clustering_engine.get_cluster_strands(
                    strand_type=learning_config.strand_type.value,
                    cluster_type=cluster_type,
                    strand_id=strand.get('id')
                )
                
                if cluster_strands and len(cluster_strands) >= learning_config.min_cluster_size:
                    clusters[cluster_type] = cluster_strands
                    
            except Exception as e:
                print(f"Error getting {cluster_type} cluster: {e}")
                continue
        
        return clusters
    
    async def _process_cluster(
        self,
        cluster_data: List[Dict[str, Any]],
        cluster_type: str,
        learning_config: LearningConfig
    ) -> bool:
        """
        Process a cluster through the learning system
        
        Args:
            cluster_data: List of strands in the cluster
            cluster_type: Type of cluster
            learning_config: Learning configuration
            
        Returns:
            True if processing succeeded, False otherwise
        """
        try:
            # Step 1: Check if cluster already has a braid
            existing_braid = await self._check_existing_braid(cluster_data, cluster_type)
            if existing_braid:
                print(f"Braid already exists for {cluster_type} cluster")
                return True
            
            # Step 2: Generate learning insights using LLM
            learning_insights = await self.llm_analyzer.analyze_cluster(
                cluster_data=cluster_data,
                cluster_type=cluster_type,
                strand_type=learning_config.strand_type.value,
                prompt_template=learning_config.prompt_template
            )
            
            if not learning_insights:
                print(f"Failed to generate learning insights for {cluster_type} cluster")
                return False
            
            # Step 3: Create braid using braid level manager
            braid_created = await self.braid_manager.create_braid(
                cluster_data=cluster_data,
                cluster_type=cluster_type,
                strand_type=learning_config.strand_type.value,
                learning_insights=learning_insights,
                braid_level=2  # Start at level 2 for new braids
            )
            
            if braid_created:
                print(f"Successfully created braid for {cluster_type} cluster")
                return True
            else:
                print(f"Failed to create braid for {cluster_type} cluster")
                return False
                
        except Exception as e:
            print(f"Error processing {cluster_type} cluster: {e}")
            return False
    
    async def _check_existing_braid(
        self, 
        cluster_data: List[Dict[str, Any]], 
        cluster_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a braid already exists for this cluster
        
        Args:
            cluster_data: List of strands in the cluster
            cluster_type: Type of cluster
            
        Returns:
            Existing braid if found, None otherwise
        """
        try:
            # Get the first strand to determine strand type
            if not cluster_data:
                return None
            
            strand_type = cluster_data[0].get('kind')
            if not strand_type:
                return None
            
            # Query for existing braids of this type and cluster
            result = await self.supabase_manager.client.table('AD_strands').select('*').eq(
                'kind', strand_type
            ).eq('braid_level', 2).eq(
                'content->>cluster_type', cluster_type
            ).execute()
            
            if result.data:
                return result.data[0]
            
            return None
            
        except Exception as e:
            print(f"Error checking existing braid: {e}")
            return None
    
    async def process_learning_queue(self, limit: int = 10) -> Dict[str, int]:
        """
        Process strands from the learning queue
        
        Args:
            limit: Maximum number of strands to process
            
        Returns:
            Dictionary with processing statistics
        """
        try:
            # Get pending strands from learning queue
            result = await self.supabase_manager.client.table('learning_queue').select(
                '*'
            ).eq('status', 'pending').limit(limit).execute()
            
            if not result.data:
                return {'processed': 0, 'successful': 0, 'failed': 0}
            
            # Process each strand
            successful = 0
            failed = 0
            
            for queue_item in result.data:
                strand_id = queue_item['strand_id']
                
                # Get the actual strand data
                strand_result = await self.supabase_manager.client.table('AD_strands').select(
                    '*'
                ).eq('id', strand_id).execute()
                
                if not strand_result.data:
                    print(f"Strand not found: {strand_id}")
                    failed += 1
                    continue
                
                strand = strand_result.data[0]
                
                # Process the strand
                success = await self.process_strand(strand)
                
                if success:
                    successful += 1
                    # Update queue status
                    await self.supabase_manager.client.table('learning_queue').update({
                        'status': 'completed',
                        'processed_at': 'now()'
                    }).eq('id', queue_item['id']).execute()
                else:
                    failed += 1
                    # Update queue status
                    await self.supabase_manager.client.table('learning_queue').update({
                        'status': 'failed',
                        'processed_at': 'now()'
                    }).eq('id', queue_item['id']).execute()
            
            return {
                'processed': len(result.data),
                'successful': successful,
                'failed': failed
            }
            
        except Exception as e:
            print(f"Error processing learning queue: {e}")
            return {'processed': 0, 'successful': 0, 'failed': 0}
    
    async def get_context_for_strand_type(self, strand_type: str, 
                                         context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get context for a specific strand type
        
        Args:
            strand_type: The strand type to get context for
            context_data: Additional context data
            
        Returns:
            Context data for the strand type
        """
        try:
            # Get learning configuration
            learning_config = self.strand_processor.get_learning_config(
                StrandType(strand_type)
            )
            
            if not learning_config:
                return {}
            
            # Get recent braids for this strand type
            braids = await self._get_recent_braids(strand_type, limit=10)
            
            # Get pattern data if available
            pattern_data = context_data.get('pattern_data', {})
            
            # Build context
            context = {
                'strand_type': strand_type,
                'learning_focus': learning_config.learning_focus,
                'recent_braids': braids,
                'pattern_data': pattern_data,
                'cluster_types': learning_config.cluster_types
            }
            
            return context
            
        except Exception as e:
            print(f"Error getting context for {strand_type}: {e}")
            return {}
    
    async def _get_recent_braids(self, strand_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent braids for a strand type
        
        Args:
            strand_type: The strand type
            limit: Maximum number of braids to return
            
        Returns:
            List of recent braids
        """
        try:
            result = await self.supabase_manager.client.table('AD_strands').select(
                '*'
            ).eq('kind', strand_type).gte('braid_level', 2).order(
                'created_at', desc=True
            ).limit(limit).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error getting recent braids: {e}")
            return []
