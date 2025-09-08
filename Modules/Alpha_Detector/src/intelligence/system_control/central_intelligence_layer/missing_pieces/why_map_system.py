"""
CIL Why-Map System - Missing Piece 1
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class MechanismType(Enum):
    """Types of mechanisms that can be hypothesized"""
    LIQUIDITY_VACUUM = "liquidity_vacuum"
    MOMENTUM_CARRYOVER = "momentum_carryover"
    ARBITRAGE_PRESSURE = "arbitrage_pressure"
    SENTIMENT_SHIFT = "sentiment_shift"
    VOLUME_CONFIRMATION = "volume_confirmation"
    REJECTION_PATTERN = "rejection_pattern"
    TREND_CONTINUATION = "trend_continuation"
    REGIME_SHIFT = "regime_shift"


class EvidenceStrength(Enum):
    """Strength of evidence supporting a mechanism"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    CONVINCING = "convincing"


class MechanismStatus(Enum):
    """Status of a mechanism hypothesis"""
    PROVISIONAL = "provisional"
    AFFIRMED = "affirmed"
    RETIRED = "retired"
    CONTRADICTED = "contradicted"


@dataclass
class MechanismHypothesis:
    """A mechanism hypothesis for why a pattern works"""
    hypothesis_id: str
    pattern_family: str
    mechanism_type: MechanismType
    mechanism_description: str
    evidence_motifs: List[str]
    fails_when_conditions: List[str]
    confidence_level: float
    evidence_strength: EvidenceStrength
    status: MechanismStatus
    created_at: datetime
    updated_at: datetime


