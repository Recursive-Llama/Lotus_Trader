"""
Test organized module structure
Tests the new organized module structure with proper imports
"""

import pytest
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any
import logging

# Import from the new organized structure
from src.intelligence.raw_data_intelligence.raw_data_intelligence_agent import RawDataIntelligenceAgent
from src.intelligence.raw_data_intelligence.analyzers.divergence_detector import RawDataDivergenceDetector
from src.intelligence.raw_data_intelligence.analyzers.volume_analyzer import VolumePatternAnalyzer
from src.intelligence.raw_data_intelligence.coordination.team_coordination import TeamCoordination
from src.intelligence.raw_data_intelligence.coordination.llm_coordination import LLMCoordination
from src.intelligence.raw_data_intelligence.integration.resonance_integration import ResonanceIntegration

from src.intelligence.universal_learning.universal_learning_system import UniversalLearningSystem
from src.intelligence.universal_learning.module_specific_scoring import ModuleSpecificScoring
from src.intelligence.universal_learning.engines.mathematical_resonance_engine import MathematicalResonanceEngine
from src.intelligence.universal_learning.pipeline.learning_pipeline import LearningPipeline

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestOrganizedModules:
    """Test the organized module structure"""
    
    def test_imports_work(self):
        """Test that all imports work correctly"""
        # This test will pass if all imports above work
        assert True
        logger.info("✅ All imports working correctly")
    
    def test_raw_data_intelligence_components(self):
        """Test raw data intelligence components can be instantiated"""
        try:
            # Test analyzers
            divergence_detector = RawDataDivergenceDetector()
            volume_analyzer = VolumePatternAnalyzer()
            
            # Test coordination
            team_coordination = TeamCoordination()
            
            logger.info("✅ Raw data intelligence components instantiated successfully")
            assert True
        except Exception as e:
            logger.error(f"❌ Failed to instantiate raw data intelligence components: {e}")
            assert False, f"Failed to instantiate components: {e}"
    
    def test_universal_learning_components(self):
        """Test universal learning components can be instantiated"""
        try:
            # Test engines
            resonance_engine = MathematicalResonanceEngine()
            
            # Test scoring
            module_scoring = ModuleSpecificScoring()
            
            logger.info("✅ Universal learning components instantiated successfully")
            assert True
        except Exception as e:
            logger.error(f"❌ Failed to instantiate universal learning components: {e}")
            assert False, f"Failed to instantiate components: {e}"
    
    def test_database_connection(self):
        """Test database connection works"""
        try:
            db = SupabaseManager()
            logger.info("✅ Database connection successful")
            assert True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            assert False, f"Database connection failed: {e}"
    
    def test_llm_connection(self):
        """Test LLM connection works"""
        try:
            llm_client = OpenRouterClient()
            logger.info("✅ LLM connection successful")
            assert True
        except Exception as e:
            logger.error(f"❌ LLM connection failed: {e}")
            assert False, f"LLM connection failed: {e}"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
