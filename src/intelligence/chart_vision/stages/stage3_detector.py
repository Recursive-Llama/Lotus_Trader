#!/usr/bin/env python3
"""
Stage 3: Trader Intent Inference

This stage takes the grid image and detected elements to infer trader intent and strategy.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from PIL import Image
import base64
import io
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Stage3Detector:
    """Stage 3: Trader Intent Inference"""
    
    def __init__(self, detector):
        """Initialize with the element detector."""
        self.detector = detector
    
    async def run_stage3(self, grid_image_path: str, stage2_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run Stage 3: Trader Intent Inference.
        
        Args:
            grid_image_path: Path to the grid overlay image
            stage2_results: Results from Stage 2 (grid mapping + precision detection)
            
        Returns:
            Dict containing trader intent analysis
        """
        try:
            print("🎯 STAGE 3: TRADER INTENT INFERENCE")
            print("=" * 50)
            
            # Load Stage 3 prompt
            with open("prompts/pipeline_prompts/stage3_trader_intent.md", "r") as f:
                stage3_prompt = f.read()
            
            # Build concise element list with ordering: Arrow → Zones → Diagonals → Horizontals
            concise_elements = self._build_concise_elements(stage2_results)
            
            # Log elements JSON for verification
            os.makedirs('stage3_debug', exist_ok=True)
            with open('stage3_debug/elements_sent.json', 'w') as f:
                json.dump(concise_elements, f, indent=2)
            
            print(f"📋 Built concise element list: {len(concise_elements)} elements")
            
            # Encode grid image
            pil = Image.open(grid_image_path)
            buf = io.BytesIO()
            pil.save(buf, format='PNG')
            buf.seek(0)
            b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            # Prepare content for LLM
            content_text = f"{stage3_prompt}\n\n## Elements\n{json.dumps(concise_elements, indent=2)}"
            
            # Create messages for LLM
            messages = [{
                "role": "user",
                "content": [
                    {"type": "text", "text": content_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}}
                ]
            }]
            
            print("🧠 Calling LLM for trader intent inference...")
            
            # Call LLM directly for intent inference
            intent_reply = await self.detector.call_llm_direct(
                messages, 
                model="gpt-4o", 
                max_tokens=400, 
                temperature=0.2
            )
            
            if not intent_reply:
                print("❌ No LLM response received")
                return {}
            
            # Save intent output for debugging
            with open('stage3_debug/intent_output.txt', 'w') as f:
                f.write(intent_reply)
            
            print("✅ Trader intent inference completed")
            
            # Parse and structure the response
            parsed_intent = self._parse_intent_response(intent_reply)
            
            # Compile final results
            final_results = {
                "trader_intent": parsed_intent,
                "raw_response": intent_reply,
                "elements_analyzed": concise_elements,
                "grid_image_path": grid_image_path,
                "debug_files": {
                    "elements_sent": "stage3_debug/elements_sent.json",
                    "intent_output": "stage3_debug/intent_output.txt"
                }
            }
            
            # Save results for debugging
            with open('stage3_results.json', 'w') as f:
                json.dump(final_results, f, indent=2)
            
            print("✅ Stage 3 completed successfully!")
            return final_results
            
        except Exception as e:
            print(f"❌ Stage 3 failed: {e}")
            logger.error(f"Stage 3 error: {e}", exc_info=True)
            raise
    
    def _build_concise_elements(self, stage2_results: Dict[str, Any]) -> List[Dict]:
        """Build concise element list with proper ordering."""
        concise_elements = []
        
        # Extract data from Stage 2 results
        stage2a_data = stage2_results.get('stage2a_results', {})
        stage2b_data = stage2_results.get('stage2b_results', {})
        stage2c_data = stage2_results.get('stage2c_results', {})
        
        # Helper functions for labeling elements
        def get_zone_span(z):
            area = z.get('area') or z.get('area_description') or ''
            return area.replace('to','→').replace(' ', '')
        
        def label_zone(eid, z):
            span = get_zone_span(z)
            color = (z.get('description','').lower().split(' ')[1] if ' ' in z.get('description','') else '').replace('support','').replace('resistance','')
            short = 'red zone' if 'red' in z.get('description','').lower() else ('blue zone' if 'blue' in z.get('description','').lower() else 'zone')
            label = f"{eid} ({short}, {span})" if span else f"{eid} ({short})"
            return {
                "element_id": eid,
                "type": "zone",
                "label": label,
                "cells": span,
                "color": 'red' if 'red' in z.get('description','').lower() else ('blue' if 'blue' in z.get('description','').lower() else '')
            }
        
        def label_diag(eid, d):
            start = d.get('start', '')
            end = d.get('end', '')
            cells = f"{start}→{end}" if start and end else (start or end)
            return {"element_id": eid, "type": "diagonal_line", "label": f"{eid} (diagonal, {cells})", "cells": cells}
        
        def label_hline(eid, h):
            row = h.get('row')
            row_txt = f"Row {row}" if row else ''
            return {"element_id": eid, "type": "horizontal_line", "label": f"{eid} (horizontal, {row_txt})", "row": row}
        
        def label_arrow(eid, a):
            cells = a.get('start') and a.get('end') and f"{a.get('start')}→{a.get('end')}" or ''
            return {"element_id": eid, "type": "arrow", "label": f"{eid} (arrow, {cells})", "cells": cells}
        
        # 1) Arrows (highest priority - shows direction)
        if 'arrows' in stage2a_data:
            for arrow in stage2a_data['arrows']:
                eid = arrow.get('element_id')
                concise_elements.append(label_arrow(eid, arrow))
        
        # 2) Zones (support/resistance areas)
        if 'zones' in stage2c_data:
            for zone in stage2c_data['zones']:
                eid = zone.get('element_id')
                concise_elements.append(label_zone(eid, zone))
        
        # 3) Diagonal lines (trend lines)
        if 'diagonal_lines' in stage2b_data:
            for diag in stage2b_data['diagonal_lines']:
                eid = diag.get('element_id')
                concise_elements.append(label_diag(eid, diag))
        
        # 4) Horizontal lines (support/resistance levels)
        if 'horizontal_lines' in stage2a_data:
            for hline in stage2a_data['horizontal_lines']:
                eid = hline.get('element_id')
                concise_elements.append(label_hline(eid, hline))
        
        return concise_elements
    
    def _parse_intent_response(self, intent_reply: str) -> Dict[str, Any]:
        """Parse the LLM response for trader intent."""
        try:
            # Try to extract structured information from the response
            parsed = {
                "strategy": "unknown",
                "direction": "unknown",
                "key_levels": [],
                "entry_points": [],
                "risk_level": "unknown",
                "confidence": "unknown",
                "notes": intent_reply
            }
            
            # Simple keyword extraction for now
            intent_lower = intent_reply.lower()
            
            # Determine strategy
            if any(word in intent_lower for word in ["long", "buy", "bullish", "uptrend"]):
                parsed["strategy"] = "long"
                parsed["direction"] = "up"
            elif any(word in intent_lower for word in ["short", "sell", "bearish", "downtrend"]):
                parsed["strategy"] = "short"
                parsed["direction"] = "down"
            elif any(word in intent_lower for word in ["range", "sideways", "consolidation"]):
                parsed["strategy"] = "range"
                parsed["direction"] = "sideways"
            
            # Determine risk level
            if any(word in intent_lower for word in ["high risk", "aggressive", "speculative"]):
                parsed["risk_level"] = "high"
            elif any(word in intent_lower for word in ["low risk", "conservative", "safe"]):
                parsed["risk_level"] = "low"
            else:
                parsed["risk_level"] = "medium"
            
            # Determine confidence
            if any(word in intent_lower for word in ["high confidence", "strong", "clear", "obvious"]):
                parsed["confidence"] = "high"
            elif any(word in intent_lower for word in ["low confidence", "uncertain", "unclear", "weak"]):
                parsed["confidence"] = "low"
            else:
                parsed["confidence"] = "medium"
            
            return parsed
            
        except Exception as e:
            logger.warning(f"Failed to parse intent response: {e}")
            return {
                "strategy": "unknown",
                "direction": "unknown",
                "key_levels": [],
                "entry_points": [],
                "risk_level": "unknown",
                "confidence": "unknown",
                "notes": intent_reply
            }
