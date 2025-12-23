# Executor Logging Analysis & Flow Mapping

**Date**: 2025-12-11  
**Goal**: Map all execution flows, identify logging gaps, and understand why emergency exits don't always trigger reclaims

---

## 1. Decision Types & Execution Flow

### Decision Types
1. **`entry`** - First buy (position status: watchlist → active)
2. **`add`** - Subsequent buys (position already active)
3. **`trim`** - Partial exit (sell fraction of position)
4. **`emergency_exit`** - Full exit (sell 100% of position)
5. **`hold`** - No action (not executed, no strand)

### Execution Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. UPTREND ENGINE (uptrend_engine_v4.py)                       │
│    - Computes EMA states (S0, S1, S2, S3)                      │
│    - Sets flags: buy_signal, buy_flag, trim_flag,             │
│      emergency_exit, reclaimed_ema333                           │
│    - Writes to: features.uptrend_engine_v4                     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. PLAN ACTIONS (pm/actions.py - plan_actions_v4())            │
│    - Reads engine flags + position state                        │
│    - Applies A/E scores, multipliers, cooldowns                  │
│    - Checks execution history (prevents duplicates)             │
│    - Returns: List[Action] or []                                │
│                                                                  │
│    Priority Order:                                               │
│    1. exit_position → emergency_exit (100%)                     │
│    2. emergency_exit flag → emergency_exit (100%)               │
│    3. trim_flag → trim (if cooldown expired)                   │
│    4. buy_signal/buy_flag → entry/add                           │
│    5. reclaimed_ema333 → add (auto-rebuy)                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. EXECUTE (pm/executor.py - execute())                         │
│    - Validates decision, position, chain                        │
│    - Gets latest price                                          │
│    - Executes swap (Jupiter for Solana, Li.Fi for others)       │
│    - Returns: {status, tx_hash, tokens, price, slippage, ...} │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. UPDATE POSITION (pm_core_tick.py - _update_position_after_) │
│    - Updates total_quantity, total_allocation_usd, etc.         │
│    - Updates status (watchlist ↔ active)                         │
│    - Recalculates P&L fields                                    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. UPDATE EXECUTION HISTORY (pm_core_tick.py - _update_exec_) │
│    - Records last_s1_buy, last_s2_buy, last_s3_buy, etc.        │
│    - Records last_trim, last_emergency_exit_ts                   │
│    - Records last_reclaim_buy                                    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. SEND NOTIFICATION (pm_core_tick.py - _send_execution_notif_) │
│    - Telegram notification (non-blocking)                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. CHECK POSITION CLOSURE (pm_core_tick.py - _check_position_)  │
│    - If state == S0 AND total_quantity == 0                     │
│    - Closes position, computes R/R, writes completed_trades     │
│    - Sends position summary notification                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Emergency Exit Flow Analysis

### S3 Emergency Exit Flow

**Step 1: Emergency Exit Flag Set**
- **When**: Price < EMA333 (in S3)
- **Action**: `emergency_exit = True` (flag only, state stays S3)
- **Logging**: ✅ `"S3 EMERGENCY EXIT: price < ema333"`
- **What Happens Next**: `plan_actions_v4()` sees `emergency_exit = True` → returns `emergency_exit` action

**Step 2: Emergency Exit Execution**
- **When**: `plan_actions_v4()` returns `emergency_exit` action
- **Action**: `execute()` sells 100% of position (`size_frac = 1.0`)
- **Result**: `total_quantity = 0` (position emptied)
- **Logging**: 
  - ✅ `"EXEC START: emergency_exit ..."`
  - ✅ `"EXEC OK: sell ..."` or `"EXEC FAIL: sell ..."`
- **Execution History**: `last_emergency_exit_ts` is recorded

**Step 3: Price Reclaims Above EMA333**
- **When**: Price >= EMA333 (still in S3)
- **Action**: `reclaimed_ema333 = True`
- **Logging**: ✅ `"S3 EMA333 RECLAIMED: price >= ema333"`
- **What Should Happen**: `plan_actions_v4()` should return `reclaimed_ema333` action

**Step 4: Reclaim Buy (Expected)**
- **When**: `reclaimed_ema333 = True` AND `last_reclaim_buy.reclaimed_at != current_ts`
- **Action**: `plan_actions_v4()` returns `add` action with `flag: "reclaimed_ema333"`
- **Problem**: If `total_quantity == 0`, this is treated as a new entry, not a reclaim
- **Logging**: ❌ **MISSING** - No clear log showing why reclaim buy was/wasn't triggered

---

## 3. Why Emergency Exit → No Reclaim?

### Scenario 1: Position Already Empty
```
1. Emergency exit executes → total_quantity = 0
2. Price reclaims → reclaimed_ema333 = True
3. plan_actions_v4() checks: is_new_trade = True (no current_trade_id)
4. Returns "entry" action (not "add" with reclaimed_ema333 flag)
5. ❌ Missing: Log showing why reclaim didn't trigger
```

