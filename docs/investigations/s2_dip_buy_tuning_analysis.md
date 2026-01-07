# S2 Dip Buy Tuning Analysis

## Current S2 Dip Buy Settings

### Overview
S2 dip buys are **retest entries at EMA333** that occur when price is above EMA333 but not yet in full bullish alignment (S3). They're similar to S1 entries but use different anchors and tighter gates.

### Entry Conditions

**1. Entry Zone (Halo)**
- **Formula**: `abs(price - EMA333) <= 0.5 * ATR`
- **Constant**: `S2_RETEST_HALO_ATR_MULTIPLIER = 0.5`
- **Comparison**: Tighter than S1 (which uses `1.0 * ATR`)
- **Rationale**: EMA333 is a stronger support level, so we can use a tighter entry zone

**2. Slope Gate**
- **Formula**: `EMA250_slope > 0.0 OR EMA333_slope >= 0.0`
- **Comparison**: Uses slow-band slopes (different from S1 which uses `EMA60_slope > 0.0 OR EMA144_slope >= 0.0`)
- **Rationale**: S2 is a defensive regime, so we check the slower structure

**3. TS Gate**
- **Formula**: `TS + S/R_boost >= 0.60`
- **Constant**: `TS_THRESHOLD = 0.60` (same as S1)
- **S/R Boost**: 
  - Maximum: `SR_BOOST_MAX = 0.25`
  - Anchored to: EMA333 (same logic as S1 anchors to EMA60)
  - Halo for S/R proximity: `1.0 * ATR` (same as S1)

**4. State Requirement**
- Must be in **S2 state**: `price > EMA333` but not full bullish alignment
- Can flip-flop between S1 and S2 based on price relative to EMA333

### Current Implementation

**Location**: `uptrend_engine_v4.py::_check_buy_signal_conditions()`

```python
# S2 retest uses EMA333 as anchor
if anchor_is_333:  # S2 retest
    halo = Constants.S2_RETEST_HALO_ATR_MULTIPLIER * atr  # 0.5 * ATR
    entry_zone_ok = abs(price - ema_anchor) <= halo
    slope_ok = (ema250_slope > 0.0) or (ema333_slope >= 0.0)
    ts_ok = (ts_with_boost >= Constants.TS_THRESHOLD)  # 0.60
```

**Diagnostics Captured**:
- `entry_zone_ok`: Boolean
- `slope_ok`: Boolean  
- `ts_ok`: Boolean
- `ts_score`: Float (0.0-1.0)
- `ts_with_boost`: Float (0.0-1.0)
- `sr_boost`: Float (0.0-0.25)
- `ema250_slope`: Float
- `ema333_slope`: Float
- `halo`: Float (0.5 * ATR)
- `atr`: Float
- `price`: Float
- `ema_anchor`: Float (EMA333)

---

## What Needs to Be Added for S2 Tuning

### 1. Episode Tracking

**Current State**: S2 dip buys are **NOT** tracked in the episode system. Only S1 and S3 episodes exist.

**What to Add**:

#### A. S2 Episode Lifecycle

**Start**: State transition `S1 → S2` OR when already in S2 and `buy_flag` becomes True
- Similar to S1, but S2 can flip-flop with S1
- Need to handle: S1 → S2 → S1 → S2 scenarios

