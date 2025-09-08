"""
Test Trader Phase 3 Components

Tests for the Phase 3 Trader Team organic intelligence components:
- Execution Doctrine Integration
- Enhanced Trader Capabilities
- Natural CIL Execution Influence
- Complete Organic Intelligence Integration
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.intelligence.trader.execution_doctrine_integration import (
    ExecutionDoctrineIntegration, ExecutionDoctrineType, ExecutionDoctrineData,
    DoctrineContraindicationType, DoctrineContraindicationData
)
from src.intelligence.trader.enhanced_trader_capabilities import (
    EnhancedTraderCapabilities, OrganicExecutionCapabilities, OrganicExecutionIntelligence
)
from src.intelligence.trader.natural_cil_execution_influence import (
    NaturalCILExecutionInfluence, NaturalInfluenceType, NaturalInfluenceData, OrganicCoordinationState
)


class TestExecutionDoctrineIntegration:
    """Test Execution Doctrine Integration"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()
    
    @pytest.fixture
    def doctrine_integration(self, mock_supabase_manager, mock_llm_client):
        return ExecutionDoctrineIntegration(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def sample_execution_evidence(self):
        return {
            'execution_type': 'market_order',
            'execution_quality': 0.85,
            'success_rate': 0.9,
            'confidence': 0.8,
            'novelty_score': 0.7,
            'pattern_strength': 0.8,
            'generality_score': 0.6,
            'innovation_score': 0.7
        }
    
    @pytest.fixture
    def sample_proposed_experiment(self):
        return {
            'experiment_type': 'execution_timing_optimization',
            'hypothesis': 'Better timing improves execution quality',
            'expected_outcome': 'Improved execution scores',
            'risk_level': 'low'
        }
    
    @pytest.mark.asyncio
    async def test_query_relevant_execution_doctrine(self, doctrine_integration):
        """Test querying relevant execution doctrine"""
        doctrine_guidance = await doctrine_integration.query_relevant_execution_doctrine('market_order')
        
        # Should return a dict with doctrine guidance
        assert isinstance(doctrine_guidance, dict)
        assert 'execution_type' in doctrine_guidance
        assert 'applicable_doctrine' in doctrine_guidance
        assert 'contraindications' in doctrine_guidance
        assert 'doctrine_confidence' in doctrine_guidance
        assert 'recommendation_score' in doctrine_guidance
    
    @pytest.mark.asyncio
    async def test_contribute_to_execution_doctrine(self, doctrine_integration, sample_execution_evidence):
        """Test contributing to execution doctrine"""
        contribution_id = await doctrine_integration.contribute_to_execution_doctrine(sample_execution_evidence)
        
        # Should return a string ID
        assert isinstance(contribution_id, str)
    
    @pytest.mark.asyncio
    async def test_check_execution_doctrine_contraindications(self, doctrine_integration, sample_proposed_experiment):
        """Test checking execution doctrine contraindications"""
        is_contraindicated = await doctrine_integration.check_execution_doctrine_contraindications(sample_proposed_experiment)
        
        # Should return a boolean
        assert isinstance(is_contraindicated, bool)
    
    def test_execution_doctrine_type_enum(self):
        """Test ExecutionDoctrineType enum"""
        assert ExecutionDoctrineType.EXECUTION_STRATEGY_DOCTRINE.value == "execution_strategy_doctrine"
        assert ExecutionDoctrineType.VENUE_SELECTION_DOCTRINE.value == "venue_selection_doctrine"
        assert ExecutionDoctrineType.TIMING_OPTIMIZATION_DOCTRINE.value == "timing_optimization_doctrine"
    
    def test_execution_doctrine_data_creation(self):
        """Test ExecutionDoctrineData dataclass"""
        data = ExecutionDoctrineData(
            doctrine_id='doctrine_001',
            doctrine_type=ExecutionDoctrineType.EXECUTION_STRATEGY_DOCTRINE,
            doctrine_content={'strategy': 'twap'},
            evidence_count=10,
            success_rate=0.9,
            applicability_score=0.8,
            resonance_metrics={'phi': 0.8, 'rho': 0.7},
            contraindications=[],
            evolution_history=[],
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        assert data.doctrine_id == 'doctrine_001'
        assert data.doctrine_type == ExecutionDoctrineType.EXECUTION_STRATEGY_DOCTRINE
        assert data.success_rate == 0.9
    
    def test_doctrine_contraindication_type_enum(self):
        """Test DoctrineContraindicationType enum"""
        assert DoctrineContraindicationType.STRATEGY_CONTRAINDICATION.value == "strategy_contraindication"
        assert DoctrineContraindicationType.VENUE_CONTRAINDICATION.value == "venue_contraindication"
        assert DoctrineContraindicationType.TIMING_CONTRAINDICATION.value == "timing_contraindication"
    
    def test_doctrine_contraindication_data_creation(self):
        """Test DoctrineContraindicationData dataclass"""
        data = DoctrineContraindicationData(
            contraindication_id='contra_001',
            contraindication_type=DoctrineContraindicationType.STRATEGY_CONTRAINDICATION,
            failure_conditions=['high_slippage', 'slow_fill'],
            failure_evidence=[{'slippage': 0.02}],
            severity_score=0.8,
            confidence_level=0.9,
            mitigation_strategies=['reduce_order_size', 'use_twap'],
            created_at=datetime.now()
        )
        
        assert data.contraindication_id == 'contra_001'
        assert data.contraindication_type == DoctrineContraindicationType.STRATEGY_CONTRAINDICATION
        assert data.severity_score == 0.8


class TestEnhancedTraderCapabilities:
    """Test Enhanced Trader Capabilities"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()
    
    @pytest.fixture
    def enhanced_capabilities(self, mock_supabase_manager, mock_llm_client):
        return EnhancedTraderCapabilities('test_enhanced_agent', mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def sample_market_data(self):
        return {
            'symbol': 'BTC-USD',
            'price': 50000.0,
            'volume': 1000.0,
            'timestamp': datetime.now().isoformat()
        }
    
    @pytest.fixture
    def sample_approved_plan(self):
        return {
            'plan_id': 'plan_001',
            'symbol': 'BTC-USD',
            'side': 'buy',
            'quantity': 100.0,
            'execution_score': 0.8,
            'risk_score': 0.3,
            'execution_type': 'market_order'
        }
    
    @pytest.fixture
    def sample_experiment_insights(self):
        return {
            'experiment_type': 'execution_timing_optimization',
            'hypothesis': 'Better timing improves execution quality',
            'expected_outcome': 'Improved execution scores',
            'risk_level': 'low'
        }
    
    def test_enhanced_capabilities_initialization(self, enhanced_capabilities):
        """Test enhanced capabilities initialization"""
        assert enhanced_capabilities.agent_name == 'test_enhanced_agent'
        assert enhanced_capabilities.enhanced_execution_agent is not None
        assert enhanced_capabilities.execution_doctrine_integration is not None
        assert enhanced_capabilities.organic_capabilities is not None
        assert enhanced_capabilities.organic_capabilities.doctrine_integration is True
        assert enhanced_capabilities.organic_capabilities.natural_cil_influence is True
        assert enhanced_capabilities.organic_capabilities.seamless_coordination is True
    
    @pytest.mark.asyncio
    async def test_demonstrate_full_organic_execution_intelligence(self, enhanced_capabilities, sample_market_data, sample_approved_plan):
        """Test demonstrating full organic execution intelligence"""
        organic_intelligence = await enhanced_capabilities.demonstrate_full_organic_execution_intelligence(
            sample_market_data, sample_approved_plan
        )
        
        # Should return OrganicExecutionIntelligence
        assert isinstance(organic_intelligence, OrganicExecutionIntelligence)
        assert organic_intelligence.execution_capabilities is not None
        assert organic_intelligence.doctrine_guidance is not None
        assert organic_intelligence.cil_influence is not None
        assert organic_intelligence.coordination_state is not None
        assert organic_intelligence.intelligence_flow is not None
        assert organic_intelligence.resonance_metrics is not None
        assert organic_intelligence.uncertainty_analysis is not None
        assert organic_intelligence.motif_contributions is not None
        assert organic_intelligence.cross_team_insights is not None
        assert organic_intelligence.strategic_insights is not None
    
    @pytest.mark.asyncio
    async def test_participate_in_organic_execution_experiments_enhanced(self, enhanced_capabilities, sample_experiment_insights):
        """Test participating in organic execution experiments with enhanced capabilities"""
        result = await enhanced_capabilities.participate_in_organic_execution_experiments_enhanced(sample_experiment_insights)
        
        # Should return experiment results
        assert isinstance(result, dict)
        assert 'experiment_results' in result
        assert 'doctrine_contribution' in result
        assert 'intelligence_impact' in result
        assert 'learning_insights' in result
    
    @pytest.mark.asyncio
    async def test_get_organic_intelligence_status(self, enhanced_capabilities):
        """Test getting organic intelligence status"""
        status = await enhanced_capabilities.get_organic_intelligence_status()
        
        # Should return comprehensive status
        assert isinstance(status, dict)
        assert 'agent_name' in status
        assert 'organic_capabilities' in status
        assert 'agent_metrics' in status
        assert 'doctrine_integration' in status
        assert 'intelligence_flow' in status
        assert 'capability_evolution_count' in status
        assert 'intelligence_history_count' in status
    
    def test_organic_execution_capabilities_creation(self):
        """Test OrganicExecutionCapabilities dataclass"""
        capabilities = OrganicExecutionCapabilities(
            doctrine_integration=True,
            natural_cil_influence=True,
            seamless_coordination=True,
            organic_intelligence_flow=True,
            end_to_end_integration=True,
            resonance_driven_evolution=True,
            uncertainty_driven_curiosity=True,
            motif_creation_evolution=True,
            cross_team_awareness=True,
            strategic_insight_consumption=True
        )
        
        assert capabilities.doctrine_integration is True
        assert capabilities.natural_cil_influence is True
        assert capabilities.seamless_coordination is True
        assert capabilities.organic_intelligence_flow is True
        assert capabilities.end_to_end_integration is True
    
    def test_organic_execution_intelligence_creation(self):
        """Test OrganicExecutionIntelligence dataclass"""
        capabilities = OrganicExecutionCapabilities(
            doctrine_integration=True,
            natural_cil_influence=True,
            seamless_coordination=True,
            organic_intelligence_flow=True,
            end_to_end_integration=True,
            resonance_driven_evolution=True,
            uncertainty_driven_curiosity=True,
            motif_creation_evolution=True,
            cross_team_awareness=True,
            strategic_insight_consumption=True
        )
        
        intelligence = OrganicExecutionIntelligence(
            execution_capabilities=capabilities,
            doctrine_guidance={'confidence': 0.8},
            cil_influence={'resonance_boost': 0.1},
            coordination_state={'coordination': True},
            intelligence_flow={'flow': True},
            resonance_metrics={'phi': 0.8, 'rho': 0.7, 'theta': 0.75},
            uncertainty_analysis={'uncertainty': 0.3},
            motif_contributions=['motif_001'],
            cross_team_insights=[{'insight': 'test'}],
            strategic_insights=[{'strategic': 'test'}],
            timestamp=datetime.now()
        )
        
        assert intelligence.execution_capabilities is not None
        assert intelligence.doctrine_guidance is not None
        assert intelligence.cil_influence is not None
        assert intelligence.coordination_state is not None
        assert intelligence.intelligence_flow is not None
        assert intelligence.resonance_metrics is not None
        assert intelligence.uncertainty_analysis is not None
        assert intelligence.motif_contributions is not None
        assert intelligence.cross_team_insights is not None
        assert intelligence.strategic_insights is not None


class TestNaturalCILExecutionInfluence:
    """Test Natural CIL Execution Influence"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()
    
    @pytest.fixture
    def natural_cil_influence(self, mock_supabase_manager, mock_llm_client):
        return NaturalCILExecutionInfluence(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def sample_execution_context(self):
        return {
            'resonance_metrics': {'phi': 0.8, 'rho': 0.7, 'theta': 0.75},
            'uncertainty_analysis': {'overall_uncertainty': 0.3},
            'motif_integration': {'motif_families': ['family1', 'family2']},
            'cil_insights': [{'insight': 'test1'}, {'insight': 'test2'}],
            'cross_team_insights': {'confluence_patterns': ['pattern1']},
            'doctrine_guidance': {'confidence': 0.8}
        }
    
    @pytest.fixture
    def sample_execution_plan(self):
        return {
            'plan_id': 'plan_001',
            'execution_type': 'market_order',
            'target_price': 50000.0,
            'quantity': 100.0
        }
    
    @pytest.mark.asyncio
    async def test_establish_natural_cil_influence(self, natural_cil_influence, sample_execution_context):
        """Test establishing natural CIL influence"""
        influence_network = await natural_cil_influence.establish_natural_cil_influence(
            'test_agent', sample_execution_context
        )
        
        # Should return influence network
        assert isinstance(influence_network, dict)
        assert 'agent_name' in influence_network
        assert 'influence_opportunities' in influence_network
        assert 'resonance_influence' in influence_network
        assert 'uncertainty_influence' in influence_network
        assert 'motif_influence' in influence_network
        assert 'strategic_influence' in influence_network
        assert 'cross_team_influence' in influence_network
        assert 'doctrine_influence' in influence_network
        assert 'natural_influence_score' in influence_network
        assert 'seamless_coordination_ready' in influence_network
    
    @pytest.mark.asyncio
    async def test_coordinate_organic_execution_flow(self, natural_cil_influence, sample_execution_context):
        """Test coordinating organic execution flow"""
        execution_agents = ['agent1', 'agent2', 'agent3']
        coordination_state = await natural_cil_influence.coordinate_organic_execution_flow(
            execution_agents, sample_execution_context
        )
        
        # Should return OrganicCoordinationState
        assert isinstance(coordination_state, OrganicCoordinationState)
        assert coordination_state.coordination_id is not None
        assert coordination_state.participating_agents == execution_agents
        assert coordination_state.coordination_type == 'organic_execution_flow'
        assert coordination_state.coordination_strength is not None
        assert coordination_state.natural_influence_patterns is not None
        assert coordination_state.organic_flow_coordination is not None
        assert coordination_state.seamless_integration_score is not None
    
    @pytest.mark.asyncio
    async def test_apply_natural_influence_to_execution(self, natural_cil_influence, sample_execution_plan):
        """Test applying natural influence to execution"""
        natural_influence = {
            'resonance_influence': {'influence_strength': 0.8},
            'uncertainty_influence': {'influence_strength': 0.6},
            'motif_influence': {'influence_strength': 0.7},
            'strategic_influence': {'influence_strength': 0.9},
            'cross_team_influence': {'influence_strength': 0.8},
            'doctrine_influence': {'influence_strength': 0.7},
            'natural_influence_score': 0.75
        }
        
        enhanced_plan = await natural_cil_influence.apply_natural_influence_to_execution(
            sample_execution_plan, natural_influence
        )
        
        # Should return enhanced execution plan
        assert isinstance(enhanced_plan, dict)
        assert enhanced_plan['natural_influence_applied'] is True
        assert enhanced_plan['natural_influence_score'] == 0.75
        assert enhanced_plan['seamless_coordination'] is True
        assert enhanced_plan['organic_intelligence_enhanced'] is True
    
    def test_natural_influence_type_enum(self):
        """Test NaturalInfluenceType enum"""
        assert NaturalInfluenceType.RESONANCE_INFLUENCE.value == "resonance_influence"
        assert NaturalInfluenceType.UNCERTAINTY_INFLUENCE.value == "uncertainty_influence"
        assert NaturalInfluenceType.MOTIF_INFLUENCE.value == "motif_influence"
        assert NaturalInfluenceType.STRATEGIC_INFLUENCE.value == "strategic_influence"
        assert NaturalInfluenceType.CROSS_TEAM_INFLUENCE.value == "cross_team_influence"
        assert NaturalInfluenceType.DOCTRINE_INFLUENCE.value == "doctrine_influence"
    
    def test_natural_influence_data_creation(self):
        """Test NaturalInfluenceData dataclass"""
        data = NaturalInfluenceData(
            influence_id='influence_001',
            influence_type=NaturalInfluenceType.RESONANCE_INFLUENCE,
            influence_strength=0.8,
            influence_source='cil',
            influence_target='trader_agent',
            influence_mechanism='resonance_enhancement',
            coordination_effect={'score_boost': 0.2},
            organic_flow_state={'naturally_enhanced': True},
            created_at=datetime.now()
        )
        
        assert data.influence_id == 'influence_001'
        assert data.influence_type == NaturalInfluenceType.RESONANCE_INFLUENCE
        assert data.influence_strength == 0.8
        assert data.influence_source == 'cil'
        assert data.influence_target == 'trader_agent'
    
    def test_organic_coordination_state_creation(self):
        """Test OrganicCoordinationState dataclass"""
        influence_data = NaturalInfluenceData(
            influence_id='influence_001',
            influence_type=NaturalInfluenceType.RESONANCE_INFLUENCE,
            influence_strength=0.8,
            influence_source='cil',
            influence_target='trader_agent',
            influence_mechanism='resonance_enhancement',
            coordination_effect={'score_boost': 0.2},
            organic_flow_state={'naturally_enhanced': True},
            created_at=datetime.now()
        )
        
        coordination_state = OrganicCoordinationState(
            coordination_id='coordination_001',
            participating_agents=['agent1', 'agent2'],
            coordination_type='organic_execution_flow',
            coordination_strength=0.8,
            natural_influence_patterns=[influence_data],
            organic_flow_coordination={'seamless': True},
            seamless_integration_score=0.9,
            timestamp=datetime.now()
        )
        
        assert coordination_state.coordination_id == 'coordination_001'
        assert coordination_state.participating_agents == ['agent1', 'agent2']
        assert coordination_state.coordination_type == 'organic_execution_flow'
        assert coordination_state.coordination_strength == 0.8
        assert len(coordination_state.natural_influence_patterns) == 1
        assert coordination_state.organic_flow_coordination is not None
        assert coordination_state.seamless_integration_score == 0.9


class TestTraderPhase3Integration:
    """Test Phase 3 integration between components"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_doctrine_and_capabilities_integration(self, mock_supabase_manager, mock_llm_client):
        """Test integration between doctrine and capabilities components"""
        # Initialize components
        doctrine_integration = ExecutionDoctrineIntegration(mock_supabase_manager, mock_llm_client)
        enhanced_capabilities = EnhancedTraderCapabilities('test_agent', mock_supabase_manager, mock_llm_client)
        
        # Test doctrine querying
        doctrine_guidance = await doctrine_integration.query_relevant_execution_doctrine('market_order')
        
        # Test enhanced capabilities
        market_data = {'price': 50000.0, 'symbol': 'BTC-USD'}
        approved_plan = {'plan_id': 'plan_001', 'execution_type': 'market_order'}
        
        organic_intelligence = await enhanced_capabilities.demonstrate_full_organic_execution_intelligence(
            market_data, approved_plan
        )
        
        # Verify integration
        assert isinstance(doctrine_guidance, dict)
        assert isinstance(organic_intelligence, OrganicExecutionIntelligence)
        assert organic_intelligence.execution_capabilities is not None
    
    @pytest.mark.asyncio
    async def test_natural_influence_and_capabilities_integration(self, mock_supabase_manager, mock_llm_client):
        """Test integration between natural influence and capabilities components"""
        # Initialize components
        natural_cil_influence = NaturalCILExecutionInfluence(mock_supabase_manager, mock_llm_client)
        enhanced_capabilities = EnhancedTraderCapabilities('test_agent', mock_supabase_manager, mock_llm_client)
        
        # Test natural influence establishment
        execution_context = {
            'resonance_metrics': {'phi': 0.8},
            'uncertainty_analysis': {'overall_uncertainty': 0.3},
            'motif_integration': {'motif_families': ['family1']},
            'cil_insights': [{'insight': 'test'}],
            'cross_team_insights': {'confluence_patterns': ['pattern1']},
            'doctrine_guidance': {'confidence': 0.8}
        }
        
        influence_network = await natural_cil_influence.establish_natural_cil_influence('test_agent', execution_context)
        
        # Test enhanced capabilities
        market_data = {'price': 50000.0, 'symbol': 'BTC-USD'}
        approved_plan = {'plan_id': 'plan_001', 'execution_type': 'market_order'}
        
        organic_intelligence = await enhanced_capabilities.demonstrate_full_organic_execution_intelligence(
            market_data, approved_plan
        )
        
        # Verify integration
        assert isinstance(influence_network, dict)
        assert isinstance(organic_intelligence, OrganicExecutionIntelligence)
        assert influence_network['seamless_coordination_ready'] is True
    
    @pytest.mark.asyncio
    async def test_full_phase3_integration(self, mock_supabase_manager, mock_llm_client):
        """Test full Phase 3 integration"""
        # Initialize all Phase 3 components
        doctrine_integration = ExecutionDoctrineIntegration(mock_supabase_manager, mock_llm_client)
        enhanced_capabilities = EnhancedTraderCapabilities('full_test_agent', mock_supabase_manager, mock_llm_client)
        natural_cil_influence = NaturalCILExecutionInfluence(mock_supabase_manager, mock_llm_client)
        
        # Test doctrine integration
        doctrine_guidance = await doctrine_integration.query_relevant_execution_doctrine('market_order')
        
        # Test natural influence establishment
        execution_context = {
            'resonance_metrics': {'phi': 0.8, 'rho': 0.7, 'theta': 0.75},
            'uncertainty_analysis': {'overall_uncertainty': 0.3},
            'motif_integration': {'motif_families': ['family1', 'family2']},
            'cil_insights': [{'insight': 'test1'}, {'insight': 'test2'}],
            'cross_team_insights': {'confluence_patterns': ['pattern1']},
            'doctrine_guidance': doctrine_guidance
        }
        
        influence_network = await natural_cil_influence.establish_natural_cil_influence('full_test_agent', execution_context)
        
        # Test enhanced capabilities
        market_data = {'price': 50000.0, 'symbol': 'BTC-USD'}
        approved_plan = {'plan_id': 'plan_001', 'execution_type': 'market_order'}
        
        organic_intelligence = await enhanced_capabilities.demonstrate_full_organic_execution_intelligence(
            market_data, approved_plan
        )
        
        # Test organic coordination
        execution_agents = ['agent1', 'agent2', 'agent3']
        coordination_state = await natural_cil_influence.coordinate_organic_execution_flow(
            execution_agents, execution_context
        )
        
        # Verify full integration
        assert isinstance(doctrine_guidance, dict)
        assert isinstance(influence_network, dict)
        assert isinstance(organic_intelligence, OrganicExecutionIntelligence)
        assert isinstance(coordination_state, OrganicCoordinationState)
        
        # Verify organic intelligence state
        assert organic_intelligence.execution_capabilities is not None
        assert organic_intelligence.doctrine_guidance is not None
        assert organic_intelligence.cil_influence is not None
        assert organic_intelligence.coordination_state is not None
        assert organic_intelligence.intelligence_flow is not None
        assert organic_intelligence.resonance_metrics is not None
        assert organic_intelligence.uncertainty_analysis is not None
        assert organic_intelligence.motif_contributions is not None
        assert organic_intelligence.cross_team_insights is not None
        assert organic_intelligence.strategic_insights is not None
        
        # Verify coordination state
        assert coordination_state.coordination_id is not None
        assert coordination_state.participating_agents == execution_agents
        assert coordination_state.coordination_type == 'organic_execution_flow'
        assert coordination_state.coordination_strength is not None
        assert coordination_state.natural_influence_patterns is not None
        assert coordination_state.organic_flow_coordination is not None
        assert coordination_state.seamless_integration_score is not None
        
        # Verify natural influence network
        assert influence_network['seamless_coordination_ready'] is True
        assert influence_network['natural_influence_score'] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