@dataclass
class WhyMapEntry:
    """A Why-Map entry for a pattern family"""
    family_id: str
    pattern_family: str
    primary_mechanism: MechanismHypothesis
    alternative_mechanisms: List[MechanismHypothesis]
    mechanism_evolution: List[Dict[str, Any]]
    cross_family_connections: List[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class MechanismEvidence:
    """Evidence supporting or contradicting a mechanism"""
    evidence_id: str
    mechanism_id: str
    evidence_type: str
    evidence_description: str
    supporting: bool
    confidence: float
    source_strand_id: str
    created_at: datetime


class WhyMapSystem:
    """CIL Why-Map System - Forces 'why does this work?' before continuation"""
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        
        # Configuration
        self.mechanism_confidence_threshold = 0.7
        self.evidence_accumulation_threshold = 3
        self.mechanism_retirement_threshold = 0.3
        self.cross_family_connection_threshold = 0.8
        
        # Why-Map state
        self.why_map_entries = {}
        self.mechanism_hypotheses = {}
        self.mechanism_evidence = {}
        
        # LLM prompt templates
        self.mechanism_analysis_prompt = self._load_mechanism_analysis_prompt()
        self.evidence_evaluation_prompt = self._load_evidence_evaluation_prompt()
        self.cross_family_analysis_prompt = self._load_cross_family_analysis_prompt()
    
    def _load_mechanism_analysis_prompt(self) -> str:
        """Load mechanism analysis prompt template"""
        return """
        Analyze the following pattern detection and generate a mechanism hypothesis for why it works.
        
        Pattern Details:
        - Family: {pattern_family}
        - Context: {context}
        - Success Rate: {success_rate}
        - Conditions: {conditions}
        - Evidence: {evidence}
        
        Generate a mechanism hypothesis that explains:
        1. What underlying market mechanism causes this pattern to work
        2. What evidence motifs support this mechanism
        3. What conditions would cause this mechanism to fail
        4. Confidence level in this mechanism (0.0-1.0)
        
        Respond in JSON format:
        {{
            "mechanism_type": "one of the mechanism types",
            "mechanism_description": "detailed explanation of the mechanism",
            "evidence_motifs": ["list of supporting evidence"],
            "fails_when_conditions": ["list of failure conditions"],
            "confidence_level": 0.0-1.0,
            "uncertainty_flags": ["any uncertainties or limitations"]
        }}
        """
    
    def _load_evidence_evaluation_prompt(self) -> str:
        """Load evidence evaluation prompt template"""
        return """
        Evaluate the strength of evidence for the following mechanism hypothesis.
        
        Mechanism: {mechanism_description}
        Evidence: {evidence_list}
        
        Assess:
        1. How strongly the evidence supports the mechanism
        2. Whether the evidence is consistent across different contexts
        3. Any contradictory evidence
        4. Overall evidence strength (weak/moderate/strong/convincing)
        
        Respond in JSON format:
        {{
            "evidence_strength": "weak|moderate|strong|convincing",
            "consistency_score": 0.0-1.0,
            "contradictory_evidence": ["list of contradictions"],
            "evaluation_confidence": 0.0-1.0
        }}
        """
    
    def _load_cross_family_analysis_prompt(self) -> str:
        """Load cross-family analysis prompt template"""
        return """
        Analyze connections between different pattern families and their mechanisms.
        
        Pattern Families: {pattern_families}
        Mechanisms: {mechanisms}
        
        Identify:
        1. Shared underlying mechanisms across families
        2. How mechanisms interact or reinforce each other
        3. Cross-family evidence that supports mechanism hypotheses
        4. Potential mechanism conflicts or contradictions
        
        Respond in JSON format:
        {{
            "shared_mechanisms": ["list of shared mechanisms"],
            "mechanism_interactions": ["list of interactions"],
            "cross_family_evidence": ["list of cross-family evidence"],
            "mechanism_conflicts": ["list of conflicts"],
            "connection_strength": 0.0-1.0
        }}
        """
    
    async def process_why_map_analysis(self, pattern_detections: List[Dict[str, Any]],
                                     learning_results: Dict[str, Any]) -> Dict[str, Any]:
        """Process Why-Map analysis for pattern detections"""
        try:
            # Generate mechanism hypotheses for new patterns
            mechanism_hypotheses = await self._generate_mechanism_hypotheses(pattern_detections)
            
            # Evaluate evidence for existing mechanisms
            evidence_evaluations = await self._evaluate_mechanism_evidence(mechanism_hypotheses)
            
            # Update Why-Map entries
            why_map_updates = await self._update_why_map_entries(mechanism_hypotheses, evidence_evaluations)
            
            # Analyze cross-family connections
            cross_family_analysis = await self._analyze_cross_family_connections(why_map_updates)
            
            # Compile results
            results = {
                'mechanism_hypotheses': mechanism_hypotheses,
                'evidence_evaluations': evidence_evaluations,
                'why_map_updates': why_map_updates,
                'cross_family_analysis': cross_family_analysis,
                'why_map_timestamp': datetime.now(timezone.utc),
                'why_map_errors': []
            }
            
            # Publish results
            await self._publish_why_map_results(results)
            
            return results
            
        except Exception as e:
            print(f"Error processing Why-Map analysis: {e}")
            return {
                'mechanism_hypotheses': [],
                'evidence_evaluations': [],
                'why_map_updates': [],
                'cross_family_analysis': [],
                'why_map_timestamp': datetime.now(timezone.utc),
                'why_map_errors': [str(e)]
            }
    
    async def _generate_mechanism_hypotheses(self, pattern_detections: List[Dict[str, Any]]) -> List[MechanismHypothesis]:
        """Generate mechanism hypotheses for pattern detections"""
        hypotheses = []
        
        for detection in pattern_detections:
            # Check if mechanism hypothesis already exists
            pattern_family = detection.get('pattern_family', 'unknown')
            if pattern_family in self.mechanism_hypotheses:
                continue
            
            # Generate mechanism hypothesis using LLM
            hypothesis = await self._create_mechanism_hypothesis(detection)
            if hypothesis:
                hypotheses.append(hypothesis)
                self.mechanism_hypotheses[pattern_family] = hypothesis
        
        return hypotheses
    
    async def _create_mechanism_hypothesis(self, detection: Dict[str, Any]) -> Optional[MechanismHypothesis]:
        """Create a mechanism hypothesis for a pattern detection"""
        try:
            # Prepare prompt data
            prompt_data = {
                'pattern_family': detection.get('pattern_family', 'unknown'),
                'context': detection.get('context', {}),
                'success_rate': detection.get('success_rate', 0.0),
                'conditions': detection.get('conditions', {}),
                'evidence': detection.get('evidence', [])
            }
            
            # Generate mechanism analysis using LLM
            mechanism_analysis = await self._generate_llm_analysis(
                self.mechanism_analysis_prompt, prompt_data
            )
            
            if not mechanism_analysis:
                return None
            
            # Create mechanism hypothesis
            hypothesis = MechanismHypothesis(
                hypothesis_id=f"MECHANISM_{int(datetime.now().timestamp())}",
                pattern_family=detection.get('pattern_family', 'unknown'),
                mechanism_type=MechanismType(mechanism_analysis.get('mechanism_type', 'liquidity_vacuum')),
                mechanism_description=mechanism_analysis.get('mechanism_description', ''),
                evidence_motifs=mechanism_analysis.get('evidence_motifs', []),
                fails_when_conditions=mechanism_analysis.get('fails_when_conditions', []),
                confidence_level=mechanism_analysis.get('confidence_level', 0.5),
                evidence_strength=EvidenceStrength.WEAK,  # Initial strength
                status=MechanismStatus.PROVISIONAL,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            return hypothesis
            
        except Exception as e:
            print(f"Error creating mechanism hypothesis: {e}")
            return None
    
    async def _generate_llm_analysis(self, prompt_template: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate LLM analysis using prompt template"""
        try:
            # Format prompt with data
            formatted_prompt = prompt_template.format(**data)
            
            # Call LLM (mock implementation)
            # In real implementation, use self.llm_client
            response = {
                "mechanism_type": "liquidity_vacuum",
                "mechanism_description": "Liquidity vacuum after failed retest creates price rejection",
                "evidence_motifs": ["volume_confirmation", "rejection_pattern", "failed_retest"],
                "fails_when_conditions": ["trend_continuation", "low_participation", "strong_momentum"],
                "confidence_level": 0.8,
                "uncertainty_flags": ["limited_sample_size", "regime_dependency"]
            }
            
            return response
            
        except Exception as e:
            print(f"Error generating LLM analysis: {e}")
            return None
    
    async def _evaluate_mechanism_evidence(self, hypotheses: List[MechanismHypothesis]) -> List[Dict[str, Any]]:
        """Evaluate evidence for mechanism hypotheses"""
        evaluations = []
        
        for hypothesis in hypotheses:
            # Gather evidence for this mechanism
            evidence = await self._gather_mechanism_evidence(hypothesis)
            
            # Evaluate evidence strength
            evaluation = await self._evaluate_evidence_strength(hypothesis, evidence)
            
            if evaluation:
                evaluations.append(evaluation)
        
        return evaluations
    
    async def _gather_mechanism_evidence(self, hypothesis: MechanismHypothesis) -> List[MechanismEvidence]:
        """Gather evidence for a mechanism hypothesis"""
        evidence = []
        
        # Query database for strands related to this pattern family
        # Mock implementation - in real system, query AD_strands table
        mock_evidence = [
            {
                'evidence_id': f"EVIDENCE_{int(datetime.now().timestamp())}",
                'mechanism_id': hypothesis.hypothesis_id,
                'evidence_type': 'supporting',
                'evidence_description': 'Volume spike confirms liquidity vacuum',
                'supporting': True,
                'confidence': 0.8,
                'source_strand_id': 'strand_123',
                'created_at': datetime.now(timezone.utc)
            }
        ]
        
        for ev_data in mock_evidence:
            evidence.append(MechanismEvidence(**ev_data))
        
        return evidence
    
    async def _evaluate_evidence_strength(self, hypothesis: MechanismHypothesis, 
                                        evidence: List[MechanismEvidence]) -> Optional[Dict[str, Any]]:
        """Evaluate the strength of evidence for a mechanism"""
        try:
            if not evidence:
                return None
            
            # Prepare evidence data for LLM analysis
            evidence_data = {
                'mechanism_description': hypothesis.mechanism_description,
                'evidence_list': [ev.evidence_description for ev in evidence]
            }
            
            # Generate evidence evaluation using LLM
            evaluation = await self._generate_llm_analysis(
                self.evidence_evaluation_prompt, evidence_data
            )
            
            if not evaluation:
                return None
            
            # Update hypothesis evidence strength
            hypothesis.evidence_strength = EvidenceStrength(evaluation.get('evidence_strength', 'weak'))
            hypothesis.updated_at = datetime.now(timezone.utc)
            
            return {
                'hypothesis_id': hypothesis.hypothesis_id,
                'evidence_strength': evaluation.get('evidence_strength', 'weak'),
                'consistency_score': evaluation.get('consistency_score', 0.5),
                'contradictory_evidence': evaluation.get('contradictory_evidence', []),
                'evaluation_confidence': evaluation.get('evaluation_confidence', 0.5)
            }
            
        except Exception as e:
            print(f"Error evaluating evidence strength: {e}")
            return None
    
    async def _update_why_map_entries(self, hypotheses: List[MechanismHypothesis],
                                    evidence_evaluations: List[Dict[str, Any]]) -> List[WhyMapEntry]:
        """Update Why-Map entries with new hypotheses and evidence"""
        updates = []
        
        for hypothesis in hypotheses:
            # Check if Why-Map entry exists for this pattern family
            if hypothesis.pattern_family in self.why_map_entries:
                # Update existing entry
                entry = self.why_map_entries[hypothesis.pattern_family]
                await self._update_existing_why_map_entry(entry, hypothesis, evidence_evaluations)
            else:
                # Create new entry
                entry = await self._create_new_why_map_entry(hypothesis, evidence_evaluations)
                self.why_map_entries[hypothesis.pattern_family] = entry
            
            updates.append(entry)
        
        return updates
    
    async def _update_existing_why_map_entry(self, entry: WhyMapEntry, hypothesis: MechanismHypothesis,
                                           evidence_evaluations: List[Dict[str, Any]]):
        """Update an existing Why-Map entry"""
        # Check if this is a better primary mechanism
        if hypothesis.confidence_level > entry.primary_mechanism.confidence_level:
            # Move current primary to alternatives
            entry.alternative_mechanisms.append(entry.primary_mechanism)
            entry.primary_mechanism = hypothesis
        else:
            # Add as alternative mechanism
            entry.alternative_mechanisms.append(hypothesis)
        
        # Update mechanism evolution
        evolution_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'action': 'mechanism_updated',
            'hypothesis_id': hypothesis.hypothesis_id,
            'confidence_level': hypothesis.confidence_level,
            'evidence_strength': hypothesis.evidence_strength.value
        }
        entry.mechanism_evolution.append(evolution_entry)
        
        # Update timestamp
        entry.updated_at = datetime.now(timezone.utc)
    
    async def _create_new_why_map_entry(self, hypothesis: MechanismHypothesis,
                                      evidence_evaluations: List[Dict[str, Any]]) -> WhyMapEntry:
        """Create a new Why-Map entry"""
        entry = WhyMapEntry(
            family_id=f"FAMILY_{int(datetime.now().timestamp())}",
            pattern_family=hypothesis.pattern_family,
            primary_mechanism=hypothesis,
            alternative_mechanisms=[],
            mechanism_evolution=[{
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'action': 'mechanism_created',
                'hypothesis_id': hypothesis.hypothesis_id,
                'confidence_level': hypothesis.confidence_level,
                'evidence_strength': hypothesis.evidence_strength.value
            }],
            cross_family_connections=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        return entry
    
    async def _analyze_cross_family_connections(self, why_map_updates: List[WhyMapEntry]) -> Dict[str, Any]:
        """Analyze connections between different pattern families"""
        try:
            if len(why_map_updates) < 2:
                return {'connections': [], 'shared_mechanisms': [], 'interactions': []}
            
            # Prepare data for cross-family analysis
            pattern_families = [entry.pattern_family for entry in why_map_updates]
            mechanisms = [entry.primary_mechanism.mechanism_description for entry in why_map_updates]
            
            analysis_data = {
                'pattern_families': pattern_families,
                'mechanisms': mechanisms
            }
            
            # Generate cross-family analysis using LLM
            analysis = await self._generate_llm_analysis(
                self.cross_family_analysis_prompt, analysis_data
            )
            
            if not analysis:
                return {'connections': [], 'shared_mechanisms': [], 'interactions': []}
            
            # Update cross-family connections in Why-Map entries
            for entry in why_map_updates:
                entry.cross_family_connections = analysis.get('shared_mechanisms', [])
                entry.updated_at = datetime.now(timezone.utc)
            
            return {
                'shared_mechanisms': analysis.get('shared_mechanisms', []),
                'mechanism_interactions': analysis.get('mechanism_interactions', []),
                'cross_family_evidence': analysis.get('cross_family_evidence', []),
                'mechanism_conflicts': analysis.get('mechanism_conflicts', []),
                'connection_strength': analysis.get('connection_strength', 0.0)
            }
            
        except Exception as e:
            print(f"Error analyzing cross-family connections: {e}")
            return {'connections': [], 'shared_mechanisms': [], 'interactions': []}
    
    async def _publish_why_map_results(self, results: Dict[str, Any]):
        """Publish Why-Map results as CIL strand"""
        try:
            # Create CIL Why-Map strand
            cil_strand = {
                'id': f"cil_why_map_{int(datetime.now().timestamp())}",
                'kind': 'cil_why_map',
                'module': 'alpha',
                'symbol': 'ALL',
                'timeframe': '1h',
                'session_bucket': 'ALL',
                'regime': 'all',
                'tags': ['agent:central_intelligence:why_map_system:mechanism_analysis'],
                'content': json.dumps(results, default=str),
                'sig_sigma': 0.9,
                'sig_confidence': 0.95,
                'outcome_score': 0.0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'agent_id': 'central_intelligence_layer',
                'cil_team_member': 'why_map_system',
                'strategic_meta_type': 'mechanism_analysis',
                'resonance_score': 0.9
            }
            
            # Insert into database
            await self.supabase_manager.insert_strand(cil_strand)
            
        except Exception as e:
            print(f"Error publishing Why-Map results: {e}")


# Example usage and testing
async def main():
    """Example usage of WhyMapSystem"""
    from src.utils.supabase_manager import SupabaseManager
    from src.llm_integration.openrouter_client import OpenRouterClient
    
    # Initialize components
    supabase_manager = SupabaseManager()
    llm_client = OpenRouterClient()
    
    # Create Why-Map system
    why_map_system = WhyMapSystem(supabase_manager, llm_client)
    
    # Mock pattern detections
    pattern_detections = [
        {
            'pattern_family': 'divergence',
            'context': {'regime': 'high_vol', 'session': 'US'},
            'success_rate': 0.8,
            'conditions': {'rsi_divergence': True, 'volume_spike': True},
            'evidence': ['volume_confirmation', 'rejection_pattern']
        },
        {
            'pattern_family': 'volume_anomaly',
            'context': {'regime': 'sideways', 'session': 'EU'},
            'success_rate': 0.7,
            'conditions': {'volume_spike': True, 'price_rejection': True},
            'evidence': ['volume_spike', 'price_rejection']
        }
    ]
    
    learning_results = {}
    
    # Process Why-Map analysis
    results = await why_map_system.process_why_map_analysis(pattern_detections, learning_results)
    
    print("Why-Map Analysis Results:")
    print(f"Mechanism Hypotheses: {len(results['mechanism_hypotheses'])}")
    print(f"Evidence Evaluations: {len(results['evidence_evaluations'])}")
    print(f"Why-Map Updates: {len(results['why_map_updates'])}")
    print(f"Cross-Family Analysis: {len(results['cross_family_analysis'])}")


if __name__ == "__main__":
    asyncio.run(main())
