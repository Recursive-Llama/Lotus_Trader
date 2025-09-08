"""
Test CIL Why-Map System
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.intelligence.system_control.central_intelligence_layer.missing_pieces.why_map_system import (
    WhyMapSystem, MechanismType, EvidenceStrength, MechanismStatus,
    MechanismHypothesis, WhyMapEntry, MechanismEvidence
)


class TestWhyMapSystem:
    """Test CIL Why-Map System"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        """Mock SupabaseManager"""
        manager = Mock()
        manager.execute_query = AsyncMock()
        manager.insert_strand = AsyncMock()
        return manager
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock OpenRouterClient"""
        return Mock()
    
    @pytest.fixture
    def why_map_system(self, mock_supabase_manager, mock_llm_client):
        """Create WhyMapSystem instance"""
        return WhyMapSystem(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def mock_pattern_detections(self):
        """Mock pattern detections"""
        return [
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
    
    def test_why_map_system_initialization(self, why_map_system):
        """Test WhyMapSystem initialization"""
        assert why_map_system.supabase_manager is not None
        assert why_map_system.llm_client is not None
        assert why_map_system.mechanism_confidence_threshold == 0.7
        assert why_map_system.evidence_accumulation_threshold == 3
        assert why_map_system.mechanism_retirement_threshold == 0.3
        assert why_map_system.cross_family_connection_threshold == 0.8
        assert why_map_system.mechanism_analysis_prompt is not None
        assert why_map_system.evidence_evaluation_prompt is not None
        assert why_map_system.cross_family_analysis_prompt is not None
    
    def test_load_prompt_templates(self, why_map_system):
        """Test prompt template loading"""
        # Test mechanism analysis prompt
        assert 'pattern_family' in why_map_system.mechanism_analysis_prompt
        assert 'context' in why_map_system.mechanism_analysis_prompt
        assert 'success_rate' in why_map_system.mechanism_analysis_prompt
        assert 'conditions' in why_map_system.mechanism_analysis_prompt
        assert 'evidence' in why_map_system.mechanism_analysis_prompt
        
        # Test evidence evaluation prompt
        assert 'mechanism_description' in why_map_system.evidence_evaluation_prompt
        assert 'evidence_list' in why_map_system.evidence_evaluation_prompt
        
        # Test cross-family analysis prompt
        assert 'pattern_families' in why_map_system.cross_family_analysis_prompt
        assert 'mechanisms' in why_map_system.cross_family_analysis_prompt
    
    @pytest.mark.asyncio
    async def test_process_why_map_analysis_success(self, why_map_system, mock_pattern_detections):
        """Test successful Why-Map analysis processing"""
        learning_results = {}
        
        # Process Why-Map analysis
        results = await why_map_system.process_why_map_analysis(mock_pattern_detections, learning_results)
        
        # Verify structure
        assert 'mechanism_hypotheses' in results
        assert 'evidence_evaluations' in results
        assert 'why_map_updates' in results
        assert 'cross_family_analysis' in results
        assert 'why_map_timestamp' in results
        assert 'why_map_errors' in results
        
        # Verify processing timestamp
        assert isinstance(results['why_map_timestamp'], datetime)
        
        # Verify results are lists
        assert isinstance(results['mechanism_hypotheses'], list)
        assert isinstance(results['evidence_evaluations'], list)
        assert isinstance(results['why_map_updates'], list)
        assert isinstance(results['cross_family_analysis'], dict)
        assert isinstance(results['why_map_errors'], list)
    
    @pytest.mark.asyncio
    async def test_generate_mechanism_hypotheses(self, why_map_system, mock_pattern_detections):
        """Test mechanism hypothesis generation"""
        # Generate mechanism hypotheses
        hypotheses = await why_map_system._generate_mechanism_hypotheses(mock_pattern_detections)
        
        # Verify results
        assert isinstance(hypotheses, list)
        assert len(hypotheses) == 2  # Should generate hypotheses for both pattern families
        
        # Check hypothesis structure
        for hypothesis in hypotheses:
            assert isinstance(hypothesis, MechanismHypothesis)
            assert hypothesis.hypothesis_id.startswith('MECHANISM_')
            assert hypothesis.pattern_family in ['divergence', 'volume_anomaly']
            assert isinstance(hypothesis.mechanism_type, MechanismType)
            assert isinstance(hypothesis.mechanism_description, str)
            assert isinstance(hypothesis.evidence_motifs, list)
            assert isinstance(hypothesis.fails_when_conditions, list)
            assert 0.0 <= hypothesis.confidence_level <= 1.0
            assert isinstance(hypothesis.evidence_strength, EvidenceStrength)
            assert isinstance(hypothesis.status, MechanismStatus)
            assert isinstance(hypothesis.created_at, datetime)
            assert isinstance(hypothesis.updated_at, datetime)
    
    @pytest.mark.asyncio
    async def test_create_mechanism_hypothesis(self, why_map_system):
        """Test mechanism hypothesis creation"""
        detection = {
            'pattern_family': 'divergence',
            'context': {'regime': 'high_vol', 'session': 'US'},
            'success_rate': 0.8,
            'conditions': {'rsi_divergence': True, 'volume_spike': True},
            'evidence': ['volume_confirmation', 'rejection_pattern']
        }
        
        # Create mechanism hypothesis
        hypothesis = await why_map_system._create_mechanism_hypothesis(detection)
        
        # Verify hypothesis
        assert hypothesis is not None
        assert isinstance(hypothesis, MechanismHypothesis)
        assert hypothesis.hypothesis_id.startswith('MECHANISM_')
        assert hypothesis.pattern_family == 'divergence'
        assert hypothesis.mechanism_type == MechanismType.LIQUIDITY_VACUUM
        assert hypothesis.mechanism_description == 'Liquidity vacuum after failed retest creates price rejection'
        assert hypothesis.evidence_motifs == ['volume_confirmation', 'rejection_pattern', 'failed_retest']
        assert hypothesis.fails_when_conditions == ['trend_continuation', 'low_participation', 'strong_momentum']
        assert hypothesis.confidence_level == 0.8
        assert hypothesis.evidence_strength == EvidenceStrength.WEAK
        assert hypothesis.status == MechanismStatus.PROVISIONAL
        assert isinstance(hypothesis.created_at, datetime)
        assert isinstance(hypothesis.updated_at, datetime)
    
    @pytest.mark.asyncio
    async def test_generate_llm_analysis(self, why_map_system):
        """Test LLM analysis generation"""
        prompt_template = "Test prompt with {test_field}"
        data = {'test_field': 'test_value'}
        
        # Generate LLM analysis
        analysis = await why_map_system._generate_llm_analysis(prompt_template, data)
        
        # Verify analysis
        assert analysis is not None
        assert isinstance(analysis, dict)
        assert 'mechanism_type' in analysis
        assert 'mechanism_description' in analysis
        assert 'evidence_motifs' in analysis
        assert 'fails_when_conditions' in analysis
        assert 'confidence_level' in analysis
        assert 'uncertainty_flags' in analysis
        
        # Verify specific values
        assert analysis['mechanism_type'] == 'liquidity_vacuum'
        assert analysis['mechanism_description'] == 'Liquidity vacuum after failed retest creates price rejection'
        assert analysis['evidence_motifs'] == ['volume_confirmation', 'rejection_pattern', 'failed_retest']
        assert analysis['fails_when_conditions'] == ['trend_continuation', 'low_participation', 'strong_momentum']
        assert analysis['confidence_level'] == 0.8
        assert analysis['uncertainty_flags'] == ['limited_sample_size', 'regime_dependency']
    
    @pytest.mark.asyncio
    async def test_evaluate_mechanism_evidence(self, why_map_system):
        """Test mechanism evidence evaluation"""
        # Create test hypotheses
        hypothesis1 = MechanismHypothesis(
            hypothesis_id='MECHANISM_1',
            pattern_family='divergence',
            mechanism_type=MechanismType.LIQUIDITY_VACUUM,
            mechanism_description='Test mechanism 1',
            evidence_motifs=['evidence1', 'evidence2'],
            fails_when_conditions=['condition1'],
            confidence_level=0.8,
            evidence_strength=EvidenceStrength.WEAK,
            status=MechanismStatus.PROVISIONAL,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        hypothesis2 = MechanismHypothesis(
            hypothesis_id='MECHANISM_2',
            pattern_family='volume_anomaly',
            mechanism_type=MechanismType.VOLUME_CONFIRMATION,
            mechanism_description='Test mechanism 2',
            evidence_motifs=['evidence3', 'evidence4'],
            fails_when_conditions=['condition2'],
            confidence_level=0.7,
            evidence_strength=EvidenceStrength.WEAK,
            status=MechanismStatus.PROVISIONAL,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        hypotheses = [hypothesis1, hypothesis2]
        
        # Evaluate mechanism evidence
        evaluations = await why_map_system._evaluate_mechanism_evidence(hypotheses)
        
        # Verify results
        assert isinstance(evaluations, list)
        assert len(evaluations) == 2  # Should evaluate both hypotheses
        
        # Check evaluation structure
        for evaluation in evaluations:
            assert isinstance(evaluation, dict)
            assert 'hypothesis_id' in evaluation
            assert 'evidence_strength' in evaluation
            assert 'consistency_score' in evaluation
            assert 'contradictory_evidence' in evaluation
            assert 'evaluation_confidence' in evaluation
            
            # Verify specific values
            assert evaluation['evidence_strength'] in ['weak', 'moderate', 'strong', 'convincing']
            assert 0.0 <= evaluation['consistency_score'] <= 1.0
            assert isinstance(evaluation['contradictory_evidence'], list)
            assert 0.0 <= evaluation['evaluation_confidence'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_gather_mechanism_evidence(self, why_map_system):
        """Test mechanism evidence gathering"""
        hypothesis = MechanismHypothesis(
            hypothesis_id='MECHANISM_1',
            pattern_family='divergence',
            mechanism_type=MechanismType.LIQUIDITY_VACUUM,
            mechanism_description='Test mechanism',
            evidence_motifs=['evidence1', 'evidence2'],
            fails_when_conditions=['condition1'],
            confidence_level=0.8,
            evidence_strength=EvidenceStrength.WEAK,
            status=MechanismStatus.PROVISIONAL,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Gather mechanism evidence
        evidence = await why_map_system._gather_mechanism_evidence(hypothesis)
        
        # Verify results
        assert isinstance(evidence, list)
        assert len(evidence) == 1  # Mock implementation returns one piece of evidence
        
        # Check evidence structure
        for ev in evidence:
            assert isinstance(ev, MechanismEvidence)
            assert ev.evidence_id.startswith('EVIDENCE_')
            assert ev.mechanism_id == 'MECHANISM_1'
            assert ev.evidence_type == 'supporting'
            assert ev.evidence_description == 'Volume spike confirms liquidity vacuum'
            assert ev.supporting is True
            assert 0.0 <= ev.confidence <= 1.0
            assert ev.source_strand_id == 'strand_123'
            assert isinstance(ev.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_evaluate_evidence_strength(self, why_map_system):
        """Test evidence strength evaluation"""
        hypothesis = MechanismHypothesis(
            hypothesis_id='MECHANISM_1',
            pattern_family='divergence',
            mechanism_type=MechanismType.LIQUIDITY_VACUUM,
            mechanism_description='Test mechanism',
            evidence_motifs=['evidence1', 'evidence2'],
            fails_when_conditions=['condition1'],
            confidence_level=0.8,
            evidence_strength=EvidenceStrength.WEAK,
            status=MechanismStatus.PROVISIONAL,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        evidence = [
            MechanismEvidence(
                evidence_id='EVIDENCE_1',
                mechanism_id='MECHANISM_1',
                evidence_type='supporting',
                evidence_description='Volume spike confirms liquidity vacuum',
                supporting=True,
                confidence=0.8,
                source_strand_id='strand_123',
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        # Evaluate evidence strength
        evaluation = await why_map_system._evaluate_evidence_strength(hypothesis, evidence)
        
        # Verify evaluation
        assert evaluation is not None
        assert isinstance(evaluation, dict)
        assert 'hypothesis_id' in evaluation
        assert 'evidence_strength' in evaluation
        assert 'consistency_score' in evaluation
        assert 'contradictory_evidence' in evaluation
        assert 'evaluation_confidence' in evaluation
        
        # Verify specific values
        assert evaluation['hypothesis_id'] == 'MECHANISM_1'
        assert evaluation['evidence_strength'] in ['weak', 'moderate', 'strong', 'convincing']
        assert 0.0 <= evaluation['consistency_score'] <= 1.0
        assert isinstance(evaluation['contradictory_evidence'], list)
        assert 0.0 <= evaluation['evaluation_confidence'] <= 1.0
        
        # Verify hypothesis was updated
        assert hypothesis.evidence_strength in [EvidenceStrength.WEAK, EvidenceStrength.MODERATE, 
                                               EvidenceStrength.STRONG, EvidenceStrength.CONVINCING]
        assert isinstance(hypothesis.updated_at, datetime)
    
    @pytest.mark.asyncio
    async def test_update_why_map_entries(self, why_map_system):
        """Test Why-Map entry updates"""
        # Create test hypotheses
        hypothesis1 = MechanismHypothesis(
            hypothesis_id='MECHANISM_1',
            pattern_family='divergence',
            mechanism_type=MechanismType.LIQUIDITY_VACUUM,
            mechanism_description='Test mechanism 1',
            evidence_motifs=['evidence1', 'evidence2'],
            fails_when_conditions=['condition1'],
            confidence_level=0.8,
            evidence_strength=EvidenceStrength.STRONG,
            status=MechanismStatus.PROVISIONAL,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        hypothesis2 = MechanismHypothesis(
            hypothesis_id='MECHANISM_2',
            pattern_family='volume_anomaly',
            mechanism_type=MechanismType.VOLUME_CONFIRMATION,
            mechanism_description='Test mechanism 2',
            evidence_motifs=['evidence3', 'evidence4'],
            fails_when_conditions=['condition2'],
            confidence_level=0.7,
            evidence_strength=EvidenceStrength.MODERATE,
            status=MechanismStatus.PROVISIONAL,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        hypotheses = [hypothesis1, hypothesis2]
        evidence_evaluations = [
            {
                'hypothesis_id': 'MECHANISM_1',
                'evidence_strength': 'strong',
                'consistency_score': 0.8,
                'contradictory_evidence': [],
                'evaluation_confidence': 0.9
            },
            {
                'hypothesis_id': 'MECHANISM_2',
                'evidence_strength': 'moderate',
                'consistency_score': 0.6,
                'contradictory_evidence': [],
                'evaluation_confidence': 0.7
            }
        ]
        
        # Update Why-Map entries
        updates = await why_map_system._update_why_map_entries(hypotheses, evidence_evaluations)
        
        # Verify results
        assert isinstance(updates, list)
        assert len(updates) == 2  # Should update both pattern families
        
        # Check update structure
        for update in updates:
            assert isinstance(update, WhyMapEntry)
            assert update.family_id.startswith('FAMILY_')
            assert update.pattern_family in ['divergence', 'volume_anomaly']
            assert isinstance(update.primary_mechanism, MechanismHypothesis)
            assert isinstance(update.alternative_mechanisms, list)
            assert isinstance(update.mechanism_evolution, list)
            assert isinstance(update.cross_family_connections, list)
            assert isinstance(update.created_at, datetime)
            assert isinstance(update.updated_at, datetime)
            
            # Verify mechanism evolution
            assert len(update.mechanism_evolution) == 1
            evolution = update.mechanism_evolution[0]
            assert 'timestamp' in evolution
            assert 'action' in evolution
            assert 'hypothesis_id' in evolution
            assert 'confidence_level' in evolution
            assert 'evidence_strength' in evolution
            assert evolution['action'] == 'mechanism_created'
    
    @pytest.mark.asyncio
    async def test_create_new_why_map_entry(self, why_map_system):
        """Test new Why-Map entry creation"""
        hypothesis = MechanismHypothesis(
            hypothesis_id='MECHANISM_1',
            pattern_family='divergence',
            mechanism_type=MechanismType.LIQUIDITY_VACUUM,
            mechanism_description='Test mechanism',
            evidence_motifs=['evidence1', 'evidence2'],
            fails_when_conditions=['condition1'],
            confidence_level=0.8,
            evidence_strength=EvidenceStrength.STRONG,
            status=MechanismStatus.PROVISIONAL,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        evidence_evaluations = [
            {
                'hypothesis_id': 'MECHANISM_1',
                'evidence_strength': 'strong',
                'consistency_score': 0.8,
                'contradictory_evidence': [],
                'evaluation_confidence': 0.9
            }
        ]
        
        # Create new Why-Map entry
        entry = await why_map_system._create_new_why_map_entry(hypothesis, evidence_evaluations)
        
        # Verify entry
        assert isinstance(entry, WhyMapEntry)
        assert entry.family_id.startswith('FAMILY_')
        assert entry.pattern_family == 'divergence'
        assert entry.primary_mechanism == hypothesis
        assert entry.alternative_mechanisms == []
        assert len(entry.mechanism_evolution) == 1
        assert entry.cross_family_connections == []
        assert isinstance(entry.created_at, datetime)
        assert isinstance(entry.updated_at, datetime)
        
        # Verify mechanism evolution
        evolution = entry.mechanism_evolution[0]
        assert evolution['action'] == 'mechanism_created'
        assert evolution['hypothesis_id'] == 'MECHANISM_1'
        assert evolution['confidence_level'] == 0.8
        assert evolution['evidence_strength'] == 'strong'
    
    @pytest.mark.asyncio
    async def test_analyze_cross_family_connections(self, why_map_system):
        """Test cross-family connection analysis"""
        # Create test Why-Map entries
        hypothesis1 = MechanismHypothesis(
            hypothesis_id='MECHANISM_1',
            pattern_family='divergence',
            mechanism_type=MechanismType.LIQUIDITY_VACUUM,
            mechanism_description='Liquidity vacuum mechanism',
            evidence_motifs=['evidence1', 'evidence2'],
            fails_when_conditions=['condition1'],
            confidence_level=0.8,
            evidence_strength=EvidenceStrength.STRONG,
            status=MechanismStatus.PROVISIONAL,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        hypothesis2 = MechanismHypothesis(
            hypothesis_id='MECHANISM_2',
            pattern_family='volume_anomaly',
            mechanism_type=MechanismType.VOLUME_CONFIRMATION,
            mechanism_description='Volume confirmation mechanism',
            evidence_motifs=['evidence3', 'evidence4'],
            fails_when_conditions=['condition2'],
            confidence_level=0.7,
            evidence_strength=EvidenceStrength.MODERATE,
            status=MechanismStatus.PROVISIONAL,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        entry1 = WhyMapEntry(
            family_id='FAMILY_1',
            pattern_family='divergence',
            primary_mechanism=hypothesis1,
            alternative_mechanisms=[],
            mechanism_evolution=[],
            cross_family_connections=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        entry2 = WhyMapEntry(
            family_id='FAMILY_2',
            pattern_family='volume_anomaly',
            primary_mechanism=hypothesis2,
            alternative_mechanisms=[],
            mechanism_evolution=[],
            cross_family_connections=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        why_map_updates = [entry1, entry2]
        
        # Analyze cross-family connections
        analysis = await why_map_system._analyze_cross_family_connections(why_map_updates)
        
        # Verify analysis
        assert isinstance(analysis, dict)
        assert 'shared_mechanisms' in analysis
        assert 'mechanism_interactions' in analysis
        assert 'cross_family_evidence' in analysis
        assert 'mechanism_conflicts' in analysis
        assert 'connection_strength' in analysis
        
        # Verify specific values
        assert isinstance(analysis['shared_mechanisms'], list)
        assert isinstance(analysis['mechanism_interactions'], list)
        assert isinstance(analysis['cross_family_evidence'], list)
        assert isinstance(analysis['mechanism_conflicts'], list)
        assert 0.0 <= analysis['connection_strength'] <= 1.0
        
        # Verify entries were updated
        for entry in why_map_updates:
            assert isinstance(entry.cross_family_connections, list)
            assert isinstance(entry.updated_at, datetime)
    
    @pytest.mark.asyncio
    async def test_analyze_cross_family_connections_insufficient_data(self, why_map_system):
        """Test cross-family connection analysis with insufficient data"""
        # Test with less than 2 entries
        why_map_updates = []
        
        analysis = await why_map_system._analyze_cross_family_connections(why_map_updates)
        
        # Verify analysis
        assert isinstance(analysis, dict)
        assert analysis['connections'] == []
        assert analysis['shared_mechanisms'] == []
        assert analysis['interactions'] == []
    
    @pytest.mark.asyncio
    async def test_publish_why_map_results(self, why_map_system, mock_supabase_manager):
        """Test publishing Why-Map results"""
        results = {
            'mechanism_hypotheses': [{'hypothesis_id': 'MECHANISM_1'}],
            'evidence_evaluations': [{'evaluation_id': 'EVALUATION_1'}],
            'why_map_updates': [{'family_id': 'FAMILY_1'}],
            'cross_family_analysis': {'connections': []},
            'why_map_timestamp': datetime.now(timezone.utc),
            'why_map_errors': []
        }
        
        await why_map_system._publish_why_map_results(results)
        
        # Verify strand was inserted
        mock_supabase_manager.insert_strand.assert_called_once()
        call_args = mock_supabase_manager.insert_strand.call_args[0][0]
        assert call_args['kind'] == 'cil_why_map'
        assert call_args['agent_id'] == 'central_intelligence_layer'
        assert call_args['cil_team_member'] == 'why_map_system'
        assert call_args['strategic_meta_type'] == 'mechanism_analysis'
        assert call_args['resonance_score'] == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
