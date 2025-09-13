"""
Simple CIL Flow Test

Quick test to verify the clean CIL module works.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

# Add project root to path
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁')
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/src')

from clean_cil_module import CleanCILModule
from Modules.Alpha_Detector.src.utils.supabase_manager import SupabaseManager
from Modules.Alpha_Detector.src.intelligence.llm_integration.llm_client import LLMClientManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_simple_cil():
    """Simple test of CIL module"""
    try:
        logger.info("🧪 Testing Simple CIL Flow")
        
        # Initialize components
        supabase_manager = SupabaseManager()
        
        # Initialize LLM client manager
        llm_config = {
            'openai': {'api_key': 'test_key', 'model': 'gpt-4o-mini'},
            'anthropic': {'api_key': 'test_key', 'model': 'claude-3-haiku-20240307'}
        }
        llm_client = LLMClientManager(llm_config)
        
        # Initialize CIL
        cil = CleanCILModule(supabase_manager, llm_client)
        
        logger.info("✅ CIL module initialized")
        
        # Test module status
        status = await cil.get_module_status()
        logger.info(f"📊 CIL Status: {status}")
        
        # Test with a simple pattern strand
        test_pattern = {
            'id': f"simple_test_{int(datetime.now().timestamp())}",
            'kind': 'pattern',
            'module': 'alpha',
            'agent_id': 'raw_data_intelligence',
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'content': {
                'pattern_type': 'test_pattern',
                'confidence': 0.8,
                'pattern_group': {
                    'asset': 'BTCUSDT',
                    'timeframe': '1h',
                    'group_type': 'single_single',
                    'patterns': [{'pattern_type': 'test_pattern', 'confidence': 0.8}]
                }
            },
            'module_intelligence': {'confidence': 0.8, 'quality': 'high'},
            'sig_sigma': 1.5,
            'confidence': 0.8,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Process pattern
        logger.info("🎯 Processing test pattern...")
        success = await cil.process_pattern_strand(test_pattern)
        
        if success:
            logger.info("✅ CIL processed pattern successfully!")
        else:
            logger.error("❌ CIL failed to process pattern")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(test_simple_cil())
