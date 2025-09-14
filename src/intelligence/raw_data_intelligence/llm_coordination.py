"""
LLM Coordination Module

Handles LLM-based meta-analysis and coordination of team results.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import pandas as pd

from src.llm_integration.openrouter_client import OpenRouterClient
from src.llm_integration.prompt_manager import PromptManager


class LLMCoordination:
    """Handles LLM-based meta-analysis and coordination"""
    
    def __init__(self, llm_client: OpenRouterClient):
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
        self.logger = logging.getLogger(f"{__name__}.llm_coordination")
    
    def perform_llm_coordination(self, team_analysis: Dict[str, Any], analysis_results: Dict[str, Any], market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Use LLM to perform meta-analysis and coordination on team results
        
        Args:
            team_analysis: Analysis results from all team members
            analysis_results: Complete analysis results
            market_data: Market data for context
            
        Returns:
            LLM coordination results including meta-analysis and CIL recommendations
        """
        try:
            # Prepare context for LLM
            context = {
                'symbol': self._extract_symbol_from_data(market_data),
                'timeframe': '1m',  # Default timeframe
                'data_points': analysis_results.get('data_points', 0),
                'analysis_time': analysis_results.get('timestamp', datetime.now(timezone.utc).isoformat()),
                'team_analysis': team_analysis
            }
            
            print(f"🔍 LLM Context: {context}")  # Debug output
            
            # Get LLM prompt for coordination
            prompt = self.prompt_manager.get_prompt('raw_data_intelligence')
            print(f"🔍 Prompt template: {prompt.get('template', 'NO TEMPLATE')[:200]}...")  # Debug output
            
            # Format prompt with context
            formatted_prompt = self.prompt_manager.format_prompt('raw_data_intelligence', context)
            print(f"🔍 Formatted prompt: {formatted_prompt[:200]}...")  # Debug output
            
            # Get LLM coordination results
            llm_response = self.llm_client.generate_completion(
                formatted_prompt,
                max_tokens=2000,
                temperature=0.3
            )
            
            # Parse LLM response (extract JSON from markdown)
            try:
                # Extract content from LLM response
                content = llm_response.get('content', '{}')
                print(f"🔍 LLM Response: {content[:200]}...")  # Debug output
                
                # Extract JSON from markdown if present
                if '```json' in content:
                    # Find JSON block in markdown
                    start_marker = '```json'
                    end_marker = '```'
                    start_idx = content.find(start_marker)
                    if start_idx != -1:
                        start_idx += len(start_marker)
                        end_idx = content.find(end_marker, start_idx)
                        if end_idx != -1:
                            json_content = content[start_idx:end_idx].strip()
                            print(f"🔍 Extracted JSON: {json_content[:200]}...")  # Debug output
                            coordination_results = json.loads(json_content)
                            return coordination_results
                
                # Try parsing the entire content as JSON
                coordination_results = json.loads(content)
                return coordination_results
                
            except (json.JSONDecodeError, AttributeError) as e:
                print(f"❌ LLM JSON Parse Error: {e}")
                print(f"🔍 Raw LLM Response: {llm_response}")
                # Fallback if LLM doesn't return valid JSON
                return {
                    'coordinated_insights': [],
                    'meta_analysis': {'error': 'Invalid LLM response format'},
                    'cil_recommendations': [],
                    'overall_confidence': 0.0
                }
            
        except Exception as e:
            self.logger.error(f"LLM coordination failed: {e}")
            return {
                'coordinated_insights': [],
                'meta_analysis': {'error': str(e)},
                'cil_recommendations': [],
                'overall_confidence': 0.0
            }
    
    def _extract_symbol_from_data(self, market_data: pd.DataFrame) -> str:
        """Extract the most common symbol from market data"""
        if market_data is None or market_data.empty or 'symbol' not in market_data.columns:
            return 'BTC'  # Default fallback
        
        # Get the most common symbol
        symbol_counts = market_data['symbol'].value_counts()
        if not symbol_counts.empty:
            return symbol_counts.index[0]  # Most common symbol
        
        return 'BTC'  # Default fallback
