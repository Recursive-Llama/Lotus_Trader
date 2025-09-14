# Stage 2A: Simple Grid Mapping - Horizontal Lines & Arrows

You are analyzing a trading chart with an 8x6 grid overlay. The grid has:
- **Columns**: A, B, C, D, E, F, G, H (left to right)
- **Rows**: 1, 2, 3, 4, 5, 6 (1=bottom/lowest price, 6=top/highest price)

## Task
Look at the chart with the grid overlay and map the horizontal lines and arrows from Stage 1.

## What to Do
- **Horizontal Lines**: Tell me which row number each line passes through (1, 2, 3, 4, 5, or 6)
- **Arrows**: Tell me which cell each arrow starts in and which cell it ends in

## Output Format
Provide a JSON response with this structure:

```json
{
  "stage2a_results": {
    "horizontal_lines": [
      {
        "element_id": "element_id",
        "row": "row_number",
        "notes": "brief description"
      }
    ],
    "arrows": [
      {
        "element_id": "element_id",
        "start": "start_cell",
        "end": "end_cell",
        "notes": "brief description"
      }
    ]
  }
}
```

## Grid System
- **Row 1**: Bottom of chart (lowest price)
- **Row 6**: Top of chart (highest price)
- **Columns A-H**: Left to right across the chart
- **Cell format**: "D4" means column D, row 4

## Important
- Only map elements that clearly exist
- Be precise about which row/cells elements are in
- Keep notes brief and clear
