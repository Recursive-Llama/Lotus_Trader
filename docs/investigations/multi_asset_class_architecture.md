# Multi-Asset Class Architecture Analysis

**Date**: 2025-01-XX  
**Question**: How does the current architecture scale to equities, commodities, FX, bonds?

---

## Current Architecture (Crypto)

**Data Flow:**
```
Price Data → TA Tracker → Uptrend Engine → PM Core Tick → Executor
```

**Key Components:**
- `PriceDataReader` (routes to correct OHLC table)
- `TATracker` (computes EMAs, ATR, etc.)
- `GeometryBuilder` (computes S/R, trendlines)
- `UptrendEngine` (state machine, signals)
- `PM Core Tick` (A/E scores, plan_actions_v4)
- `ExecutorFactory` (routes to venue-specific executor)

**Scoping:**
- `token_chain`: Exchange/venue (solana, hyperliquid, binance)
- `book_id`: Asset class (onchain_crypto, perps, spot_crypto)

---

## Asset Class Analysis

### 1. Equities (Stocks)

**Characteristics:**
- Market hours: 9:30 AM - 4:00 PM EST (NYSE/NASDAQ)
- Pre-market: 4:00 AM - 9:30 AM EST
- After-hours: 4:00 PM - 8:00 PM EST
- Gaps: Overnight, weekends, holidays
- Settlement: T+2 (trade date + 2 days)
- Data sources: IEX, Alpha Vantage, Polygon, Yahoo Finance

**Architecture Impact:**

#### A. Data Layer (`PriceDataReader`)

**Table Structure:**
```sql
CREATE TABLE equities_price_data_ohlc (
  token_contract TEXT NOT NULL,    -- "AAPL", "MSFT", "TSLA"
  chain TEXT NOT NULL DEFAULT 'nyse',  -- 'nyse', 'nasdaq', 'amex'
  timeframe TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  open_usd NUMERIC NOT NULL,
  high_usd NUMERIC NOT NULL,
  low_usd NUMERIC NOT NULL,
  close_usd NUMERIC NOT NULL,
  volume NUMERIC NOT NULL,
  -- Equities-specific
  adjusted_close NUMERIC,          -- Adjusted for splits/dividends
  split_factor NUMERIC,             -- Stock splits
  dividend NUMERIC,                  -- Dividends
  PRIMARY KEY (token_contract, chain, timeframe, timestamp)
);
```

**PriceDataReader Routing:**
```python
def get_table_name(self, token_chain: str) -> str:
    chain_lower = token_chain.lower()
    
    if chain_lower in ['nyse', 'nasdaq', 'amex']:
        return 'equities_price_data_ohlc'
    elif chain_lower == 'hyperliquid':
        return 'hyperliquid_price_data_ohlc'
    else:
        return 'lowcap_price_data_ohlc'  # Default: crypto
```

**Gap Handling:**
- **Option 1**: Forward-fill gaps (recommended for TA)
  - Overnight gap: Use previous close as open
  - Weekend gap: Forward-fill Friday close to Monday open
  - Holiday gap: Forward-fill last trading day close
  
- **Option 2**: Separate gap-aware ATR
  - Compute "session ATR" (intraday only)
  - Compute "overnight ATR" (gap magnitude)
  - Uptrend Engine uses session ATR for intraday signals

**Recommendation**: Forward-fill gaps in data layer, keep TA algorithms unchanged

#### B. TA Tracker

