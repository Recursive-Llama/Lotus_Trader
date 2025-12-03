# Telegram Notification Design - PM System

## Overview

**Goal**: Design clear, informative Telegram notifications for all PM actions with proper context, P&L tracking, and Lotus buyback info.

**Design Principles**:
- Use **specific glyphs** (⚘𒀭 ⚘⥈ ⚘𒋻 ⚘𒉿 ⚘🝗⩜ ⚘❈)
- Show **both rpnl and total_pnl** throughout
- Include **state context** (S1/S2/S3) and **signal context** (buy_flag, trim_flag, etc.)
- **Emergency exit** can happen in S1 or S3 - not "bad", just structural exit
- **Position closure** happens on S0 transition (not on selling) - Position Summary confirms it wasn't a fakeout
- Show **Lotus buyback** info on full closures
- Keep messages **scannable** and **informative**
- **ALL CAPS** for headers

---

## 1. Available Data Sources

### From Execution Result (`exec_result`)
```python
{
    "status": "success" | "error",
    "tx_hash": str,
    "tokens_bought": float,  # For adds
    "tokens_sold": float,    # For trims/exits
    "price": float,          # USD price
    "price_native": float,   # Native price
    "slippage": float        # Slippage %
}
```

### From Position (`position`)
```python
{
    "id": str,
    "token_ticker": str,
    "token_contract": str,
    "token_chain": str,
    "timeframe": str,  # "1m", "15m", "1h", "4h"
    "total_quantity": float,
    "total_allocation_usd": float,
    "total_extracted_usd": float,
    "total_pnl_usd": float,
    "total_pnl_pct": float,
    "rpnl_usd": float,      # Realized P&L
    "rpnl_pct": float,      # Realized P&L %
    "avg_entry_price": float,
    "avg_exit_price": float,
    "current_usd_value": float,
    "total_tokens_bought": float,
    "total_tokens_sold": float,
    "source_tweet_url": str,
    "features": {
        "uptrend_engine_v4": {
            "state": "S0" | "S1" | "S2" | "S3",
            "buy_signal": bool,
            "buy_flag": bool,
            "trim_flag": bool,
            "emergency_exit": bool,
            "first_dip_buy_flag": bool,
            "reclaimed_ema333": bool,
            ...
        },
        "pm_execution_history": {
            "lotus_buyback": {...}  # On full closure
        }
    }
}
```

### From Decision/Action (`act`)
```python
{
    "decision_type": "entry" | "add" | "trim" | "emergency_exit",
    "size_frac": float,  # Fraction of allocation (add) or position (trim)
    "reasons": {
        "flag": str,  # "buy_signal", "buy_flag", "trim_flag", etc.
        "state": str,  # "S1", "S2", "S3"
        "a_score": float,
        "e_score": float,
        "ts_score": float,  # For S1 entries
        "ox_score": float,  # For S2/S3 trims
        "dx_score": float,  # For S3 entries
        ...
    },
    "lever_diag": {
        "a_e_components": {
            "a_final": float,
            "e_final": float,
            ...
        }
    }
}
```

---

## 2. Action Types & Context

### Entry (Initial Position)
- **Trigger**: `decision_type == "entry"` OR (`decision_type == "add"` AND `total_quantity == 0`)
- **States**: S1, S2, S3
- **Signals**: 
  - S1: `buy_signal`
  - S2: `buy_flag` (retest at EMA333)
  - S3: `first_dip_buy_flag` or `reclaimed_ema333`
- **Note**: Entry is just the first buy - all subsequent buys are "adds"

### Add (Scaling Up)
- **Trigger**: `decision_type == "add"` AND `total_quantity > 0`
- **States**: S2, S3
- **Signals**:
  - S2: `buy_flag` → "Retest add (S2)"
  - S3: `buy_flag` → "DX buy (S3)"
  - S3: `reclaimed_ema333` → "Auto-rebuy (S3)"

### Trim (Partial Exit)
- **Trigger**: `decision_type == "trim"`
- **States**: S2, S3
- **Signals**:
  - S2: `trim_flag` (OX ≥ 0.65)
  - S3: `trim_flag` (exhaustion trim)

