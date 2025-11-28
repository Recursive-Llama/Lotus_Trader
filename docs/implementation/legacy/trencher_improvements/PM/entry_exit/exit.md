# ⚘ Portfolio Manager — Exit System v1.0

Unified exit framework for all tokens.  
Exits respond to **structure loss**, **trend exhaustion**, and **portfolio pressure**, with adaptive thresholds by **E-mode (exit aggressiveness)**.

---

## 1. Exit Types Overview

| Type | Purpose | Typical Trigger | Notes |
|------|----------|-----------------|-------|
| **Structural / Stop-loss** | Hard safety cuts | Support loss (E1) or breakout failure (E2) | Mirrors entry invalidation |
| **Resistance-zone / Exhaustion TP** | Take profits into strength | Confluence of resistance + exhaustion signals | Adaptive size by E-mode |
| **Trail-based Exit** | Rising stop; exit when trend breaks | EMA/ATR trail breach + momentum overlay | Converts core → moon-bag |
| **Portfolio Rotation (optional)** | Free capital under congestion | Cut-pressure sustained high | Uses EPS as bias to raise `E` and select trims; does not force cuts by itself. DeadScore_final > 0.6 remains a hard demotion trigger. |

---

## 2. Structural / Stop-Loss Exits

These protect capital when the entry thesis is invalidated.

| Condition | Rule | Action |
|------------|------|--------|
| **E1 support loss** | One 15 m close fully below support `S₀` **and** no reclaim above `S₀` on next 15 m bar | Sell entire E1 tranche on first retest from below |
| **E2 breakout fail** | Two consecutive 15 m closes below breakout line `B` | Sell entire E2 tranche immediately |
| **Macro hostility** | Phase ∈ {Oh-Shit, Double-Dip} | Freeze adds, bias E→Aggressive until recovery |

---

## 3. Resistance-Zone / Exhaustion Take-Profits

### 3.1. Identify Resistance Zones

Zones are drawn automatically; a zone is valid when price is within **± 0.5 × ATR(14, 15 m)**.

Priority of sources:
1. **Horizontal resistance:** clustered highs or prior S/R flips (Theil–Sen, prominence ≥ 0.5 × ATR (15 m)).
2. **Master Fib (Top→Bottom of visible range):** 38.2 / 50 / 61.8 % levels aligned with (1).
3. **Post-breakout impulse extensions:** +38.2 / +61.8 / +161.8 / +261.8 / +423.6 % of the **B→H** leg (only if they coincide with 1–2).
4. **Diagonals / channels:** upper trendline with ≥ 3 touches.

A TP may trigger **only inside** such a zone.

---

### 3.2. Exhaustion Signals

Trigger when **≥ 2 standard** or **1 strong** signals occur inside a resistance zone.

| Signal | Threshold | Description |
|---------|------------|-------------|
| **Bearish or hidden bearish divergence** | RSI/OBV 10–20 bar look-back (mode-dependent) | Price HH, indicators LH (or reverse for hidden) |
| **Volume climax + stall** | VO_z ≥ +1.5 then ≥ 3 bars drop | Blow-off + fading participation |
| **OBV roll-over** | OBV slope ≤ –0.05 per 1 m bar (≥ 3 bars) | Distribution pressure |
| **15 m rejection** | Intrabar break > resistance → 15 m close below | Failed hold of level |
| **Strong single** | Volume climax + 15 m rejection simultaneously | Immediate TP allowed |

---

### 3.3. TP Size by E-Mode

| E-mode | TP % of remaining tokens | Behaviour |
|---------|--------------------------|------------|
| **Patient E** | ~23 % | Minimal trim; only clear reversals |
| **Normal E** | ~33 % | Balanced reduction |
| **Aggressive E** | ~69 % | Decisive de-risk |

- Max 2 TPs per zone; later zones reuse same percentages.  
- Once holdings reach **moon-bag target = 0.1 × max_alloc**, stop normal TPs.  
- Moon-bag excluded from sell calculations.

DeadScore (clarification): `DeadScore_final > 0.6` is a hard trigger to demote Core → Moon (sell 70–90%) or exit on next rally. Otherwise, EPS/DeadScore influence `E` and selection priority, not forced cuts.

