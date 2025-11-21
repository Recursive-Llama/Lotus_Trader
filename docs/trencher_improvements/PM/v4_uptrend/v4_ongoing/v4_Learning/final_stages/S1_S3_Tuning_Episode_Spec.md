## Overview
- Scope: PM tuning layer only (S1 entry gating + S3 retest buys)
- Goal: convert stage diagnostics into edge-weighted overrides per `(pattern_key + scope)`
- Inputs: engine state transitions, buy_flag windows, DX/EDX diagnostics, PM action outcomes
- Outputs: `pm_tuning` lessons with lever deltas (TS threshold, SR boost, slope guard, halo, DX threshold, EDX suppression)

---

## Episode Concepts
- `episode_id` (ULID) created at start of each state-controlled window
- `trade_id` ties to actual position when size > 0; watchlist episodes keep `trade_id = null`
- `pattern_key` + `scope` (same as PM strength / DM learning) recorded on every strand
- Strands carry `signals` (TS, SR boost, slopes, halo distance, DX, EDX, etc.) and `decision` metadata (entered/skipped, skip reasons, add size, trim)
- Episode summary emitted when endpoint reached; this is what lessons consume

### S1 Episode
- **Start**: `S0 → S1`
- **End**:
  - Success: first `S1 → S2` followed by `S2 → S3` before returning to S0 (i.e. S3 reached)
  - Failure: `S1 → S0` (global exit / no S3)
- **Missed**: no entry taken *and* episode ultimately reaches S3
- **Correct skip**: no entry and episode collapses back to S0
- **Strands inside episode**:
  - Continuous `buy_flag` windows (flag true while TS/halo/slope satisfied)
  - Each window stores capped samples (`signals_bars`) plus summary stats
    - Always capture first, closest-to-threshold, last bar, and any severity-knot crossings
    - Summary block includes min/max/median TS, DX, price-band distance, etc.
    - Timestamps let us reconstruct full OHLC context later
  - Pattern key/scope captured when the buy window strand is emitted (not at generic S0→S1 transition)
  - If PM enters, strand links to `trade_id`

### S3 Episode
- **Start**: `S2 → S3` (first bar of full trend)
- **End**: `S3 → S0` (all EMAs below EMA333/global exit)
- **Inside**: multiple retest windows whenever DX buy flag toggles on
  - Each window records capped sample array + summaries (same rules as S1)
  - Diagnostics include DX, EDX, price band position, slopes, TS, SR boost, decision metadata
  - Outcomes:
    - `enter → first subsequent trim before S0`: success
    - `enter → emergency_exit/S0 before trim`: failure
    - `skip → later trim`: missed opportunity
    - `skip → S0`: correct skip

---

## Strand Schema Notes
- Use existing `ad_strands` table
- `kind`: `uptrend_stage_transition` | `uptrend_buy_window` | `uptrend_episode_summary`
- Core columns: `position_id`, `trade_id`, `timeframe`, `symbol`, `episode_id`
- `content` JSON structure:
  ```json
  {
    "pattern_key": "module=pm|pattern=uptrend.S1.entry",
    "scope": {"macro_phase": "recover", "bucket": "micro", "...": "..."},
    "from_state": "S0",
    "to_state": "S1",
    "signals": {"ts": 0.58, "sr_boost": 0.12, "ema60_slope": 0.01, "ema144_slope": 0.03, "halo_atr": 0.7},
    "decision": {"action": "skipped", "skip_reasons": ["ts_below_threshold_by_0.02"]}
  }
  ```
- Buy windows add capped `signals_bars` arrays (first/closest/last/severity-knot bars) plus summary stats (min/max/median per signal) so we can reconstruct context later; S3 windows also include `retest_index`
- Episode summary strand (`kind = uptrend_episode_summary`) captures: `episode_id`, `pattern_key`, `scope`, `episode_type`, `outcome`, `episode_edge`, aggregated diagnostics, and lever-severity tuples; emitted once per episode close similar to trade summaries

---

## Lever Mapping (S1)
- **TS threshold (`ts_min`)**
  - Tighten when failed entries cluster with TS close to threshold but SR boost absent/weak
  - Loosen when skipped windows had TS slightly below threshold and episode reached S3
