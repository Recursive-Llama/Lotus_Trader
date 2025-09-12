# Stage 1C: Zones & Text Detection

You are analyzing a trading chart image to identify **ONLY zones/boxes and text labels**.

## Your Task
**Find every visible zone/box and text label that a trader has drawn on the chart.**

## What to Look For

### **Zones/Boxes**
- **Light colored areas** (red, blue, grey, etc.)
- **Filled or shaded regions** with boundaries
- **Rectangular or box-shaped areas** that stand out
- **Highlighted zones** (avoid labeling as support/resistance; use color + "zone")
- **Order blocks** or **liquidity areas**

### **Text Labels**
- **Price annotations** written on the chart
- **Trade notes** or **comments**
- **Zone labels** (like "1D S/R + BOS zone")
- **Time markers** or **date labels**
- **Any written text** that's clearly visible

## Detection Strategy
- **Look for colored/shaded areas** that form distinct regions
- **Focus on areas that stand out** from the background
- **Check for text that's readable** and clearly written
- **Ignore candlestick patterns** - only drawn elements
- **Be thorough** - zones can be subtle but important

## Output Format
```json
{
  "zones": [
    {
      "id": "zone_1",
      "description": "Light blue zone",
      "color": "light blue",
      "style": "filled with dotted boundary",
      "position": "lower left area"
    }
  ],
  "text_labels": [
    {
      "id": "text_1",
      "description": "Zone label",
      "content": "1D S/R + BOS zone",
      "color": "black",
      "position": "below blue zone"
    }
  ]
}
```

## Important Guidelines
- **Only report elements you can clearly see**
- **Don't guess or hallucinate** - be precise about what's visible
- **Focus on obvious drawn elements** - not price action
- **Describe colors and styles** accurately
- **Note general positions** (upper, lower, left, right, middle)

## What NOT to Look For
- Candlestick patterns
- Price action that looks like zones
- Implied support/resistance areas
- Any elements that aren't clearly drawn or written
