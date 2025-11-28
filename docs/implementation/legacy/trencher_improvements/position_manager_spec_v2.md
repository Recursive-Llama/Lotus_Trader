# Position Manager – Lever Model Spec (v2)

## Purpose
Keep PM simple: PM pulls levers and makes small, explainable decisions. Complexity (signals, patterns, archetypes) lives outside and flows in as context.

## Core Philosophy
- PM does not predict; it responds.
- Entries/exits are zones; PM biases sizes in those zones.
- Levers are explicit and tunable; Learning tunes them over time.

## Lever Set (PM controls)
- aggressiveness_mode: patient | normal | aggressive
- cut_pressure: 0.0–1.0
- harvest_bias: 0.0–1.0 (higher = more partial exits)
- time_patience_h: {36, 72, 168}
- trend_redeploy_frac: 0.10 | 0.15 | 0.25 (by mode; can decouple later)
- reentry_lock_h: 36 (override with discount + trigger)

## What PM reads (features/context)
- rsi_div (bool)
- vo (float)
- sr_break: bull | bear | null (diagonal/support break)
- mention_rate: up | down | null; sentiment_tag: celebratory | negative | null
- residual_vs_majors D (simple divergence), breadth/mood (portfolio_mode)
- age_h, pnl_pct, usd_value, liquidity_usd, market_cap

Features are cached into positions.features by a worker; PM loop stays light.

## Portfolio Bands & Rules
- Soft band ≥ 30: begin trims progressively (reduce count; don’t rush)
- Hard band > 34: must reduce (target ≈ 33)
- 36h do‑not‑touch for losers (profit-taking exempt); 72h checkpoint = re‑evaluate (not auto‑exit)
- Reopen lock 36h unless price ≤ 0.70 × last_exit AND fresh trigger (divergence or diagonal break)

## Entries (zones) by mode
- Patient: 10% upfront; dip adds at −38% and −60%; conservative trend‑adds
- Normal: 33/33/33 at instant/−20%/−38%
- Aggressive: 50% upfront; −23.6% then −38%; more aggressive trend‑adds

Optional: fit dip levels to nearest support (future; v1 uses fixed percentages).

### Immediate on‑book target (F_now)
- F_now(mode) defines immediate live exposure as a fraction of DM max allocation:
  - Patient: 0.10
  - Normal: 0.33
  - Aggressive: 0.50
- On A_mode increase (e.g., Normal→Aggressive), PM tops up to target_now = F_now×max_alloc immediately; reserves remain for ladders/trend.
- On A_mode decrease, PM does not force market‑sells; it freezes new adds and lets exits/trails bleed excess (soft‑trim via larger exit slices/tighter trails).

## Exits (levels unchanged; PM biases sizing)
- Patient: fewer partial harvests per level; wider trailing
- Normal: current harvest sizes
- Aggressive: earlier partial harvest on fast thrusts; tighter trailing after large moves
- Trend entries from exits: redeploy ~10/15/25% by mode; gate by sr_break/mentions

## Trend Entry Lever
- On exit execution, PM evaluates trend add:
  - Check sr_break != bear and mention_rate != down (or strong rsi_div)
  - Allocate trend_redeploy_frac of proceeds; v1 same mode as entry; future decouple allowed

## Market Modes (portfolio_mode)
Cycle (timeframe = hours→days): Dip → Double‑dip → Oh‑shit → Recover → Good → Euphoria.
- Dip/Double‑dip: favor deploying (with TA confirmations); trim only overextended winners
- Oh‑shit: pause adds; only pulse entries
- Recover: lighten on pops; add selective new coins for quick wins
- Good: take profits sooner; be selective on adds
- Euphoria: harvest more; slow new adds; wait‑list

PM uses portfolio_mode to bias aggressiveness and cut_pressure; Learning will refine.

## Selection Policy for Trims (v1)
- Eligible set: age ≥ 36h (losers protected by DNT), not reentry‑locked
- Prefer profitable, smallest USD first; if insufficient, include oldest low‑VO/liquidity
- Log selection set and reasons for learning to replace this heuristic later

## Mentions & Intent Data
- Canonical: curator_signals rows (intent_type, intent_confidence, mentions_1h/24h, token, chain, ts)
- Position index: append to positions.curator_sources {curator_id, signal_id, intent_type, ts, is_primary}
- PM consumes mention_update events; positions row remains compact

## New Token Backfill
- One‑shot OHLCV (≤ 1000 candles) per new token to seed VO/ATR/ROC (Birdeye free tier)
- We start lowcap_price_data_1m post‑creation; backfill bridges early window

## Strands (PM I/O)
Inputs:
- decision_lowcap (from DM)
- price_tick (minute rollup)
- mention_update (from Ingest)
- portfolio_event (soft/hard band)
- time_gate (36/72/168h)
- exit_created (trend check)

Outputs:
- pm_decision {add|trim|cut|hold|trail, size_pct, reasons[]}
- pm_plan {mode, pacing, ladders, trend_frac}
- pm_log {decision + feature snapshot + forward_pnl placeholders}

## Triggers & Cadence
- 60s tick; event‑driven preferred when available
- Price dips (−20/−23.6/−38/−60), exits, mentions, bands, time gates

## Logging for Learning
- Persist reasons keys: rsi_div, sr_break_bear/bull, vo_low/high, mention_up/down, sentiment tags, portfolio_mode, age_gate_passed, profitable_smallest, weak_liquidity
- Backfill forward_pnl_24h/72h

## Notes
- “New independent high‑confidence sources” (e.g., adding_to_position, technical_breakout, fundamental_positive, strong research_positive) can nudge A/E: ΔA ≈ +0.05 each (cap +0.20), ΔE ≈ −0.03, decaying toward 0 over ~24h; dedupe correlated sources. Under Micro Euphoria the decay window may be shorter.

## Archetypes → Lever Presets (future via Learning)
- Strong Trender → high aggressiveness, low cut, high patience, medium harvest
- Early Hype/Dip → normal aggressiveness, low cut, medium patience, low harvest
- Hidden Sleeper → patient, very low cut, high patience, none harvest
- Dead Coin → n/a aggressiveness, high cut, none patience
- Fakeout → low aggressiveness, high cut, short patience, high harvest
- Rotation → patient, low cut, high patience, low harvest

## Open Items
- Whether trend-entry mode can decouple from entry mode in v1
- Exact thresholds for weak VO/liquidity filter
- Residual vs majors computation cadence; breadth definition
