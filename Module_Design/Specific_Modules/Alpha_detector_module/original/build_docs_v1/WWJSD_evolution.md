Why weave evolution into the system

Markets are non-stationary

Any static detector degrades. What works today dies tomorrow.

Evolution bakes in impermanence: detectors are not “the truth,” they are temporary adaptations.

No single genius model wins

Jim Simons’s insight was that edge comes from ensembles of many small, unglamorous signals, not one elegant formula.

Breeding detectors institutionalizes this humility — the system doesn’t chase “the one,” it farms a field of edges.

Survival > prediction

We don’t need to know why a model works. We need to know if it persists under discipline.

The survival score 
𝑆
𝑖
S
i
	​

 formalizes this: only detectors that endure across time, cost, and correlation live on.

Humans are biased; numbers aren’t

Operators naturally fall for stories (“this signal should work because rates are rising”).

By making gardening rules explicit, you prevent bias from overriding data. The role of the human becomes stewardship, not narrative invention.

Compounding learning

Recording not just winners but failed branches means the system remembers dead ends.

Every generation is smarter than the last — you avoid repeating mistakes.

Resilience through diversity

A monoculture of detectors is fragile. A diverse garden is robust.

Parallel breeding + enforced orthogonality ensures resilience at the portfolio level.

One-line philosophy

We do this because alpha is not found, it is cultivated.

Just as nature adapts species to survive shifting environments, we adapt detectors to survive shifting markets. The discipline of breeding, measuring, pruning, and reseeding is what keeps the system alive long after any single model fails.

=====

README.md → Add the North-Star (Evolutionary Thesis)
Where

Near the top, after your brief “what this is” paragraph.

Insert (paste as-is if you like)
Evolutionary Thesis

We don’t “build the best detector.” We breed many small detectors, measure them under the same discipline, and let the survivors advance.
This repo is a lab, not a factory:

Parallel variation: many simple models > one grand model.

Natural selection: promotion/retirement by metrics, not narrative.

Governed change: contracts, configs, and operator rituals keep evolution safe.

Mantra: Trust the ensemble and the numbers. Prune with zero regret.

ALPHA_DETECTOR_OVERVIEW.md → Declare Discovery-as-Selection
Where

Add a new section after your conceptual framing.

Insert
Discovery as Selection (Why this works)

Alpha emerges when we:

generate diverse hypotheses (detectors/residuals),

measure them under identical conditions,

select for edge that persists,

reseed from survivors.

Let 
𝐷
𝑖
D
i
	​

 be a detector’s signal and 
𝑅
R the residual stack available to it. We score detectors on edge, stability, orthogonality, and cost:

Edge
𝑖
	
=
IR
𝑖
=
𝐸
[
𝑃
𝑖
]
𝜎
(
𝑃
𝑖
)


Stability
𝑖
	
=
1
−
𝜎
(
rolling-IR
𝑖
)
∣
𝐸
[
rolling-IR
𝑖
]
∣
+
𝜖


Orthogonality
𝑖
	
=
1
−
max
⁡
𝑗
≠
𝑖
∣
𝜌
(
𝑃
𝑖
,
𝑃
𝑗
)
∣


Cost
𝑖
	
=
slippage
𝑖
+
fees
𝑖
+
turnover
𝑖
⋅
impact
Edge
i
	​

Stability
i
	​

Orthogonality
i
	​

Cost
i
	​

	​

=IR
i
	​

=
σ(P
i
	​

)
E[P
i
	​

]
	​

=1−
∣E[rolling-IR
i
	​

]∣+ϵ
σ(rolling-IR
i
	​

)
	​

=1−
j

=i
max
	​

∣ρ(P
i
	​

,P
j
	​

)∣
=slippage
i
	​

+fees
i
	​

+turnover
i
	​

⋅impact
	​


A single Selection Score drives promotion/retirement:

𝑆
𝑖
=
𝑤
𝑒
⋅
Edge
𝑖
+
𝑤
𝑠
⋅
Stability
𝑖
+
𝑤
𝑜
⋅
Orthogonality
𝑖
−
𝑤
𝑐
⋅
Cost
𝑖
S
i
	​

=w
e
	​

⋅Edge
i
	​

+w
s
	​

