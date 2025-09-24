# Enhanced Intent Analysis Strategy for Social Lowcap Trading

*Improving signal quality through curator intent understanding and token verification*

---

## **Overview**

The current lowcap trading strategy is simple but effective: extract tokens from social signals and make buy decisions based on curator performance. However, we're missing crucial context about **what the curator actually intends** when mentioning a token.

This enhancement adds a second LLM call to analyze curator intent, improving signal quality while maintaining the simplicity of our current 4-step decision process.

---

## **Current State vs. Target State**

### **Current Flow**
```
Tweet → LLM Extract Tokens → Verify with DexScreener → Create Strand → Decision Maker
```

**Problem**: We only check if sentiment is "positive" and call it a "buy" signal, missing important context about curator intent.

### **Enhanced Flow**
```
Tweet → LLM Extract Tokens → LLM Analyze Intent → Verify with DexScreener → Create Strand → Decision Maker
```

**Solution**: Understand curator intent before making allocation decisions.

---

## **Enhanced Intent Categories**

### **High Confidence Buy Signals**
- **"adding_to_position"** - Buying more, dip buying, accumulating
- **"research_positive"** - "Research this, looks promising", "Check this out"
- **"comparison_highlighted"** - Specifically called out as best/favorite in comparison
- **"comparison_ranked"** - Has specific ranking (1st, 2nd, 3rd, etc.)
- **"technical_breakout"** - Chart patterns, breakouts, technical analysis
- **"fundamental_positive"** - Utility, team, partnerships, fundamentals

### **Medium Confidence Buy Signals**
- **"new_discovery"** - First mention, new find
- **"comparison_listed"** - In a list but not specifically highlighted

### **Research Pipeline (Not Buy Signals)**
- **"research_neutral"** - "Research this token" (neutral tone)
- **"market_analysis"** - Discussing market conditions, token included
- **"educational"** - Teaching about token/category

### **Negative/Avoid Signals**
- **"profit_taking"** - Selling, taking profits
- **"research_negative"** - "Research this, seems sketchy"
- **"comparison_negative"** - Highlighted unfavorably in comparison
- **"warning_signal"** - Warning about risks, rug pulls
- **"mocking"** - Sarcastic, making fun of token

### **Ambiguous Signals**
- **"mention_only"** - Just mentioning without clear intent
- **"unclear_sentiment"** - Mixed or unclear signals

---

## **Allocation Multipliers by Intent**

```python
INTENT_MULTIPLIERS = {
    # High confidence buys
    "adding_to_position": 1.5,
    "research_positive": 1.4,  # Research can be a strong buy signal
    "comparison_highlighted": 1.3,
    "technical_breakout": 1.3,
    "fundamental_positive": 1.2,
    
    # Medium confidence buys
    "new_discovery": 1.0,
    "comparison_ranked": 0.8,  # Depends on ranking
    "comparison_listed": 0.6,  # Lower confidence for list inclusion
    
    # Research pipeline (don't buy, but track)
    "research_neutral": 0.0,
    "market_analysis": 0.0,
    "educational": 0.0,
    
    # Negative signals
    "profit_taking": 0.0,
    "research_negative": 0.0,
    "comparison_negative": 0.0,
    "warning_signal": 0.0,
    "mocking": 0.0,
    
    # Ambiguous
    "mention_only": 0.3,
    "unclear_sentiment": 0.1
}
```

---

## **Implementation Strategy**

### **Phase 1: Enhanced Intent Analysis (Easy Win)**

**Location**: `src/intelligence/social_ingest/social_ingest_basic.py`

**Changes**:
1. Add second LLM call after token extraction
2. Enhanced prompt with token verification and intent analysis
3. Update strand structure to include intent data

**New Prompt Template**:
```yaml
curator_intent_analysis:
  prompt: |
    Analyze the curator's intent for this token mention with enhanced context:
    
    Message: "{message_text}"
    Extracted Token: {token_name}
    Curator: {curator_id}
    
    **STEP 1: Verify Token Extraction**
    First, double-check if "{token_name}" is actually a valid token mention in this context.
    Look for:
    - Is it clearly a cryptocurrency ticker?
    - Could it be confused with other words/abbreviations?
    - Is the context about trading/investing?
    
    **STEP 2: Determine Intent**
    If token is valid, determine the curator's intent:
    
    **POSITIVE BUY SIGNALS:**
    - "adding_to_position" - Buying more, dip buying, accumulating
    - "research_positive" - "Research this, looks promising", "Check this out"
    - "comparison_highlighted" - Specifically called out as best/favorite in comparison
    - "comparison_ranked" - Has specific ranking (1st, 2nd, 3rd, etc.)
    - "technical_breakout" - Chart patterns, breakouts, technical analysis
    - "fundamental_positive" - Utility, team, partnerships, fundamentals
    
    **MEDIUM CONFIDENCE BUY SIGNALS:**
    - "new_discovery" - First mention, new find
    - "comparison_listed" - In a list but not specifically highlighted
    
    **RESEARCH PIPELINE (Not Buy Signals):**
    - "research_neutral" - "Research this token" (neutral tone)
    - "market_analysis" - Discussing market conditions, token included
    - "educational" - Teaching about token/category
    
    **NEGATIVE/AVOID SIGNALS:**
    - "profit_taking" - Selling, taking profits
    - "research_negative" - "Research this, seems sketchy"
    - "comparison_negative" - Highlighted unfavorably in comparison
    - "warning_signal" - Warning about risks, rug pulls
    - "mocking" - Sarcastic, making fun of token
    
    **AMBIGUOUS:**
    - "mention_only" - Just mentioning without clear intent
    - "unclear_sentiment" - Mixed or unclear signals
    
    Return JSON:
    {
      "token_verification": {
        "is_valid_token": true,
        "confidence": 0.9,
        "alternative_interpretations": ["possible_alternatives"]
      },
      "intent_analysis": {
        "intent": "adding_to_position",
        "confidence": 0.8,
        "reasoning": "Curator says 'adding more' and mentions dip",
        "sentiment": "positive",
        "allocation_multiplier": 1.2
      }
    }
```