### Emergency Exit (Full Exit - Any State)
- **Trigger**: `decision_type == "emergency_exit"`
- **States**: S1, S3 (can happen in any state)
- **Signal**: `emergency_exit` (structural exit, not "bad")
- **Note**: This is a **full exit** (sells all tokens), but position closure happens later on S0 transition

### Position Summary (Full Closure Confirmation)
- **Trigger**: Position `status == "watchlist"` AND `total_quantity == 0` AND state transitioned to S0
- **Context**: Confirms position closure after S3 → S0 transition (not a fakeout)
- **Timing**: Happens **after** emergency_exit (which already sold everything)
- **Includes**: Lotus buyback info, R/R metrics, trade summary
- **Note**: This is the **confirmation** that the trend ended (S0 transition), not the exit itself

---

## 3. Message Format Design

### Glyph System
- **⚘𒀭** = Entry (LOTUS TRENCHER ENTRY)
- **⚘⥈** = Add (LOTUS TRENCHER ADD)
- **⚘𒋻** = Trim (LOTUS TRENCHER TRIM)
- **⚘𒉿** = Exit (LOTUS TRENCHER EXIT)
- **⚘🝗⩜** = Position Summary (LOTUS TRENCHER POSITION SUMMARY)
- **⚘❈** = Lotus token symbol
- **⚘⟁⌖** = Standard footer/separator

### Entry Notification

```
⚘𒀭 LOTUS TRENCHER ENTRY ⚘⟁⌖

Token: [TICKER](link)
Chain: [CHAIN]
Timeframe: [1m/15m/1h/4h]

Amount: [NATIVE] ([USD])
Entry Price: [PRICE] [NATIVE]
Allocation: [%]% of portfolio

State: [S1/S2/S3]
Signal: [buy_signal/buy_flag/first_dip_buy/reclaimed_ema333]
A/E: [A]/[E]

Transaction: [View](link)
Time: [UTC]

⚘𒀭 POSITION OPENED ⚘⟁⌖
```

**Key Info**:
- Show state and signal context
- Show A/E scores (entry quality)
- Show allocation percentage
- Link to transaction

### Add Notification

```
⚘⥈ LOTUS TRENCHER ADD ⚘⟁⌖

Token: [TICKER](link)
Chain: [CHAIN]
Timeframe: [1m/15m/1h/4h]

Amount Added: [NATIVE] ([USD])
Entry Price: [PRICE] [NATIVE]
Size: [size_frac]% of remaining allocation

State: [S2/S3]
Signal: [buy_flag/reclaimed_ema333/DX]
A/E: [A]/[E]

Position Size: [TOKENS] tokens
Position Value: $[USD]
Avg Entry: [PRICE] [NATIVE]

Current P&L: $[total_pnl_usd] ([total_pnl_pct]%)
Realized P&L: $[rpnl_usd] ([rpnl_pct]%)

Transaction: [View](link)
Time: [UTC]

⚘⥈ POSITION SCALED UP ⚘⟁⌖
```

**Key Info**:
- Show position context (size, value, avg entry)
- Show both current and realized P&L
- Show state and signal (retest vs DX buy)
- Show size_frac (how much of remaining allocation)

### Trim Notification

```
⚘𒋻 LOTUS TRENCHER TRIM ⚘⟁⌖

Token: [TICKER](link)
Chain: [CHAIN]
Timeframe: [1m/15m/1h/4h]

Amount Sold: [TOKENS] tokens
Sell Price: [PRICE] [NATIVE]
Value Extracted: $[USD]
Size: [size_frac]% of position

State: [S2/S3]
Signal: [trim_flag/exhaustion]
E Score: [E]

Remaining: [TOKENS] tokens
Position Value: $[USD]

Current P&L: $[total_pnl_usd] ([total_pnl_pct]%)
Realized P&L: $[rpnl_usd] ([rpnl_pct]%)

Transaction: [View](link)
Time: [UTC]

⚘𒋻 PARTIAL PROFIT SECURED ⚘𒋻
```

**Key Info**:
- Show what was sold and what remains
- Show both P&L metrics
- Show E score (exit assertiveness)
- Show state and signal context

