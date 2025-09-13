# Social Lowcap Intelligence System

*Curated social intelligence for early-stage token discovery and execution*

---

## **System Overview**

The Social Lowcap system consists of **three specialized modules** that integrate seamlessly with our existing Lotus Trader architecture:

1. **Social Ingest Module** - Data collection and aggregation (no learning)
2. **Decision Maker Lowcap (DML)** - Portfolio-aware decision making (learns from outcomes)
3. **Trader Lowcap (TDL)** - Specialized execution for social trades (learns from execution)

**Key Principle**: Each module defines what's important for them to learn, then uses the same Simons' resonance formulas (φ, ρ, θ, ω) to calculate scores.

---

## **Module Learning Definitions**

### **Social Ingest Module - No Learning**
- **Purpose**: Collect and aggregate social signals
- **Output**: Creates `social_lowcap` strands
- **Learning**: None - just data collection

### **Decision Maker Lowcap (DML) - Curator Performance Learning**
- **What's Important to Learn**:
  - **Curator Performance**: Which curators consistently pick winners
  - **Slice Performance**: Where/how each curator excels (chain, venue, liquidity, time)
  - **Allocation Accuracy**: How well DML allocates based on curator reputation
  - **Portfolio Impact**: How DML decisions affect overall portfolio performance

- **Learning Metrics**:
  - **Curator Success Rate**: % of curator signals that become profitable
  - **Curator Consistency**: Stability of curator performance over time
  - **Allocation Quality**: Correlation between allocation size and outcome success
  - **Portfolio Risk**: How DML decisions impact portfolio risk metrics

### **Trader Lowcap (TDL) - Execution Performance Learning**
- **What's Important to Learn**:
  - **Execution Success**: How well TDL executes the three-way entry strategy
  - **Slippage Control**: Minimizing slippage across different venues
  - **Venue Selection**: Which venues work best for different token types
  - **Exit Strategy**: How well the progressive exit strategy performs

- **Learning Metrics**:
  - **Execution Accuracy**: % of successful entries at target prices
  - **Slippage Performance**: Average slippage vs market conditions
  - **Venue Effectiveness**: Performance by venue (Raydium, Orca, Uniswap, etc.)
  - **Exit Timing**: How well TDL times exits at 2x, 4x, 8x targets

---

## **Simons' Resonance Formulas Applied**

### **φ (Fractal Self-Similarity) - Pattern Quality Across Scales**
- **DML**: Curator performance consistency across different market conditions, timeframes, and token types
- **TDL**: Execution strategy effectiveness across different venues, token sizes, and market volatility

### **ρ (Recursive Feedback) - Learning from Outcomes**
- **DML**: Learning from TDL execution outcomes and portfolio performance
- **TDL**: Learning from position outcomes and market feedback

### **θ (Collective Intelligence) - Diversity and Ensemble Strength**
- **DML**: Curator diversity and collective wisdom from multiple curator perspectives
- **TDL**: Venue diversity and execution strategy variety

### **ω (Meta-Evolution) - Getting Better at Getting Better**
- **DML**: Improving curator evaluation and allocation strategies over time
- **TDL**: Improving execution strategies and venue selection over time

---

## **Strand Architecture**

### **Social Ingest Strands**
```yaml
# Primary signal strand
module: "social_ingest"
kind: "social_lowcap"
content:
  curator_id: "tg:@alphaOne"
  platform: "telegram"
  token: { chain: "sol", contract: "So1aNa...", ticker: "FOO" }
  venue: { dex: "Raydium", liq_usd: 18500, pool_age_min: 42 }
  context_slices: { liquidity_bucket: "5-25k", time_bucket_utc: "6-12" }
  message: { ts: "2025-09-13T08:12:04Z", text: "$FOO live on Raydium" }
```

### **DML Learning Strands**
```yaml
# Curator performance tracking (created by learning system)
kind: "curator_scorecard"
content:
  curator_id: "tg:@alphaOne"
  window: "2025-09-01..2025-09-13"
  n_signals: 27
  success_rate: 0.74
  median_ret_h6_pct: 5.8
  median_ret_h24_pct: 9.7
  consistency_score: 0.82
  phi_score: 0.76  # Fractal self-similarity
  rho_score: 0.68  # Recursive feedback
  theta_score: 0.71 # Collective intelligence
  omega_score: 0.73 # Meta-evolution
  top_slices: [
    {"slice": {"chain": "sol", "venue": "Raydium", "liq_bucket": "5-25k"}, "success_rate": 0.89, "n": 12}
  ]

# DML decision strands
kind: "decision_lowcap"
content:
  source_kind: "social_lowcap"
  curator_id: "tg:@alphaOne"
  token: { chain: "sol", contract: "So1aNa...", ticker: "FOO" }
  action: "approve"  # or "reject"
  allocation_pct: 3.0  # percent of book NAV
  reasoning: "Curator ⭐️, fresh, liq ok"
  curator_confidence: 0.82
  portfolio_context:
    available_capacity_pct: 15.2
    planned_positions: 3
    current_exposure_pct: 8.5
```

