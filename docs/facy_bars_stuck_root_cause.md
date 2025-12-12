# Root Cause: Why FACY's Bars Were Stuck at 0

## Summary (CORRECTED)

**FACY's `bars_since_s3` was stuck at 0 for 35+ minutes because:**
1. **Bars exist in database NOW**: FACY has 15m bars at 16:30, 17:45, 18:00, 18:15 ✅
2. **Bars were created at CORRECT scheduled times**: 
   - 17:45:00 bar created at 18:45:04 (scheduled rollup at :45) ✅
   - 18:00:00 bar created at 19:00:03 (scheduled rollup at :00) ✅
3. **Engine was running standalone BEFORE bars were created**: Engine ran at 18:21, 18:25, 18:30, 18:33 - all BEFORE 17:45:00 bar was created at 18:45:04
4. **Engine checked for bars that didn't exist yet**: Engine's `_latest_close_1h()` query returned 16:30:00 (latest bar at that time)
5. **This is a TIMING/COORDINATION issue**: Engine shouldn't run standalone, or should understand bars might not exist yet

---

## Timeline (CORRECTED)

| Time | Event | Status |
|------|-------|--------|
| 16:30:00 | FACY entered S3 | ✅ |
| 16:30:00 | Latest 15m bar exists (geckoterminal backfill) | ✅ |
| 18:21:14 | **Engine runs standalone** | ⚠️ Checks for 17:45:00 bar - doesn't exist yet |
| 18:25:59 | **Engine runs standalone** | ⚠️ Checks for 17:45:00 bar - doesn't exist yet |
| 18:30:05 | **Engine runs standalone** | ⚠️ Checks for 17:45:00 bar - doesn't exist yet |
| 18:33:41 | **Engine runs standalone** | ⚠️ Checks for 17:45:00 bar - doesn't exist yet |
| 18:45:04 | **Scheduled rollup creates 17:45:00 bar** | ✅ Created at correct time |
| 19:00:03 | **Scheduled rollup creates 18:00:00 bar** | ✅ Created at correct time |
| 19:00:05 | **Engine runs in scheduled pipeline** | ✅ Finally sees 17:45:00 bar, `bars_since_s3=5` |
| 19:15:00 | **Scheduled rollup creates 18:15:00 bar** | ✅ Created at correct time |

---

## Why Bars Were "Stuck" (CORRECTED)

### The Real Issue: Timing Mismatch

**Bars exist in database NOW**:
- 16:30:00 (geckoterminal backfill) ✅
- 17:45:00 (rollup - created at 18:45:04) ✅
- 18:00:00 (rollup - created at 19:00:03) ✅
- 18:15:00 (rollup - created at 19:15:00) ✅

**Scheduled Rollup Timing**:
- Rollup runs at :00, :15, :30, :45 (aligned to boundaries)
- 17:45:00 bar created at 18:45:04 ✅ (correct timing)
- 18:00:00 bar created at 19:00:03 ✅ (correct timing)

**The Problem**:
- Engine was running **standalone** at 18:21, 18:25, 18:30, 18:33
- These runs happened **BEFORE** scheduled rollup created 17:45:00 bar (18:45:04)
- Engine's `_latest_close_1h()` query returned 16:30:00 (latest bar at that time)
- Engine finally saw 17:45:00 bar at 19:00:05 (in scheduled pipeline)

**This is NOT a rollup issue - it's a timing/coordination issue!**

---

## Why Bars Were Stuck

### Engine Logic

```python
# From uptrend_engine_v4.py:1427-1429
last = self._latest_close_1h(contract, chain)
current_ts = last.get("ts")  # Gets latest 15m bar timestamp

# From uptrend_engine_v4.py:1844
bars_since = self._calculate_bars_since_s3_entry(s3_start_ts, current_ts, self.timeframe)
```

**What Happened**:
1. FACY entered S3 at 16:30:00 (latest 15m bar = 16:30:00)
2. Rollup tried to create 16:45, 17:00, 17:15, 17:30 bars → **all skipped** (insufficient 1m data)
3. Engine kept reading `current_ts = 16:30:00` (no new bars created)
4. `bars_since_s3` = `(16:30:00 - 16:30:00) / 15 minutes` = **0 bars**
5. Stuck for 35+ minutes until 17:45:00 bar was created (catch-up at 19:02)

---

## Why Catch-Up Didn't Help Earlier

**Catch-up runs hourly at :02** (19:02, 20:02, etc.)

**At 19:02 catch-up**:
- Tried to roll up 16:30, 16:45, 17:00, 17:15, 17:30 boundaries
- **Still skipped FACY** because 1m data was still insufficient
- Only created 17:45:00 bar (which had enough 1m data)

**Why 17:45:00 bar was created**:
- Likely had sufficient 1m data (12+ bars) by the time catch-up ran
- Or catch-up logic is more lenient for recent boundaries

---

## Root Cause: Engine Running Standalone Before Scheduled Rollup

**The real issue is timing/coordination, not data collection.**

**What happened**:
1. Scheduled rollup creates bars at :00, :15, :30, :45 (aligned to boundaries)
2. Engine was running standalone at 18:21, 18:25, 18:30, 18:33 (NOT scheduled times)
3. These standalone runs checked for 17:45:00 bar BEFORE it was created (18:45:04)
4. Engine's query returned 16:30:00 (latest bar at that time)
5. Engine finally saw 17:45:00 bar at 19:00:05 (in scheduled pipeline)

**Why engine runs standalone**:
- Decision Maker triggers engine immediately when position created (line 909-926)
- These standalone runs check data BEFORE scheduled rollup creates it
- Engine should only run in scheduled pipeline (TA→Uptrend→PM)

**This is a timing/coordination issue, not a data collection issue.**

---

## Why Logs Don't Show Skip Messages

**The skip messages should be at INFO level** (we changed from DEBUG to INFO), but they might not be visible because:

1. **Log rotation**: Logs rotate at 10MB, older skip messages may have been rotated out
2. **Message format**: Skip messages include `token_contract/chain`, but grep might not match if contract is long
3. **Timing**: Skip messages are logged during rollup, but may be in different log files or rotated

**The skip messages should look like**:
```
Skipping 15m bar at 2025-12-10T16:45:00+00:00 for 0xFAC77f01957ed1B3DD1cbEa992199B8f85B6E886/base: only 1 1m bars (need at least 12 for 15min timeframe)
```

---

## Conclusion (CORRECTED)

**FACY's bars were stuck because:**
1. ✅ **Bars exist in database** - 16:30, 17:45, 18:00, 18:15 all exist
2. ✅ **Rollup created bars at correct times** - 17:45:00 at 18:45:04 (scheduled)
3. ❌ **Engine was running standalone** - at 18:21, 18:25, 18:30, 18:33 (NOT scheduled)
4. ❌ **Engine checked BEFORE bars were created** - 17:45:00 bar created at 18:45:04, but engine ran at 18:21-18:33
5. ⚠️ **Engine correctly read latest bar** - but it was 16:30:00 because 17:45:00 didn't exist yet

**This is a timing/coordination issue, not a data collection or rollup issue.**

**Next steps**:
1. Investigate why engine runs standalone (Decision Maker trigger? 1m pipeline?)
2. Ensure engine only runs in scheduled pipeline (TA→Uptrend→PM)
3. Or have engine understand that bars might not exist yet if running standalone
4. Consider immediate PM Core trigger when engine sets flags (to avoid timing gaps)

