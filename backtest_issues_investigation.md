# Backtest Issues Investigation

## Findings

### 1. Time Range Issue
- **Expected**: 7 days of data
- **Actual**: ~4.2 days (2025-10-27 to 2025-10-31)
- **Root Cause**: Last data timestamp is `2025-10-29T06:00:00`, but backtest continues generating hourly timestamps until `2025-10-31T09:13:44`
- **Fix Needed**: Stop the hourly loop when no more OHLC data is available

### 2. Geometry Data
- **Status**: ✅ Geometry exists in `features.geometry` (confirmed in DB)
- **Problem**: Chart doesn't visualize geometry data
- **Missing**: S/R levels as horizontal lines, swing points, geometry context

### 3. Chart Visualization
- **Current**: Basic price line + colored dots for states + state timeline
- **Missing**:
  - EMA bands (20, 60, 144, 250, 333)
  - S/R levels (horizontal lines)
  - Buy signals (where S2 entries would occur based on aggressiveness)
  - Volume chart
  - State transition markers
  - Similar to `geometry_build_daily.py` chart style

### 4. Data Analysis
- **States Found**: S1 (2 points), S2 (100 points)
- **Data Available**: States, scores, levels, supports, diagnostics
- **Not Visualized**: Entry signals, S/R proximity, EMA positions, geometry context

## Required Fixes

1. **Stop when data ends**: Check if `rows_1h` is empty before continuing loop
2. **Fetch full OHLC for chart**: Get all price/volume data for the backtest period
3. **Build rich chart**:
   - Price line
   - EMA series (20, 60, 144, 250, 333)
   - S/R levels as horizontal lines (from `features.geometry`)
   - State transitions (vertical lines or color changes)
   - Buy signals (markers where S2 entries would occur)
   - Volume subplot
   - State timeline subplot
4. **Extract geometry**: Use `features.geometry.levels.sr_levels` for S/R visualization

## Sample Data Structure

```json
{
  "state": "S2",
  "supports": {
    "current_sr_level": 1.228,
    "halo": 0.03
  },
  "levels": {
    "ema20": 1.240,
    "ema60": 1.232,
    "base_sr_level": 1.212,
    "flipped_sr_levels": [...],
    "current_price": 1.245
  },
  "scores": {...}
}
```

## Next Steps

1. Modify `hourly_range` loop to stop when no data available
2. Rewrite `generate_results_chart` to include:
   - Full OHLC data fetch for chart
   - EMA calculation from TA data
   - Geometry S/R levels extraction
   - Buy signal detection from S2 payloads
   - Rich visualization similar to `geometry_build_daily.py`

