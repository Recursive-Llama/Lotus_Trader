# LLM Research Layer Reboot

Purpose: re-spec the research layer so each “level” is a true goal with multiple sub-tasks, not a single prompt. This document captures (a) the concrete objectives we want to hit in v5 launch, and (b) the long-term vision of an embedded “researcher” that collaborates with the math/tuning system.

## Operating Principles
- **Edge-first**: every level should answer “Where is edge? Why? What should we test next?”.
- **Multi-step pipelines**: a “level” can have multiple prompts/tasks stitched together; each task should be narrowly defined (one input, one structured output).
- **Tight math loop**: every output must feed a consumer—dashboards, scope builder, tuning episodes, override generator.
- **Research agent model**: level 2+ should be able to fetch external context (Dexscreener, websites, GitHub, Twitter) and write structured findings back into Supabase.

---

## Level 1 – Edge Observatory
### Goal A (v5 launch): “Explain current edge”
- **Data**: aggregate `pattern_scope_stats` by different perspectives:
  - Global top edges (action_category + module).
  - Pattern-level (pattern_key + scope subset).
  - Dimension deltas (siblings that differ by exactly one dimension and have conflicting edge).
  - Edge decay snapshots (edge_over_time from `learning_edge_history` if available).
- **LLM tasks**:
  1. *Describe best/weak patterns* (structured list).
  2. *Explain deltas* (“A_mode flips edge between these scopes”).
  3. *Pose math questions* (SQL-ready tests for aggregators/tuning).
- **Output**: JSON stored in `llm_learning` *and* piped into dashboards/alerting.

### Goal B (vision): “Edge trend detection”
- Add math layer to detect new/decaying edges via edge history.
- LLM synthesizes trend reports (“Edge in low-cap AI entries has decayed 30% over past 2 weeks; check overrides.”).

---

## Level 2 – Semantic Researcher
### Goal A (v5 launch): “Structured semantic tagging”
- **Inputs**: positions table + Dexscreener token profiles.
- **Pipeline**:
  1. Fetch base metadata (symbol, chain, mcap, tags) via API.
  2. LLM classifies into canonical semantic factors (narrative/style/theme/catalyst). Store in `position_semantic_factors`.
  3. Attach factors to `pattern_scope_stats` as optional scope dimension (`semantic_meta`).
- **Consumers**: scope stats, PM overrides, dashboards.

### Goal B (vision): “Full token researcher”
- Extend to crawling websites/GitHub/Twitter to assess:
  - Release cadence, developer activity.
  - Narrative momentum (metas, runner/laggard relationships).
  - Curator discovery: detect which curator mentioned a successful meta early and recommend onboarding.
- Eventually support semantic clustering + vector search to group similar tokens.

---

## Level 3 – Structure Optimizer
### Goal A (v5 launch): “Scope delta analyzer”
- **Math pre-processing**:
  - For each pattern_key, enumerate scope siblings that differ by one dimension; compute edge difference + sample size.
  - Rank the most impactful dimensions (which dims flip edge sign or magnify edge).
- **LLM tasks**:
  1. Explain which dimensions matter and why (using stats + semantic factors).
  2. Suggest bucket re-splits or new scope dims (e.g., add `semantic_meta`).
  3. Identify overfit dims (dimensions that don’t move edge → candidates to drop).
- **Output**: proposals to adjust lesson scopes or bucket boundaries; feed them into lesson builder / override materializer queue for validation.

### Goal B (vision): “Dimension weighting”
- Combine deltas across many patterns to infer relative importance weights per dimension (e.g., A_mode > bucket_rank). Feed into lesson builder to prioritize dims when searching for scopes.

---

## Level 4 – Semantic Pattern Explorer
### Goal A (v5 launch): “Cross-domain pattern synthesis”
- Instead of legacy braids, treat *overrides/lessons* as the concrete patterns.
- LLM looks for surprising overlaps:
  - Same lever adjustments appearing in different pattern families.
  - Semantic-factor + scope combos with consistent effects.
- Output becomes candidate “meta-lessons” that tuning/tests can validate (“Both prediction-market S2 entries and low-cap AI entries prefer early trims when volatility bucket = high”).

### Goal B (vision): “Hypothesis feeder”
- Level 4 outputs automatically spawn Level 5 hypotheses (structured tests) focused on cross-domain patterns the math layer doesn’t already surface.

---

## Level 5 – Tuning Copilot
### Goal A (v5 launch): “Episode-aware hypotheses”
- Trigger Level 5 **after each tuning episode** (S1/S3 stage tuning):
  - Inputs: episode dataset (took/not took results, success/failure, counterfactual buckets, CF timestamps).
  - LLM tasks: propose concrete tuning adjustments to improve R/R (e.g., tighten entry delay for specific scope because CF data showed large missed RR).
- Outputs go into the tuning backlog; math layer auto-tests or flags them for review.

### Goal B (vision): “R/R maximizer”
- Expand beyond entries to trims/exits: analyze `cf_exit_improvement_bucket`, `could_exit_better`, etc.
- Integrate with a future “math hypothesis runner” that auto-executes the SQL/pattern queries LLM suggests and feeds results back (closing the loop).

---

## System Architecture Notes
- Each level can run multiple prompts/tasks; orchestrate via an internal workflow (e.g., `Level1Orchestrator.run()` calls `gather_stats()`, `describe_edges()`, `generate_questions()`).
- Introduce a scheduling/triggering layer:
  - Level 1 on cron (daily) plus on-demand when major edge shifts occur.
  - Level 2 continuous (per new position) plus periodic re-crawl.
  - Level 3/4 weekly after lesson builder runs.
  - Level 5 after each tuning episode.
- Define consumers per output so nothing sits idle in `llm_learning`.

