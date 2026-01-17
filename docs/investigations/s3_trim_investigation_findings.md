# S3 Trim Investigation Findings

**Date**: 2026-01-10  
**Investigator**: Auto (AI Assistant)  
**Status**: Root Cause Identified

---

## Executive Summary

**Problem**: S3 trims are not working - no trim_flags are being set.

**Root Cause**: **OX scores are not being stored in the uptrend_engine_v4 payload**. All 23 S3 positions have empty scores dictionaries (`scores: {}`), which means `ox_score` is always 0.0, preventing trim_flag from ever being set.

---

## Investigation Results

### Database Query Results

- **Total S3 positions**: 23
- **Positions with trim_flag=True**: 0
- **Positions with OX >= 0.65**: 0
- **Positions with no SR levels**: 1
- **Positions with invalid ATR**: 5

### Key Findings

1. **All S3 positions have empty scores dictionaries**
   - `scores: {}` (no keys)
   - `ox_score: 0.0000` for all positions
   - `scores` key is missing from uptrend payload keys

2. **Uptrend engine payload structure** (from sample positions):
   ```
   uptrend_keys: ['ts', 'ema', 'meta', 'chain', 'price', 'state', 'prev_state', 'diagnostics', 'token_contract', ...]
   ```
   - **Missing**: `scores`, `trim_flag`, `buy_flag`, etc.

3. **Recent update timestamps**:
   - Some positions updated recently (e.g., PAYAI: 2026-01-09)
   - Even recently updated positions lack scores
   - This suggests scores are not being included in the payload

4. **SR Levels and ATR**:
   - Most positions (22/23) have SR levels
   - 5 positions have invalid ATR (ATR = 0.0)
   - Some positions are near SR levels but can't trim because OX = 0

---

## Code Analysis

### Expected Behavior

In `uptrend_engine_v4.py` (lines 2008-2021), when processing S3 state:

```python
extra_data = {
    "trim_flag": trim_flag,
    "buy_flag": dx_buy_ok,
    "first_dip_buy_flag": first_dip_buy_flag,
    "emergency_exit": emergency_exit,
    "reclaimed_ema333": reclaimed_ema333,
    "scores": {
        "ox": ox,
        "dx": dx,
        "edx": edx,
        "ts": ts_score,
        "ts_with_boost": ts_with_boost,
        "sr_boost": sr_boost,
    },
    ...
}
```

This `extra_data` should be merged into the payload via `**extra` in `_build_payload()`.

### Actual Behavior

The payload stored in the database does NOT contain:
- `scores` dictionary
- `trim_flag`
- `buy_flag`
- Other flags from `extra_data`

### Possible Causes

1. **Exception in `_compute_s3_scores()`**: If this throws an exception, scores might default to empty dict
2. **Payload overwrite**: Something might be overwriting the payload after it's created
3. **Payload not being saved**: The `_write_features()` call might not be persisting the scores
4. **Code path not executing**: The S3 "stay in S3" code path might not be executing

---

## Next Steps for Investigation

1. **Check logs for exceptions**:
   - Look for errors in `_compute_s3_scores()`
   - Check for exceptions during payload building
   - Verify `_write_features()` is being called

2. **Verify code execution path**:
   - Add logging to confirm S3 "stay in S3" path is executing
   - Verify `extra_data` is being created with scores
   - Check if `_build_payload()` is receiving `extra_data`

3. **Check for payload overwrites**:
   - Look for other code that modifies `features["uptrend_engine_v4"]`
   - Check if PM Core Tick or other jobs overwrite the payload

4. **Test with a single position**:
   - Manually trigger uptrend engine for one S3 position
   - Check logs to see if scores are computed
   - Verify payload before and after save

---

## Sample Position Analysis

### PAYAI/solana tf=15m (Most Recent Update)

```
State: S3
Trim Flag: False
OX Score: 0.0000 (should be calculated)
Scores keys: [] (EMPTY!)
Uptrend TS: 2026-01-09T05:31:10 (yesterday)
Price: 0.01437000
Quantity: 18.496042 (has tokens)
ATR: 0.00042922 (valid)
SR Levels: 12 (has levels)
Near SR: True (within SR halo!)
Closest SR: 0.01416267 (distance: 0.00020733 < SR halo: 0.00042922)
Last Trim TS: Never
```

**This position should have trim_flag=True if OX >= 0.65**, but:
- OX is 0.0 (not calculated)
- trim_flag is False
- Scores dictionary is empty

---

## Conclusion

The S3 trim system is not working because **OX scores are not being stored in the database**. The uptrend engine code appears correct (scores should be included in `extra_data`), but the payloads in the database are missing the `scores` key entirely.

This suggests either:
1. An exception is preventing scores from being computed/stored
2. The payload is being overwritten after creation
3. The code path that includes scores is not executing

**Recommended Action**: Check application logs for exceptions during uptrend engine execution, particularly around `_compute_s3_scores()` and payload building.

