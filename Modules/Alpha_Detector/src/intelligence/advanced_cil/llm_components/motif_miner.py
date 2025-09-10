"""
Motif Miner - LLM-first pattern naming and invariant extraction
Part of the Central Intelligence Layer Advanced LLM Components

This component reads clustered strands/braids and names recurring structures ("motifs"),
extracts their invariants (what must be present), fragilities (what breaks them), 
and contexts (regime/session/asset). It outputs Motif Cards.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.llm_integration.prompt_manager import PromptManager


@dataclass
class MotifCard:
    """Represents a discovered motif pattern"""
    motif_id: str
    motif_name: str
    motif_family: str
    invariants: List[str]
    fails_when: List[str]
    contexts: Dict[str, List[str]]
    evidence_refs: List[str]
    why_map: Dict[str, Any]
    lineage: Dict[str, Any]
    confidence_score: float
    created_at: datetime


class MotifMiner:
    """
    LLM-first component that reads clustered strands/braids and names recurring structures.
    
    Key Features:
    - Reads clustered strands from AD_strands table
    - Uses LLM to name patterns and extract invariants
    - Identifies failure conditions and contexts
    - Creates Motif Cards with full metadata
    - Publishes motifs back to AD_strands as specialized strands
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        
        # Configuration
        self.min_cluster_size = 3  # Minimum strands in cluster to consider for motif
        self.confidence_threshold = 0.7  # Minimum confidence for motif creation
        self.max_motifs_per_analysis = 10  # Limit motifs per analysis cycle
        
    async def mine_motifs_from_clusters(self) -> List[MotifCard]:
        """
        Main entry point: mine motifs from clustered strands/braids
        
        Returns:
            List of discovered MotifCard objects
        """
        try:
            # Get clustered strands that could be motifs
            clusters = await self._get_clustered_strands()
            
            if not clusters:
                return []
            
            # Analyze each cluster for motif potential
            motifs = []
            for cluster in clusters[:self.max_motifs_per_analysis]:
                motif = await self._analyze_cluster_for_motif(cluster)
                if motif and motif.confidence_score >= self.confidence_threshold:
                    motifs.append(motif)
            
            # Publish motifs to database
            for motif in motifs:
                await self._publish_motif_to_database(motif)
            
            return motifs
            
        except Exception as e:
            print(f"Error in motif mining: {e}")
            return []
    
    async def _get_clustered_strands(self) -> List[Dict[str, Any]]:
        """
        Get strands that are part of clusters and could represent motifs
        
        Returns:
            List of cluster data with strands
        """
        try:
            # Query for strands that are part of braids (clustered)
            query = """
            SELECT 
                s.*,
                s.clustering_columns,
                s.lesson,
                s.braid_level,
                s.accumulated_score
            FROM AD_strands s
            WHERE s.braid_level > 1  -- Only clustered strands
                AND s.kind IN ('signal', 'intelligence', 'braid')
                AND s.created_at >= NOW() - INTERVAL '7 days'
                AND s.accumulated_score IS NOT NULL
            ORDER BY s.braid_level DESC, s.accumulated_score DESC
            LIMIT 100
            """
            
            result = await self.supabase_manager.execute_query(query)
            
            # Group by braid_level to form clusters
            clusters = {}
            for strand in result:
                braid_level = strand.get('braid_level', 1)
                if braid_level not in clusters:
                    clusters[braid_level] = []
                clusters[braid_level].append(strand)
            
            # Filter clusters by size
            valid_clusters = []
            for braid_level, strands in clusters.items():
                if len(strands) >= self.min_cluster_size:
                    valid_clusters.append({
                        'braid_level': braid_level,
                        'strands': strands,
                        'cluster_size': len(strands)
                    })
            
            return valid_clusters
            
        except Exception as e:
            print(f"Error getting clustered strands: {e}")
            return []
    
    async def _analyze_cluster_for_motif(self, cluster: Dict[str, Any]) -> Optional[MotifCard]:
        """
        Use LLM to analyze a cluster and extract motif information
        
        Args:
            cluster: Cluster data with strands
            
        Returns:
            MotifCard if pattern is identified, None otherwise
        """
        try:
            # Prepare cluster data for LLM analysis
            cluster_summary = self._prepare_cluster_summary(cluster)
            
            # Get LLM prompt for motif analysis
            prompt = await self.prompt_manager.get_prompt(
                'motif_miner',
                'analyze_cluster_for_motif',
                {
                    'cluster_summary': cluster_summary,
                    'cluster_size': cluster['cluster_size'],
                    'braid_level': cluster['braid_level']
                }
            )
            
            # Get LLM analysis
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.3
            )
            
            # Parse LLM response
            motif_data = self._parse_motif_response(response, cluster)
            
            if motif_data:
                return MotifCard(**motif_data)
            else:
                # Check if this was due to uncertainty and publish uncertainty strand
                try:
                    if '{' in response and '}' in response:
                        start = response.find('{')
                        end = response.rfind('}') + 1
                        json_str = response[start:end]
                        parsed_response = json.loads(json_str)
                        uncertainty_flags = parsed_response.get('uncertainty_flags', {})
                        if uncertainty_flags:
                            await self._publish_uncertainty_strand(cluster, uncertainty_flags, parsed_response)
                except Exception as e:
                    print(f"Error handling uncertainty response: {e}")
            
            return None
            
        except Exception as e:
            print(f"Error analyzing cluster for motif: {e}")
            return None
    
    def _prepare_cluster_summary(self, cluster: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare cluster data for LLM analysis
        
        Args:
            cluster: Cluster data with strands
            
        Returns:
            Formatted cluster summary
        """
        strands = cluster['strands']
        
        # Extract key information from strands
        symbols = list(set(s.get('symbol') for s in strands if s.get('symbol')))
        timeframes = list(set(s.get('timeframe') for s in strands if s.get('timeframe')))
        regimes = list(set(s.get('regime') for s in strands if s.get('regime')))
        session_buckets = list(set(s.get('session_bucket') for s in strands if s.get('session_bucket')))
        
        # Extract signal characteristics
        sig_sigmas = [s.get('sig_sigma') for s in strands if s.get('sig_sigma')]
        sig_confidences = [s.get('sig_confidence') for s in strands if s.get('sig_confidence')]
        sig_directions = list(set(s.get('sig_direction') for s in strands if s.get('sig_direction')))
        
        # Extract lessons and patterns
        lessons = [s.get('lesson') for s in strands if s.get('lesson')]
        clustering_columns = [s.get('clustering_columns') for s in strands if s.get('clustering_columns')]
        
        # Calculate performance metrics
        avg_sigma = sum(sig_sigmas) / len(sig_sigmas) if sig_sigmas else 0
        avg_confidence = sum(sig_confidences) / len(sig_confidences) if sig_confidences else 0
        avg_score = sum(s.get('accumulated_score', 0) for s in strands) / len(strands)
        
        return {
            'cluster_size': len(strands),
            'braid_level': cluster['braid_level'],
            'symbols': symbols,
            'timeframes': timeframes,
            'regimes': regimes,
            'session_buckets': session_buckets,
            'sig_directions': sig_directions,
            'avg_sigma': avg_sigma,
            'avg_confidence': avg_confidence,
            'avg_score': avg_score,
            'lessons': lessons[:5],  # Limit to first 5 lessons
            'clustering_columns': clustering_columns[:3],  # Limit to first 3
            'strand_ids': [s.get('id') for s in strands[:10]]  # Limit to first 10 IDs
        }
    
    def _parse_motif_response(self, response: str, cluster: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse LLM response to extract motif information
        
        Args:
            response: LLM response text
            cluster: Original cluster data
            
        Returns:
            Parsed motif data or None
        """
        try:
            # Try to extract JSON from response
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                
                motif_data = json.loads(json_str)
                
                # Validate required fields
                required_fields = ['motif_name', 'motif_family', 'invariants', 'fails_when']
                if all(field in motif_data for field in required_fields):
                    # Check for uncertainty flags - if too uncertain, publish uncertainty strand instead of motif
                    uncertainty_flags = motif_data.get('uncertainty_flags', {})
                    if (uncertainty_flags.get('pattern_clarity') == 'low' or 
                        uncertainty_flags.get('data_sufficiency') == 'insufficient' or
                        motif_data.get('confidence_score', 0) < 0.4):
                        print(f"Motif analysis too uncertain, publishing uncertainty strand: {uncertainty_flags}")
                        # Note: Uncertainty strand publishing will be handled by the calling async function
                        return None
                    
                    # Add metadata
                    motif_data['motif_id'] = f"motif_{cluster['braid_level']}_{int(datetime.now().timestamp())}"
                    motif_data['evidence_refs'] = [s.get('id') for s in cluster['strands'][:10]]
                    motif_data['confidence_score'] = motif_data.get('confidence_score', 0.8)
                    motif_data['created_at'] = datetime.now(timezone.utc)
                    
                    # Ensure contexts is a dict
                    if 'contexts' not in motif_data:
                        motif_data['contexts'] = {
                            'regimes': cluster['strands'][0].get('regime', 'unknown'),
                            'sessions': cluster['strands'][0].get('session_bucket', 'unknown'),
                            'timeframes': cluster['strands'][0].get('timeframe', 'unknown')
                        }
                    
                    # Ensure why_map is a dict
                    if 'why_map' not in motif_data:
                        motif_data['why_map'] = {
                            'mechanism_hypothesis': 'Pattern discovered through cluster analysis',
                            'supports': motif_data.get('invariants', []),
                            'fails_when': motif_data.get('fails_when', [])
                        }
                    
                    # Ensure lineage is a dict
                    if 'lineage' not in motif_data:
                        motif_data['lineage'] = {
                            'parents': [],
                            'mutation_note': f'Discovered from braid level {cluster["braid_level"]} cluster'
                        }
                    
                    return motif_data
            
            return None
            
        except Exception as e:
            print(f"Error parsing motif response: {e}")
            return None
    
    async def _publish_motif_to_database(self, motif: MotifCard) -> bool:
        """
        Publish motif as a specialized strand to AD_strands table
        
        Args:
            motif: MotifCard to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create strand data for motif
            strand_data = {
                'id': motif.motif_id,
                'module': 'alpha',
                'kind': 'motif',
                'symbol': 'MULTI',  # Multi-symbol motif
                'timeframe': 'MULTI',  # Multi-timeframe motif
                'session_bucket': 'MULTI',  # Multi-session motif
                'regime': 'MULTI',  # Multi-regime motif
                'tags': ['agent:central_intelligence:motif_miner:motif_discovered'],
                'created_at': motif.created_at.isoformat(),
                'updated_at': motif.created_at.isoformat(),
                
                # Motif-specific fields
                'motif_name': motif.motif_name,
                'motif_family': motif.motif_family,
                'invariants': motif.invariants,
                'fails_when': motif.fails_when,
                'contexts': motif.contexts,
                'evidence_refs': motif.evidence_refs,
                'why_map': motif.why_map,
                'lineage': motif.lineage,
                
                # CIL fields
                'team_member': 'motif_miner',
                'strategic_meta_type': 'motif_discovery',
                'doctrine_status': 'provisional',
                
                # Scoring
                'sig_sigma': motif.confidence_score,
                'sig_confidence': motif.confidence_score,
                'accumulated_score': motif.confidence_score,
                
                # Resonance fields (initialized)
                'phi': 0.5,  # Initial resonance
                'rho': 1.0,  # Initial density
                'telemetry': {
                    'sr': 0.0,  # Success rate (to be updated)
                    'cr': 0.0,  # Confirmation rate (to be updated)
                    'xr': 0.0,  # Contradiction rate (to be updated)
                    'surprise': 0.8  # High surprise for new motifs
                },
                'phi_updated_at': motif.created_at.isoformat(),
                'rho_updated_at': motif.created_at.isoformat()
            }
            
            # Insert into database
            result = await self.supabase_manager.insert_strand(strand_data)
            
            if result:
                print(f"Published motif: {motif.motif_name} (ID: {motif.motif_id})")
                return True
            else:
                print(f"Failed to publish motif: {motif.motif_name}")
                return False
                
        except Exception as e:
            print(f"Error publishing motif to database: {e}")
            return False
    
    async def get_motif_by_id(self, motif_id: str) -> Optional[MotifCard]:
        """
        Retrieve a motif by ID from the database
        
        Args:
            motif_id: Motif ID to retrieve
            
        Returns:
            MotifCard if found, None otherwise
        """
        try:
            query = """
            SELECT * FROM AD_strands 
            WHERE id = %s AND kind = 'motif'
            """
            
            result = await self.supabase_manager.execute_query(query, [motif_id])
            
            if result:
                strand = result[0]
                return MotifCard(
                    motif_id=strand['id'],
                    motif_name=strand['motif_name'],
                    motif_family=strand['motif_family'],
                    invariants=strand['invariants'],
                    fails_when=strand['fails_when'],
                    contexts=strand['contexts'],
                    evidence_refs=strand['evidence_refs'],
                    why_map=strand['why_map'],
                    lineage=strand['lineage'],
                    confidence_score=strand['sig_sigma'],
                    created_at=strand['created_at']
                )
            
            return None
            
        except Exception as e:
            print(f"Error retrieving motif: {e}")
            return None
    
    async def find_similar_motifs(self, motif_family: str, limit: int = 5) -> List[MotifCard]:
        """
        Find similar motifs by family
        
        Args:
            motif_family: Family to search for
            limit: Maximum number of motifs to return
            
        Returns:
            List of similar MotifCard objects
        """
        try:
            query = """
            SELECT * FROM AD_strands 
            WHERE kind = 'motif' 
                AND motif_family = %s
            ORDER BY sig_sigma DESC, created_at DESC
            LIMIT %s
            """
            
            result = await self.supabase_manager.execute_query(query, [motif_family, limit])
            
            motifs = []
            for strand in result:
                motif = MotifCard(
                    motif_id=strand['id'],
                    motif_name=strand['motif_name'],
                    motif_family=strand['motif_family'],
                    invariants=strand['invariants'],
                    fails_when=strand['fails_when'],
                    contexts=strand['contexts'],
                    evidence_refs=strand['evidence_refs'],
                    why_map=strand['why_map'],
                    lineage=strand['lineage'],
                    confidence_score=strand['sig_sigma'],
                    created_at=strand['created_at']
                )
                motifs.append(motif)
            
            return motifs
            
        except Exception as e:
            print(f"Error finding similar motifs: {e}")
            return []
    
    async def update_motif_confidence(self, motif_id: str, new_confidence: float) -> bool:
        """
        Update motif confidence score based on performance
        
        Args:
            motif_id: Motif ID to update
            new_confidence: New confidence score
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = {
                'sig_sigma': new_confidence,
                'sig_confidence': new_confidence,
                'accumulated_score': new_confidence,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = await self.supabase_manager.update_strand(motif_id, update_data)
            return result is not None
            
        except Exception as e:
            print(f"Error updating motif confidence: {e}")
            return False
    
    async def _publish_uncertainty_strand(self, cluster: Dict[str, Any], uncertainty_flags: Dict[str, Any], motif_data: Dict[str, Any]) -> bool:
        """
        Publish uncertainty as a specialized strand for review and resolution
        
        Args:
            cluster: Original cluster data
            uncertainty_flags: Uncertainty assessment flags
            motif_data: Partial motif data (if any)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Determine uncertainty type and priority
            uncertainty_type = self._determine_uncertainty_type(uncertainty_flags)
            priority = self._determine_uncertainty_priority(uncertainty_flags)
            
            # Create uncertainty strand data
            strand_data = {
                'id': f"uncertainty_{cluster['braid_level']}_{int(datetime.now().timestamp())}",
                'module': 'alpha',
                'kind': 'uncertainty',
                'symbol': 'MULTI',
                'timeframe': 'MULTI',
                'session_bucket': 'MULTI',
                'regime': 'MULTI',
                'tags': ['agent:central_intelligence:motif_miner:uncertainty_detected'],
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                
                # Uncertainty-specific data in module_intelligence
                'module_intelligence': {
                    'uncertainty_type': uncertainty_type,
                    'uncertainty_flags': uncertainty_flags,
                    'cluster_data': {
                        'braid_level': cluster['braid_level'],
                        'cluster_size': cluster['cluster_size'],
                        'strand_ids': [s.get('id') for s in cluster['strands'][:10]]
                    },
                    'partial_motif_data': motif_data,
                    'resolution_priority': priority,
                    'resolution_actions': self._get_resolution_actions(uncertainty_type)
                },
                
                # CIL fields
                'team_member': 'motif_miner',
                'strategic_meta_type': 'uncertainty_detection',
                'doctrine_status': 'needs_resolution',
                
                # Scoring (uncertainty gets negative score to indicate needs attention)
                'sig_sigma': -priority,  # Negative score indicates uncertainty
                'sig_confidence': priority,
                'accumulated_score': -priority
            }
            
            result = await self.supabase_manager.insert_strand(strand_data)
            return result is not None
            
        except Exception as e:
            print(f"Error publishing uncertainty strand: {e}")
            return False
    
    def _determine_uncertainty_type(self, uncertainty_flags: Dict[str, Any]) -> str:
        """Determine the primary uncertainty type from flags"""
        if uncertainty_flags.get('pattern_clarity') == 'low':
            return 'pattern_clarity'
        elif uncertainty_flags.get('data_sufficiency') == 'insufficient':
            return 'data_sufficiency'
        elif uncertainty_flags.get('invariant_confidence') == 'low':
            return 'pattern_clarity'
        elif uncertainty_flags.get('context_confidence') == 'low':
            return 'data_sufficiency'
        else:
            return 'pattern_clarity'  # Default
    
    def _determine_uncertainty_priority(self, uncertainty_flags: Dict[str, Any]) -> float:
        """Determine uncertainty priority based on flags"""
        priority = 0.5  # Default medium priority
        
        # Increase priority for multiple uncertainty flags
        uncertainty_count = sum(1 for flag in uncertainty_flags.values() if flag in ['low', 'insufficient'])
        priority += uncertainty_count * 0.1
        
        # Increase priority for specific high-impact uncertainties
        if uncertainty_flags.get('pattern_clarity') == 'low':
            priority += 0.2
        if uncertainty_flags.get('data_sufficiency') == 'insufficient':
            priority += 0.3
        
        return min(priority, 1.0)  # Cap at 1.0
    
    def _get_resolution_actions(self, uncertainty_type: str) -> List[str]:
        """Get appropriate resolution actions for uncertainty type"""
        action_mapping = {
            'pattern_clarity': ['data_collection', 'experiment_design', 'human_review', 'pattern_validation'],
            'data_sufficiency': ['data_collection', 'sample_expansion', 'context_broadening', 'data_validation'],
            'causal_clarity': ['causal_analysis', 'counterfactual_testing', 'mechanism_research'],
            'analogy_confidence': ['analogy_validation', 'transfer_testing', 'cross_context_analysis'],
            'transfer_feasibility': ['transfer_validation', 'context_mapping', 'transformation_testing']
        }
        return action_mapping.get(uncertainty_type, ['data_collection', 'human_review'])
