# LLM Research Layer + Simplified Allocation Plan Integration

**Status**: Analysis  
**Date**: 2025-01-XX

---

## Executive Summary

The Simplified Allocation & Global Edge Plan **dramatically enhances** what the LLM Research Layer can reason about. The new 6-dimensional edge scores, decay metadata, and exposure/crowding data provide rich signals that directly answer Overseer's core questions and enable much deeper investigation.

---

## 1. 6-Dimensional Edge Scores → Richer Level 1 Analysis

### What Changed
Instead of just `edge_raw` (scalar), we now have:
- `ev_score` — expected value advantage
- `reliability_score` — reliability/variance
- `support_score` — sample size confidence
- `magnitude_score` — median R/R strength
- `time_score` — time efficiency
- `stability_score` — edge volatility

### Impact on LLM Layer

#### **Level 1 Can Now Answer:**
- **"Why is edge strong/weak?"** — Can break down into components:
  - "Edge is 2.5, but reliability is low (0.3) — this is fragile"
  - "EV is high (0.9) but time_score is poor (0.2) — slow payback"
  - "Magnitude is strong but stability is low — inconsistent"

#### **Overseer Can Ask Deeper Questions:**
- "Which patterns have high EV but low reliability?" → Route to Level 3 (structure)
- "Why is magnitude_score high but time_score low?" → Route to Level 5 (timing)
- "Are stability_score and reliability_score correlated?" → Route to Level 4 (cross-domain)

#### **Level 3 Can Investigate:**
- "This scope has high EV but low reliability — should we split by volatility?"
- "Support_score is low — do we need more specific scopes?"

### New Level 1 Output Schema Addition
```json
{
  "edge_breakdown": {
    "pattern_key": "pm.uptrend.S1.entry",
    "scope": {...},
    "edge_raw": 2.5,
    "edge_components": {
      "ev_score": 0.9,
      "reliability_score": 0.3,
      "support_score": 0.7,
      "magnitude_score": 0.8,
      "time_score": 0.2,
      "stability_score": 0.4
    },
    "interpretation": "High EV but fragile (low reliability, low stability)"
  }
}
```

---

## 2. Decay Metadata → Direct Answer to Q5

### What Changed
Per-mask decay with:
- Linear slope (`edge/hour`)
- Exponential rate (`B`)
- Half-life (`half_life_hours`)
- Decay state (`improving|decaying|stable`)
- Decay multiplier (`decay_mult ∈ [0.33, 1.33]`)

All stored in `pattern_scope_stats.stats` alongside edge scores.

### Impact on LLM Layer

#### **Q5: "How is our edge changing over time?"** — Now Has Direct Data
Level 1 can now answer:
- "Pattern X is decaying with half-life of 48 hours"
- "Scope Y is improving rapidly (slope +0.1/hour)"
- "Mask Z is stable (no clear decay pattern)"

#### **Overseer Can Ask:**
- "Which patterns are decaying fastest?" → Level 1 zoom
- "Why is this pattern decaying?" → Level 2 (semantic) or Level 3 (structure)
- "Should we retire this decaying pattern?" → Level 3 (structure)

#### **Level 3 Can Investigate:**
- "This scope is decaying — should we split it?"
- "Decay rate differs by volatility bucket — should we adjust scope?"

### New Level 1 Output Schema Addition
```json
{
  "edge_trends": {
    "decaying_patterns": [
      {
        "pattern_key": "pm.uptrend.S1.entry",
        "scope": {...},
        "decay_state": "decaying",
        "half_life_hours": 48,
        "slope": -0.05,
        "decay_mult": 0.5,
        "urgency": "high"
      }
    ],
    "improving_patterns": [...],
    "stable_patterns": [...]
  }
}
```

---

## 3. Exposure/Crowding Data → New Dimension for Analysis

### What Changed
New `exposure_skew` logic tracks:
- `scope_exposure[m]` — how crowded each scope mask is
- `pk_scope_exposure[(pattern_key, m)]` — pattern-specific crowding
- `exposure_skew ∈ [0.33, 1.33]` — multiplier applied to sizing

### Impact on LLM Layer

#### **New Overseer Question:**
**Q6: "Where are we over-concentrated or under-diversified?"**

Level 1 can now answer:
- "We're heavily concentrated in AI tokens with high volatility"
- "Scope X has 80% of our exposure but only 1.2x edge"
- "We're avoiding low-cap privacy coins (exposure_skew = 1.33) but edge is 2.5"

#### **Overseer Can Ask:**
- "Are we crowding into weak edges?" → Level 1 zoom
- "Why are we avoiding high-edge scopes?" → Level 2 (semantic) or Level 3 (structure)
- "Should we diversify away from crowded scopes?" → Level 3 (structure)

#### **Level 1 Can Highlight:**
- **Crowding anomalies**: "High edge but also high crowding — risk of over-concentration"
- **Diversification opportunities**: "High edge, low crowding — under-exploited"
- **Inefficient allocation**: "Low edge, high crowding — should reduce"

### New Level 1 Output Schema Addition
```json
{
  "exposure_analysis": {
    "crowded_zones": [
      {
        "scope": {...},
        "exposure_pct": 0.8,
        "edge_raw": 1.2,
        "exposure_skew": 0.5,
        "risk": "over-concentrated"
      }
    ],
    "diversification_opportunities": [
      {
        "scope": {...},
        "exposure_pct": 0.05,
        "edge_raw": 2.5,
        "exposure_skew": 1.3,
        "opportunity": "under-exploited"
      }
    ]
  }
}
```

---

## 4. Unified Scopes → More Granular Investigation

