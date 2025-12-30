# Scaling In & Scaling Out (Trims) - Detailed Analysis

## Overview

This document provides a comprehensive breakdown of how scaling in (adding to positions) and scaling out (trimming positions) works in the Lotus Trader system.

---

## 1. SCALING IN (Adding to Positions)

### 1.1 Entry Points & Triggers

The system scales into positions at three distinct entry points:

#### **S1 Entry (Initial Entry)**
- **Trigger**: `buy_signal = True` when state transitions from S0 → S1
- **One-time only**: Tracked via `pm_execution_history.last_s1_buy`
- **Purpose**: Initial position establishment
- **Location**: ```193:223:src/intelligence/lowcap_portfolio_manager/pm/actions.py```

#### **S2/S3 Entries (Add-on Entries)**
- **Triggers**:
  - `buy_flag = True` (S2 retest or S3 DX signal)
  - `first_dip_buy_flag = True` (S3 first dip after reclaim)
  - `reclaimed_ema333 = True` (S3 auto-rebuy after EMA333 reclaim)
- **Reset Conditions**: 
  - State transition (S2 ↔ S3)
  - Trim executed after last buy
- **Location**: ```874:1001:src/intelligence/lowcap_portfolio_manager/pm/actions.py```

### 1.2 Base Entry Sizes (A-Score Driven)

Entry sizes are determined by the **A-score (Aggressiveness)** and the **state**:

```python
# S1 Entries (Initial entries)
A >= 0.7 (Aggressive): 50% of remaining allocation
A >= 0.3 (Normal):      30% of remaining allocation
A < 0.3 (Patient):     10% of remaining allocation

# S2/S3 Entries (Add-on entries)
A >= 0.7 (Aggressive): 25% of remaining allocation
A >= 0.3 (Normal):      15% of remaining allocation
A < 0.3 (Patient):       5% of remaining allocation
```

**Location**: ```193:223:src/intelligence/lowcap_portfolio_manager/pm/actions.py```

### 1.3 Entry Multipliers (Profit-Based Adjustments)

Entry sizes are adjusted based on **profit ratio** (only for S2/S3, not S1):

```python
profit_ratio = total_extracted_usd / total_allocation_usd

if profit_ratio >= 1.0:
    entry_multiplier = 0.3  # 100%+ profit: smaller buys (take profits)
elif profit_ratio >= 0.0:
    entry_multiplier = 1.0  # Breakeven: normal buys
else:
    entry_multiplier = 1.5  # In loss: larger buys to average down
```

**Final Entry Size**: `base_entry_size * entry_multiplier`

**Location**: ```369:377:src/intelligence/lowcap_portfolio_manager/pm/actions.py```

**Example**:
- Base size: 15% (Normal A-score, S2 entry)
- Profit ratio: -0.2 (20% loss)
- Final size: 15% × 1.5 = **22.5%** of remaining allocation

### 1.4 Learning System Overrides (V5 Pattern-Based)

After calculating base size and multipliers, the system applies **pattern-based learning overrides**:

#### **Pattern Strength Overrides** (`pm_strength`)
- Adjusts `position_size_frac` based on learned pattern performance
- Range: 0.5x - 1.5x (clamped)
- **Only applies to entries**, not trims or exits

#### **Exposure Skew** (`exposure_skew`)
- Adjusts position size based on current exposure to similar patterns
- Prevents over-concentration
- **Only applies to entries**

#### **Final Multiplier**
```python
final_mult = pm_strength * exposure_skew
final_size_frac = base_size_frac * final_mult
```

**Location**: ```21:181:src/intelligence/lowcap_portfolio_manager/pm/actions.py```

**Important**: Learning overrides are **skipped** for:
- Emergency exits (always 100%)
- Trims (based on E-score only)

### 1.5 Execution Details

#### **Allocation Source**
- Uses `usd_alloc_remaining` (remaining capacity) for sizing
- Formula: `notional_usd = usd_alloc_remaining * size_frac`
- **Location**: ```1665:1674:src/intelligence/lowcap_portfolio_manager/pm/executor.py```

