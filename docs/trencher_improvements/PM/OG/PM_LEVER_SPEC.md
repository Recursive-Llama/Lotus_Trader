⚘ Position Manager — Lever Model Spec (v3.2)
Purpose

Provide a simple, explainable control layer for portfolio-level exposure management.
The Position Manager (PM) does not predict markets; it modulates exposure and harvesting intensity based on context from the Learning System, market phase detector, and Decision Maker (DM).

0. Core Philosophy

Respond, don’t predict.
PM biases entry and exit intensity inside pre-defined zones.

Levers, not logic.
PM exposes tunable numeric levers that other systems learn to adjust.

Continuity, not switches.
A/E evolve smoothly with market phase, cut-pressure, and sentiment flow.

1. Lever Set (PM Controls)
Lever	Type	Range	Description
A_mode	float	0–1	Entry aggressiveness.
E_mode	float	0–1	Exit aggressiveness.
cut_pressure	float	0–1	Portfolio-level de-risk intensity; rises in late-cycle or overcrowded states.
harvest_bias	float	0–1	Bias toward partial exits; scales with E.
time_patience_h	set	{36, 72, 168}	Min hours to hold before re-evaluation gates.
trend_redeploy_frac	float	0.12 / 0.23 / 0.38	Fraction of realised proceeds re-deployed (by A-mode).
reentry_lock_h	int	36	Cooldown before re-entry (unless price < 0.7× last_exit + fresh trigger).
2. Inputs (Features / Context)
Feature	Type	Description
rsi_div	float	RSI vs price divergence strength (±1).
vo_z	float	Volume z-score vs 7-day mean.
sr_break	enum	bull / bear / null — diagonal or support break.
intent_metrics	object	Weighted signals per curator (buy / profit / sell / mocking).
residual_vs_majors	float	Portfolio or token performance vs majors (1h / 12h / 1d / 1w).
breadth_z	float	% tokens above EMA(1h) (z-scored).
age_h	float	Position age.
pnl_pct	float	Unrealised profit %.
usd_value	float	Position size.
liquidity_usd	float	Average 24h on-chain volume.
market_cap	float	Current MC.

All features cached in positions.features; PM loop stays light.

3. Portfolio Seesaw & cut_pressure
Targets

Ideal Core count = 12 (seesaw around 12 via tanh); above = contraction bias, below = expansion bias.

Phase Sensitivity
Regime	Focus	Primary Cuts	When	Adds	Notes
Dip / Double-Dip	Free liquidity pre-bottom	Overperformers still in profit	Immediately	High-intent only	Weak coins held for mean reversion.
Recover / Good	Rotate to strength	Weaker laggards failing to bounce	During early recoveries	Normal	Refresh capital to stronger trends.
Euphoria	Lock in profits	Trend leaders & stretched winners	Throughout	Only new launches / laggards	Heaviest trimming here.
Mechanics

cut_pressure modulates A/E but never forces sells.

A_final = A_policy × (1 − 0.33 × cut_pressure)
E_final = E_policy × (1 + 0.33 × cut_pressure)


Rising pressure → fewer adds, tighter exits.

Falling pressure → more adds, looser exits.

Goal: Breathe around 12 Cores; overflow converts passively to Moon Bags.

DeadScore Coupling
DeadScore_final = DeadScore × (1 + 0.3 × cut_pressure)


Harsher demotion tolerance during trimming phases.

4. Weakness Tracking
Rolling Metrics
WeaknessEMA = EMA(residual_vs_majors, 7d)
if residual_vs_majors < 0:
    weakness_days += 1
else:
    weakness_days = max(weakness_days - 1, 0)

Classification	Criteria	Action
Laggard	Weakness < 0 for ≤2 cycles; intent strong	Keep Core, eligible for re-adds
Weak Coin	Weakness < 0 for >3 cycles + rising DeadScore_final	Candidate for demotion when cut_pressure > 0.3
5. Entry Logic (per Mode)
Mode	Initial Deployment	Behaviour
Patient	10 % of DM cap	E1/E2 with 3 pillars; no fixed dip ladders.
Normal	33 %	E1/E2 with 2 pillars.
Aggressive	50 %	E1/E2 with 1 pillar; E2 allowed without E1 on trend discovery.

A_final defines how much of DM’s cap (e.g. 9%) to deploy now.
Remaining held for dip adds or trend re-entries.

6. Exit Logic (per Mode)
Mode	Slice of Remaining	Trail Tightness	Behaviour
Patient	10–15 %	EMA × 1.5	Zones + exhaustion; ≤ 2 per zone.
Normal	20–25 %	EMA × 1.0	Zones + exhaustion; ≤ 2 per zone.
Aggressive	30–40 %	EMA × 0.7	Zones + exhaustion; ≤ 2 per zone.

