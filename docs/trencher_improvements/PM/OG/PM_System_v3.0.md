Here’s the **single-file .md** you can drop into the repo to replace the sprawling v2.0.
It keeps every necessary detail, but refactors into the 4-layer model + one config block as the source of truth.

---

# ⚘ Lotus_Trader — Portfolio Manager (PM) System v3.0

**A compact, executable spec** that unifies Market Mode (SPIRAL), A/E Posture, Geometry & Flow, and Actions.
It supersedes the v2.0 plan while preserving all math, schemas, and safeguards.

---

## 0) Source-of-Truth Config

```jsonc
{
  "ema": { "short": 12, "long": 60 },                // 1m context
  "atr": { "tf": "1m", "mult_support_zone": 1.0 },
  "sr_conf": { "valid": 0.50, "strong": 0.60 },
  "obv_slope_per_bar": { "rise": 0.05, "fall": -0.05 },
  "voz": { "moderate": 0.30, "strong": 0.80 },
  "divergence_lookback": { "aggr": 10, "norm": 15, "pat": 20 },
  "e2_retrace_window": [0.68, 1.00],                 // r = (H - P) / (H - B)
  "mode_sizes": {
    "patient":   { "immediate": 0.00, "e1": 0.05, "e2": 0.05 },
    "normal":    { "immediate": 0.10, "e1": 0.15, "e2": 0.15 },
    "aggressive":{ "immediate": 0.15, "e1": 0.35, "e2": 0.50 }
  },
  "trend_redeploy_frac": { "pat": 0.12, "norm": 0.23, "aggr": 0.38 },
  "cuts": {
    "e1_support_loss": { "bars15m": 1, "require_reclaim_next": true },
    "e2_breakout_fail": { "bars15m_below_B": 2 }
  },
  "trail": { "consec_below_long": 15, "no_reclaim_bars": 6 },  // profit-only trail
  "ae_coupling": { "cut_pressure_coeff": 0.33, "per_lever_cap": 0.40 },
  "macro_freeze": ["Oh-Shit", "Double-Dip"]
}
```

* Store as `config/pm_config.jsonc` and import across **L2/L3/L4**.
* Parameter tuning later plugs into Learning (§11).

---

## 1) L1 — Market Mode (SPIRAL)

**Goal:** Compute Macro/Meso/Micro phases from BTC, majors, and portfolio; emit durable `phase_state` and events.

### Inputs

* **Prices (1m canonical):** `lowcap_price_data_1m`, `majors_price_data_1m`
* **Alt basket:** EW(SOL, ETH, BNB, HYPE)
* **r_port:** from portfolio NAV hourly (`portfolio_bands.nav_usd`)
* **Dominance:** BTC.D, USDT.D (diagnostics stored in `portfolio_bands`)
* **OBV/VO/Breadth:** feature pipeline (§2)

### Method (kept from v2.0 / SPIRAL docs)

* Four lenses on **USD log returns**: `S_btcusd`, `S_rotation`, `S_port_btc`, `S_port_alt`
* Blends per horizon (Macro/Meso/Micro), dwell & hysteresis; skip rules (no Recover→Double-Dip)
* Geometry assist: swings N=10, Theil–Sen diagonals, `sr_break`, `sr_conf` (confirmation via VO_z | OBV_z)

### Outputs

* `phase_state(token, ts, horizon, phase, score, slope, curvature, delta_res, confidence, dwell_remaining, s_*)`
* Events: `phase_transition`, `rotation_tilt_on/off`

### Tables (unchanged)

* `phase_state`, `portfolio_bands` (incl. dominance diagnostics & nav_usd), `majors_price_data_1m`, `majors_trades_ticks` (optional)

---

## 2) L2 — A/E Posture (Per-Asset Stance)

**Goal:** Convert Mode + context into continuous **A** (add appetite) and **E** (exit assertiveness) in **[0,1]** with reasons.

### Inputs

* Latest `phase_state` per horizon, `portfolio_bands.cut_pressure`
* `positions.features`: rsi_div, vo_z, obv_ema/z/slope, `sr_break/sr_conf/sr_age/sr_tf`, breadth_z, residual deltas, intent metrics
* DM caps and position state (qty, avg_entry, age, locks)

### Computation (ordered & clamped)

1. **Phase → Base Policy** (Meso drives, Macro scales, Micro times)
2. **Cut-pressure coupling**:
   `A = A × (1 − 0.33·cut_pressure)`, `E = E × (1 + 0.33·cut_pressure)`
3. **TA/Flow deltas (caps ±0.4/lever)**

   * RSI divergence ±0.25; OBV divergence ±0.10 (+0.05 combo)
   * Geometry (SR/diagonal) ±0.15 to A, ±0.20 to E
   * EMA trend confirm ±0.05
   * Volume state (0.6·VO_z + 0.4·OBV_z) ±0.10
   * Residual vs majors ±0.10; Breadth ±0.05