#### **Position Tracking Updates**
After execution:
- `total_quantity` += tokens_bought
- `total_allocation_usd` += notional_usd (cumulative)
- `total_tokens_bought` += tokens_bought
- `avg_entry_price` = total_allocation_usd / total_tokens_bought (weighted average)

**Location**: ```1531:1558:src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py```

#### **Execution History Tracking**
Records which signal triggered the buy:
- `last_s1_buy` (S1 initial entry)
- `last_s2_buy` (S2 retest)
- `last_s3_buy` (S3 DX signal)
- `last_reclaim_buy` (EMA333 reclaim)

**Location**: ```1664:1694:src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py```

---

## 2. SCALING OUT (Trimming Positions)

### 2.1 Trim Triggers

Trims are triggered by the **Uptrend Engine v4** when:

1. **State**: S2 or S3 (not S1 or S0)
2. **OX Score**: >= 0.65 (exhaustion/overbought signal)
3. **Price Position**: Within 1×ATR of a Support/Resistance level
4. **Flag**: `trim_flag = True`

**Location**: ```497:614:src/intelligence/lowcap_portfolio_manager/pm/actions.py```

### 2.2 Base Trim Sizes (E-Score Driven)

Trim sizes are determined by the **E-score (Exit Assertiveness)**:

```python
E >= 0.7 (Aggressive): 10% trim
E >= 0.3 (Normal):       5% trim
E < 0.3 (Patient):       3% trim
```

**Location**: ```226:241:src/intelligence/lowcap_portfolio_manager/pm/actions.py```

### 2.3 Trim Multipliers (Allocation Risk-Based)

Trim sizes are adjusted based on **allocation deployed ratio** and **profit ratio**:

```python
allocation_deployed_ratio = current_position_value / total_allocation_usd
profit_ratio = total_extracted_usd / total_allocation_usd

if allocation_deployed_ratio >= 0.8:
    trim_multiplier = 3.0  # Nearly maxed out: take more profit
elif profit_ratio >= 1.0:
    trim_multiplier = 0.3  # 100%+ profit: take less profit (let winners run)
elif profit_ratio >= 0.0:
    trim_multiplier = 1.0  # Breakeven: normal trims
else:
    trim_multiplier = 0.5  # In loss: smaller trims, preserve capital
```

**Final Trim Size**: `base_trim_size * trim_multiplier`

**Location**: ```379:389:src/intelligence/lowcap_portfolio_manager/pm/actions.py```

**Example**:
- Base trim: 5% (Normal E-score)
- Allocation deployed: 85% (nearly maxed out)
- Final trim: 5% × 3.0 = **15%** of position

### 2.4 Trim Cooldown Logic

Trims are **gated** to prevent over-trading:

#### **Cooldown Period**
- **3 bars minimum** between trims (timeframe-specific)
  - 1m timeframe: 3 minutes
  - 15m timeframe: 45 minutes
  - 1h timeframe: 3 hours
  - 4h timeframe: 12 hours

#### **S/R Level Change Override**
- Cooldown is **bypassed** if price moves to a different S/R level
- Threshold: 1% price difference from last trim's S/R level

#### **One Trim Per S/R Level**
- System tracks `last_trim_signal.sr_level_price`
- Only emits actionable trim when S/R level changes vs last signal
- Prevents duplicate trims at same level

**Location**: ```497:551:src/intelligence/lowcap_portfolio_manager/pm/actions.py```

### 2.5 Trim Hard Cap

Trims are **capped** to prevent full exits masquerading as trims:

```python
max_trim_frac = float(os.getenv("PM_MAX_TRIM_FRAC", "0.5"))  # Default: 50%
trim_size = min(trim_size, max_trim_frac)
```

**Location**: ```557:558:src/intelligence/lowcap_portfolio_manager/pm/actions.py```

### 2.6 Learning System Overrides (Trims)

**Important**: Learning overrides are **NOT applied to trims**:

```python
if decision_type == "trim":
    # Trim: skip learning factors (based on E-score only)
    size_mult = 1.0
    final_mult = 1.0
    # Keep original trim size_frac (from E-score calculation)
    action["size_frac"] = min(1.0, max(0.0, action.get("size_frac", 0.0)))
```

**Rationale**: Trims should be based purely on E-score and allocation risk, not learned pattern performance.

