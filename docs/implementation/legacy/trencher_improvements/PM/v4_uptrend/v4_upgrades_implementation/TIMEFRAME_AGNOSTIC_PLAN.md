# Timeframe-Agnostic System Implementation Plan

## Overview

Make the uptrend engine system work with multiple timeframes (1m, 5m, 15m, 1h) based on token age, while maintaining the same number of bars (~336) for consistent analysis.

## Current State

- **Hardcoded to 1h timeframe**: All queries, calculations, and storage use `timeframe='1h'`
- **Requires 14 days of data**: System needs ~336 hourly bars to function properly
- **Cannot handle new tokens**: Tokens < 14 days old fail due to insufficient data

## API Verification ✅

**Status**: All GeckoTerminal API endpoints tested and verified working (2025-01-30)

Test script: `scripts/test_geckoterminal_timeframes.py`

**Verified endpoints**:
- ✅ `/ohlcv/minute?aggregate=1` → 1m bars
- ✅ `/ohlcv/minute?aggregate=5` → 5m bars
- ✅ `/ohlcv/minute?aggregate=15` → 15m bars
- ✅ `/ohlcv/hour?aggregate=1` → 1h bars (current)
- ✅ `/ohlcv/hour?aggregate=4` → 4h bars
- ✅ `/ohlcv/hour?aggregate=12` → 12h bars
- ✅ `/ohlcv/day` → 1d bars

All endpoints return data successfully. Ready for implementation.

## Goal

Enable backtesting and analysis on tokens of any age by selecting appropriate timeframes:

| Token Age | Timeframe | Bars Available | Meets Requirement? |
|-----------|-----------|----------------|---------------------|
| 1 day     | 1m        | 1,440          | ✅ Yes              |
| 3 days    | 5m        | 864            | ✅ Yes              |
| 7 days    | 15m       | 672            | ✅ Yes              |
| 14+ days  | 1h        | 336+           | ✅ Current          |

**Target**: Always ensure ~336 bars minimum for analysis.

## Implementation Plan

### Phase 1: Timeframe Selection Logic

**File**: `backtester/v4/code/run_backtest.py` (or new utility module)

**Function**: `get_timeframe_for_token_age(days_old: int) -> str`

```python
def get_timeframe_for_token_age(days_old: int) -> str:
    """
    Select appropriate timeframe based on token age to ensure ~336 bars.
    
    Returns:
        '1m', '5m', '15m', or '1h'
    """
    if days_old >= 14:
        return '1h'   # 336+ bars available
    elif days_old >= 7:
        return '15m'  # 672 bars at 7 days
    elif days_old >= 3:
        return '5m'   # 864 bars at 3 days
    else:
        return '1m'   # 1,440 bars at 1 day
```

**Function**: `get_seconds_per_bar(timeframe: str) -> int`

```python
def get_seconds_per_bar(timeframe: str) -> int:
    """Convert timeframe string to seconds per bar."""
    return {
        '1m': 60,
        '5m': 300,
        '15m': 900,
        '1h': 3600,
    }[timeframe]
```

---

