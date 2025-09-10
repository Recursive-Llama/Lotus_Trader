"""
Prediction Engine - Simplified CIL Component

Main prediction creation and tracking engine that processes pattern_overview strands
and creates predictions with pattern grouping and similarity matching.
"""

import asyncio
import logging
import json
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
        """Get exact group signature matches from prediction reviews"""
        try:
            group_signature = self.pattern_grouping.create_group_signature(pattern_group)
            
            # Query for exact group signature matches in prediction reviews
            query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'prediction_review' 
                AND content->>'group_signature' = %s
                AND content->>'asset' = %s
                ORDER BY created_at DESC
                LIMIT 20
            """
            
            result = await self.supabase_manager.execute_query(query, [
                group_signature, 
                pattern_group['asset']
            ])
            
            return [dict(row) for row in result]
            
        except Exception as e:
            self.logger.error(f"Error getting exact group context: {e}")
            return []
    
    async def get_similar_group_context(self, pattern_group: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get similar groups with 70% similarity threshold from prediction reviews"""
        try:
            # Query for similar groups (same asset, same group type)
            query = """
                SELECT * FROM AD_strands 
                WHERE kind = 'prediction_review' 
                AND content->>'asset' = %s
                AND content->>'group_type' = %s
                ORDER BY created_at DESC
                LIMIT 50
            """
            
            result = await self.supabase_manager.execute_query(query, [
                pattern_group['asset'],
                pattern_group['group_type']
            ])
            
            # Score similarity for each group
            scored_groups = []
            for row in result:
                group = dict(row)
                similarity_score = self.calculate_similarity_score(pattern_group, group)
                if similarity_score >= 0.7:  # 70% similarity threshold
                    scored_groups.append({
                        'group': group,
                        'similarity_score': similarity_score,
                        'match_type': 'similar',
                        'differences': self.identify_differences(pattern_group, group)
                    })
            
            return scored_groups
            
        except Exception as e:
            self.logger.error(f"Error getting similar group context: {e}")
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
        try:
            # Get historical outcomes from context
            historical_outcomes = self.extract_historical_outcomes(context)
            
            if not historical_outcomes:
                # No historical data - create conservative prediction
                return self.create_conservative_prediction(pattern_group)
            
            # Calculate prediction based on historical outcomes
            prediction = self.calculate_prediction_from_outcomes(pattern_group, historical_outcomes)
            
            return {
                'method': 'code',
                'target_price': prediction['target_price'],
                'stop_loss': prediction['stop_loss'],
                'confidence': prediction['confidence'],
                'direction': prediction['direction'],
                'duration_hours': prediction['duration_hours'],
                'historical_basis': {
                    'sample_size': len(historical_outcomes),
                    'success_rate': prediction['success_rate'],
                    'avg_return': prediction['avg_return'],
                    'max_drawdown': prediction['max_drawdown']
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error creating code prediction: {e}")
            return self.create_conservative_prediction(pattern_group)
    
    def extract_historical_outcomes(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract historical outcomes from context"""
        outcomes = []
        
        # Extract from exact matches
        for match in context.get('exact_matches', []):
            if 'outcome' in match.get('content', {}):
                outcomes.append(match['content']['outcome'])
        
        # Extract from similar matches
        for match in context.get('similar_matches', []):
            if 'outcome' in match.get('group', {}).get('content', {}):
                outcomes.append(match['group']['content']['outcome'])
        
        return outcomes
    
    def calculate_prediction_from_outcomes(self, pattern_group: Dict[str, Any], outcomes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate prediction from historical outcomes"""
        if not outcomes:
            return self.create_conservative_prediction(pattern_group)
        
        # Calculate statistics
        returns = [o.get('return_pct', 0) for o in outcomes if 'return_pct' in o]
        success_rate = len([r for r in returns if r > 0]) / len(returns) if returns else 0.5
        
        avg_return = sum(returns) / len(returns) if returns else 0.0
        max_drawdown = min(returns) if returns else -0.02
        
        # Calculate target price and stop loss
        current_price = 50000  # TODO: Get actual current price
        target_return = avg_return * 0.8  # Conservative estimate
        stop_loss_pct = abs(max_drawdown) * 1.2  # Slightly wider stop
        
        target_price = current_price * (1 + target_return / 100)
        stop_loss = current_price * (1 - stop_loss_pct / 100)
        
        # Calculate confidence based on sample size and success rate
        confidence = min(0.9, 0.3 + (len(outcomes) * 0.1) + (success_rate * 0.4))
        
        # Determine direction
        direction = 'long' if avg_return > 0 else 'short'
        
        # Calculate duration (20x timeframe)
        timeframe_hours = self.get_timeframe_hours(pattern_group.get('timeframe', '1h'))
        duration_hours = timeframe_hours * 20
        
        return {
            'target_price': target_price,
            'stop_loss': stop_loss,
            'confidence': confidence,
            'direction': direction,
            'duration_hours': duration_hours,
            'success_rate': success_rate,
            'avg_return': avg_return,
            'max_drawdown': max_drawdown
        }
    
    def create_conservative_prediction(self, pattern_group: Dict[str, Any]) -> Dict[str, Any]:
        """Create conservative prediction when no historical data available"""
        current_price = 50000  # TODO: Get actual current price
        
        return {
            'method': 'code',
            'target_price': current_price * 1.01,  # 1% target
            'stop_loss': current_price * 0.99,     # 1% stop
            'confidence': 0.3,                     # Low confidence
            'direction': 'long',
            'duration_hours': 20,                  # 20 hours
            'historical_basis': {
                'sample_size': 0,
                'success_rate': 0.5,
                'avg_return': 0.0,
                'max_drawdown': -0.01
            }
        }
    
    def get_timeframe_hours(self, timeframe: str) -> float:
        """Convert timeframe string to hours"""
        timeframe_map = {
            '1m': 1/60,
            '5m': 5/60,
            '15m': 15/60,
            '1h': 1,
            '4h': 4,
            '1d': 24
        }
        return timeframe_map.get(timeframe, 1)
    
    async def create_llm_prediction(self, pattern_group: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Create LLM-based prediction using historical outcomes"""
        try:
            # Prepare context for LLM
            llm_context = self.prepare_llm_context(pattern_group, context)
            
            # Create LLM prompt
            prompt = self.create_prediction_prompt(pattern_group, llm_context)
            
            # Get LLM prediction
            llm_response = self.llm_client.generate_completion(prompt)
            
            # Parse LLM response
            prediction = self.parse_llm_prediction(llm_response, pattern_group)
            
            return {
                'method': 'llm',
                'target_price': prediction['target_price'],
                'stop_loss': prediction['stop_loss'],
                'confidence': prediction['confidence'],
                'direction': prediction['direction'],
                'duration_hours': prediction['duration_hours'],
                'reasoning': prediction['reasoning'],
                'historical_basis': {
                    'sample_size': context.get('exact_count', 0) + context.get('similar_count', 0),
                    'match_quality': context.get('confidence_level', 0.0),
                    'similarity_scores': [g['similarity_score'] for g in context.get('similar_matches', [])]
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error creating LLM prediction: {e}")
            return self.create_conservative_prediction(pattern_group)
    
    def prepare_llm_context(self, pattern_group: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context for LLM prediction"""
        return {
            'pattern_group': pattern_group,
            'exact_matches': context.get('exact_matches', []),
            'similar_matches': context.get('similar_matches', []),
            'exact_count': context.get('exact_count', 0),
            'similar_count': context.get('similar_count', 0),
            'confidence_level': context.get('confidence_level', 0.0)
        }
    
    def create_prediction_prompt(self, pattern_group: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create prompt for LLM prediction"""
        
        # Extract historical outcomes
        historical_outcomes = []
        for match in context.get('exact_matches', []):
            if 'outcome' in match.get('content', {}):
                historical_outcomes.append(match['content']['outcome'])
        
        for match in context.get('similar_matches', []):
            if 'outcome' in match.get('group', {}).get('content', {}):
                historical_outcomes.append(match['group']['content']['outcome'])
        
        prompt = f"""
You are a quantitative trading analyst. Create a prediction based on the following pattern group and historical data.

PATTERN GROUP:
- Asset: {pattern_group['asset']}
- Group Type: {pattern_group['group_type']}
- Timeframe: {pattern_group.get('timeframe', 'N/A')}
- Patterns: {[p['pattern_type'] for p in pattern_group['patterns']]}

HISTORICAL CONTEXT:
- Exact Matches: {context.get('exact_count', 0)}
- Similar Matches: {context.get('similar_count', 0)}
- Confidence Level: {context.get('confidence_level', 0.0):.2f}

HISTORICAL OUTCOMES:
{self.format_historical_outcomes(historical_outcomes)}

TASK:
Create a trading prediction with:
1. Target price (current price is $50,000)
2. Stop loss price
3. Direction (long/short)
4. Duration in hours
5. Confidence level (0.0-1.0)
6. Brief reasoning

RESPONSE FORMAT (JSON):
{{
    "target_price": 51000,
    "stop_loss": 49500,
    "direction": "long",
    "duration_hours": 20,
    "confidence": 0.7,
    "reasoning": "Based on historical volume spike patterns showing 60% success rate with average 2% returns"
}}
"""
        return prompt
    
    def format_historical_outcomes(self, outcomes: List[Dict[str, Any]]) -> str:
        """Format historical outcomes for LLM prompt"""
        if not outcomes:
            return "No historical data available"
        
        formatted = []
        for i, outcome in enumerate(outcomes[:5]):  # Limit to 5 examples
            formatted.append(f"  {i+1}. Return: {outcome.get('return_pct', 'N/A')}%, "
                           f"Success: {outcome.get('success', 'N/A')}, "
                           f"Max DD: {outcome.get('max_drawdown', 'N/A')}%")
        
        return "\n".join(formatted)
    
    def parse_llm_prediction(self, llm_response: str, pattern_group: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM response into prediction format"""
        try:
            import json
            
            # Handle both string and dict responses
            if isinstance(llm_response, dict):
                response_text = llm_response.get('content', str(llm_response))
            else:
                response_text = str(llm_response)
            
            # Extract JSON from response
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                json_str = response_text[json_start:json_end].strip()
            else:
                json_str = response_text.strip()
            
            prediction = json.loads(json_str)
            
            # Validate and set defaults
            return {
                'target_price': float(prediction.get('target_price', 50000)),
                'stop_loss': float(prediction.get('stop_loss', 49500)),
                'direction': prediction.get('direction', 'long'),
                'duration_hours': float(prediction.get('duration_hours', 20)),
                'confidence': float(prediction.get('confidence', 0.5)),
                'reasoning': prediction.get('reasoning', 'LLM prediction based on pattern analysis')
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing LLM prediction: {e}")
            # Return conservative prediction if parsing fails
            return {
                'target_price': 50000 * 1.01,
                'stop_loss': 50000 * 0.99,
                'direction': 'long',
                'duration_hours': 20,
                'confidence': 0.3,
                'reasoning': 'Conservative prediction due to parsing error'
            }
    
    async def create_prediction_strand(self, prediction: Dict[str, Any]) -> Dict[str, Any]:
        """Store prediction as strand in database"""
        try:
            # Create prediction strand data
            strand_data = {
                'id': f"prediction_{int(datetime.now().timestamp())}",
                'kind': 'prediction',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'tags': ['cil', 'prediction'],
                'content': {
                    'pattern_group': prediction['pattern_group'],
                    'code_prediction': prediction['code_prediction'],
                    'llm_prediction': prediction['llm_prediction'],
                    'context_metadata': prediction['context_metadata'],
                    'prediction_notes': prediction['prediction_notes'],
                    'tracking_status': 'active',
                    'created_by': 'prediction_engine'
                },
                'metadata': {
                    'asset': prediction['pattern_group']['asset'],
                    'group_type': prediction['pattern_group']['group_type'],
                    'timeframe': prediction['pattern_group'].get('timeframe', 'N/A'),
                    'confidence_level': prediction['context_metadata']['confidence_level'],
                    'match_quality': prediction['context_metadata']['match_quality']
                }
            }
            
            # Store in database
            await self.supabase_manager.execute_query("""
                INSERT INTO AD_strands (id, kind, created_at, tags, content, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [
                strand_data['id'],
                strand_data['kind'],
                strand_data['created_at'],
                strand_data['tags'],
                json.dumps(strand_data['content']),
                json.dumps(strand_data['metadata'])
            ])
            
            self.logger.info(f"Created prediction strand: {strand_data['id']}")
            return strand_data
            
        except Exception as e:
            self.logger.error(f"Error creating prediction strand: {e}")
            return {
                'id': f"prediction_error_{int(datetime.now().timestamp())}",
                'created_at': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
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
    
    async def create_prediction_review_strand(self, prediction: Dict[str, Any], outcome: Dict[str, Any]) -> str:
        """Create prediction review strand for clustering and learning"""
        try:
            # Create group signature
            group_signature = self.pattern_grouping.create_group_signature(prediction['pattern_group'])
            
            # Create prediction review strand
            review_strand = {
                'id': f"prediction_review_{int(datetime.now().timestamp())}",
                'kind': 'prediction_review',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'tags': ['cil', 'prediction_review', 'learning'],
                'content': {
                    'group_signature': group_signature,
                    'pattern_group': prediction['pattern_group'],
                    'prediction_id': prediction.get('id'),
                    'outcome': outcome,
                    'success': outcome.get('success', False),
                    'return_pct': outcome.get('return_pct', 0.0),
                    'max_drawdown': outcome.get('max_drawdown', 0.0),
                    'confidence': prediction.get('confidence', 0.0),
                    'method': prediction.get('method', 'unknown'),
                    'duration_hours': outcome.get('duration_hours', 0.0)
                },
                'metadata': {
                    'asset': prediction['pattern_group']['asset'],
                    'group_type': prediction['pattern_group']['group_type'],
                    'timeframe': prediction['pattern_group'].get('timeframe', 'N/A'),
                    'success': outcome.get('success', False),
                    'return_pct': outcome.get('return_pct', 0.0)
                }
            }
            
            # Store in database
            await self.supabase_manager.execute_query("""
                INSERT INTO AD_strands (id, kind, created_at, tags, content, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [
                review_strand['id'],
                review_strand['kind'],
                review_strand['created_at'],
                review_strand['tags'],
                json.dumps(review_strand['content']),
                json.dumps(review_strand['metadata'])
            ])
            
            self.logger.info(f"Created prediction review strand: {review_strand['id']}")
            return review_strand['id']
            
        except Exception as e:
            self.logger.error(f"Error creating prediction review strand: {e}")
            return f"error: {str(e)}"


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
