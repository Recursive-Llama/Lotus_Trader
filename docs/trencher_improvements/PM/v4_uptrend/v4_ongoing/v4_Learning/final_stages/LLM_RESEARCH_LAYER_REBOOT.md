# LLM Research Layer – End‑State Blueprint

This document defines the complete architecture for the LLM research stack. The system follows a hierarchical investigation model:

**Perceive → Think → Zoom → Think → Investigate → Verify**

Where Level 1 provides zoomable perception, Overseer provides active intelligence, Level 6 provides data provisioning, Levels 2-5 provide targeted investigation, and Math provides verification.

---

## v5 MVP Scope

This document describes the **end-state blueprint**. For v5 launch, implement a minimal viable slice:

### v5 Must-Have
- **Level 1**: Overview + one zoom flow (e.g., "zoom into anomalies")
- **Level 2**: Basic semantic tagging + one investigation recipe (e.g., "investigate semantic differences in these tokens")
- **Level 3**: Stubbed or manual (scope delta analysis can be done manually initially)
- **Level 4/5**: Placeholders or single simple recipe each
- **Math Integration**: Only for a couple of flows (e.g., validate Level 2 semantic proposals, validate Level 3 scope proposals)

### v5 Nice-to-Have (Post-Launch)
- Full Level 3 automation
- Multiple Level 2 investigation types
- Level 4 cross-domain synthesis
- Level 5 comprehensive tuning copilot
- Full math feedback loop integration

The architecture is designed to scale incrementally—start with the MVP and add capabilities as they prove valuable.

---

## 0. Layer Hierarchy (Who does what?)

```
Overseer (active intelligence - asks questions, interprets, routes)
    ↓
Level 6 – Research Manager (data provisioner, recipe executor, validator)
    ↓
Level 1 – Performance Observer (zoomable perception layer)
    ↓
Levels 2-5 – Blind Researchers (targeted investigation tools)
    ↓
Math Layer (verification & execution)
```

### Core Intelligence Flow

```
1. Overseer: "How are we doing?"
   ↓
2. Level 6 → Level 1 (general overview recipe)
   ↓
3. Level 1 → Returns structured performance map
   ↓
4. Overseer: Sees anomaly → "Zoom into this region"
   ↓
5. Level 6 → Level 1 (zoom-in recipe with filters)
   ↓
6. Level 1 → Returns zoomed slice
   ↓
7. Overseer: Understands shape → "Investigate semantic differences in these tokens"
   ↓
8. Level 6 → Prepares exact data bundles → Level 2
   ↓
9. Level 2 → Analyzes only provided bundle → Returns findings
   ↓
10. Level 6 → Validates → Overseer
   ↓
11. Overseer: Evaluates → May ask more questions or escalate
```

---

## 1. Overseer (Active Intelligence Layer)

### Purpose
The Overseer is the **active intelligence** that asks questions, interprets results, and directs research attention. It is not a passive planner—it actively thinks, zooms, and routes investigations.

### The 5 Core Questions (All Asked to Level 1)

The Overseer operates by asking Level 1 these fundamental questions:

#### **Q1: "How are we doing overall?"**
- Asks Level 1 for general overview
- Receives structured performance map:
  - Strong edge zones
  - Weak edge zones
  - Anomalies/inconsistencies
  - Edge trends (decay/emergence)
  - Areas to watch
- This sparks all other questions

#### **Q2: "Where are we strongest?"**
- Asks Level 1 to zoom into high-edge regions
- Wants to understand:
  - Why strong zones are strong
  - What tokens/patterns are inside
  - Whether strength is stable
  - Whether there are hidden clusters
- Based on answer, Overseer may ask Level 2/3/4 to investigate why success occurs

#### **Q3: "Where are we weakest?"**
- Asks Level 1 to zoom into low-edge regions
- Wants to understand:
  - What exactly is failing
  - Which tokens drag performance
  - Whether weak zones overlap with strong ones
  - Whether structural changes are needed
- Based on answer, Overseer may ask Level 3/5 to investigate failures

#### **Q4: "Where are we inconsistent or anomalous?"**
- Asks Level 1 to highlight anomalies
- Wants to understand:
  - Where things look similar but behave differently
  - Where performance is mixed/unclear
  - Where there's instability
  - Where hidden structure might exist
- Based on answer, Overseer may ask Level 2 (semantic) or Level 3 (structural) to investigate

#### **Q5: "How is our edge changing over time?"**
- Asks Level 1 for edge history analysis
- Wants to understand:
  - Which edges are decaying
  - Which edges are emerging
  - Decay rates and half-lives
  - Regime shifts
- Based on answer, Overseer may ask Level 3 (structure) or Level 5 (timing) to investigate

### Questions Overseer Asks to Other Parts of the System

Based on Level 1's answers, the Overseer asks targeted questions to other parts of the system:

#### **To Level 2 (Semantic Investigator):**
- "These tokens have identical scopes but different performance. Investigate semantic subclasses."
- "What semantic factors explain this divergence?"
- "Are there hidden semantic categories within this group?"

#### **To Level 3 (Structure Investigator):**
- "This scope group has mixed performance. Should we split it by dimension X?"
- "Are bucket boundaries optimal for this pattern?"
- "Should semantic factors be integrated as scope dimensions?"

#### **To Level 4 (Cross-Domain Investigator):**
- "Do these patterns share lever adjustments? Is there a meta-lesson?"
- "Are there cross-domain patterns that explain this behavior?"

#### **To Level 5 (Tuning Investigator):**
- "CF data shows missed RR. How can we improve timing for this pattern/scope?"
- "What execution constraints are limiting R/R here?"

#### **To Math Layer:**
- "Validate this scope proposal via SQL tests"
- "Test whether this hypothesis holds statistically"
- "Verify this edge claim with historical data"