### **TDL Learning Strands**
```yaml
# Execution strands
kind: "execution_lowcap"
content:
  source_decision: "decision_lowcap_123"
  token: { chain: "sol", contract: "So1aNa...", ticker: "FOO" }
  venue: { dex: "Raydium", pair_url: "..." }
  execution_strategy: "three_way_entry"
  position_splits:
    immediate: 0.33
    minus_20_pct: 0.33
    minus_50_pct: 0.34
  execution_quality: 0.87
  slippage_pct: 0.12
  venue_effectiveness: 0.91

# Position update strands (for learning system)
kind: "position_update"
content:
  position_id: "pos_123"
  token: { chain: "sol", contract: "So1aNa...", ticker: "FOO" }
  entry_price: 0.25
  current_price: 0.28
  pnl_pct: 12.0
  position_size_usd: 500
  exit_strategy: "progressive_exit"
  execution_quality: 0.89
  venue_effectiveness: 0.91
  status: "active"
```

---

## **Learning System Integration**

### **Module-Specific Scoring Configuration**
```python
# In module_specific_scoring.py - add these module types
'social_ingest': {
    # No learning - just data collection
    'learning_enabled': False
},
'decision_maker_lowcap': {
    'curator_performance_weight': 0.4,    # How well curators perform
    'allocation_accuracy_weight': 0.3,    # How well DML allocates
    'portfolio_impact_weight': 0.3        # Portfolio risk/return impact
},
'trader_lowcap': {
    'execution_success_weight': 0.4,      # How well TDL executes
    'slippage_control_weight': 0.3,       # Slippage minimization
    'venue_selection_weight': 0.3         # Venue effectiveness
}
```

### **Context Injection for DML**
The learning system automatically provides DML with:
- **Curator Scorecards**: Overall performance and reputation scores
- **Curator Slice Scores**: Performance by chain, venue, liquidity bucket, time
- **Social Lowcap Braids**: Historical signal performance and patterns

### **Context Injection for TDL**
The learning system automatically provides TDL with:
- **Execution Braids**: Historical execution performance
- **Venue Performance**: Venue effectiveness data
- **Position Outcomes**: Historical position performance from `positions` table

---

## **Database Schema**

### **Database Schema**

#### **New Tables Required**
- **`curators`** - Curator registry and performance tracking
- **`positions`** - Universal position tracking (supports both TD and TDL)

#### **Schema File**
Complete schema available in: `Modules/Alpha_Detector/database/curators_positions_schema.sql`

#### **Existing AD_strands Table**
Uses existing `AD_strands` table with new `kind` values:
- `social_lowcap` - Social signals
- `curator_scorecard` - Curator performance (created by learning system)
- `curator_slice_score` - Slice-specific performance (created by learning system)
- `decision_lowcap` - DML decisions
- `execution_lowcap` - TDL executions
- `position_update` - Position updates for learning system

#### **Position Tracking**
- **Positions** are tracked in the `positions` table (not strands)
- **Position updates** create `position_update` strands for learning system
- **Learning system** processes position outcomes and provides context

---

## **Module Implementation**

### **Social Ingest Module**
```python
class SocialIngestModule:
    """Simple data collection - no learning"""
    
    def process_social_signal(self, curator_id, token_data, venue_data):
        """Create social_lowcap strand"""
        strand = {
  "module": "social_ingest",
  "kind": "social_lowcap",
  "content": {
                "curator_id": curator_id,
                "token": token_data,
                "venue": venue_data,
                "context_slices": self._calculate_context_slices(token_data, venue_data)
            }
        }
        return self.supabase_manager.create_strand(strand)
```

### **Decision Maker Lowcap (DML)**
```python
class DecisionMakerLowcap:
    """Portfolio-aware decision making with learning"""
    
    def __init__(self):
        self.learning_system = CentralizedLearningSystem()
        self.context_engine = ContextInjectionEngine()
    
    def make_decision(self, social_signal):
        """Make allocation decision based on curator performance"""
        # Get curator context from learning system
        curator_context = self.context_engine.get_context_for_module(
            'decision_maker_lowcap', 
            {'curator_id': social_signal['curator_id']}
        )
        
        # Calculate allocation based on curator performance
        curator_score = curator_context.get('curator_score', 0.5)
        allocation_pct = self._calculate_allocation(curator_score)
        
        # Create decision strand
        decision = {
            "module": "decision_maker_lowcap",
            "kind": "decision_lowcap",
  "content": {
    "source_kind": "social_lowcap",
                "curator_id": social_signal['curator_id'],
                "action": "approve" if allocation_pct > 0 else "reject",
                "allocation_pct": allocation_pct,
                "curator_confidence": curator_score,
                "reasoning": f"Curator score: {curator_score:.2f}"
            }
        }
        return self.supabase_manager.create_strand(decision)
```