### Scenario 2: Reclaim Buy Blocked
```
1. Emergency exit executes → last_emergency_exit_ts recorded
2. Price reclaims → reclaimed_ema333 = True
3. plan_actions_v4() checks: last_reclaim_buy exists with same reclaimed_at
4. Returns [] (no action - already rebought)
5. ❌ Missing: Log showing reclaim buy was blocked
```

### Scenario 3: State Transitioned to S0
```
1. Emergency exit executes → total_quantity = 0
2. All EMAs break below EMA333 → State transitions S3 → S0
3. Position closure happens (total_quantity == 0 AND state == S0)
4. Price reclaims → But state is S0, not S3
5. ❌ Missing: Log showing state transition prevented reclaim
```

---

## 4. Current Logging Gaps

### Executor Logging (executor.py)

**✅ What's Logged:**
- `EXEC START: {decision_type} {token}/{chain} tf={timeframe} size_frac={size_frac}`
- `EXEC OK: add/entry {token}/{chain} tf={timeframe} bought={tokens} price={price}`
- `EXEC OK: sell {token}/{chain} tf={timeframe} sold={tokens} price={price}`
- `EXEC FAIL: {decision_type} {token}/{chain} tf={timeframe} err={error}`
- `EXEC SKIP: {decision_type} {token}/{chain} ({reason})`

**❌ What's Missing:**
1. **Decision Context**: Why was this decision made? (flag, state, scores)
2. **Position State**: What was total_quantity before execution?
3. **Execution Method**: Jupiter vs Li.Fi? Which chain?
4. **Price Context**: Entry price vs current price? P&L impact?
5. **Slippage Details**: Actual slippage vs expected?
6. **Token Decimals**: What decimals were used?
7. **Execution History Check**: Was this blocked by execution history?

### Plan Actions Logging (actions.py)

**✅ What's Logged:**
- `PM BLOCKED emergency_exit: already executed in current episode`
- `PM BLOCKED emergency_exit: no tokens to sell`
- `PM detected first_dip_buy_flag=True`
- `PM BLOCKED buy (S2/S3): emergency_exit=True`

**❌ What's Missing:**
1. **Action Planning Start**: When plan_actions_v4() is called
2. **Priority Order**: Which condition matched first?
3. **Execution History Checks**: What was checked? What blocked?
4. **Reclaim Detection**: Why reclaim buy was/wasn't triggered
5. **Cooldown Status**: Trim cooldown expired? SR level changed?
6. **Multiplier Application**: What multipliers were applied?
7. **Override Application**: Were v5 overrides applied?

### Position Update Logging (pm_core_tick.py)

**✅ What's Logged:**
- `pm_core_tick.exec_update decision={type} status_before={status} qty_before={qty} ...`

**❌ What's Missing:**
1. **Before/After Comparison**: Clear before/after state
2. **Status Transitions**: watchlist → active, active → watchlist
3. **P&L Impact**: How did this execution affect P&L?
4. **Trade ID Changes**: When current_trade_id is created

### Execution History Logging (pm_core_tick.py)

**✅ What's Logged:**
- (Minimal - mostly in execution_history dict)

**❌ What's Missing:**
1. **History Checks**: What was checked? What blocked?
2. **History Updates**: What was recorded? Why?
3. **Reclaim Tracking**: When was last_reclaim_buy updated?

---

## 5. Recommended Logging Enhancements

### Executor Logging (executor.py)

```python
# At EXEC START:
logger.info(
    "EXEC START: %s %s/%s tf=%s size_frac=%.4f | "
    "position_qty=%.6f status=%s | "
    "flag=%s state=%s | "
    "method=%s chain=%s",
    decision_type, token_label, chain, timeframe, size_frac,
    position.get("total_quantity", 0.0),
    position.get("status", "unknown"),
    action.get("reasons", {}).get("flag", "unknown"),
    uptrend.get("state", "unknown"),
    "jupiter" if chain.lower() == "solana" else "lifi",
    chain
)

# At EXEC OK:
logger.info(
    "EXEC OK: %s %s/%s tf=%s | "
    "tx=%s | "
    "tokens=%s price=%.8f slippage=%.2f%% | "
    "qty_before=%.6f qty_after=%.6f | "
    "pnl_impact=$%.2f (%.2f%%)",
    decision_type, token_label, chain, timeframe,
    tx_hash,
    tokens_bought_or_sold, price, slippage,
    qty_before, qty_after,
    pnl_impact_usd, pnl_impact_pct
)

# At EXEC FAIL:
logger.error(
    "EXEC FAIL: %s %s/%s tf=%s | "
    "err=%s | "
    "position_qty=%.6f status=%s | "
    "flag=%s state=%s",
    decision_type, token_label, chain, timeframe,
    error,
    position.get("total_quantity", 0.0),
    position.get("status", "unknown"),
    action.get("reasons", {}).get("flag", "unknown"),
    uptrend.get("state", "unknown")
)
```

### Plan Actions Logging (actions.py)

