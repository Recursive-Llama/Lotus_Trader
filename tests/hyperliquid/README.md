# Hyperliquid Integration Tests

## Test Suite Overview

This directory contains tests for Hyperliquid integration, focusing on:
1. Candle/OHLC data availability (WebSocket and REST)
2. WebSocket subscription limits and behavior
3. Message volume comparisons
4. Executor functionality (future)

---

## Running Tests

### Candle Subscription Test

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies (if not already installed)
pip install websockets requests

# Run candle test
python tests/hyperliquid/test_candle_subscriptions.py
```

**Expected Output:**
- Tests WebSocket candle subscriptions (multiple formats)
- Tests REST API candle endpoints
- Compares message volume (trades vs candles)
- Saves results to `tests/hyperliquid/candle_test_results.json`

---

## Test Results

After running tests, check:
- `candle_test_results.json` - Detailed test results
- Console output - Summary and recommendations

---

## Next Tests (Future)

- Executor dry-run test
- WebSocket reconnection test
- Subscription diffing test
- Backpressure test