### Core Functions

1. **Question Formation (To Level 1)**
   - Asks Level 1 the 5 core questions (all perception questions)
   - Asks Level 1 follow-up zoom-in questions
   - Never asks vague questions—always specific
   - All questions to Level 1 are about "where" and "what" (perception)

2. **Zoom-In Requests (To Level 1)**
   - When Level 1 shows an anomaly, Overseer asks Level 1 to zoom:
     - "Zoom into this region with these filters"
     - "Break this down by semantic class"
     - "Split this scope group by bucket_volatility"
     - "Show token-level breakdown"
   - Overseer does NOT ask itself—it asks Level 1

3. **Investigation Routing (To Levels 2-5 & Math)**
   - After Level 1 provides answers, Overseer understands the shape
   - Routes targeted "why" and "how" questions to appropriate investigators:
     - **Semantic/token differences** → Level 2 ("Why do these tokens differ?")
     - **Structural/scope differences** → Level 3 ("How should we restructure?")
     - **Cross-domain patterns** → Level 4 ("What patterns span domains?")
     - **Timing/counterfactual issues** → Level 5 ("How can we improve R/R?")
     - **Mathematical validation** → Math layer ("Validate this claim")

4. **Synthesis & Decision Making**
   - Receives investigation results from Levels 2-5
   - Synthesizes findings into actionable insights
   - Decides what should be tested, changed, or monitored
   - Can request further investigation or escalate to math layer

5. **Architecture Evolution**
   - Monitors whether research outputs improve edge
   - Detects when new investigation types are needed
   - Can request Level 6 to create new recipes or summarizers

### Overseer Context & Memory

The Overseer doesn't live in a vacuum every run. When answering "What should we investigate next?", it can leverage:

- **Recent Research History**: Reads recent `llm_learning` entries (last N days) to see:
  - Which anomalies have already been investigated
  - Which hypotheses have pending validation
  - Which research directions have paid off
  - Which areas have been investigated with no payoff (de-prioritize)

- **Validation Feedback**: Reviews math layer validation results to learn:
  - Which recipe types produce validated insights
  - Which investigation patterns are most successful
  - Which anomalies recur and need escalation

- **Research Summary Bundle**: Level 6 supplies a `recent_research_summary` bundle that includes:
  - Recent investigation outcomes
  - Pending validation status
  - Historical success rates per recipe/level
  - Recurring anomaly patterns

This prevents Overseer from recursing on the same anomaly forever and helps it learn which research strategies work.

### Triggering & Scheduling

The Overseer is "always" reacting to:

- **Fresh Level 1 Overview**: Q1 ("How are we doing?") runs on:
  - A daily schedule (automatic)
  - Explicit Overseer request (on-demand)
  - Specific alerts (e.g., edge collapse detected)

- **User/Dev-Triggered Runs**: Manual investigation requests

- **Follow-Up Investigations**: After Level 1 reveals anomalies, Overseer triggers targeted investigations to Levels 2-5

Level 6 manages the actual scheduling and execution based on recipe triggers (`daily_cron|on_demand|alert_driven`).

### Does NOT
- Touch raw data, prompts, or low-level task configs
- Manage schedules or validation (Level 6 handles this)
- Write SQL, modify scopes, directly change overrides
- Execute recipes (Level 6 does this)
- Access raw tables or summarizers (always talks to Level 1 through Level 6)
- Pull data directly (receives structured Level 1 JSON outputs only)

---

## 2. Level 6 – Research Manager (Data Provisioner & Executor)

### Purpose
Level 6 is the **data provisioner and execution manager**. It translates Overseer's questions into recipes, prepares exact data bundles for investigators, and protects the math system.

### Core Responsibilities

1. **Question Translation**
   - Converts Overseer questions into concrete recipes
   - Example: "How are we doing?" → `level1_recipe_performance_overview_v1`
   - Example: "Zoom into AI tokens with pattern X" → `level1_recipe_zoom_semantic_breakdown_v1`
   - Example: "Investigate semantic differences in these 12 tokens" → `level2_recipe_semantic_deep_dive_v1`

2. **Data Bundle Preparation**
   - **Level 6 does NOT handle raw data itself**
   - **Level 6 uses summarizers and indexes** (never queries raw tables)
   - **Level 6 never writes SQL**; it only calls summarizers, which encapsulate the DB access
   - **For Level 1**: Calls summarizers to create overview/zoom bundles
   - **For Levels 2-5**: Prepares **exact, targeted data slices**
     - Selects which summarizers to call (from the summarizer registry)
     - Uses data index/catalog to know what's available
     - Calls summarizers with appropriate filters/parameters
     - Assembles bundles with precise context
     - Ensures investigators are not overwhelmed
   - This keeps Level 6 from being overwhelmed—it orchestrates, doesn't process raw data

3. **Recipe Management**
   - Owns the library of versioned recipe configs
   - Can create/modify recipes based on Overseer instructions (long-term)
   - Maintains recipe health metrics

4. **Execution Pipeline**
   - Loads recipe config
   - Calls required summarizers
   - Builds LLM prompts (system + user + bundles + schema)
   - Calls LLM, validates JSON against schema
   - Scores output (format, consistency, novelty, risk)
   - Stores result in `llm_learning`
   - Forwards actionable items to appropriate consumers

5. **Output Validation & Protection**
   - Validates JSON schema (hard fail if invalid)
   - Checks for hallucinations (numbers match input bundles?)
   - Checks for conflicts (does it contradict math state?)
   - Prevents LLM outputs from directly touching lessons/overrides
   - Ensures all proposals flow through math/tuning validation first

6. **Reporting**
   - Provides execution summaries to Overseer
   - Reports task health, coverage, drift, ROI