### What Changed
Unified scope dimensions (entry + action + regime):
- Entry: `curator`, `chain`, `mcap_bucket`, `vol_bucket`, `age_bucket`, `intent`, `mapping_confidence`, `mcap_vol_ratio_bucket`
- Action: `market_family`, `timeframe`, `A_mode`, `E_mode`
- Regime: `macro_phase`, `meso_phase`, `micro_phase`, `bucket_leader`, `bucket_rank_position`

### Impact on LLM Layer

#### **Level 3 Can Investigate More Dimensions:**
- "Does curator matter for edge?" (entry dimension)
- "Does chain affect performance?" (entry dimension)
- "Does intent (buy/sell) correlate with edge?" (entry dimension)
- "Should we split by mapping_confidence?" (entry dimension)

#### **Level 1 Can Zoom More Precisely:**
- "Zoom into AI tokens from curator X in high volatility"
- "Show breakdown by chain (Solana vs Base)"
- "Compare performance by intent (buy vs sell signals)"

#### **Level 2 Can Investigate:**
- "Do semantic factors correlate with curator performance?"
- "Are certain chains better for certain semantic categories?"

---

## 5. Global Edge → More Meaningful Comparisons

### What Changed
Edge is now global (all trades in one pool), not module-specific.

### Impact on LLM Layer

#### **Level 1 Can Compare:**
- Patterns across all modules uniformly
- Edge is more stable/interpretable
- Comparisons are more meaningful

#### **Overseer Can Reason:**
- "Why does pattern X have 2.5x edge globally but 1.2x in PM context?"
- Actually wait — this is now unified, so comparisons are cleaner

---

## 6. Updated Overseer Questions

### New/Enhanced Questions

#### **Q5 (Enhanced): "How is our edge changing over time?"**
Now has direct decay metadata:
- Decay rates, half-lives, slopes
- Improving vs decaying patterns
- Urgency signals

#### **Q6 (New): "Where are we over-concentrated or under-diversified?"**
New question enabled by exposure data:
- Crowding analysis
- Diversification opportunities
- Allocation efficiency

#### **Q2/Q3 (Enhanced): "Where are we strongest/weakest?"**
Can now break down by edge components:
- "Strong EV but weak reliability"
- "High magnitude but poor time efficiency"
- "Good support but low stability"

---

## 7. Updated Level 1 Output Schema

### Enhanced Schema
```json
{
  "edge_health": {
    "overall_status": "healthy|degrading|emerging",
    "strong_zones": [
      {
        "pattern_key": "string",
        "scope": {...},
        "edge_raw": 2.5,
        "edge_components": {
          "ev_score": 0.9,
          "reliability_score": 0.3,
          "support_score": 0.7,
          "magnitude_score": 0.8,
          "time_score": 0.2,
          "stability_score": 0.4
        },
        "decay_metadata": {
          "decay_state": "stable|improving|decaying",
          "half_life_hours": 48,
          "slope": 0.05,
          "decay_mult": 1.1
        },
        "exposure": {
          "exposure_pct": 0.3,
          "exposure_skew": 0.9,
          "crowding_level": "moderate"
        },
        "interpretation": "High EV but fragile (low reliability, low stability). Stable decay. Moderate crowding."
      }
    ],
    "weak_zones": [...],
    "anomalies": [...],
    "edge_trends": {
      "decaying_patterns": [...],
      "improving_patterns": [...],
      "stable_patterns": [...]
    },
    "exposure_analysis": {
      "crowded_zones": [...],
      "diversification_opportunities": [...]
    }
  }
}
```

---

## 8. Updated Summarizers Needed

### New Summarizers
1. **`summarize_edge_components`** — Returns 6D edge breakdown per pattern/scope
2. **`summarize_decay_metadata`** — Returns decay rates, half-lives, slopes
3. **`summarize_exposure_crowding`** — Returns exposure maps and crowding analysis
4. **`summarize_edge_trends`** — Returns improving/decaying/stable patterns

### Enhanced Summarizers
1. **`summarize_pattern_edges`** — Now includes 6D components + decay + exposure
2. **`summarize_global_edges`** — Now includes decay trends + crowding

---

## 9. Implementation Impact

### Level 1 Changes
- Output schema must include 6D edge components
- Must report decay metadata
- Must report exposure/crowding analysis
- Must interpret edge breakdowns

### Level 3 Changes
- Can investigate scope splits based on edge components
- Can investigate decay patterns
- Can investigate crowding vs edge relationships

### Level 5 Changes
- Can investigate timing issues (time_score)
- Can investigate stability issues (stability_score)
- Can investigate counterfactuals with decay context

### Overseer Changes
- Can ask Q6 (exposure/crowding)
- Can ask deeper questions about edge components
- Can reason about decay urgency
- Can prioritize investigations based on decay + crowding

---

## 10. Key Insights

1. **6D Edge Scores** → LLM can reason about *why* edge is strong/weak, not just *that* it is
2. **Decay Metadata** → Direct answer to Q5, enables proactive pattern retirement
3. **Exposure Data** → New dimension for analysis, enables diversification reasoning
4. **Unified Scopes** → More granular investigation possible
5. **Global Edge** → Cleaner comparisons, more stable signals

**The LLM layer becomes much more powerful** because it can now reason about:
- **What** is happening (edge_raw)
- **Why** it's happening (6D breakdown)
- **How fast** it's changing (decay)
- **Where** we're concentrated (exposure)
- **What** we should do about it (synthesis)

---

## Next Steps

1. **Update Level 1 schema** to include 6D components, decay, exposure
2. **Update summarizers** to fetch new data
3. **Add Q6** to Overseer question set
4. **Update Level 3** to investigate edge components
5. **Update Level 5** to investigate timing/stability issues
6. **Test end-to-end** with new data structure

