# Stage 1D: Element Validation & Feedback

You are reviewing a list of detected trader-drawn elements on a trading chart.

## Your Task
**Review the detected elements and provide feedback on accuracy and completeness.**

## What You're Reviewing
Below is a list of elements that were detected in previous stages. Your job is to:

## STEP 1: Review Each Detected Element (One by One)
**Go through the detected elements systematically:**

1. **Take the first detected element** - Does it actually exist on the chart?
2. **Mark it as exists: true/false** with confidence level
3. **Add specific notes** explaining why it exists or doesn't
4. **Repeat for every single detected element**

## STEP 2: Look for Missing Elements
**After reviewing all detected elements:**

5. **Check if anything obvious was missed** - What else should be detected?
6. **Add any missing elements** with confidence levels
7. **Provide specific descriptions** of what was overlooked

## Important: Be Systematic
- **Review elements one by one** - don't skip any
- **Be explicit about each review** - clear tick/cross for each
- **Give specific reasons** for why each element exists or doesn't
- **Then do completeness check** for missing elements

## Output Format
```json
{
  "validation_results": {
    "element_reviews": [
      {
        "element_id": "zone_1",
        "description": "Light blue support zone",
        "exists": true,
        "confidence": "high",
        "notes": "Clear light blue area in lower left"
      },
      {
        "element_id": "zone_2", 
        "description": "Light red resistance zone",
        "exists": true,
        "confidence": "high",
        "notes": "Visible red area in center right"
      },
      {
        "element_id": "hline_1",
        "description": "Resistance level at top of chart",
        "exists": true,
        "confidence": "high", 
        "notes": "Clear black line across top"
      },
      {
        "element_id": "hline_2",
        "description": "Support level in lower portion",
        "exists": false,
        "confidence": "high",
        "notes": "This is a price level, not a drawn line"
      }
    ],
    "missing_elements": [
      {
        "type": "zone",
        "description": "Light grey area in upper right",
        "confidence": "medium",
        "notes": "Subtle support zone that was overlooked"
      }
    ],
    "summary": {
      "total_reviewed": 8,
      "total_confirmed": 7,
      "total_false_positives": 1,
      "total_missing": 1,
      "overall_accuracy": "good"
    }
  }
}
```

## Validation Guidelines
- **Be systematic** - Review each detected element one by one
- **Be critical** - Don't just agree with everything
- **Mark each element clearly** - exists: true/false for every single one
- **Look for false positives** - Lines that aren't actually drawn
- **Check for missing elements** - Obvious things that should be detected
- **Provide specific feedback** - Don't just say "wrong", explain why
- **Rate confidence** - high/medium/low for each assessment

## What to Look For
- **False horizontal lines** - Price levels that look like lines but aren't drawn
- **Missing zones** - Subtle colored areas that were overlooked
- **Incorrect descriptions** - Wrong colors, positions, or styles
- **Hallucinated elements** - Things that don't actually exist

## Important
- **Only validate what you can clearly see**
- **Be honest about uncertainty**
- **Focus on the most obvious corrections first**
- **Provide actionable feedback** for improvements