### **Trader Lowcap (TDL)**
```python
class TraderLowcap:
    """Specialized execution with learning"""
    
    def __init__(self):
        self.learning_system = CentralizedLearningSystem()
        self.context_engine = ContextInjectionEngine()
    
    def execute_trade(self, decision):
        """Execute three-way entry strategy"""
        # Get execution context from learning system
        execution_context = self.context_engine.get_context_for_module(
            'trader_lowcap',
            {'token': decision['token'], 'venue': decision['venue']}
        )
        
        # Create position in positions table
        position = {
            "book_id": "social",
            "module": "trader_lowcap",
            "strand_id": decision['id'],
            "token_chain": decision['token']['chain'],
            "token_contract": decision['token']['contract'],
            "token_ticker": decision['token']['ticker'],
            "entry_strategy": "three_way_entry",
            "exit_strategy": "progressive_exit",
            "position_size_usd": decision['allocation_pct'] * self.book_nav,
            "entry_price": decision['token']['current_price']
        }
        position_id = self.supabase_manager.create_position(position)
        
        # Create execution strand for learning system
        execution = {
            "module": "trader_lowcap",
            "kind": "execution_lowcap",
            "content": {
                "source_decision": decision['id'],
                "position_id": position_id,
                "execution_strategy": "three_way_entry",
                "position_splits": {
                    "immediate": 0.33,
                    "minus_20_pct": 0.33,
                    "minus_50_pct": 0.34
                },
                "venue": self._select_best_venue(execution_context)
            }
        }
        return self.supabase_manager.create_strand(execution)
```

---

## **Configuration**

### **Feature Flags**
```yaml
# Feature flags
SOCIAL_LOWCAP_ENABLED: true
SOCIAL_LOWCAP_EXPORT_TO_DM: true
SOCIAL_LOWCAP_LEARNING_ENABLED: true
DML_ENABLED: true
TDL_ENABLED: true
```

### **DML Configuration**
```yaml
# config/decision_maker_lowcap.yaml
dm_lowcap:
  book: "social"
  allocation_bands:
    excellent_curator: [3.0, 5.0]  # 3-5% of book
    good_curator: [1.0, 3.0]       # 1-3% of book
    new_curator: [0.5, 1.0]        # 0.5-1% of book
  risk_limits:
    max_concurrent_positions: 8
    max_daily_allocation_pct: 20
    min_curator_score: 0.6
    min_liquidity_usd: 5000
```

### **TDL Configuration**
```yaml
# config/trader_lowcap.yaml
trader_lowcap:
  book: "social"
  execution_strategy: "three_way_entry"
  position_splits:
    immediate: 0.33
    minus_20_pct: 0.33
    minus_50_pct: 0.34
  exit_strategy: "progressive_exit"
  exit_splits:
    at_2x: 0.33
    at_4x: 0.33
    at_8x: 0.34
  venue_preferences:
    solana: ["Raydium", "Orca", "Saber"]
    ethereum: ["Uniswap", "Sushiswap"]
    base: ["BaseSwap", "Uniswap"]
```

---

## **Learning System Benefits**

### **Automatic Learning**
- **Curator Performance**: Tracks which curators perform best using Simons' formulas
- **Slice Analysis**: Learns where/how each curator excels
- **Context Injection**: Provides modules with relevant learning data
- **Cross-Module Learning**: DML learns from TDL execution outcomes

### **No Module-Level Learning Code**
- **Social Module**: Just creates strands, no learning code
- **DML**: Just makes decisions, gets curator context automatically
- **TDL**: Just executes trades, gets execution context automatically
- **Learning System**: Handles all learning and context injection

---

## **Integration Summary**

The social lowcap system integrates **seamlessly** with our existing architecture:

1. **Uses existing infrastructure**: Strands, learning system, context injection
2. **Minimal schema changes**: Two new tables (`curators` and `positions`)
3. **Event-driven**: Modules communicate through strands
4. **Learning-integrated**: Automatic curator and execution performance tracking
5. **Portfolio-aware**: DML understands planned and current positions via `positions` table
6. **Simple modules**: Focus on core responsibilities, learning handled by system
7. **Scalable**: Can add more curator types or execution strategies

**Key Insight**: Each module defines what's important for them to learn, then uses the same Simons' resonance formulas (φ, ρ, θ, ω) to calculate scores. The learning system handles all the complexity while keeping modules beautifully simple.
