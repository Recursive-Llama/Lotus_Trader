"""
Test CIL Team Foundation

Tests the basic functionality of the Central Intelligence Layer team foundation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.intelligence.system_control.central_intelligence_layer.core.central_intelligence_agent import CentralIntelligenceAgent
from src.intelligence.system_control.central_intelligence_layer.core.strategic_pattern_miner import StrategicPatternMiner


class TestCILTeamFoundation:
    """Test CIL team foundation functionality"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager"""
        db_manager = Mock()
        db_manager.insert_strand = AsyncMock(return_value={"success": True, "strand_id": "test_strand_123"})
        db_manager.execute_query = AsyncMock(return_value={"success": True, "data": []})
        return db_manager
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client"""
        llm_client = Mock()
        llm_client.complete = AsyncMock(return_value='{"strategic_patterns": [], "confluence_events": []}')
        return llm_client
    
    @pytest.fixture
    def cil_agent(self, mock_db_manager, mock_llm_client):
        """Create CIL agent for testing"""
        return CentralIntelligenceAgent(mock_db_manager, mock_llm_client)
    
    @pytest.fixture
    def pattern_miner(self, mock_db_manager, mock_llm_client):
        """Create strategic pattern miner for testing"""
        return StrategicPatternMiner(mock_db_manager, mock_llm_client)
    
    def test_cil_agent_initialization(self, cil_agent):
        """Test CIL agent initialization"""
        assert cil_agent.team_id == "central_intelligence_layer"
        assert cil_agent.agent_id == "central_intelligence_agent"
        assert len(cil_agent.team_members) == 1  # Only strategic_pattern_miner implemented
        assert "strategic_pattern_miner" in cil_agent.team_members
    
    def test_pattern_miner_initialization(self, pattern_miner):
        """Test strategic pattern miner initialization"""
        assert pattern_miner.team_member_id == "strategic_pattern_miner"
        assert pattern_miner.cil_team == "central_intelligence_layer"
        assert pattern_miner.db_manager is not None
        assert pattern_miner.llm_client is not None
    
    @pytest.mark.asyncio
    async def test_cil_team_startup(self, cil_agent):
        """Test CIL team startup"""
        result = await cil_agent.start_cil_team()
        
        assert result["success"] is True
        assert result["team_id"] == "central_intelligence_layer"
        assert result["agent_id"] == "central_intelligence_agent"
        assert "startup_results" in result
        assert "strategic_pattern_miner" in result["startup_results"]
    
    @pytest.mark.asyncio
    async def test_strategic_pattern_miner_analysis(self, pattern_miner):
        """Test strategic pattern miner cross-team analysis"""
        # Mock the team strands method to return test data
        with patch.object(pattern_miner, '_get_team_strands') as mock_strands, \
             patch.object(pattern_miner.context_system, 'get_relevant_context') as mock_context, \
             patch.object(pattern_miner.prompt_manager, 'get_prompt') as mock_prompt, \
             patch.object(pattern_miner.llm_client, 'complete') as mock_llm:
            
            # Mock strands data
            mock_strands.return_value = [
                {"id": "test1", "content": "test pattern", "team": "raw_data"},
                {"id": "test2", "content": "another pattern", "team": "signal_analysis"}
            ]
            
            # Mock context system
            mock_context.return_value = {"strands": [], "analysis_type": "cross_team_patterns"}
            
            # Mock prompt manager
            mock_prompt.return_value = "Test prompt template"
            
            # Mock LLM response
            mock_llm.return_value = '{"analysis_summary": "Test analysis", "strategic_patterns": []}'
            
            result = await pattern_miner.analyze_cross_team_patterns(time_window_hours=1)
            
            assert "analysis_result" in result
            assert "strategic_strands" in result
            assert "strands_analyzed" in result
            assert result["time_window_hours"] == 1
    
    @pytest.mark.asyncio
    async def test_strategic_confluence_detection(self, pattern_miner):
        """Test strategic confluence detection"""
        result = await pattern_miner.detect_strategic_confluence(confluence_threshold=0.5)
        
        assert "confluence_events" in result
        # meta_signals may not be present if no strands found
        if "error" not in result:
            assert "meta_signals" in result
        assert "threshold_used" in result
        assert result["threshold_used"] == 0.5
    
    @pytest.mark.asyncio
    async def test_meta_signal_creation(self, pattern_miner):
        """Test strategic meta-signal creation"""
        pattern_data = {
            "pattern_name": "Test Pattern",
            "pattern_type": "confluence",
            "teams_involved": ["team1", "team2"],
            "strength": 0.8,
            "confidence": 0.7,
            "description": "Test pattern description",
            "strategic_implications": "Test strategic implications"
        }
        
        result = await pattern_miner.create_strategic_meta_signal(pattern_data)
        
        assert result["success"] is True
        assert "meta_signal" in result
        assert "strand_id" in result
        assert result["meta_signal"]["kind"] == "strategic_meta_signal"
        assert result["meta_signal"]["strategic_meta_type"] == "strategic_confluence"
    
    @pytest.mark.asyncio
    async def test_cil_coordination(self, cil_agent):
        """Test CIL coordination of strategic analysis"""
        result = await cil_agent.coordinate_strategic_analysis("comprehensive")
        
        assert result["success"] is True
        assert result["analysis_type"] == "comprehensive"
        assert "coordination_results" in result
        assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_meta_signal_generation(self, cil_agent):
        """Test strategic meta-signal generation"""
        result = await cil_agent.generate_strategic_meta_signals()
        
        assert result["success"] is True
        assert "meta_signals" in result
        assert "count" in result
        assert "timestamp" in result
    
    def test_team_status(self, cil_agent):
        """Test team status reporting"""
        status = cil_agent.get_team_status()
        
        assert status["team_id"] == "central_intelligence_layer"
        assert status["agent_id"] == "central_intelligence_agent"
        assert status["total_members"] == 1
        assert status["active_members"] == 1
        assert "strategic_pattern_miner" in status["team_members"]
    
    def test_pattern_miner_team_extraction(self, pattern_miner):
        """Test team extraction from strand tags"""
        # Test valid team tags
        valid_tags = ["agent:raw_data_intelligence:test", "agent:indicator_intelligence:test"]
        for tag in valid_tags:
            team = pattern_miner._extract_team_from_tags([tag])
            assert team in ["raw_data_intelligence", "indicator_intelligence"]
        
        # Test invalid tags
        invalid_tags = ["invalid:tag", "not_agent:test"]
        for tag in invalid_tags:
            team = pattern_miner._extract_team_from_tags([tag])
            assert team is None
    
    def test_confluence_strength_calculation(self, pattern_miner):
        """Test confluence strength calculation"""
        # Test with multiple teams
        teams = {
            "team1": [{"id": "strand1"}, {"id": "strand2"}],
            "team2": [{"id": "strand3"}],
            "team3": [{"id": "strand4"}, {"id": "strand5"}]
        }
        
        strength = pattern_miner._calculate_confluence_strength(teams)
        assert 0.0 <= strength <= 1.0
        assert strength > 0.0  # Should have some confluence with 3 teams
    
    def test_market_context_extraction(self, pattern_miner):
        """Test market context extraction from strands"""
        strands = [
            {
                "symbol": "BTC",
                "timeframe": "1h",
                "session_bucket": "US",
                "regime": "high_vol"
            },
            {
                "symbol": "ETH",
                "timeframe": "4h",
                "session_bucket": "EU",
                "regime": "low_vol"
            }
        ]
        
        context = pattern_miner._extract_market_context(strands)
        
        assert "BTC" in context["symbols"]
        assert "ETH" in context["symbols"]
        assert "1h" in context["timeframes"]
        assert "4h" in context["timeframes"]
        assert "US" in context["sessions"]
        assert "EU" in context["sessions"]
        assert "high_vol" in context["regimes"]
        assert "low_vol" in context["regimes"]
    
    def test_meta_signal_type_determination(self, pattern_miner):
        """Test meta-signal type determination"""
        # Test confluence pattern
        confluence_data = {"pattern_type": "confluence"}
        signal_type = pattern_miner._determine_meta_signal_type(confluence_data)
        assert signal_type == "strategic_confluence"
        
        # Test lead-lag pattern
        lead_lag_data = {"pattern_type": "lead_lag"}
        signal_type = pattern_miner._determine_meta_signal_type(lead_lag_data)
        assert signal_type == "strategic_experiment"
        
        # Test unknown pattern
        unknown_data = {"pattern_type": "unknown"}
        signal_type = pattern_miner._determine_meta_signal_type(unknown_data)
        assert signal_type == "strategic_learning"  # Default


if __name__ == "__main__":
    pytest.main([__file__])
