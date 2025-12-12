# Rollup Logging Improvement Plan

## Current Problems

### 1. **"No OHLC bars created" - No Context**
**Current log:**
```
2025-12-10 20:05:31,323 - rollup - INFO - No OHLC bars created for 15m rollup
```

**Problems:**
- ❌ Doesn't say which tokens were checked
- ❌ Doesn't say how many 1m bars were found
- ❌ Doesn't say why bars weren't created (insufficient data? validation failed? already exists?)
- ❌ Doesn't show data coverage per token
- ❌ Can't trace back to see what went wrong

**What we need:**
- ✅ List of tokens checked
- ✅ Per-token: how many 1m bars found vs required
- ✅ Per-token: why bar wasn't created (insufficient data, validation failed, already exists)
- ✅ Data coverage percentage per token
- ✅ Timestamp range of 1m data found

### 2. **"Not enough 1m bars" - No Token Details**
**Current log:**
```
2025-12-10 19:50:14,394 - rollup - WARNING - Not enough 1m bars for lowcaps 5m rollup at 2025-12-10 18:50:00+00:00: have 2, need at least 4 (required: 5)
```

**Problems:**
- ❌ Doesn't say which tokens
- ❌ Doesn't show per-token breakdown
- ❌ Doesn't show when 1m data was last collected
- ❌ Doesn't show gap between 1m data and rollup boundary

**What we need:**
- ✅ Per-token breakdown: token, bars found, bars required, coverage %
- ✅ Latest 1m data timestamp per token
- ✅ Gap between latest 1m data and rollup boundary
- ✅ Which tokens are missing data

### 3. **No Visibility into Raw 1m Data Collection**
**Current state:**
- No logging about what 1m data is coming in
- No visibility into price collector activity
- Can't see if 1m data collection is working

**What we need:**
- ✅ Summary of 1m data collected in last period
- ✅ Per-token: latest 1m data timestamp
- ✅ Gap analysis: 1m data vs rollup data
- ✅ Tokens with stale 1m data

### 4. **"Rolled up X bars" - No Per-Token Details**
**Current log:**
```
2025-12-10 20:05:14,062 - rollup - INFO - Rolled up 20 lowcaps 15m bars at 2025-12-10 18:45:00+00:00 (skipped 0 existing) - tokens: 0xFAC77f01957ed1B3DD1cbEa992199B8f85B6E886/base, ... (+10 more)
```

**Problems:**
- ❌ Only shows first 10 tokens
- ❌ Doesn't show per-token: bars found, coverage, why skipped
- ❌ Doesn't show which tokens were successfully rolled up

**What we need:**
- ✅ Complete list of tokens processed
- ✅ Per-token: bars found, coverage %, created/skipped
- ✅ Summary: X tokens created, Y tokens skipped (with reasons)

### 5. **No Data Health Metrics**
**Current state:**
- No summary of data health
- Can't see overall system status
- Can't identify systemic issues

**What we need:**
- ✅ Summary: total tokens, tokens with data, tokens without data
- ✅ Coverage metrics: average coverage %, tokens below threshold
- ✅ Gap analysis: 1m data lag, rollup lag
- ✅ Health status: healthy/warning/critical

## Improvement Plan

### Phase 1: Enhanced Per-Token Logging

#### 1.1 Log Token Processing Details
**Location:** `_convert_to_ohlc()` method

**Add logging for:**
- Token being processed
- 1m bars found for that token
- Required bars for timeframe
- Coverage percentage
- Why bar was created/skipped

**Example log:**
```
2025-12-10 20:05:31,323 - rollup - INFO - Processing 15m rollup for 0xFAC77f01957ed1B3DD1cbEa992199B8f85B6E886/base at 2025-12-10 18:45:00+00:00: found 12/15 1m bars (80.0% coverage) - CREATED
2025-12-10 20:05:31,324 - rollup - INFO - Processing 15m rollup for 0xOTHER/chain at 2025-12-10 18:45:00+00:00: found 7/15 1m bars (46.7% coverage) - SKIPPED (insufficient data, need 12)
```

#### 1.2 Log Data Query Results
**Location:** `_get_lowcap_1m_data()` method

**Add logging for:**
- Total 1m bars found in query
- Per-token breakdown of bars found
- Timestamp range of data found
- Tokens with no data

**Example log:**
```
2025-12-10 20:05:31,323 - rollup - INFO - Querying 1m OHLC data for 15m rollup at 2025-12-10 18:45:00+00:00 (window: 2025-12-10 18:15:00+00:00 to 2025-12-10 18:45:00+00:00)
2025-12-10 20:05:31,325 - rollup - INFO - Found 1m data: 450 bars across 30 tokens (15:00-18:45)
2025-12-10 20:05:31,326 - rollup - INFO - Tokens with data: 0xFAC77f01957ed1B3DD1cbEa992199B8f85B6E886/base (15 bars), 0xOTHER/chain (12 bars), ...
2025-12-10 20:05:31,327 - rollup - WARNING - Tokens with no 1m data: 0xMISSING/chain, 0xMISSING2/chain
```

### Phase 2: Summary Logging

#### 2.1 Rollup Summary
**Location:** `rollup_timeframe()` method

**Add summary at end of rollup:**
- Total tokens checked
- Tokens with bars created
- Tokens skipped (with reasons)
- Tokens with insufficient data
- Overall coverage metrics

