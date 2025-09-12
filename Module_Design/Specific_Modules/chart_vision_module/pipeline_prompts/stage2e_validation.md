# Stage 2D: Final Validation - Grid Location + Description

## What to Do
You are reviewing the final grid mapping results for a trading chart. You have:
- **Element descriptions** from Stage 1 (what each element is)
- **Grid locations** from Stage 2 (where each element is mapped)

## Your Task
Review each element 1 by 1 to validate that the grid location makes sense given the description.

## What to Look For
- **Horizontal Lines**: Does the row number match where the line appears on the chart?
- **Arrows**: Do the start/end cells match the arrow's direction and position?
- **Diagonal Lines**: Do the start/end cells match the trendline's path?
- **Zones**: Do the described areas match the visual zones on the chart?
- **Text Labels**: Are the cells correct for where the text appears?

## Output Format
```json
{
  "validation_results": [
    {
      "element_id": "element_id",
      "element_type": "type",
      "description": "description",
      "grid_location": "location",
      "validation": {
        "is_correct": true,
        "confidence": "high",
        "notes": "notes"
      }
    }
  ],
  "summary": {
    "total_reviewed": "number",
    "total_correct": "number",
    "issues_found": "number",
    "overall_accuracy": "rating"
  }
}
```

## Important Notes
- Review EVERY element from the provided list
- Be specific about why a location does/doesn't make sense
- Use the grid image to verify positions
- Focus on logical consistency between description and location