**End**:
- **Success**: Reaches `S3` (via `S2 → S3`)
- **Failure**: Returns to `S0` without reaching S3
- **Note**: S2 → S1 is NOT a failure (it's a flip-flop)

**Outcome Classification**:
- `success`: Entered AND reached S3
- `failure`: Entered BUT returned to S0 before S3
- `missed`: Did NOT enter BUT episode reached S3 anyway
- `correct_skip`: Did NOT enter AND episode collapsed to S0

**Key Difference from S1**: S2 episodes can be interrupted by S2 → S1 transitions. Need to handle this gracefully.

#### B. Window Tracking

**Window Opens**: When `buy_flag = True` in S2 state
- Trigger: `s2_retest_check.entry_zone_ok = True` AND `slope_ok = True` AND `ts_ok = True`

**Window Closes**: When `buy_flag = False` OR episode ends

**Samples to Capture** (per tick while window open):
```python
{
    "ts": timestamp,
    "ts_score": float,
    "ts_with_boost": float,
    "sr_boost": float,
    "entry_zone_ok": bool,
    "slope_ok": bool,
    "ts_ok": bool,
    "ema250_slope": float,
    "ema333_slope": float,
    "halo_distance": float,  # abs(price - EMA333) / ATR
    "price": float,
    "ema333": float,
    "atr": float,
    "a_value": float,  # From levers
    "position_size_frac": float
}
```

### 2. Code Changes Required

#### A. Episode Creation (`pm_core_tick.py`)

**Add S2 Episode Tracking**:
```python
def _process_episode_logging(...):
    # ... existing S1/S3 code ...
    
    # S2 Episode Start
    if state == "S2" and prev_state == "S1":
        episode_id = self._generate_episode_id("s2")
        meta["s2_episode"] = {
            "episode_id": episode_id,
            "started_at": now.isoformat(),
            "entered": False,
            "windows": [],
            "active_window": None,
        }
        changed = True
    
    # Handle S2 → S1 flip-flop (pause episode, don't end it)
    elif state == "S1" and prev_state == "S2":
        s2_episode = meta.get("s2_episode")
        if s2_episode:
            # Pause episode (mark as paused, don't finalize)
            s2_episode["paused"] = True
            s2_episode["paused_at"] = now.isoformat()
    
    # Resume S2 episode if we flip back
    elif state == "S2" and prev_state == "S1":
        s2_episode = meta.get("s2_episode")
        if s2_episode and s2_episode.get("paused"):
            s2_episode["paused"] = False
            s2_episode["resumed_at"] = now.isoformat()
    
    # S2 Episode End
    if state == "S3" and prev_state == "S2":
        s2_episode = meta.get("s2_episode")
        if s2_episode:
            outcome = "success" if s2_episode.get("entered") else "missed"
            # Finalize episode
            # ... similar to S1 episode finalization ...
    
    elif state == "S0" and prev_state == "S2":
        s2_episode = meta.get("s2_episode")
        if s2_episode:
            outcome = "failure" if s2_episode.get("entered") else "correct_skip"
            # Finalize episode
            # ... similar to S1 episode finalization ...
```

#### B. Window Tracking (`pm_core_tick.py`)

**Add S2 Window Logic**:
```python
# Handle S2 windows (similar to S1)
s2_episode = meta.get("s2_episode")
if s2_episode and not s2_episode.get("paused"):
    if state == "S2":
        diagnostics = (uptrend.get("diagnostics") or {}).get("s2_retest_check") or {}
        buy_flag_ok = bool(diagnostics.get("entry_zone_ok")) and \
                     bool(diagnostics.get("slope_ok")) and \
                     bool(diagnostics.get("ts_ok"))
        
        active_window = s2_episode.get("active_window")
        if buy_flag_ok:
            if not active_window:
                active_window = {
                    "window_id": self._generate_episode_id("s2win"),
                    "window_type": "s2_retest_buy",
                    "started_at": now.isoformat(),
                    "samples": [],
                    "entered": False,
                }
                s2_episode["active_window"] = active_window
                changed = True
            
            # Capture sample
            sample = self._capture_s2_window_sample(uptrend, now, levers)
            if sample:
                self._append_window_sample(active_window, sample)
                changed = True
        elif active_window:
            # Window closed
            changed |= self._finalize_active_window(
                s2_episode, now, position, regime_context, 
                token_bucket, uptrend, levers
            )
```

#### C. Sample Capture Function (`pm_core_tick.py`)

**Add S2 Sample Capture**:
```python
def _capture_s2_window_sample(
    self, uptrend: Dict[str, Any], now: datetime, 
    levers: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Capture S2 retest window sample."""
    diagnostics = (uptrend.get("diagnostics") or {}).get("s2_retest_check") or {}
    ema_vals = uptrend.get("ema") or {}
    price = float(uptrend.get("price", 0.0))
    ema333 = float(ema_vals.get("ema333", 0.0))
    atr = float(diagnostics.get("atr", 0.0))
    
    halo_dist = None
    if atr > 0 and ema333 > 0:
        halo_dist = abs(price - ema333) / atr
    
    sample = {
        "ts": now.isoformat(),
        "ts_score": float(diagnostics.get("ts_score", 0.0)),
        "ts_with_boost": float(diagnostics.get("ts_with_boost", 0.0)),
        "sr_boost": float(diagnostics.get("sr_boost", 0.0)),
        "entry_zone_ok": bool(diagnostics.get("entry_zone_ok")),
        "slope_ok": bool(diagnostics.get("slope_ok")),
        "ts_ok": bool(diagnostics.get("ts_ok")),
        "ema250_slope": float(diagnostics.get("ema250_slope", 0.0)),
        "ema333_slope": float(diagnostics.get("ema333_slope", 0.0)),
        "halo_distance": halo_dist,
        "price": price,
        "ema333": ema333,
        "atr": atr,
    }
    
    if levers:
        sample["a_value"] = float(levers.get("A_value", 0.0))
        sample["position_size_frac"] = float(levers.get("position_size_frac", 0.0))
    
    return sample
```

#### D. Entry Detection (`pm_core_tick.py`)

**Add S2 Entry Tracking**:
```python
def _update_episode_entry_flags(self, meta: Dict[str, Any], features: Dict[str, Any]) -> bool:
    # ... existing S1/S3 code ...
    
    # S2 Entry Detection
    s2_episode = meta.get("s2_episode")
    execution_history = features.get("pm_execution_history") or {}
    last_s2_buy = execution_history.get("last_s2_buy") or {}
    last_s2_ts = last_s2_buy.get("timestamp")
    
    if s2_episode and last_s2_ts:
        consumed = meta.get("last_consumed_s2_buy_ts")
        active = s2_episode.get("active_window")
        if active and consumed != last_s2_ts:
            start_dt = self._iso_to_datetime(active.get("started_at"))
            buy_dt = self._iso_to_datetime(last_s2_ts)
            if start_dt and buy_dt and buy_dt >= start_dt:
                active["entered"] = True
                active["entry_timestamp"] = last_s2_ts
                s2_episode["entered"] = True
                meta["last_consumed_s2_buy_ts"] = last_s2_ts
                changed = True
    
    return changed
```

### 3. Lever Considerations

**Levers to Tune for S2** (similar to S1):

1. **`ts_min`**: TS threshold (currently 0.60)
   - Tighten if too many false positives
   - Loosen if too many misses

2. **`s2_halo_multiplier`**: Halo distance multiplier (currently 0.5)
   - Tighten if entries too far from EMA333 fail
   - Loosen if misses were close to EMA333

3. **`ema250_slope_min`**: EMA250 slope guard (currently 0.0)
   - Tighten if failures show barely positive slopes
   - Loosen if misses show slightly negative slopes yet succeed

4. **`ema333_slope_min`**: EMA333 slope guard (currently 0.0)
   - Same logic as EMA250

5. **`sr_boost_max`**: S/R boost ceiling (currently 0.25, shared with S1)
   - Could be separate for S2 if needed

### 4. Pattern Key

**Pattern Key for S2**:
- `pattern_key = "pm.s2_retest"` (or `"pm.s2_entry"`)
- Same scope structure as S1/S3

### 5. Tuning Miner Updates

**No changes needed** - The miner already handles any `pattern_key`, so S2 episodes will automatically be included once logged.

### 6. Materializer Updates

**Add S2 Support**:
```python
# In override_materializer.py::materialize_tuning_overrides()
if "S2" in pattern_key or "s2_retest" in pattern_key:
    overrides_to_write.append(('tuning_ts_min', mult_threshold))
    overrides_to_write.append(('tuning_s2_halo', mult_halo))  # New override type
```

### 7. Runtime Override Application

**Add S2 Override Support**:
```python
# In overrides.py::apply_pattern_execution_overrides()
if "tuning_s2_halo" in overrides:
    base_halo = Constants.S2_RETEST_HALO_ATR_MULTIPLIER
    mult = overrides["tuning_s2_halo"]["multiplier"]
    adjusted["signal_thresholds"]["s2_halo_mult"] = base_halo * mult
```

**Update Engine**:
```python
# In uptrend_engine_v4.py::_check_buy_signal_conditions()
# Read override if available
s2_halo_mult = plan_controls.get("signal_thresholds", {}).get("s2_halo_mult", 1.0)
halo = (Constants.S2_RETEST_HALO_ATR_MULTIPLIER * s2_halo_mult * atr) if anchor_is_333 else ...
```

---

## Summary: Current S2 Settings

| Setting | Value | Tunable? |
|---------|-------|----------|
| **Halo** | `0.5 * ATR` | ✅ Yes (via `S2_RETEST_HALO_ATR_MULTIPLIER`) |
| **TS Threshold** | `0.60` | ✅ Yes (via `TS_THRESHOLD`, shared with S1) |
| **EMA250 Slope** | `> 0.0` | ✅ Yes (could add minimum threshold) |
| **EMA333 Slope** | `>= 0.0` | ✅ Yes (could add minimum threshold) |
| **S/R Boost Max** | `0.25` | ✅ Yes (shared with S1, could be separate) |
| **S/R Halo** | `1.0 * ATR` | ⚠️ Hardcoded (could be tunable) |

---

## Implementation Priority

1. **Phase 1**: Episode tracking (create S2 episodes, track windows)
2. **Phase 2**: Sample capture (capture S2 signal values)
3. **Phase 3**: Entry detection (mark windows as entered/skipped)
4. **Phase 4**: Outcome determination (success/failure/missed/correct_skip)
5. **Phase 5**: Override application (apply tuning to S2 gates)

The system already has the infrastructure (miner, materializer, override application) - we just need to add S2 episode tracking similar to S1.



