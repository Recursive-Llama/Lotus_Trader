#!/usr/bin/env python3
"""
Stage 1: Element Detection, Validation, and Info Pack Creation

This stage handles:
- Stage 1A: Horizontal lines and arrows detection
- Stage 1B: Diagonal lines detection  
- Stage 1C: Zones and text labels detection
- Stage 1D: Validation and feedback
- Info pack creation for Stage 2
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Stage1Detector:
    """Stage 1: Element Detection and Validation"""
    
    def __init__(self, detector):
        """Initialize with the element detector."""
        self.detector = detector
    
    async def run_stage1(self, image_path: str) -> Dict[str, Any]:
        """
        Run the complete Stage 1 pipeline.
        
        Args:
            image_path: Path to the chart image
            
        Returns:
            Dict containing:
            - stage1_results: All detected and validated elements
            - info_packs: The 3 info packs for Stage 2
            - validation_summary: Summary of validation results
        """
        try:
            print("🎯 STAGE 1: ELEMENT DETECTION AND VALIDATION")
            print("=" * 50)
            
            # Stage 1A, 1B, 1C: Concurrent element detection
            print("🔍 Running Stages 1A, 1B, 1C concurrently...")
            stage1_results = await self._detect_elements_concurrent(image_path)
            
            # Stage 1D: Validation and feedback
            print("✅ Running Stage 1D: Validation and feedback...")
            validation_results = await self._validate_elements(image_path, stage1_results)
            
            # Create info packs for Stage 2
            print("📦 Creating info packs for Stage 2...")
            info_packs = self._create_info_packs(validation_results)
            
            # Compile final results
            final_results = {
                "stage1_results": stage1_results,
                "validation_results": validation_results,
                "info_packs": info_packs,
                "validation_summary": self._create_validation_summary(validation_results)
            }
            
            # Save results for debugging
            with open('stage1_results.json', 'w') as f:
                json.dump(final_results, f, indent=2)
            
            print("✅ Stage 1 completed successfully!")
            return final_results
            
        except Exception as e:
            print(f"❌ Stage 1 failed: {e}")
            logger.error(f"Stage 1 error: {e}", exc_info=True)
            raise
    
    async def _detect_elements_concurrent(self, image_path: str) -> Dict[str, List]:
        """Run Stages 1A, 1B, 1C concurrently."""
        tasks = [
            self.detector.detect_elements(image_path, "stage1a_lines_arrows.md"),
            self.detector.detect_elements(image_path, "stage1b_diagonal_detection.md"),
            self.detector.detect_elements(image_path, "stage1c_zones.md")
        ]
        
        results = await asyncio.gather(*tasks)
        result_1a, result_1b, result_1c = results
        
        # Extract results
        stage1_results = {
            "horizontal_lines": result_1a.get("horizontal_lines", []),
            "arrows": result_1a.get("arrows", []),
            "diagonal_lines": result_1b.get("diagonal_lines", []),
            "zones": result_1c.get("zones", []),
            "text_labels": result_1c.get("text_labels", [])
        }
        
        # Log results
        print(f"✅ Stage 1A: {len(stage1_results['horizontal_lines'])} horizontal lines, {len(stage1_results['arrows'])} arrows")
        print(f"✅ Stage 1B: {len(stage1_results['diagonal_lines'])} diagonal lines")
        print(f"✅ Stage 1C: {len(stage1_results['zones'])} zones, {len(stage1_results['text_labels'])} text labels")
        
        return stage1_results
    
    async def _validate_elements(self, image_path: str, stage1_results: Dict[str, List]) -> Dict[str, Any]:
        """Run Stage 1D: Validation and feedback."""
        # Prepare elements for validation
        all_elements = {
            "horizontal_lines": stage1_results["horizontal_lines"],
            "arrows": stage1_results["arrows"],
            "diagonal_lines": stage1_results["diagonal_lines"],
            "zones": stage1_results["zones"],
            "text_labels": stage1_results["text_labels"]
        }
        
        # Create validation prompt
        validation_prompt = self._create_validation_prompt(all_elements)
        
        # Run validation
        validation_result = await self.detector.detect_elements(image_path, validation_prompt)
        
        if "validation_results" in validation_result:
            return validation_result["validation_results"]
        else:
            print("⚠️ No validation results structure in response")
            return {"element_reviews": [], "missing_elements": []}
    
    def _create_validation_prompt(self, all_elements: Dict[str, List]) -> str:
        """Create the Stage 1D validation prompt."""
        return f"""# Stage 1D: Element Validation & Feedback

You are reviewing a list of detected trader-drawn elements on a trading chart.

## DETECTED ELEMENTS TO REVIEW:

{json.dumps(all_elements, indent=2)}

## Your Task
**Review each of the detected elements above and provide feedback on accuracy and completeness.**

## STEP 1: Review Each Detected Element (One by One)
**Go through the detected elements systematically:**

1. **Take the first detected element** - Does it actually exist on the chart?
2. **Mark it as exists: true/false** with confidence level
3. **Add specific notes** explaining why it exists or doesn't
4. **Repeat for every single detected element**

## STEP 2: Look for Missing Elements
**After reviewing all detected elements:**

