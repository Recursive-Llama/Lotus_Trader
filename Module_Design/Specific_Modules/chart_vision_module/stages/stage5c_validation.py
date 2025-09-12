#!/usr/bin/env python3
"""
Stage 5C: Chart Validation
==========================

Validates the rebuilt chart against the original chart using LLM analysis.
Compares:
- Element positioning accuracy
- Missing elements
- False positives
- Overall chart fidelity

Outputs validation report for quality assurance.
"""

import json
import os
import base64
from typing import Dict, List, Any, Optional
from datetime import datetime
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Stage5C_Validation:
    def __init__(self, 
                 original_image_path: str = "kaito_image_grid.png",
                 rebuilt_image_path: str = "stage5b_rebuilt_chart.png",
                 consolidated_data_path: str = "stage5a_consolidated_results.json"):
        """Initialize validation with image paths and data"""
        self.original_image_path = original_image_path
        self.rebuilt_image_path = rebuilt_image_path
        self.consolidated_data_path = consolidated_data_path
        self.consolidated_data = {}
        
    def load_data(self):
        """Load consolidated data from Stage 5A"""
        print("📊 Loading consolidated data...")
        
        with open(self.consolidated_data_path, 'r') as f:
            self.consolidated_data = json.load(f)
        
        print(f"  ✅ Consolidated data loaded")
        print(f"  ✅ Elements: {len(self.consolidated_data['chart_data']['elements'])}")
        
    def encode_image_to_base64(self, image_path: str) -> str:
        """Encode image to base64 for LLM input"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def create_validation_prompt(self) -> str:
        """Load the validation prompt from pipeline_prompts directory"""
        
        # Load the prompt from the pipeline_prompts directory
        prompt_path = "prompts/pipeline_prompts/stage5c_validation.md"
        
        try:
            with open(prompt_path, 'r') as f:
                prompt_content = f.read()
            
            # Get element information from consolidated data to append
            elements = self.consolidated_data['chart_data']['elements']
            element_info = []
            
            for element_id, element_data in elements.items():
                element_type = element_data.get('element_type', 'unknown')
                source = element_data.get('source', 'unknown')
                confidence = element_data.get('confidence', 'unknown')
                
                element_info.append(f"- {element_id}: {element_type} (detected by {source}, confidence: {confidence})")
            
            element_list = "\n".join(element_info)
            
            # Append detected elements to the prompt
            prompt_content += f"\n\n## DETECTED ELEMENTS (from our pipeline):\n{element_list}"
            
            return prompt_content
            
        except FileNotFoundError:
            print(f"  ⚠️ Prompt file not found: {prompt_path}")
            return "Please compare the two charts and provide validation feedback."
    
    def run_llm_validation(self) -> Dict[str, Any]:
        """Run LLM validation analysis"""
        print("🤖 Running LLM validation analysis...")
        
        # Encode images
        original_b64 = self.encode_image_to_base64(self.original_image_path)
        rebuilt_b64 = self.encode_image_to_base64(self.rebuilt_image_path)
        
        # Create the prompt
        prompt = self.create_validation_prompt()
        
        # Prepare messages for OpenAI
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{original_b64}",
                            "detail": "high"
                        }
                    },
                    {
                        "type": "image_url", 
                        "image_url": {
                            "url": f"data:image/png;base64,{rebuilt_b64}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ]
        
        try:
            # Call OpenAI API
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=4000,
                temperature=0.1
            )
            
            # Parse the response
            response_text = response.choices[0].message.content
            
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                validation_result = json.loads(json_match.group())
                print("  ✅ LLM validation completed")
                return validation_result
            else:
                print("  ⚠️ Could not extract JSON from LLM response")
                return {"error": "Could not parse LLM response", "raw_response": response_text}
                
        except Exception as e:
            print(f"  ❌ LLM validation failed: {e}")
            return {"error": str(e)}
    
    def create_validation_report(self, llm_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive validation report"""
        print("📋 Creating validation report...")
        
        # Get element data for additional analysis
        elements = self.consolidated_data['chart_data']['elements']
        
        # Create validation report
        validation_report = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "original_image": self.original_image_path,
                "rebuilt_image": self.rebuilt_image_path,
                "validation_method": "llm_analysis"
            },
            "llm_analysis": llm_result,
            "pipeline_analysis": {
                "total_elements": len(elements),
                "element_breakdown": self._analyze_elements(elements),
                "detection_sources": self._analyze_detection_sources(elements)
            },
            "recommendations": self._generate_recommendations(llm_result, elements)
        }
        
        return validation_report
    
    def _analyze_elements(self, elements: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze element types and sources"""
        element_types = {}
        detection_sources = {}
        
        for element_id, element_data in elements.items():
            element_type = element_data.get('element_type', 'unknown')
            source = element_data.get('source', 'unknown')
            
            element_types[element_type] = element_types.get(element_type, 0) + 1
            detection_sources[source] = detection_sources.get(source, 0) + 1
        
        return {
            "element_types": element_types,
            "detection_sources": detection_sources
        }
    
    def _analyze_detection_sources(self, elements: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze detection source quality"""
        stage4e_count = 0
        stage2_count = 0
        
        for element_id, element_data in elements.items():
            source = element_data.get('source', 'unknown')
            if source == 'stage4e':
                stage4e_count += 1
            elif source == 'stage2':
                stage2_count += 1
        
        return {
            "stage4e_elements": stage4e_count,
            "stage2_elements": stage2_count,
            "stage4e_percentage": (stage4e_count / len(elements)) * 100 if elements else 0
        }
    
    def _generate_recommendations(self, llm_result: Dict[str, Any], elements: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on validation results"""
        recommendations = []
        
        # Check for LLM recommendations
        if "recommendations" in llm_result:
            recommendations.extend(llm_result["recommendations"])
        
        # Add pipeline-specific recommendations
        stage2_elements = sum(1 for e in elements.values() if e.get('source') == 'stage2')
        if stage2_elements > 0:
            recommendations.append(f"Improve Stage 4E detection to reduce reliance on Stage 2 fallback ({stage2_elements} elements)")
        
        # Check for low confidence elements
        low_confidence = sum(1 for e in elements.values() if e.get('confidence') == 'low')
        if low_confidence > 0:
            recommendations.append(f"Review {low_confidence} low-confidence element detections")
        
        return recommendations
    
    def save_validation_report(self, report: Dict[str, Any], output_path: str = "stage5c_validation_results.json"):
        """Save validation report to file"""
        print(f"💾 Saving validation report to {output_path}...")
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"  ✅ Validation report saved")
    
    def print_summary(self, report: Dict[str, Any]):
        """Print validation summary"""
        print("\n📊 Stage 5C Validation Summary:")
        print("=" * 40)
        
        llm_analysis = report.get("llm_analysis", {})
        validation_summary = llm_analysis.get("validation_summary", {})
        
        if "error" in llm_analysis:
            print(f"❌ LLM Analysis Error: {llm_analysis['error']}")
        else:
            print(f"🎯 Story Consistency: {validation_summary.get('story_consistency', 'N/A')}")
            print(f"🎯 Element Accuracy: {validation_summary.get('element_accuracy', 'N/A')}")
            print(f"🎯 Level Precision: {validation_summary.get('level_precision', 'N/A')}")
            print(f"🎯 Overall Quality: {validation_summary.get('overall_quality', 'N/A')}")
            print(f"🎯 Confidence: {validation_summary.get('confidence', 'N/A')}")
        
        pipeline_analysis = report.get("pipeline_analysis", {})
        print(f"📊 Total Elements: {pipeline_analysis.get('total_elements', 0)}")
        
        element_breakdown = pipeline_analysis.get("element_breakdown", {})
        print(f"📊 Element Types: {element_breakdown.get('element_types', {})}")
        print(f"📊 Detection Sources: {element_breakdown.get('detection_sources', {})}")
        
        recommendations = report.get("recommendations", [])
        if recommendations:
            print(f"\n💡 Recommendations ({len(recommendations)}):")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        print("\n🎉 Stage 5C validation completed!")
    
    def run(self):
        """Run Stage 5C validation"""
        print("🚀 Starting Stage 5C: Chart Validation")
        print("=" * 50)
        
        # Load data
        self.load_data()
        
        # Check if images exist
        if not os.path.exists(self.original_image_path):
            print(f"❌ Original image not found: {self.original_image_path}")
            return None
            
        if not os.path.exists(self.rebuilt_image_path):
            print(f"❌ Rebuilt image not found: {self.rebuilt_image_path}")
            return None
        
        # Run LLM validation
        llm_result = self.run_llm_validation()
        
        # Create validation report
        validation_report = self.create_validation_report(llm_result)
        
        # Save report
        self.save_validation_report(validation_report)
        
        # Print summary
        self.print_summary(validation_report)
        
        return validation_report

if __name__ == "__main__":
    validator = Stage5C_Validation()
    results = validator.run()
