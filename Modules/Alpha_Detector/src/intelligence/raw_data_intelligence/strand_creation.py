"""
Strand Creation Module

Handles creation of individual and overview strands for analysis results.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
import sys
import os

from src.utils.supabase_manager import SupabaseManager

# Add the learning system to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src', 'learning_system'))


class StrandCreation:
    """Handles creation of strands from analysis results"""
    
    def __init__(self, supabase_manager: SupabaseManager):
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize module-specific scoring
        try:
            from module_specific_scoring import ModuleSpecificScoring
            self.module_scoring = ModuleSpecificScoring(supabase_manager)
        except ImportError as e:
            self.logger.warning(f"Could not import module-specific scoring: {e}")
            self.module_scoring = None
    
    async def create_individual_analyzer_strand(self, analyzer_name: str, analysis: Dict[str, Any], analysis_results: Dict[str, Any], market_data: pd.DataFrame) -> Optional[str]:
        """
        Create individual strand for each team member analysis
        
        Args:
            analyzer_name: Name of the analyzer (e.g., 'microstructure', 'volume')
            analysis: Analysis results from this analyzer
            analysis_results: Complete analysis results
            market_data: Market data for context
            
        Returns:
            Strand ID if successful, None if failed
        """
        try:
            analyzer = analysis.get('analyzer', analyzer_name)
            analysis_type = analysis.get('analysis_type', analyzer_name)
            confidence = analysis.get('confidence', 0.5)
            significance = analysis.get('significance', 'medium')
            
            # OPTIMIZATION: Only create strand if patterns were actually detected
            if confidence <= 0.0 or significance == 'none':
                self.logger.info(f"Skipping strand creation for {analyzer_name} - no patterns detected (confidence: {confidence})")
                return None
            
            # Create individual analyzer strand
            strand_id = f"raw_data_{analyzer_name}_{int(datetime.now().timestamp())}"
            
            individual_strand = {
                'id': strand_id,
                'kind': 'pattern',
                'module': 'alpha',
                'agent_id': 'raw_data_intelligence',
                'team_member': analyzer,
                'symbol': self._extract_symbol_from_data(market_data),
                'timeframe': '1m',  # Default timeframe
                'session_bucket': 'GLOBAL',
                'regime': 'unknown',
                'tags': [
                    f"intelligence:raw_data:{analysis_type}:{significance}",
                    f"analyzer:{analyzer}",
                    'team_member_analysis'
                ],
                'target_agent': None,  # Individual strands don't target CIL directly
                'module_intelligence': {
                    'pattern_type': analysis_type,
                    'analyzer': analyzer,
                    'confidence': float(confidence) if confidence is not None else 0.5,
                    'significance': significance,
                    'description': f"{analyzer} analysis results",
                    'analysis_data': self._serialize_for_json(analysis.get('results', {})),
                    'analysis_timestamp': analysis_results['timestamp'],
                    'data_points': int(analysis_results.get('data_points', 0)),
                    'symbols': analysis_results.get('symbols', []),
                    'strand_type': 'individual_analyzer',
                    'hypothesis_notes': f"{analyzer} detected {analysis_type} patterns with {significance} significance",
                    'notes': f"Raw data analysis by {analyzer} showing {analysis_type} patterns"
                },
                'sig_sigma': float(confidence) if confidence is not None else 0.5,
                'confidence': float(confidence) if confidence is not None else 0.5,
                'sig_direction': 'neutral',  # Raw data doesn't predict direction
                'sig_confidence': None,
                'prediction_score': None,
                'outcome_score': None,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Calculate module-specific resonance scores
            if self.module_scoring:
                try:
                    persistence, novelty, surprise = await self.module_scoring.calculate_module_scores(individual_strand)
                    individual_strand['persistence_score'] = persistence
                    individual_strand['novelty_score'] = novelty
                    individual_strand['surprise_rating'] = surprise
                    individual_strand['resonance_score'] = (persistence + novelty + surprise) / 3
                    
                    # Add resonance scores to module_intelligence
                    individual_strand['module_intelligence']['resonance_scores'] = {
                        'phi': persistence,
                        'rho': surprise,
                        'theta': novelty,
                        'omega': 0.5  # Will be calculated by historical data
                    }
                except Exception as e:
                    self.logger.warning(f"Could not calculate resonance scores: {e}")
                    # Set default scores
                    individual_strand['persistence_score'] = 0.5
                    individual_strand['novelty_score'] = 0.5
                    individual_strand['surprise_rating'] = 0.5
                    individual_strand['resonance_score'] = 0.5
            
            # Store individual strand
            result = self.supabase_manager.client.table('ad_strands').insert(individual_strand).execute()
            
            if result.data:
                self.logger.info(f"Created individual strand for {analyzer}: {strand_id}")
                return strand_id
            else:
                self.logger.error(f"Failed to create individual strand for {analyzer}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create individual strand for {analyzer_name}: {e}")
            return None
    
    async def create_overview_strand_with_llm_results(self, individual_strand_ids: List[str], team_analysis: Dict[str, Any], 
                                                    meta_analysis: Dict[str, Any], cil_recommendations: List[Dict[str, Any]], 
                                                    analysis_results: Dict[str, Any], market_data: pd.DataFrame) -> Optional[str]:
        """
        Create overview strand with LLM meta-analysis results
        
        Args:
            individual_strand_ids: List of individual strand IDs
            team_analysis: Analysis from all team members
            meta_analysis: LLM meta-analysis results
            cil_recommendations: CIL recommendations from LLM
            analysis_results: Complete analysis results
            market_data: Market data for context
            
        Returns:
            Overview strand ID if successful, None if failed
        """
        try:
            # Check if any individual strands were created
            if not individual_strand_ids:
                self.logger.info("No individual strands created - creating 'no patterns' overview strand")
                return await self._create_no_patterns_overview_strand(team_analysis, analysis_results, market_data)
            
            # Get overall confidence from LLM results
            overall_confidence = meta_analysis.get('meta_confidence', 0.5)
            overall_significance = 'high' if overall_confidence > 0.8 else 'medium' if overall_confidence > 0.6 else 'low'
            
            # Create overview strand
            overview_strand_id = f"raw_data_overview_{int(datetime.now().timestamp())}"
            
            overview_strand = {
                'id': overview_strand_id,
                'kind': 'pattern_overview',
                'module': 'alpha',
                'agent_id': 'raw_data_intelligence',
                'team_member': 'raw_data_intelligence_coordinator',
                'symbol': self._extract_symbol_from_data(market_data),
                'timeframe': '1m',  # Default timeframe
                'session_bucket': 'GLOBAL',
                'regime': 'unknown',
                'tags': [
                    'intelligence:raw_data:overview:coordination',
                    'cil',  # Tag for CIL processing
                    'overview_strand',
                    'llm_coordination'
                ],
                'target_agent': 'central_intelligence_layer',  # Direct CIL targeting
                'module_intelligence': {
                    'pattern_type': 'llm_coordination_overview',
                    'analyzer': 'RawDataIntelligenceCoordinator',
                    'confidence': overall_confidence,
                    'significance': overall_significance,
                    'description': f"LLM-coordinated analysis from {len(individual_strand_ids)} team members",
                    'individual_strand_ids': individual_strand_ids,  # Links to individual strands
                    'team_analysis_summary': {
                        analyzer: {
                            'analyzer': analysis.get('analyzer', analyzer),
                            'confidence': analysis.get('confidence', 0.5),
                            'significance': analysis.get('significance', 'medium'),
                            'strand_id': individual_strand_ids[i] if i < len(individual_strand_ids) else None
                        }
                        for i, (analyzer, analysis) in enumerate(team_analysis.items())
                        if 'error' not in analysis
                    },
                    'llm_meta_analysis': meta_analysis,
                    'cil_recommendations': cil_recommendations,
                    'analysis_timestamp': analysis_results['timestamp'],
                    'data_points': int(analysis_results.get('data_points', 0)),
                    'symbols': analysis_results.get('symbols', []),
                    'strand_type': 'llm_coordination_overview',
                    'hypothesis_notes': f"Coordinated analysis from {len(individual_strand_ids)} team members with {overall_significance} significance",
                    'notes': f"LLM-coordinated overview of raw data intelligence analysis"
                },
                'sig_sigma': overall_confidence,
                'confidence': overall_confidence,
                'sig_direction': 'neutral',  # Raw data doesn't predict direction
                'sig_confidence': None,
                'prediction_score': None,
                'outcome_score': None,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Calculate module-specific resonance scores for overview strand
            if self.module_scoring:
                try:
                    persistence, novelty, surprise = await self.module_scoring.calculate_module_scores(overview_strand)
                    overview_strand['persistence_score'] = persistence
                    overview_strand['novelty_score'] = novelty
                    overview_strand['surprise_rating'] = surprise
                    overview_strand['resonance_score'] = (persistence + novelty + surprise) / 3
                    
                    # Add resonance scores to module_intelligence
                    overview_strand['module_intelligence']['resonance_scores'] = {
                        'phi': persistence,
                        'rho': surprise,
                        'theta': novelty,
                        'omega': 0.5  # Will be calculated by historical data
                    }
                except Exception as e:
                    self.logger.warning(f"Could not calculate resonance scores for overview: {e}")
                    # Set default scores
                    overview_strand['persistence_score'] = 0.5
                    overview_strand['novelty_score'] = 0.5
                    overview_strand['surprise_rating'] = 0.5
                    overview_strand['resonance_score'] = 0.5
            
            # Store overview strand
            result = self.supabase_manager.client.table('ad_strands').insert(overview_strand).execute()
            
            if result.data:
                self.logger.info(f"Created LLM-coordinated overview strand: {overview_strand_id} (links {len(individual_strand_ids)} individual strands)")
                return overview_strand_id
            else:
                self.logger.error("Failed to create overview strand")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create overview strand: {e}")
            return None
    
    async def _create_no_patterns_overview_strand(self, team_analysis: Dict[str, Any], 
                                                analysis_results: Dict[str, Any], 
                                                market_data: pd.DataFrame) -> Optional[str]:
        """
        Create overview strand when no patterns were detected by any analyzer
        
        Args:
            team_analysis: Analysis from all team members
            analysis_results: Complete analysis results
            market_data: Market data for context
            
        Returns:
            Overview strand ID if successful, None if failed
        """
        try:
            # Create 'no patterns' overview strand
            overview_strand_id = f"raw_data_no_patterns_{int(datetime.now().timestamp())}"
            
            overview_strand = {
                'id': overview_strand_id,
                'kind': 'pattern_overview',
                'module': 'alpha',
                'agent_id': 'raw_data_intelligence',
                'team_member': 'raw_data_intelligence_coordinator',
                'symbol': self._extract_symbol_from_data(market_data),
                'timeframe': '1m',
                'session_bucket': 'GLOBAL',
                'regime': 'unknown',
                'tags': [
                    'intelligence:raw_data:no_patterns',
                    'overview_strand',
                    'no_patterns_detected'
                ],
                'target_agent': None,  # No CIL targeting for no patterns
                'module_intelligence': {
                    'pattern_type': 'no_patterns_overview',
                    'analyzer': 'RawDataIntelligenceCoordinator',
                    'confidence': 0.0,
                    'significance': 'none',
                    'description': 'No significant patterns detected in this analysis cycle',
                    'analysis_data': self._serialize_for_json(team_analysis),
                    'analysis_timestamp': analysis_results['timestamp'],
                    'data_points': int(analysis_results.get('data_points', 0)),
                    'symbols': analysis_results.get('symbols', []),
                    'strand_type': 'no_patterns_overview',
                    'hypothesis_notes': 'No patterns detected by any team member in this cycle',
                    'notes': 'Raw data intelligence analysis cycle completed with no significant patterns found'
                },
                'sig_sigma': 0.0,
                'confidence': 0.0,
                'sig_direction': 'neutral',
                'sig_confidence': None,
                'prediction_score': None,
                'outcome_score': None,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Store overview strand
            result = self.supabase_manager.client.table('ad_strands').insert(overview_strand).execute()
            
            if result.data:
                self.logger.info(f"Created 'no patterns' overview strand: {overview_strand_id}")
                return overview_strand_id
            else:
                self.logger.error("Failed to create 'no patterns' overview strand")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create 'no patterns' overview strand: {e}")
            return None
    
    def _serialize_for_json(self, obj):
        """Serialize object for JSON compatibility"""
        if isinstance(obj, dict):
            return {k: self._serialize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_for_json(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            # Handle NaN and infinity values
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return [self._serialize_for_json(item) for item in obj.tolist()]
        elif hasattr(obj, '__dict__'):
            return self._serialize_for_json(obj.__dict__)
        else:
            return obj
    
    def _extract_symbol_from_data(self, market_data: pd.DataFrame) -> str:
        """Extract the most common symbol from market data"""
        if market_data is None or market_data.empty or 'symbol' not in market_data.columns:
            return 'BTC'  # Default fallback
        
        # Get the most common symbol
        symbol_counts = market_data['symbol'].value_counts()
        if not symbol_counts.empty:
            return symbol_counts.index[0]  # Most common symbol
        
        return 'BTC'  # Default fallback
