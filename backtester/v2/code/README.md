# Backtester

Backtesting workflow for UptrendEngineV2.

## Structure

- `v1/` - Current test results (one token at a time, until we change settings)
- `backtest_uptrend_v2.py` - Main backtest script
- `run_backtest.py` - Workflow script (backfill → geometry → TA → backtest)

## Usage

```bash
# Run full workflow for a token
python3 backtester/run_backtest.py DREAMS 14

# Or run backtest directly (assumes data/geometry/TA already exists)
python3 backtester/backtest_uptrend_v2.py DREAMS 14
```

## Workflow Steps

1. **Backfill 1h OHLCV data** - Fetches historical data from GeckoTerminal
2. **Build Geometry** - Generates S/R levels (no charts during backtest)
3. **Run TA Tracker** - Computes technical indicators (EMAs, RSI, ADX, etc.)
4. **Run Backtest** - Simulates engine execution hour-by-hour

## Output

- `backtest_results_v2_{TICKER}_{timestamp}.json` - Full results
- `backtest_results_{TICKER}_{timestamp}.png` - Chart visualization

## Chart Features

- **Red triangles (v)**: OX sell zones (trim opportunities)
- **Green triangles (^)**: DX buy signals (price in discount zone + DX >= threshold)
- **Orange circles**: DX near-miss (price in discount zone but DX < threshold)

## Optimization Strategy

Once we have multiple token results, we can optimize thresholds using:

1. **Data-Driven Analysis:**
   - Aggregate metrics across all backtests (win rate, avg return, Sharpe ratio)
   - Grid search over threshold space (tau_dx, tau_trim, aggressiveness curves)
   - Statistical significance testing

2. **Performance Metrics:**
   - Entry quality (DX threshold vs actual outcomes)
   - Exit timing (OX threshold vs peak detection)
   - Risk-adjusted returns (max drawdown, volatility)

3. **Validation:**
   - Out-of-sample testing (train on some tokens, validate on others)
   - Time-series cross-validation
   - "By eye" sanity checks (ensure signals make sense visually)

The optimization will be a hybrid: data-driven parameter search + visual validation.