**Location**: ```127:132:src/intelligence/lowcap_portfolio_manager/pm/actions.py```

### 2.7 Execution Details

#### **Position Source**
- Uses `total_quantity` (current tokens held) for sizing
- Formula: `tokens_to_sell = total_quantity * size_frac`
- **Location**: ```1857:1865:src/intelligence/lowcap_portfolio_manager/pm/executor.py```

#### **Position Tracking Updates**
After execution:
- `total_quantity` -= tokens_sold
- `total_extracted_usd` += actual_usd (cumulative)
- `total_tokens_sold` += tokens_sold
- `avg_exit_price` = total_extracted_usd / total_tokens_sold (weighted average)

**Location**: ```1560:1577:src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py```

#### **Execution History Tracking**
Records trim execution:
- `last_trim.timestamp`
- `last_trim.price`
- `last_trim.size_frac`
- `last_trim.sr_level_price` (for cooldown logic)

**Location**: ```1696:1703:src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py```

---

## 3. EMERGENCY EXITS

### 3.1 Trigger Conditions

Emergency exits are **full exits** (100% of position) triggered by:

1. **`exit_position = True`**: Structural invalidation (e.g., price < EMA333)
2. **`emergency_exit = True`**: Critical signal from Uptrend Engine

**Location**: ```391:495:src/intelligence/lowcap_portfolio_manager/pm/actions.py```

### 3.2 Execution Details

- **Always 100%**: `size_frac = 1.0` (no multipliers, no learning overrides)
- **One per episode**: Gated via `last_emergency_exit_ts` to prevent re-spam
- **No cooldown**: Immediate execution when triggered

**Location**: ```122:126:src/intelligence/lowcap_portfolio_manager/pm/actions.py```

---

## 4. KEY METRICS & CALCULATIONS

### 4.1 Position Tracking Fields

| Field | Description | Updated On |
|-------|-------------|------------|
| `total_allocation_usd` | Cumulative USD invested | Every buy/add |
| `total_extracted_usd` | Cumulative USD extracted | Every trim/exit |
| `total_quantity` | Current tokens held | Every buy/sell |
| `total_tokens_bought` | Cumulative tokens bought | Every buy/add |
| `total_tokens_sold` | Cumulative tokens sold | Every trim/exit |
| `usd_alloc_remaining` | Remaining allocation capacity | Recalculated before decisions |
| `avg_entry_price` | Weighted average entry price | Every buy/add |
| `avg_exit_price` | Weighted average exit price | Every trim/exit |

### 4.2 Profit/Allocation Ratios

```python
# Profit ratio (for entry multipliers)
profit_ratio = total_extracted_usd / total_allocation_usd

# Allocation deployed ratio (for trim multipliers)
allocation_deployed_ratio = (total_quantity * current_price) / total_allocation_usd

# Remaining allocation
usd_alloc_remaining = (total_allocation_pct * wallet_balance) - (total_allocation_usd - total_extracted_usd)
```

**Location**: ```360:367:src/intelligence/lowcap_portfolio_manager/pm/actions.py```

### 4.3 P&L Calculations

```python
# Total P&L (God View)
total_pnl_usd = current_usd_value + total_extracted_usd - total_allocation_usd
total_pnl_pct = (total_pnl_usd / total_allocation_usd) * 100

# Realized P&L
rpnl_usd = total_extracted_usd - (total_tokens_sold * avg_entry_price)
rpnl_pct = (rpnl_usd / total_allocation_usd) * 100

# Unrealized P&L
unrealized_pnl_usd = current_usd_value - (total_quantity * avg_entry_price)
```

**Location**: ```1718:1812:src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py```

---

## 5. FLOW DIAGRAM

### Scaling In Flow

```
Uptrend Engine Signal (buy_signal/buy_flag)
    ↓
Check Execution History (cooldown/reset conditions)
    ↓
Calculate Base Entry Size (A-score + state)
    ↓
Apply Entry Multiplier (profit ratio)
    ↓
Apply Learning Overrides (pm_strength × exposure_skew)
    ↓
Execute Buy (usd_alloc_remaining × size_frac)
    ↓
Update Position (total_allocation_usd, total_quantity, etc.)
    ↓
Update Execution History (last_s1_buy, last_s2_buy, etc.)
```

