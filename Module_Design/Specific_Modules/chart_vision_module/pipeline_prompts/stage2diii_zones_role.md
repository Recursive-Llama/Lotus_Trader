# Stage 2diii (multi): LLM Zones - Single Edge Alignment

You will receive one zoomed image of the target cell with 9 horizontal green guide lines numbered 1..9. Line 1 is the bottom edge of the crop; line 9 is the top edge of the crop.

Context (read carefully):
- Zones are colored/shaded boxes on the chart. Use the visible boundary/edge of the colored area. The boundary style may be solid, dashed, or dotted.
- Color hint: {color_hint}
- Numbering: 1 at the bottom edge, 9 at the top edge. The TOP must be higher than the BOTTOM.

Task:
- Determine where the zone {cell_role} is located in this zoomed view (i.e., where the zone starts if top, or where it ends if bottom).
- Pick which guide line (1..9) the {cell_role} edge of the zone aligns with most closely.
 - For TOP: choose the highest visible edge of the colored/shaded area. For BOTTOM: choose the lowest visible edge.

Rules:
- Do not extrapolate; use the clearest visible cue from the colored area and its boundary.
- Consider boundary styles (solid/dashed/dotted). Do not ignore the colored area; follow its edge.
 - If the edge appears between two guides, choose the more extreme: higher for TOP, lower for BOTTOM.
 - If the colored area reaches the bottom edge of this crop, answer 1. If it reaches the top edge, answer 9.
 - Use the outer boundary of the zone's fill, not interior shading/gradients.

Output (plain text, exactly 5 lines):
element_id: <id>
cell_role: top|bottom
closest_line: 1|2|3|4|5|6|7|8|9
confidence: low|medium|high
notes: <one short sentence>


