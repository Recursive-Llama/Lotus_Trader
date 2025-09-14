# Stage 5C: Chart Validation - Essence & Story Comparison

## What to Do
You are comparing two trading charts to validate that the rebuilt chart tells the same trading story as the original.

## Context
- **Original Chart**: The trader's annotated chart with all their markings
- **Rebuilt Chart**: Our pipeline's reconstruction using detected elements and OHLC data
- **Key Point**: We're not looking for pixel-perfect matching, but rather **essence and story consistency**

## What Matters (Priority Order)
1. **Trading Story**: Does the rebuilt chart convey the same trading narrative?
2. **Key Levels**: Are the important support/resistance levels present and positioned correctly?
3. **Trend Lines**: Do the diagonal trend lines capture the same price action relationships?
4. **Zones**: Are the trading zones (support/resistance areas) accurately represented?
5. **Price Action Context**: Does the OHLC data align with the trader's annotations?

## What to Ignore
- **Arrows**: These are converted to trader intent text, not visual elements
- **Minor visual differences**: Slight positioning variations are acceptable
- **Chart styling**: Colors, fonts, exact pixel positioning
- **Text labels**: Focus on the trading elements, not descriptive text

## Validation Criteria
- **Story Consistency**: Does the rebuilt chart tell the same trading story?
- **Element Presence**: Are all critical trading elements detected and shown?
- **Level Accuracy**: Are key price levels (horizontal lines, zone boundaries) correctly positioned?
- **Trend Relationships**: Do diagonal lines capture the same price action relationships?
- **Trading Context**: Does the price action support the trader's narrative?

## Output Format
```json
{
  "validation_summary": {
    "story_consistency": "excellent|good|fair|poor",
    "element_accuracy": "excellent|good|fair|poor", 
    "level_precision": "excellent|good|fair|poor",
    "overall_quality": "excellent|good|fair|poor",
    "confidence": "high|medium|low"
  },
  "element_validation": {
    "ELEMENT_01": {
      "present": true,
      "story_relevant": true,
      "position_accurate": true,
      "notes": "Any notes on the element"
    }
  },
  "story_analysis": {
    "original_narrative": "Brief description of what the original chart shows",
    "rebuilt_narrative": "Brief description of what the rebuilt chart shows", 
    "narrative_match": "excellent|good|fair|poor",
    "key_differences": ["Any significant differences in trading story"]
  },
  "missing_critical_elements": [
    {
      "description": "Description of missing element",
      "impact": "high|medium|low",
      "notes": "Why this matters for the trading story"
    }
  ],
  "false_positives": [
    {
      "element_id": "ELEMENT_XX",
      "description": "What was incorrectly detected",
      "impact": "high|medium|low"
    }
  ],
  "recommendations": [
    "Specific actionable recommendations for improvement"
  ]
}
```

## Important Notes
- Focus on **trading relevance** over visual perfection
- Consider the **overall narrative** the trader is telling
- Be fair but thorough in assessment
- Provide specific, actionable feedback
- Remember: arrows are now trader intent text, not visual elements
