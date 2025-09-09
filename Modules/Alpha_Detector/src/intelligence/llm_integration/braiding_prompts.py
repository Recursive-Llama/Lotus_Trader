"""
Braiding Prompts for Learning System

This module provides structured prompts for compressing strands into braids
using LLM integration. It includes prompts for different types of braids
and learning insights.

Features:
1. Structured prompts for different braid types
2. Context-aware prompt generation
3. LLM response parsing and validation
4. Fallback templates for when LLM is unavailable
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)


class BraidingPrompts:
    """
    Manages LLM prompts for braid creation and learning insights
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize braiding prompts
        
        Args:
            llm_client: LLM client for generating braids (optional)
        """
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # Prompt templates for different braid types
        self.prompt_templates = {
            'raw_data_intelligence': self._get_raw_data_prompt,
            'central_intelligence_layer': self._get_cil_prompt,
            'trading_plan': self._get_trading_plan_prompt,
            'mixed_braid': self._get_mixed_braid_prompt,
            'universal_braid': self._get_universal_braid_prompt
        }
    
    async def generate_braid_lesson(self, strands: List[Dict[str, Any]], braid_type: str = 'universal_braid') -> str:
        """
        Generate braid lesson using LLM
        
        Args:
            strands: List of strands to compress into braid
            braid_type: Type of braid to generate
            
        Returns:
            Generated braid lesson
        """
        try:
            if not self.llm_client:
                return self._generate_fallback_lesson(strands, braid_type)
            
            # Get appropriate prompt template
            prompt_func = self.prompt_templates.get(braid_type, self._get_universal_braid_prompt)
            prompt = prompt_func(strands)
            
            # Generate lesson using LLM
            response = await self.llm_client.generate_completion(
                prompt=prompt,
                max_tokens=500,
                temperature=0.7
            )
            
            # Parse and validate response
            lesson = self._parse_llm_response(response, braid_type)
            
            self.logger.info(f"Generated {braid_type} lesson for {len(strands)} strands")
            return lesson
            
        except Exception as e:
            self.logger.error(f"Error generating braid lesson: {e}")
            return self._generate_fallback_lesson(strands, braid_type)
    
    def _get_raw_data_prompt(self, strands: List[Dict[str, Any]]) -> str:
        """Generate prompt for raw data intelligence braids"""
        strand_summary = self._summarize_strands(strands)
        
        return f"""
You are an expert market analyst analyzing raw data intelligence patterns. 

STRANDS TO ANALYZE:
{strand_summary}

TASK: Compress these similar market intelligence strands into a single, actionable braid lesson.

Focus on:
1. What market patterns do these strands reveal?
2. What are the common characteristics of successful signals?
3. What conditions lead to these patterns?
4. What actionable insights can be extracted?
5. What are the key risk factors to watch?

Format your response as a structured lesson with:
- Pattern Summary
- Key Conditions
- Actionable Insights
- Risk Factors
- Confidence Level

Keep it concise but comprehensive.
"""
    
    def _get_cil_prompt(self, strands: List[Dict[str, Any]]) -> str:
        """Generate prompt for CIL braids"""
        strand_summary = self._summarize_strands(strands)
        
        return f"""
You are a central intelligence analyst synthesizing strategic insights from multiple intelligence strands.

STRANDS TO ANALYZE:
{strand_summary}

TASK: Create a strategic intelligence braid that synthesizes these strands into actionable doctrine.

Focus on:
1. What strategic patterns emerge from these strands?
2. What are the key decision-making factors?
3. What doctrine updates are needed?
4. What are the strategic implications?
5. What actions should be taken?

Format your response as a strategic intelligence brief with:
- Strategic Summary
- Key Patterns
- Doctrine Implications
- Recommended Actions
- Confidence Assessment

Make it actionable for trading decisions.
"""
    
    def _get_trading_plan_prompt(self, strands: List[Dict[str, Any]]) -> str:
        """Generate prompt for trading plan braids"""
        strand_summary = self._summarize_strands(strands)
        
        return f"""
You are a trading strategy expert analyzing multiple trading plans to extract the best practices.

TRADING PLANS TO ANALYZE:
{strand_summary}

TASK: Create a consolidated trading plan braid that combines the best elements of these plans.

Focus on:
1. What are the most successful trading patterns?
2. What are the optimal entry/exit conditions?
3. What risk management rules work best?
4. What market conditions favor these strategies?
5. How can these plans be optimized?

Format your response as a trading strategy with:
- Strategy Overview
- Entry Conditions
- Exit Rules
- Risk Management
- Market Conditions
- Performance Expectations

