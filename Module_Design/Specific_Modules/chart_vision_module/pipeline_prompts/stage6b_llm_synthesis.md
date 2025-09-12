# Stage 6B: LLM Review & Synthesis

You are analyzing a trading chart with both detected elements and trader intent.

## Your Task
Synthesize the trader's visual intent with the mathematically detected elements to identify trading opportunities.

## Analysis Framework

### 1. Intent Mapping
- Map trader's visual annotations to actual detected elements
- Identify conflicts between intent and detection
- Note confirmations between intent and analysis

### 2. Opportunity Identification
- Primary scenario: Follow trader's exact intent
- Alternative scenarios: Improve upon trader's plan
- Backup scenarios: Conservative approaches

### 3. Risk Assessment
- Evaluate probability of each scenario
- Calculate risk/reward ratios
- Identify key risks and mitigations

### 4. Diagonal Breakout Analysis
- Analyze diagonal line breakouts and their significance
- Check for diagonal support/resistance failures
- Evaluate diagonal breakout volume confirmation
- Assess diagonal trend strength and momentum

## Output Format
```json
{
  "trader_intent_analysis": {
    "intent_clear": true,
    "elements_mapped": true,
    "confidence": 0.85,
    "conflicts": [],
    "confirmations": ["volume supports breakout", "price at key level"]
  },
  "trading_scenarios": [
    {
      "scenario_id": "primary_trader_intent",
      "description": "Follow trader's exact plan",
      "entry_conditions": "Breakout above $45,200",
      "targets": [{"level": 46500, "weight": 1.0}],
      "stop_loss": 44800,
      "probability": 0.75,
      "risk_reward": 2.6
    }
  ],
  "improvements_over_trader": [
    "Additional entry at trendline retest",
    "Better stop placement based on ATR"
  ],
  "risk_assessment": {
    "overall_confidence": 0.78,
    "key_risks": ["Low volume", "Market volatility"]
  }
}
```