### Critical Rule: Levels 2-5 Are Blind Researchers

**Levels 2-5 do NOT:**
- Access Level 1 data directly
- Fetch their own data
- Query raw tables
- Decide what data they need
- Browse or explore

**Levels 2-5 ONLY:**
- Receive exact data bundles prepared by Level 6
- Answer very specific, targeted questions
- Analyze only the provided data slice
- Return structured findings

This ensures:
- Safety (no unauthorized data access)
- Consistency (same data = same results)
- Performance (no unnecessary queries)
- Simplicity (investigators are focused tools)
- Correctness (no hallucinated correlations)

### Does NOT
- Set strategic direction (Overseer does this)
- Interpret anomalies (Overseer does this)
- Do research (Levels 2-5 do this)
- Directly change lessons/overrides (produces proposals only)
- Handle raw data (uses summarizers/indexes only)
- Query raw tables (summarizers do this)

---

## 3. Level 1 – Performance Observer (Zoomable Perception Layer)

### Purpose
Level 1 is the **Overseer's zoomable perception layer**. It provides structured situational awareness about system performance and can zoom into specific regions when asked.

**Level 1 does NOT:**
- Generate hypotheses
- Do deep reasoning
- Investigate causes
- Propose structural changes
- Modify trading logic
- Access data directly (Level 6 calls summarizers)

**Level 1 DOES:**
- Summarize performance
- Highlight strong/weak zones
- Identify anomalies
- Show what deserves attention
- Zoom into specific regions when asked
- Return structured snapshots

### Triggers
- **Daily schedule**: Q1 ("How are we doing?") runs automatically
- **Overseer request**: On-demand when Overseer needs fresh overview
- **Alert-driven**: When edge collapse or major anomaly is detected
- **Zoom-in requests**: When Overseer asks to zoom into specific regions

### The Three Core Areas

Level 1 always covers these three regions:

1. **Strong Edge Zones** - Where we're performing well
2. **Weak Edge Zones** - Where we're performing badly
3. **Anomalies** - Where behavior is inconsistent or unexpected

### Launch Goal: "How are we doing?" (General Overview)

**Input Bundles (prepared by Level 6):**
- `global_edge_summary` - Edge by module/action_category
- `pattern_edge_summary` - Edge by pattern_key + top/bottom scopes
- `scope_delta_summary` - Sibling scopes with large edge differences
- `edge_history_summary` - Edge trends over time (decay/emergence)

**Output Schema:**
```json
{
  "edge_health": {
    "overall_status": "healthy|degrading|emerging",
    "strong_zones": [
      {
        "pattern_key": "string",
        "action_category": "string",
        "scope_description": "string",
        "edge_raw": "number",
        "avg_rr": "number",
        "n": "integer",
        "stability": "stable|fragile|emerging",
        "notes": "string"
      }
    ],
    "weak_zones": [
      {
        "pattern_key": "string",
        "action_category": "string",
        "scope_description": "string",
        "edge_raw": "number",
        "avg_rr": "number",
        "n": "integer",
        "stability": "stable|fragile|decaying",
        "notes": "string"
      }
    ],
    "fragile_zones": [
      {
        "pattern_key": "string",
        "description": "string",
        "concern": "high_variance|low_n|inconsistent|decaying"
      }
    ],
    "decaying_patterns": [
      {
        "pattern_key": "string",
        "edge_trend": "number",
        "decay_pct": "number",
        "timeframe_days": "integer"
      }
    ],
    "emerging_patterns": [
      {
        "pattern_key": "string",
        "edge_trend": "number",
        "growth_pct": "number",
        "timeframe_days": "integer"
      }
    ],
    "surprising_anomalies": [
      {
        "type": "scope_divergence|semantic_split|unexpected_edge|mixed_performance",
        "description": "string",
        "pattern_key": "string",
        "scope_description": "string",
        "suggested_investigation": "semantic|structural|cross_domain|tuning",
        "priority": "low|medium|high"
      }
    ],
    "areas_to_watch": [
      {
        "pattern_key": "string",
        "reason": "string",
        "priority": "low|medium|high"
      }
    ]
  }
}
```

**Consumers:**
- **Overseer** (primary) - Uses this to decide what to investigate next
- **Dashboards** (secondary) - Human-readable performance views

### Zoom-In Capability

When Overseer sees an anomaly and asks Level 1 to zoom in, Level 1 can:

- Filter by specific pattern_keys
- Filter by scope dimensions
- Filter by semantic factors
- Filter by time windows
- Break down by subgroups (tokens, buckets, timeframes)
- Show token-level details
- Show scope-level details

**Example Zoom-In Request:**
```
Overseer: "Zoom into AI tokens with pattern pm.uptrend.S1.entry that show mixed performance"
Level 6: Prepares zoom recipe with filters
Level 1: Returns detailed breakdown of those specific tokens
```

**Zoom-In Output Schema:**
```json
{
  "zoomed_region": {
    "filters_applied": {
      "pattern_key": "pm.uptrend.S1.entry",
      "semantic_filter": "AI",
      "performance_filter": "mixed"
    },
    "token_breakdown": [
      {
        "token_address": "string",
        "edge_raw": "number",
        "avg_rr": "number",
        "n": "integer",
        "scope_values": {},
        "semantic_factors": ["string"]
      }
    ],
    "scope_breakdown": [
      {
        "scope_values": {},
        "edge_raw": "number",
        "n": "integer",
        "token_count": "integer"
      }
    ],
    "key_differences": [
      {
        "dimension": "string",
        "value_a": "string",
        "value_b": "string",
        "edge_a": "number",
        "edge_b": "number"
      }
    ]
  }
}
```

