# TA Tracker & Geometry Builder Universality Analysis

**Date**: 2025-01-XX  
**Question**: Are TA Tracker and Geometry Builder universal, or do they need venue-specific logic?

---

## Current Implementation

### TA Tracker

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/ta_tracker.py`

**What it does:**
1. Reads OHLC data from `lowcap_price_data_ohlc`
2. Computes technical indicators:
   - EMAs (60, 144, 333, etc.)
   - ATR (Average True Range)
   - ADX (Average Directional Index)
   - RSI (Relative Strength Index)
   - Slopes, z-scores, etc.
3. Writes to `lowcap_positions.features.ta`

**Current Query:**
```python
def _fetch_recent_ohlc(self, contract: str, chain: str, limit: int = 400):
    rows = (
        self.sb.table("lowcap_price_data_ohlc")
        .select("timestamp, open_usd, high_usd, low_usd, close_usd, volume")
        .eq("token_contract", contract)
        .eq("chain", chain)
        .eq("timeframe", self.timeframe)
        .order("timestamp", desc=True)
        .limit(limit)
        .execute()
        .data
    )
```

**Key Observation**: Hardcoded table name `"lowcap_price_data_ohlc"`

---

### Geometry Builder

**File**: `src/intelligence/lowcap_portfolio_manager/jobs/geometry_build_daily.py`

**What it does:**
1. Reads OHLC data from `lowcap_price_data_ohlc`
2. Computes:
   - Swing highs/lows
   - Support/Resistance levels (horizontal)
   - Trendlines (diagonals using Theil-Sen fitting)
   - ATH/ATL levels
3. Writes to `lowcap_positions.features.geometry`

**Current Query:**
```python
def _fetch_bars(self, contract: str, chain: str, end: datetime, minutes: int = None):
    query = (
        self.sb.table("lowcap_price_data_ohlc")
        .select("timestamp, open_usd, high_usd, low_usd, close_usd, volume")
        .eq("token_contract", contract)
        .eq("chain", chain)
        .eq("timeframe", self.timeframe)
        .lte("timestamp", end.isoformat())
        .order("timestamp", desc=True)
    )
```

**Key Observation**: Hardcoded table name `"lowcap_price_data_ohlc"`

---

## Universality Analysis

### Are the Algorithms Universal?

**TA Tracker Algorithms:**
- ✅ **EMAs**: Universal (exponential moving average is market-agnostic)
- ✅ **ATR**: Universal (volatility measurement works on any price series)
- ✅ **ADX**: Universal (trend strength indicator)
- ✅ **RSI**: Universal (momentum indicator)
- ✅ **Slopes**: Universal (rate of change)

**Geometry Builder Algorithms:**
- ✅ **Swing Detection**: Universal (local highs/lows are structural)
- ✅ **S/R Clustering**: Universal (price levels are price levels)
- ✅ **Trendline Fitting**: Universal (Theil-Sen regression works on any data)
- ✅ **ATH/ATL**: Universal (all-time high/low)

**Conclusion**: **The algorithms are 100% universal** - they operate on price data, not venue-specific concepts.

---

## The Problem: Data Source Routing

**Issue**: Both TA Tracker and Geometry Builder hardcode `"lowcap_price_data_ohlc"` table name.

**For Hyperliquid:**
- Need to read from `hyperliquid_price_data_ohlc` instead
- Same algorithms, different data source

**Solution**: **Data Abstraction Layer**

---

## Proposed Solution: Price Data Reader Abstraction

**Create a utility that routes to correct table based on `token_chain`:**

```python
# src/intelligence/lowcap_portfolio_manager/data/price_data_reader.py