**Universality**: ✅ **Fully Universal**
- EMAs work on any price series (gaps don't break EMA calculation)
- ATR: Use session ATR (intraday only) or full ATR (with gaps)
- ADX, RSI, slopes: All work normally

**No Changes Needed**: Algorithms are universal

#### C. Geometry Builder

**Universality**: ✅ **Fully Universal**
- Swing detection: Works on any price series
- S/R clustering: Price levels are price levels
- Trendlines: Theil-Sen regression works on any data

**Gap Handling**: 
- Gaps create large swings (which is correct - they're real price movements)
- Geometry Builder will naturally detect gap boundaries as swing points
- This is actually **desired behavior** - gaps are structural features

**No Changes Needed**: Algorithms are universal

#### D. Uptrend Engine

**Universality**: ✅ **Fully Universal**
- State machine (S0-S4) works on any price series
- EMA geometry is venue-agnostic
- Signals (buy_flag, trim_flag) are structural

**Gap Handling**:
- Gaps can trigger state transitions (which is correct)
- If gap is too large, might need gap-aware ATR for thresholds
- **Recommendation**: Use session ATR for intraday signals, full ATR for swing signals

**Potential Enhancement**: Gap-aware ATR (optional, not required)

#### E. PM Core Tick

**Universality**: ✅ **Fully Universal**
- A/E computation: Regime-based (uses equity regime drivers)
- `plan_actions_v4()`: Signal-based (works on any signals)

**Market Hours Gate**:
```python
class PMCoreTick:
    def _can_trade_now(self, position: Dict[str, Any]) -> bool:
        """Check if venue allows trading right now."""
        token_chain = position.get('token_chain', '').lower()
        
        if token_chain in ['nyse', 'nasdaq', 'amex']:
            return self._is_market_open()
        else:
            return True  # Crypto/other: 24/7
    
    def _is_market_open(self) -> bool:
        """Check if US equity markets are open."""
        now = datetime.now(timezone.utc)
        # Convert to EST
        est = now.astimezone(timezone(timedelta(hours=-5)))
        hour = est.hour
        minute = est.minute
        
        # Market hours: 9:30 AM - 4:00 PM EST
        if est.weekday() >= 5:  # Saturday/Sunday
            return False
        
        market_open = (hour == 9 and minute >= 30) or (hour > 9 and hour < 16)
        return market_open
```

**Pre-Decision Gate**:
```python
def run(self):
    positions = self._active_positions()
    for position in positions:
        # Check if we can trade right now
        if not self._can_trade_now(position):
            continue  # Skip this position
        
        # Universal PM logic
        a_final, e_final = compute_ae_v2(...)
        decision = plan_actions_v4(...)
        # ... execute ...
```

**No Algorithm Changes**: Just add market hours gate

#### F. Executor

**Venue-Specific**: ❌ **Needs Equity Executor**

```python
class EquityExecutor:
    def __init__(self, sb_client, broker_api):
        self.sb = sb_client
        self.broker = broker_api  # IEX, Alpaca, Interactive Brokers, etc.
    
    def execute(self, decision, position):
        # Equity-specific execution:
        # - Order types: Market, Limit, Stop, Stop-Limit
        # - Fractional shares support
        # - Settlement: T+2
        # - Pre-market/after-hours restrictions
        # - Round lot requirements (some brokers)
        
        if decision['decision_type'] == 'add':
            return self._execute_buy(position, decision)
        elif decision['decision_type'] == 'trim':
            return self._execute_sell(position, decision)
```

**ExecutorFactory Update:**
```python
self.executors = {
    ('solana', 'onchain_crypto'): PMExecutor(...),
    ('hyperliquid', 'perps'): HyperliquidExecutor(...),
    ('nyse', 'stocks'): EquityExecutor(...),
    ('nasdaq', 'stocks'): EquityExecutor(...),
}
```

#### G. Regime Drivers

**Equity-Specific Regime Drivers:**
- `SPY` (S&P 500) - macro driver
- `QQQ` (Nasdaq 100) - tech driver
- `DIA` (Dow Jones) - blue chip driver
- `IWM` (Russell 2000) - small cap driver
- Equity buckets: large_cap, mid_cap, small_cap
- `SPY.d` (S&P 500 dominance)

**Book ID**: `book_id = 'stocks'`

**Regime Engine**: Same architecture, different drivers

---

### 2. Commodities (Futures)

**Characteristics:**
- Futures contracts: Expiration dates, rollover
- Continuous contracts: Front month, back month
- Settlement: Physical (some) vs cash-settled
- Trading hours: Varies by commodity (24/7 for some, session-based for others)
- Data sources: CME, ICE, Bloomberg, Quandl

**Architecture Impact:**

#### A. Data Layer

**Table Structure:**
```sql
CREATE TABLE commodities_price_data_ohlc (
  token_contract TEXT NOT NULL,    -- "CL" (crude oil), "GC" (gold), "NG" (natural gas)
  chain TEXT NOT NULL DEFAULT 'cme',  -- 'cme', 'ice', 'nymex'
  timeframe TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  open_usd NUMERIC NOT NULL,
  high_usd NUMERIC NOT NULL,
  low_usd NUMERIC NOT NULL,
  close_usd NUMERIC NOT NULL,
  volume NUMERIC NOT NULL,
  -- Commodities-specific
  contract_month TEXT,             -- "2025-03" (March 2025)
  is_front_month BOOLEAN,           -- True if front month contract
  open_interest NUMERIC,            -- Open interest
  PRIMARY KEY (token_contract, chain, timeframe, timestamp, contract_month)
);
```

**Continuous Contract Handling:**
- **Option 1**: Roll on expiration (recommended)
  - Track front month contract
  - On expiration, switch to next month
  - Forward-fill price (no gap on roll)
  
- **Option 2**: Back-adjusted continuous
  - Adjust historical prices for rollover
  - More complex, but preserves historical continuity

**PriceDataReader Routing:**
```python
def get_table_name(self, token_chain: str) -> str:
    if token_chain.lower() in ['cme', 'ice', 'nymex']:
        return 'commodities_price_data_ohlc'
    # ... other chains ...
```

#### B. TA/Geometry/Uptrend Engine

**Universality**: ✅ **Fully Universal**
- All algorithms work on any price series
- No changes needed

#### C. PM Core Tick

**Universality**: ✅ **Fully Universal**
- Same A/E logic
- Same plan_actions_v4()

**Contract Rollover Handling:**
- PM doesn't need to know about contracts
- Data layer handles continuous contract
- PM just sees continuous price series

#### D. Executor

**Venue-Specific**: ❌ **Needs Commodity Executor**

```python
class CommodityExecutor:
    def execute(self, decision, position):
        # Commodity-specific execution:
        # - Contract selection (front month)
        # - Rollover management
        # - Margin requirements (higher than equities)
        # - Position limits
        # - Settlement type (physical vs cash)
        
        # Get current front month contract
        front_month = self._get_front_month_contract(position['token_contract'])
        
        if decision['decision_type'] == 'add':
            return self._execute_buy(front_month, decision)
```

#### E. Regime Drivers

**Commodity-Specific Regime Drivers:**
- `CRB` (Commodity Research Bureau Index)
- `DBC` (Commodity ETF)
- Commodity buckets: energy, metals, agriculture, softs
- `CRB.d` (Commodity index dominance)

**Book ID**: `book_id = 'commodities'`

---

### 3. Foreign Exchange (FX)

**Characteristics:**
- 24/7 trading (except weekends)
- Quote conventions: Base/quote (EUR/USD)
- Pip-based pricing
- High leverage (50:1, 100:1 common)
- Data sources: OANDA, FXCM, Interactive Brokers

**Architecture Impact:**

#### A. Data Layer

**Table Structure:**
```sql
CREATE TABLE fx_price_data_ohlc (
  token_contract TEXT NOT NULL,    -- "EURUSD", "GBPUSD", "USDJPY"
  chain TEXT NOT NULL DEFAULT 'oanda',  -- 'oanda', 'fxcm', 'ib'
  timeframe TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  open_usd NUMERIC NOT NULL,        -- Actually quote price (1.0850 for EUR/USD)
  high_usd NUMERIC NOT NULL,
  low_usd NUMERIC NOT NULL,
  close_usd NUMERIC NOT NULL,
  volume NUMERIC NOT NULL,
  PRIMARY KEY (token_contract, chain, timeframe, timestamp)
);
```

**Quote Convention Handling:**
- Store as quote price (1.0850 for EUR/USD)
- TA algorithms work normally (price is price)
- No special handling needed

**PriceDataReader Routing:**
```python
def get_table_name(self, token_chain: str) -> str:
    if token_chain.lower() in ['oanda', 'fxcm', 'ib']:
        return 'fx_price_data_ohlc'
    # ... other chains ...
```

#### B. TA/Geometry/Uptrend Engine

**Universality**: ✅ **Fully Universal**
- All algorithms work on any price series
- No changes needed

#### C. PM Core Tick

**Universality**: ✅ **Fully Universal**
- Same A/E logic
- Same plan_actions_v4()

**Weekend Handling:**
- FX markets close Friday 5 PM EST, open Sunday 5 PM EST
- Data layer: Forward-fill Friday close to Sunday open
- PM doesn't need special handling

#### D. Executor

**Venue-Specific**: ❌ **Needs FX Executor**

```python
class FXExecutor:
    def execute(self, decision, position):
        # FX-specific execution:
        # - High leverage (50:1, 100:1)
        # - Pip-based pricing
        # - Lot sizes (standard, mini, micro)
        # - Long/short (always trading pairs)
        
        if decision['decision_type'] == 'add':
            return self._execute_buy(position, decision)
        elif decision['decision_type'] == 'trim':
            return self._execute_sell(position, decision)
```

#### E. Regime Drivers

**FX-Specific Regime Drivers:**
- `DXY` (Dollar Index) - macro driver
- `EURUSD` - major pair driver
- `GBPUSD` - major pair driver
- FX buckets: majors, minors, exotics
- `DXY.d` (Dollar dominance)

**Book ID**: `book_id = 'fx'`

---

### 4. Bonds

**Characteristics:**
- Fixed income: Yield-based pricing
- Duration, convexity
- Settlement: T+1 or T+2
- Data sources: Bloomberg, FRED, Treasury Direct

**Architecture Impact:**

#### A. Data Layer

**Table Structure:**
```sql
CREATE TABLE bonds_price_data_ohlc (
  token_contract TEXT NOT NULL,    -- "10Y" (10-year Treasury), "30Y" (30-year)
  chain TEXT NOT NULL DEFAULT 'treasury',  -- 'treasury', 'corporate', 'municipal'
  timeframe TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  open_usd NUMERIC NOT NULL,        -- Price (not yield)
  high_usd NUMERIC NOT NULL,
  low_usd NUMERIC NOT NULL,
  close_usd NUMERIC NOT NULL,
  volume NUMERIC NOT NULL,
  -- Bonds-specific
  yield NUMERIC,                    -- Yield to maturity
  duration NUMERIC,                 -- Duration
  PRIMARY KEY (token_contract, chain, timeframe, timestamp)
);
```

**Price vs Yield:**
- Store **price** (not yield) for TA algorithms
- TA works on price series (universal)
- Yield can be stored separately for analysis

**PriceDataReader Routing:**
```python
def get_table_name(self, token_chain: str) -> str:
    if token_chain.lower() in ['treasury', 'corporate', 'municipal']:
        return 'bonds_price_data_ohlc'
    # ... other chains ...
```

#### B. TA/Geometry/Uptrend Engine

**Universality**: ✅ **Fully Universal**
- All algorithms work on price series
- No changes needed

#### C. PM Core Tick

**Universality**: ✅ **Fully Universal**
- Same A/E logic
- Same plan_actions_v4()

#### D. Executor

**Venue-Specific**: ❌ **Needs Bond Executor**

```python
class BondExecutor:
    def execute(self, decision, position):
        # Bond-specific execution:
        # - Par value (typically $1000)
        # - Accrued interest
        # - Settlement: T+1 or T+2
        # - Minimum lot sizes
        
        if decision['decision_type'] == 'add':
            return self._execute_buy(position, decision)
```

#### E. Regime Drivers

**Bond-Specific Regime Drivers:**
- `10Y` (10-year Treasury) - macro driver
- `30Y` (30-year Treasury) - long-term driver
- `2Y` (2-year Treasury) - short-term driver
- Bond buckets: short_term, intermediate, long_term
- `10Y.d` (10Y yield dominance)

**Book ID**: `book_id = 'bonds'`

---

## Universal Architecture Summary

### What's Universal (No Changes Needed)

1. **TA Tracker**: ✅ All algorithms universal
2. **Geometry Builder**: ✅ All algorithms universal
3. **Uptrend Engine**: ✅ State machine universal
4. **PM Core Tick Logic**: ✅ A/E, plan_actions_v4 universal
5. **Learning System**: ✅ Scope-based separation works

### What Needs Abstraction

1. **PriceDataReader**: Routes to correct table based on `token_chain`
2. **ExecutorFactory**: Routes to correct executor based on `(token_chain, book_id)`
3. **Market Hours Gate**: Optional pre-decision check (equities only)

### What's Venue-Specific

1. **Data Tables**: One per asset class (equities_price_data_ohlc, etc.)
2. **Executors**: One per venue (EquityExecutor, CommodityExecutor, etc.)
3. **Regime Drivers**: Different drivers per asset class

---

## Architecture Validation

### ✅ PriceDataReader Abstraction

**Works for all asset classes:**
- Crypto: `lowcap_price_data_ohlc`, `hyperliquid_price_data_ohlc`
- Equities: `equities_price_data_ohlc`
- Commodities: `commodities_price_data_ohlc`
- FX: `fx_price_data_ohlc`
- Bonds: `bonds_price_data_ohlc`

**Routing logic:**
```python
def get_table_name(self, token_chain: str) -> str:
    chain_lower = token_chain.lower()
    
    # Asset class routing
    if chain_lower in ['nyse', 'nasdaq', 'amex']:
        return 'equities_price_data_ohlc'
    elif chain_lower in ['cme', 'ice', 'nymex']:
        return 'commodities_price_data_ohlc'
    elif chain_lower in ['oanda', 'fxcm', 'ib']:
        return 'fx_price_data_ohlc'
    elif chain_lower in ['treasury', 'corporate', 'municipal']:
        return 'bonds_price_data_ohlc'
    elif chain_lower == 'hyperliquid':
        return 'hyperliquid_price_data_ohlc'
    else:
        return 'lowcap_price_data_ohlc'  # Default: crypto
```

### ✅ ExecutorFactory Abstraction

**Works for all asset classes:**
```python
self.executors = {
    # Crypto
    ('solana', 'onchain_crypto'): PMExecutor(...),
    ('hyperliquid', 'perps'): HyperliquidExecutor(...),
    
    # Equities
    ('nyse', 'stocks'): EquityExecutor(...),
    ('nasdaq', 'stocks'): EquityExecutor(...),
    
    # Commodities
    ('cme', 'commodities'): CommodityExecutor(...),
    
    # FX
    ('oanda', 'fx'): FXExecutor(...),
    
    # Bonds
    ('treasury', 'bonds'): BondExecutor(...),
}
```

### ✅ PM Core Tick Universality

**Works for all asset classes:**
- A/E computation: Uses asset-class-specific regime drivers
- `plan_actions_v4()`: Universal signal-based logic
- Market hours gate: Optional, venue-specific check

### ✅ Learning System Scoping

**Works for all asset classes:**
- Scopes separate by `(token_chain, book_id)`
- Equities: `(nyse, stocks)` vs `(nasdaq, stocks)`
- Crypto: `(solana, onchain_crypto)` vs `(hyperliquid, perps)`
- Perfect separation, shared learning system

---

## Conclusion

**The architecture is universal and scales to all asset classes.**

**Key Design Principles:**
1. **Algorithms are universal** (TA, Geometry, Uptrend Engine, PM logic)
2. **Data source is abstracted** (PriceDataReader routes to correct table)
3. **Execution is abstracted** (ExecutorFactory routes to correct executor)
4. **Scoping separates** (token_chain + book_id = perfect separation)

**No major refactoring needed** - just add:
- New data tables per asset class
- New executors per venue
- New regime drivers per asset class
- Market hours gate (optional, equities only)

**The abstraction is correct** - we're building it the right way.

