# Lotus Prediction Markets – Working Plan

Status: draft
Source: derived from `pred_market_rough.md` (brainstorm transcript); this is the canonical, curated plan.

---

## 1) Purpose and scope

- Define how Lotus operates on prediction markets (Polymarket first; others as fit).
- Translate brainstorm into pipelines we can implement, measure, and iterate.
- Keep this document operational: decisions, guardrails, and metrics live here.

---

## 2) Operating phases (context)

- Phase 1 (plumbing): copy-trade select signals; ensure execution, closing, accounting.
- Phase 2 (alpha): run our own strategies with clear data/logic, small capital.

This plan focuses on Phase 2 while acknowledging learnings from Phase 1.

---

## 3) Strategy map (canonical)

| strategy                              | description (short)                                        | venue fit (CLOB/AMM) | capital | risk   | horizon      | key edge                              |
| ------------------------------------- | ---------------------------------------------------------- | -------------------- | ------- | ------ | ------------ | ------------------------------------- |
| High-probability farming              | buy 95–99% near-certainty; exit early if possible          | CLOB                 | low     | low    | days–weeks   | ignored by size; micro-carry          |
| Long-dated underpricing (time-arb)    | buy long events mis-discounted; exit on repricing          | CLOB                 | medium  | low–m  | months–year  | crowd time-discount                   |
| Nowcasting                            | ingest live data → short-term probability updates          | CLOB                 | medium  | med    | hours–days   | speed + attention compression         |
| Information condensation              | slow info (filings/policy) → calibrated probability shifts | CLOB                 | low–m   | low    | days–weeks   | deeper context                        |
| Meta-prediction (repricing windows)   | trade expected market repricing; flat before resolution    | CLOB                 | low     | med    | hours–weeks  | attention/flow shifts                 |
| Non-exact/conditional arbitrage       | exploit mispriced correlations between related markets     | CLOB                 | med     | low–m  | days–weeks   | probabilistic reasoning               |
| Informational liquidity provision     | quote around our fair odds; earn fees + info edge          | CLOB/AMM             | low     | low–m  | ongoing      | calibration beats raw speed           |
| Reward/subsidy farming                | rotate where incentives are high                           | AMM                  | any     | low    | campaign     | auto-rotation                         |

Notes:
- “venue fit” indicates where the strategy is natively feasible first.
- We will prioritize small-ticket, low-liquidity niches suiting small bankrolls.

---

## 4) Pipelines (definition of done)

Each pipeline must specify:
- Inputs/signals
- Decision rule (entry/exit)
- Sizing limits and guardrails
- Execution venue/routing
- Metrics (expected vs realized EV, slippage, turnover)
- Review cadence and kill-switches

### 4.1 High-probability farming (core)
- Inputs: venue scanners; days-to-resolution; historical oracle/settlement incident rate; liquidity depth.
- Entry: buy YES/NO where EV ≫ fees + oracle/ops risk. Prefer exits at 98–99¢ when liquidity allows.
- Sizing: max 10% bankroll per event; max 30% aggregate in this pipeline.
- Exits: early at favorable prices or at resolution; auto-exit on rules/settlement dispute signals.
- Metrics: expected EV, realized EV, average hold days, exit slippage, dispute flags.

### 4.2 Informational LP (core)
- Inputs: Predictor fair odds + volatility; venue fee schedule; volume profile.
- Entry: provide narrow bands around our fair odds; widen when volatility spikes.
- Sizing: max 5% per market; max 20% pipeline.
- Exits: pull liquidity on venue outages, abnormal spreads, or realized IL > threshold.
- Metrics: fee yield, IL proxy, time-in-band, realized PnL vs passive benchmark.

### 4.3 Nowcasting (growth)
- Inputs: curated feeds (news/tweets/filings/on-chain); simple feature transforms.
- Decision: translate fresh signals into ∆probability; trade when mispricing > threshold.
- Sizing: small (1–3%) per event; hard stop on cumulative slippage/day.
- Metrics: latency-to-trade, edge decay vs time, realized EV, miss costs.

### 4.4 Meta-prediction windows (growth)
- Inputs: scheduled catalysts (debates, releases), historical repricing patterns.
- Decision: enter pre-catalyst, exit on target repricing band; avoid resolution risk.
- Metrics: expected move vs realized move, window hit-rate, exit quality.

### 4.5 Long-dated underpricing (opportunistic)
- Inputs: long-horizon markets; discount curve; narrative/attention decay.
- Decision: buy when model prob − market prob > threshold adjusted by lock-up time.
- Exits: sell on renewed attention or target repricing; cap lock-up exposure.
- Metrics: EV per month of lock-up, exit premia, drawdown control.

### 4.6 Conditional arbs (opportunistic)
- Inputs: candidate pairs/triples; joint probability model (Bayes/copula, simple first).
- Decision: enter when inconsistency > threshold net of fees; partial-fill hedging rules.
- Metrics: hedge efficiency, fill quality, correlation regime shifts.

---

## 5) Risk and guardrails (global)

- Per-pipeline allocation caps (default): core 30% each; growth 25% combined; opportunistic 20% combined; buffer 15%.
- Per-event cap: 5–10% max depending on pipeline risk.
- Venue exposure: max 50% per venue; halt on outage/settlement disputes.
- Kill-switches: daily PnL drawdown, slippage spike, data feed degradation, settlement/oracle incident.

---

## 6) Metrics and calibration (Alex)

- Prediction: probability, timestamp, source pipeline, confidence band.
- Trade: expected EV at entry, realized EV at exit, slippage, holding time, capital at risk.
- Scorekeeping: Brier/log loss (where applicable), calibration by market type, edge decay curves.
- Reviews: weekly pipeline scorecards; monthly reallocation based on realized edge.

---

## 7) Data and integrations

- Signals: curated feeds (news, filings, on-chain), wallet/identity trackers (later), venue APIs.
- Storage: append-only trade/prediction logs; feature snapshots around decisions.
- Interfaces: Predictor (probabilities), Trader (execution/routing), Alex (learning/reallocation).

---

## 8) Near-term prototypes (Phase 2 kick-off)

1) High-probability farming scanner + executor (small size, early exits at 98–99¢).
2) Meta-prediction for scheduled events (repricing window trades, flat by resolution).

Stretch: Informational LP on one venue with tight monitoring.

---

## 9) Open questions

- Minimal data we need live for nowcasting without overbuilding?
- How to standardize venue differences (fees, tick sizes, settlement quirks)?
- What’s our default dispute/oracle-risk haircut per venue?

---

Appendix: brainstorm source is `pred_market_rough.md`. As we port items in, keep this file the single source of truth for decisions and parameters.