- **SR boost (`sr_boost_max`)**
  - Increase when entry sat inside halo + SR present but TS still barely missed and episode succeeded
  - Decrease when SR boost is pushing clearly bad entries (failure episodes with large boost)
  - Adjust before touching TS threshold when SR evidence exists
- **Slope guard (`slope_min`)**
  - Parameters: require both EMA60 & EMA144 positive? min slope magnitude?
  - Tighten when failures show one slope barely > 0 and trades die quickly
  - Loosen when missed windows have slopes slightly below zero yet produce S3
- **Halo multiplier (`halo_mult`)**
  - Tighten when failures occur with large halo distances
  - Loosen when missed episodes have price barely outside halo but reach S3

### Severity Calculation
- Shared formula across levers:
  - `delta = observed_value - threshold_value` (signed; take `abs(delta)` when only distance matters)
  - Severity caps: TS/SR = 0.10, slopes = 0.02, halo = 0.20 (ATR units), DX = 0.10, EDX suppression = 0.20
  - `severity = min(1.0, |delta| / severity_cap)`
  - `signal_confidence = robustness_score × (samples_in_window / total_samples)`
  - `lever_vote_weight = outcome_weight × reliability × specificity × severity × signal_confidence`
- Episode summary includes `levers_considered: [{lever, delta, severity, signal_confidence}]` so lesson builder doesn’t need to recompute

---

## Lever Mapping (S3 Retest)
- **Price band awareness (diagnostic)**
  - Valid retests live between EMA333 (bottom/emergency-exit anchor) and EMA144 (top of discount band)
  - Diagnostic captures normalized distance: 0.0 at EMA144, 1.0 at EMA333
  - Lower position (closer to EMA333) automatically grants a price-position boost; higher position tightens the effective DX gate
- **Slow-band slope guard (`slow_slope_min`)**
  - EMA250_slope and EMA333_slope tracked independently
  - Tighten per pattern when failures cluster with barely-positive slopes
  - Loosen when skipped retests show slightly negative slopes yet still reach trims
- **TS + SR gate (`ts_min`, `sr_boost_max`)**
  - Same TS formula as S1 but anchored to EMA333
  - Increase SR boost ceiling before lowering TS when SR evidence exists but TS barely misses
- **DX threshold (`dx_min`)**
  - Base = `Constants.DX_BUY_THRESHOLD`
  - Effective threshold = base + EDX suppression − price-position boost
  - Tighten when adds taken near the boundary dump to emergency exit
  - Loosen when DX repeatedly clears base yet we skip and the episode trims
- **EDX suppression (`edx_supp_mult`)**
  - Controls how quickly high-EDX environments shut down retests
  - Lesson raises suppression for decaying patterns, lowers it when high-EDX retests still succeed
- **(Future) Retest halo**
  - We log raw ATR distance to EMA333 so we can later cap allowed halo width per pattern
- **(Future) Price-band bias lever**
  - Additional weight on the normalized band position if we need more direct control than the built-in boost

---

## Adjustment Mechanics
- Each episode summary → lesson candidate
- Lesson metadata:
  - `pattern_key`, `scope`
  - `episode_type`: `s1_entry` | `s3_retest`
  - `outcome`: success/failure/missed/correct_skip
  - `signals_at_decision`: best sample (closest to threshold) + aggregated stats
- Convert to override votes:
  ```python
  vote = {
    "lever": "ts_min",
    "target": current_ts_min ± delta,
    "weight": w_edge * w_n * w_var * w_decay * w_spec * severity
  }
  ```
- Combine votes multiplicatively/additively, same combiner as PM strength/DM allocation
- Global clamps per lever per tick (e.g. ±0.02 TS change per evaluation)

---

## Open Items
- Decide whether to store `signals_bars` as dense array or summarized stats to keep strands lean
- Confirm best timestamp to assign `pattern_key` for watchlist positions (likely use latest decision-maker context snapshot)
- Define exact values for severity caps, max step sizes, half-life defaults for `pm_tuning` lessons
- Update PM runtime so stage-only episodes (no trade) still appear in learning queue

=====

Buy-window strands store capped sample arrays (first / closest-to-threshold / last / severity knot bars) plus summary stats so we can always reconstruct the path later.
Pattern key + scope get stamped when each buy-window strand is emitted (not on plain S0→S1 transitions). Watchlist-only episodes now inherit the same logic.
S3 section explicitly states that DX windows use the same sampling rules and diagnostics