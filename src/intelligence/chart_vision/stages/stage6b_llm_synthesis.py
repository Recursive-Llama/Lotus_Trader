#!/usr/bin/env python3
"""
Stage 6B: LLM Review & Synthesis

Takes Stage 6A data + Trader Intent and synthesizes trading scenarios.
Maps trader's visual intent to actual prices and identifies opportunities.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from openai import OpenAI

class Stage6BLLMSynthesis:
    """Stage 6B: LLM Review & Synthesis"""
    
    def __init__(self, openai_api_key: str):
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.logger = logging.getLogger(__name__)
    
    async def synthesize_trading_scenarios(self, stage6a_data: Dict[str, Any], trader_intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize trading scenarios from Stage 6A data and trader intent
        
        Args:
            stage6a_data: Output from Stage 6A data collection
            trader_intent: Trader intent from Stage 3
            
        Returns:
            Synthesized trading scenarios and analysis
        """
        try:
            # Load the LLM prompt
            prompt = self._load_synthesis_prompt()
            
            # Format the data for LLM
            formatted_data = self._format_data_for_llm(stage6a_data, trader_intent)
            
            # Make LLM call
            response = await self._call_llm(prompt, formatted_data)
            
            # Parse and structure the response
            synthesis_result = self._parse_llm_response(response)
            
            # Add metadata
            synthesis_result.update({
                "stage": "6b",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source": "llm_synthesis"
            })
            
            return synthesis_result
            
        except Exception as e:
            self.logger.error(f"Error in Stage 6B synthesis: {e}")
            raise
    
    def _load_synthesis_prompt(self) -> str:
        """Load the LLM synthesis prompt"""
        prompt_path = Path(__file__).parent.parent / "pipeline_prompts" / "stage6b_llm_synthesis.md"
        with open(prompt_path, 'r') as f:
            return f.read()
    
    def _format_data_for_llm(self, stage6a_data: Dict[str, Any], trader_intent: Dict[str, Any]) -> str:
        """Format data for LLM consumption - utilizing ALL Stage 6A data"""
        return f"""
DETECTED ELEMENTS (with exact prices):
{json.dumps(stage6a_data.get('elements', {}), indent=2)}

TRADER INTENT (from arrows/annotations):
{json.dumps(trader_intent, indent=2)}

STAGE 6A COMPREHENSIVE ANALYSIS:
- Current price: {stage6a_data.get('current_price', 'Unknown')}
- Breakout status: {stage6a_data.get('breakout_status', 'Unknown')}
- Execution readiness: {stage6a_data.get('execution_readiness', 'Unknown')}
- Side: {stage6a_data.get('side', 'Unknown')}

VOLUME ANALYSIS (with specific breakout thresholds):
{json.dumps(stage6a_data.get('token_context', {}).get('volume_analysis', {}), indent=2)}

VOLATILITY ANALYSIS:
{json.dumps(stage6a_data.get('token_context', {}).get('volatility_analysis', {}), indent=2)}

PRICE POSITION ANALYSIS (including diagonal breakouts):
{json.dumps(stage6a_data.get('price_position_analysis', {}), indent=2)}

DERIVED TRADING INTELLIGENCE:
{json.dumps(stage6a_data.get('derived', {}), indent=2)}

TRADING TARGETS:
{json.dumps(stage6a_data.get('targets', []), indent=2)}

ENTRY HINT:
{json.dumps(stage6a_data.get('entry_hint', {}), indent=2)}

RISK METRICS:
{json.dumps(stage6a_data.get('derived', {}).get('risk', {}), indent=2)}

INVALIDATION LEVELS:
{json.dumps(stage6a_data.get('invalidation_levels', []), indent=2)}

RR ESTIMATE:
{json.dumps(stage6a_data.get('rr_estimate', {}), indent=2)}

ELEMENT SEQUENCES (detailed event tracking):
{json.dumps(stage6a_data.get('price_position_analysis', {}).get('elements', {}), indent=2)}

BREAKOUT VOLUME THRESHOLDS (for conditional scenarios):
- Average breakout volume: {stage6a_data.get('token_context', {}).get('volume_analysis', {}).get('breakout_volume_analysis', {}).get('average_breakout_volume', 'Unknown')}
- Max breakout volume: {stage6a_data.get('token_context', {}).get('volume_analysis', {}).get('breakout_volume_analysis', {}).get('max_breakout_volume', 'Unknown')}
- Recent average volume: {stage6a_data.get('token_context', {}).get('volume_analysis', {}).get('recent_average', 'Unknown')}
- Current volume: {stage6a_data.get('token_context', {}).get('volume_analysis', {}).get('current_volume', 'Unknown')}
"""
    
    async def _call_llm(self, prompt: str, data: str) -> str:
        """Make LLM call for synthesis"""
        full_prompt = f"{prompt}\n\n{data}"
        
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.3
        )
        
        return response.choices[0].message.content
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured data"""
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            json_str = response[json_start:json_end]
            return json.loads(json_str)
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            return {"error": "Failed to parse LLM response", "raw_response": response}
