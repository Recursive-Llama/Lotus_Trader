# System Investigation Report
**Date**: 2025-01-XX  
**Purpose**: Deep investigation of 5 critical system components based on logs

---

## 1. Dip Pool Rebuys Investigation

### Expected Behavior
- When a position is trimmed, the trimmed USD amount accumulates into a "trim pool"
- S2 dip buys can use this pool to rebuy (recovery mechanism)
- Pool is cleared after S2 dip buy (one-shot per pool)
- DX buys (S3) can also use the pool with a 6×ATR ladder (max 3 buys)

### Code Location
**File**: `src/intelligence/lowcap_portfolio_manager/pm/actions.py`

**Key Functions**:
- `_on_trim()` (lines 48-65): Accumulates trim amounts into pool
- `_on_s2_dip_buy()` (lines 68-79): Clears pool after S2 dip buy
- `_on_dx_buy()` (lines 82-96): Updates pool for DX ladder buys
- `plan_actions_v4()` (lines 1001-1096): Plans S2 dip buys from pool

### How It Works

#### Pool Creation (on Trim)
```48:65:src/intelligence/lowcap_portfolio_manager/pm/actions.py
def _on_trim(exec_history: Dict[str, Any], trim_usd: float) -> None:
    """Called when a trim happens. Accumulates or resets pool based on recovery state."""
    pool = _get_pool(exec_history)
    
    if pool.get("recovery_started", False):
        # Recovery already started - new trim creates FRESH pool
        # Old pool remainder becomes locked profit (done, gone)
        exec_history["trim_pool"] = {
            "usd_basis": trim_usd,
            "recovery_started": False,
            "dx_count": 0,
            "dx_last_price": None,
            "dx_next_arm": None,
        }
    else:
        # No recovery yet - ACCUMULATE into usd_basis
        pool["usd_basis"] = pool.get("usd_basis", 0) + trim_usd
        exec_history["trim_pool"] = pool
```

#### S2 Dip Buy Logic
```1001:1096:src/intelligence/lowcap_portfolio_manager/pm/actions.py
if effective_buy_flag and state == "S2":
    # Check episode blocking first
    token_contract = position.get("token_contract", "")
    if sb_client and is_entry_blocked(sb_client, token_contract, token_chain, timeframe, "S2"):
        pm_logger.info(
            "PLAN ACTIONS: BLOCKED S2 entry (episode block) | %s/%s tf=%s | "
            "reason: token blocked until success observed",
            token_ticker, token_chain, timeframe
        )
        return []
    
    is_flat = total_quantity <= 0
    pool = _get_pool(exec_history)
    pool_basis = pool.get("usd_basis", 0)
    has_pool = pool_basis > 0
    recovery_started = pool.get("recovery_started", False)
    
    # S2 dip allowed if: flat OR (has pool AND DX not started)
    can_s2_dip = is_flat or (has_pool and not recovery_started)
    
    pm_logger.info(
        "PLAN ACTIONS: S2 buy_flag | %s/%s tf=%s | "
        "is_flat=%s has_pool=%s (basis=$%.2f) recovery_started=%s → can_s2_dip=%s",
        token_ticker, token_chain, timeframe,
        is_flat, has_pool, pool_basis, recovery_started, can_s2_dip
    )
    
    if can_s2_dip:
        scores = uptrend.get("scores") or {}
        
        if is_flat:
            # Case 1: Flat - use remaining allocation (standard sizing)
            base_entry_size = _a_to_entry_size(a_final, state, buy_signal=False, buy_flag=True, first_dip_buy_flag=False)
            entry_size = base_entry_size * entry_multiplier
            notional = usd_alloc_remaining * entry_size
        else:
            # Case 2: Post-trim - size from pool_basis
            if a_final >= 0.7:
                rebuy_frac = 0.60
            elif a_final >= 0.3:
                rebuy_frac = 0.30
            else:
                rebuy_frac = 0.10
            
            notional = pool_basis * rebuy_frac
            notional = min(notional, usd_alloc_remaining)  # Safety cap
            entry_size = notional / usd_alloc_remaining if usd_alloc_remaining > 0 else 0
```

