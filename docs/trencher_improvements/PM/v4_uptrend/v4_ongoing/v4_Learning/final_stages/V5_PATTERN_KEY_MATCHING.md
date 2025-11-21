# v5 Pattern Key Matching in Override Application

**Purpose**: Trace how pattern keys are used to match and apply lessons at runtime

---

## Pattern Key Format

Pattern keys are canonical identifiers in format:
```
module=pm|pattern_key=family.state.motif
```

Example:
```
module=pm|pattern_key=uptrend.S1.buy_flag
```

---

## Override Application Flow

### Step 1: Action Planning (`plan_actions_v4`)

**Location**: `pm/actions.py:_apply_v5_overrides_to_action()`

When PM plans an action:
1. Gets `decision_type` from action (e.g., "add", "trim", "emergency_exit")
2. Builds `action_context` with:
   - `state` (from uptrend_engine_v4)
   - `timeframe`
   - `a_final`, `e_final`
   - `buy_flag`, `first_dip_buy_flag`, etc.
   - `market_family` = "lowcaps"
3. **Generates pattern_key**:
   ```python
   pattern_key, action_category = generate_canonical_pattern_key(
       module="pm",
       action_type=decision_type,  # e.g., "add"
       action_context=action_context,
       uptrend_signals=uptrend
   )
   ```
   Returns: `("module=pm|pattern_key=uptrend.S1.buy_flag", "entry")`
4. Extracts `scope` from context (macro_phase, meso_phase, bucket, etc.)

**Key Point**: Pattern key is generated **fresh** at runtime from current action context

---

### Step 2: Override Loading (`pm/overrides.py`)

**Location**: `pm/overrides.py:_load_config_overrides()`

1. Loads config from `learning_configs.pm.config_data`
2. Extracts:
   - `pattern_strength_overrides` (capital levers)
   - `pattern_overrides` (execution levers)
3. **Cached** (LRU cache, maxsize=1) - reloads when cache cleared

---

### Step 3: Pattern Key Matching (`pm/overrides.py`)

**Location**: `pm/overrides.py:_find_matching_overrides()`

For each override in config:

1. **Exact pattern_key match**:
   ```python
   if override.get('pattern_key') != pattern_key:
       continue  # Skip if pattern_key doesn't match exactly
   ```
   Example:
   - Override: `"module=pm|pattern_key=uptrend.S1.buy_flag"`
   - Current: `"module=pm|pattern_key=uptrend.S1.buy_flag"`
   - ✅ Match

2. **Exact action_category match**:
   ```python
   if override.get('action_category') != action_category:
       continue  # Skip if action_category doesn't match
   ```
   Example:
   - Override: `"entry"`
   - Current: `"entry"`
   - ✅ Match

3. **Scope subset match**:
   ```python
   override_scope = override.get('scope', {})  # e.g., {"macro_phase": "Recover", "bucket": "micro"}
   if not _scope_matches(override_scope, current_scope):
       continue  # Skip if override scope is not subset of current scope
   ```
   Example:
   - Override scope: `{"macro_phase": "Recover", "bucket": "micro"}`
   - Current scope: `{"macro_phase": "Recover", "meso_phase": "Dip", "bucket": "micro", "timeframe": "1h"}`
   - ✅ Match (override scope is subset)

4. **Check if enabled**:
   ```python
   if not lesson.get('enabled', True):
       continue  # Skip if lesson disabled
   ```

5. **Collect matches** and sort by specificity (most scope dims = most specific)

---

### Step 4: Apply Most Specific Override

**Location**: `pm/overrides.py:apply_pattern_strength_overrides()`

1. Gets all matching overrides (from Step 3)
2. Uses **most specific match** (first in sorted list):
   ```python
   matches = _find_matching_overrides(...)
   if not matches:
       return base_levers  # No match, return unchanged
   
   best_match = matches[0]  # Most specific (most scope dims)
   ```
3. Applies levers:
   ```python
   size_mult = best_match["levers"].get("size_mult", 1.0)
   entry_aggression_mult = best_match["levers"].get("entry_aggression_mult", 1.0)
   exit_aggression_mult = best_match["levers"].get("exit_aggression_mult", 1.0)
   ```
4. Clamps to bounds (0.7-1.3 for size_mult, etc.)

---

## Example: Full Matching Flow

### Scenario
- PM is planning an "add" action
- Current state: S2
- Current scope: `{"macro_phase": "Recover", "meso_phase": "Dip", "bucket": "micro", "timeframe": "1h"}`
- Pattern key generated: `"module=pm|pattern_key=uptrend.S2.buy_flag"`
- Action category: `"add"`

### Override Config
```json
{
  "pattern_strength_overrides": [
    {
      "pattern_key": "module=pm|pattern_key=uptrend.S2.buy_flag",
      "action_category": "add",
      "scope": {
        "macro_phase": "Recover",
        "bucket": "micro"
      },
      "levers": {
        "size_mult": 1.15,
        "entry_aggression_mult": 1.10
      }
    },
    {
      "pattern_key": "module=pm|pattern_key=uptrend.S2.buy_flag",
      "action_category": "add",
      "scope": {
        "macro_phase": "Recover"
      },
      "levers": {
        "size_mult": 1.10
      }
    }
  ]
}
```

### Matching Process

1. **Pattern key match**: Both overrides match `"module=pm|pattern_key=uptrend.S2.buy_flag"` ✅
2. **Action category match**: Both match `"add"` ✅
3. **Scope match**:
   - Override 1: `{"macro_phase": "Recover", "bucket": "micro"}` ✅ (subset of current)
   - Override 2: `{"macro_phase": "Recover"}` ✅ (subset of current)
4. **Specificity sorting**:
   - Override 1: 2 scope dims (more specific)
   - Override 2: 1 scope dim (less specific)
   - Result: Override 1 is selected (most specific)

### Applied Override

```python
size_mult = 1.15  # From Override 1 (more specific)
entry_aggression_mult = 1.10  # From Override 1
```

---

## Key Points

1. **Pattern key must match exactly** - no partial matching
2. **Action category must match exactly** - "entry" ≠ "add"
3. **Scope uses subset matching** - override scope must be subset of current scope
4. **Most specific wins** - override with most scope dims is selected
5. **Pattern key is generated fresh** at runtime from current action context
6. **Same pattern key format** used in:
   - Action logging (pm_action strands)
   - Aggregation (pattern_scope_stats)
   - Lessons (learning_lessons)
   - Overrides (learning_configs)

---

## Verification

To verify correct matching:

1. Check pattern key generation:
   ```python
   pattern_key, action_category = generate_canonical_pattern_key(...)
   # Should match format: "module=pm|pattern_key=family.state.motif"
   ```

2. Check override config:
   ```sql
   SELECT config_data->'pattern_strength_overrides' 
   FROM learning_configs 
   WHERE module_id = 'pm';
   ```
   Pattern keys should match format above

3. Check matching logic:
   - Pattern key: Exact string match ✅
   - Action category: Exact string match ✅
   - Scope: Subset matching ✅
   - Most specific: Selected ✅

---

## Potential Issues

1. **Pattern key format mismatch**: If override has different format than generated key, no match
   - Fix: Ensure consistent format in lesson builder

2. **Action category mismatch**: If override has "entry" but action is "add", no match
   - Fix: Ensure action_category mapping is consistent

3. **Scope mismatch**: If override scope has dims not in current scope, no match
   - Fix: Ensure scope extraction includes all relevant dims

4. **Cache staleness**: If config updated but cache not cleared, old overrides used
   - Fix: Clear cache after override materializer runs