### Emergency Exit Notification

```
⚘𒉿 LOTUS TRENCHER EXIT ⚘⟁⌖

Token: [TICKER](link)
Chain: [CHAIN]
Timeframe: [1m/15m/1h/4h]

Amount Sold: [TOKENS] tokens
Sell Price: [PRICE] [NATIVE]
Value Extracted: $[USD]

State: [S1/S3]
Reason: [Structural exit / Trend ending]
E Score: [E]

Total P&L: $[total_pnl_usd] ([total_pnl_pct]%)
Realized P&L: $[rpnl_usd] ([rpnl_pct]%)

Transaction: [View](link)
Time: [UTC]

⚘𒉿 FINAL EXIT - TREND ENDED ⚘𒉿
```

**Key Info**:
- Can happen in **S1 or S3** (structural exit)
- Emphasize this is **not a bad exit** - just structural/trend ending
- Show final P&L
- Show state context
- **Note**: Position closure happens later on S0 transition (not here)

### Position Summary Notification (S3 → S0 Confirmation)

```
⚘🝗⩜ LOTUS TRENCHER POSITION SUMMARY ⚘⟁⌖

Token: [TICKER](link)
Chain: [CHAIN]
Timeframe: [1m/15m/1h/4h]

Final Exit: [EMERGENCY_EXIT]
Exit Reason: S3 → S0 transition (trend ended, not fakeout)

Total Invested: $[total_allocation_usd]
Total Extracted: $[total_extracted_usd]
Realized P&L: $[rpnl_usd] ([rpnl_pct]%)
Total P&L: $[total_pnl_usd] ([total_pnl_pct]%)

Hold Time: [DAYS] days
R/R: [rr]
Return: [return]x
Max Drawdown: [max_drawdown]%
Max Gain: [max_gain]x

⚘❈ LOTUS BUYBACK⚘❈
Profit: $[profit_usd]
Swap Amount: $[swap_amount_usd] (10%)
Lotus Tokens: [lotus_tokens] ⚘❈
Transfer: [transfer_amount] ⚘❈ → Holding Wallet
Swap TX: [View](link)
Transfer TX: [View](link)

Completed Trades: [COUNT]
Entry Context: [CURATOR/CHAIN/MCAP]

Time: [UTC]

⚘🝗⩜ TREND ENDED PROFIT SECURED ⚘🝗⩜
```

**Key Info**:
- This is the **confirmation** that S3 → S0 transition happened (not a fakeout)
- Happens **after** emergency_exit (which already sold everything)
- Position closure happens on **S0 transition** (not on selling)
- Shows complete trade summary with R/R metrics
- Includes Lotus buyback details

**Key Info**:
- Show complete trade summary
- Show R/R metrics (risk/reward)
- Show Lotus buyback details
- Show entry context (curator, chain, mcap bucket)
- Show hold time and outcome

---

## 4. Information Hierarchy

### Always Show (All Notifications)
1. **Token info**: Ticker, chain, timeframe
2. **Action details**: Amount, price, transaction link
3. **State context**: S1/S2/S3
4. **Signal context**: Which signal triggered (buy_flag, trim_flag, etc.)
5. **Time**: UTC timestamp

### Show for Entries/Adds
- Allocation percentage
- A/E scores
- Position size (for adds)
- Current P&L (for adds)

### Show for Trims/Exits
- Amount sold vs remaining
- E score
- Both P&L metrics (current and realized)
- Position value

### Show for Full Closures
- Complete trade summary
- R/R metrics
- Hold time
- Lotus buyback details
- Entry context

---

## 5. P&L Display Strategy

### Two Metrics Always Shown

**Realized P&L (rpnl)**:
- From sells only
- `rpnl_usd` = realized profit from exits
- `rpnl_pct` = percentage return on sold portion
- **Shown as**: `Realized P&L: $[rpnl_usd] ([rpnl_pct]%)`

**Total P&L (total_pnl)**:
- Realized + unrealized
- `total_pnl_usd` = rpnl + current position value - cost basis
- `total_pnl_pct` = percentage return on total allocation
- **Shown as**: `Current P&L: $[total_pnl_usd] ([total_pnl_pct]%)`

