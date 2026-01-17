# DREAM Trade Analysis - Why RR=12.79?

## Trade Summary

**Token**: DREAM  
**Timeframe**: 1m  
**Entry**: $0.00130289 (2026-01-07 16:51 UTC)  
**Exit**: $0.001455 (2026-01-08 06:20 UTC)  
**Hold Time**: 0.56 days (~13.5 hours)

## Performance Metrics

- **Return**: 11.67%
- **Max Drawdown**: 0.91% (very small!)
- **RR**: 12.79 = 11.67% / 0.91%
- **PnL**: $0.56 (6.92%)
- **Outcome**: "big_win"

## Why RR is So High

**The Math**:
```
RR = return_pct / max_drawdown
RR = 11.67% / 0.91% = 12.79
```

**Key Insight**: The drawdown was **extremely small** (0.91%) relative to the return (11.67%). This means:
- The trade had very little risk (price barely dropped from entry)
- But produced a good return
- Result: High RR ratio

**This is a legitimate high RR trade** - not an error or outlier in the calculation. The pattern (S1 entry on 1m timeframe) produced a trade with minimal drawdown and good return.

## Could We Have Done Better?

The trade data shows:
- **Could exit better**: Missed RR of 25.98!
  - Best exit price: $0.001764 (vs actual $0.001455)
  - Best exit time: 2026-01-07 18:46 UTC (vs actual 06:20 UTC next day)
  - We exited ~21% early

- **Could enter better**: Missed RR of 1.0
  - Best entry price: $0.001291 (vs actual $0.00130289)
  - Best entry time: 2026-01-07 19:12 UTC (vs actual 16:51 UTC)
  - We entered slightly early

## Conclusion

**This is NOT an outlier to cap** - it's valuable information:
1. The pattern (1m S1 entry) CAN produce high RR trades
2. Even though we only hit 1 in 10 trades, when we hit, we hit big
3. The high RR is legitimate (small drawdown, good return)
4. We should learn from this pattern, not discard it

**Recommendation**: Don't cap outliers. Instead:
- Use robust statistics (median, trimmed mean) for small samples
- Track both average RR and max RR
- Use edge (delta_rr) instead of raw RR for learning
- Consider win rate AND RR magnitude together

