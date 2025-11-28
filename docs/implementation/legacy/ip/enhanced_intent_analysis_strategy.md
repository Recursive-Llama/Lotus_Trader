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
Tweet → LLM Extract Tokens (with chain context) → Verify with DexScreener → LLM Analyze Intent (per token) → Create Strand → Decision Maker
```

**Solution**: Extract chain context in Stage 1 to find the correct token, then understand curator intent for each specific token before making allocation decisions.

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
    "other_positive": 0.5,  # Default positive intent
    
    # Research pipeline (don't buy, but track)
    "research_neutral": 0.0,
    "market_analysis": 0.0,
    "educational": 0.0,
    "unsupported_chain": 0.0,  # Goes to research pipeline
    "other_neutral": 0.0,  # Default neutral intent
    
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

### **Phase 1: Enhanced Stage 1 (Chain Context) + Stage 2 (Intent Analysis)**

**Location**: `src/intelligence/social_ingest/social_ingest_basic.py`

**Changes**:
1. Enhance Stage 1 prompt to extract chain context
2. Add Stage 2 LLM call after DexScreener verification (one call per token)
3. Enhanced prompt with token verification and intent analysis
4. Update strand structure to include intent data

**Stage 1 Enhancement**:
- **Extract chain context** from tweet when available
- **Leave network blank** if chain context is unclear
- **Prevent scam token matching** by providing chain context to DexScreener

**Stage 2 Input**:
- **Original tweet text** (from `message_data['text']`)
- **Stage 1 output** (extracted token data with chain context)
- **DexScreener verified token** (correct token found using chain context)
- **One prompt per token** from Stage 1

**Enhanced Stage 1 Prompt**:
```yaml
token_extraction:
  prompt: |
    Extract token information from this social media message:
    
    "{message_text}"
    
    **Important**: Pay attention to chain context. If the curator mentions a specific chain, 
    that's the chain the token is on. Don't assume it's on your default chain.
    
    Return a JSON object with:
    - tokens: Array of token objects, each containing:
      - token_name: The token ticker/symbol
      - network: The blockchain network (solana, ethereum, base, bsc, plasma, etc.) or null if not clear
      - contract_address: Contract address if mentioned, null otherwise
      - chain_context: Any chain-specific context mentioned in the message
      - sentiment: positive, negative, or neutral
      - confidence: 0.0 to 1.0
      - has_chart: true if post contains chart/image, false otherwise
      - chart_type: type of chart if present (price, volume, technical, etc.) or null
      - market_context: Object with price_mention, market_cap, risk_assessment, competitors, platform
      - trading_signals: Object with action (set to "buy" if the token is discussed positively/favorably, null otherwise), timing, confidence
    
    Return only the JSON object, no explanations or markdown formatting.
    If no clear tokens are mentioned, return {"tokens": []}.
```

**Stage 2 Prompt Template**:
```yaml
curator_intent_analysis:
  prompt: |
    Analyze the curator's intent for this specific token mention:
    
    **Original Message:**
    "{message_text}"
    
    **Token from Stage 1:**
    - Token: {token_name}
    - Network: {network}
    - Sentiment: {sentiment}
    - Action: {action}
    - Confidence: {confidence}
    
    **Analysis Tasks:**
    1. **Token Verification**: Is "{token_name}" actually a valid token mention in this context?
    2. **Intent Analysis**: What is the curator's intent for this specific token?
    3. **Buy Decision**: Should we actually buy this token based on the full context?
    
    **Intent Types:**
    - "adding_to_position" - Buying more, dip buying
    - "research_positive" - "Research this, looks promising"
    - "new_discovery" - First mention, new find
    - "comparison_highlighted" - Specifically called out as best/favorite
    - "comparison_listed" - In a list but not highlighted
    - "research_neutral" - "Research this token" (neutral tone)
    - "profit_taking" - Selling, taking profits
    - "mention_only" - Just mentioning without clear intent
    - "extraction_error" - Stage 1 was wrong, this isn't a valid token mention
    - "unsupported_chain" - Valid token but on unsupported chain
    - "other_positive" - Intent doesn't fit standard categories but seems positive
    - "other_neutral" - Intent doesn't fit standard categories and seems neutral
    
    **Key Rules:**
    1. Consider the FULL context of the message, not just the token
    2. Focus on the curator's INTENT, not specific words or phrases
    3. Stage 1's "action" is advisory - you can override it based on context
    4. Check if token is on supported chains (SOL, ETH, BASE, BSC) - use the network from Stage 1
    5. If unsupported chain, mark as "unsupported_chain" (goes to research)
    6. If this is a comparison/list, mark tokens as "comparison_listed" unless clearly highlighted
    7. If Stage 1 made an error, return "extraction_error"
    8. Use intent types as a guide - if none fit perfectly, use "other_positive" or "other_neutral"
    9. Process ALL tokens from the message - let intent analysis determine which are buy signals
    
    Return JSON:
    {
      "token_verification": {
        "is_valid_token": true,
        "confidence": 0.9,
        "reasoning": "Token is clearly mentioned in trading context"
      },
      "intent_analysis": {
        "intent_type": "adding_to_position",
        "confidence": 0.8,
        "reasoning": "Curator says 'adding more' and mentions dip",
        "allocation_multiplier": 1.5
      },
      "buy_decision": {
        "should_buy": true,
        "reasoning": "Clear buy signal with high confidence"
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
- **Minimal architecture changes**: Just adds one LLM call per token
- **Backward compatible**: Existing strands still work
- **Smart filtering**: LLM naturally handles comparison context and intent analysis

---

## **Implementation Timeline**

### **Week 1: Enhanced Stage 1 + Intent Analysis**
- [ ] Enhance Stage 1 prompt to extract chain context
- [ ] Create Stage 2 intent analysis prompt template
- [ ] Add Stage 2 LLM call to social ingest (one per token)
- [ ] Update strand structure with intent data
- [ ] Test with sample tweets and comparisons
- [ ] Verify chain context prevents scam token matching
- [ ] Verify LLM naturally handles all tokens without arbitrary limits

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
