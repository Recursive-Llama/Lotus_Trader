# Profit Swap & Telegram Bot - Current Status Analysis

## Overview

After the PM system migration and code cleanup, here's the current state of both features:

---

## 1. Profit Swap to Lotus Coin (10% of profits)

### Current State: ❌ **NOT IMPLEMENTED**

### What Changed:
- **Old System**: Had buyback logic in `TraderLowcapSimpleV2._execute_exit()` (lines 367-408) that:
  - Only worked for Solana exits
  - Used `plan_buyback()` and `perform_buyback()` methods (which don't exist)
  - Calculated buyback from `cost_native` (SOL received)
  
- **New System**: 
  - All execution goes through `PMExecutor` (Li.Fi SDK)
  - Position closure happens in `pm_core_tick.py` (lines 1996-2054)
  - No profit swap logic exists

### Where Position Closure Happens:
**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

**Location**: `_check_position_closure()` method (around line 1996)

**What happens**:
1. PM detects position fully closed (state S0, total_quantity = 0)
2. Updates position: `status='watchlist'`, `closed_at=timestamp`
3. Writes `completed_trades` JSONB
4. Emits `position_closed` strand for learning system
5. **NO profit swap happens here**

### Profit Calculation:
**Available Data** (from position table):
- `total_allocation_usd` - Total USD invested
- `total_extracted_usd` - Total USD extracted (from all exits)
- `total_pnl_usd` - Total P&L (realized + unrealized)
- `rpnl_usd` - Realized P&L (from sells)

**Profit Formula**:
```python
profit_usd = total_extracted_usd - total_allocation_usd
# OR use rpnl_usd if position is fully closed
profit_usd = rpnl_usd  # When fully closed, this is the realized profit
```

### What Needs to Be Done:

1. **Add profit swap hook** in `pm_core_tick.py` after position closure:
   - Calculate profit: `profit_usd = total_extracted_usd - total_allocation_usd`
   - Calculate 10%: `swap_amount_usd = profit_usd * 0.10`
   - **For Solana positions**: Swap SOL → Lotus Coin directly
   - **For Base/BSC/Ethereum**: Bridge USDC → Solana, then swap SOL → Lotus Coin

2. **Use PMExecutor for swap**:
   - PMExecutor already supports cross-chain swaps via Li.Fi SDK
   - Can swap: `USDC (Solana) → Lotus Coin (Solana)`
   - Lotus Coin contract: `Ch4tXj2qf8V6a4GdpS4X3pxAELvbnkiKTHGdmXjLEXsC`

3. **Implementation location**:
   - Add method: `_swap_profit_to_lotus()` in `pm_core_tick.py`
   - Call it right after position closure (after line 2004, before strand emission)

### Challenges:
- **Cross-chain**: Base/BSC/Ethereum exits return USDC on Solana (via Li.Fi bridge)
- **Profit calculation**: Need to ensure we use correct profit (realized vs total)
- **Timing**: Swap should happen immediately after position closure

---

## 2. Telegram Announcement Bot

### Current State: ✅ **EXISTS BUT NOT INTEGRATED**

### What Exists:
**File**: `src/communication/telegram_signal_notifier.py`

**Features**:
- ✅ `send_buy_signal()` - Sends buy notifications
- ✅ `send_sell_signal()` - Sends sell notifications  
- ✅ `send_trend_entry_notification()` - Trend entry notifications
- ✅ `send_trend_exit_notification()` - Trend exit notifications
- ✅ Rich formatting with transaction links, token links, P&L info
- ✅ Already has Lotus buyback display logic (lines 474-495)

### What Changed:
- **Old System**: 
  - TraderService had `send_buy_signal()` and `send_sell_signal()` methods
  - Called from `TraderLowcapSimpleV2` after executions
  - Used `TelegramSignalNotifier` internally
  
- **New System**:
  - `TelegramSignalNotifier` class exists and is complete
  - **NOT called anywhere** in PM system
  - PM doesn't send Telegram notifications

### Where It Should Be Integrated:

1. **Buy Notifications** (`add` / `entry` decisions):
   - **Location**: `pm_core_tick.py` after successful `executor.execute()` (around line 2430)
   - **Trigger**: When `exec_result.get("status") == "success"` and `decision_type in ["add", "entry"]`
   - **Data available**: 
     - `exec_result` has: `tokens_bought`, `price`, `price_native`, `tx_hash`
     - `position` has: `token_ticker`, `token_contract`, `token_chain`
     - `decision` has: `size_frac` (can calculate allocation_pct)

2. **Sell Notifications** (`trim` / `emergency_exit` decisions):
   - **Location**: `pm_core_tick.py` after successful `executor.execute()` (around line 2430)
   - **Trigger**: When `exec_result.get("status") == "success"` and `decision_type in ["trim", "emergency_exit"]`
   - **Data available**:
     - `exec_result` has: `tokens_sold`, `price`, `price_native`, `tx_hash`
     - `position` has: `token_ticker`, `token_contract`, `token_chain`, `total_pnl_usd`, `total_pnl_pct`
     - Can calculate: `tokens_sold_value_usd = tokens_sold * price`

3. **Position Closure Notifications**:
   - **Location**: `pm_core_tick.py` in `_check_position_closure()` (after line 2004)
   - **Trigger**: When position fully closes (status → watchlist)
   - **Data available**: Full position data, completed_trades, profit info

### What Needs to Be Done:

1. **Initialize TelegramSignalNotifier** in `pm_core_tick.py`:
   ```python
   # In __init__ or as a property
   self.telegram_notifier = TelegramSignalNotifier(
       bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
       channel_id=os.getenv("TELEGRAM_CHANNEL_ID"),
       api_id=int(os.getenv("TELEGRAM_API_ID")),
       api_hash=os.getenv("TELEGRAM_API_HASH")
   )
   ```

2. **Add notification calls** after execution:
   - After line 2430 in `pm_core_tick.py` (after executor.execute())
   - Check if execution was successful
   - Call appropriate notification method

3. **Add position closure notification**:
   - In `_check_position_closure()` after position is marked as watchlist
   - Send final position summary

### Integration Points:

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/pm_core_tick.py`

1. **Line ~2430**: After `executor.execute()` - Add buy/sell notifications
2. **Line ~2004**: After position closure - Add closure notification + profit swap

---

## Summary

### Feature 1: Profit Swap to Lotus Coin
- **Status**: ❌ Not implemented
- **Location**: `pm_core_tick.py` - `_check_position_closure()` method
- **Action needed**: Add swap logic after position closure
- **Complexity**: Medium (need to handle cross-chain, use PMExecutor)

### Feature 2: Telegram Bot
- **Status**: ✅ Code exists, ❌ Not integrated
- **Location**: `telegram_signal_notifier.py` - Complete implementation
- **Action needed**: Initialize and call from PM after executions
- **Complexity**: Low (just wire up existing code)

---

## Next Steps

1. **Telegram Bot** (easier, can do first):
   - Initialize `TelegramSignalNotifier` in `pm_core_tick.py`
   - Add notification calls after executions
   - Test with a canary position

2. **Profit Swap** (more complex):
   - Add `_swap_profit_to_lotus()` method
   - Calculate profit correctly
   - Use PMExecutor to swap USDC → Lotus Coin
   - Handle cross-chain cases (Base/BSC → Solana → Lotus)
   - Test with a closed position

---

## Notes

- **Profit calculation**: Use `rpnl_usd` for fully closed positions (it's the realized profit)
- **Swap timing**: Should happen immediately after position closure, before strand emission
- **Error handling**: Both features should fail gracefully (log errors, don't break PM)
- **Configuration**: Both need environment variables for Telegram and Lotus contract address