### Phase 2: Backfill Updates

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/geckoterminal_backfill.py`

**Changes**:

1. **Add timeframe parameter to `backfill_token_1h()`**:
   - Rename to `backfill_token_ohlc(contract, chain, timeframe, lookback_minutes)`
   - Or keep name and add optional `timeframe` param (defaults to '1h' for backward compat)

2. **Update `_fetch_gt_ohlcv_by_pool()`**:
   - Currently hardcoded: `/ohlcv/hour?limit=...`
   - Change to dynamic endpoint based on timeframe:
     - **1m**: `/ohlcv/minute?aggregate=1&limit=...`
     - **5m**: `/ohlcv/minute?aggregate=5&limit=...`
     - **15m**: `/ohlcv/minute?aggregate=15&limit=...`
     - **1h**: `/ohlcv/hour?aggregate=1&limit=...` (current)
     - **4h**: `/ohlcv/hour?aggregate=4&limit=...`
     - **12h**: `/ohlcv/hour?aggregate=12&limit=...`
     - **1d**: `/ohlcv/day?limit=...`
   - ✅ **Verified**: All endpoints tested and working (see `scripts/test_geckoterminal_timeframes.py`)

3. **Update storage**:
   - Currently writes `timeframe='1h'` (hardcoded)
   - Change to use provided `timeframe` parameter

**Example**:
```python
def backfill_token_ohlc(contract: str, chain: str, timeframe: str = '1h', lookback_minutes: int = None):
    # Map timeframe to GeckoTerminal interval
    gt_interval = {
        '1m': 'minute',
        '5m': 'minute',
        '15m': 'minute',
        '1h': 'hour',
    }[timeframe]
    
    # Fetch with appropriate endpoint
    # Store with correct timeframe
```

---

### Phase 3: TA Tracker Updates

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/ta_tracker.py`

**Current State**: 
- Processes whatever timeframe data is provided
- Stores with `_1h` suffix (e.g., `ema20_1h`, `atr_1h`)

**Changes**:

1. **Make suffix dynamic**:
   - Store as `ema20_{timeframe}` instead of `ema20_1h`
   - Or store all timeframes (if we want to support multiple simultaneously)

2. **Option A: Dynamic suffix (recommended for now)**:
   ```python
   # In ta_tracker.py
   timeframe = determine_timeframe_from_data()  # or pass as param
   suffix = timeframe.replace('m', 'm').replace('h', 'h')  # '5m', '1h', etc.
   
   ta['ema']['ema20_' + suffix] = ema20_value
   ta['atr']['atr_' + suffix] = atr_value
   ```

3. **Option B: Store all timeframes** (future enhancement):
   - Compute and store EMAs/ATR/etc. for all available timeframes
   - More flexible but uses more storage

**Recommendation**: Start with Option A (dynamic suffix) for simplicity.

---

