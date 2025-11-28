Position Manager v3.2 Operator’s Cheat Sheet — a single, dense reference that distills every rule, lever, and interaction from the full spec.

It’s formatted as a quick-access table for live ops, debugging, or training the Learning System.

⚘ Position Manager — Operator’s Cheat Sheet (v3.2)
1️⃣ Core System Overview
Layer	Role	Key Variables
Decision Maker (DM)	Sets per-token max allocation cap (e.g. 9 %)	max_alloc
Position Manager (PM)	Decides what fraction to deploy & how to harvest	A_mode, E_mode, cut_pressure
Trader / Executor	Executes trades based on PM outputs	size_frac × max_alloc
2️⃣ Lever Summary
Lever	Range	Purpose	Controlled By
A_mode	0–1	Entry aggressiveness (size & speed)	Phase + RSI + Volume + Intent
E_mode	0–1	Exit aggressiveness (harvest intensity)	Phase + EMA + Intent + cut_pressure
cut_pressure	0–1	Global contraction / expansion bias	Core count + market phase
trend_redeploy_frac	0.12 / 0.23 / 0.38	% of realised profits redeployed	A_mode
reentry_lock_h	36	Cooldown before re-buy unless strong discount trigger	Fixed
3️⃣ Portfolio Structure
Band	Definition	Behaviour
Underexposed (< 12 Cores)	Too few holdings	A ↑, E ↓ (deploy capital)
Ideal (12)	Target seesaw point	Neutral; modulation via cut_pressure only
Moon Bags	0.3–0.5 % each	No adds, only harvests on major pumps
4️⃣ Phase & cut_pressure Interaction
Phase	Market Feel	cut_pressure Bias	Trim Focus	Add Policy
Dip	Early weakness	Medium	Overperformers	Waitlist only
Double-Dip	Renewed fear	Medium	Overperformers	Light probes
Oh-Shit	Capitulation	Low	None (deploy zone)	Aggressive buys
Recover	Rebound	Medium	Weak laggards	Aggressive trend adds
Good	Stable strength	Medium-High	Stale laggards	Normal adds
Euphoria	Blow-off	High	Overextended winners	Only laggards/new launches
5️⃣ Entries, Exits, Trail (no fixed ladders)
Entries: E1 (support/wedge) and E2 (breakout/retest) with mode-based pillars (patient 3, normal 2, aggressive 1). E2 allowed without E1 on trending discovery.
Exits: Zone + exhaustion trims inside resistance (two standard or one strong), ≤2 trims per zone, moon-bag guard.
Trail: profit-only; trigger after 15 × 1m closes below EMA_long and sell on the bounce; if no reclaim within 6 bars demote to Moon (70–90%).

6️⃣ DeadScore System
Component	Weight	Trigger	Notes
PnL < −30 %	0.4	Deep loss	Not instant; part of composite
VO < 0.5	0.2	Low activity	
Intent < 0.2	0.2	Weak social support	
Residual < −0.5	0.2	Sustained underperformance	
Bonus (dual weak on rallies & dumps)	+0.2	Broad weakness	
Override (intent ↑ but price ↓)	hold	Sleeper candidate	
Phase Mod (cut_pressure)	× (1 + 0.3 × cut_pressure)	Late-cycle harsher	
Threshold	> 0.6 → demote Core → Moon (sell 70–90 %)		
7️⃣ Weakness & Lagging Logic
Metric	Description	Window	Action
WeaknessEMA	EMA(Residual_vs_Majors)	7 d	Rolling relative strength
weakness_days	Consecutive days residual < 0	Dynamic counter	
Laggard	< 0 for ≤ 2 Meso cycles	Keep Core; monitor for mean reversion	
Weak Coin	< 0 for ≥ 3 cycles + rising DeadScore	Candidate for demotion	
8️⃣ Intent Model Weights
Type	ΔA	ΔE	Meaning
High-Confidence Buy	+0.25	−0.10	Strong add trigger
Medium Buy	+0.15	−0.05	Soft add
Profit Intent	−0.15	+0.15	Cooling, allow trend re-adds
Sell / Negative	−0.35	+0.45	Remove entries, exit if profit
Mocking / Derision	−0.25	+0.35	Immediate high-risk flag
Neutral	±0	±0	Ignore
Synchrony Modifiers
Condition	ΔA	ΔE	Signal
≥ 3 curators, spread > 1 d	+0.05	−0.05	Organic interest
≥ 3 curators, spread < 0.5 d	−0.10	+0.10	Herd risk
9️⃣ Cut-Pressure Coupling to A/E
Variable	Formula	Effect
A_final	A_policy × (1 − 0.33 × cut_pressure)	Dampens new adds
E_final	E_policy × (1 + 0.33 × cut_pressure)	Tightens harvesting
DeadScore_final	DeadScore × (1 + 0.3 × cut_pressure)	Faster demotions when trimming

