# GeckoTerminal Extreme Price Jumps Investigation

**Date**: 2026-01-10  
**Status**: Investigation Required - No Changes Yet

---

## Problem

Almost every token is showing "extreme price jump" warnings with ratios like:
- 129.04x
- 152.82x  
- 67,743.23x

These are being skipped during backfill, which could cause data gaps.

---

## Current Detection Logic

**Location**: `geckoterminal_backfill.py` lines 345-352

```python
# Check for extreme jumps (>100x change) - likely bad data
# Compare close to open as a sanity check
if close_usd > 0 and open_usd > 0:
    price_change_ratio = max(close_usd / open_usd, open_usd / close_usd)
    if price_change_ratio > 100.0:
        skipped_count += 1
        logger.warning(f"Skip entry {ts_iso}: extreme price jump (ratio={price_change_ratio:.2f})")
        continue
```

**What it checks**: Within a single bar, if `close_usd / open_usd` or `open_usd / close_usd` > 100.0, skip the bar.

---

## Key Questions to Answer

### 1. What Units Does GeckoTerminal Return?

**Current assumption** (line 9, 329):
- Comment says: "Uses USD prices only"
- Comment says: "Volume is already in USD from GeckoTerminal"
- Code directly assigns `entry[1-4]` to `open_usd`, `high_usd`, `low_usd`, `close_usd`

**Potential issue**: 
- GeckoTerminal might return prices in **quote token units** (e.g., TOKEN/SOL prices in SOL)
- If pool is TOKEN/SOL, prices are in SOL, not USD
- If pool is TOKEN/USDC, prices might be in USDC (which is ~USD but not exactly)

**Evidence**:
- Line 6: "prefers native-quoted highest-liquidity" → suggests TOKEN/NATIVE pools
- Line 180-193: Pool selection prefers TOKEN/NATIVE pairs
- No conversion logic visible in the code

### 2. Are Pools Switching?

**Potential issue**: If canonical pool changes (e.g., from TOKEN/SOL to TOKEN/USDC), the units would be completely different:
- TOKEN/SOL: price = 0.001 SOL
- TOKEN/USDC: price = 0.50 USDC
- If we switch pools mid-backfill, 0.001 vs 0.50 would look like a 500x jump

**Code flow**:
- Line 478-537: Gets canonical pool from features OR selects new pool
- Line 555-561: Fetches OHLCV using that pool
- **No check**: Does the pool match what was used for previous bars?

### 3. What Are the Actual Price Values?

**Need to log**:
- `open_usd` and `close_usd` values when ratio > 100
- `quote_symbol` of the pool being used
- Pool address being used
- Whether this is a new pool vs existing pool

### 4. Is This Real Price Volatility or Bad Data?

**Possible scenarios**:
- **Real volatility**: Token actually did 100x+ in one bar (unlikely but possible for low-cap tokens)
- **Bad data from GeckoTerminal**: API returning incorrect values
- **Unit mismatch**: Prices in different units (native vs USD)
- **Pool switch**: Different pool with different quote token
- **Data corruption**: Malformed response from API

---

## Investigation Plan

### Step 1: Add Diagnostic Logging (No Changes Yet)

**What to log when extreme jump detected**:

```python
# When ratio > 100.0, log:
logger.warning(
    "EXTREME_PRICE_JUMP_DIAG: %s/%s tf=%s | "
    "ts=%s | "
    "open=%.10f close=%.10f ratio=%.2f | "
    "pool=%s quote=%s | "
    "high=%.10f low=%.10f | "
    "volume=%.2f",
    token_contract, chain, timeframe,
    ts_iso,
    open_usd, close_usd, price_change_ratio,
    pool_addr, quote_symbol,
    high_usd, low_usd,
    volume_usd
)
```

**This will reveal**:
- Actual price values (are they reasonable?)
- Pool being used (is it consistent?)
- Quote symbol (SOL vs USDC vs other?)
- Whether high/low also show the jump (suggests real data vs single bad value)

### Step 2: Check Pool Consistency

**Add check**: Before processing OHLCV, verify pool hasn't changed:

```python
# Get last bar's pool info from database
last_bar = supabase.client.table('lowcap_price_data_ohlc')
    .select('pair_address, dex_id')
    .eq('token_contract', token_contract)
    .eq('chain', chain)
    .eq('timeframe', timeframe)
    .order('timestamp', desc=True)
    .limit(1)
    .execute()

if last_bar.data:
    last_pool = last_bar.data[0].get('pair_address')
    if last_pool and last_pool != pool_addr:
        logger.warning("POOL_SWITCH_DETECTED: %s/%s | old_pool=%s new_pool=%s", 
                      token_contract, chain, last_pool, pool_addr)
```

### Step 3: Verify GeckoTerminal API Response Format

**Check**:
- Does GeckoTerminal's `/ohlcv/{timeframe}` endpoint return USD prices or quote token prices?
- What does the API documentation say?
- Test with a known pool and verify units

**Test query**:
```python
# Fetch one bar and inspect
data = _fetch_gt_ohlcv_by_pool(network, pool_addr, limit=1, ...)
ohlcv_list = data.get('data', {}).get('attributes', {}).get('ohlcv_list', [])
if ohlcv_list:
    entry = ohlcv_list[0]
    logger.info("GT_API_SAMPLE: pool=%s | entry=%s", pool_addr, entry)
    # Check if values look like USD or native
```

### Step 4: Check for Pool Metadata in Response

**GeckoTerminal might include**:
- Base token info
- Quote token info  
- Price units in metadata

**Check response structure**:
```python
# After fetching OHLCV, log full response structure
logger.debug("GT_RESPONSE_STRUCTURE: %s", json.dumps(data, indent=2)[:1000])
```

### Step 5: Compare with Existing Data

**For tokens showing jumps**:
- Query existing bars in database
- Check if previous bars used same pool
- Check if price values are consistent
- Check if there's a pattern (always at certain times, certain tokens, etc.)

---

## Hypotheses

### Hypothesis 1: Unit Mismatch (Most Likely)
**Theory**: GeckoTerminal returns prices in quote token (SOL, USDC, etc.), not USD
- TOKEN/SOL pool: prices in SOL (e.g., 0.001 SOL)
- Code assumes USD, so stores 0.001 as USD
- If SOL = $100, actual USD price should be 0.001 * 100 = $0.10
- But we're storing 0.001, which is 100x too small
- When pool switches or SOL price changes, ratios look extreme

**Evidence needed**: 
- Check if prices match known USD values
- Check quote_symbol vs actual price magnitudes
- Compare with other price sources

### Hypothesis 2: Pool Switching
**Theory**: Canonical pool changes mid-backfill, causing unit mismatch
- Started with TOKEN/SOL pool (prices in SOL)
- Switched to TOKEN/USDC pool (prices in USDC)
- 0.001 SOL vs 0.50 USDC = 500x jump

**Evidence needed**:
- Check if pool_addr changes between bars
- Check if quote_symbol changes
- Log pool consistency

### Hypothesis 3: GeckoTerminal API Bug
**Theory**: GeckoTerminal API is returning bad data
- API returning incorrect values
- Data corruption in transmission
- API version issue

**Evidence needed**:
- Compare with other price sources
- Check if same timestamps show jumps in multiple tokens
- Test API directly

### Hypothesis 4: Real Volatility (Unlikely)
**Theory**: Tokens actually did 100x+ in one bar
- Low-cap tokens can be extremely volatile
- But 67,743x is almost certainly not real

**Evidence needed**:
- Check if high/low also show extreme values
- Check volume (low volume = likely bad data)
- Check if pattern repeats across tokens

---

## Recommended Next Steps

1. **Add diagnostic logging** (see Step 1 above) - this will reveal the actual values
2. **Check pool consistency** (see Step 2 above) - verify pools aren't switching
3. **Verify GeckoTerminal API format** (see Step 3 above) - understand what units are returned
4. **Compare with existing data** (see Step 5 above) - see if there's a pattern

**Once we have diagnostic logs, we can determine**:
- If it's a unit conversion issue → add conversion logic
- If it's pool switching → add pool consistency checks
- If it's bad API data → add better validation or switch data source
- If it's real volatility → adjust threshold or validation logic

---

## Current Impact

- **Data gaps**: Bars with extreme jumps are being skipped
- **Potential data quality issues**: If this is unit mismatch, all stored prices might be wrong
- **Systemic issue**: Affecting "almost every token" suggests a fundamental problem

**Priority**: HIGH - This affects data quality for all tokens