### Phase 4: Engine Updates

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/uptrend_engine_v4.py`

**Changes**:

1. **Add timeframe parameter to `UptrendEngineV4.__init__()`**:
   ```python
   def __init__(self, timeframe: str = '1h'):
       self.timeframe = timeframe
       self.suffix = timeframe.replace('m', 'm').replace('h', 'h')
   ```

2. **Replace all `_1h` references**:
   - `ema20_1h` → `f'ema20_{self.suffix}'`
   - `atr_1h` → `f'atr_{self.suffix}'`
   - `adx_1h` → `f'adx_{self.suffix}'`
   - `vo_z_1h` → `f'vo_z_{self.suffix}'`
   - etc.

3. **Update `_latest_close_1h()`**:
   - Rename to `_latest_close()` or keep name but use `self.timeframe`
   - Query: `.eq("timeframe", self.timeframe)`

4. **Update `_fetch_recent_ohlc()`**:
   - Use `self.timeframe` instead of hardcoded `'1h'`

5. **Update `_fetch_ohlc_since()`**:
   - Use `self.timeframe` instead of hardcoded `'1h'`

6. **Fix `_calculate_window_boundaries()`**:
   - Currently: `total_bars = int((current_dt - start_dt).total_seconds() / 3600)`
   - Change to: `total_bars = int((current_dt - start_dt).total_seconds() / get_seconds_per_bar(self.timeframe))`

**Key Changes**:
- Line 174-179: EMA reading
- Line 193: `_latest_close_1h()` method
- Line 219: ATR reading
- Line 228, 245: OHLC queries
- Line 835, 925, 1008: `vo_z_1h` references
- Line 870, 928: `atr_1h` references
- Line 283: Window calculation
- All other `_1h` suffix references

---

### Phase 5: Backtester Updates

**File**: `backtester/v4/code/backtest_uptrend_v4.py`

**Changes**:

1. **Determine timeframe at start**:
   ```python
   def main():
       # ... existing code ...
       
       # Determine timeframe based on token age
       token_age_days = (end_ts - start_ts).days
       timeframe = get_timeframe_for_token_age(token_age_days)
       
       # Pass to engine
       engine = BacktestEngine(target_ts, timeframe=timeframe)
   ```

2. **Update `BacktestEngine.__init__()`**:
   ```python
   def __init__(self, target_ts: datetime, timeframe: str = '1h'):
       super().__init__(timeframe=timeframe)  # Pass to parent
       self.target_ts = target_ts
       self.timeframe = timeframe
   ```

3. **Update all OHLC queries**:
   - `SupabaseCtx.fetch_ohlc_1h_lte()` → `SupabaseCtx.fetch_ohlc_lte(timeframe)`
   - Replace `.eq("timeframe", "1h")` with `.eq("timeframe", timeframe)`

4. **Update `_build_ta_payload_from_rows()`**:
   - Ensure TA calculations work with any timeframe (they should already)

5. **Update main loop**:
   - Currently: `current_ts += timedelta(hours=1)`
   - Change to: `current_ts += timedelta(seconds=get_seconds_per_bar(timeframe))`

**Files to update**:
- `backtest_uptrend_v4.py`: Main backtest logic
- `run_backtest.py`: Backfill and workflow
- `SupabaseCtx` class: All OHLC query methods

---

### Phase 6: Testing Strategy

1. **Test with 14+ day token** (should work exactly as before):
   - Use `1h` timeframe
   - Verify identical results to current system

2. **Test with 7-day token**:
   - Use `15m` timeframe
   - Verify ~672 bars available
   - Verify engine runs correctly

3. **Test with 3-day token**:
   - Use `5m` timeframe
   - Verify ~864 bars available
   - Verify engine runs correctly

4. **Test with 1-day token**:
   - Use `1m` timeframe
   - Verify ~1,440 bars available
   - Verify engine runs correctly

5. **Edge cases**:
   - Token exactly 14 days old
   - Token exactly 7 days old
   - Token exactly 3 days old
   - Token < 1 day old (should still work with 1m)

---

### Phase 7: Migration Considerations

1. **Backward Compatibility**:
   - Default `timeframe='1h'` everywhere
   - Existing tokens continue to work without changes

2. **Database**:
   - No schema changes needed (already supports multiple timeframes)
   - May need to backfill missing timeframes for existing tokens

3. **TA Tracker**:
   - Decide on storage strategy (Option A vs Option B)
   - If Option A, existing `_1h` data still works for 14+ day tokens

4. **Gradual Rollout**:
   - Start with backtester only (doesn't affect live system)
   - Then update engine (with timeframe parameter defaulting to '1h')
   - Finally update live system if needed

---

## Implementation Order

1. ✅ **Phase 1**: Timeframe selection logic (utility functions)
2. ✅ **Phase 2**: Backfill updates (test with different timeframes)
3. ✅ **Phase 5**: Backtester updates (test end-to-end)
4. ✅ **Phase 4**: Engine updates (make engine timeframe-aware)
5. ✅ **Phase 3**: TA Tracker updates (ensure correct suffix storage)
6. ✅ **Phase 6**: Comprehensive testing
7. ✅ **Phase 7**: Migration and rollout

---

## Estimated Effort

- **Timeframe selection logic**: 1 hour
- **Backfill updates**: 2-3 hours (API endpoint research + implementation)
- **TA Tracker updates**: 1-2 hours
- **Engine updates**: 3-4 hours (find/replace + testing)
- **Backtester updates**: 2-3 hours
- **Testing**: 2-3 hours
- **Total**: ~12-16 hours

---

## Notes

- The core logic (state machine, EMA calculations, etc.) doesn't change
- Only the data source and storage suffixes change
- This is primarily a parameterization effort
- Can be done incrementally without breaking existing functionality

