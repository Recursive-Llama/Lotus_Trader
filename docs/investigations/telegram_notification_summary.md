# Telegram Notification Design - Summary

## Key Design Decisions

### 1. Glyph System (ALL CAPS)
- **⚘𒀭** = Entry: `⚘𒀭 LOTUS TRENCHER ENTRY ⚘⟁⌖`
- **⚘⥈** = Add: `⚘⥈ LOTUS TRENCHER ADD ⚘⟁⌖`
- **⚘𒋻** = Trim: `⚘𒋻 LOTUS TRENCHER TRIM ⚘⟁⌖`
- **⚘𒉿** = Exit: `⚘𒉿 LOTUS TRENCHER EXIT ⚘⟁⌖`
- **⚘🝗⩜** = Position Summary: `⚘🝗⩜ LOTUS TRENCHER POSITION SUMMARY ⚘⟁⌖`
- **⚘❈** = Lotus token symbol
- **⚘⟁⌖** = Standard footer/separator

### 2. Action Types

**Entry**: First buy only (`decision_type == "entry"` OR `add` with `total_quantity == 0`)
- S1: `buy_signal` → "Entry zone (S1)"
- S2: `buy_flag` → "Retest buy (S2)"
- S3: `first_dip_buy_flag` → "First dip buy (S3)"
- S3: `reclaimed_ema333` → "Reclaimed EMA333 (S3)"

**Add**: All subsequent buys (`decision_type == "add"` AND `total_quantity > 0`)
- S2: `buy_flag` → "Retest add (S2)"
- S3: `buy_flag` → "DX buy (S3)"
- S3: `reclaimed_ema333` → "Auto-rebuy (S3)"

**Trim**: Partial exits (`decision_type == "trim"`)
- S2: `trim_flag` → "Profit trim (S2)"
- S3: `trim_flag` → "Exhaustion trim (S3)"

**Emergency Exit**: Full exit (`decision_type == "emergency_exit"`)
- **S1 or S3**: Can happen in any state
- S1: `emergency_exit` → "Structural exit (S1)"
- S3: `emergency_exit` → "Trend ending (S3)"
- **Note**: This sells everything, but position closure happens later on S0 transition

**Position Summary**: Full closure confirmation (`status == "watchlist"` AND `total_quantity == 0` AND state is S0)
- **Timing**: After S3 → S0 transition (confirms it wasn't a fakeout)
- **Includes**: Complete trade summary, R/R metrics, Lotus buyback
- **Note**: Emergency exit already happened (sold everything), this is the closure confirmation

### 3. P&L Display

**Always show both metrics**:
- `Current P&L: $[total_pnl_usd] ([total_pnl_pct]%)` - Realized + unrealized
- `Realized P&L: $[rpnl_usd] ([rpnl_pct]%)` - From sells only

### 4. Position Closure Flow

**Important**: Positions get closed on **S0 transition** (not on selling)

1. **Emergency Exit** (sells all tokens) → Notification: `⚘𒉿 LOTUS TRENCHER EXIT ⚘⟁⌖`
2. **State transitions to S0** (confirms it wasn't a fakeout)
3. **Position Summary** (closure confirmation) → Notification: `⚘🝗⩜ LOTUS TRENCHER POSITION SUMMARY ⚘⟁⌖`
   - Includes Lotus buyback info
   - Includes R/R metrics
   - Includes complete trade summary

### 5. Lotus Buyback

- **Only shown in Position Summary** (not on emergency exit)
- Shows: Profit, swap amount (10%), tokens received, transfer amount (69%), tx links
- Format: `⚘❈ LOTUS BUYBACK⚘❈`

---

## Notification Triggers

1. **After execution** (line ~2679 in pm_core_tick.py):
   - Entry: `decision_type == "entry"` OR (`decision_type == "add"` AND `total_quantity == 0`)
   - Add: `decision_type == "add"` AND `total_quantity > 0`
   - Trim: `decision_type == "trim"`
   - Emergency Exit: `decision_type == "emergency_exit"`

2. **After position closure** (line ~2204 in pm_core_tick.py):
   - After position marked as `watchlist` AND state is S0
   - This is the **Position Summary** (confirmation S3 → S0 transition)
   - Includes Lotus buyback info

---

## Key Clarifications

1. **Entry vs Add**: Entry is just the first buy, all subsequent buys are adds
2. **Emergency Exit**: Can happen in S1 or S3 (not just S3)
3. **Position Closure**: Happens on S0 transition (not on selling)
4. **Position Summary**: Confirmation that S3 → S0 transition happened (not a fakeout)
5. **Lotus Buyback**: Only shown in Position Summary (not on emergency exit)

---

## Next Steps

1. ✅ **Design complete** - Message formats defined with correct glyphs
2. ⏳ **Implementation** - Update TelegramSignalNotifier with new methods
3. ⏳ **Integration** - Wire up in pm_core_tick.py
4. ⏳ **Testing** - Test with canary positions