### Scaling Out Flow

```
Uptrend Engine Signal (trim_flag: OX >= 0.65 + near S/R)
    ↓
Check Cooldown (3 bars OR S/R level changed)
    ↓
Check S/R Level Change (vs last signal)
    ↓
Calculate Base Trim Size (E-score)
    ↓
Apply Trim Multiplier (allocation deployed + profit ratio)
    ↓
Apply Hard Cap (max 50% trim)
    ↓
Execute Sell (total_quantity × size_frac)
    ↓
Update Position (total_extracted_usd, total_quantity, etc.)
    ↓
Update Execution History (last_trim with S/R level)
```

---

## 6. CONFIGURATION & TUNING

### Environment Variables

- `PM_MAX_TRIM_FRAC`: Maximum trim size (default: 0.5 = 50%)

### Tunable Parameters

1. **Entry Sizes**: Base percentages in `_a_to_entry_size()`
2. **Trim Sizes**: Base percentages in `_e_to_trim_size()`
3. **Entry Multipliers**: Profit ratio thresholds (1.0, 0.0)
4. **Trim Multipliers**: Allocation deployed threshold (0.8) and profit ratio thresholds
5. **Cooldown Period**: Bar count (currently 3 bars)
6. **S/R Level Threshold**: Price difference % (currently 1%)

### Learning System Integration

- **Pattern Strength Overrides**: Stored in `pm_overrides` table
- **Exposure Skew**: Calculated via `ExposureLookup` class
- **Scope Matching**: Based on state, timeframe, chain, curator, etc.

---

## 7. EDGE CASES & SAFEGUARDS

### 7.1 No Position for Trim
- System logs but doesn't execute if `total_quantity <= 0`
- Prevents errors from stale signals

### 7.2 No Remaining Allocation
- Entry blocked if `usd_alloc_remaining <= 0`
- Returns error: "No remaining allocation available"

### 7.3 Duplicate Signal Prevention
- S1: One buy per S1 state (tracked via `last_s1_buy`)
- S2/S3: Reset on state transition or trim
- Trims: Cooldown + S/R level change requirement

### 7.4 Emergency Exit Gating
- One emergency exit per episode (tracked via `last_emergency_exit_ts`)
- Prevents re-spam if flag doesn't clear immediately

---

## 8. SUMMARY

### Scaling In
- **Driven by**: A-score (aggressiveness) + profit ratio + learning overrides
- **Sizing**: Percentage of `usd_alloc_remaining` (remaining capacity)
- **Multipliers**: Profit-based (0.3x to 1.5x) + learning (0.5x to 1.5x)
- **Gating**: Execution history (one per signal type, reset on trim/transition)

### Scaling Out
- **Driven by**: E-score (exit assertiveness) + allocation risk + profit ratio
- **Sizing**: Percentage of `total_quantity` (current position)
- **Multipliers**: Allocation-based (0.3x to 3.0x)
- **Gating**: Cooldown (3 bars) OR S/R level change
- **Hard Cap**: 50% maximum trim size

### Key Differences
1. **Learning Overrides**: Applied to entries, **NOT** to trims
2. **Allocation Source**: Entries use `usd_alloc_remaining`, trims use `total_quantity`
3. **Multiplier Logic**: Entries use profit ratio, trims use allocation deployed + profit ratio
4. **Cooldown**: Trims have cooldown, entries have execution history gating

---

## 9. CODE REFERENCES

### Core Functions
- `plan_actions_v4()`: Main action planning logic
- `_a_to_entry_size()`: Base entry size calculation
- `_e_to_trim_size()`: Base trim size calculation
- `_apply_v5_overrides_to_action()`: Learning system integration
- `_count_bars_since()`: Cooldown calculation

### Execution
- `PMExecutor.execute()`: Main execution entry point
- `_execute_add()`: Buy execution
- `_execute_sell()`: Sell execution
- `_update_position_after_execution()`: Position tracking updates
- `_update_execution_history()`: Execution history tracking

### Key Files
- `src/intelligence/lowcap_portfolio_manager/pm/actions.py`: Action planning
- `src/intelligence/lowcap_portfolio_manager/pm/executor.py`: Execution
- `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`: Position management

