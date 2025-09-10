"""
Prediction Engine - Simplified CIL Component

Main prediction creation and tracking engine that processes pattern_overview strands
and creates predictions with pattern grouping and similarity matching.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np

from src.utils.supabase_manager import SupabaseManager
from src.llm_integration.database_driven_context_system import DatabaseDrivenContextSystem
from src.llm_integration.openrouter_client import OpenRouterClient


class PredictionEngine:
    """
    Main prediction creation and tracking engine
    
    Responsibilities:
    1. Listen for pattern_overview strands (tagged with CIL)
    2. Extract and group patterns using 6-category system
    3. Create predictions with exact + similar context matching
    4. Track predictions and outcomes
    """
    
    def __init__(self, supabase_manager: SupabaseManager, llm_client: OpenRouterClient):
        self.supabase_manager = supabase_manager
        self.llm_client = llm_client
        self.context_system = DatabaseDrivenContextSystem(supabase_manager)
        self.logger = logging.getLogger(f"{__name__}.prediction_engine")
        
        # Pattern grouping system
        self.pattern_grouping = PatternGroupingSystem()
        
        # Prediction tracking
        self.prediction_tracker = PredictionTracker(supabase_manager)
        
        # Learning thresholds
        self.learning_thresholds = {
            'min_predictions_for_learning': 3,
            'min_success_rate': 0.4,
            'min_sample_size': 3
        }
    
    async def process_pattern_overview(self, overview_strand: Dict[str, Any]) -> List[str]:
        """
        Process pattern_overview strand and create predictions
        
        Args:
            overview_strand: Pattern overview strand from RMC
            
        Returns:
            List of prediction strand IDs created
        """
        try:
            self.logger.info(f"Processing pattern overview: {overview_strand.get('id')}")
            
            # 1. Extract pattern groups from overview
            pattern_groups = await self.pattern_grouping.extract_pattern_groups_from_overview(overview_strand)
            
            # 2. Create predictions for each pattern group
            prediction_ids = []
            for asset, asset_groups in pattern_groups.items():
                for group_type, groups in asset_groups.items():
                    for group in groups.values():
                        prediction_id = await self.create_prediction(group)
                        if prediction_id:
                            prediction_ids.append(prediction_id)
            
            self.logger.info(f"Created {len(prediction_ids)} predictions from overview")
            return prediction_ids
            
        except Exception as e:
            self.logger.error(f"Error processing pattern overview: {e}")
            return []
    
    async def create_prediction(self, pattern_group: Dict[str, Any]) -> Optional[str]:
        """Create prediction for a pattern group"""
        try:
            # 1. Get prediction context (exact + similar matches)
            prediction_context = await self.get_prediction_context(pattern_group)
            
            # 2. Create code prediction using historical outcomes
            code_prediction = await self.create_code_prediction(pattern_group, prediction_context)
            
            # 3. Create LLM prediction using historical outcomes
            llm_prediction = await self.create_llm_prediction(pattern_group, prediction_context)
            
            # 4. Create prediction with clear similarity indicators
            prediction = self.create_prediction_with_similarity_context(
                pattern_group, prediction_context, code_prediction, llm_prediction
            )
            
            # 5. Store prediction as strand
            prediction_strand = await self.create_prediction_strand(prediction)
            
            return prediction_strand['id']
            
        except Exception as e:
            self.logger.error(f"Error creating prediction: {e}")
            return None
    
    async def get_prediction_context(self, pattern_group: Dict[str, Any]) -> Dict[str, Any]:
        """Get context for prediction creation - exact + similar matches"""
        
        # 1. Get exact group matches
        exact_context = await self.get_exact_group_context(pattern_group)
        
        # 2. Get similar group matches (70% similarity threshold)
        similar_context = await self.get_similar_group_context(pattern_group)
        
        # 3. Combine and score confidence
        combined_context = {
            'exact_matches': exact_context,
            'similar_matches': similar_context,
            'exact_count': len(exact_context),
            'similar_count': len(similar_context),
            'confidence_level': self.calculate_confidence_level(exact_context, similar_context)
        }
        
        return combined_context
    
    async def get_exact_group_context(self, pattern_group: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get exact group signature matches"""
        group_signature = self.pattern_grouping.create_group_signature(pattern_group)
        
        # For now, return empty list - will implement proper context retrieval later
        return []
    
    async def get_similar_group_context(self, pattern_group: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get similar groups with 70% similarity threshold"""
        
        # For now, return empty list - will implement proper context retrieval later
        return []
    
    def calculate_similarity_score(self, current_group: Dict[str, Any], historical_group: Dict[str, Any]) -> float:
        """Calculate similarity score between groups"""
        
        # Pattern type overlap
        current_types = set(p['pattern_type'] for p in current_group['patterns'])
        historical_types = set(p['pattern_type'] for p in historical_group['patterns'])
        pattern_overlap = len(current_types.intersection(historical_types)) / len(current_types.union(historical_types))
        
        # Timeframe overlap
        current_timeframes = set(p['timeframe'] for p in current_group['patterns'])
        historical_timeframes = set(p['timeframe'] for p in historical_group['patterns'])
        timeframe_overlap = len(current_timeframes.intersection(historical_timeframes)) / len(current_timeframes.union(historical_timeframes))
        
        # Cycle proximity (within 10x timeframe)
        cycle_proximity = self.calculate_cycle_proximity(current_group, historical_group)
        
        # Weighted similarity score
        similarity_score = (
            pattern_overlap * 0.5 +      # 50% weight on pattern types
            timeframe_overlap * 0.3 +    # 30% weight on timeframes
            cycle_proximity * 0.2        # 20% weight on cycle proximity
        )
        
        return similarity_score
    
    def identify_differences(self, current_group: Dict[str, Any], historical_group: Dict[str, Any]) -> List[str]:
        """Identify specific differences between groups"""
        differences = []
        
        # Pattern type differences
        current_types = set(p['pattern_type'] for p in current_group['patterns'])
        historical_types = set(p['pattern_type'] for p in historical_group['patterns'])
        
        if current_types != historical_types:
            differences.append(f"Pattern types: {current_types} vs {historical_types}")
        
        # Timeframe differences
        current_timeframes = set(p['timeframe'] for p in current_group['patterns'])
        historical_timeframes = set(p['timeframe'] for p in historical_group['patterns'])
        
        if current_timeframes != historical_timeframes:
            differences.append(f"Timeframes: {current_timeframes} vs {historical_timeframes}")
        
        return differences
    
    def create_prediction_with_similarity_context(self, pattern_group: Dict[str, Any], context: Dict[str, Any], 
                                                code_prediction: Dict[str, Any], llm_prediction: Dict[str, Any]) -> Dict[str, Any]:
        """Create prediction with clear similarity indicators"""
        
        # Determine match quality
        match_quality = self.determine_match_quality(context)
        
        # Generate prediction notes
        prediction_notes = self.generate_prediction_notes(context)
        
        prediction = {
            'pattern_group': pattern_group,
            'code_prediction': code_prediction,
            'llm_prediction': llm_prediction,
            'context_metadata': {
                'exact_matches': context['exact_count'],
                'similar_matches': context['similar_count'],
                'confidence_level': context['confidence_level'],
                'similarity_scores': [g['similarity_score'] for g in context['similar_matches']],
                'match_quality': match_quality,
                'differences': self.get_all_differences(context['similar_matches'])
            },
            'prediction_notes': prediction_notes,
            'kind': 'prediction',
            'tracking_status': 'active'
        }
        
        return prediction
    
    def generate_prediction_notes(self, context: Dict[str, Any]) -> str:
        """Generate clear notes about match quality"""
        
        if context['exact_count'] > 0:
            return f"Based on {context['exact_count']} exact matches"
        elif context['similar_count'] > 0:
            avg_similarity = sum(g['similarity_score'] for g in context['similar_matches']) / len(context['similar_matches'])
            return f"Based on {context['similar_count']} similar matches (avg similarity: {avg_similarity:.2f}) - NOT EXACT MATCH"
        else:
            return "No historical matches - first prediction for this group"
    
    def determine_match_quality(self, context: Dict[str, Any]) -> str:
        """Determine overall match quality"""
        if context['exact_count'] > 0:
            return 'exact'
        elif context['similar_count'] > 0:
            return 'similar'
        else:
            return 'first_time'
    
    def get_all_differences(self, similar_matches: List[Dict[str, Any]]) -> List[str]:
        """Get all differences from similar matches"""
        all_differences = []
        for match in similar_matches:
            all_differences.extend(match['differences'])
        return list(set(all_differences))  # Remove duplicates
    
    async def create_code_prediction(self, pattern_group: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create code-based prediction using historical outcomes"""
        # TODO: Implement code prediction logic
        return {
            'method': 'code',
            'target_price': 0.0,
            'stop_loss': 0.0,
            'confidence': 0.5
        }
    
    async def create_llm_prediction(self, pattern_group: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create LLM-based prediction using historical outcomes"""
        # TODO: Implement LLM prediction logic
        return {
            'method': 'llm',
            'target_price': 0.0,
            'stop_loss': 0.0,
            'confidence': 0.5
        }
    
    async def create_prediction_strand(self, prediction: Dict[str, Any]) -> Dict[str, Any]:
        """Store prediction as strand in database"""
        # TODO: Implement strand creation
        return {
            'id': f"prediction_{int(datetime.now().timestamp())}",
            'created_at': datetime.now(timezone.utc).isoformat()
        }
    
    def calculate_confidence_level(self, exact_context: List[Dict[str, Any]], similar_context: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence level"""
        if len(exact_context) > 0:
            return 1.0
        elif len(similar_context) > 0:
            avg_similarity = sum(g['similarity_score'] for g in similar_context) / len(similar_context)
            return avg_similarity
        else:
            return 0.0
    
    def calculate_cycle_proximity(self, current_group: Dict[str, Any], historical_group: Dict[str, Any]) -> float:
        """Calculate cycle proximity (within 10x timeframe)"""
        # TODO: Implement cycle proximity calculation
        return 0.5


class PatternGroupingSystem:
    """Pattern grouping system with 6 categories"""
    
    def extract_pattern_groups_from_overview(self, overview_strand: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pattern groups from pattern_overview strand - all 6 categories"""
        
        # 1. Get linked individual patterns from overview
        individual_patterns = self.get_linked_patterns(overview_strand)
        
        # 2. Group by asset first
        asset_groups = self.group_by_asset(individual_patterns)
        
        # 3. For each asset, create all 6 grouping categories
        all_pattern_groups = {}
        
        for asset, asset_patterns in asset_groups.items():
            all_pattern_groups[asset] = {
                # A. Single patterns, single timeframe, same cycle
                'single_single': self.group_single_single(asset_patterns),
                
                # B. Multiple patterns, single timeframe, same cycle
                'multi_single': self.group_multi_single(asset_patterns),
                
                # C. Single patterns, multiple timeframes, same cycle
                'single_multi': self.group_single_multi(asset_patterns),
                
                # D. Multiple patterns, multiple timeframes, same cycle
                'multi_multi': self.group_multi_multi(asset_patterns),
                
                # E. Single patterns, single timeframe, multiple cycles
                'single_multi_cycle': self.group_single_multi_cycle(asset_patterns),
                
                # F. Multiple patterns, multiple cycles
                'multi_multi_cycle': self.group_multi_multi_cycle(asset_patterns)
            }
        
        return all_pattern_groups
    
    def get_linked_patterns(self, overview_strand: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get linked individual patterns from overview strand"""
        # TODO: Implement pattern extraction from overview strand
        return []
    
    def group_by_asset(self, patterns: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group patterns by asset"""
        asset_groups = {}
        for pattern in patterns:
            asset = pattern.get('asset', 'unknown')
            if asset not in asset_groups:
                asset_groups[asset] = []
            asset_groups[asset].append(pattern)
        return asset_groups
    
    def group_single_single(self, patterns: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """A. Single patterns, single timeframe, same cycle"""
        groups = {}
        for pattern in patterns:
            key = f"{pattern['pattern_type']}_{pattern['timeframe']}_{pattern['cycle_time']}"
            if key not in groups:
                groups[key] = {
                    'group_type': 'single_single',
                    'asset': pattern['asset'],
                    'timeframe': pattern['timeframe'],
                    'cycle_time': pattern['cycle_time'],
                    'patterns': []
                }
            groups[key]['patterns'].append(pattern)
        return groups
    
    def group_multi_single(self, patterns: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """B. Multiple patterns, single timeframe, same cycle"""
        groups = {}
        for pattern in patterns:
            key = f"{pattern['timeframe']}_{pattern['cycle_time']}"
            if key not in groups:
                groups[key] = {
                    'group_type': 'multi_single',
                    'asset': pattern['asset'],
                    'timeframe': pattern['timeframe'],
                    'cycle_time': pattern['cycle_time'],
                    'patterns': []
                }
            groups[key]['patterns'].append(pattern)
        
        # Only return groups with multiple patterns
        return {k: v for k, v in groups.items() if len(v['patterns']) > 1}
    
    def group_single_multi(self, patterns: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """C. Single patterns, multiple timeframes, same cycle"""
        groups = {}
        for pattern in patterns:
            key = f"{pattern['pattern_type']}_{pattern['cycle_time']}"
            if key not in groups:
                groups[key] = {
                    'group_type': 'single_multi',
                    'asset': pattern['asset'],
                    'pattern_type': pattern['pattern_type'],
                    'cycle_time': pattern['cycle_time'],
                    'patterns': []
                }
            groups[key]['patterns'].append(pattern)
        
        # Only return groups with multiple timeframes
        return {k: v for k, v in groups.items() if len(set(p['timeframe'] for p in v['patterns'])) > 1}
    
    def group_multi_multi(self, patterns: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """D. Multiple patterns, multiple timeframes, same cycle"""
        groups = {}
        for pattern in patterns:
            key = f"{pattern['cycle_time']}"
            if key not in groups:
                groups[key] = {
                    'group_type': 'multi_multi',
                    'asset': pattern['asset'],
                    'cycle_time': pattern['cycle_time'],
                    'patterns': []
                }
            groups[key]['patterns'].append(pattern)
        
        # Only return groups with multiple patterns AND multiple timeframes
        return {k: v for k, v in groups.items() 
                if len(v['patterns']) > 1 and len(set(p['timeframe'] for p in v['patterns'])) > 1}
    
    def group_single_multi_cycle(self, patterns: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """E. Single patterns, single timeframe, multiple cycles"""
        groups = {}
        for pattern in patterns:
            key = f"{pattern['pattern_type']}_{pattern['timeframe']}"
            if key not in groups:
                groups[key] = {
                    'group_type': 'single_multi_cycle',
                    'asset': pattern['asset'],
                    'pattern_type': pattern['pattern_type'],
                    'timeframe': pattern['timeframe'],
                    'patterns': []
                }
            groups[key]['patterns'].append(pattern)
        
        # Only return groups with multiple cycles
        return {k: v for k, v in groups.items() if len(set(p['cycle_time'] for p in v['patterns'])) > 1}
    
    def group_multi_multi_cycle(self, patterns: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """F. Multiple patterns, multiple cycles"""
        groups = {}
        for pattern in patterns:
            key = f"{pattern['asset']}"
            if key not in groups:
                groups[key] = {
                    'group_type': 'multi_multi_cycle',
                    'asset': pattern['asset'],
                    'patterns': []
                }
            groups[key]['patterns'].append(pattern)
        
        # Only return groups with multiple patterns AND multiple cycles
        return {k: v for k, v in groups.items() 
                if len(v['patterns']) > 1 and len(set(p['cycle_time'] for p in v['patterns'])) > 1}
    
    def create_group_signature(self, pattern_group: Dict[str, Any]) -> str:
        """Create unique signature for pattern group (excludes exact cycle numbers)"""
        group_type = pattern_group['group_type']
        
        if group_type == 'single_single':
            return f"{pattern_group['asset']}_{pattern_group['timeframe']}_{pattern_group['patterns'][0]['pattern_type']}"
        
        elif group_type == 'multi_single':
            pattern_types = sorted([p['pattern_type'] for p in pattern_group['patterns']])
            return f"{pattern_group['asset']}_{pattern_group['timeframe']}_{'_'.join(pattern_types)}"
        
        elif group_type == 'single_multi':
            timeframes = sorted([p['timeframe'] for p in pattern_group['patterns']])
            return f"{pattern_group['asset']}_{pattern_group['pattern_type']}_{'_'.join(timeframes)}"
        
        elif group_type == 'multi_multi':
            pattern_types = sorted([p['pattern_type'] for p in pattern_group['patterns']])
            timeframes = sorted([p['timeframe'] for p in pattern_group['patterns']])
            return f"{pattern_group['asset']}_{'_'.join(pattern_types)}_{'_'.join(timeframes)}"
        
        elif group_type == 'single_multi_cycle':
            # Count cycles, not specific cycle times
            cycle_count = len(set(p['cycle_time'] for p in pattern_group['patterns']))
            return f"{pattern_group['asset']}_{pattern_group['pattern_type']}_{pattern_group['timeframe']}_cycles_{cycle_count}"
        
        elif group_type == 'multi_multi_cycle':
            pattern_types = sorted([p['pattern_type'] for p in pattern_group['patterns']])
            cycle_count = len(set(p['cycle_time'] for p in pattern_group['patterns']))
            return f"{pattern_group['asset']}_{'_'.join(pattern_types)}_cycles_{cycle_count}"


class PredictionTracker:
    """Track predictions and outcomes"""
    
    def __init__(self, supabase_manager: SupabaseManager):
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(f"{__name__}.prediction_tracker")
    
    async def track_prediction(self, prediction: Dict[str, Any]) -> str:
        """Track a prediction"""
        # TODO: Implement prediction tracking
        return f"tracked_{int(datetime.now().timestamp())}"
    
    async def update_prediction_outcome(self, prediction_id: str, outcome: Dict[str, Any]) -> bool:
        """Update prediction with outcome"""
        # TODO: Implement outcome tracking
        return True
