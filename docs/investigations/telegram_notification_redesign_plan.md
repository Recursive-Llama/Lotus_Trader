# Telegram Notification Redesign Plan

## Overview

**Goal**: Redesign Telegram notifications for the new PM system with proper action types, P&L tracking, and Lotus buyback info.

**Current State**: `TelegramSignalNotifier` exists but needs redesign for PM actions.

---

## 1. Action Types in PM System

### Entry Actions
- **`entry`** (or `add` with `total_quantity == 0`): Initial position entry
  - S1: `buy_signal` triggered
  - S2: `buy_flag` retest at EMA333
  - S3: `first_dip_buy_flag` or `reclaimed_ema333`

### Scaling Actions
- **`add`**: Adding to existing position
  - S2: Retest buys
  - S3: DX buys, exhaustion adds

### Exit Actions
- **`trim`**: Partial exit
  - S2: Trim at profit targets (OX ≥ 0.65)
  - S3: Trim at exhaustion
  
- **`emergency_exit`**: Full exit from S3
  - Not a "bad" exit - just trend ending
  - Gets final position out

### Retest Buys
- **`add`** with `buy_flag` or `reclaimed_ema333`: Retest entry
  - S2: Retest at EMA333
  - S3: Reclaimed EMA333

---

## 2. Notification Design

### Message Structure

**Use glyphs, not emojis**:
- ⚘ = Lotus symbol
- ⟁ = Action indicator
- ⟡ = Entry
- ⩜ = Exit
- ⟖ = Trim
- ⚡ = Emergency
- 📊 = Info

### Entry Notification (`entry` / initial `add`)

```
⚘ LOTUS ENTRY ⟁

Token: [TICKER](link)
Chain: [CHAIN]
Amount: [NATIVE] ([USD])
Entry Price: [PRICE]
Allocation: [%]%
State: [S1/S2/S3]
Signal: [buy_signal/buy_flag/first_dip_buy/reclaimed_ema333]

Transaction: [View](link)
Time: [UTC]

⚘ Position opened
```

### Add Notification (`add` to existing position)

```
⚘ LOTUS ADD ⟁

Token: [TICKER](link)
Chain: [CHAIN]
Amount Added: [NATIVE] ([USD])
Entry Price: [PRICE]
State: [S2/S3]
Signal: [buy_flag/first_dip_buy/reclaimed_ema333/DX]

Position Size: [TOKENS] tokens
Position Value: $[USD]
Avg Entry: [PRICE]
Current P&L: $[USD] ([%]%)
Realized P&L: $[USD] ([%]%)

Transaction: [View](link)
Time: [UTC]

⚘ Position scaled up
```

### Trim Notification (`trim`)

```
⚘ LOTUS TRIM ⟁

Token: [TICKER](link)
Chain: [CHAIN]
Amount Sold: [TOKENS] tokens
Sell Price: [PRICE]
Value Extracted: $[USD]
State: [S2/S3]
Reason: [trim_flag/exhaustion]

Remaining: [TOKENS] tokens
Position Value: $[USD]
Total P&L: $[USD] ([%]%)
Realized P&L: $[USD] ([%]%)

Transaction: [View](link)
Time: [UTC]

⚘ Partial exit executed
```

### Emergency Exit Notification (`emergency_exit` from S3)

```
⚘ LOTUS EXIT ⚡

Token: [TICKER](link)
Chain: [CHAIN]
Amount Sold: [TOKENS] tokens
Sell Price: [PRICE]
Value Extracted: $[USD]
State: S3
Reason: Trend ending - final position out

Total P&L: $[USD] ([%]%)
Realized P&L: $[USD] ([%]%)

⚘ LOTUS BUYBACK
Profit: $[USD]
Swap Amount: $[USD] (10%)
Lotus Tokens: [AMOUNT] ⚘❈
Transfer: [AMOUNT] ⚘❈ → Holding Wallet
Swap TX: [View](link)
Transfer TX: [View](link)

Transaction: [View](link)
Time: [UTC]

⚘ Position closed - trend ended
```

### Position Closure Notification (Full Close)

```
⚘ LOTUS POSITION CLOSED ⟁

Token: [TICKER](link)
Chain: [CHAIN]
Timeframe: [1m/15m/1h/4h]
Final Exit: [TRIM/EMERGENCY_EXIT]

Total Invested: $[USD]
Total Extracted: $[USD]
Realized P&L: $[USD] ([%]%)
Total P&L: $[USD] ([%]%)

⚘ LOTUS BUYBACK
Profit: $[USD]
Swap Amount: $[USD] (10%)
Lotus Tokens: [AMOUNT] ⚘❈
Transfer: [AMOUNT] ⚘❈ → Holding Wallet
Swap TX: [View](link)
Transfer TX: [View](link)

Completed Trades: [COUNT]
Entry Context: [CURATOR/CHAIN/MCAP]

Time: [UTC]

⚘ Position fully closed
```

