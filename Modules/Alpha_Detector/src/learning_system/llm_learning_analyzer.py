"""
LLM Learning Analyzer - Phase 4

Analyzes prediction review clusters using LLM to extract numerical, stats-focused learning insights.
Pulls in original pattern strands for full context: Pattern → Prediction → Outcome → Learning.
"""

import logging
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


class LLMLearningAnalyzer:
    """
    Analyzes prediction review clusters using LLM to extract learning insights
    
    Responsibilities:
    1. Get original pattern strands for context
    2. Prepare cluster data for LLM analysis
    3. Create LLM prompts for cluster analysis
    4. Parse LLM responses into structured insights
    5. Create learning braid strands
    """
    
    def __init__(self, llm_client, supabase_manager):
        self.llm_client = llm_client
        self.supabase_manager = supabase_manager
        self.logger = logging.getLogger(f"{__name__}.llm_learning_analyzer")
    
    async def analyze_cluster_for_learning(self, cluster_type: str, cluster_key: str, 
                                         prediction_reviews: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Analyze a cluster of prediction reviews and extract learning insights
        
        Args:
            cluster_type: Type of cluster (pattern_timeframe, asset, etc.)
            cluster_key: Specific cluster key (BTC, success, etc.)
            prediction_reviews: List of prediction review strands
            
        Returns:
            Learning braid strand with insights, or None if analysis failed
        """
        try:
            self.logger.info(f"Analyzing cluster {cluster_type}:{cluster_key} with {len(prediction_reviews)} reviews")
            
            # 1. Get original pattern strands for context
            pattern_context = await self.get_original_pattern_context(prediction_reviews)
            
            # 2. Prepare cluster data for LLM analysis
            cluster_data = self.prepare_cluster_data(cluster_type, cluster_key, prediction_reviews, pattern_context)
            
            # 3. Create LLM prompt for cluster analysis
            prompt = self.create_cluster_analysis_prompt(cluster_data)
            
            # 4. Get LLM analysis
            llm_response = self.llm_client.generate_completion(prompt)
            
            # 5. Parse and structure the learning insights
            learning_insights = self.parse_learning_insights(llm_response, cluster_type, cluster_key)
            
            # 6. Create learning braid strand
            learning_braid = await self.create_learning_braid(learning_insights, cluster_type, cluster_key)
            
            self.logger.info(f"Created learning braid for {cluster_type}:{cluster_key}")
            return learning_braid
            
        except Exception as e:
            self.logger.error(f"Error analyzing cluster {cluster_type}:{cluster_key}: {e}")
            return None
    
    async def get_original_pattern_context(self, prediction_reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get original pattern strands that led to these predictions
        
        Reads from both 'content' and 'module_intelligence' fields for robust data access.
        """
        
        pattern_contexts = []
        
        for pr in prediction_reviews:
            # Get original pattern strand IDs from prediction review
            # Try content first, then fall back to module_intelligence
            pattern_strand_ids = []
            
            content = pr.get('content', {})
            if isinstance(content, dict) and content.get('original_pattern_strand_ids'):
                pattern_strand_ids = content.get('original_pattern_strand_ids', [])
            else:
                module_intelligence = pr.get('module_intelligence', {})
                if isinstance(module_intelligence, dict) and module_intelligence.get('original_pattern_strand_ids'):
                    pattern_strand_ids = module_intelligence.get('original_pattern_strand_ids', [])
            
            # Query database for each pattern strand
            for strand_id in pattern_strand_ids:
                pattern_strand = await self.get_pattern_strand_by_id(strand_id)
                if pattern_strand:
                    pattern_contexts.append(pattern_strand)
        
        self.logger.info(f"Retrieved {len(pattern_contexts)} original pattern strands")
        return pattern_contexts
    
    async def get_pattern_strand_by_id(self, strand_id: str) -> Optional[Dict[str, Any]]:
        """Get pattern strand by ID from database using Supabase client"""
        
        try:
            result = self.supabase_manager.client.table('ad_strands').select('*').eq('id', strand_id).eq('kind', 'pattern').execute()
            
            if result.data:
                return result.data[0]
            else:
                self.logger.warning(f"Pattern strand not found: {strand_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting pattern strand {strand_id}: {e}")
            return None
    
    def prepare_cluster_data(self, cluster_type: str, cluster_key: str, 
                           prediction_reviews: List[Dict[str, Any]], 
                           pattern_contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare structured data for LLM analysis
        
        Reads from both 'content' and 'module_intelligence' fields for robust data access.
        """
        
        # Helper function to get value from either field
        def get_value(pr: Dict[str, Any], key: str, default=0):
            # Try content first
            content = pr.get('content', {})
            if isinstance(content, dict) and content.get(key) is not None:
                return content.get(key, default)
            # Fall back to module_intelligence
            module_intelligence = pr.get('module_intelligence', {})
            if isinstance(module_intelligence, dict) and module_intelligence.get(key) is not None:
                return module_intelligence.get(key, default)
            return default
        
        # Calculate cluster statistics using robust data access
        success_count = 0
        for pr in prediction_reviews:
            success = get_value(pr, 'success', False)
            # Handle both boolean and string values
            if isinstance(success, str):
                success = success.lower() in ('true', '1', 'yes')
            if success:
                success_count += 1
        
        success_rate = success_count / len(prediction_reviews) if prediction_reviews else 0
        
        confidences = [get_value(pr, 'confidence', 0) for pr in prediction_reviews]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        returns = [get_value(pr, 'return_pct', 0) for pr in prediction_reviews]
        avg_return = sum(returns) / len(returns) if returns else 0
        
        drawdowns = [get_value(pr, 'max_drawdown', 0) for pr in prediction_reviews]
        avg_drawdown = sum(drawdowns) / len(drawdowns) if drawdowns else 0
        
        return {
            'cluster_type': cluster_type,
            'cluster_key': cluster_key,
            'prediction_count': len(prediction_reviews),
            'predictions': prediction_reviews,
            'original_patterns': pattern_contexts,
            'success_rate': success_rate,
            'avg_confidence': avg_confidence,
            'avg_return': avg_return,
            'avg_drawdown': avg_drawdown,
            'success_count': success_count,
            'failure_count': len(prediction_reviews) - success_count
        }
    
    def create_cluster_analysis_prompt(self, cluster_data: Dict[str, Any]) -> str:
        """Create LLM prompt for cluster analysis"""
        
        # Format prediction details
        prediction_details = self.format_prediction_details(cluster_data['predictions'])
        
        # Format pattern details
        pattern_details = self.format_pattern_details(cluster_data['original_patterns'])
        
        prompt = f"""
Analyze this cluster of {cluster_data['cluster_type']} predictions and extract numerical, stats-focused learning insights.

CLUSTER INFORMATION:
- Cluster Type: {cluster_data['cluster_type']}
- Cluster Key: {cluster_data['cluster_key']}
- Prediction Count: {cluster_data['prediction_count']}
- Success Rate: {cluster_data['success_rate']:.2%}
- Success Count: {cluster_data['success_count']}
- Failure Count: {cluster_data['failure_count']}
- Avg Confidence: {cluster_data['avg_confidence']:.2f}
- Avg Return: {cluster_data['avg_return']:.2%}
- Avg Drawdown: {cluster_data['avg_drawdown']:.2%}

PREDICTION DETAILS:
{prediction_details}

ORIGINAL PATTERNS:
{pattern_details}

ANALYSIS TASK:
Please analyze this data and provide numerical, stats-focused insights on:

1. PATTERNS OBSERVED:
   - What patterns can we see in the data?
   - What statistical relationships exist?
   - What numerical trends are present?

2. MISTAKES IDENTIFIED:
   - What mistakes did we make?
   - What patterns led to failures?
   - What numerical indicators of failure?

3. SUCCESS FACTORS:
   - What did we do well?
   - What patterns led to success?
   - What numerical indicators of success?

4. LESSONS LEARNED:
   - What can we learn from this cluster?
   - What statistical insights emerge?
   - What numerical patterns should we remember?

5. RECOMMENDATIONS:
   - What should we do differently next time?
   - What numerical thresholds should we use?
   - What statistical criteria should we apply?

IMPORTANT: Keep your analysis numerical and stats-focused. No narratives, just facts and insights.
Focus on numbers, percentages, statistical relationships, and quantitative patterns.
"""

        return prompt
    
    def format_prediction_details(self, predictions: List[Dict[str, Any]]) -> str:
        """Format prediction details for LLM prompt
        
        Reads from both 'content' and 'module_intelligence' fields for robust data access.
        """
        
        if not predictions:
            return "No prediction data available"
        
        # Helper function to get value from either field
        def get_value(pred: Dict[str, Any], key: str, default='N/A'):
            # Try content first
            content = pred.get('content', {})
            if isinstance(content, dict) and content.get(key) is not None:
                return content.get(key, default)
            # Fall back to module_intelligence
            module_intelligence = pred.get('module_intelligence', {})
            if isinstance(module_intelligence, dict) and module_intelligence.get(key) is not None:
                return module_intelligence.get(key, default)
            return default
        
        formatted = []
        for i, pred in enumerate(predictions[:10]):  # Limit to 10 examples
            formatted.append(
                f"  {i+1}. Success: {get_value(pred, 'success')}, "
                f"Return: {get_value(pred, 'return_pct')}%, "
                f"Confidence: {get_value(pred, 'confidence')}, "
                f"Method: {get_value(pred, 'method')}, "
                f"Drawdown: {get_value(pred, 'max_drawdown')}%"
            )
        
        return "\n".join(formatted)
    
    def format_pattern_details(self, patterns: List[Dict[str, Any]]) -> str:
        """Format pattern details for LLM prompt"""
        
        if not patterns:
            return "No original pattern data available"
        
        formatted = []
        for i, pattern in enumerate(patterns[:10]):  # Limit to 10 examples
            content = pattern.get('content', {})
            formatted.append(
                f"  {i+1}. Type: {content.get('pattern_type', 'N/A')}, "
                f"Timeframe: {content.get('timeframe', 'N/A')}, "
                f"Confidence: {content.get('confidence', 'N/A')}, "
                f"Asset: {content.get('symbol', 'N/A')}"
            )
        
        return "\n".join(formatted)
    
    def parse_learning_insights(self, llm_response: str, cluster_type: str, cluster_key: str) -> Dict[str, Any]:
        """Parse LLM response into structured learning insights"""
        
        try:
            # Handle both string and dict responses
            if isinstance(llm_response, dict):
                response_text = llm_response.get('content', str(llm_response))
            else:
                response_text = str(llm_response)
            
            # Store full LLM response without parsing
            return {
                'cluster_type': cluster_type,
                'cluster_key': cluster_key,
                'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
                'llm_response': response_text,
                'metadata': {
                    'llm_model': 'openrouter',
                    'analysis_type': 'cluster_learning',
                    'confidence': self.calculate_analysis_confidence(response_text)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing learning insights: {e}")
            return {
                'cluster_type': cluster_type,
                'cluster_key': cluster_key,
                'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
                'insights': {
                    'patterns_observed': 'Analysis failed',
                    'mistakes_identified': 'Analysis failed',
                    'success_factors': 'Analysis failed',
                    'lessons_learned': 'Analysis failed',
                    'recommendations': 'Analysis failed'
                },
                'metadata': {
                    'llm_model': 'openrouter',
                    'analysis_type': 'cluster_learning',
                    'confidence': 0.0,
                    'error': str(e)
                }
            }
    
    def extract_section(self, text: str, section_name: str) -> str:
        """Extract a specific section from LLM response"""
        
        try:
            # Look for section header
            start_marker = f"{section_name}:"
            end_marker = "\n\n"
            
            start_idx = text.find(start_marker)
            if start_idx == -1:
                return f"Section {section_name} not found"
            
            # Find the end of this section
            start_idx += len(start_marker)
            end_idx = text.find(end_marker, start_idx)
            if end_idx == -1:
                end_idx = len(text)
            
            section_text = text[start_idx:end_idx].strip()
            return section_text if section_text else f"Section {section_name} is empty"
            
        except Exception as e:
            self.logger.warning(f"Error extracting section {section_name}: {e}")
            return f"Error extracting {section_name}"
    
    def calculate_analysis_confidence(self, response_text: str) -> float:
        """Calculate confidence in the analysis based on response quality"""
        
        try:
            # Simple heuristic: longer, more detailed responses are more confident
            word_count = len(response_text.split())
            
            # Check for numerical content (indicates statistical analysis)
            import re
            numbers = len(re.findall(r'\d+\.?\d*', response_text))
            
            # Calculate confidence based on content quality
            confidence = min(1.0, (word_count / 100) + (numbers / 50))
            return max(0.1, confidence)  # Minimum 10% confidence
            
        except Exception as e:
            self.logger.warning(f"Error calculating analysis confidence: {e}")
            return 0.5  # Default 50% confidence
    
    async def create_learning_braid(self, learning_insights: Dict[str, Any], 
                                  cluster_type: str, cluster_key: str) -> Dict[str, Any]:
        """Create learning braid strand from insights"""
        
        try:
            # Create new prediction_review strand with braid_level + 1
            learning_braid = {
                'id': f"pred_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}",
                'kind': 'prediction_review',  # Keep same kind!
                'created_at': datetime.now(timezone.utc).isoformat(),
                'tags': ['cil', 'learning', 'braid', f'cluster_{cluster_type}'],
                'braid_level': 2,  # Upgraded level
                'lesson': learning_insights.get('insights', {}).get('lessons_learned', ''),  # Store LLM insights
                'content': {
                    'cluster_type': cluster_type,
                    'cluster_key': cluster_key,
                    'learning_insights': learning_insights,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'braid_level': 2,
                    'source_cluster': f"{cluster_type}_{cluster_key}"
                },
                'module_intelligence': {
                    'cluster_type': cluster_type,
                    'cluster_key': cluster_key,
                    'braid_level': 2,
                    'analysis_timestamp': learning_insights.get('analysis_timestamp'),
                    'confidence': learning_insights.get('metadata', {}).get('confidence', 0.0)
                }
            }
            
            # Store learning braid in database
            await self.store_learning_braid(learning_braid, cluster_type, cluster_key)
            
            return learning_braid
            
        except Exception as e:
            self.logger.error(f"Error creating learning braid: {e}")
            return None
    
    async def store_learning_braid(self, learning_braid: Dict[str, Any], cluster_type: str, cluster_key: str) -> bool:
        """Store learning braid in database using proper Supabase client method"""
        
        try:
            # Prepare strand data for Supabase client
            strand_data = {
                'id': learning_braid['id'],
                'module': 'alpha',
                'kind': learning_braid['kind'],
                'symbol': learning_braid['content'].get('cluster_key', 'UNKNOWN'),
                'timeframe': '1h',  # Default timeframe
                'tags': learning_braid['tags'],
                'created_at': learning_braid['created_at'],
                'updated_at': learning_braid['created_at'],
                'braid_level': learning_braid['braid_level'],
                'lesson': learning_braid['content'].get('learning_insights', {}).get('llm_response', ''),
                'content': learning_braid['content'],
                'module_intelligence': learning_braid['module_intelligence'],
                'cluster_key': self._create_braid_cluster_keys(cluster_type, cluster_key)  # Inherit from parent cluster
            }
            
            # Use proper Supabase client method instead of raw SQL
            result = self.supabase_manager.insert_strand(strand_data)
            
            if result:
                self.logger.info(f"Stored learning braid: {learning_braid['id']}")
                return True
            else:
                self.logger.error(f"Failed to store learning braid: {learning_braid['id']}")
                return False
            
        except Exception as e:
            self.logger.error(f"Error storing learning braid: {e}")
            return False
    
    def _create_braid_cluster_keys(self, cluster_type: str, cluster_key: str) -> List[Dict[str, Any]]:
        """Create cluster keys for a braid strand based on its parent cluster
        
        The braid inherits the cluster key from its parent cluster, so it can be
        grouped with other braids of the same type for future learning cycles.
        """
        
        return [{
            'cluster_type': cluster_type,
            'cluster_key': cluster_key,
            'braid_level': 2,  # This is a level 2 braid
            'consumed': False  # Not yet consumed for further braiding
        }]
