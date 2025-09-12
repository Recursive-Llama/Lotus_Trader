# Stage 1A: Horizontal Lines & Arrows Detection

You are analyzing a trading chart image to identify **ONLY horizontal lines and arrows**.

## Your Task
**Find every visible horizontal line and arrow that a trader has drawn on the chart.**

## What to Look For

### **Horizontal Lines**
- **Straight horizontal lines** drawn across the chart
- **Clearly drawn horizontal bands/levels**
- **Price targets** or **stop losses** marked with lines
- **Key horizontal markers** that stand out

### **Arrows**
- **Directional indicators** pointing up/down/left/right
- **Entry/exit signals** drawn on the chart
- **Trend continuation markers**
- **Movement predictions** or **targets**

## Detection Strategy
- **Look for obvious drawn elements** - not candlestick patterns
- **Focus on lines that span the chart** horizontally
- **Check if arrows are pointing to specific areas**
- **Ignore price action** unless it forms clear drawn lines
- **Be conservative** - only report what you're certain is drawn

## Output Format
```json
{
  "horizontal_lines": [
    {
      "id": "hline_1",
      "description": "Horizontal line at the top band",
      "color": "black",
      "style": "solid line",
      "position": "upper portion"
    }
  ],
  "arrows": [
    {
      "id": "arrow_1",
      "description": "Upward movement indicator",
      "color": "black",
      "style": "pointing up",
      "position": "middle area"
    }
  ]
}
```

## Important Guidelines
- **Only report elements you can clearly see**
- **Don't guess or hallucinate** - be precise about what's visible
- **Focus on obvious drawn elements** - not price levels
- **Be conservative** - if unsure, don't report it
- **Describe position** in general terms (upper, middle, lower, left, right)

## What NOT to Look For
- Candlestick patterns
- Price action that looks like lines
- Implied support/resistance levels
- Any elements that aren't clearly drawn
