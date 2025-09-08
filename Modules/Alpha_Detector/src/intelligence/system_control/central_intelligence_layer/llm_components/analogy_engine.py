"""
Analogy Engine - LLM cross-family rhyme detection
Part of the Central Intelligence Layer Advanced LLM Components

This component scans the Pattern Atlas to find rhymes across families and contexts
(e.g., "this ETH Asian-session motif rhymes with SOL EU-open under high vol") 
and proposes transfer hypotheses with the needed transformations (scale, lag, volatility normalization).
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.llm_integration.prompt_manager import PromptManager


@dataclass
class TransferCandidate:
    """Represents a potential transfer between motifs"""
    transfer_id: str
    source_motif_id: str
    target_context: Dict[str, Any]
    transformation_mapping: Dict[str, Any]
    confidence_score: float
    transfer_hypothesis: str
    expected_conditions: Dict[str, Any]
    created_at: datetime


@dataclass
class AnalogyPair:
    """Represents an analogy between two motifs"""
    analogy_id: str
    motif_a_id: str
    motif_b_id: str
    similarity_score: float
    transformation_functions: Dict[str, Any]
    rhyme_quality: str  # 'high', 'medium', 'low'
    context_differences: Dict[str, Any]
    created_at: datetime


class AnalogyEngine:
    """
    LLM-first component that finds rhymes across motif families and contexts.
    
    Key Features:
    - Scans Pattern Atlas for cross-family similarities
    - Identifies transformation functions needed for transfers
    - Proposes transfer hypotheses with explicit mappings
    - Creates analogy pairs for further analysis
    - Generates transfer candidates for experiment orchestration
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        
        # Configuration
        self.min_similarity_threshold = 0.6  # Minimum similarity for analogy consideration
        self.max_analogies_per_analysis = 20  # Limit analogies per analysis cycle
        self.transfer_confidence_threshold = 0.7  # Minimum confidence for transfer proposals
        
    async def find_analogies_and_transfers(self) -> Tuple[List[AnalogyPair], List[TransferCandidate]]:
        """
        Main entry point: find analogies and generate transfer candidates
        
        Returns:
            Tuple of (analogy_pairs, transfer_candidates)
        """
        try:
            # Get motifs from Pattern Atlas
            motifs = await self._get_motifs_for_analysis()
            
            if len(motifs) < 2:
                return [], []
            
            # Find analogies between motifs
            analogies = await self._find_analogies(motifs)
            
            # Generate transfer candidates from analogies
            transfers = await self._generate_transfer_candidates(analogies)
            
            # Publish results to database
            for analogy in analogies:
                await self._publish_analogy_to_database(analogy)
            
            for transfer in transfers:
                await self._publish_transfer_to_database(transfer)
            
            return analogies, transfers
            
        except Exception as e:
            print(f"Error in analogy and transfer analysis: {e}")
            return [], []
    
    async def _get_motifs_for_analysis(self) -> List[Dict[str, Any]]:
        """
        Get motifs from Pattern Atlas for analogy analysis
        
        Returns:
            List of motif data
        """
        try:
            query = """
            SELECT 
                id, motif_name, motif_family, invariants, fails_when, 
                contexts, why_map, sig_sigma, sig_confidence, accumulated_score,
                created_at, updated_at
            FROM AD_strands 
            WHERE kind = 'motif' 
                AND sig_sigma > 0.5  -- Only confident motifs
                AND created_at >= NOW() - INTERVAL '30 days'
            ORDER BY sig_sigma DESC, created_at DESC
            LIMIT 50
            """
            
            result = await self.supabase_manager.execute_query(query)
            return result
            
        except Exception as e:
            print(f"Error getting motifs for analysis: {e}")
            return []
    
    async def _find_analogies(self, motifs: List[Dict[str, Any]]) -> List[AnalogyPair]:
        """
        Find analogies between motifs using LLM analysis
        
        Args:
            motifs: List of motif data
            
        Returns:
            List of AnalogyPair objects
        """
        try:
            analogies = []
            
            # Compare each pair of motifs
            for i in range(len(motifs)):
                for j in range(i + 1, len(motifs)):
                    motif_a = motifs[i]
                    motif_b = motifs[j]
                    
                    # Skip if same family (looking for cross-family analogies)
                    if motif_a['motif_family'] == motif_b['motif_family']:
                        continue
                    
                    # Analyze potential analogy
                    analogy = await self._analyze_motif_analogy(motif_a, motif_b)
                    
                    if analogy and analogy.similarity_score >= self.min_similarity_threshold:
                        analogies.append(analogy)
            
            # Sort by similarity score and limit
            analogies.sort(key=lambda x: x.similarity_score, reverse=True)
            return analogies[:self.max_analogies_per_analysis]
            
        except Exception as e:
            print(f"Error finding analogies: {e}")
            return []
    
    async def _analyze_motif_analogy(self, motif_a: Dict[str, Any], motif_b: Dict[str, Any]) -> Optional[AnalogyPair]:
        """
        Use LLM to analyze potential analogy between two motifs
        
        Args:
            motif_a: First motif data
            motif_b: Second motif data
            
        Returns:
            AnalogyPair if analogy found, None otherwise
        """
        try:
            # Prepare motif comparison data
            comparison_data = self._prepare_motif_comparison(motif_a, motif_b)
            
            # Get LLM prompt for analogy analysis
            prompt = await self.prompt_manager.get_prompt(
                'analogy_engine',
                'analyze_motif_analogy',
                {
                    'motif_a': comparison_data['motif_a'],
                    'motif_b': comparison_data['motif_b'],
                    'comparison_context': comparison_data['context']
                }
            )
            
            # Get LLM analysis
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=1500,
                temperature=0.4
            )
            
            # Parse LLM response
            analogy_data = self._parse_analogy_response(response, motif_a, motif_b)
            
            if analogy_data:
                return AnalogyPair(**analogy_data)
            
            return None
            
        except Exception as e:
            print(f"Error analyzing motif analogy: {e}")
            return None
    
    def _prepare_motif_comparison(self, motif_a: Dict[str, Any], motif_b: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare motif data for LLM comparison
        
        Args:
            motif_a: First motif data
            motif_b: Second motif data
            
        Returns:
            Formatted comparison data
        """
        return {
            'motif_a': {
                'id': motif_a['id'],
                'name': motif_a['motif_name'],
                'family': motif_a['motif_family'],
                'invariants': motif_a['invariants'],
                'fails_when': motif_a['fails_when'],
                'contexts': motif_a['contexts'],
                'why_map': motif_a['why_map'],
                'confidence': motif_a['sig_sigma']
            },
            'motif_b': {
                'id': motif_b['id'],
                'name': motif_b['motif_name'],
                'family': motif_b['motif_family'],
                'invariants': motif_b['invariants'],
                'fails_when': motif_b['fails_when'],
                'contexts': motif_b['contexts'],
                'why_map': motif_b['why_map'],
                'confidence': motif_b['sig_sigma']
            },
            'context': {
                'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
                'min_similarity_threshold': self.min_similarity_threshold
            }
        }
    
    def _parse_analogy_response(self, response: str, motif_a: Dict[str, Any], motif_b: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse LLM response to extract analogy information
        
        Args:
            response: LLM response text
            motif_a: First motif data
            motif_b: Second motif data
            
        Returns:
            Parsed analogy data or None
        """
        try:
            # Try to extract JSON from response
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                
                analogy_data = json.loads(json_str)
                
                # Validate required fields
                required_fields = ['similarity_score', 'transformation_functions', 'rhyme_quality']
                if all(field in analogy_data for field in required_fields):
                    # Check for uncertainty flags - if too uncertain, return None
                    uncertainty_flags = analogy_data.get('uncertainty_flags', {})
                    if (uncertainty_flags.get('analogy_confidence') == 'low' or 
                        analogy_data.get('similarity_score', 0) < 0.3 or
                        analogy_data.get('rhyme_quality') == 'low'):
                        print(f"Analogy analysis too uncertain, skipping: {uncertainty_flags}")
                        return None
                    
                    # Add metadata
                    analogy_data['analogy_id'] = f"analogy_{motif_a['id']}_{motif_b['id']}_{int(datetime.now().timestamp())}"
                    analogy_data['motif_a_id'] = motif_a['id']
                    analogy_data['motif_b_id'] = motif_b['id']
                    analogy_data['created_at'] = datetime.now(timezone.utc)
                    
                    # Ensure context_differences is a dict
                    if 'context_differences' not in analogy_data:
                        analogy_data['context_differences'] = {
                            'family_difference': f"{motif_a['motif_family']} vs {motif_b['motif_family']}",
                            'context_variations': 'To be analyzed'
                        }
                    
                    return analogy_data
            
            return None
            
        except Exception as e:
            print(f"Error parsing analogy response: {e}")
            return None
    
    async def _generate_transfer_candidates(self, analogies: List[AnalogyPair]) -> List[TransferCandidate]:
        """
        Generate transfer candidates from analogies
        
        Args:
            analogies: List of AnalogyPair objects
            
        Returns:
            List of TransferCandidate objects
        """
        try:
            transfers = []
            
            for analogy in analogies:
                # Generate transfer candidate for each analogy
                transfer = await self._create_transfer_candidate(analogy)
                
                if transfer and transfer.confidence_score >= self.transfer_confidence_threshold:
                    transfers.append(transfer)
            
            # Sort by confidence score
            transfers.sort(key=lambda x: x.confidence_score, reverse=True)
            return transfers
            
        except Exception as e:
            print(f"Error generating transfer candidates: {e}")
            return []
    
    async def _create_transfer_candidate(self, analogy: AnalogyPair) -> Optional[TransferCandidate]:
        """
        Create transfer candidate from analogy
        
        Args:
            analogy: AnalogyPair to create transfer from
            
        Returns:
            TransferCandidate if successful, None otherwise
        """
        try:
            # Get source motif data
            source_motif = await self._get_motif_by_id(analogy.motif_a_id)
            if not source_motif:
                return None
            
            # Prepare transfer analysis data
            transfer_data = {
                'source_motif': source_motif,
                'analogy': {
                    'similarity_score': analogy.similarity_score,
                    'transformation_functions': analogy.transformation_functions,
                    'rhyme_quality': analogy.rhyme_quality,
                    'context_differences': analogy.context_differences
                }
            }
            
            # Get LLM prompt for transfer generation
            prompt = await self.prompt_manager.get_prompt(
                'analogy_engine',
                'generate_transfer_candidate',
                transfer_data
            )
            
            # Get LLM analysis
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=1500,
                temperature=0.3
            )
            
            # Parse LLM response
            transfer_info = self._parse_transfer_response(response, analogy)
            
            if transfer_info:
                return TransferCandidate(**transfer_info)
            
            return None
            
        except Exception as e:
            print(f"Error creating transfer candidate: {e}")
            return None
    
    def _parse_transfer_response(self, response: str, analogy: AnalogyPair) -> Optional[Dict[str, Any]]:
        """
        Parse LLM response to extract transfer information
        
        Args:
            response: LLM response text
            analogy: Original AnalogyPair
            
        Returns:
            Parsed transfer data or None
        """
        try:
            # Try to extract JSON from response
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                
                transfer_data = json.loads(json_str)
                
                # Validate required fields
                required_fields = ['target_context', 'transformation_mapping', 'confidence_score', 'transfer_hypothesis']
                if all(field in transfer_data for field in required_fields):
                    # Add metadata
                    transfer_data['transfer_id'] = f"transfer_{analogy.analogy_id}_{int(datetime.now().timestamp())}"
                    transfer_data['source_motif_id'] = analogy.motif_a_id
                    transfer_data['created_at'] = datetime.now(timezone.utc)
                    
                    # Ensure expected_conditions is a dict
                    if 'expected_conditions' not in transfer_data:
                        transfer_data['expected_conditions'] = {
                            'regime': 'To be determined',
                            'session': 'To be determined',
                            'timeframe': 'To be determined'
                        }
                    
                    return transfer_data
            
            return None
            
        except Exception as e:
            print(f"Error parsing transfer response: {e}")
            return None
    
    async def _get_motif_by_id(self, motif_id: str) -> Optional[Dict[str, Any]]:
        """
        Get motif data by ID
        
        Args:
            motif_id: Motif ID to retrieve
            
        Returns:
            Motif data if found, None otherwise
        """
        try:
            query = """
            SELECT * FROM AD_strands 
            WHERE id = %s AND kind = 'motif'
            """
            
            result = await self.supabase_manager.execute_query(query, [motif_id])
            return result[0] if result else None
            
        except Exception as e:
            print(f"Error getting motif by ID: {e}")
            return None
    
    async def _publish_analogy_to_database(self, analogy: AnalogyPair) -> bool:
        """
        Publish analogy to database as specialized strand
        
        Args:
            analogy: AnalogyPair to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            strand_data = {
                'id': analogy.analogy_id,
                'module': 'alpha',
                'kind': 'analogy',
                'symbol': 'MULTI',
                'timeframe': 'MULTI',
                'session_bucket': 'MULTI',
                'regime': 'MULTI',
                'tags': ['agent:central_intelligence:analogy_engine:analogy_discovered'],
                'created_at': analogy.created_at.isoformat(),
                'updated_at': analogy.created_at.isoformat(),
                
                # Analogy-specific data in module_intelligence
                'module_intelligence': {
                    'analogy_type': 'cross_family_rhyme',
                    'motif_a_id': analogy.motif_a_id,
                    'motif_b_id': analogy.motif_b_id,
                    'similarity_score': analogy.similarity_score,
                    'transformation_functions': analogy.transformation_functions,
                    'rhyme_quality': analogy.rhyme_quality,
                    'context_differences': analogy.context_differences
                },
                
                # CIL fields
                'cil_team_member': 'analogy_engine',
                'strategic_meta_type': 'analogy_discovery',
                'doctrine_status': 'provisional',
                
                # Scoring
                'sig_sigma': analogy.similarity_score,
                'sig_confidence': analogy.similarity_score,
                'accumulated_score': analogy.similarity_score
            }
            
            result = await self.supabase_manager.insert_strand(strand_data)
            return result is not None
            
        except Exception as e:
            print(f"Error publishing analogy to database: {e}")
            return False
    
    async def _publish_transfer_to_database(self, transfer: TransferCandidate) -> bool:
        """
        Publish transfer candidate to database as specialized strand
        
        Args:
            transfer: TransferCandidate to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            strand_data = {
                'id': transfer.transfer_id,
                'module': 'alpha',
                'kind': 'transfer_candidate',
                'symbol': 'MULTI',
                'timeframe': 'MULTI',
                'session_bucket': 'MULTI',
                'regime': 'MULTI',
                'tags': ['agent:central_intelligence:analogy_engine:transfer_proposed'],
                'created_at': transfer.created_at.isoformat(),
                'updated_at': transfer.created_at.isoformat(),
                
                # Transfer-specific data in module_intelligence
                'module_intelligence': {
                    'transfer_type': 'cross_context_generalization',
                    'source_motif_id': transfer.source_motif_id,
                    'target_context': transfer.target_context,
                    'transformation_mapping': transfer.transformation_mapping,
                    'transfer_hypothesis': transfer.transfer_hypothesis,
                    'expected_conditions': transfer.expected_conditions
                },
                
                # CIL fields
                'cil_team_member': 'analogy_engine',
                'strategic_meta_type': 'transfer_proposal',
                'doctrine_status': 'provisional',
                
                # Scoring
                'sig_sigma': transfer.confidence_score,
                'sig_confidence': transfer.confidence_score,
                'accumulated_score': transfer.confidence_score
            }
            
            result = await self.supabase_manager.insert_strand(strand_data)
            return result is not None
            
        except Exception as e:
            print(f"Error publishing transfer to database: {e}")
            return False
    
    async def get_analogies_by_family(self, motif_family: str, limit: int = 10) -> List[AnalogyPair]:
        """
        Get analogies involving a specific motif family
        
        Args:
            motif_family: Family to search for
            limit: Maximum number of analogies to return
            
        Returns:
            List of AnalogyPair objects
        """
        try:
            query = """
            SELECT * FROM AD_strands 
            WHERE kind = 'analogy' 
                AND module_intelligence->>'analogy_type' = 'cross_family_rhyme'
                AND (module_intelligence->>'motif_a_id' IN (
                    SELECT id FROM AD_strands WHERE kind = 'motif' AND motif_family = %s
                ) OR module_intelligence->>'motif_b_id' IN (
                    SELECT id FROM AD_strands WHERE kind = 'motif' AND motif_family = %s
                ))
            ORDER BY sig_sigma DESC, created_at DESC
            LIMIT %s
            """
            
            result = await self.supabase_manager.execute_query(query, [motif_family, motif_family, limit])
            
            analogies = []
            for strand in result:
                module_intel = strand['module_intelligence']
                analogy = AnalogyPair(
                    analogy_id=strand['id'],
                    motif_a_id=module_intel['motif_a_id'],
                    motif_b_id=module_intel['motif_b_id'],
                    similarity_score=module_intel['similarity_score'],
                    transformation_functions=module_intel['transformation_functions'],
                    rhyme_quality=module_intel['rhyme_quality'],
                    context_differences=module_intel['context_differences'],
                    created_at=strand['created_at']
                )
                analogies.append(analogy)
            
            return analogies
            
        except Exception as e:
            print(f"Error getting analogies by family: {e}")
            return []
    
    async def get_transfer_candidates(self, limit: int = 10) -> List[TransferCandidate]:
        """
        Get transfer candidates for experiment orchestration
        
        Args:
            limit: Maximum number of transfers to return
            
        Returns:
            List of TransferCandidate objects
        """
        try:
            query = """
            SELECT * FROM AD_strands 
            WHERE kind = 'transfer_candidate' 
                AND sig_sigma >= %s
            ORDER BY sig_sigma DESC, created_at DESC
            LIMIT %s
            """
            
            result = await self.supabase_manager.execute_query(query, [self.transfer_confidence_threshold, limit])
            
            transfers = []
            for strand in result:
                module_intel = strand['module_intelligence']
                transfer = TransferCandidate(
                    transfer_id=strand['id'],
                    source_motif_id=module_intel['source_motif_id'],
                    target_context=module_intel['target_context'],
                    transformation_mapping=module_intel['transformation_mapping'],
                    confidence_score=module_intel.get('confidence_score', strand['sig_sigma']),
                    transfer_hypothesis=module_intel['transfer_hypothesis'],
                    expected_conditions=module_intel['expected_conditions'],
                    created_at=strand['created_at']
                )
                transfers.append(transfer)
            
            return transfers
            
        except Exception as e:
            print(f"Error getting transfer candidates: {e}")
            return []