Make it ready for implementation.
"""
    
    def _get_mixed_braid_prompt(self, strands: List[Dict[str, Any]]) -> str:
        """Generate prompt for mixed-type braids"""
        strand_summary = self._summarize_strands(strands)
        
        return f"""
You are a comprehensive market analyst synthesizing insights from diverse intelligence sources.

MIXED STRANDS TO ANALYZE:
{strand_summary}

TASK: Create a unified braid that connects insights across different intelligence types.

Focus on:
1. What connections exist between these different strand types?
2. What unified patterns emerge?
3. How do different intelligence sources reinforce each other?
4. What are the cross-cutting insights?
5. What integrated actions are recommended?

Format your response as an integrated intelligence brief with:
- Unified Summary
- Cross-Connections
- Integrated Insights
- Holistic Recommendations
- Confidence Level

Synthesize across all intelligence types.
"""
    
    def _get_universal_braid_prompt(self, strands: List[Dict[str, Any]]) -> str:
        """Generate prompt for universal braids"""
        strand_summary = self._summarize_strands(strands)
        
        return f"""
You are an advanced AI system analyzing patterns across all types of market intelligence.

UNIVERSAL STRANDS TO ANALYZE:
{strand_summary}

TASK: Create a universal braid that extracts the most important patterns and insights.

Focus on:
1. What are the most significant patterns across all strands?
2. What are the common success factors?
3. What are the key failure modes to avoid?
4. What are the most actionable insights?
5. What are the highest-confidence recommendations?

Format your response as a universal intelligence brief with:
- Pattern Summary
- Success Factors
- Failure Modes
- Key Insights
- Recommendations
- Confidence Level

Extract the most valuable insights across all types.
"""
    
    def _summarize_strands(self, strands: List[Dict[str, Any]]) -> str:
        """Create a summary of strands for prompt context"""
        try:
            summary_parts = []
            
            for i, strand in enumerate(strands[:10]):  # Limit to first 10 strands
                strand_info = {
                    'id': strand.get('id', f'strand_{i}'),
                    'kind': strand.get('kind', 'unknown'),
                    'agent_id': strand.get('agent_id', 'unknown'),
                    'symbol': strand.get('symbol', 'unknown'),
                    'timeframe': strand.get('timeframe', 'unknown'),
                    'pattern_type': strand.get('pattern_type', 'unknown'),
                    'confidence': strand.get('sig_confidence', strand.get('confidence', 0.0)),
                    'persistence': strand.get('persistence_score', 0.0),
                    'novelty': strand.get('novelty_score', 0.0),
                    'surprise': strand.get('surprise_rating', 0.0)
                }
                
                summary_parts.append(f"Strand {i+1}: {strand_info}")
            
            if len(strands) > 10:
                summary_parts.append(f"... and {len(strands) - 10} more strands")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            self.logger.error(f"Error summarizing strands: {e}")
            return f"Error summarizing {len(strands)} strands"
    
    def _parse_llm_response(self, response: str, braid_type: str) -> str:
        """Parse and validate LLM response"""
        try:
            # Basic validation
            if not response or len(response.strip()) < 50:
                raise ValueError("Response too short")
            
            # Clean up response
            response = response.strip()
            
            # Add metadata
            metadata = {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'braid_type': braid_type,
                'llm_generated': True
            }
            
            # Format as structured lesson
            structured_lesson = f"""
# {braid_type.replace('_', ' ').title()} Lesson

{response}

---
*Generated by AI Learning System at {metadata['generated_at']}*
"""
            
            return structured_lesson
            
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            return response  # Return raw response if parsing fails
    
    def _generate_fallback_lesson(self, strands: List[Dict[str, Any]], braid_type: str) -> str:
        """Generate fallback lesson when LLM is unavailable"""
        try:
            # Calculate basic statistics
            total_strands = len(strands)
            avg_persistence = sum(s.get('persistence_score', 0.0) for s in strands) / total_strands
            avg_novelty = sum(s.get('novelty_score', 0.0) for s in strands) / total_strands
            avg_surprise = sum(s.get('surprise_rating', 0.0) for s in strands) / total_strands
            
            # Get common patterns
            pattern_types = [s.get('pattern_type', 'unknown') for s in strands]
            common_patterns = list(set(pattern_types))
            
            # Get common symbols
            symbols = [s.get('symbol', 'unknown') for s in strands]
            common_symbols = list(set(symbols))
            
            # Generate fallback lesson
            fallback_lesson = f"""
# {braid_type.replace('_', ' ').title()} Lesson (Fallback)

