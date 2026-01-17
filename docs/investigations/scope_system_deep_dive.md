# Scope System Deep Dive

**Date**: 2025-01-XX  
**Purpose**: Comprehensive analysis of how scopes work in the learning system

---

## Executive Summary

**Key Findings**:
1. **32 scope dimensions** total (DM + PM + Regime)
2. **All dimensions treated equally** in mining (sorted alphabetically)
3. **No dimension weighting in learning** - only specificity (count) matters
4. **Matching uses subset containment** - `scope_subset` must be contained in current `scope`
5. **Blending uses specificity + confidence** - `weight = confidence * (len(scope_subset) + 1.0)^1.5`
6. **Dimension weights exist** but only for `exposure_skew`, NOT for learning

---

## Scope Dimensions

### Complete List (32 dimensions)

**DM Dimensions** (from `entry_context`, set by Decision Maker):
- `curator` - Curator identifier
- `chain` - Blockchain (base, solana, ethereum, etc.)
- `mcap_bucket` - Market cap bucket at entry
- `vol_bucket` - Volume bucket at entry
- `age_bucket` - Token age bucket at entry
- `intent` - Intent type (research_positive, etc.)
- `mcap_vol_ratio_bucket` - Market cap to volume ratio bucket

**PM Dimensions** (from `action_context`, set by PM):
- `market_family` - Market family (lowcaps, etc.)
- `timeframe` - Timeframe (1m, 15m, 1h, 4h)
- `A_mode` - Aggressiveness mode (patient, normal, aggressive)
- `E_mode` - Exit assertiveness mode (patient, normal, aggressive)
- `bucket_leader` - Leading bucket in regime
- `bucket_rank_position` - Position in bucket rank

**Regime Dimensions** (from `regime_context`, 5 drivers × 3 horizons):
- `btc_macro`, `btc_meso`, `btc_micro`
- `alt_macro`, `alt_meso`, `alt_micro`
- `bucket_macro`, `bucket_meso`, `bucket_micro`
- `btcd_macro`, `btcd_meso`, `btcd_micro`
- `usdtd_macro`, `usdtd_meso`, `usdtd_micro`

**Total**: 7 DM + 6 PM + 15 Regime = **28 dimensions** (plus any additional ones discovered dynamically)

**Reference**: `src/intelligence/lowcap_portfolio_manager/jobs/pattern_scope_aggregator.py:27-38`

---

## How Scopes Are Extracted

### Location: `pattern_keys_v5.py::extract_scope_from_context()`

**Inputs**:
- `action_context` - PM action context (timeframe, A_mode, E_mode, etc.)
- `regime_context` - Regime states (5 drivers × 3 horizons)
- `position_bucket` - Token's cap bucket
- `bucket_rank` - Bucket rank list
- `chain` - Blockchain
- `book_id` - Book identifier

**Process**:
1. Extract PM dimensions from `action_context`
2. Derive `A_mode`/`E_mode` from A/E values if not provided
3. Add regime states from `regime_context`
4. Remove `None` values
5. Return unified scope dict

**Key Point**: Scope is built from **both** PM and DM context, merged together.

**Reference**: `src/intelligence/lowcap_portfolio_manager/pm/pattern_keys_v5.py:169-250`

---

## How Scopes Are Used in Mining

### Location: `lesson_builder_v5.py::mine_lessons()`

**Process**:

1. **Discover dimensions dynamically**:
   ```python
   scope_keys = set()
   for scope in df['scope']:
       if isinstance(scope, dict):
           scope_keys.update(scope.keys())
   
   valid_dims = sorted([k for k in scope_keys if k in SCOPE_DIMS])
   ```

2. **Flatten scope columns**:
   ```python
   for key in valid_dims:
       df[f"scope_{key}"] = df['scope'].apply(lambda x: x.get(key) if isinstance(x, dict) else None)
   ```