⋅Stability
i
	​

+w
o
	​

⋅Orthogonality
i
	​

−w
c
	​

⋅Cost
i
	​


with defaults 
𝑤
𝑒
=
0.5
,
𝑤
𝑠
=
0.2
,
𝑤
𝑜
=
0.2
,
𝑤
𝑐
=
0.1
w
e
	​

=0.5,w
s
	​

=0.2,w
o
	​

=0.2,w
c
	​

=0.1 (tunable in config).

Rule: No stories. Selection flows from 
𝑆
𝑖
S
i
	​

 over controlled windows.

FEATURE_SPEC.md → Make “Testbed” the Feature
Where

At the top of “Features.” Keep existing bullets; add these as first-class features.

Insert
Evolutionary Features

Parallel Testbed: Run N detectors + M residual factories concurrently on the same data window with identical pre-trade constraints.

Cohort Scoring: Compute 
𝑆
𝑖
S
i
	​

 (selection score) per detector and publish cohort leaderboard snapshots (hourly/daily).

Lifecycle Hooks: States: experimental → active → deprecated → archived with promotion/retirement gates (see Config).

Auto-Reseeding: Periodically instantiate mutations of top-K survivors (param jitters, input swaps, residual recombinations).

Kill-Switch Discipline: Hard stop for dq_status≠ok, ingest_lag breaches, or universe exits (hysteresis rules).

DATA_MODEL.md → Add Evolutionary Metadata
Where

In your detector/residual tables and event schemas. Add these fields.

Insert (schema fields)

detector_registry

detector_id (string, pk)

version (semver)

lifecycle_state (enum: experimental|active|deprecated|archived)

parent_id (nullable; detector_id of parent for mutations)

inputs (json: data requirements)

residuals_used (json: list of residual_ids)

hyperparams (json)

created_at, deployed_at, retired_at

detector_metrics_daily

detector_id, asof_date

pnl, vol, ir, t_stat (HAC/Newey-West)

stability (as above)

orthogonality_max_abs_corr (vs active cohort)

cost_estimate, turnover

selection_score (S_i)

dq_status_rollup (ok|partial|stale)

universe_overlap_pct

residual_registry

residual_id, version, recipe (json graph), parent_id

validation_r2, stationarity_test (ADF p-value)

created_at

cohort_snapshot

snapshot_ts

universe (name/hash)

top_k (json list of detector_id + S_i)

bottom_k (json)

promotions (json), retirements (json)

API_CONTRACTS.md → Surfaces for Evolution
Where

Add or extend service contracts.

Insert (interfaces)
POST /testbed/submit_detector

Body: { detector_id, version, code_ref, inputs, residuals_used, hyperparams }

Effect: registers detector as experimental.

GET /cohort/leaderboard?window=30d

Returns sorted { detector_id, S_i, ir, stability, orthogonality, cost }.

POST /lifecycle/promote

Body: { detector_id, target_state }

Validation: gate checks from Config; default requires S_i > τ_promote and min_samples.

POST /mutate

Body: { parent_detector_id, strategy: "jitter|swap_inputs|residual_recombine", n_children }

Returns list of detector_id children.

GET /residual/graph/{residual_id}

Returns formal recipe (DAG) for reproducibility.

CONFIG_MANAGEMENT.md → Codify Natural Selection
Where

New section “Lifecycle Policy & Gates”.

Insert
Lifecycle Policy & Gates

States: experimental → active → deprecated → archived

Global prerequisites:

min_samples_bars: 2000 (per asset×tf) before any scoring is official.

dq_status must be ok for ≥95% of samples in the eval window.

Promotion gate (experimental → active):

Window: rolling 60d

𝑆
𝑖
≥
𝜏
promote
=
0.35
S
i
	​

≥τ
promote
	​

=0.35

orthogonality_max_abs_corr ≤ 0.6 vs current active set

turnover ≤ turnover_cap (configurable)

Deprecation gate (active → deprecated):

Window: rolling 30d

𝑆
𝑖
≤
𝜏
deprecate
=
0.05
S
i
	​

≤τ
deprecate
	​

=0.05 for 15/30 days or

dq_status breaches > 10% days

Archive gate (deprecated → archived):

