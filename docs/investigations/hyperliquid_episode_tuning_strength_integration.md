# Hyperliquid Integration: Episode, Tuning, and PM Strength Analysis

**Date**: 2025-12-31  
**Status**: ✅ Integrated (with one caveat)

---

## Summary

**Good News**: Hyperliquid positions are **fully integrated** with:
- ✅ Episode logging system
- ✅ PM tuning system  
- ✅ PM strength system

**Caveat**: A/E v2 regime driver lookup needs a mapping function for crypto book_ids.

---

## 1. Episode System Integration ✅

### How Episodes Work

Episodes track trading opportunities (S1 entry, S2 entry, S3 retest) and log:
- **Decisions**: Acted vs Skipped
- **Outcomes**: Success vs Failure
- **Factors**: Signal values at decision time

### Integration Points

**Location**: `pm_core_tick.py:3622-3670`

```python
episode_strands, meta_changed = self._process_episode_logging(
    position=p,
    regime_context=regime_context,
    token_bucket=token_bucket,
    now=now,
    levers=le,
)
```

**Scope Building**: `pm_core_tick.py:1129-1137`

```python
scope = extract_scope_from_context(
    action_context=action_context,
    regime_context=regime_context or {},
    position_bucket=token_bucket,
    bucket_rank=bucket_rank,
    regime_states=regime_states,
    chain=position.get("token_chain"),        # ✅ "hyperliquid"
    book_id=position.get("book_id"),         # ✅ "perps" or "stock_perps"
)
```

**Result**: 
- Episodes include `chain="hyperliquid"` and `book_id="perps"` (or `"stock_perps"`) in scope
- Episodes are logged to `pattern_episode_events` table
- **Note**: Episodes CAN be shared between venues if the miner finds patterns that don't include `chain`/`book_id` in the scope_subset (see Tuning section)

---

## 2. PM Tuning System Integration ✅

### How Tuning Works

1. **Episode Events** → Logged to `pattern_episode_events` with full scope (all dimensions)
2. **Tuning Miner** → Recursively mines frequent scope slices at different specificity levels
3. **Materializer** → Creates `pm_overrides` with threshold adjustments
4. **Runtime** → PM applies overrides using subset matching (multiple lessons can match)

### How Scope Mining Works

**Tuning Miner**: `tuning_miner.py:84-141`
- Discovers all scope dimensions from events (sorted alphabetically)
- Recursively mines lessons at different specificity levels:
  - Global: `{}` (applies to all positions)
  - By timeframe: `{"timeframe": "1h"}` (applies to all 1h positions)
  - By chain: `{"chain": "hyperliquid"}` (applies to all Hyperliquid)
  - By chain+timeframe: `{"chain": "hyperliquid", "timeframe": "1h"}` (Hyperliquid 1h only)
  - By chain+timeframe+bucket: `{"chain": "hyperliquid", "timeframe": "1h", "bucket": "micro"}` (most specific)

**Key Insight**: The miner creates lessons at **multiple specificity levels**. A lesson with `scope_subset = {"timeframe": "1h"}` would match **BOTH** Hyperliquid and Solana 1h positions.

### Runtime Matching

**Location**: `overrides.py:56-68`

```python
res = (
    sb_client.table('pm_overrides')
    .select('*')
    .eq('pattern_key', pattern_key)
    .eq('action_category', action_category)
    .filter('scope_subset', 'cd', scope_json)  # ✅ Supabase JSONB contains operator
    .execute()
)
```

**How it works**:
- `filter('scope_subset', 'cd', scope_json)` checks if `scope_subset` is **contained in** the position's scope
- Multiple lessons can match (at different specificity levels)
- Lessons are weighted by specificity: `specificity = (len(scope_subset) + 1.0) ** SPECIFICITY_ALPHA`
- More specific lessons (more dimensions) get higher weight

