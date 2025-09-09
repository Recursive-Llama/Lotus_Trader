#!/usr/bin/env python3
"""
Test Raw Data Intelligence Statistical Focus

Tests the updated Raw Data Intelligence system with:
1. Statistical measurements instead of prediction confidence
2. RMC compilation system
3. Multi-timeframe data architecture
4. Proper strand creation with statistical focus
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
import pandas as pd
import numpy as np

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.openrouter_client import OpenRouterClient
from src.intelligence.raw_data_intelligence.raw_data_intelligence_agent import RawDataIntelligenceAgent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RawDataStatisticalFocusTester:
    """Test the updated Raw Data Intelligence system"""
    
    def __init__(self):
        self.db = SupabaseManager()
        self.llm_client = OpenRouterClient()
        self.raw_agent = RawDataIntelligenceAgent(self.db, self.llm_client)
        
    async def test_statistical_focus(self):
        """Test the statistical focus of Raw Data Intelligence"""
        logger.info("🧪 Testing Raw Data Intelligence Statistical Focus")
        
        try:
            # Create mock market data
            mock_data = self._create_mock_market_data()
            logger.info(f"📊 Created mock data with {len(mock_data)} rows")
            
            # Test pattern detection with statistical focus
            analysis_results = await self.raw_agent._analyze_raw_data_enhanced(mock_data)
            logger.info(f"🔍 Analysis completed: {len(analysis_results.get('significant_patterns', []))} patterns found")
            
            # Test strand creation
            await self.raw_agent._publish_findings(analysis_results)
            logger.info("📤 Strands published to database")
            
            # Verify statistical measurements
            self._verify_statistical_measurements(analysis_results)
            
            # Test RMC compilation system
            await self._test_rmc_compilation()
            
            logger.info("✅ All tests passed!")
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            raise
    
    def _create_mock_market_data(self) -> pd.DataFrame:
        """Create mock market data for testing"""
        # Create 5 minutes of 1-minute data
        timestamps = pd.date_range(
            start=datetime.now(timezone.utc) - timedelta(minutes=5),
            end=datetime.now(timezone.utc),
            freq='1min'
        )
        
        data = []
        base_price = 50000
        base_volume = 1000000
        
        for i, timestamp in enumerate(timestamps):
            # Create some volume spikes and price movements
            volume_multiplier = 1.0
            if i == 2:  # Volume spike at minute 3
                volume_multiplier = 4.2
            elif i == 4:  # Another volume spike at minute 5
                volume_multiplier = 3.8
            
            price_change = np.random.normal(0, 0.01)  # 1% standard deviation
            price = base_price * (1 + price_change)
            
            volume = base_volume * volume_multiplier
            
            data.append({
                'symbol': 'BTC',
                'timestamp': timestamp,
                'open': price,
                'high': price * 1.001,
                'low': price * 0.999,
                'close': price * (1 + np.random.normal(0, 0.005)),
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def _verify_statistical_measurements(self, analysis_results: Dict[str, Any]):
        """Verify that statistical measurements are properly calculated"""
        logger.info("🔬 Verifying statistical measurements...")
        
        significant_patterns = analysis_results.get('significant_patterns', [])
        
        for pattern in significant_patterns:
            # Check that pattern has statistical measurements
            assert 'pattern_clarity' in pattern, "Pattern missing pattern_clarity"
            assert 'z_score' in pattern, "Pattern missing z_score"
            assert 'statistical_significance' in pattern, "Pattern missing statistical_significance"
            assert 'team_member' in pattern, "Pattern missing team_member"
            
            # Check that confidence is not used for prediction
            assert 'confidence' not in pattern or pattern.get('confidence') is None, "Pattern should not use confidence for prediction"
            
            logger.info(f"✅ Pattern {pattern['type']} has proper statistical measurements")
    
    async def _test_rmc_compilation(self):
        """Test the RMC compilation system"""
        logger.info("📋 Testing RMC compilation system...")
        
        # Check if compilation strands were created
        result = self.db.client.table('ad_strands').select('*').eq('kind', 'intelligence').eq('agent_id', 'raw_data_intelligence').eq('cil_team_member', 'raw_data_intelligence_agent').execute()
        
        compilation_strands = [strand for strand in result.data if 'compilation' in strand.get('tags', [])]
        
        if compilation_strands:
            logger.info(f"✅ Found {len(compilation_strands)} compilation strands")
            
            # Verify compilation strand structure
            compilation = compilation_strands[0]
            module_intelligence = compilation.get('module_intelligence', {})
            
            assert module_intelligence.get('compilation_type') == 'pattern_summary', "Invalid compilation type"
            assert 'pattern_links' in module_intelligence, "Missing pattern links"
            assert 'total_patterns' in module_intelligence, "Missing total patterns"
            
            logger.info("✅ Compilation strand has proper structure")
        else:
            logger.warning("⚠️ No compilation strands found")
    
    async def test_multi_timeframe_architecture(self):
        """Test multi-timeframe data architecture"""
        logger.info("⏰ Testing multi-timeframe architecture...")
        
        # Check if multi-timeframe tables exist
        timeframes = ['5m', '15m', '1h', '4h']
        
        for timeframe in timeframes:
            table_name = f'alpha_market_data_{timeframe}'
            try:
                result = self.db.client.table(table_name).select('*').limit(1).execute()
                logger.info(f"✅ Table {table_name} exists and accessible")
            except Exception as e:
                logger.warning(f"⚠️ Table {table_name} not accessible: {e}")
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("🚀 Starting Raw Data Intelligence Statistical Focus Tests")
        
        try:
            await self.test_statistical_focus()
            await self.test_multi_timeframe_architecture()
            
            logger.info("🎉 All tests completed successfully!")
            
        except Exception as e:
            logger.error(f"💥 Test suite failed: {e}")
            raise

async def main():
    """Main test function"""
    tester = RawDataStatisticalFocusTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
