"""
Simple CIL Test with Real Database

Tests CIL functionality with minimal database interaction.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone

from src.intelligence.system_control.central_intelligence_layer.core.central_intelligence_agent import CentralIntelligenceAgent
from src.intelligence.system_control.central_intelligence_layer.core.strategic_pattern_miner import StrategicPatternMiner
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class TestCILSimple:
    """Simple CIL tests with real database"""
    
    @pytest_asyncio.fixture
    async def db_manager(self):
        """Get real database manager"""
        return SupabaseManager()
    
    @pytest_asyncio.fixture
    async def llm_client(self):
        """Get real LLM client"""
        return OpenRouterClient()
    
    @pytest.mark.asyncio
    async def test_cil_agent_initialization(self, db_manager, llm_client):
        """Test CIL agent can be initialized"""
        cil_agent = CentralIntelligenceAgent(db_manager, llm_client)
        
        # Test basic properties
        assert cil_agent.team_id == "central_intelligence_layer"
        assert cil_agent.agent_id == "central_intelligence_agent"
        assert "strategic_pattern_miner" in cil_agent.team_members
    
    @pytest.mark.asyncio
    async def test_strategic_pattern_miner_initialization(self, db_manager, llm_client):
        """Test strategic pattern miner can be initialized"""
        pattern_miner = StrategicPatternMiner(db_manager, llm_client)
        
        # Test basic properties
        assert pattern_miner.team_member_id == "strategic_pattern_miner"
        assert pattern_miner.cil_team == "central_intelligence_layer"
        assert pattern_miner.db_manager is not None
        assert pattern_miner.llm_client is not None
    
    @pytest.mark.asyncio
    async def test_cil_team_status(self, db_manager, llm_client):
        """Test CIL team status"""
        cil_agent = CentralIntelligenceAgent(db_manager, llm_client)
        
        status = cil_agent.get_team_status()
        
        assert status["team_id"] == "central_intelligence_layer"
        assert status["agent_id"] == "central_intelligence_agent"
        assert len(status["team_members"]) > 0
        assert "strategic_pattern_miner" in status["team_members"]
    
    @pytest.mark.asyncio
    async def test_cil_team_startup(self, db_manager, llm_client):
        """Test CIL team startup"""
        cil_agent = CentralIntelligenceAgent(db_manager, llm_client)
        
        startup_result = await cil_agent.start_cil_team()
        
        assert startup_result["success"] is True
        assert "startup_results" in startup_result
        assert "strategic_pattern_miner" in startup_result["startup_results"]
    
    @pytest.mark.asyncio
    async def test_strategic_analysis_coordination(self, db_manager, llm_client):
        """Test strategic analysis coordination"""
        cil_agent = CentralIntelligenceAgent(db_manager, llm_client)
        
        # Test coordination
        coordination_result = await cil_agent.coordinate_strategic_analysis(
            analysis_type="comprehensive"
        )
        
        assert "coordination_results" in coordination_result
        # The coordination results contain specific analysis types
        assert "confluence_analysis" in coordination_result["coordination_results"]
        assert "pattern_analysis" in coordination_result["coordination_results"]
    
    @pytest.mark.asyncio
    async def test_meta_signal_generation(self, db_manager, llm_client):
        """Test meta-signal generation"""
        cil_agent = CentralIntelligenceAgent(db_manager, llm_client)
        
        meta_signal_result = await cil_agent.generate_strategic_meta_signals()
        
        assert "meta_signals" in meta_signal_result
        assert "success" in meta_signal_result
        assert "count" in meta_signal_result