### When to Show Which

**For Entries**:
- No P&L yet (position just opened)

**For Adds**:
- Show both (position has unrealized P&L, may have some realized from previous trims)

**For Trims**:
- Show both (realized from this trim, total includes remaining position)

**For Emergency Exits**:
- Show both (final realized P&L, total should match realized if fully closed)

**For Position Closed**:
- Show both (final summary)

---

## 6. Lotus Buyback Display

### When to Show
- **Only on Position Summary** (after S3 → S0 transition confirmed)
- **Not on emergency_exit** (that's just the sell notification)
- Show in "Position Summary" notification (confirmation it wasn't a fakeout)

### What to Show
```
⚘ LOTUS BUYBACK
Profit: $[profit_usd]
Swap Amount: $[swap_amount_usd] (10%)
Lotus Tokens: [lotus_tokens] ⚘❈
Transfer: [transfer_amount] ⚘❈ → Holding Wallet
Swap TX: [View](link)
Transfer TX: [View](link)
```

### If Buyback Failed
```
⚘ LOTUS BUYBACK
Status: Failed
Error: [error_message]
```

---

## 7. Signal Context Display

### Entry Signals
- **S1**: `buy_signal` → "Entry zone (S1)"
- **S2**: `buy_flag` → "Retest buy (S2)"
- **S3**: `first_dip_buy_flag` → "First dip buy (S3)"
- **S3**: `reclaimed_ema333` → "Reclaimed EMA333 (S3)"

### Add Signals
- **S2**: `buy_flag` → "Retest add (S2)"
- **S3**: `buy_flag` → "DX buy (S3)"
- **S3**: `reclaimed_ema333` → "Auto-rebuy (S3)"

### Trim Signals
- **S2**: `trim_flag` → "Profit trim (S2)"
- **S3**: `trim_flag` → "Exhaustion trim (S3)"

### Exit Signals
- **S1**: `emergency_exit` → "Structural exit (S1)"
- **S3**: `emergency_exit` → "Trend ending (S3)"

---

## 8. Design Decisions

### Why Glyphs Over Emojis?
- **Consistent branding**: ⚘ is Lotus symbol
- **Professional appearance**: Less cluttered
- **Better readability**: Clearer visual hierarchy
- **Cross-platform**: Glyphs render consistently

### Why Show Both P&L Metrics?
- **Realized P&L**: What we've actually locked in from sells
- **Total P&L**: Full picture including unrealized gains/losses
- **Together**: Complete financial picture

### Why Show State Context?
- **S1/S2/S3**: Shows where we are in the trend
- **Helps understand**: Why this action happened
- **Learning**: See which states produce which outcomes

### Why Show Signal Context?
- **buy_flag vs buy_signal**: Different entry quality
- **trim_flag vs emergency_exit**: Different exit reasons
- **Helps understand**: What triggered the action

### Why Emergency Exit Isn't "Bad"?
- **Emergency exit (S1 or S3)**: Structural exit when trend structure breaks
- **Not a panic**: It's a planned exit based on engine signals
- **Positive framing**: "Structural exit" or "Trend ending - final position out"
- **Position closure**: Happens later on S0 transition (confirmation it wasn't a fakeout)

---

## 9. Implementation Notes

### Notification Triggers

1. **After successful execution** (line ~2679 in pm_core_tick.py):
   - Check `exec_result.get("status") == "success"`
   - Determine notification type from `decision_type` and `total_quantity`
   - Call appropriate notification method

2. **After position closure** (line ~2204 in pm_core_tick.py):
   - After position marked as `watchlist`
   - Include Lotus buyback info if available
   - Call position closed notification

### Data Collection

For each notification, collect:
- Position data (fresh fetch after execution)
- Execution result
- Decision/action data
- Uptrend engine signals (from `features.uptrend_engine_v4`)
- Lotus buyback info (from `features.pm_execution_history.lotus_buyback`)

### Error Handling

- If notification fails: Log error, don't block execution
- If data missing: Show "N/A" or skip field
- If Telegram unavailable: Fail gracefully, retry later

---

## 10. Example Messages

### Entry (S1 buy_signal)
```
⚘𒀭 LOTUS TRENCHER ENTRY ⚘⟁⌖

Token: PEPE
Chain: base
Timeframe: 1h

Amount: 0.1000 ETH ($250.00)
Entry Price: 0.00000123 ETH
Allocation: 2.5% of portfolio

State: S1
Signal: buy_signal
A/E: 0.65/0.35

Transaction: [View on Basescan](link)
Time: 14:30 UTC

⚘𒀭 POSITION OPENED ⚘⟁⌖
```

### Add (S2 retest)
```
⚘⥈ LOTUS TRENCHER ADD ⚘⟁⌖

Token: PEPE
Chain: base
Timeframe: 1h

Amount Added: 0.0500 ETH ($125.00)
Entry Price: 0.00000120 ETH
Size: 30% of remaining allocation

State: S2
Signal: buy_flag (retest)
A/E: 0.70/0.30

Position Size: 150,000 tokens
Position Value: $300.00
Avg Entry: 0.00000122 ETH

Current P&L: $25.00 (+10.0%)
Realized P&L: $0.00 (0.0%)

Transaction: [View on Basescan](link)
Time: 15:45 UTC

⚘⥈ POSITION SCALED UP ⚘⟁⌖
```

### Trim (S3 exhaustion)
```
⚘𒋻 LOTUS TRENCHER TRIM ⚘⟁⌖

Token: PEPE
Chain: base
Timeframe: 1h

Amount Sold: 50,000 tokens
Sell Price: 0.00000246 ETH
Value Extracted: $123.00
Size: 33% of position

State: S3
Signal: trim_flag (exhaustion)
E Score: 0.75

Remaining: 100,000 tokens
Position Value: $246.00

Current P&L: $119.00 (+47.6%)
Realized P&L: $61.50 (+24.6%)

Transaction: [View on Basescan](link)
Time: 16:20 UTC

⚘𒋻 PARTIAL PROFIT SECURED ⚘𒋻
```

### Emergency Exit (S3)
```
⚘𒉿 LOTUS TRENCHER EXIT ⚘⟁⌖

Token: PEPE
Chain: base
Timeframe: 1h

Amount Sold: 100,000 tokens
Sell Price: 0.00000250 ETH
Value Extracted: $250.00

State: S3
Reason: Trend ending
E Score: 0.80

Total P&L: $119.00 (+47.6%)
Realized P&L: $119.00 (+47.6%)

Transaction: [View on Basescan](link)
Time: 17:00 UTC

⚘𒉿 FINAL EXIT - TREND ENDED ⚘𒉿
```

### Position Summary (S3 → S0 Confirmation, with buyback)
```
⚘🝗⩜ LOTUS TRENCHER POSITION SUMMARY ⚘⟁⌖

Token: PEPE
Chain: base
Timeframe: 1h

Final Exit: EMERGENCY_EXIT
Exit Reason: S3 → S0 transition (trend ended, not fakeout)

Total Invested: $250.00
Total Extracted: $369.00
Realized P&L: $119.00 (+47.6%)
Total P&L: $119.00 (+47.6%)

Hold Time: 2.5 days
R/R: 1.42
Return: 1.48x
Max Drawdown: 12.0%
Max Gain: 2.0x

⚘❈ LOTUS BUYBACK⚘❈
Profit: $119.00
Swap Amount: $11.90 (10%)
Lotus Tokens: 1,000.00 ⚘❈
Transfer: 690.00 ⚘❈ → Holding Wallet
Swap TX: [View on Solscan](link)
Transfer TX: [View on Solscan](link)

Completed Trades: 1
Entry Context: @0xdetweiler / base / 1m-2m mcap

Time: 18:00 UTC

⚘🝗⩜ TREND ENDED PROFIT SECURED ⚘🝗⩜
```

---

## Next Steps

1. ✅ **Design complete** - Message formats defined
2. ⏳ **Implementation** - Update TelegramSignalNotifier with new methods
3. ⏳ **Integration** - Wire up in pm_core_tick.py
4. ⏳ **Testing** - Test with canary positions

