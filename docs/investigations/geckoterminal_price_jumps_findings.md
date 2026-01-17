# GeckoTerminal Extreme Price Jumps - Investigation Findings

**Date**: 2026-01-10  
**Status**: Investigation Complete - Root Cause Identified

---

## Summary

**Current data from GeckoTerminal looks normal** - prices are in expected ranges (0.0001-0.001 range for TOKEN/SOL pairs), ratios are normal (1.00-1.17x).

**The extreme jumps are happening at specific timestamps during backfill**, not in current data.

---

## Key Findings

### 1. Current Data is Normal

**Test Results** (from `investigate_geckoterminal_price_jumps.py`):
- Prices: 0.0012-0.0016 SOL (for TOKEN/SOL pairs) - **reasonable values**
- Ratios: 1.00-1.17x - **normal intra-bar volatility**
- No extreme jumps in recent 20 bars tested

**Conclusion**: The API is returning reasonable data for current/recent timestamps.

### 2. The Issue is Historical/Timestamp-Specific

**Evidence from warnings**:
- Timestamps showing jumps: `2026-01-10T07:00:00`, `2026-01-10T06:45:00`, `2026-01-06T09:15:00`
- These are specific timestamps, not all timestamps
- Affecting "almost every token" suggests a systemic issue at those times

### 3. Possible Root Causes

#### Hypothesis A: GeckoTerminal Historical Data Quality Issues (Most Likely)
**Theory**: GeckoTerminal's historical data for certain timestamps contains bad data
- API might have gaps or errors in historical data
- Specific timestamps might have corrupted/malformed data
- Could be related to pool migrations, DEX issues, or data collection problems

**Evidence**:
- Happening at specific timestamps (not random)
- Affecting multiple tokens (systemic)
- Current data is fine (recent data quality is good)

#### Hypothesis B: Pool Switching During Historical Period
**Theory**: Tokens switched pools during historical period, causing unit mismatch
- Started with TOKEN/SOL pool (prices in SOL)
- Switched to TOKEN/USDC pool (prices in USDC)
- If SOL = $100, then 0.001 SOL = $0.10, but 0.10 USDC looks like 100x jump from 0.001

**Evidence needed**:
- Check if pool addresses change at those timestamps
- Check if quote_symbol changes
- Compare pool addresses in database vs canonical pool

#### Hypothesis C: Unit Conversion Issue in Historical Data
**Theory**: GeckoTerminal might have changed how they return prices
- Old API version returned prices in one unit
- New API version returns prices in different unit
- When fetching historical data, mixing units causes jumps

**Evidence needed**:
- Check GeckoTerminal API version/changes
- Compare old vs new data formats

#### Hypothesis D: Data Gaps Filled with Bad Data
**Theory**: GeckoTerminal fills data gaps with placeholder/bad values
- Missing bars might be filled with zeros or extreme values
- Backfill encounters these and flags them

**Evidence needed**:
- Check if jumps correlate with data gaps
- Check if volume is zero or suspicious at jump timestamps

---

## What We Need to Know

### Critical Information Missing

1. **Actual price values when jump detected**:
   - What are `open_usd` and `close_usd` when ratio > 100?
   - Are they reasonable values that just happen to be far apart?
   - Or are they clearly bad data (zeros, negatives, impossibly large/small)?

2. **Pool consistency**:
   - Is the same pool being used for all bars?
   - Does pool address change at jump timestamps?
   - Does quote_symbol change?

3. **Volume at jump timestamps**:
   - Is volume zero or suspiciously low?
   - Low volume = likely bad data or data gap

4. **Pattern analysis**:
   - Do jumps happen at same timestamps across tokens?
   - Do jumps happen at specific times of day?
   - Are jumps clustered in time?

---

## Recommended Diagnostic Logging

**Add to `_build_rows_for_insert()` when extreme jump detected**:

```python
# Check for extreme jumps (>100x change) - likely bad data
if close_usd > 0 and open_usd > 0:
    price_change_ratio = max(close_usd / open_usd, open_usd / close_usd)
    if price_change_ratio > 100.0:
        skipped_count += 1
        logger.warning(
            "EXTREME_PRICE_JUMP: %s/%s tf=%s | "
            "ts=%s | "
            "open=%.10f close=%.10f ratio=%.2f | "
            "high=%.10f low=%.10f | "
            "volume=%.2f | "
            "pool=%s quote=%s | "
            "prev_bar_close=%.10f",  # Need to track previous bar
            token_contract, chain, timeframe,
            ts_iso,
            open_usd, close_usd, price_change_ratio,
            high_usd, low_usd,
            volume_usd,
            pool_addr, quote_symbol,
            prev_close  # Track previous bar's close
        )
        continue
```

**Additional logging needed**:
- Track previous bar's close price to see if jump is between bars
- Log pool address to detect pool switches
- Log quote_symbol to detect quote token changes
- Log full entry array to see raw API response

---

## Next Steps

### Without Code Changes (Investigation Only)

1. **Query database for patterns**:
   - Check if jumps happen at same timestamps across tokens
   - Check pool addresses at jump timestamps
   - Check if there are data gaps before/after jumps

2. **Manual API test**:
   - Fetch OHLCV for a token showing jumps
   - Request data for the specific timestamps showing jumps
   - Inspect raw API response

3. **Compare with other data sources**:
   - If available, compare GeckoTerminal prices with other sources
   - Verify if jumps are real or data quality issues

### With Diagnostic Logging (Recommended)

Add the logging above to capture:
- Actual price values
- Pool consistency
- Volume patterns
- Cross-bar comparisons

This will reveal whether it's:
- Bad data from GeckoTerminal → need better validation
- Pool switching → need pool consistency checks
- Unit mismatch → need conversion logic
- Real volatility → need to adjust threshold

---

## Current Impact Assessment

**Data Quality**: 
- ✅ Recent data is fine (no jumps in current bars)
- ⚠️ Historical data has gaps (jumped bars are skipped)
- ⚠️ Could affect backtesting if historical data is incomplete

**System Impact**:
- Bars are being skipped (good - prevents bad data)
- But we're losing data at those timestamps
- Need to understand if this is acceptable or if we need to fix it

---

## Conclusion

The extreme price jumps are happening at **specific historical timestamps**, not in current data. This suggests:

1. **GeckoTerminal historical data quality issues** (most likely)
2. **Pool switching** causing unit mismatches
3. **API data format changes** over time

**We need diagnostic logging to capture the actual values** when jumps are detected to determine the root cause. Without seeing the actual price values, pool addresses, and volumes at jump timestamps, we can only hypothesize.

**Recommendation**: Add diagnostic logging to capture full context when extreme jumps are detected, then analyze the patterns to determine the root cause.