```python
# At start of plan_actions_v4():
logger.debug(
    "PLAN ACTIONS: %s/%s tf=%s | "
    "state=%s prev_state=%s | "
    "flags: buy_signal=%s buy_flag=%s trim_flag=%s emergency_exit=%s reclaimed_ema333=%s | "
    "qty=%.6f status=%s",
    token, chain, timeframe,
    state, prev_state,
    uptrend.get("buy_signal"), uptrend.get("buy_flag"), 
    uptrend.get("trim_flag"), uptrend.get("emergency_exit"),
    uptrend.get("reclaimed_ema333"),
    total_quantity, position.get("status")
)

# When action is returned:
logger.info(
    "PLAN ACTIONS: %s → %s %s/%s | "
    "size_frac=%.4f | "
    "flag=%s state=%s | "
    "reason: %s",
    decision_type, token, chain,
    size_frac,
    flag, state,
    reason_summary
)

# When action is blocked:
logger.info(
    "PLAN ACTIONS: %s BLOCKED for %s/%s | "
    "reason: %s | "
    "check: %s",
    decision_type, token, chain,
    block_reason,
    check_details
)
```

### Reclaim-Specific Logging

```python
# When reclaimed_ema333 is detected:
logger.info(
    "RECLAIM DETECTED: %s/%s tf=%s | "
    "price=%.8f >= ema333=%.8f | "
    "prev_emergency_exit=%s | "
    "total_quantity=%.6f is_new_trade=%s | "
    "last_reclaim_buy=%s",
    token, chain, timeframe,
    price, ema333,
    prev_emergency_exit,
    total_quantity, is_new_trade,
    last_reclaim_buy
)

# When reclaim buy is triggered:
logger.info(
    "RECLAIM BUY: %s/%s tf=%s | "
    "size_frac=%.4f | "
    "is_new_trade=%s | "
    "reclaimed_at=%s",
    token, chain, timeframe,
    size_frac,
    is_new_trade,
    reclaimed_at
)

# When reclaim buy is blocked:
logger.info(
    "RECLAIM BUY BLOCKED: %s/%s tf=%s | "
    "reason: %s | "
    "last_reclaim_buy=%s reclaimed_at=%s",
    token, chain, timeframe,
    block_reason,
    last_reclaim_buy, reclaimed_at
)
```

---

## 6. Execution Flow State Machine

### Entry Flow
```
watchlist (qty=0) 
  → entry/add executed 
  → active (qty>0)
```

### Add Flow
```
active (qty>0) 
  → add executed 
  → active (qty increased)
```

### Trim Flow
```
active (qty>0) 
  → trim executed 
  → active (qty decreased, but >0)
```

### Emergency Exit Flow
```
active (qty>0) 
  → emergency_exit executed 
  → active (qty=0) 
  → [if state==S0] → watchlist (closed)
```

### Reclaim Flow (Expected)
```
active (qty=0, state=S3, emergency_exit=True) 
  → price reclaims EMA333 
  → reclaimed_ema333=True 
  → add executed (reclaimed_ema333 flag) 
  → active (qty>0, emergency_exit=False)
```

### Reclaim Flow (Actual - Problem)
```
active (qty=0, state=S3, emergency_exit=True) 
  → price reclaims EMA333 
  → reclaimed_ema333=True 
  → [if is_new_trade=True] → entry executed (not reclaim!) 
  → active (qty>0)
```

---

## 7. Key Issues Identified

### Issue 1: Reclaim Buy Logic
**Problem**: When `total_quantity == 0` after emergency exit, `reclaimed_ema333` buy is treated as a new entry, not a reclaim.

**Location**: `pm/actions.py` line 809-843

**Current Logic**:
```python
if state == "S3" and uptrend.get("reclaimed_ema333"):
    last_reclaim_buy = exec_history.get("last_reclaim_buy", {})
    reclaimed_at = uptrend.get("ts")
    if not last_reclaim_buy or last_reclaim_buy.get("reclaimed_at") != reclaimed_at:
        # ... returns add/entry action
```

**Issue**: If `is_new_trade = True` (no current_trade_id), it returns `"entry"` instead of `"add"` with `reclaimed_ema333` flag.

**Fix Needed**: Always use `"add"` for reclaim buys, regardless of `is_new_trade`.

### Issue 2: Missing Execution History Context
**Problem**: No logging showing why reclaim buy was/wasn't triggered.

**Fix Needed**: Add detailed logging in `plan_actions_v4()` reclaim section.

### Issue 3: Emergency Exit → Reclaim Timing
**Problem**: If state transitions S3 → S0 before reclaim happens, reclaim won't trigger (state must be S3).

**Fix Needed**: Log state transitions and why reclaim was blocked.

---

## 8. Next Steps

1. **Add comprehensive logging** to executor, plan_actions, and position updates
2. **Fix reclaim buy logic** to always use "add" with reclaimed_ema333 flag
3. **Add state transition logging** to track S3 → S0 transitions
4. **Add execution history logging** to show what was checked/blocked
5. **Test emergency exit → reclaim flow** with detailed logging

