# V5 Tuning System Plan (Simplified Causal Model)

## 1. Philosophy: "The Simple Tuning System"

The goal is to tune the **specific levers** that caused us to Act or Skip, based on whether the outcome was Good or Bad.

We treat every "Opportunity" as a binary experiment:
1.  **Opportunity**: The Engine presented a setup (e.g., S1 Entry Zone, S3 Retest).
2.  **Decision**: We `Acted` (Bought) or `Skipped` (Filtered out).
3.  **Outcome**: The setup `Succeeded` (Went to Target) or `Failed` (Stopped out).

This gives us 4 causal quadrants:

| Decision | Outcome | Conclusion | Action |
| :--- | :--- | :--- | :--- |
| **Acted** | **Success** | "Good call." | **Reinforce**: Boost size/aggressiveness for this scope. |
| **Acted** | **Failure** | "False positive." | **Tighten**: Restrict entry gates (raise `ts_min`, lower `halo`). |
| **Skipped** | **Success** | "Missed opportunity." | **Loosen**: Lower entry gates (lower `ts_min`, widen `halo`). |
| **Skipped** | **Failure** | "Good dodge." | **Reinforce**: Keep gates tight (or tighten further). |

---

## 2. Fact Table: `pattern_episode_events`

We need a table to log these "Episodes" (Opportunities). This is distinct from the `pattern_trade_events` (which logs actual trades). This table logs **decisions** on **potential** trades.

### Schema Concept

```sql
CREATE TABLE pattern_episode_events (
    id BIGSERIAL PRIMARY KEY,
    
    -- Context
    scope JSONB NOT NULL,               -- Unified Scope (Chain, Mcap, Vol, Timeframe...)
    pattern_key TEXT NOT NULL,          -- "pm.s1_entry" or "pm.s3_retest"
    episode_id TEXT NOT NULL,           -- Unique ID for this specific window
    
    -- The Experiment
    decision TEXT NOT NULL,             -- 'acted' or 'skipped'
    outcome TEXT,                       -- 'success' (Target Hit) or 'failure' (Stop Hit). Null if pending.
    
    -- Causal Factors (Why did we Act/Skip?)
    -- We capture the *values* of the gates at the moment of decision.
    factors JSONB NOT NULL,             
    -- Example: { 
    --   "ts_score": 65, "ts_min": 60,      -> Passed TS gate
    --   "dist_to_ema": 0.5, "halo": 1.0    -> Passed Halo gate
    -- }

    timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

### Capture Logic

#### A. S1 Entry Episode
*   **Start**: Engine enters `S1` (Transition from S0).
*   **End**: Engine exits `S1` (to `S0` or `S2/S3`).
*   **Decision Point**: The first time `buy_flag` is True (or if it never becomes True).
*   **Outcome**:
    *   **Success**: Reached **S3** (Trend Established) OR Reached **S2** with Profitable Trim.
    *   **Failure**: Returned to **S0** without reaching S3/Trim.

#### B. S3 Retest Episode
*   **Start**: Engine is in `S3` AND `buy_flag` becomes True (EMA333 Retest Window).
*   **End**: `buy_flag` becomes False (Price moves away or State changes).
*   **Decision Point**: Did we emit an `add` or `entry` order during this window?
*   **Outcome**:
    *   **Success**: A **Trim** signal occurred *before* State went to **S0**.
    *   **Failure**: State went to **S0** (Trend Broken) *before* any profitable Trim.

---

## 3. The Miner: Calculating Rates

The "Miner" (Lesson Builder) runs periodically (e.g., daily) to aggregate these episodes. It doesn't calculate "Edge" in the PnL sense; it calculates **Hit Rates** and **Miss Rates**.

For a given Scope (e.g., `Solana + Micro + 1h`):

1.  **Win Rate (`WR`)**: `Count(Acted & Success) / Count(Acted)`
    *   *Are our trades working?*
2.  **False Positive Rate (`FPR`)**: `Count(Acted & Failure) / Count(Acted)`
    *   *Are we buying garbage?*
3.  **Miss Rate (`MR`)**: `Count(Skipped & Success) / Count(Skipped)`
    *   *Are we filtering out winners?*
4.  **Dodge Rate (`DR`)**: `Count(Skipped & Failure) / Count(Skipped)`
    *   *Are our filters saving us?*

---

## 4. The Judge: Materializing Tuning Overrides

The "Judge" (Materializer) looks at these rates and creates **Tuning Overrides**. These are stored in a new `pm_tuning_overrides` table (or similar) and acted upon by the PM.

### Logic

*   **Scenario 1: High Miss Rate (> 60%)**
    *   *Problem*: We are skipping too many good trades.
    *   *Action*: **Loosen Gates**.
    *   *Target*: Check `factors` in the skipped episodes.
        *   If most skips were due to `ts_score < ts_min`, then **Lower `ts_min`**.
        *   If most skips were due to `dist > halo`, then **Increase `halo_multiplier`**.

*   **Scenario 2: High False Positive Rate (> 50%)**
    *   *Problem*: We are buying too many losers.
    *   *Action*: **Tighten Gates**.
    *   *Target*:
        *   **Raise `ts_min`**.
        *   **Decrease `halo_multiplier`**.

*   **Scenario 3: High Win Rate (> 70%)**
    *   *Problem*: Things are working great.
    *   *Action*: **Aggression**.
    *   *Target*: **Increase `A_value`** (Position Sizing).

### Storage (pm_overrides extension)

We can use the same `pm_overrides` table, but with different `action_category` or `key`.

*   `pattern_key`: `pm.tuning.s1_gates`
*   `scope_subset`: `{ "chain": "solana" }`
*   `multiplier`: This might need to be a JSON blob for specific params, or we map "multiplier" to specific levers.
    *   *Proposal*: Use `features` or `params` column in `pm_overrides` for non-scalar overrides. Or just stick to scalar multipliers for `ts_min` and `halo`.

    *   **ts_min_mult**: `0.9` (Loosen) -> `base_ts * 0.9`
    *   **halo_mult**: `1.2` (Loosen) -> `base_halo * 1.2`

---

## 5. Implementation Plan

### Phase 1: Episode Logging (The Fact Table)
1.  Create `pattern_episode_events` table.
2.  Update `PMCoreTick` to track "Episodes" (S1 windows, S3 windows).
3.  Log `decision='acted'` when an order is sent.
4.  Log `decision='skipped'` when a window closes without action.
5.  Update `process_position_closed` (or similar) to backfill `outcome` for pending episodes.

### Phase 2: The Miner
1.  Create `TuningLessonBuilder`.
2.  Query `pattern_episode_events`.
3.  Group by Scope.
4.  Calculate WR, FPR, MR, DR.
5.  Store "Tuning Lessons" (Rates) in `learning_lessons` (with `type='tuning'`).

### Phase 3: The Judge
1.  Create `TuningMaterializer`.
2.  Read "Tuning Lessons".
3.  Apply Logic (Miss Rate -> Loosen, FPR -> Tighten).
4.  Write overrides to `pm_overrides` (e.g., `ts_min_mult`, `halo_mult`).

### Phase 4: Runtime
1.  Update `PMCoreTick` / `UptrendEngine` to read these overrides.
2.  Apply `ts_min_mult` to `check_buy_signal`.
3.  Apply `halo_mult` to `check_buy_signal`.

