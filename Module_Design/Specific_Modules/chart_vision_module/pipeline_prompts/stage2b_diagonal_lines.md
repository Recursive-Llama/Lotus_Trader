# Stage 2B: Simple Grid Mapping - Diagonal Lines

You are analyzing a trading chart with an 8x6 grid overlay. The grid has:
- **Columns**: A, B, C, D, E, F, G, H (left to right)
- **Rows**: 1, 2, 3, 4, 5, 6 (1=bottom/lowest price, 6=top/highest price)

## Task
Look at the chart with the grid overlay and map the diagonal lines (trendlines) from Stage 1.

## What to Do
- **Diagonal Lines**: Tell me which cell each trendline starts in and which cell it ends in
- **Focus on start/end points** - these are the most important for trendline analysis

## Output Format
Provide a JSON response with this structure:

```json
{
  "stage2b_results": {
    "diagonal_lines": [
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
- Only map diagonal lines that clearly exist
- Be precise about start and end cells
- Keep notes brief and clear
- Focus on the main trendline direction, not every cell it passes through