#### Pool Update After Execution
```1995:2006:src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py
pool_basis = pool.get("usd_basis", 0)
recovery_started = pool.get("recovery_started", False)

if pool_basis > 0:
    if state == "S2" and not recovery_started:
        # S2 dip buy from pool - clears pool
        notional = float(action.get("notional", 0) or execution_result.get("tokens_received", 0) * price)
        locked = _on_s2_dip_buy(execution_history, notional)
        logger.info(
            "TRIM_POOL: S2 dip buy $%.2f from pool, locked $%.2f profit | position=%s",
            notional, locked, position_id
        )
```

### Potential Issues to Check in Logs

1. **Pool Not Created on Trim**
   - Check if `_on_trim()` is called when trims execute
   - Look for log: `"TRIM_POOL: Updated pool with $X.XX trim"`
   - Location: `pm_core_tick.py` line 2093

2. **S2 Dip Buy Not Triggered**
   - Check if `can_s2_dip` is True when pool exists
   - Look for log: `"PLAN ACTIONS: S2 buy_flag | ... can_s2_dip=True"`
   - Check if `recovery_started` is incorrectly True

3. **Pool Not Cleared After S2 Buy**
   - Check if `_on_s2_dip_buy()` is called after execution
   - Look for log: `"TRIM_POOL: S2 dip buy $X.XX from pool, locked $X.XX profit"`
   - Verify pool is cleared in execution_history

4. **Notional Calculation Issues**
   - Check if `notional` is calculated correctly from `pool_basis * rebuy_frac`
   - Verify `usd_alloc_remaining` safety cap is applied
   - Check if `entry_size` becomes 0 when `usd_alloc_remaining` is 0

### Log Search Queries
- `"TRIM_POOL"` - All pool-related operations
- `"S2 dip buy"` - S2 dip buy planning and execution
- `"can_s2_dip"` - S2 dip eligibility checks
- `"pool_basis"` - Pool balance tracking

---

## 2. Episode Failure Blocking Investigation

### Expected Behavior
- When an S1 episode fails (ends at S0), it should block S1 + S2 entries for that token/timeframe
- When an S2 episode fails (ends at S0), it should block S2 entries only
- Success (reaching S3) should unblock
- Only blocks if we actually entered (skipping is correct)

### Code Location
**File**: `src/intelligence/lowcap_portfolio_manager/pm/episode_blocking.py`

**Key Functions**:
- `record_attempt_failure()` (lines 24-96): Records failure and sets blocks
- `record_episode_success()` (lines 99-171): Unblocks on success
- `is_entry_blocked()` (lines 174-226): Checks if entry is blocked

### How It Works

#### Failure Recording
```24:96:src/intelligence/lowcap_portfolio_manager/pm/episode_blocking.py
def record_attempt_failure(
    sb_client,
    token_contract: str,
    token_chain: str,
    timeframe: str,
    entered_s1: bool,
    entered_s2: bool,
    book_id: str = "onchain_crypto"
) -> None:
    """
    Called when an attempt ends at S0 (failure).
    Only blocks if we actually acted in S1 or S2.
    """
    # We skipped - correct decision, no block needed
    if not entered_s1 and not entered_s2:
        logger.debug(
            "EPISODE_BLOCK: Skipping record (no entry) | %s/%s tf=%s",
            token_contract[:12], token_chain, timeframe
        )
        return
    
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    
    # Build upsert payload - record ALL entries that happened
    payload: Dict[str, Any] = {
        "token_contract": token_contract,
        "token_chain": token_chain,
        "timeframe": timeframe,
        "book_id": book_id,
        "updated_at": now_iso,
    }
    
    # Two separate ifs (not elif) so we record BOTH if applicable
    if entered_s1:
        # S1 failure blocks BOTH S1 and S2
        payload["blocked_s1"] = True
        payload["blocked_s2"] = True
        payload["last_s1_failure_ts"] = now_iso
        logger.info(
            "EPISODE_BLOCK: Recording S1 failure (blocks S1+S2) | %s/%s tf=%s",
            token_contract[:12], token_chain, timeframe
        )
    
    if entered_s2:
        # S2 failure blocks S2 and records timestamp
        payload["blocked_s2"] = True
        payload["last_s2_failure_ts"] = now_iso
        logger.info(
            "EPISODE_BLOCK: Recording S2 failure (blocks S2) | %s/%s tf=%s",
            token_contract[:12], token_chain, timeframe
        )
    
    try:
        sb_client.table("token_timeframe_blocks").upsert(
            payload,
            on_conflict="token_contract,token_chain,timeframe,book_id"
        ).execute()
    except Exception as e:
        logger.error(
            "EPISODE_BLOCK: Failed to record failure | %s/%s tf=%s | error=%s",
            token_contract[:12], token_chain, timeframe, e
        )
```