### Vision Goal
- More sophisticated anomaly detection
- Automatic trend classification
- Predictive edge health warnings
- Integration with semantic factors (once Level 2 matures)
- Multi-level zooming (zoom into zoom)

---

## 4. Level 2 – Semantic Investigator (Blind Researcher)

### Purpose
Level 2 investigates **semantic/token-level differences** when Overseer detects anomalies that math cannot explain.

### Triggers
- **Overseer request**: When Overseer detects semantic anomalies after Level 1 zoom
- **Specific questions**: "Tokens with same scopes perform very differently" or "Semantic factors might be driving edge divergence"
- **On-demand**: Only when Level 1 reveals token-level inconsistencies that need semantic investigation

### Critical: Level 2 is a Blind Researcher

**Level 2 does NOT:**
- Access Level 1 data directly
- Fetch its own data
- Query raw tables
- Decide what data it needs

**Level 2 ONLY:**
- Receives exact data bundle prepared by Level 6
- Answers the specific question Overseer asked
- Analyzes only the provided data slice

### Launch Goal: Semantic Factor Investigation

**How It Works:**
1. Overseer: "These 12 AI tokens have identical scopes but 50/50 performance split. Investigate semantic subclasses."
2. Level 6 prepares exact bundle:
   - Calls `token_metadata_bundle` for those 12 tokens
   - Calls `semantic_factor_summary` for those tokens
   - Calls `performance_breakdown_by_token` for those tokens
   - Assembles into targeted bundle
3. Level 6 creates recipe: `level2_recipe_semantic_subclass_analysis_v1`
4. Level 2 receives:
   - The exact 12 tokens
   - Their metadata
   - Their performance data
   - The question: "Find semantic subclasses that explain the divergence"
5. Level 2 analyzes ONLY this bundle and returns findings

**Input Bundle (prepared by Level 6):**
```json
{
  "target_tokens": ["token_address_1", "token_address_2", ...],
  "scope_context": {
    "pattern_key": "pm.uptrend.S1.entry",
    "scope_values": {...}
  },
  "token_metadata": [
    {
      "token_address": "string",
      "description": "string",
      "website": "string",
      "x_com_handle": "string",
      "dexscreener_data": {...}
    }
  ],
  "performance_data": [
    {
      "token_address": "string",
      "edge_raw": "number",
      "avg_rr": "number",
      "n": "integer"
    }
  ],
  "question": "Investigate semantic subclasses that explain why these tokens with identical scopes show 50/50 performance split"
}
```

**Output Schema:**
```json
{
  "semantic_investigation": {
    "target_tokens": ["string"],
    "findings": [
      {
        "token_address": "string",
        "semantic_subclasses": [
          {
            "subclass": "string",
            "category": "narrative|style|theme|catalyst",
            "confidence": 0.0-1.0,
            "evidence": "string",
            "source": "dexscreener|website|twitter|github"
          }
        ],
        "divergence_explanation": "string",
        "recommended_actions": [
          "add_to_scope|exclude_from_pattern|create_new_scope_dim"
        ]
      }
    ],
    "meta_observations": [
      {
        "meta_name": "string",
        "tokens_in_meta": ["string"],
        "performance_summary": "string",
        "suggested_scope_integration": "boolean"
      }
    ]
  }
}
```

**Consumers:**
- **Overseer** - Receives findings, decides if semantic factors should be added to scopes
- **Level 3** - Can use semantic findings to propose scope changes
- **Position table** - Semantic factors stored for future analysis

### Vision Goal: Full Token Research Agent
- Crawl websites, GitHub, Twitter for deeper research
- Track narrative momentum, meta rotations
- Discover new curators, data sources
- Wallet tracking, contract analysis
- Vector similarity for token clustering

---

## 5. Level 3 – Structure Investigator (Blind Researcher)

### Purpose
Level 3 investigates **structural/scope-level differences** when Overseer detects that scope dimensions might need adjustment, bucket boundaries are suboptimal, or dimensions are overfit.

### Triggers
- **Overseer request**: When Overseer detects structural anomalies after Level 1 zoom
- **Specific questions**: "Scope deltas suggest dimension X is critical", "Bucket boundaries might be too wide/narrow", "Pattern shows inconsistent behavior across similar scopes"
- **Post-Level 2**: When semantic factors (from Level 2) should be integrated into scopes
- **Weekly**: After lesson builder runs, review scope structure (optional)

### Critical: Level 3 is a Blind Researcher

**Level 3 does NOT:**
- Access Level 1 data directly
- Fetch its own data
- Query raw tables
- Decide what data it needs

**Level 3 ONLY:**
- Receives exact data bundle prepared by Level 6
- Answers the specific question Overseer asked
- Analyzes only the provided data slice

### Launch Goal: Scope Structure Analysis

**How It Works:**
1. Overseer: "This scope group has mixed performance. Investigate whether splitting by bucket_volatility stabilizes it."
2. Level 6 prepares exact bundle:
   - Calls `scope_delta_summary` for that pattern/scope
   - Calls `dimension_importance_summary` for relevant dimensions
   - Calls `bucket_performance_summary` for bucket_volatility splits
   - Assembles into targeted bundle
3. Level 6 creates recipe: `level3_recipe_scope_split_analysis_v1`
4. Level 3 receives:
   - The exact scope group
   - Dimension importance data
   - Bucket split performance data
   - The question: "Should we split this scope by bucket_volatility?"
5. Level 3 analyzes ONLY this bundle and returns findings

