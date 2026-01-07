# Hyperliquid Integration Architecture Discussion

**Date**: 2025-01-XX  
**Status**: Design Phase - Testing Before Implementation

---

## Overview

Adding Hyperliquid token trading to Lotus Trader, treating it as a separate venue from the existing majors price data (which is for market understanding). This document explores the architecture decisions needed before implementation.

---

## Key Decisions & Questions

### 1. Data Source & Table Structure

**Current State:**
- `majors_price_data_ohlc` - Used for market understanding (BTC, ETH, SOL, HYPE, BNB)
- `lowcap_price_data_ohlc` - Used for Solana token trading
- Hyperliquid WebSocket already ingesting to `majors_trades_ticks` → rolled up to `majors_price_data_ohlc`

**Question**: How to handle Hyperliquid trading tokens (many more than just the 5 majors)?

**Options:**

**Option A: Separate Table for Hyperliquid Trading**
- Create `hyperliquid_price_data_ohlc` table
- Structure: Same as `lowcap_price_data_ohlc` but for Hyperliquid tokens
- Pros: Clear separation, no confusion with majors data
- Cons: Another table to maintain, code duplication

**Option B: Unified Table with Venue/Source Field**
- Add `venue` or `source` field to existing `lowcap_price_data_ohlc`
- Values: `"spot_solana"`, `"spot_hyperliquid"`, `"perp_hyperliquid"`, etc.
- Pros: Single table, unified queries
- Cons: Mixing different data sources, potential confusion

**Option C: Extend `lowcap_price_data_ohlc` with Chain-Based Routing**
- Use `token_chain = "hyperliquid"` to distinguish
- Same table structure, different ingestion path
- Pros: Minimal changes, leverages existing infrastructure
- Cons: Table name becomes misleading ("lowcap" but includes majors)

**Recommendation**: **Option A** - Create `hyperliquid_price_data_ohlc` table
- Clear separation from majors (market understanding) vs trading tokens
- Can reuse same schema as `lowcap_price_data_ohlc`
- Easy to query: `WHERE token_chain = 'hyperliquid' AND book_id = 'spot'`
- No confusion with majors data

**Schema Structure:**
```sql
CREATE TABLE hyperliquid_price_data_ohlc (
  token_contract TEXT NOT NULL,    -- "BTC", "ETH", "SOL", etc. (ticker as contract)
  chain TEXT NOT NULL DEFAULT 'hyperliquid',
  timeframe TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  open_usd NUMERIC NOT NULL,
  high_usd NUMERIC NOT NULL,
  low_usd NUMERIC NOT NULL,
  close_usd NUMERIC NOT NULL,
  volume NUMERIC NOT NULL,
  source TEXT DEFAULT 'hyperliquid',
  PRIMARY KEY (token_contract, chain, timeframe, timestamp)
);
```

---

### 2. Token Identification

**Current Schema:**
- `token_contract` - Contract address (for Solana)
- `token_ticker` - Display name (optional)

