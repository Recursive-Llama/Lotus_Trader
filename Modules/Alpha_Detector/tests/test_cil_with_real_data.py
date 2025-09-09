"""
Test CIL Team with Real Database Data

Creates actual test data in the database and tests CIL functionality with real data.
Much simpler than complex mocking!
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timezone
import json

from src.intelligence.system_control.central_intelligence_layer.central_intelligence_agent import CentralIntelligenceAgent
from src.intelligence.system_control.central_intelligence_layer.strategic_pattern_miner import StrategicPatternMiner
from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient


class TestCILWithRealData:
    """Test CIL team with real database data"""
    
    @pytest_asyncio.fixture
    async def db_manager(self):
        """Get real database manager"""
        return SupabaseManager()
    
    @pytest_asyncio.fixture
    async def llm_client(self):
        """Get real LLM client"""
        return OpenRouterClient()
    
    @pytest_asyncio.fixture
    async def test_strands(self, db_manager):
        """Create test strands in the database"""
        # Create some test strands from different teams
        test_strands = [
            {
                "content": "BTC showing strong bullish momentum with volume spike",
                "kind": "signal",
                "symbol": "BTC",
                "timeframe": "1m",
                "team_member": "raw_data_intelligence",
                "tags": ["BTC", "bullish", "volume", "momentum"],
                "sig_sigma": 0.8,
                "sig_confidence": 0.7,
                "sig_direction": "long",
                "module_intelligence": {
                    "pattern_type": "volume_breakout",
                    "team": "raw_data_intelligence"
                }
            },
            {
                "content": "ETH RSI divergence detected on 5m timeframe",
                "kind": "signal",
                "symbol": "ETH", 
                "timeframe": "5m",
                "team_member": "signal_analysis",
                "tags": ["ETH", "RSI", "divergence", "5m"],
                "sig_sigma": 0.6,
                "sig_confidence": 0.8,
                "sig_direction": "short",
                "module_intelligence": {
                    "pattern_type": "rsi_divergence",
                    "team": "signal_analysis"
                }
            },
            {
                "content": "SOL showing similar pattern to BTC breakout",
                "kind": "signal",
                "symbol": "SOL",
                "timeframe": "1m",
                "team_member": "pattern_recognition",
                "tags": ["SOL", "BTC", "correlation", "breakout"],
                "sig_sigma": 0.7,
                "sig_confidence": 0.6,
                "sig_direction": "long",
                "module_intelligence": {
                    "pattern_type": "correlation_breakout",
                    "team": "pattern_recognition"
                }
            }
        ]
        
        # Insert test strands into database
        inserted_strands = []
        for strand in test_strands:
            result = await db_manager.insert_strand(strand)
            if result.get("success"):
                inserted_strands.append(result.get("strand_id"))
        
        yield inserted_strands
        
        # Cleanup: Remove test strands
        for strand_id in inserted_strands:
            await db_manager.delete_strand(strand_id)
    
    @pytest.mark.asyncio
    async def test_cil_agent_with_real_data(self, db_manager, llm_client, test_strands):
        """Test CIL agent with real database data"""
        # Initialize CIL agent
        cil_agent = CentralIntelligenceAgent(db_manager, llm_client)
        
        # Test startup
        startup_result = await cil_agent.start_cil_team()
        assert startup_result["success"] is True
        assert "strategic_pattern_miner" in startup_result["startup_results"]
        
        # Test team status
        status = cil_agent.get_team_status()
        assert status["team_id"] == "central_intelligence_layer"
        assert len(status["team_members"]) > 0
    
    @pytest.mark.asyncio
    async def test_strategic_pattern_miner_with_real_data(self, db_manager, llm_client, test_strands):
        """Test strategic pattern miner with real database data"""
        # Initialize pattern miner
        pattern_miner = StrategicPatternMiner(db_manager, llm_client)
        
        # Test cross-team pattern analysis
        result = await pattern_miner.analyze_cross_team_patterns(time_window_hours=1)
        
        # Should find our test strands
        assert "error" not in result
        assert "strands_analyzed" in result
        assert result["strands_analyzed"] >= len(test_strands)
        
        # Test confluence detection
        confluence_result = await pattern_miner.detect_strategic_confluence(confluence_threshold=0.5)
        
        assert "confluence_events" in confluence_result
        assert "strands_analyzed" in confluence_result
        assert confluence_result["strands_analyzed"] >= len(test_strands)
    
    @pytest.mark.asyncio
    async def test_meta_signal_creation_with_real_data(self, db_manager, llm_client, test_strands):
        """Test meta-signal creation with real data"""
        pattern_miner = StrategicPatternMiner(db_manager, llm_client)
        
        # Create a test pattern for meta-signal
        test_pattern = {
            "pattern_type": "confluence",
            "symbols": ["BTC", "ETH", "SOL"],
            "timeframe": "1m",
            "strength": 0.8,
            "description": "Multi-asset bullish momentum confluence"
        }
        
        # Create meta-signal
        result = await pattern_miner.create_strategic_meta_signal(test_pattern)
        
        assert "success" in result
        if result["success"]:
            # Clean up the created meta-signal
            strand_id = result.get("strand_id")
            if strand_id:
                await db_manager.delete_strand(strand_id)
    
    @pytest.mark.asyncio
    async def test_cil_coordination_with_real_data(self, db_manager, llm_client, test_strands):
        """Test CIL coordination with real data"""
        cil_agent = CentralIntelligenceAgent(db_manager, llm_client)
        
        # Test coordination
        coordination_result = await cil_agent.coordinate_strategic_analysis(
            analysis_type="comprehensive"
        )
        
        assert "coordination_results" in coordination_result
        assert "strategic_pattern_miner" in coordination_result["coordination_results"]