**Input Bundle (prepared by Level 6):**
```json
{
  "target_scope": {
    "pattern_key": "pm.uptrend.S1.entry",
    "scope_values": {...}
  },
  "scope_deltas": [
    {
      "dimension": "string",
      "value_a": "string",
      "value_b": "string",
      "edge_a": "number",
      "edge_b": "number",
      "n_a": "integer",
      "n_b": "integer"
    }
  ],
  "dimension_importance": [
    {
      "dimension": "string",
      "importance_score": 0.0-1.0,
      "edge_impact": "high|medium|low"
    }
  ],
  "bucket_split_options": [
    {
      "dimension": "bucket_volatility",
      "split_points": ["string"],
      "performance_by_split": [...]
    }
  ],
  "question": "Should this scope be split by bucket_volatility to improve edge stability?"
}
```

**Output Schema:**
```json
{
  "structure_investigation": {
    "dimension_insights": [
      {
        "dimension": "string",
        "importance_score": 0.0-1.0,
        "edge_impact": "high|medium|low",
        "evidence": "string",
        "recommendation": "keep|remove|split|merge"
      }
    ],
    "scope_adjustment_proposals": [
      {
        "pattern_key": "string",
        "current_scope": {},
        "proposed_scope": {},
        "rationale": "string",
        "expected_edge_improvement": "number",
        "confidence": 0.0-1.0
      }
    ],
    "bucket_split_recommendations": [
      {
        "dimension": "string",
        "current_bucket": "string",
        "proposed_split": ["string", "string"],
        "rationale": "string",
        "edge_improvement_estimate": "number"
      }
    ],
    "new_dimension_proposals": [
      {
        "dimension_name": "string",
        "dimension_type": "semantic|numeric|categorical",
        "rationale": "string",
        "integration_complexity": "low|medium|high"
      }
    ]
  }
}
```

**Consumers:**
- **Overseer** - Reviews proposals, decides what to test
- **Math layer** - Validates scope proposals via SQL tests
- **Lesson builder** - Can incorporate approved scope changes

### Vision Goal: Dimension Weighting
- Compute global importance weights for all dimensions
- Suggest architecture changes to lesson builder
- Auto-detect overfit dimensions
- Integrate semantic factors as scope dimensions

---

## 6. Level 4 – Cross-Domain Pattern Investigator (Blind Researcher)

### Purpose
Level 4 investigates **cross-domain patterns** when Overseer detects that similar lever adjustments or semantic+scope combos appear across different pattern families.

### Triggers
- **Overseer request**: When Overseer detects cross-domain patterns after reviewing multiple Level 1/2/3 outputs
- **Specific questions**: "Same lever adjustments appearing in different families", "Semantic+scope combos show consistent effects across patterns", "Potential meta-lessons that span multiple domains"
- **Weekly**: After lesson builder runs, review for cross-domain patterns (optional)

### Critical: Level 4 is a Blind Researcher

**Level 4 does NOT:**
- Access Level 1 data directly
- Fetch its own data
- Query raw tables
- Decide what data it needs

**Level 4 ONLY:**
- Receives exact data bundle prepared by Level 6
- Answers the specific question Overseer asked
- Analyzes only the provided data slice

### Launch Goal: Cross-Domain Synthesis

**How It Works:**
1. Overseer: "Both prediction-market S2 entries and low-cap AI entries show aggressive trim preference under high volatility. Investigate if this is a cross-domain pattern."
2. Level 6 prepares exact bundle:
   - Calls `lesson_override_summary` for those patterns
   - Calls `semantic_performance_summary` for relevant semantic factors
   - Calls `scope_overlap_summary` for those patterns
   - Assembles into targeted bundle
3. Level 6 creates recipe: `level4_recipe_cross_domain_pattern_v1`
4. Level 4 receives:
   - The exact patterns to compare
   - Their lever adjustments
   - Their scope/semantic conditions
   - The question: "Is there a cross-domain pattern here?"
5. Level 4 analyzes ONLY this bundle and returns findings

**Input Bundle (prepared by Level 6):**
```json
{
  "target_patterns": ["pattern_key_1", "pattern_key_2"],
  "lever_adjustments": [
    {
      "pattern_key": "string",
      "lever_type": "trim_timing|entry_delay|exit_aggression",
      "adjustment": {},
      "scope_conditions": {},
      "semantic_conditions": {}
    }
  ],
  "scope_overlap": {
    "common_scopes": [...],
    "unique_scopes": [...]
  },
  "semantic_overlap": {
    "common_factors": [...],
    "unique_factors": [...]
  },
  "question": "Is there a cross-domain pattern that explains why these patterns share lever preferences?"
}
```

**Output Schema:**
```json
{
  "cross_domain_investigation": {
    "meta_lessons": [
      {
        "meta_lesson_name": "string",
        "applies_to_patterns": ["string"],
        "lever_adjustment": {},
        "scope_conditions": {},
        "semantic_conditions": {},
        "rationale": "string",
        "confidence": 0.0-1.0,
        "suggested_validation": "sql_test|ab_test|tuning_episode"
      }
    ],
    "cross_domain_patterns": [
      {
        "pattern_description": "string",
        "affected_patterns": ["string"],
        "common_levers": ["string"],
        "common_scopes": {},
        "edge_consistency": "high|medium|low"
      }
    ],
    "hypothesis_seeds": [
      {
        "hypothesis": "string",
        "related_patterns": ["string"],
        "test_type": "sql_aggregate|sql_regression|ab_scope_test",
        "priority": "low|medium|high"
      }
    ]
  }
}
```

**Consumers:**
- **Overseer** - Reviews meta-lessons, decides what to validate
- **Level 5** - Can use hypothesis seeds for tuning investigations
- **Math layer** - Validates meta-lessons via tests

### Vision Goal: Pattern Recognition Brain
- Spot structures math doesn't detect
- Automatically spawn hypotheses for Level 5
- Detect emerging regimes via semantic+scope+override relationships

---

## 7. Level 5 – Tuning Investigator (Blind Researcher)