EMA Trail Stop

Trigger: 15 consecutive 1-min closes below EMA_long.

Action: Queue partial exit on first bounce.

If no reclaim within 6 bars, demote → Moon Bag.

Bounce = sell into strength.

Applies only when PnL > 0 (protect profit).

7. Intent Model (structured)
Signals
Type	Examples	ΔA	ΔE	Notes
High-Confidence Buy	adding_to_position, technical_breakout, fundamental_positive	+0.25	−0.10	Immediate entry bias
Medium-Confidence Buy	new_discovery, comparison_listed	+0.15	−0.05	Soft adds
Profit Intent	“took profit on 3×,” “trimmed half”	−0.15	+0.15	Cooling momentum; allow trend re-adds only
Sell / Negative	“sold all,” “team shady,” “avoid this”	−0.35	+0.45	Remove entries; exit if in profit; add +0.2 to DeadScore if red
Mocking / Derision	“dead coin,” “L project”	−0.25	+0.35	Immediate high-risk flag
Neutral / Educational	analysis / research	±0	±0	Ignored

No single composite score — all channel deltas summed & clamped (±0.4).

Source Synchrony
independent_source_count = distinct_curators_total
temporal_sync = stdev(time_gaps_last_10_mentions)


Rules:

count ≥ 3 and sync > 1d → A +0.05, E −0.05 (organic interest)

count ≥ 3 and sync < 0.5d → A −0.10, E +0.10 (herd risk)

8. DeadScore System
DeadScore = 
  0.4*(PnL < -30%)
+ 0.2*(VO < 0.5)
+ 0.2*(intent_strength < 0.2)
+ 0.2*(residual_pnl < -0.5)


Adjustments:

Underperformance on both rallies & sell-offs → +0.2

intent_divergence > 0.5 → sleeper override (hold)

macro negative & residual_pnl < −1.0 → trim

macro positive & residual_pnl < −1.0 → replace

Demotion rule:
DeadScore_final > 0.6 → convert Core → Moon (sell 70–90%)

9. Core vs Moon Bags
Type	Allocation Cap	Rules
Core Bag	≤ DM max_alloc (e.g. 9%)	Fully managed by A/E policy.
Moon Bag	≤ 0.3–0.5% each	Leftovers from trims/demotions; no adds; only sold on major pumps.

Promotion / Demotion:

Demote → Moon when DeadScore_final > 0.6 or EMA trend break confirmed.

Promote → Core when price reclaims EMA_long and intent_strength > 0.5 and phase_meso ∈ {Recover, Good}.

Moon Bags don’t count toward position limits.

10. Selection Policy for Trims

Eligible: age ≥ 36h, not re-entry locked.
Compute Exit Priority Score (EPS):

EPS =
  0.45*OverextensionZ +
  0.25*ResidualWeakness +
  0.15*(1 - intent_strength) +
  0.10*StaleAgeZ +
  0.05*LowVO


Phase bias:

Dip / Double-Dip: +0.3 bonus if OverextensionZ high → cuts overperformers first.

Recover / Good / Euphoria: +0.3 bonus if ResidualWeakness high → clears weak laggards.

Top-scoring positions are trimmed first when cut_pressure > 0.2.

11. Logging & Learning Hooks

Every decision emits a pm_decision strand:

Field	Example	Purpose
decision_type	add / trim / cut / hold / trail	Action taken
size_frac	0.33	Fraction of DM cap used (not % of portfolio)
A_value / E_value	0.42 / 0.73	Final computed modes
reasons[]	[rsi_div, intent_up, phase_recover]	Transparent causal trace
phase_state	{macro, meso, micro}	Context snapshot
forward_pnl_24h / 72h	placeholders	Backfilled later

Cadence: hourly tick + on-event triggers (exit, mention, demotion, phase flip).
Expected ~2–3 k strands/day — safe for Supabase.

12. Summary

PM keeps behaviour smooth, interpretable, and data-driven.

cut_pressure breathes the portfolio: expand below 12 Cores, contract above 26–36.

Weak coins demote gracefully; laggards survive.

RSI, volume, and intent jointly drive A/E; macro/meso/micro define timing.

EMA trails ensure profit exits happen on strength, never capitulation.

Nothing is forgotten — every trim, demotion, and “dead” coin remains on the waitlist for re-evaluation.

Philosophy:
“The PM doesn’t force the market; it listens to it breathe.”