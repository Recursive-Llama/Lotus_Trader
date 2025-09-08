"""
Cross-Team Integration for Raw Data Intelligence

Handles cross-team pattern awareness for organic intelligence. Enables agents to benefit 
from CIL's cross-team pattern detection by identifying confluence patterns, lead-lag 
relationships, and strategic significance across multiple intelligence teams.

Key Concepts:
- Cross-Team Confluence: Patterns that emerge across multiple teams
- Lead-Lag Patterns: Timing relationships between different teams
- Strategic Significance: Cross-team patterns with high strategic value
- Organic Intelligence: Natural cross-team pattern awareness
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from collections import defaultdict

from src.utils.supabase_manager import SupabaseManager


class CrossTeamIntegration:
    """
    Handles cross-team pattern awareness for organic intelligence
    
    Enables agents to:
    - Detect confluence patterns across teams
    - Identify lead-lag patterns between teams
    - Contribute to strategic analysis
    - Benefit from cross-team pattern detection
    - Participate in organic intelligence network
    """
    
    def __init__(self, supabase_manager: SupabaseManager):
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(__name__)
        
        # Cross-team analysis parameters
        self.confluence_time_window = 300  # 5 minutes in seconds
        self.lead_lag_max_delay = 1800  # 30 minutes in seconds
        self.confluence_strength_threshold = 0.7  # Minimum confluence strength
        self.lead_lag_consistency_threshold = 0.6  # Minimum lead-lag consistency
        self.strategic_significance_threshold = 0.8  # Minimum strategic significance
        
        # Intelligence teams
        self.intelligence_teams = [
            'raw_data_intelligence',
            'indicator_intelligence',
            'pattern_intelligence',
            'central_intelligence_layer',
            'system_control',
            'learning_system'
        ]
        
        # Cross-team pattern types
        self.confluence_pattern_types = [
            'volume_confluence',
            'divergence_confluence',
            'microstructure_confluence',
            'time_based_confluence',
            'cross_asset_confluence',
            'resonance_confluence'
        ]
        
        # Lead-lag relationship types
        self.lead_lag_types = [
            'volume_to_divergence',
            'divergence_to_microstructure',
            'microstructure_to_time_based',
            'time_based_to_cross_asset',
            'cross_asset_to_resonance',
            'resonance_to_strategic'
        ]
        
        # Cross-team analysis tracking
        self.confluence_detections = []
        self.lead_lag_detections = []
        self.strategic_contributions = []
    
    async def detect_cross_team_confluence(self, time_window: str = "5m") -> List[Dict[str, Any]]:
        """
        Detect confluence patterns across teams for organic insights
        
        Args:
            time_window: Time window for confluence detection
            
        Returns:
            List of confluence patterns with strategic significance
        """
        try:
            self.logger.info(f"Detecting cross-team confluence in time window: {time_window}")
            
            # 1. Query strands from all intelligence teams
            team_strands = await self._query_team_strands(time_window)
            
            # 2. Find temporal overlaps
            temporal_overlaps = await self._find_temporal_overlaps(team_strands)
            
            # 3. Calculate confluence strength
            confluence_patterns = await self._calculate_confluence_strength(temporal_overlaps)
            
            # 4. Identify strategic significance
            strategic_confluence = await self._identify_strategic_significance(confluence_patterns)
            
            # 5. Track confluence detections
            await self._track_confluence_detections(strategic_confluence)
            
            self.logger.info(f"Detected {len(strategic_confluence)} strategic confluence patterns")
            return strategic_confluence
            
        except Exception as e:
            self.logger.error(f"Cross-team confluence detection failed: {e}")
            return []
    
    async def identify_lead_lag_patterns(self, team_pairs: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """
        Identify lead-lag patterns between teams for organic learning
        
        Args:
            team_pairs: Pairs of teams to analyze for lead-lag relationships
            
        Returns:
            List of lead-lag patterns with consistency scores
        """
        try:
            self.logger.info(f"Identifying lead-lag patterns for {len(team_pairs)} team pairs")
            
            lead_lag_patterns = []
            
            for team1, team2 in team_pairs:
                # 1. Analyze timing relationships
                timing_analysis = await self._analyze_timing_relationships(team1, team2)
                
                # 2. Calculate consistency scores
                consistency_scores = await self._calculate_consistency_scores(timing_analysis)
                
                # 3. Identify reliable lead-lag structures
                reliable_patterns = await self._identify_reliable_lead_lag_structures(consistency_scores)
                
                # 4. Create lead-lag meta-signals
                meta_signals = await self._create_lead_lag_meta_signals(reliable_patterns, team1, team2)
                
                lead_lag_patterns.extend(meta_signals)
            
            # 5. Track lead-lag detections
            await self._track_lead_lag_detections(lead_lag_patterns)
            
            self.logger.info(f"Identified {len(lead_lag_patterns)} lead-lag patterns")
            return lead_lag_patterns
            
        except Exception as e:
            self.logger.error(f"Lead-lag pattern identification failed: {e}")
            return []
    
    async def contribute_to_strategic_analysis(self, confluence_data: Dict[str, Any]) -> str:
        """
        Contribute to CIL strategic analysis through cross-team insights
        
        Args:
            confluence_data: Cross-team confluence data to contribute
            
        Returns:
            Strategic analysis contribution strand ID
        """
        try:
            self.logger.info("Contributing to CIL strategic analysis with cross-team insights")
            
            # 1. Analyze raw data perspective
            raw_data_perspective = await self._analyze_raw_data_perspective(confluence_data)
            
            # 2. Provide mechanism insights
            mechanism_insights = await self._provide_mechanism_insights(confluence_data)
            
            # 3. Suggest follow-up experiments
            experiment_suggestions = await self._suggest_follow_up_experiments(confluence_data)
            
            # 4. Create strategic insight strand
            strategic_contribution = {
                'contribution_id': self._generate_contribution_id(confluence_data),
                'contribution_type': 'cross_team_strategic_analysis',
                'raw_data_perspective': raw_data_perspective,
                'mechanism_insights': mechanism_insights,
                'experiment_suggestions': experiment_suggestions,
                'confluence_data': confluence_data,
                'contribution_timestamp': datetime.now(timezone.utc).isoformat(),
                'contributor_agent': 'raw_data_intelligence',
                'strategic_relevance': await self._calculate_cross_team_strategic_relevance(confluence_data),
                'cross_team_confidence': confluence_data.get('confluence_strength', 0.0)
            }
            
            # 5. Publish strategic contribution strand
            contribution_strand_id = await self._publish_strategic_contribution(strategic_contribution)
            
            if contribution_strand_id:
                self.logger.info(f"Contributed strategic analysis: {contribution_strand_id}")
                self.logger.info(f"Strategic relevance: {strategic_contribution['strategic_relevance']}")
                self.logger.info(f"Cross-team confidence: {strategic_contribution['cross_team_confidence']}")
            
            return contribution_strand_id
            
        except Exception as e:
            self.logger.error(f"Strategic analysis contribution failed: {e}")
            return None
    
    async def _query_team_strands(self, time_window: str) -> Dict[str, List[Dict[str, Any]]]:
        """Query strands from all intelligence teams"""
        try:
            team_strands = {}
            
            # Calculate time range
            end_time = datetime.now(timezone.utc)
            if time_window == "5m":
                start_time = end_time - timedelta(minutes=5)
            elif time_window == "15m":
                start_time = end_time - timedelta(minutes=15)
            elif time_window == "1h":
                start_time = end_time - timedelta(hours=1)
            else:
                start_time = end_time - timedelta(minutes=5)  # Default to 5 minutes
            
            # Mock implementation - in real system, this would query the database
            for team in self.intelligence_teams:
                team_strands[team] = [
                    {
                        'strand_id': f'{team}_strand_1',
                        'team': team,
                        'pattern_type': 'volume_spike',
                        'confidence': 0.8,
                        'timestamp': (end_time - timedelta(minutes=2)).isoformat(),
                        'content': f'{team} detected volume spike pattern'
                    },
                    {
                        'strand_id': f'{team}_strand_2',
                        'team': team,
                        'pattern_type': 'divergence',
                        'confidence': 0.7,
                        'timestamp': (end_time - timedelta(minutes=3)).isoformat(),
                        'content': f'{team} detected divergence pattern'
                    }
                ]
            
            return team_strands
            
        except Exception as e:
            self.logger.error(f"Team strand query failed: {e}")
            return {}
    
    async def _find_temporal_overlaps(self, team_strands: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Find temporal overlaps between team strands"""
        try:
            temporal_overlaps = []
            
            # Group strands by time windows
            time_windows = defaultdict(list)
            
            for team, strands in team_strands.items():
                for strand in strands:
                    timestamp = datetime.fromisoformat(strand['timestamp'].replace('Z', '+00:00'))
                    time_key = timestamp.replace(second=0, microsecond=0)
                    time_windows[time_key].append(strand)
            
            # Find overlaps within time windows
            for time_key, strands in time_windows.items():
                if len(strands) >= 2:  # At least 2 teams have strands in this time window
                    overlap = {
                        'time_window': time_key.isoformat(),
                        'strands': strands,
                        'team_count': len(set(strand['team'] for strand in strands)),
                        'pattern_types': [strand['pattern_type'] for strand in strands],
                        'overlap_strength': len(strands) / len(self.intelligence_teams)
                    }
                    temporal_overlaps.append(overlap)
            
            return temporal_overlaps
            
        except Exception as e:
            self.logger.error(f"Temporal overlap finding failed: {e}")
            return []
    
    async def _calculate_confluence_strength(self, temporal_overlaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate confluence strength for temporal overlaps"""
        try:
            confluence_patterns = []
            
            for overlap in temporal_overlaps:
                # Calculate confluence strength based on multiple factors
                team_count = overlap['team_count']
                overlap_strength = overlap['overlap_strength']
                pattern_types = overlap['pattern_types']
                
                # Base confluence strength
                confluence_strength = (team_count / len(self.intelligence_teams)) * 0.4 + overlap_strength * 0.3
                
                # Pattern type diversity bonus
                pattern_diversity = len(set(pattern_types)) / len(pattern_types) if pattern_types else 0
                confluence_strength += pattern_diversity * 0.3
                
                # Confidence bonus
                avg_confidence = np.mean([strand.get('confidence', 0.0) for strand in overlap['strands']])
                confluence_strength += avg_confidence * 0.2
                
                confluence_pattern = {
                    'confluence_id': f"confluence_{overlap['time_window'].replace(':', '').replace('-', '')}",
                    'time_window': overlap['time_window'],
                    'confluence_strength': min(1.0, confluence_strength),
                    'team_count': team_count,
                    'pattern_types': pattern_types,
                    'strands': overlap['strands'],
                    'pattern_diversity': pattern_diversity,
                    'average_confidence': avg_confidence
                }
                
                confluence_patterns.append(confluence_pattern)
            
            return confluence_patterns
            
        except Exception as e:
            self.logger.error(f"Confluence strength calculation failed: {e}")
            return []
    
    async def _identify_strategic_significance(self, confluence_patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify strategic significance of confluence patterns"""
        try:
            strategic_confluence = []
            
            for pattern in confluence_patterns:
                confluence_strength = pattern['confluence_strength']
                team_count = pattern['team_count']
                pattern_diversity = pattern['pattern_diversity']
                
                # Calculate strategic significance
                strategic_significance = 0.0
                
                # High confluence strength
                if confluence_strength >= self.confluence_strength_threshold:
                    strategic_significance += 0.4
                
                # Multiple teams involved
                if team_count >= 3:
                    strategic_significance += 0.3
                
                # High pattern diversity
                if pattern_diversity >= 0.7:
                    strategic_significance += 0.3
                
                # Add strategic significance to pattern
                pattern['strategic_significance'] = strategic_significance
                pattern['strategic_priority'] = 'high' if strategic_significance >= self.strategic_significance_threshold else 'medium'
                
                if strategic_significance >= self.strategic_significance_threshold:
                    strategic_confluence.append(pattern)
            
            return strategic_confluence
            
        except Exception as e:
            self.logger.error(f"Strategic significance identification failed: {e}")
            return []
    
    async def _analyze_timing_relationships(self, team1: str, team2: str) -> Dict[str, Any]:
        """Analyze timing relationships between two teams"""
        try:
            # Mock implementation - in real system, this would analyze actual timing data
            timing_analysis = {
                'team1': team1,
                'team2': team2,
                'lead_lag_detected': True,
                'lead_team': team1,
                'lag_team': team2,
                'average_delay': 120,  # seconds
                'delay_consistency': 0.8,
                'sample_count': 10,
                'timing_confidence': 0.75
            }
            
            return timing_analysis
            
        except Exception as e:
            self.logger.error(f"Timing relationship analysis failed: {e}")
            return {}
    
    async def _calculate_consistency_scores(self, timing_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate consistency scores for timing analysis"""
        try:
            consistency_scores = {
                'delay_consistency': timing_analysis.get('delay_consistency', 0.0),
                'timing_confidence': timing_analysis.get('timing_confidence', 0.0),
                'sample_reliability': min(1.0, timing_analysis.get('sample_count', 0) / 20),
                'overall_consistency': 0.0
            }
            
            # Calculate overall consistency
            consistency_scores['overall_consistency'] = (
                consistency_scores['delay_consistency'] * 0.4 +
                consistency_scores['timing_confidence'] * 0.4 +
                consistency_scores['sample_reliability'] * 0.2
            )
            
            return consistency_scores
            
        except Exception as e:
            self.logger.error(f"Consistency score calculation failed: {e}")
            return {}
    
    async def _identify_reliable_lead_lag_structures(self, consistency_scores: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify reliable lead-lag structures"""
        try:
            reliable_patterns = []
            
            overall_consistency = consistency_scores.get('overall_consistency', 0.0)
            
            if overall_consistency >= self.lead_lag_consistency_threshold:
                reliable_pattern = {
                    'pattern_id': f"lead_lag_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'reliability_score': overall_consistency,
                    'consistency_scores': consistency_scores,
                    'pattern_type': 'lead_lag',
                    'reliability_level': 'high' if overall_consistency >= 0.8 else 'medium'
                }
                reliable_patterns.append(reliable_pattern)
            
            return reliable_patterns
            
        except Exception as e:
            self.logger.error(f"Reliable lead-lag structure identification failed: {e}")
            return []
    
    async def _create_lead_lag_meta_signals(self, reliable_patterns: List[Dict[str, Any]], team1: str, team2: str) -> List[Dict[str, Any]]:
        """Create lead-lag meta-signals"""
        try:
            meta_signals = []
            
            for pattern in reliable_patterns:
                meta_signal = {
                    'meta_signal_id': f"lead_lag_meta_{pattern['pattern_id']}",
                    'signal_type': 'lead_lag_pattern',
                    'lead_team': team1,
                    'lag_team': team2,
                    'reliability_score': pattern['reliability_score'],
                    'consistency_scores': pattern['consistency_scores'],
                    'meta_signal_confidence': pattern['reliability_score'],
                    'strategic_insight': f"{team1} leads {team2} with {pattern['reliability_score']:.2f} reliability",
                    'creation_timestamp': datetime.now(timezone.utc).isoformat(),
                    'applicable_teams': [team1, team2]
                }
                meta_signals.append(meta_signal)
            
            return meta_signals
            
        except Exception as e:
            self.logger.error(f"Lead-lag meta-signal creation failed: {e}")
            return []
    
    async def _analyze_raw_data_perspective(self, confluence_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze raw data perspective on confluence"""
        try:
            raw_data_perspective = {
                'confluence_interpretation': 'Raw data perspective on cross-team confluence',
                'data_quality_assessment': 'High quality data supports confluence detection',
                'pattern_validation': 'Raw data patterns validate cross-team confluence',
                'uncertainty_contribution': 'Raw data uncertainty contributes to confluence analysis',
                'resonance_contribution': confluence_data.get('confluence_strength', 0.0),
                'temporal_characteristics': {
                    'time_window': confluence_data.get('time_window', 'unknown'),
                    'confluence_duration': '5 minutes',
                    'pattern_persistence': 'High'
                }
            }
            
            return raw_data_perspective
            
        except Exception as e:
            self.logger.error(f"Raw data perspective analysis failed: {e}")
            return {}
    
    async def _provide_mechanism_insights(self, confluence_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Provide mechanism insights for confluence"""
        try:
            mechanism_insights = []
            
            # Confluence mechanism insight
            confluence_insight = {
                'mechanism_type': 'cross_team_confluence',
                'mechanism_description': 'Multiple intelligence teams detecting similar patterns simultaneously',
                'causal_factors': ['market_structure_change', 'institutional_flow', 'sentiment_shift'],
                'confidence': confluence_data.get('confluence_strength', 0.0),
                'predictive_value': 'high' if confluence_data.get('confluence_strength', 0.0) > 0.8 else 'medium'
            }
            mechanism_insights.append(confluence_insight)
            
            # Pattern diversity mechanism insight
            if confluence_data.get('pattern_diversity', 0.0) > 0.7:
                diversity_insight = {
                    'mechanism_type': 'pattern_diversity_confluence',
                    'mechanism_description': 'High pattern diversity indicates complex market dynamics',
                    'causal_factors': ['multi_factor_market_change', 'cross_asset_correlation', 'institutional_coordination'],
                    'confidence': confluence_data.get('pattern_diversity', 0.0),
                    'predictive_value': 'high'
                }
                mechanism_insights.append(diversity_insight)
            
            return mechanism_insights
            
        except Exception as e:
            self.logger.error(f"Mechanism insight provision failed: {e}")
            return []
    
    async def _suggest_follow_up_experiments(self, confluence_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest follow-up experiments for confluence"""
        try:
            experiment_suggestions = []
            
            # Confluence validation experiment
            confluence_experiment = {
                'experiment_type': 'confluence_validation',
                'hypothesis': 'Validate cross-team confluence through additional data sources',
                'methodology': 'Collect additional market data and validate confluence patterns',
                'expected_outcome': 'Confirmed confluence reliability',
                'priority': 'high' if confluence_data.get('confluence_strength', 0.0) > 0.8 else 'medium'
            }
            experiment_suggestions.append(confluence_experiment)
            
            # Pattern diversity experiment
            if confluence_data.get('pattern_diversity', 0.0) > 0.7:
                diversity_experiment = {
                    'experiment_type': 'pattern_diversity_analysis',
                    'hypothesis': 'Analyze pattern diversity impact on market dynamics',
                    'methodology': 'Study correlation between pattern diversity and market outcomes',
                    'expected_outcome': 'Understanding of pattern diversity significance',
                    'priority': 'medium'
                }
                experiment_suggestions.append(diversity_experiment)
            
            return experiment_suggestions
            
        except Exception as e:
            self.logger.error(f"Follow-up experiment suggestion failed: {e}")
            return []
    
    async def _calculate_cross_team_strategic_relevance(self, confluence_data: Dict[str, Any]) -> float:
        """Calculate cross-team strategic relevance"""
        try:
            strategic_relevance = 0.0
            
            # Base relevance from confluence strength
            confluence_strength = confluence_data.get('confluence_strength', 0.0)
            strategic_relevance += confluence_strength * 0.4
            
            # Team count contribution
            team_count = confluence_data.get('team_count', 0)
            team_contribution = min(0.3, team_count / len(self.intelligence_teams))
            strategic_relevance += team_contribution
            
            # Pattern diversity contribution
            pattern_diversity = confluence_data.get('pattern_diversity', 0.0)
            strategic_relevance += pattern_diversity * 0.2
            
            # Strategic significance contribution
            strategic_significance = confluence_data.get('strategic_significance', 0.0)
            strategic_relevance += strategic_significance * 0.1
            
            return min(1.0, strategic_relevance)
            
        except Exception as e:
            self.logger.error(f"Cross-team strategic relevance calculation failed: {e}")
            return 0.0
    
    def _generate_contribution_id(self, confluence_data: Dict[str, Any]) -> str:
        """Generate unique contribution ID"""
        try:
            confluence_id = confluence_data.get('confluence_id', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return f"cross_team_contribution_{confluence_id}_{timestamp}"
        except Exception as e:
            self.logger.error(f"Contribution ID generation failed: {e}")
            return f"cross_team_contribution_unknown_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def _publish_strategic_contribution(self, strategic_contribution: Dict[str, Any]) -> Optional[str]:
        """Publish strategic contribution to database"""
        try:
            # Mock implementation - in real system, this would publish to AD_strands table
            contribution_id = strategic_contribution.get('contribution_id', 'unknown')
            strand_id = f"strategic_contribution_{contribution_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            return strand_id
            
        except Exception as e:
            self.logger.error(f"Strategic contribution publishing failed: {e}")
            return None
    
    async def _track_confluence_detections(self, confluence_patterns: List[Dict[str, Any]]):
        """Track confluence detections for learning"""
        try:
            for pattern in confluence_patterns:
                detection_entry = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'confluence_id': pattern.get('confluence_id', 'unknown'),
                    'confluence_strength': pattern.get('confluence_strength', 0.0),
                    'team_count': pattern.get('team_count', 0),
                    'strategic_significance': pattern.get('strategic_significance', 0.0),
                    'pattern_types': pattern.get('pattern_types', [])
                }
                self.confluence_detections.append(detection_entry)
            
            # Keep only recent detections
            if len(self.confluence_detections) > 100:
                self.confluence_detections = self.confluence_detections[-100:]
            
        except Exception as e:
            self.logger.error(f"Confluence detection tracking failed: {e}")
    
    async def _track_lead_lag_detections(self, lead_lag_patterns: List[Dict[str, Any]]):
        """Track lead-lag detections for learning"""
        try:
            for pattern in lead_lag_patterns:
                detection_entry = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'meta_signal_id': pattern.get('meta_signal_id', 'unknown'),
                    'lead_team': pattern.get('lead_team', 'unknown'),
                    'lag_team': pattern.get('lag_team', 'unknown'),
                    'reliability_score': pattern.get('reliability_score', 0.0),
                    'meta_signal_confidence': pattern.get('meta_signal_confidence', 0.0)
                }
                self.lead_lag_detections.append(detection_entry)
            
            # Keep only recent detections
            if len(self.lead_lag_detections) > 100:
                self.lead_lag_detections = self.lead_lag_detections[-100:]
            
        except Exception as e:
            self.logger.error(f"Lead-lag detection tracking failed: {e}")
    
    def get_cross_team_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of cross-team analysis"""
        try:
            return {
                'confluence_detections': len(self.confluence_detections),
                'lead_lag_detections': len(self.lead_lag_detections),
                'strategic_contributions': len(self.strategic_contributions),
                'recent_confluence': self.confluence_detections[-5:] if self.confluence_detections else [],
                'recent_lead_lag': self.lead_lag_detections[-5:] if self.lead_lag_detections else [],
                'analysis_effectiveness': {
                    'avg_confluence_strength': np.mean([d['confluence_strength'] for d in self.confluence_detections]) if self.confluence_detections else 0.0,
                    'avg_lead_lag_reliability': np.mean([d['reliability_score'] for d in self.lead_lag_detections]) if self.lead_lag_detections else 0.0
                }
            }
            
        except Exception as e:
            self.logger.error(f"Cross-team analysis summary failed: {e}")
            return {'error': str(e)}