4. **Intent channels** (±0.30 aggregate; synchrony modifiers)
5. **Clamp & discretize** for UI: patient [0–0.3), normal [0.3–0.7), aggressive [0.7–1]

**API:** `compute_AE(token) -> {A_final, E_final, mode_display, reasons[]}`

---

## 3) L3 — Geometry & Flow (Token TA)

**Goal:** Provide deterministic structural signals for **entries, exits, and redeploys**.

### What we compute

* **Support/Resistance** clusters; **sr_conf** scoring
* **Diagonals:** wedges/channels (Theil–Sen) + `diag_break`
* **Fibs:** always **Top → Bottom** of visible range; alignment guide (not fixed targets)
* **Divergences:** bullish/hidden bullish & bearish across RSI/OBV
* **Context gates:** within ±1·ATR(1m) constitutes “at support”; EMA(12/60) trend only as **context**

### Persistence

* Everything cached under `positions.features` (freshness target < 2 h; skip decisions if stale)

---

## 4) L4 — Actions (Entries, Exits, Redeploy)

The live decision layer that emits **`pm_decision_strands`**.
It implements your finalized **Entry v2.0**, **Exit v1.0**, and **Trend-Redeploy v1.0**.

### 4.1 Entries — *Unified for new & known tokens*

| Mode           | Immediate | E1 (Support/Wedge) | E2 (Breakout/Retest) |    Total |
| -------------- | --------: | -----------------: | -------------------: | -------: |
| **Patient**    |        0% |                 5% |                   5% |  **10%** |
| **Normal**     |       10% |                15% |                  15% |  **40%** |
| **Aggressive** |       15% |                35% |                  50% | **100%** |

* **Immediate probe** skipped only in **Patient**.
* **E2 without E1** allowed (late/trending discovery).

**E1 unlock (any 2, or 1 strong):**

* Bullish / hidden bullish divergence; **OBV slope ≥ +0.05** (strong ≥ +0.10); **VO_z ≥ +0.3** (strong ≥ +0.8 for 3 bars); **sr_conf ≥ 0.5** (strong ≥ 0.6 with long lower wicks).
* **Cut E1**: 1× 15m close below support **and** no reclaim on next 15m bar; or metrics flip bearish (OBV slope < −0.05 for 3 bars, VO_z < −0.5, bearish divergence).

**E2 (breakout retrace):**

* Identify **B** (breakout line) and **H** (local high of leg); retrace ratio `r = (H − P)/(H − B)`
* Buy window **r ∈ [0.68, 1.00]** on quick flow confirm (**VO_z ≥ 0.5** or OBV uptick).
* **Cut E2**: 2× 15m closes below **B**.

### 4.2 Exits — *Zones + Exhaustion + Trail (profit-only)*

* **Zones**: horizontal SR / fib extensions / diagonal channel tops (from L3)
* **Exhaustion**: bearish RSI/OBV divergence **near a zone**, distribution tells (upper wicks, VO_z red), or loss of hold on the zone

**Tranche sizes by *E-mode* (of remaining tokens):**

* **Aggressive E:** 69%
* **Normal E:** 33%
* **Patient E:** 23%
  (≤ 2 tranches per zone; then wait for the next zone/exhaustion)

**Trail (dynamic leash; profit-only):**

* **Trigger:** `15` consecutive 1m closes below EMA_long (60) → queue trim on first bounce;
  if **no reclaim** within **6** bars → demote to Moon (sell 70–90%, keep moon-bag).

 

### 4.3 Trend-Redeploy — *Reinvest realised profits with same E1/E2 rules*

* **Activate:** a TP occurred on this token **and** structure **intact** (no EMA_long/diagonal break; price ≥ EMA_long)
* **Size (of realised proceeds):** Patient **12%** / Normal **23%** / Aggressive **38%**
* **Timing:** either **≥ 23.6%** pullback from the last local high **or** **≥ 36h** since TP
* **Execution:** treat as **E1** (near EMA/support) or **E2** (new breakout + retrace) with the **same cut rules**

---

## 5) Bands & Rotation (Portfolio Breathing)

* Track **core_count**; ideal target = **12** (smooth seesaw: above 12 reduces A, increases E; below 12 increases A, reduces E).
* **Cut-pressure** computed from diagnostics (incl. core-count seesaw); couples into **A/E**.
* EPS removed from scope; Actions are driven by A/E + geometry only.

---

## 6) Event Bus & Triggers (Idempotent)

* `phase_transition`, `rotation_tilt_on/off`, `sr_break_detected/retest/reject`, `ema_trail_breach`, `decision_approved`, `time_gate_expired`, `new_token_signal`, `flip_conditions_met`.
* Coalesce recomputes within 1–2s; all handlers **pure & idempotent**.

---

## 7) Strands & Logging (Learning-Ready)

