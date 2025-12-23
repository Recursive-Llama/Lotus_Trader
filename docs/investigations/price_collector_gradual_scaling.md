# Price Collector: Gradual Scaling Strategy (IMPLEMENTED)

## Overview

**Key Insight**: Scale collection frequency based on total token count, with corresponding coverage threshold adjustments.

## Implementation Details

### Files Changed

1. **`src/trading/scheduled_price_collector.py`**
   - Added parallel async collection using `aiohttp`
   - Added tiered collection logic
   - Priority for active/watchlist 1m positions

2. **`src/intelligence/lowcap_portfolio_manager/ingest/rollup_ohlc.py`**
   - Added dynamic coverage threshold calculation
   - Threshold adjusts based on collection interval

## Scaling Tiers

| Tokens | Interval | Coverage Threshold | Bars/Hour |
|--------|----------|-------------------|-----------|
| 0-250  | 1 min    | 60%               | 60        |
| 250-500| 2 min    | 45%               | 30        |
| 500-750| 3 min    | ~33%              | 20        |
| 750-1000| 4 min   | ~25%              | 15        |

**Formula**:
- `interval = ceil(total_tokens / 250)`
- `threshold = 1/interval` (with buffer)

## Performance Results

**Before (sync)**:
- 26 tokens: 7.16 seconds
- ~218 tokens/minute

**After (async)**:
- 26 tokens: 0.27 seconds
- ~5,676 tokens/minute (26x faster!)

## Special Cases

### Active/Watchlist 1m Positions
- Always collected every 1 minute (priority)
- Uses hash-based distribution for other tokens

## How It Works

1. **Price Collector** (every 1 min):
   - Count total tokens
   - Calculate interval based on token count
   - Priority 1m positions: always collect
   - Other tokens: collect based on cycle % interval

2. **Rollup**:
   - Query total token count (cached 5 min)
   - Calculate dynamic threshold
   - Use threshold for partial bar validation

## Benefits

- ✅ Scales infinitely (just increase interval)
- ✅ Always stays at ~250 calls/min limit
- ✅ 26x faster with parallel collection
- ✅ No backfill triggered (threshold matches collection)
- ✅ Active 1m positions always prioritized