---

### 3.4. Signal-Strength by E-Mode

| E-mode | OBV roll-over threshold | VO_z climax sensitivity | RSI divergence look-back |
|---------|------------------------|--------------------------|--------------------------|
| **Aggressive E** | ≤ –0.05 over 3 bars | ≥ +1.2 | 10 bars |
| **Normal E** | ≤ –0.075 over 4 bars | ≥ +1.5 | 15 bars |
| **Patient E** | ≤ –0.10 over 6 bars | ≥ +2.0 | 20 bars |

More aggressive → earlier reaction; more patient → require stronger evidence.

---

## 4. Trail-Based Exits (Rising Stop / Trend Break)

### 4.1. Setup

| Parameter | Default | Description |
|------------|----------|-------------|
| **EMA_long (1 m)** | 60 | Primary trailing base (fixed anchor) |
| **EMA_mid (15 m)** | 55 | Higher-TF confirmation (fixed anchor) |
| **ATR(14, 1 m)** | Used for adaptive gap | Volatility cushion |

### 4.2. Trigger Logic

1. **Trail-pending:**  
   - ≥ 12–15 consecutive 1 m closes below EMA_long (count can vary slightly with `E`), or  
   - 1 × 15 m full-body close below EMA_mid + OBV slope < 0.  
2. **Adaptive gap fire:**  
   - Sell when close < EMA_long – k × ATR(14, 1 m) and momentum overlay confirms.  
     - Aggressive k = 0.25  
     - Normal k = 0.40  
     - Patient k = 0.60  
3. **Momentum overlay confirmation (need ≥ 1):**  
   - OBV slope < 0  or  VO_z < 0  or  bearish RSI divergence (look-back per table).  
4. **Action:**  
   - Exit all non-moon units.  
   - Retain moon-bag (0.1 × max_alloc) until blow-off or macro flip.

---

## 5. Portfolio Rotation / Cut-Pressure Response (Optional)

| Trigger | Rule | Action |
|----------|------|--------|
| **Cut-pressure > 0.2** | soft | raise E by +1 tier temporarily |
| **Cut-pressure > 0.33 sustained 3 ticks** | hard | trigger rotation; trim weak coins |
| **EPS ranking** | high EPS = weak coin | trim first on rotation |
| **DeadScore > 0.6** | prolonged under-performance | demote Core → Moon Bag or exit on next rally |

> EPS biases exit readiness; DeadScore signals structural decay.  
> When cut-pressure high, raise E globally and demote high DeadScore assets.

---

## 6. Numeric Defaults (v1)

| Metric | Threshold | Meaning |
|---------|------------|---------|
| **Zone tolerance** | 0.5 × ATR(14, 15 m) | price proximity for TP zone |
| **VO_z climax** | ≥ +1.5 then drop | blow-off volume |
| **OBV roll-over** | ≤ –0.05 per 1 m bar (≥ 3 bars) | start of distribution |
| **Divergence window** | 10–20 bars by E-mode | exhaustion analysis |
| **EMA trail gap k** | Agg 0.25  /  Norm 0.40  /  Pat 0.60 | volatility buffer |
| **TP max per zone** | 2  | prevent over-trimming |
| **Moon-bag target** | 0.1 × max_alloc  | held until trend break |

---

## 7. Exit Flow Summary

on each PM tick:
if structural_fail: cut E1/E2
elif in resistance zone and exhaustion signals meet(E-mode thresholds):
execute TP(E-mode fraction)
elif trail_pending and adaptive_gap + momentum overlay confirm:
sell trend sleeve → retain moon bag
elif cut_pressure high:
raise E and apply EPS/DeadScore rotation

pgsql
Copy code

---

## 8. Guiding Principles

- **Sell where structure + exhaustion agree.**  
- **Let EMA trail capture the tail.**  
- **Preserve a moon-bag for asymmetric upside.**  
- **Escalate E with market stress; demote dead positions early.**

→ Enter on conviction.
→ Trim on exhaustion.
→ Exit on structure break.
→ Hold the essence.