# 1h RR Mismatch Explanation

## The Question

**Learning configs show**: rr_short=0.041  
**Actual avg RR**: -0.613  
**But**: The trade was profitable (PnL=$1.39, 27.1%)

**Why is RR negative if the trade was profitable?**

## Understanding RR Calculation

**RR Formula**:
```
RR = return_pct / max_drawdown
```

Where:
- `return_pct` = (exit_price - entry_price) / entry_price
- `max_drawdown` = (entry_price - min_price) / entry_price

## The 1h Trade Details

From the data:
- **MACARON trade**: PnL=$1.39 (27.1% return)
- **RR**: -0.308

## How Can RR Be Negative?

**RR is negative when**:
- The trade had a **loss** (exit < entry), OR
- The trade had a **gain** but the **max_drawdown was larger than the return**

**Example**:
- Entry: $1.00
- During trade: Price dropped to $0.50 (min_price) → max_drawdown = 50%
- Exit: $1.20 → return = 20%
- **RR = 20% / 50% = 0.4** (positive, but low)

**But if**:
- Entry: $1.00
- During trade: Price dropped to $0.30 (min_price) → max_drawdown = 70%
- Exit: $1.20 → return = 20%
- **RR = 20% / 70% = 0.29** (still positive, but very low)

**Or if the trade had a loss**:
- Entry: $1.00
- During trade: Price dropped to $0.50 (min_price) → max_drawdown = 50%
- Exit: $0.80 → return = -20%
- **RR = -20% / 50% = -0.4** (negative)

## Why 1h Shows RR=-0.613 But PnL Was Positive

**Possible explanations**:

1. **Multiple trades aggregated**: The "1h" timeframe might have multiple trades, and we're seeing the average RR, not the individual trade RR

2. **Different calculation methods**: 
   - PnL might be calculated from actual executed trades (accounting for trims/re-entries)
   - RR might be calculated from OHLC data (single entry/exit model)

3. **The profitable trade might not be the one in learning_configs**: 
   - Learning configs might be using an older trade
   - The profitable MACARON trade might be newer

4. **RR calculation issue**: The RR might be calculated incorrectly for this specific trade

## The Learning Configs Issue

**Learning configs show**: rr_short=0.041, n=1

**This suggests**:
- Only 1 trade has been processed for 1h timeframe
- That trade had RR=0.041 (slightly positive)
- But the actual average RR from all 1h trades is -0.613

**Why the mismatch?**
- The learning system might not have processed all 1h trades yet
- Or the RR calculation in learning_configs is using a different method
- Or there's a timing issue (old data vs new data)

## Recommendation

**Investigate**:
1. Check which 1h trade was used for learning_configs
2. Compare its RR calculation with the actual trade data
3. Verify all 1h trades have been processed by the learning system