5. **Check if anything obvious was missed** - What else should be detected?
6. **Add any missing elements** with confidence levels
7. **Provide specific descriptions** of what was overlooked

## Important: Be Systematic
- **Review elements one by one** - don't skip any
- **Be explicit about each review** - clear tick/cross for each
- **Give specific reasons** for why each element exists or doesn't
- **Then do completeness check** for missing elements

## Output Format
```json
{{
  "validation_results": {{
    "element_reviews": [
      {{
        "element_id": "element_1",
        "description": "Description from detected elements",
        "exists": true,
        "confidence": "high",
        "notes": "Specific reason why it exists or doesn't"
      }}
    ],
    "missing_elements": [
      {{
        "type": "zone",
        "description": "Description of missing element",
        "confidence": "medium",
        "notes": "Why it was overlooked"
      }}
    ],
    "summary": {{
      "total_reviewed": 8,
      "total_confirmed": 7,
      "total_false_positives": 1,
      "total_missing": 1,
      "overall_accuracy": "good"
    }}
  }}
}}

## Important
- **Review the detected elements above carefully**
- **Be systematic** - Review each detected element one by one
- **Be critical** - Don't just agree with everything
- **Mark each element clearly** - exists: true/false for every single one
- **Look for false positives** - Lines that aren't actually drawn
- **Check for missing elements** - Obvious things that should be detected
- **Provide specific feedback** - Don't just say "wrong", explain why
- **Rate confidence** - high/medium/low for each assessment"""
    
    def _create_info_packs(self, validation_results: Dict[str, Any]) -> Dict[str, Dict]:
        """Create the 3 separate info packs for Stage 2."""
        element_reviews = validation_results.get("element_reviews", [])
        
        # Initialize the 3 separate info packs
        horizontal_lines_arrows_pack = {
            "chart_image": "kaito_image.png",  # Will be updated by caller
            "total_elements": 0,
            "elements": {}
        }
        
        diagonal_lines_pack = {
            "chart_image": "kaito_image.png",  # Will be updated by caller
            "total_elements": 0,
            "elements": {}
        }
        
        zones_text_pack = {
            "chart_image": "kaito_image.png",  # Will be updated by caller
            "total_elements": 0,
            "elements": {}
        }
        
        # Process each validated element and add to appropriate pack
        for i, review in enumerate(element_reviews, 1):
            element_id = f"ELEMENT_{i:02d}"
            
            # Determine element type from description
            element_type = self._determine_element_type(review.get("description", ""))
            
            element_info = {
                "id": element_id,
                "type": element_type,
                "description": review.get("description", ""),
                "exists": review.get("exists", False),
                "confidence": review.get("confidence", "unknown"),
                "notes": review.get("notes", ""),
                "original_detection": self._find_original_detection(review.get("description", ""))
            }
            
            # Add to appropriate pack
            if element_type in ["horizontal_line", "arrow"]:
                horizontal_lines_arrows_pack["elements"][element_id] = element_info
                horizontal_lines_arrows_pack["total_elements"] += 1
            elif element_type == "diagonal_line":
                diagonal_lines_pack["elements"][element_id] = element_info
                diagonal_lines_pack["total_elements"] += 1
            elif element_type in ["zone", "text_label"]:
                zones_text_pack["elements"][element_id] = element_info
                zones_text_pack["total_elements"] += 1
            else:
                # Fallback for unknown types
                zones_text_pack["elements"][element_id] = element_info
                zones_text_pack["total_elements"] += 1
        
        return {
            "horizontal_lines_arrows_pack": horizontal_lines_arrows_pack,
            "diagonal_lines_pack": diagonal_lines_pack,
            "zones_text_pack": zones_text_pack
        }
    
    def _determine_element_type(self, description: str) -> str:
        """Determine the element type from description."""
        description_lower = description.lower()
        
        # Tight zone match: do NOT treat generic 'area' as a zone keyword
        if any(word in description_lower for word in ["zone", "box"]):
            return "zone"
        elif any(word in description_lower for word in ["horizontal", "support", "resistance", "level"]):
            return "horizontal_line"
        elif any(word in description_lower for word in ["diagonal", "trend", "wedge", "sloping"]):
            return "diagonal_line"
        elif any(word in description_lower for word in ["arrow", "indicator"]):
            return "arrow"
        elif any(word in description_lower for word in ["label", "text", "content"]):
            return "text_label"
        else:
            return "unknown"
    
    def _find_original_detection(self, description: str) -> Dict[str, Any]:
        """Find the original detection data for a validated element."""
        # This is a simplified version - in practice, we'd track the original source
        return {
            "source_stage": "unknown",
            "original_data": {}
        }
    
    def _create_validation_summary(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of validation results."""
        element_reviews = validation_results.get("element_reviews", [])
        missing_elements = validation_results.get("missing_elements", [])
        
        total_reviewed = len(element_reviews)
        total_confirmed = len([r for r in element_reviews if r.get("exists", False)])
        total_false_positives = total_reviewed - total_confirmed
        
        return {
            "total_reviewed": total_reviewed,
            "total_confirmed": total_confirmed,
            "total_false_positives": total_false_positives,
            "total_missing": len(missing_elements),
            "overall_accuracy": "good" if total_confirmed / max(total_reviewed, 1) > 0.8 else "needs_improvement"
        }