## Pattern Summary
This braid contains {total_strands} strands with the following characteristics:
- Average Persistence: {avg_persistence:.2f}
- Average Novelty: {avg_novelty:.2f}
- Average Surprise: {avg_surprise:.2f}

## Common Patterns
- Pattern Types: {', '.join(common_patterns)}
- Symbols: {', '.join(common_symbols)}

## Key Insights
- This cluster represents a recurring pattern in the market
- The patterns show {avg_persistence:.1%} persistence and {avg_novelty:.1%} novelty
- These insights can be used for future market analysis

## Recommendations
- Monitor for similar patterns in the future
- Consider these patterns in trading decisions
- Update doctrine based on these insights

---
*Generated by Fallback System at {datetime.now(timezone.utc).isoformat()}*
"""
            
            return fallback_lesson
            
        except Exception as e:
            self.logger.error(f"Error generating fallback lesson: {e}")
            return f"Error generating lesson for {len(strands)} strands"
    
    async def generate_conditional_plan_prompt(self, cluster_analysis: Dict[str, Any]) -> str:
        """Generate prompt for conditional plan creation"""
        try:
            cluster_key = cluster_analysis.get('cluster_key', 'unknown')
            success_rate = cluster_analysis.get('overall_success_rate', 0.0)
            avg_rr = cluster_analysis.get('avg_rr', 0.0)
            sample_size = cluster_analysis.get('sample_size', 0)
            
            prompt = f"""
You are a trading strategy expert creating a conditional plan based on cluster analysis.

CLUSTER ANALYSIS:
- Cluster Key: {cluster_key}
- Success Rate: {success_rate:.1%}
- Average R/R: {avg_rr:.2f}
- Sample Size: {sample_size}

TASK: Create a detailed conditional trading plan based on this analysis.

Focus on:
1. What are the optimal entry conditions?
2. What are the exit rules?
3. What risk management should be applied?
4. What market conditions favor this plan?
5. How should position sizing be determined?

Format your response as a trading plan with:
- Plan Overview
- Entry Conditions
- Exit Rules
- Risk Management
- Position Sizing
- Market Conditions
- Performance Expectations

Make it actionable and specific.
"""
            
            return prompt
            
        except Exception as e:
            self.logger.error(f"Error generating conditional plan prompt: {e}")
            return "Error generating conditional plan prompt"
    
    async def generate_plan_evolution_prompt(self, current_plan: Dict[str, Any], evolution_data: Dict[str, Any]) -> str:
        """Generate prompt for plan evolution"""
        try:
            plan_id = current_plan.get('plan_id', 'unknown')
            current_success_rate = current_plan.get('success_rate', 0.0)
            evolution_recommendations = evolution_data.get('recommendations', [])
            
            prompt = f"""
You are a trading strategy expert evolving an existing conditional plan.

CURRENT PLAN:
- Plan ID: {plan_id}
- Current Success Rate: {current_success_rate:.1%}

EVOLUTION DATA:
- Recommendations: {', '.join(evolution_recommendations)}

TASK: Update the conditional plan based on the evolution recommendations.

Focus on:
1. How should the plan be modified based on the recommendations?
2. What parameters need adjustment?
3. What new conditions should be added?
4. What existing conditions should be removed?
5. How should the plan be optimized?

Format your response as an updated trading plan with:
- Updated Overview
- Modified Conditions
- New Rules
- Optimized Parameters
- Performance Expectations

Make the changes specific and actionable.
"""
            
            return prompt
            
        except Exception as e:
            self.logger.error(f"Error generating plan evolution prompt: {e}")
            return "Error generating plan evolution prompt"


# Example usage and testing
if __name__ == "__main__":
    # Test the braiding prompts
    prompts = BraidingPrompts()
    
    # Test strands
    test_strands = [
        {
            'id': 'strand_1',
            'kind': 'intelligence',
            'agent_id': 'raw_data_intelligence',
            'symbol': 'BTC',
            'timeframe': '1h',
            'pattern_type': 'volume_spike',
            'persistence_score': 0.8,
            'novelty_score': 0.6,
            'surprise_rating': 0.7
        },
        {
            'id': 'strand_2',
            'kind': 'intelligence',
            'agent_id': 'raw_data_intelligence',
            'symbol': 'BTC',
            'timeframe': '1h',
            'pattern_type': 'volume_spike',
            'persistence_score': 0.7,
            'novelty_score': 0.5,
            'surprise_rating': 0.6
        }
    ]
    
    # Test fallback lesson generation
    lesson = prompts._generate_fallback_lesson(test_strands, 'raw_data_intelligence')
    print("Fallback Lesson:")
    print(lesson)
