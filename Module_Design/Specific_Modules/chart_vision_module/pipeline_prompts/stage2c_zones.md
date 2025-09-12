# Stage 2C: Simple Grid Mapping - Zones Only

You are analyzing a trading chart with an 8x6 grid overlay. The grid has:
- **Columns**: A, B, C, D, E, F, G, H (left to right)
- **Rows**: 1, 2, 3, 4, 5, 6 (1=bottom/lowest price, 6=top/highest price)

## Task
Look at the chart with the grid overlay and map ONLY the zones from Stage 1.

## What to Do
- **Zones**: Describe the area each zone covers (be specific about which cells/columns/rows are included)
- **Ignore text labels** - focus only on zones

## Output Format
Provide a JSON response with this exact structure:

```json
{
  "stage2c_results": {
    "zones": [
      {
        "element_id": "ELEMENT_06",
        "area": "A2 to C2",
        "notes": "Light blue zone in lower left area"
      },
      {
        "element_id": "ELEMENT_07",
        "area": "E3 to F3", 
        "notes": "Light red zone in center right area"
      }
    ],
    "text_labels": []
  }
}
```

## Grid System
- **Row 1**: Bottom of chart (lowest price)
- **Row 6**: Top of chart (highest price)
- **Columns A-H**: Left to right across the chart
- **Cell format**: "D4" means column D, row 4

## Important
- Only map zones that clearly exist
- For zones, describe the approximate area covered using "from_cell to to_cell" format
- Keep notes brief and clear
- Focus on getting the cell ranges correct
- Output must be valid JSON with the exact structure shown above
