"""
Test Trader Phase 2 Components

Tests for the Phase 2 Trader Team organic intelligence components:
- Execution Motif Integration
- Strategic Execution Insight Consumer
- Cross-Team Execution Integration
- Enhanced Execution Agent
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.intelligence.trader.execution_motif_integration import (
    ExecutionMotifIntegration, ExecutionMotifType, ExecutionMotifData
)
from src.intelligence.trader.strategic_execution_insight_consumer import (
    StrategicExecutionInsightConsumer, ExecutionInsightType, ExecutionInsightData
)
from src.intelligence.trader.cross_team_execution_integration import (
    CrossTeamExecutionIntegration, ExecutionConfluenceType, ExecutionConfluenceData, ExecutionLeadLagData
)
from src.intelligence.trader.enhanced_execution_agent import (
    EnhancedExecutionAgent, EnhancedExecutionResult
)


class TestExecutionMotifIntegration:
    """Test Execution Motif Integration"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()
    
    @pytest.fixture
    def motif_integration(self, mock_supabase_manager, mock_llm_client):
        return ExecutionMotifIntegration(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def sample_execution_pattern_data(self):
        return {
            'execution_type': 'market_order',
            'execution_quality': 0.85,
            'venue': 'hyperliquid',
            'symbol': 'BTC-USD',
            'slippage': 0.001,
            'fill_time': 2.5,
            'volume': 1000.0,
            'price_impact': 0.0005,
            'market_conditions': {'volatility': 0.3, 'liquidity': 0.8},
            'execution_strategy': 'twap',
            'success_rate': 0.9,
            'context': {'market_session': 'normal'}
        }
    
    @pytest.mark.asyncio
    async def test_create_execution_motif_from_pattern(self, motif_integration, sample_execution_pattern_data):
        """Test creating execution motif from pattern"""
        motif_id = await motif_integration.create_execution_motif_from_pattern(sample_execution_pattern_data)
        
        # Should return a string ID
        assert isinstance(motif_id, str)
        assert len(motif_id) > 0
    
    @pytest.mark.asyncio
    async def test_enhance_existing_execution_motif(self, motif_integration):
        """Test enhancing existing execution motif"""
        new_evidence = {
            'execution_quality': 0.9,
            'success_rate': 0.95,
            'novelty_score': 0.8
        }
        
        # Should not raise an exception
        await motif_integration.enhance_existing_execution_motif('motif_001', new_evidence)
    
    @pytest.mark.asyncio
    async def test_query_execution_motif_families(self, motif_integration):
        """Test querying execution motif families"""
        families = await motif_integration.query_execution_motif_families('market_order')
        
        # Should return a list
        assert isinstance(families, list)
    
    def test_execution_motif_type_enum(self):
        """Test ExecutionMotifType enum"""
        assert ExecutionMotifType.EXECUTION_QUALITY_PATTERN.value == "execution_quality_pattern"
        assert ExecutionMotifType.VENUE_SELECTION_PATTERN.value == "venue_selection_pattern"
        assert ExecutionMotifType.TIMING_OPTIMIZATION_PATTERN.value == "timing_optimization_pattern"
    
    def test_execution_motif_data_creation(self):
        """Test ExecutionMotifData dataclass"""
        data = ExecutionMotifData(
            motif_id='motif_001',
            motif_type=ExecutionMotifType.EXECUTION_QUALITY_PATTERN,
            pattern_invariants=['high_quality', 'fast_execution'],
            failure_conditions=['high_slippage', 'slow_fill'],
            mechanism_hypotheses=['optimal_venue_selection', 'good_timing'],
            lineage_information={'source': 'test'},
            resonance_metrics={'phi': 0.8, 'rho': 0.7},
            evidence_count=5,
            success_rate=0.9,
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        assert data.motif_id == 'motif_001'
        assert data.motif_type == ExecutionMotifType.EXECUTION_QUALITY_PATTERN
        assert data.success_rate == 0.9


class TestStrategicExecutionInsightConsumer:
    """Test Strategic Execution Insight Consumer"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()
    
    @pytest.fixture
    def insight_consumer(self, mock_supabase_manager, mock_llm_client):
        return StrategicExecutionInsightConsumer(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def sample_execution_analysis_data(self):
        return {
            'execution_type': 'market_order',
            'execution_quality': 0.8,
            'venue_performance': {'hyperliquid': 0.9, 'binance': 0.7},
            'timing_analysis': {'average_fill_time': 2.5, 'optimization_score': 0.8},
            'market_impact': 0.001,
            'confidence': 0.85,
            'success_score': 0.9
        }
    
    @pytest.mark.asyncio
    async def test_consume_cil_execution_insights(self, insight_consumer):
        """Test consuming CIL execution insights"""
        insights = await insight_consumer.consume_cil_execution_insights('market_order')
        
        # Should return a list
        assert isinstance(insights, list)
    
    @pytest.mark.asyncio
    async def test_subscribe_to_valuable_execution_meta_signals(self, insight_consumer):
        """Test subscribing to execution meta-signals"""
        signal_types = ['execution_confluence', 'execution_experiment_insight']
        
        # Should not raise an exception
        await insight_consumer.subscribe_to_valuable_execution_meta_signals(signal_types)
    
    @pytest.mark.asyncio
    async def test_contribute_to_strategic_execution_analysis(self, insight_consumer, sample_execution_analysis_data):
        """Test contributing to strategic execution analysis"""
        insight_id = await insight_consumer.contribute_to_strategic_execution_analysis(sample_execution_analysis_data)
        
        # Should return a string ID
        assert isinstance(insight_id, str)
    
    def test_execution_insight_type_enum(self):
        """Test ExecutionInsightType enum"""
        assert ExecutionInsightType.EXECUTION_CONFLUENCE.value == "execution_confluence"
        assert ExecutionInsightType.EXECUTION_EXPERIMENT_INSIGHT.value == "execution_experiment_insight"
        assert ExecutionInsightType.EXECUTION_DOCTRINE_UPDATE.value == "execution_doctrine_update"
    
    def test_execution_insight_data_creation(self):
        """Test ExecutionInsightData dataclass"""
        data = ExecutionInsightData(
            insight_id='insight_001',
            insight_type=ExecutionInsightType.EXECUTION_CONFLUENCE,
            execution_type='market_order',
            insight_content={'confluence_strength': 0.8},
            confidence_score=0.9,
            relevance_score=0.8,
            applicability_score=0.7,
            source_teams=['raw_data_intelligence', 'decision_maker'],
            created_at=datetime.now(),
            expires_at=datetime.now()
        )
        
        assert data.insight_id == 'insight_001'
        assert data.insight_type == ExecutionInsightType.EXECUTION_CONFLUENCE
        assert data.confidence_score == 0.9


class TestCrossTeamExecutionIntegration:
    """Test Cross-Team Execution Integration"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()
    
    @pytest.fixture
    def cross_team_integration(self, mock_supabase_manager, mock_llm_client):
        return CrossTeamExecutionIntegration(mock_supabase_manager, mock_llm_client)
    
    @pytest.fixture
    def sample_execution_confluence_data(self):
        return {
            'confluence_id': 'confluence_001',
            'confluence_type': 'temporal_confluence',
            'participating_teams': ['raw_data_intelligence', 'trader'],
            'confluence_strength': 0.8,
            'temporal_overlap': {'overlap_duration': 300},
            'pattern_similarities': {'execution_quality': 0.9},
            'strategic_significance': 0.85,
            'coordination_opportunities': ['temporal_coordination', 'strategy_sharing']
        }
    
    @pytest.mark.asyncio
    async def test_detect_cross_team_execution_confluence(self, cross_team_integration):
        """Test detecting cross-team execution confluence"""
        confluences = await cross_team_integration.detect_cross_team_execution_confluence("1h")
        
        # Should return a list
        assert isinstance(confluences, list)
    
    @pytest.mark.asyncio
    async def test_identify_execution_lead_lag_patterns(self, cross_team_integration):
        """Test identifying execution lead-lag patterns"""
        team_pairs = [('raw_data_intelligence', 'trader'), ('decision_maker', 'trader')]
        patterns = await cross_team_integration.identify_execution_lead_lag_patterns(team_pairs)
        
        # Should return a list
        assert isinstance(patterns, list)
    
    @pytest.mark.asyncio
    async def test_contribute_to_strategic_execution_analysis(self, cross_team_integration, sample_execution_confluence_data):
        """Test contributing to strategic execution analysis"""
        insight_id = await cross_team_integration.contribute_to_strategic_execution_analysis(sample_execution_confluence_data)
        
        # Should return a string ID
        assert isinstance(insight_id, str)
    
    def test_execution_confluence_type_enum(self):
        """Test ExecutionConfluenceType enum"""
        assert ExecutionConfluenceType.TEMPORAL_CONFLUENCE.value == "temporal_confluence"
        assert ExecutionConfluenceType.PATTERN_CONFLUENCE.value == "pattern_confluence"
        assert ExecutionConfluenceType.STRATEGY_CONFLUENCE.value == "strategy_confluence"
    
    def test_execution_confluence_data_creation(self):
        """Test ExecutionConfluenceData dataclass"""
        data = ExecutionConfluenceData(
            confluence_id='confluence_001',
            confluence_type=ExecutionConfluenceType.TEMPORAL_CONFLUENCE,
            participating_teams=['team1', 'team2'],
            confluence_strength=0.8,
            temporal_overlap={'duration': 300},
            pattern_similarities={'similarity': 0.9},
            strategic_significance=0.85,
            coordination_opportunities=['coordination1'],
            created_at=datetime.now()
        )
        
        assert data.confluence_id == 'confluence_001'
        assert data.confluence_type == ExecutionConfluenceType.TEMPORAL_CONFLUENCE
        assert data.confluence_strength == 0.8
    
    def test_execution_lead_lag_data_creation(self):
        """Test ExecutionLeadLagData dataclass"""
        data = ExecutionLeadLagData(
            pattern_id='pattern_001',
            lead_team='raw_data_intelligence',
            lag_team='trader',
            lead_lag_delay=1.5,
            consistency_score=0.8,
            correlation_strength=0.7,
            pattern_reliability=0.75,
            strategic_implications=['coordination_opportunity'],
            created_at=datetime.now()
        )
        
        assert data.pattern_id == 'pattern_001'
        assert data.lead_team == 'raw_data_intelligence'
        assert data.lag_team == 'trader'
        assert data.lead_lag_delay == 1.5


class TestEnhancedExecutionAgent:
    """Test Enhanced Execution Agent"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()
    
    @pytest.fixture
    def enhanced_agent(self, mock_supabase_manager, mock_llm_client):
        return EnhancedExecutionAgent('test_enhanced_agent', mock_supabase_manager, mock_llm_client)
    
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
    
    def test_enhanced_agent_initialization(self, enhanced_agent):
        """Test enhanced agent initialization"""
        assert enhanced_agent.agent_name == 'test_enhanced_agent'
        assert enhanced_agent.is_active is False
        assert enhanced_agent.execution_count == 0
        assert enhanced_agent.execution_motif_integration is not None
        assert enhanced_agent.strategic_execution_insight_consumer is not None
        assert enhanced_agent.cross_team_execution_integration is not None
        assert enhanced_agent.motif_contributions_count == 0
        assert enhanced_agent.cil_insights_applied_count == 0
        assert enhanced_agent.cross_team_coordinations_count == 0
        assert enhanced_agent.organic_experiments_participated == 0
    
    @pytest.mark.asyncio
    async def test_execute_with_organic_influence(self, enhanced_agent, sample_market_data, sample_approved_plan):
        """Test execution with organic influence"""
        result = await enhanced_agent.execute_with_organic_influence(sample_market_data, sample_approved_plan)
        
        # Should return EnhancedExecutionResult
        assert isinstance(result, EnhancedExecutionResult)
        assert result.execution_id is not None
        assert result.organic_influence is not None
        assert result.resonance_metrics is not None
        assert result.cil_insights_applied is not None
        assert result.motif_contributions is not None
        assert result.cross_team_coordination is not None
        assert result.uncertainty_exploration is not None
    
    @pytest.mark.asyncio
    async def test_participate_in_organic_execution_experiments(self, enhanced_agent):
        """Test participating in organic execution experiments"""
        experiment_insights = {
            'experiment_type': 'execution_timing_optimization',
            'hypothesis': 'Better timing improves execution quality',
            'expected_outcome': 'Improved execution scores'
        }
        
        result = await enhanced_agent.participate_in_organic_execution_experiments(experiment_insights)
        
        # Should return experiment results
        assert isinstance(result, dict)
        assert enhanced_agent.organic_experiments_participated == 1
    
    @pytest.mark.asyncio
    async def test_get_agent_specific_metrics(self, enhanced_agent):
        """Test getting agent-specific metrics"""
        metrics = await enhanced_agent._get_agent_specific_metrics()
        
        # Should return comprehensive metrics
        assert 'total_executions' in metrics
        assert 'success_rate' in metrics
        assert 'organic_influence_score' in metrics
        assert 'motif_contributions_count' in metrics
        assert 'cil_insights_applied_count' in metrics
        assert 'cross_team_coordinations_count' in metrics
        assert 'organic_experiments_participated' in metrics
        assert 'resonance_average' in metrics
        assert 'uncertainty_exploration_count' in metrics
    
    def test_enhanced_execution_result_creation(self):
        """Test EnhancedExecutionResult dataclass"""
        result = EnhancedExecutionResult(
            execution_id='exec_001',
            success=True,
            fill_price=50000.0,
            fill_quantity=100.0,
            success_score=0.9,
            organic_influence={'resonance_boost': 0.1},
            resonance_metrics={'phi': 0.8, 'rho': 0.7},
            cil_insights_applied=[{'insight': 'test'}],
            motif_contributions=['motif_001'],
            cross_team_coordination={'coordination': 'test'},
            uncertainty_exploration={'uncertainty': 0.3},
            execution_timestamp=datetime.now()
        )
        
        assert result.execution_id == 'exec_001'
        assert result.success is True
        assert result.fill_price == 50000.0
        assert result.fill_quantity == 100.0
        assert result.success_score == 0.9


class TestTraderPhase2Integration:
    """Test Phase 2 integration between components"""
    
    @pytest.fixture
    def mock_supabase_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_llm_client(self):
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_motif_and_insight_integration(self, mock_supabase_manager, mock_llm_client):
        """Test integration between motif and insight components"""
        # Initialize components
        motif_integration = ExecutionMotifIntegration(mock_supabase_manager, mock_llm_client)
        insight_consumer = StrategicExecutionInsightConsumer(mock_supabase_manager, mock_llm_client)
        
        # Sample execution pattern data
        execution_pattern_data = {
            'execution_type': 'market_order',
            'execution_quality': 0.8,
            'venue': 'hyperliquid',
            'success_rate': 0.9
        }
        
        # Create motif from pattern
        motif_id = await motif_integration.create_execution_motif_from_pattern(execution_pattern_data)
        
        # Consume CIL insights
        insights = await insight_consumer.consume_cil_execution_insights('market_order')
        
        # Verify both components work together
        assert isinstance(motif_id, str)
        assert isinstance(insights, list)
    
    @pytest.mark.asyncio
    async def test_cross_team_and_enhanced_agent_integration(self, mock_supabase_manager, mock_llm_client):
        """Test integration between cross-team and enhanced agent components"""
        # Initialize components
        cross_team_integration = CrossTeamExecutionIntegration(mock_supabase_manager, mock_llm_client)
        enhanced_agent = EnhancedExecutionAgent('test_agent', mock_supabase_manager, mock_llm_client)
        
        # Detect confluence patterns
        confluences = await cross_team_integration.detect_cross_team_execution_confluence("1h")
        
        # Test enhanced agent execution
        market_data = {'price': 50000.0, 'symbol': 'BTC-USD'}
        approved_plan = {'plan_id': 'plan_001', 'execution_type': 'market_order'}
        
        result = await enhanced_agent.execute_with_organic_influence(market_data, approved_plan)
        
        # Verify integration
        assert isinstance(confluences, list)
        assert isinstance(result, EnhancedExecutionResult)
        assert result.organic_influence is not None
    
    @pytest.mark.asyncio
    async def test_full_phase2_integration(self, mock_supabase_manager, mock_llm_client):
        """Test full Phase 2 integration"""
        # Initialize all Phase 2 components
        motif_integration = ExecutionMotifIntegration(mock_supabase_manager, mock_llm_client)
        insight_consumer = StrategicExecutionInsightConsumer(mock_supabase_manager, mock_llm_client)
        cross_team_integration = CrossTeamExecutionIntegration(mock_supabase_manager, mock_llm_client)
        enhanced_agent = EnhancedExecutionAgent('full_test_agent', mock_supabase_manager, mock_llm_client)
        
        # Test motif creation
        motif_id = await motif_integration.create_execution_motif_from_pattern({
            'execution_type': 'market_order',
            'execution_quality': 0.8
        })
        
        # Test insight consumption
        insights = await insight_consumer.consume_cil_execution_insights('market_order')
        
        # Test confluence detection
        confluences = await cross_team_integration.detect_cross_team_execution_confluence("1h")
        
        # Test enhanced agent execution
        result = await enhanced_agent.execute_with_organic_influence(
            {'price': 50000.0}, 
            {'plan_id': 'plan_001', 'execution_type': 'market_order'}
        )
        
        # Verify all components work together
        assert isinstance(motif_id, str)
        assert isinstance(insights, list)
        assert isinstance(confluences, list)
        assert isinstance(result, EnhancedExecutionResult)
        assert result.organic_influence is not None
        assert result.resonance_metrics is not None
        assert result.cil_insights_applied is not None
        assert result.motif_contributions is not None
        assert result.cross_team_coordination is not None
        assert result.uncertainty_exploration is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
