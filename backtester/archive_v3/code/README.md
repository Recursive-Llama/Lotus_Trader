# Backtester V3

Backtesting workflow for UptrendEngineV3 - EMA Phase System.

## Structure

- `v3/code/` - Backtest scripts
- `v3/backests/` - Test results (JSON and PNG charts)

## Usage

```bash
# Run full workflow for a token
python3 backtester/v3/code/run_backtest.py DREAMS 14

# Or run backtest directly (assumes data/geometry/TA already exists)
python3 backtester/v3/code/backtest_uptrend_v3.py DREAMS 14

# Run batch backtest for all active tokens
python3 backtester/v3/code/run_batch_backtest.py

# Run batch backtest for specific tokens
python3 backtester/v3/code/run_batch_backtest.py DREAMS DLMM BREW
```

## Workflow Steps

1. **Backfill 1h OHLCV data** - Fetches historical data from GeckoTerminal
2. **Build Geometry** - Generates S/R levels (needed for S3 exits, no charts during backtest)
3. **Run TA Tracker** - Computes technical indicators (EMAs, RSI, ADX, etc.)
4. **Run Backtest** - Simulates engine execution hour-by-hour

## Output

- `backtester/v3/backests/backtest_results_v3_{TICKER}_{timestamp}.json` - Full results
- `backtester/v3/backests/backtest_results_{TICKER}_{timestamp}.png` - Chart visualization

## Chart Features

- **Red triangles (v)**: OX sell zones (trim opportunities)
- **Green triangles (^)**: DX buy signals (price in discount zone + DX >= threshold)
- **Orange circles**: DX near-miss (price in discount zone but DX < threshold)
- **Green stars**: S2 buy signals (price in entry zone, no TI/TS filter)
- **Yellow stars**: S2 buy signals with TI/TS thresholds met

## V3 Differences from V2

- **EMA-based state machine** - No geometry dependency for entries
- **Tri-window acceleration** - S1 detection uses EMA60 acceleration patterns
- **Halo entry zone** - Entry zone uses 0.5 * ATR instead of fixed 3%
- **Simpler state transitions** - S0→S1→S2→S3 with clear EMA hierarchy checks
- **TI/TS thresholds** - TI = 0.45, TS = 0.58 (TS is primary gate)

## Optimization Strategy

Once we have multiple token results, we can optimize thresholds using:

1. **Data-Driven Analysis:**
   - Aggregate metrics across all backtests (win rate, avg return, Sharpe ratio)
   - Grid search over threshold space (TI/TS, DX, OX thresholds)
   - Statistical significance testing

2. **Performance Metrics:**
   - Entry quality (S2 entry signals vs actual outcomes)
   - Exit timing (OX threshold vs peak detection)
   - Risk-adjusted returns (max drawdown, volatility)
   - State transition accuracy (false positives/negatives)

3. **Validation:**
   - Out-of-sample testing (train on some tokens, validate on others)
   - Time-series cross-validation
   - "By eye" sanity checks (ensure signals make sense visually)

The optimization will be a hybrid: data-driven parameter search + visual validation.