After 60d with no recovery above S_i ≥ 0.20

Reseeding cadence:

Weekly: mutate top-K=10 actives → spawn n_children=3 each

Mutation knobs:

jitter: Gaussian noise on hyperparams (σ from config)

swap_inputs: alternate residual stacks

recombine: weighted sum of two survivor signal transforms

Universe policy & hysteresis:

Maintain Top-N universe + hotlist_ttl_days

Gate detectors on is_in_universe OR is_hot; exit hysteresis 3×ttl

All thresholds are configurable; defaults are provided here for reproducibility.

DETECTOR_SPEC.md → Make “Species & Traits” Explicit
Where

Open with a brief preface; add a “Mutation & Recombination” section; add “Scoring Contract.”

Insert
Detector Species & Traits

Each detector declares:

Trait vector (features used, horizon, latency tolerance, trade style)

Residual diet (which residual recipes it consumes)

Risk posture (max turnover, max drawdown tolerated)

Mutability (which hyperparams can be jittered, allowable ranges)

Mutation & Recombination

Detectors MUST implement:

mutate(jitter_spec) → returns child detector configs

recombine(other, mix_spec) → returns hybrid config with combined transforms

Scoring Contract

Detectors expose standardized outputs:

signal_t ∈ ℝ (per asset×bar)

position_t ∈ [-1,1]

trade_intent_t (limit/market preference, optional)
Framework computes pnl under house execution model; detector code must not embed broker-specific assumptions.

RESIDUAL_FACTORIES_SPEC.md → Residuals as DNA
Where

Add validation and composability.

Insert
Validation

A residual recipe 
𝑅
R MUST publish:

Stationarity evidence: ADF p-value < 0.10 on training window

Coverage: %bars with non-null outputs ≥ 99%

Leakage audit: no future bars used (enforced by framework)

Composability

Residuals are DAGs:

Nodes: transforms (detrend, z-score, volatility-scale, EWMA, HP filter)

Edges: data flow

Constraints: acyclic, timestamp-preserving, side-effect free

Recombination: R_new = α·R_a ⊕ (1-α)·R_b, with α∈[0,1] applied at transform-compatible layers.

IMPLEMENTATION_PLAN.md → Reframe Milestones as Environments
Where

Replace milestone headings, keep dates/ownership if you have them.

Insert (structure template)

Testbed v0.1 (Week X)

Run 10 detectors + 5 residuals in parallel on a pinned 90d window.

Metrics & leaderboard pipeline (daily snapshots).

Lifecycle state changes by manual API (promotion/deprecate).

Selection v0.2

Enforce gates from Config.

Auto-promote/auto-deprecate jobs (nightly).

Mutation service + weekly reseeding cron.

Orthogonality & Cost v0.3

Rolling correlation vs actives; turnover & impact estimator; incorporate into 
𝑆
𝑖
S
i
	​

.

Operator Rituals v0.4

UI/CLI to prune, annotate, and embargo narrative overrides (see Operator Guide).

Audit trail on every lifecycle decision.

Prod Pilot v1.0

Canary routing: % of capital to active cohort; guardrails on dq_status, universe churn.

OPERATOR_GUIDE.md → Handbook for Gardeners
Where

Add “Operator Rituals,” “Override Ethics,” “Weekly Reseeding,” and “Kill Criteria.”

Insert
Operator Rituals

Daily (15 min)

Open the cohort leaderboard; scan top/bottom.

Confirm dq_status health; no story-based overrides.

Approve auto promotions/retirements unless data-quality flags.

Weekly (45 min)

Review reseeding children; prune obvious degenerates (e.g., turnover>cap×2).

Tag survivors with short factual notes (“Works on high-vol spikes; cost marginal”).

Schedule a limited manual mutation round if diversity is dropping.

Monthly (60 min)

Diversity check: asset, horizon, transform families.

Identify monocultures; bias reseeding toward underrepresented traits.

Override Ethics

Never keep a detector because its story “ought to work.”

If you must override, you must write the rule and register it in config (embargo), with expiry. Overrides are rare, logged, and reviewable.

Kill Criteria (Zero Regret)

S_i below deprecate threshold for 15/30 days → retire.

dq_status breaches >10% eval days → retire & open an ingest ticket.