#### Where It's Called
```1279:1301:src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py
elif state == "S0" and prev_state in ("S1", "S2"):
    outcome = "failure"
    # Update DB outcomes for all windows in this episode
    self._update_episode_outcomes_from_meta(s1_episode, outcome)

    # Record blocking failure if we entered S1
    if s1_episode.get("entered"):
        try:
            # Check if S2 also entered in this attempt (need to check s2_episode before it's cleared)
            s2_episode = meta.get("s2_episode")
            entered_s2 = s2_episode.get("entered", False) if s2_episode else False
            
            record_attempt_failure(
                sb_client=self.sb,
                token_contract=position.get("token_contract", ""),
                token_chain=position.get("token_chain", ""),
                timeframe=position.get("timeframe", ""),
                entered_s1=True,
                entered_s2=entered_s2,
                book_id=position.get("book_id", "onchain_crypto")
            )
        except Exception as e:
            logger.warning(f"Failed to record attempt failure for blocking: {e}")
```

#### Blocking Check in Actions
```1002:1010:src/intelligence/lowcap_portfolio_manager/pm/actions.py
if effective_buy_flag and state == "S2":
    # Check episode blocking first
    token_contract = position.get("token_contract", "")
    if sb_client and is_entry_blocked(sb_client, token_contract, token_chain, timeframe, "S2"):
        pm_logger.info(
            "PLAN ACTIONS: BLOCKED S2 entry (episode block) | %s/%s tf=%s | "
            "reason: token blocked until success observed",
            token_ticker, token_chain, timeframe
        )
        return []
```

### Potential Issues to Check in Logs

1. **Failure Not Recorded**
   - Check if `record_attempt_failure()` is called when S0 transition happens
   - Look for log: `"EPISODE_BLOCK: Recording S1 failure"` or `"EPISODE_BLOCK: Recording S2 failure"`
   - Verify `s1_episode.get("entered")` is True when we actually entered

2. **Blocking Check Not Performed**
   - Check if `is_entry_blocked()` is called before S1/S2 entries
   - Look for log: `"PLAN ACTIONS: BLOCKED S2 entry (episode block)"`
   - Verify blocking check happens in `plan_actions_v4()` for both S1 and S2

3. **Success Not Unblocking**
   - Check if `record_episode_success()` is called when S3 is reached
   - Look for log: `"EPISODE_BLOCK: Unblocking S1 (success observed)"`
   - Verify unblocking happens after failure timestamp

4. **Database Issues**
   - Check if `token_timeframe_blocks` table exists and has correct schema
   - Verify upsert is working (check for errors in logs)
   - Check if blocking state persists across PM ticks

### Log Search Queries
- `"EPISODE_BLOCK"` - All episode blocking operations
- `"Recording S1 failure"` or `"Recording S2 failure"` - Failure recording
- `"BLOCKED S2 entry"` or `"BLOCKED S1 entry"` - Entry blocking
- `"Unblocking"` - Success unblocking

### Known Issue from Previous Investigation
**Document**: `docs/investigations/episode_blocking_failure_investigation.md`

**Finding**: `record_attempt_failure` was previously NEVER called when episodes failed. This was fixed in the current code (lines 1285-1301), but verify it's actually being called in logs.

---

## 3. Allocation Amount in Dollars Investigation

### Expected Behavior
- `total_allocation_pct` is set by Decision Maker when position is created
- `total_allocation_usd` starts at 0.0 and is updated by Executor/PM on each execution
- `usd_alloc_remaining` is recalculated before each decision: `(total_allocation_pct * wallet_balance) - (total_allocation_usd - total_extracted_usd)`
- Uses Solana USDC balance as the base (home chain)