3. **Recursive Apriori mining**:
   ```python
   def mine_recursive(slice_df, current_mask, start_dim_idx):
       # Base case: Need N_MIN_SLICE trades (after deduplication)
       if len(deduplicated) < N_MIN_SLICE:
           return
       
       # Create lesson for this scope slice
       lesson = {
           "scope_subset": current_mask,  # e.g., {"timeframe": "15m", "bucket": "micro"}
           ...
       }
       
       # Recurse: Try adding each dimension
       for i in range(start_dim_idx, len(valid_dims)):
           dim = valid_dims[i]
           counts = slice_df[col].value_counts()
           valid_values = counts[counts >= N_MIN_SLICE].index.tolist()
           
           for val in valid_values:
               new_mask = current_mask.copy()
               new_mask[dim] = val
               mine_recursive(new_slice, new_mask, i + 1)
   ```

**Key Observations**:
- **Dimensions are sorted alphabetically** - no priority ordering
- **All dimensions treated equally** - no weighting in mining
- **Apriori pruning** - only branches on dimensions with `N >= N_MIN_SLICE` values
- **Creates lessons at multiple specificity levels**:
  - Global: `{}`
  - By timeframe: `{"timeframe": "15m"}`
  - By timeframe + bucket: `{"timeframe": "15m", "bucket": "micro"}`
  - By timeframe + bucket + chain: `{"timeframe": "15m", "bucket": "micro", "chain": "solana"}`

**Reference**: `src/intelligence/lowcap_portfolio_manager/jobs/lesson_builder_v5.py:274-396`

---

## How Scope Matching Works at Runtime

### Location: `overrides.py::apply_pattern_strength_overrides()`

**Matching Logic**:

```python
scope_json = json.dumps(scope)
res = (
    sb_client.table('pm_overrides')
    .select('*')
    .eq('pattern_key', pattern_key)
    .eq('action_category', action_category)
    .filter('scope_subset', 'cd', scope_json)  # Contains operator
    .execute()
)
```

**Supabase `cd` operator**: Checks if `scope_subset` is **contained in** current `scope`

**Example**:
- Current scope: `{"chain": "solana", "timeframe": "15m", "bucket": "micro", "mcap_bucket": "500k-1m"}`
- Override 1: `scope_subset = {}` → ✅ Matches (global, applies to all)
- Override 2: `scope_subset = {"timeframe": "15m"}` → ✅ Matches (15m is in scope)
- Override 3: `scope_subset = {"timeframe": "15m", "bucket": "micro"}` → ✅ Matches (both in scope)
- Override 4: `scope_subset = {"timeframe": "1h"}` → ❌ Doesn't match (1h not in scope)
- Override 5: `scope_subset = {"timeframe": "15m", "chain": "base"}` → ❌ Doesn't match (chain is "solana", not "base")

**Result**: Can have **multiple matches** at different specificity levels

**Reference**: `src/intelligence/lowcap_portfolio_manager/pm/overrides.py:56-68`

---

## How Scopes Are Weighted in Blending

### Location: `overrides.py::apply_pattern_strength_overrides()`

**Blending Formula**:

```python
SPECIFICITY_ALPHA = 1.5

for m in matches:
    scope_subset = m.get('scope_subset', {}) or {}
    specificity = (len(scope_subset) + 1.0) ** SPECIFICITY_ALPHA
    confidence = float(m.get('confidence_score', 0.5))
    multiplier = float(m.get('multiplier', 1.0))
    
    weight = confidence * specificity
    weighted_mults.append(multiplier * weight)
    total_weight += weight

final_mult = sum(weighted_mults) / total_weight
```

**Specificity Calculation**:
- Global `{}`: `specificity = (0 + 1.0)^1.5 = 1.0`
- `{"timeframe": "15m"}`: `specificity = (1 + 1.0)^1.5 = 2.83`
- `{"timeframe": "15m", "bucket": "micro"}`: `specificity = (2 + 1.0)^1.5 = 5.20`
- `{"timeframe": "15m", "bucket": "micro", "chain": "solana"}`: `specificity = (3 + 1.0)^1.5 = 8.0`

**Key Observations**:
- **Only count matters** - `len(scope_subset)`, not which dimensions
- **No dimension weighting** - `timeframe` and `chain` treated equally
- **Exponential growth** - More dimensions = much higher weight
- **Confidence multiplies** - `weight = confidence * specificity`

**Example Blending**:
- Global override: `multiplier = 1.1`, `specificity = 1.0`, `confidence = 0.8` → `weight = 0.8`
- 15m override: `multiplier = 1.15`, `specificity = 2.83`, `confidence = 0.9` → `weight = 2.55`
- Final: `(1.1 * 0.8 + 1.15 * 2.55) / (0.8 + 2.55) = 1.14`

