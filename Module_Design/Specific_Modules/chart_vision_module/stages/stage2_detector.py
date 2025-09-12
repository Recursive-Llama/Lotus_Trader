#!/usr/bin/env python3
"""
Stage 2: Grid Mapping and Precision Detection

This stage handles:
- Grid overlay creation
- Stage 2A: Grid mapping for horizontal lines & arrows
- Stage 2B: Grid mapping for diagonal lines  
- Stage 2C: Grid mapping for zones & text
- Stage 2Di: OpenCV precision detection for horizontals
- Stage 2Dii: LLM precision detection for diagonals
- Stage 2Diii: LLM precision detection for zones
- Stage 2E: Final validation
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import base64
import io

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Stage2Detector:
    """Stage 2: Grid Mapping and Precision Detection"""
    
    def __init__(self, detector):
        """Initialize with the element detector."""
        self.detector = detector
    
    async def run_stage2(self, image_path: str, info_packs: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Run the complete Stage 2 pipeline.
        
        Args:
            image_path: Path to the chart image
            info_packs: The 3 info packs from Stage 1
            
        Returns:
            Dict containing all Stage 2 results
        """
        try:
            print("🎯 STAGE 2: GRID MAPPING AND PRECISION DETECTION")
            print("=" * 50)
            
            # Phase 1: Grid creation (sequential)
            print("🔄 Creating grid overlay...")
            grid_image_path, grid_metadata = await self._create_grid_overlay(image_path)
            print(f"✅ Grid overlay created: {grid_image_path}")
            
            # Phase 2: Grid mapping (parallel)
            print("🔍 Running grid mapping in parallel...")
            stage2a_result, stage2b_result, stage2c_result = await asyncio.gather(
                self._run_stage2a(grid_image_path, info_packs["horizontal_lines_arrows_pack"]),
                self._run_stage2b(grid_image_path, info_packs["diagonal_lines_pack"]),
                self._run_stage2c(grid_image_path, info_packs["zones_text_pack"])
            )
            
            # Phase 3: Precision detection (parallel)
            print("🎯 Running precision detection in parallel...")
            stage2di_result, stage2dii_result, stage2diii_result = await asyncio.gather(
                self._run_stage2di(image_path, stage2a_result, grid_metadata),
                self._run_stage2dii(image_path, stage2b_result, grid_metadata),
                self._run_stage2diii(image_path, stage2c_result, grid_metadata)
            )
            
            # Phase 4: Validation (sequential)
            print("✅ Running final validation...")
            stage2e_result = await self._run_stage2e(
                grid_image_path, 
                stage2a_result, 
                stage2b_result, 
                stage2c_result
            )
            
            # Compile final results
            final_results = {
                "grid_image_path": grid_image_path,
                "grid_metadata": grid_metadata,
                "stage2a_results": stage2a_result,
                "stage2b_results": stage2b_result,
                "stage2c_results": stage2c_result,
                "stage2di_results": stage2di_result,
                "stage2dii_results": stage2dii_result,
                "stage2diii_results": stage2diii_result,
                "stage2e_results": stage2e_result
            }
            
            # Save results for debugging
            with open('stage2_results.json', 'w') as f:
                json.dump(final_results, f, indent=2)
            
            print("✅ Stage 2 completed successfully!")
            return final_results
            
        except Exception as e:
            print(f"❌ Stage 2 failed: {e}")
            logger.error(f"Stage 2 error: {e}", exc_info=True)
            raise
    
    async def _create_grid_overlay(self, image_path: str) -> Tuple[str, Dict]:
        """Create grid overlay and return path + metadata."""
        try:
            from pipeline.grid_mapping import GridMapper
            
            grid_mapper = GridMapper(grid_cols=8, grid_rows=6)
            grid_image_path, grid_metadata = grid_mapper.create_grid_overlay(image_path)
            
            return grid_image_path, grid_metadata
            
        except Exception as e:
            print(f"❌ Grid overlay creation failed: {e}")
            raise
    
    async def _run_stage2a(self, grid_image_path: str, horizontal_pack: Dict) -> Dict[str, Any]:
        """Run Stage 2A: Grid mapping for horizontal lines & arrows."""
        try:
            # Filter to only include elements that actually exist
            existing_elements = {
                element_id: element_info 
                for element_id, element_info in horizontal_pack["elements"].items()
                if element_info.get("exists", False)
            }
            
            print(f"  📏 Stage 2A: Mapping {len(existing_elements)} horizontal lines & arrows")
            
            # Load Stage 2A prompt
            with open("prompts/pipeline_prompts/stage2a_lines_arrows.md", "r") as f:
                stage2a_prompt = f.read()
            
            # Add elements to map
            stage2a_prompt += f"\n\n## Elements to Map\n{json.dumps(existing_elements, indent=2)}"
            
            # Run Stage 2A
            stage2a_result = await self.detector.detect_elements(grid_image_path, stage2a_prompt)
            
            if stage2a_result and "stage2a_results" in stage2a_result:
                return stage2a_result["stage2a_results"]
            else:
                print("⚠️ Stage 2A returned no valid results")
                return {}
                
        except Exception as e:
            print(f"❌ Stage 2A failed: {e}")
            return {}
    
    async def _run_stage2b(self, grid_image_path: str, diagonal_pack: Dict) -> Dict[str, Any]:
        """Run Stage 2B: Grid mapping for diagonal lines."""
        try:
            # Filter to only include elements that actually exist
            existing_elements = {
                element_id: element_info 
                for element_id, element_info in diagonal_pack["elements"].items()
                if element_info.get("exists", False)
            }
            
            print(f"  📐 Stage 2B: Mapping {len(existing_elements)} diagonal lines")
            
            # Load Stage 2B prompt
            with open("prompts/pipeline_prompts/stage2b_diagonal_lines.md", "r") as f:
                stage2b_prompt = f.read()
            
            # Add elements to map
            stage2b_prompt += f"\n\n## Elements to Map\n{json.dumps(existing_elements, indent=2)}"
            
            # Run Stage 2B
            stage2b_result = await self.detector.detect_elements(grid_image_path, stage2b_prompt)
            
            if stage2b_result and "stage2b_results" in stage2b_result:
                return stage2b_result["stage2b_results"]
            else:
                print("⚠️ Stage 2B returned no valid results")
                return {}
                
        except Exception as e:
            print(f"❌ Stage 2B failed: {e}")
            return {}
    
    async def _run_stage2c(self, grid_image_path: str, zones_text_pack: Dict) -> Dict[str, Any]:
        """Run Stage 2C: Grid mapping for zones & text."""
        try:
            # Filter to only include elements that actually exist
            existing_elements = {
                element_id: element_info 
                for element_id, element_info in zones_text_pack["elements"].items()
                if element_info.get("exists", False)
            }
            
            print(f"  🔲 Stage 2C: Mapping {len(existing_elements)} zones & text labels")
            
            # Load Stage 2C prompt
            with open("prompts/pipeline_prompts/stage2c_zones.md", "r") as f:
                stage2c_prompt = f.read()
            
            # Add elements to map
            stage2c_prompt += f"\n\n## Elements to Map\n{json.dumps(existing_elements, indent=2)}"
            
            # Run Stage 2C
            stage2c_result = await self.detector.detect_elements(grid_image_path, stage2c_prompt)
            
            if stage2c_result and "stage2c_results" in stage2c_result:
                return stage2c_result["stage2c_results"]
            else:
                print("⚠️ Stage 2C returned no valid results")
                return {}
                
        except Exception as e:
            print(f"❌ Stage 2C failed: {e}")
            return {}
    
    async def _run_stage2di(self, image_path: str, stage2a_data: Dict, grid_metadata: Dict) -> List[Dict]:
        """Run Stage 2Di: OpenCV precision detection for horizontals."""
        try:
            from pipeline.opencv_detector import OpenCVDetector
            
            horizontals_for_opencv = stage2a_data.get('horizontal_lines', [])
            grid_results_for_opencv = {"stage2a": stage2a_data}
            
            opencv_detector = OpenCVDetector()
            opencv_detected = opencv_detector.detect_elements(
                image_path,
                horizontals_for_opencv,
                grid_results_for_opencv
            )
            
            if opencv_detected:
                print(f"  📏 Stage 2Di: OpenCV detected {len(opencv_detected)} horizontal lines")
                # Show precise coordinates like the original
                for det in opencv_detected:
                    coords = det.get('coordinates', {})
                    y_px = coords.get('y_pixel')
                    y_norm = coords.get('y_normalized', 0)
                    print(f"    - {det.get('element_id')}: y={y_px} px (norm={y_norm:.4f})")
                return opencv_detected
            else:
                print("  ⚠️ Stage 2Di: No horizontal lines detected by OpenCV")
                return []
                
        except Exception as e:
            print(f"❌ Stage 2Di failed: {e}")
            return []
    
    async def _run_stage2dii(self, image_path: str, stage2b_data: Dict, grid_metadata: Dict) -> List[Dict]:
        """Run Stage 2Dii: LLM precision detection for diagonals."""
        try:
            diagonal_lines_from_2b = stage2b_data.get('diagonal_lines', [])
            if not diagonal_lines_from_2b:
                print("  ⚠️ Stage 2Dii: No diagonal lines from Stage 2B to process")
                return []
            
            print(f"  📐 Stage 2Dii: Processing {len(diagonal_lines_from_2b)} diagonal lines")
            
            # Load the Stage 2Dii prompt
            with open("prompts/pipeline_prompts/stage2dii_diagonal_lines.md", "r") as f:
                stage2dii_prompt = f.read()
            
            # Process each diagonal line
            stage2dii_results = []
            for diag in diagonal_lines_from_2b:
                result = await self._process_diagonal_line(diag, image_path, grid_metadata, stage2dii_prompt)
                if result:
                    stage2dii_results.append(result)
            
            print(f"  ✅ Stage 2Dii: Completed {len(stage2dii_results)} diagonal detections")
            return stage2dii_results
            
        except Exception as e:
            print(f"❌ Stage 2Dii failed: {e}")
            return []
    
    async def _run_stage2diii(self, image_path: str, stage2c_data: Dict, grid_metadata: Dict) -> List[Dict]:
        """Run Stage 2Diii: LLM precision detection for zones."""
        try:
            zones = stage2c_data.get('zones', [])
            if not zones:
                print("  ⚠️ Stage 2Diii: No zones to process")
                return []
            
            print(f"  🔲 Stage 2Diii: Processing {len(zones)} zones")
            
            # Load prompts
            with open("prompts/pipeline_prompts/stage2diii_zones.md", "r") as f:
                stage2diii_prompt_single = f.read()
            with open("prompts/pipeline_prompts/stage2diii_zones_multi.md", "r") as f:
                stage2diii_prompt_multi = f.read()
            
            # Process each zone
            stage2diii_results = []
            for zone in zones:
                result = await self._process_zone(zone, image_path, grid_metadata, stage2diii_prompt_single, stage2diii_prompt_multi)
                if result:
                    stage2diii_results.append(result)
            
            print(f"  ✅ Stage 2Diii: Completed {len(stage2diii_results)} zone detections")
            return stage2diii_results
            
        except Exception as e:
            print(f"❌ Stage 2Diii failed: {e}")
            return []
    
    async def _run_stage2e(self, grid_image_path: str, stage2a_data: Dict, stage2b_data: Dict, stage2c_data: Dict) -> Dict[str, Any]:
        """Run Stage 2E: Final validation."""
        try:
            # Build unified elements database
            unified_elements = {}
            
            # From Stage 2A (horizontals + arrows)
            if 'horizontal_lines' in stage2a_data:
                for line in stage2a_data['horizontal_lines']:
                    eid = line.get('element_id')
                    unified_elements[eid] = {
                        "element_id": eid,
                        "element_type": "horizontal_line",
                        "description": line.get('description', ''),
                        "grid_location": f"Row {line.get('row', 'Unknown')}"
                    }
            if 'arrows' in stage2a_data:
                for arr in stage2a_data['arrows']:
                    eid = arr.get('element_id')
                    unified_elements[eid] = {
                        "element_id": eid,
                        "element_type": "arrow",
                        "description": arr.get('description', ''),
                        "grid_location": f"{arr.get('start','?')} → {arr.get('end','?')}"
                    }
            
            # From Stage 2B (diagonals)
            for line in stage2b_data.get('diagonal_lines', []):
                eid = line.get('element_id')
                unified_elements[eid] = {
                    "element_id": eid,
                    "element_type": "diagonal_line",
                    "description": line.get('description', ''),
                    "grid_location": f"{line.get('start','?')} → {line.get('end','?')}"
                }
            
            # From Stage 2C (zones + text)
            for zone in stage2c_data.get('zones', []):
                eid = zone.get('element_id')
                unified_elements[eid] = {
                    "element_id": eid,
                    "element_type": "zone",
                    "description": zone.get('description', ''),
                    "grid_location": zone.get('area', 'Unknown')
                }
            for txt in stage2c_data.get('text_labels', []):
                eid = txt.get('element_id')
                unified_elements[eid] = {
                    "element_id": eid,
                    "element_type": "text_label",
                    "description": txt.get('description', ''),
                    "grid_location": txt.get('cell', 'Unknown')
                }
            
            print(f"  ✅ Stage 2E: Created unified database with {len(unified_elements)} elements")
            
            # Load Stage 2E prompt
            with open("prompts/pipeline_prompts/stage2e_validation.md", "r") as f:
                stage2e_prompt = f.read()
            stage2e_prompt += f"\n\n## Elements to Validate\n{json.dumps(unified_elements, indent=2)}"
            
            # Run Stage 2E
            stage2e_result = await self.detector.detect_elements(grid_image_path, stage2e_prompt)
            
            if stage2e_result and "validation_results" in stage2e_result:
                return stage2e_result["validation_results"]
            else:
                print("⚠️ Stage 2E returned no valid results")
                return {}
                
        except Exception as e:
            print(f"❌ Stage 2E failed: {e}")
            return {}
    
    async def _process_diagonal_line(self, diag: Dict, image_path: str, grid_metadata: Dict, prompt: str) -> Dict:
        """Process a single diagonal line for Stage 2Dii with real precision detection."""
        try:
            import cv2
            import numpy as np
            from PIL import Image, ImageDraw, ImageFont
            import base64, io
            import os
            
            element_id = diag.get('element_id', 'UNKNOWN')
            start_cell = diag.get('start', '')
            end_cell = diag.get('end', '')
            description = diag.get('description', '')
            
            if not start_cell or not end_cell:
                return None
            
            print(f"    🔍 Processing diagonal: {element_id} | {start_cell} → {end_cell}")
            
            # Extract grid metadata
            padding = int(grid_metadata['cell_padding'])
            cell_w = float(grid_metadata['cell_width_px'])
            cell_h = float(grid_metadata['cell_height_px'])
            image_w = int(grid_metadata['image_width'])
            image_h = int(grid_metadata['image_height'])
            grid_rows = int(grid_metadata['grid_rows'])
            
            def cell_to_indices(cell: str):
                col = ord(cell[0].upper()) - ord('A')
                row = int(cell[1])
                return col, row
            
            # Calculate rectangle bounds
            sc_col, sc_row = cell_to_indices(start_cell)
            ec_col, ec_row = cell_to_indices(end_cell)
            
            min_col = min(sc_col, ec_col)
            max_col = max(sc_col, ec_col)
            min_row = min(sc_row, ec_row)
            max_row = max(sc_row, ec_row)
            
            left_x = padding + min_col * cell_w
            right_x = padding + (max_col + 1) * cell_w
            top_y = padding + (grid_rows - max_row) * cell_h
            bottom_y = padding + (grid_rows - min_row + 1) * cell_h
            
            left_x = max(0, int(round(left_x)))
            right_x = min(image_w, int(round(right_x)))
            top_y = max(0, int(round(top_y)))
            bottom_y = min(image_h, int(round(bottom_y)))
            
            # Load original chart for cropping
            full_bgr = cv2.imread(image_path)
            if full_bgr is None:
                print(f"      ❌ Failed to load image")
                return None
            
            # Crop the diagonal area
            crop = full_bgr[top_y:bottom_y, left_x:right_x]
            if crop.size == 0:
                print(f"      ❌ Empty crop")
                return None
            
            w, h = right_x - left_x, bottom_y - top_y
            pil_img = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)
            
            # Draw mini-grid 8x6 with labels A1..H6 (1 bottom)
            grid_color = (0, 255, 0)
            thickness = 1
            cw, ch = w / 8.0, h / 6.0
            
            for i in range(9):
                x = i * cw
                draw.line([(x, 0), (x, h)], fill=grid_color, width=thickness)
            for j in range(7):
                y = j * ch
                draw.line([(0, y), (w, y)], fill=grid_color, width=thickness)
            
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 18)
            except Exception:
                font = ImageFont.load_default()
            
            for c in range(8):
                for r in range(6):
                    col_letter = chr(ord('A') + c)
                    row_num = 6 - r
                    label = f"{col_letter}{row_num}"
                    cx = c * cw + cw / 2.0
                    cy = r * ch + ch / 2.0
                    draw.text((cx, cy), label, fill=(0, 0, 0), font=font, anchor="mm")
            
            # Draw the SAME mini-grid onto a copy of the full chart at the rect
            full_pil = Image.fromarray(cv2.cvtColor(full_bgr, cv2.COLOR_BGR2RGB))
            full_draw = ImageDraw.Draw(full_pil)
            
            # Mini-grid lines on full image (offset by left_x/top_y)
            for i in range(9):
                x = int(round(left_x + i * cw))
                full_draw.line([(x, top_y), (x, bottom_y)], fill=grid_color, width=thickness)
            for j in range(7):
                y = int(round(top_y + j * ch))
                full_draw.line([(left_x, y), (right_x, y)], fill=grid_color, width=thickness)
            
            # Labels on full image inside mini-cells
            try:
                font_full = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 18)
            except Exception:
                font_full = ImageFont.load_default()
            for c in range(8):
                for r in range(6):
                    col_letter = chr(ord('A') + c)
                    row_num = 6 - r
                    label = f"{col_letter}{row_num}"
                    cx = int(round(left_x + c * cw + cw / 2.0))
                    cy = int(round(top_y + r * ch + ch / 2.0))
                    full_draw.text((cx, cy), label, fill=(0,0,0), font=font_full, anchor="mm")
            
            # Encode full-context image (mini-grid within rectangle) for LLM
            full_buf = io.BytesIO()
            full_pil.save(full_buf, format='PNG')
            full_buf.seek(0)
            base64_full = base64.b64encode(full_buf.getvalue()).decode('utf-8')
            
            # Save overlays for debug
            debug_dir = "stage2dii_debug"
            os.makedirs(debug_dir, exist_ok=True)
            overlay_path = os.path.join(debug_dir, f"{element_id}_mini_grid.png")
            pil_img.save(overlay_path)
            
            full_context_path = os.path.join(debug_dir, f"{element_id}_rect_on_full.png")
            full_pil.save(full_context_path)
            
            buffer = io.BytesIO()
            pil_img.save(buffer, format='PNG')
            buffer.seek(0)
            base64_zoom = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Call LLM for precision detection
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{prompt}\n\nAnalyze this diagonal line: {description}\n- Image 1: Full chart (context)\n- Image 2: Zoomed mini-grid (precision)\nReturn the exact requested plain-text output (5 lines)."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64_full}", "detail": "high"}
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64_zoom}", "detail": "high"}
                        }
                    ]
                }
            ]
            
            # Call LLM directly
            llm_result = await self.detector.call_llm_direct(
                messages,
                model="gpt-4o",
                max_tokens=600,
                temperature=0.1
            )
            
            if not llm_result:
                print(f"      ❌ No LLM response")
                return None
            
            # Parse the response (simplified for now)
            parsed = self._parse_diagonal_response(llm_result, element_id)
            if not parsed:
                print(f"      ❌ Failed to parse LLM response")
                return None
            
            print(f"      ✅ Parsed precise points")
            
            return {
                "element_id": element_id,
                "start_cell": start_cell,
                "end_cell": end_cell,
                "precise_detection": parsed,
                "debug_images": {
                    "mini_grid": overlay_path,
                    "full_context": full_context_path
                }
            }
            
        except Exception as e:
            print(f"      ❌ Failed to process diagonal line: {e}")
            return None
    
    def _parse_diagonal_response(self, content: str, fallback_element_id: str):
        """Parse LLM response for diagonal precision detection."""
        try:
            # Try JSON first, then plaintext
            parsed = None
            try:
                parsed = self._try_parse_json(content)
            except Exception:
                try:
                    parsed = self._try_parse_plaintext(content, fallback_element_id)
                except Exception as e:
                    print(f"      Failed to parse plaintext: {e}")
            
            return parsed
            
        except Exception as e:
            print(f"      Failed to parse diagonal response: {e}")
            return None
    
    def _try_parse_json(self, content: str):
        """Try to parse JSON response."""
        cleaned = content.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        return json.loads(cleaned)
    
    def _try_parse_plaintext(self, content: str, fallback_element_id: str):
        """Try to parse plaintext response."""
        import re
        
        lines = [ln.strip() for ln in content.strip().splitlines() if ln.strip()]
        
        find = lambda key: next((ln for ln in lines if ln.lower().startswith(key)), None)
        el = find('element_id:')
        p1 = find('point_1_cell:')
        p2 = find('point_2_cell:')
        conf = find('confidence:')
        notes = find('notes:')

        def extract_after_colon(line: str) -> str:
            return line.split(':', 1)[1].strip() if line and ':' in line else ''

        element_id = extract_after_colon(el) or fallback_element_id

        def parse_point(line: str):
            value = extract_after_colon(line)
            m = re.match(r"^([A-H][1-6])\s*,\s*touch:\s*(body|wick)\s*$", value, re.IGNORECASE)
            cell = touch = ''
            if m:
                cell = m.group(1).upper()
                touch = m.group(2).lower()
            return cell, touch

        cell1, touch1 = parse_point(p1)
        cell2, touch2 = parse_point(p2)
        confidence = extract_after_colon(conf).lower()
        notes_text = extract_after_colon(notes)

        def split_cell(cell: str):
            return (cell[:1], cell[1:]) if len(cell) == 2 else ('', '')

        c1x, c1y = split_cell(cell1)
        c2x, c2y = split_cell(cell2)

        return {
            "diagonal_line_detection": {
                "diagonal_lines": [
                    {
                        "element_id": element_id,
                        "detected_points": {
                            "point_1": {
                                "mini_grid_x": c1x,
                                "mini_grid_y": c1y,
                                "touch_type": touch1
                            },
                            "point_2": {
                                "mini_grid_x": c2x,
                                "mini_grid_y": c2y,
                                "touch_type": touch2
                            }
                        },
                        "confidence": confidence,
                        "notes": notes_text
                    }
                ]
            }
        }
    
    async def _process_zone(self, zone: Dict, image_path: str, grid_metadata: Dict, single_prompt: str, multi_prompt: str) -> Dict:
        """Process a single zone for Stage 2Diii with real precision detection."""
        try:
            import cv2, base64, io, os
            from PIL import Image, ImageDraw, ImageFont
            
            element_id = zone.get('element_id', 'UNKNOWN')
            area = zone.get('area', zone.get('area_description', ''))
            
            if not area:
                return None
            
            print(f"    🔍 Processing zone: {element_id} | {area}")
            
            # Extract grid metadata
            padding = int(grid_metadata['cell_padding'])
            cell_w = float(grid_metadata['cell_width_px'])
            cell_h = float(grid_metadata['cell_height_px'])
            image_w = int(grid_metadata['image_width'])
            image_h = int(grid_metadata['image_height'])
            grid_rows = int(grid_metadata['grid_rows'])
            
            def parse_span(span: str):
                # e.g., "A2 to C2" → (A2, C2)
                parts = span.replace(' ', '').split('to')
                return parts[0], parts[1]
            
            def cell_to_idx(cell: str):
                return ord(cell[0].upper()) - ord('A'), int(cell[1])
            
            # Parse zone area
            start_cell, end_cell = parse_span(area)
            sc_col, sc_row = cell_to_idx(start_cell)
            ec_col, ec_row = cell_to_idx(end_cell)
            min_col = min(sc_col, ec_col)
            max_col = max(sc_col, ec_col)
            target_col = max_col  # rightmost column
            row = sc_row  # both rows are same in typical zone area
            
            # Check if zone spans multiple rows
            spans_rows = (sc_row != ec_row)
            top_row = max(sc_row, ec_row)
            bot_row = min(sc_row, ec_row)
            
            def build_rect(col_idx: int, row_idx: int):
                left_x = padding + col_idx * cell_w
                right_x = padding + (col_idx + 1) * cell_w
                top_y = padding + (grid_rows - row_idx) * cell_h
                bottom_y = padding + (grid_rows - row_idx + 1) * cell_h
                return int(round(left_x)), int(round(top_y)), int(round(right_x)), int(round(bottom_y))
            
            def draw_guides_and_encode(col_idx:int, row_idx:int):
                x1, y1, x2, y2 = build_rect(col_idx, row_idx)
                w, h = x2 - x1, y2 - y1
                
                # Load image and crop
                full_bgr = cv2.imread(image_path)
                if full_bgr is None:
                    return None, None
                
                crop = full_bgr[y1:y2, x1:x2]
                if crop.size == 0:
                    return None, None
                
                pil_zoom = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                draw_zoom = ImageDraw.Draw(pil_zoom)
                grid_color = (0, 255, 0)
                thickness = 1
                
                # 9 guides including edges; numbers on left; 1 bottom edge, 9 top edge
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 18)
                except Exception:
                    font = ImageFont.load_default()
                
                N = 9
                for i in range(1, N+1):
                    y = h - ((i - 1) * (h / (N - 1)))
                    draw_zoom.line([(0, y), (w, y)], fill=grid_color, width=thickness)
                    draw_zoom.text((10, y), str(i), fill=(0,0,0), font=font, anchor='lm')
                
                buf_zoom = io.BytesIO()
                pil_zoom.save(buf_zoom, format='PNG')
                buf_zoom.seek(0)
                return (x1, y1, x2, y2), base64.b64encode(buf_zoom.getvalue()).decode('utf-8')
            
            def parse_zone_reply_block(text: str):
                lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
                def getv(prefix):
                    for ln in lines:
                        if ln.lower().startswith(prefix):
                            return ln.split(':',1)[1].strip()
                    return ""
                return {
                    "element_id": getv('element_id:'),
                    "cell_role": getv('cell_role:'),
                    "closest_line": getv('closest_line:'),
                    "confidence": getv('confidence:'),
                    "notes": getv('notes:')
                }
            
            def line_to_y_from_n(n:int, col_idx:int, row_idx:int):
                N = 9
                x1, y1, x2, y2 = build_rect(col_idx, row_idx)
                y_rel = (N - n) / (N - 1)
                return int(round(y1 + y_rel * (y2 - y1)))
            
            # Process zone based on whether it spans rows
            y_top_px = None
            y_bottom_px = None
            
            if spans_rows:
                # Two calls: top cell then bottom cell, each 5-line output
                zone_answers = {}
                for role, r_idx in (("top", top_row), ("bottom", bot_row)):
                    rect, b64_zoom = draw_guides_and_encode(target_col, r_idx)
                    if not b64_zoom:
                        print(f"      ❌ Empty crop for {element_id} {role}")
                        continue
                    
                    color_hint = 'light red' if 'red' in zone.get('description','').lower() else 'light blue'
                    instruction = f"{multi_prompt}\n\nColor hint: {color_hint}\ncell_role: {role}"
                    messages = [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": instruction},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_zoom}", "detail": "high"}}
                        ]
                    }]
                    
                    reply = await self.detector.call_llm_direct(messages, model='gpt-4o', max_tokens=300, temperature=0.1)
                    if not reply:
                        print(f"      ❌ No LLM reply for {element_id} {role}")
                        continue
                    
                    ans = parse_zone_reply_block(reply)
                    zone_answers[role] = ans
                
                # Compute ys
                try:
                    n_top = max(1, min(9, int(zone_answers.get('top',{}).get('closest_line','0'))))
                    n_bottom = max(1, min(9, int(zone_answers.get('bottom',{}).get('closest_line','0'))))
                    y_top_px = line_to_y_from_n(n_top, target_col, top_row)
                    y_bottom_px = line_to_y_from_n(n_bottom, target_col, bot_row)
                except Exception:
                    pass
            else:
                # Single call: 10-line output (top block then bottom block)
                rect, b64_zoom = draw_guides_and_encode(target_col, row)
                if not b64_zoom:
                    print(f"      ❌ Empty crop for {element_id} single")
                    return None
                
                color_hint = 'light red' if 'red' in zone.get('description','').lower() else 'light blue'
                instruction = f"{single_prompt}\n\nColor hint: {color_hint}"
                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_zoom}", "detail": "high"}}
                    ]
                }]
                
                reply = await self.detector.call_llm_direct(messages, model='gpt-4o', max_tokens=300, temperature=0.1)
                if not reply:
                    print(f"      ❌ No LLM reply for {element_id} single")
                    return None
                
                lines = [ln for ln in reply.splitlines() if ln.strip()]
                top_block = '\n'.join(lines[0:5]) if len(lines) >= 5 else ''
                bottom_block = '\n'.join(lines[5:10]) if len(lines) >= 10 else ''
                parsed_top = parse_zone_reply_block(top_block)
                parsed_bottom = parse_zone_reply_block(bottom_block)
                
                try:
                    n_top = max(1, min(9, int(parsed_top.get('closest_line','0'))))
                    n_bottom = max(1, min(9, int(parsed_bottom.get('closest_line','0'))))
                    y_top_px = line_to_y_from_n(n_top, target_col, row)
                    y_bottom_px = line_to_y_from_n(n_bottom, target_col, row)
                except Exception:
                    y_top_px = y_bottom_px = None
            
            print(f"      ✅ Zone processed: top_y={y_top_px}, bottom_y={y_bottom_px}")
            
            return {
                "element_id": element_id,
                "area": area,
                "rightmost_cell": chr(ord('A') + target_col) + str(row),
                "y_top_px": y_top_px,
                "y_bottom_px": y_bottom_px,
                "y_top_norm": (y_top_px / image_h) if y_top_px is not None else None,
                "y_bottom_norm": (y_bottom_px / image_h) if y_bottom_px is not None else None
            }
            
        except Exception as e:
            print(f"      ❌ Failed to process zone: {e}")
            return None
