# ⚘ Portfolio Manager — Entry System v2.0

Unified entry logic for **all tokens**, applicable to both **new** and **known** assets.  
The structure defines **Immediate Probe**, **Envelope 1 (E1)** accumulation, and **Envelope 2 (E2)** breakout/retest entries, with complete signal, size, and cut logic.

---

## 1. Aggressiveness Modes

| Mode | Immediate | E1 (Support/Wedge) | E2 (Breakout/Retest) | Total Allocation | Notes |
|------|------------|-------------------|----------------------|------------------|-------|
| **Patient** | 0% | 5% | 5% | **10%** | Wait for full confirmation; skip probe. |
| **Normal** | 10% | 15% | 15% | **40%** | Balanced participation; base + breakout adds. |
| **Aggressive** | 15% | 35% | 50% | **100%** | Max conviction; full envelope fill. |

> **Immediate Probe:** skipped in *Patient* mode; always placed in *Normal* and *Aggressive* modes.  
> **E2 can be entered without E1** (for tokens already trending or newly detected mid-trend).

---

## 2. Momentum & Flow Sensitivity (by Mode)

### 2.1. Buy-Side Signal Strength

| Mode | OBV slope (rise) | VO_z confirmation | RSI divergence lookback | Condition rule |
|------|------------------|------------------|--------------------------|----------------|
| **Aggressive** | ≥ +0.05 over 3 bars | ≥ +1.2 | 10 bars | Any **one** pillar sufficient |
| **Normal** | ≥ +0.075 over 4 bars | ≥ +1.5 | 15 bars | Any **two** pillars required |
| **Patient** | ≥ +0.10 over 6 bars | ≥ +2.0 | 20 bars | All **three** pillars required |

Pillars = { OBV slope, VO_z, bullish or hidden bullish RSI divergence }

- More aggressive → looser requirements; acts early.  
- More patient → needs stronger and more synchronous confirmation.

---

## 3. Envelope 1 — Support / Wedge Accumulation

**Objective:** Begin building when price rests on key support or wedge base with bullish flow evidence.

### 3.1. Zone Definition
Valid E1 zone:
- Within ±1 × ATR(1m) of known **horizontal support** or **diagonal wedge base**.
- For horizontal zone clustering on the 15 m frame, prefer an ATR(15 m)-based band (e.g., ±0.5 × ATR(15 m)) over a flat % band (3% fallback if ATR is unstable).
- sr_conf ≥ 0.5 confirms structure validity (≥0.6 = strong).

### 3.2. Entry Trigger
E1 unlocks when:
- Structure is valid, and  
- Signal criteria (from §2.1) met.

#### Allocation Split (within mode)
1/3 of target allocation placed **at or near support**,  
2/3 reserved for **breakout confirmation** (E2).

| Mode | Add Size | Typical Behaviour |
|------|-----------|------------------|
| **Patient** | +5% (single clip) | Only on strong reversal confirmation |
| **Normal** | +15% (1–2 clips) | Accumulate at support or wedge base |
| **Aggressive** | +35% (1–3 clips) | Build actively within structure |

### 3.3. Undercut Logic
If price dips **below support** but:
- Flow & momentum **stay bullish** → add remaining E1 to catch reclaim.  
- Flow/momentum **flip bearish** → cut on first **retest from below**.

Channels as moving S/R (clarification): the lower channel bound may be treated as dynamic support for E1 accumulation when TA/flow align; the upper bound as dynamic resistance for trims/TPs. Channel breakouts are handled as E2 events when price exceeds the upper bound with confirmation.

### 3.4. E1 Cut Rules
| Trigger | Condition | Action |
|----------|------------|--------|
| **Support loss** | One 15 m close fully below support **and** no reclaim next 15 m bar | Cut full E1 tranche on first bounce |
| **Metric failure** | Any two of: OBV slope < −0.05 (3 bars), VO_z < −0.5, bearish divergence | Cut immediately on next micro bounce |
| **Macro hostility** | Macro phase ∈ {Oh-Shit, Double-Dip} | Freeze adds until recovery |

---

## 4. Envelope 2 — Breakout / Retest Add

**Objective:** Build position during breakout retrace or S/R flip with flow confirmation.

### 4.1. Breakout Identification
Let:  
- **B** = breakout line (diagonal or S/R flip)  
- **H** = local high of breakout leg before pullback  

Retracement ratio:
\[
r = \frac{H - \text{price}}{H - B}
\]

Valid E2 window: **r ∈ [0.68, 1.00]**  
→ i.e. retrace between **68%–100%** of breakout leg.

### 4.2. Confirmation
E2 can trigger when **structure + quick flow** confirm:
- VO_z ≥ +0.5 on breakout leg, or  
- OBV slope turns > 0 (positive inflection), or  
- RSI crosses above 50 **with divergence context bullish**.

