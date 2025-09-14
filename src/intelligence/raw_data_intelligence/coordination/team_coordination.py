"""
Team Coordination Module

Handles coordination of analysis from different team members (analyzers).
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import pandas as pd

from ..analyzers.market_microstructure import MarketMicrostructureAnalyzer
from ..analyzers.volume_analyzer import VolumePatternAnalyzer
from ..analyzers.time_based_patterns import TimeBasedPatternDetector
from ..analyzers.cross_asset_analyzer import CrossAssetPatternAnalyzer
from ..analyzers.divergence_detector import RawDataDivergenceDetector


class TeamCoordination:
    """Handles coordination of analysis from different team members"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.team_coordination")
        
        # Initialize analyzers
        self.microstructure_analyzer = MarketMicrostructureAnalyzer()
        self.volume_analyzer = VolumePatternAnalyzer()
        self.time_pattern_detector = TimeBasedPatternDetector()
        self.cross_asset_analyzer = CrossAssetPatternAnalyzer()
        self.divergence_detector = RawDataDivergenceDetector()
    
    async def coordinate_team_analysis(self, market_data_1m: pd.DataFrame, multi_timeframe_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinate analysis from different team members
        
        Args:
            market_data_1m: 1-minute market data
            multi_timeframe_data: Multi-timeframe processed data
            
        Returns:
            Dictionary with analysis from each team member
        """
        try:
            team_analysis = {}
            
            # 1. Market Microstructure Analysis
            self.logger.info("Coordinating microstructure analysis...")
            microstructure_analysis = await self._coordinate_microstructure_analysis(market_data_1m, multi_timeframe_data)
            team_analysis['microstructure'] = microstructure_analysis
            
            # 2. Volume Pattern Analysis
            self.logger.info("Coordinating volume analysis...")
            volume_analysis = await self._coordinate_volume_analysis(market_data_1m, multi_timeframe_data)
            team_analysis['volume'] = volume_analysis
            
            # 3. Time-Based Pattern Analysis
            self.logger.info("Coordinating time-based pattern analysis...")
            time_pattern_analysis = await self._coordinate_time_pattern_analysis(market_data_1m, multi_timeframe_data)
            team_analysis['time_patterns'] = time_pattern_analysis
            
            # 4. Cross-Asset Analysis
            self.logger.info("Coordinating cross-asset analysis...")
            cross_asset_analysis = await self._coordinate_cross_asset_analysis(market_data_1m, multi_timeframe_data)
            team_analysis['cross_asset'] = cross_asset_analysis
            
            # 5. Divergence Detection
            self.logger.info("Coordinating divergence detection...")
            divergence_analysis = await self._coordinate_divergence_analysis(market_data_1m, multi_timeframe_data)
            team_analysis['divergences'] = divergence_analysis
            
            return team_analysis
            
        except Exception as e:
            self.logger.error(f"Team coordination failed: {e}")
            return {'error': str(e)}
    
    async def _coordinate_microstructure_analysis(self, market_data_1m: pd.DataFrame, multi_timeframe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate microstructure analysis from team members"""
        try:
            # Use the microstructure analyzer
            analysis = await self.microstructure_analyzer.analyze(market_data_1m)
            
            return {
                'analyzer': 'MarketMicrostructureAnalyzer',
                'analysis_type': 'microstructure',
                'results': analysis,
                'confidence': analysis.get('confidence', 0.5),
                'significance': analysis.get('significance', 'medium'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            self.logger.error(f"Microstructure analysis coordination failed: {e}")
            return {'error': str(e), 'analyzer': 'MarketMicrostructureAnalyzer'}
    
    async def _coordinate_volume_analysis(self, market_data_1m: pd.DataFrame, multi_timeframe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate volume analysis from team members"""
        try:
            # Use the volume analyzer
            analysis = await self.volume_analyzer.analyze(market_data_1m)
            
            return {
                'analyzer': 'VolumePatternAnalyzer',
                'analysis_type': 'volume',
                'results': analysis,
                'confidence': analysis.get('confidence', 0.5),
                'significance': analysis.get('significance', 'medium'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            self.logger.error(f"Volume analysis coordination failed: {e}")
            return {'error': str(e), 'analyzer': 'VolumePatternAnalyzer'}
    
    async def _coordinate_time_pattern_analysis(self, market_data_1m: pd.DataFrame, multi_timeframe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate time-based pattern analysis from team members"""
        try:
            # Use the time pattern detector
            analysis = await self.time_pattern_detector.analyze(market_data_1m)
            
            return {
                'analyzer': 'TimeBasedPatternDetector',
                'analysis_type': 'time_patterns',
                'results': analysis,
                'confidence': analysis.get('confidence', 0.5),
                'significance': analysis.get('significance', 'medium'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            self.logger.error(f"Time pattern analysis coordination failed: {e}")
            return {'error': str(e), 'analyzer': 'TimeBasedPatternDetector'}
    
    async def _coordinate_cross_asset_analysis(self, market_data_1m: pd.DataFrame, multi_timeframe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate cross-asset analysis from team members"""
        try:
            # Use the cross-asset analyzer
            analysis = await self.cross_asset_analyzer.analyze(market_data_1m)
            
            return {
                'analyzer': 'CrossAssetPatternAnalyzer',
                'analysis_type': 'cross_asset',
                'results': analysis,
                'confidence': analysis.get('confidence', 0.5),
                'significance': analysis.get('significance', 'medium'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            self.logger.error(f"Cross-asset analysis coordination failed: {e}")
            return {'error': str(e), 'analyzer': 'CrossAssetPatternAnalyzer'}
    
    async def _coordinate_divergence_analysis(self, market_data_1m: pd.DataFrame, multi_timeframe_data: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate divergence detection from team members"""
        try:
            # Use the divergence detector
            analysis = await self.divergence_detector.analyze(market_data_1m)
            
            return {
                'analyzer': 'RawDataDivergenceDetector',
                'analysis_type': 'divergences',
                'results': analysis,
                'confidence': analysis.get('confidence', 0.5),
                'significance': analysis.get('significance', 'medium'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            self.logger.error(f"Divergence analysis coordination failed: {e}")
            return {'error': str(e), 'analyzer': 'RawDataDivergenceDetector'}