### Code Location

#### Initial Setting (Position Creation)
**File**: `src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py`

```753:754:src/intelligence/decision_maker_lowcap/decision_maker_lowcap_simple.py
'total_allocation_pct': allocation_pct * timeframe_pct,  # Store timeframe-specific allocation %
'total_allocation_usd': 0.0,  # PM will update this on execution
```

#### Recalculation (Before Decisions)
**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

```2174:2208:src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py
# Calculate usd_alloc_remaining
# Formula: (total_allocation_pct * wallet_balance) - (total_allocation_usd - total_extracted_usd)
# NOTE: Always use Solana USDC balance (home chain) - all capital is centralized there
total_allocation_pct = float(position.get("total_allocation_pct") or 0.0)
if total_allocation_pct > 0:
    # Get Solana USDC balance (home chain - all capital is here)
    home_chain = os.getenv("HOME_CHAIN", "solana").lower()
    try:
        wallet_result = (
            self.sb.table("wallet_balances")
            .select("usdc_balance,balance_usd")
            .eq("chain", home_chain)
            .limit(1)
            .execute()
        )
        if wallet_result.data:
            row = wallet_result.data[0]
            wallet_balance = float(row.get("usdc_balance") or row.get("balance_usd") or 0.0)
        else:
            wallet_balance = 0.0
            logger.warning(f"No wallet_balances row found for home chain={home_chain}, using 0.0")
    except Exception as e:
        wallet_balance = 0.0
        logger.warning(f"Error getting wallet balance for home chain {home_chain}: {e}")
    
    # Calculate max allocation and net deployed
    max_allocation_usd = wallet_balance * (total_allocation_pct / 100.0)
    net_deployed_usd = total_allocation_usd - total_extracted_usd
    usd_alloc_remaining = max_allocation_usd - net_deployed_usd
    
    logger.debug(f"usd_alloc_remaining calc (home_chain={home_chain}): wallet_balance=${wallet_balance:.2f}, total_allocation_pct={total_allocation_pct}%, max_allocation_usd=${max_allocation_usd:.2f}, net_deployed_usd=${net_deployed_usd:.2f}, usd_alloc_remaining=${usd_alloc_remaining:.2f}")
    
    updates["usd_alloc_remaining"] = max(0.0, usd_alloc_remaining)  # Can't be negative
else:
    updates["usd_alloc_remaining"] = 0.0
```

#### Update on Execution
**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

The `total_allocation_usd` is updated by the Executor when trades execute. The Executor writes the actual USD amount invested to the position table.

### How It Works

1. **Position Creation**:
   - Decision Maker sets `total_allocation_pct` (e.g., 25%)
   - `total_allocation_usd` starts at 0.0

2. **Before Each Decision**:
   - PM recalculates `usd_alloc_remaining`:
     - Gets Solana USDC balance from `wallet_balances` table
     - Calculates `max_allocation_usd = wallet_balance * (total_allocation_pct / 100.0)`
     - Calculates `net_deployed_usd = total_allocation_usd - total_extracted_usd`
     - Calculates `usd_alloc_remaining = max_allocation_usd - net_deployed_usd`

3. **After Execution**:
   - Executor updates `total_allocation_usd` with actual USD invested
   - PM recalculates `usd_alloc_remaining` on next tick

### Potential Issues to Check in Logs

1. **Wallet Balance Not Found**
   - Check for log: `"No wallet_balances row found for home chain=solana"`
   - Verify `wallet_balances` table has correct data
   - Check if `HOME_CHAIN` env var is set correctly

2. **Allocation Percentage Not Set**
   - Check if `total_allocation_pct` is 0 or None
   - Verify Decision Maker is setting it correctly on position creation
   - Check if timeframe split is applied correctly