**Reference**: `src/intelligence/lowcap_portfolio_manager/pm/overrides.py:70-84`

---

## Dimension Weighting: Does It Exist?

### Short Answer: **NO** (for learning)

**Dimension weights exist** in `pm_config.jsonc`:
```json
"scope_dim_weights": {
  "curator": 1.0,
  "chain": 1.0,
  "mcap_bucket": 1.0,
  ...
}
```

**But they're ONLY used for `exposure_skew`**, NOT for learning:
- Location: `exposure.py::ExposureLookup.build()`
- Purpose: Calculate concentration across scope masks
- NOT used in: Mining, lesson building, override matching, or blending

**Learning system treats all dimensions equally**:
- Mining: Sorted alphabetically, no priority
- Matching: Subset containment, no dimension preference
- Blending: Only specificity (count) matters, not which dimensions

**Reference**: 
- `src/config/pm_config.jsonc:35-54` (dimension weights defined)
- `src/intelligence/lowcap_portfolio_manager/pm/exposure.py:61` (only used for exposure)

---

## Scope Mining Order

### How Dimensions Are Processed

**Current Implementation**: **Alphabetical order**

```python
valid_dims = sorted([k for k in scope_keys if k in SCOPE_DIMS])
# Then iterates: for i in range(start_dim_idx, len(valid_dims))
```

**Example order** (alphabetical):
1. `age_bucket`
2. `alt_macro`
3. `alt_meso`
4. `alt_micro`
5. `btc_macro`
6. `btc_meso`
7. `btc_micro`
8. `bucket_leader`
9. `bucket_macro`
10. `bucket_meso`
11. `bucket_micro`
12. `bucket_rank_position`
13. `btcd_macro`
14. `btcd_meso`
15. `btcd_micro`
16. `chain`
17. `curator`
18. `intent`
19. `mcap_bucket`
20. `mcap_vol_ratio_bucket`
21. `market_family`
22. `timeframe`
23. `usdtd_macro`
24. `usdtd_meso`
25. `usdtd_micro`
26. `vol_bucket`
27. `A_mode`
28. `E_mode`

**Implications**:
- `A_mode` and `E_mode` are processed **last** (alphabetically)
- `timeframe` is processed relatively early
- `chain` is processed early
- No semantic priority - purely alphabetical

**Reference**: `src/intelligence/lowcap_portfolio_manager/jobs/lesson_builder_v5.py:305`

---

## Scope Matching: Subset Containment

### How It Works

**Supabase JSONB `cd` operator**: Checks if left operand is **contained in** right operand

```python
.filter('scope_subset', 'cd', scope_json)
```

**Meaning**: `scope_subset` must be a **subset** of current `scope`

**Example**:
```python
# Override stored in DB
scope_subset = {"timeframe": "15m", "bucket": "micro"}

# Current position scope
scope = {
    "chain": "solana",
    "timeframe": "15m",
    "bucket": "micro",
    "mcap_bucket": "500k-1m",
    "A_mode": "normal"
}

# Match? YES - all keys in scope_subset exist in scope with same values
```

**Key Point**: Matching is **exact value match** for keys in `scope_subset`. Extra keys in `scope` are ignored.

---

## Scope Blending: Specificity vs Confidence

### Current Formula

```python
specificity = (len(scope_subset) + 1.0) ** 1.5
weight = confidence * specificity
```

**Specificity Growth**:
- 0 dims: `1.0^1.5 = 1.0`
- 1 dim: `2.0^1.5 = 2.83`
- 2 dims: `3.0^1.5 = 5.20`
- 3 dims: `4.0^1.5 = 8.0`
- 4 dims: `5.0^1.5 = 11.18`

**Interpretation**:
- **Specificity dominates** - 3-dim override has 8x weight of global
- **Confidence modulates** - High confidence amplifies, low confidence dampens
- **Exponential growth** - Each additional dimension significantly increases weight

**Question**: Is this the right balance? Should specificity grow this fast?

---

## Scope Dimensions: Which Ones Matter?

### Analysis by Category

