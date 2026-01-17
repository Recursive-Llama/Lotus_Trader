# S3 Trim Investigation - Next Steps

**Date**: 2026-01-10  
**Status**: Root Cause Identified - Action Plan

---

## Problem Summary

OX scores are not being stored in `uptrend_engine_v4` payload, causing all `trim_flag` values to be False (since `ox >= 0.65` can never be true when `ox = 0.0`).

---

## Action Plan

### Step 1: Add Diagnostic Logging (Investigation)

Add targeted logging to trace where scores are being lost:

**Location**: `src/intelligence/lowcap_portfolio_manager/jobs/uptrend_engine_v4.py`

**Add logging at these key points**:

1. **After `_compute_s3_scores()`** (line ~1866):
   ```python
   s3_scores = self._compute_s3_scores(contract, chain, price, ema_vals, ta, features)
   logger.info("S3_SCORES_COMPUTED: %s/%s tf=%s | scores=%s", 
               contract, chain, self.timeframe, s3_scores)
   ```

2. **After `extra_data` creation** (line ~2048):
   ```python
   logger.info("S3_EXTRA_DATA: %s/%s tf=%s | has_scores=%s scores_keys=%s", 
               contract, chain, self.timeframe, 
               "scores" in extra_data, 
               list(extra_data.get("scores", {}).keys()) if "scores" in extra_data else [])
   ```

3. **After `_build_payload()`** (line ~2074):
   ```python
   payload = self._build_payload(...)
   logger.info("S3_PAYLOAD_BUILT: %s/%s tf=%s | has_scores=%s scores_keys=%s", 
               contract, chain, self.timeframe,
               "scores" in payload,
               list(payload.get("scores", {}).keys()) if "scores" in payload else [])
   ```

4. **Before `_write_features()`** (line ~2075):
   ```python
   features["uptrend_engine_v4"] = payload
   logger.info("S3_BEFORE_WRITE: %s/%s tf=%s | payload_has_scores=%s", 
               contract, chain, self.timeframe,
               "scores" in features["uptrend_engine_v4"])
   ```

5. **After `_write_features()`** (line ~2076):
   ```python
   self._write_features(pid, features)
   # Verify what was written
   written = self.sb.table("lowcap_positions").select("features").eq("id", pid).limit(1).execute().data
   if written:
       written_uptrend = written[0].get("features", {}).get("uptrend_engine_v4", {})
       logger.info("S3_AFTER_WRITE: %s/%s tf=%s | written_has_scores=%s scores_keys=%s", 
                   contract, chain, self.timeframe,
                   "scores" in written_uptrend,
                   list(written_uptrend.get("scores", {}).keys()) if "scores" in written_uptrend else [])
   ```

### Step 2: Check Application Logs

**Look for**:
- Exceptions in `_compute_s3_scores()`
- Exceptions during payload building
- Any warnings about `extra_data` being a tuple or wrong type
- Errors during `_write_features()`

**Command to check recent logs**:
```bash
# Check for S3-related errors in uptrend engine
grep -i "s3.*error\|uptrend_engine.*error\|_compute_s3_scores" /path/to/logs

# Check for exceptions
grep -i "exception\|traceback" /path/to/logs | grep -i "s3\|uptrend"
```

### Step 3: Verify Code Path Execution

**Check if the S3 "stay in S3" path is executing**:

1. Look for log message: `"S3 processing: %s/%s (timeframe=%s, bars_since_s3=%s...)"`
2. If this log doesn't appear, the code path isn't executing
3. If it appears but scores are still missing, the issue is in score computation or payload building

### Step 4: Test with Single Position

**Manual test procedure**:

1. Pick one S3 position (e.g., PAYAI/solana tf=15m)
2. Manually trigger uptrend engine for that position
3. Check logs for the diagnostic messages above
4. Query database immediately after to verify scores were written

**Query to verify**:
```sql
SELECT 
    id,
    token_ticker,
    token_chain,
    timeframe,
    features->'uptrend_engine_v4'->'scores' as scores,
    features->'uptrend_engine_v4'->'trim_flag' as trim_flag,
    features->'uptrend_engine_v4'->'ts' as updated_ts
FROM lowcap_positions
WHERE token_ticker = 'PAYAI' 
  AND token_chain = 'solana'
  AND timeframe = '15m';
```

### Step 5: Check for Payload Overwrites

**Search for code that modifies `uptrend_engine_v4` after creation**:

```bash
grep -r "uptrend_engine_v4.*=" src/ --exclude-dir=__pycache__
grep -r "features\[.*uptrend_engine_v4" src/ --exclude-dir=__pycache__
```

**Known locations to check**:
- PM Core Tick (might overwrite during processing)
- Other jobs that update features
- Any code that does partial updates to features

---

## Expected Outcomes

### If scores are computed but not in payload:
- Issue is in `_build_payload()` or `**extra` merge
- Check if `extra_data` is being passed correctly

### If scores are in payload but not in database:
- Issue is in `_write_features()` or database write
- Check for exceptions during write
- Verify database constraints/permissions

### If scores are never computed:
- Issue is in `_compute_s3_scores()`
- Check for exceptions
- Verify TA data is available
- Check if function is being called

### If code path isn't executing:
- Positions might be transitioning states instead of staying in S3
- Check state transition logic
- Verify positions are actually in S3 state

---

## Quick Win: Check Exception Logs First

Before adding logging, check if there are already exceptions in the logs:

```bash
# If using Python logging
tail -n 1000 /path/to/app.log | grep -i "exception\|error" | grep -i "s3\|uptrend\|_compute_s3"

# If logs are in database
# Query error logs table if it exists
```

This might immediately reveal the issue without needing to add diagnostic logging.

---

## Priority Order

1. **Check existing logs** (5 minutes) - might reveal the issue immediately
2. **Add diagnostic logging** (15 minutes) - if logs don't show the issue
3. **Run uptrend engine manually** (10 minutes) - test with one position
4. **Verify database writes** (5 minutes) - confirm what's actually stored
5. **Check for overwrites** (10 minutes) - if scores are written but then lost

Total estimated time: 45 minutes to 1 hour to identify the exact failure point.