---

## 3. P&L Tracking

### Track Both Metrics

**Realized P&L (rpnl)**:
- From sells only
- `rpnl_usd` = `total_tokens_sold * avg_exit_price - total_tokens_sold * avg_entry_price`
- `rpnl_pct` = `(rpnl_usd / total_allocation_usd) * 100`

**Total P&L (total_pnl)**:
- Realized + unrealized
- `total_pnl_usd` = `rpnl_usd + current_usd_value - unrealized_cost`
- `total_pnl_pct` = `(total_pnl_usd / total_allocation_usd) * 100`

### Display Format
```
Current P&L: $[total_pnl_usd] ([total_pnl_pct]%)
Realized P&L: $[rpnl_usd] ([rpnl_pct]%)
```

---

## 4. Lotus Buyback Integration

### When to Show
- **Emergency Exit**: Show buyback info in exit notification
- **Position Closure**: Show buyback info in closure notification
- **Regular Trims**: Don't show (only on full closure)

### Buyback Info Format
```
⚘ LOTUS BUYBACK
Profit: $[profit_usd]
Swap Amount: $[swap_amount_usd] (10%)
Lotus Tokens: [lotus_tokens] ⚘❈
Transfer: [transfer_amount] ⚘❈ → Holding Wallet
Swap TX: [View](link)
Transfer TX: [View](link)
```

---

## 5. Implementation Plan

### Step 1: Update TelegramSignalNotifier

**Add new methods**:
- `send_entry_notification()` - For initial entries
- `send_add_notification()` - For scaling adds
- `send_trim_notification()` - For partial exits
- `send_emergency_exit_notification()` - For S3 full exits
- `send_position_closed_notification()` - For full closures

**Update existing methods**:
- Keep `send_buy_signal()` and `send_sell_signal()` for backward compatibility
- Add new methods that use glyphs and new format

### Step 2: Integrate in pm_core_tick.py

**After execution** (line ~2430):
```python
if exec_result.get("status") == "success":
    decision_type = act.get("decision_type", "").lower()
    
    if decision_type == "entry" or (decision_type == "add" and position.get("total_quantity", 0) == 0):
        await self.telegram_notifier.send_entry_notification(...)
    elif decision_type == "add":
        await self.telegram_notifier.send_add_notification(...)
    elif decision_type == "trim":
        await self.telegram_notifier.send_trim_notification(...)
    elif decision_type == "emergency_exit":
        await self.telegram_notifier.send_emergency_exit_notification(...)
```

**After position closure** (line ~2004):
```python
# After _swap_profit_to_lotus()
buyback_result = self._swap_profit_to_lotus(position)
await self.telegram_notifier.send_position_closed_notification(
    position=position,
    buyback_result=buyback_result
)
```

### Step 3: Data Available

**From execution result**:
- `tokens_bought` / `tokens_sold`
- `price` (USD)
- `price_native`
- `tx_hash`
- `slippage`

**From position**:
- `token_ticker`, `token_contract`, `token_chain`
- `total_quantity`
- `total_allocation_usd`, `total_extracted_usd`
- `total_pnl_usd`, `total_pnl_pct`
- `rpnl_usd`, `rpnl_pct`
- `avg_entry_price`, `avg_exit_price`
- `features.uptrend_engine_v4.state`
- `source_tweet_url`

**From decision**:
- `decision_type`
- `size_frac`
- `reasons` (has state, signals, scores)

---

## 6. Design Principles

1. **Use glyphs, not emojis** - Consistent with Lotus branding
2. **Show both rpnl and pnl** - Give full picture
3. **State context** - Show which state (S1/S2/S3) triggered action
4. **Signal context** - Show which signal (buy_flag, trim_flag, etc.)
5. **Lotus buyback** - Only on full closures, show full details
6. **Transaction links** - Always include explorer links
7. **Clean formatting** - Easy to scan, not cluttered

---

## Next Steps

1. ✅ **Implement Lotus buyback** first (simpler, foundation)
2. ✅ **Then redesign Telegram notifications** (builds on buyback info)
3. ✅ **Test with canary positions**
4. ✅ **Iterate on message format** based on feedback

---

## Notes

- **Emergency exit from S3**: Not a "bad" exit - just trend ending, get final position out
- **Retest buys**: These are `add` actions with `buy_flag` or `reclaimed_ema333` - show as "Retest Entry"
- **State transitions**: Show state context so users understand why action happened
- **P&L tracking**: Always show both realized and total P&L for full picture