**Example**:
- Position scope: `{"chain": "hyperliquid", "book_id": "perps", "timeframe": "1h", "bucket": "micro"}`
- Lesson 1: `scope_subset = {"timeframe": "1h"}` → ✅ Matches (applies to all 1h)
- Lesson 2: `scope_subset = {"chain": "hyperliquid", "timeframe": "1h"}` → ✅ Matches (applies to Hyperliquid 1h)
- Lesson 3: `scope_subset = {"chain": "solana", "timeframe": "1h"}` → ❌ Doesn't match

**Result**:
- Tuning lessons **CAN** be shared between venues if the miner finds patterns that don't include `chain`/`book_id`
- Tuning lessons **CAN** be venue-specific if the miner includes `chain`/`book_id` in the scope_subset
- The system automatically uses the most specific matching lesson (weighted by specificity)

---

## 3. PM Strength System Integration ✅

### How PM Strength Works

1. **Position Closed Strands** → Logged with full scope (all dimensions)
2. **Pattern Scope Aggregator** → Computes edge statistics by `(pattern_key, scope)`
3. **Lesson Builder** → Mines lessons at different specificity levels (similar to tuning miner)
4. **Materializer** → Creates `pm_overrides` with strength multipliers
5. **Runtime** → PM applies strength multipliers using subset matching (same as tuning)

### Integration Points

**Scope Matching**: `overrides.py:56-68` (same as tuning)
```python
res = (
    sb_client.table('pm_overrides')
    .select('*')
    .eq('pattern_key', pattern_key)
    .eq('action_category', action_category)
    .filter('scope_subset', 'cd', scope_json)  # ✅ Supabase JSONB contains operator
    .execute()
)
```

**Scope Building**: `actions.py:154-180`
```python
scope = extract_scope_from_context(
    ...
    chain=position.get("token_chain"),      # ✅ "hyperliquid"
    book_id=position.get("book_id"),        # ✅ "perps" or "stock_perps"
)
```

**Result**:
- PM strength lessons **CAN** be shared between venues if the miner finds patterns that don't include `chain`/`book_id`
- PM strength lessons **CAN** be venue-specific if the miner includes `chain`/`book_id` in the scope_subset
- The system automatically uses the most specific matching lesson (weighted by specificity)
- Same subset matching logic as tuning system

---

## 4. A/E v2 Regime Driver Lookup ⚠️

### Current Behavior

**Location**: `ae_calculator_v2.py:202-251`

```python
def extract_regime_flags(
    sb_client,
    token_bucket: str,
    book_id: str = "onchain_crypto",  # ⚠️ Defaults to "onchain_crypto"
) -> Dict[str, Dict[str, bool]]:
    ...
    result = (
        sb_client.table("lowcap_positions")
        .select("features")
        .eq("token_ticker", ticker)
        .eq("status", "regime_driver")
        .eq("book_id", book_id)  # ⚠️ Exact match required
        .limit(1)
        .execute()
    )
```

**Problem**:
- Regime drivers are stored with `book_id="onchain_crypto"` (Solana)
- Hyperliquid positions have `book_id="perps"` (crypto) or `book_id="stock_perps"` (stocks)
- When Hyperliquid crypto positions call `extract_regime_flags(book_id="perps")`, it looks for regime drivers with `book_id="perps"`
- **Result**: No regime drivers found → all flags default to False → neutral A/E

### Expected Behavior

**For Hyperliquid Crypto (`book_id="perps"`)**:
- Should use same crypto regime drivers as Solana (`book_id="onchain_crypto"`)
- Both are crypto markets, so regime should be shared

**For Hyperliquid Stock Perps (`book_id="stock_perps"`)**:
- Should use neutral A/E (no crypto regime)
- This is already handled in the design doc

### Solution

**Option 1: Book ID Mapping Function** (Recommended)

```python
def get_regime_book_id(book_id: str) -> str:
    """Map crypto book_ids to shared regime driver book_id."""
    CRYPTO_BOOK_IDS = {"onchain_crypto", "perps", "spot_crypto", "perp_crypto"}
    if book_id in CRYPTO_BOOK_IDS:
        return "onchain_crypto"  # All crypto uses same regime drivers
    return book_id  # Other asset classes use their own
```

