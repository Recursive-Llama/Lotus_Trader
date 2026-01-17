# RR vs ROI Analysis - Why RR Might Not Be The Best Metric

## The 1h Trade Mystery

### Trade 1 (MACARON/ZERA?)
- **PnL**: $1.39 (27.12% profit) ✅
- **Return**: -12.54% ❌
- **Max Drawdown**: 40.70%
- **RR**: -0.308 (negative!)

### Trade 2
- **PnL**: $0.10 (0.91% profit) ✅
- **Return**: -12.54% ❌
- **Max Drawdown**: 14.43%
- **RR**: -0.917 (negative!)

## The Problem

**RR is calculated as**: `RR = return_pct / max_drawdown`

Where `return_pct = (exit_price - entry_price) / entry_price`

**But PnL is calculated differently** - it accounts for:
- Multiple entries (adds)
- Multiple exits (trims)
- Weighted average entry/exit prices
- Actual USD extracted vs allocated

**Result**: 
- PnL can be positive (we made money)
- But return_pct can be negative (exit price < entry price)
- This happens when we trim at higher prices, then exit remaining at lower price

## Example Scenario

1. **Entry**: Buy 100 tokens at $1.00 = $100 allocated
2. **Price goes up**: Trim 50 tokens at $1.50 = $75 extracted (realized $25 profit)
3. **Price drops**: Exit remaining 50 tokens at $0.80 = $40 extracted
4. **Total extracted**: $75 + $40 = $115
5. **Total allocated**: $100
6. **PnL**: $15 profit (15% ROI) ✅

**But RR calculation uses**:
- Entry price: $1.00
- Exit price: $0.80 (last exit)
- Return: (0.80 - 1.00) / 1.00 = -20% ❌
- Max drawdown: (1.00 - min_price) / 1.00
- RR: -20% / max_drawdown = negative

## Why This Matters

**Current Learning System**:
- Uses RR from `completed_trades` summary
- RR is based on entry/exit price (simplified model)
- Doesn't account for trims/re-entries properly
- Can show negative RR even when trade was profitable

**This breaks learning**:
- Profitable trades get negative RR
- System learns "this pattern is bad" when it's actually good
- Timeframe weights get skewed

## Proposed Solution: Use ROI Instead

**ROI (Return on Investment)**:
```
ROI = (total_extracted_usd - total_allocation_usd) / total_allocation_usd
```

**Benefits**:
- ✅ Accounts for all entries/exits
- ✅ Matches actual PnL
- ✅ Positive when we make money, negative when we lose
- ✅ Already calculated in `rpnl_pct` field

**Then convert to Edge**:
```
edge = (avg_roi - baseline_roi) * reliability_score * support_score
```

Where:
- `baseline_roi` = average ROI across all trades
- `reliability_score` = 1 / (1 + variance_roi)
- `support_score` = based on sample size

## Comparison

### Current (RR-based):
- ❌ Can be negative for profitable trades
- ❌ Doesn't account for trims/re-entries
- ❌ Based on simplified entry/exit model
- ✅ Normalizes by risk (drawdown)

### Proposed (ROI-based):
- ✅ Always positive when profitable
- ✅ Accounts for all trading activity
- ✅ Matches actual PnL
- ❌ Doesn't normalize by risk (but we can add that)

## Recommendation

**Switch to ROI-based learning**:
1. Use `rpnl_pct` (ROI) instead of `rr` for learning
2. Calculate edge as: `edge = (roi - baseline_roi) * reliability * support`
3. Optionally add risk adjustment: `edge_risk_adjusted = edge / (1 + avg_drawdown)`

This will give us:
- More accurate learning (profitable = positive edge)
- Better timeframe weights
- Better pattern mining