**Example log:**
```
2025-12-10 20:05:31,500 - rollup - INFO - 15m rollup summary at 2025-12-10 18:45:00+00:00:
  - Tokens checked: 30
  - Bars created: 20 tokens
  - Skipped (already exists): 5 tokens
  - Skipped (insufficient data): 5 tokens (avg coverage: 45.2%)
  - Overall coverage: 83.3% (25/30 tokens processed)
```

#### 2.2 Data Health Summary
**Location:** New method `_log_data_health_summary()`

**Add periodic health check:**
- Latest 1m data timestamp
- Latest rollup timestamp per timeframe
- Gap between 1m data and rollups
- Tokens with stale data

**Example log:**
```
2025-12-10 20:05:31,500 - rollup - INFO - Data health summary:
  - Latest 1m data: 2025-12-10 20:04:00+00:00 (1 minute ago)
  - Latest 15m rollup: 2025-12-10 18:45:00+00:00 (80 minutes ago) ⚠️
  - Gap: 79 minutes
  - Tokens with stale 1m data (>5 min): 3 tokens
  - Tokens with stale 15m rollup (>30 min): 5 tokens
```

### Phase 3: Raw 1m Data Visibility

#### 3.1 1m Data Collection Summary
**Location:** Price collector (if we have access) or new rollup method

**Add logging for:**
- 1m data points collected in last period
- Per-token: latest 1m data timestamp
- Tokens with missing 1m data

**Example log:**
```
2025-12-10 20:05:31,500 - rollup - INFO - 1m data collection summary (last 15 minutes):
  - Total 1m points collected: 450
  - Tokens with data: 30
  - Tokens without data: 5
  - Latest data: 2025-12-10 20:04:00+00:00
  - Stale tokens (>5 min): 0xFAC77f01957ed1B3DD1cbEa992199B8f85B6E886/base (last: 2025-12-10 19:55:00+00:00)
```

#### 3.2 Gap Analysis
**Location:** New method `_analyze_data_gaps()`

**Add gap analysis:**
- Gap between 1m data and rollup boundaries
- Tokens with large gaps
- Missing boundaries

**Example log:**
```
2025-12-10 20:05:31,500 - rollup - INFO - Gap analysis for 15m rollup:
  - 1m data available up to: 2025-12-10 20:04:00+00:00
  - Rollup boundaries missing: 19:00, 19:15, 19:30, 19:45, 20:00
  - Tokens with gaps: 0xFAC77f01957ed1B3DD1cbEa992199B8f85B6E886/base (missing 5 boundaries)
```

### Phase 4: Error Context

#### 4.1 Enhanced Error Logging
**Location:** All error paths

**Add context to errors:**
- What operation was being performed
- Which token/timeframe
- What data was available
- What was expected

**Example log:**
```
2025-12-10 20:05:31,500 - rollup - ERROR - Failed to create 15m bar for 0xFAC77f01957ed1B3DD1cbEa992199B8f85B6E886/base at 2025-12-10 18:45:00+00:00:
  - Operation: rollup_timeframe
  - 1m bars found: 7
  - Required: 12 (80% of 15)
  - Coverage: 46.7%
  - Reason: insufficient data
  - Latest 1m data: 2025-12-10 18:42:00+00:00 (3 minutes before boundary)
```

## Implementation Priority

1. **High Priority (Do First):**
   - Phase 1.1: Per-token processing details
   - Phase 1.2: Data query results
   - Phase 2.1: Rollup summary

2. **Medium Priority:**
   - Phase 2.2: Data health summary
   - Phase 3.2: Gap analysis

3. **Low Priority:**
   - Phase 3.1: 1m data collection summary (if price collector logging is separate)
   - Phase 4.1: Enhanced error logging (as needed)

## Expected Outcome

After improvements, logs should clearly show:
1. ✅ Which tokens are being processed
2. ✅ Per-token: data found, coverage, why created/skipped
3. ✅ Summary of rollup results
4. ✅ Data health metrics
5. ✅ Gap analysis between 1m data and rollups
6. ✅ Easy traceback to root cause of issues

## Example: Before vs After

### Before:
```
2025-12-10 20:05:31,323 - rollup - INFO - No OHLC bars created for 15m rollup
```

### After:
```
2025-12-10 20:05:31,323 - rollup - INFO - Querying 1m OHLC data for 15m rollup at 2025-12-10 18:45:00+00:00 (window: 2025-12-10 18:15:00+00:00 to 2025-12-10 18:45:00+00:00)
2025-12-10 20:05:31,325 - rollup - INFO - Found 1m data: 450 bars across 30 tokens
2025-12-10 20:05:31,326 - rollup - INFO - Processing 15m rollup for 0xFAC77f01957ed1B3DD1cbEa992199B8f85B6E886/base at 2025-12-10 18:45:00+00:00: found 12/15 1m bars (80.0% coverage) - CREATED
2025-12-10 20:05:31,327 - rollup - INFO - Processing 15m rollup for 0xOTHER/chain at 2025-12-10 18:45:00+00:00: found 7/15 1m bars (46.7% coverage) - SKIPPED (insufficient data, need 12)
...
2025-12-10 20:05:31,500 - rollup - INFO - 15m rollup summary at 2025-12-10 18:45:00+00:00:
  - Tokens checked: 30
  - Bars created: 20 tokens
  - Skipped (already exists): 5 tokens
  - Skipped (insufficient data): 5 tokens (avg coverage: 45.2%)
  - Overall coverage: 83.3% (25/30 tokens processed)
```