### Purpose
Level 5 investigates **timing/counterfactual issues** when Overseer detects that execution constraints (entry delays, trim timing, exit aggression) might be creating missed opportunities.

### Activation Trigger
Overseer sees anomaly like:
- "Counterfactual improvement buckets show large missed RR"
- "Tuning episode results suggest execution timing issues"
- "CF data shows we could enter/exit better"

### Critical: Level 5 is a Blind Researcher

**Level 5 does NOT:**
- Access Level 1 data directly
- Fetch its own data
- Query raw tables
- Decide what data it needs

**Level 5 ONLY:**
- Receives exact data bundle prepared by Level 6
- Answers the specific question Overseer asked
- Analyzes only the provided data slice

### Launch Goal: R/R Maximization Analysis

**How It Works:**
1. Overseer: "This pattern is strong but CF data shows large missed entry RR. Investigate timing constraints."
2. Level 6 prepares exact bundle:
   - Calls `tuning_episode_summary` for that pattern
   - Calls `counterfactual_opportunity_summary` for entry/exit improvements
   - Calls `lesson_response_summary` for current timing constraints
   - Assembles into targeted bundle
3. Level 6 creates recipe: `level5_recipe_timing_optimization_v1`
4. Level 5 receives:
   - The exact pattern and scope
   - CF entry/exit data
   - Current timing constraints
   - The question: "How can we improve R/R by adjusting timing?"
5. Level 5 analyzes ONLY this bundle and returns findings

**Input Bundle (prepared by Level 6):**
```json
{
  "target_pattern": {
    "pattern_key": "pm.uptrend.S1.entry",
    "scope_values": {...}
  },
  "tuning_episode_data": [
    {
      "took_trade": "boolean",
      "success": "boolean",
      "rr": "number",
      "cf_entry_improvement_bucket": "none|small|medium|large",
      "cf_exit_improvement_bucket": "none|small|medium|large",
      "could_enter_better": {...},
      "could_exit_better": {...}
    }
  ],
  "current_constraints": {
    "entry_delay": "number",
    "trim_timing": "string",
    "exit_aggression": "string"
  },
  "question": "How can we improve R/R by adjusting timing constraints for this pattern/scope?"
}
```

**Output Schema:**
```json
{
  "tuning_investigation": {
    "rr_improvement_opportunities": [
      {
        "pattern_key": "string",
        "stage": "S1|S3|trim|exit",
        "current_constraint": "string",
        "proposed_adjustment": "string",
        "rationale": "string",
        "cf_evidence": {
          "missed_rr_avg": "number",
          "cf_bucket": "none|small|medium|large",
          "sample_size": "integer"
        },
        "expected_rr_improvement": "number",
        "confidence": 0.0-1.0
      }
    ],
    "tuning_hypotheses": [
      {
        "hypothesis": "string",
        "test_type": "entry_delay|trim_timing|exit_aggression|...",
        "scope_conditions": {},
        "proposed_sql": "string",
        "priority": "low|medium|high"
      }
    ],
    "stage_specific_recommendations": [
      {
        "stage": "S1|S3|trim|exit",
        "recommendation": "string",
        "affected_patterns": ["string"],
        "validation_approach": "tuning_episode|sql_test|ab_test"
      }
    ]
  }
}
```

**Consumers:**
- **Overseer** - Reviews opportunities, decides what to test
- **Tuning system** - Receives hypotheses for validation
- **Math layer** - Validates tuning proposals via SQL tests

### Vision Goal: Full R/R Maximizer
- Cover entries, trims, exits comprehensively
- Integrate with math hypothesis runner (auto-run SQL tests)
- Feed results back into tuning episodes
- Detect systematic execution improvements

---

## 7. Math & Learning System Integration

### Purpose
The Math Layer validates all LLM research outputs and integrates validated insights into the learning system. This section defines the complete feedback loop between LLM research and the math/learning infrastructure.

### Inputs from LLM Research Layer
The Math Layer receives proposals from:

- **Level 2 (Semantic)**: Semantic factor integration suggestions, semantic scope dimension proposals
- **Level 3 (Structure)**: Scope adjustment proposals, bucket split recommendations, new dimension proposals
- **Level 4 (Cross-Domain)**: Meta-lesson candidates, cross-domain pattern hypotheses
- **Level 5 (Tuning)**: Tuning hypotheses, R/R improvement proposals, execution timing adjustments

### Validation Mechanisms

1. **SQL Tests / Aggregates**
   - Validates scope proposals by computing edge differences
   - Tests statistical significance of edge claims
   - Verifies sample sizes and variance estimates
   - Checks for overfitting (edge on training vs validation windows)

2. **Tuning Episodes**
   - Validates tuning hypotheses via S1/S3 stage episodes
   - Tests counterfactual improvements with historical data
   - Measures actual R/R impact of proposed changes

3. **AB Tests on Scopes or Overrides**
   - Tests scope splits by comparing sibling scopes
   - Validates override proposals by comparing before/after performance
   - Measures impact of new dimension integrations

### Outputs to Learning System

1. **Approved Scope Changes → Lesson Builder**
   - Validated scope proposals become inputs to `lesson_builder_v5`
   - New dimensions (e.g., semantic factors) get integrated into scope computation
   - Bucket splits get applied to future scope calculations

2. **Updated Overrides → Learning Configs**
   - Validated meta-lessons flow through override materializer
   - Tuning improvements get incorporated into PM config
   - Semantic factor overrides get added to `learning_configs.pm.config_data`

3. **Rejected Ideas → Logged with Feedback**
   - Failed validations are written back to `llm_learning` with:
     - `validation_status: "failed"`
     - `failure_reason: "string"`
     - `math_evidence: {...}`
   - This feedback helps Overseer learn which recipes/levels are useful

### Feedback Loop to Overseer

