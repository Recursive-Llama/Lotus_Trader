# ⚘ Portfolio Manager — Trend-Redeploy System v1.0

Trend-redeploys re-add exposure **after partial take-profits**, using the **same entry envelopes** (E1/E2) when the underlying trend remains intact.  
They recycle realised proceeds to grow position size within an ongoing structure — never adding new risk.

---

## 1. Purpose

- **When:** After at least one TP has been executed on the same token.  
- **Why:** To re-increase size early in an ongoing trend while maintaining tight structural protection.  
- **What:** Treat the redeploy as a *fresh entry cycle* (E1/E2) governed by the same rules and aggressiveness logic.

---

## 2. Activation Conditions

A trend-redeploy window opens only when all of the following are true:

| Condition | Requirement | Notes |
|------------|--------------|-------|
| **Same-coin TP event** | A take-profit executed on this token with realised proceeds available | Time since TP irrelevant |
| **Structure intact** | No EMA_long or diagonal break since last TP; price still above EMA_long | Confirms trend continuity |
| **Macro supportive** | Phase ∈ {Recover, Good, Euphoria} | Avoid redeploying into hostile phases |
| **DeadScore < 0.4** | Token remains healthy | Mainly a sanity check; rarely fails when structure intact |

If **EMA_long is lost**, the position reverts to a **Moon-Bag state**.  
No redeploys occur until a new E1/E2 cycle begins (fresh trend re-entry).

---

## 3. Redeploy Sizing

Redeploy allocations are **fractions of realised proceeds**, scaled by current **A-mode** aggressiveness.

| A-mode | Fraction of realised proceeds | Behaviour |
|---------|-------------------------------|------------|
| **Patient** | 12 % | Minimal reinforcement |
| **Normal** | 23 % | Balanced continuation |
| **Aggressive** | 38 % | Strong trend reinforcement |

> Redeployed capital merges into the active position (average entry recalculated).  
> Net portfolio risk does **not** increase — only recycled gains are used.

---

## 4. Timing & Trigger Logic

### 4.1. Base Criteria

Redeploys trigger only when:
1. **Price has retraced ≥ 23.6 %** from the last local high **or**  
   **≥ 36 hours** have passed since the TP (trend “reset” window), and  
2. **Structure remains intact** (price ≥ EMA_long, sr_break ≠ bear), and  
3. **Flow confirms strength**, using the same E1/E2 logic:

| Pillar | Requirement (per §2.1 of Entry System) |
|---------|----------------------------------------|
| **Momentum divergence** | Bullish or hidden bullish (RSI/OBV) |
| **OBV trend** | OBV slope ≥ +0.05 (mode-dependent) |
| **VO_z** | VO_z ≥ +0.3 (moderate) / +0.8 (strong) |
| **Structure confidence** | sr_conf ≥ 0.5 (≥ 0.6 strong) |

If these conditions align at support or along EMA_long → treat as **E1 trend add**.  
If a fresh breakout + retest appears → treat as **E2 trend add**.

---

## 5. Execution Zones

| Redeploy Type | Zone Definition | Add Size |
|----------------|-----------------|-----------|
| **E1-Trend Add** | Around EMA_long or structural support (± 1 ATR) | Use E1 add size for current A-mode (5 % / 15 % / 35 %) |
| **E2-Trend Add** | New breakout retrace (68–100 % of new impulse) | Use E2 add size for current A-mode (5 % / 15 % / 50 %) |

> These use *identical cut rules* to normal entries.  
> Invalidations are **not tighter** — same support/breakout failure logic applies.

---

## 6. Invalidation & Cut Rules

| Trigger | Rule | Action |
|----------|------|--------|
| **EMA_long break** | 15 m close below EMA_long + no reclaim next bar | Cut redeploy portion; revert to moon-bag |
| **Structure fail** | sr_break = bear or diagonal break confirmed | Cut redeploy tranche |
| **Flow reversal** | OBV slope < −0.05 (3 bars) + VO_z < 0 | Trim redeploy first |
| **Macro hostility** | Phase → Dip / Double-Dip | Pause redeploy logic until recovery |

All cuts reuse the base E1/E2 logic from the Entry System.

---

## 7. Integration into PM Flow

on TP strand confirmed:
if structure_intact and macro_supportive:
open trend_redeploy window
if E1/E2 conditions met:
size = redeploy_frac(A-mode) × realised_proceeds
emit trend_add strand (E1 or E2 type)
else:
log no_redeploy (learning)
else:
skip; wait for fresh E1/E2 cycle

yaml
Copy code

---

## 8. Behaviour Summary

| Scenario | Expected Behaviour |
|-----------|-------------------|
| **Strong uptrend, shallow retrace** | Redeploy triggers near EMA; adds continuation size |
| **Sharp blow-off + EMA hold** | Wait 36 h or ≥ 23.6 % pullback before redeploy |
| **EMA break or diagonal fail** | No redeploy; treat as moon-bag phase |
| **Fresh breakout** | Use E2 logic for redeploy entry |
| **Weak flow post-TP** | Skip redeploy; hold profits |

---

## 9. Core Principles

- **Reinvest strength, not weakness.**  
- **Never exceed prior risk; recycle only what was earned.**  
- **Structure intact → same rules apply.**  
- **If it breaks, treat it as a new trend entirely.**

→ Redeploy when trend breathes in.
→ Cut if breath turns to exhale.
→ Always within the same rhythm.