**DM Dimensions** (7):
- `curator` - Curator-specific patterns
- `chain` - Blockchain-specific patterns
- `mcap_bucket` - Market cap bucket patterns
- `vol_bucket` - Volume bucket patterns
- `age_bucket` - Token age patterns
- `intent` - Intent-specific patterns
- `mcap_vol_ratio_bucket` - Ratio bucket patterns

**PM Dimensions** (6):
- `market_family` - Market family (usually "lowcaps")
- `timeframe` - Trading timeframe (1m, 15m, 1h, 4h)
- `A_mode` - Aggressiveness mode (patient, normal, aggressive)
- `E_mode` - Exit assertiveness mode (patient, normal, aggressive)
- `bucket_leader` - Leading bucket in regime
- `bucket_rank_position` - Position in bucket rank

**Regime Dimensions** (15):
- 5 drivers (BTC, ALT, bucket, BTC.d, USDT.d) × 3 horizons (macro, meso, micro)

**Most Important** (likely):
- `timeframe` - Strongly affects pattern behavior
- `chain` - Different execution characteristics
- `mcap_bucket` - Different risk profiles
- Regime states - Market context matters

**Least Important** (likely):
- `A_mode`/`E_mode` - Derived from A/E, may be redundant
- `bucket_leader`/`bucket_rank_position` - Regime metadata
- Some regime dimensions - May be too granular

**But**: System treats them all equally!

---

## Issues and Observations

### 1. No Dimension Weighting in Learning

**Current**: All dimensions treated equally
- `timeframe` = `A_mode` = `btc_macro` in terms of specificity
- No way to say "timeframe matters more than A_mode"

**Impact**: 
- May create lessons for dimensions that don't matter
- Can't prioritize important dimensions

**Potential Fix**: Add dimension weights to mining/blending (but keep it simple)

### 2. Alphabetical Order in Mining

**Current**: Dimensions processed alphabetically
- `A_mode` processed last
- `timeframe` processed early

**Impact**:
- No semantic priority
- May miss important combinations if they're later in alphabet

**Potential Fix**: Define priority order (but alphabetical is simple and deterministic)

### 3. Specificity Growth May Be Too Aggressive

**Current**: `specificity = (len + 1.0)^1.5`
- 3-dim override has 8x weight of global
- 4-dim override has 11x weight of global

**Impact**:
- Very specific overrides dominate completely
- May overfit to narrow slices

**Potential Fix**: Reduce `SPECIFICITY_ALPHA` (e.g., 1.2 instead of 1.5)

### 4. No Dimension-Specific Confidence

**Current**: Confidence is per lesson (pattern + scope)
- Can't say "timeframe lessons are more reliable than A_mode lessons"

**Impact**:
- All dimensions contribute equally to confidence
- Can't account for dimension-specific noise

**Potential Fix**: Add dimension-specific confidence adjustments (complex)

---

## Recommendations

### 1. Keep Current System (Simple)

**Pros**:
- Simple and deterministic
- No dimension bias
- Easy to understand and debug

**Cons**:
- May create lessons for irrelevant dimensions
- Can't prioritize important dimensions

### 2. Add Dimension Weights (Moderate)

**Implementation**:
- Add `dimension_weights` to config
- Use in specificity calculation: `specificity = sum(weights[d] for d in scope_subset) ** alpha`
- Keep default weights = 1.0 (backward compatible)

**Pros**:
- Can prioritize important dimensions
- Still simple (just sum weights)

**Cons**:
- Need to tune weights
- Adds complexity

### 3. Reduce Specificity Growth (Easy)

**Implementation**:
- Change `SPECIFICITY_ALPHA` from 1.5 to 1.2 or 1.0
- Makes blending more balanced

**Pros**:
- Simple one-line change
- Reduces overfitting risk

**Cons**:
- May reduce specificity advantage too much

---

## Summary

**Current State**:
- 32 scope dimensions (DM + PM + Regime)
- All dimensions treated equally
- Mining uses alphabetical order
- Matching uses subset containment
- Blending uses `specificity = (len + 1.0)^1.5 * confidence`
- No dimension weighting in learning (only in exposure_skew)

**Key Insight**: The system is **dimension-agnostic** - it doesn't care which dimensions are in a scope, only **how many** dimensions (specificity).

**Question**: Should we add dimension weighting, or keep it simple?

