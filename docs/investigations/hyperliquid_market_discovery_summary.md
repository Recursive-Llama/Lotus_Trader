# Hyperliquid Market Discovery - Summary

**Date**: 2025-12-31  
**Status**: ✅ Implemented and Tested

---

## Problem

For Hyperliquid, we want to monitor **ALL available markets** (closed universe), not just positions we've created. This is different from Solana where we only track positions we've opened.

**Solution**: Market discovery system that:
1. Queries Hyperliquid for all available markets
2. Filters by requirements
3. Creates watchlist positions in database
4. WebSocket ingester discovers from these positions automatically

---

## Implementation

### `HyperliquidMarketDiscovery` Class

**Location**: `src/intelligence/lowcap_portfolio_manager/ingest/hyperliquid_market_discovery.py`

**Features**:
- Discovers main DEX markets (224 markets)
- Discovers HIP-3 markets (from all HIP-3 DEXs)
- Filters by requirements:
  - Min leverage (default: 1.0, no filter)
  - Exclude delisted markets
  - Include/exclude HIP-3
  - Include/exclude stock perps
- Creates watchlist positions for all timeframes (1m, 15m, 1h, 4h)
- Updates existing positions (ensures they're watchlist if not active)

---

## Discovery Results

**Test Run**:
- Main DEX: 186 markets discovered (after filtering)
- HIP-3: 41 markets discovered
- Total: 227 markets

**Sample Markets**:
- Main DEX: BTC (40x), ETH (25x), SOL (20x), etc.
- HIP-3: xyz:XYZ100, flx:TSLA, vntl:SPACEX, etc.

---

## Position Creation

**For Each Market**:
- Creates 4 positions (one per timeframe: 1m, 15m, 1h, 4h)
- Status: `watchlist` (ready to trade when data available)
- Book ID: `perps` (main DEX) or `stock_perps` (HIP-3)
- Stores metadata in `features.hyperliquid_metadata`:
  - `max_leverage`
  - `sz_decimals`
  - `dex` (for HIP-3)

**Example**:
```
BTC → 4 positions:
  - BTC (perps, 1m, watchlist)
  - BTC (perps, 15m, watchlist)
  - BTC (perps, 1h, watchlist)
  - BTC (perps, 4h, watchlist)
```

---

## Integration with WebSocket Ingester

**Flow**:
1. Market discovery runs (manually or scheduled)
2. Creates watchlist positions for all markets
3. WebSocket ingester discovers symbols from positions table
4. Subscribes to all discovered symbols
5. Ingests candle data for all markets

**Automatic**:
- When new markets are discovered, they're added to positions
- WebSocket ingester refreshes symbol list every 10 minutes
- New markets automatically get subscribed

---

## Configuration

**Env Vars**:
- `HL_DISCOVERY_MIN_LEVERAGE`: Min leverage filter (default: 1.0)
- `HL_DISCOVERY_INCLUDE_HIP3`: Include HIP-3 markets (default: true)
- `HL_DISCOVERY_INCLUDE_STOCK_PERPS`: Include stock perps (default: true)
- `HL_DISCOVERY_EXCLUDE_DELISTED`: Exclude delisted (default: true)
- `HL_DISCOVERY_TIMEFRAME`: Default timeframe (default: "1h")

---

## Usage

### Manual Discovery
```bash
# Discover and sync all markets
python src/intelligence/lowcap_portfolio_manager/ingest/hyperliquid_market_discovery.py

# Dry run (discover only, don't create positions)
python src/intelligence/lowcap_portfolio_manager/ingest/hyperliquid_market_discovery.py --dry-run

# With filters
python src/intelligence/lowcap_portfolio_manager/ingest/hyperliquid_market_discovery.py --min-leverage 5.0
```

### Programmatic
```python
from supabase import create_client
from src.intelligence.lowcap_portfolio_manager.ingest.hyperliquid_market_discovery import HyperliquidMarketDiscovery

sb = create_client(SUPABASE_URL, SUPABASE_KEY)
discovery = HyperliquidMarketDiscovery(sb)
results = discovery.run_discovery()
```

---

## Test Results

**Test**: Sync first 5 main DEX markets
- ✅ Created: 5 markets × 4 timeframes = 20 positions
- ✅ All positions created with correct schema
- ✅ Status: watchlist
- ✅ Book ID: perps
- ✅ Metadata stored correctly

---

## Next Steps

1. **Schedule Discovery**: Run discovery periodically (daily/weekly) to catch new markets
2. **Activity Gate**: Only persist candles for markets with activity (prevents bloat)
3. **Scale Test**: Test with full 227 markets (908 positions = 227 × 4 timeframes)
4. **WebSocket Integration**: Verify ingester discovers all symbols correctly

---

## Summary

✅ **Market discovery implemented and tested**

- Discovers all Hyperliquid markets (main DEX + HIP-3)
- Creates watchlist positions automatically
- WebSocket ingester discovers from positions
- Closed universe monitoring enabled

**Result**: When turned on, system will automatically monitor ALL Hyperliquid markets (with filters), not just positions we create.

