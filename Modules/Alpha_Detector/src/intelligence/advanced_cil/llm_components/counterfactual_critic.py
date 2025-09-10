"""
Counterfactual Critic - LLM causal probe generation
Part of the Central Intelligence Layer Advanced LLM Components

This component writes counterfactuals for each Motif Card ("remove the volume spike—does divergence still predict?") 
and proposes Ablation/Boundary tests that target necessary vs. optional conditions. 
It also drafts the failure surface narrative.
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
class CounterfactualTest:
    """Represents a counterfactual test for a motif"""
    test_id: str
    motif_id: str
    test_type: str  # 'ablation', 'boundary', 'necessity', 'sufficiency'
    counterfactual_description: str
    test_hypothesis: str
    necessary_conditions: List[str]
    optional_conditions: List[str]
    expected_outcome: str
    failure_surface: Dict[str, Any]
    confidence_score: float
    created_at: datetime


@dataclass
class CausalSkeleton:
    """Represents the causal structure of a motif"""
    motif_id: str
    necessary_components: List[str]
    optional_components: List[str]
    causal_chain: List[str]
    failure_points: List[str]
    robustness_factors: List[str]
    created_at: datetime


class CounterfactualCritic:
    """
    LLM-first component that generates counterfactuals and causal probes for motifs.
    
    Key Features:
    - Analyzes motifs for causal structure
    - Generates counterfactual test hypotheses
    - Proposes Ablation/Boundary experiments
    - Identifies necessary vs optional conditions
    - Drafts failure surface narratives
    - Creates causal skeletons for motif understanding
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        
        # Configuration
        self.min_confidence_for_analysis = 0.6  # Minimum motif confidence for analysis
        self.max_tests_per_motif = 5  # Maximum counterfactual tests per motif
        self.test_confidence_threshold = 0.7  # Minimum confidence for test proposals
        
    async def analyze_motifs_for_causality(self) -> Tuple[List[CausalSkeleton], List[CounterfactualTest]]:
        """
        Main entry point: analyze motifs for causal structure and generate counterfactual tests
        
        Returns:
            Tuple of (causal_skeletons, counterfactual_tests)
        """
        try:
            # Get motifs for analysis
            motifs = await self._get_motifs_for_causal_analysis()
            
            if not motifs:
                return [], []
            
            causal_skeletons = []
            counterfactual_tests = []
            
            # Analyze each motif
            for motif in motifs:
                # Generate causal skeleton
                skeleton = await self._generate_causal_skeleton(motif)
                if skeleton:
                    causal_skeletons.append(skeleton)
                
                # Generate counterfactual tests
                tests = await self._generate_counterfactual_tests(motif)
                counterfactual_tests.extend(tests)
            
            # Publish results to database
            for skeleton in causal_skeletons:
                await self._publish_causal_skeleton_to_database(skeleton)
            
            for test in counterfactual_tests:
                await self._publish_counterfactual_test_to_database(test)
            
            return causal_skeletons, counterfactual_tests
            
        except Exception as e:
            print(f"Error in causal analysis: {e}")
            return [], []
    
    async def _get_motifs_for_causal_analysis(self) -> List[Dict[str, Any]]:
        """
        Get motifs that need causal analysis
        
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
                AND sig_sigma >= %s
                AND created_at >= NOW() - INTERVAL '14 days'
                AND id NOT IN (
                    SELECT DISTINCT module_intelligence->>'motif_id' 
                    FROM AD_strands 
                    WHERE kind = 'causal_skeleton'
                )
            ORDER BY sig_sigma DESC, created_at DESC
            LIMIT 20
            """
            
            result = await self.supabase_manager.execute_query(query, [self.min_confidence_for_analysis])
            return result
            
        except Exception as e:
            print(f"Error getting motifs for causal analysis: {e}")
            return []
    
    async def _generate_causal_skeleton(self, motif: Dict[str, Any]) -> Optional[CausalSkeleton]:
        """
        Generate causal skeleton for a motif using LLM analysis
        
        Args:
            motif: Motif data
            
        Returns:
            CausalSkeleton if successful, None otherwise
        """
        try:
            # Prepare motif data for causal analysis
            analysis_data = self._prepare_motif_for_causal_analysis(motif)
            
            # Get LLM prompt for causal analysis
            prompt = await self.prompt_manager.get_prompt(
                'counterfactual_critic',
                'generate_causal_skeleton',
                analysis_data
            )
            
            # Get LLM analysis
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.3
            )
            
            # Parse LLM response
            skeleton_data = self._parse_causal_skeleton_response(response, motif)
            
            if skeleton_data:
                return CausalSkeleton(**skeleton_data)
            
            return None
            
        except Exception as e:
            print(f"Error generating causal skeleton: {e}")
            return None
    
    def _prepare_motif_for_causal_analysis(self, motif: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare motif data for causal analysis
        
        Args:
            motif: Motif data
            
        Returns:
            Formatted analysis data
        """
        return {
            'motif': {
                'id': motif['id'],
                'name': motif['motif_name'],
                'family': motif['motif_family'],
                'invariants': motif['invariants'],
                'fails_when': motif['fails_when'],
                'contexts': motif['contexts'],
                'why_map': motif['why_map'],
                'confidence': motif['sig_sigma']
            },
            'analysis_context': {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'min_confidence': self.min_confidence_for_analysis
            }
        }
    
    def _parse_causal_skeleton_response(self, response: str, motif: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse LLM response to extract causal skeleton information
        
        Args:
            response: LLM response text
            motif: Original motif data
            
        Returns:
            Parsed causal skeleton data or None
        """
        try:
            # Try to extract JSON from response
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                
                skeleton_data = json.loads(json_str)
                
                # Validate required fields
                required_fields = ['necessary_components', 'optional_components', 'causal_chain']
                if all(field in skeleton_data for field in required_fields):
                    # Check for uncertainty flags - if too uncertain, return None
                    uncertainty_flags = skeleton_data.get('uncertainty_flags', {})
                    if (uncertainty_flags.get('causal_clarity') == 'low' or 
                        skeleton_data.get('causal_confidence', 0) < 0.4):
                        print(f"Causal analysis too uncertain, skipping: {uncertainty_flags}")
                        return None
                    
                    # Add metadata
                    skeleton_data['motif_id'] = motif['id']
                    skeleton_data['created_at'] = datetime.now(timezone.utc)
                    
                    # Ensure failure_points is a list
                    if 'failure_points' not in skeleton_data:
                        skeleton_data['failure_points'] = []
                    
                    # Ensure robustness_factors is a list
                    if 'robustness_factors' not in skeleton_data:
                        skeleton_data['robustness_factors'] = []
                    
                    return skeleton_data
            
            return None
            
        except Exception as e:
            print(f"Error parsing causal skeleton response: {e}")
            return None
    
    async def _generate_counterfactual_tests(self, motif: Dict[str, Any]) -> List[CounterfactualTest]:
        """
        Generate counterfactual tests for a motif
        
        Args:
            motif: Motif data
            
        Returns:
            List of CounterfactualTest objects
        """
        try:
            tests = []
            
            # Get causal skeleton for this motif
            skeleton = await self._get_causal_skeleton_by_motif_id(motif['id'])
            
            # Generate different types of counterfactual tests
            test_types = ['ablation', 'boundary', 'necessity', 'sufficiency']
            
            for test_type in test_types:
                test = await self._create_counterfactual_test(motif, skeleton, test_type)
                if test and test.confidence_score >= self.test_confidence_threshold:
                    tests.append(test)
            
            # Limit tests per motif
            tests.sort(key=lambda x: x.confidence_score, reverse=True)
            return tests[:self.max_tests_per_motif]
            
        except Exception as e:
            print(f"Error generating counterfactual tests: {e}")
            return []
    
    async def _create_counterfactual_test(self, motif: Dict[str, Any], skeleton: Optional[CausalSkeleton], test_type: str) -> Optional[CounterfactualTest]:
        """
        Create a specific counterfactual test
        
        Args:
            motif: Motif data
            skeleton: Causal skeleton (if available)
            test_type: Type of test to create
            
        Returns:
            CounterfactualTest if successful, None otherwise
        """
        try:
            # Prepare test generation data
            test_data = {
                'motif': {
                    'id': motif['id'],
                    'name': motif['motif_name'],
                    'family': motif['motif_family'],
                    'invariants': motif['invariants'],
                    'fails_when': motif['fails_when'],
                    'contexts': motif['contexts'],
                    'why_map': motif['why_map']
                },
                'causal_skeleton': {
                    'necessary_components': skeleton.necessary_components if skeleton else [],
                    'optional_components': skeleton.optional_components if skeleton else [],
                    'causal_chain': skeleton.causal_chain if skeleton else [],
                    'failure_points': skeleton.failure_points if skeleton else []
                } if skeleton else None,
                'test_type': test_type,
                'analysis_context': {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'test_confidence_threshold': self.test_confidence_threshold
                }
            }
            
            # Get LLM prompt for test generation
            prompt = await self.prompt_manager.get_prompt(
                'counterfactual_critic',
                'generate_counterfactual_test',
                test_data
            )
            
            # Get LLM analysis
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=1500,
                temperature=0.4
            )
            
            # Parse LLM response
            test_info = self._parse_counterfactual_test_response(response, motif, test_type)
            
            if test_info:
                return CounterfactualTest(**test_info)
            
            return None
            
        except Exception as e:
            print(f"Error creating counterfactual test: {e}")
            return None
    
    def _parse_counterfactual_test_response(self, response: str, motif: Dict[str, Any], test_type: str) -> Optional[Dict[str, Any]]:
        """
        Parse LLM response to extract counterfactual test information
        
        Args:
            response: LLM response text
            motif: Original motif data
            test_type: Type of test
            
        Returns:
            Parsed test data or None
        """
        try:
            # Try to extract JSON from response
            if '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                
                test_data = json.loads(json_str)
                
                # Validate required fields
                required_fields = ['counterfactual_description', 'test_hypothesis', 'confidence_score']
                if all(field in test_data for field in required_fields):
                    # Add metadata
                    test_data['test_id'] = f"counterfactual_{motif['id']}_{test_type}_{int(datetime.now().timestamp())}"
                    test_data['motif_id'] = motif['id']
                    test_data['test_type'] = test_type
                    test_data['created_at'] = datetime.now(timezone.utc)
                    
                    # Ensure lists are properly formatted
                    if 'necessary_conditions' not in test_data:
                        test_data['necessary_conditions'] = []
                    if 'optional_conditions' not in test_data:
                        test_data['optional_conditions'] = []
                    
                    # Ensure expected_outcome is a string
                    if 'expected_outcome' not in test_data:
                        test_data['expected_outcome'] = 'To be determined through testing'
                    
                    # Ensure failure_surface is a dict
                    if 'failure_surface' not in test_data:
                        test_data['failure_surface'] = {
                            'failure_conditions': [],
                            'robustness_factors': [],
                            'failure_narrative': 'To be determined through testing'
                        }
                    
                    return test_data
            
            return None
            
        except Exception as e:
            print(f"Error parsing counterfactual test response: {e}")
            return None
    
    async def _get_causal_skeleton_by_motif_id(self, motif_id: str) -> Optional[CausalSkeleton]:
        """
        Get causal skeleton for a motif by ID
        
        Args:
            motif_id: Motif ID to search for
            
        Returns:
            CausalSkeleton if found, None otherwise
        """
        try:
            query = """
            SELECT * FROM AD_strands 
            WHERE kind = 'causal_skeleton' 
                AND module_intelligence->>'motif_id' = %s
            ORDER BY created_at DESC
            LIMIT 1
            """
            
            result = await self.supabase_manager.execute_query(query, [motif_id])
            
            if result:
                strand = result[0]
                module_intel = strand['module_intelligence']
                return CausalSkeleton(
                    motif_id=module_intel['motif_id'],
                    necessary_components=module_intel['necessary_components'],
                    optional_components=module_intel['optional_components'],
                    causal_chain=module_intel['causal_chain'],
                    failure_points=module_intel.get('failure_points', []),
                    robustness_factors=module_intel.get('robustness_factors', []),
                    created_at=strand['created_at']
                )
            
            return None
            
        except Exception as e:
            print(f"Error getting causal skeleton by motif ID: {e}")
            return None
    
    async def _publish_causal_skeleton_to_database(self, skeleton: CausalSkeleton) -> bool:
        """
        Publish causal skeleton to database as specialized strand
        
        Args:
            skeleton: CausalSkeleton to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            strand_data = {
                'id': f"causal_skeleton_{skeleton.motif_id}_{int(datetime.now().timestamp())}",
                'module': 'alpha',
                'kind': 'causal_skeleton',
                'symbol': 'MULTI',
                'timeframe': 'MULTI',
                'session_bucket': 'MULTI',
                'regime': 'MULTI',
                'tags': ['agent:central_intelligence:counterfactual_critic:causal_analysis'],
                'created_at': skeleton.created_at.isoformat(),
                'updated_at': skeleton.created_at.isoformat(),
                
                # Causal skeleton data in module_intelligence
                'module_intelligence': {
                    'motif_id': skeleton.motif_id,
                    'necessary_components': skeleton.necessary_components,
                    'optional_components': skeleton.optional_components,
                    'causal_chain': skeleton.causal_chain,
                    'failure_points': skeleton.failure_points,
                    'robustness_factors': skeleton.robustness_factors
                },
                
                # CIL fields
                'team_member': 'counterfactual_critic',
                'strategic_meta_type': 'causal_analysis',
                'doctrine_status': 'provisional',
                
                # Scoring
                'sig_sigma': 0.8,  # High confidence in causal analysis
                'sig_confidence': 0.8,
                'accumulated_score': 0.8
            }
            
            result = await self.supabase_manager.insert_strand(strand_data)
            return result is not None
            
        except Exception as e:
            print(f"Error publishing causal skeleton to database: {e}")
            return False
    
    async def _publish_counterfactual_test_to_database(self, test: CounterfactualTest) -> bool:
        """
        Publish counterfactual test to database as specialized strand
        
        Args:
            test: CounterfactualTest to publish
            
        Returns:
            True if successful, False otherwise
        """
        try:
            strand_data = {
                'id': test.test_id,
                'module': 'alpha',
                'kind': 'counterfactual_test',
                'symbol': 'MULTI',
                'timeframe': 'MULTI',
                'session_bucket': 'MULTI',
                'regime': 'MULTI',
                'tags': ['agent:central_intelligence:counterfactual_critic:test_proposed'],
                'created_at': test.created_at.isoformat(),
                'updated_at': test.created_at.isoformat(),
                
                # Counterfactual test data in module_intelligence
                'module_intelligence': {
                    'motif_id': test.motif_id,
                    'test_type': test.test_type,
                    'counterfactual_description': test.counterfactual_description,
                    'test_hypothesis': test.test_hypothesis,
                    'necessary_conditions': test.necessary_conditions,
                    'optional_conditions': test.optional_conditions,
                    'expected_outcome': test.expected_outcome,
                    'failure_surface': test.failure_surface
                },
                
                # CIL fields
                'team_member': 'counterfactual_critic',
                'strategic_meta_type': 'counterfactual_test',
                'doctrine_status': 'provisional',
                
                # Scoring
                'sig_sigma': test.confidence_score,
                'sig_confidence': test.confidence_score,
                'accumulated_score': test.confidence_score
            }
            
            result = await self.supabase_manager.insert_strand(strand_data)
            return result is not None
            
        except Exception as e:
            print(f"Error publishing counterfactual test to database: {e}")
            return False
    
    async def get_counterfactual_tests_by_motif(self, motif_id: str, limit: int = 10) -> List[CounterfactualTest]:
        """
        Get counterfactual tests for a specific motif
        
        Args:
            motif_id: Motif ID to search for
            limit: Maximum number of tests to return
            
        Returns:
            List of CounterfactualTest objects
        """
        try:
            query = """
            SELECT * FROM AD_strands 
            WHERE kind = 'counterfactual_test' 
                AND module_intelligence->>'motif_id' = %s
            ORDER BY sig_sigma DESC, created_at DESC
            LIMIT %s
            """
            
            result = await self.supabase_manager.execute_query(query, [motif_id, limit])
            
            tests = []
            for strand in result:
                module_intel = strand['module_intelligence']
                test = CounterfactualTest(
                    test_id=strand['id'],
                    motif_id=module_intel['motif_id'],
                    test_type=module_intel['test_type'],
                    counterfactual_description=module_intel['counterfactual_description'],
                    test_hypothesis=module_intel['test_hypothesis'],
                    necessary_conditions=module_intel['necessary_conditions'],
                    optional_conditions=module_intel['optional_conditions'],
                    expected_outcome=module_intel['expected_outcome'],
                    failure_surface=module_intel['failure_surface'],
                    confidence_score=strand['sig_sigma'],
                    created_at=strand['created_at']
                )
                tests.append(test)
            
            return tests
            
        except Exception as e:
            print(f"Error getting counterfactual tests by motif: {e}")
            return []
    
    async def get_high_confidence_tests(self, limit: int = 10) -> List[CounterfactualTest]:
        """
        Get high-confidence counterfactual tests for experiment orchestration
        
        Args:
            limit: Maximum number of tests to return
            
        Returns:
            List of CounterfactualTest objects
        """
        try:
            query = """
            SELECT * FROM AD_strands 
            WHERE kind = 'counterfactual_test' 
                AND sig_sigma >= %s
            ORDER BY sig_sigma DESC, created_at DESC
            LIMIT %s
            """
            
            result = await self.supabase_manager.execute_query(query, [self.test_confidence_threshold, limit])
            
            tests = []
            for strand in result:
                module_intel = strand['module_intelligence']
                test = CounterfactualTest(
                    test_id=strand['id'],
                    motif_id=module_intel['motif_id'],
                    test_type=module_intel['test_type'],
                    counterfactual_description=module_intel['counterfactual_description'],
                    test_hypothesis=module_intel['test_hypothesis'],
                    necessary_conditions=module_intel['necessary_conditions'],
                    optional_conditions=module_intel['optional_conditions'],
                    expected_outcome=module_intel['expected_outcome'],
                    failure_surface=module_intel['failure_surface'],
                    confidence_score=strand['sig_sigma'],
                    created_at=strand['created_at']
                )
                tests.append(test)
            
            return tests
            
        except Exception as e:
            print(f"Error getting high confidence tests: {e}")
            return []
