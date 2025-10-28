# Position Manager Architecture

## Overview

This document outlines the architecture for a Position Manager module that provides simple, intelligent position management through two core functions: portfolio size management and position scaling decisions.

## Core Architecture

### Position Manager Module
**Purpose**: Simple position management with two core jobs:
1. **Which positions to cut** when approaching portfolio limits
2. **How aggressive to be** on scaling into existing positions

**Data Sources**:
- Positions table (current positions, performance, allocation)
- Learning System context injection (aggressiveness modes, timing insights)

**Key Principle**: Keep the PM simple - complexity comes from the Learning System providing intelligent context

## Core Functions

### 1. Portfolio Size Management
**Current Problem**: At 34 positions → sell 6 smallest (causes churn, bad timing)

**PM Solution**: Smarter position cutting rules
- **Bands/Triggers**:
  - Soft band ≥ 30: begin progressive trims (reduce number of positions; do not rush)
  - Hard band > 34: must reduce (bring count back toward 33)
  - Time gates: 36h do-not-touch for trims on losers (profit-taking exempt); 72h checkpoint (re-evaluate, candidate halve)
  - Re-entry lock: no reopen within 36h unless new entry ≤ 0.70 × last_exit and fresh trigger
  
- **Selection (v1)**:
  - Prefer trimming profitable positions first; among them, smallest USD value first
  - If shortfall: include oldest positions with weak volume/liquidity
  - Definition of "trim": reduce or close positions to lower total count (not per-position size micro-trims)

**Future Enhancement**: Learning System provides context about timing and recovery patterns

### 2. Position Scaling Decisions
**Current Problem**: Fixed 33% on all entries (instant, -38%, -60%)

**PM Solution**: Adjust aggressiveness based on context
- **Modes (entry pacing)**:
  - Patient: 10% upfront; dip buys at −38% and −60%; conservative trend adds
  - Normal: 33/33/33 across instant, −20%, −38% (use −20% instead of −23.6% for simplicity v1)
  - Aggressive: 50% upfront; include −23.6% as first dip, then −38%; more aggressive trend adds

- **Trend entries (on exits)**:
  - Reallocate a fraction of exit proceeds into trend entries by mode:
    - Patient: ~10%
    - Normal: ~15%
    - Aggressive: ~25%
  - Mode may differ for re-entries later (v1: same as entry mode; future: LS can override)

**Future Enhancement**: Learning System provides context about which mode to use

## Triggers and Cadence

- Tick: evaluate every 60 seconds (aligned to lowcap_price_data_1m)
- Event-driven:
  - Decision approved (from Decision Maker)
  - Mention updates (new/strong intent, mention_rate delta, celebratory/negative)
  - Portfolio bands (≥30 soft, >34 hard)
  - Time gates (36h/72h checkpoints)
  - Price dip thresholds (−20/−23.6/−38/−60) and exit-created (trend-buy checks)

## Integration with Other Modules

### Decision Maker → Position Manager
- **Decision Maker**: "Buy this token, 6% allocation, base entries 33% each"
- **Position Manager**: Gets context from Learning System about aggressiveness mode
- **Position Manager**: Adjusts entry strategy (50% upfront for aggressive, 10% for patient)

### Learning System → Position Manager
- **Context Injection**: "This curator + research intent = aggressive mode"
- **Context Injection**: "This position type tends to recover after 48 hours"
- **Position Manager**: Uses context to make smarter decisions

## Entries, Exits, and Trend Entries (Zones)

- PM treats entries and exits as zones, not single points. It biases sizes within zones using simple features (v1) and mode.
- Entries (by mode):
  - Patient: 10% upfront; dip adds at −38% and −60% only
  - Normal: 33/33/33 at instant/−20%/−38%
  - Aggressive: 50% upfront; −23.6% then −38%

- Exits (levels unchanged; PM adjusts how much to realize):
  - Patient: fewer partial harvests per level; wider trailing
  - Normal: current harvest sizes
  - Aggressive: earlier partial harvest on fast moves; tighter trailing after thrusts

- Trend entries (after exits):
  - Reallocate fraction of exit proceeds: ~10% patient / ~15% normal / ~25% aggressive
  - Gate trend adds by simple feature flags (e.g., avoid if bear SR break and mention down)

## Minimal Signals/Features PM Reads (v1)

- rsi_div: boolean RSI–price divergence flag
- vo: volume oscillator (~EMA1h/EMA24h from lowcap_price_data_1m)
- sr_break: 'bull' | 'bear' | null (simple diagonal/support break flag)
- mention_rate: 'up' | 'down' | null (from curator_signals delta)
- sentiment_tag: 'celebratory' | 'negative' | null
- portfolio_mode: Dip / Double‑dip / Oh‑shit / Recover / Good / Euphoria (coarse)

These may be cached on each position (features JSONB) by a lightweight worker.

## Data Backfill for New Positions

- For new tokens (no history yet), perform a one‑shot OHLCV backfill (≤1000 candles) to seed VO/ATR/ROC for early decisions. Stay within Birdeye free tier.

## Market Context Bias (v1 minimal)

- Define portfolio_mode from SOL/ETH/BNB and breadth to bias levers:
  - Dip / Double-dip / Oh-shit / Recover / Good / Euphoria (timeframe can be hours–days)
  - Use this to bias aggressiveness and cut pressure (e.g., deploy on dip/double-dip with confirmations; harvest more in euphoria)

## Definitions

- Trim (in bands context): action to reduce the number of active positions (typically by closing smaller profitable positions first). Aim is count management, not micro‑resizing every holding.
- Re-entry lock: do not reopen within 36h unless price ≤ 0.70 × last_exit and a fresh trigger (divergence or diagonal break) is present.

## Implementation Strategy

### Phase 1: Simple Position Manager
- Implement soft/hard bands; 36h trim DNT for losers; 72h checkpoint (log-only action); 36h re-entry lock with discount rule
- Implement aggressiveness modes (patient/normal/aggressive) incl. ladders and trend reallocation fractions
- Connect to existing position/price data; keep entries/exits/trend entries in current JSONB columns

### Phase 2: Learning System Integration
- Learning System provides context injection
- Position Manager uses context for smarter decisions
- Monitor and optimize based on results

## Key Questions to Resolve

1. **Position Cutting Rules**: What are the best simple rules to start with?
2. **Aggressiveness Modes**: How many modes? What are the parameters?
3. **Context Integration**: How does PM receive and use Learning System context?
4. **Trigger Thresholds**: What position counts trigger different actions?

## Success Metrics

- Reduced position churn (fewer buy/sell cycles)
- Better timing on position cuts (not selling at bad times)
- Improved position scaling (more aggressive when appropriate)
- Smarter portfolio management (keeping winners, cutting deadweight)
- Reduced manual intervention

---

*This document will be updated as we refine the architecture and implementation details.*