class PriceDataReader:
    """Unified interface for reading OHLC data from any venue."""
    
    def __init__(self, sb_client: Client):
        self.sb = sb_client
    
    def get_table_name(self, token_chain: str) -> str:
        """Determine which table to read from based on token_chain."""
        chain_lower = token_chain.lower()
        
        if chain_lower == 'hyperliquid':
            return 'hyperliquid_price_data_ohlc'
        else:
            # Default: lowcap_price_data_ohlc (Solana, Ethereum, Base, BSC, etc.)
            return 'lowcap_price_data_ohlc'
    
    def fetch_recent_ohlc(
        self, 
        contract: str, 
        chain: str, 
        timeframe: str,
        limit: int = 400
    ) -> List[Dict[str, Any]]:
        """Fetch recent OHLC bars for any venue."""
        table = self.get_table_name(chain)
        
        rows = (
            self.sb.table(table)
            .select("timestamp, open_usd, high_usd, low_usd, close_usd, volume")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", timeframe)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
            .data
        )
        return rows or []
    
    def fetch_ohlc_since(
        self,
        contract: str,
        chain: str,
        timeframe: str,
        since_iso: str,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Fetch OHLC bars since a timestamp."""
        table = self.get_table_name(chain)
        
        rows = (
            self.sb.table(table)
            .select("timestamp, open_usd, high_usd, low_usd, close_usd, volume")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", timeframe)
            .gte("timestamp", since_iso)
            .order("timestamp", desc=False)
            .limit(limit)
            .execute()
            .data
        )
        return rows or []
    
    def fetch_bars_for_geometry(
        self,
        contract: str,
        chain: str,
        timeframe: str,
        end: datetime,
        lookback_minutes: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch bars for geometry building (with optional lookback)."""
        table = self.get_table_name(chain)
        
        query = (
            self.sb.table(table)
            .select("timestamp, open_usd, high_usd, low_usd, close_usd, volume")
            .eq("token_contract", contract)
            .eq("chain", chain)
            .eq("timeframe", timeframe)
            .lte("timestamp", end.isoformat())
            .order("timestamp", desc=True)
        )
        
        if lookback_minutes:
            start = end - timedelta(minutes=lookback_minutes)
            query = query.gte("timestamp", start.isoformat())
        
        rows = query.limit(9999).execute().data  # Geometry builder limit
        return rows or []
```

---

## Updated TA Tracker

```python
# src/intelligence/lowcap_portfolio_manager/jobs/ta_tracker.py

from src.intelligence.lowcap_portfolio_manager.data.price_data_reader import PriceDataReader

class TATracker:
    def __init__(self, timeframe: str = "1h"):
        # ... existing init ...
        self.data_reader = PriceDataReader(self.sb)
    
    def _fetch_recent_ohlc(self, contract: str, chain: str, limit: int = 400):
        """Fetch recent OHLC - now venue-agnostic."""
        return self.data_reader.fetch_recent_ohlc(
            contract, chain, self.timeframe, limit
        )
```

---

## Updated Geometry Builder

```python
# src/intelligence/lowcap_portfolio_manager/jobs/geometry_build_daily.py

from src.intelligence.lowcap_portfolio_manager.data.price_data_reader import PriceDataReader

class GeometryBuilder:
    def __init__(self, timeframe: str = "1h", generate_charts: bool = True):
        # ... existing init ...
        self.data_reader = PriceDataReader(self.sb)
    
    def _fetch_bars(self, contract: str, chain: str, end: datetime, minutes: int = None):
        """Fetch bars for geometry - now venue-agnostic."""
        return self.data_reader.fetch_bars_for_geometry(
            contract, chain, self.timeframe, end, minutes
        )
```

---

## Uptrend Engine

**Also needs updating** - it reads from `lowcap_price_data_ohlc`:

```python
# src/intelligence/lowcap_portfolio_manager/jobs/uptrend_engine_v4.py

from src.intelligence.lowcap_portfolio_manager.data.price_data_reader import PriceDataReader

class UptrendEngineV4:
    def __init__(self, timeframe: str = "1h"):
        # ... existing init ...
        self.data_reader = PriceDataReader(self.sb)
    
    def _fetch_recent_ohlc(self, contract: str, chain: str, limit: int = 400):
        """Fetch recent OHLC - now venue-agnostic."""
        return self.data_reader.fetch_recent_ohlc(
            contract, chain, self.timeframe, limit
        )
    
    def _fetch_ohlc_since(self, contract: str, chain: str, since_iso: str, limit: int = 500):
        """Fetch OHLC since timestamp - now venue-agnostic."""
        return self.data_reader.fetch_ohlc_since(
            contract, chain, self.timeframe, since_iso, limit
        )
```

---

## Summary

### Are TA Tracker & Geometry Builder Universal?

**Algorithms**: ✅ **100% Universal**
- All indicators work on price data regardless of venue
- No venue-specific logic needed in calculations

**Data Source**: ⚠️ **Needs Abstraction**
- Currently hardcoded to `lowcap_price_data_ohlc`
- Need to route to correct table based on `token_chain`

### Solution

**Create `PriceDataReader` abstraction:**
- Routes to correct table based on `token_chain`
- TA Tracker, Geometry Builder, Uptrend Engine all use it
- Algorithms stay unchanged
- Only data source routing changes

### Implementation Impact

**Files to Update:**
1. ✅ Create `price_data_reader.py` (new)
2. ✅ Update `ta_tracker.py` (use PriceDataReader)
3. ✅ Update `geometry_build_daily.py` (use PriceDataReader)
4. ✅ Update `uptrend_engine_v4.py` (use PriceDataReader)

**No Algorithm Changes Needed:**
- All calculations stay the same
- Just data source routing changes

---

## Conclusion

**TA Tracker & Geometry Builder are universal** - they just need a data abstraction layer to route to the correct price data table based on `token_chain`.

This is the same pattern as executor routing - the logic is universal, only the data source/execution differs.

