# Stage 6B: LLM Review & Synthesis

You are analyzing a trading chart with both detected elements and trader intent.

## Your Task
Take the trader's visual intent and weave it together with the comprehensive Stage 6A market analysis to create enhanced conditional instructions for trading plan creation.

## What to Look For in Stage 6A Data
- **Element sequences**: Current state, recent events, volume story for each element
- **Enhanced element data**: 
  - `now_price_at_element` (current diagonal price)
  - `pct_to_trigger` (distance to breakout)
  - `window` (time/price window for diagonals)
  - `volume_baseline` (per-element volume thresholds)
  - `retest_detection` (retest patterns)
  - `distances` (precise distances to levels)
  - `structured_events` (normalized event data)
- **Volume analysis**: Breakout volume thresholds, recent averages, volume trends
- **Price position**: Breakout status, momentum direction, key levels
- **Risk metrics**: Real ATR values, suggested stops, invalidation levels
- **Derived intelligence**: State machine mode, trading targets, entry hints

## How to Weave Them Together
- Map trader's elements to actual detected elements with specific data
- Use precise distances and percentages (e.g., "2.35% below diagonal")
- Reference specific volume thresholds (e.g., "volume > 12,000,000")
- Show how trader's plan connects to current market conditions
- Identify what the data reveals about the trader's approach
- Suggest additional scenarios based on the market analysis
- Create conditional instructions that use the specific data points

## Output Format
```json
{
  "synthesis_metadata": {
    "stage": "6b",
    "created_at": "2024-01-15T10:30:00Z",
    "source": "llm_synthesis",
    "overall_confidence": 0.78
  },
  
  "trader_plan_synthesis": {
    "trader_intent": "Wait for diagonal breakout, confirm above zone, enter at zone bottom, target horizontal",
    "intent_clear": true,
    "elements_mapped": true,
    "confidence": 0.85,
    
    "element_sequence": [
      {
        "step": 1,
        "element_id": "element_01",
        "element_type": "diagonal_line",
        "trend_line_type": "resistance",
        "action": "wait_for_breakout",
        "price_range": "0.3 to 0.1",
        "time_range": "03/07/25 to 29/07/25",
        "current_state": "below",
        "volume_story": "normal_vol_neutral (avg=7,200,000, recent=6,800,000, price_chg=+0.5%)"
      }
    ]
  },
  
  "conditional_scenarios": [
    {
      "scenario_id": "trader_plan_primary",
      "description": "Follow trader's exact sequence: diagonal breakout → zone confirmation → zone bottom entry → horizontal target",
      "conditions": [
        "price > diagonal_line (element_01)",
        "price > zone_top (element_02)", 
        "volume > average_breakout_volume (10500000)",
        "momentum_direction = up"
      ],
      "trading_plan": {
        "side": "long",
        "entry_conditions": ["price > 0.25", "volume > 10500000"],
        "entry_price": 0.205,
        "targets": [{"level": 0.40, "weight": 1.0, "element_id": "element_05"}],
        "stop_loss": 0.18,
        "probability": 0.75,
        "risk_reward": 2.6
      }
    }
  ],
  
  "volume_confirmation_analysis": {
    "breakout_volume_strength": "strong",
    "average_breakout_volume": 10500000,
    "volume_confirmation": true
  },
  
  "risk_assessment": {
    "overall_confidence": 0.78,
    "key_risks": ["Low volume on horizontal target", "Zone retest risk if breakout fails"],
    "atr_value": 0.072,
    "suggested_stop": 0.18,
    "invalidation_rule": "daily_close_below_zone_bottom"
  },
  
  "improvements_over_trader": [
    "Additional diagonal breakout volume confirmation",
    "Intermediate target for partial profit",
    "Better stop placement based on ATR"
  ]
}
```