**Update `extract_regime_flags()`**:
```python
def extract_regime_flags(
    sb_client,
    token_bucket: str,
    book_id: str = "onchain_crypto",
) -> Dict[str, Dict[str, bool]]:
    # Map crypto book_ids to shared regime driver book_id
    regime_book_id = get_regime_book_id(book_id)
    
    result = (
        sb_client.table("lowcap_positions")
        .select("features")
        .eq("token_ticker", ticker)
        .eq("status", "regime_driver")
        .eq("book_id", regime_book_id)  # ✅ Use mapped book_id
        .limit(1)
        .execute()
    )
```

**Option 2: Create Hyperliquid Regime Drivers** (Not Recommended)
- Would duplicate regime drivers for each book_id
- Unnecessary complexity

---

## 5. Summary

### ✅ Fully Integrated

1. **Episode Logging**: 
   - Hyperliquid positions log episodes with `chain="hyperliquid"` and `book_id="perps"`/`"stock_perps"` in scope
   - Episodes include all scope dimensions (not just chain/book_id)

2. **PM Tuning**:
   - Tuning miner creates lessons at multiple specificity levels
   - Lessons **CAN** be shared between venues if they don't include `chain`/`book_id` in scope_subset
   - Lessons **CAN** be venue-specific if they include `chain`/`book_id` in scope_subset
   - Runtime uses subset matching with specificity weighting

3. **PM Strength**:
   - Same as tuning: lessons at multiple specificity levels
   - Lessons **CAN** be shared between venues if they don't include `chain`/`book_id` in scope_subset
   - Lessons **CAN** be venue-specific if they include `chain`/`book_id` in scope_subset
   - Runtime uses subset matching with specificity weighting

### ⚠️ Needs Fix

1. **A/E v2 Regime Driver Lookup**:
   - Currently, Hyperliquid crypto (`book_id="perps"`) can't find regime drivers (they're stored with `book_id="onchain_crypto"`)
   - **Fix**: Add `get_regime_book_id()` mapping function to group crypto book_ids
   - **Impact**: Without fix, Hyperliquid crypto positions get neutral A/E (0.5, 0.5) instead of regime-driven A/E

---

## 6. Action Items

1. **Implement `get_regime_book_id()` mapping function** in `ae_calculator_v2.py`
2. **Update `extract_regime_flags()`** to use mapped book_id
3. **Test**: Verify Hyperliquid crypto positions get correct regime-driven A/E
4. **Verify**: Stock perps still get neutral A/E (as designed)

## 7. Key Insights

### How Learning Actually Works

1. **Mining**: The miner discovers patterns at different specificity levels (global → specific)
2. **Matching**: Runtime uses subset matching - a lesson with `scope_subset = {"timeframe": "1h"}` matches ALL 1h positions (both Hyperliquid and Solana)
3. **Weighting**: More specific lessons (more dimensions) get higher weight
4. **Venue Separation**: Venue-specific lessons only exist if the miner finds enough samples to create a lesson that includes `chain`/`book_id` in the scope_subset

### When Are Lessons Shared vs Venue-Specific?

- **Shared**: If the miner finds a pattern with `scope_subset = {"timeframe": "1h", "bucket": "micro"}` (no chain/book_id), it applies to both venues
- **Venue-Specific**: If the miner finds a pattern with `scope_subset = {"chain": "hyperliquid", "timeframe": "1h", "bucket": "micro"}`, it only applies to Hyperliquid

**The system automatically discovers the right level of specificity based on data availability.**

---

## 7. Testing Checklist

- [ ] Hyperliquid crypto position logs episode with correct scope
- [ ] Tuning miner processes Hyperliquid episodes separately
- [ ] PM strength applies Hyperliquid-specific multipliers
- [ ] A/E v2 finds regime drivers for Hyperliquid crypto (`book_id="perps"`)
- [ ] A/E v2 returns neutral A/E for Hyperliquid stock perps (`book_id="stock_perps"`)

