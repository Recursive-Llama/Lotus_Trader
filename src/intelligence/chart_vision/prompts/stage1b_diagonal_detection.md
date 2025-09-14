# Stage 1B: Diagonal Line Detection (Minimal)

Identify only trader‑drawn diagonal lines/trendlines. Keep output short and precise.

## Return for each line
- `id`: unique identifier (e.g. `dline_1`)
- `description`: one short clause (e.g., "Downtrend line connecting highs")
- `polarity`: `support` | `resistance` | `unknown` (line below or above candles)
- `direction`: `up` | `down` | `sideways` (coarse)
- `style_hint` (optional): `dashed` | `solid` | `unknown` and color if obvious
- `confidence`: `low` | `medium` | `high`

## Keep it simple
- No angles, touch counts, intersections, or channel metrics.
- Ignore horizontal and vertical lines.

## Output format
```json
{
  "diagonal_lines": [
    {
      "id": "dline_1",
      "description": "description",
      "polarity": "polarity",
      "direction": "direction",
      "style_hint": "style_hint",
      "confidence": "confidence"
    }
  ]
}
```
