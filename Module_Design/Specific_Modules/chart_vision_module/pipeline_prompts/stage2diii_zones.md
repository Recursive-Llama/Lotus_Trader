# Stage 2diii: LLM Zones - Precise Top/Bottom Lines

You will receive one zoomed image of the target cell with 9 horizontal green guide lines numbered 1..9. Line 1 is the bottom edge of the crop; line 9 is the top edge of the crop.

Context (read carefully):
- Zones are colored/shaded boxes on the chart. Look at where the colored area begins and ends. Use the outer boundary/edge of the fill (boundary may be solid/dashed/dotted).
- Color hint: {color_hint}
- Numbering: 1 at the bottom edge, 9 at the top edge. The TOP must be above the BOTTOM.

Task:
- Look at this zoomed view and determine where the zone starts and stops vertically
- Pick which guide line (1..9) marks where the TOP and BOTTOM of the zone are located

Rules:
- Do not extrapolate; if unclear, pick the clearest visible guide
- Return both boundaries in one response
 - If the edge appears between two guides, pick the more extreme: higher for TOP, lower for BOTTOM
 - If any part of the colored area touches the bottom edge of the crop, answer 1 for BOTTOM; if it touches the top edge, answer 9 for TOP

Output (plain text, exactly 10 lines total):
Lines 1-5: TOP boundary
element_id: <id>
cell_role: top
closest_line: 1|2|3|4|5|6|7|8|9
confidence: low|medium|high
notes: <one short sentence>

Lines 6-10: BOTTOM boundary
element_id: <id>
cell_role: bottom
closest_line: 1|2|3|4|5|6|7|8|9
confidence: low|medium|high
notes: <one short sentence>