The Math Layer writes validation results back so Overseer can learn:

- **Which hypotheses got validated** → Prioritize similar research directions
- **Which hypotheses got rejected** → Avoid repeating failed patterns
- **Which recipes are paying off** → Focus on high-ROI investigation types
- **Which anomalies recur** → Escalate persistent issues

Level 6 provides this feedback via a `recent_research_summary` bundle that includes:
- Recent validation outcomes
- Pending validation status
- Historical success rates per recipe/level

This prevents Overseer from recursing on the same anomaly forever and helps it learn which research strategies work.

---

## 8. Data Infrastructure

### 8.1 Data Index Layer (Catalog)
- Static registry describing available tables, fields, summarizers, bundle names, schemas
- **Note:** "Static" means table schemas are stable, not that data is static. Data updates continuously.
- Queried by Level 6 to understand what can be fetched for a recipe
- Overseer can inspect the catalog when designing new goals

### 8.2 Summarizer Layer
- Deterministic Python modules that read the DB and return *small JSON bundles*
- Bundles are designed per use case:
  - `global_edge_summary` - Edge by module/action_category
  - `pattern_edge_summary` - Edge by pattern_key + top/bottom scopes
  - `scope_delta_summary` - Sibling scopes with large edge differences
  - `edge_history_summary` - Edge trends over time
  - `semantic_factor_summary` - Semantic factor performance
  - `token_metadata_bundle` - Token metadata from DexScreener/external sources
  - `tuning_episode_summary` - Tuning episode results
  - `counterfactual_opportunity_summary` - CF entry/exit improvements
  - And more...

- Level 6 maps recipe→bundles via a registry:

```python
BUNDLE_REGISTRY = {
    "global_edge_summary": summarize_global_edges,
    "pattern_edge_summary": summarize_pattern_edges,
    "scope_delta_summary": summarize_scope_deltas,
    "edge_history_summary": summarize_edge_history,
    "semantic_factor_summary": summarize_semantic_factors,
    "token_metadata_bundle": fetch_token_metadata,
    ...
}
```

**Future:** Level 6 can create new summarizers (LLM-assisted) but only after validation by math/ops.

### 8.2.1 External Data Sources

External sources (Dexscreener, websites, x.com, GMGN, etc.) are accessed by **summarizers**, not by LLMs directly. LLMs only see the JSON bundles built from these APIs.

- Summarizers encapsulate all external API calls
- Summarizers handle rate limiting, caching, and error handling
- LLMs receive clean, structured JSON bundles
- This keeps the "no tools from inside the LLMs" pattern consistent

Example: `token_metadata_bundle` summarizer calls Dexscreener API, fetches website content, searches x.com, and returns a structured JSON bundle. Level 2 never directly calls these APIs.

### 8.3 Input Bundles
- JSON documents produced by summarizers
- Each bundle has:
  - metadata (generated_at, window_days, filters)
  - payload (e.g. list of patterns, scope stats, history)
- Level 6 merges bundles into the LLM prompt

### 8.4 Output Storage
- Structured outputs stored in `llm_learning` (or dedicated tables per level) with metadata:
  - recipe_id, level, version
  - input_bundle_hash
  - output JSON (validated)
  - scoring metrics (usefulness, risk)
  - downstream status (e.g. "math test created", "dashboard updated")

---

## 9. Execution Pipeline (Per Recipe)

```
Overseer → Level 6 (Goal: run recipe X)
Level 6:
    1. Loads recipe config (JSON)
    2. Calls required summarizers to fetch bundles
    3. Builds LLM prompt (system + user + bundles + schema)
    4. Calls LLM, validates JSON against schema
    5. Scores output
    6. Stores result + forwards actionable items
```

### 9.1 Recipe Config (Example: Level 1 General Overview)

```jsonc
{
  "id": "level1_recipe_performance_overview_v1",
  "level": "level1_performance_observer",
  "version": 1,
  "goal": "Provide structured performance awareness for Overseer.",
  "input_bundles": [
    "global_edge_summary",
    "pattern_edge_summary",
    "scope_delta_summary",
    "edge_history_summary"
  ],
  "llm_tasks": [
    "identify_strong_zones",
    "identify_weak_zones",
    "detect_fragile_zones",
    "detect_decaying_patterns",
    "detect_emerging_patterns",
    "identify_surprising_anomalies",
    "flag_areas_to_watch"
  ],
  "constraints": {
    "max_patterns_per_group": 20,
    "min_sample_size": 30,
    "min_edge_abs": 0.05
  },
  "output_schema": {
    "edge_health": { ... }
  },
  "consumers": [
    "overseer",
    "edge_dashboard"
  ],
  "run_config": {
    "trigger": "daily_cron|on_demand",
    "max_retries": 2,
    "timeout_seconds": 60
  }
}
```

### 9.2 Prompt Assembly
- System prompt: describes role, constraints, required output format
- User prompt: includes recipe metadata, instructions per task, bundle descriptions, output schema, actual bundles (as JSON inside triple backticks)
- No raw SQL or table names; only summarizer outputs

### 9.3 Validation & Scoring
- After LLM response:
  - Validate JSON schema (hard fail if invalid)
  - Score:
    - format_valid (bool)
    - consistency (did numbers match input bundles?)
    - novelty/usefulness (anomalies detected, areas flagged)
    - risk/conflict (does it contradict known math state?)
  - Store scores; degrade or disable recipe if repeated failures

### 9.4 Consumers
- Level 6 routes parts of the output to:
  - **Overseer** (primary for Level 1)
  - **Dashboards** (human-readable views)
  - **Math test queue** (SQL snippets for validation - from Levels 2-5)
  - **Tuning system** (hypotheses from Level 5)
  - **Lesson builder** (scope proposals from Level 3)