3. **Calculation Errors**
   - Check for log: `"usd_alloc_remaining calc"`
   - Verify `max_allocation_usd` calculation is correct
   - Check if `net_deployed_usd` is negative (shouldn't happen)
   - Verify `usd_alloc_remaining` can't go negative (should be clamped to 0)

4. **Timing Issues**
   - Check if `usd_alloc_remaining` is recalculated before each decision
   - Verify it's updated after executions
   - Check if wallet balance is stale (not updated recently)

5. **total_allocation_usd Not Updated**
   - Check if Executor is updating `total_allocation_usd` after trades
   - Verify it's cumulative (adds to existing value)
   - Check if it's reset incorrectly when position closes

### Log Search Queries
- `"usd_alloc_remaining calc"` - Allocation calculation logs
- `"No wallet_balances row found"` - Wallet balance errors
- `"total_allocation_pct"` - Allocation percentage tracking
- `"max_allocation_usd"` - Maximum allocation calculation

---

## 4. Portfolio Tracking Database Investigation

### Current State
**File**: `src/database/wallet_balance_snapshots_schema.sql`

The `wallet_balance_snapshots` table currently tracks:
- `total_balance_usd` - Total portfolio value (USDC + active positions)
- `usdc_total` - Sum of USDC across all chains
- `active_positions_value` - Sum of `current_usd_value` for active positions
- `active_positions_count` - Count of active positions

**Missing**: Individual position details (ticker, value, PNL) are NOT stored in snapshots.

### Current Snapshot Capture
**File**: `src/intelligence/system_observer/jobs/balance_snapshot.py`

```19:73:src/intelligence/system_observer/jobs/balance_snapshot.py
async def capture_snapshot(self, snapshot_type: str = "hourly") -> Dict[str, Any]:
    """Capture current balance snapshot
    
    Args:
        snapshot_type: 'hourly', '4hour', 'daily', 'weekly', or 'monthly'
    """
    try:
        # 1. Get USDC from all chains
        wallet_rows = (
            self.sb.table("wallet_balances")
            .select("usdc_balance")
            .execute()
        ).data or []
        
        usdc_total = sum(float(row.get("usdc_balance", 0) or 0) for row in wallet_rows)
        
        # 2. Get active positions value
        position_rows = (
            self.sb.table("lowcap_positions")
            .select("current_usd_value")
            .eq("status", "active")
            .execute()
        ).data or []
        
        active_positions_value = sum(
            float(row.get("current_usd_value", 0) or 0) 
            for row in position_rows
        )
        active_positions_count = len(position_rows)
        
        # 3. Calculate total
        total_balance = usdc_total + active_positions_value
        
        # 4. Insert snapshot
        snapshot = {
            "snapshot_type": snapshot_type,
            "total_balance_usd": total_balance,
            "usdc_total": usdc_total,
            "active_positions_value": active_positions_value,
            "active_positions_count": active_positions_count,
            "captured_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = (
            self.sb.table("wallet_balance_snapshots")
            .insert(snapshot)
            .execute()
        )
        
        logger.info(
            f"Balance snapshot captured ({snapshot_type}): ${total_balance:.2f} "
            f"(USDC: ${usdc_total:.2f}, Active: ${active_positions_value:.2f}, Count: {active_positions_count})"
        )
        
        return snapshot
```

### What's Missing

The user wants to track:
- **Ticker** - Token ticker symbol
- **Value** - Current USD value of position
- **Current PNL** - Unrealized P&L (current_usd_value - cost basis)
- **Realized PNL** - Realized P&L from exits (rpnl_usd)

### Required Changes

1. **New Table**: `portfolio_snapshot_positions`
   - Links to `wallet_balance_snapshots` via `snapshot_id`
   - Stores per-position data at snapshot time

2. **Schema Addition**:
```sql
CREATE TABLE portfolio_snapshot_positions (
    id SERIAL PRIMARY KEY,
    snapshot_id INT NOT NULL REFERENCES wallet_balance_snapshots(id),
    position_id INT NOT NULL,
    token_ticker TEXT NOT NULL,
    token_contract TEXT NOT NULL,
    token_chain TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    current_usd_value FLOAT NOT NULL,
    current_pnl_usd FLOAT NOT NULL,  -- Unrealized P&L
    realized_pnl_usd FLOAT NOT NULL,  -- Realized P&L (rpnl_usd)
    total_pnl_usd FLOAT NOT NULL,     -- Total P&L
    total_allocation_usd FLOAT NOT NULL,
    total_extracted_usd FLOAT NOT NULL,
    total_quantity FLOAT NOT NULL,
    avg_entry_price FLOAT,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(snapshot_id, position_id)
);

CREATE INDEX idx_snapshot_positions_snapshot ON portfolio_snapshot_positions(snapshot_id);
CREATE INDEX idx_snapshot_positions_position ON portfolio_snapshot_positions(position_id);
CREATE INDEX idx_snapshot_positions_ticker ON portfolio_snapshot_positions(token_ticker);
```

3. **Code Changes**:
   - Modify `balance_snapshot.py` to capture position details
   - Store position data in `portfolio_snapshot_positions` table
   - Query both tables together for portfolio history

### Current Data Available

From `lowcap_positions` table:
- `token_ticker` - Ticker symbol
- `current_usd_value` - Current USD value
- `total_pnl_usd` - Total P&L (realized + unrealized)
- `rpnl_usd` - Realized P&L
- `total_allocation_usd` - Total invested
- `total_extracted_usd` - Total extracted
- `total_quantity` - Current quantity
- `avg_entry_price` - Average entry price

### Potential Issues

1. **No Position History**
   - Current snapshots only store aggregates
   - Can't see which positions were active at each snapshot
   - Can't track position-level P&L over time

2. **Data Loss on Position Closure**
   - When position closes, it's removed from active status
   - No historical record of closed positions in snapshots
   - Can't see final P&L for closed positions

3. **Snapshot Timing**
   - Snapshots are taken hourly/4h/daily
   - Positions may change between snapshots
   - Need to capture exact state at snapshot time

### Log Search Queries
- `"Balance snapshot captured"` - Snapshot creation logs
- `"active_positions_count"` - Position count in snapshots
- Check if position data is being queried but not stored

---

## 5. Buybacks Investigation

### Expected Behavior
- When a position fully closes (state S0, total_quantity = 0), swap 10% of profit to Lotus Coin
- Transfer 69% of bought Lotus tokens to holding wallet
- Store buyback result in position features
- Fail gracefully (don't block position closure if buyback fails)

### Code Location
**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

**Method**: `_swap_profit_to_lotus()` (lines 248-378)

### How It Works

#### Buyback Execution
```3074:3094:src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py
# Execute Lotus buyback (10% of profit → Lotus Coin, then transfer 69% to holding wallet)
try:
    buyback_result = self._swap_profit_to_lotus(position_for_buyback)
    if buyback_result and buyback_result.get("success"):
        logger.info(
            f"Lotus buyback successful for position {position_id}: "
            f"{buyback_result.get('lotus_tokens', 0):.6f} tokens, "
            f"{buyback_result.get('lotus_tokens_transferred', 0):.6f} transferred to holding wallet"
        )
        # Store buyback info in position features (will be saved in main update below)
        if not isinstance(features, dict):
            features = {}
        if "pm_execution_history" not in features:
            features["pm_execution_history"] = {}
        features["pm_execution_history"]["lotus_buyback"] = buyback_result
    elif buyback_result and not buyback_result.get("success"):
        logger.warning(f"Lotus buyback failed for position {position_id}: {buyback_result.get('error')}")
except Exception as e:
    logger.error(f"Error executing Lotus buyback for position {position_id}: {e}", exc_info=True)
    # Don't block position closure if buyback fails
    buyback_result = None
```

#### Buyback Implementation
```248:378:src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py
def _swap_profit_to_lotus(self, position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Swap 10% of position profit to Lotus Coin, then transfer 69% of those tokens to holding wallet.
    """
    try:
        # Check if buyback is enabled
        if os.getenv("LOTUS_BUYBACK_ENABLED", "0") != "1":
            return {"success": True, "skipped": True, "reason": "Buyback disabled"}
        
        # Get configuration
        lotus_contract = os.getenv("LOTUS_CONTRACT", "Ch4tXj2qf8V6a4GdpS4X3pxAELvbnkiKTHGdmXjLEXsC")
        holding_wallet = os.getenv("LOTUS_HOLDING_WALLET", "AbumtzzxomWWrm9uypY6ViRgruGdJBPFPM2vyHewTFdd")
        buyback_percentage = float(os.getenv("LOTUS_BUYBACK_PERCENTAGE", "10.0"))
        transfer_percentage = float(os.getenv("LOTUS_TRANSFER_PERCENTAGE", "69.0"))
        
        # Calculate profit
        # Use rpnl_usd (realized P&L) for fully closed positions
        profit_usd = float(position.get("rpnl_usd", 0.0))
        
        # If rpnl_usd not available or zero, calculate from extracted vs allocated
        if profit_usd == 0:
            total_extracted = float(position.get("total_extracted_usd", 0.0))
            total_allocated = float(position.get("total_allocation_usd", 0.0))
            profit_usd = total_extracted - total_allocated
        
        # Only swap if profit is positive
        if profit_usd <= 0:
            return {
                "success": True,
                "skipped": True,
                "reason": f"No profit to swap (profit_usd={profit_usd:.2f})"
            }
        
        # Calculate swap amount (10% of profit)
        swap_amount_usd = profit_usd * (buyback_percentage / 100.0)
        
        # Minimum swap amount check (avoid dust)
        min_swap_usd = float(os.getenv("LOTUS_BUYBACK_MIN_USD", "1.0"))
        if swap_amount_usd < min_swap_usd:
            return {
                "success": True,
                "skipped": True,
                "reason": f"Swap amount too small: ${swap_amount_usd:.2f} < ${min_swap_usd:.2f}"
            }
        
        logger.info(f"Executing Lotus buyback: ${swap_amount_usd:.2f} (10% of ${profit_usd:.2f} profit)")
        
        # Swap USDC → Lotus Coin on Solana
        # USDC has 6 decimals, so convert to smallest unit
        usdc_amount = str(int(swap_amount_usd * 1_000_000))
        
        swap_result = self.executor._call_lifi_executor(
            action="swap",
            chain="solana",
            from_token="USDC",
            to_token=lotus_contract,
            amount=usdc_amount,
            slippage=0.5,  # 0.5% slippage tolerance
            from_chain="solana",
            to_chain="solana"
        )
        
        if not swap_result.get("success"):
            return {
                "success": False,
                "error": f"Swap failed: {swap_result.get('error', 'Unknown error')}",
                "profit_usd": profit_usd,
                "swap_amount_usd": swap_amount_usd
            }
        
        # Get Lotus tokens received from swap
        # Li.Fi returns amount in smallest unit, need to convert
        # Lotus token has 9 decimals (standard SPL token)
        tokens_received_raw = swap_result.get("toAmount") or swap_result.get("toAmountMin") or "0"
        try:
            lotus_tokens = float(tokens_received_raw) / 1_000_000_000  # 9 decimals
        except (ValueError, TypeError):
            # Fallback: try to get from result directly
            lotus_tokens = float(swap_result.get("tokens_received", 0.0))
        
        swap_tx_hash = swap_result.get("txHash") or swap_result.get("tx_hash")
        
        logger.info(f"Lotus swap successful: {lotus_tokens:.6f} tokens received (tx: {swap_tx_hash})")
        
        # Transfer 69% to holding wallet
        transfer_amount = lotus_tokens * (transfer_percentage / 100.0)
        transfer_result = None
        
        if transfer_amount > 0:
            try:
                transfer_result = self._transfer_lotus_to_holding_wallet(transfer_amount, holding_wallet)
                if not transfer_result or not transfer_result.get("success"):
                    logger.warning(f"Lotus transfer failed: {transfer_result.get('error') if transfer_result else 'Unknown error'}")
                    # Don't fail the whole buyback if transfer fails - tokens are still in trading wallet
            except Exception as e:
                logger.error(f"Error transferring Lotus tokens: {e}", exc_info=True)
                # Don't fail the whole buyback if transfer fails
        
        return {
            "success": True,
            "profit_usd": profit_usd,
            "swap_amount_usd": swap_amount_usd,
            "lotus_tokens": lotus_tokens,
            "lotus_tokens_kept": lotus_tokens * (1.0 - transfer_percentage / 100.0),  # 31% kept
            "lotus_tokens_transferred": transfer_amount if transfer_result and transfer_result.get("success") else 0.0,
            "swap_tx_hash": swap_tx_hash,
            "transfer_tx_hash": transfer_result.get("tx_hash") if transfer_result else None,
            "transfer_success": transfer_result.get("success") if transfer_result else False
        }
        
    except Exception as e:
        logger.error(f"Error in Lotus buyback: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
```

### Potential Issues to Check in Logs

1. **Buyback Not Enabled**
   - Check if `LOTUS_BUYBACK_ENABLED=1` in environment
   - Look for log: `"Buyback disabled"` or `"skipped": True, "reason": "Buyback disabled"`
   - Verify env var is set correctly

2. **Profit Calculation Issues**
   - Check if `rpnl_usd` is available and correct
   - Look for log: `"No profit to swap (profit_usd=X.XX)"`
   - Verify `total_extracted_usd - total_allocation_usd` calculation
   - Check if profit is negative (should skip)

3. **Swap Amount Too Small**
   - Check if swap amount is below minimum ($1.00 default)
   - Look for log: `"Swap amount too small: $X.XX < $1.00"`
   - Verify `LOTUS_BUYBACK_MIN_USD` is set correctly

4. **Swap Execution Failure**
   - Check if `_call_lifi_executor()` is called
   - Look for log: `"Executing Lotus buyback: $X.XX"`
   - Check for errors: `"Swap failed: ..."`
   - Verify Li.Fi executor is working
   - Check if USDC balance is sufficient on Solana

5. **Token Amount Conversion Issues**
   - Check if Lotus token decimals are correct (9 decimals)
   - Verify `toAmount` or `toAmountMin` is in response
   - Check for log: `"Lotus swap successful: X.XXXXXX tokens received"`

6. **Transfer Failure**
   - Check if `_transfer_lotus_to_holding_wallet()` is called
   - Look for log: `"Lotus transfer failed: ..."`
   - Verify `SOLANA_RPC_URL` and `SOLANA_PRIVATE_KEY` are set
   - Check if transfer succeeds but buyback still reports success

7. **Buyback Not Called**
   - Check if `_swap_profit_to_lotus()` is called on position closure
   - Verify it's called in `_check_position_closure()` or `_close_trade_on_s0_transition()`
   - Check if position closure happens at all

8. **Result Not Stored**
   - Check if buyback result is stored in `features.pm_execution_history.lotus_buyback`
   - Verify position update includes buyback result
   - Check if result is lost due to exception

### Log Search Queries
- `"Lotus buyback"` - All buyback operations
- `"Executing Lotus buyback"` - Buyback initiation
- `"Lotus swap successful"` - Successful swap
- `"Lotus buyback failed"` or `"Swap failed"` - Buyback failures
- `"Lotus transfer failed"` - Transfer failures
- `"Buyback disabled"` - Buyback not enabled
- `"No profit to swap"` - Profit calculation issues
- `"Swap amount too small"` - Minimum amount check

### Configuration Required
- `LOTUS_BUYBACK_ENABLED=1` - Enable buyback
- `LOTUS_CONTRACT=Ch4tXj2qf8V6a4GdpS4X3pxAELvbnkiKTHGdmXjLEXsC` - Lotus token contract
- `LOTUS_HOLDING_WALLET=AbumtzzxomWWrm9uypY6ViRgruGdJBPFPM2vyHewTFdd` - Holding wallet
- `LOTUS_BUYBACK_PERCENTAGE=10.0` - Percentage of profit to swap
- `LOTUS_TRANSFER_PERCENTAGE=69.0` - Percentage to transfer to holding wallet
- `LOTUS_BUYBACK_MIN_USD=1.0` - Minimum swap amount
- `SOLANA_RPC_URL` - Solana RPC endpoint
- `SOLANA_PRIVATE_KEY` - Solana private key for transfers

---

## Summary of Investigation Areas

1. **Dip Pool Rebuys**: Check trim pool creation, S2 dip buy eligibility, pool clearing
2. **Episode Blocking**: Verify failure recording, blocking checks, success unblocking
3. **Allocation Amounts**: Check wallet balance retrieval, calculation, timing
4. **Portfolio Tracking**: Verify snapshot capture, position data availability
5. **Buybacks**: Check enablement, profit calculation, swap execution, transfer

Each area has specific log search queries and potential failure points identified above.