### **Phase 2: Decision Maker Integration**

**Location**: `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py`

**Changes**:
1. Update `_calculate_allocation()` to use intent multiplier
2. Add research pipeline for neutral intents
3. Enhanced logging for intent-based decisions

**Updated Allocation Logic**:
```python
def _calculate_allocation(self, curator_score: float, intent_analysis: Dict = None) -> float:
    # Base allocation from curator score
    if curator_score >= 0.8:
        base_allocation = 6.0
    elif curator_score >= 0.6:
        base_allocation = 4.0
    else:
        base_allocation = 2.0
    
    # Apply intent multiplier
    if intent_analysis:
        multiplier = intent_analysis.get('allocation_multiplier', 1.0)
        base_allocation *= multiplier
        
        # Log intent-based adjustment
        self.logger.info(f"Intent adjustment: {intent_analysis.get('intent')} -> {multiplier}x multiplier")
    
    # Ensure within bounds
    allocation = max(self.config['min_allocation_pct'], 
                   min(self.config['max_allocation_pct'], base_allocation))
    
    return allocation
```

### **Phase 3: Research Pipeline (Future)**

**Location**: New module `src/intelligence/research_pipeline/`

**Purpose**: Handle tokens with neutral intents (research_neutral, market_analysis, educational) for future analysis rather than immediate trading.

---

## **Key Benefits**

### **Improved Signal Quality**
- **Better token verification**: Catches false positives from first LLM call
- **Contextual understanding**: Knows the difference between "buying more" vs "taking profits"
- **Comparison handling**: Understands when tokens are highlighted vs just listed

### **Smarter Allocation**
- **Intent-based sizing**: Higher allocations for high-confidence signals
- **Research pipeline**: Neutral signals go to research, not trading
- **Risk reduction**: Avoids negative signals (profit taking, warnings)

### **Maintained Simplicity**
- **Same 4-step decision process**: Token check → Curator score → Signal direction → Capacity
- **Minimal architecture changes**: Just adds one LLM call
- **Backward compatible**: Existing strands still work

---

## **Implementation Timeline**

### **Week 1: Intent Analysis**
- [ ] Create enhanced prompt template
- [ ] Add second LLM call to social ingest
- [ ] Update strand structure with intent data
- [ ] Test with sample tweets

### **Week 2: Decision Integration**
- [ ] Update decision maker to use intent multipliers
- [ ] Add intent-based logging
- [ ] Test allocation adjustments
- [ ] Monitor performance

### **Week 3: Research Pipeline**
- [ ] Create research pipeline module
- [ ] Route neutral intents to research
- [ ] Add research tracking
- [ ] Test end-to-end flow

---

## **Success Metrics**

### **Signal Quality**
- **False positive reduction**: Fewer invalid token extractions
- **Intent accuracy**: Correctly identified curator intent
- **Allocation precision**: Better sizing based on intent

### **Performance**
- **Curator performance**: Improved win rates with intent-based allocation
- **Portfolio returns**: Better risk-adjusted returns
- **Research value**: Quality of research pipeline signals

---

## **Future Enhancements**

### **Token Intelligence Layer**
- **Market metrics**: MC, FDV, volume, liquidity
- **Technical analysis**: Support/resistance, consolidation, breakout
- **Social momentum**: Mention frequency, sentiment trends

### **Dynamic Position Sizing**
- **Confidence scaling**: Adjust allocation based on multiple factors
- **Market conditions**: Consider broader market state
- **Position management**: Scale up/down based on performance

### **Advanced Intent Analysis**
- **Multi-token comparisons**: Handle complex comparison scenarios
- **Temporal analysis**: Track intent changes over time
- **Curator behavior**: Learn individual curator patterns

---

*This enhancement maintains the simplicity and effectiveness of our current strategy while adding the intelligence layer needed for more sophisticated signal processing.*