11️⃣ Core ↔ Moon Rules
Direction	Trigger	Action
Core → Moon	DeadScore_final > 0.6 or EMA trend break	Sell 70–90 %; demote
Moon → Core	EMA reclaim + intent > 0.5 + phase_meso ∈ {Recover, Good}	Promote & reopen A/E control
Moon Count	Unlimited	Excluded from core limits
12️⃣ Logging & Learning
Field	Example	Purpose
decision_type	add, trim, cut, hold, trail	Trade action
size_frac	0.33	Fraction of DM cap used
A_value / E_value	0.48 / 0.72	Final levers
reasons[]	[rsi_div, intent_up, phase_recover]	Transparency
phase_state	{macro, meso, micro}	Context snapshot
forward_pnl_24h / 72h	—	For learning feedback

Emission: hourly + event-based.
Price data tick = 60 s; PM decision cadence = ≈ 1 h or phase change.

13️⃣ Quick Behaviour Map
Situation	A Behaviour	E Behaviour	Outcome
Too many Cores (36+)	Shrinks	Tightens	Gradual rotation to Moon
Too few (< 12)	Expands	Loosens	Rapid redeploy
Weak Market (Dip)	Patient	Aggressive	Exit winners, prep laggards
Panic (Oh-Shit)	Aggressive	Aggressive	Deploy hard, trim rebounds
Recovery	Max Aggressive	Medium	Expand trends, recycle capital
Euphoria	Mixed (Aggressive new / Patient old)	Medium	Ride winners, harvest tops
Essence

cut_pressure: breath of the portfolio
DeadScore: immune system
A/E: heartbeat
Intent & Volume: nervous system
Phase Detector: circadian rhythm

All work together to make the portfolio breathe, rotate, and survive.


Excellent — here’s the Position Manager v3.2 System Diagram in text form, ready to render as a schematic (mermaid, draw.io, Figma, or Notion diagram block).
It visualizes how information, levers, and decisions flow through the PM layer.
You can drop this directly into your docs under PM_v3.2_schematic.md.

⚘ Position Manager — System Diagram (v3.2)
                    ┌────────────────────────────────────┐
                    │            DECISION MAKER           │
                    │  (sets max_alloc per token, e.g. 9%)│
                    └────────────────────────────────────┘
                                     │
                                     ▼
                 ╔═════════════════════════════════════╗
                 ║        POSITION MANAGER (PM)        ║
                 ║  "Responds, not predicts"           ║
                 ║  — Controls exposure and harvesting ║
                 ╚═════════════════════════════════════╝
                                     │
       ┌─────────────────────────────┼─────────────────────────────┐
       ▼                             ▼                             ▼