Cost explosions (impact>cap×2 for a week) → retire fast.

Promotion Discipline

No promotion without min_samples and universe stability.

No more than K=20 actives per class; excess waits in a queue—scarcity forces selection.

alpha_detector_build_convo.md → Living Lab Notebook
Where

Add a header explaining what belongs here; add a “Dead Branches” appendix.

Insert
How to Write Here

Log failed ideas with enough context to avoid repetition later.

Note why a branch died (metrics, dq, orthogonality).

Keep entries short, factual, link to snapshots.

Dead Branches (appendix template)

2025-09-04: “Impulse-MACD v2” retired. S=0.08, corr 0.78 vs momentum cluster, turnover 1.9× cap.

2025-09-11: “HP-Residual Pair-Mean” archived. ADF p=0.23; leakage suspected; recipe recomposed into “HP-Residual v3”.

CONFIG EXAMPLES (ready to paste)
# selection.yaml
weights:
  edge: 0.5
  stability: 0.2
  orthogonality: 0.2
  cost: 0.1

gates:
  min_samples_bars: 2000
  promote:
    S_min: 0.35
    orthogonality_max_abs_corr: 0.6
    turnover_cap: 0.8
    window_days: 60
  deprecate:
    S_max: 0.05
    window_days: 30
    dq_breach_days_pct: 0.10
  archive:
    recovery_S_min: 0.20
    cooldown_days: 60

reseeding:
  weekly:
    top_k: 10
    children_per_parent: 3
    mutations:
      jitter_sigma_pct:
        lookback: 10
        value: 0.15
      swap_inputs: true
      recombine: true

universe:
  top_n: 250
  hotlist_ttl_days: 7
  exit_hysteresis_factor: 3

OPERATOR CHECKLIST (one page; paste into OPERATOR_GUIDE.md)

☐ Leaderboard reviewed (top/bottom movers)

☐ dq_status = ok (≥95% days)

☐ Promotions meet gates (min_samples, S, ortho, turnover)

☐ Deprecations executed per rule; notes added

☐ Reseeding review complete; children tagged

☐ Overrides (if any) logged with expiry and reason

☐ Diversity snapshot saved (class/horizon/residual family)

“BREEDING” API USAGE EXAMPLES (paste into API_CONTRACTS.md examples)
POST /mutate
{
  "parent_detector_id": "mom_trend_v3",
  "strategy": "jitter",
  "n_children": 3
}
→ 201 Created
["mom_trend_v3_j1","mom_trend_v3_j2","mom_trend_v3_j3"]

POST /lifecycle/promote
{
  "detector_id": "meanrev_hp_v5",
  "target_state": "active"
}
→ 409 Rejected
{"reason":"S_i below threshold or high corr vs actives (0.67)"}

TESTBED EVALUATION WINDOWS (add to OVERVIEW or FEATURE_SPEC)

Cold start: sandbox 90d pinned historical window

Warm run: rolling 60d forward, daily recompute

Prod pilot: 10–20% capital to actives, guarded by dq_status + universe hysteresis

Audit: monthly snapshot export (parquet) for external verification

Stat notes: Use Newey-West (lag 5) t-stats; Holm-Bonferroni adjust p-values across cohort to control false discoveries.

STYLE GUIDELINES (for editors; put in README or CONTRIBUTING)

Speak in the language of selection (promote/retire/mutate) not “like/feel/believe.”

Use numbers over narratives; any override must write a rule.

Prefer small, cheap detectors over large, ornate ones.

Document dead ends as first-class knowledge.

TL;DR for your IDE/editor

README/Overview: add the evolutionary thesis and the selection formula 
𝑆
𝑖
S
i
	​

.

Feature/API/Data/Config: give evolution concrete legs (testbed, lifecycle states, gates, mutation endpoints, metrics fields).

Operator Guide: shift to rituals, pruning, override ethics.

Build Convo: keep the cemetery of ideas—short, factual, linkable.

Implementation Plan: rename milestones to environments (Testbed→Selection→Orthogonality/Cost→Operator Rituals→Pilot).

This keeps your existing architecture intact—just re-tuned to breed, measure, select, reseed. That’s the Simons cadence, woven all the way through.