**For Hyperliquid:**
- Hyperliquid uses tickers: "BTC", "ETH", "SOL", "ARB", etc.
- No contract addresses (it's a centralized exchange)

**Decision**: Use ticker as `token_contract`
- `token_contract = "BTC"` (ticker)
- `token_ticker = "BTC"` (same, for display)
- `token_chain = "hyperliquid"`
- This keeps the schema consistent and allows the unique constraint to work

**Example Position:**
```json
{
  "token_chain": "hyperliquid",
  "token_contract": "BTC",
  "token_ticker": "BTC",
  "book_id": "spot",
  "timeframe": "1h"
}
```

---

### 3. Data Ingestion for Hyperliquid Trading Tokens

**Current Flow:**
- Hyperliquid WS → `majors_trades_ticks` → Rollup → `majors_price_data_ohlc`
- Only tracks: BTC, ETH, BNB, SOL, HYPE

**New Requirement:**
- Track many more Hyperliquid tokens for trading
- Need to ingest OHLC data for all tokens we want to trade

**Options:**

**Option A: Extend Existing Hyperliquid WS Ingester**
- Add more symbols to `HL_SYMBOLS` env var
- Same WebSocket connection, subscribe to more symbols
- Roll up to `hyperliquid_price_data_ohlc` (new table)
- Pros: Reuse existing infrastructure
- Cons: WebSocket subscription limits? Need to check Hyperliquid limits

**Option B: Separate Hyperliquid Trading Data Ingester**
- New service that queries Hyperliquid REST API for OHLC data
- Polls for tokens we're tracking (from positions table)
- Writes to `hyperliquid_price_data_ohlc`
- Pros: More control, can track any token
- Cons: Additional service, polling overhead

**Option C: Hybrid Approach**
- WebSocket for high-frequency tokens (active positions)
- REST API polling for watchlist tokens (lower frequency)
- Pros: Best of both worlds
- Cons: More complex

**Hyperliquid WebSocket Limits (from research):**
- **100 WebSocket connections per IP**
- **1,000 subscriptions per IP** (across all connections)
- **2,000 messages sent to Hyperliquid per minute**

**Recommendation**: **Option A** (extend existing) with separate WS for trading
- Use **ONE WebSocket connection** for all trading tokens
- Subscribe to all tokens from positions table (up to 1,000 limit)
- **Separate from majors WS**: Keep `hyperliquid_ws.py` for majors (market understanding)
- Create new `hyperliquid_trading_ws.py` for trading tokens

**Implementation:**
- Create `hyperliquid_trading_ws.py` (separate from majors WS)
- Subscribe to tokens from `lowcap_positions` where `token_chain='hyperliquid'`
- Roll up to `hyperliquid_price_data_ohlc` (not `majors_price_data_ohlc`)
- Monitor subscription count (stay under 1,000)
- If >1,000 tokens needed: Use REST API polling for additional tokens

---

### 4. Positions Table & Book ID

**Current Schema:**
- `book_id TEXT DEFAULT 'social'` - Currently used for "social" (lowcap tokens)
- `token_chain` - "solana", "ethereum", "base", "bsc"

**For Hyperliquid:**
- `token_chain = "hyperliquid"`
- `book_id = "perps"` (perpetual futures)
- Future: `token_chain = "binance"`, `token_chain = "bybit"` (all with `book_id = "perps"`)

**Learning System Scoping:**
- Scopes will automatically separate:
  - `token_chain=hyperliquid` vs `token_chain=solana`
  - `book_id=perps` vs `book_id=social`
- Same learning system, different scopes = perfect separation
- Future exchanges (Binance, Bybit) will share `book_id=perps` but have different `token_chain`

**No Schema Changes Needed:**
- Existing `book_id` field works perfectly
- Existing `token_chain` field works perfectly
- Unique constraint: `(token_contract, token_chain, timeframe)` still works

---

### 5. PM Routing Logic

**Current Flow:**
```
PM Core Tick (per timeframe)
  → Reads positions for timeframe
  → Computes A/E scores
  → Calls plan_actions_v4()
  → Executor executes
```

**Question**: How to route Hyperliquid positions to Hyperliquid PM?

**Options:**

**Option A: Unified PM Core Tick with Routing**
```
PM Core Tick
  → Fetch all positions (Solana + Hyperliquid)
  → Group by (token_chain, book_id)
  → Route to appropriate PM module:
     - PM_Spot (Solana) → SolanaExecutor
     - PM_Hyperliquid_Spot → HyperliquidExecutor
  → Each PM processes its positions independently
```

**Option B: Separate PM Core Tick Instances**
```
PM Core Tick (Solana)
  → Filters: token_chain != 'hyperliquid'
  → PM_Spot logic
  → SolanaExecutor

PM Core Tick (Hyperliquid)
  → Filters: token_chain == 'hyperliquid' AND book_id == 'spot'
  → PM_Hyperliquid_Spot logic
  → HyperliquidExecutor
```

**Option C: PM Module Pattern (Recommended)**
```
PM Core Tick (Universal Router)
  → Fetch positions for timeframe
  → For each position:
     - Determine PM module from (token_chain, book_id)
     - Call appropriate PM module:
       * PM_Spot.handle_position(position)
       * PM_Hyperliquid_Spot.handle_position(position)
  → Each PM module:
     - Computes A/E scores (same logic, different scopes)
     - Calls plan_actions_v4() (same logic)
     - Calls appropriate executor
```

**Recommendation**: **Option C** - PM Module Pattern
- Clean separation of concerns
- Each PM module is self-contained
- Easy to add new venues (perp, equities, etc.)
- Shared logic (A/E calculation, plan_actions_v4) but venue-specific execution

**Implementation Structure:**
```python
# src/intelligence/lowcap_portfolio_manager/pm/modules/
pm_spot.py              # Current Solana PM logic
pm_hyperliquid_spot.py  # New Hyperliquid spot PM
pm_hyperliquid_perp.py  # Future perp PM

# PM Core Tick becomes router:
class PMCoreTick:
    def __init__(self, timeframe):
        self.pm_modules = {
            ('solana', 'social'): PM_Spot(),
            ('hyperliquid', 'spot'): PM_Hyperliquid_Spot(),
        }
    
    def run(self):
        positions = self._fetch_positions()
        for position in positions:
            key = (position['token_chain'], position['book_id'])
            pm_module = self.pm_modules.get(key)
            if pm_module:
                pm_module.process_position(position)
```

**Alternative (Simpler for Testing):**
- Keep current PM Core Tick structure
- Add conditional logic: `if token_chain == 'hyperliquid': use HyperliquidExecutor`
- Same PM logic, different executor
- This works for initial testing since trading logic is identical (long-only, same signals)

---

### 6. Uptrend Engine Data Source

**Current:**
- Uptrend Engine reads from `lowcap_price_data_ohlc`
- Hardcoded table name in queries

**For Hyperliquid:**
- Need to read from `hyperliquid_price_data_ohlc` for Hyperliquid tokens

**Options:**

**Option A: Data Abstraction Layer**
```python
class PriceDataReader:
    def get_ohlc(self, token_contract, chain, timeframe):
        if chain == 'hyperliquid':
            table = 'hyperliquid_price_data_ohlc'
        else:
            table = 'lowcap_price_data_ohlc'
        return self.sb.table(table).select(...)
```

**Option B: Pass Table Name to Engine**
- Uptrend Engine accepts `data_source` parameter
- PM Core Tick determines correct table based on `token_chain`

**Option C: Unified View/Function**
- Create database view that unions both tables
- Uptrend Engine queries view, database handles routing

**Recommendation**: **Option A** for now (simplest)
- Create `PriceDataReader` utility
- Update Uptrend Engine to use it
- Minimal changes, clear separation

---

### 7. Executor Architecture

**Current:**
- `PMExecutor` - Handles Solana via Jupiter
- `allowed_chains = ['solana']` - Hardcoded restriction

**For Hyperliquid:**
- Create `HyperliquidExecutor` class
- Hyperliquid REST API client (separate from WebSocket)
- Handle spot orders (long-only for now)
- Leverage = 0 initially (part of sizing later)

**Structure:**
```python
class HyperliquidExecutor:
    def __init__(self, sb_client):
        self.sb = sb_client
        self.api_client = HyperliquidAPIClient()
    
    def execute(self, decision, position):
        # decision: {"decision_type": "add", "size_frac": 0.5, ...}
        # position: {token_contract, token_chain, timeframe, ...}
        
        if decision['decision_type'] == 'add':
            return self._execute_buy(position, decision)
        elif decision['decision_type'] == 'trim':
            return self._execute_sell(position, decision)
    
    def _execute_buy(self, position, decision):
        # Get latest price from hyperliquid_price_data_ohlc
        # Calculate notional_usd = total_allocation_usd * size_frac
        # Call Hyperliquid API: place_order(symbol, side='B', size, leverage=0)
        # Return execution result
```

**Testing Approach:**
1. Create `HyperliquidExecutor` with dry-run mode
2. Test order placement (without execution)
3. Test price fetching
4. Test position updates
5. Then enable live execution

---

### 8. Token Tracking Limits

**Current System:**
- Price collector has tiered collection:
  - 0-250 tokens: Every 1 min
  - 250-500 tokens: Every 2 min
  - 500-750 tokens: Every 3 min
  - etc.

**For Hyperliquid:**
- No hard database limit on positions
- Practical limits:
  - Price data ingestion rate
  - WebSocket subscription limits (check Hyperliquid docs)
  - Database query performance

**Recommendation:**
- Start with 10-20 Hyperliquid tokens for testing
- Monitor ingestion performance
- Scale up gradually
- If WebSocket limits hit, use REST API polling for additional tokens

---

### 9. Leverage & Sizing

**Decision**: Leverage is part of sizing, not fixed
- Start with leverage = 0 (spot)
- Later: Link leverage to A/E aggressiveness
- Example: High A score → higher leverage (within limits)
- This is PM logic, not executor logic

**Implementation:**
- Executor accepts `leverage` parameter in decision
- PM computes leverage based on A/E scores and scope
- For now: `leverage = 0` (spot only)

---

## Implementation Phases

### Phase 1: Data Infrastructure (Testing)
1. Create `hyperliquid_price_data_ohlc` table
2. Extend Hyperliquid WS ingester to support trading symbols
3. Test data ingestion for 5-10 Hyperliquid tokens
4. Verify rollup to OHLC works correctly

### Phase 2: Executor Testing
1. Create `HyperliquidExecutor` class (dry-run mode)
2. Test order placement logic (without execution)
3. Test price fetching from `hyperliquid_price_data_ohlc`
4. Test position update logic
5. Verify execution results format matches PM expectations

### Phase 3: PM Integration (Testing)
1. Update Uptrend Engine to read from `hyperliquid_price_data_ohlc`
2. Create test positions: `token_chain='hyperliquid'`, `book_id='spot'`
3. Test PM Core Tick routing (Option C or simpler conditional)
4. Verify A/E scores compute correctly
5. Verify `plan_actions_v4()` works with Hyperliquid positions

### Phase 4: End-to-End Testing
1. Create watchlist positions for Hyperliquid tokens
2. Let data accumulate (bars_count >= 300)
3. Test full cycle: Engine → PM → Executor → Position update
4. Verify learning system receives position_closed strands
5. Verify scopes separate correctly (hyperliquid vs solana)

### Phase 5: Production Enablement
1. Enable live execution (remove dry-run)
2. Start with small allocations
3. Monitor performance
4. Scale up token count gradually

---

## Open Questions

1. **Hyperliquid WebSocket Limits**: How many symbols can we subscribe to?
2. **Order Types**: Market orders only, or support limit orders?
3. **Slippage Handling**: How does Hyperliquid handle slippage for spot?
4. **Position Sizing**: Same sizing logic as Solana, or different multipliers?
5. **Regime Drivers**: Do Hyperliquid positions use same crypto regime drivers (BTC, ALT, buckets)?

---

## Next Steps

1. **Research**: Check Hyperliquid API docs for WebSocket subscription limits
2. **Design**: Finalize PM routing approach (Option C vs simpler conditional)
3. **Test**: Create `HyperliquidExecutor` in dry-run mode
4. **Test**: Verify data ingestion for Hyperliquid trading tokens
5. **Design**: Finalize data table structure (Option A recommended)

---

## Summary

**Architecture Decisions:**
- ✅ Separate `hyperliquid_price_data_ohlc` table (not reuse majors table)
- ✅ Use ticker as `token_contract` for Hyperliquid
- ✅ `token_chain = "hyperliquid"`, `book_id = "spot"`
- ✅ PM Module pattern for routing (Option C)
- ✅ Leverage = 0 initially, part of sizing later
- ✅ Same learning system, different scopes

**Testing First:**
- Test executor before full integration
- Test data ingestion before PM integration
- Test PM routing before production

**No Schema Changes Needed:**
- Existing `lowcap_positions` table works
- Existing `book_id` field works
- Just need new price data table and executor