┌───────────────┐         ┌────────────────────┐        ┌──────────────────────┐
│ MARKET INPUTS │         │ MEMORY + INTENT DB │        │ PORTFOLIO CONTEXT    │
│ (Price, RSI,  │         │ (Curator signals,  │        │ (Core count, PnL,    │
│ Volume, Phase)│         │ Mentions, VO)      │        │ residuals, breadth)  │
└───────────────┘         └────────────────────┘        └──────────────────────┘
       │                         │                             │
       └────────────┬────────────┴────────────┬────────────────┘
                    ▼                         ▼
             ┌────────────────────────────────────────────┐
             │ FEATURE FUSION / CONTEXT AGGREGATOR         │
             │ - rsi_div                                   │
             │ - vo_z, residual_vs_majors                  │
             │ - sr_break (bull/bear/null)                 │
             │ - intent_weights (buy/sell/mock)            │
             │ - breadth_z / macro-meso-micro phases       │
             └────────────────────────────────────────────┘
                                │
                                ▼
                 ┌────────────────────────────────────┐
                 │   LEVER COMPUTATION ENGINE         │
                 │   (Smooth continuous modulation)   │
                 ├────────────────────────────────────┤
                 │ A_final = A_policy×(1–0.5×cut_p)   │
                 │ E_final = E_policy×(1+0.5×cut_p)   │
                 │ DeadScore_final = D×(1+0.3×cut_p)  │
                 │ trend_redeploy_frac by A_mode       │
                 └────────────────────────────────────┘
                                │
                                ▼
                ╔══════════════════════════════════╗
                ║   PORTFOLIO ACTION DECISION LOOP ║
                ║   (runs hourly + on triggers)    ║
                ║   Evaluates:                     ║
                ║     - New adds                   ║
                ║     - Trims / Cuts               ║
                ║     - Trend re-deploys           ║
                ║     - Demotions / Promotions     ║
                ╚══════════════════════════════════╝
                                │
                                ▼
                     ┌────────────────────────┐
                     │  TRADE EXECUTION LAYER │
                     │ (Trader / Executor)    │
                     │ Converts size_frac →   │
                     │ actual on-chain trades │
                     └────────────────────────┘
                                │
                                ▼
                ┌────────────────────────────────────────────┐
                │  STRAND LOGGING + LEARNING BACKFEED         │
                │  Every decision → pm_decision strand        │
                │    {phase_state, reasons[], forward_pnl}    │
                │  Learning Engine refines thresholds, weights│
                └────────────────────────────────────────────┘


💠 System Flow Summary
Flow	Description
1. Data Intake	Market (price, RSI, volume), memory (intent, VO), and portfolio (PnL, core count) feed into feature fusion.
2. Feature Fusion	Signals merged into a unified context: RSI divergence, VO, intent polarity, residual vs majors, phase states.
3. Lever Computation	PM translates context into live control levers: A_final, E_final, cut_pressure, DeadScore_final.
4. Decision Loop	Every hour (and on major triggers), PM decides: add, trim, cut, trail, or hold.
5. Trade Execution	Trader layer turns fractional decisions into real allocations within DM cap.
6. Strand Logging	Every PM action → strand with reasons + forward PnL for Learning.
7. Learning Feedback	Learning system updates lever tuning, thresholds, and archetype presets.
🜂 Phase-to-Lever Coupling Summary
Phase	A Bias	E Bias	cut_pressure	Behaviour
Dip	↓	↑	0.4	Cut leaders, prep laggards
Double-Dip	↓	↑	0.5	Light adds, trim overperformers
Oh-Shit	↑↑	↑↑	0.2	Deploy hard, scalp rebounds
Recover	↑↑	→	0.3	Trend adds resume
Good	→	↓	0.4	Hold winners, slow harvests
Euphoria	↑/↓	↑	0.6	Reduce risk, stop trend entries
🌕 Weak Coin Lifecycle
       underperforming
             │
             ▼
     +-------------------+
     | WeaknessEMA < 0   |
     | weakness_days +1  |
     +-------------------+
             │
     (1–2 cycles) laggard → kept Core
             │
     (3+ cycles + rising DeadScore)
             ▼
        demotion candidate
             │
      cut_pressure > 0.3 ?
             │
        YES → convert → Moon
             │
        NO  → monitor


Re-entry path:
Intent ↑ + Residual flip + phase_meso ∈ {Recover, Good} → promote back to Core.

🜃 System Philosophy (summary glyph)
    PHASE → POLICY → POSITION → LEARNING
       │        │         │        │
       ▼        ▼         ▼        ▼
     Δφ        ψ(ω)      φ_res     ρ_feedback

    "Lotus breathes with the market:
     inhale on fear, exhale on euphoria."