### 4.3. Add Execution
| Mode | Add Size | Behaviour |
|------|-----------|-----------|
| **Patient** | +5% | Only on strong reclaim retest |
| **Normal** | +15% | Standard breakout retrace |
| **Aggressive** | +50% | Full conviction fill on first retrace |

> **E2 may occur without E1** for tokens already trending (late detection).

### 4.4. Cut Logic (E2)
| Trigger | Rule | Action |
|----------|------|--------|
| **Breakout failure** | Two consecutive 15 m closes below breakout line (B) | Cut full E2 tranche immediately |
| **Distribution reversal** | OBV slope < −0.05 3 bars + VO_z < 0 | Trim to E1 only |
| **Macro hostility** | Macro phase → hostile | Pause all adds |

---

## 5. Late Arrival / Trending Tokens

If first detection occurs **mid-trend**, skip E1.  
Treat next **diagonal/SR breakout + retrace** as E2 entry.  
Use the same flow, retrace, and cut rules as above.

### Hostile phases (Oh‑Shit / Double‑Dip) — entry gating (clarification)
- Do not hard-cap `A` to Patient. Global cut-pressure and stricter confirmation naturally suppress `A`.
- Freeze trend adds.
- Raise confirmation thresholds for new entries (require stronger pillars/VO_z per mode); only very strong new launches should clear gates.

---

## 6. Geometry & Context Layer

| Component | Purpose | Rule |
|------------|----------|------|
| **Fibonacci Anchors** | Context only | Always drawn **Top → Bottom** of visible range. Align support/resistance; not used for auto-orders. |
| **EMAs (Short/Long)** | Trend classification | Price > Short > Long = uptrend bias. EMAs **do not gate entries**, only guide trend bias and strength. |
| **OBV** | Flow polarity | Rising = bullish accumulation; ≈0 = neutral; falling = distribution. |
| **VO_z** | Flow intensity | +0.3 = moderate, +0.8 = strong. Used for quick confirmation. |
| **sr_conf** | Structure reliability | ≥0.5 valid, ≥0.6 strong. Weighted into E1 logic. |

---

## 7. Universal Cut Summary

| Trigger | Rule | Action |
|----------|------|--------|
| **Support lost** | 1× 15 m close below + no reclaim next bar | Cut E1 |
| **Metrics flip bearish** | 2+ of {OBV down, VO_z < −0.5, RSI divergence bearish} | Cut E1 |
| **Breakout failure** | 2× 15 m closes below breakout | Cut E2 |
| **Distribution pattern** | Upper wicks >0.6 body + VO_z high red + OBV falling | Trim to seed |
| **Macro phase mismatch** | Phase hostility (Euphoria/Dip misalignment) | Pause adds |

---

## 8. Key Numeric Defaults (v2)

| Metric | Threshold | Meaning |
|---------|------------|---------|
| **VO_z** | > +0.3 moderate / > +0.8 strong | Buy flow confirmation |
| **OBV slope** | ≥ +0.05 rising / ≤ −0.05 falling | Flow polarity |
| **RSI divergence lookback** | 10–20 bars (by mode) | Reversal detection |
| **sr_conf** | ≥ 0.5 valid / ≥ 0.6 strong | Structure reliability |
| **ATR proximity** | ±1 × ATR(1m) | Valid “at support” region |
| **Retrace window (E2)** | r ∈ [0.68, 1.00] | Breakout retest range |
| **Macro freeze** | Phase ∈ {Oh-Shit, Double-Dip} | No new adds |

---

## 9. Entry System Summary Table

| Envelope | Condition | Add Trigger | Cut Trigger | Flow/Momentum Thresholds | Typical Use |
|-----------|------------|-------------|--------------|--------------------------|--------------|
| **Immediate Probe** | New token signal (not Patient) | Instant 10–15% (per mode) | N/A | N/A | Initial exposure / watch mode |
| **E1 — Support/Wedge** | Price near support or wedge with ≥ required bullish pillars | +5/15/35% (Patient/Normal/Aggressive) | 1×15m close below + no reclaim / metrics flip | VO_z>+0.3, OBV≥+0.05, RSI divergence bullish | Accumulate at structural base |
| **E2 — Breakout/Retest** | Breakout + flow uptick + retrace r∈[0.68,1.00] | +5/15/50% | 2×15m closes below breakout | VO_z≥+0.5 or OBV uptick | Build into confirmed trend |
| **Trending Late Entry** | Already trending; use E2 logic | Same as E2 | Same as E2 | Same thresholds | Enter mid-trend without base |

---

## ✅ Core Principles

- **Act only when structure and flow agree.**  
- **Use geometry to guide, not dictate.**  
- **Adapt confirmation strength to mode.**  
- **Cut quickly when invalidated.**  
- **Keep the system universal:** same for new or known tokens; Patient mode simply waits longer.