* **`ad_strands`**: `decision_type`, `size_frac` (of DM cap), `(A,E)`, `reasons[]`, `phase_state`, `trend_redeploy_frac`, `dead_score_final`, forward PnL (24h/72h backfill).
* Reasons are **ordered** by computation flow for audit.

---

## 8) Runtime & Schedules

* **1m**: ingest, per-minute trail/structure monitors
* **Hourly :00–:10**:

  * :02 `nav_compute_1h`
  * :03 `dominance_ingest_1h`
  * :04 `features_compute_1h` (SPIRAL)
  * :05 `pm_core_tick` (A/E + Actions)
  * :10 `geometry_build_daily` (daily)
  * `strands_backfill_pnl` hourly

**On-event:** immediate PM recompute (debounced).

---

## 9) Database (kept; minor notes)

* **Positions**: `features` JSONB (OBV/VO/RSI/geometry/diagnostics), cooldown/locks, trend counters, new_token_mode
* **Phase**: `phase_state` with **lens diagnostics** (`s_btcusd`, `s_rotation`, `s_port_btc`, `s_port_alt`)
* **Bands**: `portfolio_bands` (core_count, cut_pressure, dominance diagnostics, nav_usd)
* **Majors**: `majors_trades_ticks` (optional), `majors_price_data_1m` canonical
* **Indexes**: GIN on `positions.features`, uniques on `(token, ts, horizon)` in `phase_state`

---

## 10) Module Layout (paths kept; responsibilities simplified)

```
src/pm/
  ingest/                 # WS + 1m rollup
  spiral/                 # L1
    returns.py lenses.py phase.py geometry.py dominance.py persist.py
  core/                   # L2
    context.py modes.py apply_signals.py
  actions/                # L4
    entry.py exit.py trail.py trend_redeploy.py lifecycle.py emit.py
  bands/                  # Portfolio breathing
    eps.py select.py emit.py
  events/                 # Bus (idempotent)
    bus.py types.py
  strands/
    write.py pnl_backfill.py
  jobs/
    features_compute_1h.py bands_calc.py pm_core_tick.py
  tests/
    unit/ fixtures/ integration/
```

---

## 11) Testing & Rollout (unchanged gates; updated cases)

* **Unit:** EMA/slope/curvature/z; phase banding/dwell/skip; lever ordering & clamping; E1/E2 rules; trail; redeploy sizing
* **Fixtures:**

  * Recover→Good adds; Good/Euphoria zone exits; trail breach + bounce; E2 fail cuts; redeploy after TP with structure intact
  * New token probe→flip; liquidity & staleness guards; macro-freeze pauses adds
* **Integration replay (7d @1m):** stable dwell, zero invalid skips, strands match rules
* **Rollout:** shadow → canary (3–5 cores) → full; ACTIONS gated by env; events on

**Gates:** `ingest_lag_s < 60`, no strand write errors, flip rate within ±50% baseline, zero invalid skip count
**Rollback:** disable core tick / actions; stay in shadow; revert params

---

## 12) Learning Hooks (future)

* Datasets from `ad_strands` (+ reasons, phase snapshots, PnL 24/72h)
* Tune: lens weights, rotation tilt thresholds/dwell, hysteresis gaps, divergence windows, redeploy fractions
* Monthly param updates with checksums & auto-rollback if flip storms

---

## 13) Delta from v2.0 (what’s different)

* **Primary exits** now **Zones + Exhaustion + Trail**; fixed ladders moved to **fallback**.
* **Entries** unified; **E2 without E1** explicitly supported.
* **Trend-redeploy** reuses **E1/E2** with **12/23/38%** proceeds sizing and **23.6% or 36h** reset rule.
* **Cut-pressure**: remains a coupling to A/E; **EPS** only selects what to trim when freeing capital.
* **Single config** block controls all numeric thresholds across L2–L4.

---

## 14) Minimal Implementation Plan (do this next)

1. **Swap Actions to Entry/Exit/Redeploy v1.0** (this doc)
2. **Expose `compute_AE`** with ordered/clamped reasons
3. **Ensure L3 writes**: `sr_conf/sr_break/diag_break`, fib set (top→bottom), divergence flags
4. **Wire bus events** to L2/L4 recompute (phase, sr_break, trail, bands)
5. **Dashboards:** A/E distributions, cut_pressure, current phases, last 50 strands with reasons & size

---

### Appendix — Guardrails (quick list)

* **Feature staleness > 2h** → no new adds
* **Liquidity guard:** spread/slippage > 3% → cap to seed/E1 only
* **Macro freeze:** Oh-Shit / Double-Dip → pause adds; exits/trails still act
* **Moon/Core lifecycle:** trail/demotion on structure break with profit; promotion when EMA_long + flow reconfirm

---

**That’s it.** One page, four layers, one config.
Everything else you built slots in cleanly — and it’s now trivial to operate, test, and tune.
