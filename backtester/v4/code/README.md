# Uptrend Engine v4 Backtesting

This directory contains the backtesting infrastructure for **Uptrend Engine v4**.

## Architecture

**Key improvements over v3:**
- Uses `ta_utils.py` for all TA calculations (single source of truth)
- Calls engine methods directly (no duplicate logic)
- Preserves all diagnostics in output
- Simplified state machine (no acceleration patterns, no persistence)

## Files

- **`backtest_uptrend_v4.py`**: Main backtesting script
  - Extends `UptrendEngineV4`
  - Overrides data access for time-filtered simulation
  - Generates JSON results and charts
  
- **`run_backtest.py`**: Single token workflow script
  - Backfills 1h data
  - Builds geometry (no charts)
  - Runs TA Tracker
  - Runs backtest
  
- **`run_batch_backtest.py`**: Batch runner
  - Runs workflow for multiple tokens
  - Excludes ALCH, ASTER, GIGGLE by default
  - Provides summary of results

## Usage

### Single Token

```bash
cd backtester/v4/code
python3 run_backtest.py DREAMS 14
```

### Direct Backtest (if data already prepared)

```bash
cd backtester/v4/code
python3 backtest_uptrend_v4.py DREAMS 14
```

### Batch

```bash
cd backtester/v4/code
python3 run_batch_backtest.py
```

Or specific tokens:
```bash
python3 run_batch_backtest.py DREAMS BREW POLYTALE --days 21
```

## Output

Results are saved to `backtester/v4/backests/`:
- `backtest_results_v4_{TICKER}_{TIMESTAMP}.json` - Full results with diagnostics
- `backtest_results_v4_{TICKER}_{TIMESTAMP}.png` - Visualization chart

## Chart Features

Charts include:
- Price and all EMAs (20, 30, 60, 144, 250, 333)
- State markers (S0=red square, S1=blue circle, S2=orange triangle, S3=green star)
- Buy signals (lime diamond)
- Trim flags (yellow X)
- TS threshold markers (0.0, 0.3, 0.6, 0.9, 0.58)

## Diagnostics

All diagnostics are preserved in JSON output:
- `buy_check`: Entry zone, slope OK, TS OK, actual slope values
- `s2_retest_check`: S2 retest buy conditions
- `scores`: OX, DX, EDX scores
- Full condition breakdowns

## Differences from v3

1. **TA calculations**: Uses `ta_utils.py` instead of importing from `ta_tracker.py`
2. **State machine**: Simplified (no acceleration patterns, no persistence)
3. **Buy signal**: Directly from S1 (no separate S2 entry state)
4. **Diagnostics**: Always populated (not optional)
5. **Engine calls**: Calls engine methods directly where possible

