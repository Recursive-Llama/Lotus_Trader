"""
Test Embedding Fix

Test that embeddings are properly truncated to 1536 dimensions.
"""

import asyncio
import logging
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁')
sys.path.append('/Users/bruce/Documents/Lotus_Trader⚘⟁/src')

from Modules.Alpha_Detector.src.utils.supabase_manager import SupabaseManager
from Modules.Alpha_Detector.src.intelligence.llm_integration.llm_client import LLMClientManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_embedding_fix():
    """Test that embeddings are properly truncated to 1536 dimensions"""
    try:
        logger.info("🧪 Testing Embedding Fix - Should be exactly 1536 dimensions")
        
        # Initialize components
        supabase_manager = SupabaseManager()
        
        # Initialize LLM client manager with REAL API keys
        llm_config = {
            'openai': {
                'api_key': os.getenv('OPENAI_API_KEY', ''),
                'model': 'gpt-4o-mini'
            },
            'anthropic': {
                'api_key': os.getenv('ANTHROPIC_API_KEY', ''),
                'model': 'claude-3-haiku-20240307'
            }
        }
        llm_client = LLMClientManager(llm_config)
        
        logger.info("✅ LLM client initialized")
        
        # Test embedding generation
        test_texts = [
            "BTCUSDT bullish breakout pattern with high volume",
            "Market analysis for trading strategy development",
            "Pattern recognition and prediction accuracy assessment"
        ]
        
        for i, text in enumerate(test_texts):
            logger.info(f"\n📊 Test {i+1}: Testing embedding for: '{text}'")
            
            # Generate embedding
            embedding = await llm_client.generate_embedding(text)
            
            # Check dimensions
            dimensions = len(embedding)
            logger.info(f"✅ Embedding dimensions: {dimensions}")
            
            if dimensions == 1536:
                logger.info("✅ Perfect! Embedding is exactly 1536 dimensions")
            elif dimensions > 1536:
                logger.error(f"❌ Error! Embedding has {dimensions} dimensions (should be 1536)")
                return False
            else:
                logger.warning(f"⚠️  Warning! Embedding has {dimensions} dimensions (should be 1536)")
        
        # Test with a longer text to ensure truncation works
        logger.info(f"\n📊 Test 4: Testing with longer text to ensure truncation works")
        long_text = "This is a very long text about market analysis and trading patterns. " * 50
        
        embedding = await llm_client.generate_embedding(long_text)
        dimensions = len(embedding)
        logger.info(f"✅ Long text embedding dimensions: {dimensions}")
        
        if dimensions == 1536:
            logger.info("✅ Perfect! Long text embedding is exactly 1536 dimensions")
        else:
            logger.error(f"❌ Error! Long text embedding has {dimensions} dimensions (should be 1536)")
            return False
        
        logger.info("\n🎉 All embedding tests passed! Vectors are properly truncated to 1536 dimensions.")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    success = await test_embedding_fix()
    if success:
        logger.info("✅ Embedding fix test passed!")
    else:
        logger.error("❌ Embedding fix test failed!")
    return success


if __name__ == "__main__":
    asyncio.run(main())