---

## 10. Complete Example Investigation Flow

### Scenario: "AI tokens with identical scopes show 50/50 performance split"

**Step 1: Overseer asks Q1**
```
Overseer: "How are we doing?"
Level 6: Executes level1_recipe_performance_overview_v1
Level 1: Returns performance map with surprising_anomalies:
  {
    "surprising_anomalies": [{
      "type": "scope_divergence",
      "description": "AI tokens with identical scopes show 50% strong, 50% weak performance",
      "pattern_key": "pm.uptrend.S1.entry",
      "suggested_investigation": "semantic",
      "priority": "high"
    }]
  }
```

**Step 2: Overseer asks Level 1 to zoom**
```
Overseer: "Zoom into AI tokens with pattern pm.uptrend.S1.entry that show mixed performance"
Level 6: Executes level1_recipe_zoom_semantic_breakdown_v1 with filters:
  - pattern_key: pm.uptrend.S1.entry
  - semantic_filter: AI
  - performance_filter: mixed
Level 1: Returns zoomed slice:
  {
    "zoomed_region": {
      "token_breakdown": [
        {"token_address": "0x123...", "edge_raw": 0.15, "n": 45},
        {"token_address": "0x456...", "edge_raw": -0.08, "n": 38},
        ...
      ],
      "key_differences": [
        {
          "dimension": "semantic_factor",
          "value_a": "AI Infra",
          "value_b": "AI Meme",
          "edge_a": 0.12,
          "edge_b": -0.05
        }
      ]
    }
  }
```

**Step 3: Overseer understands shape and routes investigation**
```
Overseer: "These 12 AI tokens have identical scopes but semantic subclasses differ. 
           Investigate whether semantic subclasses explain the divergence."
Level 6: Prepares exact bundle for Level 2:
  - Calls token_metadata_bundle for those 12 tokens
  - Calls semantic_factor_summary for those tokens
  - Calls performance_breakdown_by_token for those tokens
  - Assembles into targeted bundle
Level 6: Executes level2_recipe_semantic_subclass_analysis_v1
Level 2: Receives bundle, analyzes ONLY provided data, returns:
  {
    "findings": [{
      "divergence_explanation": "Half are 'AI Infra' tokens (high utility, strong roadmap), 
                                half are 'AI Meme' tokens (trend-chasing, weak roadmap)",
      "recommended_actions": ["add_to_scope"]
    }]
  }
```

**Step 4: Overseer receives findings and decides next step**
```
Overseer: "Semantic subclasses explain divergence. Should integrate into scopes."
Overseer: "Propose scope changes to incorporate semantic_meta dimension"
Level 6: Prepares exact bundle for Level 3:
  - Calls scope_delta_summary for that pattern
  - Calls dimension_importance_summary
  - Assembles into targeted bundle
Level 6: Executes level3_recipe_scope_integration_v1
Level 3: Receives bundle, analyzes ONLY provided data, returns:
  {
    "new_dimension_proposals": [{
      "dimension_name": "semantic_meta",
      "dimension_type": "semantic",
      "values": ["AI Infra", "AI Meme", "AI Agent", ...],
      "rationale": "Semantic subclasses explain performance divergence",
      "integration_complexity": "medium"
    }]
  }
```

**Step 5: Overseer reviews and escalates to math**
```
Overseer: "Proposal looks good. Send to math layer for validation."
Level 6: Forwards scope proposal to math test queue
Math Layer: Runs SQL tests, confirms edge improvement
System: Lesson builder incorporates new scope dimension
```

---

## 11. Implementation Notes / Future Enhancements

1. **Data Catalog**
   - YAML/JSON describing tables, fields, summarizers, bundle schemas
   - Should be easily inspectable by humans and the Overseer (via tool)

2. **Recipe Store**
   - Could live in code repo (version controlled) and/or Supabase
   - Metadata includes owner, last_updated, approval status
   - Level 6 can create/modify recipes based on Overseer instructions (long-term)

3. **LLM Sandbox**
   - Each recipe should run under isolated runtime with guardrails
   - Logging for inputs/outputs (with redaction if needed)

4. **Testing & Validation**
   - Before enabling a recipe, run it in "dry run" mode (log output but don't forward to consumers)
   - Have math layer verify early outputs, ensure they're sane

5. **Metrics**
   - Track ROI per level/recipe (did it lead to validated hypotheses? overrides? tuning wins?)
   - Use metrics to prioritize research investment

6. **Scaling**
   - As new tables/dimensions appear (semantic factors, new CF metrics), add summarizers + catalog entries
   - Level 6 & Overseer adapt recipes accordingly

---

## 12. Summary

- **Overseer (Active Intelligence)** asks 5 core questions, interprets results, routes investigations
- **Level 6 (Data Provisioner)** translates questions into recipes, prepares exact bundles, protects system
- **Level 1 (Zoomable Perception)** provides structured awareness and can zoom into specific regions
- **Levels 2-5 (Blind Researchers)** receive exact bundles and answer targeted questions only
- **Data infrastructure** separates raw tables from LLMs via summarizers and bundles
- **Recipes** describe everything: inputs, tasks, outputs, triggers, consumers
- **Validation and scoring** keep the system safe; outputs always go through math/tuning before affecting overrides

**Complete Flow:** 
```
Perceive (L1) → Think (Overseer) → Zoom (L1) → Think (Overseer) → Investigate (L2-5) → Verify (Math) → Adapt (System)
```

**Key Principle:** Levels 2-5 are blind researchers. They do NOT access Level 1 data or fetch their own data. They ONLY receive exact bundles prepared by Level 6 and answer very specific questions.

This blueprint should guide both near-term implementation (v5 launch) and long-term evolution (adaptive research agent).
