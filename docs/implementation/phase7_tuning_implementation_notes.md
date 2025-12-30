# Phase 7: Tuning System Implementation Notes

## Status: Partially Implemented

### What's Already Done ✅
- DX ladder uses `dx_atr_mult` from `tuned_controls` (line 1133 in actions.py)
- Tuning infrastructure exists (`apply_pattern_execution_overrides`)
- Episode logging framework exists (`_process_episode_logging`, `_log_episode_event`)

### What's Missing ❌

#### 1. S2 Episode Tracking
**Location**: `pm_core_tick.py::_process_episode_logging()`

**Needed**:
- Track S2 episode start (S1→S2 transition, set `s2_started=True`)
- Track S2 opportunity windows (when `buy_flag=True` in S2 with pool available)
- Log episode event on attempt end (S3 success or S0 failure)
- Include `s2_opportunity_existed` flag

**Pattern**: Similar to S1 episode, but:
- Starts on S1→S2 (not S0→S1)
- Ends on attempt end (S3 or S0)
- Tracks opportunity windows (not entry zone)

#### 2. DX Episode Event Logging
**Location**: `pm_core_tick.py::_update_execution_history()` or `actions.py`

**Needed**:
- Log DX episode event when DX buy happens
- Include: `dx_count`, `dx_atr_mult_used`, `pool_basis`
- Track opportunity flags during S3 episode
- Finalize outcome on recovery cycle end (trim after recovery OR emergency before trim)

**Pattern**: Similar to S3 retest windows, but:
- Logged per DX buy (not per window)
- Outcome determined by recovery cycle (trim after = success, emergency before = failure)

#### 3. Miner Updates
**Location**: `tuning_miner.py` or `lesson_builder.py`

**Needed**:
- Handle `episode_type == "s2_entry"` in lever considerations
- Handle `episode_type == "s3_dx"` in lever considerations
- Compute outcomes for S2/DX episodes

**S2 Levers**:
- `tuning_s2_halo_mult` (from halo distance samples)
- `tuning_s2_ts_min` (from TS score samples)

**DX Levers**:
- `tuning_dx_atr_mult` (from dx_count on success only)

#### 4. Materializer Updates
**Location**: `override_materializer.py` or similar

**Needed**:
- Emit `tuning_s2_halo_mult` overrides
- Emit `tuning_s2_ts_min` overrides  
- Emit `tuning_dx_atr_mult` overrides (clamped to [2.0, 12.0])

**Runtime Application**: Already handled in `apply_pattern_execution_overrides()`

---

## Implementation Complexity

**Low Complexity** (Can do now):
- DX episode event logging (just log when DX buy happens)
- Opportunity flag tracking (boolean flags in episode meta)

**Medium Complexity** (Needs careful integration):
- S2 episode tracking (follow S1 pattern, but different triggers)
- Miner updates (add new episode types to existing logic)

**High Complexity** (Needs design decisions):
- DX recovery cycle definition (when does cycle start/end?)
- Outcome determination (trim after recovery vs emergency before)

---

## Recommendation

**Immediate**: Add DX episode event logging when DX buys happen. This is the most critical missing piece.

**Next**: Add S2 episode tracking following S1 pattern.

**Later**: Update miner/materializer (can be done incrementally as data accumulates).

---

## Quick Win: DX Event Logging

Add to `_update_execution_history()` after DX buy:

```python
# After DX buy (line ~1740)
if state == "S3" and "reclaimed" not in signal.lower():
    # Log DX episode event
    pool = _get_pool(execution_history)
    dx_count = pool.get("dx_count", 0)
    dx_atr_mult = float((action.get("reasons") or {}).get("dx_atr_mult", 6.0))
    
    # Get scope for tuning
    scope = {
        "chain": token_chain,
        "bucket": token_bucket,  # from position features
        "timeframe": timeframe,
    }
    
    # Log event
    self._log_episode_event(
        window={},  # DX is point-in-time, not window-based
        scope=scope,
        pattern_key="pm.uptrend.S3.dx",
        decision="add",
        factors={
            "dx_count": dx_count,
            "dx_atr_mult_used": dx_atr_mult,
            "pool_basis": pool.get("usd_basis", 0),
        },
        episode_id=f"dx_{position_id}_{dx_count}",
        trade_id=position.get("current_trade_id"),
    )
```

This gets DX events into the database immediately, even if miner/materializer updates come later.

